---
name: pr2-split-execution
description: "2026-10-11: PR-2 of the PR 4424 split (branch jhan-vnnik-2-amx on jhan-vnnik-1-layout 82d05e94be) built from PR2-handoff.md: steps 0-5 done on claude-box (final head 0ee8671d35 = de39dc3de7 + 0ee8671d35, 10 files +362/-89, review fixes applied, matrices OK), chain DONE 15:01 UTC (our-half ok, cells +5.4/+9.5 % TPS vs main, host suite 93/1/1, BUT newoff vs new differs at token 247 in the CPU prompt-1024 smoke = handoff stop condition); PR #4887 OPENED 2026-10-11 16:4x UTC (draft on jhan-vnnik-1-layout, head 0ee8671d35) on jhan's word; codex posted 3 review passes 18:22 UTC (no defect; it edited the live body: Short version, CI wording, kill-switch subsection); token-247 probe DONE 18:47 UTC: exact tie (near-tie hypothesis confirmed), body PATCHed and reply comment posted 18:51 UTC (issuecomment-6112469713); no watcher runs (stopped on jhan's request 19:2x UTC); check the PR by hand when asked; jhan: 'execute PR2-handoff.md ... respond to codex comments' after the PR opens"
metadata:
  node_type: memory
  type: project
  originSessionId: 93888ee8-96f1-484e-b1b8-72a8beac9a6a
  modified: 2026-10-11T01:58:03.947Z
---

State on 2026-10-11 about 02:10 UTC (jhan: "Please execute PR2-handoff.md. codex will review the PR once it is created and post comments to PR, please respond to codex comments."):

- Record file: split-4424/split-status.md, headings "PR-2 Step 0" onward (the authoritative record; read it first).
- Branch jhan-vnnik-2-amx in worktree ~/workspace/ai-runs/tron-split-pr2, built by exec/pr2-20261011/build-branch.sh (messages in msgs/a.txt, b.txt; the step-5 block holds the review fixes). FINAL head 0ee8671d355863658bbf292a12e04a566ac1af29 (de39dc3de7 + 0ee8671d35). Not pushed. Do not rebuild (the chain tests this head).
- Step 5 DONE: workflow wf_f2fd0e23-1dd (71 findings, 29 should-fix) applied through the script; step 4 re-run clean (matrix-pr2b.log, pr2check-38b.log, format-pr2b.log). Decisions recorded in split-status.md 'PR-2 Step 5'.
- Step 6 chain DONE 2026-10-11 13:28-15:01 UTC (results exec/results/pr2-20261011/, cells exec/results/pr2-E-cpu/, marker released, serving up): all.done ok; E ok (new vs base +5.4 % / +9.5 % TPS, TTFT +100 ms / -523 ms; new vs head +12.9 / +24.3 %); C 93/1/1; D: CPU p8192 and FPGA p1024 all pairs as expected, CPU p1024 newoff vs new FIRST DIFFERENCE at generated token 247 (ids 624 vs 13), new vs head same token. STOP CONDITION of PR2-handoff.md (5.4, section 7): reported to jhan, PR not opened. Hypothesis near tie (AMX vs reader numerics); confirming measurement = forced run comparing top-2 logits at token 247 (needs a serving-down window).
- Step 7: body FINAL at exec/pr2-20261011/pr-body.md (filled by fill-body.py from the results, hand interpretation, two check workflows wf_7aa3e661-c4d and wf_052a93fb-690 folded in; do not re-run the fill script, it would overwrite the hand edits; the template is pr-body-template.md). If jhan says open: push, `gh pr create --draft --base jhan-vnnik-1-layout --label "Skip benchmarks" --assignee jhan-positron`, no Run CI.
- PR #4887 open; round 1 answered. Codex's 3 reviews (5484402300 tron, 5484402416 ben, 5484402562 wade) are review bodies (no inline comments); the reply is one PR comment (draft in exec/pr2-20261011/replies/pr-comment.md), posted after the probe result; the live body (codex-edited) is the base for every PATCH: exec/pr2-20261011/pr-body.md = live copy, pr-body-posted.md = what was posted. The probe's pending subsection in the body is filled with `gh api -X PATCH` after re-fetching.
- Trap 2026-10-11: runtron deletes the --intermediates-file path before opening (no FIFO); pkill -f with the script path in the ssh command kills the ssh session.
- Explainer for jhan: split-4424/track-decode-regression-by-logits-token-ties-explained.html (generator in the session scratchpad of 93888ee8; three check workflows applied). Two corrections it forced in PR #4887's body and comment: near ties within 2 notches = 12 steps (not 17); step 248's TVD is the second highest of the run (an exact tie explains it), not 'typical in every statistic'.

**Why:** the handoff requires checkpoints and a status file; a new session must not rebuild the branch or relaunch the chain without reading the record.
**How to apply:** read split-status.md "PR-2" sections first, then this file. Related: [[pr1-split-execution]], [[pr2-handoff-writing]].

UPDATE 2026-10-14 00:34 UTC: PR #4887 body rewritten under the PR-description skill and posted (exec/pr2-20261011/pr-body-v2.md,
3,066 words total, under 2,000 counted without the Words section, from 9,262). Previous body saved as
exec/pr2-20261011/pr-body-before-skill.md. Record in split-status.md "PR-2 and PR-4 descriptions rewritten".

UPDATE 2026-10-14 18:52 UTC (jhan: "cut the words to half and emphasize the tracker is 4444" for the Token identity paragraph): body
== exec/pr2-20261011/pr-body-v5.md (paragraph 65 -> 32 words; 1,667 counted words; new Words row for temperature 0 and
`--pay-for-determinism`). Verified byte for byte; the stored body has no final newline (fetch with python json, not `--jq .body`,
for an exact cmp). Record in split-status.md "PR-2 Token identity paragraph halved".
UPDATE 2026-10-14 18:57 UTC: two more cuts on jhan's ask, live body == exec/pr2-20261011/pr-body-v7.md (1,562 counted words):
the kill-switch open item is the one sentence "Issue #4444 is tracking the token identity issue." (no "Reviewers decide."), and
"Not measured at this head." is two sentences on the per-row store's TTFT cost and PR #4898. Record in split-status.md "PR-2 Open
items cut to two sentences". jhan is cutting the 4887 body section by section; expect more such asks, apply his wording verbatim.

UPDATE 2026-10-15 18:0x UTC: the 26 comment-check threads of review 5528392683 acted on per jhan's replies (accept / his
wording / reject): 24 edits applied as commit 65a9d655ec (9 files +54/-113, comments only), pushed, PR head 65a9d655ec, all
26 threads resolved (2 were jhan's own "Reject proposed"). Record: split-status.md "PR-2 (#4887): the 2026-10-15
comment-check threads applied"; tools and logs in exec/pr2-20261011/review-20261015/ (apply.py, step4.sh r1 in
exec/pr2-20261011/, commit-on-3bda.sh, post_replies.py). Body NOT touched (jhan edits it; live saved as
pr-body-v9-jhan-live-20261015.md, still names head 0ee8671d35). PR-1's base moved to dbcb28387f; PR-2 not rebased.

UPDATE 2026-10-15 18:1x UTC: body v10 posted (live == exec/pr2-20261011/pr-body-v10.md; Verification opening names head 65a9d655ec, six-word intro, measurement head 0ee8671d35 kept). Compare against v10 before any edit.
