#!/usr/bin/env bash
# Detached launcher for the q4b-swattn campaign on the client host (copied 2026-09-19 from exec/l8b-levers-20260919/launch.sh).
# Operator steps first:
#   1. the DUT must see the same dut.sh / st_ci_perf.py / talos.py / config files as this host (NFS attribute cache);
#   2. the canon deb build must be ok on the DUT and the saved nightly deb (the base arm) must exist;
#   3. the prompt-source change must be in the systems_test checkout the driver runs (prompt.py.after == testlib/prompt.py)
#      and its offline check must have passed for the qwen tokenizer (results/prompt-check/run1.json total_exceptions 0);
#   4. no peer campaign on the DUT (plan section 2: issue4500-m6 .done marker present, no runtron/rinzler of ours running);
#   5. Bill's marker: TAKE_MARKER=1 (default) takes it HERE on jhan's order of 2026-09-19 ("we can use whole 3bda"); take
#      refuses while Bill is active (rc 2) and campaign.sh then retries every 30 min (plan 2a). TAKE_MARKER=0 (the Sunday
#      launch that sleeps through the nightly) leaves it to campaign.sh right before its preflight.
# usage: [NOT_BEFORE=...] [DEADLINE_START=...] [PASS_DEADLINE=...] [DRIVER_END_BY=...] [CHECK=1|0] [CHECK_ONLY=0|1]
#        [DRIVER_TIMEOUT=s] [TAKE_MARKER=1|0] launch.sh
# Every knob is inherited by campaign.sh through the environment (see its header).
set -u
H=/home/jhan/workspace/intel-AMX/exec/q4b-swattn-20260919
RESD=/home/jhan/workspace/intel-AMX/exec/results/q4b-swattn-20260919
LOG=/home/jhan/workspace/intel-AMX/exec/logs/q4b-swattn-20260919.log
ST=/home/jhan/workspace/ai-runs/systems_test
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
mkdir -p "$(dirname "$LOG")"
if pgrep -f "^bash $H/campaign[.]sh" >/dev/null; then echo "campaign.sh already running: $(pgrep -af "^bash $H/campaign[.]sh")"; exit 1; fi
for f in dut.sh st_ci_perf.py talos_stub/talos.py configs-full.json configs-no8192.json configs-no7168.json check-8u-p8192.json check-8u-p7168.json campaign.sh ../lib-guard.sh ../bill-share.sh; do
  want=$(md5sum "$H/$f" | cut -c1-32); have=$($SSH "md5sum $H/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
"$ST/.venv/bin/python" -m py_compile "$H/st_ci_perf.py" || { echo "st_ci_perf.py does not compile"; exit 1; }
python3 -m py_compile "$H/analyze.py" "$H/gen_report.py" || { echo "analyze.py or gen_report.py does not compile"; exit 1; }
CHK=$RESD/check-mode/perf.json
[ -f "$CHK" ] && [ ! "$H/st_ci_perf.py" -nt "$CHK" ] || { echo "st_ci_perf.py is newer than the last CI_MIMIC_CHECK=1 run ($CHK); re-run the check mode first (review C25)"; exit 1; }
bash -n "$H/campaign.sh" && bash -n "$H/dut.sh" || { echo "campaign.sh or dut.sh has a syntax error"; exit 1; }
cmp -s "$H/prompt.py.after" "$ST/testlib/prompt.py" || { echo "testlib/prompt.py in $ST differs from prompt.py.after: the prompt-source change is not in place"; exit 1; }
python3 -c "import json,sys; r=json.load(open('$RESD/prompt-check/run1.json')); sys.exit(0 if r['tokenizer']=='Qwen/Qwen3-4B-Instruct-2507' and r['total_exceptions']==0 and r['stored_lists_unchanged'] and r['identity_1024_ok'] and len(r['lengths'])==9 else 1)" || { echo "the offline prompt check did not pass for the qwen tokenizer (run1.json)"; exit 1; }
[ -f "$RESD/prompt-check/compare.txt" ] && grep -q '^DETERMINISTIC' "$RESD/prompt-check/compare.txt" || { echo "the two offline prompt-check runs were not compared as DETERMINISTIC (prompt-check/compare.txt)"; exit 1; }
st=$($SSH "cat /var/tmp/jhan/canon-ci-20260918/build.status 2>/dev/null"); [ "$st" = ok ] || { echo "canon build status on 3bda is '$st', not ok"; exit 1; }
$SSH "test -s /var/tmp/jhan/canon-ci-20260918/nightly.deb" || { echo "saved nightly deb (base arm) missing on 3bda"; exit 1; }
# peer gate (plan section 2): the issue4500 block m6 must be finished and no runtron/rinzler/issue4500 process of ours may run on the DUT
[ -f /home/jhan/workspace/intel-AMX/exec/logs/issue4500-m6.done ] || { echo "peer campaign issue4500-m6 has no .done marker"; exit 1; }
if $SSH "pgrep -u jhan -f '[r]inzler --model|[r]untron[. ]|[i]ssue4500' >/dev/null"; then echo "peer processes (runtron/rinzler/issue4500) run on the DUT as jhan; not launching"; $SSH "pgrep -u jhan -af '[r]inzler --model|[r]untron[. ]|[i]ssue4500'"; exit 1; fi
# knob sanity (review 2026-09-19): every date knob must parse, the deadlines must be ordered, the check-only run needs TONIGHT's window
# explicitly, and a six-pass launch far ahead of its window needs NOT_BEFORE (no lease file exists before the nightly takes it)
for v in NOT_BEFORE DEADLINE_START PASS_DEADLINE DRIVER_END_BY; do
  [ -z "${!v:-}" ] && continue
  date -u -d "${!v}" +%s >/dev/null 2>&1 || { echo "knob $v='${!v}' is not a date that 'date -u -d' accepts (use 2026-09-20T13:00:00Z)"; exit 1; }
done
DS=${DEADLINE_START:-2026-09-20T19:30:00Z}; PD=${PASS_DEADLINE:-2026-09-20T23:45:00Z}; DE=${DRIVER_END_BY:-2026-09-21T01:00:00Z}
[ "$(date -u -d "$DS" +%s)" -lt "$(date -u -d "$PD" +%s)" ] && [ "$(date -u -d "$PD" +%s)" -lt "$(date -u -d "$DE" +%s)" ] || { echo "deadline order wrong: need DEADLINE_START ($DS) < PASS_DEADLINE ($PD) < DRIVER_END_BY ($DE)"; exit 1; }
if [ "${CHECK_ONLY:-0}" = 1 ] && { [ -z "${DEADLINE_START:-}" ] || [ -z "${DRIVER_END_BY:-}" ] || [ -z "${PASS_DEADLINE:-}" ]; }; then
  echo "CHECK_ONLY=1 needs DEADLINE_START, PASS_DEADLINE and DRIVER_END_BY for TONIGHT's window (plan section 2), e.g. DEADLINE_START=2026-09-20T00:15:00Z PASS_DEADLINE=2026-09-20T00:30:00Z DRIVER_END_BY=2026-09-20T01:00:00Z"; exit 1
fi
if [ -z "${NOT_BEFORE:-}" ] && [ $(( $(date -u -d "$DS" +%s) - $(date -u +%s) )) -gt 28800 ]; then
  echo "DEADLINE_START $DS is more than 8 h away and NOT_BEFORE is empty: the campaign would start at once (no lease file before the nightly) and could run into the nightly; set NOT_BEFORE (plan section 2, e.g. 2026-09-20T13:00:00Z)"; exit 1
fi
if [ "${CHECK:-1}" != 1 ] && [ "${CHECK_ONLY:-0}" != 1 ] && [ ! -s "$RESD/configs-used.txt" ]; then
  echo "NOTE: CHECK=${CHECK} but no configs-used.txt from an earlier check cell: campaign.sh will run the section-6 check cell itself before the passes (about 15 min more)"
fi
if [ "${TAKE_MARKER:-1}" = 1 ]; then
  $SSH bash ~/workspace/intel-AMX/exec/bill-share.sh take 2>&1 | tail -2
  rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || echo "bill-share take rc=$rc (2 = Bill active): campaign.sh will retry every 30 min (plan 2a)"
else
  echo "TAKE_MARKER=0: campaign.sh takes Bill's marker itself right before its preflight (after the NOT_BEFORE, lease, runtron and flock waits)"
fi
setsid nohup bash "$H/campaign.sh" >>"$LOG" 2>&1 </dev/null &
echo "launched pid $! log $LOG (knobs: NOT_BEFORE=${NOT_BEFORE:-} DEADLINE_START=${DEADLINE_START:-default} PASS_DEADLINE=${PASS_DEADLINE:-default} DRIVER_END_BY=${DRIVER_END_BY:-default} CHECK=${CHECK:-1} CHECK_ONLY=${CHECK_ONLY:-0} DRIVER_TIMEOUT=${DRIVER_TIMEOUT:-default})"
