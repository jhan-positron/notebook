# Consensus Solution

## Problem definition

Fresh gpt-oss runtron launches show persistent throughput dispersion: a launch tends to remain
fast or slow for its lifetime instead of averaging toward one stable rate. The controlled Intel
reference arms reproduce this at both TP4 and TP2. A documented AMD standalone campaign also
shows material relaunch dispersion, so platform immunity is not established.

The current evidence does not identify a root cause. In particular, it does not prove listener
descheduling, a post-WCLS full vocabulary sweep, consumer backlog, polling cadence, callback
delay, or any other proposed mechanism. Existing lossy traces localize only part of the
whole-token difference.

The decision problem is therefore to obtain a causal, whole-cycle explanation with low enough
measurement perturbation to justify a later permanent fix. This review does not implement that
fix.

## Requirements and constraints

- Preserve the original goal: explain and reduce launch-to-launch throughput dispersion without
  changing supported request semantics.
- Treat independent launches, not individual decode cycles, as the inferential unit. Cycles are
  nested observations.
- Separate verified facts, inferences, hypotheses, and unresolved facts.
- Pin each measurement to exact artifact hashes, workload argv, resolved model, device geometry,
  environment, and session.
- Do not infer causality from scheduler coincidence, correlation, mode membership, or a
  source-code branch alone.
- Do not use trace segment totals unless coverage, clocks, nesting, and event conservation pass
  declared gates.
- Measure instrumentation tax with an A/A comparison and reject an instrument that changes the
  phenomenon beyond predeclared bounds.
- Determine sample sizes with prospective draw-level power or an error-controlled bounded
  sequential rule. Do not treat 8–10 or 26 draws as justified constants.
- Use deterministic mode or a predeclared functional/numerical equivalence oracle for semantic
  validation; ordinary cross-launch token identity is not valid under nondeterminism.
- Select one causal intervention at a time and require mediation of the whole per-token
  difference, not only one traced tail.
- Scope conclusions to the measured platform and configuration unless matched validation
  supports transfer.

## Evidence

### Direct evidence

- **Launch dispersion.**
  - ab54 gpt-oss-120B TP4, n=26: population CV 4.6315%; range/mean 23.0468%.
  - ab60g gpt-oss-120B TP2, n=26: population CV 2.6145%; range/mean 10.1294%.
  - ab60b Llama-70B TP4: CV 0.3951%.
  - ab60d Mixtral TP2: CV 0.1789%.
  - ab60c2 Qwen-32B TP2: CV 0.0374%.
- **Control-arm confound.** Both rolling gpt-oss arms used generation length 4096. Every completed
  tight control used 1024. Llama used u4; Mixtral and Qwen used u8. The control values are valid
  only for those tested configurations.
- **Streamed path.** At source commit
  29924aa860a475ec0c00ee6fbf539e3e645805a2, all tested TP aliases use the streamed sparse-result
  consume. Streamed-path presence is not unique to gpt-oss.
- **Trace loss and whole-token accounting.** The relevant Perfetto captures lost approximately
  19–41% of expected cycles, with loss associated with generation behavior. In the observed
  subsamples, post-final-RX accounts for 17.4/17.5% of the r3 true per-token difference and
  30.0% of the ab57 difference. The earlier 96–100% localization used an incomplete denominator
  and is withdrawn.
- **Unresolved decomposition.** r3 assigns about 327 microseconds per token, 53.5% of its
  fast/slow difference, to RX extent, while ab57 reported upstream segments nearly flat. The
  definitions and artifacts have not yet been reconciled.
- **Mode structure.** The lossy stage3 sample contains a short population plus at least two
  longer populations: a sharp population near 700 microseconds and a broad population above
  900 microseconds with inter-cycle spillover. A post-hoc threshold suggested launch differences
  in mode frequency, but the absolute frequencies and the 91.5% mixture result are not
  confirmatory.
- **Worker balance.** Existing normalized speed-share analysis found no substantial
  redistribution across workers. It did not establish equivalence or exclude uniform worker
  slowdown.
- **SMI and interrupts.** ab54 recorded zero MSR SMI increments and zero perf msr/smi events.
  By contrast, /proc/interrupts recorded 1,747,384–1,890,354 counter increments per 20-second
  window. CAL and TLB counts correlate positively with throughput, ρ=+0.5877 and +0.5248
  respectively. Aggregate counts do not exclude listener-CPU-local interference.
- **AMD.** The documented ab45 AMD Genoa standalone campaign has n=24, population CV 2.4549%,
  sample CV 2.5077%, and range/mean 9.0057%. The surviving local data do not contain the raw
  model argv.
- **Concurrent runtron evidence.** ab53 ran two rounds of 20 concurrent A+B process pairs on
  disjoint socket/card halves. The pooled Spearman correlation was ρ=0.17336 with a
  within-round permutation two-sided p=0.20048. Coupling was not confirmed; independence was
  not proved. ab54 and all completed ab60 comparison arms were solo.
- **Binary provenance.** The frozen executable is 520,810,640 bytes with SHA-256
  d34f28b4d2e17b2bb4512a8a5daa06596d436141ae8c8c6140b804ec0dc0dec3 and mtime
  2026-07-27 23:08:15 UTC. It contains logging changes later committed as
  0b6cb141389f0d0e6b74f38e8ba8093ffe2dfb16 at 23:08:32 UTC. That known 14-line delta is
  logging-only and does not touch the streamed-logits files. The complete source tree used for
  the executable is not cryptographically attested. ab54 and ab60g emitted different version
  lines while invoking the same frozen executable bytes, so dynamically sourced version metadata
  is not an artifact identity.

### Inferences supported by the evidence

- Generic MoE membership, TP4 alone, model scale alone, quantization alone, and average memory
  stall share are not sufficient explanations for the tested dispersion.
- SMI is not a credible leading explanation for ab54.
- Box-wide CAL/TLB activity moves in the wrong direction for a simple
  more-interrupts-make-it-slow explanation, but localized IRQ displacement remains testable.
- The source-path presence is universal, so a gpt-oss-associated trigger, susceptibility, or
  upstream workload difference would be needed if the same path ultimately carries the effect.

These are exclusions or prioritization inferences, not a proved root cause.

## Assumptions and unknowns

### Verified facts

- The main gpt-oss reference launches roll at both tested TP geometries.
- The completed controls are tight at their tested shorter-generation configurations.
- The tested aliases share the streamed sparse-result consume.
- Current trace loss prevents reliable absolute mode-frequency and segment attribution.
- No current metric identifies the last releaser or residual work at WCLS completion.

### Assumptions requiring verification

- The frozen executable's dirty source tree differed from 29924aa86 only by the known changes
  later committed as 0b6cb1413.
- ab45 used the same gpt-oss model and workload declared in the documentary run plan.
- A ring can collect the required fields without materially changing cycle centers or mode
  frequency.

### Hypotheses

- A listener can lose RX-flight overlap and leave residual scan/heap work after WCLS completion.
- The trigger may instead be on-CPU throughput loss, readiness/poll cadence, callback/lock delay,
  latch/fan-in behavior, upstream RX-extent delay, or launch predecessor/plugin state.
- TP may dilute or amplify a fixed work quantum, but the required fixed-quantum and fixed-event
  assumptions are not measured.

### Unresolved facts

- Where the non-tail majority of the whole-token difference occurs.
- Whether the sharp and broad long populations survive lossless capture.
- Which worker or component is the last releaser.
- Whether the AMD and Intel dispersion share one mechanism.
- Whether a long-generation, workload-matched Llama control remains tight.

## Agreed solution

The proposed review solution is a gated measurement and intervention plan:

Gate 0: artifact and scope freeze
  -> Gate 1: coverage-gated retrospective analysis
  -> Gate 1.5: matched long-generation control
  -> Gate 2: low-tax ring plus lossless whole-cycle capture
  -> Gate 3: one meter-selected intervention
  -> Gate 4: scoped permanent fix and transfer validation

### Gate 0 — freeze artifacts, definitions, and scope

- Record full source hashes and executable hashes separately. Use the executable SHA-256 as the
  binary identity. Label dirty-tree source correspondence as inference unless a build
  attestation proves the full tree.
- Record exact argv, resolved weights, users, generation length, prompt length, TP/device
  geometry, binary, environment, and session for every arm.
- Define the reproduced problem around fresh gpt-oss runtron relaunches. Treat AMD generality and
  concurrent serving behavior as related evidence, not proof of one mechanism.
- State all control results with the 4096/1024 generation and u4/u8 user confounds.

### Gate 1 — retrospective analysis before new instrumentation

- Gate every ab49/ab58 trace on event conservation, nesting, clocks, listener identity, and
  draw-level coverage. Return Insufficient data if no defensible subset remains.
- Rebuild scheduler analysis around the actual listener TIDs and CPUs. Compare long, short,
  out-of-tail, and same-cycle sham windows; report off-CPU association without causal language.
- Re-gate perf samples to listener PID/TID and state sampling-collapse, PMI, and TSX limitations.
- Re-read ab54 /proc/interrupts on each mapped listener CPU, normalized by exposure time and
  decoded tokens/cycles.
- Recompute ab57 and r3 decompositions under one definition set.
- Audit model resolution, affinity, environment, process concurrency, and per-arm cycle walls.
  Confirm ab45 argv/model from andoria-06.

### Gate 1.5 — matched long-generation control

- Randomize and interleave fresh Llama-70B TP4 u4/l4096 and gpt-oss-120B TP4 u4/l4096 draws with
  identical non-model settings.
- Predeclare the dispersion rule, independent-draw unit, drift handling, target effects, maximum
  N, and error-controlled stopping rule. Include early/middle/late generation-block throughput
  as a secondary endpoint.
- If both models roll or the result is otherwise ambiguous, add a contemporaneous Llama
  u4/l1024 arm to distinguish generation/context from session drift.
- Interpret a tight matched Llama result only as support for a difference between the two tested
  model families under the matched workload. It does not establish a root cause.

### Gate 2 — measure the whole cycle with bounded perturbation

- Add a compile-time-gated, preallocated, cache-line-separated per-worker diagnostic ring.
- Record cycle/listener ID, WCLS completion, first/last RX, entries or blocks before and after
  completion, last releaser, polling/readiness gaps, heap pushes/replacements,
  sort/callback/countdown time, wall time, and thread CPU time.
- Run an A/A tax test with predeclared bounds before collecting confirmatory data.
- Require whole-cycle and inter-cycle conservation and additive reconciliation to measured
  per-token time. If exact-zero Perfetto loss is not demonstrated, use the ring as primary
  evidence and describe trace segmentation as descriptive.
- Use draws as the inferential unit. Preserve sharp-B versus broad-C structure and report
  threshold sensitivity.
- Trace a tight control only if Gate 1.5 establishes one at the long-generation workload.

### Gate 3 — one meter-selected causal intervention

Choose one branch from the measured signature:

- mapped foreign/off-CPU displacement: isolate or reassign the named source;
- on-CPU scan/heap residual: target the measured residual work;
- polling/readiness cadence: alter only the measured wait/poll mechanism;
- callback or lock delay: target the named callback/lock;
- latch/fan-in delay: target the measured release path;
- upstream RX-extent delay: target the measured producer/arrival path.

Interleave fresh baseline and treatment provisioning draws. Determine N prospectively from
draw-level power or a bounded sequential design. Validate semantics deterministically or with a
predeclared functional/numerical oracle.

Accept a root cause only when the intervention:

- moves the predicted meter;
- materially mediates the whole per-token difference;
- reduces launch dispersion toward the stated less-than-1% target with uncertainty reported;
- preserves unrelated stages and supported request modes.

If only the tail improves while most of the whole-token difference remains, classify it as a
partial mitigation and continue localization.

### Gate 4 — select and scope the permanent fix

- Choose the smallest semantics-preserving fix matching the causally confirmed branch.
- Scope the first conclusion and fix to the tested platform and configuration.
- Before claiming cross-platform applicability, repeat the relevant measurement and intervention
  on a matched AMD arm.
- Use gpt-oss-20B or another resolved, workload-matched model only if a model discriminator
  remains after localization. Verify its exact alias/configuration first.
- Keep TP-dilution analysis optional until matched data establish its assumptions.
- Keep invalid-vocabulary filtering and other independent defects in a separate hygiene backlog.

## Rationale

This plan is preferred because it first uses existing evidence at zero DUT cost, then adds the
smallest instrumentation capable of distinguishing the live hypotheses. It measures the entire
cycle and true per-token budget, avoids treating lossy trace segments as complete, and requires a
causal intervention before selecting a permanent fix.

The matched long-generation control closes the largest known comparison confound. The A/A tax
gate addresses the demonstrated risk that hot-loop tracing can change cycle timing. Draw-level
inference avoids false precision from thousands of correlated cycles within a small number of
launches.

## Contributions from the original proposals

- **From the Codex proposal:** shared streamed-path source analysis; low-perturbation per-worker
  ring; last-releaser and residual-work fields; A/A tax; whole-cycle accounting; one
  meter-selected intervention; whole-per-token mediation; deterministic semantic validation;
  conditional model discriminator.
- **From the Claude proposal:** early listener-CPU scheduler analysis; environment and affinity
  audits; explicit trigger-versus-amplifier framing; traced control; IRQ localization; direct
  overlap measurements; branch-specific predictions.
- **From joint discussion:** corrected 17–30% whole-token tail share; trace-loss qualification;
  AMD correction; removal of SMI as a leading branch; perfect generation-length confound;
  matched Llama control; exact-versus-inferred binary provenance; ab53 concurrent-runtron
  correction; bounded sample-size rule; platform-scoped validation.

## Alternatives considered

- **Adopt the listener-outage/full-sweep mechanism now.** Rejected because cursor position,
  residual entries, last releaser, and contention factor were not measured.
- **Adopt consumer backlog as the root cause now.** Rejected for the same missing measurements.
- **Use existing hot-loop spans.** Rejected because the prior span build added approximately
  335 microseconds per cycle.
- **Treat scheduler overlap as attribution.** Rejected because coincidence can identify a
  candidate but not causal responsibility.
- **Use current control CVs as a model-specific proof.** Rejected because generation length is
  perfectly confounded with ROLLS/TIGHT across the completed arms.
- **Run a neighbor-idle fix first.** Rejected as the next step because ab54 and ab60 already
  reproduce solo; ab53 concurrency is a separate scope experiment.
- **Escalate SMI/platform firmware first.** Rejected because ab54 directly recorded zero SMI
  increments.
- **Apply work stealing, bulk fallback, affinity, top-k reduction, or routing changes before
  attribution.** Rejected because each addresses a different hypothesis and can introduce
  semantic, race, or ownership risk.

## Trade-offs

- The plan costs more engineering work than enabling existing spans, but controls measurement
  perturbation and produces branch-discriminating evidence.
- The long-generation control and confirmatory intervention may require multi-hour campaigns;
  their runtime must be measured and budgeted.
- Strict draw-level inference needs more launches than cycle-level pseudoreplication, but gives
  defensible uncertainty.
- A conditional platform-scoped conclusion is narrower than a fleet-wide claim, but avoids
  transferring mechanisms across unmatched workload forms.
- Returning Insufficient data after retrospective gating may appear slower, but prevents a
  corrupted trace from selecting the wrong fix.

## Risks and mitigations

- **Instrumentation changes the lottery.** Mitigation: compile-time gating, preallocation,
  cache-line separation, and predeclared A/A bounds.
- **Trace loss or clock mismatch biases attribution.** Mitigation: conservation/clock gates and
  ring-primary evidence if exact-zero loss is not shown.
- **Within-draw cycles create false precision.** Mitigation: draw-level analysis with nested
  cycle summaries.
- **Campaign drift confounds model comparisons.** Mitigation: randomized interleaving, fresh
  positive control, and a contemporaneous Llama l1024 branch when needed.
- **Multiple exploratory thresholds create post-selection bias.** Mitigation: pre-register the
  primary threshold and report sensitivity.
- **Nondeterminism hides semantic regressions.** Mitigation: deterministic paired mode or a
  declared numerical/functional oracle.
- **A fix works only on Intel or one TP geometry.** Mitigation: scope the initial result and add
  matched AMD/TP validation before broader adoption.
- **Binary/source mismatch invalidates source conclusions.** Mitigation: make executable hashes
  primary and state source-content correspondence with its evidence level.

## Validation plan

1. Complete Gate 1 and publish pass/fail coverage tables before interpreting any association.
2. Run Gate 1.5 under a prospective draw-level decision rule and preserve all ambiguous outcome
   branches.
3. Demonstrate that the diagnostic ring passes its A/A perturbation bounds.
4. Demonstrate whole-cycle conservation and reconciliation to measured per-token time.
5. Show which measured component accounts for the fast/slow whole-token difference, with
   uncertainty across launches.
6. Choose one intervention from that signature and compare interleaved baseline/treatment
   launches.
7. Require meter movement, whole-token mediation, launch CV improvement toward less than 1%,
   semantic equivalence, and no unrelated-stage regression.
8. If broader applicability is claimed, repeat the relevant meter and intervention on matched
   TP and AMD configurations.

## Conditions that would change the recommendation

- A build attestation proving a different executable source tree would change the source scope
  and may require rechecking the streamed-path conclusion.
- A matched long-generation control that also rolls would weaken the model-family association
  and prioritize context/workload mechanisms.
- Lossless whole-cycle evidence locating nearly all variance in one already-measured component
  could remove unnecessary ring fields or later model splits.
- Evidence that no acceptable low-tax ring is possible would require hardware-assisted or
  externally sampled instrumentation.
- A causal intervention that fails whole-token mediation would demote that branch even if its
  local metric improves.
- Different Intel and AMD meter signatures would require platform-specific recommendations.

## Unresolved issues

None

## Confidence

Confidence is high that the current evidence does not prove either candidate mechanism and that
whole-cycle, low-perturbation measurement plus a causal intervention is required. Confidence is
moderate-high that the Gate 0–4 plan is the most efficient defensible route. Confidence in any
specific root cause is low until Gate 2 and Gate 3 succeed.
