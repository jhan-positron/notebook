#!/usr/bin/env bash
# gdn-impl-20261121: the three GDN recurrence kernels in bursts, as a tron prefill pass runs them.
# Runs ON delphi-3b35 on one of OUR CPUs (default 140), when no runtron of ours runs. No FPGA card, no root.
# One burst = the kernel on one chain of 128 tokens (2 value heads). Between bursts the CPU runs scalar work
# for GAP microseconds. The program reports the kernel time inside the bursts and the core clock of the scalar
# work (from the known 3-cycle latency of a multiply), for its first quarter and for the rest.
# Kernels: token = today's kernel, chain = Part 0, block = Part A (AMX; tiles configured around each chain).
# Output: exec/results/gdn-impl-20261121/bench/task3-burst-cpu$CPU.txt
set -u
CPU=${CPU:-140}
EXEC=/home/jhan/workspace/intel-AMX/exec
SRC=$EXEC/gdn-impl-20261121/bench
RES=$EXEC/results/gdn-impl-20261121/bench
B=/var/tmp/jhan/gdn-impl-bench
mkdir -p "$RES" "$B"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
pgrep -u "$(id -u)" -f '/gen/runtron ' >/dev/null && { echo "a runtron of ours runs; benchmark refused"; exit 3; }
bash $EXEC/3b35-inspect-20261112/load-snapshot.sh >"$RES/task3-burst-load.txt" 2>&1
clang++-19 -O3 -std=c++20 -march=native -mamx-tile -mamx-bf16 -o "$B/amx_gdn_bench" "$SRC/amx_gdn_bench.cpp" || exit 2
OUT=$RES/task3-burst-cpu$CPU.txt
echo "# kernels in bursts on cpu $CPU of $(hostname), $(date -u +%FT%TZ)" >"$OUT"
for gap in 0 200 1000 2000 5000 20000; do
  for k in token chain block; do
    nice -n5 taskset -c "$CPU" "$B/amx_gdn_bench" --cpu "$CPU" --only "$k" --seconds 3 --burst-gap-us "$gap" 2>&1 | tail -1 >>"$OUT"
  done
done
echo "# end $(date -u +%FT%TZ)" >>"$OUT"
cat "$OUT"
