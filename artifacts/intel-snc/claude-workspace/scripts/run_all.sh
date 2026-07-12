#!/usr/bin/env bash
# run_all.sh -- full sweep suite for the 8 tests in input-2-ai/output.md.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; RESULTS="$HERE/../results"; case "$(cat /sys/devices/system/node/online)" in 0-5) RESULTS="$RESULTS/snc3";; 0-1) RESULTS="$RESULTS/snc-off";; *) echo "!!! unexpected node/online=$(cat /sys/devices/system/node/online) possible=$(cat /sys/devices/system/node/possible)"; exit 1;; esac; mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M); HOST=$(hostname); META="$RESULTS/run_all_${HOST}_${STAMP}.log"
exec > >(tee -a "$META") 2>&1
echo "===== run_all $(date) ====="
FAILURES=()
step(){
  local name="$1" script="$2" rc
  echo
  echo "##### [$(date +%H:%M:%S)] $name #####"
  bash "$script"
  rc=$?
  echo "##### [$(date +%H:%M:%S)] $name rc=$rc #####"
  if [ "$rc" -ne 0 ]; then
    FAILURES+=("$name rc=$rc script=$script")
  fi
  return 0
}
step "01_inspect (pre)"  "$HERE/01_inspect.sh"
step "02_latency"        "$HERE/02_latency.sh"
step "03_bandwidth"      "$HERE/03_bandwidth.sh"
step "04_c2c"            "$HERE/04_c2c.sh"
step "05_topology_bw"    "$HERE/05_topology_bw.sh"
step "06_cat"            "$HERE/06_cat.sh"
step "07_bigbuffer_bw"   "$HERE/07_bigbuffer_bw.sh"
step "01_inspect (post)" "$HERE/01_inspect.sh"
echo
echo "===== run_all FINISHED $(date) ====="
if compgen -G "$RESULTS/*.csv" >/dev/null; then
  ls -1 "$RESULTS"/*.csv
else
  echo "No CSV files found in $RESULTS"
fi

if [ "${#FAILURES[@]}" -gt 0 ]; then
  echo
  echo "===== run_all FAILURES (${#FAILURES[@]}) ====="
  for failure in "${FAILURES[@]}"; do
    echo "FAILED: $failure"
  done
  echo "Run log: $META"
  exit 1
fi

echo
echo "===== run_all OK: all steps succeeded ====="
echo "Run log: $META"
