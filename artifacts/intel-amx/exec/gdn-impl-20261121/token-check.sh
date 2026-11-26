#!/usr/bin/env bash
# gdn-impl-20261121: do the builds and switches of the campaign generate the same tokens for the same prompt?
# Runs ON delphi-3b35, on OUR half (SYSTEM_CONFIG="--instance 1,2"), through exec/gdn-20261120/run-one.sh.
#
# Why: Part 0 (the GDN chain kernel) must give the bits of today's token loop, so with fixed settings the base
# build and every arm without an AMX kernel must generate the same tokens. Part A and Part B change rare output
# bits, so their tokens may differ from some generated token on.
# How: one user, the fixed prompt text that runtron ships, temperature 0 (the sampler takes the token with the
# highest score, so the seed has no effect), --pay-for-determinism (fixed split of the worker threads), and
# --output-token-file. The token files of the arms are then compared.
# Words: runtron = tron's command-line tool; arm = one build with one set of switches (see campaign.sh).
# Output: exec/results/gdn-impl-20261121/tokens/<prompt>__<arm>.txt and tokens/summary.txt
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=gdn-impl-20261121
RES=$EXEC/results/$NAME
OUT=$RES/tokens
PROMPTS=${PROMPTS:-"1024 4096"}
LEN=${LEN:-256}
STATS="TRON_ATTN_STATS=1 TRON_GDN_STATS=1"
ARMS_ALL=$'orig|base|TRON_ATTN_STATS=1
base|ctr|'"$STATS"$'
p0|pab|'"$STATS"$' TRON_AMX_DISABLE=1
a0|pa|'"$STATS"$' TRON_AMX_GDN_DISABLE=1
a|pa|'"$STATS"$'
b|pab|'"$STATS"$' TRON_AMX_GDN_DISABLE=1
ab|pab|'"$STATS"$'
base2|ctr|'"$STATS"$'
a2|pa|'"$STATS"$'
b2|pab|'"$STATS"$' TRON_AMX_GDN_DISABLE=1
ab2|pab|'"$STATS"$'
bonly|partb|'"$STATS"
# base2, a2, b2, ab2 = a second run of the same arm (are the tokens of a run repeatable?).
# bonly = the Part B commit alone on the base commit (build tag partb): today's GDN token loop with the AMX
# attention kernels, built before the GDN changes and before the code review.
ARMS=${ARMS:-"orig base p0 a0 a b ab"}
mkdir -p "$OUT"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
arm_field() { local line; line=$(grep -m1 "^$1|" <<<"$ARMS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
for p in $PROMPTS; do
  for arm in $ARMS; do
    f=$OUT/p$p"__"$arm.txt
    [ -s "$f" ] && continue
    rm -f "/var/tmp/jhan/$NAME-tokens.txt"
    RUN=tok-q35-tp4-1u-p${p}__${arm}__rep1 USERS=1 PROMPT=$p LEN=$LEN TAG=$(arm_field "$arm" 2) NAME=$NAME \
      ARMENV="$(arm_field "$arm" 3)" EXTRA="--temperature 0 --pay-for-determinism --output-token-file /var/tmp/jhan/$NAME-tokens.txt" \
      bash "$EXEC/gdn-20261120/run-one.sh" 2>&1 | grep -a "RUN-" | tail -1
    cp "/var/tmp/jhan/$NAME-tokens.txt" "$f" 2>/dev/null || echo "no token file for $arm p$p"
    sleep 3
  done
done
{
  echo "# generated tokens of each arm against the base arm; $(date -u +%FT%TZ)"
  for p in $PROMPTS; do
    ref=$OUT/p$p"__base.txt"
    for arm in $ARMS; do
      f=$OUT/p$p"__"$arm.txt
      [ -s "$f" ] || { echo "prompt $p arm $arm: no token file"; continue; }
      python3 - "$ref" "$f" "$p" "$arm" <<'PY'
import sys
ref = open(sys.argv[1]).read().split()
got = open(sys.argv[2]).read().split()
n = min(len(ref), len(got))
first = next((i for i in range(n) if ref[i] != got[i]), None)
same = sum(1 for i in range(n) if ref[i] == got[i])
print(f"prompt {sys.argv[3]} arm {sys.argv[4]}: {len(got)} tokens; equal to the base arm at {same} of {n} positions; "
      + ("all equal" if first is None and len(ref) == len(got) else f"first difference at generated token {first}"))
PY
    done
  done
} | tee "$OUT/summary.txt"
