#!/usr/bin/env bash
# i4934-20261015 chain (runs ON delphi-3bda, detached): the three drivers back to back, each with its own END_BY and its
# own record. A failed or stopped driver does not stop the next: probe-fix.sh (our-half build and tests, then the
# whole-machine cells on jhan's order of 2026-10-15), identity-fix.sh (token identity, whole machine, jhan 2026-10-15
# "yes, run it"), mutate-fix.sh (our half). Log: exec/logs/i4934-chain.log.
# Usage (on 3bda): COMMIT=<full sha> PROBE_END_BY=<ISO> IDENTITY_END_BY=<ISO> MUTATE_END_BY=<ISO> bash chain-fix.sh
# Stop: kill -- -<pid> (setsid: the pid is the group id); the running driver's exit handler restores serving and the marker.
set -u
D=/home/jhan/workspace/intel-AMX/exec/i4934-20261015
LOG=/home/jhan/workspace/intel-AMX/exec/logs/i4934-chain.log
COMMIT=${COMMIT:?}; PROBE_END_BY=${PROBE_END_BY:?}; IDENTITY_END_BY=${IDENTITY_END_BY:?}; MUTATE_END_BY=${MUTATE_END_BY:?}
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
echo "=== chain started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') COMMIT=$COMMIT probe<=$PROBE_END_BY identity<=$IDENTITY_END_BY mutate<=$MUTATE_END_BY ==="
COMMIT=$COMMIT END_BY=$PROBE_END_BY bash "$D/probe-fix.sh"; echo "$(ts) probe-fix.sh rc=$? probe.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-20261015/probe.done 2>/dev/null)"
END_BY=$IDENTITY_END_BY bash "$D/identity-fix.sh"; echo "$(ts) identity-fix.sh rc=$? identity.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-identity/identity.done 2>/dev/null)"
COMMIT=$COMMIT END_BY=$MUTATE_END_BY bash "$D/mutate-fix.sh"; echo "$(ts) mutate-fix.sh rc=$? mutate.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-mutate/mutate.done 2>/dev/null)"
echo "=== chain finished $(ts) ==="
