---
name: debug-code-new-branch
description: "jhan directive 2026-08-30: debug-only code changes go on a NEW branch/worktree, never on the AMX PR branch jhan-amx-p0"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 528c65a4-1a65-45cc-a91c-9abf2f9fd11a
  modified: 2026-08-30T07:22:18.307Z
---

When root-causing needs instrumentation (counters, log labels, filters, kernel variants),
create a new branch off jhan-amx-p0 in its own worktree and put the debug code there.
Current one: branch `jhan-dd-debug`, worktree `~/workspace/ai-runs/tron-dd` (created 2026-08-30 for
the token-30 root cause, see intel-AMX/definitive-decode/debug-plan.html). Build it on
delphi-3bda inside `nix develop` into its own gen/.

**Why:** jhan (2026-08-30): "if you need to update code in order to do the root-cause, create a
new branch, do not change the AMX branch code if the code change are purely for debug purpose."
PR #3879 must stay a clean review target.
**How to apply:** never `git commit` debug code on jhan-amx-p0; if a debug patch turns out to be
production-worthy (e.g. an AMX engagement counter), propose it separately. Related:
[[runtron-determinism-recipe]], [[amx-tron-softattn-project]].
