**Short version:** Six passages changed, and four stay as written (1, 3, 8 and 9). Each of those four is one short sentence with simple clauses. The notes at the end list gaps that the text alone cannot fill.

**Passage 1**

The cache reduces repeated reads, it uses more memory, and it needs explicit invalidation.

**Passage 2**

- The cache avoids repeated reads when requests reuse the same records.
- It retains those records in memory until eviction. So memory use grows with the retained data.
- Writers must invalidate changed records before later requests read them. Otherwise, those requests may receive stale values.

**Passage 3**

Check the lease, start the run, then save the log.

**Passage 4**

The reader starts before initialization finishes, so it can observe an empty queue. This makes the test fail sometimes.

**Passage 5**

The total depends on the number of lines:

- above about 30 lines: 230 to 310 GB/s
- 12 to 28 lines: 459 to 480 GB/s
- 8 to 12 lines: 543.9 to 549.0 GB/s (the highest measured)

It is not established which rule inside the core causes this.

**Passage 6**

Then I do these steps:

1. Fill the run ids into the description and the replies.
2. Edit the PR (pull request) description.
3. Post the 26 thread replies and the combined reply as one review.
4. Comment on #5021.
5. Re-request the review.

**Passage 7**

Parts A, B and C are complete on CRB (the Arm server under test). Part D was not run. It holds the steps that need administrator rights.

**Passage 8**

The test was skipped, because the lease was held by another campaign.

**Passage 9**

The host has 64 physical cores, so it was nearly idle.

**Passage 10**

The old diagram, its caption and its drawing script are deleted from the page crb-memory-hierarchy.html. The page was not rendered, because this machine has no browser. I checked only that the old diagram is gone and that the page still references the new diagram's data.

**Notes**

- Passage 9 states a conclusion that the core count alone does not support. The sentence needs the measured system load next to the 64 cores. I did not invent a number.
- Passage 10: I read "wired in" as "the page still references the data". I also changed "old figure" to "old diagram", so one thing has one name.
- The supplied text does not define these terms, so I added no definitions:
  - passage 5: "lines" and "the core"
  - passage 6: "#5021"
  - passages 3 and 8: "lease" and "campaign"