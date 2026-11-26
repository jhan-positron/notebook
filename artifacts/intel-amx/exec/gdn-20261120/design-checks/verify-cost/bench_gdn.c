// Verifier (cost lens): stand-alone AVX-512 timing of the GDN recurrence loops.
// NOT tron code. A re-implementation of gated_delta_net.hpp:259-297 (token loop),
// of the proposed column-slice replay (G1), and of the AVX-512 parts of the
// proposed AMX block kernel (G2: 3-piece split + pack, triangle).
//
// Host: the design host (KVM guest on an AMD Ryzen 9 9950X, Zen 5), NOT the
// Xeon 6962P. Zen 5 has two 512-bit FMA/multiply pipes (FMA latency 4 cycles),
// L1d 48 KiB / 12 ways, L2 1 MiB. Results are indicative only.
//
// Build: gcc -O3 -march=native -o bench_gdn bench_gdn.c -lm
#define _GNU_SOURCE
#include <immintrin.h>
#include <math.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define KD 128  // key rows
#define VD 128  // value columns
#define NCH 8   // zmm chunks per state row

static inline uint64_t now_ns(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
  return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

// ---- core clock calibration: dependent chains with known latency (cross-checked in calib.c) ----
// The host is a shared KVM guest: the clock moves between about 1.5 and 5.3 GHz.
// Rule used: clock = the highest reading of the whole run; time = the lowest time of
// many interleaved repetitions. Both extremes occur when the core is undisturbed.
static double g_ghz = 0;
static void calib_tick(void) {
  const long N = 1500000;
  uint64_t x = 3;
  uint64_t t0 = now_ns();
  for (long i = 0; i < N; i++) __asm__ volatile("imul %1,%0" : "+r"(x) : "r"(0x9E3779B97F4A7C15ull));
  uint64_t t1 = now_ns();
  double g = 3.0 * (double)N / (double)(t1 - t0);
  if (g > g_ghz) g_ghz = g;
  __m128d a = _mm_set_sd(1.0), b = _mm_set_sd(1.0000001), c = _mm_set_sd(1e-9);
  t0 = now_ns();
  for (long i = 0; i < N; i++) __asm__ volatile("vfmadd213sd %2,%1,%0" : "+x"(a) : "x"(b), "x"(c));
  t1 = now_ns();
  g = 4.0 * (double)N / (double)(t1 - t0);
  if (g > g_ghz) g_ghz = g;
}

// ---- deterministic inputs ----
static uint64_t rng_state = 0x243F6A8885A308D3ull;
static inline double urand(void) {
  rng_state ^= rng_state << 13;
  rng_state ^= rng_state >> 7;
  rng_state ^= rng_state << 17;
  return (double)(rng_state >> 11) / 9007199254740992.0;
}
static inline float bf16_round(float x) {  // round to nearest even on FP32 bits (normal values)
  uint32_t b;
  memcpy(&b, &x, 4);
  b = (b + 0x7fff + ((b >> 16) & 1)) & 0xffff0000u;
  memcpy(&x, &b, 4);
  return x;
}

// ---- today's token loop (gated_delta_net.hpp:266-297), standard layout S[i][c] ----
__attribute__((noinline)) static void token_step(float *S, const float *k, const float *qs,
                                                 const float *v, float decay, float beta, float *o) {
  __m512 dv = _mm512_set1_ps(decay), bv = _mm512_set1_ps(beta);
  __m512 r[NCH];
  for (int c = 0; c < NCH; c++) r[c] = _mm512_setzero_ps();
  for (int i = 0; i < KD; i++) {
    __m512 kv = _mm512_set1_ps(k[i]);
    for (int c = 0; c < NCH; c++) {
      __m512 ds = _mm512_mul_ps(_mm512_load_ps(S + i * VD + c * 16), dv);
      r[c] = _mm512_fmadd_ps(kv, ds, r[c]);
    }
  }
  __m512 delta[NCH], res[NCH];
  for (int c = 0; c < NCH; c++) {
    delta[c] = _mm512_mul_ps(_mm512_sub_ps(_mm512_loadu_ps(v + c * 16), r[c]), bv);
    res[c] = _mm512_setzero_ps();
  }
  for (int i = 0; i < KD; i++) {
    __m512 kv = _mm512_set1_ps(k[i]);
    __m512 qv = _mm512_set1_ps(qs[i]);
    for (int c = 0; c < NCH; c++) {
      __m512 ns = _mm512_fmadd_ps(kv, delta[c], _mm512_mul_ps(_mm512_load_ps(S + i * VD + c * 16), dv));
      _mm512_store_ps(S + i * VD + c * 16, ns);
      res[c] = _mm512_fmadd_ps(qv, ns, res[c]);
    }
  }
  for (int c = 0; c < NCH; c++) _mm512_storeu_ps(o + c * 16, res[c]);
}

// ---- G1 slice replay: same operations per column, 4 chunks (64 columns) at a time ----
// Sl points at the slice: rows of `stride` floats, 4 consecutive chunks used.
// blocked layout: slice = [4 value blocks][128 rows][16] -> chunk c of row i at Sl + (c*KD + i)*16
// standard layout: chunk c of row i at Sl + i*VD + c*16
static inline __attribute__((always_inline)) void slice_step(float *Sl, int blocked, const float *k,
                                                             const float *qs, const float *v, float decay,
                                                             float beta, float *o) {
  __m512 dv = _mm512_set1_ps(decay), bv = _mm512_set1_ps(beta);
  __m512 r0 = _mm512_setzero_ps(), r1 = r0, r2 = r0, r3 = r0;
#define SP(i, c) (blocked ? (Sl + ((c) * KD + (i)) * 16) : (Sl + (i) * VD + (c) * 16))
  for (int i = 0; i < KD; i++) {
    __m512 kv = _mm512_set1_ps(k[i]);
    r0 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(SP(i, 0)), dv), r0);
    r1 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(SP(i, 1)), dv), r1);
    r2 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(SP(i, 2)), dv), r2);
    r3 = _mm512_fmadd_ps(kv, _mm512_mul_ps(_mm512_load_ps(SP(i, 3)), dv), r3);
  }
  __m512 d0 = _mm512_mul_ps(_mm512_sub_ps(_mm512_loadu_ps(v + 0), r0), bv);
  __m512 d1 = _mm512_mul_ps(_mm512_sub_ps(_mm512_loadu_ps(v + 16), r1), bv);
  __m512 d2 = _mm512_mul_ps(_mm512_sub_ps(_mm512_loadu_ps(v + 32), r2), bv);
  __m512 d3 = _mm512_mul_ps(_mm512_sub_ps(_mm512_loadu_ps(v + 48), r3), bv);
  __m512 o0 = _mm512_setzero_ps(), o1 = o0, o2 = o0, o3 = o0;
  for (int i = 0; i < KD; i++) {
    __m512 kv = _mm512_set1_ps(k[i]);
    __m512 qv = _mm512_set1_ps(qs[i]);
    __m512 n0 = _mm512_fmadd_ps(kv, d0, _mm512_mul_ps(_mm512_load_ps(SP(i, 0)), dv));
    __m512 n1 = _mm512_fmadd_ps(kv, d1, _mm512_mul_ps(_mm512_load_ps(SP(i, 1)), dv));
    __m512 n2 = _mm512_fmadd_ps(kv, d2, _mm512_mul_ps(_mm512_load_ps(SP(i, 2)), dv));
    __m512 n3 = _mm512_fmadd_ps(kv, d3, _mm512_mul_ps(_mm512_load_ps(SP(i, 3)), dv));
    _mm512_store_ps(SP(i, 0), n0);
    _mm512_store_ps(SP(i, 1), n1);
    _mm512_store_ps(SP(i, 2), n2);
    _mm512_store_ps(SP(i, 3), n3);
    o0 = _mm512_fmadd_ps(qv, n0, o0);
    o1 = _mm512_fmadd_ps(qv, n1, o1);
    o2 = _mm512_fmadd_ps(qv, n2, o2);
    o3 = _mm512_fmadd_ps(qv, n3, o3);
  }
#undef SP
  _mm512_storeu_ps(o + 0, o0);
  _mm512_storeu_ps(o + 16, o1);
  _mm512_storeu_ps(o + 32, o2);
  _mm512_storeu_ps(o + 48, o3);
}
__attribute__((noinline)) static void slice_window(float *Sl, int blocked, int ntok, const float *K,
                                                   const float *QS, const float *V, const float *decay,
                                                   const float *beta, float *O, int col0) {
  // K, QS: [ntok][128]; V, O: [ntok][128] for this value head; col0 = first column of the slice
  for (int t = 0; t < ntok; t++)
    slice_step(Sl, blocked, K + t * KD, QS + t * KD, V + t * VD + col0, decay[t], beta[t], O + t * VD + col0);
}

// ---- prelude of one value head (normalize q or k once, decay, beta, value rounding) ----
static inline __m512 round_bf16_chunk(__m512 x) {
  __m256bh h = _mm512_cvtneps_pbh(x);
  return _mm512_castsi512_ps(_mm512_slli_epi32(_mm512_cvtepu16_epi32((__m256i)h), 16));
}
__attribute__((noinline)) static void normalize_gdn(const float *in, float *out) {
  __m512 sq = _mm512_setzero_ps();
  for (int c = 0; c < 8; c++) {
    __m512 x = round_bf16_chunk(_mm512_loadu_ps(in + c * 16));
    _mm512_storeu_ps(out + c * 16, x);
    sq = _mm512_add_ps(sq, round_bf16_chunk(_mm512_mul_ps(x, x)));
  }
  float quad = bf16_round(_mm512_reduce_add_ps(sq));
  float nsq = bf16_round(quad + bf16_round(1e-6f));
  __m512 inv = _mm512_set1_ps(bf16_round(1.0f / sqrtf(nsq)));
  for (int c = 0; c < 8; c++)
    _mm512_storeu_ps(out + c * 16, round_bf16_chunk(_mm512_mul_ps(_mm512_loadu_ps(out + c * 16), inv)));
}
__attribute__((noinline)) static float decay_of(float a, float A_exp, float dt_bias) {
  float x = bf16_round(a) + dt_bias;
  float sp = x > 20.0f ? x : log1pf(expf(x));
  return expf(-A_exp * sp);
}
__attribute__((noinline)) static float beta_of(float b) {
  return bf16_round(1.0f / (expf(-bf16_round(b)) + 1.0f));
}

// ---- G2 AVX-512 parts ----
// 3-piece truncation split + pair-interleaved pack of one value block (128 rows x 16 columns,
// blocked layout = 128 consecutive lines) into a 12 KiB scratch [key block 4][piece 3][16 rows][64 B].
__attribute__((noinline)) static __m512 split_pack_block(const float *Sb, uint8_t *scratch) {
  const __m512i M = _mm512_set1_epi32((int)0xffff0000u);
  __m512 guard = _mm512_setzero_ps(), zero = _mm512_setzero_ps();
  for (int j = 0; j < 64; j++) {
    __m512 xe = _mm512_load_ps(Sb + (2 * j) * 16), xo = _mm512_load_ps(Sb + (2 * j + 1) * 16);
    guard = _mm512_fmadd_ps(xe, zero, guard);
    guard = _mm512_fmadd_ps(xo, zero, guard);
    __m512 he = _mm512_castsi512_ps(_mm512_and_si512(_mm512_castps_si512(xe), M));
    __m512 ho = _mm512_castsi512_ps(_mm512_and_si512(_mm512_castps_si512(xo), M));
    __m512 re = _mm512_sub_ps(xe, he), ro = _mm512_sub_ps(xo, ho);
    __m512 me = _mm512_castsi512_ps(_mm512_and_si512(_mm512_castps_si512(re), M));
    __m512 mo = _mm512_castsi512_ps(_mm512_and_si512(_mm512_castps_si512(ro), M));
    __m512 le = _mm512_sub_ps(re, me), lo = _mm512_sub_ps(ro, mo);
    int kb = j / 16, row = j % 16;
    uint8_t *base = scratch + (size_t)kb * 3 * 1024 + (size_t)row * 64;
    _mm512_store_si512(base + 0 * 1024,
                       _mm512_or_si512(_mm512_srli_epi32(_mm512_castps_si512(le), 16), _mm512_castps_si512(lo)));
    _mm512_store_si512(base + 1 * 1024,
                       _mm512_or_si512(_mm512_srli_epi32(_mm512_castps_si512(me), 16), _mm512_castps_si512(mo)));
    _mm512_store_si512(base + 2 * 1024,
                       _mm512_or_si512(_mm512_srli_epi32(_mm512_castps_si512(he), 16), _mm512_castps_si512(ho)));
  }
  return guard;
}

// triangle of block_algorithm step 4, C tokens, 128 value columns.
__attribute__((noinline)) static void triangle(int C, const float *R0, const float *U0, const float *CK,
                                               const float *CQ, const float *gamma, const float *sg,
                                               const float *V, const float *beta, float *Delta, float *O) {
  for (int t = 0; t < C; t++) {
    __m512 g = _mm512_set1_ps(gamma[t]), s = _mm512_set1_ps(sg[t]), b = _mm512_set1_ps(beta[t]);
    __m512 r[8], o[8];
    for (int c = 0; c < 8; c++) {
      r[c] = _mm512_mul_ps(g, _mm512_load_ps(R0 + t * VD + c * 16));
      o[c] = _mm512_mul_ps(s, _mm512_load_ps(U0 + t * VD + c * 16));
    }
    for (int u = 0; u < t; u++) {
      __m512 ck = _mm512_set1_ps(CK[t * C + u]), cq = _mm512_set1_ps(CQ[t * C + u]);
      for (int c = 0; c < 8; c++) {
        __m512 d = _mm512_load_ps(Delta + u * VD + c * 16);
        r[c] = _mm512_fmadd_ps(ck, d, r[c]);
        o[c] = _mm512_fmadd_ps(cq, d, o[c]);
      }
    }
    __m512 cq = _mm512_set1_ps(CQ[t * C + t]);
    for (int c = 0; c < 8; c++) {
      __m512 d = _mm512_mul_ps(_mm512_sub_ps(_mm512_load_ps(V + t * VD + c * 16), r[c]), b);
      _mm512_store_ps(Delta + t * VD + c * 16, d);
      _mm512_store_ps(O + t * VD + c * 16, _mm512_fmadd_ps(cq, d, o[c]));
    }
  }
}

static float *alloc_f(size_t n) {
  float *p = aligned_alloc(4096, ((n * sizeof(float)) + 4095) / 4096 * 4096);
  if (!p) abort();
  memset(p, 0, n * sizeof(float));
  return p;
}

#define POOL 128  // tokens in the input pool (one prefill chain)

typedef struct {
  char label[112];
  double ns;       // lowest time per token per value head (or per item)
  double ops;      // zmm operations per item (0 = not applicable)
  char note[160];
} row_t;
static row_t rows[64];
static int n_rows = 0;
static int add_row(const char *label, double ops) {
  snprintf(rows[n_rows].label, sizeof rows[n_rows].label, "%s", label);
  rows[n_rows].ns = 1e30;
  rows[n_rows].ops = ops;
  rows[n_rows].note[0] = 0;
  return n_rows++;
}
static inline void upd(int r, double ns) {
  if (ns < rows[r].ns) rows[r].ns = ns;
}

static void to_blocked(float *Sblk, const float *Sstd, int H) {
  for (int h = 0; h < H; h++)
    for (int i = 0; i < KD; i++)
      for (int c = 0; c < NCH; c++)
        _mm512_store_ps(Sblk + ((size_t)h * NCH * KD + (size_t)c * KD + i) * 16,
                        _mm512_load_ps(Sstd + ((size_t)h * KD + i) * VD + c * 16));
}
static void to_standard(float *Sstd, const float *Sblk, int H) {
  for (int h = 0; h < H; h++)
    for (int i = 0; i < KD; i++)
      for (int c = 0; c < NCH; c++)
        _mm512_store_ps(Sstd + ((size_t)h * KD + i) * VD + c * 16,
                        _mm512_load_ps(Sblk + ((size_t)h * NCH * KD + (size_t)c * KD + i) * 16));
}

int main(int argc, char **argv) {
  int cpu = argc > 1 ? atoi(argv[1]) : -1;
  int rounds_scale = argc > 2 ? atoi(argv[2]) : 1;
  if (cpu >= 0) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    sched_setaffinity(0, sizeof(set), &set);
  }
  for (int i = 0; i < 20; i++) calib_tick();

  const float scale = (float)(1.0 / sqrt(128.0));
  enum { MAXH = 32 };
  float *K = alloc_f((size_t)POOL * (MAXH / 2) * KD), *QS = alloc_f((size_t)POOL * (MAXH / 2) * KD);
  float *V = alloc_f((size_t)POOL * MAXH * VD), *O = alloc_f((size_t)POOL * MAXH * VD);
  float *DEC = alloc_f((size_t)POOL * MAXH), *BET = alloc_f((size_t)POOL * MAXH);
  for (int t = 0; t < POOL; t++) {
    for (int kh = 0; kh < MAXH / 2; kh++) {
      float kk[KD], qq[KD];
      double nk = 0, nq = 0;
      for (int i = 0; i < KD; i++) {
        kk[i] = (float)(urand() * 2 - 1);
        qq[i] = (float)(urand() * 2 - 1);
        nk += kk[i] * kk[i];
        nq += qq[i] * qq[i];
      }
      for (int i = 0; i < KD; i++) {
        K[((size_t)t * (MAXH / 2) + kh) * KD + i] = bf16_round((float)(kk[i] / sqrt(nk)));
        QS[((size_t)t * (MAXH / 2) + kh) * KD + i] = bf16_round((float)(qq[i] / sqrt(nq))) * scale;
      }
    }
    for (int h = 0; h < MAXH; h++) {
      for (int c = 0; c < VD; c++) V[((size_t)t * MAXH + h) * VD + c] = bf16_round((float)(urand() * 2 - 1));
      DEC[t * MAXH + h] = (float)(0.9 + 0.1 * urand());
      BET[t * MAXH + h] = bf16_round((float)(0.3 + 0.4 * urand()));
    }
  }

  // ---------- (1) today's token loop, H value heads x 64 KiB, all stepped per token ----------
  int Hs[] = {1, 2, 8, 16, 32};
  enum { NH = 5 };
  float *Sm[NH];
  int r1[NH];
  for (int hi = 0; hi < NH; hi++) {
    int H = Hs[hi];
    Sm[hi] = alloc_f((size_t)H * KD * VD);
    for (size_t i = 0; i < (size_t)H * KD * VD; i++) Sm[hi][i] = (float)(0.02 * (urand() * 2 - 1));
    char label[112];
    snprintf(label, sizeof label, "(1) token loop today, %2d value heads cycled = %4d KiB of state", H, H * 64);
    r1[hi] = add_row(label, 5120);
  }
  for (int round = 0; round < 40 * rounds_scale; round++) {
    calib_tick();
    for (int hi = 0; hi < NH; hi++) {
      int H = Hs[hi];
      float *S = Sm[hi];
      uint64_t t0 = now_ns();
      for (int t = 0; t < POOL; t++)
        for (int h = 0; h < H; h++)
          token_step(S + (size_t)h * KD * VD, K + ((size_t)t * (MAXH / 2) + h / 2) * KD,
                     QS + ((size_t)t * (MAXH / 2) + h / 2) * KD, V + ((size_t)t * MAXH + h) * VD,
                     DEC[t * MAXH + h], BET[t * MAXH + h], O + ((size_t)t * MAXH + h) * VD);
      uint64_t t1 = now_ns();
      upd(r1[hi], (double)(t1 - t0) / (POOL * (double)H));
    }
  }
  for (int hi = 0; hi < NH; hi++) {
    float mn = 1e30f, mx = 0;
    int bad = 0;
    for (size_t i = 0; i < (size_t)Hs[hi] * KD * VD; i++) {
      float a = fabsf(Sm[hi][i]);
      if (!(a < 1e30f)) bad++;
      if (a != 0 && a < mn) mn = a;
      if (a > mx) mx = a;
    }
    snprintf(rows[r1[hi]].note, sizeof rows[0].note, "|S| in [%.1e, %.1e], %d non-finite", mn, mx, bad);
  }

  // ---------- (2) one key-head group: 2 value heads = 128 KiB working copy, chain of POOL tokens ----------
  enum { H = 2 };
  float *S0 = alloc_f((size_t)H * KD * VD);
  for (size_t i = 0; i < (size_t)H * KD * VD; i++) S0[i] = (float)(0.02 * (urand() * 2 - 1));
  float *Sstd = alloc_f((size_t)H * KD * VD), *Sblk = alloc_f((size_t)H * KD * VD), *Sref = alloc_f((size_t)H * KD * VD);
  float *Oref = alloc_f((size_t)POOL * H * VD);
  float *k1 = alloc_f((size_t)POOL * KD), *q1 = alloc_f((size_t)POOL * KD);
  float *v1 = alloc_f((size_t)POOL * H * VD), *dec1 = alloc_f((size_t)POOL * H), *bet1 = alloc_f((size_t)POOL * H);
  float *vh[H], *oh[H], *dh[H], *bh[H];
  for (int h = 0; h < H; h++) {
    vh[h] = alloc_f((size_t)POOL * VD);
    oh[h] = alloc_f((size_t)POOL * VD);
    dh[h] = alloc_f(POOL);
    bh[h] = alloc_f(POOL);
  }
  for (int t = 0; t < POOL; t++) {
    memcpy(k1 + t * KD, K + (size_t)t * (MAXH / 2) * KD, KD * 4);
    memcpy(q1 + t * KD, QS + (size_t)t * (MAXH / 2) * KD, KD * 4);
    for (int h = 0; h < H; h++) {
      memcpy(v1 + ((size_t)t * H + h) * VD, V + ((size_t)t * MAXH + h) * VD, VD * 4);
      memcpy(vh[h] + t * VD, V + ((size_t)t * MAXH + h) * VD, VD * 4);
      dec1[t * H + h] = dh[h][t] = DEC[t * MAXH + h];
      bet1[t * H + h] = bh[h][t] = BET[t * MAXH + h];
    }
  }
  int r_tok = add_row("(2) token loop today, one key-head group (128 KiB working copy)", 5120);
  int r_sl[2][3];
  int windows[3] = {32, 128, 8};
  for (int layout = 0; layout < 2; layout++)
    for (int wi = 0; wi < 3; wi++) {
      char label[112];
      snprintf(label, sizeof label, "(2) slice replay G1, %s layout, window %3d tokens", layout ? "blocked " : "standard", windows[wi]);
      r_sl[layout][wi] = add_row(label, 5120);
    }
  int r_l1 = add_row("(2) one 32 KiB slice held in L1 for the chain (x2 = one value head)", 5120);
  int r_conv = add_row("(2) layout conversion in + out, 2 x 128 KiB, per token per value head at 128 tokens", 0);
  int same[2][3] = {{1, 1, 1}, {1, 1, 1}};
  for (int round = 0; round < 60 * rounds_scale; round++) {
    calib_tick();
    memcpy(Sref, S0, (size_t)H * KD * VD * 4);
    uint64_t t0 = now_ns();
    for (int t = 0; t < POOL; t++)
      for (int h = 0; h < H; h++)
        token_step(Sref + (size_t)h * KD * VD, k1 + t * KD, q1 + t * KD, v1 + ((size_t)t * H + h) * VD, dec1[t * H + h],
                   bet1[t * H + h], Oref + ((size_t)t * H + h) * VD);
    uint64_t t1 = now_ns();
    upd(r_tok, (double)(t1 - t0) / (POOL * (double)H));
    for (int layout = 0; layout < 2; layout++)
      for (int wi = 0; wi < 3; wi++) {
        int W = windows[wi];
        float *Swork = layout ? Sblk : Sstd;
        if (layout)
          to_blocked(Sblk, S0, H);
        else
          memcpy(Sstd, S0, (size_t)H * KD * VD * 4);
        t0 = now_ns();
        for (int w0 = 0; w0 < POOL; w0 += W)
          for (int h = 0; h < H; h++)
            for (int s = 0; s < 2; s++) {
              float *Sl = layout ? Swork + ((size_t)h * NCH * KD + (size_t)(4 * s) * KD) * 16
                                 : Swork + (size_t)h * KD * VD + s * 64;
              slice_window(Sl, layout, W, k1 + w0 * KD, q1 + w0 * KD, vh[h] + w0 * VD, dh[h] + w0, bh[h] + w0,
                           oh[h] + w0 * VD, s * 64);
            }
        t1 = now_ns();
        upd(r_sl[layout][wi], (double)(t1 - t0) / (POOL * (double)H));
        if (round == 0) {  // bit identity against the token loop: outputs and final state
          for (int h = 0; h < H; h++) {
            for (int t = 0; t < POOL; t++)
              if (memcmp(oh[h] + t * VD, Oref + ((size_t)t * H + h) * VD, VD * 4)) same[layout][wi] = 0;
            for (int i = 0; i < KD; i++)
              for (int c = 0; c < NCH; c++) {
                const float *a = layout ? Sblk + ((size_t)h * NCH * KD + (size_t)c * KD + i) * 16
                                        : Sstd + ((size_t)h * KD + i) * VD + c * 16;
                if (memcmp(a, Sref + ((size_t)h * KD + i) * VD + c * 16, 64)) same[layout][wi] = 0;
              }
          }
        }
      }
    to_blocked(Sblk, S0, H);
    t0 = now_ns();
    slice_window(Sblk, 1, POOL, k1, q1, vh[0], dh[0], bh[0], oh[0], 0);
    t1 = now_ns();
    upd(r_l1, 2.0 * (double)(t1 - t0) / POOL);
    t0 = now_ns();
    to_blocked(Sblk, S0, H);
    to_standard(Sstd, Sblk, H);
    t1 = now_ns();
    upd(r_conv, (double)(t1 - t0) / (POOL * (double)H));
  }
  for (int layout = 0; layout < 2; layout++)
    for (int wi = 0; wi < 3; wi++)
      snprintf(rows[r_sl[layout][wi]].note, sizeof rows[0].note, "bits vs token loop: %s",
               same[layout][wi] ? "IDENTICAL (outputs and state)" : "DIFFER");

  // ---------- (3) prelude ----------
  int r_norm = add_row("(3) prelude: normalize one 128-wide vector (one per value head)", 0);
  int r_sc = add_row("(3) prelude: decay (expf, log1pf, expf) + beta (expf, divide)", 0);
  {
    float in[KD], out[KD];
    for (int i = 0; i < KD; i++) in[i] = (float)(urand() * 2 - 1);
    volatile float sink = 0;
    const int N = 20000;
    for (int round = 0; round < 60 * rounds_scale; round++) {
      calib_tick();
      uint64_t t0 = now_ns();
      for (int n = 0; n < N; n++) {
        in[n & 127] += 1e-3f;
        normalize_gdn(in, out);
        sink += out[n & 127];
      }
      uint64_t t1 = now_ns();
      upd(r_norm, (double)(t1 - t0) / N);
      t0 = now_ns();
      for (int n = 0; n < N; n++) {
        float a = (float)(n & 1023) * 1e-3f - 0.5f;
        sink += decay_of(a, 0.45f, -0.18f) + beta_of(a);
      }
      t1 = now_ns();
      upd(r_sc, (double)(t1 - t0) / N);
    }
  }

  // ---------- (4) AVX-512 parts of the proposed AMX block kernel, C = 32 ----------
  int r_split = add_row("(4) G2 split + pack + guard of S0, per token per value head (C = 32)", 8192.0 / 32);
  int r_tri = add_row("(4) G2 triangle, per token per value head (C = 32)", 9216.0 / 32);
  int r_fin = add_row("(4) G2 final S = fma(gamma, S0, T), per token per value head (C = 32)", 1024.0 / 32);
  {
    enum { C = 32 };
    uint8_t *scratch = aligned_alloc(4096, 16 * 1024);
    float *Tscr = alloc_f(1024);  // 4 KiB tile-store scratch
    float *R0 = alloc_f(C * VD), *U0 = alloc_f(C * VD), *CK = alloc_f(C * C), *CQ = alloc_f(C * C);
    float *Vv = alloc_f(C * VD), *De = alloc_f(C * VD), *Oo = alloc_f(C * VD);
    float gam[64], sgv[64], bet[64];
    for (int i = 0; i < C * VD; i++) {
      R0[i] = (float)(urand() - 0.5);
      U0[i] = (float)(urand() - 0.5);
      Vv[i] = (float)(urand() - 0.5);
    }
    for (int i = 0; i < C * C; i++) {
      CK[i] = (float)(0.05 * (urand() - 0.5));
      CQ[i] = (float)(0.05 * (urand() - 0.5));
    }
    for (int t = 0; t < C; t++) {
      gam[t] = 0.9f;
      sgv[t] = 0.08f;
      bet[t] = 0.5f;
    }
    for (size_t i = 0; i < 1024; i++) Tscr[i] = (float)(0.01 * (urand() - 0.5));
    volatile float sink = 0;
    int bad_total = 0;
    for (int round = 0; round < 200 * rounds_scale; round++) {
      if ((round & 7) == 0) calib_tick();
      to_blocked(Sblk, S0, H);  // working copy sits in L2 / L1 as after a chain start
      uint64_t t0 = now_ns();
      __m512 g = _mm512_setzero_ps();
      for (int h = 0; h < H; h++)
        for (int vb = 0; vb < NCH; vb++)
          g = _mm512_add_ps(g, split_pack_block(Sblk + ((size_t)h * NCH + vb) * KD * 16, scratch));
      uint64_t t1 = now_ns();
      sink += _mm512_reduce_add_ps(g) + scratch[round & 1023];
      upd(r_split, (double)(t1 - t0) / (H * (double)C));
      if (round == 0) {
        const float *blk = Sblk + ((size_t)(H - 1) * NCH + (NCH - 1)) * KD * 16;
        for (int j = 0; j < 64; j++)
          for (int c = 0; c < 16; c++)
            for (int par = 0; par < 2; par++) {
              float sum = 0;
              for (int p = 0; p < 3; p++) {
                uint16_t w16;
                memcpy(&w16, scratch + (size_t)(j / 16) * 3 * 1024 + (size_t)p * 1024 + (size_t)(j % 16) * 64 + c * 4 + par * 2, 2);
                uint32_t b = (uint32_t)w16 << 16;
                float f;
                memcpy(&f, &b, 4);
                sum += f;
              }
              if (sum != blk[(2 * j + par) * 16 + c]) bad_total++;
            }
      }
      t0 = now_ns();
      triangle(C, R0, U0, CK, CQ, gam, sgv, Vv, bet, De, Oo);
      t1 = now_ns();
      sink += Oo[round & 1023];
      upd(r_tri, (double)(t1 - t0) / C);
      // final pass: per value block and group of 4 key-row blocks, S = fma(gamma, S, T) from the 4 KiB scratch
      t0 = now_ns();
      {
        __m512 gm = _mm512_set1_ps(0.97f);
        for (int h = 0; h < H; h++)
          for (int vb = 0; vb < NCH; vb++)
            for (int grp = 0; grp < 2; grp++) {
              float *Sp = Sblk + (((size_t)h * NCH + vb) * KD + grp * 64) * 16;
              for (int rr = 0; rr < 64; rr++)
                _mm512_store_ps(Sp + rr * 16, _mm512_fmadd_ps(gm, _mm512_load_ps(Sp + rr * 16), _mm512_load_ps(Tscr + rr * 16)));
            }
      }
      t1 = now_ns();
      upd(r_fin, (double)(t1 - t0) / (H * (double)C));
    }
    snprintf(rows[r_split].note, sizeof rows[0].note, "split check: %d of 2048 values not equal to lo + mid + hi", bad_total);
  }
  for (int i = 0; i < 20; i++) calib_tick();

  printf("host: design host, KVM guest on AMD Ryzen 9 9950X (Zen 5). NOT the Xeon 6962P.\n");
  printf("cpu %d; core clock = highest reading of the run = %.3f GHz; times = lowest of the interleaved repetitions\n\n", cpu, g_ghz);
  printf("%-88s %9s %8s %8s  %s\n", "case", "ns", "cycles", "ops/cyc", "note");
  for (int i = 0; i < n_rows; i++) {
    double cyc = rows[i].ns * g_ghz;
    if (rows[i].ops > 0)
      printf("%-88s %9.1f %8.0f %8.2f  %s\n", rows[i].label, rows[i].ns, cyc, rows[i].ops / cyc, rows[i].note);
    else
      printf("%-88s %9.1f %8.0f %8s  %s\n", rows[i].label, rows[i].ns, cyc, "-", rows[i].note);
  }
  double tok = rows[r_tok].ns, l1 = rows[r_l1].ns;
  printf("\nderived (ratios do not depend on the clock reading):\n");
  printf("  token loop, 2,048 KiB (the M1 state size) / token loop, 128 KiB (the tron prefill working copy) = %.2fx\n",
         rows[r1[NH - 1]].ns / rows[r1[1]].ns);
  printf("  token loop, 1,024 KiB (= this host's L2 size) / token loop, 128 KiB = %.2fx\n", rows[r1[NH - 2]].ns / rows[r1[1]].ns);
  printf("  token loop 128 KiB / slice replay blocked window 32  = %.2fx\n", tok / rows[r_sl[1][0]].ns);
  printf("  token loop 128 KiB / slice replay blocked window 128 = %.2fx\n", tok / rows[r_sl[1][1]].ns);
  printf("  token loop 128 KiB / slice replay standard window 32 = %.2fx\n", tok / rows[r_sl[0][0]].ns);
  printf("  token loop 128 KiB / one slice in L1                 = %.2fx (upper limit of any same-bits reorder on this host)\n", tok / l1);
  printf("  memory cost of the token loop at 128 KiB: (%.0f - %.0f) cycles / 2,048 lines = %.2f cycles per line on this host\n",
         tok * g_ghz, l1 * g_ghz, (tok - l1) * g_ghz / 2048);
  printf("  prelude per value head per token = %.0f cycles on this host\n", (rows[r_norm].ns + rows[r_sc].ns) * g_ghz);
  return 0;
}
