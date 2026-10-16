---
name: tron-intuition-page
description: "2026-10-07 mental-map page PR3879/new-PRs/new-counters/tron-intuition-claude.html (generator exec/tron-intuition-20261007/gen_intuition.py + leaves.py): the six-step manual estimate recipe, per-layer timer budgets of the 2026-10-02 cells, model geometry table, the CI-harness-vs-runtron gap at llama 8u/1024 as an open edge"
metadata:
  node_type: memory
  type: project
  originSessionId: ca85cde0-d3cd-49b4-9d0f-c42111714d4a
  modified: 2026-10-08T00:02:23.644Z
---

jhan asked (2026-10-07, after the Notion Scratch page's gpt-oss time-budget answer) how to build a
mental map of tron so he can estimate AMX/AVX/AoF timing by hand for llama-3.1, qwen-2.5 and gpt-oss.
Page: PR3879/new-PRs/new-counters/tron-intuition-claude.html (pure ASCII, light theme, 5 inline SVGs).
Humanized edition (jhan /humanize-writing, same day): tron-intuition-claude-humanized.html, built by
exec/tron-intuition-20261007/humanize.py = 38 source-level (old, new) edits on gen_intuition.py (no bold labels in
lists, 'not X but Y' contrasts rewritten as direct claims, 'Measured:' fragments turned into sentences, 'anchor' ->
'reference measurement'); the skill's lint passed both pages (2.3-2.4 hits per 1000 words, all 'CI harness').
Generator: exec/tron-intuition-20261007/gen_intuition.py (writes the page; `leaves.py` next to it reads
exec/results/attnstats-20261002/leaves/<run>/decode_like_layer_* for the per-layer T2/T3/T4/T5 means).

Facts established for the page (reuse, all sourced):
- Per-layer budgets (worker 0, in-flight snapshots, us): llama-8b p1024 kernel on: period 247 = 2 jobs x 87 + 73
  (kill switch 248, busy/job 98 -> 89: period UNCHANGED, the other minibatch's card lane sets it); qwen3-4b CPU
  p1024: 329 = 83 + 57 waits + 185 busy + 4 join (kill switch 366: 1:1 pass); qwen AoF p1024: 201 = 101 + 58 +
  18 tail + 24 card wait; gpt-oss sliding layer 272 = 181 + 55 + 29 + 6.6 join, card layer 245 = 154 + 63 + 24 + 3.8.
- Attention busy share of T1 at 8 users (busy/job x jobs per worker per forward / T1): llama 67 % (p1024, 64 jobs =
  2 minibatches x 32 layers), 93 % (p8192); qwen CPU 56 %; qwen AoF 20 % (p1024, 58 % join wait) / 55 % (p8192, 88 %);
  gpt-oss 11 %. Kernel pass to T1: 1:1 for one-minibatch plugins or attention-dominated cells; ~1/3 for llama at
  8u/1024 (T2 drop 0.77 ms per worker-forward, T1 drop 0.26 ms).
- Geometry (tron-amx 85fc8ff4de): llama-3.1-8b 32L/32Q/8KV/128 (kv_mul 4, pass); llama-70b 80/64/8/128 (8, fail);
  qwen-2.5-32b 64/40/8/128 (kv_mul 5, FAIL -> 0 AMX today; llama.hpp:1594, CPU attention default); qwen3-4b
  36/32/8/128 (pass, AoF default); gpt-oss-120b 36 = 18 sliding(128)+18 card, 64/8/64 (fail); 20b 24 = 12+12.
- Prefill chunk default 128 (libtron.hpp:194-205). Some 2026-10-02 leaf snapshots are empty (gptoss amxoff,
  l8b p8192 amxon totals, q3-4b p8192 fpga) -> use exit-reports.txt for whole-run totals.
- OPEN EDGE: llama-8b 8 users prompt 1024: runtron lockstep +2.9 % vs CI harness 8u/engine +10.8 % (deb vs deb) /
  +12.9 % (kill switch, rinzler). Hypothesis on the page: mixed forwards (other users' prefill chunks, kernel 1.7-2.5x
  faster per job) in continuous batching; measurement = TRON_ATTN_STATS exit report of a rinzler engine under the
  CI harness (T1 sums of decode_like vs prompt_or_mixed, both arms). Not measured.

Traps: cairosvg renders blank when the <svg> root carries style="...height:auto" (strip it for render checks);
"<run>" in prose is an HTML tag (escape); the Notion Scratch page is a screenshot (download via
notion-get-file-download-urls, read as an image).

**How to apply:** when jhan asks for a timing estimate, walk the page's six steps (cell -> what is on the CPU ->
kernel-eligible visits -> price with 0.50/0.66/0.75 us per visit at prompt 256/2048/8192 -> pass fraction ->
anchor) and cite Table 1 / Table 3 of the page. Related: [[attnstats-20261002-campaign]], [[single-attention-measurement]],
[[perf-model-project]], [[aof-amx-question-20260925]], [[l8b-levers-20260919-campaign]].
