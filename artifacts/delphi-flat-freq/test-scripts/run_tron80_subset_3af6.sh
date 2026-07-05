#!/usr/bin/env bash
# ~6h benchmark subset on delphi-3af6 under the strict TRON-80 shape
# (cores 27-46,51-70,75-94,99-118 + HT sibs in CLOS0/TF-on -> 4100 MHz
# under load; all other cores CLOS3 <= 2700). Shape applied separately via
# flat_freq_apply <cpulist> (v2). Subset = gpt-oss-120b-tp4 +
# llama-3.2-3b-fast-tp4, full 7x7 matrix each — the same matrices as the
# 2026-07-03 24h flat-freq sweep on delphi-3bda, for direct comparison.
#
# Usage: run_tron80_subset_3af6.sh [output-dir]
set -u
TS=$(date -u +%Y-%m-%d)
D="${1:-/scratch/jhan/flat_freq_tests/${TS}_tron80-4100-3af6_gpt-oss-3b-matrix}"
rm -rf "$D"
mkdir -p "$D"
cd /home/jhan/workspace/run_checkerboard/checkerboard || { echo norepo > "$D/DONE"; exit 1; }

# shared-NFS-home shell landmine + debug log levels
unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL

date -u +"%F %T runner start on $(hostname)" > "$D/runner_timeline.txt"

timeout 28800 sudo -n turbostat --quiet --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,CPU%c1,CPU%c6,PkgWatt,RAMWatt -i 30 > "$D/turbostat_per_cpu.tsv" 2> "$D/turbostat.err" &
TURBO=$!

# Shape drift watch: boost probe cpu 30 must stay clos:0, non-boost probe
# cpu 2 must stay clos:3. Every 10 min.
ISST=/home/jhan/workspace/intel-vs-amd/speed-select/workspace/intel-speed-select/intel-speed-select
(
  while true; do
    echo "# $(date -u "+%F %T")"
    for c in 30 2; do
      sudo -n "$ISST" --cpu $c core-power get-assoc 2>&1 | grep -E "cpu-|clos:" | tr "\n" " "; echo
    done
    sleep 600
  done
) > "$D/shape_watch.log" 2>&1 &
WATCH=$!

# ===== THE BENCHMARK COMMAND =====
CHECKERBOARD_MEMLOCK_KB=197971044 ./run-multi-sweep.sh \
  --models ingested-gpt-oss-120b-tp4,llama-3.2-3b-instruct-fast-tp4 \
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

SWEEP_REL=$(grep -m1 "Output directory:" "$D/sweep_console.log" | sed "s/.*Output directory: //" | tr -d "[:space:]" | sed "s|^sweeps/||")
if [ -n "$SWEEP_REL" ]; then
  ./post-processing/export_to_spreadsheet.py "sweeps/$SWEEP_REL" > "$D/export.log" 2>&1
  ./post-processing/collect_failures.py "sweeps/$SWEEP_REL" >> "$D/export.log" 2>&1
  cp -r "/var/tmp/jhan/checkerboard/sweeps/$SWEEP_REL" "$D/sweep-results" 2>> "$D/export.log"
fi
echo done > "$D/DONE"
