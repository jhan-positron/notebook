---
name: crb-label-loads-slash-stores
description: In CRB documents the core limit is written "3 loads / 2 stores of 16 B per cycle", not "3 loads + 2 stores"; the user decided this on 2026-11-12
metadata:
  type: project
---

The user (Jibin) asked on 2026-11-12 to change every "3 loads + 2 stores" in `crb/crb-memory-hierarchy.html` to "3 loads / 2 stores" (six places: figure box, source-table row, a reference to that row, section heading, contents entry, one sentence).

**Why:** the two numbers are separate limits of the core. A plus sign reads as five operations in one cycle. The user called the sentence that explains this "great clarification".

**How to apply:** write "3 loads / 2 stores" for the label in any new CRB text. Keep the plus sign only for a real mix of one cycle, such as "3 loads + 1 store" or "2 loads + 2 stores". Related: [[crb-term-slc-not-mesh-cache]].
