#!/bin/sh
# run_map.sh - the mesh latency map (run 8): the time of one dependent load from each CPU to each
# of the five home nodes (the mesh nodes that own an address; ids 88, 160, 216, 288, 344). It is
# measured for the node's OCM lines and for DRAM-backed lines held in the node's slice of the mesh
# cache (SLC). The earlier rows give the OCM cells from CPUs 2, 4, 6 and 8 only. Their SLC row is
# an average over the five nodes: a DRAM line's home node is a hash of its address, and no earlier
# program selects lines by node. The program meshmap finds the home node of each line of one
# 2 MiB page with the mesh counters (the classification). Then it times each node's lines alone.
#
# Runs as root under asimov-os, POSIX sh.
# Usage: sh run_map.sh [--quick] [--dry-run] [--out DIR] [--kernel-cpus]
# The first three options are in lib_run.sh. --kernel-cpus also measures from CPU 0, the kernel's
# CPU, in a last block after every other row is written. Needs a built tree (make). CPUs 2 to 9
# all stay online: the script brings CPU 3 back when an earlier script took it offline. On a boot
# that runs several scripts this one runs last, so a meshmap failure costs only its own rows.
#
# Phase M:
#   sysinfo   sysinfo-map.txt: the online CPUs, the kernel's CONFIG_PROC_PAGE_MONITOR line (the
#             option behind /proc/self/pagemap) and the CPU of the mesh PMU arm_cmn_0.
#   control   four rows of the existing latency program: the dense flushed OCM chain of 256 KiB
#             from CPUs 2 and 8 on regions 0 and 4 (the form of run_followup.sh G2), uncounted.
#             They are the same-boot reference for meshmap's ocm-flush cells.
#   meshmap   one process. It appends its rows to latency-map.csv itself and flushes every line,
#             so the rows written before a kill survive. A cell is one (kind, CPU, node): 7 timed
#             passes of 2,048 dependent loads, each pass over a different random chain on the
#             same lines. Kinds, in the order they run:
#               ocm-flush   OCM lines of the node. Per pass: DC CIVAC (the instruction that removes
#                           a line from the core's caches) on every line, timed chase. It needs
#                           no mesh counter, so it runs first.
#               idle        one row per CPU with zero loads: the background of the counters.
#                           It is written before the CPU's slc cells.
#               slc         DRAM lines of the node. Per pass: one store to every chain line, then
#                           the evictor (one load of every other line of the page, which pushes
#                           the chain lines out of the cluster's caches to the SLC), timed chase.
#               dram-flush  the same DRAM lines with the ocm-flush recipe. The load misses at the
#                           node and is fetched from DRAM.
#               ocm-evict   OCM lines with the slc recipe: the control of that recipe.
#             The mesh counters and the classification come after the ocm-flush cells. A part that
#             fails prints a "#" line and the later parts still run. meshmap exits 1 when a
#             requested cell is missing, which this script counts as a failed command.
#             meshmap opens the mesh counters itself. So it never runs under cmn or cmnq (the
#             lib_run.sh helpers that run a command under cmncount): cmncount would hold the
#             counters that meshmap needs.
# The reading rules are in README.md ("Reading rules for latency-map.csv"). The program applies
# none of them and drops no row.
# --quick (any Linux host): meshmap --selftest, then a small run with fake homes and without OCM.
# Chip time about 0.92 s (est.), about 43 min of wall time at 2,779 s per chip second:
# `sh run_map.sh --dry-run | python3 est_chip_time.py`. The evictor loads are 0.55 s of it (est.).

# --kernel-cpus is this script's own option. lib_run.sh exits 2 on an option it does not know, so
# the option is taken out of the arguments before lib_run.sh reads them.
KCPUS=0
for a in "$@"; do
    shift
    if [ "$a" = --kernel-cpus ]; then KCPUS=1; else set -- "$@" "$a"; fi
done

HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib_run.sh"
MM="$HERE/meshmap"
[ -x "$MM" ] || { echo "build first: make" >&2; exit 2; }
LAST=""
[ "$KCPUS" = 1 ] && LAST="--last-cpus 0"

say "# run_map.sh start $(date -u +%FT%TZ) quick=$QUICK out=$OUT kernel_cpus=$KCPUS"
cpu_set_online "$OFFLINE_CPU" 1

# ---- M. sysinfo (its own file: run_asimov.sh and run_l3.sh each rewrite sysinfo.txt) ----
[ "$DRY" = 1 ] || {
    echo "## online cpus"; cat /sys/devices/system/cpu/online 2>&1
    echo "## config: the option behind /proc/self/pagemap"
    zcat /proc/config.gz 2>/dev/null | grep PROC_PAGE_MONITOR || echo "config.gz unreadable (or it has no PROC_PAGE_MONITOR line)"
    echo "## arm_cmn_0 cpumask"; cat /sys/bus/event_source/devices/arm_cmn_0/cpumask 2>&1
} > "$OUT/sysinfo-map.txt" 2>&1
[ "$DRY" = 1 ] || say "sysinfo-map.txt written"

say "## M. mesh latency map: each CPU to each home node"
# The same-boot reference for the ocm-flush cells: the existing program's dense flushed OCM chain
# from CPUs 2 and 8 to regions 0 and 4. By the crosspoint coordinates these four cells are 1, 3, 5
# and 1 steps apart. Plain run, uncounted.
if [ "$HAVE_OCM" = 1 ]; then
    for c in 2 8; do
        for r in 0 4; do
            run latency-ocm-region$r-mapctl-cpu$c.csv "$LAT" --cpu $c --perf --mem ocm --ocm-regions $r --sizes 256K --fresh 3 --flush
        done
    done
fi

# meshmap writes latency-map.csv and map-homes.txt itself. Its stdout (progress and summary lines)
# goes to meshmap-log.txt. Plain run, never cmn or cmnq (see the header).
# shellcheck disable=SC2086
if [ "$QUICK" = 1 ]; then
    run meshmap-selftest.txt "$MM" --selftest
    run meshmap-log.txt "$MM" --no-perf --no-ocm --cpus $CPU --lines 256 --reps 3 --out "$OUT/latency-map.csv" --homes "$OUT/map-homes.txt" --nodes "$HNS" $LAST
else
    run meshmap-log.txt "$MM" --out "$OUT/latency-map.csv" --homes "$OUT/map-homes.txt" --nodes "$HNS" $LAST
fi

[ "$DRY" = 1 ] && exit 0
# Three lines for the console, since run does not echo a command's output: the counter level, the
# classification result and the cell count. Each is the last such line of the row file, cut to 120
# characters. A line that is not there is reported as missing.
mapline() { # <pattern> <what>
    l=$(grep -E "$1" "$OUT/latency-map.csv" 2>/dev/null | tail -n 1 | cut -c1-120)
    say "${l:-# run_map.sh: no $2 line in latency-map.csv}"
}
mapline '^# (mesh counters:|meshmap: no mesh counters)' "mesh counters"
mapline '^# classify: probed=' "classification"
mapline '^# meshmap: done' "done"
finish_suite run_map.sh
