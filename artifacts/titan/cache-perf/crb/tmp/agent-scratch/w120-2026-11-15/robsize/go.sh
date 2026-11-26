#!/bin/bash
# CRB wrapper: wait until no other measurement runs, hold the lock file,
# build, then run robsize on CPU 2 inside CPUs 0-119.
# usage: go.sh TAG [robsize arguments]
set -uo pipefail
cd "$(dirname "$0")"
tag=$1; shift
LOCK=$HOME/cache-perf/w120-20261115/LOCK.rob
out="rob-$tag-$(date -u +%Y%m%dT%H%M%SZ).csv"

quiet() { # 3 empty checks 20 s apart; else wait 2 min; up to 60 min
    local deadline=$(( $(date +%s) + 3600 ))
    while :; do
        if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi
        local ok=1
        for i in 1 2 3; do
            if [ -n "$(pgrep -x 'bwx11|bwx12|perf|robsize')" ]; then ok=0; break; fi
            [ $i -lt 3 ] && sleep 20
        done
        [ $ok = 1 ] && return 0
        [ "$(date +%s)" -ge "$deadline" ] && { echo "busy for 60 min: stop"; exit 4; }
        echo "busy at $(date -u +%T), waiting 2 min"
        sleep 120
    done
}

quiet
taskset -c 0-119 gcc -O2 -Wall -o robsize robsize.c || { echo "BUILD FAILED"; exit 5; }
[ "$tag" = build ] && { echo "BUILD OK"; exit 0; }
quiet
touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT
{
    echo "# host=$(uname -n) arch=$(uname -m) kernel=$(uname -r)"
    echo "# gcc=$(gcc -dumpfullversion) args=$*"
    echo "# start_utc=$(date -u +%FT%TZ)"
    echo "# loadavg_before=$(cat /proc/loadavg)"
    echo "# thp_enabled=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo unknown)"
} > "$out"
# With no arguments: one run of every kind. With a file TAG.spec: one
# robsize call per line of that file, all inside one 570 s budget.
t_end=$(( $(date +%s) + 570 ))
rc=0
if [ -f "$tag.spec" ]; then
    while read -r line; do
        [ -z "$line" ] && continue
        left=$(( t_end - $(date +%s) ))
        [ $left -le 5 ] && { echo "# budget used up, skipped: $line" >> "$out"; rc=124; continue; }
        echo "# call: $line" >> "$out"
        # shellcheck disable=SC2086
        timeout $left taskset -c 0-119 ./robsize --cpu 2 $line >> "$out" 2>> "$out.err" < /dev/null || rc=$?
    done < "$tag.spec"
else
    timeout 570 taskset -c 0-119 ./robsize --cpu 2 "$@" >> "$out" 2> "$out.err"
    rc=$?
fi
echo "# exit_code=$rc" >> "$out"
echo "# loadavg_after=$(cat /proc/loadavg)" >> "$out"
echo "# end_utc=$(date -u +%FT%TZ)" >> "$out"
echo "DONE rc=$rc $out"
