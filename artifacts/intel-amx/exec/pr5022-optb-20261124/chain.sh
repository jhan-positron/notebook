#!/usr/bin/env bash
# pr5022-optb-20261124 chain. Runs ON delphi-3b35, detached, on OUR half only (CPUs 96-143, FPGA cards 90/93/b9/bc).
#
# Question: does option B (one changed declaration of s_pages, see build-3b35.sh) leave tron's output and
# throughput unchanged? Two binaries from one commit and one recipe are compared: a = unchanged, b = with the change.
# Words: tron = the inference program; runtron = its command-line tool; AMX = Intel tile-matrix instructions;
# kv_mul = query heads per KV head (16 for Muse Glimmer, 4 for llama-3.1-8b); tp4 = one engine on four FPGA cards.
#
# Steps (STEPS, default "B T I P"):
#   B  build both trees in parallel (build-3b35.sh).
#   T  the three unit tests of each tree, with the fake device (no FPGA card).
#   I  identity: per model, 1 user, temperature 0, --pay-for-determinism, seed 1, prompt 1024 tokens, 256 generated
#      tokens. Runs a1, a2 (the same binary twice) and b1. The token files of a1 and a2 must match (the setup is
#      repeatable), and those of a1 and b1 must match (the change keeps the output).
#   P  throughput: per model, 8 users, prompt 1024 tokens, 256 generated tokens, REPS repetitions per arm. The arm
#      order alternates per repetition, so a slow drift of the machine does not favour one arm.
# Cells (key|model|environment of both arms):
#   glm-tp4      Muse Glimmer 30B, the model's default attention: 13 full layers on the FPGA cards and 39
#                sliding-window layers on the CPU, where the AMX kernels run with kv_mul 16.
#   l8b-tp4-cpu  llama-3.1-8b-instruct-good with USE_HW_ATTN=0: all attention on the CPU, AMX kernels with kv_mul 4.
# Every run goes through run-one.sh: load snapshot first, refusal when our cards are open or our CPUs are busy.
# Outputs: exec/results/pr5022-optb-20261124/{build-*.txt,tests.txt,identity.txt,tokens/,rt-results.txt,rt/,load/},
#          log exec/logs/pr5022-optb-20261124-chain.log, marker exec/results/pr5022-optb-20261124/chain.done.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5022-optb-20261124
C=$EXEC/$NAME
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
MARKER=$RES/chain.done
STEPS=${STEPS:-"B T I P"}
REPS=${REPS:-4}
PROMPT=1024
LEN=256
OUR_CPUS=96-143
PIN="nice -n10 taskset -c $OUR_CPUS"
CELLS_ALL=$'glm-tp4|ingested-meta-models--Muse-Glimmer-30B-tp4|TRON_ATTN_STATS=1
l8b-tp4-cpu|llama-3.1-8b-instruct-good-tp4|TRON_ATTN_STATS=1 USE_HW_ATTN=0'
CELLS=${CELLS:-"glm-tp4 l8b-tp4-cpu"}
mkdir -p "$RES/tokens" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
exec {CHAIN_LOCK_FD}>"/var/tmp/jhan/$NAME.chain.lock"
flock -n "$CHAIN_LOCK_FD" || { echo "$(ts) another chain.sh holds the lock; this copy exits"; exit 1; }
rm -f "$MARKER"
finish() { echo "$1" >"$MARKER"; echo "=== chain finished $(ts): $1 ==="; exit "${2:-0}"; }
cell_field() { local line; line=$(grep -m1 "^$1|" <<<"$CELLS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
has_step() { case " $STEPS " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }
echo "=== $NAME chain started $(ts) pid $$ STEPS=[$STEPS] CELLS=[$CELLS] REPS=$REPS ==="
# One run through run-one.sh. A refused run (exit code 3: our half is not free) is tried again after 2 minutes.
one_run() { # $1 run name, $2 tag, $3 model, $4 users, $5 arm environment, $6 extra runtron arguments
  local try rc
  for try in 1 2 3 4 5 6; do
    ( exec {CHAIN_LOCK_FD}>&-; RUN=$1 TAG=$2 MODEL=$3 USERS=$4 PROMPT=$PROMPT LEN=$LEN ARMENV="$5" EXTRA="$6" NAME=$NAME bash "$C/run-one.sh" ) 2>&1 | tail -14
    rc=${PIPESTATUS[0]}
    [ "$rc" -ne 3 ] && return "$rc"
    echo "$(ts) run $1 refused (try $try); waiting 120 s"; sleep 120
  done
  return 3
}

if has_step B; then
  echo "$(ts) step B: builds a and b in parallel"
  ( exec {CHAIN_LOCK_FD}>&-; TAG=a bash "$C/build-3b35.sh" ) &
  pa=$!
  ( exec {CHAIN_LOCK_FD}>&-; TAG=b bash "$C/build-3b35.sh" ) &
  pb=$!
  wait $pa; wait $pb
  for tag in a b; do
    [ "$(cat "$RES/build-$tag.done" 2>/dev/null)" = ok ] || finish "failed in step B: build $tag: $(cat "$RES/build-$tag.done" 2>/dev/null)" 1
  done
  echo "$(ts) step B done"
fi

if has_step T; then
  echo "$(ts) step T: unit tests of both trees"
  : >"$RES/tests.txt"
  tfail=0
  for tag in a b; do
    for t in t_amx_dispatch_dtype t_amx_numerics t_llama_unit; do
      out=$( cd "/var/tmp/jhan/b35-optb-$tag" && SYSTEM_CONFIG="--instance 1,2" $PIN "gen/$t" 2>&1 ); rc=$?
      echo "tree $tag $t exit code $rc: $(grep -E 'All tests passed|test cases:|assertions:' <<<"$out" | tr '\n' ' ')" | tee -a "$RES/tests.txt"
      [ $rc -eq 0 ] || tfail=$((tfail + 1))
    done
  done
  [ $tfail -eq 0 ] || finish "failed in step T: $tfail unit test runs failed" 1
  echo "$(ts) step T done"
fi

if has_step I; then
  echo "$(ts) step I: identity runs"
  : >"$RES/identity.txt"
  ifail=0
  for key in $CELLS; do
    model=$(cell_field "$key" 2); armenv=$(cell_field "$key" 3)
    for r in a1 a2 b1; do
      run=id-${key}__$r
      tok=$RES/tokens/$run.tokens
      one_run "$run" "${r%[0-9]}" "$model" 1 "$armenv" "--temperature 0 --pay-for-determinism -s 1 --output-token-file $tok"
      rc=$?
      echo "$(ts) end $run rc=$rc"
      [ $rc -eq 0 ] && [ -s "$tok" ] || finish "failed in step I: run $run rc=$rc" 1
      sleep 5
    done
    ha1=$(sha256sum "$RES/tokens/id-${key}__a1.tokens" | cut -d' ' -f1)
    ha2=$(sha256sum "$RES/tokens/id-${key}__a2.tokens" | cut -d' ' -f1)
    hb1=$(sha256sum "$RES/tokens/id-${key}__b1.tokens" | cut -d' ' -f1)
    {
      echo "cell $key model $model"
      echo "  a1 $ha1 ($(wc -w <"$RES/tokens/id-${key}__a1.tokens") words)"
      echo "  a2 $ha2"
      echo "  b1 $hb1"
      echo "  a1 vs a2 (same binary twice): $([ "$ha1" = "$ha2" ] && echo identical || echo DIFFERENT)"
      echo "  a1 vs b1 (without vs with the change): $([ "$ha1" = "$hb1" ] && echo identical || echo DIFFERENT)"
    } | tee -a "$RES/identity.txt"
    [ "$ha1" = "$ha2" ] && [ "$ha1" = "$hb1" ] || ifail=$((ifail + 1))
  done
  echo "identity cells that differ: $ifail" | tee -a "$RES/identity.txt"
  echo "$(ts) step I done"
fi

if has_step P; then
  echo "$(ts) step P: throughput runs, REPS=$REPS"
  pfail=0; consec=0
  for rep in $(seq 1 "$REPS"); do
    arms="a b"; [ $((rep % 2)) -eq 0 ] && arms="b a"
    for key in $CELLS; do
      model=$(cell_field "$key" 2); armenv=$(cell_field "$key" 3)
      for arm in $arms; do
        run=${key}-8u-p${PROMPT}__${arm}__rep${rep}
        echo "$(ts) start $run"
        one_run "$run" "$arm" "$model" 8 "$armenv" ""
        rc=$?
        echo "$(ts) end $run rc=$rc"
        if [ $rc -eq 0 ]; then consec=0; else pfail=$((pfail + 1)); consec=$((consec + 1)); fi
        [ $consec -ge 2 ] && finish "failed in step P: 2 consecutive failed runs (last: $run)" 1
        sleep 5
      done
    done
  done
  [ $pfail -eq 0 ] || finish "step P ended with $pfail failed runs" 1
  echo "$(ts) step P done"
fi
finish ok 0
