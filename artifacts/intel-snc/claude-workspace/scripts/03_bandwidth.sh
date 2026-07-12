#!/usr/bin/env bash
# 03_bandwidth.sh -- single-thread AVX-512 BW, cpu 0 -> each mem-node, 4G, read+rmw. Test 4.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BIN="$HERE/../bin/bw_avx512"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/bw_avx512_${HOST}_${STAMP}.csv"; LOG="$RESULTS/bw_avx512_${HOST}_${STAMP}.log"
echo "test,cpu,mem_node,size_bytes,hugepage,pattern,iters,median_GBps,min_GBps,max_GBps,mean_GBps,stddev_GBps" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 03_bandwidth $(date) ====="; echo "CSV: $OUT"
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in
  0-5) MODE=SNC3;    NODES="0 1 2 3 4 5" ;;
  0-1) MODE=SNC-OFF; NODES="0 1" ;;
  *) echo "!!! unexpected SNC online=$SNC possible=$(cat /sys/devices/system/node/possible)"; exit 1 ;;
esac
echo "mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible))  nodes={$NODES}"
NPASS=0; NFAIL=0; FAILED=()
run(){ local cpu="$1" memn="$2" sz="$3" hp="$4" pat="$5"
  echo "  cpu=$cpu mem=$memn size=$sz pat=$pat"
  local to te; to=$(mktemp); te=$(mktemp)
  "$BIN" --cpu "$cpu" --mem-node "$memn" --size "$sz" --hugepage "$hp" --pattern "$pat" --iters 5 --min-walk-secs 0.5 --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then cat "$to" >>"$OUT"; NPASS=$((NPASS+1))
  else printf 'FAILED,%s,%s,%s,%s,%s,0,0,0,0,0,0\n' "$cpu" "$memn" "$sz" "$hp" "$pat" >>"$OUT"; NFAIL=$((NFAIL+1)); FAILED+=("cpu=$cpu mem=$memn pat=$pat rc=$rc"); echo "    FAIL rc=$rc"; sed 's/^/    /' "$te"; fi
  rm -f "$to" "$te"; }
echo ">>> Test 4: DRAM 4G, cpu 0 -> each mem-node, read + rmw"
for memn in $NODES; do for pat in read rmw; do run 0 "$memn" 4G 1g "$pat"; done; done
echo "===== done $(date)  pass=$NPASS fail=$NFAIL ====="
[ $NFAIL -gt 0 ] && { echo "FAILED:"; for t in "${FAILED[@]}"; do echo "  - $t"; done; }
echo "CSV: $OUT"
