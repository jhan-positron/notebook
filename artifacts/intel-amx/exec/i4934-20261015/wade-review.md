# Wade-style review of branch jhan-vnnik-5-i4934 (HEAD 7a41c79edd, BASE 175b1837b9)

Short version: no must-change finding. The parallel conversion's ordering argument holds at HEAD (release fetch_or in k_block_to_vnni_at, acquire loads at every reader, the latch join inside parallel_for, the call before the logit enqueue). Six findings are claim or comment precision: two commit-message claims that no run backs yet (the loss attribution and the mutation claim of the new score test), three comments that say "one block per task" or "the app-pool workers convert them" where the code gives each worker a strided share and converts short queues on the main thread, and one new parameter without a line at its declaration. One question for the author: the per-worker FIFO is shared with any other forward in the process. The rest are nits.

Reviewed: the diff 175b1837b9..7a41c79edd (8 files, +528/-130), the full text at HEAD of every touched file, the six commit messages (used as the body), design-v1.md and status.md. No PR exists: PR body, discussion, bot threads and CI runs are Insufficient data. Not run: the unit tests (the 3bda build was in progress at review time); checks 3B and 8 therefore record Insufficient data.

## Findings, by severity

### Claims (commit messages as the body)

1. **Check 6, commit b03a9c4ab5 (message), claim wider than a run shows.** "Removing both costs is most of the decode loss and the prefill loss of issue #4934." The lazy probe measured the dotter part (2.0 to 2.3 points at tp2 prompt 1024, exec/results/pr4lazy-E-cpu); the per-token tests' share and the prefill share are estimates (understand-digest.txt, prefill Q4: est. 0.45 to 1.3 s wall). So the sentence states a measurement that does not exist at this head. Ask: until i4934-E-cpu reports, write "the measured dotter cost and the estimated cost of the per-token tests" or move the attribution to the PR body's Verification with the run id.

2. **Check 6 / 33, commit 7a41c79edd (message) and t/t_amx_dispatch_dtype.cpp:285-292 (the new case's header comment).** "This one fails when a row-major row is scored through the reader or a VNNI block through the dotter." The check compares m_star bit for bit (t_amx_dispatch_dtype.cpp, check_scores, `REQUIRE(sp[h].m_star == m)`). It fails under those mutations only if the two readers' fp32 add orders give different floats for the dominant row's 128-term sum; the values are chosen to make that likely (7 exponents, every mantissa) but no mutation run shows it. So the discriminating claim is unverified. Ask: run the two mutations once on 3bda (`in_vnni = live` and scoring the VNNI block through row_major_row) and keep the sentence, or soften it to "is meant to fail".

### Comments that say more or less than the code (check 17)

3. **h/tron/models/kv_cache.hpp:691-693 (Note [K VNNI storage], bullet 1)** says "the app-pool workers convert the queued blocks, one block per task". At HEAD convert_pending_k_blocks (model.hpp:3195-3212) gives every worker a strided share through parallel_for_or_serial, and a queue shorter than k_convert_parallel_min (8) is converted on the main thread. So "one block per task" and "the app-pool workers" are both wider than the code. Suggestion: "the app-pool workers convert the queued blocks (a strided share each; a queue of fewer than k_convert_parallel_min blocks stays on the main thread), and the main thread joins them before the logit delivery reuses the pool".

4. **h/tron/models/kv_cache.hpp:2215-2217 (above k_block_to_vnni)** says "by one app-pool worker per block". Same fact: a worker converts several blocks of the queue. Suggestion: "by the main thread, or by an app-pool worker (convert_pending_k_blocks in model.hpp gives each worker a strided share of the queue)".

5. **h/tron/models/model.hpp:1846-1847 (the forward-end comment)** says "The app-pool workers convert them, and the call joins them before the logit delivery below reuses the pool." Below k_convert_parallel_min the main thread converts (model.hpp:3205-3209). Nit: "The app-pool workers convert a queue of k_convert_parallel_min or more blocks (the main thread a shorter one), and ...".

### Declarations (check 21)

6. **h/tron/models/self_attention.hpp:1886-1887, the new parameter `vnni_blocks` of apply_page_tok.** The function's doc comment (:1868-1871, "Minimum iota of work ... Returns {number of relevant k tokens, final range hint, path}") does not mention it; the explanation sits in the caller (:1590-1598) and in the dense-gate comment (:1925-1930). A reader of the declaration alone sees `tron_maybe_unused uint8_t vnni_blocks`. Nit: one sentence in the doc comment: "`vnni_blocks` is the page's K block mask (page::k_vnni_blocks), read once per page by apply_page_range; a row-major slot passes 0 and it is never read."

### Constants (check 13)

7. **h/tron/models/model.hpp:3159-3166, `k_convert_parallel_min = 8`.** The derivation is three estimates ("a few microseconds (est.)", "tens of microseconds (est.)", "a handful of blocks (est.)"). The comment is honest about it, so this is the nit Wade asks as a question: can the comment carry the measured per-block and hand-off cost once the traces of the i4934 driver are read (the convert_k_blocks span gives both)? Keep "est." until then.

### Shared state (check 28): a question, not a finding

8. **h/tron/models/model.hpp:3209, parallel_for_or_serial(app_pool(), ...).** thread_pool::parallel_for enqueues one task to every worker's FIFO (threading.hpp:746-758) and waits on a latch. At the forward end of this forward the pool is idle (Note [Plugin-owned worker launch], model.hpp:1806-1829). If another forward of the same process (another work_queue, work_queue.hpp:116, 227) has tasks in those FIFOs, the conversion tasks queue behind them and this thread's latch wait grows by that work. The logit delivery at BASE has the same property (enqueue_to, model.hpp:1851-1853), so this is not new exposure; no deadlock is possible (the other forward's tasks wait on its own latches). Question: does rinzler ever run two forwards of one process at once? Insufficient data here (rinzler's work_queue construction was not read). If yes, the comment at :3195-3205 should say the wait includes whatever precedes the tasks in the FIFO.

### Tests

9. **Check 3A, t/t_llama_unit.cpp:4132-4134.** The new save_k section exits with SKIP when app_pool().num_workers() == 0, before its assertions. On any multi-core runner the pool has workers (app_pool creates app_get_num_cpus() - 1, threading.hpp:830-836), so the assertions are reachable there; Catch2 reports a SKIP, not a pass, elsewhere. Four facts per the check: (1) the target compiles on the lane: Insufficient data (no CI run); (2) the case is selected: t_llama_unit is registered with catch_discover_tests (t/CMakeLists.txt:610-617); (3) reachable on a runner with 2 or more CPUs; (4) a log at HEAD: Insufficient data (the 3bda build was in progress). No change asked; name the SKIP in the PR body's Builds and tests.

10. **Check 4 (fwiw, no ask).** The pre-existing section "full page with unrecorded rows" (t/t_amx_dispatch_dtype.cpp, RECORDED_ROWS_0) and the new "48 recorded rows" section make the same call and reach the same gate arm (vnni_blocks != 0xF). A gate mutated to `!= 0` or to `(vnni_blocks & 1) != 0` fails the 48-row section and passes the 0-row one; the reverse mutation set is empty. The 0-row section is pre-existing and re-spelled only, so the check does not fire; the 48-row section is the stronger of the two.

11. **Check 33 (fwiw).** The parallel branch is reached only by the direct call in the save_k section; no forward drives it (the heterogeneous forward case completes one block, the serial branch). The forward-end placement and the idle pool are Note facts, not test facts. Acceptable: the branch's contract (every block once, bits and bytes) is what the section checks.

### Nits (checks 15, 20, 22)

12. **Check 15, t/t_amx_dispatch_dtype.cpp:85-86.** clang-format moved the value of RECORDED_ROWS_32 to its own line because the trailing comment is long: `constexpr size_t RECORDED_ROWS_32 =\n    32;  // blocks 0 and 1; ...`. Suggestion: shorten the comment to "blocks 0 and 1 VNNI" so the value stays on the declaration line, as its siblings do.

13. **Check 22 (fwiw).** `[[maybe_unused]] auto dot_q` is the int 0 on a VNNI slot (self_attention.hpp:2001-2007), read only in the discarded `else` branch of the loop. The placeholder exists so the row-major branch compiles; it is the same shape as `keys` and as BASE's PR 4898 code. No ask.

14. **Check 15, spelling.** prose.py/spell.py over the diff: 0 BAD, 0 VOCAB, 15 EXCUSED tokens, all repository words (accessor, app, dotters, est, hpp, ...). step5 near-miss scan: 0 findings. width.py: 0 over-wide Markdown lines (no .md in the diff).

## Checks that passed without a finding

- 14 dead symbols: every added symbol has a consumer at HEAD (block_token_bits 4 uses incl. page::k_block_bits and the static_assert; block_token_mask 5; k_convert_parallel_min 2 incl. the test's static_assert; every test constant used; `<bit>` consumed by std::countr_zero at self_attention.hpp:2079).
- 9 narration: no added code comment names a review round, a PR or an issue (grep of the added lines). The commit messages name issue #4934 (allowed).
- 10 unrelated hunks: the amx_attn_iface.hpp:49-57 contract rewrite and the Note item 3 parenthetical (kv_cache.hpp:794-796) are stale-comment fixes on the path the PR changes; commit b03a9c4ab5's message states both. No hunk fails the revert test.
- 11 history: 6 topical commits, one author, no fixup cluster; the target branch merges (origin/main first-parent is all merge commits), so the history is permanent and fine.
- 12 shared header: no global-namespace addition; tensor/k_vnni.hpp and kv_cache.hpp are the author's files in this stack.
- 16 debug switches: none. 23 disabled code: none. 24 placement: block_token_bits/mask next to block_bit in tensor/k_vnni.hpp; k_convert_parallel_min next to k_store_block in model.hpp.
- 17 (other comments): the dense-gate text matches the code order (`k_layout_dense && is_dense_amx_page`); "Note [Minibatch Dependency Tracking] in model.hpp" at self_attention.hpp:1595-1596 is wrong by file: the Note lives in h/tron/models/common.hpp:966 (nit, same class as findings 3-5: fix the file name).
- 18 helpers: parallel_for_or_serial reused (threading.hpp:802); block_token_mask is the only place that expands a block mask; page::k_block_bits delegates instead of duplicating.
- 19 types: size_t counts, const where never reassigned, `uint64_t rows` mutated by design.
- 20 names: vnni_blocks / vnni_tokens / in_vnni / rows / dot_rows / make_dot_q / page_shape / query_value / k_row_value say what they hold.
- 25 behavior changes: the re-save return value of note_k_row_saved (stated in bd68fc73e0's message), the conversion thread (5a9ed2e983), the gate evaluation order (pure predicates, no input differs).
- 26/27: the strided loop covers [0, n_blocks); countr_zero runs only while rows != 0; no clamp, no silent exit added.
- 29: pending_k_blocks_ is read-only during the join; pages outlive the forward end as at BASE.
- 30 hot path: per visit the VNNI path now does the live shift-or per token, one block_token_mask (4 iterations, constant-folded), two ANDs and two branches; the per-page mask read replaces a per-visit read; make_dot_q runs only when rows != 0.
- 31/32: the convert_k_blocks span keeps its blocks argument; no new state without an operator view (a per-task span was suggested by the design panel, optional).
- 1 test literals: pre_bits (exponent field 0x60..0x6f, stated) and source_bits (0x70..0x7f) are disjoint as the comment says; DOMINANT_TOKEN_20/50 and RECORDED_ROWS_32/48 are pinned by static_asserts to their blocks; the BF16 bit constants state their values.
- 2: no new STATIC_REQUIRE; the static_asserts added are value-stating ones in the file's idiom.
- 5 names: the two new sections and the new case describe their passing state; tags follow the sibling files ([attention][k_vnni] as in heterogeneous_scheduler_compile.cpp).
- 34 workarounds: none. 35 bot findings: none.

## Correction to finding list numbering

Finding 15 (check 17, self_attention.hpp:1595-1596): the comment cites "Note [Minibatch Dependency Tracking] in model.hpp"; the Note is in h/tron/models/common.hpp:966. Nit: fix the file name.
