#!/usr/bin/env bash
# 08_thread_scaling.sh -- Test 9: aggregate BW vs thread count (SNC3).
# bw_multi, cpus 0..N-1 -> mem-node 0, two regimes:
#   L3   : 4M/thread  (cache-resident; N=1..72, spans socket 0's 3 dies as N grows)
#   DRAM : 64M/thread (DRAM-bound; N=1..24, die 0 only, ~node-0 free-mem limited)
# read + rmw. Answers: where does BW saturate, and at what thread count.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BIN="$HERE/../bin/bw_multi"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/thread_scaling_${HOST}_${STAMP}.csv"; LOG="$RESULTS/thread_scaling_${HOST}_${STAMP}.log"
echo "regime,test,nthreads,mem_node,size_per_thread,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 08_thread_scaling $(date) ====="; echo "CSV: $OUT"
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in
  0-5) MODE=SNC3;    DRAMPOINTS="1 2 4 8 12 16 24";             NODEDESC="die 0 (4 channels, ~204 GB/s ceiling)" ;;
  0-1) MODE=SNC-OFF; DRAMPOINTS="1 2 4 8 12 16 24 36 48 64 72"; NODEDESC="whole socket (12 channels, ~614 GB/s ceiling)" ;;
  *) echo "!!! unexpected SNC online=$SNC possible=$(cat /sys/devices/system/node/possible)"; exit 1 ;;
esac
echo "mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible))  mem-node 0 = $NODEDESC; DRAM-regime thread points: $DRAMPOINTS"
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
HUGE2M_FREE=/sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages
ORIG=$(cat "$HUGE2M")
RESTORE_HUGE2M=0
HP2M=2m
cleanup(){ [ "$RESTORE_HUGE2M" -eq 1 ] && echo "$ORIG" | sudo -n tee "$HUGE2M" >/dev/null || true; }; trap cleanup EXIT
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
NPASS=0; NFAIL=0; FAILED=()
run(){ local regime="$1"; local cpus="$2"; local sz="$3"; local pat="$4"; local hp="$5"
  local n; n=$(( $(echo "$cpus" | awk -F- '{print $2}') + 1 ))
  echo "  [$regime] cpus=$cpus (N=$n) size/thr=$sz pat=$pat hp=$hp"
  local to te; to=$(mktemp); te=$(mktemp)
  "$BIN" --cpus "$cpus" --mem-node 0 --size-per-thread "$sz" --hugepage "$hp" --pattern "$pat" --iters 5 --min-walk-secs 0.5 --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then awk -v r="$regime" -F, 'BEGIN{OFS=","}{print r,$0}' "$to" >>"$OUT"; NPASS=$((NPASS+1))
  else printf 'FAILED,%s,0,0,%s,%s,%s,0,0,0,0,0,0\n' "$regime" "$sz" "$hp" "$pat" >>"$OUT"; NFAIL=$((NFAIL+1)); FAILED+=("$regime N=$n sz=$sz pat=$pat hp=$hp rc=$rc"); echo "    FAIL rc=$rc"; sed 's/^/    /' "$te"; fi
  rm -f "$to" "$te"; }
# L3 regime: 4M/thread, 2m pages (small, fits node-0 pool). Run TWICE to gauge
# shared-box run-to-run variance (the first pass was non-monotonic).
echo ">>> L3 regime pass 1 (4M/thread, hp=$HP2M, cpus 0..N-1 -> node 0)"
for N in 1 2 4 8 12 16 24 36 48 64 72; do for pat in read rmw; do run L3 "0-$((N-1))" 4M $pat $HP2M; done; done
echo ">>> L3 regime pass 2 (repeat, for variance check)"
for N in 8 16 24 36 48 64 72; do run L3p2 "0-$((N-1))" 4M read $HP2M; done
# DRAM regime: 64M/thread, 4K pages (none) to avoid node-0 2M-pool SIGBUS.
echo ">>> DRAM regime (64M/thread, 4K pages, cpus 0..N-1 -> node 0)"
for N in $DRAMPOINTS; do for pat in read rmw; do run DRAM "0-$((N-1))" 64M $pat none; done; done
echo "===== done $(date)  pass=$NPASS fail=$NFAIL ====="
[ $NFAIL -gt 0 ] && { echo "FAILED:"; for t in "${FAILED[@]}"; do echo "  - $t"; done; }
echo "CSV: $OUT"
