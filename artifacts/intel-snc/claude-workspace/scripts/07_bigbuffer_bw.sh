#!/usr/bin/env bash
# 07_bigbuffer_bw.sh -- Test 8: big-buffer DRAM-streaming BW, per-thread 100/500/1000 MB.
#
# Design note: the data-home node 0 has only ~3 GB conventional free (the 1G
# hugepage pool consumed it) and only 48 free 1G pages, so it cannot host
# 24 x (100..1000 MB) buffers. node 2 is the symmetric end-die of socket 0
# (cpus 48-71) with ~59 GB free, so Test 8 runs on mem-node 2. 4K pages are
# used so the exact 100/500/1000 MB sizes are representable (1G hugepages
# would round sub-GiB up to 1 GiB). 4K costs ~10% vs hugepages on streaming
# but uniformly across sizes, so the size-trend is preserved.
#
# Topologies (all -> mem-node 2):
#   LOCAL : cpus 48-71  (node 2's own cores, local-die big buffer)
#   XSOCK : cpus 72-95  (socket 1 cores, cross-socket big buffer)
#   1T    : single thread cpu 48 (per-core DRAM ceiling, via bw_avx512)
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; MULTI="$HERE/../bin/bw_multi"; ONE="$HERE/../bin/bw_avx512"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/bigbuf_${HOST}_${STAMP}.csv"; LOG="$RESULTS/bigbuf_${HOST}_${STAMP}.log"
echo "topology,test,nthreads,mem_node,size_per_thread,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 07_bigbuffer_bw $(date) ====="; echo "CSV: $OUT"
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in
  0-5) MODE=SNC3;    BIGNODE=2; LOCALCPUS="48-71"; LOCALLAB="LOCAL_die2" ;;
  0-1) MODE=SNC-OFF; BIGNODE=0; LOCALCPUS="48-71"; LOCALLAB="LOCAL_sock0" ;;
  *) echo "!!! unexpected SNC online=$SNC possible=$(cat /sys/devices/system/node/possible)"; exit 1 ;;
esac
echo "mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible))  big buffers -> mem-node $BIGNODE; LOCAL=$LOCALCPUS XSOCK=72-95 (1T=cpu48)"
if command -v numactl >/dev/null 2>&1; then
  echo "mem-node $BIGNODE free: $(numactl --hardware | grep "node $BIGNODE free")"
else
  echo "mem-node $BIGNODE free: $(awk '/MemFree/{print $4 " kB"}' /sys/devices/system/node/node$BIGNODE/meminfo)"
fi
NPASS=0; NFAIL=0; FAILED=()
runm(){ local lab="$1" cpus="$2" sz="$3" pat="$4"
  echo "  [$lab] cpus=$cpus size/thr=$sz pat=$pat (4K pages, mem-node $BIGNODE)"
  local to te; to=$(mktemp); te=$(mktemp)
  "$MULTI" --cpus "$cpus" --mem-node $BIGNODE --size-per-thread "$sz" --hugepage none --pattern "$pat" --iters 5 --min-walk-secs 0.5 --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then awk -v l="$lab" -F, 'BEGIN{OFS=","}{print l,$0}' "$to" >>"$OUT"; NPASS=$((NPASS+1))
  else printf 'FAILED,%s,0,%s,%s,none,%s,0,0,0,0,0,0\n' "$lab" "$BIGNODE" "$sz" "$pat" >>"$OUT"; NFAIL=$((NFAIL+1)); FAILED+=("$lab sz=$sz pat=$pat rc=$rc"); echo "    FAIL rc=$rc"; sed 's/^/    /' "$te"; fi
  rm -f "$to" "$te"; }
run1(){ local sz="$1" pat="$2"
  echo "  [1T] cpu=48 size=$sz pat=$pat (4K pages, mem-node $BIGNODE)"
  local to te; to=$(mktemp); te=$(mktemp)
  "$ONE" --cpu 48 --mem-node $BIGNODE --size "$sz" --hugepage none --pattern "$pat" --iters 5 --min-walk-secs 0.5 --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then awk -F, 'BEGIN{OFS=","}{print "1T_cpu48","bw_multi",1,$3,$4,$5,$6,$7,$8,$9,$10,$11}' "$to" >>"$OUT"; NPASS=$((NPASS+1))
  else printf 'FAILED,1T_cpu48,1,%s,%s,none,%s,0,0,0,0,0,0\n' "$BIGNODE" "$sz" "$pat" >>"$OUT"; NFAIL=$((NFAIL+1)); FAILED+=("1T sz=$sz pat=$pat rc=$rc"); echo "    FAIL rc=$rc"; sed 's/^/    /' "$te"; fi
  rm -f "$to" "$te"; }
for sz in 100M 500M 1000M; do
  echo ">>> size $sz"
  runm "$LOCALLAB" "$LOCALCPUS" "$sz" read; runm "$LOCALLAB" "$LOCALCPUS" "$sz" rmw
  runm XSOCK_s1  72-95 "$sz" read; runm XSOCK_s1  72-95 "$sz" rmw
  run1 "$sz" read
done
echo "===== done $(date)  pass=$NPASS fail=$NFAIL ====="
[ $NFAIL -gt 0 ] && { echo "FAILED:"; for t in "${FAILED[@]}"; do echo "  - $t"; done; }
echo "CSV: $OUT"
