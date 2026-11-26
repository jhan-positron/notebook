---
name: review-reply-edits-as-diffs
description: "jhan 2026-11-19 - a reply draft that proposes a code edit must show a before/after diff with line numbers and say why its lines differ from the review comment's anchor line"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6
  modified: 2026-11-20T01:41:43.857Z
---

jhan, 2026-11-19, on the I6 card of `respond-2-Isaac.html` (PR 5022): "your writing at I6 looked wrong to me, your proposed edit is at 1795-1803 lines, but his comment was about line 1788. And your proposed code do not read relevant to this particular comment."

The edit was correct. The draft showed only the new code, said "Proposed edit at lines 1795-1803", and did not quote the reviewer's words "Just below this call".

**Why:** the reviewer's comment was attached to line 1788 (the nearest changed line) and was about unchanged code at lines 1795-1797. Without the quote and a before/after view, the draft read as unrelated to the comment.

**How to apply (my reading of the correction):** in a reply draft that proposes a code change,
- show the change as a diff against the reviewed commit, with line numbers, built from the real source lines;
- quote the reviewer's own words that name the target;
- when the comment's anchor line differs from the edited lines, say so and say why.

Related: [[isaac-reviews-are-agent-pipeline]].
