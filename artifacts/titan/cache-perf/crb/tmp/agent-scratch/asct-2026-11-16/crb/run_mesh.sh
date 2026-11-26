#!/usr/bin/env bash
# run_mesh.sh NAME SETS < spec - mesh (CMN) counters while one ASCT bandwidth process runs. ROOT IS USED FOR
# 'perf stat -a' ONLY (read-only counters, as rc.sh of 2026-11-15). No system setting is changed. The benchmark
# process itself runs without root. CPUs 0-119 only for the benchmark.
# spec lines: tag|layout|bytes|nops|duration   layout: 6456, 6400, c<cpu> (one core), idle (no process, sleep only)
# SETS: one event set per line, setname|ev1;ev2;...  Each event is counted as arm_cmn_0/EV/ and arm_cmn_1/EV/.
# Environment: WIN = seconds per counting window (default 4), DELAY = seconds from launch to the first window.
set -u
M=/tmp/positron-perf.RUNNING; STOP=$HOME/cache-perf/STOP
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
name=$1; sets=$2; WIN=${WIN:-4}; DELAY=${DELAY:-8}
W=$HOME/cache-perf/asct-20261116
PLAIN=$HOME/asct/asct_venv/bin/loaded-latency-asct-sve.bin
NUMA=$(command -v numactl || ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null)
sudo -n true 2>/dev/null || { echo "sudo needs a password: stop, nothing was run"; exit 5; }
out=$HOME/cache-perf/results/asct-mesh-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
{ echo "utc $(date -u +%FT%TZ)"; uname -r; cat /proc/loadavg; who; sha256sum $PLAIN; echo "WIN $WIN DELAY $DELAY sets $sets"; } > $out/env.txt 2>&1
cp $sets $out/sets.txt
: > $out/sets.ok
while IFS='|' read -r sn evs; do
  [ -z "$sn" ] && continue; ok=
  for e in ${evs//;/ }; do
    if sudo -n perf stat -a -x, -e "arm_cmn_0/$e/" -o /dev/null -- true 2>/dev/null < /dev/null; then ok="$ok;$e"; else echo "unsupported $sn $e" >> $out/unsupported.txt; fi
  done
  [ -n "$ok" ] && echo "$sn|${ok#;}" >> $out/sets.ok
done < $sets
cpuflags() {
  case $1 in 6456) r="0-119";; 6400) r="0-63";; 0056) r="64-119";; c*) r="${1#c}-${1#c}";; *) echo "bad layout $1" >&2; exit 2;; esac
  for part in $r; do for c in $(seq ${part%-*} ${part#*-}); do printf -- '--bw-cpu %d ' $c; done; done
}
while IFS='|' read -r tag lay bytes nops dur <&3; do
  [ -z "$tag" ] && continue
  [ -e $M ] && { echo "marker: stop"; exit 3; }
  [ -e $STOP ] && { echo "STOP file: stop"; exit 4; }
  for i in $(seq 60); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done
  sleep 5
  echo "launch $tag epoch $(date +%s.%N) load $(cat /proc/loadavg) users $(who | wc -l) layout $lay bytes $bytes nops $nops duration $dur" >> $out/launches.txt
  pid=
  if [ "$lay" != idle ]; then
    case $lay in c*) case ${lay#c} in 12[0-7]) echo "CPU ${lay#c} is not allowed"; exit 2;; esac;; esac
    taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $PLAIN --duration $dur --delay-seconds 0 $(cpuflags $lay) --bw-buflen $bytes \
        --bw-fine-delay $nops --bw-write=0 --bw-cacheline-bytes 64 > $out/$tag.out 2>&1 < /dev/null &
    pid=$!
  fi
  sleep $DELAY
  while IFS='|' read -r sn evs; do
    if [ -n "$pid" ]; then kill -0 $pid 2>/dev/null || { echo "process ended before set $sn of $tag" >> $out/launches.txt; break; }; fi
    [ -e $M ] && { [ -n "$pid" ] && kill $pid; echo "marker: killed"; exit 3; }
    el=
    for e in ${evs//;/ }; do el="$el,arm_cmn_0/$e/,arm_cmn_1/$e/"; done
    echo "win $tag $sn start $(date +%s.%N)" >> $out/launches.txt
    sudo -n perf stat -a -x, -e "arm_cmn_0/dtc_cycles/,arm_cmn_1/dtc_cycles/$el" -o $out/$tag.$sn.perf -- sleep $WIN 2>> $out/stderr.txt < /dev/null
    echo "win $tag $sn end $(date +%s.%N)" >> $out/launches.txt
  done < $out/sets.ok
  echo "sets done $tag $(date +%s.%N)" >> $out/launches.txt
  if [ -n "$pid" ]; then
    while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done
    wait $pid; echo "rc $? $tag epoch $(date +%s.%N)" >> $out/launches.txt
  fi
done 3<&0
sudo -n chown -R $(id -un): $out 2>/dev/null
echo "done $out"; cat $out/unsupported.txt 2>/dev/null; grep -c '^win .* start' $out/launches.txt; grep '^rc\|ended' $out/launches.txt
wc -c < $out/stderr.txt; head -c 600 $out/stderr.txt; grep -h "Total Bandwidth (MB/sec)" $out/*.out 2>/dev/null; cat /proc/loadavg
