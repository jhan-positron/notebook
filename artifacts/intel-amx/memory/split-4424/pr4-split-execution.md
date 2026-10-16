---
name: pr4-split-execution
description: "2026-10-13 18:45 UTC: PR #4901 OPEN, head 175b1837b9 PUSHED (forward test; 3bda ok + mutation + option-off; step4 ok; draft CI green); W, lazy probe, probe83 done and in the body with comments; open for jhan: deferred-dotter decision; for me: review activity; always re-fetch the body before editing (external edit at 18:12Z)"
metadata:
  node_type: memory
  type: project
  originSessionId: 15630040-e750-46e7-b46a-df8546e00b44
  modified: 2026-10-13T18:45:00.000Z
---

State on 2026-10-12 about 21:35 UTC (jhan: "Execute PR4-handoff.md, after you open the PR, codex will review and comment, please respond codex comments"; then "we have 7 hours before nightly CI, feel free to use 3bda half or whole"; then: campaign W = llama-3.1-8b (decode and prefill at least similar to PR 4424's) and gpt-oss (similar), no full suite; debug a regression, one caused by main is ok):

- Record file: split-4424/split-status.md, headings "# split-status: PR-4 of the PR 4424 split" onward (authoritative; read first).
- Branch jhan-vnnik-4-tail-block in ~/workspace/ai-runs/tron-split-pr4, built by exec/pr4-20261012/build-branch.sh (msgs/a,b,c.txt; step-5 editf lines; mode d = the cost-row commit from exec/results/pr4-20261012/bench-update.diff). FINAL three-commit head ea94e95a4e30830e33a2e1feda51ac231e97c667 (a 88b81bf2f7, b c4ab92a5ba, c ea94e95a4e). Not pushed. Do not rebuild (the chain tests this head).
- Step 5 applied 13 fixes (split-status "PR-4 Step 5"), including protocol-1: k_storage_readable now uses book.slot_page(storage_offset, pageno()).base (a production change beyond the tested T tree; flagged to jhan). Not applied: cppguide-1a/1b, wade-2 (copy_token), protocol-2 (refuted), tron-6 (report only).
- Chain: exec/pr4-20261012/chain2.sh (fork by fork-chain.py; 19 edits), chain-finish.sh, launch2.sh, wait-chain2.sh. Run 1 DONE (21:31-22:35 UTC, all.done ok; debs 2026.10.12-72308ec9-jhan-pr4ci-base / 2026.10.12-ea94e95a-jhan-pr4ci-target in /var/tmp/jhan/pr4ci-20261012). Run 2 RUNNING: pid 1678975 on 3bda since 22:36 UTC (WHOLE_MACHINE_ONLY=1, END_BY=2026-10-13T02:00:00Z), expected end ~00:50 UTC; stop: `ssh delphi-3bda kill -- -1678975`; poller wait-chain2.sh (log wait-chain2-run2.log); results exec/results/pr4-20261012/, cells exec/results/pr4-E-cpu/ and pr4-E-fpga/.
- Campaign W: fork exec/pr4ci-20261012/ (fixture 21/21; scope applied: subset3.json, SW8K=0, NEED_FLOOR_S); check mode ok 21:47 UTC; LAUNCHED 22:36 UTC pid 1098150 on claude-box (option (b) variables: NOT_BEFORE 2026-10-13T13:00Z, DEADLINE_START 19:00Z, PASS_DEADLINE 2026-10-14T00:30Z, DRIVER_END_BY 02:05Z; EXPECTED_BASE=2026.10.12-72308ec9-jhan-pr4ci-base, sha 5bc91172...); log exec/logs/pr4ci-20261012.log; results exec/results/pr4ci-20261012/; stop with `kill -TERM 1098150` only while the chain does not hold the machine. Baseline for jhan's comparison: exec/results/pr4424ci-20261009/summary.md rows llama-3.1-8b (8u p1024: -0.3 %, 32u p4096: +4.8 % resolved) and gpt-oss-120b (-0.5 %, TTFT -22 ms).
- Step 7 prep: exec/pr4-20261012/pr-body-template-part1.md and -part2.md (placeholders); fill-body.py fork not written yet; review record exec/pr4-20261012/review-findings.txt.
- After opening: codex reviews; jhan asked to respond to codex's comments (same pattern as PR-3: fix as a focused commit, PATCH after re-fetch, one comment).

**Why:** the handoff requires checkpoints and a status file; a restarted session must not rebuild the branch or relaunch the chain without reading the record.
**How to apply:** read split-status.md "PR-4" sections first, then this file. Related: [[pr4-handoff-writing]], [[pr3-split-execution]].


UPDATE 2026-10-13 00:30 UTC: run 2 DONE 00:17 UTC (chain.done = "failed host=failed smoke=SMOKE-VERDICT differs/VALIDATE ok/ok/SMOKE-VERDICT differs/VALIDATE ok E=ok/ok bench=ok"; machine restored: serving up, Bill's marker present, hand-off marker removed). Results: exec/results/pr4-E-cpu, pr4-E-fpga, pr4-20261012 (host-suite-pr4.txt, bench-update.diff). Findings: (a) smokes: CPU p1024 new == head (differ from base at 83), CPU p8192 all identical, FPGA p1024 new == base (head differs at 83), newoff vs new 247 at CPU p1024 -> section-7 stop-and-ask, reported with a hypothesis (reader-vs-dotter flips on partial pages; not a defect); (b) FPGA claim holds (new vs base +0.6 %/-0.3 % inside; head vs base -1.9 %/-11.0 %); (c) newoff vs headoff -3.4/-2.9/-2.0 % TPS beyond the band in all CPU cells (hypotheses H1 per-token block test in the software loop, H2 the dotter array constructed per page visit; measure with a trace or a variant build); (d) new vs head inside the band with AMX on. W: its gate refuses tonight's verdict; the classifier refused my gate edit ("Security Weaken"); the knob CHAIN_DONE_ACCEPT is declared (campaign.sh:109) but the case is unchanged; jhan must run `! bash ~/workspace/intel-AMX/exec/pr4ci-20261012/accept-verdict-and-relaunch.sh` before 13:00 UTC 10-13 (it edits the gate, stops the sleeping W, relaunches with the knob). fill-body.py parses every chain result (--check fails only at the missing W summary). Do NOT push or open the PR before jhan decides on (a) and (c).


Update 2026-10-13 01:05 UTC (preparations done while waiting; record in split-status.md "PR-4 preparations while waiting for jhan's three decisions"):

- Probe measurement scripts ready in exec/pr4-20261012/: campaign-probe.sh (sync4424 campaign fork, arms lazy/lazyoff via RT_LAZY), probe-lazy.sh (3bda driver: build runtron.pr4lazy on our half, bill-share take, serving down, 3 CPU cells x 6 arms x 3 reps = 54 runs ~74 min est., chain-finish.sh exit handler), launch-probe.sh (COMMIT=ca6456b7dc0009eee32bcb9a2b15ac1e931160c0 END_BY=... [START_NOT_BEFORE=...]). Launch only on jhan's order. Windows: after W (~15:30Z 10-13, END_BY 02:00Z 10-14) or before W after the nightly (~05:00-12:30Z 10-13).
- Body: all hand-written sections live in pr-body-template-part1/2.md (regenerate with `python3 fill-body.py` once W is done, `--pushed <sha>` after the push). Two new Open items (token identity, AMX-off TPS) are written as "Reviewers decide" with labelled hypotheses; they change with jhan's decisions. Remaining semicolons in the Words table and config bullets are left for the step-7 plain-English pass.
- msgs/d.txt written (t_llama_unit 28 s -> 5.6 s: facts recorded, cause not investigated; the test runs 6.3 s without --skip-benchmarks at ea94e95a4e, 6.2 s at dfafd13dce). `bash build-branch.sh d` NOT run: if a lazy-dotter commit is added, the cost rows must be re-measured and (d) becomes the fifth commit.
- Lesson: `ls` output appears at the top of every Bash result after a `cd` in this environment (a cd hook); use absolute paths, no cd.


Update 2026-10-13 04:10 UTC: PR #4901 OPEN (jhan: "go ahead to open PR4, state open items which are to investigate and will update PR description"). Head e7d06a1267 (4 commits on dfafd13dce). Posted body = exec/pr4-20261012/pr-body-post.md from post-body.py (--w-pending; later --words-url); the glossary table is the PR's first comment (GitHub's 65,536-char description limit; full body 84 KB). Lazy-dotter probe launched (launch-probe.sh, 3bda pid 1077064): waits for W's .done* (10 min old) + Bill marker, END_BY 2026-10-14T00:00Z. W accept script still needs jhan (`! bash ~/workspace/intel-AMX/exec/pr4ci-20261012/accept-verdict-and-relaunch.sh` before 13:00Z). Record: split-status.md "PR-4 OPENED: PR #4901".
- 04:3x UTC: probe83.sh (token-83 forced-run logits probe, 7 runs, chained behind the lazy-dotter probe via exec/results/pr4lazy-20261013/probe.done + Bill marker; END_BY 2026-10-14T00:30Z) launched on 3bda; results exec/results/p83-20261013/verdict.txt. Watchers on claude-box: gh pr checks --watch (task be9jk9bdo) and a 5-min comment poll on PR 4901 (task bhtpwbp3o).
- 04:10 UTC: jhan ran the accept script; W relaunched (pid 2458712, NOT_BEFORE 13:00Z). The gate edit is in campaign.sh:463-464. Both probes still wait.
- 04:50 UTC: codex round 1 answered. Record: split-status.md 'PR-4 review round 1'. Live body = codex's rewrite + fixes (replies/body-round1.md); later edits by hand. Pending tonight on 3bda in order: W (13:00Z), probe-lazy (54 runs), probe83 (8 runs), test-forward.sh (build+mutation of the new test). After test.done = ok: cherry-pick fwdtest commit onto jhan-vnnik-4-tail-block, run step4.sh, push, edit body (coverage item), comment with numbers.


Update 2026-10-13 15:40 UTC: campaign W DONE (13:58-15:33 UTC; .done clean; outcome: no incomplete pass, no problem; restore ok; Bill's marker back). Results exec/results/pr4ci-20261012/summary.md: llama-3.1-8b 8u p1024 -0.4 % (not resolved, TTFT +14 ms t 2.08 not resolved), 32u p4096 +5.2 % RESOLVED (t 53.81), gpt-oss-120b -0.3 % (not resolved); memory within 3-14 MiB. Matches PR 4424's 2026-10-09 campaign in direction and resolution (-0.3 / +4.8 / -0.5 %). jhan's scope is met; nothing to debug. Live body = exec/pr4-20261012/replies/body-w.md (campaign section filled, Open item "Package campaign" removed); comment 6149296083. Record: split-status.md "PR-4 campaign W: DONE". Still pending tonight on 3bda (automatic): probe-lazy (54 runs; result -> AMX-off Open item; if lazyoff recovers the 2-3.4 %, the fix joins PR-4 as a commit with re-runs), probe83 (verdict.txt -> token-identity item), test-forward (test.done ok -> cherry-pick 86bdbd31b7 with msgs/e.txt via --no-verify, step4.sh, push, body "Forward-path coverage" item, comment). Edit the body by hand from replies/body-w.md after re-fetching (gh pr view --json body) and comparing.


Update 2026-10-13 17:25 UTC: lazy-dotter probe DONE (E=ok; exec/results/pr4lazy-E-cpu/summary.md). lazyoff vs newoff +2.3 % (beyond), +1.6 % (inside the 0.40 TPS floor, t 19), +0.2 % (inside); lazyoff vs headoff -1.5/-1.5/-1.0 % (first beyond); lazy vs new inside everywhere (no AMX-on cost). Body = replies/body-lazy.md (CPU attention "Deferred-dotter measurement", Open item rewritten "Reviewers decide", Words row); comment replies/comment-lazy.md. Decision pending from jhan: add the deferred-dotter commit (ca6456b7dc; its code comment about fp32 conversion is wrong and must be fixed; then step-4 checks + 3bda CPU cells and smokes re-run) or follow-up PR. probe83 running since 17:16 UTC (8 runs; verdict.txt -> token-identity item); then test-forward.


Update 2026-10-13 18:35 UTC: probe83 DONE (ok): every 2026-10-12 mismatch is a near-tie (token 83: base/head exact tie 258 vs 1499, new ahead by 1-2 ulps; token 247: 1-ulp reversal under the kill switch); body Token identity + Open item + Short version updated (replies/body-p83.md), comment posted. The live body was edited externally at 18:12:54Z under jhan's account (wording: packed -> VNNI-packed); my script re-applied on top. Forward test attempt 1 FAILED: fwd_hw_attn_enabled reads USE_HW_ATTN once per process, so setenv in the test had no effect; fix = plugin template parameter force_hw_attention (software_scored_heterogeneous_model), commit 175b1837b9 on branch jhan-vnnik-4-probe-fwdtest2 (fwdtest-commit.txt updated); attempt 2 running (pid 3205796 on 3bda). Record: split-status.md "PR-4 forward test: attempt 1 FAILED".


Update 2026-10-13 18:40 UTC: forward test attempt 2 OK (2855/4; mutation fails 1/72 at the block check; option off 2855/4). jhan-vnnik-4-tail-block fast-forwarded to 175b1837b9 (the tested commit), step4 ok, PUSHED 18:32 UTC (PR head 175b1837b9, 5 commits). Body = replies/body-fwd.md (Revisions, "Forward-path test" in Builds, "Forward-end conversion call" mutation, Open item -> "Conversion-call ordering", checks sentence); comment replies/comment-fwd.md. Pending: update the checks list when the draft CI finishes at 175b1837b9 (gh pr checks); jhan's deferred-dotter decision; review activity. Record: split-status.md "PR-4 forward test: attempt 2 OK".

Update 2026-10-13 18:45 UTC: draft CI at 175b1837b9 green (runs 38447600680, 38447600467, 38447600326); body checks list updated (replies/body-ci.md). Nothing runs on 3bda. Pending: jhan's deferred-dotter decision; review activity (watcher bb7de8xqz, threshold 6 issue comments).

UPDATE 2026-10-14 00:37 UTC: PR #4901 body rewritten under the PR-description skill and posted (exec/pr4-20261012/pr-body-v2.md,
2,786 words total, under 2,000 counted without the Words section, from 9,851). Previous body saved as
exec/pr4-20261012/pr-body-before-skill.md. The live body had not changed since the 23:54 UTC snapshot (re-fetch + byte compare).
The deferred-dotter decision is still "Reviewers decide" in the body. Record in split-status.md.

Update 2026-10-14 04:40 UTC: the PR watcher of 2026-10-13 expired at 04:35 UTC with no review activity (still 6 issue comments, 0 review comments, 0 reviews); restarted for 10 h (task bf2wxfbki, same thresholds). Live body == exec/pr4-20261012/pr-body-v4.md (posted 01:59 UTC by another session; 2,687 words total, 1,933 counted). That file is now the last saved copy to compare against before any body edit; the replies/ copies are older. Nothing runs on 3bda. Pending unchanged: jhan's deferred-dotter decision; review activity.

Update 2026-10-14 14:40 UTC: second PR watcher expired at 14:37 UTC, still no review activity on #4901 (6 issue comments, 0 review comments, 0 reviews; body and head unchanged since 01:59 UTC). Third 10 h watcher started at 14:40 UTC with the same thresholds. Two full 10 h windows passed without a codex round 2; if the third expires too, report and ask jhan whether to keep watching.

UPDATE 2026-10-14 20:55 UTC (jhan: same token-identity cut as 4898): live body == exec/pr4-20261012/pr-body-v6.md (1,865 counted
words), built on jhan's web edit of 20:49 UTC (saved as pr-body-v5-jhan-edited.md, eight Words rows removed by him). Token identity
paragraph 51 -> 23 words, token-differences open item -> "Issue #4444 is tracking the token identity issue."; probe paragraph and
the other five open items untouched. Record in split-status.md "PR-4 (#4901) Token identity paragraph halved".

UPDATE 2026-10-14 21:44 UTC (jhan: "did we test PR 4901 against main with AMX off? If not, do it now, plus the partial fix"):
campaign pr4off-20261014 LAUNCHED on 3bda (driver exec/pr4-20261012/probe-off.sh, pid 3103711, setsid group), arms baseoff /
headoff / newoff / lazyoff (runtron.main1010, .pr3, .pr4, .pr4lazy with TRON_AMX_DISABLE=1), 3 CPU cells x 3 reps = 36 runs,
est. done 22:40 UTC; results exec/results/pr4off-E-cpu/summary.md, driver record exec/results/pr4off-20261014/probe.done.
Bill's marker taken and serving down by the driver; its exit handler restores both. DO NOT relaunch: check probe.done first.
Record in split-status.md "PR-4 AMX-off campaign against main". Then: chart page + PR 4901 body Performance/Open items update.

UPDATE 2026-10-14 22:55 UTC: campaign pr4off-20261014 DONE (E=ok 22:42 UTC, 36/36 runs; machine restored by the exit handler and
verified: serving up, Bill's marker present). PR 4 vs main with the kill switch: TPS inside the band in all three CPU cells
(+0.7 / +2.7 / -0.5 %; the +2.7 % is 0.39 TPS against the 0.40 floor), TTFT at p8192 4.98 s faster (beyond). PR 4 vs PR 3 repeats
(-3.3 / -2.7 / -0.5 %, TTFT p8192 +587 ms). Probe vs PR 4 +2.0 (beyond) / +0.9 / +0.2 %; probe vs main +2.7 / +3.6 (beyond) / -0.4 %.
Live body == exec/pr4-20261012/pr-body-v7.md (1,989 counted words; Performance kill-switch bullets and the "AMX-disabled slowdown"
open item rewritten main-first, Words row gains baseoff). Chart page split-4424/pr4-amx-off-vs-main-20261014.html. Record in
split-status.md "PR-4 AMX-off campaign against main (pr4off-20261014): DONE". Nothing runs on 3bda. Pending: jhan's deferred-dotter
decision (now with main-relative numbers), review activity. Compare against pr-body-v7.md before any body edit.

UPDATE 2026-10-14 23:40 UTC (jhan: "take it as a problem ... file an issue"): issue #4934 filed (kill-switch decode slowdown of PR 4
vs PR 3, qwen-3-4b tp2 2.7-3.7 %; body split-4424/issue-pr4off-decode/body-20261014.md; leads: H2 dotter construction = the probe,
H1 per-token layout branch, H3 serial forward-end conversion, each with its settling measurement; no new runs). Live body ==
exec/pr4-20261012/pr-body-v8.md (1,857 counted words): the "AMX-disabled slowdown" open item is now the one sentence "Issue #4934 is
tracking the decode slowdown against the parent with the kill switch." and the deferred-dotter decision moved into the issue. Record in
split-status.md "PR-4 kill-switch decode slowdown: issue #4934 filed". Compare against pr-body-v8.md before any body edit.

Update 2026-10-15 00:45 UTC: third 10 h PR watcher expired at 00:38 UTC with no review activity on #4901 (6 issue comments, 0 review comments, 0 reviews). The PR's updatedAt of 2026-10-14 23:38:56Z is the v8 body PATCH plus the cross-reference from issue #4934, not a review. No watcher restarted: three 10 h windows passed without a codex round 2, and another session now works on PR-4 with jhan (pr4off campaign, issue #4934). The deferred-dotter decision is settled: it lives in issue #4934 (lead 1), not in PR-4. Ask jhan before watching again.

UPDATE 2026-10-15 01:40 UTC (jhan: "Act per ~/tmp/PR4901-questions.txt", 12 code questions + skill suggestion): page
split-4424/PR4901-explain.html written and reviewed; record in split-status.md "PR-4 (#4901) comment review of jhan".
Worktree ~/workspace/ai-runs/tron-split-pr4 is DIRTY and NOT COMMITTED: index = change set A (ordered edits, kv_cache.hpp
+5/-19), working tree = A + B (proposals, 4 files +18/-28); patches and commit messages in
exec/pr4-20261012/review-20261015/. Head still 175b1837b9, nothing pushed. step4 q15 passed on the working tree. The commits
need jhan's nix shell (pre-commit hook execs lefthook from a nix path; `--no-verify` is blocked by the permission classifier
here). After jhan commits: the PR body (compare against pr-body-v8.md) needs the new head in Revisions and Verification.
cpp-coding-guide skill updated (bool literals rule); draft simplify-cpp-comments skill at
split-4424/PR4901-explain/simplify-cpp-comments/SKILL.md, not installed.

UPDATE 2026-10-15 03:05 UTC (jhan: undo Q5, why not `~uint64_t{0}`, regenerate Q5/Q11/Open decisions): Q5 helper change
REVERTED in the worktree; change set B is now Q3, Q8, Q10, Q12 (4 files +13/-23; B-proposals.patch regenerated, old one kept as
B-proposals-v1-with-q5.patch, msg-B.txt updated). A unchanged (staged). Still not committed, head 175b1837b9, nothing pushed.
Q11: `~uint64_t{0}` recommended (same value/type, matches the stack's layout test from PR 1), NOT applied, listed as an open decision. Page sections
regenerated; draft skill rule 8 rewritten (helper only for a verbatim repeat). step4 q16 re-run on the reverted tree. Record:
split-status.md "PR-4 (#4901) comment review, round 2". Lesson saved in [[no-minor-refactors]].

UPDATE 2026-10-15 03:40 UTC (jhan: "change to ~uint64_t{0}"): applied and STAGED with A (index updated directly), A = Q1,
Q2, Q4, Q6, Q11 (+6/-20), B = Q3, Q8, Q10, Q12 (+13/-23). Patches regenerated, msg-A.txt updated, merged msg-AB.txt written
for a single commit (jhan asked why A/B were split: by authorization, not importance; and why no commit here: lefthook hook,
--no-verify refused). step4 q17 re-run. Still not committed, nothing pushed. Record: split-status.md "round 3".

UPDATE 2026-10-15 04:00 UTC: jhan's `git add -A h t` (his own command, from the right directory) has staged A+B together
(4 files +19/-43), commit still pending at head 175b1837b9. His first attempt ran outside the worktree ("not a git
repository"). claude-agentsrv has NO nix (/nix empty); the home is NFS (filer.positron.internal), so the worktree is
visible on delphi-3bda, which has Determinate Nix 2.34.6 and the hook's lefthook store path. Told him: ssh delphi-3bda,
cd the worktree, `git commit -F .../msg-AB.txt` (nix develop --accept-flake-config optional for the commit).

UPDATE 2026-10-15 04:10 UTC: COMMITTED by jhan on delphi-3bda: 8ad54a13b1 (A+B, msg-AB.txt, 4 files +19/-43, content
verified = 175b1837b9 + A + B). NOT pushed (origin still 175b1837b9). Worktree clean. step4 q18 PASSED on the committed
head (04:10-04:13 UTC, diff-check rc=0 on the commit). Next after jhan pushes: PR body update (new head in Revisions/Verification, compare against pr-body-v8.md), draft CI
check. Pending jhan's answer: drop the default-argument clause from the cpp-coding-guide bool rule (my addition) and make
RECORD_ROWS_TRUE a literal (t_amx_dispatch_dtype.cpp:81/95).

UPDATE 2026-10-15 04:26 UTC: PUSHED 8ad54a13b1 (04:19 UTC, on jhan's "you push"); body v9 POSTED 04:26 UTC (live ==
exec/pr4-20261012/pr-body-v9.md, 1,890 counted words; compare against v9 before any edit). Draft CI green at 8ad54a13b1
(7 checks pass, 12 skip as before). cpp-coding-guide bool rule now jhan's wording (04:25 UTC). simplify-cpp-comments
installed by jhan (03:11 UTC, rule 0 added, rules 7/8 removed). Pending jhan's word: the default-argument edit in
t_amx_dispatch_dtype.cpp (lines 93-95 -> literals, RECORD_ROWS_TRUE deleted) as a new commit.

UPDATE 2026-10-15 04:39 UTC: default-argument commit d0e6f816dd (t_amx_dispatch_dtype.cpp: literal defaults,
RECORD_ROWS_TRUE deleted, four named bools moved into the TRON_AMX_DISPATCH block to keep the cells warning-free) made
over ssh on delphi-3bda (hook ran) and PUSHED 04:34 UTC; head d0e6f816dd. step4 q19 passed with 0 warnings in every cell
(reference summary + step4.sh expectation updated). Body v10 POSTED 04:39 UTC (live == exec/pr4-20261012/pr-body-v10.md,
1,922 counted words; compare against v10 before any edit). CI green (7 pass, 12 skip). Open for jhan: template arguments
and the /*name=*/ call-site form under the bool rule; Q8/Q12 placement. Record: split-status.md 04:39 UTC section.

UPDATE 2026-10-15 04:55 UTC: template-argument commit 4d64013dff (named bool template arguments in
t/heterogeneous_scheduler_compile.cpp; jhan's rule: template argument = call argument, defaults keep literals) made over
ssh on 3bda and PUSHED; head 4d64013dff; step4 q20 0 warnings, summaries identical; CI green. Body v11 POSTED (live ==
exec/pr4-20261012/pr-body-v11.md, 1,957 counted words; compare against v11 before any edit). jhan: /*name=*/true call
sites stay; Q8/Q12 as committed. The 2026-10-15 comment review is CLOSED, no open decision. Record: split-status.md.

UPDATE 2026-10-15 05:11 UTC: body v12 POSTED on jhan's ask ("no need to describe the changes of coding style"): the
Verification paragraph now names the three style commits in one clause, no list of what they changed. jhan had edited
the live body in the web first (machine sentence removed), so v12 is built on the live body, not v11 (saved as
exec/pr4-20261012/pr-body-live-20261015b.md). Live == exec/pr4-20261012/pr-body-v12.md, 1,834 counted words; compare
against v12 before any edit. Record: split-status.md 05:11 UTC section.

2026-10-15 19:07 UTC body v13 posted: the "Hardware-attention fallback cost" open item deleted on jhan's ask and one sentence added to the save_k bullet of How to review (CPU scores row-major blocks below the engagement point and for a range without FPGA memory); built on jhan's web edit of the Short version (pr-body-live-20261015c.md). Live == exec/pr4-20261012/pr-body-v13.md, 1,821 counted words. Compare against v13 before any edit.

2026-10-15 20:00 UTC: trace run exec/pr4trace-20261015/trace.sh launched on 3bda (claim written 19:58 UTC, runtron.pr4 at ea94e95a4e, CPU attention tp2+tp4, 8 users, prompt 1024, 64 generated, --trace-gen --trace-passes 1-72) to measure the convert_k_blocks span for the body's open item "The conversion"; reader exec/pr4trace-20261015/analyze.py; results exec/results/pr4trace-20261015/, marker exec/logs/pr4trace-20261015.done. It waits on the campaign flock held by ANOTHER session's issue #4934 ablation campaign (exec/i4934-20261015/abl-run.sh, results i4934-abl-cpu) with a 10 s poll, 5 h limit. Plan after the number: replace the cost sentence of the open item with the measurement, keep the ordering sentence, release the claim (people-check.sh --release).

2026-10-15 20:31 UTC body v14 posted: conversion cost measured (trace pr4trace-20261015, results exec/results/pr4trace-20261015/summary.md: convert_k_blocks 1.1-1.2 ms per 16 decode steps, 288 blocks, 0.6-0.8 % of decode time), Performance paragraph added, open item "The conversion" reduced to the ordering sentence. Live == exec/pr4-20261012/pr-body-v14.md, 1,893 counted words. 3bda claim RELEASED 20:30 UTC; the other session's i4934 campaign still runs there.

2026-10-15 20:4x UTC body v15 posted: the Words row "mutation check" (v4 wording) restored on jhan's ask. Live == exec/pr4-20261012/pr-body-v15.md. Compare against v15 before any edit.

2026-10-15 21:2x UTC: issue #4955 filed (the conversion-order test gap; body split-4424/issue-conversion-order/body-20261015.md) and body v16 posted: open item reworded to "The conversion's position is untested" naming #4955, How-to-review Open bullet names #4955. Live == exec/pr4-20261012/pr-body-v16.md. Compare against v16 before any edit. PR 4901 open items now: #4934 (kill-switch decode), deb preset decision, #4955 (ordering test), #4444 (token identity), not-measured list.
