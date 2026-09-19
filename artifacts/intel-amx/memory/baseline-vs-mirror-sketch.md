---
name: baseline-vs-mirror-sketch
description: "2026-09-13/14: jhan's hand sketch (Notion 'Scratch' page) contrasting Baseline (canonical-K) vs Mirror AMX, read against tron 60d66d9c04 and verified by 21 agents; page PR3879/baseline-vs-mirror-sketch.html; section 2 diagram carries verified matrix shapes in every box since 2026-09-14 (47 agents); corrected facts (0.37 us is the QK-phase gap, unit gap 0.22 us; arena figures are GiB; Q pack is per section; QK scores bit-identical by test; v* stored bf16 and truncated on store; kv_cache.hpp:598-600 FPGA wording imprecise)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 97fe382e-01e4-49e9-b02b-782618f409a7
  modified: 2026-09-14T00:33:32.698Z
---

jhan drew a two-column sketch (Notion page "Scratch", 3c3d132d3cfd80b38c47cc0f424f0511, image only)
contrasting "Baseline AMX" (S^T = K.Q^T, S = (S^T)^T, softmax, P = norm, P.V, softmax, norm) with
"Mirror AMX" (write K* interleaved & transposed when generating K, cache hot; S = Q.K*, then the same
tail). Asked "what do you see". Deliverable: PR3879/baseline-vs-mirror-sketch.html (light theme,
lane diagram + step check table + stacked phase chart + corrected redraw), published as an artifact.

Verified reading (tron pre-split tree ~/workspace/ai-runs/tron-presplit @ 60d66d9c04, the last head
with both kernels; 16 refuter verdicts, 3 number checks, 1 transcriber, 1 critic):
- QK orientation and transpose match the sketch (amx_attn.cpp:113-181 canonical, 237-268 mirror).
- The softmax tail is wrong in the sketch: no scale step shown, P is NEVER normalized before P.V,
  the "second softmax" is the running-state rescale (c = exp(m*_old - m)), and the division v*/s*
  happens once in finish() (self_attention.hpp:296-305) after join_page_ranges.
- K* is written in save_k right after the canonical store (model.hpp:2787-2803); "cache hot" is
  true for the READ side only (the scatter writes 64 cache lines per row, 70 ns/row, scalar).
- K* is a second copy (Note [Why not replace canonical K], kv_cache.hpp:593-611). The comment's
  reason (1) "the FPGA reads the K page bytes as stored" is imprecise: the CPU GOF swizzle
  (gof::populate -> shuffle_k_head, gof.cpp:108-162) reads the rows and the DMA reads the staging
  buffer. Not fixed in code (PR2 is parked); flagged to jhan on 2026-09-13.
- Q pack is once per (token, KV head, SECTION) = per apply_page_range call, not per (token, KV head).
- Mirror QK scores are BIT-IDENTICAL to canonical by test (t/t_amx_numerics.cpp:185-224).
- Second K* write site: copy_storage_slot rebuild on page moves (kv_cache.hpp:1966-1977).

Number corrections learned (apply whenever quoting these):
- single-attn-20260901 at prompt 8192: the 0.37 us canonical-vs-mirror gap is the QK PHASE only
  (1.487 vs 1.119 us); the whole-unit gap is 0.22 us (2.885 vs 2.661) because the mirror's PV is
  0.12 us slower (1.232 vs 1.110; cause unmeasured). At prompt 256 QK gap 1.0 us (1.53 vs 0.54).
- Round-1 soak arena figures are GiB (kv_cache.hpp:491 divides by 1024^3 but prints "GB");
  status.md:209 / notes.md:8 "printed in GB, 10^9 bytes" is wrong. Arena 43.8 GiB at 30 min,
  39.3-46.5 GiB over the hour (peak 46.45 GiB at KV footprint 92.9 GiB); "43.8-44.6" was a
  single-sample band, do not quote it. Host growth peak 42.3 GiB, plateau ~40 GiB.
- G1 TTFT numbers (qwen 1630/2022 +24.0%, llama 2685/3160 +17.7%, split 190/190/12 ms) verified.

Shape facts added to the section 2 diagram on 2026-09-14 (generator tmp: scratchpad gen_sec2.py, not
kept; the SVG is hand-editable in the page). Verified by 27 + 20 workflow agents (2 lenses per box)
against 60d66d9c04; all confirmed after two corrections:
- Q group = 4 head x 128 dim bf16 = 1 KB (this KV head's slice of the token's Q row). Baseline
  Q_packed = 4 panels (one per 32-dim step), each one B tile = 16 dim-pair rows x 16 col x 2 bf16
  = 1 KB, col 0-3 = heads, col 4-15 zero -> 4 KB, 1 KB real. jhan's guess "Q_packed 2 x 128" is
  wrong; "16 x 128" is only the byte-size identity (Q_PACK_ELEMS_2048), NOT the layout.
- K tile (A operand, baseline) = 16 tok x 32 dim, 16 loads per page (4 tok blocks x 4 dim steps);
  jhan's guess "K tile 4 x 128" is wrong. S^T = 64 tok x 16 col fp32 (4 KB, col 0-3 real) in
  s_transposed, transposed into s_pages 4 head x 64 tok fp32 (1 KB, stride 64 floats).
- Mirror: Q_rows = 16 row x 128 dim (rows 4-15 zero, caller keeps them zero), A tile 16 x 32 dim;
  K* plane = 16 panels (4 dim steps x 4 tok blocks) of 16 dim-pair rows x 16 tok x 2 = 1 KB each;
  scatter of K row j hits the 4 panels of token block j/16, row = dim pair, col = j mod 16, 64
  writes of 4 B. S = 16 row x 64 tok fp32 (qk_s, 4 KB), rows 0-3 memcpy'd into s_pages.
- Both QK kernels: 16 tile multiplies, 20 loads, 4 stores per page.
- PV: P -> bf16 RNE 16 row x 64 tok (2 KB thread_local); V_page 64 tok x 128 dim = 32 token-pair
  rows x 256 bf16; B tile 16 token-pair rows x 16 dim x 2; O = 16 row x 128 dim fp32 (8 KB, 8 C
  tiles, rows 0-3 real).
- v* is bf16 IN MEMORY (btensor_t = dmatensor<bf16>), the update v*.c + O is fp32 fma and the store
  TRUNCATES to bf16 (fp32s_to_bf16s, "round-to-zero semantics", simd/bf16.hpp:53) in both AVX and
  AMX arms; s*, m* are fp32. out = 4 head x 128 dim bf16 (512 values of the token's output row).
  Never write "v* fp32".

**Why:** jhan is constructing the baseline-vs-mirror explanation (likely for PR2 / reviewers); the
sketch's softmax tail and the "0.37 us per unit" shorthand are the two traps.
**How to apply:** reuse the page's section 3 table and section 6 redraw when the contrast comes up;
quote 0.37 us as "QK phase" and 0.22 us as "per unit"; write GiB for arena sizes. Related:
[[single-attention-measurement]], [[more-testing-round1]], [[g1-store-cost-campaign]],
[[mirror-naming-convention]], [[breakup-pr3879-plan]].
