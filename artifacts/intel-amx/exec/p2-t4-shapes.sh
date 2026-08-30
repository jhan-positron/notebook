#!/usr/bin/env bash
# T4 gate 5 (shape coverage): llama-3.1-8b-tp2 (head 128 / GQA 4 - the AMX
# fast-path shape) and gpt-oss-20b-tp2 (different shape - checks no-regression
# where the dense fast path may not engage). Same-binary kill-switch A/B on
# the arena binary (validated against clean this morning).
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/t4
OUT=$DIR/t4-shapes.txt
LOG=$EXEC/logs/p2-t4-shapes.log
MARKER=$EXEC/logs/p2-t4-shapes.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== t4-shapes start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
guard() { t=$(hhmm); [ "$t" -ge 245 ] && [ "$t" -lt 930 ]; }

cd ~/workspace/tron-amx
{
  echo "# T4 shape coverage (arena binary, same-binary A/B), $(date -u +%FT%TZ)"
  sha256sum gen/runtron
  for model in ingested-llama-3.1-8b-tp2 ingested-gpt-oss-20b-tp2; do
    RTARGS="stream-generate-text -m $model \
      --instance 0,4 --devices 10:00.0,13:00.0 \
      --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
      --numa 0 --hugepage_file /dev/hugepages/amx-t4s --nr_hugepages 128 -o"
    for mode in "TRON_AMX_DISABLE=1" "TRON_AMX_DISABLE=0"; do
      for w in "8192 1" "2048 8"; do
        set -- $w
        for rep in 1 2; do
          if guard; then echo GUARD-STOP; break 4; fi
          echo "### model=$model mode=$mode ctx=$1 len=256 users=$2 rep=$rep"
          env USE_HW_ATTN=0 $mode timeout 900 ./gen/runtron $RTARGS \
            --prompt-length "$1" -l 256 -u "$2" 2>&1 \
            | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
        done
      done
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-t4s* 2>/dev/null
if grep -qE "GUARD-STOP|RUN-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== t4-shapes done $(date -u +%FT%TZ) ==="
