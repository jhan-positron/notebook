# Sol P1a decision review - 2026-08-24

Model: gpt-5.6-sol via PAL bridge; requested by session 7ff0b556 after P1a completion.
Verbatim below.

## Verdict

1. **Finding (A) is correct.** The `~0.2%` value is the post-replacement blocked-read residual, not the untraced cost of the FPGA round trip.
2. **Finding (B) is correct in substance, with one evidentiary qualification.** The attempted control is inconclusive, not sufficient to declare token comparison “instrument-invalid.” The attached artifacts do not include the exact run command, so omission of the determinism flags should be confirmed before stating it as fact.
3. **The negative G-B result is valid and robust.** None of the reported execution deviations invalidates the same-binary throughput result.
4. **Recommend exactly one tightly bounded parallel-placement experiment, then stop unless it clears the existing gate.** Do not authorize P1b independently. Hand option (e) to the card team with recalibrated—not unchanged—performance inputs.
5. **The earlier G0 deviation endorsement remains procedurally sound.** Its estimate was superseded as anticipated, but the G0 package and P0 report should receive short dated addenda so historical “PROCEED” numbers are not mistaken for current evidence.

---

## 1. Finding (A): `~0.2%` is mislabeled

At `router/p1a-spike.html` lines 170–171:

> “the round trip's untraced end-to-end cost (≈0.2% of step at 1u) is far smaller than P0's traced view suggested.”

That statement is dimensionally inconsistent with the report’s own estimate at lines 113–117:

> “the untraced recoverable stall is ≈8 μs/layer at 1u”

Using the report’s 1u/2K baseline:

- Step time: approximately `1 / 251.78 s = 3,972 µs`
- Gross untraced router-dependent stall: `8 µs × 24 = 192 µs`
- Gross fraction of step: `192 / 3,972 = 4.83%`
- Post-replacement traced blocked-read residual: `0.36 µs × 24 = 8.64 µs`
- Residual fraction: `8.64 / 3,972 = 0.22%`

Therefore:

- `~4.8%` is the estimated **gross recoverable router-dependent stall**.
- `~0.2%` is the **remaining top-k-output blocked-read duration after replacement**.
- `+0.81%` is the measured **serialized end-to-end net result**.
- `+1–2%` is only an estimated **parallel-placement net opportunity**, not the gross stall.

### Required replacement

**Location:** `router/p1a-spike.html` lines 170–171  
**Current excerpt:** `Close option (c)... ≈0.2% of step at 1u`

**context_start_text:** `<li><b>Close option (c)</b>:`  
**context_end_text:** `far smaller than P0's traced view suggested.</li>`

Replace with:

> **Close option (c):** defensible if the bounded-parallel placement check below is declined or fails its gate. At 1u/2K, the estimated untraced gross router-dependent stall is ≈8 µs/layer, or ≈4.8% of the ≈3,972 µs decode step—not 0.2%. The serialized implementation recovers that dependency but pays the CPU kernel and driving-thread placement costs, producing only +0.81% [95% CI −0.22, +1.85] end to end. The ≈0.2% figure is the post-replacement top-k-output blocked-read residual (0.36 µs × 24 layers), not the original round-trip cost.

The parallel bullet at lines 158–163 also needs a labeling clarification. It currently moves directly from an `8 µs/layer` gross stall to `≈+1–2% decode`, although those are different quantities.

**context_start_text:** `<li><b>Bounded-parallel CPU router`  
**context_end_text:** `Cheap to prototype in the same spike harness.</li>`

Suggested replacement:

> **Bounded-parallel CPU router (P1a variant the plan pre-named):** run the router on a bounded helper placement rather than on the driving thread, allowing the rmsnorm-arrival wait and router computation to overlap with otherwise available work. The estimated untraced gross router-dependent stall is ≈8 µs/layer at 1u and ≈12 µs/layer at 8u; at 1u/2K the former is ≈4.8% of the decode step. After paying kernel, synchronization, and any contention costs, the modeled net opportunity is only ≈+1–2% decode. That net figure is an estimate, not the cost of the round trip. The Note [Expert matmuls] worker-contention and FPGA-feed risks apply. Cheap to prototype in the existing spike harness under the stop conditions below.

This also avoids implying that moving work to a helper automatically removes its entire latency from the dependency chain. The compute still must complete before top-k; the benefit depends on useful overlap and lack of contention.

---

## 2. Finding (B): “instrument-invalid” is overdrawn

There is an internal inconsistency in the attached record.

The pre-registration at `P1A-preregistration.md` lines 56–58 specified:

> “identical prompt, greedy decoding — token sequences must match between arms, or the first divergence step is recorded and investigated”

But the report at `p1a-spike.html` lines 145–148 says:

> “sampled generation is not seed-reproducible in this harness (seeded off-vs-off control diverges from the first tokens), so token comparison cannot verify router numerics”

“Sampled generation” is not the pre-registered “greedy decoding” setup. Moreover, given the supplied attention-project result that runtron was deterministic with:

```text
--temperature 0 -s 42 --pay-for-determinism
```

an OFF-vs-OFF divergence under some other command does not establish that token comparison is intrinsically unusable.

The attached artifacts do not contain the exact P1a command line. Consequently, this review can verify that the conclusion is unsupported, but cannot verify from these files alone that all three flags were omitted. The record should first audit and preserve the actual command.

### Required replacement in the report

**Location:** `router/p1a-spike.html` lines 145–148  
**Current excerpt:** `sampled generation is not seed-reproducible...`

**context_start_text:** `<li><b>Numerics instrument finding</b>:`  
**context_end_text:** `On-arm output is qualitatively sane.</li>`

Replace with:

> **Numerics instrument finding:** the attempted seeded OFF-vs-OFF control diverged from the first tokens under the command used for this phase. That attempt does not establish that token comparison is instrument-invalid: the pre-registration required greedy decoding, and the attention-project `t1-quick` record established deterministic runtron output with `--temperature 0 -s 42 --pay-for-determinism` on its tested models/configurations. Audit the preserved P1a command and retry an OFF-vs-OFF control on gpt-oss with all three flags before abandoning token comparison. If that control is byte-identical, repeat OFF-vs-ON and record the first divergence. If gpt-oss remains nondeterministic—potentially because of MoE routing ties—record that model-specific result and use the planned logits/expert-set pin. Until that retry, token comparison is unresolved rather than instrument-invalid. On-arm output was qualitatively sane.

### Required replacement in the pre-registration outcome

At `P1A-preregistration.md` lines 96–97:

> “Numerics: seeded off-vs-off control diverges -> token comparison instrument-invalid; P2 logits pin is the instrument.”

**context_start_text:** `Numerics: seeded off-vs-off control`  
**context_end_text:** `P2 logits pin is the instrument.`

Replace with:

> Numerics: the attempted seeded OFF-vs-OFF control diverged under the command used. This does not establish that token comparison is instrument-invalid: the pre-registered greedy/deterministic setup must be checked against the prior runtron recipe (`--temperature 0 -s 42 --pay-for-determinism`) and retried on gpt-oss. Token comparison remains unresolved; if a correctly configured OFF-vs-OFF control still diverges, the P2 logits/expert-set pin is the authoritative instrument.

If command auditing confirms that the flags were absent, add that fact explicitly and list it in section 5 as a deviation from the pre-registered greedy numerics setup.

### Effect on G-B

This defect does **not** rescue the serialized arm:

- The throughput criterion already fails in every cell.
- Numerics is unresolved rather than passed, but resolving it cannot turn `+0.81%` into a gate pass.
- Therefore the proper conclusion is: **serialized G-B failed on performance independently; its token-comparison check remains unresolved.**

The report should avoid wording that implies the numerics gate passed or that token comparison has been permanently disqualified.

---

## 3. Recommended decision for jhan

### Recommended choice

Authorize **one bounded-parallel CPU-router prototype in the existing spike harness**, with a hard stop and no production/emitter work. In parallel, hand option (e) to the FPGA/card team with corrected magnitude information. Do not authorize standalone P1b.

The rationale is narrow:

- The serialized result is negative.
- The best cell’s CI still admits modest upside: `+0.81% [−0.22,+1.85]`.
- Placement introduced a specific avoidable critical-thread cost.
- The parallel variant was already contemplated by the plan at lines 167–173, so this is not an invented post-hoc architecture.
- It is cheap in the existing harness and can directly test the last plausible host-side mechanism.
- The estimated upside is only `~1–2%`, so more than one bounded attempt would be disproportionate.

### Hard scope

The follow-on should permit:

1. One predeclared helper placement and worker count.
2. Existing AVX-bf16 kernel only.
3. Same-binary FPGA OFF vs parallel-host ON.
4. Direct slices for:
   - rmsnorm-ready/arrival,
   - helper router start/end,
   - publish,
   - top-k output read,
   - first expert submission.
5. Existing ABBA and maximum `n=6/arm`.
6. Deterministic numerics retry using the established flags.
7. No emitter integration, AMX plumbing, generalized scheduler, worker-pool tuning campaign, or production packaging.

If there are two obviously available placements in the harness, choose one prospectively based on the scheduler mechanics; do not run a placement sweep and select the winner.

### Staged stop conditions

#### Stage 1: 1u/2K, the only positive serialized cell

Stop and close option (c) if any of these occurs:

- Upper 95% CI for decode improvement is below `+1%`.
- Mean improvement is below `+1%` after the fixed rep budget.
- The helper placement measurably delays first-expert submission or increases FPGA idle/starvation enough that the end-to-end gain does not clear G-B.
- Synchronization or scheduling consumes most of the modeled `~1–2%` opportunity.
- Correctly configured OFF-vs-OFF determinism passes but OFF-vs-ON has an unexplained token divergence.
- Implementation requires scheduler redesign or work outside the existing spike harness.

For an affirmative result, retain the existing project gate: mean improvement at least `+1%` and 95% CI excluding zero. Do not weaken it because the projected upside is small.

#### Stage 2: remaining production cells

Proceed only if Stage 1 clears the gate. Then run the three remaining cells under the same frozen placement.

Stop and do not advance toward production if:

- Any production cell has a material regression, especially either 8u cell.
- The 8u result confirms worker contention or FPGA starvation.
- The result depends on configuration-specific placement tuning.
- The final record does not show a credible production-wide benefit under the plan’s no-regression requirements.

#### Absolute campaign cap

One implementation, one fixed placement, and one campaign capped at six reps per arm per config. A miss closes host option (c). No second scheduler strategy should be authorized merely because the first confidence interval overlaps the threshold.

---

## 4. Assessment of each follow-on

### (i) Bounded-parallel CPU router

**Recommendation: authorize once, tightly bounded.**

This is the only follow-on directly motivated by a newly measured and potentially removable failure mode: serialized placement charges rmsnorm arrival to the driving thread, whereas the FPGA path parks it elsewhere.

Trade-offs:

- Plausible opportunity: only `~1–2% net`, estimated.
- Gross `~4.8%` at 1u/2K should not be presented as realizable net gain.
- Contention could erase the gain or worsen 8u.
- The prototype must demonstrate end-to-end benefit, not merely a shorter driving-thread slice.

One attribution wording should also be corrected. Lines 118–121 mark the entire finding as measured, while section 5 lines 183–186 admits that the `~14.6 µs` wait was separated arithmetically.

Suggested wording:

> The traced CPU-router slice is 21.0 µs/layer at M=1. Using the independently measured 6.4 µs AVX-bf16 kernel cost gives an inferred ≈14.6 µs rmsnorm-arrival component. Because this phase did not place a separate arrival-ready marker, 14.6 µs is derived attribution rather than a directly measured slice.

That preserves the plausible root cause without overstating instrumentation precision.

### (ii) P1b AMX

**Recommendation: do not authorize independently or for serialized placement.**

The record supports the report’s conclusion that AMX is relevant only at 8u:

- AVX-bf16: approximately `22 µs`
- AMX: approximately `6.6 µs`
- Serialized placement still retains the arrival-wait problem.
- The serialized arm already loses at both 8u configurations.

P1b should become eligible only if the bounded-parallel experiment demonstrates all of the following:

1. Placement and contention are under control.
2. The remaining measured 8u critical path is actually kernel-dominated.
3. Substituting the measured AMX kernel time into that measured decomposition projects an integrated result above `+1%` with useful margin.
4. The estimated margin is large enough to justify AMX plumbing, packing, lifecycle, and integrated testing—not merely “flat-positive.”

A projection barely above zero is not sufficient. The original project threshold remains `+1%`, and P1b has materially greater engineering cost than the parallel harness change.

### (iii) Option (e), card-side fusion

**Recommendation: hand off for pricing in parallel, but correct “unchanged inputs.”**

At lines 167–169 the report says:

> “unchanged by P1a — its input numbers ... are in p0-trace.html”

The architectural attraction is unchanged: card-side fusion avoids host CPU compute and host placement. The numerical inputs are **not** unchanged, because P1a indicates that Perfetto inflated the host-observed P0 stall.

Suggested replacement:

> **Option (e), card-side fusion:** its architectural case is unchanged—card-side fusion avoids both host CPU compute and host placement. Its payoff magnitude must, however, be repriced: P1a indicates that the P0 Perfetto capture inflated the host-observed router-dependent stall, with the untraced recoverable component estimated at ≈8 µs/layer at 1u and ≈12 µs/layer at 8u. Use the P0 chain decomposition together with this P1a recalibration; do not price fusion directly from the traced 19.7/32.9 µs blocked-read values.

Option (e) may still be preferable technically, but the current artifacts do not establish its implementation cost or integrated payoff. It is a handoff, not a router-project authorization.

### (iv) Close option (c)

**Recommendation: close after one bounded-parallel miss, or close now if jhan considers a `~1–2%` estimated ceiling too small to justify even the cheap harness check.**

Closing now is defensible based on:

- Serialized G-B missed in all four cells.
- Two 8u cells are negative; one excludes zero.
- The best cell’s mean is below the threshold.
- The G0 estimate was based on trace-inflated stalls.
- The remaining plausible gain requires scheduler placement and carries known contention risk.

The close case must rest on the **small measured/modeled net payoff after costs**, not on the incorrect claim that the gross round trip is `0.2%`.

---

## 5. Effect on the earlier G0 deviation endorsement

Nothing in P1a undermines the endorsement itself.

The G0 endorsement answered whether replacing the nonblocking logits-read marker with the top-k-output read was a legitimate post-capture operationalization correction. `G0-decision-package.md` lines 32–50 explicitly grounded endorsement in:

> “causal correspondence and minimality, not on the corrected outcome”

P1a confirms that causal correspondence: the traced top-k-output block collapses from `19.7/32.9 µs` to `0.36 µs`. Thus the corrected marker really did identify a router-dependent block.

What P1a invalidates is the corrected trace-derived **magnitude as a predictor of untraced production payoff**, not the marker correction or the decision to run a bounded integrated test.

The record also anticipated this outcome:

- `P1A-preregistration.md` lines 29–30:  
  > “The integrated measurement SUPERSEDES the G0 residual model R.”
- `G0-decision-package.md` lines 70–71:  
  > “P1a must mark the CPU-world boundaries directly and its integrated measurement supersedes the residual estimate.”

Therefore:

- No retroactive reversal of G0 is appropriate.
- The historical status remains “deviation-endorsed PROCEED to P1a-spike-first.”
- The current performance status is “P1a serialized G-B NOT MET.”

### Dated addendum recommended for `G0-decision-package.md`

The package’s current top-level text still prominently says “20b G0 ... PROCEED” at lines 7–8. Historically that is correct, but a dated addendum is needed to prevent it being read as current authorization.

**Insert after line 11.**

**context_start_text:** `intel-amx-a3 applied the three documentation-of-record edits and started P1a.`  
**context_end_text:** `## What you are deciding`

Suggested wording:

> **POST-G0 OUTCOME — 2026-08-24:** P1a completed the authorized spike-first work. Mixed host/device type feasibility succeeded, but the pre-registered serialized AVX-bf16 arm did not meet G-B in any 20b configuration; best result was 1u/2K at +0.81% [95% CI −0.22, +1.85]. The integrated result supersedes the corrected G0 residual estimate as pre-registered. P1a indicates that Perfetto inflated the P0 router-dependent stall by approximately 2.5× and that serialized host placement adds an rmsnorm-arrival wait to the driving thread. This does not reverse the 2026-08-23 endorsement of the boundary correction, which was procedural and based on causal correspondence rather than outcome; it closes that endorsement’s authorization by recording the resulting integrated test.

### Dated addendum recommended for `p0-trace.html`

Do not rewrite or delete the original P0 numbers. Add a prominent dated measurement-status note near its verdict or G0 table:

> **Measurement-status addendum — 2026-08-24:** The subsequent same-binary untraced P1a A/B supersedes this report’s corrected G0 residual estimate for implementation decisions. P1a indicates that Perfetto inflated the P0 router-dependent blocked-read duration by approximately 2.5×: the untraced recoverable component back-computes to ≈8 µs/layer at 1u and ≈12 µs/layer at 8u, rather than the traced 19–33 µs/layer view. The corrected P0 boundary remains a valid causal marker, but its traced magnitude must not be used as an untraced end-to-end payoff estimate. See `p1a-spike.html`.

This is an addendum, not a correction to frozen G0 computations. P1a’s own report and preregistration outcome technically establish supersession already, but backlinking from the older decision artifacts is important because those artifacts can be read independently.

---

## 6. P1a deviations and their effect on G-B

### Placeholder-arm first pass

At lines 178–180:

> “The first A/B pass ran a placeholder kernel ... corrected, and re-run; both generations preserved”

**Not fatal.** The wrong arm’s data were not silently substituted for the pre-registered result. The correct AVX-bf16 arm was rerun, reported separately, and reached `n=6/arm`. Preservation of both generations is the right treatment.

The placeholder data should remain secondary and must not contribute to the AVX confidence intervals, which the report appears to respect.

### Rep extension

At lines 181–182:

> “The rep extension covered all four configs ... every n=3 CI was wide.”

This is not substantively a deviation. The pre-registration at lines 49–50 explicitly required:

> “add reps until the per-arm CI half-width < 0.3% of mean tok/s or 6 reps reached.”

If every `n=3` interval was wide, extending every config to six reps followed the registered rule. It is acceptable to disclose it, but the wording should be:

> Rep extension to n=6/arm was performed in all four configurations because every n=3 interval exceeded the pre-registered precision target. This was execution of the registered adaptive-rep rule, not a post-hoc sample-size change.

### Unseparated rmsnorm-arrival wait

At lines 183–186:

> “the arrival wait was not separately sliced. Attribution separated it arithmetically”

**Not fatal to the throughput conclusion.** Same-binary untraced A/B does not depend on that trace decomposition.

It does weaken the precision of the root-cause claim:

- The `21.0 µs` combined slice is directly measured.
- The `6.4 µs` kernel input comes from P0b.
- The `14.6 µs` wait is inferred by subtraction.
- The report should label it “derived” or “estimated,” not a directly measured wait slice.

A bounded-parallel follow-on must add the missing direct boundary before using this decomposition for another implementation decision.

### 2K-only traced attribution

At lines 187–188:

> “the 8K cells were not traced — scope cut, stated.”

This violates the pre-registered “one traced rep per config per arm” attribution scope, but it is **not fatal to G-B**, whose primary metric is untraced steady-state decode throughput.

Consequences:

- The 8K throughput results remain valid.
- The traced mechanism evidence is directly established only at 2K.
- The report must not imply that the exact same wait decomposition was directly observed at 8K.
- Any follow-on relying on the mechanism at 8K should collect the missing trace rather than extrapolate silently.

### Numerics setup

This is the more important unlisted deviation or unresolved item. The report says “sampled generation,” while the preregistration says “greedy decoding.” If command auditing confirms that deterministic greedy flags were absent, add a fifth section-5 bullet:

> The token-control run did not use the previously established complete deterministic runtron recipe (`--temperature 0 -s 42 --pay-for-determinism`), despite the pre-registration requiring greedy comparison. Its OFF-vs-OFF divergence is therefore inconclusive. A correctly configured gpt-oss retry remains required before token comparison can be declared unavailable.

Again, this does not invalidate the negative throughput gate; it prevents the report from claiming a resolved numerics-instrument conclusion.

---

## Final recommendation to jhan

1. Record the serialized P1a arm as **G-B NOT MET**, with numerics comparison unresolved rather than instrument-invalid.
2. Correct the `0.2%` statement and distinguish gross stall, residual wait, measured serialized net, and estimated parallel net.
3. Authorize **one** fixed-design bounded-parallel experiment in the existing spike harness, capped at one implementation and six reps per arm/config.
4. Stop immediately unless 1u/2K clears the existing `≥+1%` mean plus CI-excluding-zero gate without contention or correctness problems.
5. Run the remaining cells only after that pass; any material production-cell regression closes option (c).
6. Do not authorize P1b unless parallel placement first succeeds and a measured 8u decomposition shows AMX can clear—not merely approach—the project threshold.
7. Send option (e) for separate pricing using the P1a-recalibrated untraced magnitude.
8. Add dated supersession notes to the G0 package and P0 report; do not reverse or rewrite the historical deviation endorsement.
