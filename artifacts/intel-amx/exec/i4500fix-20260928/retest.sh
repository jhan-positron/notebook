#!/usr/bin/env bash
# i4500fix-20260928 retest (runs ON delphi-3bda, our half): rebuild and rerun the two unit tests that failed in the chain
# (t_k_vnni_layout, t_llama_unit) at COMMIT_FIX in both existing worktrees (incremental builds). Waits for the lease and
# other people like chain.sh's build steps. Markers: results/build-retest.done, build-retestrm.done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4500fix-20260928
RES=$EXEC/results/i4500fix-20260928
LOG=$EXEC/logs/i4500fix-20260928-retest.log
STATUS=$EXEC/logs/i4500fix-20260928-retest.status
COMMIT_FIX=${COMMIT_FIX:?}
CONF_VNNI='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
TESTS='t_k_vnni_layout t_llama_unit'
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
source "$EXEC/lib-guard.sh"
source "$C/lib.sh"
exec >>"$LOG" 2>&1
echo "=== retest started $(ts) pid $$ COMMIT_FIX=$COMMIT_FIX ==="
waited=0; while preci_hold || ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $waited = 0 ] && { status "waiting: pre-CI hold, CI lease busy or another person active"; waited=1; }; sleep 120; done
status "retest: VNNI build"
env RES="$RES" SRC=/home/jhan/workspace/tron COMMIT="$COMMIT_FIX" WT=/var/tmp/jhan/tron-i4500 SUFFIX=retest CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TESTS" TESTS="$TESTS" bash "$EXEC/i4525-20260922/build2.sh"
echo "$(ts) VNNI build result: $(cat "$RES/build-retest.done" 2>/dev/null)"
status "retest: row-major build"
env RES="$RES" SRC=/home/jhan/workspace/tron COMMIT="$COMMIT_FIX" WT=/var/tmp/jhan/tron-i4500rm SUFFIX=retestrm CONFIGURE_ARGS="$CONF_RM" TARGETS="$TESTS" TESTS="$TESTS" bash "$EXEC/i4525-20260922/build2.sh"
echo "$(ts) row-major build result: $(cat "$RES/build-retestrm.done" 2>/dev/null)"
status "retest finished: vnni=$(cat "$RES/build-retest.done" 2>/dev/null) rm=$(cat "$RES/build-retestrm.done" 2>/dev/null)"
echo "=== retest finished $(ts) ==="
