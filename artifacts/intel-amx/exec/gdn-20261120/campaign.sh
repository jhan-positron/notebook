#!/usr/bin/env bash
# gdn-20261120 campaign: baseline of the Qwen3.5 4B model (tron slug ingested-qwen-3.5-4b) on OUR half of
# delphi-3b35. Each cell is run by run-one.sh (load snapshot first, SYSTEM_CONFIG="--instance 1,2").
#
# Words: tron = the inference program, runtron = its command-line tool; GDN = GatedDeltaNet, the recurrent layer
# type in 24 of the model's 32 layers; AMX = Intel tile-matrix instructions; tp4 = one engine on four FPGA cards.
#   arms: on  = TRON_ATTN_STATS=1 (attention path statistics on; AMX kernels allowed),
#         off = TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1 (the AMX kill switch: every software attention visit takes AVX).
#   cell table: key|model|users|prompt|len. The run name is <key>__<arm>__rep<N>.
# Inputs: CELLS (keys to run, default all), ARMS (default "on off"), REPS (default 1), FIRST_REP (default 1),
#         NAME (results folder, default gdn-20261120), TAG (build tag, default base).
# The arm order alternates per repetition, so a slow drift of the machine does not favour one arm.
# Outputs: see run-one.sh; log exec/logs/$NAME-campaign.log; marker exec/logs/$NAME-campaign.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/gdn-20261120
NAME=${NAME:-gdn-20261120}
TAG=${TAG:-base}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-campaign.log
MARKER=$EXEC/logs/$NAME-campaign.done
REPS=${REPS:-1}
FIRST_REP=${FIRST_REP:-1}
ARMS=${ARMS:-"on off"}
ARM_ENV_on=${ARM_ENV_on:-"TRON_ATTN_STATS=1"}
ARM_ENV_off=${ARM_ENV_off:-"TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"}
CELLS_ALL=${CELLS_ALL:-$'q35-tp4-1u-p1024|ingested-qwen-3.5-4b-tp4|1|1024|256
q35-tp4-8u-p1024|ingested-qwen-3.5-4b-tp4|8|1024|256
q35-tp4-1u-p4096|ingested-qwen-3.5-4b-tp4|1|4096|256
q35-tp4-8u-p4096|ingested-qwen-3.5-4b-tp4|8|4096|256
q35-tp4-1u-p8192|ingested-qwen-3.5-4b-tp4|1|8192|256
q35-tp4-8u-p8192|ingested-qwen-3.5-4b-tp4|8|8192|256'}
CELLS=${CELLS:-$(cut -d"|" -f1 <<<"$CELLS_ALL" | tr "\n" " ")}
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
exec {CAMP_LOCK_FD}>"/var/tmp/jhan/$NAME.campaign.lock"
flock -n "$CAMP_LOCK_FD" || { echo "$(ts) another campaign.sh holds the lock; this copy exits"; exit 1; }
rm -f "$MARKER"
echo "=== $NAME campaign started $(ts) pid $$ CELLS=[$CELLS] ARMS=[$ARMS] REPS=$FIRST_REP..$REPS TAG=$TAG ==="
cell_field() { local line; line=$(grep -m1 "^$1|" <<<"$CELLS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
arm_env() { local v="ARM_ENV_$1"; echo "${!v:-}"; }
fails=0; consec=0
for rep in $(seq "$FIRST_REP" "$REPS"); do
  arms_rep=$ARMS
  [ $((rep % 2)) -eq 0 ] && arms_rep=$(tr ' ' '\n' <<<"$ARMS" | tac | tr '\n' ' ')
  for key in $CELLS; do
    model=$(cell_field "$key" 2) || { echo "$(ts) unknown cell $key"; fails=$((fails + 1)); continue; }
    for arm in $arms_rep; do
      run=${key}__${arm}__rep${rep}
      echo "$(ts) start $run"
      ( exec {CAMP_LOCK_FD}>&-; RUN=$run MODEL=$model USERS=$(cell_field "$key" 3) PROMPT=$(cell_field "$key" 4) LEN=$(cell_field "$key" 5) \
        ARMENV="$(arm_env "$arm")" TAG=$TAG NAME=$NAME bash "$C/run-one.sh" ) 2>&1 | tail -12
      rc=${PIPESTATUS[0]}
      echo "$(ts) end $run rc=$rc"
      if [ "$rc" -eq 0 ]; then consec=0; else fails=$((fails + 1)); consec=$((consec + 1)); fi
      [ $consec -ge 3 ] && { echo "$(ts) 3 consecutive failed runs; campaign ends"; echo "aborted-3-consecutive-failures" >"$MARKER"; exit 1; }
      sleep 5
    done
  done
  echo "$(ts) repetition $rep done (arm order [$arms_rep]), failed runs so far: $fails"
done
echo "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")" >"$MARKER"
echo "=== campaign finished $(ts): $(cat "$MARKER") ==="
