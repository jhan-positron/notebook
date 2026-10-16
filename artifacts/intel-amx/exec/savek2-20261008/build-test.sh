#!/usr/bin/env bash
# savek2-20261008 (runs ON delphi-3bda, detached): build and unit-test the merge of PR 4774 (one save_k for main and
# the main helpers) onto the jhan-amx-vnniK head 6b939d25d2 (main be0d5565b3 + typed K port). Our half of the machine
# only (socket 1 cpus, SYSTEM_CONFIG="--instance 1,2" for the fake-device tests), next to production serving. No runtron run.
#   A.  VNNI build (preset native: explicit AVX-512 flags; AMX dispatch ON, TRON_K_VNNI ON, ingest models ON) in
#       /var/tmp/jhan/tron-savek2: runtron + the unit tests; then t_amx_numerics with TRON_AMX_DISABLE=1 (kill switch);
#       then the generated-plugin grep (main-side and helper-side save_k calls, no save_k_helper).
#   A2. the ingest Haskell test suite (bin/ingest-cabal test) in the same worktree.
#   B.  row-major build (TRON_K_VNNI OFF, ingest OFF) in /var/tmp/jhan/tron-savek2rm: the layout-independent tests.
#   F.  format checks inside the nix shell: clang-format on the two C++ files, fourmolu on the two Haskell files,
#       git diff --check of the merge against its first parent.
# Every step waits for the CI lease (600 s grace) and for other people's activity to end (bill excluded: half split).
# Usage (on 3bda): COMMIT=<full sha> bash build-test.sh      (see launch.sh)
# Never edit this file while it runs (bash re-reads a running script; NFS stale-handle trap).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
B=$EXEC/i4525-20260922/build2.sh
NAME=savek2-20261008
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-build-test.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the merge) is required}
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
WT=/var/tmp/jhan/tron-savek2
WT_RM=/var/tmp/jhan/tron-savek2rm
CONF_VNNI='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
TARGETS_VNNI='runtron t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'
TESTS_VNNI='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'
TESTS_RM='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler'
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy or another person active"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
exec >>"$LOG" 2>&1
rm -f "$RES/all.done"
echo "=== $NAME started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT ==="
echo "$(ts) machine: lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"

# ---- A. VNNI build + unit tests ----
wait_slot "step A"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT" SUFFIX=savek2 CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TARGETS_VNNI" TESTS="$TESTS_VNNI" JOBS=64 bash "$B"
step_done A "$(cat "$RES/build-savek2.done" 2>/dev/null) $(cat "$RES/tests-savek2.txt" 2>/dev/null | cut -c1-160 | tr '\n' ';')"
[ "$(cat "$RES/build-savek2.done" 2>/dev/null)" = ok ] || { echo failed-A >"$RES/all.done"; exit 1; }
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" TRON_AMX_DISABLE=1 timeout -k 60 1800 ./gen/t_amx_numerics ) >"$RES/tests-savek2-t_amx_numerics-killswitch.out" 2>&1
echo "t_amx_numerics killswitch rc=$? $(grep -E 'test cases:|assertions|All tests passed|FAILED|AMX unavailable' "$RES/tests-savek2-t_amx_numerics-killswitch.out" | tr '\n' ' ' | cut -c1-400)" | tee -a "$RES/tests-savek2.txt"
n=$(strings "$WT/gen/runtron.savek2" | grep -c ingested-qwen-3-4b-instruct-2507); echo "$(ts) runtron.savek2 qwen3-4b plugin strings=$n"
# the generated plugin text: both save_k call forms must be present, save_k_helper absent
{
  echo "generated plugin grep ($(ts)):"
  for f in $(grep -rlE 'save_k<' "$WT/gen" --include=*.cpp --include=*.hpp 2>/dev/null | sort); do
    echo "  $(basename "$f"): main-side=$(grep -cE 'save_k<[^;]*k, *0, *n_workers' "$f") helper-side=$(grep -cE 'save_k<[^;]*k, *worker_ix, *n_workers' "$f") save_k_helper=$(grep -c 'save_k_helper' "$f")"
  done
  echo "  files with save_k_helper: $(grep -rl 'save_k_helper' "$WT/gen" --include=*.cpp --include=*.hpp 2>/dev/null | wc -l)"
} | tee -a "$RES/tests-savek2.txt"

# ---- A2. ingest Haskell tests ----
wait_slot "step A2"
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'bin/ingest-cabal test 2>&1 | tail -40; echo "ingest-cabal-test rc=${PIPESTATUS[0]}"' ) >"$RES/ingest-test-savek2.txt" 2>&1
echo "$(ts) ingest tests done in $(( $(date +%s) - t0 )) s: $(grep -E 'rc=|examples,|failures' "$RES/ingest-test-savek2.txt" | tr '\n' ' ' | cut -c1-300)" | tee -a "$RES/tests-savek2.txt"
step_done A2 "$(grep -E 'ingest-cabal-test rc=' "$RES/ingest-test-savek2.txt") $(grep -E 'examples,' "$RES/ingest-test-savek2.txt" | tail -1)"

# ---- F. format checks (in the VNNI worktree, nix shell) ----
( cd "$WT" && "$NIX" develop --accept-flake-config --command bash -c '
  echo "clang-format: $(clang-format --version 2>&1 | head -1)"
  clang-format --dry-run --Werror h/tron/models/model.hpp t/t_llama_unit.cpp; echo "clang-format rc=$?"
  echo "fourmolu: $(fourmolu --version 2>&1 | head -1)"
  fourmolu --mode check ingest/src/TronCpp.hs ingest/test/LoopyTronSpec.hs; echo "fourmolu rc=$?"
  git diff --check HEAD^1 HEAD; echo "diff-check rc=$?"' ) >"$RES/format-savek2.txt" 2>&1
step_done F "$(grep -E ' rc=' "$RES/format-savek2.txt" | tr '\n' ' ')"

# ---- B. row-major build + tests ----
wait_slot "step B"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT_RM" SUFFIX=savek2rm CONFIGURE_ARGS="$CONF_RM" TARGETS="$TESTS_RM" TESTS="$TESTS_RM" JOBS=64 bash "$B"
step_done B "$(cat "$RES/build-savek2rm.done" 2>/dev/null) $(cat "$RES/tests-savek2rm.txt" 2>/dev/null | cut -c1-160 | tr '\n' ';')"

a=$(cat "$RES/build-savek2.done"); b=$(cat "$RES/build-savek2rm.done" 2>/dev/null); i=$(grep -o 'ingest-cabal-test rc=[0-9]*' "$RES/ingest-test-savek2.txt"); f=$(grep -cE ' rc=0$' "$RES/format-savek2.txt")
if [ "$a" = ok ] && [ "$b" = ok ] && [ "$i" = "ingest-cabal-test rc=0" ] && [ "$f" = 3 ]; then echo ok >"$RES/all.done"; else echo "failed vnni=$a rm=$b $i format-ok=$f/3" >"$RES/all.done"; fi
echo "=== $NAME finished $(ts): $(cat "$RES/all.done") ==="
