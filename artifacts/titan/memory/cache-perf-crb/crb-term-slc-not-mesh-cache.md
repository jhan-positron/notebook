---
name: crb-term-slc-not-mesh-cache
description: "In the CRB report and brief the shared cache in the mesh is called \"SLC\" (\"SLC (L3)\" where introduced), not \"mesh cache\"; the user approved the rename on 2026-11-12"
metadata:
  node_type: memory
  type: project
  originSessionId: 6eb09a16-5942-4cc5-8ed0-249c7d5ab696
  modified: 2026-11-12T20:02:37.840Z
---

The user (Jibin) approved on 2026-11-12 the rename of the report's own term "mesh cache" to Arm's term. Write "SLC (L3)" where the term is introduced and in main labels (first figure, section heading, size table, word list), and "SLC" in running text. Definition: system level cache, Arm's name for the cache in the mesh interconnect; Linux lists it as L3.

Keep the word "mesh" where it means the interconnect itself (mesh 0, mesh counters, mesh clock, mesh links, own mesh, "in the mesh").

State on 2026-11-12: renamed in `crb/crb-memory-hierarchy.html`, in `crb/crb-memory-hierarchy-brief.html` and in its generator `crb/make-brief.py` (see [[crb-brief-generator]]). Not renamed, by scope: the element ids and anchors of the report (they still contain "mesh-cache"), `crb/perf-measurement-tech.html`, `crb/crb-cross-check-bill.html`, the plan and review files in `crb/`, the scripts in `bench/`, and the files in `asimov/`.

**Why:** "mesh cache" is in no Arm document (0 occurrences in the CMN S3 TRM against 445 of "SLC"), and the user asked whether it was Arm's term.

**How to apply:** use "SLC" in any new text about CRB. When a file that was not renamed is edited for another reason, ask before renaming it. A rename also has to catch the bare word "mesh" where it names the cache level (for example "mesh write" row, "mesh-served").
