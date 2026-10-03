# h/tron/models/model.hpp, h/tron/scheduler/full.hpp, h/tron/gof.hpp, src/tron/gof.cpp, h/tron/models/common.hpp, ingest/src/TronCpp.hs, ingest/test/LoopyTronSpec.hs (merge of PR 4557 c12df586b6 into PR 4424 30c4ac82cb, worktree /home/jhan/workspace/ai-runs/tron-vnnik-typed)

## textual_conflicts
- h/tron/models/common.hpp 3-8 (HEAD side `#include <array>` + `#include <atomic>`; origin/jhan-kv-typed-tensors side `#include <algorithm>`): Keep all three includes, alphabetical: <algorithm>, <array>, <atomic>, then the common <compare>, <cstdint>, <span>. Evidence: <array>/<atomic> are the CHILD's (diff c7844ca2ce..origin/jhan-amx-vnniK adds them for `struct k_store_window_t`: `std::atomic<uint32_t> next_unit/opened/finished` and `std::array<uint32_t, ...> unit_start/helper_windows`, worktree common.hpp:1134-1153). <algorithm> is not PARENT code at all: PARENT's diff 996f58ec82..origin/jhan-kv-typed-tensors on common.hpp is empty; it came from main commit 362365b9ca 'HW attention: stream the join as passes complete' (c7844ca2ce..996f58ec82), which added `std::max` and `std::find_if` to common.hpp. Both sides' includes have live users. NOTE: while this analysis ran, the worktree's markers disappeared and common.hpp now reads exactly this union (lines 3-8) with status 'M ' (someone else resolved it; this agent wrote nothing). The resolution now in the worktree is the correct one.

## semantic_changes
- [MUST] h/tron/models/model.hpp @ store_k_block, scatter path, worktree lines 2936 and 2940: `pg.template set_k_row<geometry.kv>(slot, kv_head, j, kout.data)` and `... (slot, kv_head, j, conv[0])`
  CHANGE: Pass a typed read-only row instead of a raw `const bf16*`: `const_view<bf16, VIEW_ALIGNED_TRUE, k_buffer_t::dma, seq<geometry.kv.head_size>, sseq<1>>{kout}` for the bf16 buffer branch (constructed from the `view` via `const_view(view const&)`, view.hpp:385), and `const_view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<geometry.kv.head_size>, sseq<1>>{conv[0]}` for the converted branch (alignas(64) stack array). Add `using k_buffer_t = std::remove_cvref_t<decltype(ks[token_job_id(0)])>;` next to `row_of`, mirroring the PARENT's `v_buffer_t` at save_v_impl (worktree model.hpp:3122).
  WHY: Design table 'page::set_k_row, page::get_k_row': set_k_row takes `const_view<bf16,Aligned,Dma,seq<D>,sseq<1>>`; 'Construct read-only source views explicitly in model save paths ... Template deduction does not use the conversion from a writable view or raw pointer to const_view.' Goal (c): no raw bf16* K-plane pointer crossing the cache boundary. Compile necessity once the kv_cache area changes set_k_row's parameter type.
  EVIDENCE: CHILD kv_cache.hpp:1701-1703 (origin/jhan-amx-vnniK) `set_k_row(kv_slot_id, size_t, size_t, const bf16* row)`; worktree model.hpp:2936/2940 pass `kout.data` / `conv[0]`. `kout` = `slice<head_size>()(ks[ix].as_view(), kv_head*head_size)` keeps the source view's aligned/dma (slice.hpp:48-76 returns `view<T, aligned, dma, ...>`), and the executor tensors expose `static constexpr bool dma` (tensor.hpp:35 false, dmatensor.hpp:38 true), exactly what the PARENT uses as `v_buffer_t::dma` at model.hpp:3135. Rank-1 `view` has no static aligned/dma members (view.hpp:116-125), so the type must be spelled.
- [MUST] h/tron/scheduler/full.hpp @ k_head_fn lambda, worktree lines 2747-2763, VNNI branch `pg_ptr->template get_k_row<hw_kv>(slot, kv_head, off, dest);`
  CHANGE: Wrap the caller-owned scratch in the typed destination row: `pg_ptr->template get_k_row<hw_kv>(slot, kv_head, off, view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<hw_kv.head_size>, sseq<1>>{dest}); return dest;` (same shape as the PARENT's V callback at worktree full.hpp:2771-2774, which calls `v_destination_row<head_size>(dest)`). Keep the `else` branch `return pg_ptr->template k<hw_kv>(slot, kv_head, off).data;` unchanged: page_info is the bf16* hardware boundary that the PARENT kept ('the parent keeps native K directly readable', design line 473).
  WHY: Design table 'page::set_k_row, page::get_k_row': load takes `view<bf16,Aligned,Dma,seq<D>,sseq<1>>`, 'Wrap scratch without copying'. Design 'hardware::page_info K callback: Add the child's scratch parameter' is already satisfied by the merge (see evidence). Compile necessity once get_k_row's parameter becomes a view.
  EVIDENCE: Merged full.hpp is a clean union: worktree vs CHILD diff = PARENT+main changes only (hunks at 2766-2774 = v_destination_row), worktree vs PARENT = the CHILD's k_head_fn rewrite. gof.cpp:203 (CHILD, unchanged in worktree) hands `k_scratch.data() + h * HW_BAKED_HEAD_SIZE` from an `alignas(64) std::array<bf16, HW_MAX_KV_HEADS * HW_BAKED_HEAD_SIZE>`; HW_BAKED_HEAD_SIZE*sizeof(bf16) = 256 bytes per head, so every per-head pointer is 64-byte aligned and the VIEW_ALIGNED_TRUE precondition holds.
- [MUST] h/tron/models/model.hpp @ whole file (semantic check of the auto-merge, task 1)
  CHANGE: No change needed for the merge itself. Verified: the merged model.hpp is an exact textual union. `git diff origin/jhan-amx-vnniK -- model.hpp` = 88 changed lines = `git diff c7844ca2ce origin/jhan-kv-typed-tensors -- model.hpp` (main movement + PARENT's 28-line save_v change). `git diff origin/jhan-kv-typed-tensors -- model.hpp` = 312 changed lines = CHILD's diff (307+14 minus overlap-free). Every K write: native branch `pg.template k<geometry.kv>(...).set(row_of(...))` (2889), VNNI scatter `set_k_row` (2936, 2940), VNNI block `set_k_block(..., present, rows)` (2957); every V write: `set_v(..., v_source_row<head_size, v_buffer_t::dma>(&vs[ix][...]))` under TRON_CHUNK_SIZE==16 (3134-3136) and `v<geometry.kv>(...).set(slice...)` otherwise (3138-3140). Marks/credits: mark_k_complete 3065 after the join (CHILD intent), mark_v_complete 3143 (PARENT intent). No line drops either side.
  WHY: Task item (1).
  EVIDENCE: Line counts above; grep of worktree model.hpp for save_k_impl/save_k_helper/store_k_block/set_k_row/set_k_block/set_v/v_source_row/mark_*_complete (lines 2748-3167).
- [MUST] h/tron/gof.hpp, src/tron/gof.cpp @ page_info::k_head_fn signature (gof.hpp:61-78 CHILD) and gof::populate k_scratch (gof.cpp:203, 213 CHILD)
  CHANGE: No change. Both files are byte-identical to CHILD in the worktree (`git diff origin/jhan-amx-vnniK -- h/tron/gof.hpp src/tron/gof.cpp` empty) and PARENT/main did not touch them (`git diff c7844ca2ce 996f58ec82 -- ...` empty, PARENT diff empty). The three-parameter `std::function<bf16*(kv_slot_id, size_t, bf16* scratch)> k_head_fn` is the design's 'add the child's scratch parameter' and matches the full.hpp lambda `[pg_ptr, off](kv_slot_id slot, size_t kv_head, bf16* dest) -> bf16*`.
  WHY: Task item (3); design line 475 'Keep the parent's hardware::page_info K callback shape. The extra K scratch parameter belongs to the child. [S9]' and the child table row 'hardware::page_info K callback'.
  EVIDENCE: CHILD diffs shown: gof.hpp +18/-5 (comment + signature), gof.cpp +2/-1 (k_scratch array and the call).
- [MUST] ingest/src/TronCpp.hs, ingest/test/LoopyTronSpec.hs @ runHelperStatement AttentionStmt branch (worktree TronCpp.hs:2326-2342), submitAttentionOperation saveKv (2401-2407), attentionRuntimeCall (2425-2432); LoopyTronSpec.hs 2866-2881 and 3290-3297
  CHANGE: No generator change is needed for the typed-K port. The PARENT did not touch either file (PARENT diff from 996f58ec82 is empty for both). The merge is a clean union: TronCpp.hs worktree-vs-CHILD = 191 lines = main's c7844ca2ce..996f58ec82 change; worktree-vs-PARENT = 25 lines = CHILD's 22+3. LoopyTronSpec.hs: 141 = main, 28 = CHILD's 26+2. main's hunks adjacent to the CHILD's edits are type-signature spelling only (`Name Buffer` -> `Name ('Tron 'Buffer)` at attentionChannel/matmulFill; removal of MoeExpertViewInitStmt arms). Generated text vs C++: run() emits `outer_state.template save_k<geometry,ix>(q_batch->outer_batch, k, n_workers);` = 3 arguments, declaration `save_k(batch* q_batch, kv_buffer_t& ks, size_t n_workers = 1)` (worktree model.hpp:3081) = 3 parameters. run_main_help emits `outer_state.template save_k_helper<geometry,ix>(q_batch->outer_batch, k, worker_ix, n_workers);` = 4 arguments, declaration `save_k_helper(batch*, kv_buffer_t& ks, size_t worker_ix, size_t n_workers)` (model.hpp:2969-2970) = 4 parameters. The spec assertions encode exactly these tails (`q_batch->outer_batch,k,n_workers);` at 2873, `q_batch->outer_batch,k,worker_ix,n_workers);` at 2879, `,k,n_workers);` 3292, `,k,worker_ix,n_workers);` 3297). main's new prefix-only assertions (`attentionCallPrefix method geometry 0`, 2889-2900 and 3095-3107) and `Txt.count "outer_state.template save_k<" ... 1` are compatible ("save_k_helper<" does not match "save_k<").
  WHY: Task items (5) and (6).
  EVIDENCE: attentionRuntimeCall (worktree TronCpp.hs:2425-2432) emits `TemplateMethodCall (Var "outer_state") method (attentionOperationTemplateArgs stmt) (ExprLit "q_batch->outer_batch" : args)`; args lists quoted above from worktree lines 2342 and 2407.
- [SHOULD] h/tron/models/model.hpp, h/tron/scheduler/full.hpp, h/tron/gof.hpp @ Comments pointing at `Note [K VNNI storage] in kv_cache.hpp`: model.hpp:2752, full.hpp:2753, gof.hpp:71 (CHILD numbering 68-71)
  CHANGE: If the kv_cache/k_vnni area moves Note [K VNNI storage] into h/tron/tensor/k_vnni.hpp (design: 'The mapping, scatter/gather/block-store bodies, plane view ... become local to h/tron/tensor/k_vnni.hpp'), update these three cross-references to the new file. If the Note stays in kv_cache.hpp, no change.
  WHY: Design rule (4): comments stay accurate; the PARENT did the same for Note [VNNI Packed V layout] (model.hpp:214, 3114 now name h/tron/tensor/v_vnni.hpp).
  EVIDENCE: grep of worktree for 'Note [K VNNI storage]': model.hpp:2752, full.hpp:2753, gof.hpp:71, kv_cache.hpp:~659 (the Note body, CHILD).
- [SHOULD] h/tron/models/model.hpp @ store_k_block block path, worktree lines 2951-2957: `const bf16* rows[K_STORE_BLOCK_16] = {}; rows[run_t[i]] = kout.data; ... set_k_block(slot, kv_head, c, present, rows)`
  CHANGE: Keep as is. The design keeps `const bf16* const rows[BLOCK_TOKENS_16]` for set_k_block ('Preserve const bf16* const rows[BLOCK_TOKENS_16] for 16 independent native source rows, with null entries for absent lanes. ... These source-row pointers do not expose packed storage.'). These are activation-row pointers (native layout), not K-plane pointers, so goal (c) is not violated. Only add braces to any brace-less loop bodies the PARENT rule (3) would flag; the CHILD's loops here already have braces.
  WHY: Consistency with the design table row 'page::set_k_block'; avoids inventing a typed 16-row argument the design explicitly does not ask for.
  EVIDENCE: Design child table, row page::set_k_block; worktree model.hpp:2951-2957.
- [COULD] h/tron/scheduler/full.hpp @ includes, lines 3-38
  CHANGE: Include the K tensor header (h/tron/tensor/k_vnni.hpp after the split) directly, since the k_head_fn lambda names `k_vnni::layout_on<hw_kv.head_size>` (worktree 2751). Today it is reached transitively through model.hpp -> kv_cache.hpp -> kernels/k_vnni.hpp. Not a compile necessity: the design keeps 'The cache includes the K tensor header', so the transitive path survives the split.
  WHY: Consistency only (the file already includes tron/gof.hpp directly for page_info).
  EVIDENCE: worktree full.hpp:3-38 include list has no k_vnni header; kv_cache.hpp:27 (CHILD) includes tron/kernels/k_vnni.hpp.
- [COULD] h/tron/models/model.hpp, ingest/src/TronCpp.hs, ingest/test/LoopyTronSpec.hs, t/t_llama_unit.cpp @ Design 'Worker-index request': merge save_k/save_k_helper into `save_k(..., worker_ix = 0, n_workers = 1)`; generated run() passes `0, n_workers`, run_main_help calls save_k with `worker_ix, n_workers`; 7 spec assertions (worktree 2866-2881, 3290-3297) and the three-thread calls in t_llama_unit.cpp (CHILD 2767-2784)
  CHANGE: Defer to a separate commit or drop. It is orthogonal to the typed-K goal (a)-(d), has no reviewer source (ben-review-5270587330 and the API sketch never mention worker indices; design tags it [S18] = 'pinned child sources', i.e. the design's own choice), and it IS a generator change, contradicting the task's item (6). If the user wants it, the exact edits are: model.hpp 3081/3089 signatures gain `size_t worker_ix = 0` before `n_workers`, save_k_helper bodies fold into save_k_impl behind `if (worker_ix != 0)`, TronCpp.hs:2340 `"save_k_helper"` -> `"save_k"`, TronCpp.hs:2407 args gain `ExprLit "0"`, spec counts of `save_k<` become 2 and `save_k_helper<` go away, t_llama_unit three-thread section calls save_k with worker_ix.
  WHY: Design lines 576-582 vs task item (6) and the PARENT body ('The packed-K half of each point waits for #4424' lists only typing points).
  EVIDENCE: Design text lines 576-582 [S18]/[S21]; ben review/sketch files; pr4557-body.md Response table.

## proposed_code
// h/tron/models/model.hpp, store_k_block (worktree lines ~2877-2895 and 2933-2941).
// Mirrors the PARENT's save_v_impl pattern (v_buffer_t::dma, model.hpp:3122/3135).
auto row_of = [&](token_job_id ix, size_t kv_head) {
  return slice<geometry.kv.head_size>()(ks[ix].as_view(), kv_head * geometry.kv.head_size);
};
// The executor's K buffer holds bf16 (btensor), fp16 (htensor) or float (tensor);
// its dma flag travels with the row view. slice keeps the buffer's alignment.
using k_buffer_t = std::remove_cvref_t<decltype(ks[token_job_id(0)])>;
// One token's K row, read-only, in dimension order (not packed storage).
using const_k_source_row =
    const_view<bf16, VIEW_ALIGNED_TRUE, k_buffer_t::dma, seq<geometry.kv.head_size>, sseq<1>>;
using const_k_conv_row =
    const_view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<geometry.kv.head_size>, sseq<1>>;
...
if (n == K_SCATTER_RUN_LEN_1) {
  for (size_t i = 0; i < n; ++i) {
    const size_t j = c * K_STORE_BLOCK_16 + run_t[i];
    for (size_t kv_head = 0; kv_head < geometry.kv.n_kv_heads; ++kv_head) {
      auto kout = row_of(run_ix[i], kv_head);
      if constexpr (rows_are_bf16) {
        // const_view(view const&) (view.hpp:385): no raw pointer crosses here.
        pg.template set_k_row<geometry.kv>(slot, kv_head, j, const_k_source_row{kout});
      } else {
        view<bf16, true, false, seq<geometry.kv.head_size>>{conv[0]}.set(kout);
        pg.template set_k_row<geometry.kv>(slot, kv_head, j, const_k_conv_row{conv[0]});
      }
    }
  }
} else {
  // unchanged: const bf16* rows[K_STORE_BLOCK_16] + pg.set_k_block(slot, kv_head, c, present, rows)
}

// h/tron/scheduler/full.hpp, k_head_fn (worktree lines 2747-2763)
pi.k_head_fn = [pg_ptr, off](kv_slot_id slot, size_t kv_head, bf16* dest) -> bf16* {
  constexpr kv_geometry hw_kv = model_t::hardware_attention_geometry.kv;
  if constexpr (k_vnni::layout_on<hw_kv.head_size>) {
    // dest is page_info's caller-owned, 64-byte-aligned scratch (gof.cpp k_scratch,
    // 256 bytes per head). The packed row is gathered into it (get_k_row -> load_row).
    pg_ptr->template get_k_row<hw_kv>(slot, kv_head, off,
        view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<hw_kv.head_size>, sseq<1>>{dest});
    return dest;
  } else {
    (void)dest;
    return pg_ptr->template k<hw_kv>(slot, kv_head, off).data;  // native row, FPGA boundary (kept by the PARENT)
  }
};

// If the kv_cache/k_vnni area prefers named aliases (like const_v_row_view / v_row_view in
// h/tron/tensor/v_vnni.hpp:210-226 from PR 4697), use them here instead of the spelled types:
//   template <typename T, size_t Cols, bool Aligned, bool Dma> using const_k_row_view = const_view<T, Aligned, Dma, seq<Cols>, sseq<1>>;
//   template <typename T, size_t Cols, bool Aligned, bool Dma> using k_row_view = view<T, Aligned, Dma, seq<Cols>, sseq<1>>;
// The call sites above then read const_k_row_view<bf16, head_size, VIEW_ALIGNED_TRUE, k_buffer_t::dma>{kout}.

// common.hpp lines 3-8 (resolution; already present in the worktree now):
#include <algorithm>
#include <array>
#include <atomic>
#include <compare>
#include <cstdint>
#include <span>

## design_contradictions
- Design lines 576-582 ('Worker-index request': merge save_k/save_k_helper into save_k(..., worker_ix = 0, n_workers = 1); generated run() passes 0, n_workers; run_main_help calls save_k; 7 LoopyTronSpec assertions change) requires a generator change. The task's item (6) asks to confirm that nothing in the port needs a generator change. For the typed-K goal (a)-(d) that confirmation holds: the PARENT did not touch TronCpp.hs/LoopyTronSpec.hs, the merged generator emits calls that match the merged model.hpp signatures (3 and 4 arguments), and no K typing flows through generated code. The worker-index merge is a separate, design-only request with no reviewer source (ben-review-5270587330 and the sketch do not mention it; the design tags it [S18] = pinned child sources).
- Design table 'page::set_k_row': 'Use const_view<bf16,Aligned,Dma,seq<D>,sseq<1>> ... The boolean template arguments preserve the caller's alignment and DMA properties' implies deducing Aligned/Dma from the argument. A `view` argument cannot deduce a `const_view` parameter (different templates; const_view's converting constructor view.hpp:385 is not used in deduction, as the design itself says). So the model.hpp call site must spell the const_view type, which needs Aligned/Dma as compile-time facts. The rank-1 `view` has no static aligned/dma members (view.hpp:116-125), so the only sources are the buffer type's `static constexpr bool dma` (tensor.hpp:35, dmatensor.hpp:38) plus the slice's alignment guarantee (slice.hpp:48-63 asserts a 32-byte-multiple offset and keeps `aligned`). This is the PARENT's own pattern (`v_buffer_t::dma`, model.hpp:3135), so it is consistent, but it means 'preserve the caller's alignment' is realised by the caller asserting VIEW_ALIGNED_TRUE, not by deduction.
- Design line 475 says 'Keep the parent's hardware::page_info K callback shape' while the child table says 'Add the child's scratch parameter'. These are consistent in time (parent = 2-arg, child = 3-arg) and the merge already yields the 3-arg child shape (gof.hpp identical to CHILD, PARENT/main never touched gof.hpp/gof.cpp). No action, stated here so nobody 'restores' the 2-arg form.

## risks
- The worktree state changed during this analysis: at start, 7 files were 'UU' with markers (common.hpp lines 3-8 shown); at the end all 7 are staged 'M ' with 0 markers. Another actor resolved them. Any file:line numbers quoted for kv_cache.hpp/self_attention.hpp in this report are from the CHILD ref, not the worktree. Re-run `git -C <worktree> status` before building on this report.
- The two MUST call-site edits (model.hpp set_k_row arguments, full.hpp get_k_row argument) depend on the kv_cache area actually changing set_k_row/get_k_row to typed row parameters. If that area keeps `const bf16* row` / `bf16* row`, the edits above will not compile; if it changes the signatures and model.hpp/full.hpp are not edited, the build breaks there. The two areas must land in the same commit.
- The PARENT's `v_source_row` wraps `&vs[ix][kv_head * head_size]`, a raw element pointer, while the proposal here constructs the K const_view from the slice `view` (no raw pointer). If the kv_cache area adopts named K row aliases taking a pointer (like v_source_row), the K path would reintroduce a raw-pointer hop in model.hpp. Prefer the view-constructed form or a helper that takes a `view`.
- If the kernel header split moves Note [K VNNI storage] out of kv_cache.hpp, three comments in this area (model.hpp:2752, full.hpp:2753, gof.hpp:71) become stale; plain-English rule (4) treats stale cross-references as defects.
- The design's worker-index merge, if done later as a stacked change, will touch exactly the generator lines and spec assertions that PR #4737 (origin/jhan-amx-vnniK-i4500, row-major tail block) may also touch. Nothing in this area's typed-K port blocks #4737's later merge: model.hpp save_k/save_k_helper signatures, the generator, and the spec are left as CHILD has them.
- gof.cpp consumes k_heads[h]/v_heads[h] inside the same `pos` iteration before the next token overwrites k_scratch (design [S14] scratch lifetime). This is unchanged CHILD code that passed the CHILD's tests; it was not re-read line by line here.

## open_questions
- Does the kv_cache/k_vnni area want named K row aliases (const_k_row_view / k_row_view, analogous to PR 4697's const_v_row_view / v_row_view in h/tron/tensor/v_vnni.hpp:210-226) or spelled const_view/view types at the model.hpp and full.hpp call sites? The proposal here compiles either way once the alias template parameter order is fixed; the aliases need an Aligned parameter that V's do not have (design: 'These K routines do not acquire V's stronger alignment requirement').
- Is the design's worker-index merge (save_k with worker_ix, generator + 7 spec assertions + t_llama_unit three-thread calls) in scope for this sync, or deferred? It is the only item in this area that would require a generator change, and it is not needed for typed K.
- Where will Note [K VNNI storage] live after the header split (kv_cache.hpp or h/tron/tensor/k_vnni.hpp)? Three comments in this area reference its location.
- Who resolved the 7 conflicted files in the worktree during this run, and from which design decisions? This area's analysis of common.hpp agrees with the resolution now present, but the other six files were not reviewed here.
