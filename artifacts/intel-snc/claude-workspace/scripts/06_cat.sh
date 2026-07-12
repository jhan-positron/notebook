#!/usr/bin/env bash
# 06_cat.sh -- CAT capacity sweep via resctrl. Test 6. ptr_chase cpu0 mem0 under varying L3 CBM.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BIN="$HERE/../bin/ptr_chase"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; GROUP=/sys/fs/resctrl/cat_test; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname)
OUT="$RESULTS/cat_${HOST}_${STAMP}.csv"; LOG="$RESULTS/cat_${HOST}_${STAMP}.log"
echo "test,cpu,mem_node,size_bytes,hugepage,cbm_hex,cbm_bits,iters,median_ns,min_ns,max_ns,mean_ns,stddev_ns" > "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 06_cat $(date) ====="; echo "CSV: $OUT"
[ -d /sys/fs/resctrl/info/L3 ] || { echo "!!! resctrl not mounted"; exit 1; }
[ -d "$GROUP" ] && sudo -n /usr/bin/rmdir "$GROUP" 2>/dev/null || true
if ! sudo -n /usr/bin/mkdir "$GROUP" 2>/dev/null; then
  echo "!!! 06_cat requires NOPASSWD sudo for specific resctrl commands"
  echo "!!! failed: sudo -n /usr/bin/mkdir $GROUP"
  exit 1
fi
sudo -n /usr/bin/rmdir "$GROUP" 2>/dev/null || true
SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in 0-5) MODE=SNC3 ;; 0-1) MODE=SNC-OFF ;; *) echo "!!! unexpected SNC online=$SNC possible=$(cat /sys/devices/system/node/possible)"; exit 1 ;; esac
echo "mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible))  L3 CAT domains are per-socket in both modes; floor will be the mode's L3-hit latency"
echo "num_closids=$(cat /sys/fs/resctrl/info/L3/num_closids) cbm_mask=$(cat /sys/fs/resctrl/info/L3/cbm_mask) shareable=$(cat /sys/fs/resctrl/info/L3/shareable_bits)"
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
HUGE2M_FREE=/sys/kernel/mm/hugepages/hugepages-2048kB/free_hugepages
ORIG=$(cat "$HUGE2M")
RESTORE_HUGE2M=0
HP2M=2m
cleanup(){ [ "$RESTORE_HUGE2M" -eq 1 ] && echo "$ORIG" | sudo -n /usr/bin/tee "$HUGE2M" >/dev/null || true; [ -d "$GROUP" ] && sudo -n /usr/bin/rmdir "$GROUP" 2>/dev/null || true; }; trap cleanup EXIT
if echo 2048 | sudo -n /usr/bin/tee "$HUGE2M" >/dev/null; then RESTORE_HUGE2M=1; else echo "WARN: failed to set 2M hugepages"; fi
FREE2M=$(cat "$HUGE2M_FREE")
if [ "$FREE2M" -lt 256 ]; then
  HP2M=none
  echo "WARN: only $FREE2M free 2M hugepages; using --hugepage none for tests that requested 2m"
else
  echo "2M hugepages free=$FREE2M; using --hugepage 2m where requested"
fi
[ -d "$GROUP" ] && sudo -n /usr/bin/rmdir "$GROUP" 2>/dev/null
sudo -n /usr/bin/mkdir "$GROUP" || { echo "!!! failed to create $GROUP"; exit 1; }
echo "$$" | sudo -n /usr/bin/tee "$GROUP/tasks" >/dev/null || { echo "!!! failed to attach task to $GROUP"; exit 1; }
declare -a CBMS=(ffff 3fff 003f 000f 0003 0001); declare -A B=([ffff]=16 [3fff]=14 [003f]=6 [000f]=4 [0003]=2 [0001]=1)
NPASS=0; NFAIL=0
run(){ local cbm="$1" sz="$2"; local hp; case "$sz" in 1M|2M) hp=none;; *) hp=$HP2M;; esac
  local to te; to=$(mktemp); te=$(mktemp)
  "$BIN" --cpu 0 --mem-node 0 --size "$sz" --hugepage "$hp" --iters 5 --min-walk-secs 0.5 --csv >"$to" 2>"$te"; local rc=$?
  if [ $rc -eq 0 ] && [ -s "$to" ]; then awk -v c="$cbm" -v b="${B[$cbm]}" -F, 'BEGIN{OFS=","}{print $1,$2,$3,$4,$5,c,b,$6,$7,$8,$9,$10,$11}' "$to" >>"$OUT"; NPASS=$((NPASS+1))
  else printf 'FAILED,0,0,%s,%s,%s,%s,0,0,0,0,0,0\n' "$sz" "$hp" "$cbm" "${B[$cbm]}" >>"$OUT"; NFAIL=$((NFAIL+1)); fi
  rm -f "$to" "$te"; }
for cbm in "${CBMS[@]}"; do
  echo ">>> CBM L3:0=$cbm (${B[$cbm]} bits)"
  echo "L3:0=$cbm;1=ffff" | sudo -n /usr/bin/tee "$GROUP/schemata" >/dev/null
  grep -E '^\s*L3:' "$GROUP/schemata"; sleep 1
  for sz in 1M 2M 4M 8M 16M 32M 64M 128M; do echo "  cbm=$cbm sz=$sz"; run "$cbm" "$sz"; done
done
echo "===== done $(date)  pass=$NPASS fail=$NFAIL ====="
echo "CSV: $OUT"
