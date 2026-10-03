#!/usr/bin/env bash
# i4500c-20260930 chain (runs ON delphi-3bda, detached): after the i4500b chain (step W waits for its end marker), the
# perf block of perf.sh (step P): perf record of the canonical runtron (main c7844ca2ce) and of the policy runtron
# (452b2052c9) in decode at tp2 with 2 users, to explain the main thread's Save K gap (105 vs 58 us per pass in the
# 2026-09-30 traces). No build: both binaries exist. Log: exec/logs/i4500c-20260930-chain.log.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4500c-20260930
RES=$EXEC/results/i4500c-20260930
LOG=$EXEC/logs/i4500c-20260930-chain.log
STATUS=$EXEC/logs/i4500c-20260930-chain.status
export NOT_BEFORE=${NOT_BEFORE:-2026-09-30T13:00:00Z}
COMMIT_FIX=${COMMIT_FIX:-0bb74c2ab0}
COMMIT_DEB=${COMMIT_DEB:-f6aa724144}
COMMIT_REF=${COMMIT_REF:-f34b0fe2ec}
export REPS=${REPS:-3}
STEPS=${STEPS:-"W P"}
WAIT_FOR=${WAIT_FOR:-/home/jhan/workspace/intel-AMX/exec/results/i4500b-20260930/chain.done}
CONF_VNNI='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
# t_gof_dma and t_gof_staging_leaks are real-FPGA tests (pos, not pos_fake); they are built but not run here: the
# production engine may hold our cards during the build steps.
TARGETS_ALL='runtron t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_gof_dma t_gof_staging_leaks t_phase1_integration'
TESTS_ALL='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_phase1_integration'
TESTS_RM='t_k_vnni_layout t_amx_dispatch_dtype t_llama_unit'
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
source "$C/lib.sh"
exec >>"$LOG" 2>&1
date -u -d "$NOT_BEFORE" +%s >/dev/null 2>&1 || { echo "$(ts) bad NOT_BEFORE '$NOT_BEFORE' (use 2026-09-30T13:00:00Z); not starting"; exit 1; }
pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/i4500c-20260930/chain[.]sh$' | grep -vx "$$" | grep -q . && { echo "$(ts) another chain.sh runs; exit"; exit 1; }
rm -f "$RES/chain.done"
echo "=== i4500c chain started $(ts) pid $$ on $(hostname) NOT_BEFORE=$NOT_BEFORE STEPS=[$STEPS] REPS=$REPS COMMIT_FIX=$COMMIT_FIX COMMIT_DEB=$COMMIT_DEB COMMIT_REF=$COMMIT_REF ==="
# Builds need only the lease and an idle machine of other people; they leave the production engines alone.
wait_build_slot() { local waited=0; not_before_wait || return 1; while preci_hold || ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $waited = 0 ] && { status "waiting before $1: pre-CI hold, CI lease busy or another person active"; waited=1; }; sleep 120; done; echo "$(ts) $1 may start: $(machine_line)"; }
# Run a build step in the background and stop it (its process group) if the CI lease turns busy meanwhile.
run_build() { setsid bash -c "$1" & local bp=$!; while kill -0 $bp 2>/dev/null; do if ci_lease_busy; then echo "$(ts) CI lease busy during $2: stopping the build"; kill -TERM -- -$bp 2>/dev/null; sleep 5; kill -KILL -- -$bp 2>/dev/null; fi; sleep 60; done; wait $bp; }
trap 'serving_restore' EXIT
step_done() { [ -e "$RES/$1" ] && grep -q -E "^(ok|tests-failed-[0-9]+|done)$" "$RES/$1"; }
fail_chain() { status "chain stopped: $*"; echo "stopped: $*" >"$RES/chain.done"; exit 1; }
for step in $STEPS; do
  case $step in
    W)
      waited=0; until [ -e "$WAIT_FOR" ]; do [ $waited = 0 ] && { status "waiting: $WAIT_FOR (the i4500b chain)"; waited=1; }; sleep 120; done
      echo "$(ts) step W: $WAIT_FOR present ($(cat "$WAIT_FOR"))" ;;
    P)
      if [ "$(cat "$RES/perf/perf.done" 2>/dev/null)" = done ]; then echo "$(ts) step P already done"; continue; fi
      status "step P: perf"; bash "$C/perf.sh"; echo "$(ts) step P result: $(cat "$RES/perf/perf.done" 2>/dev/null)" ;;
  esac
done
serving_restore
echo "ok" >"$RES/chain.done"; status "chain finished"
echo "=== i4500c chain finished $(ts): P=$(cat "$RES/perf/perf.done" 2>/dev/null) ==="
