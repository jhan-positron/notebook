#pragma once
// This file defines typed access to the K plane stored in the VNNI layout
// (TRON_K_VNNI): an owner that holds the bytes (k_vnni_tensor), a matrix view
// that knows the address formula (k_vnni_view), the index map and its
// constants (namespace k_vnni), and the vector operations that move whole token
// rows in and out (store_row, load_row, copy_token). The AVX-512
// score reader of this layout is in h/tron/kernels/k_vnni.hpp. Who writes and
// reads the layout is described in Note [K VNNI storage] (kv_cache.hpp).
//
// Words used here: AMX (Advanced Matrix Extensions) is the tile instruction
// set of the CPU. AVX-512 (Advanced Vector Extensions) is the CPU's 512-bit
// vector instruction set. bf16 is the 16-bit brain floating-point format. VNNI
// (Vector Neural Network Instructions) layout means that the two values of a
// dimension pair of one token are stored next to each other. One 64-byte row
// holds that dimension pair for 16 consecutive tokens. The VNNI layout is the
// B-operand layout of the AMX tile multiply (TDPBF16PS). It is also the operand
// layout of the AVX-512 pair dot product (VDPBF16PS). A KV page holds 64
// tokens. The layout exists for 128-dimension heads only. A plane is K for one
// KV head of one page.
//
// Plane layout (64 tokens x 128 dimensions of bf16 = 16 KiB, the same bytes as the
// row-major plane), indexed by dimension step s (32 dimensions), token block c (16
// tokens), dimension pair dp and token t:
//   plane[(((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j] == K[c * 16 + t][s * 32 + 2 * dp
//   + j]
// One (s, c) is one 1 KiB panel: 16 dimension-pair rows of 64 bytes. A panel is
// exactly one AMX B tile. Token i owns column (i % 16) of token block (i / 16)
// in every panel. So tokens are written independently (no read-modify-write
// between tokens, unlike the pair-interleaved V plane).
//
// Who may compute a packed address: the typed operations in this header, and
// the layout-specific score reader (k_vnni::qk_group), which reaches the plane
// through detail::k_vnni_access. Cache code, the model, hardware staging and the tests
// use the typed operations or the page accessors built on them (page::set_k_row,
// page::get_k_row, page::score_k). book::fill_random is the
// one documented exception: it fills a whole kv_block without interpreting
// coordinates.

#include <concepts>
#include <cstddef>
#include <cstdint>
#include <immintrin.h>
#include <type_traits>

#include "common/assert.hpp"
#include "common/attributes.hpp"
#include "common/numerics/bf16.hpp"
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/seq.hpp"
#include "tron/tensor/view.hpp"

namespace tron {

namespace k_vnni {

inline constexpr size_t PAGE_TOKENS_64 = 64;
inline constexpr size_t HEAD_SIZE_128 = 128;
// The two values of one dimension pair share one 32-bit lane.
inline constexpr size_t PAIR_2 = 2;
inline constexpr size_t DWORD_BYTES_4 = 4;
// One 64-byte line holds one dimension pair of 16 consecutive tokens.
inline constexpr size_t LINE_BYTES_64 = 64;
inline constexpr size_t BLOCK_TOKENS_16 = LINE_BYTES_64 / (PAIR_2 * sizeof(bf16));
inline constexpr size_t TOKEN_BLOCKS_4 = PAGE_TOKENS_64 / BLOCK_TOKENS_16;
inline constexpr size_t STEP_DIMS_32 = 32;
inline constexpr size_t STEP_PAIRS_16 = STEP_DIMS_32 / PAIR_2;
inline constexpr size_t DIM_STEPS_4 = HEAD_SIZE_128 / STEP_DIMS_32;
inline constexpr size_t ROW_ELEMS_32 = LINE_BYTES_64 / sizeof(bf16);
inline constexpr size_t ROW_DWORDS_16 = LINE_BYTES_64 / DWORD_BYTES_4;
inline constexpr size_t PANEL_ELEMS_512 = STEP_PAIRS_16 * BLOCK_TOKENS_16 * PAIR_2;
inline constexpr size_t PANEL_BYTES_1024 = PANEL_ELEMS_512 * sizeof(bf16);
inline constexpr size_t PANEL_DWORDS_256 = PANEL_BYTES_1024 / DWORD_BYTES_4;
inline constexpr size_t N_PANELS_16 = DIM_STEPS_4 * TOKEN_BLOCKS_4;
// Width of a bf16: a bf16 shifted up by this many bits is the exact fp32.
inline constexpr int BF16_BITS_16 = 16;
// The high half of a dword: the odd value of a dimension pair as an fp32 bit pattern.
inline constexpr uint32_t HIGH_HALF_0XFFFF0000 = 0xffff0000u;
static_assert(BLOCK_TOKENS_16 == 16 && TOKEN_BLOCKS_4 == 4 && STEP_PAIRS_16 == 16 &&
                  DIM_STEPS_4 == 4 && ROW_ELEMS_32 == 32 && ROW_DWORDS_16 == 16 &&
                  PANEL_ELEMS_512 == 512 && PANEL_BYTES_1024 == 1024 &&
                  PANEL_DWORDS_256 == 256 && N_PANELS_16 == 16,
    "every constant's name states its value");
static_assert(N_PANELS_16 * PANEL_ELEMS_512 == PAGE_TOKENS_64 * HEAD_SIZE_128,
    "the VNNI plane is a permutation of the row-major plane: same element count");

// The layout gate. TRON_K_VNNI is a CMake option. The gate depends on the head
// size only, not on the query type or on AMX availability. So every reader and
// writer of a slot sees the same layout.
#ifdef TRON_K_VNNI
template <size_t head_size>
inline constexpr bool layout_on = head_size == HEAD_SIZE_128;
#else
template <size_t head_size>
inline constexpr bool layout_on = false;
#endif

// Element index of K[token][dim] inside the plane (the formula of the header
// comment).
constexpr size_t index(size_t token, size_t dim) noexcept {
  const size_t s = dim / STEP_DIMS_32, c = token / BLOCK_TOKENS_16,
               dp = (dim % STEP_DIMS_32) / PAIR_2, t = token % BLOCK_TOKENS_16,
               j = dim % PAIR_2;
  return (((s * TOKEN_BLOCKS_4 + c) * STEP_PAIRS_16 + dp) * BLOCK_TOKENS_16 + t) *
             PAIR_2 +
         j;
}

}  // namespace k_vnni

namespace detail {
// The one route from a packed K view to its plane address. Its users are listed
// in Note [K VNNI storage] (kv_cache.hpp).
struct k_vnni_access;
}  // namespace detail

template <typename T>
concept k_vnni_element = std::same_as<T, bf16> || std::same_as<T, const bf16>;

// A VNNI packed K plane of [Rows tokens * Cols dimensions]. There is no element write:
// rows enter only through store_row and copy_token. There is no public pointer
// access: a bare pointer does not say which layout it points at.
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view final {
  static_assert(k_vnni_element<T>, "a packed K plane holds bf16 or const bf16");
  // k_vnni::index is written for 4 token blocks and 4 dimension steps.
  static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128,
      "the K VNNI layout exists for 64-token pages of 128-dimension heads only");

  template <typename U>
    requires(std::is_const_v<T> && std::same_as<U, std::remove_const_t<T>>)
  TRON(inline)
  k_vnni_view(k_vnni_view<U, Rows, Cols> other) noexcept
  : data_(other.data_) {}

  TRON(nodiscard, inline, pure)
  const bf16& at(size_t token, size_t dim) const noexcept {
    TRON_ASSERT_LT(token, Rows);
    TRON_ASSERT_LT(dim, Cols);
    return data_[k_vnni::index(token, dim)];
  }

private:
  friend struct k_vnni_tensor<Rows, Cols>;
  friend struct detail::k_vnni_access;
  template <typename U, size_t R, size_t C>
  friend struct k_vnni_view;

  TRON(inline)
  explicit k_vnni_view(T* data) noexcept
  : data_(data) {}

  T* data_;
};

// Owns one VNNI packed K plane. No initialization: the cache's DMA allocation creates
// the kv_blocks that hold it (Note [KV block lifetime] in kv_cache.hpp). 64-byte
// alignment: every pair row is one 64-byte line.
template <size_t Rows, size_t Cols>
struct alignas(64) k_vnni_tensor final {
  static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128,
      "the K VNNI layout exists for 64-token pages of 128-dimension heads only");

  TRON(nodiscard, inline)
  k_vnni_view<bf16, Rows, Cols> as_view() & noexcept TRON(this_lifetimebound)
  {
    return k_vnni_view<bf16, Rows, Cols>(data_);
  }

  TRON(nodiscard, inline)
  k_vnni_view<const bf16, Rows, Cols> as_view() const& noexcept TRON(this_lifetimebound)
  {
    return k_vnni_view<const bf16, Rows, Cols>(data_);
  }

  k_vnni_view<bf16, Rows, Cols> as_view() && = delete;
  k_vnni_view<const bf16, Rows, Cols> as_view() const&& = delete;

private:
  alignas(64) bf16 data_[Rows * Cols];
};
static_assert(
    sizeof(k_vnni_tensor<k_vnni::PAGE_TOKENS_64, k_vnni::HEAD_SIZE_128>) ==
            k_vnni::PAGE_TOKENS_64 * k_vnni::HEAD_SIZE_128 * sizeof(bf16) &&
        alignof(k_vnni_tensor<k_vnni::PAGE_TOKENS_64, k_vnni::HEAD_SIZE_128>) == 64,
    "the owner is the plane: the same bytes as the row-major K plane, 64-byte aligned");

namespace detail {
struct k_vnni_access final {
  template <typename T, size_t Rows, size_t Cols>
  TRON(nodiscard, inline, pure)
  static T* plane(k_vnni_view<T, Rows, Cols> k) noexcept {
    return k.data_;
  }
};
}  // namespace detail

// Transfer rows: one token's values in dimension order, not packed storage.
// Aligned is not a precondition (unlike the packed V rows): store_row and load_row
// use unaligned loads and stores.
template <size_t Cols, bool Aligned = true, bool Dma = false>
using const_k_row_view = const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;

template <size_t Cols, bool Aligned = true, bool Dma = false>
using k_row_view = view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;

template <size_t Cols, bool Aligned = true, bool Dma = false>
TRON(nodiscard, inline)
const_k_row_view<Cols, Aligned, Dma> k_source_row(const bf16* row) noexcept {
  return const_k_row_view<Cols, Aligned, Dma>{row};
}

template <size_t Cols, bool Aligned, bool Dma, ptrdiff_t Stride>
  requires(Stride == 1)
TRON(nodiscard, inline)
const_k_row_view<Cols, Aligned, Dma> k_source_row(
    view<bf16, Aligned, Dma, seq<Cols>, sseq<Stride>> row) noexcept {
  return const_k_row_view<Cols, Aligned, Dma>{row};
}

template <size_t Cols, bool Aligned = true, bool Dma = false>
TRON(nodiscard, inline)
k_row_view<Cols, Aligned, Dma> k_destination_row(bf16* row) noexcept {
  return k_row_view<Cols, Aligned, Dma>{row};
}

namespace k_vnni::detail {
// The byte address of dimension pair 0 of dimension step s for token `token`.
TRON(inline)
char* pair_base(bf16* plane, size_t s, size_t token) noexcept {
  const size_t c = token / BLOCK_TOKENS_16, t = token % BLOCK_TOKENS_16;
  return reinterpret_cast<char*>(plane) +
         ((s * TOKEN_BLOCKS_4 + c) * PANEL_DWORDS_256 + t) * DWORD_BYTES_4;
}
TRON(inline)
const char* pair_base(const bf16* plane, size_t s, size_t token) noexcept {
  const size_t c = token / BLOCK_TOKENS_16, t = token % BLOCK_TOKENS_16;
  return reinterpret_cast<const char*>(plane) +
         ((s * TOKEN_BLOCKS_4 + c) * PANEL_DWORDS_256 + t) * DWORD_BYTES_4;
}
// Dword offsets of the 16 pair rows of one panel (64 bytes = 16 dwords apart).
TRON(inline)
__m512i pair_row_offsets() noexcept {
  constexpr int ROW_STRIDE_16 = int(ROW_DWORDS_16);
  return _mm512_set_epi32(15 * ROW_STRIDE_16, 14 * ROW_STRIDE_16, 13 * ROW_STRIDE_16,
      12 * ROW_STRIDE_16, 11 * ROW_STRIDE_16, 10 * ROW_STRIDE_16, 9 * ROW_STRIDE_16,
      8 * ROW_STRIDE_16, 7 * ROW_STRIDE_16, 6 * ROW_STRIDE_16, 5 * ROW_STRIDE_16,
      4 * ROW_STRIDE_16, 3 * ROW_STRIDE_16, 2 * ROW_STRIDE_16, 1 * ROW_STRIDE_16, 0);
}
}  // namespace k_vnni::detail

// Store one token's K row into a packed plane. Only this token's 64 pair slots
// are written.
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void store_row(k_vnni_view<bf16, Rows, Cols> dst,
    size_t token,
    const_k_row_view<Cols, Aligned, Dma> src) noexcept {
  TRON_ASSERT_LT(token, Rows);
  bf16* const plane = detail::k_vnni_access::plane(dst);
  const bf16* const row = src.data;
  const __m512i offsets = k_vnni::detail::pair_row_offsets();
  for (size_t s = 0; s < k_vnni::DIM_STEPS_4; ++s) {
    const __m512i pairs = _mm512_loadu_si512(row + s * k_vnni::STEP_DIMS_32);
    _mm512_i32scatter_epi32(k_vnni::detail::pair_base(plane, s, token), offsets, pairs,
        k_vnni::DWORD_BYTES_4);
  }
}

// The inverse of store_row: load one token's K row out of a packed plane.
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void load_row(k_vnni_view<const bf16, Rows, Cols> src,
    size_t token,
    k_row_view<Cols, Aligned, Dma> dst) noexcept {
  TRON_ASSERT_LT(token, Rows);
  const bf16* const plane = detail::k_vnni_access::plane(src);
  bf16* const row = dst.data;
  const __m512i offsets = k_vnni::detail::pair_row_offsets();
  for (size_t s = 0; s < k_vnni::DIM_STEPS_4; ++s) {
    const __m512i pairs = _mm512_i32gather_epi32(
        offsets, k_vnni::detail::pair_base(plane, s, token), k_vnni::DWORD_BYTES_4);
    _mm512_storeu_si512(row + s * k_vnni::STEP_DIMS_32, pairs);
  }
}

// Copy one token between packed K planes, or within one plane. The token indices
// are checked by load_row and store_row.
template <size_t Rows, size_t Cols>
TRON(inline)
void copy_token(k_vnni_view<bf16, Rows, Cols> dst,
    size_t dst_token,
    k_vnni_view<const bf16, Rows, Cols> src,
    size_t src_token) noexcept {
  alignas(64) bf16 row[Cols];
  load_row(src, src_token, k_destination_row<Cols>(row));
  store_row(dst, dst_token, k_source_row<Cols>(row));
}

}  // namespace tron

