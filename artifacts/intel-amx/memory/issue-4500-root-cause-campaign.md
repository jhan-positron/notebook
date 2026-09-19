---
name: issue-4500-root-cause-campaign
description: "2026-09-18 root-cause design + campaign for issue #4500 (qwen-3-4b FPGA-attention decode TPS loss under VNNI K): verified decode-step facts, micro-benchmark numbers, the design page issue4500/root-cause-debug.html, scripts exec/issue4500-20260918/, campaign state and blocker"
metadata: 
  node_type: memory
  type: project
  originSessionId: 65d0ce4e-a16a-4f49-ace2-6f1e986914d2
  modified: 2026-09-18T21:59:54.154Z
---

Request (jhan 2026-09-18 ~20:50 UTC, ultracode): design how to find the root cause of issue #4500, compare with the
codex design (codex/design/root-cause-tracing.html), write the final design to VNNIed-K-in-place/issue4500/root-cause-debug.html
(generator exec/issue4500-20260918/gen_design.py), execute it on 3bda.

VERIFIED decode-step facts (16-agent read+verify, PR head 30c4ac82cb, base c7844ca2ce):
- Only 3 operations differ on the FPGA-attention decode path: (1) K store scatter_row on the MAIN thread every step
  (64 partial-line writes per row vs 4 whole lines; never shared with helpers below 17 items) [model.hpp:2806-2814, 3040];
  (2) gof::populate gather_row (64 lines per row) once per GOF = every 4th token per user, on attention workers via
  help_drain_gof(4) at the start of the NEXT layer or on main in wait_coop_gof after the last layer [model.hpp:3146-3189];
  (3) tail scoring qk_group (64 masked line loads per 16-token block, any live count) vs dotter (4 lines per token) on
  workers in the pending section [self_attention.hpp:1604-1641]. Card bytes identical; AMX dense kernel NEVER runs in
  FPGA decode (tail page never dense) -> no read gain to offset the store (explains why CPU-attention runs net positive).
- Launch phase: B >= TRON_HWATTN_EARLY_LAUNCH_MIN_B (default 4, env read at run time, model.hpp:107-128) launches the card
  BEFORE Save K/V (early); B < 4 saves first (late) -> CI tp2 (2 users/engine) has the store fully serial.
- Engagement point 127 gates QUERY positions, not keys; CPU scores only the tail after the last DMA-complete GOF.
- populate never gates the same step's launch; DMA completion is polled once per forward at its start.
- runtron -u 8 = 8 distinct prompts of equal length -> all users complete a GOF on the same step (288 populates every 4th step).
- Budget: loss per step runtron tp2 +0.18 ms, tp4 +0.80-0.83, CI tp2 +0.285 (16 rows/layer), CI tp4 +0.825 (32 rows);
  NOT proportional to rows (79-716 ns/row) -> exposure matters. tp4 runtron base is bimodal (7.4 vs 8.5 ms steps).

MICRO-BENCHMARK (exec/issue4500-20260918/bench/, results exec/results/issue4500-20260918/bench/bench.txt, 3bda cores 87/88,
decode-like main-store/worker-read alternation, 2304 planes = 36 MiB): store 389 vs 34 ns/row (+355, flat vs working set,
with/without worker); tail 1 live token x 4 heads: qk_group 628 vs dotter 70 ns (+558); staging gather 83 vs 20 ns (+64).
-> store alone predicts 0.81 ms/step at 8 users (98 % of the runtron tp4 loss; only 49 % of CI tp4 at 4 users/engine), 0.20 ms at 2 users (71 % of CI tp2). Bimodal tp4 data = wedperf base eb2de0265a + mid c7844ca2ce (headoff never ran there).

CAMPAIGN exec/issue4500-20260918/campaign.sh (relaunched 22:2x UTC in WAIT mode after a 37-finding page review; blocks m1 attribution
5 arms x tp2/tp4 x 8u x3, m2 launch-phase knob MIN_B=1/100 x users 2/8 x REPS_M2=3, m3 perfetto traces catA/catB all passes gen 40,
m4 sudo perf record FIRST then counters, gen 4096, m1b users 2/4 x2; summarize.py pairs vs base/headoff/vnni + m2 criterion
D = (vnni-headoff)@late - @early with paired t); arms base=main0916, headoff=headoff0916 (ff680c8020 VNNI OFF), vnni=pr4424, vnni2 A/A, vnnikill,
head30=tilec. summarize.py, trace_analyze.py (python TraceProcessor: claude-agentsrv only). Results exec/results/issue4500-20260918/.
COORDINATION 22:1x UTC: session pr1-58 (canonical-AMX deb nightly-phase replica, whole machine, ~22:40-00:30 UTC, holds the
flock) goes first (jhan: "give machine to it first"); its handoff = nightly deb reinstalled + engines down + slice files removed +
flock released = my start condition -> my campaign starts by itself ~00:30 UTC, stops at the 01:40 hold (m1 + most of m2), resumes
after the nightly (~13:20 UTC Sat) for m3/m4/m1b. jhan authorized "Option B" (I may run the take-down recipe myself: journal idle
check, POST /api/inference/down, rm positron slice files) for this campaign incl. the resume.
HANDOFF 2026-09-19 00:22:03 UTC (pr1-58 done): my campaign started m1 at 00:22:16 UTC (base tp2 rep1 124.87 TPS; ~46 s per run).
pr1-58 RESULT (canon-ci-20260918, canonical AMX deb = main 3faba6d0fd + deb preset, NO PR 4424, whole machine CI layout):
qwen-3-4b tp2 +0.1 % (186.25 vs 186.13), tp4 -2.6 % (146.05 vs 149.94, inside the night-to-night band), 10.5 G AMX-busy cycles
on tp2 -> the -5/-11 % of issue #4500 is the PR 4424 layout, not the AMX kernel (cite in the page and the issue).
BLOCKER (before the coordination): the l8bload campaign's restore (21:07 UTC) left 4 idle positron gemma-4-31b engines on ALL cards (512 hugepages);
the classifier refused the platformd take-down in my script -> campaign waits for units inactive + 256 free hugepages;
operator recipe in launch.sh (journal idle check, POST /api/inference/down, rm slice files). ci-runner-stop timer 02:45 UTC
brings serving back; pre-CI hold 01:40-03:45 UTC stops the campaign.

RESULTS NIGHT 1 (2026-09-19 00:22-01:40 UTC, 81 runs, m1 + m2 complete, m3 1 trace (base tp2 catA), m4/m1b/rest of m3 pending):
- tp2 8u: vnni vs headoff +0.148 ms/step (-1.8 %, t +10.2); headoff vs base +0.006 (t 0.2) -> H6 excluded; vnnikill vs vnni +0.029
  (t 2.3, unresolved) -> AMX kernel excluded; vnni2 vs vnni -0.004 (A/A clean); head30 vs vnni -0.05 (1 run, +0.6 %).
- m2 tp2: forced late launch: vnni-headoff = +0.810 ms/step at 8u (= store prediction 0.81!), +0.176 at 2u (pred 0.20);
  forced early: +0.229 (8u), +0.043 (2u). D = late-early = +0.582 (t +19.7) / +0.133 (t +6.1) -> H1 (main-thread scatter store)
  CONFIRMED as the exposed cost at tp2. Side finding: MIN_B=1 at 2 users speeds headoff itself +4.3 % TPS (t -8) -> CI-layout lever.
- tp4: bimodal per-run state (base 7.06-7.83 ms/step, sd 7 TPS); vnni vs headoff +1.40 ms (-15.8 %, t 2.8 unresolved); A/A not
  clean (vnni2-vnni -0.51 ms); m2 D unresolved -> needs m3 traces (fast vs slow run) + m4.
- summary: exec/results/issue4500-20260918/summary.md; page sec 8 filled (reading.html in the results dir is included by gen_design.py).
Codex design comparison (page sec 9): taken = manifest, A/A arm, second-order tail mechanism, both step estimators,
mod-4/16/64 analysis, row-major shadow copy as the selective gather test, rinzler SIGUSR1+TRACE_FILE tracing; ours adds
launch-phase switch (cheapest discriminator), kill-switch arm, sudo perf, early micro-benchmark, dense-AMX-never-runs fact.

**How to apply:** when 3bda is free, check exec/logs/issue4500-20260918.{status,log}; after m3 copy traces and run
trace_analyze.py here; regenerate the page (gen_design.py reads summary.json); comment on issue #4500 with the split.
Related: [[issue-4500-fpga-attention-vnni-tps]], [[fpga-path-under-vnni-k]], [[ci-mimic-20260918-campaign]], [[vnnied-k-in-place-project]].
