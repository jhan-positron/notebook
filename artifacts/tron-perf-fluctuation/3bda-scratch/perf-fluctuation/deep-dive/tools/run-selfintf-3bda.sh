#!/usr/bin/env bash
# Freeze causal test: quiet arm, then arm with concurrent trace_processor ingest.
set -u
D=/scratch/jhan/perf-fluctuation/deep-dive
SHA=$(sha256sum $D/install-kvprobe7/bin/runtron | cut -d" " -f1)
BIGTRACE=/scratch/jhan/perf-fluctuation/pfgate-3bda/ungated-tp4-20260812T173050Z-r3/results/draw_10-slowest/trace.pftrace
for arm in quiet tpload; do
  ROOT=$D/3bda-selfintf-$arm-$(date -u +%Y%m%dT%H%M%SZ)
  mkdir -p $ROOT
  cp $D/tools/deepdive-campaign.sh $ROOT/harness.sh
  if [ $arm = tpload ]; then
    ( while [ ! -f $ROOT/harness-exit-code.txt ]; do
        trace_processor $BIGTRACE -q <(echo "SELECT COUNT(*) FROM slice;") > /dev/null 2>&1
      done ) &
    LOADPID=$!
  fi
  env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 SLICE_OF=2 ROUNDS=6 CAPTURE=none KVWAIT=1 \
    INSTALL=$D/install-kvprobe7 EXPECTED_BIN_SHA=$SHA CAMPAIGN_ROOT=$ROOT \
    bash $ROOT/harness.sh > /tmp/3bda-selfintf-$arm.stdout 2>&1
  [ $arm = tpload ] && { kill $LOADPID 2>/dev/null; pkill -f "trace_processor $BIGTRACE" 2>/dev/null; }
  echo "$arm done rc=$? root=$ROOT" >> /tmp/3bda-selfintf.status
done
