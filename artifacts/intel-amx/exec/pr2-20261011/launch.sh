#!/usr/bin/env bash
# Launch chain.sh detached on delphi-3bda from claude-box.
# Usage: COMMIT=<full sha> PR1_COMMIT=<full sha> [START_NOT_BEFORE=2026-10-11T13:00:00Z] [END_BY=2026-10-12T01:30:00Z] bash launch.sh
set -u
COMMIT=${COMMIT:?}; PR1_COMMIT=${PR1_COMMIT:?}; START_NOT_BEFORE=${START_NOT_BEFORE:-}; END_BY=${END_BY:-2026-10-12T01:30:00Z}
ssh -n delphi-3bda "COMMIT=$COMMIT PR1_COMMIT=$PR1_COMMIT START_NOT_BEFORE=$START_NOT_BEFORE END_BY=$END_BY setsid nohup bash /home/jhan/workspace/intel-AMX/exec/pr2-20261011/chain.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
