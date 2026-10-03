#!/usr/bin/env bash
# Launch the attnstats-20261002 chain on delphi-3bda from claude-box (detached there with setsid nohup), after checking
# that 3bda sees the same script files (NFS attribute cache trap), that the scripts parse, and that no chain runs yet.
# Copy of the exec/i4500fix-20260928/launch.sh recipe.
# usage: [NOT_BEFORE=2026-10-02T13:00:00Z] [COMMIT=<sha>] [STEPS="F A D R"] [REPS=1] bash launch.sh
set -u
C=/home/jhan/workspace/intel-AMX/exec/attnstats-20261002
LOG=/home/jhan/workspace/intel-AMX/exec/logs/attnstats-20261002-chain.log
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
for f in chain.sh campaign.sh gen_compare.py ../i4525-20260922/build2.sh ../lib-guard.sh ../q4b-fpga-20260921/dut.sh; do
  case $f in *.py) python3 -m py_compile "$C/$f" || { echo "$f does not parse"; exit 1; } ;; *) bash -n "$C/$f" || { echo "$f does not parse"; exit 1; } ;; esac
  want=$(md5sum "$C/$f" | cut -c1-32); have=$($SSH "md5sum $C/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
$SSH "pgrep -f 'attnstats-20261002/(chain|campaign)[.]sh' >/dev/null" && { echo "chain.sh or campaign.sh already runs on 3bda"; exit 1; }
$SSH "python3 -c 'import json,re,statistics'" || { echo "3bda: python3 lacks a module"; exit 1; }
sha=$($SSH "git -C /home/jhan/workspace/tron ls-remote origin refs/heads/main 2>/dev/null" | cut -c1-10)
[ -n "$sha" ] && echo "3bda sees origin/main at $sha" || echo "warning: 3bda cannot reach origin; step F will use COMMIT_FALLBACK"
timeout 90 $SSH -n "cd /home/jhan && setsid nohup env NOT_BEFORE=${NOT_BEFORE:-2026-10-02T13:00:00Z} COMMIT=${COMMIT:-} STEPS='${STEPS:-F A D R}' REPS=${REPS:-1} bash $C/chain.sh >>$LOG 2>&1 </dev/null & echo launched pid \$!"
echo "log: $LOG ; status: ${LOG%.log}.status"
