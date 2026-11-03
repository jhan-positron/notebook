#!/usr/bin/env bash
# run_followup3.sh - 2026-11-02 follow-up, no root needed.
#   A. DRAM write fall: asmwrite 256M with a threads on mesh 0 (CPUs 0..a-1) and
#      b threads on mesh 1 (CPUs 64..64+b-1), a and b varied independently.
#   B. the same grid for asmread, a subset.
#   C. per-core sweep, CPUs 0-119, two sweeps: 16M mesh-cache latency (repeated
#      and fresh) and 1-thread asmread 8M. Shows whether a core's position
#      changes its mesh-cache latency and bandwidth.
# Same rules as run_crb.sh: CPUs 0-119 only, stops if the RUNNING marker appears.
set -euo pipefail
if [[ -z ${_RUN_CRB_PINNED:-} ]]; then
    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"
fi
MARKER=/tmp/positron-perf.RUNNING
BENCH=$(cd "$(dirname "$0")" && pwd)
check_marker() { [[ -e $MARKER ]] && { echo "$MARKER exists: stopping" >&2; exit 3; }; return 0; }
check_marker
OUT=$HOME/cache-perf/results/followup3-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
exec > >(tee -a "$OUT/log.txt") 2>&1
echo "results: $OUT"; date -u
make -C "$BENCH"
L="$BENCH/latency"; B="$BENCH/bandwidth"

cpulist() { # a threads on mesh 0, b threads on mesh 1 -> cpu list
    local a=$1 b=$2 l=""
    (( a > 0 )) && l="0-$((a-1))"
    (( b > 0 )) && l="${l:+$l,}64-$((64+b-1))"
    echo "$l"
}
grid() { local k=$1 out=$2; shift 2; for ab in "$@"; do local a=${ab%,*} b=${ab#*,}; check_marker
    echo "-- kernel $k mesh0 $a mesh1 $b cpus $(cpulist $a $b)" >> "$out"
    $B --threads $((a+b)) --cpus "$(cpulist $a $b)" --bytes 256M --kernel $k --reps 3 --min-ms 500 >> "$out"; done; }

echo "== A. asmwrite 256M, threads per mesh grid"; date -u
: > "$OUT/writegrid.csv"
grid asmwrite "$OUT/writegrid.csv" 16,0 32,0 48,0 64,0 0,16 0,32 0,48 0,56 16,16 32,16 16,32 32,32 48,16 16,48 48,32 32,48 48,48 64,16 64,32 64,48 64,56 48,56 32,56 16,56

echo "== B. asmread 256M, subset of the grid"; date -u
: > "$OUT/readgrid.csv"
grid asmread "$OUT/readgrid.csv" 64,0 0,56 16,16 32,32 48,48 64,56

echo "== C. per-core sweep"; date -u
for sweep in 1 2; do
    : > "$OUT/percore-latency-$sweep.csv"; : > "$OUT/percore-asmread-$sweep.csv"
    for c in $(seq 0 119); do
        check_marker
        echo "-- cpu $c" >> "$OUT/percore-latency-$sweep.csv"
        $L --cpu $c --sizes 16M --reps 2 --min-ms 300 >> "$OUT/percore-latency-$sweep.csv"
        $L --cpu $c --sizes 16M --fresh 3 >> "$OUT/percore-latency-$sweep.csv"
        echo "-- cpu $c" >> "$OUT/percore-asmread-$sweep.csv"
        $B --threads 1 --cpus $c --bytes 8M --kernel asmread --reps 3 --min-ms 300 >> "$OUT/percore-asmread-$sweep.csv"
    done
done
echo "== done"; date -u; echo "$OUT"
