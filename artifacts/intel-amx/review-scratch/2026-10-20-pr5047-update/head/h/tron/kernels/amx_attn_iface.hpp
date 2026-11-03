#pragma once
// Interface to the AMX software-attention kernels. This header contains no
// intrinsics, so any translation unit may include it; the implementations live in
// src/tron/kernels/amx_attn.cpp, the only translation unit compiled with
// -mamx-tile/-mamx-bf16. See Note [AMX attention dispatch].
//
// Words used here: AMX is Intel Advanced Matrix Extensions, the tile-matrix
// instruction set. AVX-512 is the vector instruction set the existing
// attention code (the "dotter") uses. QK is the query-key score product and
// PV the product of the softmax weights with V. bf16 is bfloat16, the 2-byte
// floating-point format K, V and (for eligible executors) Q are stored in.
// A KV page holds 64 tokens. GQA (grouped-query attention) lets several query
// heads share one KV head; kv_mul is that ratio. The kernels serve one shape:
// head size 128 and kv_mul 4, hence the namespace name amx_attn_h128g4 and
// the _128x4 suffix of every kernel.

// Note [AMX attention dispatch]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// TRON_AMX_DISPATCH (CMake option, default OFF) adds an opt-in AMX fast path
// to software attention for the dense case only: a full 64-token page, all
// of it visible to the query and inside the sliding window, on a model with
// head size 128 and kv_mul 4 whose executor stores activations as bf16
// (amx_attn_h128g4::eligible = shape_ok + query_scalar_ok). One GQA group of
// that shape is 4 query heads x 128 dims = 512 bf16 = 1024 bytes. Packed as
// the B operand, it occupies 4096 bytes: four panels of 16 columns, 4 of them
// the query heads and 12 zero padding; the K operand fills its tiles
// completely (64 tokens = 4 tiles of 16 rows). Everything else, incomplete
// or partially visible pages, pages outside the sliding window, other
// geometries, other activation types, runs the existing AVX-512 dotter loop
// unchanged. The unit of the decision is the (query, page) pair, not the
// query: a query runs its complete pages on AMX and its partial tail page on AVX.
//
// Safety chain, in order:
//   1. compile time: TRON_AMX_DISPATCH off: the kernel translation unit is
//      not compiled and every dispatch block is excluded (this header's
//      declarations and constexpr gate predicates remain).
//   2. compile time: the executor's activation scalar. The query packer
//      copies Q as bf16 and converts nothing, so executors whose btensor_t
//      element is float (host) or fp16 (host_fp16) compile no fast path
//      (query_scalar_ok) and keep the AVX dotter, which reads Q with its own
//      type.
//   3. process start: available() = CPUID leaf 7.0 EDX bits 22 (AMX-BF16) and
//      24 (AMX-TILE), XCR0 bits 17 and 18 (the OS enabled tile state), and
//      arch_prctl(ARCH_REQ_XCOMP_PERM), the per-process permission Linux
//      requires; the result is cached. Hosts without AMX (feature bits, not
//      vendor strings, so AMD hosts too) run the AVX path.
//   4. runtime disable: TRON_AMX_DISABLE=1 in the environment makes
//      available() false. Contract: AMX off, same layout, same AVX dotter,
//      clean-binary numerics; it exists for same-binary A/B tests and for
//      rollback. It will be listed in the TRON environment-variable document
//      (https://github.com/positron-ai/tron/issues/4338).
//   5. per page: the dense-case predicate above, evaluated per (query, page)
//      in self_attention.hpp (is_dense_amx_page).
//
// Contract with the caller's per-page softmax update, per 64-token page:
//
//   inputs: q (4 heads x 128 bf16), K page, V page (64 x 128 bf16)
//      |
//   QK kernel   ->  s_pages[4][64] fp32, raw q.k (UNSCALED)
//      |            AVX: dotter<bf16,128> per token | AMX: qk_rowmajor_128x4 per page
//      |                 (VNNI K: k_vnni::qk_group)  |      (VNNI K: not taken until
//      |                                              |      the VNNI AMX kernel lands)
//   caller      ->  s *= scale (or tanh softcap); m_page = max(s, m*)
//                   P = exp(s - m_page) fp32; sum(P)
//
//   PV kernel   ->  O[4][128] = bf16(P) . V
//      |            AVX: P truncated to bf16 | AMX: P rounded to nearest even
//   caller      ->  c = exp(m*_old - m_new)
//                   v* = v*.c + O; s* = s*.c + sum(P); m* = m_new
//
// The QK kernel writes raw dot products q.k, not yet multiplied by the
// attention scale and not yet softcapped, into s_pages[4][64], the same array
// and layout the AVX dotter loop fills. The caller does everything after
// that: the scale (or tanh softcap), the page max, exp(s - max), and the
// v*/s*/m* running-softmax update.
// Numerics: both code paths (AVX-512 and AMX) multiply bf16 inputs and add
// the products in fp32, in QK and in PV. For inputs that are finite and not
// subnormal, their outputs differ for exactly two reasons:
//   1. the bf16 rounding of the PV weights P = exp(s - max): the AVX path
//      truncates (drops the low 16 bits), the AMX path rounds to nearest
//      even (VCVTNE2PS2BF16). A truncating version is a one-line change
//      at the cvtne2ps_pbh call if AVX-style rounding is ever required;
//      the add-order difference below would remain;
//   2. the order in which the fp32 products are added.
// t/t_amx_numerics.cpp checks that the kernels stay within the error band
// those two causes allow, so any other change (wrong index, dropped token,
// lower precision) fails.
//
// Tile configuration is per-thread state: begin_region()/end_region()
// encloses one worker's page loop (begin_region() loads the 8x(16x64B) config,
// end_region() executes TILERELEASE).
//
// Note [Tile stores write 16 rows]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// Every tile in these kernels is 16 rows x 64 bytes, and TILESTORED has no
// "store only 4 rows" mode: storing a result tile writes all 16 configured
// rows to memory. weights_times_v_128x4 stores its result tiles directly into
// the memory the caller passed in (`o`), so `o` must have room for 16 rows of
// 128 fp32 (8192 bytes) even though only rows 0..3 (one row per query head)
// hold real data. Passing a buffer sized for the 4 real rows causes a silent
// overrun: rows 4..15 are written past its end, nothing reports an error, and
// whatever follows the buffer in memory is corrupted. Rows 4..15 of `o` are
// the products of the kernel's zero padding rows of P (output row i of a tile
// multiply comes from row i of the A operand); callers read rows 0..3 and
// ignore the rest.
// qk_rowmajor_128x4 stores its result tiles into a buffer inside the kernel
// (s_transposed), and the transpose that reads that buffer writes only the 4
// query rows into the caller's `s`, so `s` needs only 4 rows
// (s[4][s_stride_floats]).

#include <cstddef>
#include <type_traits>

#include "common/numerics/bf16.hpp"
#include "tron/tensor/kv_cache_fwd.hpp"

namespace tron::amx_attn_h128g4 {

// The Q, packed-Q, K and V buffers hold tron::bf16 objects, whose 2-byte
// representation the tile instructions read directly; scores, softmax weights
// and outputs are fp32.
static_assert(sizeof(bf16) == 2, "the AMX kernels assume 2-byte bf16 elements");
static_assert(std::is_trivially_copyable_v<bf16>,
    "the query packer copies bf16 objects by value");

// Tile geometry shared by every kernel below. begin_region() configures all
// 8 tiles as 16 rows x 64 bytes. A tile store (TILESTORED) always writes all
// 16 rows, even when only 4 of them hold real data (see Note [Tile stores
// write 16 rows]). Only one caller buffer receives a tile store directly: the
// output `o` of weights_times_v_128x4. The caller must therefore allocate `o`
// with TILE_ROWS_16 rows, not 4.
inline constexpr size_t TILE_ROWS_16 = 16;
inline constexpr size_t TILE_ROW_BYTES_64 = 64;

// The one attention shape these kernels serve (Note [AMX attention
// dispatch]): a 64-token KV page, 128-dim heads, and 4 query heads per KV
// head (4 x 128 bf16 = 1024 bytes per query group). The kernel's shape
// constants derive from these three.
inline constexpr size_t PAGE_TOKENS_64 = 64;
inline constexpr size_t HEAD_SIZE_128 = 128;
inline constexpr size_t GROUP_HEADS_4 = 4;

// One packed Q group (the pack_q_group_128x4 output buffer): 4 panels x 16
// dim-pair rows x 16 columns x 2 = 2048 bf16 = 4096 bytes, padding included.
inline constexpr size_t Q_PACK_ELEMS_2048 = TILE_ROWS_16 * HEAD_SIZE_128;
static_assert(Q_PACK_ELEMS_2048 == 2048, "the constant's name states its value");

// The shape half of the gate: the AMX kernels serve exactly one attention
// shape, 4 query heads x 128 dims per KV head (see
// Note [AMX attention dispatch]).
constexpr bool shape_ok(size_t model_head_size, size_t model_kv_mul) noexcept {
  return model_head_size == HEAD_SIZE_128 && model_kv_mul == GROUP_HEADS_4;
}

// The scalar half of the gate: pack_q_group_128x4 takes `const bf16*` and
// copies the values without conversion, so the executor's activation scalar
// (btensor_t<N>::element, the type of the Q buffer) must be bf16.
// tp*/perm_tp*/host_bf16 store bf16; host stores float and host_fp16 stores
// fp16 (common.hpp). Those executors keep the AVX dotter path, which reads Q
// with its own type.
template <typename query_scalar_t>
inline constexpr bool query_scalar_ok = std::is_same_v<query_scalar_t, bf16>;

// The gate the dispatch evaluates: shape and scalar must both hold.
template <typename query_scalar_t>
constexpr bool eligible(size_t model_head_size, size_t model_kv_mul) noexcept {
  return shape_ok(model_head_size, model_kv_mul) && query_scalar_ok<query_scalar_t>;
}

// True when the CPU, the OS, and the per-process permission all allow AMX,
// and TRON_AMX_DISABLE is not `1`. Probed once; the result is cached for the
// process lifetime. See Note [AMX attention dispatch].
bool available() noexcept;

// Pack one query group (4 query heads x 128 dims, contiguous bf16) into the
// tile B-operand (VNNI pair-interleaved) layout consumed by
// qk_rowmajor_128x4. VNNI (Vector Neural Network Instructions) layout means
// that consecutive pairs of a row are stored next to each other so that one
// tile row holds one dim pair for 16 columns.
// `packed` must hold Q_PACK_ELEMS_2048 bf16 (4096 bytes), aligned to 64
// bytes, with columns 4..15 of every panel already zero: this call writes
// columns 0..3 only, so a buffer zeroed once at allocation stays valid for
// every pack.
// `packed` layout: 4 panels, one per 32-dim step of the head; each panel is
// 16 dim-pair rows x 16 query columns (columns 0..3 = the 4 heads, columns
// 4..15 zero padding) x 2 paired values:
//   packed[((step * 16 + dim_pair) * 16 + q_head) * 2 + j]
//     == q_group[q_head * 128 + step * 32 + 2 * dim_pair + j]
void pack_q_group_128x4(const bf16* q_group, bf16* packed) noexcept;

// Note [QK orientation]
// ~~~~~~~~~~~~~~~~~~~~~
// The AMX bf16 tile multiply (TDPBF16PS) accepts a row-major matrix only as
// its left operand (A); the right operand (B) must be in the VNNI
// pair-interleaved layout. Stored K is row-major (one 128-dim bf16 row per
// token) and K is larger than Q, so pick K as A operand and the packed Q group
// as B operand. The product then comes out transposed, S^T[token][head],
// and the kernel transposes the 4 useful query rows on the way out. That
// transpose is the price of reading K exactly as stored.
//
// How qk_rowmajor_128x4 computes S^T = K_page . Q^T, step by step:
//
// - A operand = K as stored. The K page is 64 tokens x 128 dims, one bf16
//   row per token. Each tile load takes 16 tokens x 32 dims (one DIM_STEP_32).
//   Four 16-token slices x four dim steps cover the page; tile registers 4
//   and 5 are reused for the K loads.
// - B operand = packed Q. The 4 query heads of the group are packed as 16
//   columns (4 heads + 12 padding columns the caller keeps zero) in the VNNI
//   pair-interleaved layout, one panel per dim step.
// - Tile product. Each _tile_dpbf16ps adds one step's 32-dim partial dot
//   into a 16 x 16 fp32 tile. After the four steps, entry [token][column]
//   is K[token] . Q[column], and the four tiles hold S^T, 64 x 16, of which
//   only columns 0..3 are real heads.
// - Store, then transpose. The four tiles are stored into an internal 64 x 16
//   buffer; an AVX-512 register transpose then writes columns 0..3 as rows
//   into s[head][token], the same 4 x 64 layout the AVX dotter loop fills.

// Dense QK for one page: computes S^T = K_page . Q^T in tiles and transposes
// on the way out (see Note [QK orientation]); writes s[4][s_stride_floats]
// fp32, all 64 token columns, UNSCALED. k_page = the page's whole native K
// plane, 64 tokens x 128 dims bf16 row-major (the kv_block K storage), passed
// as its typed view so that a packed V plane or a bare pointer cannot be handed
// in by mistake; q_packed = the pack_q_group_128x4 output.
void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const bf16* q_packed,
    float* s,
    size_t s_stride_floats) noexcept;

// Weights-times-values for one page: O = P[4][64] . V_page, where P (the
// exponentiated scores, i.e. the unnormalized softmax weights) comes from the
// caller's fp32 exp rows (converted to bf16 inside) and v_page is the page's
// packed V plane (v_vnni_view, see Note [VNNI Packed V layout] in
// h/tron/tensor/v_vnni.hpp), consumed in place as the B operand. `o` MUST hold
// 16 * 128 fp32 (8192 bytes, aligned to 64 bytes, row stride 128 floats);
// see Note [Tile stores write 16 rows].
void weights_times_v_128x4(
    v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page,
    const float* exp_rows,
    size_t row_stride_floats,
    float* o) noexcept;

// Tile-configuration bracket for a worker's AMX region.
// See Note [AMX attention dispatch].
void begin_region() noexcept;
void end_region() noexcept;

}  // namespace tron::amx_attn_h128g4

