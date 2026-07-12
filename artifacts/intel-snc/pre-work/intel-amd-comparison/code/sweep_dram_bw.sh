#!/usr/bin/env bash
# sweep_dram_bw.sh -- extended single-thread DRAM bandwidth sweep.
#
# Tests sizes from 4 GiB up to 32 GiB, both local and cross-socket.
# Uses 1 GiB hugepages exclusively.
#
# Note: 64 GiB was removed because it consistently triggered SIGBUS
# on the AMD test system. The 4G..32G data already shows DRAM BW
# is flat in this region, so the missing 64G point does not affect
# conclusions.
#
# Output:
#   bw_dram_<host>_<timestamp>.csv          measurement results
#   bw_dram_<host>_<timestamp>.log          stderr from each invocation
#                                           AND end-of-run summary

set -u   # NOTE: removed 'e'; we handle failures per-test instead

# ===== Open log file FIRST, before anything that can fail =====
STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
OUT="bw_dram_${HOST}_${STAMP}.csv"
LOG="bw_dram_${HOST}_${STAMP}.log"
echo "test,cpu,mem_node,size_bytes,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"

exec > >(tee -a "$LOG") 2>&1

echo "===== sweep_dram_bw started at $(date) ====="
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
    echo "===== sweep_dram_bw ABORTED at $(date) ====="
    exit 1
fi

NPASS=0
NFAIL=0
FAILED_TESTS=()

TOOLS=/scratch/jhan/Intel_vs_AMD/tools/inspect_pages_n_ptr_chase

run() {
    local cpu="$1" memn="$2" sz="$3" pat="$4"
    local tag="cpu=$cpu mem=$memn size=$sz pat=$pat"
    echo ""
    echo "=== $tag ==="

    # Capture stderr separately so we can inspect on failure.
    # stdout (CSV row) goes to a temp file then to the CSV.
    local tmp_out tmp_err
    tmp_out=$(mktemp)
    tmp_err=$(mktemp)

    "$TOOLS/bw_avx512" --cpu "$cpu" --mem-node "$memn" --size "$sz" \
        --hugepage 1g --pattern "$pat" \
        --iters 5 --min-walk-secs 0.5 --csv \
        > "$tmp_out" 2> "$tmp_err"
    local rc=$?

    if [ "$rc" -eq 0 ] && [ -s "$tmp_out" ]; then
        cat "$tmp_out" >> "$OUT"
        echo "OK ($(wc -l < "$tmp_out") row appended)"
        NPASS=$((NPASS+1))
    else
        echo ""
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "!!! TEST FAILED: $tag"
        echo "!!! exit code: $rc"
        echo "!!! stderr from bw_avx512:"
        echo "!!!"
        sed 's/^/!!!   /' "$tmp_err"
        echo "!!!"
        echo "!!! stdout (should be CSV but was empty or partial):"
        sed 's/^/!!!   /' "$tmp_out"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo ""
        # Insert FAILED marker row so the gap is visible in the CSV
        printf "FAILED,%s,%s,%s,1g,%s,0,0,0,0,0,0\n" "$cpu" "$memn" "$sz" "$pat" >> "$OUT"
        NFAIL=$((NFAIL+1))
        FAILED_TESTS+=("$tag (rc=$rc)")
    fi
    rm -f "$tmp_out" "$tmp_err"
}

# Local memory
echo ">>> Local memory DRAM BW sweep"
for sz in 4G 8G 16G 32G; do
    for pat in read rmw; do
        run 0 0 "$sz" "$pat"
    done
done

# Cross-socket
echo ""
echo ">>> Cross-socket DRAM BW sweep (cpu 0 on socket 0, memory on socket 1)"
for sz in 4G 16G; do
    for pat in read rmw; do
        run 0 1 "$sz" "$pat"
    done
done

# End-of-run summary always prints (no set -e)
echo ""
echo "===== sweep_dram_bw FINISHED at $(date) ====="
echo "Passed: $NPASS"
echo "Failed: $NFAIL"
if [ "$NFAIL" -gt 0 ]; then
    echo ""
    echo "FAILED TESTS:"
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t"
    done
    echo ""
    echo "Look in $LOG for the captured stderr from each failed test."
    echo "Look in $OUT for 'FAILED,...' marker rows in place of real data."
fi
echo ""
echo "CSV rows total: $(wc -l < "$OUT") (incl header)"
echo "Expected: 1 header + 12 data = 13 rows"
echo ""
echo "wrote $OUT"
echo "log:   $LOG"
