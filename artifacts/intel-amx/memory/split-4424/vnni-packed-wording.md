---
name: vnni-packed-wording
description: "jhan's wording rule (2026-10-13) for the bodies of PRs 4868/4887/4898/4901: 'packed' in the K/V storage sense is written 'VNNI-packed'; 'query pack', 'packer', 'pack site' keep 'pack'; applied with 112 substitutions, verified live"
metadata:
  node_type: memory
  type: feedback
  originSessionId: f0fb48e7-5749-4983-870b-ce4ee0ace8fa
  modified: 2026-10-13T18:26:51.699Z
---

On 2026-10-13 jhan asked: in the descriptions of PRs 4868, 4887, 4898 and 4901, where "pack(ed)" means
"packed to VNNI", write "VNNI packed" or equivalent grammar. Applied as the hyphenated attributive
"VNNI-packed" to: K, V, plane, slot, page, view, owner, storage, layout, binary, build, position, column,
token, row store, "the VNNI-packed reader" (the reader of VNNI-packed K), and to main's B-operand query pack
in the Background ("VNNI-packed queries go on the right"; `pack_q_group_128x4` "packs them into the VNNI
layout as the B operand", confirmed in amx_attn_iface.hpp: that packer fills the VNNI B-operand layout).
The Words rows "VNNI layout, packed" became "VNNI layout, VNNI-packed". Counts: 4868 42, 4887 37, 4898 19,
4901 14 (112). Each body was re-fetched immediately before the PATCH and compared byte for byte afterwards.

Kept unchanged (not the storage sense): "query pack", "AMX query pack", "query-pack slot", "packer(s)",
"VNNI packer" (PR-2's name for the packer chosen for a VNNI slot; it packs the A operand row-major),
"pack site", "packs no query", "query packing", "a packed query" (the `amx_q_packed != nullptr` test),
"packed query data", code identifiers (`page::k_packed`, `pack_q_rows_128x4`, `pack_q_group_128x4`,
`amx_q_packed`), and every "package".

**Why:** "packed" named two different things (the K storage layout and the AMX operand preparation of Q),
and PR-2's `pack_q_rows_128x4` packs the A operand row-major, so "packed" alone no longer implied VNNI.

**How to apply:** new body text for these PRs uses "VNNI-packed" for the storage sense and keeps "pack" for
the query-operand step. Re-fetch the live body before any edit: the PR-4 session edits the 4901 body
concurrently (it re-fetches too; my edit survived its 18:12 UTC update). Related: [[pr1-split-execution]],
[[pr4-split-execution]].

UPDATE 2026-10-13 ~20:30 UTC (jhan: "insert a column, PR #"): the stack tables of all four bodies now have a
"PR #" column after "Order" (#4868, #4887, #4898, #4901); the duplicate "PR #NNNN, " prefix was dropped from the
branch cell; "to follow as a draft" became "draft until PR #<predecessor> merges" (the wording 4898/4901 already
used); "based on PR 2/3" became "based on PR #4887/#4898". Patched with re-fetch + byte compare (script
stackcol.py in the session scratchpad). Left alone and flagged to jhan: the sentence "PR #4424 remains open as a
reference until all four are open" in 4868/4887/4898 (all four are open; 4424 is still an open draft).
