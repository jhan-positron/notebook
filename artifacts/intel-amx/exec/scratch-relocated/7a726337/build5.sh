#!/bin/bash
cd /var/tmp/jhan/tron-issue4525 || exit 1
T=/var/tmp/jhan/tron-issue4525-tests
SIG=$HOME/workspace/intel-AMX/exec/results/i4525-20260922/chain-steps.txt
date -u
if grep -q "STEP E-head" "$SIG" 2>/dev/null; then echo "STEP E already started; not building"; exit 3; fi
setsid taskset -c 72-143,216-287 "$HOME/.nix-profile/bin/nix" develop --accept-flake-config --command bash -c 'cmake --build gen -j 48 --target t_llama_unit -- -k 0 2>&1 | grep -vE "^\[[0-9]+/[0-9]+\] "; echo BUILD5 EXIT ${PIPESTATUS[0]}' > $T/build5.log 2>&1 &
BPID=$!
while kill -0 $BPID 2>/dev/null; do
  if grep -q "STEP E-head" "$SIG" 2>/dev/null; then kill -- -$BPID 2>/dev/null; echo "WATCHDOG: Step E signal seen, build stopped"; exit 4; fi
  sleep 5
done
grep -E "BUILD5 EXIT|error:" $T/build5.log | grep -v nix.conf | head -12
grep -q "BUILD5 EXIT 0" $T/build5.log || exit 5
if grep -q "STEP E-head" "$SIG" 2>/dev/null; then echo "STEP E started; skipping the run"; exit 3; fi
taskset -c 72-143 gen/t_llama_unit > $T/t_llama_unit.rev.log 2>&1; echo "REV t_llama_unit EXIT $? ($(grep -E 'All tests passed|test cases' $T/t_llama_unit.rev.log | tail -1))"
grep -E "Catch2 passed \"(packed V rows|a host tensor|bf16 rows|float rows|fp16 rows)" $T/t_llama_unit.rev.log | sed 's/.*Catch2 passed//' | sort | uniq -c
date -u
