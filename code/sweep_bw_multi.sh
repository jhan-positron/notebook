#!/usr/bin/env bash
# bw_multi scaling sweep: L3 region + DRAM region, threads 1..all.
# Single socket (mem-node 0); threads pulled from first-thread-of-core
# range for each system.
#
# Detect system: pick max thread count and CPU range based on hostname/CPU.
# We use first N logical CPUs which on both systems are the physical-core
# first-thread per /sys topology earlier.
#
# Output: bw_multi_<host>_<timestamp>.csv

set -eu

# detect max physical cores on socket 0
# both systems put socket 0's first-thread-per-core at CPUs 0..N-1
# Intel 6962P: 72 cores per socket → cpus 0-71 are socket 0
# AMD 9654:    96 cores per socket → cpus 0-95 are socket 0
SOCKET0_CORES=$(awk -F, 'NR>1{print $4}' /sys/devices/system/node/node0/cpulist 2>/dev/null || true)
# fallback: parse /sys/devices/system/node/node0/cpulist
CPULIST=$(cat /sys/devices/system/node/node0/cpulist)
echo "node0 cpulist: $CPULIST" >&2

# Use the LOW range of node0's cpulist as physical cores
# (e.g. "0-71,144-215" on Intel: take "0-71"; HT siblings excluded)
LOW_RANGE=$(echo "$CPULIST" | awk -F, '{print $1}')
MAX_CPU=$(echo "$LOW_RANGE" | awk -F- '{print $2}')
MAX_THREADS=$((MAX_CPU + 1))
echo "Will scale threads up to $MAX_THREADS (CPUs 0..$MAX_CPU)" >&2

# ---- hugepage pool ----
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
# Per-thread sizes: 4M for L3, 256M for DRAM
# Worst case: MAX_THREADS × 256M = up to 24 GB
# Add headroom -> WANT_2M
WANT_2M=$(( (MAX_THREADS * 256 / 2) + 256 ))   # extra 512 MiB headroom
echo "want 2M pages: $WANT_2M" >&2
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    echo "restoring 2M pool to $ORIG_2M" >&2
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

sudo bash -c "echo $WANT_2M > $HUGE2M"
GOT_2M=$(cat "$HUGE2M")
echo "2M pool: $GOT_2M" >&2
if [ "$GOT_2M" -lt $(( WANT_2M * 9 / 10 )) ]; then
    echo "ERROR: only got $GOT_2M 2M pages (wanted ~$WANT_2M)" >&2
    exit 1
fi

OUT="bw_multi_$(hostname)_$(date +%Y%m%d_%H%M).csv"
echo "test,nthreads,mem_node,size_per_thread,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"

run() {
    local cpus="$1" sz="$2" pat="$3"
    local nt=$(echo "$cpus" | awk -F- '{print $2 - $1 + 1}')
    echo "=== threads=$nt size/thr=$sz pattern=$pat ===" >&2
    ./bw_multi --cpus "$cpus" --mem-node 0 --size-per-thread "$sz" \
               --hugepage 2m --pattern "$pat" \
               --iters 5 --min-walk-secs 0.5 --csv >> "$OUT"
}

# pick thread counts to sample
# 1 first; then powers of 2; then several near max
declare -a THREAD_COUNTS=()
for n in 1 2 4 8 16 24 32 40 48 56 64; do
    if [ "$n" -le "$MAX_THREADS" ]; then
        THREAD_COUNTS+=("$n")
    fi
done
# add max if not already present
LAST=${THREAD_COUNTS[-1]}
if [ "$LAST" -lt "$MAX_THREADS" ]; then
    THREAD_COUNTS+=("$MAX_THREADS")
fi

echo "Thread counts: ${THREAD_COUNTS[*]}" >&2

# TEST 1: L3 saturation (4M per thread)
echo ">>> TEST 1: L3 saturation, 4M per thread" >&2
for n in "${THREAD_COUNTS[@]}"; do
    last=$((n - 1))
    for pat in read rmw; do
        run "0-$last" 4M "$pat"
    done
done

# TEST 2: DRAM saturation (256M per thread)
echo ">>> TEST 2: DRAM saturation, 256M per thread" >&2
for n in "${THREAD_COUNTS[@]}"; do
    last=$((n - 1))
    for pat in read rmw; do
        run "0-$last" 256M "$pat"
    done
done

echo "wrote $OUT" >&2
echo "rows: $(wc -l < "$OUT")" >&2
