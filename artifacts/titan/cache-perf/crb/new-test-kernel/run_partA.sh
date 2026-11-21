#!/usr/bin/env bash
# run_partA.sh - Part A (screening) of new-test-kernel/plan.md, on CRB.
# Usage: STOP_AT=<UTC time or "none"> run_partA.sh [A1 A2 A3 A4 A5 A6 A7]   (no step: all steps)
#   STOP_AT is required. Example: STOP_AT=2026-11-14T15:00Z (start nothing that could run past this
#   time, e.g. 30 min before a block of Jeremy), or STOP_AT=none when no block is announced.
# Exit status: 0 done; 2 usage or wrong binaries; 3 marker file appeared; 4 STOP_AT reached;
#   5 stop file ~/cache-perf/STOP found; 130 interrupted. In every case the csv files written so far are kept.
# Needs bw_old and bw_new in the same folder as this script (see handoff.md).
# Uses CPUs 0-119 only, writes only under $HOME/cache-perf, no sudo.
# Status: written 2026-11-13, syntax-checked only, never run.
set -euo pipefail
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi
MARKER=/tmp/positron-perf.RUNNING
STOPFILE=$HOME/cache-perf/STOP     # ours: "touch ~/cache-perf/STOP" from another login stops this script
: "${STOP_AT:?set STOP_AT to a UTC time like 2026-11-14T15:00Z, or to none}"
if [[ $STOP_AT == none ]]; then STOP_EPOCH=0; else STOP_EPOCH=$(date -u -d "$STOP_AT" +%s) || { echo "bad STOP_AT" >&2; exit 2; }; fi
MARGIN=${MARGIN:-150}              # seconds: longest single process of this script (est.) plus reserve
CHILD=""
stop_child() { if [[ -n $CHILD ]]; then kill -- -"$CHILD" 2>/dev/null || true; sleep 1; kill -9 -- -"$CHILD" 2>/dev/null || true; wait "$CHILD" 2>/dev/null || true; CHILD=""; fi; }
# why_stop: prints the reason and returns the exit status to use, or returns 0 if nothing asks us to stop.
# It is called in every turn of the wait and every second while a benchmark runs, so STOP_AT itself is
# enforced on a running benchmark. check_deadline adds the margin before a launch.
why_stop() {
  if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; return 3; fi
  if [[ -e $STOPFILE ]]; then echo "stop file $STOPFILE present: stop" >&2; return 5; fi
  if (( STOP_EPOCH && $(date -u +%s) >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT reached: stop" >&2; return 4; fi
  return 0
}
check_marker() { local rc=0; why_stop || rc=$?; if (( rc )); then stop_child; exit $rc; fi; }
check_deadline() { if (( STOP_EPOCH && $(date -u +%s) + MARGIN >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT is less than $MARGIN s away: stop" >&2; exit 4; fi; }
trap 'echo "interrupted: stopping the benchmark" >&2; stop_child; exit 130' INT TERM HUP
check_marker; check_deadline
SRC=$(cd "$(dirname "$0")" && pwd)
for b in bw_old bw_new; do [[ -x $SRC/$b ]] || { echo "missing $SRC/$b" >&2; exit 2; }; done
# the binaries of the run of 2026-11-13 (results/kernels-20261113T181222Z/probe.txt); stop if they are others
(cd "$SRC" && sha256sum -c --quiet - <<'SUMS'
e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old
fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new
SUMS
) || { echo "bw_old or bw_new is not the binary of 2026-11-13: stop (see handoff.md, Files)" >&2; exit 2; }
STEPS=${*:-A1 A2 A3 A4 A5 A6 A7}
OUT=$HOME/cache-perf/results/partA-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
echo "result folder: $OUT"
{
  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg) logins=$(who | wc -l) steps=$STEPS"
  echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag=$(cat /sys/kernel/mm/transparent_hugepage/defrag)"
  echo "## uptime=$(cut -d' ' -f1 /proc/uptime) $(grep -E 'MemFree|MemAvailable' /proc/meminfo | tr -s ' ' | tr '\n' ' ')"
  echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu | head -6
  echo "## sha256:"; (cd "$SRC" && sha256sum bw_old bw_new run_partA.sh)
  echo "## vmstat thp:"; grep -E '^thp_(fault_alloc|fault_fallback|collapse_alloc) ' /proc/vmstat
} > "$OUT/env.txt"

# Wait until at most 2 tasks are runnable (field 4 of /proc/loadavg, before the slash), 20 s at most.
# The field is read with the shell builtin, so the check itself starts no process.
# The marker and the stop file are checked in every turn. The wait is returned in WAITED.
settle() { local t=0 r; while :; do check_marker; read -r _ _ _ r _ < /proc/loadavg; r=${r%/*}; (( r <= 2 || t >= 20 )) && break; sleep 2 & wait $! || true; t=$((t+2)); done; WAITED=$t; }
# one <csv> <tag> <binary> <benchmark options...>: one process, with a header line.
one() {
  local csv=$1 tag=$2 bin=$3; shift 3
  check_marker; check_deadline
  settle                                  # checks the marker in every turn
  # evidence for the load of this launch: users logged in and the 5 busiest processes
  { echo "== $csv $tag utc $(date -u +%T) loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who | wc -l)"; ps -eo pcpu,user,comm --sort=-pcpu | head -6; } >> "$OUT/launches.txt"
  check_marker; check_deadline            # again, directly before the launch
  echo "-- step ${csv%.csv} tag $tag binary $bin waited_s $WAITED loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who | wc -l) utc $(date -u +%T) args $*" >> "$OUT/$csv"
  # run in an own process group; poll the marker and the stop file every second; kill the group if one appears
  setsid "$SRC/$bin" "$@" >> "$OUT/$csv" 2>> "$OUT/stderr.txt" & CHILD=$!
  local rc=0
  while kill -0 "$CHILD" 2>/dev/null; do
    why_stop || rc=$?
    if (( rc )); then echo "-- killed tag $tag status $rc utc $(date -u +%T)" >> "$OUT/$csv"; stop_child; exit $rc; fi
    sleep 1 & wait $! || true
  done
  wait "$CHILD" || rc=$?; CHILD=""
  if (( rc )); then echo "-- failed tag $tag exit $rc" >> "$OUT/$csv"; echo "benchmark failed ($tag, exit $rc): stop" >&2; exit 1; fi
}
# a threads on mesh 0 (CPUs 0..a-1), b threads on mesh 1 (CPUs 64..64+b-1): same rule as bench/run_followup3.sh
cpulist() { local a=$1 b=$2 l=""; (( a > 0 )) && l="0-$((a-1))"; (( b > 0 )) && l="${l:+$l,}64-$((64+b-1))"; echo "$l"; }
bin_of() { case $1 in read_old|write_old) echo bw_old;; *) echo bw_new;; esac; }   # old C kernels from bw_old, all others from bw_new
ker_of() { case $1 in read_old|read_new) echo read;; write_old|write_new) echo write;; *) echo "$1";; esac; }
K6="read_old read_new asmread write_old write_new asmwrite"; K6R="asmwrite write_new write_old asmread read_new read_old"
ALL=(--threads 120 --cpus "$(cpulist 64 56)" --bytes 256M --per-thread)

for s in $STEPS; do case $s in
A1) # default 0.5 s interval, per-thread rows, 2 rounds, round 2 in reversed order
  for round in 1 2; do [[ $round == 1 ]] && L=$K6 || L=$K6R
    for k in $L; do one A1.csv "$k-r$round" "$(bin_of $k)" "${ALL[@]}" --kernel "$(ker_of $k)" --reps 3 --min-ms 500; done; done ;;
A2) # long interval: 6 s for read kernels, 15 s for write kernels
  for round in 1 2; do [[ $round == 1 ]] && L=$K6 || L=$K6R
    for k in $L; do case $k in *read*) ms=6000;; *) ms=15000;; esac
      one A2.csv "$k-r$round" "$(bin_of $k)" "${ALL[@]}" --kernel "$(ker_of $k)" --reps 3 --min-ms $ms; done; done ;;
A3) avail=$(awk '/^MemAvailable:/{print int($2/1048576)}' /proc/meminfo)   # two buffers of 256 MiB for 120 threads need 60 GiB
  if (( avail < 70 )); then echo "A3 skipped: MemAvailable is $avail GiB, below 70 GiB" | tee -a "$OUT/env.txt" >&2; continue; fi
  # old read with one buffer per thread (--kernel read) and with two (--kernel all: also times write and copy; compare the read rows only)
  for ms in 500 6000; do for i in 1 2 3; do
      one A3.csv "onebuf-ms$ms-$i" bw_old "${ALL[@]}" --kernel read --reps 3 --min-ms $ms
      one A3.csv "twobuf-ms$ms-$i" bw_old "${ALL[@]}" --kernel all  --reps 3 --min-ms $ms
  done; done ;;
A4) # threads per mesh: 64+b and a+a, old read and asm read, 6 s interval
  for ab in 64,0 64,16 64,32 64,40 64,48 64,52 64,56 32,32 40,40 48,48 56,56; do a=${ab%,*}; b=${ab#*,}
    for k in read_old asmread; do
      one A4.csv "$k-$a+$b" "$(bin_of $k)" --threads $((a+b)) --cpus "$(cpulist $a $b)" --bytes 256M --per-thread --kernel "$(ker_of $k)" --reps 2 --min-ms 6000
    done; done ;;
A5) # one thread, 8 MiB, 30 intervals of 0.3 s, then at once a second process on the same CPU
  for cpu in 2 41; do for i in 1 2; do
      one A5.csv "cpu$cpu-proc$i" bw_new --threads 1 --cpus $cpu --bytes 8M --kernel asmread --reps 30 --min-ms 300
  done; done ;;
A6) # one thread, 8 MiB, with and without 2 MiB pages, alternating
  for i in 1 2 3 4 5 6 7 8; do
      one A6.csv "thp-$i"   bw_new --threads 1 --cpus 2 --bytes 8M --kernel asmread --reps 3 --min-ms 500
      one A6.csv "nothp-$i" bw_new --threads 1 --cpus 2 --bytes 8M --kernel asmread --reps 3 --min-ms 500 --no-thp
  done ;;
A7) check_marker; check_deadline
  { echo "## sve_default_vector_length (bytes):"; cat /proc/sys/abi/sve_default_vector_length 2>&1 || true; } > "$OUT/A7-sve.txt"
  perf list > "$OUT/A7-perf-list.txt" 2>&1 || echo "perf list failed" >> "$OUT/A7-perf-list.txt"
  ls /sys/bus/event_source/devices/ > "$OUT/A7-pmu-devices.txt" 2>&1 || true
  for d in /sys/bus/event_source/devices/armv8*; do echo "== $d type=$(cat "$d/type" 2>/dev/null)"; grep -H . "$d"/events/* 2>/dev/null; done > "$OUT/A7-core-events.txt" || true ;;
*) echo "unknown step $s" >&2; exit 2 ;;
esac; done
echo "## end utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg)" >> "$OUT/env.txt"
grep -E '^thp_(fault_alloc|fault_fallback|collapse_alloc) ' /proc/vmstat >> "$OUT/env.txt"
echo "$OUT"
