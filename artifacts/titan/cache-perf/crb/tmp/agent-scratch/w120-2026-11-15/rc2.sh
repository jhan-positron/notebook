#!/usr/bin/env bash
# rc2.sh NAME BINARY SHA256 SETS < spec - like rc.sh, but each set line holds full perf event strings: setname|event,event,...
# spec lines: tag|arguments of the binary (one long timed interval). SETS: file, one event set per line: setname|ev1,ev2,...
# Each event EV is counted as arm_cmn_0/EV/ and arm_cmn_1/EV/. sudo is used for perf stat only. No system setting is changed.
set -u
M=/tmp/positron-perf.RUNNING
name=$1; BW=$2; sha=$3; sets=$4; WIN=${WIN:-4}; DELAY=${DELAY:-9}
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
echo "$sha  $BW" | sha256sum -c - >/dev/null || { echo "sha mismatch"; exit 2; }
out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
{ date -u; uname -r; cat /proc/loadavg; who; echo "binary $BW $sha WIN $WIN DELAY $DELAY"; } > $out/env.txt
cp $sets $out/sets.txt
cp $sets $out/sets.ok
while IFS='|' read -r tag args <&3; do
  [ -z "$tag" ] && continue
  [ -e $M ] && { echo "marker: stop"; exit 3; }
  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done
  sleep 5
  echo "launch $tag utc $(date -u +%T.%N) epoch $(date +%s.%N) load $(cat /proc/loadavg) users $(who | wc -l) args $args" >> $out/launches.txt
  taskset -c 0-119 $BW $args > $out/$tag.csv 2>> $out/stderr.txt < /dev/null &
  pid=$!
  sleep $DELAY
  while IFS='|' read -r sn evs; do
    kill -0 $pid 2>/dev/null || { echo "process ended before set $sn of $tag" >> $out/launches.txt; break; }
    [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }
    echo "win $tag $sn start $(date +%s.%N)" >> $out/launches.txt
    sudo -n perf stat -a -x, -e "arm_cmn_0/dtc_cycles/,arm_cmn_1/dtc_cycles/,$evs" -o $out/$tag.$sn.perf -- sleep $WIN 2>> $out/stderr.txt
    echo "win $tag $sn end $(date +%s.%N)" >> $out/launches.txt
  done < $out/sets.ok
  echo "sets done $tag $(date +%s.%N)" >> $out/launches.txt
  while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done
  wait $pid; echo "rc $? $tag utc $(date -u +%T)" >> $out/launches.txt
done 3<&0
sudo -n chown -R $(id -un): $out 2>/dev/null
echo "done $out"; cat $out/unsupported.txt 2>/dev/null; grep -c '^win' $out/launches.txt; grep '^rc\|ended' $out/launches.txt; wc -c < $out/stderr.txt; head -c 800 $out/stderr.txt
