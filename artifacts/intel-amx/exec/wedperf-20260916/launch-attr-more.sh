#!/usr/bin/env bash
# Block F launcher (run ON delphi-3bda, detached): after block E (wedperf-attr2-20260916) has written
# its marker, relaunch campaign-attr.sh under the block D NAME with REPS_B=6: the CPU cells (REPS=2)
# are already complete and are skipped, the three FPGA-attention cells gain repetitions 3 to 6 with
# the three binaries interleaved (the tp4 FPGA cells had sd up to 12 TPS at n = 2). Idempotent.
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/wedperf-20260916
PREV_MARKER=$EXEC/logs/wedperf-attr2-20260916.done
export NAME=wedperf-attr-20260916 GEN_LEN=256 REPS=2 DO_SMOKE=0 DO_B=1 REPS_B=${REPS_B:-6} DEADLINE_HHMM=${DEADLINE_HHMM:-130}
export ARMS="base mid target" CELLS_A="gptoss-tp4-8u g2-9b-tp2-8u q3-4b-tp2-8u l8b-tp2-8u"
export CELLS_B="gptoss-tp4-8u q3-4b-tp4-8u q3-4b-tp2-8u"
export WEDPERF_ARMS="base mid target" WEDPERF_PAIRS="mid:base target:mid target:base"
LOG=$EXEC/logs/$NAME-more-launcher.log
if pgrep -f "(^|/)bash $C/campaign-attr[.]sh" >/dev/null; then echo "already running"; exit 0; fi
ts() { date -u +%FT%TZ; }
{
  echo "$(ts) block F launcher pid $$ waits for $PREV_MARKER"
  until [ -s "$PREV_MARKER" ]; do sleep 60; done
  echo "$(ts) block E marker: $(cat "$PREV_MARKER"); relaunching campaign-attr.sh NAME=$NAME REPS_B=$REPS_B (FPGA cells, repetitions 3-$REPS_B)"
  bash "$C/campaign-attr.sh"
  echo "$(ts) campaign-attr.sh returned rc=$?; marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
} >>"$LOG" 2>&1
