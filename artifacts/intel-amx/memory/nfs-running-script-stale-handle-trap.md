---
name: nfs-running-script-stale-handle-trap
description: "2026-09-22: a bash script that runs on delphi-3bda from the NFS home dies with 'error reading input file: Stale file handle' when the file is replaced on claude-box in ANY way (sed -i, mv over it, editor save) — not only by in-place writes; copy to a new name instead and point new invocations at it"
metadata:
  type: feedback
  originSessionId: d7314eec-6275-458e-8946-af0dec5dd459
  modified: 2026-09-22T21:20:59.876Z
---

Observed 2026-09-22 21:18 UTC (issue #4525 first machine test, exec/i4525-20260922/smoke.sh): the smoke.sh
process running on 3bda finished its five runtron runs and then died with
`smoke.sh: error reading input file: Stale file handle` before the verdict lines ran. Cause: while it ran,
I replaced the file on claude-box with `sed -i` (new inode + rename) and later with `mv new old`. bash reads a
script incrementally from an open fd; over NFS the unlinked old inode's handle goes stale, so the next read
fails. The in-place-write variant of this trap (bash re-reading shifted bytes) was already known
[[vnnied-k-in-place-project]]; rename-replacement is NOT safe either on NFS.

**Why:** the exec/ scripts live on the NFS home and are executed on 3bda; any edit of a running script,
however atomic on the client, kills the remote process at its next read.
**How to apply:** never touch a file that a running 3bda process executes (chain drivers, smoke/campaign
scripts, lib-guard.sh, dut.sh). Fix bugs in a COPY with a new name (build2.sh, chain2/3/4.sh pattern) and
launch or reference the copy; a driver that calls `bash "$C/smoke.sh"` per step must be killed and relaunched
as a new file if smoke.sh has to change. Python files are read whole at start and can be edited between runs.
Data files (logs, smoke.txt) are safe to append to. Related: [[worktree-prune-nfs-trap]], [[nfs-attr-cache-build-trap]].
