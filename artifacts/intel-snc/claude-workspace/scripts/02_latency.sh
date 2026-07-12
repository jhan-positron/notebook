#!/usr/bin/env bash
# 02_latency.sh -- single-thread pointer-chase latency. Tests 1,2,3 (read + rmw).
#   T1: L3 plateau curve, cpu 0 + mem 0, 32K..4G (read + rmw)
#   T2: DRAM 4G, cpu {0,24,48} x mem {0..5} (read + rmw)
#   T3: L3 hit per-node, cpu 0 x mem {0..5} at 4M,64M (read + rmw)
# CSV adds a 'pattern' column (read|rmw) and a 'phase' column (T1|T2|T3).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BIN="$HERE/../bin/ptr_chase"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/ptr_chase_${HOST}_${STAMP}.csv"; LOG="$RESULTS/ptr_chase_${HOST}_${STAMP}.log"
echo "phase,pattern,cpu,mem_node,size_bytes,hugepage,iters,median_ns,min_ns,max_ns,mean_ns,stddev_ns" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 02_latency $(date) ====="; echo "CSV: $OUT"
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in
  0-5) MODE=SNC3;    NODES="0 1 2 3 4 5"; T2CPUS="0 24 48" ;;
  0-1) MODE=SNC-OFF; NODES="0 1";         T2CPUS="0 72" ;;
  *) echo "!!! unexpected SNC online=$SNC possible=$(cat /sys/devices/system/node/possible)"; exit 1 ;;
esac
echo "mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible))  T2/T3 nodes={$NODES}  T2 origin cpus={$T2CPUS}"
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
run(){ local ph="$1" pat="$2" cpu="$3" memn="$4" sz="$5" hp="$6"; local rflag=""; [ "$pat" = rmw ] && rflag="--rmw"
  echo "  [$ph/$pat] cpu=$cpu mem=$memn size=$sz hp=$hp"
  local to te; to=$(mktemp); te=$(mktemp)
  "$BIN" --cpu "$cpu" --mem-node "$memn" --size "$sz" --hugepage "$hp" --iters 5 --min-walk-secs 0.5 $rflag --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then awk -v p="$ph" -v pt="$pat" -F, 'BEGIN{OFS=","}{print p,pt,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11}' "$to" >>"$OUT"; NPASS=$((NPASS+1))
  else printf 'FAILED,%s,%s,%s,%s,%s,0,0,0,0,0,0\n' "$pat" "$cpu" "$memn" "$sz" "$hp" >>"$OUT"; NFAIL=$((NFAIL+1)); FAILED+=("$ph/$pat cpu=$cpu mem=$memn sz=$sz rc=$rc"); echo "    FAIL rc=$rc"; sed 's/^/    /' "$te"; fi
  rm -f "$to" "$te"; }

echo ">>> T1 L3 plateau curve, cpu 0 mem 0 (read + rmw)"
for pat in read rmw; do
  for sz in 32K 64K 128K 256K 512K 1M 2M; do run T1 $pat 0 0 $sz none; done
  for sz in 4M 8M 16M 32M 64M 96M 128M 256M; do run T1 $pat 0 0 $sz $HP2M; done
  for sz in 1G 2G 4G; do run T1 $pat 0 0 $sz 1g; done
done
echo ">>> T3 L3 hit per-node, cpu 0 x mem {0..5} at 4M,64M (read + rmw)"
for pat in read rmw; do for memn in $NODES; do for sz in 4M 64M; do run T3 $pat 0 $memn $sz $HP2M; done; done; done
echo ">>> T2 DRAM 4G, cpu {0,24,48} x mem {0..5} (read + rmw)"
for pat in read rmw; do for cpu in $T2CPUS; do for memn in $NODES; do run T2 $pat $cpu $memn 4G 1g; done; done; done

echo "===== done $(date)  pass=$NPASS fail=$NFAIL ====="
[ $NFAIL -gt 0 ] && { echo "FAILED:"; for t in "${FAILED[@]}"; do echo "  - $t"; done; }
echo "CSV: $OUT"
