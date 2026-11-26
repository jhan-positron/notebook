---
name: asimov-c1nano-page-rewrite
description: "2026-11-10/11: asimov-c1nano-perf.html rebuilt from scratch by gen_c1nano_perf.py + c1nano_page/ (boot F1 main, older boots only where F1 has no row); gen_perf.py would overwrite it; codex loop protocol"
metadata:
  node_type: memory
  type: project
  originSessionId: 44910dbc-316f-4921-a7fe-7178628c5666
  modified: 2026-11-11T03:38:05.100Z
---

On 2026-11-10 Jibin asked for asimov-c1nano-perf.html to be regenerated from scratch (no resolved history, old data only where the latest boot has none, "Words used here" towards the end), then a codex review loop in codex-review-asimov-c1nano-perf.md.

- Generator: `python3 gen_c1nano_perf.py` (`--out PATH`, `--only KEY`) with package `c1nano_page/` (data.py with `python3 -m c1nano_page.data` selftest, 418 checks; own copies of viz.py and shell.py; refs.py, words.py, ids.py, IDS.md, API.md, sec_setup/glance/latency/bandwidth/multicore/ocm/mesh/open.py). cme_page/ untouched.
- Scope: boot F1 (011) main; boot E (hit-set, address-order chain, L1 forms, read variants), B (prefetchers off: address order, read variants, per-region OCM route cells + mesh-step fit), C (prefetcher effect = C against B, L3 step = E against C), D (page mapping, D over B), "boot R3" = folder 004 (one open item: read stream against L3 state). Boots C and D map OCM with 64 KiB contiguous translations, not 2 MiB pages.
- Page wording: "L3 on" / "the L3 holds no data" (never "L3 off"), "background control", no "baseline", "DRAM-model row", "OCM row" = every line, all five regions.
- First build: 25 figures, 29 tables, 116 references, about 22,600 words, sha256 48d9c6ca1b45de25. Previous page saved as asimov-c1nano-perf.prev-2026-11-10.html.
- CONFLICT: old `gen_perf.py` (through gen_perf_core.py) still writes the same file name. Do not run it.
- Codex loop: while building, write only to the scratchpad (`--out`), because codex watches the real file. Then append "Page ready for review: asimov-c1nano-perf.html SHA-256 <hash>" to the review file; Monitor the review file, re-arm every 30 min; ends on codex's explicit "No further comments".
- Spec, fact sheets and critic.md are in that session's scratchpad (core/SPEC.md, core/facts/); session-local.

Related: [[asimov-cme-page-rewrite]], [[asimov-page-wording]].

2026-11-11 UTC: codex loop closed in three rounds. Round 1 six findings, all accepted (compare repeatability with the same row's own reps; refill rates are not a partition of loads; 2 MiB rows are "DRAM-backed", timed SLC/DRAM split unknown; L2 capacity alone does not exclude outside-cluster traffic; boot pairs also differ in build and command list; L3 register coverage stated per boot). Round 2 two findings in Table 28 (DRAM anonymous allocation vs fixed OCM regions; eight-reader statement limited to 2 and 16 MiB). Round 3 "No further comments". Final page sha256 5c3d53a591a501b3: 26 figures, 29 tables, 122 references, about 24,600 words (over the 20,000-word target of the spec; Jibin not yet asked whether to tighten). refs.py stops the build when common.h's cited lines move (a peer process replaced common.h during the work).
