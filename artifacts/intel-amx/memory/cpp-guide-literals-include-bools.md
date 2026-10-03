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

UPDATE 2026-10-02 (jhan, PR #4737): "Remove BIT_1, directly use literal 1". A literal `1` inside a bit helper
(`uint8_t(1u << c)`, `uint64_t{1} << offset`) and in "mask minus one" arithmetic stays a literal; naming it adds no
meaning. Keep one helper per mask kind (k_vnni::block_bit / offset_bit) so the spelling exists once. This is an
EXPLICIT exception jhan granted, not a working interpretation: still list it in the chat summary when applied.
Also: jhan prefers a constant name that says what the value IS over one that names a set
(BLOCKS_PER_PAGE_MASK_0XF, not ALL_BLOCKS_0XF; FULL_BLOCK_0XFFFF-style "full page" was offered and not chosen).
UPDATE 2026-10-02 (jhan, PR #4737, second exception): `return true;` in the row-major branch of the layout gate
(`if constexpr` else-branch that always passes) stays a literal; a named ROW_MAJOR_DENSE_TRUE was asked to be reverted.
Reading of both exceptions: a literal whose only meaning is "the trivial value of this expression" (a shift's 1, a
subtraction's 1, a gate that is always open) is not named; a literal that encodes a choice or a flag (view aligned/dma,
support_eagle, repeat, record_rows, converted) is named. Confirm with jhan before extending this reading to new cases.
