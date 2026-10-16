---
name: bash-local-expansion-trap
description: "bash `local a=$1 b=\"$a\"` leaves b empty (every word of one local/declare is expanded before any assignment); under set -u it aborts with 'a: unbound variable'. It killed the i4934 driver on 2026-10-15 after serving-down. Dry-run every 3bda driver in a stub sandbox before launch."
metadata:
  type: project
---

In bash, `local x=$1 y="$x"` (also `declare`, `export`, `readonly`) expands every word of the statement before the builtin
assigns any of them, so `y` sees the OLD value of `x` (empty, or `x: unbound variable` under `set -u`). The i4934 campaign
driver (exec/i4934-20261015/probe-fix.sh, 2026-10-15 01:52 UTC) died that way in its first trace_one call, after it had
taken Bill's marker and production serving down: the exit handler restored both, but the whole-machine window was lost
until the relaunch after the nightly.

**Why:** a driver's late steps (traces, cells, builds) are never executed before launch, so a one-word bug there costs a
whole machine window; `bash -n` does not catch run-time expansion errors.

**How to apply:** (1) one `local` per dependent assignment (`local a=$1; local out="$RES/$a"`); grep new scripts with
`grep -nE '^\s*local .*=\$[a-z_]+' ` and look for a right-hand side that names a sibling of the same statement. (2) Before
launching a 3bda driver, run it once in a sandbox: copy the scripts with their paths rewritten (sed on the exec dir,
/var/tmp/jhan, /dev/hugepages, the nix path), stub runtron, build2.sh, lib-guard.sh, bill-share.sh, dut.sh, systemctl and
nix with tiny scripts, and check that every step line and done file appears (pattern: the session scratchpad dry.sh of
2026-10-15, described in VNNIed-K-in-place/issue4934/status.md). Related: [[issue-4934-fix]], [[nfs-running-script-stale-handle-trap]].
