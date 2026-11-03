#!/usr/bin/env bash
# run_sudo.sh - the root-only measurements. Run on CRB as:  sudo ./run_sudo.sh
# Root is needed for the mesh (CMN) counters: kernel.perf_event_paranoid is 2.
#   1. homelat self-test: 16 MiB buffer, core 3 only, 2048 lines per node as in the full run. Discovery must find 64 home nodes per
#      mesh, a 512-line re-check must agree 98 %, and 8 slices must show the expected cache
#      state (about 1 SLC access, 0 misses, 1 L2 refill per timed load). The tool aborts otherwise.
#   2. homelat full: 32 MiB buffer, every core 0-119 to every home node ("slice distance"); its
#      cache-state check (local-home residency, latency range, no multiplexing) is fatal, like part 1's;
#      chunks.csv says which mesh homes each 2 MiB chunk ("two mesh halves").
#   3. mesh-cache write bandwidth: home-node counters during asmwrite and asmread streams.
#      Two runs per case (short and long); the count difference divided by the byte difference
#      cancels buffer setup. Events in a run have different event ids, because two filter
#      variants of one id share a counter slot and get multiplexed (seen 2026-11-02 at 50 %).
#   4. DRAM write collapse: the same counters for 64 writers on one mesh versus 32 on each mesh.
#   5. single-core write path (2026-11-02, not in the default PARTS; note: dtc_cycles counted only ~6,500/s here, so it is not usable as a mesh clock): where is the 73 GB/s bound of one
#      writer? Core counters on CPU 2 (L1/L2 write allocation and write-back, bus writes), the flit and
#      credit-stall counters of CPU 2's crosspoint (x=1, y=3, node id 0x98, core port p1), and the
#      home-node queue occupancy on both meshes. Cases: one writer, partners 2+3 on one port, 2+4 on two
#      ports, 4 ports, and one reader as control.  Run:  sudo PARTS=5 ./run_sudo.sh   (about 6 min)
# PARTS selects what runs, e.g.  sudo PARTS=12 ./run_sudo.sh  runs the two homelat parts only.
# Shared-host rule: CPUs 0-119 only; every measurement is killed within 5 s if the RUNNING
# marker appears (guard below), and homelat checks the marker itself every second.
set -euo pipefail
if [[ -z ${_RUN_CRB_PINNED:-} ]]; then
    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"
fi
if [[ $(id -u) -ne 0 ]]; then echo "run as root: sudo $0" >&2; exit 4; fi
MARKER=/tmp/positron-perf.RUNNING
BENCH=$(cd "$(dirname "$0")" && pwd)
check_marker() { [[ -e $MARKER ]] && { echo "$MARKER exists: stopping" >&2; exit 3; }; return 0; }
# guard CMD...: runs CMD in its own process group, polls the marker every 5 s, and if it appears
# kills the whole group (perf and the bandwidth process under it) and exits 3. Worst case to stop:
# 5 s poll + 1 s grace. The kills and waits are guarded against set -e (reviewer's catch).
guard() {
    check_marker
    setsid "$@" & local pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        if [[ -e $MARKER ]]; then
            echo "$MARKER appeared: killing process group $pid ($1)" >&2
            kill -- -"$pid" 2>/dev/null || true; sleep 1; kill -9 -- -"$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            exit 3
        fi
        sleep 5 & wait $! || true
    done
    wait "$pid"
}
check_marker
HOME_DIR=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)
OUT=$HOME_DIR/cache-perf/results/sudo-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
trap 'chown -R "${SUDO_USER:-root}": "$OUT" "$BENCH" 2>/dev/null || true' EXIT
exec > >(tee -a "$OUT/log.txt") 2>&1
echo "results: $OUT"; date -u; uname -r
make -C "$BENCH"
H="$BENCH/homelat"; B="$BENCH/bandwidth"
PARTS=${PARTS:-1234}
part() { [[ $PARTS == *$1* ]]; }

part 1 && {
echo "== 1. homelat self-test (16 MiB, core 3)"; date -u
mkdir -p "$OUT/selftest"
guard "$H" --bytes 16M --cores 3 --reps 7 --verify-sample 256 --verify-slices 8 --out "$OUT/selftest"
echo "-- nodes per mesh:"; awk -F, 'NR>1{n[$1]++} END{for (m in n) print "mesh " m ": " n[m] " home nodes"}' "$OUT/selftest/nodes.csv"
echo "-- chunk split (contiguous, mesh0 lines, mesh1 lines, unknown):"; cat "$OUT/selftest/chunks.csv"
echo "-- cache state per slice:"; cat "$OUT/selftest/verify.csv"
}

part 2 && {
echo "== 2. homelat full (32 MiB, cores 0-119)"; date -u
mkdir -p "$OUT/full"
guard "$H" --bytes 32M --cores 0-119 --reps 7 --out "$OUT/full"
}

# counter runs: perf stat around a bandwidth run, short (0.2 s) and long (2 s) so that
# (long - short) counts / (long - short) bytes is the rate of the streaming loop alone.
# EV is a list of event names with distinct event ids; each is opened on both meshes.
counted() { # counted <csvfile> <tag> <events> -- bandwidth args
    local csv=$1 tag=$2 events=$3; shift 3
    local ev=""; for e in ${events//,/ }; do ev="$ev${ev:+,}arm_cmn_0/$e/,arm_cmn_1/$e/"; done
    for len in short long; do
        local ms=200; [[ $len == long ]] && ms=2000
        echo "-- $tag $len events $events args $*" >> "$csv"
        guard perf stat -a -x, -e "$ev" -o "$OUT/perf-$tag-$len-${events%%,*}.csv" -- "$B" "$@" --reps 1 --min-ms $ms >> "$csv"
        grep -v '^#' "$OUT/perf-$tag-$len-${events%%,*}.csv" | grep . >> "$csv"
    done
}
# event sets: distinct event ids per set (0x5 reqs, 0x3 fill, 0x1 miss, 0xd mc local, 0x3b mc remote, 0x2 access, 0x6 sf hit, 0xa eviction)
SETS="hns_pocq_reqs_recvd_write,hns_cache_fill_all hns_cache_miss_all,hns_mc_reqs_local_all hns_mc_reqs_remote_all,hns_slc_sf_cache_access_all hns_pocq_reqs_recvd_read,hns_sf_hit_all hns_slc_eviction_all_all,hns_pocq_reqs_recvd_hbt"

part 3 && {
echo "== 3. mesh-cache write bandwidth with home-node counters"; date -u
: > "$OUT/writebw.csv"
echo "-- background control, 2 s idle" >> "$OUT/writebw.csv"
for set in $SETS; do ev=""; for e in ${set//,/ }; do ev="$ev${ev:+,}arm_cmn_0/$e/,arm_cmn_1/$e/"; done
    guard perf stat -a -x, -e "$ev" -o "$OUT/perf-idle-${set%%,*}.csv" -- sleep 2; grep -v '^#' "$OUT/perf-idle-${set%%,*}.csv" | grep . >> "$OUT/writebw.csv"; done
for cfg in "asmwrite 8M 1" "asmwrite 8M 4" "asmwrite 8M 14" "asmwrite 1G 1" "asmwrite 1G 14" "asmread 8M 1" "asmread 8M 4" "asmread 8M 14" "asmread 1G 14"; do
    set -- $cfg; k=$1; bytes=$2; t=$3
    for set in $SETS; do
        counted "$OUT/writebw.csv" "$k-$bytes-$t" "$set" --threads $t --cpus 0-119 --bytes $bytes --kernel $k
    done
done
}

part 4 && {
echo "== 4. DRAM write collapse with writers on both meshes: home-node counters"; date -u
# followup3 (2026-11-02): 64 writers on mesh 0 alone write 394 GB/s, 32 on each mesh write 173 GB/s, reads do not collapse.
: > "$OUT/crossmesh.csv"
SETS4="hns_pocq_reqs_recvd_write,hns_pocq_retry_write hns_pocq_reqs_recvd_rnf,hns_mc_reqs_remote_all hns_pocq_reqs_recvd_ccgrn,hns_mc_reqs_local_all hns_sn_throttle_write,hns_mc_retries_remote_all"
echo "-- background control, 2 s idle" >> "$OUT/crossmesh.csv"
for set in $SETS4; do ev=""; for e in ${set//,/ }; do ev="$ev${ev:+,}arm_cmn_0/$e/,arm_cmn_1/$e/"; done
    guard perf stat -a -x, -e "$ev" -o "$OUT/perf-idle4-${set%%,*}.csv" -- sleep 2; grep -v '^#' "$OUT/perf-idle4-${set%%,*}.csv" | grep . >> "$OUT/crossmesh.csv"; done
for cfg in "asmwrite 0-63 64" "asmwrite 0-31,64-95 64" "asmread 0-31,64-95 64"; do
    set -- $cfg; k=$1; cpus=$2; t=$3
    for set in $SETS4; do
        counted "$OUT/crossmesh.csv" "cross-$k-${cpus//,/_}" "$set" --threads $t --cpus $cpus --bytes 256M --kernel $k
    done
done
}

# counted2 <csv> <tag> <label> <perf opts> <-e string> -- bandwidth args: like counted(), but the event
# string and the perf scope (-a, or -C 2 for the core PMU) are given in full.
counted2() {
    local csv=$1 tag=$2 label=$3 popts=$4 ev=$5; shift 5
    for len in short long; do
        local ms=200; [[ $len == long ]] && ms=2000
        echo "-- $tag $len set $label events $ev args $*" >> "$csv"
        guard perf stat $popts -x, -e "$ev" -o "$OUT/perf5-$tag-$len-$label.csv" -- "$B" "$@" --reps 1 --min-ms $ms >> "$csv"
        grep -v '^#' "$OUT/perf5-$tag-$len-$label.csv" | grep . >> "$csv"
    done
}

part 5 && {
echo "== 5. single-core write path: core, crosspoint and home-queue counters"; date -u
XP=0x98   # crosspoint of CPUs 2 and 3: x=1, y=3 (node id = x<<7 | y<<3), core port p1 [results/sudo-20261102T054936Z/core-positions.json, results/cmn-map.txt]
# every event name is checked in sysfs first; a missing name stops the part before any measurement
need_cmn="hns_qos_pocq_occupancy_write hns_qos_pocq_occupancy_all dtc_cycles mxp_n_dat_txflit_valid mxp_s_dat_txflit_valid mxp_e_dat_txflit_valid mxp_w_dat_txflit_valid mxp_n_dat_txflit_stall mxp_s_dat_txflit_stall mxp_e_dat_txflit_stall mxp_w_dat_txflit_stall mxp_p1_req_txflit_valid mxp_p1_rsp_txflit_valid mxp_p1_snp_txflit_valid mxp_p1_dat_txflit_valid mxp_p1_rsp_txflit_stall mxp_p1_dat_txflit_stall mxp_n_req_txflit_valid mxp_e_req_txflit_valid"
need_core="l1d_cache l1d_cache_refill l1d_cache_wb l2d_cache l2d_cache_refill l2d_cache_wb bus_access mem_access stall_backend_mem bus_cycles"
missing=""
for e in $need_cmn; do [[ -e /sys/bus/event_source/devices/arm_cmn_0/events/$e ]] || missing="$missing arm_cmn_0/$e"; done
for e in $need_core; do [[ -e /sys/bus/event_source/devices/armv8_pmuv3_0/events/$e ]] || missing="$missing armv8_pmuv3_0/$e"; done
if [[ -n $missing ]]; then echo "part 5: event names not in sysfs:$missing" >&2; exit 5; fi
for e in hns_qos_pocq_occupancy_write dtc_cycles mxp_n_dat_txflit_valid; do echo "event $e: $(cat /sys/bus/event_source/devices/arm_cmn_0/events/$e)"; done
# event sets. Mesh-wide sets open each name on both meshes (two names per set: distinct event ids 0x0f, 0x14, and the DTC cycle counter).
# Crosspoint sets are four events at XP 0x98 on mesh 0 (one crosspoint has four counters) plus the mesh-0 cycle counter.
# Core sets are six events on CPU 2 (six programmable counters). Raw ids: 0x41 L1D_CACHE_WR, 0x43 L1D_CACHE_REFILL_WR,
# 0x51 L2D_CACHE_WR, 0x53 L2D_CACHE_REFILL_WR, 0x61 BUS_ACCESS_WR, 0x67 MEM_ACCESS_WR (Arm architectural PMU event numbers).
xp() { local ev=""; for e in "$@"; do ev="$ev${ev:+,}arm_cmn_0/$e,bynodeid=1,nodeid=$XP/"; done; echo "$ev,arm_cmn_0/dtc_cycles/"; }
both() { local ev=""; for e in "$@"; do ev="$ev${ev:+,}arm_cmn_0/$e/,arm_cmn_1/$e/"; done; echo "$ev"; }
core() { local ev=""; for e in "$@"; do ev="$ev${ev:+,}armv8_pmuv3_0/$e/"; done; echo "$ev"; }
declare -A SET5 OPT5
SET5[occw]=$(both hns_qos_pocq_occupancy_write dtc_cycles);            OPT5[occw]="-a"
SET5[occa]=$(both hns_qos_pocq_occupancy_all hns_txdat_stall);          OPT5[occa]="-a"
if [[ ! -e /sys/bus/event_source/devices/arm_cmn_0/events/hns_txdat_stall ]]; then
    echo "part 5: hns_txdat_stall is not an event name here; the occa set counts occupancy_all alone" >&2
    SET5[occa]=$(both hns_qos_pocq_occupancy_all)
fi
SET5[xpdat]=$(xp mxp_n_dat_txflit_valid mxp_s_dat_txflit_valid mxp_e_dat_txflit_valid mxp_w_dat_txflit_valid);  OPT5[xpdat]="-a"
SET5[xpstall]=$(xp mxp_n_dat_txflit_stall mxp_s_dat_txflit_stall mxp_e_dat_txflit_stall mxp_w_dat_txflit_stall); OPT5[xpstall]="-a"
SET5[xpport]=$(xp mxp_p1_req_txflit_valid mxp_p1_rsp_txflit_valid mxp_p1_snp_txflit_valid mxp_p1_dat_txflit_valid); OPT5[xpport]="-a"
SET5[xpmix]=$(xp mxp_p1_rsp_txflit_stall mxp_p1_dat_txflit_stall mxp_n_req_txflit_valid mxp_e_req_txflit_valid);   OPT5[xpmix]="-a"
SET5[core1]=$(core l1d_cache l1d_cache_refill l1d_cache_wb l2d_cache l2d_cache_refill l2d_cache_wb);               OPT5[core1]="-C 2"
SET5[core2]=$(core event=0x41 event=0x43 event=0x51 event=0x53 event=0x61 event=0x67);                            OPT5[core2]="-C 2"
SET5[core3]=$(core bus_access mem_access stall_backend_mem bus_cycles cycles instructions);                        OPT5[core3]="-C 2"
ORDER5="occw occa xpdat xpstall xpport xpmix core1 core2 core3"
: > "$OUT/writepath.csv"
echo "-- background control, 2 s idle" >> "$OUT/writepath.csv"
for l in $ORDER5; do
    echo "-- idle set $l events ${SET5[$l]}" >> "$OUT/writepath.csv"
    guard perf stat ${OPT5[$l]} -x, -e "${SET5[$l]}" -o "$OUT/perf5-idle-$l.csv" -- sleep 2
    grep -v '^#' "$OUT/perf5-idle-$l.csv" | grep . >> "$OUT/writepath.csv"
done
for cfg in "w8M-c2 asmwrite 8M 1 2" "w1G-c2 asmwrite 1G 1 2" "w8M-c2c3 asmwrite 8M 2 2,3" "w8M-c2c4 asmwrite 8M 2 2,4" "w8M-c2c4c6c8 asmwrite 8M 4 2,4,6,8" "r8M-c2 asmread 8M 1 2"; do
    set -- $cfg; tag=$1; k=$2; bytes=$3; t=$4; cpus=$5
    for l in $ORDER5; do
        counted2 "$OUT/writepath.csv" "$tag" "$l" "${OPT5[$l]}" "${SET5[$l]}" --threads $t --cpus $cpus --bytes $bytes --kernel $k
    done
done
}
echo "== done"; date -u; echo "$OUT"
