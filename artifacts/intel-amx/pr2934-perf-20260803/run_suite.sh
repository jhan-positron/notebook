#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 REPO OUTPUT_DIR VARIANT" >&2
  exit 2
fi

repo=$1
output_dir=$2
variant=$3
runner="$repo/bin/ci/benchmark_run.py"
validator="${BASH_SOURCE[0]%/*}/validate_config.py"

mkdir -p "$output_dir"
export RZ_FUSE_MOUNT_PATH="/tmp/tron-pr2934-perf-20260803-$variant"
mkdir -p "$RZ_FUSE_MOUNT_PATH"
exec > >(tee -a "$output_dir/suite.log") 2>&1

echo "# Variant: $variant"
echo "# Host: $(hostname)"
echo "# Started: $(date --iso-8601=seconds)"
echo "# Git: $(git -C "$repo" rev-parse HEAD)"
echo "# SYSTEM_CONFIG: ${SYSTEM_CONFIG:-unset}"
echo "# DICE_SLOTS: ${DICE_SLOTS:-unset}"

# The outer Dice job reserves the full machine. benchmark_run.py then divides
# that reservation into explicit, non-overlapping --instance X,N children.
# runtron forbids explicit --instance while these outer-grant variables exist.
unset DICE_DAEMON_CHILD DICE_SLOTS DICE_GRANT_ID DICE_GRANT_TOKEN SYSTEM_CONFIG
echo "# Inner runtron Dice grant variables: unset"

run_config() {
  local name=$1
  shift
  echo "# Starting $variant/$name at $(date --iso-8601=seconds)"
  env --chdir="$repo" python3 -u "$runner" \
    "$@" \
    --repeats 10 \
    -c 144 \
    -f 8 \
    --output-dir "$output_dir/$name"
  python3 "$validator" "$output_dir/$name"
  echo "# Completed $variant/$name at $(date --iso-8601=seconds)"
}

run_config 01_llama32-3b-fast-tp2 \
  -m llama-3.2-3b-instruct-fast \
  -tp 2 \
  -spl 800 \
  -pl 199 \
  -l 335 \
  -p 32 \
  -i 4 \
  --isolated-iterations 5 \
  --timeout-sec 600

run_config 02_llama31-8b-good-tp4 \
  -m llama-3.1-8b-instruct-good \
  -tp 4 \
  -spl 0 \
  -pl 1919 \
  -l 130 \
  -p 8 \
  -i 2 \
  --isolated-iterations 10 \
  --timeout-sec 600

run_config 03_ingested-llama31-8b-tp2 \
  -m ingested-llama-3.1-8b \
  -tp 2 \
  -spl 0 \
  -pl 1919 \
  -l 130 \
  -p 8 \
  -i 4 \
  --isolated-iterations 5 \
  --timeout-sec 600

run_config 04_llama31-8b-good-tp2 \
  -m llama-3.1-8b-instruct-good \
  -tp 2 \
  -spl 0 \
  -pl 1919 \
  -l 130 \
  -p 8 \
  -i 4 \
  --isolated-iterations 5 \
  --timeout-sec 600

run_config 05_ingested-gpt-oss-120b-tp4 \
  -m ingested-gpt-oss-120b \
  -tp 4 \
  -spl 0 \
  -pl 2047 \
  -l 514 \
  -p 8 \
  -i 2 \
  --isolated-iterations 10 \
  --timeout-sec 660

touch "$output_dir/SUITE_COMPLETE"
