#!/usr/bin/env bash
# Review-thread helper for the PR 4812 review loop (runs on claude-box, needs gh auth).
#   bash pr-threads.sh list [PR]                 -> JSON: every review thread (id, resolved, outdated, path, line, comments)
#   bash pr-threads.sh open [PR]                 -> the unresolved threads only, readable text
#   bash pr-threads.sh reviews [PR]              -> review bodies (state, author, body) and issue comments
#   bash pr-threads.sh reply <comment_db_id> <body-file> [PR]   -> reply inside the thread of that review comment
#   bash pr-threads.sh resolve <thread_node_id>  -> mark the thread resolved
set -u
OWNER=positron-ai; REPO=tron
cmd=${1:?list|open|reviews|reply|resolve}; shift
Q='query($owner:String!,$repo:String!,$pr:Int!){ repository(owner:$owner,name:$repo){ pullRequest(number:$pr){ headRefOid reviewThreads(first:100){ nodes{ id isResolved isOutdated path line startLine diffSide comments(first:50){ nodes{ id databaseId author{login} body createdAt url } } } } } } }'
case $cmd in
  list) PR=${1:-4812}; gh api graphql -f query="$Q" -F owner=$OWNER -F repo=$REPO -F pr="$PR" --jq '.data.repository.pullRequest' ;;
  open) PR=${1:-4812}; gh api graphql -f query="$Q" -F owner=$OWNER -F repo=$REPO -F pr="$PR" --jq '.data.repository.pullRequest | "head \(.headRefOid)", (.reviewThreads.nodes[] | select(.isResolved|not) | "=== thread \(.id) \(.path):\(.line // "-") outdated=\(.isOutdated)", (.comments.nodes[] | "--- comment \(.databaseId) by \(.author.login) at \(.createdAt)\n\(.body)\n"))' ;;
  reviews) PR=${1:-4812}; echo "=== reviews"; gh api "repos/$OWNER/$REPO/pulls/$PR/reviews" --jq '.[] | "--- review \(.id) \(.state) by \(.user.login) at \(.submitted_at)\n\(.body)\n"'; echo "=== issue comments"; gh api "repos/$OWNER/$REPO/issues/$PR/comments" --jq '.[] | "--- comment \(.id) by \(.user.login) at \(.created_at)\n\(.body)\n"' ;;
  reply) cid=${1:?comment db id}; f=${2:?body file}; PR=${3:-4812}; gh api -X POST "repos/$OWNER/$REPO/pulls/$PR/comments/$cid/replies" -F body=@"$f" --jq '"replied: \(.html_url)"' ;;
  resolve) tid=${1:?thread node id}; gh api graphql -f query='mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){ thread{ id isResolved } } }' -F id="$tid" --jq '.data.resolveReviewThread.thread' ;;
  *) echo "unknown command $cmd"; exit 2 ;;
esac
