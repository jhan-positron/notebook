// unit_bench.cpp - the attention "unit" of Tron's CPU software attention,
// transcribed from the production code, run outside Tron.
//
// One unit = one query token's group of 4 query heads against one 64-token
// page of one KV head, including the softmax pieces and the running-state
// update (Tron: apply_page_tok in h/tron/models/self_attention.hpp).
//
// Two code paths, both transcribed step by step (fence branch 8fd1e7798d):
//   avx : dotter<bf16,128> QK, per-head scale/max/exp/sum, scaled_v_expr PV,
//         state update (the AVX "dotter" path, used with TRON_AMX_DISABLE=1).
//   amx : qk_mirror_128x4 + score copy, per-head softmax pieces, P pack,
//         weights_times_v_128x4, output copy + state update
//         (the arena-mirror AMX path).
//
// Memory is laid out as Tron's KV cache lays it out:
//   canonical arena : blocks of 32 KiB (K plane 16 KiB, then V plane 16 KiB),
//                     block index = ((layer * 8 + head) * n_pages + page)
//   K mirror arena  : planes of 16 KiB, same index, on 4 KiB pages
// The planner's assignment (finish_sw_plan with equal worker speeds) is
// reproduced: the (head, page) list of one layer is walked in order and cut
// into equal-work runs, advancing at most one worker per page.
//
// Per-phase timers use rdtsc where the fence-branch probe puts its stamps
// (7613-7619): on the AVX path QK / common (softmax pieces + state update,
// as Tron's cyc_common_dotter) / PV; on the AMX path QK / softmax / PV / state.
// So the split is comparable with exec/results/single-attn-20260901/summary.json.
//
// Build:  g++ -O3 -std=c++17 -march=x86-64-v4 -mavx512bf16 -mamx-tile -mamx-bf16 -pthread
// Usage:  unit_bench --variant avx|amx --pages P --threads N --cpus LIST
//                    [--passes 300] [--warmup 20] [--hot] [--huge thp|1g|none]
//                    [--shuffle] [--json FILE] [--check]
//   --pages P    pages per (layer, head): 130 = prompt 8192 at the median
//                decode pass, 34 = prompt 2048, 6 = prompt 256.
//   --hot        every unit reads the same one page (compute-only measure;
//                the page plus the thread's buffers, about 70 KiB, sit in L2).
//   --passes 0   fill only (control for perf stat).
//   --check      validate the path against a scalar reference and exit.
// Prints "RUN-START <epoch s>" / "RUN-END <epoch s>" on stderr around the
// timed phase so external samplers (turbostat, perf) can be windowed.

#include <immintrin.h>
#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#define XFEATURE_XTILEDATA 18
#ifndef MAP_HUGE_1GB
#define MAP_HUGE_1GB (30 << 26)
#endif

// ---------------------------------------------------------------- geometry
static constexpr int N_LAYERS = 36;     // qwen-3-4b decoder layers
static constexpr int N_KV_HEADS = 8;    // KV heads per layer
static constexpr int GROUP = 4;         // query heads per KV head (kv_mul)
static constexpr int PAGE = 64;         // tokens per page
static constexpr int HD = 128;          // head size
static constexpr int TILE_ROWS = 16;
static constexpr int DIM_STEP = 32;
static constexpr size_t PLANE_BYTES = size_t(PAGE) * HD * 2;  // 16 KiB
static constexpr size_t BLOCK_BYTES = 2 * PLANE_BYTES;        // 32 KiB (K, then V)
static constexpr float SCALE = 0.088388347f;                  // 1/sqrt(128)

using bf16 = uint16_t;

// ------------------------------------------------------------ small helpers
static inline uint64_t rdtsc() {
  unsigned lo, hi;
  __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
  return (uint64_t(hi) << 32) | lo;
}
static double now_s() {
  timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + t.tv_nsec * 1e-9;
}
static double epoch_s() {
  timespec t;
  clock_gettime(CLOCK_REALTIME, &t);
  return t.tv_sec + t.tv_nsec * 1e-9;
}
static inline float b2f(bf16 v) {
  uint32_t u = uint32_t(v) << 16;
  float f;
  std::memcpy(&f, &u, 4);
  return f;
}
static inline bf16 f2b(float f) {  // round to nearest even
  uint32_t u;
  std::memcpy(&u, &f, 4);
  uint32_t lsb = (u >> 16) & 1;
  u += 0x7fff + lsb;
  return bf16(u >> 16);
}
static uint64_t splitmix(uint64_t& s) {
  uint64_t z = (s += 0x9e3779b97f4a7c15ull);
  z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
  z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
  return z ^ (z >> 31);
}

// Tron's exp (h/tron/simd/fp32.hpp:881, 896-901, 982-992): Estrin 7th degree,
// sollya coefficients, floor / fma / scalef, zero below exp_min. Constants
// copied digit for digit.
static const float EXP_MIN = -88.3762626647949f;
static const float E7_2 = 0.5f, E7_3 = 0.16666664183139801025390625f,
                   E7_4 = 4.16664592921733856201171875e-2f, E7_5 = 8.333896286785602569580078125e-3f,
                   E7_6 = 1.39354146085679531097412109375e-3f, E7_7 = 1.95693559362553060054779052734375e-4f;
static inline __m512 tron_exp(__m512 x) {
  __m512 fx = _mm512_floor_ps(_mm512_fmadd_ps(x, _mm512_set1_ps(float(M_LOG2E)), _mm512_set1_ps(0.5f)));
  __mmask16 kz = _mm512_cmp_ps_mask(x, _mm512_set1_ps(EXP_MIN), _CMP_NLT_UQ);
  x = _mm512_fmadd_ps(fx, _mm512_set1_ps(float(-M_LN2)), x);
  __m512 x2 = _mm512_mul_ps(x, x);
  __m512 y = _mm512_fmadd_ps(x, _mm512_set1_ps(E7_7), _mm512_set1_ps(E7_6));
  y = _mm512_fmadd_ps(y, x2, _mm512_fmadd_ps(x, _mm512_set1_ps(E7_5), _mm512_set1_ps(E7_4)));
  y = _mm512_fmadd_ps(y, x2, _mm512_fmadd_ps(x, _mm512_set1_ps(E7_3), _mm512_set1_ps(E7_2)));
  y = _mm512_fmadd_ps(y, x2, _mm512_add_ps(x, _mm512_set1_ps(1.0f)));
  return _mm512_maskz_scalef_ps(kz, y, fx);
}

// ------------------------------------------------------------- AMX plumbing
struct tile_config {
  uint8_t palette, start_row;
  uint8_t reserved[14];
  uint16_t column_bytes[16];
  uint8_t rows[16];
};
static bool amx_request() {
  return syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) == 0;
}
static inline void begin_region() {  // amx_attn::begin_region (LDTILECFG)
  tile_config cfg{};
  cfg.palette = 1;
  for (int i = 0; i < 8; i++) {
    cfg.rows[i] = TILE_ROWS;
    cfg.column_bytes[i] = 64;
  }
  _tile_loadconfig(&cfg);
}
static inline void end_region() {
  _tile_release();
}

// amx_attn::qk_mirror_128x4 (transcribed; tile numbers and strides as in
// src/tron/kernels/amx_attn.cpp:241-268).
static inline void qk_mirror_128x4(const bf16* k_mirror, const bf16* q_rows, float* s) {
  _tile_zero(0);
  _tile_zero(1);
  _tile_zero(2);
  _tile_zero(3);
  constexpr int PANEL_ELEMS = 16 * 16 * 2;
  constexpr int BF16_ROW_BYTES = HD * 2;
  constexpr int S_ROW_BYTES = PAGE * 4;
  for (int step = 0; step < HD / DIM_STEP; step++) {
    _tile_loadd(4, q_rows + step * DIM_STEP, BF16_ROW_BYTES);
    _tile_loadd(5, k_mirror + (step * 4 + 0) * PANEL_ELEMS, 64);
    _tile_dpbf16ps(0, 4, 5);
    _tile_loadd(6, k_mirror + (step * 4 + 1) * PANEL_ELEMS, 64);
    _tile_dpbf16ps(1, 4, 6);
    _tile_loadd(5, k_mirror + (step * 4 + 2) * PANEL_ELEMS, 64);
    _tile_dpbf16ps(2, 4, 5);
    _tile_loadd(6, k_mirror + (step * 4 + 3) * PANEL_ELEMS, 64);
    _tile_dpbf16ps(3, 4, 6);
  }
  _tile_stored(0, s + 0, S_ROW_BYTES);
  _tile_stored(1, s + 16, S_ROW_BYTES);
  _tile_stored(2, s + 32, S_ROW_BYTES);
  _tile_stored(3, s + 48, S_ROW_BYTES);
}

// amx_attn::weights_times_v_128x4 (transcribed, amx_attn.cpp:183-230). P is
// the thread-local 16 x 64 bf16 buffer whose rows 4..15 stay zero.
static inline void weights_times_v_128x4(
    const bf16* v_page, const float* exp_rows, size_t row_stride_floats, float* o, bf16 (*P)[PAGE]) {
  for (int q = 0; q < GROUP; q++) {
    for (int c = 0; c < PAGE; c += 32) {
      __m512 lo = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c);
      __m512 hi = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c + 16);
      _mm512_storeu_si512(P[q] + c, (__m512i)_mm512_cvtne2ps_pbh(hi, lo));
    }
  }
  constexpr int P_ROW_BYTES = PAGE * 2;
  constexpr int V_PAIR_ROW_BYTES = 2 * HD * 2;
  constexpr int O_ROW_BYTES = HD * 4;
  for (int half = 0; half < 2; half++) {
    _tile_zero(0);
    _tile_zero(1);
    _tile_zero(2);
    _tile_zero(3);
    for (int s = 0; s < 2; s++) {
      _tile_loadd(4, &P[0][s * DIM_STEP], P_ROW_BYTES);
      _tile_loadd(5, v_page + s * TILE_ROWS * HD * 2 + (half * 4 + 0) * DIM_STEP, V_PAIR_ROW_BYTES);
      _tile_dpbf16ps(0, 4, 5);
      _tile_loadd(6, v_page + s * TILE_ROWS * HD * 2 + (half * 4 + 1) * DIM_STEP, V_PAIR_ROW_BYTES);
      _tile_dpbf16ps(1, 4, 6);
      _tile_loadd(5, v_page + s * TILE_ROWS * HD * 2 + (half * 4 + 2) * DIM_STEP, V_PAIR_ROW_BYTES);
      _tile_dpbf16ps(2, 4, 5);
      _tile_loadd(6, v_page + s * TILE_ROWS * HD * 2 + (half * 4 + 3) * DIM_STEP, V_PAIR_ROW_BYTES);
      _tile_dpbf16ps(3, 4, 6);
    }
    _tile_stored(0, o + half * 64 + 0, O_ROW_BYTES);
    _tile_stored(1, o + half * 64 + 16, O_ROW_BYTES);
    _tile_stored(2, o + half * 64 + 32, O_ROW_BYTES);
    _tile_stored(3, o + half * 64 + 48, O_ROW_BYTES);
  }
}

// ------------------------------------------------------------ AVX kernels
// dotter<bf16,128>: x01..x67 preloaded (the query head), dot(y) = 4 VDPBF16PS
// into 2 accumulators + reduce (h/tron/kernels/dotter.hpp:176-226).
struct dotter128 {
  __m512i x01, x23, x45, x67;
  explicit dotter128(const bf16* x)
  : x01(_mm512_load_si512(x + 0)), x23(_mm512_load_si512(x + 32)),
    x45(_mm512_load_si512(x + 64)), x67(_mm512_load_si512(x + 96)) {}
  inline float operator()(const bf16* y) const {
    __m512i y01 = _mm512_load_si512(y + 0);
    __m512i y23 = _mm512_load_si512(y + 32);
    __m512i y45 = _mm512_load_si512(y + 64);
    __m512i y67 = _mm512_load_si512(y + 96);
    __m512 sum1 = _mm512_dpbf16_ps(_mm512_setzero_ps(), (__m512bh)x01, (__m512bh)y01);
    __m512 sum2 = _mm512_dpbf16_ps(_mm512_setzero_ps(), (__m512bh)x23, (__m512bh)y23);
    sum1 = _mm512_dpbf16_ps(sum1, (__m512bh)x45, (__m512bh)y45);
    sum2 = _mm512_dpbf16_ps(sum2, (__m512bh)x67, (__m512bh)y67);
    return _mm512_reduce_add_ps(_mm512_add_ps(sum1, sum2));
  }
  // Keep the four query loads alive even when no dot is computed (the AMX
  // path constructs the dotters before the dispatch and uses them only on
  // its fallback branch; the loads stay in the compiled production unit).
  inline void keep_alive() const { __asm__ volatile("" ::"v"(x01), "v"(x23), "v"(x45), "v"(x67)); }
};

// scaled_v_expr<64,128> (h/tron/models/kv_cache.hpp:2151-2175): per token
// pair, interleave the two fp32 scales into one bf16-pair register
// (truncating shift, interleave_bf16_ps), 8 VDPBF16PS into 8 accumulators;
// then 8 stores into the 128-float scratch row.
static inline void scaled_v_128(const float* scales, const bf16* v_pairs, int count, float* scratch) {
  const __m512i hi16 = _mm512_set1_epi32((int)0xffff0000u);
  __m512 t0 = _mm512_setzero_ps(), t1 = t0, t2 = t0, t3 = t0, t4 = t0, t5 = t0, t6 = t0, t7 = t0;
  const int end = (count + 1) / 2 * 2;
  for (int i = 0; i < end; i += 2) {
    __m512i lo = _mm512_srli_epi32(_mm512_castps_si512(_mm512_set1_ps(scales[i])), 16);
    __m512i hi = _mm512_castps_si512(_mm512_set1_ps(scales[i + 1]));
    __m512i scale = _mm512_ternarylogic_epi32(lo, hi, hi16, 0xF8 /* A | (B & C) */);
    const bf16* tile = v_pairs + size_t(i) * HD;  // pair row: [128 dims][2]
    t0 = _mm512_dpbf16_ps(t0, (__m512bh)_mm512_load_si512(tile + 0 * 32), (__m512bh)scale);
    t1 = _mm512_dpbf16_ps(t1, (__m512bh)_mm512_load_si512(tile + 1 * 32), (__m512bh)scale);
    t2 = _mm512_dpbf16_ps(t2, (__m512bh)_mm512_load_si512(tile + 2 * 32), (__m512bh)scale);
    t3 = _mm512_dpbf16_ps(t3, (__m512bh)_mm512_load_si512(tile + 3 * 32), (__m512bh)scale);
    t4 = _mm512_dpbf16_ps(t4, (__m512bh)_mm512_load_si512(tile + 4 * 32), (__m512bh)scale);
    t5 = _mm512_dpbf16_ps(t5, (__m512bh)_mm512_load_si512(tile + 5 * 32), (__m512bh)scale);
    t6 = _mm512_dpbf16_ps(t6, (__m512bh)_mm512_load_si512(tile + 6 * 32), (__m512bh)scale);
    t7 = _mm512_dpbf16_ps(t7, (__m512bh)_mm512_load_si512(tile + 7 * 32), (__m512bh)scale);
  }
  _mm512_store_ps(scratch + 0, t0);
  _mm512_store_ps(scratch + 16, t1);
  _mm512_store_ps(scratch + 32, t2);
  _mm512_store_ps(scratch + 48, t3);
  _mm512_store_ps(scratch + 64, t4);
  _mm512_store_ps(scratch + 80, t5);
  _mm512_store_ps(scratch + 96, t6);
  _mm512_store_ps(scratch + 112, t7);
}

// ------------------------------------------------------- per-head state
struct alignas(64) head_state {
  float v[HD];
  float m, s;
  int valid;
  int pad[13];
};

// Per-thread work buffers (the production thread_local / stack buffers).
struct alignas(64) thread_bufs {
  alignas(64) float s_pages[GROUP][PAGE];         // 1 KiB: the unit's score rows
  alignas(64) float qk_s[TILE_ROWS * PAGE];       // 4 KiB: mirror QK tile store
  alignas(64) bf16 P[TILE_ROWS][PAGE];            // 2 KiB: probabilities, rows 4..15 zero
  alignas(64) float amx_o[TILE_ROWS * HD];        // 8 KiB: PV tile store
  alignas(64) bf16 q_rows[TILE_ROWS * HD];        // 4 KiB: padded Q rows, rows 4..15 zero
  alignas(64) float scratch[HD];                  // one head's PV result
  alignas(64) uint32_t token_positions[2 * PAGE]; // the per-unit q/k position lookups
  alignas(64) head_state st[N_KV_HEADS * GROUP];  // running softmax state per query head
};

struct phase_cyc {
  uint64_t qk = 0, softmax = 0, pv = 0, state = 0, common = 0, units = 0, range = 0;
};

// ------------------------------------------------------------ the unit (AVX)
// apply_page_tok, dotter path: transcribed from self_attention.hpp:1595-1870.
// Timer placement as the probe: QK (7617), common = softmax pieces + state
// update (7618), PV (7619).
static inline void unit_avx(const bf16* k_page, const bf16* v_page, int32_t k_lo, int32_t tok_hi,
    int sliding_window, const bf16* q_group, int kv_head, thread_bufs& tb, phase_cyc& pc, bool probe) {
  const uint64_t t_u0 = probe ? rdtsc() : 0;
  // s_pages = -inf; dot_q construction (loads the 4 query heads).
  for (int o = 0; o < GROUP; o++)
    for (int c = 0; c < PAGE; c += 16)
      _mm512_store_ps(&tb.s_pages[o][c], _mm512_set1_ps(-INFINITY));
  const dotter128 dot_q[GROUP] = {dotter128(q_group + 0 * HD), dotter128(q_group + 1 * HD),
      dotter128(q_group + 2 * HD), dotter128(q_group + 3 * HD)};
  // token_positions[q_tok] and token_positions[page.at_offset(0)]: two loads per unit
  const int32_t q_position = int32_t(tb.token_positions[PAGE + 7]);
  const int32_t k_position = int32_t(tb.token_positions[0]);
  int relevant = 0;
  for (int i = 0; i < PAGE; ++i) {
    // page.at_offset(i) = lo + i (an add), the range-hint check and the
    // sliding-window check (all inside Tron's QK timer).
    const int32_t kv_idx = k_lo + i;
    if (kv_idx >= tok_hi) continue;                                  // never true here
    if (q_position - (k_position + i) >= sliding_window) continue;   // never true here
    relevant++;
    const bf16* k = k_page + size_t(i) * HD;
    for (int o = 0; o < GROUP; o++) tb.s_pages[o][i] = dot_q[o](k);
  }
  uint64_t t_prev = probe ? rdtsc() : 0;
  if (probe) pc.qk += t_prev - t_u0;
  const __m512 vscale = _mm512_set1_ps(SCALE);
  for (int o = 0; o < GROUP; o++) {
    head_state& hs = tb.st[kv_head * GROUP + o];
    float* s_page = tb.s_pages[o];
    // s_page = s_page * scale; m_page = max(s_page) (and m*)
    for (int c = 0; c < PAGE; c += 16) _mm512_store_ps(s_page + c, _mm512_mul_ps(_mm512_load_ps(s_page + c), vscale));
    __m512 mx = _mm512_load_ps(s_page);
    for (int c = 16; c < PAGE; c += 16) mx = _mm512_max_ps(mx, _mm512_load_ps(s_page + c));
    float m_page = _mm512_reduce_max_ps(mx);
    if (hs.valid) m_page = std::max(hs.m, m_page);
    // exp_s_minus_m = exp(s_page - m_page), in place
    const __m512 vm = _mm512_set1_ps(m_page);
    for (int c = 0; c < PAGE; c += 16)
      _mm512_store_ps(s_page + c, tron_exp(_mm512_sub_ps(_mm512_load_ps(s_page + c), vm)));
    uint64_t t_sm = 0;
    if (probe) {
      t_sm = rdtsc();
      pc.common += t_sm - t_prev;
    }
    scaled_v_128(s_page, v_page, relevant, tb.scratch);  // scaled_v (PV) into scratch
    if (probe) {
      t_prev = rdtsc();
      pc.pv += t_prev - t_sm;
    }
    // state update (lands in the next head's common interval, as in Tron)
    __m512 acc = _mm512_load_ps(s_page);
    for (int c = 16; c < PAGE; c += 16) acc = _mm512_add_ps(acc, _mm512_load_ps(s_page + c));
    const float sum_e = _mm512_reduce_add_ps(acc);
    if (hs.valid) {
      const float corr = std::exp(hs.m - m_page);
      const __m512 vc = _mm512_set1_ps(corr);
      for (int d = 0; d < HD; d += 16)
        _mm512_store_ps(hs.v + d, _mm512_fmadd_ps(_mm512_load_ps(hs.v + d), vc, _mm512_load_ps(tb.scratch + d)));
      hs.s = hs.s * corr + sum_e;
    } else {
      for (int d = 0; d < HD; d += 16) _mm512_store_ps(hs.v + d, _mm512_load_ps(tb.scratch + d));
      hs.s = sum_e;
      hs.valid = 1;
    }
    hs.m = m_page;
  }
  if (probe) pc.common += rdtsc() - t_prev;
  pc.units++;
}

// ------------------------------------------------------------ the unit (AMX)
// apply_page_tok, dense AMX path (mirror): transcribed from
// self_attention.hpp:1595-1830. q_rows was packed once per page range.
static inline void unit_amx(const bf16* k_mirror, const bf16* v_page, const bf16* q_group,
    int kv_head, thread_bufs& tb, phase_cyc& pc, bool probe) {
  const uint64_t t_u0 = probe ? rdtsc() : 0;
  for (int o = 0; o < GROUP; o++)
    for (int c = 0; c < PAGE; c += 16)
      _mm512_store_ps(&tb.s_pages[o][c], _mm512_set1_ps(-INFINITY));
  const dotter128 dot_q[GROUP] = {dotter128(q_group + 0 * HD), dotter128(q_group + 1 * HD),
      dotter128(q_group + 2 * HD), dotter128(q_group + 3 * HD)};
  for (int o = 0; o < GROUP; o++) dot_q[o].keep_alive();  // constructed before the dispatch in production
  const volatile uint32_t q_position = tb.token_positions[PAGE + 7];
  const volatile uint32_t k_position = tb.token_positions[0];
  (void)q_position; (void)k_position;
  qk_mirror_128x4(k_mirror, tb.q_rows, tb.qk_s);
  std::memcpy(&tb.s_pages[0][0], tb.qk_s, GROUP * PAGE * sizeof(float));
  uint64_t t_qk = 0;
  if (probe) {
    t_qk = rdtsc();
    pc.qk += t_qk - t_u0;
  }
  float corr_arr[GROUP], m_new_arr[GROUP], sum_arr[GROUP];
  const __m512 vscale = _mm512_set1_ps(SCALE);
  for (int o = 0; o < GROUP; o++) {
    head_state& hs = tb.st[kv_head * GROUP + o];
    float* s_page = tb.s_pages[o];
    for (int c = 0; c < PAGE; c += 16) _mm512_store_ps(s_page + c, _mm512_mul_ps(_mm512_load_ps(s_page + c), vscale));
    __m512 mx = _mm512_load_ps(s_page);
    for (int c = 16; c < PAGE; c += 16) mx = _mm512_max_ps(mx, _mm512_load_ps(s_page + c));
    float m_page = _mm512_reduce_max_ps(mx);
    if (hs.valid) m_page = std::max(hs.m, m_page);
    const __m512 vm = _mm512_set1_ps(m_page);
    for (int c = 0; c < PAGE; c += 16)
      _mm512_store_ps(s_page + c, tron_exp(_mm512_sub_ps(_mm512_load_ps(s_page + c), vm)));
    // sum(s_page): a separate pass, as production's sum() over the stored expression
    __m512 acc = _mm512_load_ps(s_page);
    for (int c = 16; c < PAGE; c += 16) acc = _mm512_add_ps(acc, _mm512_load_ps(s_page + c));
    m_new_arr[o] = m_page;
    sum_arr[o] = _mm512_reduce_add_ps(acc);
    corr_arr[o] = hs.valid ? std::exp(hs.m - m_page) : 0.f;
  }
  uint64_t t_sm = 0;
  if (probe) {
    t_sm = rdtsc();
    pc.softmax += t_sm - t_qk;
  }
  weights_times_v_128x4(v_page, &tb.s_pages[0][0], PAGE, tb.amx_o, tb.P);
  uint64_t t_pv = 0;
  if (probe) {
    t_pv = rdtsc();
    pc.pv += t_pv - t_sm;
  }
  for (int o = 0; o < GROUP; o++) {
    head_state& hs = tb.st[kv_head * GROUP + o];
    std::memcpy(tb.scratch, tb.amx_o + o * HD, HD * sizeof(float));
    if (hs.valid) {
      const __m512 vc = _mm512_set1_ps(corr_arr[o]);
      for (int d = 0; d < HD; d += 16)
        _mm512_store_ps(hs.v + d, _mm512_fmadd_ps(_mm512_load_ps(hs.v + d), vc, _mm512_load_ps(tb.scratch + d)));
      hs.s = hs.s * corr_arr[o] + sum_arr[o];
    } else {
      for (int d = 0; d < HD; d += 16) _mm512_store_ps(hs.v + d, _mm512_load_ps(tb.scratch + d));
      hs.s = sum_arr[o];
      hs.valid = 1;
    }
    hs.m = m_new_arr[o];
  }
  if (probe) pc.state += rdtsc() - t_pv;
  pc.units++;
}

// ------------------------------------------------------ scalar reference
// Both production paths feed the PV multiply bf16 probabilities: the AVX path
// truncates (interleave_bf16_ps shifts the fp32 bits), the AMX path rounds to
// nearest even (cvtne2ps). The softmax sum s* stays fp32. The reference
// models the same rounding so that the check measures transcription errors,
// not the known bf16 quantization.
static void reference_unit(const bf16* k_page, const bf16* v_page, const bf16* q_group,
    int kv_head, head_state* st, bool truncate_p) {
  for (int o = 0; o < GROUP; o++) {
    head_state& hs = st[kv_head * GROUP + o];
    double s_row[PAGE];
    for (int t = 0; t < PAGE; t++) {
      double acc = 0;
      for (int d = 0; d < HD; d++) acc += double(b2f(q_group[o * HD + d])) * b2f(k_page[t * HD + d]);
      s_row[t] = float(float(acc) * SCALE);
    }
    double pm = *std::max_element(s_row, s_row + PAGE);
    double m_new = hs.valid ? std::max(pm, double(hs.m)) : pm;
    double corr = hs.valid ? std::exp(hs.m - m_new) : 0.0;
    double ssum = 0, pv[HD] = {0};
    for (int t = 0; t < PAGE; t++) {
      float e = float(std::exp(s_row[t] - m_new));
      ssum += e;
      uint32_t u;
      std::memcpy(&u, &e, 4);
      const float e_bf = truncate_p ? b2f(bf16(u >> 16)) : b2f(f2b(e));
      for (int d = 0; d < HD; d++) pv[d] += double(e_bf) * b2f(v_page[(t / 2) * HD * 2 + d * 2 + (t & 1)]);
    }
    for (int d = 0; d < HD; d++) hs.v[d] = float(hs.v[d] * corr + pv[d]);
    hs.s = float(hs.s * corr + ssum);
    hs.m = float(m_new);
    hs.valid = 1;
  }
}

// -------------------------------------------------------- data layout
struct arena {
  uint8_t* canon = nullptr;   // blocks of 32 KiB
  uint8_t* mirror = nullptr;  // planes of 16 KiB (4 KiB pages)
  bf16* q = nullptr;          // N_LAYERS x N_KV_HEADS x GROUP x HD
  size_t n_pages = 0;
  size_t book_pages = 0;       // 0 = one arena [layer][head][page]; N = Tron's books: [book][layer][head][page in book]
  std::vector<uint32_t> perm;  // logical page -> physical block (identity unless --shuffle)
  size_t block_index(int layer, int head, size_t pg) const {
    const size_t p = perm[pg];
    if (book_pages == 0) return (size_t(layer) * N_KV_HEADS + head) * n_pages + p;
    const size_t book = p / book_pages, in = p % book_pages;
    return (book * (size_t(N_LAYERS) * N_KV_HEADS) + size_t(layer) * N_KV_HEADS + head) * book_pages + in;
  }
  size_t canon_bytes = 0, mirror_bytes = 0;
  std::string huge_mode;
  const bf16* k_plane(int layer, int head, size_t pg) const {
    return reinterpret_cast<const bf16*>(canon + block_index(layer, head, pg) * BLOCK_BYTES);
  }
  const bf16* v_plane(int layer, int head, size_t pg) const {
    return reinterpret_cast<const bf16*>(canon + block_index(layer, head, pg) * BLOCK_BYTES + PLANE_BYTES);
  }
  const bf16* mirror_plane(int layer, int head, size_t pg) const {
    return reinterpret_cast<const bf16*>(mirror + block_index(layer, head, pg) * PLANE_BYTES);
  }
  bf16* k_plane_w(int layer, int head, size_t pg) { return const_cast<bf16*>(k_plane(layer, head, pg)); }
  bf16* v_plane_w(int layer, int head, size_t pg) { return const_cast<bf16*>(v_plane(layer, head, pg)); }
  bf16* mirror_plane_w(int layer, int head, size_t pg) { return const_cast<bf16*>(mirror_plane(layer, head, pg)); }
};

// Note [K mirror coherence] layout: plane[(((s*4 + c)*16 + dp)*16 + t)*2 + j] = K[c*16+t][s*32+2dp+j]
static void scatter_k_mirror(bf16* plane, const bf16* k_page) {
  for (int tok = 0; tok < PAGE; tok++) {
    const int c = tok / 16, t = tok % 16;
    for (int s = 0; s < HD / 32; s++)
      for (int dp = 0; dp < 16; dp++) {
        bf16* dst = plane + (((s * (PAGE / 16) + c) * 16 + dp) * 16 + t) * 2;
        dst[0] = k_page[tok * HD + s * 32 + 2 * dp];
        dst[1] = k_page[tok * HD + s * 32 + 2 * dp + 1];
      }
  }
}

// mmap a region; 1 GiB huge pages when asked and available, else THP with the
// region aligned to 2 MiB (mmap alone gives 4 KiB alignment), else 4 KiB pages.
static void* map_region(size_t bytes, const std::string& mode, bool small_pages, std::string& used) {
  void* p = MAP_FAILED;
  if (!small_pages && mode == "1g") {
    size_t rounded = (bytes + (1ull << 30) - 1) & ~((1ull << 30) - 1);
    p = mmap(nullptr, rounded, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB | MAP_HUGE_1GB, -1, 0);
    if (p != MAP_FAILED) { used = "1g"; return p; }
    fprintf(stderr, "note: 1 GiB huge pages unavailable (%s), falling back to THP\n", strerror(errno));
  }
  const size_t align = 2u << 20;
  size_t rounded = (bytes + align - 1) & ~(align - 1);
  uint8_t* raw = static_cast<uint8_t*>(mmap(nullptr, rounded + align, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
  if (raw == MAP_FAILED) { perror("mmap"); exit(1); }
  uint8_t* aligned = reinterpret_cast<uint8_t*>((reinterpret_cast<uintptr_t>(raw) + align - 1) & ~uintptr_t(align - 1));
  if (small_pages || mode == "none") {
    madvise(aligned, rounded, MADV_NOHUGEPAGE);
    used = "4k";
  } else {
    madvise(aligned, rounded, MADV_HUGEPAGE);
    used = "thp";
  }
  return aligned;
}

// What the kernel actually gave us (AnonHugePages = THP; *_Hugetlb = 1 GiB pool).
static void smaps_rollup(long& anon_huge_kb, long& hugetlb_kb) {
  anon_huge_kb = hugetlb_kb = 0;
  FILE* f = fopen("/proc/self/smaps_rollup", "r");
  if (!f) return;
  char line[256];
  while (fgets(line, sizeof line, f)) {
    long v;
    if (sscanf(line, "AnonHugePages: %ld kB", &v) == 1) anon_huge_kb = v;
    else if (sscanf(line, "Shared_Hugetlb: %ld kB", &v) == 1) hugetlb_kb += v;
    else if (sscanf(line, "Private_Hugetlb: %ld kB", &v) == 1) hugetlb_kb += v;
  }
  fclose(f);
}

// --------------------------------------------------------- threading
struct spin_barrier {
  std::atomic<int> count{0};
  std::atomic<int> gen{0};
  int n;
  explicit spin_barrier(int n) : n(n) {}
  void wait() {
    int g = gen.load(std::memory_order_acquire);
    if (count.fetch_add(1, std::memory_order_acq_rel) + 1 == n) {
      count.store(0, std::memory_order_relaxed);
      gen.store(g + 1, std::memory_order_release);
    } else {
      while (gen.load(std::memory_order_acquire) == g) _mm_pause();
    }
  }
};

struct run_cfg {
  std::string variant = "avx";
  int pages = 130;
  int threads = 1;
  std::vector<int> cpus;
  int passes = 300;
  int warmup = 20;
  bool hot = false;
  bool shuffle = false;
  std::string huge = "thp";
  std::string json;
  bool check = false;
  int book_pages = 0;  // --book-pages N: Tron's book layout (25 pages per book by default in Tron; 24 used per book with 128-token chunks)
};

struct pass_rec {
  double qk_ns, softmax_ns, pv_ns, state_ns, common_ns, unit_ns, range_ns_per_unit, barrier_ns, pass_us;
  uint64_t units;
};

struct thread_ctx {
  int idx, cpu;
  const run_cfg* cfg;
  arena* ar;
  spin_barrier* bar;
  double tsc_ghz;
  std::vector<pass_rec> recs;
  thread_bufs* tb;
  std::vector<std::array<int, 3>> runs;  // (head, first page, last page) per layer, same for every layer
};

// Tron's planner (finish_sw_plan) with equal worker speeds: the (head, page)
// list is walked in order; a page goes to the next worker when its center
// passes the worker's cumulative share; at most one worker step per page.
static void plan_runs(int n_workers, int pages, std::vector<std::vector<std::array<int, 3>>>& runs) {
  runs.assign(n_workers, {});
  const long total = long(N_KV_HEADS) * pages;
  long idx = 0;
  int worker = 0;
  for (int head = 0; head < N_KV_HEADS; head++) {
    for (int pg = 0; pg < pages; pg++, idx++) {
      const double center = (idx + 0.5) / double(total);
      if (worker + 1 < n_workers && double(worker + 1) / n_workers < center) worker++;
      auto& wr = runs[worker];
      if (!wr.empty() && wr.back()[0] == head && wr.back()[2] == pg - 1) wr.back()[2] = pg;
      else wr.push_back({head, pg, pg});
    }
  }
}

static void* worker_main(void* arg) {
  thread_ctx& tc = *static_cast<thread_ctx*>(arg);
  const run_cfg& cfg = *tc.cfg;
  arena& ar = *tc.ar;
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(tc.cpu, &set);
  if (sched_setaffinity(0, sizeof set, &set) != 0) perror("sched_setaffinity");
  const bool is_amx = cfg.variant == "amx";
  if (is_amx && !amx_request()) { fprintf(stderr, "arch_prctl failed on cpu %d\n", tc.cpu); exit(1); }
  thread_bufs& tb = *tc.tb;
  std::memset(&tb, 0, sizeof tb);
  for (int i = 0; i < 2 * PAGE; i++) tb.token_positions[i] = uint32_t(i);
  const int total_passes = cfg.warmup + cfg.passes;
  const int sliding_window = 1 << 30;
  const int32_t tok_hi = 1 << 30;

  for (int pass = 0; pass < total_passes; pass++) {
    phase_cyc pc;
    uint64_t barrier_cyc = 0;
    const uint64_t t_pass0 = rdtsc();
    for (int layer = 0; layer < N_LAYERS; layer++) {
      for (int h = 0; h < N_KV_HEADS * GROUP; h++) tb.st[h].valid = 0;  // fresh token state per operation
      for (const auto& run : tc.runs) {
        const int head = run[0];
        const bf16* q_group = ar.q + ((size_t(layer) * N_KV_HEADS + head) * GROUP) * HD;
        const uint64_t t_r0 = rdtsc();
        if (is_amx) {
          begin_region();  // LDTILECFG once per page range (apply_page_range)
          std::memcpy(tb.q_rows, q_group, GROUP * HD * sizeof(bf16));  // pack_q_rows_128x4
        }
        pc.range += rdtsc() - t_r0;
        for (int pg = run[1]; pg <= run[2]; pg++) {
          const int L = cfg.hot ? 0 : layer, H = cfg.hot ? 0 : head;
          const size_t P = cfg.hot ? 0 : size_t(pg);
          if (is_amx)
            unit_amx(ar.mirror_plane(L, H, P), ar.v_plane(L, H, P), q_group, head, tb, pc, true);
          else
            unit_avx(ar.k_plane(L, H, P), ar.v_plane(L, H, P), int32_t(P) * PAGE, tok_hi, sliding_window, q_group, head, tb, pc, true);
        }
        if (is_amx) {
          const uint64_t t_r1 = rdtsc();
          end_region();
          pc.range += rdtsc() - t_r1;
        }
      }
      const uint64_t t_b0 = rdtsc();
      tc.bar->wait();
      barrier_cyc += rdtsc() - t_b0;
    }
    const uint64_t t_pass1 = rdtsc();
    if (pass >= cfg.warmup && pc.units > 0) {
      const double ns = 1.0 / tc.tsc_ghz;
      pass_rec r;
      const double u = double(pc.units);
      r.units = pc.units;
      r.qk_ns = pc.qk * ns / u;
      r.softmax_ns = pc.softmax * ns / u;
      r.pv_ns = pc.pv * ns / u;
      r.state_ns = pc.state * ns / u;
      r.common_ns = pc.common * ns / u;
      r.unit_ns = r.qk_ns + r.softmax_ns + r.pv_ns + r.state_ns + r.common_ns;
      r.range_ns_per_unit = pc.range * ns / u;
      r.barrier_ns = barrier_cyc * ns;
      r.pass_us = (t_pass1 - t_pass0) * ns / 1000.0;
      tc.recs.push_back(r);
    }
  }
  return nullptr;
}

static double median(std::vector<double> v) {
  if (v.empty()) return 0;
  std::sort(v.begin(), v.end());
  size_t n = v.size();
  return n % 2 ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]);
}

static std::vector<int> parse_cpus(const std::string& s) {
  std::vector<int> out;
  size_t i = 0;
  while (i < s.size()) {
    size_t j = s.find(',', i);
    if (j == std::string::npos) j = s.size();
    std::string tok = s.substr(i, j - i);
    size_t d = tok.find('-');
    if (d == std::string::npos) out.push_back(atoi(tok.c_str()));
    else {
      int a = atoi(tok.substr(0, d).c_str()), b = atoi(tok.substr(d + 1).c_str());
      for (int c = a; c <= b; c++) out.push_back(c);
    }
    i = j + 1;
  }
  return out;
}

static double measure_tsc_ghz() {
  const double t0 = now_s();
  const uint64_t c0 = rdtsc();
  while (now_s() - t0 < 0.2) {}
  const double t1 = now_s();
  const uint64_t c1 = rdtsc();
  return (c1 - c0) / (t1 - t0) / 1e9;
}

int main(int argc, char** argv) {
  run_cfg cfg;
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    auto next = [&](void) -> std::string { if (i + 1 >= argc) { fprintf(stderr, "missing value for %s\n", a.c_str()); exit(2); } return argv[++i]; };
    if (a == "--variant") cfg.variant = next();
    else if (a == "--pages") cfg.pages = atoi(next().c_str());
    else if (a == "--threads") cfg.threads = atoi(next().c_str());
    else if (a == "--cpus") cfg.cpus = parse_cpus(next());
    else if (a == "--passes") cfg.passes = atoi(next().c_str());
    else if (a == "--warmup") cfg.warmup = atoi(next().c_str());
    else if (a == "--hot") cfg.hot = true;
    else if (a == "--shuffle") cfg.shuffle = true;
    else if (a == "--huge") cfg.huge = next();
    else if (a == "--json") cfg.json = next();
    else if (a == "--check") cfg.check = true;
    else if (a == "--book-pages") cfg.book_pages = atoi(next().c_str());
    else { fprintf(stderr, "unknown arg %s\n", a.c_str()); return 2; }
  }
  if (cfg.variant != "avx" && cfg.variant != "amx") { fprintf(stderr, "variant avx|amx\n"); return 2; }
  if (cfg.huge != "thp" && cfg.huge != "1g" && cfg.huge != "none") { fprintf(stderr, "--huge thp|1g|none\n"); return 2; }
  const bool is_amx = cfg.variant == "amx";
  if (cfg.cpus.empty()) for (int i = 0; i < cfg.threads; i++) cfg.cpus.push_back(i);
  if ((int)cfg.cpus.size() < cfg.threads) { fprintf(stderr, "need %d cpus, got %zu\n", cfg.threads, cfg.cpus.size()); return 2; }
  if (is_amx && !amx_request()) { fprintf(stderr, "AMX not available (arch_prctl failed)\n"); return 3; }

  // ---- arena
  arena ar;
  ar.n_pages = cfg.hot ? 1 : size_t(cfg.pages);
  ar.book_pages = cfg.hot ? 0 : size_t(std::max(0, cfg.book_pages));
  const size_t n_books = ar.book_pages ? (ar.n_pages + ar.book_pages - 1) / ar.book_pages : 1;
  const size_t n_blocks = ar.book_pages ? n_books * size_t(N_LAYERS) * N_KV_HEADS * ar.book_pages : size_t(N_LAYERS) * N_KV_HEADS * ar.n_pages;
  ar.canon_bytes = n_blocks * BLOCK_BYTES;
  ar.mirror_bytes = n_blocks * PLANE_BYTES;
  std::string used_canon, used_mirror;
  ar.canon = static_cast<uint8_t*>(map_region(ar.canon_bytes, cfg.huge, false, used_canon));
  ar.mirror = static_cast<uint8_t*>(map_region(ar.mirror_bytes, cfg.huge, true, used_mirror));
  ar.huge_mode = used_canon + "/" + used_mirror;
  ar.q = static_cast<bf16*>(aligned_alloc(64, size_t(N_LAYERS) * N_KV_HEADS * GROUP * HD * sizeof(bf16)));
  ar.perm.resize(ar.n_pages);
  for (size_t p = 0; p < ar.n_pages; p++) ar.perm[p] = uint32_t(p);
  if (cfg.shuffle) {
    uint64_t s = 12345;
    for (size_t p = ar.n_pages; p > 1; p--) std::swap(ar.perm[p - 1], ar.perm[splitmix(s) % p]);
  }
  {
    uint64_t s = 777;
    const size_t nq = size_t(N_LAYERS) * N_KV_HEADS * GROUP * HD;
    for (size_t i = 0; i < nq; i++) ar.q[i] = f2b((float(splitmix(s) & 0xffff) / 65535.f - 0.5f) * 0.6f);
  }
  // Fill K, V (pair-interleaved), mirror. Values in a small range so exp() is
  // in its normal regime. Done by threads on the worker CPUs for first touch
  // on the right NUMA node (the process is also run under numactl --membind=0).
  {
    const double t0 = now_s();
    std::vector<pthread_t> th(cfg.threads);
    struct fill_arg { arena* ar; int idx, n, cpu; };
    std::vector<fill_arg> fa(cfg.threads);
    auto fill = [](void* p) -> void* {
      fill_arg& a = *static_cast<fill_arg*>(p);
      cpu_set_t set; CPU_ZERO(&set); CPU_SET(a.cpu, &set); sched_setaffinity(0, sizeof set, &set);
      arena& ar = *a.ar;
      const size_t n_blocks = size_t(N_LAYERS) * N_KV_HEADS * ar.n_pages;
      std::vector<bf16> tmp(PAGE * HD);
      for (size_t b = a.idx; b < n_blocks; b += a.n) {
        uint64_t s = 0x1000 + b;
        const int layer = int(b / (N_KV_HEADS * ar.n_pages));
        const int head = int((b / ar.n_pages) % N_KV_HEADS);
        const size_t pg = b % ar.n_pages;
        bf16* K = ar.k_plane_w(layer, head, pg);
        bf16* V = ar.v_plane_w(layer, head, pg);
        for (int i = 0; i < PAGE * HD; i++) K[i] = f2b((float(splitmix(s) & 0xffff) / 65535.f - 0.5f) * 0.6f);
        for (int i = 0; i < PAGE * HD; i++) tmp[i] = f2b((float(splitmix(s) & 0xffff) / 65535.f - 0.5f) * 0.6f);
        for (int t = 0; t < PAGE; t++)
          for (int d = 0; d < HD; d++) V[(t / 2) * HD * 2 + d * 2 + (t & 1)] = tmp[t * HD + d];
        scatter_k_mirror(ar.mirror_plane_w(layer, head, pg), K);
      }
      return nullptr;
    };
    for (int i = 0; i < cfg.threads; i++) {
      fa[i] = {&ar, i, cfg.threads, cfg.cpus[i]};
      if (pthread_create(&th[i], nullptr, fill, &fa[i]) != 0) { perror("pthread_create(fill)"); return 1; }
    }
    for (int i = 0; i < cfg.threads; i++) pthread_join(th[i], nullptr);
    long anon_kb, htlb_kb;
    smaps_rollup(anon_kb, htlb_kb);
    fprintf(stderr, "arena: %.0f MiB canonical (%s) + %.0f MiB mirror (%s), filled in %.1f s; obtained: AnonHugePages %ld MiB, Hugetlb %ld MiB\n",
        ar.canon_bytes / 1048576.0, used_canon.c_str(), ar.mirror_bytes / 1048576.0, used_mirror.c_str(), now_s() - t0, anon_kb / 1024, htlb_kb / 1024);
    ar.huge_mode += " obtained:anon_huge_mib=" + std::to_string(anon_kb / 1024) + ",hugetlb_mib=" + std::to_string(htlb_kb / 1024);
  }

  const double tsc_ghz = measure_tsc_ghz();

  // ---- correctness check against the scalar reference
  if (cfg.check) {
    thread_bufs* tb = static_cast<thread_bufs*>(aligned_alloc(64, sizeof(thread_bufs)));
    std::memset(tb, 0, sizeof *tb);
    for (int i = 0; i < 2 * PAGE; i++) tb->token_positions[i] = uint32_t(i);
    std::vector<head_state> ref(N_KV_HEADS * GROUP);
    std::memset(ref.data(), 0, ref.size() * sizeof(head_state));
    const int npg = std::min<int>(3, int(ar.n_pages));
    phase_cyc pc;
    const bf16* q_group = ar.q;  // layer 0, head 0
    if (is_amx) { begin_region(); std::memcpy(tb->q_rows, q_group, GROUP * HD * sizeof(bf16)); }
    for (int pg = 0; pg < npg; pg++) {
      if (is_amx) unit_amx(ar.mirror_plane(0, 0, pg), ar.v_plane(0, 0, pg), q_group, 0, *tb, pc, false);
      else unit_avx(ar.k_plane(0, 0, pg), ar.v_plane(0, 0, pg), int32_t(pg) * PAGE, 1 << 30, 1 << 30, q_group, 0, *tb, pc, false);
      reference_unit(ar.k_plane(0, 0, pg), ar.v_plane(0, 0, pg), q_group, 0, ref.data(), /*truncate_p=*/!is_amx);
    }
    if (is_amx) end_region();
    // Three gates. m* (a max of fp32 scores) and s* (fp32 sum of exps) are
    // untouched by the bf16 rounding of P, so they catch score-scale and
    // dropped-instruction errors at 1e-4. The normalized output v*/s* carries
    // the bf16-rounded P on both sides; its gate is 1e-3 (a correct
    // transcription measures about 1e-7).
    double worst_m = 0, worst_s = 0, worst_v = 0;
    for (int o = 0; o < GROUP; o++) {
      worst_m = std::max(worst_m, double(std::fabs(tb->st[o].m - ref[o].m)) / (double(std::fabs(ref[o].m)) + 1e-6));
      worst_s = std::max(worst_s, double(std::fabs(tb->st[o].s - ref[o].s)) / double(std::fabs(ref[o].s)));
      for (int d = 0; d < HD; d++) {
        double a = tb->st[o].v[d] / tb->st[o].s, b = ref[o].v[d] / ref[o].s;
        worst_v = std::max(worst_v, std::fabs(a - b) / (std::fabs(b) + 1e-2));
      }
    }
    const bool ok = worst_m < 1e-4 && worst_s < 1e-4 && worst_v < 1e-3;
    if (getenv("UNIT_BENCH_DEBUG"))
      for (int o = 0; o < GROUP; o++)
        printf("  head %d: bench m %.6f s %.5f v[0..2] %.5f %.5f %.5f | ref m %.6f s %.5f v[0..2] %.5f %.5f %.5f\n", o,
            tb->st[o].m, tb->st[o].s, tb->st[o].v[0], tb->st[o].v[1], tb->st[o].v[2],
            ref[o].m, ref[o].s, ref[o].v[0], ref[o].v[1], ref[o].v[2]);
    printf("check variant=%s pages=%d worst_rel_err m %.3e s %.3e v/s %.3e %s\n", cfg.variant.c_str(), npg, worst_m, worst_s, worst_v, ok ? "OK" : "FAIL");
    return ok ? 0 : 1;
  }

  // ---- plan and run
  std::vector<std::vector<std::array<int, 3>>> runs;
  plan_runs(cfg.threads, cfg.hot ? cfg.pages : int(ar.n_pages), runs);
  spin_barrier bar(cfg.threads);
  std::vector<thread_ctx> ctx(cfg.threads);
  std::vector<pthread_t> th(cfg.threads);
  for (int i = 0; i < cfg.threads; i++) {
    ctx[i].idx = i; ctx[i].cpu = cfg.cpus[i]; ctx[i].cfg = &cfg; ctx[i].ar = &ar; ctx[i].bar = &bar;
    ctx[i].tsc_ghz = tsc_ghz; ctx[i].runs = runs[i];
    ctx[i].tb = static_cast<thread_bufs*>(aligned_alloc(64, sizeof(thread_bufs)));
  }
  const double t0 = now_s(), e0 = epoch_s();
  fprintf(stderr, "RUN-START %.3f\n", e0);
  for (int i = 0; i < cfg.threads; i++)
    if (pthread_create(&th[i], nullptr, worker_main, &ctx[i]) != 0) { perror("pthread_create"); return 1; }
  for (int i = 0; i < cfg.threads; i++) pthread_join(th[i], nullptr);
  const double wall = now_s() - t0, e1 = epoch_s();
  fprintf(stderr, "RUN-END %.3f\n", e1);

  // ---- summarize: per thread medians over passes; worker 0 and all-thread median
  auto med_of = [&](int t, double pass_rec::*f) { std::vector<double> v; for (auto& r : ctx[t].recs) v.push_back(r.*f); return median(v); };
  std::vector<double> all_unit, all_qk, all_sm, all_pv, all_st, all_cm, all_bar, all_pass;
  FILE* jf = cfg.json.empty() ? nullptr : fopen(cfg.json.c_str(), "w");
  if (jf) {
    fprintf(jf, "{\n \"variant\": \"%s\", \"pages\": %d, \"hot\": %s, \"shuffle\": %s, \"threads\": %d, \"passes\": %d, \"warmup\": %d,\n"
        " \"tsc_ghz\": %.4f, \"book_pages\": %zu, \"huge\": \"%s\", \"canon_mib\": %.0f, \"mirror_mib\": %.0f, \"wall_s\": %.2f, \"run_start_epoch\": %.3f, \"run_end_epoch\": %.3f,\n \"per_thread\": [\n",
        cfg.variant.c_str(), cfg.pages, cfg.hot ? "true" : "false", cfg.shuffle ? "true" : "false", cfg.threads,
        cfg.passes, cfg.warmup, tsc_ghz, ar.book_pages, ar.huge_mode.c_str(), ar.canon_bytes / 1048576.0, ar.mirror_bytes / 1048576.0, wall, e0, e1);
  }
  for (int t = 0; t < cfg.threads; t++) {
    double u = med_of(t, &pass_rec::unit_ns), qk = med_of(t, &pass_rec::qk_ns), sm = med_of(t, &pass_rec::softmax_ns),
           pv = med_of(t, &pass_rec::pv_ns), st = med_of(t, &pass_rec::state_ns), cm = med_of(t, &pass_rec::common_ns),
           rg = med_of(t, &pass_rec::range_ns_per_unit), bw = med_of(t, &pass_rec::barrier_ns), pu = med_of(t, &pass_rec::pass_us);
    uint64_t units = ctx[t].recs.empty() ? 0 : ctx[t].recs[0].units;
    all_unit.push_back(u); all_qk.push_back(qk); all_sm.push_back(sm); all_pv.push_back(pv); all_st.push_back(st); all_cm.push_back(cm); all_bar.push_back(bw); all_pass.push_back(pu);
    if (jf) fprintf(jf, "  {\"idx\": %d, \"cpu\": %d, \"passes_recorded\": %zu, \"units_per_pass\": %llu, \"qk_ns\": %.1f, \"softmax_ns\": %.1f, \"pv_ns\": %.1f, \"state_ns\": %.1f, \"common_ns\": %.1f, \"unit_ns\": %.1f, \"range_ns_per_unit\": %.1f, \"barrier_ns_per_pass\": %.0f, \"pass_us\": %.1f}%s\n",
        t, ctx[t].cpu, ctx[t].recs.size(), (unsigned long long)units, qk, sm, pv, st, cm, u, rg, bw, pu, t + 1 < cfg.threads ? "," : "");
  }
  const double w0 = all_unit[0];
  printf("variant=%s pages=%d hot=%d shuffle=%d book_pages=%zu threads=%d huge=%s  worker0: unit %.0f ns = qk %.0f + softmax %.0f + pv %.0f + state %.0f + common(avx) %.0f  | all-thread median unit %.0f ns | barrier %.0f ns/pass | pass %.0f us | units/pass %llu\n",
      cfg.variant.c_str(), cfg.pages, cfg.hot, cfg.shuffle, ar.book_pages, cfg.threads, ar.huge_mode.c_str(), w0, all_qk[0], all_sm[0], all_pv[0], all_st[0], all_cm[0],
      median(all_unit), median(all_bar), median(all_pass), (unsigned long long)(ctx[0].recs.empty() ? 0 : ctx[0].recs[0].units));
  if (jf) {
    fprintf(jf, " ],\n \"worker0\": {\"unit_ns\": %.1f, \"qk_ns\": %.1f, \"softmax_ns\": %.1f, \"pv_ns\": %.1f, \"state_ns\": %.1f, \"common_ns\": %.1f},\n"
        " \"all_median\": {\"unit_ns\": %.1f, \"qk_ns\": %.1f, \"softmax_ns\": %.1f, \"pv_ns\": %.1f, \"state_ns\": %.1f, \"common_ns\": %.1f, \"barrier_ns_per_pass\": %.0f, \"pass_us\": %.1f}\n}\n",
        w0, all_qk[0], all_sm[0], all_pv[0], all_st[0], all_cm[0], median(all_unit), median(all_qk), median(all_sm), median(all_pv), median(all_st), median(all_cm), median(all_bar), median(all_pass));
    fclose(jf);
  }
  return 0;
}
