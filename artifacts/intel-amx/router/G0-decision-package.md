# G0 decision package - for jhan

**DECISION RECORDED 2026-08-23:** jhan endorsed the gate-variable deviation (verbatim
instruction to session intel-amx-a3: "Endorse the gate-variable deviation"; relayed to this
session the same day - provenance is that relay, not a direct message here). Effects, per
this package's sequencing: Sol's decision-record wording (sec "Sol verdict") is adopted;
**20b G0 is closed as deviation-endorsed PROCEED (P1a-spike-first)**; 120b remains
conditional scope only; g0-decision*.json stay frozen as published;
`exec/r0-g0-recompute.py` is the standing verification record; per-layer residual clamping
applies prospectively in the P1a pre-registration. intel-amx-a3 applied the three
documentation-of-record edits and started P1a.

**POST-G0 OUTCOME - 2026-08-24 (dated addendum, Sol P1a round):** P1a completed the authorized
spike-first work. Mixed host/device type feasibility succeeded, but the pre-registered
serialized AVX-bf16 arm did not meet G-B in any 20b configuration; best result was 1u/2K at
+0.81% [95% CI -0.22, +1.85]. The integrated result supersedes the corrected G0 residual
estimate as pre-registered. P1a indicates that perfetto tracing inflated the P0
router-dependent stall by approximately 2.5x and that serialized host placement adds an
rmsnorm-arrival wait to the driving thread. This does not reverse the 2026-08-23 endorsement
of the boundary correction, which was procedural and based on causal correspondence rather
than outcome; it closes that endorsement's authorization by recording the resulting
integrated test. Next decision package: `router/P1A-decision-package.md` (Sol review at
`exec/results/router/sol-p1a-review.md`).

Assembled 2026-08-23 by the rampup/plan session (7ff0b556). Inputs: P0 execution by session
intel-amx-a3 (`router/p0-trace.html`, `exec/results/router/G0-preregistration.md`), a Sol
consensus round dedicated to the gate deviation, and an independent recomputation of the gate
from the raw per-step artifacts (`exec/r0-g0-recompute.py`, this session, Sol finding 8).

## What you are deciding

1. **Endorse or reject the G0 deviation.** The pre-registered gate variable (the driving
   thread's logits-read slice) measured 0.3 us/layer and says STOP. Post-capture analysis
   showed that slice is nonblocking in the generated execution; the router-dependent block
   lands one statement later, at the top-k-output read (19.3/32.4 us per layer at 1u/8u,
   20b). The corrected gate is advisory until you endorse it.
2. **If endorsed: adopt the per-model verdicts** (below) and give intel-amx-a3 the P1a
   signal.
3. **Plan sec-2 base decision** (wait for #3879 vs extract plumbing) - can wait; P1a's
   spike needs no AMX plumbing.

## Sol verdict: ENDORSE-DEVIATION (round of 2026-08-23)

Basis (Sol's criteria, all satisfied): the pre-registration's recorded INTENT ("the serial
cost actually paid") was unambiguous and the chosen marker failed to operationalize it; the
replacement marker represents the same dependency in the code (top-k output cannot arrive
without router logits); the correction is minimal (one statement); it was applied
symmetrically to all models/configs; both results are retained everywhere; and the 20b
decision survives the less-favorable sensitivity treatment. Sol's condition: the endorsement
is "based on causal correspondence and minimality, not on the corrected outcome," and the
corrected result must stay labeled deviation forever (no retroactive claim).

Sol's recommended decision-record wording, to adopt verbatim if you endorse:

> "Jhan endorses the corrected boundary as a post-capture operationalization correction. The
> pre-registration unambiguously targeted the driving thread's router-dependent serial cost
> but attached that intent to a logits-channel read that is nonblocking in the generated
> execution. Code mechanics and trace closure independently locate the dependency one
> statement later at the top-k-output read. The original pre-registered computation remains
> the formal registered result (STOP); the corrected computation is accepted as the
> decision-relevant deviation and must remain labeled as such. This endorsement is based on
> causal correspondence and minimality, not on the corrected outcome."

## Per-model verdicts (Sol wording, condensed)

- **20b: G0 PROCEED** - all four corrected configs clear +1% with margin, including the
  reduced-overlap sensitivity (+2.24..+4.41%). Authorization is for the P1a-spike-first
  order (mixed host/device compile-and-run spike, then minimal host-router A/B). It is NOT
  an AMX shipping decision and NOT P1b authorization.
- **120b: literal non-STOP, conditional scope only.** Single-core: negative at 1u,
  +1.35%/+0.81% at 8u. The 4-worker AMX viability (8.49 us/layer measured in the bench) is
  an integrated-performance estimate and is NOT used to pass G0 (it collides with the
  worker-contention risk). Keep 120b as a host-placement + scheduling spike alongside the
  20b P1a work; no production 4-worker design without integrated contention + FPGA-feed
  measurements.

Sol's secondary corrections (apply to the record, not blockers): the primary corrected
estimand is the top-k-output block alone (the adjacent 0.3 us logits-read and 0.2 us
wait-indices slices are not presumed removable until P1a shows it); rename the alternate
row "reduced-overlap sensitivity", not "maximally conservative" (the residual formula does
not model the late-logits branch where top-k still executes after CPU completion); the 2 us
allowance is not endorsed as a reusable model constant - P1a must mark the CPU-world
boundaries directly and its integrated measurement supersedes the residual estimate.

## Independent recomputation (Sol finding 8 - required before G0 closure)

Done by this session (not the capturing one): `exec/r0-g0-recompute.py` re-derives the gate
from the per-step-layer records and raw bench RESULT lines with independent parsing,
aggregation, residual arithmetic, and bootstrap. Results:

- Pre-registered g, A_corr, T_step, M, and best-arm selection: **reproduced** across all 8
  configs (A and T to 0.1 us; g_pre to <0.02pp).
- One aggregation difference found and root-caused: the published gate applies the residual
  clamp once per config from MEAN helper-entry E and MEAN top-k span (r0-g0.py:149-156);
  the recomputation clamps per layer (strictly more conservative). Effect: 20b 1u corrected
  means lower by 0.03-0.04pp (5.32 vs 5.36; 4.69 vs 4.72) - still far above +1%; 120b
  u1/ctx2048 lower (-1.62 vs -1.42) - still negative. **No verdict changes; the stricter
  treatment strengthens the 20b PROCEED.**
- Extraction-consistency (closure) check across all layers: mean gap (helper entry +
  helper wait + top-k span) minus the blocked-read duration = +2.4..+2.7 us per layer in
  every config = the pre-block dispatch work, as expected. Tails show outliers (to -22 us)
  in individual layers - consistent with span noise, not with a systematic error.
- Remaining independence gap, stated plainly: span extraction from the raw
  .perfetto-trace files was not re-implemented (r0-analyze.py's JSON is the shared input);
  the closure statistics are the consistency check on it. Sol's finding 9: a baseline
  re-capture is NOT required unless recomputation had found ambiguity - it did not; the
  higher-value verification is pre-registered instrumentation on the P1a spike itself.

## Sequencing after endorsement (Sol finding 10)

1. ~~Independent recomputation~~ (done, above).
2. You close 20b G0 as deviation-endorsed PROCEED (decision-record wording above).
3. intel-amx-a3 runs the mixed host/device compile-and-run spike (plan sec 4 P1a).
4. Instrumented minimal P1a same-binary FPGA-vs-host A/B, with the CPU-world boundaries
   pre-registered this time (CPU compute start/end, logits publish, helper entry, top-k
   completion, output publish, worker-0 read return).
5. Only then the P1b/AMX-plumbing decision; 120b 4-worker AMX stays a separate conditional
   experiment.

## Artifact index

| artifact | what |
|---|---|
| `router/p0-trace.html` | P0 report (lanes, G0 tables, microbench, deviations) |
| `router/status-report/index.html` | status-report form |
| `exec/results/router/G0-preregistration.md` | pre-registration + deviation record |
| `exec/results/router/g0-decision*.json` | published gate rows |
| `exec/r0-g0-recompute.py` | independent recomputation (this session) |
| `exec/results/router/sol-deviation-review.md` | Sol's full 10-finding review (verbatim) |
| `exec/QUEUE.md` R0 section | campaign narrative |
