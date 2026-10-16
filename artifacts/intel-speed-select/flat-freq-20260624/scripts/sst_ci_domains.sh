#!/usr/bin/env bash
set -euo pipefail

action="${1:?usage: sst_ci_domains.sh readback|baseline|candidate RUN_DIR [label]}"
run_dir="${2:?usage: sst_ci_domains.sh readback|baseline|candidate RUN_DIR [label]}"
label="${3:-$action}"

ISST="${ISST:-/home/jhan/workspace/intel-vs-amd/speed-select/workspace/flat_freq/20260623_codex_preserved_tmp/intel-speed-select-v6.8/intel-speed-select}"
ANCHORS="${ANCHORS:-24 48 72 96}"
state_dir="$run_dir/state"
mkdir -p "$state_dir"

ensure_isst_interface() {
  sudo -n /usr/sbin/modprobe isst_if_mbox_pci || true
  sudo -n /usr/sbin/modprobe isst_if_mmio || true
  sudo -n /usr/sbin/modprobe isst_tpmi || true
  if [[ ! -e /dev/isst_interface ]]; then
    echo "ERROR: /dev/isst_interface is missing after modprobe" >&2
    return 1
  fi
}

readback_one() {
  local cpu="$1"
  {
    echo "timestamp=$(date -Is)"
    echo "anchor_cpu=$cpu"
    echo
    "$ISST" -c "$cpu" core-power info
    "$ISST" -c "$cpu" perf-profile info
  } > "$state_dir/${label}_isst_cpu${cpu}.log" 2>&1
}

summarize_one() {
  local cpu="$1"
  printf 'CPU %s: ' "$cpu"
  rg 'clos-enable-status:|speed-select-turbo-freq:|speed-select-core-power:' \
    "$state_dir/${label}_isst_cpu${cpu}.log" | head -3 | tr '\n' ' '
  echo
}

ensure_isst_interface

case "$action" in
  baseline)
    for cpu in $ANCHORS; do
      echo "Restoring baseline on anchor CPU $cpu: turbo-freq enable, core-power disable"
      "$ISST" -c "$cpu" turbo-freq enable
      "$ISST" -c "$cpu" core-power disable
    done
    ;;
  candidate)
    for cpu in $ANCHORS; do
      echo "Applying candidate on anchor CPU $cpu: core-power disable, turbo-freq disable"
      "$ISST" -c "$cpu" core-power disable || true
      "$ISST" -c "$cpu" turbo-freq disable
    done
    ;;
  readback)
    ;;
  *)
    echo "ERROR: unknown action '$action'" >&2
    exit 2
    ;;
esac

for cpu in $ANCHORS; do
  readback_one "$cpu"
  summarize_one "$cpu"
done
