---
name: asimov-mesh-map-page
description: asimov-mesh-map.html (2026-11-12) - single run 8 summary page by gen_mesh_map.py; review loop closed in 3 rounds; what the script patches and what was removed
metadata:
  node_type: memory
  type: project
  originSessionId: f551609f-f91d-4e18-82b6-d0fff29e01c0
  modified: 2026-11-12T18:31:08.006Z
---

asimov-mesh-map.html is the one-page mesh latency map of run 8. Another session wrote it and gen_mesh_map.py on 2026-11-12; this session ran the inter-agent review loop as worker (review file asimov-mesh-map.html.review.md, REVIEW_COMPLETE at round 3, digest 59b9335c...12a7).

- gen_mesh_map.py imports gen_run8_report.py and gen_run8_boots.py with --out /dev/null and patches their figures and table rows by string replacement (`must()` fails if the source text changes). The two source generators and pages were not edited. See [[asimov-run8-results]].
- The page prints the rounded formula 20.6 + 2.0 X + 1.0 Y ns; the model column and chart line use it. Largest error against it on boot 1 is 0.34 ns (0.32 ns is the CPU-pair agreement, a different number).
- The memory-path fit cannot tell (0,3) from (1,3); (0,3) is taken from the mesh map.
- The hash table order 88, 216, 344, 160, 288 equals HN-S #0 to #4 in the folder 011 sysinfo mesh map.
- Removed: the sentence "88 of 113 claims confirmed" in section 8.5, because no file in the folder records those counts. Restore only with a cited record.
- Places of CPUs 4-5 and 6-7 on the mesh have no primary source in the folder; the page states this.
