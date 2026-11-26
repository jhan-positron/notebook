#!/usr/bin/env bash
# ra.sh NAME - rerun of the 120-thread part of run_kernels.sh (2026-11-13).
# It uses the SAME two binaries as that run (sha256 checked) and builds nothing.
# bw_old = bandwidth.orig.c (read kernel: portable C, 16 running sums, load + add).
# bw_new = bandwidth.c      (read kernel: NEON intrinsics, loads only).
# Process arguments, kernel order and round order are those of run_kernels.sh.
# Writes only under $HOME/cache-perf/results. Uses CPUs 0-119 only. No sudo.
set -euo pipefail
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi
NAME=${1:?usage: ra.sh NAME}
MARKER=/tmp/positron-perf.RUNNING
check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }
check_marker
SRC=$HOME/cache-perf/scratch-kernels-20261113
# sha256 of the binaries as recorded in results/kernels-20261113T181222Z/probe.txt
(cd "$SRC" && sha256sum -c - > /dev/null <<'SUMS'
e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old
fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new
SUMS
) || { echo "sha mismatch: bw_old or bw_new is not the binary of 2026-11-13" >&2; exit 2; }
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=$HOME/cache-perf/results/k120-$NAME-$TS
mkdir -p "$OUT"
load() { cut -d' ' -f1-3 /proc/loadavg; }
# Before the first process: wait until at most 2 tasks are runnable, then 5 s (rule of rx.sh).
for _ in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); if [[ $r -le 2 ]]; then break; fi; sleep 1; done
if [[ $r -gt 2 ]]; then echo "not quiet: $r tasks runnable after 40 s: stop" >&2; exit 6; fi
sleep 5
check_marker
{
  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(load) logins=$(who | wc -l) name=$NAME"
  echo "## boot_id=$(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo | tr -s ' ') runnable=$r"
  echo "## kernel=$(uname -r) thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"
  echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu | head -6
  echo "## sha256:"; (cd "$SRC" && sha256sum bw_old bw_new); sha256sum "$0"
} > "$OUT/probe.txt"
# One process per (binary, kernel): no kernel is timed after another kernel
# in the same process. Round 2 reverses the order of binaries and kernels.
one() { # csv binary kernel threads cpus bytes round
  check_marker
  echo "-- binary $2 kernel $3 threads $4 cpus $5 bytes $6 round $7 load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T)" >> "$1"
  "$SRC/$2" --threads "$4" --cpus "$5" --bytes "$6" --kernel "$3" --reps 3 --min-ms 500 >> "$1"
}
K1="read write copy asmread asmwrite asmcopy"; K2="asmcopy asmwrite asmread copy write read"
for round in 1 2; do
  if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi
  for k in $KS; do for b in $BINS; do one "$OUT/threads120.csv" $b $k 120 0-119 256M $round; done; done
done
echo "## load_after=$(load) utc=$(date -u +%FT%TZ) $(grep MemTotal /proc/meminfo | tr -s ' ')" >> "$OUT/probe.txt"
echo "done $OUT"
