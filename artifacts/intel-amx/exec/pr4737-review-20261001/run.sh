#!/usr/bin/env bash
# pr4737-review-20261001 (runs ON delphi-3bda, detached): build the PR #4737 review-response head COMMIT and run the
# unit tests in both builds, on our half of the machine (socket 1), with the fake device. Step A = the VNNI build in
# /var/tmp/jhan/tron-i4500b (AMX + VNNI K + ingest models, runtron + 7 tests, 5 run); step E = the row-major build
# (TRON_K_VNNI=OFF) in /var/tmp/jhan/tron-i4500rm (3 tests). Each build waits for the CI lease and for other people's
# activity to end (bill excluded by the half-split agreement). Production engines are left alone.
# Markers: RES/build-r1.done, RES/build-r1rm.done, RES/chain.done. Log: exec/logs/pr4737-review-20261001.log.
# Usage: COMMIT=<sha> bash run.sh
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/pr4737-review-20261001
LOG=$EXEC/logs/pr4737-review-20261001.log
COMMIT=${COMMIT:?}
CONF_VNNI='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
TARGETS_ALL='runtron t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_gof_dma t_gof_staging_leaks t_phase1_integration'
TESTS_ALL='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_phase1_integration'
TESTS_RM='t_k_vnni_layout t_amx_dispatch_dtype t_llama_unit'
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
rm -f "$RES/chain.done"
echo "=== pr4737 review build started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT ==="
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy or another person active"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
wait_slot "step A"
env RES="$RES" SRC=/home/jhan/workspace/tron COMMIT="$COMMIT" WT=/var/tmp/jhan/tron-i4500b SUFFIX=r1 CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TARGETS_ALL" TESTS="$TESTS_ALL" bash "$EXEC/i4525-20260922/build2.sh"
echo "$(ts) step A: $(cat "$RES/build-r1.done" 2>/dev/null)"
wait_slot "step E"
env RES="$RES" SRC=/home/jhan/workspace/tron COMMIT="$COMMIT" WT=/var/tmp/jhan/tron-i4500rm SUFFIX=r1rm CONFIGURE_ARGS="$CONF_RM" TARGETS="$TESTS_RM" TESTS="$TESTS_RM" bash "$EXEC/i4525-20260922/build2.sh"
echo "$(ts) step E: $(cat "$RES/build-r1rm.done" 2>/dev/null)"
echo done >"$RES/chain.done"
echo "=== pr4737 review build finished $(ts) ==="
