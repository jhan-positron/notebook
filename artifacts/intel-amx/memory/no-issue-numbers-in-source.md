---
name: no-issue-numbers-in-source
description: "jhan 2026-10-18 (PR 5015 thread r4308443563): issue numbers must not appear in source code comments; a header sentence that only renames the mismatch is 'too nit picking'"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 146c3a6e-a1e1-402b-a412-2cd6ec96fdfc
  modified: 2026-10-18T23:51:53.808Z
---

jhan, PR 5015 review thread r4308443563 (2026-10-18): "Issue# should not appear in source code. And this is too nit picking."
The rejected proposal replaced the amx_attn_iface.hpp header clause "and are kept" with "Issue #5021 tracks the rename."

**Why:** an issue number in a comment goes stale when the issue closes and sends the reader out of the tree; the
tracking belongs in the PR body or the issue itself. A one-clause wording change in a file header is below the bar
for a review comment.

**How to apply:** when proposing or writing a code comment, never cite a GitHub issue or PR number; describe the
lasting design fact instead. Keep wording-only header nits out of reviews unless the sentence is wrong.
Related: [[pr5015-multi-skill-review]], [[deleted-comments-stay-deleted]], [[no-names-in-github-issues]].


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): jhan 2026-10-18: never cite an issue/PR number in a code comment; header wording-only nits are too nit picking
