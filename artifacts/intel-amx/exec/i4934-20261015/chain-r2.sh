#!/usr/bin/env bash
# i4934-20261015 round 2 (2026-10-15): copy of chain-fix.sh with fresh result names, so the final head's records do not reuse
# round 1's (campaign-fix.sh skips a cell whose log holds 'average tok/s', smoke-fix.sh an arm with a .tokens file).
# Made by fork-round2.py; only the replacements listed there differ. Original header follows.
# i4934-20261015 chain (runs ON delphi-3bda, detached): the three drivers back to back, each with its own END_BY and its
# own record. A failed or stopped driver does not stop the next: probe-fix.sh (our-half build and tests, then the
# whole-machine cells on jhan's order of 2026-10-15), identity-fix.sh (token identity, whole machine, jhan 2026-10-15
# "yes, run it"), mutate-fix.sh (our half). Log: exec/logs/i4934-chain.log.
# Usage (on 3bda): COMMIT=<full sha> PROBE_END_BY=<ISO> IDENTITY_END_BY=<ISO> MUTATE_END_BY=<ISO> [WAIT_FOR=<file>] bash chain-r2.sh
# WAIT_FOR: a file the chain waits for before its first driver (round 2: the comparison traces' done file).
# Stop: kill -- -<pid> (setsid: the pid is the group id); the running driver's exit handler restores serving and the marker.
set -u
D=/home/jhan/workspace/intel-AMX/exec/i4934-20261015
LOG=/home/jhan/workspace/intel-AMX/exec/logs/i4934-chain2.log
COMMIT=${COMMIT:?}; PROBE_END_BY=${PROBE_END_BY:?}; IDENTITY_END_BY=${IDENTITY_END_BY:?}; MUTATE_END_BY=${MUTATE_END_BY:?}
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
echo "=== chain started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') COMMIT=$COMMIT probe<=$PROBE_END_BY identity<=$IDENTITY_END_BY mutate<=$MUTATE_END_BY WAIT_FOR=${WAIT_FOR:-none} ==="
WAIT_FOR=${WAIT_FOR:-}
w=0
while [ -n "$WAIT_FOR" ] && [ ! -e "$WAIT_FOR" ]; do
  [ "$(date -u +%s)" -ge "$(date -u -d "$PROBE_END_BY" +%s)" ] && { echo "$(ts) past PROBE_END_BY while waiting for $WAIT_FOR: nothing run"; exit 1; }
  [ $w = 0 ] && echo "$(ts) waiting for $WAIT_FOR"; w=1; sleep 120
done
[ $w = 1 ] && echo "$(ts) $WAIT_FOR exists"
COMMIT=$COMMIT END_BY=$PROBE_END_BY bash "$D/probe-r2.sh"; echo "$(ts) probe-r2.sh rc=$? probe.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-r2/probe.done 2>/dev/null)"
END_BY=$IDENTITY_END_BY bash "$D/identity-r2.sh"; echo "$(ts) identity-r2.sh rc=$? identity.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-identity2/identity.done 2>/dev/null)"
COMMIT=$COMMIT END_BY=$MUTATE_END_BY bash "$D/mutate-r2.sh"; echo "$(ts) mutate-r2.sh rc=$? mutate.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-mutate2/mutate.done 2>/dev/null)"
echo "=== chain finished $(ts) ==="
