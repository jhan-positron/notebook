#!/usr/bin/env bash
# Background pre-build of runtron in ~/workspace/tron-router-p0 (jhan-router-p0,
# main 1407f48dd + router trace markers). Runs NEXT TO live serving: nice -n19,
# 8 spare cores (same list as p0-slot1-build.sh). The canonical, recorded build
# is r0-build.sh at slot start; this only warms the ninja cache so that build
# is incremental.
set -u
LOG=~/workspace/intel-AMX/exec/logs/r0-build-bg.log
exec >>"$LOG" 2>&1
echo "=== r0-build-bg start $(date -u +%FT%TZ) on $(hostname) ==="
cd ~/workspace/tron-router-p0 || { echo "BUILD-DONE rc=99"; exit 99; }
nix develop --command bash -c '
  cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON &&
  nice -n19 taskset -c 89,94,96,108,233,238,240,252 cmake --build gen --target runtron -j8
'
rc=$?
echo "BUILD-DONE rc=$rc $(date -u +%FT%TZ)"
exit $rc
