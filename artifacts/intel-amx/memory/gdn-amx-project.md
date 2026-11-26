---
name: gdn-amx-project
description: "2026-11-20/21 GDN x AMX investigation (Qwen3.5 4B, GatedDeltaNet): model lives in open PR #3696 stack (not on main), build/run recipe on delphi-3b35, baseline + trace numbers, prediction (revised 2026-11-21), design page GDN/gdn-amx-design.html = artifact 27kTHHUMpJPoRTnxV1GJFf, scripts exec/gdn-20261120/, review loop record GDN/gdn-amx-design.html.review.md"
metadata:
  node_type: memory
  type: project
  originSessionId: be74f0ef-9ecd-4d0b-b01e-43155cd9bc79
  modified: 2026-11-23T20:11:03.439Z
---

jhan 2026-11-20 (cwd intel-AMX/GDN): "investigate adding GDN support in AMX" for the new qwen model; Bill said AMX
has potential for GDN. Asked for: baseline on delphi-3b35 (prefill/TTFT + decode TPS), attention metrics, a
prediction from metrics BEFORE testing a solution, and GDN/gdn-amx-design.html (what GDN is vs llama-3.1-8b,
prediction, sw design; plain English, short sentences, bullets, diagrams/charts over prose).
STATE: page published 2026-11-20 as https://claude.ai/artifact/27kTHHUMpJPoRTnxV1GJFf (private). Nothing is built.
REVIEW LOOP 2026-11-21: DONE. (jhan: /inter-agent-review-loop role=worker, reviewer = another agent, codex; round 1 got 7
findings R1-R7, all accepted; round 2 got REVIEW_COMPLETE "No further comments." at 05:08Z for digest 82eab393...). Then, as
jhan asked, the page was rewritten with /plain-english-experiment (354 violations -> 0 by check_lengths.py incl. table
cells; no measured/predicted number changed; 8 writers on private generator copies + AST merge by block name + 5 readers);
page now sha256 af8ee4fe..., artifact republished as version 2 (same URL). Check report: GDN/gdn-amx-design.plain-english-
check.html. Reviewed version kept at exec/gdn-20261120/review-loop/gdn-amx-design.reviewed-82eab393.html; tools in
review-loop/plain-english-tools/. Review record in
GDN/gdn-amx-design.html.review.md, session 20261121T021835Z-a7a95a. Before READY round 1 a pre-submission check found
72 findings (67 confirmed) and the page was REVISED (numbers below are the revised ones). Evidence + check scripts:
exec/gdn-20261120/review-loop/ (regen_check.py = read-only reproducibility check, structure_check.py, extract_text.py).
The experimental rule set forbids bold run-in labels at the start of bullets; the page now uses h4 sub-headings and
nested lists instead (keep that form when adding text; run check_page.py after every text change).

FACTS (verified 2026-11-20):
- Model = Qwen3.5 4B, slug ingested-qwen-3.5-4b(-tp2/-tp4), 32 layers = [GDN,GDN,GDN,full attn] x 8. NOT on tron
  main: registered by open PR #3696 (branch rbjarnason/qwen35-native-4b-registry, head 72e1191804, support_level
  cpp_plugin = tokens not yet valid). Local read-only worktree ~/workspace/ai-runs/tron-qwen35-4b.
- Weights are in /opt/positron/weights/huggingface (positron-ai/Qwen--Qwen3.5-4B-ingest-best-gptq, Qwen/Qwen3.5-4B).
- Build on 3b35: exec/gdn-20261120/build-3b35.sh (plain shell, clang-19, make ingest-deps, one-model registry
  models.gdn.yaml via -DDEV_MODEL_CONFIG, BUILD_INGEST_MODELS=ON, TRON_AMX_DISPATCH=ON) -> /var/tmp/jhan/b35-gdn-base,
  707 s. Run: run-one.sh (load snapshot first, SYSTEM_CONFIG="--instance 1,2", tp4 on our 4 cards), campaign.sh,
  trace.sh (--trace-gen/--trace-passes, cats model+scheduler), poll-leaves2.sh, collect.py, predict.py,
  analyze_trace.py. Results exec/results/gdn-20261120/ (collected.json, predictions.json, plugin/qwen_3p5_4b.hpp).
- Full attention: 16 query heads x 256, 4 KV heads. AMX attention kernels accept only head 128 x kv_mul 4
  (amx_attn_iface.hpp:149-151 shape_ok) and FPGA attention only head 64/128 -> all 8 attention layers run AVX-512.
  TRON_AMX_DISABLE on/off arms are identical on this model (0 AMX K tokens).
- GDN: 16 key heads, 32 value heads, 128x128 FP32 state per value head (2 MiB/layer, 50.25 MiB/sequence), runs on
  main + 15 main helpers only (16 of 56 threads; 40 attention workers idle during GDN); work item = (chain, key head);
  decode in place, prefill chains of 128 tokens on a 128 KiB working copy; per-token NaN scan in decode.
- TRON_ATTN_STATS does not time GDN; only the Perfetto slice "GatedDeltaNet" does. Use attention BUSY time
  (busy_cycles / 40 workers) for the kernel-speedup term, not T3 (wall_cycles_w0 includes the K/V wait: 2.4 ms per
  prefill pass at 1 user, 19 ms at 8 users).
- Traced decode steps are 3-28 % longer than untraced ones; traced prefill passes 0.2-3 %.

RESULTS (6 cells x 6 runs + 6 traces):
- Baseline TTFT / decode tok/s per user: 1u p1024 0.385 s / 273; 1u p4096 1.90 / 253; 1u p8192 4.71 / 231;
  8u p1024 2.91 / 121; 8u p4096 14.3 / 77.6; 8u p8192 35.7 / 56.3. Load: our CPUs <= 0.2 % busy, other socket 43 %.
- Prefill pass split GDN wall / attention busy / rest: p1024 42-44 / 9-13 / 45-46 %; p8192 27-29 / 41-43 / 30 %.
  GDN wall per prefill pass 20.2 ms (1u), 160 ms (8u), constant over prompt length.
- GDN step in prefill: 6.3-6.5 us on 14 threads, 3.8-4.0 us on the threads of CPUs 108/109 (those cores run at
  4.00 GHz; also CPU 126; the other 26 probed CPUs 2.70 GHz), mean 6.1 us; decode 13-16 us.
- CLOCK PROBE on 3b35 (bench/clock-probe*.txt): AVX-512 FMA 2.70 GHz; tile products with upper vector halves
  cleared 2.40 GHz; tile products with live 512-bit values 1.90 GHz; turns of 4 TDP + 64 FMA (34 ns) 1.90 GHz;
  turns of 4,096 TDP + 16,384 FMA (25 us) 2.40 GHz; lengths between NOT probed (both new kernels lie between).
  TDPBF16PS 16.17 cycles, TILELOADD 8.38 cycles, FMA 0.61 cycles. Kernel bench: recurrence 3.06 us per value head.
- DESIGN: Part 0 = chain replay by 64-column halves in a contiguous 32 KiB buffer (AVX-512 only, BIT-IDENTICAL,
  factor 1.4/2.1/2.4 on the GDN step; low 1.4 = the only timing of this loop order, on ANOTHER CPU: AMD Zen 5 KVM guest,
  design-checks/verify-cost/bench_gdn.run*.out, 1.46-1.74x on the recurrence at 128 KiB, 0.6-0.9 cycles per L2 line there
  vs 1.8-2.96 est. for 3b35; the first page version did not disclose it); Part A = AMX block kernel (32 tokens, FP32 state split into 3 bf16 pieces,
  18.5 TDPBF16PS per value head per token, est. 970-1,290 cycles, factor 2.0/3.2/3.7, NOT bit-identical: 0.005-0.10 %
  of bf16 output words differ, resumed-vs-cold runs differ too); Part B = AMX attention kernel 256x4 (prefill factor
  1.6/2.3/2.9 [fit prints 2.95-3.05, not 3.0-3.3] applied ONLY to the "full-page time" = slope x ready-pass K tokens from a
  line fit of busy - join wait (67 ns per K token; 51-96 % of busy), plus a clock cost +42/+42/+12.5 % on the "other
  attention work" (busy - full-page - join wait); decode 0.9/1.0/1.17 on the whole busy time; risk: a 256-wide page is 64 KiB and does not fit L1); GDN decode: no AMX.
  Non-AMX side finding: only 16 of 56 threads run GDN.
- PREDICTION (est., 3b35, working values; range in brackets; REVISED twice on 2026-11-21, this is the review round-2
  state): TTFT Part 0 -14..-23 % (8..26); Part A -18..-29 % (11..32); Part B -2..-22 % (1..26); A+B -30..-41 % (18..47);
  decode 0 % (-5.3..+7.8 %). Part A at 1.90 GHz instead of the assumed 2.40 GHz = 14..23 % = Part 0.
- Other facts corrected 2026-11-21: clock-probe turns are 35 ns and 33 us (not 34 ns / 25 us); stage 3 = 9,216 AVX-512
  ops per block; up to 67 bf16 increments near zero; 2-piece split error 5-227x; one attention page visit = two runs of 32
  tile products; memory stall 47 % (AVX-512) / 77 % (AMX) of a page unit on 3bda; a resumed request can already differ in
  logits today (full.hpp Note [Recurrent state snapshots]); the vLLM/SGLang GDN kernel has no tile intrinsics (calls
  brgemm; file comment says amx-bf16); Intel opt manual vol 1 = doc 248966, AMX store-to-load forwarding = section 20.15.
- Design-check scripts + verifier scripts saved in exec/gdn-20261120/design-checks/ (kernel, proto, skeptic,
  integration, lead, verify-math, verify-cost, verify-fit, review). Page generator: gen_design.py + design_numbers.py
  + figs_*.py + pagelib.py (run predict.py first; pure ASCII output; byte-reproducible since 2026-11-21; gen_design.py
  asserts that predict.py factors equal the values derived in design_numbers.py).

TRAPS: Artifact read of the stack design doc (claude.ai/artifact/Ca5QHdEWLUDu2NfDS2gg5P) failed twice with a
safeguard error; do not read other users' home dirs on 3b35 (auto-mode denial); `cd` inside ssh prints an ls
(shell hook) - use absolute paths; leaf snapshots taken while a run ends read {} for worker files; `rm` with a
shell-variable path is blocked by the harness (use "${VAR:?}" or literal paths).

**Why:** the build/run recipe and the stack branch are not derivable from main. **How to apply:** reuse
exec/gdn-20261120/ scripts; rebuild from the PR head when the stack moves; the plan's first task is a stand-alone
benchmark of the recurrence at the 128 KiB working-copy size. Review-round facts: busy_cycles (T2) includes join wait (T5) + pending-page AVX-512 scoring + join; attention wait =
T3(worker 0) - mean T2 mixes Q wait + K/V wait; ready-pass (full-page) scoring can overlap FPGA K/V production (model.hpp
Note [Ready versus pending attention work]); measured A/B with the same stats on 3bda = exec/results/attnstats-20261002
(busy 1.88x shorter at 8u p1024). Headless Chromium works on agentsrv: ~/.cache/ms-playwright/chromium_headless_shell-1243
(--no-sandbox --disable-gpu --disable-dev-shm-usage --disable-software-rasterizer; a file URL with #fragment gives a
blank screenshot). gen_design.py table(): do not name a parameter cls (a local lambda has that name).
Related: [[delphi-3b35-default-server]],
[[attn-stats-pr-implementation]], [[perf-model-project]], [[glimmer-kvmul16-implementation]].

IMPLEMENTATION PHASE - DONE 2026-11-22 ~02:40Z (jhan 2026-11-21: "implement GDN/AMX, test at 3b35, compare the perf w/
prediction, use /plain-english-experiment to write report HTML; add GDN/AMX counters similar to the attention and AMX counters").
- RESULT PAGE: GDN/gdn-amx-results.html = private artifact https://claude.ai/artifact/T4FxXrJVomTvmX3UWG3jSY (v3 text; republish the same file path to update) (generator exec/gdn-impl-20261121/gen_report.py + report_data.py + collect.py +
  compare.py; text copies exec/results/gdn-impl-20261121/results-page-text-*.txt). Checked twice by agent workflows
  (understand/verify-page-result.json + verify-page-v2-result.json: tables reproduce from raw logs; wrong values in 4 + 2
  tables and ~60 wording/interpretation points fixed; collect.py now divides prefill totals by prompt/128 passes).
- PAGE v5 (2026-11-22, after jhan's questions on both pages): results page got a NEW section 5 "Why decode gains little"
  (old sections 5-11 are now 6-12; figures 3, 5, 6, 7 are new, 5 and 6 are animated with inline JS), a sub-section in
  section 3 "8 users against 1 user at prompt 1,024", and a sub-section in section 2 "Which kernel takes a token".
  Generator of the new parts: exec/gdn-impl-20261121/decode_why.py (called from gen_report.py; reads the decode class of
  collected.json). Facts behind it: Part A is built on Part 0 and REPLACES its kernel for full 32-token blocks (a token takes
  exactly one of token / chain / block kernel), so "Parts A and B" = all three changes and the gains of 0 and A do not add;
  decode = chains of 1 token -> step() + token kernel in every arm (100 % token path); decode step split (base, GDN wall /
  attention wall T3 on worker 0 / other work): 1 user 9-11 / 13-23 / 67-76 %, 8 users 18-33 / 18-55 / 27-49 %; decode GDN
  step 14.4 us = start of the chain 7.5 us (bind, copy if another buffer, NaN check of the 128 KiB state; not split by the
  counters) + token step 6.7 us, vs 6.08 us per token in prefill; 8u p1024 vs 1u p1024: attention work without the join wait
  1.52x vs 1.32x shorter under Part B, but the prefill join wait rose 3.3 -> 10.9 ms with 8 users (cause not measured).
  jhan's reading that needed correction: Part B is AMX for the 8 attention layers (not the dense/FPGA layers); TRON_GDN_STATS
  is a separate switch from TRON_ATTN_STATS. Animation test recipe: headless shell + a fake requestAnimationFrame clock
  (rAF does not advance under --virtual-time-budget); cairosvg for static renders.
- PAGE v5 PUBLISHED 2026-11-22 as artifact version 3 (same URL). A 5-agent check (understand/verify-decode-section-result.json:
  34 findings, 32 applied, no wrong number) corrected: the prefill JOIN WAIT (T5, failed polls on other threads' sections, inside
  busy T2) is NOT the wait for K and V (outside T2; T3 - mean T2 changed only 19.2 -> 19.8 ms at 8u p1024), so the cause of the
  join-wait rise under Part B is still unmeasured (same rise on 3bda: 4.1 -> 12.0 ms); step() for chains of 1 token is tron's
  choice (the chain kernel would add two 128 KiB copies per token), not a need of the kernel; Figure 5 shows ONE KEY HEAD.
- HANDOFF FOR THE SPLIT (jhan 2026-11-22 ~16:20 PST: "please generate handoff md to status/ folder, the file instructs
  another agent to implement the new PRs as we discussed"; and on E4B: "`I still recommend keeping E4B in scope`: agree"):
  GDN/status/handoff-gdn-pr-split-20261122.md + GDN/status/handoff-material/facts-{cut,switch,partb,tests,scripts}.md (5
  read-only reader reports with file:line). ANOTHER AGENT executes it; this session did NOT start the split. The file was
  checked by 6 + 2 read-only agents (112 findings in round 1, applied). It holds 3 START QUESTIONS for jhan: Q1 the go (jhan
  gave none in this session; the request for the file is not the go), Q2 the D10 approval - tron AGENTS.md lines 29-35 say a
  test that no required CI suite executes "must not be committed" without the user's explicit approval, so by the letter the
  deferred decision BLOCKS the push of PR 3 and PR 4 (their AMX cases run only in the CMake workflow on an Intel runner; I had
  told jhan "not blocking for drafts" - reported the stricter reading to jhan on 2026-11-22), Q3 whether the two
  measurement-only branches may be pushed. Defaults I set
  there that jhan has not decided (U1-U11): close #5572 as step 1; a second comment with the 4 links; branch names jhan-gdn-1-stats / jhan-gdn-2-chain / jhan-gdn-3-amx / jhan-attn-h256
  (jhan-gdn-stats is an old local branch, jhan-gdn-amx is PR #5572's head); timing file unchanged (open item); measurement
  branches jhan-attn-h256-on-qwen35(-base) pushed without a PR; model-level E4B test = open item (needs token + golden files
  in /scratch/test/data on every CI runner, 1,048,584 bytes per position); no combined A+B numbers in a body.
  Facts found while writing it: the split adds NO new CTest name (t_gdn_stats.cpp is in binary t_gated_delta_net,
  t_amx_gdn_numerics.cpp in t_amx_numerics); gdn_stats.hpp already includes attn_stats.hpp (add `using
  attn_stats::env_enabled;`); 0d69ef3ce8 defines ten keys without a production writer (5 written by Part 0, 5 by Part A);
  775bba7661 cuts by file for 12 of 15 files, mixed = gdn_rolling_executor.hpp, gdn_execution.hpp (1 line),
  t_gated_delta_net.cpp; cherry-pick of 882e5322f1 onto ddf843ad97 conflicts in 5 of 7 files / 29 places; #5022's net change
  (3bea58b788..ddf843ad97) cherry-picks onto 72e1191804 with 0 conflicts; agentsrv git is 2.34.1 (no merge-tree
  --write-tree); never run bin/slice bench on 3b35 (measures on the other users' half; note in the muse-glimmer memory).
- PR SPLIT - DECIDED BY jhan 2026-11-22, NOT YET EXECUTED (jhan: "Do not create the new PR, still at discussion phase"; wait
  for an explicit go). Decisions: 4 separate draft PRs. Sequence (GitHub stack, described in each body with "The stack"
  table): counters -> Part 0 -> Part A, on the model's branch (PR #3696 head). Part B outside the sequence, on a NEW BRANCH OFF
  jhan's PR #5022 branch jhan-amx-kvmul16 (base main; 6 of Part B's 7 files conflict with #5022, so it is a port next to the
  group_heads template; model numbers from a measurement-only build "model's branch + #5022 + Part B": #5022 applies to the
  model's branch except config/test-benchmarks.json). Counters: REUSE TRON_ATTN_STATS, drop TRON_GDN_STATS. A campaign run at
  the Part 0 head is required (plan: one fresh campaign over every new head). PR #5572: add a note that it will be split, then
  close it (first step after the go). All PRs draft, label Skip benchmarks, NO Run CI at opening: jhan reviews first, then
  jhan calls Run CI - REMIND jhan to call it (when the PRs are reported open and when jhan says the review is done) and put
  this action item into each PR body. AMX-tests-only-in-the-legacy-CI-lane approval: deferred by jhan, not blocking drafts,
  keep as open item in the Part A and Part B bodies. Housekeeping practice found on main (last 150 commits): changelog.d rule
  exists since 2026-11-18 (fragment changelog.d/<PR>.<section>.md, one "- scope: Entry. (#N)" line <= 80 chars, performance is
  notable; 3 of 16 recent source-changing commits have one; #5022 has one; needs the PR number, so push after opening; the
  model's branch forked 2026-11-16, before the folder existed); config/test-benchmarks.json is changed by 36 of 70 commits that
  change a test and by both commits that added a new t/t_*.cpp (tool: bin/slice bench --update <name>; file keyed by CI machine
  type, e.g. genoa96 - unknown whether 3b35 gives valid entries). Proposed branch names: jhan-gdn-stats, jhan-gdn-chain,
  jhan-gdn-amx, jhan-attn-h256. Facts: commit 775bba7661 must be cut (about 35 Part A lines inside gdn_rolling_executor.hpp;
  t_gated_delta_net.cpp uses the counter tally in 24 places, so counters go first); gdn_execution.hpp exists only in the
  model's stack; PR #3696 sits on another stack PR (rbjarnason/qwen35-normalize-conv-weight-storage); main squash-merges.
- PART B ALSO SERVES GEMMA 4 E4B (found 2026-11-22, read-only check; reported to jhan, NO decision yet). Part B's gate
  (amx_attn_h256g4::shape_ok = head size 256 and kv_mul 4, applied per attention operation through amx_serves<geometry>) is
  not specific to Qwen3.5. google/gemma-4-E4B-it (public config: 8 query heads, 2 KV heads, head_dim 256, sliding window 512,
  35 sliding + 7 full layers, global_head_dim 512, num_kv_shared_layers 18) has that shape in its 35 sliding layers. E4B is
  on main AND on the model's branch (config/models.yaml gemma_4_e4b_it tp1/tp2/tp4 and gemma_4_e4b_it_permuted, tag test).
  Sliding layers always run in software (compute_operation_uses_hw requires no sliding window), so the generation tests
  t_generate_ingest_1_gemma_4_e4b_* reach the new kernels on an Intel host with AMX. Our builds held only qwen_3p5_4b
  (models.gdn.yaml), so E4B was NEVER built or run with Part B, and PR #5572's body does not name it. Not served: 512-wide
  layers, and the other Gemma 4 models (12B 16/8, 31B 32/16, 26B-A4B 16/8 at 256 = kv_mul 2). The bf16-activation half of the
  gate is unchecked for E4B (needs a build). E4B ingest weights are on 3b35:
  /opt/positron/weights/huggingface/positron-ai/google--gemma-4-E4B-it-ingest-best-gptq (also _promoted/...--2026-07-06).
  MEASURED 2026-11-22 23:28-23:55Z at 882e5322f1 (build tree /var/tmp/jhan/b35-gdn-e4b, model list
  exec/gdn-impl-20261121/models.e4b.yaml = Qwen3.5 4B + both E4B plugins; build.sh now takes REG=<model list>; scripts
  e4b-check.sh and e4b-tests.sh; results exec/results/gdn-e4b-20261122/{tokens/summary.txt,tests/summary.txt,rt,load}):
  (1) both E4B plugins COMPILE with Part B (749 s fresh build, AMX dispatch on). (2) runtron, 1 user, prompt 1024, 128
  tokens, temperature 0, --pay-for-determinism: tp4 and permuted read K tokens with AMX in exactly 35 layers (all but
  5,11,17,23,29,35,41 = the 512-wide full-attention layers, which stay AVX-512); kill switch gives 0 AMX layers. So the
  bf16 half of the gate holds for tp4 and perm_tp1. (3) Tokens: tp4 AMX on vs kill switch differ from generated token 63
  (65 of 128 equal); repeat of AMX on is identical; permuted on = off = repeat (128 of 128). Margin at token 63 NOT measured
  (logit-margin.sh could do it). (4) The 4 tests t_generate_ingest_1_gemma_4_e4b_{fpga,tp2_fpga,tp4_fpga,permuted_fpga}
  pass with AMX on and with the kill switch (178 assertions, 1 case, 0 skipped each) BUT they do not reach the AMX kernels:
  with TRON_ATTN_STATS=1 the tp4 test reads 600 K tokens per layer, all AVX-512, 0 AMX (the forced text has only 24 tokens:
  600 = (1+...+24) x 2 KV heads; TRON_BOOK_*_TOKENS=64 sizes the KV book, it is NOT the context limit - I first told jhan
  "the test limits its context to 64 tokens", corrected 2026-11-22; only whole 64-token pages inside the sliding window
  take AMX, is_dense_amx_page). I had told jhan "its generation tests take
  them too" - WRONG, corrected in the report. No repository test exercises the 256x4 kernels inside E4B. Single runs only:
  no performance claim (tp4 TTFT 0.361/0.367 s on vs 0.381 s off; 190.8/189.6 vs 188.0 tok/s). Load: socket0 42 % (user
  disagg), our app cores 0.0-0.1 %. DECIDED by jhan 2026-11-22: E4B stays in the Part B scope, shape-based gate.
- TEST-TIMING FILE (checked 2026-11-22): config/test-benchmarks.json has 4 machine blocks: genoa96 (AMD PR-CI class, 164
  tests), genoa32, granite_rapids_6960p, granite_rapids_6962p (159 tests). delphi-3b35 is a Xeon 6962P, so bin/slice bench
  --update there can only write the granite_rapids_6962p block; the genoa96 block needs an AMD worker (bin/slice bench
  --remote --remote-sku sku0 --update T reserves a whole pool worker - needs jhan's OK). A test without an entry is legal:
  slice runs it in its "unbenched phase". On main: t_gated_delta_net has a genoa96 entry only; t_amx_numerics and
  t_amx_dispatch_dtype have genoa96 and 6962p entries; t_gdn_stats and t_amx_gdn_numerics have none. Not verified: whether
  bench respects SYSTEM_CONFIG="--instance 1,2" on the shared host.
- DRAFT PR #5572 (https://github.com/positron-ai/tron/pull/5572), opened 2026-11-22 on jhan's "generate a draft PR": branch
  jhan-gdn-amx pushed, base = rbjarnason/qwen35-native-4b-registry (head branch of PR #3696), label "Skip benchmarks", no
  "Run CI" (repo AGENTS.md: descendants of a stack stay draft; Skip benchmarks on every PR; Run CI only on explicit request).
  Body = exec/gdn-impl-20261121/pr-body.md from gen_pr_body.py (PR-description skill; 1,973 words; compact table rows to fit
  the 2,000-word limit). Re-fetch the live body before any gh pr edit.
- CODE: worktree ~/workspace/ai-runs/tron-gdn-amx, branch jhan-gdn-amx = 3 commits on 72e1191804:
  0d69ef3ce8 counters (gdn_stats.hpp, TRON_GDN_STATS=1, [gdn-stats] exit lines, FUSE /model/<id>/gdn/),
  775bba7661 Part 0 + Part A in one commit (chain kernel gdn_recurrence_chain, executor advance(), AMX block kernel
  src/tron/kernels/amx_gdn.cpp, switch TRON_AMX_GDN_DISABLE=1), 882e5322f1 Part B (namespace amx_attn_h256g4).
  Branch jhan-gdn-amx-measured (aacdd287c0, local only) = the commits session 2 ran; the head differs only in comments,
  tests, commit messages, README.stats.md and README.ci.md. Backups jhan-gdn-amx-wip1..wip7 (local). Unit tests at head on
  3b35: 19 of 19 runs pass, plus a Debug build without TRON_AMX_DISPATCH (tag noamx: t_gated_delta_net 109,130 / 50);
  clang-format 19.1.7 (uvx --from clang-format==19.1.7), git diff --check and make lint-notes (on 3b35, needs ghcup) clean;
  fourmolu not run.
- PRE-PR CHECK (understand/pre-pr-check-result.json) open points, also in the PR body: default GCP Nix pipeline builds tests
  with TRON_AMX_DISPATCH off, so the AMX tests run only in the legacy cmake-single-platform.yml lane (repo test policy asks
  for jhan's explicit approval of tests that do not run in CI: NOT yet asked/answered); config/test-benchmarks.json not
  refreshed (bin/slice bench --update t_gated_delta_net t_amx_numerics); no changelog.d fragment (base older than the rule);
  jhan's own PR #5022 (kv_mul 16) changes the same kernel calls in self_attention.hpp; other qwen35 stack PRs change GDN code.
- MEASURED (session 2 = reps 11-13, 108 runs, 2026-11-22 00:13-01:17Z, medians of 3; our CPUs 0.0-0.1 % busy, other socket
  42.4-42.5 % busy): TTFT fall vs base run of the same session, measured [working prediction; range]:
  Part 0 9.0-14.1 % [14-23; 8-26], Part A 15.3-24.8 % [18-29; 11-32], Parts 0+B 14.9-32.3 % [24-37; 13-42],
  Parts A+B 25.2-39.0 % [30-41; 18-47]: all 24 inside the range, all below the working value. Part B alone (kill-switch
  pair p0->b) 0.8-23.0 %: below its range in 1 cell (8u p1024: 0.8 % vs 1.8-4.2 %; prefill join wait rose 3.3-3.8 ->
  7.6-12.1 ms with 8 users). Session 1 (reps 1-2, pre-review commits) agrees within 0.5 points.
  DECODE: Parts 0/A within 0.7 %; Part B +17.7/+22.6 % at 8u p4096/p8192 (prediction range max +7.8 %; decode attention
  busy 1.31-1.55x shorter with 8 users, ~45-49 % of the fall is a shorter join wait), -1 to +3 % elsewhere.
  GDN step (mean of 16 threads, 1u p1024): 6.08 -> 4.01 (Part 0) -> 2.56 us (Part A); median thread 6.39 / 4.23 / 2.70 us;
  work around the recurrence 1.56 us vs design 0.7-1.0 (the main miss of the prediction). Counters cost: not visible
  (-0.6 to +0.1 % decode, spread 0.3-1.2 %).
- NUMERICS FINDINGS: Part 0 bit-exact (unit tests) and same tokens at model level. Part B flips an EXACT bf16 tie at
  generated token 1 of the p1024 prompt (16.375 vs 16.375 -> 16.25; deterministic; same with the stand-alone Part B build;
  the tie stays with Part A and with Parts A+B).
  Part A: same tokens for 185 steps, scores drift during decode (same decode code in both arms) from <=1 bf16 step to up to
  10 steps, then a margin of 8 bf16 steps flips at token 185 - NOT a tie; open point for the GDN numerics contract.
  Score dump tool: exec/gdn-impl-20261121/logit-margin.sh + logit_summary.py (runtron --intermediates-file, 9.1 MB per
  token on local disk; keeps the "Top-k Logits of token N (320)" lines; results tokens/logits-*).
- BUG FOUND + FIXED: block kernel 5.5x slower for heads with small decays (subnormal decay products) -> MXCSR FTZ|DAZ scope
  in advance_value_head (TTFT 0.318-0.320 -> 0.292-0.295 s at 1u p1024).
- NOT DONE (listed on the page and in the PR): t_llama_unit probes for the 256 kernels, unit test that sets TRON_AMX_GDN_DISABLE, counters
  through generated plugin + forward pass, wall-clamp test, kernel-set type for the 3 dispatch branches, shared helpers
  between 128/256 kernels, faster 256 query pack; numerics contract not accepted by GDN owners; no human review.
- SCRIPTS: exec/gdn-impl-20261121/{build.sh, build-all.sh (CTR= PA= PAB=), campaign.sh (FIRST_REP/REPS/ARMS/CELLS),
  final-chain.sh, post-chain.sh, unit-tests.sh, token-check.sh, logit-margin.sh, bench/task{1,3,3_burst,4}.sh}. 3b35 build
  trees /var/tmp/jhan/b35-gdn-{ctr,pa,pab} are at the head commits.
- NEWS 2026-11-23 (jhan: "check slack chats with Runar, Ben and Bill"; update the handoffs; new handoff for "the numeric
  rounding issue"). Slack group chat C0CL3US5HAP 10:53-10:59 PST: GDN owner estimates PR #3696 "mid-to-late December"; advice
  "the AMX work can branch from main, and you can run Qwen3.5 4b end-to-end from the #3696 branch"; jhan answered "Yes, I will
  use this strategy"; heads-up on #3221 and on issue #5433 / draft PR #5571. jhan to me: "asked us to use its branch" - NOT the
  same as the advice; left OPEN as question Q4 of the split handoff (default = the model's branch; main holds only kernel-only
  files: no gdn_execution.hpp, no GDN code in model.hpp/TronCpp.hs, no caller, no model). DM to Bill 10:47: jhan merges PR #5022
  on approval (base of PR 4).
  STACK (verified): main f454423b09; 12 open PRs between main and #3696 (#3206 #5345 #3205 #3221 #5023 #5486 #5024 #3689 #3690
  #3692 #3694 #3695), lower 7 rewritten on main 2026-11-23, upper 5 + #3696 (72e1191804) still the 2026-11-17 commits; the
  model's branch holds an older copy of #3221; our commits apply cleanly only there (head of #3221: >= 12 conflict regions in
  5 files).
  ROUNDING: issue #5433 (GDN owner) = 22 bf16 rounding calls in the GDN host code; draft PR #5571 removes 14; six
  normalization roundings go "whatever the measurement says" - by our reading (NOT confirmed by the owner) incl. the rounding
  of the normalized product = K and Q. PART A NEEDS K AND Q AS bf16 VALUES: amx_gdn.cpp packs them with bf16_bits (upper 16
  bits) at 3 places (lines 258-262, 271-278), no check; unrounded input = truncation < 2^-7 toward zero; float64-model est.
  state diff ~3e-3 vs 5e-8..4e-7 measured today; t_amx_gdn_numerics.cpp rounds its own keys, so it would still pass. Part 0
  shares normalize_gdn/gdn_beta/gdn_decay with the token kernel; own copy of the value rounding at gated_delta_net.hpp:418.
  Options: O1 kernel rounds K,Q (18.5 tile products), O2 2/3 pieces (38.0 / 58.5), O3 layer rounds, O4 no block kernel.
  Same-binary gain of the block kernel (a vs a0, commit 8351e4ad52): TTFT fall 6.9-12.1 %.
  FILES: new task root ~/workspace/smaller-tasks/numeric-rounding/ (handoff-numeric-rounding-20261123.md, handoff-material/
  facts-{rounding,port,4444,method,parta-options,stack}.md, drafts/comment-4444-draft.md + comment-5433-draft.md, BOTH NOT
  POSTED). Split handoff updated (section 0 news, Q4 base, Q5 hold PR 3 until the rounding task reports = my view, default
  hold; old version kept as ...before-20261123.md). Checked by 5 + 2 agents (98 findings round 1, applied).
  ISSUE #4444: jhan asked "update our issue if you believe it is tightly related" -> my judgment: related through item 3
  (model-level TVD rule) only, NOT tightly -> nothing posted; draft kept. Related: #4600 (GDN owner, open) = the AVX-512
  truncation of P (cause 2 of #4444), still on main. Mean TVD per forced step from our records: qwen3-4b p1024 0.0053-0.0060,
  p8192 0.0000081, Glimmer 0.018.
  CORRECTIONS to this note: delphi-3b35 ran kernel 6.8.0-138 already on 2026-11-20..22 (load snapshots); it was rebooted
  2026-11-23 08:55 UTC (same kernel; /dev/hugepages held only slice-0..3 afterwards). The TTFT numbers of arms a/a0 are
  commit 8351e4ad52, arm p0 = aacdd287c0 + kill switch (not 775bba7661). pgrep -f inside ssh matches its own shell: use
  bracket patterns ('[r]untron|...').
- TRAPS learned: never run performance runs while builds run on CPUs 96-135 (false stalls); `cd X && ...` in the Bash tool or
  ssh prints a directory listing (use `cd X >/dev/null` once or absolute paths); ratios must be formed inside one run file;
  attention busy_cycles include the join wait; Monitor expires after 30 min (re-arm); a Bash background waiter lives 10 min.
