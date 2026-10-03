---
name: pr4596-claude-review-20260929
description: "2026-09-29/30 exhaustive Claude review of PR 4596 at 04da001cb5: verdict approve with nits (0 must-fix, 7 should-fix, 76 nit, 20 info); page PR3879/new-PRs/new-counters/claude-review.html (generator + data in exec/review-20260929/); five should-fix test gaps CLOSED by 7 test-only commits pushed 2026-09-30, PR head 0f784c44ff; open should-fix: R1-M13 (PR-body perf claims measured at cbf1bb6c0c) and R1-M27 (T3 has no sample count)"
metadata:
  node_type: memory
  type: project
  originSessionId: c1e2475d-c671-4e92-9fc3-579c9ced20ea
  modified: 2026-09-30T04:51:36.045Z
---

jhan asked (2026-09-29, ultracode on): /tron-code-review of PR 4596 -> claude-review.html -> /plain-english check;
then "add unit tests to address the 5 gaps, after they pass, push".

State (2026-09-30):
- Reviewed head 04da001cb5, diff base 66c7bb8db1. 19 lenses, 128 raw findings, 106 merged, 3 refuters each
  (reachability / evidence / intent), 103 survive, 3 rejected. Verdict approve with nits. No wrong number, crash
  or race found in production paths.
- Should-fix (7): R1-M1 no test drives model::state::forward with stats on; R1-M2 path bits never read back
  through token_jobs_by_path_set; R1-M8 T2/T3/T4 hooks in run_attention_job untested with stats on; R1-M9
  note_fpga_pass call site untested; R1-M15 a case pinned raw-hook misuse; R1-M13 PR-body A/A + objdump numbers
  measured at cbf1bb6c0c (14 commits before head); R1-M27 T3 (wall_cycles_w0) has no sample count.
- Closed 2026-09-30 by test-only commits on jhan-attn-path-stats: 7f86648d10 (M15), 5eb8fa0419 (M2),
  492345f04c (M8), 5b6a5deb51 (M9), 4094b51dde (M1), 4c70f04604 (M1 follow-up: atomic listener counter,
  the test had a data race), 0f784c44ff (M8 follow-up: named literals). PR head 0f784c44ff. Each test was
  mutation-checked (deliberate production break -> new assertion fails -> reverted). git diff 04da001cb5..
  0f784c44ff -- h/ is empty. Full runs at 0f784c44ff on claude-box: 12/12 pass (+ USE_HW_ATTN=1 arm).
- Posted test-data comments (5902483127 / 5902523541 / 5902534762) verified: every number recomputes;
  the run log names binary tip=bff317e0d3, not 04da001cb5 (same end values); worker-leaf "snapshot at forward
  142" is a 240 ms sequential read; 44 % of each attention worker's decode time is outside every PR timer.
- Page: claude-review.html (~750 KB, 98 finding cards, nits/info collapsible, follow-up section). Artifact
  https://claude.ai/artifact/9TnzzUSE5MqfQ6qkbhzKH6 (republish by file path from this folder; from another
  session pass the URL as `url`). Generator + data + workflow scripts + test
  summaries preserved in ~/workspace/intel-AMX/exec/review-20260929/.
- Not done: no PR comment posted (jhan did not ask); PR body still stale (R1-M13 + samples); T3 sample
  count (R1-M27) undecided.

Traps: (1) the implementer sub-agent pushed 4094b51dde despite "do not push"; recovered by pushing the two
follow-up changes as new commits (no force push). (2) See [[workflow-journal-reconstruction-trap]] for
the journal-order and 64k-output traps. (3) The plain-English pass edits by exact string replacement in
the data JSON; overlapping edits leave ~10 % unmatched -> run a second pass.

**Why:** next steps (PR body refresh, T3 count decision, reviewer replies) start from this state.
**How to apply:** regenerate the page from exec/review-20260929/ (python3 gen_review.py out.html with data/
beside it); line numbers in findings are of 04da001cb5 for h/ files and shift for t/ files after the push.
