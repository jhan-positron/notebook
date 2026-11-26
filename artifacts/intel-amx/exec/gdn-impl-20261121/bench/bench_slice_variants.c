// gdn-impl-20261121: why does the GDN recurrence run at about 1.1 vector operations per cycle on delphi-3b35
// even when its state stays in the L1 cache? (Task 1 measured 4,700 cycles per value head per token for the
// column-half order. The count of 5,120 operations at 2 per cycle predicts 2,560.)
//
// NOT tron code. Each variant runs the same arithmetic as gdn_recurrence (h/tron/kernels/gated_delta_net.hpp)
// for one value head (128 key rows x 128 value columns) and a chain of 128 tokens, with another loop shape or
// another state layout. Every variant is checked for equal bits against the token loop.
// Words: chunk = 16 value columns (one 512-bit register); slice = the chunks processed together;
// pass 1 = the read loop (remembered value), pass 2 = the write loop (new state and output).
//
// Build: clang-19 -O3 -march=native -o bench_slice_variants bench_slice_variants.c -lm
// Run:   taskset -c CPU ./bench_slice_variants CPU
#define _GNU_SOURCE
#include <immintrin.h>
#include <math.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define KD 128
#define VD 128
#define NCH 8
#define NTOK 128

static inline uint64_t now_ns(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
  return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}
static uint64_t rng_state = 0x243F6A8885A308D3ull;
static inline double urand(void) {
  rng_state ^= rng_state << 13;
  rng_state ^= rng_state >> 7;
  rng_state ^= rng_state << 17;
  return (double)(rng_state >> 11) / 9007199254740992.0;
}
static inline float bf16_round(float x) {
  uint32_t b;
  memcpy(&b, &x, 4);
  b = (b + 0x7fff + ((b >> 16) & 1)) & 0xffff0000u;
  memcpy(&x, &b, 4);
  return x;
}
static float *alloc_f(size_t n) {
  float *p = aligned_alloc(4096, ((n * sizeof(float)) + 4095) / 4096 * 4096);
  if (!p) abort();
  memset(p, 0, n * sizeof(float));
  return p;
}

// inputs of one value head: K, QS (query already scaled) [NTOK][KD]; V [NTOK][VD]; decay, beta [NTOK]
static float *K, *QS, *V, *DEC, *BET;

// ---- reference: today's token loop on the standard layout S[row][col] ----
__attribute__((noinline)) static void token_chain(float *S, float *O) {
  for (int t = 0; t < NTOK; t++) {
    const float *k = K + t * KD, *qs = QS + t * KD, *v = V + t * VD;
    __m512 dv = _mm512_set1_ps(DEC[t]), bv = _mm512_set1_ps(BET[t]);
    __m512 r[NCH], delta[NCH], res[NCH];
    for (int c = 0; c < NCH; c++) r[c] = _mm512_setzero_ps();
    for (int i = 0; i < KD; i++) {
      __m512 kv = _mm512_set1_ps(k[i]);
      for (int c = 0; c < NCH; c++)
        r[c] = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(S + i * VD + c * 16), dv), r[c]);
    }
    for (int c = 0; c < NCH; c++) {
      delta[c] = _mm512_mul_ps(_mm512_sub_ps(_mm512_loadu_ps(v + c * 16), r[c]), bv);
      res[c] = _mm512_setzero_ps();
    }
    for (int i = 0; i < KD; i++) {
      __m512 kv = _mm512_set1_ps(k[i]), qv = _mm512_set1_ps(qs[i]);
      for (int c = 0; c < NCH; c++) {
        __m512 ns = _mm512_fmadd_ps(kv, delta[c], _mm512_mul_ps(_mm512_load_ps(S + i * VD + c * 16), dv));
        _mm512_store_ps(S + i * VD + c * 16, ns);
        res[c] = _mm512_fmadd_ps(qv, ns, res[c]);
      }
    }
    for (int c = 0; c < NCH; c++) _mm512_storeu_ps(O + t * VD + c * 16, res[c]);
  }
}

// ---- generic slice chain: W chunks per slice, ROWS key rows, row r chunk c at Sl[(r * rs + c * cs)] floats ----
// two passes per token, as today.
#define SLICE_CHAIN(NAME, W)                                                                                     \
  __attribute__((noinline)) static void NAME(float *Sl, size_t rs, size_t cs, int rows, int col0, float *O) {   \
    for (int t = 0; t < NTOK; t++) {                                                                             \
      const float *k = K + t * KD, *qs = QS + t * KD, *v = V + t * VD + col0;                                    \
      __m512 dv = _mm512_set1_ps(DEC[t]), bv = _mm512_set1_ps(BET[t]);                                           \
      __m512 r[W], d[W], o[W];                                                                                   \
      for (int c = 0; c < W; c++) r[c] = _mm512_setzero_ps();                                                    \
      for (int i = 0; i < rows; i++) {                                                                           \
        __m512 kv = _mm512_set1_ps(k[i]);                                                                        \
        for (int c = 0; c < W; c++)                                                                              \
          r[c] = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sl + i * rs + c * cs), dv), r[c]);             \
      }                                                                                                          \
      for (int c = 0; c < W; c++) {                                                                              \
        d[c] = _mm512_mul_ps(_mm512_sub_ps(_mm512_loadu_ps(v + c * 16), r[c]), bv);                              \
        o[c] = _mm512_setzero_ps();                                                                              \
      }                                                                                                          \
      for (int i = 0; i < rows; i++) {                                                                           \
        __m512 kv = _mm512_set1_ps(k[i]), qv = _mm512_set1_ps(qs[i]);                                            \
        for (int c = 0; c < W; c++) {                                                                            \
          __m512 n = _mm512_fmadd_ps(kv, d[c], _mm512_mul_ps(_mm512_load_ps(Sl + i * rs + c * cs), dv));         \
          _mm512_store_ps(Sl + i * rs + c * cs, n);                                                              \
          o[c] = _mm512_fmadd_ps(qv, n, o[c]);                                                                   \
        }                                                                                                        \
      }                                                                                                          \
      for (int c = 0; c < W; c++) _mm512_storeu_ps(O + t * VD + col0 + c * 16, o[c]);                            \
    }                                                                                                            \
  }
SLICE_CHAIN(slice4, 4)
SLICE_CHAIN(slice2, 2)
SLICE_CHAIN(slice8, 8)

// ---- fused chain: the write loop of token t also computes the read sum of token t + 1 ----
// Per lane the operations and their order are those of the token loop: the read sum of token t + 1 adds
// k[t+1][i] * (S_new[i] * decay[t+1]) for i = 0, 1, ... with one fma each. One load and one store per row and token.
#define FUSED_CHAIN(NAME, W)                                                                                     \
  __attribute__((noinline)) static void NAME(float *Sl, size_t rs, size_t cs, int rows, int col0, float *O) {   \
    __m512 r[W], d[W], o[W];                                                                                     \
    {                                                                                                            \
      const float *k = K;                                                                                        \
      __m512 dv = _mm512_set1_ps(DEC[0]);                                                                        \
      for (int c = 0; c < W; c++) r[c] = _mm512_setzero_ps();                                                    \
      for (int i = 0; i < rows; i++) {                                                                           \
        __m512 kv = _mm512_set1_ps(k[i]);                                                                        \
        for (int c = 0; c < W; c++)                                                                              \
          r[c] = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sl + i * rs + c * cs), dv), r[c]);             \
      }                                                                                                          \
    }                                                                                                            \
    for (int t = 0; t < NTOK; t++) {                                                                             \
      const float *k = K + t * KD, *qs = QS + t * KD, *v = V + t * VD + col0;                                    \
      int last = t + 1 == NTOK;                                                                                  \
      const float *kn = K + (last ? t : t + 1) * KD;                                                             \
      __m512 dv = _mm512_set1_ps(DEC[t]), bv = _mm512_set1_ps(BET[t]);                                           \
      __m512 dn = _mm512_set1_ps(DEC[last ? t : t + 1]);                                                         \
      __m512 rn[W];                                                                                              \
      for (int c = 0; c < W; c++) {                                                                              \
        d[c] = _mm512_mul_ps(_mm512_sub_ps(_mm512_loadu_ps(v + c * 16), r[c]), bv);                              \
        o[c] = _mm512_setzero_ps();                                                                              \
        rn[c] = _mm512_setzero_ps();                                                                             \
      }                                                                                                          \
      for (int i = 0; i < rows; i++) {                                                                           \
        __m512 kv = _mm512_set1_ps(k[i]), qv = _mm512_set1_ps(qs[i]), knv = _mm512_set1_ps(kn[i]);               \
        for (int c = 0; c < W; c++) {                                                                            \
          __m512 n = _mm512_fmadd_ps(kv, d[c], _mm512_mul_ps(_mm512_load_ps(Sl + i * rs + c * cs), dv));         \
          _mm512_store_ps(Sl + i * rs + c * cs, n);                                                              \
          o[c] = _mm512_fmadd_ps(qv, n, o[c]);                                                                   \
          rn[c] = _mm512_fmadd_ps(knv, _mm512_mul_ps(n, dn), rn[c]);                                             \
        }                                                                                                        \
      }                                                                                                          \
      for (int c = 0; c < W; c++) {                                                                              \
        _mm512_storeu_ps(O + t * VD + col0 + c * 16, o[c]);                                                      \
        r[c] = rn[c];                                                                                            \
      }                                                                                                          \
    }                                                                                                            \
  }
FUSED_CHAIN(fused4, 4)
FUSED_CHAIN(fused8, 8)
FUSED_CHAIN(fused2, 2)

// ---- single passes on a 4-chunk blocked slice, to time the read loop and the write loop apart ----
__attribute__((noinline)) static __m512 pass1_only(const float *Sl, int reps) {
  __m512 acc = _mm512_setzero_ps();
  for (int n = 0; n < reps; n++) {
    const float *k = K + (n % NTOK) * KD;
    __m512 dv = _mm512_set1_ps(DEC[n % NTOK]);
    __m512 r0 = _mm512_setzero_ps(), r1 = r0, r2 = r0, r3 = r0;
    for (int i = 0; i < KD; i++) {
      __m512 kv = _mm512_set1_ps(k[i]);
      r0 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sl + (0 * KD + i) * 16), dv), r0);
      r1 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sl + (1 * KD + i) * 16), dv), r1);
      r2 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sl + (2 * KD + i) * 16), dv), r2);
      r3 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sl + (3 * KD + i) * 16), dv), r3);
    }
    acc = _mm512_add_ps(acc, _mm512_add_ps(_mm512_add_ps(r0, r1), _mm512_add_ps(r2, r3)));
  }
  return acc;
}
__attribute__((noinline)) static __m512 pass2_only(float *Sl, int reps) {
  __m512 acc = _mm512_setzero_ps();
  for (int n = 0; n < reps; n++) {
    const float *k = K + (n % NTOK) * KD, *qs = QS + (n % NTOK) * KD;
    __m512 dv = _mm512_set1_ps(0.999f), d = _mm512_set1_ps(1e-4f);
    __m512 o0 = _mm512_setzero_ps(), o1 = o0, o2 = o0, o3 = o0;
    for (int i = 0; i < KD; i++) {
      __m512 kv = _mm512_set1_ps(k[i]), qv = _mm512_set1_ps(qs[i]);
      __m512 n0 = _mm512_fmadd_ps(kv, d, _mm512_mul_ps(_mm512_load_ps(Sl + (0 * KD + i) * 16), dv));
      __m512 n1 = _mm512_fmadd_ps(kv, d, _mm512_mul_ps(_mm512_load_ps(Sl + (1 * KD + i) * 16), dv));
      __m512 n2 = _mm512_fmadd_ps(kv, d, _mm512_mul_ps(_mm512_load_ps(Sl + (2 * KD + i) * 16), dv));
      __m512 n3 = _mm512_fmadd_ps(kv, d, _mm512_mul_ps(_mm512_load_ps(Sl + (3 * KD + i) * 16), dv));
      _mm512_store_ps(Sl + (0 * KD + i) * 16, n0);
      _mm512_store_ps(Sl + (1 * KD + i) * 16, n1);
      _mm512_store_ps(Sl + (2 * KD + i) * 16, n2);
      _mm512_store_ps(Sl + (3 * KD + i) * 16, n3);
      o0 = _mm512_fmadd_ps(qv, n0, o0);
      o1 = _mm512_fmadd_ps(qv, n1, o1);
      o2 = _mm512_fmadd_ps(qv, n2, o2);
      o3 = _mm512_fmadd_ps(qv, n3, o3);
    }
    acc = _mm512_add_ps(acc, _mm512_add_ps(_mm512_add_ps(o0, o1), _mm512_add_ps(o2, o3)));
  }
  return acc;
}
// independent FMAs with no memory operand: the port limit of this core for 512-bit FMA.
__attribute__((noinline)) static __m512 fma_port_limit(int reps) {
  __m512 a0 = _mm512_set1_ps(1.0f), a1 = a0, a2 = a0, a3 = a0, a4 = a0, a5 = a0, a6 = a0, a7 = a0;
  __m512 a8 = a0, a9 = a0, a10 = a0, a11 = a0;
  __m512 x = _mm512_set1_ps(0.9999999f), y = _mm512_set1_ps(1e-9f);
  for (int n = 0; n < reps; n++) {
    a0 = _mm512_fmadd_ps(a0, x, y);
    a1 = _mm512_fmadd_ps(a1, x, y);
    a2 = _mm512_fmadd_ps(a2, x, y);
    a3 = _mm512_fmadd_ps(a3, x, y);
    a4 = _mm512_fmadd_ps(a4, x, y);
    a5 = _mm512_fmadd_ps(a5, x, y);
    a6 = _mm512_fmadd_ps(a6, x, y);
    a7 = _mm512_fmadd_ps(a7, x, y);
    a8 = _mm512_fmadd_ps(a8, x, y);
    a9 = _mm512_fmadd_ps(a9, x, y);
    a10 = _mm512_fmadd_ps(a10, x, y);
    a11 = _mm512_fmadd_ps(a11, x, y);
  }
  return _mm512_add_ps(_mm512_add_ps(_mm512_add_ps(a0, a1), _mm512_add_ps(a2, a3)),
                       _mm512_add_ps(_mm512_add_ps(_mm512_add_ps(a4, a5), _mm512_add_ps(a6, a7)),
                                     _mm512_add_ps(_mm512_add_ps(a8, a9), _mm512_add_ps(a10, a11))));
}

// layouts of one value head
static void std_to_blocked(float *B, const float *S) {  // [chunk][row][16]
  for (int i = 0; i < KD; i++)
    for (int c = 0; c < NCH; c++) memcpy(B + ((size_t)c * KD + i) * 16, S + (size_t)i * VD + c * 16, 64);
}
static void blocked_to_std(float *S, const float *B) {
  for (int i = 0; i < KD; i++)
    for (int c = 0; c < NCH; c++) memcpy(S + (size_t)i * VD + c * 16, B + ((size_t)c * KD + i) * 16, 64);
}
// [slice][row][W chunks]: rows of a slice are contiguous
static void std_to_rows(float *R, const float *S, int W) {
  for (int s = 0; s < NCH / W; s++)
    for (int i = 0; i < KD; i++) memcpy(R + ((size_t)s * KD + i) * W * 16, S + (size_t)i * VD + s * W * 16, (size_t)W * 64);
}
static void rows_to_std(float *S, const float *R, int W) {
  for (int s = 0; s < NCH / W; s++)
    for (int i = 0; i < KD; i++) memcpy(S + (size_t)i * VD + s * W * 16, R + ((size_t)s * KD + i) * W * 16, (size_t)W * 64);
}

typedef struct {
  const char *label;
  double ns;
  int same;
} row_t;
static row_t rows[40];
static int n_rows;
static int add(const char *label) {
  rows[n_rows].label = label;
  rows[n_rows].ns = 1e30;
  rows[n_rows].same = -1;
  return n_rows++;
}
static void upd(int r, double ns) {
  if (ns < rows[r].ns) rows[r].ns = ns;
}

int main(int argc, char **argv) {
  int cpu = argc > 1 ? atoi(argv[1]) : -1;
  double ghz = argc > 2 ? atof(argv[2]) : 2.70;
  if (cpu >= 0) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    sched_setaffinity(0, sizeof(set), &set);
  }
  const float scale = (float)(1.0 / sqrt(128.0));
  K = alloc_f(NTOK * KD);
  QS = alloc_f(NTOK * KD);
  V = alloc_f(NTOK * VD);
  DEC = alloc_f(NTOK);
  BET = alloc_f(NTOK);
  for (int t = 0; t < NTOK; t++) {
    float kk[KD], qq[KD];
    double nk = 0, nq = 0;
    for (int i = 0; i < KD; i++) {
      kk[i] = (float)(urand() * 2 - 1);
      qq[i] = (float)(urand() * 2 - 1);
      nk += kk[i] * kk[i];
      nq += qq[i] * qq[i];
    }
    for (int i = 0; i < KD; i++) {
      K[t * KD + i] = bf16_round((float)(kk[i] / sqrt(nk)));
      QS[t * KD + i] = bf16_round((float)(qq[i] / sqrt(nq))) * scale;
    }
    for (int c = 0; c < VD; c++) V[t * VD + c] = bf16_round((float)(urand() * 2 - 1));
    DEC[t] = (float)(0.9 + 0.1 * urand());
    BET[t] = bf16_round((float)(0.3 + 0.4 * urand()));
  }
  float *S0 = alloc_f(KD * VD), *Sref = alloc_f(KD * VD), *Sw = alloc_f(KD * VD), *Sback = alloc_f(KD * VD);
  float *Oref = alloc_f(NTOK * VD), *O = alloc_f(NTOK * VD);
  for (int i = 0; i < KD * VD; i++) S0[i] = (float)(0.02 * (urand() * 2 - 1));

  int r_tok = add("token loop today, standard layout, 8 chunks per row (64 KiB)");
  int r_b4 = add("two passes, blocked layout [chunk][row], 4 chunks per slice (32 KiB)");
  int r_r4 = add("two passes, row layout [row][4 chunks], 4 chunks per slice (32 KiB)");
  int r_b2 = add("two passes, blocked layout, 2 chunks per slice (16 KiB)");
  int r_r2 = add("two passes, row layout [row][2 chunks], 2 chunks per slice (16 KiB)");
  int r_s8 = add("two passes, standard layout, 8 chunks = the token loop as a chain function");
  int r_f4b = add("fused passes, blocked layout, 4 chunks per slice (32 KiB)");
  int r_f4r = add("fused passes, row layout, 4 chunks per slice (32 KiB)");
  int r_f2r = add("fused passes, row layout, 2 chunks per slice (16 KiB)");
  int r_f8 = add("fused passes, standard layout, 8 chunks per row (64 KiB)");
  int r_p1 = add("read loop only, 4-chunk blocked slice in L1 (x2 slices = per value head)");
  int r_p2 = add("write loop only, 4-chunk blocked slice in L1 (x2 slices = per value head)");
  int r_p1s = add("read loop only, 4 chunks x 16 rows (4 KiB), 8 repeats per token-slice");
  int r_fma = add("12 independent FMAs per iteration, no memory operand: ns per FMA");

  for (int round = 0; round < 40; round++) {
    uint64_t t0, t1;
    memcpy(Sref, S0, KD * VD * 4);
    t0 = now_ns();
    token_chain(Sref, Oref);
    t1 = now_ns();
    upd(r_tok, (double)(t1 - t0) / NTOK);

#define CHECK(r, Sstd)                                                                                           \
  if (round == 0) rows[r].same = !memcmp(O, Oref, NTOK * VD * 4) && !memcmp(Sstd, Sref, KD * VD * 4);
    // blocked 4
    std_to_blocked(Sw, S0);
    t0 = now_ns();
    for (int s = 0; s < 2; s++) slice4(Sw + (size_t)s * 4 * KD * 16, 16, (size_t)KD * 16, KD, s * 64, O);
    t1 = now_ns();
    upd(r_b4, (double)(t1 - t0) / NTOK);
    blocked_to_std(Sback, Sw);
    CHECK(r_b4, Sback);
    // row layout 4
    std_to_rows(Sw, S0, 4);
    t0 = now_ns();
    for (int s = 0; s < 2; s++) slice4(Sw + (size_t)s * KD * 64, 64, 16, KD, s * 64, O);
    t1 = now_ns();
    upd(r_r4, (double)(t1 - t0) / NTOK);
    rows_to_std(Sback, Sw, 4);
    CHECK(r_r4, Sback);
    // blocked 2
    std_to_blocked(Sw, S0);
    t0 = now_ns();
    for (int s = 0; s < 4; s++) slice2(Sw + (size_t)s * 2 * KD * 16, 16, (size_t)KD * 16, KD, s * 32, O);
    t1 = now_ns();
    upd(r_b2, (double)(t1 - t0) / NTOK);
    blocked_to_std(Sback, Sw);
    CHECK(r_b2, Sback);
    // row layout 2
    std_to_rows(Sw, S0, 2);
    t0 = now_ns();
    for (int s = 0; s < 4; s++) slice2(Sw + (size_t)s * KD * 32, 32, 16, KD, s * 32, O);
    t1 = now_ns();
    upd(r_r2, (double)(t1 - t0) / NTOK);
    rows_to_std(Sback, Sw, 2);
    CHECK(r_r2, Sback);
    // standard 8
    memcpy(Sw, S0, KD * VD * 4);
    t0 = now_ns();
    slice8(Sw, VD, 16, KD, 0, O);
    t1 = now_ns();
    upd(r_s8, (double)(t1 - t0) / NTOK);
    CHECK(r_s8, Sw);
    // fused 4 blocked
    std_to_blocked(Sw, S0);
    t0 = now_ns();
    for (int s = 0; s < 2; s++) fused4(Sw + (size_t)s * 4 * KD * 16, 16, (size_t)KD * 16, KD, s * 64, O);
    t1 = now_ns();
    upd(r_f4b, (double)(t1 - t0) / NTOK);
    blocked_to_std(Sback, Sw);
    CHECK(r_f4b, Sback);
    // fused 4 rows
    std_to_rows(Sw, S0, 4);
    t0 = now_ns();
    for (int s = 0; s < 2; s++) fused4(Sw + (size_t)s * KD * 64, 64, 16, KD, s * 64, O);
    t1 = now_ns();
    upd(r_f4r, (double)(t1 - t0) / NTOK);
    rows_to_std(Sback, Sw, 4);
    CHECK(r_f4r, Sback);
    // fused 2 rows
    std_to_rows(Sw, S0, 2);
    t0 = now_ns();
    for (int s = 0; s < 4; s++) fused2(Sw + (size_t)s * KD * 32, 32, 16, KD, s * 32, O);
    t1 = now_ns();
    upd(r_f2r, (double)(t1 - t0) / NTOK);
    rows_to_std(Sback, Sw, 2);
    CHECK(r_f2r, Sback);
    // fused 8 standard
    memcpy(Sw, S0, KD * VD * 4);
    t0 = now_ns();
    fused8(Sw, VD, 16, KD, 0, O);
    t1 = now_ns();
    upd(r_f8, (double)(t1 - t0) / NTOK);
    CHECK(r_f8, Sw);
    // single passes
    volatile float sink = 0;
    std_to_blocked(Sw, S0);
    t0 = now_ns();
    sink += _mm512_reduce_add_ps(pass1_only(Sw, 256));
    t1 = now_ns();
    upd(r_p1, 2.0 * (double)(t1 - t0) / 256);
    for (int i = 0; i < 4 * KD * 16; i++) Sw[i] = 0.01f;
    t0 = now_ns();
    sink += _mm512_reduce_add_ps(pass2_only(Sw, 256));
    t1 = now_ns();
    upd(r_p2, 2.0 * (double)(t1 - t0) / 256);
    {
      // 16 rows only: the 4 streams are 128 rows apart, so use rows 0..15 of each stream
      __m512 acc = _mm512_setzero_ps();
      t0 = now_ns();
      for (int n = 0; n < 256 * 8; n++) {
        const float *k = K + (n % NTOK) * KD;
        __m512 dv = _mm512_set1_ps(DEC[n % NTOK]);
        __m512 r0 = _mm512_setzero_ps(), r1 = r0, r2 = r0, r3 = r0;
        for (int i = 0; i < 16; i++) {
          __m512 kv = _mm512_set1_ps(k[i]);
          r0 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sw + (0 * 16 + i) * 16), dv), r0);
          r1 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sw + (1 * 16 + i) * 16), dv), r1);
          r2 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sw + (2 * 16 + i) * 16), dv), r2);
          r3 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(Sw + (3 * 16 + i) * 16), dv), r3);
        }
        acc = _mm512_add_ps(acc, _mm512_add_ps(_mm512_add_ps(r0, r1), _mm512_add_ps(r2, r3)));
      }
      t1 = now_ns();
      sink += _mm512_reduce_add_ps(acc);
      upd(r_p1s, 2.0 * (double)(t1 - t0) / 256);
    }
    t0 = now_ns();
    sink += _mm512_reduce_add_ps(fma_port_limit(2000000));
    t1 = now_ns();
    upd(r_fma, (double)(t1 - t0) / (2000000.0 * 12));
  }
  char hn[64] = "?";
  gethostname(hn, sizeof hn);
  printf("host %s cpu %d; cycles = ns x %.2f GHz (assumed core clock); lowest of 40 rounds\n", hn, cpu, ghz);
  printf("%-82s %9s %8s %8s  %s\n", "variant (one value head, per token)", "ns", "cycles", "ops/cyc", "bits vs token loop");
  for (int i = 0; i < n_rows; i++) {
    double cyc = rows[i].ns * ghz;
    double ops = i == r_fma ? 1 : (i == r_p1 || i == r_p1s ? 2048 : (i == r_p2 ? 3072 : 5120));
    printf("%-82s %9.2f %8.1f %8.2f  %s\n", rows[i].label, rows[i].ns, cyc, ops / cyc,
           rows[i].same < 0 ? "-" : (rows[i].same ? "IDENTICAL" : "DIFFER"));
  }
  return 0;
}
