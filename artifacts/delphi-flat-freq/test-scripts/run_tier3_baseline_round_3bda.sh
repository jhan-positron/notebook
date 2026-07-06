#!/usr/bin/env bash
# Baseline-matched round on delphi-3bda under the 3-TIER shape
# ("tier3": app-worker cores 27-46,51-70,75-94,99-118 (+sibs) CLOS0/TF-on
# -> 4100; TRON-aux cores 0,24-26,48-50,72-74,96-98 (+sibs, incl. TX/RX
# driver cores, rinzler, platform) CLOS1 -> <=3900; rest CLOS3 <=2700).
# Applied via flat_freq_apply_tiers (v3). Same test set as the tron88
# round for direct comparison.
set -u
TS=$(date -u +%Y-%m-%d)
D="${1:-/scratch/jhan/flat_freq_tests/${TS}_tier3-4100-3900-3bda_baseline-matrix}"
rm -rf "$D"
mkdir -p "$D"
cd /home/jhan/workspace/run_checkerboard/checkerboard || { echo norepo > "$D/DONE"; exit 1; }

unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL

date -u +"%F %T runner start on $(hostname)" > "$D/runner_timeline.txt"

timeout 14400 sudo -n turbostat --quiet --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,CPU%c1,CPU%c6,PkgWatt,RAMWatt -i 30 > "$D/turbostat_per_cpu.tsv" 2> "$D/turbostat.err" &
TURBO=$!

# Tier drift watch: cpu 30 fast (clos:0), cpu 25 mid (clos:1), cpu 2 low (clos:3)
ISST=/opt/intel-speed-select/intel-speed-select
(
  while true; do
    echo "# $(date -u "+%F %T")"
    for c in 30 25 2; do
      sudo -n "$ISST" --cpu $c core-power get-assoc 2>&1 | grep -E "cpu-|clos:" | tr "\n" " "; echo
    done
    sleep 600
  done
) > "$D/shape_watch.log" 2>&1 &
WATCH=$!

# ===== THE BENCHMARK COMMAND =====
CHECKERBOARD_MEMLOCK_KB=197971044 ./run-multi-sweep.sh \
  --models ingested-gpt-oss-120b-tp4,llama-3.1-8b-instruct-good-tp4,llama-3.1-8b-instruct-good-tp2 \
  -p 256,512,1024,2048 \
  -g 256,512,1024,2048 \
  --shared-system-prompt-lengths 64,128,256,512 \
  -s 0 \
  -u 2,4,8,16,32 > "$D/sweep_console.log" 2>&1
RC=$?
# =================================
echo "$RC" > "$D/SWEEP_EXIT_CODE"
date -u +"%F %T sweep exited rc=$RC" >> "$D/runner_timeline.txt"
kill "$TURBO" "$WATCH" 2>/dev/null

SWEEP_REL=$(grep -m1 "Output directory:" "$D/sweep_console.log" | sed "s/.*Output directory: //" | tr -d "[:space:]" | sed "s|^sweeps/||")
if [ -n "$SWEEP_REL" ]; then
  ./post-processing/export_to_spreadsheet.py "sweeps/$SWEEP_REL" > "$D/export.log" 2>&1
  ./post-processing/collect_failures.py "sweeps/$SWEEP_REL" >> "$D/export.log" 2>&1
  cp -r "/var/tmp/jhan/checkerboard/sweeps/$SWEEP_REL" "$D/sweep-results" 2>> "$D/export.log"
fi
echo done > "$D/DONE"
