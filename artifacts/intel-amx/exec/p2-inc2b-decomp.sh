#!/usr/bin/env bash
# QUEUE row 15: mirOFF fallback-penalty decomposition (Sol's arm ii).
# Build the layout-only diagnostic binary (3-plane kv_block, canonical kernel,
# NO mirror writes), run the decode suite both kill-switch modes, then perf-stat
# the 1u/8K decode workload on layout-only vs the preserved inc-1b binary.
# Guard: no new run at/after 03:00 UTC (CI prep 03:30; user-confirmed window).
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/p2-inc2b-decomp.txt
LOG=$EXEC/logs/p2-inc2b-decomp.log
MARKER=$EXEC/logs/p2-inc2b-decomp.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p2-inc2b-decomp start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
ci_guard() { t=$(hhmm); [ "$t" -ge 300 ] && [ "$t" -lt 2100 ]; }

cd ~/workspace/tron-amx
[ -f gen/runtron.inc2mir ] || cp gen/runtron gen/runtron.inc2mir
nix develop --command bash -c \
  'cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=OFF -DTRON_AMX_K_MIRROR_LAYOUT_ONLY=ON -DCMAKE_CXX_FLAGS= &&
   cmake --build gen --target runtron -j96' \
  || { echo build-failed >"$MARKER"; exit 1; }
sha256sum gen/runtron gen/runtron.inc1b gen/runtron.inc2mir

RTARGS="stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-p2d --nr_hugepages 128 -o"
{
  echo "# Row-15 decomposition: layout-only binary suite, $(date -u +%FT%TZ)"
  sha256sum gen/runtron
  for mode in "TRON_AMX_DISABLE=1" "TRON_AMX_DISABLE=0"; do
    for w in "2048 256 1" "8192 256 1" "2048 256 8"; do
      set -- $w
      for rep in 1 2 3; do
        if ci_guard; then echo GUARD-STOP; break 3; fi
        echo "### bin=layout-only mode=$mode ctx=$1 len=$2 users=$3 rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 900 ./gen/runtron $RTARGS \
          --prompt-length "$1" -l "$2" -u "$3" 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
  # perf counters on the -7.8% case (1u/8K decode), AVX arm, one rep per binary.
  # Whole-process counters (prefill included) - first-pass signal only.
  for bin in gen/runtron gen/runtron.inc1b; do
    if ci_guard; then echo GUARD-STOP; break; fi
    echo "### perf bin=$bin mode=TRON_AMX_DISABLE=1 ctx=8192 users=1"
    env USE_HW_ATTN=0 TRON_AMX_DISABLE=1 timeout 900 \
      perf stat -e cycles,instructions,LLC-loads,LLC-load-misses,dTLB-loads,dTLB-load-misses,page-faults \
      ./$bin $RTARGS --prompt-length 8192 -l 256 -u 1 2>&1 \
      | grep -E "Parsing the prompt took|average tok/s|cycles|instructions|LLC|dTLB|page-faults|seconds" \
      || echo RUN-FAILED
  done
} >"$OUT"
rm -f /dev/hugepages/amx-p2d* 2>/dev/null
if grep -q "GUARD-STOP\|RUN-FAILED\|build-failed" "$OUT"; then
  echo check-output >"$MARKER"
else
  echo ok >"$MARKER"
fi
echo "=== p2-inc2b-decomp done $(date -u +%FT%TZ) ==="
