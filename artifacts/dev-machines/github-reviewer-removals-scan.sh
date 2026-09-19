#!/bin/bash
# Paginate all PRs in positron-ai/tron, collect ReviewRequestRemovedEvent nodes.
cursor=null
out=removals.jsonl
: > $out
while :; do
  resp=$(gh api graphql -f query="query(\$c:String){repository(owner:\"positron-ai\",name:\"tron\"){pullRequests(first:50,after:\$c,orderBy:{field:CREATED_AT,direction:DESC}){pageInfo{hasNextPage endCursor} nodes{number title state createdAt author{login} timelineItems(first:50,itemTypes:[REVIEW_REQUEST_REMOVED_EVENT]){nodes{... on ReviewRequestRemovedEvent{createdAt actor{login} requestedReviewer{__typename ... on User{login} ... on Team{name}}}}}}}}}" -F c="$cursor" 2>/dev/null) || { echo "fail at $cursor" >&2; break; }
  echo "$resp" | jq -c '.data.repository.pullRequests.nodes[] | {number,title,state,createdAt,author:.author.login} + {ev:.timelineItems.nodes} | select(.ev|length>0) | .ev[] as $e | {number,title,state,pr_author:.author,pr_created:.createdAt,at:$e.createdAt,actor:$e.actor.login,removed:($e.requestedReviewer.login // $e.requestedReviewer.name)}' >> $out
  hasnext=$(echo "$resp" | jq -r '.data.repository.pullRequests.pageInfo.hasNextPage')
  cursor=$(echo "$resp" | jq -r '.data.repository.pullRequests.pageInfo.endCursor')
  last=$(echo "$resp" | jq -r '.data.repository.pullRequests.nodes[-1].number')
  echo "page done, last PR #$last" >&2
  [ "$hasnext" = "true" ] || break
done
