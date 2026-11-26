#!/usr/bin/env bash
# run_chip.sh - many cores, ASCT read loop, 256 MiB per thread (the layout of the 2026-11-15 work:
# 64 threads on CPUs 0-63 + 56 threads on CPUs 64-119). No root. Never CPUs 120-127.
# Steps (STEPS selects): BASE  64+56, 0 injected NOPs, 6 processes
#                        DEF   64+56, 0 injected NOPs, ASCT's default duration 0.25 s, 3 processes
#                        NOPS  64+56, injected NOPs (--bw-fine-delay) 1..180, 2 processes each
#                        LAY   layouts 64+0, 0+56, 56+56 at 0 and 20 injected NOPs, 2 processes each
#                        MIX   64+56, the four read-write traffic types of ASCT's peak-bandwidth, 2 processes each
#                        CNT   ASCT's probe variant with counters: 64+56 at 0 and 20 NOPs, 64+0 at 0 NOPs
# Before every process: marker and STOP check, wait until at most 2 tasks are runnable, then 5 s.
set -u
M=/tmp/positron-perf.RUNNING; STOP=$HOME/cache-perf/STOP
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
W=$HOME/cache-perf/asct-20261116
PLAIN=$HOME/asct/asct_venv/bin/loaded-latency-asct-sve.bin
PROBE=$W/loaded-latency-asct-probe-sve.bin
STEPS=${STEPS:-BASE DEF NOPS LAY MIX CNT}; DUR=${DUR:-2}; BYTES=268435456
NUMA=$(command -v numactl || ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null)
out=$HOME/cache-perf/results/asct-chip-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
{ echo "utc $(date -u +%FT%TZ)"; uname -r; cat /proc/loadavg; who; ps -eo user,pcpu,comm --sort=-pcpu | head -6
  sha256sum $PLAIN $PROBE; echo "STEPS $STEPS DUR $DUR BYTES $BYTES numactl ${NUMA:-none}"; } > $out/env.txt 2>&1
cp $W/events.codes $out/
cpuflags() { # cpuflags LAYOUT -> the --bw-cpu options
  case $1 in
    6456) r="0-119";; 6400) r="0-63";; 0056) r="64-119";; 5656) r="0-55 64-119";; *) echo "bad layout $1" >&2; exit 2;;
  esac
  for part in $r; do for c in $(seq ${part%-*} ${part#*-}); do printf -- '--bw-cpu %d ' $c; done; done
}
n=0
one() { # one TAG BINARY LAYOUT NOPS DURATION [TRAFFIC]   traffic: ASCT's --bw-write value, default 0 = all reads
  [ -e $M ] && { echo "marker: stop after $n processes"; exit 3; }
  [ -e $STOP ] && { echo "STOP file: stop after $n processes"; exit 4; }
  # ASCT's Python layer creates the counter folder before the run; two threads that create it at the same time fail
  [ -n "${DIETPERF_OUTDIR:-}" ] && mkdir -p "$DIETPERF_OUTDIR"
  # the name rq: the callers use r as their loop variable (r here overwrote 8 file names in the run of 23:19 UTC)
  for i in $(seq 60); do rq=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); [ "$rq" -le 2 ] && break; sleep 1; done
  sleep 5
  echo "launch $1 epoch $(date +%s.%N) load $(cat /proc/loadavg) users $(who | wc -l)" >> $out/launches.txt
  taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $2 --duration $5 --delay-seconds 0 $(cpuflags $3) --bw-buflen $BYTES \
      --bw-fine-delay $4 --bw-write=${6:-0} --bw-cacheline-bytes 64 > $out/$1.out 2>&1 < /dev/null &
  pid=$!
  while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed $1"; exit 3; }; sleep 1; done
  wait $pid; echo "rc $? $1 epoch $(date +%s.%N)" >> $out/launches.txt; n=$((n+1))
}
has() { case " $STEPS " in *" $1 "*) return 0;; esac; return 1; }
if has BASE; then for r in 1 2 3 4 5 6; do one w.6456.n0.d$DUR.$r $PLAIN 6456 0 $DUR; done; fi
if has DEF; then for r in 1 2 3; do one w.6456.n0.d0.25.$r $PLAIN 6456 0 0.25; done; fi
if has NOPS; then
  NL="1 2 3 4 6 8 10 15 20 30 40 50 70 100 180"
  for nn in $NL; do one w.6456.n$nn.d$DUR.1 $PLAIN 6456 $nn $DUR; done
  for nn in $(echo $NL | tr ' ' '\n' | tac); do one w.6456.n$nn.d$DUR.2 $PLAIN 6456 $nn $DUR; done
fi
if has LAY; then
  for r in 1 2; do for lay in 6400 0056 5656; do for nn in 0 20; do one w.$lay.n$nn.d$DUR.$r $PLAIN $lay $nn $DUR; done; done; done
fi
if has MIX; then  # the other four traffic types of ASCT's peak-bandwidth benchmark (2: 3:1, 3: 2:1, 4: 1:1, 5: 2:1 non-temporal)
  for r in 1 2; do for t in 2 3 4 5; do one x.6456.t$t.d$DUR.$r $PLAIN 6456 0 $DUR $t; done; done
fi
if has CNT; then
  while IFS='|' read -r s evs <&3; do
    [ -z "$evs" ] && continue
    codes=$(echo "$evs" | tr ',' '\n' | cut -d= -f2 | paste -sd,)
    for cfg in "6456 0" "6456 20" "6400 0"; do
      set -- $cfg
      DIETPERF_OUTDIR=$out/c.$s.$1.n$2.d DIETPERF_PMUv3=$codes one c.$s.$1.n$2 $PROBE $1 $2 $DUR
    done
  done 3< $W/events.codes
fi
echo "done $out processes $n"
grep -c '^rc 0 ' $out/launches.txt; grep '^rc' $out/launches.txt | grep -v '^rc 0 ' | head -5
for f in $out/w.6456.n0.d$DUR.*.out $out/w.6456.n20.d$DUR.*.out; do [ -e $f ] && echo "$(basename $f) $(grep -h 'Total Bandwidth (MB/sec)' $f)"; done
cat /proc/loadavg
