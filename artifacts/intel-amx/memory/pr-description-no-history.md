---
name: pr-description-no-history
description: "jhan 2026-09-30: a PR description is written as of today, present tense, no review-round or change narration (no 'since cbf1bb6c0c', 'W1 changed T5', 'first/final commit'); measurements keep only provenance (commit id + date)"
metadata:
  type: feedback
---

jhan rejected the first PR 4596 description refresh (2026-09-30): "no. Do not mention change history. Treat the PR
description is first written today. Please do it again."

**Why:** reviewers read the description to learn what the PR does now; the review history lives in the threads.
Narrating rounds ("round 4 changed T1", "the final commit", "since 1430736b2a both leaves read {}") makes the reader
reconstruct the past before understanding the present.

**How to apply:**
- Describe the head in the present tense. Define each timer, leaf, test and cost as it is.
- Measurements keep provenance only: "9b3832eb4b, 2026-09-24", "this branch at 04da001cb5". No "before/after",
  "earlier version", "superseded", "the first commit" framing.
- Obsolete data (old objdump numbers, old test counts, samples of an old leaf format) is replaced or deleted, not
  annotated as old.
- Same register as the positron-code-review skill for comments: keep the invariant, drop the history.
- Still preserve the author's own sentences when the head keeps them true (the "preserve the current" rule).
Related: [[pr4596-body-refresh-20260930]], [[pr-body-refetch-before-edit]], [[pr-item-register]].
