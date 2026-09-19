#!/usr/bin/env bash
# Block E launcher (run ON delphi-3bda, detached): wait until block D (wedperf-attr-20260916) has
# written its marker, build runtron.p3879 from 3fd5edaa66 (the PR #3879 merge commit; same flags as
# the mid binary plus the production model tag so build.sh's slug check passes), then run
# campaign-attr2.sh with four binaries on the gpt-oss cell in both attention modes. Idempotent.
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/wedperf-20260916
PREV_MARKER=$EXEC/logs/wedperf-attr-20260916.done
export NAME=wedperf-attr2-20260916 GEN_LEN=256 REPS=${REPS:-2} DO_SMOKE=0 DO_B=1 REPS_B=${REPS_B:-2} DEADLINE_HHMM=${DEADLINE_HHMM:-130}
export ARMS="base p3879 mid target" CELLS_A=${CELLS_A:-"gptoss-tp4-8u"} CELLS_B=${CELLS_B:-"gptoss-tp4-8u"}
export WEDPERF_ARMS="base p3879 mid target" WEDPERF_PAIRS="p3879:base mid:p3879 target:mid target:base"
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-launcher.log
if pgrep -f "(^|/)bash $C/campaign-attr2[.]sh" >/dev/null; then echo "already running"; exit 0; fi
ts() { date -u +%FT%TZ; }
{
  echo "$(ts) block E launcher pid $$ waits for $PREV_MARKER"
  until [ -s "$PREV_MARKER" ]; do sleep 60; done
  echo "$(ts) block D marker: $(cat "$PREV_MARKER"); building runtron.p3879"
  mkdir -p "$RES"
  RES=$RES LOG=$EXEC/logs/wedperf-build-p3879.log SKIP_LEASE_WAIT=1 EXPECT_K_VNNI=OFF EXPECT_AMX_DISPATCH=ON \
    bash "$C/build.sh" 3fd5edaa6659d0fb69960f0cbf5e3bc423274940 /var/tmp/jhan/tron-p3879 p3879 -DTRON_AMX_DISPATCH=ON -DBUILD_PRODUCTION_MODELS=ON; rc=$?
  [ -s "$RES/build-p3879.done" ] || echo "build-failed rc=$rc (build.sh left no marker)" >"$RES/build-p3879.done"
  echo "$(ts) build marker: $(cat "$RES/build-p3879.done")"
  bash "$C/campaign-attr2.sh"
  echo "$(ts) campaign-attr2.sh returned rc=$?; marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
} >>"$LOG" 2>&1
