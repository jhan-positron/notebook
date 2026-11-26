#!/usr/bin/env bash
# gdn-20261120 clock probe. Runs ON delphi-3b35, on ONE of our CPUs (default 140), when no runtron of ours runs.
# Question: how fast does a core of our half run under AVX-512 FMA work, under AMX tile products, and under a mix?
# Why: every busy core on this machine reads 2.70 GHz (no flat-frequency service). One earlier probe on a 2.70 GHz
# core of the sister machine saw about 1.93 GHz after tile products. The prediction needs the value on this machine.
# Method: two programs, each loop 4 s, pinned to the CPU; the script samples the kernel's frequency reading
# (/sys/devices/system/cpu/cpuN/cpufreq/scaling_cur_freq, no root needed) every 0.25 s while a loop runs.
#   clock_probe (this folder)      : fma, tdp, mix
#   insn_loops (perf-model-20260903): vdp_tp16, tdp_tp, tdp_lat, tld_l1   (the loops measured on delphi-3bda)
# Cycle counts known from delphi-3bda (same CPU model): TDPBF16PS 16.2 cycles, VDPBF16PS 2.01 cycles.
# So clock under AMX = 16.2 / ns_per_tdp, and clock under AVX-512 bf16 dots = 2.01 / ns_per_vdp.
# Output: exec/results/gdn-20261120/bench/clock-probe.txt
set -u
CPU=${CPU:-140}
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/gdn-20261120/bench
B=/var/tmp/jhan/gdn-probe
OUT=$RES/clock-probe.txt
mkdir -p "$RES" "$B"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
pgrep -u "$(id -u)" -f '/gen/runtron ' >/dev/null && { echo "a runtron of ours runs; probe refused"; exit 3; }
g++ -O2 -std=c++17 -march=x86-64-v4 -mamx-tile -mamx-bf16 "$EXEC/gdn-20261120/clock_probe.cpp" -o "$B/clock_probe" || exit 2
g++ -O3 -std=c++17 -march=x86-64-v4 -mavx512bf16 -mamx-tile -mamx-bf16 "$EXEC/perf-model-20260903/src/insn_loops.cpp" -o "$B/insn_loops" || exit 2
F=/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_cur_freq
{
  echo "# clock probe on $(hostname) cpu $CPU, $(date -u +%FT%TZ); kernel $(uname -r)"
  echo "# cpufreq: driver $(cat /sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_driver) governor $(cat /sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_governor) base $(cat /sys/devices/system/cpu/cpu$CPU/cpufreq/base_frequency 2>/dev/null) max $(cat /sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_max_freq) kHz"
  echo "# idle reading before the loops: $(cat $F) kHz"
} >"$OUT"
run() {  # $1 label, rest = command
  local label=$1; shift
  local samples=$B/freq.$label
  : >"$samples"
  ( while :; do cat "$F" >>"$samples"; sleep 0.25; done ) & local sp=$!
  local line; line=$("$@" 2>&1 | tail -1)
  kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null
  # drop the first 4 samples (1 s: frequency ramp) and report the median of the rest
  local med; med=$(tail -n +5 "$samples" | sort -n | awk '{a[NR]=$1} END {if (NR) print a[int((NR+1)/2)]; else print "na"}')
  echo "$label | freq_khz_median $med (n=$(tail -n +5 "$samples" | wc -l)) | $line" >>"$OUT"
}
for rep in 1 2 3; do
  run "fma-$rep" "$B/clock_probe" --cpu "$CPU" --only fma --seconds 4
  run "tdp-$rep" "$B/clock_probe" --cpu "$CPU" --only tdp --seconds 4
  run "mix-$rep" "$B/clock_probe" --cpu "$CPU" --only mix --seconds 4
done
for loop in vdp_tp16 tdp_tp tdp_lat tld_l1; do
  run "insn-$loop" "$B/insn_loops" --cpu "$CPU" --only "$loop" --seconds 4
done
# the recurrence kernel benchmarks of the tron build, same CPU (3 runs each)
T=/var/tmp/jhan/b35-gdn-base/gen/t_gated_delta_net
if [ -x "$T" ]; then
  for rep in 1 2 3; do
    ( cd /var/tmp/jhan/b35-gdn-base && SYSTEM_CONFIG="--instance 1,2" taskset -c "$CPU" "$T" "GatedDeltaNet recurrence step at the Qwen head geometry" --benchmark-samples 300 2>&1 | grep -A3 "^gdn_recurrence" | tr -s ' ' | tr '\n' ' ' ) | sed "s/^/gdn-recurrence-$rep | /" >>"$OUT"; echo >>"$OUT"
    ( cd /var/tmp/jhan/b35-gdn-base && SYSTEM_CONFIG="--instance 1,2" taskset -c "$CPU" "$T" "GatedDeltaNet convolution step at 8192 channels" --benchmark-samples 300 2>&1 | grep -A2 "^gdn_conv1d" | tr -s ' ' | tr '\n' ' ' ) | sed "s/^/gdn-conv-$rep | /" >>"$OUT"; echo >>"$OUT"
  done
fi
echo "# end $(date -u +%FT%TZ)" >>"$OUT"
cat "$OUT"
