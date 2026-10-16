#!/usr/bin/env bash
# Launch identity-fix.sh detached on delphi-3bda from claude-box. Whole-machine step (Bill's marker, serving down): only on
# jhan's order. It refuses while the first driver (probe-fix.sh) still runs, so the two never contend for the machine.
# Usage: END_BY=<ISO UTC> [START_NOT_BEFORE=<ISO UTC>] bash launch-identity.sh
set -u
START_NOT_BEFORE=${START_NOT_BEFORE:-}
END_BY=${END_BY:?END_BY is required (ISO UTC)}
date -u -d "$END_BY" +%s >/dev/null 2>&1 || { echo "END_BY '$END_BY' is not a date"; exit 64; }
[ -z "$START_NOT_BEFORE" ] || date -u -d "$START_NOT_BEFORE" +%s >/dev/null 2>&1 || { echo "START_NOT_BEFORE '$START_NOT_BEFORE' is not a date"; exit 64; }
if ssh -n delphi-3bda "pgrep -f probe-fix.sh >/dev/null"; then echo "probe-fix.sh still runs on delphi-3bda: wait for exec/results/i4934-20261015/probe.done"; exit 1; fi
ssh -n delphi-3bda "START_NOT_BEFORE=$START_NOT_BEFORE END_BY=$END_BY setsid nohup bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/identity-fix.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
