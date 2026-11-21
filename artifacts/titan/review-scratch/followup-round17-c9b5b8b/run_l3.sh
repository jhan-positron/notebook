#!/bin/sh
# run_l3.sh - the L3-mode follow-up (follow-up-run-plan.md section 14). With the DSU L3 of CPUs 2-9
# in full mode (boot F1) the one-core sequential read of a 32 MiB buffer reads 2.7 times faster
# than with the L3 in snoop-filter-only mode (run 3), while the random read chains, the write
# streams, the refills per line and the requests at the home nodes do not move
# (asimov-c1nano-perf.html section 2.3). Three hypotheses, one phase each. The same script runs on
# three boots; the boot sets the condition and the rows are the same:
#   L3 on,  prefetchers on    boot F1's firmware    H1's L3-on side, H3, H2's reference
#   L3 off, prefetchers on    run 3's firmware      H1's L3-off side, H3 with the L3 off
#   L3 on,  prefetchers off   boot F2's firmware    H2
#
# Runs as root under asimov-os, POSIX sh. Usage: sh run_l3.sh [--quick] [--dry-run] [--out DIR]
# (options in lib_run.sh). Needs a built tree (make). No OCM, SPM or CME row.
#
# Phase H (CPU numbers as in run_asimov.sh; CPU 3 offline for H1 and H2 so CPU 2 owns its DSU's
# L2 and L3, online for H3):
#   H0  sysinfo       as run_asimov.sh phase 0, plus the /dev/ocm module's IMP_CLUSTERPWRSTAT_EL1 file
#   H1  in flight     hypothesis 1, more reads in flight per cluster: the one-core 32 MiB and 2 MiB
#                     sequential reads, the 32 MiB write and the 32 MiB random chain from CPU 2, each
#                     under the mesh queue set (lib_run.sh cmnq): per home node the read occupancy of
#                     its request queue, and over all nodes the mesh cycles, the requests received
#                     and the occupancy of every request type. Occupancy over cycles is the mean
#                     number of requests waiting at the node, so the five read rows summed give the
#                     mean number of this core's reads in flight at the home nodes. The chain is the
#                     calibration: one load in flight, so its sum should read about 1 over the timed
#                     passes (the chain build and the buffer fill dilute it, as every count covers
#                     the whole command). The reads run 8 and 64 passes so the timed passes dominate
#                     the command. The write row is the control whose rate did not move.
#   H2  prefetchers   hypothesis 2, the prefetcher's requests are the ones that overlap more: run 3's
#                     one-core sweep, 16 KiB to 32 MiB, read kernel only, plus the 32 MiB write (the
#                     rows of run_asimov.sh phase D). On the prefetchers-off boot with the L3 on a
#                     32 MiB read near boot B's 2.4 GB/s says the rise needs the prefetcher; a rate
#                     well above it says the L3 path overlaps demand misses on its own. On the other
#                     two boots the rows repeat run 3's and F1's.
#   H3  per cluster   hypothesis 3, a per-cluster limit: 16 MiB sequential reads with one reader
#                     (CPU 2), two readers in one cluster (CPUs 2,3), two readers in two clusters
#                     (CPUs 2,4 and 2,8), four readers in two clusters (2,3,4,5 and 2,3,8,9) and four
#                     readers in four clusters (2,4,6,8), each under the queue set. If two readers in
#                     one cluster read about one reader's rate together while two readers in two
#                     clusters read twice that, the limit is per cluster.
# Chip time: `sh run_l3.sh --dry-run | python3 est_chip_time.py` (est.; see the plan).

HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib_run.sh"

say "# run_l3.sh start $(date -u +%FT%TZ) quick=$QUICK out=$OUT"

# ---- H0. sysinfo ----
[ "$DRY" = 1 ] || {
    echo "## date"; date -u; cat /proc/uptime
    echo "## uname"; uname -a
    echo "## cmdline"; cat /proc/cmdline 2>/dev/null
    echo "## online cpus"; cat /sys/devices/system/cpu/online 2>/dev/null
    echo "## cpuinfo"; cat /proc/cpuinfo 2>/dev/null
    echo "## cache topology (cpu$CPU)"
    for d in /sys/devices/system/cpu/cpu$CPU/cache/index*; do
        [ -d "$d" ] || continue
        echo "$d: level=$(cat $d/level) type=$(cat $d/type) size=$(cat $d/size) ways=$(cat $d/ways_of_associativity 2>/dev/null) line=$(cat $d/coherency_line_size 2>/dev/null) shared_cpu_list=$(cat $d/shared_cpu_list)"
    done
    echo "## meminfo"; grep -E 'MemTotal|MemFree|HugePages_|Hugepagesize|AnonHugePages' /proc/meminfo
    echo "## thp"; cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null
    echo "## dmesg timer/memory/pmu"; dmesg 2>/dev/null | grep -iE 'arch_timer|timer\(s\) running|Memory:|hugepage|ocm|cmn|prefetch|perfevents|counters available' | head -40
    echo "## clusterpwrstat (IMP_CLUSTERPWRSTAT_EL1 of CPU 2's cluster, read by the /dev/ocm module)"
    cat /sys/module/membench_ocm/parameters/clusterpwrstat 2>&1
    echo "## perf events"; ls /sys/bus/event_source/devices/ 2>/dev/null
    echo "## arm_cmn_0"
    P=/sys/bus/event_source/devices/arm_cmn_0
    if [ -d "$P" ]; then
        echo "type=$(cat $P/type) cpumask=$(cat $P/cpumask) events=$(ls $P/events | wc -l)"
        for e in $(echo "$CMN_Q_PER_NODE,$CMN_Q_GLOBAL" | tr ',' ' '); do
            printf '%s: ' "$e"; cat "$P/events/$e" 2>&1
        done
        echo "## arm_cmn_0 events (all)"; ls "$P/events"
    else
        echo "absent"
    fi
    echo "## arm-cmn mesh map (needs CONFIG_DEBUG_FS)"
    grep -q ' /sys/kernel/debug debugfs' /proc/mounts 2>/dev/null || mount -t debugfs none /sys/kernel/debug 2>&1
    cat /sys/kernel/debug/arm-cmn/map* 2>&1
} > "$OUT/sysinfo.txt" 2>&1
say "sysinfo written"
say "hugepages_free=$(grep HugePages_Free /proc/meminfo | awk '{print $2}')"

cpu_set_online "$OFFLINE_CPU" 0

# ---- H1. requests in flight at the home nodes (cpu $CPU) ----
say "## H1. requests in flight at the home nodes (cpu $CPU)"
run latency-chain-32M.csv cmnq "chain-32M-cpu$CPU" "$LAT" --cpu $CPU --perf --fresh 3 --sizes 32M
run bandwidth-inflight.csv cmnq "read-32M-cpu$CPU" "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel read --passes 8 --reps 3
run bandwidth-inflight.csv cmnq "read-2M-cpu$CPU" "$BW" --threads 1 --cpus $CPU --bytes 2M --kernel read --passes 64 --reps 3
run bandwidth-inflight.csv cmnq "write-32M-cpu$CPU" "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel write --passes 8 --reps 3

# ---- H2. run 3's one-core sweep, read kernel (cpu $CPU) ----
say "## H2. one-core read sweep, run 3's rows (cpu $CPU)"
for sp in 16K:256 48K:128 96K:64 256K:32 2M:4 32M:2; do
    s=${sp%%:*}; p=${sp##*:}
    run bandwidth-dram-1core.csv "$BW" --threads 1 --cpus $CPU --bytes $s --kernel read --passes $p --reps 3
done
run bandwidth-dram-1core.csv "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel write --passes 2 --reps 3

# ---- H3. 16 MiB readers by placement ----
cpu_set_online "$OFFLINE_CPU" 1
say "## H3. 16 MiB sequential readers by placement"
if [ "$QUICK" = 1 ]; then SETS="$CPU $PAIR"; else SETS="2 2,3 2,4 2,8 2,3,4,5 2,3,8,9 2,4,6,8"; fi
for cp in $SETS; do
    n=$(echo "$cp" | tr ',' '-')
    t=$(echo "$cp" | tr ',' '\n' | wc -l)
    run bandwidth-read-cpus$n.csv cmnq "read-cpus$n" "$BW" --threads $t --cpus $cp --bytes 16M --kernel read --passes 2 --reps 3
done

[ "$DRY" = 1 ] && exit 0
finish_suite run_l3.sh
