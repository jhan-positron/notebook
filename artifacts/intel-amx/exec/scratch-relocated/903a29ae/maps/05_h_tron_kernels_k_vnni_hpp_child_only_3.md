# h/tron/kernels/k_vnni.hpp (CHILD-only, 310 lines at origin/jhan-amx-vnniK 30c4ac82cb) and its split into h/tron/tensor/k_vnni.hpp (constants, layout_on, index, k_vnni_view / k_vnni_tensor / detail::k_vnni_access, row-view aliases, typed store_row / load_row / store_block with their helpers) and h/tron/kernels/k_vnni.hpp (qk_group only), modelled on PARENT's h/tron/tensor/v_vnni.hpp and h/tron/tensor/kv_cache_fwd.hpp (origin/jhan-kv-typed-tensors c12df586b6). Includes the typed qk_vnni_128x4 boundary (amx_attn_iface.hpp, amx_attn.cpp, t_amx_dispatch_dtype.cpp fake) and the identifier inventory the rest of the tree uses from k_vnni::.

INVENTORY of CHILD h/tron/kernels/k_vnni.hpp (all in namespace tron::k_vnni):
- includes (32-40): <cstddef> <cstdint> <cstring> <immintrin.h> <type_traits>, common/attributes.hpp, common/numerics/bf16.hpp, common/numerics/fp16.hpp (fp16 only for qk_group). It contains AVX-512 intrinsics, no AMX intrinsics (header comment 7-8). No #if TRON_CHUNK_SIZE guard anywhere in the file.
- constants 44-75: PAGE_TOKENS_64, HEAD_SIZE_128, PAIR_2, DWORD_BYTES_4, LINE_BYTES_64, BLOCK_TOKENS_16, TOKEN_BLOCKS_4, STEP_DIMS_32, STEP_PAIRS_16, DIM_STEPS_4, ROW_ELEMS_32, ROW_DWORDS_16, PANEL_ELEMS_512, PANEL_BYTES_1024, PANEL_DWORDS_256, N_PANELS_16, FULL_BLOCK_0XFFFF (__mmask16), LANES_16, BF16_BITS_16 (int), HIGH_HALF_0XFFFF0000 (uint32_t), MAX_KV_MUL_16; static_asserts 76-84.
- layout_on<head_size> 91-97 (TRON_K_VNNI gate); constexpr index(token, dim) 101-107.
- detail::pair_base(bf16*/const bf16*, s, token) 112-123 (returns char*), detail::pair_row_offsets() 125-132.
- scatter_row(bf16* plane, token, const bf16* row) 138-146 (4 x _mm512_i32scatter_epi32, unaligned loads _mm512_loadu_si512).
- detail::transpose_16x16_epi32(__m512i (&r)[16]) 152-179.
- store_block(bf16* plane, c, __mmask16 present, const bf16* const rows[16]) 193-216 (loadu per row, storeu / mask_storeu_epi32).
- gather_row(const bf16* plane, token, bf16* row) 220-228 (4 x _mm512_i32gather_epi32, storeu).
- qk_group<kv_mul, q_scalar>(const bf16* plane, const q_scalar* q, uint64_t live, float* s, size_t s_stride) 246-308 (fp16 -> float recursion 255-261; maskz_loadu_epi32, dpbf16_ps / fmadd).
- Who includes the header at CHILD: h/tron/models/kv_cache.hpp:27, src/tron/kernels/amx_attn.cpp:14, t/t_amx_numerics.cpp:28, t/t_k_vnni_layout.cpp:25. self_attention.hpp, model.hpp, full.hpp, t_llama_unit.cpp get it transitively through kv_cache.hpp.

PARENT v_vnni.hpp facts mirrored (origin/jhan-kv-typed-tensors):
- v_vnni_view<T, Rows, Cols> final (103-154): class-body static_asserts (105-109), writable->const converting ctor guarded by requires (113-117), at() writable/const with TRON_ASSERT_LT (122-134), private explicit pointer ctor (142-144), private pair_base, T* data_; friends: owner, detail::v_vnni_access, other view specialisations (137-140).
- v_vnni_tensor<Rows, Cols> alignas(V_PLANE_ALIGNMENT_64) final (161-185): as_view() & / const& with TRON(this_lifetimebound), rvalue overloads deleted (180-181), private alignas(64) bf16 data_[Rows*Cols], no ctor.
- detail::v_vnni_access (187-206): static plane(view) and pair_base(view, token).
- row aliases const_v_row_view / v_row_view with fixed VIEW_ALIGNED_TRUE (208-213), helpers v_source_row / v_destination_row (217-227).
- Operation bodies under #if TRON_CHUNK_SIZE == 16 (229-408); class definitions outside the guard; header includes tron/simd/auto.hpp (23), which is where TRON_CHUNK_SIZE is #defined (auto.hpp:18/20).
- kv_cache_fwd.hpp forward-declares only the two class templates (33-36) plus VIEW_ALIGNED_TRUE / VIEW_DMA_FALSE (24-25) and the native_k_view aliases (42-53); amx_attn_iface.hpp:113 includes it and declares weights_times_v_128x4 with the view by value (234-238) and qk_rowmajor_128x4 with const_native_k_view (222-225). No v_vnni_row, no expr base anywhere at PARENT; t_llama_unit.cpp:422-423 asserts STATIC_REQUIRE_FALSE(matrix_indexes_rows<...>).
- 8 lanes: the V classes are complete at 8 lanes (static_assert Cols % chunk_size == 0 holds for 128 at chunk 8); the operations do not exist; t_amx_dispatch_dtype.cpp:195 defines the fake with the view type unconditionally.

## textual_conflicts
- h/tron/kernels/k_vnni.hpp whole file (CHILD 1-310): No merge conflict: PARENT does not touch this file (git diff origin/jhan-amx-vnniK -- h/tron/kernels/k_vnni.hpp in the worktree is empty). The split is an adaptation commit after the merge: move lines 42-228 (constants, layout_on, index, detail helpers, scatter_row, store_block, gather_row) into h/tron/tensor/k_vnni.hpp as typed operations, keep lines 230-308 (qk_group) plus MAX_KV_MUL_16 here with the typed view parameter.
- src/tron/kernels/amx_attn.cpp 14-20 in the worktree (<<<<<<< HEAD '#include "tron/kernels/k_vnni.hpp"' vs PARENT's kv_cache_fwd.hpp, v_vnni.hpp, view.hpp): Keep PARENT's three includes and add '#include "tron/tensor/k_vnni.hpp"' in place of the CHILD kernel-header include. amx_attn.cpp uses only the mapping constants (k_vnni::BLOCK_TOKENS_16, PANEL_ELEMS_512, TOKEN_BLOCKS_4, PAGE_TOKENS_64, HEAD_SIZE_128, STEP_DIMS_32, STEP_PAIRS_16 at CHILD 214-223) and never qk_group, so the kernel header is not needed there.
- src/tron/kernels/amx_attn.cpp CHILD 195-261 (qk_vnni_128x4 definition) adjacent to PARENT 215-223 (typed weights_times_v_128x4); the worktree showed markers at 219/295/298 on one read and none on a later read, so another process is editing this file: Change the definition to 'void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page, const bf16* q_rows, float* s, size_t s_stride_floats) noexcept', add as first statement 'const bf16* const k_vnni_plane = detail::k_vnni_access::plane(k_page);' (the same pattern as PARENT 223 'detail::v_vnni_access::plane(v_page)'), and leave lines 205-260 of the body unchanged so the tile loads and scores stay bit-identical.
- t/t_amx_dispatch_dtype.cpp CHILD 196 fake 'void qk_vnni_128x4(const bf16*, const bf16*, float* output, size_t stride)' next to PARENT 188-201 typed fakes; include block CHILD 38-47 vs PARENT 39-47: Retype the fake to take k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> by value (a definition needs the complete type, so add '#include "tron/tensor/k_vnni.hpp"' next to PARENT's '#include "tron/tensor/v_vnni.hpp"' at line 46). Keep PARENT's typed qk_rowmajor_128x4 and weights_times_v_128x4 fakes.
- h/tron/kernels/amx_attn_iface.hpp CHILD 243-254 (qk_vnni_128x4 declaration, raw pointer) vs PARENT 109-113 (kv_cache_fwd.hpp include) and 216-238 (typed declarations): Git merges this automatically (different hunks). Then change the declaration to the typed view (see proposed_code). PARENT already includes tron/tensor/kv_cache_fwd.hpp at 113, so no new include is needed and the header stays intrinsics-free.
- h/tron/models/self_attention.hpp include block 21-28 (identical in both PRs); call sites CHILD 1436-1439 and 1632-1641: Not a textual conflict in the include block, but after the split self_attention.hpp must add '#include "tron/kernels/k_vnni.hpp"' (design: 'self_attention.hpp includes the kernel header directly for qk_group'); today qk_group arrives transitively through kv_cache.hpp:27, which the port changes to the tensor header.

## semantic_changes
- [MUST] h/tron/tensor/k_vnni.hpp (new) @ whole file
  CHANGE: Create the K tensor header holding, in namespace tron::k_vnni, the constants (CHILD 44-84 verbatim), layout_on (86-97) and index (99-107); in namespace tron the class templates k_vnni_view<T, Rows, Cols> and k_vnni_tensor<Rows, Cols>, detail::k_vnni_access, the row-view aliases and k_source_row / k_destination_row helpers; and, under #if TRON_CHUNK_SIZE == 16, the helpers pair_base / pair_row_offsets / transpose_16x16_epi32 (CHILD 109-133, 148-180 verbatim) and the typed store_row / load_row / store_block whose bodies are CHILD 140-145, 222-227 and 198-215 verbatim after one 'plane = detail::k_vnni_access::plane(view)' line.
  WHY: Design: 'Define k_vnni_tensor, k_vnni_view ... in h/tron/tensor/k_vnni.hpp. Move mapping constants, k_vnni::layout_on<head_size>, and the existing constexpr free function k_vnni::index there. Keep the function spelling for the independent index checks. Define the typed K store_row, load_row, store_block ... and detail::k_vnni_access in h/tron/tensor/k_vnni.hpp. Move their pair_base, pair_row_offsets, and transpose_16x16_epi32 helpers with them.' Keeping the bodies verbatim is what guarantees goal (d), bit-identical plane bytes.
  EVIDENCE: design-child-section.txt paragraph 'Define k_vnni_tensor...'; PARENT v_vnni.hpp 64-227 and 229-408 as the model; CHILD k_vnni.hpp line ranges listed.
- [MUST] h/tron/tensor/k_vnni.hpp (new) @ include list
  CHANGE: Include "tron/simd/auto.hpp" (plus <concepts>, <cstddef>, <cstdint>, <immintrin.h>, <type_traits>, common/assert.hpp, common/attributes.hpp, common/numerics/bf16.hpp, tron/tensor/kv_cache_fwd.hpp, tron/tensor/seq.hpp, tron/tensor/view.hpp). Do not include common/numerics/fp16.hpp (only qk_group needs fp16).
  WHY: Compile necessity: TRON_CHUNK_SIZE is #defined only in h/tron/simd/auto.hpp (18/20). Without that include '#if TRON_CHUNK_SIZE == 16' is '#if 0 == 16' and the typed operations silently vanish; the errors then appear in kv_cache.hpp callers. PARENT's v_vnni.hpp includes auto.hpp for the same reason (23). common/assert.hpp is needed for TRON_ASSERT_LT in at(); seq.hpp/view.hpp for the row aliases.
  EVIDENCE: origin/jhan-kv-typed-tensors:h/tron/simd/auto.hpp:18,20,86; v_vnni.hpp:14-27; common/assert.hpp:80 (TRON_ASSERT_LT).
- [MUST] h/tron/tensor/k_vnni.hpp (new) @ k_vnni_view / k_vnni_tensor class bodies
  CHANGE: Pin the shape with class-body static_asserts 'Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128' and the element with a k_vnni_element concept (bf16 or const bf16). No requires-clause on the class templates. Define both classes outside the #if TRON_CHUNK_SIZE == 16 guard; the owner is alignas(64) with one private 'alignas(64) bf16 data_[Rows * Cols]', no constructors, lvalue-only as_view() with the && overloads deleted, writable-to-const converting constructor only, private explicit pointer constructor, no data() and no operator[].
  WHY: Design: 'Put K shape and element constraints in class-body static_assert statements too. std::conditional_t must be able to name the unselected packed specialization for native geometries. A rejecting class-template constraint would fail before selection.' Naming k_vnni_tensor<64, 64> inside std::conditional_t does not complete it, so the static_assert never fires for native geometries; a constrained template-id would be ill-formed when named. 'Keep K class definitions complete in both vector widths for unconditional fake definitions' (the t_amx_dispatch_dtype.cpp fake takes the view by value). The 64x128 pin matches the hard-coded TOKEN_BLOCKS_4 / DIM_STEPS_4 arithmetic of index(), scatter and gather (CHILD 101-107, 141, 223) and 'Keep the existing 64-token by 128-dimension kernel limit'. PARENT decision (2): no public pointer (v_vnni.hpp 99-102, 142-144); PARENT decision (1): no row type / operator[] (t_llama_unit.cpp:422-423).
  EVIDENCE: design-child-section.txt 'Child storage and access' paragraph; PARENT v_vnni.hpp:103-185; PARENT t_llama_unit.cpp:409-423; CHILD kv_cache.hpp:1522 (page_size = 64).
- [MUST] h/tron/tensor/kv_cache_fwd.hpp @ after the V declarations (PARENT 33-36)
  CHANGE: Add 'template <size_t Rows, size_t Cols> struct k_vnni_tensor; template <typename T, size_t Rows, size_t Cols> struct k_vnni_view;' with a comment pointing at Note [K VNNI storage] / h/tron/tensor/k_vnni.hpp. Do NOT add k_vnni_row.
  WHY: Design: 'Add unconstrained k_vnni_tensor, k_vnni_view ... forward declarations to h/tron/tensor/kv_cache_fwd.hpp, parallel to the V declarations. Then amx_attn_iface.hpp can declare qk_vnni_128x4(k_vnni_view<const bf16,PAGE_TOKENS_64,HEAD_SIZE_128>, ...) without intrinsics.' k_vnni_row is dropped by PARENT decision (1) (v_vnni_row removed in c12df586b6, 'do not add code which has no consumer').
  EVIDENCE: PARENT kv_cache_fwd.hpp:27-36; pr4557-body.md table row 'Follow the tensor / dtensor precedent ... Dropped by agreement'; design Q3 line 568 'If Q3 is rejected, remove the row expressions ... from both families.'
- [MUST] h/tron/kernels/k_vnni.hpp @ whole file after the split
  CHANGE: Keep only MAX_KV_MUL_16 and qk_group. New first parameter 'k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page'; first statement of the non-fp16 branch 'const bf16* const plane = tron::detail::k_vnni_access::plane(k_page);' then CHILD 265-306 unchanged; the fp16 recursion (CHILD 260) passes k_page through. Wrap the template in #if TRON_CHUNK_SIZE == 16. Includes: <cstddef> <cstdint> <cstring> <immintrin.h> <type_traits>, common/attributes.hpp, common/numerics/bf16.hpp, common/numerics/fp16.hpp, tron/tensor/k_vnni.hpp. Write 'tron::detail::k_vnni_access', not 'detail::', because inside namespace tron::k_vnni the name detail resolves to tron::k_vnni::detail.
  WHY: Design: 'h/tron/kernels/k_vnni.hpp includes that header and keeps only qk_group ... Pass k_vnni_view<const bf16,64,128> by value to qk_vnni_128x4 and the corresponding shape to qk_group. Retain score arithmetic in kernels.' qk_group is one of the two layout-specific K readers, so it may use the access struct (mirror of weights_times_v_128x4 using v_vnni_access at PARENT amx_attn.cpp:223). Goal (c): no raw K-plane pointer crosses the cache/kernel boundary; self_attention.hpp:1636-1639 will pass page.k_packed<geometry.kv>(slot, kv_head).
  EVIDENCE: CHILD k_vnni.hpp:246-308; CHILD self_attention.hpp:1632-1641; PARENT v_vnni.hpp:50-54 and amx_attn.cpp:215-223.
- [MUST] h/tron/kernels/amx_attn_iface.hpp @ CHILD 243-254
  CHANGE: Declare 'void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page, const bf16* q_rows, float* s, size_t s_stride_floats) noexcept;' and reword the comment: 'k_page = the page's K plane in the K VNNI layout (h/tron/tensor/k_vnni.hpp), passed as its typed view so a native K view, a packed V view or a bare pointer cannot be handed in by mistake.' Keep the header free of intrinsics (only kv_cache_fwd.hpp, already included at PARENT 113).
  WHY: Design item 'amx_attn_iface.hpp can declare qk_vnni_128x4(... k_vnni_view<const bf16,PAGE_TOKENS_64,HEAD_SIZE_128> ...) noexcept without intrinsics'. A by-value parameter of an incomplete class type is legal in a declaration; only the definition (amx_attn.cpp) and the callers (self_attention.hpp through kv_cache.hpp, t_amx_numerics.cpp) need the complete type, and they include the tensor header.
  EVIDENCE: PARENT amx_attn_iface.hpp:109-113, 222-225, 234-238; CHILD amx_attn_iface.hpp:251-254.
- [MUST] src/tron/kernels/amx_attn.cpp @ CHILD 14 and 201-204
  CHANGE: Include tron/tensor/k_vnni.hpp (not the kernel header); typed qk_vnni_128x4 signature; 'const bf16* const k_vnni_plane = detail::k_vnni_access::plane(k_page);' as the first statement; body 205-260 unchanged.
  WHY: Design: 'Include the full K tensor header in src/tron/kernels/amx_attn.cpp'. The body reads the plane in 1 KiB panels through the raw pointer exactly as before, so scores stay bit-identical (goal d).
  EVIDENCE: CHILD amx_attn.cpp:201-261; PARENT amx_attn.cpp:215-223 pattern.
- [MUST] t/t_amx_dispatch_dtype.cpp @ CHILD 196 and the include block
  CHANGE: Fake becomes 'void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>, const bf16*, float* output, size_t stride) noexcept { ++probe.qk_calls; std::fill_n(output, GROUP_HEADS_4 * stride, 0.0f); }'; add '#include "tron/tensor/k_vnni.hpp"'.
  WHY: Design: 'Include the full K tensor header in ... t/t_amx_dispatch_dtype.cpp'. The definition must match the new declaration, and a by-value class parameter in a definition needs the complete type. The class is complete at 8 lanes too (no chunk_size dependence in its static_asserts), which is what 'Keep K class definitions complete in both vector widths for unconditional fake definitions' requires.
  EVIDENCE: PARENT t_amx_dispatch_dtype.cpp:44-47, 188-201; CHILD 196-199.
- [MUST] h/tron/models/kv_cache.hpp @ CHILD 27 (include), 1651 at PARENT (fill_storage_slot), page K methods CHILD 1689-1748, copy_storage_slot CHILD 2099-2116
  CHANGE: Replace '#include "tron/kernels/k_vnni.hpp"' with '#include "tron/tensor/k_vnni.hpp"'. Callers inside kv_cache.hpp use the typed entry points: store_row(block.k.as_view(), i_page, src), load_row(std::as_const(block).k.as_view(), i_page, dst), store_block(block.k.as_view(), c, present, rows); page::k_packed<geometry>() returns 'kv_block<geometry>(slot, kv_head).k.as_view()' (const). In fill_storage_slot the range-for 'for (auto& value : block.k)' (PARENT 1651) does not compile for the owner, so the packed branch must take 'bf16* k = detail::k_vnni_access::plane(block.k.as_view())' in the same way PARENT does for V at 1654 (the documented fill_random exception).
  WHY: Design: 'The cache includes the K tensor header ... The cache drops its include of this kernel header.' Compile necessity for fill_storage_slot (owner has no begin/end). This item is owned by the kv_cache.hpp area; it is listed here because the header split decides the include and the k_vnni_access::plane entry point it needs.
  EVIDENCE: PARENT kv_cache.hpp:1645-1661 (v_vnni_access use), 1945-1956 (v_packed); CHILD kv_cache.hpp:1704-1706, 1729-1730, 1741-1743, 2107-2114.
- [MUST] h/tron/models/self_attention.hpp @ include block (line 21-28) and call sites CHILD 1436-1439, 1632-1641
  CHANGE: Add '#include "tron/kernels/k_vnni.hpp"' (after amx_attn_iface.hpp, with the comment 'qk_group, AVX-512 reader of the K VNNI layout'). Call 'amx_attn_h128g4::qk_vnni_128x4(pg.template k_packed<geometry.kv>(slot, kv_head), q_packed, &s_pages[0][0], page::page_size)' and 'k_vnni::qk_group<operation_kv_mul>(page.template k_packed<geometry.kv>(slot, kv_head), ...)'.
  WHY: Design: 'self_attention.hpp includes the kernel header directly for qk_group. Neither tensor header includes an attention kernel header.' Without the explicit include, qk_group disappears from self_attention.hpp once kv_cache.hpp stops including the kernel header.
  EVIDENCE: CHILD self_attention.hpp:21-28, 1436-1444, 1632-1641; CHILD kv_cache.hpp:27.
- [MUST] h/tron/tensor/k_vnni.hpp (new) @ typed operation signatures
  CHANGE: store_row(k_vnni_view<bf16, Rows, Cols> dst, size_t token, const_k_row_view<Cols, Aligned, Dma> src); load_row(k_vnni_view<const bf16, Rows, Cols> src, size_t token, k_row_view<Cols, Aligned, Dma> dst); store_block(k_vnni_view<bf16, Rows, Cols> dst, size_t c, __mmask16 present, const bf16* const rows[k_vnni::BLOCK_TOKENS_16]). Row aliases: 'template <size_t Cols, bool Aligned, bool Dma> using const_k_row_view = const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;' and k_row_view = view<...> likewise. Keep the unaligned vector instructions (loadu/storeu) of the CHILD bodies.
  WHY: Design table rows page::set_k_row / get_k_row: 'Use const_view<bf16,Aligned,Dma,seq<D>,sseq<1>> for save and view<bf16,Aligned,Dma,seq<D>,sseq<1>> for load. The boolean template arguments preserve the caller's alignment and DMA properties. Preserve the existing gather/scatter instructions. These K routines do not acquire V's stronger alignment requirement.' Row page::set_k_block: 'Call store_block(writable_k_view, block, mask, rows). Preserve const bf16* const rows[BLOCK_TOKENS_16] ... These source-row pointers do not expose packed storage.' Bodies stay verbatim so stored bytes are unchanged.
  EVIDENCE: design-child-section.txt table; CHILD k_vnni.hpp:138-146, 193-216, 220-228 (loadu/storeu/scatter/gather); PARENT seq.hpp:25 (sseq), view.hpp:115-125 and 360-373 (rank-1 view / const_view with 'data').
- [SHOULD] h/tron/tensor/k_vnni.hpp (new) @ namespace tron, before the classes
  CHANGE: Named constants 'inline constexpr size_t K_PLANE_ALIGNMENT_64 = 64;' (owner alignment) and 'inline constexpr size_t K_PLANE_BYTES_16384 = k_vnni::PAGE_TOKENS_64 * k_vnni::HEAD_SIZE_128 * sizeof(bf16);' with a static_assert that the owner has that size and alignment.
  WHY: PARENT decision (3): every PR-added literal gets a named constexpr whose name ends in its value; design: 'Require 64-byte alignment ... and a 16,384-byte owner for 64 tokens by 128 dimensions.' Mirrors V_PLANE_ALIGNMENT_64 (PARENT v_vnni.hpp:78).
  EVIDENCE: PARENT v_vnni.hpp:75-78; PARENT t_llama_unit.cpp:431-434 (size/alignment STATIC_REQUIREs for V).
- [SHOULD] h/tron/tensor/k_vnni.hpp (new) @ k_vnni_view
  CHANGE: Provide bounds-checked 'T& at(size_t token, size_t dim)' and the const overload returning 'const bf16&', implemented as data_[k_vnni::index(token, dim)] with TRON_ASSERT_LT on both indices.
  WHY: Consistency with the V view (PARENT v_vnni.hpp:122-134) and with the design's section-8 contract probes ('read-only writes, const-row mutation'), which are the matrix_at_writes probes at PARENT t_llama_unit.cpp:112-113 and 419-421; the K port mirrors them. Flagged as an open question because no production code reads single K elements (PARENT rule: no code without a consumer).
  EVIDENCE: PARENT v_vnni.hpp:119-134; PARENT t_llama_unit.cpp:112-113, 419-421; design section 8 'Typed function boundaries' row.
- [SHOULD] h/tron/tensor/k_vnni.hpp (new) @ row helpers
  CHANGE: Add 'k_source_row<Cols, Aligned = VIEW_ALIGNED_TRUE, Dma = VIEW_DMA_FALSE>(const bf16*)' and 'k_destination_row<...>(bf16*)' returning the row aliases, mirroring v_source_row / v_destination_row.
  WHY: Design: 'Construct read-only source views explicitly in model save paths, copy paths, and affected test callers. Template deduction does not use the conversion from a writable view or raw pointer to const_view.' Callers today pass raw pointers: model.hpp:2920 (kout.data), 2924 (conv[0]), full.hpp:2655 (dest), t_k_vnni_layout.cpp:401-459 and t_llama_unit.cpp (about 30 set_k_row/get_k_row calls with row.data()), t_amx_dispatch_dtype.cpp:101. A one-call helper keeps those edits to a wrap, as PARENT did for V at t_amx_dispatch_dtype.cpp:107.
  EVIDENCE: PARENT v_vnni.hpp:215-227; worktree t_amx_dispatch_dtype.cpp:105-107; CHILD model.hpp:2914-2941.
- [SHOULD] h/tron/tensor/k_vnni.hpp (new) and h/tron/kernels/k_vnni.hpp @ constant placement
  CHANGE: Keep all mapping constants, including BF16_BITS_16, HIGH_HALF_0XFFFF0000 and FULL_BLOCK_0XFFFF, in the tensor header's tron::k_vnni namespace; only MAX_KV_MUL_16 moves with qk_group.
  WHY: t_k_vnni_layout.cpp:35-40 uses k_vnni::BF16_BITS_16 and FULL_BLOCK_0XFFFF for its own helpers and for store_block; amx_attn.cpp:214-223 uses seven constants and must not depend on the kernel header. Keeping the block in one place also keeps the PR 4737 hunk (which inserts PANEL_ROWS_4 / BLOCKS_PER_PAGE_MASK_0XF / block_bit / offset_bit into that block) re-applicable.
  EVIDENCE: CHILD t_k_vnni_layout.cpp:35-40; CHILD amx_attn.cpp:214-223; git diff origin/jhan-amx-vnniK origin/jhan-amx-vnniK-i4500 -- h/tron/kernels/k_vnni.hpp.
- [SHOULD] t/t_k_vnni_layout.cpp @ 25 (include), 67-70 (plane_and_rows), every scatter_row / gather_row / store_block / qk_group call (113, 129, 139, 199, 201, 214, 226, 228, 232, 291, 306, 308)
  CHANGE: Include both tron/tensor/k_vnni.hpp and tron/kernels/k_vnni.hpp. Replace the raw 'bf16 plane[8192]' with 'std::make_unique<k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>()' owners; fill poison with 64 typed store_row calls of a poison row; for the index-anchor comparisons memcpy the owner's bytes into a 'bf16 bytes[8192]' buffer and index that with k_vnni::index; compare two owners with memcmp of the owners (trivially copyable). Do not use detail::k_vnni_access in tests.
  WHY: Design: 'Adapt t_k_vnni_layout to actual aligned owners. Fill poison with 64 typed row saves. Copy the trivially copyable owner's bytes to a test buffer for physical-layout comparisons. Preserve independent index anchors and avoid the internal friend helpers.' The raw-pointer entry points disappear with the split.
  EVIDENCE: CHILD t_k_vnni_layout.cpp:67-70, 105-113, 115-124, 190-202; design child section.
- [SHOULD] t/t_amx_numerics.cpp @ 28 (include), 210-219, 230-231
  CHANGE: Include tron/tensor/k_vnni.hpp (not the kernel header; the file never calls qk_group). Replace 'struct vnni_plane { bf16 v[...] }' with a k_vnni_tensor<64,128> owner, store with 'store_row(owner->as_view(), tok, k_source_row<HEAD_SIZE_128>(in->k + tok * HEAD_SIZE_128))' and call 'qk_vnni_128x4(std::as_const(*owner).as_view(), q_rows, ...)'.
  WHY: Compile necessity after the signature change; design 'Include the full K tensor header in ... callers constructing views'. Mirrors PARENT's own change for V at t_amx_numerics.cpp:221-227.
  EVIDENCE: CHILD t_amx_numerics.cpp:210-231; grep shows 0 qk_group uses in that file; PARENT t_amx_numerics.cpp:221-227.
- [SHOULD] t/t_llama_unit.cpp @ next to PARENT 94-118 (probes) and 386-439 (STATIC_REQUIREs)
  CHANGE: Add 'amx_qk_vnni_accepts<K>' probe calling amx_attn_h128g4::qk_vnni_128x4, and assert: accepts k_vnni_view<const bf16,64,128> and the writable view; rejects const bf16*, bf16*, v_vnni_view, const_native_k_view; qk_rowmajor_128x4 and weights_times_v_128x4 reject the packed K view; no pointer construction, no default construction, writable-to-const only, no view of a temporary owner, at() writes only through the writable view, no operator[]; owner trivially default-constructible / copyable / destructible, sizeof == K_PLANE_BYTES_16384, alignof == K_PLANE_ALIGNMENT_64; kv_block size unchanged. Include tron/tensor/k_vnni.hpp directly.
  WHY: Design section 8 'Typed function boundaries' row and PARENT decision 'A bare pointer or the other plane's view is a compile error (tested with STATIC_REQUIRE)'. These checks are the acceptance evidence for goal (c).
  EVIDENCE: PARENT t_llama_unit.cpp:94-118, 386-439; pr4557-body.md row 'No bare bf16_t* ...'.
- [SHOULD] h/tron/models/kv_cache.hpp, h/tron/kernels/amx_attn_iface.hpp, src/tron/kernels/amx_attn.cpp, t/t_amx_numerics.cpp @ comments: CHILD kv_cache.hpp:657 ('tron/kernels/k_vnni.hpp'), 677/680/702 (k_vnni::store_block / scatter_row / gather_row), 686 (page::k_vnni_plane); amx_attn_iface.hpp:223, 249-250; amx_attn.cpp:212; t_amx_numerics.cpp:195-196
  CHANGE: Point at h/tron/tensor/k_vnni.hpp for the layout, name store_row / load_row / store_block and page::k_packed in place of scatter_row / gather_row / k_vnni_plane. Plain English, one claim per sentence.
  WHY: PARENT decision (4) and accuracy after the rename; stale names would send readers to a header that no longer defines them.
  EVIDENCE: CHILD kv_cache.hpp:653-710; amx_attn_iface.hpp:215-254; amx_attn.cpp:210-213.
- [COULD] h/tron/tensor/k_vnni.hpp (new) @ after load_row
  CHANGE: A K 'copy_token(k_vnni_view<bf16,R,C> dst, size_t dst_token, k_vnni_view<const bf16,R,C> src, size_t src_token)' doing 4 gathers followed by 4 scatters without a scratch row. Its only consumer would be copy_storage_slot's partial-range path (CHILD kv_cache.hpp:2109-2115). The alternative with no new function is to keep that path as load_row into a 64-byte-aligned scratch row then store_row.
  WHY: Design says 'Use typed K token copies' but also 'Add no K plane-copy helper', and PARENT decision (1) forbids code without a consumer; both forms are typed and produce the same bytes (gather then scatter of the same 64 dwords). Leave the choice to the kv_cache.hpp area.
  EVIDENCE: CHILD kv_cache.hpp:2099-2116; PARENT v_vnni.hpp:352-406 (V copy_token exists because V pairs need merging; K lanes do not).

## proposed_code
// ---------- h/tron/tensor/kv_cache_fwd.hpp : add after the V declarations (PARENT 33-36)
// Packed K types (TRON_K_VNNI, Note [K VNNI storage] in kv_cache.hpp):
// - k_vnni_tensor holds one bf16 array of [Rows tokens * Cols dimensions] in the
//   K VNNI layout of h/tron/tensor/k_vnni.hpp, at an address that is a multiple
//   of 64 bytes.
// - k_vnni_view refers to that array and computes where each (token, dim) is.
// T = bf16 allows writes, and T = const bf16 is read-only.
template <size_t Rows, size_t Cols>
struct k_vnni_tensor;
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view;

// ---------- h/tron/tensor/k_vnni.hpp (new)
#pragma once
// (header comment: CHILD h/tron/kernels/k_vnni.hpp 2-30, reworded: types and
//  typed row/block operations; qk_group now lives in h/tron/kernels/k_vnni.hpp)
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <immintrin.h>
#include <type_traits>

#include "common/assert.hpp"
#include "common/attributes.hpp"
#include "common/numerics/bf16.hpp"
#include "tron/simd/auto.hpp"  // defines TRON_CHUNK_SIZE: the 16-lane guard below needs it
#include "tron/tensor/kv_cache_fwd.hpp"
#include "tron/tensor/seq.hpp"
#include "tron/tensor/view.hpp"

namespace tron {

namespace k_vnni {
// CHILD k_vnni.hpp 44-84 verbatim: PAGE_TOKENS_64 ... MAX_KV_MUL_16 excluded
// (it moves with qk_group), the three static_asserts.
// CHILD 86-97 verbatim: layout_on<head_size> under #ifdef TRON_K_VNNI.
// CHILD 99-107 verbatim: constexpr size_t index(size_t token, size_t dim) noexcept.
}  // namespace k_vnni

namespace detail {
// The one route from a packed K view to its plane address: the typed operations
// below, the AMX kernel qk_vnni_128x4 and the AVX-512 reader k_vnni::qk_group.
struct k_vnni_access;
}  // namespace detail

// Byte alignment of one K VNNI plane: every pair row is one 64-byte line, and
// the AMX QK kernel reads the plane in 64-byte tile rows.
inline constexpr size_t K_PLANE_ALIGNMENT_64 = 64;
// One plane: 64 tokens x 128 dimensions of bf16.
inline constexpr size_t K_PLANE_BYTES_16384 =
    k_vnni::PAGE_TOKENS_64 * k_vnni::HEAD_SIZE_128 * sizeof(bf16);
static_assert(K_PLANE_BYTES_16384 == 16384, "the constant's name states its value");

template <typename T>
concept k_vnni_element = std::same_as<T, bf16> || std::same_as<T, const bf16>;

// A K plane in the VNNI layout, [Rows tokens * Cols dimensions]. One element is
// reached through at(token, dim). Whole token rows move through store_row,
// load_row and store_block below. Views come only from an owner
// (k_vnni_tensor::as_view). A writable view (bf16) converts to a read-only one
// (const bf16), never the reverse. There is no public pointer constructor, no
// data() accessor, no operator[] and no pointer conversion.
template <typename T, size_t Rows, size_t Cols>
struct k_vnni_view final {
  static_assert(k_vnni_element<T>, "a packed K plane holds bf16 or const bf16");
  static_assert(Rows == k_vnni::PAGE_TOKENS_64 && Cols == k_vnni::HEAD_SIZE_128,
      "the K VNNI layout exists for 64-token pages of 128-dimension heads only");

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

// Owns one K VNNI plane: exactly one 64-byte-aligned bf16 array, no separate
// allocation and no initialization (the cache's DMA allocation creates the
// kv_blocks that hold it; see Note [KV block lifetime] in kv_cache.hpp).
// Trivial to construct, copy and destroy; copying an owner copies the plane
// (copy_storage_slot's whole-page copy is `dst_block.k = src_block.k`).
// as_view() on a temporary is deleted: a view must not outlive its owner.
template <size_t Rows, size_t Cols>
struct alignas(K_PLANE_ALIGNMENT_64) k_vnni_tensor final {
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
  alignas(K_PLANE_ALIGNMENT_64) bf16 data_[Rows * Cols];
};
static_assert(sizeof(k_vnni_tensor<k_vnni::PAGE_TOKENS_64, k_vnni::HEAD_SIZE_128>) ==
                  K_PLANE_BYTES_16384 &&
              alignof(k_vnni_tensor<k_vnni::PAGE_TOKENS_64, k_vnni::HEAD_SIZE_128>) ==
                  K_PLANE_ALIGNMENT_64,
    "the owner is the plane: same bytes as the row-major K plane, 64-byte aligned");

namespace detail {
struct k_vnni_access final {
  // The plane's first element: panel (step 0, block 0), pair row 0, token 0.
  template <typename T, size_t Rows, size_t Cols>
  TRON(nodiscard, inline, pure)
  static T* plane(k_vnni_view<T, Rows, Cols> v) noexcept {
    return v.data_;
  }
};
}  // namespace detail

// Contiguous transfer rows for page::set_k_row / get_k_row, not packed storage.
// Unlike the V rows, the caller's alignment and DMA flags are kept: the K store
// and load use unaligned vector loads and stores.
template <size_t Cols, bool Aligned, bool Dma>
using const_k_row_view = const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;
template <size_t Cols, bool Aligned, bool Dma>
using k_row_view = view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>;

template <size_t Cols, bool Aligned = VIEW_ALIGNED_TRUE, bool Dma = VIEW_DMA_FALSE>
TRON(nodiscard, inline)
const_k_row_view<Cols, Aligned, Dma> k_source_row(const bf16* row) noexcept {
  return const_k_row_view<Cols, Aligned, Dma>{row};
}
template <size_t Cols, bool Aligned = VIEW_ALIGNED_TRUE, bool Dma = VIEW_DMA_FALSE>
TRON(nodiscard, inline)
k_row_view<Cols, Aligned, Dma> k_destination_row(bf16* row) noexcept {
  return k_row_view<Cols, Aligned, Dma>{row};
}

#if TRON_CHUNK_SIZE == 16

namespace k_vnni::detail {
// CHILD 112-123 pair_base (both overloads), 125-132 pair_row_offsets,
// 152-179 transpose_16x16_epi32: verbatim.
}  // namespace k_vnni::detail

// Store one token's 128-dimension K row into the plane: 4 scatters of 16 dwords
// (CHILD scatter_row). Only this token's 64 pair slots are written.
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void store_row(k_vnni_view<bf16, Rows, Cols> dst,
    size_t token,
    const_k_row_view<Cols, Aligned, Dma> src) noexcept {
  bf16* const plane = detail::k_vnni_access::plane(dst);
  const bf16* const row = src.data;
  // CHILD 140-145 verbatim (pair_row_offsets, loadu, i32scatter per step).
}

// Load one token's 128-dimension K row out of the plane: 4 gathers of 16 dwords
// (CHILD gather_row), the inverse of store_row.
template <size_t Rows, size_t Cols, bool Aligned, bool Dma>
TRON(inline)
void load_row(k_vnni_view<const bf16, Rows, Cols> src,
    size_t token,
    k_row_view<Cols, Aligned, Dma> dst) noexcept {
  const bf16* const plane = detail::k_vnni_access::plane(src);
  bf16* const row = dst.data;
  // CHILD 222-227 verbatim (pair_row_offsets, i32gather, storeu per step).
}

// Store the K rows of up to 16 tokens of token block c with full-line stores
// (CHILD store_block). rows[t] points at the 128 bf16 of token c * 16 + t, or is
// null for an absent token (bit t of `present` clear). Row pointers are plain
// source rows; they do not expose packed storage.
template <size_t Rows, size_t Cols>
TRON(inline)
void store_block(k_vnni_view<bf16, Rows, Cols> dst,
    size_t c,
    __mmask16 present,
    const bf16* const rows[k_vnni::BLOCK_TOKENS_16]) noexcept {
  bf16* const plane = detail::k_vnni_access::plane(dst);
  // CHILD 198-215 verbatim (transpose, storeu / mask_storeu_epi32 per pair row).
}

#endif  // TRON_CHUNK_SIZE == 16

}  // namespace tron

// ---------- h/tron/kernels/k_vnni.hpp (after the split)
#pragma once
// AVX-512 QK reader of the K VNNI layout (h/tron/tensor/k_vnni.hpp) for partial
// pages, hosts without AMX and the kill switch TRON_AMX_DISABLE=1. No AMX
// instruction here, so any translation unit may include it.
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <immintrin.h>
#include <type_traits>

#include "common/attributes.hpp"
#include "common/numerics/bf16.hpp"
#include "common/numerics/fp16.hpp"
#include "tron/tensor/k_vnni.hpp"

namespace tron::k_vnni {

// One accumulator register per query head of the group.
inline constexpr size_t MAX_KV_MUL_16 = 16;

#if TRON_CHUNK_SIZE == 16
// (CHILD 230-245 comment, reworded for the typed argument)
template <size_t kv_mul, typename q_scalar>
TRON(inline)
void qk_group(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const q_scalar* q,
    uint64_t live,
    float* s,
    size_t s_stride) noexcept {
  static_assert(kv_mul >= 1 && kv_mul <= MAX_KV_MUL_16, "one accumulator register per head");
  if constexpr (std::is_same_v<q_scalar, fp16>) {
    alignas(64) float qf[kv_mul * HEAD_SIZE_128];
    for (size_t i = 0; i < kv_mul * HEAD_SIZE_128; ++i) {
      qf[i] = float(q[i]);
    }
    qk_group<kv_mul, float>(k_page, qf, live, s, s_stride);
    return;
  } else {
    // Inside tron::k_vnni the name `detail` is tron::k_vnni::detail, so qualify.
    const bf16* const plane = tron::detail::k_vnni_access::plane(k_page);
    // CHILD 263-306 verbatim.
  }
}
#endif  // TRON_CHUNK_SIZE == 16

}  // namespace tron::k_vnni

// ---------- h/tron/kernels/amx_attn_iface.hpp (replaces CHILD 243-254)
// Dense QK for one page whose K is stored in the K VNNI layout (Note [K VNNI
// storage] in kv_cache.hpp). Computes S = Q . K^T; the padded Q rows are the A
// operand and the page's 16 K panels are the B operand. Writes
// s[4][s_stride_floats] fp32, all 64 token columns, UNSCALED (Note [Tile stores
// write 16 rows]). k_page = the page's K plane as its typed view
// (h/tron/tensor/k_vnni.hpp), so a native K view, a packed V view or a bare
// pointer cannot be handed in by mistake. q_rows = the pack_q_rows_128x4 output.
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const bf16* q_rows,
    float* s,
    size_t s_stride_floats) noexcept;

// ---------- src/tron/kernels/amx_attn.cpp (replaces CHILD 201-204; body 205-260 unchanged)
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> k_page,
    const bf16* q_rows,
    float* s,
    size_t s_stride_floats) noexcept {
  // One of the two layout-specific readers allowed to take the plane address.
  const bf16* const k_vnni_plane = detail::k_vnni_access::plane(k_page);
  ... // CHILD 205-260 verbatim

// ---------- t/t_amx_dispatch_dtype.cpp (replaces CHILD 196-199)
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const bf16*,
    float* output,
    size_t stride) noexcept {
  ++probe.qk_calls;
  std::fill_n(output, GROUP_HEADS_4 * stride, 0.0f);
}

// ---------- t/t_llama_unit.cpp probes (next to PARENT 97-105)
template <typename K>
constexpr bool amx_qk_vnni_accepts = requires(K k, const bf16* q, float* s) {
  amx_attn_h128g4::qk_vnni_128x4(k, q, s, size_t{0});
};
// and in the case at PARENT 386-439:
using k_packed_t = k_vnni_view<const bf16, amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
using k_packed_mut_t = k_vnni_view<bf16, amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
using k_owner_t = k_vnni_tensor<amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
STATIC_REQUIRE(amx_qk_vnni_accepts<k_packed_t>);
STATIC_REQUIRE(amx_qk_vnni_accepts<k_packed_mut_t>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<const bf16*>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<bf16*>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<v_plane_t>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<k_plane_t>);   // native K view
STATIC_REQUIRE_FALSE(amx_qk_accepts<k_packed_t>);
STATIC_REQUIRE_FALSE(amx_pv_accepts<k_packed_t>);
STATIC_REQUIRE_FALSE(std::is_constructible_v<k_packed_mut_t, bf16*>);
STATIC_REQUIRE_FALSE(std::is_default_constructible_v<k_packed_t>);
STATIC_REQUIRE(std::is_convertible_v<k_packed_mut_t, k_packed_t>);
STATIC_REQUIRE_FALSE(std::is_convertible_v<k_packed_t, k_packed_mut_t>);
STATIC_REQUIRE_FALSE(owner_views_temporary<k_owner_t>);
STATIC_REQUIRE(matrix_at_writes<k_packed_mut_t>);
STATIC_REQUIRE_FALSE(matrix_at_writes<k_packed_t>);
STATIC_REQUIRE_FALSE(matrix_indexes_rows<k_packed_t>);
STATIC_REQUIRE(std::is_trivially_default_constructible_v<k_owner_t> && std::is_trivially_copyable_v<k_owner_t> && std::is_trivially_destructible_v<k_owner_t>);
STATIC_REQUIRE(sizeof(k_owner_t) == K_PLANE_BYTES_16384 && alignof(k_owner_t) == K_PLANE_ALIGNMENT_64);

// ---------- include graph after the split
// kv_cache_fwd.hpp  <- tensor/k_vnni.hpp, tensor/v_vnni.hpp, kernels/amx_attn_iface.hpp
// tensor/k_vnni.hpp <- models/kv_cache.hpp (replaces kernels/k_vnni.hpp at CHILD:27),
//                      kernels/k_vnni.hpp, src/tron/kernels/amx_attn.cpp,
//                      t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp,
//                      t/t_k_vnni_layout.cpp, t/t_llama_unit.cpp
// kernels/k_vnni.hpp (qk_group) <- models/self_attention.hpp (new direct include),
//                      t/t_k_vnni_layout.cpp
// model.hpp, full.hpp reach k_vnni::layout_on / BLOCK_TOKENS_16 / __mmask16 through kv_cache.hpp.
// Neither tensor header includes a kernel header; amx_attn_iface.hpp includes only kv_cache_fwd.hpp.

## design_contradictions
- Design table 'Child storage and access' writes 'using native_k_storage = bf16s[page_size][head_size / chunk_size];' but PARENT changed kv_block::k to 'alignas(kv_block_alignment) bf16 k[page_size * head_size];' (PARENT kv_cache.hpp:2452; diff 996f58ec82..origin/jhan-kv-typed-tensors line '-bf16s k[page_size][head_size / chunk_size]' / '+bf16 k[page_size * head_size]'), with k_view()/k_at() built on it (2472-2495) and fill_storage_slot iterating it as a flat range (1651). The port must use 'using native_k_storage = bf16[page_size * head_size];' as the array branch of std::conditional_t.
- Design text (Q3, lines 528/568 of design-new-tensor-type.txt and the child section) still specifies k_vnni_row and 'logical expression reads'. PARENT commit c12df586b6 removed v_vnni_row and the expr base; pr4557-body.md records 'Dropped by agreement' and PARENT t_llama_unit.cpp:422-423 asserts STATIC_REQUIRE_FALSE(matrix_indexes_rows<...>). Per the given override, the child adds no k_vnni_row, no operator[], no expression base, and no forward declaration of a row type in kv_cache_fwd.hpp.
- Design says 'Guard packed operation bodies at 16 lanes'. CHILD's h/tron/kernels/k_vnni.hpp has no TRON_CHUNK_SIZE guard at all (the only 8-lane rejection is kv_cache.hpp:35-39, which fires only when TRON_K_VNNI is defined), so today the AVX-512 inline functions are parsed in every build. Adding the guard is a behaviour-neutral change at 16 lanes and follows PARENT v_vnni.hpp:229/408; it is not a contradiction with CHILD's intent, but the implementer should know the guard is new.
- Design table row 'hardware::page_info K callback: Add the child's scratch parameter' is already satisfied at CHILD (full.hpp:2644-2661 k_head_fn takes bf16* dest and calls page::get_k_row); after the port that lambda wraps dest with k_destination_row<hw_kv.head_size>(dest). No new parameter is needed.
- Ben's sketch (ben-sketch-5765866077.md) proposes one header h/tron/tensor/vnni.hpp with a layout-parameterised vnni_view<T, Layout> and std::span row arguments. PARENT chose separate v_ types in h/tron/tensor/v_vnni.hpp with const_view/view row arguments (v_vnni.hpp:208-213), and the design records 'The separate K/V files and the v_ prefix are this design's choice'. The K port follows PARENT (k_vnni_view<T, Rows, Cols>, const_k_row_view), not the sketch.

## risks
- If h/tron/tensor/k_vnni.hpp omits '#include "tron/simd/auto.hpp"', TRON_CHUNK_SIZE is undefined there and '#if TRON_CHUNK_SIZE == 16' compiles the operations away silently; the first error appears in kv_cache.hpp's page methods ('no matching function for call to store_row'). auto.hpp:18/20 is the only definition.
- Name lookup trap: inside namespace tron::k_vnni (the kernel header) 'detail::k_vnni_access' resolves to tron::k_vnni::detail (CHILD's helper namespace, 109-133) and fails; write tron::detail::k_vnni_access. Inside the typed operations in namespace tron, the helpers must be written k_vnni::detail::pair_base / pair_row_offsets / transpose_16x16_epi32.
- load_row becomes an overload set in namespace tron: the V overload (PARENT v_vnni.hpp:314-319) and the K overload differ in the first parameter's class template, so deduction picks one; a wrong-plane argument yields 'no matching function', which is the intended compile error. Both must sit under the same #if TRON_CHUNK_SIZE == 16 guard.
- PR #4737 (origin/jhan-amx-vnniK-i4500 bb32a80774) adds to h/tron/kernels/k_vnni.hpp raw-pointer helpers row_ptr(bf16*/const bf16*, token), block_to_vnni(bf16*, c), block_to_rows(bf16*, c), constants PANEL_ROWS_4, BLOCKS_PER_PAGE_MASK_0XF, block_bit(), offset_bit(), ROW_ALIGNED_TRUE / ROW_DMA_FALSE, used from kv_cache.hpp (24 references), self_attention.hpp (7) and t_k_vnni_layout.cpp (12). After the split its k_vnni.hpp hunk conflicts textually with a rewritten file, and its helpers must be re-expressed as typed operations (row_ptr returning k_row_view / const_k_row_view from a k_vnni_view) to keep goal (c). The later merge stays possible but is a re-port, not a clean merge. Keeping the constants block (CHILD 44-84) verbatim in the tensor header minimises that hunk.
- The scratch worktree is being modified concurrently: conflict markers in src/tron/kernels/amx_attn.cpp were at lines 219/295/298 on one read and absent on the next, and h/tron/models/common.hpp showed markers in grep but not in sed. Every citation above is to the fetched refs (origin/jhan-amx-vnniK, origin/jhan-kv-typed-tensors), not to the worktree text.
- 8-lane builds: no CI lane that compiles at TRON_CHUNK_SIZE == 8 was identified (grep of CMakeLists.txt, src/tron/CMakeLists.txt, workflows found only the -mavx2 default flags at src/tron/CMakeLists.txt:268/315 and the AMX-only flags at 222). Insufficient data on whether such a lane exists; the design requires the guard regardless, and the class definitions must stay complete at 8 lanes for the t_amx_dispatch_dtype.cpp fake.
- store_block keeps '__mmask16 present' and FULL_BLOCK_0XFFFF (typedef from <immintrin.h>, available at both widths), so model.hpp:2899-2941 keeps building the mask; model.hpp sees the type through kv_cache.hpp -> tensor/k_vnni.hpp -> <immintrin.h>.
- Every caller that today passes a raw row pointer to page::set_k_row / get_k_row (model.hpp:2920, 2924; full.hpp:2655; t_amx_dispatch_dtype.cpp:101; t_k_vnni_layout.cpp:401-459; about 30 call sites in t_llama_unit.cpp, e.g. 362-366, 392-407, 579-607, 1469-1490, 2247-2333, 2724) must wrap the pointer (k_source_row / k_destination_row) because a raw pointer does not deduce into const_view; a missed site is a compile error, not a silent change.
- Bit-identity (goal d) rests on copying the CHILD bodies verbatim after a single plane-pointer extraction; any 'cleanup' of the scatter/gather/transposes while moving them would need the t_k_vnni_layout block-save and t_amx_numerics bit-identity cases rerun on 3bda with TRON_K_VNNI=ON.

## open_questions
- at(token, dim) on k_vnni_view: include it (mirrors V and lets the section-8 contract probes matrix_at_writes / const-row checks apply to K) or omit it under the PARENT rule 'do not add code which has no consumer' (no production code reads a single K element; the tests use index() against memcpy'd bytes to stay independent)? Recommendation: include, with the t_llama_unit probes as the named consumer.
- Operation names: the design says store_row / load_row / store_block in namespace tron (load_row then overloads the V operation). Alternative: store_k_row / load_k_row to avoid any overload set. Recommendation: follow the design names.
- Partial-range K copy in copy_storage_slot (CHILD kv_cache.hpp:2109-2115): add a typed K copy_token (one consumer) or keep load_row into aligned scratch then store_row (no new function)? Both are typed; the kv_cache.hpp area should decide.
- Should the mapping constants that only qk_group uses (BF16_BITS_16 as int, HIGH_HALF_0XFFFF0000) stay in the tensor header with the rest of the block (keeps the PR 4737 hunk re-applicable and t_k_vnni_layout.cpp:35 working) or move with qk_group? Recommendation: stay; only MAX_KV_MUL_16 moves.
- Does any CI lane build tron at TRON_CHUNK_SIZE == 8 (needed to know whether the 'limited 8-lane child check ... TRON_K_VNNI=OFF' of the design is exercised anywhere)? Insufficient data from CMake and workflow greps.
