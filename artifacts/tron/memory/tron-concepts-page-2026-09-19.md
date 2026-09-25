---
name: tron-concepts-page-2026-09-19
description: "TRON attention-concepts explainer page (attention, KV page, sliding window, visible range, minibatch) built 2026-09-19 from brief random/input-2-ai/internalize-concepts.md; location, mock design, verified facts"
metadata: 
  node_type: memory
  type: project
  originSessionId: fcd18152-9ade-458a-935d-031499cd5ec4
  modified: 2026-09-19T21:09:24.778Z
---

Deliverables: `~/workspace/random/from-claude/TRON-concepts-claude.html` (full, 9,259 visible words) and `TRON-concepts-claude-short.html` (distilled 2026-09-20, about 3,000 visible words, same figures via the same script with null-guards; built by scratchpad build_short.py from parts/short/), single files with inline SVG/CSS/JS, light theme, answering the brief `~/workspace/random/input-2-ai/internalize-concepts.md` (the brief also names a codex variant `TRON-concepts-codex.html` for comparison). Source of truth: `~/workspace/tron` main at commit 9b11a912ba (2026-09-08).

Mock pass used by every figure (fixed; reordering changes every number): shared prompt s0..s8 (edge S, book X), request B decoding b0, b1 cached + b2 new (edge B, first child, continues book X), request A prefilling a0..a4 (edge A, book Y). 17 token_ids, 6 queries (token_job_id 0 = b2, 1..5 = a0..a4), pages P0..P2, Q0, Q1 with page_size 4, 7 ranged-mask ranges, minibatches MB0 = (b2, a0, a1), MB1 = (a2, a3, a4) with cap 4 / grain 2 (real llama constants give MB0 = [b2], MB1 = [a0..a4]), layer 1 window W = 6 positions. The page recomputes all of these in JS at load and shows a red banner on mismatch.

Facts verified in source that contradict older docs: ranged_mask capacity 4096 (doc says 128); max_minibatch_size 128 in llama.hpp (doc says 64); minibatching is NOT disabled by HW attention (generated plugins force max_minibatches = 1 for a code-generation reason); shard events are live code, not a stub; pages have only lo and offset_bound (no hi[]). Sliding window is per attention operation (INT_MAX sentinel = no window), applied after the mask at three points (select_relevant_pages per minibatch, whole-page skip, per-entry skip), measured in token positions, never trimming kv_pages; windowed layers always run in software with visible().

**Why:** follow-ups (a codex comparison, or extending the page) need the same mock and the same resolved doc-vs-code conflicts.
**How to apply:** reuse the mock numbers and the file:line citations from the page's sections rather than re-deriving; render checks via [[headless-chromium-render-check]].
