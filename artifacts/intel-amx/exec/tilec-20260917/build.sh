#!/usr/bin/env bash
# tilec-20260917: build + unit-test the jhan-amx-vnniK head after three comment/style
# commits (gof.hpp callback comment, "dim" wording revert on pre-existing lines, named
# tile registers in qk_vnni_128x4). Copy of vnnik5-20260916/build.sh reduced to the
# build and the four unit tests. Waits for the CI lease (ci_lease_busy) and the
# campaign flock before it uses the machine.
# Usage (on delphi-3bda): build.sh <commit>
set -u
COMMIT=$1
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=${RES:-$EXEC/results/tilec-20260917}
LOG=${LOG:-$EXEC/logs/tilec-build.log}
WT=${WT:-/var/tmp/jhan/tron-tilec}
OUR_CPUS=72-143,216-287
TESTS="t_k_vnni_layout t_amx_numerics t_amx_dispatch_dtype t_llama_unit"
NIX=/home/jhan/.nix-profile/bin/nix
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== tilec build of $COMMIT started $(ts) ==="
rm -f "$RES/build.done"
if [ ! -d "$WT/.git" ] && [ ! -f "$WT/.git" ]; then
  ( cd /home/jhan/workspace/tron-amx && git cat-file -e "$COMMIT^{commit}" && git worktree add --detach "$WT" "$COMMIT" ) || { echo "$(ts) worktree add failed"; echo worktree-failed >"$RES/build.done"; exit 1; }
else
  ( cd "$WT" && git cat-file -e "$COMMIT^{commit}" && git checkout -q --detach "$COMMIT" ) || { echo "$(ts) checkout failed"; echo checkout-failed >"$RES/build.done"; exit 1; }
fi
cd "$WT" || exit 1
echo "$(ts) worktree at $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
# The machine rule: heavy work only when the CI lease is clear.
while ci_lease_busy; do echo "$(ts) CI lease busy; build waits"; sleep 120; done
exec {LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$LOCK_FD"; do echo "$(ts) campaign flock held; build waits"; sleep 30; done
if ci_lease_busy; then echo "$(ts) CI lease became busy after the flock; giving up"; echo ci-busy >"$RES/build.done"; exit 3; fi
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c '
  set -o pipefail
  cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= 2>&1 | tail -3 || exit 2
  echo "configure ok $(date -u +%T)"
  grep -E "^TRON_AMX_DISPATCH:|^TRON_K_VNNI:" gen/CMakeCache.txt | tr "\n" " "; echo
  bin/slice route 2>&1 | tail -3 | sed "s/^/slice route: /"
  cmake --build gen --target runtron '"$TESTS"' -j96 2>&1 | grep -E "error|FAILED|warning: .*(k_vnni|save_k|amx_attn|gof)" | sed -n 1,80p
  echo "build rc=${PIPESTATUS[0]}"
' || { echo "$(ts) BUILD FAILED"; echo build-failed >"$RES/build.done"; exit 1; }
for t in $TESTS; do [ -x "$WT/gen/$t" ] || { echo "$(ts) missing binary gen/$t"; echo build-failed >"$RES/build.done"; exit 1; }; done
{
  echo "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= ; targets runtron $TESTS; built $(ts) in $(( $(date +%s) - t0 )) s on cpus $OUR_CPUS; commit $(git rev-parse HEAD)"
} >"$RES/build.txt"
echo "$(ts) build ok in $(( $(date +%s) - t0 )) s"
# unit tests (fake device; our half of the machine)
: >"$RES/tests.txt"
fail=0
for t in $TESTS; do
  t1=$(date +%s)
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 2400 "$WT/gen/$t" ) >"$RES/tests-$t.out" 2>&1
  rc=$?
  summary=$(grep -E "^All tests passed|^test cases:|^assertions:|FAILED|failed" "$RES/tests-$t.out" | tail -3 | tr "\n" " ")
  echo "$t rc=$rc $(( $(date +%s) - t1 )) s: $summary" | tee -a "$RES/tests.txt"
  [ $rc -eq 0 ] || fail=1
done
echo "$(ts) tests done fail=$fail"
[ $fail -eq 0 ] && echo ok >"$RES/build.done" || echo tests-failed >"$RES/build.done"
