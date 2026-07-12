#!/usr/bin/env bash
# sweep_dram_lat.sh -- extended single-thread DRAM latency sweep.
#
# Tests sizes from 4 GiB up to 32 GiB, both local and cross-socket.
# Uses 1 GiB hugepages exclusively.
#
# Note: 64 GiB was removed because it consistently triggered SIGBUS
# on the AMD test system (insufficient 1G hugepage budget combined
# with memory pressure). The 4G..32G data already shows the DRAM
# latency curve is flat in this region, so the missing 64G point
# does not affect conclusions.
#
# Output:
#   ptr_chase_dram_<host>_<timestamp>.csv
#   ptr_chase_dram_<host>_<timestamp>.log

set -u

# ===== Open log file FIRST, before anything that can fail =====
STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
OUT="ptr_chase_dram_${HOST}_${STAMP}.csv"
LOG="ptr_chase_dram_${HOST}_${STAMP}.log"
echo "test,cpu,mem_node,size_bytes,hugepage,iters,median_ns,min_ns,max_ns,mean_ns,stddev_ns" > "$OUT"

exec > >(tee -a "$LOG") 2>&1

echo "===== sweep_dram_lat started at $(date) ====="
echo "CSV output: $OUT"
echo "Log output: $LOG"
echo ""

HUGE1G_FREE=/sys/kernel/mm/hugepages/hugepages-1048576kB/free_hugepages
FREE_1G=$(cat "$HUGE1G_FREE")
echo "1G hugepages free: $FREE_1G"

NEED_1G=40   # need ~32 1G pages for largest test, plus headroom
if [ "$FREE_1G" -lt "$NEED_1G" ]; then
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!! FATAL: need at least $NEED_1G free 1G pages, have $FREE_1G"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "===== sweep_dram_lat ABORTED at $(date) ====="
    exit 1
fi

NPASS=0
NFAIL=0
FAILED_TESTS=()

TOOLS=/scratch/jhan/Intel_vs_AMD/tools/inspect_pages_n_ptr_chase

run() {
    local cpu="$1" memn="$2" sz="$3" iters="$4" walk="$5"
    local tag="cpu=$cpu mem=$memn size=$sz iters=$iters walk=${walk}s"
    echo ""
    echo "=== $tag ==="

    local tmp_out tmp_err
    tmp_out=$(mktemp)
    tmp_err=$(mktemp)

    "$TOOLS/ptr_chase" --cpu "$cpu" --mem-node "$memn" --size "$sz" \
        --hugepage 1g --iters "$iters" --min-walk-secs "$walk" --csv \
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
        printf "FAILED,%s,%s,%s,1g,%s,0,0,0,0,0\n" "$cpu" "$memn" "$sz" "$iters" >> "$OUT"
        NFAIL=$((NFAIL+1))
        FAILED_TESTS+=("$tag (rc=$rc)")
    fi
    rm -f "$tmp_out" "$tmp_err"
}

echo ">>> Local memory DRAM sweep"
run 0 0 4G  5 0.5
run 0 0 8G  5 0.5
run 0 0 16G 5 1.0
run 0 0 32G 3 1.5

echo ""
echo ">>> Cross-socket DRAM sweep (cpu 0 on socket 0, memory on socket 1)"
run 0 1 4G  5 0.5
run 0 1 16G 3 1.5

echo ""
echo "===== sweep_dram_lat FINISHED at $(date) ====="
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
echo "Expected: 1 header + 6 data = 7 rows"
echo ""
echo "wrote $OUT"
echo "log:   $LOG"
