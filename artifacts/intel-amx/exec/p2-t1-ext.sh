#!/usr/bin/env bash
# T1 extension (formulation gate 1): two additional qwen prompts at 256 and
# 640 total tokens (with 64 forced steps each), HF fp32 references, both
# kill-switch arms dumped per prompt via t_amx_logit_ab (arena binary's test
# build). TVD scoring happens on alpha afterward.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/t4
OUT=$DIR/t1-ext.txt
LOG=$EXEC/logs/p2-t1-ext.log
MARKER=$EXEC/logs/p2-t1-ext.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== t1-ext start $(date -u +%FT%TZ) ==="
cd ~/workspace/tron-amx
{
  echo "# T1 extension: qwen, prompts 2-3, $(date -u +%FT%TZ)"
  for spec in "t1-prompt2 256" "t1-prompt3 640"; do
    set -- $spec; name=$1; maxtok=$2
    echo "### golden $name maxtok=$maxtok"
    timeout 2400 ./bin/extract_logits \
      --model /opt/positron/weights/huggingface/Qwen/Qwen3-4B-Instruct-2507 \
      --max-layers 36 --text-file $EXEC/$name.txt --max-tokens $maxtok \
      --save-tokens --scratch-dir /scratch/jhan/t1-goldens 2>&1 \
      | grep -E "Tokens shape|Saved" || { echo GOLDEN-FAILED; continue; }
    # newest two files are tokens+logits; identify by size (tokens file is small)
    tok=$(ls -t /scratch/jhan/t1-goldens | head -2 | while read f; do
      [ $(stat -c%s /scratch/jhan/t1-goldens/$f) -lt 100000 ] && echo $f; done | head -1)
    log=$(ls -t /scratch/jhan/t1-goldens | head -2 | grep -v "^$tok$" | head -1)
    echo "tokens=$tok logits=$log"
    for mode in "TRON_AMX_DISABLE=1 off" "TRON_AMX_DISABLE=0 on"; do
      set -- $mode; env_kv=$1; arm=$2
      echo "### dump $name arm=$arm"
      env USE_HW_ATTN=0 $env_kv AMX_MODEL=ingested-qwen-3-4b-instruct-2507 \
        AMX_TOKENS=/scratch/jhan/t1-goldens/$tok \
        AMX_LOGIT_OUT=$DIR/t1ext-$name-$arm.bin \
        timeout 600 ./gen/t_amx_logit_ab 2>&1 | grep -cE "passed" || echo RUN-FAILED
    done
  done
} >"$OUT"
grep -qE "FAILED" "$OUT" && echo check-output >"$MARKER" || echo ok >"$MARKER"
echo "=== t1-ext done $(date -u +%FT%TZ) ==="
