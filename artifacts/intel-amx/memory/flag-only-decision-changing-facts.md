---
name: flag-only-decision-changing-facts
description: "jhan 2026-10-08: never promote a trivial fact (a small delta marked inside the noise band, a wording consequence) to a headline callout in a reply; a callout is only for a fact that changes a decision"
metadata:
  type: feedback
---

On 2026-10-08, after the PR 4424 body purge, my summary carried a bold section "One change of meaning you should
know about" with a table, saying the -57 ms TTFT delta at prompt 1024 is inside the 0.15 s noise band. jhan: "I do
not see why you want to prompt me, there is nothing significant here ... -56 ms is within noise range, that is all
you want me to be aware of? It is such trival fact, waste my attention".

**Why:** jhan reads the reply to decide what to do next. A headline callout promises a decision-relevant change. A
noise mark on a delta that was already small, in a table they can read themselves, is not one.

**How to apply:** before giving a fact its own section, table or bold label in a reply, ask: does it change what
jhan decides or does? If not, it is at most one clause in a sentence, or nothing. Band marks, rounding, re-labelled
cells and other presentation consequences of an edit belong in the diff, not in the summary. Related:
[[plain-english-default]], [[pr-description-no-history]].
