#!/usr/bin/env bash
# Start the wedperf-20260916 campaign on delphi-3bda (run ON delphi-3bda). Idempotent: exits if a
# campaign.sh of this campaign is already running. campaign.sh waits for the build markers and
# the CI lease itself. Do not edit campaign.sh after this launch (bash reads a running script
# incrementally from NFS). Environment overrides (REPS, REPS_B, CELLS_A, ...) pass through.
EXEC=/home/jhan/workspace/intel-AMX/exec
if pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/wedperf-20260916/campaign[.]sh' >/dev/null; then
  echo "already running: $(pgrep -af 'wedperf-20260916/campaign[.]sh' | grep -v pgrep | cut -c1-120 | tr '\n' ';')"; exit 0
fi
mkdir -p "$EXEC/logs"
echo "$(date -u +%FT%TZ) queued: wedperf campaign.sh waits for the build markers, then runs smokes, block A, block B" >"$EXEC/logs/wedperf-20260916.status"
setsid nohup bash "$EXEC/wedperf-20260916/campaign.sh" >/dev/null 2>&1 &
sleep 2
echo "started: $(pgrep -af 'wedperf-20260916/campaign[.]sh' | grep -v pgrep | cut -c1-120 | tr '\n' ';')"; cat "$EXEC/logs/wedperf-20260916.status" 2>/dev/null
