#!/usr/bin/env bash
# run_cread.sh - compare asmread, cread and read with one thread on CRB.
# Reads stdin: nothing. Writes only under $HOME/cache-perf.
set -euo pipefail
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi
MARKER=/tmp/positron-perf.RUNNING
check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }
check_marker
SRC=$(cd "$(dirname "$0")" && pwd)
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=$HOME/cache-perf/results/cread-$TS
mkdir -p "$OUT"
CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11"
B=$SRC/bandwidth_cread
gcc $CFLAGS -o "$B" "$SRC/bandwidth_cread.c"
{
  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(cut -d' ' -f1-3 /proc/loadavg) logins=$(who | wc -l)"
  echo "## gcc=$(gcc --version | head -1)"
  echo "## CFLAGS=$CFLAGS"
  echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"
  echo "## sha256:"; sha256sum "$SRC/bandwidth_cread.c" "$B" "$HOME/cache-perf/bench/bandwidth.c"
  for f in k_cread k_asmread k_read; do
    echo "=== $f ==="
    objdump -d --no-show-raw-insn --disassemble=$f "$B" | sed -n '/>:$/,$p'
  done
} > "$OUT/probe.txt"
: > "$OUT/cread.csv"
for round in 1 2; do
  for cpu in 0 2; do
    for bytes in 32K 1M 8M 1G; do
      check_marker
      echo "-- round $round cpu $cpu bytes $bytes load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T)" >> "$OUT/cread.csv"
      "$B" --threads 1 --cpus $cpu --bytes $bytes --kernel readcmp --reps 3 --min-ms 500 >> "$OUT/cread.csv"
    done
  done
done
echo "## load_after=$(cut -d' ' -f1-3 /proc/loadavg) utc=$(date -u +%FT%TZ)" >> "$OUT/probe.txt"
echo "$OUT"
