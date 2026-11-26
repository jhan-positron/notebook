#!/bin/bash
# Usage: wait_run.sh RUN_ID MAX_MINUTES ; polls one run of positron-ai/tron until it is completed.
run=$1; max=${2:-90}
for ((i=0; i<max*2; i++)); do
  out=$(gh run view "$run" --repo positron-ai/tron --json status,conclusion,workflowName,updatedAt --jq '[.workflowName,.status,.conclusion,.updatedAt]|@tsv' 2>&1)
  st=$(echo "$out" | cut -f2)
  if [ "$st" = "completed" ]; then echo "$(date -u +%FT%TZ) run $run: $out"; gh run view "$run" --repo positron-ai/tron --json jobs --jq '.jobs[] | [.databaseId,.name,.status,.conclusion,.startedAt,.completedAt] | @tsv'; exit 0; fi
  sleep 30
done
echo "$(date -u +%FT%TZ) run $run: not completed after $max minutes: $out"; exit 3
