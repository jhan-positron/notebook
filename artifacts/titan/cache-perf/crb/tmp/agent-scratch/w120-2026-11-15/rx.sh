#!/usr/bin/env bash
# rx.sh NAME BINARY SHA256 < spec   - generic runner for the 120-thread investigation, no root.
# spec lines: tag|arguments of the binary. Marker file checked before and during every process. CPUs 0-119 only.
set -u
M=/tmp/positron-perf.RUNNING
name=$1; BW=$2; sha=$3
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
echo "$sha  $BW" | sha256sum -c - >/dev/null || { echo "sha mismatch"; exit 2; }
out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
{ date -u; uname -r; cat /proc/loadavg; who; ps -eo user,pcpu,comm --sort=-pcpu | head -6; echo "binary $BW $sha"; } > $out/env.txt
while IFS='|' read -r tag args; do
  [ -z "$tag" ] && continue
  [ -e $M ] && { echo "marker: stop"; exit 3; }
  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done
  sleep 5
  echo "launch $tag utc $(date -u +%T) load $(cat /proc/loadavg) users $(who | wc -l) args $args" >> $out/launches.txt
  taskset -c 0-119 $BW $args > $out/$tag.csv 2>> $out/stderr.txt < /dev/null &
  pid=$!
  while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done
  wait $pid; echo "rc $? $tag utc $(date -u +%T)" >> $out/launches.txt
done
echo "done $out"; grep -c . $out/launches.txt; grep '^rc' $out/launches.txt | grep -v '^rc 0' ; wc -c < $out/stderr.txt; head -c 600 $out/stderr.txt
