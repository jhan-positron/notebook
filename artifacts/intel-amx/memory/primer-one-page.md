---
name: primer-one-page
description: "2026-09-04 one-page Notion primer \"Predicting the AMX Decode Boost\" (sub page of \"Generate primer\"); where its source lives, how it was built and verified, the length constraint and its open risk"
metadata: 
  node_type: memory
  type: project
  originSessionId: 60f495c1-23f6-4851-b9b9-117f2c15afb3
  modified: 2026-09-04T03:16:03.449Z
---

Notion page: https://app.notion.com/p/3d1d132d3cfd8124bba6d3940f68913b (child of "Generate primer"
3d0d132d3cfd80509775ef836f2b9221, under Estimate 3cfd132d3cfd81fe8b79d71a428e7695). Built 2026-09-04
from the perf-model report (perf-model/index.html, model.json) per jhan's brief: title + skeleton,
one A4 page, data table, bullets, formula, chain walkthrough, figurative diagram of Tron-AVX vs AVX
bench vs AMX bench.

Source archived at perf-model/primer/ (final.md page body, fig.py -> fig.svg/fig.png, a4sim.py,
README.md). The figure is a PNG image block (Notion file upload), not mermaid: a mermaid LR version
renders 1603 px wide (7 px glyphs when scaled to page width) and the TB version is 696 px tall.
Regenerate with python3 fig.py; it prints label overflows (must be empty).

Process: 2 workflows (3 drafters + 3 judges; then 6 adversarial verifiers: numbers x2, program
descriptions, English rules, Notion/mermaid format, completeness). All numbers verified against
model.json prompts.8192 / baseline.8192 and medians.json. Verified wording rules that came out of it:
"hot 1.682 us" is clock-scaled (timed 1.615 at 3.895 GHz), the 0.067 us clock part applies to the
compute part only; do NOT say the bench and Tron run "the same code" or attribute the 9.5% gap to
"the harness" (the report leaves the 0.267 us unexplained; the copy misses pieces inside the unit) -
say "hand copy of the same per-unit code" and "calibration error"; unit_bench is ONE program with two
code paths ("three measurements", not "three programs"); coverage 99.24% comes from the 2026-09-01
AMX run's fallback counters, so say "no AMX run of Tron in this campaign"; validation rows' gates
also failed (17.8% / 14.9% short, limit 10%); state the pre-registered rule (+8.8%) and band
(+7.9..+15.9%, measurement outside it) whenever +14.4% is quoted.

UPDATE 2026-09-04 (later): jhan restructured the page himself (sections "1. Setup" with the figure and
two bullets, "2. Modeling", "3. Inputs and arithmetic"; Short version, glossary and step 4 removed) and
asked for figure v2: no "limit 5%: failed", no "measured +17.3%" / "2.9 points low", result box says
"Result", bottom arrow lowered (canvas 1400x470). Uploaded as amx-primer-three-measurements-v2.png.
Notion edit trap: update_content cannot match an image block (its markdown carries a signed S3 URL
that changes per fetch) - use replace_content with a fresh fetch of the whole body, image line swapped.

2026-09-04 04:00Z: page now has TWO figures: fig-setup.png (no numbers) under "1. Setup" and the values
figure under "4. Result" (jhan's own copy, re-uploaded as amx-primer-result.png); jhan set the title to
"Could We Have Seen +17.3% Coming?" and added a "3. Config" list. Generators: fig-setup.py / fig.py.

OPEN RISK: one-A4 fit is estimated, not printed. a4sim.py (DejaVu metrics, pessimistic ~10%) gives
120% of A4 at 10 pt with a 200 px figure; the page should fit with Notion's "Small text" toggle and
PDF export scale <= 90%. If jhan says it overflows: cut the two "Words used here" bullets to one, or
drop the second Step 4 bullet's band sentence. Title alternatives offered: "The AMX Boost Chain",
"Six Steps to the AMX Estimate".

**Why:** jhan wants a primer that walks the prediction steps like report section 6 and prints on one
page; the verifiers showed that compressing the report invites over-claims (same code, harness,
three programs), so the wording rules above must survive future edits.
**How to apply:** edit perf-model/primer/final.md, re-run a4sim.py, re-upload fig.png only if fig.py
changed, then update the Notion page with notion-update-page (page id above). Related:
[[perf-model-project]], [[perf-model-artifact]], [[notion-questions-keep-verbatim]], [[prompt-not-ctx]].
