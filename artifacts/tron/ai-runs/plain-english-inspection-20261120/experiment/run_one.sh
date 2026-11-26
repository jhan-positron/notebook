#!/bin/bash
# usage: run_one.sh TASK ARM REP   -> out/TASK_ARM_REP.json
# One headless run. --safe-mode drops CLAUDE.md, skills, hooks and plugins, so the
# only writing rules in context are the ones in ctx/ctx_ARM.md.
E=/home/jhan/workspace/ai-runs/plain-english-inspection-20261120/experiment
task=$1; arm=$2; rep=$3
out=$E/out/${task}_${arm}_${rep}.json
[ -s "$out" ] && exit 0
cd /tmp || exit 1
timeout 600 claude -p --safe-mode --tools "" --model claude-fable-5-2 --no-session-persistence \
  --append-system-prompt-file $E/ctx/ctx_${arm}.md --output-format json \
  < $E/prompts/${task}.txt > "$out" 2> "${out%.json}.err"
echo "$task $arm $rep exit=$? bytes=$(stat -c %s "$out")"
