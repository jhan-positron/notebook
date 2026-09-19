#!/usr/bin/env bash
# Block C launcher (run ON delphi-3bda, detached): wait until the main wedperf-20260916 campaign has
# written its marker, then run campaign-gen.sh with the nightly's generated-token count (1536) over
# the 12 cells, CPU attention, 2 repetitions, no smokes, no FPGA block, under its own NAME.
# Idempotent: exits if a campaign-gen.sh of this NAME is already running.
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/wedperf-20260916
MAIN_MARKER=$EXEC/logs/wedperf-20260916.done
export NAME=wedperf-gen1536-20260916 GEN_LEN=1536 REPS=${REPS:-2} DO_SMOKE=0 DO_B=0 DEADLINE_HHMM=${DEADLINE_HHMM:-130}
LOG=$EXEC/logs/$NAME-launcher.log
if pgrep -f "(^|/)bash $C/campaign-gen[.]sh" >/dev/null; then echo "already running"; exit 0; fi
ts() { date -u +%FT%TZ; }
{
  echo "$(ts) block C launcher pid $$ waits for $MAIN_MARKER"
  until [ -s "$MAIN_MARKER" ]; do sleep 60; done
  echo "$(ts) main campaign marker: $(cat "$MAIN_MARKER"); starting campaign-gen.sh NAME=$NAME GEN_LEN=$GEN_LEN REPS=$REPS"
  bash "$C/campaign-gen.sh"
  echo "$(ts) campaign-gen.sh returned rc=$?; marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
} >>"$LOG" 2>&1
