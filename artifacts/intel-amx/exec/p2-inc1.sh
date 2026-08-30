#!/usr/bin/env bash
# P2 increment 1: build runtron with the AMX QK fast path and A/B it against
# the same binary with TRON_AMX_DISABLE=1 (identical everything else).
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/p2-inc1.txt
LOG=$EXEC/logs/p2-inc1.log
MARKER=$EXEC/logs/p2-inc1.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p2-inc1 start $(date -u +%FT%TZ) ==="
cd ~/workspace/tron-amx
nix develop --command bash -c \
  'cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS= &&
   cmake --build gen --target runtron -j96' \
  || { echo build-failed >"$MARKER"; exit 1; }
sha256sum gen/runtron

RT="./gen/runtron stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-p2 --nr_hugepages 128 -o"
{
  echo "# P2 increment 1 same-binary A/B, $(date -u +%FT%TZ)"
  sha256sum gen/runtron
  for mode in "TRON_AMX_DISABLE=1" "TRON_AMX_DISABLE=0"; do
    for w in "2048 256 1" "8192 256 1" "2048 256 8"; do
      set -- $w
      for rep in 1 2 3; do
        echo "### mode=$mode ctx=$1 len=$2 users=$3 rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 900 $RT --prompt-length "$1" -l "$2" -u "$3" 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-p2* 2>/dev/null
echo "=== p2-inc1 done $(date -u +%FT%TZ) ==="
echo ok >"$MARKER"
