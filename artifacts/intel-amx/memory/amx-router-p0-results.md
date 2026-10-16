---
name: amx-router-p0-results
description: "Router option (c) CLOSED 2026-08-24 (P1a G-B miss, parallel variant declined); measured facts + reusable methodology lessons"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8ec4ebec-ac50-40e4-a3d4-befac2716040
  modified: 2026-08-23T23:09:44.534Z
---

CLOSED 2026-08-24: jhan declined the bounded-parallel experiment after the Sol-reviewed
decision package (router/P1A-decision-package.md); option (c) closed, P1b dead, P2 router
numerics pin dead (token-16 divergence = documented observation, near-tie hypothesis,
uninvestigated). tron-router-p0 = archived spike branch, NO PR (contains the marker patch
+ TRON_TRACE_GEN_FROM_PARSE, commits 3b0234df6/3de009774 - reusable if tracing work recurs).
Live handoff owned by jhan: option (e) FPGA-team pricing from REPRICED untraced magnitudes
(~8us/layer 1u, ~12us 8u), NOT the traced 19.7/32.9us.

P1A FINAL (2026-08-24): jhan endorsed the deviation; spike executed (dual-member hand-edit
of the generated header via exec/r0-p1a-patch-header.py; feasibility PROVEN: loader/latch/
mixed types all work; stall collapses 19.7->0.36us/layer). Integrated A/B (avx_bf16 arm,
n=6/arm): +0.81% / -0.03% / -2.30% / -1.77% -> G-B NOT MET; corrected G0 estimate
superseded per pre-registration. GENERAL FACTS worth reuse: (1) perfetto tracing inflates
channel-wait magnitudes ~2.5x on this workload (untraced 254 vs traced-implied 206 tok/s
at 1u/2K) - never gate on traced stall magnitudes without an untraced A/B; (2) CORRECTED
2026-08-24: runtron IS seed-reproducible INCLUDING gpt-oss MoE, but ONLY with the full
recipe --temperature 0 -s 42 --pay-for-determinism (bare --seed 42 is NOT enough; also
compare via color-span token extraction - interleaved log lines poison line diffs).
With the valid instrument, CPU-vs-FPGA router logits genuinely flip a token by ~position
16 (near-tie hypothesis; P2 logits pin decides); (3) a synchronous host op at
a generated launch site inherits the activation ARRIVAL wait on the driving thread (async
launchers park it on the TX worker). Open options for jhan: bounded-parallel router
(~+1-2% upper est), P1b AMX at 8u (with parallel placement only), option (e), or close
option (c). Records: router/p1a-spike.html, P1A-preregistration.md OUTCOME section.

Router option-(c) P0 executed 2026-08-23 (session intel-amx-a3), gpt-oss on delphi-3bda tp2.
Full report: router/p0-trace.html; status: router/status-report/index.html; raw:
exec/results/router/. Related: [[amx-router-project]], [[delphi-3bda-hardware]].

MEASURED FACTS (survive across sessions):
- The FPGA router round trip is ~19-22us (1u) / 34-36us (8u) per MoE layer; the driving
  thread's serial block for it lands at `start_reading topk_snd_channel` (19.3/32.4 us per
  layer for 20b), NOT at the logits-channel read (0.3us - slot latch satisfied early).
  Any future channel-wait analysis must look at the CONSUMER-OUTPUT read, not the data read.
- Pre-registered G0 said STOP (variable mis-specified); corrected gate: 20b PROCEED-eligible
  all 4 decode configs (+2.6..+5.4% net est); 120b only 8u/2K positive single-core; 4-worker
  AMX kernel (8.49us/layer n=128) makes 120b viable est. Deviation awaiting jhan endorsement.
- P0b on 6962P: AMX router kernel is M-flat (n=32: 6.55us, n=128: 26.0us cyclic); AVX-512
  bf16 ties AMX only at M=1 n=32; fp32 arm 2x bf16. Real cyclic L3 delivery = 2.4x the
  25B/cycle napkin floor. Same-socket streaming disruptor changes nothing (<=1%).
  License clocks 1-core: avx fp32 3.89 GHz, avx bf16 3.20 (!), amx 3.59.
- gpt-oss-120b-tp2 RUNS on 3bda (128 hugepages, 178.6 tok/s decode 1u/2K).
- Decode T_step: 20b 4.85/5.51/11.4/16.1 ms; 120b 8.0/8.1/19.7/25.7 ms (1u2K/1u8K/8u2K/8u8K).
- Perfetto: --trace-gen runs under a 5s in-process cap (perf.cpp perfetto_duration_ms) that
  starts at prompt-parse completion; whole-run --trace cannot capture prefill (cap expires
  during model load). TRON_TRACE_GEN_FROM_PARSE=1 (commit 3de009774, jhan-router-p0) starts
  the phased trace at parse begin with no cap. 120b traces truncate (ring buffer) to
  ~6-166 steps/config.
SOL DEVIATION REVIEW (2026-08-23/24, via intel-amx-3d; exec/results/router/
sol-deviation-review.md; decision package router/G0-decision-package.md, AWAITING jhan):
ENDORSE-DEVIATION. 20b = PROCEED, P1a-spike-first order, explicitly NOT a P1b/AMX
authorization. 120b = conditional scope only; the 4-worker AMX point must NOT be used to
pass G0. Independent recompute (exec/r0-g0-recompute.py) reproduced all numbers; stricter
per-layer residual clamp (vs my per-config clamp in r0-g0.py:149-156) changes no verdict.
Post-endorsement edits queued (do NOT apply before jhan endorses): (a) rename "maximally
conservative" -> "reduced-overlap sensitivity"; (b) primary corrected estimand =
stall_topk_read ALONE (0.3us logits-read + 0.2us wait-indices not presumed removable until
P1a); (c) one line in p0-trace.html sec 6: "independent recomputation
(exec/r0-g0-recompute.py, session 7ff0b556): reproduced; stricter per-layer residual
variant changes no verdict" (closes Sol finding 8). Do NOT regenerate g0-decision*.json
with the per-layer clamp (amended 2026-08-24, intel-amx-3d): the published config-mean-clamp
numbers are the decision basis; the recomputation is the standing verification record;
per-layer clamping applies PROSPECTIVELY as the residual treatment in the P1a analysis
pre-registration. P1a requirement: pre-register and directly
mark CPU-world boundaries (compute start/end, logits publish, helper entry, topk done,
output publish, worker-0 read return); integrated P1a measurement supersedes the residual
estimate. Note: 7/5880 (20b u1/2K) + 8/216 (120b u1/2K) layer records lack
helper_entry_off - flag treatment explicitly in future reports.

- Marker set lives on branch jhan-router-p0 (main 1407f48dd + 3b0234df6 + 3de009774);
  bench router/bench_router_kernel.cpp; campaign scripts exec/r0-*.sh; analyzer
  exec/r0-analyze.py (step alignment by routing_channel suffix; M from "expert token
  counts" instants /topk - MoE-matmul tokens args double-count across gate_up+down).
