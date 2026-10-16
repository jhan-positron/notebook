#!/usr/bin/env bash
# pr4fwd-20261013 (runs ON delphi-3bda, detached, our half only): builds and runs the new t_heterogeneous_scheduler case of
# the probe commit COMMIT (branch jhan-vnnik-4-probe-fwdtest = PR #4901 head e7d06a1267 + t/heterogeneous_scheduler_compile.cpp),
# then the discriminating mutation (the convert_pending_k_blocks() call removed from model::state::forward: the case must
# fail), the restore, and the option-off build (TRON_K_VNNI=OFF: the case passes on its row-major branch). Why: codex's
# review of PR #4901, tron-code-review: no test reached the forward-end conversion through the forward.
# Waits for the forced-run probe (exec/results/p83-20261013/probe.done) so that no build runs during the whole-machine
# measurements, then for the CI lease, other people and the pre-CI hold. Our half only: build2.sh pins the build to cpus
# 72-143,216-287 and runs the tests with SYSTEM_CONFIG="--instance 1,2". No marker, no serving change.
# Usage (on 3bda): COMMIT=<full sha> [END_BY=<ISO UTC>] [CHAIN_WAIT=0] bash test-forward.sh
# Outputs: exec/results/pr4fwd-20261013/ (steps.txt, build-*.txt, tests-*.txt, case-*.out, mutation-*.txt, test.done),
# log exec/logs/pr4fwd-20261013.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
B=$EXEC/i4525-20260922/build2.sh
export NAME=pr4fwd-20261013
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the probe commit) is required}
END_BY=${END_BY:-2026-10-14T01:30:00Z}
P83_DONE=$EXEC/results/p83-20261013/probe.done
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
WT=/var/tmp/jhan/tron-pr4t
WT_RM=/var/tmp/jhan/tron-pr4trm
CONF_VNNI='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
T=t_heterogeneous_scheduler
CASE='model::state::forward converts the K block its decode step completes at the forward end'
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 210 ] && [ "$hm" -lt 345 ]; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do past_end && { step_done end-by "past END_BY while waiting before $1: stop"; echo stopped-end-by >"$RES/test.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
summary_of() { grep -E 'test cases:|assertions|All tests passed|FAILED|AMX unavailable' "$1" | tr '\n' ' ' | cut -c1-400; }
nix_build_target() {  # nix_build_target <worktree> <target> <label>
  ( cd "$1" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'cmake --build gen --target '"$2"' -j32 2>&1 | grep -E "error|FAILED" | head -5; echo "'"$3"' build rc=${PIPESTATUS[0]}"' )
}
run_case() {  # run_case <worktree> <binary> <spec> > out; rc returned
  ( cd "$1" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 1800 "./gen/$2" --skip-benchmarks "$3" )
}
mutate() {  # mutate <file> <old> <new>: exact replacement, exactly one match
  python3 - "$1" "$2" "$3" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); old, new = sys.argv[2], sys.argv[3]
s = p.read_text(); n = s.count(old)
print(f"before={n}", end=" ")
if n != 1: print("FAIL: the old text does not occur exactly once"); sys.exit(1)
s = s.replace(old, new); p.write_text(s)
print(f"after-old={s.count(old)} after-new={s.count(new)}")
PY
}
exec >>"$LOG" 2>&1
rm -f "$RES/test.done"
echo "=== $NAME started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT END_BY=$END_BY ==="
git -C "$REPO" cat-file -e "$COMMIT^{commit}" 2>/dev/null || { step_done start "$COMMIT not in the shared store: abort"; echo failed-start >"$RES/test.done"; exit 1; }
if [ "${CHAIN_WAIT:-1}" = 1 ]; then w=0; while [ ! -s "$P83_DONE" ]; do past_end && { step_done end-by "past END_BY while waiting for the forced-run probe: stop"; echo stopped-end-by >"$RES/test.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting for the forced-run probe ($P83_DONE)"; w=1; sleep 120; done; echo "$(ts) forced-run probe over: $(cat "$P83_DONE")"; fi
# ---- A. option on: build the test binary, run it whole, then the new case alone ----
wait_slot "step A"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT" SUFFIX=pr4t CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$T" TESTS="$T" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
step_done A "$(cat "$RES/build-pr4t.done" 2>/dev/null) $(cut -c1-200 "$RES/tests-pr4t.txt" 2>/dev/null | tr '\n' ';')"
[ "$(cat "$RES/build-pr4t.done" 2>/dev/null)" = ok ] || { echo failed-A >"$RES/test.done"; exit 1; }
run_case "$WT" "$T" "$CASE" >"$RES/case-pr4t.out" 2>&1; a_rc=$?
step_done A-case "rc=$a_rc (expected 0) $(summary_of "$RES/case-pr4t.out")"
# ---- M. the discriminating mutation: the forward's conversion call removed ----
past_end && { step_done M "skipped: past END_BY"; echo "failed-end-by" >"$RES/test.done"; exit 1; }
wait_slot "step M"
m_old=$'      convert_pending_k_blocks();\n\n      // Launch logit delivery\n'
m_new=$'      // Launch logit delivery\n'
{ echo "mutation: model.hpp forward without convert_pending_k_blocks(); $(ts)"; mutate "$WT/h/tron/models/model.hpp" "$m_old" "$m_new"; } | tee "$RES/mutation-fwd.txt"
grep -q 'FAIL' "$RES/mutation-fwd.txt" && { step_done M "mutation text not found: abort"; echo failed-M >"$RES/test.done"; exit 1; }
nix_build_target "$WT" "$T" mutant >>"$RES/mutation-fwd.txt" 2>&1
run_case "$WT" "$T" "$CASE" >"$RES/case-mutant.out" 2>&1; m_rc=$?
m_failed=$(grep -c 'FAILED' "$RES/case-mutant.out")
step_done M "mutant rc=$m_rc (expected non-zero) FAILED lines=$m_failed; $(summary_of "$RES/case-mutant.out"); $(grep -E 'converted_blocks\(\) == BLOCK_0|REQUIRE\(' "$RES/case-mutant.out" | head -2 | tr '\n' ' ' | cut -c1-200)"
git -C "$WT" checkout -- h/tron/models/model.hpp; echo "restored: $(git -C "$WT" status --porcelain | wc -l) changed files" | tee -a "$RES/mutation-fwd.txt"
nix_build_target "$WT" "$T" restored >>"$RES/mutation-fwd.txt" 2>&1
run_case "$WT" "$T" "$CASE" >"$RES/case-restored.out" 2>&1; r_rc=$?
step_done M-restored "rc=$r_rc (expected 0) $(summary_of "$RES/case-restored.out")"
# ---- B. option off ----
past_end && { step_done B "skipped: past END_BY"; echo "failed-end-by" >"$RES/test.done"; exit 1; }
wait_slot "step B"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT_RM" SUFFIX=pr4trm CONFIGURE_ARGS="$CONF_RM" TARGETS="$T" TESTS="$T" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
step_done B "$(cat "$RES/build-pr4trm.done" 2>/dev/null) $(cut -c1-200 "$RES/tests-pr4trm.txt" 2>/dev/null | tr '\n' ';')"
run_case "$WT_RM" "$T" "$CASE" >"$RES/case-pr4trm.out" 2>&1; b_rc=$?
step_done B-case "rc=$b_rc (expected 0) $(summary_of "$RES/case-pr4trm.out")"
a=$(cat "$RES/build-pr4t.done"); b=$(cat "$RES/build-pr4trm.done" 2>/dev/null)
if [ "$a" = ok ] && [ "$a_rc" = 0 ] && [ "$m_rc" != 0 ] && [ "$m_failed" -gt 0 ] && [ "$r_rc" = 0 ] && [ "$b" = ok ] && [ "$b_rc" = 0 ]; then echo ok >"$RES/test.done"
else echo "failed vnni=$a case=$a_rc mutant=$m_rc/$m_failed restored=$r_rc off=$b case-off=$b_rc" >"$RES/test.done"; fi
step_done end "$(cat "$RES/test.done")"
echo "=== $NAME finished $(ts): $(cat "$RES/test.done") ==="
