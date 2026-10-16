---
name: pr-body-pending-measurement-subsection
description: "jhan 2026-10-08: a pending or attribution measurement in a PR body gets its own (sub)section (question, comparator, cells, verdict rule, status, result table), not a sentence inside another section"
metadata:
  type: feedback
---

jhan, 2026-10-08, on the PR 4424 body sentence "A comparator binary without the typed port is built; its
cells ... run after the nightly. I'll update the PR body with those rows": "have a dedicated (sub) section
for this". Applied as "### TTFT difference between `new` and `head`: which change causes it (running)"
under Verification: the observation, the hypothesis, the comparator binary, the cells, the verdict rule,
the status, and a table to fill.

**Why:** a reader looks for the open question and its answer in one place; a sentence inside the
performance paragraph is lost, and the result rows would have nowhere to go.

**How to apply:** whenever a PR body (or report) carries a measurement that is still running or that
attributes a difference, give it a subsection with those six parts; fill the table in place when the
result lands. Related: [[sync-4424-main-20261007]], [[pr-description-no-history]].
