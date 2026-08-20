#!/usr/bin/env bash
# F1 causal pair on the stall-mode host: control then TRON_MAX_LOGITS_CHUNK_SIZE=1.
set -u
D=/scratch/jhan/perf-fluctuation/deep-dive
SHA=$(sha256sum $D/install-kvprobe7/bin/runtron | cut -d" " -f1)
for arm in control chunk1; do
  ROOT=$D/3bda-f1${arm}-tp4-$(date -u +%Y%m%dT%H%M%SZ)
  mkdir -p $ROOT
  cp $D/tools/deepdive-campaign.sh $ROOT/harness.sh
  env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 SLICE_OF=2 ROUNDS=12 CAPTURE=none KVWAIT=1 \
    $( [ $arm = chunk1 ] && echo CHUNKSIZE=1 ) \
    INSTALL=$D/install-kvprobe7 EXPECTED_BIN_SHA=$SHA CAMPAIGN_ROOT=$ROOT \
    bash $ROOT/harness.sh > /tmp/3bda-f1$arm.stdout 2>&1
  echo "$arm done rc=$? root=$ROOT" >> /tmp/3bda-f1pair.status
done
