#!/usr/bin/env bash
set -u
MK=/tmp/positron-perf.RUNNING
D=~/cache-perf/bwx8-20261114; R=~/cache-perf/results/bwx8-accept3-s1-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$R" && cd "$D" || exit 2
cp accC.plan "$R/"
one() { n=$1; shift
  [ -e $MK ] && { echo "RUNNING file present: stop" >&2; exit 3; }
  echo "-- $n load $(cat /proc/loadavg) who $(who | wc -l) utc $(date -u +%T) args $*" >> "$R/launches.txt"
  taskset -c 0-119 ./bwx8 "$@" > "$R/$n.csv" 2> "$R/$n.err"; echo "-- $n status $?" >> "$R/launches.txt"; }
one cnt        --trial --cpus 41 --bytes 8388608 --plan accC.plan --trace --pmu-type 11 --events cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17
one cnt-notrace --trial --cpus 41 --bytes 8388608 --plan accC.plan --pmu-type 11 --events cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17
cat "$R/launches.txt" "$R"/*.err >&2
