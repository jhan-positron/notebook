# Context for the PR 4557 Runar-review response (collected 2026-10-06 23:30 UTC)

Read-only context for the drafting and checking agents. Verify before you cite.

## Where the code is

- PR head c5d44bd86f (what Runar reviewed): worktree `/home/jhan/workspace/ai-runs/tron-issue4525`
  (branch jhan-kv-typed-tensors, one commit on main dd6e85226b). Use `git -C <wt> show c5d44bd86f:<path>`
  or read files directly. Run NO build, NO git write, and write NO file under ~/workspace.
- main dd6e85226b (the base): `git -C /home/jhan/workspace/ai-runs/tron-issue4525 show dd6e85226b:<path>`.
- Side branch d9e7645fee (jhan-kv-typed-tensors-plain-names, Wade's style nit: value-suffixed constants removed from
  the shared files; "spelling only", disassembly identical): worktree `/home/jhan/workspace/ai-runs/tron-i4525-style`.
  NOT yet on the PR branch. jhan told Wade (issue comment 6027277800, 2026-10-06 23:23 UTC) that this commit reverted the
  changes, so the next push of the PR will contain it. Runar's line numbers are at c5d44bd86f; v_vnni.hpp shifts by
  -20 lines after line 86 in d9e7645fee (the six header constants are gone).
- Pre-squash history (every reviewed commit): branch jhan-kv-typed-tensors-pre-squash-20261006 (tip 1bdd592ff2).
- Runar's 8 inline comments: `runar-comments.json` in this folder. His summary: `runar-summary.md`.
  The live PR body: `pr-body-live.md` (142 lines, numbered as `cat -n` prints them).

## People and state

- Runar = GitHub rbjarnason-positron, review 5432936425, COMMENTED, 2026-10-06 18:29 UTC, at c5d44bd86f.
  "I found nothing blocking and nothing that changes the shape of the code."
- Wade = Wado-posi: APPROVED 2026-10-06 17:05 UTC; his style nit -> d9e7645fee.
- Ben = bgamari-positron (maintainer): CHANGES_REQUESTED 2026-09-29 still the recorded decision; his six threads were
  answered and applied 2026-10-01 (page status/PR4557-respond-2-Ben.html). He has NOT re-reviewed. He has not explicitly
  signed off on the tagged `operator new[]` approach (commit 39a6899446); his comment 4133772400 on memory.hpp:175 only
  asked to clarify the Note. Wade's resolved thread 4188336279 (memory.hpp:192) asked for Ben's explicit sign-off.
- Requested reviewers now: axch, mcherba, BillBaumann, bgamari-positron.
- jhan's rules: replies under 100 words, first person, plain English (define terms, one claim per sentence, no idioms),
  no @-mentions or names of people in anything Claude drafts for GitHub (roles + links instead), describe the PR head in
  present tense (no history in the PR description), "do not add code which has no consumer" (jhan's own B5 decision).
- Prior rounds' pages (format to follow): status/PR4557-respond-Wade-comments.html (generator exec/wade-20261005/gen_wade.py)
  and status/PR4557-respond-2-Ben.html.

## Pre-gathered facts (verified by hand at c5d44bd86f unless noted; re-verify what you cite)

### R1 comment 4199039224, t/t_llama_unit.cpp:3461 (benchmark row)
- t/AGENTS.md:23-26: "After adding or materially changing a test, refresh config/test-benchmarks.json with
  `bin/slice bench --new` or targeted `bin/slice bench --update <name>`."
- config/test-benchmarks.json has four platform blocks: genoa96 (line 3), genoa32 (168), granite_rapids_6960p (273),
  granite_rapids_6962p (378, meta last_full_bench 2026-09-20, load_factor 0.978). t_llama_unit rows at lines 149, 259,
  330, 437. The 6962p row (437): times {"1":5.187,"2":5.256,"4":4.936} s, max_rss_mb 331. delphi-3bda is a 6962P.
- The PR changes 14 files; config/test-benchmarks.json is not among them. Precedent 8887cbe37c (2026-10-03, two commits
  before the branch point) refreshed t_tool_call_serialize rows only (4 lines).
- New test cases: "packed V rows keep their bits through set_v, get_v and at()" (3461) and "append_v_row matches the
  independent packed-V formula" (3693); Status table: 20751 + 8192 assertions. t_llama_unit at c5d44bd86f: 249115
  assertions in 62 cases (both trees). t_amx_numerics 0.42 s row; t_heap_v2 gained one CHECK.
- bin/slice bench --help: `--update [TEST ...]` benches only these tests and merges; `--no-calibration` skips the
  post-bench full-suite calibration run. doc/slice.md:447-472: measures elapsed and peak RSS at 1-, 2-, 4-slice widths;
  one test per NUMA node at a time; `--update` preserves other entries verbatim; atomic write; lock config/.slice-bench.lock.
- Memory rule (3bda-shared-with-bill): `bin/slice bench --update` launches tests under --instance i,n for every slot, both
  sockets = whole-machine measurement; run only when the machine is free. Right now (23:30 UTC) rinzler@0 and rinzler@1
  serve production on both sockets (load average 126 = two rinzler processes spin-waiting), the nightly CI lease is absent,
  Bill's marker /bill-has-instance-0,2 exists. The nightly CI takes the machine ~03:30-11:30 UTC. So the bench can run after
  the nightly, with serving stopped per our campaign protocol, and jhan decides the slot. No timing of the new cases exists
  yet (Insufficient data for "unchanged").

### R2 comment 4199039245, h/tron/tensor/v_vnni.hpp:190 (pair_base comment, history wording, assert question)
- v_vnni.hpp:190-193 comment: "No bounds check here: this is the route of the bulk save/load/copy operations, whose callers
  (the page methods) already index inside the page, and page::set_v never checked it either. Checked element access goes
  through at()."
- page::set_v (kv_cache.hpp:2419-2428) and page::get_v (2437-2446) pass i_page straight to append_v_row / load_row.
  book::kv_block (1547-1558) asserts pg < n_pages and kv_head < n_kv_heads only; page::kv_block (2054-2075) takes no token.
- save_v_impl: model.hpp:3165 `int j = pg.offset_in_page(tok_ix);` (offset_in_page = tok.i - lo, kv_cache.hpp:1833-1835),
  set_v at 3168, then `pg.mark_v_complete(slot, j)` at 3172; mark_v_complete asserts offset < page_size (2004) AFTER the store.
- Direct callers of append_v_row with no page: t/t_amx_numerics.cpp:233, t/t_llama_unit.cpp:3709 (loop bounds 0..63).
- pair_base is called once per row operation: 245 (append_v_row), 312 (load_row), 356-357 (copy_token). The row loops do
  Cols/16 iterations (8 for 128 dims).
- The assert was removed by pre-squash commit daf227de13 "v_vnni: no bounds assert on the bulk save/load/copy route":
  Step F instruction comparison found TRON_ASSERT_LT(token, Rows) in pair_base "added a compare-and-branch to every
  page::set_v / page::get_v call and two to every token copied by book::append. TRON_ASSERT stays active in release builds,
  and main never checked the token on these paths, so the refactor was no longer instruction-neutral there." No TPS
  measurement of the assert alone exists; the criterion was instruction neutrality, not a measured slowdown.
- h/common/assert.hpp:3-5 undefines NDEBUG, so TRON_ASSERT is active in release builds.
- PR body line 105: "One difference found and removed: a bounds assert in detail::v_vnni_access::pair_base ... sat on a
  frequently executed path. The second commit removed it (TRON_ASSERT is active in release builds)."
- History wording also at v_vnni.hpp:74-76 ("have always required") and 236-237 ("exactly as page::set_v always did").
  In d9e7645fee the 74-76 text moved to the append_v_row comment (lines ~221-223) and 237 is at ~218.

### R3 comment 4199039256, h/tron/tensor/v_vnni.hpp:209 (aligned flag only in prose)
- v_vnni.hpp:202-221: const_v_row_view / v_row_view hard-code VIEW_ALIGNED_TRUE (kv_cache_fwd.hpp:24 `inline constexpr bool
  VIEW_ALIGNED_TRUE = true`); v_source_row / v_destination_row wrap a raw pointer; comment 209-210 "The caller must provide
  Cols elements aligned to chunk_alignment. These helpers neither check alignment nor copy data."
- view.hpp:43 and :125 `explicit constexpr view(T* data = nullptr) noexcept` (no check). view.hpp:13-15 has a TODO:
  "If a view purports to be aligned, validate that all strides except the last are multiples of (alignment/sizeof(T))".
- append_v_row / load_row use aligned forms: _mm512_load_ps (260, 289), _mm256_load_epi32 (253, 256, 269, 285),
  _mm512_store_si512 (263, 277, 297), _mm512_store_ps (321, 335), _mm256_store_si256 (324, 338).
- Other aligned views wrap storage with static alignment: kv_block `alignas(kv_block_alignment) bf16 k[...]` (kv_cache.hpp:2333),
  v_vnni_tensor `alignas(V_PLANE_ALIGNMENT_64) bf16 data_[...]` (v_vnni.hpp:178).
- t/heterogeneous_scheduler_compile.cpp:681-685: `alignas(chunk_alignment) std::array<float, ...> values;` added by this PR
  (main fed a plain std::array to set_v's _mm512_load_ps).
- Production chain: full.hpp:2754-2764 v_head_fn comment "dest is page_info's caller-owned, 64-byte-aligned scratch";
  gof.cpp:203 `alignas(64) std::array<bf16, HW_MAX_KV_HEADS * HW_BAKED_HEAD_SIZE> v_scratch;`. model.hpp:3168-3170 passes
  `&vs[ix][kv_head * head_size]` from the executor's V buffer (tensor/btensor/htensor, aligned storage; head_size*2 or *4
  bytes per head offset is a multiple of 64 for head_size 64/128/256/512).
- tron::is_aligned(const void*, uintptr_t) at h/common/memory.hpp:94-98; used at h/tron/threading.hpp:372 and :511.
  chunk_alignment = chunk_size * sizeof(float) = 64 (simd/auto.hpp:52).
- Runar: assert in both helpers (one branch per row) or validate in `view` itself ("the better answer").

### R4 comment 4199039265, h/tron/tensor/v_vnni.hpp:74 (V_ROW_WIDTH_MULTIPLE_32)
- v_vnni.hpp:74-77 comment + constant; used only at 240 (append_v_row requires) and 307 (load_row requires). copy_token
  (350-357) has no width clause. v_vnni_view / v_vnni_tensor static_assert `Cols % chunk_size == 0` (102-103, 159-160).
- page::set_v / get_v keep `head_size % 32 == 0` as a literal (kv_cache.hpp:1912, 1920, 1929, 1938, 2425, 2443, 2460, 2477);
  main dd6e85226b has the same clauses (1879-1929), so they are main's, unchanged.
- The loops step chunk_size (16) dims: `for (size_t i = 0; i < Cols; i += chunk_size)`. Nothing needs 32.
- scaled_v_expr requires head_size 64/128/256/512 (2253-2254). All real geometries are multiples of 32.
- In d9e7645fee: constant gone; `requires(Cols % 32 == 0)` literal at both sites; the three-sentence comment moved onto
  append_v_row ("Cols % 32: page::set_v and page::get_v have always required ... The constraint stays so that the accepted
  row widths do not change.").

### R5 comment 4199039272, h/tron/tensor/v_vnni.hpp:57 ("they serve fixtures")
- "fixture" appears in the two Notes only: v_vnni.hpp:57 and kv_cache.hpp:2242 ("Direct writes serve fixtures.").
- Non-const `T& at(token, dim)` at v_vnni.hpp:117-121; const at() at 123-128.
- Users of at(): t/t_llama_unit.cpp:3681 reads through `page->template v_packed<geometry>(slot, 0)` (a const view);
  t/t_llama_unit.cpp:112 probe `matrix_at_writes` used at 401-403 (STATIC_REQUIRE(matrix_at_writes<v_plane_mut_t>) etc.).
  No code writes through at(). Fixtures build planes through append_v_row (t_amx_numerics.cpp:233, t_llama_unit.cpp:3709).
- Ben's B5 (4134076112, old line 104): "It is a bit unfortunate that we grow this 100 LoC without any obvious users";
  jhan's decision 2026-10-01: drop v_vnni_row + expr base ("do not add code which has no consumer"), commit c12df586b6,
  whose message says "at() writes through a writable view and not through a const one" was kept as a tested property.
- Comment at 113-115 above at(): "Writing through it neither clears the pair partner nor marks the token complete".

### R6 comment 4199039284, h/tron/models/kv_cache.hpp:2248 (book goes through typed operations)
- kv_cache.hpp:2245-2248: "The plane arrives as its typed view. This weighted sum is the one cache-side kernel that takes
  the plane address (through v_vnni_access, Note [VNNI Packed V layout]). Its dot-product loop reads pair rows directly.
  Page methods, book and tests go through the typed operations instead."
- book::fill_storage_slot (1645-1657): `bf16* v = detail::v_vnni_access::plane(block.v.as_view());` then linear fill of
  page_size * head_size elements. Its caller book::fill_random (1217-1231) comment calls it "the one documented exception".
  v_vnni.hpp:50-52 says the same. book::append copies V through copy_token (typed).
- Callers of v_vnni_access::plane: kv_cache.hpp:1653 (fill_storage_slot), :2257 (scaled_v_expr),
  src/tron/kernels/amx_attn.cpp:223 (AMX PV kernel). pair_base callers: the three bulk operations only.

### R7 comment 4199039288, h/tron/models/kv_cache.hpp:2190 (PR body credits #4697/#4698 as if upstream)
- PR 4697 "Share KV row view helpers across cache callers" and PR 4698 "Fix KV cache access across object boundaries":
  author bgamari-positron, baseRefName jhan-kv-typed-tensors, both MERGED, mergeCommit 8e0cf77bed.
  `git merge-base --is-ancestor 8e0cf77bed dd6e85226b` -> rc 1 (not an ancestor of main). Also not an ancestor of
  c5d44bd86f by commit graph (the squash flattened history), but its content is in c5d44bd86f.
- main dd6e85226b kv_cache.hpp: `const bf16s* const data;` (2183); tile addressing
  `reinterpret_cast<const bf16x32*>(data + i * (head_size / chunk_size)) + chunk_offset` with `tile + k` (2208-2210, 2277, 2292);
  fill_storage_slot `bf16* data = reinterpret_cast<bf16*>(&block);` (1616).
- head c5d44bd86f: `const bf16* const data;` (2166); `const bf16* tile = data + i * head_size + 2 * chunk_size * chunk_offset;`
  with `tile + 2 * chunk_size * k` (2190-2206; 2268, 2282 for the other sizes); fill_storage_slot via v_vnni_access::plane.
- PR body line 43: "The V reads do the same since the maintainer's PR #4698 (merge commit 8e0cf77bed): scaled_v_expr and
  fill_storage_slot read bf16 arrays without a cast." Line 44: "(... the aliases from the maintainer's PR #4697, defined in
  v_vnni.hpp)". Line 47: "scaled_v_expr (the software path's weighted sum) takes the packed view." Lines 34-40 (v_vnni.hpp
  bullet) list owner, view, no row type, v_vnni_access, the three moved operations, the Note; NOT const_v_row_view /
  v_row_view / v_source_row / v_destination_row. Line 106: "Scope: the wrapper comparison is of the pre-rebase code."
- Evidence that exists for the rewrite (Ben-round page, 2026-10-01, round r2): objdump of t_llama_unit showed the two
  scaled_v_expr<64,128> functions (82 + 219 instructions) identical after address normalization between the tree without
  and with #4698, "so #4698 does not change 16-lane V dot-product code" (results exec/ben-20260930/r2-results.txt).
  Also the 2026-10-06 token identity at c5d44bd86f vs main (seven arms, one identical token file) covers the rewritten loops.

### R8 comment 4199039306, h/system/memory.hpp:197 (Note's verdict vs four sibling templates)
- memory.hpp:167-195 Note [DMA allocation creates objects]; 180-186: "dma_allocate_aligned is not on that list. It is an
  ordinary function that calls none of them, so the memory it returns holds no objects ... So try_make_unique_dma_for_overwrite
  gets its memory through the wrapper below, a function named operator new[]." Wrapper at 196-201.
- Sibling templates calling dma_allocate_aligned directly (main's code, untouched by the PR): make_unique_dma<T> (251,
  memset path 252-253), make_unique_dma<T[]> (266, memset 268-269), make_unique_dma_for_overwrite<T> (286),
  make_unique_dma_for_overwrite<T[]> (298). std::memset is not on the [intro.object]/13 list (memcpy/memmove are).
- Class-typed callers: src/pos/dma_ring.cpp:39 `make_unique_dma<dma_desc_t[]>(sz)` then `d->desc_idx = index;` at :47
  (dma_desc_t = 32-byte bit-field struct, h/pos/dma/common.hpp:42-62, trivial); h/pos/dma/queue.hpp:213-214
  `make_unique_dma<dma_queue_head>()`. Others: h/tron/hardware/dmatensor.hpp (scalar arrays), h/tron/hardware/tensor.hpp:107
  (`strip[]`).
- src/system/memory.cpp:461-469: dma_allocate_aligned calls heap->allocate / v2 heap allocate (not malloc, not operator new).
  src/pos/fake.cpp:440-444: the unit-test shim calls aligned_alloc (on the list), as the Note's last paragraph says.
- Issue #4588 (filed 2026-09-24, Tech Debt, assignee jhan, closed 2026-10-01 after #4698) is the precedent for a tracking
  issue. Project rule: no names in issues Claude drafts.
- Runar: "Not for this PR ... a sentence saying the wrapper covers the KV-book path, with an issue alongside #4588 ...
  probably best settled once [the maintainer] has signed off on the operator new[] approach."

## Position jhan's assistant leans to (challenge it)
- R1 holds -> run the bench on delphi-3bda after the nightly, commit the row; no timing claim before the measurement.
- R2 holds (all three parts) -> restore TRON_ASSERT_LT(token, Rows) in pair_base (one compare per row operation; no
  measurement ever showed it mattering), rewrite 190-193 as a precondition, fix the two history sentences (74-76, 236-237),
  and correct PR body line 105 to say the assert is back and what it costs.
- R3 holds -> TRON_ASSERT(is_aligned(row, chunk_alignment)) in both helpers now; the view-level check is main's TODO
  (view.hpp:13) and a follow-up issue.
- R4 holds -> drop the constant and both `% 32` clauses in v_vnni.hpp (Cols % chunk_size carries it); page methods keep
  main's clauses.
- R5 holds -> drop the non-const at() and the "fixture" clause in both Notes; keep the const at(); turn the writable-at()
  probe into STATIC_REQUIRE_FALSE (no element write path through a view) or drop it.
- R6 holds -> name book::fill_random as the exception in the sentence.
- R7 holds -> reword body lines 43-44, add the rewrite + cast removal as changes of this PR, list the four aliases in the
  v_vnni.hpp bullet, cite the r2 objdump evidence in Verification.
- R8 holds, deferrable -> one sentence in the Note + a Tech Debt issue (like #4588), after the maintainer's sign-off.
