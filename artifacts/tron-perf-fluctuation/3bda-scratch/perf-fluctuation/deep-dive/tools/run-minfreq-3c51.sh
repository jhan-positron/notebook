#!/usr/bin/env bash
# H4 intervention: pin core frequency floor to max (scaling_min_freq = scaling_max_freq)
# on ALL CPUs, so HWP cannot downclock during near-idle spans. C-states unaffected.
# Trap restores the saved per-cpu floors no matter how the wrapper exits.
set -u
TOOLS=/scratch/jhan/perf-fluctuation/deep-dive/tools
ROOT=/scratch/jhan/perf-fluctuation/deep-dive/3c51-minfreq-tp4-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$ROOT"
cp "$TOOLS/deepdive-campaign-3c51.sh" "$ROOT/harness.sh"

for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
  echo "$c $(cat $c/scaling_min_freq)"
done > "$ROOT/minfreq_saved.txt"

restore() {
  while read -r c v; do echo "$v" | sudo -n tee "$c/scaling_min_freq" >/dev/null; done < "$ROOT/minfreq_saved.txt"
  echo "minfreq floors restored from minfreq_saved.txt" >> "$ROOT/journal.log"
}
trap restore EXIT

while read -r c _; do
  cat "$c/scaling_max_freq" | sudo -n tee "$c/scaling_min_freq" >/dev/null
done < "$ROOT/minfreq_saved.txt"
# proof: sample cores must now read min == max
for cpu in 0 24 151; do
  echo "cpu$cpu min=$(cat /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_min_freq) max=$(cat /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_max_freq)"
done > "$ROOT/minfreq_active.txt"
grep -qv "min=4400000" "$ROOT/minfreq_active.txt" && { echo "REFUSED: min-freq pin did not take" | tee -a "$ROOT/journal.log"; exit 1; }

SHA=$(sha256sum /scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe9/bin/runtron | cut -d' ' -f1)
env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 SLICE_OF=2 ROUNDS="${ROUNDS:-12}" \
  CAPTURE=none KVWAIT=1 SMICOUNT=1 RAPLCAP=1 \
  INSTALL=/scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe9 \
  EXPECTED_BIN_SHA="$SHA" CAMPAIGN_ROOT="$ROOT" bash "$ROOT/harness.sh"
