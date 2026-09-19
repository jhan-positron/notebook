#!/usr/bin/env bash
# Detached launcher for campaign.sh on the client host. Operator steps first (review 2026-09-18):
#   1. the DUT must see the same dut.sh as this host (NFS attribute cache trap);
#   2. the canon deb build must be ok on the DUT;
#   3. Bill's marker is taken HERE, on jhan's order (bill-share.sh: "take happens only on jhan's word, never from a
#      campaign script"); take refuses while Bill is active. The campaign releases the marker at its end.
# usage: [DEADLINE_START=...] [HANDOFF=down|up] launch.sh
set -u
H=/home/jhan/workspace/intel-AMX/exec/canon-ci-20260918
LOG=/home/jhan/workspace/intel-AMX/exec/logs/canon-ci-20260918.log
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
mkdir -p "$(dirname "$LOG")"
# anchored pattern with [.] so this launcher's own command line (which names the file) cannot match itself
if pgrep -f "^bash $H/campaign[.]sh" >/dev/null; then echo "campaign.sh already running: $(pgrep -af "^bash $H/campaign[.]sh")"; exit 1; fi
for f in dut.sh st_ci_perf.py talos_stub/talos.py; do
  want=$(md5sum "$H/$f" | cut -c1-32); have=$($SSH "md5sum $H/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
st=$($SSH "cat /var/tmp/jhan/canon-ci-20260918/build.status 2>/dev/null"); [ "$st" = ok ] || { echo "canon build status on 3bda is '$st', not ok"; exit 1; }
$SSH bash ~/workspace/intel-AMX/exec/bill-share.sh take 2>&1 | tail -2
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || { echo "bill-share take rc=$rc (2 = Bill active): not launching"; exit 1; }
setsid nohup bash "$H/campaign.sh" >>"$LOG" 2>&1 </dev/null &
echo "launched pid $! log $LOG"
