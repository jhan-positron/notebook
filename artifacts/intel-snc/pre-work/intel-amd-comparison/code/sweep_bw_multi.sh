#!/usr/bin/env bash
# sweep_bw_multi.sh -- multi-thread bandwidth scaling sweep.
# TEST 1: L3 saturation (4M per thread)
# TEST 2: DRAM saturation (256M per thread)
# Threads 1 .. (physical cores per socket).
#
# Output:
#   bw_multi_<host>_<timestamp>.csv
#   bw_multi_<host>_<timestamp>.log

set -u

# ===== Open log file FIRST, before anything that can fail =====
STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
OUT="bw_multi_${HOST}_${STAMP}.csv"
LOG="bw_multi_${HOST}_${STAMP}.log"
echo "test,nthreads,mem_node,size_per_thread,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"

# Redirect everything from this point — even setup errors land in the log
exec > >(tee -a "$LOG") 2>&1

echo "===== sweep_bw_multi started at $(date) ====="
echo "CSV: $OUT"
echo "Log: $LOG"
echo ""

# ===== now do setup (with errors visible in log) =====
CPULIST=$(cat /sys/devices/system/node/node0/cpulist)
echo "node0 cpulist: $CPULIST"

LOW_RANGE=$(echo "$CPULIST" | awk -F, '{print $1}')
MAX_CPU=$(echo "$LOW_RANGE" | awk -F- '{print $2}')
MAX_THREADS=$((MAX_CPU + 1))
echo "Will scale threads up to $MAX_THREADS (CPUs 0..$MAX_CPU)"

HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
WANT_2M=$(( (MAX_THREADS * 256 / 2) + 256 ))
echo "want 2M pages: $WANT_2M (~$((WANT_2M * 2 / 1024)) GiB)"
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    echo "restoring 2M pool to $ORIG_2M"
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

sudo bash -c "echo $WANT_2M > $HUGE2M"
GOT_2M=$(cat "$HUGE2M")
echo "2M pool: GOT $GOT_2M (~$((GOT_2M * 2 / 1024)) GiB)"

if [ "$GOT_2M" -lt $(( WANT_2M * 9 / 10 )) ]; then
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!! FATAL: 2M page reservation insufficient"
    echo "!!! wanted: $WANT_2M, got: $GOT_2M"
    echo "!!! This is usually caused by memory pressure or"
    echo "!!! fragmentation. Check free physical memory."
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo ""
    echo "===== sweep_bw_multi ABORTED at $(date) ====="
    echo "No sweeps were run. Both CSV and LOG files exist for diagnostics."
    exit 1
fi

NPASS=0
NFAIL=0
FAILED_TESTS=()

TOOLS=/scratch/jhan/Intel_vs_AMD/tools/inspect_pages_n_ptr_chase

run() {
    local cpus="$1" sz="$2" pat="$3"
    local nt
    nt=$(echo "$cpus" | awk -F- '{print $2 - $1 + 1}')
    local tag="threads=$nt size/thr=$sz pattern=$pat"
    echo ""
    echo "=== $tag ==="

    local tmp_out tmp_err
    tmp_out=$(mktemp)
    tmp_err=$(mktemp)

    "$TOOLS/bw_multi" --cpus "$cpus" --mem-node 0 --size-per-thread "$sz" \
        --hugepage 2m --pattern "$pat" \
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
        echo "!!! stderr from bw_multi:"
        sed 's/^/!!!   /' "$tmp_err"
        echo "!!! stdout was:"
        sed 's/^/!!!   /' "$tmp_out"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo ""
        printf "FAILED,%s,0,%s,2m,%s,0,0,0,0,0,0\n" "$nt" "$sz" "$pat" >> "$OUT"
        NFAIL=$((NFAIL+1))
        FAILED_TESTS+=("$tag (rc=$rc)")
    fi
    rm -f "$tmp_out" "$tmp_err"
}

declare -a THREAD_COUNTS=()
for n in 1 2 4 8 16 24 32 40 48 56 64; do
    if [ "$n" -le "$MAX_THREADS" ]; then
        THREAD_COUNTS+=("$n")
    fi
done
LAST=${THREAD_COUNTS[-1]}
if [ "$LAST" -lt "$MAX_THREADS" ]; then
    THREAD_COUNTS+=("$MAX_THREADS")
fi
echo "Thread counts: ${THREAD_COUNTS[*]}"

echo ">>> TEST 1: L3 saturation, 4M per thread"
for n in "${THREAD_COUNTS[@]}"; do
    last=$((n - 1))
    for pat in read rmw; do
        run "0-$last" 4M "$pat"
    done
done

echo ""
echo ">>> TEST 2: DRAM saturation, 256M per thread"
for n in "${THREAD_COUNTS[@]}"; do
    last=$((n - 1))
    for pat in read rmw; do
        run "0-$last" 256M "$pat"
    done
done

echo ""
echo "===== sweep_bw_multi FINISHED at $(date) ====="
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
