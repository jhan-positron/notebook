---
name: wedperf-20260916-campaign
description: "DONE 2026-09-17 00:1x UTC: perf round on the nightly CI's 12 perf models, base = main eb2de0265a (just before PR #3879 merged) vs target = PR #4424 head ff680c8020 (AMX dispatch + VNNI K on), our half of 3bda; blocks A-F (CPU 256 tok, FPGA, 1536 tok, attribution base/mid/target, base/p3879/mid/target); report status/Wednesday-perf-test.html = artifact 1FjwnaQQmQbXmXPEouZroJ; key findings, scripts, traps"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5159102-6afc-41e0-998c-81147ffc8f47
  modified: 2026-09-16T17:41:20.740Z
---

Request (jhan 2026-09-16 17:2x UTC, ultracode): "do a round of testing, use same models as CI, for each model run
pre-PR3879 as base and PR4424 as target, generate results to status/Wednesday-perf-test.html to compare base vs
target. Use our half of 3bda." No model list was pasted ("see below" was empty) -> the list is systems_test
scripts/perf.py `configs` at origin/main 6b20db0 (12 configs, 11 slugs): llama-3.2-3b-fast tp2 32u, llama-3.1-8b-good
tp2 8u, llama-3.3-70b-good tp2 8u + 4u, llama-3.3-70b-good tp4 4u, mixtral-8x7b tp2 8u, qwen-2.5-32b-fast tp2 8u,
ingested-qwen-3-4b tp2 8u + tp4 8u, gemma-2-9b-fast tp2 8u, ingested-gpt-oss-120b tp4 8u, ingested-gemma-4-31b tp2 8u.

Facts established:
- pre-PR3879 = eb2de0265a = parent 1 of the #3879 merge commit 3fd5edaa66 (main first-parent log). PR #4424 head
  ff680c8020, merge base with main c7844ca2ce (post-#3879).
- llama-3.3-70b-instruct-good is tagged [production] only -> default dev builds (--tags test) exclude it; both
  binaries are built with -DBUILD_PRODUCTION_MODELS=ON (cmake/model_selection.cmake; all 12 CI variants carry the
  production tag at both commits). build.sh checks the selected runtime slugs in gen/selected_models.cmake.
- USE_HW_ATTN unset = FPGA attention for ingested models only (plugin force_hw_attn from TronCpp.hs), CPU attention
  for hand-written plugins (h/tron/models/hw_attn_config.hpp:12).
- Weights for every CI model are cached in /opt/positron/weights_cache/cached/ (NFS root /opt/positron/weights).

Design (exec/wedperf-20260916/): build.sh (fork of vnnik6, model-slug check), build-chain.sh (both builds; launched
17:34 UTC, worktrees /var/tmp/jhan/tron-pre3879 -> runtron.pre3879, tron-pr4424 -> runtron.pr4424), campaign.sh
(smokes 1u greedy per slug per arm -> block A CPU attention 12 cells x REPS=3 -> block B FPGA attention 4 ingested cells
x REPS_B=2; deadline 01:30 UTC; a (cell,attn,arm) failing twice is skipped; 5 consecutive failures abort),
summarize.py (paired target-base per cell), compare_tokens.py, launch-*.sh. Review + model-facts workflow
wf_e87cdf3f-0f6 (51 agents): 6 confirmed of 13 -> applied 2026-09-16 18:10 UTC after a clean stop (kill -TERM ->
finish aborted) and relaunch: rt runs pass --dont-stop (= CI ignore_eos; both binaries have the flag; smokes do not),
deadline = fixed instant (next DEADLINE_HHMM after start, validated, checked in wait_clear/take_guard -> rc 2),
stopped smoke removes its partial token file, build-chain.sh clears old markers, compare_tokens lists attempted
cells. Model facts (model-facts.json): AMX kernel eligible only for llama-3.1-8b, mixtral, qwen-3-4b (kv_mul 4,
head 128); VNNI layout also on for llama-3.2-3b (kv_mul 3), llama-3.3-70b (kv_mul 8), qwen-2.5-32b (kv_mul 5);
neither for gemma-2-9b (head 256), gemma-4-31b (head 256), gpt-oss-120b (head 64). DEB FINDING: the apt package
(make deb -> preset deb) compiles NEITHER option -> the nightly cannot see either PR until the deb build enables them.
Smokes (1 user): gemma-2-9b identical, q3-4b tp4 identical, others diverge at tokens 26-119; 1-user TPS equal.
STATUS: campaign relaunched 18:10:58 UTC (pid 3392077), deadline 2026-09-17T01:30Z; block A started 18:16 (rep ~45 min).
BLOCK C queued 18:24 UTC (launch-gen1536.sh waits for the main .done marker, then campaign-gen.sh = copy of campaign.sh
with GEN_LEN + BUILD_RES; NAME=wedperf-gen1536-20260916, 1536 generated tokens = the nightly's generation length, its
TPS capture window is tokens 896-1024; 12 cells x 2 arms x 2 reps, CPU attention). gen_report.py reads it as
WEDPERF_RES_C and shows a 256-vs-1536 comparison table. First rep-1 numbers: llama-8b good tp2 +2.1% TPS / -5.2% TTFT,
llama-3b 32u +4.0%; 70b tp2 8u TTFT 38 s, 15.4 TPS (a 70b run takes ~2 min). Rep = 30 min.
AFTER 2 REPS (19:16 UTC): q3-4b tp2 +16.0% TPS / -860 ms TTFT (t +28 / -370), tp4 +7.6% / -342 ms; l8b +2.1% / -160 ms;
gpt-oss tp4 TTFT +175 ms (+6.6%, sd 6 ms) = reproducible; gemma-2-9b +1.2% TPS (t 84); 70b/q25-32b/g4-31b unchanged.
ATTRIBUTION: base->target also includes main's #4400 (ingest BufferReuse/LivenessAnalysis = generated-plugin code!) besides
#3879 -> BLOCK D queued (launch-attr.sh waits for the block C marker): campaign-attr.sh, ARMS base/mid/target with mid =
runtron.main0916 (c7844ca2ce), cells gptoss-tp4-8u g2-9b-tp2-8u q3-4b-tp2-8u l8b-tp2-8u, 2 reps; summarize.py now takes
WEDPERF_ARMS/WEDPERF_PAIRS (mid:base target:mid target:base); gen_report.py section 4c reads WEDPERF_RES_D.
MAIN CAMPAIGN DONE 20:06 UTC (ok, 52 rt + 22 smokes, 0 failures). Block A final (3 reps, CPU attn, 256 tok): q3-4b tp2 +16.2% /
-858 ms, tp4 +7.6% / -342 ms, l8b +2.0% / -146 ms, l3b +3.6%, g2-9b +1.1%, gpt-oss TTFT +196 ms (+7.4%), 70b/mixtral/q25/g4-31b 0.
Block B (FPGA attn, 2 reps): q3-4b tp2 TPS -2.7% (t -10), gpt-oss TPS -2.9% / TTFT +205 ms, q3-4b tp4 n.r., g4-31b 0.
BLOCK C DONE 21:41 UTC (1536 tokens, 2 reps, 0 fail): l8b +17.0% (vs +2.0% at 256!), q3-4b tp2 +21.8%, tp4 +8.8%, l3b +4.0%,
q25-32b +1.1%, gpt-oss TTFT +206 ms, rest 0. BLOCK D running (started 21:42; rep 1: gpt-oss TTFT +193 ms and g2-9b +1.4% come
from MID vs BASE = main's own change, not PR #4424; q3-4b tp2: main +12.1%, #4424 +3.8%). BLOCK E queued (launch-attr2.sh waits
for the attr marker -> build runtron.p3879 from 3fd5edaa66 = the #3879 merge commit -> campaign-attr2.sh ARMS base p3879 mid
target, gpt-oss cpu+fpga, 2 reps) to split main's change into #3879 vs #4400 (ingest BufferReuse change = generated code).
Report rule: resolved = |t| >= 2 AND |change| >= 1% (PCT_FLOOR); plain-English workflow wf_77b60b19-84d applied 47 fixes.
BLOCK D DONE 22:27 UTC (0 fail): CPU: gpt-oss TTFT +162 ms = mid vs base (main's change), #4424 +28 ms n.r.; q3-4b tp2 main +12.2% /
-786 ms, #4424 +4.5% / -65 ms; l8b main +3.0% / -214 ms, #4424 -1.1% n.r.; g2-9b n.r. FPGA: q3-4b tp2 #4424 -2.6% TPS (t -3.0);
gpt-oss fpga mid +4.1%, #4424 -6.6% TPS (t -3.6); q3-4b tp4 fpga sd 12 = noise. BLOCK E (runtron.p3879 = 3fd5edaa66 built 22:37,
gpt-oss cpu+fpga, arms base p3879 mid target): CPU: #3879 alone = nothing (TTFT -18 ms n.r.), #4400 alone = TTFT +246 ms (t 8.3)
and TPS +5.0% (t 6.0), #4424 = TTFT -71 ms (t -2.6), TPS -3.4% (t -2.4). => the gpt-oss TTFT regression is PR #4400 (ingest
BufferReuse/LivenessAnalysis), not jhan's PRs. BLOCK F queued (launch-attr-more.sh: FPGA cells reps 3-6 with base/mid/target).
VERIFICATION wf_6ed9b61d-84a: 3407 numbers recomputed, 0 numeric mismatches; 23 prose/claim findings applied (gemma-4-31b has NO
FPGA attention: its block B runs used CPU attention; nightly default fpga only for q3-4b + gpt-oss). Generator backups:
gen_report.py.pre-english, .pre-verify. model-facts.json prose rewritten by agent facts-prose (backup .pre-prose).
BLOCK E DONE 23:04 UTC. FPGA: #4400 alone TTFT +147 ms (t 62); #3879 alone +28 ms (+1.0%); #4424 +8 ms n.r.; TPS all n.r. (gpt-oss
tp4 FPGA TPS sign flips between blocks B and E at n=2 = noise). BLOCK F started 23:04 but WAITS since 23:11: another session's
exec/vnnik7-20260916/build.sh (worktree /var/tmp/jhan/tron-vnnik7) holds the campaign flock; the guard alternates runs between
campaigns, so block F's finish time is open (deadline 01:30 UTC). BLOCK F DONE 23:55 UTC (78 records total in wedperf-attr-20260916, 0 fail; FPGA cells n=6): PR #4424 alone (target vs mid) with
FPGA attention: q3-4b tp2 TPS -2.2% (t -6.5), q3-4b tp4 -9.7% (t -2.9, sd 10.6), gpt-oss tp4 -5.0% (t -2.3); TTFT q3-4b -34/-58 ms
(gain). Main's change (mid vs base) FPGA: gpt-oss TTFT +146 ms (t 6.3) = PR #4400 per block E. base->target FPGA: q3-4b tp4 -11.5%
(t -4.4), q3-4b tp2 -1.8% (t -6.2), gpt-oss TPS -1.3% n.r., TTFT +176 ms (t 7.4).
FINAL REPORT: status/Wednesday-perf-test.html regenerated 2026-09-16 23:56 UTC (204 KB, ASCII, 0 pending); verification workflows
wf_6ed9b61d-84a (3407 numbers, 0 numeric mismatches, 23 prose/claim fixes) + wf_393cc2e4-e20 (308 block E numbers, 26 fixes) applied;
final check wf (Short version/Reading vs tables) launched 23:57. Publish copy via exec/wedperf-20260916/make_artifact_copy.py.
Extra worktrees on 3bda: /var/tmp/jhan/tron-pre3879, tron-pr4424, tron-p3879 (~10 GB each; cleanup is jhan's call).
PUBLISHED 2026-09-17 00:1x UTC: https://claude.ai/artifact/1FjwnaQQmQbXmXPEouZroJ (Version 1; republish the same scratchpad
copy made by make_artifact_copy.py to keep the URL). Last check wf_8699999e-e84: 1774 items, 17 prose fixes applied (0 numeric).
KEY FINDINGS for PR #4424 review: (1) CPU attention, nightly length 1536 tokens: qwen-3-4b tp2 +21.8%, llama-3.1-8b +17.0%,
qwen-3-4b tp4 +8.8% TPS; main's AMX kernel gives most of it (q3-4b tp2: main +12.2%, #4424 +4.5%; l8b: main +3.0%, #4424 -1.1% n.r.).
(2) FPGA attention (nightly default for q3-4b/gpt-oss): PR #4424 alone costs TPS -2.2% (q3-4b tp2, t -6.5), -9.7% (q3-4b tp4,
t -2.9, sd 10.6), -5.0% (gpt-oss tp4, t -2.3) at n=6 -> the VNNI K store / get_k_row gather on the FPGA path is a real cost.
(3) gpt-oss TTFT +7% comes from PR #4400 (ingest compiler), not from #3879/#4424 (block E). (4) The apt deb compiles neither
AMX option -> the nightly cannot see any of this until the deb build enables them. (5) gemma-4-31b has NO FPGA attention
(head 256, 16 KV heads) -> block B fell back to CPU. TRAPS: NFS negative cache on claude-box hides fresh .done/.log files for
~1 min (check on 3bda); killing campaign.sh via pgrep matches its subshells too (fine); the "block A repetition N done" log
line is reused by campaign-gen/attr for their own loops; another session's build can hold the campaign flock for 10+ min.

**Why:** the user wants CI-model coverage of the combined PR #3879 + #4424 effect before reviewers ask.
**How to apply:** relaunch campaign.sh with REPS=5 to add repetitions (idempotent per run); never edit it while
running. Related: [[vnnik6-kvmul8-campaign]], [[more-testing-round1]], [[3bda-shared-with-bill]],
[[pr4424-description-on-github]].
