#!/usr/bin/env bash
# vnnik4-20260915 driver: the whole re-verification of the cleaned-up jhan-amx-vnniK head,
# in order, each step waiting for the CI lease as needed:
#   1. verify.sh <commit>: build (runtron + the 4 unit tests + Haskell suite), cost data
#      for t_k_vnni_layout (bin/slice bench --update), greedy smoke vs runtron.vnnik3,
#      cells base vs new at prompt 1024 (tp2, tp4; 2 repetitions) on our half.
#   2. the whole host test suite with TRON_K_VNNI=ON (the CI build job will compile and
#      run everything with the option after this PR): make build-test-host + make
#      test-host (bin/slice run --filter=host --exclude-tag=slow) in the same worktree,
#      SYSTEM_CONFIG="--instance 1,2" (our half), nix develop toolchain.
#   3. models.sh: FPGA-attention check and the other generated models (handoff item 3).
# Usage (on delphi-3bda): nohup chain.sh <commit> &
set -u
COMMIT=$1
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/vnnik4-20260915
RES=$EXEC/results/vnnik4-20260915
LOG=$EXEC/logs/vnnik4-chain.log
WT=/var/tmp/jhan/tron-vnnik4
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== chain.sh $COMMIT started $(ts) pid $$ ==="
bash "$C/verify.sh" "$COMMIT"
echo "$(ts) step 1 done: build=$(cat "$RES/build.done" 2>/dev/null) campaign=$(cat "$EXEC/logs/vnnik4-20260915.done" 2>/dev/null)"
if [ "$(cat "$RES/build.done" 2>/dev/null)" = ok ]; then
  while ci_lease_busy; do echo "$(ts) CI lease busy; host suite waits"; sleep 120; done
  exec {LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
  until flock -n "$LOCK_FD"; do echo "$(ts) campaign flock held; host suite waits"; sleep 30; done
  echo "$(ts) step 2: host test suite with TRON_K_VNNI=ON"
  t0=$(date +%s)
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c '
      set -o pipefail
      make build-test-host NPROC_BUILD=96 2>&1 | grep -E "error|FAILED|warning: .*(k_vnni|save_k)|Linking|ninja: no work" | tail -40; echo "build-test-host rc=${PIPESTATUS[0]}"
      grep -q "TRON_K_VNNI:BOOL=ON" gen/CMakeCache.txt && echo "cache: TRON_K_VNNI=ON kept" || echo "cache: TRON_K_VNNI NOT ON (reconfigure dropped it)"
      SYSTEM_CONFIG="--instance 1,2" make test-host 2>&1 | tail -60; echo "test-host rc=${PIPESTATUS[0]}"' ) >"$RES/host-suite.txt" 2>&1
  echo "$(ts) step 2 done in $(( $(date +%s) - t0 )) s: $(grep -E 'rc=|cache:' "$RES/host-suite.txt" | tr '\n' ' ')"
  exec {LOCK_FD}>&-
  echo "$(ts) step 3: models.sh"
  bash "$C/models.sh"
  echo "$(ts) step 3 done: $(cat "$EXEC/logs/vnnik4-models-20260915.done" 2>/dev/null)"
else
  echo "$(ts) build not ok; steps 2 and 3 skipped"
fi
echo "=== chain.sh finished $(ts) ==="
