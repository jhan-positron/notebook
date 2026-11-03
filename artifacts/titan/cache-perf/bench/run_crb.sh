#!/usr/bin/env bash
# run_crb.sh - cache latency and bandwidth measurement plan for CRB.
#
# Usage: ./run_crb.sh [--quick]
#   --quick   tiny sizes, 1-2 threads, short timings; for a local smoke test
#             (set CPUS=0-7 to limit the CPU list on a small host)
#
# Estimated wall time of the full run (est.):
#   latency sweep:   26 sizes x 3 reps x 0.3 s = 23 s, plus the sizes above
#                    256 MiB where two cycles exceed 0.3 s (1G ~16 s, 2G ~32 s,
#                    512M ~8 s), plus permutation build: about 2 min
#   latency + perf:  same sweep twice per size (2 cycles, then max(1 s, 6
#                    cycles)); the 256M-2G sizes dominate: about 2.5 min
#   bandwidth:       27 configurations, 3 reps x 0.5 s per kernel: about 100 s
#                    of timed loops, plus first touch (up to 120 x 256 MiB x 2
#                    = 60 GiB resident at the largest configuration): about 3-4 min
#   total:           about 8-9 min
#
# Reads /sys and /proc only for sysinfo.txt; never writes to /sys, cpufreq or
# sysctl, never uses sudo, writes only under $HOME/cache-perf.
set -euo pipefail

# Run everything (bash, make, tee, perf, the benchmarks' main threads) under
# the allowed CPU mask; the benchmarks' own pinning is a subset of it.
if [[ -z ${_RUN_CRB_PINNED:-} ]]; then
    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"
fi

MARKER=/tmp/positron-perf.RUNNING
CPUS=${CPUS:-0-119}          # CPUs 120-127 are reserved; never list them
LAT_CPU=3
BENCH=$(cd "$(dirname "$0")" && pwd)
QUICK=0
case ${1:-} in
    "") ;;
    --quick) QUICK=1 ;;
    *) echo "usage: $0 [--quick]" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { echo "usage: $0 [--quick]" >&2; exit 2; }

for tok in ${CPUS//,/ }; do
    if [[ ! $tok =~ ^([0-9]+)(-([0-9]+))?$ ]]; then
        echo "CPUS=$CPUS: bad token '$tok'" >&2; exit 2
    fi
    lo=${BASH_REMATCH[1]}; hi=${BASH_REMATCH[3]:-$lo}
    if (( lo > hi )); then
        echo "CPUS=$CPUS: reversed range '$tok'" >&2; exit 2
    fi
    if (( hi > 119 )); then
        echo "CPUS=$CPUS contains CPUs outside 0-119 (120-127 are reserved)" >&2; exit 2
    fi
done

check_marker() {
    if [[ -e $MARKER ]]; then
        echo "$MARKER exists: another team's timed run is active, stopping" >&2
        exit 3
    fi
}

check_marker
OUT=$HOME/cache-perf/results/$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
exec > >(tee -a "$OUT/log.txt") 2>&1
echo "results: $OUT"

# Bandwidth regimes. Copy uses two buffers per thread, so its thread list is
# capped separately to keep 2 x bytes x threads inside the level under test.
if (( QUICK )); then
    LAT_CPU=${CPUS%%[-,]*}   # first CPU of the list: a small host may lack CPU 3
    LAT_SIZES=4K,16K,64K,1M,8M
    LAT_REPS=1; LAT_MS=50; PERF_MS=50
    BW_REPS=1; BW_MS=50
    L1_THREADS="1 2"; L2_THREADS="1 2"
    L3_BYTES=8M; L3_RW_THREADS="1 2"; L3_COPY_THREADS="1"
    DRAM_SMALL_BYTES=64M; DRAM_SMALL_THREADS="1"
    DRAM_BYTES=32M; DRAM_THREADS="2"
else
    LAT_SIZES=4K,8K,16K,32K,48K,64K,96K,128K,256K,512K,1M,1.5M,2M,3M,4M,8M,16M,32M,64M,96M,128M,192M,256M,512M,1G,2G
    LAT_REPS=3; LAT_MS=300; PERF_MS=1000
    BW_REPS=3; BW_MS=500
    L1_THREADS="1 8 32 120"; L2_THREADS="1 8 32 120"
    # L3: 8 MiB per thread (4x the 2 MiB L2); 14 x 8 MiB = 112 MiB and
    # copy 7 x 2 x 8 MiB = 112 MiB both stay under the 128 MiB L3.
    L3_BYTES=8M; L3_RW_THREADS="1 2 4 8 12 14"; L3_COPY_THREADS="1 2 4 7"
    # DRAM: 1 GiB per thread (8x L3) for the small thread counts, where the
    # per-core number is read; 256 MiB per thread for the large ones.
    DRAM_SMALL_BYTES=1G; DRAM_SMALL_THREADS="1 2 4 8"
    DRAM_BYTES=256M; DRAM_THREADS="16 32 64 96 120"
fi

echo "== build"
make -C "$BENCH"

echo "== sysinfo"
{
    echo "## date"; date -u
    echo "## uname"; uname -a
    echo "## nproc"; nproc
    echo "## gcc"; gcc --version
    echo "## cmdline"; cat /proc/cmdline
    echo "## governor"; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo none
    echo "## thp"; cat /sys/kernel/mm/transparent_hugepage/enabled /sys/kernel/mm/transparent_hugepage/defrag || true
    echo "## lscpu"; lscpu
    echo "## cache sysfs (cpu0)"
    for d in /sys/devices/system/cpu/cpu0/cache/index*; do
        echo "$d: level=$(cat "$d/level") type=$(cat "$d/type") size=$(cat "$d/size") ways=$(cat "$d/ways_of_associativity") line=$(cat "$d/coherency_line_size") sets=$(cat "$d/number_of_sets") shared_cpu_list=$(cat "$d/shared_cpu_list")"
    done
    echo "## interrupts"; cat /proc/interrupts
} > "$OUT/sysinfo.txt" 2>&1

echo "== latency sweep (cpu $LAT_CPU)"
: > "$OUT/latency.csv"
for size in ${LAT_SIZES//,/ }; do
    check_marker
    "$BENCH/latency" --cpu "$LAT_CPU" --sizes "$size" --reps $LAT_REPS --min-ms $LAT_MS >> "$OUT/latency.csv"
done

# Two perf runs per size: "short" = exactly 2 timed cycles, "long" = at least
# PERF_MS and 6 cycles. Setup (first touch, permutation, warm-up) is identical
# in both, so count_long - count_short is the refills of the extra timed loads.
echo "== latency sweep under perf stat (short: 2 cycles; long: >= $PERF_MS ms and 6 cycles)"
PERF_EVENTS=l1d_cache_refill,l2d_cache_refill,l3d_cache_refill,ll_cache_miss_rd,dtlb_walk,cpu_cycles,inst_retired
if command -v perf >/dev/null; then
    : > "$OUT/latency-perfrun-short.csv"
    : > "$OUT/latency-perfrun-long.csv"
    for size in ${LAT_SIZES//,/ }; do
        check_marker
        if ! perf stat -x, -e "$PERF_EVENTS" -o "$OUT/latency-perf-$size-short.csv" -- \
                "$BENCH/latency" --cpu "$LAT_CPU" --sizes "$size" --reps 1 --min-ms 0 --min-cycles 2 \
                >> "$OUT/latency-perfrun-short.csv" ||
           ! perf stat -x, -e "$PERF_EVENTS" -o "$OUT/latency-perf-$size-long.csv" -- \
                "$BENCH/latency" --cpu "$LAT_CPU" --sizes "$size" --reps 1 --min-ms $PERF_MS --min-cycles 6 \
                >> "$OUT/latency-perfrun-long.csv"; then
            echo "perf stat failed for size $size; continuing"
        fi
    done
else
    echo "perf not found; skipping the perf run"
fi

echo "== bandwidth sweep (cpus $CPUS)"
: > "$OUT/bandwidth.csv"
run_bw() { # kernel bytes thread-list
    local kernel=$1 bytes=$2 t
    for t in $3; do
        check_marker
        echo "-- kernel $kernel bytes $bytes threads $t"
        "$BENCH/bandwidth" --threads "$t" --cpus "$CPUS" --bytes "$bytes" --kernel "$kernel" \
            --reps $BW_REPS --min-ms $BW_MS >> "$OUT/bandwidth.csv"
    done
}
run_bw all 32K "$L1_THREADS"
run_bw all 1M "$L2_THREADS"
run_bw read "$L3_BYTES" "$L3_RW_THREADS"
run_bw write "$L3_BYTES" "$L3_RW_THREADS"
run_bw copy "$L3_BYTES" "$L3_COPY_THREADS"
run_bw all "$DRAM_SMALL_BYTES" "$DRAM_SMALL_THREADS"
run_bw all "$DRAM_BYTES" "$DRAM_THREADS"

echo "== done"
echo "$OUT"
