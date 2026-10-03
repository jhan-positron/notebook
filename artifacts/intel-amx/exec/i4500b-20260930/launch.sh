#!/usr/bin/env bash
# Launch the i4500b chain on delphi-3bda from claude-box (detached there with setsid nohup), after checking that
# 3bda sees the same script files (NFS attribute cache trap) and that the scripts parse.
# usage: [NOT_BEFORE=2026-09-30T13:00:00Z] [REPS=3] [STEPS="A0 A B C T D E"] bash launch.sh
set -u
C=/home/jhan/workspace/intel-AMX/exec/i4500b-20260930
LOG=/home/jhan/workspace/intel-AMX/exec/logs/i4500b-20260930-chain.log
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
for f in chain.sh lib.sh build-deb.sh smoke.sh traces.sh campaign.sh st_perf2.py summarize.py ../i4525-20260922/build2.sh ../lib-guard.sh; do
  bash -n "$C/$f" 2>/dev/null || python3 -m py_compile "$C/$f" || { echo "$f does not parse"; exit 1; }
  want=$(md5sum "$C/$f" | cut -c1-32); have=$($SSH "md5sum $C/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
$SSH "pgrep -f 'i4500b-20260930/chain[.]sh' >/dev/null" && { echo "chain.sh already runs on 3bda"; exit 1; }
$SSH "git -C /home/jhan/workspace/tron cat-file -e ${COMMIT_FIX:-452b2052c9}^{commit} && git -C /home/jhan/workspace/tron cat-file -e ${COMMIT_DEB:-2fd11e32ca}^{commit}" || { echo "3bda does not see the commits in ~/workspace/tron yet"; exit 1; }
timeout 90 $SSH -n "cd /home/jhan && setsid nohup env NOT_BEFORE=${NOT_BEFORE:-2026-09-30T13:00:00Z} REPS=${REPS:-3} STEPS='${STEPS:-A0 A B C T D E}' bash $C/chain.sh >>$LOG 2>&1 </dev/null & echo launched pid \$!"
echo "log: $LOG ; status: ${LOG%.log}.status"
