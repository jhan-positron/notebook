**Short version:** Six passages changed, and four stay as written (1, 3, 8 and 9). Passages 2, 5 and 6 became lists, and passages 4, 7 and 10 were split or reworded. Passage 9 lacks the measured load, and I did not invent one.

**Passage 1** (unchanged)

The cache reduces repeated reads, it uses more memory, and it needs explicit invalidation.

**Passage 2**

- The cache avoids repeated reads when requests reuse the same records.
- It retains those records in memory until eviction. So memory use grows with the retained data.
- Writers must invalidate changed records before later requests read them. Otherwise, those requests may receive stale values.

**Passage 3** (unchanged)

Check the lease, start the run, then save the log.

**Passage 4**

The reader starts before initialization finishes, so it can observe an empty queue. This is why the test sometimes fails.

**Passage 5**

The total has three ranges:

- above about 30 lines: 230 to 310 GB/s
- 12 to 28 lines: 459 to 480 GB/s
- 8 to 12 lines: 543.9 to 549.0 GB/s (the highest measured)

It is not established which rule inside the core causes this.

**Passage 6**

Then I do these steps in order:

1. Fill the run ids into the description and the replies.
2. Edit the PR (pull request) description.
3. Post the 26 thread replies and the combined reply as one review.
4. Comment on #5021.
5. Re-request the review.

**Passage 7**

Parts A, B and C are complete on CRB (the Arm server under test). Part D was not run. It holds the steps that need administrator rights.

**Passage 8** (unchanged)

The test was skipped, because the lease was held by another campaign.

**Passage 9** (unchanged)

The host has 64 physical cores, so it was nearly idle.

**Passage 10**

The old diagram, its caption and its drawing script are deleted from the page crb-memory-hierarchy.html. The page was not rendered, because this machine has no browser. I checked only that the old figure is gone and that the new diagram's data is still connected.

**Notes**

- Passages 1, 3 and 8 are short sentences with short, simple clauses. The experimental rules keep such sentences whole.
- Passage 9 stays whole for the same reason, but its reason is incomplete. A core count alone does not show that the host was nearly idle. The sentence needs the measured system load, and I did not invent one.
- In passage 5, the last sentence was reordered so that no clause sits inside another clause.
- In passage 10, "wired in" is an idiom, so it became "connected". If the check was more specific, state the exact check instead.
- Some terms have no definition, because the passages do not give one: "lease", "campaign", "the total", "lines", "the core" and "#5021". Add a definition clause at first use in the real document.