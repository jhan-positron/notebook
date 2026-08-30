#!/usr/bin/env bash
# P1: measure achievable query-width sharing on real qwen workloads.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/p1-sharing.txt
LOG=$EXEC/logs/p1-counters.log
MARKER=$EXEC/logs/p1-counters.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p1 start $(date -u +%FT%TZ) ==="
cd ~/workspace/tron-amx
nix develop --command bash -c \
  'cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DCMAKE_CXX_FLAGS=-DTRON_P1_COUNTERS=1 &&
   cmake --build gen --target runtron -j96' \
  || { echo build-failed >"$MARKER"; exit 1; }

RT="./gen/runtron stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-p1 --nr_hugepages 128 -o"
{
  echo "# P1 sharing counters, $(date -u +%FT%TZ)"
  echo "## workload A: prefill-heavy (8u, 2048 prompt, 2 gen)"
  USE_HW_ATTN=0 timeout 600 env USE_HW_ATTN=0 $RT --prompt-length 2048 -l 2 -u 8 2>&1 | grep '^\[P1\]'
  echo "## workload B: decode-heavy private (8u, 64 prompt, 512 gen)"
  USE_HW_ATTN=0 timeout 600 env USE_HW_ATTN=0 $RT --prompt-length 64 -l 512 -u 8 2>&1 | grep '^\[P1\]'
  echo "## workload C: decode with shared system prompt (8u, shared 1024 + 64 prompt, 256 gen)"
  USE_HW_ATTN=0 timeout 600 env USE_HW_ATTN=0 $RT --shared-system-prompt-length 1024 --prompt-length 64 -l 256 -u 8 2>&1 | grep '^\[P1\]'
} >"$OUT"
rm -f /dev/hugepages/amx-p1* 2>/dev/null
echo "=== p1 done $(date -u +%FT%TZ) ==="
echo ok >"$MARKER"
