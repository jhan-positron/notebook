---
name: tron-pr-push-triggers-bot-review
description: "A push to a positron-ai/tron PR brings an automated claude[bot] review within about 16 minutes and code-owner team review requests; re-read the PR before posting replies, and test bot findings before acting on them"
metadata:
  node_type: memory
  type: project
  originSessionId: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6
  modified: 2026-11-24T23:53:35.628Z
---

Seen on 2026-11-20 on tron PR 5022, after the push of ddf843ad97 at 16:52 UTC:

- 16:52:26 UTC: GitHub requested reviews from the teams tron-ci, tron-ingest and tron-core. `.github/CODEOWNERS` on main owns `/h/`, `/src/`, `/t/` (tron-core), `/h/tron/models/` (tron-ingest), `README.ci.md` and the default `*` (tron-ci). The event is attributed to the pusher.
- 17:08:20 UTC: `claude[bot]` submitted a COMMENTED review of the new head with 2 inline findings (one marked red, one yellow "optional"). Its body says yellow findings "need no follow-up push".
- 16:52:57 UTC: `cursor[bot]` rewrote its PR summary comment.

The red finding was wrong. It said that Catch2 v3.7.1 exits with the count of failed assertions, so 4 failures would look like `SKIP_RETURN_CODE 4`. The pinned source says otherwise: v3.7.1 standardised the exit codes, a failed assertion always exits with 42, and 4 means only "every selected case skipped" (`catch_session.cpp:37, :39, :350-356`; release notes of 3.7.1). A mutation run on delphi-3b35 confirmed it: one broken transpose line gave exactly 4 failed assertions, exit code 42, and ctest reported Failed (`exec/results/pr5022-final-20261119/mutation-exit-code.txt`).

**Why:** the bot review arrived between the push and my posting of the replies, and it contested a change made at the human reviewer's request. Posting without looking would have left a red finding unanswered at the re-request.

**How to apply:** after a push to a tron PR, wait for CI and then list reviews and threads again before posting anything or re-requesting a review. Treat a bot finding as a claim to test (source of the pinned dependency, then a run), not as a fact. Replies to bot findings are new text: jhan's go for the prepared replies does not cover them (my reading of jhan's rule that nothing is posted without a go). The folks-code-review checks list unanswered bot findings, so answer them before the re-request.

Seen again on 2026-11-24, after the push of 90a9110be5 at 18:36 UTC (the two commits of Isaac's PR 5606):
- `claude[bot]` reviewed after 4 minutes ("Code review found no issues") and marked its own 2 threads of 2026-11-20 as resolved. So the wait is 4 to 16 minutes in two observations.
- A head commit that is also the head of another pull request carries that pull request's checks. The 12 skipped checks of draft PR 5606 showed on PR 5022 until the new run replaced them. Judge the checks by the run id, not by `gh pr checks` alone.
- GitHub marked PR 5606 as merged at the push, because its base was our branch.

Seen on 2026-11-24, after the force-push of the rebased head 187da02163 at 23:11 UTC:
- `cursor[bot]` (Cursor Bugbot) posted a review with 1 inline finding after 5 minutes. Before that date it had only rewritten its summary comment. So two bots can open threads after a push.
- The finding was correct. A commit that main gained after our branch point (#5461, 2026-11-20) added a rule to a Note, and a line of the PR contradicted it. The rebase had no text conflict. After a rebase or merge of main, read the Notes and comments that main changed in files the PR's code depends on (`git diff <old base> origin/main -- <header>`), not only the conflict list.
- A bot thread is unresolved, and main requires resolved conversations, so it blocks the merge until answered ([[tron-main-merge-queue-squash]]).

Seen on 2026-11-25, after the push of the fix e863b27272 at 01:19 UTC: `cursor[bot]` resolved its own thread within 2 minutes, without a reply from us, and `claude[bot]` reviewed after 3 minutes ("no issues"). So a bot thread may need no reply once the fix is pushed: read the thread state first.

Related: [[isaac-reviews-are-agent-pipeline]], [[tron-manual-legacy-ci-run]], [[tron-pr-post-replies-as-one-review]].
