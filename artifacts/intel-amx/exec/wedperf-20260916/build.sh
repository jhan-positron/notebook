#!/usr/bin/env bash
# wedperf-20260916 build: one runtron binary from one commit with the given CMake options,
# into its own worktree under /var/tmp/jhan. Fork of exec/vnnik6-20260916/build.sh; the only
# change is the model check: every CI perf model slug (systems_test scripts/perf.py at
# 6b20db0) must be in the build's selected runtime slugs, which needs
# -DBUILD_PRODUCTION_MODELS=ON (llama-3.3-70b-instruct-good is tagged production only).
#
# Words used here: worktree = a second checkout of the shared repository
# (~/workspace/tron/.git owns every worktree; ~/workspace/tron-amx is one of them and is
# used as the entry point); nix develop = the project's pinned build shell; preset
# cross-avx512 = the CMake preset of every campaign binary so far.
#
# Steps: wait until the CI lease is free (SKIP_LEASE_WAIT=1 skips this) -> worktree add
# (or checkout in an existing worktree) -> campaign flock -> configure -> build runtron on
# our socket -> check the selected model slugs -> copy to gen/runtron.<suffix> -> write
# $RES/build-<suffix>.txt and the marker $RES/build-<suffix>.done
# (ok | build-failed rc=N | worktree-failed | checkout-failed | missing-models | cache-mismatch ...).
# Usage (on delphi-3bda): build.sh <commit> <worktree> <suffix> [extra cmake -D options...]
set -u
COMMIT=$1; WT=$2; SUFFIX=$3; shift 3
EXTRA="$*"
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=${RES:-$EXEC/results/wedperf-20260916}
LOG=${LOG:-$EXEC/logs/wedperf-build-$SUFFIX.log}
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
CI_SLUGS="llama-3.2-3b-instruct-fast-tp2 llama-3.1-8b-instruct-good-tp2 llama-3.3-70b-instruct-good-tp2 llama-3.3-70b-instruct-good-tp4 mixtral-8x7b-instruct-v0.1-tp2 qwen-2.5-32b-it-fast-tp2 ingested-qwen-3-4b-instruct-2507-tp2 ingested-qwen-3-4b-instruct-2507-tp4 gemma-2-9b-it-fast-tp2 ingested-gpt-oss-120b-tp4 ingested-gemma-4-31b-it-tp2"
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== wedperf build $SUFFIX of $COMMIT started $(ts) extra=[$EXTRA] ==="
rm -f "$RES/build-$SUFFIX.done"
if [ "${SKIP_LEASE_WAIT:-0}" != 1 ]; then
  while ci_lease_busy; do echo "$(ts) CI lease busy; build waits"; sleep 120; done
  echo "$(ts) CI lease free"
fi
if [ ! -d "$WT/.git" ] && [ ! -f "$WT/.git" ]; then
  ( cd /home/jhan/workspace/tron-amx && git cat-file -e "$COMMIT^{commit}" && git worktree add --detach "$WT" "$COMMIT" ) || { echo "$(ts) worktree add failed"; echo worktree-failed >"$RES/build-$SUFFIX.done"; exit 1; }
else
  ( cd "$WT" && git cat-file -e "$COMMIT^{commit}" && git checkout -q --detach "$COMMIT" ) || { echo "$(ts) checkout failed"; echo checkout-failed >"$RES/build-$SUFFIX.done"; exit 1; }
fi
cd "$WT" || exit 1
echo "$(ts) worktree at $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
exec {LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$LOCK_FD"; do echo "$(ts) campaign flock held; build waits"; sleep 30; done
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c '
  set -o pipefail
  cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DCMAKE_CXX_FLAGS= '"$EXTRA"' 2>&1 | tail -3 || exit 2
  echo "configure ok $(date -u +%T)"
  grep -E "^TRON_AMX_DISPATCH:|^TRON_K_VNNI:|^BUILD_[A-Z_]*MODELS:" gen/CMakeCache.txt | sed "s/^/cache: /"
  cmake --build gen --target runtron -j96 2>&1 | grep -E "error|FAILED" | sed -n 1,80p
  exit ${PIPESTATUS[0]}'
rc=$?
echo "$(ts) build rc=$rc in $(( $(date +%s) - t0 )) s"
if [ $rc -ne 0 ]; then echo "build-failed rc=$rc" >"$RES/build-$SUFFIX.done"; exec {LOCK_FD}>&-; exit 1; fi
if [ -n "${EXPECT_K_VNNI:-}" ]; then
  have=$(grep -E "^TRON_K_VNNI:BOOL=" gen/CMakeCache.txt | cut -d= -f2)
  if [ "${have:-OFF}" != "$EXPECT_K_VNNI" ]; then echo "$(ts) TRON_K_VNNI in the cache is '${have:-unset}', expected $EXPECT_K_VNNI"; echo "cache-mismatch TRON_K_VNNI=${have:-unset}" >"$RES/build-$SUFFIX.done"; exec {LOCK_FD}>&-; exit 1; fi
fi
if [ -n "${EXPECT_AMX_DISPATCH:-}" ]; then
  have=$(grep -E "^TRON_AMX_DISPATCH:BOOL=" gen/CMakeCache.txt | cut -d= -f2)
  if [ "${have:-OFF}" != "$EXPECT_AMX_DISPATCH" ]; then echo "$(ts) TRON_AMX_DISPATCH in the cache is '${have:-unset}', expected $EXPECT_AMX_DISPATCH"; echo "cache-mismatch TRON_AMX_DISPATCH=${have:-unset}" >"$RES/build-$SUFFIX.done"; exec {LOCK_FD}>&-; exit 1; fi
fi
# every CI perf slug must be a selected runtime slug of this build (the plan file lists them)
missing=""
for s in $CI_SLUGS; do
  sed -n '/^set(TRON_SELECTED_RUNTIME_MODEL_SLUGS/,/^)/p' gen/selected_models.cmake | grep -q "\"$s\"" || missing="$missing $s"
done
if [ -n "$missing" ]; then echo "$(ts) CI model slugs MISSING from the selected runtime slugs:$missing"; echo "missing-models:$missing" >"$RES/build-$SUFFIX.done"; exec {LOCK_FD}>&-; exit 1; fi
cp gen/runtron "gen/runtron.$SUFFIX"
{
  echo "suffix $SUFFIX"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
  echo "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DCMAKE_CXX_FLAGS= $EXTRA ; target runtron; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS"
  grep -E "^TRON_AMX_DISPATCH:|^TRON_K_VNNI:|^BUILD_[A-Z_]*MODELS:" gen/CMakeCache.txt | sed 's/^/cache: /'
  echo "selected runtime slugs: $(sed -n '/^set(TRON_SELECTED_RUNTIME_MODEL_SLUGS/,/^)/p' gen/selected_models.cmake | grep -c '"')"
  sha256sum "gen/runtron.$SUFFIX"
  ( cd gen && "./runtron.$SUFFIX" --version 2>&1 | head -2 )
} >"$RES/build-$SUFFIX.txt"
cat "$RES/build-$SUFFIX.txt"
exec {LOCK_FD}>&-
echo ok >"$RES/build-$SUFFIX.done"
echo "=== wedperf build $SUFFIX finished $(ts): ok ==="
