## Short version: purpose

`make_q2_html.py` builds the HTML result page for question Q2 of the test plan of 2026-11-13: why the old read kernel totals more than the new one with 64+56 threads and 256 MiB per thread, and why the write kernels give several separate totals. It takes the result folders that the run script `run_bwx.sh` wrote for the steps B7, B10, B8, B5, B9 and C3, lets the analysis script `analyze_bwx.py` read the rows and apply the decision rules, and adds descriptions, charts and tables. For each of seven hypotheses it prints one of five fixed words, by rule 11 of the plan and by four rules of its own.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Whole chip, 120 threads**: our runs use the CPUs 0 to 119 only: 64 threads on mesh 0 plus 56 threads on mesh 1.
- **a+b threads**: a threads on mesh 0 and b threads on mesh 1. So 64+56 threads are the 120 threads of the whole chip.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Old read, new read, asm read**: the names that the script prints for the kernels `oldread`, `read` and `asmread`. The write kernels `oldwrite`, `write` and `asmwrite` are printed as old write, new write and asm write.
- **A/A control**: one loop that exists twice in the program under two names: `asmread` and `asmread2`, or `asmwrite` and `asmwrite2`. The difference between the two copies shows how much two equal loops differ.
- **`read_sparse`, `read_nop4` to `read_nop32`**: load-only read loops of step B5 with added `nop` instructions. A `nop` is an instruction that does nothing.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **Pass**: one sweep of a thread over its whole buffer. The column `passes` of a T row is the bytes of the thread divided by the size of the buffer.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It names two questions, the hypotheses H1 to H11, eleven rules for the measurements, and the steps of its Parts A to D [Ref1].
- **Handoff**: the file `handoff.md`, the instructions for the execution of the plan. Its section B.3 defines the rows that the runner prints. Its section B.10 defines the decision rules [Ref2].
- **Parts A, B, C and D of the plan**: Part A is a screening with the older benchmark binaries. Part B uses the runner `bwx`. Part C repeats steps with core counters. Part D needs root rights. On this page these names have this meaning.
- **Q2**: the second question of the plan, about 64+56 threads with one 256 MiB buffer per thread. Q2a asks why the old read kernel has a higher total than the new one. Q2b asks why the write kernels give several separate totals.
- **Q1**: the first question of the plan, about one thread with an 8 MiB buffer. Another script builds its page.
- **Step**: one measurement of the plan. Each call of the run script for a step writes one result folder.
- **B7**: step: `oldread`, `read`, `asmread` and `asmread2` at 64+56 threads in all 8 settings, 4 processes per setting, and the reproduction condition with one kernel per process.
- **B10**: step: `oldwrite`, `write`, `asmwrite` and `asmwrite2` at 64+56 threads in 8 settings. The run script splits it into the calls `B10a` and `B10b`, so it has two result folders.
- **B8**: step: `oldread`, `asmread` and `asmread2` with 64 threads on mesh 0 and several thread counts on mesh 1.
- **B5**: step: `oldread` against `read`, `read_sparse`, the four `nop` variants and `asmread`, at 64+56 threads. It tests whether a loop without vector adds can show the total of old read.
- **B9**: step: `oldread` alone, with one buffer and with two buffers per thread.
- **C3**: step: the sequences of B7 and B5 with core counters.
- **D1**: step of Part D with the counters of the mesh, which need root rights.
- **H7a**: hypothesis: the stop method and the short interval make a part of the read difference of Q2a and of the separate write totals of Q2b.
- **H7b**: hypothesis: the common start makes a part of the same two effects.
- **H8**: hypothesis: with threads on both meshes the chip has two states, split and uniform. A loop that only loads reaches the uniform state at a lower thread count than old read.
- **H9a**: hypothesis: the second buffer per thread moved old read to the uniform pattern on 2026-10-30.
- **H9b**: hypothesis: the pattern of old read differs between days or sessions for a reason other than the kernel.
- **H10**: hypothesis: in the uniform state the memory system fetches lines that the loop does not consume.
- **H11**: hypothesis: the write totals differ, and the cause is that the threads of one mesh run faster in some intervals.
- **B5 statement**: the statement that step B5 of the plan tests: vector adds are needed for the split pattern of old read at 64+56 threads [Ref1]. The script words it as "vector adds are needed for the pattern and total of old read" ({L611}).
- **Bounded prediction**: the one measurable statement of a hypothesis that a step tests.
- **Session of Parts B and C**: one run of all steps of Parts B and C. Rule 10 of the plan asks for at least 2 sessions some hours apart. On this page "session" has this meaning.
- **Visit**: one login to CRB that runs one or more steps.
- **Run script**: the file `run_bwx.sh`. For each step it starts the processes on CRB and writes the result folder: the csv file of the step, `env.txt`, `launches.txt` and `stderr.txt` [Ref6].
- **Header line**: the line that the run script writes into the csv file before each process. It starts with `-- step` and holds the step, the tag, the binary, the waited seconds, four fields of `/proc/loadavg`, the number of logins, the time of day in UTC and the arguments of the runner.
- **Tag**: the name of a process in the run script, for example `pass-500-common-p1`.
- **`env.txt`**: a file of the result folder with one reading of the machine state before the first process of the step and one after the last.
- **`launches.txt`**: a file of the result folder with one more load reading and the 5 busiest processes before each process.
- **T row**: a row of the csv file for one thread and one interval. Its fields are `T`, round, position, kernel, thread number, CPU, bytes, `elapsed_s`, `t_sched_s`, `t_start_s`, `t_end_s`, `passes` and the flag (`-` or `late`).
- **P row**: a row with the page state of one buffer: its size `kB_total` and its part on 2 MiB pages `kB_huge`, both in kB, or `NA`. 2 MiB pages are memory pages that Linux can use for a buffer in place of its smaller standard pages.
- **C row**: a row for one thread and one interval of a run with counters: the enabled time and the running time of the counter group, the CPU time of the thread, all in ns, and the counter values.
- **I row**: a row with the rounded total of one interval. The analysis does not use its total.
- **Thread rate**: the bytes of one T row divided by its `elapsed_s`, in GB/s.
- **Total, `M_hist`**: the bytes of all threads of one interval divided by the longest `elapsed_s` of a thread, in GB/s. It is the decision metric.
- **`M_sum`**: the sum of the thread rates of one interval, in GB/s. It is a second metric beside `M_hist`.
- **Mesh value**: the bytes of the threads of one mesh divided by the longest `elapsed_s` of all threads of the interval, in GB/s.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one interval. With 120 threads these are the 12th and the 108th smallest rate.
- **Pattern labels**: the labels `split` (q below 0.65) and `uniform` (q above 0.85) that the handoff gives an interval. By decision 2 of the user of 2026-11-13 they are not used [Ref3].
- **Setting**: one combination of stop method (`pass` for the whole-pass stop, `common` for the common stop), shortest interval length in ms, and start. It is written as in `pass/500/common`.
- **Timing factor**: one of the three parts of a setting: the stop method, the interval and the start.
- **Common start, offset start**: with the common start every thread starts its pass at the start of its buffer. With the offset start every thread starts at its own offset inside its buffer.
- **Reproduction condition**: the setting `pass/500/common`. By the plan it is the timing method of the benchmark run of 2026-11-13 that raised question Q2.
- **2 % check**: rule 7 of the plan for the whole-pass stop: one pass may take at most 2 % of the interval. So each thread needs at least 50 passes.
- **Late, end skew**: a thread is late when it starts more than 100 microseconds after the common start time. The runner then sets the flag `late` in its T row. The end skew of an interval is the latest `t_end_s` minus the earliest.
- **Irregular interval, regular interval**: an interval is irregular when a thread is late, or when the process uses the common stop and the end skew is above 5 ms. Every other interval is regular. An irregular interval is not used.
- **Complete process**: a process in whose rows the analysis found no problem: no line `-- killed` or `-- failed`, every expected interval, and one T row per thread in each interval. Only complete processes are used.
- **Process value**: one number per process. Decisions use process values, never single intervals.
- **D**: the total of old read minus the total of new read. For one process it is the mean over its rounds of the mean total of its old read intervals minus the mean total of its new read intervals.
- **E**: the same value as D for the A/A control: `asmread2` minus `asmread`.
- **A/A spread**: the largest absolute E over the processes of one setting.
- **Resolved**: D of a setting is resolved when its absolute median over the processes is above the A/A spread and every D has the same sign. A setting needs 4 processes with a value.
- **Limit of a change**: the sum of the A/A spreads of the two compared settings. A change between two settings is resolved when it is above its limit and the values of the two settings do not overlap.
- **Spread (B10)**: for one write kernel in one process, the highest minus the lowest total of its 4 intervals.
- **Controls (B10)**: three values of one setting from the A/A control of the write kernels: the control of the spread, of the total, and of the rate of each mesh.
- **Cell (B10), counted process**: a cell is one write kernel in one setting. A process counts for H11 only when its highest and its lowest total of the kernel differ by more than the control of the total.
- **Group (C3)**: one setting and one sequence. The analysis forms the medians of the counter values per group, kernel and mesh.
- **The five words**: the words that rule 11 of the plan allows for a result: `rejected`, `not rejected`, `not observed`, `not resolved` and `not tested`.
- **Flag**: the result of one session for a bounded prediction: `fail` (it failed), `hold` (it held), `not observed` or `not resolved`.
- **Page rules 1 to 4**: four rules of this script for the words of H8, H9a, H9b, H10, H11 and the B5 statement. They are not rules of the plan ({L11-20}).
- **Analysis script, `A`**: the file `analyze_bwx.py`. It reads the csv files and applies the decision rules of the file `decide.py` [Ref5].
- **`PA`**: the file `make_partA_html.py`, the generator of the Part A page. This script takes number formats, colors and the page style from it [Ref8].
- **Summary**: the result of the analysis script: the decisions per session and step, and one entry per hypothesis.
- **Model**: the dictionary of computed values that `compute` returns and from which `build` writes the page.
- **Generated page**: the HTML file that this script writes.
- **Typed text**: text that stands in the script as it is. The script does not compute it from the input.
- **Tooltip**: a text that the browser shows when the mouse pointer is over a marker of a chart.
- **Anchor name**: the `id` of a heading. A link can jump to the heading by this name.
- **Highlighted paragraph**: a paragraph of the class `take` or `miss`. The page style gives it a colored background.
- **Caption**: a paragraph of the class `cap`, in smaller grey text below a chart or a table.
- **Folded block**: an HTML `details` element. The browser shows only its summary line until the reader opens it.
- **Insufficient data box**: the paragraph that the function `missing` returns. It starts with the bold words `Insufficient data.` and names what is missing.
- **Offsets file**: the file `offsets.tsv` of a build of `bwx`. Each line gives a binary, a kernel, a function, two addresses and the address of the loop start modulo 64 [Ref10].
- **Unix time**: the seconds counted from 1970-01-01 00:00 UTC.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **`ps`**: the Linux tool that lists processes. The run script uses it to list the processes with the highest CPU share.
- **HTML, CSS, SVG**: HTML is the text format of a web page. CSS is the language that sets its look. SVG is a picture format that is written as text.

## Main flow

1. `main` reads the command line: one or more `--session` options, each with a session name and result folders, the name of the output file, an optional banner text and the path of the offsets file ({L1867-1878}).
2. `compute` reads every csv file of the folders with the reader of the analysis script and keeps the processes of the six steps of Q2 ({L698-707}).
3. The analysis script decides every step and every hypothesis from these processes ({L708}).
4. `compute` adds its own values per session: the load readings, the times of the sessions, and for each step the medians of the total, of q and of the thread rates per mesh ({L709-737}).
5. `hypotheses` turns the results into one row per hypothesis with one of the five words, by rule 11 of the plan and by the four page rules ({L438-695}).
6. `build` writes the page: the Short version, the list of words, the hypothesis tables, the decisions and settings, the system load, the processes used, and one section per step with charts and tables ({L1796-1861}).
7. `build` adds the list of the cited references and moves each reference index in front of the full stop of its sentence ({L1862-1864}).
8. `main` writes the page to the output file and prints the word of each hypothesis ({L1879-1885}).

## Behavior a reader must know

- Where the numbers come from: every rate comes from the T rows of the csv files. A thread rate is `bytes` divided by `elapsed_s` of one row ({L110}). The total `M_hist` is the sum of `bytes` of all threads of an interval divided by the longest `elapsed_s`. The rounded total of the I row is not used [Ref5].
- What is timed: in the runner a thread reads the clock directly before its first timed kernel call and directly after its last one. The warm-up pass and the waits lie outside [Ref7].
- What ends a timed interval: with the whole-pass stop a thread reads the clock after each whole pass over a 256 MiB buffer and ends when the minimum time has passed, so the threads end at different times. With the common stop it reads the clock after each 2 MiB chunk and ends when the common deadline has passed. It counts the bytes of the passes or chunks that it finished [Ref7].
- How values are combined for a decision: one value per process. D of a process is a mean over its rounds. A setting is decided from the median D of its processes against the A/A spread. A change between two settings is decided against the sum of two A/A spreads ({L469-470}).
- How values are combined for a description: the charts and tables of q, of the thread rates per mesh and of the totals put the regular intervals of all processes into one list and give its median or its range ({L117-123}, {L258}).
- An irregular interval is left out of the descriptions of the totals, of q and of the thread rates ({L126-127}). The counter values of C3 are not filtered in this way: `c3_model` and the function `a_count` of the analysis script do not test whether the interval of a C row is irregular ({L353-358}). A process with an irregular interval gives no D. A setting with fewer than 4 processes with a value is `not observed`.
- The words of H7a and H7b: the flag of each session comes from the analysis script ({L465}, {L508}). For the B5 statement this script sets the flags itself ({L616-630}). `word_of` gives `rejected` only when at least 2 sessions all say `fail`. With one session the flags `fail` and `hold` both give `not rejected` ({L391-399}).
- The pattern labels decide nothing on this page. H8 and H9a are `not resolved` whenever the input holds their step, and `not tested` without it. The B5 statement is decided by the totals alone ({L604}, {L658}, {L624-629}).
- H9b is decided by a rule of this script that the user has not approved, as the script itself says: `not observed` when the ranges of q of old read overlap between the sessions ({L672-673}).
- H10 is `not tested` in every case ({L691}).
- H11 with one session: every cell whose result is not `not observed` counts as `not rejected`, also a cell that is `contradicted` or `not resolved`. The page then prints `not rejected` with the plan word `supported` ({L549}, {L583}). A cell with a result in 2 or more sessions needs the same result in every one of them. A cell with a result in one session only is treated as in the one-session case, also on a page with two sessions. A cell has a result in one session only when the other session has no complete process of that setting.
- The setting for the later steps: `chosen` takes the setting with the common stop and a resolved D that has the largest absolute median D. The second case of the handoff, D resolved only with the whole-pass stop, is not coded ({L270}, {L1066}).
- Typed text that states facts about the runs: the sentences on the level limits ({L1057-1059}), on Part A ({L1098}), on the steps of Q1 and the build option of `bwx_o52` ({L1101-1103}), on the totals of 2026-11-13 ({L1807}), on the short run ({L1845}), the loop offsets in the limits ({L1855}), the thread counts in the Short version ({L1783}) and in the word list ({L1752}), and the words `That reading is met` ({L1127}). They do not change with the input. The description of the script names fewer kinds of typed text ({L23-24}).
- Fixed limits in the code: 50 passes for the 2 % check ({L261}), 10 % of one CPU for a process of another account ({L178}), 30 s for one start time of the machine ({L247}), 60 s for a pause before a folder ({L1186}), and 3600 s for a short gap between sessions ({L1125}).
- Paths: `BWX_DIR` and the reference texts are built from the folder two levels above the script. They fit the working folder on the agent server [Ref4]. In the code repo the analysis script lies in another folder, so `BWX_ANALYSIS_DIR` must be set ({L31}).
- Files: the script only reads the result folders and the offsets file. It writes one file, the page, and replaces an existing file of that name ({L1880-1881}).
- Errors: a folder without a csv file, or a header line that the analysis script cannot read, stops the script with a Python error. A wrong command line ends it with exit status 2 ({L1877}). A missing step does not stop it: the section of the step then shows `Insufficient data` ({L996-997}).
- A reference index of the generated page is not a reference of this explanation page. The generated page numbers its references in the order of their first citation ({L942-943}).

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/plan.md`: the plan: the two questions, the hypotheses, the rules 1 to 11 and the tables of the steps.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the handoff: section B.3 (output rows), B.4 (stop methods, late thread, irregular interval), B.9 (sequences, settings after B7) and B.10 (decision procedure).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/decisions.md`: the decisions of the user of 2026-11-13. Decision 2 says to report q without labels.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/results.md`: the result handoff. Its section "Files" gives the folders of the scripts and of the result folders on the agent server.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/analyze_bwx.py` and `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/decide.py`: the reader of the csv files and the decision rules. The classes `Interval` and `Proc`, and the functions `a_b7`, `a_b10`, `a_b8`, `a_b5`, `a_b9`, `a_count`, `two_sessions` and `cross`.
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/run_bwx.sh`: the run script. The function `one` writes the header line and the block of `launches.txt`. The loop at the end of the file writes `env.txt`.
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/bwx.c`: the runner. The function `worker` holds the clock readings, and `main` prints the rows I, T, P and C.
- [Ref8] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/partA-analysis/make_partA_html.py`: the functions `fx`, `fs`, `pl` and `svg_open`, the colors and the text `CSS`.
- [Ref9] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-scripts.md`: the choices of the analysis, A1 to A33.
- [Ref10] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/offsets.tsv`: an offsets file with its heading line and six columns.
