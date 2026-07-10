#!/usr/bin/env bash
# Baseline-matched round on delphi-3bda for tron PR #3070 (new die-aware
# core map: 14 phys cores/slice, die-A cores addressed via HT-sibling ids).
# runtron built from pull/3070/head at /var/tmp/jhan/tron-pr3070.
# Shape: flat_freq_apply 7-14,24-71,79-86,96-143  (=112 phys cores fast
# ~4100 incl. sibs; other 64 threads <=2700) — validated identical to
# gen_tron_flatfreq.py output for the PR resource map.
set -u
TS=$(date -u +%Y-%m-%d)
D="${1:-/scratch/jhan/flat_freq_tests/${TS}_pr3070-tron112-4100-3bda_baseline-matrix}"
rm -rf "$D"
mkdir -p "$D"
cd /home/jhan/workspace/run_checkerboard/checkerboard || { echo norepo > "$D/DONE"; exit 1; }

unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL
export RUNTRON_BIN=/var/tmp/jhan/tron-pr3070/gen/runtron

date -u +"%F %T runner start on $(hostname) RUNTRON_BIN=$RUNTRON_BIN" > "$D/runner_timeline.txt"
"$RUNTRON_BIN" --version >> "$D/runner_timeline.txt" 2>&1 || true

timeout 14400 sudo -n turbostat --quiet --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,CPU%c1,CPU%c6,PkgWatt,RAMWatt -i 30 > "$D/turbostat_per_cpu.tsv" 2> "$D/turbostat.err" &
TURBO=$!

# Shape drift watch: cpu 7 fast (clos:0, die-A phys core), cpu 30 fast
# (clos:0), cpu 16 low (clos:3)
ISST=/opt/intel-speed-select/intel-speed-select
(
  while true; do
    echo "# $(date -u "+%F %T")"
    for c in 7 30 16; do
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
