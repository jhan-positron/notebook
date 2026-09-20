#!/usr/bin/env bash
# Detached launcher for the l8b-levers campaign on the client host. Operator steps first:
#   1. the DUT must see the same dut.sh / st_ci_perf.py / talos.py / config files as this host (NFS attribute cache);
#   2. the canon deb build must be ok on the DUT and the saved nightly deb must exist;
#   3. the prompt-source change must be in the systems_test checkout the driver runs (prompt.py.after == testlib/prompt.py)
#      and its offline check must have passed (results/prompt-check/run1.json total_exceptions 0);
#   4. Bill's marker is taken HERE on jhan's order of 2026-09-19 ("we can use whole 3bda"); take refuses while Bill
#      is active (rc 2). campaign.sh retries every 30 min in that case (plan 2a) and releases the marker at its end.
# usage: [DEADLINE_START=...] [CHECK=1] launch.sh
set -u
H=/home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919
LOG=/home/jhan/workspace/intel-AMX/exec/logs/l8b-levers-20260919.log
ST=/home/jhan/workspace/ai-runs/systems_test
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
mkdir -p "$(dirname "$LOG")"
if pgrep -f "^bash $H/campaign[.]sh" >/dev/null; then echo "campaign.sh already running: $(pgrep -af "^bash $H/campaign[.]sh")"; exit 1; fi
for f in dut.sh st_ci_perf.py talos_stub/talos.py configs-full.json configs-no8192.json configs-no7168.json check-32u-p8192.json check-32u-p7168.json campaign.sh ../lib-guard.sh ../bill-share.sh; do
  want=$(md5sum "$H/$f" | cut -c1-32); have=$($SSH "md5sum $H/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
"$ST/.venv/bin/python" -m py_compile "$H/st_ci_perf.py" || { echo "st_ci_perf.py does not compile"; exit 1; }
CHK=/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/check-mode/perf.json
[ -f "$CHK" ] && [ ! "$H/st_ci_perf.py" -nt "$CHK" ] || { echo "st_ci_perf.py is newer than the last CI_MIMIC_CHECK=1 run ($CHK); re-run the check mode first (review C25)"; exit 1; }
bash -n "$H/campaign.sh" && bash -n "$H/dut.sh" || { echo "campaign.sh or dut.sh has a syntax error"; exit 1; }
cmp -s "$H/prompt.py.after" "$ST/testlib/prompt.py" || { echo "testlib/prompt.py in $ST differs from prompt.py.after: the prompt-source change is not in place"; exit 1; }
python3 -c "import json,sys; r=json.load(open('/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/prompt-check/run1.json')); sys.exit(0 if r['total_exceptions']==0 and r['stored_lists_unchanged'] and r['identity_1024_ok'] else 1)" || { echo "the offline prompt check did not pass (run1.json)"; exit 1; }
st=$($SSH "cat /var/tmp/jhan/canon-ci-20260918/build.status 2>/dev/null"); [ "$st" = ok ] || { echo "canon build status on 3bda is '$st', not ok"; exit 1; }
$SSH "test -s /var/tmp/jhan/canon-ci-20260918/nightly.deb" || { echo "saved nightly deb missing on 3bda (campaign.sh save-base-deb would fall back to the apt repository)"; }
if [ "${TAKE_MARKER:-1}" = 1 ]; then
  $SSH bash ~/workspace/intel-AMX/exec/bill-share.sh take 2>&1 | tail -2
  rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || echo "bill-share take rc=$rc (2 = Bill active): campaign.sh will retry every 30 min (plan 2a)"
else
  echo "TAKE_MARKER=0: campaign.sh takes Bill's marker itself right before its preflight (after the runtron and flock waits)"
fi
setsid nohup bash "$H/campaign.sh" >>"$LOG" 2>&1 </dev/null &
echo "launched pid $! log $LOG"
