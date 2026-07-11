#!/bin/bash
# ci_workload_profile.sh — plan item 6b: workload-shape profiling during a FULL
# CI/nightly run on delphi-3bda. OBSERVATIONAL ONLY: never starts/stops tron;
# refuses to run unless serving processes are already up.
#
# Usage (during an approved window, while the nightly is in its gpt-oss phase):
#   sudo -v && /scratch/jhan/flat_freq_tests/scripts/ci_workload_profile.sh
# Options:
#   --check           preflight only (no sudo, no capture) — safe any time
#   --model SUBSTR    require this substring in an engine cmdline (default: gpt-oss)
#   --any             skip the model check (profile whatever is serving)
#   --secs N          perfetto trace length (default 60; perf runs 30)
#
# Captures (total ~2 min):
#   1. perfetto system trace (sched_switch/waking + cpu_frequency/idle) via
#      tracebox — the per-thread work-vs-wait timeline
#   2. perf record -a -g (30 s) + per-engine perf stat (IPC) — where cycles go
#      (root bypasses perf_event_paranoid=4; no sysctl change needed)
#   3. provenance: engine cmdlines, per-thread CPU/wchan/ctxt-switch snapshots
#      (before+after), turbostat, isst shape probes
#
# Analysis afterwards:
#   /scratch/jhan/tools/trace_processor -q <sql> <trace.pftrace>   (on-host SQL)
#   or copy the .pftrace to a laptop and open https://ui.perfetto.dev
set -u
TOOLS=/scratch/jhan/tools
CFG=$TOOLS/ci_profile_trace.cfg
BASE=/scratch/jhan/flat_freq_tests
MODEL=gpt-oss; CHECK=0; ANY=0; SECS=60
while [ $# -gt 0 ]; do case "$1" in
  --check) CHECK=1;; --any) ANY=1;; --model) MODEL=$2; shift;; --secs) SECS=$2; shift;;
  *) echo "unknown arg: $1" >&2; exit 2;; esac; shift; done

fail=0
for t in "$TOOLS/tracebox" /usr/bin/perf /usr/bin/turbostat; do
  [ -x "$t" ] || { echo "MISSING: $t" >&2; fail=1; }
done
[ -f "$CFG" ] || { echo "MISSING: $CFG" >&2; fail=1; }
# engine pids: rinzler-launched runtron/rinzler processes (bracket avoids self-match)
mapfile -t PIDS < <(pgrep -f '[r]inzler|[r]untron' | while read -r p; do
  [ -r "/proc/$p/cmdline" ] && tr '\0' ' ' < "/proc/$p/cmdline" | grep -q -e rinzler -e runtron && echo "$p"; done)
if [ ${#PIDS[@]} -eq 0 ]; then echo "NO ENGINE PROCESSES RUNNING — nothing to profile (this script never starts tron)." >&2; exit 1; fi
if [ "$ANY" -eq 0 ]; then
  hit=0
  for p in "${PIDS[@]}"; do tr '\0' ' ' < "/proc/$p/cmdline" | grep -q "$MODEL" && hit=1; done
  [ $hit -eq 1 ] || { echo "engines running but none match model '$MODEL' — wait for that phase or pass --any" >&2; exit 1; }
fi
echo "engine pids: ${PIDS[*]}"
[ $fail -eq 0 ] || exit 1
if [ "$CHECK" -eq 1 ]; then echo "PREFLIGHT OK (tools + engines present). Run without --check during the window."; exit 0; fi
sudo -n true 2>/dev/null || { echo "need cached sudo: run 'sudo -v' first" >&2; exit 1; }

OUT=$BASE/$(date +%Y%m%d-%H%M%S)_ci-workload-profile-$(hostname -s)
mkdir -p "$OUT"; cd "$OUT"
echo "output: $OUT"

# --- provenance (before) ---
for p in "${PIDS[@]}"; do echo "== $p =="; tr '\0' ' ' < "/proc/$p/cmdline"; echo; done > engine-cmdlines.txt
ps -Lo pid,tid,comm,psr,pcpu,wchan:24 -p "$(IFS=,; echo "${PIDS[*]}")" > threads-before.txt
for p in "${PIDS[@]}"; do for t in /proc/$p/task/*/status; do
  awk -v f="$t" '/^Name|^Pid|^voluntary_ctxt|^nonvoluntary_ctxt/ {print f": "$0}' "$t"; done; done > ctxt-before.txt
ISST="sudo -n /opt/intel-speed-select/intel-speed-select"
{ $ISST --cpu 27 core-power get-assoc; $ISST --cpu 0 core-power get-config --clos 3; } > isst-shape.txt 2>&1
sudo -n turbostat --quiet --show Package,Core,CPU,Busy%,Bzy_MHz -i 5 -n 2 > turbostat-before.txt 2>&1 &
TSPID=$!

# --- 1. perfetto system trace ---
sed "s/^duration_ms:.*/duration_ms: $((SECS*1000))/" "$CFG" > trace.cfg
echo "[1/3] perfetto trace ($SECS s)..."
sudo -n "$TOOLS/tracebox" -c trace.cfg --txt -o ci-workload.pftrace || echo "TRACEBOX FAILED" >&2

# --- 2. perf ---
echo "[2/3] perf record -a -g (30 s)..."
sudo -n perf record -a -g -F 199 -o perf-system.data -- sleep 30 2> perf-record.log || echo "PERF RECORD FAILED" >&2
echo "[2/3] perf stat per engine (10 s)..."
for p in "${PIDS[@]}"; do
  sudo -n perf stat -e cycles,instructions,task-clock -p "$p" -- sleep 10 2> "perf-stat-$p.txt"; done
sudo -n chown "$USER": perf-system.data ci-workload.pftrace 2>/dev/null

# --- 3. provenance (after) ---
ps -Lo pid,tid,comm,psr,pcpu,wchan:24 -p "$(IFS=,; echo "${PIDS[*]}")" > threads-after.txt
for p in "${PIDS[@]}"; do for t in /proc/$p/task/*/status; do
  awk -v f="$t" '/^Name|^Pid|^voluntary_ctxt|^nonvoluntary_ctxt/ {print f": "$0}' "$t"; done; done > ctxt-after.txt
wait $TSPID 2>/dev/null
echo "[3/3] done."; ls -la "$OUT"; echo "DONE $OUT"
