---
name: stack-reopened-20261015
description: "2026-10-15: the four stack PRs were CLOSED and re-opened with fresh conversations on the SAME branches: 4868->4956, 4887->4957, 4898->4958, 4901->4959; conflicts resolved by merge commits 23:0x UTC, all four MERGEABLE; use the new numbers and heads"
metadata:
  type: project
---

On 2026-10-15 21:2x UTC jhan asked for new PRs with identical code and zero threads (the old ones had too many
historical comments). He chose: close the old PRs, reuse the same branches.

- Mapping (old CLOSED -> new OPEN): #4868 -> #4956 (ready), #4887 -> #4957 (draft), #4898 -> #4958 (draft),
  #4901 -> #4959 (draft). Same base chain main <- 1-layout <- 2-amx <- 3-shared-save <- 4-tail-block.
- Heads since 23:0x UTC (one merge commit each, cascaded down the stack): a5697f86d3 (merges main 76bb0bf3f4),
  26b86a279a, b39765ec29, 6b081187e1. Code lines identical to the old PRs; comment conflicts resolved with PR-1's
  reviewed wording winning. All four MERGEABLE (#4956 BEHIND = main moved on, no conflict). Checks m1/m2/m3b/m4 passed.
- Bodies: live == split-4424/exec/newprs-20261015/new/<new>-v2.md (compare before any edit); every `#old` number mapped
  to the new one, head sentences name the merge commits. Old PRs carry one "Superseded by #new" comment.
- Issues #4444 (jhan's comment 6158706248), #4934, #4955 cite the new numbers.
- Record: split-4424/split-status.md, sections "re-opened with fresh conversations" and "Conflicts resolved by merges".

**How to apply:** all PR work (bodies, comments, checks, CI watchers) now targets 4956/4957/4958/4959 at the merge
heads; the pr1..pr4-split-execution memories describe history under the old numbers. Worktrees
~/workspace/ai-runs/tron-split-pr{1,2,3,4} are at the heads. See [[pr1-split-execution]], [[pr2-split-execution]],
[[pr3-split-execution]], [[pr4-split-execution]], [[tron-commit-hook]].
