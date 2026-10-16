#!/usr/bin/env bash
# pr2-20261011 chain (runs ON delphi-3bda, detached): build and test PR-2 of the PR 4424 split (branch jhan-vnnik-2-amx,
# PR2-handoff.md step 6). Fork of exec/pr1-20261010/chain2.sh (the our-half steps A, M, A3, B, A0) and chain3.sh (step F
# against PR1_COMMIT, the whole-machine part). Words: "our half" = socket 1 (cpus 72-143,216-287, SYSTEM_CONFIG="--instance
# 1,2" for the fake device); "the option" = TRON_K_VNNI; "AMX dispatch" = TRON_AMX_DISPATCH; "kill switch" = TRON_AMX_DISABLE=1;
# "identity case" = the t_amx_numerics case "AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K".
#   new  = COMMIT (the PR-2 head), built into /var/tmp/jhan/tron-pr2 (runtron.pr2)
#   head = PR1_COMMIT (the PR-1 head), /var/tmp/jhan/tron-pr1 (runtron.pr1): reused when the worktree is at PR1_COMMIT and the
#          binary's sha256 equals the one recorded by the pr1b-20261010 build; otherwise rebuilt there
#   base = MAIN_COMMIT (the main inside PR-1), /var/tmp/jhan/tron-main1010 (runtron.main1010): reused when present
# Our-half steps (next to production serving; each waits for the CI lease with 600 s grace, for other people, and outside the
# 02:10-03:45 UTC pre-CI hold):
#   A.  option on + AMX dispatch on: runtron + 6 unit tests (--skip-benchmarks), then t_llama_unit and t_amx_numerics once more
#       with the kill switch (both must exit 0); the AMX-on t_amx_numerics must print no "AMX unavailable" line (the identity
#       case ran on real AMX)
#   M.  mutation check of the identity case: the second panel load reads token block 2 instead of block 1; the case must fail;
#       amx_attn.cpp restored; t_amx_numerics rebuilt and run whole again (must pass with A's counts)
#   A3. option on + AMX dispatch OFF (D2): the same targets; t_amx_numerics and t_amx_dispatch_dtype are placeholders there
#   B.  option off (row-major K): the 5 layout-independent tests (the identity case compiles and runs on AMX there too)
#   F.  clang-format 19 (nix shell) on the changed C++ files and git diff --check, against PR1_COMMIT (not HEAD^2)
#   A0. base: runtron only, when runtron.main1010 is missing
#   head. the PR-1 binary: reused or rebuilt (see above)
#   all.done = ok only when the three builds are ok, every test binary passed, both kill-switch runs exited 0, the identity
#   case ran on AMX in A and B, the mutation check passed, the format checks are rc 0, and the base and head binaries exist.
# Whole-machine steps (exec/bill-share.sh take first, on jhan's order to execute PR2-handoff.md; refused while Bill is active ->
# the chain stops here with chain.done=stopped-marker):
#   1.  serving down through platformd (exec/q4b-fpga-20260921/dut.sh serving-down)
#   D.  token identity (1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens, qwen3-4b tp2): arms base, new,
#       new2 (A/A), newoff (kill switch), head; cells cpu p1024, cpu p8192, fpga p1024. Must match: new == new2, newoff == new.
#       After each cell validate-smoke.py checks every arm's rc=0 line and 256 tokens (smoke.sh's verdict ignores both).
#   E.  performance (8 users, 256 tokens, CPU attention, prompts 1024 and 8192, 3 repetitions, arms interleaved): base, new,
#       newoff, head, headoff (head with the kill switch); summarizer arms and pairs set with WEDPERF_ARMS / WEDPERF_PAIRS
#   C.  the host test suite in the option-on tree (last: a late end costs it first)
#   4.  serving up, the Bill marker released, chain.done = ok | failed-<step>
# No step starts after END_BY. START_NOT_BEFORE (ISO UTC, optional) holds the whole chain until that time.
# Usage (on 3bda): COMMIT=<full sha> PR1_COMMIT=<full sha> [MAIN_COMMIT=<full sha>] [END_BY=2026-10-12T01:30:00Z]
#        [START_NOT_BEFORE=2026-10-11T13:00:00Z] bash chain.sh   (see launch.sh)
# Never edit this file while it runs (bash re-reads a running script; NFS stale-handle trap): copy to a new name instead.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/pr2-20261011
B=$EXEC/i4525-20260922/build2.sh
S=$EXEC/sync4424-20261002
DUT=$EXEC/q4b-fpga-20260921/dut.sh
export NAME=pr2-20261011
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the PR-2 head) is required}
PR1_COMMIT=${PR1_COMMIT:?PR1_COMMIT (full sha of the PR-1 head) is required}
MAIN_COMMIT=${MAIN_COMMIT:-72308ec90c80318403c4575dd9ce4a3bc9af5033}
END_BY=${END_BY:-2026-10-12T01:30:00Z}
START_NOT_BEFORE=${START_NOT_BEFORE:-}
PR1_RES=$EXEC/results/pr1b-20261010
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
WT=/var/tmp/jhan/tron-pr2
WT_A3=/var/tmp/jhan/tron-pr2nd
WT_RM=/var/tmp/jhan/tron-pr2rm
WT_BASE=/var/tmp/jhan/tron-main1010
WT_HEAD=/var/tmp/jhan/tron-pr1
export RT_NEW=$WT/gen/runtron.pr2
export RT_BASE=$WT_BASE/gen/runtron.main1010
export RT_HEAD=$WT_HEAD/gen/runtron.pr1   # the "head" and "headoff" arms of D and E (campaign.sh maps both to RT_HEAD)
export ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_baseoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
CONF_VNNI='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_A3='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=OFF -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
CONF_BASE='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
TESTS_6='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'
TARGETS_6="runtron $TESTS_6"
TESTS_RM='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler'
IDENTITY_CASE='AMX QK from the VNNI K plane is bit-identical to AMX QK from row-major K'
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 210 ] && [ "$hm" -lt 345 ]; }   # advisory pre-CI hold (prep 02:45, nightly lease ~03:37 UTC)
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
machine() { echo "lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
summary_of() { grep -E 'test cases:|assertions|All tests passed|FAILED|AMX unavailable' "$1" | tr '\n' ' ' | cut -c1-400; }
MARKER_TAKEN=0
finish() { [ "$MARKER_TAKEN" = 1 ] && { bash "$EXEC/bill-share.sh" release 2>&1 | tail -1; echo "$(ts) Bill marker released"; }; echo "$(ts) machine at exit: $(machine)"; }
trap finish EXIT
exec >>"$LOG" 2>&1
rm -f "$RES/all.done" "$RES/chain.done"
echo "=== $NAME chain started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT PR1_COMMIT=$PR1_COMMIT MAIN_COMMIT=$MAIN_COMMIT END_BY=$END_BY START_NOT_BEFORE=${START_NOT_BEFORE:-none} ==="
echo "$(ts) machine: $(machine)"
for c in "$COMMIT" "$PR1_COMMIT" "$MAIN_COMMIT"; do git -C "$REPO" cat-file -e "$c^{commit}" 2>/dev/null || { step_done start "$c not in the shared store: abort"; echo failed-start >"$RES/chain.done"; exit 1; }; done
if [ -n "$START_NOT_BEFORE" ]; then
  snb=$(date -u -d "$START_NOT_BEFORE" +%s) || { step_done start "bad START_NOT_BEFORE: abort"; echo failed-start >"$RES/chain.done"; exit 1; }
  while [ "$(date -u +%s)" -lt "$snb" ]; do left=$(( snb - $(date -u +%s) )); [ "$left" -gt 1800 ] && left=1800; echo "$(ts) holding until $START_NOT_BEFORE (next check in $((left / 60)) min)"; sleep "$left"; done
  echo "$(ts) START_NOT_BEFORE passed; machine: $(machine)"
fi

# ---- A. option on, AMX dispatch on: build, 6 tests, kill-switch runs ----
wait_slot "step A"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT" SUFFIX=pr2 CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TARGETS_6" TESTS="$TESTS_6" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
step_done A "$(cat "$RES/build-pr2.done" 2>/dev/null) $(cut -c1-160 "$RES/tests-pr2.txt" 2>/dev/null | tr '\n' ';')"
[ "$(cat "$RES/build-pr2.done" 2>/dev/null)" = ok ] || { echo failed-A >"$RES/all.done"; echo failed-A >"$RES/chain.done"; exit 1; }
a_unavail=$(grep -c 'AMX unavailable' "$RES/tests-pr2-t_amx_numerics.out" 2>/dev/null); a_cases=$(grep -oE 'in [0-9]+ test cases?' "$RES/tests-pr2-t_amx_numerics.out" | head -1)
step_done A-identity "AMX-on t_amx_numerics: 'AMX unavailable' lines=$a_unavail (expected 0), $a_cases (expected 5); $(summary_of "$RES/tests-pr2-t_amx_numerics.out")"
ks_fail=0
for t in t_llama_unit t_amx_numerics; do
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" TRON_AMX_DISABLE=1 timeout -k 60 3600 ./gen/$t --skip-benchmarks ) >"$RES/tests-pr2-$t-killswitch.out" 2>&1
  rc=$?; [ $rc -eq 0 ] || ks_fail=$((ks_fail + 1))
  echo "$t killswitch rc=$rc env=[TRON_AMX_DISABLE=1] $(summary_of "$RES/tests-pr2-$t-killswitch.out")" | tee -a "$RES/tests-pr2.txt"
done
step_done A-killswitch "failed runs: $ks_fail; t_amx_numerics 'AMX unavailable' lines=$(grep -c 'AMX unavailable' "$RES/tests-pr2-t_amx_numerics-killswitch.out") (expected 3: QK precision, VNNI identity, PV precision)"
n=$(strings "$RT_NEW" | grep -c ingested-qwen-3-4b-instruct-2507); echo "$(ts) runtron.pr2 qwen3-4b plugin strings=$n"
[ "${n:-0}" -gt 0 ] || { step_done A "runtron.pr2 lacks the qwen3-4b plugin: abort"; echo failed-plugin >"$RES/all.done"; echo failed-plugin >"$RES/chain.done"; exit 1; }
( cd "$WT" && bin/slice route ) >"$RES/slice-route.txt" 2>&1; echo "$(ts) bin/slice route: $(tr '\n' ' ' <"$RES/slice-route.txt" | cut -c1-300)"

# ---- M. mutation check of the identity case: token block 1 reads block 2's panel; the case must fail ----
K=src/tron/kernels/amx_attn.cpp
( cd "$WT" && b1=$(grep -c '(step \* TOKEN_BLOCKS_4 + 1) \* PANEL_ELEMS_512' $K) && sed -i 's/(step \* TOKEN_BLOCKS_4 + 1) \* PANEL_ELEMS_512/(step * TOKEN_BLOCKS_4 + 2) * PANEL_ELEMS_512/' $K && echo "before1=$b1 after1=$(grep -c '(step \* TOKEN_BLOCKS_4 + 1) \* PANEL_ELEMS_512' $K) after2=$(grep -c '(step \* TOKEN_BLOCKS_4 + 2) \* PANEL_ELEMS_512' $K)" ) >"$RES/mutation-applied.txt" 2>&1
m_ok=failed
if [ "$(cat "$RES/mutation-applied.txt")" = "before1=1 after1=0 after2=2" ]; then
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c 'cmake --build gen --target t_amx_numerics -j32 2>&1 | grep -E "error|FAILED" | head -5; echo "mutant build rc=${PIPESTATUS[0]}"' ) >"$RES/mutation-build.txt" 2>&1
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 1800 ./gen/t_amx_numerics --skip-benchmarks "$IDENTITY_CASE" ) >"$RES/mutation-run.out" 2>&1
  mrc=$?; echo "mutant t_amx_numerics rc=$mrc $(grep -E 'test cases:|assertions:|FAILED:|All tests passed|AMX unavailable' "$RES/mutation-run.out" | tr '\n' ' ' | cut -c1-300) captured: $(grep -oE '(seed|qi|t) := [0-9]+' "$RES/mutation-run.out" | head -3 | tr '\n' ' ')" | tee "$RES/mutation-result.txt"
  ( cd "$WT" && git checkout -- $K && git status --porcelain -- $K | wc -l ) >"$RES/mutation-reverted.txt" 2>&1
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c 'cmake --build gen --target t_amx_numerics -j32 2>&1 | grep -E "error|FAILED" | head -5; echo "restore build rc=${PIPESTATUS[0]}"' ) >>"$RES/mutation-build.txt" 2>&1
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 1800 ./gen/t_amx_numerics --skip-benchmarks ) >"$RES/tests-pr2-t_amx_numerics-restored.out" 2>&1
  rrc=$?; echo "restored t_amx_numerics rc=$rrc $(summary_of "$RES/tests-pr2-t_amx_numerics-restored.out")" | tee -a "$RES/mutation-result.txt"
  reverted=$([ "$(cat "$RES/mutation-reverted.txt")" = 0 ] && echo clean || echo DIRTY)
  same=$([ "$(grep -oE 'All tests passed \([0-9]+ assertions in [0-9]+ test cases?\)' "$RES/tests-pr2-t_amx_numerics.out")" = "$(grep -oE 'All tests passed \([0-9]+ assertions in [0-9]+ test cases?\)' "$RES/tests-pr2-t_amx_numerics-restored.out")" ] && echo same-counts || echo COUNTS-DIFFER)
  step_done M "mutant: $(grep -oE 'test cases: [0-9]+ \| [0-9]+ failed|assertions: [0-9]+ \| [0-9]+ passed \| [0-9]+ failed' "$RES/mutation-run.out" | tr '\n' '; ') (rc=$mrc, expected nonzero); amx_attn.cpp reverted=$reverted; restored rc=$rrc $same"
  [ $mrc -ne 0 ] && [ $rrc -eq 0 ] && [ "$reverted" = clean ] && [ "$same" = same-counts ] && grep -q 'FAILED' "$RES/mutation-run.out" && m_ok=ok
else
  step_done M "mutation pattern not found ($(cat "$RES/mutation-applied.txt")): skipped"; m_ok=skipped; ( cd "$WT" && git checkout -- $K )
fi

# ---- A3. option on, AMX dispatch off (D2) ----
wait_slot "step A3"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT_A3" SUFFIX=pr2nd CONFIGURE_ARGS="$CONF_A3" TARGETS="$TARGETS_6" TESTS="$TESTS_6" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
step_done A3 "$(cat "$RES/build-pr2nd.done" 2>/dev/null) $(cut -c1-160 "$RES/tests-pr2nd.txt" 2>/dev/null | tr '\n' ';') (t_amx_numerics and t_amx_dispatch_dtype are placeholders without dispatch)"

# ---- B. option off (row-major K) ----
wait_slot "step B"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT_RM" SUFFIX=pr2rm CONFIGURE_ARGS="$CONF_RM" TARGETS="$TESTS_RM" TESTS="$TESTS_RM" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
b_unavail=$(grep -c 'AMX unavailable' "$RES/tests-pr2rm-t_amx_numerics.out" 2>/dev/null)
step_done B "$(cat "$RES/build-pr2rm.done" 2>/dev/null) $(cut -c1-160 "$RES/tests-pr2rm.txt" 2>/dev/null | tr '\n' ';') row-major t_amx_numerics 'AMX unavailable' lines=$b_unavail (expected 0)"

# ---- F. format checks (nix shell of the option-on worktree), against the PR-1 head ----
( cd "$WT" && "$NIX" develop --accept-flake-config --command bash -c '
  echo "clang-format: $(clang-format --version 2>&1 | head -1)"
  files=$(git diff --name-only '"$PR1_COMMIT"' HEAD -- "*.hpp" "*.cpp"); echo "files: $(echo $files | wc -w)"
  clang-format --dry-run --Werror $files; echo "clang-format rc=$?"
  git diff --check '"$PR1_COMMIT"' HEAD -- ":!lib/**"; echo "diff-check rc=$?"
  echo "cassert-in-diff $(git diff '"$PR1_COMMIT"' HEAD | grep -c "^+.*<cassert>")"' ) >"$RES/format-pr2.txt" 2>&1
step_done F "$(grep -E ' rc=|cassert|files:' "$RES/format-pr2.txt" | tr '\n' ' ')"

# ---- A0. base build (main, runtron only) ----
if [ ! -x "$RT_BASE" ]; then
  wait_slot "step A0"
  env RES="$RES" SRC="$REPO" COMMIT="$MAIN_COMMIT" WT="$WT_BASE" SUFFIX=main1010 CONFIGURE_ARGS="$CONF_BASE" TARGETS=runtron TESTS= JOBS=64 bash "$B"
  step_done A0 "$(cat "$RES/build-main1010.done" 2>/dev/null)"
else
  step_done A0 "base binary present ($(sha256sum "$RT_BASE" | cut -c1-16), $(git -C "$WT_BASE" rev-parse --short=10 HEAD)), build skipped"
fi

# ---- head. the PR-1 binary: reuse when the worktree is at PR1_COMMIT and the sha256 matches the pr1b record, else rebuild ----
rec=$(grep -E ' gen/runtron\.pr1$' "$PR1_RES/build-pr1.txt" 2>/dev/null | awk '{print $1}')
cur=$([ -x "$RT_HEAD" ] && sha256sum "$RT_HEAD" | awk '{print $1}')
if [ -x "$RT_HEAD" ] && [ "$(git -C "$WT_HEAD" rev-parse HEAD 2>/dev/null)" = "$PR1_COMMIT" ] && [ -n "$rec" ] && [ "$cur" = "$rec" ]; then
  step_done head "runtron.pr1 reused: worktree at $PR1_COMMIT, sha256 ${cur:0:16} = pr1b-20261010 record"
else
  step_done head "runtron.pr1 rebuilt: worktree HEAD=$(git -C "$WT_HEAD" rev-parse HEAD 2>/dev/null) sha256=${cur:0:16} record=${rec:0:16}"
  wait_slot "step head"
  env RES="$RES" SRC="$REPO" COMMIT="$PR1_COMMIT" WT="$WT_HEAD" SUFFIX=pr1 CONFIGURE_ARGS="$CONF_VNNI" TARGETS=runtron TESTS= JOBS=64 bash "$B"
  step_done head-build "$(cat "$RES/build-pr1.done" 2>/dev/null)"
fi

# ---- our-half verdict ----
a=$(cat "$RES/build-pr2.done"); a3=$(cat "$RES/build-pr2nd.done" 2>/dev/null); b=$(cat "$RES/build-pr2rm.done" 2>/dev/null)
a0=$([ -x "$RT_BASE" ] && echo ok || echo missing); hd=$([ -x "$RT_HEAD" ] && echo ok || echo missing)
f=$(grep -cE ' rc=0$' "$RES/format-pr2.txt")
if [ "$a" = ok ] && [ "$a3" = ok ] && [ "$b" = ok ] && [ "$a0" = ok ] && [ "$hd" = ok ] && [ "$ks_fail" = 0 ] && [ "$f" = 2 ] && [ "$m_ok" = ok ] && [ "${a_unavail:-1}" = 0 ] && [ "${b_unavail:-1}" = 0 ]; then echo ok >"$RES/all.done"; else echo "failed vnni=$a nodispatch=$a3 rm=$b base=$a0 head=$hd killswitch-failed=$ks_fail format-ok=$f/2 mutation=$m_ok amx-unavailable-A=$a_unavail amx-unavailable-B=$b_unavail" >"$RES/all.done"; fi
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

# ---- D. token identity (5 arms) + the validator ----
export MUST_MATCH="new:new2 newoff:new"
export DEADLINE_HHMM=0130
for spec in "cpu 1024 base new new2 newoff head" "cpu 8192 base new new2 newoff head" "fpga 1024 base new new2 newoff head"; do
  past_end && { step_done D "skipped $spec: past END_BY"; continue; }
  set -- $spec; attn=$1; prompt=$2; shift 2
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$S/smoke.sh"
  v=$(python3 "$D/validate-smoke.py" "$RES/smoke/$attn-p$prompt" 256 "$@" 2>&1 | tail -1); echo "$v" >"$RES/smoke/$attn-p$prompt/validate.txt"
  step_done D "$attn p$prompt: smoke.done=$(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null) $v; $(grep -E ' vs .*(identical|first difference)' "$RES/smoke/$attn-p$prompt/smoke.txt" | tail -8 | cut -c1-110 | tr '\n' ';')"
done

# ---- E. performance (5 arms) ----
cells() { local p out=""; for p in "$@"; do out+="q3-4b-tp2-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp2|2|8|$p"$'\n'; done; printf '%s' "${out%$'\n'}"; }
if past_end; then step_done E "skipped: past END_BY"; else
  NAME=pr2-E-cpu CELLS_ALL="$(cells 1024 8192)" ARMS="base new newoff head headoff" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 \
    WEDPERF_ARMS="base new newoff head headoff" WEDPERF_PAIRS="new:base new:head newoff:new newoff:headoff head:headoff" bash "$S/campaign.sh"
  step_done E "$(cat "$EXEC/logs/pr2-E-cpu.done" 2>/dev/null); head line: $(grep -m1 '^# arms:' "$EXEC/results/pr2-E-cpu/rt-results.txt" 2>/dev/null | cut -c1-200)"
fi

# ---- C. host suite (serving down; last) ----
if past_end; then step_done C "skipped: past END_BY"; else
  wait_slot "step C"
  env RES="$RES" WT="$WT" SUFFIX=pr2 bash "$EXEC/i4525-20260922/host-suite.sh"
  step_done C "$(cat "$RES/host-suite-pr2.done" 2>/dev/null) $(grep -E '^(build-test-host|test-host) rc=|passed|skipped|failed' "$RES/host-suite-pr2.txt" 2>/dev/null | tr '\n' ' ' | cut -c1-200)"
fi

# ---- 4. serving up, verdict ----
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$DUT" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
h=$(cat "$RES/host-suite-pr2.done" 2>/dev/null)
sm() { [ "$(cat "$RES/smoke/$1/smoke.done" 2>/dev/null)" = ok ] && [ "$(cat "$RES/smoke/$1/validate.txt" 2>/dev/null)" = "VALIDATE ok" ] && echo ok || echo "$(cat "$RES/smoke/$1/smoke.done" 2>/dev/null)/$(cat "$RES/smoke/$1/validate.txt" 2>/dev/null | cut -c1-40)"; }
s1=$(sm cpu-p1024); s2=$(sm cpu-p8192); s3=$(sm fpga-p1024)
e=$(cat "$EXEC/logs/pr2-E-cpu.done" 2>/dev/null)
if [ "$h" = ok ] && [ "$s1" = ok ] && [ "$s2" = ok ] && [ "$s3" = ok ]; then echo "ok (E: $e)" >"$RES/chain.done"; else echo "failed host=$h smoke=$s1/$s2/$s3 E=$e" >"$RES/chain.done"; fi
step_done end "$(cat "$RES/chain.done")"
echo "=== $NAME chain finished $(ts): $(cat "$RES/chain.done") ==="
