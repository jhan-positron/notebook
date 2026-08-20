#!/bin/bash
# Intervention A/B: uncore min pinned to max for the campaign; guaranteed restore.
set -u
ROOT=$1
U=/sys/devices/system/cpu/intel_uncore_frequency
restore() {
  for p in $U/package_*; do echo 800000 | sudo -n tee $p/min_freq_khz >/dev/null; done
  echo "$(date -u +%FT%TZ) uncore min restored to 800000" >> $ROOT/intervention.log
}
trap restore EXIT
for p in $U/package_*; do
  MAX=$(cat $p/max_freq_khz)
  echo $MAX | sudo -n tee $p/min_freq_khz >/dev/null
  echo "$(date -u +%FT%TZ) $p min pinned to $MAX" >> $ROOT/intervention.log
done
SHA=$(sha256sum /scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe7/bin/runtron | cut -d" " -f1)
env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 SLICE_OF=2 ROUNDS=16 CAPTURE=none KVWAIT=1 \
  INSTALL=/scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe7 EXPECTED_BIN_SHA=$SHA CAMPAIGN_ROOT=$ROOT \
  bash $ROOT/harness.sh
