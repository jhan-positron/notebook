**Short version:** Passages 2, 4, 5, 6, 7 and 10 are rewritten. Passages 1, 3, 8 and 9 already follow the rules and are unchanged. Passage 9 lacks a load figure, and a rewrite cannot supply one.

**Passage 1**

The cache reduces repeated reads, it uses more memory, and it needs explicit invalidation.

**Passage 2**

- The cache avoids repeated reads when requests reuse the same records.
- It retains those records in memory until eviction. So memory use grows with the retained data.
- Writers must invalidate changed records before later requests read them. Otherwise, those requests may receive stale values.

**Passage 3**

Check the lease, start the run, then save the log.

**Passage 4**

The reader starts before initialization finishes, so it can observe an empty queue. This is why the test sometimes fails.

**Passage 5**

The total changes with the number of lines:

- above about 30 lines: 230 to 310 GB/s
- 12 to 28 lines: 459 to 480 GB/s
- 8 to 12 lines: 543.9 to 549.0 GB/s (the highest measured)

The rule inside the core that causes this is not established.

**Passage 6**

Then I do these steps in order:

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

The old diagram, its caption and its drawing script are deleted from the page crb-memory-hierarchy.html. The page was not rendered, because this machine has no browser. I checked only that the old diagram is gone and that the new diagram is still connected to its data.

## What changed

| Passage | Rule | Original phrase | Fix |
|---|---|---|---|
| 2 | 4 | "The cache avoids repeated reads when", 3 sentences | Three aspects of one thing became three bullets. |
| 4 | 3 | "Because the reader, which starts before", 17 words | A clause sat inside another clause. It became two sentences. |
| 5 | 3 | "The total is 230 to 310", 45 words | The values became a list. The last claim became its own sentence. |
| 6 | 3 | "Then I fill the run ids", 35 words | The five actions became a numbered list. |
| 6 | 8 | "PR" | Defined as "pull request". |
| 7 | 3 | "Parts A, B and C are", 26 words | Split at ", and". The Part D parenthesis became its own sentence. |
| 10 | 1 | "wired in" | Replaced with "connected to". |
| 10 | 8 | "crb-memory-hierarchy.html" | Named as "the page" at first use. |
| 10 | 8 | "the old figure" | Changed to "the old diagram". I assumed both words name one thing. |

## Why four passages are unchanged

- Passages 1 and 3 are the skill's own examples of sentences to keep.
- Passage 8 has 12 words and two short clauses, so it stays whole.
- Passage 9 has 10 words and one subject, so it stays whole.

## Open points

- Passage 9 states the core count but not the load. "Nearly idle" needs the measured load next to the core count.
- Insufficient data to define "lines" (passage 5), "#5021" (passage 6), and "lease" and "campaign" (passage 8). The source documents would give the meanings.
- Word counts are hand counts. This session had no tool to run the skill's length script.
- My count for the original passage 7 is 26 words. The skill text says 27.