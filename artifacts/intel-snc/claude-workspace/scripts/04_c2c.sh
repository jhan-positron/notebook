#!/usr/bin/env bash
# 04_c2c.sh -- cache-coherence latency (atomic CAS ping-pong), cpu 0 -> partners. Test 5.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BIN="$HERE/../bin/c2c_lat"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/c2c_${HOST}_${STAMP}.csv"; LOG="$RESULTS/c2c_${HOST}_${STAMP}.log"
echo "test,cpu_a,cpu_b,mem_node,iters,rounds,median_ns_rt,min_ns_rt,max_ns_rt,mean_ns_rt,stddev_ns_rt" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 04_c2c $(date) ====="; echo "CSV: $OUT"
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in 0-5) MODE=SNC3 ;; 0-1) MODE=SNC-OFF ;; *) echo "!!! unexpected SNC online=$SNC possible=$(cat /sys/devices/system/node/possible)"; exit 1 ;; esac
echo "mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible))  partners are physical cpus (identical in both modes); 'die' labels below are nominal under SNC-OFF (no per-die nodes)"
NPASS=0; NFAIL=0; FAILED=()
run(){ local a="$1"; local b="$2"; local mn="$3"
  echo "  cpu_a=$a cpu_b=$b mem=$mn"
  local to te; to=$(mktemp); te=$(mktemp)
  "$BIN" --cpu-a "$a" --cpu-b "$b" --mem-node "$mn" --iters 5 --rounds 1000000 --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then cat "$to" >>"$OUT"; NPASS=$((NPASS+1))
  else printf 'FAILED,%s,%s,%s,0,0,0,0,0,0,0\n' "$a" "$b" "$mn" >>"$OUT"; NFAIL=$((NFAIL+1)); FAILED+=("a=$a b=$b rc=$rc"); echo "    FAIL rc=$rc"; sed 's/^/    /' "$te"; fi
  rm -f "$to" "$te"; }
echo ">>> within-die 0"; for b in 1 5 11 23; do run 0 "$b" 0; done
echo ">>> cross-die same socket"; for b in 24 47 48 71; do run 0 "$b" 0; done
echo ">>> cross-socket"; for b in 72 96 120 143; do run 0 "$b" 0; done
echo "===== done $(date)  pass=$NPASS fail=$NFAIL ====="
[ $NFAIL -gt 0 ] && { echo "FAILED:"; for t in "${FAILED[@]}"; do echo "  - $t"; done; }
echo "CSV: $OUT"
