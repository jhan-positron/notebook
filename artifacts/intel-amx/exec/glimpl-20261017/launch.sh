#!/usr/bin/env bash
# Launch the glimpl-20261017 build or chain on delphi-3bda from claude-box (detached there with setsid nohup), after
# checking that 3bda sees the same script files (NFS attribute cache trap), that the scripts parse, and that no copy runs yet.
# Fork of exec/attnstats-20261002/launch.sh. jhan may instead run the one-line commands of README.md by hand on 3bda.
# usage: SHA=<full sha> bash launch.sh build            # build.sh, detached on 3bda
#        SHA=<full sha> [NOT_BEFORE=2026-10-17T13:00:00Z] [STEPS="B T G D R"] [REPS=2] bash launch.sh chain
set -u
WHAT=${1:?usage: SHA=<sha> bash launch.sh build|chain}
SHA=${SHA:?SHA=<full 40-hex commit sha> is required}
C=/home/jhan/workspace/intel-AMX/exec/glimpl-20261017
LOGS=/home/jhan/workspace/intel-AMX/exec/logs
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
for f in build.sh tests.sh chain.sh campaign.sh gen_compare.py ../lib-guard.sh ../q4b-fpga-20260921/dut.sh; do
  case $f in *.py) python3 -m py_compile "$C/$f" || { echo "$f does not parse"; exit 1; } ;; *) bash -n "$C/$f" || { echo "$f does not parse"; exit 1; } ;; esac
  want=$(md5sum "$C/$f" | cut -c1-32); have=$($SSH "md5sum $C/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
$SSH "git -C /home/jhan/workspace/tron cat-file -e '$SHA^{commit}' 2>/dev/null" || echo "warning: 3bda does not see commit $SHA yet (build.sh retries for 5 min)"
case $WHAT in
  build)
    $SSH "pgrep -f 'glimpl-20261017/build[.]sh' >/dev/null" && { echo "build.sh already runs on 3bda"; exit 1; }
    timeout 90 $SSH -n "cd /home/jhan && setsid nohup env SHA=$SHA KSYM_N=${KSYM_N:-6} KSYM_RE='${KSYM_RE:-}' bash $C/build.sh >>$LOGS/glimpl-20261017-build.log 2>&1 </dev/null & echo launched build pid \$!"
    echo "log: $LOGS/glimpl-20261017-build.log ; marker: /home/jhan/workspace/intel-AMX/exec/results/glimpl-20261017/build.done" ;;
  chain)
    $SSH "pgrep -f 'glimpl-20261017/(chain|campaign|tests)[.]sh' >/dev/null" && { echo "chain.sh, campaign.sh or tests.sh already runs on 3bda"; exit 1; }
    $SSH "python3 -c 'import json,re,statistics'" || { echo "3bda: python3 lacks a module"; exit 1; }
    timeout 90 $SSH -n "cd /home/jhan && setsid nohup env SHA=$SHA NOT_BEFORE=${NOT_BEFORE:-2026-10-17T13:00:00Z} STEPS='${STEPS:-B T G D R}' REPS=${REPS:-2} WAIT_MARKERS='${WAIT_MARKERS:-}' CELLS='${CELLS:-}' ARM_ENV_amxon='${ARM_ENV_amxon:-}' ARM_ENV_amxoff='${ARM_ENV_amxoff:-}' bash $C/chain.sh >>$LOGS/glimpl-20261017-chain.log 2>&1 </dev/null & echo launched chain pid \$!"
    echo "log: $LOGS/glimpl-20261017-chain.log ; status: $LOGS/glimpl-20261017-chain.status" ;;
  *) echo "usage: SHA=<sha> bash launch.sh build|chain"; exit 2 ;;
esac
