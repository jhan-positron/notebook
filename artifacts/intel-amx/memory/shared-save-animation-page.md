---
name: shared-save-animation-page
description: "2026-09-17/18 companion page to the store-remedies report: the shared block save played claim by claim, plus (revision 5, 2026-09-18) sections 2-3 on the stage of prefill, inputs/outputs/functions and the relation to the block store (status/shared-save-animation.html, artifact 9F8pqRrgZJjTbzQpFJg7eR); generators exec/shared-save-animation/{gen_page.py,context_sections.py}; KEY tp4 prefill split 15/40"
metadata:
  type: project
---

Page: VNNIed-K-in-place/status/shared-save-animation.html = artifact
https://claude.ai/artifact/9F8pqRrgZJjTbzQpFJg7eR. Generators in
VNNIed-K-in-place/exec/shared-save-animation/: gen_page.py (imports context_sections.py),
ground truth window_layout.cpp (struct offsets), cut_units.py (unit cut rule, checked
against t_llama_unit), savek_spans.py -> savek_spans.json (single Save K spans, n = 288,
sd/min/max; needs the python perfetto TraceProcessor, claude-box only).

Revision 5 (2026-09-18, jhan: "bigger context: stage of prefill, input/output data,
involving functionalities; relation to block store"): sections 2 (run/pass/layer tree,
measured lanes of layer 10 of prefill pass 3 before/after the remedies, statement order
of the generated plugin, data-flow figure + functions table) and 3 (2 x 2 who-writes x
how-written with factors from unrounded means, TTFT table from
exec/results/vnnik2-20260915/summary.json, scope table) inserted; old sections 2-6 are
now 4-8. Lane extracts for vnni0/a/b/ab (tp2, tp4) were made 2026-09-18 with
exec/vnnik-trace-20260914/lanes.py TRACE 2 10 (files next to the traces in
exec/results/vnnik2-trace-20260915/).

KEY CORRECTION in revision 5: a tp4 PREFILL window has 15 main helpers and 40 attention
workers (16 claimers, 80 fetch_adds, 4 units per thread). The 8 / 47 of revisions 1-4,
of analysis.json "threads", of lanes.py "cls" and of the report's section 1 words table
and 4.3 reading ("7.9x with 8 helpers, ideal 9x") is the DECODE split: helper count =
fixed_main_helper_split = pool workers x 2 / 7 (27 -> 7 at tp2, 55 -> 15 at tp4),
capped by available_main_parallelism(items) = items x max MoE top-k (1 for qwen), so 8
in a decode pass [model.hpp:1933-1935, 1950-1960, 1976-1982; TronCpp.hs:1397-1412].
The report's section 2.2 figure labels (15 / 40) are right. The REPORT WAS NOT EDITED
(jhan decides). Consequence on the page: the tp4 simulation of section 6.6 (25.5 / 57.5
us) agrees with no measurement; the ideal at tp4 is 16x, the measured shared-save-alone
factor 7.86x.

Other verified facts (all cited on the page): Pending sections start 0.2-0.5 us after
Save V ends (latch kvs_needed = 2: one minibatch, its own upstream); pages written in a
pass are not dense for that pass's queries (a visible range closes above each query
token; is_dense_amx_page tests the range of the page's first token), so Pending sections
run k_vnni::qk_group and the AMX kernel reads the planes in later passes; the layer end
moved 762 us between vnni0 and ab at tp2 while Save K shrank 771 us (one traced layer);
launch_early_hw_attention precedes the K channel waits (early phase for >= 4 items,
TRON_HWATTN_EARLY_LAUNCH_MIN_B); completion marks are consumed only by the FPGA GOF
dispatch and an assertion (copy_from copies them; CPU attention's gate is the latch);
kernel names: rope kernel _L, add_rmsnorm _2L and _(2L+1), layer 0 no suffix; "layer
10" in the traces counts from 0 = the 11th layer = window W 11; K row (256 B, one KV
head) vs K buffer entry (2048 B, one item); K buffer is bf16 (hardware::btensor).

Reviews: round 1 wf_fedc5c94-b53 (241 agents, 72 confirmed of 78), round 2
wf_93b2ef49-262 (156 agents, 42 of 50); all confirmed findings applied. Backups:
gen_page.py.rev4 / .rev5a / .rev5b, context_sections.py.draft1 / .rev5b. Pure ASCII
asserted; the three static SVGs rendered with cairosvg and inspected before publishing.

**Why:** jhan asked for the shared save in its bigger context; the review found that
revisions 1-4 (and the report) used the decode thread split for tp4.
**How to apply:** regenerate with gen_page.py; when quoting tp4 thread counts say prefill
15 / 40 and decode 8 / 47; the report's section 1 words table and its 4.3 reading still
say 8 / 47 for tp4 (offer the fix to jhan). Related: [[block-store-animation-page]],
[[vnnied-k-in-place-project]], [[vnni-k-terminology]] (say "shared block save").
