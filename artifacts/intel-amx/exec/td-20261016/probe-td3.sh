#!/usr/bin/env bash
# td3-20261016 (runs ON delphi-3bda, detached): third round of the issue #4444 probe: the attention path counters
# (TRON_ATTN_STATS=1, printed at exit as "[attn-stats] ... k_tokens per layer (amx/avx/fpga)") of base (main 72308ec90c)
# and new (PR #4959 probe commit) at 63 and at 64 generated tokens, prompt 1024, CPU attention, forced to the same tokens.
# Question: the record-for-record comparison base vs poc is identical up to decode step 63 and first differs at step 64
# (token 1087), the step that writes the 64th row of decode page 16. Hypothesis: main scores that page on AMX in the same
# step (no layout gate), the stack scores it in the software loop (block 3 is still row-major until the forward end).
# Measurement: the difference of the per-layer amx / avx k_tokens between the 64-step and the 63-step run of each binary.
# Fork of probe-td2.sh; waits for the second round's probe.done. Logits are not recorded (no --intermediates-file).
# Usage (on 3bda): [END_BY=<ISO UTC>] bash probe-td3.sh   Outputs: exec/results/td3-20261016/ (runs.txt, stats-<arm>.txt,
# probe.done); logs on /var/tmp/jhan/td3/; log exec/logs/td3-20261016.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
S=$EXEC/sync4424-20261002
DUT=$EXEC/q4b-fpga-20260921/dut.sh
export NAME=td3-20261016
END_BY=${END_BY:-2026-10-17T02:15:00Z}
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export RT_HEAD=/var/tmp/jhan/tron-td-poc/gen/runtron.poc
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export CELLS_ALL="smoke|ingested-qwen-3-4b-instruct-2507-tp2|2|1|1024"
export DEADLINE_HHMM=0215
SYNC_FUNCTIONS_ONLY=1; source "$S/campaign.sh"; unset SYNC_FUNCTIONS_ONLY
OUR_RT_RE='^/var/tmp/jhan/(tron-main1010|tron-pr4|tron-td-[a-z]+)/gen/runtron[.a-z0-9]* '
D=/var/tmp/jhan/td3
PREV_DONE=$EXEC/results/td2-20261016/probe.done
FORCED=$EXEC/results/pr4-20261012/smoke/cpu-p1024/new.tokens
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
mkdir -p "$RES" "$D"
exec >>"$LOG" 2>&1
rm -f "${RES:?}/probe.done"
MARKER_TAKEN=0
finish() { stop_watcher; kill_ours; remove_our_slice_files; campaign_guard_release 2>/dev/null
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"; elif rinzler_active; then echo "$(ts) serving: units active, nothing to bring up"; else timeout 900 bash "$DUT" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
  [ "$MARKER_TAKEN" = 1 ] && { bash "$EXEC/bill-share.sh" release 2>&1 | tail -1; echo "$(ts) Bill marker released"; }
  echo "$(ts) machine at exit: $(machine_line) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"; }
trap finish EXIT
echo "=== $NAME probe started $(ts) pid $$ on $(hostname) END_BY=$END_BY ==="
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
w=0; while [ ! -s "$PREV_DONE" ]; do past_end && { echo "$(ts) past END_BY while waiting for the second round: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting for the second round ($PREV_DONE)"; w=1; sleep 120; done
echo "$(ts) second round over: $(cat "$PREV_DONE")"
for b in "$RT_NEW" "$RT_BASE" "$RT_HEAD"; do [ -x "$b" ] || { echo "$b missing"; echo failed-binary >"$RES/probe.done"; exit 1; }; done
w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do past_end && { echo "$(ts) past END_BY while waiting for the lease: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting: CI lease busy or another person active"; w=1; sleep 120; done
past_end && { echo "$(ts) past END_BY: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }
tout=$(bash "$EXEC/bill-share.sh" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) echo "$(ts) marker not taken (rc $trc): stop"; echo stopped-marker >"$RES/probe.done"; exit 1;; esac
if rinzler_active; then IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); the runs retry through the guard"; fi
echo "$(ts) serving: $(machine_line) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"

run_arm() {  # run_arm <name> <binary> <"env assignments"|-> <generated tokens>
  local name=${1:?} bin=${2:?} extra=${3:?} ntok=${4:?}
  local ex=() rc t0
  if grep -q "attn-stats.*k_tokens per layer" "$D/$name.log" 2>/dev/null && [ "$(wc -w < "$D/$name.tokens" 2>/dev/null)" = "$ntok" ]; then
    echo "run $name reused: tokens=$ntok stats present" | tee -a "$RES/runs.txt"; return 0
  fi
  [ "$extra" != - ] && ex=($extra)
  past_end && { echo "$(ts) past END_BY before $name: skip"; return 2; }
  wait_clear || { echo "$(ts) deadline while waiting before $name"; return 2; }
  take_guard || { echo "$(ts) deadline while waiting for the guard before $name"; return 2; }
  status "run $name"
  rm -f "${D:?}/${name:?}.tokens"
  echo "### $name bin=$bin env=[${extra}] attn=cpu prompt=1024 tokens=$ntok forced=$FORCED $(ts) $(machine_line)" >>"$RES/runs.txt"
  rm -f "${RES:?}/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  t0=$(date +%s)
  (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_ATTN_STATS=1 "${ex[@]}" TRON_LOG_LEVEL=info \
      timeout -k 30 3600 "$bin" stream-generate-text -m "$MODEL" $(placement 2) --hugepage_file "$HPFILE" -o \
      --prompt-length 1024 -l "$ntok" -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$D/$name.tokens" \
      --force-feed-text-token-file "$FORCED") >"$D/$name.log" 2>&1
  rc=$?
  stop_watcher; campaign_guard_release; remove_our_slice_files
  grep -a "attn-stats" "$D/$name.log" > "$RES/stats-$name.txt"
  echo "run $name rc=$rc wall=$(( $(date +%s) - t0 ))s tokens=$(wc -w < "$D/$name.tokens" 2>/dev/null) stats-lines=$(wc -l < "$RES/stats-$name.txt") $(grep -E 'Version:' "$D/$name.log" | head -1 | cut -c1-120)" | tee -a "$RES/runs.txt"
  [ -e "$RES/rt.STOPPED" ] && echo "RUN-STOPPED $(cat "$RES/rt.STOPPED")" | tee -a "$RES/runs.txt"
  return $rc
}
fails=0
run_arm base63 "$RT_BASE" - 63 || fails=$((fails + 1))
run_arm base64 "$RT_BASE" - 64 || fails=$((fails + 1))
run_arm new63  "$RT_NEW"  - 63 || fails=$((fails + 1))
run_arm new64  "$RT_NEW"  - 64 || fails=$((fails + 1))
run_arm poc64  "$RT_HEAD" - 64 || fails=$((fails + 1))
echo "$(ts) runs done, failed=$fails"
python3 - "$RES" <<'PY' | tee "$RES/verdict.txt"
import re, sys, os
R = sys.argv[1]
def layers(name):
    t = open(os.path.join(R, f"stats-{name}.txt"), errors="replace").read()
    m = re.search(r"decode_like\S* k_tokens per layer \(amx/avx/fpga\): (.*)", t)
    if not m: return None
    out = {}
    for tok in m.group(1).split():
        l, v = tok.split("=", 1); a, b, c = (int(x) for x in v.split("/")); out[int(l)] = (a, b, c)
    return out
for arm in ("base", "new"):
    a63, a64 = layers(arm + "63"), layers(arm + "64")
    if not a63 or not a64: print(f"{arm}: stats missing"); continue
    d = {l: (a64[l][0] - a63[l][0], a64[l][1] - a63[l][1]) for l in a64 if l in a63}
    vals = sorted(set(d.values()))
    print(f"{arm}: step 64 added per layer (amx k_tokens, avx k_tokens): {vals} over {len(d)} layers; layer 0: {d.get(0)}")
PY
echo "$([ $fails -eq 0 ] && echo ok || echo "failed-runs-$fails")" >"$RES/probe.done"
echo "=== $NAME probe finished $(ts): $(cat "$RES/probe.done") ==="
