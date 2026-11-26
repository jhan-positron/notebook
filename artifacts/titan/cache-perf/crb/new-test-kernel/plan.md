# Plan: two open questions after the rewrite of the C kernels

## Short version

The run of 2026-11-13 left two questions: why the 8 MiB buffer with one thread behaves differently from the other sizes, and why the old read kernel is faster than the new one when 120 threads run. This plan names what the existing result files already show, lists the hypotheses, and gives the measurements in the order of their cost, each with the bounded prediction that it tests. Nothing in this plan has been run yet, and the two steps that need root on CRB wait for the user's approval.

## Words used here

- **CRB**: the Arm Phoenix Reference Server (128 cores, AArch64). All measurements run there.
- **Kernel**: one timed loop of the benchmark `bench/bandwidth.c`. It is not the Linux kernel.
- **Old read**: the read kernel before 2026-11-13. Per 128 B it runs 4 `ldp` (loads of 32 B) and 8 vector adds.
- **New read**: the read kernel since 2026-11-13. Per 256 B it runs 8 `ldp` and no add.
- **asm read / asm write / asm copy**: the kernels written in inline assembly. asm read has the same loop body as new read.
- **Load-only loop**: new read or asm read.
- **`bw_old` / `bw_new`**: the benchmark built from the source before and after the rewrite.
- **Process**: one start of the benchmark program. It allocates its own buffers.
- **Repetition**: one timed interval inside a process (at least 0.5 s by default, option `--min-ms`).
- **Pass**: one sweep of a thread over its whole buffer. A thread runs whole passes until the interval is over.
- **Rate**: bytes moved per second, in GB/s (1 GB = 10^9 bytes).
- **L1, L2, SLC**: the three cache levels of a core. SLC is the system-level cache (L3), shared by all cores. An 8 MiB buffer fits the SLC and does not fit L2.
- **DRAM**: main memory. A buffer of 256 MiB per thread is read from DRAM.
- **Mesh 0 / mesh 1**: the two halves of the chip. CPUs 0 to 63 are on mesh 0, and CPUs 64 to 127 are on mesh 1 [Ref6]. We may use CPUs 0 to 119, so 120 threads means 64 threads on mesh 0 and 56 threads on mesh 1.
- **a+b threads**: a threads on mesh 0 and b threads on mesh 1.
- **Low level / high level**: the two rates that a load-only loop shows at 8 MiB with one thread: about 67 to 69 GB/s and about 70.5 to 71.7 GB/s.
- **Interval**: one repetition, seen as one point in the time sequence of a process. This plan labels each interval with a level, not each process.
- **Reference interval**: an interval of asm read that is timed directly before or after a compared interval, to show the level at that time.
- **A/A control**: one loop that exists twice in the binary under two names. The difference between the two copies shows how much two equal loops differ.
- **Huge-page coverage**: how many bytes of a buffer are backed by 2 MiB pages (the value `AnonHugePages` of the buffer in `/proc/self/smaps`).
- **Physical-page identity**: which physical pages back a buffer. Linux can replace them while the buffer stays mapped [Ref9].
- **Split pattern / uniform pattern**: the two per-thread distributions seen with many threads at 256 MiB. Split: the slowest thread has about half the rate of the fastest. Uniform: all threads have nearly the same rate.
- **THP**: transparent huge pages, the Linux feature that backs memory with 2 MiB pages.
- **Counter**: a hardware event counter read with the Linux tool `perf`.
- **Core counter / mesh counter**: a counter inside one core, or a counter of the mesh (PMU name `arm_cmn`).
- **`:u`**: the `perf` suffix for an event that counts only user-mode code. Without root on CRB, `perf` counts in this mode.
- **Root**: administrator rights on CRB. The setting `kernel.perf_event_paranoid` is 2 there, so mesh counters need root [Ref8].
- **Marker file**: `/tmp/positron-perf.RUNNING`. Jeremy's test account creates it while his measurements run.
- **Scratch binary**: a copy of `bandwidth.c` under `crb/tmp/agent-scratch/`, changed for this investigation only. `bench/bandwidth.c` is not changed by this plan.
- **est.**: an estimate, not a measurement.

## The two questions

**Q1. One thread, 8 MiB.** Three observations of the run of 2026-11-13 at 18:12 UTC [Ref1]:

- Q1a. New read is only 0.9 % above old read (67.71 against 67.08 GB/s, best rates). At the other three sizes it is 7.6 % to 99.6 % above.
- Q1b. New C copy is 2.91 % below asm copy (57.09 against 58.80 GB/s, best rates). In the other 11 cells the new C kernel is within 0.5 % of its asm kernel.
- Q1c. The same asm read loop gave 71.07 GB/s (best) in the run at 06:05 UTC and 67.99 GB/s (best) in the run at 18:12 UTC [Ref1][Ref2].

**Q2. 120 threads, 256 MiB per thread.** Two observations of the same run [Ref1]:

- Q2a. Old read totals 464.42 to 466.65 GB/s. New read totals 279.66 to 304.05 GB/s, and asm read 271.10 to 305.90 GB/s. With one thread at 1 GiB the order is the opposite (old 28.72, new 30.89 GB/s).
- Q2b. The write kernels give several separate totals between repetitions: about 117 GB/s, about 124 GB/s, about 145 GB/s, and once 186.88 GB/s.

## What the existing files already show

I computed every number in this section from local result files on 2026-11-13. No new run was made for this plan.

### For Q1 (8 MiB, one thread)

1. **A load-only loop has two levels at 8 MiB, and two load-only loops that ran one after the other in one process showed the same level.** In the 06:05 run, old read, asm read and the C load-only loop ran in one process on one buffer. Asm read and the C loop agree in each of the 4 processes: about 71.0 GB/s in 3 processes and 67.85 to 68.31 GB/s in the fourth [Ref2]. In the 18:12 run, all repetitions of the 12 processes of new read and asm read were between 67.23 and 68.21 GB/s [Ref1]. The level can change inside a process (item 5), so it is a property of an interval, not of a process.
2. **So Q1c compares a run that had the high level with a run that did not.** It is not a difference between kernels.
3. **Old read does not follow the level.** It gave 67.07 to 67.12 GB/s in all 4 processes at 06:05 and 66.97 to 67.08 GB/s at 18:12 [Ref1][Ref2]. It also gives 66.64 to 67.13 GB/s at 32 KiB and 1 MiB [Ref1]. So old read is at about 67 GB/s at every size that fits a cache.
4. **This answers Q1a in part.** The 0.9 % is the distance between the rate of old read (about 67.1 GB/s at all cache sizes) and the low level of the load-only loop on CPUs 0 and 2 (67.2 to 68.2 GB/s). With the high level, the same comparison in the 06:05 run gives +5.8 % to +6.1 % in 3 of the 4 processes [Ref2]. What sets the two levels is not known.
5. **The two levels were seen before.** A sweep of 2026-11-02 ran asm read at 8 MiB on each of the 120 CPUs, 3 repetitions of 0.3 s, twice (240 processes) [Ref3]:
   - The first repetition is between 66.43 and 68.99 GB/s on all CPUs. No process starts at the high level.
   - 41 repetitions are above 70.5 GB/s. 39 of them are the third repetition and 2 are the second. They belong to 39 of the 240 processes.
   - So in that sweep the high level appears only after some time inside a process. The files do not show whether the physical pages of the buffer stayed the same during that time.
6. **The copy difference of Q1b is present in all 4 process pairs.** Mean rate per process, in the order (CPU 0 round 1, CPU 2 round 1, CPU 0 round 2, CPU 2 round 2): new C copy 54.57, 56.23, 56.83, 56.44 GB/s; asm copy of `bw_new` 56.59, 58.47, 58.48, 58.51 GB/s [Ref1]. Paired, new C minus asm is -2.02, -2.24, -1.65, -2.07 GB/s.
7. **But the two copy kernels never ran in the same process.** Asm copy of `bw_old`, which has the same source, gave 57.80, 58.69, 58.12, 57.18 GB/s [Ref1]. So one identical loop spreads over 1.51 GB/s between processes. The mean difference in question is 1.99 GB/s.
8. **The machine code of the two copy loops differs in three ways** [Ref1]: the position of the two `add` instructions (7 of the 8 stores of the C loop use the pointer that was advanced in the same iteration), the registers (q16 to q31 against q0 to q15), and the address of the loop start (0x1ca4 against 0x1bf4, which is 36 and 52 modulo 64).

### For Q2 (many threads, 256 MiB)

9. **The benchmark counts whole passes, and a repetition holds very few of them.** A thread runs whole passes until 0.5 s are over. The total bytes of a repetition divided by 256 MiB is the number of passes of all threads [Ref1]:
   - New read and asm read: 600 passes in 17 of the 18 repetitions, which is 5 passes for each of the 120 threads. One repetition has 664 passes.
   - Old read: 952 to 970 passes.
   - Write kernels: 240 passes (2 per thread) in all 12 repetitions between 117 and 124 GB/s. 295 or 296 passes in the 8 repetitions between 129 and 148 GB/s. 360 passes at 139.92 and 152.01 GB/s. 337 passes at 140.91 GB/s. 416 passes at 186.88 GB/s.
   - So the separate write totals of Q2b follow the pass count exactly. A thread that needs 0.50 to 0.55 s for 2 passes is at the limit of the 0.5 s interval. Whether the totals describe the hardware or the timing method is not known.
10. **Old read at 120 threads has two patterns in the files.** On 2026-11-13 it gave 464 to 467 GB/s with per-thread rates from 2.66 to 5.15 GB/s (split) [Ref1]. On 2026-10-30 it gave 365.10 to 368.25 GB/s with per-thread rates from 2.68 to 3.51 GB/s [Ref4]. In the earlier run each thread also held a second 256 MiB buffer (option `--kernel all`). So the files do not show that old read is always faster at 120 threads.
11. **The load-only loop has both patterns too, at other thread counts.** Asm read with 64+32 threads: 410 to 411 GB/s, per-thread 2.59 to 5.65 GB/s (split) [Ref5]. Asm read with 48+48 threads: 320 to 322 GB/s, per-thread 3.22 to 3.51 GB/s (uniform) [Ref3]. Asm read with 64+56 threads on three days: 303 to 308, 292 to 298, and 271 to 306 GB/s, all uniform [Ref5][Ref3][Ref1].
12. **In the uniform pattern, 120 threads read less than one mesh alone.** 64 asm read threads on mesh 0 alone read 344 to 346 GB/s. 56 threads on mesh 1 alone read 318 GB/s [Ref3].
13. **Which threads are the fast ones is not recorded.** No 256 MiB run has per-thread rows. For old read at 64+56 threads, the pass count fits "64 threads at about 10 passes and 56 threads at about 5.8 passes" (64 x 10 + 56 x 5.8 = 965). This is arithmetic, not a measurement.
14. **The report already describes a fall of the DRAM write rate with writers on both meshes** [Ref6]. Root counters did not locate its cause. No counter exists for any read kernel above 64 threads.

## Hypotheses

Each hypothesis has a label. None of them is established. A hypothesis with two parts has one label per part, so that each test names the part it tests.

| Label | Question | Hypothesis | Observation it does not explain |
|---|---|---|---|
| H1 | Q1a | Old read is limited inside the core at every cache size, and its rate at 8 MiB does not depend on the level of the load-only loop. The load-only loop at 8 MiB is limited by the path from the SLC. The two limits are close on CPUs 0 and 2. | What the limit inside the core is (the report's hypotheses A and B, still open [Ref7]). |
| H2 | Q1c | The low level can change to the high level while the stream runs, and the high level can stay for the next process. Candidates for the state: the prefetcher of the core, or the state of the lines in the SLC. | Why no interval of the 18:12 run reached the high level in 1.5 s, when 3 of 4 processes did at 06:05. |
| H3a | Q1c | Huge-page coverage decides the level: the low level is a buffer that is not fully on 2 MiB pages. | Not known: the coverage was never recorded. |
| H3b | Q1c | The physical address of the pages decides the level. | Not known: physical addresses were never recorded. |
| H4 | Q1b | The copy difference does not come from the kernel code. It comes from something that differs between processes (pages, or what ran before). | The same sign in all 4 pairs (item 6). |
| H5 | Q1b | The copy difference comes from the instruction order of the C loop (position of the `add` instructions, store addresses that depend on the same iteration). | No difference at 1 GiB (-0.49 %) and at 1 MiB (+0.34 %). |
| H6 | Q1b | The copy difference comes from the address of the loop (36 against 52 modulo 64). | The opposite sign at 32 KiB, where the C copy is 0.39 % faster. |
| H7a | Q2a, Q2b | A part of the difference is made by the stop method and the short interval: whole passes, and 5 passes or fewer per repetition. "A part" means a resolved change of the difference in GB/s. It need not be the whole difference. | Old read at 464 to 467 GB/s in all 6 repetitions, and the uniform pattern of asm read on three days. |
| H7b | Q2a, Q2b | A part of the difference (in the same sense) is made by the common start: all threads start together at the start of their buffers. | The same as for H7a. |
| H8 | Q2a | With threads on both meshes the chip has two states (split and uniform). The state depends on the request pressure of all cores together. A load-only loop presses harder per core than old read, so it reaches the uniform state at a lower thread count. | Old read in a uniform pattern on 2026-10-30 (item 10). |
| H9a | Q2a | The second buffer per thread moved old read to the uniform pattern on 2026-10-30 (item 10). | Asm read uniform at 64+56 threads with one buffer and with two buffers [Ref3][Ref5]. |
| H9b | Q2a | The pattern of old read differs between days or sessions for a reason other than the kernel. | Not known. |
| H10 | Q2a | In the uniform state the memory system fetches lines that the loop does not consume (prefetch beyond need, or repeated requests). The benchmark then counts less than the memory system delivers. | The dependence on the balance between the meshes (48+48 against 64+32). |
| H11 | Q2b | Apart from H7a, the write totals differ because the threads of one mesh run faster in some intervals (candidate: the 56 threads of mesh 1). | Not known before per-thread rows exist. |

Why H8 says "presses harder": old read has 16 instructions per 2 lines of 64 B, and the load-only loop has 11 instructions per 4 lines [Ref1]. This is a model that counts instructions. For one number of instructions, the load-only loop covers about 2.9 times as many lines. The model holds only if every instruction uses the same resources of the core. It is not a measurement of the loads in flight or of the entries in use in the out-of-order window. Insufficient data for that: no counter in the local files measures it.

## Two kinds of measurement

- **Screening (part A).** It uses the existing binaries and needs nothing new. It cannot meet the rules below: old and new kernels are in two binaries, there is no A/A control, the page state is not printed, and the existing `--per-thread` row holds only the thread index, the CPU, the kernel, the repetition and the rate [Ref10]. So part A never closes a hypothesis. Its results say which tests of part B come first, and they are reported as "observed in screening".
- **Deciding measurements (parts B to D).** They follow all rules below. A hypothesis is called "rejected" only from these, and only for the bounded prediction that the step names.

## Rules for the deciding measurements (parts B to D)

These rules come from the weak points of the run of 2026-11-13.

1. **Compare kernels inside one process.** Two kernels that are compared run in the same process on the same buffers, in alternating order (A B B A ...). The scratch binary needs a `--kernel` option that takes a list, and one shared schedule for all threads.
2. **One binary, and known loop addresses.** The scratch binary holds the old kernels, the new kernels and all variants. For the reproduction of Q1b it holds the C copy loop and the asm copy loop at the offsets they have in `bw_new` (36 and 52 modulo 64). Other variants state their offset. The listing and the start address of every loop are checked with objdump and saved.
3. **A/A control in the same processes.** Each comparison includes an A/A pair of the same kind (copy with copy, read with read) in the same process, at the same size, CPU and schedule. The A/A spread of a comparison is the largest absolute A/A difference over its processes, so it is never negative. A difference between kernels keeps its sign. It is "resolved" only if the absolute value of its median over the processes is larger than the A/A spread and it has one sign in all processes. The same holds for a change of a difference between two settings: the absolute value of the median change must be larger than the A/A spread, and the change must have one sign in all processes.
4. **Keep the sequence.** The output keeps every interval in time order. Differences are formed between neighbouring intervals of the two kernels. A value per process is given only for a process whose reference intervals are all at one level.
5. **Label each interval, not each process.** For one thread at 8 MiB the schedule brackets every compared pair with reference intervals of asm read (R A B R B A R ...). An interval is "low" if both neighbouring references are below 69 GB/s, "high" if both are above 70.5 GB/s, and "changing" otherwise. The two thresholds are provisional. In the sweep of 2026-11-02, 638 of the 720 repetitions are below 69 GB/s, 41 are above 70.5 GB/s, and 41 lie between [Ref3]. The thresholds are checked against the distribution of the new data before they are used. Results are given per label. "Changing" intervals are reported and are not used for a comparison. Whether the read level is related to the copy rate at all is open, and the brackets are what will show it.
6. **Per-thread rows for every run with more than one thread.** The scratch binary prints for each thread and interval: thread ID, CPU, kernel, bytes, elapsed time, start and end time. The analysis gives totals per mesh, and the total only over the time in which all threads ran.
7. **The stop method is recorded and is a factor.** The scratch binary has two stop methods: whole passes as in `bandwidth.c`, and one common stop time at which each thread counts the bytes of its partial pass. B7 and B10 compare the two. The other multi-thread steps use the common stop time. Where the whole-pass method is used with a long interval (part A), the check is: (interval of the thread) / (passes of the thread) must be at most 2 % of the interval. A repetition that fails the check is marked. With the existing binaries this value is known only as an average over the threads, from the total bytes.
8. **Record the page state around the intervals.** Before every interval (outside the timed part) the process reads the huge-page coverage of each buffer from `/proc/self/smaps` and the system counters `thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc` and `pgmigrate_success` from `/proc/vmstat`. These need no root. They show coverage and whether the system replaced or moved pages somewhere. They do not show the physical-page identity of our buffer.
9. **Record the system load.** Before each process: `/proc/loadavg`, the 5 busiest processes, the logged-in users, and the marker file check. Between two processes with many threads the script waits until the count of runnable tasks is back at the idle value, and records the wait. Every result table gives the load.
10. **Two sessions.** A deciding comparison is run in at least 2 sessions some hours apart, and reported per session. A number from an earlier result folder is used for hypotheses only, not as evidence.
11. **Use limited words.** Each result is one of: "rejected" (the bounded prediction failed in both sessions), "not rejected", "not observed" (an event that the test could have shown did not occur), "not resolved" (the difference is inside the A/A spread), or "not tested". Each reported difference names the number of processes and the A/A spread.

Host rules, unchanged: read the Slack channel #phoenix-crb before each login and do not log in during an announced block of Jeremy; check the marker file before every process; use CPUs 0 to 119 only; write only under `~/cache-perf`; no sudo in our scripts; no package installation and no change of system settings [Ref8].

## Measurements

### Part A. Screening with the existing binaries, no root

Part A closes no hypothesis (see "Two kinds of measurement"). The last column says what a result would point to.

| Step | What runs | Looks at | What the result points to |
|---|---|---|---|
| A1 | 120 threads (64+56), 256 MiB, `--per-thread`, the default 0.5 s interval: old read, new read, asm read, old write, new write, asm write. One process each, 2 rounds. | H8, H11, item 13 | Which CPUs are the fast threads of old read and of the faster write repetitions. |
| A2 | The same six kernels with `--min-ms 6000` for read and `--min-ms 15000` for write, `--reps 3`, `--per-thread`. The 2 % check of rule 7 is computed from the output. | H7a only | If the totals change with the long interval, H7a gets priority in B7. If they stay, the short interval alone is not sufficient to explain Q2a. H7b is untouched: the common start stays. |
| A3 | Old read with one buffer per thread (`--kernel read`) and with two (`--kernel all`, `bw_old`), 120 threads, long interval, 3 processes each, alternating. | H9a only | Whether the second buffer changes the pattern in this session. H9b is untouched. |
| A4 | Old read and asm read at 64+b threads for b = 0, 16, 32, 40, 48, 52, 56, and at a+a threads for a = 32, 40, 48, 56. Long interval, `--per-thread`. | H8 | For each kernel, the two neighbouring thread counts between which the pattern changes. Equal brackets for both kernels are "not resolved at this grid", and the grid is then refined in B8. |
| A5 | One thread, 8 MiB, asm read, `--reps 30 --min-ms 300`, on CPU 2 and on CPU 41 (a CPU that reached the high level in both sweeps of 2026-11-02 [Ref3]). Then at once a second process. | H2 | Whether a change of level is observed in 30 intervals, in which direction, and after how many intervals. No change in 30 intervals is "not observed". It does not reject H2. A different level in the second process says nothing about H2, because the buffer is a new allocation. |
| A6 | One thread, 8 MiB, asm read with `--no-thp`, 8 processes, alternating with 8 processes without the option. | H3a | The rate of a buffer on 4 KiB pages, as a reference value for B4. Alone it rejects nothing: it does not show which coverage the low and the high intervals had. |
| A7 | Read `/proc/sys/abi/sve_default_vector_length` and the list of `perf` events (`perf list`) once. | Needed for the old write kernel, whose bytes per iteration are not recorded, and for the event names of parts C and D. | - |

Cost (est.): A1 about 3 min, A2 about 9 min, A3 about 4 min, A4 about 15 min, A5 and A6 about 3 min. One session of about 35 min outside Jeremy's blocks.

### Part B. Scratch binary, no root

The scratch binary is `bandwidth.c` with these changes: the kernel list and the alternating schedule (rule 1), the old kernels next to the new ones, the loop offsets of rule 2, the A/A pairs (rule 3), the reference intervals (rule 5), the per-thread rows (rule 6), the common stop time (rule 7), the page state (rule 8), both stop methods of rule 7, an option that starts each thread at its own offset inside its buffer, and the variants below. A self-test like the one of 2026-11-13 checks every variant that stores [Ref1]. The scratch binary is reviewed before it is used.

**For Q1 (one thread):**

| Step | What runs | Bounded prediction that is tested | Outcomes |
|---|---|---|---|
| B1 | New C copy against asm copy, both at their original loop offsets, with the A/A pair of asm copy, in one process on the same two buffers, with reference intervals. 16 processes on CPUs 0, 2, 41 and 94. Sizes 4, 8, 16, 32 MiB, each with its own A/A spread. | H4 predicts: inside one process the difference between new C copy and asm copy at 8 MiB is not resolved (rule 3). | Resolved difference in both sessions: H4 is rejected, and B2 and B3 follow. Not resolved: "the difference of 2026-11-13 is not reproduced inside one process". This does not show what made the earlier difference. |
| B2 | Only after a resolved difference in B1. An asm kernel whose loop is the objdump text of the C copy loop (same order, offsets and registers), at the offset of asm copy. Then one change at a time: the position of the two `add` instructions, then the registers. | H5 predicts: the asm kernel with the C instruction order differs from asm copy by a resolved amount of the same sign as in B1. | Prediction fails: H5 is rejected for this order and offset. |
| B3 | Only after a resolved difference in B1. The C copy loop and the asm copy loop each placed at 0, 36 and 52 modulo 64. | H6 predicts: the difference between the two loops changes by a resolved amount when both are at one offset. | Prediction fails: H6 is rejected for these three offsets. |
| B4 | One process, one buffer of 8 MiB that stays mapped, asm read for 200 intervals of 0.3 s, page state before every interval (rule 8). 8 processes on CPUs 2 and 41. Half of them with `--no-thp`. | H3a predicts: every low interval has less than full huge-page coverage, and every high interval has full coverage. | H3a is rejected if low and high intervals are both observed with full coverage (or both with none). H3b is not decided by B4: a level change with constant coverage and with no increase of `thp_collapse_alloc` and `pgmigrate_success` in that interval is reported as "no sign of a page change", which is not proof of physical-page identity. |
| B6 | Old read at 8 MiB and old read at 1 MiB (a size that fits L2) on the same CPU in one process, with reference intervals of asm read at 8 MiB. CPUs 2, 41 and 94. A/A pair: old read twice. | H1 predicts: the rate of old read at 8 MiB does not differ by a resolved amount between low and high intervals, and it does not differ by a resolved amount from its rate at 1 MiB. | H1 is rejected if either difference is resolved. If no high interval occurs, the first part is "not observed". |

**For Q2 (64+56 threads, 256 MiB):**

| Step | What runs | Bounded prediction that is tested | Outcomes |
|---|---|---|---|
| B7 | Read at 64+56 threads: old read, new read, asm read and a second copy of asm read (A/A), per-thread rows. Three factors with two settings each, all 8 combinations: stop method (whole passes as in `bandwidth.c`, or common stop time with partial-pass counting), interval (0.5 s or 6 s), start (common start at the start of each buffer, or per-thread offsets). The setting "whole passes, 0.5 s, common start" is the reproduction condition. It is run in two ways: kernels alternating in one process, and one kernel per process as on 2026-11-13. Two sessions. | The measured effect is D = total rate of old read minus total rate of new read, in GB/s, also per mesh. The reproduction condition predicts a resolved D of the sign seen on 2026-11-13. H7a predicts: D changes by a resolved amount when the stop method changes (other factors fixed), or when the interval changes (other factors fixed). H7b predicts: D changes by a resolved amount when the start changes (other factors fixed). A contribution does not have to remove D. | Reproduction condition gives no resolved D in either way of running: "Q2a is not reproduced in the scratch binary", no cause is assigned, and the difference between the scratch binary and the run of 2026-11-13 is examined first. Reproduction succeeds: each factor is reported with its change of D in GB/s, as "contributes" (resolved change) or "no resolved contribution". If one setting removes D (D not resolved there), that result is reported as "the difference depends on this factor of the timing method", and B5, B8, C3 and D1 are then run only for the settings where D is resolved. |
| B8 | The grid of A4, refined to a step of 4 threads around the brackets that A4 found, with the kernels alternating in one process. For each kernel the result is a bracket: the two neighbouring counts of mesh-1 threads between which the pattern changes. | H8 predicts: asm read changes to the uniform pattern at a lower count of mesh-1 threads than old read. | The bracket of asm read lies wholly below the bracket of old read in both sessions: the prediction is supported. It lies wholly above: the prediction is contradicted. Equal or overlapping brackets: "not resolved at this grid". No rejection is made from overlapping brackets. |
| B5 | Sensitivity test. A load-only read with `nop` instructions: per 128 B, 4 `ldp` and 9 `nop` (the 16 instructions of the old read loop, no add). Also 0, 4, 8, 16 and 32 `nop` per 256 B. Alternating with old read and new read in one process. | Tested statement: "vector adds are needed for the split pattern of old read at 64+56 threads". | The sparse loop shows the pattern and total of old read (difference not resolved): the statement is rejected. Fewer loads per instruction are then sufficient in this test. This does not identify window occupancy as the cause: a `nop` does not use the same resources as a vector add. The sparse loop stays uniform: this perturbation is insufficient, and H8 is not rejected. |
| B9 | Old read with one and with two buffers per thread, alternating processes, two sessions (this needs two processes per comparison, so rule 1 does not apply; the A/A control is the same configuration run twice). | H9a predicts: old read is uniform with two buffers and split with one. | H9a is rejected if the pattern is the same in both cases in both sessions. H9b can only be "observed" or "not observed" over the sessions that were run. |
| B10 | Write at 64+56 threads, independent of the result of B7: old write, new write, asm write and a second copy of asm write (A/A), per-thread and per-mesh rows. The same three factors as in B7, with 0.5 s and 15 s as the two intervals. At least 12 intervals per kernel and setting, so that lower and higher totals can both occur. Two sessions. | For Q2b the measured value is the total rate of each interval and the rate of each mesh in that interval. The spread of a kernel is the highest minus the lowest total of its intervals in one setting, in GB/s. H7a predicts for write: the spread changes by a resolved amount when the stop method changes (other factors fixed), or when the interval changes (other factors fixed). H7b predicts the same for the start. H11 predicts: in an interval with a higher total, the rate of the threads of one mesh is higher by a resolved amount than in an interval with a lower total, and the rate of the other mesh is not. | Each factor is reported with its change of the spread and of the median total in GB/s, as "contributes" (resolved change) or "no resolved contribution". If separate levels remain in every setting, the statement is: these timing changes do not fully explain the levels. The remaining levels are not assigned to the hardware or to any other cause without further evidence. H11 is supported if the higher totals come from one mesh in both sessions, and contradicted if both meshes rise together. If no interval with a higher total occurs under any setting, H11 is "not observed". Per-thread and per-mesh rows are kept for the lower and for the higher totals. |

Cost (est.): writing and reviewing the scratch binary about half a day; B1 to B10 about 90 min of machine time per session, in two sessions.

### Part C. Core counters without root

**Protocol.** The scratch binary counts inside each worker thread, as `bench/homelat.c` already does with the system call `perf_event_open` [Ref11]:

- Each thread opens one counter group on itself, for user mode only, after it is pinned. Events: cycles, instructions, L1 refills, L2 refills, last-level read misses. The names are taken from the event list of step A7. An event that cannot be opened is recorded as "not supported" and gives no result.
- The thread reads the group directly before and directly after each timed interval. So first touch, warm-up and the waits on the barrier are outside the counts.
- Each row holds: thread ID, CPU, kernel, interval number, bytes, elapsed time, the counts, and the time the group was enabled and the time it was running. A row whose running time is below its enabled time is marked as multiplexed and is not used.
- So every count belongs to one kernel, one thread and one interval, and the level or pattern of that interval is known from the rates of the same run. No subtraction of a short run from a long run is used in part C.
- Clock of a busy core: cycles of the interval divided by the CPU time of the thread in that interval (thread CPU clock), not by a time that includes waiting.
- Counter runs are separate from the timing runs of part B. The rates of a counter run are compared with part B to see whether counting changes them.

That user-mode counting of our own threads works with `bandwidth` on CRB is not yet tried. Earlier it was used with the pointer-chase program through `perf stat` [Ref8][Ref4].

| Step | What runs | What it gives | Limits |
|---|---|---|---|
| C1 | One thread, 8 MiB, asm read, the long schedule of B4 with counters. | Refills, cycles and instructions per line for low intervals and for high intervals, labelled from the rates of the same run. No counter was ever read at the low level in a long run. | If no change of level occurs, only one level is described. |
| C2 | One thread, 8 MiB, new C copy and asm copy with their A/A pair, the schedule of B1 with counters. | Whether the memory-side counts per line differ between the two loops. | It is descriptive. H5 and H6 do not predict different instruction or refill counts, so equal counts do not weaken them. |
| C3 | 64+56 threads, old read, new read and the sparse loop of B5, the schedule of B7 with counters. | Per thread: clock (cycles per CPU second), refills per line. Per mesh: the sums. | Equal refills per line read would say that the core side shows no extra fetches. H10 could still hold for traffic that these events do not count. |

Cost (est.): 20 min per session.

### Part D. Mesh counters with root (needs the user's approval)

Mesh counters need root. The earlier root runs were started by the user with `bench/run_sudo.sh` [Ref8]. I do not run sudo. This part is done only if parts A to C leave H8, H10 or H3b open, and only after the user approves it.

| Step | What runs | What it gives | Limits |
|---|---|---|---|
| D1 | 64+56 threads, one kernel per process (old read, asm read), per-thread rows. System-wide mesh counters: `hns_mc_reqs_local_all` and `hns_mc_reqs_remote_all` (memory requests seen by the home nodes of each mesh), `hns_pocq_reqs_recvd_read`, and `dtc_cycles`. | Memory requests per line read, per kernel, with the pattern (split or uniform) taken from the per-thread rows of the same run. The mesh clock with all cores busy. | See below. |
| D2 | One thread, 8 MiB: physical addresses of the buffer pages (`/proc/self/pagemap`) before every interval of the schedule of B4. | Physical-page identity for H3b. | Without D2, H3b stays "not tested", and every statement on the cause of the two levels carries that limit. |

Limits and conditions of D1:

- Mesh counters are system-wide. They cannot be assigned to a thread. So one process runs one kernel.
- Two events with different event IDs per set and per mesh, as in `bench/run_sudo.sh`, and a row is used only if its counter ran 100 % of the time [Ref8].
- A short run is subtracted from a long run only if the per-thread rows of both runs show the same pattern and the same huge-page coverage. Otherwise the long run is reported whole, with the setup included, and marked.
- The two memory-request events overlap: the report notes that a request for a line whose home is on the other mesh is counted on both sides [Ref6]. So the sum is an event count, not a count of unique reads.
- If the requests per line are equal for the two kernels, the result is "H10 is not supported by these counters". It is not a rejection: traffic that these events do not count stays unseen. Insufficient data on the event names for the link between the meshes and for read-side throttling; the event list of step A7 would give them.
- Mesh clock: the raw count of `dtc_cycles` divided by the run time of the counter, with no subtraction of an idle run, as the report's corrected treatment does [Ref12].

## Order and decision points

1. Part A in one session, as screening. It shows which threads are fast (item 13) and how the totals react to a long interval. It closes nothing.
2. The scratch binary is written and reviewed. The results of part A only set the order of the Q2 steps: if A2 changed the totals, B7 comes first; otherwise B7 and B8 are run together.
3. Q2a in part B: B7 first, in two sessions. If the reproduction condition does not reproduce the difference, no cause is assigned and the difference between the scratch binary and the run of 2026-11-13 is examined before anything else. If it reproduces: the contribution of each timing factor is reported, then B8, B5 and B9 for the settings where the difference is resolved, then C3, then D1 if H10 is still open and the user approves.
4. Q2b in part B: B10, in two sessions. It is run whatever B7 shows.
5. Q1 in part B: B1, B4 and B6, in two sessions. B2, B3 and C2 only after a resolved difference in B1. C1 with B4. D2 only if the user approves.
6. After each part I write the results with charts and tables, give per hypothesis one of the words of rule 11, and update this plan before the next part.

## What this plan does not do

- It does not change `bench/bandwidth.c`. The timing method of the benchmark (whole passes, 0.5 s, common start) is a finding to report. A change of the benchmark is a separate decision for the user.
- It does not update the report `crb/crb-memory-hierarchy.html`. The sentence there that the asm loop gives the same numbers as the compiled loop from DRAM does not hold at 120 threads in the run of 2026-11-13 [Ref1][Ref6].
- It does not test the report's hypotheses A and B on the limit of old read inside the core [Ref7].
- It does not read Arm documents. The hypotheses name candidate mechanisms from the measurements only.
- It does not identify what a core holds in its out-of-order window. No step measures that.

## Results expected at the end

- For Q1a: whether the rate of old read at 8 MiB is independent of the level (H1), with the limit that the cause of its own rate stays open.
- For Q1c: the sequence of levels over time with the huge-page coverage of each interval, and counters at each level that was observed. Whether physical addresses matter (H3b) stays "not tested" unless D2 is approved.
- For Q1b: whether a resolved difference between new C copy and asm copy exists inside one process at the original loop offsets. If yes: which single change of order, registers or offset removes it. If no: "not reproduced", with no cause assigned to the earlier difference.
- For Q2a: whether the read difference is reproduced under the original timing method in the scratch binary, the change of the difference in GB/s for each of the three timing factors, and per-thread and per-mesh rates for old and new kernels. Whether vector adds are needed for the pattern of old read.
- For Q2b: whether the separate write totals remain with the common stop time and a long interval (H7a for write), and whether the higher totals come from the threads of one mesh (H11), with per-mesh rows for lower and higher totals.
- For Q2a also: The cause inside the chip is expected to stay a hypothesis unless part D is run, and part D can support H10 but cannot reject it.
- One result page per part in a new folder under `crb/results/`, and a handoff file.

## References

- [Ref1] `/home/jhan/tmp/update_kernel.md` and `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/` (`one-thread.csv`, `threads120.csv`, `probe.txt` with the machine code). The run of 2026-11-13 at 18:12 UTC.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/results/cread-20261113T060510Z/cread.csv`. The run of 2026-11-13 at 06:05 UTC: old read, asm read and the C load-only loop in one process.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/results/followup3-20261102T031936Z/`: `percore-asmread-1.csv` and `percore-asmread-2.csv` (asm read at 8 MiB on each CPU), `readgrid.csv` (asm read against threads per mesh), `writegrid.csv`. Script: `bench/run_followup3.sh`.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/20261030T193108Z/`: `bandwidth.csv`, lines 323 to 325 (old read, 120 threads, 256 MiB, with `--kernel all`), and the files `latency-perf-*.csv` (counter output with the suffix `:u`).
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/followup-20261030T194205Z/asm.csv` (asm kernels against thread count) and `dram.csv` (old kernels against thread count).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html`, section "DRAM bandwidth against thread count" and its part "Writers on both meshes collapse DRAM write bandwidth".
- [Ref7] `/home/jhan/tmp/k_cread.md`, which names the report's hypotheses A and B and the test with 3 loads per 2 adds.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/bench/run_sudo.sh` (root counter runs, short and long pairs, line 3 on `perf_event_paranoid`), `bench/run_crb.sh` (lines 122 to 135: pointer-chase runs under `perf stat` without root), and `/home/jhan/workspace/titan/cache-perf/crb/jeremy-plan-constraints-2026-10-30.md` (host rules).
- [Ref9] Linux kernel documentation, "Transparent Hugepage Support", counter `thp_collapse_alloc`: https://www.kernel.org/doc/html/latest/admin-guide/mm/transhuge.html . Named by the reviewer in round 1. It says that a new huge page is allocated when existing pages are collapsed.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c`: `worker()` (the timing loop with whole passes, first touch, warm-up and barriers) and the `--per-thread` output in `main()`.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/bench/homelat.c`, lines 770 to 790: counter groups opened with `perf_event_open` and read with the enabled and running times.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html`, line 290, and `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/mesh_clock.py`: the mesh clock from the raw `dtc_cycles` count without idle subtraction. The comment in `bench/run_sudo.sh` line 15 on this counter is older.
