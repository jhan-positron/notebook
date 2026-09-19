---
name: amx-vnni-pseudocode-check-page
description: "2026-09-16 Notion sub-page checking jhan's AMX/VNNI-K decision pseudocode line by line against ff680c8020; key corrections and the pending-page rule"
metadata: 
  node_type: memory
  type: project
  originSessionId: 150fe5cd-91f2-4ba4-a357-dc1a80c785c9
  modified: 2026-09-16T20:01:22.854Z
---

Notion sub-page "Pseudocode check: what decides AMX and VNNI-K (2026-09-16)",
id 3ddd132d3cfd8121ae4aff7138318a8d, under [[amx-options-notion-page]]
(3ddd132d3cfd81ec8b97f46aec9ebbe9). Verified by 88 read-only agents on the
tree at ff680c8020 (13 claims x 1 verifier + 2 refuters; 46 factors x 1 refuter).

Findings that are easy to get wrong again:
- "VNNI-K code is not compiled when TRON_K_VNNI=OFF" is FALSE: amx_attn.cpp has
  no TRON_K_VNNI guard, so qk_vnni_128x4 + pack_q_rows_128x4 are in every
  TRON_AMX_DISPATCH build; TRON_K_VNNI only flips k_vnni::layout_on<128>.
- TRON_K_VNNI=ON with DISPATCH=OFF stops at CONFIGURE (FATAL_ERROR), not compile.
- Visible ranges of a pass close above every query token of that pass
  (src/tron/models/ranged_mask.cpp:42-49), so a page whose tokens are queries
  of the current pass is never dense (is_dense_amx_page one-range term); only
  pages written by earlier passes take AMX. Same fact as "pending page = AVX"
  in [[attn-worker-lane-facts]].
- Both gates (layout_on, eligible) are per attention geometry (KV slot /
  operation), not per model; VNNI reader compiles for kv_mul 1..16 only.
- TRON_AMX_DISABLE is inert on a DISPATCH=OFF binary and never read for a
  non-128x4 geometry (available() sits behind a constexpr-false &&).

**Why:** jhan asked "do I get it right" about the pseudocode; the answer page
is the reference for future explanations of the AMX/VNNI-K decision chain.

**How to apply:** when explaining or re-checking the AMX/VNNI decision tree,
start from this page's corrected pseudocode (section 2) instead of re-deriving;
cite ff680c8020 lines only after re-verifying on the current head.
