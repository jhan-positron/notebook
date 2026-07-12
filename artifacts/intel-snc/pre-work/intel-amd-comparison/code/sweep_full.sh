#!/usr/bin/env bash
# sweep_full.sh -- full single-thread latency sweep.
#
# Phase 1: Local memory, sizes 32 KiB to 4 GiB (cpu 0 -> mem-node 0)
# Phase 2: Cross-socket DRAM (cpu 0 -> mem-node 1), sizes 1-4 GiB
#
# Picks hugepage size appropriate for each buffer size:
#   32K - 2M  -> 4K pages (none)
#   4M - 768M -> 2M pages
#   1G - 4G   -> 1G pages
#
# Output:
#   ptr_chase_full_<host>_<timestamp>.csv
#   ptr_chase_full_<host>_<timestamp>.log

set -u   # no 'e'; we handle failures per-test

# ===== Open log file FIRST, before anything that can fail =====
STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
OUT="ptr_chase_full_${HOST}_${STAMP}.csv"
LOG="ptr_chase_full_${HOST}_${STAMP}.log"
echo "test,cpu,mem_node,size_bytes,hugepage,iters,median_ns,min_ns,max_ns,mean_ns,stddev_ns" > "$OUT"

exec > >(tee -a "$LOG") 2>&1

echo "===== sweep_full started at $(date) ====="
echo "CSV output: $OUT"
echo "Log output: $LOG"
echo ""

# ---- hugepage pool management ----
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
HUGE1G=/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages

WANT_2M=2048
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    echo "Restoring 2M pool: -> $ORIG_2M"
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

echo "Reserving $WANT_2M 2M pages (was $ORIG_2M)..."
sudo bash -c "echo $WANT_2M > $HUGE2M"

GOT_2M=$(cat "$HUGE2M")
FREE_2M=$(cat /sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages)
FREE_1G=$(cat /sys/kernel/mm/hugepages/hugepages-1048576kB/free_hugepages)
echo "Pools: 2M=$GOT_2M free=$FREE_2M | 1G free=$FREE_1G"

if [ "$GOT_2M" -lt 1500 ]; then
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!! FATAL: only $GOT_2M 2M pages allocated (wanted $WANT_2M)"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "===== sweep_full ABORTED at $(date) ====="
    exit 1
fi
if [ "$FREE_1G" -lt 4 ]; then
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!! FATAL: need at least 4 free 1G pages for 4G test, have $FREE_1G"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "===== sweep_full ABORTED at $(date) ====="
    exit 1
fi

# ---- sweep setup ----
NPASS=0
NFAIL=0
FAILED_TESTS=()

TOOLS=/scratch/jhan/Intel_vs_AMD/tools/inspect_pages_n_ptr_chase

run() {
    local cpu="$1" memn="$2" sz="$3" hp="$4"
    local tag="cpu=$cpu mem=$memn size=$sz hugepage=$hp"
    echo ""
    echo "=== $tag ==="

    local tmp_out tmp_err
    tmp_out=$(mktemp)
    tmp_err=$(mktemp)

    "$TOOLS/ptr_chase" --cpu "$cpu" --mem-node "$memn" --size "$sz" \
        --hugepage "$hp" --iters 5 --min-walk-secs 0.5 --csv \
        > "$tmp_out" 2> "$tmp_err"
    local rc=$?

    if [ "$rc" -eq 0 ] && [ -s "$tmp_out" ]; then
        cat "$tmp_out" >> "$OUT"
        echo "OK"
        NPASS=$((NPASS+1))
    else
        echo ""
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "!!! TEST FAILED: $tag"
        echo "!!! exit code: $rc"
        echo "!!! stderr from ptr_chase:"
        sed 's/^/!!!   /' "$tmp_err"
        echo "!!! stdout was:"
        sed 's/^/!!!   /' "$tmp_out"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo ""
        printf "FAILED,%s,%s,%s,%s,0,0,0,0,0,0\n" "$cpu" "$memn" "$sz" "$hp" >> "$OUT"
        NFAIL=$((NFAIL+1))
        FAILED_TESTS+=("$tag (rc=$rc)")
    fi
    rm -f "$tmp_out" "$tmp_err"
}

# ===== Local memory sweep =====
echo ">>> Local memory sweep"

for sz in 32K 64K 128K 256K 512K 1M 2M; do
    run 0 0 "$sz" none
done

for sz in 4M 8M 16M 32M 48M 64M 96M 128M 192M 256M 384M 512M 768M; do
    run 0 0 "$sz" 2m
done

for sz in 1G 2G 4G; do
    run 0 0 "$sz" 1g
done

# ===== Cross-socket sweep =====
echo ""
echo ">>> Cross-socket sweep (cpu 0, mem-node 1)"
for sz in 1G 2G 4G; do
    run 0 1 "$sz" 1g
done

# ===== summary =====
echo ""
echo "===== sweep_full FINISHED at $(date) ====="
echo "Passed: $NPASS"
echo "Failed: $NFAIL"
if [ "$NFAIL" -gt 0 ]; then
    echo ""
    echo "FAILED TESTS:"
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t"
    done
    echo ""
    echo "Look in $LOG for captured stderr from each failed test."
fi
echo ""
echo "CSV rows total: $(wc -l < "$OUT") (incl header)"
echo "Expected: 1 header + 23 local + 3 cross-socket = 27 rows"
echo ""
echo "wrote $OUT"
echo "log:   $LOG"
