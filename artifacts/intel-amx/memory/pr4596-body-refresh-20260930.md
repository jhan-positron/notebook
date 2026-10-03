---
name: pr4596-body-refresh-20260930
description: "2026-09-30: PR 4596 description refresh delivered as files only (jhan applies): new-counters/pr-body-20260930.md (new body), pr-body-20260930.patch + pr-body-20260930-patch.md (unified diff + change register), pr-body-live-20260930.md (live body fetched 23:4x UTC, jhan's 09-25 22:31 edit); objdump refresh at 8670da7f0b in exec/results/attnstats-20260930-objdump/; PR head moved to 8c95514924 (merge of main) mid-session"
metadata:
  type: project
---

jhan (2026-09-30, after Wade's approval at 441e81178b): "update PR description first since some of the verbose and
data are obsolete ... preserve the current, only correct or delete the obsolete ... plain-english ... generate md patch
file and md new description files, do not update PR directly."

Delivered in PR3879/new-PRs/new-counters/: pr-body-live-20260930.md (the fetched live body, 117 lines, jhan's last GitHub
edit 2026-09-25 22:31 UTC = round-3 state), pr-body-20260930.md (new body, 155 lines), pr-body-20260930.patch (unified
diff, `patch` applies and reproduces the new body byte for byte), pr-body-20260930-patch.md (change register table +
the same diff fenced). NOT applied to GitHub. VERSION 2 (after jhan's 'no change history' feedback, see [[pr-description-no-history]]): present tense, no round narration, old objdump/test-count/sample data replaced by the 2026-09-30 and 2026-09-29 data, the round-3 verification bullet deleted, the cbf1bb6c0c instruction-count paragraph deleted; provenance kept as commit id + date.

What the patch changes (all verified against `git show 441e81178b:<path>`, never the worktree): Short version "per
attention worker" -> "per pool worker"; Words: continuous-batching class rule, listener, pool worker; T1 = forward_scope
inside model::state::forward (W2), T3/T4 per layer on attention worker 0 with no *_w0 keys in worker leaves (W5), T5
both join modes inside T2 (W1); tests: 12 -> 17 t_attn_stats cases, new sections/cases of t_llama_unit /
t_amx_dispatch_dtype / heterogeneous_scheduler_compile, new t/assertion_signal.hpp; "two apply_page_range arguments
main lacks" was WRONG -> one (batch_queries has no default; main's call has 8 args, PR and #4557 pass `visible`);
design page path PR1/counter.html -> new-counters/counter.html; A/A labels "final commit" -> cbf1bb6c0c + new paragraph
(no A/A after cbf1bb6c0c, three off-path bool-test changes, objdump refresh); cross-check bullets labeled by binary
(first commit 9b3832eb4b, kill switch 2026-09-24), the "empty totals" claim corrected (forwards leaf was zero-filled,
{} since 1430736b2a); leaf samples replaced by the 2026-09-29 bff317e0d3 runs (stderr from the 23:24Z run, worker
leaves from the 23:38Z run, = jhan's PR comments 5902523541/5902483127, every number re-grepped in exit-reports.txt);
Verification gains round 4 (3bda), 04da001cb5 (3bda as 8670da7f0b), the 8 later commits (claude-box counts at
441e81178b: t_llama_unit 220,153/60, hetero 2,783/3, dispatch 1,612/1, compute 124/4, page_share 61/4), the merge
8c95514924, the CPU-attention runs.

objdump refresh (read-only, nice 15, cores 72-75, 50 s, 2026-09-30 23:45 UTC): script copy
exec/attnstats-20260930-objdump/objdump-check.sh (the 09-24 script hardcodes OUT under results/attnstats-20260924 and
would have OVERWRITTEN the 09-24 record; the 09-24 objdump-check.txt already is the cbf1bb6c0c run, the 9b3832eb4b
numbers survive only in the PR body). Result exec/results/attnstats-20260930-objdump/objdump-check.txt at 8670da7f0b
(= 04da001cb5 + comments; 3bda never built anything later): apply_page_range 384 instantiations, largest 12,708 B /
2,217 insns, 0 lock / 0 rdtsc / 0 xadd, total +79,633 B (+6.5 %) vs main; run_attention_job largest 4,941 B, 9 rdtsc
(main 4,281 / 8).

Facts learned: the T5 "54,179,328 cycles = 20.07 ms" number of pr-body-round4.md exists in NO result file (dropped);
the pr-body-round4.md "18 cases" and PR comment "19 cases" were right for their commits (19 at 04da001cb5, 18 at
0f784c44ff, 17 at 441e81178b after W8); exec/results/attnstats-20260925-fpga/ = FPGA-attention run at cbf1bb6c0c
(8u + 1u, headon2/headkill2) never cited in the body (left out, offered to jhan); PR checks at head show only Cursor
Bugbot + Graphite (tron CI lanes not in statusCheckRollup); mergeStateStatus BLOCKED after the merge push.

**Why:** jhan applies the patch by hand; the next session must not re-derive the verification or overwrite records.
**How to apply:** before any `gh pr edit --body-file`, re-fetch the live body and diff it against
pr-body-live-20260930.md ([[pr-body-refetch-before-edit]]); if jhan edited in between, re-apply pr-body-20260930.patch
onto the fresh copy. TRAPS: (1) the tron-attn-stats worktree HEAD moved DURING this session (another session merged
main -> 8c95514924, pushed 23:52Z): line numbers from the worktree were inconsistent between two reads; take code
facts from `git show <sha>:path`; (2) `cd` in Bash prints a directory listing here, use absolute paths / git -C;
(3) a 40-word list sentence remains in the tests bullet on purpose. Related: [[attn-stats-pr-implementation]],
[[wade-pr4596-round5-response]], [[pr4596-claude-review-20260929]].
