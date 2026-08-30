#!/usr/bin/env bash
# Increment 3: parallel-arena mirror. Build TRON_AMX_K_MIRROR=ON with the new
# arena design, run the A7 tests, then the same-binary A/B suite. The two
# predictions to check against the in-block mirror (runtron.inc2mir):
#   (a) kill-switch arm ~= clean (fallback penalty gone),
#   (b) AMX arm gains most of the ~9% layout tax back on top of inc-2.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/t4
OUT=$DIR/p2-inc3-arena.txt
LOG=$EXEC/logs/p2-inc3-arena.log
MARKER=$EXEC/logs/p2-inc3-arena.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== inc3-arena start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
guard() { t=$(hhmm); [ "$t" -ge 245 ] && [ "$t" -lt 930 ]; }

cd ~/workspace/tron-amx
nix develop --command bash -c \
  'cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON -DCMAKE_CXX_FLAGS= &&
   cmake --build gen --target runtron t_amx_mirror t_llama_unit -j96' \
  || { echo build-failed >"$MARKER"; exit 1; }
cp gen/runtron gen/runtron.inc3arena
sha256sum gen/runtron.inc3arena

{
  echo "# Increment 3 (parallel-arena mirror): tests + same-binary A/B, $(date -u +%FT%TZ)"
  sha256sum gen/runtron
  echo "### tests"
  ./gen/t_amx_mirror 2>&1 | tail -3
  ./gen/t_llama_unit "fixed KV layout addresses each slot geometry" 2>&1 | tail -3
  RTARGS="stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
    --instance 0,4 --devices 10:00.0,13:00.0 \
    --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
    --numa 0 --hugepage_file /dev/hugepages/amx-i3 --nr_hugepages 128 -o"
  for mode in "TRON_AMX_DISABLE=1" "TRON_AMX_DISABLE=0"; do
    for w in "2048 1" "8192 1" "2048 8" "8192 8"; do
      set -- $w
      for rep in 1 2 3; do
        if guard; then echo GUARD-STOP; break 3; fi
        echo "### mode=$mode ctx=$1 len=256 users=$2 rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 900 ./gen/runtron $RTARGS \
          --prompt-length "$1" -l 256 -u "$2" 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-i3* 2>/dev/null
if grep -qE "GUARD-STOP|RUN-FAILED|FAILED" "$OUT"; then
  echo check-output >"$MARKER"
else
  echo ok >"$MARKER"
fi
echo "=== inc3-arena done $(date -u +%FT%TZ) ==="
