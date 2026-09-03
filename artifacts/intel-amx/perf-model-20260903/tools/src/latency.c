// latency.c - dependent-load memory latency (pointer chase) on one CPU.
// Builds one random cycle over all cache lines of a buffer (Sattolo's
// algorithm), then follows it: each load's address depends on the previous
// load's value, so one hop = one memory access latency.
// Run alone for idle latency; run while memrate streams on the other cores for
// loaded latency. The buffer should be several times the L3 (432 MB here) or
// part of the hops hit in the L3: use --mb 8192 with --huge 1g (8 huge pages,
// no TLB walks) for the DRAM number; --mb 1024 rows are kept for comparison.
// Usage: latency --cpu C [--mb 1024] [--hops 20000000] [--huge thp|none|1g]
// Output: "latency cpu C mb M huge_requested H huge_obtained O ns_per_hop X"

#define _GNU_SOURCE
#include <errno.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>

#ifndef MAP_HUGE_1GB
#define MAP_HUGE_1GB (30 << 26)
#endif

static double now(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + t.tv_nsec * 1e-9;
}
static uint64_t splitmix(uint64_t* s) {
  uint64_t z = (*s += 0x9e3779b97f4a7c15ull);
  z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
  z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
  return z ^ (z >> 31);
}
static void smaps(long* anon_kb, long* htlb_kb) {
  *anon_kb = *htlb_kb = 0;
  FILE* f = fopen("/proc/self/smaps_rollup", "r");
  if (!f) return;
  char line[256];
  long v;
  while (fgets(line, sizeof line, f)) {
    if (sscanf(line, "AnonHugePages: %ld kB", &v) == 1) *anon_kb = v;
    else if (sscanf(line, "Shared_Hugetlb: %ld kB", &v) == 1) *htlb_kb += v;
    else if (sscanf(line, "Private_Hugetlb: %ld kB", &v) == 1) *htlb_kb += v;
  }
  fclose(f);
}

int main(int argc, char** argv) {
  int cpu = 0;
  const char* huge = "thp";
  size_t mb = 1024;
  long hops = 20000000;
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--cpu") && i + 1 < argc) cpu = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--mb") && i + 1 < argc) mb = (size_t)atol(argv[++i]);
    else if (!strcmp(argv[i], "--hops") && i + 1 < argc) hops = atol(argv[++i]);
    else if (!strcmp(argv[i], "--huge") && i + 1 < argc) huge = argv[++i];
    else { fprintf(stderr, "usage: latency --cpu C [--mb 1024] [--hops N] [--huge thp|none|1g]\n"); return 2; }
  }
  if (strcmp(huge, "thp") && strcmp(huge, "none") && strcmp(huge, "1g")) { fprintf(stderr, "--huge thp|none|1g\n"); return 2; }
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(cpu, &set);
  if (sched_setaffinity(0, sizeof set, &set)) { perror("setaffinity"); return 1; }
  const size_t bytes = mb << 20, lines = bytes / 64;
  uint8_t* buf = MAP_FAILED;
  const char* obtained = huge;
  if (!strcmp(huge, "1g")) {
    size_t rounded = (bytes + (1ull << 30) - 1) & ~((1ull << 30) - 1);
    buf = mmap(NULL, rounded, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB | MAP_HUGE_1GB, -1, 0);
    if (buf == MAP_FAILED) { fprintf(stderr, "note: 1 GiB pages unavailable (%s); falling back to THP\n", strerror(errno)); obtained = "thp-fallback"; }
  }
  if (buf == MAP_FAILED) {
    const size_t align = 2u << 20;
    uint8_t* raw = mmap(NULL, bytes + align, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED) { perror("mmap"); return 1; }
    buf = (uint8_t*)(((uintptr_t)raw + align - 1) & ~(uintptr_t)(align - 1));
    madvise(buf, bytes, strcmp(huge, "none") ? MADV_HUGEPAGE : MADV_NOHUGEPAGE);
  }
  memset(buf, 0, bytes);
  // random cycle over line indices: next[i] stored in the first 8 bytes of line i
  uint32_t* perm = malloc(lines * sizeof(uint32_t));
  for (size_t i = 0; i < lines; i++) perm[i] = (uint32_t)i;
  uint64_t s = 0xC0FFEE;
  for (size_t i = lines - 1; i > 0; i--) {  // Sattolo: one cycle
    size_t j = splitmix(&s) % i;
    uint32_t t = perm[i]; perm[i] = perm[j]; perm[j] = t;
  }
  for (size_t i = 0; i < lines; i++) {
    uint64_t* line = (uint64_t*)(buf + (size_t)perm[i] * 64);
    *line = (uint64_t)perm[(i + 1) % lines] * 64;
  }
  free(perm);
  long anon_kb, htlb_kb;
  smaps(&anon_kb, &htlb_kb);
  // warm the chase (TLB, page table), then time
  volatile uint64_t idx = 0;
  for (long h = 0; h < 500000; h++) idx = *(uint64_t*)(buf + idx);
  double t0 = now();
  uint64_t p = idx;
  for (long h = 0; h < hops; h++) p = *(uint64_t*)(buf + p);
  double t1 = now();
  idx = p;
  printf("latency cpu %d mb %zu huge_requested %s huge_obtained %s anon_huge_mib %ld hugetlb_mib %ld ns_per_hop %.1f\n",
      cpu, mb, huge, obtained, anon_kb / 1024, htlb_kb / 1024, (t1 - t0) / hops * 1e9);
  return (int)(idx & 1);
}
