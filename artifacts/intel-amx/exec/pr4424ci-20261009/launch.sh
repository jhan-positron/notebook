#!/usr/bin/env bash
# Detached launcher for the pr4424ci campaign on the client host (forked 2026-10-08 from exec/q4b-fpga-20260921/launch.sh).
# It syncs nothing: it VALIDATES (syntax, compile, the DUT sees the same files over NFS, the target build and the saved
# base deb exist on the DUT, platformd 0.11, the check mode ran after the last driver edit, no peer campaign, knob
# sanity) and then starts campaign.sh detached with setsid + nohup. Bill's marker is taken by campaign.sh itself right
# before its preflight (after the NOT_BEFORE, lease, runtron and flock waits).
# usage: [NOT_BEFORE=...] [DEADLINE_START=...] [PASS_DEADLINE=...] [DRIVER_END_BY=...] [PASSES="base target target base"]
#        [PASS_TAGS="..."] [DRIVER_TIMEOUT=s] [SW8K_TIMEOUT=s] [AMX_PROBE=1|0] bash launch.sh
# Every knob is inherited by campaign.sh through the environment (see its header). Prints the pid and the log path.
set -u
H=/home/jhan/workspace/intel-AMX/exec/pr4424ci-20261009
RESD=/home/jhan/workspace/intel-AMX/exec/results/pr4424ci-20261009
LOG=/home/jhan/workspace/intel-AMX/exec/logs/pr4424ci-20261009.log
ST=/home/jhan/workspace/ai-runs/systems_test
OUT=/var/tmp/jhan/pr4424ci-20261009
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
mkdir -p "$(dirname "$LOG")"
if pgrep -f "^bash $H/campaign[.]sh" >/dev/null; then echo "campaign.sh already running: $(pgrep -af "^bash $H/campaign[.]sh")"; exit 1; fi
for f in dut.sh st_ci_perf.py talos_stub/talos.py sw8k.json campaign.sh summarize.py ../lib-guard.sh ../bill-share.sh; do
  want=$(md5sum "$H/$f" | cut -c1-32); have=$($SSH "md5sum $H/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
"$ST/.venv/bin/python" -m py_compile "$H/st_ci_perf.py" "$H/summarize.py" "$H/configs.py" || { echo "a python file does not compile"; exit 1; }
bash -n "$H/campaign.sh" && bash -n "$H/dut.sh" && bash -n "$H/build-target.sh" || { echo "a bash file has a syntax error"; exit 1; }
CHK=$RESD/check-mode/perf.json
[ -f "$CHK" ] && [ ! "$H/st_ci_perf.py" -nt "$CHK" ] || { echo "st_ci_perf.py is newer than the last CI_MIMIC_CHECK=1 run ($CHK); re-run the check mode first (see README)"; exit 1; }
[ "$(git -C "$ST" rev-parse --short HEAD 2>/dev/null)" = "$(git -C "$ST" rev-parse --short origin/main 2>/dev/null)" ] || echo "NOTE: the harness checkout $ST is not at origin/main (HEAD $(git -C "$ST" rev-parse --short HEAD), origin/main $(git -C "$ST" rev-parse --short origin/main)); the driver follows the checkout"
[ -z "$(git -C "$ST" status --short -- scripts testlib 2>/dev/null)" ] || { echo "the harness checkout has local changes under scripts/ or testlib/ (fidelity with the nightly needs a clean checkout):"; git -C "$ST" status --short -- scripts testlib; exit 1; }
$SSH "dpkg-query -W -f='\${Version}' platformd" | grep -q '^0\.11' || { echo "platformd on 3bda is not 0.11.x (the harness's explicit provisioning path is what this campaign was checked against)"; exit 1; }
st=$($SSH "cat $OUT/build.status 2>/dev/null"); [ "$st" = ok ] || { echo "target build status on 3bda is '$st', not ok (run build-target.sh COMMIT on delphi-3bda first)"; exit 1; }
$SSH "test -s $OUT/target.deb && test -s $OUT/rinzler.target && test -s $OUT/manifest.json" || { echo "target.deb, rinzler.target or manifest.json missing in $OUT on 3bda"; exit 1; }
nv=$($SSH "dpkg-deb -f $OUT/nightly.deb Version 2>/dev/null"); [ "$nv" = "${EXPECTED_BASE:-2026.10.08-be0d5565}" ] || { echo "saved nightly deb (base arm) on 3bda has version '$nv', expected ${EXPECTED_BASE:-2026.10.08-be0d5565}"; exit 1; }
# peer gate: no runtron/rinzler process of ours may run on the DUT
if $SSH "pgrep -u jhan -f '[r]inzler --model|[r]untron[. ]' >/dev/null"; then echo "peer processes (runtron/rinzler) run on the DUT as jhan; not launching"; $SSH "pgrep -u jhan -af '[r]inzler --model|[r]untron[. ]'"; exit 1; fi
# knob sanity: every date knob must parse, the deadlines must be ordered, a launch far ahead of its window needs NOT_BEFORE
for v in NOT_BEFORE DEADLINE_START PASS_DEADLINE DRIVER_END_BY; do
  [ -z "${!v:-}" ] && continue
  date -u -d "${!v}" +%s >/dev/null 2>&1 || { echo "knob $v='${!v}' is not a date that 'date -u -d' accepts (use 2026-10-09T13:00:00Z)"; exit 1; }
done
NB=${NOT_BEFORE:-2026-10-09T13:00:00Z}; DS=${DEADLINE_START:-2026-10-09T19:00:00Z}; PD=${PASS_DEADLINE:-2026-10-09T23:30:00Z}; DE=${DRIVER_END_BY:-2026-10-10T02:05:00Z}
[ "$(date -u -d "$DS" +%s)" -lt "$(date -u -d "$PD" +%s)" ] && [ "$(date -u -d "$PD" +%s)" -lt "$(date -u -d "$DE" +%s)" ] || { echo "deadline order wrong: need DEADLINE_START ($DS) < PASS_DEADLINE ($PD) < DRIVER_END_BY ($DE)"; exit 1; }
[ "$(date -u -d "$NB" +%s)" -lt "$(date -u -d "$DS" +%s)" ] || { echo "NOT_BEFORE ($NB) must be before DEADLINE_START ($DS)"; exit 1; }
[ "$(date -u +%s)" -lt "$(date -u -d "$DE" +%s)" ] || { echo "DRIVER_END_BY ($DE) is already past"; exit 1; }
setsid nohup bash "$H/campaign.sh" >>"$LOG" 2>&1 </dev/null &
echo "launched pid $! log $LOG (knobs: NOT_BEFORE=$NB DEADLINE_START=$DS PASS_DEADLINE=$PD DRIVER_END_BY=$DE PASSES=${PASSES:-default} PASS_TAGS=${PASS_TAGS:-none} DRIVER_TIMEOUT=${DRIVER_TIMEOUT:-default} SW8K_TIMEOUT=${SW8K_TIMEOUT:-default})"
