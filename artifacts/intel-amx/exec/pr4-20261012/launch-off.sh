#!/usr/bin/env bash
# Launch probe-off.sh detached on delphi-3bda from claude-box (fork of launch-probe.sh). Only on jhan's order (2026-10-14:
# "please do the testing now"): the campaign takes Bill's marker (bill-share.sh take) for its whole-machine part.
# Usage: END_BY=<ISO UTC> [START_NOT_BEFORE=<ISO UTC>] bash launch-off.sh
set -u
START_NOT_BEFORE=${START_NOT_BEFORE:-}
END_BY=${END_BY:?END_BY is required (ISO UTC, for example 2026-10-13T12:30:00Z)}
date -u -d "$END_BY" +%s >/dev/null 2>&1 || { echo "END_BY '$END_BY' is not a date that 'date -u -d' accepts"; exit 64; }
[ -z "$START_NOT_BEFORE" ] || date -u -d "$START_NOT_BEFORE" +%s >/dev/null 2>&1 || { echo "START_NOT_BEFORE '$START_NOT_BEFORE' is not a date"; exit 64; }
ssh -n delphi-3bda "START_NOT_BEFORE=$START_NOT_BEFORE END_BY=$END_BY setsid nohup bash /home/jhan/workspace/intel-AMX/exec/pr4-20261012/probe-off.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
