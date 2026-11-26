**Short version:** All 10 passages are rewritten below. Passage 9 needs a load figure that the original does not give, and I marked the gap with a placeholder. The source does not define several project terms (listed at the end), and I left them undefined.

**Passage 1**

The cache reduces repeated reads. It uses more memory. It needs explicit invalidation (a writer must mark a changed record as no longer valid).

**Passage 2**

The cache avoids repeated reads when requests reuse the same records. It keeps those records in memory until it evicts (removes) them. So memory use grows with the amount of data it keeps.

Writers must invalidate a changed record (mark the cached copy as no longer valid) before a later request reads it. Otherwise the later request may receive an outdated value.

**Passage 3**

Do these steps in order:

1. Check the lease.
2. Start the run.
3. Save the log.

**Passage 4**

The reader starts before initialization finishes. So the reader can see an empty queue. This causes the test to fail on some runs.

**Passage 5**

The total depends on the number of lines:

| Lines | Total in GB/s (gigabytes per second) |
|---|---|
| Above about 30 | 230 to 310 |
| 12 to 28 | 459 to 480 |
| 8 to 12 | 543.9 to 549.0 (the highest measured) |

The rule inside the core that causes these differences has not been identified.

**Passage 6**

Then I do these steps in order:

1. Fill the run IDs into the description and the replies.
2. Edit the PR (pull request) description.
3. Post the 26 thread replies and the combined reply as one review.
4. Comment on #5021.
5. Re-request the review.

**Passage 7**

Parts A, B and C are complete on CRB (the Arm server under test). Part D (the steps that need administrator rights) was not run.

**Passage 8**

Another campaign held the lease. So the test was skipped.

**Passage 9**

The host has 64 physical cores. The measured load was [load value missing from the original]. So the host was nearly idle.

**Passage 10**

The old diagram, its caption and its drawing script are deleted from crb-memory-hierarchy.html (the page that held them). This machine has no browser. So the page was not rendered.

I checked only two things:

- The old diagram is gone.
- The new diagram's data is still connected to the new diagram.

**Gaps I could not close from the source**

- **Passage 9:** The core count alone does not show that the host was idle. The sentence needs the measured load.
- **Passages 3 and 8:** "lease" and "campaign" are project terms with no definition in the source.
- **Passage 5:** "the total", "lines" and "the core" are not defined in the source.
- **Passage 5:** The value 12 lines appears in two ranges, and no range covers 28 to 30 lines. I kept the ranges as written.
- **Passage 6:** The source does not say whether #5021 is an issue or a pull request.