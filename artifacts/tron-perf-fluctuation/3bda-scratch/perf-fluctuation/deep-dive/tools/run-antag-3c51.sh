#!/usr/bin/env bash
# Memory-bandwidth antagonist campaign: 4x membw (~80 GB/s reads) on spare
# socket-0 cores (88,90,92,94) for the whole campaign; trap kills them.
# Usage: ROUNDS=12 MODEL=...-tp2 SLICE_OF=4 bash run-antag-3c51.sh
set -u
TOOLS=/scratch/jhan/perf-fluctuation/deep-dive/tools
ROOT=/scratch/jhan/perf-fluctuation/deep-dive/3c51-tp2antag-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$ROOT"
cp "$TOOLS/deepdive-campaign-3c51.sh" "$ROOT/harness.sh"

PIDS=()
for c in 88 90 92 94; do
  nohup "$TOOLS/membw" "$c" 512 100 7200 >> "$ROOT/membw.log" 2>&1 &
  PIDS+=($!)
done
restore() { kill "${PIDS[@]}" 2>/dev/null; echo "membw antagonists killed" >> "$ROOT/journal.log"; }
trap restore EXIT
sleep 2
ps -o pid,psr,comm -p "${PIDS[@]}" > "$ROOT/membw_active.txt" || { echo "REFUSED: antagonists not running"; exit 1; }

SHA=$(sha256sum /scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe9/bin/runtron | cut -d' ' -f1)
env MODEL="${MODEL:-ingested-qwen-3-4b-instruct-2507-tp2}" SLICE_OF="${SLICE_OF:-4}" ROUNDS="${ROUNDS:-12}" \
  CAPTURE=none KVWAIT=1 \
  INSTALL=/scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe9 \
  EXPECTED_BIN_SHA="$SHA" CAMPAIGN_ROOT="$ROOT" bash "$ROOT/harness.sh"
