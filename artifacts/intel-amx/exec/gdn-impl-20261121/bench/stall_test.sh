#!/usr/bin/env bash
# gdn-impl-20261121: do AMX bursts on some of OUR CPUs stall another of our CPUs on delphi-3b35?
# A "victim" (stall_probe) spins on one CPU and records every gap in its own execution. "Aggressors"
# (amx_gdn_bench in burst mode) run the GDN kernel in bursts on other CPUs, as tron's 16 GDN threads do:
#   none   = no aggressor;
#   chain  = the AVX-512 chain kernel (Part 0) in bursts;
#   block  = the AMX block kernel (Part A) in bursts.
# Runs ON delphi-3b35 when no runtron of ours runs. No FPGA card, no root.
# Output: exec/results/gdn-impl-20261121/bench/stall-test.txt
set -u
VICTIMS=${VICTIMS:-"130 96 142"}
AGGR=${AGGR:-"110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125"}
GAP=${GAP:-2000}
EXEC=/home/jhan/workspace/intel-AMX/exec
SRC=$EXEC/gdn-impl-20261121/bench
RES=$EXEC/results/gdn-impl-20261121/bench
B=/var/tmp/jhan/gdn-impl-bench
mkdir -p "$RES" "$B"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
pgrep -u "$(id -u)" -f '/gen/runtron ' >/dev/null && { echo "a runtron of ours runs; test refused"; exit 3; }
bash $EXEC/3b35-inspect-20261112/load-snapshot.sh >"$RES/stall-test-load.txt" 2>&1
clang-19 -O2 -o "$B/stall_probe" "$SRC/stall_probe.c" || exit 2
clang++-19 -O3 -std=c++20 -march=native -mamx-tile -mamx-bf16 -o "$B/amx_gdn_bench" "$SRC/amx_gdn_bench.cpp" || exit 2
OUT=$RES/stall-test${TAG:-}.txt
echo "# stall test on $(hostname), $(date -u +%FT%TZ); aggressor CPUs [$AGGR], burst gap $GAP us; victims [$VICTIMS]" >"$OUT"
for mode in none chain block none; do
  pids=""
  if [ "$mode" != none ]; then
    for c in $AGGR; do
      nice -n5 taskset -c "$c" "$B/amx_gdn_bench" --cpu "$c" --only "$mode" --seconds 7 --burst-gap-us "$GAP" >/dev/null 2>&1 & pids="$pids $!"
    done
    sleep 1
  fi
  vp=""
  for v in $VICTIMS; do
    ( taskset -c "$v" "$B/stall_probe" "$v" 4 | sed "s/^/aggressors=$mode | /" >>"$OUT" ) & vp="$vp $!"
  done
  wait $vp
  [ -n "$pids" ] && wait $pids
done
echo "# end $(date -u +%FT%TZ)" >>"$OUT"
cat "$OUT"
