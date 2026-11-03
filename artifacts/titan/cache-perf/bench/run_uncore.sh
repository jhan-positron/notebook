#!/usr/bin/env bash
# run_uncore.sh - count CMN (mesh) system-level-cache events while the pointer
# chase runs at chosen footprints, to tell whether the sysfs "L3" is the mesh SLC
# and where its hits turn into DRAM reads.
# Needs kernel.perf_event_paranoid <= 0 (uncore PMUs are system-wide). The CMN
# PMU events are opened on the PMU's own cpumask CPU (cpu 0), not on every CPU,
# so no interrupt reaches CPUs 120-127.
# Same rules as run_crb.sh: CPUs 0-119 only, stops if the RUNNING marker appears.
set -euo pipefail
if [[ -z ${_RUN_CRB_PINNED:-} ]]; then
    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"
fi
MARKER=/tmp/positron-perf.RUNNING
BENCH=$(cd "$(dirname "$0")" && pwd)
check_marker() { [[ -e $MARKER ]] && { echo "$MARKER exists: stopping" >&2; exit 3; }; return 0; }
check_marker
P=$(cat /proc/sys/kernel/perf_event_paranoid)
if (( P > 0 )); then echo "perf_event_paranoid=$P; need <= 0" >&2; exit 4; fi
OUT=$HOME/cache-perf/results/uncore-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
exec > >(tee -a "$OUT/log.txt") 2>&1
echo "results: $OUT"
make -C "$BENCH"
EV=""
for c in 0 1; do
    for e in hns_slc_sf_cache_access_all hns_cache_miss_all hns_cache_fill_all hns_sf_hit_all hns_pocq_reqs_recvd_read hns_mc_reqs_local_all hns_mc_reqs_remote_all; do
        EV="$EV${EV:+,}arm_cmn_$c/$e/"
    done
done
echo "events: $EV"
# Two runs per size, like run_crb.sh: short (2 cycles) and long (6+ cycles, >= 1 s).
# count_long - count_short divided by loads_long - loads_short = events per load.
: > "$OUT/chase-short.csv"; : > "$OUT/chase-long.csv"
for s in 1M 8M 16M 32M 48M 64M 96M 128M 192M 256M 512M 1G; do
    check_marker
    perf stat -a -x, -e "$EV" -o "$OUT/cmn-$s-short.csv" -- \
        "$BENCH/latency" --cpu 3 --sizes $s --reps 1 --min-ms 0 --min-cycles 2 >> "$OUT/chase-short.csv"
    perf stat -a -x, -e "$EV" -o "$OUT/cmn-$s-long.csv" -- \
        "$BENCH/latency" --cpu 3 --sizes $s --reps 1 --min-ms 1000 --min-cycles 6 >> "$OUT/chase-long.csv"
done
# Streaming read, 14 threads x 8 MiB (the "L3 regime"): are the reads served by the SLC?
check_marker
perf stat -a -x, -e "$EV" -o "$OUT/cmn-bw-8M-14T.csv" -- \
    "$BENCH/bandwidth" --threads 14 --cpus 0-119 --bytes 8M --kernel read --reps 1 --min-ms 1000 > "$OUT/bw-8M-14T.csv"
check_marker
perf stat -a -x, -e "$EV" -o "$OUT/cmn-bw-256M-64T.csv" -- \
    "$BENCH/bandwidth" --threads 64 --cpus 0-119 --bytes 256M --kernel read --reps 1 --min-ms 1000 > "$OUT/bw-256M-64T.csv"
echo "== done"; echo "$OUT"
