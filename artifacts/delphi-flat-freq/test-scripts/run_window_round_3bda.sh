#!/usr/bin/env bash
# 2026-07-11 window round on delphi-3bda: baseline-matched grid under the
# DEPLOYED strict tron80 shape (PR#165 boot service — this runner makes NO
# shape change, verify-only). Purpose:
#   (a) first checkerboard validation of the deployed boot-service shape,
#   (b) fresh comparability point vs the tron88 (2026-07-05) and 3-tier
#       (2026-07-06) rounds — identical grid,
#   (c) plan-item-5 aux-pressure thread sampling (unprivileged /proc only;
#       perfetto/perf need interactive sudo, not available autonomously).
# Yield contract: writes PGID to $D/RUNNER_PGID; yield_monitor_3bda.sh kills
# the whole group and cleans hugepages if a human/CI/rinzler appears.
# Usage: run_window_round_3bda.sh [output-dir]
set -u
D="${1:-/scratch/jhan/flat_freq_tests/20260711_tron80-deployed-3bda_window-round}"
rm -rf "$D"; mkdir -p "$D"
ps -o pgid= -p $$ | tr -d ' ' > "$D/RUNNER_PGID"
cd /home/jhan/workspace/run_checkerboard/checkerboard || { echo norepo > "$D/DONE"; exit 1; }
unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL
date -u +"%F %T runner start on $(hostname)" > "$D/runner_timeline.txt"

ISST=/opt/intel-speed-select/intel-speed-select
# provenance + guard: deployed shape must read strict tron80 (worker fast,
# driver+rinzler+other slow); abort rather than run under a wrong shape.
for c in 27 51 75 99 2 24 25; do
  echo -n "cpu$c " ; sudo -n "$ISST" --cpu $c core-power get-assoc 2>&1 | grep -m1 clos:
done > "$D/shape_readback_start.txt" 2>&1
grep -q "cpu27 .*clos:0" "$D/shape_readback_start.txt" || { echo bad-shape > "$D/DONE"; exit 1; }
grep -q "cpu2 .*clos:3"  "$D/shape_readback_start.txt" || { echo bad-shape > "$D/DONE"; exit 1; }
grep -E "HugePages_(Total|Free)" /proc/meminfo > "$D/hugepages_start.txt"

timeout 10800 sudo -n turbostat --quiet --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,CPU%c1,CPU%c6,PkgWatt,RAMWatt -i 30 > "$D/turbostat_per_cpu.tsv" 2> "$D/turbostat.err" &
TURBO=$!

# shape drift watch: deployed tron80 -> cpu30 clos:0, cpu25+cpu2 clos:3
( while true; do
    echo "# $(date -u "+%F %T")"
    for c in 30 25 2; do
      sudo -n "$ISST" --cpu $c core-power get-assoc 2>&1 | grep -E "cpu-|clos:" | tr "\n" " "; echo
    done
    sleep 600
  done ) > "$D/shape_watch.log" 2>&1 &
WATCH=$!

# plan-item-5 sampler: active threads of our runtron processes every 60 s
( while true; do
    echo "=== $(date -u "+%F %T") ==="
    P=$(pgrep -x runtron | paste -sd, -)
    [ -n "$P" ] && ps -Lo pid,tid,comm,psr,pcpu -p "$P" 2>/dev/null | awk 'NR==1 || $5>0.5'
    sleep 60
  done ) > "$D/thread_sampler.log" 2>&1 &
SAMPLER=$!

# one-shot deep dump ~8 min in: per-thread ctxt switches (work-vs-wait hint)
( sleep 480
  for pid in $(pgrep -x runtron); do
    for t in /proc/$pid/task/*/status; do
      grep -H -E "^(Name|voluntary_ctxt_switches|nonvoluntary_ctxt_switches)" "$t" 2>/dev/null
    done
  done ) > "$D/thread_ctxt_dump_8min.txt" 2>&1 &
DUMP=$!

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
kill "$TURBO" "$WATCH" "$SAMPLER" "$DUMP" 2>/dev/null

SWEEP_REL=$(grep -m1 "Output directory:" "$D/sweep_console.log" | sed "s/.*Output directory: //" | tr -d "[:space:]" | sed "s|^sweeps/||")
if [ -n "$SWEEP_REL" ]; then
  ./post-processing/export_to_spreadsheet.py "sweeps/$SWEEP_REL" > "$D/export.log" 2>&1
  ./post-processing/collect_failures.py "sweeps/$SWEEP_REL" >> "$D/export.log" 2>&1
  cp -r "/var/tmp/jhan/checkerboard/sweeps/$SWEEP_REL" "$D/sweep-results" 2>> "$D/export.log"
fi

# CI-machine duty: return every hugepage before tonight's nightly
find /dev/hugepages -maxdepth 1 -user jhan -name "libpos*" -delete 2> "$D/cleanup.log"
grep -E "HugePages_(Total|Free)" /proc/meminfo > "$D/hugepages_end.txt"
date -u +"%F %T runner end" >> "$D/runner_timeline.txt"
echo done > "$D/DONE"
