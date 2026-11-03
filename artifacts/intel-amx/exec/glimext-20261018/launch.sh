#!/usr/bin/env bash
# Launch the glimext-20261018 chain on delphi-3bda from claude-box (detached there with setsid nohup), after checking that
# 3bda sees the same script files (NFS attribute cache trap), that the scripts parse, and that no copy runs yet.
# Fork of exec/glimmer-20261016/launch.sh. jhan may instead run the one-line command of README.md by hand on 3bda.
# usage: [NOT_BEFORE=2026-10-19T13:30:00Z] [STEPS="B T I D E R"] [REPS=4] [CELLS="..."] [E_NOT_AFTER=..] [E_MIN_HOURS=..] [BASE_SHA=..] [HEAD_SHA=..] [CHAIN=chain2.sh] bash launch.sh chain
#        bash launch.sh check      # the file and syntax checks only
set -u
WHAT=${1:?usage: bash launch.sh chain|check}
C=/home/jhan/workspace/intel-AMX/exec/glimext-20261018
LOGS=/home/jhan/workspace/intel-AMX/exec/logs
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
for f in build.sh tests.sh chain.sh chain2.sh campaign.sh smoke.sh smoke2.sh margin.sh gen_report.py ../lib-guard.sh ../q4b-fpga-20260921/dut.sh ../sync4424-20261002/summarize.py ../dd/dd_logits_step.py ../glimmer-20261016/gen_compare.py; do
  case $f in *.py) python3 -m py_compile "$C/$f" || { echo "$f does not parse"; exit 1; } ;; *) bash -n "$C/$f" || { echo "$f does not parse"; exit 1; } ;; esac
  want=$(md5sum "$C/$f" | cut -c1-32); have=$($SSH "md5sum $C/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
echo "files and syntax ok"
[ "$WHAT" = check ] && exit 0
case $WHAT in
  chain)
    $SSH "pgrep -f 'glimext-20261018/(chain|campaign|smoke|margin|tests|build)[.]sh' >/dev/null" && { echo "a glimext-20261018 script already runs on 3bda"; exit 1; }
    $SSH "python3 -c 'import json,re,statistics,numpy'" || { echo "3bda: python3 lacks a module (json/re/statistics/numpy)"; exit 1; }
    timeout 90 $SSH -n "cd /home/jhan && setsid nohup env NOT_BEFORE=${NOT_BEFORE:-2026-10-19T13:30:00Z} STEPS='${STEPS:-B T I D E R}' REPS=${REPS:-4} CELLS='${CELLS:-}' E_NOT_AFTER='${E_NOT_AFTER:-}' E_MIN_HOURS='${E_MIN_HOURS:-}' BASE_SHA='${BASE_SHA:-}' HEAD_SHA='${HEAD_SHA:-}' MAX_CAMPAIGN_PASSES='${MAX_CAMPAIGN_PASSES:-}' bash $C/${CHAIN:-chain.sh} >>$LOGS/glimext-20261018-chain.log 2>&1 </dev/null & echo launched chain pid \$!"
    echo "log: $LOGS/glimext-20261018-chain.log ; status: $LOGS/glimext-20261018-chain.status" ;;
  *) echo "usage: bash launch.sh chain|check"; exit 2 ;;
esac
