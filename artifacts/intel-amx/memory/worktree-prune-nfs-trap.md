---
name: worktree-prune-nfs-trap
description: Never run `git worktree prune` in the NFS-shared tron repo from claude-box; 3bda-only worktrees under /var/tmp/jhan look prunable and lose their admin dirs
metadata:
  type: feedback
---

Never run `git worktree prune` (or `git worktree add` on a path that
triggers auto-prune) in ~/workspace/tron or any of its linked worktrees
(tron-amx, ai-runs/tron-*) from claude-box.

**Why:** the tron repo is one NFS-shared .git; worktrees created on
delphi-3bda under /var/tmp/jhan/ do not exist on claude-box, so `git worktree
list` marks them "prunable" and prune deletes their .git/worktrees/<id> admin
dirs. On 2026-09-11 this broke six 3bda worktrees (tron-g1 = admin id
tron-g11, tron-g1canon, tron-p0perf, tron-qwen-pr1-amx, tron-qwen-pr1-clean,
tron-split-PR2-on). `git worktree repair` cannot recreate a missing admin dir.

**How to apply:** recover by recreating the admin dir by hand on 3bda:
`.git/worktrees/<id>/{gitdir = /var/tmp/jhan/<w>/.git, HEAD = FULL 40-hex
sha, commondir = ../..}` then `git -C /var/tmp/jhan/<w> reset -q` to rebuild
the index (working files untouched). A short sha in HEAD does not work. See
[[nfs-attr-cache-build-trap]] for the sibling cross-host trap.
