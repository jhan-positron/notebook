#!/usr/bin/env bash
# H2 intervention: hold /dev/cpu_dma_latency at 0 for a whole campaign.
# The kernel honors the request only while the file is HELD OPEN, so a holder
# process keeps the fd; the trap kills it (restoring normal idle states) no
# matter how the wrapper exits. Usage:
#   ROUNDS=12 bash run-dmalat-3c51.sh
set -u
TOOLS=/scratch/jhan/perf-fluctuation/deep-dive/tools
ROOT=/scratch/jhan/perf-fluctuation/deep-dive/3c51-dmalat0-tp4-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$ROOT"
cp "$TOOLS/deepdive-campaign-3c51.sh" "$ROOT/harness.sh"

sudo -n nohup python3 - >/dev/null 2>&1 <<'PY' &
import struct, time
f = open("/dev/cpu_dma_latency", "wb")
f.write(struct.pack("<i", 0)); f.flush()
time.sleep(14400)
PY
HOLDER=$!
restore() { sudo -n kill "$HOLDER" 2>/dev/null; echo "dma_latency holder killed, idle states restored" >> "$ROOT/journal.log"; }
trap restore EXIT

sleep 2
# proof the request took: current aggregated target must read as int32 0
sudo -n od -An -td4 /dev/cpu_dma_latency > "$ROOT/dma_latency_active.txt"
grep -q '^ *0$' "$ROOT/dma_latency_active.txt" || { echo "REFUSED: cpu_dma_latency not 0" | tee -a "$ROOT/journal.log"; exit 1; }
# idle-state snapshot on a tron core, pre and post, to prove deep states were suppressed
for s in /sys/devices/system/cpu/cpu24/cpuidle/state*; do
  echo "$(cat $s/name) usage=$(cat $s/usage) time=$(cat $s/time)"
done > "$ROOT/cpuidle_cpu24_pre.txt"

SHA=$(sha256sum /scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe9/bin/runtron | cut -d' ' -f1)
env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 SLICE_OF=2 ROUNDS="${ROUNDS:-12}" \
  CAPTURE=none KVWAIT=1 SMICOUNT=1 \
  INSTALL=/scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe9 \
  EXPECTED_BIN_SHA="$SHA" CAMPAIGN_ROOT="$ROOT" bash "$ROOT/harness.sh"
RC=$?

for s in /sys/devices/system/cpu/cpu24/cpuidle/state*; do
  echo "$(cat $s/name) usage=$(cat $s/usage) time=$(cat $s/time)"
done > "$ROOT/cpuidle_cpu24_post.txt"
exit $RC
