#!/usr/bin/env bash
# 24-hour multi-model sweep with monitoring — Hannah'\''s reference command,
# with one substitution: her llama-3.3-70b-instruct-good-tp{4,2} do not
# exist in tron main (ae82870ae); llama-3.1-70b-instruct-good-tp{4,2} is
# the equivalent 70B dense model there (verified against runtron'\''s
# supported-model list, 2026-07-03).
#
# Usage: run_24h_sweep.sh [output-dir]
#
# The ACTUAL benchmark command is the run-multi-sweep.sh invocation below —
# to run it manually, cd to the checkerboard repo, apply the same env
# hygiene (unset + CHECKERBOARD_MEMLOCK_KB), and paste that block.
set -u
TS=$(date -u +%Y-%m-%d)
D="${1:-/scratch/jhan/flat_freq_tests/${TS}_flat-freq_24h-sweep}"
rm -rf "$D"
mkdir -p "$D"
cd /home/jhan/workspace/run_checkerboard/checkerboard || { echo norepo > "$D/DONE"; exit 1; }

# jhan-shell landmine (SYSTEM_CONFIG overrides runtron --instance) + debug
# log levels that skew perf numbers.
unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL

date -u +"%F %T runner start" > "$D/runner_timeline.txt"

# Per-CPU freq/power capture, 30 s cadence (~50 MB over 24 h).
timeout 144000 sudo -n turbostat --quiet --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,CPU%c1,CPU%c6,PkgWatt,RAMWatt -i 30 > "$D/turbostat_per_cpu.tsv" 2> "$D/turbostat.err" &
TURBO=$!

# Flat-freq drift watch: every 10 min log the CLOS association of cpu 2
# (boot-default CLOS3). If the 2700 MHz clamp ever comes back mid-run,
# "clos:3" reappears in this log.
(
  while true; do
    echo "# $(date -u "+%F %T")"
    sudo -n /opt/intel-speed-select/intel-speed-select --cpu 2 core-power get-assoc 2>&1 | grep -E "cpu-|clos:"
    sleep 600
  done
) > "$D/flat_freq_watch.log" 2>&1 &
WATCH=$!

# ===== THE BENCHMARK COMMAND =====
CHECKERBOARD_MEMLOCK_KB=197971044 ./run-multi-sweep.sh \
  --models llama-3.1-70b-instruct-good-tp4,llama-3.1-70b-instruct-good-tp2,llama-3.1-8b-instruct-good-tp2,llama-3.1-8b-instruct-good-tp4,ingested-gpt-oss-120b-tp4,llama-3.2-3b-instruct-fast-tp4,llama-3.2-3b-instruct-fast-tp2,llama-3.2-3b-instruct-fast-tp1,mixtral-8x7b-instruct-v0.1-tp1,mixtral-8x7b-instruct-v0.1-tp2,mixtral-8x7b-instruct-v0.1-tp4 \
  -p 256,512,1024,2048,4096,6144,8192 \
  -g 256,512,1024,2048,4096,6144,8192 \
  --shared-system-prompt-lengths 64,128,256,512,512,512,512 \
  -s 0 \
  -u 2,4,8,16,32,48,64 > "$D/sweep_console.log" 2>&1
RC=$?
# =================================
echo "$RC" > "$D/SWEEP_EXIT_CODE"
date -u +"%F %T sweep exited rc=$RC" >> "$D/runner_timeline.txt"
kill "$TURBO" "$WATCH" 2>/dev/null

# Post-sweep: consolidated CSV + failure collection (README workflow),
# then copy the whole sweep tree next to the monitoring data.
SWEEP_REL=$(grep -m1 "Output directory:" "$D/sweep_console.log" | sed "s/.*Output directory: //" | tr -d "[:space:]" | sed "s|^sweeps/||")
if [ -n "$SWEEP_REL" ]; then
  ./post-processing/export_to_spreadsheet.py "sweeps/$SWEEP_REL" > "$D/export.log" 2>&1
  ./post-processing/collect_failures.py "sweeps/$SWEEP_REL" >> "$D/export.log" 2>&1
  cp -r "/var/tmp/jhan/checkerboard/sweeps/$SWEEP_REL" "$D/sweep-results" 2>> "$D/export.log"
fi
echo done > "$D/DONE"
