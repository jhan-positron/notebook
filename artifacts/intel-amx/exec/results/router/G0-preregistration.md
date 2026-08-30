# G0 pre-registration — router option (c), P0

Written 2026-08-23, BEFORE any P0 capture or microbenchmark run on delphi-3bda.
Executes `router/02-option-c-plan.md` sec 3 "Gate G0" (Sol round 1: gate on predicted
NET decode gain, not gross segment (a)). Nothing below may be changed after data
collection; deviations must be reported as deviations in `router/p0-trace.html`.

## Target production configurations

ingested-gpt-oss-20b-tp2 on delphi-3bda, production attention mode (`USE_HW_ATTN` unset),
decode: (1u, ctx 2048), (1u, ctx 8192), (8u, ctx 2048), (8u, ctx 8192).
gpt-oss-120b: only if the runnability check passes; 20b→120b arithmetic scaling is
reported as labeled sensitivity `est` only and does not decide G0 for 120b.

## Timestamp operationalization (7 boundaries, per MoE layer ℓ, per decode step s)

New markers (branch jhan-router-p0): "await deps <launcher>", "launch <launcher>",
"<kernel> first wait", "wait indices <buffer>", "start_reading <channel>" /
"start_writing <channel>" around every top-level blocking channel wait on the
driving thread (added pre-data, 2026-08-23, after header inspection showed the
main thread's logits wait was otherwise unmarked), plus label annotation on the
driver "Launch hardware matmul job" event. Existing: kernel_add_topk_softmax slices,
"build routing", "MoE matmul", "legacy/attn tx_launch" (labeled), "rx collecting
results" + Flow(request_id).

- T1 input-ready(ℓ,s): end of "await deps mlp_router_weight_launcher*" slice.
- T2 dispatch(ℓ,s): start of "launch mlp_router_weight_launcher*" slice (main thread).
  Hardware submission reported alongside: labeled tx_launch event for
  label=mlp_router_weight (TX worker), joined by flow id from the labeled
  "Launch hardware matmul job".
- T3 logits-ready(ℓ,s): primary = end of the RX completion (flow-joined "rx
  collecting results"/callback) for the router matmul's request_id. Fallback if
  flow join is not resolvable in trace_processor: max over workers of the end of
  the layer's topk-kernel "first wait" slice.
- T4/T5 topk start/end: the layer's kernel_add_topk_softmax slice bounds
  (per worker; start = min over workers, end = max).
- T6 routing done: end of "build routing" slice; "wait indices" slice reported
  separately (arrival wait not charged to build).
- T7 first expert-prepare start / hw-launch submission: start of the layer's first
  "MoE matmul" slice / first expert-labeled tx_launch submission.

Segments — AMENDED pre-data 2026-08-23 after header inspection (the generated
code puts a directly-measurable blocking wait on the driving thread:
"start_reading <logits channel>"):
- (a-stall), THE G0 VARIABLE: per layer, the duration of the driving thread's
  "start_reading <logits channel>" slice (its blocked time waiting for router
  logits). Rationale: the round trip T3 − T2 can overlap with other main-thread
  work; replacing an overlapped round trip with synchronous CPU compute can be
  a net loss. The stall is the serial cost actually paid, so the net-gain
  computation uses it. A(s) = Σ_ℓ stall(ℓ,s).
- (a-roundtrip) = T3 − T2, reported as the upper bound of removable latency
  (and for FPGA-team option-e pricing), never as the gate variable.
- Dispatch-side cost (fill/prepare/launch slice durations) reported separately;
  excluded from the gate (conservative: a CPU router would also save it).
- (b) = T7(submission) − T3, subdivided (logits→topk start, topk, wait-indices,
  build, prepare→submission). (c) = T7(submission) − T2.
  T2 − T1 (await deps) reported separately, never added to (a).

## Aggregation statistic and confidence interval

- Decode step boundaries: consecutive starts of layer-0 "launch
  mlp_router_weight_launcher" slices. Discard the first 8 decode steps (warmup)
  and any step overlapping prompt parsing.
- Per step: A(s) = Σ_ℓ (a-stall)(ℓ,s); T_step(s) = step wall time.
- CPU-router cost per step: C(s) = L × t_bench(arm*, N, M(s), regime), where
  L = 24 (20b), arm* = the best CPU arm available at that stage, regime = cyclic
  (primary) with disrupted as sensitivity row; t_bench = mean of 3 repetitions of
  the matching P0b cell; sensitivity row uses max of 3. Measured dispatch/sync
  overhead: the --workers 4 bench cell's barrier overhead is included when a
  parallel kernel is the candidate; single-core candidate adds none (synchronous
  call at the launch site).
- M(s): decode tokens per q_batch step = (Σ per-expert token counts from the
  "expert token counts" annotation)/4; distribution reported per config.
- Net gain fraction per step: g(s) = (A(s) − C(s)) / T_step(s).
- Statistic: mean of g(s) over retained steps; 95% CI by nonparametric bootstrap
  over steps (10,000 resamples, percentile method, fixed seed 20260823).

## Decision rules (pre-registered)

1. STOP if the upper 95% bound of mean g is < 1% in ALL four target configs.
   Segment (a) alone is reported as an upper bound, never as the go/no-go variable.
2. AMX candidacy (P0b, weighted by the measured M distribution, cyclic + disrupted
   regimes): AMX proceeds to P1b only if
   adv = t_bestAVX − t_AMX satisfies (upper 95% bound of adv) ≥ 0.10 × t_bestAVX
   OR L × adv ≥ 0.005 × median T_step. Otherwise P1a proceeds without AMX.
   P0b arm CIs: 3 repetitions per realistic-regime cell; CI from the t
   distribution on the 3 means (reported as a range if df too small for a stable
   interval — then rule 2 uses min/max bounds conservatively).
3. Otherwise both engines proceed through P1/P2; shipping decision is made by the
   integrated measurement (plan sec 3).

## DEVIATION (2026-08-23, post-capture — recorded, not silently patched)

The pre-registered (a-stall) slice ("start_reading <logits channel>") measured
0.3 us/layer. Post-capture consistency checking exposed that the driving
thread's router-chain block lands ONE statement later, at
"start_reading topk_snd_channel" (measured 19.4 us/layer at 1u, 32.6 at 8u,
gpt-oss-20b): the slot-level logits read returns immediately, and the thread
then blocks waiting for the topk OUTPUT, whose critical input is the router
round trip. The pre-registered variable therefore under-measured the removable
serial cost. Both results are reported: the pre-registered computation
(STOP) and a corrected computation using
A_corr(s) = Σ_ℓ [stall_linear + stall_topk_read + wait_indices](ℓ,s),
with the CPU-world residual block R(s) modeled explicitly from the measured
helper kernel-entry latency (labeled est), including a maximally conservative
variant (CPU world saves nothing until helper entry). The corrected gate is
advisory until jhan endorses the deviation; the plan's consensus practice
applies.

ENDORSED by jhan 2026-08-24 (Sol consensus round: ENDORSE-DEVIATION,
exec/results/router/sol-deviation-review.md; decision package
router/G0-decision-package.md). Scope of the endorsement: 20b = G0 PROCEED in
P1a-spike-first order (explicitly NOT a P1b/AMX authorization); 120b = literal
non-STOP, conditional scope only — the 4-worker AMX point must not be used to
pass G0. Wording corrections adopted with the endorsement (documentation of
record; published g0-decision*.json numbers stay as decided):
- the alternate residual row is named "reduced-overlap sensitivity" (its
  formula misses the late-logits branch where top-k still executes after CPU
  completion — it is a sensitivity row, not a worst case);
- the primary corrected estimand is stall_topk_read ALONE; the adjacent
  0.3 us logits-read and 0.2 us wait-indices slices are not presumed removable
  until P1a shows they disappear (they are inside the published A_corr, an
  immaterial ~0.5 us/layer);
- independent recomputation (exec/r0-g0-recompute.py, session 7ff0b556):
  reproduced; a stricter per-layer residual clamp changes no verdict. The
  per-layer clamp applies PROSPECTIVELY as the residual treatment in the P1a
  pre-registration.
- data note: 7/5880 (20b u1/2K) and 8/216 (120b u1/2K) layer records lack
  helper_entry_off; they contribute to A but not to E; immaterial here,
  treated explicitly in the P1a pre-registration.

## Reporting commitments

- Per-config table: mean A, mean C, mean g with CI, decision; per-layer and
  all-layer distributions; M distribution; prefill capture reported descriptively
  (no gate). Raw traces + bench lines land in exec/results/router/.
