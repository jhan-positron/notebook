#!/usr/bin/env bash
# pr5606-check-20261123: steps 2 and 3 in the option-OFF tree, one after the other. Runs ON delphi-3b35.
# Step 1 (state S0: build-3b35.sh, then tests-3b35.sh) must have run before.
#   step 2: state S1, build of t_amx_dispatch_dtype, its two runs, the compile-command record
#   step 3: state S2, build of the four targets, the six runs, the compile-command record, the AMX instruction
#           count, and the wall times of the kept S0 and S2 binaries (no build runs at that time)
# Usage (on 3b35): nohup bash chain-off-3b35.sh >/dev/null 2>&1 &
# Marker: exec/results/pr5606-check-20261123/chain-off.done. Log: exec/logs/pr5606-check-20261123-chain-off.log.
set -u
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
only_3b35
exec >>"$LOGDIR/$NAME-chain-off.log" 2>&1
rm -f "$RES/chain-off.done"
echo "=== chain-off started $(ts) ==="
step() { echo "$(ts) $*"; "$@" || { echo "failed at: $*" >"$RES/chain-off.done"; echo "=== chain-off FAILED $(ts) at: $* ==="; exit 1; }; }
ok() { [ "$(cat "$RES/$1.done" 2>/dev/null)" = ok ]; }
step env OPT=off STATE=S1 TARGETS=t_amx_dispatch_dtype bash "$HERE/build-3b35.sh"
step ok build-off-S1
step env OPT=off STATE=S1 TESTS=dispatch bash "$HERE/tests-3b35.sh"
step ok tests-off-S1
step env OPT=off STATE=S1 bash "$HERE/compile-commands-3b35.sh"
step env OPT=off STATE=S2 bash "$HERE/build-3b35.sh"
step ok build-off-S2
step env OPT=off STATE=S2 bash "$HERE/tests-3b35.sh"
step ok tests-off-S2
step env OPT=off STATE=S2 bash "$HERE/compile-commands-3b35.sh"
step env OPT=off STATE=S2 WALL=1 WALL_STATES="S0 S1 S2" bash "$HERE/extras-3b35.sh"
echo ok >"$RES/chain-off.done"
echo "=== chain-off finished $(ts) ==="
