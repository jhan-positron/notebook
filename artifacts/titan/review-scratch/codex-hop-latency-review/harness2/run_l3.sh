#!/bin/sh
# run_l3.sh - the L3-mode follow-up (follow-up-run-plan.md section 14). With the DSU L3 of CPUs 2-9
# in full mode (boot F1) one core's sequential read of a 32 MiB buffer runs 2.7 times faster than
# with the L3 in snoop-filter-only mode (run 3), at a footprint 128 times the L3. Boot E against
# boot C (one build, the L3 the one change) reads 2.7 times faster at 2 and 32 MiB with the same L1
# and L2 refills per line; the counted 2 MiB read of F1 puts 0.975 times run 3's requests on the
# home nodes. The random read chains of 1.5 MiB and above, the one-core writes and the controls
# repeat run 3 (asimov-c1nano-perf.html section 2.3). Three hypotheses, one phase each. The same
# script runs on four boots; the boot sets the condition and the rows are the same:
#   L3 on,  prefetchers on    boot F1's firmware    H1, H3; H2's reference
#   L3 off, prefetchers on    run 3's firmware      H1 and H3 with the L3 off
#   L3 on,  prefetchers off   boot F2's firmware    H2; H1 and H3 without the prefetcher
#   L3 off, prefetchers off   boot B's firmware     H2's L3-off side, the same build and options
#
# Runs as root under asimov-os, POSIX sh. Usage: sh run_l3.sh [--quick] [--dry-run] [--out DIR]
# (options in lib_run.sh). Needs a built tree (make). No OCM, SPM or CME row.
#
# Phase H (CPU numbers as in run_asimov.sh; CPU 3 offline for H1 and H2 so CPU 2 owns its DSU's
# L2 and L3, online for H3):
#   H0  sysinfo       as run_asimov.sh phase 0, plus the /dev/ocm module's IMP_CLUSTERPWRSTAT_EL1 file
#   H1  queue         hypothesis 1, more reads in flight per cluster: the one-core 32 MiB and 2 MiB
#                     sequential reads, the 32 MiB write and the 32 MiB random chain from CPU 2,
#                     each run twice: under the request set (lib_run.sh cmn: requests received per
#                     home node) and under the queue set (cmnq: the read occupancy of each home
#                     node's request queue, and the mesh cycles). (occupancy count << 12) over
#                     dtc_cycles is the mean number of active read entries at that node over the
#                     whole command, every process of the system included; summed over the five
#                     nodes it is the whole-command read-queue occupancy of the mesh. It does not
#                     select this core, demand against prefetch, or the timed passes. The chain, one
#                     load in flight, is the serialized comparison for the streams; the write is the
#                     control whose rate did not move. The reads run 8 and 64 passes so the timed
#                     passes take most of the command. A queue row is complete only when all five
#                     node rows and the cycle row are present with running time equal to enabled time.
#   H2  prefetchers   hypothesis 2, the prefetcher's requests are the ones that overlap more. The
#                     prefetchers are the core's hardware data prefetchers (the C1-Nano has several;
#                     each picks the cache its linefills go to, L1, L2 or L3; the DSU has none of its
#                     own). Run 3's one-core sweep, 16 KiB to 32 MiB, read kernel only, plus the
#                     32 MiB write (the rows of run_asimov.sh phase D): the prefetchers-off boots, L3 on
#                     against L3 off, say whether the L3 mode changes the rate without the prefetcher;
#                     boots B and D (an older build, --perf on) read 2.38 GB/s at 32 MiB with both off.
#                     Then three counted rows on CPU 2: the 32 MiB read under the prefetch-refill set
#                     (--perf: the L1 and L2 refills the prefetchers requested, per line, on this build)
#                     and the 2 MiB and 32 MiB reads under the prefetch-target set (--perf --events pf:
#                     the L2 and L3 accesses by prefetchers targeting that level and the demand reads
#                     that first hit a line a prefetcher placed in the L3). 0x8156 counts the access,
#                     not a fill: the DSU counts a prefetch whose stash is not performed because the L3
#                     is off as a prefetch access, so it may read nonzero on either L3 mode. 0x81E6 is
#                     the one column that says a line was in the L3 and found. A column that never reads
#                     nonzero on any boot is unvalidated; a 0 where 0 is expected is a consistency
#                     check only. A nonzero 0x81E6 on the L3-on boots and 0 on the L3-off boots would
#                     be the observation that the prefetched lines are found in the L3. Then the 2 MiB
#                     and 32 MiB reads under the last-level-cache set (--perf --events llc: 0x36
#                     LL_CACHE_RD, 0x37 LL_CACHE_MISS_RD, 0x400B L3D_CACHE_LMISS_RD), a candidate
#                     count of the lines fetched from outside the cluster under each L3 mode, which
#                     0xA2 has not established for this stream (0xA2 read about 0 per line on boot C,
#                     where every line came from outside; its population is an interpretation). What
#                     0x36 and 0x37 count depends on IMP_CPUECTLR_EL1.EXTLLC and the caches present:
#                     returns from outside the cluster with EXTLLC set and no L3 present; the L3's
#                     own read accesses and refills (0xA0's and 0xA2's populations) with EXTLLC clear
#                     and an L2 and L3 present; another source in other configurations, to be
#                     identified from the RTL's selection. 0x400B is 0xA2's signal in this RTL. The
#                     columns are reported with EXTLLC's value and the selected source. Once the
#                     external source is shown selected, they are the selected external-source
#                     counts per program line; they become the total of lines fetched from outside
#                     the cluster only with separate evidence of which demand and prefetch
#                     populations the event includes. Until then that total is Insufficient data.
#   H3  per cluster   hypothesis 3, a per-cluster limit: 16 MiB sequential reads with one reader
#                     (CPU 2), two readers in one cluster (CPUs 2,3), two readers in two clusters
#                     (CPUs 2,4 and 2,8), four readers in two clusters (2,3,4,5 and 2,3,8,9) and four
#                     readers in four clusters (2,4,6,8), each under the queue set. Two readers in one
#                     cluster well below two readers in two clusters, by more than the reps' spread,
#                     shows a limit shared inside the cluster; equal rates show no sharing at that
#                     load and do not locate the limit.
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
        for e in $(echo "$CMN_PER_NODE,$CMN_GLOBAL,$CMN_Q_PER_NODE,$CMN_Q_GLOBAL" | tr ',' ' '); do
            printf '%s: ' "$e"; cat "$P/events/$e" 2>&1
        done
        echo "## arm_cmn_0 format"; for f in "$P"/format/*; do printf '%s: ' "$(basename $f)"; cat "$f"; done
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

# ---- H1. the home nodes' request queues (cpu $CPU) ----
say "## H1. requests and read-queue occupancy at the home nodes (cpu $CPU)"
for set in cmn cmnq; do
    run latency-chain-32M.csv $set "$set-chain-32M-cpu$CPU" "$LAT" --cpu $CPU --perf --fresh 3 --sizes 32M
    run bandwidth-queue.csv $set "$set-read-32M-cpu$CPU" "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel read --passes 8 --reps 3
    run bandwidth-queue.csv $set "$set-read-2M-cpu$CPU" "$BW" --threads 1 --cpus $CPU --bytes 2M --kernel read --passes 64 --reps 3
    run bandwidth-queue.csv $set "$set-write-32M-cpu$CPU" "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel write --passes 8 --reps 3
done

# ---- H2. run 3's one-core sweep, read kernel (cpu $CPU) ----
say "## H2. one-core read sweep, run 3's rows (cpu $CPU)"
for sp in 16K:256 48K:128 96K:64 256K:32 2M:4 32M:2; do
    s=${sp%%:*}; p=${sp##*:}
    run bandwidth-dram-1core.csv "$BW" --threads 1 --cpus $CPU --bytes $s --kernel read --passes $p --reps 3
done
run bandwidth-dram-1core.csv "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel write --passes 2 --reps 3
run bandwidth-read-prefetch.csv "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel read --passes 2 --reps 3 --perf
run bandwidth-read-pftarget.csv "$BW" --threads 1 --cpus $CPU --bytes 2M --kernel read --passes 4 --reps 3 --perf --events pf
run bandwidth-read-pftarget.csv "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel read --passes 2 --reps 3 --perf --events pf
run bandwidth-read-outside.csv "$BW" --threads 1 --cpus $CPU --bytes 2M --kernel read --passes 4 --reps 3 --perf --events llc
run bandwidth-read-outside.csv "$BW" --threads 1 --cpus $CPU --bytes 32M --kernel read --passes 2 --reps 3 --perf --events llc

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
