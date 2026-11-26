// gdn-20261120 clock probe: one-core loops that show how fast the core runs under three kinds of work.
//   fma : AVX-512 FP32 fused multiply-add, 8 independent accumulators (the GDN recurrence's instruction).
//   tdp : AMX TDPBF16PS (bf16 tile dot product), 4 independent destination tiles.
//   mix : 4 tile products, then 64 FMAs, repeated (a block kernel mixes the two kinds of work).
// It prints nanoseconds per instruction and TSC ticks per instruction. The TSC runs at a constant rate, so a
// change of ns per instruction between this machine and a machine with a known clock is a change of core clock.
// The caller samples /sys/devices/system/cpu/cpuN/cpufreq/scaling_cur_freq while a loop runs.
// Usage: clock_probe --cpu C --only fma|tdp|mix [--seconds S]
// Build: g++ -O2 -std=c++17 -march=x86-64-v4 -mamx-tile -mamx-bf16 clock_probe.cpp -o clock_probe
#include <immintrin.h>
#include <sched.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#define XFEATURE_XTILEDATA 18

static double now_s() {
  timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return double(ts.tv_sec) + 1e-9 * double(ts.tv_nsec);
}

struct tile_config {
  uint8_t palette;
  uint8_t start_row;
  uint8_t reserved[14];
  uint16_t bytes_per_row[16];
  uint8_t rows[16];
};

alignas(64) static uint16_t A[16][32];
alignas(64) static uint16_t B[16][32];
alignas(64) static float OUT[16][16];

// 64 FMAs: 8 accumulators x 8 rounds. The accumulators stay in registers.
static inline void fma_block(__m512& a0, __m512& a1, __m512& a2, __m512& a3, __m512& a4, __m512& a5, __m512& a6,
    __m512& a7, __m512 x, __m512 y) {
  for (int r = 0; r < 8; r++) {
    a0 = _mm512_fmadd_ps(x, y, a0);
    a1 = _mm512_fmadd_ps(x, y, a1);
    a2 = _mm512_fmadd_ps(x, y, a2);
    a3 = _mm512_fmadd_ps(x, y, a3);
    a4 = _mm512_fmadd_ps(x, y, a4);
    a5 = _mm512_fmadd_ps(x, y, a5);
    a6 = _mm512_fmadd_ps(x, y, a6);
    a7 = _mm512_fmadd_ps(x, y, a7);
  }
}

// Tile products with no live 512-bit register: the upper halves of the vector registers are cleared first.
__attribute__((noinline)) static uint64_t tdp_clean(int reps) {
  _mm256_zeroupper();
  for (int rep = 0; rep < reps; rep++) {
    _tile_dpbf16ps(0, 4, 5); _tile_dpbf16ps(1, 4, 5); _tile_dpbf16ps(2, 4, 5); _tile_dpbf16ps(3, 4, 5);
  }
  return uint64_t(reps) * 4;
}

alignas(64) static float ACC[8][16];

// One block of 64 FMAs whose accumulators live in memory between calls, then the upper halves are cleared.
__attribute__((noinline)) static void fma_block_mem() {
  __m512 a0 = _mm512_load_ps(ACC[0]), a1 = _mm512_load_ps(ACC[1]), a2 = _mm512_load_ps(ACC[2]), a3 = _mm512_load_ps(ACC[3]);
  __m512 a4 = _mm512_load_ps(ACC[4]), a5 = _mm512_load_ps(ACC[5]), a6 = _mm512_load_ps(ACC[6]), a7 = _mm512_load_ps(ACC[7]);
  __m512 const x = _mm512_set1_ps(1.0e-3f), y = _mm512_set1_ps(1.0e-3f);
  fma_block(a0, a1, a2, a3, a4, a5, a6, a7, x, y);
  _mm512_store_ps(ACC[0], a0); _mm512_store_ps(ACC[1], a1); _mm512_store_ps(ACC[2], a2); _mm512_store_ps(ACC[3], a3);
  _mm512_store_ps(ACC[4], a4); _mm512_store_ps(ACC[5], a5); _mm512_store_ps(ACC[6], a6); _mm512_store_ps(ACC[7], a7);
  _mm256_zeroupper();
}

int main(int argc, char** argv) {
  int cpu = -1;
  double seconds = 4.0;
  std::string only = "fma";
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--cpu") && i + 1 < argc) cpu = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--only") && i + 1 < argc) only = argv[++i];
    else if (!strcmp(argv[i], "--seconds") && i + 1 < argc) seconds = atof(argv[++i]);
  }
  if (cpu >= 0) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) { perror("sched_setaffinity"); return 1; }
  }
  bool const tiles = only != "fma";
  if (tiles) {
    if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) != 0) { perror("arch_prctl"); return 1; }
    tile_config cfg{};
    cfg.palette = 1;
    for (int i = 0; i < 8; i++) { cfg.bytes_per_row[i] = 64; cfg.rows[i] = 16; }
    _tile_loadconfig(&cfg);
    for (int r = 0; r < 16; r++)
      for (int c = 0; c < 32; c++) { A[r][c] = 0x3c00; B[r][c] = 0x3c00; }  // bf16 small positive values
    _tile_loadd(4, A, 64);
    _tile_loadd(5, B, 64);
    _tile_zero(0); _tile_zero(1); _tile_zero(2); _tile_zero(3);
  }
  if (only == "tdpz" || only == "mixz" || only == "mixzp") {
    // tdpz : tile products only, upper vector halves cleared (no 512-bit state at all).
    // mixz : 4 tile products, then 64 FMAs with memory accumulators and a clear, repeated (fine-grained mix).
    // mixzp: 4,096 tile products, then 16,384 FMAs, repeated (phases of about 25 us, as a block kernel would have).
    uint64_t nt = 0, nf = 0;
    double const t0 = now_s();
    uint64_t const c0 = __rdtsc();
    double t1 = t0;
    while (t1 - t0 < seconds) {
      if (only == "tdpz") {
        nt += tdp_clean(20000);
      } else if (only == "mixz") {
        for (int rep = 0; rep < 20000; rep++) { nt += tdp_clean(1); fma_block_mem(); nf += 64; }
      } else {
        for (int rep = 0; rep < 20; rep++) {
          nt += tdp_clean(1024);
          for (int b = 0; b < 256; b++) { fma_block_mem(); nf += 64; }
        }
      }
      t1 = now_s();
    }
    uint64_t const c1 = __rdtsc();
    _tile_stored(0, OUT, 64);
    _tile_release();
    double const wall = t1 - t0, ticks = double(c1 - c0);
    printf("%s cpu %d wall_s %.3f tsc_hz %.0f tdp %llu fma %llu ns_per_tdp_if_alone %.4f ns_total_per_tdp %.4f ticks_total_per_tdp %.3f acc %.3g out %.3g\n",
        only.c_str(), cpu, wall, ticks / wall, (unsigned long long)nt, (unsigned long long)nf, nf ? 0.0 : 1e9 * wall / nt,
        1e9 * wall / nt, ticks / nt, ACC[0][0], OUT[0][0]);
    return 0;
  }
  __m512 a0 = _mm512_set1_ps(0.0f), a1 = a0, a2 = a0, a3 = a0, a4 = a0, a5 = a0, a6 = a0, a7 = a0;
  __m512 const x = _mm512_set1_ps(1.0e-3f), y = _mm512_set1_ps(1.0e-3f);
  uint64_t n_fma = 0, n_tdp = 0;
  double const t0 = now_s();
  uint64_t const c0 = __rdtsc();
  double t1 = t0;
  while (t1 - t0 < seconds) {
    for (int rep = 0; rep < 20000; rep++) {
      if (only == "fma") {
        fma_block(a0, a1, a2, a3, a4, a5, a6, a7, x, y);
        n_fma += 64;
      } else if (only == "tdp") {
        _tile_dpbf16ps(0, 4, 5); _tile_dpbf16ps(1, 4, 5); _tile_dpbf16ps(2, 4, 5); _tile_dpbf16ps(3, 4, 5);
        n_tdp += 4;
      } else {
        _tile_dpbf16ps(0, 4, 5); _tile_dpbf16ps(1, 4, 5); _tile_dpbf16ps(2, 4, 5); _tile_dpbf16ps(3, 4, 5);
        n_tdp += 4;
        fma_block(a0, a1, a2, a3, a4, a5, a6, a7, x, y);
        n_fma += 64;
      }
    }
    t1 = now_s();
  }
  uint64_t const c1 = __rdtsc();
  if (tiles) { _tile_stored(0, OUT, 64); _tile_release(); }
  float sink[16];
  _mm512_storeu_ps(sink, _mm512_add_ps(_mm512_add_ps(a0, a1), _mm512_add_ps(_mm512_add_ps(a2, a3),
                             _mm512_add_ps(_mm512_add_ps(a4, a5), _mm512_add_ps(a6, a7)))));
  double const wall = t1 - t0;
  double const ticks = double(c1 - c0);
  printf("%s cpu %d wall_s %.3f tsc_hz %.0f", only.c_str(), cpu, wall, ticks / wall);
  if (only == "fma") printf(" fma %llu ns_per_fma %.4f ticks_per_fma %.4f", (unsigned long long)n_fma, 1e9 * wall / n_fma, ticks / n_fma);
  else if (only == "tdp") printf(" tdp %llu ns_per_tdp %.4f ticks_per_tdp %.3f", (unsigned long long)n_tdp, 1e9 * wall / n_tdp, ticks / n_tdp);
  else printf(" tdp %llu fma %llu ns_per_round %.3f ticks_per_round %.2f (one round = 4 tile products + 64 FMAs)",
      (unsigned long long)n_tdp, (unsigned long long)n_fma, 1e9 * wall / (n_tdp / 4.0), ticks / (n_tdp / 4.0));
  printf(" sink %.3g out %.3g\n", sink[0], OUT[0][0]);
  return 0;
}
