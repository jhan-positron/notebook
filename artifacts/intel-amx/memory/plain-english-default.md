---
name: plain-english-default
description: "jhan 2026-08-30: plain English ALWAYS (no switch word); rules now codified in ~/.claude/CLAUDE.md # English; applied 2026-08-30 at jhan's direction"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 528c65a4-1a65-45cc-a91c-9abf2f9fd11a
  modified: 2026-08-30T18:54:40.026Z
---

Default register for everything I write for jhan: an engineer who has never seen the project
must follow it on first read. Concretely:
1. Define every technical term, abbreviation and internal name at first use (parenthesis or a
   "words used here" list): bf16, ulp, logits, p95, rel-L2, arm, forced run, mirror, tron labels.
2. One claim per sentence, in the order test -> observation -> meaning.
3. Numbers carry units and a plain meaning ("0.125, one bf16 notch at that size").
4. Citations follow the plain sentence in brackets; they never replace it.
5. Reports and long answers open with a "Short version" (<= 3 sentences).
6. No idioms, metaphors, wordplay, uncommon words (existing rule).
No switch word: jhan removed it - plain English all the time. The full rule set now lives in
~/.claude/CLAUDE.md (# English), applied 2026-08-30; code comments follow rules 2 and 6 only.

**Why:** 2026-08-30 jhan had to ask twice for plain English on the token-30 results page; my
text obeyed the letter of the CLAUDE.md "English" rule (exact technical terms, no idioms) but
packed undefined shorthand (ulps, p95, rel-L2, label names) into dense sentences. The register
he accepted is the "Conclusions in plain English" section of definitive-decode/token30-results.html
(word list, then per conclusion: what we did / what we saw / why it settles it).
Second instance (2026-09-01): the make-sense-amx-vs-avx.html fence-caveat table CELL was dense
(written 08-31, after the rule existed) - the session had started 08-28 with the OLD CLAUDE.md
and never re-read it; a page-level glossary does not make a cell readable alone.
**How to apply:** write the plain version first; add citations after; before sending, scan for
any undefined abbreviation or internal name. Rules 1-3 apply to every unit a reader can land on
alone: a table cell, a figure caption, a commit message. In sessions that span days, re-read
~/.claude/CLAUDE.md whenever jhan says he changed it. Related: [[plain-words-comment-register]],
[[english-banned-words]].
