#!/usr/bin/env bash
# gdn-impl-20261121 campaign: measured effect of the GDN/AMX changes on Qwen3.5 4B, on OUR half of delphi-3b35.
# Each run goes through exec/gdn-20261120/run-one.sh (load snapshot first, SYSTEM_CONFIG="--instance 1,2",
# refuses to start when our cards or CPUs are busy).
#
# Words: tron = the inference program, runtron = its command-line tool; GDN = GatedDeltaNet, the recurrent layer
# type in 24 of the model's 32 layers; AMX = Intel tile-matrix instructions; tp4 = one engine on four FPGA cards;
# TTFT = time to first token; arm = one build with one set of switches.
#
# Arms (name|build tag|extra environment). Every arm also sets TRON_ATTN_STATS=1 TRON_GDN_STATS=1 (the counters).
#   base  ctr  -                        today's GDN token loop, AVX-512 attention (the build holds only the counters)
#   p0    pab  TRON_AMX_DISABLE=1       Part 0: GDN chain kernel, AVX-512 attention (kill switch: no AMX kernel runs)
#   b     pab  TRON_AMX_GDN_DISABLE=1   Part 0 + Part B: GDN chain kernel, AMX attention (GDN switch set)
#   ab    pab  -                        Part A + Part B: AMX block kernel for GDN, AMX attention
#   a0    pa   TRON_AMX_GDN_DISABLE=1   Part 0 in the build without Part B (run 1 of the Part A comparison)
#   a     pa   -                        Part A: AMX block kernel for GDN, AVX-512 attention
#   orig  base -                        the baseline build of 2026-11-20 (no counters; TRON_GDN_STATS is ignored)
#   nost  ctr  (TRON_GDN_STATS unset)   the counter build with the GDN counters off
# Cell table: key|model|users|prompt|len. The run name is <key>__<arm>__rep<N>.
# Inputs: CELLS (keys, default all 6), ARMS (default "base p0 b ab a0 a"), REPS (default 3), FIRST_REP (default 1).
# The arm order is rotated by one position per repetition, so a slow drift of the machine does not favour one arm.
# Outputs: exec/results/gdn-impl-20261121/rt/<run>.log, load/<run>.txt, rt-results.txt;
#          log exec/logs/gdn-impl-20261121-campaign.log; marker exec/logs/gdn-impl-20261121-campaign.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=gdn-impl-20261121
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-campaign.log
MARKER=$EXEC/logs/$NAME-campaign.done
REPS=${REPS:-3}
FIRST_REP=${FIRST_REP:-1}
ARMS=${ARMS:-"base p0 b ab a0 a"}
STATS="TRON_ATTN_STATS=1 TRON_GDN_STATS=1"
ARMS_ALL=$'base|ctr|'"$STATS"$'
p0|pab|'"$STATS"$' TRON_AMX_DISABLE=1
b|pab|'"$STATS"$' TRON_AMX_GDN_DISABLE=1
ab|pab|'"$STATS"$'
a0|pa|'"$STATS"$' TRON_AMX_GDN_DISABLE=1
a|pa|'"$STATS"$'
orig|base|'"$STATS"$'
nost|ctr|TRON_ATTN_STATS=1'
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
echo "=== $NAME campaign started $(ts) pid $$ CELLS=[$CELLS] ARMS=[$ARMS] REPS=$FIRST_REP..$REPS ==="
cell_field() { local line; line=$(grep -m1 "^$1|" <<<"$CELLS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
arm_field() { local line; line=$(grep -m1 "^$1|" <<<"$ARMS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
for arm in $ARMS; do
  tag=$(arm_field "$arm" 2) || { echo "unknown arm $arm"; exit 1; }
  [ -x "/var/tmp/jhan/b35-gdn-$tag/gen/runtron" ] || { echo "arm $arm: /var/tmp/jhan/b35-gdn-$tag/gen/runtron missing"; exit 1; }
  echo "arm $arm = build $tag at $(git -C "/var/tmp/jhan/b35-gdn-$tag" rev-parse --short HEAD), env [$(arm_field "$arm" 3)]"
done
n_arms=$(wc -w <<<"$ARMS")
fails=0; consec=0
for rep in $(seq "$FIRST_REP" "$REPS"); do
  # rotate the arm order by (rep - 1) positions
  shift_by=$(( (rep - 1) % n_arms ))
  arms_rep=$(tr ' ' '\n' <<<"$ARMS" | awk -v s="$shift_by" '{a[NR]=$0} END {for (i = 0; i < NR; i++) printf "%s ", a[(i + s) % NR + 1]}')
  for key in $CELLS; do
    model=$(cell_field "$key" 2) || { echo "$(ts) unknown cell $key"; fails=$((fails + 1)); continue; }
    for arm in $arms_rep; do
      run=${key}__${arm}__rep${rep}
      echo "$(ts) start $run"
      ( exec {CAMP_LOCK_FD}>&-; RUN=$run MODEL=$model USERS=$(cell_field "$key" 3) PROMPT=$(cell_field "$key" 4) LEN=$(cell_field "$key" 5) \
        ARMENV="$(arm_field "$arm" 3)" TAG=$(arm_field "$arm" 2) NAME=$NAME bash "$EXEC/gdn-20261120/run-one.sh" ) 2>&1 | tail -12
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
