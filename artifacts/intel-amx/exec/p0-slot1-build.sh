#!/usr/bin/env bash
# Slot-1 phase A: build qwen-capable runtron from current main in the isolated
# tron-amx worktree. Safe to run while serving is still up (nice 19, safe cores);
# once serving stops we rebuild/continue at full width (ninja is incremental).
set -u
EXEC=~/workspace/intel-AMX/exec
LOG="$EXEC/logs/p0-slot1-build.log"
MARKER="$EXEC/logs/p0-slot1-build.done"
mkdir -p "$EXEC/logs"
exec >>"$LOG" 2>&1
echo "=== slot1 build start $(date -u +%FT%TZ) ==="
rm -f "$MARKER"
cd ~/workspace/tron-amx || { echo tree-missing >"$MARKER"; exit 1; }

# If serving is down, use wide parallelism; else restrict to safe threads.
if pgrep -x rinzler >/dev/null; then
  CPUS=89,94,96,108,233,238,240,252; J=8
else
  CPUS=0-287; J=96
fi
echo "serving_up=$(pgrep -cx rinzler || true) cpus=$CPUS j=$J"

nix develop --command bash -c \
  "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON && \
   nice -n19 taskset -c $CPUS cmake --build gen --target runtron -j$J" \
  || { echo build-failed >"$MARKER"; exit 1; }

# confirm the qwen plugin made it in
if strings gen/runtron | grep -q 'ingested-qwen-3-4b-instruct-2507'; then
  echo "qwen plugin present in runtron"
  echo ok >"$MARKER"
else
  echo "qwen plugin MISSING from runtron"
  echo built-but-no-qwen >"$MARKER"
fi
echo "=== slot1 build end $(date -u +%FT%TZ) ==="
