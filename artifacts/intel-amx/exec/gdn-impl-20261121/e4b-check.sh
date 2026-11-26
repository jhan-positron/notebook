#!/usr/bin/env bash
# gdn-impl-20261121, E4B check: does Gemma 4 E4B take the 256-wide AMX attention kernels of Part B, and does it
# generate the same tokens with AMX on and with AMX off?
# Runs ON delphi-3b35, on OUR half (SYSTEM_CONFIG="--instance 1,2"), through exec/gdn-20261120/run-one.sh. That
# script takes the load snapshot before every run and refuses a run when our half is busy.
#
# Why: Part B selects an attention layer by its head shape (head size 256, 4 query heads per KV head), not by its
# model. Gemma 4 E4B has that shape in its 35 sliding-window layers (8 query heads, 2 KV heads, head size 256).
# The campaign of gdn-impl-20261121 built and ran Qwen3.5 4B only.
# How: one user, the fixed prompt text that runtron ships, temperature 0 (the sampler takes the token with the
# highest score), --pay-for-determinism (fixed split of the worker threads), --output-token-file, and
# TRON_ATTN_STATS=1 (the attention counters, which say per layer which kernel read the K tokens).
# Words: tron = the inference program; runtron = its command-line tool; AMX = Intel tile-matrix instructions;
# Part B = the AMX attention kernels for 256-wide heads; TRON_AMX_DISABLE=1 = the switch that turns AMX off at run
# time; arm = one set of switches.
# Usage (on 3b35): [TAG=e4b] [MODELS='<slug> ...'] [PROMPTS='1024'] [LEN=128] [ARMS='on off on2'] bash e4b-check.sh
# Output: exec/results/gdn-e4b-20261122/{rt,load,tokens}/ and tokens/summary.txt; marker e4b-check.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=gdn-e4b-20261122
RES=$EXEC/results/$NAME
OUT=$RES/tokens
TAG=${TAG:-e4b}
MODELS=${MODELS:-"ingested-gemma-4-e4b-it-tp4 ingested-gemma-4-e4b-it-permuted"}
PROMPTS=${PROMPTS:-"1024"}
LEN=${LEN:-128}
# on2 = a second run of the arm on (are the tokens of a run repeatable?).
ARMS_ALL=$'on|TRON_ATTN_STATS=1
off|TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1
on2|TRON_ATTN_STATS=1'
ARMS=${ARMS:-"on off on2"}
TOK=/var/tmp/jhan/$NAME-tokens.txt
mkdir -p "$OUT"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
rm -f "$RES/e4b-check.done"
arm_field() { local line; line=$(grep -m1 "^$1|" <<<"$ARMS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
for m in $MODELS; do
  for p in $PROMPTS; do
    for arm in $ARMS; do
      f=$OUT/${m}__p${p}__${arm}.txt
      [ -s "$f" ] && continue
      rm -f "$TOK"
      RUN=tok-${m}-1u-p${p}__${arm}__rep1 MODEL=$m USERS=1 PROMPT=$p LEN=$LEN TAG=$TAG NAME=$NAME \
        ARMENV="$(arm_field "$arm" 2)" EXTRA="--temperature 0 --pay-for-determinism --output-token-file $TOK" \
        bash "$EXEC/gdn-20261120/run-one.sh" 2>&1 | grep -a "RUN-" | tail -1
      cp "$TOK" "$f" 2>/dev/null || echo "no token file for $m prompt $p arm $arm"
      sleep 3
    done
  done
done
python3 - "$RES" "$MODELS" "$PROMPTS" "$ARMS" <<'PY' | tee "$OUT/summary.txt"
import datetime, json, os, re, sys

res, models, prompts, arms = sys.argv[1], sys.argv[2].split(), sys.argv[3].split(), sys.argv[4].split()
print("# Gemma 4 E4B at the Part B head: attention kernel per layer and generated tokens;",
      datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ"))
LAYER = re.compile(r"(\d+)=(\d+)/(\d+)/(\d+)")
for m in models:
    for p in prompts:
        ref_path = f"{res}/tokens/{m}__p{p}__on.txt"
        ref = open(ref_path).read().split() if os.path.exists(ref_path) else None
        for arm in arms:
            name = f"{m} prompt {p} arm {arm}"
            log = f"{res}/rt/tok-{m}-1u-p{p}__{arm}__rep1.log"
            if not os.path.exists(log):
                print(f"{name}: no run log (the run failed or was refused)")
                continue
            lines = [l for l in open(log, errors="replace") if l.startswith("[attn-stats]")]
            head = next((l for l in lines if "] model " in l), None)
            if head:
                facts = json.loads(head[head.index("{"):])
                print(f"{name}: amx_compiled={facts['amx_compiled']} amx_available={facts['amx_available']} "
                      f"header head_size={facts['head_size']} kv_mul={facts['kv_mul']} n_layers={facts['n_layers']}")
            # K tokens read per layer by the AMX kernels, by the AVX-512 kernels and by the FPGA cards, summed over
            # the two phases that the counters print.
            per = {}
            for l in lines:
                if "k_tokens per layer" not in l:
                    continue
                for layer, amx, avx, fpga in LAYER.findall(l.split("):", 1)[1]):
                    a = per.setdefault(int(layer), [0, 0, 0])
                    a[0] += int(amx); a[1] += int(avx); a[2] += int(fpga)
            amx_layers = sorted(k for k, v in per.items() if v[0] > 0)
            avx_only = sorted(k for k, v in per.items() if v[0] == 0 and v[1] > 0)
            fpga_layers = sorted(k for k, v in per.items() if v[2] > 0)
            print(f"{name}: layers with AMX K tokens = {len(amx_layers)} {amx_layers}")
            print(f"{name}: layers with AVX-512 K tokens only = {len(avx_only)} {avx_only}")
            print(f"{name}: layers with FPGA K tokens = {len(fpga_layers)} {fpga_layers}")
            print(f"{name}: K tokens amx/avx/fpga = {sum(v[0] for v in per.values())}/"
                  f"{sum(v[1] for v in per.values())}/{sum(v[2] for v in per.values())}")
            tps = [l.strip()[-160:] for l in open(log, errors="replace") if "average tok/s" in l or "s TTFT and" in l]
            for t in tps[-2:]:
                print(f"{name}: {t}")
            tok_path = f"{res}/tokens/{m}__p{p}__{arm}.txt"
            if not os.path.exists(tok_path) or ref is None:
                print(f"{name}: no token file")
                continue
            got = open(tok_path).read().split()
            n = min(len(ref), len(got))
            first = next((i for i in range(n) if ref[i] != got[i]), None)
            same = sum(1 for i in range(n) if ref[i] == got[i])
            verdict = ("all equal" if first is None and len(ref) == len(got)
                       else f"first difference at generated token {first}")
            print(f"{name}: {len(got)} tokens; equal to the arm on at {same} of {n} positions; {verdict}")
PY
echo "done $(date -u +%FT%TZ)" >"$RES/e4b-check.done"
