---
name: glimmer-perf-followups
description: "2026-10-17 follow-ups to PR #5015 (jhan: 'perf boost opportunities lost because of the minimum-change requirement'): 58-agent workflow found 2 survivors of 26; prefetch branch (jhan-amx-kvmul16-prefetch 0ce944a9de) MEASURED +0.0..+1.4 % decode = below the 1 % ship rule, NO PR; planner branch (jhan-amx-kvmul16-planner 7ce44251c0, option B threshold) MEASURED: Glimmer tp2 p2048 prefill -3.3 % decode +1.9 %, tp2 p1024 decode +1.1 %, tp4 neutral, llama -0.4 % -> DRAFT PR #5017 stacked on #5015"
metadata:
  node_type: memory
  type: project
  originSessionId: 2286d13f-0c9b-4afd-a521-f1f97342a0e9
  modified: 2026-10-17T21:38:32.262Z
---

jhan 2026-10-17 ~18:1x UTC: "Your code change was under one requirement of minimum code changes, were there any perf boost
opportunities lost because of the requirement? Namespace naming or coding style improvement are still not considered. Please
explore, test on 3bda and open another PR if improvement are made."

Exploration: workflow wf_74d55a8d-2eb (5 readers x lens, 2 skeptics per candidate, synthesis), report
exec/glimci-20261017/perf-opportunities-report.md: 26 candidates, 24 refuted (mostly < 1 % of a decode step), 2 survivors:
(1) pv-3 in-kernel prefetch of the next dense page's K/V planes (est. +0.7..+3.2 % decode), (2) prefill-2 planner: separate
ready/pending walks + path-weighted page costs (est. 4-5 % TTFT).

Implementation (agents, worktrees under ai-runs/, stacked on 5061623a34): prefetch 17fa974626 + review fixes 0ce944a9de
(kill switch TRON_AMX_PREFETCH_DISABLE=1, two-page call-site test); planner a61dcc2be6 + review fixes f523e4253c (kill switch
TRON_PLAN_WEIGHTED_DISABLE=1; review found a cursor-advance bug and test UB, fixed). Review workflows wf_0ded7e6f-e4b (7
confirmed) and wf_8bb1dcce-397 (9 confirmed), findings in exec/glimpf-20261017/review-prefetch.json, exec/glimpl-20261017/
review-planner.json.

3bda build trap (2026-10-17): `nix develop` no longer builds on 3bda (dev-shell closure gone from the local cache, no mirror),
so build.sh of both chains runs in a plain shell: make ingest-deps + make gen/tokenize_py (uv /tools/uv/0.9.5), cmake --preset
native with -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache. The host nm cannot
demangle the requires-clause kernel symbols, so the symbol check needs KSYM_RE='amx_attn_h128g4(17qk_rowmajor_128x4|
18pack_q_group_128x4|21weights_times_v_128x4)ILm(4|16)E' KSYM_N=8 (6 kernels + 2 static-local guards). Second trap: the forked
chain.sh hard-exported ARM_ENV_amxoff (kill switch) and overrode the launch env; fixed to ${ARM_ENV_amxoff:-...}; the 8 wrong-arm
runs are in exec/results/glimpf-20261017/wrong-arm-run1/.

PREFETCH RESULT (exec/results/glimpf-20261017/, 40/40 runs, 4 reps, 2026-10-17 20:32-21:36 UTC, prefetch on vs off, FPGA
attention): decode TPS/user tp2 p1024 41.91 -> 42.00 (+0.2 %), tp4 p1024 63.04 -> 63.06 (+0.0 %, inside the band), tp2 p2048
38.15 -> 38.70 (+1.4 %), tp4 p2048 59.73 -> 59.99 (+0.4 %), llama 119.41 -> 120.43 (+0.8 %); prefill unchanged (<= 0.1 %);
attention busy per job 0.060 ms both arms. Below the pre-registered ship rule (>= 1 % at tp4 p1024) -> no PR; the
micro-benchmark estimate (per-visit data wait) does not transfer to production (bandwidth-bound with 40-47 workers + FPGA DMA,
the report's own open point). Tests pass on the branch (t_amx_numerics 17432/5, t_amx_dispatch_dtype 5814/2, t_llama_unit).

**How to apply:** planner chain launched 21:4x UTC (exec/glimpl-20261017/, REPS 3, cells l8b, glm tp2 p1024/p2048 fpga, glm tp4
p1024 fpga; metric = 'Parsing the prompt took' slowest user + decode TPS; ship rule: prefill shorter beyond the band at the
Glimmer cells with decode inside its band and llama unchanged). Related: [[glimmer-kvmul16-implementation]],
[[glimci-20261017-campaign]].

PLANNER RESULT: round 1 (f523e4253c + 6cda072924, two walks always; results/glimpl-20261017-r1): tp2 p2048 prefill -4.4 %,
decode +1.9 %; tp2 p1024 prefill +0.4 %, decode +1.7 %; tp4 p1024 prefill +2.1 % WORSE, decode -0.8 %; llama unchanged.
Diagnosis (agent, per-worker leaves): identical visits, +2.6 % sum of worker compute in the 39 CPU prefill layers at tp4 =
cost of spreading few pending pages (0.8 per block worker) over many workers; not the weights, not the zero-work return.
Round 2 (option B, f2c75d260b: separate walk only when pending pages per block worker >= pending_pages_per_worker_for_split
= 2; results/glimpl-20261017, 24/24 runs, 3 reps, 22:42-23:12 UTC): tp2 p2048 prefill 30.946 -> 29.925 s (-3.3 %), decode
38.18 -> 38.90 (+1.9 %); tp2 p1024 decode +1.1 %, prefill inside band; tp4 p1024 prefill -0.4 %, decode +0.4 % (inside);
llama-8b decode 119.66 -> 119.18 (-0.4 %, beyond its 0.30 band) = open item. Tests on 7ce44251c0 (test-fix): all pass
(t_llama_unit 265621/69). Draft PR #5017 (https://github.com/positron-ai/tron/pull/5017) opened 2026-10-17 23:21 UTC on base jhan-amx-kvmul16 (stack policy: draft until #5015
merges); body exec/glimpl-20261017/pr-body.md. Chain traps this round: stale exec/logs/<NAME>.done marker makes chain.sh
skip step D (move it aside between rounds); test expectations derived by simulation were wrong twice (query split at 8
workers; a spread is bounded by the block's workers).


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): 2026-10-17: prefetch +0.0..+1.4 % = no PR; planner = draft PR #5017 (tp2 p2048 prefill -3.3 %, llama -0.4 % open); 3bda nix shell broken -> plain-shell build recipe
