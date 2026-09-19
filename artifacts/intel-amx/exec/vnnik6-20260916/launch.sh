#!/usr/bin/env bash
# Queue the vnnik6-20260916 chain on delphi-3bda (run ON delphi-3bda). Idempotent: exits if a
# chain.sh or campaign.sh of this campaign is already running. chain.sh itself waits for the
# CI lease, so nothing heavy starts inside the CI window. Do not edit chain.sh, build.sh or
# campaign.sh after this launch (bash reads a running script incrementally from NFS).
EXEC=/home/jhan/workspace/intel-AMX/exec
if pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/vnnik6-20260916/(chain|campaign)[.]sh' >/dev/null; then
  echo "already running: $(pgrep -af 'vnnik6-20260916/(chain|campaign)[.]sh' | grep -v pgrep | cut -c1-100 | tr '\n' ';')"; exit 0
fi
mkdir -p "$EXEC/logs"
echo "$(date -u +%FT%TZ) queued: vnnik6 chain.sh waits for the CI lease, then builds and runs the campaign" >"$EXEC/logs/vnnik6-20260916.status"
setsid nohup bash "$EXEC/vnnik6-20260916/chain.sh" >/dev/null 2>&1 &
sleep 2
echo "queued: $(pgrep -af 'vnnik6-20260916/chain[.]sh' | grep -v pgrep | cut -c1-100 | tr '\n' ';')"; cat "$EXEC/logs/vnnik6-20260916.status" 2>/dev/null
