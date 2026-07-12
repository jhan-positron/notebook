#!/usr/bin/env bash
# sweep_c2c.sh -- c2c_lat sweep
#   Phase D-1: dense scan, cpu 0 vs every other core on socket 0
#   Phase D-2: cross-socket spot checks
# All pairs measured with --mem-node 0 (line homed on socket 0).
#
# Output:
#   c2c_lat_<host>_<timestamp>.csv
#   c2c_lat_<host>_<timestamp>.log

set -u

CPULIST_N0=$(cat /sys/devices/system/node/node0/cpulist)
CPULIST_N1=$(cat /sys/devices/system/node/node1/cpulist)
LOW0=$(echo "$CPULIST_N0" | awk -F, '{print $1}')
LOW1=$(echo "$CPULIST_N1" | awk -F, '{print $1}')
MAX0=$(echo "$LOW0" | awk -F- '{print $2}')
MIN1=$(echo "$LOW1" | awk -F- '{print $1}')
MAX1=$(echo "$LOW1" | awk -F- '{print $2}')
echo "node0 first-thread range: $LOW0 (max=$MAX0)" >&2
echo "node1 first-thread range: $LOW1 (min=$MIN1 max=$MAX1)" >&2

STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
OUT="c2c_lat_${HOST}_${STAMP}.csv"
LOG="c2c_lat_${HOST}_${STAMP}.log"
echo "test,cpu_a,cpu_b,mem_node,iters,rounds,median_ns_rt,min_ns_rt,max_ns_rt,mean_ns_rt,stddev_ns_rt" > "$OUT"

NPASS=0
NFAIL=0
FAILED_TESTS=()

exec > >(tee -a "$LOG") 2>&1

echo "===== sweep_c2c started at $(date) ====="
echo "CSV: $OUT"
echo "Log: $LOG"
echo ""

TOOLS=/scratch/jhan/Intel_vs_AMD/tools/inspect_pages_n_ptr_chase

run() {
    local a="$1" b="$2" mn="$3"
    local tag="a=$a b=$b mn=$mn"
    echo "=== $tag ==="

    local tmp_out tmp_err
    tmp_out=$(mktemp)
    tmp_err=$(mktemp)

    "$TOOLS/c2c_lat" --cpu-a "$a" --cpu-b "$b" --mem-node "$mn" \
        --iters 5 --rounds 1000000 --csv \
        > "$tmp_out" 2> "$tmp_err"
    local rc=$?

    if [ "$rc" -eq 0 ] && [ -s "$tmp_out" ]; then
        cat "$tmp_out" >> "$OUT"
        NPASS=$((NPASS+1))
    else
        echo ""
        echo "!!! TEST FAILED: $tag  rc=$rc"
        echo "!!! stderr:"
        sed 's/^/!!!   /' "$tmp_err"
        echo ""
        printf "FAILED,%s,%s,%s,0,0,0,0,0,0,0\n" "$a" "$b" "$mn" >> "$OUT"
        NFAIL=$((NFAIL+1))
        FAILED_TESTS+=("$tag (rc=$rc)")
    fi
    rm -f "$tmp_out" "$tmp_err"
}

echo ">>> Phase D-1: dense scan, cpu 0 vs all of socket 0"
for b in $(seq 1 "$MAX0"); do
    run 0 "$b" 0
done

echo ""
echo ">>> Phase D-2: cross-socket spot checks"
for b in "$MIN1" "$((MIN1 + 16))" "$((MIN1 + 32))" "$MAX1"; do
    if [ "$b" -le "$MAX1" ]; then
        run 0 "$b" 0
    fi
done

echo ""
echo "===== sweep_c2c FINISHED at $(date) ====="
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
