#!/usr/bin/env bash
# 09_loaded_latency.sh -- Test 10: victim latency vs background memory load.
# Victim = ptr_chase on cpu 0 -> mem-node 0 (DRAM 1G, and L3 16M).
# Background = bw_multi on cpus 1..K -> mem-node 0 (32M/thread, read), running
# continuously while the victim is timed. Sweep K = 0,4,8,12,16,23.
# Shows the loaded-latency curve (the gap between unloaded latency and peak BW).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; PC="$HERE/../bin/ptr_chase"; BM="$HERE/../bin/bw_multi"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/loaded_lat_${HOST}_${STAMP}.csv"; LOG="$RESULTS/loaded_lat_${HOST}_${STAMP}.log"
echo "victim_ws,bg_threads,bg_cpus,median_ns,min_ns,max_ns,mean_ns,stddev_ns" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 09_loaded_latency $(date) ====="; echo "CSV: $OUT"
# Victim + background both target node 0, which exists in BOTH SNC modes (under
# SNC-OFF node 0 = the whole socket = the apple-to-apple pre-SNC3 comparison).
# Auto-detect and LOG the mode instead of refusing -- the SNC-OFF re-run is wanted.
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in
  0-5) MODE=SNC3 ;;
  0-1) MODE=SNC-OFF ;;
  *)   MODE="unknown($SNC)" ;;
esac
echo "node online=$SNC possible=$(cat /sys/devices/system/node/possible) -> running as $MODE (victim cpu0 + bg cpus1..K both -> node 0)"
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
HUGE2M_FREE=/sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages
ORIG=$(cat "$HUGE2M")
RESTORE_HUGE2M=0
HP2M=2m
BGPID=""
cleanup(){
  if [ -n "$BGPID" ]; then
    kill "$BGPID" 2>/dev/null
    wait "$BGPID" 2>/dev/null || true
    BGPID=""
  fi
  [ "$RESTORE_HUGE2M" -eq 1 ] && echo "$ORIG" | sudo -n tee "$HUGE2M" >/dev/null || true
}
trap cleanup EXIT
if echo 2048 | sudo -n tee "$HUGE2M" >/dev/null; then
  RESTORE_HUGE2M=1
else
  echo "WARN: failed to set 2M hugepages via sudo -n tee"
fi
FREE2M=$(cat "$HUGE2M_FREE")
if [ "$FREE2M" -lt 256 ]; then
  HP2M=none
  echo "WARN: only $FREE2M free 2M hugepages; using --hugepage none for tests that requested 2m"
else
  echo "2M hugepages free=$FREE2M; using --hugepage 2m where requested"
fi

probe(){ # victim_ws_label  size  hugepage  bg_K
  local lbl="$1"; local sz="$2"; local hp="$3"; local K="$4"
  BGPID=""
  local bgcpus="(none)"
  if [ "$K" -gt 0 ]; then
    bgcpus="1-$K"
    "$BM" --cpus "$bgcpus" --mem-node 0 --size-per-thread 32M --hugepage none --pattern read --iters 60 --min-walk-secs 0.5 >/dev/null 2>&1 &
    BGPID=$!
    sleep 2   # let background traffic reach steady state
  fi
  local to te; to=$(mktemp); te=$(mktemp)
  "$PC" --cpu 0 --mem-node 0 --size "$sz" --hugepage "$hp" --iters 5 --min-walk-secs 0.5 --csv >"$to" 2>"$te"; local rc=$?
  if [ -n "$BGPID" ]; then kill "$BGPID" 2>/dev/null; wait "$BGPID" 2>/dev/null; BGPID=""; fi
  if [ $rc -eq 0 ] && [ -s "$to" ]; then
    # ptr_chase CSV: test,cpu,mem_node,size_bytes,hugepage,iters,median,min,max,mean,stddev
    awk -v l="$lbl" -v k="$K" -v c="$bgcpus" -F, 'BEGIN{OFS=","}{print l,k,c,$7,$8,$9,$10,$11}' "$to" >>"$OUT"
    echo "  [$lbl] bg=$K ($bgcpus) -> median=$(awk -F, '{print $7}' "$to") ns"
  else
    printf '%s,%s,%s,0,0,0,0,0\n' "$lbl" "$K" "$bgcpus" >>"$OUT"; echo "  [$lbl] bg=$K FAIL rc=$rc"; sed 's/^/    /' "$te"
  fi
  rm -f "$to" "$te"; }

echo ">>> DRAM victim (1 GiB, mem-node 0) vs background load"
for K in 0 4 8 12 16 23; do probe DRAM_1G 1G 1g "$K"; done
echo ">>> L3 victim (16 MiB, mem-node 0) vs background load"
for K in 0 4 8 12 16 23; do probe L3_16M 16M $HP2M "$K"; done
echo "===== done $(date) ====="
echo "CSV: $OUT"
