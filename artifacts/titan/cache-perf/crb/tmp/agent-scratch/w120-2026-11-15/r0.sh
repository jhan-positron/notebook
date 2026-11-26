#!/usr/bin/env bash
# r0.sh - round 0 of the 120-thread investigation: existing bwx11 kernels at 64+56 threads, 256 MiB, common stop, 6 s.
# Runs on CRB without root. Checks the marker file before and during every process. Uses CPUs 0-119 only.
set -u
M=/tmp/positron-perf.RUNNING
BW=$HOME/cache-perf/bwx11-20261115/bwx11
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
echo "f1215f9ea7b64dd89bad83520e39356dbfdd14934927723ace8024e7d72b00ec  $BW" | sha256sum -c - || exit 2
out=$HOME/cache-perf/results/w120-R0-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
EV='cycles=0x11,instructions=0x08,l1d_refill=0x03,l2d_refill=0x17,ll_miss_rd=0x37,stall_backend_mem=0x4005'
{ date -u; uname -r; cat /proc/loadavg; who; ps -eo user,pcpu,comm --sort=-pcpu | head -6; } > $out/env.txt
run() { tag=$1; shift
  [ -e $M ] && { echo "marker: stop"; exit 3; }
  for i in $(seq 30); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done
  echo "launch $tag utc $(date -u +%T) load $(cat /proc/loadavg) users $(who | wc -l) args $*" >> $out/launches.txt
  taskset -c 0-119 $BW "$@" > $out/$tag.csv 2>> $out/stderr.txt &
  pid=$!
  while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done
  wait $pid; echo "rc $? $tag utc $(date -u +%T)" >> $out/launches.txt
  sleep 15
}
C="--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 6000 --rounds 2 --count --pmu-type 11 --events $EV"
run p1 $C --seq oldread,asmread,read_nop32,read_nop64,read_nop96,read_nop128,read_1pl,read_pf256,read_pf2048,read_sparse,asmread,oldread
run p2 $C --seq oldread,asmread,read_sparse,read_pf2048,read_pf256,read_1pl,read_nop128,read_nop96,read_nop64,read_nop32,asmread,oldread
echo "done $out"; cat $out/launches.txt; wc -c $out/stderr.txt; grep -h '^I,' $out/p1.csv $out/p2.csv
