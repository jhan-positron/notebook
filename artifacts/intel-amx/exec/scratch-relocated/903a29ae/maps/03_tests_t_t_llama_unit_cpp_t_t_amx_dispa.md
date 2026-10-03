# Tests: t/t_llama_unit.cpp, t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp, t/t_k_vnni_layout.cpp, t/heterogeneous_scheduler_compile.cpp, t/t_heap_v2.cpp, t/t_gof_dma.cpp, t/t_gof_staging_leaks.cpp, t/t_phase1_integration.cpp, t/CMakeLists.txt, config/test-benchmarks.json (merge worktree /home/jhan/workspace/ai-runs/tron-vnnik-typed; HEAD = CHILD 30c4ac82cb, other side = PARENT c12df586b6)

## textual_conflicts
- t/t_llama_unit.cpp 141-153 (merged file). HEAD side 142-144: `page_supports_uniform_kv_access = requires(Page& page, bf16* output) { page.get_k_row(kv_slot_id(0), 0, 0, output); ...get_v(..., output) }`. PARENT side 146-152: `requires(Page& page, view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<Page::layout_t::primary_geometry.head_size>, sseq<1>> output) { page.k(kv_slot_id(0), 0, 0); page.get_v(..., output); }`. Both sides changed the same 3 lines of the merge-base text (c7844ca2ce t/t_llama_unit.cpp:99-102 and 996f58ec82:105-108 both read `requires(Page& page, bf16* output) { page.k(kv_slot_id(0), 0, 0); page.get_v(kv_slot_id(0), 0, 0, output); }`).: Take the PARENT's typed `output` parameter and the CHILD's `get_k_row` call: `requires(Page& page, view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<Page::layout_t::primary_geometry.head_size>, sseq<1>> output) { page.get_k_row(kv_slot_id(0), 0, 0, output); page.get_v(kv_slot_id(0), 0, 0, output); }`. Why: the probe is asserted true at merged line 605 for a {1 head, 64 dims} page and false at 1167 for a heterogeneous page. Under TRON_K_VNNI the CHILD removed `page.k(slot, head, i_page)` for 128-dimension slots (CHILD kv_cache.hpp:1619-1674, every native overload carries `requires(... && !k_vnni::layout_on<head_size>)`), so `page.k` would make the probe layout dependent; `get_k_row` is the layout-agnostic form (CHILD kv_cache.hpp:1737-1764). The design row 'page::set_k_row, page::get_k_row' makes the load destination `view<bf16, Aligned, Dma, seq<D>, sseq<1>>`, the same shape as the PARENT's `v_row_view<bf16, head_size, Dma>` (PARENT v_vnni.hpp: `using v_row_view = view<T, VIEW_ALIGNED_TRUE, Dma, seq<Cols>, sseq<1>>`), so one `output` variable serves both calls.
- t/t_llama_unit.cpp 3257-3751 (merged file). HEAD side 3258-3505 holds the CHILD's whole new TEST_CASE "save_k stores every token's K row once, grouped by page block, alone or with helper threads" ([kv_data][k_vnni]; 3-page book, 192 tokens, 8 KV heads, snapshot lambda, one-thread SECTION and three-thread SECTION with `save_k_helper`). PARENT side 3507-3750 holds the PARENT's whole new TEST_CASE "packed V rows keep their bits through set_v, get_v and at()" ([kv_data]) inside `#if TRON_CHUNK_SIZE == 16 ... #endif`. Each side appended one test case at the end of the file after the same preceding case (the scaled_v/get_v value test ending at 3255), so git shows them as one conflicting hunk. The `=======` is at 3506 and `>>>>>>> origin/jhan-kv-typed-tensors` at 3751.: Keep both cases, one after the other (CHILD's save_k case first, then the PARENT's `#if TRON_CHUNK_SIZE == 16` block, or the reverse; they share no identifiers: the CHILD case uses `k_vnni::HEAD_SIZE_128`, `N_HEADS_16`, ...; the PARENT case uses `HEAD_SIZE_64`, `PATTERN_BASE_0X3C00`, ...). Then adapt the CHILD case body (see semantic_changes): the snapshot lambda `page->get_k_row(slot, kv_head, offset, row.data())` at 3419 takes a typed destination view, and the three-thread SECTION replaces `save_k_helper<geometry>(&q_batch, operation, kouts, worker_ix, N_WORKERS_3)` (3474-3475) with `save_k<geometry>(&q_batch, operation, kouts, worker_ix, N_WORKERS_3)` and the main call `save_k<geometry>(&q_batch, operation, kouts, N_WORKERS_3)` (3478-3479) with `save_k<geometry>(&q_batch, operation, kouts, 0, N_WORKERS_3)` (design 'Worker-index request': final call shape `save_k(..., worker_ix = 0, n_workers = 1)`, helper entry points deleted). The one-thread call at 3462 `save_k<geometry>(&q_batch, operation, kouts)` keeps the defaults.
- t/t_amx_dispatch_dtype.cpp 105-112 (merged file), inside `exercise_page`. HEAD: `page->set_k_row(slot, 0, token, zero.data()); page->template set_v<geometry.kv>(slot, 0, token, zero.data());`. PARENT: `std::copy(zero.begin(), zero.end(), page->k(slot, 0, token).data); page->template set_v<geometry.kv>(slot, 0, token, v_source_row<head_size>(zero.data()));`.: `page->set_k_row(slot, 0, token, k_source_row<head_size>(zero.data()));` (name of the K row helper: open question 1) followed by the PARENT's `set_v` line with `v_source_row<head_size>(zero.data())`. Why: the model is 1 KV head x 128 dims (line 68-69), so under TRON_K_VNNI `page->k(slot, 0, token)` does not exist (CHILD kv_cache.hpp:1631-1640 `requires(... && !k_vnni::layout_on<geometry.head_size>)`), and the PARENT's `set_v` takes a typed source row (PARENT kv_cache.hpp:1913-1931, `const_v_row_view<Source, head_size, Dma> src`). The CHILD's raw `zero.data()` for `set_k_row` must become an explicit read-only view (design: 'Construct read-only source views explicitly in ... affected test callers. Template deduction does not use the conversion from a writable view or raw pointer to const_view').
- t/t_amx_dispatch_dtype.cpp 204-222 (merged file), the CPU fakes in `namespace tron::amx_attn_h128g4`. HEAD: adds `pack_q_rows_128x4(const bf16*, bf16*)` fake (counts into probe.pack_calls, copies the query), adds `qk_vnni_128x4(const bf16*, const bf16*, float* output, size_t stride)` fake (counts qk_calls), and keeps `weights_times_v_128x4(const bf16*, const float*, size_t, float* output)`. PARENT: only retypes `weights_times_v_128x4(v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>, const float*, size_t, float* output)` (and, outside the conflict, already retyped `qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>, ...)` at 195-201).: Keep all three fakes: the CHILD's `pack_q_rows_128x4` unchanged; the CHILD's `qk_vnni_128x4` with its first parameter retyped to `k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>`; the PARENT's typed `weights_times_v_128x4`. The fake signatures must match the declarations in h/tron/kernels/amx_attn_iface.hpp exactly (merged iface 232 for rowmajor, 244 for pack_q_rows, 254 for qk_vnni which still says `const bf16* k_vnni_plane` and must change in the iface owner's area, 266-267 for PV), otherwise the linker pulls libtron's amx_attn.cpp object and the TU's purpose (file header, lines 1-8) is lost. Add `#include "tron/tensor/k_vnni.hpp"` next to the existing `tron/tensor/v_vnni.hpp` include (line 50): a function definition with a by-value parameter needs the complete class type, the forward declaration in kv_cache_fwd.hpp is not enough (design: 'Include the full K tensor header in ... t/t_amx_dispatch_dtype.cpp').
- config/test-benchmarks.json 424-428 (merged file), inside the "granite_rapids_6962p" block (block starts at line 364, meta last_full_bench 2026-09-20). HEAD: `{"name":"t_llama_unit",..."times":{"1":13.436,"2":13.388,"4":13.618},"max_rss_mb":{"1":643,...}}`. PARENT: `{"name":"t_llama_unit",..."times":{"1":5.187,"2":5.256,"4":4.936},"max_rss_mb":{"1":331,...}}`.: Take the PARENT row (rule given for this port: keep the parent's rows, mark t_llama_unit for remeasurement). Record in the PR body that the merged t_llama_unit binary holds both sides' new cases and that the row is a placeholder until `bin/slice bench --update t_k_vnni_layout t_llama_unit` runs on delphi-3bda under user authorization (design S20: bench takes the whole host). Note for the record: the CHILD's own measurement was 13.4 s and 643 MB, so the placeholder understates the merged binary; which CHILD case accounts for the extra 8 s is not measured (insufficient data).
- config/test-benchmarks.json 476-531 (merged file), the tail of the "granite_rapids_6962p" tests array. HEAD (7 rows): t_kv_sliding_reclamation, t_hwperf, t_kv_oom_subcases, t_page_share_counters, t_amx_numerics (0.804/0.745/0.728), t_amx_dispatch_dtype, t_k_vnni_layout (0.709/0.697/0.696, 9/8/8 MB). PARENT (51 rows): the same first six names with the 2026-09-20 main numbers (t_amx_numerics 0.903/0.698/0.58) plus 45 rows main added later (t_memperf ... t_build_tool_schema-slow). t_k_vnni_layout appears nowhere on the PARENT side (grep count 0).: Take the PARENT side whole, then append the CHILD's t_k_vnni_layout row as the last array element: add a comma after the `t_build_tool_schema-slow` row and insert `{"name":"t_k_vnni_layout","filter":"","labels":["fake"],"times":{"1":0.709,"2":0.697,"4":0.696},"max_rss_mb":{"1":9,"2":8,"4":8}}`. Validate with `python3 -m json.tool`. The t_amx_numerics row keeps the PARENT's numbers; the CHILD adds one AMX case to that binary, so include t_amx_numerics in the same bench --update run ('Include t_amx_numerics if materially changed', design line 536). Only the granite_rapids_6962p block is refreshed; genoa96, genoa32 and granite_rapids_6960p stay unrefreshed and are named as such in the PR.

## semantic_changes
- [MUST] t/t_amx_numerics.cpp @ merged lines 235-236, CHILD case "AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K"
  CHANGE: Replace `tron::amx_attn_h128g4::qk_rowmajor_128x4(in->k, q_packed, &s_row[0][0], PAGE_TOKENS_64);` with `qk_rowmajor_128x4(tron::const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>{in->k}, q_packed, &s_row[0][0], PAGE_TOKENS_64);`.
  WHY: Compile necessity. Git auto-merged this file, but the CHILD's call passes a raw `bf16*` to the PARENT's typed declaration.
  EVIDENCE: PARENT h/tron/kernels/amx_attn_iface.hpp:232 `void qk_rowmajor_128x4(const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128> k_page, ...)`; the PARENT fixed its own call the same way at merged t_amx_numerics.cpp:165-167 (`git diff 996f58ec82 origin/jhan-kv-typed-tensors -- t/t_amx_numerics.cpp`).
- [MUST] t/t_amx_numerics.cpp @ merged lines 217-221 (`struct alignas(64) vnni_plane { bf16 v[...] }`, `auto plane = std::make_unique<vnni_plane>()`), 224-227 (`k_vnni::scatter_row(plane->v, tok, in->k + tok * HEAD_SIZE_128)`), 237-238 (`qk_vnni_128x4(plane->v, q_rows, ...)`), and the include at 28
  CHANGE: Replace the raw plane with a typed owner: `auto k_owner = std::make_unique<tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>();` fill it in the same scrambled order with `tron::store_row(k_owner->as_view(), tok, k_source_row<HEAD_SIZE_128>(in->k + tok * HEAD_SIZE_128));` and call `qk_vnni_128x4(std::as_const(*k_owner).as_view(), q_rows, &s_vnni[0][0], PAGE_TOKENS_64);`. Replace `#include "tron/kernels/k_vnni.hpp"` with `#include "tron/tensor/k_vnni.hpp"` (this TU never calls qk_group). Update the comment at 202 ('the K store (k_vnni::scatter_row)') to name store_row.
  WHY: Design: 'Pass k_vnni_view<const bf16,64,128> by value to qk_vnni_128x4'; goal (c) no raw K-plane pointer at the kernel boundary; 'Include the full K tensor header in ... callers constructing views'. The PARENT's PV case already uses the same pattern for V (heap owner, typed row writes, owner->as_view() to the kernel).
  EVIDENCE: merged t_amx_numerics.cpp:285-291 (`auto v_owner = std::make_unique<tron::v_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>(); ... tron::append_v_row(v_owner->as_view(), t, tron::v_source_row<HEAD_SIZE_128>(row));`) and 314-315 (`weights_times_v_128x4(v_owner->as_view(), ...)`). Row fixture `qk_inputs::k` (line 71) stays raw row-major: native rows are legal sources (design: 'These source-row pointers do not expose packed storage'; 'Keep explicit native-view pointer construction legal').
- [MUST] t/t_llama_unit.cpp @ every `set_k_row(..., <array>.data())` call: merged lines 469, 470, 499, 506, 686, 708, 712, 1181, 1822, 1942, 2928-2931, 2965-2967, 3099-3100, 3133-3134
  CHANGE: Wrap the source pointer in an explicit read-only row view, e.g. `page->set_k_row(slot_0, 0, 0, k_source_row<HEAD_SIZE_128>(ones.data()));` and for the geometry forms `page->template set_k_row<geometry_128>(kv_slot_id(1), 0, 0, k_source_row<geometry_128.head_size>(k_row.data()));`. All these arrays are already `alignas(64) std::array<bf16, 128>`, so aligned = true is a true precondition.
  WHY: Design row 'page::set_k_row, page::get_k_row': save takes `const_view<bf16,Aligned,Dma,seq<D>,sseq<1>>`; 'Construct read-only source views explicitly in ... affected test callers. Template deduction does not use the conversion from a writable view or raw pointer to const_view.' Goal (c).
  EVIDENCE: CHILD kv_cache.hpp:1701-1703 current signature `void set_k_row(kv_slot_id slot, size_t kv_head, size_t i_page, const bf16* row)`; PARENT precedent for V at merged t_llama_unit.cpp:190, 777, 1186, 2124 (`v_source_row<...>(...)`).
- [MUST] t/t_llama_unit.cpp @ every `get_k_row(..., <array>.data())` call: merged lines 471, 473, 509, 514, 714, 1205-1206, 1843-1844, 1965, 2434, 3013-3016, 3419
  CHANGE: Wrap the destination pointer in a writable row view, e.g. `page->get_k_row(slot_0, 0, 0, k_destination_row<HEAD_SIZE_128>(got.data()));`. In the snapshot lambda of the save_k case (3419) the buffer `row` is `alignas(64) std::array<bf16, HEAD_SIZE_128>`, so the same wrapper applies.
  WHY: Design row 'page::set_k_row, page::get_k_row': load takes `view<bf16,Aligned,Dma,seq<D>,sseq<1>>`. The PARENT did the identical rewrite for `get_v` (design line 347: 'Rewrite the six raw-pointer test callers').
  EVIDENCE: CHILD kv_cache.hpp:1737-1739 `void get_k_row(kv_slot_id slot, size_t kv_head, size_t i_page, bf16* row) const`; PARENT precedent merged t_llama_unit.cpp:784, 1212, 2440, 3179 (`v_destination_row<...>(...)`).
- [MUST] t/t_llama_unit.cpp @ merged lines 3470-3479, three-thread SECTION of the save_k case
  CHANGE: Helpers: `state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts, worker_ix, N_WORKERS_3);` Main thread: `state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts, 0, N_WORKERS_3);` Update the SECTION comment ('the helpers share the window') to say every thread calls save_k with its worker index. The one-thread SECTION (3462) and the consumer/producer calls at 2328/2331 stay as they are (defaults worker_ix = 0, n_workers = 1).
  WHY: Design 'Worker-index request': 'Merge both existing save_k/save_k_helper overload pairs ... The final call shape is save_k(..., worker_ix = 0, n_workers = 1). Delete the separate helper entry points. ... Update adjacent comments and direct three-thread calls in t/t_llama_unit.cpp. Search all old positional calls, which passed only n_workers.' The call at 3478-3479 is such a positional call (passes only N_WORKERS_3).
  EVIDENCE: CHILD model.hpp:2953-2962 `save_k_helper(...)`, 3065 `void save_k(batch* q_batch, kv_buffer_t& ks, size_t n_workers = 1)`, 3073 descriptor form; PARENT model.hpp:2789/2797 `save_k(batch*, kv_buffer_t&)` and `save_k(batch*, operation, ks)` calling `save_k_impl`. The merged model.hpp currently carries both shapes (3081-3094 with n_workers, 2969-2990 save_k_helper) and is a UU conflict owned by another area; the test calls must follow the final shape the model.hpp owner lands.
- [MUST] t/t_k_vnni_layout.cpp @ whole file (CHILD-only file, 472 lines, no PARENT edits); every site that touches a raw K plane
  CHANGE: Map each raw-plane use to the typed API. (1) Fixture `struct alignas(64) plane_and_rows { bf16 plane[64*128]; bf16 rows[64*128]; }` (67-70): replace `plane` by `tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128> plane;` keep `rows` raw (native source rows). (2) `k_vnni::scatter_row(buf->plane, tok, buf->rows + tok*128)` at 113, 139-140, 199, 214, 226, 291 -> `tron::store_row(buf->plane.as_view(), tok, k_source_row<HEAD_SIZE_128>(buf->rows + tok * HEAD_SIZE_128))`. (3) `k_vnni::gather_row(buf->plane, tok, row)` at 129, 232 -> `tron::load_row(std::as_const(buf->plane).as_view(), tok, k_destination_row<HEAD_SIZE_128>(row))` (as_const: the first parameter is `k_vnni_view<const bf16, Rows, Cols>`, deduction does not apply the writable-to-read-only conversion). (4) `k_vnni::store_block(blk->plane, c, __mmask16(m), rows)` at 201, 228 -> `tron::store_block(blk->plane.as_view(), c, __mmask16(m), rows)` with `const bf16* const rows[BLOCK_TOKENS_16]` unchanged (design: 'Preserve const bf16* const rows[BLOCK_TOKENS_16]'). (5) Direct element reads `buf->plane[k_vnni::index(tok, d)]` at 120-122, 143-144 -> copy the owner's bytes first: `alignas(64) std::array<tron::bf16, PAGE_TOKENS_64 * HEAD_SIZE_128> bytes; std::memcpy(bytes.data(), &buf->plane, sizeof(buf->plane));` then index `bytes[k_vnni::index(tok, d)]` ('Copy the trivially copyable owner's bytes to a test buffer for physical-layout comparisons. Preserve independent index anchors'). (6) Poison fills `for (auto& x : buf->plane) x = POISON` at 107-109, 190-192 and the NaN fill at 286-288 -> one poison row `alignas(64) bf16 poison_row[128]` filled with the pattern, then `for tok in 0..63: store_row(plane.as_view(), tok, k_source_row<128>(poison_row))` ('Fill poison with 64 typed row saves'). (7) `std::memcpy(blk->plane, ref->plane, sizeof)` at 193, 216 -> `blk->plane = ref->plane;` (defaulted trivially-copyable owner assignment, design: 'Whole-plane copying uses the defaulted owner assignment'). (8) `std::memcmp(blk->plane, ref->plane, sizeof(ref->plane))` at 202, 229 -> `std::memcmp(&blk->plane, &ref->plane, sizeof(ref->plane)) == 0` (one 16384-byte array member, alignas 64, no padding; add `static_assert(sizeof(tron::k_vnni_tensor<64,128>) == 64 * 128 * sizeof(bf16))`). (9) `k_vnni::qk_group<KV_MUL_4>(buf->plane, q, live, s, stride)` at 306-309 -> `tron::k_vnni::qk_group<KV_MUL_4>(std::as_const(buf->plane).as_view(), q_bf16, live, &s_bf16[0][0], PAGE_TOKENS_64)`. (10) `page->set_k_row(SLOT_0, 0, tok, row.data())` at 401, 424, 428, 453 and `get_k_row(..., got.data())` at 405, 434, 441, 459 -> typed row views as in t_llama_unit. (11) Includes (24-26): add `#include "tron/tensor/k_vnni.hpp"` (owner, view, index, layout_on, constants, store/load/block ops) and keep `#include "tron/kernels/k_vnni.hpp"` only for qk_group; keep `tron/kernels/dotter.hpp` and `tron/models/kv_cache.hpp`. (12) The index anchors (81-90, `STATIC_REQUIRE(index(17, 34) == 2594)` etc.) and `using tron::k_vnni::index` stay verbatim ('Keep the function spelling for the independent index checks'). (13) Do not call `detail::k_vnni_access`, `detail::pair_base` or `pair_row_offsets` ('avoid the internal friend helpers'). The `#if TRON_CHUNK_SIZE == 16` guard (31, 466) and the `#ifdef TRON_K_VNNI` layout_on checks (388-392) stay.
  WHY: Design: 'Adapt t_k_vnni_layout to actual aligned owners. Fill poison with 64 typed row saves. Copy the trivially copyable owner's bytes to a test buffer for physical-layout comparisons. Preserve independent index anchors and avoid the internal friend helpers.' Goal (c) and (d): the test still proves bit-identical plane contents against the hand-computed index map, now through the owner's bytes.
  EVIDENCE: CHILD h/tron/kernels/k_vnni.hpp:139 `void scatter_row(bf16* plane, size_t token, const bf16* row)`, 194 `void store_block(bf16* plane, ...)`, 221 `void gather_row(const bf16* plane, size_t token, bf16* row)`, 248 `void qk_group(const bf16* plane, const q_scalar* q, uint64_t live, float* s, size_t s_stride)`; the row loads inside scatter_row/gather_row are `_mm512_loadu_si512` / `_mm512_storeu_si512` (CHILD k_vnni.hpp:142, 226), so the K row views carry the caller's alignment flag without a new alignment requirement (design: 'These K routines do not acquire V's stronger alignment requirement').
- [MUST] t/t_amx_dispatch_dtype.cpp @ merged line 50 (includes) and the fakes at 196-230
  CHANGE: Add `#include "tron/tensor/k_vnni.hpp"`; retype the `qk_vnni_128x4` fake's first parameter to `k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>` (see textual conflict 4). Keep the fakes unconditional (no `#ifdef TRON_K_VNNI`): the declarations in amx_attn_iface.hpp are unconditional, and the file header (1-8) promises every entry point is a fake.
  WHY: Compile and link necessity; design 'Keep K class definitions complete in both vector widths for unconditional fake definitions'.
  EVIDENCE: merged amx_attn_iface.hpp:244 `void pack_q_rows_128x4(const bf16* q_group, bf16* padded)`, 254 `void qk_vnni_128x4(const bf16* k_vnni_plane, ...)` (to be retyped by the iface owner), 266-267 `void weights_times_v_128x4(v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128> v_page, ...)`.
- [SHOULD] t/t_llama_unit.cpp @ probes at merged 95-166 and the case "attention operations resolve to typed KV slots" at 362-478 (design line 598 cites the stale positions 84-123 and 316-342)
  CHANGE: Add K-VNNI analogs of the PARENT's V contracts: a probe `amx_qk_vnni_accepts<K>` = `requires(K k, const bf16* q, float* s) { amx_attn_h128g4::qk_vnni_128x4(k, q, s, size_t{0}); }`; aliases `k_vnni_plane_t = k_vnni_view<const bf16, 64, 128>`, `k_vnni_plane_mut_t = k_vnni_view<bf16, 64, 128>`, `k_vnni_owner_t = k_vnni_tensor<64, 128>`; then `STATIC_REQUIRE(amx_qk_vnni_accepts<k_vnni_plane_t>)`, `STATIC_REQUIRE(amx_qk_vnni_accepts<k_vnni_plane_mut_t>)`, `STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<const bf16*>)`, `...<bf16*>`, `...<k_plane_t>` (native K view), `...<v_plane_t>`; `STATIC_REQUIRE_FALSE(amx_qk_accepts<k_vnni_plane_t>)` and `STATIC_REQUIRE_FALSE(amx_pv_accepts<k_vnni_plane_t>)` (the row-major QK and the PV kernel reject the VNNI K view); `STATIC_REQUIRE_FALSE(std::is_constructible_v<k_vnni_plane_mut_t, bf16*>)`, `...<k_vnni_plane_t, const bf16*>`, `STATIC_REQUIRE_FALSE(std::is_default_constructible_v<k_vnni_plane_t>)`; `STATIC_REQUIRE(std::is_convertible_v<k_vnni_plane_mut_t, k_vnni_plane_t>)`, `STATIC_REQUIRE_FALSE(std::is_convertible_v<k_vnni_plane_t, k_vnni_plane_mut_t>)`; `STATIC_REQUIRE_FALSE(owner_views_temporary<k_vnni_owner_t>)`; `STATIC_REQUIRE_FALSE(matrix_indexes_rows<k_vnni_plane_t>)`; trivial traits, `sizeof(k_vnni_owner_t) == 64 * 128 * sizeof(bf16)` (16384 bytes), `alignof(k_vnni_owner_t) == 64`; and the storage selection: `#ifdef TRON_K_VNNI STATIC_REQUIRE(std::is_same_v<decltype(kv_block_t::k), k_vnni_owner_t>); #else STATIC_REQUIRE(std::is_same_v<decltype(kv_block_t::k), bf16[64 * 128]>); #endif`. The existing `sizeof(kv_block_t) == detail::KV_BLOCK_PLANES_2 * sizeof(v_owner_t)` (445) keeps holding (design: 'sizeof(k) == sizeof(v)'). Add `matrix_at_writes` checks for K only if k_vnni_view gets `at()` (open question 2).
  WHY: Design 'Typed function boundaries' row: 'Positive checks accept each function's own view. Use STATIC_REQUIRE/STATIC_REQUIRE_FALSE for those call contracts ... Reject raw-pointer construction of packed matrices ... Accept writable-to-read-only matrix conversion only.' and 'Apply the V owner's lvalue-only as_view(), const conversion, and private packed-pointer rules to K too. Require 64-byte alignment ... sizeof(k) == sizeof(v), and a 16,384-byte owner for 64 tokens by 128 dimensions.' These compile in both builds because the K classes are defined unconditionally and qk_vnni_128x4 is declared unconditionally.
  EVIDENCE: PARENT contracts at merged t_llama_unit.cpp:392-445 (`amx_qk_accepts`, `amx_pv_accepts`, `owner_views_temporary`, `matrix_at_writes`, `matrix_indexes_rows`, the sizeof/alignof/trivial-trait checks for `v_owner_t`); PARENT kv_block at kv_cache.hpp:2452 `bf16 k[page_size * head_size]`.
- [SHOULD] t/t_llama_unit.cpp @ merged 158-160 (`page_k_accepts_geometry`), 1072-1077, 1157-1167, 1800-1801
  CHANGE: Keep the existing `STATIC_REQUIRE_FALSE((page_k_accepts_geometry<page_t, geometry_128>))` under TRON_K_VNNI (1075-1076, 1162): still correct, the native overloads keep their `!layout_on` restriction. Add a probe `page_k_packed_accepts_geometry<Page, geometry>` = `requires(Page const& page) { page.template k_packed<geometry>(kv_slot_id(0), 0); }` and assert `#ifdef TRON_K_VNNI STATIC_REQUIRE((page_k_packed_accepts_geometry<page_t, geometry_128>)); STATIC_REQUIRE(std::is_same_v<decltype(std::declval<page_t const&>().template k_packed<geometry_128>(kv_slot_id(0), 0)), k_vnni_view<const bf16, page_t::page_size, 128>>); #else STATIC_REQUIRE_FALSE(...geometry_128) #endif` and `STATIC_REQUIRE_FALSE((page_k_packed_accepts_geometry<page_t, geometry_64>))` in both builds. Reword the comments at 1159-1161 and 1073-1074 ('set_k_row / get_k_row serve the slot') to add 'and k_packed exposes the plane as a read-only typed view'.
  WHY: Design row 'page::k, page::k_vnni_plane': 'Keep native overloads and their !layout_on restrictions. Replace the raw packed-plane accessor with page::k_packed<geometry>(slot, head), constrained to packed storage. Const access returns k_vnni_view<const bf16,page_size,geometry.head_size>'. Mirrors the PARENT's `v_packed` and the existing `page_scaled_v_accepts_geometry` probe.
  EVIDENCE: CHILD kv_cache.hpp:1686-1693 `const bf16* k_vnni_plane(kv_slot_id slot, size_t kv_head) const` with `requires(... && k_vnni::layout_on<geometry.head_size>)`; PARENT kv_cache.hpp:1952 `v_vnni_view<const bf16, page_size, geometry.head_size> v_packed(...)`; probe precedent merged t_llama_unit.cpp:162-166.
- [SHOULD] t/t_llama_unit.cpp @ includes at merged 60-77
  CHANGE: Add `#include "tron/tensor/k_vnni.hpp"` next to `tron/tensor/v_vnni.hpp`.
  WHY: The file names `k_vnni::HEAD_SIZE_128` (465, 496, 3270) and `k_vnni::layout_on` (1072, 3484) and, after the port, `k_vnni_view`/`k_vnni_tensor`; today these arrive only transitively through kv_cache.hpp (merged kv_cache.hpp:27 includes `tron/kernels/k_vnni.hpp`, which the design replaces by the tensor header). IWYU consistency with the PARENT's explicit `tron/tensor/v_vnni.hpp` include.
  EVIDENCE: merged t_llama_unit.cpp:60-77 include list has no k_vnni header; design: 'The cache includes the K tensor header ... The cache drops its include of this kernel header.'
- [SHOULD] t/t_amx_numerics.cpp @ CHILD case at merged 195-250 and PARENT case at 252-346; coexistence
  CHANGE: Both cases stay as separate TEST_CASEs in the one TU: the PARENT's PV case (V owner `v_vnni_tensor<64,128>`, bytes compared with the independent pair formula, kernel fed `v_owner->as_view()`) and the CHILD's QK identity case (K owner `k_vnni_tensor<64,128>`, both kernels fed typed views, scores compared bit for bit). Fixture types the typed `qk_vnni_128x4` needs: `std::unique_ptr<tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>` (16384 bytes, alignas 64, heap: aligned operator new honors alignas) plus the existing `qk_inputs` (row-major `k` for `const_native_k_view` and `q`). Keep the `available()` early-return WARN (206-209); the design's acceptance rule (line 656) asks for a 3bda log showing the identity case ran without the 'AMX unavailable' warning and a separate TRON_AMX_DISABLE=1 run showing the warning.
  WHY: Design: 'Pass k_vnni_view<const bf16,64,128> by value to qk_vnni_128x4'; parity with the PARENT's PV fixture (design line 503).
  EVIDENCE: merged t_amx_numerics.cpp:279-299 (PARENT owner pattern), 217-238 (CHILD raw pattern).
- [SHOULD] config/test-benchmarks.json @ granite_rapids_6962p block, after the conflict resolution
  CHANGE: Run `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics` on delphi-3bda under user authorization (whole host, 1/2/4 slices), then commit the refreshed rows; until then state the deferral in the PR body naming the unrefreshed platforms.
  WHY: Design line 536/666/700: 'resolve the shared t_llama_unit record by remeasurement ... Record any deferred refresh explicitly'; 'Do not insert estimated durations'.
  EVIDENCE: HEAD row 13.436 s / 643 MB vs PARENT row 5.187 s / 331 MB for t_llama_unit (merged test-benchmarks.json:425, 427).
- [COULD] t/t_gof_dma.cpp, t/t_gof_staging_leaks.cpp, t/t_phase1_integration.cpp @ merged t_gof_dma.cpp:347, t_gof_staging_leaks.cpp:137, t_phase1_integration.cpp:857, 890, 943 (`k_head_fn = [...](kv_slot_id, size_t h, bf16*) { return kbuf[t][h]; }`)
  CHANGE: No change. The CHILD added the scratch `bf16*` parameter; the PARENT did not touch these files or the callback type; merged full.hpp:2747 already builds the 3-argument lambda. The lambdas return native rows from caller buffers, not plane pointers.
  WHY: Design row 'hardware::page_info K callback: Add the child's scratch parameter.' Already satisfied by the auto-merge; recording that it was reviewed semantically.
  EVIDENCE: `git diff c7844ca2ce origin/jhan-amx-vnniK -- t/t_gof_dma.cpp t/t_gof_staging_leaks.cpp t/t_phase1_integration.cpp` shows only the signature change; `git diff 996f58ec82 origin/jhan-kv-typed-tensors -- <same files>` is empty.
- [COULD] t/heterogeneous_scheduler_compile.cpp, t/t_heap_v2.cpp, t/CMakeLists.txt @ heterogeneous_scheduler_compile.cpp:440-455 (geometry_256 slot, `page->k<software_geometry.kv>(slot, 0, 0)[i] = bf16(0.0f)`), t_heap_v2.cpp:1212-1220 (alignment check of try_make_unique_dma_for_overwrite), t/CMakeLists.txt:618 (`add_catch_test(NAME t_k_vnni_layout LIBRARIES tron pos_fake PROPERTIES LABELS fake)`)
  CHANGE: No change. heterogeneous_scheduler_compile writes a 256-dimension head, which is native in both builds (`k_vnni::layout_on<256>` is false, CHILD k_vnni.hpp:92-97). t_heap_v2 is PARENT-only and has no K access. t/CMakeLists.txt is CHILD-only (+1 line) and auto-merged; no new test TU is needed for this port.
  WHY: Semantic review of auto-merged files, as the design asks ('Review every file changed on both sides semantically, even when Git merges it automatically').
  EVIDENCE: `git diff --stat` of both sides over t/ (CHILD touches t_gof_dma, t_gof_staging_leaks, t_k_vnni_layout, t_phase1_integration, CMakeLists; PARENT touches heterogeneous_scheduler_compile, t_heap_v2; both touch t_amx_dispatch_dtype, t_amx_numerics, t_llama_unit).
- [COULD] t/t_amx_numerics.cpp @ CHILD QK identity case
  CHANGE: Do not add a K 'owner bytes equal the index map' check here; t_k_vnni_layout already pins the index map against the store (its case 'VNNI K store and load are exact and token-independent').
  WHY: Rule 2 (no speculative code); the PARENT's byte check for V exists because no other test pins the V formula.
  EVIDENCE: merged t_k_vnni_layout.cpp:115-125.

## proposed_code
// ---- t/t_llama_unit.cpp : merged probe (resolves conflict 141-153) ----
template <typename Page>
constexpr bool page_supports_uniform_kv_access = requires(Page& page,
    view<bf16,
        VIEW_ALIGNED_TRUE,
        VIEW_DMA_FALSE,
        seq<Page::layout_t::primary_geometry.head_size>,
        sseq<1>> output) {
  page.get_k_row(kv_slot_id(0), 0, 0, output);  // both K layouts (Note [K VNNI storage])
  page.get_v(kv_slot_id(0), 0, 0, output);
};

// New probes beside the existing ones (merged 95-166)
template <typename K>
constexpr bool amx_qk_vnni_accepts = requires(K k, const bf16* q, float* s) {
  amx_attn_h128g4::qk_vnni_128x4(k, q, s, size_t{0});
};
template <typename Page, kv_geometry geometry>
constexpr bool page_k_packed_accepts_geometry =
    requires(Page const& page) { page.template k_packed<geometry>(kv_slot_id(0), 0); };

// Additions to the case "attention operations resolve to typed KV slots" (merged 392-445)
using k_vnni_plane_t = k_vnni_view<const bf16, amx_attn_h128g4::PAGE_TOKENS_64,
    amx_attn_h128g4::HEAD_SIZE_128>;
using k_vnni_plane_mut_t = k_vnni_view<bf16, amx_attn_h128g4::PAGE_TOKENS_64,
    amx_attn_h128g4::HEAD_SIZE_128>;
using k_vnni_owner_t =
    k_vnni_tensor<amx_attn_h128g4::PAGE_TOKENS_64, amx_attn_h128g4::HEAD_SIZE_128>;
STATIC_REQUIRE(amx_qk_vnni_accepts<k_vnni_plane_t>);
STATIC_REQUIRE(amx_qk_vnni_accepts<k_vnni_plane_mut_t>);  // writable converts to read-only
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<const bf16*>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<bf16*>);
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<k_plane_t>);  // the native K view
STATIC_REQUIRE_FALSE(amx_qk_vnni_accepts<v_plane_t>);
STATIC_REQUIRE_FALSE(amx_qk_accepts<k_vnni_plane_t>);
STATIC_REQUIRE_FALSE(amx_pv_accepts<k_vnni_plane_t>);
STATIC_REQUIRE_FALSE(std::is_constructible_v<k_vnni_plane_mut_t, bf16*>);
STATIC_REQUIRE_FALSE(std::is_constructible_v<k_vnni_plane_t, const bf16*>);
STATIC_REQUIRE_FALSE(std::is_default_constructible_v<k_vnni_plane_t>);
STATIC_REQUIRE(std::is_convertible_v<k_vnni_plane_mut_t, k_vnni_plane_t>);
STATIC_REQUIRE_FALSE(std::is_convertible_v<k_vnni_plane_t, k_vnni_plane_mut_t>);
STATIC_REQUIRE_FALSE(owner_views_temporary<k_vnni_owner_t>);
STATIC_REQUIRE_FALSE(matrix_indexes_rows<k_vnni_plane_t>);
STATIC_REQUIRE(std::is_trivially_default_constructible_v<k_vnni_owner_t>);
STATIC_REQUIRE(std::is_trivially_destructible_v<k_vnni_owner_t>);
STATIC_REQUIRE(std::is_trivially_copyable_v<k_vnni_owner_t>);
STATIC_REQUIRE(sizeof(k_vnni_owner_t) ==
               amx_attn_h128g4::PAGE_TOKENS_64 * amx_attn_h128g4::HEAD_SIZE_128 * sizeof(bf16));
STATIC_REQUIRE(alignof(k_vnni_owner_t) == 64);
#ifdef TRON_K_VNNI
STATIC_REQUIRE(std::is_same_v<decltype(kv_block_t::k), k_vnni_owner_t>);
#else
STATIC_REQUIRE(std::is_same_v<decltype(kv_block_t::k),
    bf16[amx_attn_h128g4::PAGE_TOKENS_64 * amx_attn_h128g4::HEAD_SIZE_128]>);
#endif
// (existing) STATIC_REQUIRE(sizeof(kv_block_t) == detail::KV_BLOCK_PLANES_2 * sizeof(v_owner_t));

// Typed row calls (pattern for all set_k_row / get_k_row call sites); helper names: open question 1
page->set_k_row(slot_0, 0, 0, k_source_row<HEAD_SIZE_128>(ones.data()));
page->get_k_row(slot_0, 0, 0, k_destination_row<HEAD_SIZE_128>(got.data()));
page->template set_k_row<geometry_128>(
    kv_slot_id(1), 0, 0, k_source_row<geometry_128.head_size>(k_row.data()));

// save_k three-thread SECTION (merged 3470-3479)
for (size_t worker_ix = 1; worker_ix < N_WORKERS_3; ++worker_ix) {
  helpers.emplace_back([&, worker_ix] {
    state.template save_k<geometry>(
        &q_batch, operation, state.plugin_state.kouts, worker_ix, N_WORKERS_3);
  });
}
state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts, 0, N_WORKERS_3);

// ---- t/t_amx_dispatch_dtype.cpp ----
#include "tron/tensor/k_vnni.hpp"   // full K types: the fakes take views by value
// fill loop (resolves conflict 105-112)
page->set_k_row(slot, 0, token, k_source_row<head_size>(zero.data()));
page->template set_v<geometry.kv>(slot, 0, token, v_source_row<head_size>(zero.data()));
// fakes (resolves conflict 204-222)
void pack_q_rows_128x4(const bf16* input, bf16* output) noexcept { /* unchanged CHILD body */ }
void qk_vnni_128x4(k_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const bf16*,
    float* output,
    size_t stride) noexcept {
  ++probe.qk_calls;
  std::fill_n(output, GROUP_HEADS_4 * stride, 0.0f);
}
void weights_times_v_128x4(v_vnni_view<const bf16, PAGE_TOKENS_64, HEAD_SIZE_128>,
    const float*,
    size_t,
    float* output) noexcept { /* PARENT body */ }

// ---- t/t_amx_numerics.cpp : CHILD identity case on typed owners ----
#include "tron/tensor/k_vnni.hpp"   // replaces "tron/kernels/k_vnni.hpp" (qk_group unused here)
auto in = std::make_unique<qk_inputs>();
auto k_owner = std::make_unique<tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>>();
for (size_t i = 0; i < PAGE_TOKENS_64; ++i) {  // scrambled store order
  const size_t tok = (i * SCRAMBLE_STRIDE_37 + SCRAMBLE_OFFSET_11) % PAGE_TOKENS_64;
  tron::store_row(k_owner->as_view(), tok,
      k_source_row<HEAD_SIZE_128>(in->k + tok * HEAD_SIZE_128));
}
tron::amx_attn_h128g4::qk_rowmajor_128x4(
    tron::const_native_k_view<PAGE_TOKENS_64, HEAD_SIZE_128>{in->k}, q_packed,
    &s_row[0][0], PAGE_TOKENS_64);
tron::amx_attn_h128g4::qk_vnni_128x4(
    std::as_const(*k_owner).as_view(), q_rows, &s_vnni[0][0], PAGE_TOKENS_64);

// ---- t/t_k_vnni_layout.cpp : fixture and the five operation shapes ----
#include "tron/kernels/k_vnni.hpp"  // qk_group only
#include "tron/tensor/k_vnni.hpp"   // owner, view, index, layout_on, store_row/load_row/store_block
struct alignas(64) plane_and_rows {
  tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128> plane;
  tron::bf16 rows[PAGE_TOKENS_64 * HEAD_SIZE_128];  // the same K, one native row per token
};
static_assert(sizeof(tron::k_vnni_tensor<PAGE_TOKENS_64, HEAD_SIZE_128>) ==
              PAGE_TOKENS_64 * HEAD_SIZE_128 * sizeof(tron::bf16));
// poison: 64 typed row saves
alignas(64) tron::bf16 poison_row[HEAD_SIZE_128];
for (auto& x : poison_row) { x = tron::bf16::from_bits(POISON_0XA5A5); }
for (size_t tok = 0; tok < PAGE_TOKENS_64; ++tok) {
  tron::store_row(buf->plane.as_view(), tok, k_source_row<HEAD_SIZE_128>(poison_row));
}
// store / load / block
tron::store_row(buf->plane.as_view(), tok, k_source_row<HEAD_SIZE_128>(buf->rows + tok * HEAD_SIZE_128));
tron::load_row(std::as_const(buf->plane).as_view(), tok, k_destination_row<HEAD_SIZE_128>(row));
tron::store_block(blk->plane.as_view(), c, __mmask16(m), rows);  // const bf16* const rows[16]
// physical-layout comparison through the owner's bytes
alignas(64) std::array<tron::bf16, PAGE_TOKENS_64 * HEAD_SIZE_128> bytes;
std::memcpy(bytes.data(), &buf->plane, sizeof(buf->plane));
REQUIRE(bytes[tron::k_vnni::index(tok, d)].to_bits() == buf->rows[tok * HEAD_SIZE_128 + d].to_bits());
// whole-plane copy and compare
blk->plane = ref->plane;
REQUIRE(std::memcmp(&blk->plane, &ref->plane, sizeof(ref->plane)) == 0);
// software reader
tron::k_vnni::qk_group<KV_MUL_4>(std::as_const(buf->plane).as_view(), q_bf16, live, &s_bf16[0][0], PAGE_TOKENS_64);

// ---- config/test-benchmarks.json : tail of granite_rapids_6962p after taking the PARENT side ----
      {"name":"t_build_tool_schema-slow","filter":"[slow]","labels":["fake","slow"],"times":{"1":16.476,"2":16.484,"4":16.496},"max_rss_mb":{"1":253,"2":296,"4":263}},
      {"name":"t_k_vnni_layout","filter":"","labels":["fake"],"times":{"1":0.709,"2":0.697,"4":0.696},"max_rss_mb":{"1":9,"2":8,"4":8}}
    ]

## design_contradictions
- Design 'Child storage and access' spells the native branch as `using native_k_storage = bf16s[page_size][head_size / chunk_size];`. The PARENT's final kv_block::k is `alignas(kv_block_alignment) bf16 k[page_size * head_size];` with `k_view()` / `k_at()` (PARENT h/tron/models/kv_cache.hpp:2449-2495). The test contracts must assert `decltype(kv_block_t::k)` is `bf16[64 * 128]` in the native build, not the bf16s shape; the `std::conditional_t` selection in kv_cache.hpp (other area) must use the PARENT's array.
- Design asks for `k_vnni_row` and 'row expressions and their compatibility checks' (design lines 528, 'The proposed K row expression ... If Q3 is rejected, remove the row expressions ... from both families'). Q3 is rejected (PARENT commit c12df586b6 dropped v_vnni_row and the expr base; PR body: 'do not add code which has no consumer'). So the tests add no `k_vnni_row` probe and keep `STATIC_REQUIRE_FALSE(matrix_indexes_rows<k_vnni_plane_t>)`, mirroring the PARENT's V checks at merged t_llama_unit.cpp:428-429.
- Design line 598 cites 'the existing constants at t_llama_unit.cpp:84-123' and 'the existing case at 316-342'. In the merged file the probes are at 95-166 and the case "attention operations resolve to typed KV slots" spans 362-478; the design's line numbers are stale (design line 195 already warns to re-locate citations).
- Design line 536 says 'Carry the child's granite_rapids_6962p records for t_llama_unit, t_amx_numerics, and t_k_vnni_layout as historical measurements', but the JSON holds one row per test name, and the port rule keeps the PARENT's t_llama_unit and t_amx_numerics rows. The CHILD's numbers for those two tests survive only in git history (origin/jhan-amx-vnniK config/test-benchmarks.json), not in the file. Only t_k_vnni_layout's CHILD row is carried.
- Design row 'page::set_k_row, page::get_k_row' makes `Aligned` a deduced template flag ('These K routines do not acquire V's stronger alignment requirement'), while the PARENT's V helpers fix `VIEW_ALIGNED_TRUE` (`v_source_row`, `v_destination_row` in v_vnni.hpp). The merged `page_supports_uniform_kv_access` probe passes one aligned/dma-false view to both get_k_row and get_v, which works under either choice, but the K row helper for test callers has no name in the design or the PARENT (open question 1).
- Design 'Keep K class definitions complete in both vector widths for unconditional fake definitions' requires `k_vnni_tensor` / `k_vnni_view` to exist with TRON_K_VNNI=OFF and at 8 lanes. The proposed STATIC_REQUIRE contracts and the unconditional fakes in t_amx_dispatch_dtype.cpp depend on it; if the tensor-header owner guards the classes behind TRON_K_VNNI, the test contracts (and the CPU fakes) fail to compile in the OFF build.
- Design says the test should 'avoid the internal friend helpers' and compare 'the trivially copyable owner's bytes'. This means `k_vnni_view` needs no `at()` for t_k_vnni_layout. The PARENT gave `v_vnni_view` an `at(token, dim)` whose only non-kernel consumer is a test (merged t_llama_unit.cpp:3737-3745). Whether K gets `at()` is undecided (open question 2); the K contracts proposed above omit `matrix_at_writes` until it is.

## risks
- t/t_amx_numerics.cpp was auto-merged but does not compile: line 235-236 passes raw `in->k` to the PARENT's typed `qk_rowmajor_128x4` (amx_attn_iface.hpp:232). Easy to miss because git reported no conflict.
- `load_row` and `qk_group` take `k_vnni_view<const bf16, Rows, Cols>` as a deduced parameter; passing `owner.as_view()` from a non-const owner (a writable view) fails deduction. Test code must use `std::as_const(owner).as_view()` or a const owner reference. Non-template kernel calls (`qk_vnni_128x4`) accept the writable view through the conversion.
- `std::memcmp(&a_owner, &b_owner, sizeof)` is valid only while the owner is a single bf16[8192] member with no padding (16384 is a multiple of the 64-byte alignment). The static_assert on `sizeof(k_vnni_tensor<64,128>) == 16384` in the test guards it.
- t_llama_unit's test-cost row after resolution (PARENT 5.2 s) understates the merged binary (CHILD measured 13.4 s with its save_k case); bin/slice uses the row for load balancing. Remeasure before merge; the row does not affect correctness.
- PR #4737 (origin/jhan-amx-vnniK-i4500, stacked on CHILD) adds in t_llama_unit.cpp, t_k_vnni_layout.cpp and t_amx_dispatch_dtype.cpp tests that call `page->set_k_row(slot_0, kv_head, tok, (*rows)[tok].data())` with raw pointers and new page methods `note_k_row_saved` / `k_block_to_vnni` (in-place block conversion between row-major and VNNI). After this port those tests need the same typed-row rewrite, and `k_block_to_vnni` must operate through writable owner views; if the typed owner exposes no in-place block conversion route, #4737 cannot be merged on top. Only mentioned; not part of this port.
- If the iface owner keeps `qk_vnni_128x4(const bf16* k_vnni_plane, ...)` (merged amx_attn_iface.hpp:254) while the test fakes are retyped, the fakes stop matching and the linker pulls libtron's amx_attn.cpp into t_amx_dispatch_dtype, defeating the test's purpose (file header lines 1-8). The fake signatures and the declarations must change together.
- The save_k three-thread test (merged 3470-3479) depends on the final `save_k(..., worker_ix, n_workers)` shape landing in model.hpp (a UU conflict in another area). If model.hpp keeps `save_k_helper`, the test must keep the CHILD's calls; the two must be changed in the same commit or the test TU fails to compile.
- 8-lane builds: t_llama_unit and t_heterogeneous_scheduler already contain unguarded 16-lane-only set_v/get_v calls (design line 626); this port does not make them 8-lane clean. t_k_vnni_layout stays guarded by `#if TRON_CHUNK_SIZE == 16`.
- The STATIC_REQUIRE contracts proposed for `k_vnni_tensor` with TRON_K_VNNI=OFF exercise a class that selects no storage in that build; a header that defines the K classes only under TRON_K_VNNI breaks the OFF build of t_llama_unit and t_amx_dispatch_dtype.

## open_questions
- Name and home of the K row-view helpers for callers: `k_source_row<D, Dma = VIEW_DMA_FALSE>(const bf16*)` -> `const_view<bf16, VIEW_ALIGNED_TRUE, Dma, seq<D>, sseq<1>>` and `k_destination_row<D>(bf16*)` in h/tron/tensor/k_vnni.hpp (mirroring v_source_row / v_destination_row in v_vnni.hpp from Ben's fast-forwarded PR #4697, commit 8bbbb7c82d), or reuse of the v_* helpers (same view types, misleading name), or a neutral kv_* rename of Ben's helpers. About 40 test call sites depend on the choice (t_llama_unit 26, t_k_vnni_layout 8, t_amx_dispatch_dtype 1, t_amx_numerics 1 plus the fixture loops).
- Does `k_vnni_view` get `at(token, dim)` like `v_vnni_view`? With Q3 rejected and the layout test comparing owner bytes, its only consumer would be a test. If added, mirror `matrix_at_writes` positive/negative checks for K; if not, the K contracts stay as proposed.
- Namespace of the typed K operations: `tron::store_row` / `tron::load_row` / `tron::store_block` (like the PARENT's `tron::append_v_row`, `tron::load_row`, `tron::copy_token`, overloading on the view type) or `tron::k_vnni::` (where `index`, `layout_on` and the constants stay per the design). The proposed test code assumes `tron::` for operations and `tron::k_vnni::` for constants, `index`, `layout_on` and `qk_group`.
- Who authorizes and runs `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics` on delphi-3bda (whole host, 1/2/4 slices; design S20)? Until then the PR body records the deferral and the unrefreshed platforms (genoa96, genoa32, granite_rapids_6960p).
- Should the Typed-boundary case also assert `offsetof(kv_block_t, v) == sizeof(k_vnni_owner_t)` ('unchanged K/V offsets and block size' in the design)? kv_block is standard-layout so offsetof is defined; left out of the proposal as COULD pending the kv_cache.hpp owner's own static_asserts.
- The test-benchmarks.json t_amx_dispatch_dtype rows are identical on both sides (0.778/0.775/0.873); no remeasurement is requested for it. Confirm that the CHILD's extra fakes do not change its runtime materially (they are counted, not timed).
