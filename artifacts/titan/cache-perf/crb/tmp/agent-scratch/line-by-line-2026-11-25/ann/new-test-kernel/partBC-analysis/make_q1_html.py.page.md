## Short version: purpose

`make_q1_html.py` builds the HTML result page for question Q1 (one thread with a buffer of 8 MiB) of the test plan of 2026-11-13, from the result folders that the run script `run_bwx.sh` wrote for the runner `bwx`. It takes the words for the hypotheses H1, H3a, H4, H5 and H6 from the analysis script `analyze_bwx.py`, and it adds its own description of every process, with charts and tables. The generated page shows the measured rate differences per step and session beside the strict word of each decision rule, and it lists what stays open for the user.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Plan**: the test plan of 2026-11-13, the file `plan.md`. It holds two questions (Q1 and Q2), the hypotheses H1 to H11, 11 rules for the measurements, and the steps of its Parts A to D [Ref1].
- **Handoff note**: the file `handoff.md`, the instructions for the execution of the plan. Its section B.3 defines the result rows, section B.9 the sequence of each step, and section B.10 the numeric decision rules [Ref2].
- **Q1**: the first question of the plan: why one thread with a buffer of 8 MiB behaves differently from the other buffer sizes [Ref1].
- **Parts A to D of the plan**: Part A is a screening with the older benchmark binaries. Part B uses the runner `bwx`. Part C repeats steps of Part B with core counters. Part D needs root rights. On this page "Part C" always means this part of the plan.
- **Step**: one measurement of the plan with a name such as B1. The run script writes one result folder per step.
- **B1**: step: the kernels `copy` and `asmcopy` are compared inside one process, with the A/A pair `asmcopy2` and `asmcopy`, at buffer sizes of 4, 8, 16 and 32 MiB [Ref1].
- **B2**: step: as B1 at 8 MiB, with one of three assembly variants of the C copy loop in place of `copy` [Ref2].
- **B3**: step: as B1 at 8 MiB, in three more builds of the runner. Each build places the loops of `copy` and `asmcopy` at one loop offset: 0, 36 or 52 [Ref2].
- **B4**: step: one process times `asmread` 200 times on one buffer of 8 MiB, and the page state is read before every interval. Half of the processes run with the option `--no-thp` [Ref2].
- **B6**: step: `oldread` at 8 MiB and at 1 MiB in one process, with the A/A pair `oldread2` and `oldread` [Ref2].
- **C1, C2**: steps: the schedule of B4 and the schedule of B1 at 8 MiB, run with the option `--count`, which makes the runner read core counters [Ref2].
- **Level**: the word of the plan for one of two rates of a loop that only loads, at 8 MiB with one thread: the low level and the high level [Ref1].
- **Low, high, between**: the label of an `asmread` interval at 8 MiB. It is low for a rate below 69.0 GB/s and high for a rate above 70.5 GB/s. For a rate from 69.0 to 70.5 GB/s the analysis prints `changing` and the generated page prints "between". The plan calls the two limits provisional [Ref1][Ref4].
- **Copy difference**: the difference between the rate of the C copy kernel and the rate of the assembly copy kernel at 8 MiB with one thread. Question Q1b of the plan asks where it comes from, and H4, H5 and H6 are three answers [Ref1].
- **H1**: hypothesis: the old read kernel is limited inside the core at every cache size, and its rate at 8 MiB does not depend on the level [Ref1].
- **H2**: hypothesis: the low level can change to the high level while the loop runs, and the high level can stay for the next process [Ref1].
- **H3a**: hypothesis: huge-page coverage decides the level. The low level is a buffer that is not fully on pages of 2 MiB [Ref1].
- **H3b**: hypothesis: the physical address of the pages decides the level [Ref1].
- **H4**: hypothesis: the copy difference does not come from the kernel code. It comes from something that differs between processes [Ref1].
- **H5**: hypothesis: the copy difference comes from the instruction order of the C loop [Ref1].
- **H6**: hypothesis: the copy difference comes from the address of the loop [Ref1].
- **Bounded prediction**: the one statement of a hypothesis that a step tests, as the plan words it.
- **Session (of the plan)**: one run of all steps on CRB. The plan asks for at least 2 sessions some hours apart. The command line of this script gives each session a name, for example `s1`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Tag**: the name that the run script gives a process, for example `8M-cpu2-p1`.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Sequence, entry**: the sequence is the ordered list of kernels that one process times, one interval per entry. An entry is a kernel name. The entry `oldread@1M` runs the kernel `oldread` on the first 1 MiB of the buffer.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`oldread`, `oldread2`**: the old read kernel in the runner, and a second copy of the same source under another name. The generated page calls them "old read" and "old read 2".
- **`copy`, `asmcopy`, `asmcopy2`**: three copy kernels of the runner. `copy` is the C copy kernel, which the generated page calls "new C copy". `asmcopy` is the copy kernel written in assembly ("asm copy"). `asmcopy2` is a second copy of the source of `asmcopy` ("asm copy 2").
- **`asmcopy_c`, `asmcopy_c_add`, `asmcopy_c_reg`**: the three assembly variants of step B2. `asmcopy_c` has the machine code of the C copy loop. `asmcopy_c_add` has its two `add` instructions behind the 8 stores, as `asmcopy` has. `asmcopy_c_reg` uses the registers of `asmcopy` [Ref2].
- **Loop offset**: the address of the first instruction of a loop, as the remainder after a division by 64. 64 B is the size of one cache line.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`run_bwx.sh`**: the run script of Parts B and C. It starts one runner process after the other and writes one result folder per step [Ref5].
- **csv file of a step**: the file of a result folder that holds the output of all processes of the step, for example `B1.csv`. For each process it holds one header line and then the rows that the runner printed.
- **Header line**: the line that `run_bwx.sh` writes before the output of each process. It starts with `-- step` and holds the step, the tag, the binary, the wait `waited_s` in seconds, four load values behind the word `loadavg`, the number of logins, the UTC time and the arguments of the runner [Ref5].
- **Field**: one value of a row, between two commas. On this page fields are counted from 1, and the row letter is field 1.
- **`T` row**: one row per thread and interval. Field 7 is `bytes`, the bytes that the thread moved in the timed part. Field 8 is `elapsed_s`, the length of the timed part in seconds [Ref2][Ref6].
- **`I` row**: one row per interval with totals over the threads. This script takes no rate from it.
- **`P` row**: the page state of one buffer, read before an interval. Field 6 is `kB_total` and field 7 is `kB_huge`. Fields 10 and 11 are the system counters `thp_collapse_alloc` and `pgmigrate_success` of the file `/proc/vmstat` [Ref2].
- **`C` row**: one row per thread and interval of a process with `--count`. Field 7 is `enabled_ns`, field 8 is `running_ns`, field 9 is `cputime_ns` (the CPU time of the thread in the timed part), and one count per event follows [Ref2].
- **Rate of an interval**: for a process with one thread: field 7 of the `T` row divided by field 8 and by 1e9, in GB/s. Every process of a step of Q1 has one thread.
- **`env.txt`**: a file of the result folder that the run script writes once per step. Its first line holds the UTC time and the load at the start of the step. A line that starts with `## end` holds them at the end [Ref5].
- **`launches.txt`**: a file of the result folder with one block per launch: a line that starts with `==`, and then the 5 processes with the highest percent value of the tool `ps` [Ref5].
- **`stderr.txt`**: a file of the result folder with the error output of the runner.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Reference interval**: an interval of `asmread` at the buffer size of the process. In the sequences of B1, B2, B3, B6 and C2 one stands before and one behind every compared pair [Ref2].
- **Stable process**: a process whose reference intervals all have the label low, or all have the label high.
- **Pair, pair value**: a pair is two neighbouring intervals of two compared entries between the same two reference intervals. The pair value is the rate of the first-named entry minus the rate of the second, in GB/s [Ref2].
- **A/A pair, A/A spread**: an A/A pair is a pair of the two copies of one loop, for example `asmcopy2` and `asmcopy`. The A/A spread of a CPU is the largest absolute `e` of its processes. It shows how much two equal loops differ.
- **`d`, `e`**: the two values of one process. `d` is the median of its pair values of the two compared entries. `e` is the median of its A/A pair values.
- **Resolved**: the word of the plan for a difference whose absolute median is larger than the A/A spread and that has one sign in all processes [Ref1].
- **The five words**: the result words of rule 11 of the plan: "rejected" (the bounded prediction failed in both sessions), "not rejected", "not observed", "not resolved" and "not tested" [Ref1].
- **Flag of a session**: the result of one session for one hypothesis in `analyze_bwx.py`: `fail` (the bounded prediction failed), `hold`, `not observed` or `not resolved` [Ref3].
- **Description**: values that this script computes for all complete processes without the level labels. A description never changes a word of a rule.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **`--no-thp`**: an option of the runner. By the text of the generated page, the benchmark then asks for pages of 4 KiB ({L1698}).
- **Page state, huge-page coverage**: the page state is the content of a `P` row. The coverage is `kB_huge` of `kB_total`: how many kB of the buffer lie on pages of 2 MiB. It is "full" when the two are equal and "none" when `kB_huge` is 0.
- **Case (a), case (b)**: the two results of step B4 that contradict H3a. Case (a): one CPU has at least 10 low and at least 10 high intervals with full coverage. Case (b): the same with no huge page [Ref2].
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Per line**: a count divided by the number of lines of 64 B that the interval moved. That number is field 7 of the `T` row divided by 64.
- **Generated page**: the HTML file that this script writes. Its default name is `partB-q1-result.html`.
- **Typed text**: text that stands in the script as it is. The script does not compute it from the input.
- **`ab`, `pa`**: the short names under which this script imports `analyze_bwx.py` and `make_partA_html.py`.
- **`D`, `R`**: `D` is the dictionary with all computed values that `compute` returns. `R` is the reference list of the generated page, an object of the class `Refs`.
- **Dictionary**: the table type of Python. It maps a key to a value.
- **Docstring**: a text literal at the top of a Python file or function that describes it.
- **SVG, unit of the drawing**: SVG is a picture format that is written as text. A browser draws it. Sizes and positions are given in units of the drawing. At the full width of 900 units one unit is one pixel.
- **CSS**: the language that sets the look of an HTML page.
- **Tooltip**: a text that a browser shows when the mouse pointer is over an element.
- **UTC**: Coordinated Universal Time.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. When Python loads the file, it sets the paths of the helper modules, imports `analyze_bwx.py` and `make_partA_html.py`, and defines the constants: the seven steps, the two level limits of `decide.py`, the colors and the added style rules ({L20-54}).
2. `main` reads the command line: one `--session` per session with a name and its result folders, the output name, a banner text and the path of the file of loop offsets ({L1971-1982}).
3. `make` calls `load`. For every folder `load` scans the header lines of the csv files, lets `ab.load_session` parse the folders that hold a step of Q1, and reads `env.txt`, `launches.txt` and the size of `stderr.txt` ({L164-189}).
4. `compute` runs the decision analysis `ab.analyze` over all sessions. Then it computes the description of each session: `d` and `e` of every process per group, the level counts of the reference rates, the facts of the processes of B4, B6, C1 and C2, and the load readings ({L370-425}).
5. `hypotheses` builds one row per hypothesis from the words and flags of the analysis, with notes and with the items that stay open for the user ({L488-689}).
6. `build` stores the references and puts the page together in a fixed order: the Short version, the main numbers, the list "Words used here", the hypothesis table, the system load, the reference rate, the sections of B1, B2, B3, B4, B6 and of C1 with C2, the deviations, the limits and the references ({L1867-1948}).
7. `main` writes the page to the output file, prints one line with its length and one line per hypothesis, and returns 0 ({L1983-1989}).

## Behavior a reader must know

- Where a rate comes from: `analyze_bwx.py` computes every rate from a `T` row, as field 7 (`bytes`) divided by field 8 (`elapsed_s`) and by 1e9, in GB/s. It does not use the value `aggregate_GBps` of the `I` row [Ref3].
- What is timed: in a process of a step of Q1 the thread first runs one pass without timing (the warm-up pass) and reads the page state. A pass covers the range of the entry: the whole buffer, or its first 1 MiB for the entry `oldread@1M`. Then the thread reads the clock and runs whole passes. It reads the clock again after every 8 MiB of work, or after every pass of a larger range. The interval ends at the first of these readings at which the minimum time of the option `--min-ms` has passed. `bytes` counts the whole passes, and a copy pass counts twice, for the bytes read and the bytes written [Ref6].
- How values are combined: a pair value is the rate of the first-named entry minus the rate of the second. `d` and `e` are medians over the pairs of one process. Per CPU the script takes the median of `d` over the processes and the largest absolute `e` ({L205-241}). The page prints no median and no A/A spread over processes of different CPUs. Over the CPUs it gives only counts and ranges, for example the number of processes with `d` below 0 ({L1829}). In the tables each session keeps its own columns.
- Two sets of numbers stand side by side. The rule of `analyze_bwx.py` and `decide.py` uses only stable processes at 8 MiB [Ref3][Ref4]. The description of this script uses all complete processes. So the A/A spread of the description can differ from the A/A spread of the rule ({L228}, {L625-627}).
- The words of H1, H3a, H4, H5 and H6 come from the analysis. This script changes one thing in them: the long word of the analysis for one session becomes `not rejected` ({L428-433}). This script itself sets the word `not tested` in three cases: always for H2 ({L545}, {L549}), always for H3b ({L603}), and for a hypothesis that has no entry of the analysis, for example H1 in {L531}. No description changes a word.
- These limits are choices of this script and not of the plan: 0.2 GB/s for "near a level limit" ({L39}), 1 GB/s for a large step between two intervals ({L540}, {L1405}), 5 % of one CPU for a busy other process ({L1000}), a 1-minute load average above 2 tasks ({L982}), and 90 % of the A/A pairs for the position effect of B6 ({L473}).
- Only complete processes give rates and descriptions ({L377}). The load readings use all processes of a step, complete or not ({L325}). The section on the system load lists every process that was left out, with the reason ({L1011-1012}).
- The script stops with a Python error when a word of the hypothesis table is not one of the five words, or when an input of one session would give the word "rejected" ({L685-688}). An error of the parser of `analyze_bwx.py` stops it too. A wrong command line ends it with exit status 2 ({L1977}, {L1981}). After a page was written the exit status is 0.
- Some typed sentences state a result and are not computed from the input: that step B1 has no resolved difference at 8 MiB ({L1912}, {L1918}, {L1925}), that the design could give H4, H5 and H6 only "not observed" ({L1933}), that the position changes the rate of old read in B6 ({L1942}), that the measured difference of H1 depends on the loop before ({L1855}), and that all stable processes are stable low ({L502}). The docstring of the file says that every sentence that interprets data is computed ({L16}).
- Some typed sentences hold numbers of other runs: {L1241}, {L1653}, {L1686} and {L1939}. Three of them carry a citation of the generated page. The entry of {L1686} in the list `WORDS` carries none. With another input these numbers would not change.
- The docstring of `limits_fit` says the opposite of what the code does ({L1815}, {L1818}). The code and its one caller agree with each other.
- With one session whose flag for H3a is `fail`, the test of {L592} is true, and the box "Open for the user" gets the item of {L594-596}. Its typed words speak of two sessions.
- The entry of the list `WORDS` for the labels holds the two level limits as typed numbers ({L1688}). All other places print them from `decide.py` ({L34}).
- The paths of {L23-25} fit the working tree in which the script was written. In this repo `analyze_bwx.py` lies in the code folder `bwx-2026-11-13`, and the code folder has no folder `tmp`. So the import of {L29} works here only when that folder is on the module search path of Python in another way. The default of `--offsets` lies below the same missing folder ({L1976}). Without the file the generated page prints a block "Insufficient data" in place of the table of loop offsets ({L1952-1953}).
- The generated page has its own list of references. Each reference gets its number at its first use ({L98-106}), and the paths in it are the paths of the working tree of the author ({L1869-1877}). They are not the references of this explanation page.
- The generated page loads nothing from another place: the style sheet and all charts are part of the file. The style sheet sets a white background [Ref7].
- The test data hold a copy of this script and a page with the default output name [Ref10].

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/plan.md`: the test plan of 2026-11-13. Section "The two questions" (Q1 with Q1a, Q1b and Q1c), the table of the hypotheses, the rules 3, 4, 5, 10 and 11, and the tables of the steps B1 to B6 and C1, C2.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the handoff note. Section B.1 (the kernels of `bwx`), B.3 (the rows `I`, `T`, `P` and `C`), B.9 (the sequence and the options of each step) and B.10 (the numeric decision rules of the one-thread steps and of B4).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/analyze_bwx.py`: the parser (classes `Proc` and `Interval`) and the functions `pair_values`, `one_thread_group`, `coverage`, `a_copy`, `a_b4`, `a_b6`, `a_count`, `two_sessions`, `cross` and `analyze`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/decide.py`: the two level limits `LOW_MAX` and `HIGH_MIN`, and the functions `level`, `process_value`, `resolved`, `decide_one_thread` and `decide_b6_state`.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/run_bwx.sh`: the function `one` (the block of `launches.txt`, the header line and the launch), the function `settle` (the wait for at most 2 runnable tasks), the functions of the steps, and the lines that write `env.txt`.
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/bwx.c`: the function `worker` (warm-up pass, page state, clock readings, passes and counter readings) and the lines of `main` that print the rows.
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/partA-analysis/make_partA_html.py`: the style sheet `CSS`, the colors, and the functions `fx`, `fs`, `pl`, `svg_open`, `marker` and `place_label`.
- [Ref8] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-scripts.md`: the choices of the analysis that the generated page cites, points A12 to A16, A19, A20, A22, A30 and A32.
- [Ref9] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/offsets.tsv`: a file of loop offsets in the test data. Its first line names the six columns `binary`, `kernel`, `function`, `start`, `loop_start` and `loop_mod64`.
- [Ref10] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/partBC-20261114`: a folder of the test data. Its folder `scripts` holds copies of `make_q1_html.py` and `test_q1.py`. Check of 2026-11-25: the command `cmp` finds both equal to the files of the code folder. Its file `partB-q1-result.html` has the page title of this script, and its last caption names `make_q1_html.py` as the script that built it.
