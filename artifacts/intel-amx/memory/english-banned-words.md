---
name: english-banned-words
description: "User's banned-word list for my writing - convoy, refund, \"in disguise\", swept"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3a96feab-43b5-493a-97f2-e9a59a459e74
  modified: 2026-08-18T18:39:13.919Z
---

Do NOT use these words/phrases in any writing (docs, chat, commit messages, reports):
- convoy
- refund
- "in disguise"
- swept (and by extension prefer plain alternatives to "sweep" as jargon; keep it only
  when quoting file names, code identifiers, or product specs)

Exception: allowed only when they literally appear in software source code or a product
spec being quoted.

**Why:** extends the user's global no-idioms/plain-English rule (CLAUDE.md). "In disguise"
and "swept" were flagged in the AMX doc reviews (2026-08-18) as not understandable;
replacements used: "in disguise" -> "written as X, but the math it computes is Y";
"swept" -> "measured across every combination of settings (widths x residencies)".

**How to apply:** scan deliverable text for these words before finishing; replace with
plain descriptions of the concrete action or mechanism. Related: [[amx-tron-softattn-project]]
docs follow the same plain-English conventions (glossary + terminology sections).

- "young positions" (2026-08-19): NOT a standard LLM term - my invention, jhan flagged it.
  Use "queries at positions below 127" or "early-position queries" and note it is an FPGA
  constraint. Removed from pr-rampup.html and gptoss-estimate.html.
