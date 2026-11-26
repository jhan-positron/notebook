---
name: crb-scaled-perf-counts
description: CRB counter files of 2026-10-30 (results/uncore2-20261030T203752Z) hold perf-scaled counts (each counter ran 49-50 % of the run); check column 5 of perf stat -x output before citing any count
metadata:
  node_type: memory
  type: project
  originSessionId: 6eb09a16-5942-4cc5-8ed0-249c7d5ab696
  modified: 2026-11-12T03:21:47.033Z
---

In `perf stat -x,` output, column 5 is the share of the run in which the counter ran. Below 100 % the printed count is scaled by perf, so it is an estimate.

Fact found on 2026-11-12 (second internal check of the CRB report update): in all 8 files `crb/results/uncore2-20261030T203752Z/cmn-*.csv` every counter ran for 49 or 50 % of the run. The report values that come from them are scaled counts: 0.62 TB/s and 0.45 accesses per line (40 threads), 2.9 % misses, 81 % / 19 % and 54 GB/s (one reader at 8 MiB). The root runs of 2026-11-02 are at 100 % in every counter row: `results/sudo-20261102T054936Z/writebw.csv` (part 3, 380 rows) and `results/sudo-20261102T211150Z/writepath.csv` (part 5, 598 rows). For one asm reader at 8 MiB they give 0.83 of the lines from the mesh cache (port flits, L2 refills and slice accesses agree), not 0.81.

**Why:** I used the scaled 0.81 as a count in the report update. The internal check rated it major, and the converted pair read rate changed from "63 to 65 GB/s" to "64.1 to 64.9 GB/s (est.)". The user's rule says never to present an estimate where a measurement exists.

**How to apply:** before citing a counter value from any CRB result file, read column 5 of its row. If it is below 100, mark the value "est." and look for a full-run count of the same event in the part 3 or part 5 files. The record of that update (`~/tmp/update-crb-memory-hierarchy.md`) lists the affected older report lines as item F21 (not changed, the user's decision). The caption and the source row of the first figure (report lines 97 and 113) were corrected on 2026-11-12 after the reviewer's finding CRB-R5. Related: [[review-loop-claim-defect-classes]].
