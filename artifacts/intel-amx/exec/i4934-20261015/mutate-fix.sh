#!/usr/bin/env bash
# i4934-20261015 mutation checks (runs ON delphi-3bda, our half, next to production serving): three deliberate breaks of
# the issue #4934 fix, each must make its named test fail (the PR body's "Mutation checks" open item). The tree is a copy
# of the fix commit (/var/tmp/jhan/tron-i4934mut, option on + AMX dispatch on, no ingested models), first built and tested
# unbroken with build2.sh (the three tests must pass). Then per break (mutations.py apply): the one test target is rebuilt
# inside nix develop, the test runs with the fake device, its exit status and the failing names are recorded, and git
# restores the file. A break is caught when the test exits non-zero AND its output names the expected case or section.
# Verdict mutate.done: ok | failed-<list of uncaught or unbuilt breaks> | failed-build | stopped-end-by.
# Waits like probe-fix.sh before each build: the CI lease (600 s grace), other people, the 02:10-03:45 UTC pre-CI hold.
# Usage (on 3bda): COMMIT=<full sha> END_BY=<ISO UTC> bash mutate-fix.sh
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/i4934-20261015
B=$EXEC/i4525-20260922/build2.sh
export NAME=i4934-mutate
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the fix commit) is required}
END_BY=${END_BY:?END_BY (ISO UTC) is required}
WT=/var/tmp/jhan/tron-i4934mut
OUR_CPUS=${OUR_CPUS:-72-143,216-287}   # build2.sh takes the same default; a test harness passes its own set
NIX=/home/jhan/.nix-profile/bin/nix
CONF='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
TESTS_3='t_amx_dispatch_dtype t_k_vnni_layout t_llama_unit'
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 210 ] && [ "$hm" -lt 345 ]; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do past_end && { step_done end-by "past END_BY while waiting before $1: stop"; echo stopped-end-by >"$RES/mutate.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
exec >>"$LOG" 2>&1
rm -f "$RES/mutate.done"
echo "=== $NAME started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT END_BY=$END_BY ==="
git -C "$REPO" cat-file -e "$COMMIT^{commit}" 2>/dev/null || { step_done start "$COMMIT not in the shared store: abort"; echo failed-start >"$RES/mutate.done"; exit 1; }
# 0. the unbroken tree: checkout, configure, build and run the three tests (every one must pass)
wait_slot "build mut"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT" SUFFIX=mut CONFIGURE_ARGS="$CONF" TARGETS="$TESTS_3" TESTS="$TESTS_3" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
step_done build-mut "$(cat "$RES/build-mut.done" 2>/dev/null); tests: $(cut -c1-160 "$RES/tests-mut.txt" 2>/dev/null | tr '\n' '|')"
[ "$(cat "$RES/build-mut.done" 2>/dev/null)" = ok ] || { echo failed-build >"$RES/mutate.done"; exit 1; }
# the three breaks
uncaught=""
while IFS='|' read -r m file t frag; do
  if past_end; then step_done "$m" "skipped: past END_BY"; uncaught="$uncaught $m-skipped"; continue; fi
  wait_slot "mutation $m"
  if ! python3 "$D/mutations.py" apply "$m" "$WT"; then step_done "$m" "apply failed"; uncaught="$uncaught $m-apply"; continue; fi
  echo "$(ts) $m: $(git -C "$WT" diff --stat | tail -1)"
  t0=$(date +%s)
  ( cd "$WT" && nice -n10 taskset -c "$OUR_CPUS" "$NIX" develop --command bash -c '
      set -o pipefail
      cmake --build gen --target '"$t"' -j64 2>&1 | grep -E "error|FAILED" | sed -n 1,60p
      exit ${PIPESTATUS[0]}' ) >"$RES/$m-build.log" 2>&1
  brc=$?
  echo "$(ts) $m: build of $t rc=$brc in $(( $(date +%s) - t0 )) s"
  if [ $brc -ne 0 ]; then
    step_done "$m" "build of $t failed rc=$brc (see $m-build.log)"; uncaught="$uncaught $m-build"
  else
    ( cd "$WT" && nice -n10 taskset -c "$OUR_CPUS" env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 3600 "$WT/gen/$t" --skip-benchmarks ) >"$RES/$m-$t.out" 2>&1
    rc=$?
    named=$(grep -c -F "$frag" "$RES/$m-$t.out" 2>/dev/null || true)
    summary=$(grep -E 'test cases:|assertions:|All tests passed' "$RES/$m-$t.out" | tr '\n' ' ' | cut -c1-200)
    if [ $rc -ne 0 ] && [ "${named:-0}" -gt 0 ]; then verdict=caught; else verdict=NOT-caught; uncaught="$uncaught $m"; fi
    step_done "$m" "$verdict: $t rc=$rc, output names '$frag' $named time(s); $summary"
  fi
  git -C "$WT" checkout -- "$file" && echo "$(ts) $m: $file restored ($(git -C "$WT" status --short | wc -l) files still changed)"
done < <(python3 "$D/mutations.py" list)
if [ -z "$uncaught" ]; then echo ok >"$RES/mutate.done"; else echo "failed-$(echo $uncaught | tr ' ' ',')" >"$RES/mutate.done"; fi
step_done end "$(cat "$RES/mutate.done")"
echo "=== $NAME finished $(ts): $(cat "$RES/mutate.done") ==="
