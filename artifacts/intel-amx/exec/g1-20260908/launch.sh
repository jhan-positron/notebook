#!/usr/bin/env bash
# Queue the G1 campaign on delphi-3bda (run ON delphi-3bda). Idempotent.
# A tiny waiter polls the CI lease and only then starts g1-campaign.sh, so the
# campaign file can still be edited until the lease clears (bash reads a running
# script incrementally from NFS; a waiting campaign could not be edited).
# The campaign then does its own waits: idle-serving takeover, PR 0b chain done,
# Bill absent (monitor CLEAR), campaign guard. See g1-campaign.sh header.
EXEC=~/workspace/intel-AMX/exec
if pgrep -f 'g1-20260908/g1-campaign[.]sh' >/dev/null || pgrep -f 'g1-20260908 waiter' >/dev/null; then
  echo "already queued/running: $(pgrep -af 'g1-20260908' | grep -v pgrep | cut -c1-80 | tr '\n' ';')"; exit 0
fi
pgrep -f 'bill-watch[.]sh' >/dev/null || echo "WARNING: bill-watch.sh is not running; the campaign will wait forever (monitor state stale)"
mkdir -p "$EXEC/logs"
echo "$(date -u +%FT%TZ) queued: g1-20260908 waiter polls the CI lease" >"$EXEC/logs/g1-20260908.status"
setsid nohup bash -c ': g1-20260908 waiter; source ~/workspace/intel-AMX/exec/lib-guard.sh; while ci_lease_busy; do sleep 60; done; exec bash ~/workspace/intel-AMX/exec/g1-20260908/g1-campaign.sh' >/dev/null 2>&1 &
sleep 2
echo "queued: $(pgrep -af 'g1-20260908' | grep -v pgrep | cut -c1-100 | tr '\n' ';')"; cat "$EXEC/logs/g1-20260908.status" 2>/dev/null
