#!/usr/bin/env bash
# td2-20261016 (runs ON delphi-3bda, detached): second round of the issue #4444 probe: the prompt-8192 cell, where every
# stack PR reported "identical" tokens against main (issue #4444, 2026-10-14 table). Question: are the logits identical at
# 8192 too (the paths coincide) or only the tokens (no near tie was hit in 256 steps)? Forced runs (fed the free-running
# tokens of `new` at 8192, produced by the first arm here), qwen3-4b tp2, 1 user, prompt 8192, CPU attention, logits only
# (the full intermediates file, about 165 GB per run at this prompt length, is filtered to the 'Logits of token' lines and
# deleted after each run). Arms: new (runtron.pr4, free-running then its tokens are the forced file), base (runtron.main1010),
# newoff (runtron.pr4 + TRON_AMX_DISABLE=1), poc (runtron.poc). Fork of probe-td.sh; waits for the first round's probe.done.
# Usage (on 3bda): [END_BY=<ISO UTC>] bash probe-td2.sh   Outputs: exec/results/td2-20261016/, logits on /var/tmp/jhan/td2/,
# log exec/logs/td2-20261016.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
S=$EXEC/sync4424-20261002
DUT=$EXEC/q4b-fpga-20260921/dut.sh
DD=$EXEC/dd
export NAME=td2-20261016
END_BY=${END_BY:-2026-10-17T02:15:00Z}
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export RT_HEAD=/var/tmp/jhan/tron-td-poc/gen/runtron.poc
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export CELLS_ALL="smoke|ingested-qwen-3-4b-instruct-2507-tp2|2|1|8192"
export DEADLINE_HHMM=0215
SYNC_FUNCTIONS_ONLY=1; source "$S/campaign.sh"; unset SYNC_FUNCTIONS_ONLY
OUR_RT_RE='^/var/tmp/jhan/(tron-main1010|tron-pr4|tron-td-[a-z]+)/gen/runtron[.a-z0-9]* '
D=/var/tmp/jhan/td2
FIRST_DONE=$EXEC/results/td-20261016/probe.done
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
PROMPT=8192
mkdir -p "$RES" "$D"
exec >>"$LOG" 2>&1
rm -f "${RES:?}/probe.done"
MARKER_TAKEN=0
finish() { stop_watcher; kill_ours; remove_our_slice_files; campaign_guard_release 2>/dev/null
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"; elif rinzler_active; then echo "$(ts) serving: units active, nothing to bring up"; else timeout 900 bash "$DUT" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
  [ "$MARKER_TAKEN" = 1 ] && { bash "$EXEC/bill-share.sh" release 2>&1 | tail -1; echo "$(ts) Bill marker released"; }
  echo "$(ts) machine at exit: $(machine_line) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"; }
trap finish EXIT
echo "=== $NAME probe started $(ts) pid $$ on $(hostname) prompt=$PROMPT END_BY=$END_BY ==="
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
w=0; while [ ! -s "$FIRST_DONE" ]; do past_end && { echo "$(ts) past END_BY while waiting for the first round: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting for the first round ($FIRST_DONE)"; w=1; sleep 120; done
echo "$(ts) first round over: $(cat "$FIRST_DONE")"
for b in "$RT_NEW" "$RT_BASE" "$RT_HEAD"; do [ -x "$b" ] || { echo "$b missing"; echo failed-binary >"$RES/probe.done"; exit 1; }; done
w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do past_end && { echo "$(ts) past END_BY while waiting for the lease: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting: CI lease busy or another person active"; w=1; sleep 120; done
past_end && { echo "$(ts) past END_BY: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }
tout=$(bash "$EXEC/bill-share.sh" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) echo "$(ts) marker not taken (rc $trc): stop"; echo stopped-marker >"$RES/probe.done"; exit 1;; esac
if rinzler_active; then IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); the runs retry through the guard"; fi
echo "$(ts) serving: $(machine_line) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"

run_arm() {  # run_arm <name> <binary> <"env assignments"|-> <forced file|->
  local name=${1:?} bin=${2:?} extra=${3:?} forced=${4:?}
  local ex=() ff=() rc t0
  if [ "$(wc -w < "$D/$name.tokens" 2>/dev/null)" = 256 ] && [ "$(grep -c 'Logits of token' "$D/$name.txt" 2>/dev/null)" -ge 256 ]; then
    echo "run $name reused: tokens=256 logits-lines=$(grep -c 'Logits of token' "$D/$name.txt")" | tee -a "$RES/runs.txt"; return 0
  fi
  [ "$extra" != - ] && ex=($extra)
  [ "$forced" != - ] && ff=(--force-feed-text-token-file "$forced")
  past_end && { echo "$(ts) past END_BY before $name: skip"; return 2; }
  wait_clear || { echo "$(ts) deadline while waiting before $name"; return 2; }
  take_guard || { echo "$(ts) deadline while waiting for the guard before $name"; return 2; }
  status "run $name"
  rm -f "${D:?}/${name:?}.full" "${D:?}/${name:?}.txt" "${D:?}/${name:?}.tokens"
  echo "### $name bin=$bin env=[${extra}] attn=cpu prompt=$PROMPT forced=$forced $(ts) $(machine_line)" >>"$RES/runs.txt"
  rm -f "${RES:?}/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  t0=$(date +%s)
  (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 "${ex[@]}" TRON_LOG_LEVEL=info \
      timeout -k 30 7200 "$bin" stream-generate-text -m "$MODEL" $(placement 2) --hugepage_file "$HPFILE" -o \
      --prompt-length $PROMPT -l 256 -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$D/$name.tokens" \
      --intermediates-file "$D/$name.full" "${ff[@]}") >"$D/$name.log" 2>&1
  rc=$?
  stop_watcher; campaign_guard_release; remove_our_slice_files
  grep -E 'Logits of token' "$D/$name.full" > "$D/$name.txt"; echo "$(ts) $name: full log $(stat -c %s "$D/$name.full") bytes filtered to $(stat -c %s "$D/$name.txt") bytes"; rm -f "${D:?}/${name:?}.full"
  echo "run $name rc=$rc wall=$(( $(date +%s) - t0 ))s tokens=$(wc -w < "$D/$name.tokens" 2>/dev/null) logits-lines=$(grep -c 'Logits of token' "$D/$name.txt" 2>/dev/null) $(grep -E 'Version:|average tok/s|orced' "$D/$name.log" | tr '\n' ' ' | cut -c1-240)" | tee -a "$RES/runs.txt"
  [ -e "$RES/rt.STOPPED" ] && echo "RUN-STOPPED $(cat "$RES/rt.STOPPED")" | tee -a "$RES/runs.txt"
  return $rc
}
fails=0
run_arm new "$RT_NEW" - - || fails=$((fails + 1))
FORCED=$D/new.tokens
if [ "$(wc -w < "$FORCED" 2>/dev/null)" = 256 ]; then
  run_arm base   "$RT_BASE" -                  "$FORCED" || fails=$((fails + 1))
  run_arm newoff "$RT_NEW"  TRON_AMX_DISABLE=1 "$FORCED" || fails=$((fails + 1))
  run_arm poc    "$RT_HEAD" -                  "$FORCED" || fails=$((fails + 1))
else
  echo "$(ts) new.tokens missing or short: no forced arms"; fails=$((fails + 1))
fi
echo "$(ts) runs done, failed=$fails"
cmp_tok() { python3 - "$1" "$2" <<'PY'
import sys, re
a = [int(x) for x in re.findall(r'-?\d+', open(sys.argv[1]).read().splitlines()[0])]
b = [int(x) for x in re.findall(r'-?\d+', open(sys.argv[2]).read().splitlines()[0])]
n = min(len(a), len(b)); d = next((i for i in range(n) if a[i] != b[i]), None)
print(f"{sys.argv[1].split('/')[-1]} vs {sys.argv[2].split('/')[-1]}: " + (f"identical for {n} tokens (lengths {len(a)} / {len(b)})" if d is None else f"first difference at index {d} ({a[d]} vs {b[d]})"))
PY
}
{ echo "# token checks $(ts)"; for a in base newoff poc; do [ -s "$D/$a.tokens" ] && cmp_tok "$D/$a.tokens" "$FORCED"; done; } | tee "$RES/tokens.txt"
for pair in "base new" "new newoff" "base poc"; do set -- $pair
  [ -s "$D/$1.txt" ] && [ -s "$D/$2.txt" ] || { echo "$(ts) skip logits $1 vs $2 (missing)"; continue; }
  python3 "$DD/dd_logits_step.py" --off "$D/$1.txt" --on "$D/$2.txt" --forced "$FORCED" --mark 1 --out "$RES/steps-$1-vs-$2.json" > "$RES/steps-$1-vs-$2.txt" 2>&1; echo "$(ts) dd_logits_step $1 vs $2 rc=$?"
done
python3 - "$RES"/steps-*.json <<'PY' | tee "$RES/verdict.txt"
import json, sys
for p in sys.argv[1:]:
    r = json.load(open(p)); s = r['summary']
    print(f"== {p.split('/')[-1]}: steps={s['n_with_logits']}/{s['n_steps']} identical_steps={s['n_identical_steps']} flips={s['flip_steps']} first_flip={s['first_flip']} "
          f"nonflip median|delta_pair|={s['nonflip_median_abs_delta_pair']} p95={s['nonflip_p95_abs_delta_pair']} median mean|d|={s['nonflip_median_mean_abs_delta']} median frac_changed={s['nonflip_median_frac_changed']} max_tvd={s['max_tvd']} median margin_off={s['median_margin_off']}")
PY
echo "$([ $fails -eq 0 ] && echo ok || echo "failed-runs-$fails")" >"$RES/probe.done"
echo "=== $NAME probe finished $(ts): $(cat "$RES/probe.done") ==="
