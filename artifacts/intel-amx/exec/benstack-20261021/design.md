# Design brief v2: PRs 4957, 4958, 4959 re-expressed on PR 5047's structure

Version 2 (2026-10-21, after the prediction workflow: 82 kept findings in findings-4957/4958/4959.md, four critics in
wfA-critics.md). Version 1 is design-v1.md. Changes from v1 are marked [v2].

Words used here: tron = the inference program; the cache = h/tron/models/kv_cache.hpp (struct page, struct book);
the option = CMake option TRON_K_VNNI; a VNNI slot = a K storage slot of a 128-dimension head when the option is on;
the kernel = the AMX QK kernel qk_vnni_128x4; the reader = k_vnni::qk_group (AVX-512 scoring of the VNNI plane); the
dotter = the per-token AVX-512 dot product over a row-major row; a block = 16 consecutive tokens of a 64-token KV page;
a lane = one of the 16 token positions of a block; a run = consecutive minibatch items inside one block of one page;
the window = the shared K store of one (layer, pass) in which the main helpers take part; the barrier = tron::barrier
(h/tron/threading.hpp Note [Resettable Barrier Design]); P1-P5 / C1-C16 = the items of ben-profile.md.

## 1. The stack and the new branches

| PR | title | PR branch | head | base | new branch (worktree) |
|---|---|---|---|---|---|
| 4956 | Add the VNNI K layout and its readers | jhan-vnnik-1-layout | a5697f86d3 | main | (Ben's PR 5047 targets this branch) |
| 5047 | Ben: self_attention token selection + kv_cache hides the K layout | bgamari/vnnik-1 | ade89a9d9c | jhan-vnnik-1-layout | (worktree ~/workspace/ai-runs/tron-pr5047, read-only reference) |
| 4957 | Use VNNI K layout in AMX attention | jhan-vnnik-2-amx | 26b86a279a | jhan-vnnik-1-layout | jhan-vnnik-2-amx-5047 (~/workspace/ai-runs/tron-ben-pr2) |
| 4958 | Save K in 16-token blocks, shared with idle worker threads | jhan-vnnik-3-shared-save | b39765ec29 | jhan-vnnik-2-amx | jhan-vnnik-3-shared-save-5047 (~/workspace/ai-runs/tron-ben-pr3) |
| 4959 | Keep short K writes row-major; enable VNNI K in the deb preset | jhan-vnnik-4-tail-block | 6b081187e1 | jhan-vnnik-3-shared-save | jhan-vnnik-4-tail-block-5047 (~/workspace/ai-runs/tron-ben-pr4) |

Merge base of every stack branch with Ben's head = a5697f86d3. Simulated merges of Ben's head (git merge-tree):
4957: 6 conflict hunks (kv_cache.hpp 2, self_attention.hpp 3, t_amx_dispatch_dtype.cpp 1);
4958: 9 (kv_cache 3, model 1, self_attention 3, tensor/k_vnni 1, t_amx_dispatch_dtype 1) of which 4 are PR 4958's own
(the rest are PR2' work: the real PR3' merge is against the finished PR2' branch);
4959: 13 (kv_cache 4, model 1, self_attention 5, scheduler/full 1, tensor/k_vnni 1, t_amx_dispatch_dtype 1); the real PR4'
merge is against the finished PR3' branch, so store_k_block / set_k_block conflicts differ from the simulation.
Files that merge without markers but still need care: t/t_llama_unit.cpp, t/heterogeneous_scheduler_compile.cpp.

The new branches are stacked like the PRs: pr2 branch = jhan-vnnik-2-amx + merge of origin/bgamari/vnnik-1 + changes;
pr3 branch = jhan-vnnik-3-shared-save + merge of jhan-vnnik-2-amx-5047 + changes; pr4 branch = jhan-vnnik-4-tail-block +
merge of jhan-vnnik-3-shared-save-5047 + changes. Draft PRs will target the PR branches (jhan-vnnik-2-amx, ...).

Reference material (scratchpad/stack/): pr4957.diff, pr4958.diff, pr4959.diff, pr495N-body.md, ben-corpus.md,
ben-profile.md, findings-495N.md (verified predictions with remedies), wfA-critics.md; ../pr5047.diff,
../pr5047-c1.diff, ../pr5047-c2.diff (Ben's commits); Ben's tree at ~/workspace/ai-runs/tron-pr5047 (do not modify);
PR heads at ~/workspace/ai-runs/tron-split-pr2/3/4 (do not modify).

## 2. Ben's structure at ade89a9d9c (what the merges must preserve)

- page::score_k<geometry>(slot, kv_head, q, uint64_t live, float* scores, size_t stride) const: VNNI slot -> the reader
  over `live`; row-major slot -> the dotter array over the live bits (kv_cache.hpp:1978-2007).
- page::try_score_k_amx<geometry>(slot, kv_head, const bf16* q_packed, float* scores, stride) const (under
  TRON_AMX_DISPATCH): VNNI slot -> `return false` (no AMX reader yet); row-major -> qk_rowmajor_128x4 (2015-2031).
- page::set_k_row(slot, kv_head, i_page, const_k_row_view) and set_k_row(slot, kv_head, i_page, const expr<X,dims>&)
  (converts on the stack for a VNNI slot, `k_at(i_page).set(row)` for row-major) (2035-2065); get_k_row (2071).
- page::kv_block(slot, kv_head) is PRIVATE (2233 private:, 2264-2290). page::k() (8 overloads) and page::k_packed are
  gone. save_k (model.hpp:3096-3101) is one set_k_row call per (token, kv_head). full.hpp k_head_fn (2747-2753) always
  get_k_row into caller scratch (a copy for row-major slots; measured inside the band in every FPGA cell, section 5).
- self_attention.hpp: packed_amx_query (1684-1700) calls pack_q_group_128x4; apply_dense_amx_page (1734-1806) asks
  try_score_k_amx and returns false when declined; apply_page_tok (1819-1920): the loop fills `live`, then one score_k
  call. No k_vnni::layout_on in self_attention.hpp, model.hpp, full.hpp.
- Tests: t/kv_cache_helpers.hpp set_k_tag/k_tag; t_llama_unit probes page_k_accepts_geometry (set_k_row with a row view)
  and STATIC_REQUIRE_FALSE(page_k_packed_accepts_geometry).
- Existing primitives the stack must reuse instead of re-implementing [v2]:
  tron::barrier (threading.hpp:883-975: reset(n_participants), next_phase(action), wait(participant_ix),
  done(participant_ix), wait_for_all(); already a batch member as free_scratchpads_barrier, reset per pass in
  batch::reset_channels(n_attn_workers, n_main_workers) at common.hpp:1071-1074; the generated run() passes
  n_workers = 1 + n_main_helpers as n_main_workers before it launches the helpers, TronCpp.hs:1358-1392);
  greedy_range (threading.hpp: dynamic work assignment over an std::atomic_size_t counter, chunk 1 = one unit per claim);
  latch waits are acquire loads (h/system/mwaitx.hpp:190-203) and count_down is acq_rel; TRON_LATCH_WATCHDOG (a logging
  watchdog thread for every latch, threading.hpp:174-240). view<T,...,seq<d0>,sseq<s0>> default-constructs to an invalid
  view (data == nullptr) and has valid() (view.hpp:116-140).
- Known defects of Ben's head that the merged branches must not inherit:
  (d1) t/heterogeneous_scheduler_compile.cpp:687-689 still calls page->k<software_geometry.kv>(slot, 0, 0)[i] for
       i < 256 (zeroes one 256-dim row) -> GitHub "Build Tron" is red. Fix: a zero row through the page operation the
       test already uses for V three lines above: `alignas(64) std::array<bf16, software_geometry.kv.head_size> zeros{};
       page->set_k_row<software_geometry.kv>(slot, 0, 0, k_source_row<software_geometry.kv.head_size>(zeros.data()));`
       (test::set_k_tag(..., bf16(0.0f)) would also zero the row but reads as "tag with 0"). At PR 4959's head the
       same lines sit at :722-723; the fix arrives in PR4' through the merge (verify with grep '->k<').
  (d2) t_llama_unit.cpp:118-120 page_k_accepts_raw_index names Page::head_size; page has no such member (its members
       are layout_t and page_size, kv_cache.hpp:1874-1881), so the requires-expression is false for every Page and
       STATIC_REQUIRE_FALSE(:391) passes vacuously. Fix: k_row_view<Page::layout_t::primary_geometry.head_size> plus a
       positive control (the same probe with kv_slot_id(0), asserted true) so the negative cannot pass for the wrong
       reason. Also at Ben's head: page_k_packed_accepts_geometry (:106-110) is dead in every build (k_packed is gone)
       and its STATIC_REQUIRE_FALSE passes vacuously; delete it or replace it by a probe that page::kv_block is not
       public (a requires-expression on a private member is false).
  (d3) stale comments: self_attention.hpp:1723-1727 ("so this function always applies the page"; it returns bool now),
       :1750-1751 ("A layout without an AMX reader declines before any attention state is changed"), :1869-1872 ("The
       cache can decline if it has no AMX reader for its K storage"), kv_cache.hpp:2009-2011 (try_score_k_amx doc
       "when the K layout has no AMX reader"), gof.hpp:61-67 (says the staging pointer is into the page when the row is
       contiguous; K now always arrives in the caller's scratch). All fixed in PR2' (the merge touches these files).

## 3. Target per PR

### PR2' = jhan-vnnik-2-amx-5047 (worktree ~/workspace/ai-runs/tron-ben-pr2): "the VNNI AMX kernel behind the cache"

Goal: PR 4957's content (qk_vnni_128x4, pack_q_rows_128x4, bit-identity test, dispatch test, comments) with zero layout
knowledge outside the cache: the cache chooses the kernel AND the query operand format, in one place.

Commit 1 [v2: resolved so that every commit is green for t_amx_dispatch_dtype]:
`git merge origin/bgamari/vnnik-1` (message: "Merge branch 'bgamari/vnnik-1' into jhan-vnnik-2-amx-5047", body names
the resolutions). Resolution rules:
   - kv_cache.hpp: Ben's code side. Resolve the try_score_k_amx hunk by putting PR 4957's kernel call inside the VNNI
     branch (this is the resolution of the self_attention.hpp kernel-call hunk, whose 4957 side is exactly that call):
     `amx_attn_h128g4::qk_vnni_128x4(kv_block<geometry>(slot, kv_head).k.as_view(), q_packed, scores, stride);
     return true;` (try_score_k_amx is const, so the const kv_block overload yields k_vnni_view<const bf16, 64, 128>,
     the kernel's parameter type). Drop PR 4957's k_packed comment above it; check the #ifdef TRON_AMX_DISPATCH /
     #endif pair. Note [K VNNI storage] items 2-3 reworded (Ben's shape, 4957's facts):
       item 2: "page::try_score_k_amx passes the plane view the cache holds (kv_block::k.as_view()) to qk_vnni_128x4;
       the caller applies the page with the AMX PV kernel."
       item 3: "page::score_k runs k_vnni::qk_group for every other visit of a VNNI slot: partial or partly visible
       pages, the kill switch (TRON_AMX_DISABLE=1), hosts without AMX, builds without TRON_AMX_DISPATCH, and shapes and
       query types outside the AMX gate. That reader is AVX-512 code with one token per vector lane. It needs no
       per-token gather and no horizontal reduction. The dotter loop of score_k runs only for row-major slots.
       Attention code supplies queries and a live-token mask, not a layout."
     (keep Ben's last sentence; the phrase "of self_attention.hpp" must not survive). 4957's removal of "Until the
     VNNI AMX kernel is merged ..." merges without a marker and is right.
   - self_attention.hpp: Ben's side of all three conflict hunks (apply_dense_amx_page comment, kernel call, AMX-gate
     comment). PR 4957's packer `if constexpr` in packed_amx_query merges without a marker and STAYS in this commit
     (commit 2 moves it). Keep PR 4957's comment edits that are still true.
   - t_amx_dispatch_dtype.cpp: PR 4957's fakes (pack_q_rows_128x4, qk_vnni_128x4, rows_pack_calls), its `dense`
     predicate, and its side of the header hunk only (Ben's header sentence "declines the dense AMX page path ..." is
     false once the kernel runs; there is no Ben text to keep). Keep 4957's "(Note [K VNNI storage] in kv_cache.hpp)"
     reference. The test's own k_vnni::layout_on in the rows_pack_calls expectation is test code and stays.
   - t_llama_unit.cpp: merges without a marker (4957's six amx_qk_vnni_accepts probes land; Ben's deletion of the
     k_packed decltype block wins). Verified; nothing to resolve.
   - tensor/k_vnni.hpp header: the automatic merge gives the wanted wording; extend the accessor list to
     "(page::set_k_row, page::get_k_row, page::score_k, page::try_score_k_amx)".
   - kernels/k_vnni.hpp, amx_attn_iface.hpp, amx_attn.cpp, t_amx_numerics.cpp, README.ci.md: merge cleanly.
   - ingest/src/TronCpp.hs, LoopyTronSpec.hs: nothing (the only K reference is the generated save_k call, unchanged).
   - hetero test: the merge brings Ben's kv_cache_helpers.hpp include and set_k_tag rewrites without conflict; d1 is
     fixed in commit 3.

Commit 2 "kv_cache: the page picks the query packer with the kernel" [v2: name, requires clause, comments]:
   - New static member directly ABOVE try_score_k_amx, same #ifdef TRON_AMX_DISPATCH:
     `template <kv_geometry geometry> requires(book_t::template declares_geometry<geometry>()) static void
     pack_q_amx(const bf16* q_group, bf16* packed) noexcept` with the same static_assert on head_size as
     try_score_k_amx. Body: pack_q_rows_128x4 for a VNNI slot (Q is the A operand), pack_q_group_128x4 otherwise (Q is
     the B operand). Comment: "Packs one query group as the operand try_score_k_amx expects for this geometry. The
     packer and the kernel are chosen together here; see Note [QK orientation]." Name: pack_q_amx follows Ben's page
     verbs (score_k, try_score_k_amx, set_k_row) and is not one letter away from the caller packed_amx_query (C1).
     Shape: two raw bf16 pointers = the packers' own shape; the attn_accum slot is a bf16 array; a typed packed-query
     view would be new machinery without a second user (C11).
   - self_attention.hpp packed_amx_query: `page::template pack_q_amx<geometry.kv>(group, slot);` and nothing else of
     code; the packer `if constexpr` and the k_vnni:: use go away (no k_vnni:: use remains in self_attention.hpp;
     Ben already dropped the dotter.hpp and kernels/k_vnni.hpp includes).
   - try_score_k_amx doc comment -> present-tense contract: "Score the dense page with the AMX QK kernel of the slot's K
     layout. Returns false, with scores and storage untouched, when the cache cannot score the page with AMX; the
     caller then scores it in software. q_packed is the output of pack_q_amx for the same geometry." (Do not say in a
     comment why no layout declines today; that goes in the PR body.)
   - Comment edits (d3 and the packer): self_attention.hpp :1723-1727 -> "The caller has already checked that a packed Q
     exists and that the page is dense (is_dense_amx_page). The cache may still decline; then this function returns
     false and has changed nothing."; :1750-1751 -> "Ask the cache to score the dense page. When it returns false
     nothing has been changed and the caller scores in software."; :1869-1872 -> "Try AMX only with a packed Q and a
     dense page. The cache may decline (try_score_k_amx returns false); then use software scoring."; amx_qpack_slot
     (:254-258) -> "One packed query group for the AMX attention path (the output of page::pack_q_amx): 4096 bytes.
     alignas(64) meets both packers' 64-byte alignment contract; ..."; keep 4957's resize() comment ("Both packers rely
     on the padding they do not write staying zero").
   - amx_attn_iface.hpp Note [AMX attention dispatch], one line under the diagram: "Both QK calls are made by the cache:
     page::score_k (AVX) and page::try_score_k_amx (AMX). Attention code passes queries, a live mask or a packed query,
     never a layout."
   (Line numbers are Ben's tree; find the text, not the number.)

Commit 3 "tests: fix the raw K access and the vacuous probe inherited from the K-layout refactor" (d1, d2, gof.hpp d3):
   - d1 and d2 as in section 2; gof.hpp:61-67 -> "K and V always arrive in the caller's scratch (page::get_k_row,
     page::get_v_row); the pointer the staging returns is the scratch row."  No named literals in these shared files.
   - PR body: "needed in PR 5047 too" with the exact lines, as a recommendation for jhan to post as suggestion comments
     on PR 5047 (not posted by the agents: GitHub posting is authorized only for the three branches and draft PRs).

Keep PR 4957's tests. README.ci.md: no change (verified: it names no removed accessor).

Verification for PR2' (beyond section 4): t_amx_dispatch_dtype expectations hold at every commit (pack 1, QK 1 for a
full page under the option); the two 3bda runs the syntax matrix cannot replace are t_amx_dispatch_dtype (option ON
and OFF, dispatch ON) and t_amx_numerics on the AMX host.

### PR3' = jhan-vnnik-3-shared-save-5047 (worktree ~/workspace/ai-runs/tron-ben-pr3): "shared block save through the cache"

Goal [v2]: PR 4958's content (block save, shared window, generated helpers' save_k call, tests) where every page
operation save_k calls exists for every slot and the cache chooses the physical store inside the operation; model.hpp
keeps exactly one layout fact (the sharing policy) and no layout code; the window uses tron::barrier and greedy_range
instead of hand-written counters.

Commit 1: `git merge jhan-vnnik-2-amx-5047`. Resolution rules:
   - self_attention.hpp, t_amx_dispatch_dtype.cpp: the PR2' side (PR 4958 does not touch them).
   - model.hpp hunk = PR 4958's side: delete Ben's per-token set_k_row(expr) loop inside the mark loop (store_k_block
     stores; keeping both would store every row twice).
   - kv_cache.hpp: Ben's code + PR2' code; PR 4958's set_k_block placed after set_k_row(expr) (reshaped in commit 2);
     Note item 1 from PR 4958 reworded (no page::k); verify Note item 2 carries PR2''s wording; no k_packed comment.
   - tensor/k_vnni.hpp accessor list = "(page::set_k_row, page::get_k_row, page::set_k_block, page::score_k,
     page::try_score_k_amx)".
   - t_llama_unit.cpp merges without markers. TronCpp.hs / LoopyTronSpec.hs: PR 4958's hunks, unchanged.
   Count the PR3' merge's own conflicts in the PR body (4 in the simulation).

Commit 2 "kv_cache: set_k_block serves every slot and converts inside the page":
   - ONE public signature: `template <kv_geometry geometry, typename Row> void set_k_block(kv_slot_id slot, size_t
     kv_head, size_t c, const std::array<Row, k_block_tokens>& rows) noexcept` where Row is the activation row view type
     (the type store_k_block's row_of returns) and an absent lane is a default-constructed (invalid) view. Inside:
     the lane mask comes from valid(); VNNI slot: one valid lane -> store_row (the scatter) of that row; otherwise
     store_block with the mask; bf16 rows are read in place (the k_source_row(view) overload, stride 1), other scalars
     are converted into a 16 x head_size bf16 stack block first (as Ben's set_k_row(expr) converts one row); row-major
     slot: `kv_block<geometry>(slot, kv_head).k_at(c * k_block_tokens + t).set(rows[t])` per valid lane (Ben's
     set_k_row(expr) body, 4 lines). The `const bf16* rows[16] + __mmask16` page overload is removed; the tensor-level
     store_block (h/tron/tensor/k_vnni.hpp) keeps its mask (t_k_vnni_layout calls it directly).
   - `static constexpr size_t k_block_tokens = k_vnni::BLOCK_TOKENS_16;` on page (the store granule; no geometry
     parameter, no sentinel). model.hpp's k_store_block becomes an alias of it.
   - `template <kv_geometry geometry> static constexpr bool k_store_scatters() noexcept` = k_vnni::layout_on<...>:
     "the per-row store of this layout scatters across 64 lines; sharing the store with idle helpers pays only then".
     Used once, by k_store_shared. (Replaces v1's k_block_tokens<geometry>() with its 0 sentinel: C7.)
   - Note [K VNNI storage] item 1 and the set_k_block comment ("VNNI slots only" is gone; the cache chooses store_row or
     store_block; the same operation serves every slot, Ben's item 6 stays true). amx_attn_iface.hpp:222-230 ("A run of
     two or more consecutive tokens ... uses the block save") reworded: the page chooses the block store for a run of
     two or more lanes.

Commit 3 "model: store_k_block has one flow; the run scan is next_k_run":
   - next_k_run(q_batch, t, task_end) -> a small struct (page*, block index c, lane set, item indices, count); the scan
     is PR 4958's (skip non-KV items, stop at another page, another block, a repeated offset, or 16 lanes).
   - store_k_block: for each run, for each kv_head: `std::array<Row, page::k_block_tokens> rows{}` filled at the run's
     lanes with row_of(ix, kv_head); `pg.template set_k_block<geometry.kv>(slot, kv_head, run.c, rows)`. No layout
     query, no __mmask16, no k_source_row / k_destination_row / conv / rows_are_bf16, no k_scatter_run_len (the cache
     decides). Row-major slots take the same path (the cache stores per lane). Bytes identical; the row-major path gains
     the run scan (a few ns per token, est.); sharing stays VNNI-only, so the OFF build's thread assignment is unchanged.
   - store_k_block's comment (model.hpp:3193-3199 at the PR head names page::k(...).set) rewritten.
   - model.hpp includes: remove <immintrin.h> and <chrono> if no user remains (they carry "(Note [Shared block save])").

Commit 4 "model: the K store window is a tron::barrier phase" [v2: replaces v1's open/enter/claim/finish/join type]:
   - batch (common.hpp): `barrier k_store_barrier;` constructed like free_scratchpads_barrier (name "k_store_barrier",
     index ix) and reset in reset_channels with n_main_workers: `k_store_barrier.reset(n_main_workers);`. The unit
     table stays as a small struct `k_store_units_t { alignas(cache_line_size) std::atomic_size_t next_unit{0};
     size_t n_units = 0; std::array<uint32_t, max_minibatch_size + 1> unit_start{}; } k_store_units;` (comment: lives
     in every batch of every build; a conditional member would need a second batch template parameter; size ~ 4 x
     (max_minibatch_size + 1) bytes + 2 lines). Delete opened, finished, helper_windows, max_shared_workers.
   - save_k_impl: `shared = k_store_shared<geometry>(q_batch, n_workers)` (now: page::k_store_scatters<geometry.kv>()
     && n_workers > 1 && items.size() > k_block_tokens; the 128-worker cap is gone). Main: k_store_cut_units;
     `q_batch->k_store_barrier.next_phase([&] { units.next_unit.store(0, std::memory_order_relaxed); });` claim loop;
     `done(0)`; `wait_for_all()` (the join). Helper: `wait(worker_ix)`; claim loop; `done(worker_ix)`; return.
     Claim loop: `for (size_t u : greedy_range(units.next_unit, units.n_units)) store_k_block<geometry>(q_batch, slot,
     ks, units.unit_start[u], units.unit_start[u + 1]);`. The phase pairing is the barrier's: a helper's W-th wait meets
     the W-th phase, and main cannot open phase W+1 before every participant called done for W. Happens-before: main's
     unit table -> ++started_phase (seq_cst RMW) -> helper's acquire wait; helper's row stores -> count_down (acq_rel)
     -> main's acquire wait -> the mark loop. Delete k_join_clock_spins, k_join_timeout_s, the spin loops and
     _mm_pause. A mismatched save_k call count now waits (TRON_LATCH_WATCHDOG logs the latch states) instead of
     aborting after 120 s: say so in the PR body (the "join watchdog, reviewers decide" item of PR 4958 is closed by
     the existing watchdog).
   - Note [Shared block save] rewritten to at most about 25 lines: why the helpers are idle at that statement, the
     deadlock argument (the helpers reach their save_k without main's help), the unit cut rule, the phase pairing, the
     measurement that motivated sharing. The counters' narration goes.
   - TronCpp.hs comment in runHelperStatement ("the N-th window a helper enters is the N-th window main opens") stays
     true under barrier phases; reword "window" to "phase" only if the Note's term changes.

Commit 5 "tests: the save_k case drives the barrier":
   - t_llama_unit save_k case: `q_batch.reset_channels(0, n_workers)` before the three-thread section (the barrier
     needs the participants); keep `next_unit == n_units + n_workers` (greedy_range: each worker's final claim past the
     end) and the unit invariants; replace the finished_at_return proxy by calling check(before) right after main's
     save_k returns and before the helper threads are joined (proves the production join directly); the option-off
     `opened == 0` assertions go (the absence of a window is not observable through the barrier; the bytes check
     covers it). No test calls page::set_k_block directly (t_k_vnni_layout calls the tensor op), so commit 2 changes no
     test.
   - LoopyTronSpec.hs / TronCpp.hs: no change beyond the comment.

PR body facts for PR3': the merge's own hunk count; "How to review" names next_k_run, set_k_block (one signature),
k_store_barrier phases, greedy_range; the open item "Join watchdog" is closed by TRON_LATCH_WATCHDOG (behaviour change:
wait + log instead of abort); the 128-worker limit disappears; the performance table (80bce9a08d) is PR 4958's head's
and the TTFT cells (tp2 and tp4 at prompt 1024; tp2 at prompt 8192) are pending at the PR3' head: own "Pending
measurement" subsection.

### PR4' = jhan-vnnik-4-tail-block-5047 (worktree ~/workspace/ai-runs/tron-ben-pr4): "the row-major tail block inside the cache"

Goal [v2]: PR 4959's content (per-block layout state in the page, row-major tail block, forward-end conversion,
hardware-attention policy, deb preset, tests) with: self_attention.hpp unchanged from PR3' (Ben's loop); the tail-block
scoring and the "all blocks converted" gate inside page::score_k / page::try_score_k_amx; full.hpp unchanged from Ben
(no k_staging_row: dropped, see 2c); the pending-block record a page-owned type; no raw plane access in tests.

Commit 1: `git merge jhan-vnnik-3-shared-save-5047`. Resolution rules:
   - self_attention.hpp = PR3' side entirely (drop PR 4959's k_layout_dense lambda, the vnni_blocks/plane placeholders
     and the in-loop tail dotter; keep nothing of PR 4959 there).
   - kv_cache.hpp = PR3' operations + PR 4959's state and members (then reshaped). Note [K VNNI storage] items for PR4':
     item 2: "page::try_score_k_amx passes the plane to qk_vnni_128x4 only when every block of the page is converted,
     otherwise it declines"; item 3: "page::score_k gives the live tokens of converted blocks to k_vnni::qk_group and
     the live tokens of row-major blocks to the dotter"; item 4: "k_head_fn always calls get_k_row, which for a
     row-major block is one 4-line read plus a 256-byte copy into the staging scratch"; item 6: Ben's sentence plus
     "set_k_row and get_k_row follow the block's recorded layout". Replace "(issue #4500)" at kv_cache.hpp:757 by the
     plain cost statement (no issue numbers in source).
   - model.hpp = PR3' store_k_block / save_k_impl / barrier window. PR 4959's `if (n < k_store_block)` policy (a short
     run stays row-major) moves INTO set_k_block (commit 2): fewer than 16 valid lanes -> per-lane row-major stores
     (store_row_major) and no bit; 16 lanes -> store_block and the block recorded as converted (what PR 4959's
     note_k_block_saved did after the call). PR 4959's recording loop is folded in commit 4. Drop PR 4959's comment
     edit at model.hpp:3232-3236.
   - full.hpp = Ben's three lines (the PR3' side). Delete PR 4959's k_row_if_row_major, its Note item 4 sentence and its
     test block (t_k_vnni_layout.cpp:680-693).
   - tensor/k_vnni.hpp = both; t_amx_dispatch_dtype.cpp = PR3' + PR 4959's record_rows additions + header sentence
     ("with record_rows every block is converted and the VNNI kernel runs; without it the page keeps row-major blocks
     and try_score_k_amx declines"); hetero test = both (d1 fix arrives from PR2'; verify `grep -n '->k<'` is empty).
   - CMakePresets.json, README.ci.md, config/test-benchmarks.json: PR 4959's hunks, in their own commit (commit 8).

Commit 2 "kv_cache: a short block save stays row-major inside set_k_block" (the policy of PR 4959 as a cache decision;
   one set_k_block, no `present`; tensor store_block keeps its mask with a comment naming its callers: the bit-for-bit
   test and block_to_vnni). Un-name EAGLE_STORAGE_SLOTS_1 to the file's lower_snake idiom (eagle_storage_slots = 1;
   kv_cache.hpp has no other NAME_<value> constant). The hetero test's HAS_HARDWARE_GEOMETRY_TRUE /
   FORCE_HW_ATTENTION_FALSE match that file's idiom (18 such names) and stay.

Commit 3 "kv_cache: the dense gate and the tail-block scoring live in the page":
   a. try_score_k_amx VNNI branch: decline unless every block is converted, through the PRIVATE mask
      (`k_vnni_blocks_[k_state_ix(slot)].load(acquire) == k_vnni::BLOCKS_PER_PAGE_MASK_0XF` or the existing private
      helper); comment: "when a block of the page is not in the VNNI layout yet; the caller then scores in software".
      The public k_vnni_blocks<geometry>(slot) accessor keeps test callers only: its comment says so (C11). Cost to
      state in the PR body: Ben's apply_dense_amx_page zero-fills s_pages before the call, so a declined visit costs a
      1 KiB fill (one pass per block completed by a short run, plus hardware-policy pages the CPU scores).
   b. score_k: one local generic lambda `score_rows(uint64_t rows, auto row_at)` capturing q, kv_head, scores, stride,
      building the dotter array INSIDE (lazy, as Ben's row-major branch) and looping over the bits. Row-major branch:
      `score_rows(live, [&](size_t i) { return keys[i]; })`. VNNI branch: `const uint64_t vnni = live &
      k_vnni_token_mask(blocks); if (vnni) k_vnni::qk_group(... vnni ...); if (live & ~vnni) score_rows(live & ~vnni,
      [&](size_t i) { return row_major_row(plane, i); });`. Private `static constexpr uint64_t k_vnni_token_mask(uint8_t
      blocks)` next to k_block_bits: a loop over the 4 blocks with k_block_bits(c), no multiply trick (C15). No member
      helper with six parameters.
   c. [v2] k_staging_row is DROPPED. full.hpp keeps Ben's always-copy k_head_fn. Reasons: it would hand out a raw bf16*
      into K storage (P2, C5) and undo the v_head_fn symmetry Ben made; PR 4959's get_k_row already reads a row-major
      block through load_row_major (one 4-line read + a 256-byte copy into L1-resident scratch); the copy measured
      inside the band in every FPGA cell of the 2026-10-21 campaign (section 5). If jhan wants the pointer path, it is
      a separate follow-up with its own FPGA cells.
   d. Bit helpers (block_bit, offset_bit, BLOCKS_PER_PAGE_MASK_0XF) stay in tensor/k_vnni.hpp and the cache; no use in
      self_attention.hpp, model.hpp or full.hpp.
   e. [v2, C3] copy_storage_slot (37 -> 91 lines at the PR head) and k_forget_row get one private helper per job (the
      bit plan of a copy, the row-major row copy, converting the complete blocks) so each loop body is one line per
      layout; the slot's bit plan is computed once per slot, not per KV head (structure-4959-10). Behaviour unchanged.

Commit 4 "model: a saved row's pending block is the page's answer" [v2: M4, interface-4959-4, record-4959-5]:
   - note_k_row_saved<geometry>(slot, offset) returns a page-owned token instead of bool: `std::optional<k_pending_block>`
     where `struct k_pending_block { k_storage_ref storage; uint32_t block; }` is a page type (the page captures the
     storage view at save time so a relocation before the forward end cannot redirect the conversion: say that in its
     comment). A row-major slot returns std::nullopt at compile time (the geometry test stays inside the page).
   - model.hpp: the recording loop is folded into the mark loop: `const bool record =
     !cached_operation_uses_hw(binding.operation);` once; after `pg.mark_k_complete(slot, j)`: `if (record) if (auto
     pending = pg.template note_k_row_saved<geometry.kv>(slot, j)) pending_k_blocks_.push_back({&pg, *pending});`.
     No `if constexpr (k_vnni::layout_on ...)` in model.hpp, no `j / k_store_block`, no k_storage_of call. Order of the
     row bit and the completion mark is not observable (readers take the layout from the block bit, which only the
     forward-end conversion sets).
   - convert_pending_k_blocks: `b.pg->k_block_to_vnni(b.pending)`; page::k_block_to_vnni(slot, c) (test-only at the PR
     head) is removed; the production entry takes the token (rename k_block_to_vnni_at to k_block_to_vnni).
   - pending_k_blocks_ gets one amortized reserve in resize() with a comment deriving the bound (C13).

Commit 5 "attention: hardware-attention policy" = PR 4959's cached_operation_uses_hw policy and Note [Row-major blocks
   under hardware attention], trimmed to what the reader needs there (C9); the hetero test's forward-conversion case.

Commit 6 "tests: no raw plane access; one helper for save-and-convert" [v2]:
   - t/kv_cache_helpers.hpp: `test::save_k_rows_and_convert(page, slot, offsets...)` (or a loop form): for each offset
     `if (auto p = page.note_k_row_saved(slot, off)) page.k_block_to_vnni(*p);` replacing the three copies
     (t_amx_dispatch_dtype.cpp:122, t_llama_unit.cpp:2602, t_k_vnni_layout.cpp:597) and their three #ifdef wrappers.
   - t_llama_unit check_page_range_reductions: delete the element()/k_packed re-store (a get_k_row/set_k_row round trip
     on an unconverted block is the identity, dead work); keep the recording loop; comment: "the VNNI build scores the K
     instance fill_random wrote, converted in place; nothing compares across builds".
   - t_k_vnni_layout page case: drop the raw checks (plane.at / row_major_row; subsumed by the tensor-level case
     "row-major tail block converts to the VNNI layout and back, bit for bit", which owns its plane) and the snapshot
     check (block 1's bytes after a forget are not observable through page operations: say so in the test comment);
     keep the bit checks and check_rows; check_rows proves get_k_row for both block kinds. No test-only friend in page.
   - t_amx_dispatch_dtype.cpp exercise_page: the three adjacent bool parameters become enum classes (C7; the four named
     bool constants at :301/:319 go with them).
   - config/test-benchmarks.json rows: state in the PR body that they are PR 4959's head's measurements (or re-measure).

Commit 7 "docs: the VNNI K options and the kill switch" [v2, M8]: README.ci.md's existing paragraph (582-601) gains
   TRON_AMX_DISABLE (what it changes at run time), and the sentence that a layout rollback needs a rebuild (the kill
   switch keeps the layout). README.ci.md is the only place tron documents these options (verified by grep over *.md).
   Comment pass (simplify-cpp-comments on the merged files; the 17-line comment on a 7-line lambda, the kv_cache.hpp:727
   bullet of record-4959-7, Note sizes). amx_attn_iface.hpp:222-230 and kernels/k_vnni.hpp:25-33 name page::score_k as
   the tail scorer.

Commit 8 "build: VNNI K in the deb preset; benchmark rows" = PR 4959's CMakePresets.json, config/test-benchmarks.json
   hunks, kept separate so reviewers can split the production default from the mechanism (M9: offer the split in the
   PR body as an open item: (a) tail block and conversion, (b) hardware-attention policy, (c) preset and rows).

PR body facts for PR4': FPGA rows (+2.5 % and +12.1 % TPS against the parent at ea94e95a4e) were measured with the
pointer staging path; the new head copies every staged K row (PR 5047's path), so they are pending re-measurement; the
dropped k_staging_row with the in-band FPGA cells as evidence; the 1 KiB fill per declined visit; the test-coverage
changes (snapshot check dropped, cross-build property not checked by any test); the recording fold; no ingest change.

## 4. Rules for every branch

- Behaviour-preserving [v2 wording]: same stored bytes, same scores, same expectations observable through the page's
  operations. Synchronization may change only by adopting an existing tron primitive (PR3' barrier). Named exceptions:
  the AMX gate is evaluated at run time (PR2'); the d2 probe becomes real; PR3' join waits instead of aborting; PR4'
  keeps PR 5047's staging copy (no pointer path). A performance-only path is a new feature and is not added.
- Ben-record findings (findings-495N.md) that are not in section 3 go into a named commit on the same branch; they are
  not skipped because they are unlisted. Pre-existing smells outside the stack's changes stay (ben-review: preserve
  existing code).
- Surgical: touch only what the merge and the listed changes require. Do not edit the PR branches themselves. Do not
  push. Do not run git in any /var/tmp/jhan tree. Do not modify ~/workspace/ai-runs/tron-pr5047 or tron-split-pr*.
- Style: clang-format 19.1.7 (`uvx --from clang-format==19.1.7 clang-format --style=file:<worktree>/.clang-format -i
  <files>`), `git diff --check` clean, no `<cassert>`, no issue/PR numbers in code comments (hunks the merge carries
  are brought to this rule in the merge commit), NAME_<value> constants only in AMX-owned files (shared files keep
  their own idiom: kv_cache.hpp lower_snake, the hetero test NAME_<value>), Note references consistent (lint-notes
  needs GHC and is not runnable here: check Note names by grep), comments in plain English (define terms, one claim per
  sentence, no idioms), comment length: a comment at a line says what the reader needs there and points to one Note
  for the rest (C9); dead includes removed with their last user.
- Commits: one topical commit per numbered item of section 3, each compiling (syntax matrix) and each green for the
  dispatch test's expectations; `git commit --no-verify` (the lefthook hook is missing on this host); every message ends
  with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; no message line starts with '#'. The draft PR is
  meant to be read commit by commit: the body says so.
- Verification on this host: the 22-cell syntax matrix `W=<worktree> P=<scratch>/stack/lcheck bash
  <scratch>/stack/lcheck/matrix.sh <label>` must print "MATRIX OK" (cells: gen / gen-amxoff x option off / on x
  t_llama_unit, t_k_vnni_layout, t_amx_dispatch_dtype, t_amx_numerics, heterogeneous_scheduler_compile, + amx_attn.cpp).
  Greps on code lines (comments excluded) of h/tron/models/self_attention.hpp, h/tron/models/model.hpp,
  h/tron/scheduler/full.hpp: `k_vnni::` (model.hpp may reference page::k_block_tokens only), `k_packed`, `template k<`,
  `kv_block(`, `k_vnni_blocks`, `block_bit`, `offset_bit`, `row_major_row`, `__mmask16`, `BLOCKS_PER_PAGE_MASK`,
  `BLOCK_TOKENS_16`, `k_storage_of` -> all 0. `k_source_row` / `k_destination_row` may appear only as the typed row-view argument of page::set_k_row / page::get_k_row (the views are layout-agnostic; Ben's k_head_fn in full.hpp holds one such line, which stays), never next to a conv / rows_are_bf16 helper. Repository-wide: `k_packed<`,
  `template k<`, `kv_block(` outside kv_cache.hpp print only the t_llama_unit probe definitions. `grep -n 'issue #\|PR #'`
  over kv_cache.hpp, model.hpp, tensor/k_vnni.hpp prints nothing.
- Gate before any draft PR opens (run by the session owner on delphi-3bda): builds with the option OFF and ON (dispatch
  ON) for each branch, the unit tests t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit, t_k_vnni_layout,
  t_heterogeneous_scheduler (USE_HW_ATTN unset: its software-scored section skips otherwise), and the forced-run token
  check where time allows.

## 5. Facts to carry into the PR bodies

- [v2 corrected] PR 5047 made k_head_fn copy every staged K row (full.hpp). k_head_fn runs only under FPGA attention.
  The 2026-10-21 campaign (exec/pr5047-20261020, interim counts) measured PR 5047 vs its base in the FPGA cells inside
  the band: qwen3-4b tp2 prompt 1024 TPS +0.28 % (band 1.76 TPS), prefill +0.011 s (band 0.15 s); gpt-oss-120b tp4
  prompt 1024 TPS -1.66 % (band 6.6 TPS); qwen3-4b tp2 prompt 8192 TPS +0.27 % (1 repetition). The llama-3.1-8b prompt
  8192 prefill +0.19 s (+0.5 %) is a CPU-attention cell (USE_HW_ATTN=0) and is NOT the staging copy; its cause is open.
- PR 4957's performance table was measured at 0ee8671d35 on PR 4956 at 82d05e94be, before PR 5047 existed; PR 4958's at
  80bce9a08d; PR 4959's at ea94e95a4e. Every number in a new body carries the head it was measured on; re-measurement
  at the new heads is a "Pending measurement" subsection.
- Ben's CI "Build Tron" failure (d1), the vacuous probes (d2) and the stale comments (d3) are defects of PR 5047's head;
  PR2' fixes them and recommends the same fix for PR 5047.
- The three bodies follow the PR-description skill (Short version, Background, Words used here, How to review,
  Verification, Open items, The stack), present tense, no change narration; every "How to review" step names a function
  that exists at the new head.
