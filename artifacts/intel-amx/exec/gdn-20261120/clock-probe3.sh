#!/usr/bin/env bash
# gdn-20261120 clock probe, part 3. Question: do all of our CPUs run AVX-512 work at the same clock?
# Why: in the traces two GDN threads (pinned on CPUs 108 and 109) are 1.65 times faster than the other 14 in prefill.
# Method: the FMA loop of clock_probe (2 s) on one CPU at a time, kernel frequency sampled every 0.25 s.
# Output: exec/results/gdn-20261120/bench/clock-probe3.txt
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/gdn-20261120/bench
B=/var/tmp/jhan/gdn-probe
OUT=$RES/clock-probe3.txt
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
pgrep -u "$(id -u)" -f '/gen/runtron ' >/dev/null && { echo "a runtron of ours runs; probe refused"; exit 3; }
[ -x "$B/clock_probe2" ] || { echo "$B/clock_probe2 missing (run clock-probe2.sh first)"; exit 2; }
echo "# clock probe 3 on $(hostname), $(date -u +%FT%TZ): FMA loop, one CPU at a time" >"$OUT"
for cpu in ${CPUS:-96 97 100 101 102 107 108 109 110 111 113 119 120 125 126 131 132 137 138 140 143 223 224 225 226 227 228 229 230}; do
  F=/sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_cur_freq
  S=$B/freq3.$cpu; : >"$S"
  ( while :; do cat "$F" >>"$S"; sleep 0.25; done ) & sp=$!
  line=$("$B/clock_probe2" --cpu "$cpu" --only fma --seconds 2 2>&1 | tail -1)
  kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
  med=$(tail -n +4 "$S" | sort -n | awk '{a[NR]=$1} END {if (NR) print a[int((NR+1)/2)]; else print "na"}')
  echo "cpu $cpu | freq_khz_median $med | max_khz $(cat /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_max_freq) base_khz $(cat /sys/devices/system/cpu/cpu$cpu/cpufreq/base_frequency 2>/dev/null) | $(echo "$line" | grep -o 'ns_per_fma [0-9.]*')" >>"$OUT"
done
echo "# end $(date -u +%FT%TZ)" >>"$OUT"
cat "$OUT"
