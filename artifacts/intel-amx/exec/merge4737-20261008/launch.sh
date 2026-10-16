#!/usr/bin/env bash
# Launch build-test.sh detached on delphi-3bda from claude-box. Usage: COMMIT=<full sha> bash launch.sh
set -u
COMMIT=${COMMIT:?}
ssh -n delphi-3bda "COMMIT=$COMMIT setsid nohup bash /home/jhan/workspace/intel-AMX/exec/merge4737-20261008/build-test.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
