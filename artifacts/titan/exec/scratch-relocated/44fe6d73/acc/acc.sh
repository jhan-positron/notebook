#!/usr/bin/env bash
# Stage 1 items 1 and 4 on CRB: five short processes with --trace. Rates of a trace run are not used.
set -u
MK=/tmp/positron-perf.RUNNING
D=~/cache-perf/bwx8-20261114; R=~/cache-perf/results/bwx8-accept-s1-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$R" && cd "$D" || exit 2
cat > "$R/accS3.plan" < accS3.plan; cp accC.plan "$R/"
one() { n=$1; shift
  [ -e $MK ] && { echo "RUNNING file present: stop" >&2; exit 3; }
  echo "-- $n load $(cat /proc/loadavg) who $(who | wc -l) utc $(date -u +%T) args $*" >> "$R/launches.txt"
  taskset -c 0-119 ./bwx8 "$@" > "$R/$n.csv" 2> "$R/$n.err"; echo "-- $n status $?" >> "$R/launches.txt"; }
one s2-asmread --trial --cpus 2 --bytes 8388608 --plan sched/s1/S2/0018.plan --trace
one s2-read    --trial --cpus 2 --bytes 8388608 --plan sched/s1/S2/0019.plan --trace
one s2-oldread --trial --cpus 41 --bytes 8388608 --plan sched/s1/S2/0020.plan --trace
one s3         --trial --cpus 2 --bytes 8388608 --plan accS3.plan --trace
one cnt        --trial --cpus 41 --bytes 8388608 --plan accC.plan --trace --pmu-type 11 --events cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17
cat "$R/launches.txt" >&2
tar cf - -C ~/cache-perf/results "$(basename "$R")"
