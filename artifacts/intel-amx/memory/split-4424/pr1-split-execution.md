---
name: pr1-split-execution
description: "2026-10-10: PR #4868 (PR-1 of the PR 4424 split) open at 82d05e94be after review round 1 (jhan asked 'respond to review comments'): 4 fix commits, 3bda re-run pr1b-20261010 green, description rewritten in plain English (exec/pr1-20261010/pr-body.md), 5 thread replies + 1 PR comment posted; status file split-4424/split-status.md; PR-2 not started"
metadata:
  node_type: memory
  type: project
  originSessionId: 8fea3a6f-7ad9-451b-8c8e-0abdf5692000
  modified: 2026-10-10T06:32:35.320Z
---

State on 2026-10-10 ~07:00 UTC (jhan: "Execute create-PR1-handoff.md"; confirmed the run ends with opening the PR):

- Branch jhan-vnnik-1-layout (worktree ~/workspace/ai-runs/tron-split-pr1) = a711aeee831c7c4da24ce3737d93dd0c76df1149:
  six topical commits from the probe tree 76a0160b72 (06c9f48b8c caa0f38f72 28064e6f84 d1afc70bf1 13474d0b3f dc859f0cdc),
  the PR-1-only commit c3334a079f ("the layout needs no AMX dispatch", D2 + comment rewrites + the Note's
  "requires TRON_AMX_DISPATCH" clause dropped), merge of origin/main 72308ec90c (clean). Rebuilt by the deterministic
  script exec/pr1-20261010/build-branch.sh (messages in exec/pr1-20261010/msgs/). Local tag pr4424-pre-split-0a5334ccb6.
- claude-box checks: 22-cell and 38-cell lcheck matrices MATRIX OK on a711aeee83; both negative controls behave;
  clang-format 19.1.7 rc 0 (after rewrapping the 100-column amx_attn_iface diagram line into two lines inside the
  kernels commit); diff --check 0; no cassert; "temporary until" x2; no A/S/T symbol.
- 3bda chain exec/pr1-20261010/chain.sh (pid 2796735, log exec/logs/pr1-20261010-chain.log, results
  exec/results/pr1-20261010/): A (VNNI build + 6 tests + kill-switch t_llama_unit/t_amx_numerics), A3 (option on +
  dispatch off), B (row-major), F (format), A0 (main 72308ec90c runtron.main1010), then bill-share take, serving down,
  D smokes (cpu p1024/p8192, fpga p1024; arms base new new2 newoff), E cells (pr1-E-cpu: qwen3-4b tp2 8u p1024/p8192,
  arms base new newoff baseoff, 3 reps), C host suite, serving up, marker release. Poller exec/pr1-20261010/wait-chain.sh.
- Body draft exec/pr1-20261010/pr-body.md with placeholders {{MEASUREMENTS}} {{VERIFICATION}} {{PERF_ALONE}} {{DIVERGENCE}}.
- DONE 15:0x UTC: body filled, branch pushed, PR #4868 opened (https://github.com/positron-ai/tron/pull/4868). Chain results: our-half ok; smokes ok (new==new2, newoff==new; new vs base first difference at token 83 at prompt 1024 under CPU and FPGA attention, identical at prompt 8192); E: new vs base TPS -6.2/-11.0 %, TTFT +26/+123 %; newoff vs baseoff TPS +4.4/+5.3 %; host suite 93/1/1 (venv). Remaining: watch CI on #4868; PR-2 only after jhan has seen PR-1.
- (superseded) Next: fill the body from exec/results/pr1-20261010 (tests-*.txt, smoke/*/smoke.txt, host-suite-pr1.txt,
  results/pr1-E-cpu/summary.md), checkpoint to jhan, `git push -u origin jhan-vnnik-1-layout`, `gh pr create --base main
  --title "VNNI K: the layout, its AVX-512 reader and the FPGA staging path" --body-file ... --label "Skip benchmarks"
  --assignee jhan-positron` (no --draft, no Run CI), record the PR number in split-status.md.

**Why:** the handoff requires checkpoints and a status file; a new session must not rebuild the branch or relaunch the chain.
**How to apply:** read split-4424/split-status.md first; it is the authoritative record. Traps seen this session: the
auto-mode classifier allowed the detached ssh launch this time; an ssh remote command with `|` inside single quotes needs
`bash -s <<'EOF'`; the `cd DIR && ...` Bash hook prints a directory listing. Related: [[split-4424-plan]].

UPDATE 2026-10-10 ~18:3x UTC (review round 1 done): head 82d05e94be = a711aeee83 + dbe32b8af4 (k_vnni row ops assert token < Rows) + 07f072bdf1 (t_phase1_integration stages K through the scratch, per-element swizzle check, unique tag) + 7633d56c8f (t_llama_unit keeps main's bounds for row-major K) + 82d05e94be (poison comment, k_destination_row). Verified on 3bda by chain2/chain3 (results exec/results/pr1b-20261010, cells pr1b-E-cpu): mutation check passes (stride removed -> case fails), row-major build passes main's bounds, smokes/cells/host suite as before. Description = plain-English rewrite (jhan's checker's proposal + fixes), checked by 3 agents (wf_daa456c5-21a). Traps this round: chain step F used HEAD^2 (only valid for a merge head); a pgrep -f pattern matched its own ssh command line; fill-body.py mapped build times by file order and swapped two; Catch2 exit code of the mutant run (42) is not the failed-assertion count, quote the summary line instead. TPS question answered with the 4-arm decomposition (3 agents, wf_b00598b7-9a4).

UPDATE 2026-10-13 ~18:45 UTC (jhan: "PR 4868 description is overwhelming ... cut in half"): review page written at
split-4424/PR1-4868/PR-desc-review.html (generator gen_review.py lived in the session scratchpad only). Measured on the live
body after the VNNI-packed edit ([[vnni-packed-wording]]): 6,191 words (wc -w), 20 sections; The changes 1,654 and
Verification+host suite+CI 1,089 hold 45 % of section words; median merged tron body (last 60) is 300 words. Importance per
section by the Wade reader test (check 9) plus round-1 evidence: Decides / Records / Explains. Three designs (est., incl.
122 heading words): A merge duplicates 20->12 sections, 3,120 (-50 %), recommended; B halve every section, 3,150 (-49 %);
C reviewer core in the body + "Verification record" PR comment, 2,780 (-55 %). Nothing applied to the body; jhan chooses.
Evidence found: after posting on 10-10 a GitHub edit removed 23 of the 35 glossary rows (970 words); the posted file
exec/pr1-20261010/pr-body.md has 7,162 words.
UPDATE 2026-10-13 ~20:10 UTC: on jhan's decision ("yes, let's consolidate"), Design A of PR1-4868/PR-desc-review.html
now merges Measurements into Verification (one provenance paragraph; subsections Builds and tests, Token identity,
Performance, CI coverage): the merged group 2,177 -> 800 words est., Design A total 2,915 (-53 %), 11 sections.
Designs B and C unchanged (3,152 / 2,775). Still nothing applied to the live body.
UPDATE 2026-10-13 ~21:3x UTC: Design A EXECUTED on jhan's "Please execute Design A": body v3 (exec/pr1-20261010/pr-body-v3.md)
posted and verified, 6,202 -> 4,096 words (-34 %), sections per the PR-description skill (section 4 = How to review this PR,
Q-and-A; Measurements merged into Verification). Record in split-status.md "PR-1 description, Design A executed". The
2,915 estimate was wrong (tables 614 words). Stale "PR #4424 remains open ... until all four are open" sentence kept.

UPDATE 2026-10-14 01:20 UTC: the token-divergence topic (first difference at generated token 83) is tracked in ONE place, issue #4444
(status comment 6158706248 of 2026-10-14, text in split-4424/issue-4444/status-20261014.md). The near-tie explanation is confirmed
by two forced runs (PR #4887 token 247, PR #4901 probe p83-20261013 token 83); the kill-switch rollback contract (narrow the
promise, or keep a row-major rollback binary) is still undecided; a model-level bound is not started. PRs 4887/4898/4901 bodies
(pr-body-v3.md) point their kill-switch item at the issue; jhan did the same in 4868 by hand. jhan is editing the 4868 body:
do not touch it.

UPDATE 2026-10-15 18:4x UTC: head 7ce378934f (dbcb28387f = the style-check threads applied, 7ce378934f = three follow-ups, see
[[checks-20261015]] and [[rule0-diff-only]]), pushed, CI running. Open: his question about a clean, no-history
look for reviewers (options A-D in chat; B = new PR from a new branch name at the same commit recommended). The body is still
jhan's to edit.
NOTE 2026-10-15 19:0x UTC: PR 4868 is CONFLICTING with main (only config/test-benchmarks.json timing rows; predates the
2026-10-15 commits), so GitHub runs no CI on new pushes until main is merged in (jhan's call). The 2026-10-15 comment
commits made PR 4887 conflict with its base in 6 files (9 comment hunks); PR-2 needs the new PR-1 tip merged in, or the
stack rebase. Details in split-status.md "follow-up commit 7ce378934f" section.
