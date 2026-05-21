#!/usr/bin/env bash
# A + B: single-thread bandwidth sweep
#   A: local memory, fine size grid, read + rmw (+ optional write)
#   B: cross-socket memory, spot checks at L3/x-CCD/DRAM sizes
#
# Output: bw_sweep_<host>_<timestamp>.csv

set -eu

# ---- hugepage pool management ----
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
WANT_2M=2048
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    echo "restoring 2M pool to $ORIG_2M" >&2
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

echo "reserving $WANT_2M 2M pages (was $ORIG_2M)..." >&2
sudo bash -c "echo $WANT_2M > $HUGE2M"
GOT_2M=$(cat "$HUGE2M")
FREE_2M=$(cat /sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages)
FREE_1G=$(cat /sys/kernel/mm/hugepages/hugepages-1048576kB/free_hugepages)
echo "pools: 2M=$GOT_2M free=$FREE_2M | 1G free=$FREE_1G" >&2

if [ "$GOT_2M" -lt 1500 ]; then
    echo "ERROR: only $GOT_2M 2M pages allocated (wanted $WANT_2M)" >&2
    exit 1
fi
if [ "$FREE_1G" -lt 4 ]; then
    echo "ERROR: need >=4 free 1G pages, have $FREE_1G" >&2
    exit 1
fi

# ---- output ----
OUT="bw_sweep_$(hostname)_$(date +%Y%m%d_%H%M).csv"
echo "test,cpu,mem_node,size_bytes,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"

run() {
    local cpu="$1" memn="$2" sz="$3" hp="$4" pat="$5"
    echo "=== cpu=$cpu mem-node=$memn size=$sz hp=$hp pat=$pat ===" >&2
    ./bw_avx512 --cpu "$cpu" --mem-node "$memn" --size "$sz" \
                --hugepage "$hp" --pattern "$pat" \
                --iters 5 --min-walk-secs 0.5 --csv >> "$OUT"
}

# ============================================================
# A: LOCAL MEMORY SWEEP (cpu 0, mem-node 0)
#    Matches latency sweep size grid for direct comparison.
# ============================================================

echo ">>> Phase A: local memory bandwidth sweep" >&2

# L1/L2 region: 4K pages fine
for sz in 32K 64K 128K 256K 512K 1M 2M; do
    for pat in read rmw; do
        run 0 0 "$sz" none "$pat"
    done
done

# L3 region: 2M pages
for sz in 4M 8M 16M 32M 48M 64M 96M 128M 192M 256M 384M 512M 768M; do
    for pat in read rmw; do
        run 0 0 "$sz" 2m "$pat"
    done
done

# DRAM region: 1G pages
for sz in 1G 2G 4G; do
    for pat in read rmw; do
        run 0 0 "$sz" 1g "$pat"
    done
done

# ============================================================
# B: CROSS-SOCKET SPOT CHECKS (cpu 0, mem-node 1)
#    Three sizes chosen to land in distinct cache regions
#    of the OWNING socket (mem-node 1).
# ============================================================

echo ">>> Phase B: cross-socket bandwidth spot checks" >&2

for sz in 16M 256M 4G; do
    if [ "$sz" = "4G" ]; then hp=1g; else hp=2m; fi
    for pat in read rmw; do
        run 0 1 "$sz" "$hp" "$pat"
    done
done

echo "wrote $OUT" >&2
echo "rows: $(wc -l < "$OUT") (incl header)" >&2
