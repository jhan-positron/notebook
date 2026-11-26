#!/usr/bin/env bash
# gdn-20261120 clock probe, part 2. Same method as clock-probe.sh (one of our CPUs, 4 s per loop, frequency sampled
# from the kernel every 0.25 s). Question: does clearing the upper halves of the vector registers before tile
# products keep the core at the higher AMX clock, and what clock does a kernel get that alternates AVX-512 phases
# and tile phases? Modes: tdpz (tiles only, cleared), mixz (4 tile products + 64 FMAs, alternating), mixzp (phases
# of 4,096 tile products and 16,384 FMAs), plus fma and tdp again as references in the same minute.
# Output: exec/results/gdn-20261120/bench/clock-probe2.txt
set -u
CPU=${CPU:-140}
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/gdn-20261120/bench
B=/var/tmp/jhan/gdn-probe
OUT=$RES/clock-probe2.txt
mkdir -p "$RES" "$B"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
pgrep -u "$(id -u)" -f '/gen/runtron ' >/dev/null && { echo "a runtron of ours runs; probe refused"; exit 3; }
g++ -O2 -std=c++17 -march=x86-64-v4 -mamx-tile -mamx-bf16 "$EXEC/gdn-20261120/clock_probe.cpp" -o "$B/clock_probe2" || exit 2
F=/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_cur_freq
echo "# clock probe 2 on $(hostname) cpu $CPU, $(date -u +%FT%TZ)" >"$OUT"
run() {
  local label=$1; shift
  local samples=$B/freq2.$label
  : >"$samples"
  ( while :; do cat "$F" >>"$samples"; sleep 0.25; done ) & local sp=$!
  local line; line=$("$@" 2>&1 | tail -1)
  kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
  local med; med=$(tail -n +5 "$samples" | sort -n | awk '{a[NR]=$1} END {if (NR) print a[int((NR+1)/2)]; else print "na"}')
  echo "$label | freq_khz_median $med (n=$(tail -n +5 "$samples" | wc -l)) | $line" >>"$OUT"
}
for rep in 1 2; do
  for mode in fma tdpz tdp mixz mixzp; do run "$mode-$rep" "$B/clock_probe2" --cpu "$CPU" --only "$mode" --seconds 4; done
done
echo "# end $(date -u +%FT%TZ)" >>"$OUT"
cat "$OUT"
