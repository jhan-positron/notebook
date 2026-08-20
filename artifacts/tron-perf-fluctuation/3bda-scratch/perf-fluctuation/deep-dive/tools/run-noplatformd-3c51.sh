#!/bin/bash
# Intervention A/B: campaign with platformd STOPPED; guaranteed restart.
set -u
ROOT=$1
restart() { sudo -n systemctl start platformd 2>/dev/null; echo "$(date -u +%FT%TZ) platformd restarted" >> $ROOT/intervention.log; }
trap restart EXIT
sudo -n systemctl stop platformd
echo "$(date -u +%FT%TZ) platformd stopped: $(systemctl is-active platformd)" >> $ROOT/intervention.log
SHA=$(sha256sum /scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe7/bin/runtron | cut -d" " -f1)
env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 SLICE_OF=2 ROUNDS=16 CAPTURE=none KVWAIT=1 \
  INSTALL=/scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe7 EXPECTED_BIN_SHA=$SHA CAMPAIGN_ROOT=$ROOT \
  bash $ROOT/harness.sh
