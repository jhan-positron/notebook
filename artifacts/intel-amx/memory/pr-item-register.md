---
name: pr-item-register
description: jhan 2026-09-16 on PR 4424 open items: write PR text at the mechanism level from the start (which job runs which command with which flags, what each path measures, what is NOT affected, the precedent), in plain English; "I wish it was like that the first version"
metadata:
  type: feedback
---

When I unpacked the "Benchmark artifact (reviewer decision)" item of PR 4424 into a
mechanism-level paragraph (which job compiles what with which flags, what the hand-over
path and the fallback path each measure, that default CI is not affected, the
TRON_PAGE_SHARE_COUNTERS precedent), jhan wrote: "This is beautiful, I wish it was like
that the first version. Please replace."

**Why:** the first version named the mechanism only by shorthand ("bundles its
gen/runtron as the benchmark artifact", "rebuilds locally", "that mix") and left out
what was unaffected and the precedent, so a reviewer had to reconstruct the CI flow.

**How to apply:** for every PR description item, open item or review reply: verify the
flow in the CI files first, then write it as a chain of plain sentences: actor (job,
script) -> action (command, flags) -> consequence (what is measured or built), then the
boundary (what is not affected) and the precedent. Name the decision owner in the
heading ("reviewers decide"). Do this before posting, not after a follow-up question.
Related: [[plain-words-comment-register]], [[plain-english-default]],
[[pr4424-description-on-github]].
