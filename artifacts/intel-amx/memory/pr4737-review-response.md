---
name: pr4737-review-response
description: "2026-10-01: PR #4737 (jhan-amx-vnniK-i4500 -> jhan-amx-vnniK, the issue #4500 row-major tail block + policy, draft) got a Codex review (5 inline comments + C++-guide note, posted under jhan's account); responses = 3 commits on 452b2052c9 (d8f6c479bc k_storage_ref param, a9923ddd97 comment passages, 9e813a8ce5 named literals); C1 (VNNI tests not in default CI) = reply only, jhan/CI owner decide; verification chain exec/pr4737-review-20261001/"
metadata:
  node_type: memory
  type: project
  originSessionId: 922a3361-aa01-4c82-918d-776e08c4d97d
  modified: 2026-10-01T23:50:01.484Z
---

Request (jhan 2026-10-01 ~23:10 UTC, ultracode): "Codex is creating PR and adding review comments to the PR, after
that, it will write the PR number to ~/tmp/PR-number.txt. Please respond to the review comments." PR = #4737
(draft, base jhan-amx-vnniK 30c4ac82cb, head 452b2052c9 at review time; Codex wrote the body and the review).

Review (review id 5386692119, comments 4161434893/902/905/910/920):
- C1 [P2] t_llama_unit.cpp:1952: the TRON_K_VNNI-guarded tests do not run in the default CI (gcp-nix.yml builds via
  nix/cmake-tron-test-build.nix without TRON_AMX_DISPATCH/TRON_K_VNNI; only the manual cmake-single-platform.yml
  sets them). HOLDS; pre-exists from PR #4424 (f4889f8072, 929fa94e42 added the flags to the legacy lane after the
  cutover 2f1ee29982). Reply only: options (a) flags in the nix test build inside #4424 (precedent PR #4505),
  (b) second nix configuration, (c) manual legacy run as evidence; decision = jhan + CI owner (nix lane) + #4424
  reviewers (whole suite would run the VNNI layout: TRON_K_VNNI is a PUBLIC definition). Deliberate-break CI run NOT done.
- C2 [P3] copy_storage_slot 6 params -> pass k_storage_ref: FIXED d8f6c479bc (also k_block_to_vnni_at; copy_from
  builds the ref from the physical slot, never k_storage_of = view-dependent).
- C3 item 4 "256-byte copy from a row-major block" wrong (callback returns k_row_if_row_major in place): FIXED a9923ddd97,
  plus the V sentence qualified (v_head_fn copies only when TRON_CHUNK_SIZE == 16) and the full.hpp in-callback remark.
- C4 bullet credited set_k_block with setting bits (note_k_block_saved after the last KV head does): FIXED a9923ddd97.
- C5 "tokens are the same either way" over-promises (dotter vs qk_group add order): FIXED a9923ddd97.
- G (review body) literals: FIXED 9e813a8ce5 (alignas(LINE_BYTES_64); k_vnni::BIT_1 + block_bit/offset_bit helpers;
  ROW_ALIGNED_TRUE/ROW_DMA_FALSE in k_vnni.hpp because PR #4557 has tron::VIEW_ALIGNED_TRUE in kv_cache_fwd.hpp not on
  this branch; sseq<1> dropped = default stride; EAGLE_STORAGE_SLOTS_1, BLOCK_COMPLETED_FALSE, CONVERTED_*; tests
  SUPPORT_EAGLE_TRUE, NEXT_ROW_1, REPEAT_FALSE, RECORD_ROWS_*, CONVERTED_*, PAGE_1/2, OTHER_OPERATION_1). Listed, not
  changed: index-zero args (39 test lines), suffix-check static_asserts, Catch2 names, TRACE strings, base lines.
  jhan's precedent 5051264d80 (PR #4557): bools and view flags named, sseq<1> kept bare.

Verification: syntax-only (lcheck2.sh, clang 19 zig, both -DTRON_K_VNNI and not) of t_k_vnni_layout, t_llama_unit,
t_amx_dispatch_dtype, heterogeneous_scheduler_compile = 0 errors at every step; clang-format 19.1.7 clean.
3bda chain exec/pr4737-review-20261001/run.sh (launched 23:47 UTC, our half, build2.sh of i4525-20260922; VNNI build in
/var/tmp/jhan/tron-i4500b: runtron + 7 tests, 5 run; row-major in /var/tmp/jhan/tron-i4500rm: 3 tests); results
exec/results/pr4737-review-20261001/{build-r1,tests-r1,build-r1rm,tests-r1rm}.txt. Reference at 452b2052c9: 5/5 + 3/3 pass.
Draft replies: session 922a3361 scratchpad replies/{C1..C5,G}.md (checked by workflow before posting).

TRAPS: `ssh host 'setsid nohup ... &'` hangs the ssh session (the detached child keeps the channel); use `ssh -n` and
a fresh connection to check; lcheck2.sh lives in the session scratchpad (copy from the b0cfc925 scratchpad; flags from
~/workspace/ai-runs/lcheck). The exec/ campaign folders live at ~/workspace/intel-AMX/exec, not under VNNIed-K-in-place/.

**How to apply:** after the chain: read tests-r1.txt/tests-r1rm.txt; if 5/5 + 3/3, push jhan-amx-vnniK-i4500, post the
replies (gh api .../pulls/4737/comments/<id>/replies; G and C1 as written), patch the PR body head line (re-fetch first,
[[pr-body-refetch-before-edit]]), then update this file with STATUS. Related: [[i4500b-policy-campaign]],
[[issue-4500-fix-implementation]], [[cpp-guide-literals-include-bools]], [[amx-ci-coverage-facts]], [[no-names-in-github-issues]].

STATUS 2026-10-01 23:58 UTC: DONE. Pushed jhan-amx-vnniK-i4500 = 9e813a8ce5 (PR head). 3bda chain: VNNI build 5/5 and
row-major build 3/3 pass at 9e813a8ce5 (assertion counts identical to 452b2052c9; builds 347 s + ~2 min, our half).
Replies posted: C1 r4161653875, C2 r4161654010, C3 r4161654161, C4 r4161654289, C5 r4161654407, G = issue comment
5942962731. PR body patched (head sha line; validation now lists 452b2052c9 results dated 09-30 and 9e813a8ce5 results
dated 10-01; hardware numbers remain from 452b2052c9). Reply drafts were fact-checked by wf_26d88e9e-f68 (12 agents):
caught f4889f8072 = PR #3879 not #4424, "about 500 guarded lines" -> 627 total / 81 under #ifdef, the C5 dates (09-30
fixS1==fix in 4 cells; 09-29 fix vs PR head first diff token 52 (65/128) / token 6 (114/128), attribution not proven),
k_vnni.hpp:328 -> 344 at the new head. OPEN for jhan: C1 decision (options a/b/c in the reply); the deliberate-break CI
run was not done; TPS/tokens not re-measured at 9e813a8ce5.

UPDATE 2026-10-02 00:1x UTC (jhan follow-ups, head now 721a12186b, pushed, PR body head line updated each time):
ffaaf09ec6 rewrote the k_layout_dense comment (mask semantics -> comparison), 195ef5d7a4 renamed ALL_BLOCKS_0XF ->
BLOCKS_PER_PAGE_MASK_0XF (jhan picked it from 5 options), 721a12186b removed BIT_1 (literal 1 in the bit helpers and
mask arithmetic; see [[cpp-guide-literals-include-bools]]). Follow-up PR comment posted. Comment/name-only changes:
the 3bda unit-test run at 9e813a8ce5 still covers the head (syntax-only re-checked in both builds each time).
UPDATE 2026-10-02: bb32a80774 (pushed) returns `true` directly in the row-major branch of k_layout_dense (jhan request); PR body head line updated.
UPDATE 2026-10-02 03:4x UTC: threads C2-C5 RESOLVED by Claude (jhan: "if no open questions, resolve"); C1 thread (CI coverage, t_llama_unit.cpp:1952) left OPEN: it holds the option a/b/c decision for jhan + CI owner.

C1 FOLLOW-UP 2026-10-02 03:54 UTC (jhan: "sure" to the CI simulation; "After the run returns good tomorrow, resolve C1"):
chain exec/pr4737-ci-sim-20261002/run.sh launched on 3bda (pid 3336073), waits for the nightly lease (run 36961332956,
clears ~11:30 UTC), then 3 host suites in /var/tmp/jhan/tron-i4500b at bb32a80774 via i4525-20260922/host-suite.sh:
head, break (tail-row scores zeroed in self_attention.hpp, must FAIL), restored. Results exec/results/pr4737-ci-sim-20261002/
host-suite-{head,break,restored}.txt + .done; log exec/logs/pr4737-ci-sim-20261002.log. Reference (PR 4424 body): 90 host
tests, 89 passed 1 skipped, 107 s. TODO when done and good: post the 3 results on the C1 thread (PRRT_kwDOKStajs6oLIEo,
reply to r4161434893) and RESOLVE it (jhan's instruction). Not the exact nix recipe (needs the 3-job plugin bundle, up to
4 h); say so in the reply. AGENTS.md = tron repo root file (Test policy section line 20).

C1 DONE 2026-10-02 14:0x UTC: chain pr4737-ci-sim-20261002 ran 13:32-13:59 UTC after the nightly (which ended 13:32, later than
usual): head 83/1/6 (6 heap_setup failures = hugepage slice files still held 10 min after the lease cleared: ENVIRONMENTAL),
break 86/1/3 (t_llama_unit "apply and join page ranges" :2143, t_generate_host, t_generate_host_2-fast = the break IS caught),
restored 89/1/0 (= PR 4424 reference). Posted on the C1 thread and RESOLVED it (all 5 threads resolved). TRAP fixed: host-suite.sh
wrote "ok" when test-host failed, because grep 'test-host rc=0' matched the line "build-test-host rc=0" (anchored with ^ now;
read the rc lines, not the .done file, for runs before 2026-10-02). TRAP: start a host suite a few minutes after the lease
clears, or clean /dev/hugepages/slice-*-of-8 first (i4500b/lib.sh has a cleanup) to avoid heap_setup failures.
