#!/usr/bin/env bash
# stub runtron (__TAG__): prints the log lines the parsers need, writes tokens / intermediates files
TAG=__TAG__; SHA=__SHA__
model=; out=; inter=; forced=; len=256; users=1; prompt=1024
while [ $# -gt 0 ]; do case $1 in -m) model=$2; shift;; --output-token-file) out=$2; shift;; --intermediates-file) inter=$2; shift;; --force-feed-text-token-file) forced=$2; shift;; -l) len=$2; shift;; -u) users=$2; shift;; --prompt-length) prompt=$2; shift;; --version) echo "Version: 2026.10.18-stub hash: $SHA"; exit 0;; esac; shift; done
sleep 1
echo "[info ] Version: 2026.10.18-${SHA:0:8} hash: $SHA"
if [ "${USE_HW_ATTN:-unset}" = 0 ]; then echo "[info ] HW attention disabled for model '$model': USE_HW_ATTN=0"; else echo "[info ] HW attention enabled for model '$model' (hw_slots 13)"; fi
base=100; [ "$TAG" = g16h ] && [ -z "${TRON_AMX_DISABLE:-}" ] && base=104
for u in $(seq 1 "$users"); do
  echo "Parsing the prompt took $(awk -v p=$prompt 'BEGIN{printf "%.3f", p/830.0}') s at 830.0 tokens/s"
  echo "Generating $((len - 3)) response tokens with $((prompt + len)) context took 2.1 s at $(awk -v b=$base -v r=$RANDOM 'BEGIN{printf "%.2f", b + (r % 100) / 100.0}') average tok/s"
done
cat "/tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/648b68dc-a925-47af-a6eb-b7586de6dc8b/scratchpad/attn-stats-sample.txt"
if [ -n "$out" ]; then
  if [ -n "$forced" ]; then cp "$forced" "$out"
  else
    flip=0; case $model in *Glimmer*) [ "$TAG" = g16h ] && [ -z "${TRON_AMX_DISABLE:-}" ] && flip=1;; esac
    { for i in $(seq 0 $((len - 1))); do v=$((1000 + i)); [ $flip = 1 ] && [ $i -ge 40 ] && v=$((2000 + i)); printf '%d ' $v; done; echo; } >"$out"
  fi
fi
if [ -n "$inter" ]; then
  python3 - "$inter" "$prompt" "$len" "$TAG" <<'PY'
import sys, random
p, P, L, tag = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
random.seed(1)
with open(p, "w") as f:
  for k in range(L):
    N = P - 1 + k
    v = [round(random.uniform(-2, 10), 4) for _ in range(32)]
    if tag == "g16h": v[3] += 0.01
    f.write("  Logits of token %d (32): %s\n" % (N, " ".join("%12.6f" % x for x in v)))
    top = sorted(range(32), key=lambda i: -v[i])[:5]
    f.write("  Top-k Logits of token %d (5): %s\n" % (N, " ".join("%12.6f" % v[i] for i in top)))
    f.write("  Top-k Token IDs for Logits of token %d (5): %s\n" % (N, " ".join(str(i) for i in top)))
PY
fi
exit 0
