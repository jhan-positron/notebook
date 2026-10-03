# Design specification (issue 4525 "adapt PR #4424 as a stacked child" section) versus the PARENT's final code (origin/jhan-kv-typed-tensors = c12df586b6) and the CHILD (origin/jhan-amx-vnniK = 30c4ac82cb). Acceptance checklist C01-C32 is encoded in semantic_changes (one entry per item, status APPLIES / SUPERSEDED / UNVERIFIABLE in the change text). Worktree note: at the start of this analysis /home/jhan/workspace/ai-runs/tron-vnnik-typed had 7 UU files with conflict markers; by 17:07 UTC (reflog "reset: moving to HEAD" 10:07:52 -0700) another process had resolved them (0 unmerged paths, 0 marker files). Line numbers in textual_conflicts are the ones observed before that resolution.

## textual_conflicts
- h/tron/models/kv_cache.hpp 1981-2122 (HEAD = CHILD 1981-2072: k_vnni_plane, set_k_row, set_k_block, get_k_row, uniform forms; PARENT 2072-2122: typed set_v/get_v declarations with const_v_row_view/v_row_view, v_packed): Keep both blocks, CHILD K accessors first, then PARENT V accessors (both are insertions at the same anchor, the old '// The actual V data' comment). Then the adaptation commit replaces k_vnni_plane (const bf16*) with k_packed<geometry>() returning k_vnni_view<const bf16, page_size, geometry.head_size> (see C08). The CHILD's copy_storage_slot K branch (child kv_cache.hpp:2099-2117) auto-merged next to the PARENT's unchanged V branch; retype it per C11.
- h/tron/models/self_attention.hpp 1653-1666 (comment) and 1674-1687 (dense QK call: CHILD if constexpr k_vnni::layout_on -> qk_vnni_128x4(pg.k_vnni_plane...) else qk_rowmajor_128x4(k0.data,...) vs PARENT qk_rowmajor_128x4(pg.template k<geometry.kv>(slot, kv_head), ...)): Keep the CHILD's if constexpr; the else branch takes the PARENT's typed whole-plane call (pg.template k<geometry.kv>(slot, kv_head), no .data). Merge the two comments: VNNI branch sentence from CHILD, const_native_k_view sentence from PARENT. The if-branch later becomes qk_vnni_128x4(pg.template k_packed<geometry.kv>(slot, kv_head), ...) (C08/C12). The observed resolution did exactly this merge.
- src/tron/kernels/amx_attn.cpp 14-20 (includes: CHILD tron/kernels/k_vnni.hpp vs PARENT tron/tensor/kv_cache_fwd.hpp, tron/tensor/v_vnni.hpp, tron/tensor/view.hpp) and 219-298 (CHILD pack_q_rows_128x4 + qk_vnni_128x4 definitions vs PARENT weights_times_v_128x4 typed signature + detail::v_vnni_access::plane): Keep all four includes (after the split the CHILD include becomes tron/tensor/k_vnni.hpp, C13/C14). Keep both function groups. Then retype qk_vnni_128x4 to take k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> and read the plane once via detail::k_vnni_access::plane(k_page), mirroring PARENT amx_attn.cpp weights_times_v_128x4 ('const bf16* const v_pairs = detail::v_vnni_access::plane(v_page);').
- t/t_amx_dispatch_dtype.cpp 105-112 (CHILD page->set_k_row(slot, 0, token, zero.data()) vs PARENT set_v(..., v_source_row<head_size>(zero.data()))) and 204-222 (CHILD fakes pack_q_rows_128x4 / qk_vnni_128x4(const bf16*, ...) vs PARENT typed fakes qk_rowmajor_128x4(const_native_k_view<64,128>, ...) / weights_times_v_128x4(v_vnni_view<const bf16,64,128>, ...)): Keep both lines in exercise_page and all four fakes. Then (C09) wrap the K row: set_k_row(slot, 0, token, <const K row view of zero.data()>), and (C12) change the qk_vnni_128x4 fake parameter to k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>. Add #include "tron/tensor/k_vnni.hpp" next to the PARENT's new includes (lines 44-47 at PARENT).
- t/t_llama_unit.cpp 141-153 (concept page_supports_uniform_kv_access: CHILD adds page.get_k_row(kv_slot_id(0), 0, 0, k_output) with bf16* k_output; PARENT changes get_v to a view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<head_size>, sseq<1>> output) and 3257-3751 (CHILD appended save_k shared-save TEST_CASE 3257-3506 vs PARENT appended 'packed V rows keep their bits through set_v, get_v and at()' 3506-3751): Combine the concept (both requirements; after C09 the K parameter becomes a typed destination row view). Keep both appended test cases in either order. The merged concept already reads this way in the worktree.
- h/tron/models/common.hpp 3-8 (CHILD #include <array> / <atomic> vs main's #include <algorithm>; the PARENT never touched common.hpp, so this is child-vs-main): Keep all three includes in sorted order (the worktree now has <algorithm>, <array>, <atomic>, <compare>, <cstdint>, <span>). The CHILD's batch::k_store_window struct (common.hpp +30 lines) auto-merged.
- config/test-benchmarks.json 424-428 (granite_rapids_6962p block, key at line 364: CHILD t_llama_unit 13.436/13.388/13.618 s, 643 MB vs main 5.187/5.256/4.936 s, 331 MB) and 476-531 (CHILD t_amx_numerics 0.804/0.745/0.728 + new t_k_vnni_layout row vs main's t_amx_numerics 0.903/0.698/0.58 plus ~45 new records). The PARENT did not change this file (not in its 14-file diff), so both hunks are child-vs-main.: Take main's list and values (they are the newer baseline), add the CHILD's t_k_vnni_layout row ({"name":"t_k_vnni_layout","filter":"","labels":["fake"],"times":{"1":0.709,"2":0.697,"4":0.696},"max_rss_mb":{"1":9,"2":8,"4":8}}) after t_amx_dispatch_dtype, record the CHILD's three granite_rapids_6962p values in the PR text as historical, and remeasure t_llama_unit (and t_k_vnni_layout) after the port under the authorization rule (C26). The observed resolution kept main's t_llama_unit 5.187 row and added the t_k_vnni_layout row.

## semantic_changes
- [MUST] h/tron/models/kv_cache.hpp @ struct kv_block (PARENT c12df586b6 lines 2449-2470: 'alignas(kv_block_alignment) bf16 k[page_size * head_size];' then v_storage selection under #if TRON_CHUNK_SIZE == 16)
  CHANGE: C01 APPLIES (adapted). Replace k with 'using k_storage = std::conditional_t<k_vnni::layout_on<head_size>, k_vnni_tensor<page_size, head_size>, bf16[page_size * head_size]>; alignas(kv_block_alignment) k_storage k;' plus the same is_trivially_* static_assert the PARENT has for v_storage (2459-2462). The design's native branch 'bf16s[page_size][head_size / chunk_size]' is SUPERSEDED: PARENT commit c73e7fb2f9 made k a plain bf16 array.
  WHY: Design 'Child storage and access' block; the code wins over the design text for the native array type.
  EVIDENCE: git show origin/jhan-kv-typed-tensors:h/tron/models/kv_cache.hpp | sed -n 2449,2470p; PARENT log c73e7fb2f9 'Declare kv_block::k as a plain bf16 array'.
- [MUST] h/tron/tensor/k_vnni.hpp (new) @ class bodies of k_vnni_tensor<Rows, Cols> and k_vnni_view<T, Rows, Cols>
  CHANGE: C02 APPLIES. Put the K shape and element constraints in class-body static_asserts (Rows > 0 && Rows % 16 == 0, Cols > 0 && Cols % 32 == 0, T is bf16 or const bf16), no requires-clause on the class templates. std::conditional_t names k_vnni_tensor<64, 64> for gpt-oss (head 64) without completing it, so a body static_assert is safe; a class-template constraint would be checked at naming time and fail.
  WHY: Design: 'std::conditional_t must be able to name the unselected packed specialization'; 'Do not add class-template requires clauses: the forward declarations are unconstrained' (design-new-tensor-type.txt line 377). PARENT precedent: v_vnni_view static_asserts and the v_vnni_element concept (v_vnni.hpp).
  EVIDENCE: PARENT v_vnni.hpp: 'static_assert(v_vnni_element<T>, ...)', 'static_assert(Rows > 0 && Rows % V_PAIR_TOKENS_2 == 0, ...)'. Child panel geometry: k_vnni.hpp:25-30 (16-token blocks, 32-dim steps).
- [MUST] h/tron/tensor/k_vnni.hpp (new) @ k_vnni_tensor / k_vnni_view definitions
  CHANGE: C03 APPLIES. Copy the PARENT owner/view rules: 'struct alignas(K_PLANE_ALIGNMENT_64) k_vnni_tensor final' with one 'alignas(64) bf16 data_[Rows * Cols];', 'as_view() & / const& ' returning k_vnni_view<bf16,...> / <const bf16,...> with TRON(this_lifetimebound), 'as_view() && = delete; as_view() const&& = delete;', private 'explicit k_vnni_view(T* data)', writable-to-const converting constructor only, friends: k_vnni_tensor<Rows,Cols>, detail::k_vnni_access, other k_vnni_view instantiations; no data(), no operator[], no pointer conversion. Bounds-checked at(token, dim) using k_vnni::index.
  WHY: Design: 'Apply the V owner's lvalue-only as_view(), const conversion, and private packed-pointer rules to K too'. Goal (c) no raw bf16* K-plane pointer crosses the cache/kernel boundary.
  EVIDENCE: PARENT v_vnni.hpp struct v_vnni_view final (private ctor, friends, converting ctor 'requires(std::is_const_v<T> && std::same_as<U, std::remove_const_t<T>>)') and struct alignas(V_PLANE_ALIGNMENT_64) v_vnni_tensor final.
- [MUST] h/tron/models/kv_cache.hpp and t/t_llama_unit.cpp @ kv_block static_assert(sizeof(k) == sizeof(v)) (PARENT :2470); kv_block_at_storage static_asserts sizeof(kv_block_t) == expected_block_bytes and alignof == storage_alignment (PARENT :1594-1595); t_llama_unit owner checks (PARENT :428-439)
  CHANGE: C04 APPLIES. Keep the existing asserts (they now check the K owner automatically). Add to t_llama_unit the K mirror of lines 428-439: k_owner_t trivially default-constructible/copyable/destructible, sizeof(k_owner_t) == 64 * 128 * sizeof(bf16) (16384 bytes), alignof(k_owner_t) == 64, sizeof(kv_block_t) == 2 * sizeof(k_owner_t). Guard the K-owner checks with #ifdef TRON_K_VNNI where k_owner_t is the selected storage.
  WHY: Design: 'Require 64-byte alignment, unchanged K/V offsets and block size, sizeof(k) == sizeof(v), and a 16,384-byte owner for 64 tokens by 128 dimensions.'
  EVIDENCE: PARENT t_llama_unit.cpp:428-439 (v_owner_t checks); PARENT kv_cache.hpp:1594-1598.
- [MUST] h/system/memory.hpp, h/tron/models/kv_cache.hpp @ operator new[](size_t, dma_allocation_t, std::align_val_t) and the std::launder accessors (PARENT kv_cache.hpp:1553-1573, 1596-1613)
  CHANGE: C05 APPLIES, no code change. The K owner must stay trivially default-constructible, copyable and destructible so the DMA allocation's implicit object creation covers it; the PARENT's static_asserts in kv_block() and kv_block_at_storage() enforce this at compile time.
  WHY: Design: 'Reuse the parent's allocation-time array construction.' PARENT body: 'KV blocks are created by the tagged operator new[] with no construct pass'.
  EVIDENCE: PARENT memory.hpp diff lines 57-75 (operator new[] with dma_allocation_t); kv_cache.hpp:1553-1555 static_assert message 'The DMA allocation creates KV blocks; see Note [KV block lifetime]'.
- [MUST] h/tron/models/kv_cache.hpp @ kv_block::k_view() / k_at() (PARENT :2472-2495)
  CHANGE: C06 APPLIES. Add 'requires(!k_vnni::layout_on<head_size>)' to all four k_view/k_at members. 'view<...>{k}' does not compile when k is a k_vnni_tensor.
  WHY: Compile necessity and design: 'Constrain native k_view() and k_at() to the array branch.'
  EVIDENCE: PARENT kv_cache.hpp:2473-2476: 'return view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<page_size, head_size>>{k};'.
- [MUST] h/tron/models/kv_cache.hpp @ page::k(...) overloads (CHILD 30c4ac82cb diff hunks at 1611-1680)
  CHANGE: C07 APPLIES, already in the CHILD: every page::k overload carries '&& !k_vnni::layout_on<head_size>' or '!k_vnni::layout_on<geometry.head_size>'. Preserve through the merge; the PARENT did not change these signatures.
  WHY: Design: 'Keep native overloads and their !layout_on restrictions.'
  EVIDENCE: git diff c7844ca2ce origin/jhan-amx-vnniK -- h/tron/models/kv_cache.hpp (hunks @@ -1544 .. @@ -1598).
- [MUST] h/tron/models/kv_cache.hpp, h/tron/models/self_attention.hpp @ page::k_vnni_plane (CHILD kv_cache.hpp ~1682-1692: 'const bf16* k_vnni_plane(...) const noexcept { return reinterpret_cast<const bf16*>(kv_block<geometry>(slot, kv_head).k); }'); callers self_attention.hpp dense call (~1437) and qk_group call (~1636); Note [K VNNI storage] item 2
  CHANGE: C08 APPLIES. Delete k_vnni_plane. Add 'template <kv_geometry geometry> requires(book_t::template declares_geometry<geometry>() && k_vnni::layout_on<geometry.head_size>) k_vnni_view<const bf16, page_size, geometry.head_size> k_packed(kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound) { return kv_block<geometry>(slot, kv_head).k.as_view(); }'. Internal writers (set_k_row, set_k_block, copy_storage_slot) use 'kv_block<geometry>(slot, kv_head).k.as_view()' directly, as the PARENT's V writers do. Update the two self_attention.hpp calls and the Note text.
  WHY: Design table row 'page::k, page::k_vnni_plane'; goal (c). PARENT analog page::v_packed (kv_cache.hpp:1946-1956).
  EVIDENCE: PARENT kv_cache.hpp:1952: 'v_vnni_view<const bf16, page_size, geometry.head_size> v_packed(kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound) { return kv_block<geometry>(slot, kv_head).v.as_view(); }'.
- [MUST] h/tron/models/kv_cache.hpp, h/tron/models/model.hpp, h/tron/scheduler/full.hpp, t/t_llama_unit.cpp, t/t_k_vnni_layout.cpp, t/t_amx_dispatch_dtype.cpp @ page::set_k_row / get_k_row (CHILD kv_cache.hpp ~1694-1765, raw 'const bf16* row' / 'bf16* row'); callers: model.hpp store_k_block 'pg.template set_k_row<geometry.kv>(slot, kv_head, j, kout.data)' and '(..., conv[0])' (CHILD ~2918-2924); full.hpp k_head_fn 'get_k_row<hw_kv>(slot, kv_head, off, dest)'; t_llama_unit ~25 set_k_row/get_k_row sites (diff lines 18-351); t_k_vnni_layout:401-459; t_amx_dispatch_dtype:101
  CHANGE: C09 APPLIES with PARENT naming. Parameters become typed unit-stride rows; call typed store_row/load_row on the owner view in the packed branch and keep the memcpy in the native branch. Follow the PARENT's alias shape (const_v_row_view<T, Cols, Dma> / v_row_view<T, Cols, Dma> fix aligned = VIEW_ALIGNED_TRUE; helpers v_source_row<Cols, Dma>(ptr) / v_destination_row(ptr)), i.e. add const_k_row_view<Cols, Dma> / k_row_view<Cols, Dma> and k_source_row / k_destination_row for bf16 rows. Every caller constructs the view explicitly (template deduction does not use conversions). Preserve _mm512_i32scatter_epi32 / _mm512_i32gather_epi32 bodies; no head_size % 32 requirement added.
  WHY: Design table row 'page::set_k_row, page::get_k_row'; goal (c). The design's 'Aligned' template parameter is a shape difference from the PARENT (see design_contradictions).
  EVIDENCE: PARENT v_vnni.hpp: 'template <typename T, size_t Cols, bool Dma = VIEW_DMA_FALSE> using const_v_row_view = const_view<T, VIEW_ALIGNED_TRUE, Dma, seq<Cols>, sseq<1>>;' and 'v_source_row<Cols, Dma>(const T* row)'; PARENT model.hpp diff: 'v_source_row<geometry.kv.head_size, v_buffer_t::dma>(&vs[ix][...])'; PARENT full.hpp diff: 'v_destination_row<model_t::hardware_attention_geometry.kv.head_size>(dest)'.
- [MUST] h/tron/models/kv_cache.hpp @ page::set_k_block (CHILD ~1720-1737: 'k_vnni::store_block(reinterpret_cast<bf16*>(kv_block<geometry>(slot, kv_head).k), c, present, rows);')
  CHANGE: C10 APPLIES. Keep the name and the 'const bf16* const rows[k_vnni::BLOCK_TOKENS_16]' parameter (null entries for absent lanes); call 'store_block(kv_block<geometry>(slot, kv_head).k.as_view(), c, present, rows)'. The source-row pointers are native rows, not packed storage, so they stay raw.
  WHY: Design table row 'page::set_k_block'.
  EVIDENCE: CHILD k_vnni.hpp:193-216 store_block(bf16* plane, size_t c, __mmask16 present, const bf16* const rows[BLOCK_TOKENS_16]).
- [MUST] h/tron/models/kv_cache.hpp @ copy_storage_slot packed branch (CHILD ~2099-2117: 'memcpy(dst_block.k, src_block.k, sizeof(dst_block.k));' and the gather_row/scatter_row loop with 'alignas(64) bf16 row[geometry.head_size]')
  CHANGE: C11 APPLIES. Whole page: 'dst_block.k = src_block.k;' (defaulted owner assignment, trivially copyable). Other ranges: a typed K copy_token(dst_view, dst_token, src_view, src_token) whose body is the existing gather+scatter through a stack row. Keep the native memcpy branch. Add no K plane-copy helper.
  WHY: Design table row 'Copy and score readers'; goal (d) stored bytes unchanged (a struct copy of 16384 bytes equals the memcpy).
  EVIDENCE: CHILD kv_cache.hpp diff @@ -1930,15 +2096,35 @@ (verified text 'memcpy(dst_block.k, src_block.k, sizeof(dst_block.k))'). PARENT V analog: book::append copies V through copy_token (PR body).
- [MUST] h/tron/kernels/amx_attn_iface.hpp, src/tron/kernels/amx_attn.cpp, h/tron/kernels/k_vnni.hpp, t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp @ qk_vnni_128x4 declaration (CHILD iface :250-253 'void qk_vnni_128x4(const bf16* k_vnni_plane, const bf16* q_rows, float* s, size_t s_stride_floats) noexcept;'), definition (CHILD amx_attn.cpp :196-262), fake (CHILD t_amx_dispatch_dtype :196), qk_group (CHILD k_vnni.hpp:246-252 'void qk_group(const bf16* plane, ...)'), test (CHILD t_amx_numerics VNNI case: 'struct alignas(64) vnni_plane { bf16 v[...] }' + 'qk_vnni_128x4(plane->v, q_rows, ...)')
  CHANGE: C12 APPLIES. qk_vnni_128x4 takes 'k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page' by value; body: 'const bf16* const plane = detail::k_vnni_access::plane(k_page);' then the unchanged tile loads. qk_group<kv_mul, q_scalar>(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page, const q_scalar* q, uint64_t live, float* s, size_t s_stride). Fake: same parameter type. t_amx_numerics: 'auto k_owner = std::make_unique<k_vnni_tensor<64,128>>();' filled by typed store_row, passed as k_owner->as_view() (writable converts to const). Score arithmetic unchanged (goal d).
  WHY: Design: 'Pass k_vnni_view<const bf16,64,128> by value to qk_vnni_128x4 and the corresponding shape to qk_group.' PARENT precedent for both kernel and test.
  EVIDENCE: PARENT amx_attn.cpp: 'void weights_times_v_128x4(v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page, ...) { const bf16* const v_pairs = detail::v_vnni_access::plane(v_page);'; PARENT t_amx_numerics diff line 52: 'auto v_owner = std::make_unique<tron::v_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>();'.
- [MUST] h/tron/tensor/k_vnni.hpp (new), h/tron/kernels/k_vnni.hpp @ whole CHILD header h/tron/kernels/k_vnni.hpp (310 lines)
  CHANGE: C13 APPLIES. Move to h/tron/tensor/k_vnni.hpp: the constants (:44-84), layout_on (:86-97), constexpr index (:99-107, keep the spelling tron::k_vnni::index for the test anchors), detail::pair_base / pair_row_offsets (:109-133), scatter_row -> store_row (:135-146), transpose_16x16_epi32 (:148-180), store_block (:182-216), gather_row -> load_row (:218-228), a K copy_token, detail::k_vnni_access, k_vnni_tensor, k_vnni_view. h/tron/kernels/k_vnni.hpp keeps only qk_group (:230-308) and includes the tensor header. The PARENT's V bulk operations are free functions in namespace tron named append_v_row / load_row / copy_token; the K ones can overload load_row / copy_token on the view type and add store_row / store_block.
  WHY: Design: header split with 'qk_group only' in the kernel header; neither tensor header includes an attention kernel header.
  EVIDENCE: git show origin/jhan-amx-vnniK:h/tron/kernels/k_vnni.hpp | cat -n (line ranges above); PARENT v_vnni.hpp function names.
- [MUST] h/tron/models/kv_cache.hpp, h/tron/models/self_attention.hpp, src/tron/kernels/amx_attn.cpp, t/t_amx_dispatch_dtype.cpp, t/t_k_vnni_layout.cpp, t/t_amx_numerics.cpp @ include lists: CHILD kv_cache.hpp:27 '#include "tron/kernels/k_vnni.hpp"'; CHILD self_attention.hpp:21-28 has no k_vnni include (gets qk_group through kv_cache.hpp); CHILD amx_attn.cpp:14; tests
  CHANGE: C14 APPLIES. kv_cache.hpp includes tron/tensor/k_vnni.hpp (drops the kernel header). self_attention.hpp adds '#include "tron/kernels/k_vnni.hpp"' for qk_group. amx_attn.cpp, t_amx_dispatch_dtype.cpp, t_amx_numerics.cpp, t_k_vnni_layout.cpp include tron/tensor/k_vnni.hpp (and the kernel header only where qk_group is called). Do not forward-declare seq/sseq as classes: they are aliases (seq.hpp:22, :25).
  WHY: Design include rules; the kernels-to-tensor direction follows dotter.hpp (includes tron/tensor/view.hpp) and the PARENT's amx_attn.cpp.
  EVIDENCE: git show origin/main:h/tron/tensor/seq.hpp:22 'using seq = std::integer_sequence<size_t, ds...>;'; main dotter.hpp:10; PARENT amx_attn.cpp includes kv_cache_fwd.hpp, v_vnni.hpp, view.hpp.
- [MUST] h/tron/tensor/kv_cache_fwd.hpp @ after the v_vnni_tensor / v_vnni_view forward declarations (PARENT lines 29-36)
  CHANGE: C15 APPLIES for the tensor and the view; the k_vnni_row declaration is SUPERSEDED (see C17). Add 'template <size_t Rows, size_t Cols> struct k_vnni_tensor; template <typename T, size_t Rows, size_t Cols> struct k_vnni_view;' in namespace tron with a two-line comment parallel to the V one. No intrinsics, no seq.hpp include (the PARENT spells std::integer_sequence here).
  WHY: Design: 'Add unconstrained ... forward declarations to h/tron/tensor/kv_cache_fwd.hpp, parallel to the V declarations.'
  EVIDENCE: git show origin/jhan-kv-typed-tensors:h/tron/tensor/kv_cache_fwd.hpp (55 lines; declares bf16, view, const_view, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, v_vnni_tensor, v_vnni_view, native_k_view, const_native_k_view).
- [MUST] h/tron/kernels/amx_attn_iface.hpp @ qk_vnni_128x4 declaration (CHILD :242-253) and Note [QK orientation] paragraph (CHILD :215-223)
  CHANGE: C16 APPLIES. Declare 'void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page, const bf16* q_rows, float* s, size_t s_stride_floats) noexcept;' using only kv_cache_fwd.hpp (already included at PARENT :113). Rename the comment's 'k_vnni_plane = the page's 16 KiB K plane' to the view. The header stays intrinsics-free.
  WHY: Design: 'Then amx_attn_iface.hpp can declare qk_vnni_128x4(k_vnni_view<const bf16,PAGE_TOKENS_64,HEAD_SIZE_128>, const bf16*, float*, size_t) noexcept without intrinsics.'
  EVIDENCE: PARENT iface :222 'void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128> k_page, ...' and :234-235 for V.
- [MUST] h/tron/tensor/k_vnni.hpp, h/tron/tensor/kv_cache_fwd.hpp, t/t_k_vnni_layout.cpp, t/t_llama_unit.cpp @ design items 'k_vnni_row', 'expression base', 'named host-tensor expression consumer' (design-child-section.txt lines 11, 15, 51; full design Q3 at line 136, child test row at line 608)
  CHANGE: C17 SUPERSEDED: do NOT add k_vnni_row, no expr base on k_vnni_view, no operator[], no host-tensor consumer test. The design itself says 'If Q3 is rejected, remove the row expressions and their compatibility checks from both families.' SHOULD: add STATIC_REQUIRE_FALSE(matrix_indexes_rows<k_vnni_view<...>>) next to the PARENT's V checks (t_llama_unit :422-423).
  WHY: PARENT commit c12df586b6 'Drop v_vnni_row and the expression base of v_vnni_view' after review thread 4134076112 ('do not add code which has no consumer'). PR body row 2: 'Dropped by agreement'.
  EVIDENCE: git log 996f58ec82..origin/jhan-kv-typed-tensors (c12df586b6); pr4557-body.md lines 37 and 62.
- [MUST] h/tron/gof.hpp, src/tron/gof.cpp, h/tron/scheduler/full.hpp, t/t_gof_dma.cpp, t/t_gof_staging_leaks.cpp, t/t_phase1_integration.cpp @ page_info::k_head_fn (CHILD gof.hpp:58-79 'std::function<bf16*(kv_slot_id slot, size_t kv_head, bf16* scratch)> k_head_fn;'); gof.cpp k_scratch (CHILD :203, :213); full.hpp k_head_fn lambda (CHILD :2644-2660)
  CHANGE: C18 APPLIES, already in the CHILD; preserve through the merge (these files merged without conflict). One adaptation: full.hpp's 'pg_ptr->template get_k_row<hw_kv>(slot, kv_head, off, dest);' must pass a typed destination row once C09 lands (PARENT does 'v_destination_row<...>(dest)' two lines below). gof::populate consumes k_heads[h] before the next token (loop body), satisfying [S14].
  WHY: Design table row 'hardware::page_info K callback'.
  EVIDENCE: git diff c7844ca2ce origin/jhan-amx-vnniK -- h/tron/gof.hpp h/tron/scheduler/full.hpp src/tron/gof.cpp t/t_gof_dma.cpp; PARENT full.hpp diff.
- [MUST] h/tron/tensor/k_vnni.hpp @ store_row (scatter) and store_block bodies moved from CHILD k_vnni.hpp:139-146 and :194-216
  CHANGE: C19 APPLIES, bodies unchanged: store_row uses _mm512_i32scatter_epi32 (4-byte lanes), store_block uses full _mm512_storeu_si512 for a full block and _mm512_mask_storeu_epi32 for a partial block. No read-merge-rewrite of a 64-byte line, so disjoint token lanes may be written concurrently by several workers during the shared save.
  WHY: Design [S10]: 'Use lane scatter or lane-masked stores. Never read, merge, and rewrite the whole 64-byte line.'
  EVIDENCE: CHILD k_vnni.hpp:143-144, :206-213.
- [MUST] h/tron/tensor/k_vnni.hpp, h/tron/models/kv_cache.hpp @ #if TRON_CHUNK_SIZE == 16 guards; CHILD kv_cache.hpp:35-40 '#error TRON_K_VNNI requires TRON_CHUNK_SIZE == 16'
  CHANGE: C20 APPLIES, 8-lane part UNVERIFIABLE here. Keep k_vnni_tensor / k_vnni_view complete at both widths (the fake kernel definitions in t_amx_dispatch_dtype take them by value). Guard the AVX-512 operation bodies (store_row, load_row, store_block, copy_token, transpose) and qk_group with '#if TRON_CHUNK_SIZE == 16', as the PARENT guards append_v_row/load_row/copy_token. Keep the #error. The CHILD's kernels/k_vnni.hpp today has no width guard (only '#ifdef TRON_K_VNNI' at :91-97) while t_k_vnni_layout.cpp includes it unguarded at :25 and guards only its cases (:31, :466); whether an -DAVX512=OFF build compiles it was not tested in this analysis. Report packed K at 8 lanes as not applicable; the limited 8-lane check uses TRON_K_VNNI=OFF.
  WHY: Design: 'Keep K class definitions complete in both vector widths for unconditional fake definitions. Guard packed operation bodies at 16 lanes.'
  EVIDENCE: PARENT v_vnni.hpp '#if TRON_CHUNK_SIZE == 16' around the operations; CHILD k_vnni.hpp guard list from grep -n -E '^#(if|else|endif)'.
- [SHOULD] t/t_k_vnni_layout.cpp @ struct alignas(64) plane_and_rows { bf16 plane[64*128]; ... } (CHILD :67-68); direct plane reads 'buf->plane[tron::k_vnni::index(tok, d)]' (:120-122, :143); index anchors (:81-90); book-level cases (:385-465)
  CHANGE: C21 APPLIES. Replace the raw plane buffers by k_vnni_tensor<64,128> owners (make_unique, heap: 16 KiB each) filled with 64 typed store_row calls (poison first); for the physical-layout checks memcpy the trivially copyable owner into a bf16[8192] test buffer and index it with tron::k_vnni::index. Keep the STATIC_REQUIRE anchors on index(). Do not use detail::k_vnni_access in tests. Book-level cases pass typed rows to set_k_row/get_k_row.
  WHY: Design: 'Adapt t_k_vnni_layout to actual aligned owners. Fill poison with 64 typed row saves. Copy the trivially copyable owner's bytes to a test buffer ... Preserve independent index anchors and avoid the internal friend helpers.'
  EVIDENCE: git show origin/jhan-amx-vnniK:t/t_k_vnni_layout.cpp | grep -n (lines above).
- [MUST] h/tron/models/model.hpp @ save_k overload pair (CHILD :3064-3079: 'void save_k(batch* q_batch, kv_buffer_t& ks, size_t n_workers = 1)' and the descriptor form with 'size_t n_workers = 1'); save_k_helper pair (CHILD :2950-2990: '(batch*, kv_buffer_t&, size_t worker_ix, size_t n_workers)'); save_k_impl (CHILD :2992+)
  CHANGE: C22 APPLIES, NOT already done in the CHILD (the task's doubt is resolved: the CHILD at 30c4ac82cb still has two separate pairs). Merge into one pair: 'save_k(batch*, kv_buffer_t&, size_t worker_ix = 0, size_t n_workers = 1)' and the descriptor form. Delete save_k_helper. TRON_ASSERT(n_workers >= 1) and TRON_ASSERT_LT(worker_ix, n_workers). Worker 0 keeps window setup, claims, join, completion marks, GOF credits, countdowns (today's save_k_impl). First check layout_on and k_store_shared(q_batch, n_workers): if not shared, workers > 0 return at once and worker 0 does the serial save; if shared, workers > 0 wait for the window, claim units, increment finished, return (today's save_k_helper body).
  WHY: Design 'Worker-index request' [S18]. This is orthogonal to the typed tensors; keep it as its own commit.
  EVIDENCE: git show origin/jhan-amx-vnniK:h/tron/models/model.hpp | grep -n save_k (lines 3065, 3073, 2953-2990).
- [MUST] ingest/src/TronCpp.hs @ runHelperStatement AttentionStmt (CHILD :2321-2340: attentionRuntimeCall "save_k_helper" ... [key, ExprLit "worker_ix", ExprLit "n_workers"]); submitAttentionOperation saveKv (CHILD :2399-2408: attentionRuntimeCall "save_k" stmt [key, ExprLit "n_workers"])
  CHANGE: C23 APPLIES. run(): save_k(..., k, 0, n_workers). run_main_help: save_k(..., k, worker_ix, n_workers) (rename the helper-side call). Preserve main's intervening generator changes (main changed TronCpp.hs by 194 lines between c7844ca2ce and 996f58ec82; the merge was automatic). Read ingest/AGENTS.md first.
  WHY: Design: 'Generated run() passes 0, n_workers. Generated run_main_help passes worker_ix, n_workers.'
  EVIDENCE: git diff c7844ca2ce origin/jhan-amx-vnniK -- ingest/src/TronCpp.hs; git ls-tree origin/main ingest/AGENTS.md exists.
- [MUST] ingest/test/LoopyTronSpec.hs @ CHILD lines 2801-2818 (case 1: 'Txt.count "outer_state.template save_k<" cpp `shouldBe` 1', main tail 'q_batch->outer_batch,k,n_workers);', 'save_k_helper<' count 1, helper tail 'q_batch->outer_batch,k,worker_ix,n_workers);') and 3225-3232 (case 2: 'save_k<' count 1, ',k,n_workers);', 'save_k_helper<' count 1, ',k,worker_ix,n_workers);')
  CHANGE: C24 APPLIES; the design's line numbers and call shapes match the CHILD exactly (8 assertions, 7 change, the one at 3232 stays). Both 'save_k<' counts become 2; remove or set to 0 the two 'save_k_helper<' counts; main tails become ',k,0,n_workers);' (case 1 with the attentionCallPrefix "save_k" prefix); the helper call text in case 1 uses attentionCallPrefix "save_k" with tail ',k,worker_ix,n_workers);'. Then in nix develop: make format-haskell, bin/ingest-cabal build, bin/ingest-cabal test; the required CI job is nix build .#checks.x86_64-linux."tron-ingest:test:ingest-tests".
  WHY: Design [S21].
  EVIDENCE: git show origin/jhan-amx-vnniK:ingest/test/LoopyTronSpec.hs | sed -n '2790,2830p;3215,3240p'.
- [MUST] t/t_llama_unit.cpp, h/tron/plugins/llama.hpp @ CHILD t_llama_unit.cpp:2767 'state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts);', :2779-2780 'save_k_helper<geometry>(&q_batch, operation, kouts, worker_ix, N_WORKERS_3)', :2783-2784 'save_k<geometry>(&q_batch, operation, kouts, N_WORKERS_3)'; llama.hpp:1024 'outer_state.template save_k<attention_geometry>(' and doc comments :82, :111
  CHANGE: C25 APPLIES. :2779-2780 -> save_k<geometry>(&q_batch, operation, kouts, worker_ix, N_WORKERS_3); :2783-2784 -> save_k<geometry>(&q_batch, operation, kouts, 0, N_WORKERS_3); :2767 unchanged (defaults). llama.hpp:1024 stays valid through the defaults (verify its argument list); update the two comments if they name the worker count. Search every old positional call that passed only n_workers.
  WHY: Design: 'Update adjacent comments and direct three-thread calls in t/t_llama_unit.cpp. Search all old positional calls, which passed only n_workers.'
  EVIDENCE: git grep -n -E 'save_k<|save_k\(' origin/jhan-amx-vnniK -- h/tron/plugins src/tron; t_llama_unit grep above.
- [SHOULD] config/test-benchmarks.json @ granite_rapids_6962p block (key at merged line 364): t_llama_unit row (~424), t_amx_numerics / t_amx_dispatch_dtype / t_k_vnni_layout rows (~476-478)
  CHANGE: C26 APPLIES. Carry the CHILD's records as historical in the PR text (t_llama_unit 13.436/13.388/13.618 s, 643 MB; t_amx_numerics 0.804/0.745/0.728 s; t_k_vnni_layout 0.709/0.697/0.696 s). After the typed-owner and merged-save commits, remeasure on delphi-3bda: run bin/slice route first, then 'bin/slice bench --update t_k_vnni_layout t_llama_unit' (add t_amx_numerics if materially changed; '--new' if the layout row is missing); refresh only the granite_rapids_6962p block; record any deferral in the PR text. Whole-host benchmark use needs the user's authorization (design section 8).
  WHY: Design: 'Include config/test-benchmarks.json in the shared-file review ... resolve the shared t_llama_unit record by remeasurement.'
  EVIDENCE: git diff c7844ca2ce origin/jhan-amx-vnniK -- config/test-benchmarks.json; main's row at merged :425 5.187/5.256/4.936 s, 331 MB.
- [MUST] .github/workflows/cmake-single-platform.yml, README.ci.md @ CHILD workflow :333-334 '-DTRON_REQUIRE_ALL_MODEL_TESTS=ON -DTRON_AMX_DISPATCH=ON \ -DTRON_K_VNNI=ON'; CHILD README.ci.md:518-556 (flag line + 'TRON_K_VNNI=ON stores the K cache...' paragraph)
  CHANGE: C27 APPLIES, already in the CHILD and merged without conflict. Read .github/AGENTS.md and README.ci.md before touching them again; keep the flag and its README paragraph in one commit; run the affected CI-tool tests (bin/ci tests) and the matching Nix checks. Do not assume the README conflicts (it did not).
  WHY: Design: 'Read .github/AGENTS.md and README.ci.md before porting the packed-K workflow flag and its README paragraph together.'
  EVIDENCE: git status --short at merge start: both files 'M', not 'UU'; git ls-tree origin/main .github/AGENTS.md exists.
- [MUST] src/tron/CMakeLists.txt @ merged file: TRON_K_VNNI block at :227-240 (after the TRON_AMX_DISPATCH block, auto-merged) and main's new 'tron_model_compile_config' INTERFACE library at :316-351 (main :298-330) whose compile-definition blocks re-declare TRON_AMX_DISPATCH (main :323-326) and TRON_PAGE_SHARE_COUNTERS (main :327-330) for the generated model OBJECT libraries (main :342 'target_link_libraries(${MODEL_TARGET} PRIVATE tron_model_compile_config)'); the interface library does not link 'tron' (main :299-305)
  CHANGE: C28 APPLIES with a new MUST finding: add 'if(TRON_K_VNNI) target_compile_definitions(tron_model_compile_config INTERFACE TRON_K_VNNI) endif()' next to the TRON_AMX_DISPATCH entry. Without it the generated model objects compile with k_vnni::layout_on == false (row-major kv_block) while libtron compiles with true: a silent layout mismatch (one definition rule violation). This block did not exist at the CHILD's base c7844ca2ce (its TRON_AMX_DISPATCH appeared only once, at :193-197), so the CHILD could not have added it. Verify by grepping the generated model object's compile command for -DTRON_K_VNNI.
  WHY: Design: 'Include ... main's restructured src/tron/CMakeLists.txt, where the child's build-option block must be placed.' Compile/run correctness.
  EVIDENCE: git show origin/main:src/tron/CMakeLists.txt | sed -n '296,332p'; git show c7844ca2ce:src/tron/CMakeLists.txt | grep -n tron_model_compile_config (no hits).
- [MUST] GitHub PR #4424 (positron-ai/tron) @ PR metadata (gh pr view 4424: baseRefName main, headRefName jhan-amx-vnniK, isDraft true, labels [Skip benchmarks], mergeable CONFLICTING)
  CHANGE: C29 APPLIES. Keep draft. Keep 'Skip benchmarks'. Add no 'Run CI' label without the user's direction. Retarget before pushing the new history: gh pr edit 4424 --base jhan-kv-typed-tensors. After #4557 merges: verify the base is main (GitHub retargets automatically when the base branch is deleted), rebase or merge onto updated main, check the diff and the child validation before promoting from draft.
  WHY: Design lines 5 and 23; repository rules [S12].
  EVIDENCE: gh pr view output above; #4557: isDraft false, reviewDecision CHANGES_REQUESTED, mergeable CONFLICTING; #4737: base jhan-amx-vnniK, MERGEABLE.
- [MUST] pr4557-body.md 'Response to the reviewer's comments on #4424' table @ rows 1, 3, 4, 5 end with the packed-K half waiting for #4424; row 2 (expr) 'Dropped by agreement'
  CHANGE: C30 APPLIES: row 1 (encapsulate the VNNI representation) -> C08 + C12 (no public K-plane pointer); row 3 (vnni_tensor type) -> C03 k_vnni_tensor; row 4 (row-wise load/store) -> C13 store_row/load_row/store_block/copy_token; row 5 (no bare bf16* without layout) -> C12 + C32 STATIC_REQUIRE checks. Row 2 (expr/tensor precedent) does NOT transfer to the child: dropped (C17). PR body sentence to honour: 'After merging this PR, we will rebase PR #4424 and update its code to use the new tensor data type.'
  WHY: Task item 4.
  EVIDENCE: pr4557-body.md lines 55-67.
- [MUST] verification on delphi-3bda (no file) @ design section 8 rows for the child (full design lines 608, 620-628, 656)
  CHANGE: C31 APPLIES. Build and run with TRON_K_VNNI=ON and OFF (16-lane, TRON_AMX_DISPATCH=ON); run the K cases also with TRON_AMX_DISABLE=1; keep logs-<host>/run-NNNN/t_amx_numerics.log showing the packed-K QK identity case passed without an 'AMX unavailable on this host' warning plus a separate TRON_AMX_DISABLE=1 run showing the warning; verify all 16 rows after disjoint worker writes, masks, independent source rows, whole-plane owner copy, scratch use; bit-identical K plane bytes and scores against the CHILD binary (goal d). Run bin/slice route before substantial execution.
  WHY: Design acceptance rules; task goal (a) and (d).
  EVIDENCE: design-new-tensor-type.txt lines 608, 656.
- [SHOULD] t/t_llama_unit.cpp @ probes (PARENT :84-135: amx_qk_accepts, amx_pv_accepts, owner_views_temporary, matrix_at_writes, matrix_indexes_rows) and case 'attention operations resolve to typed KV slots' (PARENT :358-460; the design's 84-123 / 316-342 are the pre-rebase line numbers)
  CHANGE: C32 APPLIES. Add amx_qk_vnni_accepts<K> probe; STATIC_REQUIRE(amx_qk_vnni_accepts<k_packed_t>) where k_packed_t = k_vnni_view<const bf16, 64, 128>; STATIC_REQUIRE_FALSE for const bf16*, bf16*, v_plane_t and the native k_plane_t; STATIC_REQUIRE_FALSE(amx_qk_accepts<k_packed_t>); writable-to-const conversion only; no construction from a pointer; no view of a temporary owner; at() const rules; no operator[]. Guard with #ifdef TRON_K_VNNI only where the page accessor type depends on the option.
  WHY: Design table 'Typed function boundaries' and goal (c).
  EVIDENCE: PARENT t_llama_unit.cpp:397-423.

## proposed_code
// ---- h/tron/tensor/kv_cache_fwd.hpp (PARENT names kept; add after v_vnni_view) ----
// Packed K types (TRON_K_VNNI): k_vnni_tensor owns one bf16 array of
// [Rows tokens * Cols dimensions] in the VNNI layout of h/tron/tensor/k_vnni.hpp;
// k_vnni_view refers to it. No row type (see v_vnni_view).
template <size_t Rows, size_t Cols>
struct k_vnni_tensor;
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view;

// ---- h/tron/tensor/k_vnni.hpp (new; moved from h/tron/kernels/k_vnni.hpp) ----
namespace tron {
namespace k_vnni {  // constants, layout_on<head_size>, constexpr index(token, dim): unchanged text
inline constexpr size_t K_PLANE_ALIGNMENT_64 = 64;
inline constexpr size_t K_BLOCK_TOKENS_16 = 16;   // or reuse BLOCK_TOKENS_16
inline constexpr size_t K_STEP_DIMS_32 = 32;      // or reuse STEP_DIMS_32
}  // namespace k_vnni
namespace detail { struct k_vnni_access; }

template <typename T>
concept k_vnni_element = std::same_as<T, bf16> || std::same_as<T, const bf16>;

template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view final {
  static_assert(k_vnni_element<T>, "a packed K plane holds bf16 or const bf16");
  static_assert(Rows > 0 && Rows % k_vnni::BLOCK_TOKENS_16 == 0, "K blocks hold 16 tokens");
  static_assert(Cols > 0 && Cols % k_vnni::STEP_DIMS_32 == 0, "K panels hold 32 dimensions");
  template <typename U>
    requires(std::is_const_v<T> && std::same_as<U, std::remove_const_t<T>>)
  TRON(inline) k_vnni_view(k_vnni_view<U, Rows, Cols> other) noexcept : data_(other.data_) {}
  TRON(nodiscard, inline, pure) T& at(size_t token, size_t dim) noexcept {
    TRON_ASSERT_LT(token, Rows); TRON_ASSERT_LT(dim, Cols);
    return data_[k_vnni::index(token, dim)];   // index is 64x128-specific today: generalize or static_assert Rows==64 && Cols==128
  }
  TRON(nodiscard, inline, pure) const bf16& at(size_t token, size_t dim) const noexcept { /* same */ }
private:
  friend struct k_vnni_tensor<Rows, Cols>;
  friend struct detail::k_vnni_access;
  template <typename U, size_t R, size_t C> friend struct k_vnni_view;
  TRON(inline) explicit k_vnni_view(T* data) noexcept : data_(data) {}
  T* data_;
};

template <size_t Rows, size_t Cols>
struct alignas(k_vnni::K_PLANE_ALIGNMENT_64) k_vnni_tensor final {
  static_assert(Rows > 0 && Rows % k_vnni::BLOCK_TOKENS_16 == 0, "K blocks hold 16 tokens");
  static_assert(Cols > 0 && Cols % k_vnni::STEP_DIMS_32 == 0, "K panels hold 32 dimensions");
  TRON(nodiscard, inline) k_vnni_view<bf16, Rows, Cols> as_view() & noexcept TRON(this_lifetimebound)
  { return k_vnni_view<bf16, Rows, Cols>(data_); }
  TRON(nodiscard, inline) k_vnni_view<const bf16, Rows, Cols> as_view() const& noexcept TRON(this_lifetimebound)
  { return k_vnni_view<const bf16, Rows, Cols>(data_); }
  k_vnni_view<bf16, Rows, Cols> as_view() && = delete;
  k_vnni_view<const bf16, Rows, Cols> as_view() const&& = delete;
private:
  alignas(k_vnni::K_PLANE_ALIGNMENT_64) bf16 data_[Rows * Cols];
};

namespace detail {
struct k_vnni_access final {
  template <typename T, size_t Rows, size_t Cols>
  TRON(nodiscard, inline, pure) static T* plane(k_vnni_view<T, Rows, Cols> v) noexcept { return v.data_; }
};
}  // namespace detail

// Contiguous bf16 transfer rows for set_k_row / get_k_row (not packed storage).
// Open question Q-A below: keep Aligned as a parameter (design) or fix VIEW_ALIGNED_TRUE (PARENT shape).
template <size_t Cols, bool Dma = VIEW_DMA_FALSE, bool Aligned = VIEW_ALIGNED_TRUE>
using const_k_row_view = const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;
template <size_t Cols, bool Dma = VIEW_DMA_FALSE, bool Aligned = VIEW_ALIGNED_TRUE>
using k_row_view = view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;
template <size_t Cols, bool Dma = VIEW_DMA_FALSE, bool Aligned = VIEW_ALIGNED_TRUE>
TRON(nodiscard, inline) const_k_row_view<Cols, Dma, Aligned> k_source_row(const bf16* row) noexcept { return {row}; }
template <size_t Cols, bool Dma = VIEW_DMA_FALSE, bool Aligned = VIEW_ALIGNED_TRUE>
TRON(nodiscard, inline) k_row_view<Cols, Dma, Aligned> k_destination_row(bf16* row) noexcept { return {row}; }

#if TRON_CHUNK_SIZE == 16
// Bodies = CHILD scatter_row / gather_row / store_block, with `plane` obtained once via detail::k_vnni_access::plane.
template <size_t Rows, size_t Cols, bool Dma, bool Aligned>
TRON(inline) void store_row(k_vnni_view<bf16, Rows, Cols> dst, size_t token, const_k_row_view<Cols, Dma, Aligned> src) noexcept;
template <size_t Rows, size_t Cols, bool Dma, bool Aligned>
TRON(inline) void load_row(k_vnni_view<const bf16, Rows, Cols> src, size_t token, k_row_view<Cols, Dma, Aligned> dst) noexcept;
template <size_t Rows, size_t Cols>
TRON(inline) void store_block(k_vnni_view<bf16, Rows, Cols> dst, size_t c, __mmask16 present,
    const bf16* const rows[k_vnni::BLOCK_TOKENS_16]) noexcept;
template <size_t Rows, size_t Cols>
TRON(inline) void copy_token(k_vnni_view<bf16, Rows, Cols> dst, size_t dst_token,
    k_vnni_view<const bf16, Rows, Cols> src, size_t src_token) noexcept;  // gather into a 64-byte-aligned stack row, scatter
#endif
}  // namespace tron

// ---- h/tron/kernels/k_vnni.hpp (keeps qk_group only) ----
#include "tron/tensor/k_vnni.hpp"
namespace tron::k_vnni {
template <size_t kv_mul, typename q_scalar>
TRON(inline) void qk_group(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const q_scalar* q, uint64_t live, float* s, size_t s_stride) noexcept;  // body: const bf16* plane = detail::k_vnni_access::plane(k_page); then unchanged
}

// ---- h/tron/models/kv_cache.hpp ----
template <size_t page_size, size_t head_size>
struct alignas(kv_block_alignment) kv_block {
  using k_storage = std::conditional_t<k_vnni::layout_on<head_size>,
      k_vnni_tensor<page_size, head_size>, bf16[page_size * head_size]>;
  static_assert(std::is_trivially_default_constructible_v<k_storage> &&
      std::is_trivially_copyable_v<k_storage> && std::is_trivially_destructible_v<k_storage>,
      "the DMA allocation creates kv_blocks; see Note [KV block lifetime]");
  alignas(kv_block_alignment) k_storage k;
  // ... v as in PARENT ...
  static_assert(sizeof(k) == sizeof(v));
  TRON(nodiscard, inline, pure) auto k_view() noexcept TRON(this_lifetimebound)
    requires(!k_vnni::layout_on<head_size>) { return view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<page_size, head_size>>{k}; }
  // k_view() const, k_at(), k_at() const: same requires clause
};

// page:
template <kv_geometry geometry>
  requires(book_t::template declares_geometry<geometry>() && k_vnni::layout_on<geometry.head_size>)
TRON(nodiscard, inline, pure)
k_vnni_view<const bf16, page_size, geometry.head_size> k_packed(kv_slot_id slot, size_t kv_head) const noexcept
    TRON(this_lifetimebound) { return kv_block<geometry>(slot, kv_head).k.as_view(); }

template <kv_geometry geometry, bool Dma, bool Aligned>
  requires(book_t::template declares_geometry<geometry>())
TRON(inline) void set_k_row(kv_slot_id slot, size_t kv_head, size_t i_page,
    const_k_row_view<geometry.head_size, Dma, Aligned> row) noexcept {
  TRON_ASSERT_LT(i_page, page_size);
  if constexpr (k_vnni::layout_on<geometry.head_size>) {
    store_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);
  } else {
    std::memcpy(kv_block<geometry>(slot, kv_head).k_at(i_page).data, row.data, geometry.head_size * sizeof(bf16));
  }
}
// get_k_row mirrors with k_row_view + load_row; set_k_block calls store_block(kv_block<geometry>(slot, kv_head).k.as_view(), c, present, rows).
// copy_storage_slot packed branch: whole page -> dst_block.k = src_block.k; else copy_token(dst_block.k.as_view(), dst_begin + i, src_block.k.as_view(), src_begin + i).

// ---- h/tron/kernels/amx_attn_iface.hpp ----
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const bf16* q_rows, float* s, size_t s_stride_floats) noexcept;

// ---- h/tron/models/self_attention.hpp (dense page) ----
if constexpr (k_vnni::layout_on<operation_head_size>) {
  amx_attn_h128g4::qk_vnni_128x4(pg.template k_packed<geometry.kv>(slot, kv_head), q_packed, &s_pages[0][0], page::page_size);
} else {
  amx_attn_h128g4::qk_rowmajor_128x4(pg.template k<geometry.kv>(slot, kv_head), q_packed, &s_pages[0][0], page::page_size);
}
// partial page: k_vnni::qk_group<operation_kv_mul>(page.template k_packed<geometry.kv>(slot, kv_head), q.data + ..., live, &s_pages[0][0], page::page_size);

// ---- h/tron/scheduler/full.hpp k_head_fn ----
pg_ptr->template get_k_row<hw_kv>(slot, kv_head, off, k_destination_row<hw_kv.head_size>(dest));

// ---- h/tron/models/model.hpp (merged worker pair; delete save_k_helper) ----
template <attention_geometry geometry, size_t operation_ix, typename kv_buffer_t>
void save_k(batch* q_batch, kv_buffer_t& ks, size_t worker_ix = 0, size_t n_workers = 1) noexcept;
template <attention_geometry geometry, typename kv_buffer_t>
void save_k(batch* q_batch, attention_operation_descriptor const& operation, kv_buffer_t& ks,
    size_t worker_ix = 0, size_t n_workers = 1) noexcept;
// body start: TRON_ASSERT(n_workers >= 1, ...); TRON_ASSERT_LT(worker_ix, n_workers);
//   if (!k_store_shared<geometry>(q_batch, n_workers)) { if (worker_ix != 0) return; serial save + readiness; return; }
//   if (worker_ix != 0) { today's save_k_helper body; return; }  else today's shared save_k_impl body.
// store_k_block row store: pg.template set_k_row<geometry.kv>(slot, kv_head, j, k_source_row<geometry.kv.head_size>(kout.data));

// ---- ingest/src/TronCpp.hs ----
-- run():          attentionRuntimeCall "save_k" stmt [Var key, ExprLit "0", ExprLit "n_workers"]
-- run_main_help:  attentionRuntimeCall "save_k" attention [Var key, ExprLit "worker_ix", ExprLit "n_workers"]
// ---- ingest/test/LoopyTronSpec.hs (both cases) ----
-- Txt.count "outer_state.template save_k<" cpp `shouldBe` 2
-- main tail:   "q_batch->outer_batch,k,0,n_workers);"   /  ",k,0,n_workers);"
-- helper tail: "q_batch->outer_batch,k,worker_ix,n_workers);" / ",k,worker_ix,n_workers);"  (prefix attentionCallPrefix "save_k")
-- drop the two `Txt.count "outer_state.template save_k_helper<"` lines

// ---- src/tron/CMakeLists.txt (main's tron_model_compile_config block) ----
if(TRON_K_VNNI)
  target_compile_definitions(tron_model_compile_config INTERFACE
    TRON_K_VNNI)
endif()

// ---- git (recommended, see open_questions) ----
# git -C <repo> tag jhan-amx-vnniK-pre-typed 30c4ac82cb            # preserve the old child head
# git checkout -b jhan-amx-vnniK-typed 30c4ac82cb
# git merge --no-ff origin/jhan-kv-typed-tensors -m "Merge branch 'jhan-kv-typed-tensors' into jhan-amx-vnniK-typed"
# ... adaptation commits C13, C03/C02, C01/C06/C08-C11, C12/C16, C18, C21/C32, C22-C25, C28, C26 ...
# gh pr edit 4424 --base jhan-kv-typed-tensors   # only when pushing to jhan-amx-vnniK itself

## design_contradictions
- Q3 row expressions: design-child-section.txt lines 11, 15 and 51 define k_vnni_row, an expression base and a host-tensor consumer test. The PARENT dropped v_vnni_row and the expr base in c12df586b6 after review thread 4134076112 (pr4557-body.md lines 37, 62). The design's own fallback sentence ('If Q3 is rejected, remove the row expressions and their compatibility checks from both families') applies: the child adds no k_vnni_row and no k_vnni_row forward declaration.
- native_k_storage type: the design spells 'using native_k_storage = bf16s[page_size][head_size / chunk_size];'. The PARENT's kv_block::k is 'bf16 k[page_size * head_size]' (c73e7fb2f9; kv_cache.hpp:2452 at PARENT) and k_view() builds its view from that array without a cast. The child's native branch must be bf16[page_size * head_size].
- Row view shape: the design prescribes 'const_view<bf16,Aligned,Dma,seq<D>,sseq<1>>' with the caller's Aligned flag preserved. The PARENT's row aliases fix aligned to VIEW_ALIGNED_TRUE ('const_v_row_view<T, Cols, Dma> = const_view<T, VIEW_ALIGNED_TRUE, Dma, seq<Cols>, sseq<1>>') and construct through v_source_row<Cols, Dma>(ptr) / v_destination_row(ptr). Not a hard contradiction, but the child cannot reuse the V helpers for an Aligned=false K row; it needs its own K aliases either way (open question Q-A).
- Fixed 64x128 shape in the K class bodies: full design line 377 says 'The child's packed-K owner and matrix view assert that fixed shape inside their definitions', while the reviewer's sketch (ben-sketch) constrains storage to Tokens % 16 == 0 and Dims % 32 == 0 and leaves 64x128 to the kernels ('Kernels can impose stricter restrictions'). The CHILD's amx_attn.cpp already static_asserts the kernel shape. Recommend the sketch's storage-level constraint; the child's constexpr index() is written for 64 tokens x 128 dims (TOKEN_BLOCKS_4, DIM_STEPS_4), so at() must either generalize index() to Rows/Cols or the view must static_assert Rows == 64 && Cols == 128 until it does.
- Worker-index item: the computed task asked whether the CHILD already has the merged save_k signature. It does not: at 30c4ac82cb model.hpp:3065 and :3073 take 'size_t n_workers = 1' and save_k_helper (:2953-2990) takes (worker_ix, n_workers); LoopyTronSpec.hs 2801-2818 / 3225-3232 and TronCpp.hs 2321-2340 / 2399-2408 match the design's described OLD shapes exactly. The item applies in full.
- Design line 13 'self_attention.hpp includes the kernel header directly for qk_group': at 30c4ac82cb self_attention.hpp (includes at :21-28) has no k_vnni include and relies on kv_cache.hpp. After the split kv_cache.hpp includes only the tensor header, so the direct include is a compile necessity, not just hygiene.
- Git strategy: the design prescribes reconstructing the child's changes as focused commits on the parent branch (history rewrite + force push). For this repository a merge-based branch (CHILD + 'Merge branch jhan-kv-typed-tensors into ...' + adaptation commits) is the safer choice: (1) PR #4737 (10 commits, base jhan-amx-vnniK, kv_cache.hpp +539 lines rewriting set_k_row/copy_storage_slot/k_vnni_plane with k_storage_ref and reinterpret_cast sites) keeps its merge base only if 30c4ac82cb stays reachable; (2) the PARENT is still CHANGES_REQUESTED and CONFLICTING with main (13 hunks in 6 files by 3-way merge-file: kv_cache.hpp 6, model.hpp 1, self_attention.hpp 1, heterogeneous_scheduler_compile.cpp 1, t_amx_dispatch_dtype.cpp 1, t_llama_unit.cpp 3), so its head will move again and a rewritten child would need repeated rebases; (3) git 2.34.1 on the box has no 'rebase --update-refs' (2.38) and only the old-style merge-tree, so stacked rebases are manual; (4) merge commits are the repo convention (15 of the last 200 merges on main are 'Merge branch main into <branch>'; the PARENT itself carries 'Merge PR #4698' 8e0cf77bed); (5) retargeting the PR base to jhan-kv-typed-tensors already gives GitHub a child-only diff, which is the design's stated reason for reconstruction. The design's requirement to preserve the old head locally (tag) applies to both strategies.

## risks
- Generated model objects compiled without TRON_K_VNNI: main's src/tron/CMakeLists.txt (after c7844ca2ce) builds model_<arch>.cpp OBJECT libraries against tron_model_compile_config, an INTERFACE target that does not link 'tron' and re-declares TRON_AMX_DISPATCH / TRON_PAGE_SHARE_COUNTERS explicitly (main :320-330). The merged tree has no TRON_K_VNNI there (merged :345-351). Result if unfixed: libtron's kv_block has a k_vnni_tensor K plane while the plugins see row-major K (layout_on false): silent corruption, not a compile error. Check the model object compile line for -DTRON_K_VNNI before the first runtron test.
- PR #4737 (jhan-amx-vnniK-i4500, bb32a80774) touches the same accessors the port retypes (kv_cache.hpp k_vnni_plane, set_k_row, set_k_block, get_k_row, copy_storage_slot with k_storage_ref, 11 reinterpret_cast sites; k_vnni.hpp row_ptr/block_to_vnni/block_to_rows returning bf16*; amx_attn_iface.hpp Note text; model.hpp +88; self_attention.hpp +80). Its later merge into the typed child will conflict in every one of these places and its new raw-pointer helpers violate goal (c); plan a typed rework of #4737 rather than a mechanical merge. Keep 30c4ac82cb reachable (tag) so #4737 keeps its merge base.
- 8-lane build: the CHILD's h/tron/kernels/k_vnni.hpp has AVX-512 intrinsics in non-template inline functions with no TRON_CHUNK_SIZE guard (only '#ifdef TRON_K_VNNI' at :91-97), and kv_cache.hpp includes it unconditionally. Whether a -DAVX512=OFF build compiles today is unmeasured (Insufficient data; a cmake --preset native -DAVX512=OFF -DTRON_AMX_DISPATCH=OFF configure+build of tron and t_amx_dispatch_dtype resolves it). The split must put the operation bodies under '#if TRON_CHUNK_SIZE == 16' as the PARENT does for V.
- The scratch worktree changed under this analysis: 7 UU files with markers at 17:00 UTC, 0 unmerged paths and 0 marker files by 17:17 UTC (reflog 'reset: moving to HEAD' at 10:07:52 -0700). Another process resolved the merge; the line numbers in textual_conflicts refer to the pre-resolution state and the resolution content was only spot-checked (kv_cache.hpp keeps k_vnni_plane at :1988 and v_packed at :2118; self_attention.hpp else-branch uses the PARENT's typed call; test-benchmarks.json keeps main's t_llama_unit 5.187 row and adds t_k_vnni_layout).
- The PARENT is not final: reviewDecision CHANGES_REQUESTED, mergeable CONFLICTING with main (13 hunks). Every further PARENT change (for example a renamed alias) must be re-merged into the child; naming in this report follows c12df586b6.
- config/test-benchmarks.json: the CHILD's granite_rapids_6962p t_llama_unit record (13.436 s) is 2.6x main's (5.187 s) because the shared-save case was added; after the port the row must be remeasured on the whole machine (bin/slice bench --update), which needs the user's authorization and a free 3bda (bin/slice route first). Deferring it leaves 'bin/slice bench --check' in the CMake lane at risk of failing on the stale row.
- Template deduction trap: with typed row parameters every raw-pointer caller of set_k_row/get_k_row stops compiling (about 25 sites in t_llama_unit.cpp, 8 in t_k_vnni_layout.cpp, 1 in t_amx_dispatch_dtype.cpp, 2 in model.hpp store_k_block, 1 in full.hpp, 2 in copy_storage_slot). A missed site is a compile error, not a silent bug, but the list must be worked through with TRON_K_VNNI both ON and OFF (the native branch is only instantiated OFF or for non-128 heads).
- The design says 'Pass k_vnni_view<const bf16,64,128> by value'. qk_group is a template over kv_mul and q_scalar and is also called for kv_mul 8 (qwen-3-30b-a3b): the view's fixed 64x128 shape is right (same page/head), but the kv_mul <= 16 static_assert and the MAX_KV_MUL_16 constant must move with it unchanged.
- Rebase strips commit-message lines that start with '#': none of the CHILD's 21 commit bodies start a line with '#' (grep count 0), so a rebase would not lose text; a merge does not touch messages at all.

## open_questions
- Q-A (naming/shape, decision needed before C09): K row views with the design's Aligned template parameter (const_view<bf16, Aligned, Dma, seq<D>, sseq<1>>) or the PARENT's shape with aligned fixed to VIEW_ALIGNED_TRUE (const_v_row_view<T, Cols, Dma>)? The K store/load bodies use unaligned loadu/storeu, so Aligned=false callers are legal for K; but every present caller passes 64-byte-aligned rows (btensor buffers, alignas(64) conv[], k_scratch, test arrays). Recommendation: K-specific aliases with a defaulted Aligned = VIEW_ALIGNED_TRUE (proposed_code), which satisfies both the design text and PARENT consistency.
- Q-B (namespace/naming of the K bulk operations): keep them in tron::k_vnni with the CHILD's names scatter_row/gather_row, or move to namespace tron as store_row/load_row/store_block/copy_token overloads on the view type (the PARENT puts append_v_row/load_row/copy_token in namespace tron)? The design names store_row/load_row. Recommendation: namespace tron, design names, constants and index() stay in tron::k_vnni (the test anchors spell tron::k_vnni::index).
- Q-C (git strategy, user decision): (1) design: rewrite the child as focused commits on jhan-kv-typed-tensors, force-push jhan-amx-vnniK, retarget #4424's base; or (2) merge-based: new branch jhan-amx-vnniK-typed = 30c4ac82cb + merge of c12df586b6 + adaptation commits, opened as a NEW draft PR based on jhan-kv-typed-tensors while #4424 and #4737 stay untouched until the parent merges; or (3) merge-based but pushed to jhan-amx-vnniK itself with #4424 retargeted. The user's request says 'work out draft PR' and 'test the changes at 3bda', which (2) satisfies with the least risk to #4737; the design text prescribes (1).
- Q-D (should the sync wait?): the PARENT is CHANGES_REQUESTED and CONFLICTING with main; starting now means re-merging each PARENT head. The user explicitly offered 'let me know if you think it is better to wait'. Data point: 13 PARENT-vs-main conflict hunks today, all in files the child also changes.
- Q-E (fixed shape in the view): generalize k_vnni::index() to Rows/Cols for at(), or static_assert Rows == 64 && Cols == 128 inside the K class bodies (full design line 377) until a second geometry exists? The storage-level constraint (Rows % 16, Cols % 32) is what std::conditional_t needs for the unselected specializations; the 64x128 pin can live in the kernels (already there in amx_attn.cpp static_asserts).
- Q-F (worker-index merge in this PR?): C22-C25 are orthogonal to the typed tensors and conflict heavily with #4737's model.hpp changes. Keep them as one separable commit at the end of the series, or defer to after #4737 lands? The design puts them in the child port [S18]; the maintainer's requests on #4424 (review 5270587330) do not mention them, so they come from the issue-4525 design review only.
- Q-G (cost rows): authorization to run 'bin/slice bench --update t_k_vnni_layout t_llama_unit' on the whole 3bda after the port, or record a deferral in the PR text?
- Q-H (8-lane build): run the -DAVX512=OFF configure+build of tron and t_amx_dispatch_dtype on the typed child to measure the 8-lane status (design section 8 limited check), given the CHILD header's unguarded intrinsics?
