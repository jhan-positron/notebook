---
name: prefill-amx-vs-fpga-qwen3-4b
description: "2026-09-21/22 answer to jhan's question 'qwen3-4b prefill: AMX (canonical, VNNI-K) vs attention on the FPGA': equal within a few percent at prompt 1024; from 1536 up the FPGA wins, 1.9x at a cold 8192 prefill (6.7 s vs 12.7 s CPU AMX), AMX itself 2.3x over AVX; page CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html (section 5 = measured curve), generator exec/prefill-amx-vs-fpga-20260921/"
metadata: 
  node_type: memory
  type: project
  originSessionId: d431f4bb-1f10-45d3-99fe-097238cabbde
  modified: 2026-09-21T21:02:31.524Z
---

Question (jhan 2026-09-21): decode TPS is known to favour attention-on-FPGA (AoF); is prefill (TTFT) different?

Answer (all qwen-3-4b, prompt 1024; FPGA minus CPU, percent of the CPU arm, positive = FPGA slower):
- canonical AMX on CPU vs FPGA (range over the 5 matched pairs -1.9..+4.6 %): CI harness our half tp2 +4.6 % (727 vs 761 ms, same binary 544ca05c7a, n=3, t +14; FPGA arm had the kill switch, m6 measured that switch at +62 ms, so the gap is really -4..+4.6 %),
  tp4 -1.9 % (856 vs 839); whole 3bda nightly layout, same deb 0594dc54: 517 (q4b-swattn CPU) vs 516 ms (canon-ci FPGA) = -0.3 %;
  runtron 8u tp2 +0.4 / +1.2 %. Equal within run-to-run and night-to-night spread; the sign flips with tp/layout.
- VNNI-K on CPU vs FPGA: only runtron pairs exist (no CI-harness VNNI-K CPU-attention run was ever made): FPGA slower by
  +2.0..+2.6 % tp2, +6.1 % tp4 (wedperf/wedperf-attr/vnnik4 2026-09-15/16).
- AVX (nightly deb / kill switch) vs FPGA: FPGA faster by 8..22 % everywhere. That is what the nightly sees today.
- With FPGA attention the CPU build is second order: AMX debs lower TTFT by 2 % (whole machine 528->516) to 8 % (m6 our half 762->700).
- (2026-09-21 state) GAP: every qwen-3-4b run with "HW attention enabled" used prompt 1024; long prompts = Insufficient data.
- CLOSED 2026-09-22 by campaign q4b-fpga-20260921 (CI harness, whole 3bda, platformd 0.11, 2 users/engine, one pass per FPGA arm
  + cold cells): FPGA attention WINS above 1024 and the gap grows with the prompt. Cold 8192: CPU AMX (canon deb) 12,743 ms
  (09-19 check cell) vs FPGA 6,743 (AMX build) / 6,878 (AVX build) = 1.9x; cold 4096: FPGA 2,932 / 3,063 (no cold CPU cell).
  Warm 8192 (pass cells, 12-50 % prefix-cache hits): AVX-CPU 15,764 / AMX-CPU 6,929 (4 passes) / FPGA+AMX 3,681 / FPGA+AVX 6,662.
  jhan's "AMX 2x at 8k" = 2.3x warm (15.8/6.9 s) and 2.3x runtron cold (121.7/53.3 s). Warm fpgacanon vs canon: -9 % (1536) to
  -47 % (8192), monotone-ish; fpgabase vs base: -18..-62 %. Cold FPGA numbers agree across CPU builds within 2-4 % (card-bound);
  warm FPGA numbers favour the AMX build by up to 47 % (hypothesis: cached-prefix pages are not HBM-resident -> scored on CPU as
  dense pages -> AMX applies). Decode at 8192: 121 TPS (FPGA+AMX) vs 60 (CPU AMX).
- HBM EXHAUSTION (2026-09-22, engine journal; refined 07:3x UTC after a 4-agent verification): the warm FPGA cells at
  4096/5120 ran with the card's K/V space exhausted through the whole cell (about 78 % of shard placements failed, est.), 6144
  for its first 76-79 %, 7168 NOT at all, 8192 only from round 7 (AVX) / 8 (AMX) on (85 / 36 of ~800 shards). 509 of the 2,804
  warnings are the pre-cell AMX probe's own requests in the 30 s gaps (card already full when the 3000 cell ended). 0 in cold
  cells, CPU pass, all earlier 1024 FPGA runs. Warm FPGA numbers at 4096-6144 = FPGA+CPU hybrids; cold cells clean (8192 cold
  6,743/6,878 ms stands). NOT the cause of the AMX-build warm gains: they also appear at 2048 (-22.5 %, 0 warnings), 7168
  (-30.1 % TTFT, +14.0 % TPS, 0 warnings) and 8192 rounds 1-6 (-33 %) -> "measured co-occurrence, not measured cause";
  cached-prefix-on-CPU hypothesis stays open (pre-cell probe 16-21 G cycles in every warm window without warnings vs 10.6-13.4 G
  fresh, but the probe measures its own 4 requests). Card facts (tron source 30c4ac82cb): allocator 1 GiB address range x 32
  channels = 32 GiB per card (FUSE capacity 34,359,738,368 B), compile-time, shared with weights (weights' share NOT measured;
  the old "1.1 GiB est." had no source and was withdrawn); shard (1024 tokens, 36 slots) = 4.5 MiB/channel = 144 MiB/card ->
  upper bound 227 shards ~232k tokens per card; shard freed only on prefix-cache tree-node eviction; warnings say largest free
  block 0x3000 (lower-PCI card) / 0x5800 (other card), constant. Counters free_total/free_max/sw_fallback_total recorded per
  cell from the second launch on. Mapper: exec/prefill-amx-vs-fpga-20260921/hbm_cells.py -> hbm-exhaustion-cells.json.
- jhan 2026-09-22 01:5x UTC "is it a pattern that AMX + AoF > AoF alone, decode and prefill?" -> page section 6 (verified by 3
  agents, findings applied, v5 published 02:3x UTC): PREFILL yes for warm requests at long prompts only (AMX build faster in 10 of
  11 cells; -22.5 % at 2048, -30..-47 % warm 4096-8192; cold -2..-6 %, 1536/3000 and 1024 pairs not resolved; at tp4 prompt 1024
  the AMX build is 1.6 % SLOWER in both pairs); DECODE no at 1024 (-2.0..+0.5 %) and in cold cells (-0.6..+0.6 %), not resolved
  in warm long cells (+2..+14 %, all five point to AMX, n=1, within-pass t +0.5..+5.6; warm decode is 20-36 % below cold under
  AoF); VNNI-K build decodes 4-13 % SLOWER under AoF (issue 4500). Hypothesis for both: cached-prefix pages not HBM-resident ->
  scored on the CPU -> AMX applies (test: perfetto trace warm 8192 request, AMX vs kill switch, prefill + first decode steps).

Mechanism (tron source, PR 4424 tree 30c4ac82cb and main 1279137d, 3 code readers + 2 verifiers): prompt fed 128 tokens per
user per forward (TRON_PER_USER_PROMPT_CHUNK_LIMIT default; NOT 1024 - the 1024 is the per-forward capacity across users);
with FPGA attention the FPGA scores forward k's queries against HBM-resident K/V of forwards 1..k-1, the CPU keeps forward 1
(engagement 127), each query's own-chunk causal triangle (AVX path in every build) and DMA-lagging K/V; with CPU attention the
AMX dense-page kernel covers exactly those cross-chunk rectangles (~87 % est. of pairs). So AMX and FPGA replace the same work.
runtron 8-user "Parsing the prompt took" = batched prefill of all 8 prompts (all 8 values equal); CI TTFT = client stopwatch
per request (2 users/engine at tp2). Never compare across harnesses (ratio 4.3x tp2 / 2.6x tp4 is layout).

Measurement that closes the gap: fork exec/q4b-swattn-20260919/ into attention x build grid (canon deb / nightly deb, USE_HW_ATTN
unset vs =0, 9 prompts 1024..8192, 3 interleaved passes, same cell order for prefix-cache warmth + one cold launch at 1024/4096/8192;
dut.sh hwattn-off/hwattn-clear already exist). Cheaper: wedperf campaign.sh with prompt length as a cell field, cpu|fpga interleaved.

Artifacts: page CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html = artifact https://claude.ai/artifact/T6c2gB9zzJQsCukmC69e51 (private, v1 2026-09-21; republish the same file path) (light theme, ASCII); generator + pairs.json + rows-extracted.json
(253 rows from workflow wf_258257df-233) in exec/prefill-amx-vs-fpga-20260921/. Verification workflow wf_89cf57ff-912 (162 findings, 109 non-confirmed applied: p0perf summary.md line refs shift by 6, nightly 528 lives in ci-mimic reference/nightly-0918.arm.json not nightly_stats.json, q4b-swattn base-pass3 702 ms uneven Caddy spread, VNNI-K tp4 +6.1 % has ~1 df).

**Why:** the question will recur when someone proposes switching qwen (ingested models) from FPGA attention to CPU AMX attention:
the prefill side is equal at 1024 and the FPGA wins from 1536 up (1.9x at a cold 8192), decode also favours the FPGA.
**How to apply:** cite the pairs table; do not quote ci-mimic base 556 ms as the FPGA number (loaded client), use the nightly 528 /
13-night 509.5 +/- 7.2. Related: [[p0perf-20260913-campaign]], [[q4b-swattn-20260919-campaign]], [[canon-ci-20260918-campaign]],
[[wedperf-20260916-campaign]], [[issue-4500-root-cause-campaign]], [[fpga-path-under-vnni-k]].

- v9 (artifact Version 8, 2026-09-22 ~19:40 UTC): THREE passes per FPGA arm + runtron section 7. Verified numbers (workflow
  wf_29fc06f2-9fd, 3 agents, 52 findings applied): AMX build vs AVX build under FPGA attention, warm 4096-8192: -33..-48 % TTFT
  mean of paired per-pass deltas, faster in all 15 pairs, Welch t -4.4..-9.4; per UNCACHED prompt token -27..-44 % (arms saw
  different prefix-cache shares); 2048 -15 % (t -2.8); 1536/3000 not resolved; cold cells -7.5/-4.3/-2.4 %; decode warm not
  resolved (per-pass -9..+22 %), cold within 0.7 %. FPGA vs CPU AMX (canon): warm -6..-41 %, resolved except 1536/3000/5120;
  cold 8192 6,734 vs 12,743 ms. Exhaustion: 4096/5120 nearly ALL new shard placements failed (81-114 % est.) in every pass ->
  both arms scored nearly all new context on the CPU -> the AMX gain there (42/37 %) = the CPU-attention AMX gain (49/53 %);
  6144 56-78 %; 7168: no new failure in 4 of 6 pass-cells, the 2 failing ones = the engine that restarted earlier in the pass;
  8192 from round 6-8. TRAP (refuter): a degraded shard warns once and stays on CPU while its tree node lives (shard.hpp:8-31,
  full.hpp:2400-2428) -> 0 new warnings != no CPU attention; only 2048 is a clean counter-example. Fresh engines: 30.1-30.9 GB
  free per card (before-first-cell counter) -> weights+fixed 3.5-4.3 GB, 199-204 shards. free_total residue 59,113,472 B
  only in cells still exhausted at their end. Three FPGA-arm cells had a mid-cell engine restart (fpgabase p2@2048, p3@7168,
  fpgacanon p3@1536; pass 1 is the only clean pass). Pre-cell probe groups overlap at ~21 G cycles (does not separate clean
  warm from full). Runtron 8u (section 7): FPGA vs CPU AMX 0.98x(1024)/1.12/1.44/1.84x(8192) prefill, 1.6-3.6x decode; AMX vs
  AVX under FPGA -2.0..+0.3 % prefill, decode within 1.2 %; 0 HBM warnings in 72 runs (72 shards/engine at 8u x 8192).
  Nightly = cold for qwen3-4b (1.2 % hit; fresh engines per model; distinct seeds per user x round); warm only llama-3.2-3b
  shared prefix (14 %) and the 2nd llama-70b tp2 config (18-42 %). Generators: gen_page.py + fpga_section.py + rt8u_section.py
  + hbm_cells.py (shards_new_est from uncached tokens; free_before fields).
