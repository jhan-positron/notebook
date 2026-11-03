#!/usr/bin/env bash
# td-20261016 (runs ON delphi-3bda, detached): the issue #4444 root-cause probe. Fork of exec/pr4-20261012/probe83.sh (its
# method, run_arm, guards, whole-machine steps). Forced runs (every arm force-fed the same 256-token sequence, the free-running
# tokens of runtron.pr4 of 2026-10-12) of qwen3-4b tp2, 1 user, prompt 1024, CPU attention, with the FULL --intermediates-file
# kept on the local disk (about 20.6 GB per run) for the per-layer comparison (exec/dd/dd_first_divergence.py, run by
# analyze-td.sh afterwards). Arms (binary, env):
#   new      runtron.pr4      (PR #4959 probe commit ea94e95a4e: VNNI K + AMX; the stack's "new")
#   base     runtron.main1010 (main 72308ec90c, row-major K, AMX dispatch on; the stack's "base")
#   poc      runtron.poc      (ea94e95a4e + jhan-td-poc 017181c02d: VNNI blocks unpacked and scored by the row-major dotter)
#   newoff   runtron.pr4 + TRON_AMX_DISABLE=1   (the kill switch: every page through the VNNI reader + the AVX PV path)
#   trunc    runtron.trunc    (ea94e95a4e + jhan-td-trunc 3d1426f549: AMX PV weights truncated to bf16 like the AVX path)
#   baseoff  runtron.main1010 + TRON_AMX_DISABLE=1 (the row-major binary under the kill switch: the dotter everywhere)
#   pocoff   runtron.poc + TRON_AMX_DISABLE=1
#   clean    runtron.clean    (main 72308ec90c built with TRON_AMX_DISPATCH=OFF: the issue's "row-major binary")
# Predictions written before the runs (see token-divergence-4444/predictions.md): poc == base and pocoff == baseoff == clean
# record for record; trunc == newoff if the AMX and AVX add orders agree; new vs base first differs at prompt token 1, layer 0.
# Whole machine: Bill's marker taken (bill-share.sh take), serving down through platformd, up again at the end, the marker
# released in the exit trap. Waits first for the three new binaries, then for the CI lease / other people. No step after END_BY.
# Usage (on 3bda): [END_BY=<ISO UTC>] bash probe-td.sh    Outputs: exec/results/td-20261016/ (runs.txt, tokens.txt,
# steps-*.txt/json, verdict.txt, probe.done); logs + full intermediates on /var/tmp/jhan/td/; log exec/logs/td-20261016.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
S=$EXEC/sync4424-20261002
DUT=$EXEC/q4b-fpga-20260921/dut.sh
DD=$EXEC/dd
export NAME=td-20261016
END_BY=${END_BY:-2026-10-17T02:15:00Z}
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export RT_HEAD=/var/tmp/jhan/tron-td-clean/gen/runtron.clean
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
RT_POC=/var/tmp/jhan/tron-td-poc/gen/runtron.poc
RT_TRUNC=/var/tmp/jhan/tron-td-trunc/gen/runtron.trunc
export CELLS_ALL="smoke|ingested-qwen-3-4b-instruct-2507-tp2|2|1|1024"
export DEADLINE_HHMM=0215
SYNC_FUNCTIONS_ONLY=1; source "$S/campaign.sh"; unset SYNC_FUNCTIONS_ONLY   # RES, LOG, HPFILE, placement, guards, watch_run, status
OUR_RT_RE='^/var/tmp/jhan/(tron-main1010|tron-pr4|tron-td-[a-z]+)/gen/runtron[.a-z0-9]* '
D=/var/tmp/jhan/td
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
echo "=== $NAME probe started $(ts) pid $$ on $(hostname) forced=$FORCED ($(wc -w < "$FORCED") ids) END_BY=$END_BY ==="
echo "$(ts) machine: $(machine_line) lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
# the three new binaries: wait for the builds (build-clean.sh, build-variant.sh) to finish
w=0; while ! { [ -x "$RT_HEAD" ] && [ -x "$RT_POC" ] && [ -x "$RT_TRUNC" ]; }; do past_end && { echo "$(ts) past END_BY while waiting for the builds: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting for the builds: clean=$([ -x "$RT_HEAD" ] && echo ok || echo no) poc=$([ -x "$RT_POC" ] && echo ok || echo no) trunc=$([ -x "$RT_TRUNC" ] && echo ok || echo no)"; w=1; sleep 60; done
echo "$(ts) binaries present"
chk() { [ "$(git -C "$1" rev-parse HEAD)" = "$2" ] || { echo "$1 is not at $2: abort"; echo failed-tree >"$RES/probe.done"; exit 1; }; }
chk /var/tmp/jhan/tron-pr4 ea94e95a4e30830e33a2e1feda51ac231e97c667
chk /var/tmp/jhan/tron-main1010 72308ec90c80318403c4575dd9ce4a3bc9af5033
chk /var/tmp/jhan/tron-td-clean 72308ec90c80318403c4575dd9ce4a3bc9af5033
chk /var/tmp/jhan/tron-td-poc 017181c02d6f46dd50e33c3d2efe78ebbcccccb4
chk /var/tmp/jhan/tron-td-trunc 3d1426f5491d676900f625edd8e933d04acf7dc5
for b in "$RT_NEW" "$RT_BASE" "$RT_HEAD" "$RT_POC" "$RT_TRUNC"; do [ -x "$b" ] || { echo "$b missing"; echo failed-binary >"$RES/probe.done"; exit 1; }; sha256sum "$b"; done
grep -E "^TRON_(AMX_DISPATCH|K_VNNI):" /var/tmp/jhan/tron-td-clean/gen/CMakeCache.txt | tr '\n' ' '; echo " (clean)"
w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do past_end && { echo "$(ts) past END_BY while waiting for the lease: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting: CI lease busy or another person active"; w=1; sleep 120; done
past_end && { echo "$(ts) past END_BY: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }
tout=$(bash "$EXEC/bill-share.sh" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) echo "$(ts) marker not taken (rc $trc): stop"; echo stopped-marker >"$RES/probe.done"; exit 1;; esac
if rinzler_active; then IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); the runs retry through the guard"; fi
echo "$(ts) serving: $(machine_line) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"

run_arm() {  # run_arm <name> <binary> <"env assignments"|->   (always CPU attention, always force-fed)
  local name=${1:?} bin=${2:?} extra=${3:?}
  local ex=() rc t0
  if [ "$(wc -w < "$D/$name.tokens" 2>/dev/null)" = 256 ] && [ "$(grep -c 'Logits of token' "$D/$name.txt" 2>/dev/null)" -ge 256 ] && [ -s "$D/$name.full" ]; then
    echo "run $name reused: tokens=256 logits-lines=$(grep -c 'Logits of token' "$D/$name.txt") full=$(stat -c %s "$D/$name.full") $(grep -E 'Version:' "$D/$name.log" | head -1 | cut -c1-120)" | tee -a "$RES/runs.txt"; return 0
  fi
  [ "$extra" != - ] && ex=($extra)
  past_end && { echo "$(ts) past END_BY before $name: skip"; return 2; }
  wait_clear || { echo "$(ts) deadline while waiting before $name"; return 2; }
  take_guard || { echo "$(ts) deadline while waiting for the guard before $name"; return 2; }
  status "run $name"
  rm -f "${D:?}/${name:?}.full" "${D:?}/${name:?}.txt" "${D:?}/${name:?}.tokens"
  echo "### $name bin=$bin env=[${extra}] attn=cpu forced=$FORCED $(ts) $(machine_line)" >>"$RES/runs.txt"
  rm -f "${RES:?}/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  t0=$(date +%s)
  (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 "${ex[@]}" TRON_LOG_LEVEL=info \
      timeout -k 30 5400 "$bin" stream-generate-text -m "$MODEL" $(placement 2) --hugepage_file "$HPFILE" -o \
      --prompt-length 1024 -l 256 -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$D/$name.tokens" \
      --intermediates-file "$D/$name.full" --force-feed-text-token-file "$FORCED") >"$D/$name.log" 2>&1
  rc=$?
  stop_watcher; campaign_guard_release; remove_our_slice_files
  grep -E 'Logits of token' "$D/$name.full" > "$D/$name.txt"; echo "$(ts) $name: full log $(stat -c %s "$D/$name.full") bytes kept, filtered to $(stat -c %s "$D/$name.txt") bytes of logits"
  echo "run $name rc=$rc wall=$(( $(date +%s) - t0 ))s tokens=$(wc -w < "$D/$name.tokens" 2>/dev/null) logits-lines=$(grep -c 'Logits of token' "$D/$name.txt" 2>/dev/null) full=$(stat -c %s "$D/$name.full" 2>/dev/null) $(grep -E 'Version:|average tok/s|orced' "$D/$name.log" | tr '\n' ' ' | cut -c1-240)" | tee -a "$RES/runs.txt"
  [ -e "$RES/rt.STOPPED" ] && echo "RUN-STOPPED $(cat "$RES/rt.STOPPED")" | tee -a "$RES/runs.txt"
  return $rc
}
fails=0
run_arm new     "$RT_NEW"   -                  || fails=$((fails + 1))
run_arm base    "$RT_BASE"  -                  || fails=$((fails + 1))
run_arm poc     "$RT_POC"   -                  || fails=$((fails + 1))
run_arm newoff  "$RT_NEW"   TRON_AMX_DISABLE=1 || fails=$((fails + 1))
run_arm trunc   "$RT_TRUNC" -                  || fails=$((fails + 1))
run_arm baseoff "$RT_BASE"  TRON_AMX_DISABLE=1 || fails=$((fails + 1))
run_arm pocoff  "$RT_POC"   TRON_AMX_DISABLE=1 || fails=$((fails + 1))
run_arm clean   "$RT_HEAD"  -                  || fails=$((fails + 1))
echo "$(ts) runs done, failed=$fails"

# ---- token checks and the per-step logit comparison (numpy on 3bda) ----
cmp_tok() { python3 - "$1" "$2" <<'PY'
import sys, re
a = [int(x) for x in re.findall(r'-?\d+', open(sys.argv[1]).read().splitlines()[0])]
b = [int(x) for x in re.findall(r'-?\d+', open(sys.argv[2]).read().splitlines()[0])]
n = min(len(a), len(b)); d = next((i for i in range(n) if a[i] != b[i]), None)
print(f"{sys.argv[1].split('/')[-1]} vs {sys.argv[2].split('/')[-1]}: " + (f"identical for {n} tokens (lengths {len(a)} / {len(b)})" if d is None else f"first difference at index {d} ({a[d]} vs {b[d]})"))
PY
}
{ echo "# token checks $(ts) (forced runs: every arm's output tokens must equal the forced file)"; for a in new base poc newoff trunc baseoff pocoff clean; do [ -s "$D/$a.tokens" ] && cmp_tok "$D/$a.tokens" "$FORCED"; done; } | tee "$RES/tokens.txt"
for pair in "base poc" "baseoff pocoff" "clean baseoff" "base new" "new newoff" "newoff trunc" "new trunc" "baseoff base" "baseoff newoff" "clean new"; do set -- $pair
  [ -s "$D/$1.txt" ] && [ -s "$D/$2.txt" ] || { echo "$(ts) skip logits $1 vs $2 (missing)"; continue; }
  case "$2" in newoff|pocoff|trunc) mark=248;; *) mark=84;; esac
  python3 "$DD/dd_logits_step.py" --off "$D/$1.txt" --on "$D/$2.txt" --forced "$FORCED" --mark $mark --out "$RES/steps-$1-vs-$2.json" > "$RES/steps-$1-vs-$2.txt" 2>&1; echo "$(ts) dd_logits_step $1 vs $2 (mark $mark) rc=$?"
done
python3 - "$RES"/steps-*.json <<'PY' | tee "$RES/verdict.txt"
import json, sys
for p in sys.argv[1:]:
    r = json.load(open(p)); s = r['summary']; m = s.get('marked_step', {})
    print(f"== {p.split('/')[-1]}: steps={s['n_with_logits']}/{s['n_steps']} identical_steps={s['n_identical_steps']} flips={s['flip_steps']} first_flip={s['first_flip']} "
          f"nonflip median|delta_pair|={s['nonflip_median_abs_delta_pair']} p95={s['nonflip_p95_abs_delta_pair']} median mean|d|={s['nonflip_median_mean_abs_delta']} p95={s['nonflip_p95_mean_abs_delta']} median frac_changed={s['nonflip_median_frac_changed']} max_tvd={s['max_tvd']} max|d|={s['max_max_abs_delta']} median margin_off={s['median_margin_off']}")
    if m: print(f"   marked step: off_top1={m['off_top1']} off_top2={m['off_top2']} on_top1={m['on_top1']} on_top2={m['on_top2']} forced={m['forced_id']} margin_off={m['margin_off']:.5f} ({m['margin_off_ulps']} ulps of {m['off_top1_logit']:.4f}) margin_on_same_pair={m['margin_on_same_pair']:.5f} delta_pair={m['delta_pair']:.5f} mean|d|={m['mean_abs_delta']:.6f} max|d|={m['max_abs_delta']:.5f} frac_changed={m['frac_changed']:.3f} tvd={m['tvd']:.5f}")
PY
echo "$([ $fails -eq 0 ] && echo ok || echo "failed-runs-$fails")" >"$RES/probe.done"
echo "=== $NAME probe finished $(ts): $(cat "$RES/probe.done") ==="
