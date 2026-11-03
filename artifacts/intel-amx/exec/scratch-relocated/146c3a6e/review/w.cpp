// AMX software-attention kernels. See Note [AMX attention dispatch]
// (in amx_attn_iface.hpp). The ONLY translation unit compiled with
// -mamx-tile/-mamx-bf16.

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <immintrin.h>
#include <unistd.h>

#include <sys/syscall.h>

#include "tron/kernels/amx_attn_iface.hpp"
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/v_vnni.hpp"
#include "tron/tensor/view.hpp"

// Linux lets a process use the AMX tile registers only after it asked for
// them: arch_prctl(ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) (kernel 5.16 and
// later, documented in Documentation/arch/x86/xstate.rst). Both values are
// part of the kernel ABI. The request code is defined here, guarded, rather
// than taken from <asm/prctl.h>, so the build does not depend on the version
// of the kernel headers in the toolchain.
#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
// XSAVE component number of the AMX tile data (XTILEDATA); the same bit 18
// that available() checks in XCR0.
constexpr unsigned long xfeature_xtiledata = 18;

namespace tron::amx_attn_h128g4 {
namespace {

// The kernel shape (PAGE_TOKENS_64, HEAD_SIZE_128, and the group sizes
// GROUP_HEADS_4 and GROUP_HEADS_16 the kernels are instantiated for at the end
// of this file) and the tile shape (TILE_ROWS_16, TILE_ROW_BYTES_64) come from
// the interface header and are used by name below. begin_region() configures
// all 8 tiles with the tile shape.
constexpr int N_TILES_8 = 8;
// Tile register numbers. Tiles 0-3 are accumulator tiles: _tile_dpbf16ps adds
// its products into them, so they hold the running sums. Both kernels load
// their operands into tiles 4-6. The tile intrinsics take the number as a
// constant.
constexpr int ACCUMULATOR_TILE_0 = 0;
constexpr int ACCUMULATOR_TILE_1 = 1;
constexpr int ACCUMULATOR_TILE_2 = 2;
constexpr int ACCUMULATOR_TILE_3 = 3;
// qk_rowmajor_128x4: K blocks 0 and 2 load into tile 4, K blocks 1 and 3 into
// tile 5, and the packed Q into tile 6.
constexpr int K_EVEN_BLOCK_TILE_4 = 4;
constexpr int K_ODD_BLOCK_TILE_5 = 5;
constexpr int Q_TILE_6 = 6;
// weights_times_v_128x4: P (the weights) loads into tile 4. V slices 0 and 2
// load into tile 5, V slices 1 and 3 into tile 6.
constexpr int P_TILE_4 = 4;
constexpr int V_EVEN_SLICE_TILE_5 = 5;
constexpr int V_ODD_SLICE_TILE_6 = 6;
// One stored tile's worth of fp32 scores (16 rows x 16 values).
static_assert(sizeof(float) == 4, "AMX/AVX fp32 kernels assume 32-bit float");
constexpr size_t TILE_FP32S = TILE_ROWS_16 * TILE_ROW_BYTES_64 / sizeof(float);
// TDPBF16PS consumes the head dim in 32-dim steps (16 bf16 pairs per step).
constexpr size_t DIM_STEP_32 = 32;
// weights_times_v_128x4 produces the 128 output dims in two 64-dim halves; each
// half is 4 accumulator tiles, one DIM_STEP_32 slice of the pair row per tile.
constexpr size_t PV_TILES_PER_HALF_4 = 4;
// Two tokens share one pair row of the packed V plane (Note [VNNI Packed V
// layout] in v_vnni.hpp).
constexpr size_t V_PAIR_TOKENS_2 = 2;
// Row strides handed to tile loads/stores, in bytes.
constexpr size_t BF16_ROW_BYTES = HEAD_SIZE_128 * sizeof(bf16);  // one 128-dim bf16 row
constexpr size_t V_PAIR_ROW_BYTES =
    2 * HEAD_SIZE_128 * sizeof(bf16);  // pair-interleaved V
constexpr size_t O_ROW_BYTES =
    HEAD_SIZE_128 * sizeof(float);  // one 128-dim fp32 output row

// The 64-byte tile configuration LDTILECFG loads (palette 1). Intel's manual
// names the per-tile byte length of one row "colsb" (column bytes); it is the
// same quantity as TILE_ROW_BYTES_64, so the field is called bytes_per_row.
struct tile_config {
  uint8_t palette, start_row;
  uint8_t reserved[14];
  uint16_t bytes_per_row[16];
  uint8_t rows[16];
};

bool detect_and_request() noexcept {
  // Runtime kill switch for same-binary A/B tests and emergency disable.
  // Exactly "1" disables, the same rule as TRON_NO_RTM.
  const char* off = std::getenv("TRON_AMX_DISABLE");
  if (off != nullptr && std::strcmp(off, "1") == 0) return false;
  unsigned a, b, c, d;
  // CPUID leaf 7.0 EDX: bit 22 AMX-BF16, bit 24 AMX-TILE
  __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(7), "c"(0));
  if (!((d >> 22) & 1) || !((d >> 24) & 1)) return false;
  // XCR0 bits 17:18 (OS enabled tile state)
  unsigned xlo, xhi;
  __asm__ volatile("xgetbv" : "=a"(xlo), "=d"(xhi) : "c"(0));
  if ((xlo & (3u << 17)) != (3u << 17)) return false;
  return syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, xfeature_xtiledata) == 0;
}

}  // namespace

bool available() noexcept {
  // available() is called on every dispatch, but the probe deliberately runs
  // once and the result stays constant for the process lifetime: CPUID and
  // XCR0 are hardware and boot state, the arch_prctl grant is per process,
  // and TRON_AMX_DISABLE is read once, at that first call. The disable switch
  // therefore selects the behavior of a whole run (same-binary A/B = run the
  // binary twice with different environments), never mid-flight. See Note
  // [AMX attention dispatch] in amx_attn_iface.hpp.
  static const bool ok = detect_and_request();
  return ok;
}

void begin_region() noexcept {
  tile_config cfg{};
  cfg.palette = 1;
  for (int i = 0; i < N_TILES_8; i++) {
    cfg.rows[i] = uint8_t(TILE_ROWS_16);
    cfg.bytes_per_row[i] = uint16_t(TILE_ROW_BYTES_64);
  }
  _tile_loadconfig(&cfg);
}

void end_region() noexcept {
  _tile_release();
}

template <size_t group_heads>
  requires(group_heads_ok(group_heads))
void pack_q_group_128x4(const bf16* q_group, bf16* packed) noexcept {
  // Writes columns 0..group_heads-1 of every panel; the remaining columns are
  // padding the caller keeps zero (see the contract at the declaration). One
  // panel per 32-dim step.
  for (size_t step = 0; step < HEAD_SIZE_128 / DIM_STEP_32; step++) {
    for (size_t dim_pair = 0; dim_pair < DIM_STEP_32 / 2; dim_pair++) {
      for (size_t q_head = 0; q_head < group_heads; q_head++) {
        bf16* dst = packed + ((step * 16 + dim_pair) * 16 + q_head) * 2;
        dst[0] = q_group[q_head * HEAD_SIZE_128 + step * DIM_STEP_32 + 2 * dim_pair];
        dst[1] =
            q_group[q_head * HEAD_SIZE_128 + step * DIM_STEP_32 + 2 * dim_pair + 1];
      }
    }
  }
}

namespace {

// The transposing store of qk_rowmajor_128x4. After the two unpack stages of
// the 16 x 16 transpose (stage 1 interleaves 32-bit values, stage 2 interleaves
// 64-bit pairs), 128-bit lane `lane` (0..3) of u[row_group][k] holds tile
// column 4 * lane + k for the four tokens 4 * row_group .. 4 * row_group + 3.
// Output row 4 * lane + k (one query head, 16 tokens) is assembled from lane
// `lane` of u[0..3][k] by two _mm512_shuffle_f32x4 stages. Stage 3 pairs row
// groups 0/1 and 2/3. Stage 4 joins the two pairs. Each stage picks the even
// lanes (selector 0x88) or the odd lanes (selector 0xdd) of its two inputs.
// Stage 3 selects lanes {0, 2} or {1, 3} of each row-group pair. That choice
// is bit 0 of `lane`. Stage 4 selects the first or the second lane of each
// pair. That choice is bit 1 of `lane`. The selectors are immediates, so
// `lane` is a template argument. Lane 0 = (0x88, 0x88) is the one store
// sequence the 4-head kernel emits.
constexpr int LANES_EVEN_0X88 = 0x88;
constexpr int LANES_ODD_0XDD = 0xdd;
// A 128-bit lane holds 4 fp32 values: lane `lane` of u[.][0..3] holds tile
// columns 4 * lane .. 4 * lane + 3, which become 4 consecutive output rows.
constexpr size_t ROWS_PER_LANE_4 = 4;

template <int lane>
inline void store_transposed_rows(
    const __m512 (&u)[TILE_ROWS_16 / ROWS_PER_LANE_4][ROWS_PER_LANE_4],
    float* s_block,
    size_t s_stride_floats) {
  constexpr int pair_sel = (lane & 1) ? LANES_ODD_0XDD : LANES_EVEN_0X88;
  constexpr int quad_sel = (lane & 2) ? LANES_ODD_0XDD : LANES_EVEN_0X88;
  float* const s_rows = s_block + lane * ROWS_PER_LANE_4 * s_stride_floats;
  for (size_t k = 0; k < ROWS_PER_LANE_4; k++) {
    __m512 p = _mm512_shuffle_f32x4(u[0][k], u[1][k], pair_sel);
    __m512 q2 = _mm512_shuffle_f32x4(u[2][k], u[3][k], pair_sel);
    _mm512_storeu_ps(
        s_rows + k * s_stride_floats, _mm512_shuffle_f32x4(p, q2, quad_sel));
  }
}

}  // namespace

// S^T[64][16] = K_page . Q^T in tiles (K row-major as the A operand, packed
// Q as the B operand), then a transposing store of the group_heads useful
// query rows into the caller's s buffer (UNSCALED). See Note [QK orientation]
// in amx_attn_iface.hpp.
template <size_t group_heads>
  requires(group_heads_ok(group_heads))
void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const bf16* q_packed,
    float* s,
    size_t s_stride_floats) noexcept {
  // The view's data pointer is token 0's row; the tile loads below read the 64
  // consecutive 128-dim rows behind it, which is what the view type promises.
  const bf16* const k_rows = k_page.data;
  // The tiles produce the scores transposed: s_transposed[token][query].
  alignas(64) float s_transposed[PAGE_TOKENS_64 * TILE_ROWS_16];
  _tile_zero(ACCUMULATOR_TILE_0);
  _tile_zero(ACCUMULATOR_TILE_1);
  _tile_zero(ACCUMULATOR_TILE_2);
  _tile_zero(ACCUMULATOR_TILE_3);
  for (size_t step = 0; step < HEAD_SIZE_128 / DIM_STEP_32; step++) {
    _tile_loadd(
        Q_TILE_6, q_packed + step * TILE_ROWS_16 * DIM_STEP_32, TILE_ROW_BYTES_64);
    _tile_loadd(K_EVEN_BLOCK_TILE_4,
        k_rows + 0 * TILE_ROWS_16 * HEAD_SIZE_128 + step * DIM_STEP_32, BF16_ROW_BYTES);
    _tile_dpbf16ps(ACCUMULATOR_TILE_0, K_EVEN_BLOCK_TILE_4, Q_TILE_6);
    _tile_loadd(K_ODD_BLOCK_TILE_5,
        k_rows + 1 * TILE_ROWS_16 * HEAD_SIZE_128 + step * DIM_STEP_32, BF16_ROW_BYTES);
    _tile_dpbf16ps(ACCUMULATOR_TILE_1, K_ODD_BLOCK_TILE_5, Q_TILE_6);
    _tile_loadd(K_EVEN_BLOCK_TILE_4,
        k_rows + 2 * TILE_ROWS_16 * HEAD_SIZE_128 + step * DIM_STEP_32, BF16_ROW_BYTES);
    _tile_dpbf16ps(ACCUMULATOR_TILE_2, K_EVEN_BLOCK_TILE_4, Q_TILE_6);
    _tile_loadd(K_ODD_BLOCK_TILE_5,
        k_rows + 3 * TILE_ROWS_16 * HEAD_SIZE_128 + step * DIM_STEP_32, BF16_ROW_BYTES);
    _tile_dpbf16ps(ACCUMULATOR_TILE_3, K_ODD_BLOCK_TILE_5, Q_TILE_6);
  }
  _tile_stored(ACCUMULATOR_TILE_0, s_transposed + 0 * TILE_FP32S, TILE_ROW_BYTES_64);
  _tile_stored(ACCUMULATOR_TILE_1, s_transposed + 1 * TILE_FP32S, TILE_ROW_BYTES_64);
  _tile_stored(ACCUMULATOR_TILE_2, s_transposed + 2 * TILE_FP32S, TILE_ROW_BYTES_64);
  _tile_stored(ACCUMULATOR_TILE_3, s_transposed + 3 * TILE_FP32S, TILE_ROW_BYTES_64);

  // Transpose s_transposed(64x16) -> s rows 0..group_heads-1 only. Stages 1
  // and 2 (the unpack loop below) are the same for both group sizes; the
  // store helper emits stages 3 and 4 for lane 0 (rows 0..3) always and for
  // lanes 1..3 (rows 4..15) only when group_heads is 16.
  for (int r = 0; r < 4; r++) {
    const float* src = s_transposed + r * TILE_FP32S;
    __m512 u[4][4];
    // row_group: which 4-row group of the 16x16 tile this pass interleaves
    // (rows 4*row_group .. 4*row_group+3).
    for (int row_group = 0; row_group < 4; row_group++) {
      __m512 r0 = _mm512_loadu_ps(src + (4 * row_group + 0) * 16);
      __m512 r1 = _mm512_loadu_ps(src + (4 * row_group + 1) * 16);
      __m512 r2 = _mm512_loadu_ps(src + (4 * row_group + 2) * 16);
      __m512 r3 = _mm512_loadu_ps(src + (4 * row_group + 3) * 16);
      __m512 t0 = _mm512_unpacklo_ps(r0, r1);
      __m512 t1 = _mm512_unpackhi_ps(r0, r1);
      __m512 t2 = _mm512_unpacklo_ps(r2, r3);
      __m512 t3 = _mm512_unpackhi_ps(r2, r3);
      u[row_group][0] = _mm512_castpd_ps(
          _mm512_unpacklo_pd(_mm512_castps_pd(t0), _mm512_castps_pd(t2)));
      u[row_group][1] = _mm512_castpd_ps(
          _mm512_unpackhi_pd(_mm512_castps_pd(t0), _mm512_castps_pd(t2)));
      u[row_group][2] = _mm512_castpd_ps(
          _mm512_unpacklo_pd(_mm512_castps_pd(t1), _mm512_castps_pd(t3)));
      u[row_group][3] = _mm512_castpd_ps(
          _mm512_unpackhi_pd(_mm512_castps_pd(t1), _mm512_castps_pd(t3)));
    }
    float* const s_block = s + r * 16;
    store_transposed_rows<0>(u, s_block, s_stride_floats);
    if constexpr (group_heads == GROUP_HEADS_16) {
      store_transposed_rows<1>(u, s_block, s_stride_floats);
      store_transposed_rows<2>(u, s_block, s_stride_floats);
      store_transposed_rows<3>(u, s_block, s_stride_floats);
    }
  }
}

template <size_t group_heads>
  requires(group_heads_ok(group_heads))
void weights_times_v_128x4(
    v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page,
    const float* exp_rows,
    size_t row_stride_floats,
    float* o) noexcept {
  // The packed plane's first element; pair row s*16 starts s*16*2*128 elements
  // later (Note [VNNI Packed V layout] in h/tron/tensor/v_vnni.hpp). This kernel is
  // one of the two layout-specific readers allowed to take the plane address.
  const bf16* const v_pairs = detail::v_vnni_access::plane(v_page);
  // o holds 16 rows x 128 floats; see Note [Tile stores write 16 rows].
  // P: 16 rows x 64 bf16 bit patterns (the AVX-512 convert instruction
  // writes raw 16-bit lanes, so this scratch stays uint16_t); rows
  // group_heads..15 are zero padding (never written after thread init), so
  // the padded tile rows contribute nothing. A function template's static
  // locals exist once per specialization. This scratch therefore belongs to
  // the 4-head or the 16-head instantiation only, and a 4-head call never
  // sees a 16-head call's rows. For 16 heads every row is written, so there
  // is no padding.
  alignas(64) thread_local uint16_t P[TILE_ROWS_16][PAGE_TOKENS_64] = {};
  for (size_t q = 0; q < group_heads; q++) {
    for (size_t c = 0; c < PAGE_TOKENS_64; c += 32) {
      __m512 lo = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c);
      __m512 hi = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c + 16);
      // cvtne2ps_pbh(a, b) puts b in the low 16 lanes, so (hi, lo) keeps the
      // tokens in order.
      _mm512_storeu_si512(P[q] + c, (__m512i)_mm512_cvtne2ps_pbh(hi, lo));
    }
  }
  constexpr size_t P_ROW_BYTES = PAGE_TOKENS_64 * sizeof(uint16_t);
  for (int half = 0; half < 2; half++) {
    _tile_zero(ACCUMULATOR_TILE_0);
    _tile_zero(ACCUMULATOR_TILE_1);
    _tile_zero(ACCUMULATOR_TILE_2);
    _tile_zero(ACCUMULATOR_TILE_3);
    for (int s = 0; s < 2; s++) {
      _tile_loadd(P_TILE_4, &P[0][s * DIM_STEP_32], P_ROW_BYTES);
      _tile_loadd(V_EVEN_SLICE_TILE_5,
          v_pairs + s * TILE_ROWS_16 * HEAD_SIZE_128 * V_PAIR_TOKENS_2 +
              (half * PV_TILES_PER_HALF_4) * DIM_STEP_32,
          V_PAIR_ROW_BYTES);
      _tile_dpbf16ps(ACCUMULATOR_TILE_0, P_TILE_4, V_EVEN_SLICE_TILE_5);
      _tile_loadd(V_ODD_SLICE_TILE_6,
          v_pairs + s * TILE_ROWS_16 * HEAD_SIZE_128 * V_PAIR_TOKENS_2 +
              (half * PV_TILES_PER_HALF_4 + 1) * DIM_STEP_32,
          V_PAIR_ROW_BYTES);
      _tile_dpbf16ps(ACCUMULATOR_TILE_1, P_TILE_4, V_ODD_SLICE_TILE_6);
      _tile_loadd(V_EVEN_SLICE_TILE_5,
          v_pairs + s * TILE_ROWS_16 * HEAD_SIZE_128 * V_PAIR_TOKENS_2 +
              (half * PV_TILES_PER_HALF_4 + 2) * DIM_STEP_32,
          V_PAIR_ROW_BYTES);
      _tile_dpbf16ps(ACCUMULATOR_TILE_2, P_TILE_4, V_EVEN_SLICE_TILE_5);
      _tile_loadd(V_ODD_SLICE_TILE_6,
          v_pairs + s * TILE_ROWS_16 * HEAD_SIZE_128 * V_PAIR_TOKENS_2 +
              (half * PV_TILES_PER_HALF_4 + 3) * DIM_STEP_32,
          V_PAIR_ROW_BYTES);
      _tile_dpbf16ps(ACCUMULATOR_TILE_3, P_TILE_4, V_ODD_SLICE_TILE_6);
    }
    _tile_stored(ACCUMULATOR_TILE_0, o + half * 64 + 0, O_ROW_BYTES);
    _tile_stored(ACCUMULATOR_TILE_1, o + half * 64 + 16, O_ROW_BYTES);
    _tile_stored(ACCUMULATOR_TILE_2, o + half * 64 + 32, O_ROW_BYTES);
    _tile_stored(ACCUMULATOR_TILE_3, o + half * 64 + 48, O_ROW_BYTES);
  }
}

// The kernel bodies live only in this translation unit, so this list is the
// set of group sizes callers can use: it equals group_heads_ok in
// amx_attn_iface.hpp.
template void pack_q_group_128x4<GROUP_HEADS_4>(const bf16*, bf16*) noexcept;
template void pack_q_group_128x4<GROUP_HEADS_16>(const bf16*, bf16*) noexcept;
template void qk_rowmajor_128x4<GROUP_HEADS_4>(
    const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>,
    const bf16*,
    float*,
    size_t) noexcept;
template void qk_rowmajor_128x4<GROUP_HEADS_16>(
    const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>,
    const bf16*,
    float*,
    size_t) noexcept;
template void weights_times_v_128x4<GROUP_HEADS_4>(
    v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const float*,
    size_t,
    float*) noexcept;
template void weights_times_v_128x4<GROUP_HEADS_16>(
    v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const float*,
    size_t,
    float*) noexcept;

}  // namespace tron::amx_attn_h128g4
