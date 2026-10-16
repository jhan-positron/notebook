#!/usr/bin/env bash
# p83-20261013 (runs ON delphi-3bda, detached): forced-run probe of the token-83 differences of PR #4901 (PR-4 of the PR 4424
# split); fork of exec/pr2-20261011/probe247.sh (its method, its run_arm, its analysis). In the smokes of 2026-10-12 (1 user,
# greedy, seed 1, --pay-for-determinism, prompt 1024, 256 tokens): under CPU attention new (runtron.pr4) and head (runtron.pr3)
# agree and both first differ from base (runtron.main1010) at generated token index 83 (ids 1499 vs 258); under FPGA attention
# new and base agree and head first differs at index 83 (258 vs 1499). Hypothesis (PR #4901, Open items): a near tie of the two
# best tokens at that step, decided by the fp32 add order of the reader (PR-3 and PR-4 on the converted blocks of a partial
# page; PR-3 on the row-major tail) against the dotter's (main; PR-4 on the tail). Method: every step's logits
# (--intermediates-file, about 20 GB per run on the local disk, filtered to the "Logits of token" lines), the forced arms
# force-fed the free-running arm's token sequence, so every arm scores the same context at every step; dd_logits_step.py
# compares two arms step by step and reports the marked step (--mark 84 = token index 83).
# Runs (8, about 5.5 min each):
#   CPU cell (USE_HW_ATTN=0), forced file = the smoke's cpu-p1024/new.tokens:
#     new        runtron.pr4 free-running (its tokens must equal the smoke's new.tokens)
#     newforced  runtron.pr4 force-fed (A/A control: forcing must change no logit)
#     base       runtron.main1010 force-fed            -> the pair new vs base at index 83
#     head       runtron.pr3 force-fed                 -> control: equals new in this cell
#     newoff     runtron.pr4 + TRON_AMX_DISABLE=1 force-fed -> the kill-switch pair new vs newoff at index 247 (codex, PR #4901
#                review, wade checks 6 and 8: the tie must be shown on this binary, not inferred from PR-2's probe)
#   FPGA cell (USE_HW_ATTN unset), forced file = the smoke's fpga-p1024/new.tokens:
#     fnew       runtron.pr4 free-running (its tokens must equal the smoke's fpga new.tokens)
#     fhead      runtron.pr3 force-fed                 -> the pair fnew vs fhead at index 83
#     fbase      runtron.main1010 force-fed            -> control: equals fnew in this cell
# Chained behind the lazy-dotter probe (exec/pr4-20261012/probe-lazy.sh): waits for exec/results/pr4lazy-20261013/probe.done
# and Bill's marker present (that probe's exit handler releases it), then the CI lease. Whole-machine step on jhan's order
# of 2026-10-13 ("go ahead to open PR4, state open items which are to investigate"): Bill's marker taken, serving down
# through platformd, up again at the end, the marker released in the exit trap. No step starts after END_BY.
# Usage (on 3bda): [END_BY=<ISO UTC>] [CHAIN_WAIT=0] bash probe83.sh    Outputs: exec/results/p83-20261013/ (runs.txt,
# tokens.txt, steps-*.txt/json, verdict.txt, probe.done); logits on /var/tmp/jhan/p83/; log exec/logs/p83-20261013.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
S=$EXEC/sync4424-20261002
DUT=$EXEC/q4b-fpga-20260921/dut.sh
DD=$EXEC/dd
export NAME=p83-20261013
END_BY=${END_BY:-2026-10-14T00:30:00Z}
LAZY_DONE=$EXEC/results/pr4lazy-20261013/probe.done
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export RT_HEAD=/var/tmp/jhan/tron-pr3/gen/runtron.pr3
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export CELLS_ALL="smoke|ingested-qwen-3-4b-instruct-2507-tp2|2|1|1024"
export DEADLINE_HHMM=0130
SYNC_FUNCTIONS_ONLY=1; source "$S/campaign.sh"; unset SYNC_FUNCTIONS_ONLY   # RES, LOG, HPFILE, placement, guards, watch_run, status
D=/var/tmp/jhan/p83
FORCED=$EXEC/results/pr4-20261012/smoke/cpu-p1024/new.tokens
FORCED_F=$EXEC/results/pr4-20261012/smoke/fpga-p1024/new.tokens
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
echo "=== $NAME probe started $(ts) pid $$ on $(hostname) forced=$FORCED ($(wc -w < "$FORCED") ids) forced_f=$FORCED_F ($(wc -w < "$FORCED_F") ids) END_BY=$END_BY ==="
echo "$(ts) machine: $(machine_line) lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"
[ "$(git -C /var/tmp/jhan/tron-pr4 rev-parse HEAD)" = ea94e95a4e30830e33a2e1feda51ac231e97c667 ] || { echo "tron-pr4 is not at ea94e95a4e: abort"; echo failed-tree >"$RES/probe.done"; exit 1; }
[ "$(git -C /var/tmp/jhan/tron-pr3 rev-parse HEAD)" = dfafd13dce ] 2>/dev/null || [ "$(git -C /var/tmp/jhan/tron-pr3 rev-parse --short=10 HEAD)" = dfafd13dce ] || { echo "tron-pr3 is not at dfafd13dce: abort"; echo failed-tree >"$RES/probe.done"; exit 1; }
[ "$(git -C /var/tmp/jhan/tron-main1010 rev-parse HEAD)" = 72308ec90c80318403c4575dd9ce4a3bc9af5033 ] || { echo "tron-main1010 is not at 72308ec90c: abort"; echo failed-tree >"$RES/probe.done"; exit 1; }
for b in "$RT_NEW" "$RT_HEAD" "$RT_BASE"; do [ -x "$b" ] || { echo "$b missing"; echo failed-binary >"$RES/probe.done"; exit 1; }; sha256sum "$b"; done
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
if [ "${CHAIN_WAIT:-1}" = 1 ]; then w=0; while ! { [ -s "$LAZY_DONE" ] && [ -e /bill-has-instance-0,2 ]; }; do past_end && { echo "$(ts) past END_BY while waiting for the lazy-dotter probe: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting for the lazy-dotter probe ($LAZY_DONE) and Bill's marker"; w=1; sleep 120; done; echo "$(ts) lazy-dotter probe over: $(cat "$LAZY_DONE"), marker present"; fi
w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do past_end && { echo "$(ts) past END_BY while waiting for the lease: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting: CI lease busy or another person active"; w=1; sleep 120; done
past_end && { echo "$(ts) past END_BY: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }
tout=$(bash "$EXEC/bill-share.sh" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) echo "$(ts) marker not taken (rc $trc): stop"; echo stopped-marker >"$RES/probe.done"; exit 1;; esac
if rinzler_active; then IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); the runs retry through the guard"; fi
echo "$(ts) serving: $(machine_line) units=$(systemctl is-active rinzler@0 rinzler@1 | tr '\n' ' ')"

run_arm() {  # run_arm <name> <binary> <"env assignments"|-> <forced file|-> <cpu|fpga>
  local name=$1 bin=$2 extra=$3 forced=$4 attn=$5 ff=() ex=() hw=() rc t0
  if [ "$attn" = fpga ]; then hw=(-u USE_HW_ATTN); else hw=(USE_HW_ATTN=0); fi
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
  echo "### $name bin=$bin env=[${extra}] attn=$attn forced=$forced $(ts) $(machine_line)" >>"$RES/runs.txt"
  rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  t0=$(date +%s)
  (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE "${hw[@]}" "${ex[@]}" TRON_LOG_LEVEL=info \
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
run_arm new       "$RT_NEW"  - -           cpu  || fails=$((fails + 1))
run_arm newforced "$RT_NEW"  - "$FORCED"   cpu  || fails=$((fails + 1))
run_arm base      "$RT_BASE" - "$FORCED"   cpu  || fails=$((fails + 1))
run_arm head      "$RT_HEAD" - "$FORCED"   cpu  || fails=$((fails + 1))
run_arm newoff    "$RT_NEW"  TRON_AMX_DISABLE=1 "$FORCED" cpu || fails=$((fails + 1))
run_arm fnew      "$RT_NEW"  - -           fpga || fails=$((fails + 1))
run_arm fhead     "$RT_HEAD" - "$FORCED_F" fpga || fails=$((fails + 1))
run_arm fbase     "$RT_BASE" - "$FORCED_F" fpga || fails=$((fails + 1))
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
{ echo "# token checks $(ts)"; cmp_tok "$D/new.tokens" "$FORCED"; cmp_tok "$D/newforced.tokens" "$FORCED"; cmp_tok "$D/base.tokens" "$FORCED"; cmp_tok "$D/head.tokens" "$FORCED"; cmp_tok "$D/newoff.tokens" "$FORCED"; cmp_tok "$D/fnew.tokens" "$FORCED_F"; cmp_tok "$D/fhead.tokens" "$FORCED_F"; cmp_tok "$D/fbase.tokens" "$FORCED_F"; } | tee "$RES/tokens.txt"
for pair in "new base" "new head" "new newforced" "fnew fhead" "fnew fbase" "new newoff"; do set -- $pair
  case $1 in f*) fc=$FORCED_F;; *) fc=$FORCED;; esac
  case "$1 $2" in "new newoff") mark=248;; *) mark=84;; esac
  python3 "$DD/dd_logits_step.py" --off "$D/$1.txt" --on "$D/$2.txt" --forced "$fc" --mark $mark --out "$RES/steps-$1-vs-$2.json" > "$RES/steps-$1-vs-$2.txt" 2>&1; echo "$(ts) dd_logits_step $1 vs $2 (mark $mark) rc=$?"
done
python3 - "$RES/steps-new-vs-base.json" "$RES/steps-new-vs-head.json" "$RES/steps-new-vs-newforced.json" "$RES/steps-fnew-vs-fhead.json" "$RES/steps-fnew-vs-fbase.json" "$RES/steps-new-vs-newoff.json" <<'PY' | tee "$RES/verdict.txt"
import json, sys
for p in sys.argv[1:]:
    r = json.load(open(p)); s = r['summary']; m = s.get('marked_step', {})
    print(f"== {p.split('/')[-1]}: steps={s['n_with_logits']}/{s['n_steps']} identical_steps={s['n_identical_steps']} flips={s['flip_steps']} first_flip={s['first_flip']} "
          f"nonflip median|delta_pair|={s['nonflip_median_abs_delta_pair']} p95={s['nonflip_p95_abs_delta_pair']} median mean|d|={s['nonflip_median_mean_abs_delta']} p95={s['nonflip_p95_mean_abs_delta']} median frac_changed={s['nonflip_median_frac_changed']} max_tvd={s['max_tvd']} max|d|={s['max_max_abs_delta']} median margin_off={s['median_margin_off']}")
    if m: print(f"   step {s.get('marked', r.get('mark', '?'))} (token index {int(s.get('marked', r.get('mark', 0)) or 0) - 1}): off_top1={m['off_top1']} off_top2={m['off_top2']} on_top1={m['on_top1']} on_top2={m['on_top2']} forced={m['forced_id']} margin_off={m['margin_off']:.5f} ({m['margin_off_ulps']} ulps of {m['off_top1_logit']:.4f}) margin_on_same_pair={m['margin_on_same_pair']:.5f} delta_pair={m['delta_pair']:.5f} mean|d|={m['mean_abs_delta']:.6f} max|d|={m['max_abs_delta']:.5f} frac_changed={m['frac_changed']:.3f} tvd={m['tvd']:.5f} forced_rank_off={m['forced_rank_off']} forced_rank_on={m['forced_rank_on']}")
PY
echo "$([ $fails -eq 0 ] && echo ok || echo "failed-runs-$fails")" >"$RES/probe.done"
echo "=== $NAME probe finished $(ts): $(cat "$RES/probe.done") ==="
