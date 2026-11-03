---
name: ben-stack-reexpress-20261021
description: "2026-10-21 \"what would Ben dislike in PRs 4957/4958/4959\" + re-expression of the stack on PR 5047's structure as draft PRs from new branches jhan-vnnik-{2-amx,3-shared-save,4-tail-block}-5047; design brief, scripts, workflow ids, decisions"
metadata:
  node_type: memory
  type: project
  originSessionId: e5f1ec3f-7cb5-4755-a5bc-0280de828ba5
  modified: 2026-10-21T13:40:00.000Z
---

Request (jhan 2026-10-20): "Given what we know from his commits at PR 5047, what would he dislike of our PR 4957, 4958
and 4959? Generate draft PR from new branches if you see code change opportunities from learning 5047".

Decisions and facts (verified in the trees):
- Prediction workflow wf_e4c2f652-7e0 (277 agents): 82 kept findings, 5 refuted; per-PR digests in the session
  scratchpad stack/findings-495N.md; critics in stack/wfA-critics.md. Design brief v2 = stack/design.md (copy in
  exec/benstack-20261021/design.md).
- Ben's shape to follow: the cache (kv_cache.hpp page) owns the K layout; attention code passes queries + a live mask or
  a packed query, never a layout; no public raw K views; one control flow per function; call site asks the cache and
  takes a run-time "declined". His own head has defects d1 (hetero test calls page->k, CI red), d2 (vacuous probe
  Page::head_size), d3 (stale comments).
- Re-expression per PR: PR2' = page::pack_q_amx chooses the packer with the kernel; try_score_k_amx VNNI branch calls
  qk_vnni_128x4. PR3' = ONE page::set_k_block(std::array<Row,16>, invalid lanes absent) for every slot, conversion
  inside the page; page::k_store_scatters<geometry>() is the one layout fact model.hpp keeps (sharing policy);
  the window = tron::barrier k_store_barrier in batch (reset with n_main_workers in reset_channels) + greedy_range
  claim loop; hand-rolled counters/watchdog gone (TRON_LATCH_WATCHDOG logs instead of a 120 s abort). PR4' = dense
  gate + tail scoring inside try_score_k_amx/score_k (local score_rows lambda + private k_vnni_token_mask);
  k_staging_row DROPPED (keep Ben's always-copy k_head_fn: FPGA cells inside band); note_k_row_saved returns a
  page-owned pending token; recording folded into the mark loop; tests through t/kv_cache_helpers.hpp; README.ci.md
  documents TRON_AMX_DISABLE + rebuild-for-rollback; preset flip in its own commit.
- Fact correction: the llama prompt-8192 prefill +0.19 s of PR 5047 is a CPU-attention cell, NOT the staging memcpy.
- Existing primitives: tron::barrier (threading.hpp Note [Resettable Barrier Design]), greedy_range, latch_ref
  (acquire waits), TRON_LATCH_WATCHDOG. Only README.ci.md documents TRON_K_VNNI / TRON_AMX_DISPATCH.
- Worktrees (claude-box): ~/workspace/ai-runs/tron-ben-pr2/3/4; references tron-pr5047 (Ben), tron-split-pr2/3/4.
- 3bda scripts: exec/benstack-20261021/{build.sh,tests.sh,run-one.sh (per branch),run-all.sh}; tags bpN/bpNv; builds
  ~24 min each (two concurrent); the PR 5047 chain owns the machine from 13:30 UTC 2026-10-21 (~3 h).
- Implementation workflows: PR2' = wf_c5916ca6-7e7 (141 agents, 100 min), PR3' = wf_a044b496-23f (script
  ben-stack-implement-pr-wf_c5916ca6-7e7.js, args-parameterized; `extra` arg = branch-specific instructions).
- PR2' final head 9a8045836a (merge 708eed4ef9 + 5 commits: zero-row comment, pack_q_amx, probe fixes, panel_offset,
  Note item 2); 3bda gate run-one bp2 started 2026-10-21T07:49Z; PR body draft exec/benstack-20261021/bodies/pr2-body.md.
- PR3' final head 2c501a9390 (merge 0c16181b11 + 4 commits: set_k_block for every slot, store_k_block = loop over
  next_k_run runs, tron::barrier phase, store_k_block takes std::span<const token_job_id>); workflow
  wf_a044b496-23f (168 agents, 133 min); Note renamed [Shared VNNI K store]; body exec/benstack-20261021/bodies/pr3-body.md.
- PR4' final head f7c2ccf6b7 (merge 627092917a of PR3' 2c501a9390 + 11 commits; workflow wf_61fcb49e-71b, 183 agents,
  178 min, ended at 5219b3f0da; four messages reworded afterwards with identical trees). Deviations: the dense gate,
  the tail scoring and the short-run policy live inside the merge commit's resolutions; the deb preset flip and the
  benchmark rows are PR 4959's own commits below the merge (no separate last commit exists); k_plan_copy keeps the
  five-value list of Ben's copy_storage_slot. Reword trap: `git rebase -i` reword runs the pre-commit hook (lefthook
  missing) -> use `-c core.hooksPath=<empty dir>`; `commit --amend --no-verify` is enough for a merge amend.
  PR4' status: matrix pr4-final OK, clean checks OK, sha-bp4.txt written on 3bda, status.json branch 4 + page
  regenerated, body bodies/pr4-body.md (1,6xx words, placeholders BDA_TABLE_PR4 / STACK_SECTION only). Of 38
  predicted objections: 33 removed, 4 reduced, 1 kept by design. Draft PRs open only after each 3bda gate (bp2,
  bp3, bp4 in that order, after the PR 5047 chain).
- 3bda gates moved AFTER the PR 5047 chain (driver exec/benstack-20261021/run-gates-after-chain.sh, pid 3310850,
  reads results/benstack-20261021/sha-bpN.txt when it reaches N; skips builds already at that sha): the scheduled
  System CI run (systems_test repo, "Rinzler 72-core Intel system OCI version", starts 03:41Z) held the CI lease all
  morning (yesterday's ended 13:17Z), so unit tests waiting on the lease would have collided with the chain's 13:30Z
  perf reps. The bp2 tests.sh was killed at 10:10Z (run-one-bp2.done = failed, expected); bp2/bp2v builds at
  9a8045836a are kept and reused.
- ssh trap: a remote command containing `cd` triggers the prompt hook's directory listing on 3bda too; use absolute
  paths in ssh commands.
- Grep rule amended 2026-10-21: k_source_row / k_destination_row allowed as the typed row-view argument of
  set_k_row / get_k_row (Ben's k_head_fn line stays).
- git 2.34 on claude-box: autosquash needs `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash <base>` (-i required).
- Deliverable page: random/Ben-stack-PR4957-4959.html (generator exec/benstack-20261021/gen_page.py).
- GitHub: push only the three new branches; draft PRs with base = the PR branches, label "Skip benchmarks"; never
  post on PR 5047 (d1/d2 fixes are a recommendation in the PR bodies).

**Why:** the stack's reviewer rewrote PR 4956 himself; the draft PRs show how the rest of the stack reads on his
structure before he asks.

**How to apply:** when continuing this work, read design.md v2 first; keep the branches stacked (each merges the
previous new branch); state verification status (syntax matrix vs 3bda) in every PR body.

Related: [[pr5047-ben-refactor-review]], [[split-4424-plan]], [[value-suffix-names-shared-files]],
[[no-issue-numbers-in-source]], [[pr-description-no-history]].

## Gate and draft-PR log (2026-10-21)
- PR 5047 chain finished 14:43 UTC (B=ok x4, I=ok, D=ok, T=ok, report written). Gate driver started bp2 at 14:48 UTC.
- PR2' gate ok at 9a8045836a: bp2/bp2v 5 of 5 tests each, same assertion counts, kill switch skips 3 AMX checks (expected). Draft PR #5086 opened (base jhan-vnnik-2-amx, label Skip benchmarks), body = bodies/pr2-final.md (1,509 words).
- assemble_body.py now carries skip reasons in the 'What the table says' bullets (skips_of parses 'skips=N' and the 'AMX unavailable on this host - X skipped' lines).
- Next: bp3 gate -> PR3' draft, bp4 gate -> PR4' draft, then re-run assemble_body.py 2/3 and gh pr edit (re-fetch live bodies first) for the stack URLs.
- Page render pass traps (fixed 2026-10-21 in both gen_page.py): the entity guard must cover hex entities (&#x27; = apostrophe) or 'PR2&#x27; body' turns into 'PR2'. Body'; the capitalization rule must match the whole token ([\w:.-]+) or 'page::x' becomes 'Page::x'. cairosvg needs the svg style=height:auto removed and width/height attrs set, else the PNG is blank. No whole-page renderer on claude-box (no chromium/playwright).
- PR4' body source trimmed to 1,942 dry words (history sentence, duplicate ea94e95a4e, duplicate deb-preset clause, memory-order duplicate).
- PR3' gate ok at 2c501a9390 (builds 15:09 UTC, tests 15:11 UTC, 10 of 10; t_llama_unit +322 assertions with the option on, cause not pinned). Draft PR #5087 opened (base jhan-vnnik-3-shared-save), body bodies/pr3-final.md (1,592 words). PR #5086 and #5087 bodies re-edited with the stack links (live-text check first). bp4 gate launched 15:11 UTC.
- PR4' gate FAILED at f7c2ccf6b7 (2026-10-21 15:31 UTC): bp4 (option off) 5/5 pass; bp4v (option on) t_llama_unit rc 42, case 'apply and join page ranges' / section 'page splits match emulation' (t_llama_unit.cpp:3218, helper check_page_range_reductions ~2480-2900), assert_allclose at testutil.hpp:86 from the emulation comparison (~2778): 1 of 256 v_star values off by 0.022 (observed[255] 0.269 vs expected 0.253, tol abs 0.01 + rel 0.02). Same under TRON_AMX_DISABLE=1 (not AMX). PR 4959 head ea94e95a4e passed this with the option on (results pr4-20261012). PR4' removed the test's VNNI re-store (k_packed) and records with test::record_k_row_and_convert. Diagnosis workflow wf_208a07c8-9ac launched 15:40 UTC. No PR4' draft PR until a new gate passes (rerun: SKIP_BUILD=0 N=4 SHA=<new> run-one.sh, only after the kill-switch cell finishes).
- Kill-switch cell killswitch.sh launched 15:33 UTC on 3bda (pid 3427968, log exec/logs/pr5047-20261020-killswitch.log, marker line 'killswitch cell finished'); regenerate Ben-PR4956.html afterwards (gen_page.py knows the pair headoff:baseoff).
- PR4' diagnosis facts (probe 16:03 UTC, bp4v binary, section alone): the first call <8,false,true> (uses_hw=true, 10 pages, 640 tokens, queries = tokens 632-639 = page 9 rows 56-63, block 3 row-major unrecorded) fails at query tok 6 of ONE_PASS; its s_star/m_star match the reference within 1e-5 (weights right), only v_star[tok 6][head 1][dim 127] is off by 0.0155. The reference copies K AND V from storage (get_k_row/get_v) after the recording, so the difference arises during apply_page_range: one V value as the model reads it, or a storage write during scoring.
- Diagnostic worktree ~/workspace/ai-runs/tron-ben-pr4-diag, local branch jhan-vnnik-4-diag (NEVER push), commit a3df5a48ce = f7c2ccf6b7 + DIAG prints (storage re-read after apply_page_range, per-element v_star diffs per tok). Built on 3bda as TAG=bp4d via the new exec/benstack-20261021/build-diag.sh (t_llama_unit only; shared repo on NFS makes local shas visible). Probe logs: exec/results/benstack-20261021/probe-bp4v-pagesplit.log, probe-bp4d-pagesplit.log.
- Instrumented run at PR4' (bp4d, 16:16 UTC): storage unchanged by apply_page_range (K 0, V 0 of 131,072 each); EVERY element of v_star deviates (131-196 of 256 beyond 2e-3 per query), obs/exp ratio mean 0.997 with spread 0.99-1.003 (a consistent shrink), s_star/m_star exact. scaled_v (the software PV) is byte-identical across HEAD / 2c501a9390 / 6b081187e1, so the cause is in what feeds it or in the page setup. Bisection builds launched 16:25 UTC: bp4e = same DIAG at PR 4959 head 6b081187e1 (7ab3e89528, branch jhan-vnnik-4-diag-base), bp4f = PR4' DIAG with later_page_recorded_rows 0 (33f9f473a7, branch jhan-vnnik-4-diag-f), bp4g = 64 (dc8b5c4c21, branch jhan-vnnik-4-diag-g). All local branches, never push. Probe logs exec/results/benstack-20261021/probe-bp4{d,e,f,g}-pagesplit.log.
- Base-head instrumented run (bp4e at 6b081187e1+DIAG, 16:26 UTC): PASSES with the SAME deviation level (131-205 elements beyond 2e-3 per query, max 0.019 vs PR4' 0.030). So the v_star deviation against the fp32 emulation is inherent to the test's software path at PR 4959's head too; PR4' fails on a data-dependent tolerance edge (abs 0.01 + rel 2 % is absolute-dominated for small elements). fill_random is identical at both heads (raw linear fill). Open: same data + different scoring numerics, or different K instance (the base re-stored rows via set_k_row before recording; PR4' does not)? Hash builds bp4h (PR4' diag 560f08eb2b) and bp4i (base diag 7a3c3fb759) print the K/V hash and exact s_star/m_star; equal hash + equal s_star = PV-only difference, equal hash + different s_star = scoring numerics, different hash = data.
- Fix candidates for PR4' (decide after the hash result): (1) VNNI-aware emulation tolerance at t_llama_unit.cpp ~2778 mirroring the v_star_tolerance precedent at ~2814 (5e-2 under layout_on), with a measured comment; (2) restore the base's K instance in the test through public operations only (set_k_row of rows read back through get_k_row before recording) if the hash differs and the instance can be reproduced.
- Bisection by configuration (bp4f = later pages all row-major, bp4g = all converted, 16:38 UTC): IDENTICAL deviation counts (191/189/131/188/144/196/184), identical largest diffs (0.0298/0.0271/0.0185) and the identical failing value 0.269017 at idx 255 of query 6. So the K layout path of PR4' (qk_group for converted blocks, dotter for row-major rows) is numerically sound to 1e-6, and the ~0.3 % v_star deviation lives in the shared softmax/PV path. PR4' vs base differ in the DATA (the test's K instance), pending the hash check (bp4h/bp4i). bp4j = PR4' DIAG with the option OFF launched 16:42 UTC to see whether the deviation exists in the row-major build at all. Workflow wf_208a07c8-9ac in synthesis (5 analyses, 57 verifications done).
- Hash runs (16:46 UTC): K hash PR4' ON e7e1751da7e836ce vs base ON e89c1ad9f62aec32 (V hash equal ad4d211d902d1a11), m_star bit-identical, s_star differs 0.25 %: different K INSTANCES. Option-OFF run at PR4' (bp4j): counts 205/187/131/190/150/195/176 and max 0.0188 = IDENTICAL to base ON, so base ON == row-major instance (the re-store's purpose) and PR4' ON != row-major instance. The failing call is the 2-page uses_hw=false one (GENERATE(false,true) runs false first), queries = tokens 120-127. The inherent deviation = bf16 truncation of the softmax weights in detail::scaled_v_expr (interleave_bf16_ps + _mm512_dpbf16_ps), same in every build; the test already states this for the split comparison (t_llama_unit.cpp ~2806-2814: 'One truncation step is up to 2^-7 of the weight', v_star_tolerance 5e-2 under layout_on). bp4k (82da6c7f87, diag branch) prints the K hash BEFORE the recording loop: equal to e89c1ad9… => the in-place conversion changes values (PR4' defect to fix in code); different => the VNNI plane's row-major read differs from a row-major slot (test-data artifact, fix = emulation bound 5e-2 under layout_on, mirroring the precedent).
- VERDICT (16:50 UTC): no PR4' numeric defect. bp4k: K hash before recording == after (e7e1751d…), conversion in place preserves values; the VNNI plane presents its row-major blocks through the panel mapping, so fill_random's row i sits at token perm(i) = ((i%16)/4)*16 + (i/16)*4 + i%4 (workflow wf_208a07c8-9ac, 63 agents, 19 hypotheses, 3 survivors, same conclusion from code). The removed re-store had put raw row i at token i (the row-major build's instance). The inherent error = bf16 truncation (toward zero) of softmax weights in detail::scaled_v_expr; test bound abs 1e-2 was below it (max 0.019 row-major instance, 0.030 VNNI instance, worst 0.039 across instances per the agents' replication).
- FIX committed on jhan-vnnik-4-tail-block-5047: 38ad10f25c 'tests: the page-range emulation bound covers the bf16 weights of the PV product' (emulation_abs_tolerance = layout_on ? 5e-2 : 1e-2, mirrors step-12 precedent; comment states the measurements). Matrix OK 22 cells at 01eedc135b (pre-format twin), clang-format + diff --check clean at 38ad10f25c. Gate rerun launched 16:53 UTC (run-one.sh N=4 SHA=38ad10f25c; stale bp4/bp4v worktrees removed first). Alternatives for the body's Open items: reference-side bf16 truncation of the weights with a tight bound (agents' preferred), or restoring the row-major instance via get_k_row/set_k_row permutation. Diag worktrees d-j removed on 3bda; bp4k remains (remove after the gate).
- DONE 2026-10-21 17:10 UTC: PR4' gate ok at 38ad10f25c (builds 17:01 UTC, 10 of 10 tests, kill-switch t_llama_unit passes, 277,668 assertions). Draft PR #5094 opened (base jhan-vnnik-4-tail-block, 18 files, +1206/-1314). All three bodies (#5086, #5087, #5094) re-edited with the three stack links after live-text checks (1,532 / 1,626 / 1,935 words). status.json 3 of 3 open; page Ben-stack-PR4957-4959.html regenerated (114,840 bytes, 0 prose semicolons). Diagnosis record: exec/benstack-20261021/pr4-diagnosis.md + pr4-diagnosis-workflow.json + pr4-diagnosis-synthesis.md. Local diag branches kept (jhan-vnnik-4-diag*, never push), their worktrees removed. 3bda: only tron-bp2*/bp3*/bp4* gate worktrees remain. Still unmeasured: performance at the three new heads (the bodies' Pending measurement sections).

## 2026-10-21 follow-up (jhan's answers to "What to tell Ben")
- jhan's decisions: #1, #2, #8 fixed in a NEW draft PR #5098 (branch jhan-vnnik-1-5047-fixes from bgamari/vnnik-1, base bgamari/vnnik-1, head 887fa6bd58 = ade89a9d9c + 3 commits: hetero zero row via set_k_row, the two probes + gof.hpp comment (cherry-pick of d142089c00), the apply_dense_amx_page comment; label Skip benchmarks; body bodies/pr1fix-body.md). #3 and #7 accepted. #4 answered (PR 4957 / #5086 removes the decline). #5 explained (extra 256-byte stack copy per row in set_k_row(expr), not bf16 itself). #6 -> memory pr4956-description-names-after-5047. #9 answered (yes: merge 5047, then take #5086/#5087/#5094 into the PR branches in order, #5098 first). #10 -> issue #5097 (Performance, claude-code-assisted, assignee jhan-positron) + root-cause workflow wf_163ce000-641 (source diff, -O3 objdump compare via lcheck -c -o, prefill-vs-decode model, adversarial verify, synthesis to scratch ksroot/root-cause.md).
- 3bda: jhan said Rhys is using it (who: rhys on pts/0, guard says idle, no lease). No build, unit test or perf run started for #5098. The #5098 3bda gate (bp1f/bp1fv) and the issue #5097 profile (perf stat/record on /var/tmp/jhan/tron-b47b and tron-b47h runtron, kill-switch cell l8b p8192) wait until jhan says the machine is free. GitHub CI is #5098's build/test gate meanwhile.
- Page updates: Ben-PR4956.html items carry "Decision 2026-10-21" lines (template page_template.html); Ben-stack-PR4957-4959.html Short version reworded (jhan did not understand "moved every decision into the cache" and "82 verified objections").
- PR #5098 round 1 (jhan, 2026-10-21 19:2x UTC): three inline comments on t/t_llama_unit.cpp = remove the comments that narrate the change (two probe comments, one assertion comment). Done: fixup folded into the probe commit, head db76973fdd pushed (force-with-lease). Explanation moved into the body's How-to-review item 2. Slip: overwrote jhan's body edits once, restored (see pr-body-refetch-before-edit). CI: draft needs label "Run CI" + reopen (added); run 39662512337 at the new head.
- CI at db76973fdd (run 39662512337): Lint, Build Tron, Test host, Test, Test FPGA, Test ingest all success (2026-10-21 ~20:1x UTC). #5098 is green; 3bda gate still pending jhan's go-ahead.
- PR #5086 round 1 (jhan 2026-10-21 20:45Z, k_vnni.hpp:110): the three comment lines above panel_offset are unnecessary. Removed, folded into the panel-accessor commit (bd49b6f5a2 -> 16ad7409b3), head 3258fcbe69 pushed (force-with-lease). status.json: branch 2 head 3258fcbe69 with gate_head 9a8045836a (assemble_body.py prints `ok at <gate_head>`); body Verification says the 3bda runs are at 9a8045836a, three deleted comment lines from the head. Live-body compare done BEFORE the edit this time (only the Verification line differed).
- Status page VNNIed-K-in-place/PR4956-4959/Ben-review-response-status.html (moved there by jhan 2026-10-21, directory is new; was random/) (2026-10-21 21:xx UTC): 17 items (5 PRs, issue 5097, 4 machine runs, pages, skill), dependency diagram with three lanes (GitHub merge chain serial, 3bda serial, parallel reviews); hand-written HTML, no generator.
- 2026-10-22: PR 5098 head b79dfb9fed (fix F2 for issue 5097 pushed, CI running, label Run CI present). Status page updated (State as of 2026-10-22 17:40 UTC). Ben-PR4956.html item 10 got the campaign update. Next machine item: performance at the three draft heads once review rounds settle.
- 2026-10-22 18:0x UTC: CI at #5098 head b79dfb9fed green (run 39823435486: Build Tron, Test, Test host, Test FPGA, Lint). PR 5022 (jhan-amx-kvmul16, kv_mul 16 Glimmer, against main, head 4c4b7b8864) vs PR 5047: ONE real conflict = its qk_rowmajor_128x4<operation_kv_mul>(pg.k(...)) hunk in apply_dense_amx_page, which 5047 moves into kv_cache.hpp try_score_k_amx (and page::k is gone); plus the t_amx_dispatch_dtype.cpp header comment rewritten by both; #5098 adds no conflict (probe adjacency only). Whichever lands second carries the move. Status page item 18 records it. Status page = VNNIed-K-in-place/PR4956-4959/Ben-review-response-status.html, "State as of 2026-10-22 18:00 UTC".
