#!/bin/bash
# Build robsize and run every filler kind on CPU 2.
# Run on the AArch64 target, from any directory. Extra arguments are passed
# to robsize, for example:  ./run_rob.sh --kind nop --nmin 300 --nmax 420 --nstep 1
set -euo pipefail
cd "$(dirname "$0")"

CPU=2
out="rob-$(date -u +%Y%m%dT%H%M%SZ).csv"

gcc -O2 -Wall -o robsize robsize.c

{
    echo "# host=$(uname -n) arch=$(uname -m) kernel=$(uname -r)"
    echo "# gcc=$(gcc -dumpfullversion)"
    echo "# loadavg_before=$(cat /proc/loadavg)"
    echo "# thp_enabled=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo unknown)"
} | tee "$out"

./robsize --cpu "$CPU" "$@" | tee -a "$out"

echo "# loadavg_after=$(cat /proc/loadavg)" | tee -a "$out"
echo "wrote $(pwd)/$out" >&2
echo "step summary:" >&2
grep -E '^# (step|cut)' "$out" >&2 || true
