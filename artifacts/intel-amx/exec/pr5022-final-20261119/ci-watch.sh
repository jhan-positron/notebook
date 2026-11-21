#!/usr/bin/env bash
# pr5022-final-20261119 CI watch. Runs on the agent's own machine (claude-box), not on a test server.
# Polls the CI runs of the pushed head of tron PR 5022 every 90 s and appends one status line per poll to
# exec/results/pr5022-final-20261119/ci-watch.txt. It only reads from GitHub.
# It ends when every run is completed, or as soon as one run completes with a conclusion other than success.
# Usage: bash ci-watch.sh <run id> [<run id> ...]
set -u
OUT=/home/jhan/workspace/intel-AMX/exec/results/pr5022-final-20261119/ci-watch.txt
REPO=positron-ai/tron
[ $# -ge 1 ] || { echo "usage: $0 <run id> ..."; exit 2; }
echo "# watch started $(date '+%F %T %Z') for runs: $*" >>"$OUT"
while :; do
  all=1; bad=0; line="$(date '+%F %T %Z')"
  for r in "$@"; do
    j=$(gh run view "$r" -R $REPO --json status,conclusion,workflowName \
          --jq '"\(.workflowName) [\(.databaseId // "")]=\(.status)/\(.conclusion // "-")"' 2>/dev/null) || j="$r=query-failed/-"
    line="$line | $j"
    case "$j" in
      *=completed/success) ;;
      *=completed/*) bad=1 ;;
      *) all=0 ;;
    esac
  done
  echo "$line" >>"$OUT"
  if [ $bad = 1 ]; then echo "# a run completed without success, $(date '+%F %T %Z')" >>"$OUT"; tail -2 "$OUT"; exit 1; fi
  if [ $all = 1 ]; then echo "# all runs completed with success, $(date '+%F %T %Z')" >>"$OUT"; tail -2 "$OUT"; exit 0; fi
  sleep 90
done
