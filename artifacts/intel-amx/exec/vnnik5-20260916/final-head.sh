#!/usr/bin/env bash
# vnnik5-20260916 step 3: the FINAL rebased head (argument; 65a1c41d72 = d5b59b1101 plus a
# clang-format line break in t/t_llama_unit.cpp). Waits for host-suite.sh to finish, then
# in /var/tmp/jhan/tron-vnnik5: check out the head, rebuild the five targets (only the
# t_llama_unit translation unit changed), run t_llama_unit, and refresh the t_llama_unit
# cost row (bin/slice bench --update; main added 12 cases under the old row). Saves
# bench-update.txt/.diff and final-head.done. Usage (on delphi-3bda): nohup final-head.sh <commit> &
set -u
COMMIT=$1
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/vnnik5-20260916
LOG=$EXEC/logs/vnnik5-final-head.log
WT=/var/tmp/jhan/tron-vnnik5
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
TESTS="t_k_vnni_layout t_amx_numerics t_amx_dispatch_dtype t_llama_unit"
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== final-head.sh $COMMIT started $(ts) pid $$ ==="
rm -f "$RES/final-head.done"
for i in $(seq 1 540); do [ -f "$RES/host-suite.done" ] && break; sleep 20; done
[ -f "$RES/host-suite.done" ] || { echo "host-suite.done never appeared" | tee "$RES/final-head.done"; exit 1; }
echo "$(ts) host suite finished: $(tr '\n' ' ' < "$RES/host-suite.done" | cut -c1-300)"
while ci_lease_busy; do echo "$(ts) CI lease busy; waits"; sleep 120; done
exec {LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$LOCK_FD"; do echo "$(ts) campaign flock held; waits"; sleep 30; done
cd "$WT" || exit 1
( git cat-file -e "$COMMIT^{commit}" && git checkout -q --detach "$COMMIT" ) || { echo "checkout failed" | tee "$RES/final-head.done"; exit 1; }
echo "$(ts) worktree at $(git rev-parse HEAD) ($(git log -1 --format='%ci %s'))"
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c '
  set -o pipefail
  grep -q "TRON_K_VNNI:BOOL=ON" gen/CMakeCache.txt && echo "cache: TRON_K_VNNI=ON kept" || echo "cache: TRON_K_VNNI NOT ON"
  cmake --build gen --target runtron '"$TESTS"' -j96 2>&1 | grep -E "error|FAILED|Linking|ninja: no work" | tail -20
  echo "rebuild rc=${PIPESTATUS[0]}"' 
echo "$(ts) rebuild done in $(( $(date +%s) - t0 )) s"
: >"$RES/tests-final.txt"
for t in $TESTS; do
  ( nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 2400 "$WT/gen/$t" ) >"$RES/tests-final-$t.out" 2>&1
  trc=$?
  echo "$t rc=$trc tip=$COMMIT $(grep -E 'test cases:|All tests passed|FAILED|AMX unavailable' "$RES/tests-final-$t.out" | tr '\n' ' ' | cut -c1-300)" >>"$RES/tests-final.txt"
done
cat "$RES/tests-final.txt"
echo "$(ts) bench --update t_llama_unit (quiet machine)"
( env -u SYSTEM_CONFIG "$NIX" develop --command bash -c 'bin/slice bench --update t_llama_unit 2>&1 | tail -25; echo "bench rc=${PIPESTATUS[0]}"; git diff --stat -- config/test-benchmarks.json' ) >"$RES/bench-update.txt" 2>&1
git diff -- config/test-benchmarks.json >"$RES/bench-update.diff"
echo "$(ts) bench: $(tail -3 "$RES/bench-update.txt" | tr '\n' ' ')"
exec {LOCK_FD}>&-
{ echo "head $(git rev-parse HEAD)"; cat "$RES/tests-final.txt"; tail -2 "$RES/bench-update.txt"; } >"$RES/final-head.done"
echo "=== final-head.sh finished $(ts) ==="
