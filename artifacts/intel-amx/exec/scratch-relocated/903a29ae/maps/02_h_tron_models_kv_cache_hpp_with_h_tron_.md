# h/tron/models/kv_cache.hpp (with h/tron/tensor/kv_cache_fwd.hpp and h/tron/tensor/v_vnni.hpp as the parent's pattern)

## textual_conflicts
- h/tron/models/kv_cache.hpp worktree 1981-2122 (one block: <<<<<<< HEAD at 1981, ======= at 2072, >>>>>>> origin/jhan-kv-typed-tensors at 2122): Both sides are additions in the same place of struct page, between the native K row overloads and the V accessors. The HEAD side (worktree 1982-2071 = CHILD h/tron/models/kv_cache.hpp:1682-1771 at origin/jhan-amx-vnniK) holds the CHILD's K accessors: page::k_vnni_plane (1682-1693), set_k_row (1695-1710), set_k_block (1712-1731), get_k_row (1733-1748), the two uniform-geometry forms (1750-1765), and then the FIVE comment lines 'Pointer to this page's V values for one KV head ...' (CHILD 1767-1771). Those five lines are the comment of page::v_data, which the PARENT deleted together with v_data and kv_block::v_base (PARENT diff 996f58ec82..origin/jhan-kv-typed-tensors, hunk @@ -1856,79 +1897,63 @@). The PARENT side (worktree 2073-2121) holds the PARENT's new V text: the 'The actual V data for a token in this page.' comment, the `#if TRON_CHUNK_SIZE == 16` packed-V comment, the four templated set_v/get_v declarations taking const_v_row_view / v_row_view, and the v_packed comment. The v_packed definition itself (worktree 2123-2130) is already outside the markers. Resolution: keep the whole HEAD side MINUS the five stale v_data comment lines, then keep the whole PARENT side after it. Order: K accessors first, then '// The actual V data for a token in this page.' and the rest. No line of either side is dropped except those five. After that textual fix the K accessors still do not compile against the PARENT's kv_block (semantic changes below): k_vnni_plane, set_k_row, set_k_block and get_k_row all do reinterpret_cast on kv_block::k, which must become typed calls.

## semantic_changes
- [MUST] h/tron/models/kv_cache.hpp @ kv_block::k (worktree 2638; PARENT kv_cache.hpp:2452 `alignas(kv_block_alignment) bf16 k[page_size * head_size];`; CHILD 2380 `bf16s k[page_size][head_size / chunk_size]`)
  CHANGE: Replace the plain array with a compile-time selection: `using native_k_storage = bf16[page_size * head_size]; using k_storage = std::conditional_t<k_vnni::layout_on<head_size>, k_vnni_tensor<page_size, head_size>, native_k_storage>; alignas(kv_block_alignment) k_storage k;`. Add class-body static_asserts: trivially default-constructible / copyable / destructible k_storage (same wording as the v_storage assert at worktree 2645-2648), `sizeof(k_storage) == page_size * head_size * sizeof(bf16)`, `alignof(k_storage) <= kv_block_alignment`. Keep `static_assert(sizeof(k) == sizeof(v))` (worktree 2656): it holds, both are 64*128*2 = 16384 bytes for the production shape.
  WHY: Design 'Child storage and access': k_vnni_tensor owner selected by std::conditional_t; goal (b) typed owner; goal (c) no raw plane pointer. The PARENT base type is a flat bf16 array, not the design's bf16s[][] (see design_contradictions). The unselected k_vnni_tensor<64,64> (gpt-oss heads with TRON_K_VNNI on) is only named, never instantiated, so its shape checks must be class-body static_asserts, not a class-head requires-clause (design: 'A rejecting class-template constraint would fail before selection').
  EVIDENCE: PARENT kv_cache.hpp:2449-2470 (kv_block with `bf16 k[...]`, v_storage asserts, sizeof(k)==sizeof(v)); design-child-section.txt 'Child storage and access'; v_vnni.hpp:161-185 (owner pattern); book asserts PARENT 1594-1599 require trivial kv_block.
- [MUST] h/tron/models/kv_cache.hpp @ kv_block::k_view() and k_at() (worktree 2659-2682; PARENT 2473-2494)
  CHANGE: Add a trailing `requires(!k_vnni::layout_on<head_size>)` to all four members (two k_view, two k_at), placed after `TRON(this_lifetimebound)` as page::k already does (worktree 1918). Bodies unchanged: `view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<page_size, head_size>>{k}` only compiles when k is an array.
  WHY: Compile necessity: `{k}` needs array-to-pointer decay; a k_vnni_tensor has no pointer conversion (private data_, as v_vnni_tensor). Design: 'Constrain native k_view() and k_at() to the array branch.' page::k overloads (worktree 1915-1979) are already constrained by the CHILD, so no caller reaches k_view() on a packed block.
  EVIDENCE: worktree 2659-2682; CHILD k() constraints at origin/jhan-amx-vnniK kv_cache.hpp:1619-1679; v_vnni.hpp:183-184 private data_.
- [MUST] h/tron/models/kv_cache.hpp @ book::fill_storage_slot (worktree 1713-1728; PARENT 1646-1659, line 1651 `for (auto& value : block.k)`)
  CHANGE: Branch on the K layout: `if constexpr (k_vnni::layout_on<geometry.head_size>) { bf16* k = detail::k_vnni_access::plane(block.k.as_view()); for (size_t i = 0; i < page_size * geometry.head_size; ++i) { k[i] = static_cast<bf16>(distribution(gen)); } } else { for (auto& value : block.k) { value = ...; } }`. Mirror the V code at worktree 1720-1726. Extend the fill_random comment (worktree ~1286-1289, PARENT diff @@ -1214) so the 'one documented exception to the typed packed access rule' names K as well as V.
  WHY: Compile necessity: range-for over a k_vnni_tensor has no begin/end. This hunk auto-merged cleanly, so the merge result hides the break. Design: fill_random is the documented whole-block exception; the K owner needs the same escape through detail::k_vnni_access.
  EVIDENCE: worktree 1718-1719 `for (auto& value : block.k)`; PARENT 1646-1659; v_vnni.hpp:187-206 (v_vnni_access); CHILD 1433-1441 (old reinterpret_cast of the whole block, removed by PARENT).
- [MUST] h/tron/models/kv_cache.hpp @ page::k_vnni_plane (worktree 1982-1992; CHILD 1682-1693)
  CHANGE: Delete it. Add `template <kv_geometry geometry> requires(book_t::template declares_geometry<geometry>() && k_vnni::layout_on<geometry.head_size>) TRON(nodiscard, inline, pure) k_vnni_view<const bf16, page_size, geometry.head_size> k_packed(kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound) { return kv_block<geometry>(slot, kv_head).k.as_view(); }` next to v_packed (worktree 2123-2130). Comment: 'This page's packed K plane for one KV head of one slot, read-only: the argument type of qk_vnni_128x4 and k_vnni::qk_group. Internal cache writes take writable views from the block owner instead.' Callers to update outside this area: self_attention.hpp:1438 and 1637 at origin/jhan-amx-vnniK.
  WHY: Design table row 'page::k, page::k_vnni_plane': replace the raw packed-plane accessor with page::k_packed<geometry>(slot, head). Goal (c): the `reinterpret_cast<const bf16*>(...k)` at CHILD 1692 is exactly the raw K-plane pointer crossing the cache/kernel boundary.
  EVIDENCE: CHILD kv_cache.hpp:1682-1693; PARENT v_packed 1952-1956; design-child-section.txt table row 1.
- [MUST] h/tron/models/kv_cache.hpp @ page::set_k_row and page::get_k_row, geometry and uniform forms (worktree 1997-2010, 2035-2048, 2051-2064; CHILD 1695-1710, 1733-1748, 1750-1765)
  CHANGE: Packed branch: `store_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);` and `load_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);` (typed operations defined in h/tron/tensor/k_vnni.hpp, bodies = the CHILD's scatter_row / gather_row). Native branch: keep the two memcpy lines through k_at(i_page).data. Row parameter per design: `const_k_row_view<geometry.head_size, Aligned, Dma> row` for set_k_row and `k_row_view<geometry.head_size, Aligned, Dma> row` for get_k_row, with `template <kv_geometry geometry, bool Aligned, bool Dma>`; the uniform forms get `template <bool Aligned, bool Dma>`. In the native branch use `row.data` in the memcpy. Keep TRON_ASSERT_LT(i_page, page_size).
  WHY: Compile necessity for the body (the reinterpret_cast<bf16*>(...k) at CHILD 1706 and 1742 no longer compiles against an owner). Typed rows are the design table row 'page::set_k_row, page::get_k_row' (use const_view<bf16,Aligned,Dma,seq<D>,sseq<1>> for save, view<...> for load; Aligned and Dma preserved from the caller; K does not take V's VIEW_ALIGNED_TRUE requirement because scatter_row/store_block use _mm512_loadu_si512 on the row, CHILD k_vnni.hpp:142, 201). This ripples to every caller (model.hpp:2920, 2924; full.hpp:2655; t_llama_unit, t_k_vnni_layout, t_amx_dispatch_dtype: about 40 call sites listed by `git grep set_k_row\|get_k_row origin/jhan-amx-vnniK`), because template deduction does not apply the pointer-to-view conversion: callers must construct the row view explicitly (the PARENT does this for V with v_source_row, model.hpp:2842 at origin/jhan-kv-typed-tensors).
  EVIDENCE: CHILD kv_cache.hpp:1695-1765; PARENT set_v/get_v 1897-1950 and 2551-2620; v_vnni.hpp:208-227 (row aliases and v_source_row / v_destination_row helpers); CHILD k_vnni.hpp:138-146, 220-228.
- [MUST] h/tron/models/kv_cache.hpp @ page::set_k_block (worktree 2019-2031; CHILD 1712-1731)
  CHANGE: Body becomes `store_block(kv_block<geometry>(slot, kv_head).k.as_view(), c, present, rows);`. Keep the name, the `__mmask16 present` and the `const bf16* const rows[k_vnni::BLOCK_TOKENS_16]` parameter, the constraint and the TRON_ASSERT_LT.
  WHY: Compile necessity (reinterpret_cast at CHILD 1730). Design table row 'page::set_k_block': keep the name, call store_block(writable_k_view, block, mask, rows); the 16 source-row pointers are native rows, not packed storage, so they stay raw.
  EVIDENCE: CHILD kv_cache.hpp:1712-1731; CHILD k_vnni.hpp:193-216 (store_block body to move).
- [MUST] h/tron/models/kv_cache.hpp @ page::copy_storage_slot packed branch (worktree 2351-2368; CHILD 2099-2116, memcpy at CHILD 2107)
  CHANGE: Whole-page case: `dst_block.k = src_block.k;` (defaulted owner copy assignment). Partial case: `for (size_t i = 0; i < count; ++i) { copy_token(dst_block.k.as_view(), dst_begin + i, src_block.k.as_view(), src_begin + i); }` where copy_token is the K overload in h/tron/tensor/k_vnni.hpp (gather into a 64-byte-aligned local row, scatter out; the CHILD's two calls moved inside). Delete the `alignas(64) bf16 row[...]` scratch and both reinterpret_casts. `src_block` is `auto const&` so `.k.as_view()` yields the const view the src parameter needs; `dst_block` is a non-const lvalue so as_view() yields the writable view. Native branch (worktree 2369-2378) unchanged. Update the comment: 'a whole-page copy copies the owner; every other range moves token by token with copy_token'.
  WHY: Compile necessity (memcpy(dst_block.k, ...) needs array decay; reinterpret_cast of an owner). Design: 'replace the whole-page K memcpy at child kv_cache.hpp:2107 with dst_block.k = src_block.k in the packed branch. Use defaulted owner assignment, as for V. Retain the existing array copy in the native branch. Add no K plane-copy helper.' and 'Use typed K token copies.' Bytes are identical: a trivially-copyable assignment copies all 16384 bytes.
  EVIDENCE: CHILD kv_cache.hpp:2093-2127; PARENT append_v -> copy_token 2159-2166; v_vnni.hpp:358-406 (V copy_token signature pattern).
- [MUST] h/tron/models/kv_cache.hpp @ include list (worktree 27 `#include "tron/kernels/k_vnni.hpp"`, 34 `#include "tron/tensor/v_vnni.hpp"`)
  CHANGE: Replace line 27 with `#include "tron/tensor/k_vnni.hpp"`. Keep the `#if defined(TRON_K_VNNI) && TRON_CHUNK_SIZE != 16 #error` block (worktree 36-41). `<type_traits>` is already in use (std::is_trivially_* at worktree 2645) so std::conditional_t needs no new include. Outside this area but caused by it: self_attention.hpp must include "tron/kernels/k_vnni.hpp" itself for qk_group (it currently gets it through kv_cache.hpp).
  WHY: Design: 'The cache includes the K tensor header. h/tron/kernels/k_vnni.hpp includes that header and keeps only qk_group. The cache drops its include of this kernel header. self_attention.hpp includes the kernel header directly for qk_group.' Mirrors the PARENT: kv_cache.hpp includes tensor/v_vnni.hpp, never a kernel header.
  EVIDENCE: worktree 27, 34; PARENT diff hunk @@ -30,6 +30,7 @@; design-child-section.txt paragraph 'The cache includes the K tensor header'.
- [MUST] h/tron/tensor/kv_cache_fwd.hpp @ after the v_vnni forward declarations (PARENT kv_cache_fwd.hpp:33-36)
  CHANGE: Add `template <size_t Rows, size_t Cols> struct k_vnni_tensor; template <typename T, size_t Rows, size_t Cols> struct k_vnni_view;` with a comment parallel to lines 27-32 ('Packed K types: k_vnni_tensor holds one bf16 array of [Rows tokens * Cols dimensions] in the blocked VNNI order of Note [K VNNI storage] ...'). No k_vnni_row (decision 1). Unconstrained declarations.
  WHY: Design: 'Add unconstrained k_vnni_tensor, k_vnni_view ... forward declarations to h/tron/tensor/kv_cache_fwd.hpp, parallel to the V declarations. Then amx_attn_iface.hpp can declare qk_vnni_128x4(k_vnni_view<const bf16,PAGE_TOKENS_64,HEAD_SIZE_128>, const bf16*, float*, size_t) noexcept without intrinsics.'
  EVIDENCE: PARENT kv_cache_fwd.hpp:27-36; PARENT amx_attn_iface.hpp includes kv_cache_fwd.hpp (diff @@ -110,6 +110,7 @@).
- [MUST] h/tron/tensor/k_vnni.hpp (new; moved from h/tron/kernels/k_vnni.hpp at origin/jhan-amx-vnniK) @ whole file; kernel header keeps only qk_group (CHILD k_vnni.hpp:230-308)
  CHANGE: Move verbatim: constants and static_asserts (CHILD 44-84), layout_on (86-97), index (99-107), detail::pair_base / pair_row_offsets (109-133), scatter_row (135-146) as the body of store_row, transpose_16x16_epi32 (148-180), store_block (182-216) retargeted to a view, gather_row (218-228) as the body of load_row. Add k_vnni_view<T,Rows,Cols> and k_vnni_tensor<Rows,Cols> copied from v_vnni_view / v_vnni_tensor (v_vnni.hpp:103-185) with: element concept bf16/const bf16; class-body `static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128)` (the CHILD index map is fixed to 4 token blocks and 4 dimension steps, so no other shape is addressable); private explicit pointer constructor; writable-to-const conversion only; `at(token, dim)` through k_vnni::index with TRON_ASSERT_LT bounds; as_view() & / const& and deleted && / const&&; private `alignas(64) bf16 data_[Rows * Cols]`. Add detail::k_vnni_access { plane(view), pair_base(view, s, token) }. Add row aliases `const_k_row_view<Cols, Aligned, Dma>` / `k_row_view<Cols, Aligned, Dma>` (defaults VIEW_ALIGNED_TRUE / VIEW_DMA_FALSE) and the typed operations store_row, load_row, store_block, copy_token under `#if TRON_CHUNK_SIZE == 16`. Add `static_assert(sizeof(k_vnni_tensor<64,128>) == K_PLANE_BYTES_16384)` and `alignof(...) == K_PLANE_ALIGNMENT_64`. The kernel header h/tron/kernels/k_vnni.hpp then includes the tensor header and keeps qk_group with first parameter `k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k` and `const bf16* plane = detail::k_vnni_access::plane(k);` as its first line.
  WHY: Design header split and 'Keep K class definitions complete in both vector widths for unconditional fake definitions. Guard packed operation bodies at 16 lanes.' Compile necessity: kv_cache.hpp needs complete k_vnni_tensor for the member; amx_attn.cpp and t_amx_dispatch_dtype.cpp need complete k_vnni_view for by-value parameters in definitions.
  EVIDENCE: CHILD k_vnni.hpp:1-310; v_vnni.hpp:64-227; design-child-section.txt paragraphs 'Define k_vnni_tensor ...' and 'Keep K class definitions complete ...'.
- [MUST] h/tron/models/kv_cache.hpp @ Note [K VNNI storage] (CHILD 653-709; worktree about 656-712, auto-merged) and the kv_block comment at worktree 2636-2637
  CHANGE: Item 2: 'passes page::k_packed (a k_vnni_view<const bf16, 64, 128>) to qk_vnni_128x4'. Item 3: qk_group takes the same view. Item 5: 'a whole-page copy assigns the owner (dst_block.k = src_block.k). Every other range moves token by token (copy_token in h/tron/tensor/k_vnni.hpp).' Item 6: add 'The K plane is reached only through the owner k_vnni_tensor and its views; no raw plane pointer leaves the cache (detail::k_vnni_access is the one route, for the typed operations and the two score kernels).' First paragraph: the layout now lives in 'h/tron/tensor/k_vnni.hpp' not 'tron/kernels/k_vnni.hpp'. kv_block comment: describe both branches of k_storage. Plain English, one claim per sentence, define VNNI/AMX at first use as the CHILD text already does.
  WHY: Decision (4) plain-English comments; the Note names k_vnni_plane, the memcpy and the kernel header path, all of which this port removes. make lint-notes checks Note references, so the Note title must stay.
  EVIDENCE: CHILD kv_cache.hpp:653-709 (items 2, 5, 6 at 686-687, 699-702, 703-705); PR 4557 body 'make lint-notes (the repo's checker of Note references)'.
- [SHOULD] h/tron/models/kv_cache.hpp @ Note [KV block lifetime] last paragraph (PARENT 1458-1460; worktree about 1526-1528): 'K and V are separate bf16 arrays. Fill each array separately, and compute SIMD load addresses within V with bf16 pointers.'
  CHANGE: Reword: 'K and V are separate members: a bf16 array or a trivially copyable owner (k_vnni_tensor for packed K, v_vnni_tensor for packed V). Fill each member separately. SIMD load addresses inside a packed plane come from the plane's access helper (detail::k_vnni_access, detail::v_vnni_access).'
  WHY: Consistency: the sentence becomes false for packed K. The lifetime argument itself (operator new[] creates implicit-lifetime objects; launder) is unchanged and still holds because k_vnni_tensor is trivially default-constructible and trivially destructible.
  EVIDENCE: PARENT kv_cache.hpp:1441-1461; memory.hpp Note [DMA allocation creates objects].
- [SHOULD] h/tron/models/kv_cache.hpp @ book/page overview comment (worktree 579-582, PARENT diff hunk @@ -568,8 +569,9 @@: 'packed-V storage (through the typed operations of h/tron/tensor/v_vnni.hpp ...)')
  CHANGE: Add 'and packed-K storage (h/tron/tensor/k_vnni.hpp, Note [K VNNI storage])'.
  WHY: Consistency with the PARENT's wording; one line.
  EVIDENCE: worktree 579-582.
- [SHOULD] h/tron/models/kv_cache.hpp @ kv_block (worktree 2634-2683)
  CHANGE: Add, inside `#ifdef TRON_K_VNNI` or guarded by `if constexpr`-free static_assert on the selected type: `static_assert(!k_vnni::layout_on<head_size> || sizeof(k_storage) == k_vnni::PAGE_TOKENS_64 * k_vnni::HEAD_SIZE_128 * sizeof(bf16), "the packed K owner is 16384 bytes for 64 tokens by 128 dimensions");` and `static_assert(offsetof(kv_block, v) == sizeof(k))` is NOT possible for a non-standard-layout check in-class; instead keep the book-level `sizeof(kv_block_t) == expected_block_bytes` (worktree 1661) and t_llama_unit:439 at PARENT (`sizeof(kv_block_t) == KV_BLOCK_PLANES_2 * sizeof(v_owner_t)`), which already pin block size and therefore the V offset given sizeof(k) == sizeof(v).
  WHY: Design: 'Require 64-byte alignment, unchanged K/V offsets and block size, sizeof(k) == sizeof(v), and a 16,384-byte owner for 64 tokens by 128 dimensions.' Most of it is already enforced by existing asserts; only the 16384 check is new.
  EVIDENCE: worktree 1660-1662; PARENT t_llama_unit.cpp:428-439.
- [COULD] h/tron/models/kv_cache.hpp @ page::k_packed
  CHANGE: Also provide a private non-const `k_packed_mut<geometry>()` returning the writable view, used by set_k_row/set_k_block/copy_storage_slot instead of spelling `kv_block<geometry>(slot, kv_head).k.as_view()` three times.
  WHY: Readability only. The PARENT did not add such a helper for V (it spells `.v.as_view()` at 2559, 2577, 2162), so omitting it matches the PARENT more closely. Default: omit.
  EVIDENCE: PARENT kv_cache.hpp:2162-2166, 2559, 2577.

## proposed_code
// ---------- h/tron/tensor/kv_cache_fwd.hpp : add after the V declarations (PARENT :33-36)
// Packed K types (Note [K VNNI storage] in kv_cache.hpp):
// - k_vnni_tensor holds one bf16 array of [Rows tokens * Cols dimensions] in the
//   blocked VNNI order. The array starts at an address that is a multiple of 64 bytes.
// - k_vnni_view refers to that array and computes where each (token, dim) value is.
// The view owns no memory. T = bf16 allows writes, and T = const bf16 is read-only.
template <size_t Rows, size_t Cols>
struct k_vnni_tensor;
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view;

// ---------- h/tron/tensor/k_vnni.hpp (new) : skeleton. Constants, layout_on, index,
// detail::pair_base / pair_row_offsets / transpose_16x16_epi32 and the three vector
// bodies move here VERBATIM from h/tron/kernels/k_vnni.hpp (CHILD :44-228).
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/seq.hpp"
#include "tron/tensor/view.hpp"
namespace tron {
namespace k_vnni { /* constants 44-84, layout_on 86-97, index 99-107 unchanged */ }
namespace detail { struct k_vnni_access; }

inline constexpr size_t K_PLANE_ALIGNMENT_64 = 64;
inline constexpr size_t K_PLANE_BYTES_16384 =
    k_vnni::PAGE_TOKENS_64 * k_vnni::HEAD_SIZE_128 * sizeof(bf16);

template <typename T>
concept k_vnni_element = std::same_as<T, bf16> || std::same_as<T, const bf16>;

// A packed K plane of [Rows tokens * Cols dimensions]. One element is reached
// through at(token, dim). Whole token rows move through store_row, load_row,
// store_block and copy_token. Views come only from an owner (k_vnni_tensor::as_view).
// A writable view converts to a read-only one, never the reverse. No public pointer
// constructor, no data(), no pointer conversion, no operator[].
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view final {
  static_assert(k_vnni_element<T>, "a packed K plane holds bf16 or const bf16");
  // The index map (k_vnni::index) is written for 4 token blocks and 4 dimension
  // steps. So the packed K layout exists for one shape.
  static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128,
      "packed K exists for 64 tokens by 128 dimensions (Note [K VNNI storage])");

  template <typename U>
    requires(std::is_const_v<T> && std::same_as<U, std::remove_const_t<T>>)
  TRON(inline)
  k_vnni_view(k_vnni_view<U, Rows, Cols> other) noexcept
  : data_(other.data_) {}

  TRON(nodiscard, inline, pure)
  T& at(size_t token, size_t dim) noexcept {
    TRON_ASSERT_LT(token, Rows);
    TRON_ASSERT_LT(dim, Cols);
    return data_[k_vnni::index(token, dim)];
  }
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

// Owns one packed K plane: exactly one 64-byte-aligned bf16 array, no separate
// allocation and no initialization (the cache's DMA allocation creates the kv_blocks
// that hold it; see Note [KV block lifetime] in kv_cache.hpp). Trivial to construct,
// copy and destroy; copying an owner copies the plane. as_view() on a temporary is
// deleted: a view must not outlive its owner.
template <size_t Rows, size_t Cols>
struct alignas(K_PLANE_ALIGNMENT_64) k_vnni_tensor final {
  static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128,
      "packed K exists for 64 tokens by 128 dimensions (Note [K VNNI storage])");
  TRON(nodiscard, inline)
  k_vnni_view<bf16, Rows, Cols> as_view() & noexcept TRON(this_lifetimebound)
  { return k_vnni_view<bf16, Rows, Cols>(data_); }
  TRON(nodiscard, inline)
  k_vnni_view<const bf16, Rows, Cols> as_view() const& noexcept TRON(this_lifetimebound)
  { return k_vnni_view<const bf16, Rows, Cols>(data_); }
  k_vnni_view<bf16, Rows, Cols> as_view() && = delete;
  k_vnni_view<const bf16, Rows, Cols> as_view() const&& = delete;
private:
  alignas(K_PLANE_ALIGNMENT_64) bf16 data_[Rows * Cols];
};
static_assert(sizeof(k_vnni_tensor<k_vnni::PAGE_TOKENS_64, k_vnni::HEAD_SIZE_128>) ==
                  K_PLANE_BYTES_16384 &&
              alignof(k_vnni_tensor<k_vnni::PAGE_TOKENS_64, k_vnni::HEAD_SIZE_128>) ==
                  K_PLANE_ALIGNMENT_64,
    "one packed K owner is 16384 bytes, aligned to 64 bytes");

namespace detail {
// The one route from a packed K view to its plane address: for the typed operations
// below, k_vnni::qk_group and amx_attn_h128g4::qk_vnni_128x4.
struct k_vnni_access final {
  template <typename T, size_t Rows, size_t Cols>
  TRON(nodiscard, inline, pure)
  static T* plane(k_vnni_view<T, Rows, Cols> k) noexcept { return k.data_; }
};
}  // namespace detail

// Contiguous transfer rows for set_k_row / get_k_row, not packed K storage. The
// alignment and DMA flags are the caller's: the K row operations load the row with
// unaligned vector loads, so they do not require VIEW_ALIGNED_TRUE.
template <size_t Cols, bool Aligned = VIEW_ALIGNED_TRUE, bool Dma = VIEW_DMA_FALSE>
using const_k_row_view = const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;
template <size_t Cols, bool Aligned = VIEW_ALIGNED_TRUE, bool Dma = VIEW_DMA_FALSE>
using k_row_view = view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;

#if TRON_CHUNK_SIZE == 16
// Bodies: CHILD scatter_row (:138-146), gather_row (:220-228), store_block (:193-216),
// each with `plane` obtained from detail::k_vnni_access::plane(view) as its first line.
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void store_row(k_vnni_view<bf16, Rows, Cols> dst, size_t token,
    const_k_row_view<Cols, Aligned, Dma> src) noexcept;
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void load_row(k_vnni_view<const bf16, Rows, Cols> src, size_t token,
    k_row_view<Cols, Aligned, Dma> dst) noexcept;
template <size_t Rows, size_t Cols>
TRON(inline)
void store_block(k_vnni_view<bf16, Rows, Cols> dst, size_t c, __mmask16 present,
    const bf16* const rows[k_vnni::BLOCK_TOKENS_16]) noexcept;
// Copy one token between packed K planes: gather its row (4 gathers) into a
// 64-byte-aligned local row, then scatter it (4 scatters). Same instructions as the
// CHILD copy (kv_cache.hpp:2109-2115 at origin/jhan-amx-vnniK).
template <size_t Rows, size_t Cols>
TRON(inline)
void copy_token(k_vnni_view<bf16, Rows, Cols> dst, size_t dst_token,
    k_vnni_view<const bf16, Rows, Cols> src, size_t src_token) noexcept;
#endif
}  // namespace tron

// ---------- h/tron/kernels/k_vnni.hpp : keeps only qk_group
#include "tron/tensor/k_vnni.hpp"
template <size_t kv_mul, typename q_scalar>
TRON(inline)
void qk_group(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k, const q_scalar* q,
    uint64_t live, float* s, size_t s_stride) noexcept {
  const bf16* plane = detail::k_vnni_access::plane(k);  // then the CHILD body :253-307
  ...
}

// ---------- h/tron/models/kv_cache.hpp : kv_block (replaces worktree 2636-2638, 2659-2682)
template <size_t page_size, size_t head_size>
struct alignas(kv_block_alignment) kv_block {
  // Native K: one row of head_size bf16 values per token, indexed as
  // [p * head_size + i]. Packed K (TRON_K_VNNI, 128-dimension heads): the typed owner
  // of Note [K VNNI storage]. Both hold page_size * head_size bf16 values.
  using native_k_storage = bf16[page_size * head_size];
  using k_storage = std::conditional_t<k_vnni::layout_on<head_size>,
      k_vnni_tensor<page_size, head_size>,
      native_k_storage>;
  static_assert(std::is_trivially_default_constructible_v<k_storage> &&
                    std::is_trivially_copyable_v<k_storage> &&
                    std::is_trivially_destructible_v<k_storage>,
      "the DMA allocation creates kv_blocks; see Note [KV block lifetime]");
  static_assert(sizeof(k_storage) == page_size * head_size * sizeof(bf16),
      "packed K holds the same bytes as native K");
  static_assert(alignof(k_storage) <= kv_block_alignment);
  alignas(kv_block_alignment) k_storage k;
  /* v unchanged (worktree 2639-2654) */
  static_assert(sizeof(k) == sizeof(v));

  TRON(nodiscard, inline, pure)
  auto k_view() noexcept TRON(this_lifetimebound)
    requires(!k_vnni::layout_on<head_size>)
  {
    return view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<page_size, head_size>>{k};
  }
  TRON(nodiscard, inline, pure)
  auto k_view() const noexcept TRON(this_lifetimebound)
    requires(!k_vnni::layout_on<head_size>)
  {
    return const_view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,
        seq<page_size, head_size>>{k};
  }
  TRON(nodiscard, inline, pure)
  auto k_at(size_t i_page) noexcept TRON(this_lifetimebound)
    requires(!k_vnni::layout_on<head_size>)
  { return k_view()[i_page]; }
  TRON(nodiscard, inline, pure)
  auto k_at(size_t i_page) const noexcept TRON(this_lifetimebound)
    requires(!k_vnni::layout_on<head_size>)
  { return k_view()[i_page]; }
};

// ---------- page accessors (replace worktree 1982-2064 after the textual resolution)
// This page's packed K plane for one KV head of one slot, read-only: the argument
// type of qk_vnni_128x4 and k_vnni::qk_group (Note [K VNNI storage]). Internal
// cache writes take writable views from the block owner instead.
template <kv_geometry geometry>
  requires(book_t::template declares_geometry<geometry>() &&
           k_vnni::layout_on<geometry.head_size>)
TRON(nodiscard, inline, pure)
k_vnni_view<const bf16, page_size, geometry.head_size> k_packed(
    kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound)
{
  return kv_block<geometry>(slot, kv_head).k.as_view();
}

template <kv_geometry geometry, bool Aligned, bool Dma>
  requires(book_t::template declares_geometry<geometry>())
TRON(inline)
void set_k_row(kv_slot_id slot, size_t kv_head, size_t i_page,
    const_k_row_view<geometry.head_size, Aligned, Dma> row) noexcept {
  TRON_ASSERT_LT(i_page, page_size);
  if constexpr (k_vnni::layout_on<geometry.head_size>) {
    store_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);
  } else {
    std::memcpy(kv_block<geometry>(slot, kv_head).k_at(i_page).data, row.data,
        geometry.head_size * sizeof(bf16));
  }
}

template <kv_geometry geometry>
  requires(book_t::template declares_geometry<geometry>() &&
           k_vnni::layout_on<geometry.head_size>)
TRON(inline)
void set_k_block(kv_slot_id slot, size_t kv_head, size_t c, __mmask16 present,
    const bf16* const rows[k_vnni::BLOCK_TOKENS_16]) noexcept {
  TRON_ASSERT_LT(c, page_size / k_vnni::BLOCK_TOKENS_16);
  store_block(kv_block<geometry>(slot, kv_head).k.as_view(), c, present, rows);
}

template <kv_geometry geometry, bool Aligned, bool Dma>
  requires(book_t::template declares_geometry<geometry>())
TRON(inline)
void get_k_row(kv_slot_id slot, size_t kv_head, size_t i_page,
    k_row_view<geometry.head_size, Aligned, Dma> row) const noexcept {
  TRON_ASSERT_LT(i_page, page_size);
  if constexpr (k_vnni::layout_on<geometry.head_size>) {
    load_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);
  } else {
    std::memcpy(row.data, kv_block<geometry>(slot, kv_head).k_at(i_page).data,
        geometry.head_size * sizeof(bf16));
  }
}
// uniform-geometry forms: template <bool Aligned, bool Dma> forwarding to
// set_k_row<layout_t::primary_geometry> / get_k_row<layout_t::primary_geometry>.

// ---------- copy_storage_slot packed branch (replaces worktree 2358-2367)
if (src_begin == 0 && dst_begin == 0 && count == page_size) {
  // Defaulted owner assignment copies the whole 16 KiB plane.
  dst_block.k = src_block.k;
} else {
  for (size_t i = 0; i < count; ++i) {
    copy_token(dst_block.k.as_view(), dst_begin + i, src_block.k.as_view(), src_begin + i);
  }
}

// ---------- fill_storage_slot (replaces worktree 1718-1719)
if constexpr (k_vnni::layout_on<geometry.head_size>) {
  bf16* k = detail::k_vnni_access::plane(block.k.as_view());
  for (size_t i = 0; i < page_size * geometry.head_size; ++i) {
    k[i] = static_cast<bf16>(distribution(gen));
  }
} else {
  for (auto& value : block.k) {
    value = static_cast<bf16>(distribution(gen));
  }
}

## design_contradictions
- Design snippet 'using native_k_storage = bf16s[page_size][head_size / chunk_size];' names the OLD array shape. The PARENT replaced it with `bf16 k[page_size * head_size]` (PARENT kv_cache.hpp:2452, PR 4557 body: 'kv_block::k is a plain bf16 array ... k_view now builds its views from this array with no reinterpret_cast'). The port must use `bf16[page_size * head_size]` as the native branch; the bf16s shape would reintroduce the reinterpret_cast the PARENT removed and break the PARENT's k_view() body.
- Design 'Reuse the parent's allocation-time array construction' and the design's lifetime section (`::new (static_cast<void*>(region_base)) kv_block_t[block_count];`, design-new-tensor-type.txt 'Arena construction without clearing') describe a placement-new pass. The PARENT's final code has NO construction pass: objects come into existence through the tagged `operator new[]` in h/system/memory.hpp and are reached through std::launder (PARENT kv_cache.hpp:1441-1461 Note [KV block lifetime], :1564/:1573/:1613; PR 4557 body: 'No placement new and no second pass over the arena remain'). For the child this means: nothing to reuse or call; the only obligation is that k_vnni_tensor stays trivially default-constructible and trivially destructible so the book-level static_asserts (PARENT 1553-1556, 1596-1599) keep holding.
- Design defines k_vnni_row and an expression base and says 'If Q3 is rejected, remove the row expressions and their compatibility checks from both families.' Decision (1) rejects Q3 (PARENT commit c12df586b6 dropped v_vnni_row). So: no k_vnni_row, no operator[], no expr base; the PARENT test even asserts `STATIC_REQUIRE_FALSE(matrix_indexes_rows<v_plane_t>)` (t_llama_unit.cpp:422-423 at origin/jhan-kv-typed-tensors) and the K view should pass the same negative probe.
- Design table row 'hardware::page_info K callback: Add the child's scratch parameter' is already in the CHILD (full.hpp:2644-2661 and gof.hpp/gof.cpp at origin/jhan-amx-vnniK: k_head_fn takes `bf16* dest`). Nothing to add; only its get_k_row call changes to pass a typed destination row.
- The design's generic `k_vnni_view<T, Rows, Cols>::at(token, dim)` implies an index map parameterized by Rows (the reviewer sketch's k_vnni_layout::offset uses Tokens/16). The CHILD's k_vnni::index (k_vnni.hpp:99-107) hard-codes TOKEN_BLOCKS_4 and STEP_PAIRS_16 for 64x128, and the design also says 'Keep the existing 64-token by 128-dimension kernel limit' and 'Keep the function spelling for the independent index checks' (t_k_vnni_layout.cpp:80-90 uses STATIC_REQUIRE on index(...)). Resolution: keep index unchanged and pin Rows == 64 && Cols == 128 by class-body static_assert in both K types. This is safe because page_size is 64 (worktree 1821) and layout_on is true only for head_size 128, so only that specialization is ever instantiated; the unselected k_vnni_tensor<64, 64> (gpt-oss) is named by std::conditional_t but never instantiated.

## risks
- Hidden breakage in cleanly merged hunks: fill_storage_slot (worktree 1718 range-for over block.k) and copy_storage_slot (worktree 2359 memcpy on .k, 2363-2366 reinterpret_cast) merged without conflict but do not compile once kv_block::k is an owner. Build TRON_K_VNNI=ON before trusting the merge.
- Typed set_k_row/get_k_row rows ripple beyond this area: model.hpp:2920 (kout.data), :2924 (conv[0]), full.hpp:2655 (dest scratch), t_amx_dispatch_dtype.cpp:101, t_k_vnni_layout.cpp:401-459, t_llama_unit.cpp (about 30 sites, e.g. 101, 362-366, 392-407, 579-607, 829, 852, 1469, 1490, 1588, 1610, 1951, 2247-2249, 2284-2285, 2331-2333, 2410, 2442, 2724) all pass raw pointers today (all at origin/jhan-amx-vnniK). Each needs an explicit view construction (template deduction does not use pointer-to-view conversion), as the PARENT did for V with v_source_row (model.hpp:2842). Suggest a small `k_source_row<Cols, Aligned, Dma>(const bf16*)` / `k_destination_row<...>(bf16*)` helper pair in the tensor header, parallel to v_source_row / v_destination_row (v_vnni.hpp:215-227).
- Alignment flag honesty: if set_k_row's row view is spelled with Aligned = true at a call site whose buffer is not 64-byte aligned, nothing checks it (PARENT comment: 'The rows' aligned flag is a precondition on the caller's buffer, not a promise the wrapper makes'). The CHILD operations use loadu/storeu so the bytes stay correct either way, but the flag would be a false statement. `conv` in save_k (model.hpp around 2860-2930 at origin/jhan-amx-vnniK) alignment was not verified in this analysis.
- Name sharing: `load_row` and `copy_token` exist for V in namespace tron (v_vnni.hpp:317, 360). Adding K overloads with k_vnni_view parameters is unambiguous (deduction fails for the other family), but a future caller passing a mistyped view gets a 'no matching function' error naming both families. Acceptable; mirrors the design's 'typed function boundaries'.
- Raw plane pointers remain in files outside this area and must be converted in the same port or the branch does not compile: amx_attn_iface.hpp:231-234 and amx_attn.cpp:201 (qk_vnni_128x4 const bf16*), t_amx_dispatch_dtype.cpp:196 (fake), t_amx_numerics.cpp:219 and :230 (scatter_row on a raw array, raw kernel call), t_k_vnni_layout.cpp:67-70 (plane_and_rows with a raw bf16 plane) and its 12 scatter_row/gather_row/store_block/qk_group calls on buf->plane (lines 113-308). The design says to adapt t_k_vnni_layout to actual aligned owners and copy the trivially copyable owner's bytes out for the physical-layout comparisons.
- PR #4737 (origin/jhan-amx-vnniK-i4500, 'row-major tail block') is stacked on CHILD. If it stores some tokens of a packed plane row-major, a single k_vnni_tensor owner that asserts one layout for all 64 tokens and a copy_token that always gathers/scatters would make its later merge a redesign, not a rebase. Not analysed further here (out of scope); flag before finalising the K view type.
- 8-lane build: the class definitions and k_vnni::index must compile with TRON_CHUNK_SIZE == 8 (the CMake lane without AVX-512), because kv_cache_fwd.hpp names the types in amx_attn_iface.hpp and the fakes define qk_vnni_128x4 by value. Keep all intrinsics-using bodies (store_row, load_row, store_block, copy_token, qk_group) under `#if TRON_CHUNK_SIZE == 16`, and keep the `#error` guard in kv_cache.hpp (worktree 36-41).
- Bit-identity evidence: the whole-page owner assignment replaces memcpy of the same 16384 bytes, and copy_token keeps the CHILD's 4 gathers + 4 scatters, so stored bytes are unchanged by construction. The proof the PARENT used (objdump of noinline wrappers, PR 4557 body 'Instruction comparison') should be repeated for store_row / load_row / store_block / copy_token versus scatter_row / gather_row / store_block / the CHILD copy loop.

## open_questions
- Land the typed set_k_row/get_k_row row parameters in this port (about 40 call sites across model.hpp, full.hpp and 5 test files) or keep `const bf16* row` in a first compiling commit and convert in a focused follow-up commit on the same branch? The design requires the typed rows; the sequencing is the question.
- Is `conv` in save_k (model.hpp, the bf16 conversion scratch used when rows_are_bf16 is false) 64-byte aligned, so the call may state Aligned = true? If not, pass Aligned = false there.
- Should the K view's `at(token, dim)` exist at all, given the reviewer's 'no code without a consumer' rule? Its consumers would be t_k_vnni_layout (replacing `buf->plane[index(tok, d)]` reads at lines 120-122, 143) and the PARENT-style STATIC_REQUIRE probes (matrix_at_writes). If the test keeps copying the owner's bytes out and indexing with k_vnni::index, at() has no consumer.
- Where should the `#if defined(TRON_K_VNNI) && TRON_CHUNK_SIZE != 16 #error` guard live after the header split: stay in kv_cache.hpp (CHILD placement, worktree 36-41) or move to h/tron/tensor/k_vnni.hpp next to layout_on? Either works; the design says 'The child's cache header rejects packed K at 8 lanes', which favours keeping it in kv_cache.hpp.
- PR #4737 interplay: does the row-major tail block need a per-block layout inside one plane? If yes, the owner/view design here must be reviewed with that PR before pushing.
