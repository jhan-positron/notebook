#!/bin/bash
# Usage: wait_job.sh JOB_ID MAX_MINUTES ; polls one job of positron-ai/tron until it is completed, prints runner and result.
job=$1; max=${2:-30}
for ((i=0; i<max*4; i++)); do
  out=$(gh api repos/positron-ai/tron/actions/jobs/$job --jq '[.name,.status,(.conclusion//""),(.runner_name//""),(.run_attempt|tostring),(.started_at//""),(.completed_at//"")]|@tsv' 2>&1)
  st=$(echo "$out" | cut -f2)
  if [ "$st" = "completed" ]; then echo "$(date -u +%FT%TZ) job $job: $out"; exit 0; fi
  sleep 15
done
echo "$(date -u +%FT%TZ) job $job: not completed after $max minutes: $out"; exit 3
