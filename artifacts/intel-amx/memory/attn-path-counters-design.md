---
name: attn-path-counters-design
description: "2026-09-22 counter.html (PR3879/new-PRs/PR1/counter.html, generator exec/counter-20260922/gen_counter.py): AVX/AMX/FPGA attention path counters + timers design on main 0a51385e95; jhan's two wrong premises (prefill = one token on AMX; a decode token has one path); verified hook sites, closed-form shares, the 2026-09-01 phase probe as the answer to per-phase timers"
metadata:
  node_type: memory
  type: project
  originSessionId: 031ee4ef-f487-45ff-9379-b5f4c385cda9
  modified: 2026-09-22T18:36:20.079Z
---

jhan (2026-09-22) asked for counters "on top of PR3879" measuring how much of the attention work runs
on AVX / AMX / AoF (attention on the FPGA), plus attention, per-layer and per-decode-step run time,
and then asked about timing QK / softmax / PV per path. Deliverable: PR3879/new-PRs/PR1/counter.html = artifact
https://claude.ai/artifact/BDw6g8QYbCUKdZkGAmbdMQ (private, v1 2026-09-22; republish the same file path)
(generator exec/counter-20260922/gen_counter.py + closed_form.py + rdtsc_cost.c; workflow result json
in the same folder). Verified by workflow wf_a8e982c8-1b8 (8 readers, 16 refuters, 3 designs, 2 judges,
1 critic; 411 claims, 327 hold, 82 qualified, 2 refuted) against a read-only worktree
~/workspace/ai-runs/tron-counters-ro @ 0a51385e95 (main, 2026-09-22).

Facts that settle the questions (file:line = main 0a51385e95):
- Prefill is every prompt token as a query, 128 tokens per user per forward (h/libtron.hpp:196-204);
  only the last chunk requests logits (context.cpp:48-50). Own-chunk (pending) pages have one mask range
  per query token, so is_dense_amx_page fails -> AVX; ready pages of earlier chunks -> AMX; first chunk
  100 % AVX. Closed form prompt 1024: 524,800 K tokens per (layer, KV head), AMX 87.4 %, = 1.78x the whole
  256-step decode (295,040); 8192: 15.75x. Under AoF the resident prefix goes to the FPGA and AMX gets
  only DMA-lagging dense pages (uses_hw does not gate AMX; query_visible = sw_required, :1406, :1746).
- Decode: path chosen per (query, page, kv_head) visit at apply_page_tok return sites :1768 (AMX),
  :1820 (empty), :1852 (AVX); CPU attention closed form floor(N/64) AMX pages + N mod 64 AVX tokens; under
  AoF the boundary = DMA progress at plan time (model.hpp:2503-2519), lag >= 1 GOF (4 tokens), first shard
  needs 128 resident tokens, engagement point 127 = query position rule -> steady-state decode under AoF
  predicts ZERO AMX visits (only AVX tail). Whether a full pending decode page (N mod 64 == 0) is dense is
  unverified (test: 2-chunk prompt, pending-pass amx visits must be 0).
- Layers: same path in every layer for llama-3.1-8b, llama-3.3-70b, mixtral-8x7b, qwen-3-4b; not for
  gpt-oss-120b (sliding-window layers never FPGA, head 64 -> no AMX), gemma-4, EAGLE. No per-layer FPGA
  cap (cfg.max_layers = loaded layers). AMX eligible = head 128, kv_mul 4, bf16 (llama-8b, mixtral,
  qwen-3-4b yes; llama-70b, qwen-32b, qwen3-30b-a3b(est.) no).
- Unit: K tokens scored per visit (x kv_mul = planner's k_dot_products); FPGA side = tok_ix + 1 per
  (pass, query) at self_attention.hpp:600 behind the :540-542 gate (inclusive-index off-by-one open).
- Existing: PR0 page-share counters have NO path tag; attn_elapsed rdtsc busy time exists (:774-806) but
  only feeds attn_time_estimator; perfetto spans exist without layer id; runtron prints no per-token time;
  the 2026-09-01 phase probe (tron-fence-amx @ 8fd1e7798d, TRON_ATTN_PHASE=1, attn_phase enum
  self_attention.hpp:223-260) already counts units_amx/dotter/empty, k_tokens_dotter, qpacks, cyc_* per
  phase; results exec/results/single-attn-20260901/summary.json (prompt 8192 per unit: AVX QK 1.87 /
  softmax 0.16 / PV 1.62 = 3.64 us; canonical AMX 1.49 / 0.11 / 1.11 / state 0.17 = 2.89 us; probe
  overhead 0-5 %).
- Design recommended: v1 compile-time option (PR0 shape) with counters at the three return sites + FPGA
  plan site, per-token path-set table keyed by token_job_id, five same-thread rdtsc timers (forward wall
  full.hpp:1993; attn busy :774-806; worker-0 wall :755-806; layer period entry-to-entry; hw join wait
  :1075-1078), rows [worker][layer], header amx_compiled/amx_available; publish the same rows as casual
  FUSE leaves under the define; env-var always-compiled variant (issue #4303) only after an A/A off-cost
  run; free perfetto one-liners ("layer" on Attention Ready/Pending, "n_listeners" on forward). Judges
  split (engineering 31 vs 29, user 30 vs 34 of 40) -> gating is a reviewer decision to obtain.
- Per-phase timers: lab-build option only (4 rdtsc per visit; rdtsc 7.25 ns/read on claude-box AMD,
  3bda unmeasured); FPGA phases not observable from the host (Insufficient data).

UPDATE 2026-09-22 (later): jhan clarified his model: "prefill processes every prompt token because we need
their K/V cache, but those tokens are given, so there is no attention or FFN involved; only the one generated
token involves attention." This is a misconception, corrected in counter.html section 1.1 (figure 1b): K/V of
token i at layer L are a linear map of its layer-(L-1) output, which needs attention over 0..i and the FFN;
a known prompt saves only the logits projection (tron: KV-missing prompt tokens become token jobs with
do_kv=1, full.hpp:2014-2030; llama.hpp:656-700 runs attention + FFN + next-layer K/V for every token job;
logits only for the last chunk, context.cpp:48-50; doc/hw-kv-rules.md:4 defines "Query" as logits requested
OR missing KV). Evidence: 2026-08-19 P1 counters 110.9 query tokens per page visit in prefill vs 1.02 in
decode; TTFT prompt 8192 qwen-3-4b 15.8 s AVX -> 6.9 s AMX -> 6.7 s FPGA. Expect the premise to recur; point
at section 1.1.

UPDATE 2026-09-22 (v4 of the page): jhan asked which counters belong to a build option vs env var vs
perfetto -> new section 9 (one table, 29 rows, rule = hook frequency): per-VISIT hooks (AMX/AVX/empty
tallies, per-token path sets, AVX reasons, hollow tile regions, Q packs, phase timers) = build option
(TRON_ATTN_PATH_COUNTERS / TRON_ATTN_PHASE_TIMERS); per-job / per-pass / per-forward hooks (FPGA k tokens,
fpga_queries, planner CPU dots per forward, forwards[class], attn_jobs, T1-T5, DMA lag, HBM fallback,
imbalance, attention share, prefill accounting) = env var TRON_ATTN_STATS + FUSE after the A/A; perfetto
= "layer"/"n_listeners" args, "attention op" span, inter-token latency (notify_listener span exists).
Sections renumbered: measurements 10, open 11, sources 12. Short version rewritten to 3 plain sentences
after a /plain-english check (10 violations); TOC added under the Short version. jhan also wants the
switch column visible per counter: keep section 9 in sync when counters change.

**Why:** the next step is a PR; the hook lines and the wrong premises will be asked again.
**How to apply:** cite counter.html sections by number; re-run gen_counter.py to change the page;
line numbers shift with PR 4424 (VNNI K), re-verify before writing a PR. Related:
[[wade-fuse-question-pr4267]], [[single-attention-measurement]], [[prefill-amx-vs-fpga-qwen3-4b]],
[[amx-busy-perf-counter]], [[pr3879-split-progress]].
