---
name: pr3-split-execution
description: "2026-10-12: PR-3 of the PR 4424 split: PR #4898 OPEN (draft on jhan-vnnik-2-amx), head dfafd13dce = the measured 80bce9a08d + one test commit (review round 1 fix: finished count read at the main call return, late helper; M3 mutation verified on 3bda); round 1 (codex, 5 passes) ANSWERED 16:27 UTC: body PATCHed to codex proposed text + band correction + 3 additions, PR comment 6128332242 and inline reply r4250232288 posted; record in split-status.md PR-3 sections; PR-4 not started; reply to further rounds only when jhan asks"
metadata:
  node_type: memory
  type: project
  originSessionId: 7b9490fe-ca59-4987-be07-8363990fa2cb
  modified: 2026-10-12T01:08:44.304Z
---

State on 2026-10-12 about 01:10 UTC (jhan: "execute PR3-handoff.md"):

- Record file: split-4424/split-status.md, headings "# split-status: PR-3 of the PR 4424 split" onward (the authoritative record; read it first).
- Branch jhan-vnnik-3-shared-save in worktree ~/workspace/ai-runs/tron-split-pr3, built by exec/pr3-20261012/build-branch.sh (messages msgs/a.txt, b.txt, c.txt; the step-5 block applies edits/<name>.old -> .new). FINAL head 80bce9a08d682677f970505eb0f314538a3f4aa8. Not pushed. Do not rebuild (the chain tests this head); the script refuses once origin/jhan-vnnik-3-shared-save exists.
- Step 5 applied (details in split-status.md "PR-3 Step 5"): store_block block-index assert; Note opening names the per-token store; overload comment; assert messages; TronCpp.hs comment + Var; the duplicate t_k_vnni_layout SECTION removed (block-save case now 153 assertions -> t_k_vnni_layout expected 1011585 in 5); t_llama_unit three-thread section rewritten (exact claim count, helper_windows, cut-at-change check, second window on operation 1). Not applied: wade-6 (mwaitx wait primitive, design), wade-8 (why 128), wade-11 (duplicate-offset branch).
- Chain: exec/pr3-20261012/chain2.sh (= chain.sh + modes STOP_AFTER_OUR_HALF / WHOLE_MACHINE_ONLY; chain-finish.sh exit handler). The first launch (chain.sh pid 2292134, holding) was killed at 01:12 UTC after jhan pointed out the free hour before the nightly. Run 1 (our half) pid 2692198 launched 01:12:59 UTC with STOP_AFTER_OUR_HALF=1; run 2 (whole machine) pid 2702542 launched 01:13:05 UTC with WHOLE_MACHINE_ONLY=1 START_NOT_BEFORE=2026-10-12T13:00:00Z END_BY=2026-10-13T01:30:00Z (waits for run 1's all.done = ok, which is present since 01:44 UTC). Log exec/logs/pr3-20261012-chain.log; results exec/results/pr3-20261012/ and pr3-E-cpu/. Stop with `ssh delphi-3bda kill -- -<pid>`. Poller wait-chain2.sh (log exec/pr3-20261012/wait-chain2.log). If run 1 fails, kill run 2 before relaunching. Expected chain.done on a good run: "failed host=failed smoke=ok/ok/ok E=ok" (the t_proxy_llama31 venv exception); judge C from host-suite-pr3.txt.
- Review round 1 DONE 2026-10-12 16:27 UTC (details in split-status.md "PR-3 review round 1"): fix commit dfafd13dce pushed (checks: step4 r3 clean, fix1-check.sh on 3bda ok incl. M3), body = replies/body-round1.md (live copy pr-body.md), comment 6128332242, inline reply 4250232288. A further round: same pattern (fix as a focused commit, fix1-check-style verification on our half, PATCH after re-fetch, one comment).
- Step 7 DONE: PR #4898 https://github.com/positron-ai/tron/pull/4898 opened 2026-10-12 15:5x UTC (draft, base jhan-vnnik-2-amx, label Skip benchmarks, assignee jhan-positron, no Run CI); posted body = exec/pr3-20261012/pr-body-posted.md (live copy pr-body.md; re-fetch before any PATCH). The construction script is retired (branch published): a repair is a focused fourth commit on the published head; merges of PR-2 with --no-ff; never rebase. Former step-7 plan was: `python3 exec/pr3-20261012/fill-body.py --check`, then without --check -> pr-body.md; hand-write the *_TEXT and CI_STATUS placeholders; plain-English Check + facts-vs-results workflow on the body; then push and `gh pr create --draft --base jhan-vnnik-2-amx --head jhan-vnnik-3-shared-save --title "VNNI K: shared block save" --body-file ... --label "Skip benchmarks" --assignee jhan-positron` from the worktree (no Run CI). Stop conditions of PR3-handoff.md section 7 apply (new vs head or new vs new2 differ; newoff vs new differs other than at token 247 at CPU p1024; a watchdog abort; a mutation check that does not fail its case; A2 or plugin check failure).
- Clock facts: the first launch slot (22:30 UTC 2026-10-11) had passed at start (00:26 UTC 2026-10-12), so the chain uses the second slot.

**Why:** the handoff requires checkpoints and a status file; a new session must not rebuild the branch or relaunch the chain without reading the record.
**How to apply:** read split-status.md "PR-3" sections first, then this file. Related: [[pr3-handoff-writing]], [[pr2-split-execution]], [[pr1-split-execution]].

UPDATE 2026-10-14 00:27 UTC: PR #4898 body rewritten under the PR-description skill and posted (exec/pr3-20261012/pr-body-v2.md,
2,650 words total, 1,989 counted without the Words section, from 10,841). Previous body saved as
exec/pr3-20261012/pr-body-before-skill.md. Record in split-status.md "PR-3 description rewritten". Drafted by a fork,
checked by a fresh agent (pr3check), posted with re-fetch and byte compare (scratchpad postbody.py).

UPDATE 2026-10-14 19:24 UTC (jhan: same token-identity cut as 4887): live body == exec/pr3-20261012/pr-body-v6.md (1,663 counted
words), built on jhan's own web edit of 19:19 UTC (saved as pr-body-v5-jhan-edited.md; eight Words rows removed by him). Token
identity paragraph 81 -> 37 words, kill-switch open item -> "Issue #4444 is tracking the token identity issue.", new Words row for
temperature 0 / `--pay-for-determinism`, `new2` added to the base/new row. Trap: a body edited in the GitHub web UI comes back with
CRLF line endings; strip CRs before diffing, and Python text-mode reads normalize them. Record in split-status.md "PR-3 (#4898) Token
identity paragraph halved".
