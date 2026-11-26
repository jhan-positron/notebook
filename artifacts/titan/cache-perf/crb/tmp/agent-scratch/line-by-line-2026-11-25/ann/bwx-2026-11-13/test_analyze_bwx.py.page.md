## Short version: purpose

`test_analyze_bwx.py` holds 28 tests of the analysis script `analyze_bwx.py`. Each test writes csv files with invented rates in the row format of the runner `bwx`, runs the analysis on them, and checks one decision rule or one part of the output. No test uses a measurement, so a passed test says something about the analysis and nothing about CRB.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D [Ref2].
- **Handoff note**: the file `handoff.md`. It tells how to execute the plan. Its section B.3 gives the rows of the result files, and its section B.10 gives the decision rules in words [Ref1].
- **Deviations note**: the file `DEVIATIONS-scripts.md` in the folder of this file. Its points A1 to A33 say where the analysis adds to the handoff note or differs from it [Ref3].
- **Analysis**: the script `analyze_bwx.py`. This file imports it under the name `ab`.
- **Test**: one function of this file whose name starts with `test_`. It holds one or more checks.
- **Check**: one `assert` line. It stops the run with an error when its condition is false.
- **Block**: the text of one invented process: a header line and the rows of the runner after it. The function `block` builds it.
- **Step**: one named batch of processes of the plan, for example `B1` or `C3`. `SHORT` is a short trial run of every sequence.
- **Session, in Parts B and C**: one run of all steps. The plan asks for 2 sessions some hours apart. This is not the session of the later rerun.
- **Sequence, entry**: the sequence is the ordered list of kernels that one process times (option `--seq`). An entry is one element of it: a kernel name, or a kernel name with a size, as in `oldread@1M`.
- **Header line**: the line that the run script `run_bwx.sh` writes before each process. It starts with `-- step` and holds the step, the tag, the binary, the wait, the load record, the number of logins, the time and the arguments.
- **Tag**: the name that the run script gives to one process.
- **`I` row, `T` row, `P` row, `C` row**: the four kinds of data rows of the runner. `I`: one row per interval. `T`: one row per thread and interval, with the bytes and the times of the thread. `P`: the page state of one buffer. `C`: the counter values of one thread in one interval.
- **Elapsed time**: the column `elapsed_s` of a `T` row: the time between the clock reading of the thread before its first kernel call of the interval and its clock reading after the last.
- **`M_hist`**: a total rate of an interval: the bytes of all threads, divided by the longest elapsed time of a thread.
- **`M_sum`**: a total rate of an interval: the sum of the rates of the threads. Each thread is divided by its own elapsed time.
- **`q`**: the rate of the thread at the 10th percentile divided by the rate of the thread at the 90th percentile, in one interval. A value near 1 means that all threads have nearly the same rate.
- **Pattern: split, uniform, mixed**: the label of an interval with many threads. Split is a `q` below 0.65, and uniform is a `q` above 0.85. A thread count is mixed unless all its intervals have the same one of these two labels.
- **A/A pair**: one loop that exists in the binary twice, under two names, for example `asmread` and `asmread2`.
- **A/A spread**: the largest absolute A/A difference of a group of processes. It is never negative.
- **Reference interval**: an interval of `asmread` that is timed directly before or after a compared interval, to show the level at that time.
- **Level: low, high**: the label of a rate of `asmread` with one thread and a buffer of 8 MiB. Low is below 69 GB/s, and high is above 70.5 GB/s. The two limits are provisional.
- **Process value, `d`, `e`**: one number per process. In a step with one thread, `d` is the median of the differences between the compared kernel and its partner, and `e` is the median of the A/A differences of the same process.
- **`D`, `E`**: the two process values of a step with many threads. `D` is the difference between two kernels. `E` is the A/A difference of the same process.
- **Setting**: one combination of the timing options of a step with many threads: the stop method, the interval length in ms and the start method, written as in `pass/500/common`.
- **Reproduction condition**: the setting `pass/500/common` of step B7: whole passes, 0.5 s and the common start [Ref2].
- **Resolved**: the word for a difference that is larger than the A/A spread and has one sign in all processes.
- **Not resolved**: the word for a difference that lies inside the A/A spread, or whose sign changes between the processes.
- **Not observed**: the word for a case with too few processes for a decision, or for an event that did not occur.
- **Hypothesis, H1 to H11**: a possible explanation that the plan names, with a label such as H4. Each one makes a bounded prediction that one step tests [Ref2].
- **Flag of a session**: the result of one session for one hypothesis: `fail` (the prediction failed), `hold`, `not observed` or `not resolved`.
- **Late thread**: a thread whose `T` row has the flag `late`.
- **End skew**: the latest end time of a thread minus the earliest end time, inside one interval.
- **Irregular interval**: an interval with a late thread, or, with the common stop, with an end skew above 5 ms. It is listed and not used for a decision.
- **Coverage: full, none, partial**: the share of a buffer that lies on huge pages, read from a `P` row.
- **Bracket**: in step B8, the two counts of mesh-1 threads between which the pattern of a kernel changes from split to uniform.
- **Spread of a kernel**: in step B10, the highest minus the lowest `M_hist` of the intervals of one kernel in one process.
- **Control**: in step B10, the largest absolute A/A difference of one setting: one for the spread, one for the total rate and one for the rate of each mesh.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Docstring**: a text literal at the top of a Python file, class or function that describes it.
- **JSON**: a text format for nested lists and dictionaries.

## Main flow

1. The file imports the analysis and defines the sequences of the steps B1, B6, B7, B8, B5 and B10 as texts ({L8-19}).
2. The helpers follow. `block` builds the text of one process from a rate function, and `analyze` writes such texts to csv files in a temporary folder and runs the analysis on them ({L22-102}).
3. Tests of the steps with one thread: the parsing and the processes left out, four tests of step B1, one test each of the steps B6 and B3, and two tests of step B4 ({L107-269}).
4. Tests of the steps with 120 threads: four tests of step B7, then the brackets of B8, the answer of B5, the pattern of B9, the words without labels, and the spread and H11 of B10 ({L274-509}).
5. Tests of the counter rows, of the step SHORT, of the words over two sessions and of the command line with its output files ({L514-567}).
6. Six tests that were added after the review: the preconditions of H7 and H6, the disagreement of the two metrics in three places, and the counter tables ({L571-668}).
7. `main` runs every test in the alphabetical order of the test names, deletes the temporary folder and prints the result line ({L671-683}).

## Behavior a reader must know

- Every rate, time and counter value in the tests is invented. A rate function gives the rate of each thread, and `block` computes the bytes as rate times 1e9 times elapsed time ({L53}).
- `block` writes the rows that the analysis reads. It does not model the runner in every detail: the planned start equals the real start with both stop methods ({L55}), and the system counters of the `P` rows never change ({L43}).
- A failed check ends the whole run with a Python error and exit status 1. The later tests do not run then. The temporary folder is deleted in every case ({L673-678}).
- The tests run in the alphabetical order of their names, not in the order of the file ({L672}). No test reads a file of another test.
- Every call of `analyze` also turns the summary into JSON and builds the text table of each step ({L94-97}). So these two output paths are exercised by every test.
- The import of the analysis also imports `decide.py` ({L11}). In the code repo that file lies in the folder `new-test-kernel` beside this folder, where the analysis does not look for it. So in the repo layout the tests start only when the environment variable `DECIDE_DIR` names that folder.
- In `test_b4_cases` the variable `other` is set and never used ({L247}).
- The check of {L128} has two halves that are joined with `or`. With the input of the test only the second half is true.
- The deviations note records one trial of the first 20 tests: the analysis was changed in 16 ways, one at a time, and 15 of the changes made a test fail. The change that no test saw removed the check that two reference intervals are 3 positions apart [Ref3].

## References

- [Ref1] The handoff note: the file `tests/2026-11-13-new-read-kernel/report/handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Rule 4 of the rules for the machine: the system load is reported in every result. Section B.3: the fields of the `I`, `T`, `P` and `C` rows. Section B.6: the first page reading of a process with many threads has the position -1. Section B.9: the sequence and the options of each step. Section B.10: the decision rules.
- [Ref2] The plan: the file `tests/2026-11-13-new-read-kernel/report/plan.md` of the same repo. The table of the hypotheses, the rules 4, 5, 10 and 11, and step B7 with its reproduction condition.
- [Ref3] The deviations note: the file `code/bwx-2026-11-13/DEVIATIONS-scripts.md` of the same repo. Table "Analysis": the points A1 to A33. Section "What the tests cover": the number of tests, and the trial with 16 changed copies of the analysis.
