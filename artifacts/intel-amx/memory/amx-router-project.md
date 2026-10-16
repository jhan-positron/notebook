---
name: amx-router-project
description: "MoE router x AMX work item - verified tron router facts, options analysis, doc location"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7ff0b556-0b05-4866-ab4c-65aa8a3450bd
  modified: 2026-08-24T19:07:17.366Z
---

Spawned 2026-08-23 from input-2-ai/router-amx.md ("router matrix calculation is a good AMX use
case"). Root dir: ~/workspace/intel-AMX/router/. Deliverables:
router/01-router-amx-rampup.html (+ router/router_cost_model.py; card added to rampup/index.html)
and router/02-option-c-plan.md (execution plan, Sol round CLOSED 2026-08-23: ENDORSE-WITH-EDITS,
15 defects applied - key design decisions now IN THE PLAN: two-control switch design
(TRON_CPU_ROUTER = FPGA-vs-host runtime A/B with both weight representations in experimental
builds; TRON_AMX_ROUTER = AMX-vs-AVX engine only), G0 gates on predicted NET decode gain (95% CI
upper bound >= 1%; gross segment (a) is only an upper bound), P1a mixed host/device TP
generation needs a compile-and-run spike (host executor precedent is NOT proof), weight
source/dtype audit (incl gptq variants) is a P1a prerequisite, plumbing extraction waits for G0,
NEW risk row: CPU router competes with worker-0 expert-dispatch chain per Note [Expert matmuls]).
EXECUTION HANDED OFF 2026-08-23: peer session intel-amx-a3 (uds:/tmp/cc-socks/3102743.sock)
executes the plan starting with P0, per jhan; this session confirmed plan final + sent
coordination notes (worktree isolation, campaign guard, G0 pre-registration). jhan still
reviewing the rampup doc - plan amendments may follow.
G0 DECISION MADE 2026-08-23: jhan ENDORSED the gate-variable deviation (verbatim to
intel-amx-a3: "Endorse the gate-variable deviation"; relayed - recorded with that provenance
in the package header). 20b G0 CLOSED as deviation-endorsed PROCEED, P1a-spike-first; 120b
conditional scope only. P1a UNDERWAY by intel-amx-a3: pre-registration first (CPU-world
boundary markers, per-layer clamp, missing-record handling), then type-feasibility spike as
a HAND-EDIT of the generated 20b header in tron-router-p0 (no emitter change yet, so no
ingest-owner dependency; caveats sent: spike must cover the weight-loader path for the host
tensor, and the hand-edited header must never become a golden-generator baseline).
P1A RESULT (2026-08-24, intel-amx-a3): G-B NOT MET for the serialized CPU router on 20b -
best cell 1u/2K +0.81% [CI -0.22,+1.85], 8u cells losses; corrected G0 estimate SUPERSEDED
per pre-registration. Root causes MEASURED: perfetto tracing inflated P0 stalls ~2.5x
(untraced recoverable ~8us/layer 1u = ~4.8% gross, ~12us 8u; kernel 6.4/22us leaves <=1-2us
net at 1u, negative 8u); serialized placement adds rmsnorm-arrival wait (~14.6us, derived)
to the driving thread. Spike SUCCEEDED as feasibility proof (mixed host/device types, normal
loader, sentinel publish; block 19.7->0.36us/layer). My cross-check found 2 confirmed record
defects: "0.2% of step" = post-replacement residual mislabeled as round-trip cost; numerics
"instrument-invalid" overdrawn (control likely lacked --temperature 0 -s 42
--pay-for-determinism; retry in flight -> p1a-numerics2-verdict.txt). Sol P1a round
(exec/results/router/sol-p1a-review.md): negative result valid/robust; recommend ONE
tightly-bounded parallel-placement experiment (hard stops: Stage-1 1u/2K gate >=+1% CI>0,
one placement no sweep, cap n=6/arm, miss closes option c), option (e) handed off with
REPRICED inputs (NOT the traced 19-33us - use untraced ~8/12us), NO independent P1b,
close-now also defensible. G0 endorsement NOT undermined (causal correspondence confirmed;
magnitude superseded as pre-registered); dated addenda added to G0 package + p0-trace.
NUMERICS VERDICT (2026-08-24): gpt-oss-20b IS deterministic with --temperature 0 -s 42
--pay-for-determinism (OFF-vs-OFF token-identical; MoE does NOT break determinism - durable
fact; original P1a control lacked the flags, recorded deviation). OFF-vs-ON genuinely
diverges at token ~16/34 deterministic greedy: CPU-router logits flip one expert selection;
hypothesis = top-k near-tie flip; decided by P2 logits/expert-set pin with cutoff margins.
Trap re-confirmed: token extraction must use color-span (ANSI green chunks) NOT line diff -
a mid-stream [Load] log line produced a false "invalid-even-flagged" verdict first. All 7
Sol record corrections applied by peer; records final.
OPTION (C) CLOSED 2026-08-24: jhan declined the bounded-parallel experiment (terse "n" in the
rampup session to the authorize-vs-close question; interpretation stated and unchallenged).
No P1b, no P2 router pin; token-16 divergence stays a documented observation. tron-router-p0
= archived spike branch, no PR - but its tracer commits are REUSABLE for future perf work
(3b0234df6 + 3de009774: "await deps"/"launch"/"start_reading <channel>" blocking-wait slices
on generated launchers, driver launch labels, TRON_TRACE_GEN_FROM_PARSE prefill capture;
details p0-trace.html sec 6; caveat: tracing inflates stall measurements ~2.5x - never use
traced magnitudes as untraced payoff estimates). LIVE REMAINDER: option (e) card-side fusion handoff to FPGA
team - MUST use repriced untraced magnitudes (~8us/layer 1u, ~12us 8u) not traced 19-33us.
Project answer to input-2-ai/router-amx.md: router/AMX closed with honest negative - CPU
router nets <1% serialized, ~1-2% est parallel, below threshold; opportunity is card-side.
Decision trail: G0-decision-package.md -> P1A-decision-package.md (both carry dated records).
Package (with full history) at router/G0-decision-package.md (2026-08-23): P0 found
the pre-registered gate variable mis-specified (logits-read slice = 0.3us, nonblocking; real
driving-thread block = topk_snd read, 19.3/32.4us per layer 1u/8u 20b). Sol round:
ENDORSE-DEVIATION (operationalization error, not gate-shopping; full review saved at
exec/results/router/sol-deviation-review.md); verdicts 20b = PROCEED (P1a-spike-first, NOT
P1b/AMX authorization), 120b = literal non-STOP but conditional scope only (1u negative;
4-worker AMX est must not pass G0). Sol finding 8 (independent recomputation) DONE by this
session: exec/r0-g0-recompute.py - published numbers reproduced; one aggregation difference
root-caused (published residual clamp at config-mean level r0-g0.py:149-156 vs per-layer;
stricter per-layer variant changes no verdict, strengthens 20b). Rename to carry: the
alternate residual row = "reduced-overlap sensitivity" NOT "maximally conservative"; primary
corrected estimand = stall_topk_read alone. PROCESS SETTLED with intel-amx-a3 (2026-08-23):
g0-decision*.json stay FROZEN as published (decision basis; no retroactive regeneration);
r0-g0-recompute.py output = standing verification record; per-layer residual clamping goes
PROSPECTIVELY into the P1a analysis pre-registration. Peer's staged post-endorsement edits:
Sol wording corrections + sec-6 recomputation one-liner + helper_entry_off treatment note -
all held until jhan's G0 decision. RAMPUP DOC UPDATES QUEUED (held while jhan
reviews): sec 4 napkin table superseded by measured P0b (cyclic n=128 26.0us/layer = 2.4x
nominal L3 floor; AMX M-flat 6.55/26.1; license clocks avx_fp32 3.89 / avx_bf16 3.20 /
amx 3.59 GHz), sec 6 G0 outcome + deviation pointer, Note[Expert matmuls] paragraph scoped
by segment-(b) finding (expert dispatch 6-10us/layer, not the bottleneck at tp2 decode).
Related: [[amx-tron-softattn-project]] (attention branch; shared AMX plumbing only).

VERIFIED TRON FACTS (5-way survey + adversarial verification, 2026-08-23, tron main 1407f48dd):
- Two MoE router paths. Hand-written (mixtral_8x7b/8x22b via llama.hpp): router logits ON CPU -
  host fp32 tensor<n_experts,dim> gate (feed_forward.hpp:114), run_gate (feed_forward.hpp:474-494)
  -> tensor::matmul serialize=true = serial AVX dot() double loop on calling worker
  (tensor.hpp:387-406) + blocking gate_ready.wait(); topk = std::partial_sort
  (mixture_of_experts.hpp:306-321); softmax mode when n_shared_experts==0 else sigmoid.
- Ingest-generated (gpt-oss et al, models.yaml source: generated): router weight emitted
  dtensor_t<128,2880> = FPGA, because LoopyTron.hs:800-802 unconditionally promoteToDeviceMemory
  on every L.Matmul weight. Generated plugin headers live ONLY in build trees
  (gen_sst_round4_ingest/src/tron/h/tron/plugins/ingested_gpt_oss_{20b,120b}.hpp; no source-tree
  file). Per-layer sequence (120b hpp:2036-2110): CPU rmsnorm -> FPGA router mm (round trip) ->
  CPU helpers kernel_add_topk_softmax (bias + tron::topk_fixed<4> + softmax; worker 0 returns
  early) -> worker-0 build_moe_routing_from_indices<128,4> -> per-expert FPGA prepare_and_launch.
  Router bias is host fp32 tensor<128>.
- Note [Expert matmuls] (common.hpp:55-71): single-core matmul dispatch measured starving FPGA
  on gpt-oss-120b - same worker-0 chain the router feeds; fix was expert_dtensor_t TP1 policy.
- ONLY production CPU matmul in tron outside attention = the hand-written router gate. lm_head,
  QKV/O, expert FFNs all FPGA on tp1/2/4. Dense models: zero production CPU matmuls -> router
  AMX kernel serves nothing dense. tp2/tp4 map dtensor_t to tp2_min1k_tensor/tp4_min512_tensor
  (partitioned device types), only tp1/perm_tp1 use hardware::dtensor directly.
- Dims (HF config.json on disk, measured): gpt-oss-20b 24L/2880h/32E/top4/inter2880;
  120b 36L/2880h/128E/top4; mixtral 32L/4096h/8E/top2/inter14336. Router = 0.09%/0.37%/0.01% of
  MoE-block MACs -> LATENCY play (round-trip removal + earlier expert dispatch), not FLOPs.
  Router weights bf16: 720KB/layer, 25.3MB all-layer (120b) = L3-resident on 3bda.
  AMX tile fit clean: K=2880=90 pair-steps, N=128=8 col tiles; attention geometry gate
  irrelevant (router never touches self_attention.hpp).
- Router weight is SHARED across tokens/users -> cross-user M batching valid (unlike attention
  KV); framework already batches router over q_batch->items.

RECOMMENDATION (doc sec 6): option (c) independent increment on shared AMX plumbing; NOT (a)
graft into PR #3879, NOT (b) sequence behind gpt-oss attention kernels (no dependency; attention
gpt-oss support est ~0 production payoff per gptoss-estimate). P0 = perfetto trace of
ingested-gpt-oss decode on 3bda (red-slice per layer: router launch -> topk start -> routing ->
first expert launch; + decode M distribution) + standalone microbench M x 2880 x {32,128}, arms
AVX-fp32/AVX-bf16/AMX-bf16, L2/L3. Stop conditions: red slice <1% of decode step -> close item;
AVX within noise of AMX at measured M -> ship CPU router without AMX. Option (e) FPGA-side
fusion (logits return with existing DMA) named as non-AMX alternative - price with FPGA team
using same P0 trace. Open Qs: serialize=true correctness-vs-perf in run_gate; M distribution;
whether GPTQ builds quantize router weight on card.

Consensus CLOSED 2026-08-23: Sol round 1 ENDORSE-WITH-EDITS, 10 defects, ALL APPLIED verbatim.
Key Sol corrections to carry forward: (1) my AMX 6.9us was an INSTRUCTION bound missing the
common L3 weight-delivery floor (~10.9us both engines) - the M~4 AMX-vs-AVX crossover claim was
WITHDRAWN, crossover must be measured; (2) 25.3MB "L3-resident" downgraded to capacity-fit
(residency unmeasured, P0 needs warm cyclic + cache-disrupted arms); (3) the 73% FPGA-wait
number is a DIFFERENT channel - motivates measuring, proves nothing about the router round
trip; (4) delivery dependency: AMX plumbing lives on jhan-amx-p0 (PR #3879 open), router work
waits for it to land OR extracts plumbing as a prerequisite change; (5) FPGA-fusion option (e)
cannot just piggyback the o_proj DMA - router input is post-CPU-add+rmsnorm, card-side fusion
must move those too; (6) P0 trace decomposes in 3 segments (router-replaceable (a) vs
topk/routing/prepare (b) vs combined (c)) - stop condition keys on segment (a) <1%; router
matmul has NO perfetto span today, markers may need adding. Workflow facts cached in
wf_a3fb4cf7-311 journal (session 7ff0b556).
