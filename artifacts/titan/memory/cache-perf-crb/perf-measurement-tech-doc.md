---
name: perf-measurement-tech-doc
description: crb/perf-measurement-tech.html is the technique explainer built from bench/bandwidth.c and bench/run_sudo.sh on 2026-11-02; how it was verified and what the machine lacks for render checks
metadata:
  node_type: memory
  type: project
  originSessionId: e794ebbe-0c8e-4133-b9c3-364a6c50bb4d
  modified: 2026-11-02T20:05:54.264Z
---

On 2026-11-02 I generated `~/workspace/titan/cache-perf/crb/perf-measurement-tech.html`
(about 100 KB, 8 inline SVGs, 27 technique cards with verbatim code from
`bench/bandwidth.c`, `bench/run_sudo.sh`, `README.md`, `Makefile`, `subtract.py`,
`run_crb.sh`).

**Why:** the user wants technique docs that an outside engineer can re-implement
from; every snippet was checked verbatim by script and every prose claim was
adversarially verified against the code and the brief/full report.

**How to apply:**
- The verbatim-snippet check is a small python loop over `<pre>` blocks against
  the source files; re-run it after any edit of that page.
- The dev machine has no chromium, playwright or weasyprint: SVG layout must be
  checked by coordinates (label width about 6.3 px per char at 12 px).
- Source-side defect noticed, not fixed: `run_sudo.sh:5` says "512-line
  re-check" but part 1 passes `--verify-sample 256`.
- Measured numbers in the page come from `crb/crb-memory-hierarchy-brief.html`
  and the full report; see [[crb-memory-hierarchy-report]] if that memory exists.
