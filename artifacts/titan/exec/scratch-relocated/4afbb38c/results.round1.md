# Result handoff: the two open questions of the new C kernels (Parts A, B and C)

## Short version

We measured two open questions about a memory benchmark on one Arm test server, twice in one night, and every run that needs no administrator rights completed. With 120 threads, the read loop from before the rewrite of 2026-11-13 moved 158.06 to 178.72 GB/s more in total than the rewritten read loop (33.8 to 37.9 % of its own total), under all 8 ways of timing that we tried. For one thread with an 8 MiB buffer the planned decision rule gave no decision for the copy loops, and the user has nine decisions to make (see "Open decisions for the user").

- Why the rule gave no decision: its two rate limits (69 and 70.5 GB/s) do not fit the data. See "Limits".
- The numbers of the second sentence are the median of each timing setting, per session [Ref7][Ref21].

## Words used here

**Machine, files and runs**

- **CRB**: the Arm Phoenix Reference Server (128 cores). All measurements ran there.
- **Development machine**: the x86-64 server that holds this folder. The analysis ran there.
- **Plan, handoff**: `plan.md` (what to test and how to decide) and `handoff.md` (how to execute it) [Ref1][Ref2]. "Plan rule 5" is rule 5 of the plan. "Handoff B.10" is section B.10 of the handoff.
- **Specification v1**: the design of `bwx` in the handoff, sections B.1 to B.10.
- **Lead**: the agent that executed the handoff. **Lead's record**: its own notes. They are not in a file, so a claim that rests on them cannot be verified from the result files [Ref20].
- **Run of 2026-11-13**: the earlier benchmark run (at 18:12 UTC) that raised the two questions. It is not a part of Parts A, B and C. **Run of 2026-10-30**: an earlier run in which old read gave 365.10 to 368.25 GB/s with 120 threads and two buffers per thread [Ref1].
- **Part A / B / C / D**: the four parts of the plan. Part A is screening (a first look with the existing binaries), and it decides nothing. Part B is the deciding measurements with `bwx`. Part C repeats some steps with counters of the core. Part D needs root and was not run (D1 mesh counters, D2 physical page addresses).
- **Root**: administrator rights on CRB.
- **Session (s1, s2)**: one run of all steps of Parts B and C. **Visit**: one login to CRB that runs one or more steps.
- **Short run**: one run of every sequence with intervals of 0.1 s, before session s1. It checks the output of `bwx` and decides nothing.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it while his measurements run.
- **sha256**: a checksum of a file. Two files with the same value are equal.
- **est.**: an estimate, not a measurement.

**Benchmark**

- **Kernel**: one timed loop of the benchmark. It is not the Linux kernel.
- **`bw_old` / `bw_new`**: the benchmark `bench/bandwidth.c` built from the source before and after the rewrite of 2026-11-13.
- **`bwx`**: the changed copy of `bench/bandwidth.c` that Parts B and C use. `bwx_o0`, `bwx_o36`, `bwx_o52` are three more builds with both copy loops at one loop offset.
- **Loop offset**: the address of the first instruction of a loop, modulo 64 (the remainder after division by 64).
- **asm**: written in assembly.
- **Old read / new read / asm read**: the read loop before 2026-11-13, the read loop since then, and the same loop written in assembly. The same three forms exist for write and copy.
- **Vector add**: an add instruction on a 128-bit register. Old read has 8 of them per 128 B. New read has none.
- **`nop`**: an instruction that does nothing. **`read_sparse`**: a read loop with 16 instructions per 128 B and no vector add (4 load instructions of 32 B each, 9 `nop`, and the 3 instructions that advance and close the loop).
- **Process**: one start of the benchmark. **Interval**: one timed period inside a process. **Pass**: one sweep of a thread over its whole buffer.
- **Mesh 0 / mesh 1**: the two halves of the chip. Mesh 0 holds CPUs 0 to 63. Mesh 1 holds CPUs 64 to 127, and we may use CPUs 64 to 119 of it. "64+56 threads" means 64 threads on mesh 0 and 56 on mesh 1.
- **Rate**: bytes per second in GB/s (1 GB = 10^9 bytes). **Total (M_hist)**: the bytes of all threads divided by the longest time of a thread. **M_sum**: the sum of the thread rates. The decisions use M_hist.
- **Setting**: one combination of stop method (whole passes, or one common stop time), interval length and start (common start, or one offset per thread).
- **Reproduction condition**: whole passes, 0.5 s, common start. It is the timing method of the run of 2026-11-13.
- **End skew**: the latest end time of a thread minus the earliest, in one interval. **Irregular interval**: an interval in which a thread started more than 100 µs late, or, with the common stop time only, in which the end skew is above 5 ms. With whole passes the end skew is reported and does not make an interval irregular (analysis choice A5).
- **2 % check**: plan rule 7 for whole passes. One pass must take at most 2 % of the interval, which means at least 50 passes per thread.
- **Huge-page coverage**: how much of a buffer is on 2 MiB pages. "Full" means all of it. **`--no-thp`**: an option of the benchmark that asks Linux for no 2 MiB pages.
- **`thp_collapse_alloc`, `pgmigrate_success`**: two counts of the Linux kernel. They rise when the system merges pages into a 2 MiB page, or moves a page.
- **Counter**: a hardware event counter of one core. **PMU**: the unit of the core that holds the counters. **L1 refill, L2 refill**: a 64 B line that the first, or the second, cache level of the core had to fetch. **Last-level read miss**: a read that the last cache level did not hold.
- **1-minute load average**: the Linux value for the average number of tasks that are runnable or in uninterruptible wait (for example for disk I/O) over about the last minute.

**Comparisons**

- **A/A pair**: one loop that exists twice in the binary. **A/A spread**: the largest absolute difference between the two copies over the processes of a group, in GB/s.
- **Group**: the processes of one session, one size, one CPU and one level label. For steps with 120 threads: the 4 processes of one setting in one session.
- **Pair value**: the rate of one loop minus the rate of the loop timed next to it, between the same two reference intervals.
- **d**: the difference of two loops inside one process (median of its pair values), in GB/s. **D**: total of old read minus total of new read in one process, in GB/s.
- **Resolved**: the absolute value of the median of a difference is larger than the A/A spread, and the difference has one sign in all processes. **Resolved (+) / resolved (-)**: a resolved difference above 0, or below 0.
- **Comparison, change**: the value of one setting minus the value of a second setting that differs in one factor.
- **Limit of a change**: the sum of the A/A spreads of the two settings. A change is resolved if its absolute value is above its limit and the values of the two settings do not overlap.
- **Spread of a kernel** (step B10): the highest total minus the lowest total of its intervals in one process, in GB/s. It is not the A/A spread.
- **Control** (step B10): the A/A value that a rule uses for a spread, a total or the rate of one mesh.
- **Cell** (step B10): one kernel in one setting. There are 32 cells per session.
- **Position effect**: a rate that depends on which loop ran directly before.

**Levels and patterns**

- **Low / high level**: the two rates of a read loop without adds at 8 MiB with one thread. **Level limits**: below 69 GB/s is low, above 70.5 GB/s is high. The limits are provisional (plan rule 5) [Ref1].
- **Reference interval**: an interval of asm read next to a compared interval. **Stable process**: a process whose reference intervals all have one level label.
- **Case (a)**: at least 10 low and at least 10 high intervals with full coverage on one CPU in one session (handoff B.10, step B4) [Ref2]. **Case (b)**: the same with no huge page.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile in one interval. It has no unit. The percentiles are taken by nearest rank (the 12th and the 108th smallest of 120 rates).
- **Split pattern / uniform pattern**: the two distributions of the thread rates that the plan names for many threads. Split: the slowest thread has about half the rate of the fastest. Uniform: all threads have nearly the same rate.
- **Pattern labels**: split (q below 0.65) and uniform (q above 0.85). They are not used (user decision 2). **Label rule**: a rule of the handoff that needs the pattern labels.
- **Bracket**: the two neighbouring thread counts between which the pattern of a kernel changes. **Bracket rule**: the rule of step B8 that compares the brackets of two kernels.

**Result words**

- **Bounded prediction**: the one measurable statement that a step tests for a hypothesis. A result word applies to this statement only.
- **fail / hold**: the bounded prediction failed, or held, in one session.
- **The five words** (plan rule 11, with the mapping over two sessions that `analyze_bwx.py` codes) [Ref1][Ref17]:
  - **rejected**: the bounded prediction failed in both sessions.
  - **not observed**: an event that the test could have shown did not occur. The script also gives this word when a rule does not find the processes or intervals that it needs.
  - **not resolved**: the difference is inside the A/A spread. The handoff also gives this word when a definition does not fit the data [Ref2]. User decision 2 gives it when a rule needs a pattern label.
  - **not tested**: no step that ran gives the hypothesis a bounded prediction.
  - **not rejected**: every other outcome of two sessions, for the hypotheses that the function `two_sessions` alone maps (H1, H4, H5, H6, H7a, H7b, H9a and the B5 statement). There the prediction did not fail in at least one session. The script has three more rules [Ref17]:
    - H3a: it also writes "not rejected" when the prediction failed in both sessions and no CPU has a case in both sessions.
    - H8: it writes "not resolved" unless both sessions are "supported" or both are "contradicted".
    - A cell of H11: it writes "not resolved" for every outcome other than both sessions "supported", both "contradicted" or both "not observed".
- **supported / contradicted**: the plan's words for steps B8 and H11. The outcome of one cell or bracket in one session agrees with the prediction, or is the opposite. The handoff maps "supported" to "not rejected" and "contradicted" to "rejected", with the plan's word in brackets [Ref2].
- **Strict output** (also "strict word", "strict rule"): the word that the analysis script `analyze_bwx.py` writes into `hypotheses.txt` [Ref6].
- **Second recount**: a recount of every word from the raw csv files by a second agent. Only the lead's record holds it [Ref20].

**Steps** [Ref1][Ref2]. The thread counts of B8, the settings of C3 and the process counts are those that ran. They are in the `env.txt` and csv files of the result folders [Ref10][Ref11][Ref12].

| Step | What runs | Threads, size | Processes per session | Tests |
|---|---|---|---|---|
| A1 | Old, new and asm kernels for read and write, 0.5 s intervals, rows per thread | 64+56, 256 MiB | Part A has 78 in total | screening for H8, H11 |
| A2 | As A1 with 6 s (read) and 15 s (write) intervals | 64+56, 256 MiB | | screening for H7a |
| A3 | Old read with one and with two buffers per thread | 64+56, 256 MiB | | screening for H9a |
| A4 | Old read and asm read at several thread counts | up to 64+56, 256 MiB | | screening for H8 |
| A5 | Asm read, 30 intervals, on CPUs 2 and 41 | 1, 8 MiB | | screening for H2 |
| A6 | Asm read with and without `--no-thp` | 1, 8 MiB | | screening for H3a |
| A7 | Reads the list of counter events | - | - | needed for Part C |
| B1 | New C copy against asm copy, with the A/A pair of asm copy and reference intervals, on CPUs 0, 2, 41, 94 | 1, each of 4, 8, 16, 32 MiB | 64 | H4 |
| B2 | The B1 sequence with new C copy replaced by one of three asm variants | 1, 8 MiB | 48 | H5 |
| B3 | The B1 sequence in the builds `bwx_o0`, `bwx_o36`, `bwx_o52` | 1, 8 MiB | 48 | H6 |
| B4 | Asm read alone, 200 intervals of 0.3 s, page state before each, CPUs 2 and 41, half with `--no-thp` | 1, 8 MiB | 8 | H3a, description for H2 |
| B6 | Old read at 8 MiB and at 1 MiB, with the A/A pair of old read and reference intervals, CPUs 2, 41, 94 | 1, 8 MiB and 1 MiB | 24 | H1 |
| B7 | Old read, new read, asm read twice, in all 8 settings. Also the reproduction condition with one kernel per process | 64+56, 256 MiB | 48 | H7a, H7b for read |
| B8 | Old read and asm read at 64+32 to 64+56 threads in steps of 4 | 64+b, 256 MiB | 14 | H8 |
| B5 | Old read, new read, `read_sparse`, four `nop` variants and asm read twice (the A/A pair). 2 processes run this order and 2 run the reversed order | 64+56, 256 MiB | 4 | the B5 statement |
| B9 | Old read with one and with two buffers per thread | 64+56, 256 MiB | 6 | H9a |
| B10 (B10a, B10b) | Old write, new write, asm write twice, in all 8 settings, with 0.5 s and 15 s intervals. It runs in two halves | 64+56, 256 MiB | 32 | H7a, H7b for write, H11 |
| C1 | As B4 with counters, without `--no-thp` | 1, 8 MiB | 4 | description |
| C2 | As B1 at 8 MiB with counters | 1, 8 MiB | 8 | description |
| C3 | As B7 (2 processes per setting) and as B5 (2 processes), with counters | 64+56, 256 MiB | 18 | description |

## The two questions

The numbers in this section come from the run of 2026-11-13 at 18:12 UTC, which raised the questions [Ref1]. The one exception is the 71.07 GB/s of Q1c. It comes from a second run of that day, at 06:05 UTC [Ref1]. None of these numbers is a result of Parts A, B and C.

- **Q1. Why does the 8 MiB buffer with one thread behave differently from the other buffer sizes?**
  - Q1a. With the best rates of the run, new read was only 0.9 % above old read at 8 MiB. At the other three sizes it was 7.6 % to 99.6 % above.
  - Q1b. With the best rates of the run, new C copy was 2.91 % below asm copy at 8 MiB.
  - Q1c. The same asm read loop gave 71.07 GB/s (best rate) in the run at 06:05 UTC and 67.99 GB/s (best rate) in the run at 18:12 UTC.
- **Q2. Why is old read faster than new read when 120 threads run, each on a 256 MiB buffer?**
  - Q2a. Old read totalled 464.42 to 466.65 GB/s, and new read 279.66 to 304.05 GB/s.
  - Q2b. The write loops gave several separate totals between repetitions (about 117, 124 and 145 GB/s).

## The hypotheses

Statement and bounded prediction of each hypothesis, from the plan [Ref1].

| Label | Question | Statement | Bounded prediction in Parts B and C |
|---|---|---|---|
| H1 | Q1a | Old read is limited inside the core. Its rate at 8 MiB does not depend on the level or on the size. | Step B6: the rate of old read at 8 MiB does not differ by a resolved amount between low and high intervals (part 1). It does not differ by a resolved amount from its rate at 1 MiB (part 2). |
| H2 | Q1c | The low level can change to the high level while the stream runs, and the high level can stay for the next process. | None. Steps B4 and C1 give a description. |
| H3a | Q1c | Huge-page coverage decides the level. | Step B4: every low interval has less than full coverage, and every high interval has full coverage. Case (a) or case (b) is a failure. |
| H3b | Q1c | The physical address of the pages decides the level. | None without step D2. |
| H4 | Q1b | The copy difference does not come from the loop code. | Step B1: inside one process, new C copy minus asm copy at 8 MiB is not resolved. |
| H5 | Q1b | The copy difference comes from the instruction order of the C loop. | Step B2: the asm loop with the C instruction order (`asmcopy_c`) differs from asm copy by a resolved amount of the sign of B1. |
| H6 | Q1b | The copy difference comes from the loop offset (36 against 52). | Step B3: the difference between the two loops changes by a resolved amount when both are at one offset. |
| H7a | Q2a, Q2b | The stop method and the short interval make a part of the difference. | Read, step B7: D changes by a resolved amount between the two stop methods or between the two interval lengths (8 comparisons per session). Write, step B10: the spread of a kernel does so (32 comparisons per session). |
| H7b | Q2a, Q2b | The common start makes a part of the difference. | Read: D changes by a resolved amount between common start and offset start (4 comparisons per session). Write: the spread of a kernel does so (16 comparisons per session). |
| H8 | Q2a | A loop that only loads reaches the uniform pattern at a lower thread count than old read. | Step B8: the bracket of asm read lies wholly below the bracket of old read. |
| H9a | Q2a | The second buffer per thread moved old read to the uniform pattern on 2026-10-30. | Step B9: old read is uniform with two buffers and split with one. |
| H9b | Q2a | The pattern of old read differs between days or sessions. | None. The plan allows only "observed" or "not observed" over the sessions that ran. |
| H10 | Q2a | The memory system fetches lines that the loop does not consume. | None without step D1. Step C3 gives a description. |
| H11 | Q2b | The higher write totals come from the threads of one mesh. | Step B10: in an interval with a higher total, the rate of one mesh is higher by a resolved amount, and the rate of the other mesh is not. |
| B5 statement | Q2a | Vector adds are needed for the split pattern of old read. | Step B5: a loop without vector adds does not show the pattern and total of old read. |

## Result per hypothesis: one table

- The word is one of the five words.
- A word is final only where no item is marked "Open". Five rows without the mark are also not final. Open decision 1 (level limits) can change the words of H4, H5 and H6. Open decision 9 (choice A5) can change the words of H7a for read and of H7a for write.
- "Processes" gives the processes of the step per session.
- All A/A values are in GB/s unless said.

| Hypothesis | Word | Step | Processes s1 / s2 | A/A spread | Basis |
|---|---|---|---|---|---|
| H1 | **rejected**. Open: "not resolved" is the other reading. | B6 | 24 / 24 | Per CPU 2, 41, 94. s1: 0.47, 0.44, 0.82. s2: 1.00, 0.25, 0.95. | s1 fail, s2 fail, through part 2 only (8 MiB against 1 MiB). The difference is a position effect. See H1 below. [Ref6][Ref7] |
| H2 | **not tested** | B4, C1 (description) | 12 / 12 | No A/A pair | The plan gives no bounded prediction in Parts B and C. s1: 0 level changes inside a process. s2: 2. [Ref8] |
| H3a | **not rejected** (strict output). Without the same-CPU condition the script gives **rejected**. Open. | B4 | 8 / 8 | No A/A pair | s1 fail (case (a) on CPU 2). s2 fail (case (a) on CPU 41). No CPU has a case in both sessions. [Ref6][Ref7] |
| H3b | **not tested** | D2, not run | 0 / 0 | - | Part D needs root. [Ref2] |
| H4 | **not observed** | B1 at 8 MiB | 16 / 16. The rule uses 2 / 3. | CPU 2: 0.08 (s1), 0.17 (s2) | Stable processes exist only on CPU 2. The rule needs 2 CPUs with 3 each. The word comes from the level limits. [Ref7] |
| H5 | **not observed** | B2, variant `asmcopy_c` | 16 / 16. The rule uses 3 / 2. | CPU 2: 0.25 (s1), 0.09 (s2) | Same reason as H4. B1 has no resolved sign. [Ref7] |
| H6 | **not observed** | B3 | 48 / 48. The rule uses 8 / 5. | CPU 2: 0.43 to 1.58 (s1), 0.06 to 1.13 (s2) | Same reason as H4. [Ref7][Ref8] |
| H7a, read | **not rejected** | B7 | 48 / 48 (32 with all kernels, 16 with one kernel) | Per setting: 1.49 to 6.64 (s1), 1.35 to 6.31 (s2) | s1 fail (0 of 8 comparisons of stop or interval resolved). s2 hold (3 of 8). [Ref7] |
| H7a, write | **not rejected** | B10 | 32 / 32 | Control of the spread: 4.49 to 26.42 (s1), 3.97 to 42.13 (s2) | s1 hold (1 of 32 comparisons of stop or interval resolved). s2 fail (0 of 32). [Ref7][Ref9] |
| H7b, read | **rejected**. Open: "not resolved" is the other reading. | B7 | 48 / 48 | As H7a, read. Limits of the 8 changes: 4.01 to 13.20. | s1 fail (0 of 4 comparisons of the start resolved). s2 fail (0 of 4). All 8 changes lie inside their limits. [Ref7] |
| H7b, write | **rejected**. Open: "not resolved" is the other reading. | B10 | 32 / 32 | As H7a, write. Limits of the 32 changes: 11.43 to 72.85. | s1 fail (0 of 16 comparisons of the start resolved). s2 fail (0 of 16). All 32 changes lie inside their limits. [Ref7][Ref9] |
| H8 | **not resolved** (user decision 2 [Ref3]. The label rule of the handoff also gives "not resolved", because no bracket formed [Ref2]) | B8 | 14 / 14 | Largest A/A difference of q: 0.052 (no unit) | The bracket rule needs the pattern labels, which are not used. No bracket formed in either session. [Ref6][Ref9] |
| H9a | **not resolved** (user decision 2). Output of the label rule: "rejected". Open. | B9 | 6 / 6 (3 with one buffer, 3 with two) | A/A of the total: 2.47 (s1), 3.27 (s2) | The prediction is worded with the pattern labels. The ranges of q with one and with two buffers overlap in both sessions (0.531 to 0.548 against 0.532 to 0.549 over both sessions, no unit). [Ref6][Ref9] |
| H9b | **not observed**. Open: "not resolved" is the other reading. | B7, B5, B8, B9 | 157 / 157 intervals of old read with one buffer per thread | No A/A pair | The ranges of q overlap between the sessions. This test is a rule that only the Q2 page defines. [Ref9] |
| H10 | **not tested** | D1, not run. C3 is a description. | 18 / 18 with counters | - | No step of Parts B and C tests a bounded prediction of H10. [Ref1][Ref9] |
| H11 | **not resolved**. Per cell and session: "not rejected (supported)" in 2 of 32 cells. | B10 | 32 / 32 | Control of the total: 8.02 to 26.38 (s1), 4.45 to 50.03 (s2) | No cell is supported in both sessions. No cell is "rejected (contradicted)". [Ref6][Ref9] |
| B5 statement | **not rejected** | B5 | 4 / 4 | 6.54 (s1), 8.84 (s2) | Hold in both sessions. Old read minus `read_sparse` is resolved (+) in both. [Ref6][Ref7] |

## State

- Parts A, B and C are complete. Part D was not run [Ref2].
- 78 processes ran in Part A and 326 processes in each session of Parts B and C. No csv file has a `-- killed` or `-- failed` line, and every `stderr.txt` has 0 bytes (counted from the result folders) [Ref10][Ref11][Ref12].
- The long Part A login and the 14 visits of Parts B and C ended with status 0 [Ref13].
- The two builds and the short run ended with exit 0 (`build.out` and `short.out`) [Ref15].
- Insufficient data: the status of the short Part A login. `partA-short.log` has no status line. A log line with the status of that login would give it. Its 20 processes are complete, with no `-- killed` or `-- failed` line and an empty `stderr.txt` [Ref10].
- Insufficient data: the status of the logins that fetched files, and of the extra login of 05:58 (see "Host rules"). No file records them.
- Three result pages exist: Part A, question Q1 (one thread), question Q2 (120 threads) [Ref8][Ref9][Ref10]. The generators of the two pages of Parts B and C have tests [Ref18].
- `bench/bandwidth.c` and `plan.md` have the sha256 values that the handoff names [Ref2]. So both files are unchanged.
- The report `crb-memory-hierarchy.html` was not changed (lead's record) [Ref20].

## What was run

All times are UTC.

- A start time is the time in the name of the first result folder (clock of CRB). The start time of a build is the first line of its `build.txt` (clock of CRB) [Ref15].
- The end time of a visit of Parts B and C, and of the long Part A login, is the line `ssh status` of its log (clock of the development machine) [Ref13].
- The end time of the short Part A login, of the builds and of the short run is the end line of `env.txt` or `build.txt` (clock of CRB) [Ref10][Ref15][Ref16].

| Visit | Steps | Start | End | Processes | Status |
|---|---|---|---|---|---|
| Part A, short | A7, A5, A6 | 11-13 20:49:39 | 20:50:47 | 20 | not recorded |
| Part A, long | A1, A2, A3, A4 | 11-13 20:50:55 | 21:07:34 | 58 | 0 |
| First build of `bwx` | 4 binaries, 4 self-tests | 11-13 21:42:39 | 21:42:41 | - | exit 0, `failures=0` in all 4. The acceptance test failed: the C copy loop of `bwx_o52` was at offset 0, not 52. This build was not used. |
| Second build of `bwx` | 4 binaries, 4 self-tests | 11-13 21:43:35 | 21:43:38 | - | exit 0, `failures=0` in all 4. See lead's change 1 for the acceptance test. |
| Short run | every sequence with 0.1 s intervals | 11-13 21:43:38 | 21:45:03 | 32 | exit 0, no process killed or failed |
| s1, visit 1 | B7 | 11-13 23:28:59 | 23:59:04 | 48 | 0 |
| s1, visit 2 | B10a | 11-13 23:59:19 | 00:33:50 | 16 | 0 |
| s1, visit 3 | B10b | 11-14 00:33:59 | 01:08:29 | 16 | 0 |
| s1, visit 4 | B8, B5, B9 | 11-14 01:08:39 | 01:23:01 | 14, 4, 6 | 0 |
| s1, visit 5 | B1, B4, B6 | 11-14 01:23:15 | 01:54:50 | 64, 8, 24 | 0 |
| s1, visit 6 | B2, B3, C1, C2 | 11-14 01:55:17 | 02:27:08 | 48, 48, 4, 8 | 0 |
| s1, visit 7 | C3 | 11-14 02:27:08 | 02:43:38 | 18 | 0 |
| s2, visit 1 | B7 | 11-14 02:43:52 | 03:13:56 | 48 | 0 |
| s2, visit 2 | B10a | 11-14 03:13:57 | 03:48:55 | 16 | 0 |
| s2, visit 3 | B10b | 11-14 03:48:55 | 04:23:30 | 16 | 0 |
| s2, visit 4 | B8, B5, B9 | 11-14 04:23:31 | 04:37:51 | 14, 4, 6 | 0 |
| s2, visit 5 | B1, B4, B6 | 11-14 04:37:52 | 05:09:25 | 64, 8, 24 | 0 |
| s2, visit 6 | B2, B3, C1, C2 | 11-14 05:09:25 | 05:41:16 | 48, 48, 4, 8 | 0 |
| s2, visit 7 | C3 | 11-14 05:41:16 | 05:57:44 | 18 | 0 |

- **Stopped steps: none.** The run script ends with status 3 after a marker file, 4 after the stop time `STOP_AT`, 5 after our own stop file, and 130 after an interruption [Ref2]. None of the 15 logins with a recorded status (the long Part A login and the 14 visits of Parts B and C) ended with one of these [Ref13]. The short Part A login has no recorded status. Its `env.txt` holds the end line, and its csv files have no `-- killed` line [Ref10]. The script `run_partA.sh` writes the end line only after its last step [Ref19].
- **Repeated: the build, once** (see lead's change 1). No step of Parts A, B and C was repeated.
- Each step of s2 started 3 h 14 min to 3 h 15 min after the same step of s1. Session s2 started 14 s after session s1 ended, and the machine was not restarted between them [Ref9].
- `bwx` was built with gcc 14.2.0. The sha256 of `bwx` is `5b702073...d826f1` [Ref15]. `visit.sh` passes this value to the run script. The run script compares it with the binary before its first launch, and stops with status 2 when they differ [Ref14][Ref19]. The `env.txt` of each of the 28 step folders of Parts B and C records this digest for `bwx` [Ref11][Ref12].

**System load.** The two run scripts (`run_partA.sh` for Part A, `run_bwx.sh` for Parts B and C) read the load directly before every launch [Ref19].

| Reading | Part A (78 launches) | s1 (326 launches) | s2 (326 launches) |
|---|---|---|---|
| Logged-in users | 0 at every launch | 0 at every launch | 0 at every launch |
| Runnable tasks (one is the script itself) | at most 2 | at most 2 | at most 2 |
| Launches that waited for an idle system | 0 | 1 (2 s, step B1) | 0 |
| 1-minute load average, one-thread steps | 0.00 to 0.66 | 0.86 to 90.41 (highest at the first launch of B1, 14 s after B9 with 120 threads) | 0.90 to 116.25 (highest at the first launch of B1, 1 s after B9) |
| 1-minute load average, steps with 120 threads | 0.64 to 120.26 | 0.00 to 121.27 | 1.00 to 121.09 |

- The 1-minute load average covers about the last minute. A high value follows directly after one of our own processes with up to 120 threads [Ref8][Ref9].
- One process of another account was above 10 % of one CPU at 1 of 652 launches (1 of the 244 launches of the steps with 120 threads, and 0 of the 408 launches of the one-thread steps). It was `check-new-relea` of root at 90.9 %, at the first launch of C3 in s2 [Ref8][Ref9].
  - The tool ps cuts a name to 15 characters. The full name `check-new-release` is a reading of the Q2 page, not a recorded value.
  - ps divides the CPU time of a process by the time since its start. So a process that has just started can show a high value.
- Insufficient data: the load while an interval ran. A reading of the runnable tasks of each account during an interval would give it.

**Host rules.** The lead's record holds the three points below [Ref20]. The result files hold two parts of the second point, and no other part of the three points. The setting `STOP_AT=none` of Parts B and C and of the short run is in the settings line of `env.txt` in each of the 28 step folders and in the folder of the short run [Ref11][Ref12][Ref16]. No login with a recorded status ended with status 3, the status after a marker file [Ref13].

- The Slack channel #phoenix-crb was read before every login and about every 10 min during every run.
- The only block message of the last 24 h was the block of 2026-11-13 15:30 to 18:10, which had ended. The stop time was set to none (`STOP_AT=none`). The marker file never appeared.
- One error: at 05:58 on 2026-11-14 the lead made one extra login that ran only `true` without the marker-file check. The cause was a typing error in a fetch command. The channel showed no block at that time.

## Result per hypothesis

Each block gives the prediction, the measurement and the word. The order is the order of the table above.

### Question Q1: one thread, 8 MiB

**H1 (old read is limited inside the core, and its rate at 8 MiB does not depend on the level or on the size). Step B6.**

- Predicted: no resolved difference of old read at 8 MiB between low and high intervals (part 1), and none against old read at 1 MiB (part 2).
- Measured, part 1: "not observed" in both sessions. No CPU had a stable high process [Ref7].
- Measured, part 2: resolved (-) on 3 of 3 CPUs in both sessions, with 8 processes per CPU. Median d per CPU is -1.71 to -1.10 GB/s in s1 (A/A spread 0.44 to 0.82 GB/s). It is -2.67 to -1.91 GB/s in s2 (A/A spread 0.25 to 1.00 GB/s) [Ref7].
- Word: "rejected" (strict word). The bounded prediction failed in both sessions. The second recount gives the same word (lead's record) [Ref20].
- Limit of the word: the difference depends on which loop ran directly before [Ref8][Ref21].
  - After an asm read interval, the pair value of old read at 8 MiB per CPU is -4.18 to -3.44 GB/s in s1 and -5.54 to -4.45 GB/s in s2.
  - After an interval of old read at 1 MiB, it is -0.10 to -0.06 GB/s in s1 and -0.11 to -0.07 GB/s in s2. That is inside every A/A spread.
  - In 192 of 192 A/A pairs of each session, the first of two old read intervals after an asm read interval is the slower one.
  - Old read at 1 MiB shows 0.00 GB/s between the two positions.
- So these data do not show that the rate of old read depends on the buffer size. They show that old read at 8 MiB is slower in the 0.3 s interval after an asm read interval.
- Hypothesis (not tested): the loop that ran before leaves a state in the cache or in the prefetcher. A counter run of the B6 sequence would test it.
- Open for the user: "rejected" (strict rule) or "not resolved". The reason for "not resolved" is that the pair definition does not fit the data (last paragraph of handoff B.10) [Ref2].

**H2 (the low level can change to the high level while the stream runs). Steps B4 and C1, description only.**

- Predicted: nothing. No row of Parts B and C gives H2 a bounded prediction [Ref1].
- Word: "not tested".
- Measured, s1: 0 changes between low and high inside a process, in 12 processes [Ref8][Ref21].
  - Two processes were high in all 200 intervals: `thp-cpu2-p2` (CPU 2, 70.55 to 71.12 GB/s) and `thp-cpu41-p2` (CPU 41, 71.06 to 71.79 GB/s).
  - A third, `thp-cpu41-p1`, was high in 199 of 200 intervals after a first interval at 69.59 GB/s. That first interval is between the two limits.
- Measured, s2: 2 changes in 12 processes, both in B4 on CPU 41 with full coverage. One process went from low (68.60 GB/s) to high (71.41 GB/s) after its first interval. One was high in its first 17 intervals (71.56 GB/s in the 17th), then between the two limits for 7 intervals, and first low in its 25th interval (68.93 GB/s) [Ref8].
- The second half of H2 (the high level can stay for the next process) has no test. Each process allocates a new buffer.

**H3a (huge-page coverage decides the level). Step B4.**

- Predicted: every low interval has less than full coverage, and every high interval has full coverage [Ref1]. The rule of the handoff counts a failure only as case (a) or case (b): at least 10 low and at least 10 high intervals on one CPU in one session, all with full coverage (a) or all with no huge page (b) [Ref2].
- Measured, s1, CPU 2: 200 low and 200 high intervals with full coverage. This is case (a). The two levels are in two different processes [Ref7][Ref8].
- Measured, s2, CPU 41: 176 low and 216 high intervals with full coverage. This is case (a) [Ref7][Ref8].
  - Both processes with huge pages hold both labels. `thp-cpu41-p1` has 1 low and 199 high intervals. `thp-cpu41-p2` has 17 high, 8 between the limits and 175 low intervals [Ref21].
  - Only `thp-cpu41-p2` has at least 10 of each.
- Case (b) occurred nowhere. No interval without huge pages was high [Ref7].
- Word, strict output: "not rejected". The handoff asks for a case "on one CPU in both sessions" [Ref2]. The script reads this as the same CPU (analysis choice A13 in the table below) [Ref5][Ref6].
- Word, second reading: "rejected". Step B4 of the plan has no same-CPU condition, and the prediction failed in each session. The script prints this word as `word_without_the_same_cpu_condition` [Ref6].
- A second limit: 175 of the 176 low intervals of s2 lie less than 0.2 GB/s below the limit of 69 GB/s. If that case is not counted, the word is "not rejected" under both readings [Ref8].
- Open for the user: which reading applies. No reading gives "not observed".

**H3b (the physical address of the pages decides the level).**

- Word: "not tested". Step D2 was not run.
- Description: in s2 the 2 level changes had equal coverage before and after [Ref8].
- The counts `thp_collapse_alloc` and `pgmigrate_success` did not rise at these 2 changes [Ref8].
- The plan calls this "no sign of a page change". It does not prove that the pages stayed the same [Ref1].

**H4 (the copy difference does not come from the loop code). Step B1 at 8 MiB.**

- Predicted: new C copy minus asm copy at 8 MiB is not resolved inside one process.
- Word, strict: "not observed" for the label low and for the label high, in both sessions [Ref6].
- Measured by the rule: stable low processes exist on CPU 2 only, 2 of 4 in s1 and 3 of 4 in s2. Stable high processes: 0. The rule needs 2 CPUs with 3 stable processes each [Ref7].
- On CPU 2 alone, s2 gives resolved (-), median d -1.50 GB/s over 3 processes against an A/A spread of 0.17 GB/s [Ref7].
- Description without labels, no decision (4 processes per CPU) [Ref8][Ref21]:
  - s1: d is below 0 in 16 of 16 processes. The median d per CPU is -2.61 to -1.32 GB/s. The A/A spread per CPU is 0.19 to 2.60 GB/s.
  - s2: d is below 0 in 15 of 16 processes. The median d per CPU is -1.74 to -1.18 GB/s. The A/A spread per CPU is 0.15 to 1.52 GB/s.
  - The median d per CPU is 2.1 to 4.5 % of the rate of asm copy.
- The rule for a size without level, applied to 8 MiB as a description, gives "not resolved" in both sessions (3 of 4 CPUs resolved in s1, 2 of 4 in s2) [Ref8].
- At 4, 16 and 32 MiB the difference is resolved (-) on 4 of 4 CPUs in both sessions. H4 predicts 8 MiB only [Ref7].

**H5 (instruction order) and H6 (loop offset). Steps B2 and B3.**

- Predicted, H5: `asmcopy_c` differs from asm copy by a resolved amount of the sign of B1. Predicted, H6: the copy difference changes by a resolved amount when both loops are at one offset.
- Word, strict: "not observed" for both, in both sessions. The reason is the same as for H4, and B1 has no resolved sign to compare with [Ref6].
- The plan runs B2 and B3 only after a resolved difference in B1. They were run anyway. The data then exist for a later change of the limits (lead's change 3).
- Description, no decision: median d per CPU against asm copy, with the A/A spread per CPU in brackets, in GB/s. Each cell has 16 processes, 4 per CPU [Ref8][Ref21].

| Loop | s1: median d (A/A spread) | s2: median d (A/A spread) |
|---|---|---|
| `asmcopy_c` (assembly with the C instruction order) | -1.78 to -1.07 (0.20 to 0.42) | -1.60 to -1.36 (0.18 to 0.80) |
| `asmcopy_c_add` (the two `add` instructions moved) | -2.16 to -1.50 (0.24 to 0.46) | -2.15 to -1.65 (0.17 to 0.75) |
| `asmcopy_c_reg` (registers q0 to q15, as asm copy) | +0.13 to +0.29 (0.11 to 0.59) | +0.13 to +0.59 (0.33 to 0.51) |
| Both loops at offset 0 (`bwx_o0`) | -2.41 to -1.08 (0.21 to 1.43) | -1.77 to -1.10 (0.16 to 1.44) |
| Both loops at offset 36 (`bwx_o36`) | -2.10 to -1.04 (0.17 to 0.43) | -1.76 to -1.00 (0.21 to 0.64) |
| Both loops at offset 52 (`bwx_o52`) | -1.75 to +0.67 (0.14 to 2.06) | -1.65 to -0.02 (0.39 to 1.74) |

### Question Q2: 64+56 threads, 256 MiB per thread

**H7a and H7b for read. Step B7.**

- Predicted, H7a: D changes by a resolved amount between the two stop methods, or between the two interval lengths. Predicted, H7b: D changes by a resolved amount between the two starts.
- Measured: D is resolved (+) in 16 of 16 settings, with 4 processes per setting [Ref7][Ref21].
  - s1: the median D of a setting is 158.06 to 167.50 GB/s. That is 33.8 to 35.6 % of the old read total of the same processes.
  - s2: the median D of a setting is 161.51 to 178.72 GB/s. That is 34.5 to 37.9 % of the old read total.
- Change of D between two settings that differ in one factor, with the limit of the change in brackets, in GB/s. Each cell holds the 4 comparisons of one factor, with 4 and 4 processes. "R" marks a resolved change [Ref7]:

| Factor (first minus second) | s1 | s2 |
|---|---|---|
| Interval, 0.5 s minus 6 s | -1.96 (8.28), +0.85 (8.93), -1.62 (3.93), -7.45 (10.21) | -16.15 (9.61) R, -10.43 (7.77) R, -10.66 (8.03), -8.01 (7.13) |
| Stop, whole passes minus common stop | -6.41 (8.13), -7.42 (12.92), -6.75 (4.08), +0.87 (6.22) | +0.80 (10.28), -4.76 (11.62), -4.69 (7.35), -7.18 (3.28) R |
| Start, common minus offset | +0.06 (13.20), +2.86 (4.01), +1.07 (7.85), -4.76 (6.29) | -6.78 (12.14), -1.06 (5.23), -1.22 (9.76), +1.43 (5.40) |

- A change above its limit is still "not resolved" when the D values of the two settings overlap (for example -6.75 GB/s against a limit of 4.08 GB/s in s1).
- Word, H7a: "not rejected". The 3 resolved changes make D larger with the 6 s interval (2) and with the common stop (1). The largest is 9.5 % of the median D of s2 [Ref9].
- Word, H7b: "rejected", for the bounded prediction only. A start contribution below the limits (up to 8.0 % of the median D) is not excluded [Ref9].
- Open for the user: rule 11 gives two words for "every change is inside its limit". The script chose "rejected". The plan's phrase for this outcome is "no resolved contribution" [Ref1].

**H7a and H7b for write. Step B10.**

- Predicted, H7a: the spread of a kernel changes by a resolved amount between the two stop methods, or between the two interval lengths. Predicted, H7b: it does so between the two starts.
- Word, H7a: "not rejected". One of 64 comparisons is resolved (1 of 32 in s1, 0 of 32 in s2). It is asm write in s1, whole passes minus common stop at 0.5 s with offset start: +26.41 GB/s against a limit of 12.20 GB/s [Ref7].
- The second copy of the same loop does not repeat it (+20.55 GB/s, not resolved). Session s2 does not repeat it. No correction for the 64 comparisons was made [Ref9].
- Word, H7b: "rejected", for the bounded prediction only [Ref7].
  - s1: the 16 start changes of the spread are -20.74 to +6.65 GB/s. Their limits are 15.32 to 41.00 GB/s.
  - s2: the 16 start changes are -7.28 to +6.76 GB/s. Their limits are 11.43 to 72.85 GB/s.
- So the test can show only a start effect that is larger than its limit. A smaller start effect is not excluded.
- Open for the user, as for read.

**H8 (a loop that only loads reaches the uniform pattern at a lower thread count). Step B8.**

- Predicted: the bracket of asm read lies wholly below the bracket of old read.
- Word: "not resolved". The bracket rule needs the pattern labels [Ref3].
- Measured without labels, both sessions together: at 64+32 threads q is 0.645 to 0.689 for asm read and 0.656 to 0.800 for old read. At 64+56 threads q is 0.862 to 0.920 for asm read and 0.535 to 0.561 for old read [Ref9].
- From one count of mesh-1 threads to the next, the median q of asm read rises 5 times and falls 1 time. This holds in s1 and in s2 [Ref9].
- The median q of old read rises 3 times and falls 3 times, in s1 and in s2 [Ref9].

**H9a (the second buffer per thread moved old read to the uniform pattern). Step B9.**

- Predicted: old read is uniform with two buffers and split with one.
- Measured, s1: q of old read is 0.534 to 0.547 with one buffer and 0.536 to 0.549 with two, in 9 intervals each [Ref9].
- Measured, s2: q of old read is 0.531 to 0.548 with one buffer and 0.532 to 0.546 with two, in 9 intervals each [Ref9].
- The median thread rate is 4.93 to 5.04 GB/s on mesh 0 and 2.71 to 2.76 GB/s on mesh 1 in all 36 intervals [Ref9].
- Total with one buffer minus total with two (3 processes of each kind): +3.20 GB/s in s1 (A/A value 2.47 GB/s, resolved) and -0.07 GB/s in s2 (A/A value 3.27 GB/s, not resolved) [Ref7].
- Word: the strict output of the label rule is "rejected". Under user decision 2 the word is "not resolved" [Ref3][Ref6].
- Open for the user: confirm "not resolved", or accept q as the measure of the pattern for this step. The ranges of q with one and with two buffers overlap in both sessions. If the user accepts that as the same pattern, the plan names that outcome "rejected" [Ref1]. The uniform distribution that H9a predicts was not seen.

**H9b (the pattern of old read differs between days or sessions).**

- Predicted: nothing. The plan allows only "observed" or "not observed" [Ref1].
- Measured, old read at 64+56 threads with one buffer per thread, 157 intervals per session [Ref9]. The raw files give B7 140, B5 4, B8 4 and B9 9 intervals per session [Ref11][Ref12]. The page generator leaves out the 9 intervals of B9 with two buffers per thread [Ref18]. The ranges:
  - s1: q is 0.528 to 0.607, and the total is 464.01 to 472.94 GB/s.
  - s2: q is 0.522 to 0.583, and the total is 462.76 to 472.84 GB/s.
- No interval has a total at or below 368.25 GB/s, the highest total of the run of 2026-10-30 [Ref9].
- Word: "not observed". It covers two sessions that ran one after the other in one night.
- The test (overlapping ranges of q) is a rule that only the Q2 page defines. The user has not approved it. Under user decision 2 the word would be "not resolved". Open for the user.

**H10 (the memory system fetches lines that the loop does not consume).**

- Word: "not tested". Step D1 was not run.
- Description from C3: L2 refills per 64 B line are 1.0001 to 1.0004 for old read and new read on both meshes [Ref9].
  - One L2 refill per line means that the core fetched each line about once. The plan reads equal refills per line as "the core side shows no extra fetches" [Ref1].
  - H10 could still hold for traffic that these events do not count [Ref1].
- Last-level read misses per line are 0.0812 to 0.0848 for old read (about 1 per 12 lines) and 0.0994 to 0.1045 for new read (about 1 per 10 lines) [Ref9]. No rule of the plan decides on this difference.

**H11 (the higher write totals come from the threads of one mesh). Step B10.**

- Predicted: in a process, the mesh rate of exactly one mesh is higher in the interval with the highest total than in the interval with the lowest total, by more than its control.
- Measured, s1: 2 cells "supported", 30 "not observed". Measured, s2: 2 "supported", 3 "not resolved", 27 "not observed" [Ref7].
- The 4 supported cells are [Ref6]:
  - s1: old write and asm write at whole passes, 0.5 s, offset start.
  - s2: old write at common stop, 15 s, common start.
  - s2: old write at whole passes, 15 s, offset start.
- No cell is supported in both sessions. In s1 the mesh that rose is mesh 0 in the old write cell and mesh 1 in the asm write cell [Ref9].
- Word: "not resolved", over both sessions. Higher totals occurred in both sessions. So "not observed" does not apply.

**Statement of B5 (vector adds are needed for the split pattern of old read).**

- Predicted: `read_sparse` does not show the pattern and total of old read.
- Word: "not rejected". No label is needed.
- Measured: old read minus `read_sparse` is +156.64 GB/s in s1 (4 processes, A/A spread 6.54 GB/s) and +166.21 GB/s in s2 (4 processes, A/A spread 8.84 GB/s). Both are resolved [Ref7].
- q is 0.874 to 0.910 for `read_sparse` and 0.539 to 0.557 for old read in s1. It is 0.883 to 0.912 and 0.541 to 0.544 in s2 [Ref9].
- Limit: the loop of `read_sparse` is at offset 4. The loops of asm read and of the four `nop` variants are at offset 20, and the loop of old read is at offset 40 [Ref4][Ref15].

## Answers to the expected results

The plan lists these points in its section "Results expected at the end" [Ref1].

**Q1a. Is the rate of old read at 8 MiB independent of the level (H1)?**

- Insufficient data. No stable high process occurred in B6, so old read was never compared between the two levels [Ref7].
- What would give it: a B6 session in which one CPU has at least 2 stable low and 2 stable high processes, or new level limits.
- The second part of H1 (8 MiB against 1 MiB) is resolved by the rule, and the difference is a position effect (see H1).
- The cause of the rate of old read itself stays open, as the plan expected.

**Q1b. Does a resolved difference between new C copy and asm copy exist inside one process at the original loop offsets?**

- By the rule of the handoff: "not observed" at 8 MiB [Ref6]. So the answer is not "yes". The answer is also not "not reproduced".
- Description without labels, 4 processes per CPU [Ref8][Ref21]:
  - s1: new C copy is slower in 16 of 16 processes, by 1.32 to 2.61 GB/s (median per CPU, A/A spread per CPU 0.19 to 2.60 GB/s).
  - s2: new C copy is slower in 15 of 16 processes, by 1.18 to 1.74 GB/s (A/A spread per CPU 0.15 to 1.52 GB/s).
- Which single change removes it: not decided. As a description, only the variant with the registers of asm copy (`asmcopy_c_reg`) has no negative median d (+0.13 to +0.29 GB/s in s1, +0.13 to +0.59 GB/s in s2) [Ref8].
- At 4, 16 and 32 MiB the difference is resolved (-) in both sessions. Median d per CPU, with the A/A spread per CPU in brackets, 4 processes per CPU [Ref7]:

| Size | s1, GB/s | s2, GB/s |
|---|---|---|
| 4 MiB | -6.59 to -4.60 (0.20 to 1.17) | -5.38 to -4.54 (0.12 to 0.47) |
| 16 MiB | -1.03 to -0.61 (0.29 to 0.47) | -1.29 to -0.82 (0.06 to 0.74) |
| 32 MiB | -0.75 to -0.44 (0.10 to 0.22) | -0.83 to -0.42 (0.05 to 0.21) |

- What would decide 8 MiB: the user's decision on the level limits. The analysis is then rerun on the same files. No new measurement is needed.

**Q1c. The sequence of levels, with coverage and counters.**

- Sequence and coverage: B4 gives 200 intervals for each of 8 processes per session, with the coverage before every interval. The charts are on the Q1 page [Ref8].
- With full coverage in every interval, the process medians are 67.29 to 71.73 GB/s in s1 and 67.26 to 71.56 GB/s in s2. With no huge page they are 69.07 to 69.69 GB/s in s1 and 67.50 to 69.82 GB/s in s2 [Ref8].
- So both levels occurred with full coverage (case (a) in each session, on different CPUs).
- Counters at the low level, long run (C1, 200 intervals per process): 2.7506 instructions, 0.3664 to 0.3706 L1 refills and 0.8213 to 0.8254 L2 refills per 64 B line. The core clock is 2.7998 GHz. These are the medians of the 4 groups of low intervals [Ref7].
- Counters at the high level: C1 has none. No interval of C1 was above 70.5 GB/s in either session (highest 70.01 GB/s in s1 and 69.10 GB/s in s2) [Ref21].
- C2 has counters at the high level for reference intervals of asm read that stand between copy intervals (0.3 s each, the same interval length as in C1) [Ref7][Ref21]:
  - s1: 21 intervals above 70.5 GB/s, up to 70.76 GB/s. Medians per 64 B line: 2.7506 instructions, 0.2630 L1 refills, 0.8205 L2 refills.
  - s2: 30 intervals above 70.5 GB/s, up to 70.76 GB/s. Medians: 2.7506 instructions, 0.2579 L1 refills, 0.8195 L2 refills.
  - Low intervals of the same C2 files: 78 in s1 (0.2699 L1 refills, 0.8231 L2 refills) and 77 in s2 (0.2663 and 0.8233).
  - The median core clock is 2.7998 GHz in each of these 4 groups (single intervals: 2.7997 to 2.7999 GHz).
  - The L1 refills of C2 (0.26 to 0.27 per line) differ from those of C1 (0.37 per line) at the same level. So levels are compared inside one step only.
- Insufficient data: counters at 71 GB/s and above, the level that B4 showed, and counters in a long run at the high level. A C1 process that reaches the high level would give both.
- H3b stays "not tested".

**Q2a. Is the read difference reproduced, and what does each timing factor change?**

- Reproduced: yes, in both sessions. Under the reproduction condition, with all kernels in one process, D is +159.13 GB/s (A/A spread 1.49 GB/s) in s1 and +162.31 GB/s (A/A spread 3.98 GB/s) in s2. Each value has 4 processes [Ref7].
- With one kernel per process D is +158.12 GB/s (A/A value 4.35 GB/s) in s1 and +162.39 GB/s (A/A value 7.11 GB/s) in s2. Each kernel has 4 processes [Ref7].
- Change per factor: see the table under H7a. Three of 24 comparisons are resolved, all in s2. The start has no resolved contribution. No setting removes D.
- Per mesh, description, over the 8 settings with 4 processes each [Ref7]:
  - s1: D of mesh 0 is 132.07 to 148.50 GB/s (A/A spread 1.40 to 9.62 GB/s). D of mesh 1 is 16.79 to 25.56 GB/s (A/A spread 0.38 to 5.29 GB/s).
  - s2: D of mesh 0 is 140.88 to 156.95 GB/s (A/A spread 2.24 to 6.26 GB/s). D of mesh 1 is 18.32 to 22.65 GB/s (A/A spread 0.09 to 2.93 GB/s).
- Per thread, description: the median thread of old read is faster than that of new read by 2.28 GB/s in s1 and by 2.40 GB/s in s2 on mesh 0. On mesh 1 it is faster by 0.36 GB/s in both sessions [Ref9].
- Are vector adds needed for the pattern of old read? The statement is "not rejected". A loop with the same instruction count and no add does not show the total of old read.
- A `nop` does not use the same resources as a vector add. So this test does not identify the cause [Ref1].
- The cause inside the chip stays a hypothesis. Part D was not run.
- Limit: in each of the two 0.5 s settings of B7 with whole passes, 64 of 64 intervals fail the 2 % check, in both sessions. One of the two is the reproduction condition. With one kernel per process, 48 of 48 intervals of the reproduction condition fail it in each session [Ref9].

**Q2b. Do the separate write totals remain with the common stop and a long interval, and do the higher totals come from one mesh?**

- Insufficient data for "separate levels remain". The plan and the handoff set no rule for when two totals are separate levels. A rule on the gap between totals, set before the data are read, would give it [Ref9].
- Description: the largest gap between two neighbouring totals of a kernel is above the control of the total in 6 of 8 settings in s1 and in 4 of 8 in s2 [Ref9].
- With the common stop and 15 s, that holds in 1 of 2 settings in s1 (asm write 2) and in 2 of 2 in s2 (new write, old write) [Ref9].
- H7a for write: "not rejected", through 1 of 64 comparisons.
- H11: "not resolved". One mesh rose alone in 2 of 32 cells per session, and never in the same cell in both sessions. Per-mesh rows for the highest and the lowest interval of every process are on the Q2 page [Ref9].
- The median total over the four write kernels of a setting is 117.5 to 125.5 GB/s in s1 and 117.5 to 125.6 GB/s in s2. Old write alone is 126.2 to 144.8 GB/s in s1 and 126.3 to 143.4 GB/s in s2 [Ref9].

**Pages and handoff.**

- The plan asks for one page per part [Ref1].
- Delivered: one page for Part A, and two pages for Parts B and C together (one per question), plus this file.

## Changes to specification v1

### Changes of the lead

The lead made 11 changes to specification v1. Only the lead's record holds them, except where a file is cited [Ref20].

1. `bwx_o52` is built with `-falign-loops=1`. Without it gcc moved the C copy loop from offset 52 to 0. That first build failed the acceptance test and was not used [Ref15][Ref21].
   - Side effect of the option: `oldwrite` of `bwx_o52` differs outside the loop from `bw_old`. No B3 sequence uses it.
   - With the second build, `check_listing.py` reports 83 of 84 rows ok and ends with status 1. The failed row is `oldwrite` of `bwx_o52` (code outside the loop). The planned offsets of all 4 binaries pass [Ref21].
   - So the acceptance test of handoff B.7 passes for the loops and the offsets, and the check script, which is stricter, does not pass [Ref2][Ref4].
2. `check_listing.py` no longer compares addresses outside a function (`adrp`, `bl`). They depend on the link layout.
3. B2, B3 and C2 were run although the rule gives no resolved difference for B1 at 8 MiB. The word of the rule is "not observed" [Ref6].
4. B8 used the counts 64+32 to 64+56 in steps of 4. Part A gave no bracket, because the labels are not used [Ref10].
5. B8, B5, B9 and the B5 sequence of C3 used common stop, 6 s, common start. This setting was chosen from B7 of s1 (median D 167.50 GB/s). Session s2 reused it [Ref7][Ref14].
   - The handoff rule, applied to B7 of s2 itself, chooses the offset start (178.72 against 177.66 GB/s).
   - The two settings differ by 1.06 GB/s in their median D. That is inside the limit of 5.23 GB/s. Steps B8, B5 and B9 did not run with the offset start. So no file shows whether a result word of these steps depends on the choice.
6. C3 repeated all 8 B7 settings, 2 processes each, plus the B5 sequence.
7. One result folder `partBC-20261114` holds both pages and the scripts, in place of one page per visit.
8. The short run was checked by an independent agent before Part B (lead's record) [Ref20]. The raw files of the short run are in its folder [Ref16].
9. Part C of s1 ran before s2 of Part B.
10. The review of `bwx` was done by 4 reviewer agents (18 findings, 13 fixed), not by the file-based review loop. The user accepted this (user decision 1) [Ref3]. Insufficient data: what happened to the other 5 findings. The lead's record does not say it, and a saved review record would give it.
11. Session s2 started 14 s after session s1 ended. The handoff says "Session 2 some hours later" [Ref2]. Each step of s2 started 3 h 14 min to 3 h 15 min after the same step of s1 [Ref9].

### Changes in `bwx` (24 points and 3 known limits)

`DEVIATIONS-bwx.md` lists 24 changes and 3 known limits [Ref4].

| No | Change |
|---|---|
| 1 | The pad before a function uses `.pushsection`, `.p2align 6`, `.fill`, `.popsection`, not `.text` and `.skip`. |
| 2 | One macro `PAD_<name>` per kernel. The build can set `HEAD_<name>` or `PAD_<name>`. |
| 3 | Kernels without a planned offset get the function start they have in `bw_new` or `bw_old`. |
| 4 | Step B3 is three more binaries, not six more functions. |
| 5 | The asm kernels are macro bodies, so an A/A copy is the same source. |
| 6 | The three `asmcopy_c*` kernels bind their pointers to x0, x1, x2. |
| 7 | The loop end of the three `asmcopy_c*` kernels is that of the C loop (`cmp`, `b.hi`). |
| 8 | Kernels are called through a table of function pointers. |
| 9 | On a target that is not AArch64, plain C loops replace the kernels and the output says "STAND-IN". |
| 10 | `--seq` is required. New options `--list` and `--selftest`. |
| 11 | Added comment lines with the options and the column names. `round` and `pos` count from 0. The first page reading of a process with more than one thread has `pos` -1. |
| 12 | Added line `# page_read` with the time of each page reading. |
| 13 | Row order: P, I, T, C with one thread. I, T, C, P with more threads. |
| 14 | The write value is `v` plus the chunk number with the common stop. |
| 15 | Start offset for entry sizes that B.5 does not cover: size divided by 2 MiB, rounded down. |
| 16 | The buffer length is `--bytes` rounded up to 2 MiB, and `kB_total` is that length. |
| 17 | After an `mprotect` failure the program continues and prints `NA` in the P rows. |
| 18 | No event code is built in. `--count` needs `--pmu-type` and `--events`, or two environment variables. |
| 19 | Order of the readings: counters, CPU time, clock at the start, and the reverse at the end. |
| 20 | The self-test is a mode of `bwx`, with added fault checks for every read kernel. |
| 21 | One more barrier after each page reading, so that no warm-up pass starts before the reading. |
| 22 | `bwx` removes CPUs above 119 from its allowed set and rejects them in `--cpus`. |
| 23 | Bad numbers on the command line end the program with status 2. |
| 24 | `build.sh` has `EXTRA_<binary>` for options of one build. |
| Smaller points | `build.sh` runs under `taskset -c 0-119`. It has `BWX_CPUS`, which changes that CPU list. It has `BWX_MARKER`, which replaces the marker path and exists only to test the marker check. `check_listing.py` requires all four binaries. |
| Limit | With 120 threads the main thread shares a CPU with a worker. Insufficient data on the size of this effect on CRB. A run with the main thread on a spare CPU would give it. The host rules allow CPUs 0 to 119 only, so no spare CPU exists. |
| Limit | The loop of `read_sparse` is at offset 4. The loops of asm read, of its A/A copy and of the four `nop` variants are at offset 20. The loop of new read is at offset 36 and the loop of old read is at offset 40 (measured in `offsets.tsv`) [Ref15]. |
| Limit | `check_listing.py` checks more than B.7 asks. For the 8 kernels that have no reference listing of the whole function (`asmcopy_c`, `asmcopy_c_add`, `asmcopy_c_reg`, the four `nop` variants, `read_sparse`) it checks outside the loop only two points: the function has one backward branch, and d8 to d15 are saved and restored where the kernel uses them. `DEVIATIONS-bwx.md` counts these as five kernels, with the four `nop` variants as one [Ref4]. |

`DEVIATIONS-bwx.md` also lists 12 checks that only a build on CRB could make, and 2 local observations without explanation [Ref4]. Their outcome on CRB:

| No | Check | Outcome |
|---|---|---|
| 1, 2 | `bwx.c` compiles for AArch64 with gcc 14.2.0, without warnings | Yes. 4 binaries, and `build.txt` has no compiler message [Ref15]. |
| 3, 5, 6 | Loop bodies, loop offsets, own address of each A/A copy | 83 of 84 rows of `check_listing.py` are ok on the second build. See lead's change 1 for the failed row [Ref21]. |
| 4 | Distance from function start to loop start | gcc aligned the C copy loop of `bwx_o52` in the first build. The second build uses `-falign-loops=1` for that binary [Ref15]. |
| 7 | Self-test of the real kernels | `failures=0` in all 4 binaries [Ref15]. |
| 8 | `build.sh` and `check_listing.py` on a real listing | Both ran. `check_listing.py` was changed (lead's change 2). |
| 9 | Counters without root | They work. The short run gives 11.14 instructions per 256 B for asm read at 32 KiB. That is 1.3 % above the 11 of the loop, inside the 3 % that the handoff accepts [Ref2][Ref16][Ref21]. |
| 10 | Lookup of the buffer in `/proc/self/smaps` | 0 P rows without a value in every step [Ref7]. The longest page reading took 8.90 ms (step B9 of s2, 240 buffers), below the 50 ms of handoff B.6 [Ref21]. |
| 11 | Late thread starts and end skew with 120 threads | 0 of 378912 T rows of both sessions have the flag `late` [Ref21]. The largest end skew with the common stop is 2.966 ms, below the limit of 5 ms [Ref9]. |
| 12 | Memory use of the guard space | Insufficient data. A reading of the resident memory of one `bwx` process would give it. |
| Local observation 1 | Late thread starts on the loaded development machine | Not seen on CRB (see check 11). |
| Local observation 2 | One counter value near 2^47 (about 1.4 x 10^14) in 1 of 48 rows on the development machine | Not seen on CRB. 0 of 68192 C rows of both sessions have a count above 10^13 [Ref21]. The cause on the development machine is still not known. |

### Changes in the run script `run_bwx.sh`

`DEVIATIONS-scripts.md` lists the points S1 to S20 [Ref5].

| No | Change |
|---|---|
| S1 | One result folder per step, not per visit. |
| S2 | B10 runs in two halves (B10a, B10b). Each half holds every setting. Both halves write a file named `B10.csv`. |
| S3 | `MARGIN` is set per step: the timed intervals of its longest process plus 90 s. The 90 s are an estimate (est.). |
| S4 | The counter codes come from two environment variables and are recorded in `env.txt`. |
| S5 | `BWX_STOP`, `BWX_START`, `BWX_MIN_MS` are required for B8, B5, B9, C3. B9 also uses `BWX_START`. |
| S6 | C3 takes a list of B7 settings, 2 processes each, then the B5 sequence forward and reversed. |
| S7 | B8 takes one list of counts for both kernels. |
| S8 | B4: on each CPU 2 processes with `--no-thp` and 2 without, alternating. |
| S9 | B2 and B3: 4 processes on each of the 4 CPUs. |
| S10 | B5: forward, reversed, forward, reversed. |
| S11 | Interleaving: the outer loop is the process index, with a fixed order of settings inside. |
| S12 | The short run has 28 processes plus 4 with counters. It covers 4 of 8 B7 settings and 2 of 8 B10 settings. |
| S13 | B9 is skipped below 70 GiB of free memory, with the new status 6. This did not occur. |
| S14 | `env.txt` holds the sha256 of the binaries. `BWX_SHA256` makes the script stop on a different `bwx`. |
| S15 | A missing `STOP_AT` gives status 2. |
| S16 | `--dry-run` prints the plan of a step. |
| S17 | The stop functions of `run_partA.sh` are copied without change. |
| S18 | No variable of `run_bwx.sh` changes the marker path. (`build.sh` has one, see the table of `bwx`.) |
| S19 | After an interruption (status 130) no `-- killed` line is written. This did not occur. |
| S20 | A PMU type that is not a whole number stops the script before the first launch. |

### Changes and choices in the analysis `analyze_bwx.py`

`DEVIATIONS-scripts.md` lists the points A1 to A33, P1 and P2 [Ref5]. The rules are coded in `analyze_bwx.py` and `decide.py` [Ref17].

| No | Choice |
|---|---|
| A1 | The entry of an interval comes from `--seq` and `pos`. |
| A2 | Rates come from the T rows, not from the rounded I row. |
| A3 | A process with a missing interval or row is left out and listed. None was left out. |
| A4 | Rounds are ordered by their printed number. |
| A5 | With whole passes the end skew does not make an interval irregular. **Needs a decision.** The largest such skew was 182.0 ms, in step B10 of s2 at 0.5 s (36 % of the interval, against the limit of 5 ms for the common stop) [Ref9][Ref21]. |
| A6 | A process with an irregular interval gives no value. **Needs a decision.** No interval was irregular, so no result depends on it [Ref9]. |
| A7 | If M_hist and M_sum give another word or sign, the result is "not resolved". |
| A8 | The rule for one kernel per process is coded in the analysis. |
| A9 | B9: rule for the pattern and for the total, with the A/A value from two processes of one kind. |
| A10 | B5: rule as the handoff words it, with at least 4 processes. |
| A11 | Percentiles of q by nearest rank (12th and 108th of 120 rates). |
| A12 | B4: cases (a) and (b) are counted per CPU and session over all its processes. **Needs a decision.** |
| A13 | B4: "rejected" needs one CPU with a case in every session. **Open, see H3a.** |
| A14 | B4: level changes with equal coverage and equal counts `thp_collapse_alloc` and `pgmigrate_success` are counted as a description. |
| A15 | B6: the A/A spread of a CPU uses all its complete processes. |
| A16 | B3: the change against B1 needs 3 processes of one label on a CPU in both. |
| A17 | B8: brackets may share one end point for "supported". |
| A18 | B10: controls and H11 from `decide.py`. The change of the median total is a description. |
| A19 | The mapping of a step result to a word over two sessions is the script authors' reading. |
| A20 | H5 is mapped to the variant `asmcopy_c` only. |
| A21 | H11: the script does not compare the mesh between sessions. The Q2 page does [Ref9]. |
| A22 | Part C is a description with no decision. |
| A23 | No page state is assigned to an interval of a process with more than one thread. |
| A24 | No rate is computed for the time in which all threads ran. |
| A25 | The short run gives no decision. |
| A26 | H7a and H7b for read are "not observed" in a session without a reproduced D. This did not occur. |
| A27 | The rule for one kernel per process uses both metrics. |
| A28 | B5: a disagreement of the two metrics gives "not resolved", never "yes". **Needs a decision.** It did not occur. |
| A29 | H7a and H7b for read: the same for a change of D. It did not occur. |
| A30 | H6 is "not observed" in a session whose B1 has no resolved difference. This applies to both sessions. |
| A31 | Tables of Part C count processes, and keep the B7 and B5 sequences of C3 apart. |
| A32 | Fix of 2026-11-14: the H3a flag of a session comes from that session alone. Before, the word was "not observed". |
| A33 | Fix of 2026-11-14: H8, H9a and the B5 statement now show two words: the word without labels and the word of the label rule. |
| P1 | Part A: write and copy rows of A3 are left out of the test of q (36 rows). **Needs a decision.** |
| P2 | Part A: the page text was corrected on which words it quotes from the plan. |

No file records a decision of the lead on A5, A6, A12, A28 and P1. They are applied as coded.

## Steps not run

- **Part D** (D1 mesh counters, D2 physical page addresses). It needs root. The handoff forbids root [Ref2]. Consequence: H3b and H10 are "not tested".
- **The file-based review loop for `bwx`.** Replaced by the agent review that the user accepted [Ref3].
- **The update of `plan.md` after each part** (plan, order item 6) [Ref1]. `plan.md` is unchanged.
- **One result page per visit** (handoff, "What to deliver") [Ref2]. Replaced by one page per question.
- Every step of Parts A, B and C ran in full. No step of them was stopped or repeated. The build ran twice (lead's change 1).

## Limits

- The two sessions ran one after the other in one night, with no restart of the machine between them. No result covers another day or a restart [Ref9].
- The level limits (69 and 70.5 GB/s) do not fit the data. Only 24 of 144 processes with reference intervals are stable in s1 and 25 of 144 in s2 [Ref8].
- In the copy steps (B1, B2, B3 and C2) the median reference rate on CPUs 41 and 94 is 70.19 to 70.41 GB/s in s1 and 70.12 to 70.46 GB/s in s2. These values lie between the two limits [Ref8].
- In step B6 the median reference rate on the same two CPUs is 68.76 to 68.91 GB/s. That is below the low limit [Ref8].
- No value is the traffic of the time in which all threads ran. Plan rule 6 is met only in part [Ref2].
- The decisions use many comparisons of two settings with no correction for their number [Ref9].
- A thread that loses its CPU inside an interval is not marked in a run without counters. In C3 the lowest CPU share of a thread was 92.46 % of its interval (s2) [Ref9].
- Hypothesis (not tested): the root process `check-new-relea` took that CPU time. A record of the CPU on which it ran would test it [Ref9].
- The count of L1 refills is lower than the count of L2 refills in every asm read interval of C1 and C2. Hypothesis: the two events do not count what their names say. The event definitions of the core would decide it [Ref8].
- The page state of an interval with many threads is the reading after the interval before it [Ref2].
- The limits 100 µs and 5 ms for an irregular interval are provisional [Ref2].
- Part A is a first look with the existing binaries and decides nothing. Its numbers were recomputed by an independent agent (3497 values, 0 differences, lead's record) [Ref20].
- The chart colours of the two pages were not checked with the palette checker of the chart rules (a script that tests whether chart colours can be told apart) [Ref8][Ref9].
- The Slack readings and the login error are in the lead's record only [Ref20].
- The second recount of the words is in the lead's record only [Ref20].

## Decisions already made

Both answers were given by the user on 2026-11-13, about 23:25 UTC [Ref3].

1. **User decision 1. Who reviews `bwx`?** Answer: "Agent review is enough." The review by 4 reviewer agents is accepted. No file-based review loop was run.
2. **User decision 2. What do steps B8 and B5 use, given that q did not fall into two groups in Part A?** Answer: "Report q, no labels." Where a rule needs a label that the data do not give, the word is "not resolved". No rule is adapted.

## Open decisions for the user

- Only item 7 needs a new run.
- Decide item 1 first. Item 2 uses the same limit of 69 GB/s.

1. **Level limits at 8 MiB.** The limits 69 and 70.5 GB/s label only 24 of 144 processes as stable in s1 and 25 of 144 in s2 [Ref3][Ref8].
   - Option a: set new limits.
   - Option b: use a rule without labels for B1, B2, B3 and B6. One candidate is the rule for a size without level. As a description it gives "not resolved" for B1 at 8 MiB in both sessions (see H4).
   - Option c: keep the limits. The words stay "not observed".
   - Options a and b can change the words of H4, H5, H6 and of part 1 of H1. The analysis is then rerun on the same files.
2. **H3a.** Two questions.
   - Must the case be on the same CPU in both sessions? Yes gives "not rejected" (strict output). No gives "rejected" (plan, step B4).
   - Does the s2 case count, with 175 of its 176 low intervals less than 0.2 GB/s below the limit of 69 GB/s? If it does not count, the word is "not rejected" under both readings.
3. **H1.** Option a: "rejected" (strict rule). Option b: "not resolved", because the difference is a position effect and the pair definition does not fit it.
4. **H7b, read and write.** Option a: "rejected" (the bounded prediction failed in both sessions). Option b: "not resolved" (every change is inside its limit). The choice changes two rows of the table.
5. **H9a and H9b.**
   - H9a, option a: confirm "not resolved" under user decision 2. Option b: accept q as the measure of the pattern for step B9. The word is then "rejected".
   - H9b, option a: "not observed" (the rule of the Q2 page). Option b: "not resolved" under user decision 2.
6. **Q2b.** The plan sets no rule for when two write totals are separate levels.
   - Option a: set a rule on the gap between neighbouring totals. The analysis then answers Q2b from the same files.
   - Option b: set no rule. The answer stays "Insufficient data".
7. **Part D.** Whether to run D1 and D2 with root. Without them H3b and H10 stay "not tested". This is the only item that needs a new run.
8. **Benchmark and report.** Whether `bench/bandwidth.c` or `crb-memory-hierarchy.html` should change. Both are unchanged.
   - The reason for the benchmark: its timing method (whole passes, 0.5 s, common start) is the reproduction condition, and the plan leaves a change of it to the user [Ref1].
   - The reason for the report: the plan names one sentence of it that does not hold at 120 threads in the run of 2026-11-13 [Ref1].
9. **Analysis choices A5, A6, A12, A28 and P1.** Confirm or change each. Only A5 and A12 change a result of these data.
   - A5: with whole passes, an end skew above 5 ms does not make an interval irregular. If it did, 304 of 304 whole-pass intervals of B7 and 256 of 256 of B10 would be irregular in each session [Ref21]. The reproduction condition would then give no value. By choice A26 the script then gives "not observed" for H7a and H7b for read in both sessions [Ref5]. A rerun of the analysis with this one change gives these two words. It also gives "rejected" in place of "not rejected" for H7a for write. It also gives "not observed" in both sessions for 4 cells of H11 (old write and asm write, whole passes, offset start, 0.5 s and 15 s). Three of the 4 supported cell results are in these cells [Ref21].
   - A6: a process with an irregular interval gives no value. No interval was irregular.
   - A12: cases (a) and (b) of B4 are counted over all processes of a CPU. With a count per process, s1 has no case, because its two levels are in two processes. s2 still has its case in process `thp-cpu41-p2` (175 low and 17 high intervals) [Ref21].
   - A28: in B5, a disagreement of M_hist and M_sum gives "not resolved". It did not occur.
   - P1: in Part A, 36 write and copy rows of A3 are left out of the test of q.

## Files

`R` stands for `/home/jhan/workspace/titan/cache-perf/crb/results`. `N` stands for `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel`.

| What | Where |
|---|---|
| Part A raw files | `R/partA-20261113T204939Z/` (A5, A6, A7), `R/partA-20261113T205055Z/` (A1 to A4) |
| Part A page and numbers | `R/partA-20261113T205055Z/partA-result.html`, `partA-summary.json` |
| Session s1 raw files | `R/B7-20261113T232859Z`, `R/B10a-20261113T235919Z`, `R/B10b-20261114T003359Z`, `R/B8-20261114T010839Z`, `R/B5-20261114T011723Z`, `R/B9-20261114T012105Z`, `R/B1-20261114T012315Z`, `R/B4-20261114T014024Z`, `R/B6-20261114T014825Z`, `R/B2-20261114T015517Z`, `R/B3-20261114T020808Z`, `R/C1-20261114T022058Z`, `R/C2-20261114T022500Z`, `R/C3-20261114T022708Z` |
| Session s2 raw files | `R/B7-20261114T024352Z`, `R/B10a-20261114T031357Z`, `R/B10b-20261114T034855Z`, `R/B8-20261114T042331Z`, `R/B5-20261114T043213Z`, `R/B9-20261114T043555Z`, `R/B1-20261114T043752Z`, `R/B4-20261114T045459Z`, `R/B6-20261114T050300Z`, `R/B2-20261114T050925Z`, `R/B3-20261114T052215Z`, `R/C1-20261114T053506Z`, `R/C2-20261114T053907Z`, `R/C3-20261114T054116Z` |
| Each raw folder holds | `<step>.csv` (`B10.csv` in the B10a and B10b folders), `env.txt`, `launches.txt`, `stderr.txt` |
| Pages of Parts B and C | `R/partBC-20261114/partB-q1-result.html`, `R/partBC-20261114/partB-q2-result.html` |
| Decision analysis | `R/partBC-20261114/analysis/` (`hypotheses.txt`, `summary.json`, `<step>.txt`) |
| Copies of the scripts | `R/partBC-20261114/scripts/` |
| Short run | `R/SHORT-20261113T214338Z/` |
| `bwx` source, build records, deviations | `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/` (`bwx.c`, `run_bwx.sh`, `analyze_bwx.py`, `crb-build-1/`, `crb-build-2/`, `DEVIATIONS-bwx.md`, `DEVIATIONS-scripts.md`) |
| Page generators and tests | `N/partBC-analysis/` (`make_q1_html.py`, `test_q1.py`, `make_q2_html.py`, `test_q2.py`), `N/partA-analysis/` |
| Recount for this file | `N/partBC-analysis/recount/` (`recount_results_md.py`, `recount_results_md.txt`, `check_listing-crb-build-1.txt`, `check_listing-crb-build-2.txt`, `a5-reversed/`) |
| Logs and user decisions | `N/partA-short.log`, `N/partA-long.log`, `N/visit-s1-*.log`, `N/visit-s2-*.log`, `N/session2.log`, `N/decisions.md` |
| Older outputs, not sources | `R/partB-s1-analysis/` (one session only), `N/partBC-analysis/OLD-partB-q2-result-session1-only-20261113.html` |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md`: the two questions, hypotheses H1 to H11, rules 1 to 11, steps, "Results expected at the end".
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md`: host rules, stop controls, specification v1 (B.1 to B.10), "Order of work", "What to deliver".
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/decisions.md`: user decisions 1 and 2, and the open decision on the level limits.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/DEVIATIONS-bwx.md`: deviations 1 to 24, the known limits of `bwx`, the smaller points of `build.sh` and `check_listing.py`, and the list of checks that need a build on CRB.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/DEVIATIONS-scripts.md`: points S1 to S20, A1 to A33, P1, P2.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/results/partBC-20261114/analysis/hypotheses.txt` and `summary.json`: the strict output per hypothesis and session.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/results/partBC-20261114/analysis/`: `B1.txt` to `B10.txt`, `C1.txt` to `C3.txt` (decision, processes, A/A spread and value of every group, and the load of every step).
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/results/partBC-20261114/partB-q1-result.html`: page of question Q1 (B1, B2, B3, B4, B6, C1, C2).
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/results/partBC-20261114/partB-q2-result.html`: page of question Q2 (B7, B10, B8, B5, B9, C3).
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/results/partA-20261113T205055Z/partA-result.html` and `partA-summary.json`, with the raw files in that folder and in `/home/jhan/workspace/titan/cache-perf/crb/results/partA-20261113T204939Z/` (`env.txt` holds the start and end lines).
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/session1-folders.txt`: the 14 result folders of session s1.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/session2-folders.txt`: the 14 result folders of session s2.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/`: `partA-short.log` (result folder only, no status line), `partA-long.log`, `visit-s1-*.log`, `visit-s2-*.log`, `session2.log` (result folder, planned processes and status of every visit).
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/session2.sh` and `visit.sh`: the settings of session 2 and the sha256 check of `bwx`.
- [Ref15] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/crb-build-2/`: `build.txt` (compiler, flags, `EXTRA_bwx_o52`, self-test results, sha256), `build.out` (exit status of the build), `short.out` (exit status of the short run), `offsets.tsv`, `listing.txt`. The first build is in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/crb-build-1/` (`build.txt`, `build.out`, `offsets.tsv`, `listing.txt`, and four `selftest-*.txt` files).
- [Ref16] `/home/jhan/workspace/titan/cache-perf/crb/results/SHORT-20261113T214338Z/`: the short run before session 1 (`SHORT.csv`, `env.txt`).
- [Ref17] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/analyze_bwx.py` (function `two_sessions` maps two sessions to a word), `test_analyze_bwx.py`, and `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/decide.py`: the decision rules as code.
- [Ref18] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partBC-analysis/`: `make_q1_html.py`, `test_q1.py`, `make_q2_html.py`, `test_q2.py`.
- [Ref19] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/run_bwx.sh` and `bwx.c`: the load readings before each launch, the sha256 check of `bwx`, and the benchmark. For Part A: `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/run_partA.sh` (the same load readings, and the end line of `env.txt`).
- [Ref20] The lead's record of the execution. It is not a file, so no claim that cites it can be verified from the result files. It holds the Slack readings, the login error of 05:58 UTC, the changes of the lead, the review counts of `bwx`, the second recount of the words, and the recomputation of Part A.
- [Ref21] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partBC-analysis/recount/`: `recount_results_md.py` and its output `recount_results_md.txt` (recount from the raw csv files of both sessions and of the short run: B4 intervals per process, C1 and C2 counters by level, d and A/A spread of B1, B2 and B3 over all processes, B6 by position, D as a share of the old read total, end skew, late starts, page reading time), and `check_listing-crb-build-1.txt`, `check_listing-crb-build-2.txt` (output of `check_listing.py` on the two listings, run on the development machine on 2026-11-14 UTC). The folder `a5-reversed/` holds the rerun of `analyze_bwx.py` on the 28 step folders with choice A5 reversed: the one changed line (`analyze_bwx-a5-reversed.diff`), its `hypotheses.txt` (`hypotheses-a5-reversed.txt`), and the lines that differ from the delivered `hypotheses.txt` (`hypotheses-change.diff`).
