---
name: tron-pr-post-replies-as-one-review
description: "How to post many review-thread replies on a GitHub PR at once: one pending review via GraphQL, read back, then submit; tools in muse-glimmer/pr5022-post/"
metadata:
  node_type: memory
  type: reference
  originSessionId: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6
  modified: 2026-11-20T17:56:22.086Z
---

Used on 2026-11-20 for positron-ai/tron PR 5022 (26 thread replies and one combined reply, review 5997064669).

Method (GraphQL through `gh api graphql --input -`, a JSON object with `query` and `variables` on stdin):

1. Map each review thread to its first comment: `pullRequest.reviewThreads.nodes { id comments(first:1) { nodes { databaseId } } }`. The `discussion_rN` number of a comment link is that `databaseId`.
2. `addPullRequestReview(input: {pullRequestId, commitOID})` without `event` creates a PENDING review. Only its author sees it.
3. `addPullRequestReviewThreadReply(input: {pullRequestReviewId, pullRequestReviewThreadId, body})` once per thread.
4. Read the pending review back (`node(id) { ... on PullRequestReview { comments { nodes { body replyTo { databaseId } } } } }`) and compare each body with the text sent.
5. `submitPullRequestReview(input: {pullRequestReviewId, event: COMMENT, body})`. The body carries the reply to the review body. On any failure before this step: `deletePullRequestReview`, and nothing was visible.

Why this and not 27 REST calls: the reviewer gets one notification, and a failure in the middle leaves no half-posted set.

Checks that paid off before posting (scripts in `~/workspace/intel-AMX/muse-glimmer/pr5022-post/`, README there):
- every quoted code line compared with the pushed head (`check_quotes.py`), and stated "now at line N" numbers compared with the pushed head (`locate_blocks.py`): 5 of 26 replies carried line numbers of the reviewed commit;
- markup hazards outside code (`md_hazards.py`) and a render through `gh api markdown` (`render_check.py`);
- a fresh count of threads right before posting. The script stopped once because an automated review had added 2 threads, see [[tron-pr-push-triggers-bot-review]].

GitHub facts met on the way: a newline inside a paragraph of an issue or comment renders as a line break, so unwrap paragraphs; `gh api .../jobs/<id>/logs` refuses output with escape sequences unless `--allow-escape-sequences` is passed, `gh run view <run> --job <id> --log` works for a finished run; `gh api --jq` has no `--arg`.

A single reply to a conversation comment (2026-11-24, comment 7142046348): `POST repos/positron-ai/tron/issues/<n>/comments` with a JSON body on stdin, then `GET .../issues/comments/<id>` and compare. The script `muse-glimmer/round2-tools/post_after_go.py` also saves the PR description (`PATCH .../pulls/<n>`) with checks before and a read-back after. The description text from `--jq .body` carries one extra newline at the end: strip exactly one before sending.

Review request after the reply (jhan, 2026-11-24: "please update PR5022 and request Issac to review at the PR"). jhan expects a fresh review request once the push, CI and the reply are done, so plan it as a step and ask for it in the same go. `POST .../pulls/<n>/requested_reviewers` changes nothing for a reviewer who is still on the requested list: no timeline event appears. A fresh request needs `DELETE` and then `POST` with the same body. Check the `review_requested` event in `.../issues/<n>/timeline`. The remove-and-add step was my choice of means, and jhan had not commented on it when this was written.

Related: [[review-replies-keep-simple]], [[review-reply-edits-as-diffs]], [[isaac-reviews-are-agent-pipeline]].
