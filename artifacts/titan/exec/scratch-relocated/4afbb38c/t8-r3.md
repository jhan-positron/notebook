# Design: explain the small read-bandwidth gain at 8 MiB

## Short version

First test the candidate that old read reaches a core limit near 67 GB/s while the new loop's data-supply rate falls toward that value as the buffer grows. Measure each loop across sizes under same-kernel preparation, then use counters only after establishing that counting preserves the measured rates and contrasts. The predecessor test is conditional work on the later mixed sequences; the original small gain came from runs with one read kernel per process.

## Scope and words used here

This is a proposed design, not an executed experiment. The user requested this Markdown file and its review. Implementation and machine runs are later work.

- **8 MiB**: 8,388,608 bytes. This is the buffer size called “8 MB” in the question.
- **Rate**: bytes read divided by measured elapsed time, in GB/s. One GB is 1,000,000,000 bytes.
- **Old read, new read, assembly read**: the read loops before the rewrite, after the rewrite, and written in assembly. Their names in the existing experiment program are `oldread`, `read`, and `asmread`.
- **Kernel**: one of these benchmark loops. It is not the Linux kernel.
- **CRB**: the Arm Phoenix Reference Server where the original measurements ran.
- **CPU**: a processor core selected for the worker thread. CPU 2 repeats a configuration of the original question. CPU 41 tests a CPU with a different observed load-only baseline.
- **Pass**: one complete read of the selected buffer range.
- **Loop offset**: the address of a loop's first instruction modulo 64, or its position within a 64-byte address block.
- **First touch**: initialization writes by the pinned worker that cause the buffer's pages to be allocated.
- **Allocation**: one buffer mapping, initialized by the pinned worker. A fresh process supplies a fresh allocation. A fresh mapping does not guarantee different physical pages.
- **Prefix**: the same preparation loop before each trial. It standardizes recent work. It is not assumed to reset the hardware.
- **Predecessor**: the loop deliberately run immediately before the loop being measured.
- **Target**: the loop whose subsequent rate is measured.
- **Trial**: prefix, optional predecessor, and target, in that order, without changing the buffer or worker CPU. Same-kernel trials omit the separate predecessor.
- **Window**: one measured period inside the prefix or target. Four consecutive windows show whether an effect persists or recovers.
- **A/A control**: repeat the same condition under two analysis labels. The difference estimates variation without an intended change. Both labels call the same function address.
- **Session**: one complete set of processes. Confirmation uses a second session whose start is at least 3 hours after the first session ends. This separation is a design choice, not evidence of independence across days.
- **Counter**: a hardware event count for the worker thread. **PMU** is the processor unit that supplies these counts. **L1 and L2** are the first two cache levels. A **refill** is an event reported as a cache line fetched into a level.
- **SLC**: the system-level cache shared by the cores. The local hardware report records a private 2 MiB L2 per core and a shared 128 MiB SLC. A 1 MiB buffer fits L2; an 8 MiB buffer does not. [Ref9]
- **Thread CPU time**: time during which the worker executes, rather than waits off the CPU. A **context switch** occurs when the scheduler changes the running task. **Multiplexed counters** run for only part of the time they are enabled.
- **Huge-page coverage**: the fraction of the buffer backed by 2 MiB pages. It does not identify those pages.
- **Root**: administrator access. Initial experiments use no root.
- **B4, B6, C1**: earlier experiments. B4 repeatedly timed assembly read. B6 alternated old read at two sizes with assembly-read references. C1 repeated the long read sequence with counters.
- **`bwx`**: the existing experimental benchmark. **`bwx8`**: the proposed scratch copy for this design.
- **est.**: an estimate, not a measurement.

The primary question is read bandwidth. The difference between C copy and assembly copy is separate work. Whole-chip bandwidth is also separate work.

## What the existing evidence supports

The original run used CPUs 0 and 2 in two rounds. Every binary/kernel/size/CPU/round combination had its own process. Each read process initialized its buffer with a write, then ran three 0.5 s repetitions with a warm-up pass of that same read kernel before each. No other read loop ran before it inside that process. The table takes the maximum over the 12 repetitions of the four processes for each read kernel and size. These best rates describe the question; they are not the estimator for the new experiments. [Ref1][Ref8]

| Buffer size | Old read | New read | New-read gain |
|---|---:|---:|---:|
| 32 KiB | 66.76 GB/s | 133.22 GB/s | 99.55% |
| 1 MiB | 67.13 GB/s | 85.26 GB/s | 27.01% |
| 8 MiB | 67.08 GB/s | 67.71 GB/s | 0.94% |
| 1 GiB | 28.72 GB/s | 30.89 GB/s | 7.56% |

The gain is `100 × (new / old − 1)`. These values are recomputed from the original CSV file. Each original process had same-kernel read history. Allocation and the preceding process differed between comparisons. The small gain also appears in every pair of process medians at 8 MiB: 0.51%, 0.69%, 0.94%, and 0.51%. It is not an artifact of selecting the best repetition. [Ref1][Ref8]

- In each of the two B6 sessions, the first old-read interval after assembly read was slower in all 192 pairs of consecutive old-read intervals. The two intervals used the same 8 MiB buffer. [Ref2]
- Even the second old-read interval can remain below the rate after the 1 MiB predecessor. Pooling positions 8 and 11 within each CPU/session gives median rates from 64.98 to 66.97 GB/s. Position 5, after the 1 MiB predecessor, ranges from 66.91 to 67.08 GB/s across its individual intervals. The B6 traces do not establish that 1.2 s of old read erases earlier history. [Ref12]
- B6's old-read comparison against 1 MiB depended on position. Its difference was about −3.44 to −5.54 GB/s immediately after assembly read. It was about −0.06 to −0.11 GB/s after old read at 1 MiB. These are ranges of the per-CPU medians across the two sessions. They are not yet a randomized estimate of the predecessor's effect. [Ref2]
- Assembly read reached both lower and higher rates with full huge-page coverage in B4. C1 captured no interval above 70.5 GB/s. Absence of that observation does not show that counters caused its absence. [Ref2]
- The existing worker performs a target warm-up pass, reads page information, and waits on a barrier before timing. Output occurs between intervals. These operations separate the nominal predecessor from the timed target. [Ref3]
- Old read has a returned sum stored to a worker-local volatile variable. The new runner must preserve this consumption of the result. [Ref3]

The B6 effect lowers old read. With new read fixed, this makes the old-to-new percentage gain larger. It cannot by itself explain the original small gain, whose process never ran assembly read as a predecessor. It is a limitation of mixed-sequence measurements that the design must control. [Ref1][Ref2][Ref8]

CPU 2 is the primary reproduction CPU. CPU 41 is a deliberate contrast: B1's 8 MiB assembly-read reference medians span 70.070 to 70.460 GB/s on CPUs 41 and 94, against 67.880 to 68.755 GB/s on CPUs 0 and 2. B1 also ran copy and held two buffers. These are measured reference rates, not predictions for a one-buffer run. CPU 0 is omitted to keep two worker CPUs and reserve it for the controller. A conclusion on CPU 2 does not claim a new reproduction on CPU 0. [Ref2][Ref10]

There are two separate issues to explain:

1. Why the old and new rates are close at 8 MiB compared with 1 MiB.
2. Why a load-only read loop sometimes changes between nearby rates at 8 MiB.

Even a repeatable change from about 67 GB/s to about 71 GB/s would not reproduce the 1 MiB gain. It must not be presented as a complete explanation of the size comparison. [Ref1][Ref2]

## Candidate explanation and bounded predictions

The candidate comes from H1 in the earlier plan. Old read may reach a core-side limit near 67 GB/s. New read removes work inside that loop, but at 8 MiB its supply of data may become the tighter limit. The two rates then happen to be close on CPU 2. This does not identify the resource that limits old read, or a specific bottleneck on the path from the SLC. [Ref11]

The earlier result table marked H1 rejected through the size comparison in B6. That comparison was affected by sequence position. It therefore does not establish that the candidate fails under same-kernel preparation. The separate low/high-state comparison of old read was not obtained. [Ref2]

This candidate is restricted to the cache-size comparison. It does not explain why old read is also slower at 1 GiB. At that size the original best rates were 28.72 and 30.89 GB/s. Do not extend a simple “smaller of a core limit and a supply limit” model to that result without another test. [Ref1]

| Prediction | Measurement | Outcome against the candidate |
|---|---|---|
| P1: old read remains nearly constant from 1 MiB to 8 MiB | Old-8-MiB minus old-1-MiB rate in each matched process set, with its two-rate A/A limit | A repeatable difference larger than 0.30 GB/s contradicts this bounded prediction. Equivalence requires every one of the six set differences, in absolute value plus its limit, to be at most 0.30 GB/s on each CPU/session. Otherwise it is undecided. |
| P2: the load-only loops lose rate as the buffer grows from 1 MiB to 8 MiB | Separate size contrasts for new read and assembly read | A repeatable decrease supports this prediction. A repeatable increase contradicts it. An unresolved contrast is undecided. |
| P3: old read stays stable across observed variation of the load-only rate at 8 MiB | Conditional paired-allocation experiment: fourth-window old, new, and assembly rates on the same allocation | Evaluate new read and assembly read separately under the rules below. Each needs a load-only range of at least 2.0 GB/s. The old-read range across all six processes, plus its control limit, must be at most 0.30 GB/s for compatibility. An old endpoint change beyond that margin and control is contrary descriptive evidence. Otherwise the result is undecided. |

The 0.30 GB/s equivalence margin and 2.0 GB/s coverage requirement are proposed analysis choices, fixed before collection. P3 supplies two descriptive comparisons per CPU/session, one selected by new read and one by assembly read. Each uses that kernel's own minimum and maximum process medians as endpoints. Its coverage test applies to that kernel alone. Ties use the earlier process in the saved schedule.

For P3, define the old-rate control limit as twice the largest absolute old-read A/A value among all six processes. Compatibility requires the old-read range across all six process medians plus this limit to be at most 0.30 GB/s. Thus a non-endpoint old-read outlier cannot be hidden. An endpoint old-rate difference is contrary descriptive evidence only if its absolute value minus the limit exceeds 0.30 GB/s. Other outcomes are undecided. These selected endpoints are not six confirmed interventions. Confirm any inferred state dependence in a new controlled batch before assigning a mechanism.

Mark a kernel's process trace as unstable if its four fourth-window rates span more than 0.30 GB/s, or any trial's first and fourth windows differ by more than 0.30 GB/s. This diagnostic is fixed before collection. An unstable load-only process cannot supply an endpoint. If any of the six processes is unstable for the selected load-only kernel or for old read, that P3 comparison is **Insufficient data**. Keep all traces and ranges visible, and do not select a quieter replacement subset. New-read and assembly-read comparisons can therefore have different outcomes.

Also locate where the load-only rate approaches the old-read rate. Existing B1 reference medians were 73.075 to 75.735 GB/s at 4 MiB and 64.830 to 66.255 GB/s at 16 MiB. They were measured in two-buffer copy sequences. For the proposed one-buffer runs, the corresponding predictions are **est. 73 to 76 GB/s at 4 MiB** and **est. 64 to 66 GB/s at 16 MiB**, not acceptance bands. The size experiment tests whether the rates approach or cross between 8 and 16 MiB. [Ref10]

Expected 8 MiB gains under the proposed preparation are **est. 0 to 1% on CPU 2 at its earlier lower rate**, and **est. 2 to 5% on CPU 41 at its earlier reference rates**. A higher-rate state may give a larger gain. These estimates guide the comparison; no observation is excluded for missing them. A gain that differs between CPUs is a per-CPU result, not a failed confirmation of a size explanation. [Ref1][Ref2][Ref10]

## Sequence and decision points

```text
Check existing traces -> Validate runner -> Compare sizes
                                              |
                          +-------------------+---------+
                          |                             |
                          v                             v
              History unclear?                Sustained reads
              Test predecessor                and counters
                          |                             |
                          +--------------+--------------+
                                         v
                          Test one remaining mechanism
```

The diagram shows experiment order, not elapsed time. Each stage has a stopping condition below. An unresolved stage produces a bounded conclusion and a named missing observation.

**Trigger for Stage 3:** a diagnostic relation of the Stage 2 fourth-window rate to trial order or the kernel of the preceding process, or a named later comparison that requires interleaving different kernels. These observations motivate a test; they do not prove a predecessor effect. Record which trigger applies before scheduling Stage 3. All references to conditional mixed-sequence work below use this trigger.

## Stage 0: extract the evidence before adding code

Use the saved files on the development machine. No login is needed.

1. Recompute the original size comparison from every repetition as well as the best rates. Retain CPU, process, kernel, and run order.
2. Recompute the absolute rates of the first and second old-read intervals in every B6 A/A pair. Plot their paired difference by CPU, session, and sequence position. Do not substitute the old-8-MiB-minus-old-1-MiB value for that direct difference.
3. Plot all reference rates continuously. Keep the historical 69 and 70.5 GB/s lines only as annotations. Do not remove processes whose reference rates lie between them.
4. Read the B6 sequence and the worker path together. Record every warm-up, page read, barrier, output operation, and clock/counter read between kernels. The current sequence is already saved in the run script. [Ref3][Ref4]
5. Verify the instruction sequences and loop offsets of old, new, and assembly read against the saved machine-code listings. In the new runner, compare actual instructions and offsets again after linking. Source equality alone is insufficient. [Ref5]
6. Put the original run, the 06:05 UTC run, and the B1 assembly-read reference intervals in one table by size, CPU, kernel, and run. Keep the B1 two-buffer rows separate. Put the cache sizes beside this table. The 06:05 run already pairs old read near 67 GB/s with assembly read near 71 GB/s in three processes. Do not discard that evidence. [Ref9][Ref10][Ref11]
7. Report absolute old-read rates by every B6 position, including position 5 after old read at 1 MiB. Pair them with the assembly-read reference rates of the same process. This distinguishes restoration toward the original old-read rate from a new size effect. [Ref2][Ref4]
8. Assess whether the proposed equivalence checks can resolve their margins. Use B4, C1, B6 position 5, and B6's 1 MiB positions 2 and 4. For B6, split the four repetitions into {1, 3} and {2, 4}. For B4 and C1, apply the same split to successive blocks of four intervals. Retain the largest absolute value for each process and show transitions separately, without deleting them. Tabulate the per-CPU/session maxima, sample counts, and projected two-, four-, and eight-spread limits. Label these **est. for the new trial wrapper**. Fix the applicable margins and feasibility decisions under Stage 1's rule before collection. Saved B6 position 5 already gives two-spread limits of 0.155 and 0.118 GB/s on CPU 2 in the two sessions. A fixed 0.10 GB/s gate would fail there. [Ref12]

Output: one light-background HTML page with the paired old-read chart, reference-rate traces, exact tables, and source identifiers. This stage describes existing data. It does not establish a causal history effect.

Stop Stage 0 when the evidence table, position traces, source/loop checks, and equivalence-feasibility table are complete. If sources or accounting contradict the claimed size comparison, stop for reconciliation before a machine run. If the original small gain and the candidate above remain consistent with the files, proceed through runner acceptance to the size experiment. Conditional mixed-sequence work uses the trigger defined above. An existing B6 effect alone does not make that stage the first experiment.

## Runner design: change the sequence, preserve the read loops

Extend a scratch copy of `bwx`. Keep the original program and all old results intact. A separate one-thread trial mode is sufficient. Do not build a general experiment framework.

### Fixed setup

- One worker is pinned before allocation and first touch. The controlling thread uses CPU 0 and does not touch the benchmark buffer during a trial. Run only one benchmark process at a time. Reverse the worker CPU order in the second session of each stage. Record any intervening reboot or host configuration change.
- In the primary size experiment, one process allocates one selected size and runs one selected read kernel throughout. In conditional shared-allocation experiments, allocate and first-touch the 8 MiB buffer once per process. It stays mapped through all trials. A 1 MiB predecessor uses the first 1 MiB of that buffer, matching B6.
- Request the same huge-page policy as the earlier full-coverage runs. Record actual coverage. A failed page-policy request or unreadable coverage is a reported failure, not an assumed success.
- Preallocate and first-touch the output-record storage before the first trial. Bound its size. Record the size in the result. It must not allocate or grow during a trial.
- Preserve the read-loop bodies, their original loop offsets modulo 64, their calling convention, and old read's result consumption. Reject a build whose acceptance listing differs. Add no new read-loop variants before Stage 5.
- Pinning and output storage are held fixed across all conditions. The metadata and its memory traffic are part of the measurement method and need a control.

### One trial

```text
Page snapshot -> Prefix -> Predecessor -> Target x 4 -> Snapshot
```

This sequence is schematic. Each target window lasts at least 0.3 s. The prefix lasts at least 1.2 s. The predecessor lasts at least 0.3 s. These are proposed durations, not measurements.

- Prefix: old read over the full 8 MiB buffer for 1.2 s in every mixed-sequence trial. Record it as four consecutive 0.3 s windows. The size experiment instead uses the target itself as its prefix.
- Predecessor: the chosen loop and range for 0.3 s.
- Target: four consecutive 0.3 s windows, with no warm-up, page read, output, allocation, sleep, or barrier between predecessor and target or between target windows.
- Use whole passes. Check time after at least 8 MiB of reads, as the existing pass-mode worker does. For a 1 MiB loop, this means 8 passes between clock checks. Count only bytes actually read. Record actual durations and complete-pass counts.
- Target windows end at the first clock check after their requested duration. All primary rates use the actual bytes and times. Do not apportion bytes across a nominal boundary.
- Save timestamps and byte totals to memory. Flush records only after the trial. Record the actual predecessor-end-to-target-start gap. For a same-kernel trial, use prefix-end-to-target-start instead. The same gap quality check applies. A gap is not silently treated as zero.
- Optional time bins inside a window have a requested width of 10 ms. Close each bin on a real clock check. Save actual boundaries and bytes. Aggregate the bins by summing bytes and time, not by averaging rates. The bins are descriptive until the measurement-overhead check passes.
- Read page state before the prefix and after the final target. Unchanged snapshots do not prove that physical pages stayed fixed between them.

The prefix gives every condition the same immediate preparation. It may suppress a naturally occurring state. The long single-kernel observation in Stage 4 addresses this limitation. Do not call the prefix a cache reset.

### Required records

Every trial records session, CPU, process/allocation identifier, trial order, random seed, previous trial's condition and target (or “none”), current predecessor, target, sizes, function addresses, prefix-window rates, predecessor duration, transition gap, target-window bytes and times, and page snapshots. Also record the binary digest, compiler flags, kernel listing digest, host identity, and page policy.

Record thread CPU time and the worker's voluntary/involuntary context-switch counts around the whole trial. Read these outside the prefix-to-target sequence in the timing-only mode. Record system load before each process. A counter run adds per-target-window CPU time and counter metadata.

Keep raw rows for interrupted, invalid, or incomplete trials. Identify them in an explicit exclusion table. Do not retry individual slow trials until a desired result appears.

## Stage 1: establish that the runner can measure the effect

These are acceptance checks for later implementation. They have not run.

1. **Code and accounting.** Verify the machine code, pinning, whole-pass byte counts, monotonic timestamps, and the old-read result sink. Verify that an unsupported CPU target or malformed sequence fails before work starts.
2. **Compatibility mode for conditional mixed-sequence work.** Replay B6's 13-entry sequence for four rounds using the unchanged interval wrapper in `bwx8`. On each CPU in each session, run 2 fresh processes. Each process supplies 8 old-read A/A pairs immediately after assembly read. The positional effect is reproduced on that CPU/session only if the first interval is slower in all 8 pairs in both processes. This is a descriptive wrapper check, explicitly exempt from the 6-process contrast rule. Report absolute rates and differences beside B6. Failure blocks the mixed-sequence stage until the difference is investigated. It does not block the original same-kernel size experiment if that experiment's own acceptance checks pass.
3. **Measurement overhead, if fine bins are needed.** Compare trial mode with only window records against trial mode with 10 ms bins. Use 6 fresh processes per CPU/session for each selected kernel and size. In each process, interleave the two modes in a balanced order under the same preparation. Include repeated same-mode controls. For the primary size experiment, keep one read kernel per process. A mixed-sequence check requires that branch's prefix acceptance. Use the decision rule below for both the first and last target windows.
4. **Transition fidelity.** Trace the actual call path in a non-measuring test. Check that a target warm-up, page read, output flush, counter read, or barrier cannot enter the timing-only predecessor-to-target path. Validate that recorded gaps include all wrapper work between those loops.
5. **Previous-trial carry-over, for conditional shared-allocation work.** The primary size experiment has only one read kernel per process and needs no cross-kernel prefix claim. Before the paired-allocation experiment, deliberately run 2.4 s of old, new, or assembly read as previous activity at 8 MiB. This matches the preceding trial's prefix plus target exposure. Follow it with the planned same-kernel prefix and target. Cross all three previous activities with all three targets. Each process runs the nine conditions four times. Use 6 processes per CPU/session. Compare the final prefix window and first target window across previous activities for a fixed target. There are 18 rate contrasts per CPU/session: 3 targets × 3 pairs of previous activities × 2 windows. Each contrast uses two spreads. Before the broader mixed-sequence experiment, use 1.2 s of previous activity, matching that schedule's final target. Then check the common old-read prefix, an old-read predecessor, and an old-read target. Its 3 pairs of previous activities × 2 windows give 6 contrasts per CPU/session, also two spreads each. Also inspect dependence on the recorded previous target within each condition of the actual balanced schedule. The prefix is not accepted merely because its duration sounds long enough.

**Equivalence gates.** Fix each margin before its acceptance batch, using only earlier same-condition variation. Stage 0 supplies the initial forecast. For counter checks after Stage 2 or Stage 3, use that branch's uncounted observations to update the forecast before any mode comparison is collected. Never choose a margin after seeing a mode or previous-activity effect.

| Quantity compared between modes or previous activities | Spreads in its gate limit | Permitted margin |
|---|---:|---:|
| One rate, including each prefix contrast | 2 | 0.10 to 0.30 GB/s |
| A two-rate difference between modes | 4 | 0.10 to 0.30 GB/s |
| A four-rate interaction between modes | 8 | 0.20 to 0.60 GB/s |

For each selected branch and quantity, let L0 be the largest projected limit across its planned conditions, CPUs, and available sessions. Round twice L0 up to the next 0.05 GB/s. Choose that margin, clipped to the table's lower and upper bounds, and freeze it in the schedule. The upper bounds limit the mode effect that the design is prepared to overlook. They are design choices, not estimates of noise. This rule does not change P1's 0.30 GB/s margin.

If L0 is at or above the chosen margin, the saved protocol forecasts **precision insufficient**. Do not schedule the full optional gate batch by default. Leave that branch descriptive or propose a separately reviewed pilot that could improve precision. For first-window mixed-sequence counters, make this feasibility decision from the uncounted Stage 3 batch before collecting counters. Large first-window variation can make the four- or eight-spread gate infeasible even at the upper bound. A wider margin is not an automatic remedy.

A gate passes on a CPU/session only if the absolute median difference is within its A/A limit, the limit is below its frozen margin, and the absolute median difference plus the limit is at most that margin. All 18 paired-allocation prefix contrasts, or all 6 mixed-sequence prefix contrasts, must pass on both CPUs in both sessions for the corresponding prefix. All mode comparisons required for a selected use must also pass. This is an operational repeatability gate, not a confidence interval. A large limit never counts as a pass.

If the instrumentation gate fails or is incomplete, state “mode equivalence not established”. Fine bins or counted contrasts remain descriptive. Continue timing with window-only records if their accounting checks pass. The compatibility wrapper and trial wrapper remain different experimental conditions.

If prefix equivalence is not established, the affected stage cannot use that prefix for causal conclusions. Failure caused only by a large limit means **precision insufficient**. It is not evidence of carry-over or of a mode effect. Do not lengthen the prefix to remedy that failure. If a previous-activity difference is repeatable under the directional rule, a separately recorded calibration may try 2.4 s, then 4.8 s prefixes on fresh processes. Both changes alter the nominal work budget. If equivalence still fails, stop that branch. A design that explicitly groups conditions by previous activity, or changes how variation is estimated, needs a new schedule and review. Do not add uncontrolled repetitions until the gate passes.

Except for the specified B6 wrapper check, acceptance comparisons use 6 processes per CPU/session and four repeats per mode/condition. The four-repeat rule and same-mode controls below apply. Include every preparation used by the selected later stage. Fix the schedule and emit its count in a dry run before measurements. Acceptance runtime is listed separately from the main timing stages; the runner must report its nominal work before execution.

## Stage 2: test the size explanation first

This is the first measurement stage after code/accounting acceptance. It tests P1 and P2 under the original one-read-kernel-per-process structure. P3 and the mixed-sequence experiment are conditional later work.

Use separate allocations for 32 KiB, 1 MiB, 4 MiB, 8 MiB, and 16 MiB. The added 4 MiB and 16 MiB points test where the load-only rate approaches the old-read rate. Each added size requires 72 single-kernel processes and 691.2 s of nominal kernel work. The mixed-sequence stage's 3,110.4 s is conditional work. The 2 MiB and 32 MiB sizes are deferred. The initial grid will not locate a crossing more precisely than its measured bracket. The original 1 GiB observation remains contextual evidence.

For each size and kernel, run 6 fresh processes per CPU/session. Each process contains four trials of that kernel only. Each trial uses it as a 1.2 s prefix, followed by four uninterrupted 0.3 s target windows. There is no different predecessor and no other read kernel in that process. There are 360 processes across five sizes, three kernels, two CPUs, and two sessions.

Pair the three kernel processes by replicate index. For each size/CPU/session, the six replicate sets use the six possible orders of the three kernels once each, with a saved random assignment. Randomize size order within each replicate block before collection. Record preceding processes as well. This balances launch order but does not prove independence across fresh allocations or erase host-wide history.

- Primary value: the fourth-window old-to-new difference and percentage gain in each matched process set. A process's kernel rate is the median of its four trials. Keep the first-window values beside it.
- Apply the [shared repeatability rule](#shared-repeatability-rule) to the rate differences, using matched process sets as the units. Its A/A limit measures within-process variation only. It is a lower bound on the variation relevant to a comparison of different processes, not an uncertainty bound for that comparison.
- Test old-8-MiB minus old-1-MiB under P1's 0.30 GB/s margin. Every one of the six matched-set differences must satisfy absolute difference plus the two-rate limit at most 0.30 GB/s. Require this on each CPU/session. Test new-8-MiB minus new-1-MiB and assembly-8-MiB minus assembly-1-MiB separately under P2. Each is a two-rate contrast. A difference too uncertain to establish equivalence does not support a flat old-read rate.
- The size contrast compares separate process sets. Pair their process indices by a schedule fixed before collection. Sum the four constituent A/A spreads when comparing the 8 MiB old-to-new rate difference with the 1 MiB difference. This is a comparison under the allocation policy, not a same-physical-pages intervention.
- At every size, report all six matched-set differences and gains, and their range, beside each median. For a size contrast, also report all six matched-set contrast values and their range. Plot both absolute rates and gains. Separate levels must stay visible even when all six differences share a sign. A confirmed direction does not establish one common magnitude.
- Decompose the collapse of the absolute new-minus-old advantage: `ΔG = (new_1 − new_8) − (old_1 − old_8)`, in GB/s. Report both terms. If ΔG is resolved and nonzero, their signed shares are `100 × (new_1 − new_8) / ΔG` and `−100 × (old_1 − old_8) / ΔG`. Shares can be negative or exceed 100% when one kernel offsets the other's change. The original best-rate example is a 17.55 GB/s new-read decrease and a 0.05 GB/s old-read decrease. Their net is 17.50 GB/s. [Ref1]
- At 8 MiB, report the rate range of each kernel and the differences of matched process sets. These are different allocations. Do not label them a same-buffer test of P3.
- If P1 meets its equivalence margin and P2 shows the predicted decreases, the measurements support the candidate's bounded explanation of the size comparison: the new loop carries the loss of advantage. They still do not identify old read's limiting core resource or the precise data-supply bottleneck. If P1 or P2 is contradicted, stop using this candidate as the explanation and choose a new discriminating test. If either is undecided, name the needed precision or observation.
- The fourth window is a measurement at that elapsed time, not proof that the rate has reached a permanent steady value. If window position or run order changes the answer, investigate that dependency. If P1/P2 hold and P3's state dependence is the next question, use the paired-allocation branch below. Stage 3 uses the trigger in “Sequence and decision points”.
- If the gain changes with preparation, quantify that change. The original run's exact hardware state was not recorded. Do not claim that the new history experiment reconstructs it.

The next result should read like: “Under preparation P, old read was X GB/s and new read was Y GB/s at 8 MiB. The gain was Z%.” If the conditional history test runs, add its measured change in gain in percentage points. Fill these values only from measurements.

### Conditional paired-allocation branch for P3

This is additional work, not a substitute for the primary sweep. After the 8 MiB prefix gate passes, run old, new, and assembly read on one 8 MiB allocation. Each trial has the target's own 1.2 s prefix and four 0.3 s target windows. Each process runs each kernel four times. Use 6 processes per CPU/session: 24 processes and 691.2 s (11.52 min) of nominal work. Across each CPU/session's 24 cycles, use all six kernel permutations four times with saved randomized row assignment. Record actual previous targets at cycle boundaries.

Plot each process's fourth-window old rate against its new and assembly rates. Keep the individual trial rates and time order beside the medians. Report ranges, instability marks, and P3's separate new-read and assembly-read endpoint checks per CPU/session. This is a relation across preparations on the same allocation, not proof that a hidden state persisted while kernels changed. Apply the P3 rules above. Missing coverage, an unstable process, or a failed prefix gate yields **Insufficient data** for the affected comparison. A high/low comparison is not obtained by inventing new labels.

## Stage 3: conditional test of history in mixed sequences

This conditional test changes the predecessor, then measures the same target. It addresses the effect found in mixed sequences, not the original one-kernel-per-process gain. It uses the trigger in “Sequence and decision points”. It does not label a whole process as “low” or “high”.

| Predecessor, 0.3 s | Targets, each 1.2 s in four windows | Purpose |
|---|---|---|
| Old read, 8 MiB | Old, new, assembly read at 8 MiB | Same-loop preparation and reference condition |
| New read, 8 MiB | Old, new, assembly read at 8 MiB | Test the actual rewritten loop as predecessor |
| Assembly read, 8 MiB | Old, new, assembly read at 8 MiB | Connect the intervention to the earlier B6 observation |
| Old read, first 1 MiB | Old, new, assembly read at 8 MiB | Test the other history that occurred in B6 |

- Each process runs all 12 conditions in four cycles. Each cycle contains every condition once. It contains 48 trials in total.
- Generate a position- and preceding-condition-balanced schedule before collection. Number the 12 conditions 0 to 11. Start with the order `[0,1,11,2,10,3,9,4,8,5,7,6]`. Make 12 rows by adding a row number modulo 12 to every entry. Randomly relabel the conditions with a saved seed. Use two copies of these rows, shuffle the 24 rows, and assign them to the 6 processes × 4 cycles. Within rows, each ordered pair of distinct conditions occurs twice. Every condition occupies every position twice. Record actual previous targets at row boundaries too; the boundary transitions are additional observations, not assumed balanced.
- Run 6 fresh processes per CPU, on CPUs 2 and 41, in each of 2 sessions. These are 24 process units, each with a fresh allocation. Their independence is not established. Windows and trials within a process are repeated measurements of that unit. The prefix check and preceding-condition balance address carry-over explicitly.
- Reverse the CPU order in session 2. Preserve the protocol, binary, and analysis rules. Record any intervening reboot or host configuration change.
- Keep every rate continuous. The old rate thresholds can be drawn on plots, but do not determine which trials enter the primary estimates.

### Fixed primary questions

Let `R(T | P, w)` be the median target rate over the four repeats in one process. `T` is the target, `P` is the predecessor, and `w` is the window. All rates below are in GB/s.

1. **Does new read change the next old-read measurement?** Primary difference: `R(old | new, first) − R(old | old, first)`. A negative difference means old read is slower after new read. The corresponding assembly-predecessor contrast is a pre-specified secondary replication. Test and report it under the same rule, but do not substitute it for a failed new-predecessor contrast.
2. **Does that history change the benefit of the rewrite?** For a fixed predecessor, the read difference is `G(P, w) = R(new | P, w) − R(old | P, w)`. Primary history interaction: `G(new, first) − G(old, first)`.
3. **Does the difference persist?** Report the same contrasts in the fourth window. The first window is the primary test of immediate history. The fourth is the specified persistence check. Do not replace a failed first-window test with the most favorable bin.

Also report the percentage gain `100 × (R(new | P, w) / R(old | P, w) − 1)` for each process and window. Decide rate differences in GB/s first. Percentages describe their size.

## Shared repeatability rule

This is a conservative repeatability rule, fixed before collection. It is not a confidence interval or a probability that a mechanism is true. The unit is a matched process set in Stage 2 and one process in a comparison whose conditions share an allocation. Neither unit is claimed independent of host-wide history.

- For each condition and window, split trials 1 and 3 against trials 2 and 4. Their median-rate difference is that process's A/A value. The controls use the same kernel address and preparation.
- The A/A spread for that condition/window is the largest absolute A/A value over the 6 processes of one CPU and session.
- A contrast's limit is the sum of the A/A spreads of its constituent rates. A two-rate contrast uses two spreads. The four-rate history interaction uses four spreads.
- Call a contrast **repeatable on a CPU in a session** only if its median across the 6 unit values exceeds its limit in absolute value and all 6 values have the same sign. For Stage 2, report the six values and range as well. Its limit omits between-process variation and cannot be presented as a bound on that uncertainty. P1 additionally requires every set to fit its equivalence margin.
- For a directional effect, call it **confirmed on a CPU** only if it passes with the same sign in both sessions. Call it **confirmed on both tested CPUs** only if both CPUs also agree in sign. Report CPU-specific outcomes. The size answer does not require identical gains across CPUs.
- The same rule applies to the pre-specified size contrasts and rate differences of Stage 2. For mixed sequences it applies to the two primary contrasts, the specified assembly-predecessor replication, and their persistence checks. P3's selected endpoint comparison remains descriptive as stated above. Other predecessor/target contrasts and fine time bins are exploratory. Any mechanism chosen from them needs a separately recorded confirmation schedule on new processes.
- An effect inside the limit is “not distinguished from variation”, not proof of equality. Report the limit in GB/s. A failed high-rate observation is “not observed”, not rejection of the associated mechanism.

Do not silently change the number of units. A CPU/session with fewer than 6 valid units is incomplete for this rule. Keep the partial observations, and stop for a scheduling or protocol decision before adding a replacement batch.

### Quality checks and exclusions

Pre-register these checks in the analysis and show results with and without quality exclusions:

- Reject a trial from every numerical estimate if pinning or byte accounting failed, or required records are missing. Detect interruption from the runner's signal/exit record or a trial-start record without a trial-complete record. These are execution failures.
- Mark a trial as disturbed if thread CPU time is below 99% of its wall time, its involuntary context-switch count rises, or the predecessor-to-target gap exceeds 100 µs. These are proposed diagnostic limits. Report the measured values rather than treating the limits as hardware constants.
- Mark a trial if huge-page coverage differs between its snapshots. Keep such trials as observations of changing coverage. They cannot establish a history effect under unchanged observed coverage.
- A “disturbed” or coverage-change mark fails the filtered primary comparison. Such rows remain in the unfiltered estimate if their accounting is valid. Apply completeness per contrast: a two-rate contrast needs its 8 trials (2 conditions × 4 repeats); a four-rate contrast needs its 16 trials. In Stage 2 these come from 2 or 4 processes of a matched set. In shared-allocation work they come from one process. An invalid unrelated condition does not discard the unit. If a required trial fails, the unit is incomplete for that contrast. Preserve filtered and unfiltered counts and estimates side by side.
- A context-switch-free trial does not prove the absence of interference. Unchanged page snapshots do not prove physical-page identity.

## Stage 4: observe sustained rates and add counters cautiously

### Observe without forcing a level

The uncounted sustained batch is fixed work after the size sweep, subject to acceptance and host stop rules. It does not depend on running either conditional branch.

For old read, new read, and assembly read, run 60 s on one fixed 8 MiB allocation with only that kernel after first touch. Use the accepted measurement mode. Preserve the complete time sequence. Each kernel has its own process. The old-read traces test whether its rate also varies over that duration; they do not measure old read at the exact same hidden state as a different process's load-only transition.

Run 3 fresh processes per kernel, CPU, and session: 36 processes across both sessions. Stop after that fixed batch even if no high-rate interval appears. No “run until high” selection is allowed. The historical thresholds remain plot annotations.

This branch asks whether any kernel changes rate without a kernel switch. If Stage 3 runs, it also checks whether that stage's common old-read prefix excluded behavior seen during uninterrupted reads. A newly observed transition is descriptive evidence until it can be changed by a controlled intervention.

### Counter validation and matched collection

Use only worker-local user-mode counters without root. Start with the previously collected cycles, instructions, L1 refills, L2 refills, and last-level read misses. Record event encodings and their source. [Ref6]

Before interpreting a refill as a physical traffic count, obtain the processor's authoritative event definitions. Insufficient data: the existing results have fewer L1 than L2 refills per line, and the meaning of that relation is not established. Until validated, report raw event names and counts without assigning a cache mechanism. [Ref2]

- Use three explicit modes: **closed**, no counter group open; **open, not read**, groups open but no target-boundary reads; and **open, read**, groups open with window-boundary reads. The closed mode is the timing-only baseline. Open or close groups before the prefix, with checked return values. Record the mode and actual transition gap.
- For size counters, use one selected kernel and size per process throughout, as in Stage 2. Within its allocation, interleave all three modes with four repeats per mode. Use 6 processes per kernel/size/CPU/session. Balance mode order before collection. This preserves the primary experiment's kernel history.
- For mixed-sequence counters, cross the three modes with all four old/new predecessor × old/new target conditions at 8 MiB. Use 6 processes per CPU/session and four repeats per cell. Independently balance mode and condition order. This check requires that branch's prefix acceptance. Do not require it when only size counters are needed.
- Compare open/not-read against closed, open/read against open/not-read, and open/read against closed. Use the same-mode A/A spreads from repeated cells. A rate-mode comparison uses two spreads. Comparing a two-rate history contrast between modes uses four spreads. Comparing the four-rate interaction between modes uses eight spreads. Apply Stage 1's frozen margin for the named rate or contrast. All required comparisons must pass for the selected use. Otherwise report “mode equivalence not established”, distinguishing insufficient precision from a resolved mode effect.
- If counted mode changes the first-window history contrast, it cannot explain the uncounted transition. Report that instrumentation changes the experiment. If the precision is insufficient for equivalence, keep the counts descriptive. Do not infer that the underlying history effect vanished.
- Read counters once per 0.3 s target window, not per 10 ms bin. Record enabled time, running time, and thread CPU time. Reject unsupported or multiplexed event counts for interpretation. Keep the timing rows.
- Report counts per 64 B read, instructions per byte, cycles per byte, and cycles per thread CPU second. The last quantity is a clock estimate. Do not divide cycles by wall time that includes descheduling.
- Collect the size contrasts with counters only after the applicable mode checks pass. Repeat the two primary mixed-sequence contrasts with counters only if that branch is needed and its own mode checks pass. Use 6 processes per CPU in each session. Do not compare counters from a copy-interleaved trace with counters from uninterrupted read and attribute every difference to bandwidth state.
- For sustained-read counting, repeat the same fixed Stage 4 batch with counters after the measurement-mode check. If it contains no high-rate observations, state the missing observation. Low-state counts cannot substitute for high-state counts.

Counters describe where behavior differs. Similar counts do not prove identical microarchitectural state. A causal claim still needs an intervention.

## Stage 5: choose one remaining mechanism test

Choose a branch using the confirmed results. Record its exact schedule before collecting new data. Do not launch every branch automatically.

| Established observation | Next controlled test | What it could establish | What it cannot establish alone |
|---|---|---|---|
| A predecessor changes a subsequent rate | Allocate two 8 MiB buffers in every condition. Compare the predecessor on the target buffer against the predecessor on the other buffer. Swap buffer roles in the paired trial. Keep the prefix, target, total allocated memory, and code fixed. | Whether the effect depends on addressing the target buffer during preparation | A particular cache, prefetcher, or physical page as the cause. The second buffer changes the footprint relative to Stage 3, so first reproduce the effect with both buffers allocated. |
| A predecessor effect decays across target windows | Insert a fixed delay of 0, 1, 10, or 100 ms after the predecessor. Measure actual delay. Use the same sleep method for each nonzero delay and record thread CPU time. | Dependence on an idle delay versus target reads | A cache lifetime. Sleeping also changes scheduling and possibly core operating state. |
| The small gain survives same-kernel preparation and varies with size | At fixed loop offset and buffer, compare the load-only loop with one specified added-instruction variant at 1 MiB and 8 MiB. Start with the saved 4-`nop` variant, whose extra instructions do no data work. Verify its listing. | Whether extra instructions have a different rate cost at the two sizes | A unique core bottleneck or a specific shared-cache bandwidth limit. A `nop` is not a vector add. |
| Rates differ between allocations or change with apparently unchanged coverage | The planned D2 experiment: physical-page addresses before and after observations, with user-authorized root access | Whether the observed rate changes coincide with a change in physical pages | That unchanged pages exclude cache state, or that correlation proves page placement causes the rate |

For the first three branches, use the Stage 3 sampling unit, 6 processes per CPU/session, and two-session confirmation. Each arm gets four repeats. Use a two-rate limit for one changed factor, or a four-rate limit for a difference of effects. Freeze the selected contrast and primary window first. New claims outside that contrast remain exploratory.

The physical-address branch keeps the limits and approval requirements of Part D. A new allocation, a different pointer, and unchanged huge-page coverage are not replacements for physical-page observations. [Ref7]

## What counts as progress, and what counts as an answer

| Result | Allowed conclusion |
|---|---|
| Reproduced low and high rates | The rate variation exists under the named protocol. Its cause is open. |
| Confirmed predecessor contrast | Recent execution history changes the target's rate under this preparation. |
| Confirmed change of the old-to-new gain in a mixed sequence | History changes the gain measured in that mixed sequence. State its sign and size. This does not explain the original run, which had no other read kernel as predecessor. |
| P1 establishes nearly constant old read and P2 establishes falling new/assembly rates | The per-kernel size contrasts support the candidate's bounded explanation of the shrinking advantage. Name the unresolved core and data-supply mechanisms. |
| Small gain remains under same-kernel preparation | The original size behavior persists under the specified preparation. A mixed-sequence predecessor effect is not needed to produce it. |
| Counter difference with validated measurement mode | A named event count differs. State which competing predictions this distinguishes. |
| A controlled mechanism change predicts and reproduces the gain change on both CPUs and sessions | Evidence supports that mechanism within the tested conditions. State any remaining unexplained part. |

Do not call the 8 MiB problem solved merely because a threshold can label the data or one hypothesis is not rejected. A complete answer needs the old and new rates under controlled conditions, the part of the gap explained by an intervention, and the remaining uncertainty. If that evidence is absent, write **Insufficient data** and name the next discriminating measurement.

## Run budget and gates

The counts below are proposed, not completed. Durations are nominal kernel work, calculated from the design. They exclude allocation, page inspection, output, host waits, acceptance checks, and pass overshoot. They are not safe wall-time bounds.

| Stage | Processes across both CPUs and both sessions | Nominal kernel work |
|---|---:|---:|
| Stage 2: 5 sizes × 3 kernels, 4 trials per process, 2.4 s per trial | 360 | 3,456 s (57.6 min) |
| Stage 4: sustained old/new/assembly read, uncounted | 36 | 2,160 s (36 min) |
| These two timing stages together | 396 | 5,616 s (93.6 min) |
| Conditional paired-allocation branch for P3 | 24 | 691.2 s (11.52 min) |
| Conditional Stage 3: 48 trials per process, 2.7 s per trial | 24 | 3,110.4 s (51.84 min) |
| Including both conditional timing branches | 444 | 9,417.6 s (156.96 min) |

- Stage 0 comes first. Stage 1's relevant acceptance checks must pass before the size experiment supplies conclusions.
- Run the size experiment first, then the fixed uncounted sustained batch. Use the results to choose counters or a conditional branch under its stated trigger. Inspect the mixed-sequence result before adding history-mechanism variants.
- Acceptance checks are additional work. The conditional paired-allocation prefix check is 24 processes × 36 trials × 4.8 s = 4,147.2 s (69.12 min). It is unnecessary for the primary one-kernel-per-process sweep. The mixed-sequence old-prefix check adds 24 processes × 12 trials × 3.9 s = 1,123.2 s (18.72 min). Its B6 wrapper check adds 8 processes × 52 intervals × 0.3 s = 124.8 s (2.08 min). Apply the feasibility screen before scheduling an optional acceptance batch. Stop a branch if its acceptance fails.
- Counted repetitions, optional 10 ms instrumentation checks, longer-prefix calibrations, and Stage 5 are further batches. Their runner must print the selected conditions, process count, and nominal work before execution. Do not hide acceptance or conditional work inside the 93.6 min figure.
- A host stop interrupts the batch. Preserve it as incomplete. Report which scheduled work remains. No experiment has permission to run through a host reservation to complete its count.
- The initial fixed batch can end without an explanation. That is a valid outcome. Design review is complete when the protocol and its limits are reviewable, not when the future measurements are known.

## Execution constraints for later work

The target is CRB, the source of these results. The generic Delphi rules do not make a different host a substitute for this Arm experiment. No login is required for the current design task.

For a later authorized run, follow the existing CRB handoff: read the reservation channel before every login, refuse access during a reserved block, check the marker file as the first remote action and before each process, record system load, and preserve the stop controls. Use only the permitted CPUs and project directory. Do not run root commands or change system settings. Do not reuse a past `STOP_AT=none` decision without checking current reservations. [Ref7]

The design does not require sending a channel message. Missing access to the reservation record blocks machine use. Builds and code validation must follow the host rules as well as benchmark runs.

## Deliverables and validation

Later implementation should produce:

1. The scratch runner, preserved loop listings, source/binary digests, and a dry-run schedule with exact counts.
2. Tests that catch an intervening warm-up, lost/duplicated bytes, unreported counter failure, and mixing observations from different processes. Synthetic analysis cases must distinguish a real predecessor effect from an order trend, an allocation-only difference, and an effect caused solely by the previous trial's target. A noisy equivalence check must fail. P1 must fail equivalence when one matched set falls outside its margin despite a small median. P3 must not call unstable traces or a non-endpoint old-rate outlier compatible.
3. Raw trial/window rows, metadata, interrupted-process records, and an explicit exclusion table.
4. A light-background HTML report with:
   - paired old/new dots by buffer size and preparation, with rates, gains, all six set values, and ranges;
   - the new-read and old-read terms of the lost-advantage decomposition, in GB/s;
   - the complete 60 s sustained traces for each kernel;
   - if Stage 3 runs, target-rate traces after each predecessor using actual elapsed time;
   - if shared-allocation work runs, paired first/fourth-window dots for each allocation and individual trial traces;
   - separate CPU and session panels, with exact tables beside the charts;
   - a statement of what intervention explains what part of the 8 MiB gain, with missing evidence stated explicitly.
5. A result handoff that records protocol changes and remaining evidence gaps.

Validation of this design itself: local source inspection, verification of cited paths, recomputation of the original gains and nominal work counts, and the shared file-based review. No runner implementation, machine-code build, hardware test, or new causal measurement has been performed for this document.

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/one-thread.csv`: original per-process repetitions and best rates. Context: `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md`, “What the existing files already show”.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/results.md`: the reviewed result handoff, particularly H1, H2, Q1a, and Q1c. Recount: `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partBC-analysis/recount/recount_results_md.py` and `recount_results_md.txt`. Raw folder manifests: `session1-folders.txt` and `session2-folders.txt` in this directory.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/bwx.c`: `call`, `worker`, and the main interval loop. These show the result sink, first touch, warm-up, page reads, clocks, barriers, and output.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/run_bwx.sh`: `B6SEQ`, `step_B6`, and the process wrapper.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/crb-build-2/listing.txt`, `offsets.tsv`, and `build.txt`. Original loop reference: `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md`, B.8. Counter metadata and observations: `/home/jhan/workspace/titan/cache-perf/crb/results/partBC-20261114/analysis/C1.txt` and `C2.txt`. Processor event semantics still need authoritative validation before a causal interpretation.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md`, “The machine, and the rules for using it” and “Stop controls”. Root-only physical-page work: `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md`, Part D, step D2.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`, function `one` and the one-thread sweep. Sources for the original binaries: `bandwidth.orig.c` and `bandwidth.c` in that same directory. Current production source: `/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c`, function `worker`.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html`: cache-size table and the section defining the SLC. These are the local report's recorded hardware sizes.
- [Ref10] B1 raw files: `/home/jhan/workspace/titan/cache-perf/crb/results/B1-20261114T012315Z/B1.csv` and `/home/jhan/workspace/titan/cache-perf/crb/results/B1-20261114T043752Z/B1.csv`. Use `asmread` reference rows only, with per-process medians. These processes also ran copy and held two buffers.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/results/cread-20261113T060510Z/cread.csv`: old read, assembly read, and the C load-only variant in one process. The earlier plan's H1 candidate is in `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md`, “Hypotheses” and “What the existing files already show”.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/results/B6-20261114T014825Z/B6.csv` and `/home/jhan/workspace/titan/cache-perf/crb/results/B6-20261114T050300Z/B6.csv`: second old-read intervals at positions 8 and 11, restored-rate intervals at position 5, and same-condition variation at positions 2, 4, and 5. Use the exact rate from each T row's bytes and elapsed time. The second-interval summary pools 64 intervals per CPU/session before taking the median. The A/A check takes each process's four repetitions at a fixed position, then the maximum absolute split difference over all eight processes of a CPU/session.
