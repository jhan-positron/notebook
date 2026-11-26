#!/usr/bin/env bash
# rg.sh NAME BINARY SHA256 < spec - groups of processes that run at the same time (mixed kernels). No root.
# spec lines: group|tag=args ;; tag=args ...  (args that start with @ are a full command, used for the latency probe)   Marker file checked before and during every group. CPUs 0-119 only.
set -u
M=/tmp/positron-perf.RUNNING
name=$1; BW=$2; sha=$3
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
echo "$sha  $BW" | sha256sum -c - >/dev/null || { echo "sha mismatch"; exit 2; }
out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
{ date -u; uname -r; cat /proc/loadavg; who; echo "binary $BW $sha"; } > $out/env.txt
while IFS='|' read -r grp items; do
  [ -z "$grp" ] && continue
  [ -e $M ] && { echo "marker: stop"; exit 3; }
  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done
  sleep 5
  echo "launch $grp utc $(date -u +%T) load $(cat /proc/loadavg) users $(who | wc -l) items $items" >> $out/launches.txt
  pids=
  while read -r it; do
    [ -z "$it" ] && continue
    tag=${it%%=*}; args=${it#*=}
    if [ "${args#@}" != "$args" ]; then taskset -c 0-119 ${args#@} > $out/$grp.$tag.csv 2>> $out/stderr.txt < /dev/null &
    else taskset -c 0-119 $BW $args > $out/$grp.$tag.csv 2>> $out/stderr.txt < /dev/null & fi
    pids="$pids $!"; echo "start $grp $tag epoch $(date +%s.%N)" >> $out/launches.txt
  done < <(echo "$items" | sed 's/ ;; /\n/g')
  while :; do alive=0; for p in $pids; do kill -0 $p 2>/dev/null && alive=1; done; [ $alive = 0 ] && break
    [ -e $M ] && { kill $pids; echo "marker: killed"; exit 3; }; sleep 1; done
  for p in $pids; do wait $p; echo "rc $? $grp" >> $out/launches.txt; done
done
echo "done $out"; grep -c '^rc 0' $out/launches.txt; grep '^rc' $out/launches.txt | grep -vc '^rc 0'; wc -c < $out/stderr.txt; head -c 500 $out/stderr.txt
