#!/usr/bin/env bash
# vnnik7-20260916 build: the jhan-amx-vnniK tip 04ffeedccb ("tidy up": one return expression
# re-wrapped in h/tron/kernels/k_vnni.hpp, no code change) into its own worktree
# /var/tmp/jhan/tron-vnnik7 on delphi-3bda. Copy of vnnik5-20260916/build.sh with these changes:
# the CMake options of the wedperf-20260916 target build (results/wedperf-20260916/build-pr4424.txt,
# which adds BUILD_PRODUCTION_MODELS=ON), no syntax-only pre-check, and no test run (the request
# was "rebuild"; the four unit-test binaries are still built).
#
# Words used here: worktree = a second checkout of the shared repository (~/workspace/tron/.git
# owns every worktree; ~/workspace/tron-amx is the entry point, as before); nix develop = the
# project's pinned build shell; campaign flock = /var/tmp/jhan/3bda-campaign.lock, the
# cross-session lock that every campaign run and every build takes (lib-guard.sh); socket 1 =
# cpus 72-143,216-287, our half of the machine.
#
# Steps: wait for a free CI lease -> worktree add (or checkout in an existing worktree) ->
# campaign flock -> configure -> build runtron + the four unit tests on socket 1 -> plugin check
# -> copy to gen/runtron.vnnik7 -> write $RES/build.txt and the marker $RES/build.done
# (ok | build-failed rc=N | worktree-failed | checkout-failed | no-qwen).
# Usage (on delphi-3bda): build.sh [commit]
set -u
COMMIT=${1:-04ffeedccb63b0fe882979c728d82539bb466367}
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=${RES:-$EXEC/results/vnnik7-20260916}
LOG=${LOG:-$EXEC/logs/vnnik7-build.log}
WT=${WT:-/var/tmp/jhan/tron-vnnik7}
SUFFIX=${SUFFIX:-vnnik7}   # gen/runtron.$SUFFIX
OUR_CPUS=72-143,216-287
TESTS="t_k_vnni_layout t_amx_numerics t_amx_dispatch_dtype t_llama_unit"
CMAKE_OPTS="-DBUILD_INGEST_MODELS=ON -DBUILD_PRODUCTION_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS="
NIX=/home/jhan/.nix-profile/bin/nix
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== vnnik7 build of $COMMIT started $(ts) ==="
rm -f "$RES/build.done"
while ci_lease_busy; do echo "$(ts) CI lease busy; build waits"; sleep 120; done
echo "$(ts) CI lease free"
if [ ! -d "$WT/.git" ] && [ ! -f "$WT/.git" ]; then
  ( cd /home/jhan/workspace/tron-amx && git cat-file -e "$COMMIT^{commit}" && git worktree add --detach "$WT" "$COMMIT" ) || { echo "$(ts) worktree add failed"; echo worktree-failed >"$RES/build.done"; exit 1; }
else
  ( cd "$WT" && git cat-file -e "$COMMIT^{commit}" && git checkout -q --detach "$COMMIT" ) || { echo "$(ts) checkout failed"; echo checkout-failed >"$RES/build.done"; exit 1; }
fi
cd "$WT" || exit 1
echo "$(ts) worktree at $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
# The wedperf-attr campaign holds the flock only during a run (about 100 s) and re-takes it after
# a 10 s guard sample, so a 5 s poll catches the gap; the campaign then waits for this build.
exec {LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$LOCK_FD"; do echo "$(ts) campaign flock held; build waits"; sleep 5; done
echo "$(ts) campaign flock taken"
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c '
  set -o pipefail
  cmake --preset cross-avx512 '"$CMAKE_OPTS"' 2>&1 | tail -3 || exit 2
  echo "configure ok $(date -u +%T)"
  grep -E "^TRON_AMX_DISPATCH:|^TRON_K_VNNI:|^BUILD_[A-Z_]*MODELS:" gen/CMakeCache.txt | sed "s/^/cache: /"
  cmake --build gen --target runtron '"$TESTS"' -j96 2>&1 | grep -E "error|FAILED|warning: .*k_vnni" | sed -n 1,80p
  exit ${PIPESTATUS[0]}'
rc=$?
echo "$(ts) build rc=$rc in $(( $(date +%s) - t0 )) s"
if [ $rc -ne 0 ]; then echo "build-failed rc=$rc" >"$RES/build.done"; exec {LOCK_FD}>&-; exit 1; fi
strings gen/runtron | grep -q 'ingested-qwen-3-4b-instruct-2507' || { echo "$(ts) qwen plugin MISSING"; echo no-qwen >"$RES/build.done"; exec {LOCK_FD}>&-; exit 1; }
cp gen/runtron "gen/runtron.$SUFFIX"
{
  echo "suffix $SUFFIX"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
  echo "cmake --preset cross-avx512 $CMAKE_OPTS ; targets runtron $TESTS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS"
  grep -E "^TRON_AMX_DISPATCH:|^TRON_K_VNNI:|^BUILD_[A-Z_]*MODELS:" gen/CMakeCache.txt | sed 's/^/cache: /'
  sha256sum "gen/runtron.$SUFFIX" $(for t in $TESTS; do echo "gen/$t"; done)
  ( cd gen && "./runtron.$SUFFIX" --version 2>&1 | head -2 )
} >"$RES/build.txt"
cat "$RES/build.txt"
exec {LOCK_FD}>&-
echo ok >"$RES/build.done"
echo "=== vnnik7 build finished $(ts): ok ==="
