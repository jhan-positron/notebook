#!/usr/bin/env bash
# Full single-thread latency sweep: 32 KiB to 4 GiB, local memory.
# Selects appropriate hugepage size per buffer size.
#
# Output: ptr_chase_full_<host>_<timestamp>.csv

set -eu

# ---- hugepage pool management ----
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
HUGE1G=/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages

WANT_2M=2048    # 2048 x 2 MiB = 4 GiB pool, plenty for 2M-page tests
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    echo "Restoring 2M pool: -> $ORIG_2M" >&2
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

echo "Reserving $WANT_2M 2M pages (was $ORIG_2M)..." >&2
sudo bash -c "echo $WANT_2M > $HUGE2M"

GOT_2M=$(cat "$HUGE2M")
FREE_2M=$(cat /sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages)
FREE_1G=$(cat /sys/kernel/mm/hugepages/hugepages-1048576kB/free_hugepages)
echo "Pools: 2M=$GOT_2M free=$FREE_2M | 1G free=$FREE_1G" >&2

if [ "$GOT_2M" -lt 1500 ]; then
    echo "ERROR: only $GOT_2M 2M pages allocated (wanted $WANT_2M)" >&2
    exit 1
fi
if [ "$FREE_1G" -lt 4 ]; then
    echo "ERROR: need at least 4 free 1G pages for 4G test, have $FREE_1G" >&2
    exit 1
fi

# ---- sweep ----
OUT="ptr_chase_full_$(hostname)_$(date +%Y%m%d_%H%M).csv"
echo "test,cpu,mem_node,size_bytes,hugepage,iters,median_ns,min_ns,max_ns,mean_ns,stddev_ns" > "$OUT"

run() {
    local sz="$1" hp="$2"
    echo "=== size=$sz hugepage=$hp ===" >&2
    ./ptr_chase --cpu 0 --mem-node 0 --size "$sz" --hugepage "$hp" \
                --iters 5 --min-walk-secs 0.5 --csv >> "$OUT"
}

# L1 / L2 region: 4K pages are fine
for sz in 32K 64K 128K 256K 512K 1M 2M; do
    run "$sz" none
done

# L3 region: 2M pages, no TLB-walk contamination
for sz in 4M 8M 16M 32M 48M 64M 96M 128M 192M 256M 384M 512M 768M; do
    run "$sz" 2m
done

# DRAM region: 1G pages
for sz in 1G 2G 4G; do
    run "$sz" 1g
done

echo "wrote $OUT" >&2
cat "$OUT"
