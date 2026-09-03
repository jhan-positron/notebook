// insn_loops.cpp - one-core instruction cost loops for the model's floors.
// Each loop runs alone (--only NAME) for a few seconds so an external clock
// sampler (turbostat, 1 s interval) can attribute a core clock to it:
//   vdp_tp4 / vdp_tp8 / vdp_tp16 : VDPBF16PS throughput with 4 / 8 / 16
//                                  independent accumulators (distinct initial
//                                  values so the compiler cannot merge them;
//                                  throughput-bound only when 8 and 16 agree)
//   vdp_lat  : VDPBF16PS latency, one dependent chain
//   hred_tp  : horizontal reduce_add throughput, independent inputs, results
//              stored (the dotter's per-token reduction pattern)
//   hred_lat : reduce_add in a dependent chain (latency upper bound; the
//              dotter never chains reductions)
//   dotter_l1: the dotter<bf16,128> per-token sequence over one L1-resident
//              64-token page, 4 heads: the QK arithmetic floor directly
//   tdp_tp   : TDPBF16PS throughput, 4 independent destination tiles
//   tdp_lat  : TDPBF16PS dependent chain (same destination tile)
//   tld_l1   : TILELOADD of L1-resident 1 KiB tiles
// Output per loop: "<name> ns_per_insn X tsc_ticks_per_insn Y  <note>", plus
// the run's wall time so the sampler window is known.
// Usage: insn_loops --cpu C --only NAME [--seconds S]

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
#include <type_traits>
#include <utility>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#define XFEATURE_XTILEDATA 18

static inline uint64_t rdtsc_fenced() {
  unsigned lo, hi;
  __asm__ volatile("lfence\n\trdtsc\n\tlfence" : "=a"(lo), "=d"(hi));
  return (uint64_t(hi) << 32) | lo;
}
static double now_s() { timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static double tsc_ghz() { double t0 = now_s(); uint64_t c0 = rdtsc_fenced(); while (now_s() - t0 < 0.2) {} double t1 = now_s(); uint64_t c1 = rdtsc_fenced(); return (c1 - c0) / (t1 - t0) / 1e9; }

struct tile_config { uint8_t palette, start_row; uint8_t reserved[14]; uint16_t column_bytes[16]; uint8_t rows[16]; };

using bf16 = uint16_t;

static void report(const char* name, uint64_t ticks, double n, double tsc, double wall, const char* note) {
  printf("%-9s ns_per_insn %.4f tsc_ticks_per_insn %.3f  wall_s %.2f  %s\n", name, ticks / tsc / n, double(ticks) / n, wall, note);
  fflush(stdout);
}

#define KEEP(v) __asm__ volatile("" : "+v"(v))

int main(int argc, char** argv) {
  int cpu = 0; double seconds = 3.0; std::string only;
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--cpu") && i + 1 < argc) cpu = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--only") && i + 1 < argc) only = argv[++i];
    else if (!strcmp(argv[i], "--seconds") && i + 1 < argc) seconds = atof(argv[++i]);
    else { fprintf(stderr, "usage: insn_loops --cpu C --only NAME [--seconds S]\n"); return 2; }
  }
  cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu, &set); sched_setaffinity(0, sizeof set, &set);
  const double tsc = tsc_ghz();
  printf("cpu %d tsc %.4f GHz loop %s target_seconds %.1f\n", cpu, tsc, only.c_str(), seconds);
  fflush(stdout);
  // Repeat the inner loop until `seconds` have passed; report per instruction.
  auto timed = [&](auto body, double insns_per_iter, long iters_per_call) {
    double n_calls = 0; uint64_t total = 0; const double t_end = now_s() + seconds;
    body(1000);  // warm
    while (now_s() < t_end) { uint64_t t0 = rdtsc_fenced(); body(iters_per_call); total += rdtsc_fenced() - t0; n_calls++; }
    return std::pair<uint64_t, double>(total, n_calls * iters_per_call * insns_per_iter);
  };

  alignas(64) uint16_t a[32], b[32];
  for (int i = 0; i < 32; i++) { a[i] = 0x3f80 + i; b[i] = 0x3f00 + i; }
  __m512bh va = (__m512bh)_mm512_load_si512(a), vb = (__m512bh)_mm512_load_si512(b);
  const long IT = 4000000;
  double wall0 = now_s();

  if (only == "vdp_tp4" || only == "vdp_tp8" || only == "vdp_tp16") {
    // The chain count is a compile-time constant so the accumulators stay in
    // zmm registers. With a runtime count GCC keeps c[] on the stack and each
    // chain step becomes load, VDPBF16PS, store: the loop then times the
    // store-to-load round trip, not the instruction.
    auto run_tp = [&](auto ch) {
      constexpr int CH = decltype(ch)::value;
      __m512 c[CH];
      for (int k = 0; k < CH; k++) c[k] = _mm512_set1_ps(1.0f + k);  // distinct: no merging
      auto body = [&](long n) {
        for (long i = 0; i < n; i++) {
          for (int k = 0; k < CH; k++) c[k] = _mm512_dpbf16_ps(c[k], va, vb);
        }
        for (int k = 0; k < CH; k++) KEEP(c[k]);
      };
      auto [ticks, n] = timed(body, CH, IT);
      __m512 s = c[0]; for (int k = 1; k < CH; k++) s = _mm512_add_ps(s, c[k]);
      volatile float sink = _mm512_reduce_add_ps(s); (void)sink;
      char note[64]; snprintf(note, sizeof note, "%d independent register accumulators", CH);
      report(only.c_str(), ticks, n, tsc, now_s() - wall0, note);
    };
    if (only == "vdp_tp4") run_tp(std::integral_constant<int, 4>{});
    else if (only == "vdp_tp8") run_tp(std::integral_constant<int, 8>{});
    else run_tp(std::integral_constant<int, 16>{});
  } else if (only == "vdp_lat") {
    __m512 c0 = _mm512_set1_ps(1.0f);
    auto body = [&](long n) { for (long i = 0; i < n; i++) { c0 = _mm512_dpbf16_ps(c0, va, vb); c0 = _mm512_dpbf16_ps(c0, va, vb); c0 = _mm512_dpbf16_ps(c0, va, vb); c0 = _mm512_dpbf16_ps(c0, va, vb); } KEEP(c0); };
    auto [ticks, n] = timed(body, 4, IT);
    volatile float sink = _mm512_reduce_add_ps(c0); (void)sink;
    report("vdp_lat", ticks, n, tsc, now_s() - wall0, "one dependent chain");
  } else if (only == "hred_tp") {
    __m512 v[8]; for (int k = 0; k < 8; k++) v[k] = _mm512_set1_ps(1.0f + k * 0.001f);
    alignas(64) static float out[64];
    auto body = [&](long n) {
      for (long i = 0; i < n; i++) {
        for (int k = 0; k < 8; k++) { KEEP(v[k]); out[(i & 7) * 8 + k] = _mm512_reduce_add_ps(v[k]); }
        __asm__ volatile("" ::: "memory");
      }
    };
    auto [ticks, n] = timed(body, 8, IT / 4);
    volatile float sink = out[3]; (void)sink;
    report("hred_tp", ticks, n, tsc, now_s() - wall0, "independent reduce_add, results stored (dotter pattern)");
  } else if (only == "hred_lat") {
    __m512 v = _mm512_set1_ps(1.0001f); float acc = 0;
    auto body = [&](long n) { for (long i = 0; i < n; i++) { acc = _mm512_reduce_add_ps(v); v = _mm512_set1_ps(acc * 1e-9f); } };
    auto [ticks, n] = timed(body, 1, IT / 4);
    volatile float sink = acc; (void)sink;
    report("hred_lat", ticks, n, tsc, now_s() - wall0, "dependent chain reduce+mul+broadcast: latency upper bound, not the dotter's cost");
  } else if (only == "dotter_l1") {
    // dotter<bf16,128> over one 64-token page (16 KiB, L1-resident), 4 heads:
    // per token per head 4 loads, 4 VDPBF16PS into 2 chains, add, reduce, store.
    alignas(64) static bf16 K[64 * 128], Q[4 * 128];
    alignas(64) static float S[4][64];
    for (int i = 0; i < 64 * 128; i++) K[i] = 0x3f00 + (i & 63);
    for (int i = 0; i < 4 * 128; i++) Q[i] = 0x3f80 + (i & 31);
    auto body = [&](long n) {
      for (long it = 0; it < n; it++) {
        for (int o = 0; o < 4; o++) {
          __m512i x01 = _mm512_load_si512(Q + o * 128), x23 = _mm512_load_si512(Q + o * 128 + 32), x45 = _mm512_load_si512(Q + o * 128 + 64), x67 = _mm512_load_si512(Q + o * 128 + 96);
          KEEP(x01); KEEP(x23); KEEP(x45); KEEP(x67);
          for (int t = 0; t < 64; t++) {
            const bf16* y = K + t * 128;
            __m512 s1 = _mm512_dpbf16_ps(_mm512_setzero_ps(), (__m512bh)x01, (__m512bh)_mm512_load_si512(y));
            __m512 s2 = _mm512_dpbf16_ps(_mm512_setzero_ps(), (__m512bh)x23, (__m512bh)_mm512_load_si512(y + 32));
            s1 = _mm512_dpbf16_ps(s1, (__m512bh)x45, (__m512bh)_mm512_load_si512(y + 64));
            s2 = _mm512_dpbf16_ps(s2, (__m512bh)x67, (__m512bh)_mm512_load_si512(y + 96));
            S[o][t] = _mm512_reduce_add_ps(_mm512_add_ps(s1, s2));
          }
        }
        __asm__ volatile("" ::: "memory");
      }
    };
    auto [ticks, n] = timed(body, 256, IT / 512);  // 256 dots per page pass
    volatile float sink = S[1][7]; (void)sink;
    report("dotter_l1", ticks, n, tsc, now_s() - wall0, "per (token, head) dot of the dotter over an L1-resident page; x256 = one unit's QK arithmetic");
  } else if (only == "tdp_tp" || only == "tdp_lat" || only == "tld_l1") {
    if (syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) != 0) { printf("%s: AMX not available on this host\n", only.c_str()); return 0; }
    tile_config cfg{}; cfg.palette = 1; for (int i = 0; i < 8; i++) { cfg.rows[i] = 16; cfg.column_bytes[i] = 64; }
    _tile_loadconfig(&cfg);
    alignas(64) static uint16_t A[16 * 32], B[16 * 32];
    for (int i = 0; i < 16 * 32; i++) { A[i] = 0x3f80; B[i] = 0x3f00; }
    _tile_loadd(4, A, 64); _tile_loadd(5, B, 64);
    _tile_zero(0); _tile_zero(1); _tile_zero(2); _tile_zero(3);
    if (only == "tdp_tp") {
      auto body = [&](long n) { for (long i = 0; i < n; i++) { _tile_dpbf16ps(0, 4, 5); _tile_dpbf16ps(1, 4, 5); _tile_dpbf16ps(2, 4, 5); _tile_dpbf16ps(3, 4, 5); } };
      auto [ticks, n] = timed(body, 4, IT / 8);
      report("tdp_tp", ticks, n, tsc, now_s() - wall0, "4 independent destination tiles");
    } else if (only == "tdp_lat") {
      auto body = [&](long n) { for (long i = 0; i < n; i++) { _tile_dpbf16ps(0, 4, 5); _tile_dpbf16ps(0, 4, 5); _tile_dpbf16ps(0, 4, 5); _tile_dpbf16ps(0, 4, 5); } };
      auto [ticks, n] = timed(body, 4, IT / 8);
      report("tdp_lat", ticks, n, tsc, now_s() - wall0, "same destination tile (dependent)");
    } else {
      auto body = [&](long n) { for (long i = 0; i < n; i++) { _tile_loadd(4, A, 64); _tile_loadd(5, B, 64); _tile_loadd(6, A, 64); _tile_loadd(7, B, 64); } };
      auto [ticks, n] = timed(body, 4, IT / 8);
      report("tld_l1", ticks, n, tsc, now_s() - wall0, "TILELOADD, L1-resident 1 KiB tiles");
    }
    alignas(64) static float O[16 * 16];
    _tile_stored(0, O, 64);
    _tile_release();
    volatile float sink = O[0]; (void)sink;
  } else {
    fprintf(stderr, "unknown --only %s\n", only.c_str());
    return 2;
  }
  return 0;
}
