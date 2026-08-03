# Codex follow-up review of Claude's AB58/AB59 report

**Reviewed:** 2026-07-30
**Revised source report:** `from-claude/ab58-report.md`, 63,557 bytes,
SHA-256 `E6619FDBCA15B62AE193AED141141B477CD91CD32B6DE7D3060AF4EE0F8CCDFB`
**Earlier source/review:** SHA-256
`57F7DEE0ED85EC76C3EEB9CE5003BB7743D9D81053CBF140FF06F97A7B682A5E`,
reviewed in `from-codex/ab58-report-review.md`
**Other sources:** `04-runbook-post-ab57.md` (standing rules and Part E),
the current tail of `02-investigation-plan.md`, `03-pal-consensus-log.md`,
`from-codex/simlot-S1-report-review.md`, and read-only checks of both AB59
artifact sets.

## Bottom line

I accept the new primary result in its narrow, configuration-specific form:

> Two consecutive same-evening AB59 rounds, each with 26 fresh analysis
> launches, classify `llama-3.1-8b-instruct-good-tp2 @8u` as **TIGHT** under
> the frozen Part-E rule.

Round 1 has population CV **0.2974%** and round 2 **0.3845%**; bootstrap
uncertainty, leave-one-out checks, and the nearly identical round means make
the threshold call very robust. This is strong evidence that the large
gpt-oss launch dispersion is **configuration/model dependent** and is absent
from this exact 8B w4a16, tp2, two-card, 8-user, g1024 configuration in this
evening epoch.

I do **not** accept the report's stronger claims that method rule 3 is
satisfied, that the result is an hours-apart confirmed replication, that A2
token determinism is answered, or that MoE/sparse-tail mechanisms have been
causally isolated. The two starts are only **59m06s apart**, and round 2 began
only **32m45s after round 1 restored**. That is a useful immediate repeat, not
the pre-registered hours-apart temporal replication intended to guard against
the campaign's known sub-hour/epoch behavior.

The report also analyzes the wrong IMC endpoint, overstates what the token
files prove, omits registered captures and analyses, has not completed the
required hostile/PAL workflow, and retains a stale machine-state section.
Those issues do not overturn the TIGHT primary, but they keep the broader
interpretation **provisional**.

| Claim | Follow-up assessment |
|---|---|
| Round 1 primary is TIGHT | **Agree.** |
| Round 2 primary is TIGHT | **Agree.** |
| The exact llama-8B configuration repeated tightly | **Agree.** Strong immediate-repeat evidence. |
| Standing method rule 3 is satisfied | **Disagree.** The rounds are not hours apart in the rule's intended sense. |
| Dense models generally do not roll | **Not established.** Only one dense configuration was tested. |
| The lottery needs MoE or the sparse/wcls tail | **Not established.** Those are leading candidates, not isolated causes. |
| A2/gpt-oss token determinism is answered | **Disagree.** AB59 tested llama-8B/u8, not gpt-oss/u4. |
| SEC1 mem-bound coupling repeated | **Numerically yes; mechanistically provisional.** |
| SEC2 IMC result is the registered endpoint | **No.** The script used MiB/s, not bytes/token. |
| Post-run state is healthy | **Yes, from journal/current checks.** Section 9 cites the wrong pre-AB59 snapshot and the CI timer remains disabled. |

## What changed after the first Codex review

The revised report adds Part E/AB59:

- one smoke plus 26 analysis launches in round 1, 20:48–21:14 UTC;
- an immediate second run of the same frozen kit, 21:47–22:13 UTC;
- exact model identity for the 8B w4a16 dense control;
- primary dispersion, topdown/IMC/TTFT/worker secondaries, and token hashes;
- a useful warning that a second kit launch rotates `results/` to
  `results.prev.<timestamp>` while repointing the bare path and overwriting
  root-level summary JSON.

The core AB57/AB58 assessment from my first review does not change. Original
Part B remains aborted, r3 remains adaptive, and the lossy r2/AB57 trace levels
remain exploratory. AB59 adds a clean no-Perfetto control; it does not repair
or replicate the trace localization.

## What the new test establishes

### 1. Execution and primary arithmetic are sound

Read-only artifact checks support the following:

- frozen orchestrator SHA-256:
  `ba336ea8b7c8bca4f1ba464e47042efb5bdc93fe37b32f2b74f7e07087c89b7d`;
- frozen runtron SHA-256:
  `d34f28b4d2e17b2bb4512a8a5daa06596d436141ae8c8c6140b804ec0dc0dec3`;
- round 1 preserved at
  `/scratch/jhan/ab59/results.prev.20260730214714/`;
- round 2 at `/scratch/jhan/ab59/results/`;
- each round has one excluded smoke and **26/26** successful analysis draws;
- no excluded, failed, substituted, or rerun analysis draws were found;
- the normalized harness command is identical across all draws except the
  required per-draw token-output path;
- both rounds use two devices, `10:00.0` and `13:00.0`, with speculation
  asserted off and complete 8×1024 token outputs;
- round 2's journal records `ALL_DONE`, `RESTORE_DONE`, and
  `RESTORE verified: trio serving (3 models)` at 22:13:42 UTC.

The drawmap hashes are:

- round 1:
  `8848290b9d25d38663f34dcca56946fba3a55952dadb2d21378cbac3d3749be5`;
- round 2:
  `ebc971d63803fec71f711e9f6fe76e1e42a8562f2a49080ba81d7572dbab5e3a`.

Independent primary recomputation:

| Statistic | Round 1 | Round 2 | Pooled, descriptive |
|---|---:|---:|---:|
| n | 26 | 26 | 52 |
| mean gen | 85.749014 | 85.743880 | 85.746447 |
| population CV | **0.297401%** | **0.384511%** | 0.343737% |
| sample CV | 0.303291% | 0.392125% | 0.347090% |
| range/mean | 1.02858% | 1.57868% | 1.57864% |
| seeded bootstrap 95% CI, population CV | [0.227%, 0.348%] | [0.286%, 0.468%] | — |
| leave-one-out population CV | 0.281–0.303% | 0.343–0.392% | — |

No bootstrap resample in 200,000 per round crossed the frozen **0.8%** TIGHT
threshold. The round-mean difference is −0.00513 t/s/u, with an approximate
95% Welch interval of **[−0.173, +0.162]**. Thus the narrow primary conclusion
is not a threshold accident or one influential draw.

### 2. The immediate repeat materially strengthens configuration dependence

The first round alone was a single-session control. The second shows that the
same tight distribution reappears after a fresh kit launch, fresh processes,
and a restore/reclaim cycle. That rules out a one-off lucky set of 26 launches
far more convincingly than round 1 alone.

The appropriate wording is:

> This exact llama-8B configuration was TIGHT in two adjacent same-evening
> rounds.

It is not yet:

> dense-model immunity is confirmed across an hours-apart epoch.

### 3. The report's exact-model scope paragraph is an important improvement

I agree with the new disclosure that the model is a 5.4 GB w4a16 dense model,
tp2 on two cards. That properly limits generalization. Relative to the
gpt-oss benchmark, however, the comparison changes more than the report's
listed four factors:

- dense versus MoE architecture and logits path;
- 5.4 GB versus a much larger store/KV footprint;
- quantization/model format;
- tp2/two-card versus tp4/four-card geometry;
- **8 users versus 4**;
- **g1024 versus g4096**;
- **27 versus 55 app workers** and the associated runtime geometry.

AB59 therefore supports model/configuration dependence. It does not identify
which of these differences is causal.

## Agreements

### 1. The TIGHT decision uses the registered branch correctly

Part E defines TIGHT solely as CV ≤0.8%. The missing within-draw block-CV only
gates the ROLLS branch, so its absence does not invalidate either TIGHT call.

### 2. The results-path warning is real

Launching round 2 rotated round 1 into
`results.prev.20260730214714/`, removed the completion flags, and made bare
`results/` refer to a live partial run. Root-level
`analysis_ab59_stats.json` and `token_determinism.json` were then overwritten
with round 2. The report is right that immutable launch-stamped directories
and versioned summaries are needed.

### 3. The repeat of SEC1 is worth preserving as exploratory evidence

Independent values are:

- round 1: Spearman ρ = **−0.49333**, permutation p ≈ **0.0111**;
- round 2: ρ = **−0.70371**, permutation p ≈ **0.00012**.

The repeated negative sign is evidence that ordinary residual efficiency in
this tight model covaries with topdown mem-bound share. It is also a useful
warning that this correlation alone is not a unique fingerprint of the large
gpt-oss lottery.

### 4. Restore succeeded

The round-2 journal records the policy check, three-model serving restore,
completion flags, and no kit/engine left running. A later read-only check found
rinzler@0–3 active, no runtron/orchestrator/tronsim/capture process, and no
jhan hugepage files. This is valid post-AB59 evidence, unlike the report's
section-9 timestamp.

## Disagreements and required corrections

### 1. This is not the registered hours-apart replication

Round 1 started at about 20:48:08 and restored at 21:14:29. Round 2 started at
21:47:14. Therefore:

- start-to-start separation: **59m06s**;
- round-1-restore to round-2-start separation: **32m45s**.

The report repeatedly calls this “hours-apart,” “an hour later,”
“REPLICATED,” and says method rule 3 is satisfied. The literal and scientific
purpose of the rule are not met: the runs remain in one short evening epoch,
and this campaign has already seen sub-hour/epoch effects. Call it a
successful immediate repeat. Run a truly hours-apart or different-day sealed
round before promoting the status to confirmed replication.

### 2. SEC2 analyzes the wrong endpoint

The runbook pre-registers **IMC bytes/token versus gen**. `stats_ab59.py`
instead computes aggregate IMC **MiB/s** and reports that correlation:

- report round 1: ρ = +0.241;
- report round 2: ρ = +0.237.

After applying the registered token denominator, the correct results are:

| | Mean bytes/token | ρ(bytes/token, gen) | p |
|---|---:|---:|---:|
| Round 1 | 19,045,001 | +0.11795 | 0.565 |
| Round 2 | 18,943,078 | +0.09643 | 0.639 |

The qualitative verdict remains null, but the report must replace the
estimand, units, and numbers. This is a pre-registered endpoint deviation, not
just a label.

### 3. Token evidence is real, but its interpretation is overclaimed

What the artifacts establish:

- 26/26 token files in each round;
- exactly eight users ×1024 tokens in every file;
- 26 distinct whole-file hashes and 26 distinct sorted-prefix hashes per
  round;
- no whole/prefix hash overlap between rounds.

What they do **not** establish:

- The report's “diverge from the first token” statement is false. The
  eight-user first-token tuple is identical across every audited draw. Across
  per-user comparisons the common-prefix length has minimum 2, median 22, and
  maximum 1024 tokens. Distinct 200-token hashes prove divergence somewhere
  in that prefix, not at token 1.
- Round-1 file sizes are **36,011–36,955 B**, not 36,011–36,123 B. Round 2 is
  35,881–36,786 B.
- The engine text makes closed-loop batch-context variation plausible; it
  does not prove that cause or exclude floating-point/reduction/order effects.
  `--pay-for-determinism` or u1 is still required.
- Every hash class is a singleton, so the registered “hash class versus gen”
  test is non-identifiable. The report should say so.

Most importantly, original A2 asks whether **gpt-oss** greedy streams are
draw-identical. AB59 tests **llama-8B at u8**. The report's status table and
TL;DR say A2 is answered while section 2.4 still says it is unresolved and
section 8.3 still prescribes the clean test. The correct status is:

> llama-8B/u8 outputs differ across launches; gpt-oss A2 and the causal source
> of the differences remain unresolved.

AB49's gpt-oss/u4 4×1 batch-shape observation also does not bound the llama/u8
content confound or show that token values are performance-irrelevant.

### 4. Registered captures and analyses are missing

Part E requires, per draw, the standard block including a dram probe, inode
witnesses, and per-block rate series. The frozen orchestrator/archive show:

- no dram-probe invocation or artifact;
- a prelaunch hugepage-file listing, but not the full registered witness set;
- no per-block rate series;
- consequently no registered rank-stationarity analysis.

The report discloses only the missing ROLLS block-CV. It should also disclose
the missed mandatory capture and rank-stationarity endpoint.

The runbook also says to confirm on the smoke that token-file output has no
gen effect before freezing. The header was already frozen and there is no
token-output versus no-output control; one output-enabled smoke can detect a
gross failure, not establish zero I/O tax. Because every analysis draw used
the same output mechanism, this is unlikely to create the observed
across-draw TIGHT result, but it is still an execution deviation.

### 5. SEC1/SEC3/SEC4 interpretation remains too strong

- SEC1 is one secondary among several, with no confidence interval,
  multiplicity plan, or temporally independent replication. Its metric is
  not the gpt-oss cycle-share metric. “Coupling repeats” is fair; “the same
  signature transfers” is stronger than the design.
- TTFT ρ is −0.0687 in round 1 and −0.1426 in round 2, both nonsignificant.
  This is consistent with a prefill null; it does not prove every residual
  variation is decode-side.
- Worker-CV ρ is −0.1364 (p=0.506) and −0.2202 (p=0.276). Failure to reject is
  not equivalence and does not independently corroborate A9. It means no
  association was detected in a very narrow throughput range.

### 6. Mechanistic narrowing still overuses S1, A9, and lossy traces

The report continues to treat these as exclusions:

- S1 excluding tron's thread/core shape, **scale**, membind, spin tail, and
  TSX as sufficient;
- A9 closing the laggard-core class;
- AB57/r2 having localized “exactly” the sparse/wcls window.

Those claims exceed the audited evidence:

- The S1 review accepts only “this simulator configuration did not
  reproduce.” S1 used about 46 GiB versus roughly 210 GiB for tron, anonymous
  mappings rather than the full hugetlbfs/device path, no FPGA/VFIO/DMA, and a
  radically different tail anatomy. It did not test tron scale or all listed
  ingredients faithfully.
- A9 shows no detected large **relative-share redistribution** in its
  normalized metric. It is not an equivalence test and cannot prove every
  worker slows uniformly in absolute time.
- AB57/AB58 trace levels have informative 19–41% loss, original Part B
  aborted, and r2's 83.5%/76% values are one lossy soak's observed-subsample
  liveness/coverage. They are hypothesis-generating, not confirmed
  localization.

The supported next-step wording is:

> If a properly matched, temporally replicated llama-70b-tp4 arm is also
> TIGHT, MoE/sparse-path explanations become leading candidates.

It would not by itself prove them.

### 7. Required hostile verification and PAL Gate 7 are absent

Part E explicitly requires the standard eight-agent hostile workflow. No
AB59 hostile-review archive is identified, and `03-pal-consensus-log.md`
still has no Part-E/Gate-7 entry. The lab log was updated, but that is not a
substitute for the registered verification or PAL gate. This Codex review is
one independent/adversarial audit; it does not retroactively satisfy the
specified workflow.

The A4 strip plot also still reports 311 draws across ab44–ab58 rather than
adding the required dense-model CV row.

### 8. Section 9 is stale and the timer statement remains false

Section 9 cites a **19:52 UTC** state snapshot, before both AB59 rounds. It
must cite the 22:13:42 restore and/or a post-run snapshot.

Current read-only state was healthy, except that
`ci-runner-start@delphi-3bda.timer` was **disabled/inactive with no next
trigger**. The report's “timer re-arms itself tomorrow” statement is therefore
not verified and was false at review time.

### 9. Audit-side deviation during round 2

For transparency: a malformed Codex read-only SSH grep, launched just before
round 2, left one sleeping `bash` plus its blocked `grep` child on the DUT for
the whole round. At 22:19 they were:

```text
24759 ... S ... bash -c grep -nE RUNTRON|BENCH_BIN|BIN= ...
24791 ... S ... grep -nE RUNTRON
```

I identified and removed exactly those two stale processes at about 22:20,
then verified no benchmark/capture process remained. They were blocked in
sleep, were present as a fixed covariate across the round, and cannot
plausibly create the observed draw-to-draw TIGHT dispersion. Nevertheless,
round 2 was not a perfectly pristine-machine replication, and this audit-side
contamination belongs in the record.

## Limitations

I did not rerun the benchmark or mutate its artifacts. All AB59 artifact
analysis was read-only, primarily from the off-DUT shared mirror. Root-level
summary JSON now represents round 2; round 1 was independently reconstructed
from its immutable draw archive. The review cannot verify who physically
launched round 2 beyond the report/user record.

The model-control conclusion is also inherently conditional: no experiment
here separates density, sparse-logits behavior, footprint, quantization,
topology, user count, generation length, or worker geometry.

## Recommended next steps

1. **Correct the report status.** Replace “hours-apart confirmed replication”
   with “successful adjacent same-evening repeat”; keep the configuration
   TIGHT result, but mark broader mechanism claims provisional.
2. **Run one genuinely separated sealed round.** Use the same frozen kit after
   several hours or on a different day, with no audit/background processes.
   Publish launch-stamped artifacts and summaries.
3. **Fix the registered analysis.** Compute IMC bytes/token, report the missing
   dram/inode/per-block/rank-stationarity captures, add CIs/multiplicity
   discipline to secondaries, and test token-output overhead.
4. **Resolve token causality.** Run the pre-registered
   `--pay-for-determinism` and/or u1 control. Keep gpt-oss A2 open until tested
   on gpt-oss with stable request/position keys.
5. **Before llama-70b, freeze actual comparability.** Record resident/touched
   store and KV footprint, exact quantization, tp/card and worker geometry,
   users, generation length, speculation, device identities, and token-output
   behavior. Interpret a tight result as narrowing, not proof of MoE causality.
6. **Complete the process gates.** Perform the registered hostile workflow,
   append PAL Gate 7, add the AB59 CV row to the A4 plot, and version both
   rounds' analysis JSON beside immutable result directories.
7. **Repair operations/bookkeeping.** Update section 9 with the post-AB59
   snapshot and fix the disabled CI start timer through the owning workflow.

Overall: AB59 contributes a strong and useful configuration-specific negative.
Two adjacent rounds show that this llama-8B setup is far tighter than the
gpt-oss launch sets. That result meaningfully narrows the experimental search,
but the report currently promotes an immediate repeat into a method-confirmed
replication and promotes correlated controls into mechanism exclusions. Those
promotions should be rolled back while preserving the solid TIGHT primary.
