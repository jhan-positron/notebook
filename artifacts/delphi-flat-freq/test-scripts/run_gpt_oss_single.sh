#!/usr/bin/env bash
# Single-config checkerboard benchmark of ingested-gpt-oss-120b-tp4
# (reference config from Hannah: p1024 g1024 s256, spec off, 2 inst x 4 users)
# with a system-wide turbostat capture running alongside.
#
# Usage: run_gpt_oss_single.sh [output-dir]
# Output dir defaults to a UTC-dated folder under /scratch/jhan/flat_freq_tests.
set -u
TS=$(date -u +%Y-%m-%d-%H%M%S)
D="${1:-/scratch/jhan/flat_freq_tests/${TS}_unlabeled_gpt-oss-single}"
mkdir -p "$D"
cd /home/jhan/workspace/run_checkerboard/checkerboard || { echo norepo > "$D/DONE"; exit 1; }

# Scrub personal-shell leftovers that change runtron behavior:
# - SYSTEM_CONFIG overrides --instance and makes multi-instance runs collide
#   (this is what killed the 2026-07-02 attempt1 run)
# - debug log levels skew performance comparisons vs reference runs
unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL

date -u +"%F %T runner start" > "$D/runner_timeline.txt"

timeout 2400 sudo -n turbostat --quiet --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,CPU%c1,CPU%c6,PkgWatt,RAMWatt -i 5 > "$D/turbostat_per_cpu.tsv" 2> "$D/turbostat.err" &
TURBO=$!

CHECKERBOARD_MEMLOCK_KB=197971044 ./run-multi-sweep.sh \
  --models ingested-gpt-oss-120b-tp4 \
  -p 1024 \
  -g 1024 \
  --shared-system-prompt-lengths 256 \
  -s 0 \
  -u 8 > "$D/sweep_console.log" 2>&1
RC=$?
echo "$RC" > "$D/SWEEP_EXIT_CODE"
date -u +"%F %T sweep exited rc=$RC" >> "$D/runner_timeline.txt"
sleep 12
kill "$TURBO" 2>/dev/null

# Copy the checkerboard sweep tree next to the monitoring data so each run
# folder is self-contained.
SWEEP_REL=$(grep -m1 "Output directory:" "$D/sweep_console.log" | sed "s/.*Output directory: //" | tr -d "[:space:]" | sed "s|^sweeps/||")
if [ -n "$SWEEP_REL" ] && [ -d "/var/tmp/jhan/checkerboard/sweeps/$SWEEP_REL" ]; then
  cp -r "/var/tmp/jhan/checkerboard/sweeps/$SWEEP_REL" "$D/sweep-results"
fi
echo done > "$D/DONE"
