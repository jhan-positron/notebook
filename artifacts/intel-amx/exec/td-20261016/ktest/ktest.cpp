// ktest.cpp - bit-level measurements of the tron QK/PV attention kernels
// (positron-ai/tron issue #4444, token divergence AMX / VNNI-K vs row-major
// AVX-512). Links the real kernel translation unit src/tron/kernels/amx_attn.cpp
// and the real headers (dotter.hpp, kernels/k_vnni.hpp, tensor/k_vnni.hpp,
// tensor/v_vnni.hpp). No tron source is modified. The AVX-512 PV loop of
// kv_cache.hpp (detail::scaled_v_expr, head_size 128) is reproduced verbatim
// below (avx_scaled_v) because it is a private member of a cache template.
//
// Sections (one result line each, prefixed by the section label):
//   T0  semantics of one _mm512_dpbf16_ps lane (which fp32 add order it is)
//   T1  qk_vnni_128x4 (AMX) vs k_vnni::qk_group<4,bf16> (AVX-512 VNNI reader)
//   T1b qk_rowmajor_128x4 vs qk_vnni_128x4
//   T2  dotter<bf16,128> vs qk_vnni_128x4
//   T3  dotter<bf16,128> vs scalar references in the dotter's own order
//   T4  k_vnni::qk_group vs scalar sequential references
//   T5  qk_vnni_128x4 (TDPBF16PS) vs scalar references (sequential, exact ...)
//   T6  weights_times_v_128x4 vs the AVX scaled_v loop (bf16-exact P, fp32 P,
//       RNE-fed AVX loop)
//   T7  accuracy of the truncated-P (AVX) and RNE-P (AMX) outputs vs fp64
//   T8  T7 for 16-token and 1-token pages
#include <immintrin.h>
#include <sched.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <random>
#include <string>
#include <vector>

#include "common/numerics/bf16.hpp"
#include "tron/kernels/amx_attn_iface.hpp"
#include "tron/kernels/dotter.hpp"
#include "tron/kernels/k_vnni.hpp"
#include "tron/tensor/k_vnni.hpp"
#include "tron/tensor/v_vnni.hpp"
#include "tron/tensor/view.hpp"

// common/assert.hpp declares this; src/common/assert.cpp is not linked here.
namespace tron {
std::string get_abort_context() noexcept {
  return "ktest";
}
}  // namespace tron

namespace {

using tron::bf16;
namespace amx = tron::amx_attn_h128g4;
constexpr size_t T64 = 64, D128 = 128, H4 = 4;
constexpr size_t N_QK_INSTANCES = 2000;
constexpr size_t N_PV_INSTANCES = 2000;
constexpr uint64_t SEED = 20261016;

// ---------------------------------------------------------------- bit helpers
uint32_t fbits(float f) {
  uint32_t u;
  std::memcpy(&u, &f, 4);
  return u;
}
float fromfbits(uint32_t u) {
  float f;
  std::memcpy(&f, &u, 4);
  return f;
}
uint16_t bf16_trunc_bits(float f) {
  return uint16_t(fbits(f) >> 16);
}
uint16_t bf16_rne_bits(float f) {
  uint32_t u = fbits(f);
  u += 0x7fffu + ((u >> 16) & 1u);
  return uint16_t(u >> 16);
}
float bits2f(uint16_t b) {
  return fromfbits(uint32_t(b) << 16);
}
float bf16r(float f) {  // round to nearest even, returned as the exact float
  return bits2f(bf16_rne_bits(f));
}
float bf16t(float f) {  // truncate, returned as the exact float
  return bits2f(bf16_trunc_bits(f));
}
bf16 mk(float f) {  // bf16 object with RNE bits
  return bf16::from_bits(bf16_rne_bits(f));
}
float val(const bf16& x) {  // exact float value of a bf16 object
  return bits2f(x.to_bits());
}

// ------------------------------------------------- exact fixed-point accumulator
// Exact sum of fp32 values as a 128-bit integer scaled by 2^-SCALE, rounded
// once to fp32 (RNE) on demand. Products of two bf16 are exact fp32 values, so
// this gives the single-rounding reference of any sum of such products.
struct fx {
  static constexpr int SCALE = 100;
  __int128 v = 0;
  bool inexact = false;
  bool overflow = false;
  void add(float f) {
    if (f == 0.0f) return;
    int e;
    const float m = std::frexp(f, &e);           // f = m * 2^e, 0.5 <= |m| < 1
    const int64_t M = int64_t(std::ldexp(m, 24));  // exact, |M| < 2^24
    const int sh = e - 24 + SCALE;
    if (sh >= 0) {
      if (sh > 100) overflow = true;
      else v += __int128(M) << sh;
    } else {
      const int k = -sh;
      if (k >= 63 || (M & ((int64_t(1) << k) - 1)) != 0) inexact = true;
      v += M >> k;
    }
  }
  static int clz128(unsigned __int128 u) {
    const uint64_t hi = uint64_t(u >> 64), lo = uint64_t(u);
    return hi ? __builtin_clzll(hi) : 64 + __builtin_clzll(lo);
  }
  // RNE to P significant bits, kept exact in this fixed-point form
  fx round_to_bits(int P) const {
    fx r;
    if (v == 0) return r;
    const bool neg = v < 0;
    unsigned __int128 u = neg ? (unsigned __int128)(-v) : (unsigned __int128)v;
    const int msb = 127 - clz128(u);
    const int drop = msb - (P - 1);
    if (drop <= 0) {
      r.v = v;
      return r;
    }
    unsigned __int128 mant = u >> drop;
    const unsigned __int128 rem = u - (mant << drop);
    const unsigned __int128 half = (unsigned __int128)1 << (drop - 1);
    if (rem > half || (rem == half && (mant & 1))) mant++;
    r.v = (__int128)(mant << drop);
    if (neg) r.v = -r.v;
    return r;
  }
  float round() const {
    if (v == 0) return 0.0f;
    const bool neg = v < 0;
    unsigned __int128 u = neg ? (unsigned __int128)(-v) : (unsigned __int128)v;
    const int msb = 127 - clz128(u);
    int drop = msb - 23;
    uint64_t mant;
    if (drop > 0) {
      mant = uint64_t(u >> drop);
      const unsigned __int128 rem = u - ((unsigned __int128)mant << drop);
      const unsigned __int128 half = (unsigned __int128)1 << (drop - 1);
      if (rem > half || (rem == half && (mant & 1))) {
        mant++;
        if (mant == (uint64_t(1) << 24)) {
          mant >>= 1;
          drop++;
        }
      }
    } else {
      mant = uint64_t(u);
      drop = 0;
    }
    const float f = std::ldexp(float(mant), drop - SCALE);
    return neg ? -f : f;
  }
};

// ----------------------------------------------------- candidate add semantics
// One pair step of a bf16 dot-product instruction: acc receives the two exact
// products pe (even dim) and po (odd dim). Each + is an fp32 RNE add.
enum sem : int { S1 = 0, S2, S3, SG, N_SEM };
const char* sem_name[N_SEM] = {"s1:(acc+pe)+po", "s2:(acc+po)+pe", "s3:acc+(pe+po)",
    "sg:round1(acc+pe+po)"};
float dp_pair(float acc, float pe, float po, int s) {
  switch (s) {
  case S1: return (acc + pe) + po;
  case S2: return (acc + po) + pe;
  case S3: return acc + (pe + po);
  default: {
    fx x;
    x.add(acc);
    x.add(pe);
    x.add(po);
    return x.round();
  }
  }
}

// ----------------------------------------------------------- comparison stats
struct cmp_stats {
  size_t n = 0, ndiff = 0, nref0 = 0;
  double max_abs = 0, max_rel = 0, max_bf16ulp = 0, sum_abs = 0;
  uint64_t max_bits = 0;
  uint64_t hist[7] = {};  // bit distance 0,1,2,3-4,5-8,9-16,>16
  void add(float ref, float other) {
    n++;
    const uint32_t a = fbits(ref), b = fbits(other);
    if (a == b) {
      hist[0]++;
      return;
    }
    ndiff++;
    const double d = std::fabs(double(ref) - double(other));
    sum_abs += d;
    max_abs = std::max(max_abs, d);
    if (ref != 0.0f) max_rel = std::max(max_rel, d / std::fabs(double(ref)));
    else nref0++;
    uint64_t bd;
    if ((a >> 31) == (b >> 31)) bd = a > b ? a - b : b - a;
    else bd = uint64_t(a & 0x7fffffffu) + uint64_t(b & 0x7fffffffu);
    max_bits = std::max(max_bits, bd);
    int e;
    std::frexp(ref == 0.0f ? other : ref, &e);
    const double ulp_bf16 = std::ldexp(1.0, e - 8);  // 2^(exponent-7), bf16 has 8 significant bits
    max_bf16ulp = std::max(max_bf16ulp, d / ulp_bf16);
    const int bucket = bd == 1 ? 1 : bd == 2 ? 2 : bd <= 4 ? 3 : bd <= 8 ? 4 : bd <= 16 ? 5 : 6;
    hist[bucket]++;
  }
  void print(const char* label) const {
    std::printf("%s identical=%s n=%zu diff=%zu (%.3f%%)", label, ndiff == 0 ? "yes" : "no",
        n, ndiff, 100.0 * double(ndiff) / double(n ? n : 1));
    if (ndiff) {
      std::printf(" max_abs=%.3e mean_abs=%.3e max_rel=%.3e max_fp32ulps=%llu max_bf16ulps=%.4f"
                  " hist[0,1,2,3-4,5-8,9-16,>16]=[%llu,%llu,%llu,%llu,%llu,%llu,%llu]",
          max_abs, sum_abs / double(ndiff), max_rel, (unsigned long long)max_bits,
          max_bf16ulp, (unsigned long long)hist[0], (unsigned long long)hist[1],
          (unsigned long long)hist[2], (unsigned long long)hist[3],
          (unsigned long long)hist[4], (unsigned long long)hist[5],
          (unsigned long long)hist[6]);
    }
    std::printf("\n");
  }
};

// ------------------------------------------------------------------ QK data
struct qk_inst {
  alignas(64) bf16 k[T64 * D128];  // row-major K, token-major
  alignas(64) bf16 q[H4 * D128];   // 4 query heads
};

void fill_qk(qk_inst& in, std::mt19937_64& g) {
  std::normal_distribution<float> nd(0.0f, 1.0f);
  for (auto& x : in.k) x = mk(nd(g));
  for (auto& x : in.q) x = mk(nd(g));
}

// exact products q_h[d] * k_t[d], d = 0..127, in dimension order
void products(const qk_inst& in, size_t h, size_t t, float p[D128]) {
  for (size_t d = 0; d < D128; d++) {
    p[d] = val(in.q[h * D128 + d]) * val(in.k[t * D128 + d]);
  }
}

// scalar sequential reference over the 64 dimension pairs in order
float ref_seq(const float p[D128], int s) {
  float acc = 0.0f;
  for (size_t dp = 0; dp < D128 / 2; dp++) acc = dp_pair(acc, p[2 * dp], p[2 * dp + 1], s);
  return acc;
}

// AMX-shaped references: 4 instructions (steps) of 16 pairs each, acc carried
// across the steps in fp32.
enum amx_cand : int {
  A_SEQ_S1 = 0,
  A_SEQ_S2,
  A_SEQ_S3,
  A_SEQ_SG,
  A_STEP_EXACT_ADD,  // per step: round1(sum of 32 products), then acc + that
  A_STEP_EXACT_ACC,  // per step: round1(acc + sum of 32 products)
  A_ALL_EXACT,       // round1(sum of all 128 products)
  A_STEP_PAIRTREE,   // per step: pair sums fl(pe+po), pairwise tree of 16, acc + that
  A_STEP_SEQ_S1_ADD, // per step: sequential s1 from 0 over 16 pairs, then acc + that
  N_AMX_CAND
};
const char* amx_cand_name[N_AMX_CAND] = {"seq_s1", "seq_s2", "seq_s3", "seq_sg(round1 per pair)",
    "step_exact_then_add", "step_exact_with_acc", "all128_exact_round1", "step_pairtree_then_add",
    "step_seq_s1_then_add"};

float ref_amx(const float p[D128], int cand) {
  switch (cand) {
  case A_SEQ_S1: return ref_seq(p, S1);
  case A_SEQ_S2: return ref_seq(p, S2);
  case A_SEQ_S3: return ref_seq(p, S3);
  case A_SEQ_SG: return ref_seq(p, SG);
  case A_STEP_EXACT_ADD: {
    float acc = 0.0f;
    for (size_t st = 0; st < 4; st++) {
      fx x;
      for (size_t d = 0; d < 32; d++) x.add(p[st * 32 + d]);
      acc = acc + x.round();
    }
    return acc;
  }
  case A_STEP_EXACT_ACC: {
    float acc = 0.0f;
    for (size_t st = 0; st < 4; st++) {
      fx x;
      x.add(acc);
      for (size_t d = 0; d < 32; d++) x.add(p[st * 32 + d]);
      acc = x.round();
    }
    return acc;
  }
  case A_ALL_EXACT: {
    fx x;
    for (size_t d = 0; d < D128; d++) x.add(p[d]);
    return x.round();
  }
  case A_STEP_PAIRTREE: {
    float acc = 0.0f;
    for (size_t st = 0; st < 4; st++) {
      float v[16];
      for (size_t k = 0; k < 16; k++) v[k] = p[st * 32 + 2 * k] + p[st * 32 + 2 * k + 1];
      for (size_t w = 8; w >= 1; w /= 2)
        for (size_t k = 0; k < w; k++) v[k] = v[2 * k] + v[2 * k + 1];
      acc = acc + v[0];
    }
    return acc;
  }
  case A_STEP_SEQ_S1_ADD: {
    float acc = 0.0f;
    for (size_t st = 0; st < 4; st++) {
      float t = 0.0f;
      for (size_t k = 0; k < 16; k++) t = dp_pair(t, p[st * 32 + 2 * k], p[st * 32 + 2 * k + 1], S1);
      acc = acc + t;
    }
    return acc;
  }
  default: return 0.0f;
  }
}

// dotter<bf16,128> order: lane j of sum1 = dims (2j,2j+1) then (64+2j,64+2j+1);
// sum2 = dims (32+2j,..) then (96+2j,..); v = sum1 + sum2 lanewise; reduce.
enum red_cand : int { R_HALVING = 0, R_SEQ, R_ADJ_TREE, N_RED };
const char* red_name[N_RED] = {"halving(j+8,j+4,j+2,0+1)", "sequential(l0..l15)",
    "adjacent_tree((0+1)+(2+3)..)"};
float reduce16(const float in[16], int r) {
  float v[16];
  std::memcpy(v, in, sizeof(v));
  switch (r) {
  case R_HALVING:
    for (size_t w = 8; w >= 1; w /= 2)
      for (size_t j = 0; j < w; j++) v[j] = v[j] + v[j + w];
    return v[0];
  case R_SEQ: {
    float acc = v[0];
    for (size_t j = 1; j < 16; j++) acc = acc + v[j];
    return acc;
  }
  default:
    for (size_t w = 8; w >= 1; w /= 2)
      for (size_t j = 0; j < w; j++) v[j] = v[2 * j] + v[2 * j + 1];
    return v[0];
  }
}
float ref_dotter(const float p[D128], int s, int r) {
  float v[16];
  for (size_t j = 0; j < 16; j++) {
    float s1 = dp_pair(0.0f, p[2 * j], p[2 * j + 1], s);
    s1 = dp_pair(s1, p[64 + 2 * j], p[64 + 2 * j + 1], s);
    float s2 = dp_pair(0.0f, p[32 + 2 * j], p[32 + 2 * j + 1], s);
    s2 = dp_pair(s2, p[96 + 2 * j], p[96 + 2 * j + 1], s);
    v[j] = s1 + s2;
  }
  return reduce16(v, r);
}

// ------------------------------------------------------------- PV helpers
// Verbatim copy of the head_size == 128 loop of detail::scaled_v_expr
// (h/tron/models/kv_cache.hpp), with the same interleave_bf16_ps (truncation).
// `plane` is the packed V plane (pair rows), `scales` the fp32 P row, `count`
// the number of live tokens. Writes out[0..127] = the 8 accumulator chunks.
void avx_scaled_v(const bf16* plane, const float* scales, size_t count, float out[D128]) {
  const __m512i hi_16_of_32 = _mm512_set1_epi32(0xffff0000);
  auto interleave_bf16_ps = [&](__m512 lo_fp32, __m512 hi_fp32) -> __m512i {
    __m512i lo_bf16 = _mm512_srli_epi32(_mm512_castps_si512(lo_fp32), 16);
    __m512i hi_bf16 = _mm512_castps_si512(hi_fp32);
    return _mm512_ternarylogic_epi32(
        lo_bf16, hi_bf16, hi_16_of_32, _MM_TERNLOG_A | (_MM_TERNLOG_B & _MM_TERNLOG_C));
  };
  constexpr size_t chunk_size = 16, head_size = D128;
  __m512 t0 = _mm512_setzero_ps(), t1 = t0, t2 = t0, t3 = t0, t4 = t0, t5 = t0, t6 = t0,
         t7 = t0;
  const size_t end = (count + 1) / 2 * 2;  // Round up to even to operate on pairs.
  for (size_t i = 0; i < end; i += 2) {
    const __m512i scale =
        interleave_bf16_ps(_mm512_set1_ps(scales[i]), _mm512_set1_ps(scales[i + 1]));
    const bf16* tile = plane + i * head_size;
    t0 = _mm512_dpbf16_ps(t0, (__m512bh)_mm512_load_si512(tile + 2 * chunk_size * 0), (__m512bh)scale);
    t1 = _mm512_dpbf16_ps(t1, (__m512bh)_mm512_load_si512(tile + 2 * chunk_size * 1), (__m512bh)scale);
    t2 = _mm512_dpbf16_ps(t2, (__m512bh)_mm512_load_si512(tile + 2 * chunk_size * 2), (__m512bh)scale);
    t3 = _mm512_dpbf16_ps(t3, (__m512bh)_mm512_load_si512(tile + 2 * chunk_size * 3), (__m512bh)scale);
    t4 = _mm512_dpbf16_ps(t4, (__m512bh)_mm512_load_si512(tile + 2 * chunk_size * 4), (__m512bh)scale);
    t5 = _mm512_dpbf16_ps(t5, (__m512bh)_mm512_load_si512(tile + 2 * chunk_size * 5), (__m512bh)scale);
    t6 = _mm512_dpbf16_ps(t6, (__m512bh)_mm512_load_si512(tile + 2 * chunk_size * 6), (__m512bh)scale);
    t7 = _mm512_dpbf16_ps(t7, (__m512bh)_mm512_load_si512(tile + 2 * chunk_size * 7), (__m512bh)scale);
  }
  _mm512_storeu_ps(out + 0 * 16, t0);
  _mm512_storeu_ps(out + 1 * 16, t1);
  _mm512_storeu_ps(out + 2 * 16, t2);
  _mm512_storeu_ps(out + 3 * 16, t3);
  _mm512_storeu_ps(out + 4 * 16, t4);
  _mm512_storeu_ps(out + 5 * 16, t5);
  _mm512_storeu_ps(out + 6 * 16, t6);
  _mm512_storeu_ps(out + 7 * 16, t7);
}

struct pv_inst {
  alignas(64) bf16 v[T64 * D128];  // logical V[token][dim]
  alignas(64) float p[H4][T64];    // fp32 weights (exp rows)
};

using v_owner_t = tron::v_vnni_tensor<T64, D128>;

void fill_v_plane(const pv_inst& in, v_owner_t& owner) {
  for (size_t t = 0; t < T64; t++) {
    tron::append_v_row(owner.as_view(), t, tron::v_source_row<D128>(in.v + t * D128));
  }
}

// softmax-like weights for `count` live tokens: P = exp(s - max), s ~ N(0, 3);
// the other tokens get 0.
void fill_p(pv_inst& in, std::mt19937_64& g, size_t count, bool bf16_exact) {
  std::normal_distribution<float> nd(0.0f, 3.0f);
  for (size_t h = 0; h < H4; h++) {
    float s[T64], m = -INFINITY;
    for (size_t t = 0; t < count; t++) {
      s[t] = nd(g);
      m = std::max(m, s[t]);
    }
    for (size_t t = 0; t < T64; t++) {
      float p = t < count ? std::exp(s[t] - m) : 0.0f;
      in.p[h][t] = bf16_exact ? bf16r(p) : p;
    }
  }
}

struct acc_stats {  // accuracy of one path vs the fp64 reference
  double sum_rel = 0, sum_rel2 = 0, sum_signed_num = 0, sum_abs_exact = 0;
  size_t n_incl = 0, n_all = 0, n_exact_match = 0;
  double max_rel = 0;
  void add(double exact, double got, double mass) {
    n_all++;
    if (got == exact) n_exact_match++;
    const double err = got - exact;
    sum_signed_num += exact >= 0 ? err : -err;
    sum_abs_exact += std::fabs(exact);
    if (std::fabs(exact) >= 0.1 * mass) {  // skip cancellation-dominated outputs
      const double rel = err / exact;
      sum_rel += rel;
      sum_rel2 += rel * rel;
      max_rel = std::max(max_rel, std::fabs(rel));
      n_incl++;
    }
  }
  double bias() const { return sum_rel / double(n_incl ? n_incl : 1); }
  double rms() const { return std::sqrt(sum_rel2 / double(n_incl ? n_incl : 1)); }
  double mass_bias() const { return sum_signed_num / (sum_abs_exact > 0 ? sum_abs_exact : 1); }
};

void print_acc(const char* label, const char* what, const acc_stats& a) {
  std::printf("%s %s: n=%zu incl=%zu exact_match=%zu mean_signed_rel(bias)=%+.3e"
              " mass_weighted_bias=%+.3e rms_rel=%.3e max_rel=%.3e\n",
      label, what, a.n_all, a.n_incl, a.n_exact_match, a.bias(), a.mass_bias(), a.rms(), a.max_rel);
}

// T7/T8 body: softmax-like fp32 P over `count` tokens, V as given (already in `in.v`).
void accuracy_section(const char* label, size_t count, std::mt19937_64& g,
    float v_scale, size_t n_inst) {
  auto in = std::make_unique<pv_inst>();
  auto owner = std::make_unique<v_owner_t>();
  alignas(64) static float o_amx[16 * D128];
  acc_stats st_trunc, st_rne;
  double wm_trunc = 0, wm_rne = 0;
  size_t wm_n = 0;
  std::normal_distribution<float> nd(0.0f, 1.0f);
  for (size_t it = 0; it < n_inst; it++) {
    for (auto& x : in->v) x = mk(v_scale * nd(g));
    fill_v_plane(*in, *owner);
    if (count == 1) {
      for (size_t h = 0; h < H4; h++) {
        for (size_t t = 0; t < T64; t++) in->p[h][t] = t == 0 ? 1.0f : 0.0f;  // exp(s - max) = exp(0)
      }
    } else {
      fill_p(*in, g, count, false);
    }
    amx::weights_times_v_128x4(std::as_const(*owner).as_view(), &in->p[0][0], T64, o_amx);
    const bf16* plane = tron::detail::v_vnni_access::plane(std::as_const(*owner).as_view());
    for (size_t h = 0; h < H4; h++) {
      float o_avx[D128];
      avx_scaled_v(plane, in->p[h], count, o_avx);
      double sp = 0, spt = 0, spr = 0;
      for (size_t t = 0; t < count; t++) {
        sp += in->p[h][t];
        spt += bf16t(in->p[h][t]);
        spr += bf16r(in->p[h][t]);
      }
      wm_trunc += spt / sp - 1.0;
      wm_rne += spr / sp - 1.0;
      wm_n++;
      for (size_t d = 0; d < D128; d++) {
        double exact = 0, mass = 0;
        for (size_t t = 0; t < count; t++) {
          const double pv = double(in->p[h][t]) * double(val(in->v[t * D128 + d]));
          exact += pv;
          mass += std::fabs(pv);
        }
        st_trunc.add(exact, o_avx[d], mass);
        st_rne.add(exact, o_amx[h * D128 + d], mass);
      }
    }
  }
  std::printf("%s tokens=%zu V~bf16(N(0,1)*%g) instances=%zu\n", label, count, v_scale, n_inst);
  print_acc(label, "o_trunc(AVX path) vs fp64", st_trunc);
  print_acc(label, "o_rne(AMX kernel) vs fp64", st_rne);
  std::printf("%s rms_ratio trunc/rne=%.3f\n", label, st_trunc.rms() / (st_rne.rms() > 0 ? st_rne.rms() : 1));
  std::printf("%s weight-mass bias: sum(bf16_trunc(P))/sum(P)-1=%+.4e  sum(bf16_rne(P))/sum(P)-1=%+.4e (mean over %zu rows)\n",
      label, wm_trunc / double(wm_n), wm_rne / double(wm_n), wm_n);
  std::printf("%s normalized output o/sum(P): both paths divide by the same fp32 sum(P) of the UNROUNDED P, so the relative errors above apply unchanged\n", label);
}


// ------------------------------------------- T5x: TDPBF16PS inner-arithmetic search
// Model of one fused dot-product unit: the 2G exact products of G dimension
// pairs (and optionally the accumulator) are aligned to the largest exponent
// among them, each kept to W bits below that leading bit (bits shifted out are
// dropped by `align_rm`), summed exactly as integers, and the sum is rounded to
// fp32 by `final_rm`. If the accumulator is not inside the unit, the unit's
// result is added to it with an fp32 RNE add (combine=seq), or the group
// results of one instruction are first combined pairwise (combine=tree) and
// the tree result is then added to the accumulator.
struct t5_sample {
  float p[D128];
  float hw;
};
enum rm : int { RM_RZ = 0, RM_FLOOR, RM_RNE, N_RM };
const char* rm_name[N_RM] = {"rz", "floor", "rne"};
struct term {  // exact fp32 value as integer mantissa M (|M| < 2^24) times 2^e24
  int64_t M;
  int e24;
  int lead;  // exponent of the leading bit (value in [2^lead, 2^lead+1)), INT_MIN for 0
};
term to_term(float f) {
  term t{};
  if (f == 0.0f) {
    t.lead = -100000;
    return t;
  }
  int e;
  const float m = std::frexp(f, &e);
  t.M = int64_t(std::ldexp(m, 24));
  t.e24 = e - 24;
  t.lead = e - 1;
  return t;
}
__int128 shift_round(int64_t M, int k, int mode) {  // M / 2^k with rounding mode
  if (k <= 0) return __int128(M) << (-k);
  if (k >= 62) {
    if (mode == RM_FLOOR && M < 0) return -1;
    return 0;
  }
  const int64_t mask = (int64_t(1) << k) - 1;
  switch (mode) {
  case RM_FLOOR: return M >> k;
  case RM_RZ: return M < 0 ? -((-M) >> k) : (M >> k);
  default: {  // RNE on the magnitude
    const bool neg = M < 0;
    const int64_t a = neg ? -M : M;
    int64_t q = a >> k;
    const int64_t rem = a & mask, half = int64_t(1) << (k - 1);
    if (rem > half || (rem == half && (q & 1))) q++;
    return neg ? -q : q;
  }
  }
}
float int128_to_fp32(__int128 v, int lsb_exp, int mode) {  // v * 2^lsb_exp -> fp32
  if (v == 0) return 0.0f;
  const bool neg = v < 0;
  unsigned __int128 u = neg ? (unsigned __int128)(-v) : (unsigned __int128)v;
  const int msb = 127 - fx::clz128(u);
  int drop = msb - 23;
  uint64_t mant;
  if (drop > 0) {
    mant = uint64_t(u >> drop);
    if (mode == RM_RNE) {
      const unsigned __int128 rem = u - ((unsigned __int128)mant << drop);
      const unsigned __int128 half = (unsigned __int128)1 << (drop - 1);
      if (rem > half || (rem == half && (mant & 1))) {
        mant++;
        if (mant == (uint64_t(1) << 24)) {
          mant >>= 1;
          drop++;
        }
      }
    }  // RM_RZ: truncate the magnitude
  } else {
    mant = uint64_t(u);
    drop = 0;
  }
  const float f = std::ldexp(float(mant), drop + lsb_exp);
  return neg ? -f : f;
}
// one fused unit over terms[0..n), optionally with acc inside
float fused_unit(const term* terms, int n, const term* acc, int W, int align_rm, int final_rm) {
  int E = -100000;
  for (int i = 0; i < n; i++) E = std::max(E, terms[i].lead);
  if (acc) E = std::max(E, acc->lead);
  if (E == -100000) return 0.0f;
  const int L = E - W + 1;  // exponent of the unit's LSB
  __int128 S = 0;
  for (int i = 0; i < n; i++) {
    if (terms[i].M == 0) continue;
    S += shift_round(terms[i].M, L - terms[i].e24, align_rm);
  }
  if (acc && acc->M != 0) S += shift_round(acc->M, L - acc->e24, align_rm);
  return int128_to_fp32(S, L, final_rm);
}
struct t5_cand {
  int G;  // pairs per fused unit: 1,2,4,8,16
  int acc_inside;
  int W;
  int align_rm, final_rm;
  int tree;  // 0: unit results added to acc one by one; 1: adjacent tree per instruction, then acc add
  size_t match = 0;
  std::string name() const {
    char b[160];
    std::snprintf(b, sizeof(b), "G=%d acc_inside=%d W=%d align=%s final=%s combine=%s", G,
        acc_inside, W, rm_name[align_rm], rm_name[final_rm], tree ? "tree" : "seq");
    return b;
  }
};
float eval_cand(const t5_cand& c, const term* terms /*128, dimension order*/) {
  float acc = 0.0f;
  for (int st = 0; st < 4; st++) {
    const int units = 16 / c.G;
    float r[16];
    for (int u = 0; u < units; u++) {
      const term* t = terms + st * 32 + u * 2 * c.G;
      if (c.acc_inside) {
        const term a = to_term(acc);
        acc = fused_unit(t, 2 * c.G, &a, c.W, c.align_rm, c.final_rm);
      } else {
        r[u] = fused_unit(t, 2 * c.G, nullptr, c.W, c.align_rm, c.final_rm);
      }
    }
    if (!c.acc_inside) {
      if (c.tree && units > 1) {
        int w = units;
        while (w > 1) {
          for (int k = 0; k < w / 2; k++) r[k] = r[2 * k] + r[2 * k + 1];
          w /= 2;
        }
        acc = acc + r[0];
      } else {
        for (int u = 0; u < units; u++) acc = acc + r[u];
      }
    }
  }
  return acc;
}
void t5_search(const std::vector<t5_sample>& samples, const std::vector<t5_sample>& all) {
  std::vector<t5_cand> cands;
  const int Ws[] = {16, 18, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
      38, 40, 44, 48, 56, 64, 80};
  for (int G : {16, 8, 4, 2, 1})
    for (int ai = 0; ai < 2; ai++)
      for (int W : Ws)
        for (int ar = 0; ar < N_RM; ar++)
          for (int fr = 0; fr < 2; fr++)  // final: rz or rne (floor = rz on magnitude here)
            for (int tr = 0; tr < (ai || G == 16 ? 1 : 2); tr++)
              cands.push_back({G, ai, W, ar, fr == 0 ? RM_RZ : RM_RNE, tr});
  std::vector<term> terms(D128);
  for (const auto& s : samples) {
    for (size_t d = 0; d < D128; d++) terms[d] = to_term(s.p[d]);
    for (auto& c : cands)
      if (fbits(eval_cand(c, terms.data())) == fbits(s.hw)) c.match++;
  }
  std::sort(cands.begin(), cands.end(), [](const t5_cand& a, const t5_cand& b) { return a.match > b.match; });
  std::printf("T5x model search over %zu candidates on %zu scores; top 12:\n", cands.size(), samples.size());
  for (size_t i = 0; i < 12 && i < cands.size(); i++)
    std::printf("T5x   %s match=%zu (%.4f%%)\n", cands[i].name().c_str(), cands[i].match,
        100.0 * double(cands[i].match) / double(samples.size()));
  std::printf("T5x best per family (G, acc_inside, combine):\n");
  for (int G : {16, 8, 4, 2, 1})
    for (int ai = 0; ai < 2; ai++)
      for (int tr = 0; tr < 2; tr++) {
        const t5_cand* best = nullptr;
        for (const auto& c : cands)
          if (c.G == G && c.acc_inside == ai && c.tree == tr && (!best || c.match > best->match)) best = &c;
        if (best) std::printf("T5x   %s match=%zu (%.4f%%)\n", best->name().c_str(), best->match, 100.0 * double(best->match) / double(samples.size()));
      }
  // confirm the best three on every score
  for (size_t i = 0; i < 3 && i < cands.size(); i++) {
    size_t m = 0;
    cmp_stats cs;
    for (const auto& s : all) {
      for (size_t d = 0; d < D128; d++) terms[d] = to_term(s.p[d]);
      const float r = eval_cand(cands[i], terms.data());
      if (fbits(r) == fbits(s.hw)) m++;
      cs.add(s.hw, r);
    }
    std::printf("T5x full-set check: %s match=%zu/%zu (%.4f%%)%s\n", cands[i].name().c_str(), m,
        all.size(), 100.0 * double(m) / double(all.size()), m == all.size() ? "  <== bit-identical" : "");
    if (m != all.size()) cs.print("T5x   residual vs hardware:");
  }
}



// Structured candidates for F(0, 32 products) of one TDPBF16PS (p in dimension order).
constexpr int N_STRUCT = 14;
const char* struct_name[N_STRUCT] = {"exact_rne", "seq_s1", "even_odd_chains:fl(E+O)",
    "two_half_chains(pairs0-7,8-15)", "two_interleaved_chains(even k, odd k)",
    "four_quarter_chains_adjtree", "Pchain25", "Pchain26", "Pchain28", "Pchain32", "Pchain40",
    "Pchain48", "even_odd_chains_Pchain32", "even_odd_Pchains_then_round1"};
void struct_cands(const float* p, float out[N_STRUCT]) {
  {
    fx x;
    for (int d = 0; d < 32; d++) x.add(p[d]);
    out[0] = x.round();
  }
  {
    float a = 0;
    for (int k = 0; k < 16; k++) a = dp_pair(a, p[2 * k], p[2 * k + 1], S1);
    out[1] = a;
  }
  {
    float E = 0, O = 0;
    for (int k = 0; k < 16; k++) {
      E = E + p[2 * k];
      O = O + p[2 * k + 1];
    }
    out[2] = E + O;
  }
  {
    float A = 0, B = 0;
    for (int k = 0; k < 8; k++) A = dp_pair(A, p[2 * k], p[2 * k + 1], S1);
    for (int k = 8; k < 16; k++) B = dp_pair(B, p[2 * k], p[2 * k + 1], S1);
    out[3] = A + B;
  }
  {
    float A = 0, B = 0;
    for (int k = 0; k < 16; k += 2) A = dp_pair(A, p[2 * k], p[2 * k + 1], S1);
    for (int k = 1; k < 16; k += 2) B = dp_pair(B, p[2 * k], p[2 * k + 1], S1);
    out[4] = A + B;
  }
  {
    float q[4] = {0, 0, 0, 0};
    for (int k = 0; k < 16; k++) q[k / 4] = dp_pair(q[k / 4], p[2 * k], p[2 * k + 1], S1);
    out[5] = (q[0] + q[1]) + (q[2] + q[3]);
  }
  const int Ps[] = {25, 26, 28, 32, 40, 48};
  for (int i = 0; i < 6; i++) {
    fx acc;
    for (int k = 0; k < 16; k++) {
      acc.add(p[2 * k]);
      acc.add(p[2 * k + 1]);
      acc = acc.round_to_bits(Ps[i]);
    }
    out[6 + i] = acc.round();
  }
  {
    fx E, O;
    for (int k = 0; k < 16; k++) {
      E.add(p[2 * k]);
      E = E.round_to_bits(32);
      O.add(p[2 * k + 1]);
      O = O.round_to_bits(32);
    }
    out[12] = E.round() + O.round();
    fx S = E;
    S.v += O.v;
    out[13] = S.round();
  }
}


// The measured TDPBF16PS model: per instruction, E = sequential fp32 sum of the
// 16 even-dim products in k order, O = the same over the odd-dim products; the
// accumulator enters by `combine` (see T5y (b)); 0 = even chain starts at acc,
// 1 = odd chain starts at acc, 2 = acc + fl(E + O), 3 = fl(fl(acc + E) + O),
// 4 = fl(fl(acc + O) + E).
float tdpbf16ps_model(float acc, const float* prod32, int combine) {
  float E = combine == 0 ? acc : 0.0f, O = combine == 1 ? acc : 0.0f;
  for (int k = 0; k < 16; k++) {
    E = E + prod32[2 * k];
    O = O + prod32[2 * k + 1];
  }
  switch (combine) {
  case 0:
  case 1: return E + O;
  case 2: return acc + (E + O);
  case 3: return (acc + E) + O;
  default: return (acc + O) + E;
  }
}

// ---------------------------------------- T5y: isolate the inner unit and the combine
// (a) q dims 32..127 = 0: the kernel's result is F(0, 32 products of step 0).
// (b) q dims 64..127 = 0: the result is F(acc0, 32 products of step 1) with acc0
//     = the result of (a), known bit for bit.
void t5y(std::mt19937_64& g, size_t n_inst) {
  auto in = std::make_unique<qk_inst>();
  auto kt = std::make_unique<tron::k_vnni_tensor<T64, D128>>();
  alignas(64) static bf16 q_rows[amx::Q_PACK_ELEMS_2048];
  alignas(64) static float s0[H4][T64], s01[H4][T64];
  // single-step candidates
  struct c1 { const char* name; size_t match = 0; };
  std::vector<c1> cands_a = {{"exact_round1(RNE)"}, {"exact_round1(RZ)"}, {"seq_s1_from0"}, {"seq_s2_from0"},
      {"seq_s3_from0"}, {"pairsum_adjacent_tree"}, {"pairsum_halving_tree"}, {"product_adjacent_tree"},
      {"pairsum_sequential"}, {"two_halves_exact_then_add"}, {"four_quarters_exact_adjtree"}};
  std::vector<c1> cands_b = {{"acc+round1(S)"}, {"round1(acc+S)"}, {"acc+round_rz(S)"},
      {"round_rz(acc+S)"}, {"acc+round1(S) with S from two exact halves added in fp32"},
      {"E starts at acc: fl(seq(acc,even)+seq(0,odd))"}, {"O starts at acc: fl(seq(0,even)+seq(acc,odd))"},
      {"acc + fl(E+O)"}, {"fl(fl(acc+E)+O)"}, {"fl(fl(acc+O)+E)"}, {"fl(E + fl(O + acc))"}};
  // per-W aligned variants for (a): align rne/rz, final rne
  std::vector<std::pair<std::string, size_t>> cands_aw;
  const int Ws[] = {16, 20, 22, 23, 24, 25, 26, 27, 28, 30, 32, 36, 40, 48, 64};
  for (int W : Ws) for (int ar = 0; ar < N_RM; ar++) cands_aw.push_back({"aligned W=" + std::to_string(W) + " align=" + rm_name[ar] + " final=rne", 0});
  size_t n = 0;
  size_t struct_match[N_STRUCT] = {};
  std::vector<std::string> examples;
  amx::begin_region();
  for (size_t it = 0; it < n_inst; it++) {
    fill_qk(*in, g);
    for (size_t t = 0; t < T64; t++)
      tron::store_row(kt->as_view(), t, tron::k_source_row<D128>(in->k + t * D128));
    // (a)
    alignas(64) bf16 qa[H4 * D128], qb[H4 * D128];
    std::memcpy(qa, in->q, sizeof(qa));
    std::memcpy(qb, in->q, sizeof(qb));
    for (size_t h = 0; h < H4; h++)
      for (size_t d = 0; d < D128; d++) {
        if (d >= 32) qa[h * D128 + d] = bf16::from_bits(0);
        if (d >= 64) qb[h * D128 + d] = bf16::from_bits(0);
      }
    std::memset(q_rows, 0, sizeof(q_rows));
    amx::pack_q_rows_128x4(qa, q_rows);
    amx::qk_vnni_128x4(std::as_const(*kt).as_view(), q_rows, &s0[0][0], T64);
    std::memset(q_rows, 0, sizeof(q_rows));
    amx::pack_q_rows_128x4(qb, q_rows);
    amx::qk_vnni_128x4(std::as_const(*kt).as_view(), q_rows, &s01[0][0], T64);
    for (size_t h = 0; h < H4; h++)
      for (size_t t = 0; t < T64; t++) {
        n++;
        float p[D128];
        products(*in, h, t, p);
        const float hw0 = s0[h][t], hw01 = s01[h][t];
        {
          float sc[N_STRUCT];
          struct_cands(p, sc);
          for (int i = 0; i < N_STRUCT; i++)
            if (fbits(sc[i]) == fbits(hw0)) struct_match[i]++;
        }
        // ---- (a) candidates on p[0..31]
        float r[16];
        fx x;
        for (int d = 0; d < 32; d++) x.add(p[d]);
        const float ex = x.round();
        term terms[32];
        for (int d = 0; d < 32; d++) terms[d] = to_term(p[d]);
        const float ex_rz = fused_unit(terms, 32, nullptr, 120, RM_RZ, RM_RZ);
        if (fbits(ex) == fbits(hw0)) cands_a[0].match++;
        if (fbits(ex_rz) == fbits(hw0)) cands_a[1].match++;
        for (int s = 0; s < 3; s++) {
          float acc = 0.0f;
          for (int k = 0; k < 16; k++) acc = dp_pair(acc, p[2 * k], p[2 * k + 1], s);
          if (fbits(acc) == fbits(hw0)) cands_a[2 + s].match++;
        }
        for (int k = 0; k < 16; k++) r[k] = p[2 * k] + p[2 * k + 1];
        {
          float v[16];
          std::memcpy(v, r, sizeof(v));
          for (int w = 8; w >= 1; w /= 2) for (int k = 0; k < w; k++) v[k] = v[2 * k] + v[2 * k + 1];
          if (fbits(v[0]) == fbits(hw0)) cands_a[5].match++;
          std::memcpy(v, r, sizeof(v));
          for (int w = 8; w >= 1; w /= 2) for (int k = 0; k < w; k++) v[k] = v[k] + v[k + w];
          if (fbits(v[0]) == fbits(hw0)) cands_a[6].match++;
          float u[32];
          std::memcpy(u, p, sizeof(u));
          for (int w = 16; w >= 1; w /= 2) for (int k = 0; k < w; k++) u[k] = u[2 * k] + u[2 * k + 1];
          if (fbits(u[0]) == fbits(hw0)) cands_a[7].match++;
          float acc = 0.0f;
          for (int k = 0; k < 16; k++) acc = acc + r[k];
          if (fbits(acc) == fbits(hw0)) cands_a[8].match++;
          fx h1, h2;
          for (int d = 0; d < 16; d++) h1.add(p[d]);
          for (int d = 16; d < 32; d++) h2.add(p[d]);
          if (fbits(h1.round() + h2.round()) == fbits(hw0)) cands_a[9].match++;
          fx q4[4];
          for (int d = 0; d < 32; d++) q4[d / 8].add(p[d]);
          const float qa0 = q4[0].round() + q4[1].round(), qa1 = q4[2].round() + q4[3].round();
          if (fbits(qa0 + qa1) == fbits(hw0)) cands_a[10].match++;
        }
        {
          size_t i = 0;
          for (int W : Ws) for (int ar = 0; ar < N_RM; ar++) {
            if (fbits(fused_unit(terms, 32, nullptr, W, ar, RM_RNE)) == fbits(hw0)) cands_aw[i].second++;
            i++;
          }
        }
        // ---- (b) candidates: acc = hw0, products p[32..63]
        {
          fx y;
          for (int d = 32; d < 64; d++) y.add(p[d]);
          const float S = y.round();
          if (fbits(hw0 + S) == fbits(hw01)) cands_b[0].match++;
          fx z = y;
          z.add(hw0);
          if (fbits(z.round()) == fbits(hw01)) cands_b[1].match++;
          term tb[32];
          for (int d = 0; d < 32; d++) tb[d] = to_term(p[32 + d]);
          const float Srz = fused_unit(tb, 32, nullptr, 120, RM_RZ, RM_RZ);
          if (fbits(hw0 + Srz) == fbits(hw01)) cands_b[2].match++;
          const term ta = to_term(hw0);
          if (fbits(fused_unit(tb, 32, &ta, 120, RM_RZ, RM_RZ)) == fbits(hw01)) cands_b[3].match++;
          fx h1, h2;
          for (int d = 32; d < 48; d++) h1.add(p[d]);
          for (int d = 48; d < 64; d++) h2.add(p[d]);
          if (fbits(hw0 + (h1.round() + h2.round())) == fbits(hw01)) cands_b[4].match++;
          {
            float E = 0, O = 0;
            for (int k = 0; k < 16; k++) {
              E = E + p[32 + 2 * k];
              O = O + p[32 + 2 * k + 1];
            }
            float Ea = hw0, Oa = hw0;
            for (int k = 0; k < 16; k++) {
              Ea = Ea + p[32 + 2 * k];
              Oa = Oa + p[32 + 2 * k + 1];
            }
            if (fbits(Ea + O) == fbits(hw01)) cands_b[5].match++;
            if (fbits(E + Oa) == fbits(hw01)) cands_b[6].match++;
            if (fbits(hw0 + (E + O)) == fbits(hw01)) cands_b[7].match++;
            if (fbits((hw0 + E) + O) == fbits(hw01)) cands_b[8].match++;
            if (fbits((hw0 + O) + E) == fbits(hw01)) cands_b[9].match++;
            if (fbits(E + (O + hw0)) == fbits(hw01)) cands_b[10].match++;
          }
          if (examples.size() < 12 && fbits(ex) != fbits(hw0)) {
            char b[400];
            long double exact = 0;
            for (int d = 0; d < 32; d++) exact += (long double)p[d];
            std::snprintf(b, sizeof(b), "T5y example: hw0=%.9g (0x%08x) exact=%.12Lg round1=%.9g (0x%08x) seq_s1=%.9g  |products| max=%.3g min=%.3g",
                hw0, fbits(hw0), exact, ex, fbits(ex), [&] { float a = 0; for (int k = 0; k < 16; k++) a = dp_pair(a, p[2*k], p[2*k+1], S1); return a; }(),
                [&] { float m = 0; for (int d = 0; d < 32; d++) m = std::max(m, std::fabs(p[d])); return m; }(),
                [&] { float m = 1e30f; for (int d = 0; d < 32; d++) m = std::min(m, std::fabs(p[d])); return m; }());
            examples.push_back(b);
          }
        }
      }
  }
  amx::end_region();
  std::printf("T5y (a) single TDPBF16PS from a zero accumulator, F(0, 32 products), n=%zu:\n", n);
  for (auto& c : cands_a)
    std::printf("T5y   %s match=%zu (%.4f%%)%s\n", c.name, c.match, 100.0 * double(c.match) / double(n), c.match == n ? "  <== bit-identical" : "");
  for (auto& c : cands_aw)
    std::printf("T5y   %s match=%zu (%.4f%%)%s\n", c.first.c_str(), c.second, 100.0 * double(c.second) / double(n), c.second == n ? "  <== bit-identical" : "");
  std::printf("T5y (a) structured candidates, n=%zu:\n", n);
  for (int i = 0; i < N_STRUCT; i++)
    std::printf("T5y   %s match=%zu (%.4f%%)%s\n", struct_name[i], struct_match[i], 100.0 * double(struct_match[i]) / double(n), struct_match[i] == n ? "  <== bit-identical" : "");
  std::printf("T5y (b) second TDPBF16PS, F(acc0, 32 products) with acc0 the hardware's own step-0 result, n=%zu:\n", n);
  for (auto& c : cands_b)
    std::printf("T5y   %s match=%zu (%.4f%%)%s\n", c.name, c.match, 100.0 * double(c.match) / double(n), c.match == n ? "  <== bit-identical" : "");
  for (auto& e : examples) std::printf("%s\n", e.c_str());
}


// ------------------------------- T5z: controlled products, one TDPBF16PS from zero
// q_d and k_d are random bf16 (full 8-bit mantissas), so a product has up to 16
// significant bits; k_d is scaled by 2^-g_d to set the exponent gap between products.
// Only the listed dims are non-zero. hw = F(0, products) from the real kernel.
struct zexp {
  const char* name;
  std::vector<int> dims;      // non-zero dims
  std::vector<int> gap_dims;  // dims scaled by 2^-g
};
void t5z(std::mt19937_64& g) {
  auto in = std::make_unique<qk_inst>();
  auto kt = std::make_unique<tron::k_vnni_tensor<T64, D128>>();
  alignas(64) static bf16 q_rows[amx::Q_PACK_ELEMS_2048];
  alignas(64) static float s0[H4][T64];
  std::normal_distribution<float> nd(0.0f, 1.0f);
  const std::vector<zexp> exps = {
      {"same pair dims{0,1} small=dim1", {0, 1}, {1}},
      {"same pair dims{0,1} small=dim0", {0, 1}, {0}},
      {"pairs 0,1 dims{0,2} small=dim2", {0, 2}, {2}},
      {"pairs 0,15 dims{0,30} small=dim30", {0, 30}, {30}},
      {"pairs 0,8 dims{0,16} small=dim16", {0, 16}, {16}},
      {"three dims{0,2,4} small=dims2,4", {0, 2, 4}, {2, 4}},
      {"three dims{0,1,2} small=dims1,2", {0, 1, 2}, {1, 2}},
      {"three dims{0,1,3} small=dims1,3", {0, 1, 3}, {1, 3}},
      {"three dims{0,2,3} small=dims2,3", {0, 2, 3}, {2, 3}},
      {"three dims{1,2,3} small=dims2,3", {1, 2, 3}, {2, 3}},
      {"three dims{0,16,17} small=16,17", {0, 16, 17}, {16, 17}},
      {"four dims{0,1,2,3} small=1,2,3", {0, 1, 2, 3}, {1, 2, 3}},
      {"four dims{0,1,2,3} small=2,3", {0, 1, 2, 3}, {2, 3}},
      {"five dims{0,2,4,6,8} small=2..8", {0, 2, 4, 6, 8}, {2, 4, 6, 8}},
      {"all 32 dims, small=dims 2..31", {}, {}},
      {"all 32 dims, small=odd dims", {}, {-1}},
  };
  const int gaps[] = {0, 4, 8, 12, 16, 20, 24, 26, 28, 32};
  const char** cand_names = struct_name;
  constexpr int NC = N_STRUCT;
  amx::begin_region();
  for (const auto& e : exps) {
    std::vector<int> dims = e.dims, gd = e.gap_dims;
    if (dims.empty()) {
      const bool odd_small = !gd.empty();
      gd.clear();
      for (int d = 0; d < 32; d++) dims.push_back(d);
      for (int d = 0; d < 32; d++)
        if (odd_small ? (d % 2 == 1) : (d >= 2)) gd.push_back(d);
    }
    std::printf("T5z %s: per gap g, match %% of candidates [", e.name);
    for (int c = 0; c < NC; c++) std::printf("%s%s", c ? "," : "", cand_names[c]);
    std::printf("]\n");
    for (int gap : gaps) {
      size_t match[NC] = {}, n = 0;
      for (int rep = 0; rep < 4; rep++) {
        for (auto& x : in->k) x = bf16::from_bits(0);
        for (auto& x : in->q) x = bf16::from_bits(0);
        for (size_t h = 0; h < H4; h++)
          for (int d : dims) in->q[h * D128 + d] = mk(nd(g));
        for (size_t t = 0; t < T64; t++)
          for (int d : dims) {
            const bool small = std::find(gd.begin(), gd.end(), d) != gd.end();
            in->k[t * D128 + d] = mk(std::ldexp(nd(g), small ? -gap : 0));
          }
        for (size_t t = 0; t < T64; t++)
          tron::store_row(kt->as_view(), t, tron::k_source_row<D128>(in->k + t * D128));
        std::memset(q_rows, 0, sizeof(q_rows));
        amx::pack_q_rows_128x4(in->q, q_rows);
        amx::qk_vnni_128x4(std::as_const(*kt).as_view(), q_rows, &s0[0][0], T64);
        for (size_t h = 0; h < H4; h++)
          for (size_t t = 0; t < T64; t++) {
            float p[D128];
            products(*in, h, t, p);
            term terms[32];
            for (int d = 0; d < 32; d++) terms[d] = to_term(p[d]);
            const float hw = s0[h][t];
            float c[NC];
            struct_cands(p, c);
            (void)terms;
            for (int i = 0; i < NC; i++)
              if (fbits(c[i]) == fbits(hw)) match[i]++;
            n++;
          }
      }
      std::printf("T5z   g=%2d n=%zu:", gap, n);
      for (int i = 0; i < NC; i++) std::printf(" %5.1f", 100.0 * double(match[i]) / double(n));
      std::printf("\n");
    }
  }
  amx::end_region();
}


// ------------------------------------------------- T9: AVX-512 kernels in the AMX order
// Proof of concept: AVX-512 readers that reproduce the AMX kernels bit for bit
// with the measured TDPBF16PS rule (per instruction of 16 pairs: E = fp32 chain
// over the even products from 0, O = the same over the odd products,
// acc = acc + fl(E + O)). Each product is formed exactly by an FMA whose
// addend is the running chain, so every add is one RNE rounding.

// (a) QK over the VNNI K plane, same signature and lane layout as
// k_vnni::qk_group<kv_mul,bf16>: one token per lane, 16-token blocks, the
// panel (step, block) holds 16 dim-pair rows of 16 dwords.
template <size_t kv_mul>
void qk_group_amxorder(tron::k_vnni_view<const bf16, T64, D128> k_page, const bf16* q,
    uint64_t live, float* s, size_t s_stride) noexcept {
  using namespace tron::k_vnni;
  const bf16* const plane = tron::detail::k_vnni_access::plane(k_page);
  const __m512i hi_mask = _mm512_set1_epi32(int(HIGH_HALF_0XFFFF0000));
  for (size_t c = 0; c < TOKEN_BLOCKS_4; ++c) {
    const __mmask16 mask = __mmask16(live >> (c * BLOCK_TOKENS_16));
    if (mask == 0) continue;
    __m512 acc[kv_mul];
    for (size_t h = 0; h < kv_mul; ++h) acc[h] = _mm512_setzero_ps();
    for (size_t step = 0; step < DIM_STEPS_4; ++step) {
      const bf16* panel = plane + (step * TOKEN_BLOCKS_4 + c) * PANEL_ELEMS_512;
      __m512 E[kv_mul], O[kv_mul];
      for (size_t h = 0; h < kv_mul; ++h) {
        E[h] = _mm512_setzero_ps();
        O[h] = _mm512_setzero_ps();
      }
      for (size_t dp = 0; dp < STEP_PAIRS_16; ++dp) {
        const __m512i k_pairs = _mm512_maskz_loadu_epi32(mask, panel + dp * ROW_ELEMS_32);
        const __m512 k_even = _mm512_castsi512_ps(_mm512_slli_epi32(k_pairs, BF16_BITS_16));
        const __m512 k_odd = _mm512_castsi512_ps(_mm512_and_si512(k_pairs, hi_mask));
        const size_t d = step * STEP_DIMS_32 + PAIR_2 * dp;
        for (size_t h = 0; h < kv_mul; ++h) {
          const float qe = bits2f(q[h * D128 + d].to_bits());
          const float qo = bits2f(q[h * D128 + d + 1].to_bits());
          E[h] = _mm512_fmadd_ps(_mm512_set1_ps(qe), k_even, E[h]);
          O[h] = _mm512_fmadd_ps(_mm512_set1_ps(qo), k_odd, O[h]);
        }
      }
      for (size_t h = 0; h < kv_mul; ++h) acc[h] = _mm512_add_ps(acc[h], _mm512_add_ps(E[h], O[h]));
    }
    for (size_t h = 0; h < kv_mul; ++h)
      _mm512_mask_storeu_ps(s + h * s_stride + c * BLOCK_TOKENS_16, mask, acc[h]);
  }
}

// (b) PV over the V pair rows: P rounded RNE to bf16 and widened (the bits of
// the AMX kernel's P tile); two "instructions" of 16 token pairs for a 64-token
// page; out[0..127] for one query row.
void scaled_v_amxorder(const bf16* plane, const float* p_row, float out[D128]) noexcept {
  const __m512i hi_mask = _mm512_set1_epi32(int(0xffff0000u));
  __m512 acc[8];
  for (int c = 0; c < 8; c++) acc[c] = _mm512_setzero_ps();
  for (int ins = 0; ins < 2; ins++) {
    __m512 E[8], O[8];
    for (int c = 0; c < 8; c++) {
      E[c] = _mm512_setzero_ps();
      O[c] = _mm512_setzero_ps();
    }
    for (int k = 0; k < 16; k++) {
      const int pair = ins * 16 + k;
      const __m512 pe = _mm512_set1_ps(bf16r(p_row[2 * pair]));
      const __m512 po = _mm512_set1_ps(bf16r(p_row[2 * pair + 1]));
      const bf16* row = plane + pair * 2 * D128;
      for (int c = 0; c < 8; c++) {
        const __m512i v = _mm512_load_si512(row + 2 * 16 * c);
        const __m512 v_even = _mm512_castsi512_ps(_mm512_slli_epi32(v, 16));
        const __m512 v_odd = _mm512_castsi512_ps(_mm512_and_si512(v, hi_mask));
        E[c] = _mm512_fmadd_ps(pe, v_even, E[c]);
        O[c] = _mm512_fmadd_ps(po, v_odd, O[c]);
      }
    }
    for (int c = 0; c < 8; c++) acc[c] = _mm512_add_ps(acc[c], _mm512_add_ps(E[c], O[c]));
  }
  for (int c = 0; c < 8; c++) _mm512_storeu_ps(out + 16 * c, acc[c]);
}

// Make the compiler assume `p` is read after the call (defeats dead-store
// elimination of outputs nobody reads).
inline void escape(const void* p) {
  asm volatile("" : : "r"(p) : "memory");
}
template <typename F>
double time_ns_per_call(F&& f, int warm, int iters) {
  for (int i = 0; i < warm; i++) f();
  const auto t0 = std::chrono::steady_clock::now();
  for (int i = 0; i < iters; i++) f();
  const auto t1 = std::chrono::steady_clock::now();
  return std::chrono::duration<double, std::nano>(t1 - t0).count() / iters;
}

void t9() {
  // (a) the same 2000 QK instances as T1-T5 (same seed, same draw order)
  std::mt19937_64 g(SEED);
  auto in = std::make_unique<qk_inst>();
  auto kt = std::make_unique<tron::k_vnni_tensor<T64, D128>>();
  alignas(64) static bf16 q_rows[amx::Q_PACK_ELEMS_2048];
  alignas(64) static float s_vnni[H4][T64], s_new[H4][T64];
  cmp_stats a;
  amx::begin_region();
  for (size_t it = 0; it < N_QK_INSTANCES; it++) {
    fill_qk(*in, g);
    for (size_t t = 0; t < T64; t++)
      tron::store_row(kt->as_view(), t, tron::k_source_row<D128>(in->k + t * D128));
    std::memset(q_rows, 0, sizeof(q_rows));
    amx::pack_q_rows_128x4(in->q, q_rows);
    amx::qk_vnni_128x4(std::as_const(*kt).as_view(), q_rows, &s_vnni[0][0], T64);
    std::memset(s_new, 0xff, sizeof(s_new));
    qk_group_amxorder<H4>(std::as_const(*kt).as_view(), in->q, ~uint64_t{0}, &s_new[0][0], T64);
    for (size_t h = 0; h < H4; h++)
      for (size_t t = 0; t < T64; t++) a.add(s_vnni[h][t], s_new[h][t]);
  }
  a.print("T9a qk_group_amxorder<4> (AVX-512, AMX order) vs qk_vnni_128x4:");
  // (b) PV: 2000 instances, fp32 softmax-like P, V ~ bf16(N(0,1))
  std::mt19937_64 gp(SEED + 9);
  auto pin = std::make_unique<pv_inst>();
  auto owner = std::make_unique<v_owner_t>();
  alignas(64) static float o_amx[16 * D128];
  std::normal_distribution<float> nd(0.0f, 1.0f);
  cmp_stats b;
  for (size_t it = 0; it < N_PV_INSTANCES; it++) {
    for (auto& x : pin->v) x = mk(nd(gp));
    fill_v_plane(*pin, *owner);
    fill_p(*pin, gp, T64, false);
    amx::weights_times_v_128x4(std::as_const(*owner).as_view(), &pin->p[0][0], T64, o_amx);
    const bf16* plane = tron::detail::v_vnni_access::plane(std::as_const(*owner).as_view());
    for (size_t h = 0; h < H4; h++) {
      float o_new[D128];
      scaled_v_amxorder(plane, pin->p[h], o_new);
      for (size_t d = 0; d < D128; d++) b.add(o_amx[h * D128 + d], o_new[d]);
    }
  }
  b.print("T9b scaled_v_amxorder (AVX-512, AMX order, RNE P) vs weights_times_v_128x4:");
  // (c) cost per (query group, page), one instance resident in cache, single thread
  {
    const bf16* vplane = tron::detail::v_vnni_access::plane(std::as_const(*owner).as_view());
    alignas(64) static float s_a[H4][T64], s_b[H4][T64], o_a[H4][D128], o_b[H4][D128];
    constexpr int WARM = 2000, ITERS = 20000;
    // pin to one CPU of the allowed set (the lowest), so the timings come from one core
    int cpu_used = -1;
    {
      cpu_set_t cs;
      CPU_ZERO(&cs);
      if (sched_getaffinity(0, sizeof(cs), &cs) == 0) {
        for (int c = 0; c < CPU_SETSIZE; c++)
          if (CPU_ISSET(c, &cs)) { cpu_used = c; break; }
        if (cpu_used >= 0) {
          cpu_set_t one;
          CPU_ZERO(&one);
          CPU_SET(cpu_used, &one);
          if (sched_setaffinity(0, sizeof(one), &one) != 0) cpu_used = -2;
        }
      }
    }
    const double t_reader = time_ns_per_call([&] {
      escape(in->q); escape(kt.get());
      tron::k_vnni::qk_group<H4, bf16>(std::as_const(*kt).as_view(), in->q, ~uint64_t{0}, &s_a[0][0], T64);
      escape(s_a);
    }, WARM, ITERS);
    const double t_qk_new = time_ns_per_call([&] {
      escape(in->q); escape(kt.get());
      qk_group_amxorder<H4>(std::as_const(*kt).as_view(), in->q, ~uint64_t{0}, &s_b[0][0], T64);
      escape(s_b);
    }, WARM, ITERS);
    const double t_qk_amx = time_ns_per_call([&] {
      escape(in->q); escape(kt.get());
      amx::pack_q_rows_128x4(in->q, q_rows);
      amx::qk_vnni_128x4(std::as_const(*kt).as_view(), q_rows, &s_vnni[0][0], T64);
      escape(s_vnni);
    }, WARM, ITERS);
    const double t_qk_amx_nopack = time_ns_per_call([&] {
      escape(q_rows); escape(kt.get());
      amx::qk_vnni_128x4(std::as_const(*kt).as_view(), q_rows, &s_vnni[0][0], T64);
      escape(s_vnni);
    }, WARM, ITERS);
    const double t_pv_avx = time_ns_per_call([&] {
      escape(pin.get()); escape(vplane);
      for (size_t h = 0; h < H4; h++) {
        avx_scaled_v(vplane, pin->p[h], T64, o_a[h]);
        escape(o_a[h]);
      }
    }, WARM, ITERS);
    const double t_pv_new = time_ns_per_call([&] {
      escape(pin.get()); escape(vplane);
      for (size_t h = 0; h < H4; h++) {
        scaled_v_amxorder(vplane, pin->p[h], o_b[h]);
        escape(o_b[h]);
      }
    }, WARM, ITERS);
    const double t_pv_amx = time_ns_per_call([&] {
      escape(pin.get()); escape(vplane);
      amx::weights_times_v_128x4(std::as_const(*owner).as_view(), &pin->p[0][0], T64, o_amx);
      escape(o_amx);
    }, WARM, ITERS);
    std::printf("T9c timing cpu=%d (pinned inside the taskset mask; -1 = not pinned)\n", cpu_used);
    std::printf("T9c cost per (query group = 4 heads, 64-token page), single thread, %d calls after %d warm-up, data in cache:\n", ITERS, WARM);
    std::printf("T9c   QK  k_vnni::qk_group<4,bf16> (current VNNI reader)      %8.1f ns\n", t_reader);
    std::printf("T9c   QK  qk_group_amxorder<4> (AMX order)                     %8.1f ns  ratio vs reader %.2fx\n", t_qk_new, t_qk_new / t_reader);
    std::printf("T9c   QK  qk_vnni_128x4 (AMX kernel, with pack_q_rows)         %8.1f ns  (kernel only %.1f ns)\n", t_qk_amx, t_qk_amx_nopack);
    std::printf("T9c   PV  avx_scaled_v x4 heads (current AVX loop)            %8.1f ns\n", t_pv_avx);
    std::printf("T9c   PV  scaled_v_amxorder x4 heads (AMX order)              %8.1f ns  ratio vs AVX loop %.2fx\n", t_pv_new, t_pv_new / t_pv_avx);
    std::printf("T9c   PV  weights_times_v_128x4 (AMX kernel, 4 heads)          %8.1f ns\n", t_pv_amx);
  }
  amx::end_region();
}

}  // namespace

int main() {
  const auto t_start = std::chrono::steady_clock::now();
  std::printf("ktest: tron QK/PV kernel bit-exactness measurements (issue #4444)\n");
  std::printf("seed=%llu qk_instances=%zu pv_instances=%zu\n", (unsigned long long)SEED,
      N_QK_INSTANCES, N_PV_INSTANCES);
  const unsigned csr0 = _mm_getcsr();
  std::printf("MXCSR at start=0x%04x (FTZ=%u DAZ=%u) - tron sets neither\n", csr0,
      (csr0 >> 15) & 1u, (csr0 >> 6) & 1u);
  const bool amx_ok = amx::available();
  std::printf("amx available()=%s\n", amx_ok ? "yes" : "NO (AMX sections skipped)");

  std::mt19937_64 g(SEED);

  // ------------------------------------------------------------------ T0
  {
    std::normal_distribution<float> nd(0.0f, 1.0f);
    std::uniform_int_distribution<int> ue(-6, 6);
    for (int daz = 0; daz < 2; daz++) {
      if (daz) _mm_setcsr(csr0 | 0x8040u);  // FTZ | DAZ
      else _mm_setcsr(csr0);
      size_t match[N_SEM] = {}, n = 0, disc12 = 0, disc13 = 0, disc1g = 0;
      std::mt19937_64 g0(SEED + 1);
      for (size_t i = 0; i < 2000000; i++) {
        const float acc = std::ldexp(nd(g0), ue(g0));
        const bf16 ae = mk(nd(g0)), ao = mk(nd(g0)), be = mk(nd(g0)), bo = mk(nd(g0));
        const uint32_t a_pair = uint32_t(ae.to_bits()) | (uint32_t(ao.to_bits()) << 16);
        const uint32_t b_pair = uint32_t(be.to_bits()) | (uint32_t(bo.to_bits()) << 16);
        const __m512 r = _mm512_dpbf16_ps(_mm512_set1_ps(acc),
            (__m512bh)_mm512_set1_epi32(int(a_pair)), (__m512bh)_mm512_set1_epi32(int(b_pair)));
        const float hw = _mm512_cvtss_f32(r);
        const float pe = val(ae) * val(be), po = val(ao) * val(bo);
        float c[N_SEM];
        for (int s = 0; s < N_SEM; s++) {
          c[s] = dp_pair(acc, pe, po, s);
          if (fbits(c[s]) == fbits(hw)) match[s]++;
        }
        if (fbits(c[S1]) != fbits(c[S2])) disc12++;
        if (fbits(c[S1]) != fbits(c[S3])) disc13++;
        if (fbits(c[S1]) != fbits(c[SG])) disc1g++;
        n++;
      }
      std::printf("T0 _mm512_dpbf16_ps lane semantics (MXCSR FTZ/DAZ=%s) n=%zu:", daz ? "on" : "off", n);
      for (int s = 0; s < N_SEM; s++)
        std::printf(" %s=%zu(%.4f%%)", sem_name[s], match[s], 100.0 * double(match[s]) / double(n));
      std::printf(" | cases s1!=s2:%zu s1!=s3:%zu s1!=sg:%zu\n", disc12, disc13, disc1g);
    }
    _mm_setcsr(csr0);
  }

  // ------------------------------------------------------------ QK sections
  {
    auto in = std::make_unique<qk_inst>();
    auto kt = std::make_unique<tron::k_vnni_tensor<T64, D128>>();
    alignas(64) static bf16 q_rows[amx::Q_PACK_ELEMS_2048];
    alignas(64) static bf16 q_packed[amx::Q_PACK_ELEMS_2048];
    alignas(64) static float s_vnni[H4][T64], s_row[H4][T64], s_reader[H4][T64], s_dot[H4][T64];
    cmp_stats t1, t1b, t2;
    size_t t3_match[N_SEM][N_RED] = {}, t4_match[N_SEM] = {}, t5_match[N_AMX_CAND] = {}, n = 0;
    size_t fx_bad = 0;
    cmp_stats t5_best;  // filled against the best-matching candidate after a first pass
    int t5_best_cand = -1;
    std::vector<t5_sample> t5_all;
    t5_all.reserve(N_QK_INSTANCES * H4 * T64);
    if (amx_ok) amx::begin_region();
    for (size_t it = 0; it < N_QK_INSTANCES; it++) {
      fill_qk(*in, g);
      for (size_t t = 0; t < T64; t++) {
        tron::store_row(kt->as_view(), t, tron::k_source_row<D128>(in->k + t * D128));
      }
      std::memset(s_vnni, 0xff, sizeof(s_vnni));
      std::memset(s_row, 0xff, sizeof(s_row));
      std::memset(s_reader, 0xff, sizeof(s_reader));
      if (amx_ok) {
        std::memset(q_rows, 0, sizeof(q_rows));
        std::memset(q_packed, 0, sizeof(q_packed));
        amx::pack_q_rows_128x4(in->q, q_rows);
        amx::pack_q_group_128x4(in->q, q_packed);
        amx::qk_vnni_128x4(std::as_const(*kt).as_view(), q_rows, &s_vnni[0][0], T64);
        amx::qk_rowmajor_128x4(
            tron::const_native_k_view<T64, D128>{in->k}, q_packed, &s_row[0][0], T64);
      }
      tron::k_vnni::qk_group<H4, bf16>(std::as_const(*kt).as_view(), in->q, ~uint64_t{0},
          &s_reader[0][0], T64);
      for (size_t h = 0; h < H4; h++) {
        tron::const_view<bf16, true, false, tron::seq<D128>> qv{in->q + h * D128};
        tron::dotter<bf16, D128> dot(qv);
        for (size_t t = 0; t < T64; t++) {
          tron::const_view<bf16, true, false, tron::seq<D128>> kv{in->k + t * D128};
          s_dot[h][t] = dot(kv);
        }
      }
      for (size_t h = 0; h < H4; h++) {
        for (size_t t = 0; t < T64; t++) {
          n++;
          float p[D128];
          products(*in, h, t, p);
          if (amx_ok) {
            t1.add(s_vnni[h][t], s_reader[h][t]);
            t1b.add(s_vnni[h][t], s_row[h][t]);
            t2.add(s_vnni[h][t], s_dot[h][t]);
            for (int c = 0; c < N_AMX_CAND; c++) {
              if (fbits(ref_amx(p, c)) == fbits(s_vnni[h][t])) t5_match[c]++;
            }
            {
              fx x;
              for (size_t d = 0; d < D128; d++) x.add(p[d]);
              if (x.inexact || x.overflow) fx_bad++;
            }
            {
              t5_sample smp;
              std::memcpy(smp.p, p, sizeof(smp.p));
              smp.hw = s_vnni[h][t];
              t5_all.push_back(smp);
            }
          }
          for (int s = 0; s < N_SEM; s++) {
            for (int r = 0; r < N_RED; r++) {
              if (fbits(ref_dotter(p, s, r)) == fbits(s_dot[h][t])) t3_match[s][r]++;
            }
            if (fbits(ref_seq(p, s)) == fbits(s_reader[h][t])) t4_match[s]++;
          }
        }
      }
    }
    if (amx_ok) amx::end_region();
    if (amx_ok) {
      t1.print("T1 qk_vnni_128x4(AMX) vs k_vnni::qk_group<4,bf16>(AVX VNNI reader):");
      t1b.print("T1b qk_rowmajor_128x4 vs qk_vnni_128x4:");
      t2.print("T2 dotter<bf16,128>(AVX row-major) vs qk_vnni_128x4(AMX):");
    } else {
      std::printf("T1/T1b/T2/T5 skipped: AMX unavailable\n");
    }
    std::printf("T3 dotter<bf16,128> vs scalar reference in the dotter's order, n=%zu:\n", n);
    for (int s = 0; s < N_SEM; s++)
      for (int r = 0; r < N_RED; r++)
        std::printf("T3   lane=%s reduce=%s match=%zu (%.4f%%)%s\n", sem_name[s], red_name[r],
            t3_match[s][r], 100.0 * double(t3_match[s][r]) / double(n),
            t3_match[s][r] == n ? "  <== bit-identical" : "");
    std::printf("T4 k_vnni::qk_group<4,bf16> vs scalar sequential reference (64 pairs in dimension order), n=%zu:\n", n);
    for (int s = 0; s < N_SEM; s++)
      std::printf("T4   %s match=%zu (%.4f%%)%s\n", sem_name[s], t4_match[s],
          100.0 * double(t4_match[s]) / double(n), t4_match[s] == n ? "  <== bit-identical" : "");
    if (amx_ok) {
      std::printf("T5 qk_vnni_128x4 (4 x TDPBF16PS, 16 pairs each) vs scalar references, n=%zu (exact-accumulator flags=%zu):\n", n, fx_bad);
      for (int c = 0; c < N_AMX_CAND; c++) {
        std::printf("T5   %s match=%zu (%.4f%%)%s\n", amx_cand_name[c], t5_match[c],
            100.0 * double(t5_match[c]) / double(n), t5_match[c] == n ? "  <== bit-identical" : "");
        if (t5_best_cand < 0 || t5_match[c] > t5_match[t5_best_cand]) t5_best_cand = c;
      }
      std::printf("T5 best candidate: %s\n", amx_cand_name[t5_best_cand]);
      {  // where does the best simple candidate miss? sign of the miss relative to the magnitude
        size_t lo = 0, hi = 0;
        cmp_stats cs;
        for (const auto& s : t5_all) {
          const float r = ref_amx(s.p, t5_best_cand);
          cs.add(s.hw, r);
          if (fbits(r) != fbits(s.hw)) (std::fabs(s.hw) < std::fabs(r) ? lo : hi)++;
        }
        cs.print("T5 residual of best simple candidate vs hardware:");
        std::printf("T5   misses: |hw| < |cand| in %zu, |hw| > |cand| in %zu\n", lo, hi);
      }
      const size_t n_sub = std::min<size_t>(t5_all.size(), 100 * H4 * T64);
      std::vector<t5_sample> sub(t5_all.begin(), t5_all.begin() + n_sub);
      t5_search(sub, t5_all);
      t5y(g, 500);
      t5z(g);
      {
        const char* cmb[5] = {"even chain starts at acc", "odd chain starts at acc", "acc+fl(E+O)", "fl(fl(acc+E)+O)", "fl(fl(acc+O)+E)"};
        for (int c = 0; c < 5; c++) {
          cmp_stats cs;
          for (const auto& s : t5_all) {
            float acc = 0.0f;
            for (int st = 0; st < 4; st++) acc = tdpbf16ps_model(acc, s.p + 32 * st, c);
            cs.add(s.hw, acc);
          }
          char label[200];
          std::snprintf(label, sizeof(label), "T5m qk_vnni_128x4 vs even/odd-chain model, combine=%s:", cmb[c]);
          cs.print(label);
        }
      }
    }
  }

  // ------------------------------------------------------------ PV sections
  if (amx_ok) {
    auto in = std::make_unique<pv_inst>();
    auto owner = std::make_unique<v_owner_t>();
    alignas(64) static float o_amx[16 * D128];
    alignas(64) static float p_rne[H4][T64];
    cmp_stats t6a, t6b, t6c;
    std::normal_distribution<float> nd(0.0f, 1.0f);
    amx::begin_region();
    for (size_t it = 0; it < N_PV_INSTANCES; it++) {
      for (auto& x : in->v) x = mk(nd(g));
      fill_v_plane(*in, *owner);
      const bf16* plane = tron::detail::v_vnni_access::plane(std::as_const(*owner).as_view());
      // (a) P exactly representable in bf16
      fill_p(*in, g, T64, true);
      amx::weights_times_v_128x4(std::as_const(*owner).as_view(), &in->p[0][0], T64, o_amx);
      for (size_t h = 0; h < H4; h++) {
        float o_avx[D128];
        avx_scaled_v(plane, in->p[h], T64, o_avx);
        for (size_t d = 0; d < D128; d++) t6a.add(o_amx[h * D128 + d], o_avx[d]);
      }
      // (b) general fp32 P: AVX truncation vs AMX RNE; (c) AVX fed RNE-rounded P
      fill_p(*in, g, T64, false);
      amx::weights_times_v_128x4(std::as_const(*owner).as_view(), &in->p[0][0], T64, o_amx);
      for (size_t h = 0; h < H4; h++) {
        float o_avx[D128], o_avx_rne[D128];
        avx_scaled_v(plane, in->p[h], T64, o_avx);
        for (size_t t = 0; t < T64; t++) p_rne[h][t] = bf16r(in->p[h][t]);
        avx_scaled_v(plane, p_rne[h], T64, o_avx_rne);
        for (size_t d = 0; d < D128; d++) {
          t6b.add(o_amx[h * D128 + d], o_avx[d]);
          t6c.add(o_amx[h * D128 + d], o_avx_rne[d]);
        }
      }
    }
    t6a.print("T6a H-B weights_times_v_128x4 vs AVX scaled_v loop, P bf16-exact, 64 tokens:");
    {  // T6d: the PV kernel vs the even/odd-chain TDPBF16PS model (2 instructions of 16 token pairs)
      const char* cmb[5] = {"even chain starts at acc", "odd chain starts at acc", "acc+fl(E+O)", "fl(fl(acc+E)+O)", "fl(fl(acc+O)+E)"};
      cmp_stats cs[5];
      std::mt19937_64 g6(SEED + 7);
      for (size_t it = 0; it < 200; it++) {
        for (auto& x : in->v) x = mk(nd(g6));
        fill_v_plane(*in, *owner);
        fill_p(*in, g6, T64, false);
        amx::weights_times_v_128x4(std::as_const(*owner).as_view(), &in->p[0][0], T64, o_amx);
        for (size_t h = 0; h < H4; h++)
          for (size_t d = 0; d < D128; d++) {
            float prod[T64];
            for (size_t t = 0; t < T64; t++) prod[t] = bf16r(in->p[h][t]) * val(in->v[t * D128 + d]);
            for (int c = 0; c < 5; c++) {
              float acc = 0.0f;
              for (int st = 0; st < 2; st++) acc = tdpbf16ps_model(acc, prod + 32 * st, c);
              cs[c].add(o_amx[h * D128 + d], acc);
            }
          }
      }
      for (int c = 0; c < 5; c++) {
        char label[200];
        std::snprintf(label, sizeof(label), "T6d weights_times_v_128x4 vs even/odd-chain model (RNE P), combine=%s:", cmb[c]);
        cs[c].print(label);
      }
    }
    t6b.print("T6b weights_times_v_128x4 (RNE P) vs AVX scaled_v loop (truncated P), fp32 softmax-like P:");
    t6c.print("T6c weights_times_v_128x4 vs AVX scaled_v loop fed RNE-rounded P:");
    // T7 / T8
    accuracy_section("T7a", T64, g, 1.0f, N_PV_INSTANCES);
    accuracy_section("T7b", T64, g, 0.1f, N_PV_INSTANCES);
    accuracy_section("T8a", 16, g, 1.0f, N_PV_INSTANCES / 4);
    accuracy_section("T8b", 1, g, 1.0f, N_PV_INSTANCES / 4);
    amx::end_region();
  } else {
    std::printf("T6/T7/T8 skipped: AMX unavailable\n");
  }
  if (amx_ok) t9();
  const double secs =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - t_start).count();
  std::printf("done in %.1f s\n", secs);
  return 0;
}
