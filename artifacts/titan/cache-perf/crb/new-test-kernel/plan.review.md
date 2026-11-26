## session=20261113T1915Z-p7x3 round=1 role=worker status=START digest=- time=2026-11-13T19:15:19Z

Initial file: /home/jhan/tmp/investigate-new-c-mysteries.md
Review file: /home/jhan/tmp/investigate-new-c-mysteries.md.review.md
Subject: a plan (no measurement yet) for two open questions of the kernel rewrite of 2026-11-13: the behaviour at 8 MiB with one thread, and the opposite order of old and new read with 120 threads.

END ENTRY

## session=20261113T1915Z-p7x3 round=1 role=worker status=READY digest=93bcaa5d75f409f2699716b61780e77b254cea0c5547350476d2b4a442ff9f6e time=2026-11-13T19:15:19Z

Summary of the submitted work:
- The file is a plan. It holds: the two questions with their numbers, 14 items that existing result files already show, 11 hypotheses (H1 to H11), 11 rules for the measurements, and the measurements in four parts (A: existing binaries; B: scratch binary; C: core counters without root; D: mesh counters with root, only with the user's approval), each step with the result that rejects a hypothesis.
- No file of the benchmark was changed. No new measurement was made.

Evidence from checks that were run:
- Three agents prepared inputs from local files (existing evidence, candidate mechanisms, measurement confounds). I did not copy their numbers unchecked: I recomputed with my own scripts the numbers of items 1, 3, 5, 6, 7, 9, 10, 11 and 12 from the csv files named in Ref1 to Ref5 (per-process rates at 8 MiB in both runs of 2026-11-13; the per-CPU sweep of 2026-11-02: first-repetition range 66.43 to 68.99 GB/s, 41 repetitions above 70.5 GB/s in 39 processes, 39 of them the third repetition; pass counts = total_bytes / 268435456 for all 72 repetitions of threads120.csv; old read at 120 threads on 2026-10-30; asm read at 64, 96, 48+48 and 64+56 threads).
- CPU 41 reached the high level in both sweeps, and CPU 94 has the highest first-repetition rate in both sweeps (computed from the two percore files).
- bench/run_crb.sh lines 122 to 135 run perf stat without root, and the output files in results/20261030T193108Z/ show the suffix :u.

Checks that were NOT run:
- No step of the plan was run. No login to CRB was made for the plan, with one exception: by mistake one command of mine contained "ssh ... true" at 19:12 UTC, which opened and closed one login without running anything. No block of Jeremy was announced for that time (Slack #phoenix-crb read at 18:31 and 19:13 UTC).
- The list of perf events on CRB was not read, so the event names of part C and D are those found in earlier scripts and result files.
- No Arm document was consulted. The mechanisms named in the hypotheses are candidates only.
- The cost values are estimates (marked est.), not measured.
- The agents' statements that I did not recompute are not in the plan as facts, with these exceptions that I took from the report text itself: the report's section on the write fall (item 14) and the CPU-to-mesh assignment.

END ENTRY


## session=20261113T1915Z-p7x3 round=1 role=reviewer status=COMMENTS digest=- time=2026-11-13T19:18:53Z

Short version: The checked rate summaries and pass counts agree with the source data. The plan needs changes to its controls and decision rules before those experiments can settle the questions. No machine experiment was run in this review.

### R1 — Make the screening stage consistent with the required controls

Location: Rules 1–11, Part A, and Order and decision points 1–3.

Part A cannot satisfy the rules labelled "for every measurement". It uses separate old and new binaries, has no A/A control, and has no buffer page-state reporting. The existing --per-thread output contains CPU and rate, but not the bytes, elapsed time, start time, and end time required by rule 6 [RRef1]. Nevertheless, the decision section says Part A decides H7 and H9 and can remove later tests. Rule 10 requires two sessions for a deciding comparison, while Part A is described as one session.

Requested correction: Either make Part A explicitly exploratory, with named exceptions and confirmation under the required controls before closing a hypothesis, or move the necessary scratch-binary work ahead of the deciding tests. Define how the 2% maximum pass-duration condition is checked rather than assuming that --min-ms 5000 guarantees it. Reconcile the decision order with the two-session requirement.

### R2 — Do not remove the suspected alignment effect before deciding whether to test it

Location: Rule 2, B0–B3, and the B1 conclusion "Q1b is closed: the difference belonged to the process."

Rule 2 aligns every variant to 64 B. The historical copy loops started at offsets 36 and 52 modulo 64. B1 therefore changes a candidate cause before measuring the original difference. If alignment removes the difference, B1 would attribute it to the process and skip B3, although H6 could be the cause. Also, a difference within the A/A variation means the comparison is unresolved. It does not prove a process effect, as rule 11 already says.

Requested correction: Retain verified variants at the original offsets for the reproduction comparison, or run the alignment comparison even when aligned B1 is unresolved. Separate "no difference resolved in this configuration" from causal attribution. Define the A/A spread used as the threshold and match it to the tested size, CPU, and schedule. B0 currently lists copy controls at 1 and 8 MiB, while B1 also tests 4, 16, and 32 MiB.

### R3 — Classify the rate by interval, not once per process

Location: Existing evidence item 1, rules 4–5, B1, C1, and Results expected.

The statement that the level "belongs to the process" conflicts with item 5's observed transitions inside a process. A process median and one asm-read reference can combine low and high intervals. A reference before or after copy also does not establish the state during copy. C1 cannot label a new counter process from the state of an earlier A5 process.

Requested correction: Preserve the sequence of repetition rates. Bracket comparisons with reference intervals, identify transitions, and specify how mixed or changing cases are handled. Base counter-run state labels on measurements from that run. Describe a process as stable only when its recorded reference intervals support that label.

### R4 — A live buffer does not establish stable physical pages

Location: H3, A6, B4, rule 8, and D2.

H3 says the pages stay the same inside a process. B4 would reject a physical-address explanation when the same buffer changes rate. That conclusion needs evidence of stable physical backing. Linux can replace existing small pages with a newly allocated huge page while the virtual buffer remains mapped [RRef2]. AnonHugePages before and after a process does not identify physical page addresses. Also, A6's third rate under --no-thp does not show that the original low and high cases had the same page size.

Requested correction: Separate virtual-buffer identity, huge-page coverage, and physical-page identity. Record page coverage around the relevant intervals. Treat the physical-address hypothesis as unresolved without suitable physical-backing evidence. Make A6 test the page-size explanation against observed coverage in both original rate states, rather than rejecting it from a third rate alone. Do not require root work now; state the resulting limit on conclusions if it remains deferred.

### R5 — Narrow rejection rules to what each intervention actually tests

Location: A2–A5, B6, C2, and Order and decision points.

Several rejection criteria are stronger than the proposed measurements:

- A2 changes duration but retains synchronized starts at the beginning of each buffer. H7 includes both effects. A persistent difference cannot reject all of H7.
- A3 changes the second buffer in one session. H9 also includes a day/session effect, which this test does not reject.
- A4 samples discrete thread counts. The same observed transition bracket does not establish equal transition thresholds.
- A5 failing to produce a transition in a finite run does not reject the statement that a state can change. A fall in a fresh process also changes the buffer allocation.
- B6's 67.2 GB/s cutoff does not follow from H1's approximate 67 GB/s limit. Use a same-core cache-resident baseline and measured variation before rejecting that limit.
- C2's equal instruction and refill counts do not exclude an instruction-order or alignment effect. Those hypotheses do not predict different instruction or refill counts.

Requested correction: Split compound hypotheses into testable claims. State a bounded prediction for each decisive test. Use "not observed", "not resolved", or "this component is insufficient" when the experiment does not exclude the broader mechanism. Update the decision section and expected results to use the same limits.

### R6 — Specify how counters are assigned to each kernel, thread, and rate state

Location: Part C introduction, C1–C3, D1.

Subtracting two whole-process counter runs is not guaranteed to remove setup when allocations or rate states differ. It also cannot separate kernels when the scratch process alternates them. The current worker includes first touch, warm-up, and barriers outside the timed intervals [RRef1]. C3 names perf stat --per-thread but has no thread-attachment protocol. The perf documentation describes this option with monitored thread or process IDs [RRef3]. Dividing user-mode cycles by wall time that includes waiting would not directly give the busy core's clock frequency.

Requested correction: Add a concrete counting protocol. Identify worker thread IDs and CPUs, define counted interval boundaries, and assign event counts and bytes to one kernel and state. Require usable event coverage and reject unsupported or materially multiplexed measurements. Permit short/long subtraction only with checked assumptions about matching state and setup. Define the clock denominator separately from bandwidth elapsed time. For D1, state which events count memory requests and what coverage is needed before excluding H10; equality of selected counters alone is not evidence about uncounted traffic. Preserve the corrected raw-cycle treatment already documented in the report [RRef4].

### R7 — Treat the nop variant as a sensitivity test, not proof of window occupancy

Location: H8 explanation and B5.

The ratio 2.9 follows from source-level instruction density. It does not measure outstanding loads or occupied entries in the core's instruction window. Replacing vector adds with nop instructions does not establish equal resource use or equal request pressure. Therefore, a sparse loop near 300 GB/s cannot reject the whole H8 mechanism. A sparse loop matching old read shows that vector adds are not necessary for that result, but does not identify window density as the cause.

Requested correction: Keep the nop sweep as a useful controlled perturbation. State the limited conclusions for either outcome. Label the 2.9 ratio as an instruction-count model conditional on equal per-instruction resource use, rather than an estimate of measured lines in flight. Require independent evidence before assigning the effect to instruction-window occupancy.

### Review references and checks

- [RRef1] /home/jhan/workspace/titan/cache-perf/bench/bandwidth.c: worker at lines 445–483; aggregate and --per-thread output at lines 572–613. The --per-thread rows contain index, CPU, kernel, repetition, and rate only.
- [RRef2] Linux kernel documentation, Transparent Hugepage Support, thp_collapse_alloc: https://www.kernel.org/doc/html/latest/admin-guide/mm/transhuge.html . It documents allocation of a new huge page when existing pages are collapsed.
- [RRef3] Linux perf documentation, --per-thread, --delay, and --control: https://github.com/torvalds/linux/blob/master/tools/perf/Documentation/perf-stat.txt . This review did not test the installed CRB perf version.
- [RRef4] /home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html:290 and crb/tmp/agent-scratch/spec-row-2026-11-11/mesh_clock.py. These correct the earlier idle-subtracted mesh-clock interpretation. The older comment in bench/run_sudo.sh:15 is stale.
- Recomputed from kernels-20261113T181222Z: old-read 952–970 passes; load-only reads 600 passes in 17 of 18 repetitions and 664 in the remaining repetition; all copy process means listed in items 6–7. Recomputed the two percore-asmread sweeps: 41 repetitions above 70.5 GB/s in 39 processes, with 39 third repetitions and 2 second repetitions. These agree with the submitted initial file.
- No CRB login, benchmark execution, implementation edit, or initial-file edit was made by the reviewer.

END ENTRY
## session=20261113T1915Z-p7x3 round=2 role=worker status=READY digest=adec29cb0c4fe3dcaa7269e0885e2231d2039bdb5b62e4deb49cbb405263506c time=2026-11-13T19:21:57Z

Replies to round 1. All seven comments are accepted. The sections "Hypotheses", "Rules", "Measurements", "Order and decision points", "What this plan does not do" and "Results expected at the end" are rewritten. The questions and the 14 items of existing evidence are kept, with the two changes named under R3.

R1 (accepted). New section "Two kinds of measurement": part A is screening, names its four exceptions (two binaries, no A/A control, no page state, the existing --per-thread row holds only index, CPU, kernel, repetition and rate), and closes no hypothesis. The rules are now titled "Rules for the deciding measurements (parts B to D)". The table of part A has a column "What the result points to" and no rejection column. The 2 % condition is now a check (rule 7): interval of the thread divided by its passes, at most 2 % of the interval, a failing repetition is marked; in the scratch binary the common stop time with partial-pass counting replaces the whole-pass limit. The decision section says that part A closes nothing and only sets the order; only B7 (under the rules, two sessions) can end the Q2a branch. New steps B7, B8, B9 confirm under controls what A2, A4, A3 screen.

R2 (accepted). Rule 2 no longer aligns every variant to 64 B. The reproduction step B1 keeps the C copy loop and the asm copy loop at their original offsets (36 and 52 modulo 64), checked with objdump. B3 varies the offset only after a resolved difference at the original offsets, so alignment is not removed before the difference is measured. An unresolved B1 now reads "the difference of 2026-11-13 is not reproduced inside one process. This does not show what made the earlier difference." The A/A spread is defined in rule 3 (largest absolute A/A difference over the processes of the same comparison, same kind, size, CPU and schedule; "resolved" = median larger than that and one sign in all processes). The separate step B0 is removed: the A/A pair runs inside every comparison, so each of the sizes 4, 8, 16, 32 MiB has its own A/A spread.

R3 (accepted). Item 1 no longer says the level "belongs to the process"; it says two load-only loops in one process showed the same level and that the level is a property of an interval. New terms "Interval" and "Reference interval". Rule 4 keeps the sequence and forms differences between neighbouring intervals; a per-process value is given only if all its references are at one level. Rule 5 brackets every compared pair with asm read references and labels each interval low, high or changing; changing intervals are reported and not used. The thresholds are provisional and stated with the counts of the 2026-11-02 sweep (638 below 69 GB/s, 41 above 70.5 GB/s, 41 between; recomputed from the two percore files). C1 takes its labels from the rates of the counter run itself. The plan also says that a relation between the read level and the copy rate is open.

R4 (accepted). H3 is split into H3a (huge-page coverage) and H3b (physical address). New terms "Huge-page coverage" and "Physical-page identity" with your reference as Ref9. Rule 8 records coverage and four /proc/vmstat counters before every interval and says that they do not show physical-page identity. A6 is now a reference value only and rejects nothing. B4 tests H3a against the observed coverage of low and of high intervals. H3b is not decided by B4; a level change with constant coverage and no counted collapse or migration is reported as "no sign of a page change", not as proof. H3b stays "not tested" unless D2 (root, user's approval) is run, and "Results expected" states that limit. Item 5 now says that the files do not show whether the pages stayed the same.

R5 (accepted). H7 is split into H7a (short interval) and H7b (common start); A2 looks at H7a only, and B7 tests each with its own prediction (per-thread start offsets are a new option of the scratch binary). H9 is split into H9a (second buffer) and H9b (session); B9 can reject only H9a, and H9b can only be "observed" or "not observed". A4 and B8 report the bracket between two neighbouring thread counts; equal brackets are "not resolved at this grid", and B8's rejection is bounded to a grid step of 4 threads. A5: no change in 30 intervals is "not observed" and does not reject H2; a different level in a new process says nothing, because the buffer is a new allocation. B6: the fixed cutoff of 67.2 GB/s is removed; the baseline is old read at 1 MiB on the same CPU in the same process, with its own A/A pair. C2 is descriptive and its rejection clause is removed. Rule 11 fixes the five result words, and the decision section and "Results expected" use them.

R6 (accepted). Part C has a protocol: each worker thread opens a user-mode counter group on itself with perf_event_open (as bench/homelat.c does, Ref11), reads it directly before and after each timed interval, and writes thread ID, CPU, kernel, interval, bytes, elapsed time, counts, enabled time and running time; multiplexed rows and events that cannot be opened give no result; no short/long subtraction in part C; the clock is cycles divided by the thread's CPU time. D1: one kernel per process, pattern from the per-thread rows of the same run, 100 % counter coverage required, short/long subtraction only when pattern and coverage match, the two memory-request events named with their overlap, equality reported as "not supported by these counters" and not as a rejection of H10, mesh clock from the raw dtc_cycles count as in the report's corrected treatment (Ref12).
How checked: I read bench/homelat.c lines 770 to 777 (open_counter with the enabled and running read format) and the docstring of mesh_clock.py. I did not test perf_event_open for our own threads on CRB; the plan says so.

R7 (accepted). The 2.9 ratio is now described as an instruction-count model that holds only if every instruction uses the same resources, not as a measurement of lines in flight, with "Insufficient data" for the latter. B5 is titled a sensitivity test. Its tested statement is "vector adds are needed for the split pattern of old read". Both outcomes have limited conclusions: matching old read rejects that statement and does not identify window occupancy; staying uniform means the perturbation is insufficient and H8 is not rejected. "What this plan does not do" says that no step measures the content of the out-of-order window.

Checks that were NOT run:
- No step of the plan was run, and no login to CRB was made in this round.
- The new protocol of part C and the scratch binary do not exist yet; they are described, not built.
- The kernel documentation page of Ref9 and the perf documentation you named were not opened by me; Ref9 is cited as named by you.

END ENTRY


## session=20261113T1915Z-p7x3 round=2 role=reviewer status=COMMENTS digest=- time=2026-11-13T19:23:31Z

Short version: R1, R2, R3, R4, R6, and R7 are resolved for this plan. R5 is partly resolved. One new scope gap, R8, was introduced by the revision.

### R5 — Keep the new deciding tests consistent with their stated predictions

Location: H7a/H7b, rule 7, B7, B8, and Order and decision points.

The revised screening, page-state limits, instruction-order limits, and same-core baseline address the earlier examples. Two problems remain in the new deciding steps:

1. **B7 removes the whole-pass timing method before testing its contribution.** Both the 0.5 s and 6 s cases now use a common stop time with partial-pass counting. H7a explicitly includes whole passes. If the historical read difference disappears in every B7 case, the plan stops the branch without a controlled reproduction of the original timing method. This would leave the timing question unanswered. Also, H7a and H7b say "a part of the difference", while B7 treats complete disappearance as their prediction. A smaller but still resolved difference would support a contribution, not reject it.

   Requested correction: Include a reproduction condition with the original whole-pass stopping method in the same scratch binary and process schedule. Compare it with partial-pass stopping while holding the other factors fixed. Test duration and start offset as separate factors. Define the measured effect in consistent units, such as the change in the old-minus-new rate difference in GB/s. A contribution need not remove the entire difference. If even the reproduction condition fails to reproduce it, report that limit and assign no cause. If the reproduction condition succeeds and a timing change removes it, retain and report that result before ending the branch.

2. **B8 still rejects an earlier threshold from an equal observed bracket.** The prediction is "a lower count", with no minimum separation. Two thresholds inside the same four-thread bracket can satisfy that prediction. The added sentence "This says nothing below that step" does not make rejection of the stated prediction valid.

   Requested correction: Equal or overlapping brackets remain "not resolved at this grid". Alternatively, define a separate prediction requiring a minimum threshold separation and show how the measured brackets bound it. Do not label the broader earlier-transition claim rejected from overlapping brackets.

### R8 — Retain a deciding path for Q2b and H11

Location: Q2b, H7a/H7b, H11, Part B's Q2 table, and Results expected at the end.

The revised Part A screens the write-rate levels and explicitly closes no hypothesis. Every Q2 deciding step now runs read kernels only. H11 therefore has no deciding measurement, and the short-versus-long write question has no confirmation under the new controls. The original plan included write kernels in the timing investigation. The revision has left Q2b in scope without a path to its stated result.

Requested correction: Extend the controlled timing comparison to the old, new, and assembly write kernels. Retain per-thread and per-mesh results for both the lower and higher write totals when they occur. State the bounded observation that would support or contradict H11. Keep this path independent of whether the Q2a read difference reproduces. If the write work is intentionally deferred, state that scope cut explicitly in the short version, decision order, and expected results instead of implying Q2 is fully covered.

### Checks in this round

- The initial-file digest matches round 2 READY: adec29cb0c4fe3dcaa7269e0885e2231d2039bdb5b62e4deb49cbb405263506c.
- Recomputed the provisional level bins from both percore-asmread files: 638 repetitions below 69 GB/s, 41 above 70.5 GB/s, and 41 between. These match rule 5.
- Read bench/homelat.c's counter-group setup. It provides the stated group read format. The proposed thread-local user-mode counting protocol remains a plan and is correctly marked untested.
- No machine experiment, implementation edit, or initial-file edit was made by the reviewer.

END ENTRY
## session=20261113T1915Z-p7x3 round=3 role=worker status=READY digest=1660b1e581245bcc3d4d40910a58a8c06901b0b6e10629ea99bfda885663e7b2 time=2026-11-13T19:24:30Z

Replies to round 2. Both comments are accepted.

R5, part 1 (accepted). B7 is rewritten. It now has three separate factors with two settings each, in all 8 combinations: stop method (whole passes as in bandwidth.c, or common stop time with partial-pass counting), interval (0.5 s or 6 s), and start (common, or per-thread offsets). The setting "whole passes, 0.5 s, common start" is named the reproduction condition, and it is run both with alternating kernels in one process and with one kernel per process as on 2026-11-13. The measured effect is D = total rate of old read minus total rate of new read, in GB/s, also per mesh. H7a and H7b now predict a resolved change of D when their factor changes with the other factors fixed; the hypothesis table says that "a part" means a resolved change in GB/s and need not be the whole difference. Outcomes: if the reproduction condition gives no resolved D, the result is "not reproduced in the scratch binary", no cause is assigned, and the difference to the run of 2026-11-13 is examined first; if it reproduces, each factor is reported with its change of D; if one setting removes D, that is reported as a result before the later steps are limited to the settings where D is resolved. Rule 7 now says that the stop method is recorded and is a factor, and the scratch binary keeps both stop methods.

R5, part 2 (accepted). B8 no longer rejects from equal brackets. Its outcomes are: bracket of asm read wholly below that of old read in both sessions = supported; wholly above = contradicted; equal or overlapping = "not resolved at this grid". The row says that no rejection is made from overlapping brackets.

R8 (accepted, not deferred). New step B10 for Q2b: old write, new write, asm write and an A/A copy of asm write at 64+56 threads, with the same three timing factors (intervals 0.5 s and 15 s), per-thread and per-mesh rows, at least 12 intervals per kernel and setting, two sessions. It has a bounded prediction for H7a on write (separate levels in the reproduction condition; spread within the A/A spread with the common stop time) and for H11 (in an interval with a higher total, one mesh is higher by a resolved amount and the other is not). Outcomes are given for "rejected", "supported", "contradicted" and "not observed". Per-mesh rows are kept for lower and higher totals. The decision order has a new point 4: B10 is run whatever B7 shows. "Results expected" now has separate lines for Q2a and Q2b. H11's wording now names "the threads of one mesh", with mesh 1 as the candidate. The machine-time estimate of part B is raised to about 90 min per session (est.).

Checks that were NOT run: as in round 2. No step of the plan was run, and no login to CRB was made in this round.

END ENTRY


## session=20261113T1915Z-p7x3 round=3 role=reviewer status=COMMENTS digest=- time=2026-11-13T19:25:25Z

Short version: R5 is resolved. R8's requested write measurements are present, but its new conclusion needs one correction. One sign-handling ambiguity in the shared decision rule also needs correction before the plan is used.

### R8 — Limit the conclusion of the new write experiment

Location: B10, prediction and outcome columns.

The independent write path addresses the scope gap. However, the new outcome says that persistent levels with common stopping and a long interval mean "the levels are a property of the hardware under this load". This experiment changes two timing factors. It does not exclude all other software or measurement causes. It also returns to predicting complete removal of the spread, although H7a now means a partial contribution.

Requested correction: Report whether changing each factor changes the write totals or their spread by a resolved amount. If levels persist, state that these timing changes do not fully explain them. Do not assign the remaining levels to hardware without further evidence. The H11 per-mesh comparison and its limited conclusions can remain.

### R9 — Make the resolution rule work for negative differences

Location: Rule 3 and the definition of resolved changes used throughout Part B.

Rule 3 compares the median difference to a nonnegative A/A spread. As written, a consistently negative difference can never be resolved. The observed new-copy-minus-asm-copy differences are negative, and a timing intervention can reduce D in B7.

Requested correction: Compare the absolute value of the median difference with the nonnegative A/A spread, while retaining the signed difference and the same-sign condition. Apply the same convention to changes between settings. This is a wording correction to make the intended decision rule unambiguous.

Checks: The file digest matches round 3 READY (1660b1e581245bcc3d4d40910a58a8c06901b0b6e10629ea99bfda885663e7b2). Rechecked the new B7 reproduction condition, its separate timing factors, B8's non-overlapping-bracket rule, B10, the decision order, and expected results. No experiment or implementation change was made by the reviewer.

END ENTRY
## session=20261113T1915Z-p7x3 round=4 role=worker status=READY digest=0b0c4a3455792e88389f4f7c783223f9871d52ff89fe0b147200bd18a724599a time=2026-11-13T19:25:49Z

Replies to round 3. Both comments are accepted.

R8 (accepted). B10 no longer predicts complete removal and no longer assigns remaining levels to the hardware. The prediction column defines the spread of a kernel (highest minus lowest total of its intervals in one setting, in GB/s) and says that H7a predicts a resolved change of that spread when the stop method or the interval changes with the other factors fixed, and H7b the same for the start. The outcome column reports each factor with its change of the spread and of the median total as "contributes" or "no resolved contribution". If levels remain in every setting, the statement is "these timing changes do not fully explain the levels", and the remaining levels are not assigned to the hardware or to any other cause without further evidence. The H11 part is unchanged.

R9 (accepted). Rule 3 now says: the A/A spread is never negative; a difference keeps its sign; it is "resolved" only if the absolute value of its median over the processes is larger than the A/A spread and it has one sign in all processes. The same convention is stated for a change of a difference between two settings.

Checks that were NOT run: as before. No step of the plan was run, and no login to CRB was made in this round.

END ENTRY


## session=20261113T1915Z-p7x3 round=4 role=reviewer status=REVIEW_COMPLETE digest=0b0c4a3455792e88389f4f7c783223f9871d52ff89fe0b147200bd18a724599a time=2026-11-13T19:26:22Z

No further comments.

R1 through R9 are resolved for the submitted investigation plan. Rechecked the revised write conclusions and the signed-difference rule in round 4. The initial-file digest still matches the latest READY entry.

This completes review of the plan only. The scratch binary and counter protocol remain to be implemented and checked. No proposed machine experiment was run as part of this review.

Initial file: /home/jhan/tmp/investigate-new-c-mysteries.md
Review file: /home/jhan/tmp/investigate-new-c-mysteries.md.review.md

END ENTRY
