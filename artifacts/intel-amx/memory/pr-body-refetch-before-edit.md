---
name: pr-body-refetch-before-edit
description: "2026-09-25: gh pr edit --body-file from the local pr-body.md OVERWROTE jhan's own GitHub edit of the PR 4596 description (their 22:11:19Z edit, my 22:13:14Z write); always re-fetch the live body right before an edit and diff it against the last fetched copy; recovery = GraphQL userContentEdits(last:N){nodes{editedAt diff}} where diff holds the FULL body text of each version"
metadata:
  type: feedback
---

jhan edits PR descriptions on GitHub by hand between my writes. On 2026-09-25 my second `gh pr edit 4596 --body-file`
(22:13:14Z) replaced the body jhan had edited two minutes earlier (22:11:19Z); I had diffed my candidate only against a
copy fetched hours before. jhan: "you seemed overwrote my PR description edit, please retrieve the version of my edit".

**Why:** the local pr-body.md is not the source of truth once jhan has touched the body; a stale-base write silently drops
their changes.

**How to apply:**
- Immediately before every `gh pr edit --body-file`: `gh pr view N --json body -q .body > live.md`, diff live.md against the
  last copy I fetched; if it differs, jhan edited it -> apply my change ONTO live.md (patch), never replace it.
- Recovery when it already happened: `gh api graphql` on repository.pullRequest(number).userContentEdits(last:20) {nodes
  {editedAt editor{login} diff}}: `diff` is the full body text after that edit (verified: the latest entry equals the live
  body); every entry shows editor = jhan-positron even for my gh writes, so identify mine by timestamp.
- Deliverables jhan asked for: ~/tmp/pr-desc.md (their version) and ~/tmp/update.md (my change as a unified diff against
  the version before their edit), so they can merge by hand. Do not rewrite the live body afterwards unless asked.
Related: [[attn-stats-pr-implementation]], [[pr4424-description-on-github]].
