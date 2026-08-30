#!/usr/bin/env bash
# Slot-1 phase B: quiet-machine measurements (machine handed over by Rhys).
#  1. occupancy capture (provenance)
#  2. microbench re-run on quiet machine (final kernel numbers)
#  3. P0(a) baseline qwen-3-4b-tp2 series, USE_HW_ATTN=0: u x ctx sweep, 3 repeats
#  4. one perfetto-traced run (u8/ctx2048) for attention spans
# Guard: stop by 02:30 UTC (before the 02:45 stop-timer / ~04:00 nightly).
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1
LOG=$EXEC/logs/p0-slot1-measure.log
MARKER=$EXEC/logs/p0-slot1-measure.done
mkdir -p "$OUT" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== slot1 measure start $(date -u +%FT%TZ) ==="

guard() {
  local hm=$(date -u +%H%M)
  if [ "$hm" -ge 0230 ] && [ "$hm" -lt 0500 ]; then
    echo "guard: nightly window reached at $hm UTC"; echo guard-stop >"$MARKER"; exit 0
  fi
}

echo "--- occupancy ---" | tee "$OUT/occupancy.txt"
{ date -u +%FT%TZ; uptime; pgrep -cx rinzler || echo "rinzler none";
  grep -E "HugePages_Total|HugePages_Free" /proc/meminfo; } >>"$OUT/occupancy.txt"

guard
echo "--- microbench re-run (quiet) ---"
cd ~/workspace/tron-pr2934-reconciled
BIN=./gen-delphi/amx_microbench
{
  echo "# quiet-machine re-run $(date -u +%FT%TZ), cpu 96"
  for hd in 128 64; do
    for v in dotter avx dispatch; do
      for M in 1 2 3 4 6 8 12 16; do
        taskset -c 96 $BIN "$M" 200000 "$v" "$hd" || echo "RUN-FAILED $M $v $hd"
      done
    done
  done
  for v in v1 v2; do for M in 1 4 8 16; do
    taskset -c 96 $BIN "$M" 200000 "$v" 128 || echo "RUN-FAILED $M $v"
  done; done
} >"$OUT/microbench-quiet.txt"

guard
echo "--- qwen baseline series ---"
cd ~/workspace/tron-amx
RT="./gen/runtron stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-baseline --nr_hugepages 128 -o"
for u in 1 4 8; do
  for ctx in 256 2048 8192; do
    for rep in 1 2 3; do
      guard
      echo "### run u=$u ctx=$ctx rep=$rep $(date -u +%FT%TZ)"
      USE_HW_ATTN=0 timeout 900 env USE_HW_ATTN=0 $RT \
        --prompt-length "$ctx" -l 256 -u "$u" 2>&1 \
        | grep -E "Parsing the prompt|Generating .* response tokens|TTFT|Throughput" \
        >>"$OUT/qwen-baseline-swattn.txt" || echo "RUN-FAILED u=$u ctx=$ctx rep=$rep" >>"$OUT/qwen-baseline-swattn.txt"
    done
  done
done

guard
echo "--- perfetto traced run (u8 ctx2048) ---"
USE_HW_ATTN=0 timeout 900 env USE_HW_ATTN=0 $RT \
  --prompt-length 2048 -l 256 -u 8 --trace-gen "$OUT/qwen-u8-ctx2048-swattn.perfetto-trace" 2>&1 \
  | grep -E "Parsing|Generating|TTFT" >>"$OUT/qwen-baseline-swattn.txt" \
  || echo "TRACE-RUN-FAILED" >>"$OUT/qwen-baseline-swattn.txt"

rm -f /dev/hugepages/amx-baseline* 2>/dev/null
echo "=== slot1 measure done $(date -u +%FT%TZ) ==="
echo ok >"$MARKER"
