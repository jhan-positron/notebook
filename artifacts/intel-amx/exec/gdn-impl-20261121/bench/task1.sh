#!/usr/bin/env bash
# gdn-impl-20261121, task 1 of the plan in GDN/gdn-amx-design.html (section 6).
# Runs ON delphi-3b35, on OUR CPUs only (96-143), when no runtron of ours runs. No FPGA card, no root.
#
# Question: how much faster is the column-half loop order of the GDN recurrence than today's token loop,
# on this CPU, at the working-copy size of tron's prefill (128 KiB = 2 value heads)?
# Words: GDN = GatedDeltaNet, the recurrent layer type of Qwen3.5 4B; recurrence = the per-token read and
# rewrite of the 128 x 128 FP32 state; column-half order = all tokens of a chain on 64 value columns, then on
# the other 64 (the "slice replay, blocked layout" rows of the benchmark).
# Program: bench_gdn_task1.c = design-checks/verify-cost/bench_gdn.c with the host line read from the machine.
# Runs: 3 single runs on one CPU, then 16 copies at once on 16 CPUs (tron runs GDN on 16 threads).
# The kernel's frequency reading of each CPU is sampled while the copies run.
# Output: exec/results/gdn-impl-20261121/bench/task1-*.txt
set -u
CPU=${CPU:-140}
CPUS16=${CPUS16:-"110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125"}
EXEC=/home/jhan/workspace/intel-AMX/exec
SRC=$EXEC/gdn-impl-20261121/bench/bench_gdn_task1.c
RES=$EXEC/results/gdn-impl-20261121/bench
B=/var/tmp/jhan/gdn-impl-bench
mkdir -p "$RES" "$B"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
pgrep -u "$(id -u)" -f '/gen/runtron ' >/dev/null && { echo "a runtron of ours runs; benchmark refused"; exit 3; }
bash $EXEC/3b35-inspect-20261112/load-snapshot.sh >"$RES/task1-load.txt" 2>&1
clang-19 -O3 -march=native -o "$B/bench_gdn_task1" "$SRC" -lm || exit 2
freq() { cat "/sys/devices/system/cpu/cpu$1/cpufreq/scaling_cur_freq"; }
for rep in 1 2 3; do
  out=$RES/task1-single-cpu$CPU-run$rep.txt
  ( while :; do freq "$CPU"; sleep 0.25; done ) >"$B/freq.single" & sp=$!
  nice -n5 taskset -c "$CPU" "$B/bench_gdn_task1" "$CPU" 1 >"$out" 2>&1
  kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
  echo "cpufreq reading of cpu $CPU while the run was in progress, kHz: median $(sort -n "$B/freq.single" | awk '{a[NR]=$1} END {print a[int((NR+1)/2)]}') min $(sort -n "$B/freq.single" | head -1) max $(sort -n "$B/freq.single" | tail -1) (n=$(wc -l <"$B/freq.single"))" >>"$out"
done
# 16 copies at once
( while :; do for c in $CPUS16; do printf '%s %s\n' "$c" "$(freq "$c")"; done; sleep 0.5; done ) >"$B/freq.multi" & sp=$!
pids=""
for c in $CPUS16; do
  nice -n5 taskset -c "$c" "$B/bench_gdn_task1" "$c" 1 >"$RES/task1-16copies-cpu$c.txt" 2>&1 & pids="$pids $!"
done
wait $pids
kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
for c in $CPUS16; do
  echo "cpufreq reading of cpu $c while the 16 copies ran, kHz: median $(awk -v c="$c" '$1==c {print $2}' "$B/freq.multi" | sort -n | awk '{a[NR]=$1} END {print a[int((NR+1)/2)]}')" >>"$RES/task1-16copies-cpu$c.txt"
done
echo "task1 done $(date -u +%FT%TZ)"
