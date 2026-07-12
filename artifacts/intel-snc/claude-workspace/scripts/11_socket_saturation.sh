#!/usr/bin/env bash
# 11_socket_saturation.sh -- Test 11: saturated WHOLE-SOCKET DRAM bandwidth vs
# thread count, socket 0, Intel SNC3 (and, when re-run under SNC-OFF, pre-SNC3).
#
# Each thread streams its OWN local-node memory via `bw_multi --local` (first-touch
# while pinned), so ALL of socket 0's memory channels engage:
#   - SNC3:    3 dies x 4 DDR5 channels = 12 channels (nodes 0,1,2)
#   - SNC-OFF: node 0 = whole socket = 12 channels (interleaved)
# Single-node binding would cap SNC3 at one die's 4 channels (~204 GB/s) and is NOT
# comparable to SNC-OFF -- hence --local.
#
# Cores are added in order of their die-node's FREE memory (richest first, the
# memory-POOR node last -- probed at runtime), so the BW plateau is reached before
# any fragmented node is touched. Per-thread 64 MiB, 4K pages (avoids the 2M-hugepage
# scarcity on node 0; 64M x 24 die-0 threads = 1.5 GB < node-0 free).
#
# Saturation is confirmed by the curve flattening (or dropping) as N -> 72.
#
# ===================================================================================
# APPLE-TO-APPLE pre-SNC3 RE-TEST: run THIS SAME SCRIPT, UNCHANGED, under SNC-OFF.
#   Do NOT change: --local, per-thread 64 MiB, 4K pages, the thread-count points,
#   or the socket-0 core set. Under SNC-OFF the script auto-detects that socket 0 is
#   a single node and orders cores 0-71 within it; --local still first-touches on
#   socket-0 memory. The ONLY difference between the two runs must be the BIOS SNC
#   mode. Compare the two socket_sat_*.csv curves directly.
# ===================================================================================
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BIN="$HERE/../bin/bw_multi"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/socket_sat_${HOST}_${STAMP}.csv"; LOG="$RESULTS/socket_sat_${HOST}_${STAMP}.log"
echo "snc_mode,pattern,nthreads,agg_GBps,min_GBps,max_GBps,cpus" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in 0-5) MODE=SNC3 ;; 0-1) MODE=SNC-OFF ;; *) MODE="UNKNOWN($SNC)" ;; esac
echo "===== 11_socket_saturation $(date)  mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible)) ====="
echo "method: bw_multi --local, 64M/thread, 4K pages; cores added memory-poor-node-last"

# --- build socket-0 core order: nodes containing cores 0-71, richest free mem first ---
declare -A NODE_FREE NODE_CPUS
for nd in /sys/devices/system/node/node*; do
  n=$(basename "$nd" | sed 's/node//')
  # physical cores 0-71 belonging to this node (exclude SMT siblings >=144)
  cl=$(cat "$nd/cpulist")
  cores=$(python3 - "$cl" <<'PY'
import sys
out=[]
for part in sys.argv[1].split(','):
    if '-' in part:
        a,b=part.split('-'); a,b=int(a),int(b)
        out+= [c for c in range(a,b+1) if c<72]
    else:
        c=int(part)
        if c<72: out.append(c)
print(','.join(str(c) for c in sorted(out)))
PY
)
  [ -z "$cores" ] && continue   # node has no socket-0 cores
  free=$(awk '/MemFree/{print $4}' "$nd/meminfo")
  NODE_FREE[$n]=$free; NODE_CPUS[$n]=$cores
  echo "  node$n: socket-0 cores=[$cores]  free=$((free/1024)) MB"
done
# order nodes by free desc
ORDER_NODES=$(for n in "${!NODE_FREE[@]}"; do echo "${NODE_FREE[$n]} $n"; done | sort -rn | awk '{print $2}')
ORDERED=""
for n in $ORDER_NODES; do ORDERED="${ORDERED:+$ORDERED,}${NODE_CPUS[$n]}"; done
IFS=',' read -ra CPUARR <<< "$ORDERED"
echo "  core add-order (memory-rich node first): $ORDERED"
echo "  total socket-0 cores available: ${#CPUARR[@]}"

HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
run(){ local N="$1" pat="$2"
  local list; list=$(IFS=,; echo "${CPUARR[*]:0:$N}")
  local to te; to=$(mktemp); te=$(mktemp)
  "$BIN" --cpus "$list" --local --size-per-thread 64M --hugepage none --pattern "$pat" --iters 4 --min-walk-secs 0.5 --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then
    awk -v s="$MODE" -v p="$pat" -v n="$N" -v cl="$list" -F, 'BEGIN{OFS=","}{print s,p,n,$8,$9,$10,"\""cl"\""}' "$to" >>"$OUT"
    echo "  N=$N $pat -> $(awk -F, '{print $8}' "$to") GB/s"
  else
    printf '%s,%s,%s,0,0,0,"%s"\n' "$MODE" "$pat" "$N" "$list" >>"$OUT"; echo "  N=$N $pat FAIL rc=$rc"; sed 's/^/    /' "$te"
  fi
  rm -f "$to" "$te"; }

NMAX=${#CPUARR[@]}
POINTS="1 2 4 8 12 16 24 32 40 48 56 64 72"
for pat in read rmw; do
  echo ">>> pattern=$pat"
  for N in $POINTS; do [ "$N" -le "$NMAX" ] && run "$N" "$pat"; done
done
echo "===== done $(date) ====="
echo "CSV: $OUT"
