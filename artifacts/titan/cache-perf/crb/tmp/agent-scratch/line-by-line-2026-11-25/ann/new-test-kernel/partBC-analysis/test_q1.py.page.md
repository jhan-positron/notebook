## Short version: purpose

`test_q1.py` holds the 14 tests of the page builder `make_q1_html.py`. Twelve tests write result folders with invented rates in the format of the run script `run_bwx.sh` and of the runner `bwx`, build the page from them, and compare values and sentences of the page with what the invented rates must give. Two more tests run only when the real result folders lie in the working tree, and compare the page with a saved output of the analysis script and with values typed into the test.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Page builder**: the script `make_q1_html.py`. This file imports it under the short name `M` [Ref3].
- **Generated page**: the HTML page that the page builder writes: the result page for question Q1 of the plan.
- **Plan**: the test plan of 2026-11-13, the file `plan.md`. Its rule 10 asks for a result per session. Its rule 11 allows five result words [Ref1].
- **Handoff note**: the file `handoff.md`, the instructions for the execution of the plan. Its section B.3 defines the result rows and its section B.10 the numeric decision rules [Ref2].
- **Q1**: the first question of the plan: why one thread with a buffer of 8 MiB behaves differently from the other buffer sizes [Ref1].
- **Parts B, C and D of the plan**: Part B uses the runner `bwx`. Part C repeats steps of Part B with core counters. Part D needs root rights.
- **Step**: one measurement of the plan with a name such as B1. The run script writes one result folder per step.
- **B1**: step: the kernels `copy` and `asmcopy` are compared inside one process, with the A/A pair `asmcopy2` and `asmcopy` [Ref1].
- **B4**: step: one process times `asmread` many times on one buffer of 8 MiB, and the page state is read before every interval [Ref1].
- **B6**: step: `oldread` at 8 MiB and at 1 MiB in one process, with the A/A pair `oldread2` and `oldread` [Ref1].
- **B9**: a step of the second question of the plan that runs 120 threads. The page builder uses only its header lines and its `env.txt`, for the system load.
- **C1**: step: the schedule of B4, run with the option `--count`, which makes the runner read core counters [Ref2].
- **Level, low, high**: a level is the word of the plan for one of two rates of a loop that only loads, at 8 MiB with one thread. An `asmread` interval at 8 MiB has the label low for a rate below 69.0 GB/s and the label high for a rate above 70.5 GB/s. The plan calls the two limits provisional [Ref1].
- **H1**: hypothesis: the old read kernel is limited inside the core at every cache size, and its rate at 8 MiB does not depend on the level [Ref1].
- **H2**: hypothesis: the low level can change to the high level while the loop runs, and the high level can stay for the next process [Ref1].
- **H3a**: hypothesis: huge-page coverage decides the level. The low level is a buffer that is not fully on pages of 2 MiB [Ref1].
- **H3b**: hypothesis: the physical address of the pages decides the level [Ref1].
- **H4, H5, H6**: three hypotheses of the plan on the copy difference, the difference between the rates of the C copy kernel and of the assembly copy kernel at 8 MiB with one thread. H4: it comes from something that differs between processes, and not from the kernel code. H5: it comes from the instruction order of the C loop. H6: it comes from the address of the loop [Ref1].
- **Bounded prediction**: the one statement of a hypothesis that a step tests, as the plan words it.
- **The five words**: the result words of rule 11 of the plan: "rejected" (the bounded prediction failed in both sessions), "not rejected", "not observed", "not resolved" and "not tested" [Ref1].
- **Session (of the plan)**: one run of all steps on CRB. The plan asks for at least 2 sessions some hours apart. The tests name their sessions `s1` and `s2`.
- **Strong session**: the word of this file for an invented session in which every bounded prediction that can fail does fail ({L69-74}).
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`oldread`, `oldread2`, `oldread@1M`**: the old read kernel in the runner, a second copy of the same source, and the entry that runs `oldread` on the first 1 MiB of the buffer.
- **`copy`, `asmcopy`, `asmcopy2`**: three copy kernels of the runner: the C copy kernel, the copy kernel written in assembly, and a second copy of the source of `asmcopy`.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Invented folder**: a folder that the function `folder` of this file writes in the form of a result folder. Its rates are invented and are no measurement.
- **Block**: the text of one process in the csv file of a step: the header line and the rows that the runner prints. The function `block` of `test_analyze_bwx.py` writes it from a rate function [Ref4].
- **Rate function**: a small function that gives the invented rate in GB/s for a round, a position, an entry, a thread and a CPU.
- **Header line**: the line that the run script writes before the output of each process. It starts with `-- step` and holds the step, the tag, the load values and the arguments of the runner.
- **Tag**: the name that the run script gives a process, for example `8M-cpu2-p1`.
- **`P` row**: a row with the page state of one buffer, read before an interval. Counted from 1 with the row letter as field 1, field 6 is `kB_total`, field 7 is `kB_huge`, and fields 10 and 11 are the system counters `thp_collapse_alloc` and `pgmigrate_success` [Ref2].
- **`C` row**: a row with the counter values of one thread and interval: the enabled time, the running time and the CPU time in ns, and one count per event [Ref2].
- **`env.txt`, `launches.txt`, `stderr.txt`**: three more files of a result folder: the state of the machine at the start and the end of the step, one block of load readings per launch, and the error output of the runner.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Reference interval**: an interval of `asmread` at the buffer size of the process, timed before and behind every compared pair.
- **Stable process**: a process whose reference intervals all have the label low, or all have the label high.
- **Pair, pair value**: a pair is two neighbouring intervals of two compared entries between the same two reference intervals. The pair value is the rate of the first-named entry minus the rate of the second, in GB/s.
- **A/A pair, A/A spread**: an A/A pair is a pair of the two copies of one loop. The A/A spread of a CPU is the largest absolute `e` of its processes.
- **`d`, `e`**: the two values of one process. `d` is the median of its pair values of the two compared entries. `e` is the median of its A/A pair values.
- **Resolved**: the word of the plan for a difference whose absolute median is larger than the A/A spread and that has one sign in all processes [Ref1].
- **Rule, description**: the rule is the decision rule of the analysis script. At 8 MiB it uses only stable processes. The description is what the page builder computes for all complete processes. It never changes a word of the rule.
- **Flag of a session**: the result of one session for one hypothesis in the analysis script, for example `fail` when the bounded prediction failed.
- **Open item**: a text of the box "Open for the user" of the generated page. It gives two readings of a result and leaves the choice to the user.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Huge-page coverage**: `kB_huge` of `kB_total` of a `P` row. It is full when the two are equal.
- **Case (a)**: a result of step B4 that contradicts H3a: one CPU has at least 10 low and at least 10 high intervals with full coverage [Ref2].
- **Position effect**: the rate of a loop depends on the loop that ran directly before it in the sequence.
- **Analysis script**: the file `analyze_bwx.py`. The page builder imports its parser and its decision rules [Ref5].
- **`D`**: the dictionary with all computed values of a page. The function `make` of the page builder returns it with the page text.
- **`T`**: the short name under which this file imports `test_analyze_bwx.py`.
- **Visible text**: the page text without its style sheet, its tooltips and its tags ({L56-60}).
- **Tooltip**: a text that a browser shows when the mouse pointer is over an element.
- **Docstring**: a text literal at the top of a Python file or function that describes it.
- **UTC**: Coordinated Universal Time.

## Main flow

1. The first lines import the page builder and the row writer of `test_analyze_bwx.py`, and set the banner text, the option `--keep` and the folder for the test files ({L10-21}).
2. Five helpers follow: `folder` writes one invented folder, `page` builds a page from such folders, `word` finds one row of the hypothesis table, `visible` gives the visible text, and `near` compares two numbers ({L24-64}).
3. `strong_session` writes the three folders of a session in which the predictions of H1, H3a and H4 fail ({L69-74}).
4. Two tests cover the words over the sessions: one session never gives "rejected" ({L77-95}), and the two readings of H3a stand side by side ({L98-116}).
5. Three tests cover the level limits: a case near a limit is marked ({L119-135}), a process that is not stable is described and not decided ({L138-162}), and a size without a level uses every process ({L165-171}).
6. One test covers the position effect of step B6 ({L174-212}).
7. Three tests cover the page state, the counters and missing data: the counter increases and level changes of B4 ({L215-243}), the observation on the two refill counts ({L246-270}), and missing steps with Part D ({L273-284}).
8. Two tests cover the section on the system load ({L287-314}) and the columns and markers of tables and charts ({L317-328}).
9. `check_page_rules` holds the page rules that a script can check. One test applies them to three kinds of input, and then tests that the command line writes a page that holds the banner ({L331-361}).
10. Two tests run on the real result folders when they exist: session 1 alone ({L364-388}) and both sessions ({L391-418}).
11. The start of the script runs every function whose name starts with `test_`, in the order of the names, removes the temporary folders and prints the counts ({L421-431}).

## Behavior a reader must know

- Every rate of the first twelve tests is invented. Their pages carry a banner that says so ({L18}). These tests prove what the page builder does with given rows. They prove nothing about CRB.
- A test fails through an `assert`. The first failed `assert` stops the script with a Python error. Then the later tests do not run, the temporary folders stay, and the result line of {L431} is not printed.
- The tests run in the order of their names, not in the order of the file ({L422}).
- The two tests on real folders look for a folder `results` two levels above the folder of the page builder, and the second also for two text files in the folder `new-test-kernel` there ({L367}, {L394-397}). In this repo that place is the folder `code`, which has no folder `results`. So both tests take the path that prints the skip line here ({L371-373}, {L400-402}). A skipped test is counted apart and not as passed.
- The expected values of the two tests on real folders are typed into this file ({L381-387}, {L405-417}). This page reports them as what the test expects, not as results.
- The import of {L15} needs the page builder, and the page builder needs `analyze_bwx.py` at a path of the working tree. In this repo that path does not exist, so the import works only when the folder of `analyze_bwx.py` is on the module search path of Python in another way.
- Some comparisons cannot fail. Both texts of {L153}, the first text of {L112} and the first text of {L162} stand on every page. The first text of {L268} stands on no page, and the test asks that it is absent.
- No invented folder holds a process of the steps B2, B3 or C2. So the sections of B2 and B3 with data, a word of the rule for H5 and H6, and the comparison of the two copy loops in step C2 run only in the two tests on real folders.
- `page` calls `M.make` with the default path of the file of loop offsets. No test looks at the table of loop offsets.
- Without `--keep` the test writes only below a new temporary folder and removes it at the end ({L20}, {L428-429}). With `--keep DIR` the invented folders and all pages stay in `DIR`.
- The file does not set an exit status itself. Python ends with status 0 after the last line, and with a status other than 0 after an error.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/plan.md`: the test plan of 2026-11-13: the question Q1, the table of the hypotheses, the rules 3, 4, 5, 10 and 11, and the table of the steps B1 to B6.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the handoff note: section B.3 (the rows `I`, `T`, `P` and `C`), section B.9 (the sequences of the steps) and section B.10 (the numeric decision rules, with the cases of step B4).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/partBC-analysis/make_q1_html.py`: the page builder under test. The tests call its functions `make`, `main`, `short_version`, `sec_b4` and `dumbbell`, its class `Refs`, and read its values `TD`, `TE`, `WORDS5` and `CRB`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/test_analyze_bwx.py`: the row writer `block`, the block builders `b1`, `b4` and `b6`, the rate functions `copy_rate` and `b6_rate`, and the sequences `B1SEQ` and `B6SEQ`.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/analyze_bwx.py`: the analysis script: the parser and the decision rules whose words the page prints.
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/results.md`: the result note of the test. Its list "Words used here" defines the lead as the agent that executed the handoff.
