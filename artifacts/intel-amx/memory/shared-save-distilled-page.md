---
name: shared-save-distilled-page
description: "2026-09-21 distilled version of the shared-save animation page (status/shared-save-animation-distilled.html = artifact NgSY2o6p7LkLQjpERc5o6v): same animation script and measured charts, visible text capped at 3000 words by the generator gen_distilled.py; how the word count is defined and where the cuts were made"
metadata: 
  node_type: memory
  type: project
  originSessionId: 154f65b5-9b50-4d8d-9e68-26b5f8c7d229
  modified: 2026-09-21T06:27:24.498Z
---

Page: VNNIed-K-in-place/status/shared-save-animation-distilled.html = artifact
https://claude.ai/artifact/NgSY2o6p7LkLQjpERc5o6v. Generator
VNNIed-K-in-place/exec/shared-save-animation/gen_distilled.py, which imports gen_page.py
(CSS, JS, MEAS, SIM, UNIT_COST, layout/units JSON) and context_sections.py (stage_svg,
remedies_svg, FACT, ttft_ms) and asserts ASCII-only and <= 3000 visible words.

Word count definition (jhan's request 2026-09-21: "limit text at viewable page up to
3000 words"): strip <script> and <style>, replace tags by spaces, unescape, split on
whitespace. SVG labels count (509 words in the two reused charts), the text the
animation script renders does not. Final: 2990 (full page: about 16,600).

What was cut vs the full page (revision 5): the 64-unit table, the levels tree and table,
the 12-configuration milestone table, the statement-order table, the data-flow figure
and functions table (replaced by a 5-row table), the 2 x 2 matrix table (the dumbbell
SVG carries the numbers), the TTFT table (one sentence: both remedies cut TTFT 4.0% tp2 /
10.7% tp4, from unrounded means), the 9-unit test table (one sentence with the unit_start
list), the full sources table (3 bullets). Glossary: 12 rows instead of 60. Section
numbers of the full page kept (2.1 is folded into 2, 2.3/2.4 share a heading).

Review: workflow wf_aa7e148a-e78 (141 agents: 6 lenses x findings x 3 skeptics), 42 of
45 findings confirmed and applied (4 transposes per block and KV head, not "a
transpose"; unit cost = serial Save K of a or vnni0; t_llama_unit.cpp ends at line 2810;
save_k_impl :2992-3059, store_k_block :2855-2946; sd/GOF/FPGA/AVX-512/AMX/VNNI/rope/
minibatch defined; 40 attention workers = tp4 prefill only; factor = both measured;
"claims cost nothing" = mock 0 us; "may write the same lines").

Prompt history that led to the full page (jhan's own prompts, UTC): 2026-09-17 01:00
block-store animation request; 03:27 "Please do similar to 3.2 (b) Striping" (revision
1-4); 2026-09-18 18:56 "bigger context ... relation to block store" (revision 5);
2026-09-21 05:30 "How many words are on the viewable page?"; 05:39 the distill request.

**Why:** jhan wanted a page that can be read in one sitting; the full page is a
reference.
**How to apply:** regenerate with gen_distilled.py after any change to gen_page.py or
context_sections.py (it reuses their data); keep the count under 3000 by its own
definition; publish with the artifact url above. Related: [[shared-save-animation-page]],
[[block-store-animation-page]], [[vnni-k-terminology]].
