---
name: pending-move-amx-worktrees
description: "PARTLY DONE 2026-09-01: tron-dd and tron-fence-amx moved to ~/workspace/ai-runs/ (jhan request, exec scripts repointed); tron-amx still at ~/workspace/tron-amx, not yet requested; moved trees need a fresh cmake configure before their next build"
metadata:
  type: project
---

Status 2026-09-01 ~22:00Z: jhan asked to move tron-dd and tron-fence-amx; done with
`git -C ~/workspace/tron worktree move` -> ~/workspace/ai-runs/tron-dd (branch jhan-dd-debug) and
~/workspace/ai-runs/tron-fence-amx (branch jhan-amx-fence, HEAD 8fd1e7798d). All exec/ scripts that
named the old paths were repointed (fence-20260831/*, perfstat-20260831/run-perfstat3.sh, dd/*,
jeremy-measure-20260831.sh, single-attn-20260901/*). NOT moved: ~/workspace/tron-amx (PR #3879 branch
jhan-amx-p0) - jhan did not ask; ask before moving it.

Consequence to remember: the moved trees' gen/ build directories still record the old source path
(CMAKE_HOME_DIRECTORY); a `cmake --preset` in the new location refuses until gen/CMakeCache.txt is
removed (then a full rebuild, ~5 min per configured arm observed for incremental builds; a clean
build is longer). The binaries already in gen/ (runtron.fence, .fcanon, .samirror, .sacanon) still run
from their new gen/ (RUNPATH is $ORIGIN-relative).

**Why:** jhan keeps agent-created folders under ~/workspace/ai-runs/ ([[workspace-ai-runs-layout]]).
**How to apply:** use the ai-runs paths everywhere; if jhan asks to move tron-amx, repeat the same
steps (verify no runtron/build/lock, git worktree move, repoint exec/ + memory paths, notify any peer
session sharing the tree). Related: [[debug-code-new-branch]], [[single-attention-measurement]].
