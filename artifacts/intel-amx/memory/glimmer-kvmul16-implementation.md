---
name: glimmer-kvmul16-implementation
description: "PR #5015 OPENED 2026-10-17 19:56 UTC (jhan-amx-kvmul16 head 5061623a34 pushed, Skip benchmarks label, body exec/glimmer-20261016/pr-body.md): Muse Glimmer kv_mul-16 AMX support ( worktree ai-runs/tron-glimmer-amx, base main 6198824246); 3bda campaign exec/glimmer-20261016/ 36/36 runs ok: decode +4.4..+15.2 % (FPGA config), +6.1..+21.2 % (CPU config), prefill -0.6..-14.8 %, llama +5.2 %; results page muse-glimmer/muse-glimmer-amx-results.html (gen_page.py); design page section 4 corrected"
metadata:
  node_type: memory
  type: project
  originSessionId: 2286d13f-0c9b-4afd-a521-f1f97342a0e9
  modified: 2026-10-16T21:18:16.889Z
---

jhan 2026-10-16 (after muse-glimmer-amx.html): "implement based on main, preserve the current code as much as possible;
test at 3bda (another session is using it, coordinate); enable attention counters (TRON_ATTN_STATS) to measure
AVX/AMX/AoF; compare decode and prefill perf with and without AMX on Muse Glimmer".

Design chosen (judge panel): the three kernels (pack_q_group_128x4, qk_rowmajor_128x4, weights_times_v_128x4) became
function templates on `size_t group_heads` with `requires(group_heads_ok(group_heads))`, explicitly instantiated for
GROUP_HEADS_4 and GROUP_HEADS_16 at the end of amx_attn.cpp; shape_ok = head 128 && group_heads_ok(kv_mul); namespace
amx_attn_h128g4 and the _128x4 suffixes KEPT (user's no-rename constraint; header comment says they record the first
shape). QK transposing store: helper store_transposed_rows<lane> (selectors pair_sel = lane&1 ? 0XDD : 0X88, quad_sel =
lane&2 ? 0XDD : 0X88, row offset lane*4*stride); lane 0 always, lanes 1..3 under `if constexpr (group_heads == 16)`.
Call sites pass geometry.kv_mul() / operation_kv_mul; buffers were already geometry-sized (s_pages<kv_mul,64>, amx_o
16x128, amx_qpack slot 4096 B). t_llama_unit requires-probes pass <GROUP_HEADS_4>. Tests: t_amx_numerics sections for
4 and 16 heads (sentinel UNWRITTEN_ROW_SENTINEL_MINUS_12345 pins "s needs only group_heads rows"), gate STATIC_REQUIREs
(16 true, KV_MUL_8 false); t_amx_dispatch_dtype fakes = primary-template definitions recording pack/qk/pv_group_heads
separately (review finding T1), 16-head full-page section, fill 1 + head*HEAD_OFFSET_STEP_0_0625 + (i%4)*0.25.

Facts measured on 3bda (2026-10-16 21:00-21:17 UTC): fresh build 808 s (preset native, BUILD_INGEST_MODELS=ON,
TRON_AMX_DISPATCH=ON, -j20 our half), incremental 60 s; runtron.g16 has 64 tdpbf16ps (16 QK + 16 PV per kernel x 2
instantiations); tests: t_amx_numerics 17424 assertions/4 cases all pass with AMX (6 sections), kill switch 4110 + 2
WARN skips, t_amx_dispatch_dtype 5756/1, t_llama_unit 265452/67. The implementation agent's -O3 object compare: pack<4>
and qk<4> instruction-identical to main; pv<4> differs only in the TLS access model of the template's thread_local P
(general-dynamic vs local-dynamic; both relax to local-exec in the executable).

Blast radius (verified from 19 generated headers + llama.hpp configs): kv_mul 16 at head 128 = Muse Glimmer 30B (+ its
permuted twin) only; production-tagged. kv_mul 8 (llama-70b family, qwen-3-32b, qwen-3-30b-moe) stays refused.

Coordination: session token-divergence-4444-23 (td-20261016 issue #4444 probe) owns 3bda tonight until
exec/results/td3-20261016/probe.done (its 3 chained rounds, whole machine, serving down via platformd); it approved my
build (-j20 our half) and the fake tests; runtron measurements only after td3's marker + its message, before 02:10 UTC,
else after the nightly (NOT_BEFORE 2026-10-17T13:00Z). Trap: `ssh host 'A && B && setsid nohup x & sleep; tail'` keeps
ssh attached (the && chain runs in a background subshell that waits); launch as a bare `setsid nohup ... &`.

FINAL (2026-10-17 00:22 UTC, chain finished, serving restored, 36/36 runs ok, reps differ by <= 0.3 TPS): decode TPS/user
amxoff -> amxon: tp2 p1024 fpga 38.42 -> 41.89 (+9.0 %), tp2 p2048 fpga 33.11 -> 38.15 (+15.2 %), tp4 p1024 fpga 60.44 -> 63.08
(+4.4 %), tp4 p2048 fpga 54.21 -> 59.74 (+10.2 %); cpu: +13.4 / +21.2 / +6.1 / +13.7 %; l8b +5.2 %. Prefill time: fpga -2.8 /
-8.7 / -0.6 / -6.9 %, cpu -6.6 / -14.8 / -1.3 / -11.0 %, l8b -6.3 %. Attention busy share of a decode forward (from the
counters): Glimmer 13-37 %, llama 70-74 %. Open: kill-switch baseline vs a TRON_AMX_DISPATCH=OFF build (not measured); full
layers show AMX K tokens in PROMPT forwards at prompt 2048 only (workflow wf_4aa35874-11f explains).

Campaign status (2026-10-16 23:45 UTC): chain.sh running on 3bda with WAIT_MARKERS incl. td4; tests under the chain all
pass; campaign started 23:23 UTC after a 10 min wait (platformd takeover refuses serving younger than 10 min). Runs take
about 2 min each (36 planned). First results (rep 1): l8b cpu +5.1 % decode / -6.4 % prefill time; glm tp2 p1024 fpga
38.42 -> 41.90 TPS/user (+9.1 %), prefill 15.26 -> 14.84 s (-2.7 %); glm tp2 p2048 fpga 33.1 -> 38.1 (+15.1 %), prefill
33.9 -> 30.9 s (-8.7 %). Counters: 39 sliding layers AMX, 13 full layers FPGA (layers 3,7,11,... every 4th from 3), amxoff
no AMX. Observation: at prompt 2048 the full layers' PROMPT forwards also show AMX (933888) and AVX K tokens next to the
FPGA (gen_compare layer_check says UNEXPECTED; cause open, lose=0 exhausted=0). Page generator:
exec/glimmer-20261016/gen_page.py (imports gen_compare.py; dumbbell charts + layer map SVGs, rendered with cairosvg for
checks) -> muse-glimmer/muse-glimmer-amx-results.html.

Deliverables (2026-10-17 ~01:40 UTC): muse-glimmer/muse-glimmer-amx-results.html (generator exec/glimmer-20261016/gen_page.py,
reads gen_compare.py parsers + local-obj-compare/*.s; FPGA per-layer counts x n_kv_heads = software scale, AMX share 72.1 %
tp2 p1024 fpga decode) and the design page muse-glimmer-amx.html (doctype added, section 4 rows corrected, Measured bullet,
Words extended). Review: 97-agent workflow, 88 confirmed findings all applied (units of FPGA counts, 253 counted tokens vs
256 asked, per-rep worker counts, plain-English splits, Short version 3 sentences). Section 4a (prompt-2048 full-layer AMX
share): 128-token chunks, card scores only DMA-complete shards, 1600-token KV book full at the 13th chunk -> edge split at
1536, walker refuses the moved shard for one forward -> positions 1024..1535 scored on the CPU (8 dense pages user 1, 7 + 2
partial for users 2-8); glimmer_model.py reproduces all K-token counts. Not published as an artifact (offered).

**How to apply:** campaign scripts exec/glimmer-20261016/ (build.sh/tests.sh/campaign.sh/chain.sh/launch.sh/
gen_compare.py, written by agent campaign-g16); pre-build scripts exec/glimmer-20261016-pre/{build0,build1,tests0}.sh;
results exec/results/glimmer-20261016/. Report page to update: intel-AMX/muse-glimmer/muse-glimmer-amx.html (section 4
corrections from the verify workflow: self_attention.hpp call sites DO change, t_llama_unit probes, transposing store =
new shuffle selectors, main binary cannot give an AMX-on arm for Glimmer). Related: [[muse-glimmer-amx]],
[[attnstats-20261002-campaign]], [[platformd-011-restarts-stopped-units]], [[3bda-shared-with-bill]].

PR #5015 opened 2026-10-17 19:56 UTC (https://github.com/positron-ai/tron/pull/5015), base main, head 5061623a34, label Skip
benchmarks, body = exec/glimmer-20261016/pr-body.md (1,969 words, plain-English + numbers check applied, section "Performance at
the CI configuration" from [[glimci-20261017-campaign]]). jhan 2026-10-17: keep the namespace/suffix names (amx_attn_h128g4,
_128x4). Follow-up candidates (jhan: "perf boost opportunities lost because of the minimum-change requirement"): branches
jhan-amx-kvmul16-prefetch (0ce944a9de, in-kernel next-page K/V prefetch, kill switch TRON_AMX_PREFETCH_DISABLE=1) and
jhan-amx-kvmul16-planner (f523e4253c, path-weighted planner + separate pending walk, kill switch TRON_PLAN_WEIGHTED_DISABLE=1),
chains exec/glimpf-20261017/ and exec/glimpl-20261017/ (tags g16p / g16q); report exec/glimci-20261017/perf-opportunities-report.md.


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): PR #5015 opened 2026-10-17 (5061623a34); follow-up branches -prefetch/-planner; 3bda A/B 36/36 ok: Glimmer decode +4.4..+15.2 % (FPGA config), prefill -0....
