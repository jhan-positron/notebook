---
name: tron-worktree-prune-trap
description: ~/workspace/tron (on NFS /home) registers about 100 worktrees under /var/tmp/jhan on delphi-3bda's local disk; from any other host they all show as "prunable", so never run `git worktree prune` there except on delphi-3bda; remove a single dead entry by deleting .git/worktrees/<name> instead (done 2026-10-21 for pdjn-wt)
metadata:
  type: project
---

On 2026-10-21, `git -C ~/workspace/tron worktree list` run on claude-agentsrv showed every worktree under /var/tmp/jhan/tron-* as "prunable" (about 100 entries, for example tron-pr4424ci, tron-vnnik7, tron-main1010). Those directories exist on delphi-3bda's local /var/tmp, which agentsrv does not mount. A `git worktree prune --dry-run` listed them all for removal.

**Why:** /home is an NFS share, so the repository metadata is shared, but /var/tmp is per host. Pruning from the wrong host deletes the registrations of live worktrees on delphi-3bda.
**How to apply:** never run `git worktree prune` in ~/workspace/tron from agentsrv, claude-box or sw-dev-01. To drop one dead worktree, check its `.git/worktrees/<name>/gitdir` points at a path that no longer exists anywhere, then `rm -rf .git/worktrees/<name>` (done for pdjn-wt on 2026-10-21 after /scratch/jhan/pdjn-wt was deleted, see [[scratch-jhan-prune-review-2026-10]]).
