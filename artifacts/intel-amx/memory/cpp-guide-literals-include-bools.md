---
name: cpp-guide-literals-include-bools
description: "jhan's cpp-coding-guide named-value rule covers every literal, incl. true/false and 0/1; pass the guide verbatim to sub-agents, no invented exemptions, list every class left unfixed"
metadata:
  node_type: memory
  type: feedback
  originSessionId: d9f8fa2b-f112-45c9-945e-1ec86934aa71
  modified: 2026-09-23T18:00:22.825Z
---

The named-value rule of ~/.claude/skills/cpp-coding-guide ("Keep literal values in these
declarations") covers every C++ literal on the lines in scope: boolean `true`/`false` (for example
the aligned/dma flags in `view<bf16, true, false, ...>`), 0 and 1, and numbers "without domain
meaning". jhan, 2026-09-23 ~18:00 UTC, on PR #4557: "true and false should have been replaced by
variables. How come they got missed?"

**Why:** the 2026-09-23 06:00 UTC guide-check workflow (wf_04bd86f9-b06, script
guide-checks-pr4557-wf_04bd86f9-b06.js line 12) gave the finders a "working interpretation" that
narrowed the rule to "literals with domain meaning", with numeric examples only and 0/1 exempt.
The test-file finder then exempted the flags as "Boolean flags, not numeric values, and the
codebase-wide spelling". The full.hpp finder never flagged them and its own replacement text
re-typed them. Refuters only check reported findings, so nothing looked for misses. The summary
to jhan listed sseq<1>, #if, zeros, tile indices and predicates, but not booleans. Commit
1c87d66926 rewrote two lines and kept bare `true, false`. The 28 lines (39 boolean literals)
were fixed in commit 5051264d80 (2026-09-23 18:38 UTC). jhan then added to the skill: "Literal
values include true, false, 0 and 1. List any exception instead of applying it silently."

**How to apply:**
- Hand the guide to sub-agents verbatim. Do not add exemptions. A doubtful class becomes a
  question for jhan, not a working rule.
- Add a mechanical completeness pass: list every literal token on the + lines (numeric, bool,
  char, string, nullptr) and mark each one fixed or listed.
- The chat summary names every literal class left unfixed, with a count.
- A conflict with the repo idiom (bare view flags, sseq<1> on main) is surfaced per the global
  Rule 7, never resolved silently toward the repo.

Related: [[issue4525-implementation]].
