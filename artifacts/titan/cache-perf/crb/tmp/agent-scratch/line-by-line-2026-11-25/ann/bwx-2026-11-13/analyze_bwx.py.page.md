## Short version: purpose

`analyze_bwx.py` reads the result files that the runner `bwx` wrote in Parts B and C of the test plan of 2026-11-13. For each step and each session it computes rates and differences from the rows of the threads, and it applies the decision rules of the handoff note, most of them through the functions of `decide.py`. It prints one text table per step and one word per hypothesis of the plan, and with `--out` it also writes these texts and a summary in JSON to a folder.

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
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D [Ref2].
- **Parts B and C**: two parts of the plan. Part B holds the deciding measurements with the runner `bwx`. Part C repeats some of them with counters. They are not the parts of the later rerun.
- **Handoff note**: the file `handoff.md`. It tells how to execute the plan. Its section B.3 gives the rows of the result files, and its section B.10 gives the decision rules in words [Ref1].
- **Deviations note**: the file `DEVIATIONS-scripts.md` in the folder of this script. Its points A1 to A33 say where the analysis adds to the handoff note or differs from it [Ref3].
- **`decide.py`**: the file that holds the decision rules of section B.10 as Python functions [Ref4].
- **Local rule**: a decision rule that is coded in this file, where `decide.py` has no function for it.
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
- **Pattern: split, uniform, between**: the label of an interval with many threads. Split is a `q` below 0.65, uniform is a `q` above 0.85, and between is the rest. The two limits are provisional.
- **A/A pair**: one loop that exists in the binary twice, under two names, for example `asmread` and `asmread2`.
- **A/A difference**: the difference between the rates of the two copies of an A/A pair. It shows how much two equal loops differ.
- **A/A spread**: the largest absolute A/A difference of a group of processes. It is never negative.
- **Reference interval**: an interval of `asmread` that is timed directly before or after a compared interval, to show the level at that time.
- **Level: low, high, changing**: the label of a rate of `asmread` with one thread and a buffer of 8 MiB. Low is below 69 GB/s, high is above 70.5 GB/s, and changing is every rate from 69 to 70.5 GB/s. The two limits are provisional.
- **Stable process**: a process whose reference intervals all have the label low, or all have the label high.
- **Pair value**: the rate of one kernel minus the rate of the other in two neighbouring intervals, in GB/s.
- **Process value, `d`, `e`**: one number per process. In a step with one thread, `d` is the median of the pair values of the kernel comparison, and `e` is the median of the pair values of the A/A comparison.
- **`D`, `E`**: the two process values of a step with many threads. `D` is the difference between two kernels. `E` is the A/A difference of the same process.
- **Setting**: one combination of the timing options of a step with many threads: the stop method, the interval length in ms and the start method, written as in `pass/500/common`.
- **Resolved**: the word for a difference that is larger than the A/A spread and has one sign in all processes.
- **Not resolved**: the word for a difference that lies inside the A/A spread, or whose sign changes between the processes.
- **Not observed**: the word for a case with too few processes for a decision, or for an event that did not occur.
- **Hypothesis, H1 to H11**: a possible explanation that the plan names, with a label such as H4. Each one makes a bounded prediction that one step tests [Ref2]. The rows of the function `cross` give the prediction of each hypothesis that this script handles.
- **Flag of a session**: the result of one session for one hypothesis: `fail` (the prediction failed), `hold`, `not observed` or `not resolved`.
- **Copy difference**: what question Q1b of the plan asks about: with one thread and a buffer of 8 MiB, a lower rate of the new C copy kernel than of the assembly copy kernel [Ref2].
- **Read difference**: what question Q2a of the plan asks about: with 120 threads, a higher total rate of the old read kernel than of the new read kernel [Ref2].
- **Late thread**: a thread whose `T` row has the flag `late`. With the common stop it started more than 100 us after the planned common start.
- **End skew**: the latest end time of a thread minus the earliest end time, inside one interval.
- **Irregular interval**: an interval with a late thread, or, with the common stop, with an end skew above 5 ms. It is listed and not used for a decision.
- **Coverage: full, none, partial, unknown**: the share of a buffer that lies on huge pages, read from a `P` row.
- **Bracket**: in step B8, the two counts of mesh-1 threads between which the pattern of a kernel changes from split to uniform.
- **Spread of a kernel**: in step B10, the highest minus the lowest `M_hist` of the intervals of one kernel in one process.
- **Control**: in step B10, the largest absolute A/A difference of one setting: one for the spread, one for the total rate and one for the rate of each mesh.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Docstring**: a text literal at the top of a Python file, class or function that describes it.
- **JSON**: a text format for nested lists and dictionaries.

## Main flow

1. The script finds and imports `decide.py`, and it sets its constants: the CPUs of mesh 0, the limits for an irregular interval and for the pattern labels, and the regular expression for a header line ({L22-40}).
2. `main` reads the options: one or more `--session` with a name and paths, and `--out` ({L1075-1083}).
3. For each session `load_session` reads every csv file. `read_csv` makes one `Proc` per header line and passes every data row to it ({L194-223}, {L95-167}).
4. At the end of a file each `Proc` computes the values of its intervals from the `T` rows: the rate of each thread, `M_hist`, `M_sum`, the values per mesh, the end skew, `q` and the pattern. Then it decides whether the process is complete ({L63-89}, {L169-185}).
5. `analyze` takes the steps of a session in a fixed order and calls the analysis function of each step. Each function first lists the processes used and left out, the irregular intervals and the load ({L1011-1030}, {L849-851}, {L237-252}).
6. Steps with one thread: B1, B2 and B3 compare a copy kernel with `asmcopy` per CPU, B6 compares the old read kernel between levels and between sizes, and B4 counts intervals per level and coverage ({L327-440}).
7. Steps with many threads: B7 decides the difference `D` between old read and new read per setting and its change between settings, B10 does the same for the spread of the write kernels and tests H11, B8 builds brackets, and B5 and B9 compare patterns and totals ({L445-784}).
8. The steps C1 to C3 get a description of the counter rows, and the step SHORT gets one line per process. Neither gets a decision ({L789-846}).
9. `cross` joins the results of all sessions into one word per hypothesis ({L856-1003}, {L1031}).
10. `main` builds the text tables, writes them and `summary.json` to the folder of `--out` when it is given, and prints all texts ({L1085-1100}).

## Behavior a reader must know

- Every rate comes from the `T` rows: the column `bytes` (field 7) divided by the column `elapsed_s` (field 8) and by 1e9, in GB/s. The values of the `I` rows are stored and never used ({L137-138}).
- The script reads no clock and times nothing. The time of a thread is the elapsed time that the runner printed.
- `M_hist` divides the bytes of all threads by the longest elapsed time of one thread. `M_sum` adds the rates of the threads. The two differ when the threads have different elapsed times, which the whole-pass stop allows.
- No value is the rate of the time in which all threads ran. The output says so in its list of limits ({L1014}).
- A process gives values only when it is complete: no `-- killed` or `-- failed` line, no problem, and every expected interval with one `T` row per thread ({L181}).
- An irregular interval is listed. A process gives no value for a quantity that needs such an interval ({L458-460}).
- With `--stop pass` an end skew never makes an interval irregular ({L86}). The deviations note marks this as a point that needs a decision of the lead [Ref3].
- Where a decision rule uses process values, a process gives one value, however many intervals it has. This holds for the steps B1, B2, B3, B6, B7 and B10 and for the totals of B5 and B9. Step B4 counts single intervals ({L420}), and the pattern labels of B8, B5 and B9 are given per interval. In the steps with one thread, values of different CPUs are never put into one group.
- The decision metric is `M_hist`. When `M_sum` gives another word or another sign for `D`, the result is `not resolved` ({L480-486}). For a change of `D` between two settings only the words are compared: those records hold no sign ({L543}).
- The limits 69 and 70.5 GB/s (level), 0.65 and 0.85 (pattern), 100 us and 5 ms (irregular interval) are provisional. The output says so ({L1016}).
- By a decision of the user the pattern labels are not used [Ref5]. The script still computes them. The entries for H8, H9a and the statement of step B5 hold a second word without labels ({L1006-1008}).
- The names of the five counts of a `C` row are assigned by position ({L789}, {L813}).
- The docstring of `a_copy` names step C2, but the table of {L849-850} gives C2 to `a_count`.
- The script ends with a Python error when a header line does not fit the pattern, when a folder holds no csv file, or when `decide.py` is not found. A wrong command line gives exit status 2. A normal end gives exit status 0.
- In the code repo `decide.py` lies in the folder `new-test-kernel` beside the folder of this file. That is none of the three places of {L26} unless `DECIDE_DIR` names it. So in the repo layout the import needs `DECIDE_DIR`.

## References

- [Ref1] The handoff note: the file `tests/2026-11-13-new-read-kernel/report/handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Section B.1: the kernels of the runner. Section B.2: the options of the runner. Section B.3: the fields of the `I`, `T`, `P` and `C` rows. Section B.4: the two stop methods, the flag `late` and the irregular interval. Section B.5: the start offsets. Section B.6: the page state and when it is read. Section B.8: the counters. Section B.9: the sequence and the options of each step. Section B.10: the decision rules.
- [Ref2] The plan: the file `tests/2026-11-13-new-read-kernel/report/plan.md` of the same repo. The section "The two questions" with the questions Q1b and Q2a, the table of the hypotheses H1 to H11, the rules 3, 4, 5, 6, 8, 10 and 11 for the deciding measurements, and the tables of the steps of Part B and Part C with the prediction that each step tests. The protocol of Part C: a row whose running time is below its enabled time is not used.
- [Ref3] The deviations note: the file `code/bwx-2026-11-13/DEVIATIONS-scripts.md` of the same repo, table "Analysis", points A1 to A33.
- [Ref4] The file `code/new-test-kernel/decide.py` of the same repo: the functions `level`, `process_value`, `resolved`, `decide_one_thread`, `decide_b6_state`, `decide_setting`, `decide_change`, `controls_from_aa` and `decide_h11`.
- [Ref5] The file `tests/2026-11-13-new-read-kernel/report/decisions.md` of the same repo, item 2: the answer "Report q, no labels".
- [Ref6] The source of the runner: the file `code/bwx-2026-11-13/bwx.c` of the same repo. The output loop of `main` prints the rows and the comment lines with the column names. The first comment line says that a copy counts the bytes read plus the bytes written. The constant `LATE_NS` is 100000 ns, and the worker sets the flag `late` only with the common stop. The defaults of the options are in the initial values of `cfg` and in `main` before the option loop.
- [Ref7] The run script: the file `code/bwx-2026-11-13/run_bwx.sh` of the same repo. Its function `one` writes the header line, the line `-- killed` and the line `-- failed`.
