## session=20261114T171124Z-c1a5 round=1 role=worker status=START digest=- time=2026-11-14T17:11:24Z

Initial file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md
Review file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md.review.md

Scope: design an investigation of the small old-to-new read bandwidth gain at 8 MiB. The deliverable is tackle-8mb.md. No benchmark campaign or implementation is included in this task. The design will distinguish the original size comparison from the measured effect of the preceding loop, and define controls, decision rules, limits, and follow-up branches.

The worker is reading the existing benchmark, result files, and host rules. A READY entry will follow after the design and local checks are complete.

END ENTRY


## session=20261114T171124Z-c1a5 round=1 role=worker status=READY digest=a34d091505d4df4fd8e41fe4488f38356fa13e9cf84f606f0a113a6169454cb8 time=2026-11-14T17:18:10Z

Initial file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md
Review file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md.review.md

The requested design is complete for review. The scope is a design for the small old-to-new read gain at 8 MiB, not an implementation or a new measurement campaign.

The design distinguishes the buffer-size question from the nearby-rate variation. It starts with the observed B6 position effect, controls predecessor and target on one mapping, tests the actual new read loop as well as assembly read, and requires a separate old/new comparison across sizes. It names the current wrapper's warm-up, page reads, barriers, and output as possible influences. It specifies a one-thread trial mode, continuous target windows, measurement-overhead checks, balanced schedules, per-process comparisons, decision limits, exclusions, confirmation sessions, and conditional counter/mechanism tests. It does not use the earlier low/high thresholds to exclude data.

Reviewer focus:
- Can the proposed experiment distinguish a predecessor effect from changes introduced by its own measurement wrapper?
- Do the primary contrasts and size comparison answer the original read-gain question?
- Are the controls, sampling units, schedules, decision rules, quality checks, and conditional branches sufficient and consistent?
- Do the conclusions distinguish a reproducible effect from an established mechanism?

Validation performed locally:
- Read the existing worker, call dispatch, main interval loop, B6 schedule, prior handoff, reviewed results, and saved recount.
- Recomputed the original four best-rate read comparisons from one-thread.csv. Every old/new rate and rounded gain in the design matches.
- Verified that all 7 reference identifiers are defined and all 10 absolute cited paths exist.
- Computed nominal work: Stage 2 = 3110.4 s, Stage 3 = 2073.6 s, sustained uncounted Stage 4 = 1440 s, total = 6624 s (110.4 min). The document excludes acceptance work, counters, conditional branches, and runtime overhead from this total.
- Checked the schedule construction: 24 cycles of 12 conditions place every condition at every position exactly twice.
- Checked balanced Markdown fences and text-diagram widths of at most 70 columns. Read the prose against the plain-english rules.

Not run: Stage 0's full reanalysis and HTML output, implementation tests, AArch64 builds, machine-code acceptance for a new binary, or any experiment on CRB. These are proposed later work. No remote login, root command, or external message was made. No old result, benchmark source, or prior plan was changed.

END ENTRY

## session=20261114T171124Z-c1a5 round=1 role=reviewer status=COMMENTS digest=- time=2026-11-14T17:29:59Z

The digest of tackle-8mb.md matches READY (a34d0915...69454cb8) before and after the checks. Line numbers below are those of that version.

How this review was made: four reviewer agents read the design against the sources (facts, experiment design, "does it answer the question", consistency). A second agent per angle tried to refute each finding with its own recount. 35 findings were raised, 22 were confirmed, and the confirmed ones are merged into T1 to T10. The rejected ones are listed at the end.

### T1 (high) — The predecessor effect was absent from the run that raised the question, and it has the wrong sign

Location: lines 5, 49, 146-169, 261, 279-280.

Problem:
- The design never states how the original run was ordered. In that run every (binary, kernel, size, CPU, round) was its own process. Before a timed read repetition the process ran a first-touch write, a warm-up pass of the same kernel, and earlier repetitions of the same kernel. No other read loop ran before the timed loop.
- So line 49 is wrong for the history inside a process ("does not hold ... recent execution history constant"). Only the allocation and the preceding process differ.
- In B6 the predecessor effect lowers old read. A slower old read makes the old-to-new gain larger, not smaller. So this effect cannot produce the 0.94 %.
- The small gain is not a product of the best rate. It is in each of the 4 process pairs.
- Stage 2 is the first and largest measurement stage (51.84 of 110.4 min). The row at line 261 would let a confirmed interaction be read as "contributes to the small gain", for an effect that the original run did not contain.

Evidence:
- /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh lines 58-70: "One process per (binary, kernel): no kernel is timed after another kernel in the same process." The launch has `--kernel "$3" --reps 3 --min-ms 500`, CPUs 0 and 2, sizes 32K 1M 8M 1G, 2 rounds.
- one-thread.csv has 192 `-- binary` headers, 96 for CPU 0 and 96 for CPU 2, each with one kernel.
- The worker of the original benchmark (bandwidth.c in the same scratch folder, and /home/jhan/workspace/titan/cache-perf/bench/bandwidth.c lines 458-481): first touch with k_write, then per repetition a warm-up pass of the same kernel, then the timed passes. Best is the maximum inside a process.
- Recount of one-thread.csv at 8 MiB, all 12 repetitions: old read 66.97 to 67.08 GB/s, new read 67.36 to 67.71 GB/s. Gain of the per-process medians: 0.51 %, 0.69 %, 0.94 %, 0.51 %. At 1 MiB it is 27.01 % in all 4 pairs.
- Recount of both B6.csv files: old read at 8 MiB directly after asm read has process medians of 61.03 to 65.18 GB/s. Old read after old read at 1 MiB (sequence position 5) is 66.91 to 67.08 GB/s in all 192 intervals. That equals the rate of old read alone in the original run.

Requested correction:
- State the structure of the original run in "What the existing evidence supports": one read kernel per process, CPUs 0 and 2, 2 rounds, first-touch write, warm-up pass of the same kernel, 3 repetitions of 0.5 s, and the table value as the maximum over 12 repetitions of 4 processes. Add that the small gain is in each of the 4 process pairs.
- Correct the last sentence of line 49.
- State that the B6 effect lowers old read and so enlarges the gain.
- Label Stage 2 in the Short version and in its own heading as a test of the effect seen in mixed sequences (issue 2), not of the original gain.
- Reword line 261, for example: "History changes the gain measured in an interleaved sequence. State the sign and size. It does not explain the gain of the original run, which had no other read loop as predecessor."
- Either run the size experiment before Stage 2, or make Stage 2 conditional on a Stage 0 or Stage 3 result that needs it. Update lines 279-280 and the diagram to match.

### T2 (high) — No candidate explanation of the size comparison, and no bounded prediction for it

Location: lines 57-62, 197-212, 240-266.

Problem: line 5 says that a successful investigation must explain the small gain, and line 59 names the size comparison as issue 1. No stage states a candidate explanation of it or a prediction that a measurement could reject. Stage 3 can only end with "the predecessor effect does not fully explain it" (lines 209, 262), which restates the question. The only test aimed at the size comparison is the conditional 4-`nop` row of Stage 5. A candidate exists in the sources (H1 of plan.md), the saved numbers fit it, and the design names H1 only inside the entry of [Ref2].

Evidence:
- plan.md, H1 and "What the existing files already show" items 3 and 4: old read is limited inside the core at every size that fits a cache, the load-only loop at 8 MiB is limited by the path from the SLC, and the two limits are close on CPUs 0 and 2. The plan says that this answers Q1a in part.
- Recount of one-thread.csv, all repetitions: old read 66.64 to 66.76 GB/s at 32 KiB, 67.12 to 67.13 at 1 MiB, 66.97 to 67.08 at 8 MiB. New read 132.06 to 133.22, 85.24 to 85.26, 67.36 to 67.71 GB/s. So new read carries the change of the gain between 1 MiB and 8 MiB (17.55 GB/s), and old read moves by 0.05 GB/s.
- crb-memory-hierarchy.html: L2 is 2 MiB and private. So 1 MiB fits in L2 and 8 MiB does not.
- results.md gives H1 the word "rejected" with an open second reading. The failure came through the position effect only.
- Against a pure "smaller of two limits" reading: at 1 GiB old read is 28.72 against 30.89 GB/s for new read. The design should say that the candidate does not cover that size.
- results.md lines 25-26 name the first missing evidence for Q1: a comparison of old read between the low and the high level at 8 MiB on one CPU. The design has no analysis that relates the old-read rate to the load-only rate, and Stage 4 runs new read and asm read only.

Requested correction:
- Add a short section before the first measurement stage with the candidate explanation carried over from H1, its status in results.md, and what it does not name (what holds old read near 67 GB/s).
- Give it bounded predictions that Stage 3 can test under same-kernel preparation, and say which outcome rejects it. For example: (1) old read at 8 MiB minus old read at 1 MiB stays inside its two-rate limit; (2) new read and asm read at 8 MiB are below their 1 MiB rates by more than the limit; (3) per process at 8 MiB, old read does not rise with the load-only rate.
- Add the two per-kernel size contrasts of (1) and (2) to the Stage 3 rule, next to the four-rate contrast of line 207. That contrast alone (about 0.6 against about 18 GB/s) can only confirm the question. Report the share of the change of the gain that each kernel carries.
- For (3), add the per-process analysis at 8 MiB (old-read rate against asm-read and new-read rate, fourth window, with the range of each). It needs no extra run. Add old read to the sustained runs of Stage 4, or alternate long blocks of old read and asm read in one process, so that a level change can be compared with old read.
- Add one row for this result to the table "What counts as progress".

### T3 (medium) — Three sizes cannot locate where the gain shrinks

Location: lines 201-207.

Problem: 32 KiB, 1 MiB and 8 MiB are the three points of the question, one per cache level. They can reproduce the table. They cannot show where the load-only rate meets the old-read rate, which is what the candidate of T2 predicts. Old read has no saved one-thread measurement at 2, 4, 16 or 32 MiB.

Evidence: recount of the asm-read reference intervals of both B1.csv files (process medians, 16 processes per size and session): 4 MiB 73.08 to 75.73 GB/s, 8 MiB 67.88 to 70.46, 16 MiB 64.83 to 66.25, 32 MiB 63.28 to 64.03. So the load-only rate passes 67.1 GB/s between 8 and 16 MiB, outside the planned range. B1 held two buffers, so these values are est. for a one-buffer run.

Requested correction: add at least 4 MiB and 16 MiB to Stage 3 as separate allocations (2 MiB and 32 MiB if the budget allows). Write the predictions before the run and label them est. Update the budget table: each added size is 24 processes and 691.2 s of nominal kernel work. If Stage 2 becomes conditional (T1), say that this pays for the added sizes.

### T4 (medium) — Stage 0 has no stopping condition and leaves out saved data that carry part of the answer

Location: lines 79, 81-91, 279.

Problem: line 79 says that each stage has a stopping condition. Stage 0 has none, and no later stage is gated on its outcome. Items 1 to 5 do not name the B1 reference intervals (asm read at 4, 8, 16, 32 MiB), the run at 06:05 UTC (old read and load-only loops in one process at the high level), the cache sizes, or the absolute rate of old read at B6 position 5. Item 2 asks only for the first and second interval of the A/A pairs.

Evidence: the recounts of T1 to T3. results/cread-20261113T060510Z/cread.csv at 8 MiB: old read 67.07 to 67.12 GB/s in all 4 processes, asm read 70.94 to 71.07 GB/s in 3 of them.

Requested correction: add two Stage 0 items. (6) A table of old, new and asm read by size from one-thread.csv, cread.csv and the B1 reference intervals, next to the cache sizes, with B1 marked as a two-buffer run. (7) Old read at 8 MiB by B6 sequence position as absolute rates, with the asm-read rate of the same process. Add a stopping condition that says which stage runs next for which Stage 0 outcome.

### T5 (high) — The schedule ties each condition to one preceding trial, in an experiment about history

Location: lines 158-159, 177-181, with 21 and 123.

Problem:
- All 24 orders of a CPU/session are cyclic shifts of one permutation. A cyclic shift keeps the neighbour order. So a condition follows the same other condition in 22 of its 24 occurrences. The previous trial ends with 1.2 s of one target kernel, so "target of the previous trial" is confounded with the condition for the whole CPU/session.
- The A/A split (cycles {1,3} against {2,4}) has the same preceding trial in both halves. So the limit holds none of this variation.
- A carry-over has the same sign in all 6 processes. So the rule "median above the limit and 6 of 6 with one sign" can fire on carry-over alone inside one CPU/session.
- No check shows that the 1.2 s old-read prefix removes the influence of the previous trial. Line 21 says that the prefix is not assumed to reset the hardware.
- Line 159 calls the 24 units "independent". Lines 20 and 27 say why that is not established, and the 6 processes of a CPU/session share one schedule family.

Evidence:
- Simulation of the stated construction, 20,000 schedules: the share of occurrences with the same preceding condition is 22 of 24 in every schedule. The two conditions of primary contrast 1 have different dominant previous-trial targets in 72.9 % of the schedules.
- Recount of both B6.csv files: the second old-read interval after asm read (positions 8 and 11, 0.3 to 0.6 s later) has medians per CPU and session of 64.75 to 66.98 GB/s. Position 5 is 66.91 to 67.08 GB/s. So 0.3 s of old read at 8 MiB does not always restore the rate. Line 51 cites the first interval only. Insufficient data: whether the effect outlasts 1.2 s. No B6 interval is that far after asm read.

Requested correction:
- Replace the schedule of line 158 by one in which the preceding condition varies for each condition (for example a Williams design for 12 conditions, or a separate random permutation per process and cycle). Record the previous trial's target in every trial row (line 127).
- Record the 1.2 s prefix in four 0.3 s windows. Add a Stage 1 check, with the existing rule, that the last prefix window and the first target window of old read do not depend on the previous trial's target. Say what follows if they do (a longer prefix, or the previous target as a blocking factor).
- Add the B6 observation on the second interval to the evidence section.
- Line 159: write that the 24 units are processes with a fresh allocation each, and that their independence is not established.
- Add a carry-over case to the synthetic analysis tests of line 298.

### T6 (medium) — The CPUs of the question are 0 and 2, and CPU 41 has another baseline

Location: lines 16, 99, 159, 181, 209.

Problem: the four gains of the table come from CPUs 0 and 2 only. The design leaves out CPU 0 and adds CPU 41, and says neither. The saved data show that the load-only rate at 8 MiB is higher on CPU 41 while old read is the same. So "the small 8 MiB gain remains" (line 209) has two different baselines, and one is not a configuration of the question.

Evidence: run_kernels.sh line 68 (`for cpu in 0 2`). B6 recount, asm-read reference against old read at position 5: CPU 2 +0.19 % (s1) and +0.28 % (s2), CPU 41 +2.66 % and +2.60 %. B1 at 8 MiB: 67.88 to 68.75 GB/s on CPUs 0 and 2 against 70.07 to 70.46 GB/s on CPUs 41 and 94.

Requested correction: state in the evidence section which CPUs produced the table and that the baseline gain differs per CPU. Name CPU 2 as the CPU that reproduces the question, and give the reason for CPU 41 and for leaving out CPU 0. Give the expected Stage 3 gain per CPU as est. Say that a gain that differs between the two CPUs is a result per CPU under line 181, not a failed confirmation of the size answer.

### T7 (medium) — Two gates pass when the rule does not fire

Location: lines 120, 139, 142, 231, 235, against 183.

Problem: the measurement-overhead check and the counter mode check "pass" when the Stage 2 rule finds no resolved mode difference. That rule is built to be hard to fire, and a noisier measurement gives a larger limit. So the gate passes more easily when the measurement is worse. This contradicts line 183, which says that a value inside the limit is no proof of equality. No line bounds the limit for a pass.

Evidence: the rule of the design applied to B6 gives two-rate limits of 0.45 to 2.84 GB/s for old read after another loop. That is a large share of the 3 to 5 GB/s effect.

Requested correction: define "pass" for both gates as an equivalence result. Pass only if the median mode difference is inside the limit and the limit itself is below a margin in GB/s that is fixed before collection. Otherwise the word is "mode equivalence not established", and the fine bins or the counted contrasts stay descriptive.

### T8 (medium) — The counter check has no arm without an open counter group

Location: lines 230-231, 235, against 53.

Problem: all three arms keep the counter groups open, and two of them are called "uncounted". So the check measures only the cost of reading counters at the boundary. The Stage 2 timing mode has no group open. Line 53 keeps open that counters relate to the missing high rates, and that is a comparison of "open" against "not open".

Evidence: bwx.c opens the groups only under `--count` (line 985). C1 is the B4 command plus `--count`. C1 has 0 of 800 intervals above 70.5 GB/s in each session, and B4 has processes that stay above it.

Requested correction: rename the arm "open, not read", and state that this check does not compare against the Stage 2 mode. Then either add trials with no group open to the same check, or state before collection which comparison tests the effect of open groups (the counted repeat of line 235 against the Stage 2 batch, and the counted against the uncounted Stage 4 batch), and that this comparison is between batches.

### T9 (medium) — The compatibility check has no criterion

Location: lines 138, 144, 279.

Problem: line 138 runs 2 processes per CPU and session and reports a "failure to reproduce the old positional effect". Line 144 applies the rule "below" to acceptance comparisons. That rule needs 6 process values and calls fewer "incomplete" (lines 180, 185). So neither "reproduced" nor "failure" is defined, and this is the control that guards against the new wrapper removing the cause. "Use the same binary's unchanged wrapper as the reference" does not say which quantity is compared with which.

Requested correction: fix the criterion before the run. For example: reproduced on a CPU in a session if, in both processes, the first old-read interval after asm read is the slower one in all 8 pairs (B6 gave 192 of 192 in each session). Or run 6 processes and apply the Stage 2 rule to the B6 pair value. State whether a failure blocks Stage 2 or is only reported.

### T10 (low) — Four places where the wording contradicts another line

- Line 100: "matching the earlier size comparison" is true for the B6 sequence only. In the original run 1 MiB had its own process and allocation. Name B6.
- Lines 167 and 182: the asm-predecessor contrast is "a specified replication" in line 167 and falls under "all other ... contrasts ... exploratory" in line 182. It is the only contrast with earlier evidence. Give it one status in both places.
- Lines 191-194: line 191 "rejects" a trial, lines 192-193 "mark" one, and line 194 needs all trials to "meet the declared quality checks". State whether a marked trial fails. Line 194 needs all 48 trials of a process, and a primary contrast uses 16 trials of 4 conditions. Apply completeness per contrast, or say why not. Say how "the worker was interrupted" is detected.
- [Ref1] and the task text name `bench/bandwidth.c` without a path. The file is /home/jhan/workspace/titan/cache-perf/bench/bandwidth.c, and the copy that built the original binaries is in tmp/agent-scratch/kernels-2026-11-13/. Add the path of the original run script and source to the references when T1 is corrected.

### Checked and found correct

- The gain table: old 66.76 / 67.13 / 67.08 / 28.72 GB/s, new 133.22 / 85.26 / 67.71 / 30.89 GB/s, gains 99.55 / 27.01 / 0.94 / 7.56 %.
- The B6 statements of lines 51-52, the B4 and C1 statements of line 53, and the description of the bwx worker in lines 54-55 and 117 (warm-up pass, page reads, barrier, volatile sink, clock check every 8 MiB).
- [Ref1] to [Ref7] resolve and hold what they are cited for.
- The budget arithmetic: 3,110.4 s, 2,073.6 s, 1,440 s, 6,624 s, 120 processes.
- The position balance of line 158 is true over the 24 orders of a CPU/session. The defect is the neighbour order (T5).

### Raised by a reviewer agent and rejected by its verifier (not findings)

The 0.3 s length of the predecessor; the sensitivity of the four-rate limit; pairing by index in the size contrast; the strictness of the exclusion chain as a stop risk; position balance inside one process; a floor for the limit; the exclusion of 1 GiB; the use of "prefix" and "trial" in Stage 3; the wording of row 260; the completeness of the host-rule list.

### Not done in this review

No run on CRB, no build, no change to any file except this entry. The feasibility of the trial mode inside bwx.c was read from the source and not tested. The Linux and processor event definitions were not checked.

END ENTRY

## session=20261114T171124Z-c1a5 round=2 role=worker status=READY digest=530767c13109fbc7c02dd1423cbfdc43d81c9286c18374b5886be2c134576fb0 time=2026-11-14T17:44:56Z

Revised initial file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md
Shared review file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md.review.md

All T1–T10 are accepted. The main change is to test the size explanation first with one read kernel per process, matching the structure of the original experiment. Mixed sequences are conditional. The same-allocation analysis therefore becomes a separate conditional branch with its own prefix check and stated cost.

### Replies

- **T1:** Added the original CPUs, rounds, first-touch write, same-kernel warm-up, three repetitions, per-process structure, and maximum-of-12 estimator. Recomputed all four 8 MiB process-median gains (0.51%, 0.69%, 0.94%, 0.51%). Corrected the history claim and the sign: slowing old read enlarges the gain. The size sweep is now Stage 2. Stage 3 and the conclusion table explicitly limit the predecessor effect to mixed sequences.
- **T2:** Added H1's candidate, its conflicted prior rejection through B6 position, its unresolved resource, and its exclusion of 1 GiB. Defined bounded P1/P2 size predictions and P3's descriptive old-versus-load-only endpoint check. Added each kernel's size contrast and the signed decomposition of the lost absolute advantage. Old read now has sustained runs. Unlike the original paired draft, the primary sweep now preserves one kernel per process. P3 therefore needs a separately budgeted paired-allocation branch. Its selected extrema do not count as six independent interventions, and a contrary relation requires a new controlled state comparison before rejecting independence from the load-only state.
- **T3:** Added 4 MiB and 16 MiB, retained 32 KiB, 1 MiB, and 8 MiB, and explicitly deferred 2 MiB and 32 MiB. Added estimated rate ranges based on B1, with the two-buffer limitation. One kernel per process makes each added size 72 processes instead of 24; read time remains 691.2 s. The primary five-size sweep is 360 processes and 3,456 s. Conditional history work is 3,110.4 s. Acceptance costs are separate.
- **T4:** Stage 0 now requests the 06:05 run, B1 reference rows, cache sizes, and absolute old rates by every B6 position, including position 5. Added a completion condition and explicit routes to reconciliation, the primary sweep, or conditional mixed-sequence work.
- **T5:** Replaced cyclic shifts by the stated 12-condition balanced construction. Verified that all 144 position/condition combinations occur twice and all 132 ordered pairs of distinct neighboring conditions occur twice within rows. Boundary transitions are recorded and are not claimed balanced. Added previous-condition/target records, four prefix windows, an explicit carry-over acceptance check, longer-prefix alternatives, and a stop if equivalence fails. Removed the independence claim. Added the second-interval B6 limitation and a synthetic carry-over-only case. The primary size sweep avoids cross-kernel carry-over inside a process entirely.
- **T6:** CPU 2 is the original-configuration reproduction; CPU 41 is a deliberate different-baseline comparison. CPU 0 is reserved for the controller and is not claimed newly reproduced. Added per-CPU estimates and CPU-specific conclusions. Equal percentage gains are not a confirmation requirement.
- **T7:** Added fixed practical margins and an explicit equivalence gate: absolute median difference within the A/A limit, limit below the margin, and absolute median difference plus limit no greater than the margin. A large or unresolved limit fails. Defined failure handling. The rule is described as an operational repeatability gate, not a confidence interval. P1 has its own 0.30 GB/s equivalence margin. Added a noisy-equivalence synthetic case.
- **T8:** Counter checks now have closed, open/not-read, and open/read modes. They compare all three relevant differences, including open against closed. Size counter checks preserve one read kernel per process. Mixed-sequence counter checks require that branch's own acceptance. No absence of a high observation is attributed to counters without this comparison.
- **T9:** Fixed compatibility success in advance: both processes on a CPU/session must have the first old-read interval slower in all eight pairs. This is a descriptive exception to the six-process rule. Failure blocks the mixed-sequence branch, not an otherwise accepted same-kernel size experiment.
- **T10:** Named B6 for the shared-buffer 1 MiB predecessor. Gave the assembly-predecessor contrast one status: a pre-specified secondary replication. Defined execution rejection versus quality marks, filtered/unfiltered estimates, interruption detection, and completeness per contrast (8 or 16 relevant trials). Added absolute original-run script and source paths plus the current production source path.

### Validation

- Recounted the original raw CSV: 192 process headers, original gains, and all four paired process medians at 8 MiB. Read the original launch script and worker path.
- Recounted B6 positions, including the second old-read interval and position 5. This does not establish recovery after 1.2 s.
- Recounted both B1 raw files using per-process medians: 32 process values per size across sessions. Kept exact half-step endpoints where the median falls between two rounded rows (for example 75.735 GB/s). Checked the CPU grouping at 8 MiB. Recounted the 06:05 raw file and verified three processes with old near 67 GB/s and assembly near 71 GB/s.
- Checked the revised schedule balance mathematically and all nominal-work calculations. Main size plus uncounted sustained work is 5,616 s across 396 processes. Adding both conditional timing branches gives 9,417.6 s across 444 processes. Prefix acceptance and compatibility work are listed separately; these are not elapsed-time bounds.
- All 11 reference identifiers have definitions; all 19 absolute backtick source paths exist. Diagram lines fit within 70 columns. Read the final protocol for consistent primary/conditional ordering, one-kernel primary processes, counter modes, and per-contrast exclusions.

Not run: the full Stage 0 analysis or HTML, any runner implementation or tests, an AArch64 build, new-binary machine-code acceptance, authoritative counter-event validation, or any CRB experiment. This is a design revision. No remote login, root command, external message, or changes to prior sources/results were made.

END ENTRY

## session=20261114T171124Z-c1a5 round=2 role=reviewer status=COMMENTS digest=- time=2026-11-14T17:53:54Z

The digest of tackle-8mb.md matches the round 2 READY entry (530767c1...34576fb0) before and after the checks. Line numbers below are those of that version.

**T1 to T10 are resolved.** Three reviewer agents rechecked the revised file, and a second agent per part tried to refute each new finding. The new numbers of the revision were recomputed from the raw files and hold (see "Checked and found correct"). The findings below concern text that the revision added. They are U1 to U4.

### U1 (medium) — The limit of the size experiment leaves out the variation between processes

Location: lines 80, 192-195, 242-248.

Problem: the size experiment now runs one kernel per process. So every contrast of it (old against new at one size, 8 MiB against 1 MiB, the four-rate contrast) is a difference between separate processes and allocations. The limit is still built only from the split of the four trials inside one process (line 242). It holds none of the variation of the unit that the contrast compares.

- The directional rule is protected, because it also needs one sign in 6 of 6 matched sets.
- The equivalence rule of P1 (line 80) is not protected. It uses only the median of the 6 set differences plus that limit. It can pass while single sets differ by more than the margin.
- The limit that lines 192-193, 203 and 248 report beside a difference or a gain understates its uncertainty. The 8 MiB gain can be "confirmed" while the six set values mix two levels.

Evidence (recount from the raw files):
- Asm read at 8 MiB with full huge-page coverage, B4: process medians of 67.29 and 71.08 GB/s on CPU 2 in s1, and 71.56 and 68.89 GB/s on CPU 41 in s2. Inside each process the design's A/A value, emulated on blocks of 32 intervals, is at most 0.075 GB/s (est., because B4 has the old wrapper between intervals).
- one-thread.csv: new read at 32 KiB on CPU 2 has process medians of 133.127 and 132.077 GB/s (1.05 GB/s apart), with 0.034 to 0.134 GB/s inside a process. Old read at 32 KiB differs by 0.118 GB/s between the rounds, with 0.003 to 0.017 GB/s inside a process.
- For old read at 1 MiB and 8 MiB the part left out is small. A P1 emulation across B6 processes gives single differences of -0.150 to -0.008 GB/s. So P1 would pass correctly on the saved data. The defect is in the rule, not in an expected result.

Requested correction:
- State that in the size experiment the within-process A/A value is a lower bound of the variation.
- For P1 equivalence, require each of the 6 set differences, not only their median, to satisfy "absolute difference plus limit at most 0.30 GB/s". Or add a between-process spread to the limit (for example the largest absolute difference of the fourth-window medians among the 6 processes of one kernel, size, CPU and session).
- Report the 6 set values and their range beside every median difference and gain of the size experiment, at every size. Line 198 asks for this at 8 MiB only.

### U2 (medium) — Several equivalence gates cannot pass with the variation that the saved data show

Location: lines 172, 174, 178, 207, 279-281, 285.

Problem: the margins of line 174 (0.10 GB/s for a rate or a two-rate contrast, 0.20 GB/s for the four-rate interaction) are fixed "design tolerances", and a gate needs "limit below the margin". The saved same-kernel variation at 8 MiB is at or above these margins.

- Line 281 raises the limit to four spreads (a two-rate contrast between modes) and to eight spreads (the interaction between modes) and keeps the margins. Each spread must then be at most 0.025 GB/s on average. No 8 MiB condition in the saved data is that calm. So the mixed-sequence counter gate (lines 280, 285) cannot pass, and 24 processes per check would be spent on a known outcome.
- Line 174 does not say whether the instrumentation gate for the four-rate interaction uses four spreads (line 244) or eight (line 281).
- The base gate (two spreads below 0.10 GB/s, on both CPUs in both sessions) is at the edge at 8 MiB. It is the entry to the P3 branch (line 207), to Stage 3 (line 178) and to the 8 MiB size counters (line 279). The prefix check of line 172 needs it for 18 contrasts per CPU/session (3 targets, 3 pairs of previous activity, 2 windows). The document does not state that count.
- Line 178 gives a longer prefix as the remedy for a failed prefix gate. A gate that fails because its limit is large is not evidence of carry-over, and a longer prefix does not help it.

Evidence (the rule of the design applied to saved data, est. for the trial mode):
- B6 position 5 (old read at 8 MiB after old read at 1 MiB, the calmest 8 MiB condition), 8 processes: one spread is 0.077 / 0.038 / 0.059 / 0.034 GB/s (CPU 2 s1, CPU 41 s1, CPU 2 s2, CPU 41 s2). Two spreads are 0.155 / 0.077 / 0.118 / 0.067 GB/s, which fails 0.10 GB/s on CPU 2 in both sessions. Eight spreads are at least 0.27 GB/s.
- B4, asm read alone at 8 MiB: largest-of-6 A/A value of 0.026 to 0.104 GB/s per process, and 0.919 GB/s in the one process with a level change.
- B6, old read in the first interval after asm read: one spread is 0.33 to 1.18 GB/s.
- At 1 MiB (B6 positions 2 and 4) two spreads are 0.006 to 0.038 GB/s. The gates are reachable there.
- The P1 margin of 0.30 GB/s is reachable: limit 0.022 to 0.083 GB/s, absolute median plus limit at most 0.199 GB/s.

Requested correction:
- Add a Stage 0 item that applies the equivalence gate to the saved same-kernel data (B4, C1, B6 position 5 and the 1 MiB positions) and fixes the 8 MiB margins from that measured spread before collection. Or compute the A/A value on the derived quantity itself (per process, the between-mode difference from trials 1 and 3 minus the same from trials 2 and 4), so that the limit is one spread and not a sum of four or eight maxima.
- State how many spreads each gate uses, and how many contrasts the prefix gate needs per CPU/session, or name the smaller set that gates each branch.
- For the first-window mixed-sequence contrasts, either set the margin after the uncounted batch gives the spread and before the counted batch runs, or state now that this gate is expected to end "mode equivalence not established" and that those counts are then descriptive.
- State that a gate that fails only because its limit is above the margin means "precision insufficient". It is not evidence of carry-over or of a mode effect, and a longer prefix is not its remedy.

### U3 (medium) — The endpoint rule of P3 has undefined cases

Location: lines 82, 84, 207-209.

Problem:
- "Load-only" covers two kernels (new read and asm read). Line 84 selects "the two processes at the smallest and largest load-only process medians" and counts "one" comparison per CPU/session. The two kernels can select different processes, so the endpoint pair and the 2.0 GB/s coverage test are not fixed before collection.
- Line 82 names "compatible" and "contrary". No outcome is named for an endpoint difference that is neither. The P1 row has "Otherwise it is undecided".
- The verdict uses 2 of the 6 processes. If a non-endpoint process has an old-read rate more than 0.30 GB/s away, the rule still says "compatible".
- The load-only rate can change level inside a process. B4 s2 process thp-cpu41-p2 ran at about 71.6 GB/s for 17 intervals (about 5 s) and then at 68.9 GB/s. A P3 process lasts 28.8 s of nominal work. The median of four trials can then lie between two levels, and the old-read trials are compared with a level that they did not run next to.

Requested correction: define the endpoint rule per load-only kernel (two comparisons per CPU/session, each with its own coverage test), or name the one kernel that selects. Add "otherwise undecided". Require the old-read range of all 6 processes plus the limit to be at most 0.30 GB/s for "compatible". State how a process whose load-only trials change level is marked, and whether it can be an endpoint.

### U4 (low) — Places where the revised text does not agree with itself or with its source

- Line 53: the sentence on the second old-read interval is true in the raw files, and [Ref2] does not hold it. results.md and the recount give only positions 1 and 5 and the count 192 of 192. In recount_results_md.py the variable named second is position 5 minus position 4. Cite the two B6.csv files (positions 8 and 11 against position 5), and give the numbers: the median of the second interval per CPU and session is 64.97 to 66.97 GB/s, against 66.91 to 67.08 GB/s at position 5.
- Lines 242, 250, 259 against 188-195: the decision rule and the quality checks sit under Stage 3 and keep its terms ("cycle groups", "that process is incomplete"). Line 247 applies them to the size experiment, where a contrast takes its 8 or 16 trials from 2 or 4 processes of a matched set. Say that the unit there is the matched set of line 190, and write "trials 1 and 3 against trials 2 and 4". Line 193 says "the same rule" before any rule is defined. Name it.
- Line 333 against lines 268, 326-327, 335: the sustained batch of Stage 4 is fixed work inside the 93.6 min figure, and line 333 lists it as one of three choices made from the Stage 2 result. Make them agree.
- Lines 122, 200, 213: the trigger of Stage 3 has three wordings, and none names an observation of Stage 2, which has no predecessor. State the trigger once as an observable (for example a dependence of the fourth-window rate on trial order or on the kernel of the preceding process) or as a named later need.
- Line 172 against 207 and 334: the carry-over gate for the paired-allocation branch uses 1.2 s of previous activity. In that branch the activity before the next trial is 2.4 s of another kernel (1.2 s prefix plus 1.2 s target). Use 2.4 s (the check is then 24 x 36 x 4.8 s = 4,147.2 s), or state that the gate covers half of the exposure.
- Line 25 defines a window as "inside the target", and lines 145 and 172 use windows of the prefix. Line 134 says "in this first stage" inside the runner section. Lines 352 and 356 list outputs of the conditional Stage 3 without the condition. Item 4 of the deliverables has no entry for the two terms of the decomposition of line 197 or for the 60 s traces of Stage 4.

### Checked and found correct

- All ten round 1 findings, with the lines where each is resolved.
- The schedule of line 223, built by script: all 144 position/condition combinations occur twice, and all 132 ordered pairs of distinct neighbours occur twice within rows.
- Lines 41 and 50 (run structure, 192 processes, the four gains 0.51 %, 0.69 %, 0.94 %, 0.51 %), line 61 (B1 medians per CPU group), line 86 (4 MiB and 16 MiB medians), line 88 (est. gains per CPU), line 117 (three processes of the 06:05 run), line 197 (17.55, 0.05, 17.50 GB/s), line 29 (cache sizes).
- Every count and duration of lines 186-190, 207, 266-268 and 323-335, including the three acceptance figures of line 334.
- [Ref1] to [Ref11] are defined, exist and hold what they are cited for, except the citation of line 53.

### Rejected by the verifiers (not findings)

A missing diagram box for the P3 branch; "trial" with a fourth part in the carry-over check; the test against "mixing observations from different processes"; the reference "decision rule below" in line 170.

### Not done in this review

No run on CRB, no build, no change to any file except this entry. The spreads above come from saved runs with the old interval wrapper, so they are estimates for the proposed trial mode.

END ENTRY

## session=20261114T171124Z-c1a5 round=3 role=worker status=READY digest=db30e6e2b0c25b348dd3c6831e25a903ffb40354dedf9ed64a280a786d44c294 time=2026-11-14T17:59:53Z

Initial file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md
Review file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md.review.md

U1–U4 are accepted. The primary experiment and its 5,616 s timing budget are unchanged. This revision corrects the analysis rules, optional-check feasibility, the P3 definition, and consistency details.

### Replies

- **U1:** P1 equivalence now requires every one of the six matched-set differences to fit 0.30 GB/s after adding its two-rate control limit, on each CPU/session. The size experiment explicitly calls its within-process A/A value a lower bound on relevant variation, not an uncertainty bound for comparisons of different processes. Every median difference and gain at every size must show all six set values and their range. A common direction is not a common magnitude. The shared rule now names the matched set as the Stage 2 unit.
- **U2:** Added Stage 0 item 8 to project two-, four-, and eight-spread limits from B4, C1, B6 position 5, and B6's 1 MiB positions. B6 uses its four repeats; B4/C1 use successive groups of four intervals, retaining each process's largest absolute split and all transitions. These projections are estimates for the new wrapper. Stage 1 now fixes a margin from earlier control variation before the relevant acceptance batch: twice the projected limit rounded up to 0.05 GB/s, bounded by 0.10–0.30 GB/s for rates/two-rate differences and 0.20–0.60 GB/s for interactions. No observed mode or predecessor effect can select the margin. Forecast failure at the cap prevents scheduling the full optional gate by default. For first-window mixed-sequence counters, the uncounted Stage 3 result must supply this feasibility decision before counting. Listed two, four, and eight constituent spreads explicitly. Listed all 18 paired-prefix contrasts and 6 mixed-prefix contrasts per CPU/session. A failure caused only by a large limit is “precision insufficient”; it is not evidence of a history or mode effect. A longer prefix is considered only after a repeatable previous-activity difference, not for inadequate precision. P1's 0.30 GB/s margin remains fixed.
- **U3:** P3 now supplies separate new-read and assembly-read comparisons, each with its own endpoint selection and 2.0 GB/s coverage requirement. Ties use saved process order. Compatibility requires the old-read range across all six processes plus twice the largest old-read A/A value to fit 0.30 GB/s. Endpoint changes have a stated contrary-evidence rule; all intermediate outcomes are undecided. A process is marked unstable if its four fourth-window rates span more than 0.30 GB/s or any trial's first/fourth windows differ by more than that amount. An unstable trace cannot supply an endpoint. Any such process makes the affected kernel's P3 comparison insufficient, with all traces preserved and no quieter subset selected. Each kernel can therefore have a different outcome.
- **U4:** Added direct B6 raw-file reference [Ref12]. The second-interval summary explicitly pools 64 intervals at positions 8/11 per CPU/session before its median. Rates calculated from T-row bytes/time give a range of 64.978561587 to 66.971789853 GB/s, printed as 64.98–66.97 GB/s; position 5 spans 66.912683729–67.084937039 GB/s across individual intervals, printed as 66.91–67.08 GB/s. The shared decision rule now has its own section and names trials 1/3 versus 2/4. Completeness is explicitly per matched set for Stage 2 and per process for shared-allocation work. Sustained uncounted observation is fixed work after the size sweep, consistent with the budget. Defined the Stage 3 trigger once and referred back to it. The paired-prefix check now uses 2.4 s of previous activity, giving 4,147.2 s (69.12 min) of acceptance work. The mixed-prefix check still covers its 1.2 s final target. Defined prefix windows, removed “first stage” from the runner constraint, made conditional report outputs explicit, and added the per-kernel decomposition and 60 s traces to the deliverables.

### Checks

- Recomputed B6 position-5 split controls from all eight processes per CPU/session. CPU 2's projected two-spread limits are 0.154586224 and 0.117834898 GB/s. Both exceed the previous 0.10 GB/s margin. Recomputed the second-interval and position-5 rates cited above from raw bytes/time.
- Ran numerical counterexamples against the revised rules: P1 rejects equivalence when one matched set is outside its margin despite a small median; P3 rejects compatibility when a non-endpoint old-rate process is outside the range margin; a changing load trace is marked unstable. These check the design formulas, not an implemented runner or analysis program.
- Checked the margin formula on a 0.155 GB/s forecast (0.30 GB/s margin) and a 0.618 GB/s forecast for an interaction (above the 0.60 GB/s cap, so precision is insufficient). Checked the 18/6 prefix-contrast counts and the changed 4,147.2 s acceptance cost. Main timing counts are unchanged.
- All 12 reference identifiers are defined, all 21 absolute source paths exist, and diagram lines remain within 70 columns. Read the revised gate, unit, exclusion, branch, and output rules together for consistency.

Not run: full Stage 0 feasibility tables or HTML, runner/analysis implementation, hardware measurements, new builds, or authoritative counter-event validation. The future margins must still be frozen from the selected control data before their acceptance batches. No source or earlier result file was changed.

END ENTRY

## session=20261114T171124Z-c1a5 round=3 role=reviewer status=REVIEW_COMPLETE digest=db30e6e2b0c25b348dd3c6831e25a903ffb40354dedf9ed64a280a786d44c294 time=2026-11-14T18:06:17Z

No further comments.

T1 to T10 (round 1) and U1 to U4 (round 2) are resolved. The digest of tackle-8mb.md matched the round 3 READY entry before and after the checks.

What this completion covers: the design document. It states the structure of the original run, tests the size explanation first with one read kernel per process, gives bounded predictions P1 to P3 with the outcomes that reject them, and keeps the mixed-sequence test and the counters as conditional work behind stated gates. It does not mean that the cause of the small gain at 8 MiB is known. No experiment of the design has run.

Checks in this round (two reviewer agents, and a second agent per part that tried to refute each finding):
- U1: the P1 equivalence rule now needs every one of the six matched-set differences plus its limit to be at most 0.30 GB/s. An emulation on B6 (position 5 minus position 4) gives single differences of -0.139 to -0.054 GB/s and a largest "difference plus limit" of 0.162 to 0.222 GB/s. So P1 is reachable. The primary size experiment needs no equivalence gate.
- U2: the margin formula was run on edge cases (a projected limit of 0, of the cap, and above the cap) and gives a defined answer in each. The margin uses only A/A splits of earlier same-condition data, in which a mean mode or predecessor effect cancels. Line 125: the two-spread limits at B6 position 5 on CPU 2 are 0.1546 and 0.1178 GB/s. The counts of 18 and 6 prefix contrasts and the acceptance costs of 4,147.2 s and 1,123.2 s hold.
- U3: the P3 rule was run on constructed cases (a tie, a non-endpoint outlier, an endpoint change, an unstable process, different endpoints for new read and assembly read). Each gives exactly one outcome.
- U4: line 53 recomputed from the T rows of both B6.csv files. The pooled medians of positions 8 and 11 are 64.98 to 66.97 GB/s, and the intervals of position 5 are 66.91 to 67.08 GB/s. [Ref12] holds them. The budget table and its sums are unchanged and correct.

Four points were raised by a reviewer agent in this round and rejected by its verifier. They are not findings, and they are recorded for the implementer:
- Stage 0 item 8 takes the largest of about 100 block values per CPU/session from B4 and C1. Applied to the saved data, it forecasts "precision insufficient" for gates that include assembly read at 8 MiB (two-spread limit of 0.335 to 2.840 GB/s, est.). The gate itself also takes a maximum over many values, so the forecast is not wrong. The consequence is that the P3 branch is not scheduled by default from saved data alone.
- When twice the projected limit is above the cap, the margin is clipped, and the gate then passes only for a median well below the limit. The document states the caps as design choices.
- One projected limit per "branch" can let the least calm condition decide for a calmer one. Lines 193, 300 and 302 already name the narrower unit ("selected use").
- A P3 comparison without coverage is "Insufficient data" by line 228, and line 86 could be read as "undecided". Neither label supports or contradicts the candidate.

Not done in this review: no run on CRB, no build, no implementation of the runner or of the analysis. The spreads quoted from saved runs come from the old interval wrapper and are estimates for the proposed trial mode. No file was changed except this record.

Initial file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md
Review file: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md.review.md

END ENTRY
