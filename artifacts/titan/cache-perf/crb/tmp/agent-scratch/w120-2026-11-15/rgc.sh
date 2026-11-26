#!/usr/bin/env bash
# rgc.sh NAME BINARY SHA256 SETS < spec - groups of simultaneous processes (mixed kernels) with mesh counters (root, perf stat -a).
# spec lines: group|tag=args ;; tag=args ...   SETS lines: setname|full perf event list. sudo is used for perf stat only.
set -u
M=/tmp/positron-perf.RUNNING
name=$1; BW=$2; sha=$3; sets=$4; WIN=${WIN:-3}; DELAY=${DELAY:-9}
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
echo "$sha  $BW" | sha256sum -c - >/dev/null || { echo "sha mismatch"; exit 2; }
out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
{ date -u; uname -r; cat /proc/loadavg; who; echo "binary $BW $sha WIN $WIN DELAY $DELAY"; } > $out/env.txt
cp $sets $out/sets.ok
while IFS='|' read -r grp items <&3; do
  [ -z "$grp" ] && continue
  [ -e $M ] && { echo "marker: stop"; exit 3; }
  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done
  sleep 5
  echo "launch $grp utc $(date -u +%T) load $(cat /proc/loadavg) users $(who | wc -l) items $items" >> $out/launches.txt
  pids=
  while read -r it; do
    [ -z "$it" ] && continue
    tag=${it%%=*}; args=${it#*=}
    taskset -c 0-119 $BW $args > $out/$grp.$tag.csv 2>> $out/stderr.txt < /dev/null &
    pids="$pids $!"
  done < <(echo "$items" | sed 's/ ;; /\n/g')
  sleep $DELAY
  while IFS='|' read -r sn evs; do
    for p in $pids; do kill -0 $p 2>/dev/null || { echo "process ended before set $sn of $grp" >> $out/launches.txt; break 2; }; done
    [ -e $M ] && { kill $pids; echo "marker: killed"; exit 3; }
    sudo -n perf stat -a -x, -e "arm_cmn_0/dtc_cycles/,arm_cmn_1/dtc_cycles/,$evs" -o $out/$grp.$sn.perf -- sleep $WIN 2>> $out/stderr.txt
  done < $out/sets.ok
  while :; do alive=0; for p in $pids; do kill -0 $p 2>/dev/null && alive=1; done; [ $alive = 0 ] && break
    [ -e $M ] && { kill $pids; echo "marker: killed"; exit 3; }; sleep 1; done
  for p in $pids; do wait $p; echo "rc $? $grp" >> $out/launches.txt; done
done 3<&0
sudo -n chown -R $(id -un): $out 2>/dev/null
echo "done $out"; grep -c '^rc 0' $out/launches.txt; grep -c 'ended' $out/launches.txt; wc -c < $out/stderr.txt; head -c 600 $out/stderr.txt
