#!/usr/bin/env bash
# glimci-20261017 launcher (runs on the client host claude-agentsrv): checks, then starts campaign.sh detached.
# Usage: [NOT_BEFORE=...] [DEADLINE_START=...] [PASSES="..."|PASS_TAGS="..."] [HANDOFF=up] bash launch.sh
# Forked 2026-10-17 from exec/q4b-fpga-20260921/launch.sh (qwen-specific prompt checks dropped; target build check added).
set -u
H=/home/jhan/workspace/intel-AMX/exec/glimci-20261017
RESD=/home/jhan/workspace/intel-AMX/exec/results/glimci-20261017
LOG=/home/jhan/workspace/intel-AMX/exec/logs/glimci-20261017.log
ST=/home/jhan/workspace/ai-runs/systems_test
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
mkdir -p "$(dirname "$LOG")" "$RESD"
if pgrep -f "^bash $H/campaign[.]sh" >/dev/null; then echo "campaign.sh already running: $(pgrep -af "^bash $H/campaign[.]sh")"; exit 1; fi
for f in dut.sh st_ci_perf.py talos_stub/talos.py configs-glimmer.json campaign.sh ../lib-guard.sh ../bill-share.sh; do
  want=$(md5sum "$H/$f" | cut -c1-32); have=$($SSH "md5sum $H/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
"$ST/.venv/bin/python" -m py_compile "$H/st_ci_perf.py" || { echo "st_ci_perf.py does not compile"; exit 1; }
CHK=$RESD/check-mode/perf.json
[ -f "$CHK" ] && [ ! "$H/st_ci_perf.py" -nt "$CHK" ] || { echo "st_ci_perf.py is newer than the last CI_MIMIC_CHECK=1 run ($CHK); re-run the check mode first"; exit 1; }
bash -n "$H/campaign.sh" && bash -n "$H/dut.sh" || { echo "campaign.sh or dut.sh has a syntax error"; exit 1; }
$SSH "dpkg-query -W -f='\${Version}' platformd" | grep -q '^0\.11' || { echo "platformd on 3bda is not 0.11.x"; exit 1; }
st=$($SSH "cat /var/tmp/jhan/glimci-20261017/build.status 2>/dev/null"); [ "$st" = ok ] || { echo "target build status on 3bda is '$st', not ok"; exit 1; }
$SSH "test -s /var/tmp/jhan/glimci-20261017/target.deb" || { echo "target deb missing on 3bda"; exit 1; }
if $SSH "pgrep -u jhan -f '^(/[^ ]*/)?rinzler --model|^(/[^ ]*/)?runtron[^ ]* |[m]ake deb|[b]uild-deb' >/dev/null"; then echo "peer processes (runtron/rinzler/build) run on the DUT as jhan; not launching"; $SSH "pgrep -u jhan -af '^(/[^ ]*/)?rinzler --model|^(/[^ ]*/)?runtron[^ ]* |[m]ake deb|[b]uild-deb'"; exit 1; fi
for v in NOT_BEFORE DEADLINE_START PASS_DEADLINE DRIVER_END_BY; do
  [ -z "${!v:-}" ] && continue
  date -u -d "${!v}" +%s >/dev/null 2>&1 || { echo "knob $v='${!v}' is not a date that 'date -u -d' accepts"; exit 1; }
done
DS=${DEADLINE_START:-2026-10-17T23:30:00Z}; PD=${PASS_DEADLINE:-2026-10-18T00:50:00Z}; DE=${DRIVER_END_BY:-2026-10-18T01:20:00Z}
[ "$(date -u -d "$DS" +%s)" -lt "$(date -u -d "$PD" +%s)" ] && [ "$(date -u -d "$PD" +%s)" -lt "$(date -u -d "$DE" +%s)" ] || { echo "deadline order wrong: need DEADLINE_START ($DS) < PASS_DEADLINE ($PD) < DRIVER_END_BY ($DE)"; exit 1; }
echo "TAKE_MARKER: campaign.sh takes Bill's marker itself right before its preflight (after the lease, runtron and flock waits)"
cd "$H" || exit 1
setsid nohup env NOT_BEFORE="${NOT_BEFORE:-}" DEADLINE_START="$DS" PASS_DEADLINE="$PD" DRIVER_END_BY="$DE" \
  PASSES="${PASSES:-base amxoff amxon base amxoff amxon base amxoff amxon}" PASS_TAGS="${PASS_TAGS:-}" HANDOFF="${HANDOFF:-up}" NO_WAIT="${NO_WAIT:-0}" AMX_PROBE="${AMX_PROBE:-1}" \
  bash "$H/campaign.sh" >>"$LOG" 2>&1 < /dev/null &
pid=$!
sleep 3
echo "launched campaign.sh pid $pid; log $LOG; status $RESD/.status"
tail -3 "$LOG"
