#!/usr/bin/env bash
# glimext-20261018 near-tie margin probe (runs ON delphi-3bda, our half, called by chain.sh step E when the Glimmer CPU
# identity cell showed head (AMX) and base (AVX) generating different tokens): two teacher-forced runs of Muse Glimmer 30B
# tp2, 1 user, CPU attention, both fed the base arm's generated ids (FORCED = the identity cell's base.tokens), each with
# --intermediates-file so that every step's logits are recorded; then exec/dd/dd_logits_step.py compares the two logit
# rows step by step and reports, at the step where the free-running tokens first differed (MARK, 1-based), the base arm's
# top-1 minus top-2 margin in logit units and in bf16 ulps, and the head arm's change of that pair. This is the issue
# #4444 measurement (near tie flipped by a different fp32 add order) for the kv_mul-16 kernel.
# Words: forced run = teacher forcing (--force-feed-text-token-file: the ids are fed back regardless of the argmax; the
# logits of every step stay the model's own); the records file = --intermediates-file (every layer's outputs, tens of GB;
# only the 'Logits of token' lines are kept, the file is deleted after the filter).
# Usage: FORCED=<base.tokens> MARK=<1-based step> [MODEL=ingested-meta-models--Muse-Glimmer-30B-tp2] [TP=2] [PROMPT=1024]
#        [LEN=256] [END_BY=<ISO UTC>] [RT_BASE=...] [RT_HEAD=...] bash margin.sh
# Outputs: exec/results/glimext-20261018/margin/{baseF.txt,headF.txt,<arm>.tokens,<arm>.log,steps-base-vs-head.{json,txt},margin.txt,margin.done}.
# Scratch: /var/tmp/jhan/glimext-margin/<arm>.full (deleted at the end). Never edit this file while it runs on 3bda.
# 2026-10-18: the first run passed --prompt-len PROMPT to dd_logits_step.py; Glimmer's tokenizer adds a BOS token (1025 prompt
# tokens, first 'Logits of token 1024'), which shifted every step by one (first_flip 55 for a free-running divergence at index 53).
# The prompt length is now derived from the log (steps-base-vs-head-v2.json = the corrected analysis of that run).
EXEC=/home/jhan/workspace/intel-AMX/exec
export NAME=${NAME:-glimext-20261018}
FORCED=${FORCED:?FORCED (the --output-token-file row of the base arm) is required}
MARK=${MARK:?MARK (1-based step of the first free-running difference) is required}
MODEL=${MODEL:-ingested-meta-models--Muse-Glimmer-30B-tp2}; TP=${TP:-2}; PROMPT=${PROMPT:-1024}; LEN=${LEN:-256}
END_BY=${END_BY:-}
D=/var/tmp/jhan/glimext-margin
CAMPAIGN_FUNCTIONS_ONLY=1; source "$EXEC/glimext-20261018/campaign.sh"   # guards, placement, watcher, cleanup
unset CAMPAIGN_FUNCTIONS_ONLY
M=$RES/margin; mkdir -p "$M" "$D"
exec >>"$LOG" 2>&1
rm -f "$M/margin.done"
echo "=== $NAME margin started $(ts) pid $$ model=$MODEL tp=$TP prompt=$PROMPT len=$LEN forced=$FORCED mark=$MARK end_by=${END_BY:-none} ==="
[ -s "$FORCED" ] || { echo "$(ts) FORCED $FORCED missing or empty"; echo "failed-no-forced" >"$M/margin.done"; exit 1; }
[ "$(wc -w <"$FORCED")" = "$LEN" ] || { echo "$(ts) FORCED has $(wc -w <"$FORCED") ids, expected $LEN"; echo "failed-forced-len" >"$M/margin.done"; exit 1; }
past_end() { [ -n "$END_BY" ] && [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
NEED_HUGEPAGES=$([ "$TP" = 4 ] && echo 256 || echo 128)
placement "$TP" >/dev/null || { echo "$(ts) TP $TP has no placement"; echo "failed-bad-tp" >"$M/margin.done"; exit 1; }
trap 'stop_watcher; kill_ours; remove_our_slice_files; campaign_guard_release 2>/dev/null; rm -f "${D:?}"/*.full' EXIT
run_forced() {  # $1 arm name (baseF|headF) $2 binary
  local arm=$1 bin=$2 wt rc t0
  wt=$(wt_of "$bin")
  [ -s "$M/$arm.txt" ] && [ "$(wc -w <"$M/$arm.tokens" 2>/dev/null)" = "$LEN" ] && [ "$(grep -c 'Logits of token' "$M/$arm.txt")" -ge "$LEN" ] && { echo "$(ts) $arm already done ($(grep -c 'Logits of token' "$M/$arm.txt") logits lines)"; return 0; }
  past_end && { echo "$(ts) past END_BY before $arm: skip"; return 2; }
  wait_clear || { echo "$(ts) deadline while waiting before $arm"; return 2; }
  take_guard || { echo "$(ts) deadline while waiting for the guard before $arm"; return 2; }
  status "margin $arm"
  rm -f "${D:?}/${arm:?}.full" "$M/$arm.txt" "$M/$arm.tokens"
  echo "### margin arm=$arm bin=$bin model=$MODEL tp=$TP attn=cpu prompt=$PROMPT len=$LEN users=1 temperature=0 pay-for-determinism seed=1 forced=$FORCED $(ts) $(machine_line)" >>"$M/margin.txt"
  rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  t0=$(date +%s)
  (cd "$wt" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=info \
      timeout -k 30 5400 "$bin" stream-generate-text -m "$MODEL" $(placement "$TP") --hugepage_file "$HPFILE" -o \
      --prompt-length "$PROMPT" -l "$LEN" -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$M/$arm.tokens" \
      --intermediates-file "$D/$arm.full" --force-feed-text-token-file "$FORCED") >"$M/$arm.log" 2>&1
  rc=$?
  stop_watcher; campaign_guard_release; remove_our_slice_files
  grep -E 'Logits of token' "$D/$arm.full" >"$M/$arm.txt" 2>/dev/null
  echo "run $arm rc=$rc wall=$(( $(date +%s) - t0 ))s tokens=$(wc -w <"$M/$arm.tokens" 2>/dev/null) logits-lines=$(grep -c 'Logits of token' "$M/$arm.txt" 2>/dev/null) full=$(stat -c %s "$D/$arm.full" 2>/dev/null) $(grep -E 'Version:|average tok/s|orced' "$M/$arm.log" | tr '\n' ' ' | cut -c1-240)" | tee -a "$M/margin.txt"
  rm -f "${D:?}/${arm:?}.full"
  [ -e "$RES/rt.STOPPED" ] && { echo "RUN-STOPPED $(cat "$RES/rt.STOPPED")" | tee -a "$M/margin.txt"; rm -f "$M/$arm.txt"; return 1; }
  [ $rc -eq 0 ] && [ "$(wc -w <"$M/$arm.tokens" 2>/dev/null)" = "$LEN" ] && [ "$(grep -c 'Logits of token' "$M/$arm.txt")" -ge "$LEN" ] || { echo "RUN-FAILED $arm rc=$rc" | tee -a "$M/margin.txt"; rm -f "$M/$arm.txt"; return 1; }
  return 0
}
fails=0
run_forced baseF "$RT_BASE" || fails=$((fails + 1))
run_forced headF "$RT_HEAD" || fails=$((fails + 1))
cmp_tok() { python3 - "$1" "$2" <<'PY'
import sys, re
a = [int(x) for x in re.findall(r'-?\d+', open(sys.argv[1]).read().splitlines()[0])]
b = [int(x) for x in re.findall(r'-?\d+', open(sys.argv[2]).read().splitlines()[0])]
n = min(len(a), len(b)); d = next((i for i in range(n) if a[i] != b[i]), None)
print(f"{sys.argv[1].split('/')[-1]} vs forced: " + (f"identical for {n} tokens (lengths {len(a)} / {len(b)})" if d is None else f"first difference at index {d} ({a[d]} vs {b[d]})"))
PY
}
{ echo "# token checks $(ts) (forced runs: every arm's output tokens must equal the forced file)"; for a in baseF headF; do [ -s "$M/$a.tokens" ] && cmp_tok "$M/$a.tokens" "$FORCED"; done; } | tee -a "$M/margin.txt"
if [ $fails -eq 0 ] && [ -s "$M/baseF.txt" ] && [ -s "$M/headF.txt" ]; then
  nice -n10 taskset -c 72-143 python3 "$EXEC/dd/dd_logits_step.py" --off "$M/baseF.txt" --on "$M/headF.txt" --forced "$FORCED" --mark "$MARK" --out "$M/steps-base-vs-head.json" >"$M/steps-base-vs-head.txt" 2>&1; arc=$?
  echo "$(ts) dd_logits_step base vs head (mark $MARK) rc=$arc"
  python3 - "$M/steps-base-vs-head.json" "$MARK" <<'PY' | tee -a "$M/margin.txt"
import json, sys
r = json.load(open(sys.argv[1])); s = r['summary']; m = s.get('marked_step', {})
print(f"MARGIN steps={s['n_with_logits']}/{s['n_steps']} identical_steps={s['n_identical_steps']} flips={s['flip_steps']} first_flip={s['first_flip']} "
      f"nonflip median|delta_pair|={s['nonflip_median_abs_delta_pair']} p95={s['nonflip_p95_abs_delta_pair']} median mean|d|={s['nonflip_median_mean_abs_delta']} max_tvd={s['max_tvd']} median margin_off={s['median_margin_off']}")
if m: print(f"MARKED step={sys.argv[2]} off_top1={m['off_top1']} off_top2={m['off_top2']} on_top1={m['on_top1']} on_top2={m['on_top2']} forced={m['forced_id']} margin_off={m['margin_off']:.5f} ({m['margin_off_ulps']} ulps of {m['off_top1_logit']:.4f}) margin_on_same_pair={m['margin_on_same_pair']:.5f} delta_pair={m['delta_pair']:.5f} mean|d|={m['mean_abs_delta']:.6f} max|d|={m['max_abs_delta']:.5f} frac_changed={m['frac_changed']:.3f} tvd={m['tvd']:.5f}")
else: print(f"MARKED step={sys.argv[2]}: not in the compared steps")
PY
  [ $arc -eq 0 ] && echo ok >"$M/margin.done" || echo "failed-analysis" >"$M/margin.done"
else
  echo "failed-runs-$fails" >"$M/margin.done"
fi
echo "=== $NAME margin finished $(ts): $(cat "$M/margin.done") ==="
