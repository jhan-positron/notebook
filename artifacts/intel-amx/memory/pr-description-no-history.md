---
name: pr-description-no-history
description: "jhan 2026-09-30 + 2026-10-08: a PR description is written as of today, present tense, no review-round or change narration; measurements keep only provenance (commit id + date); the only meaningful perf data is the FINAL head vs the LATEST main (no previous-head, headm or between-version comparisons, no attribution subsections)"
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

Addendum (jhan, 2026-10-08, on the PR 4424 body): "They do not care the changes we have made before the final version.
In other words, the meaningful data specific to this PR is, with and without the changes of the final version of this
PR, and the base is sync'ed to latest main, what is perf diff. ... any verbose and test data describing historical
changes need to be deleted." Applied the same day: the "### TTFT difference between new and head: which change causes
it" subsection (headm comparator) was deleted, every `head` (previous PR head 30c4ac82cb) column/row/pair went, the
"Cost rows (done)" item became a present-tense Verification sentence + a genoa96 open item, "(was ...)" values and
chain-cutoff narration went. Kept with provenance: the PR #3879 table (the protected Short version cites its six
cells) and the 2026-09-16 kv_mul-8 numbers. jhan then (2026-10-08 18:13 UTC, by hand on GitHub) DELETED the
"(measure before merging)" qualifier from that item's heading: "No need to keep such noise." Never reinstate it; a
pending-measurement requirement in an open-item heading counts as noise to jhan.

**How to apply (2026-10-08):** never add a previous-head arm, a comparator binary or an attribution subsection to a PR
body; measure the final head against the latest main and report only that. If a protected section still cites older
data, keep the backing table with commit + date provenance and tell jhan the dependency.


UPDATE 2026-10-08 (reviewer agent on PR 4812, applying the wade-code-review PR-description check): in the Test section keep the date, commit ids, build settings, pass/skip results and exact test counts; remove clock times (start/end hours, time in the status line), paths into the author's workspace (scripts, results directories), and comparisons with another head's assertion counts ("192 more than the comparator"). Related: [[pr4812-merge-4774-onto-4424-head]].
