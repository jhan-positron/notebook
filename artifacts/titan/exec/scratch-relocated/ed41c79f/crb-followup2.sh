#!/bin/bash
# After the Asimov validator finishes: cross-chiplet latency and spread-placement write on CRB.
set -u
L=/tmp/claude-0/-home-jhan-workspace-titan-cache-perf/ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e/scratchpad/crb-validate.log
until grep -qE "done rc=|aborting|RUNNING" "$L" 2>/dev/null; do sleep 60; done
H=jhan@192.168.2.45
echo "start $(date -u)"
if ssh -o BatchMode=yes $H 'test -e /tmp/positron-perf.RUNNING'; then echo "RUNNING marker present, aborting"; exit 3; fi
scp -q /home/jhan/workspace/titan/cache-perf/bench/latency.c $H:~/cache-perf/bench/ || exit 2
ssh -o BatchMode=yes $H 'set -e; cd ~/cache-perf/bench; gcc -O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -std=gnu11 -o latency latency.c
T=~/cache-perf/results/followup2-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $T; echo "out $T"
chk() { test -e /tmp/positron-perf.RUNNING && { echo RUNNING; exit 3; }; true; }
echo "## cross-chiplet latency"
for pair in "3 3" "67 3" "3 67" "67 67" "3 64" "119 3"; do set -- $pair; chk
  taskset -c 0-119 ./latency --cpu $1 --build-cpu $2 --fresh 3 --sizes 16M,32M,64M >> $T/cross.csv; done
echo "## spread write/read"
for spec in "16 0-56:8,64-112:8,119" "30 0-62:4,64-119:4" "16 0-60:4" "8 0-56:8" "8 64-112:8"; do set -- $spec; chk
  for k in asmwrite asmread; do taskset -c 0-119 ./bandwidth --threads $1 --cpus "$2" --bytes 256M --kernel $k --min-ms 500 --reps 2 >> $T/spread.csv; done; done
echo "## done"; grep -h "best" $T/cross.csv $T/spread.csv'
RC=$?
mkdir -p /home/jhan/workspace/titan/cache-perf/crb/results && scp -q -r "$H:~/cache-perf/results/followup2-*" /home/jhan/workspace/titan/cache-perf/crb/results/ 2>/dev/null
echo "done rc=$RC $(date -u)"
