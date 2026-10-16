#!/usr/bin/env bash
# chain3.sh = part 2 of the pr1b-20261010 run: the chain2 run stopped at its our-half verdict because step F diffed
# against HEAD^2 (a merge-commit parent that the review-fix head does not have; rc 128, empty file list). This script
# reuses chain2's A/M/A3/B results for this COMMIT, runs F against MAIN_COMMIT, then the whole-machine part.
# pr1b-20261010 chain = pr1-20261010/chain.sh re-run at the review-fix head of PR #4868 (results pr1b-20261010,
# cells pr1b-E-cpu), plus step M after A: a mutation check of the extended staging test (gof::populate without the
# per-head scratch stride must fail t_phase1_integration; gof.cpp is restored and the test binary rebuilt afterwards).
# The base binary runtron.main1010 of the first run is reused (A0 skipped when it exists).
# Original header: pr1-20261010 chain (runs ON delphi-3bda, detached): build and test PR-1 of the PR 4424 split (branch
# jhan-vnnik-1-layout, create-PR1-handoff.md step 5). Fork of exec/merge4737-20261008/build-test.sh (steps A, F, B),
# exec/sync4424b-20261007/chain.sh (A0, D, E) and exec/merge4737-20261008/precheck3.sh (the whole-machine part with
# the Bill marker). Words: "our half" = socket 1 (cpus 72-143,216-287, SYSTEM_CONFIG="--instance 1,2" for the fake
# device); "the option" = TRON_K_VNNI; "AMX dispatch" = TRON_AMX_DISPATCH; "kill switch" = TRON_AMX_DISABLE=1.
#   new  = COMMIT (the PR-1 head, main merged), built into /var/tmp/jhan/tron-pr1 (runtron.pr1)
#   base = MAIN_COMMIT (the main the branch merged), built into /var/tmp/jhan/tron-main1010 (runtron.main1010)
# Our-half steps (next to production serving; each waits for the CI lease with 600 s grace and for other people):
#   A.  option on + AMX dispatch on: runtron + 6 unit tests (--skip-benchmarks), then t_llama_unit and t_amx_numerics
#       once more with the kill switch (both must exit 0)
#   A3. option on + AMX dispatch OFF (decision D2): the same targets; t_amx_numerics and t_amx_dispatch_dtype are
#       placeholders there (one SUCCEED case each) and are recorded as such
#   B.  option off (row-major K): the 5 layout-independent tests
#   F.  clang-format 19 (nix shell) on the changed C++ files, git diff --check against the merged main
#   A0. base: runtron only
#   all.done = ok only when the three builds are ok, every test binary passed, both kill-switch runs exited 0 and
#   the format checks are rc 0. The whole-machine part runs only then.
# Whole-machine steps (exec/bill-share.sh take first; refused while Bill is active -> the chain stops here):
#   1.  serving down through platformd (exec/q4b-fpga-20260921/dut.sh serving-down)
#   D.  token identity (1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens, qwen3-4b tp2): arms base,
#       new, new2 (A/A), newoff (kill switch); cells cpu p1024, cpu p8192, fpga p1024. Must match: new == new2,
#       newoff == new. new vs base is reported (expected first difference at generated token 52, issue 4444).
#   E.  performance (8 users, 256 tokens, CPU attention, prompts 1024 and 8192, 3 repetitions, arms interleaved):
#       base, new, newoff, baseoff (base with the kill switch; the reader vs the dotter with AMX off on both)
#   C.  the host test suite in the option-on tree (last: a late end costs it first)
#   4.  serving up, the Bill marker released, chain.done = ok | failed-<step>
# No step starts after END_BY (the nightly takes the lease ~03:38 UTC; long work ends before 02:30 UTC).
# Usage (on 3bda): COMMIT=<full sha> [MAIN_COMMIT=<full sha>] [END_BY=2026-10-11T01:30:00Z] bash chain.sh  (see launch.sh)
# Never edit this file while it runs (bash re-reads a running script; NFS stale-handle trap): copy to chain2.sh instead.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
B=$EXEC/i4525-20260922/build2.sh
S=$EXEC/sync4424-20261002
DUT=$EXEC/q4b-fpga-20260921/dut.sh
export NAME=pr1b-20261010
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the PR-1 head) is required}
MAIN_COMMIT=${MAIN_COMMIT:-72308ec90c80318403c4575dd9ce4a3bc9af5033}
END_BY=${END_BY:-2026-10-11T01:30:00Z}
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
WT=/var/tmp/jhan/tron-pr1
WT_A3=/var/tmp/jhan/tron-pr1nd
WT_RM=/var/tmp/jhan/tron-pr1rm
WT_BASE=/var/tmp/jhan/tron-main1010
export RT_NEW=$WT/gen/runtron.pr1
export RT_BASE=$WT_BASE/gen/runtron.main1010
export RT_HEAD=$RT_BASE   # smoke.sh and campaign.sh require RT_HEAD; no "head" arm runs here
export ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_baseoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
CONF_VNNI='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_A3='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=OFF -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
CONF_BASE='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
TESTS_6='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'
TARGETS_6="runtron $TESTS_6"
TESTS_RM='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler'
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy or another person active"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
machine() { echo "lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
MARKER_TAKEN=0
finish() { [ "$MARKER_TAKEN" = 1 ] && { bash "$EXEC/bill-share.sh" release 2>&1 | tail -1; echo "$(ts) Bill marker released"; }; echo "$(ts) machine at exit: $(machine)"; }
trap finish EXIT
exec >>"$LOG" 2>&1
rm -f "$RES/all.done" "$RES/chain.done"  # the chain2 run wrote failed-our-half; this part-2 run rewrites both
echo "=== $NAME chain started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT MAIN_COMMIT=$MAIN_COMMIT END_BY=$END_BY ==="
echo "$(ts) machine: $(machine)"
git -C "$REPO" cat-file -e "$COMMIT^{commit}" 2>/dev/null || { step_done start "$COMMIT not in the shared store: abort"; echo failed-start >"$RES/chain.done"; exit 1; }

# ---- A, M, A3, B: results of the chain2 run of this COMMIT are reused (its F step used HEAD^2, which exists only for a merge commit) ----
for f in build-pr1.done build-pr1nd.done build-pr1rm.done tests-pr1.txt mutation-result.txt mutation-reverted.txt; do
  [ -s "$RES/$f" ] || { step_done start "missing $RES/$f from the chain2 run: abort"; echo failed-start >"$RES/chain.done"; exit 1; }
done
grep -q "tip=$COMMIT" "$RES/tests-pr1.txt" || { step_done start "tests-pr1.txt is not for $COMMIT: abort"; echo failed-start >"$RES/chain.done"; exit 1; }
[ "$(git -C "$WT" rev-parse HEAD)" = "$COMMIT" ] || { step_done start "$WT is not at $COMMIT: abort"; echo failed-start >"$RES/chain.done"; exit 1; }
ks_fail=$(grep -c 'killswitch rc=[1-9]' "$RES/tests-pr1.txt")
mrc=$(sed -n 's/^mutant t_phase1_integration rc=\([0-9]*\).*/\1/p' "$RES/mutation-result.txt"); rrc=$(sed -n 's/^restored t_phase1_integration rc=\([0-9]*\).*/\1/p' "$RES/mutation-result.txt")
m_ok=$([ -n "$mrc" ] && [ "$mrc" -ne 0 ] && [ "$rrc" = 0 ] && [ "$(cat "$RES/mutation-reverted.txt")" = 0 ] && echo ok || echo failed)
step_done reuse "A=$(cat "$RES/build-pr1.done") A3=$(cat "$RES/build-pr1nd.done") B=$(cat "$RES/build-pr1rm.done") killswitch-failed=$ks_fail mutation=$m_ok (from the chain2 run)"

# ---- F. format checks (nix shell of the option-on worktree), against the merged main ----
( cd "$WT" && "$NIX" develop --accept-flake-config --command bash -c '
  echo "clang-format: $(clang-format --version 2>&1 | head -1)"
  files=$(git diff --name-only '"$MAIN_COMMIT"' HEAD -- "*.hpp" "*.cpp"); echo "files: $(echo $files | wc -w)"
  clang-format --dry-run --Werror $files; echo "clang-format rc=$?"
  git diff --check '"$MAIN_COMMIT"' HEAD -- ":!lib/**"; echo "diff-check rc=$?"
  echo "cassert-in-diff $(git diff '"$MAIN_COMMIT"' HEAD | grep -c "^+.*<cassert>")"' ) >"$RES/format-pr1.txt" 2>&1
step_done F "$(grep -E ' rc=|cassert|files:' "$RES/format-pr1.txt" | tr '\n' ' ')"

# ---- A0. base build (main, runtron only) ----
if [ ! -x "$RT_BASE" ]; then
  wait_slot "step A0"
  env RES="$RES" SRC="$REPO" COMMIT="$MAIN_COMMIT" WT="$WT_BASE" SUFFIX=main1010 CONFIGURE_ARGS="$CONF_BASE" TARGETS=runtron TESTS= JOBS=64 bash "$B"
  step_done A0 "$(cat "$RES/build-main1010.done" 2>/dev/null)"
else
  step_done A0 "base binary present, build skipped"
fi

# ---- our-half verdict ----
a=$(cat "$RES/build-pr1.done"); a3=$(cat "$RES/build-pr1nd.done" 2>/dev/null); b=$(cat "$RES/build-pr1rm.done" 2>/dev/null); a0=$([ -x "$RT_BASE" ] && echo ok || echo missing)
f=$(grep -cE ' rc=0$' "$RES/format-pr1.txt")
if [ "$a" = ok ] && [ "$a3" = ok ] && [ "$b" = ok ] && [ "$a0" = ok ] && [ "$ks_fail" = 0 ] && [ "$f" = 2 ] && [ "$m_ok" = ok ]; then echo ok >"$RES/all.done"; else echo "failed vnni=$a nodispatch=$a3 rm=$b base=$a0 killswitch-failed=$ks_fail format-ok=$f/2 mutation=$m_ok" >"$RES/all.done"; fi
step_done our-half "$(cat "$RES/all.done")"
[ "$(cat "$RES/all.done")" = ok ] || { echo "failed-our-half: $(cat "$RES/all.done")" >"$RES/chain.done"; exit 1; }

# ---- whole-machine part: the Bill marker, serving down ----
past_end && { step_done 0 "past END_BY before the whole-machine part"; echo stopped-end-by >"$RES/chain.done"; exit 1; }
wait_slot "step 0"
tout=$(bash "$EXEC/bill-share.sh" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) step_done 0 "Bill marker not taken (rc $trc): the whole-machine steps wait for jhan"; echo stopped-marker >"$RES/chain.done"; exit 1;; esac
if rinzler_active; then
  IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); the steps below retry through the guard"
fi
step_done 1 "serving: $(machine)"

# ---- D. token identity ----
export MUST_MATCH="new:new2 newoff:new"
export DEADLINE_HHMM=0130
for spec in "cpu 1024 base new new2 newoff" "cpu 8192 base new new2 newoff" "fpga 1024 base new new2 newoff"; do
  past_end && { step_done D "skipped $spec: past END_BY"; continue; }
  set -- $spec; attn=$1; prompt=$2; shift 2
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$S/smoke.sh"
  step_done D "$attn p$prompt: $(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null)"
done

# ---- E. performance ----
cells() { local p out=""; for p in "$@"; do out+="q3-4b-tp2-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp2|2|8|$p"$'\n'; done; printf '%s' "${out%$'\n'}"; }
if past_end; then step_done E "skipped: past END_BY"; else
  NAME=pr1b-E-cpu CELLS_ALL="$(cells 1024 8192)" ARMS="base new newoff baseoff" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 \
    WEDPERF_ARMS="base new newoff baseoff" WEDPERF_PAIRS="new:base newoff:baseoff newoff:new baseoff:base" bash "$S/campaign.sh"
  step_done E "$(cat "$EXEC/logs/pr1b-E-cpu.done" 2>/dev/null)"
fi

# ---- C. host suite (serving down; last) ----
if past_end; then step_done C "skipped: past END_BY"; else
  wait_slot "step C"
  env RES="$RES" WT="$WT" SUFFIX=pr1 bash "$EXEC/i4525-20260922/host-suite.sh"
  step_done C "$(cat "$RES/host-suite-pr1.done" 2>/dev/null) $(grep -E '^(build-test-host|test-host) rc=|passed|skipped|failed' "$RES/host-suite-pr1.txt" 2>/dev/null | tr '\n' ' ' | cut -c1-200)"
fi

# ---- 4. serving up, verdict ----
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$DUT" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
h=$(cat "$RES/host-suite-pr1.done" 2>/dev/null)
s1=$(cat "$RES/smoke/cpu-p1024/smoke.done" 2>/dev/null); s2=$(cat "$RES/smoke/cpu-p8192/smoke.done" 2>/dev/null); s3=$(cat "$RES/smoke/fpga-p1024/smoke.done" 2>/dev/null)
e=$(cat "$EXEC/logs/pr1b-E-cpu.done" 2>/dev/null)
if [ "$h" = ok ] && [ "$s1" = ok ] && [ "$s2" = ok ] && [ "$s3" = ok ]; then echo "ok (E: $e)" >"$RES/chain.done"; else echo "failed host=$h smoke=$s1/$s2/$s3 E=$e" >"$RES/chain.done"; fi
step_done end "$(cat "$RES/chain.done")"
echo "=== $NAME chain finished $(ts): $(cat "$RES/chain.done") ==="
