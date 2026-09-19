#!/usr/bin/env bash
# Start the wedperf-20260916 build chain on delphi-3bda (run ON delphi-3bda). Idempotent.
EXEC=/home/jhan/workspace/intel-AMX/exec
if pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/wedperf-20260916/(build-chain|build)[.]sh' >/dev/null; then
  echo "already running: $(pgrep -af 'wedperf-20260916/(build-chain|build)[.]sh' | grep -v pgrep | cut -c1-120 | tr '\n' ';')"; exit 0
fi
mkdir -p "$EXEC/logs"
setsid nohup bash "$EXEC/wedperf-20260916/build-chain.sh" >/dev/null 2>&1 &
sleep 2
echo "started: $(pgrep -af 'wedperf-20260916/build-chain[.]sh' | grep -v pgrep | cut -c1-120 | tr '\n' ';')"
