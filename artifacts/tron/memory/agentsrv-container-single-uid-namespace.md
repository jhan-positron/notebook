---
name: agentsrv-container-single-uid-namespace
description: claude-dev container on agentsrv maps only uid/gid 0 (uid_map "0 644434775 1"); chown to any other id fails EINVAL; tar as root needs --no-same-owner (TAR_OPTIONS); hit 2026-11-09 installing herdr-reviewr
metadata:
  type: project
---

The claude-dev container on agentsrv (hostname claude-agentsrv, shell is root, HOME=/home/jhan on NFS) runs in a user namespace that maps exactly one id: `/proc/self/uid_map` and `gid_map` are both `0 644434775 1` (checked 2026-11-09). Any `chown` to a uid or gid other than 0 fails with EINVAL "Invalid argument", on the overlay root as well as on NFS, so it is not an NFS root-squash issue.

Symptom seen 2026-11-09: `herdr plugin install persiyanov/herdr-reviewr` failed in its build step with `tar: herdr-reviewr: Cannot change ownership to uid 1001, gid 1001: Invalid argument` (GitHub release tarballs record owner 1001/1001 = the Actions runner; GNU tar as root restores owners by default). Fix: `TAR_OPTIONS=--no-same-owner herdr plugin install ...` (herdr build commands inherit the environment). Guide updated: random/from-claude/install-herdr-reviewr.md step 5.

**Why:** any installer or script that extracts a tarball as root inside this container, or that chowns to a non-zero id, will fail the same way. sw-dev-01's container is set up the same way by agentsrv-setup.sh and most likely shares the limit (not verified there).

**How to apply:** when a tar extraction or chown fails with "Invalid argument" in claude-dev, check `/proc/self/uid_map` first and add `--no-same-owner` (or `TAR_OPTIONS=--no-same-owner` when a third-party script calls tar). Related: [[herdr-code-review-plugins]], [[herdr-restart-restore-agentsrv]], [[claude-box-alpha-layout]].
