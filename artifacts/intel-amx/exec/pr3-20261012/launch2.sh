#!/usr/bin/env bash
# Launch chain.sh detached on delphi-3bda from claude-box (PR3-handoff.md step 6).
# Usage: COMMIT=<full sha> PR2_COMMIT=<full sha> [STOP_AFTER_OUR_HALF=1 | WHOLE_MACHINE_ONLY=1] [START_NOT_BEFORE=...] [END_BY=2026-10-13T01:30:00Z] bash launch2.sh
set -u
COMMIT=${COMMIT:?}; PR2_COMMIT=${PR2_COMMIT:?}; START_NOT_BEFORE=${START_NOT_BEFORE:-}; END_BY=${END_BY:-2026-10-13T01:30:00Z}
ssh -n delphi-3bda "COMMIT=$COMMIT PR2_COMMIT=$PR2_COMMIT START_NOT_BEFORE=$START_NOT_BEFORE END_BY=$END_BY STOP_AFTER_OUR_HALF=${STOP_AFTER_OUR_HALF:-0} WHOLE_MACHINE_ONLY=${WHOLE_MACHINE_ONLY:-0} setsid nohup bash /home/jhan/workspace/intel-AMX/exec/pr3-20261012/chain2.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
