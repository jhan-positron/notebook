#!/bin/bash
K=/tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad/ksroot
B=/home/jhan/workspace/ai-runs/tron-split-pr1
H=/home/jhan/workspace/ai-runs/tron-pr5047
run() { # name worktree tu
  local s=$(date +%s)
  timeout 1200 $K/objcompile.sh $2 $K/tu/$3.cpp $K/obj/$1/$3.o > $K/log/$1-$3.log 2>&1
  echo "$1 $3 rc=$? secs=$(( $(date +%s) - s ))" >> $K/log/status.txt
}
: > $K/log/status.txt
run base $B model_llama_3p1_8b & 
run head $H model_llama_3p1_8b &
run base $B model_llama_3p1_8b_tp2only &
run head $H model_llama_3p1_8b_tp2only &
wait
echo ALLDONE >> $K/log/status.txt
