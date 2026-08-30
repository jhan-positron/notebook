#!/usr/bin/env bash
# End-to-end EAGLE cases on delphi-3bda against the K_MIRROR build with the
# Option A fix (96b5a6c72). Mode 1: default (FPGA HW attention where eligible,
# software elsewhere; the EAGLE child is always software). Mode 2: all-software
# attention (USE_HW_ATTN=0) so every full page of the validator takes the AMX
# mirror path - the strongest end-to-end exposure of the fixed seam.
set -u
cd ~/workspace/tron-amx || exit 1
. ~/workspace/intel-AMX/exec/lib-guard.sh
campaign_guard_acquire || { echo "guard refused"; exit 3; }
trap campaign_guard_release EXIT
export TRON_LOG_LEVEL=${TRON_LOG_LEVEL:-warn}
run() {  # run <label> <catch2 spec> [env...]
  local label=$1 spec=$2; shift 2
  echo "=== $label $(date -u +%FT%TZ) :: $spec :: ${*:-<default env>}"
  env "$@" nice -n5 ./gen/t_generate_2 "$spec" --skip-benchmarks 2>&1 \
    | grep -v "\[info\]\|\[debug\]" | tail -12
  echo "exit=${PIPESTATUS[0]}"
  ci_took_dut && { echo "CI took the DUT - stopping"; exit 4; }
}
run "A. EAGLE agreement, default attention"      "Speculation via EAGLE"
run "B. EAGLE crosses shard boundary, default"   "Speculation via EAGLE, crosses shard boundary"
run "C. EAGLE stopping, default"                 "Speculation via EAGLE, stopping"
run "D. EAGLE agreement, all-software attention" "Speculation via EAGLE" USE_HW_ATTN=0
echo "=== done $(date -u +%FT%TZ)"
