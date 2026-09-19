#!/usr/bin/env bash
# Detached launcher for campaign.sh on the client host. Passes env knobs through.
# usage: [PASSES=1] [SMOKE=1] launch.sh
set -u
H=/home/jhan/workspace/intel-AMX/exec/ci-mimic-20260918
LOG=/home/jhan/workspace/intel-AMX/exec/logs/ci-mimic-20260918${SMOKE:+-smoke}.log
mkdir -p "$(dirname "$LOG")"
# anchored pattern with [.] so this launcher's own command line (which names the file) cannot match itself
if pgrep -f "^bash $H/campaign[.]sh" >/dev/null; then echo "campaign.sh already running: $(pgrep -af "^bash $H/campaign[.]sh")"; exit 1; fi
setsid nohup bash "$H/campaign.sh" >>"$LOG" 2>&1 </dev/null &
echo "launched pid $! log $LOG"
