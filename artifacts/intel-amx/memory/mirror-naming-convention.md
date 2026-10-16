---
name: mirror-naming-convention
description: "'mirror' = formulation from Bill's PR #2934; implementation/numbers are OURS - always add the lineage note in HTML docs"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3a96feab-43b5-493a-97f2-e9a59a459e74
  modified: 2026-08-19T01:31:17.637Z
---

In the [[amx-tron-softattn-project]], the user asked whether "mirror build" means Bill's PR
build and requested a blanket rename to "Bill's PR". It does NOT: "mirror" names the
FORMULATION (S = Q.K^T read from a second, VNNI-interleaved K copy), which originates from
Bill's PR #2934; every mirror implementation and measurement from increment 2 onward is ours
(worktree jhan-amx-p0). Bill's PR tree predates the qwen plugin and cannot run qwen at all.

**Why:** a literal rename would attribute our measured numbers to code that cannot produce
them, and would corrupt quoted identifiers (TRON_AMX_K_MIRROR, qk_mirror_128x4, k_vnni).
User accepted the recommended alternative (2026-08-19).

**How to apply:** keep "mirror" as the technical term; in every HTML doc that discusses our
mirror work, include a first-use lineage note: "the mirror formulation originates from
Bill's PR #2934; the implementation and all numbers here are ours (jhan-amx-p0)". Doc 03 and
p0-night1.html discuss Bill's actual PoC/tree - their "mirror" references are correctly his.

**"Canonical-K" (added 2026-08-19):** also project shorthand, not a standard term. Means: K
kept in today's original single-copy storage, read as-is. Defined in doc 02 glossary + doc 04
naming note. When it appears in a new doc, gloss it in plain English at first use ("K in
today's original single-copy storage") - the user flagged it as unclear.
