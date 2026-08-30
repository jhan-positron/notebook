// AMX runtime-overhead microbenchmark (Bill's question, 2026-08-21).
// Measures on the actual 6962P what opt-manual Table 20-2 documents for the
// Sapphire-Rapids-era chapter: setup (arch_prctl, XFD first-use fault,
// LDTILECFG), teardown (TILERELEASE), per-instruction costs (TILEZERO,
// TILELOADD, TILESTORED, TDPBF16PS latency + throughput), and the
// AMX<->non-AMX seams (tile store -> vector load round trip; AVX-512 FMA
// block right after TDP* per opt-manual 20.11.3).
//
// Usage: bench_amx_overhead <mode> <iters>
//   modes: baseline ldtilecfg cfg_release sttilecfg tilerelease tilezero
//          tileload tilestore tdp_lat tdp_tput store_fwd store_far
//          fma_pure fma_after_tdp oneshot cpuid
// Cycle counts come from `sudo -n perf stat -e cycles` over the whole run
// (subtract the baseline mode); the program itself prints TSC ns/op.
#include <immintrin.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

#include <cstdint>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#define XFEATURE_XTILEDATA 18

struct tile_config {
  uint8_t palette, start_row;
  uint8_t reserved[14];
  uint16_t column_bytes[16];
  uint8_t rows[16];
};

static tile_config g_cfg;
alignas(64) static uint16_t g_a[16 * 32];
alignas(64) static uint16_t g_b[16 * 32];
alignas(64) static float g_c[16 * 16];
alignas(64) static float g_far[16];

static inline uint64_t tsc_begin() {
  _mm_lfence();
  uint64_t t = __rdtsc();
  _mm_lfence();
  return t;
}
static inline uint64_t tsc_end() {
  unsigned aux;
  uint64_t t = __rdtscp(&aux);
  _mm_lfence();
  return t;
}

static void make_cfg() {
  memset(&g_cfg, 0, sizeof g_cfg);
  g_cfg.palette = 1;
  for (int i = 0; i < 8; i++) {
    g_cfg.rows[i] = 16;
    g_cfg.column_bytes[i] = 64;
  }
}

static double tsc_ghz() {
  // Calibrate TSC against CLOCK_MONOTONIC over 50 ms.
  struct timespec a, b;
  clock_gettime(CLOCK_MONOTONIC, &a);
  uint64_t t0 = __rdtsc();
  do {
    clock_gettime(CLOCK_MONOTONIC, &b);
  } while ((b.tv_sec - a.tv_sec) * 1e9 + (b.tv_nsec - a.tv_nsec) < 50e6);
  uint64_t t1 = __rdtsc();
  double ns = (b.tv_sec - a.tv_sec) * 1e9 + (b.tv_nsec - a.tv_nsec);
  return (t1 - t0) / ns;
}

// One-time costs, each measured individually with serialized TSC.
static void oneshot() {
  uint64_t t0 = tsc_begin();
  long rc = syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA);
  uint64_t t1 = tsc_end();
  double ghz = tsc_ghz();
  printf("tsc_ghz %.3f\n", ghz);
  printf("arch_prctl_rc %ld tsc %lu ns %.0f\n", rc, t1 - t0, (t1 - t0) / ghz);

  // Per-thread XFD first-use: in fresh threads, time the first LDTILECFG,
  // the first TILEDATA-touching instruction (TILEZERO), and a second
  // TILEZERO for contrast.
  for (int rep = 0; rep < 8; rep++) {
    pthread_t th;
    auto fn = [](void*) -> void* {
      uint64_t r[6];
      r[0] = tsc_begin();
      _tile_loadconfig(&g_cfg);
      r[1] = tsc_end();
      r[2] = tsc_begin();
      _tile_zero(0);
      r[3] = tsc_end();
      r[4] = tsc_begin();
      _tile_zero(1);
      r[5] = tsc_end();
      _tile_release();
      auto* out = new uint64_t[3];
      out[0] = r[1] - r[0];
      out[1] = r[3] - r[2];
      out[2] = r[5] - r[4];
      return out;
    };
    void* ret;
    pthread_create(&th, nullptr, fn, nullptr);
    pthread_join(th, &ret);
    uint64_t* v = (uint64_t*)ret;
    printf("thread%d first_ldtilecfg_tsc %lu first_tilezero_tsc %lu "
           "second_tilezero_tsc %lu  (ns %.0f / %.0f / %.0f)\n",
        rep, v[0], v[1], v[2], v[0] / ghz, v[1] / ghz, v[2] / ghz);
    delete[] v;
  }
  // Main-thread first use for completeness (permission was just granted).
  uint64_t a0 = tsc_begin();
  _tile_loadconfig(&g_cfg);
  uint64_t a1 = tsc_end();
  uint64_t b0 = tsc_begin();
  _tile_zero(0);
  uint64_t b1 = tsc_end();
  _tile_release();
  printf("main first_ldtilecfg_tsc %lu first_tilezero_tsc %lu (ns %.0f / %.0f)\n",
      a1 - a0, b1 - b0, (a1 - a0) / ghz, (b1 - b0) / ghz);
}

static void cpuid_report() {
  unsigned a, b, c, d;
  __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d)
                   : "a"(0xD), "c"(0));
  printf("xsave_max_size_enabled %u max_size_all %u\n", b, c);
  __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d)
                   : "a"(0xD), "c"(17));
  printf("xtilecfg size %u offset %u\n", a, b);
  __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d)
                   : "a"(0xD), "c"(18));
  printf("xtiledata size %u offset %u ecx %u\n", a, b, c);
}

int main(int argc, char** argv) {
  const char* mode = argc > 1 ? argv[1] : "baseline";
  long n = argc > 2 ? atol(argv[2]) : 1000000;
  make_cfg();
  for (int i = 0; i < 16 * 32; i++) {
    g_a[i] = 0x3f80 >> 0;  // bf16 patterns; values irrelevant
    g_b[i] = 0x3f00;
  }

  if (!strcmp(mode, "cpuid")) {
    cpuid_report();
    return 0;
  }
  if (!strcmp(mode, "oneshot")) {
    oneshot();
    return 0;
  }

  if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA)) {
    fprintf(stderr, "arch_prctl failed\n");
    return 1;
  }
  double ghz = tsc_ghz();

  // Warm everything once (XFD fault, page faults, config cached).
  _tile_loadconfig(&g_cfg);
  _tile_zero(0);
  _tile_zero(1);
  _tile_zero(2);
  _tile_zero(3);
  _tile_loadd(6, g_a, 64);
  _tile_loadd(7, g_b, 64);
  _tile_stored(0, g_c, 64);
  g_far[0] = 1.f;

  uint64_t t0 = tsc_begin();

  if (!strcmp(mode, "baseline")) {
    for (long i = 0; i < n; i++)
      __asm__ volatile("" ::: "memory");
  } else if (!strcmp(mode, "ldtilecfg")) {
    for (long i = 0; i < n; i++)
      _tile_loadconfig(&g_cfg);
  } else if (!strcmp(mode, "cfg_release")) {
    for (long i = 0; i < n; i++) {
      _tile_loadconfig(&g_cfg);
      _tile_release();
    }
  } else if (!strcmp(mode, "sttilecfg")) {
    static tile_config out;
    for (long i = 0; i < n; i++)
      _tile_storeconfig(&out);
  } else if (!strcmp(mode, "tilerelease")) {
    for (long i = 0; i < n; i++)
      _tile_release();
  } else if (!strcmp(mode, "tilezero")) {
    for (long i = 0; i < n; i++)
      _tile_zero(0);
  } else if (!strcmp(mode, "tileload")) {
    for (long i = 0; i < n; i++)
      _tile_loadd(6, g_a, 64);
  } else if (!strcmp(mode, "tilestore")) {
    for (long i = 0; i < n; i++)
      _tile_stored(0, g_c, 64);
  } else if (!strcmp(mode, "tdp_lat")) {
    // Dependent chain: same C accumulator every time.
    for (long i = 0; i < n; i++)
      _tile_dpbf16ps(0, 6, 7);
  } else if (!strcmp(mode, "tdp_tput")) {
    // 4 independent accumulators.
    for (long i = 0; i < n; i += 4) {
      _tile_dpbf16ps(0, 6, 7);
      _tile_dpbf16ps(1, 6, 7);
      _tile_dpbf16ps(2, 6, 7);
      _tile_dpbf16ps(3, 6, 7);
    }
  } else if (!strcmp(mode, "store_fwd")) {
    // Tile store, then immediately a dependent vector load of the SAME line.
    __m512 acc = _mm512_setzero_ps();
    for (long i = 0; i < n; i++) {
      _tile_stored(0, g_c, 64);
      acc = _mm512_add_ps(acc, _mm512_load_ps(g_c));
    }
    _mm512_store_ps(g_far, acc);
  } else if (!strcmp(mode, "store_far")) {
    // Tile store, then a vector load of an UNRELATED hot line.
    __m512 acc = _mm512_setzero_ps();
    for (long i = 0; i < n; i++) {
      _tile_stored(0, g_c, 64);
      acc = _mm512_add_ps(acc, _mm512_load_ps(g_far));
    }
    _mm512_store_ps(g_far, acc);
  } else if (!strcmp(mode, "fma_pure") || !strcmp(mode, "fma_after_tdp")) {
    // 80 FMAs per iteration in 10 independent chains - enough parallelism
    // to be PORT-bound (2 FMA ports when port 5 is open, 1 when closed),
    // not latency-bound. fma_after_tdp issues one TDP first each iteration
    // (opt-manual 20.11.3: a <100-instruction AVX-512 block after TDP runs
    // with the port-5 FMA closed).
    const int with_tdp = !strcmp(mode, "fma_after_tdp");
    __m512 x0, x1, x2, x3, x4, x5, x6, x7, x8, x9;
    x0 = x1 = x2 = x3 = x4 = x5 = x6 = x7 = x8 = x9 =
        _mm512_set1_ps(1.0001f);
    __m512 m = _mm512_set1_ps(0.9999f);
#define FMA_ROUND()                 \
  x0 = _mm512_fmadd_ps(x0, m, x0);  \
  x1 = _mm512_fmadd_ps(x1, m, x1);  \
  x2 = _mm512_fmadd_ps(x2, m, x2);  \
  x3 = _mm512_fmadd_ps(x3, m, x3);  \
  x4 = _mm512_fmadd_ps(x4, m, x4);  \
  x5 = _mm512_fmadd_ps(x5, m, x5);  \
  x6 = _mm512_fmadd_ps(x6, m, x6);  \
  x7 = _mm512_fmadd_ps(x7, m, x7);  \
  x8 = _mm512_fmadd_ps(x8, m, x8);  \
  x9 = _mm512_fmadd_ps(x9, m, x9)
    for (long i = 0; i < n; i++) {
      if (with_tdp) _tile_dpbf16ps(0, 6, 7);
      FMA_ROUND(); FMA_ROUND(); FMA_ROUND(); FMA_ROUND();
      FMA_ROUND(); FMA_ROUND(); FMA_ROUND(); FMA_ROUND();
    }
#undef FMA_ROUND
    __m512 acc = _mm512_add_ps(_mm512_add_ps(_mm512_add_ps(x0, x1),
                                   _mm512_add_ps(x2, x3)),
        _mm512_add_ps(_mm512_add_ps(x4, x5),
            _mm512_add_ps(_mm512_add_ps(x6, x7), _mm512_add_ps(x8, x9))));
    _mm512_store_ps(g_far, acc);
  } else {
    fprintf(stderr, "unknown mode %s\n", mode);
    return 1;
  }

  uint64_t t1 = tsc_end();
  _tile_release();
  printf("%s iters %ld tsc_total %lu tsc/op %.2f ns/op %.2f tsc_ghz %.3f\n",
      mode, n, t1 - t0, double(t1 - t0) / n, (t1 - t0) / ghz / n, ghz);
  return 0;
}
