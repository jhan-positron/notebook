#!/usr/bin/env bash
# Launch precheck.sh detached on delphi-3bda from claude-box. Usage: COMMIT=<full sha> [NOT_BEFORE=ISO] bash launch-precheck.sh
set -u
COMMIT=${COMMIT:?}
NOT_BEFORE=${NOT_BEFORE:-2026-10-09T13:00:00Z}
ssh -n delphi-3bda "COMMIT=$COMMIT NOT_BEFORE=$NOT_BEFORE setsid nohup bash /home/jhan/workspace/intel-AMX/exec/merge4737-20261008/precheck.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
