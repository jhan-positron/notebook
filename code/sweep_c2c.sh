#!/usr/bin/env bash
# c2c_lat sweep:
#   Phase D-1: dense scan, cpu 0 vs every other core on socket 0
#   Phase D-2: cross-socket spot checks
# All pairs measured with --mem-node 0 (line homed on socket 0).
set -eu

# detect cpus
CPULIST_N0=$(cat /sys/devices/system/node/node0/cpulist)
CPULIST_N1=$(cat /sys/devices/system/node/node1/cpulist)
LOW0=$(echo "$CPULIST_N0" | awk -F, '{print $1}')
LOW1=$(echo "$CPULIST_N1" | awk -F, '{print $1}')
MAX0=$(echo "$LOW0" | awk -F- '{print $2}')
MIN1=$(echo "$LOW1" | awk -F- '{print $1}')
MAX1=$(echo "$LOW1" | awk -F- '{print $2}')

echo "node0 first-thread range: $LOW0 (max=$MAX0)" >&2
echo "node1 first-thread range: $LOW1 (min=$MIN1 max=$MAX1)" >&2

OUT="c2c_lat_$(hostname)_$(date +%Y%m%d_%H%M).csv"
echo "test,cpu_a,cpu_b,mem_node,iters,rounds,median_ns_rt,min_ns_rt,max_ns_rt,mean_ns_rt,stddev_ns_rt" > "$OUT"

run() {
    local a="$1" b="$2" mn="$3"
    echo "=== a=$a b=$b mn=$mn ===" >&2
    ./c2c_lat --cpu-a "$a" --cpu-b "$b" --mem-node "$mn" \
              --iters 5 --rounds 1000000 --csv >> "$OUT"
}

# Phase D-1: dense scan within socket 0
echo ">>> Phase D-1: dense scan, cpu 0 vs all of socket 0" >&2
for b in $(seq 1 "$MAX0"); do
    run 0 "$b" 0
done

# Phase D-2: cross-socket spot checks
echo ">>> Phase D-2: cross-socket spot checks" >&2
for b in "$MIN1" "$((MIN1 + 16))" "$((MIN1 + 32))" "$MAX1"; do
    if [ "$b" -le "$MAX1" ]; then
        run 0 "$b" 0      # line on node 0, peer on node 1
    fi
done

echo "wrote $OUT" >&2
echo "rows: $(wc -l < "$OUT")" >&2
