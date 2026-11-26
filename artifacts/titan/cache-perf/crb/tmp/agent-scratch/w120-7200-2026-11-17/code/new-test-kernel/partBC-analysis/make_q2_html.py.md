# `make_q2_html.py` explained, line by line

- Source file: `new-test-kernel/partBC-analysis/make_q2_html.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1889 lines, 156681 bytes).
- sha256 of the source when this page was built: `e821de3e888f21fd259542972dacb27d920c2784620c16ba9b51d4980582c42e`.

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
- **B5 statement**: the statement that step B5 of the plan tests: vector adds are needed for the split pattern of old read at 64+56 threads [Ref1]. The script words it as "vector adds are needed for the pattern and total of old read" (line 611).
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
- **Page rules 1 to 4**: four rules of this script for the words of H8, H9a, H9b, H10, H11 and the B5 statement. They are not rules of the plan (lines 11 to 20).
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

1. `main` reads the command line: one or more `--session` options, each with a session name and result folders, the name of the output file, an optional banner text and the path of the offsets file (lines 1867 to 1878).
2. `compute` reads every csv file of the folders with the reader of the analysis script and keeps the processes of the six steps of Q2 (lines 698 to 707).
3. The analysis script decides every step and every hypothesis from these processes (line 708).
4. `compute` adds its own values per session: the load readings, the times of the sessions, and for each step the medians of the total, of q and of the thread rates per mesh (lines 709 to 737).
5. `hypotheses` turns the results into one row per hypothesis with one of the five words, by rule 11 of the plan and by the four page rules (lines 438 to 695).
6. `build` writes the page: the Short version, the list of words, the hypothesis tables, the decisions and settings, the system load, the processes used, and one section per step with charts and tables (lines 1796 to 1861).
7. `build` adds the list of the cited references and moves each reference index in front of the full stop of its sentence (lines 1862 to 1864).
8. `main` writes the page to the output file and prints the word of each hypothesis (lines 1879 to 1885).

## Behavior a reader must know

- Where the numbers come from: every rate comes from the T rows of the csv files. A thread rate is `bytes` divided by `elapsed_s` of one row (line 110). The total `M_hist` is the sum of `bytes` of all threads of an interval divided by the longest `elapsed_s`. The rounded total of the I row is not used [Ref5].
- What is timed: in the runner a thread reads the clock directly before its first timed kernel call and directly after its last one. The warm-up pass and the waits lie outside [Ref7].
- What ends a timed interval: with the whole-pass stop a thread reads the clock after each whole pass over a 256 MiB buffer and ends when the minimum time has passed, so the threads end at different times. With the common stop it reads the clock after each 2 MiB chunk and ends when the common deadline has passed. It counts the bytes of the passes or chunks that it finished [Ref7].
- How values are combined for a decision: one value per process. D of a process is a mean over its rounds. A setting is decided from the median D of its processes against the A/A spread. A change between two settings is decided against the sum of two A/A spreads (lines 469 to 470).
- How values are combined for a description: the charts and tables of q, of the thread rates per mesh and of the totals put the regular intervals of all processes into one list and give its median or its range (lines 117 to 123, line 258).
- An irregular interval is left out of the descriptions of the totals, of q and of the thread rates (lines 126 to 127). The counter values of C3 are not filtered in this way: `c3_model` and the function `a_count` of the analysis script do not test whether the interval of a C row is irregular (lines 353 to 358). A process with an irregular interval gives no D. A setting with fewer than 4 processes with a value is `not observed`.
- The words of H7a and H7b: the flag of each session comes from the analysis script (line 465, line 508). For the B5 statement this script sets the flags itself (lines 616 to 630). `word_of` gives `rejected` only when at least 2 sessions all say `fail`. With one session the flags `fail` and `hold` both give `not rejected` (lines 391 to 399).
- The pattern labels decide nothing on this page. H8 and H9a are `not resolved` whenever the input holds their step, and `not tested` without it. The B5 statement is decided by the totals alone (line 604, line 658, lines 624 to 629).
- H9b is decided by a rule of this script that the user has not approved, as the script itself says: `not observed` when the ranges of q of old read overlap between the sessions (lines 672 to 673).
- H10 is `not tested` in every case (line 691).
- H11 with one session: every cell whose result is not `not observed` counts as `not rejected`, also a cell that is `contradicted` or `not resolved`. The page then prints `not rejected` with the plan word `supported` (line 549, line 583). A cell with a result in 2 or more sessions needs the same result in every one of them. A cell with a result in one session only is treated as in the one-session case, also on a page with two sessions. A cell has a result in one session only when the other session has no complete process of that setting.
- The setting for the later steps: `chosen` takes the setting with the common stop and a resolved D that has the largest absolute median D. The second case of the handoff, D resolved only with the whole-pass stop, is not coded (line 270, line 1066).
- Typed text that states facts about the runs: the sentences on the level limits (lines 1057 to 1059), on Part A (line 1098), on the steps of Q1 and the build option of `bwx_o52` (lines 1101 to 1103), on the totals of 2026-11-13 (line 1807), on the short run (line 1845), the loop offsets in the limits (line 1855), the thread counts in the Short version (line 1783) and in the word list (line 1752), and the words `That reading is met` (line 1127). They do not change with the input. The description of the script names fewer kinds of typed text (lines 23 to 24).
- Fixed limits in the code: 50 passes for the 2 % check (line 261), 10 % of one CPU for a process of another account (line 178), 30 s for one start time of the machine (line 247), 60 s for a pause before a folder (line 1186), and 3600 s for a short gap between sessions (line 1125).
- Paths: `BWX_DIR` and the reference texts are built from the folder two levels above the script. They fit the working folder on the agent server [Ref4]. In the code repo the analysis script lies in another folder, so `BWX_ANALYSIS_DIR` must be set (line 31).
- Files: the script only reads the result folders and the offsets file. It writes one file, the page, and replaces an existing file of that name (lines 1880 to 1881).
- Errors: a folder without a csv file, or a header line that the analysis script cannot read, stops the script with a Python error. A wrong command line ends it with exit status 2 (line 1877). A missing step does not stop it: the section of the step then shows `Insufficient data` (lines 996 to 997).
- A reference index of the generated page is not a reference of this explanation page. The generated page numbers its references in the order of their first citation (lines 942 to 943).

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partBC-analysis/make_q2_html.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1889 lines, 156681 bytes, sha256 `e821de3e888f21fd259542972dacb27d920c2784620c16ba9b51d4980582c42e`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description of the script: usage and the four page rules (lines 1 to 25)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""make_q2_html.py --session NAME FOLDER [FOLDER...] [--session NAME FOLDER...] -o PAGE.html [--banner TEXT] [--offsets FILE]` | Starts the description of the script with its usage. Each `--session` gives the name of a session and its result folders. `-o` names the HTML page to write. `--banner` gives a notice text for the top of the page. `--offsets` names the file with the loop addresses. |
| 4 | `Builds one self-contained HTML result page for question Q2 of the plan (64+56 threads at 256 MiB):` | Continues the description: the script builds one HTML page that needs no other file. It is the result page for question Q2 of the plan. Q2 is about 120 threads, 64 on mesh 0 and 56 on mesh 1, each with its own buffer of 256 MiB. It asks why the old read kernel has a higher total rate than the new one, and why the write kernels give several separate totals. |
| 5 | `steps B7, B10, B8, B5, B9 and C3, hypotheses H7a, H7b, H8, H9a, H9b, H10 and H11.` | Continues the description: the page covers six steps of the plan and seven hypotheses. Steps: B7 (the four read kernels at 64+56 threads in 8 timing settings), B10 (the four write kernels in 8 timing settings), B8 (read kernels with fewer threads on mesh 1), B5 (old read against load-only loops with added `nop` instructions), B9 (old read with one and with two buffers per thread), C3 (the sequences of B7 and B5 with core counters). Hypotheses: H7a (the stop method and the short interval make a part of the difference), H7b (the common start makes a part of it), H8 (a loop that only loads reaches the uniform state at a lower thread count than old read), H9a (the second buffer per thread changed the pattern of old read on 2026-10-30), H9b (old read differs between days or sessions for a reason other than the kernel), H10 (the memory system fetches lines that the loop does not consume), H11 (the higher write totals come from the threads of one mesh). |
| 6 | `FOLDER is a result folder of run_bwx.sh. Folders of other steps may be given. Their processes are not used here.` | Continues the description: each `FOLDER` is a result folder that the run script `run_bwx.sh` wrote. Folders of other steps are accepted, and their processes are not used (line 704). Their files `env.txt` are still read for the times of the sessions (line 707). |
| 7 | `The page works with one session. "rejected" then cannot occur, because rule 11 of the plan needs two sessions.` | Continues the description: one session is enough for a page. The word `rejected` cannot occur then. Rule 11 of the plan gives that word only when the prediction failed in two sessions. |
| 9 | `The parser and every decision rule come from analyze_bwx.py (which imports decide.py). This file adds only:` | Continues the description: the code that reads the result files and every decision rule come from the analysis script `analyze_bwx.py`, which uses the rules of `decide.py`. The next lines list what this file adds. |
| 10 | `  - descriptions without a decision (q, median thread rates per mesh, totals of every interval, counters),` | First item of the list: values that describe the data and decide nothing. They are q (the thread rate at the 10th percentile divided by the thread rate at the 90th percentile), the median thread rate of each mesh, the total of every interval, and the counter values. |
| 11 | `  - the mapping of the results to one of the five words of rule 11, with these page rules, all marked on the page:` | Second item: the script maps each result to one of the five words of rule 11 of the plan: `rejected`, `not rejected`, `not observed`, `not resolved` and `not tested`. For this it uses four rules of its own, the page rules of lines 12 to 20. The page marks them as its own rules. |
| 12 | `      1  the pattern labels split and uniform are not used (user decision 2 of 2026-11-13, decisions.md). A rule that` | Page rule 1: the pattern labels `split` and `uniform` are not used. The handoff gives an interval the label `split` when q is below 0.65 and `uniform` when q is above 0.85. The user decided on 2026-11-13 not to use them (decision 2 in the file `decisions.md`). |
| 13 | `         needs a label gives "not resolved" (H8, H9a, and the B5 statement when the totals do not decide it).` | Continues page rule 1: a rule that needs a label gives the word `not resolved`. This holds for H8, for H9a, and for the statement of step B5 when the totals alone do not decide it. |
| 14 | `      2  H11 has one result per kernel and setting (a cell). The word of the page is: "not observed" if every cell is` | Page rule 2: H11 has one result per cell. A cell is one write kernel in one setting. The word of the page is `not observed` if every cell is `not observed`. |
| 15 | `         "not observed", "rejected" if every cell with another word is "rejected", "not rejected" if at least one` | Continues page rule 2: the word is `rejected` if every cell that has another word than `not observed` is `rejected`. The word `not rejected` needs at least one cell, as the next line says. |
| 16 | `         cell is "not rejected" and none is "rejected", and "not resolved" otherwise.` | Continues page rule 2: the word is `not rejected` if at least one cell is `not rejected` and no cell is `rejected`. In every other case it is `not resolved`. |
| 17 | `      3  H9b: with fewer than 2 sessions "not tested". With 2 or more: "not observed" if the ranges of q of` | Page rule 3, for H9b: with fewer than 2 sessions the word is `not tested`. With 2 or more sessions the word depends on the ranges of q, as the next line says. |
| 18 | `         old read at 64+56 threads overlap between all sessions, and "not resolved" otherwise (no label).` | Continues page rule 3: the word is `not observed` if the ranges of q of old read at 64+56 threads overlap between all sessions. If not, it is `not resolved`. No label is used. |
| 19 | `         The user has not approved this rule. The page marks H9b "open for the user".` | Continues page rule 3: the user has not approved this rule. So the page marks H9b as `open for the user`. |
| 20 | `      4  H10 is "not tested": no step of Parts B and C tests a bounded prediction of H10, and Part D was not run.` | Page rule 4: H10 is `not tested`. By this text no step of Parts B and C tests a bounded prediction of H10, and Part D was not run. |
| 21 | `  - for every hypothesis: the output of the analysis script as it stands, next to the word of the page, and the` | Third item of the list: for every hypothesis the page shows the unchanged output of the analysis script, next to the word of the page. |
| 22 | `    other reading with its reason where two readings exist. A judgment is marked "open for the user".` | Continues the third item: where two readings of a rule exist, the page gives the other reading with its reason. A judgment that the page does not make is marked `open for the user`. |
| 23 | `Text that interprets data is built from computed values. Typed text is limited to definitions, the wording of` | Continues the description: every sentence of the page that interprets data is built from computed values. Text that is typed into this file is limited to definitions and to the wording of the plan. |
| 24 | `the plan and of the handoff, the limits, and the references.` | Continues the sentence: typed text may also be the wording of the handoff, the limits of the page and the references. |
| 25 | `"""` | Ends the description. |

### Imports, folders and constants (lines 26 to 47)

| Line | Source | Explanation |
|---:|---|---|
| 26 | `import argparse, calendar, glob, html, os, re, sys, time` | Imports eight modules of the Python standard library: `argparse` (command line), `calendar` and `time` (times), `os` (paths), `re` (regular expressions), `sys`, `glob` and `html`. No later line uses `glob` or `html`. |
| 27 | `from statistics import median` | Imports `median`: the middle value of a sorted list. With an even count it is the mean of the two middle values. |
| 29 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder that holds this file. |
| 30 | `CRB = os.path.abspath(os.path.join(HERE, '..', '..'))` | `CRB`: the folder two levels above `HERE`. On the agent server the scripts lay in the folder `crb/new-test-kernel/partBC-analysis`, so `CRB` was the folder `crb` [Ref4]. In the code repo it is the code folder. |
| 31 | `BWX_DIR = os.environ.get('BWX_ANALYSIS_DIR') or os.path.join(CRB, 'tmp', 'agent-scratch', 'bwx-2026-11-13')` | `BWX_DIR`: the folder that holds `analyze_bwx.py`. It is the value of the environment variable `BWX_ANALYSIS_DIR` when that is set and not empty. If not, it is the folder `tmp/agent-scratch/bwx-2026-11-13` below `CRB`. The code repo has no such folder: there `analyze_bwx.py` lies in the folder `bwx-2026-11-13`. So in the code repo the variable must be set. |
| 32 | `for _d in (BWX_DIR, os.path.join(HERE, '..', 'partA-analysis')):` | Loop over two folders: `BWX_DIR`, and the folder `partA-analysis` beside the folder of this file. |
| 33 | `    sys.path.insert(0, os.path.abspath(_d))` | Puts the folder at the front of the list of folders in which Python looks for a module. |
| 34 | `import analyze_bwx as A            # noqa: E402  parser and decisions` | Imports the analysis script under the short name `A`. It reads the csv files that the runner wrote, and it holds the decision rules. The comment `noqa: E402` tells a style checker to accept an import that stands below other code. |
| 35 | `import make_partA_html as PA       # noqa: E402  style and number format of the Part A page` | Imports the generator of the Part A page under the short name `PA`. This file takes the page style, the colors and the number formats from it. |
| 37 | `fx, fs, e, pl, CSS, ID = PA.fx, PA.fs, PA.e, PA.pl, PA.CSS, PA.ID` | Takes six names from `PA`. `fx(v, nd)` prints a number with `nd` decimals, 2 when `nd` is not given. A half is rounded away from zero, and a zero has no minus sign. With 2 decimals, a value with exactly 3 decimals that end in 5, such as 0.995, keeps its 3 decimals. `fs` is `fx` with a sign (line 65 replaces it). `e` is `html.escape`: it replaces the characters that have a meaning in HTML. `pl(n, one, many)` gives the count `n` with the word `one` for 1 and the word `many` for every other count. `CSS` is the style text of the page. `ID` is the text `Insufficient data`. |
| 38 | `C0, C1, C2, INK, MUTED, GRID, BAND = PA.C0, PA.C1, PA.C2, PA.INK, PA.MUTED, PA.GRID, PA.BAND` | Takes seven colors from `PA`. `C0` is a blue (`#2a78d6`) for mesh 0 or the first series. `C1` is an orange (`#eb6834`) for mesh 1 or the second series. `C2` is a green (`#1baf7a`) for a third series. `MUTED` is a dark grey for axis text and dashed lines. `GRID` is a light grey for grid lines. No later line uses `INK` or `BAND`. |
| 39 | `STEPS = ['B7', 'B10', 'B8', 'B5', 'B9', 'C3']` | `STEPS`: the six steps of question Q2, in the order of the page. |
| 40 | `OFFSETS = os.path.join(BWX_DIR, 'crb-build-2', 'offsets.tsv')` | `OFFSETS`: the default path of the offsets file: `crb-build-2/offsets.tsv` below `BWX_DIR`. That file gives, for each binary and kernel, the address of the loop start modulo 64. |
| 41 | `KN = dict(oldread='old read', read='new read', asmread='asm read', asmread2='asm read 2', oldwrite='old write', write='new write',` | `KN`: the name that the page prints for each kernel name of the runner. This line: `oldread` is `old read`, `read` is `new read`, `asmread` is `asm read`, `asmread2` is `asm read 2`, `oldwrite` is `old write`, `write` is `new write`. |
| 42 | `          asmwrite='asm write', asmwrite2='asm write 2', read_sparse='read_sparse', read_nop4='read_nop4', read_nop8='read_nop8',` | Continues `KN`: `asmwrite` is `asm write` and `asmwrite2` is `asm write 2`. The names `read_sparse`, `read_nop4` and `read_nop8` are printed as they are. |
| 43 | `          read_nop16='read_nop16', read_nop32='read_nop32')` | Continues `KN`: `read_nop16` and `read_nop32` are also printed as they are. |
| 44 | `EVN = dict(cycles='cycles', instructions='instructions', l1d_refill='L1 refills', l2d_refill='L2 refills', ll_read_miss='last-level read misses')` | `EVN`: a printed name for each of the five counter events: cycles, instructions, L1 refills, L2 refills and last-level read misses. No later line uses `EVN`. |
| 45 | `REPRO = 'pass/500/common'` | `REPRO`: the setting of the reproduction condition: whole-pass stop, intervals of at least 500 ms, common start. By the plan it is the timing method of the benchmark run of 2026-11-13 that raised question Q2 [Ref1]. |

### Small helpers: median, number formats, times and setting names (lines 48 to 106)

| Line | Source | Explanation |
|---:|---|---|
| 48 | `def med(v):` | Starts the function `med`. It gives the median of a list and ignores the entries that are `None`. |
| 49 | `    v = [x for x in v if x is not None]` | Keeps the entries of `v` that are not `None`. |
| 50 | `    return median(v) if v else None` | Returns the median of these entries, or `None` when no entry is left. |
| 53 | `def f(v, nd=2):` | Starts the function `f`. It prints a number with `nd` decimals for a sentence or a table cell. |
| 54 | `    return '-' if v is None else fx(v, nd)` | Returns `-` for `None`. For a number it returns the text that `fx` gives. |
| 57 | `def rng(vals, nd=2):` | Starts the function `rng`. It prints the lowest and the highest value of a list as a range. |
| 58 | `    v = [x for x in vals if x is not None]` | `v`: the entries of `vals` that are not `None`. |
| 59 | `    if not v:` | Tests whether no entry is left. |
| 60 | `        return '-'` | In that case the function returns `-`. |
| 61 | `    a, b = fx(min(v), nd), fx(max(v), nd)` | `a` and `b`: the lowest and the highest entry, each printed with `nd` decimals. |
| 62 | `    return a if a == b else f'{a} to {b}'` | Returns `a` alone when both print the same text. If not, it returns the two numbers with the word `to` between them. |
| 65 | `def fs(v, nd=2):` | Starts the function `fs` of this file. From here on it replaces the `fs` that line 37 took from `PA`. |
| 66 | `    """As fx, with a sign. A value that prints as zero carries no sign."""` | Description of `fs`: as `fx`, with a sign. A value that prints as zero has no sign. |
| 67 | `    t = PA.fs(v, nd)` | `t`: the number as `PA.fs` prints it, with a sign at the front, for example `+1.50`. |
| 68 | `    return t.lstrip('+-') if float(t) == 0 else t` | When the printed number is zero, the sign is removed, so `-0.00` and `+0.00` both become `0.00`. Every other text is returned as it is. |
| 71 | `def utc(t):` | Starts the function `utc`. It turns a time text into Unix time, the seconds counted from 1970-01-01 00:00 UTC. |
| 72 | `    """'2026-11-14T02:43:52Z' -> seconds since 1970, or None."""` | Description of `utc`: a text of the form `2026-11-14T02:43:52Z` gives the Unix time, and every other input gives `None`. |
| 73 | `    try:` | Starts a block whose errors line 75 handles. |
| 74 | `        return calendar.timegm(time.strptime(t, '%Y-%m-%dT%H:%M:%SZ'))` | `time.strptime` reads the year, month, day, hour, minute and second from the text. `calendar.timegm` takes them as UTC and returns the Unix time. |
| 75 | `    except (TypeError, ValueError):` | Handles two errors: `t` is not a text (for example `None`), or the text does not have this form. |
| 76 | `        return None` | In both cases the function returns `None`. |
| 79 | `def hm(sec):` | Starts the function `hm`. It prints a duration in words. |
| 80 | `    """A duration in plain words."""` | Description of `hm`: a duration in plain words. |
| 81 | `    sec = int(round(sec))` | Rounds the duration to whole seconds. |
| 82 | `    if sec < 120:` | Tests whether the duration is below 120 s. |
| 83 | `        return f'{sec} s'` | In that case the result is the seconds, for example `14 s`. |
| 84 | `    h, mnt = divmod(int(round(sec / 60)), 60)` | For 120 s and more: rounds the duration to whole minutes and splits them into the hours `h` and the minutes `mnt`. |
| 85 | `    return (f'{h} h {mnt} min' if h else f'{mnt} min')` | Returns a text such as `3 h 15 min`. When the hours are 0, it returns the minutes alone, such as `25 min`. |
| 88 | `def clock(t):` | Starts the function `clock`. It prints a Unix time as a time of day. |
| 89 | `    return time.strftime('%H:%M:%S', time.gmtime(t))` | Returns the hours, minutes and seconds in UTC, in the form `02:43:52`. |
| 92 | `def folder_step(path):` | Starts the function `folder_step`. It gives the step part of the name of a result folder. |
| 93 | `    return os.path.basename(path.rstrip('/')).split('-')[0]` | Takes the last part of the path, without a slash at its end, and returns the text before the first `-`. The folder name `B10a-20261113T235919Z` gives `B10a`. |
| 96 | `def sname(s):` | Starts the function `sname`. It turns a setting such as `pass/500/common` into words for the page. |
| 97 | `    """Plain name of a setting stop/min_ms/start."""` | Description of `sname`: the plain name of a setting. A setting has the form `stop/min_ms/start`. |
| 98 | `    stop, ms, start = s.split('/')` | Splits the setting at the slashes into the stop method, the interval length in ms and the start. |
| 99 | `    return f"{'whole passes' if stop == 'pass' else 'common stop'}, {int(ms) / 1000:g} s, {'common start' if start == 'common' else 'offset start'}"` | Returns three parts with commas between them. Part 1 is `whole passes` for the stop method `pass` and `common stop` for every other one. Part 2 is the interval length in seconds, such as `0.5 s` or `6 s`. Part 3 is `common start` for the start `common` and `offset start` for every other one. So `pass/500/common` gives `whole passes, 0.5 s, common start`. |
| 102 | `def skey(s):` | Starts the function `skey`. It gives the sort key of a setting. |
| 103 | `    stop, ms, start = s.split('/')` | Splits the setting in the same way as line 98. |
| 104 | `    return (stop != 'pass', int(ms), start != 'common')` | Returns three values that are compared in this order. So settings with whole passes come before settings with the common stop. Then the shorter interval comes first. Then the common start comes before the offset start. |

### Values of one interval, and medians over several intervals (lines 107 to 129)

| Line | Source | Explanation |
|---:|---|---|
| 107 | `# ---------------------------------------------------------------- model (computed values only)` | Comment: here starts the code that builds the model. The model is the set of computed values from which the page is written. |
| 109 | `def ivstat(iv):` | Starts the function `ivstat`. It collects the values of one interval that the page uses. `iv` is an interval object of the analysis script. It holds the T rows of the interval, one per thread. |
| 110 | `    r = [(x['cpu'], x['bytes'] / x['elapsed'] / 1e9) for x in iv.rows]` | `r`: one pair per T row: the CPU number of the row, and the thread rate. The thread rate is the column `bytes` divided by the column `elapsed_s` and by 1e9, in GB/s. In the runner source `bwx.c` a thread reads the clock directly before its first timed kernel call and directly after its last one, and `elapsed_s` is the difference. The warm-up pass lies before the first reading. |
| 111 | `    a = [v for c, v in r if c in A.MESH0_CPUS]` | `a`: the thread rates of the threads on mesh 0. `A.MESH0_CPUS` is the range of the CPU numbers 0 to 63. |
| 112 | `    b = [v for c, v in r if c not in A.MESH0_CPUS]` | `b`: the thread rates of all other threads. These are the threads on mesh 1. |
| 113 | `    return dict(hist=iv.hist, msum=iv.msum, q=iv.q, m0=med(a), m1=med(b), mh0=iv.mesh_hist[0], mh1=iv.mesh_hist[1],` | Returns a dictionary. `hist`: the total `M_hist` of the interval: the bytes of all threads divided by the longest elapsed time of a thread, in GB/s. `msum`: `M_sum`, the sum of the thread rates. `q`: the thread rate at the 10th percentile divided by the one at the 90th percentile. `m0` and `m1`: the median thread rate of mesh 0 and of mesh 1. `mh0` and `mh1`: the bytes of the threads of one mesh divided by the longest elapsed time of all threads. The analysis script computed `hist`, `msum`, `q` and the two mesh values from the same T rows. |
| 114 | `                minpass=min(x['passes'] for x in iv.rows), entry=iv.entry, round=iv.round, pos=iv.pos)` | Continues the dictionary. `minpass`: the smallest value of the column `passes` over the T rows, so the fewest passes over its buffer that a thread made in the interval. `entry`: the kernel of the interval, taken from the sequence in the header line. `round` and `pos`: the round and the position that the rows give. |
| 117 | `def agg(stats):` | Starts the function `agg`. It combines the values of several intervals into medians and ranges. `stats` is a list of dictionaries of `ivstat`. |
| 118 | `    if not stats:` | Tests whether the list is empty. |
| 119 | `        return None` | In that case the function returns `None`. |
| 120 | `    g = lambda k: [s[k] for s in stats]` | `g`: a small function that gives the list of the values of one key over all intervals. |
| 121 | `    return dict(n=len(stats), hist=med(g('hist')), hist_min=min(g('hist')), hist_max=max(g('hist')), msum=med(g('msum')),` | Returns a dictionary. `n`: the number of intervals. `hist`, `hist_min` and `hist_max`: the median, the lowest and the highest total `M_hist` over the intervals. `msum`: the median of `M_sum`. |
| 122 | `                q=med(g('q')), q_min=min(g('q')), q_max=max(g('q')), m0=med(g('m0')), m1=med(g('m1')),` | Continues the dictionary. `q`, `q_min` and `q_max`: the median, the lowest and the highest q. `m0` and `m1`: the median over the intervals of the median thread rate of mesh 0 and of mesh 1. |
| 123 | `                mh0=med(g('mh0')), mh1=med(g('mh1')))` | Continues the dictionary. `mh0` and `mh1`: the median over the intervals of the `M_hist` value of mesh 0 and of mesh 1. |
| 126 | `def regular(p, entry=None):` | Starts the function `regular`. It gives the intervals of a process `p` that may be used. |
| 127 | `    return [iv for iv in p.ordered if not iv.irregular and (entry is None or iv.entry == entry)]` | Returns the intervals of the process, in the order of round and position, that are not irregular. With `entry` given, only the intervals of that kernel are kept. The analysis script calls an interval irregular when a thread has the flag `late`, or when the process uses the common stop and the end times of its threads differ by more than 5 ms. |

### `read_env` and `read_launches`: the load readings of one result folder (lines 130 to 177)

| Line | Source | Explanation |
|---:|---|---|
| 130 | `def read_env(folder):` | Starts the function `read_env`. It reads the file `env.txt` of one result folder. The run script writes this file: a start line before the first process of the step, some lines on the state of the machine, and an end line after the last process. |
| 131 | `    out = dict(folder=os.path.basename(folder.rstrip('/')), present=False, busy=[])` | `out`: the result. It starts with the name of the folder, with `present` as false and with an empty list `busy`. |
| 132 | `    path = os.path.join(folder, 'env.txt')` | `path`: the path of `env.txt` in the folder. |
| 133 | `    if not os.path.exists(path):` | Tests whether the file is missing. |
| 134 | `        return out` | In that case the function returns `out`, with `present` still false. |
| 135 | `    out['present'] = True` | The file exists: `present` becomes true. |
| 136 | `    inbusy = False` | `inbusy`: true while the loop reads the process list that follows the line `## busiest processes`. |
| 137 | `    for line in open(path, errors='replace'):` | Loop over the lines of the file. `errors='replace'` puts a replacement character in the place of a byte that is not valid text, so such a byte does not stop the script. |
| 138 | `        m = re.match(r'## host=\S+ utc=(\S+) loadavg=(\S+) \S+ \S+ (\d+)/(\d+) \S+ logins=(\S+) step=(\S+) steps=(.*)', line)` | Tests whether the line is the start line. The pattern fits `## host=` with the host name, `utc=`, `loadavg=` with the five fields of the file `/proc/loadavg`, `logins=`, `step=` and `steps=`. Group 1 holds the UTC start time. Group 2 holds the load average of the last minute. Groups 3 and 4 hold the two numbers of the fourth field: the tasks that are runnable now, and all tasks. Group 5 holds the number of logins. Group 6 holds the step. Group 7 holds the rest of the line: the steps of the visit, the one login that ran this step. |
| 139 | `        if m:` | The next line runs only for the start line. |
| 140 | `            out.update(start_utc=m.group(1), start_load=float(m.group(2)), start_runnable=int(m.group(3)), start_logins=m.group(5), steps=m.group(7).strip())` | Keeps five values: the start time, the load average of the last minute as a number, the number of runnable tasks, the logins, and the steps of the visit. |
| 141 | `        m = re.match(r'## end utc=(\S+) loadavg=(\S+)', line)` | Tests whether the line is the end line. Group 1 holds the UTC end time. Group 2 holds the load average of the last minute at the end. |
| 142 | `        if m:` | The next line runs only for the end line. |
| 143 | `            out.update(end_utc=m.group(1), end_load=float(m.group(2)))` | Keeps the end time and the load average at the end. |
| 144 | `        m = re.match(r'## uptime=([\d.]+)', line)` | Tests whether the line is the uptime line. Group 1 holds the uptime: the seconds for which the machine has run after its start, as digits with a dot. |
| 145 | `        if m:` | The next line runs only for the uptime line. |
| 146 | `            out['uptime'] = float(m.group(1))` | Keeps the uptime as a number, in seconds. |
| 147 | `        if line.startswith('## settings:'):` | Tests whether the line is the settings line. It holds the settings of the run script in the form `NAME=value`. |
| 148 | `            out['settings'] = dict(kv.split('=', 1) for kv in re.findall(r'(\w+=(?:[^=]*?))(?= \w+=\|$)', line[len('## settings:'):].strip()))` | Builds a dictionary of the settings. The pattern finds each piece that is a name, `=` and the shortest text without `=` that ends before a space and the next name with `=`, or at the end of the line. Each piece is split at its first `=` into the name and the value. A value that holds `=` itself, such as the event list of `BWX_EVENTS`, does not fit: its name is lost and a wrong entry is made. No later line of this file reads `settings`. |
| 149 | `        if line.startswith('##'):` | Tests whether the line starts with `##`. |
| 150 | `            inbusy = line.startswith('## busiest processes')` | Such a line sets `inbusy`: true for the line `## busiest processes`, false for every other one. |
| 151 | `        elif inbusy:` | A line without `##` is read as a line of the process list while `inbusy` is true. |
| 152 | `            m = re.match(r'\s*([\d.]+)\s+(\S+)\s+(\S.*)$', line)` | The pattern fits one line of the list that the tool `ps` printed. Group 1 holds the CPU share of the process in % of one CPU. Group 2 holds the account. Group 3 holds the command name. The heading line of `ps` does not start with a number, so it does not fit. |
| 153 | `            if m:` | The next line runs only when the pattern fits. |
| 154 | `                out['busy'].append((float(m.group(1)), m.group(2), m.group(3).strip()))` | Adds the share as a number, the account and the command name to the list `busy`. No later line of this file reads this list of `env.txt`. |
| 155 | `    return out` | Returns `out`. |
| 158 | `def read_launches(folder):` | Starts the function `read_launches`. It reads the file `launches.txt` of one result folder. The run script adds one block to this file before each process: a line that starts with `==`, and then the output of `ps` with a heading line and the 5 processes with the highest CPU share. |
| 159 | `    """launches.txt: the second reading before each launch, and the 5 busiest processes."""` | Description of `read_launches`: the file holds the second load reading before each launch, and the 5 busiest processes. |
| 160 | `    path = os.path.join(folder, 'launches.txt')` | `path`: the path of `launches.txt` in the folder. |
| 161 | `    out = []` | `out`: the list of the launches, empty at first. |
| 162 | `    if not os.path.exists(path):` | Tests whether the file is missing. |
| 163 | `        return out` | In that case the function returns the empty list. |
| 164 | `    cur = None` | `cur`: the launch whose process list is read now. It is `None` before the first `==` line. |
| 165 | `    for line in open(path, errors='replace'):` | Loop over the lines of the file. |
| 166 | `        m = re.match(r'== (\S+) (\S+) utc (\S+) loadavg (\S+) \S+ \S+ (\d+)/(\d+) logins (\S+)', line)` | Tests whether the line starts a launch. The pattern fits `==`, the name of the csv file, the tag, `utc` with a time of day, `loadavg` with four fields, and `logins`. Group 1 holds the csv name, for example `B7.csv`. Group 2 holds the tag of the process. Group 3 holds the time. Group 4 holds the load average of the last minute. Groups 5 and 6 hold the tasks that are runnable now, and all tasks. Group 7 holds the number of logins. |
| 167 | `        if m:` | The next four lines run only for such a line. |
| 168 | `            cur = dict(step=m.group(1).split('.')[0], tag=m.group(2), utc=m.group(3), load=float(m.group(4)), runnable=int(m.group(5)), logins=m.group(7), busy=[],` | `cur`: a new entry for this launch. `step` is the csv name up to its first dot, so `B10.csv` gives `B10`. The entry also keeps the tag, the time, the load average as a number, the number of runnable tasks, the logins and an empty process list `busy`. |
| 169 | `                       folder=os.path.basename(folder.rstrip('/')))` | Continues the entry: the name of the result folder. |
| 170 | `            out.append(cur)` | Adds the entry to `out`. |
| 171 | `            continue` | Goes on with the next line of the file. |
| 172 | `        m = re.match(r'\s*([\d.]+)\s+(\S+)\s+(\S.*)$', line)` | For every other line: the same pattern as in line 152, for one line of the `ps` list. |
| 173 | `        if m and cur is not None:` | The next line runs only when the pattern fits and a launch has started. |
| 174 | `            cur['busy'].append((float(m.group(1)), m.group(2), m.group(3).strip()))` | Adds the share as a number, the account and the command name to the process list of the launch. |
| 175 | `    return out` | Returns the list of the launches. |

### `load_model`: the load readings of every step (lines 178 to 215)

| Line | Source | Explanation |
|---:|---|---|
| 178 | `BUSY_LIMIT = 10.0          # % of one CPU: a process of another account above this value is listed by name` | `BUSY_LIMIT`: 10 % of one CPU. The page names a process of another account when `ps` shows it above this value at a launch. |
| 181 | `def load_model(procs, folders):` | Starts the function `load_model`. For each step of one session it collects the load readings from two sources: the header lines of the processes `procs`, and the files `launches.txt` of the result folders `folders`. |
| 182 | `    out = {}` | `out`: the result, one entry per step. |
| 183 | `    launches = [x for fo in folders for x in read_launches(fo)]` | `launches`: the launch entries of all folders in one list. |
| 184 | `    own = {u for x in launches for _, u, c in x['busy'] if re.sub(r'[/:].*$', '', c) in ('bash', 'ps', 'bwx')}` | `own`: the set of the accounts that the script takes as our own. An account belongs to it when a process list shows it with a process named `bash`, `ps` or `bwx`. `re.sub` first cuts the command name at its first `/` or `:`, so `kworker/0:1` becomes `kworker`. |
| 185 | `    for step in STEPS:` | Loop over the six steps of Q2. |
| 186 | `        g = [p for p in procs if p.step == step]` | `g`: the processes of this step. The step of a process comes from its header line. |
| 187 | `        if not g:` | Tests whether the step has no process. |
| 188 | `            continue` | Such a step gets no entry. |
| 189 | `        run = [int(p.runnable.split('/')[0]) for p in g if re.fullmatch(r'\d+/\d+', p.runnable or '')]` | `run`: the number of runnable tasks of each header line. The header line holds the fourth field of `/proc/loadavg`, for example `1/1077`. The number before the slash is kept. A header line whose field does not have this form gives no value. |
| 190 | `        la = [x for x in launches if x['step'] == step]` | `la`: the launch entries of this step. |
| 191 | `        busy = {}` | `busy`: for each pair of account and command name, the highest CPU share over the launches of the step. It is empty at first. |
| 192 | `        for x in la:` | Loop over the launch entries of the step. |
| 193 | `            for pc, user, comm in x['busy']:` | Loop over the lines of the process list of the launch. |
| 194 | `                k = (user, re.sub(r'[/:].*$', '', comm))` | `k`: the account, and the command name cut at its first `/` or `:`. |
| 195 | `                busy[k] = max(busy.get(k, 0.0), pc)` | Keeps the higher of the value so far and the share `pc` of this line. |
| 196 | `        other = sorted(((v, u, c) for (u, c), v in busy.items() if u not in own), reverse=True)` | `other`: the entries of the accounts that are not in `own`, each as share, account and command, sorted from the highest share down. |
| 197 | `        mine = sorted(((v, u, c) for (u, c), v in busy.items() if u in own), reverse=True)` | `mine`: the same for the accounts in `own`. |
| 198 | `        logins = [int(p.logins) for p in g if str(p.logins).isdigit()]` | `logins`: the number of logged-in users of each header line, when the field is a number. |
| 199 | `        # every launch at which a process of another account is above BUSY_LIMIT` | Comment: the next statement collects every launch at which a process of another account is above `BUSY_LIMIT`. |
| 200 | `        ev = [dict(step=step, tag=x['tag'], utc=x['utc'], load=x['load'], runnable=x['runnable'], pc=pc, user=u, comm=re.sub(r'[/:].*$', '', c), n_launches=len(la))` | `ev`: one entry for each such line of a process list. The entry keeps the step, the tag and the time of the launch, its load average and its runnable tasks, the share `pc`, the account, the cut command name, and the number of launches of the step. |
| 201 | `              for x in la for pc, u, c in x['busy'] if u not in own and pc > BUSY_LIMIT]` | Continues the statement of line 200: it runs over the launches of the step and over their process lists, and keeps the lines of an account outside `own` with a share above `BUSY_LIMIT`. |
| 202 | `        runs = run + [x['runnable'] for x in la]` | `runs`: the numbers of runnable tasks of the header lines and of the launch entries together. |
| 203 | `        logs = logins + [int(x['logins']) for x in la if x['logins'].isdigit()]` | `logs`: the numbers of logins of the header lines and of the launch entries together. |
| 204 | `        out[step] = dict(n=len(g), utc=(g[0].utc, g[-1].utc), load_min=min((p.load1 for p in g if p.load1 is not None), default=None),` | Starts the entry of the step. `n`: the number of processes. `utc`: the times of day of the first and of the last header line. `load_min`: the lowest load average of the last minute over the header lines, or `None` when no header line has one. |
| 205 | `                         load_max=max((p.load1 for p in g if p.load1 is not None), default=None), first_load=g[0].load1,` | `load_max`: the highest such load average. `first_load`: the load average of the first header line of the step. |
| 206 | `                         runnable_max=max(run) if run else None, n_waited=sum(1 for p in g if p.waited_s),` | `runnable_max`: the highest number of runnable tasks of a header line. `n_waited`: the number of processes whose header line gives a wait above 0 s. Before a launch the run script waits until at most 2 tasks are runnable, for 20 s at most. It writes the waited seconds into the header line as `waited_s`. |
| 207 | `                         wait_max=max((p.waited_s for p in g if p.waited_s is not None), default=None), logins_max=max(logins) if logins else None,` | `wait_max`: the longest wait in s. `logins_max`: the highest number of logins of a header line. |
| 208 | `                         n_launches_txt=len(la), runnable_txt_max=max((x['runnable'] for x in la), default=None),` | `n_launches_txt`: the number of launch entries of `launches.txt`. `runnable_txt_max`: the highest number of runnable tasks of these entries. |
| 209 | `                         logins_txt_max=max((int(x['logins']) for x in la if x['logins'].isdigit()), default=None),` | `logins_txt_max`: the highest number of logins of the launch entries. |
| 210 | `                         runnable_min=min(runs) if runs else None, runnable_all_max=max(runs) if runs else None,` | `runnable_min` and `runnable_all_max`: the lowest and the highest number of runnable tasks over both sources. |
| 211 | `                         logins_all_max=max(logs) if logs else None, n_log_readings=len(logs),` | `logins_all_max`: the highest number of logins over both sources. `n_log_readings`: the number of login readings. |
| 212 | `                         busy_other=other[:2], busy_own=mine[:2], threads_max=max(p.threads for p in g), other_events=ev)` | `busy_other` and `busy_own`: the two entries with the highest share of the other accounts and of our own accounts. `threads_max`: the highest thread count of a process of the step, from its option `--threads`. `other_events`: the list `ev`. |
| 213 | `    return out` | Returns `out`. |

### `timing_model`: when the sessions and the result folders ran (lines 216 to 251)

| Line | Source | Explanation |
|---:|---|---|
| 216 | `def timing_model(env_all, names):` | Starts the function `timing_model`. From the readings of `env.txt` it computes when each session ran and how far the sessions and the folders lie apart. `env_all` holds, per session, the result of `read_env` for every folder given. `names` is the list of the session names. |
| 217 | `    """env_all {session: [env of every folder given]} -> start, end and distances of the sessions (from env.txt)."""` | Description of `timing_model`: the input is the `env.txt` reading of every folder given, per session. The output holds the start, the end and the distances of the sessions. |
| 218 | `    out = dict(sessions={}, gaps=[], same_step=None, same_boot=None, visits={})` | `out`: the result, with five entries that the next lines fill: `sessions`, `gaps`, `same_step`, `same_boot` and `visits`. |
| 219 | `    allv = []` | `allv`: the readings of all sessions in one list, empty at first. |
| 220 | `    for s in names:` | Loop over the sessions. |
| 221 | `        ev = [x for x in env_all[s] if x['present'] and utc(x.get('start_utc')) is not None]` | `ev`: the readings of this session whose `env.txt` exists and whose start time can be read. |
| 222 | `        for x in ev:` | Loop over these readings. |
| 223 | `            allv.append(dict(x, session=s, t0=utc(x['start_utc']), t1=utc(x.get('end_utc'))))` | Adds a copy of the reading to `allv`, with the session name, the start time `t0` and the end time `t1`, both as Unix time. `t1` is `None` when the file has no end line. |
| 224 | `        if ev:` | The next two lines run only when the session has such a reading. |
| 225 | `            ends = [utc(x.get('end_utc')) for x in ev if utc(x.get('end_utc')) is not None]` | `ends`: the end times of the folders of the session that have one. |
| 226 | `            out['sessions'][s] = dict(t0=min(utc(x['start_utc']) for x in ev), t1=max(ends) if ends else None, n=len(ev))` | The entry of the session. `t0`: the earliest start time of its folders. `t1`: the latest end time, or `None`. `n`: the number of folders with a start time. |
| 227 | `    allv.sort(key=lambda x: x['t0'])` | Sorts the readings of all sessions by their start time. |
| 228 | `    # the visit before each folder: the folder that ended last before this one started (any session, any step given)` | Comment: the next loop finds the visit before each folder. That is the folder that ended last before this folder started. Folders of every session and of every step given are taken into account. |
| 229 | `    for i, x in enumerate(allv):` | Loop over the sorted readings. `i` is the place of the reading `x` in the list. |
| 230 | `        prev = [y for y in allv[:i] if y['t1'] is not None and y['t1'] <= x['t0']]` | `prev`: the folders that started earlier, have an end time, and ended at or before the start of this folder. |
| 231 | `        p = max(prev, key=lambda y: y['t1']) if prev else None` | `p`: the one of them that ended last, or `None` when there is none. |
| 232 | `        out['visits'][(x['session'], x['folder'])] = dict(gap=(x['t0'] - p['t1']) if p else None, prev_steps=p.get('steps') if p else None,` | The entry of this folder, stored under its session and its folder name. `gap`: the seconds from the end of `p` to the start of this folder. `prev_steps`: the steps of the visit of `p`. |
| 233 | `                                                          prev_folder=p['folder'] if p else None, prev_session=p['session'] if p else None)` | Continues the entry: the folder name and the session of `p`. All four values are `None` when no folder ended before this one. |
| 234 | `    have = [s for s in names if s in out['sessions']]` | `have`: the sessions that have at least one folder with a start time. |
| 235 | `    for a, b in zip(have, have[1:]):` | Loop over each pair of sessions that follow each other in the order of the command line. |
| 236 | `        if out['sessions'][a]['t1'] is not None:` | The next line runs only when the first session of the pair has an end time. |
| 237 | `            out['gaps'].append((a, b, out['sessions'][b]['t0'] - out['sessions'][a]['t1']))` | Adds to `gaps`: the two names, and the seconds from the end of the first session to the start of the second. |
| 238 | `    if len(have) >= 2:` | The next six lines run only with at least 2 such sessions. |
| 239 | `        a, b = have[0], have[1]` | `a` and `b`: the first two sessions. |
| 240 | `        fa = {folder_step(x['folder']): utc(x['start_utc']) for x in env_all[a] if x['present'] and 'start_utc' in x}` | `fa`: for session `a`, a dictionary from the step part of each folder name, such as `B10a`, to the start time of that folder. |
| 241 | `        fb = {folder_step(x['folder']): utc(x['start_utc']) for x in env_all[b] if x['present'] and 'start_utc' in x}` | `fb`: the same for session `b`. |
| 242 | `        d = [fb[k] - fa[k] for k in fa if k in fb]` | `d`: for each step part that both sessions have, the seconds from the start of the folder in `a` to the start of the folder in `b`. |
| 243 | `        if d:` | The next line runs only when the two sessions share a step part. |
| 244 | `            out['same_step'] = (a, b, min(d), max(d), len(d))` | `same_step`: the two names, the smallest and the largest of these distances, and their number. |
| 245 | `    boots = [x['t0'] - x['uptime'] for x in allv if x.get('uptime') is not None]` | `boots`: for each folder with an uptime reading, its start time minus the uptime. This is the time at which the machine was started, computed from that reading. |
| 246 | `    if len(boots) == len(allv) and boots:` | The next two lines run only when every folder has an uptime reading. |
| 247 | `        out['same_boot'] = (max(boots) - min(boots)) < 30          # the boot time computed from each reading agrees within 30 s` | `same_boot`: true when the computed start times of the machine differ by less than 30 s. The page then says that the machine was not restarted between the sessions (line 1122). |
| 248 | `        out['boot_n'] = len(boots)` | `boot_n`: the number of uptime readings. |
| 249 | `    return out` | Returns `out`. |

### `b7_model` and `b7_rep`: the values of step B7 (lines 252 to 293)

| Line | Source | Explanation |
|---:|---|---|
| 252 | `def b7_model(procs, res):` | Starts the function `b7_model`. It builds the values of step B7 for one session. `procs` are the B7 processes of the session. `res` is the result of the analysis script for B7. |
| 253 | `    main = [p for p in procs if p.complete and len(p.seq) > 1]` | `main`: the complete processes whose sequence holds more than one kernel. These run the four read kernels in one process. The analysis script calls a process complete when it found no problem in its rows: no line `-- killed` or `-- failed`, every expected interval, and one T row per thread in each interval. |
| 254 | `    single = [p for p in procs if p.complete and len(p.seq) == 1]` | `single`: the complete processes whose sequence holds one kernel. These are the processes of the reproduction condition with one kernel per process. |
| 255 | `    out = dict(res=res, n_main=len(main), n_single=len(single), kern={}, single={}, fail2={}, skew_pass_ms=None, procs=main)` | `out`: the result. It keeps `res`, the number of processes of each kind, and the list `main` as `procs`. The next lines fill the other entries. |
| 256 | `    for s in sorted({p.setting for p in main}, key=skey):` | Loop over the settings of the `main` processes, in the order of `skey`. |
| 257 | `        g = [p for p in main if p.setting == s]` | `g`: the `main` processes of this setting. |
| 258 | `        out['kern'][s] = {k: agg([ivstat(iv) for p in g for iv in regular(p, k)]) for k in ('oldread', 'read', 'asmread', 'asmread2')}` | For this setting and each of the four read kernels: the medians and ranges of `agg` over the regular intervals of the kernel. The intervals of all processes of the setting and of both rounds go into one list. |
| 259 | `        if s.startswith('pass/'):` | The next two lines run only for a setting with whole passes. |
| 260 | `            ivs = [ivstat(iv) for p in g for iv in regular(p)]` | `ivs`: the values of every regular interval of the setting, of all four kernels. |
| 261 | `            out['fail2'][s] = (sum(1 for x in ivs if x['minpass'] < 50), len(ivs), min((x['minpass'] for x in ivs), default=None))` | The 2 % check of rule 7 of the plan. By that rule one pass may take at most 2 % of the interval, so each thread must make at least 50 passes. The entry holds three values: the number of intervals in which a thread made fewer than 50 passes, the number of intervals, and the fewest passes of a thread in the setting. |
| 262 | `    for k in ('oldread', 'read', 'asmread', 'asmread2'):` | Loop over the four read kernels. |
| 263 | `        out['single'][k] = agg([ivstat(iv) for p in single if p.seq[0] == k for iv in regular(p)])` | The same medians and ranges for the processes that ran this kernel alone. |
| 264 | `    ivs = [ivstat(iv) for p in single if p.stop == 'pass' for iv in regular(p)]          # the 2 % check of rule 7 also applies here` | `ivs`: the values of every regular interval of the one-kernel processes with whole passes. The comment says that the 2 % check of rule 7 applies to them too. |
| 265 | `    out['fail2_single'] = (sum(1 for x in ivs if x['minpass'] < 50), len(ivs), min((x['minpass'] for x in ivs), default=None)) if ivs else None` | `fail2_single`: the same three values as in line 261 for these intervals, or `None` when there is no such interval. |
| 266 | `    sk = [iv.skew * 1e3 for p in main + single if p.stop == 'pass' for iv in p.ordered]` | `sk`: the end skew in ms of every interval of the processes with whole passes. The end skew is the latest end time of a thread minus the earliest one, from the column `t_end_s` of the T rows. |
| 267 | `    out['skew_pass_ms'] = max(sk) if sk else None` | Keeps the largest end skew. No later line of this file reads `skew_pass_ms`. |
| 268 | `    # The setting for the later steps (handoff B.9, "Settings after B7"): resolved, --stop common, largest \|median D\|.` | Comment: the next line finds the setting for the later steps by the rule of the handoff (section B.9, `Settings after B7`). The setting must have a resolved D and the common stop. Of these settings the one with the largest absolute median D is taken. D is the total of old read minus the total of new read. |
| 269 | `    cand = [(abs(v['metrics']['M_hist']['median_D']), s) for s, v in res['settings'].items() if v['decision'] == 'resolved' and s.startswith('common/')]` | `cand`: one pair for each setting with the common stop whose decision for D is `resolved`: the absolute median D with `M_hist`, and the setting. |
| 270 | `    out['chosen'] = max(cand)[1] if cand else None` | `chosen`: the setting of the pair with the largest absolute median D, or `None` when no setting fits. The handoff has a second case that this line does not code: when D is resolved only in settings with whole passes, it takes the one of them with the largest absolute median D. |
| 271 | `    out['rep'] = None` | `rep`: the place for the example pair of intervals. `b7_rep` fills it later. |
| 272 | `    return out` | Returns `out`. |
| 275 | `def b7_rep(b, used):` | Starts the function `b7_rep`. It picks one old read interval and one new read interval of one process, for the chart of thread rate against CPU number. `b` is the model of B7. `used` is the one setting in which B8, B5 and B9 of the session ran, or `None`. |
| 276 | `    """Representative interval pair. The setting: the one that B8, B5 and B9 of the session ran in (used, from their header` | Description of `b7_rep`: the pair comes from the setting in which B8, B5 and B9 of the session ran, as their header lines show. |
| 277 | `    lines) if it is one setting of B7. Else the setting that the handoff rule selects, else the reproduction condition,` | Continues the description: this holds when that setting is one of the settings of B7. If not, the setting that the handoff rule selects is taken, and if there is none, the reproduction condition. |
| 278 | `    else the first setting. The process: the first in the file. Its first regular old read and new read interval."""` | Continues the description: the last choice is the first setting. The process is the first one in the file. The pair is its first regular old read interval and its first regular new read interval. |
| 279 | `    kern = b['kern']` | `kern`: the settings of B7 with their values. |
| 280 | `    if used and used in kern:` | Tests whether `used` is set and is a setting of B7. |
| 281 | `        rs, why = used, 'used'` | Then `rs`, the setting of the pair, is `used`, and the reason `why` is `used`. |
| 282 | `    elif b['chosen']:` | If not: tests whether the handoff rule selected a setting (line 270). |
| 283 | `        rs, why = b['chosen'], 'chosen'` | Then `rs` is that setting, and `why` is `chosen`. |
| 284 | `    else:` | In every other case the next line applies. |
| 285 | `        rs, why = (REPRO if REPRO in kern else (sorted(kern, key=skey)[0] if kern else None)), 'fallback'` | `rs` is the reproduction condition when B7 has it. If not, it is the first setting in the order of `skey`, or `None` when B7 has no setting. `why` is `fallback`. |
| 286 | `    for p in b['procs']:` | Loop over the processes with all four kernels, in the order of the csv file. |
| 287 | `        if p.setting == rs and regular(p, 'oldread') and regular(p, 'read'):` | Takes the first process of the setting `rs` that has a regular old read interval and a regular new read interval. |
| 288 | `            o, n = regular(p, 'oldread')[0], regular(p, 'read')[0]` | `o` and `n`: its first regular interval of old read and of new read. |
| 289 | `            pts = lambda iv: sorted((x['cpu'], x['bytes'] / x['elapsed'] / 1e9) for x in iv.rows)` | `pts`: a small function that gives one pair per T row of an interval: the CPU number and the thread rate in GB/s (column `bytes` divided by column `elapsed_s`). The pairs are sorted by CPU number. |
| 290 | `            b['rep'] = dict(setting=rs, why=why, tag=p.tag, file=p.file, old=pts(o), new=pts(n), old_s=ivstat(o), new_s=ivstat(n))` | Stores the pair in the model: the setting, the reason `why`, the tag and the file of the process, the points of both intervals, and the `ivstat` values of both. |
| 291 | `            break` | Ends the loop after the first process that fits. |

### `b10_model` and `b8_model`: the values of the steps B10 and B8 (lines 294 to 332)

| Line | Source | Explanation |
|---:|---|---|
| 294 | `def b10_model(procs, res):` | Starts the function `b10_model`. It builds the values of step B10 for one session: the four write kernels in 8 settings. |
| 295 | `    used = [p for p in procs if p.complete]` | `used`: the complete processes of the step. |
| 296 | `    out = dict(res=res, settings={}, fail2={})` | `out`: the result. It keeps `res`, the result of the analysis script for B10. The next lines fill `settings` and `fail2`. |
| 297 | `    for s in sorted(res['settings'], key=skey):` | Loop over the settings that the analysis found, in the order of `skey`. |
| 298 | `        g = [p for p in used if p.setting == s]` | `g`: the used processes of this setting. |
| 299 | `        ks = {}` | `ks`: the values of this setting, one entry per kernel. |
| 300 | `        for k in ('oldwrite', 'write', 'asmwrite', 'asmwrite2'):` | Loop over the four write kernels. |
| 301 | `            tot, hl = [], []` | `tot`: the totals of the single intervals. `hl`: per process, the interval with the highest and the one with the lowest total. Both are empty at first. |
| 302 | `            for p in g:` | Loop over the processes of the setting. |
| 303 | `                ivs = p.rate_by_entry.get(k, [])` | `ivs`: the intervals of this kernel in the process. The B10 sequence of the run script names each kernel twice, and a process runs 2 rounds. So a kernel has 4 intervals per process. |
| 304 | `                tot += [(iv.hist, p.tag, iv.round, iv.pos, sum(x['passes'] for x in iv.rows)) for iv in ivs if not iv.irregular]` | Adds one entry per regular interval to `tot`: the total `M_hist`, the tag of the process, the round, the position, and the sum of the column `passes` over the T rows of the interval. |
| 305 | `                if ivs and not any(iv.irregular for iv in ivs):` | The next two lines run only when the process has intervals of the kernel and none of them is irregular. |
| 306 | `                    hi, lo = max(ivs, key=lambda iv: iv.hist), min(ivs, key=lambda iv: iv.hist)      # as a_b10 does` | `hi` and `lo`: the interval with the highest and the one with the lowest total `M_hist` of the kernel in this process. The comment says that the function `a_b10` of the analysis script does the same. |
| 307 | `                    hl.append(dict(tag=p.tag, hi=hi.hist, lo=lo.hist, hi_mesh=hi.mesh_hist, lo_mesh=lo.mesh_hist))` | Adds an entry for the process to `hl`: its tag, the two totals, and for each of the two intervals the `M_hist` values of mesh 0 and of mesh 1. |
| 308 | `            v = sorted(t[0] for t in tot)` | `v`: the totals of all regular intervals of the kernel in this setting, sorted upward. |
| 309 | `            ks[k] = dict(totals=tot, hl=hl, gap=max((b - a for a, b in zip(v, v[1:])), default=None),` | The entry of the kernel: the two lists, and `gap`. `gap` is the largest distance between two neighbouring totals of the sorted list, in GB/s. It is `None` with fewer than 2 totals. |
| 310 | `                         lo=v[0] if v else None, hi=v[-1] if v else None, med=med(v))` | Continues the entry: `lo`, `hi` and `med` are the lowest, the highest and the median total. |
| 311 | `        out['settings'][s] = ks` | Stores the values of the setting. |
| 312 | `        if s.startswith('pass/'):                               # the 2 % check of rule 7 (whole passes only)` | The next two lines run only for a setting with whole passes. The comment names the 2 % check of rule 7. |
| 313 | `            mp = [min(x['passes'] for x in iv.rows) for p in g for iv in regular(p)]` | `mp`: for every regular interval of the setting, the fewest passes of a thread (column `passes`). |
| 314 | `            out['fail2'][s] = (sum(1 for x in mp if x < 50), len(mp), min(mp, default=None), max(mp, default=None))` | Four values: the number of intervals in which a thread made fewer than 50 passes, the number of intervals, and the lowest and the highest value of `mp`. |
| 315 | `    return out` | Returns `out`. |
| 318 | `def b8_model(procs, res):` | Starts the function `b8_model`. It builds the values of step B8 for one session: read kernels with all threads of mesh 0 and several thread counts on mesh 1. |
| 319 | `    used = [p for p in procs if p.complete]` | `used`: the complete processes of the step. |
| 320 | `    out = dict(res=res, kern={}, counts=sorted({p.threads_mesh1 for p in used}), mesh0=sorted({p.threads_mesh0 for p in used}),` | `out`: the result. `counts`: the thread counts on mesh 1 that occur, sorted. `mesh0`: the thread counts on mesh 0 that occur. The analysis script counts the threads of each mesh from the CPU numbers in the T rows of the first interval of a process. |
| 321 | `               settings=sorted({p.setting for p in used}), n=len(used), aa_q=None)` | Continues `out`: the settings of the processes, the number of processes, and a place for `aa_q`. |
| 322 | `    for k in ('oldread', 'asmread', 'asmread2'):` | Loop over the three kernels of the B8 sequence. |
| 323 | `        out['kern'][k] = {b: [ivstat(iv) for p in used if p.threads_mesh1 == b for iv in regular(p, k)] for b in out['counts']}` | For this kernel: a dictionary from each mesh-1 thread count to the list of the `ivstat` values of the regular intervals of the kernel in the processes with that count. |
| 324 | `    dq = []` | `dq`: differences of q between the two copies of one loop, empty at first. |
| 325 | `    for p in used:                                             # A/A description: q of neighbouring asm read and asm read 2 intervals` | Loop over the used processes. The comment calls the next lines an A/A description: q of neighbouring intervals of asm read and asm read 2. |
| 326 | `        for a, b in zip(p.ordered, p.ordered[1:]):` | Loop over each pair of intervals that follow each other in the process. |
| 327 | `            if {a.entry, b.entry} == {'asmread', 'asmread2'} and not (a.irregular or b.irregular):` | Takes the pair when one interval is `asmread`, the other is `asmread2`, and both are regular. |
| 328 | `                dq.append(abs(a.q - b.q))` | Adds the absolute difference of q of the two intervals. |
| 329 | `    out['aa_q'] = max(dq) if dq else None` | `aa_q`: the largest of these differences, or `None`. It shows how much q differs between two runs of the same loop body. |
| 330 | `    return out` | Returns `out`. |

### `b5_model`, `b9_model`, `c3_model` and `old_q_at_full` (lines 333 to 381)

| Line | Source | Explanation |
|---:|---|---|
| 333 | `def b5_model(procs, res):` | Starts the function `b5_model`. It builds the values of step B5 for one session: old read against the load-only variants. |
| 334 | `    used = [p for p in procs if p.complete]` | `used`: the complete processes of the step. |
| 335 | `    entries = list(dict.fromkeys(en for p in used for en in (p.seq if 'oldread' in p.seq[:1] else p.seq[::-1])))` | `entries`: the kernels of the B5 sequence, each once, in the forward order. A process whose first kernel is `oldread` gives its sequence as it is. Every other process ran the reversed sequence, so its sequence is turned around first. |
| 336 | `    return dict(res=res, n=len(used), entries=entries, settings=sorted({p.setting for p in used}),` | Returns a dictionary: `res`, the number of processes, the kernels and the settings of the processes. |
| 337 | `                kern={k: [dict(ivstat(iv), tag=p.tag) for p in used for iv in regular(p, k)] for k in entries})` | Continues the dictionary. `kern`: for each kernel, the `ivstat` values of its regular intervals in all processes, each with the tag of its process. |
| 340 | `def b9_model(procs, res):` | Starts the function `b9_model`. It builds the values of step B9 for one session: old read with one buffer and with two buffers per thread. |
| 341 | `    used = [p for p in procs if p.complete]` | `used`: the complete processes of the step. |
| 342 | `    out = dict(res=res, kinds={}, settings=sorted({p.setting for p in used}))` | `out`: the result, with `res` and the settings of the processes. The next lines fill `kinds`. |
| 343 | `    for name, flag in (('one_buffer', False), ('two_buffers', True)):` | Loop over the two kinds of process: without and with the option `--two-buffers`. |
| 344 | `        g = [p for p in used if p.two_buffers == flag]` | `g`: the processes of this kind. |
| 345 | `        out['kinds'][name] = dict(n=len(g), ivs=[dict(ivstat(iv), tag=p.tag) for p in g for iv in regular(p)],` | The entry of the kind. `n`: the number of processes. `ivs`: the `ivstat` values of every regular interval, each with the tag of its process. |
| 346 | `                                  pv=[(p.tag, median(iv.hist for iv in p.ordered)) for p in g if not any(iv.irregular for iv in p.ordered)])` | Continues the entry. `pv`: the process values. For each process without an irregular interval: its tag, and the median of the totals `M_hist` of its intervals. |
| 347 | `    return out` | Returns `out`. |
| 350 | `def c3_model(procs, res):` | Starts the function `c3_model`. It builds the values of step C3 for one session: the runs with core counters. |
| 351 | `    used = [p for p in procs if p.complete]` | `used`: the complete processes of the step. |
| 352 | `    out = dict(res=res, n=len(used), cpu={}, lowest=None, n_rows=0, n_below99=0)` | `out`: the result, with `res`, the number of processes and the start values of the entries that the next lines fill. |
| 353 | `    for p in used:` | Loop over the used processes. |
| 354 | `        for c in p.C:` | Loop over the C rows of the process. A C row holds, for one thread and one interval, the enabled time and the running time of the counter group, the CPU time of the thread, and the counter values. |
| 355 | `            iv = p.raw.get((c['round'], c['pos']))` | `iv`: the interval with the round and the position of the C row. |
| 356 | `            t = next((x for x in iv.rows if x['tid'] == c['tid']), None) if iv else None` | `t`: the T row of the same thread in that interval, found by the thread number `tid`. It is `None` when the interval or the row is missing. |
| 357 | `            if t is None or not c['cputime'] or c['cputime'] <= 0:` | Tests whether the T row is missing, or the CPU time is missing or not above 0. |
| 358 | `                continue` | Such a C row is left out. This test does not look at the enabled time and the running time of the counter group. |
| 359 | `            share = c['cputime'] / (t['elapsed'] * 1e9)` | `share`: the CPU time of the thread divided by its elapsed time in the interval. The column `cputime_ns` is in ns, and the column `elapsed_s` of the T row is in s. In the runner source `bwx.c` the thread reads its CPU time directly before the first clock reading of the interval and directly after the last one. |
| 360 | `            off_ms = t['elapsed'] * 1e3 - c['cputime'] / 1e6` | `off_ms`: the elapsed time minus the CPU time, in ms. This is the time in which the thread did not have its CPU. |
| 361 | `            g = out['cpu'].setdefault(p.min_ms, dict(n=0, share_min=share, off_max=off_ms, below99=0))` | `g`: the entry for the interval length of the process, its option `--min-ms`. A new entry starts with the values of this row. |
| 362 | `            g['n'] += 1` | Counts the row in the entry. |
| 363 | `            g['share_min'], g['off_max'] = min(g['share_min'], share), max(g['off_max'], off_ms)` | Keeps the lowest share and the largest `off_ms` of the entry. |
| 364 | `            g['below99'] += share < 0.99` | Counts the row when its share is below 99 %. |
| 365 | `            out['n_rows'] += 1` | Counts the row over all interval lengths. |
| 366 | `            out['n_below99'] += share < 0.99` | Counts it over all interval lengths when its share is below 99 %. |
| 367 | `            if out['lowest'] is None or share < out['lowest']['share']:` | Tests whether this row has the lowest share so far. |
| 368 | `                out['lowest'] = dict(share=share, off_ms=off_ms, cpu=c['cpu'], kernel=c['kernel'], tag=p.tag, elapsed=t['elapsed'])` | `lowest`: the values of that row: the share, `off_ms`, the CPU, the kernel, the tag of the process and the elapsed time in s. |
| 369 | `    # per kernel and mesh: the group medians of the analysis (one group = one setting and sequence)` | Comment: the next lines collect the group medians of the analysis per kernel and mesh. One group is one setting and one sequence. |
| 370 | `    out['km'] = {}` | `km`: the dictionary for them, empty at first. |
| 371 | `    for g in res.get('groups', []):` | Loop over the groups of the analysis result. For C3 the analysis makes one group per setting, sequence (that of B7 or that of B5), kernel and mesh. Each group holds medians over its C rows. |
| 372 | `        out['km'].setdefault((g['entry'], g['mesh']), []).append(g)` | Adds the group to the list of its kernel and mesh. |
| 373 | `    return out` | Returns `out`. |
| 376 | `def old_q_at_full(procs):` | Starts the function `old_q_at_full`. It collects q and the total of the old read intervals at the full thread count, for the test of H9b. |
| 377 | `    """(q, total) of every regular old read interval with one buffer at the full thread count (64+56 on CRB), for H9b."""` | Description of `old_q_at_full`: one pair of q and total for every regular old read interval with one buffer at the full thread count, which is 64+56 on CRB. |
| 378 | `    full = max((p.threads for p in procs), default=0)` | `full`: the highest thread count of the processes given, from the option `--threads`. It is 0 when there is no process. |
| 379 | `    return [(iv.q, iv.hist) for p in procs if p.complete and p.step in ('B7', 'B5', 'B9', 'B8') and not p.two_buffers and p.threads == full` | Returns one pair of q and total `M_hist` per interval. The process must be complete, belong to step B7, B5, B9 or B8, run without `--two-buffers`, and have `full` threads. |
| 380 | `            for iv in regular(p, 'oldread')]` | Continues the list: only the regular intervals of `oldread` are taken. |

### The words of rule 11, and small text helpers (lines 382 to 437)

| Line | Source | Explanation |
|---:|---|---|
| 383 | `def norm(word):` | Starts the function `norm`. It maps a word of the analysis script to one of the five words of rule 11. |
| 384 | `    """A word of the analysis -> one of the five words of rule 11 (plus the plan's word in brackets, kept apart)."""` | Description of `norm`: the analysis can add the word of the plan in brackets. That part is not kept. |
| 385 | `    for w in ('not rejected', 'rejected', 'not observed', 'not resolved', 'not tested'):` | Loop over the five words. `not rejected` is tested before `rejected`. |
| 386 | `        if word.startswith(w):` | Tests whether the text starts with this word. |
| 387 | `            return w` | Returns the first word that fits. So `not rejected (supported)` gives `not rejected`. |
| 388 | `    return 'not resolved'` | A text that starts with none of the five words gives `not resolved`. |
| 391 | `def word_of(flags):` | Starts the function `word_of`. It turns the flags of the sessions into one of the five words. `flags` has one entry per session: `fail` (the bounded prediction failed in that session), `hold` (it held), `not observed` or `not resolved`. |
| 392 | `    """flags {session: fail \| hold \| not observed \| not resolved} -> one of the five words. The rule is two_sessions() of` | Description of `word_of`: the rule is the function `two_sessions` of the analysis script. |
| 393 | `    analyze_bwx.py. Added here: if no session gives 'fail' or 'hold' and at least one gives 'not resolved', the word is 'not resolved'."""` | Continues the description: this file adds one case. If no session gives `fail` or `hold` and at least one gives `not resolved`, the word is `not resolved`. |
| 394 | `    f_ = list(flags.values())` | `f_`: the flags as a list. |
| 395 | `    if not f_:` | Tests whether there is no flag. |
| 396 | `        return 'not tested'` | The word is then `not tested`. |
| 397 | `    if all(x in ('not resolved', 'not observed') for x in f_) and 'not resolved' in f_:` | The added case: every flag is `not resolved` or `not observed`, and at least one is `not resolved`. |
| 398 | `        return 'not resolved'` | The word is then `not resolved`. |
| 399 | `    return norm(A.two_sessions(flags))` | In every other case the word comes from `A.two_sessions`. That function gives `not observed` when every session says `not observed`. It gives `rejected` when there are at least 2 sessions and every one says `fail`. In the other cases it gives `not rejected`. So with one session the word is `not rejected`, also when the flag is `fail`. |
| 402 | `PLAN_OLD_LOW = (365.10, 368.25)     # plan, item 10: totals of old read on 2026-10-30 (GB/s). A number of an earlier folder, for H9b only.` | `PLAN_OLD_LOW`: the lowest and the highest total of old read on 2026-10-30, 365.10 and 368.25 GB/s, typed in from item 10 of the plan [Ref1]. The comment says that it is a number of an earlier result folder and is used for H9b only. |
| 405 | `def join_and(items):` | Starts the function `join_and`. It joins words into a list for a sentence. |
| 406 | `    items = list(items)` | Turns the input into a list. |
| 407 | `    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1] if items else ''` | Returns the one word alone, or two words with `and` between them, or the form `a, b and c`. An empty list gives an empty text. |
| 410 | `def rngs(vals, nd=2):` | Starts the function `rngs`. It does the work of `rng` with a sign on each number. |
| 411 | `    v = [x for x in vals if x is not None]` | `v`: the entries of `vals` that are not `None`. |
| 412 | `    return '-' if not v else fs(min(v), nd) if len(v) == 1 or fs(min(v), nd) == fs(max(v), nd) else f'{fs(min(v), nd)} to {fs(max(v), nd)}'` | Returns `-` when no entry is left. It returns one signed number when there is one entry, or when the lowest and the highest print the same. If not, it returns the two signed numbers with the word `to` between them. |
| 415 | `def larger_with(c, change):` | Starts the function `larger_with`. `c` is a comparison of two settings that differ in one factor. `change` is the value of the first setting minus the value of the second. The function names in words the factor value of the setting with the larger value. |
| 416 | `    """The factor value of the setting with the larger value (change = first minus second)."""` | Description of `larger_with`: the factor value of the setting with the larger value. |
| 417 | `    stop, ms, start = (c['second'] if change < 0 else c['first']).split('/')` | Takes the second setting when `change` is below 0, and the first setting in every other case. Then it splits that setting into its three parts. |
| 418 | `    if c['factor'] == 'stop':` | Tests whether the factor is the stop method. |
| 419 | `        return 'the common stop' if stop == 'common' else 'whole passes'` | Returns `the common stop` or `whole passes`. |
| 420 | `    if c['factor'] == 'interval':` | Tests whether the factor is the interval. |
| 421 | `        return f'the {int(ms) / 1000:g} s interval'` | Returns the interval length in seconds, such as `the 0.5 s interval`. |
| 422 | `    return 'the offset start' if start == 'offset' else 'the common start'` | For the factor start: returns `the offset start` or `the common start`. |
| 425 | `def isare(n):` | Starts the function `isare`. |
| 426 | `    return 'is' if n == 1 else 'are'` | Returns `is` for the count 1 and `are` for every other count. |
| 429 | `def flag_txt(flags):` | Starts the function `flag_txt`. It prints the flags of the sessions. |
| 430 | `    return ', '.join(f'{s}: {v}' for s, v in flags.items()) or '-'` | Returns a text such as `s1: fail, s2: fail`, or `-` when there is no flag. |
| 433 | `TWO_WORDS = ('Rule 11 of the plan has two words that fit this case. "rejected": the bounded prediction (a resolved change) failed in every session. '` | `TWO_WORDS`: a typed text for the page, used where a prediction of a resolved change failed in every session. This line: rule 11 of the plan has two words that fit this case, and `rejected` means that the bounded prediction failed in every session. |
| 434 | `             '"not resolved": the difference is inside the A/A spread. The plan words the outcome of this step as "no resolved contribution". '` | Continues the text: `not resolved` means that the difference is inside the A/A spread. The plan words the outcome of the step as `no resolved contribution`. |
| 435 | `             'The analysis script maps "no resolved change" to a failed prediction, and its authors call that mapping their own reading.')` | Continues the text: the analysis script maps `no resolved change` to a failed prediction, and its authors call that mapping their own reading. |

### `hypotheses`: start, and the inner helpers `have`, `add` and `strict_of` (lines 438 to 457)

| Line | Source | Explanation |
|---:|---|---|
| 438 | `def hypotheses(m):` | Starts the function `hypotheses`. It builds the rows of the hypothesis table of the page: one row for each hypothesis of Q2, and one for the statement of step B5. `m` is the model. |
| 439 | `    """One row per hypothesis of Q2. Every word is computed.` | Description of `hypotheses`: one row per hypothesis of Q2, and every word is computed. |
| 440 | `    word   = the word of this page.            strict = the output of the analysis script (or of the plan's rule) as it stands.` | Continues the description: `word` is the word of this page. `strict` is the unchanged output of the analysis script, or of the rule of the plan. |
| 441 | `    other  = another reading of the same data, with its reason.     open = what the user must decide ('' if nothing)."""` | Continues the description: `other` is another reading of the same data with its reason. `open` is what the user must decide, and it is empty when nothing is open. |
| 442 | `    S, hyp, names = m['S'], m['summary']['hypotheses'], m['sessions']` | `S`: the model of each session. `hyp`: the entries of the analysis script per hypothesis. Each entry holds a word over the sessions and the flag of each session. `names`: the session names. |
| 443 | `    one = len(names) < 2` | `one`: true when the page has fewer than 2 sessions. |
| 444 | `    rows = []` | `rows`: the result, empty at first. |
| 446 | `    def have(step):` | Starts the inner function `have`. |
| 447 | `        return [s for s in names if step in S[s]]` | Returns the sessions whose model holds data of the step. |
| 449 | `    def add(label, meaning, text, step, word, n, aa, basis, flags, plan_word='', strict='-', other='', open_='', short=''):` | Starts the inner function `add`. It adds one row. Its arguments are: the label, the meaning in plain words, the bounded prediction, the step, the word of the page, a text on the number of processes, a text on the A/A spread or control, the basis sentences, the flags per session, the word of the plan, the output of the analysis rule, the other reading, the open question, and a short text for the list at the top of the page. |
| 450 | `        rows.append(dict(label=label, meaning=meaning, text=text, step=step, word=word, n=n, aa=aa, basis=basis, flags=flags, plan_word=plan_word,` | Adds the row to `rows` as a dictionary with these values. |
| 451 | `                         strict=strict, other=other, open=open_, short=short,` | Continues the dictionary: the output of the analysis rule, the other reading, the open question and the short text. |
| 452 | `                         one_session=one and word == 'not rejected' and any(v == 'fail' for v in flags.values())))` | Continues the dictionary. `one_session`: true when the page has one session, the word is `not rejected`, and the flag of a session is `fail`. The page then adds the note that the prediction failed in this session (line 1031). |
| 454 | `    def strict_of(key):` | Starts the inner function `strict_of`. It gives the output of the analysis script for one hypothesis as text. |
| 455 | `        h = hyp.get(key)` | `h`: the entry of the analysis script under this key, or `None`. |
| 456 | `        return f'"{h["word"]}" ({flag_txt(h["per_session"])})' if h else 'no entry'` | Returns the word in double quotes and the flags of the sessions in brackets, for example `"rejected" (s1: fail, s2: fail)`. Without an entry it returns `no entry`. |

### `hypotheses`: H7a and H7b for the read kernels (step B7) (lines 458 to 500)

| Line | Source | Explanation |
|---:|---|---|
| 458 | `    # ---- H7a, H7b for read (B7)` | Comment: the next block makes the rows of H7a and H7b for read, from step B7. |
| 459 | `    for hl, key, meaning, text, factors in (` | Loop over two hypotheses. Each pass gets the label of the row, the key of the entry in `hyp`, the meaning, the bounded prediction, and the timing factors that belong to the hypothesis. |
| 460 | `            ('H7a, read', 'H7a (B7, read)', 'the stop method and the short interval make a part of the read difference', 'D changes by a resolved amount when the stop method or the interval changes', ('stop', 'interval')),` | The values for H7a: the stop method and the short interval make a part of the read difference. Its prediction: D changes by a resolved amount when the stop method or the interval changes. Its factors are `stop` and `interval`. |
| 461 | `            ('H7b, read', 'H7b (B7, read)', 'the common start makes a part of the read difference', 'D changes by a resolved amount when the start changes', ('start',))):` | The values for H7b: the common start makes a part of the read difference. Its prediction: D changes by a resolved amount when the start changes. Its factor is `start`. |
| 462 | `        ss = have('B7')` | `ss`: the sessions with data of B7. |
| 463 | `        if not ss:` | Tests whether no session has B7. |
| 464 | `            add(hl, meaning, text, 'B7', 'not tested', '-', '-', f'{ID}: no B7 process in the input.', {}, short='no B7 process in the input'); continue` | Then the row gets the word `not tested`, with a basis that starts with `Insufficient data` and says that the input holds no B7 process. The loop goes on with the next hypothesis. |
| 465 | `        flags = hyp.get(key, {}).get('per_session', {})` | `flags`: the flag of each session from the analysis script. For these two hypotheses the analysis gives `hold` when at least one comparison of the factors is resolved, and `fail` when none is. It gives `not resolved` when none is resolved and `M_hist` and `M_sum` disagree for a pair of settings. It gives `not observed` when no comparison has a value, or when the reproduction condition shows no resolved D with old read above new read. |
| 466 | `        parts, allch, allres, medD = [], [], [], {}` | Four start values. `parts`: the sentences of the basis. `allch`: the comparisons with a value, over all sessions. `allres`: the resolved ones. `medD`: a median D per session. |
| 467 | `        for s in ss:` | Loop over the sessions with B7. |
| 468 | `            res = S[s]['B7']['res']` | `res`: the result of the analysis for B7 in this session. |
| 469 | `            ch = [c for c in res['changes'].values() if c['factor'] in factors and c['metrics']['M_hist']['change'] is not None]` | `ch`: the comparisons of two settings that differ only in a factor of this hypothesis, and that have a value. The value of a comparison is the median D of the first setting minus the median D of the second, with `M_hist`. Each median runs over the processes of the setting, one D per process. The first setting is the one with whole passes, with the shorter interval, or with the common start. |
| 470 | `            r = [c for c in ch if c['decision'] == 'resolved']` | `r`: the comparisons whose decision is `resolved`. A change is resolved when its absolute value is above the sum of the A/A spreads of the two settings, when every D of one setting lies on one side of every D of the other, and when `M_sum` gives the same word as `M_hist`. |
| 471 | `            medD[s] = med([v['metrics']['M_hist']['median_D'] for v in res['settings'].values()])` | `medD` of the session: the median over its settings of the median D with `M_hist`. |
| 472 | `            allch += [(s, c) for c in ch]; allres += [(s, c) for c in r]` | Adds the comparisons to `allch` and the resolved ones to `allres`, each with its session. |
| 473 | `            parts.append(f"Session {s}: {len(r)} of {len(ch)} comparisons of two settings {isare(len(r))} resolved"` | Adds a sentence for the session: how many of its comparisons of two settings are resolved. |
| 474 | `                         + (f" ({join_and(fs(c['metrics']['M_hist']['change']) for c in r)} GB/s, first setting minus second)" if r else '') + '.')` | Continues the sentence: when some are resolved, it lists their changes in GB/s with a sign, first setting minus second. |
| 475 | `        chg = lambda c: c['metrics']['M_hist']['change']` | `chg`: a small function that gives the change of a comparison with `M_hist`. |
| 476 | `        lim = lambda c: c['metrics']['M_hist']['sum_of_aa_spreads']` | `lim`: a small function that gives the limit of a comparison: the sum of the A/A spreads of its two settings. |
| 477 | `        if allres:` | The next six lines run only when a comparison is resolved. |
| 478 | `            cnt = {}` | `cnt`: counts the resolved comparisons by the factor value with the larger D. |
| 479 | `            for s, c in allres:` | Loop over the resolved comparisons. |
| 480 | `                cnt[larger_with(c, chg(c))] = cnt.get(larger_with(c, chg(c)), 0) + 1` | Adds 1 to the count of the factor value that `larger_with` names for this comparison. |
| 481 | `            parts.append('In the resolved comparisons D is larger with ' + join_and(f'{k} ({n} of {len(allres)})' for k, n in cnt.items()) + '.')` | Adds a sentence that says with which factor value D is larger in the resolved comparisons, and in how many of them. |
| 482 | `            bs, bc = max(allres, key=lambda t: abs(chg(t[1])))` | `bs` and `bc`: the session and the comparison with the largest absolute resolved change. |
| 483 | `            if medD[bs]:` | The next line runs only when the median D of that session exists and is not 0. |
| 484 | `                parts.append(f'The largest resolved change is {fx(abs(chg(bc)) / abs(medD[bs]) * 100, 1)} % of the median D of session {bs}.')` | Adds a sentence with a ratio: the largest absolute resolved change divided by the absolute median D of that session, in % with 1 decimal. |
| 485 | `        unres = [(s, c) for s, c in allch if c['decision'] != 'resolved']` | `unres`: the comparisons that are not resolved. |
| 486 | `        if unres:` | The next four lines run only when there is one. |
| 487 | `            inside = sum(1 for _, c in unres if abs(chg(c)) <= lim(c))` | `inside`: the number of them whose absolute change is at or below its limit. |
| 488 | `            parts.append(f"The {pl(len(unres), 'change that is not resolved is', 'changes that are not resolved are')} {rngs([chg(c) for _, c in unres])} GB/s. "` | Adds a sentence with the number of changes that are not resolved and with their range in GB/s, with signs. |
| 489 | `                         f"{'Its limit (sum of the two A/A spreads) is' if len(unres) == 1 else 'Their limits (sum of the two A/A spreads) are'} {rng([lim(c) for _, c in unres])} GB/s. "` | Continues the text: a sentence with the range of their limits in GB/s. |
| 490 | `                         f"{inside} of {len(unres)} {'lies' if inside == 1 else 'lie'} inside the limit.")` | Continues the text: a sentence that says how many of them lie inside the limit. |
| 491 | `        if allch and not allres and all(medD.values()):` | The next line runs only when there are comparisons, none is resolved, and every session has a median D that is not 0. |
| 492 | `            parts.append(f"So this test could not show a contribution below its limit, which is up to {fx(max(lim(c) for _, c in allch) / min(abs(v) for v in medD.values()) * 100, 1)} % of the median D.")` | Adds a sentence on what the test could show: the largest limit divided by the smallest absolute median D of a session, in %. The text says that the test could not show a contribution below that share of the median D. |
| 493 | `        nset = sum(len(S[s]['B7']['res']['settings']) for s in ss); nresD = sum(1 for s in ss for v in S[s]['B7']['res']['settings'].values() if v['decision'] == 'resolved')` | `nset`: the number of settings over all sessions. `nresD`: the number of them in which D itself is resolved. |
| 494 | `        parts.append(f"D itself is resolved in {nresD} of {nset} settings" + (', so no timing setting removes it.' if nresD == nset else '.'))` | Adds a sentence with these two counts. When D is resolved in every setting, it adds that no timing setting removes D. |
| 495 | `        aa = [v['metrics']['M_hist']['aa_spread'] for s in ss for v in S[s]['B7']['res']['settings'].values()]` | `aa`: the A/A spread of every setting of every session, with `M_hist`. The A/A spread of a setting is the largest absolute E over its processes. E is the total of `asmread2` minus the total of `asmread` in one process, the difference between two copies of one loop. |
| 496 | `        w = word_of(flags)` | `w`: the word of the page, from the flags (lines 391 to 399). |
| 497 | `        add(hl, meaning, text, 'B7', w, ', '.join(f"{s}: {S[s]['B7']['n_main']} with all kernels, {S[s]['B7']['n_single']} with one kernel" for s in ss),` | Adds the row. The text on the processes gives, per session, the number of processes with all kernels and the number with one kernel. |
| 498 | `            f'{rng(aa)} GB/s over the settings', ' '.join(parts), flags, strict=strict_of(key),` | Continues the call: the range of the A/A spreads in GB/s, the basis sentences joined by spaces, the flags, and the output of the analysis script. |
| 499 | `            other=TWO_WORDS if w == 'rejected' else '', open_='"rejected" or "not resolved"' if w == 'rejected' else '',` | Continues the call: when the word is `rejected`, the row also gets the text `TWO_WORDS` as the other reading, and the open question whether the word is `rejected` or `not resolved`. |
| 500 | `            short='resolved comparisons of two settings: ' + join_and(f"{sum(1 for x, _ in allres if x == s)} of {sum(1 for x, _ in allch if x == s)} in {s}" for s in ss))` | Continues the call: the short text gives, per session, how many of its comparisons are resolved. |

### `hypotheses`: H7a and H7b for the write kernels (step B10) (lines 501 to 541)

| Line | Source | Explanation |
|---:|---|---|
| 501 | `    # ---- H7a, H7b for write (B10)` | Comment: the next block makes the rows of H7a and H7b for write, from step B10. |
| 502 | `    for hl, key, meaning, text, factors in (` | Loop over the same two hypotheses, now for the write kernels. |
| 503 | `            ('H7a, write', 'H7a (B10, write)', 'the stop method and the short interval make a part of the separate write totals', 'the spread of a write kernel changes by a resolved amount when the stop method or the interval changes', ('stop', 'interval')),` | The values for H7a for write: the stop method and the short interval make a part of the separate write totals. Its prediction: the spread of a write kernel changes by a resolved amount when the stop method or the interval changes. The spread of a kernel in one process is the highest minus the lowest total of its 4 intervals. |
| 504 | `            ('H7b, write', 'H7b (B10, write)', 'the common start makes a part of the separate write totals', 'the spread of a write kernel changes by a resolved amount when the start changes', ('start',))):` | The values for H7b for write: the common start makes a part of the separate write totals. Its prediction: the spread changes by a resolved amount when the start changes. |
| 505 | `        ss = have('B10')` | `ss`: the sessions with data of B10. |
| 506 | `        if not ss:` | Tests whether no session has B10. |
| 507 | `            add(hl, meaning, text, 'B10', 'not tested', '-', '-', f'{ID}: no B10 process in the input.', {}, short='no B10 process in the input'); continue` | Then the row gets the word `not tested`, and the loop goes on with the next hypothesis. |
| 508 | `        flags = hyp.get(key, {}).get('per_session', {})` | `flags`: the flag of each session from the analysis script: `hold` when at least one comparison of a spread is resolved, `fail` when none is, and `not observed` when no comparison has a value. |
| 509 | `        parts, allch, allres = [], [], []` | Three start values: the basis sentences, all comparisons with a value, and the resolved ones. |
| 510 | `        for s in ss:` | Loop over the sessions with B10. |
| 511 | `            sc = S[s]['B10']['res']['spread_changes']` | `sc`: the comparisons of the analysis for this session. Each one is for one kernel and two settings that differ in one factor. |
| 512 | `            ch = [c for c in sc.values() if c['factor'] in factors and c['change_of_spread'] is not None]` | `ch`: the comparisons of the factors of this hypothesis that have a value. The value is the median spread of the kernel in the first setting minus that in the second. Each median runs over the processes of the setting. |
| 513 | `            r = [c for c in ch if c['decision'] == 'resolved']` | `r`: the resolved ones. A change of the spread is resolved when its absolute value is above the sum of the controls of the spread of the two settings, and the spreads of the two settings do not overlap. The control of the spread of a setting is the largest absolute difference, over its processes, between the spread of `asmwrite2` and the spread of `asmwrite`. |
| 514 | `            allch += [(s, c) for c in ch]; allres += [(s, c) for c in r]` | Adds the comparisons to `allch` and the resolved ones to `allres`, each with its session. |
| 515 | `            parts.append(f"Session {s}: {len(r)} of {len(ch)} comparisons (one kernel, two settings) {isare(len(r))} resolved.")` | Adds a sentence for the session: how many of its comparisons are resolved. |
| 516 | `            for c in r:` | Loop over the resolved comparisons of the session. |
| 517 | `                parts.append(f"The resolved one: {KN[c['kernel']]}, {c['factor']}, \"{sname(c['first'])}\" minus \"{sname(c['second'])}\": the median spread changes by {fs(c['change_of_spread'])} GB/s, limit {f(c['sum_of_controls'])} GB/s.")` | Adds a sentence for the resolved comparison: the kernel, the factor, the two settings in words, the change of the median spread in GB/s with a sign, and its limit. |
| 518 | `                twin = {'asmwrite': 'asmwrite2', 'asmwrite2': 'asmwrite'}.get(c['kernel'])` | `twin`: the other copy of the loop when the kernel is `asmwrite` or `asmwrite2`. For the two other kernels it is `None`. |
| 519 | `                t = next((x for x in sc.values() if x['kernel'] == twin and (x['factor'], x['first'], x['second']) == (c['factor'], c['first'], c['second'])), None)` | `t`: the comparison of the twin for the same factor and the same two settings, or `None`. |
| 520 | `                if t and t['change_of_spread'] is not None:` | The next line runs only when the twin has a value. |
| 521 | `                    parts.append(f"The second copy of the same loop ({KN[twin]}) in the same two settings: {fs(t['change_of_spread'])} GB/s, {t['decision']}.")` | Adds a sentence with the change of the second copy of the same loop in the same two settings, and with its decision. |
| 522 | `        if allres:` | The next four lines run only when a comparison is resolved. |
| 523 | `            none = [k for k in ('oldwrite', 'write', 'asmwrite', 'asmwrite2') if not any(c['kernel'] == k for _, c in allres)]` | `none`: the kernels without a resolved comparison in any session. |
| 524 | `            if none:` | The next line runs only when there is such a kernel. |
| 525 | `                parts.append(f"No comparison of {join_and(KN[k] for k in none)} is resolved in any session.")` | Adds a sentence that names these kernels. |
| 526 | `            parts.append(f"{len(allch)} comparisons were made, with no correction for their number.")` | Adds a sentence with the number of comparisons that were made. It says that no correction for their number was applied. |
| 527 | `        unres = [(s, c) for s, c in allch if c['decision'] != 'resolved']` | `unres`: the comparisons that are not resolved. |
| 528 | `        if unres:` | The next three lines run only when there is one. |
| 529 | `            inside = sum(1 for _, c in unres if abs(c['change_of_spread']) <= c['sum_of_controls'])` | `inside`: the number of them whose absolute change is at or below the sum of the two controls. |
| 530 | `            parts.append(f"The {len(unres)} changes that are not resolved are {rngs([c['change_of_spread'] for _, c in unres])} GB/s. Their limits (sum of the two controls of the spread) are {rng([c['sum_of_controls'] for _, c in unres])} GB/s. "` | Adds two sentences: the range of the changes that are not resolved, with signs, and the range of their limits, both in GB/s. |
| 531 | `                         f"{inside} of {len(unres)} {'lies' if inside == 1 else 'lie'} inside the limit.")` | Continues the text: a sentence that says how many of them lie inside the limit. |
| 532 | `        if allch and not allres:` | The next two lines run only when there are comparisons and none is resolved. |
| 533 | `            sp = [x for s in ss for v in S[s]['B10']['res']['settings'].values() for kk in v['kernels'].values() for x in [kk['median_spread']] if x is not None]` | `sp`: the median spread of every kernel in every setting of every session, where it exists. |
| 534 | `            parts.append(f"The median spread of a kernel in a setting is {rng(sp)} GB/s. So only a change as large as most spreads could have been resolved.")` | Adds two sentences: the range of these median spreads in GB/s, and the conclusion that only a change as large as most spreads could have been resolved. |
| 535 | `        cs = [v['control_spread'] for s in ss for v in S[s]['B10']['res']['settings'].values()]` | `cs`: the control of the spread of every setting of every session. |
| 536 | `        w = word_of(flags)` | `w`: the word of the page, from the flags. |
| 537 | `        add(hl, meaning, text, 'B10', w, ', '.join(f"{s}: {S[s]['B10']['res']['n_used']}" for s in ss), f'{rng(cs)} GB/s (control of the spread, over the settings)',` | Adds the row. The text on the processes gives the number of used processes per session. The next text gives the range of the controls of the spread in GB/s. |
| 538 | `            ' '.join(parts), flags, strict=strict_of(key),` | Continues the call: the basis sentences, the flags, and the output of the analysis script. |
| 539 | `            other=('' if w != 'rejected' else TWO_WORDS if not any(r['other'] == TWO_WORDS for r in rows) else 'The same two readings of rule 11 as for H7b, read.'),` | Continues the call: the other reading. It is empty unless the word is `rejected`. Then it is the text `TWO_WORDS` when no earlier row holds that text. When an earlier row holds it, a short sentence names the row `H7b, read` as the place of the two readings. The sentence names that row also when the earlier row is `H7a, read`. |
| 540 | `            open_='"rejected" or "not resolved"' if w == 'rejected' else '',` | Continues the call: the open question, set only when the word is `rejected`. |
| 541 | `            short='resolved comparisons of two settings: ' + join_and(f"{sum(1 for x, _ in allres if x == s)} of {sum(1 for x, _ in allch if x == s)} in {s}" for s in ss))` | Continues the call: the short text gives, per session, how many of its comparisons are resolved. |

### `hypotheses`: H11 (page rule 2) (lines 542 to 586)

| Line | Source | Explanation |
|---:|---|---|
| 542 | `    # ---- H11 (page rule 2)` | Comment: the next block makes the row of H11 by page rule 2. |
| 543 | `    ss = have('B10')` | `ss`: the sessions with data of B10. |
| 544 | `    cells = {k: v for k, v in hyp.items() if k.startswith('H11 (B10')}` | `cells`: the entries of the analysis script for H11. There is one per setting and write kernel. Each holds a word over the sessions, and the result of each session. |
| 545 | `    meaning, text = 'the higher write totals come from the threads of one mesh', 'in an interval with a higher total, one mesh is faster by a resolved amount and the other is not'` | The meaning of H11 in plain words: the higher write totals come from the threads of one mesh. Its bounded prediction: in an interval with a higher total, one mesh is faster by a resolved amount and the other is not. |
| 546 | `    if not ss or not cells:` | Tests whether no session has B10 or the analysis gave no cell. |
| 547 | `        add('H11', meaning, text, 'B10', 'not tested', '-', '-', f'{ID}: no B10 process in the input.', {}, short='no B10 process in the input')` | Then the row gets the word `not tested`. |
| 548 | `    else:` | In every other case the lines up to line 586 run. |
| 549 | `        w = [norm(v['word']) for v in cells.values()]` | `w`: the word of each cell, as one of the five words. For a cell with a result in 2 or more sessions, the analysis gives `not rejected` only when every session supports it, and `rejected` only when every session contradicts it. For a cell with a result in one session only, it gives `not rejected` whenever that result is not `not observed`, also when the result is `contradicted` or `not resolved`. On a page with one session this holds for every cell. |
| 550 | `        cnt = {x: w.count(x) for x in ('not rejected', 'rejected', 'not observed', 'not resolved')}` | `cnt`: the number of cells with each of the four words. |
| 551 | `        word = 'not observed' if cnt['not observed'] == len(w) else 'rejected' if cnt['rejected'] and cnt['rejected'] == len(w) - cnt['not observed'] else \` | Page rule 2. The word is `not observed` when every cell is `not observed`. It is `rejected` when at least one cell is `rejected` and every cell that is not `not observed` is `rejected`. |
| 552 | `            'not rejected' if cnt['not rejected'] and not cnt['rejected'] else 'not resolved'` | Continues page rule 2: the word is `not rejected` when at least one cell is `not rejected` and none is `rejected`. In every other case it is `not resolved`. |
| 553 | `        per = {s: {x: sum(1 for v in cells.values() if v['per_session'].get(s) == x) for x in ('supported', 'contradicted', 'not observed', 'not resolved')} for s in ss}` | `per`: for each session, the number of cells with each result of that session: `supported`, `contradicted`, `not observed` or `not resolved`. These are the words of the rule for H11 in one session. |
| 554 | `        both = sum(1 for v in cells.values() if len(v['per_session']) > 1 and all(x == 'supported' for x in v['per_session'].values()))` | `both`: the number of cells that have more than one session and are `supported` in every one. |
| 555 | `        ct = [v['control_total'] for s in ss for v in S[s]['B10']['res']['settings'].values() if v['control_total'] is not None]` | `ct`: the control of the total of every setting of every session. It is the largest absolute difference of the total between two neighbouring intervals of `asmwrite` and `asmwrite2` in the setting. |
| 556 | `        parts = ['A cell is one kernel in one setting. ' + ' '.join(` | `parts` starts with a sentence that says what a cell is. |
| 557 | `            f"Session {s}: " + join_and(f"{n} {x}" for x, n in per[s].items() if n) + '.' for s in ss)]` | Continues the text: one sentence per session with its number of cells per result. |
| 558 | `        sup = []` | `sup`: the details of the supported cells, empty at first. |
| 559 | `        for s in ss:` | Loop over the sessions with B10. |
| 560 | `            b = S[s]['B10']` | `b`: the model of B10 for this session. |
| 561 | `            for st in b['settings']:` | Loop over the settings of the session. |
| 562 | `                v = b['res']['settings'][st]` | `v`: the result of the analysis for this setting. |
| 563 | `                for k in b['settings'][st]:` | Loop over the kernels of the setting. |
| 564 | `                    if v['kernels'][k]['H11'] != 'supported':` | Tests whether the result of the cell in this session is not `supported`. |
| 565 | `                        continue` | Such a cell is left out. |
| 566 | `                    hl_ = [h for h in b['settings'][st][k]['hl'] if (h['hi'] - h['lo']) > v['control_total']]` | `hl_`: the counted processes of the cell. A process counts when its highest total of this kernel minus its lowest total is above the control of the total. |
| 567 | `                    d = {0: [h['hi_mesh'][0] - h['lo_mesh'][0] for h in hl_], 1: [h['hi_mesh'][1] - h['lo_mesh'][1] for h in hl_]}` | `d`: for each mesh, the list over the counted processes of the rate of the mesh in the highest interval minus its rate in the lowest interval. |
| 568 | `                    c = {0: v['control_mesh0'], 1: v['control_mesh1']}` | `c`: the control of the rate of each mesh. It is the largest absolute difference of the rate of that mesh between two neighbouring intervals of `asmwrite` and `asmwrite2`. |
| 569 | `                    rose = [i for i in (0, 1) if all(abs(x) > c[i] for x in d[i])]` | `rose`: the meshes whose change is above the control of the mesh in every counted process. The test uses the absolute value of the change. The sign was tested before by the rule of the analysis: a cell is `supported` only when the one changed mesh got faster. |
| 570 | `                    sup.append(dict(s=s, st=st, k=k, rose=rose, d=d, c=c, n=len(hl_)))` | Adds the details of the cell to `sup`. |
| 571 | `        if not one:` | The next line runs only with more than one session. |
| 572 | `            parts.append(f"{both} of {len(w)} cells are supported in every session. The merged cells are: " + join_and(f"{n} {x}" for x, n in cnt.items() if n) + '.')` | Adds two sentences: the number of cells that are supported in every session, and the number of cells per word over the sessions. |
| 573 | `        for x in sup:` | Loop over the supported cells. |
| 574 | `            if len(x['rose']) == 1:` | The next three lines run only when exactly one mesh is in `rose`. |
| 575 | `                i = x['rose'][0]; j = 1 - i` | `i`: that mesh. `j`: the other mesh. |
| 576 | `                parts.append(f"Supported in {x['s']}: {KN[x['k']]} with \"{sname(x['st'])}\". Mesh {i} rose by {rng(x['d'][i])} GB/s (control {f(x['c'][i])} GB/s) in its {x['n']} counted processes. "` | Adds two sentences for the supported cell. They give the session, the kernel, the setting, the range of the rise of mesh `i` in GB/s with its control, and the number of counted processes. |
| 577 | `                             f"Mesh {j} changed by {rngs(x['d'][j])} GB/s, below its control of {f(x['c'][j])} GB/s.")` | Continues the text: a sentence with the range of the change of mesh `j`, with signs, and its control. |
| 578 | `        rs = {x['rose'][0] for x in sup if len(x['rose']) == 1}` | `rs`: the set of the meshes that changed alone in a supported cell. |
| 579 | `        if len(sup) > 1:` | The next line runs only with more than one supported cell. |
| 580 | `            parts.append('The supported cells name different meshes.' if len(rs) > 1 else f"The supported cells all name mesh {next(iter(rs))}." if rs else '')` | Adds a sentence that says whether the supported cells name different meshes or all the same mesh. |
| 581 | `        add('H11', meaning, text, 'B10', word, ', '.join(f"{s}: {S[s]['B10']['res']['n_used']} (4 per setting)" for s in ss), f'{rng(ct)} GB/s (control of the total, over the settings)',` | Adds the row of H11. The text on the processes gives the number of used processes per session, with the typed note `4 per setting`. The next text gives the range of the controls of the total in GB/s. |
| 582 | `            ' '.join(p for p in parts if p), {s: join_and(f"{n} {x}" for x, n in per[s].items() if n) for s in ss},` | Continues the call: the basis sentences without empty ones. As the flag of each session, the row gets the text with its number of cells per result. |
| 583 | `            plan_word='supported' if word == 'not rejected' else 'contradicted' if word == 'rejected' else '',` | Continues the call: the word of the plan that the page prints in brackets. It is `supported` for `not rejected`, `contradicted` for `rejected`, and empty for the other words. |
| 584 | `            strict='one word per cell: ' + join_and(f'{n} "{x}"' for x, n in cnt.items() if n),` | Continues the call: as the output of the analysis rule, the number of cells per word. |
| 585 | `            short='one mesh rose alone in ' + join_and(f"{per[s]['supported']} of {len(w)} cells in {s}" for s in ss) + ('' if one else f'. Cells in which it did so in every session: {both}'))` | Continues the call: the short text says in how many cells of each session one mesh rose alone. With more than one session it adds the number of cells in which this holds in every session. |
| 586 | `        rows[-1]['cells'] = cnt` | Stores the counts per word in the row. No later line of this file reads them. |

### `hypotheses`: H8 and the statement of step B5 (page rule 1) (lines 587 to 639)

| Line | Source | Explanation |
|---:|---|---|
| 587 | `    # ---- H8 (page rule 1)` | Comment: the next block makes the row of H8 by page rule 1. |
| 588 | `    ss = have('B8')` | `ss`: the sessions with data of B8. |
| 589 | `    meaning, text = 'a loop that only loads reaches the uniform state at a lower thread count than old read', 'asm read changes to the uniform pattern at a lower count of mesh-1 threads than old read'` | The meaning of H8: a loop that only loads reaches the uniform state at a lower thread count than old read. Its bounded prediction: asm read changes to the uniform pattern at a lower count of mesh-1 threads than old read. |
| 590 | `    if not ss:` | Tests whether no session has B8. |
| 591 | `        add('H8', meaning, text, 'B8', 'not tested', '-', '-', f'{ID}: no B8 process in the input.', {}, short='no B8 process in the input')` | Then the row gets the word `not tested`. |
| 592 | `    else:` | In every other case the lines up to line 608 run. |
| 593 | `        aq = [S[s]['B8']['aa_q'] for s in ss if S[s]['B8']['aa_q'] is not None]` | `aq`: the value `aa_q` of each session that has one (line 329). |
| 594 | `        nb = sum(1 for s in ss for kv in S[s]['B8']['res'].get('kernels', {}).values() if kv.get('bracket'))` | `nb`: the number of brackets that the label rule of the analysis formed, counted over the sessions and the kernels. A bracket is a pair of mesh-1 thread counts: up to the first one every tested count has the label `split`, and from the second one on every tested count has the label `uniform`. |
| 595 | `        parts = ['The bracket rule needs the labels split and uniform, which are not used. ' + ('No bracket was formed by the label rule in any session.' if not nb else f'The label rule formed {pl(nb, "bracket", "brackets")}.')]` | `parts` starts with two sentences: the bracket rule needs the labels, which are not used, and how many brackets the label rule formed. |
| 596 | `        counts = sorted({c for s in ss for c in S[s]['B8']['counts']})` | `counts`: the mesh-1 thread counts of all sessions, sorted. |
| 597 | `        if counts:` | The next five lines run only when there is a count. |
| 598 | `            qat = lambda k, c: [i['q'] for s in ss for i in S[s]['B8']['kern'][k].get(c, [])]` | `qat`: a small function that gives the values of q of the regular intervals of kernel `k` at the mesh-1 count `c`, over all sessions. |
| 599 | `            c0, cN = counts[0], counts[-1]` | `c0` and `cN`: the lowest and the highest mesh-1 count. |
| 600 | `            m0 = S[ss[0]]['B8']['mesh0'][0] if S[ss[0]]['B8']['mesh0'] else 64` | `m0`: the mesh-0 thread count of the first session, or 64 when it is not known. |
| 601 | `            parts.append(f"Without labels: at {m0}+{c0} threads q is {rng(qat('asmread', c0), 3)} for asm read and {rng(qat('oldread', c0), 3)} for old read. "` | Adds a sentence without labels: the range of q of asm read and of old read at the lowest count, with 3 decimals. |
| 602 | `                         f"At {m0}+{cN} threads q is {rng(qat('asmread', cN), 3)} for asm read and {rng(qat('oldread', cN), 3)} for old read.")` | Continues the text: the same two ranges at the highest count. |
| 603 | `        w8 = hyp.get('H8 (B8)', {}).get('word', '')` | `w8`: the word of the analysis script for H8. It comes from the label rule. |
| 604 | `        add('H8', meaning, text, 'B8', 'not resolved', ', '.join(f"{s}: {S[s]['B8']['n']}" for s in ss),` | Adds the row of H8. Its word is `not resolved` in every case (page rule 1). The text on the processes gives the number of processes per session. |
| 605 | `            (f'{f(max(aq), 3)} (largest difference of q between neighbouring asm read and asm read 2 intervals, no unit)' if aq else '-'),` | Continues the call: the largest `aa_q` of the sessions with 3 decimals. The text describes it as the largest difference of q between neighbouring asm read and asm read 2 intervals, without a unit. |
| 606 | `            ' '.join(parts), {s: 'not resolved' for s in ss}, plan_word='labels not used' + ('' if nb else ', no bracket formed'), strict=strict_of('H8 (B8)') + ', from the label rule',` | Continues the call: the basis, the flag `not resolved` for every session, the note `labels not used` in the place of a word of the plan (with `no bracket formed` when `nb` is 0), and the output of the analysis script, marked as coming from the label rule. |
| 607 | `            other=('' if w8.endswith('not resolved') else 'The label rule gives another word. It is not used: user decision 2 of 2026-11-13.'),` | Continues the call: the other reading. When the word of the label rule does not end with `not resolved`, it says that the label rule gives another word, which is not used by user decision 2 of 2026-11-13. |
| 608 | `            short='the rule needs the pattern labels, which are not used')` | Continues the call: the short text says that the rule needs the pattern labels, which are not used. |
| 609 | `    # ---- B5 statement` | Comment: the next block makes the row of the B5 statement. |
| 610 | `    ss = have('B5')` | `ss`: the sessions with data of B5. |
| 611 | `    meaning, text = 'B5 tests whether a loop without vector adds can show the total of old read', 'statement of B5: vector adds are needed for the pattern and total of old read'` | The meaning of this row: B5 tests whether a loop without vector adds can show the total of old read. The statement of B5: vector adds are needed for the pattern and total of old read. |
| 612 | `    b5key = next((k for k in hyp if k.startswith('B5 statement')), None)` | `b5key`: the key of the entry of the analysis script for the B5 statement, or `None`. |
| 613 | `    if not ss:` | Tests whether no session has B5. |
| 614 | `        add('B5 statement', meaning, text, 'B5', 'not tested', '-', '-', f'{ID}: no B5 process in the input.', {}, short='no B5 process in the input')` | Then the row gets the word `not tested`. |
| 615 | `    else:` | In every other case the lines up to line 639 run. |
| 616 | `        flags, aa, parts = {}, [], []` | Three start values: the flags, the A/A spreads and the basis sentences. |
| 617 | `        for s in ss:` | Loop over the sessions with B5. |
| 618 | `            v = S[s]['B5']['res']['variants'].get('read_sparse')` | `v`: the result of the analysis for the variant `read_sparse`. By the handoff that loop has 4 load instructions, 9 `nop` instructions and 3 loop instructions per 128 B. These are 16 instructions per 128 B, as many as the old read loop has, and no vector add. |
| 619 | `            if not v or v['total_difference']['decision'] == 'not observed':` | Tests whether the variant is missing or the decision for its total is `not observed`. |
| 620 | `                flags[s] = 'not observed'; parts.append(f'Session {s}: read_sparse has fewer than 4 processes with a value.'); continue` | Then the flag of the session is `not observed`, a sentence says that `read_sparse` has fewer than 4 processes with a value, and the loop goes on with the next session. |
| 621 | `            d = v['total_difference']; h = d['metrics']['M_hist']` | `d`: the decision of the analysis for the difference of the totals, old read minus `read_sparse`. `h`: its values with `M_hist`. The difference is one value per process, and its A/A spread comes from `asmread2` minus `asmread` in the same processes. |
| 622 | `            aa.append(h['aa_spread'])` | Adds the A/A spread of the session to `aa`. |
| 623 | `            qs_, qo_ = [x['q'] for x in S[s]['B5']['kern'].get('read_sparse', [])], [x['q'] for x in S[s]['B5']['kern'].get('oldread', [])]` | `qs_` and `qo_`: the values of q of the regular intervals of `read_sparse` and of old read. |
| 624 | `            if d['decision'] == 'resolved' and not d['metrics_disagree']:` | Tests whether the difference is resolved and `M_hist` and `M_sum` agree. |
| 625 | `                flags[s] = 'hold'` | Then the flag is `hold`: `read_sparse` does not show the total of old read, so the statement held in this session. |
| 626 | `                parts.append(f"Session {s}: old read minus read_sparse is {fs(h['median_D'])} GB/s (median of {h['n_processes']} processes, A/A spread {f(h['aa_spread'])} GB/s), which is resolved. "` | Adds a sentence for the session: the median difference in GB/s with a sign, the number of processes, the A/A spread, and the statement that the difference is resolved. |
| 627 | `                             f"q is {rng(qs_, 3)} for read_sparse and {rng(qo_, 3)} for old read.")` | Continues the text: a sentence with the ranges of q of `read_sparse` and of old read, with 3 decimals. |
| 628 | `            else:` | In every other case the next two lines run. |
| 629 | `                flags[s] = 'not resolved'` | The flag is `not resolved`. |
| 630 | `                parts.append(f"Session {s}: old read minus read_sparse is {fs(h['median_D'])} GB/s, which is not resolved. The rule then asks whether the pattern labels are equal, and the labels are not used.")` | Adds two sentences: the median difference, which is not resolved, and the remark that the rule then asks whether the pattern labels are equal, and that the labels are not used. |
| 631 | `        if flags and all(x == 'hold' for x in flags.values()):` | Tests whether every session has the flag `hold`. |
| 632 | `            parts.append('So read_sparse does not show the total of old read, and no label is needed.')` | Then a sentence is added: `read_sparse` does not show the total of old read, and no label is needed. |
| 633 | `        w = word_of(flags)` | `w`: the word of the page, from the flags. |
| 634 | `        ws = hyp.get(b5key, {}).get('word', '') if b5key else ''` | `ws`: the word of the analysis script for the B5 statement, or an empty text. |
| 635 | `        add('B5 statement', meaning, text, 'B5', w, ', '.join(f"{s}: {S[s]['B5']['n']}" for s in ss), (f'{rng(aa)} GB/s' if aa else '-'), ' '.join(parts), flags,` | Adds the row. The text on the processes gives the number of processes per session. The next text gives the range of the A/A spreads in GB/s. |
| 636 | `            strict=(strict_of(b5key) if b5key else 'no entry') + ', from the label rule and the totals',` | Continues the call: the output of the analysis script, marked as coming from the label rule and the totals. |
| 637 | `            other=('' if norm(ws) == w else 'The label rule gives another word. It is not used: user decision 2 of 2026-11-13.'),` | Continues the call: the other reading. When the word of the analysis differs from the word of the page, it says that the label rule gives another word, which is not used. |
| 638 | `            short=('the total of read_sparse differs from old read by a resolved amount in ' + join_and(flags) if flags and all(x == 'hold' for x in flags.values())` | Continues the call: the short text. When every session has `hold`, it says that the total of `read_sparse` differs from old read by a resolved amount, and names the sessions. |
| 639 | `                   else 'result per session: ' + flag_txt(flags)))` | Continues the short text: in every other case it gives the flag of each session. |

### `hypotheses`: H9a, H9b (page rule 3) and H10 (page rule 4) (lines 640 to 697)

| Line | Source | Explanation |
|---:|---|---|
| 640 | `    # ---- H9a (page rule 1)` | Comment: the next block makes the row of H9a by page rule 1. |
| 641 | `    ss = have('B9')` | `ss`: the sessions with data of B9. |
| 642 | `    meaning, text = 'the second buffer per thread changed the pattern of old read on 2026-10-30', 'old read is uniform with two buffers per thread and split with one'` | The meaning of H9a: the second buffer per thread changed the pattern of old read on 2026-10-30. Its bounded prediction: old read is uniform with two buffers per thread and split with one. |
| 643 | `    if not ss:` | Tests whether no session has B9. |
| 644 | `        add('H9a', meaning, text, 'B9', 'not tested', '-', '-', f'{ID}: no B9 process in the input.', {}, short='no B9 process in the input')` | Then the row gets the word `not tested`. |
| 645 | `    else:` | In every other case the lines up to line 663 run. |
| 646 | `        aa = [S[s]['B9']['res']['total']['aa_value'] for s in ss if S[s]['B9']['res']['total']['aa_value'] is not None]` | `aa`: the A/A value of the total of each session that has one. In B9 the process value is the median total of the intervals of a process. The A/A value is the largest difference between two process values of one kind, and the larger of the two kinds counts. |
| 647 | `        q1 = [x['q'] for s in ss for x in S[s]['B9']['kinds']['one_buffer']['ivs']]; q2 = [x['q'] for s in ss for x in S[s]['B9']['kinds']['two_buffers']['ivs']]` | `q1` and `q2`: the values of q of the regular intervals with one buffer and with two buffers, over all sessions. |
| 648 | `        ivs = [x for s in ss for kk in S[s]['B9']['kinds'].values() for x in kk['ivs']]` | `ivs`: the values of the regular intervals of both kinds, over all sessions. |
| 649 | `        parts = ['The prediction is worded with the labels split and uniform, which are not used.']` | `parts` starts with a sentence: the prediction is worded with the labels, which are not used. |
| 650 | `        if q1 and q2:` | The next two lines run only when both kinds have intervals. |
| 651 | `            parts.append(f"Without labels: q of old read is {rng(q1, 3)} with one buffer ({len(q1)} intervals) and {rng(q2, 3)} with two ({len(q2)} intervals). "` | Adds a sentence without labels: the range of q of old read with one buffer and with two, each with its number of intervals. |
| 652 | `                         f"The median thread rate is {rng([x['m0'] for x in ivs])} GB/s on mesh 0 and {rng([x['m1'] for x in ivs])} GB/s on mesh 1 in all {len(ivs)} intervals of both kinds.")` | Continues the text: a sentence with the range of the median thread rate on mesh 0 and on mesh 1, over all intervals of both kinds. |
| 653 | `        for s in ss:` | Loop over the sessions with B9. |
| 654 | `            t = S[s]['B9']['res']['total']` | `t`: the result of the analysis for the total. |
| 655 | `            if t['difference'] is not None:` | The next line runs only when the analysis has a difference. |
| 656 | `                parts.append(f"Session {s}: the total with one buffer minus the total with two is {fs(t['difference'])} GB/s (A/A value {f(t['aa_value'])} GB/s, {t['decision']}).")` | Adds a sentence for the session: the total with one buffer minus the total with two in GB/s, the A/A value, and the decision of the analysis. Each of the two totals is the median of the process values of its kind. |
| 657 | `        w9 = hyp.get('H9a (B9)', {}).get('word', '')` | `w9`: the word of the analysis script for H9a. It comes from the label rule. |
| 658 | `        add('H9a', meaning, text, 'B9', 'not resolved', ', '.join(f"{s}: {S[s]['B9']['kinds']['one_buffer']['n']} with one buffer, {S[s]['B9']['kinds']['two_buffers']['n']} with two" for s in ss),` | Adds the row of H9a. Its word is `not resolved` in every case (page rule 1). The text on the processes gives, per session, the number of processes with one buffer and with two. |
| 659 | `            (f'{rng(aa)} GB/s (largest difference of the total between two processes of one kind)' if aa else '-'),` | Continues the call: the range of the A/A values in GB/s, described as the largest difference of the total between two processes of one kind. |
| 660 | `            ' '.join(parts), {s: 'not resolved' for s in ss}, plan_word='labels not used', strict=strict_of('H9a (B9)') + ', from the label rule',` | Continues the call: the basis, the flag `not resolved` for every session, the note `labels not used`, and the output of the analysis script, marked as coming from the label rule. |
| 661 | `            other=('' if norm(w9) == 'not resolved' else f'The label rule gives "{w9}". It is not used: user decision 2 of 2026-11-13 says that a rule which needs a label gives "not resolved". '` | Continues the call: the other reading. When the label rule gives another word than `not resolved`, the text names that word and says that it is not used, with the reason of user decision 2. |
| 662 | `                   'The word of the label rule would need the labels, or a decision of the user to accept q for this step.'),` | Continues the text: the word of the label rule would need the labels, or a decision of the user to accept q for this step. |
| 663 | `            short='the prediction is worded with the pattern labels, which are not used')` | Continues the call: the short text says that the prediction is worded with the pattern labels, which are not used. |
| 664 | `    # ---- H9b (page rule 3)` | Comment: the next block makes the row of H9b by page rule 3. |
| 665 | `    qs = {s: S[s]['old_q'] for s in names if S[s]['old_q']}` | `qs`: per session, the list of the pairs of q and total of the old read intervals at the full thread count (lines 376 to 380). A session without such an interval is left out. |
| 666 | `    meaning, text = 'old read behaves differently between days or sessions for a reason other than the kernel', 'the pattern of old read differs between days or sessions for a reason other than the kernel'` | The meaning of H9b: old read behaves differently between days or sessions for a reason other than the kernel. Its bounded prediction says the same of the pattern of old read. |
| 667 | `    if len(qs) < 2:` | Tests whether fewer than 2 sessions have such intervals. |
| 668 | `        add('H9b', meaning, text, 'B7, B5, B8, B9', 'not tested', '-', '-',` | Then the row gets the word `not tested`. The step column names B7, B5, B8 and B9. |
| 669 | `            (f"One session ({', '.join(qs)}) has data. A comparison between sessions needs at least two." if qs else f'{ID}: no old read interval at 64+56 threads in the input.'), {},` | Continues the call: the basis. With one session it says that a comparison between sessions needs at least two. With none it starts with `Insufficient data` and says that the input holds no old read interval at 64+56 threads. |
| 670 | `            short='a comparison between sessions needs two sessions')` | Continues the call: the short text. |
| 671 | `    else:` | In every other case the lines up to line 688 run. |
| 672 | `        lo, hi = max(min(q for q, _ in v) for v in qs.values()), min(max(q for q, _ in v) for v in qs.values())` | `lo`: the highest of the lowest values of q of the sessions. `hi`: the lowest of the highest values of q of the sessions. |
| 673 | `        overlap = lo <= hi` | `overlap`: true when `lo` is at or below `hi`. Then at least one value lies inside the range of q of every session. This is the test of page rule 3. |
| 674 | `        tmin = min(t for v in qs.values() for _, t in v)` | `tmin`: the lowest total of all these intervals. |
| 675 | `        parts = [' '.join(f'Session {s}: q of old read is {f(min(q for q, _ in v), 3)} to {f(max(q for q, _ in v), 3)}, and its total is {rng([t for _, t in v])} GB/s ({len(v)} intervals).' for s, v in qs.items())]` | `parts` starts with one sentence per session: the lowest and the highest q of old read with 3 decimals, the range of its total in GB/s, and the number of intervals. |
| 676 | `        parts.append('The ranges of q overlap.' if overlap else 'The ranges of q do not overlap.')` | Adds a sentence that says whether the ranges of q overlap. |
| 677 | `        parts.append(f"No interval has a total at or below {fx(PLAN_OLD_LOW[1])} GB/s, the highest total of old read on 2026-10-30." if tmin > PLAN_OLD_LOW[1] else` | Adds a sentence on the totals. When `tmin` is above 368.25 GB/s, it says that no interval has a total at or below that value, the highest total of old read on 2026-10-30. |
| 678 | `                     f"The lowest total is {f(tmin)} GB/s. The totals of old read on 2026-10-30 were {fx(PLAN_OLD_LOW[0])} to {fx(PLAN_OLD_LOW[1])} GB/s.")` | Continues the statement: in the other case the sentence gives the lowest total and the two totals of 2026-10-30. |
| 679 | `        ts = m['timing'].get('same_step')` | `ts`: the distance between the same steps of the first two sessions (line 244), or `None`. |
| 680 | `        if ts:` | The next line runs only when it exists. |
| 681 | `            parts.append(f"Each step of {ts[1]} started {hm(ts[2])}" + ('' if hm(ts[2]) == hm(ts[3]) else f' to {hm(ts[3])}') + f" after the same step of {ts[0]}, in one continuous run.")` | Adds a sentence that says how long after the same step of the first session each step of the second session started. The words `in one continuous run` at its end are typed. They do not depend on the data. |
| 682 | `        add('H9b', meaning, text, 'B7, B5, B8, B9', 'not observed' if overlap else 'not resolved', ', '.join(f'{s}: {len(v)} intervals of old read' for s, v in qs.items()), '-',` | Adds the row of H9b. Its word is `not observed` when the ranges overlap and `not resolved` when they do not. The text on the processes gives the number of old read intervals per session. |
| 683 | `            ' '.join(parts), {s: 'described' for s in qs},` | Continues the call: the basis, and the flag `described` for every session. |
| 684 | `            strict='no entry of the analysis script. Plan, step B9: H9b can only be "observed" or "not observed" over the sessions that were run',` | Continues the call: in the place of an output of the analysis script, a typed text. It says that the analysis has no entry and that by the plan, step B9, H9b can only be `observed` or `not observed` over the sessions that were run. |
| 685 | `            other=('H9b is worded with the pattern, and the pattern labels are not used. Under user decision 2 of 2026-11-13 the word would then be "not resolved". '` | Continues the call: the other reading, a typed text. This line: H9b is worded with the pattern, the labels are not used, and under user decision 2 the word would then be `not resolved`. |
| 686 | `                   'The test of this page (overlapping ranges of q, page rule 3) is not a rule of the plan or of the handoff, and the user has not approved it.'),` | Continues the text: the test of this page, overlapping ranges of q, is not a rule of the plan or of the handoff, and the user has not approved it. |
| 687 | `            open_='"not observed" (page rule 3) or "not resolved" (user decision 2)' if overlap else '',` | Continues the call: the open question, set only when the ranges overlap: `not observed` by page rule 3, or `not resolved` by user decision 2. |
| 688 | `            short='the ranges of q of old read overlap between the sessions' if overlap else 'the ranges of q of old read do not overlap, and no label names the change')` | Continues the call: the short text says whether the ranges of q of old read overlap between the sessions. |
| 689 | `    # ---- H10 (page rule 4)` | Comment: the next block makes the row of H10 by page rule 4. |
| 690 | `    ss = have('C3')` | `ss`: the sessions with data of C3. |
| 691 | `    add('H10', 'the memory system fetches lines that the loop does not consume', 'in the uniform state the memory system fetches lines that the loop does not consume', 'C3 (description), D1 (not run)', 'not tested',` | Adds the row of H10 with the word `not tested` in every case (page rule 4). The meaning: the memory system fetches lines that the loop does not consume. The step column names C3 as a description and D1 as not run. D1 is the step of Part D with the mesh counters, which need root rights. |
| 692 | `        ', '.join(f"{s}: {S[s]['C3']['n']} with counters" for s in ss) or '-', '-',` | Continues the call: the text on the processes gives the number of processes with counters per session, or `-`. |
| 693 | `        'No step of Parts B and C tests a bounded prediction of H10. The core counters of C3 are a description. Step D1 (mesh counters, root) was not run.', {},` | Continues the call: the basis, a typed text. It says that no step of Parts B and C tests a bounded prediction of H10, that the core counters of C3 are a description, and that step D1 was not run. |
| 694 | `        strict='no entry of the analysis script', short='the counters that need root were not run')` | Continues the call: the analysis script has no entry for H10. The short text says that the counters that need root were not run. |
| 695 | `    return rows` | Returns the rows. |

### `compute`: read the result folders and build the model (lines 698 to 741)

| Line | Source | Explanation |
|---:|---|---|
| 698 | `def compute(session_paths, offsets=OFFSETS):` | Starts the function `compute`. It reads the result folders of all sessions and builds the model. `session_paths` gives the list of folders for each session name. `offsets` is the path of the offsets file. |
| 699 | `    """session_paths: {name: [folders]} -> the model (computed values only)."""` | Description of `compute`: the input is a dictionary from session name to folders, and the output is the model, which holds computed values only. |
| 700 | `    names = list(session_paths)` | `names`: the session names in the order of the command line. |
| 701 | `    procs, folders, env_all = {}, {}, {}` | Three empty dictionaries, each with one entry per session: the processes, the folders of Q2, and the `env.txt` readings. |
| 702 | `    for s, paths in session_paths.items():` | Loop over the sessions with their folders. |
| 703 | `        allp = A.load_session(s, paths)` | `allp`: the processes of the session. `A.load_session` reads every file `*.csv` of each folder. A header line that starts with `-- step` begins a new process, and the rows below it belong to that process. |
| 704 | `        procs[s] = [p for p in allp if p.step in STEPS]` | Keeps the processes whose step is one of the six steps of Q2. The processes of other steps are dropped here. |
| 705 | `        used = {p.file.split('/')[0] for p in procs[s]}` | `used`: the names of the folders that hold at least one such process. |
| 706 | `        folders[s] = [x for x in paths if os.path.basename(x.rstrip('/')) in used]` | `folders` of the session: the paths of these folders. |
| 707 | `        env_all[s] = [read_env(x) for x in paths]` | `env_all` of the session: the `env.txt` reading of every folder given, also of the folders of other steps. |
| 708 | `    summary = A.analyze(procs)` | `summary`: the result of the analysis script for these processes. It holds the decisions per session and step, and under `hypotheses` one entry per hypothesis with its word over the sessions. |
| 709 | `    m = dict(sessions=names, summary=summary, S={}, folders=folders, offsets={}, offsets_path=offsets, timing=timing_model(env_all, names))` | `m`: the model. It starts with the session names, the summary, the folders, the path of the offsets file, and the times of the sessions from `timing_model`. |
| 710 | `    for s in names:` | Loop over the sessions. |
| 711 | `        res, P = summary['sessions'][s], procs[s]` | `res`: the analysis results of the session per step. `P`: its processes. |
| 712 | `        by = lambda st: [p for p in P if p.step == st]` | `by`: a small function that gives the processes of one step. |
| 713 | `        d = dict(load=load_model(P, folders[s]), env=[read_env(x) for x in folders[s]], old_q=old_q_at_full(P), steps=[st for st in STEPS if st in res],` | `d`: the model of the session. `load`: the load readings per step. `env`: the `env.txt` readings of the folders of Q2. `old_q`: the values for H9b. `steps`: the steps of Q2 that have a result. |
| 714 | `                 integ={st: res[st] for st in STEPS if st in res},` | Continues `d`. `integ`: the result of the analysis per step. Among other values it holds the number of processes, the irregular intervals and the processes left out. |
| 715 | `                 page={st: dict(rows=sum(len(p.P) for p in by(st)), na=sum(1 for p in by(st) for x in p.P if x['kB_total'] is None or x['kB_huge'] is None),` | Continues `d`. `page`: values of the page state per step, from the P rows. A P row gives for one buffer its size `kB_total` and its part on 2 MiB pages `kB_huge`, both in kB. `rows`: the number of P rows. `na`: the number of P rows in which one of the two values is `NA`. |
| 716 | `                                not_full=sum(1 for p in by(st) for x in p.P if x['kB_total'] is not None and x['kB_huge'] != x['kB_total']))` | Continues the entry. `not_full`: the number of P rows whose part on 2 MiB pages differs from the size. Such a buffer is not fully on 2 MiB pages. |
| 717 | `                       for st in STEPS if st in res},` | Continues `page`: one entry for each step of Q2 that has a result. |
| 718 | `                 skew={st: (max([iv.skew * 1e3 for p in by(st) if p.complete and p.stop == 'common' for iv in p.ordered], default=None),` | Continues `d`. `skew`: three values per step. The first: the largest end skew in ms over the intervals of the complete processes with the common stop. |
| 719 | `                            max([iv.skew * 1e3 for p in by(st) if p.complete and p.stop == 'pass' for iv in p.ordered], default=None),` | The second: the largest end skew in ms over the intervals of the complete processes with whole passes. |
| 720 | `                            sum(iv.late for p in by(st) if p.complete for iv in p.ordered)) for st in STEPS if st in res})` | The third: the number of late thread starts over the intervals of the complete processes. A late start is a T row with the flag `late`. With the common stop the runner sets the flag when a thread starts more than 100 microseconds after the common start time. |
| 721 | `        for st, fn in (('B7', b7_model), ('B10', b10_model), ('B8', b8_model), ('B5', b5_model), ('B9', b9_model), ('C3', c3_model)):` | Loop over the six steps, each with the function that builds its model. |
| 722 | `            if st in res:` | The next line runs only when the step has a result. |
| 723 | `                d[st] = fn(by(st), res[st])` | Builds the model of the step from its processes and its analysis result. |
| 724 | `        d['later_settings'] = {st: d[st]['settings'] for st in ('B8', 'B5', 'B9') if st in d}` | `later_settings`: the settings in which the processes of B8, B5 and B9 ran, per step, as their header lines show. |
| 725 | `        ls = {x for v in d['later_settings'].values() for x in v}` | `ls`: the set of these settings over the three steps. |
| 726 | `        d['used_setting'] = next(iter(ls)) if len(ls) == 1 else None          # the one setting of B8, B5 and B9, if it is one` | `used_setting`: that setting when the three steps ran in exactly one setting. If not, it is `None`. |
| 727 | `        if 'B7' in d:` | The next line runs only when the session has B7. |
| 728 | `            b7_rep(d['B7'], d['used_setting'])` | Picks the example pair of intervals for the thread chart of B7 (lines 275 to 291). |
| 729 | `        m['S'][s] = d` | Stores the model of the session. |
| 730 | `    # one y axis for the B8 panels of all sessions, so that two sessions can be compared at a glance` | Comment: the B8 panels of all sessions get one y axis. A reader can then compare two sessions. |
| 731 | `    r8 = [v for s in names if 'B8' in m['S'][s] for k in m['S'][s]['B8']['kern'].values() for iv in k.values() for x in iv for v in (x['m0'], x['m1']) if v is not None]` | `r8`: the median thread rates of mesh 0 and of mesh 1 of every B8 interval of every session. |
| 732 | `    m['b8_ymax'] = float(max(2, 2 * __import__('math').ceil(max(r8) * 1.02 / 2))) if r8 else None` | `b8_ymax`: the upper end of that axis: the largest of these rates plus 2 %, rounded up to the next even number, and at least 2 GB/s. `__import__('math')` loads the module `math` at this place. |
| 733 | `    if offsets and os.path.exists(offsets):` | The next four lines run only when an offsets file is named and exists. |
| 734 | `        for line in open(offsets):` | Loop over the lines of the offsets file. |
| 735 | `            c = line.split()` | `c`: the fields of the line, split at spaces and tabs. |
| 736 | `            if len(c) == 6 and c[0] != 'binary':` | Takes a line with 6 fields that is not the heading line. The heading line starts with `binary`. |
| 737 | `                m['offsets'][(c[0], c[1])] = int(c[5])` | Stores the sixth field as a number under the binary and the kernel of the line. It is the address of the loop start modulo 64. |
| 738 | `    m['hyp'] = hypotheses(m)` | Builds the rows of the hypothesis table. |
| 739 | `    return m` | Returns the model. |

### Chart helpers: `ticks_for`, `wrap` and `dot` (lines 742 to 775)

| Line | Source | Explanation |
|---:|---|---|
| 742 | `# ---------------------------------------------------------------- charts` | Comment: here starts the code that draws the charts. |
| 744 | `def ticks_for(lo, hi, n=6):` | Starts the function `ticks_for`. It chooses the values at which an axis from `lo` to `hi` gets a tick. `n` is the wanted number of steps. |
| 745 | `    span = (hi - lo) or 1.0` | `span`: the length of the axis, or 1.0 when the length is 0. |
| 746 | `    raw = span / n` | `raw`: the length divided by `n`. |
| 747 | `    mag = 10 ** __import__('math').floor(__import__('math').log10(raw))` | `mag`: the largest power of ten that is not above `raw`. |
| 748 | `    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)` | `step`: the first of 1, 2, 2.5, 5 and 10 times `mag` that is at least `raw`. So the distance between two ticks is a round number. |
| 749 | `    t0 = __import__('math').ceil(lo / step - 1e-9) * step` | `t0`: the first multiple of `step` at or above `lo`. The small value 1e-9 guards against a rounding error. |
| 750 | `    out = []` | `out`: the list of the ticks, empty at first. |
| 751 | `    while t0 <= hi + 1e-9:` | Loop as long as the tick is not above `hi`. |
| 752 | `        out.append(round(t0, 10)); t0 += step` | Adds the tick, rounded to 10 decimals, and goes on to the next one. |
| 753 | `    return out` | Returns the list. |
| 756 | `def wrap(text, n):` | Starts the function `wrap`. |
| 757 | `    """Break a text into lines of at most n characters, at spaces."""` | Description of `wrap`: it breaks a text into lines of at most `n` characters, at spaces. |
| 758 | `    out, cur = [], ''` | `out`: the finished lines. `cur`: the line that is filled now. |
| 759 | `    for w in text.split():` | Loop over the words of the text. |
| 760 | `        if cur and len(cur) + 1 + len(w) > n:` | Tests whether the word would make the line longer than `n` characters. |
| 761 | `            out.append(cur); cur = w` | Then the line is finished, and the word starts the next line. |
| 762 | `        else:` | In the other case the next line applies. |
| 763 | `            cur = (cur + ' ' + w).strip()` | The word is added to the line, with a space before it when the line is not empty. |
| 764 | `    return out + ([cur] if cur else [])` | Returns the finished lines and the last line when it is not empty. |
| 767 | `def dot(x, y, color, shape, title, r=4.5, op=1.0):` | Starts the function `dot`. It gives the SVG text of one marker of a chart at the position `x`, `y`. SVG is a picture format that is written as text. `r` is the radius of the marker in the units of the drawing, and `op` its opacity. |
| 768 | `    t = f'<title>{e(title)}</title>' if title else ''` | `t`: a `title` element with the escaped text, or nothing. A browser shows this text when the mouse pointer is over the marker. |
| 769 | `    if shape == 'ring':` | Tests whether the shape is `ring`. |
| 770 | `        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r - 0.75:.1f}" fill="#fff" stroke="{color}" stroke-width="1.5">{t}</circle>'` | Returns a ring: a white circle with an outline of width 1.5 in the color. |
| 771 | `    if shape == 'diamond':` | Tests whether the shape is `diamond`. |
| 772 | `        return f'<path d="M{x:.1f},{y - r - 1:.1f} l{r + 1},{r + 1} l-{r + 1},{r + 1} l-{r + 1},-{r + 1} Z" fill="{color}" fill-opacity="{op}" stroke="#fff" stroke-width="1">{t}</path>'` | Returns a diamond: a filled square that stands on one corner, drawn as a path with a white outline. |
| 773 | `    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" fill-opacity="{op}" stroke="#fff" stroke-width="1">{t}</circle>'` | For every other shape: returns a filled circle with a white outline. |

### `rowchart` and `spread_labels`: a chart with one row of markers per name (lines 776 to 831)

| Line | Source | Explanation |
|---:|---|---|
| 776 | `def rowchart(rows, xmin, xmax, xlabel, aria, L=250, R=250, W=880, rh=24, note=None, vlines=(), ticks=None):` | Starts the function `rowchart`. It draws a chart with one horizontal row per name and one x axis from `xmin` to `xmax`. `L` and `R` are the widths of the left and the right margin, `W` is the width of the drawing and `rh` the height of one row, all in units of the drawing. `aria` is the label for screen readers. |
| 777 | `    """rows: dict(head=text) or dict(name, pts=[dict(v, c, shape, t, dy, lab, side)], right, bar=(a, b), seg=(a, b)).` | Description of `rowchart`: a row is a heading (`head`), or it has a name, a list of points `pts`, a text `right` for the right margin, a `bar` and a `seg`. A point has a value `v`, a color `c`, a shape, a tooltip `t`, a vertical shift `dy`, a label `lab` and the side of the label. |
| 778 | `    A bar is a grey band (a control). A seg joins two points of one row (a dumbbell)."""` | Continues the description: a bar is a grey band that shows a control. A seg is a line that joins two points of one row. |
| 779 | `    nl = wrap(note, int((W - 16) / 7.3)) if note else []` | `nl`: the note above the chart, broken into lines by `wrap`. A line gets at most `(W - 16) / 7.3` characters. That is 118 characters for a width of 880. |
| 780 | `    top = 30 + 16 * len(nl) if nl else 26` | `top`: the height of the area above the first row: 26 without a note, or 30 plus 16 for each line of the note. |
| 781 | `    H = top + len(rows) * rh + 46` | `H`: the height of the drawing: the top area, the rows, and 46 for the axis below them. |
| 782 | `    PW = W - L - R` | `PW`: the width of the plot area. |
| 783 | `    X = lambda v: L + (min(max(v, xmin), xmax) - xmin) / ((xmax - xmin) or 1) * PW` | `X`: a small function that turns a value into a horizontal position. `xmin` lies at the left edge of the plot area and `xmax` at its right edge. A value outside the axis is drawn at the nearest end of the axis. |
| 784 | `    o = PA.svg_open(W, H, aria)` | `o`: the list of the text pieces of the drawing. `PA.svg_open` gives the first piece: the opening `svg` tag with the size `W` by `H` of the drawing, a width of 100 % of the page up to `W` px, and the label for screen readers. |
| 785 | `    for i, ln in enumerate(nl):` | Loop over the lines of the note. |
| 786 | `        o.append(f'<text x="8" y="{16 + 16 * i}" class="lab" font-weight="600">{e(ln)}</text>')` | Adds the line of the note as bold text at the top left. |
| 787 | `    for t in (ticks or ticks_for(xmin, xmax)):` | Loop over the tick values of the x axis: the list `ticks` when the caller gave one, or the values of `ticks_for`. |
| 788 | `        o.append(f'<line x1="{X(t):.1f}" y1="{top - 4}" x2="{X(t):.1f}" y2="{H - 46}" stroke="{GRID}"/>')` | Adds a vertical grid line at the tick. |
| 789 | `        o.append(f'<text x="{X(t):.1f}" y="{H - 30}" text-anchor="middle" class="ax">{t:g}</text>')` | Adds the number of the tick below the plot area. The format `g` prints a number in its shortest form. |
| 790 | `    for v, lab in vlines:` | Loop over the extra vertical lines that the caller asked for, each with a value and a label. |
| 791 | `        o.append(f'<line x1="{X(v):.1f}" y1="{top - 4}" x2="{X(v):.1f}" y2="{H - 46}" stroke="{MUTED}" stroke-dasharray="4 3"/>')` | Adds a dashed vertical line at the value. |
| 792 | `        if lab:` | The next line runs only when the line has a label. |
| 793 | `            o.append(f'<text x="{X(v):.1f}" y="{top - 8}" text-anchor="middle" class="ax">{e(lab)}</text>')` | Adds the label above the dashed line. |
| 794 | `    o.append(f'<text x="{L + PW / 2:.1f}" y="{H - 8}" text-anchor="middle" class="ax">{e(xlabel)}</text>')` | Adds the title of the x axis, centered below the plot area. |
| 795 | `    for i, r in enumerate(rows):` | Loop over the rows. `i` counts them from 0. |
| 796 | `        y = top + i * rh + rh / 2` | `y`: the vertical middle of the row. |
| 797 | `        if 'head' in r:` | Tests whether the row is a heading. |
| 798 | `            o.append(f'<text x="8" y="{y + 4:.1f}" class="lab" font-weight="600" style="paint-order:stroke;stroke:#fff;stroke-width:4px">{e(r["head"])}</text>')` | Adds the heading as bold text at the left edge, with a white outline behind the letters. |
| 799 | `            continue` | Goes on with the next row. |
| 800 | `        o.append(f'<text x="{L - 10}" y="{y + 4:.1f}" text-anchor="end" class="lab">{e(r["name"])}</text>')` | Adds the name of the row. The text ends 10 units left of the plot area. |
| 801 | `        o.append(f'<line x1="{L}" y1="{y + rh / 2:.1f}" x2="{L + PW}" y2="{y + rh / 2:.1f}" stroke="{GRID}"/>')` | Adds a horizontal grid line at the lower edge of the row. |
| 802 | `        if r.get('bar'):` | The next two lines run only when the row has a bar. |
| 803 | `            a, b = sorted(r['bar'])` | `a` and `b`: the two ends of the bar, the smaller one first. |
| 804 | `            o.append(f'<rect x="{X(a):.1f}" y="{y - rh / 2 + 3:.1f}" width="{max(X(b) - X(a), 1):.1f}" height="{rh - 6}" fill="#d9d7cf"><title>{e(r.get("bar_t", "control"))}</title></rect>')` | Adds the bar: a grey rectangle from `a` to `b`, at least 1 unit wide. Its tooltip is the text `bar_t` of the row, or the word `control`. |
| 805 | `        if r.get('seg'):` | The next two lines run only when the row has a seg. |
| 806 | `            a, b = r['seg']` | `a` and `b`: the two ends of the seg. |
| 807 | `            o.append(f'<line x1="{X(a):.1f}" y1="{y:.1f}" x2="{X(b):.1f}" y2="{y:.1f}" stroke="{MUTED}" stroke-width="2"/>')` | Adds a horizontal line of width 2 between the two ends. |
| 808 | `        for p in r.get('pts', []):` | Loop over the points of the row. |
| 809 | `            px, py = X(p['v']), y + p.get('dy', 0)` | `px` and `py`: the position of the marker. `dy` shifts it up or down from the middle of the row. |
| 810 | `            o.append(dot(px, py, p.get('c', C0), p.get('shape', 'circle'), p.get('t', ''), p.get('r', 4.5), p.get('op', 0.8)))` | Adds the marker with `dot`. Without other values the marker is a circle in the color `C0` with radius 4.5 and opacity 0.8. |
| 811 | `            if p.get('lab'):` | The next lines up to line 816 run only when the point has a label. |
| 812 | `                side = p.get('side', 'r')` | `side`: the side of the label, `r` for right when the point names none. |
| 813 | `                if side in ('a', 'b'):` | Tests whether the side is `a` (above) or `b` (below). |
| 814 | `                    o.append(f'<text x="{px:.1f}" y="{py + (-9 if side == "a" else 17):.1f}" text-anchor="middle" class="val">{e(p["lab"])}</text>')` | Adds the label centered above the marker (9 units up) or below it (17 units down). |
| 815 | `                    continue` | Goes on with the next point. |
| 816 | `                o.append(f'<text x="{px + (9 if side == "r" else -9):.1f}" y="{py + 4:.1f}" text-anchor="{"start" if side == "r" else "end"}" class="val">{e(p["lab"])}</text>')` | For the sides right and left: adds the label 9 units right of the marker, or 9 units left of it. |
| 817 | `        if r.get('right'):` | The next line runs only when the row has a text for the right margin. |
| 818 | `            o.append(f'<text x="{L + PW + 10}" y="{y + 4:.1f}" class="val">{e(r["right"])}</text>')` | Adds that text 10 units right of the plot area. |
| 819 | `    o.append('</svg>')` | Adds the closing `svg` tag. |
| 820 | `    return '\n'.join(o)` | Returns the drawing as one text, with a line break between the pieces. |
| 823 | `def spread_labels(items, gap=12):` | Starts the function `spread_labels`. |
| 824 | `    """items: [(y, payload)] -> [(y_label, payload)] with at least gap px between labels."""` | Description of `spread_labels`: it takes pairs of a vertical position and a payload. It returns them with at least `gap` units between the positions of two labels. |
| 825 | `    out, last = [], None` | `out`: the result. `last`: the position of the label before, `None` at first. |
| 826 | `    for y, p in sorted(items, key=lambda t: t[0]):` | Loop over the pairs, sorted by position from the top down. |
| 827 | `        y = y if last is None else max(y, last + gap)` | The first label keeps its position. Every later label is moved down when it lies less than `gap` below the label before it. |
| 828 | `        out.append((y, p)); last = y` | Adds the pair with its new position and remembers that position. |
| 829 | `    return out` | Returns the list. |

### `linechart`: lines through medians, with a dot per interval (lines 832 to 871)

| Line | Source | Explanation |
|---:|---|---|
| 832 | `def linechart(series, xs, ymin, ymax, xlabel, ylabel, aria, W=300, H=260, R=74, title=None, label_pts=()):` | Starts the function `linechart`. It draws a chart with x values `xs`, a y axis from `ymin` to `ymax` and one line per series. `W` and `H` are the width and the height of the drawing, and `R` is the width of the right margin. |
| 833 | `    """series: dict(name, c, med=[(x, y)], pts=[(x, y, title)]). Lines join the medians. Dots are the single intervals.` | Description of `linechart`: a series has a name, a color `c`, the medians `med` as pairs of x and y, and the points `pts` as x, y and tooltip. Lines join the medians. Dots are the single intervals. |
| 834 | `    label_pts: names of series whose median values are printed at the points ('above' or 'below')."""` | Continues the description: `label_pts` names the series whose median values are printed at the points, above or below the point. |
| 835 | `    L, top, bot = 40, 30, 40` | `L`, `top` and `bot`: the left margin 40, the top margin 30 and the bottom margin 40. |
| 836 | `    PW, PH = W - L - R, H - top - bot` | `PW` and `PH`: the width and the height of the plot area. |
| 837 | `    X = lambda v: L + (v - xs[0]) / ((xs[-1] - xs[0]) or 1) * PW` | `X`: a small function that turns an x value into a horizontal position. The first value of `xs` lies at the left edge of the plot area and the last one at its right edge. |
| 838 | `    Y = lambda v: top + PH - (min(max(v, ymin), ymax) - ymin) / ((ymax - ymin) or 1) * PH` | `Y`: a small function that turns a y value into a vertical position. A larger value lies higher. A value outside the axis is drawn at the nearest end of the axis. |
| 839 | `    o = PA.svg_open(W, H, aria)` | `o`: the list of the text pieces of the drawing, with the opening `svg` tag. |
| 840 | `    if title:` | The next line runs only when the chart has a title. |
| 841 | `        o.append(f'<text x="{L}" y="14" class="lab" font-weight="600">{e(title)}</text>')` | Adds the title as bold text at the top left. |
| 842 | `    for t in ticks_for(ymin, ymax, 5):` | Loop over the tick values of the y axis, about 5 steps. |
| 843 | `        o.append(f'<line x1="{L}" y1="{Y(t):.1f}" x2="{L + PW}" y2="{Y(t):.1f}" stroke="{GRID}"/>')` | Adds a horizontal grid line at the tick. |
| 844 | `        o.append(f'<text x="{L - 6}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{t:g}</text>')` | Adds the number of the tick at the left of the plot area. |
| 845 | `    for x in xs:` | Loop over the x values. |
| 846 | `        o.append(f'<text x="{X(x):.1f}" y="{H - bot + 14}" text-anchor="middle" class="ax">{x:g}</text>')` | Adds the x value as a number below the plot area. |
| 847 | `    o.append(f'<text x="{L + PW / 2:.1f}" y="{H - 8}" text-anchor="middle" class="ax">{e(xlabel)}</text>')` | Adds the title of the x axis, centered at the bottom. |
| 848 | `    o.append(f'<text x="{L - 34}" y="{top - 8}" class="ax">{e(ylabel)}</text>')` | Adds the title of the y axis at the top left. |
| 849 | `    ends = []` | `ends`: the labels for the line ends, empty at first. |
| 850 | `    for s in series:` | Loop over the series. |
| 851 | `        md = [(x, y) for x, y in s['med'] if y is not None]` | `md`: the medians of the series that have a value. |
| 852 | `        if len(md) > 1:` | The next line runs only with more than one median. |
| 853 | `            o.append(f'<polyline fill="none" stroke="{s["c"]}" stroke-width="2" points="' + ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in md) + '"/>')` | Adds a line of width 2 in the color of the series through the medians. |
| 854 | `        for x, y, t in s.get('pts', []):` | Loop over the single points of the series. |
| 855 | `            o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="2.6" fill="{s["c"]}" fill-opacity="0.55" stroke="#fff" stroke-width="0.6"><title>{e(t)}</title></circle>')` | Adds a small dot of radius 2.6 and opacity 0.55 for the point, with its tooltip. |
| 856 | `        if md:` | The next line runs only when the series has a median. |
| 857 | `            ends.append((Y(md[-1][1]), (s, md[-1][1])))` | Adds an entry to `ends`: the vertical position of the last median, the series and the value of that median. |
| 858 | `    # Values at the points of the series named in label_pts. At each x the higher series is labelled above its` | Comment: the next lines print the values at the points of the series named in `label_pts`. At each x value the higher series gets its label above its point and the lower one below. |
| 859 | `    # point and the lower one below. The last x is left out: its value stands in the label at the line end.` | Comment: the last x value is left out. Its value stands in the label at the line end. |
| 860 | `    lab = [s for s in series if s['name'] in label_pts]` | `lab`: the series whose names are in `label_pts`. |
| 861 | `    for i, x in enumerate(xs[:-1]):` | Loop over the x values except the last one. |
| 862 | `        here = sorted(((dict(s['med']).get(x), s) for s in lab if dict(s['med']).get(x) is not None), key=lambda t: t[0])` | `here`: the medians of these series at this x value, each with its series, sorted from the lowest value up. A series without a median at this x value is left out. |
| 863 | `        for j, (y, s) in enumerate(here):` | Loop over them. `j` counts from 0. |
| 864 | `            up = j == len(here) - 1 and len(here) > 1 or (len(here) == 1)` | `up`: true for the highest of several series, and for a series that is alone at this x value. |
| 865 | `            o.append(f'<text x="{X(x) + (3 if i == 0 else 0):.1f}" y="{Y(y) + (-7 if up else 15):.1f}" text-anchor="{"start" if i == 0 else "middle"}" class="val" style="font-size:10px">{f(y, s.get("nd", 2))}</text>')` | Adds the value as text of size 10 px: 7 units above the point when `up` is true, and 15 units below it when not. At the first x value the text starts 3 units right of the point. At the other x values it is centered. The series gives the number of decimals in `nd`, 2 when it gives none. |
| 866 | `    for y, (s, v) in spread_labels(ends, 13):` | Loop over the entries of `ends`, moved apart by `spread_labels` to at least 13 units. |
| 867 | `        o.append(f'<text x="{L + PW + 7}" y="{min(max(y + 4, top + 4), H - bot + 4):.1f}" class="val" style="fill:{s["c"]}">{e(s["name"])} {f(v, s.get("nd", 2))}</text>')` | Adds the label of the line end 7 units right of the plot area, in the color of the series: the name of the series and its last median. The position is kept inside the height of the plot area. |
| 868 | `    o.append('</svg>')` | Adds the closing `svg` tag. |
| 869 | `    return '\n'.join(o)` | Returns the drawing as one text. |

### `cpu_scatter`, `legend`, `table`, `NW` and `missing` (lines 872 to 924)

| Line | Source | Explanation |
|---:|---|---|
| 872 | `def cpu_scatter(rep, aria):` | Starts the function `cpu_scatter`. It draws the thread rate of each thread against its CPU number for the example pair of B7: one old read interval and one new read interval (lines 275 to 291). |
| 873 | `    W, H, L, R, top, bot = 880, 350, 52, 20, 82, 44` | The sizes of the drawing: width 880, height 350, left margin 52, right margin 20, top margin 82 and bottom margin 44. |
| 874 | `    PW, PH = W - L - R, H - top - bot` | `PW` and `PH`: the width and the height of the plot area. |
| 875 | `    cmax = max(c for c, _ in rep['old'] + rep['new'])` | `cmax`: the highest CPU number of both intervals. |
| 876 | `    ymax = max(v for _, v in rep['old'] + rep['new']) * 1.08` | `ymax`: the highest thread rate of both intervals plus 8 %. |
| 877 | `    X = lambda c: L + c / cmax * PW` | `X`: a small function that turns a CPU number into a horizontal position. CPU 0 lies at the left edge of the plot area and CPU `cmax` at its right edge. |
| 878 | `    Y = lambda v: top + PH - v / ymax * PH` | `Y`: a small function that turns a thread rate into a vertical position. The y axis starts at 0. |
| 879 | `    o = PA.svg_open(W, H, aria)` | `o`: the list of the text pieces of the drawing, with the opening `svg` tag. |
| 880 | `    for t in ticks_for(0, ymax, 6):` | Loop over the tick values of the y axis, from 0 to `ymax`. |
| 881 | `        o.append(f'<line x1="{L}" y1="{Y(t):.1f}" x2="{L + PW}" y2="{Y(t):.1f}" stroke="{GRID}"/><text x="{L - 6}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{t:g}</text>')` | Adds a horizontal grid line at the tick and its number at the left. |
| 882 | `    for c in range(0, cmax + 1, 8):` | Loop over every eighth CPU number, from 0 up. |
| 883 | `        o.append(f'<text x="{X(c):.1f}" y="{H - bot + 14}" text-anchor="middle" class="ax">{c}</text>')` | Adds the CPU number below the plot area. |
| 884 | `    has1 = any(c >= 64 for c, _ in rep['old'])` | `has1`: true when a thread of the old read interval ran on a CPU from 64 up, so on mesh 1. |
| 885 | `    if has1:` | The next two lines run only in that case. |
| 886 | `        xb = (X(63) + X(64)) / 2` | `xb`: the horizontal position in the middle between CPU 63 and CPU 64. |
| 887 | `        o.append(f'<line x1="{xb:.1f}" y1="{top - 6}" x2="{xb:.1f}" y2="{H - bot}" stroke="{MUTED}" stroke-dasharray="4 3"/>')` | Adds a dashed vertical line there. It marks the border between mesh 0 and mesh 1. |
| 888 | `    o.append(f'<text x="{L + PW / 2:.1f}" y="{H - 8}" text-anchor="middle" class="ax">CPU number of the thread</text>')` | Adds the title of the x axis: the CPU number of the thread. |
| 889 | `    o.append(f'<text x="8" y="{top - 12}" class="ax">thread rate (GB/s)</text>')` | Adds the title of the y axis: the thread rate in GB/s. |
| 890 | `    for pts, col, shape in ((rep['old'], C0, 'circle'), (rep['new'], C1, 'diamond')):` | Loop over the two intervals: old read as circles in the color `C0`, new read as diamonds in the color `C1`. |
| 891 | `        for c, v in pts:` | Loop over the threads of the interval. |
| 892 | `            o.append(dot(X(c), Y(v), col, shape, f'CPU {c}: {fx(v)} GB/s', 3.2, 0.8))` | Adds a marker of radius 3.2 and opacity 0.8 for the thread. Its tooltip gives the CPU number and the thread rate. |
| 893 | `    so, sn = rep['old_s'], rep['new_s']` | `so` and `sn`: the `ivstat` values of the old read interval and of the new read interval. |
| 894 | `    xa, xc = X(4), L + PW` | `xa` and `xc`: the horizontal positions of the two text blocks above the plot: at CPU 4, and at the right edge of the plot area. |
| 895 | `    o.append(f'<text x="{xa:.1f}" y="16" class="lab" font-weight="600">mesh 0 (CPUs 0 to 63)</text>')` | Adds a bold heading for mesh 0 at the top left. It names the CPUs 0 to 63. |
| 896 | `    o.append(f'<text x="{xa:.1f}" y="32" class="val" style="fill:{C0}">old read, median thread {f(so["m0"])} GB/s</text>')` | Adds below it, in the color `C0`: the median thread rate of old read on mesh 0 in GB/s. |
| 897 | `    o.append(f'<text x="{xa:.1f}" y="47" class="val" style="fill:{C1}">new read, median thread {f(sn["m0"])} GB/s</text>')` | Adds below it, in the color `C1`: the median thread rate of new read on mesh 0 in GB/s. |
| 898 | `    if has1:` | The next three lines run only when threads ran on mesh 1. |
| 899 | `        o.append(f'<text x="{xc:.1f}" y="16" text-anchor="end" class="lab" font-weight="600">mesh 1 (CPUs 64 to {cmax})</text>')` | Adds a bold heading for mesh 1 at the top right. It names the CPUs 64 to `cmax`. |
| 900 | `        o.append(f'<text x="{xc:.1f}" y="32" text-anchor="end" class="val" style="fill:{C0}">old read, median thread {f(so["m1"])} GB/s</text>')` | Adds below it: the median thread rate of old read on mesh 1. |
| 901 | `        o.append(f'<text x="{xc:.1f}" y="47" text-anchor="end" class="val" style="fill:{C1}">new read, median thread {f(sn["m1"])} GB/s</text>')` | Adds below it: the median thread rate of new read on mesh 1. |
| 902 | `    o.append('</svg>')` | Adds the closing `svg` tag. |
| 903 | `    return '\n'.join(o)` | Returns the drawing as one text. |
| 906 | `def legend(items):` | Starts the function `legend`. `items` is a list of entries, each with a color, a text and extra style text. |
| 907 | `    return '<p>' + ''.join(f'<span class="lg"><i style="background:{c};{st}"></i>{e(t)}</span>' for c, t, st in items) + '</p>'` | Returns one paragraph. For each entry it holds a small shape with the color as background and with the extra style, and then the escaped text. The page style draws the shape as a round dot unless the extra style changes it. |
| 910 | `def table(head, rows, cls=''):` | Starts the function `table`. It gives the HTML text of a table. `head` holds the column headings, `rows` the rows, and `cls` an optional class name for the style. |
| 911 | `    o = [f'<div class="tw"><table{" class=" + chr(34) + cls + chr(34) if cls else ""}><tr>' + ''.join(f'<th>{h}</th>' for h in head) + '</tr>']` | The first piece: a `div` that can scroll sideways, the opening `table` tag with the class when one is given, and the heading row. `chr(34)` is the double quote character. |
| 912 | `    o += ['<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows]` | Adds one table row per entry of `rows`, with one cell per value. The values are put in as they are, so the caller must escape text. |
| 913 | `    o.append('</table></div>')` | Adds the closing tags of the table and of the `div`. |
| 914 | `    return '\n'.join(o)` | Returns the table as one text. |
| 917 | `def NW(t):` | Starts the function `NW`. |
| 918 | `    return f'<span style="white-space:nowrap">{t}</span>'` | Returns the text inside a `span` that the browser does not break into two lines. |
| 921 | `def missing(what):` | Starts the function `missing`. |
| 922 | `    return f'<p class="miss"><b>{ID}.</b> {what}</p>'` | Returns a paragraph of the class `miss`: the bold words `Insufficient data.` and then the text `what`. The page style gives this class a light background and a colored bar at the left. |

### References: the class `Refs`, `make_refs` and `tidy_refs` (lines 925 to 987)

| Line | Source | Explanation |
|---:|---|---|
| 925 | `# ---------------------------------------------------------------- references` | Comment: here starts the code for the references of the generated page. |
| 927 | `class Refs:` | Starts the class `Refs`. It keeps the reference texts of the generated page and gives each one its number. |
| 928 | `    """References are defined first and get their number at the first citation. Only cited ones are listed."""` | Description of `Refs`: references are defined first. A reference gets its number at its first citation, and only cited references are listed. |
| 930 | `    def __init__(self):` | Starts the method that sets up a new object. |
| 931 | `        self.text, self.items, self.idx = {}, [], {}` | Three empty stores. `text`: the reference text of each key. `items`: the cited texts in the order of their numbers. `idx`: the number of each cited key. |
| 933 | `    def add(self, key, text):` | Starts the method `add`. It defines a reference. |
| 934 | `        self.text.setdefault(key, text)` | Stores the text under the key, unless the key already has a text. |
| 935 | `        return self` | Returns the object itself. |
| 937 | `    def __call__(self, *keys):` | Starts the method that runs when the object is called like a function, as in `R('plan')`. It cites one or more references. |
| 938 | `        out = ''` | `out`: the text of the citation, empty at first. |
| 939 | `        for k in keys:` | Loop over the keys given. |
| 940 | `            if k not in self.text:` | Tests whether the key was never defined. |
| 941 | `                continue` | Such a key is skipped without a message. |
| 942 | `            if k not in self.idx:` | Tests whether the key is cited for the first time. |
| 943 | `                self.items.append(self.text[k]); self.idx[k] = len(self.items)` | Then its text is added to `items`, and the key gets the next number, counted from 1. |
| 944 | `            out += f'[Ref{self.idx[k]}]'` | Adds the index of the key to the citation: the word `Ref` and the number, in square brackets. |
| 945 | `        return out` | Returns the citation. |
| 948 | `def make_refs(m):` | Starts the function `make_refs`. It defines all references of the generated page. A reference appears in the list of that page only when a later line cites it. |
| 949 | `    R = Refs()` | `R`: a new object of the class `Refs`. |
| 950 | `    N = os.path.join(CRB, 'new-test-kernel')` | `N`: the folder `new-test-kernel` below `CRB`. On the agent server the plan, the handoff and the decisions lay there. |
| 951 | `    two = len(m['sessions']) > 1` | `two`: true when the page has more than one session. |
| 952 | `    R.add('plan', f'<code>{N}/plan.md</code>: the two questions, the hypotheses H1 to H11, the rules 1 to 11 for the deciding measurements, and the tables of the steps B7, B8, B5, B9, B10, C3 and D1.')` | Defines the reference `plan`: the file `plan.md` with the two questions, the hypotheses H1 to H11, the rules 1 to 11, and the tables of the steps. |
| 953 | `    R.add('handoff', f'<code>{N}/handoff.md</code>: sections B.3 (output rows), B.4 (stop methods, irregular interval), B.6 (page state), B.8 (counters), B.9 (sequences, "Settings after B7") and B.10 (numeric decision procedure, the two metrics, the pattern rule).')` | Defines `handoff`: the file `handoff.md` with the sections that the page uses: B.3 (output rows), B.4 (stop methods, irregular interval), B.6 (page state), B.8 (counters), B.9 (sequences) and B.10 (the decision procedure). |
| 954 | `    R.add('analyze', f'<code>{BWX_DIR}/analyze_bwx.py</code> and <code>{N}/decide.py</code>: the parser and the decision rules that this page uses.')` | Defines `analyze`: the files `analyze_bwx.py` and `decide.py`, the parser and the decision rules that the page uses. |
| 955 | `    R.add('devs', f'<code>{BWX_DIR}/DEVIATIONS-scripts.md</code>: the choices of the run script and of the analysis (S1 to S20, A1 to A33). A19 says that the mapping of a step result to a word is the reading of the authors of the analysis.')` | Defines `devs`: the file `DEVIATIONS-scripts.md` with the choices of the run script and of the analysis. The text names choice A19: the mapping of a step result to a word is the reading of the authors of the analysis. |
| 956 | `    R.add('devb', f'<code>{BWX_DIR}/DEVIATIONS-bwx.md</code>: the deviations of <code>bwx</code> from the specification, and its known limits (main thread without a CPU of its own, loop offset of <code>read_sparse</code>).')` | Defines `devb`: the file `DEVIATIONS-bwx.md` with the deviations of the runner `bwx` from its specification, and its known limits. |
| 957 | `    R.add('partA', f'<code>{CRB}/results/partA-20261113T205055Z/partA-result.html</code>: the result page of Part A (screening). It shows that q did not fall into two groups.')` | Defines `partA`: the result page of Part A in the folder `partA-20261113T205055Z`. The typed text says that this page shows that q did not fall into two groups. |
| 958 | `    R.add('offsets', f'<code>{m["offsets_path"]}</code>: the start address of every loop of the four <code>bwx</code> binaries, and <code>build.txt</code> in the same folder (compiler options).')` | Defines `offsets`: the offsets file that was given to the script, and the file `build.txt` in the same folder with the compiler options. |
| 959 | `    R.add('short', f'<code>{CRB}/results/SHORT-20261113T214338Z/</code>: the short run of every sequence before session 1.')` | Defines `short`: the result folder `SHORT-20261113T214338Z` of the short run of every sequence before session 1. |
| 960 | `    R.add('antxt', (f'<code>{CRB}/results/partBC-20261114/analysis/</code>: the text tables, <code>hypotheses.txt</code> and <code>summary.json</code> that <code>analyze_bwx.py</code> wrote for both sessions (all steps of Parts B and C).' if two else` | Defines `antxt`: the folder with the text tables, `hypotheses.txt` and `summary.json` that `analyze_bwx.py` wrote. With more than one session the text names the folder `partBC-20261114/analysis` and both sessions. |
| 961 | `                    f'<code>{CRB}/results/partB-s1-analysis/</code>: the text tables, <code>hypotheses.txt</code> and <code>summary.json</code> that <code>analyze_bwx.py</code> wrote for session 1 (all steps of Parts B and C).'))` | Continues the call: with one session the text names the folder `partB-s1-analysis` and session 1. Both folder names are typed. They do not depend on the folders of the command line. |
| 962 | `    R.add('decisions', f'<code>{N}/decisions.md</code>: the decisions of the user during the execution (2026-11-13), and the open decision on the level limits at 8 MiB.')` | Defines `decisions`: the file `decisions.md` with the decisions of the user of 2026-11-13, and the open decision on the level limits at 8 MiB. |
| 963 | `    R.add('session2', f'<code>{N}/session2.sh</code>: the run script of session 2. Its line 2 says that it repeats the visits of session 1 with the same settings, and its line 6 sets the common stop, the common start and 6 s.')` | Defines `session2`: the run script `session2.sh` of session 2. The typed text says what two lines of that script hold: it repeats the visits of session 1 with the same settings, and it sets the common stop, the common start and 6 s. |
| 964 | `    R.add('q1page', f'<code>{CRB}/results/partBC-20261114/partB-q1-result.html</code>: the result page of question Q1 (the steps with one thread).')` | Defines `q1page`: the result page of question Q1, the steps with one thread. |
| 965 | `    R.add('gen', f'<code>{HERE}/make_q2_html.py</code> and <code>test_q2.py</code>: the generator of this page with its page rules 1 to 4, and its test.')` | Defines `gen`: this file and `test_q2.py`, the generator of the page with its page rules 1 to 4, and its test. |
| 966 | `    for s in m['sessions']:` | Loop over the sessions. |
| 967 | `        for st in STEPS:` | Loop over the six steps of Q2. |
| 968 | `            fo = [x for x in m['folders'][s] if os.path.basename(x.rstrip('/')).split('-')[0].rstrip('ab') == st]` | `fo`: the folders of the session whose step part is this step. A letter `a` or `b` at the end of the step part is removed first, so the folders of `B10a` and `B10b` both count for B10. |
| 969 | `            if fo:` | The next two lines run only when the step has a folder. |
| 970 | `                R.add((s, st), f"Session {e(s)}, step {st}: " + ', '.join(f'<code>{e(os.path.abspath(x))}/</code>' for x in fo)` | Defines one reference under the pair of session and step. Its text starts with the session, the step and the full paths of the folders. |
| 971 | `                      + f" (<code>{st}.csv</code> with the header line of every launch and the rows I, T, P" + (', C' if st == 'C3' else '') + ', and <code>env.txt</code>, <code>launches.txt</code>, <code>stderr.txt</code>).')` | Continues the text: it names the csv file of the step with the header line of every launch and the rows I, T and P (and C for step C3), and the files `env.txt`, `launches.txt` and `stderr.txt`. |
| 972 | `    return R` | Returns the object with all definitions. |
| 975 | `def tidy_refs(h):` | Starts the function `tidy_refs`. It moves the reference indexes in the finished HTML text `h` to the place that the user asks for. |
| 976 | `    """Rule of the user: a reference index stands at the end of the sentence that carries the claim, before its full stop.` | Description of `tidy_refs`: by a rule of the user, a reference index stands at the end of the sentence that makes the claim, before its full stop. |
| 977 | `    'claim. [Ref3]' becomes 'claim [Ref3].', and 'claim [Ref2]. [Ref3]' becomes 'claim [Ref2][Ref3].'. A reference is never repeated in one group."""` | Continues the description with two examples: an index after the full stop of a claim moves in front of that full stop, and it joins an index that already stands there. A reference is never repeated in one group. |
| 978 | `    def uniq(t):` | Starts the inner function `uniq`. It removes repeated indexes from a group. |
| 979 | `        seen = []` | `seen`: the indexes found so far, empty at first. |
| 980 | `        for x in re.findall(r'\[Ref\d+\]', t):` | Loop over the indexes in the text. The pattern fits a square bracket, `Ref`, digits and the closing bracket. |
| 981 | `            if x not in seen:` | Tests whether the index is new. |
| 982 | `                seen.append(x)` | A new index is added to `seen`. |
| 983 | `        return ''.join(seen)` | Returns the indexes in their first order, each once. |
| 984 | `    h = re.sub(r'\s*((?:\[Ref\d+\])*)\.(</code>)?\s+((?:\[Ref\d+\])+)(?=\s*</(?:p\|li\|div)>\|\s+[A-Z("<])', lambda mm: (mm.group(2) or '') + ' ' + uniq(mm.group(1) + mm.group(3)) + '.', h)` | First replacement. The pattern fits, in this order: optional spaces, group 1 with the indexes that stand directly before a full stop (it may be empty), the full stop, group 2 with a closing `code` tag directly after it (it may be missing), one or more spaces, and group 3 with one or more indexes. The match counts only when the end of a paragraph, of a list item or of a `div` follows, or spaces and then an upper-case letter, an opening bracket, a double quote or the start of a tag. The match is replaced by the closing `code` tag when there was one, one space, the indexes of group 1 and group 3 without repeats, and the full stop. |
| 985 | `    return re.sub(r'(?:\[Ref\d+\]){2,}', lambda mm: uniq(mm.group(0)), h)` | Second replacement: in every run of two or more indexes that stand directly one after the other, each index is kept once. The result is returned. |

### `per_session`, `details`, `hyp_bullets` and `sec_hyp`: the hypothesis section (lines 988 to 1050)

| Line | Source | Explanation |
|---:|---|---|
| 988 | `# ---------------------------------------------------------------- sections` | Comment: here starts the code that builds the sections of the generated page. |
| 990 | `def per_session(m, step, fn, what):` | Starts the function `per_session`. It builds the part of a step section that is repeated for each session. `fn` is the function that draws the block of one session. `what` is a sentence for the case that the step is missing. |
| 991 | `    """One block per session. A session without the step gets 'Insufficient data'."""` | Description of `per_session`: one block per session. A session without the step gets the text `Insufficient data`. |
| 992 | `    o = []` | `o`: the list of the HTML pieces, empty at first. |
| 993 | `    for s in m['sessions']:` | Loop over the sessions. |
| 994 | `        if len(m['sessions']) > 1:` | The next line runs only when the page has more than one session. |
| 995 | `            o.append(f'<h3>Session {e(s)}</h3>')` | Adds a heading of level 3 with the escaped session name. |
| 996 | `        if step not in m['S'][s]:` | Tests whether the session has no model of the step. |
| 997 | `            o.append(missing(f'Session {e(s)} has no process of step {step}. {what}'))` | Then the `Insufficient data` box is added. It says that the session has no process of the step, followed by the sentence `what`. |
| 998 | `        else:` | In the other case the next line applies. |
| 999 | `            o.append(fn(m, s, m['S'][s][step]))` | Adds the block that `fn` builds from the model, the session name and the model of the step. |
| 1000 | `    return '\n'.join(o)` | Returns the pieces as one text. |
| 1003 | `def details(summary, body):` | Starts the function `details`. |
| 1004 | `    return f'<details><summary>{summary}</summary>{body}</details>'` | Returns a `details` element: a block that the browser shows folded, with the line `summary` as the text that opens it. |
| 1007 | `def hyp_bullets(m):` | Starts the function `hyp_bullets`. |
| 1008 | `    """One line per hypothesis, directly under the Short version."""` | Description of `hyp_bullets`: one line per hypothesis, directly under the Short version of the page. |
| 1009 | `    o = ['<ul>']` | `o`: the list of the HTML pieces. It starts with the opening tag of a list. |
| 1010 | `    for h in m['hyp']:` | Loop over the rows of the hypothesis table. |
| 1011 | `        w = f'"{h["word"]}"' + (f' ({h["plan_word"]})' if h['plan_word'] else '')` | `w`: the word of the page in double quotes, followed by the word of the plan in brackets when the row has one. |
| 1012 | `        o.append(f'<li><b>{e(h["label"])}</b> ({e(h["meaning"])}): <b>{e(w)}</b>' + (', open for the user' if h['open'] else '') + (f'. {e(h["short"][0].upper() + h["short"][1:])}.' if h['short'] else '.') + '</li>')` | Adds one list item: the label in bold, the meaning in brackets, the word in bold, the words `open for the user` when the row has an open question, and then the short text as a sentence with an upper-case first letter. |
| 1013 | `    o.append('</ul>')` | Adds the closing tag of the list. |
| 1014 | `    return '\n'.join(o)` | Returns the list as one text. |
| 1017 | `def sec_hyp(m, R):` | Starts the function `sec_hyp`. It builds the section `Result per hypothesis`. `R` is the object with the references. |
| 1018 | `    one = len(m['sessions']) < 2` | `one`: true when the page has fewer than 2 sessions. |
| 1019 | `    o = ['<h2 id="hyp">Result per hypothesis</h2>']` | `o`: the list of the HTML pieces of the section. It starts with the heading of level 2, which has the anchor name `hyp`. |
| 1020 | `    if one:` | The next two lines run only with one session. |
| 1021 | `        o.append(f'<p class="take">This page is built from one session ({e(m["sessions"][0])}). Rule 11 of the plan gives "rejected" only when the bounded prediction failed in two sessions {R("plan")}. '` | Adds a highlighted paragraph. It names the session and says that rule 11 of the plan gives `rejected` only when the bounded prediction failed in two sessions, with a citation of the plan. |
| 1022 | `                 'So no row of this table can say "rejected". A row that says "not rejected" with the note "prediction failed in this session" becomes "rejected" if the second session shows the same.</p>')` | Continues the paragraph: so no row of the table can say `rejected`. A row that says `not rejected` with the note that the prediction failed in this session becomes `rejected` if the second session shows the same. |
| 1023 | `    else:` | With more sessions the next line applies. |
| 1024 | `        o.append(f'<p>The page is built from {len(m["sessions"])} sessions ({", ".join(map(e, m["sessions"]))}). "rejected" needs a failed prediction in every session {R("plan", "analyze")}.</p>')` | Adds a paragraph with the number and the names of the sessions. It says that `rejected` needs a failed prediction in every session, with citations of the plan and of the analysis script. |
| 1025 | `    o.append(f'<p>The third column quotes the output of the analysis script as it stands in <code>hypotheses.txt</code> {R("antxt")}. Where the word of this page differs from it, or where two readings of a rule exist, the last column gives the other reading and its reason. '` | Adds a paragraph that explains the columns. The third column quotes the output of the analysis script, unchanged, from the file `hypotheses.txt`. The last column gives the other reading and its reason, where the word of the page differs from that output or where two readings of a rule exist. |
| 1026 | `             'An item marked "open for the user" is a judgment that this page does not make.</p>')` | Continues the paragraph: an item marked `open for the user` is a judgment that the page does not make. |
| 1027 | `    rows, rec = [], []` | `rows`: the rows of the first table. `rec`: the rows of the second table. Both are empty at first. |
| 1028 | `    for h in m['hyp']:` | Loop over the rows that `hypotheses` built. |
| 1029 | `        w = f'<b>{h["word"]}</b>' + (f' ({h["plan_word"]})' if h['plan_word'] else '')` | `w`: the cell with the word of the page in bold, and the word of the plan in brackets when the row has one. |
| 1030 | `        if h['one_session']:` | Tests the mark `one_session` of the row (line 452). |
| 1031 | `            w += '<br>prediction failed in this session'` | Then the cell gets a second line: the prediction failed in this session. |
| 1032 | `        if h['open']:` | Tests whether the row has an open question. |
| 1033 | `            w += '<br><b>open for the user</b>'` | Then the cell gets a line with the bold words `open for the user`. |
| 1034 | `        other = e(h['other']) + (f' <b>Open for the user:</b> {e(h["open"])}.' if h['open'] else '')` | `other`: the cell with the escaped other reading. When the row has an open question, a sentence follows that starts with the bold words `Open for the user:` and gives the question. |
| 1035 | `        rows.append((f'<b>{e(h["label"])}</b><br>{e(h["meaning"])}', w, e(h['strict']), e(h['basis']), other or '-'))` | Adds the row of the first table: the label in bold with the meaning below it, the word cell, the output of the analysis rule, the basis, and the other reading or `-`. |
| 1036 | `        rec.append((e(h['label']), e(h['text']), h['step'], e(str(h['n'])), e(str(h['aa'])), e(flag_txt(h['flags']))))` | Adds the row of the second table: the label, the bounded prediction, the step, the text on the processes, the text on the A/A spread or control, and the flags per session. |
| 1037 | `    o.append(table(['Hypothesis, in plain words', 'Word of this page', 'Output of the analysis rule as it stands', 'Basis and caveat (computed)', 'Other reading and its reason'], rows, 'pt hy'))` | Adds the first table. Its five columns: the hypothesis in plain words, the word of this page, the unchanged output of the analysis rule, the basis and caveat, and the other reading with its reason. |
| 1038 | `    o.append(table(['Hypothesis', 'Bounded prediction that the step tests', 'Step', 'Processes', 'A/A spread or control', 'Result per session'], rec, 'pt hr'))` | Adds the second table. Its six columns: the hypothesis, the bounded prediction that the step tests, the step, the processes, the A/A spread or control, and the result per session. |
| 1039 | `    o.append(f'<p class="cap">Result per session: "fail" means the prediction failed in that session, and "hold" means it held. "supported" and "contradicted" are the words of the plan for one cell of H11 in one session. '` | Adds a caption for the column with the result per session: `fail` means that the prediction failed in that session, and `hold` that it held. `supported` and `contradicted` are the words of the plan for one cell of H11 in one session. |
| 1040 | `             f'The words of H7a, H7b and of the cells of H11 come from the analysis script {R("analyze")}. That script maps each step result to a word, and its authors call the mapping their own reading {R("devs")}. '` | Continues the caption: the words of H7a, H7b and of the cells of H11 come from the analysis script. That script maps each step result to a word, and its authors call the mapping their own reading. Each of the two sentences has a citation. |
| 1041 | `             f'The words of H8, H9a, H9b, H10, the B5 statement and the merged word of H11 follow the page rules 1 to 4 {R("gen")}.</p>')` | Continues the caption: the words of H8, H9a, H9b, H10, of the B5 statement and the merged word of H11 follow the page rules 1 to 4, with a citation of this script. |
| 1042 | `    o.append('<h3>Page rules (rules of this page, not of the plan)</h3><ul>'` | Adds a heading of level 3 for the page rules. It says that they are rules of this page and not of the plan. The line also opens a list. |
| 1043 | `             f'<li><b>Page rule 1.</b> The labels split and uniform are not used. This is decision 2 of the user of 2026-11-13: "Where a rule needs a label that the data do not give, the word is not resolved. No rule is adapted" {R("decisions")}. The reason is that q did not fall into two groups in Part A {R("partA")}. The page reports q and the median thread rate of each mesh in place of a label.</li>'` | List item for page rule 1: the labels split and uniform are not used. It quotes decision 2 of the user of 2026-11-13 and gives as the reason that q did not fall into two groups in Part A. It says that the page reports q and the median thread rate of each mesh in place of a label. |
| 1044 | `             '<li><b>Page rule 2.</b> The analysis gives H11 one result per cell (one kernel in one setting) and session. Over the sessions a cell is "not rejected (supported)" only if it is supported in every session. It is "rejected (contradicted)" only if it is contradicted in every session. It is "not observed" if it is not observed in every session. In every other case it is "not resolved". So a cell that is supported in one session only counts as "not resolved". '` | List item for page rule 2. This line: how the analysis merges one cell over the sessions. A cell is `not rejected (supported)` only if it is supported in every session, `rejected (contradicted)` only if it is contradicted in every session, `not observed` if it is not observed in every session, and `not resolved` in every other case. This text describes the case of 2 or more sessions (line 549). |
| 1045 | `             'The word of the table is "not observed" if every cell is "not observed". It is "rejected" if every cell with another word is "rejected". It is "not rejected" if at least one cell is "not rejected" and none is "rejected". Otherwise it is "not resolved".</li>'` | Continues the item: how the word of the table follows from the cells, in the wording of lines 551 to 552. |
| 1046 | `             f'<li><b>Page rule 3.</b> H9b needs at least two sessions. The plan allows the words "observed" and "not observed" for it {R("plan")}. With two or more sessions this page writes "not observed" if the ranges of q of old read at 64+56 threads overlap between the sessions, and "not resolved" otherwise. The user has not approved this rule. It is marked "open for the user" in the table.</li>'` | List item for page rule 3: H9b needs at least two sessions, the plan allows the words `observed` and `not observed` for it, and the page writes `not observed` if the ranges of q of old read at 64+56 threads overlap between the sessions, and `not resolved` otherwise. It adds that the user has not approved this rule. |
| 1047 | `             f'<li><b>Page rule 4.</b> H10 is "not tested". The plan gives the counters of C3 no decision, and step D1 was not run {R("plan")}.</li></ul>')` | List item for page rule 4: H10 is `not tested`. The text says that the plan gives the counters of C3 no decision and that step D1 was not run. The line also closes the list. |
| 1048 | `    return '\n'.join(o)` | Returns the section as one text. |

### `sec_facts` and `sec_sessions`: decisions, deviations, settings and times (lines 1051 to 1130)

| Line | Source | Explanation |
|---:|---|---|
| 1051 | `ONE_THREAD_STEPS = {'B1', 'B2', 'B3', 'B4', 'B6', 'C1', 'C2'}` | `ONE_THREAD_STEPS`: the steps of question Q1 of the plan, which run one thread. `sec_load` uses the set in line 1188. |
| 1054 | `def sec_facts(m, R):` | Starts the function `sec_facts`. It builds the section on the decisions, the deviations and the settings of the runs. |
| 1055 | `    o = ['<h2 id="facts">Decisions, deviations and settings of the runs</h2>']` | `o`: the list of the HTML pieces. It starts with the heading of level 2, which has the anchor name `facts`. |
| 1056 | `    o.append(f'<p><b>Decision of the user (2026-11-13).</b> The labels split and uniform of the handoff are not used (page rule 1) {R("decisions", "partA", "handoff")}.</p>')` | Adds a paragraph on the decision of the user of 2026-11-13: the labels split and uniform of the handoff are not used (page rule 1). It has three citations. |
| 1057 | `    o.append('<p class="miss"><b>Open decision (not made): level limits at 8 MiB.</b> The plan labels an interval with one thread at 8 MiB by the rate of asm read: low below 69 GB/s, high above 70.5 GB/s. '` | Starts a highlighted paragraph on a decision that is still open: the level limits at 8 MiB. This line: the plan labels an interval with one thread at 8 MiB by the rate of asm read, low below 69 GB/s and high above 70.5 GB/s. |
| 1058 | `             + ('These provisional limits do not fit the data of both sessions. ' if len(m['sessions']) > 1 else 'These provisional limits do not fit the data of this session. ')` | Continues the paragraph with a typed sentence: these provisional limits do not fit the data of both sessions, or of this session when the page has one. The script does not compute this statement from the input. |
| 1059 | `             + f'The rate of asm read forms different groups per CPU and per step. The Q1 page gives the evidence {R("q1page", "antxt")}. The limits were not changed. The user decides on new limits {R("decisions")}. No result on this page uses these limits.</p>')` | Continues the paragraph with more typed sentences: the rate of asm read forms different groups per CPU and per step, the Q1 page gives the evidence, the limits were not changed, the user decides on new limits, and no result on this page uses these limits. |
| 1060 | `    sets, b8s, c3s = [], {}, {}` | Three start values. `sets`: the list items on the setting of the later steps. `b8s`: the sessions per set of thread counts of B8. `c3s`: the sessions per set of sequences of C3. |
| 1061 | `    for s in m['sessions']:` | Loop over the sessions. |
| 1062 | `        d = m['S'][s]` | `d`: the model of the session. |
| 1063 | `        if 'B7' in d:` | The lines up to line 1087 run only when the session has B7. |
| 1064 | `            ch = d['B7']['chosen']; res = d['B7']['res']` | `ch`: the setting that the handoff rule selects (line 270). `res`: the result of the analysis for B7. |
| 1065 | `            if not ch:` | Tests whether no setting was selected. |
| 1066 | `                sets.append(f'<li>Session {e(s)}: D is resolved in no setting of B7 with the common stop. So the handoff gives no setting for B8, B5, B9 and C3 {R("handoff")}.</li>')` | Then a list item says that D is resolved in no setting of B7 with the common stop, and that the handoff then gives no setting for B8, B5, B9 and C3. The handoff does name a setting when D is resolved with whole passes only (line 270). |
| 1067 | `            else:` | In the other case the lines up to line 1087 run. |
| 1068 | `                md = res['settings'][ch]['metrics']['M_hist']['median_D']` | `md`: the median D with `M_hist` in the selected setting. |
| 1069 | `                used = d['later_settings']; u = d['used_setting']` | `used`: the settings of B8, B5 and B9 per step. `u`: the one setting of all three, or `None`. |
| 1070 | `                if not used:` | Tests whether the input holds no process of B8, B5 or B9. |
| 1071 | `                    sets.append(f'<li>Session {e(s)}: the handoff rule selects "{sname(ch)}" (median D {fx(md)} GB/s) {R("handoff")}. No process of B8, B5 or B9 is in the input.</li>')` | Then a list item names the selected setting with its median D and says that no process of these steps is in the input. |
| 1072 | `                elif u == ch:` | Tests whether the three steps ran in the selected setting. |
| 1073 | `                    sets.append(f'<li>Session {e(s)}: the handoff rule selects "{sname(ch)}" (median D {fx(md)} GB/s) {R("handoff")}. The header lines of {join_and(used)} show this setting for every process {R((s, "B7"))}.</li>')` | Then a list item names the selected setting with its median D and says that the header lines of these steps show this setting for every process. |
| 1074 | `                else:` | In every other case the lines up to line 1087 build a list item on a deviation. |
| 1075 | `                    t = f'<li><b>Deviation, session {e(s)}.</b> The handoff rule selects "{sname(ch)}" (median D {fx(md)} GB/s) {R("handoff")}. '` | `t`: the start of the item: the bold words `Deviation, session` with the session name, and the selected setting with its median D. |
| 1076 | `                    t += 'The header lines show another setting: ' + ', '.join(f"{st} ran with \"{' and '.join(sname(x) for x in v)}\"" for st, v in used.items()) + f' {R((s, "B8"))}. '` | Continues the item: the header lines show another setting. For each of the steps B8, B5 and B9 it names the settings in which the step ran. |
| 1077 | `                    if u and u in res['settings']:` | The next five lines run only when the three steps ran in one setting and B7 has that setting. |
| 1078 | `                        vu = res['settings'][u]` | `vu`: the result of B7 for that setting. |
| 1079 | `                        t += f"In B7 of this session D in that setting is {vu['decision']}, with a median of {fx(vu['metrics']['M_hist']['median_D'])} GB/s. "` | Adds a sentence: the decision for D in that setting in B7 of this session, and its median in GB/s. |
| 1080 | `                        c = next((c for c in res['changes'].values() if {c['first'], c['second']} == {u, ch}), None)` | `c`: the comparison of B7 between the used setting and the selected setting. It exists when the two differ in exactly one factor. |
| 1081 | `                        if c and c['metrics']['M_hist']['change'] is not None:` | The next line runs only when the comparison has a value. |
| 1082 | `                            t += f"The change of D between the two settings is {fx(abs(c['metrics']['M_hist']['change']))} GB/s, with a limit of {fx(c['metrics']['M_hist']['sum_of_aa_spreads'])} GB/s ({c['decision']}). "` | Adds a sentence: the absolute change of D between the two settings, its limit, and the decision. |
| 1083 | `                    first = m['sessions'][0]` | `first`: the first session of the page. |
| 1084 | `                    if s != first and 'B7' in m['S'][first] and u == m['S'][first]['B7']['chosen']:` | Tests three things: this is not the first session, the first session has B7, and the used setting is the one that the rule selects in the first session. |
| 1085 | `                        t += f'It is the setting that the rule selects in session {e(first)}. The run script of session 2 repeats the settings of session 1, so the two sessions ran the same settings {R("session2")}. '` | Then two sentences are added: it is the setting that the rule selects in the first session, and the run script of session 2 repeats the settings of session 1. The second sentence is typed with these two session numbers. |
| 1086 | `                    t += 'The user did not decide this.</li>'` | Ends the item with the typed sentence that the user did not decide this. |
| 1087 | `                    sets.append(t)` | Adds the item to `sets`. |
| 1088 | `        if 'B8' in d:` | The next two lines run only when the session has B8. |
| 1089 | `            b = d['B8']` | `b`: the model of B8. |
| 1090 | `            b8s.setdefault((tuple(b['mesh0']), tuple(b['counts'])), []).append(s)` | Adds the session to `b8s`, under its mesh-0 thread counts and its mesh-1 thread counts. |
| 1091 | `        if 'C3' in d:` | The next two lines run only when the session has C3. |
| 1092 | `            seqs = sorted({g['group'] for g in d['C3']['res'].get('groups', [])})` | `seqs`: the group names of C3 in this session, sorted. A group name is a setting followed by the words `B7 sequence` or `B5 sequence`. |
| 1093 | `            c3s.setdefault((sum(1 for x in seqs if x.endswith('B7 sequence')), tuple(x.split(' ')[0] for x in seqs if x.endswith('B5 sequence'))), []).append(s)` | Adds the session to `c3s` under two values: the number of settings in which the B7 sequence ran with counters, and the settings in which the B5 sequence ran. |
| 1094 | `    who = lambda ss: ('Both sessions' if len(ss) == 2 and len(m['sessions']) == 2 else 'Session ' + join_and(map(e, ss)))` | `who`: a small function that names sessions: `Both sessions` when the page has two and both are meant, or the word `Session` with the names. |
| 1095 | `    o.append('<ul>' + ''.join(sets))` | Opens a list and adds the items of `sets`. |
| 1096 | `    for (m0, counts), ss in b8s.items():` | Loop over the sets of thread counts of B8. |
| 1097 | `        o.append(f'<li>{who(ss)}: B8 ran {" and ".join(str(a) for a in m0)} threads on mesh 0 with these counts of mesh-1 threads: {", ".join(map(str, counts))} {R(*[(s, "B8") for s in ss])}. '` | Adds a list item: the sessions, the thread count on mesh 0, and the counts of mesh-1 threads with which B8 ran, with citations of the B8 folders. |
| 1098 | `                 f'Part A gave no pair of counts between which the pattern changes {R("partA")}.</li>')` | Continues the item with a typed sentence: Part A gave no pair of counts between which the pattern changes. It cites the Part A page. |
| 1099 | `    for (nb7, b5s), ss in c3s.items():` | Loop over the sets of sequences of C3. |
| 1100 | `        o.append(f'<li>{who(ss)}: C3 ran the B7 sequence with counters in {pl(nb7, "setting", "settings")}' + (f', and the B5 sequence in the setting "{", ".join(sname(x) for x in b5s)}"' if b5s else '') + f' {R(*[(s, "C3") for s in ss])}.</li>')` | Adds a list item: the sessions, the number of settings in which C3 ran the B7 sequence with counters, and the setting of the B5 sequence when it ran. |
| 1101 | `    o.append('<li>The same sessions also ran the steps with one thread of question Q1 (B1 to B4, B6, C1, C2). Q1 asks why one thread with an 8 MiB buffer behaves differently from the other sizes. Those steps are on the Q1 page and not here ' + R('q1page') + '. Two more points of Q1 also matter for this page:'` | Adds a typed list item: the same sessions also ran the one-thread steps of question Q1 (B1 to B4, B6, C1, C2), and those steps are on the Q1 page. It says that two more points of Q1 matter for this page. |
| 1102 | `             '<ul><li>B2, B3 and C2 were run although B1 at 8 MiB is not formally resolved. This is a deviation from the plan. Its purpose is that data exist if the limits are revised ' + R('plan') + '.</li>'` | First typed point: B2, B3 and C2 were run although B1 at 8 MiB is not formally resolved. The text calls this a deviation from the plan and gives its purpose. |
| 1103 | `             f'<li>The binary <code>bwx_o52</code> (the build of <code>bwx</code> with both copy loops at offset 52) is built with the compiler option <code>-falign-loops=1</code>. Without it the compiler moved the C copy loop from offset 52 to offset 0 modulo 64 {R("offsets")}.</li></ul></li>')` | Second typed point: the binary `bwx_o52` is built with the compiler option `-falign-loops=1`. The text says that without it the compiler moved the C copy loop from offset 52 to offset 0 modulo 64. |
| 1104 | `    o.append('</ul>')` | Closes the list. |
| 1105 | `    o.append(sec_sessions(m, R))` | Adds the paragraph on the times of the sessions (lines 1109 to 1128). |
| 1106 | `    return '\n'.join(o)` | Returns the section as one text. |
| 1109 | `def sec_sessions(m, R):` | Starts the function `sec_sessions`. |
| 1110 | `    """When the sessions ran, from env.txt. Rule 10 of the plan asks for two sessions some hours apart."""` | Description of `sec_sessions`: when the sessions ran, from `env.txt`. Rule 10 of the plan asks for two sessions some hours apart. |
| 1111 | `    T = m['timing']` | `T`: the result of `timing_model`. |
| 1112 | `    if not T['sessions']:` | Tests whether no session has a start time. |
| 1113 | `        return missing('No <code>env.txt</code> with a start time was found, so the times of the sessions are not known.')` | Then the function returns the `Insufficient data` box: no `env.txt` with a start time was found. |
| 1114 | `    t = '<p id="when"><b>When the sessions ran.</b> ' + ' '.join(` | `t`: the paragraph, with the anchor name `when`. It starts with the bold words `When the sessions ran.` |
| 1115 | `        f"Session {e(s)} ran from {clock(v['t0'])} to {clock(v['t1']) if v['t1'] else '-'} UTC (start on {time.strftime('%Y-%m-%d', time.gmtime(v['t0']))})." for s, v in T['sessions'].items())` | Continues the text: one sentence per session with its start and its end as times of day in UTC, and the date of the start. |
| 1116 | `    for a, b, g in T['gaps']:` | Loop over the gaps between two sessions. |
| 1117 | `        t += f' Session {e(b)} started {hm(g)} after session {e(a)} ended.'` | Adds a sentence: how long after the end of the first session the second one started, in the words of `hm`. |
| 1118 | `    ts = T['same_step']` | `ts`: the distance between the same steps of the first two sessions, or `None`. |
| 1119 | `    if ts:` | The lines up to line 1127 run only when it exists. |
| 1120 | `        t += f' So each step of session {e(ts[1])} started {hm(ts[2])}' + ('' if hm(ts[2]) == hm(ts[3]) else f' to {hm(ts[3])}') + f' after the same step of session {e(ts[0])}.'` | Adds a sentence: how long after the same step of the first session each step of the second session started. It gives one duration, or the shortest and the longest. |
| 1121 | `        if T['same_boot'] is True:` | Tests whether all uptime readings give one start time of the machine. |
| 1122 | `            t += f' The uptime readings of all {T["boot_n"]} result folders give one boot time, so the machine was not restarted between the sessions.'` | Then a sentence says so, with the number of result folders, and concludes that the machine was not restarted between the sessions. |
| 1123 | `        elif T['same_boot'] is None:` | Tests whether the uptime readings are not complete. When all readings exist and the computed start times differ by 30 s or more, neither sentence is added, so the page then says nothing on a restart. |
| 1124 | `            t += f' {ID}: whether the machine was restarted between the sessions. An uptime reading in every <code>env.txt</code> would give it.'` | Then a sentence starts with `Insufficient data` and says that an uptime reading in every `env.txt` would show whether the machine was restarted. |
| 1125 | `        short = [g for _, _, g in T['gaps'] if g < 3600]` | `short`: the gaps between sessions that are shorter than 3600 s (1 hour). |
| 1126 | `        t += (f' Rule 10 of the plan asks for two sessions some hours apart {R("plan")}. The handoff reads this as: every deciding step is run twice with some hours between its two runs {R("handoff")}. '` | Adds two sentences with citations: rule 10 of the plan asks for two sessions some hours apart, and the handoff reads this as two runs of every deciding step with some hours between them. |
| 1127 | `              + ('That reading is met. The two sessions are still one continuous run of one night, and not two separate visits.' if short else 'That reading is met.'))` | Adds the typed sentence that this reading is met. The script does not compare the distance with a number of hours. When a gap is shorter than 1 hour, a second sentence says that the two sessions are still one continuous run of one night and not two separate visits. |
| 1128 | `    return t + '</p>'` | Returns the paragraph. |

### `sec_load`: the system load of every step (lines 1131 to 1210)

| Line | Source | Explanation |
|---:|---|---|
| 1131 | `def sec_load(m, R):` | Starts the function `sec_load`. It builds the section on the system load of every step. |
| 1132 | `    o = ['<h2 id="load">System load of every step</h2>']` | `o`: the list of the HTML pieces. It starts with the heading of level 2, which has the anchor name `load`. |
| 1133 | `    tot = dict(n=0, wait=0, lmax=0.0, thr=0)` | `tot`: totals over all steps and sessions: the number of launches `n`, the number of launches that waited, the highest load average `lmax`, and the highest thread count `thr`. |
| 1134 | `    rmin, rmax, lgmax, nlog = [], [], [], 0` | Four more start values: the lowest and the highest numbers of runnable tasks per step, the highest numbers of logins per step, and the number of login readings. |
| 1135 | `    rows, events = [], []` | `rows`: the rows of the load table. `events`: the launches with a busy process of another account. |
| 1136 | `    for s in m['sessions']:` | Loop over the sessions. |
| 1137 | `        for st, L in m['S'][s]['load'].items():` | Loop over the steps of the session with their load readings `L` (lines 204 to 212). |
| 1138 | `            tot['n'] += L['n']; tot['wait'] += L['n_waited']; tot['lmax'] = max(tot['lmax'], L['load_max'] or 0); tot['thr'] = max(tot['thr'], L['threads_max'])` | Updates the four totals with the values of this step. |
| 1139 | `            rmin += [L['runnable_min']] if L['runnable_min'] is not None else []; rmax += [L['runnable_all_max']] if L['runnable_all_max'] is not None else []` | Adds the lowest and the highest number of runnable tasks of the step to the two lists, when they exist. |
| 1140 | `            lgmax += [L['logins_all_max']] if L['logins_all_max'] is not None else []; nlog += L['n_log_readings']` | Adds the highest number of logins of the step, and counts its login readings. |
| 1141 | `            events += [dict(x, session=s) for x in L['other_events']]` | Adds the events of the step to `events`, each with its session. |
| 1142 | `            bo = ', '.join(f'{e(c)} of {e(u)} {fx(v, 1)} %' for v, u, c in L['busy_other'][:1]) or '-'` | `bo`: the busiest process of another account: its command, its account and its highest CPU share with 1 decimal, or `-`. |
| 1143 | `            bm = ', '.join(f'{e(c)} of {e(u)} {fx(v, 1)} %' for v, u, c in L['busy_own']) or '-'` | `bm`: the same for the two busiest processes of our own accounts. |
| 1144 | `            rows.append((e(s), st, L['n'], NW(f'{L["utc"][0]} to {L["utc"][1]}'), NW(f'{f(L["load_min"])} to {f(L["load_max"])}'), f"{L['runnable_max']} / {'-' if L['runnable_txt_max'] is None else L['runnable_txt_max']}",` | Starts the row of the step: the session, the step, the number of launches, the time of the first and of the last launch, the lowest and the highest load average of the last minute, and the highest number of runnable tasks from the header lines and from `launches.txt`. |
| 1145 | `                         f"{L['n_waited']} / {L['wait_max']:g}" if L['wait_max'] is not None else '-', L['logins_max'], bm, bo, R((s, st))))` | Continues the row: the number of launches that waited and the longest wait in s, the highest number of logins of a header line, the two process texts, and the citation of the result folders. |
| 1146 | `    if not rows:` | Tests whether there is no row. |
| 1147 | `        return '\n'.join(o) + missing('No header line of a launch was found. The header lines of the csv files give the load.')` | Then the function returns the heading and the `Insufficient data` box: no header line of a launch was found. |
| 1148 | `    o.append(f'<p class="take">The 1-minute load average at a launch went up to {fx(tot["lmax"])} tasks. Our own benchmark process with up to {tot["thr"]} threads ended directly before such a launch. '` | Adds a highlighted paragraph: the highest load average of the last minute at a launch, in tasks. A typed sentence follows: our own benchmark process, with up to the highest thread count, ended directly before such a launch. |
| 1149 | `             'The load average covers about the last minute, so it still counts those threads. So the load average alone does not show whether another user ran something. The readings below do.</p>')` | Continues the paragraph with typed sentences: the load average covers about the last minute, so it still counts those threads, and alone it does not show whether another user ran something. |
| 1150 | `    run_t = (f'{min(rmin)} at each' if min(rmin) == max(rmax) else f'{min(rmin)} or {max(rmax)} at each' if max(rmax) - min(rmin) == 1 else f'{min(rmin)} to {max(rmax)} at each') if rmin and rmax else '-'` | `run_t`: a text on the runnable tasks over all readings: one number when the lowest and the highest are equal, two numbers with `or` when they differ by 1, and a range in the other cases. Without a reading it is `-`. |
| 1151 | `    o.append('<p>The run script took these readings directly before each launch:</p><ul>'` | Adds a paragraph and opens a list of the readings that the run script took directly before each launch. |
| 1152 | `             f'<li>Runnable tasks: {run_t} of the {tot["n"]} launches, in the header line and in <code>launches.txt</code>. One of them is the script that reads the value.'` | List item on the runnable tasks: the text `run_t` and the number of launches, from the header line and from `launches.txt`. A typed sentence says that one of the tasks is the script that reads the value. |
| 1153 | `             + (' A second one, where present, is not identified by the reading.' if rmax and max(rmax) > 1 else '') + '</li>'` | Continues the item: when a reading is above 1, a sentence says that a second task, where present, is not identified by the reading. |
| 1154 | `             f'<li>Waits: {tot["wait"]} of {tot["n"]} launches had to wait for an idle system (<code>waited_s</code> above 0).</li>'` | List item on the waits: how many of the launches had to wait for an idle system, so have a `waited_s` above 0. |
| 1155 | `             + (f'<li>Logged-in users: 0 at each of the {tot["n"]} launches ({nlog} readings).</li>' if lgmax and max(lgmax) == 0 else f'<li>Logged-in users: up to {max(lgmax) if lgmax else "-"} at a launch.</li>')` | List item on the logged-in users. When the highest reading is 0, it says 0 at each launch and gives the number of readings. If not, it gives the highest number. |
| 1156 | `             + f'<li>Busiest processes: <code>ps</code> listed a process of another account above {BUSY_LIMIT:g} % of one CPU at {pl(len(events), "launch", "launches")} of {tot["n"]}.</li></ul>')` | List item on the busiest processes: at how many of the launches `ps` listed a process of another account above 10 % of one CPU. The line also closes the list. |
| 1157 | `    for x in events:` | Loop over these events. |
| 1158 | `        k = sum(1 for y in events if (y['session'], y['step'], y['comm']) == (x['session'], x['step'], x['comm']))` | `k`: the number of launches of the same session and step at which the same command was above the limit. |
| 1159 | `        t = (f"<p class=\"miss\"><b>Another account, session {e(x['session'])}, step {x['step']}.</b> At the launch <code>{e(x['tag'])}</code> ({e(x['utc'])} UTC), <code>ps</code> listed the process <code>{e(x['comm'])}</code> of the account {e(x['user'])} at {fx(x['pc'], 1)} % of one CPU. "` | `t`: a highlighted paragraph for the event. It starts with the bold words `Another account` and the session and step. Then it gives the tag and the time of the launch, the command, the account and the CPU share. |
| 1160 | `             f"It was listed above {BUSY_LIMIT:g} % at {k} of {x['n_launches']} launches of that step. The load average at that launch was {fx(x['load'])} tasks, with {pl(x['runnable'], 'runnable task', 'runnable tasks')}. "` | Continues the paragraph: at how many launches of that step the process was above the limit, and the load average and the runnable tasks at that launch. |
| 1161 | `             '<code>ps</code> divides the CPU time of a process by the time since its start, so a process that has just started can show a high value. ')` | Continues the paragraph with a typed sentence: `ps` divides the CPU time of a process by the time for which the process has existed, so a process that started a moment before the reading can show a high value. |
| 1162 | `        if x['comm'].startswith('check-new-relea'):` | Tests whether the command name starts with `check-new-relea`. |
| 1163 | `            t += 'The name is cut to 15 characters by <code>ps</code>. The program is <code>check-new-release</code>, the check of the operating system for a new release. '` | Then a typed sentence is added: `ps` cuts the name to 15 characters, and the program is `check-new-release`, the check of the operating system for a new release. |
| 1164 | `        c3 = m['S'][x['session']].get('C3')` | `c3`: the model of C3 of that session, or `None`. |
| 1165 | `        if x['step'] == 'C3':` | The next five lines run only when the event belongs to step C3. |
| 1166 | `            t += 'Step C3 gives a description and no decision. '` | Adds the sentence that step C3 gives a description and no decision. |
| 1167 | `            if c3 and c3.get('lowest') and c3['lowest']['tag'] == x['tag']:` | Tests whether the thread with the lowest CPU share of the session ran in the process of this launch. |
| 1168 | `                lw = c3['lowest']` | `lw`: the values of that thread (line 368). |
| 1169 | `                t += (f"In the same process a thread has the lowest CPU share of the session: {fx(lw['share'] * 100, 2)} % on CPU {lw['cpu']} (section C3). "` | Adds a sentence: in the same process a thread has the lowest CPU share of the session, with the share in % and the CPU. |
| 1170 | `                      'Hypothesis, not tested: this process took CPU time from that thread. A record of the CPU on which it ran would confirm or reject it. ')` | Continues the text: a hypothesis, marked as not tested, that this process took CPU time from that thread, and the record that would confirm or reject it. |
| 1171 | `        o.append(t + f"{R((x['session'], x['step']))}</p>")` | Adds the paragraph with the citation of the result folders of the step. |
| 1172 | `    o.append(details('Load readings per session and step', table(` | Adds a folded block with the load table per session and step. |
| 1173 | `        ['Session', 'Step', 'Launches', 'UTC first to last', '1-minute load (tasks), lowest to highest', 'Runnable tasks, highest: header line / launches.txt',` | The first six column headings: session, step, launches, first and last UTC time, the load average of the last minute from lowest to highest, and the highest number of runnable tasks from the header line and from `launches.txt`. |
| 1174 | `         'Launches that waited / longest wait (s)', 'Logged-in users, highest', 'Busiest processes of our account (% of one CPU)', 'Busiest process of another account (% of one CPU)', 'Source'], rows, 'sm')` | The other five headings: launches that waited and the longest wait in s, the highest number of logged-in users, the busiest processes of our account, the busiest process of another account, and the source. |
| 1175 | `        + '<p class="cap">The process <code>ps</code> of our account is the reading itself: the script starts <code>ps</code> to write this list. A process name is cut to 15 characters by <code>ps</code>.</p>'))` | Adds a caption below the table: the process `ps` of our account is the reading itself, and `ps` cuts a process name to 15 characters. |
| 1176 | `    # visits` | Comment: the next lines handle the readings at the start of each result folder. |
| 1177 | `    env, cat = [], dict(pause=[], one=[], many=[])` | `env`: the rows of the second table. `cat`: three lists of folders, by what ran before the folder: `pause`, `one` and `many`. |
| 1178 | `    for s in m['sessions']:` | Loop over the sessions. |
| 1179 | `        for x in m['S'][s]['env']:` | Loop over the `env.txt` readings of the Q2 folders of the session. |
| 1180 | `            if x['present'] and 'start_utc' in x:` | Tests whether the file exists and has a start line. |
| 1181 | `                v = m['timing']['visits'].get((s, x['folder']), {})` | `v`: the values of `timing_model` for the folder before this one (lines 232 to 233). |
| 1182 | `                g = v.get('gap')` | `g`: the seconds from the end of that folder to the start of this one, or `None`. |
| 1183 | `                env.append((e(s), f'<code>{e(x["folder"])}</code>', e(x.get('steps', '-')), NW(e(x['start_utc'])), fx(x['start_load']), x['start_runnable'], ('-' if g is None else f'{g:g}'), e(v.get('prev_steps') or '-'),` | Starts the row of the folder: the session, the folder name, the steps of its visit, the start time, the load average of the last minute at the start, the runnable tasks at the start, the seconds `g`, and the steps of the visit before. |
| 1184 | `                            NW(e(x.get('end_utc', '-'))), f(x.get('end_load'))))` | Continues the row: the end time and the load average of the last minute at the end. |
| 1185 | `                name = f"{folder_step(x['folder'])} of {s}"` | `name`: the step part of the folder name and the session, for the sentences below. |
| 1186 | `                if g is None or g > 60:` | Tests whether no folder ended before, or the gap is above 60 s. |
| 1187 | `                    cat['pause'].append((name, x['start_load'], g))` | Then the folder goes to the list `pause`. |
| 1188 | `                elif set((v.get('prev_steps') or '').split()) <= ONE_THREAD_STEPS:` | If not: tests whether the visit before ran only steps of `ONE_THREAD_STEPS`. |
| 1189 | `                    cat['one'].append((name, x['start_load'], g, v.get('prev_steps')))` | Then the folder goes to the list `one`. |
| 1190 | `                else:` | In every other case the next line applies. |
| 1191 | `                    cat['many'].append((name, x['start_load'], g))` | The folder goes to the list `many`. |
| 1192 | `            else:` | For a folder without a start line the next line applies. |
| 1193 | `                env.append((e(s), f'<code>{e(x["folder"])}</code>', '-', f'{ID}: env.txt is missing', '-', '-', '-', '-', '-', '-'))` | Adds a row that says `Insufficient data: env.txt is missing`. |
| 1194 | `    t = '<p>Each result folder starts with one reading in <code>env.txt</code>, taken before its first launch. '` | `t`: a paragraph. It starts with the sentence that each result folder starts with one reading in `env.txt`, taken before its first launch. |
| 1195 | `    if cat['pause']:` | The next line runs only when the list `pause` is not empty. |
| 1196 | `        t += f"After a pause (no folder before it, or more than 60 s): {join_and(e(n) for n, _, _ in cat['pause'])}, with a start load of {rng([v for _, v, _ in cat['pause']])} tasks. "` | Adds a sentence: the folders that started after a pause, and the range of their start load in tasks. |
| 1197 | `    if cat['one']:` | The next two lines run only when the list `one` is not empty. |
| 1198 | `        t += (f"Directly after steps of question Q1 with one thread: {join_and(e(n) for n, _, _, _ in cat['one'])}, with a start load of {rng([v for _, v, _, _ in cat['one']])} tasks. "` | Adds a sentence: the folders that started directly after one-thread steps of question Q1, and the range of their start load. |
| 1199 | `              'That load is our own one-thread process. ')` | Continues with the typed sentence that this load is our own one-thread process. |
| 1200 | `    if cat['many']:` | The next two lines run only when the list `many` is not empty. |
| 1201 | `        t += (f"The other {pl(len(cat['many']), 'folder', 'folders')} started {rng([g for _, _, g in cat['many']], 0)} s after the end of a step with many threads, with a start load of {rng([v for _, v, _ in cat['many']])} tasks. "` | Adds a sentence: how many folders started after a step with many threads, the range of the seconds after its end, and the range of their start load. |
| 1202 | `              'That load still counts our own threads. ')` | Continues with the typed sentence that this load still counts our own threads. |
| 1203 | `    o.append(t + '</p>')` | Adds the paragraph. |
| 1204 | `    o.append(details('Readings at the start and the end of every result folder', table(` | Adds a folded block with the table of the readings at the start and the end of every result folder. |
| 1205 | `        ['Session', 'Folder', 'Steps of the visit (one login)', 'Start (UTC)', '1-minute load at the start (tasks)', 'Runnable tasks at the start', 'Seconds since the end of the folder before', 'Steps of the visit before',` | The first eight column headings: session, folder, steps of the visit, start time, load average at the start, runnable tasks at the start, seconds after the end of the folder before, and steps of the visit before. |
| 1206 | `         'End (UTC)', '1-minute load at the end (tasks)'], env, 'sm')))` | The other two headings: the end time and the load average at the end. |
| 1207 | `    o.append(f'<p class="miss"><b>{ID}.</b> The load while an interval ran. The script reads the load only before a launch. A reading of the runnable tasks of each account during an interval would give it.</p>')` | Adds the `Insufficient data` box on the load while an interval ran: the script reads the load only before a launch. |
| 1208 | `    return '\n'.join(o)` | Returns the section as one text. |

### `sec_integrity`: processes used, irregular intervals and page state (lines 1211 to 1237)

| Line | Source | Explanation |
|---:|---|---|
| 1211 | `def sec_integrity(m, R):` | Starts the function `sec_integrity`. It builds the section on the processes used, the irregular intervals and the page state. |
| 1212 | `    o = ['<h2 id="used">Processes used, irregular intervals and page state</h2>']` | `o`: the list of the HTML pieces. It starts with the heading of level 2, which has the anchor name `used`. |
| 1213 | `    rows, irr, left = [], [], []` | Three empty lists: the rows of the count table, the irregular intervals, and the processes left out. |
| 1214 | `    for s in m['sessions']:` | Loop over the sessions. |
| 1215 | `        d = m['S'][s]` | `d`: the model of the session. |
| 1216 | `        for st in d['steps']:` | Loop over the steps of Q2 that have a result. |
| 1217 | `            g, pg, sk = d['integ'][st], d['page'][st], d['skew'][st]` | `g`: the result of the analysis for the step. `pg`: the P row counts (lines 715 to 716). `sk`: the three skew values (lines 718 to 720). |
| 1218 | `            rows.append((e(s), st, g['n_processes'], g['n_used'], len(g['irregular_intervals']), sk[2], f(sk[0], 3), f(sk[1], 1), pg['rows'], pg['na'], pg['not_full'], R((s, st))))` | Adds the row of the step: session, step, processes in the files, processes used, number of irregular intervals, late thread starts, largest end skew with the common stop (3 decimals) and with whole passes (1 decimal), P rows, P rows without a value, P rows with less than full coverage, and the citation. |
| 1219 | `            irr += [(e(s), st, e(x['tag']), x['round'], x['pos'], e(KN.get(x['entry'], x['entry'])), x['late_threads'], f(x['end_skew_ms'], 3)) for x in g['irregular_intervals']]` | Adds one entry per irregular interval of the step: session, step, tag of the process, round, position, printed kernel name, number of late threads, and end skew in ms. |
| 1220 | `            left += [(e(s), st, e(x['tag']), e(x['reason'].replace(';', ','))) for x in g['left_out']]` | Adds one entry per process that the analysis left out: session, step, tag and reason. Each semicolon of the reason is replaced by a comma. |
| 1221 | `    if not rows:` | Tests whether there is no row. |
| 1222 | `        return '\n'.join(o) + missing('No process of the steps B7, B10, B8, B5, B9 or C3 is in the input.')` | Then the function returns the heading and the `Insufficient data` box: no process of the six steps is in the input. |
| 1223 | `    sk0 = [float(r[6]) for r in rows if r[6] != '-']; sk1 = [float(r[7]) for r in rows if r[7] != '-']` | `sk0` and `sk1`: the largest end skews of the steps with the common stop and with whole passes, read back from the printed rows as numbers. |
| 1224 | `    o.append(f'<p>{sum(r[3] for r in rows)} of {sum(r[2] for r in rows)} processes of these steps were used. {pl(len(irr), "interval is", "intervals are")} irregular, and {pl(sum(r[5] for r in rows), "thread start is", "thread starts are")} late. '` | Adds a paragraph. First sentence: how many of the processes of these steps were used, summed over the rows. Second sentence: the number of irregular intervals and the number of late thread starts. |
| 1225 | `             + (f'The largest end skew with the common stop is {fx(max(sk0), 3)} ms (limit 5 ms). ' if sk0 else '') + (f'With whole passes it is {fx(max(sk1), 1)} ms, which is not a reason to leave an interval out {R("devs")}. ' if sk1 else '')` | Continues the paragraph: the largest end skew with the common stop in ms, with the limit of 5 ms. Then the largest end skew with whole passes, with the remark that it is not a reason to leave an interval out. |
| 1226 | `             + f'{sum(r[8] for r in rows)} page-state rows (P rows) were read: {sum(r[9] for r in rows)} without a value, and {sum(r[10] for r in rows)} with less than full coverage by 2 MiB pages.</p>')` | Continues the paragraph: the number of P rows that were read, how many have no value, and how many show less than full coverage by 2 MiB pages. |
| 1227 | `    o.append(f'<p>An interval is irregular if a thread started late or if the end skew with the common stop is above 5 ms {R("handoff")}. An irregular interval is not used, and its process then gives no value for the quantity that needs it. '` | Adds a paragraph with typed text: an interval is irregular if a thread started late or if the end skew with the common stop is above 5 ms. An irregular interval is not used, and its process then gives no value for the quantity that needs it. |
| 1228 | `             f'In a process with more than one thread, the page-state reading that belongs to an interval is the reading taken after the interval before it. The warm-up pass lies between that reading and the timed part {R("handoff")}.</p>')` | Continues the paragraph: in a process with more than one thread, the page state that belongs to an interval is the reading taken after the interval before it. The warm-up pass lies between that reading and the timed part. |
| 1229 | `    o.append('<h3>Irregular intervals</h3>' + (table(['Session', 'Step', 'Process', 'Round', 'Position', 'Kernel', 'Late threads', 'End skew (ms)'], irr) if irr else f'<p>No interval of these steps is irregular ({sum(r[2] for r in rows)} processes).</p>'))` | Adds a heading of level 3 for the irregular intervals, and then their table with eight columns. Without an irregular interval a sentence says so and gives the number of processes. |
| 1230 | `    if left:` | The next line runs only when a process was left out. |
| 1231 | `        o.append('<h3>Processes left out</h3>' + table(['Session', 'Step', 'Process', 'Reason'], left, 'pt'))` | Adds a heading of level 3 and the table of the processes left out: session, step, process and reason. |
| 1232 | `    o.append(details('Counts per session and step', table(` | Adds a folded block with the count table per session and step. |
| 1233 | `        ['Session', 'Step', 'Processes in the files', 'Processes used', 'Irregular intervals', 'Late thread starts', 'Largest end skew with the common stop (ms)', 'Largest end skew with whole passes (ms)',` | The first eight column headings: session, step, processes in the files, processes used, irregular intervals, late thread starts, and the largest end skew in ms with the common stop and with whole passes. |
| 1234 | `         'P rows', 'P rows without a value', 'P rows with less than full coverage', 'Source'], rows, 'sm')))` | The other four headings: P rows, P rows without a value, P rows with less than full coverage, and the source. |
| 1235 | `    return '\n'.join(o)` | Returns the section as one text. |

### `b7_block`: D per setting, and the reproduction condition (lines 1238 to 1298)

| Line | Source | Explanation |
|---:|---|---|
| 1238 | `def b7_block(R):` | Starts the function `b7_block`. It returns the function `fn`, which draws the B7 block of one session. `R` is the object with the references. |
| 1239 | `    def fn(m, s, b):` | Starts the inner function `fn`. `m` is the model, `s` the session name, and `b` the model of B7 for that session. |
| 1240 | `        res = b['res']; S = sorted(res['settings'], key=skey); ref = R((s, 'B7'))` | `res`: the result of the analysis for B7. `S`: its settings in the order of `skey`. `ref`: the citation of the B7 folders of the session. |
| 1241 | `        o = []` | `o`: the list of the HTML pieces of the block, empty at first. |
| 1242 | `        allD = [x for v in res['settings'].values() for mm in ('M_hist', 'M_sum') for x in v['metrics'][mm]['D']]` | `allD`: the D of every process in every setting, with `M_hist` and with `M_sum`. The list sets the range of the x axis of the first chart. For one process D is the mean over its rounds of the mean total of its old read intervals minus the mean total of its new read intervals. |
| 1243 | `        sk = res['single_kernel']` | `sk`: the result of the analysis for B7 with one kernel per process. There the process value is the median total of the intervals of a process. D is the median of the process values of old read minus the median of those of new read. The A/A value is the absolute difference between the medians of `asmread2` and of `asmread`. |
| 1244 | `        if sk.get('D') is not None:` | The next line runs only when that result has a D. |
| 1245 | `            allD += [sk['D'], sk['metrics']['M_sum']['D']]` | Adds its D with `M_hist` and its D with `M_sum` to `allD`. |
| 1246 | `        if not allD:` | Tests whether there is no D at all. |
| 1247 | `            return missing('No setting of B7 has a process with a value of D.')` | Then the block is the `Insufficient data` box: no setting of B7 has a process with a value of D. |
| 1248 | `        lo, hi = min(allD + [0.0]), max(allD + [0.0])` | `lo` and `hi`: the lowest and the highest D. The value 0 is added first, so the axis always holds 0. |
| 1249 | `        pad = (hi - lo) * 0.06` | `pad`: 6 % of the range, as space at the ends of the axis. |
| 1250 | `        rows = []` | `rows`: the rows of the first chart, empty at first. |
| 1251 | `        for st in S:` | Loop over the settings. |
| 1252 | `            v = res['settings'][st]; h, ms = v['metrics']['M_hist'], v['metrics']['M_sum']` | `v`: the result of the setting. `h` and `ms`: its values with `M_hist` and with `M_sum`. |
| 1253 | `            pts = [dict(v=x, c=C0, t=f'M_hist: D = {fx(x)} GB/s', dy=-4) for x in h['D']] + [dict(v=x, c=C0, shape='ring', t=f'M_sum: D = {fx(x)} GB/s', dy=5) for x in ms['D']]` | `pts`: the markers of the row. Each process gives a filled circle for its D with `M_hist`, drawn 4 units above the middle of the row, and a ring for its D with `M_sum`, drawn 5 units below it. The tooltip gives the metric and the D in GB/s. |
| 1254 | `            right = f"D {f(h['median_D'], 1)}, A/A {f(h['aa_spread'], 1)} GB/s: {v['decision']}{A.sign_txt(v['sign'])}" if h['median_D'] is not None else v['decision']` | `right`: the text at the right of the row: the median D and the A/A spread with 1 decimal, and the decision with its sign. `A.sign_txt` prints `(+)` for a positive D and `(-)` for a negative one. Without a median D the text is the decision alone. |
| 1255 | `            rows.append(dict(name=sname(st) + (' *' if st == REPRO else ''), pts=pts, right=right, bar=(0, h['aa_spread']) if h['aa_spread'] else None, bar_t='A/A spread'))` | Adds the row. Its name is the setting in words, with a star for the reproduction condition. A grey bar runs from 0 to the A/A spread. |
| 1256 | `        if sk.get('D') is not None:` | The next four lines run only when B7 with one kernel per process has a D. |
| 1257 | `            rows.append(dict(name='* with one kernel per process', pts=[dict(v=sk['D'], c=C0, shape='diamond', t=f"M_hist: D = {fx(sk['D'])} GB/s", dy=-4),` | Adds a last row for it, marked with a star: a diamond for its D with `M_hist` and a ring for its D with `M_sum`. |
| 1258 | `                                                                      dict(v=sk['metrics']['M_sum']['D'], c=C0, shape='ring', t='M_sum', dy=5)],` | Continues the row: the ring. |
| 1259 | `                             right=f"D {f(sk['D'], 1)}, A/A {f(sk['aa_value'], 1)} GB/s: {sk['decision']}{A.sign_txt(sk.get('sign'))}", bar=(0, sk['aa_value']), bar_t='A/A value'))` | Continues the row: the text at the right with D, the A/A value and the decision, and a grey bar from 0 to the A/A value. |
| 1260 | `        nres = sum(1 for st in S if res['settings'][st]['decision'] == 'resolved' and res['settings'][st]['sign'] == 1)` | `nres`: the number of settings in which D is resolved with a positive sign, so with old read above new read. |
| 1261 | `        meds = [res['settings'][st]['metrics']['M_hist']['median_D'] for st in S if res['settings'][st]['metrics']['M_hist']['median_D'] is not None]` | `meds`: the median D with `M_hist` of each setting that has one. |
| 1262 | `        aas = [res['settings'][st]['metrics']['M_hist']['aa_spread'] for st in S if res['settings'][st]['metrics']['M_hist']['aa_spread'] is not None]` | `aas`: the A/A spread with `M_hist` of each setting that has one. |
| 1263 | `        ratio = [md / aa for md, aa in zip(meds, aas) if aa]` | `ratio`: the median D divided by the A/A spread, per setting. A setting with an A/A spread of 0 is left out. |
| 1264 | `        note = f'D is resolved with old read above new read in {nres} of {len(S)} settings.' + (f' Median D is {fx(min(ratio), 0)} to {fx(max(ratio), 0)} times the A/A spread.' if ratio and min(ratio) > 0 else '')` | `note`: the note above the chart: in how many of the settings D is resolved with old read above new read. When every ratio is above 0, it adds the lowest and the highest ratio as a multiple of the A/A spread, without decimals. |
| 1265 | `        o.append(rowchart(rows, lo - pad if lo < 0 else 0, hi + pad, 'D = total of old read minus total of new read (GB/s)', f'B7 session {s}: D per process and setting', note=note))` | Adds the first chart: D per process and setting, with the x axis in GB/s. The axis starts at 0 unless a D is negative. |
| 1266 | `        o.append(legend([(C0, 'D of one process with M_hist (decision metric)', ''), ('#fff', 'D of one process with M_sum', f'border:1.5px solid {C0}'), ('#d9d7cf', 'A/A spread, drawn from 0', 'border-radius:0')]))` | Adds the legend: a filled dot for the D of one process with `M_hist` (the decision metric), a ring for the D with `M_sum`, and a grey square for the A/A spread, drawn from 0. |
| 1267 | `        o.append(f'<p class="cap">One row per setting. * marks the reproduction condition, the timing method of the run of 2026-11-13. The last row runs one kernel per process. Its marker is the difference of two medians, not a process. '` | Adds a caption. This line: one row per setting, the star marks the reproduction condition, which the text calls the timing method of the run of 2026-11-13, and the last row runs one kernel per process, so its marker is the difference of two medians and not a process. |
| 1268 | `                 f'Median D is {rng(meds)} GB/s over the settings, and the A/A spread is {rng(aas)} GB/s. Data: {ref}.</p>')` | Continues the caption: the range of the median D over the settings and the range of the A/A spread, both in GB/s, and the citation of the data. |
| 1269 | `        trs, trs2 = [], []` | `trs` and `trs2`: the rows of the table with `M_hist` and of the table with `M_sum`. |
| 1270 | `        for st in S:` | Loop over the settings. |
| 1271 | `            v = res['settings'][st]; h, ms = v['metrics']['M_hist'], v['metrics']['M_sum']` | `v`, `h` and `ms`: the result of the setting and its values with the two metrics. |
| 1272 | `            f2 = b['fail2'].get(st)` | `f2`: the three values of the 2 % check for this setting (line 261), or `None` for a setting with the common stop. |
| 1273 | `            trs.append((sname(st) + (' *' if st == REPRO else ''), f"{v['decision']}{A.sign_txt(v['sign'])}", f(h['median_D']), f(h['aa_spread']), h['n_processes'], ', '.join(fx(x, 1) for x in h['D']),` | Adds the row of the first table: the setting, the decision with its sign, the median D, the A/A spread, the number of processes with a value, and the D of each process with 1 decimal. |
| 1274 | `                        ('does not apply' if f2 is None else f'{f2[0]} of {f2[1]}')))` | Continues the row: the number of intervals that fail the 2 % check, out of all intervals of the setting, or `does not apply`. |
| 1275 | `            trs2.append((sname(st) + (' *' if st == REPRO else ''), f(ms['median_D']), f(ms['aa_spread'])))` | Adds the row of the second table: the setting, the median D and the A/A spread with `M_sum`. |
| 1276 | `        if sk.get('D') is not None:` | The next five lines run only when B7 with one kernel per process has a D. |
| 1277 | `            n = sk['n_processes']; f2 = b.get('fail2_single')` | `n`: its number of processes per kernel. `f2`: its values of the 2 % check (line 265). |
| 1278 | `            trs.append(('* with one kernel per process', f"{sk['decision']}{A.sign_txt(sk.get('sign'))}", f(sk['D']), f(sk['aa_value']), '/'.join(str(x) for x in n.values()),` | Adds its row to the first table: the decision, D, the A/A value, and the four process counts with slashes between them. |
| 1279 | `                        'old read ' + ', '.join(fx(x, 1) for x in sk['process_values']['oldread']) + '<br>new read ' + ', '.join(fx(x, 1) for x in sk['process_values']['read']),` | Continues the row: the process values of old read and of new read with 1 decimal, on two lines of the cell. |
| 1280 | `                        ('-' if not f2 else f'{f2[0]} of {f2[1]}')))` | Continues the row: the number of intervals that fail the 2 % check, or `-`. |
| 1281 | `            trs2.append(('* with one kernel per process', f(sk['metrics']['M_sum']['D']), f(sk['metrics']['M_sum']['aa_value'])))` | Adds its row to the second table: D and the A/A value with `M_sum`. |
| 1282 | `        o.append(table(['Setting', 'Decision', 'Median D, M_hist (GB/s)', 'A/A spread, M_hist (GB/s)', 'Processes with a value', 'D of each process, M_hist (GB/s)', 'Intervals that fail the 2 % check'], trs, 'wr'))` | Adds the first table. Its seven columns: setting, decision, median D with `M_hist`, A/A spread with `M_hist`, processes with a value, the D of each process, and the intervals that fail the 2 % check. |
| 1283 | `        o.append(details('The same with M_sum', table(['Setting', 'Median D, M_sum (GB/s)', 'A/A spread, M_sum (GB/s)'], trs2)))` | Adds a folded block with the second table: the same with `M_sum`. |
| 1284 | `        # reproduction` | Comment: the next lines write the paragraph on the reproduction condition. |
| 1285 | `        rp = res['settings'].get(REPRO)` | `rp`: the result of the setting `pass/500/common`, or `None`. |
| 1286 | `        t = '<p><b>Reproduction condition.</b> '` | `t`: the paragraph. It starts with the bold words `Reproduction condition.` |
| 1287 | `        if rp:` | The next two lines run only when that setting has a result. |
| 1288 | `            h = rp['metrics']['M_hist']` | `h`: its values with `M_hist`. |
| 1289 | `            t += f"With the kernels alternating in one process: D is {rp['decision']}{A.sign_txt(rp['sign'])}, median {f(h['median_D'])} GB/s over {h['n_processes']} processes, A/A spread {f(h['aa_spread'])} GB/s. "` | Adds a sentence for the kernels that alternate in one process: the decision for D with its sign, the median D, the number of processes and the A/A spread. |
| 1290 | `        else:` | In the other case the next line applies. |
| 1291 | `            t += f'{ID}: no process ran the setting "{sname(REPRO)}" with all kernels. '` | Adds a sentence that starts with `Insufficient data`: no process ran this setting with all kernels. |
| 1292 | `        if sk.get('D') is not None:` | The next line runs only when B7 with one kernel per process has a D. |
| 1293 | `            t += f"With one kernel per process: D is {sk['decision']}{A.sign_txt(sk.get('sign'))}, {f(sk['D'])} GB/s, A/A value {f(sk['aa_value'])} GB/s. "` | Adds a sentence for one kernel per process: the decision with its sign, D and the A/A value. |
| 1294 | `        else:` | In the other case the next line applies. |
| 1295 | `            t += f"With one kernel per process: {e(sk.get('note', 'no value'))}. "` | Adds a sentence with the note of the analysis for that case, or the words `no value`. |
| 1296 | `        t += ('So the difference of 2026-11-13 is reproduced in the changed benchmark' if res.get('reproduced_in_either_way') else` | Adds the conclusion. When the analysis found a resolved D with old read above new read in one of the two ways of running, it says that the difference of 2026-11-13 is reproduced in the changed benchmark. |
| 1297 | `              'So Q2a is not reproduced in the changed benchmark, and the plan assigns no cause in that case') + f' {ref}{R("plan")}.</p>'` | Continues the statement: in the other case it says that Q2a is not reproduced in the changed benchmark and that the plan assigns no cause then. The sentence ends with the citations of the data and of the plan. |
| 1298 | `        o.append(t)` | Adds the paragraph. |

### `b7_block`: change of D per factor, rates per mesh, and the thread chart (lines 1299 to 1368)

| Line | Source | Explanation |
|---:|---|---|
| 1299 | `        # change per factor` | Comment: the next lines show the change of D for each timing factor. |
| 1300 | `        ch = sorted(res['changes'].values(), key=lambda c: (('stop', 'interval', 'start').index(c['factor']), skey(c['first'])))` | `ch`: the comparisons of two settings, sorted by factor (stop method, interval, start) and then by the first setting. |
| 1301 | `        if ch:` | The lines up to line 1328 run only when there is a comparison. |
| 1302 | `            vals = [abs(c['metrics']['M_hist']['change'] or 0) for c in ch] + [c['metrics']['M_hist']['sum_of_aa_spreads'] or 0 for c in ch]` | `vals`: the absolute change and the limit of every comparison, with 0 for a missing value. |
| 1303 | `            lim = max(vals) * 1.12 or 1` | `lim`: the largest of them plus 12 %, or 1 when all are 0. The x axis of the chart runs from `-lim` to `lim`. |
| 1304 | `            rows, last = [], None` | `rows`: the rows of the chart. `last`: the factor of the row before. |
| 1305 | `            FN = dict(stop='Stop method: whole passes minus common stop', interval='Interval: short minus long', start='Start: common minus offset')` | `FN`: the heading of each factor. It says which setting is the first one: whole passes minus common stop, short interval minus long, common start minus offset start. |
| 1306 | `            for c in ch:` | Loop over the comparisons. |
| 1307 | `                if c['factor'] != last:` | Tests whether a new factor starts. |
| 1308 | `                    rows.append(dict(head=FN[c['factor']])); last = c['factor']` | Then a heading row with the text of the factor is added. |
| 1309 | `                h = c['metrics']['M_hist']` | `h`: the values of the comparison with `M_hist`. |
| 1310 | `                fixed = [x for i, x in enumerate(sname(c['first']).split(', ')) if i != ('stop', 'interval', 'start').index(c['factor'])]` | `fixed`: the two parts of the setting name that are equal in both settings. The part of the compared factor is left out. |
| 1311 | `                if h['change'] is None:` | Tests whether the comparison has no value. |
| 1312 | `                    rows.append(dict(name=', '.join(fixed), pts=[], right='not observed')); continue` | Then the row has no marker and the text `not observed`, and the loop goes on. |
| 1313 | `                rows.append(dict(name=', '.join(fixed), pts=[dict(v=h['change'], c=C0, t=f"change of median D: {fs(h['change'])} GB/s")], bar=(-h['sum_of_aa_spreads'], h['sum_of_aa_spreads']), bar_t='sum of the two A/A spreads',` | Adds the row: its name is the two fixed parts. One dot shows the change of the median D. A grey bar runs from minus the limit to plus the limit, the sum of the two A/A spreads. |
| 1314 | `                                 right=f"{fs(h['change'], 1)}, band {f(h['sum_of_aa_spreads'], 1)} GB/s: {c['decision']}"))` | Continues the row: the text at the right with the signed change, the limit (called band) and the decision. |
| 1315 | `            nr = sum(1 for c in ch if c['decision'] == 'resolved')` | `nr`: the number of resolved comparisons. |
| 1316 | `            outside = sum(1 for c in ch if c['metrics']['M_hist']['change'] is not None and abs(c['metrics']['M_hist']['change']) > c['metrics']['M_hist']['sum_of_aa_spreads'])` | `outside`: the number of comparisons whose absolute change is above the limit, so whose dot lies outside the grey band. |
| 1317 | `            note = f"{nr} of {len(ch)} changes of D are resolved. {pl(outside, 'dot lies', 'dots lie')} outside the grey band of its row."` | `note`: the note above the chart: how many changes of D are resolved, and how many dots lie outside the grey band of their row. |
| 1318 | `            o.append('<h4>Change of D per factor</h4>' + rowchart(rows, -lim, lim, 'change of median D between two settings that differ in one factor (GB/s)', f'B7 session {s}: change of D per factor', note=note, vlines=[(0, '')]))` | Adds a heading of level 4 and the chart of the change of D per factor, with a dashed line at 0. |
| 1319 | `            o.append(f'<p class="cap">The grey band is the limit: the sum of the A/A spreads of the two settings, drawn to both sides of 0. A change is resolved only if the dot lies outside the band and every D of one setting lies on one side of every D of the other {R("handoff")}. Data: {ref}.</p>')` | Adds a caption: the grey band is the limit, drawn to both sides of 0. A change is resolved only if the dot lies outside the band and every D of one setting lies on one side of every D of the other. It cites the handoff and the data. |
| 1320 | `            big = max(ch, key=lambda c: abs(c['metrics']['M_hist']['change'] or 0))` | `big`: the comparison with the largest absolute change. |
| 1321 | `            FW = dict(stop='the stop method', interval='the interval', start='the start')` | `FW`: the words for each factor in a sentence. |
| 1322 | `            fixed = [x for i, x in enumerate(sname(big['first']).split(', ')) if i != ('stop', 'interval', 'start').index(big['factor'])]` | `fixed`: the two fixed parts of the setting name of that comparison. |
| 1323 | `            o.append(f"<p class=\"take\">The largest change is {fs(big['metrics']['M_hist']['change'])} GB/s ({fx(abs(big['metrics']['M_hist']['change']) / max(abs(med(meds)), 1e-9) * 100, 1)} % of the median D of this session). "` | Adds a highlighted paragraph: the largest change in GB/s with its sign, and its size in % of the median D of the session. The median D of the session is the median of the values of `meds`. |
| 1324 | `                     f"It is the change of {FW[big['factor']]}, with {' and '.join(fixed)}. It is {big['decision']}.</p>")` | Continues the paragraph: which factor changed, with which fixed parts, and the decision for it. |
| 1325 | `            o.append(details(f'Exact numbers of the {len(ch)} comparisons', table(` | Adds a folded block with the exact numbers of all comparisons. |
| 1326 | `                ['Factor', 'First setting', 'Second setting', 'Change of median D, M_hist (GB/s)', 'Sum of the two A/A spreads, M_hist (GB/s)', 'Change, M_sum (GB/s)', 'Sum of A/A spreads, M_sum (GB/s)', 'Decision'],` | The eight column headings: factor, first setting, second setting, change of the median D and sum of the two A/A spreads with `M_hist`, the same two with `M_sum`, and the decision. |
| 1327 | `                [(c['factor'], sname(c['first']), sname(c['second']), ('-' if c['metrics']['M_hist']['change'] is None else fs(c['metrics']['M_hist']['change'])), f(c['metrics']['M_hist']['sum_of_aa_spreads']),` | The rows: one per comparison, with the signed change or `-` and the limit with `M_hist`. |
| 1328 | `                  ('-' if c['metrics']['M_sum']['change'] is None else fs(c['metrics']['M_sum']['change'])), f(c['metrics']['M_sum']['sum_of_aa_spreads']), c['decision']) for c in ch], 'sm')))` | Continues the rows: the same two values with `M_sum`, and the decision. |
| 1329 | `        # per mesh` | Comment: the next lines show the rates per mesh. |
| 1330 | `        o.append('<h4>Rates per mesh</h4>')` | Adds a heading of level 4 for the rates per mesh. |
| 1331 | `        rows, trs, vmax = [], [], 0` | Three start values: the rows of the chart, the rows of the table, and the largest value for the axis. |
| 1332 | `        for st in S:` | Loop over the settings. |
| 1333 | `            rows.append(dict(head=sname(st)))` | Adds a heading row with the setting in words. |
| 1334 | `            for k in ('oldread', 'read', 'asmread'):` | Loop over three kernels: old read, new read and asm read. |
| 1335 | `                a = b['kern'][st].get(k)` | `a`: the medians of this kernel in this setting (line 258). |
| 1336 | `                if not a:` | Tests whether the kernel has no regular interval there. |
| 1337 | `                    continue` | Such a kernel gets no row. |
| 1338 | `                vmax = max(vmax, a['m0'], a['m1'])` | Keeps the largest median thread rate so far in `vmax`. |
| 1339 | `                l0, l1 = ('l', 'r') if a['m0'] <= a['m1'] else ('r', 'l')` | `l0` and `l1`: the sides of the two labels. The lower of the two values gets its label at the left, the higher one at the right. |
| 1340 | `                rows.append(dict(name=KN[k], seg=(a['m0'], a['m1']), pts=[dict(v=a['m0'], c=C0, lab=fx(a['m0']), side=l0, op=1, t='mesh 0'), dict(v=a['m1'], c=C1, shape='diamond', lab=fx(a['m1']), side=l1, op=1, t='mesh 1')],` | Adds the row of the kernel: a line joins two markers. A circle in the color `C0` shows the median thread rate of mesh 0 and a diamond in the color `C1` that of mesh 1. Each has its value as a label. The values are the medians over the intervals of the median thread rate of the mesh. |
| 1341 | `                                 right=f"mesh 0 minus mesh 1: {fs(a['m0'] - a['m1'])} GB/s"))` | Continues the row: the text at the right with the difference, mesh 0 minus mesh 1, in GB/s with a sign. |
| 1342 | `                trs.append((sname(st), KN[k], a['n'], f(a['hist']), f(a['mh0']), f(a['mh1']), f(a['m0']), f(a['m1']), f'{f(a["q_min"], 3)} to {f(a["q_max"], 3)}'))` | Adds the table row: the setting, the kernel, the number of intervals, the median total, the median `M_hist` value of mesh 0 and of mesh 1, the median thread rate of mesh 0 and of mesh 1, and the lowest and the highest q with 3 decimals. |
| 1343 | `        ko, kr = [b['kern'][st]['oldread'] for st in S if b['kern'][st].get('oldread')], [b['kern'][st]['read'] for st in S if b['kern'][st].get('read')]` | `ko` and `kr`: the medians of old read and of new read in every setting that has them. |
| 1344 | `        note = ''` | `note`: the note above the chart, empty at first. |
| 1345 | `        if ko and kr:` | The next two lines run only when both kernels have values. |
| 1346 | `            note = (f"Median thread of old read: {rng([a['m0'] for a in ko])} GB/s on mesh 0 and {rng([a['m1'] for a in ko])} GB/s on mesh 1. "` | The note gets the range over the settings of the median thread rate of old read on mesh 0 and on mesh 1. |
| 1347 | `                    f"New read: {rng([a['m0'] for a in kr])} and {rng([a['m1'] for a in kr])} GB/s.")` | Continues the note: the same two ranges for new read. |
| 1348 | `        o.append(rowchart(rows, 0, vmax * 1.1, 'median thread rate (GB/s), median over the intervals of the setting', f'B7 session {s}: median thread rate per mesh', L=150, R=230, rh=22, note=note))` | Adds the chart of the median thread rate per mesh. Its x axis starts at 0 and ends 10 % above the largest value. |
| 1349 | `        o.append(legend([(C0, 'mesh 0 (CPUs 0 to 63)', ''), (C1, 'mesh 1 (CPUs 64 to 119)', 'border-radius:0;transform:rotate(45deg)')]))` | Adds the legend: a dot for mesh 0 (CPUs 0 to 63) and a square turned by 45 degrees for mesh 1 (CPUs 64 to 119). |
| 1350 | `        if ko and kr:` | The next two lines run only when both kernels have values. |
| 1351 | `            d0 = med([a['m0'] for a in ko]) - med([a['m0'] for a in kr]); d1 = med([a['m1'] for a in ko]) - med([a['m1'] for a in kr])` | `d0` and `d1`: for mesh 0 and for mesh 1, the median over the settings of the value of old read minus the median over the settings of the value of new read. |
| 1352 | `            o.append(f"<p class=\"take\">Old read minus new read, median thread over the settings: {fs(d0)} GB/s on mesh 0 and {fs(d1)} GB/s on mesh 1. This is a description. Data: {ref}.</p>")` | Adds a highlighted paragraph with these two differences in GB/s. It says that this is a description, and it cites the data. |
| 1353 | `        o.append(details('Exact numbers per setting, kernel and mesh', table(` | Adds a folded block with the exact numbers per setting, kernel and mesh. |
| 1354 | `            ['Setting', 'Kernel', 'Intervals', 'Total, M_hist (GB/s)', 'Mesh 0, M_hist (GB/s)', 'Mesh 1, M_hist (GB/s)', 'Median thread, mesh 0 (GB/s)', 'Median thread, mesh 1 (GB/s)', 'q, lowest to highest'], trs, 'sm')` | The nine column headings of that table, in the order of the values of line 1342. |
| 1355 | `            + '<p class="cap">Every rate is the median over the intervals of the kernel in the setting. The value of a mesh uses the longest time of all threads as divisor.</p>'))` | Adds a caption below the table: every rate is the median over the intervals of the kernel in the setting, and the value of a mesh uses the longest time of all threads as divisor. |
| 1356 | `        # per-thread chart` | Comment: the next lines draw the chart with one marker per thread. |
| 1357 | `        rep = b['rep']` | `rep`: the example pair of intervals (line 290), or `None`. |
| 1358 | `        if rep:` | The lines up to line 1364 run only when there is a pair. |
| 1359 | `            o.append('<h4>Thread rate against CPU number, one interval of each kernel</h4>' + cpu_scatter(rep, f'B7 session {s}: thread rate against CPU number'))` | Adds a heading of level 4 and the chart of thread rate against CPU number. |
| 1360 | `            o.append(legend([(C0, 'old read', ''), (C1, 'new read', 'border-radius:0;transform:rotate(45deg)')]))` | Adds the legend: a dot for old read and a square turned by 45 degrees for new read. |
| 1361 | `            why = dict(used='the setting in which B8, B5 and B9 of this session ran', chosen='the setting that the handoff rule selects for the later steps', fallback='the first setting with data')[rep['why']]` | `why`: the words for the reason of the choice: the setting in which B8, B5 and B9 of this session ran, the setting that the handoff rule selects, or the first setting with data. |
| 1362 | `            o.append(f"<p class=\"cap\">The pair shown: process <code>{e(rep['tag'])}</code> (setting \"{sname(rep['setting'])}\"), its first old read interval (round {rep['old_s']['round']}, position {rep['old_s']['pos']}) "` | Adds a caption. This line: the tag of the process, its setting, and the round and position of its first old read interval. |
| 1363 | `                     f"and its first new read interval (round {rep['new_s']['round']}, position {rep['new_s']['pos']}). The rule for the choice: the first process in the file of {why}. "` | Continues the caption: the round and position of its first new read interval, and the rule for the choice: the first process in the file of the setting named by `why`. |
| 1364 | `                     f"In this pair q is {f(rep['old_s']['q'], 3)} for old read and {f(rep['new_s']['q'], 3)} for new read, and the totals are {f(rep['old_s']['hist'])} and {f(rep['new_s']['hist'])} GB/s. Data: {ref}.</p>")` | Continues the caption: q of old read and of new read in this pair with 3 decimals, the two totals in GB/s, and the citation of the data. |
| 1365 | `        return '\n'.join(o)` | Returns the block as one text. |
| 1366 | `    return fn` | Returns the function `fn`. |

### `b10_block`: totals of every interval, the description for Q2b, and the spread (lines 1369 to 1422)

| Line | Source | Explanation |
|---:|---|---|
| 1369 | `def b10_block(R):` | Starts the function `b10_block`. It returns the function `fn`, which draws the B10 block of one session. |
| 1370 | `    def fn(m, s, b):` | Starts the inner function `fn`. `b` is the model of B10 for the session `s`. |
| 1371 | `        res = b['res']; ref = R((s, 'B10')); S = list(b['settings'])` | `res`: the result of the analysis for B10. `ref`: the citation of the B10 folders. `S`: the settings in the order of the model. |
| 1372 | `        allv = [t[0] for st in S for k in b['settings'][st].values() for t in k['totals']]` | `allv`: the totals `M_hist` of all regular intervals of all kernels and settings. |
| 1373 | `        if not allv:` | Tests whether there is no such interval. |
| 1374 | `            return missing('No regular interval of B10.')` | Then the block is the `Insufficient data` box: no regular interval of B10. |
| 1375 | `        lo, hi = min(allv), max(allv); pad = (hi - lo) * 0.05 or 1` | `lo` and `hi`: the lowest and the highest total. `pad`: 5 % of the range, or 1 when the range is 0. |
| 1376 | `        rows = []` | `rows`: the rows of the first chart, empty at first. |
| 1377 | `        for st in S:` | Loop over the settings. |
| 1378 | `            rows.append(dict(head=sname(st)))` | Adds a heading row with the setting in words. |
| 1379 | `            for k, v in b['settings'][st].items():` | Loop over the kernels of the setting with their values `v`. |
| 1380 | `                pts = [dict(v=t[0], c=C0, r=3.5, op=0.6, dy=((j * 7) % 5 - 2) * 2.0, t=f'{t[1]} round {t[2]} position {t[3]}: {fx(t[0])} GB/s, {fx(t[4], 1)} passes of all threads') for j, t in enumerate(v['totals'])]` | `pts`: one dot per regular interval at its total. The dots are shifted up or down by 0, 2 or 4 units in a fixed order. Equal totals then stay visible. The tooltip gives the tag, the round, the position, the total in GB/s and the passes of all threads together. |
| 1381 | `                rows.append(dict(name=KN[k], pts=pts, right=(f"{f(v['lo'], 1)} to {f(v['hi'], 1)}, gap {f(v['gap'], 1)} GB/s" if v['totals'] else '-')))` | Adds the row of the kernel. The text at the right gives the lowest and the highest total and the largest gap between two neighbouring totals, with 1 decimal. |
| 1382 | `        gaps = [(v['gap'], st, k) for st in S for k, v in b['settings'][st].items() if v['gap'] is not None]` | `gaps`: the largest gap of every kernel in every setting, with the setting and the kernel. |
| 1383 | `        g = max(gaps)` | `g`: the entry with the largest gap of all. |
| 1384 | `        note = f"Largest gap between two neighbouring totals of one row: {f(g[0], 1)} GB/s ({KN[g[2]]}, {sname(g[1])})."` | `note`: the note above the chart: the largest gap between two neighbouring totals of one row, with its kernel and setting. |
| 1385 | `        o = [rowchart(rows, lo - pad, hi + pad, 'total of one interval, M_hist (GB/s). The axis does not start at 0.', f'B10 session {s}: totals of every interval', L=120, R=230, rh=20, note=note)]` | `o`: the list of the HTML pieces. It starts with the chart of the totals of every interval. The title of its x axis says that the axis does not start at 0. |
| 1386 | `        o.append(f'<p class="cap">One dot per interval, {len(allv)} intervals. Dots are moved a little up or down so that equal totals stay visible. The right column gives the lowest and the highest total of the row, and the largest gap between two neighbouring totals of the row. Data: {ref}.</p>')` | Adds a caption: one dot per interval and the number of intervals. It explains the small shifts of the dots and the text at the right of each row, and cites the data. |
| 1387 | `        # Q2b: description per setting. The plan sets no rule for "separate levels".` | Comment: the next lines describe question Q2b per setting. The plan sets no rule for when totals are separate levels. |
| 1388 | `        trs, over = [], 0` | `trs`: the rows of the table. `over`: a count of settings, 0 at first. |
| 1389 | `        for st in S:` | Loop over the settings. |
| 1390 | `            v = res['settings'][st]; ks = b['settings'][st]` | `v`: the result of the analysis for the setting. `ks`: the values of the model for it. |
| 1391 | `            allk = med([t[0] for k in ks.values() for t in k['totals']])` | `allk`: the median total over the regular intervals of all four kernels of the setting. |
| 1392 | `            n_over = [KN[k] for k, kv in ks.items() if kv['gap'] is not None and v['control_total'] is not None and kv['gap'] > v['control_total']]` | `n_over`: the printed names of the kernels whose largest gap is above the control of the total of the setting. |
| 1393 | `            over += bool(n_over)` | Adds 1 to `over` when the setting has such a kernel. |
| 1394 | `            f2 = b['fail2'].get(st)` | `f2`: the four values of the 2 % check for this setting (line 314), or `None` for a setting with the common stop. |
| 1395 | `            trs.append((sname(st), f(allk, 1), f(ks['oldwrite']['med'], 1) if 'oldwrite' in ks else '-', rng([kv['gap'] for kv in ks.values()], 1), f(v['control_total'], 1),` | Adds the table row: the setting, the median total over the four kernels, the median total of old write, the lowest and the highest of the largest gaps of the kernels, and the control of the total, each with 1 decimal. |
| 1396 | `                        (join_and(n_over) if n_over else 'none'), ('does not apply' if f2 is None else f'{f2[0]} of {f2[1]}'), ('-' if f2 is None else f'{f2[2]:g} to {f2[3]:g}')))` | Continues the row: the kernels of `n_over` or `none`, the number of intervals that fail the 2 % check, and the lowest and the highest value of the fewest passes of a thread in an interval. |
| 1397 | `        o.append(table(['Setting', 'Median total over the four kernels (GB/s)', 'Median total of old write (GB/s)', 'Largest gap of a kernel, lowest to highest (GB/s)', 'Control of the total (GB/s)',` | Adds the table. This line: its first five column headings. |
| 1398 | `                        'Kernels whose largest gap is above the control of the total', 'Intervals that fail the 2 % check', 'Fewest passes of a thread in an interval, lowest to highest'], trs, 'wr'))` | Continues the call: the other three headings. |
| 1399 | `        medt = [float(r[1]) for r in trs]` | `medt`: the median totals of the settings, read back from the printed cells as numbers. |
| 1400 | `        ow = [kv['med'] for st in S for k, kv in b['settings'][st].items() if k == 'oldwrite' and kv['med'] is not None]` | `ow`: the median total of old write of each setting that has one. |
| 1401 | `        o.append(f"<p class=\"take\"><b>Question Q2b, description and no decision.</b> {ID}: the plan and the handoff set no rule for when two totals are separate levels, so this page does not decide whether the levels of 2026-11-13 remain. "` | Adds a highlighted paragraph on question Q2b, marked as a description and no decision. First sentence, starting with `Insufficient data`: the plan and the handoff set no rule for when two totals are separate levels, so the page does not decide whether the levels of 2026-11-13 remain. |
| 1402 | `                 f"A rule on the gap, set before the data are read, would give it. What the data show: the largest gap of a kernel is above the control of the total of its setting in {over} of {len(S)} settings. "` | Continues the paragraph: a rule on the gap, set before the data are read, would decide it. Then what the data show: in how many of the settings the largest gap of a kernel is above the control of the total. |
| 1403 | `                 f"The median total over the four kernels of a setting is {f(min(medt), 1)} to {f(max(medt), 1)} GB/s" + (f", and old write alone is {rng(ow, 1)} GB/s" if ow else '') + f". The remaining gaps are not assigned to a cause {R('plan')}.</p>")` | Continues the paragraph: the lowest and the highest median total over the four kernels of a setting, the range of old write alone when it exists, and the sentence that the remaining gaps are not assigned to a cause. |
| 1404 | `        trs = []` | `trs`: the rows of the next table, empty again. |
| 1405 | `        for st in S:` | Loop over the settings. |
| 1406 | `            v = res['settings'][st]` | `v`: the result of the analysis for the setting. |
| 1407 | `            for k in b['settings'][st]:` | Loop over the kernels of the setting. |
| 1408 | `                kk = v['kernels'][k]` | `kk`: the result of the analysis for this kernel in this setting. |
| 1409 | `                trs.append((sname(st), KN[k], kk['n_processes'], NW(', '.join(fx(x, 1) for x in kk['spreads'])), f(kk['median_spread']), f(kk['median_total']),` | Adds the row: the setting, the kernel, the number of processes, the spread of each process with 1 decimal, the median spread and the median total. The median total is the median over the processes of the median total of the 4 intervals of the kernel. |
| 1410 | `                            NW(' / '.join(f(v[c], 1) for c in ('control_spread', 'control_total', 'control_mesh0', 'control_mesh1'))), kk['H11']))` | Continues the row: the four controls of the setting with slashes between them (spread, total, mesh 0, mesh 1), and the result of the rule for H11 in this session. |
| 1411 | `        o.append(details('Spread, the three A/A controls, and H11 per setting and kernel', table(` | Adds a folded block with this table: the spread, the controls and H11 per setting and kernel. |
| 1412 | `            ['Setting', 'Kernel', 'Processes', 'Spread of each process (GB/s)', 'Median spread (GB/s)', 'Median total (GB/s)', 'Controls: spread / total / mesh 0 / mesh 1 (GB/s)', 'H11 (word of the plan)'], trs, 'sm')` | The eight column headings of that table. |
| 1413 | `            + '<p class="cap">The spread of a process is the highest minus the lowest total of the 4 intervals of a kernel. The three controls come from asm write and asm write 2 in the same setting.</p>'))` | Adds a caption: the spread of a process is the highest minus the lowest total of the 4 intervals of a kernel, and the controls come from asm write and asm write 2 in the same setting. |
| 1414 | `        sc = sorted(res['spread_changes'].values(), key=lambda c: (c['kernel'], ('stop', 'interval', 'start').index(c['factor']), skey(c['first'])))` | `sc`: the comparisons of the spread, sorted by kernel, factor and first setting. |
| 1415 | `        rs = [c for c in sc if c['decision'] == 'resolved']` | `rs`: the resolved ones. |
| 1416 | `        o.append(f"<p><b>Change of the spread per factor (H7a and H7b for write).</b> {len(rs)} of {len(sc)} comparisons {'shows' if len(rs) == 1 else 'show'} a resolved change of the spread. "` | Adds a paragraph on the change of the spread per factor (H7a and H7b for write): how many of the comparisons show a resolved change of the spread. |
| 1417 | `                 + (' '.join(f"{KN[c['kernel']]}, {c['factor']}: the median spread changes by {fs(c['change_of_spread'])} GB/s from \"{sname(c['second'])}\" to \"{sname(c['first'])}\" (sum of the two controls {f(c['sum_of_controls'])} GB/s)." for c in rs))` | Continues the paragraph: one sentence per resolved comparison with the kernel, the factor, the change of the median spread from the second setting to the first, and the sum of the two controls. |
| 1418 | `                 + f' Data: {ref}.</p>')` | Continues the paragraph: the citation of the data. |
| 1419 | `        o.append(details('Exact numbers of every comparison of the spread', table(` | Adds a folded block with the exact numbers of every comparison of the spread. |
| 1420 | `            ['Kernel', 'Factor', 'First setting', 'Second setting', 'Change of the median spread, first minus second (GB/s)', 'Sum of the two controls (GB/s)', 'Change of the median total (GB/s), description', 'Decision'],` | The eight column headings: kernel, factor, first setting, second setting, change of the median spread (first minus second), sum of the two controls, change of the median total as a description, and decision. |
| 1421 | `            [(KN[c['kernel']], c['factor'], sname(c['first']), sname(c['second']), '-' if c['change_of_spread'] is None else fs(c['change_of_spread']), f(c['sum_of_controls']),` | The rows: one per comparison, with the signed change of the spread or `-`, and the sum of the controls. |
| 1422 | `              '-' if c['change_of_median_total'] is None else fs(c['change_of_median_total']), c['decision']) for c in sc], 'sm')))` | Continues the rows: the signed change of the median total or `-`, and the decision. |

### `b10_block`: the chart and the details for H11 (lines 1423 to 1472)

| Line | Source | Explanation |
|---:|---|---|
| 1423 | `        # H11 chart` | Comment: the next lines draw the chart for H11. |
| 1424 | `        rows, vals = [], [0.0]` | `rows`: the rows of the chart. `vals`: the values for the range of the axis, starting with 0. |
| 1425 | `        for st in S:` | Loop over the settings. |
| 1426 | `            v = res['settings'][st]` | `v`: the result of the analysis for the setting. |
| 1427 | `            rows.append(dict(head=f"{sname(st)}: controls total {f(v['control_total'], 1)}, mesh 0 {f(v['control_mesh0'], 1)}, mesh 1 {f(v['control_mesh1'], 1)} GB/s"))` | Adds a heading row: the setting in words and its three controls for H11 in GB/s: of the total, of mesh 0 and of mesh 1. |
| 1428 | `            for k, kv in b['settings'][st].items():` | Loop over the kernels of the setting with their values `kv`. |
| 1429 | `                pts = []` | `pts`: the markers of the row, empty at first. |
| 1430 | `                for j, h in enumerate(kv['hl']):` | Loop over the processes that have a highest and a lowest interval of this kernel (lines 305 to 307). |
| 1431 | `                    counted = v['control_total'] is not None and (h['hi'] - h['lo']) > v['control_total']` | `counted`: true when the highest total minus the lowest total of the process is above the control of the total. Only such a process counts for H11. |
| 1432 | `                    d0, d1 = h['hi_mesh'][0] - h['lo_mesh'][0], h['hi_mesh'][1] - h['lo_mesh'][1]` | `d0` and `d1`: for mesh 0 and for mesh 1, the rate of the mesh in the highest interval minus its rate in the lowest interval. The rate of a mesh is its `M_hist` value. |
| 1433 | `                    vals += [d0, d1]` | Adds both values to `vals`. |
| 1434 | `                    tt = f"{h['tag']}: totals {fx(h['hi'])} and {fx(h['lo'])} GB/s"` | `tt`: the start of the tooltip: the tag of the process and its two totals. |
| 1435 | `                    pts.append(dict(v=d0, c=C0, shape='circle' if counted else 'ring', dy=-4, t=tt + f', mesh 0 {fs(d0)} GB/s', op=0.9))` | Adds the marker of mesh 0 at `d0`, 4 units above the middle of the row: a circle when the process counts and a ring when it does not. |
| 1436 | `                    pts.append(dict(v=d1, c=C1, shape='diamond' if counted else 'ring', dy=5, t=tt + f', mesh 1 {fs(d1)} GB/s', op=0.9))` | Adds the marker of mesh 1 at `d1`, 5 units below the middle of the row: a diamond when the process counts and a ring when it does not. |
| 1437 | `                nc = sum(1 for h in kv['hl'] if v['control_total'] is not None and (h['hi'] - h['lo']) > v['control_total'])` | `nc`: the number of counted processes of the row. |
| 1438 | `                rows.append(dict(name=KN[k], pts=pts, right=f"{nc} of {len(kv['hl'])} processes count: {v['kernels'][k]['H11']}"))` | Adds the row of the kernel. The text at the right says how many of its processes count, and gives the result of the rule for H11. |
| 1439 | `        lim = max(abs(min(vals)), abs(max(vals))) * 1.1 or 1` | `lim`: the largest absolute value of `vals` plus 10 %, or 1. The x axis runs from `-lim` to `lim`. |
| 1440 | `        cells = [res['settings'][st]['kernels'][k]['H11'] for st in S for k in b['settings'][st]]` | `cells`: the result for H11 of every kernel in every setting of this session. |
| 1441 | `        note = 'H11 per kernel and setting in this session: ' + ', '.join(f'{cells.count(w)} {w}' for w in dict.fromkeys(cells)) + '.'` | `note`: the note above the chart: the number of cells per result in this session. |
| 1442 | `        o.append('<h4>H11: rate of each mesh in the highest interval minus the lowest interval of a process</h4>'` | Adds a heading of level 4 for the H11 chart. |
| 1443 | `                 + rowchart(rows, -lim, lim, 'rate of the mesh in the highest interval minus its rate in the lowest interval (GB/s)', f'B10 session {s}: change per mesh between the lowest and the highest interval', L=120, R=250, rh=22, note=note, vlines=[(0, '')]))` | Continues the statement: the chart itself, with a dashed line at 0. Its x axis is the rate of a mesh in the highest interval minus its rate in the lowest interval, in GB/s. |
| 1444 | `        o.append(legend([(C0, 'mesh 0, process counts', ''), (C1, 'mesh 1, process counts', 'border-radius:0;transform:rotate(45deg)'), ('#fff', 'process does not count (either mesh)', f'border:1.5px solid {MUTED}')]))` | Adds the legend: a dot for mesh 0 and a square turned by 45 degrees for mesh 1 when the process counts, and a ring for a process that does not count. |
| 1445 | `        o.append(f'<p class="cap">Two markers per process. A process counts only if its highest and lowest total differ by more than the control of the total. Data: {ref}.</p>')` | Adds a caption: two markers per process, and the rule for when a process counts. It cites the data. |
| 1446 | `        sup = [(st, k) for st in S for k in b['settings'][st] if res['settings'][st]['kernels'][k]['H11'] == 'supported']` | `sup`: the cells of this session whose result is `supported`. |
| 1447 | `        t = ''` | `t`: the text on them, empty at first. |
| 1448 | `        rose = set()` | `rose`: the set of the meshes that changed in a supported cell. |
| 1449 | `        for st, k in sup:` | Loop over the supported cells. |
| 1450 | `            v = res['settings'][st]` | `v`: the result of the analysis for the setting of the cell. |
| 1451 | `            hl = [h for h in b['settings'][st][k]['hl'] if (h['hi'] - h['lo']) > v['control_total']]` | `hl`: the counted processes of the cell. |
| 1452 | `            d0, d1 = [h['hi_mesh'][0] - h['lo_mesh'][0] for h in hl], [h['hi_mesh'][1] - h['lo_mesh'][1] for h in hl]` | `d0` and `d1`: the changes of mesh 0 and of mesh 1 over the counted processes. |
| 1453 | `            which = [nm for nm, d, c in (('mesh 0', d0, v['control_mesh0']), ('mesh 1', d1, v['control_mesh1'])) if all(abs(x) > c for x in d)]` | `which`: the names of the meshes whose absolute change is above the control of the mesh in every counted process. |
| 1454 | `            rose.update(which)` | Adds these names to `rose`. |
| 1455 | `            t += (f"Supported: {KN[k]} with \"{sname(st)}\". In its {len(hl)} counted processes mesh 0 changed by {rngs(d0)} GB/s (control {f(v['control_mesh0'])} GB/s) "` | Adds sentences for the cell: the kernel and the setting, the number of counted processes, and the range of the change of mesh 0 with its control. |
| 1456 | `                  f"and mesh 1 by {rngs(d1)} GB/s (control {f(v['control_mesh1'])} GB/s). So the mesh that changed by more than its control is {' and '.join(which) or 'none'}. ")` | Continues the text: the range of the change of mesh 1 with its control, and the mesh that changed by more than its control. |
| 1457 | `        if len(sup) > 1:` | The next line runs only with more than one supported cell. |
| 1458 | `            t += ('The supported cells name different meshes. ' if len(rose) > 1 else f"The supported cells name the same mesh ({', '.join(rose)}). ")` | Adds a sentence that says whether the supported cells name different meshes or the same mesh. |
| 1459 | `        if sup:` | The next two lines run only when a cell is supported. |
| 1460 | `            t += 'A change below the control of its mesh does not count as a change, also when it is large.'` | Adds the typed sentence that a change below the control of its mesh does not count as a change, also when it is large. |
| 1461 | `            o.append(f'<p class="take">{t}</p>')` | Adds the text as a highlighted paragraph. |
| 1462 | `        det = []` | `det`: the rows of the detail table, empty at first. |
| 1463 | `        for st in S:` | Loop over the settings. |
| 1464 | `            for k, kv in b['settings'][st].items():` | Loop over the kernels of the setting. |
| 1465 | `                for h in kv['hl']:` | Loop over the processes with a highest and a lowest interval. |
| 1466 | `                    det.append((sname(st), KN[k], e(h['tag']), f(h['hi']), f(h['hi_mesh'][0]), f(h['hi_mesh'][1]), f(h['lo']), f(h['lo_mesh'][0]), f(h['lo_mesh'][1]), fs(h['hi_mesh'][0] - h['lo_mesh'][0]), fs(h['hi_mesh'][1] - h['lo_mesh'][1])))` | Adds the row: the setting, the kernel, the tag of the process, the highest total with its two mesh values, the lowest total with its two mesh values, and the two differences high minus low with a sign. |
| 1467 | `        o.append(details('Rates of each mesh in the highest and in the lowest interval of every process', table(` | Adds a folded block with this table: the rates of each mesh in the highest and in the lowest interval of every process. |
| 1468 | `            ['Setting', 'Kernel', 'Process', 'Highest total (GB/s)', 'its mesh 0 (GB/s)', 'its mesh 1 (GB/s)', 'Lowest total (GB/s)', 'its mesh 0 (GB/s)', 'its mesh 1 (GB/s)', 'Mesh 0, high minus low (GB/s)', 'Mesh 1, high minus low (GB/s)'], det, 'sm')))` | Continues the call: the eleven column headings and the rows. |
| 1469 | `        return '\n'.join(o)` | Returns the block as one text. |
| 1470 | `    return fn` | Returns the function `fn`. |

### `b8_block`: q and thread rates against the count of mesh-1 threads (lines 1473 to 1520)

| Line | Source | Explanation |
|---:|---|---|
| 1473 | `def b8_block(R):` | Starts the function `b8_block`. It returns the function `fn`, which draws the B8 block of one session. |
| 1474 | `    def fn(m, s, b):` | Starts the inner function `fn`. `b` is the model of B8 for the session `s`. |
| 1475 | `        ref = R((s, 'B8')); xs = b['counts']` | `ref`: the citation of the B8 folders. `xs`: the thread counts on mesh 1, sorted. They are the x values of the charts. |
| 1476 | `        if len(xs) < 2:` | Tests whether B8 has fewer than 2 counts. |
| 1477 | `            return missing('B8 has fewer than 2 counts of mesh-1 threads, so no line can be drawn.')` | Then the block is the `Insufficient data` box: with fewer than 2 counts of mesh-1 threads no line can be drawn. |
| 1478 | `        o = []` | `o`: the list of the HTML pieces of the block, empty at first. |
| 1479 | `        m0n = b['mesh0'][0] if b['mesh0'] else 64` | `m0n`: the thread count on mesh 0, or 64 when it is not known. |
| 1480 | `        qs = [x['q'] for k in b['kern'].values() for v in k.values() for x in v]` | `qs`: the values of q of all regular intervals of the three kernels at all counts. |
| 1481 | `        ymin = max(0.0, __import__('math').floor(min(qs) * 10 - 1) / 10)` | `ymin`: the lower end of the q axis: the lowest q minus 0.1, rounded down to a multiple of 0.1, and not below 0. |
| 1482 | `        ser = []` | `ser`: the series of the q chart, empty at first. |
| 1483 | `        for k, col in (('oldread', C0), ('asmread', C1), ('asmread2', C2)):` | Loop over the three kernels with their colors: old read in `C0`, asm read in `C1` and asm read 2 in `C2`. |
| 1484 | `            ser.append(dict(name=KN[k], c=col, nd=2, med=[(x, med([i['q'] for i in b['kern'][k][x]])) for x in xs], pts=[(x, i['q'], f'{KN[k]}, {m0n}+{x}: q {fx(i["q"], 3)}') for x in xs for i in b['kern'][k][x]]))` | Adds the series of the kernel. Its medians: for each count, the median of q over the regular intervals of the kernel at that count. Its points: one per interval, with a tooltip that gives the kernel, the thread counts and q with 3 decimals. |
| 1485 | `        o.append(linechart(ser, xs, ymin, 1.0, f'threads on mesh 1 (with {m0n} threads on mesh 0)', 'q', f'B8 session {s}: q against the count of mesh-1 threads', W=880, H=320, R=116,` | Adds the q chart: q against the count of mesh-1 threads, with the y axis from `ymin` to 1.0. It is 880 units wide. |
| 1486 | `                           title='q (thread at the 10th percentile divided by thread at the 90th percentile)', label_pts=(KN['oldread'], KN['asmread'])))` | Continues the call: the title of the chart says how q is formed. The median values are printed at the points of old read and of asm read. |
| 1487 | `        t = f'<p class="cap">The q axis starts at {ymin:g}, not at 0. '` | `t`: a caption. It starts with the sentence that the q axis starts at `ymin` and not at 0. |
| 1488 | `        for k in ('oldread', 'asmread'):` | Loop over old read and asm read. |
| 1489 | `            md = [(x, med([i['q'] for i in b['kern'][k][x]])) for x in xs]` | `md`: the median q of the kernel at each count. |
| 1490 | `            md = [(x, v) for x, v in md if v is not None]` | Keeps the counts that have a median. |
| 1491 | `            ups = sum(1 for (_, a), (_, c) in zip(md, md[1:]) if c > a); downs = sum(1 for (_, a), (_, c) in zip(md, md[1:]) if c < a)` | `ups` and `downs`: how many times the median q rises, and how many times it falls, from one count to the next. |
| 1492 | `            if md:` | The next two lines run only when the kernel has a median. |
| 1493 | `                lo_, hi_ = min(md, key=lambda z: z[1]), max(md, key=lambda z: z[1])` | `lo_` and `hi_`: the count with the lowest and the count with the highest median q, each with its value. |
| 1494 | `                t += (f"Median q of {KN[k]}: lowest {f(lo_[1], 3)} at {m0n}+{lo_[0]} threads, highest {f(hi_[1], 3)} at {m0n}+{hi_[0]} threads. From one count to the next it rises {pl(ups, 'time', 'times')} and falls {pl(downs, 'time', 'times')}. ")` | Adds two sentences for the kernel: its lowest and its highest median q with the thread counts at which they occur, and how many times the median rises and falls from one count to the next. |
| 1495 | `        o.append(t + f'No label is given. Data: {ref}.</p>')` | Adds the caption. It ends with the sentence that no label is given, and with the citation of the data. |
| 1496 | `        panels = []` | `panels`: the three small charts of the thread rates, empty at first. |
| 1497 | `        ymax = m.get('b8_ymax') or max(v for k in b['kern'].values() for iv in k.values() for x in iv for v in (x['m0'], x['m1']) if v is not None) * 1.12` | `ymax`: the upper end of their y axis: the common value of all sessions (line 732). Without it: the largest median thread rate of this session plus 12 %. |
| 1498 | `        for k in ('oldread', 'asmread', 'asmread2'):` | Loop over the three kernels. Each gets one panel. |
| 1499 | `            s0 = dict(name='mesh 0', c=C0, med=[(x, med([i['m0'] for i in b['kern'][k][x]])) for x in xs], pts=[(x, i['m0'], f'{KN[k]}, {m0n}+{x}, mesh 0: {fx(i["m0"])} GB/s') for x in xs for i in b['kern'][k][x]])` | `s0`: the series of mesh 0. Its medians: for each count, the median over the intervals of the median thread rate of mesh 0. Its points: one per interval. |
| 1500 | `            s1 = dict(name='mesh 1', c=C1, med=[(x, med([i['m1'] for i in b['kern'][k][x]])) for x in xs], pts=[(x, i['m1'], f'{KN[k]}, {m0n}+{x}, mesh 1: {fx(i["m1"])} GB/s') for x in xs for i in b['kern'][k][x] if i['m1'] is not None])` | `s1`: the same for mesh 1. An interval without a thread on mesh 1 gives no point. |
| 1501 | `            panels.append('<div style="flex:0 1 440px">' + linechart([s0, s1], xs, 0, ymax, 'threads on mesh 1', 'GB/s', f'B8 session {s}: median thread rate per mesh, {KN[k]}', W=440, H=270, R=80, title=KN[k], label_pts=('mesh 0', 'mesh 1')) + '</div>')` | Adds the panel: a chart 440 units wide with the two series and a y axis from 0 to `ymax` in GB/s. Its title is the printed kernel name. The median values are printed at the points of both series. |
| 1502 | `        o.append('<h4>Median thread rate of each mesh against the count of mesh-1 threads</h4><div style="display:flex;flex-wrap:wrap;gap:8px">' + ''.join(panels) + '</div>')` | Adds a heading of level 4 and the three panels next to each other. The browser moves a panel to the next row when the page is too narrow. |
| 1503 | `        t = '<p class="cap">'` | `t`: the next caption, empty at first. |
| 1504 | `        for k in ('oldread', 'asmread'):` | Loop over old read and asm read. |
| 1505 | `            first, last = b['kern'][k][xs[0]], b['kern'][k][xs[-1]]` | `first` and `last`: the intervals of the kernel at the lowest and at the highest count. |
| 1506 | `            if first and last:` | The next two lines run only when both exist. |
| 1507 | `                t += (f"{KN[k].capitalize()}: the median thread on mesh 0 goes from {f(med([i['m0'] for i in first]))} GB/s at {m0n}+{xs[0]} to {f(med([i['m0'] for i in last]))} GB/s at {m0n}+{xs[-1]}, "` | Adds a sentence for the kernel: the median thread rate on mesh 0 at the lowest count and at the highest count. |
| 1508 | `                      f"and on mesh 1 from {f(med([i['m1'] for i in first]))} to {f(med([i['m1'] for i in last]))} GB/s. ")` | Continues the sentence: the same two values on mesh 1. |
| 1509 | `        o.append(t + f"The largest difference of q between neighbouring intervals of asm read and asm read 2 is {f(b['aa_q'], 3)}. Data: {ref}.</p>")` | Adds the caption. It ends with the largest difference of q between neighbouring intervals of asm read and asm read 2 (line 329), with 3 decimals, and with the citation of the data. |
| 1510 | `        trs = []` | `trs`: the rows of the table, empty at first. |
| 1511 | `        for k in ('oldread', 'asmread', 'asmread2'):` | Loop over the three kernels. |
| 1512 | `            for x in xs:` | Loop over the counts. |
| 1513 | `                v = b['kern'][k][x]` | `v`: the intervals of the kernel at this count. |
| 1514 | `                if v:` | The next line runs only when there is one. |
| 1515 | `                    trs.append((KN[k], f'{m0n}+{x}', len(v), NW(', '.join(fx(i['q'], 3) for i in v)), f(med([i['q'] for i in v]), 3), f(med([i['m0'] for i in v])), f(med([i['m1'] for i in v])), f(med([i['hist'] for i in v]))))` | Adds the row: the kernel, the thread counts, the number of intervals, q of each interval with 3 decimals, the median q, the median over the intervals of the median thread rate of mesh 0 and of mesh 1, and the median total `M_hist`. |
| 1516 | `        o.append(details('Exact numbers per kernel and count', table(['Kernel', 'Threads', 'Intervals', 'q of each interval', 'Median q', 'Median thread, mesh 0 (GB/s)', 'Median thread, mesh 1 (GB/s)', 'Median total, M_hist (GB/s)'], trs, 'sm')))` | Adds a folded block with this table and its eight column headings. |
| 1517 | `        return '\n'.join(o)` | Returns the block as one text. |
| 1518 | `    return fn` | Returns the function `fn`. |

### `b5_block` and `b5_intro`: the read variants against old read (lines 1521 to 1581)

| Line | Source | Explanation |
|---:|---|---|
| 1521 | `def b5_block(R):` | Starts the function `b5_block`. It returns the function `fn`, which draws the B5 block of one session. |
| 1522 | `    def fn(m, s, b):` | Starts the inner function `fn`. `b` is the model of B5 for the session `s`. |
| 1523 | `        ref = R((s, 'B5')); res = b['res']; K = [k for k in b['entries'] if b['kern'].get(k)]` | `ref`: the citation of the B5 folders. `res`: the result of the analysis for B5. `K`: the kernels of the sequence that have a regular interval, in the forward order. |
| 1524 | `        if 'oldread' not in K:` | Tests whether old read is not among them. |
| 1525 | `            return missing('B5 has no regular interval of old read.')` | Then the block is the `Insufficient data` box: B5 has no regular interval of old read. |
| 1526 | `        var = res['variants']` | `var`: the results of the analysis per variant. A variant is every kernel of the sequence except `oldread` and `asmread2`. |
| 1527 | `        tv = [x['hist'] for k in K for x in b['kern'][k]]` | `tv`: the totals `M_hist` of all regular intervals of these kernels. |
| 1528 | `        old = med([x['hist'] for x in b['kern']['oldread']])` | `old`: the median total of the old read intervals. |
| 1529 | `        dproc = lambda k: (var.get(k, {}).get('total_difference') or {}).get('metrics', {}).get('M_hist', {}).get('median_D')` | `dproc`: a small function that gives, for a kernel, the median over the processes of old read minus that kernel, with `M_hist`. It gives `None` when the analysis has no value. |
| 1530 | `        rows = []` | `rows`: the rows of the first chart, empty at first. |
| 1531 | `        for k in K:` | Loop over the kernels. |
| 1532 | `            v = b['kern'][k]; mk = med([x['hist'] for x in v])` | `v`: the intervals of the kernel. `mk`: the median of their totals. |
| 1533 | `            rows.append(dict(name=KN.get(k, k), pts=[dict(v=x['hist'], c=C0 if k == 'oldread' else C1, shape='circle' if k == 'oldread' else 'diamond', t=f"{x['tag']}: {fx(x['hist'])} GB/s") for x in v],` | Adds the row of the kernel: one marker per interval at its total. Old read gets circles in the color `C0`, every other kernel diamonds in the color `C1`. The tooltip gives the tag of the process and the total. |
| 1534 | `                             right=f"median {f(mk, 1)} GB/s" + ('' if dproc(k) is None else f", old read {fs(dproc(k), 1)}")))` | Continues the row: the text at the right with the median total. When the analysis has a value, it adds the words `old read` and the signed median difference of old read minus this kernel. |
| 1535 | `        others = [med([x['hist'] for x in b['kern'][k]]) for k in K if k != 'oldread']` | `others`: the median total of each kernel except old read. |
| 1536 | `        note = f"Median total of old read {f(old, 1)} GB/s. Every other kernel of the sequence: {rng(others, 1)} GB/s."` | `note`: the note above the chart: the median total of old read, and the range of the median totals of the other kernels. |
| 1537 | `        o = [rowchart(rows, 0, max(tv) * 1.06, 'total of one interval, M_hist (GB/s)', f'B5 session {s}: total of each variant', L=110, R=250, note=note)]` | `o`: the list of the HTML pieces. It starts with the chart of the total of each variant. Its x axis starts at 0 and ends 6 % above the highest total. |
| 1538 | `        rows = []` | `rows`: the rows of the second chart, empty again. |
| 1539 | `        for k in K:` | Loop over the kernels. |
| 1540 | `            v = b['kern'][k]` | `v`: the intervals of the kernel. |
| 1541 | `            rows.append(dict(name=KN.get(k, k), pts=[dict(v=x['q'], c=C0 if k == 'oldread' else C1, shape='circle' if k == 'oldread' else 'diamond', t=f"{x['tag']}: q {fx(x['q'], 3)}") for x in v],` | Adds the row of the kernel: one marker per interval at its q, with the same shapes and colors as in the first chart. |
| 1542 | `                             right=f"q {rng([x['q'] for x in v], 3)}"))` | Continues the row: the text at the right with the range of q, with 3 decimals. |
| 1543 | `        qo = [x['q'] for x in b['kern']['oldread']]; qv = [x['q'] for k in K if k != 'oldread' for x in b['kern'][k]]` | `qo`: the values of q of old read. `qv`: the values of q of all other kernels. |
| 1544 | `        o.append(rowchart(rows, 0, 1.0, 'q of one interval (no unit)', f'B5 session {s}: q of each variant', L=110, R=250, note=f"q of old read {rng(qo, 3)}. q of every other kernel {rng(qv, 3)}."))` | Adds the chart of q of each variant, with the x axis from 0 to 1. Its note gives the range of q of old read and of every other kernel. |
| 1545 | `        o.append(f'<p class="cap">One marker per process ({b["n"]} processes, one interval of each kernel per process). In the upper chart "old read +x" is old read minus the kernel, as the median of the process values. Setting: {", ".join(sname(x) for x in b["settings"])}. Data: {ref}.</p>')` | Adds a caption: one marker per process, the number of processes, and one interval of each kernel per process. It explains the text at the right of the upper chart, names the setting and cites the data. |
| 1546 | `        nres = [k for k, v in var.items() if v['total_difference']['decision'] == 'resolved' and v['total_difference']['sign'] == 1]` | `nres`: the variants for which old read minus the variant is resolved with a positive sign, so with old read above. |
| 1547 | `        aa = next((v['total_difference']['metrics']['M_hist']['aa_spread'] for v in var.values() if v['total_difference']['metrics']['M_hist']['aa_spread'] is not None), None)` | `aa`: the A/A spread of the first variant that has one. Every variant uses the same A/A pair, `asmread2` minus `asmread` in the same processes. |
| 1548 | `        t = f"<p class=\"take\">Old read minus the variant is resolved with old read above for {len(nres)} of {len(var)} kernels (A/A spread {f(aa)} GB/s). "` | `t`: a highlighted paragraph. It starts with the number of kernels for which old read minus the variant is resolved with old read above, out of all variants, and with the A/A spread in GB/s. |
| 1549 | `        if 'read_sparse' in var and dproc('read_sparse') is not None:` | The next two lines run only when `read_sparse` has a value. |
| 1550 | `            t += (f"Old read minus <code>read_sparse</code> is {fs(dproc('read_sparse'))} GB/s (median of the {var['read_sparse']['total_difference']['metrics']['M_hist']['n_processes']} process values). "` | Adds a sentence: old read minus `read_sparse` in GB/s with a sign, as the median of the process values, with their number. |
| 1551 | `                  + (f"The difference of the two median totals is {fx(abs(med([x['hist'] for x in b['kern']['read_sparse']]) - old), 1)} GB/s, which is the same quantity computed in another way." if b['kern'].get('read_sparse') else ''))` | Continues the text: the absolute difference between the median total of `read_sparse` and that of old read, with 1 decimal. The text calls it the same quantity computed in another way. |
| 1552 | `        o.append(t + '</p>')` | Adds the paragraph. |
| 1553 | `        trs = []` | `trs`: the rows of the table, empty at first. |
| 1554 | `        for k in K:` | Loop over the kernels. |
| 1555 | `            v = b['kern'][k]; d = var.get(k, {}).get('total_difference'); h = d['metrics']['M_hist'] if d else None` | `v`: the intervals of the kernel. `d`: the decision of the analysis for old read minus this kernel, or `None`. `h`: its values with `M_hist`. |
| 1556 | `            off = m['offsets'].get(('bwx', k))` | `off`: the address of the loop start modulo 64 of this kernel in the binary `bwx`, from the offsets file, or `None`. |
| 1557 | `            trs.append((KN.get(k, k), len(v), f(med([x['hist'] for x in v])), f(med([x['msum'] for x in v])), NW(rng([x['q'] for x in v], 3)), f(med([x['m0'] for x in v])), f(med([x['m1'] for x in v])),` | Adds the row: the kernel, the number of intervals, the median total with `M_hist` and with `M_sum`, the range of q, and the median over the intervals of the median thread rate of mesh 0 and of mesh 1. |
| 1558 | `                        (fs(h['median_D']) if h and h['median_D'] is not None else '-'), (f(h['aa_spread']) if h else '-'), NW(f"{d['decision']}{A.sign_txt(d['sign'])}" if d else '-'), '-' if off is None else off))` | Continues the row: the signed median difference of old read minus the kernel, the A/A spread, the decision with its sign, and the loop offset. A missing value prints as `-`. |
| 1559 | `        o.append(table(['Kernel', 'Intervals', 'Median total, M_hist (GB/s)', 'Median total, M_sum (GB/s)', 'q, lowest to highest', 'Median thread, mesh 0 (GB/s)', 'Median thread, mesh 1 (GB/s)',` | Adds the table. This line: its first seven column headings. |
| 1560 | `                        'Old read minus kernel, median of the processes (GB/s)', 'A/A spread (GB/s)', 'Decision for the difference', 'Loop start modulo 64 (B)'], trs, 'sm'))` | Continues the call: the other four headings, among them the loop start modulo 64 in bytes. |
| 1561 | `        return '\n'.join(o)` | Returns the block as one text. |
| 1562 | `    return fn` | Returns the function `fn`. |
| 1565 | `def b5_intro(m, R):` | Starts the function `b5_intro`. |
| 1566 | `    """Printed once, above the sessions."""` | Description of `b5_intro`: the text is printed once, above the blocks of the sessions. |
| 1567 | `    t = (f'<p>The rule of the handoff asks two things of a variant: the pattern label of old read, and a total whose difference to old read is not resolved {R("handoff")}. '` | `t`: a paragraph. This line: the rule of the handoff asks two things of a variant: the pattern label of old read, and a total whose difference to old read is not resolved. It cites the handoff. |
| 1568 | `         'The label is not used. Where the difference of the totals is resolved, the variant does not show the total of old read, and that part alone decides the rule.</p>')` | Continues the paragraph: the label is not used. Where the difference of the totals is resolved, the variant does not show the total of old read, and that part alone decides the rule. |
| 1569 | `    t += f'<p>Loop offsets are from the build listing {R("offsets")}. '` | Starts a second paragraph: the loop offsets are from the build listing, with a citation of the offsets file. |
| 1570 | `    ks = [k for k in ('read_sparse', 'read_nop4', 'read_nop8', 'read_nop16', 'read_nop32', 'asmread', 'asmread2')]` | `ks`: seven kernels whose loop offsets are compared: `read_sparse`, the four `nop` variants, `asmread` and `asmread2`. |
| 1571 | `    o5 = {k: m['offsets'].get(('bwx', k)) for k in ks}` | `o5`: the loop offset of each of them in the binary `bwx`, or `None`. |
| 1572 | `    if all(v is not None for v in o5.values()):` | Tests whether all seven offsets are known. |
| 1573 | `        groups = {}` | `groups`: the kernels per offset, empty at first. |
| 1574 | `        for k, v in o5.items():` | Loop over the kernels with their offsets. |
| 1575 | `            groups.setdefault(v, []).append(KN.get(k, k))` | Adds the printed kernel name to the list of its offset. |
| 1576 | `        t += ' '.join(f"{', '.join(g)}: loop at {v} modulo 64." for v, g in sorted(groups.items())) + (' So the variants do not all share one loop offset.' if len(groups) > 1 else '')` | Adds one sentence per offset, in rising order: the kernels and the offset of their loop modulo 64. With more than one offset a sentence follows: the variants do not all share one loop offset. |
| 1577 | `    else:` | In the other case the next line applies. |
| 1578 | `        t += f'{ID}: the offsets file was not found.'` | Adds a sentence that starts with `Insufficient data`: the offsets file was not found. |
| 1579 | `    return t + f' {R("devb")}</p>'` | Returns the text, with a citation of `DEVIATIONS-bwx.md` at its end. |

### `b9_block`: old read with one buffer and with two buffers per thread (lines 1582 to 1612)

| Line | Source | Explanation |
|---:|---|---|
| 1582 | `def b9_block(R):` | Starts the function `b9_block`. It returns the function `fn`, which draws the B9 block of one session. |
| 1583 | `    def fn(m, s, b):` | Starts the inner function `fn`. `b` is the model of B9 for the session `s`. |
| 1584 | `        ref = R((s, 'B9')); k1, k2 = b['kinds']['one_buffer'], b['kinds']['two_buffers']; tot = b['res']['total']` | `ref`: the citation of the B9 folders. `k1` and `k2`: the values of the processes with one buffer and with two buffers. `tot`: the result of the analysis for the total. |
| 1585 | `        if not k1['pv'] or not k2['pv']:` | Tests whether one of the two kinds has no process value. |
| 1586 | `            return missing('B9 needs processes with one buffer and with two buffers. One kind is missing.')` | Then the block is the `Insufficient data` box: B9 needs processes with one buffer and with two buffers. |
| 1587 | `        vals = [v for _, v in k1['pv'] + k2['pv']]` | `vals`: the process values of both kinds. A process value is the median total `M_hist` of the intervals of one process. |
| 1588 | `        lo, hi = min(vals), max(vals); pad = (hi - lo) * 0.25 or 1` | `lo` and `hi`: the lowest and the highest process value. `pad`: 25 % of the range, or 1 when the range is 0. |
| 1589 | `        rows = [dict(name='one buffer per thread', pts=[dict(v=v, c=C0, t=f'{t}: {fx(v)} GB/s', lab=fx(v, 1), side='a' if i % 2 else 'b') for i, (t, v) in enumerate(sorted(k1['pv'], key=lambda z: z[1]))],` | `rows`: the two rows of the chart. First row, one buffer per thread: one circle in the color `C0` per process at its process value, in rising order. Each has its value with 1 decimal as a label. The first label stands below its marker, the next one above, and so on. |
| 1590 | `                     right=f"median {f(med([v for _, v in k1['pv']]))} GB/s"),` | Continues the first row: the text at the right with the median of its process values. |
| 1591 | `                dict(name='two buffers per thread', pts=[dict(v=v, c=C1, shape='diamond', t=f'{t}: {fx(v)} GB/s', lab=fx(v, 1), side='a' if i % 2 else 'b') for i, (t, v) in enumerate(sorted(k2['pv'], key=lambda z: z[1]))],` | Second row, two buffers per thread: the same with diamonds in the color `C1`. |
| 1592 | `                     right=f"median {f(med([v for _, v in k2['pv']]))} GB/s")]` | Continues the second row: the median of its process values. |
| 1593 | `        if tot['difference'] is not None:` | Tests whether the analysis has a difference of the totals. |
| 1594 | `            note = f"Total with one buffer minus total with two: {fs(tot['difference'])} GB/s. A/A value: {f(tot['aa_value'])} GB/s."` | `note`: the note above the chart: the total with one buffer minus the total with two in GB/s, and the A/A value. |
| 1595 | `        else:` | In the other case the next line applies. |
| 1596 | `            note = 'Fewer than 2 processes of a kind.'` | The note says that a kind has fewer than 2 processes. |
| 1597 | `        o = [rowchart(rows, lo - pad, hi + pad, 'median total of the intervals of one process, M_hist (GB/s). The axis does not start at 0.', f'B9 session {s}: total of old read with one and with two buffers', L=160, R=150, rh=46, note=note)]` | `o`: the list of the HTML pieces. It starts with the chart. The title of its x axis says that the axis does not start at 0. |
| 1598 | `        q1, q2 = [x['q'] for x in k1['ivs']], [x['q'] for x in k2['ivs']]` | `q1` and `q2`: the values of q of the regular intervals with one buffer and with two buffers. |
| 1599 | `        t = f'<p class="take"><b>Description.</b> '` | `t`: a highlighted paragraph. It starts with the bold word `Description.` |
| 1600 | `        if tot['difference'] is not None:` | The next two lines run only when the analysis has a difference. |
| 1601 | `            t += (f"The total with one buffer minus the total with two is {fs(tot['difference'])} GB/s ({fx(abs(tot['difference']) / med(vals) * 100, 2)} % of the total). "` | Adds a sentence: the total with one buffer minus the total with two, in GB/s with a sign. In brackets it gives the absolute difference in % of the median of all process values, with 2 decimals. |
| 1602 | `                  f"The largest difference between two processes of one kind is {f(tot['aa_value'])} GB/s. So the difference of the totals is {tot['decision']}. ")` | Continues the text: the largest difference between two processes of one kind, the A/A value, and the decision of the analysis for the difference of the totals. |
| 1603 | `        t += (f"q of old read is {rng(q1, 3)} with one buffer ({len(q1)} intervals) and {rng(q2, 3)} with two ({len(q2)} intervals). "` | Adds a sentence: the range of q of old read with one buffer and with two, each with its number of intervals. |
| 1604 | `              + ('The two ranges of q overlap.' if q1 and q2 and max(min(q1), min(q2)) <= min(max(q1), max(q2)) else 'The two ranges of q do not overlap.'))` | Continues the text: whether the two ranges of q overlap. They overlap when the higher of the two lowest values is not above the lower of the two highest values. |
| 1605 | `        o.append(t + f' One marker per process. Setting: {", ".join(sname(x) for x in b["settings"])}. Data: {ref}.</p>')` | Adds the paragraph. It ends with the remark that there is one marker per process, with the setting and with the citation of the data. |
| 1606 | `        o.append(table(['Kind', 'Processes', 'Median total of each process (GB/s)', 'Intervals', 'q, lowest to highest', 'Median thread, mesh 0 (GB/s)', 'Median thread, mesh 1 (GB/s)'],` | Adds a table. This line: its seven column headings: kind, processes, median total of each process, intervals, lowest and highest q, and the median thread rate of mesh 0 and of mesh 1. |
| 1607 | `                       [(nm, k['n'], ', '.join(fx(v) for _, v in k['pv']), len(k['ivs']), rng([x['q'] for x in k['ivs']], 3), f(med([x['m0'] for x in k['ivs']])), f(med([x['m1'] for x in k['ivs']])))` | The rows: the kind, the number of processes, the process values, the number of regular intervals, the range of q, and the median over the intervals of the median thread rate of mesh 0 and of mesh 1. |
| 1608 | `                        for nm, k in (('one buffer', k1), ('two buffers', k2))]))` | Continues the rows: one row for one buffer and one for two buffers. |
| 1609 | `        return '\n'.join(o)` | Returns the block as one text. |
| 1610 | `    return fn` | Returns the function `fn`. |

### `c3_block`: core counters per kernel and mesh (lines 1613 to 1673)

| Line | Source | Explanation |
|---:|---|---|
| 1613 | `def c3_block(R):` | Starts the function `c3_block`. It returns the function `fn`, which draws the C3 block of one session. |
| 1614 | `    def fn(m, s, b):` | Starts the inner function `fn`. `b` is the model of C3 for the session `s`. |
| 1615 | `        ref = R((s, 'C3')); km = b['km']` | `ref`: the citation of the C3 folders. `km`: the groups of the analysis per kernel and mesh (lines 370 to 372). |
| 1616 | `        if not km:` | Tests whether there is no group. |
| 1617 | `            return missing('C3 has no counter row that can be used.')` | Then the block is the `Insufficient data` box: C3 has no counter row that can be used. |
| 1618 | `        kernels = [k for k in ('oldread', 'read', 'asmread', 'asmread2', 'read_sparse', 'read_nop4', 'read_nop8', 'read_nop16', 'read_nop32') if (k, 'mesh0') in km or (k, 'mesh1') in km]` | `kernels`: the kernels that have a group on mesh 0 or on mesh 1, in a fixed order of nine names. |
| 1619 | `        o = [f"<p>{b['res']['rows_C']} C rows were read (one per thread and interval), and {b['res']['rows_C_not_used']} were not used. Data: {ref}.</p>"]` | `o`: the list of the HTML pieces. It starts with a paragraph: the number of C rows that the analysis read, one per thread and interval, and the number that it did not use. The analysis does not use a C row when its T row is missing, when a time is missing or not above 0, or when the counter group ran for less than its enabled time. |
| 1620 | `        panels = []` | `panels`: the four small charts, empty at first. |
| 1621 | `        for key, lab, nd in (('median_l1d_refill_per_line', 'L1 refills per 64 B line', 4), ('median_l2d_refill_per_line', 'L2 refills per 64 B line', 4),` | Loop over four values of a group, each with its title and its number of decimals. This line: the L1 refills and the L2 refills per 64 B line. |
| 1622 | `                             ('median_ll_read_miss_per_line', 'last-level read misses per 64 B line', 4), ('median_clock_GHz', 'clock of the busy core (GHz)', 4)):` | Continues the list: the last-level read misses per 64 B line, and the clock of the busy core in GHz. |
| 1623 | `            vals = [g[key] for gs in km.values() for g in gs if g[key] is not None]` | `vals`: this value of every group of every kernel and mesh, where it exists. For a counter it is the median over the C rows of the group of the count divided by the lines. The lines of a row are the bytes of its T row divided by 64. The clock is the median of the cycles divided by the CPU time of the thread in ns. |
| 1624 | `            if not vals:` | Tests whether no group has this value. |
| 1625 | `                panels.append(f'<div style="flex:1 1 400px">{missing(lab + ": the event is not supported or did not open. The event list of step A7 names the events.")}</div>'); continue` | Then the panel is the `Insufficient data` box: the event is not supported or did not open. The loop goes on with the next value. |
| 1626 | `            lo, hi = min(vals), max(vals); pad = (hi - lo) * 0.15 or abs(hi) * 0.01 or 1` | `lo` and `hi`: the lowest and the highest group median. `pad`: 15 % of the range. When the range is 0 it is 1 % of the value, and 1 when that is 0 too. |
| 1627 | `            rows = []` | `rows`: the rows of the panel, empty at first. |
| 1628 | `            for k in kernels:` | Loop over the kernels. |
| 1629 | `                pts, rt = [], []` | `pts`: the markers of the row. `rt`: the two numbers for the text at the right. |
| 1630 | `                for mesh, col, shp, dy in (('mesh0', C0, 'circle', -4), ('mesh1', C1, 'diamond', 5)):` | Loop over the two meshes: mesh 0 as circles in `C0`, 4 units above the middle of the row, and mesh 1 as diamonds in `C1`, 5 units below it. |
| 1631 | `                    gv = [g[key] for g in km.get((k, mesh), []) if g[key] is not None]` | `gv`: the group medians of this kernel on this mesh, where they exist. One group is one setting and one sequence. |
| 1632 | `                    pts += [dict(v=x, c=col, shape=shp, dy=dy, r=3.5, op=0.7, t=f'{KN.get(k, k)} {mesh}: {fx(x, nd)}') for x in gv]` | Adds one marker per group. Its tooltip gives the kernel, the mesh and the value. |
| 1633 | `                    rt.append(f(med(gv), 4))` | Adds the median of these group medians, with 4 decimals, to `rt`. |
| 1634 | `                rows.append(dict(name=KN.get(k, k), pts=pts, right=' / '.join(rt)))` | Adds the row of the kernel. The text at the right gives the two medians, mesh 0 first, with a slash between them. |
| 1635 | `            panels.append('<div style="flex:0 1 440px">' + rowchart(rows, lo - pad, hi + pad, lab + '. The axis does not start at 0.', f'C3 session {s}: {lab}', L=92, R=104, W=440, rh=22,` | Adds the panel: a chart 440 units wide. The title of its x axis says that the axis does not start at 0. |
| 1636 | `                                                                                    note=lab + ' (mesh 0 / mesh 1)', ticks=ticks_for(lo - pad, hi + pad, 4)) + '</div>')` | Continues the call: the note above the chart names the value and the order mesh 0 and mesh 1. The axis gets about 4 tick steps. |
| 1637 | `        o.append('<div style="display:flex;flex-wrap:wrap;gap:8px">' + ''.join(panels) + '</div>')` | Adds the four panels next to each other. |
| 1638 | `        o.append(legend([(C0, 'mesh 0', ''), (C1, 'mesh 1', 'border-radius:0;transform:rotate(45deg)')]))` | Adds the legend: a dot for mesh 0 and a square turned by 45 degrees for mesh 1. |
| 1639 | `        # computed comparison old read against new read` | Comment: the next lines compare old read with new read from computed values. |
| 1640 | `        t = '<p class="take"><b>Description, and no rule of the plan decides on it.</b> '` | `t`: a highlighted paragraph. It starts with bold words: this is a description, and no rule of the plan decides on it. |
| 1641 | `        for key, lab in (('median_l2d_refill_per_line', 'L2 refills per line'), ('median_ll_read_miss_per_line', 'last-level read misses per line')):` | Loop over two values: the L2 refills per line and the last-level read misses per line. |
| 1642 | `            for mesh in ('mesh0', 'mesh1'):` | Loop over the two meshes. |
| 1643 | `                a = [g[key] for g in km.get(('oldread', mesh), []) if g[key] is not None]; c = [g[key] for g in km.get(('read', mesh), []) if g[key] is not None]` | `a`: the group medians of old read on this mesh. `c`: the group medians of new read. |
| 1644 | `                if a and c:` | The next two lines run only when both lists have a value. |
| 1645 | `                    per = lambda v: (f' (about 1 per {fx(1 / med(v), 1)} lines)' if med(v) and med(v) < 0.5 else '')` | `per`: a small function for a second way to say a small value. When the median of the list is above 0 and below 0.5, it gives the words `about 1 per N lines`, with N as 1 divided by the median. |
| 1646 | `                    t += f"{lab.capitalize()} on {mesh.replace('mesh', 'mesh ')}: old read {rng(a, 4)}{per(a)}, new read {rng(c, 4)}{per(c)}. "` | Adds a sentence: the value on this mesh for old read and for new read, each as a range with 4 decimals and with the text of `per`. |
| 1647 | `        ck = [g['median_clock_GHz'] for gs in km.values() for g in gs if g['median_clock_GHz'] is not None]` | `ck`: the median clock of every group, where it exists. |
| 1648 | `        if ck:` | The next line runs only when a group has a clock. |
| 1649 | `            t += f"The clock of a busy core is {rng(ck, 4)} GHz over all kernels and both meshes, a spread of {fx((max(ck) - min(ck)) / med(ck) * 100, 2)} %."` | Adds a sentence: the range of the clock of a busy core in GHz over all kernels and both meshes. It also gives the spread: the highest minus the lowest group median, in % of their median. |
| 1650 | `        o.append(t + '</p>')` | Adds the paragraph. |
| 1651 | `        trs = []` | `trs`: the rows of the table, empty at first. |
| 1652 | `        for k in kernels:` | Loop over the kernels. |
| 1653 | `            for mesh in ('mesh0', 'mesh1'):` | Loop over the two meshes. |
| 1654 | `                gs = km.get((k, mesh), [])` | `gs`: the groups of this kernel on this mesh. |
| 1655 | `                if gs:` | The next three lines run only when there is a group. |
| 1656 | `                    r_ = lambda key, nd=4: rng([g[key] for g in gs], nd)` | `r_`: a small function that prints the lowest and the highest value of one key over the groups. |
| 1657 | `                    trs.append((KN.get(k, k), mesh.replace('mesh', 'mesh '), len(gs), sum(g['n_rows'] for g in gs), r_('median_thread_GBps', 2), r_('median_clock_GHz'), r_('median_instructions_per_line'),` | Adds the row: the kernel, the mesh, the number of groups, the sum of their C rows, and the ranges of the median thread rate (2 decimals), of the clock and of the instructions per line. |
| 1658 | `                                r_('median_l1d_refill_per_line'), r_('median_l2d_refill_per_line'), r_('median_ll_read_miss_per_line')))` | Continues the row: the ranges of the L1 refills, of the L2 refills and of the last-level read misses per line, with 4 decimals. |
| 1659 | `        o.append(details('Exact numbers per kernel and mesh', table(` | Adds a folded block with this table: the exact numbers per kernel and mesh. |
| 1660 | `            ['Kernel', 'Mesh', 'Groups', 'C rows', 'Median thread rate (GB/s)', 'Clock (GHz)', 'Instructions per line', 'L1 refills per line', 'L2 refills per line', 'Last-level read misses per line'], trs, 'sm')` | The ten column headings of that table. |
| 1661 | `            + '<p class="cap">Each cell gives the lowest and the highest group median. A line is 64 B of the bytes that the thread counted. The clock is the cycle count divided by the CPU time of the thread.</p>'))` | Adds a caption: each cell gives the lowest and the highest group median. A line is 64 B of the bytes that the thread counted. The clock is the cycle count divided by the CPU time of the thread. |
| 1662 | `        # cputime against elapsed` | Comment: the next lines compare the CPU time with the elapsed time. |
| 1663 | `        if b['n_rows']:` | The lines up to line 1669 run only when the model counted a C row (line 365). |
| 1664 | `            lw = b['lowest']` | `lw`: the values of the row with the lowest CPU share (line 368). |
| 1665 | `            o.append('<h4>CPU time against elapsed time (threads that lost their CPU for a part of an interval)</h4>')` | Adds a heading of level 4: CPU time against elapsed time. It names the purpose: threads that lost their CPU for a part of an interval. |
| 1666 | `            o.append(table(['Interval length (ms)', 'C rows', 'Lowest CPU time as a share of elapsed time (%)', 'Largest elapsed time minus CPU time in one interval (ms)', 'Rows below 99 %'],` | Adds a table. This line: its five column headings: interval length in ms, C rows, lowest CPU time as a share of the elapsed time in %, largest elapsed time minus CPU time in one interval in ms, and rows below 99 %. |
| 1667 | `                           [(ms, g['n'], fx(g['share_min'] * 100, 2), fx(g['off_max'], 2), g['below99']) for ms, g in sorted(b['cpu'].items())]))` | The rows: one per interval length, in rising order, with the values of lines 361 to 364. |
| 1668 | `            o.append(f"<p class=\"take\">In {b['n_below99']} of {b['n_rows']} rows the thread had its CPU for less than 99 % of the interval. The lowest share is {fx(lw['share'] * 100, 2)} %. "` | Adds a highlighted paragraph: in how many of the rows the thread had its CPU for less than 99 % of the interval, and the lowest share in %. |
| 1669 | `                     f"That thread ran on CPU {lw['cpu']} ({KN.get(lw['kernel'], lw['kernel'])}, process <code>{e(lw['tag'])}</code>). It had {fx(lw['off_ms'], 2)} ms of its {fx(lw['elapsed'] * 1e3, 1)} ms without CPU time.</p>")` | Continues the paragraph: the CPU on which that thread ran, its kernel and the tag of its process, and how many ms of its elapsed time it had no CPU time. |
| 1670 | `        return '\n'.join(o)` | Returns the block as one text. |
| 1671 | `    return fn` | Returns the function `fn`. |

### `sec_h10_h9b`: what the data can and cannot say for H10 and H9b (lines 1674 to 1688)

| Line | Source | Explanation |
|---:|---|---|
| 1674 | `def sec_h10_h9b(m, R):` | Starts the function `sec_h10_h9b`. |
| 1675 | `    o = ['<h2 id="h10">H10 and H9b: what these data can and cannot say</h2>']` | `o`: the list of the HTML pieces. It starts with the heading of level 2, which has the anchor name `h10`. |
| 1676 | `    h = {x['label']: x for x in m['hyp']}` | `h`: the rows of the hypothesis table by their label. |
| 1677 | `    o.append(f'<h3>H10: "{h["H10"]["word"]}"</h3><ul>'` | Adds a heading of level 3 with the label H10 and the word of its row in double quotes, and opens a list. |
| 1678 | `             '<li><b>Can say:</b> how many refills of its own caches a core counted for each 64 B line that the loop read, per kernel and mesh. The section of C3 gives these values.</li>'` | Typed list item `Can say`: how many refills of its own caches a core counted for each 64 B line that the loop read, per kernel and mesh. It names the section of C3 as the place of these values. |
| 1679 | `             f'<li><b>Cannot say:</b> whether the memory system fetched lines that the loop did not consume. The core events count refills that the core saw. The plan states that H10 could still hold for traffic that these events do not count {R("plan")}.</li>'` | Typed list item `Cannot say`: whether the memory system fetched lines that the loop did not consume. The core events count refills that the core saw, and by the plan H10 could still hold for traffic that these events do not count. |
| 1680 | `             f'<li><b>{ID}:</b> memory requests per line read. Step D1 would give them (mesh counters <code>hns_mc_reqs_local_all</code> and <code>hns_mc_reqs_remote_all</code>, with root). Part D was not run. Even D1 can support H10 and cannot reject it {R("plan")}.</li></ul>')` | Typed list item that starts with `Insufficient data`: the memory requests per line read. Step D1 would give them, with the mesh counters `hns_mc_reqs_local_all` and `hns_mc_reqs_remote_all` and root rights. The text says that Part D was not run, and that even D1 can support H10 and cannot reject it. The line closes the list. |
| 1681 | `    o.append(f'<h3>H9b: "{h["H9b"]["word"]}"' + (', open for the user' if h['H9b']['open'] else '') + '</h3><ul>'` | Adds a heading of level 3 with the label H9b and the word of its row, with the words `open for the user` when the row has an open question, and opens a list. |
| 1682 | `             '<li>The hypothesis table gives the ranges of q and of the total of old read per session, and the two readings of the word.</li>'` | Typed list item: the hypothesis table gives the ranges of q and of the total of old read per session, and the two readings of the word. |
| 1683 | `             f'<li><b>Cannot say:</b> why old read gave totals of {fx(PLAN_OLD_LOW[0])} to {fx(PLAN_OLD_LOW[1])} GB/s on 2026-10-30 {R("plan")}. That run is a number from an earlier result folder. Rule 10 of the plan uses such a number for hypotheses only, not as evidence.</li>'` | Typed list item `Cannot say`: why old read gave totals of 365.10 to 368.25 GB/s on 2026-10-30. That run is a number from an earlier result folder, and rule 10 of the plan uses such a number for hypotheses only, not as evidence. |
| 1684 | `             '<li><b>Cannot say:</b> anything about another day or about the state after a restart of the machine. The section "When the sessions ran" gives the times.</li>'` | Typed list item `Cannot say`: anything about another day, or about the state after a restart of the machine. |
| 1685 | `             f'<li><b>{ID}:</b> the same steps on another day, and after a restart of the machine. They would show whether the values of old read change for a reason other than the kernel.</li></ul>')` | Typed list item that starts with `Insufficient data`: the same steps on another day and after a restart of the machine would show whether the values of old read change for a reason other than the kernel. The line closes the list. |
| 1686 | `    return '\n'.join(o)` | Returns the section as one text. |

### `WORDS`: the list "Words used here" of the generated page (lines 1689 to 1771)

| Line | Source | Explanation |
|---:|---|---|
| 1689 | `WORDS = [` | `WORDS`: the entries of the list `Words used here` of the generated page. Each entry is a pair of a term and its definition. Both are HTML text that is typed here, so no entry depends on the input. |
| 1690 | `    ('CRB', 'the Arm Phoenix Reference Server (128 cores of the 64-bit Arm architecture). All measurements ran there.'),` | Entry for CRB: the Arm reference server on which all measurements ran. |
| 1691 | `    ('Plan, handoff', 'the files <code>plan.md</code> (the reviewed test plan) and <code>handoff.md</code> (the instructions for its execution).'),` | Entry for the plan and the handoff: the files `plan.md` (the reviewed test plan) and `handoff.md` (the instructions for its execution). |
| 1692 | `    ('Part A, B, C, D', 'the parts of the plan. Part A: screening with the existing benchmark. Part B: the changed benchmark. Part C: core counters without root. Part D: counters and page addresses that need root. Part D was not run.'),` | Entry for the parts A to D of the plan: Part A is the screening with the existing benchmark, Part B uses the changed benchmark, Part C reads core counters without root, and Part D needs root. The text says that Part D was not run. |
| 1693 | `    ('Q2, Q2a, Q2b', 'the second question of the plan. Q2a: why old read has a higher total than new read with 120 threads. Q2b: why the write kernels give several separate totals.'),` | Entry for Q2 and its two parts: Q2a asks why old read has a higher total than new read with 120 threads, and Q2b why the write kernels give several separate totals. |
| 1694 | `    ('<code>bwx</code>', 'the changed copy of the benchmark <code>bandwidth.c</code> that Parts B and C use. It holds the old kernels, the new kernels and all variants in one program.'),` | Entry for `bwx`: the changed copy of the benchmark `bandwidth.c` that Parts B and C use. It holds the old kernels, the new kernels and all variants in one program. |
| 1695 | `    ('Kernel', 'one timed loop of the benchmark. It is not the Linux kernel.'),` | Entry for the word kernel: one timed loop of the benchmark, not the Linux kernel. |
| 1696 | `    ('Old read (<code>oldread</code>)', 'the read loop before 2026-11-13. Per 128 B it runs 4 load instructions (<code>ldp</code>, 32 B each) and 8 vector adds.'),` | Entry for old read (`oldread`): the read loop before 2026-11-13. The text gives its instructions per 128 B: 4 load instructions of 32 B each and 8 vector adds. |
| 1697 | `    ('New read (<code>read</code>)', 'the read loop since 2026-11-13, written in C. Per 256 B it runs 8 <code>ldp</code> and no add.'),` | Entry for new read (`read`): the read loop from 2026-11-13 on, written in C. The text gives its instructions per 256 B: 8 load instructions and no add. |
| 1698 | `    ('asm read (<code>asmread</code>), asm read 2 (<code>asmread2</code>)', 'the read loop written in assembly, with the same loop body as new read, and a second copy of it under another name.'),` | Entry for asm read and asm read 2: the read loop written in assembly with the same loop body as new read, and a second copy of it under another name. |
| 1699 | `    ('Old write, new write, asm write, asm write 2', 'the write loops in the same four forms (<code>oldwrite</code>, <code>write</code>, <code>asmwrite</code>, <code>asmwrite2</code>).'),` | Entry for the four write loops: `oldwrite`, `write`, `asmwrite` and `asmwrite2`, the same four forms as for read. |
| 1700 | `    ('<code>nop</code>', 'an instruction that does nothing.'),` | Entry for `nop`: an instruction that does nothing. |
| 1701 | `    ('<code>read_nop4</code>, <code>read_nop8</code>, <code>read_nop16</code>, <code>read_nop32</code>', 'the asm read loop with 4, 8, 16 or 32 <code>nop</code> instructions added per 256 B.'),` | Entry for the four `nop` variants: the asm read loop with 4, 8, 16 or 32 `nop` instructions added per 256 B. |
| 1702 | `    ('<code>read_sparse</code>', 'a read loop with 4 <code>ldp</code> and 9 <code>nop</code> per 128 B. It has the 16 instructions per 128 B of old read and no vector add.'),` | Entry for `read_sparse`: a read loop with 4 load instructions and 9 `nop` per 128 B. The text says that it has the 16 instructions per 128 B of old read and no vector add. |
| 1703 | `    ('Loop offset', 'the address of the first instruction of a loop modulo 64 B.'),` | Entry for the loop offset: the address of the first instruction of a loop modulo 64 B. |
| 1704 | `    ('Process, launch, tag', 'one start of <code>bwx</code>. Its name in the run script is its tag, for example <code>pass-500-common-p1</code>.'),` | Entry for process, launch and tag: one start of `bwx`. Its tag is its name in the run script. |
| 1705 | `    ('Visit', 'one login to CRB that runs one or more steps. Each step writes its own result folder.'),` | Entry for a visit: one login to CRB that runs one or more steps, each with its own result folder. |
| 1706 | `    ('Short run', 'one run of every sequence with 0.1 s intervals before session 1, made to test the scripts.'),` | Entry for the short run: one run of every sequence with intervals of 0.1 s before session 1, made to test the scripts. |
| 1707 | `    ('Sequence, interval, round, position', 'a process times a list of kernels (the sequence), one interval per entry. A round is one run of the whole sequence. The position counts the entries from 0.'),` | Entry for sequence, interval, round and position: a process times a list of kernels, one interval per entry. A round is one run of the whole sequence, and the position counts the entries from 0. |
| 1708 | `    ('Pass', 'one sweep of a thread over its whole buffer.'),` | Entry for a pass: one sweep of a thread over its whole buffer. |
| 1709 | `    ('Process value', 'one number per process, for example the median total of its intervals. Decisions use process values, never single intervals.'),` | Entry for the process value: one number per process. The text says that decisions use process values and never single intervals. |
| 1710 | `    ('Warm-up pass', 'one pass that a thread makes with the kernel before the timed interval starts. It is not timed.'),` | Entry for the warm-up pass: one pass that a thread makes with the kernel before the timed interval starts. It is not timed. |
| 1711 | `    ('Header line, <code>env.txt</code>, <code>launches.txt</code>', 'the run script writes one header line per launch into the csv file, with the load readings. <code>env.txt</code> holds the readings at the start and the end of a visit. <code>launches.txt</code> holds a second reading and the 5 busiest processes before each launch.'),` | Entry for the header line, `env.txt` and `launches.txt`: where the run script writes the load readings. |
| 1712 | `    ('Root', 'administrator rights on CRB. Our scripts do not use them.'),` | Entry for root: administrator rights on CRB, which our scripts do not use. |
| 1713 | `    ('Session', 'one run of all steps. The plan asks for two sessions some hours apart. The section "When the sessions ran" gives the times.'),` | Entry for a session: one run of all steps. The plan asks for two sessions some hours apart. |
| 1714 | `    ('256 MiB, GB/s', 'each thread has its own buffer of 256 MiB (1 MiB = 2<sup>20</sup> bytes), which is read from main memory. Rates are in GB/s (1 GB = 10<sup>9</sup> bytes).'),` | Entry for the units: each thread has its own buffer of 256 MiB, which is read from main memory, and rates are in GB/s. The HTML tag `sup` raises the exponents of the two powers. |
| 1715 | `    ('Mesh 0, mesh 1', 'the two halves of the chip. CPUs 0 to 63 are on mesh 0. CPUs 64 to 127 are on mesh 1, and we use 64 to 119.'),` | Entry for mesh 0 and mesh 1: the two halves of the chip, with the CPUs 0 to 63 and 64 to 127. Our runs use 64 to 119 on mesh 1. |
| 1716 | `    ('a+b threads, 64+56', 'a threads on mesh 0 and b threads on mesh 1. 64+56 is all 120 CPUs that we may use.'),` | Entry for the form `a+b threads`: a threads on mesh 0 and b threads on mesh 1. 64+56 is all 120 CPUs that our runs may use. |
| 1717 | `    ('Thread rate', 'the bytes of one thread divided by its own elapsed time.'),` | Entry for the thread rate: the bytes of one thread divided by its own elapsed time. |
| 1718 | `    ('Total, M_hist', 'the bytes of all threads divided by the longest elapsed time of a thread. This is what the benchmark prints. It is the decision metric.'),` | Entry for the total, `M_hist`: the bytes of all threads divided by the longest elapsed time of a thread. The text says that the benchmark prints this value and that it is the decision metric. |
| 1719 | `    ('M_sum', 'the sum of the thread rates. It is reported next to M_hist as a description.'),` | Entry for `M_sum`: the sum of the thread rates, reported next to `M_hist` as a description. |
| 1720 | `    ('Median', 'the middle value of a sorted list. With an even count it is the mean of the two middle values.'),` | Entry for the median: the middle value of a sorted list, and the mean of the two middle values with an even count. |
| 1721 | `    ('q', 'the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one interval. With 120 threads these are the 12th and the 108th smallest rate. q near 1 means that all threads have nearly the same rate.'),` | Entry for q: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one interval. With 120 threads these are the 12th and the 108th smallest rate. A q near 1 means that all threads have nearly the same rate. |
| 1722 | `    ('Pattern', 'how the thread rates of one interval are distributed over the threads.'),` | Entry for the pattern: how the thread rates of one interval are distributed over the threads. |
| 1723 | `    ('Split, uniform', 'the two pattern labels of the handoff (q below 0.65, q above 0.85). They are not used on this page.'),` | Entry for split and uniform: the two pattern labels of the handoff, q below 0.65 and q above 0.85. The text says that they are not used on this page. |
| 1724 | `    ('Bounded prediction', 'the one measurable statement of a hypothesis that a step tests.'),` | Entry for the bounded prediction: the one measurable statement of a hypothesis that a step tests. |
| 1725 | `    ('Setting', 'one combination of stop method, interval length and start.'),` | Entry for a setting: one combination of stop method, interval length and start. |
| 1726 | `    ('Stop method', '"whole passes": a thread stops after a whole pass, as in <code>bandwidth.c</code>. "common stop": all threads stop at one common time and count the bytes of the partial pass.'),` | Entry for the stop method. Whole passes: a thread stops after a whole pass, as in `bandwidth.c`. Common stop: all threads stop at one common time and count the bytes of the partial pass. |
| 1727 | `    ('Start', '"common start": every thread starts at the start of its buffer. "offset start": every thread starts at its own offset inside its buffer.'),` | Entry for the start. Common start: every thread starts at the start of its buffer. Offset start: every thread starts at its own offset inside its buffer. |
| 1728 | `    ('Reproduction condition', 'the setting "whole passes, 0.5 s, common start". It is the timing method of the run of 2026-11-13.'),` | Entry for the reproduction condition: the setting whole passes, 0.5 s, common start. The text calls it the timing method of the run of 2026-11-13. |
| 1729 | `    ('2 % check', 'rule 7 of the plan for whole passes: one pass must take at most 2 % of the interval. That means at least 50 passes per thread.'),` | Entry for the 2 % check: rule 7 of the plan for whole passes. One pass must take at most 2 % of the interval, so a thread needs at least 50 passes. |
| 1730 | `    ('D', 'the total of old read minus the total of new read, in GB/s. One value per process: the mean over its rounds.'),` | Entry for D: the total of old read minus the total of new read, in GB/s. There is one value per process, the mean over its rounds. |
| 1731 | `    ('A/A control, A/A spread, E', 'an A/A control is one loop that exists twice in the program (asm read and asm read 2). E is the difference of the two copies in one process. The A/A spread is the largest absolute E over the processes of a setting.'),` | Entry for the A/A control, the A/A spread and E. An A/A control is one loop that exists twice in the program. E is the difference of the two copies in one process. The A/A spread is the largest absolute E over the processes of a setting. |
| 1732 | `    ('Resolved', 'the absolute median of the process values is larger than the A/A spread, and all process values have one sign. A change between two settings is resolved if it is larger than the sum of the two A/A spreads and the two sets of values do not overlap.'),` | Entry for the word resolved: the absolute median of the process values is larger than the A/A spread, and all process values have one sign. A change between two settings is resolved if it is larger than the sum of the two A/A spreads and the two sets of values do not overlap. |
| 1733 | `    ('Limit, band (of a change)', 'the sum of the two A/A spreads (B7) or of the two controls of the spread (B10) of the two settings that are compared. A chart draws it as a grey band around 0.'),` | Entry for the limit or band of a change: the sum of the two A/A spreads (B7) or of the two controls of the spread (B10) of the two compared settings. A chart draws it as a grey band around 0. |
| 1734 | `    ('A/A value', 'the A/A control of a comparison that has no A/A spread per setting: for B7 with one kernel per process, and for the totals of B9.'),` | Entry for the A/A value: the A/A control of a comparison that has no A/A spread per setting. It is used for B7 with one kernel per process and for the totals of B9. |
| 1735 | `    ('Spread (B10)', 'for one write kernel in one process: the highest minus the lowest total of its 4 intervals.'),` | Entry for the spread in B10: for one write kernel in one process, the highest minus the lowest total of its 4 intervals. |
| 1736 | `    ('Controls (B10)', 'three values from asm write and asm write 2: the control of the spread, of the total, and of the rate of each mesh.'),` | Entry for the controls in B10: three values from asm write and asm write 2, for the spread, for the total and for the rate of each mesh. |
| 1737 | `    ('Cell (B10), counted process', 'a cell is one kernel in one setting. A process counts for H11 only if its highest and lowest total differ by more than the control of the total.'),` | Entry for a cell and a counted process in B10: a cell is one kernel in one setting. A process counts for H11 only if its highest and lowest total differ by more than the control of the total. |
| 1738 | `    ('Level (of write totals), gap', 'the run of 2026-11-13 gave write totals in separate groups, called levels. The gap is the distance between two neighbouring totals of one kernel in one setting.'),` | Entry for the levels of the write totals and for the gap: the run of 2026-11-13 gave write totals in separate groups, called levels. The gap is the distance between two neighbouring totals of one kernel in one setting. |
| 1739 | `    ('Group (C3)', 'one setting and one sequence.'),` | Entry for a group in C3: one setting and one sequence. |
| 1740 | `    ('Irregular interval, late, end skew', 'a thread is late if it starts more than 100 µs after the common start. The end skew is the latest end minus the earliest end of the threads. An interval is irregular if a thread is late or if the end skew with the common stop is above 5 ms.'),` | Entry for irregular interval, late and end skew. A thread is late if it starts more than 100 microseconds after the common start. The end skew is the latest end minus the earliest end of the threads. An interval is irregular if a thread is late, or if the end skew with the common stop is above 5 ms. |
| 1741 | `    ('Page state, P row', 'how many bytes of a buffer are on 2 MiB pages (huge-page coverage), read from <code>/proc/self/smaps</code> and printed in a P row.'),` | Entry for the page state and the P row: how many bytes of a buffer are on 2 MiB pages, read from the file `/proc/self/smaps` and printed in a P row. |
| 1742 | `    ('I row, T row, C row', 'output rows of <code>bwx</code>. I: one per interval. T: one per thread and interval, with bytes and times. C: one per thread and interval with the counter values.'),` | Entry for the I, T and C rows of `bwx`. I: one per interval. T: one per thread and interval with bytes and times. C: one per thread and interval with the counter values. |
| 1743 | `    ('Counter, cycles, refill, last-level read miss', 'a counter is a hardware event counter of one core. Cycles are clock ticks of the core. L1 and L2 are the first and the second cache level of a core. An L1 or L2 refill is a line that this cache level had to fetch. A last-level read miss is a read that the last cache level did not hold.'),` | Entry for the counter words: a counter is a hardware event counter of one core, cycles are clock ticks of the core, L1 and L2 are the first and the second cache level of a core, a refill is a line that a cache level had to fetch, and a last-level read miss is a read that the last cache level did not hold. |
| 1744 | `    ('Line', '64 B, the unit of a cache.'),` | Entry for a line: 64 B, the unit of a cache. |
| 1745 | `    ('Clock', 'cycles of an interval divided by the CPU time of the thread in that interval, in GHz.'),` | Entry for the clock: the cycles of an interval divided by the CPU time of the thread in that interval, in GHz. |
| 1746 | `    ('CPU time', 'the time for which a thread really ran on its CPU (the thread CPU clock of Linux).'),` | Entry for the CPU time: the time for which a thread really ran on its CPU, from the thread CPU clock of Linux. |
| 1747 | `    ('Load, runnable tasks, <code>waited_s</code>, logins', 'the Linux 1-minute load average (average count of tasks that run or wait to run), the count of tasks that can run at one moment, the seconds the script waited for an idle system before a launch, and the count of logged-in users.'),` | Entry for the load words: the load average of the last minute, the number of tasks that can run at one moment, the seconds that the script waited for an idle system before a launch (`waited_s`), and the number of logged-in users. |
| 1748 | `    ('<code>ps</code>, <code>kworker</code>, <code>systemd</code>, <code>rcu_preempt</code>', '<code>ps</code> is the Linux tool that lists processes. The others are service tasks of the operating system.'),` | Entry for `ps` and three names from its lists: `ps` is the Linux tool that lists processes, and `kworker`, `systemd` and `rcu_preempt` are service tasks of the operating system. |
| 1749 | `    ('UTC', 'Coordinated Universal Time. All times of this page are in UTC.'),` | Entry for UTC. The text says that all times of the page are in UTC. |
| 1750 | `    ('B7', 'step: the four read kernels at 64+56 threads in all 8 settings, and the reproduction condition with one kernel per process.'),` | Entry for step B7: the four read kernels at 64+56 threads in all 8 settings, and the reproduction condition with one kernel per process. |
| 1751 | `    ('B10', 'step: the four write kernels at 64+56 threads in 8 settings, with 0.5 s and 15 s as the two intervals.'),` | Entry for step B10: the four write kernels at 64+56 threads in 8 settings, with 0.5 s and 15 s as the two intervals. |
| 1752 | `    ('B8', 'step: old read, asm read and asm read 2 at 64 threads on mesh 0 and 32 to 56 threads on mesh 1.'),` | Entry for step B8: old read, asm read and asm read 2 with 64 threads on mesh 0 and 32 to 56 threads on mesh 1. These thread counts are typed. They are not taken from the input. |
| 1753 | `    ('B5', 'step: old read against new read, <code>read_sparse</code>, the four <code>nop</code> variants and asm read at 64+56 threads.'),` | Entry for step B5: old read against new read, `read_sparse`, the four `nop` variants and asm read, at 64+56 threads. |
| 1754 | `    ('B9', 'step: old read with one buffer and with two buffers per thread.'),` | Entry for step B9: old read with one buffer and with two buffers per thread. |
| 1755 | `    ('C3', 'step: the sequences of B7 and B5 with core counters.'),` | Entry for step C3: the sequences of B7 and B5 with core counters. |
| 1756 | `    ('D1', 'step of Part D: counters of the mesh (the network that joins the cores and the memory), which need root. Not run.'),` | Entry for step D1 of Part D: the counters of the mesh, the network that joins the cores and the memory. They need root. The text says that the step was not run. |
| 1757 | `    ('H7a', 'hypothesis: a part of the difference is made by the stop method and the short interval.'),` | Entry for H7a: a part of the difference is made by the stop method and the short interval. |
| 1758 | `    ('H7b', 'hypothesis: a part of the difference is made by the common start.'),` | Entry for H7b: a part of the difference is made by the common start. |
| 1759 | `    ('H8', 'hypothesis: with threads on both meshes the chip has two states. A loop that only loads reaches the uniform state at a lower thread count than old read.'),` | Entry for H8: with threads on both meshes the chip has two states, and a loop that only loads reaches the uniform state at a lower thread count than old read. |
| 1760 | `    ('H9a', 'hypothesis: the second buffer per thread moved old read to the uniform pattern on 2026-10-30.'),` | Entry for H9a: the second buffer per thread moved old read to the uniform pattern on 2026-10-30. |
| 1761 | `    ('H9b', 'hypothesis: the pattern of old read differs between days or sessions for a reason other than the kernel.'),` | Entry for H9b: the pattern of old read differs between days or sessions for a reason other than the kernel. |
| 1762 | `    ('H10', 'hypothesis: in the uniform state the memory system fetches lines that the loop does not consume.'),` | Entry for H10: in the uniform state the memory system fetches lines that the loop does not consume. |
| 1763 | `    ('H11', 'hypothesis: the write totals differ because the threads of one mesh run faster in some intervals.'),` | Entry for H11: the write totals differ, and the cause is that the threads of one mesh run faster in some intervals. |
| 1764 | `    ('H3b', 'hypothesis of question Q1: the physical address of the pages decides the level at 8 MiB.'),` | Entry for H3b, a hypothesis of question Q1: the physical address of the pages decides the level at 8 MiB. |
| 1765 | `    ('The five words', 'rule 11 of the plan. "rejected": the bounded prediction failed in both sessions. "not rejected". "not observed": an event that the test could have shown did not occur. "not resolved": the difference is inside the A/A spread, or the rule cannot be applied. "not tested".'),` | Entry for the five words of rule 11 of the plan, each with its meaning: `rejected`, `not rejected`, `not observed`, `not resolved` and `not tested`. |
| 1766 | `    ('Fail, hold, described', 'results of one session. "fail": the bounded prediction failed in that session. "hold": it held. "described": the session gives values and no decision.'),` | Entry for the results of one session: `fail` (the bounded prediction failed in that session), `hold` (it held) and `described` (the session gives values and no decision). |
| 1767 | `    ('Open for the user', 'a judgment between two readings of a rule. This page prints both readings and does not choose.'),` | Entry for `open for the user`: a judgment between two readings of a rule. The page prints both readings and does not choose. |
| 1768 | `    ('Supported, contradicted', 'the words of the plan for B8 and for one cell of H11 in one session. For a word over the sessions this page writes "not rejected" and "rejected" and adds the word of the plan in brackets.'),` | Entry for `supported` and `contradicted`: the words of the plan for B8 and for one cell of H11 in one session. For a word over the sessions the page writes `not rejected` and `rejected` and adds the word of the plan in brackets. |
| 1769 | `]` | Ends the list `WORDS`. |

### `short_version`: the three sentences at the top of the page (lines 1772 to 1795)

| Line | Source | Explanation |
|---:|---|---|
| 1772 | `def short_version(m):` | Starts the function `short_version`. |
| 1773 | `    """At most three sentences, built from computed values. No hypothesis label: the list under the box gives the words."""` | Description of `short_version`: at most three sentences, built from computed values. They hold no hypothesis label. The list under the box gives the words. |
| 1774 | `    h = {x['label']: x for x in m['hyp']}` | `h`: the rows of the hypothesis table by their label. |
| 1775 | `    ss = [s for s in m['sessions'] if 'B7' in m['S'][s]]` | `ss`: the sessions that have B7. |
| 1776 | `    if not ss:` | Tests whether no session has B7. |
| 1777 | `        return f'{ID}: the input holds no process of step B7, so the difference between the old and the new read loop at 64+56 threads cannot be described.'` | Then the text starts with `Insufficient data` and says that the input holds no process of step B7, so the difference between the old and the new read loop at 64+56 threads cannot be described. |
| 1778 | `    sets = [(s, v) for s in ss for v in m['S'][s]['B7']['res']['settings'].values()]` | `sets`: every setting of B7 of every session, with its result from the analysis. |
| 1779 | `    nres = sum(1 for _, v in sets if v['decision'] == 'resolved' and v['sign'] == 1)` | `nres`: the number of them in which D is resolved with a positive sign, so with old read above new read. |
| 1780 | `    md = [v['metrics']['M_hist']['median_D'] for _, v in sets if v['metrics']['M_hist']['median_D'] is not None]` | `md`: the median D with `M_hist` of every setting of every session that has one. |
| 1781 | `    nset = max(len(m['S'][s]['B7']['res']['settings']) for s in ss)` | `nset`: the largest number of settings that a session has. |
| 1782 | `    where = (f"in all {nset} timing settings of {'both sessions' if len(ss) == 2 else pl(len(ss), 'session', 'sessions')}" if nres == len(sets) else f'in {nres} of {len(sets)} timing settings')` | `where`: the words on the settings. When D is resolved with old read above in every setting, they say `in all` with `nset` and the number of sessions (`both sessions` for two). If not, they give `nres` out of the number of settings over all sessions. |
| 1783 | `    s1 = (f"With 120 threads on the test server CRB (64 on one half of the chip and 56 on the other, each reading its own 256 MiB buffer), "` | `s1`: the first sentence. This line: typed words on the test: 120 threads on the test server CRB, 64 on one half of the chip and 56 on the other, each reading its own 256 MiB buffer. These numbers are not read from the input. |
| 1784 | `          f"the old read loop moved {rng(md, 1)} GB/s more in total than the new read loop {where}.")` | Continues the sentence: the old read loop moved more in total than the new read loop, by the range of `md` in GB/s with 1 decimal, followed by the words of `where`. |
| 1785 | `    ch = [(s, c) for s in ss for c in m['S'][s]['B7']['res']['changes'].values() if c['metrics']['M_hist']['change'] is not None]` | `ch`: every comparison of two settings of B7 that has a value, with its session. |
| 1786 | `    s2 = ''` | `s2`: the second sentence, empty at first. |
| 1787 | `    if ch:` | The next four lines run only when there is a comparison. |
| 1788 | `        bs, bc = max(ch, key=lambda t: abs(t[1]['metrics']['M_hist']['change']))` | `bs` and `bc`: the session and the comparison with the largest absolute change of D. |
| 1789 | `        mD = med([v['metrics']['M_hist']['median_D'] for v in m['S'][bs]['B7']['res']['settings'].values()])` | `mD`: the median over the settings of that session of the median D. |
| 1790 | `        s2 = (f" The largest change of that difference between two timing methods (stop rule, interval length or start position) was {fx(abs(bc['metrics']['M_hist']['change']))} GB/s "` | The second sentence: the largest change of the difference between two timing methods, as an absolute value in GB/s. The timing methods are named in brackets: stop rule, interval length or start position. |
| 1791 | `              f"({fx(abs(bc['metrics']['M_hist']['change']) / abs(mD) * 100, 1)} % of the difference)" + (', so no timing method removed it.' if nres == len(sets) else '.'))` | Continues the sentence: that change in % of `mD`, with 1 decimal. When D is resolved with old read above in every setting, the sentence ends with the words that no timing method removed the difference. |
| 1792 | `    s3 = (' The cause inside the chip is not tested, because the counters that need root were not run.' if h['H10']['word'] == 'not tested' else '')` | `s3`: the third sentence: the cause inside the chip is not tested, as the counters that need root were not run. It is added when the word of H10 is `not tested`. Line 691 gives H10 that word in every case. |
| 1793 | `    return s1 + s2 + s3` | Returns the three sentences as one text. |

### `build`: the whole page (lines 1796 to 1866)

| Line | Source | Explanation |
|---:|---|---|
| 1796 | `def build(m, banner=None):` | Starts the function `build`. It writes the whole HTML page from the model `m`. `banner` is an optional notice text. |
| 1797 | `    R = make_refs(m)` | `R`: the object with all reference definitions. |
| 1798 | `    one = len(m['sessions']) < 2` | `one`: true when the page has fewer than 2 sessions. |
| 1799 | `    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',` | `o`: the list of the HTML pieces of the page. The first piece starts the document: the document type, the language English, the character set UTF-8, and a setting that fits the page width to small screens. |
| 1800 | `         '<title>Parts B and C, question Q2: result</title>', f'<style>{CSS} h4{{font-size:14px;margin:22px 0 6px}} table.sm{{font-size:12px}} table.sm td,table.sm th{{padding:4px 5px}} '` | The page title, and the start of the style block: the style text `CSS` of the Part A page, then rules of this page. CSS is the language that sets the look of an HTML page. This line: headings of level 4 get 14 px, and tables of the class `sm` get 12 px text and smaller cell margins. |
| 1801 | `         'table.wr td,table.hy td{white-space:normal} table.wr td:first-child{min-width:190px} table.wr td:nth-child(2){white-space:nowrap} table.hy td:first-child{min-width:110px} table.hy td:nth-child(2){min-width:80px} table.hy td:nth-child(3){min-width:120px} table.hy td:nth-child(4){min-width:290px} table.hy td:nth-child(5){min-width:220px} table.hr td{white-space:normal} table.hr td:nth-child(2){min-width:250px} table.hr td:nth-child(4){min-width:170px} ul.words{columns:2;column-gap:28px;font-size:13px} ul.words li{break-inside:avoid}</style></head><body>']` | Continues the style block: the cells of the tables of the classes `wr`, `hy` and `hr` may break their text, and some of their columns get a smallest width. The word list is set in 2 columns with 13 px text, and an entry is not split between the columns. The line also ends the head of the document and opens its body. |
| 1802 | `    if banner:` | The next line runs only when a banner text was given. |
| 1803 | `        o.append(f'<p class="banner">{e(banner)}</p>')` | Adds the escaped banner text as a paragraph of the class `banner`. The page style gives it a border and bold text. |
| 1804 | `    o.append('<h1>Parts B and C, question Q2: 64+56 threads at 256 MiB</h1>')` | Adds the main heading: Parts B and C, question Q2, 64+56 threads at 256 MiB. |
| 1805 | `    o.append(f'<p class="take"><b>Short version.</b> {short_version(m)}</p>')` | Adds a highlighted paragraph with the bold words `Short version.` and the text of `short_version`. |
| 1806 | `    o.append('<p>The result per hypothesis in one line each. The section "Result per hypothesis" gives the basis.</p>' + hyp_bullets(m))` | Adds a sentence that introduces the list of the hypotheses, and then the list of `hyp_bullets` with one line per hypothesis. |
| 1807 | `    o.append(f'<p>Question Q2 comes from the benchmark run of 2026-11-13 {R("plan")}. With 120 threads, old read totalled 464 to 467 GB/s. New read totalled 280 to 304 GB/s. The write kernels gave several separate totals. '` | Adds a paragraph on the origin of Q2, with a citation of the plan. Its numbers are typed: with 120 threads old read totalled 464 to 467 GB/s and new read 280 to 304 GB/s in the benchmark run of 2026-11-13, and the write kernels gave several separate totals. The plan gives the two ranges with 2 decimals in its item Q2a [Ref1]. |
| 1808 | `             f'This page gives the results of the steps B7, B10, B8, B5, B9 and C3 for that question. The decision rules are those of the handoff, applied by the analysis script {R("handoff", "analyze")}.</p>')` | Continues the paragraph: the page gives the results of the six steps for that question, and the decision rules are those of the handoff, applied by the analysis script. |
| 1809 | `    parts = []` | `parts`: the sentences on the input, empty at first. |
| 1810 | `    for s in m['sessions']:` | Loop over the sessions. |
| 1811 | `        nf, st = len(m['folders'][s]), m['S'][s]['steps']` | `nf`: the number of result folders of Q2 of the session. `st`: its steps with a result. |
| 1812 | `        two = sorted({folder_step(x).rstrip('ab') for x in m['folders'][s] if folder_step(x)[-1:] in 'ab' and folder_step(x)[:-1] in STEPS})` | `two`: the steps of Q2 that have a folder whose step part ends with the letter `a` or `b`, such as `B10a` and `B10b` for B10. |
| 1813 | `        parts.append(f"Session {e(s)} has {pl(nf, 'result folder', 'result folders')} for {pl(len(st), 'step', 'steps')} ({', '.join(st) or 'no step of Q2'})" + (f". {join_and(two)} has two folders" if two and nf > len(st) else '') + '.')` | Adds a sentence: how many result folders the session has for how many steps, with the step names. When there are more folders than steps, it adds which step has two folders. |
| 1814 | `    t = '<p>Input: ' + ' '.join(parts)` | `t`: a paragraph that starts with the word `Input:` and these sentences. |
| 1815 | `    miss = [(s, st) for s in m['sessions'] for st in STEPS if st not in m['S'][s]]` | `miss`: every pair of session and step for which the session has no data. |
| 1816 | `    t += (' No step is missing.' if not miss else ' Missing: ' + ', '.join(f'{st} in session {e(s)}' for s, st in miss) + '.')` | Adds the sentence that no step is missing, or the list of the missing steps with their sessions. |
| 1817 | `    if one:` | The next line runs only with one session. |
| 1818 | `        t += ' The page holds one session. Every "rejected" is impossible with one session, because rule 11 of the plan needs both sessions.'` | Adds two sentences: the page holds one session, and every `rejected` is impossible then, as rule 11 of the plan needs both sessions. |
| 1819 | `    o.append(t + '</p>')` | Adds the paragraph. |
| 1820 | `    o.append('<h2 id="words">Words used here</h2><ul class="words">' + ''.join(f'<li><b>{k}</b>: {v}</li>' for k, v in WORDS) + '</ul>')` | Adds the section `Words used here`: a heading of level 2 with the anchor name `words`, and a list with one item per entry of `WORDS`, the term in bold. |
| 1821 | `    o += [sec_hyp(m, R), sec_facts(m, R), sec_load(m, R), sec_integrity(m, R)]` | Adds four sections: the result per hypothesis, the decisions and settings, the system load, and the processes used. |
| 1822 | `    o.append('<h2 id="b7">B7: old read against new read in 8 timing settings</h2>'` | Starts the section of B7: a heading of level 2 with the anchor name `b7`. It names old read against new read in 8 timing settings. |
| 1823 | `             f'<p>Each process runs old read, new read, asm read and asm read 2 in alternating order on the same buffers, 2 rounds. D is one value per process {R("handoff")}. '` | Continues with a typed paragraph: each process runs old read, new read, asm read and asm read 2 in alternating order on the same buffers, in 2 rounds. D is one value per process. |
| 1824 | `             'The last row of each chart and table has one kernel per process. Its process value is the median total of the 3 intervals of a process. Its D is the median of old read minus the median of new read. '` | Continues the paragraph: the last row of each chart and table has one kernel per process. Its process value is the median total of the 3 intervals of a process, and its D is the median of old read minus the median of new read. |
| 1825 | `             f'Its A/A value is the median of asm read 2 minus the median of asm read {R("handoff")}. The 2 % check applies to whole passes only: an interval fails if a thread ran fewer than 50 passes {R("plan")}.</p>'` | Continues the paragraph: its A/A value is the median of asm read 2 minus the median of asm read (line 1243 gives the rule of the analysis, which takes the absolute value). The 2 % check applies to whole passes only: an interval fails if a thread ran fewer than 50 passes. |
| 1826 | `             + per_session(m, 'B7', b7_block(R), 'A run of step B7 would give D and its A/A spread.'))` | Continues the statement: the B7 block of each session. The last argument is the sentence for a session without B7. |
| 1827 | `    o.append('<h2 id="b10">B10: the write kernels in 8 timing settings</h2>'` | Starts the section of B10: a heading of level 2 with the anchor name `b10`. It names the write kernels in 8 timing settings. |
| 1828 | `             f'<p>Each process runs old write, new write, asm write and asm write 2, 2 rounds. Every kernel has 4 intervals per process and 16 per setting {R("handoff")}. '` | Continues with a typed paragraph: each process runs the four write kernels in 2 rounds. Every kernel has 4 intervals per process and 16 per setting. |
| 1829 | `             'A mesh "has changed" only if its change between the highest and the lowest interval of a process is larger than the control of that mesh. '` | Continues the paragraph: a mesh has changed only if its change between the highest and the lowest interval of a process is larger than the control of that mesh. |
| 1830 | `             'H11 is "supported" for one kernel in one setting if three things hold in every counted process. Exactly one mesh has changed. It has risen. It is the same mesh in every counted process. '` | Continues the paragraph: H11 is supported for one kernel in one setting if three things hold in every counted process: exactly one mesh has changed, it has risen, and it is the same mesh in every counted process. |
| 1831 | `             f'With fewer than 2 counted processes the result is "not observed" {R("handoff")}.</p>'` | Continues the paragraph: with fewer than 2 counted processes the result is `not observed`. |
| 1832 | `             + per_session(m, 'B10', b10_block(R), 'A run of step B10 would give the totals of the write kernels.'))` | Continues the statement: the B10 block of each session. |
| 1833 | `    o.append('<h2 id="b8">B8: q and thread rates against the count of mesh-1 threads</h2>'` | Starts the section of B8: a heading of level 2 with the anchor name `b8`. It names q and the thread rates against the count of mesh-1 threads. |
| 1834 | `             f'<p>H8 is worded with a count of mesh-1 threads at which the pattern changes. The handoff finds that count from the labels split and uniform {R("handoff")}. The labels are not used, so the result for H8 is "not resolved" (page rule 1). '` | Continues with a typed paragraph: H8 is worded with a count of mesh-1 threads at which the pattern changes, the handoff finds that count from the labels, and the labels are not used. So the result for H8 is `not resolved` (page rule 1). |
| 1835 | `             'In the charts, lines join the medians of the intervals of one count, and small dots are the single intervals. Printed values are medians. The value at the last count stands in the label at the end of each line.</p>'` | Continues the paragraph on how to read the charts: lines join the medians of the intervals of one count, small dots are the single intervals, printed values are medians, and the value at the last count stands in the label at the end of each line. |
| 1836 | `             + per_session(m, 'B8', b8_block(R), 'A run of step B8 would give q per thread count.'))` | Continues the statement: the B8 block of each session. |
| 1837 | `    o.append('<h2 id="b5">B5: read variants against old read</h2>' + b5_intro(m, R)` | Starts the section of B5: a heading of level 2 with the anchor name `b5`, and the text of `b5_intro`. |
| 1838 | `             + per_session(m, 'B5', b5_block(R), 'A run of step B5 would give the totals of the variants.'))` | Continues the statement: the B5 block of each session. |
| 1839 | `    o.append('<h2 id="b9">B9: old read with one buffer and with two buffers per thread</h2>'` | Starts the section of B9: a heading of level 2 with the anchor name `b9`. It names old read with one buffer and with two buffers per thread. |
| 1840 | `             f'<p><b>Decision.</b> H9a predicts the label uniform with two buffers and the label split with one. The labels are not used, so the result for H9a is "not resolved" (page rule 1). '` | Continues with a typed paragraph that starts with the bold word `Decision.`: H9a predicts the label uniform with two buffers and the label split with one. The labels are not used, so the result for H9a is `not resolved` (page rule 1). |
| 1841 | `             f'The comparison of the totals needs no label, and it is a description. Its A/A value is the largest difference between two processes of one kind {R("devs")}.</p>'` | Continues the paragraph: the comparison of the totals needs no label and is a description. Its A/A value is the largest difference between two processes of one kind. |
| 1842 | `             + per_session(m, 'B9', b9_block(R), 'A run of step B9 would give the comparison.'))` | Continues the statement: the B9 block of each session. |
| 1843 | `    o.append('<h2 id="c3">C3: core counters per kernel and mesh</h2>'` | Starts the section of C3: a heading of level 2 with the anchor name `c3`. It names the core counters per kernel and mesh. |
| 1844 | `             f'<p>A C row is not used if its counter group did not run for the whole enabled time {R("handoff")}. The charts and the table give medians over the threads of one mesh. One group is one setting and one sequence. A chart has one marker per group. Its right column gives the median of the group medians for mesh 0 and for mesh 1, in the unit of the panel. '` | Continues with a typed paragraph: a C row is not used if its counter group did not run for the whole enabled time. The charts and the table give medians over the threads of one mesh. One group is one setting and one sequence, and a chart has one marker per group. The right column of a chart gives the median of the group medians for mesh 0 and for mesh 1. |
| 1845 | `             f'The CPU time of a thread exists only in runs with counters. A run without counters does not mark a thread that lost its CPU inside an interval. This was found in the short run {R("short")}.</p>'` | Continues the paragraph: the CPU time of a thread exists only in runs with counters, so a run without counters does not mark a thread that lost its CPU inside an interval. The typed text says that this was found in the short run, and cites its folder. |
| 1846 | `             + per_session(m, 'C3', c3_block(R), 'A run of step C3 would give the counters.'))` | Continues the statement: the C3 block of each session. |
| 1847 | `    o.append(sec_h10_h9b(m, R))` | Adds the section on H10 and H9b. |
| 1848 | `    T = m['timing']` | `T`: the times of the sessions from `timing_model`. |
| 1849 | `    o.append('<h2 id="limits">Limits of this page</h2><ul>'` | Starts the section `Limits of this page`: a heading of level 2 with the anchor name `limits`, and a list. |
| 1850 | `             + (f'<li>The sessions are one continuous run of one night. Session {e(T["gaps"][0][1])} started {hm(T["gaps"][0][2])} after session {e(T["gaps"][0][0])} ended. No result of this page says anything about another day or about the state after a restart.</li>' if T['gaps'] and T['gaps'][0][2] < 3600 else '')` | First list item, added only when the first gap between two sessions is shorter than 3600 s: the sessions are one continuous run of one night, with the gap in the words of `hm`. No result of the page says anything about another day or about the state after a restart. |
| 1851 | `             + f'<li>No value on this page is the traffic of the time in which all threads ran. A thread records only its total, so the bytes of the common time are not measured {R("handoff")}. Rule 6 of the plan is met only in part.</li>'` | Typed list item: no value on the page is the traffic of the time in which all threads ran. A thread records only its total, so the bytes of the common time are not measured, and rule 6 of the plan is met only in part. |
| 1852 | `             f'<li>The page state of an interval with many threads is the reading taken after the interval before it. A change during the warm-up pass shows only in the next reading {R("handoff")}.</li>'` | Typed list item: the page state of an interval with many threads is the reading taken after the interval before it. A change during the warm-up pass shows only in the next reading. |
| 1853 | `             f'<li>A thread that loses its CPU inside an interval is not marked in a run without counters {R("short")}. Only C3 has the CPU time of each thread.</li>'` | Typed list item: a thread that loses its CPU inside an interval is not marked in a run without counters. Only C3 has the CPU time of each thread. |
| 1854 | `             f'<li>With 120 threads the main thread of <code>bwx</code> has no CPU of its own. It shares a CPU with a worker {R("devb")}. {ID}: the size of this effect on CRB. A run with the main thread on a spare CPU would give it, and the rules of the host allow CPUs 0 to 119 only.</li>'` | Typed list item: with 120 threads the main thread of `bwx` has no CPU of its own and shares a CPU with a worker. The size of this effect on CRB is marked `Insufficient data`. A run with the main thread on a spare CPU would give it, and the rules of the host allow the CPUs 0 to 119 only. |
| 1855 | `             f'<li>The loop of <code>read_sparse</code> starts at 4 modulo 64, and the other asm read loops start at 20 {R("offsets", "devb")}. So B5 compares <code>read_sparse</code> at another loop offset.</li>'` | Typed list item: the loop of `read_sparse` starts at 4 modulo 64 and the other asm read loops at 20, so B5 compares `read_sparse` at another loop offset. The two numbers are typed here. `b5_intro` reads the same offsets from the offsets file (lines 1571 to 1576). |
| 1856 | `             f'<li>Part D (root counters, physical pages) was not run. So H3b of question Q1 is "not tested", and H10 is "not tested" {R("plan")}.</li>'` | Typed list item: Part D (root counters, physical pages) was not run. So H3b of question Q1 and H10 are `not tested`. |
| 1857 | `             f'<li>The limits 100 µs and 5 ms for an irregular interval are provisional {R("handoff")}.</li>'` | Typed list item: the limits of 100 microseconds and 5 ms for an irregular interval are provisional. |
| 1858 | `             '<li>The decisions use many comparisons of two settings. No correction for the number of comparisons is made.</li>'` | Typed list item: the decisions use many comparisons of two settings, and no correction for the number of comparisons is made. |
| 1859 | `             + (f'<li>One session only. Every result is the result of that session. "rejected" needs a second session {R("plan")}.</li>' if one else '')` | List item added only with one session: every result is the result of that session, and `rejected` needs a second session. |
| 1860 | `             + f'<li>{ID}: load readings during an interval. The script reads the load only before each launch.</li>'` | List item that starts with `Insufficient data`: load readings during an interval. The script reads the load only before each launch. |
| 1861 | `             '<li>The chart colours were not checked with the palette checker of the chart rules, because Node.js is not installed on the machine where this page was built. Every chart also uses position, marker shape or a text label.</li></ul>')` | Typed list item: the chart colors were not checked with the palette checker of the chart rules, as Node.js was not installed on the machine where the page was built. Every chart also uses position, marker shape or a text label. The line closes the list. |
| 1862 | `    o.append('<h2 id="refs">References</h2><ul>' + ''.join(f'<li>[Ref{i}] {t}</li>' for i, t in enumerate(R.items, 1)) + '</ul></body></html>')` | Adds the last piece: the section `References` with the anchor name `refs`. It lists every cited reference with its number, in the order of the first citations, and closes the document. |
| 1863 | `    body = tidy_refs('\n'.join(o[:-1]))` | `body`: all pieces except the reference list, joined and passed through `tidy_refs`. |
| 1864 | `    return body + '\n' + o[-1]` | Returns the page: `body`, a line break, and the reference list. |

### `main`: the command line (lines 1867 to 1889)

| Line | Source | Explanation |
|---:|---|---|
| 1867 | `def main(argv=None):` | Starts the function `main`. `argv` is the list of arguments. With `None` the arguments of the command line are used. |
| 1868 | `    ap = argparse.ArgumentParser(description='result page of Q2 (steps B7, B10, B8, B5, B9, C3)')` | `ap`: the reader of the command line, with a short description of the script. |
| 1869 | `    ap.add_argument('--session', nargs='+', action='append', required=True, metavar=('NAME', 'FOLDER'))` | Defines the option `--session`. It is required and may be given several times. Each use takes one or more values: the session name and then its folders. |
| 1870 | `    ap.add_argument('-o', '--out', default='partB-q2-result.html')` | Defines the option `-o` or `--out`: the name of the page to write. Without it the name is `partB-q2-result.html` in the working folder. |
| 1871 | `    ap.add_argument('--banner')` | Defines the option `--banner`: a notice text for the top of the page. |
| 1872 | `    ap.add_argument('--offsets', default=OFFSETS)` | Defines the option `--offsets`: the path of the offsets file, by default `OFFSETS` (line 40). |
| 1873 | `    a = ap.parse_args(argv)` | `a`: the values of the options. An error in the arguments ends the script here with a message. |
| 1874 | `    sp = {}` | `sp`: the folders per session name, empty at first. |
| 1875 | `    for s in a.session:` | Loop over the uses of `--session`. |
| 1876 | `        if len(s) < 2:` | Tests whether the option got fewer than 2 values. |
| 1877 | `            ap.error('--session needs a name and at least one folder')` | Then `ap.error` prints the usage and the message that `--session` needs a name and at least one folder. It ends the script with exit status 2. |
| 1878 | `        sp.setdefault(s[0], []).extend(s[1:])` | The first value is the session name. The other values are added to the folders of that name. Two uses of `--session` with the same name give one session. |
| 1879 | `    m = compute(sp, a.offsets)` | Builds the model from the folders and the offsets file. |
| 1880 | `    with open(a.out, 'w') as fh:` | Opens the output file for writing. An existing file with that name is replaced. |
| 1881 | `        fh.write(build(m, a.banner))` | Builds the page and writes it to the file. |
| 1882 | `    print('wrote', a.out)` | Prints `wrote` and the name of the page. |
| 1883 | `    for h in m['hyp']:` | Loop over the rows of the hypothesis table. |
| 1884 | `        print('  %-14s %s%s' % (h['label'], h['word'], ' (%s)' % h['plan_word'] if h['plan_word'] else ''))` | Prints one line per row: the label in a field of 14 characters, the word of the page, and the word of the plan in brackets when the row has one. |
| 1885 | `    return 0` | Returns 0. |
| 1888 | `if __name__ == '__main__':` | Tests whether the file was started as a script. The test is false when another file imports it, as `test_q2.py` does. |
| 1889 | `    sys.exit(main())` | Runs `main` and ends the script with its return value as the exit status. |

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
