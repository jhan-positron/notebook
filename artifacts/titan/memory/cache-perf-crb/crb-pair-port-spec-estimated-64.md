---
name: crb-pair-port-spec-estimated-64
description: "User decisions of 2026-11-12 on the CRB report - the pair-port Spec box says \"estimated 64 GB/s\", and the three older statements on the pair port, DRAM traffic and the single-writer limit are replaced by measured rates plus named hypotheses"
metadata:
  node_type: memory
  type: project
  originSessionId: 6eb09a16-5942-4cc5-8ed0-249c7d5ab696
  modified: 2026-11-13T01:02:28.332Z
---

On 2026-11-12 the user decided two open points of the CRB report `crb/crb-memory-hierarchy.html` (D1 and D2 of the update record `~/tmp/update-crb-memory-hierarchy.md`):

1. The Spec box of the pair port in the first figure says "estimated 64 GB/s" (two text lines in the 76-unit box: "estimated" and "64 GB/s"). I had recommended to keep "unknown". The user chose the number and asked for the explanation in the section "Where each number in the figure comes from". The explanation stands under the source table (report line 121).
2. The texts P1 to P3 of record section 10.6 were applied (report lines 214, 289, 380). They give measured rates first and name the causes as hypotheses 1 and 2 of "Open items".

**Why:** the user first asked "we measured 80 GB/s, but your hypothesis calculation is 64 GB/s, that does not look right". The answer that the user accepted: the two numbers are counted at two places. About 78 GB/s is every byte that two partner cores read at their loops (8 MiB each, lines from their own L2 included). 64 GB/s is 32 B per data flit x 2.0 GHz mesh clock for the bytes that cross the port in one direction (hypothesis 1, not confirmed).

**How to apply:** do not turn the label back to "unknown", and do not recommend that again. In any new text about the pair port, say where a rate is counted (at the loops or at the port), mark the converted values "est.", and keep three statements apart: capacity (hypothesis 1), saturation (hypothesis 2) and the conversion. A sentence such as "the pair port is a 78 GB/s limit" or "the single-writer limit is inside the core" must not come back. Older F items of the record that the user has not decided stay open (see record section 6).

Related: [[crb-term-slc-not-mesh-cache]], [[crb-label-loads-slash-stores]], [[review-loop-claim-defect-classes]], [[crb-brief-generator]].
