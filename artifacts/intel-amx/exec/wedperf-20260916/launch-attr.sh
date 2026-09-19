#!/usr/bin/env bash
# Block D launcher (run ON delphi-3bda, detached): wait until block C (wedperf-gen1536-20260916) has
# written its marker, then run campaign-attr.sh with three binaries (base, mid = main c7844ca2ce,
# target) on the cells whose base-vs-target change needs attribution: CPU attention (CELLS_A, REPS
# repetitions) and FPGA attention (CELLS_B, REPS_B repetitions), 256 tokens, no smokes. Idempotent.
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/wedperf-20260916
PREV_MARKER=$EXEC/logs/wedperf-gen1536-20260916.done
export NAME=wedperf-attr-20260916 GEN_LEN=256 REPS=${REPS:-2} DO_SMOKE=0 DO_B=1 REPS_B=${REPS_B:-2} DEADLINE_HHMM=${DEADLINE_HHMM:-130}
export ARMS="base mid target" CELLS_A=${CELLS_A:-"gptoss-tp4-8u g2-9b-tp2-8u q3-4b-tp2-8u l8b-tp2-8u"}
# block B of the attribution run = the same three binaries in the nightly mode of the ingested cells (FPGA attention)
export CELLS_B=${CELLS_B:-"gptoss-tp4-8u q3-4b-tp4-8u q3-4b-tp2-8u"}
export WEDPERF_ARMS="base mid target" WEDPERF_PAIRS="mid:base target:mid target:base"   # summarize.py: three binaries, the two steps and the whole
LOG=$EXEC/logs/$NAME-launcher.log
if pgrep -f "(^|/)bash $C/campaign-attr[.]sh" >/dev/null; then echo "already running"; exit 0; fi
ts() { date -u +%FT%TZ; }
{
  echo "$(ts) block D launcher pid $$ waits for $PREV_MARKER"
  until [ -s "$PREV_MARKER" ]; do sleep 60; done
  echo "$(ts) block C marker: $(cat "$PREV_MARKER"); starting campaign-attr.sh NAME=$NAME ARMS=[$ARMS] CELLS_A=[$CELLS_A] REPS=$REPS"
  bash "$C/campaign-attr.sh"
  echo "$(ts) campaign-attr.sh returned rc=$?; marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
} >>"$LOG" 2>&1
