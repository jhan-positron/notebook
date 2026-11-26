#!/usr/bin/env bash
# gdn-impl-20261121, task 4 of the plan in GDN/gdn-amx-design.html (section 6).
# Runs ON delphi-3b35, on ONE of our CPUs (default 142), when no runtron of ours runs. No FPGA card, no root.
#
# Question: how fast are the new AMX attention kernels for 256-wide heads (Part B) against the AVX-512 path
# that tron runs today, per page unit, with the data in cache and from main memory? At which core clock does
# the CPU run each path?
# Words: tron = the inference program; runtron = its command-line tool; AMX = Intel tile-matrix instructions;
# AVX-512 = the vector instructions of today's attention code; page unit = one query token with 4 query heads
# on one 64-token page of one KV head (32 KiB of K and 32 KiB of V).
# Program: task4_attn256.cpp (this folder). Its header describes the two paths, the two memory regimes
# (cache, memory) and the four uses (prefill16, prefill128, prefill1024, decode).
# Pass rule of task 4: the AMX path is 1.5 times faster than the AVX-512 path or more, with the data in cache.
# Clock reading: the program reads the kernel's frequency file of the CPU (scaling_cur_freq, no root) about
# every 0.25 s while one cell runs in a 4 s loop. It drops the first second and prints the median.
# The AVX-512 cells of the clock part run in their own process, which never loads a tile configuration.
# Compiler flags: the optimization and vector flags of tron's build on this server (from
# gen/compile_commands.json of the campaign build tree), plus the two AMX flags that tron gives to its AMX
# kernel file. So the AVX-512 path is compiled as in tron.
# Runs: the timing table 3 times, then two more tables for the record (4 KiB pages instead of huge pages;
# compiler flag -march=native instead of tron's flags), then the clock of every cell 3 times.
# Output: exec/results/gdn-impl-20261121/bench/task4-*.txt
set -u
CPU=${CPU:-142}
TAG=${TAG:-}
EXEC=/home/jhan/workspace/intel-AMX/exec
SRC=$EXEC/gdn-impl-20261121/bench
RES=$EXEC/results/gdn-impl-20261121/bench
B=/var/tmp/jhan/gdn-impl-partb
mkdir -p "$RES" "$B"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
pgrep -u "$(id -u)" -f '/gen/runtron ' >/dev/null && { echo "a runtron of ours runs; benchmark refused"; exit 3; }
bash $EXEC/3b35-inspect-20261112/load-snapshot.sh >"$RES/task4${TAG}-load.txt" 2>&1
TRON_FLAGS="-O3 -fno-omit-frame-pointer -msse4.2 -mavx -mbmi2 -mfma -mavx2 -mclflushopt -ftree-vectorize -funroll-loops -mavx512f -mavx512dq -mavx512bw -mavx512vl -mavx512vbmi2 -mavx512vpopcntdq -mavx512vp2intersect -mavx512bf16"
clang++-19 $TRON_FLAGS -std=c++20 -mamx-tile -mamx-bf16 -o "$B/task4_attn256$TAG" "$SRC/task4_attn256.cpp" || exit 2
clang++-19 -O3 -std=c++20 -march=native -mamx-tile -mamx-bf16 -o "$B/task4_attn256$TAG-native" "$SRC/task4_attn256.cpp" || exit 2
SIB=$(tr ',-' '  ' <"/sys/devices/system/cpu/cpu$CPU/topology/thread_siblings_list" | tr ' ' '\n' | grep -vx "$CPU" | head -1)
# busy share of one CPU since the given /proc/stat line (user nice system idle iowait irq softirq steal)
busy_since() { awk -v c="cpu$1" -v was="$2" 'BEGIN { split(was, w, " ") } $1 == c { b = 0; t = 0; for (i = 2; i <= 9; i++) { d = $i - w[i]; t += d; if (i != 5 && i != 6) b += d } printf "%.1f", t ? 100 * b / t : 0 }' /proc/stat; }
sib_before=$(grep -w "^cpu$SIB" /proc/stat)
for rep in 1 2 3; do
  nice -n5 taskset -c "$CPU" "$B/task4_attn256$TAG" --cpu "$CPU" >"$RES/task4${TAG}-table-cpu$CPU-run$rep.txt" 2>&1
done
nice -n5 taskset -c "$CPU" "$B/task4_attn256$TAG" --cpu "$CPU" --thp 0 >"$RES/task4${TAG}-table-cpu$CPU-nohugepages.txt" 2>&1
nice -n5 taskset -c "$CPU" "$B/task4_attn256$TAG-native" --cpu "$CPU" >"$RES/task4${TAG}-table-cpu$CPU-marchnative.txt" 2>&1
F=/sys/devices/system/cpu/cpu$CPU/cpufreq
OUT=$RES/task4${TAG}-clock-cpu$CPU.txt
{
  echo "# core clock of cpu $CPU on $(hostname) while one cell runs for 4 s, $(date -u +%FT%TZ); kernel $(uname -r)"
  echo "# cpufreq: driver $(cat $F/scaling_driver) governor $(cat $F/scaling_governor) base $(cat $F/base_frequency 2>/dev/null) max $(cat $F/scaling_max_freq) kHz"
  echo "# idle reading before the loops: $(cat $F/scaling_cur_freq) kHz"
} >"$OUT"
USES="prefill16 prefill128 prefill1024 decode"
CELLS=""
for path in avx amx; do for regime in cache memory; do for use in $USES; do CELLS="$CELLS $path.$regime.$use"; done; done; done
CELLS="$CELLS avx_tilecfg.cache.prefill128 avx_tilecfg.cache.decode"
for rep in 1 2 3; do
  for c in $CELLS; do
    echo "rep$rep | $(nice -n5 taskset -c "$CPU" "$B/task4_attn256$TAG" --cpu "$CPU" --only "$c" --seconds 4 2>&1 | tail -1)" >>"$OUT"
  done
done
echo "# hyperthread sibling cpu $SIB was busy $(busy_since "$SIB" "$sib_before") % of the time of this script" >>"$OUT"
echo "# end $(date -u +%FT%TZ)" >>"$OUT"

# Summary: the range over the 3 table runs and over the 3 clock runs.
SUM=$RES/task4${TAG}-summary-cpu$CPU.txt
{
  echo "# task 4 summary, cpu $CPU on $(hostname), $(date -u +%FT%TZ). Ranges are lowest to highest of 3 runs."
  echo "# us = microseconds per page unit (lowest of 7 rounds inside each run). ratio = AVX-512 / AMX."
  echo "# clock = median reading of the core clock in GHz during a 4 s loop of the cell."
  printf '%-7s %-12s | %-15s | %-15s | %-13s | %-13s | %-13s\n' regime use "AVX-512 us" "AMX us" ratio "AVX-512 clock" "AMX clock"
  for regime in cache memory; do
    for use in $USES; do
      awk -v regime="$regime" -v use="$use" '
        function upd(k, v) { if (!(k in lo) || v < lo[k]) lo[k] = v; if (!(k in hi) || v > hi[k]) hi[k] = v }
        FILENAME ~ /-table-/ && $1 == regime && $2 == use { upd("avx", $4); upd("amx", $8); upd("ratio", $12) }
        FILENAME ~ /-clock-/ && $3 == "avx." regime "." use { for (i = 1; i <= NF; i++) if ($i == "freq_khz_median") upd("favx", $(i + 1) / 1e6) }
        FILENAME ~ /-clock-/ && $3 == "amx." regime "." use { for (i = 1; i <= NF; i++) if ($i == "freq_khz_median") upd("famx", $(i + 1) / 1e6) }
        END { printf "%-7s %-12s | %6.3f - %6.3f | %6.3f - %6.3f | %5.2f - %5.2f | %5.2f - %5.2f | %5.2f - %5.2f\n",
              regime, use, lo["avx"], hi["avx"], lo["amx"], hi["amx"], lo["ratio"], hi["ratio"], lo["favx"], hi["favx"], lo["famx"], hi["famx"] }' \
        "$RES/task4${TAG}-table-cpu$CPU-run1.txt" "$RES/task4${TAG}-table-cpu$CPU-run2.txt" "$RES/task4${TAG}-table-cpu$CPU-run3.txt" "$OUT"
    done
  done
  echo
  echo "# AVX-512 path while a tile configuration is loaded (us per page unit and clock, 3 runs of 4 s):"
  grep 'avx_tilecfg' "$OUT"
  echo
  echo "# parts on one page in the L1 cache, run 1:"
  sed -n '/^parts on one page/,$p' "$RES/task4${TAG}-table-cpu$CPU-run1.txt"
  echo
  echo "# self-check of run 1:"
  grep -A3 '^self-check' "$RES/task4${TAG}-table-cpu$CPU-run1.txt"
  echo
  echo "# pass rule: ratio of 1.5 or more with the data in cache (the four cache rows above)."
} >"$SUM"
cat "$SUM"
