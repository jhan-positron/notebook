#!/usr/bin/env bash
# P0(b) fused-path sweep: our AMX formulation vs AVX baseline, widths x residency.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/fused-sweep-v2.txt
LOG=$EXEC/logs/p0-fused-sweep.log
MARKER=$EXEC/logs/p0-fused-sweep.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== fused sweep start $(date -u +%FT%TZ) ==="
cd ~/workspace/tron-amx
g++ -O3 -std=c++17 -mavx512f -mavx512bw -mavx512vl -mavx512dq -mavx512bf16 \
    -mavx2 -mfma -mamx-tile -mamx-bf16 -o /tmp/amx_fused_bench \
    src/amx_fused_bench.cpp || { echo build-failed >"$MARKER"; exit 1; }
{
  echo "# fused-page sweep $(date -u +%FT%TZ), cpu 96, binary sha256:"
  sha256sum /tmp/amx_fused_bench
  for pages in 1 512 16384; do
    case $pages in
      1) iters=200000 ;; 512) iters=800 ;; 16384) iters=25 ;;
    esac
    for v in avx amx44 amx62 amxqk; do
      for nq in 1 2 3 4 6 8 12 16; do
        taskset -c 96 /tmp/amx_fused_bench "$nq" "$iters" "$v" "$pages" \
          || echo "RUN-FAILED nq=$nq v=$v pages=$pages"
      done
    done
  done
} >"$OUT"
echo "=== fused sweep done $(date -u +%FT%TZ) ==="
echo ok >"$MARKER"
