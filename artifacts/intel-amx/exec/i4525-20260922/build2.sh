#!/usr/bin/env bash
# i4525-20260922 build step (runs ON delphi-3bda): check out COMMIT of repo SRC into worktree WT, configure with
# CONFIGURE_ARGS inside nix develop, build TARGETS on our half of the machine (socket 1 cpus), copy gen/runtron to
# gen/runtron.SUFFIX when runtron is among the targets, then run each test in TESTS with the fake device
# (SYSTEM_CONFIG="--instance 1,2" gives the core set only). Writes RES/build.txt, RES/tests.txt, RES/tests-<t>.out
# and the marker RES/build.done (ok | configure-failed | build-failed rc=N | tests-failed-N | checkout-failed).
# Generic fork of exec/vnnik2-20260915/build.sh for the issue #4525 (typed KV-cache tensors) first machine test.
# build2.sh (20:58 UTC) = build.sh with the checkout fix; build.sh was left untouched because a copy of it was still running.
# Usage: RES=... SRC=<repo or worktree with the commit> COMMIT=<sha> WT=/var/tmp/jhan/tron-<name> SUFFIX=<name> \
#        CONFIGURE_ARGS='--preset cross-avx512 -DTRON_AMX_DISPATCH=ON ...' TARGETS='runtron t_llama_unit ...' \
#        TESTS='t_llama_unit t_amx_numerics ...' [TEST_ENV='TRON_AMX_DISABLE=1'] [TEST_ARGS='...'] bash build.sh
set -u
: "${RES:?}" "${SRC:?}" "${COMMIT:?}" "${WT:?}" "${SUFFIX:?}" "${CONFIGURE_ARGS:?}" "${TARGETS:?}"
TESTS=${TESTS:-}
TEST_ENV=${TEST_ENV:-}
TEST_ARGS=${TEST_ARGS:-}
JOBS=${JOBS:-96}
OUR_CPUS=${OUR_CPUS:-72-143,216-287}
NIX=/home/jhan/.nix-profile/bin/nix
LOG=${LOG:-$RES/build-$SUFFIX.log}
EXEC=/home/jhan/workspace/intel-AMX/exec
mkdir -p "$RES"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== build $SUFFIX of $COMMIT started $(ts) pid $$ on $(hostname) ==="
rm -f "$RES/build-$SUFFIX.done"
GD=$(sed -n 's/^gitdir: //p' /var/tmp/jhan/tron-main0916/.git); REPO=${GD%%/.git/*}   # the repo that owns the /var/tmp/jhan worktrees
# fetch only when the commit is not yet in the owner repo (a self-fetch of a short sha fails: "couldn't find remote ref")
if ! git -C "$REPO" cat-file -e "$COMMIT^{commit}" 2>/dev/null; then
  git -C "$REPO" fetch -q "$SRC" "$COMMIT" || { echo "$(ts) fetch of $COMMIT from $SRC failed"; echo checkout-failed >"$RES/build-$SUFFIX.done"; exit 1; }
fi
if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$COMMIT" || { echo "$(ts) worktree add failed"; echo checkout-failed >"$RES/build-$SUFFIX.done"; exit 1; }
else
  git -C "$WT" checkout -q --detach "$COMMIT" || { echo "$(ts) checkout failed"; echo checkout-failed >"$RES/build-$SUFFIX.done"; exit 1; }
fi
cd "$WT" || exit 1
echo "$(ts) worktree $WT at $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
[ "$(git rev-parse HEAD)" = "$(git rev-parse "$COMMIT^{commit}")" ] || { echo "$(ts) HEAD is not $COMMIT"; echo checkout-failed >"$RES/build-$SUFFIX.done"; exit 1; }
t0=$(date +%s)
nice -n10 taskset -c "$OUR_CPUS" "$NIX" develop --command bash -c '
  set -o pipefail
  cmake '"$CONFIGURE_ARGS"' 2>&1 | tail -3 || exit 2
  echo "configure ok $(date -u +%T): $(grep -E "^(CMAKE_BUILD_TYPE|AVX512|TRON_AMX_DISPATCH|TRON_K_VNNI|BUILD_INGEST_MODELS|TRON_IGNORE_NAN):" gen/CMakeCache.txt | tr "\n" " ")"
  cmake --build gen --target '"$TARGETS"' -j'"$JOBS"' 2>&1 | grep -E "error|FAILED|warning:" | sed -n 1,120p
  exit ${PIPESTATUS[0]}'
rc=$?
echo "$(ts) build rc=$rc in $(( $(date +%s) - t0 )) s"
if [ $rc -eq 2 ]; then echo configure-failed >"$RES/build-$SUFFIX.done"; exit 1; fi
if [ $rc -ne 0 ]; then echo "build-failed rc=$rc" >"$RES/build-$SUFFIX.done"; exit 1; fi
case " $TARGETS " in *" runtron "*) cp gen/runtron "gen/runtron.$SUFFIX" ;; esac
{
  echo "suffix $SUFFIX worktree $WT"
  echo "tip $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
  echo "configure: cmake $CONFIGURE_ARGS"
  echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|AVX512|TRON_AMX_DISPATCH|TRON_K_VNNI|BUILD_INGEST_MODELS|TRON_IGNORE_NAN|CMAKE_CXX_COMPILER):' gen/CMakeCache.txt | tr '\n' ' ')"
  echo "targets: $TARGETS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS"
  for tg in $TARGETS; do [ -e "gen/$tg" ] && sha256sum "gen/$tg"; done
  [ -e "gen/runtron.$SUFFIX" ] && { sha256sum "gen/runtron.$SUFFIX"; "./gen/runtron.$SUFFIX" --version 2>&1 | head -2; }
} >"$RES/build-$SUFFIX.txt"
cat "$RES/build-$SUFFIX.txt"
fails=0; : >"$RES/tests-$SUFFIX.txt"
for t in $TESTS; do
  ( cd "$WT" && nice -n10 taskset -c "$OUR_CPUS" env SYSTEM_CONFIG="--instance 1,2" $TEST_ENV timeout -k 60 3600 "$WT/gen/$t" $TEST_ARGS ) >"$RES/tests-$SUFFIX-$t.out" 2>&1
  trc=$?
  echo "$t rc=$trc tip=$COMMIT env=[$TEST_ENV] args=[$TEST_ARGS] $(grep -E 'test cases:|assertions|All tests passed|FAILED|AMX unavailable' "$RES/tests-$SUFFIX-$t.out" | tr '\n' ' ' | cut -c1-400)" >>"$RES/tests-$SUFFIX.txt"
  [ $trc -eq 0 ] || fails=$((fails + 1))
done
cat "$RES/tests-$SUFFIX.txt"
echo "$([ $fails -eq 0 ] && echo ok || echo "tests-failed-$fails")" >"$RES/build-$SUFFIX.done"
echo "=== build $SUFFIX finished $(ts): $(cat "$RES/build-$SUFFIX.done") ==="
