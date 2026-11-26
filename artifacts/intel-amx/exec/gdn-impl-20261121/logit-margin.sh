#!/usr/bin/env bash
# gdn-impl-20261121: how close are the two best scores at the step where an arm picks another token?
# Runs ON delphi-3b35, on OUR half, through exec/gdn-20261120/run-one.sh. One run at a time.
#
# Why: token-check.sh found that the arm with the AMX attention kernels picks another token than the base arm at
# generated token 1 of the prompt of 1,024 tokens. The sampler takes the best score (temperature 0). If the two
# best scores of the base arm are equal or one bf16 step apart at that step, a change of rare low bits can
# change the choice. This script reads the scores.
# How: runtron --intermediates-file writes every logged vector of every token as text. The file is large, so it
# goes to the local disk and only the lines with the best scores of the generated tokens are kept:
#   "Top-k Logits of token N" and "Top-k Token IDs for Logits of token N".
# Words: runtron = tron's command-line tool; arm = one build with one set of switches (see campaign.sh);
# logits = the scores of all vocabulary words for the next token; bf16 = a 16-bit float format.
# Step 1 measures the file size per token with a prompt of 64 tokens. The script stops when the full run would
# need more than MAX_GB of disk or more than half of the free space.
# Output: exec/results/gdn-impl-20261121/tokens/logits-p<prompt>-l<len>__<arm>.txt and logits-summary-p<prompt>-l<len>.txt
#         (logit_summary.py makes the summary)
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=gdn-impl-20261121
RES=$EXEC/results/$NAME
OUT=$RES/tokens
PROMPT=${PROMPT:-1024}
LEN=${LEN:-4}
MAX_GB=${MAX_GB:-60}
BIG=/var/tmp/jhan/$NAME-intermediates.txt
STATS="TRON_ATTN_STATS=1 TRON_GDN_STATS=1"
ARMS_ALL=$'base|ctr|'"$STATS"$'
b|pab|'"$STATS"$' TRON_AMX_GDN_DISABLE=1
a|pa|'"$STATS"$'
ab|pab|'"$STATS"
ARMS=${ARMS:-"base b"}
mkdir -p "$OUT"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
arm_field() { local line; line=$(grep -m1 "^$1|" <<<"$ARMS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
one_run() {  # run-name arm prompt len
  rm -f "$BIG"
  RUN=$1 USERS=1 PROMPT=$3 LEN=$4 TAG=$(arm_field "$2" 2) NAME=$NAME TMO=${TMO:-1500} ARMENV="$(arm_field "$2" 3)" \
    EXTRA="--temperature 0 --pay-for-determinism --intermediates-file $BIG" bash "$EXEC/gdn-20261120/run-one.sh" 2>&1 | grep -a "RUN-" | tail -1
}
echo "=== logit margin started $(date -u +%FT%TZ) prompt=$PROMPT len=$LEN arms=[$ARMS] ==="
# The trial generates 2 tokens, so runtron prints no decode rate and run-one.sh calls the run failed. The file is
# what the trial is for. PER_TOKEN=<bytes> skips the trial (9,133,727 bytes per token were measured on 2026-11-22).
if [ -z "${PER_TOKEN:-}" ]; then
  one_run "logit-trial-p64__base__rep$(date +%s)" base 64 2
  [ -s "$BIG" ] || { echo "the trial run wrote no intermediates file"; exit 2; }
  bytes=$(stat -c %s "$BIG"); per_token=$((bytes / 66))
  grep -a -c "Top-k Logits of token" "$BIG" | sed 's/^/trial: Top-k Logits lines = /'
  rm -f "$BIG"
else
  bytes=0; per_token=$PER_TOKEN
fi
need_gb=$(( per_token * (PROMPT + LEN) / 1000000000 + 1 ))
free_gb=$(( $(df --output=avail -B1000000000 /var/tmp/jhan | tail -1) ))
echo "trial: $bytes bytes for 66 tokens = $per_token bytes per token; the full run needs about $need_gb GB; free $free_gb GB"
if [ "$need_gb" -gt "$MAX_GB" ] || [ $((need_gb * 2)) -gt "$free_gb" ]; then echo "too large; stopping"; exit 3; fi
for arm in $ARMS; do
  f=$OUT/logits-p${PROMPT}-l${LEN}__$arm.txt
  [ -s "$f" ] && continue
  one_run "logit-q35-tp4-1u-p${PROMPT}-l${LEN}__${arm}__rep1" "$arm" "$PROMPT" "$LEN"
  grep -a -E "Top-k (Logits|Token IDs for Logits) of token" "$BIG" >"$f" 2>/dev/null || echo "no top-k lines for $arm"
  ls -la "$BIG" 2>/dev/null | awk '{print "intermediates file bytes:", $5}'
  rm -f "$BIG"
  sleep 3
done
python3 "$EXEC/$NAME/logit_summary.py" "$OUT" "$PROMPT" "$LEN" $ARMS | tee "$OUT/logits-summary-p$PROMPT-l$LEN.txt"
echo "=== logit margin finished $(date -u +%FT%TZ) ==="
