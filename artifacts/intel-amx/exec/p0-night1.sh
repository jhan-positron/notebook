#!/usr/bin/env bash
# P0 night-1: build amx_microbench from the reconciled PoC tree and run the
# single-core kernel sweep. Isolation rules (docs 04 / user directive):
#   - runs ONLY in ~/workspace/tron-pr2934-reconciled (separate worktree)
#   - build pinned to the 4 fully-idle physical cores' threads, nice 19
#   - bench pinned to one fully-idle physical core (96; sibling 240 idle)
#   - no system changes; artifacts in the worktree + logs on shared home
#   - hard stop before the CI runner starts at 14:00 UTC
set -u
EXEC=~/workspace/intel-AMX/exec
LOG="$EXEC/logs/p0-night1.log"
RESULTS="$EXEC/results/p0-night1-microbench.txt"
MARKER="$EXEC/logs/p0-night1.done"
mkdir -p "$EXEC/logs" "$EXEC/results"
exec >>"$LOG" 2>&1
echo "=== p0-night1 start $(date -u +%FT%TZ) on $(hostname) ==="
rm -f "$MARKER"

ci_guard() {  # abort work if within 30 min of the 14:00 UTC CI start
  local now=$(date -u +%H%M)
  if [ "$now" -ge 1330 ] && [ "$now" -lt 1401 ]; then
    echo "CI window guard tripped at $now UTC - stopping"; echo "guard-stop" >"$MARKER"; exit 0
  fi
}

BUILD_CPUS=89,94,96,108,233,238,240,252
cd ~/workspace/tron-pr2934-reconciled || { echo "worktree missing" >"$MARKER"; exit 1; }

ci_guard
echo "--- configure (delphi preset, ingest models off) ---"
nix develop --command bash -c \
  "cmake --preset delphi -DBUILD_INGEST_MODELS=OFF" \
  || { echo "configure-failed" >"$MARKER"; exit 1; }

ci_guard
echo "--- build amx_microbench (nice 19, cpus $BUILD_CPUS, -j8) ---"
nix develop --command bash -c \
  "nice -n19 taskset -c $BUILD_CPUS cmake --build gen-delphi --target amx_microbench -j8" \
  || { echo "build-failed" >"$MARKER"; exit 1; }

ci_guard
echo "--- bench sweep on cpu 96 (fully idle physical core) ---"
BIN=./gen-delphi/amx_microbench
{
  echo "# p0-night1 microbench, $(date -u +%FT%TZ), delphi-3bda, taskset cpu 96"
  echo "# args: M ITERS variant head_dim"
  for hd in 128 64; do
    for v in dotter avx dispatch; do
      for M in 1 2 3 4 6 8 12 16; do
        echo "## M=$M variant=$v head_dim=$hd"
        taskset -c 96 $BIN "$M" 200000 "$v" "$hd" || echo "RUN-FAILED M=$M $v $hd"
      done
    done
  done
  for v in v1 v2; do
    for M in 1 4 8 16; do
      echo "## M=$M variant=$v head_dim=128"
      taskset -c 96 $BIN "$M" 200000 "$v" 128 || echo "RUN-FAILED M=$M $v"
    done
  done
} >"$RESULTS"

echo "=== p0-night1 done $(date -u +%FT%TZ) ==="
echo "ok" >"$MARKER"
