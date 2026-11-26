---
name: tron-main-merge-queue-squash
description: "positron-ai/tron main has a GitHub merge queue with merge method SQUASH (measured 2026-11-19); every PR lands as one commit, and the squash message lists the branch commit messages"
metadata:
  node_type: memory
  type: reference
  originSessionId: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6
  modified: 2026-11-25T17:55:23.916Z
---

Measured 2026-11-19 with the GitHub API: `positron-ai/tron` main has a merge queue (https://github.com/positron-ai/tron/queue/main) whose merge method is SQUASH. Since 2026-10-27 all 143 pull requests merged into main landed as one commit. Before that merge commits were normal: 40 of the 41 pull requests merged from 2026-10-19 to 2026-10-26 were merge commits, the last one on 2026-10-26 19:53 UTC. The repository settings still list merge commits and rebase merges as allowed.

The queue writes the squashed commit's message: the PR title with `(#N)`, then every branch commit message as a `*` list (seen on #5429, #5003, #5423).

jhan's own PRs into main (#4557, #4596, #4505, #3879) were merge commits, all before the queue. #5098 merged into the branch `bgamari/vnnik-1`, not into main.

Merge gate on main, measured 2026-11-24 for PR 5022 (GraphQL `pullRequest.baseRef.refUpdateRule`; the REST protection endpoint needs admin rights):
- 1 approving review, no code-owner requirement, and every review conversation must be resolved (`requiresConversationResolution: true`). One unresolved thread gives `mergeStateStatus: BLOCKED` although `reviewDecision` is APPROVED.
- 12 required checks: Build Tron, Build ingest, Build model traces, Generate model plugins, Fresh Cabal plan, Test, Test FPGA, Test host, Test ingest, CI machinery tests, Lint, deb-smoke-tests.
- A push does not dismiss an approval. In 40 merged PRs sampled, 0 had a `review_dismissed` event, and many were force-pushed after the approval and then queued. PR 5022 kept its approval after a force-push.
- The queue strategy is ALLGREEN and it builds the PR on current main, so a branch behind main can be queued without a rebase. jhan asked for a rebase anyway on 2026-11-24 ("If head is ahead of us, please rebase and merge").

How to put a PR in the queue, measured 2026-11-25 for PR 5022:
- `gh pr merge 5022 --squash --match-head-commit <sha>` failed with "GraphQL: Auto merge is not allowed for this repository (enablePullRequestAutoMerge)". The PR read CLEAN 16 s before and 7 s after that call. gh may have read a transient state right after I withdrew a review request (not verified).
- The GraphQL mutation worked at once: `enqueuePullRequest(input:{pullRequestId:<PR node id>, expectedHeadOid:<sha>})`. It returns the queue entry (state QUEUED and the position). Use it directly.
- Wait in the queue: PR 5022 entered at 17:55:02 UTC at position 2 and merged at 18:33:41 UTC (38 min 39 s). The queue runs GCP Nix, Nix build validation and Debian smoke on a branch `gh-readonly-queue/main/pr-N-<base sha>`. The commit it tests becomes the commit on main, with the same id.
- To withdraw one review request without text: `gh api -X DELETE repos/positron-ai/tron/pulls/N/requested_reviewers -f 'reviewers[]=<login>'`. The reviewer's earlier approval stays, and `reviewDecision` stays APPROVED.

**Why:** jhan asked on 2026-11-19 what confusion would follow from ignoring Isaac's commit-shape comments on PR 5022. Answer: none on main, because the queue squashes.

**How to apply:** Do not recommend reshaping or rebasing a branch for the sake of main's history. Do say that branch commit messages end up in the squashed commit's body, so review-round titles ("Apply accepted review changes") show there. Re-check before relying on it: `gh api graphql -f query='query{repository(owner:"positron-ai",name:"tron"){mergeQueue(branch:"main"){configuration{mergeMethod}}}}'`. Related: [[isaac-reviews-are-agent-pipeline]].
