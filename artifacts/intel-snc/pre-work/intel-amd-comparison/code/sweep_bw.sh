#!/usr/bin/env bash
# sweep_bw.sh -- single-thread bandwidth sweep
#   Phase A: local memory, fine size grid, read + rmw
#   Phase B: cross-socket spot checks
#
# Output:
#   bw_sweep_<host>_<timestamp>.csv
#   bw_sweep_<host>_<timestamp>.log

set -u

# ===== Open log file FIRST, before anything that can fail =====
STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
OUT="bw_sweep_${HOST}_${STAMP}.csv"
LOG="bw_sweep_${HOST}_${STAMP}.log"
echo "test,cpu,mem_node,size_bytes,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"

exec > >(tee -a "$LOG") 2>&1

echo "===== sweep_bw started at $(date) ====="
echo "CSV output: $OUT"
echo "Log output: $LOG"
echo ""

# ---- hugepage pool management ----
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
WANT_2M=2048
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    echo "restoring 2M pool to $ORIG_2M"
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

echo "reserving $WANT_2M 2M pages (was $ORIG_2M)..."
sudo bash -c "echo $WANT_2M > $HUGE2M"
GOT_2M=$(cat "$HUGE2M")
FREE_2M=$(cat /sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages)
FREE_1G=$(cat /sys/kernel/mm/hugepages/hugepages-1048576kB/free_hugepages)
echo "pools: 2M=$GOT_2M free=$FREE_2M | 1G free=$FREE_1G"

if [ "$GOT_2M" -lt 1500 ]; then
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!! FATAL: only $GOT_2M 2M pages allocated (wanted $WANT_2M)"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "===== sweep_bw ABORTED at $(date) ====="
    exit 1
fi
if [ "$FREE_1G" -lt 4 ]; then
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!! FATAL: need >=4 free 1G pages, have $FREE_1G"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "===== sweep_bw ABORTED at $(date) ====="
    exit 1
fi

NPASS=0
NFAIL=0
FAILED_TESTS=()

TOOLS=/scratch/jhan/Intel_vs_AMD/tools/inspect_pages_n_ptr_chase

run() {
    local cpu="$1" memn="$2" sz="$3" hp="$4" pat="$5"
    local tag="cpu=$cpu mem=$memn size=$sz hp=$hp pat=$pat"
    echo ""
    echo "=== $tag ==="

    local tmp_out tmp_err
    tmp_out=$(mktemp)
    tmp_err=$(mktemp)

    "$TOOLS/bw_avx512" --cpu "$cpu" --mem-node "$memn" --size "$sz" \
        --hugepage "$hp" --pattern "$pat" \
        --iters 5 --min-walk-secs 0.5 --csv \
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
        echo "!!! stderr from bw_avx512:"
        sed 's/^/!!!   /' "$tmp_err"
        echo "!!! stdout was:"
        sed 's/^/!!!   /' "$tmp_out"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo ""
        printf "FAILED,%s,%s,%s,%s,%s,0,0,0,0,0,0\n" "$cpu" "$memn" "$sz" "$hp" "$pat" >> "$OUT"
        NFAIL=$((NFAIL+1))
        FAILED_TESTS+=("$tag (rc=$rc)")
    fi
    rm -f "$tmp_out" "$tmp_err"
}

# Phase A: local memory
echo ">>> Phase A: local memory bandwidth sweep"
for sz in 32K 64K 128K 256K 512K 1M 2M; do
    for pat in read rmw; do
        run 0 0 "$sz" none "$pat"
    done
done
for sz in 4M 8M 16M 32M 48M 64M 96M 128M 192M 256M 384M 512M 768M; do
    for pat in read rmw; do
        run 0 0 "$sz" 2m "$pat"
    done
done
for sz in 1G 2G 4G; do
    for pat in read rmw; do
        run 0 0 "$sz" 1g "$pat"
    done
done

# Phase B: cross-socket
echo ""
echo ">>> Phase B: cross-socket bandwidth spot checks"
for sz in 16M 256M 4G; do
    if [ "$sz" = "4G" ]; then hp=1g; else hp=2m; fi
    for pat in read rmw; do
        run 0 1 "$sz" "$hp" "$pat"
    done
done

echo ""
echo "===== sweep_bw FINISHED at $(date) ====="
echo "Passed: $NPASS"
echo "Failed: $NFAIL"
if [ "$NFAIL" -gt 0 ]; then
    echo ""
    echo "FAILED TESTS:"
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t"
    done
fi
echo ""
echo "CSV rows: $(wc -l < "$OUT")"
echo "wrote $OUT"
echo "log:   $LOG"
