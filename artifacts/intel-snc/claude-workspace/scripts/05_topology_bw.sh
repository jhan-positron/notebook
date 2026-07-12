#!/usr/bin/env bash
# 05_topology_bw.sh -- multi-thread BW vs thread placement. Test 7.
# 24 threads (1 per core), all access mem-node 0. Sizes 4/6/8/16/20 MiB per thread.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BIN="$HERE/../bin/bw_multi"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/bw_topology_${HOST}_${STAMP}.csv"; LOG="$RESULTS/bw_topology_${HOST}_${STAMP}.log"
echo "topology,test,nthreads,mem_node,size_per_thread,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 05_topology_bw $(date) ====="; echo "CSV: $OUT"
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in
  0-5) MODE=SNC3;    MEMDESC="die 0 (4 channels)" ;;
  0-1) MODE=SNC-OFF; MEMDESC="whole socket (12 channels, interleaved)" ;;
  *) echo "!!! unexpected SNC online=$SNC possible=$(cat /sys/devices/system/node/possible)"; exit 1 ;;
esac
echo "mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible))  mem-node 0 = $MEMDESC; topology labels A-E nominal under SNC-OFF (expect A~B~C~D to converge)"
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
declare -A T=( [A_die0_local]="0-23" [B_die1_xdie]="24-47" [C_die2_xdie]="48-71" [D_mixed_3dies]="0-7,24-31,48-55" [E_socket1_xsock]="72-95" )
NPASS=0; NFAIL=0; FAILED=()
run(){ local lab="$1" cpus="$2" sz="$3" pat="$4"
  echo "  topo=$lab cpus=$cpus size/thr=$sz pat=$pat"
  local to te; to=$(mktemp); te=$(mktemp)
  "$BIN" --cpus "$cpus" --mem-node 0 --size-per-thread "$sz" --hugepage "$HP2M" --pattern "$pat" --iters 5 --min-walk-secs 0.5 --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then awk -v l="$lab" -F, 'BEGIN{OFS=","}{print l,$0}' "$to" >>"$OUT"; NPASS=$((NPASS+1))
  else printf 'FAILED,%s,0,0,%s,%s,%s,0,0,0,0,0,0\n' "$lab" "$sz" "$HP2M" "$pat" >>"$OUT"; NFAIL=$((NFAIL+1)); FAILED+=("$lab sz=$sz pat=$pat hp=$HP2M rc=$rc"); echo "    FAIL rc=$rc"; sed 's/^/    /' "$te"; fi
  rm -f "$to" "$te"; }
for lab in A_die0_local B_die1_xdie C_die2_xdie D_mixed_3dies E_socket1_xsock; do
  echo ">>> $lab (${T[$lab]})"
  for sz in 4M 6M 8M 16M 20M; do for pat in read rmw; do run "$lab" "${T[$lab]}" "$sz" "$pat"; done; done
done
echo "===== done $(date)  pass=$NPASS fail=$NFAIL ====="
[ $NFAIL -gt 0 ] && { echo "FAILED:"; for t in "${FAILED[@]}"; do echo "  - $t"; done; }
echo "CSV: $OUT"
