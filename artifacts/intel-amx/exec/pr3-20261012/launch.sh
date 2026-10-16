#!/usr/bin/env bash
# Launch chain.sh detached on delphi-3bda from claude-box (PR3-handoff.md step 6).
# Usage: COMMIT=<full sha> PR2_COMMIT=<full sha> [START_NOT_BEFORE=2026-10-12T13:00:00Z] [END_BY=2026-10-13T01:30:00Z] bash launch.sh
set -u
COMMIT=${COMMIT:?}; PR2_COMMIT=${PR2_COMMIT:?}; START_NOT_BEFORE=${START_NOT_BEFORE:-}; END_BY=${END_BY:-2026-10-13T01:30:00Z}
ssh -n delphi-3bda "COMMIT=$COMMIT PR2_COMMIT=$PR2_COMMIT START_NOT_BEFORE=$START_NOT_BEFORE END_BY=$END_BY setsid nohup bash /home/jhan/workspace/intel-AMX/exec/pr3-20261012/chain.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
