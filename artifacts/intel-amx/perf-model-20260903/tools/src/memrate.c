// memrate.c - per-core DRAM streaming-read rate with N concurrent readers.
// Each thread is pinned to one CPU, owns a private buffer far larger than its
// share of the L3, and reads it sequentially in a loop until the time is up.
// Descends from perf-fluctuation/deep-dive/harness/membw.c (2026-08), with:
//   - one process, N threads, a start barrier so all readers overlap fully;
//   - 64-byte AVX-512 loads, 8 independent accumulators (one load per line);
//   - optional "tile" mode: AMX TILELOADD of 1 KiB tiles (16 rows x 64 B,
//     stride 64 B, the K-mirror panel pattern) instead of vector loads.
// Buffers are touched by their own thread (first touch on the thread's NUMA
// node; run under numactl --membind=0 as well).
// Usage: memrate --cpus LIST --threads N [--mb 1024] [--seconds 8] [--mode load|tile] [--huge thp|none]
// Output: one line per thread "thread i cpu C GB/s R" and one "aggregate" line.

#define _GNU_SOURCE
#include <immintrin.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#define XFEATURE_XTILEDATA 18

static double now(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + t.tv_nsec * 1e-9;
}

struct cfg {
  int cpus[512];
  int ncpu, threads, mode_tile, huge;
  size_t bytes;
  double seconds;
};

struct targ {
  const struct cfg* c;
  int idx, cpu;
  double gbs;
  atomic_int* ready;
  atomic_int* go;
};

struct tile_config {
  uint8_t palette, start_row;
  uint8_t reserved[14];
  uint16_t column_bytes[16];
  uint8_t rows[16];
};

static void* run(void* p) {
  struct targ* a = (struct targ*)p;
  const struct cfg* c = a->c;
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(a->cpu, &set);
  if (sched_setaffinity(0, sizeof set, &set)) { perror("setaffinity"); exit(1); }
  uint8_t* buf = mmap(NULL, c->bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (buf == MAP_FAILED) { perror("mmap"); exit(1); }
  madvise(buf, c->bytes, c->huge ? MADV_HUGEPAGE : MADV_NOHUGEPAGE);
  memset(buf, 1 + a->idx, c->bytes);
  if (c->mode_tile) {
    if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) != 0) { perror("arch_prctl"); exit(1); }
    struct tile_config tc;
    memset(&tc, 0, sizeof tc);
    tc.palette = 1;
    for (int i = 0; i < 8; i++) { tc.rows[i] = 16; tc.column_bytes[i] = 64; }
    _tile_loadconfig(&tc);
  }
  atomic_fetch_add(a->ready, 1);
  while (!atomic_load(a->go)) _mm_pause();
  const double t_end = now() + c->seconds;
  double bytes = 0;
  __m512i acc0 = _mm512_setzero_si512(), acc1 = acc0, acc2 = acc0, acc3 = acc0, acc4 = acc0, acc5 = acc0, acc6 = acc0, acc7 = acc0;
  double t0 = now();
  while (now() < t_end) {
    if (!c->mode_tile) {
      for (size_t off = 0; off + 512 <= c->bytes; off += 512) {
        const uint8_t* p8 = buf + off;
        acc0 = _mm512_add_epi64(acc0, _mm512_load_si512((const void*)(p8 + 0)));
        acc1 = _mm512_add_epi64(acc1, _mm512_load_si512((const void*)(p8 + 64)));
        acc2 = _mm512_add_epi64(acc2, _mm512_load_si512((const void*)(p8 + 128)));
        acc3 = _mm512_add_epi64(acc3, _mm512_load_si512((const void*)(p8 + 192)));
        acc4 = _mm512_add_epi64(acc4, _mm512_load_si512((const void*)(p8 + 256)));
        acc5 = _mm512_add_epi64(acc5, _mm512_load_si512((const void*)(p8 + 320)));
        acc6 = _mm512_add_epi64(acc6, _mm512_load_si512((const void*)(p8 + 384)));
        acc7 = _mm512_add_epi64(acc7, _mm512_load_si512((const void*)(p8 + 448)));
      }
    } else {
      // 1 KiB tiles, contiguous (stride 64 B), 4 tiles per 4 KiB: the K-mirror
      // panel read pattern of qk_mirror_128x4.
      for (size_t off = 0; off + 4096 <= c->bytes; off += 4096) {
        const uint8_t* p8 = buf + off;
        _tile_loadd(0, p8 + 0, 64);
        _tile_loadd(1, p8 + 1024, 64);
        _tile_loadd(2, p8 + 2048, 64);
        _tile_loadd(3, p8 + 3072, 64);
      }
    }
    bytes += (double)c->bytes;
  }
  double t1 = now();
  if (c->mode_tile) _tile_release();
  // keep the accumulators alive
  __m512i s = _mm512_add_epi64(_mm512_add_epi64(acc0, acc1), _mm512_add_epi64(acc2, acc3));
  s = _mm512_add_epi64(s, _mm512_add_epi64(_mm512_add_epi64(acc4, acc5), _mm512_add_epi64(acc6, acc7)));
  volatile long long sink = _mm512_reduce_add_epi64(s);
  (void)sink;
  a->gbs = bytes / (t1 - t0) / 1e9;
  munmap(buf, c->bytes);
  return NULL;
}

static void parse_cpus(const char* s, struct cfg* c) {
  c->ncpu = 0;
  char* dup = strdup(s);
  for (char* tok = strtok(dup, ","); tok; tok = strtok(NULL, ",")) {
    char* dash = strchr(tok, '-');
    if (dash) { *dash = 0; int a = atoi(tok), b = atoi(dash + 1); for (int x = a; x <= b; x++) c->cpus[c->ncpu++] = x; }
    else c->cpus[c->ncpu++] = atoi(tok);
  }
  free(dup);
}

int main(int argc, char** argv) {
  struct cfg c;
  memset(&c, 0, sizeof c);
  c.threads = 1; c.bytes = 1024ull << 20; c.seconds = 8; c.huge = 1;
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--cpus") && i + 1 < argc) parse_cpus(argv[++i], &c);
    else if (!strcmp(argv[i], "--threads") && i + 1 < argc) c.threads = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--mb") && i + 1 < argc) c.bytes = (size_t)atol(argv[++i]) << 20;
    else if (!strcmp(argv[i], "--seconds") && i + 1 < argc) c.seconds = atof(argv[++i]);
    else if (!strcmp(argv[i], "--mode") && i + 1 < argc) c.mode_tile = !strcmp(argv[++i], "tile");
    else if (!strcmp(argv[i], "--huge") && i + 1 < argc) {
      const char* h = argv[++i];
      if (!strcmp(h, "thp")) c.huge = 1;
      else if (!strcmp(h, "none")) c.huge = 0;
      else { fprintf(stderr, "--huge thp|none (1 GiB pages are not supported here)\n"); return 2; }
    }
    else { fprintf(stderr, "usage: memrate --cpus LIST --threads N [--mb 1024] [--seconds 8] [--mode load|tile] [--huge thp|none]\n"); return 2; }
  }
  if (c.threads > c.ncpu) { fprintf(stderr, "need %d cpus, got %d\n", c.threads, c.ncpu); return 2; }
  pthread_t th[512];
  struct targ ta[512];
  atomic_int ready = 0, go = 0;
  for (int i = 0; i < c.threads; i++) {
    ta[i].c = &c; ta[i].idx = i; ta[i].cpu = c.cpus[i]; ta[i].ready = &ready; ta[i].go = &go; ta[i].gbs = 0;
    pthread_create(&th[i], NULL, run, &ta[i]);
  }
  while (atomic_load(&ready) < c.threads) usleep(1000);
  atomic_store(&go, 1);
  double sum = 0, mn = 1e9, mx = 0;
  for (int i = 0; i < c.threads; i++) {
    pthread_join(th[i], NULL);
    sum += ta[i].gbs;
    if (ta[i].gbs < mn) mn = ta[i].gbs;
    if (ta[i].gbs > mx) mx = ta[i].gbs;
  }
  for (int i = 0; i < c.threads; i++) printf("thread %d cpu %d GB/s %.2f\n", i, ta[i].cpu, ta[i].gbs);
  printf("aggregate mode=%s threads=%d mb=%zu seconds=%.0f huge=%s per_core_GBs_mean %.2f min %.2f max %.2f total_GBs %.1f\n",
      c.mode_tile ? "tile" : "load", c.threads, c.bytes >> 20, c.seconds, c.huge ? "thp" : "none", sum / c.threads, mn, mx, sum);
  return 0;
}
