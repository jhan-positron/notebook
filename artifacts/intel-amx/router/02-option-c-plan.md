# Option (c) execution plan: CPU router for ingest-generated MoE models

> **CLOSED 2026-08-24 (jhan decision, after P0 + P1a).** The serialized CPU router measured
> +0.81% best-cell / losses at 8u (G-B not met); the bounded-parallel follow-on was declined
> (~+1-2% est ceiling). Decision trail: router/G0-decision-package.md ->
> router/P1A-decision-package.md. Remaining live item: option (e) card-side fusion handoff
> to the FPGA team with repriced inputs. This plan is retained as the execution record.

Written 2026-08-23. Companion to `router/01-router-amx-rampup.html` (Sol-reviewed; see its
sections 3-6 for the evidence base). This plan turns the recommendation into ordered,
gate-checked work items. Labels: `code` = verified directly in cited source; `meas` = existing
measurement artifact; `est` = computed or extrapolated estimate; `open` = unresolved question
paired with the check that resolves it. A precedent from a different executor or hand-written
path is supporting evidence, not `code` proof of mixed generated-TP feasibility.

## 1. Goal and non-goals

**Goal:** remove the per-MoE-layer FPGA router round trip from ingest-generated models
(gpt-oss-20b/120b) by computing router logits on the CPU, with AMX as the kernel engine if and
only if measurement justifies it over AVX-512.

**Success criteria (project Rule 4):**
- G-A: measured per-layer time of the router-replaceable segment (P0 segment (a)) is known,
  with the decode M distribution, before any integration work.
- G-B: on the predeclared primary production configurations, the selected CPU-router arm
  improves steady-state decode tok/s by at least the project threshold - recommended 1% versus
  FPGA baseline - with a 95% confidence interval excluding zero; it also passes the numerics
  gate and causes no material prefill or latency-tail regression.
- G-C: `TRON_CPU_ROUTER=off` matches the clean FPGA baseline within a predeclared noise bound
  (same standard as the attention project's T4 kill-switch check), and a generator golden test
  shows that a build with CPU-router generation disabled emits today's baseline code unchanged.

**Non-goals:**
- No changes to attention kernels, the attention geometry gate, or the KV cache.
- No gpt-oss QK/PV attention kernel work (that is a separate item; est ~0 production payoff,
  rampup doc sec 5).
- No mixtral hand-written-path gate optimization (option d; 0.01% of block MACs) unless it
  falls out for free from shared kernel code.
- No FPGA-side fusion work (option e) - but P0's trace is shared with the FPGA team so they can
  price it (rampup doc sec 6).

## 2. Prerequisite: where the AMX plumbing comes from (decision needed from jhan)

The reusable AMX plumbing (`available()`, `begin_region()/end_region()`, isolated `-mamx` TU,
cmake + kill-switch pattern) lives on `jhan-amx-p0` (PR #3879, open), not on main. Two ways to
base the router work:

| choice | mechanics | when it is right |
|---|---|---|
| **Wait for #3879** | branch from jhan-amx-p0 (or from main after it lands) | if #3879 review is expected to conclude soon |
| **Extract plumbing first** | small prerequisite PR: `amx_attn.cpp` detection/region code moved to a model-agnostic `amx_common` TU + iface; #3879 rebases on it | if #3879 will stay open a while, or reviewers prefer smaller pieces |

P0 needs neither choice (the microbenchmark is standalone; the trace needs no AMX). Decide the
intended base during P0, but do not perform router-driven plumbing extraction until G0 passes -
P0 may stop the project. **Recommended base after G0: extract the model-agnostic plumbing
first** if #3879 has not landed (it shrinks #3879 slightly and gives the router increment a
reviewable base of ~150 lines). The extraction may proceed earlier only if it is independently
justified as part of delivering or reviewing #3879.

## 3. P0 - measure (low code risk; one to two quiet slots on 3bda)

### P0a. Trace the router chain in real decode

1. **Span audit** (alpha, no machine time): establish distinct timestamps for router input
   ready, router dispatch/submission, logits ready on host, top-k start/end, routing-build
   completion, first expert-prepare start, and first expert hardware-launch submission. Add
   narrowly scoped markers where existing events do not provide these boundaries (separate
   timestamps - do not conflate logits readiness with top-k start, or `prepare_and_launch`
   entry with hardware-launch submission; otherwise scheduler wake-up / helper delay gets
   charged to the replaceable router matmul). Known today `code`: the topk kernel and routing
   have `TRACE_EVENT`s; the router matmul itself has none (rampup doc sec 3). Keep new markers
   behind the existing trace macros so production builds are unaffected.
2. **Capture** on delphi-3bda, quiet slot per standing authorization (verify CI done, rinzler
   cleanup policy, `campaign_guard_acquire` from `exec/lib-guard.sh`):
   - model: ingested-gpt-oss-20b tp2 (known runnable on 3bda `meas`, T4 shapes run).
     ingested-gpt-oss-120b `open`: verify weights present + executor/card fit on 3bda before
     scheduling its capture. If it is not runnable, report 20b as measured evidence for 20b
     only. An arithmetic N/layer extrapolation may be included as a labeled sensitivity
     estimate, but it must not be used to pass or fail G0 for 120b; 120b remains open until
     measured on a runnable production-equivalent system (FPGA launch, queueing, DMA,
     contention, and overlap do not scale linearly with N or layer count).
   - configs: decode 1u and 8u, ctx 2K and 8K; one prefill capture (8K prompt) for the prefill
     side of the story.
   - `USE_HW_ATTN` default (production attention mode) - the router question is orthogonal to
     software attention, and production mode is where the answer matters.
3. **Report** per layer and per decode step (per-layer and all-layer distributions):
   - (a) router dispatch/submission -> logits ready on host: the part a CPU router replaces;
     also report input-ready -> dispatch separately so prerequisite waiting is not
     misclassified as engine time;
   - (b) logits ready -> first expert hardware-launch submission, subdivided into
     logits-ready -> top-k start, top-k, routing build, and expert prepare: remains unless
     separately optimized;
   - (c) router dispatch/submission -> first expert hardware-launch submission;
   plus the decode M distribution (tokens per q_batch).
   Deliverable: `router/p0-trace.html` + raw in `exec/results/router/`.

### P0b. Standalone microbenchmark (no tron dependencies)

`router/bench_router_kernel.cpp`, amx_fused_bench pattern (plain g++, self-validating against a
scalar reference before timing):
- shapes: M x 2880 x {32, 128}, M in {1, 2, 4, 8, 16};
- arms: (1) AVX fp32-weight dot loop (mirrors current `tensor::matmul` inner path),
  (2) AVX-512 bf16-weight, (3) AMX bf16 with pre-packed VNNI B;
- cache regimes: L2-pinned single-layer, model-accurate cyclic-all-layer, and cache-disrupted.
  Use 24 layers x N=32 for 20b and 36 layers x N=128 for 120b, with arm-accurate fp32 or bf16
  byte sizes. Report capacity fit separately from observed cache-miss/bandwidth behavior; do
  not infer residency from aggregate L3 capacity (rampup doc sec 4, Sol round-1 correction);
- record license-clock effect (AMX arm core frequency vs AVX arm, per attention-project
  method `meas` 3.59 vs 3.89 GHz single-core);
- 1 core first; one multi-core split point (e.g. 4 workers over N) to bound the parallel
  option.

### Gate G0 (stop/go, pre-registered)

- For each decode configuration, compute the predicted net CPU-router gain as the measured
  all-layer contribution of segment (a), minus the P0b CPU-router time at that configuration's
  measured M distribution and realistic cache regime, including measured
  dispatch/synchronization overhead where available. Predeclare the aggregation statistic and
  confidence interval. If the upper 95% confidence bound of predicted net decode-step
  improvement is below 1% for all target production configurations: **stop**. Write the numbers
  into the rampup doc, close the item, hand the trace to the FPGA team (option e pricing) and
  to the Note [Expert matmuls] owners (segment (b) evidence). Segment (a) alone is reported as
  an upper bound, not the go/no-go variable.
- Weight AVX and AMX P0b results by the measured decode M distribution and the realistic
  warm-all-layer / cache-disrupted regimes. If AMX's upper 95% confidence bound does not exceed
  AVX by a predeclared practical threshold - recommended: 10% of router-kernel time or 0.5% of
  predicted decode-step time - **proceed with P1a and defer P1b**.
- Otherwise retain both engines through P2. Ship AMX only if the integrated host-AMX arm beats
  host-AVX by the predeclared decode threshold without a regression in surrounding CPU
  segments, FPGA utilization, or prefill (P0b decides candidacy; integrated P1/P2 measurement
  makes the final shipping decision - AMX license-clock effects can touch surrounding CPU
  work).

## 4. P1 - prototype behind switches

Two sub-increments, mirroring P0's decomposition, so the round-trip win and the engine win are
measured separately:

### P1a. Host-router prototype: placement/type selection plus existing fp32 CPU matmul

- **Ingest change** (Haskell): stop promoting the router gate matmul's weight to device.
  Today `LoopyTron.hs:800-802` (`translateStmt' L.Matmul`) unconditionally calls
  `promoteToDeviceMemory`. Options `open` (pick with ingest owners):
  - (i) explicit marker: the frontend already knows the router context
    (`FxFx.hs isMoeRouterBody`, MoeRouter lowering in `TypedFxBulk.hs`) - tag the gate matmul
    statement and skip promotion; most precise;
  - (ii) heuristic: skip promotion when the output feeds only a TopK kernel; no frontend
    change but implicit.
- **Type feasibility has supporting precedent but is not yet proven for mixed TP generation**
  `open`: host executors demonstrate that the generated fill/prepare/launch abstractions have
  host-tensor instantiations when the whole executor is host-typed, and the hand-written path
  demonstrates a host fp32 router weight multiplying bf16 DMA activation views
  (feed_forward.hpp:486-492). Neither proves that a TP-generated executor may make only the
  router matmul host-typed while retaining device types elsewhere. Before estimating P1a as a
  placement-only change, add a compile-and-run spike covering generated type selection, weight
  visitation/loading, launcher selection, latch/channel behavior, and mixed `is_host`
  assumptions (common.hpp:228). If that spike requires emitter or launcher specialization,
  count it explicitly as P1a integration work rather than "already proven".
- **Weight source and conversion audit before P1a** `open`: inspect the router tensors in
  every target gpt-oss checkpoint variant, including `*-ingest-best-gptq`; record safetensors
  dtype, current ingest conversion/dequantization, device representation, and loader support
  for a host fp32 copy. Define the exact fp32 and bf16 values used by the FPGA, AVX, and AMX
  references before numerics baselines are recorded. (Prototype weight dtype: fp32 host tensor,
  same as the hand-written path; 1.44 MB/layer for 120b vs 720 KB bf16 `est` - acceptable for a
  prototype; bf16/VNNI host weight arrives with P1b.)
- **Execution semantics** `open`: verify in the generated TP output that the host router
  selects the synchronous host `tensor::matmul` launcher (tensor.hpp:387-406; the generated
  launch site sits right after `kernel_add_add_rmsnorm`), consumes the post-rmsnorm bf16 DMA
  views only after they are ready, publishes logits with the existing channel/latch contract,
  and does not alter downstream top-k ordering. Then A/B `serialize=true` against the existing
  TBB path; do not assume the hand-written path's serialization choice transfers unchanged to
  generated gpt-oss (its rationale - correctness vs tiny-N overhead - is itself `open`).
- **CPU scheduling and FPGA-feed check:** measure worker-0 occupancy, logits-ready ->
  first-expert-launch time, helper utilization, FPGA idle/starvation intervals, and end-to-end
  decode for serialized and selected parallel CPU-router configurations. Pin allocation and
  execution to the model's NUMA socket. Reject a kernel configuration that wins standalone but
  increases segment (b), starves expert launches (the Note [Expert matmuls] failure mode -
  the CPU router lands on the same worker-0 chain), or interferes with other in-flight batches
  enough to erase the net gain.
- **Two distinct controls:**
  1. a runtime `TRON_CPU_ROUTER` control selects the existing FPGA router or the host router;
     experimental A/B builds retain both the device router weight/path and a host router
     representation so FPGA-vs-host comparisons are same-binary;
  2. `TRON_AMX_ROUTER` selects AMX or AVX/fp32 only after the host router is selected.
  `TRON_CPU_ROUTER=off` must match the clean FPGA baseline within a predeclared noise bound.
  Separately, retain a generator golden test showing that a build with CPU-router generation
  disabled emits today's baseline code unchanged. Do not call runtime-disabled output
  "byte-for-byte" equivalent.
- **Measure**: same-binary A/B (`TRON_CPU_ROUTER` on/off), decode 1u/8u x 2K/8K,
  ingested-gpt-oss-20b. This isolates the round-trip effect with no new kernel.

### P1b. AMX router kernel (engine win; requires plumbing base per sec 2)

- New kernel in the AMX TU family: `router_logits_MxK_N` - A = M x 2880 bf16 activations
  (pad rows to tile height), B = pre-packed VNNI bf16 router weight (packed once at weight
  load; constant thereafter - no mirror-style coherence problem), C = M x N fp32 logits;
  bias add stays in the existing topk kernel (it also handles the fp32->comparison layout).
- Dispatch: `available()` + M/residency threshold from P0b; AVX-512 bf16 fallback arm from
  P0b if it earned its place; fp32 dot loop as the always-there fallback.
- **Representation lifecycle:** retain the canonical fp32 host weight required by the
  always-available fallback and derive the packed bf16/VNNI representation once during model
  load. Allocate and first-touch both on the executor's NUMA socket; validate alignment and
  packed-buffer size; include conversion/packing numerics in tests. If allocation, conversion,
  AMX permission, or validation fails, continue with fp32 without leaving a partially enabled
  AMX path. Report the combined fp32-plus-packed all-layer footprint as capacity fit, not
  cache residency.
- **Engine kill switch:** `TRON_AMX_ROUTER=off` forces the host AVX/fp32 implementation; it
  does not restore the FPGA path. `TRON_CPU_ROUTER=off` is the independent full fallback to
  today's FPGA router. Both separate from the attention toggles so the two projects A/B
  independently.
- Tile-config note `code`: router kernel uses the same max-shape config as attention today;
  if gpt-oss attention kernels later introduce shape-selected configs, same-thread mixing
  must re-issue `LDTILECFG` (rampup doc sec 5 interaction point).
- Weight source dtypes: covered by the P1a-prerequisite audit (sec 4) - P1b consumes its
  result to define the exact bf16 values the VNNI pack produces.

## 5. P2 - A/B, numerics, tests, packaging

- **A/B campaign** (3bda, campaign guard): predeclare the primary configurations,
  warm-up/discard policy, run ordering, sample count determined by variance rather than a
  fixed minimum, confidence-interval method, decode throughput metric, latency-tail metrics,
  and prefill no-regression threshold. Arms = FPGA baseline / host-AVX / host-AMX, using the
  two-control same-binary design (P1a); decode 1u/8u x 2K/8K + prefill 8K;
  ingested-gpt-oss-20b (and 120b if P0 verified it runnable). Secondary shape:
  ingested-mixtral-8x7b (generated MoE, N=8 - expect ~0 `est`; it is the no-regression
  control).
- **Numerics** (per rampup doc sec 6 P2, Sol-corrected): compare router logits vs the
  device-matmul reference; record rank-k vs rank-(k+1) cutoff margins; require exact
  expert-set agreement away from a pre-declared near-tie tolerance; T1 treatment for
  cutoff-near-tie flips. Test file per `t_amx_numerics.cpp` pattern.
- **Fallback and lifecycle tests:** CPUID/XCR0 unsupported, `ARCH_REQ_XCOMP_PERM` denied, AMX
  disabled by environment, packed-buffer allocation/conversion failure, `TRON_AMX_ROUTER=off`
  selecting host AVX/fp32, and `TRON_CPU_ROUTER=off` selecting the existing FPGA path. Cover
  M={1,2,4,8,16} plus the maximum supported runtime M and partial-tile tails; N={32,128}, and
  N=8 only if generated mixtral remains in scope. Verify repeated model load/unload, NUMA
  placement, concurrent executor/thread use, host-executor build, and generator golden output
  with CPU-router generation disabled.
- **Notes convention**: add source Notes at the ingest placement decision and the kernel
  (`Note [Router weight placement]`, `Note [Router logits on CPU]`), See-refs from the
  generated-code emitter; `make lint-notes`.
- **Docs**: results page `router/p2-ab.html`; rampup doc sec 4/6 updated with measured
  numbers replacing est pills; consensus rounds logged.

## 6. Dependencies, risks, open questions

| item | type | resolution |
|---|---|---|
| plumbing base (sec 2) | decision (jhan) | pick wait-for-#3879 vs extract-first |
| ingest change ownership | dependency | Haskell emitter change needs ingest-owner review; scope with them before P1a |
| segment (a) magnitude | open (the deciding number) | P0a |
| decode M distribution | open | P0a |
| AMX-vs-AVX crossover in M | open (napkin model cannot decide - common L3 floor, Sol round 1) | P0b candidacy; integrated P1/P2 measurement makes the shipping decision |
| Real cache delivery of host router weights under runtime traffic | open | P0b bounds L2/warm-all-layer/disrupted behavior; P1a/P2 collect runtime cache/bandwidth counters. P0a alone cannot establish host-weight residency because the baseline router weight is device-resident |
| CPU router competes with single-core expert dispatch/helpers (Note [Expert matmuls] failure mode) | risk | P1a/P2 segmented traces + FPGA-utilization counters; A/B serialized and bounded-parallel implementations under real concurrency |
| 120b runnable on 3bda | open | check weights + executor fit before P0a capture |
| `serialize=true` rationale in run_gate | open | ask author / A/B in P1a |
| router weight source dtype/conversion (incl. gptq variants) | open | safetensors dtype + loader audit, prerequisite to P1a (sec 4) |
| mixed host/device generated-TP feasibility | open | P1a compile-and-run spike (sec 4) |
| mixed host/device weight assumptions in tp executors | risk | P1a compile + host-executor tests; grep `is_host` uses |
| FPGA team option-e pricing | parallel, non-blocking | hand over P0a trace |

## 7. Effort and sequencing (est)

```
P0a span audit + markers        1 day (alpha)          --+
P0b microbenchmark              1-2 days (alpha + 3bda)   |-- G0 gate: stop / AVX-only / full
P0a capture + report            1 quiet slot (3bda)     --+
P1a ingest placement + A/B      2-3 days + 1 slot       -- isolates round-trip win
P1b AMX kernel + pack + tests   3-5 days + 1 slot       -- isolates engine win (needs sec-2 base)
P2 campaign + numerics + docs   2-3 days + 1-2 slots
```

After G0, P1a may begin independently of the plumbing extraction (P1a needs no AMX). The
extraction and P1b kernel development may run in parallel with P1a where ownership permits, but
integrated P1b measurement waits for the P1a host path and weight lifecycle.

Total est: ~2 weeks elapsed with 3bda quiet-slot cadence; P0 alone answers whether the rest
happens. All numbers est until G0.

## 8. Consensus log

- 2026-08-23: draft v1. Sol round 1 - ENDORSE-WITH-EDITS, 15 defects, ALL APPLIED with Sol's
  wording. Key corrections: P1a "type feasibility proven" downgraded to precedent + a
  compile-and-run spike (host executor proves all-host instantiation, not mixed host/device TP
  generation); switch design split into two controls (`TRON_CPU_ROUTER` FPGA-vs-host runtime
  A/B with both representations in experimental builds, `TRON_AMX_ROUTER` engine-only) since
  one switch cannot give byte-identical OFF output, same-binary A/B, and device-weight removal
  at once; G0 re-based on predicted NET decode gain (segment (a) minus P0b CPU cost at
  measured M, 95% CI) instead of gross segment (a); AVX-vs-AMX criterion operationalized
  (10% router-kernel time or 0.5% decode-step; P0b decides candidacy, integrated P2 decides
  shipping); 20b->120b arithmetic scaling barred from deciding G0 for 120b; trace boundaries
  split (input-ready vs dispatch vs logits-ready vs hw-launch submission); weight
  source/dtype audit moved to a P1a prerequisite; cache regimes made model/dtype-accurate;
  NEW risk added - CPU router competes with the worker-0 expert-dispatch chain (Note [Expert
  matmuls] failure mode) with a P1a scheduling/FPGA-feed check; representation lifecycle
  (canonical fp32 + derived VNNI pack, NUMA first-touch, fail-soft) specified;
  plumbing extraction deferred until after G0; G-B/A-B given predeclared statistical
  thresholds; fallback matrix expanded (perm-denial, pack failure, M tails, load/unload,
  golden generator output); `code` label defined. Consensus CLOSED (edits applied verbatim,
  per project practice).
