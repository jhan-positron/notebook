#!/usr/bin/env bash
# Launch chain.sh detached on delphi-3bda from claude-box. Usage: COMMIT=<full sha> bash launch.sh
# ssh -n + setsid nohup + redirects, so the ssh session returns at once (trap: a detached child keeps the channel open otherwise).
set -u
COMMIT=${COMMIT:?}
ssh -n delphi-3bda "COMMIT=$COMMIT setsid nohup bash /home/jhan/workspace/intel-AMX/exec/sync4424-20261002/chain.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
