---
name: asimov-cme-page-rewrite
description: "2026-11-10 asimov-cme-perf.html was rewritten from scratch (boots F1/F2 only, no history) by gen_cme_perf.py + cme_page/; gen_perf.py still writes the same file name and would overwrite it"
metadata:
  node_type: memory
  type: project
  originSessionId: 495815bc-dbda-43cc-9015-e0d1efe06259
  modified: 2026-11-10T20:33:03.815Z
---

On 2026-11-10 Jibin asked for asimov-cme-perf.html to be regenerated from scratch from the test data, with no historical narrative (earlier data only where the latest runs lack it).

- New generator: `python3 gen_cme_perf.py` in ~/workspace/titan/cache-perf/asimov, package `cme_page/` (data.py data layer with `python3 -m cme_page.data` selftest, viz.py SVG charts, shell.py page shell with a lint for forbidden words, refs.py, words.py, sec_setup/glance/latency/l3/bandwidth/callcost/ocm/open.py, API.md). Reads only results/membench-jibin-011 (boot F1) and -012 (boot F2); one earlier-boot row (address-order chain) in section 9.
- Page: 56 figures, 68 tables, 62 references, about 61,000 words, about 120,000 px tall. Jibin has not yet said whether that length is acceptable.
- CONFLICT: the old `gen_perf.py` (through gen_perf_cme.py) still writes asimov-cme-perf.html. Do not run gen_perf.py without redirecting or disabling its CME full-page output, or the new page is overwritten. For edits to the briefs, patch gen_brief.py and the brief HTML directly.
- Previous page saved as asimov-cme-perf.prev-2026-11-08.html (sha256 prefix 8f057c0cd0a34d84).
- CME brief headings 1 and 2 now name the data path end point (Jibin's wording, 2026-11-10); the brief printed on 3 A4 pages before and after that edit.
- The spec and review records are in that session's scratchpad (cme/SPEC.md, cme/facts/, cme/review/integration.md); session-local.

**Why:** two generators now target one file name, and the new page's rules (no history, boots named "boot F1 (prefetchers on)" / "boot F2 (prefetchers off)") differ from the other three pages.
**How to apply:** edit cme_page/sec_*.py and rerun gen_cme_perf.py; keep [[asimov-page-wording]] rules. Related: [[asimov-run6-results]].

2026-11-10 (later): codex review loop on the new page closed in three rounds (codex-review-asimov-cme-perf.md): round 1 seven findings all accepted (bandwidth = loop throughput, "effective cycles per 64 bytes transferred"; round-trip baseline is a separate measurement and differences from it are not memory-access time; refill totals do not give each line's history; address-order row has 3 read refills per pass; charts scroll at narrow viewports; Figure 40 bars of durations, not nested intervals; only refill counters read zero in the baseline), round 2 one finding (Table 44 note on long-row precision), round 3 "no further comments". Final page sha256 88eca9932286dec3. Loop protocol that worked: I append "Replies from Claude, round N" ending with "Page ready for review: <sha256>", codex reviews only that hash; Monitor on the review file, re-armed every 30 min. Page is about 65,000 words; a tightening pass was offered to Jibin, no answer yet.
