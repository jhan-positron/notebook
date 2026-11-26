#!/usr/bin/env bash
# run_single.sh - one core, ASCT read loop, size sweep. No root. CPUs 2 and 41 only (the CPUs of the 2026-11-15 work).
# Part U: the installed ASCT binary, no counters, REPS processes per CPU and size.
# Part N: the installed binary with 1, 2, 4, 8 injected NOPs at 32 KiB, 1 MiB and 8 MiB, NREPS processes each.
# Part C: ASCT's probe variant with ASCT's counter capture (environment DIETPERF_PMUv3), CREPS processes per
#         CPU, size and event set. Every process is one ASCT bandwidth run with ASCT's default command line
#         (benchspec/memory_benchspec.py: --duration 0.25 --delay-seconds 0 --bw-fine-delay 0 --bw-write=0).
# Stop controls: marker file /tmp/positron-perf.RUNNING and ~/cache-perf/STOP are checked before every process.
set -u
M=/tmp/positron-perf.RUNNING; STOP=$HOME/cache-perf/STOP
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
W=$HOME/cache-perf/asct-20261116
PLAIN=$HOME/asct/asct_venv/bin/loaded-latency-asct-sve.bin
PROBE=$W/loaded-latency-asct-probe-sve.bin
REPS=${REPS:-8}; CREPS=${CREPS:-2}; DUR=${DUR:-0.25}; PARTS=${PARTS:-U N C}
SIZES=${SIZES:-"32768 1048576 1572864 2097152 2621440 3145728 4194304 5242880 6291456 8388608 12582912 16777216 25165824 33554432 268435456 1073741824"}
CA=${CA:-2}; CB=${CB:-41}   # the two CPUs; the defaults are the CPUs of the 2026-11-15 work
RSIZES=$(echo $SIZES | tr ' ' '\n' | tac | tr '\n' ' ')
NUMA=$(command -v numactl || ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null)
out=$HOME/cache-perf/results/asct-single-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
{ echo "utc $(date -u +%FT%TZ)"; uname -r; cat /proc/loadavg; who; ps -eo user,pcpu,comm --sort=-pcpu | head -6
  sha256sum $PLAIN $PROBE; echo "REPS $REPS CREPS $CREPS DUR $DUR PARTS $PARTS CPUS $CA $CB numactl ${NUMA:-none}"; echo "SIZES $SIZES"; } > $out/env.txt 2>&1
cp $W/events.codes $out/
n=0
one() { # one TAG BINARY CPU BYTES [NOPS]  (environment of the caller is passed on)
  [ -e $M ] && { echo "marker: stop after $n processes"; exit 3; }
  [ -e $STOP ] && { echo "STOP file: stop after $n processes"; exit 4; }
  # ASCT's Python layer creates the counter folder before the run; two threads that create it at the same time fail
  [ -n "${DIETPERF_OUTDIR:-}" ] && mkdir -p "$DIETPERF_OUTDIR"
  echo "launch $1 epoch $(date +%s.%N) load $(cat /proc/loadavg)" >> $out/launches.txt
  taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $2 --duration $DUR --delay-seconds 0 --bw-cpu $3 --bw-buflen $4 \
      --bw-fine-delay ${5:-0} --bw-write=0 --bw-cacheline-bytes 64 > $out/$1.out 2>&1 < /dev/null
  echo "rc $? $1" >> $out/launches.txt; n=$((n+1))
}
case " $PARTS " in *" U "*)
for r in $(seq $REPS); do
  if [ $((r % 2)) = 1 ]; then cpus="$CA $CB"; sz=$SIZES; else cpus="$CB $CA"; sz=$RSIZES; fi
  for b in $sz; do for c in $cpus; do one u.$c.$b.$r $PLAIN $c $b; done; done
done;; esac
case " $PARTS " in *" C "*)
for r in $(seq $CREPS); do
  if [ $((r % 2)) = 1 ]; then cpus="$CA $CB"; sz=$SIZES; else cpus="$CB $CA"; sz=$RSIZES; fi
  while IFS='|' read -r s evs; do
    [ -z "$evs" ] && continue
    codes=$(echo "$evs" | tr ',' '\n' | cut -d= -f2 | paste -sd,)
    for b in $sz; do for c in $cpus; do
      DIETPERF_OUTDIR=$out/c.$s.$c.$b.$r.d DIETPERF_PMUv3=$codes one c.$s.$c.$b.$r $PROBE $c $b
    done; done
  done < $W/events.codes
done;; esac
# Part N: the ASCT loop with injected NOPs (a loop that is limited by its own instructions), 3 sizes
case " $PARTS " in *" N "*)
for r in $(seq ${NREPS:-4}); do
  if [ $((r % 2)) = 1 ]; then cpus="$CA $CB"; else cpus="$CB $CA"; fi
  for nn in 1 2 4 8; do for b in 32768 1048576 8388608; do for c in $cpus; do one n.$nn.$c.$b.$r $PLAIN $c $b $nn; done; done; done
done;; esac
# Part NC (added 2026-11-16 after the first data, see DECISIONS.md): the padded ASCT loop with counters, sets A B E
case " $PARTS " in *" NC "*)
for r in $(seq $CREPS); do
  if [ $((r % 2)) = 1 ]; then cpus="$CA $CB"; else cpus="$CB $CA"; fi
  while IFS='|' read -r s evs; do
    case $s in A|B|E) ;; *) continue;; esac
    codes=$(echo "$evs" | tr ',' '\n' | cut -d= -f2 | paste -sd,)
    for nn in 1 2 4; do for b in 1048576 8388608; do for c in $cpus; do
      DIETPERF_OUTDIR=$out/nc.$s.$nn.$c.$b.$r.d DIETPERF_PMUv3=$codes one nc.$s.$nn.$c.$b.$r $PROBE $c $b $nn
    done; done; done
  done < $W/events.codes
done;; esac
echo "done $out processes $n"
grep -c '^rc 0 ' $out/launches.txt; grep '^rc' $out/launches.txt | grep -v '^rc 0 ' | head -5
grep -h "Total Bandwidth (MB/sec)" $out/u.$CA.8388608.*.out 2>/dev/null | head -8
cat /proc/loadavg
