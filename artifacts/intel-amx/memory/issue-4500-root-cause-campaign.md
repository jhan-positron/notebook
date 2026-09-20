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
NIGHT 2 RESUME 2026-09-19 13:41 UTC: l8b-levers (session ci-test-22) had finished its restore 13:39:56; I stopped the idle engines
(Option B, 0 requests/10 min, POST inference/down, slice files removed, 512 free) and relaunched; m3 decode-only traces work
(passes 10-: 38 decode passes, 11.5 MB, 9 burst passes of 288 gof_rodeo, Save K base 5.0 us/layer; the earlier passes-1- trace
held only 4 prefill passes: ~250k hw-wait spans per prefill pass filled ~100 MB in 2.3 s). Trace overhead catA ~9 % TPS (113.5 vs
124.9) -> compare traced arms only among themselves. ci-test-22 queues behind us (process gate: pgrep runtron|issue4500 campaign),
needs the WHOLE machine ~5 h after us (until ~20:00 UTC) and brings the engines + Bill's marker back itself -> leave engines DOWN.
FACT from ci-test-22: on this deployment rinzler truncates chat prompts above 4096 tokens for llama-3.1-8b (server counted 4096
for 8192-token requests; FUSE max_prompt_tokens 131072, cap is elsewhere).
RESULTS NIGHT 2 (2026-09-19 13:41-14:24 UTC, 123 runs total, campaign DONE ok; machine handed to ci-test-22 at 14:24):
- traces (catA, 38 decode passes, one per arm): Save K on main 4.6 -> 20.3 us/layer (tp2 8u), 5.4 -> 21.0 (tp4): +566 us/step serial (H1);
  busiest worker's Attention Pending 337 -> 742 us/pass (tp2), 540 -> 914 (tp4): the qk_group tail read (H3) +3.5 us per call in
  place (bench said +0.56); hw wait per worker 1015 -> 392 (tp2), 351 -> 264 (tp4): the card stops being the critical path;
  GOF drain on workers +1054 us per burst pass (+3.7 us/populate) but burst passes not slower in vnni (H2 hidden).
- perf: main thread LLC misses x2.6 (tp2) / x1.7 (tp4), L1/L2 unchanged; workers L1 +25 %, L2 +40 %; perf record: apply_page_range
  1.84 -> 4.44 %, run_joins 9.57 -> 3.65 %, store_k_block 0.05 -> 0.26 %, qk_vnni_128x4 0.04 % (dense AMX path absent), mwaitx 78 %.
- m1b (n=2): tp2 2u vnni-headoff +0.215 ms (-4.3 %, t 43.8) = CI tp2 loss & store prediction 0.20; tp2 4u +0.131 (-2.2 %, t 17.8);
  headoff = base; tp4 unresolved (sd 0.6-1.3 ms).
- VERDICT: root cause = VNNI per-token column layout in decode (64 lines/row paid 3x: main scatter store, workers' tail read,
  staging gather); exposure depends on launch phase (B<4 late -> store serial) and card step length (tp4 short -> worker chain
  critical). AMX kernel, rest of PR, card excluded. Fix idea (unmeasured): keep the incomplete 16-token block row-major, convert
  to VNNI when the block completes (prefill block store exists); mitigation: TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 for 2 users/engine.
- Page sec 8 filled (reading.html Night 2 block); traces/analysis.{json,md}; perf/ per arm; perf.data on 3bda /var/tmp/jhan/traces/issue4500-20260918.
- TRAP: trace overhead 9-12 % TPS and it amplifies the vnni delta (0.636 traced vs 0.148 untraced at tp2 8u) -> traces give structure, not size.
BLOCK m6 DONE 2026-09-19 18:40 UTC (exec/issue4500-20260918/m6.sh + m6_summarize.py; results .../m6/; rinzler on our half, 1 engine,
nightly client; base = installed nightly deb, target = ci-mimic target deb; n=2): tp2 2u target vs base -4.3 % (+0.235 ms) = CI cell
reproduced; kill switch +0.3 % (nothing); MIN_B=1: base +7.7 % (t -9.4), target +11.0 % (t -27); target+MIN_B=1 beats base as shipped
by +6.2 %; layout cost when both early +0.067 ms (-1.4 %). tp4 4u: target -13.4 % (+1.0 ms, sd 0.6); targetkill vs target +6.8 %
(t -3.4) -> AMX-side component at tp4 (also in runtron m1: vnnikill +8.1 % vs vnni at tp4, none at tp2): hypothesis = per-call AMX
prep (Q pack + tile bracket in apply_page_range) on the critical worker chain at tp4; test = headoff vs headoff+kill at tp4 +
turbostat per-core MHz. TRAP: rinzler writes alderaan.log into its cwd -> never cd into /opt/positron/bin (root-owned); use a
jhan-owned cwd (m6.sh uses /var/tmp/jhan/i4500m6-cwd). Engines left DOWN (02:45 UTC timer restores); ci-test-22 done for the day.
Codex design comparison (page sec 9): taken = manifest, A/A arm, second-order tail mechanism, both step estimators,
mod-4/16/64 analysis, row-major shadow copy as the selective gather test, rinzler SIGUSR1+TRACE_FILE tracing; ours adds
launch-phase switch (cheapest discriminator), kill-switch arm, sudo perf, early micro-benchmark, dense-AMX-never-runs fact.

**How to apply:** when 3bda is free, check exec/logs/issue4500-20260918.{status,log}; after m3 copy traces and run
trace_analyze.py here; regenerate the page (gen_design.py reads summary.json); comment on issue #4500 with the split.
Related: [[issue-4500-fpga-attention-vnni-tps]], [[fpga-path-under-vnni-k]], [[ci-mimic-20260918-campaign]], [[vnnied-k-in-place-project]].
