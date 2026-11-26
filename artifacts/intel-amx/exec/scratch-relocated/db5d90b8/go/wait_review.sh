#!/bin/bash
# Exits when PR 5022 has a new review, inline comment or conversation comment (baseline 4 / 56 / 3), or after MAX minutes.
max=${1:-40}
for ((i=0; i<max*2; i++)); do
  r=$(gh api "repos/positron-ai/tron/pulls/5022/reviews?per_page=100" --jq 'length' 2>/dev/null)
  c=$(gh api "repos/positron-ai/tron/pulls/5022/comments?per_page=100" --jq 'length' 2>/dev/null)
  k=$(gh api "repos/positron-ai/tron/issues/5022/comments?per_page=100" --jq 'length' 2>/dev/null)
  if [ -n "$r" ] && [ -n "$c" ] && [ -n "$k" ] && { [ "$r" != 4 ] || [ "$c" != 56 ] || [ "$k" != 3 ]; }; then
    echo "$(date -u +%FT%TZ) change: reviews=$r inline=$c conversation=$k"; exit 0; fi
  sleep 30
done
echo "$(date -u +%FT%TZ) no change after $max minutes: reviews=$r inline=$c conversation=$k"; exit 0
