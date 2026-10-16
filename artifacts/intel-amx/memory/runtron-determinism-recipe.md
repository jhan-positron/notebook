---
name: runtron-determinism-recipe
description: "Verified 2026-08-29: how to make two runtron runs comparable for AMX debugging (pinning knobs, traps, what identity can and cannot mean); page in definitive-decode/index.html"
metadata: 
  node_type: memory
  type: project
  originSessionId: 528c65a4-1a65-45cc-a91c-9abf2f9fd11a
  modified: 2026-08-29T19:34:18.100Z
---

Brainstorm deliverable: intel-AMX/definitive-decode/index.html (linked from rampup/index.html),
source-verified by a 19-agent read + 9-agent fact-check workflow (2026-08-29). Key facts that
took effort and are NOT obvious from any one file:

- Pinning knobs: --pay-for-determinism (helper split num_workers*2/7 + uniform worker weights;
  model.hpp:2038-2092) + --temperature 0 + USE_HW_ATTN=0 (ingested plugins hard-code
  force_hw_attn=true, TronCpp.hs:233; unset => FPGA attention => hollow AMX A/B) + identical
  --app-cores/--dev-cores/--devices/-m + exactly one prompt + fresh process per run. The seed is
  inert at temperature 0 (argmax before any PRNG draw, stats.cpp:81-97). "Dense model" is not a
  requirement (MoE routing is a pure function of gate logits; Mixtral tests assert TVD 0).
- TRAP: `-u N` / `--users N` APPENDS N Moby Dick prompt files (runtron.cpp:734-742); it never
  limits users. t1-quick.sh used `-u 1` as its only prompt. Never combine -u with a token-file
  prompt (two prompts share every pass; --output-token-file gets two rows;
  --force-feed-text-token-file concatenates all rows into one vector applied to every prompt).
- Teacher forcing: --force-feed-text-token-file (exact ids, same format as --output-token-file
  rows); --force-feed takes TEXT and re-tokenizes. Forced ids count toward -l; sampler resumes
  when the list runs out; forced stop token ends the stream; asserts with --dont-stop or a draft
  model. Logits are logged BEFORE the forced id replaces the sampled one (model.hpp:3189-3226 then
  context.cpp:137-138), so per-step logits stay the model's own; read the ON arm's argmax from
  'Top-k Token IDs for Logits of token N'[0].
- Per-layer "logits" do not exist (lm_head once, model.hpp:1801-1812). Per-layer data =
  --intermediates-file (std::remove'd at model construction despite help text "append";
  model.hpp:1362-1369). Compare by key (thread-interleaved lines); bin/compare_intermediates
  always exits 0 -> grep 'Busted|Not found'; --vec-rtol 0 = identity mode; reports missing keys
  in one direction only. Ingested qwen labels: Embedding, WQ, WK, WO, WFF1, WFF3, WFF2 + shared
  WQ roped / WK roped / WV; the attention output itself is NEVER logged (AMX sits in the one
  unlabeled stage; first visible delta = 'WO layer 0 of token T', T>=63). WO = o_proj OUTPUT
  (BulkBulk.hs:158). Ingested plugins refuse --max-layers truncation (TronCpp.hs:986-999).
  Log cost est. ~15.5 MB/token over 36 layers -> keep prompts 64-192 tokens.
- AMX-on vs AMX-off is never expected bit-identical when AMX ran (fp32 add order + PV rounding,
  amx_attn_iface.hpp:64-72); identical ON-vs-OFF usually means AMX never engaged (no counter/log
  exists; did_amx is a local). Engagement needs: TRON_AMX_DISPATCH=ON build (default OFF),
  bf16 executor (not host/host_fp16), head 128 / kv_mul 4, >=64 visible tokens (first AMX step =
  query position 63), TRON_AMX_DISABLE unset in the ON process (exact "1" disables).
- Measured record corrections (re-extracted from exec/results/slot1/t1-quick/*.log): OFF==OFF
  identical (256 tokens, ctx 2048 & 8192) although t1-quick.txt prints a false "DIFFER";
  OFF-vs-ON first differs at generated token 30 at ctx 2048 (QUEUE.md says "~20"); identical at
  8192 (AMX engagement unproven). QUEUE.md:68 merges two experiments: llama-3.1-8b (190/192
  argmax, margins 0.031/0.000) vs Qwen3-4B (956 steps, max TVD 0.054, identical HF distance).
- MoE: gpt-oss (head 64, kv_mul 8) never runs AMX attention; Mixtral-8x7B (hand-written OR
  ingested) does; 8x22B (kv_mul 6) does not. --forced-routing is honored ONLY by hand-written
  Mixtral (feed_forward.hpp:278-285); on ingested plugins it loads + logs + does nothing. JSON
  only from HF extract_logits --save-routing (default --max-layers 2 = silent fallback for
  layers 2+). No tron-side routing exporter exists ("expert forcing" gap).
- HF arbiter: extract_logits takes --text-file (text), truncates to --max-tokens (default 40),
  --save-tokens writes the BINARY --token-file format => ids flow HF -> tron. check_golden_logits
  thresholds are per test (0.05/0.3/10%/top-5 is the llama ingest test; gpt-oss 0.10); no qwen
  golden test exists.

**Why:** these are the exact places the run-twice-and-compare idea silently fails; each cost a
source read to establish and several contradict help text or QUEUE.md wording.
**How to apply:** when anyone proposes comparing runtron runs (AMX or otherwise), start from
definitive-decode/index.html's recipe; never use -u with token-file prompts; treat identical
ON-vs-OFF as a hollow-A/B suspect until engagement is proven. Related: [[amx-router-p0-results]]
(older one-line recipe: its "-s 42" is inert at temperature 0), [[amx-tron-softattn-project]].
