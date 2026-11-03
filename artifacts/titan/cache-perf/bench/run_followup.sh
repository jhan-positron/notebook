#!/usr/bin/env bash
# run_followup.sh - follow-up experiments after the first CRB sweep (2026-10-30).
#   A. fresh-chain latency (defeats a temporal prefetcher), CPU 3
#   B. CPU-pair bandwidth test: do two adjacent CPUs share a mesh port?
#   C. inline-asm kernels (loads/stores only) for peak per-core and aggregate bandwidth
#   D. DRAM regime at more thread counts
#   E. latency from CPUs 3, 64, 119 (mesh position)
# Same rules as run_crb.sh: CPUs 0-119 only, stops if the RUNNING marker appears.
set -euo pipefail
if [[ -z ${_RUN_CRB_PINNED:-} ]]; then
    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"
fi
MARKER=/tmp/positron-perf.RUNNING
BENCH=$(cd "$(dirname "$0")" && pwd)
check_marker() { [[ -e $MARKER ]] && { echo "$MARKER exists: stopping" >&2; exit 3; }; return 0; }
check_marker
OUT=$HOME/cache-perf/results/followup-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
exec > >(tee -a "$OUT/log.txt") 2>&1
echo "results: $OUT"
make -C "$BENCH"
L="$BENCH/latency"; B="$BENCH/bandwidth"

echo "== A. fresh-chain latency, cpu 3"
: > "$OUT/latency-fresh.csv"
for s in 256K 512K 1M 1.5M 2M 3M 4M 6M 8M 12M 16M 24M 32M 40M 48M 56M 64M 80M 96M 128M 192M 256M; do
    check_marker; $L --cpu 3 --sizes $s --fresh 8 >> "$OUT/latency-fresh.csv"
done
for s in 512M 1G 2G; do
    check_marker; $L --cpu 3 --sizes $s --fresh 3 >> "$OUT/latency-fresh.csv"
done

echo "== B. CPU-pair bandwidth (read, 8M per thread, 2 threads)"
: > "$OUT/pair.csv"
for c in 0,1 0,2 0,3 1,2 2,3 0,64 0,119 4,5 4,6; do
    check_marker; echo "-- cpus $c" >> "$OUT/pair.csv"
    $B --threads 2 --cpus $c --bytes 8M --kernel read --reps 2 --min-ms 300 >> "$OUT/pair.csv"
done
echo "-- cpus 0,1 1M (L2 regime)" >> "$OUT/pair.csv"
$B --threads 2 --cpus 0,1 --bytes 1M --kernel read --reps 2 --min-ms 300 >> "$OUT/pair.csv"
echo "-- cpus 0,1 1G (DRAM regime)" >> "$OUT/pair.csv"
$B --threads 2 --cpus 0,1 --bytes 1G --kernel read --reps 2 --min-ms 300 >> "$OUT/pair.csv"
echo "-- cpus 0,64 1G (DRAM regime)" >> "$OUT/pair.csv"
$B --threads 2 --cpus 0,64 --bytes 1G --kernel read --reps 2 --min-ms 300 >> "$OUT/pair.csv"

echo "== C. asm kernels"
: > "$OUT/asm.csv"
run_bw() { local k=$1 bytes=$2 cpus=$3; shift 3; for t in "$@"; do check_marker; echo "-- kernel $k bytes $bytes cpus $cpus threads $t" >> "$OUT/asm.csv";
    $B --threads $t --cpus $cpus --bytes $bytes --kernel $k --reps 3 --min-ms 500 >> "$OUT/asm.csv"; done; }
run_bw asmall 32K 0-119 1 120
run_bw asmall 1M  0-119 1 120
run_bw asmread  8M 0-119 1 2 4 8 14
run_bw asmwrite 8M 0-119 1 2 4 8 14
run_bw asmcopy  8M 0-119 1 2 4 7
run_bw asmall 1G 0-119 1 2 4 8
run_bw asmall 256M 0-119 16 32 64 96 120
# even-CPU placement: one thread per CPU pair, if pairs share a port
run_bw asmread 8M 0-118:2 1 2 4 8 14 32 56
run_bw asmall 256M 0-118:2 32 60

echo "== D. DRAM regime, compiled kernels, more thread counts"
: > "$OUT/dram.csv"
run_bw2() { local k=$1 bytes=$2 cpus=$3; shift 3; for t in "$@"; do check_marker; echo "-- kernel $k bytes $bytes cpus $cpus threads $t" >> "$OUT/dram.csv";
    $B --threads $t --cpus $cpus --bytes $bytes --kernel $k --reps 3 --min-ms 500 >> "$OUT/dram.csv"; done; }
run_bw2 all 256M 0-119 48 80 112
run_bw2 all 256M 0-118:2 32 48 60

echo "== E. latency by CPU (repeated and fresh)"
: > "$OUT/latency-bycpu.csv"
for c in 3 64 119; do
    check_marker; echo "-- cpu $c repeated" >> "$OUT/latency-bycpu.csv"
    $L --cpu $c --sizes 1M,16M,1G --reps 2 --min-ms 300 >> "$OUT/latency-bycpu.csv"
    echo "-- cpu $c fresh" >> "$OUT/latency-bycpu.csv"
    $L --cpu $c --sizes 16M,64M,1G --fresh 3 >> "$OUT/latency-bycpu.csv"
done
echo "== done"; echo "$OUT"
