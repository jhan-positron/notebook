#!/usr/bin/env bash
# pr3-20261012 chain (runs ON delphi-3bda, detached): build and test PR-3 of the PR 4424 split (branch
# jhan-vnnik-3-shared-save, PR3-handoff.md step 6). Fork of exec/pr2-20261011/chain.sh. Words: "our half" = socket 1
# (cpus 72-143,216-287, SYSTEM_CONFIG="--instance 1,2" for the fake device); "the option" = TRON_K_VNNI; "AMX dispatch" =
# TRON_AMX_DISPATCH; "kill switch" = TRON_AMX_DISABLE=1; "identity case" = the t_amx_numerics case "AMX QK from the VNNI K
# plane is bit-identical to AMX QK from row-major K"; "block-save case" = the t_k_vnni_layout case "VNNI K block save
# equals the per-token row store, bit for bit"; "save_k case" = the t_llama_unit case "save_k stores every token's K row
# once, grouped by page block, alone or with helper threads".
#   new  = COMMIT (the PR-3 head), built into /var/tmp/jhan/tron-pr3 (runtron.pr3)
#   head = PR2_COMMIT (the PR-2 head), /var/tmp/jhan/tron-pr2 (runtron.pr2): reused when the worktree is at PR2_COMMIT and
#          the binary's sha256 equals the one recorded by the pr2-20261011 build; otherwise rebuilt there
#   base = MAIN_COMMIT (the main inside PR-1), /var/tmp/jhan/tron-main1010 (runtron.main1010): reused when present
# Our-half steps (next to production serving; each waits for the CI lease with 600 s grace, for other people, and outside the
# 02:10-03:45 UTC pre-CI hold):
#   A.   option on + AMX dispatch on: runtron + 6 unit tests (--skip-benchmarks), then t_llama_unit and t_amx_numerics once
#        more with the kill switch (both must exit 0); the AMX-on t_amx_numerics must print no "AMX unavailable" line;
#        runtron.pr3 must carry the qwen3-4b tp2 and tp4 plugins
#   plugin check. every generated plugin has main_k == helper_k == kv_ops > 0 and other_k == helper_fn == 0 (plugin-calls.py)
#   M1.  mutation check of the block store: block c's rows land in block c ^ 1's panels; the block-save case must fail
#   M2.  mutation check of the work-unit cut: a block change inside a page no longer cuts; the save_k case must fail
#   A2.  the Haskell suite (bin/ingest-cabal test): rc 0, Failed: 0
#   A3.  option on + AMX dispatch OFF (D2): the same targets; t_amx_numerics and t_amx_dispatch_dtype are placeholders there
#   B.   option off (row-major K): the 5 layout-independent tests (the block-save case and the save_k case run there too)
#   F.   clang-format 19 on the 7 changed C++ files, fourmolu on the 2 Haskell files, git diff --check, cassert count
#        (nix shell, against PR2_COMMIT); lint-notes in the lint shell when it is available within 10 min (recorded only)
#   A0.  base: runtron only, when runtron.main1010 is missing
#   head. the PR-2 binary: reused or rebuilt (see above)
#   all.done = ok only when the three builds are ok and every test binary passed, both kill-switch runs exited 0, the
#   identity case ran on AMX in A and B, the plugin check passed, both mutation checks passed, A2 is rc 0 with Failed: 0,
#   the three format checks are rc 0 and the cassert count is 0, and the base and head binaries exist.
# Whole-machine steps (exec/bill-share.sh take first, on jhan's order to execute PR3-handoff.md; refused while Bill is
# active -> the chain stops here with chain.done=stopped-marker):
#   1.   serving down through platformd (exec/q4b-fpga-20260921/dut.sh serving-down)
#   D.   token identity (1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens, qwen3-4b tp2): arms base, new,
#        new2 (A/A), newoff (kill switch), head; cells cpu p1024, cpu p8192, fpga p1024. Must match: new == new2, new == head
#        (newoff vs new is expected to differ at generated token 247 at cpu p1024: PR3-handoff.md 5.4). After each cell
#        validate-smoke.py checks every arm's rc=0 line and 256 tokens.
#   E.   performance (8 users, 256 tokens, CPU attention, 3 repetitions, arms interleaved): cells tp2 p1024, tp2 p8192,
#        tp4 p1024; arms base, new, newoff, head, headoff; summarizer arms and pairs set with WEDPERF_ARMS / WEDPERF_PAIRS
#   C.   the host test suite in the option-on tree (last: a late end costs it first)
#   end. chain.done = ok | failed-<step>; then the exit handler (chain-finish.sh): stop our workload, serving up when this
#        chain took it down (unless the lease is busy or the units are active), the Bill marker released, the machine line.
# No step starts after END_BY. START_NOT_BEFORE (ISO UTC, optional) holds the whole chain until that time.
# To stop the chain: SIGTERM to its process group (`kill -- -<pid>`; it is started with setsid, so its pid is the group id).
# Usage (on 3bda): COMMIT=<full sha> PR2_COMMIT=<full sha> [MAIN_COMMIT=<full sha>] [END_BY=2026-10-13T01:30:00Z]
#        [START_NOT_BEFORE=2026-10-12T13:00:00Z] bash chain.sh   (see launch.sh)
# Never edit this file or chain-finish.sh while the chain runs (bash re-reads a running script; NFS trap): copy to a new name.
# chain2.sh = chain.sh split in two runs (2026-10-12 01:1x UTC, jhan: the our-half part fits before the nightly):
#   STOP_AFTER_OUR_HALF=1  runs the our-half steps and the our-half verdict, writes chain.done=our-half-done, exits 0
#   WHOLE_MACHINE_ONLY=1   skips the our-half steps: waits for all.done = ok of the earlier run (and the three binaries),
#                          then the marker, serving down, D, E, C, the end verdict and the exit handler
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/pr3-20261012
B=$EXEC/i4525-20260922/build2.sh
S=$EXEC/sync4424-20261002
DUT=$EXEC/q4b-fpga-20260921/dut.sh
BILL_SHARE=$EXEC/bill-share.sh
export NAME=pr3-20261012
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the PR-3 head) is required}
PR2_COMMIT=${PR2_COMMIT:?PR2_COMMIT (full sha of the PR-2 head) is required}
MAIN_COMMIT=${MAIN_COMMIT:-72308ec90c80318403c4575dd9ce4a3bc9af5033}
END_BY=${END_BY:-2026-10-13T01:30:00Z}
START_NOT_BEFORE=${START_NOT_BEFORE:-}
PR2_RES=$EXEC/results/pr2-20261011
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
WT=/var/tmp/jhan/tron-pr3
WT_A3=/var/tmp/jhan/tron-pr3nd
WT_RM=/var/tmp/jhan/tron-pr3rm
WT_BASE=/var/tmp/jhan/tron-main1010
WT_HEAD=/var/tmp/jhan/tron-pr2
export RT_NEW=$WT/gen/runtron.pr3
export RT_BASE=$WT_BASE/gen/runtron.main1010
export RT_HEAD=$WT_HEAD/gen/runtron.pr2   # the "head" and "headoff" arms of D and E (campaign.sh maps both to RT_HEAD)
export ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_baseoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
CONF_VNNI='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_A3='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=OFF -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
CONF_BASE='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
TESTS_6='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'
TARGETS_6="runtron $TESTS_6"
TESTS_RM='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler'
# Catch2 test specs: a comma in a case name is escaped with a backslash, or the spec selects nothing (docs/command-line.md).
BLOCK_CASE='VNNI K block save equals the per-token row store\, bit for bit'
SAVEK_CASE="save_k stores every token's K row once\, grouped by page block\, alone or with helper threads"
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
passed_line() { grep -oE 'All tests passed \([0-9]+ assertions? in [0-9]+ test cases?\)' "$1"; }
cases_of() { grep -oE 'in [0-9]+ test cases?' "$1" | head -1; }
nix_build_target() {  # nix_build_target <target> <label> >> mutation<N>-build.txt
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'cmake --build gen --target '"$1"' -j32 2>&1 | grep -E "error|FAILED" | head -5; echo "'"$2"' build rc=${PIPESTATUS[0]}"' )
}
run_case() {  # run_case <binary> <spec> > out; rc returned
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 3600 "./gen/$1" --skip-benchmarks "$2" )
}
mutate() {  # mutate <file> <old> <new>: exact replacement, exactly one match; prints before/after counts
  python3 - "$WT/$1" "$2" "$3" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); old, new = sys.argv[2], sys.argv[3]
s = p.read_text(); n = s.count(old)
print(f"before={n}", end=" ")
if n != 1: print("FAIL: the old text does not occur exactly once"); sys.exit(1)
s = s.replace(old, new); p.write_text(s)
print(f"after-old={s.count(old)} after-new={s.count(new)}")
PY
}
OUR_RT_RE="^($(printf '%s' "$RT_BASE" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_HEAD" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_NEW" | sed 's/[.[\*^$()+?{}|]/\\&/g')) "
MARKER_TAKEN=0
SERVING_DOWN_BY_US=0
source "$D/chain-finish.sh"
trap 'finish term; exit 143' TERM
trap 'finish exit' EXIT
exec >>"$LOG" 2>&1
if [ "${WHOLE_MACHINE_ONLY:-0}" = 1 ]; then rm -f "$RES/chain.done"; else rm -f "$RES/all.done" "$RES/chain.done"; fi
echo "=== $NAME chain started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') on $(hostname) COMMIT=$COMMIT PR2_COMMIT=$PR2_COMMIT MAIN_COMMIT=$MAIN_COMMIT END_BY=$END_BY START_NOT_BEFORE=${START_NOT_BEFORE:-none} ==="
echo "$(ts) machine: $(machine)"
for c in "$COMMIT" "$PR2_COMMIT" "$MAIN_COMMIT"; do git -C "$REPO" cat-file -e "$c^{commit}" 2>/dev/null || { step_done start "$c not in the shared store: abort"; echo failed-start >"$RES/chain.done"; exit 1; }; done
if [ -n "$START_NOT_BEFORE" ]; then
  snb=$(date -u -d "$START_NOT_BEFORE" +%s) || { step_done start "bad START_NOT_BEFORE: abort"; echo failed-start >"$RES/chain.done"; exit 1; }
  while [ "$(date -u +%s)" -lt "$snb" ]; do left=$(( snb - $(date -u +%s) )); [ "$left" -gt 1800 ] && left=1800; echo "$(ts) holding until $START_NOT_BEFORE (next check in $((left / 60)) min)"; sleep "$left"; done
  echo "$(ts) START_NOT_BEFORE passed; machine: $(machine)"
fi

if [ "${WHOLE_MACHINE_ONLY:-0}" = 1 ]; then
  # ---- the our-half part ran earlier: wait for its verdict ----
  w=0
  while [ "$(cat "$RES/all.done" 2>/dev/null)" != ok ]; do
    v=$(cat "$RES/all.done" 2>/dev/null)
    [ -n "$v" ] && { step_done our-half "earlier run: $v (not ok): abort"; echo "failed-our-half: $v" >"$RES/chain.done"; exit 1; }
    past_end && { step_done our-half "all.done still missing at END_BY: abort"; echo stopped-end-by >"$RES/chain.done"; exit 1; }
    [ $w = 0 ] && echo "$(ts) waiting for the our-half verdict ($RES/all.done)"; w=1; sleep 60
  done
  for b in "$RT_NEW" "$RT_BASE" "$RT_HEAD"; do [ -x "$b" ] || { step_done our-half "$b missing: abort"; echo failed-binary >"$RES/chain.done"; exit 1; }; done
  step_done our-half "reused from the earlier run: $(cat "$RES/all.done"); runtron.pr3 $(sha256sum "$RT_NEW" | cut -c1-16) at $(git -C "$WT" rev-parse HEAD)"
else
# ---- A. option on, AMX dispatch on: build, 6 tests, kill-switch runs, plugin strings ----
wait_slot "step A"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT" SUFFIX=pr3 CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TARGETS_6" TESTS="$TESTS_6" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
step_done A "$(cat "$RES/build-pr3.done" 2>/dev/null) $(cut -c1-160 "$RES/tests-pr3.txt" 2>/dev/null | tr '\n' ';')"
[ "$(cat "$RES/build-pr3.done" 2>/dev/null)" = ok ] || { echo failed-A >"$RES/all.done"; echo failed-A >"$RES/chain.done"; exit 1; }
a_unavail=$(grep -c 'AMX unavailable' "$RES/tests-pr3-t_amx_numerics.out" 2>/dev/null); a_cases=$(cases_of "$RES/tests-pr3-t_amx_numerics.out")
step_done A-identity "AMX-on t_amx_numerics: 'AMX unavailable' lines=$a_unavail (expected 0), $a_cases (expected 5); $(summary_of "$RES/tests-pr3-t_amx_numerics.out")"
step_done A-layout "t_k_vnni_layout $(cases_of "$RES/tests-pr3-t_k_vnni_layout.out") (expected 5: the block-save case is new); $(passed_line "$RES/tests-pr3-t_k_vnni_layout.out"); t_llama_unit $(passed_line "$RES/tests-pr3-t_llama_unit.out")"
ks_fail=0
for t in t_llama_unit t_amx_numerics; do
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" TRON_AMX_DISABLE=1 timeout -k 60 3600 ./gen/$t --skip-benchmarks ) >"$RES/tests-pr3-$t-killswitch.out" 2>&1
  rc=$?; [ $rc -eq 0 ] || ks_fail=$((ks_fail + 1))
  echo "$t killswitch rc=$rc env=[TRON_AMX_DISABLE=1] $(summary_of "$RES/tests-pr3-$t-killswitch.out")" | tee -a "$RES/tests-pr3.txt"
done
step_done A-killswitch "failed runs: $ks_fail; t_amx_numerics 'AMX unavailable' lines=$(grep -c 'AMX unavailable' "$RES/tests-pr3-t_amx_numerics-killswitch.out") (expected 3: QK precision, VNNI identity, PV precision)"
for m in tp2 tp4; do
  n=$(strings "$RT_NEW" | grep -c "ingested-qwen-3-4b-instruct-2507-$m"); echo "$(ts) runtron.pr3 qwen3-4b $m plugin strings=$n"
  [ "${n:-0}" -gt 0 ] || { step_done A "runtron.pr3 lacks the qwen3-4b $m plugin: abort"; echo failed-plugin >"$RES/all.done"; echo failed-plugin >"$RES/chain.done"; exit 1; }
done
( cd "$WT" && bin/slice route ) >"$RES/slice-route.txt" 2>&1; echo "$(ts) bin/slice route: $(tr '\n' ' ' <"$RES/slice-route.txt" | cut -c1-300)"

# ---- plugin check: every generated plugin calls save_k on both sides, once per KV-writing operation ----
python3 "$D/plugin-calls.py" "$WT/gen/src/tron/h/tron/plugins" >"$RES/plugin-calls-pr3.txt" 2>&1
plugin_ok=$(tail -1 "$RES/plugin-calls-pr3.txt" | grep -q '^PASS' && echo ok || echo failed)
step_done plugin "$plugin_ok: $(tail -1 "$RES/plugin-calls-pr3.txt" | cut -c1-200); qwen_3_4b: $(grep -E '^qwen_3_4b' "$RES/plugin-calls-pr3.txt" | tr -s ' ' | cut -c1-120)"

# ---- M1. mutation check of the block store: block c's rows land in block c ^ 1's panels; the block-save case must fail ----
K1=h/tron/tensor/k_vnni.hpp
OLD1='bf16* panel = plane + (s * k_vnni::TOKEN_BLOCKS_4 + c) * k_vnni::PANEL_ELEMS_512;'
NEW1='bf16* panel = plane + (s * k_vnni::TOKEN_BLOCKS_4 + (c ^ 1)) * k_vnni::PANEL_ELEMS_512;'
( cd "$WT" && ./gen/t_k_vnni_layout --list-tests "$BLOCK_CASE" ) >"$RES/mutation1-list.txt" 2>&1
l1=$(grep -oE '^[0-9]+ matching test cases?' "$RES/mutation1-list.txt" | grep -oE '^[0-9]+')
m1_ok=failed
mutate $K1 "$OLD1" "$NEW1" >"$RES/mutation1-applied.txt" 2>&1
if [ "$(cat "$RES/mutation1-applied.txt")" = "before=1 after-old=0 after-new=1" ] && [ "${l1:-0}" = 1 ]; then
  nix_build_target t_k_vnni_layout mutant >"$RES/mutation1-build.txt" 2>&1
  run_case t_k_vnni_layout "$BLOCK_CASE" >"$RES/mutation1-run.out" 2>&1; mrc=$?
  echo "mutant t_k_vnni_layout rc=$mrc $(grep -E 'test cases:|assertions:|FAILED:|No tests ran|All tests passed' "$RES/mutation1-run.out" | tr '\n' ' ' | cut -c1-300)" | tee "$RES/mutation1-result.txt"
  ( cd "$WT" && git checkout -- $K1 && git status --porcelain -- $K1 | wc -l ) >"$RES/mutation1-reverted.txt" 2>&1
  nix_build_target t_k_vnni_layout restore >>"$RES/mutation1-build.txt" 2>&1
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 3600 ./gen/t_k_vnni_layout --skip-benchmarks ) >"$RES/tests-pr3-t_k_vnni_layout-restored.out" 2>&1; rrc=$?
  echo "restored t_k_vnni_layout rc=$rrc $(summary_of "$RES/tests-pr3-t_k_vnni_layout-restored.out")" | tee -a "$RES/mutation1-result.txt"
  reverted=$([ "$(cat "$RES/mutation1-reverted.txt")" = 0 ] && echo clean || echo DIRTY)
  same=$([ "$(passed_line "$RES/tests-pr3-t_k_vnni_layout.out")" = "$(passed_line "$RES/tests-pr3-t_k_vnni_layout-restored.out")" ] && echo same-counts || echo COUNTS-DIFFER)
  if [ $mrc -ne 0 ] && [ $rrc -eq 0 ] && [ "$reverted" = clean ] && [ "$same" = same-counts ] && grep -q 'FAILED:' "$RES/mutation1-run.out" && ! grep -q 'No tests ran' "$RES/mutation1-run.out" && grep -E '^test cases:' "$RES/mutation1-run.out" | grep -q '1 failed'; then m1_ok=ok; fi
  step_done M1 "$m1_ok; listed=$l1 case(s); mutant rc=$mrc: $(grep -E 'test cases:|assertions:' "$RES/mutation1-run.out" | tr '\n' ';') $(grep -m1 'FAILED:' "$RES/mutation1-run.out" | cut -c1-80); k_vnni.hpp reverted=$reverted; restored rc=$rrc $same"
else
  ( cd "$WT" && git checkout -- $K1 ); step_done M1 "mutation not applied ($(cat "$RES/mutation1-applied.txt"); listed=$l1): failed"
fi

# ---- M2. mutation check of the work-unit cut: a block change inside a page no longer cuts; the save_k case must fail ----
K2=h/tron/models/model.hpp
OLD2='pg != run_page || block != run_block'
NEW2='pg != run_page || block == run_block'
( cd "$WT" && ./gen/t_llama_unit --list-tests "$SAVEK_CASE" ) >"$RES/mutation2-list.txt" 2>&1
l2=$(grep -oE '^[0-9]+ matching test cases?' "$RES/mutation2-list.txt" | grep -oE '^[0-9]+')
m2_ok=failed
mutate $K2 "$OLD2" "$NEW2" >"$RES/mutation2-applied.txt" 2>&1
if [ "$(cat "$RES/mutation2-applied.txt")" = "before=1 after-old=0 after-new=1" ] && [ "${l2:-0}" = 1 ]; then
  t0=$(date +%s); nix_build_target t_llama_unit mutant >"$RES/mutation2-build.txt" 2>&1; echo "mutant build $(( $(date +%s) - t0 )) s" >>"$RES/mutation2-build.txt"
  run_case t_llama_unit "$SAVEK_CASE" >"$RES/mutation2-run.out" 2>&1; mrc=$?
  echo "mutant t_llama_unit rc=$mrc $(grep -E 'test cases:|assertions:|FAILED:|No tests ran|All tests passed' "$RES/mutation2-run.out" | tr '\n' ' ' | cut -c1-300) captured: $(grep -oE '^ *(u|begin|end|t) := [0-9]+' "$RES/mutation2-run.out" | head -4 | tr -s ' ' | tr '\n' ' ')" | tee "$RES/mutation2-result.txt"
  ( cd "$WT" && git checkout -- $K2 && git status --porcelain -- $K2 | wc -l ) >"$RES/mutation2-reverted.txt" 2>&1
  t0=$(date +%s); nix_build_target t_llama_unit restore >>"$RES/mutation2-build.txt" 2>&1; echo "restore build $(( $(date +%s) - t0 )) s" >>"$RES/mutation2-build.txt"
  ( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" timeout -k 60 3600 ./gen/t_llama_unit --skip-benchmarks ) >"$RES/tests-pr3-t_llama_unit-restored.out" 2>&1; rrc=$?
  echo "restored t_llama_unit rc=$rrc $(summary_of "$RES/tests-pr3-t_llama_unit-restored.out")" | tee -a "$RES/mutation2-result.txt"
  reverted=$([ "$(cat "$RES/mutation2-reverted.txt")" = 0 ] && echo clean || echo DIRTY)
  same=$([ "$(passed_line "$RES/tests-pr3-t_llama_unit.out")" = "$(passed_line "$RES/tests-pr3-t_llama_unit-restored.out")" ] && echo same-counts || echo COUNTS-DIFFER)
  if [ $mrc -ne 0 ] && [ $rrc -eq 0 ] && [ "$reverted" = clean ] && [ "$same" = same-counts ] && grep -q 'FAILED:' "$RES/mutation2-run.out" && ! grep -q 'No tests ran' "$RES/mutation2-run.out" && grep -E '^test cases:' "$RES/mutation2-run.out" | grep -q '1 failed'; then m2_ok=ok; fi
  step_done M2 "$m2_ok; listed=$l2 case(s); mutant rc=$mrc: $(grep -E 'test cases:|assertions:' "$RES/mutation2-run.out" | tr '\n' ';') $(grep -m1 'FAILED:' "$RES/mutation2-run.out" | cut -c1-80) captured: $(grep -oE '^ *(u|begin|end|t) := [0-9]+' "$RES/mutation2-run.out" | head -4 | tr -s ' ' | tr '\n' ' '); model.hpp reverted=$reverted; restored rc=$rrc $same"
else
  ( cd "$WT" && git checkout -- $K2 ); step_done M2 "mutation not applied ($(cat "$RES/mutation2-applied.txt"); listed=$l2): failed"
fi

# ---- A2. the Haskell suite (bin/ingest-cabal test) ----
wait_slot "step A2"
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'bin/ingest-cabal test 2>&1 | tail -40; echo "ingest-cabal-test rc=${PIPESTATUS[0]}"' ) >"$RES/ingest-test-pr3.txt" 2>&1
a2_secs=$(( $(date +%s) - t0 ))
a2_rc=$(grep -oE 'ingest-cabal-test rc=[0-9]+' "$RES/ingest-test-pr3.txt" | tail -1)
a2_ok=$([ "$a2_rc" = "ingest-cabal-test rc=0" ] && grep -qE '^\s*Failed:\s+0\s*$' "$RES/ingest-test-pr3.txt" && grep -q 'Test suite ingest-tests: PASS' "$RES/ingest-test-pr3.txt" && echo ok || echo failed)
step_done A2 "$a2_ok ($a2_secs s): $a2_rc $(grep -E 'Examples:|Passed:|Failed:|Test suite ingest-tests' "$RES/ingest-test-pr3.txt" | tr -s ' ' | tr '\n' ';')"

# ---- A3. option on, AMX dispatch off (D2) ----
wait_slot "step A3"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT_A3" SUFFIX=pr3nd CONFIGURE_ARGS="$CONF_A3" TARGETS="$TARGETS_6" TESTS="$TESTS_6" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
step_done A3 "$(cat "$RES/build-pr3nd.done" 2>/dev/null) $(cut -c1-160 "$RES/tests-pr3nd.txt" 2>/dev/null | tr '\n' ';') (t_amx_numerics and t_amx_dispatch_dtype are placeholders without dispatch); t_k_vnni_layout $(cases_of "$RES/tests-pr3nd-t_k_vnni_layout.out")"

# ---- B. option off (row-major K) ----
wait_slot "step B"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT_RM" SUFFIX=pr3rm CONFIGURE_ARGS="$CONF_RM" TARGETS="$TESTS_RM" TESTS="$TESTS_RM" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
b_unavail=$(grep -c 'AMX unavailable' "$RES/tests-pr3rm-t_amx_numerics.out" 2>/dev/null)
step_done B "$(cat "$RES/build-pr3rm.done" 2>/dev/null) $(cut -c1-160 "$RES/tests-pr3rm.txt" 2>/dev/null | tr '\n' ';') row-major t_amx_numerics 'AMX unavailable' lines=$b_unavail (expected 0); t_k_vnni_layout $(cases_of "$RES/tests-pr3rm-t_k_vnni_layout.out")"

# ---- F. format checks (nix shell of the option-on worktree), against the PR-2 head; lint-notes recorded only ----
( cd "$WT" && "$NIX" develop --accept-flake-config --command bash -c '
  echo "clang-format: $(clang-format --version 2>&1 | head -1)"
  files=$(git diff --name-only '"$PR2_COMMIT"' HEAD -- "*.hpp" "*.cpp"); echo "files: $(echo $files | wc -w)"
  clang-format --dry-run --Werror $files; echo "clang-format rc=$?"
  echo "fourmolu: $(fourmolu --version 2>&1 | grep -v capabilities | head -1)"
  fourmolu +RTS -N8 -RTS --mode check -o -XImportQualifiedPost ingest/src/TronCpp.hs ingest/test/LoopyTronSpec.hs 2>&1 | grep -v "256 capabilities"; echo "fourmolu rc=${PIPESTATUS[0]}"
  git diff --check '"$PR2_COMMIT"' HEAD -- ":!lib/**"; echo "diff-check rc=$?"
  echo "cassert-in-diff $(git diff '"$PR2_COMMIT"' HEAD | grep -c "^+.*<cassert>")"' ) >"$RES/format-pr3.txt" 2>&1
( cd "$WT" && timeout 600 "$NIX" develop .#lint --accept-flake-config -c make lint-notes 2>&1 | tail -5; rc=${PIPESTATUS[0]}; if [ $rc = 124 ]; then echo "lint-notes: not run (the lint shell was not available within 600 s)"; else echo "lint-notes rc=$rc"; fi ) >"$RES/lint-notes-pr3.txt" 2>&1
step_done F "$(grep -E ' rc=|cassert|files:' "$RES/format-pr3.txt" | tr '\n' ' ') $(tail -1 "$RES/lint-notes-pr3.txt")"

# ---- A0. base build (main, runtron only) ----
if [ ! -x "$RT_BASE" ]; then
  wait_slot "step A0"
  env RES="$RES" SRC="$REPO" COMMIT="$MAIN_COMMIT" WT="$WT_BASE" SUFFIX=main1010 CONFIGURE_ARGS="$CONF_BASE" TARGETS=runtron TESTS= JOBS=64 bash "$B"
  step_done A0 "$(cat "$RES/build-main1010.done" 2>/dev/null)"
else
  step_done A0 "base binary present ($(sha256sum "$RT_BASE" | cut -c1-16), $(git -C "$WT_BASE" rev-parse --short=10 HEAD)), build skipped"
fi

# ---- head. the PR-2 binary: reuse when the worktree is at PR2_COMMIT and the sha256 matches the pr2-20261011 record, else rebuild ----
rec=$(grep -E ' gen/runtron\.pr2$' "$PR2_RES/build-pr2.txt" 2>/dev/null | awk '{print $1}')
cur=$([ -x "$RT_HEAD" ] && sha256sum "$RT_HEAD" | awk '{print $1}')
if [ -x "$RT_HEAD" ] && [ "$(git -C "$WT_HEAD" rev-parse HEAD 2>/dev/null)" = "$PR2_COMMIT" ] && [ -n "$rec" ] && [ "$cur" = "$rec" ]; then
  step_done head "runtron.pr2 reused: worktree at $PR2_COMMIT, sha256 ${cur:0:16} = pr2-20261011 record"
else
  step_done head "runtron.pr2 rebuilt: worktree HEAD=$(git -C "$WT_HEAD" rev-parse HEAD 2>/dev/null) sha256=${cur:0:16} record=${rec:0:16}"
  wait_slot "step head"
  env RES="$RES" SRC="$REPO" COMMIT="$PR2_COMMIT" WT="$WT_HEAD" SUFFIX=pr2 CONFIGURE_ARGS="$CONF_VNNI" TARGETS=runtron TESTS= JOBS=64 bash "$B"
  step_done head-build "$(cat "$RES/build-pr2.done" 2>/dev/null)"
fi

# ---- our-half verdict ----
a=$(cat "$RES/build-pr3.done"); a3=$(cat "$RES/build-pr3nd.done" 2>/dev/null); b=$(cat "$RES/build-pr3rm.done" 2>/dev/null)
a0=$([ -x "$RT_BASE" ] && echo ok || echo missing); hd=$([ -x "$RT_HEAD" ] && echo ok || echo missing)
f=$(grep -cE '^(clang-format|fourmolu|diff-check) rc=0$' "$RES/format-pr3.txt"); cas=$(grep -oE '^cassert-in-diff [0-9]+' "$RES/format-pr3.txt" | awk '{print $2}')
if [ "$a" = ok ] && [ "$a3" = ok ] && [ "$b" = ok ] && [ "$a0" = ok ] && [ "$hd" = ok ] && [ "$ks_fail" = 0 ] && [ "${a_unavail:-1}" = 0 ] && [ "${b_unavail:-1}" = 0 ] && [ "$plugin_ok" = ok ] && [ "$m1_ok" = ok ] && [ "$m2_ok" = ok ] && [ "$a2_ok" = ok ] && [ "$f" = 3 ] && [ "${cas:-1}" = 0 ]; then echo ok >"$RES/all.done"
else echo "failed vnni=$a nodispatch=$a3 rm=$b base=$a0 head=$hd killswitch-failed=$ks_fail amx-unavailable-A=$a_unavail amx-unavailable-B=$b_unavail plugin=$plugin_ok mutation1=$m1_ok mutation2=$m2_ok haskell=$a2_ok format-ok=$f/3 cassert=${cas:-?}" >"$RES/all.done"; fi
step_done our-half "$(cat "$RES/all.done")"
[ "$(cat "$RES/all.done")" = ok ] || { echo "failed-our-half: $(cat "$RES/all.done")" >"$RES/chain.done"; exit 1; }
if [ "${STOP_AFTER_OUR_HALF:-0}" = 1 ]; then echo "our-half-done $(cat "$RES/all.done")" >"$RES/chain.done"; step_done end "$(cat "$RES/chain.done") (STOP_AFTER_OUR_HALF: the whole-machine part runs in a later run)"; exit 0; fi
fi

# ---- whole-machine part: the Bill marker, serving down ----
past_end && { step_done 0 "past END_BY before the whole-machine part"; echo stopped-end-by >"$RES/chain.done"; exit 1; }
wait_slot "step 0"
tout=$(bash "$BILL_SHARE" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) step_done 0 "Bill marker not taken (rc $trc): the whole-machine steps wait for jhan"; echo stopped-marker >"$RES/chain.done"; exit 1;; esac
if rinzler_active; then
  SERVING_DOWN_BY_US=1
  IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); the steps below retry through the guard"
fi
step_done 1 "serving: $(machine)"

# ---- D. token identity (5 arms) + the validator ----
export MUST_MATCH="new:new2 new:head"
export DEADLINE_HHMM=0130
for spec in "cpu 1024 base new new2 newoff head" "cpu 8192 base new new2 newoff head" "fpga 1024 base new new2 newoff head"; do
  past_end && { step_done D "skipped $spec: past END_BY"; continue; }
  set -- $spec; attn=$1; prompt=$2; shift 2
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$S/smoke.sh"
  v=$(python3 "$D/validate-smoke.py" "$RES/smoke/$attn-p$prompt" 256 "$@" 2>&1 | tail -1); echo "$v" >"$RES/smoke/$attn-p$prompt/validate.txt"
  step_done D "$attn p$prompt: smoke.done=$(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null) $v; $(grep -E ' vs .*(identical|first difference)' "$RES/smoke/$attn-p$prompt/smoke.txt" | tail -8 | cut -c1-110 | tr '\n' ';')"
done

# ---- E. performance (5 arms, 3 cells: tp2 p1024, tp2 p8192, tp4 p1024) ----
cells() { local s tp p out=""; for s in "$@"; do tp=${s%%:*}; p=${s##*:}; out+="q3-4b-tp$tp-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp$tp|$tp|8|$p"$'\n'; done; printf '%s' "${out%$'\n'}"; }
if past_end; then step_done E "skipped: past END_BY"; else
  NAME=pr3-E-cpu CELLS_ALL="$(cells 2:1024 2:8192 4:1024)" ARMS="base new newoff head headoff" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 \
    WEDPERF_ARMS="base new newoff head headoff" WEDPERF_PAIRS="new:base new:head newoff:new newoff:headoff head:base" bash "$S/campaign.sh"
  step_done E "$(cat "$EXEC/logs/pr3-E-cpu.done" 2>/dev/null); head line: $(grep -m1 '^# arms:' "$EXEC/results/pr3-E-cpu/rt-results.txt" 2>/dev/null | cut -c1-200)"
fi

# ---- C. host suite (serving down; last) ----
if past_end; then step_done C "skipped: past END_BY"; else
  wait_slot "step C"
  env RES="$RES" WT="$WT" SUFFIX=pr3 bash "$EXEC/i4525-20260922/host-suite.sh"
  step_done C "$(cat "$RES/host-suite-pr3.done" 2>/dev/null) $(grep -E '^(build-test-host|test-host) rc=|passed|skipped|failed' "$RES/host-suite-pr3.txt" 2>/dev/null | tr '\n' ' ' | cut -c1-200)"
fi

# ---- end. the verdict; serving up and the marker release follow in the exit handler ----
h=$(cat "$RES/host-suite-pr3.done" 2>/dev/null)
sm() { [ "$(cat "$RES/smoke/$1/smoke.done" 2>/dev/null)" = ok ] && [ "$(cat "$RES/smoke/$1/validate.txt" 2>/dev/null)" = "VALIDATE ok" ] && echo ok || echo "$(cat "$RES/smoke/$1/smoke.done" 2>/dev/null)/$(cat "$RES/smoke/$1/validate.txt" 2>/dev/null | cut -c1-40)"; }
s1=$(sm cpu-p1024); s2=$(sm cpu-p8192); s3=$(sm fpga-p1024)
e=$(cat "$EXEC/logs/pr3-E-cpu.done" 2>/dev/null)
if [ "$h" = ok ] && [ "$s1" = ok ] && [ "$s2" = ok ] && [ "$s3" = ok ]; then echo "ok (E: $e)" >"$RES/chain.done"; else echo "failed host=$h smoke=$s1/$s2/$s3 E=$e" >"$RES/chain.done"; fi
step_done end "$(cat "$RES/chain.done")"
echo "=== $NAME chain finished $(ts): $(cat "$RES/chain.done") (the exit handler restores serving and releases the marker next) ==="
