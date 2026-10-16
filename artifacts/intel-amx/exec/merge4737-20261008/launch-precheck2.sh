#!/usr/bin/env bash
# Launch precheck2.sh detached on delphi-3bda from claude-box. Usage: COMMIT=<full sha> [END_BY=ISO] bash launch-precheck2.sh
set -u
COMMIT=${COMMIT:?}
NOT_BEFORE=${NOT_BEFORE:-2026-10-10T13:00:00Z}
END_BY=${END_BY:-2026-10-11T01:40:00Z}
ssh -n delphi-3bda "COMMIT=$COMMIT NOT_BEFORE=$NOT_BEFORE END_BY=$END_BY setsid nohup bash /home/jhan/workspace/intel-AMX/exec/merge4737-20261008/precheck2.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
