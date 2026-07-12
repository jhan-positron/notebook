#!/usr/bin/env bash
# run_full_codex.sh -- Codex fresh-pass runner for current input-2-ai suite.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS="$HERE/../results"
ONLINE="$(cat /sys/devices/system/node/online)"
case "$ONLINE" in
  0-5) MODE=SNC3; RESULTS="$RESULTS/snc3" ;;
  0-1) MODE=SNC-OFF; RESULTS="$RESULTS/snc-off" ;;
  *)
    echo "!!! unexpected node/online=$ONLINE possible=$(cat /sys/devices/system/node/possible)"
    exit 1
    ;;
esac
mkdir -p "$RESULTS"

STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
META="$RESULTS/run_full_codex_${HOST}_${STAMP}.log"
exec > >(tee -a "$META") 2>&1

FAILURES=()

step() {
  local name="$1" script="$2" rc
  echo
  echo "##### [$(date '+%Y-%m-%d %H:%M:%S')] START $name #####"
  if [ ! -x "$script" ] && [ ! -f "$script" ]; then
    echo "missing script: $script"
    rc=127
  else
    bash "$script"
    rc=$?
  fi
  echo "##### [$(date '+%Y-%m-%d %H:%M:%S')] END $name rc=$rc #####"
  if [ "$rc" -ne 0 ]; then
    FAILURES+=("$name rc=$rc script=$script")
  fi
  return 0
}

echo "===== run_full_codex $(date) host=$HOST mode=$MODE online=$ONLINE possible=$(cat /sys/devices/system/node/possible) ====="
echo "results: $RESULTS"
echo "log: $META"
uptime

step "01_inspect_pre"        "$HERE/01_inspect.sh"
step "02_latency"            "$HERE/02_latency.sh"
step "03_bandwidth"          "$HERE/03_bandwidth.sh"
step "04_c2c"                "$HERE/04_c2c.sh"
step "05_topology_bw"        "$HERE/05_topology_bw.sh"
step "06_cat"                "$HERE/06_cat.sh"
step "07_bigbuffer_bw"       "$HERE/07_bigbuffer_bw.sh"
step "08_thread_scaling"     "$HERE/08_thread_scaling.sh"
step "09_loaded_latency"     "$HERE/09_loaded_latency.sh"
step "11_socket_saturation"  "$HERE/11_socket_saturation.sh"
step "12_latency_vs_socket_bw" "$HERE/12_latency_vs_socket_bw.sh"
step "01_inspect_post"       "$HERE/01_inspect.sh"

echo
echo "===== run_full_codex FINISHED $(date) ====="
echo "CSV files in $RESULTS:"
if compgen -G "$RESULTS/*.csv" >/dev/null; then
  ls -1 "$RESULTS"/*.csv
else
  echo "No CSV files found in $RESULTS"
fi

if [ "${#FAILURES[@]}" -gt 0 ]; then
  echo
  echo "===== run_full_codex FAILURES (${#FAILURES[@]}) ====="
  for failure in "${FAILURES[@]}"; do
    echo "FAILED: $failure"
  done
  echo "Run log: $META"
  exit 1
fi

echo
echo "===== run_full_codex OK: all steps succeeded ====="
echo "Run log: $META"
