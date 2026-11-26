#!/usr/bin/env bash
# gdn-impl-20261121, task 3 of the plan in GDN/gdn-amx-design.html (section 6).
# Runs ON delphi-3b35, on OUR CPUs only, when no runtron of ours runs. No FPGA card, no root.
#
# Question: how fast is the stand-alone AMX block kernel of the GDN recurrence (Part A), how close are its
# results to today's kernel, and at which core clock does the CPU run it?
# Program: amx_gdn_bench.cpp + gdn_kernels.hpp (this folder). The three kernels are
#   token = today's kernel, chain = Part 0 (same bits), block = Part A (AMX tile products, 32 tokens at once).
# Clock reading: the kernel's frequency file of the CPU (scaling_cur_freq, no root) is sampled every 0.25 s
# while one kernel runs in a 4 s loop. The first second is dropped. The median is reported.
# Output: exec/results/gdn-impl-20261121/bench/task3-*.txt
set -u
CPU=${CPU:-140}
CPUS16=${CPUS16:-"110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125"}
TAG=${TAG:-}
EXEC=/home/jhan/workspace/intel-AMX/exec
SRC=$EXEC/gdn-impl-20261121/bench
RES=$EXEC/results/gdn-impl-20261121/bench
B=/var/tmp/jhan/gdn-impl-bench
mkdir -p "$RES" "$B"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
pgrep -u "$(id -u)" -f '/gen/runtron ' >/dev/null && { echo "a runtron of ours runs; benchmark refused"; exit 3; }
bash $EXEC/3b35-inspect-20261112/load-snapshot.sh >"$RES/task3${TAG}-load.txt" 2>&1
clang++-19 -O3 -std=c++20 -march=native -mamx-tile -mamx-bf16 ${DEFS:-} -o "$B/amx_gdn_bench$TAG" "$SRC/amx_gdn_bench.cpp" || exit 2
F=/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_cur_freq
for rep in 1 2 3; do
  nice -n5 taskset -c "$CPU" "$B/amx_gdn_bench$TAG" --cpu "$CPU" >"$RES/task3${TAG}-table-cpu$CPU-run$rep.txt" 2>&1
done
OUT=$RES/task3${TAG}-clock-cpu$CPU.txt
echo "# core clock of cpu $CPU on $(hostname) while one kernel runs, $(date -u +%FT%TZ)" >"$OUT"
for rep in 1 2 3; do
  for k in token chain chain_tiles block block_bracket; do
    samples=$B/freq.$k
    : >"$samples"
    ( while :; do cat "$F" >>"$samples"; sleep 0.25; done ) & sp=$!
    line=$(nice -n5 taskset -c "$CPU" "$B/amx_gdn_bench$TAG" --cpu "$CPU" --only "$k" --seconds 4 2>&1 | tail -1)
    kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
    med=$(tail -n +5 "$samples" | sort -n | awk '{a[NR]=$1} END {if (NR) print a[int((NR+1)/2)]; else print "na"}')
    echo "$k-$rep | freq_khz_median $med (n=$(tail -n +5 "$samples" | wc -l)) | $line" >>"$OUT"
  done
done
# 16 copies of the block kernel at once (tron runs GDN on 16 threads), 4 s
( while :; do for c in $CPUS16; do printf '%s %s\n' "$c" "$(cat /sys/devices/system/cpu/cpu$c/cpufreq/scaling_cur_freq)"; done; sleep 0.5; done ) >"$B/freq.multi" & sp=$!
pids=""
for c in $CPUS16; do
  nice -n5 taskset -c "$c" "$B/amx_gdn_bench$TAG" --cpu "$c" --only block --seconds 4 >"$B/multi.$c" 2>&1 & pids="$pids $!"
done
wait $pids
kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
for c in $CPUS16; do
  echo "block-16copies | freq_khz_median $(awk -v c="$c" '$1==c {print $2}' "$B/freq.multi" | tail -n +3 | sort -n | awk '{a[NR]=$1} END {print a[int((NR+1)/2)]}') | $(tail -1 "$B/multi.$c")" >>"$OUT"
done
echo "# end $(date -u +%FT%TZ)" >>"$OUT"
cat "$OUT"
