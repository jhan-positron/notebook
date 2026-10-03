#!/usr/bin/env bash
# i4500b-20260930 chain (runs ON delphi-3bda, detached): the issue #4500 policy commit 452b2052c9 ("blocks completed
# under hardware attention stay row-major", on top of the fix f34b0fe2ec) from source to numbers, on our half, after
# the nightly CI of 2026-09-30 (NOT_BEFORE default 2026-09-30T13:00:00Z; the lease clears ~13:20 UTC). Every step
# waits for the CI lease (600 s grace) and for any other person's activity to end (lib-guard other_user_active; bill
# excluded). Fork of exec/i4500b-20260930/chain.sh. Steps, each with a marker under RES (resume = relaunch; done
# steps are skipped):
#   A0 build-fixrt : build2.sh -> /var/tmp/jhan/tron-i4500 (the existing fix worktree) at f34b0fe2ec, runtron only
#                    (incremental), copied to gen/runtron.fix: the pre-policy reference of the smoke and the traces.
#   A  build-fixS1 : build2.sh -> /var/tmp/jhan/tron-i4500b at COMMIT_FIX (452b2052c9), cross-avx512, AMX + VNNI K +
#                    ingest models, targets runtron + 7 tests, tests run with the fake device. A failed BUILD stops the
#                    chain; failed TESTS are recorded and the chain goes on.
#   B  build-deb   : build-deb.sh -> /var/tmp/jhan/i4500b-20260930/fix.deb from COMMIT_DEB (2fd11e32ca). A failure stops the chain.
#   C  smoke       : smoke.sh (runtron token rows: fixS1 vs fix, A/A, CPU and FPGA attention, prompts 1024 and 1000).
#   T  traces      : traces.sh (Perfetto decode traces: base c7844ca2ce / fix / fixS1 at tp2 2 users and tp4 4 users).
#   D  campaign    : campaign.sh (the rinzler cells; REPS, CELLS pass through).
#   E  build-fixS1rm: build2.sh with TRON_K_VNNI=OFF at COMMIT_FIX (the row-major build must still pass the changed tests).
# Log: exec/logs/i4500b-20260930-chain.log; status: exec/logs/i4500b-20260930-chain.status; marker RES/chain.done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4500b-20260930
RES=$EXEC/results/i4500b-20260930
LOG=$EXEC/logs/i4500b-20260930-chain.log
STATUS=$EXEC/logs/i4500b-20260930-chain.status
export NOT_BEFORE=${NOT_BEFORE:-2026-09-30T13:00:00Z}
COMMIT_FIX=${COMMIT_FIX:-452b2052c9}
COMMIT_DEB=${COMMIT_DEB:-2fd11e32ca}
COMMIT_REF=${COMMIT_REF:-f34b0fe2ec}
export REPS=${REPS:-3}
STEPS=${STEPS:-"A0 A B C T D E"}
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
pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/i4500b-20260930/chain[.]sh$' | grep -vx "$$" | grep -q . && { echo "$(ts) another chain.sh runs; exit"; exit 1; }
rm -f "$RES/chain.done"
echo "=== i4500b chain started $(ts) pid $$ on $(hostname) NOT_BEFORE=$NOT_BEFORE STEPS=[$STEPS] REPS=$REPS COMMIT_FIX=$COMMIT_FIX COMMIT_DEB=$COMMIT_DEB COMMIT_REF=$COMMIT_REF ==="
# Builds need only the lease and an idle machine of other people; they leave the production engines alone.
wait_build_slot() { local waited=0; not_before_wait || return 1; while preci_hold || ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $waited = 0 ] && { status "waiting before $1: pre-CI hold, CI lease busy or another person active"; waited=1; }; sleep 120; done; echo "$(ts) $1 may start: $(machine_line)"; }
# Run a build step in the background and stop it (its process group) if the CI lease turns busy meanwhile.
run_build() { setsid bash -c "$1" & local bp=$!; while kill -0 $bp 2>/dev/null; do if ci_lease_busy; then echo "$(ts) CI lease busy during $2: stopping the build"; kill -TERM -- -$bp 2>/dev/null; sleep 5; kill -KILL -- -$bp 2>/dev/null; fi; sleep 60; done; wait $bp; }
trap 'serving_restore' EXIT
step_done() { [ -e "$RES/$1" ] && grep -q -E "^(ok|tests-failed-[0-9]+|done)$" "$RES/$1"; }
fail_chain() { status "chain stopped: $*"; echo "stopped: $*" >"$RES/chain.done"; exit 1; }
for step in $STEPS; do
  case $step in
    A0)
      if step_done build-fix.done; then echo "$(ts) step A0 already done: $(cat "$RES/build-fix.done")"; continue; fi
      wait_build_slot "step A0 (build-fixrt)" || fail_chain "bad NOT_BEFORE"; status "step A0: runtron of $COMMIT_REF (VNNI build, incremental)"
      run_build "env RES='$RES' SRC=/home/jhan/workspace/tron COMMIT='$COMMIT_REF' WT=/var/tmp/jhan/tron-i4500 SUFFIX=fix CONFIGURE_ARGS='$CONF_VNNI' TARGETS='runtron' TESTS='' bash $EXEC/i4525-20260922/build2.sh" "step A0"
      r=$(cat "$RES/build-fix.done" 2>/dev/null); echo "$(ts) step A0 result: $r"
      case $r in ok) ;; *) fail_chain "step A0 build failed ($r), see $RES/build-fix.log" ;; esac ;;
    A)
      if step_done build-fixS1.done; then echo "$(ts) step A already done: $(cat "$RES/build-fixS1.done")"; continue; fi
      wait_build_slot "step A (build-fixS1)" || fail_chain "bad NOT_BEFORE"; status "step A: build + tests of $COMMIT_FIX (VNNI build)"
      run_build "env RES='$RES' SRC=/home/jhan/workspace/tron COMMIT='$COMMIT_FIX' WT=/var/tmp/jhan/tron-i4500b SUFFIX=fixS1 CONFIGURE_ARGS='$CONF_VNNI' TARGETS='$TARGETS_ALL' TESTS='$TESTS_ALL' bash $EXEC/i4525-20260922/build2.sh" "step A"
      r=$(cat "$RES/build-fixS1.done" 2>/dev/null); echo "$(ts) step A result: $r"
      case $r in ok) ;; tests-failed-*) status "step A: $r (see $RES/tests-fixS1.txt); chain continues" ;; *) fail_chain "step A build failed ($r), see $RES/build-fixS1.log" ;; esac ;;
    B)
      if [ "$(cat /var/tmp/jhan/i4500b-20260930/build.status 2>/dev/null)" = ok ] && [ -x /var/tmp/jhan/i4500b-20260930/root/opt/positron/bin/rinzler ]; then echo "$(ts) step B already done"; continue; fi
      wait_build_slot "step B (build-deb)" || fail_chain "bad NOT_BEFORE"; status "step B: deb build of $COMMIT_DEB"
      run_build "COMMIT='$COMMIT_DEB' bash $C/build-deb.sh >>$RES/build-deb.log 2>&1" "step B"
      [ "$(cat /var/tmp/jhan/i4500b-20260930/build.status 2>/dev/null)" = ok ] || fail_chain "step B deb build failed, see $RES/build-deb.log and /var/tmp/jhan/i4500b-20260930/make-deb.log" ;;
    C)
      if [ "$(cat "$RES/smoke/smoke.done" 2>/dev/null)" = done ]; then echo "$(ts) step C already done"; continue; fi
      status "step C: smoke"; bash "$C/smoke.sh"; echo "$(ts) step C result: $(tail -4 "$RES/smoke/smoke.txt" 2>/dev/null | tr '\n' ' ')" ;;
    T)
      if [ "$(cat "$RES/traces/traces.done" 2>/dev/null)" = done ]; then echo "$(ts) step T already done"; continue; fi
      status "step T: traces"; bash "$C/traces.sh"; echo "$(ts) step T result: $(cat "$RES/traces/traces.done" 2>/dev/null)" ;;
    D)
      if [ -e "$RES/campaign.done" ] && [ "$(cat "$RES/campaign.done")" = ok ]; then echo "$(ts) step D already done"; continue; fi
      status "step D: campaign"; bash "$C/campaign.sh"; echo "$(ts) step D result: $(cat "$RES/campaign.done" 2>/dev/null)" ;;
    E)
      if step_done build-fixS1rm.done; then echo "$(ts) step E already done: $(cat "$RES/build-fixS1rm.done")"; continue; fi
      wait_build_slot "step E (build-fixS1rm)" || fail_chain "bad NOT_BEFORE"; status "step E: build + tests of $COMMIT_FIX (row-major build)"
      run_build "env RES='$RES' SRC=/home/jhan/workspace/tron COMMIT='$COMMIT_FIX' WT=/var/tmp/jhan/tron-i4500rm SUFFIX=fixS1rm CONFIGURE_ARGS='$CONF_RM' TARGETS='$TESTS_RM' TESTS='$TESTS_RM' bash $EXEC/i4525-20260922/build2.sh" "step E"
      echo "$(ts) step E result: $(cat "$RES/build-fixS1rm.done" 2>/dev/null)" ;;
  esac
done
serving_restore
echo "ok" >"$RES/chain.done"; status "chain finished"
echo "=== i4500b chain finished $(ts): A0=$(cat "$RES/build-fix.done" 2>/dev/null) A=$(cat "$RES/build-fixS1.done" 2>/dev/null) B=$(cat /var/tmp/jhan/i4500b-20260930/build.status 2>/dev/null) C=$(cat "$RES/smoke/smoke.done" 2>/dev/null) T=$(cat "$RES/traces/traces.done" 2>/dev/null) D=$(cat "$RES/campaign.done" 2>/dev/null) E=$(cat "$RES/build-fixS1rm.done" 2>/dev/null) ==="
