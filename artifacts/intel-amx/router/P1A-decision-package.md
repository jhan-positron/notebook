# P1a decision package - for jhan

**DECISION RECORDED 2026-08-24: jhan declined the bounded-parallel experiment ("n" to the
authorize-vs-close question in the rampup/plan session) - OPTION (C) IS CLOSED.** Basis (the
package's close case, Sol-endorsed as defensible): serialized G-B missed in all four cells,
both 8u cells negative, the G0 estimate was built on trace-inflated stalls, and the remaining
upside (~+1-2% est, parallel placement) carries the Note [Expert matmuls] contention risk -
too small a ceiling to spend further slots on. Consequences: no bounded-parallel prototype,
P1b/AMX router kernel dead, P2 router numerics pin dead (the recorded token-16 divergence
stays a documented open observation, not an investigation), tron-router-p0 stays an archived
spike branch (no PR). What remains live: **option (e), card-side fusion, as a handoff to the
FPGA team** - price it from the REPRICED untraced magnitudes (~8 us/layer at 1u, ~12 at 8u,
p1a-spike.html sec 2/4), NOT the traced 19-33 us figures; host-side traces and the chain
decomposition are in p0-trace.html sec 4. The honest one-line project answer to
input-2-ai/router-amx.md: the router matmul was a plausible AMX target, but measurement
showed the FPGA round trip's true untraced cost leaves a CPU router under +1% serialized and
~+1-2% est at best in parallel placement - below the project threshold; the remaining
opportunity belongs card-side. Inputs: P1a execution by
intel-amx-a3 (`router/p1a-spike.html`, `exec/results/router/P1A-preregistration.md` OUTCOME),
my cross-check of its arithmetic, and a Sol decision round
(`exec/results/router/sol-p1a-review.md`, verbatim).

## The result (meas, untraced same-binary A/B, n=6/arm)

**G-B NOT MET for the pre-registered serialized CPU router** on gpt-oss-20b-tp2:
best cell 1u/2K +0.81% [95% CI -0.22, +1.85]; 1u/8K flat; 8u/2K -2.30; 8u/8K -1.77
(CI excludes zero). The corrected G0 estimate (+2.6..+5.4%) is superseded by this integrated
measurement, exactly as the pre-registration and the plan required. The mechanism itself
worked (top-k output block 19.7 -> 0.36 us/layer traced), and the type-feasibility spike
passed every checklist item - the "no" is about payoff, not feasibility.

Two measured root causes:
1. **Perfetto tracing inflated the P0 stalls ~2.5x** (untraced baseline 251.8 tok/s vs P0's
   traced-implied 206). The untraced recoverable stall back-computes to ~8 us/layer at 1u
   (~4.8% of the step, gross) and ~12 us at 8u - against a CPU kernel cost of 6.4/22 us
   (avx_bf16 at M=1/M=8), leaving <=1-2 us/layer of net margin at 1u and negative at 8u.
2. **Serialized placement adds a new serial wait**: the driving thread must wait for the
   helpers' rmsnorm output (~14.6 us at 1u, derived attribution) before computing; the async
   FPGA path parks that wait off the critical thread.

Verification status: my recomputation cross-checks passed (the +0.81% is consistent with the
back-computed stall arithmetic); Sol confirmed the negative G-B result is valid and robust,
and that none of the phase's recorded deviations is fatal to it. Two record defects I found
were confirmed by Sol and are being corrected in the report (a mislabeled 0.2% figure in the
close-option bullet - it is the post-replacement residual, not the round trip's cost - and an
overdrawn "token comparison is instrument-invalid" numerics claim; the determinism retry with
the established `--temperature 0 -s 42 --pay-for-determinism` recipe has since completed -
see the numerics verdict below).

## Numerics verdict (2026-08-24, exec/results/router/p1a-numerics2-verdict.txt)

- **The token-comparison instrument IS valid**: the flagged OFF-vs-OFF control is
  token-identical, and gpt-oss MoE does not break determinism under the established recipe
  (new fact; the P1a command audit confirmed the original control lacked the flags - recorded
  as a deviation in the report). An initial "invalid-even-flagged" verdict was a normalization
  artifact (a [Load] log line interleaved mid-stream poisoned the line diff); re-verdicted by
  color-span token extraction - the same trap and fix the attention project recorded in 2026-08.
- **OFF-vs-ON genuinely diverges at token ~16 of 34** under deterministic greedy: the CPU
  router's logits differ from the FPGA's enough to flip an expert selection once, after which
  divergence is by construction. Labeled hypothesis: top-k near-tie flip (same class as the
  attention project's argmax-tie flips); deciding investigation: the P2 logits/expert-set pin
  with rank-k/k+1 cutoff margins.
- **Decision relevance**: moot for the serialized arm (already failed on throughput). Live for
  the bounded-parallel option: its Stage-1 stop conditions cover "unexplained token
  divergence" - this divergence now has a recorded position and a testable cause, so an
  affirmative bounded-parallel result would additionally require the cutoff-margin pin to show
  flips occur only at near-ties within the numerics contract.

## What you are deciding

Four follow-ons were on the table. Sol's assessment (full text in sol-p1a-review.md):

| option | Sol verdict |
|---|---|
| (i) bounded-parallel CPU router | **Authorize ONCE, tightly bounded** - the only follow-on motivated by a newly measured, potentially removable failure mode (the placement wait). Est net upside ~+1-2% only. |
| (ii) P1b AMX | **Do not authorize independently.** Eligible only if parallel placement first succeeds AND a measured 8u decomposition shows AMX clears (not approaches) +1%. |
| (iii) option (e) card-side fusion | **Hand off for pricing in parallel - with REPRICED inputs** (the P0 traced 19-33 us/layer numbers are inflated; price from the untraced ~8/12 us recalibration). |
| (iv) close option (c) now | **Defensible** - if you consider a ~1-2% est ceiling too small to justify even the cheap harness check. The close case must rest on the small NET payoff, not the mislabeled 0.2% figure. |

**Sol's recommended package (I concur):** authorize exactly one bounded-parallel prototype in
the existing spike harness with hard stops, hand option (e) to the FPGA team with the
recalibrated numbers, no P1b. My one addition: the bounded-parallel experiment is also the
cheapest way to make the close-of-(c) decision permanent and evidence-backed either way - one
quiet slot buys the final answer to the host-side question.

### Pre-registered stop conditions for the bounded-parallel experiment (Sol wording, condensed)

- ONE predeclared helper placement and worker count (chosen prospectively from scheduler
  mechanics - no placement sweep); existing avx_bf16 kernel only; same-binary A/B; direct
  slices for rmsnorm-ready, helper router start/end, publish, top-k read, first expert
  submission; max n=6/arm; deterministic numerics retry with the established flags; no
  emitter work, no AMX plumbing, no scheduler redesign.
- Stage 1 = 1u/2K only. Stop and close option (c) if: upper 95% CI < +1%, or mean < +1% at
  the rep budget, or the placement delays first-expert submission / increases FPGA idle
  enough to eat the gain, or sync consumes most of the modeled upside, or implementation
  needs work outside the harness.
- Stage 2 (only on a Stage-1 pass): the other three cells under the frozen placement; any
  material production-cell regression closes option (c).
- Absolute cap: one implementation, one placement, one campaign. A miss closes host option
  (c). The +1%/CI-excluding-zero gate is not weakened.

## Process notes

- The G0 deviation endorsement is NOT undermined: P1a confirmed the corrected marker's causal
  correspondence (the block collapses when the dependency is removed); what fell was the
  traced magnitude as a payoff predictor - and its supersession by integrated measurement was
  pre-registered on both sides. Dated addenda added to `router/G0-decision-package.md` (done)
  and `router/p0-trace.html` (peer applying).
- The tracing-inflation finding also affects the queued rampup-doc updates (sec 3's
  round-trip narrative must carry the traced-vs-untraced distinction) - still held on your
  review.

## Artifact index

| artifact | what |
|---|---|
| `router/p1a-spike.html` | P1a report (A/B, mechanism, spike proof, deviations) |
| `exec/results/router/P1A-preregistration.md` | pre-registration + OUTCOME |
| `exec/results/router/p1a-ab.txt`, `p1a-*-rep*.txt` | raw A/B lines |
| `exec/results/router/sol-p1a-review.md` | Sol's full review (verbatim) |
| `exec/results/router/p1a-numerics2-verdict.txt` | determinism retry: instrument valid; OFF-vs-ON diverges at token ~16 (near-tie hypothesis) |
| `router/G0-decision-package.md` | prior decision + dated POST-G0 addendum |
