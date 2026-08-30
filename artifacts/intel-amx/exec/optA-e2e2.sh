#!/usr/bin/env bash
# Re-run of the EAGLE end-to-end cases with correct Catch2 name escaping
# (commas in names must be written as "\,") and full per-run logs.
set -u
cd ~/workspace/tron-amx || exit 1
. ~/workspace/intel-AMX/exec/lib-guard.sh
campaign_guard_acquire || { echo "guard refused"; exit 3; }
trap campaign_guard_release EXIT
OUT=~/workspace/intel-AMX/exec/logs/optA-e2e2-runs; mkdir -p "$OUT"
run() {  # run <tag> <catch2 spec> [env...]
  local tag=$1 spec=$2; shift 2
  local f="$OUT/$tag.log"
  echo "=== $tag $(date -u +%FT%TZ) :: $spec :: ${*:-<default env>}"
  env "$@" nice -n5 ./gen/t_generate_2 "$spec" --skip-benchmarks > "$f" 2>&1
  echo "exit=$?"
  grep -o "HW attention enabled for model '[^']*'[^(]*([^)]*)\|USE_HW_ATTN=0\|HW attention disabled[^|]*\|hardware attention[^|]*off[^|]*" "$f" | sort | uniq -c | head -4
  grep -o "Generating [0-9]* response tokens with [0-9]* context took [0-9.]* s at [0-9.]* average tok/s" "$f" | head -6
  grep -o "Speculation mean acceptance length = [0-9.]* rate = [0-9.]* over [0-9]* tokens" "$f" | head -6
  grep -E "Catch2 (passed|failed)|FAILED|^All tests passed|^test cases:|^assertions:|No test cases matched" "$f" | sed 's/^\[[^]]*\] //' | head -8
  ci_took_dut && { echo "CI took the DUT - stopping"; exit 4; }
}
run A-agree-default   "Speculation via EAGLE"
run B-shard-default   "Speculation via EAGLE\, crosses shard boundary"
run C-stop-default    "Speculation via EAGLE\, stopping"
run D-agree-sw        "Speculation via EAGLE"                            USE_HW_ATTN=0
run E-shard-sw        "Speculation via EAGLE\, crosses shard boundary"   USE_HW_ATTN=0
run F-shard-sw-noamx  "Speculation via EAGLE\, crosses shard boundary"   USE_HW_ATTN=0 TRON_AMX_DISABLE=1
echo "=== done $(date -u +%FT%TZ)"
