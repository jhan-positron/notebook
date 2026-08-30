# Review of the Decode-Lottery Handoff Files

Reviewed:

- `status_report/handoff-2-Bill-delphi.precheck.md`
- `status_report/handoff-2-Bill-delphi.testing.md`

## Conclusion

I agree with the concern, with one important distinction: the investigation has
not lost its target yet, but further layer-by-layer decomposition probably
would.

The results have established a useful parent-level target: the repeated,
once-per-token end-of-step path from the attention/lm-head boundary through
streamed-logits handling, token selection, callback work, and the start of the
next step. The handoff says that per-layer work, per-job card latency, host
memory behavior, hugepage placement, and PCIe state are flat across the
lottery. In contrast, several adjacent portions of this end-of-step path
co-stretch in slow launches.

The newer testing handoff explicitly recognizes the decomposition limit in
section 3.5. On delphi-3bda, the fast-to-slow loss has divided into several
segments with deltas of approximately +313k, +183k, +104k, and +27k cycles.
Those shrinking child values do not mean that the overall finding is becoming
unimportant. They are partitions of the same parent delay.

## Why continued decomposition can become misleading

Repeated subdivision mechanically makes every child's absolute contribution
smaller. It can therefore produce the appearance that there is no meaningful
target, even when the parent path still accounts for most of the launch-level
performance difference.

More importantly, a shared underlying cause may delay several consecutive
segments. Examples include CPU scheduling interference, housekeeping or timer
activity, a frequency-state difference, resource mapping, or backpressure
crossing the card/host boundary. In that situation, finer timestamps identify
where the delay manifests, not what causes it.

Several properties in the handoffs point toward a shared cause rather than a
single slow leaf operation:

- Multiple adjacent boundary segments co-stretch in slow launches.
- Per-step distributions are heavy-tailed rather than uniformly slower.
- Slow launches contain more or heavier stalls.
- Work outside the end-of-step path remains flat.
- Each additional split reduces the individual deltas without isolating a
  uniquely dominant operation.

Segment correlations also should not be treated as independent contributions.
Adjacent timing segments can be correlated with one another, and TPS is
mathematically related to their combined elapsed time. Ranking the correlations
does not, by itself, identify a causal owner.

## Recommended stopping rule

Continue decomposing only while a split creates meaningful discrimination—for
example, one child dominates while the others remain flat, or the children
respond differently across launches.

Stop decomposing when all of the following are true:

1. Several adjacent children co-stretch.
2. Their individual deltas shrink as boundaries are added.
3. Heavy-tail stall behavior appears across multiple children.
4. The split does not distinguish between competing causal hypotheses.

At that point, retain the common parent path as the performance target and
switch from localization to controlled interventions.

## Recommended next phase

Bill's machine should be used for one cross-host replication, as specified by
the newer testing handoff:

- First determine whether the machine exhibits the lottery at all.
- If it is tight, stop and treat host dependence as the primary finding.
- If it rolls, perform one boundary decomposition to determine whether the
  same parent path stretches.
- If the result matches delphi-3bda, do not continue splitting the path.

The next experiments should each change one plausible shared cause and measure
whether the overall TPS CV and the complete end-of-step delay collapse or
remain:

- Pin or isolate the relevant threads and move candidate interferers such as
  platform or housekeeping work elsewhere.
- Control core and uncore frequency state.
- Vary the stream/consume configuration.
- Examine existing traces for periodic, clustered, or cross-segment-aligned
  stall events.
- Add card-side stream-arrival visibility for the fill segment only if it can
  distinguish card-side delay from host-side consumption or scheduling delay.

Each intervention should be evaluated against the parent-path delay first;
child segments are diagnostic evidence, not competing top-level targets.

## Reporting recommendation

Future reports should present two levels of attribution together:

1. The contribution of the complete end-of-step parent path to the total
   fast-versus-slow launch difference.
2. The distribution of that parent-path difference among its measured child
   segments.

The report should also include a residual so that the parent decomposition can
be checked against the total observed token-time or TPS difference. This keeps
the main finding visible even as the measured children become smaller.

## Overall assessment

The concern is valid. Requiring a single increasingly narrow subtask to retain
a large share of the whole fluctuation would lead to an artificial “no clear
target” conclusion. The current evidence instead supports a clear parent-level
target—the end-of-step synchronization and logits-consumption path—and suggests
that the investigation should now pivot from finer attribution to
hypothesis-driven causal intervention.
