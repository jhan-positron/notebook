#!/usr/bin/env bash
# p247-20261011 (runs ON delphi-3bda, detached): forced-run probe of the token-247 difference of PR #4887 (PR-2 of the
# PR 4424 split). In the CPU prompt-1024 smoke of 2026-10-11, newoff (runtron.pr2 with TRON_AMX_DISABLE=1) and new
# (runtron.pr2) first differ at generated token index 247 (0-based; token ids 624 vs 13); head (runtron.pr1) gives 624 too.
# Hypothesis: a near tie at that step, flipped by the numerical difference between the AMX path (new) and the AVX-512
# reader path (newoff, head). Method (exec/dd/dd-campaign-v3.sh, dd_logits_step.py): log every step's vocabulary logits
# (--intermediates-file) and compare the two arms step by step with newoff and head force-fed new's token sequence, so all
# arms score the same context at every step. This tree has no intermediates filter (TRON_INTERMEDIATES_FILTER was a debug
# branch), and runtron deletes and recreates the log path (std::remove, then open), so a named pipe does not work (the first
# launch, 18:15 UTC, hung on that). The full log (about 20.6 GB per run, every layer's activations of the 1,280 tokens) goes
# to a regular file on the local disk; grep then keeps the "Logits of token N" lines (dense logits and the top-k records)
# and the full log is deleted. A run whose <name>.tokens (256 ids) and <name>.txt (>= 256 Logits lines) exist is skipped,
# and a leftover <name>.fifo regular file from the first launch is filtered the same way (the `new` run completed there).
# Runs, all CPU attention, prompt 1024, 1 user, greedy, seed 1, --pay-for-determinism, 256 tokens
# (the smoke recipe of sync4424-20261002/smoke.sh):
#   new        runtron.pr2 free-running (its tokens must equal the smoke's new.tokens)      -> the OFF arm of the comparison
#   newforced  runtron.pr2 force-fed new.tokens (forcing must change no logit: A/A control)
#   newoff     runtron.pr2 + TRON_AMX_DISABLE=1 force-fed new.tokens                      -> the ON arm (the reader)
#   head       runtron.pr1 force-fed new.tokens (control: with the kill switch newoff runs the reader as head does)
# Whole-machine step: Bill's marker is taken (jhan's order of 2026-10-11 ~16:3x UTC: "go ahead with machine test"),
# serving goes down through platformd, comes back up at the end, the marker is released in the exit trap.
# Usage (on 3bda): bash probe247.sh    Outputs: exec/results/p247-20261011/ (runs.txt, steps-*.txt/json, tokens-*.txt,
# probe.done), logits logs on /var/tmp/jhan/p247/ (local disk), log exec/logs/p247-20261011.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
S=$EXEC/sync4424-20261002
DUT=$EXEC/q4b-fpga-20260921/dut.sh
DD=$EXEC/dd
export NAME=p247-20261011
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export RT_HEAD=/var/tmp/jhan/tron-pr1/gen/runtron.pr1
export RT_NEW=/var/tmp/jhan/tron-pr2/gen/runtron.pr2
export CELLS_ALL="smoke|ingested-qwen-3-4b-instruct-2507-tp2|2|1|1024"
export DEADLINE_HHMM=0130
SYNC_FUNCTIONS_ONLY=1; source "$S/campaign.sh"; unset SYNC_FUNCTIONS_ONLY   # RES, LOG, HPFILE, placement, guards, watch_run, status
D=/var/tmp/jhan/p247
FORCED=$EXEC/results/pr2-20261011/smoke/cpu-p1024/new.tokens
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
mkdir -p "$RES" "$D"
exec >>"$LOG" 2>&1
rm -f "$RES/probe.done"
MARKER_TAKEN=0
finish() { stop_watcher; kill_ours; remove_our_slice_files; campaign_guard_release 2>/dev/null
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"; elif rinzler_active; then echo "$(ts) serving: units active, nothing to bring up"; else timeout 900 bash "$DUT" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
  [ "$MARKER_TAKEN" = 1 ] && { bash "$EXEC/bill-share.sh" release 2>&1 | tail -1; echo "$(ts) Bill marker released"; }
  echo "$(ts) machine at exit: $(machine_line) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"; }
trap finish EXIT
echo "=== $NAME probe started $(ts) pid $$ on $(hostname) forced=$FORCED ($(wc -w < "$FORCED") ids) ==="
echo "$(ts) machine: $(machine_line) lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"
[ "$(git -C /var/tmp/jhan/tron-pr2 rev-parse HEAD)" = 0ee8671d355863658bbf292a12e04a566ac1af29 ] || { echo "tron-pr2 is not at 0ee8671d35: abort"; echo failed-tree >"$RES/probe.done"; exit 1; }
[ "$(git -C /var/tmp/jhan/tron-pr1 rev-parse HEAD)" = 82d05e94bea0dda172c9d23a7b5f58e90a7d7f49 ] || { echo "tron-pr1 is not at 82d05e94be: abort"; echo failed-tree >"$RES/probe.done"; exit 1; }
for b in "$RT_NEW" "$RT_HEAD"; do [ -x "$b" ] || { echo "$b missing"; echo failed-binary >"$RES/probe.done"; exit 1; }; sha256sum "$b"; done
w=0; while ci_lease_busy 600; do [ $w = 0 ] && echo "$(ts) waiting: CI lease busy"; w=1; sleep 120; done
tout=$(bash "$EXEC/bill-share.sh" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) echo "$(ts) marker not taken (rc $trc): stop"; echo stopped-marker >"$RES/probe.done"; exit 1;; esac
if rinzler_active; then IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); the runs retry through the guard"; fi
echo "$(ts) serving: $(machine_line) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"

run_arm() {  # run_arm <name> <binary> <"env assignments"|-> <forced file|->
  local name=$1 bin=$2 extra=$3 forced=$4 ff=() ex=() rc t0
  if [ -f "$D/$name.fifo" ] && [ ! -s "$D/$name.txt" ]; then   # the first launch's regular file (runtron replaced the pipe)
    grep -E 'Logits of token' "$D/$name.fifo" > "$D/$name.txt"; echo "$(ts) $name: leftover full log $(stat -c %s "$D/$name.fifo") bytes filtered to $(stat -c %s "$D/$name.txt") bytes"; rm -f "$D/$name.fifo"
  fi
  if [ "$(wc -w < "$D/$name.tokens" 2>/dev/null)" = 256 ] && [ "$(grep -c 'Logits of token' "$D/$name.txt" 2>/dev/null)" -ge 256 ]; then
    echo "run $name reused: tokens=256 logits-lines=$(grep -c 'Logits of token' "$D/$name.txt") $(grep -E 'Version:' "$D/$name.log" | head -1 | cut -c1-120)" | tee -a "$RES/runs.txt"; return 0
  fi
  [ "$forced" != - ] && ff=(--force-feed-text-token-file "$forced")
  [ "$extra" != - ] && ex=($extra)
  wait_clear || { echo "$(ts) deadline while waiting before $name"; return 2; }
  take_guard || { echo "$(ts) deadline while waiting for the guard before $name"; return 2; }
  status "run $name"
  rm -f "$D/$name.full" "$D/$name.txt" "$D/$name.tokens"
  echo "### $name bin=$bin env=[${extra}] forced=$forced $(ts) $(machine_line)" >>"$RES/runs.txt"
  rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  t0=$(date +%s)
  (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 "${ex[@]}" TRON_LOG_LEVEL=info \
      timeout -k 30 5400 "$bin" stream-generate-text -m "$MODEL" $(placement 2) --hugepage_file "$HPFILE" -o \
      --prompt-length 1024 -l 256 -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$D/$name.tokens" \
      --intermediates-file "$D/$name.full" "${ff[@]}") >"$D/$name.log" 2>&1
  rc=$?
  stop_watcher; campaign_guard_release; remove_our_slice_files
  grep -E 'Logits of token' "$D/$name.full" > "$D/$name.txt"; echo "$(ts) $name: full log $(stat -c %s "$D/$name.full") bytes filtered to $(stat -c %s "$D/$name.txt") bytes"; rm -f "$D/$name.full"
  echo "run $name rc=$rc wall=$(( $(date +%s) - t0 ))s tokens=$(wc -w < "$D/$name.tokens" 2>/dev/null) logits-lines=$(grep -c 'Logits of token' "$D/$name.txt" 2>/dev/null) bytes=$(stat -c %s "$D/$name.txt" 2>/dev/null) $(grep -E 'Version:|average tok/s|orced' "$D/$name.log" | tr '\n' ' ' | cut -c1-240)" | tee -a "$RES/runs.txt"
  [ -e "$RES/rt.STOPPED" ] && echo "RUN-STOPPED $(cat "$RES/rt.STOPPED")" | tee -a "$RES/runs.txt"
  return $rc
}
fails=0
run_arm new       "$RT_NEW"  -                   -         || fails=$((fails + 1))
run_arm newforced "$RT_NEW"  -                   "$FORCED" || fails=$((fails + 1))
run_arm newoff    "$RT_NEW"  TRON_AMX_DISABLE=1  "$FORCED" || fails=$((fails + 1))
run_arm head      "$RT_HEAD" -                   "$FORCED" || fails=$((fails + 1))
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
{ echo "# token checks $(ts)"; cmp_tok "$D/new.tokens" "$FORCED"; cmp_tok "$D/newforced.tokens" "$FORCED"; cmp_tok "$D/newoff.tokens" "$FORCED"; cmp_tok "$D/head.tokens" "$FORCED"; } | tee "$RES/tokens.txt"
for pair in "new newoff" "new head" "new newforced" "newoff head"; do set -- $pair
  python3 "$DD/dd_logits_step.py" --off "$D/$1.txt" --on "$D/$2.txt" --forced "$FORCED" --mark 248 --out "$RES/steps-$1-vs-$2.json" > "$RES/steps-$1-vs-$2.txt" 2>&1; echo "$(ts) dd_logits_step $1 vs $2 rc=$?"
done
python3 - "$RES/steps-new-vs-newoff.json" "$RES/steps-new-vs-head.json" "$RES/steps-new-vs-newforced.json" "$RES/steps-newoff-vs-head.json" <<'PY' | tee "$RES/verdict.txt"
import json, sys
for p in sys.argv[1:]:
    r = json.load(open(p)); s = r['summary']; m = s.get('marked_step', {})
    print(f"== {p.split('/')[-1]}: steps={s['n_with_logits']}/{s['n_steps']} identical_steps={s['n_identical_steps']} flips={s['flip_steps']} first_flip={s['first_flip']} "
          f"nonflip median|delta_pair|={s['nonflip_median_abs_delta_pair']} p95={s['nonflip_p95_abs_delta_pair']} median mean|d|={s['nonflip_median_mean_abs_delta']} p95={s['nonflip_p95_mean_abs_delta']} median frac_changed={s['nonflip_median_frac_changed']} max_tvd={s['max_tvd']} max|d|={s['max_max_abs_delta']} median margin_off={s['median_margin_off']}")
    if m: print(f"   step 248 (token index 247): off_top1={m['off_top1']} off_top2={m['off_top2']} on_top1={m['on_top1']} on_top2={m['on_top2']} forced={m['forced_id']} margin_off={m['margin_off']:.5f} ({m['margin_off_ulps']} ulps of {m['off_top1_logit']:.4f}) margin_on_same_pair={m['margin_on_same_pair']:.5f} delta_pair={m['delta_pair']:.5f} mean|d|={m['mean_abs_delta']:.6f} max|d|={m['max_abs_delta']:.5f} frac_changed={m['frac_changed']:.3f} tvd={m['tvd']:.5f} forced_rank_off={m['forced_rank_off']} forced_rank_on={m['forced_rank_on']}")
PY
echo "$([ $fails -eq 0 ] && echo ok || echo "failed-runs-$fails")" >"$RES/probe.done"
echo "=== $NAME probe finished $(ts): $(cat "$RES/probe.done") ==="
