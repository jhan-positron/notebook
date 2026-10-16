---
name: plain-words-comment-register
description: "jhan wants dense source comments explained with a two-column 'the comment says | in plain words' table, and the comment itself rewritten in that plain-words register (2026-08-27, R1-10)"
metadata:
  type: feedback
---

On 2026-08-27 jhan praised the "Sentence by sentence" table under R1-10 in PR3879/alexey-review.html (left column =
the comment's sentence verbatim, right column = the same fact in plain words; followed by a glossary) - "its English
intuits every person" - and asked that the source Note be rewritten using it, then pushed (tron 7aae13df5).

**Why:** a comment that needs a translation table is too dense; the plain-words column IS the better comment. The
table also exposes hidden generalizations (one row per sentence forces each claim to be checked on its own).

**How to apply:** when jhan calls a comment dense, produce the two-column table first (generator hook EXPLAIN in
exec/review-pipeline/gen_review6.py, text in r6/explain_<id>.md); when asked to fix the comment, write it in the
right-hand column's register: name the mechanism ("has no 'store only 4 rows' mode"), say what goes wrong concretely
("rows 4..15 are written past its end, nothing reports an error"), gloss ISA terms once ("its left-hand input (the A
operand)"), keep source identifiers exact, no test-file references in headers. Still run a fact-check panel: plain
rewording tends to re-generalize (see [[reviewer-personas]] round-6d). Length is acceptable (7 -> 20 lines) when
every sentence carries a distinct fact. Related: [[english-banned-words]], [[review-body-format]].
