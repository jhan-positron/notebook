#!/bin/sh
# run_followup.sh - the run 3 follow-ups (see follow-up-run-plan.md): the OCM chase rows and the
# CME latency sweep again with three more counters in each group (the refills the hardware
# prefetchers made), a third chain shape for the OCM rows, a translation counter set on the OCM
# rows from CPU 2, and a sequential chain as the prefetcher positive control. The same script is
# meant to run on more than one boot (the normal boot, then boots with the prefetchers disabled
# or OCM in larger pages, as the platform allows); each boot writes its own --out directory.
#
# Runs as root under asimov-os, POSIX sh. Usage: sh run_followup.sh [--quick] [--dry-run] [--out DIR]
# (options in lib_run.sh). Needs a built tree (make). The CME rows are skipped when
# /proc/cpuinfo has no sme2; the OCM rows when /dev/ocm is absent.
#
# Counter groups (common.h): the core prefetch set is cycles, 0x03 L1D refill, 0x17 L2D refill,
# 0xA2 L3D read refill, plus 0x81BC L1D_CACHE_REFILL_HWPRF, 0x81BD L2D_CACHE_REFILL_HWPRF and
# 0x0111 IMP_L2D_CACHE_REFILL_L1DHWPRF (refills a hardware prefetcher requested, by level and by
# prefetcher). The core TLB set (--events tlb) keeps the first four and adds 0x05 L1D_TLB_REFILL,
# 0x2D L2D_TLB_REFILL and 0x34 DTLB_WALK. The CME set is cycles, 0x3246 CME_CYCLES, 0x327D inner
# refills, 0x327E outer refills, plus 0x3280 CME_L1D_CACHE_REFILL_RD (refills by loads), 0x32B2
# CME_L1D_CACHE_REFILL_HWPRF (by the CME prefetcher) and 0x3281 CME_L1D_CACHE_REFILL_WR (by
# stores; the chase has none). An added event that is refused costs its own column only: the
# row keeps the run 3 columns and prints "-" in that one.
#
# Chain shapes (latency.c): dense = run 2's OCM chain, every line of a region (--fresh 3 --flush,
# 4,096 hops a pass); sparse = run 3's, one line per 4 KiB page at one fixed line per chain
# (--sparse --fresh 8 --flush, 64 hops a pass); vary = sparse with the line changing from page to
# page (--sparse-vary); seq = the lines in address order (--seq), the positive control.
#
# Phase G (CPU numbers as in run_asimov.sh; CPU 3 offline throughout so CPU 2 owns its DSU's
# L2, L3 and CME):
#   G0  sysinfo       as run_asimov.sh phase 0, plus the kernel command line and the PMU counter count
#   G1  core chase    the run 3 DRAM sweep (4 KiB to 32 MiB, repeated, fresh, flushed) on CPU 2,
#                     then the 8 MiB sequential chain, flushed (the positive control)
#   G2  core OCM      from CPUs 2 and 8 (1 and 5 crosspoints at most): run 3's 4 KiB control; each
#                     region dense, sparse and vary; all five dense and sparse. From CPU 2 the
#                     per-region rows again with the TLB set (-tlb files)
#   G3  CME chase     the run 3 CME DRAM sweep and controls (CPU 2 in streaming mode), then the
#                     8 MiB sequential chain through the CME
#   G4  CME OCM       each region dense, sparse and vary; all five dense and sparse
# No bandwidth rows and no mesh counters: the questions are about fills per load.
# Chip time: `sh run_followup.sh --dry-run | python3 est_chip_time.py` (est.; see the plan).

HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lib_run.sh"

say "# run_followup.sh start $(date -u +%FT%TZ) quick=$QUICK out=$OUT sme2=$HAVE_SME2 ocm=$HAVE_OCM"

# ---- G0. sysinfo ----
if [ "$DRY" != 1 ]; then
{
    echo "## date"; date -u +%FT%TZ; cat /proc/uptime
    echo "## kernel"; cat /proc/version 2>/dev/null
    echo "## cmdline"; cat /proc/cmdline 2>/dev/null
    echo "## cpuinfo"; cat /proc/cpuinfo 2>/dev/null
    echo "## cache topology (cpu$CPU)"
    for d in /sys/devices/system/cpu/cpu$CPU/cache/index*; do
        [ -d "$d" ] || continue
        echo "$d: level=$(cat $d/level) type=$(cat $d/type) size=$(cat $d/size) ways=$(cat $d/ways_of_associativity 2>/dev/null) line=$(cat $d/coherency_line_size 2>/dev/null) shared_cpu_list=$(cat $d/shared_cpu_list)"
    done
    echo "## meminfo"; grep -E 'MemTotal|MemFree|HugePages_|Hugepagesize|AnonHugePages' /proc/meminfo
    echo "## thp"; cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null
    echo "## dmesg timer/memory/sme/pmu"; dmesg 2>/dev/null | grep -iE 'arch_timer|timer\(s\) running|Memory:|hugepage|ocm|spm|cmn|sme|prefetch|perfevents|counters available' | head -40
    echo "## devices"; ls -l /dev/ocm /dev/asimov-spm 2>&1
    echo "## perf events"; ls /sys/bus/event_source/devices/ 2>/dev/null
    echo "## arm-cmn mesh map (needs CONFIG_DEBUG_FS)"
    grep -q ' /sys/kernel/debug debugfs' /proc/mounts 2>/dev/null || mount -t debugfs none /sys/kernel/debug 2>&1
    cat /sys/kernel/debug/arm-cmn/map* 2>&1
} > "$OUT/sysinfo.txt" 2>&1
say "sysinfo written"
say "ocm=$HAVE_OCM sme2=$HAVE_SME2 hugepages_free=$(grep HugePages_Free /proc/meminfo | awk '{print $2}')"
fi

cpu_set_online "$OFFLINE_CPU" 0

# ---- G1. the core DRAM sweep (cpu $CPU), with the prefetch-refill columns ----
# Run 3's rows: the 192 and 256 KiB rows mix L2, L3 and mesh service; the new columns say how
# many of their L1 and L2 fills the prefetchers made. The 4 KiB repeated row is the drift control
# against run 3's latency-dram-small.csv (same command). The sequential 8 MiB chain is the
# positive control: on a normal boot the prefetch columns must count on it and its latency must
# sit well below the flushed random chain's; on a prefetch-off boot both must vanish.
say "## G1. core DRAM latency (cpu $CPU)"
run latency-dram-small.csv "$LAT" --cpu $CPU --perf --loads 64K --reps 3 \
    --sizes 4K,8K,16K,24K,32K,48K,64K,96K,128K,192K,256K,384K
if [ "$QUICK" = 1 ]; then
    run latency-dram-large.csv "$LAT" --cpu $CPU --perf --fresh 3 --sizes 512K,1M,2M,4M
    run latency-dram-flushed.csv "$LAT" --cpu $CPU --perf --fresh 3 --flush --sizes 2M
    run latency-dram-seq.csv "$LAT" --cpu $CPU --perf --seq --fresh 3 --flush --sizes 2M
else
    run latency-dram-large.csv "$LAT" --cpu $CPU --perf --fresh 3 \
        --sizes 512K,768K,1M,1.5M,2M,3M,4M,6M,8M,16M,32M
    run latency-dram-flushed.csv "$LAT" --cpu $CPU --perf --fresh 3 --flush --sizes 8M
    run latency-dram-seq.csv "$LAT" --cpu $CPU --perf --seq --fresh 3 --flush --sizes 8M
fi

# ---- G2. core OCM chase, dense, sparse and vary, from CPUs 2 and 8 ----
# Dense per region: run 2's row (fresh=3, two timed passes of 4,096 hops), which counted 0.77 to
# 0.92 L3 read refills per load. Sparse per region: run 3's row (fresh=8, seven timed passes of
# 64 hops), which counted 0.61 to 0.83, fewer, so a prefetcher landed on sparse members more
# often, not less. Vary: the sparse chain with the line changing per page, the test of the
# hypothesis that the prefetcher carries the fixed line offset from page to page. The prefetch
# columns say which fills the prefetchers made; the -tlb rows from CPU 2 count the translation
# activity of the same three chains. CPU 2 sees the regions at 1 and 3 crosspoints, CPU 8 at
# 1, 3 and 5. The control is run 3's command, so its file compares directly.
if [ "$HAVE_OCM" = 1 ]; then
    for c in 2 8; do
        [ "$QUICK" = 1 ] && c=$CPU
        say "## G2. OCM latency (cpu $c)"
        run latency-control-cpu$c.csv "$LAT" --cpu $c --perf --no-thp --sizes 4K --loads 8K --reps 1
        for r in 0 1 2 3 4; do
            run latency-ocm-region$r-dense-cpu$c.csv "$LAT" --cpu $c --perf --mem ocm --ocm-regions $r --sizes 256K --fresh 3 --flush
            run latency-ocm-region$r-cpu$c.csv "$LAT" --cpu $c --perf --mem ocm --ocm-regions $r --sizes 256K --sparse --fresh 8 --flush
            run latency-ocm-region$r-vary-cpu$c.csv "$LAT" --cpu $c --perf --mem ocm --ocm-regions $r --sizes 256K --sparse-vary --fresh 8 --flush
        done
        run latency-ocm-all5-dense-cpu$c.csv "$LAT" --cpu $c --perf --mem ocm --ocm-regions 0,1,2,3,4 --sizes 1280K --fresh 3 --flush
        run latency-ocm-all5-cpu$c.csv "$LAT" --cpu $c --perf --mem ocm --ocm-regions 0,1,2,3,4 --sizes 1280K --sparse --fresh 8 --flush
        if [ "$c" = "$CPU" ]; then
            say "## G2. OCM latency, TLB counter set (cpu $c)"
            for r in 0 1 2 3 4; do
                run latency-ocm-region$r-dense-tlb-cpu$c.csv "$LAT" --cpu $c --perf --events tlb --mem ocm --ocm-regions $r --sizes 256K --fresh 3 --flush
                run latency-ocm-region$r-tlb-cpu$c.csv "$LAT" --cpu $c --perf --events tlb --mem ocm --ocm-regions $r --sizes 256K --sparse --fresh 8 --flush
                run latency-ocm-region$r-vary-tlb-cpu$c.csv "$LAT" --cpu $c --perf --events tlb --mem ocm --ocm-regions $r --sizes 256K --sparse-vary --fresh 8 --flush
            done
        fi
        [ "$QUICK" = 1 ] && break
    done
else
    say "## G2. OCM rows skipped: no /dev/ocm"
fi

# ---- G3, G4. the CME rows (cpu $CPU in streaming mode, CPU 3 offline) ----
# Run 3's CME sweep read 1.65 to 3.43 outer refills per load at 8 KiB and up to 16.9 near 128 to
# 256 KiB, more than one line fill per load. The new columns say whether those fills were
# loads (demand), the CME prefetcher's, or stores (none expected). The sequential chain is the
# CME prefetcher's positive control, as in G1.
if [ "$HAVE_SME2" = 1 ]; then
    say "## G3. CME DRAM latency (cpu $CPU)"
    run cme-latency-dram-small.csv "$LAT" --cme --cpu $CPU --perf --loads 64K --reps 3 \
        --sizes 4K,8K,16K,24K,32K,48K,64K,96K,128K,192K,256K,384K
    if [ "$QUICK" = 1 ]; then
        run cme-latency-dram-large.csv "$LAT" --cme --cpu $CPU --perf --fresh 3 --sizes 512K,1M,2M,4M
        run cme-latency-dram-flushed.csv "$LAT" --cme --cpu $CPU --perf --fresh 3 --flush --sizes 2M
        run cme-latency-dram-seq.csv "$LAT" --cme --cpu $CPU --perf --seq --fresh 3 --flush --sizes 2M
    else
        run cme-latency-dram-large.csv "$LAT" --cme --cpu $CPU --perf --fresh 3 \
            --sizes 512K,768K,1M,1.5M,2M,3M,4M,6M,8M,16M,32M
        run cme-latency-dram-flushed.csv "$LAT" --cme --cpu $CPU --perf --fresh 3 --flush --sizes 8M
        run cme-latency-dram-seq.csv "$LAT" --cme --cpu $CPU --perf --seq --fresh 3 --flush --sizes 8M
    fi
    if [ "$HAVE_OCM" = 1 ]; then
        say "## G4. CME OCM latency (cpu $CPU)"
        for r in 0 1 2 3 4; do
            run cme-latency-ocm-region$r-dense.csv "$LAT" --cme --cpu $CPU --perf --mem ocm --ocm-regions $r --sizes 256K --fresh 3 --flush
            run cme-latency-ocm-region$r.csv "$LAT" --cme --cpu $CPU --perf --mem ocm --ocm-regions $r --sizes 256K --sparse --fresh 8 --flush
            run cme-latency-ocm-region$r-vary.csv "$LAT" --cme --cpu $CPU --perf --mem ocm --ocm-regions $r --sizes 256K --sparse-vary --fresh 8 --flush
        done
        run cme-latency-ocm-all5-dense.csv "$LAT" --cme --cpu $CPU --perf --mem ocm --ocm-regions 0,1,2,3,4 --sizes 1280K --fresh 3 --flush
        run cme-latency-ocm-all5.csv "$LAT" --cme --cpu $CPU --perf --mem ocm --ocm-regions 0,1,2,3,4 --sizes 1280K --sparse --fresh 8 --flush
    fi
else
    say "## G3, G4. CME rows skipped: no sme2 in /proc/cpuinfo"
fi

cpu_set_online "$OFFLINE_CPU" 1
[ "$DRY" = 1 ] && exit 0
finish_suite run_followup.sh
