#!/usr/bin/env bash
# Launch chain2.sh detached on delphi-3bda from claude-box (PR4-handoff.md step 6, edit 17; fork of exec/pr3-20261012/launch2.sh).
# A mode flag and END_BY are required (a run without a mode flag would enter the whole-machine part at its verdict whatever the clock).
# Usage: COMMIT=<full sha> PR3_COMMIT=<full sha> {STOP_AFTER_OUR_HALF=1 | WHOLE_MACHINE_ONLY=1} [START_NOT_BEFORE=<ISO UTC>] END_BY=<ISO UTC> bash launch2.sh
#   run 1 (our half + the two deb builds): STOP_AFTER_OUR_HALF=1 END_BY=<D+1>T01:30:00Z
#   run 2 (whole machine), option (a):     WHOLE_MACHINE_ONLY=1 START_NOT_BEFORE=<D+1>T13:00:00Z END_BY=<D+2>T01:30:00Z
#   run 2 (whole machine), option (b):     WHOLE_MACHINE_ONLY=1 END_BY=<D+1>T01:30:00Z
set -u
COMMIT=${COMMIT:?}; PR3_COMMIT=${PR3_COMMIT:?}; START_NOT_BEFORE=${START_NOT_BEFORE:-}
END_BY=${END_BY:?END_BY is required (ISO UTC, for example 2026-10-13T01:30:00Z)}
[ "${STOP_AFTER_OUR_HALF:-0}" = 1 ] || [ "${WHOLE_MACHINE_ONLY:-0}" = 1 ] || { echo "a mode flag is required: STOP_AFTER_OUR_HALF=1 or WHOLE_MACHINE_ONLY=1"; exit 64; }
[ "${STOP_AFTER_OUR_HALF:-0}" = 1 ] && [ "${WHOLE_MACHINE_ONLY:-0}" = 1 ] && { echo "only one mode flag"; exit 64; }
date -u -d "$END_BY" +%s >/dev/null 2>&1 || { echo "END_BY '$END_BY' is not a date that 'date -u -d' accepts"; exit 64; }
[ -z "$START_NOT_BEFORE" ] || date -u -d "$START_NOT_BEFORE" +%s >/dev/null 2>&1 || { echo "START_NOT_BEFORE '$START_NOT_BEFORE' is not a date"; exit 64; }
ssh -n delphi-3bda "COMMIT=$COMMIT PR3_COMMIT=$PR3_COMMIT START_NOT_BEFORE=$START_NOT_BEFORE END_BY=$END_BY STOP_AFTER_OUR_HALF=${STOP_AFTER_OUR_HALF:-0} WHOLE_MACHINE_ONLY=${WHOLE_MACHINE_ONLY:-0} setsid nohup bash /home/jhan/workspace/intel-AMX/exec/pr4-20261012/chain2.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
