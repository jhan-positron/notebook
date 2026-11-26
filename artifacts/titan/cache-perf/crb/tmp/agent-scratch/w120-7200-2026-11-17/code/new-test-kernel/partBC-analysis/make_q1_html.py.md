# `make_q1_html.py` explained, line by line

- Source file: `new-test-kernel/partBC-analysis/make_q1_html.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1993 lines, 152639 bytes).
- sha256 of the source when this page was built: `624e401ec528cbac38e90650cddffcd728ad3ded8a29eb36c39e403a98314145`.

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
- **`--no-thp`**: an option of the runner. By the text of the generated page, the benchmark then asks for pages of 4 KiB (line 1698).
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

1. When Python loads the file, it sets the paths of the helper modules, imports `analyze_bwx.py` and `make_partA_html.py`, and defines the constants: the seven steps, the two level limits of `decide.py`, the colors and the added style rules (lines 20 to 54).
2. `main` reads the command line: one `--session` per session with a name and its result folders, the output name, a banner text and the path of the file of loop offsets (lines 1971 to 1982).
3. `make` calls `load`. For every folder `load` scans the header lines of the csv files, lets `ab.load_session` parse the folders that hold a step of Q1, and reads `env.txt`, `launches.txt` and the size of `stderr.txt` (lines 164 to 189).
4. `compute` runs the decision analysis `ab.analyze` over all sessions. Then it computes the description of each session: `d` and `e` of every process per group, the level counts of the reference rates, the facts of the processes of B4, B6, C1 and C2, and the load readings (lines 370 to 425).
5. `hypotheses` builds one row per hypothesis from the words and flags of the analysis, with notes and with the items that stay open for the user (lines 488 to 689).
6. `build` stores the references and puts the page together in a fixed order: the Short version, the main numbers, the list "Words used here", the hypothesis table, the system load, the reference rate, the sections of B1, B2, B3, B4, B6 and of C1 with C2, the deviations, the limits and the references (lines 1867 to 1948).
7. `main` writes the page to the output file, prints one line with its length and one line per hypothesis, and returns 0 (lines 1983 to 1989).

## Behavior a reader must know

- Where a rate comes from: `analyze_bwx.py` computes every rate from a `T` row, as field 7 (`bytes`) divided by field 8 (`elapsed_s`) and by 1e9, in GB/s. It does not use the value `aggregate_GBps` of the `I` row [Ref3].
- What is timed: in a process of a step of Q1 the thread first runs one pass without timing (the warm-up pass) and reads the page state. A pass covers the range of the entry: the whole buffer, or its first 1 MiB for the entry `oldread@1M`. Then the thread reads the clock and runs whole passes. It reads the clock again after every 8 MiB of work, or after every pass of a larger range. The interval ends at the first of these readings at which the minimum time of the option `--min-ms` has passed. `bytes` counts the whole passes, and a copy pass counts twice, for the bytes read and the bytes written [Ref6].
- How values are combined: a pair value is the rate of the first-named entry minus the rate of the second. `d` and `e` are medians over the pairs of one process. Per CPU the script takes the median of `d` over the processes and the largest absolute `e` (lines 205 to 241). The page prints no median and no A/A spread over processes of different CPUs. Over the CPUs it gives only counts and ranges, for example the number of processes with `d` below 0 (line 1829). In the tables each session keeps its own columns.
- Two sets of numbers stand side by side. The rule of `analyze_bwx.py` and `decide.py` uses only stable processes at 8 MiB [Ref3][Ref4]. The description of this script uses all complete processes. So the A/A spread of the description can differ from the A/A spread of the rule (line 228, lines 625 to 627).
- The words of H1, H3a, H4, H5 and H6 come from the analysis. This script changes one thing in them: the long word of the analysis for one session becomes `not rejected` (lines 428 to 433). This script itself sets the word `not tested` in three cases: always for H2 (line 545, line 549), always for H3b (line 603), and for a hypothesis that has no entry of the analysis, for example H1 in line 531. No description changes a word.
- These limits are choices of this script and not of the plan: 0.2 GB/s for "near a level limit" (line 39), 1 GB/s for a large step between two intervals (line 540, line 1405), 5 % of one CPU for a busy other process (line 1000), a 1-minute load average above 2 tasks (line 982), and 90 % of the A/A pairs for the position effect of B6 (line 473).
- Only complete processes give rates and descriptions (line 377). The load readings use all processes of a step, complete or not (line 325). The section on the system load lists every process that was left out, with the reason (lines 1011 to 1012).
- The script stops with a Python error when a word of the hypothesis table is not one of the five words, or when an input of one session would give the word "rejected" (lines 685 to 688). An error of the parser of `analyze_bwx.py` stops it too. A wrong command line ends it with exit status 2 (line 1977, line 1981). After a page was written the exit status is 0.
- Some typed sentences state a result and are not computed from the input: that step B1 has no resolved difference at 8 MiB (line 1912, line 1918, line 1925), that the design could give H4, H5 and H6 only "not observed" (line 1933), that the position changes the rate of old read in B6 (line 1942), that the measured difference of H1 depends on the loop before (line 1855), and that all stable processes are stable low (line 502). The docstring of the file says that every sentence that interprets data is computed (line 16).
- Some typed sentences hold numbers of other runs: line 1241, line 1653, line 1686 and line 1939. Three of them carry a citation of the generated page. The entry of line 1686 in the list `WORDS` carries none. With another input these numbers would not change.
- The docstring of `limits_fit` says the opposite of what the code does (line 1815, line 1818). The code and its one caller agree with each other.
- With one session whose flag for H3a is `fail`, the test of line 592 is true, and the box "Open for the user" gets the item of lines 594 to 596. Its typed words speak of two sessions.
- The entry of the list `WORDS` for the labels holds the two level limits as typed numbers (line 1688). All other places print them from `decide.py` (line 34).
- The paths of lines 23 to 25 fit the working tree in which the script was written. In this repo `analyze_bwx.py` lies in the code folder `bwx-2026-11-13`, and the code folder has no folder `tmp`. So the import of line 29 works here only when that folder is on the module search path of Python in another way. The default of `--offsets` lies below the same missing folder (line 1976). Without the file the generated page prints a block "Insufficient data" in place of the table of loop offsets (lines 1952 to 1953).
- The generated page has its own list of references. Each reference gets its number at its first use (lines 98 to 106), and the paths in it are the paths of the working tree of the author (lines 1869 to 1877). They are not the references of this explanation page.
- The generated page loads nothing from another place: the style sheet and all charts are part of the file. The style sheet sets a white background [Ref7].
- The test data hold a copy of this script and a page with the default output name [Ref10].

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partBC-analysis/make_q1_html.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1993 lines, 152639 bytes, sha256 `624e401ec528cbac38e90650cddffcd728ad3ded8a29eb36c39e403a98314145`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Docstring: what the script builds, and from which files (lines 1 to 19)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""make_q1_html.py --session NAME FOLDER [FOLDER...] [--session NAME FOLDER...] -o PAGE.html [--banner TEXT] [--offsets FILE]` | Starts the docstring of the file. It ends in line 19. This line is the usage: one or more options `--session`, each with a session name and one or more result folders, then `-o` with the name of the generated page, and the optional `--banner` and `--offsets`. The code gives `-o` a default name (line 1974), so it may be left out too. |
| 4 | `Builds one self-contained HTML result page for question Q1 (one thread) of Parts B and C:` | Docstring: the script builds one HTML page that needs no other file. The page is the result page for question Q1 of Parts B and C of the plan: the behavior of one thread with a buffer of 8 MiB. |
| 5 | `steps B1, B2, B3, B4, B6, C1, C2 and hypotheses H1, H2, H3a, H3b, H4, H5, H6 of plan.md.` | Docstring: the steps and hypotheses of the generated page. Steps: B1 (`copy` against `asmcopy` in one process), B2 (three assembly variants of the C copy loop), B3 (both copy loops at one loop offset), B4 (200 `asmread` intervals with the page state), B6 (`oldread` at 8 MiB and 1 MiB), C1 and C2 (B4 and B1 with core counters). Hypotheses: H1 (the rate of old read at 8 MiB does not depend on the level), H2 (the level can change from low to high while the loop runs), H3a (huge-page coverage decides the level), H3b (the physical page address decides it), H4 (the copy difference comes from a difference between processes), H5 (from the instruction order of the C loop), H6 (from the loop address). |
| 6 | `FOLDER is a result folder of run_bwx.sh (<step>.csv, env.txt, launches.txt, stderr.txt). Folders of other steps` | Docstring: `FOLDER` is a result folder of the run script `run_bwx.sh`. It holds four files: the csv file of the step (the output of all runner processes of the step), `env.txt`, `launches.txt` and `stderr.txt`. The sentence on other folders starts here and goes on in line 7. |
| 7 | `may be named too: only their header lines and env.txt are read, for the system load. Any number of sessions is accepted.` | Docstring: folders of other steps may be named too. By the docstring only their header lines and `env.txt` are read, for the system load. The code also reads `launches.txt` and the size of `stderr.txt` of such a folder (lines 177 to 179), and no line uses these two values. Any number of sessions is accepted. |
| 9 | `The decisions come from analyze_bwx.py (its parser and its functions are imported, not written again).` | Docstring: the decisions come from `analyze_bwx.py`. Its parser and its functions are imported (line 29). They are not written a second time. |
| 10 | `This file adds a DESCRIPTION without level labels (process values d and e of every process), because the` | Docstring: this file adds a description without level labels: the process values `d` and `e` of every process. The reason follows in line 11. |
| 11 | `provisional level limits do not give stable processes at 8 MiB. A description is never turned into a decision.` | Docstring: the reason that the docstring gives: the provisional level limits do not give stable processes at 8 MiB. A description is never turned into a decision. |
| 13 | `Where a second reading of the plan and analyze_bwx.py give different words, the page prints the strict output of the script, the` | Docstring: a second reading of the plan can give another word than `analyze_bwx.py` gives. Then the generated page prints three things side by side: the strict output of the script, the other reading and its reason. The sentence goes on in line 14. |
| 14 | `other reading and its reason side by side, under "Open for the user". It chooses neither.` | Docstring: these three things stand under the heading "Open for the user". The page chooses neither word. |
| 16 | `Every sentence that interprets data is built from computed values. Typed text is limited to: the list` | Docstring: every sentence of the generated page that interprets data is built from computed values. Typed text is text that stands in the script as it is. The list of the allowed kinds of typed text starts here and ends in line 18. Some typed sentences still state a result: line 1912, line 1918 and line 1925 say that step B1 has no resolved difference at 8 MiB, and no code computes these sentences from the input. |
| 17 | `"Words used here", the questions, what the plan, the handoff and the scripts ask for or do, the limits, the` | Docstring: the allowed kinds of typed text: the list "Words used here", the questions, what the plan, the handoff note and the scripts ask for or do, and the limits. The list goes on in line 18. |
| 18 | `captions that say how a chart is drawn, and the references. No external script, font or image. Light background only.` | Docstring: the last two kinds: the captions that say how a chart is drawn, and the references. The generated page loads no script, no font and no image from another place. It has a light background only. |
| 19 | `"""` | Ends the docstring. |

### Imports, paths, constants and the added style rules (lines 20 to 54)

| Line | Source | Explanation |
|---:|---|---|
| 20 | `import argparse, calendar, glob, html, math, os, re, sys, time` | Imports nine modules of the Python standard library: `argparse` (the options of the command line), `calendar` and `time` (a time text to seconds), `glob` (file name patterns), `html` (the function `html.escape`), `math`, `os` (paths and files), `re` (regular expressions, which are patterns for text) and `sys`. |
| 21 | `from statistics import median` | Imports the function `median` of the module `statistics`. For an even count of values it returns the mean of the two middle values. |
| 23 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the full path of the folder that holds this file. |
| 24 | `CRB = os.path.normpath(os.path.join(HERE, '..', '..'))` | `CRB`: the folder two levels above `HERE`, as a cleaned path. Here the name means a folder, not the machine. In the working tree of the author it is the folder `crb`. In this repo it is the folder `code`. |
| 25 | `BWX = os.path.join(CRB, 'tmp', 'agent-scratch', 'bwx-2026-11-13')` | `BWX`: the folder `tmp/agent-scratch/bwx-2026-11-13` below `CRB`. The script expects the analysis script `analyze_bwx.py` and the build record `crb-build-2` there. In this repo the folder `code` has no folder `tmp`. `analyze_bwx.py` lies in the code folder `bwx-2026-11-13`. |
| 26 | `for _d in (BWX, os.path.join(HERE, '..', 'partA-analysis'), os.path.join(HERE, '..')):` | Loop over three folders: `BWX`, the folder `partA-analysis` beside the folder of this file, and the folder above the folder of this file. The last one holds `decide.py`. |
| 27 | `    if _d not in sys.path:` | Tests whether the folder is missing in `sys.path`. That is the list of folders in which Python looks for a module. |
| 28 | `        sys.path.insert(0, _d)` | If it is missing, the folder is put at the front of that list. |
| 29 | `import analyze_bwx as ab          # noqa: E402  parser, decision analysis` | Imports `analyze_bwx.py` under the short name `ab`. It gives the parser of the csv files and the decision analysis. Comment: `noqa: E402` tells a style checker not to report an import that does not stand at the top of the file. |
| 30 | `import make_partA_html as pa      # noqa: E402  style, number format, label placement` | Imports `make_partA_html.py`, the page builder of Part A, under the short name `pa`. Comment: this file takes the style, the number format and the label placement from it. |
| 31 | `decide = ab.decide` | `decide`: the module `decide.py`, as `analyze_bwx.py` imported it. It holds the two level limits and the function `level`. |
| 33 | `Q1_STEPS = ['B1', 'B2', 'B3', 'B4', 'B6', 'C1', 'C2']` | `Q1_STEPS`: the seven steps of question Q1, in the order of the sections of the generated page: B1, B2, B3, B4, B6, C1, C2. A process of any other step gives no value to the page. |
| 34 | `LOW, HIGH = decide.LOW_MAX, decide.HIGH_MIN` | `LOW` and `HIGH`: the two provisional level limits of `decide.py`, 69.0 GB/s and 70.5 GB/s. An `asmread` interval at 8 MiB with a rate below `LOW` has the label low. One with a rate above `HIGH` has the label high. |
| 35 | `MIB = 1 << 20` | `MIB`: 1048576, the number of bytes of 1 MiB. The expression shifts the number 1 left by 20 bits. |
| 36 | `ID = 'Insufficient data'` | `ID`: the text `Insufficient data`. The generated page prints it where a measurement is missing. |
| 37 | `C0, C1c, C2c, RED = pa.C0, pa.C1, pa.C2, '#c22f2f'` | Four colors. `C0` (blue), `C1c` (orange) and `C2c` (green) come from `pa`. `RED` is `#c22f2f`. No other line of this file uses `C2c`. |
| 38 | `TD, TE = '#1b5fb0', '#a8431a'      # text colours of the d and e values in a chart (darker than the markers, for small text)` | `TD` and `TE`: a dark blue and a dark orange for the numbers of `d` and `e` in a chart. Comment: they are darker than the markers, for small text. |
| 39 | `NEAR = 0.2                         # GB/s: an interval nearer than this to a level limit is "near the limit" (a choice of this page)` | `NEAR`: 0.2 GB/s. An interval whose rate lies less than 0.2 GB/s from a level limit counts as near the limit (lines 361 to 362). Comment: this value is a choice of the generated page. |
| 40 | `INK, MUTED, GRID, BAND = pa.INK, pa.MUTED, pa.GRID, pa.BAND` | Four more colors from `pa`: `INK` (black, for text), `MUTED` (dark grey), `GRID` (light grey, for grid lines) and `BAND` (very light grey, for shaded bands). No other line of this file uses `INK`. |
| 41 | `e, fx, fs, pl = html.escape, pa.fx, pa.fs, pa.pl` | Four short names. `e` is `html.escape`: it replaces the characters that have a meaning in HTML, such as the angle brackets. `fx` prints a number with a fixed count of decimals, 2 unless another count is given, and rounds a half upward. With 2 decimals, a value that lies exactly in the middle of two printed values is printed with 3 decimals. `fs` does the same and always prints the sign. `pl` prints a count and the singular or the plural word behind it, for example `1 process` or `3 processes` [Ref7]. |
| 42 | `KN = {'copy': 'new C copy', 'asmcopy': 'asm copy', 'asmcopy2': 'asm copy 2', 'asmread': 'asm read', 'oldread': 'old read at 8 MiB',` | Starts `KN`: the names that the generated page prints for the entries of a sequence. This line: `copy` is "new C copy", `asmcopy` is "asm copy", `asmcopy2` is "asm copy 2", `asmread` is "asm read", and `oldread` is "old read at 8 MiB". |
| 43 | `      'oldread2': 'old read 2 at 8 MiB', 'oldread@1M': 'old read at 1 MiB', 'asmcopy_c': 'asmcopy_c', 'asmcopy_c_add': 'asmcopy_c_add',` | Continues `KN`: `oldread2` is "old read 2 at 8 MiB", and `oldread@1M` is "old read at 1 MiB". The two variants `asmcopy_c` and `asmcopy_c_add` keep their names. |
| 44 | `      'asmcopy_c_reg': 'asmcopy_c_reg'}` | Ends `KN` with the third variant, `asmcopy_c_reg`, which keeps its name too. |
| 45 | `EV = [('cycles', 'cycles'), ('instructions', 'instructions'), ('l1d_refill', 'L1D refill'), ('l2d_refill', 'L2D refill'),` | Starts `EV`: five pairs, one per counter event. The first value is the name of the event in the result of `analyze_bwx.py`. The second is the name on the generated page. This line: cycles, instructions, `l1d_refill` (a line that is brought into the L1 data cache) and `l2d_refill` (the same for the L2 cache). |
| 46 | `      ('ll_read_miss', 'LL read miss')]` | Ends `EV` with the fifth event: `ll_read_miss`, a read that misses the last cache level. |
| 47 | `CSS = pa.CSS + """` | Starts `CSS`: the style sheet of the generated page. It is the style sheet of `pa`, which sets a white background, plus the rules of lines 48 to 52. |
| 48 | `table.c td,table.c th{padding:3px 6px;font-size:12px} .nw{white-space:nowrap} td.l,th.l{text-align:left}` | CSS: cells of a table of the class `c` get a padding of 3 px above and below and 6 px at the sides, and a font size of 12 px. The class `nw` forbids a line break inside a cell. Cells of the class `l` are aligned left. |
| 49 | `td.wr{white-space:normal;text-align:left;min-width:170px}` | CSS: a cell of the class `wr` may break its text, is aligned left and is at least 170 px wide. The column of the busiest process uses it. |
| 50 | `.sm{font-size:12px;color:#52514e} ul.words{columns:2;column-gap:28px;font-size:13px;padding-left:18px} ul.words li{break-inside:avoid;margin-bottom:3px}` | CSS: the class `sm` gives small grey text of 12 px. The list of the class `words` ("Words used here") is set in 2 columns with a gap of 28 px and a font size of 13 px, and no list item is cut between the columns. |
| 51 | `table.hy{table-layout:fixed;width:100%} .hy td{font-size:13px} .hy td:nth-child(2){white-space:nowrap} h4{font-size:14px;margin:18px 0 4px}` | CSS: a table of the class `hy` (the hypothesis table and the table of the main numbers) has fixed column widths and the full page width. Its cells have a font size of 13 px, and its second column does not break. A heading of level 4 gets a font size of 14 px. |
| 52 | `.how{border:1px solid #c9c8c2;border-radius:6px;padding:4px 14px;margin-top:32px;font-size:14px} .open{background:#fdf3e7;border-left:4px solid #b85c00;padding:4px 14px;margin:10px 0}` | CSS: the box of the class `how` ("How to read the charts") gets a thin grey border with round corners. The box of the class `open` ("Open for the user") gets a light orange background and an orange bar of 4 px at its left side. |
| 53 | `"""` | Ends the text of the added rules. |
| 54 | `WORDS5 = ('rejected', 'not rejected', 'not observed', 'not resolved', 'not tested')` | `WORDS5`: the five result words of rule 11 of the plan: `rejected`, `not rejected`, `not observed`, `not resolved` and `not tested`. Line 686 tests every word of the hypothesis table against this list. |

### Small helpers for names, numbers and missing data (lines 55 to 88)

| Line | Source | Explanation |
|---:|---|---|
| 57 | `def kn(k):` | Starts the function `kn`. It returns the page name of a sequence entry. |
| 58 | `    return KN.get(k, k)` | Looks `k` up in `KN`. An entry that is not in `KN` is returned unchanged. |
| 61 | `def f2(v, nd=2):` | Starts the function `f2`. It formats a number that may be missing. `nd` is the count of decimals, 2 unless the caller gives another count. |
| 62 | `    return '-' if v is None else fx(v, nd)` | Returns `-` when `v` is `None`, the Python value for "no value". In every other case it returns the text of `fx`. |
| 65 | `def s2(v, nd=2):` | Starts the function `s2`. It does the same as `f2` and prints the sign. |
| 66 | `    return '-' if v is None else fs(v, nd)` | Returns `-` when `v` is `None`. In every other case it returns the text of `fs`. |
| 69 | `def rng(a, b, nd=2, signed=False):` | Starts the function `rng`. It prints a range of two numbers. |
| 70 | `    """'a to b' with nd decimals, or one value if both print the same."""` | Docstring: the result is the text `a to b` with `nd` decimals, or one value when both numbers print the same. |
| 71 | `    g = zs if signed else fx` | `g`: the format function for both numbers: `zs` when `signed` is true, `fx` when it is false. |
| 72 | `    return g(a, nd) if g(a, nd) == g(b, nd) else f'{g(a, nd)} to {g(b, nd)}'` | Returns one text when both numbers give the same text. If they differ, it returns the first text, the word `to` and the second text. |
| 75 | `def zs(v, nd=2):` | Starts the function `zs`. It prints a number with a sign. |
| 76 | `    """A signed number. A value that prints as zero is printed without a sign."""` | Docstring: a value that prints as zero is printed without a sign. |
| 77 | `    t = fs(v, nd)` | `t`: the text of `fs`, for example `+0.25` or `-1.30`. |
| 78 | `    return t.lstrip('+-') if float(t) == 0 else t` | When the printed value is zero, the sign in front is removed and `0.00` is returned. In every other case `t` is returned as it is. |
| 81 | `def yn(b):` | Starts the function `yn`. |
| 82 | `    return 'yes' if b else 'no'` | Returns the word `yes` for a true value and `no` for a false one. |
| 85 | `def miss(what):` | Starts the function `miss`. It builds the block that the generated page shows where data are missing. |
| 86 | `    return f'<p class="miss"><b>{ID}.</b> {what}</p>'` | Returns one HTML paragraph of the class `miss`: the words `Insufficient data.` in bold, then the text `what`. The style sheet of `pa` gives this class a light orange background and an orange bar at the left. |

### Class `Refs`: the reference list of the generated page (lines 89 to 111)

| Line | Source | Explanation |
|---:|---|---|
| 89 | `class Refs:` | Starts the class `Refs`. One object of it holds the references of the generated page and gives each used reference a number. |
| 90 | `    """Reference list. ref(key) gives the text [RefN]. Only references that the page uses are printed."""` | Docstring: a call with a key gives the citation text `[RefN]`. Only references that the page uses are printed. |
| 92 | `    def __init__(self):` | Starts the constructor, which runs when an object is created. |
| 93 | `        self.text, self.order = {}, []` | `text`: a dictionary from the key of a reference to its text. `order`: the list of the keys that were used, in the order of their first use. Both start empty. |
| 95 | `    def add(self, key, text):` | Starts the method `add`. It stores one reference under a key. |
| 96 | `        self.text[key] = text` | Stores the text. The reference has no number yet. |
| 98 | `    def __call__(self, *keys):` | Starts the method `__call__`. Python runs it when the object is called like a function, for example `R('plan', 'handoff')`. It takes any count of keys. |
| 99 | `        out = ''` | `out`: the citation text, empty at the start. |
| 100 | `        for k in keys:` | Loop over the given keys. |
| 101 | `            if k not in self.text:` | Tests whether the key was never stored with `add`. |
| 102 | `                continue` | Such a key is skipped. It gives no citation. |
| 103 | `            if k not in self.order:` | Tests whether this is the first use of the key. |
| 104 | `                self.order.append(k)` | If so, the key is appended to `order`. So the references get their numbers in the order in which the page builder first cites them. |
| 105 | `            out += '[Ref%d]' % (self.order.index(k) + 1)` | Appends the citation to `out`: the text `[Ref`, the number and `]`. The number is the place of the key in `order`, counted from 1. |
| 106 | `        return out` | Returns the citations of all given keys as one text, with nothing between them. |
| 108 | `    def html(self):` | Starts the method `html`. It builds the section of references. |
| 109 | `        return '<ul>' + ''.join('<li>[Ref%d] %s</li>' % (i + 1, self.text[k]) for i, k in enumerate(self.order)) + '</ul>'` | Returns an HTML list with one item per used reference, in the order of the numbers: the citation and the text of the reference. A reference that was stored and never cited is not printed. |

### Pattern `LAUNCH` and function `read_launches`: the file `launches.txt` (lines 112 to 133)

| Line | Source | Explanation |
|---:|---|---|
| 112 | `# ---------------------------------------------------------------- loading` | Comment: a divider. The functions that read the input files follow. |
| 114 | `LAUNCH = re.compile(r'^== (\S+) (\S+) utc (\S+) loadavg (\S+) (\S+) (\S+) (\d+)/(\d+) logins (\S+)')` | `LAUNCH`: a compiled pattern for the line that `run_bwx.sh` writes into `launches.txt` directly before each launch. The line starts with `==`. Each `\S+` fits one text without a space. The words `utc`, `loadavg` and `logins` must stand between the values. `(\d+)/(\d+)` fits two numbers with a slash between them. The 9 groups hold: the name of the csv file, the tag of the process, the UTC time, the load averages of 1, 5 and 15 minutes, the number of runnable tasks, the number of all tasks, and the number of logins. |
| 117 | `def read_launches(path):` | Starts the function `read_launches`. It reads the file `launches.txt` of one result folder. |
| 118 | `    """launches.txt -> {(csv name, tag): dict(runnable, busiest=[(pcpu, user, comm)])}."""` | Docstring: the result is a dictionary. The key is the pair of csv file name and tag. The value holds `runnable` and `busiest`, a list with one entry per process line: the percent value, the user and the command. |
| 119 | `    out, cur = {}, None` | `out`: the result, empty at the start. `cur`: the entry of the launch whose lines are read now. It is `None` before the first launch line. |
| 120 | `    if not os.path.exists(path):` | Tests whether the file is missing. |
| 121 | `        return out` | Without the file the function returns the empty dictionary. |
| 122 | `    for line in open(path, errors='replace'):` | Loop over the lines of the file. `errors='replace'`: a byte that is not valid text becomes a mark character and does not stop the script. |
| 123 | `        m = LAUNCH.match(line)` | `m`: the result of the test of the line against `LAUNCH`. |
| 124 | `        if m:` | The next two lines run for a launch line. |
| 125 | `            cur = out.setdefault((m.group(1), m.group(2)), dict(runnable=int(m.group(7)), busiest=[], own_users=set()))` | `cur` becomes the entry of this launch. `setdefault` creates the entry only when the pair of csv name and tag is new. A new entry holds `runnable` (group 7 as a number: the runnable tasks at that moment), an empty list `busiest` and an empty set `own_users`. |
| 126 | `            continue` | Goes on with the next line of the file. |
| 127 | `        f = line.split(None, 2)` | For every other line: `f` holds the first two fields of the line and, as its third field, the rest of the line. The line is split at white space. |
| 128 | `        if cur is not None and len(f) == 3 and re.fullmatch(r'[\d.]+', f[0]):` | Keeps only the process lines of the tool `ps`. The test needs a launch line before, 3 fields, and a first field that holds only digits and dots. The title line of `ps` starts with `%CPU` and fails the test. |
| 129 | `            cur['busiest'].append((float(f[0]), f[1], f[2].strip()))` | Appends one entry to `busiest`: the percent value as a number, the user, and the command without the line end. The run script takes these lines from `ps`, sorted by the percent value, and keeps the 5 highest [Ref5]. By the text of line 1006, the value is the CPU time of a process divided by the time from its start to that moment. |
| 130 | `            if f[2].strip() in ('ps', 'bash'):` | Tests whether the command is `ps` or `bash`. |
| 131 | `                cur['own_users'].add(f[1])                    # ps and bash are the run script itself` | If so, the user of the line is added to `own_users`. Comment: `ps` and `bash` are the run script itself. So `own_users` holds the account under which the run script ran. |
| 132 | `    return out` | Returns the dictionary. |

### Functions `read_env` and `scan_headers` (lines 134 to 163)

| Line | Source | Explanation |
|---:|---|---|
| 135 | `def read_env(path):` | Starts the function `read_env`. It reads the file `env.txt` of one result folder. `run_bwx.sh` writes this file once per step. |
| 136 | `    out = dict(present=os.path.exists(path))` | `out`: the result. Its value `present` says whether the file exists. |
| 137 | `    if not out['present']:` | Tests whether the file is missing. |
| 138 | `        return out` | Without the file the function returns `out` with `present` false. |
| 139 | `    t = open(path, errors='replace').read()` | `t`: the whole text of the file. |
| 140 | `    m = re.search(r'^## host=\S+ utc=(\S+) loadavg=(\S+) \S+ \S+ (\d+)/\d+ \S+ logins=(\S+) step=(\S+)', t, re.M)` | Searches the first line of `env.txt`. It starts with `## host=`. With `re.M` the sign `^` fits the start of every line of the text. Group 1 holds the UTC time at the start of the step, in the form that line 347 shows. Group 2 holds the 1-minute load average. The pattern then fits two more fields and keeps neither. Group 3 holds the runnable tasks, the number before the slash. Group 4 holds the number of logins. Group 5 holds the step. |
| 141 | `    if m:` | Tests whether the line was found. |
| 142 | `        out.update(start_utc=m.group(1), start_load1=float(m.group(2)), start_runnable=int(m.group(3)), logins=m.group(4), step=m.group(5))` | Stores the five groups as `start_utc`, `start_load1`, `start_runnable`, `logins` and `step`. Other lines of this file read only `start_utc`. |
| 143 | `    m = re.search(r'^## end utc=(\S+) loadavg=(\S+)', t, re.M)` | Searches the line that the run script appends when the step has ended. It starts with `## end utc=`. Group 1 holds the UTC time of the end. Group 2 holds the 1-minute load average at that time. |
| 144 | `    if m:` | Tests whether the line was found. |
| 145 | `        out.update(end_utc=m.group(1), end_load1=float(m.group(2)))` | Stores the two groups as `end_utc` and `end_load1`. |
| 146 | `    m = re.search(r'BWX_PMU_TYPE=(\S*) BWX_EVENTS=(\S*)', t)` | Searches the two counter settings in the settings line of `env.txt`. Group 1 holds the value of `BWX_PMU_TYPE`, the type number of the counter unit of the core. Group 2 holds the value of `BWX_EVENTS`, the list of event codes. Each group may be empty. |
| 147 | `    if m:` | Tests whether the text was found. |
| 148 | `        out.update(pmu_type=m.group(1), events=m.group(2))` | Stores the two groups as `pmu_type` and `events`. No other line of this file reads them. |
| 149 | `    return out` | Returns `out`. |
| 152 | `def scan_headers(path):` | Starts the function `scan_headers`. It finds out which steps a folder holds, without a full read of the rows. |
| 153 | `    """The header lines of the csv files of a folder -> [(step, threads)]. Cheap: no row is parsed."""` | Docstring: from the header lines of the csv files of a folder it makes a list of pairs of step and thread count. It costs little time: no row is parsed. |
| 154 | `    out = []` | `out`: the list, empty at the start. |
| 155 | `    for f in (sorted(glob.glob(os.path.join(path, '*.csv'))) if os.path.isdir(path) else [path]):` | Loop over the csv files of the folder, in the order of their names. When `path` is not a folder, it is taken as one csv file. |
| 156 | `        with open(f, errors='replace') as fh:` | Opens the file for reading. |
| 157 | `            for line in fh:` | Loop over its lines. |
| 158 | `                if line.startswith('-- step '):` | A header line starts with `-- step`. The run script writes one before the output of each process. |
| 159 | `                    m = re.search(r'--threads (\d+)', line)` | `m`: the result of a search for the option `--threads` and a number in the header line. Group 1 holds the thread count. |
| 160 | `                    out.append((line.split()[2], int(m.group(1)) if m else 1))` | Appends one pair: the third word of the line, which is the step, and the thread count. A line without `--threads` counts as 1 thread. |
| 161 | `    return out` | Returns the list. |

### Function `load`: read all folders of the command line (lines 164 to 191)

| Line | Source | Explanation |
|---:|---|---|
| 164 | `def load(spec):` | Starts the function `load`. It reads every folder that the command line names. |
| 165 | `    """spec: [(session name, [paths])] -> {name: dict(procs, folders, other)}. Only the Q1 steps give processes."""` | Docstring: `spec` is a list of pairs of a session name and its paths. The result has one entry per session with the three lists `procs`, `folders` and `other`. Only the steps of Q1 give processes. |
| 166 | `    sessions = {}` | `sessions`: the result, empty at the start. |
| 167 | `    for name, paths in spec:` | Loop over the sessions of `spec`. |
| 168 | `        s = sessions.setdefault(name, dict(procs=[], folders=[], other=[]))` | `s`: the entry of this session. A new entry holds three empty lists: `procs` (the processes of the Q1 steps), `folders` (the result folders with such processes) and `other` (all other folders). A session name that is given twice adds to the same entry. |
| 169 | `        for path in paths:` | Loop over the paths of the session. |
| 170 | `            path = os.path.abspath(path)` | Makes the path absolute. |
| 171 | `            folder = path if os.path.isdir(path) else os.path.dirname(path)` | `folder`: the path itself when it is a folder. For a path of a csv file it is the folder of that file. |
| 172 | `            head = scan_headers(path)` | `head`: the pairs of step and thread count of all header lines below `path`. |
| 173 | `            procs = ab.load_session(name, [path]) if any(st in Q1_STEPS for st, _ in head) else []` | `procs`: the full parse of the csv files by `ab.load_session`. It runs only when at least one header line names a step of Q1. For any other folder the list is empty and no row is parsed. The parser returns one object per process, with the values of its header line and its `I`, `T`, `P` and `C` rows. |
| 174 | `            mine = [p for p in procs if p.step in Q1_STEPS]` | `mine`: the processes whose step is a step of Q1. |
| 175 | `            env = read_env(os.path.join(folder, 'env.txt'))` | `env`: the values of `env.txt` of the folder. |
| 176 | `            err = os.path.join(folder, 'stderr.txt')` | `err`: the path of `stderr.txt`. The run script sends the error output of the runner there. |
| 177 | `            info = dict(path=folder, name=os.path.basename(folder), env=env, steps=sorted({st for st, _ in head}),` | Starts `info`, the record of the folder: its path, its name, the values of `env.txt`, and the sorted step names of its header lines. |
| 178 | `                        stderr_bytes=os.path.getsize(err) if os.path.exists(err) else None,` | Continues line 177. `stderr_bytes`: the size of `stderr.txt` in bytes, or `None` when the file is missing. |
| 179 | `                        threads_max=max((n for _, n in head), default=0), launches=read_launches(os.path.join(folder, 'launches.txt')))` | Continues line 177. `threads_max`: the highest thread count of a header line, 0 when the folder has no header line. `launches`: the content of `launches.txt`. |
| 180 | `            if not mine:` | Tests whether the folder has no process of a Q1 step. |
| 181 | `                s['other'].append(info)` | Such a folder goes to the list `other`. |
| 182 | `                continue` | Goes on with the next path. |
| 183 | `            for p in mine:` | Loop over the processes of the Q1 steps. |
| 184 | `                p.folder = info` | Gives the process the record of its folder. |
| 185 | `                l = info['launches'].get((os.path.basename(p.file), p.tag))` | `l`: the entry of `launches.txt` for this process. It is found by the name of the csv file and the tag. It is `None` when the file has no such entry. |
| 186 | `                p.launch = l` | Gives the process this entry as `launch`. |
| 187 | `            s['procs'] += mine` | Appends the processes to the list `procs` of the session. |
| 188 | `            s['folders'].append(info)` | Appends the record of the folder to the list `folders`. |
| 189 | `    return sessions` | Returns the sessions. |

### Functions `level_counts` and `stable_label` (lines 192 to 204)

| Line | Source | Explanation |
|---:|---|---|
| 192 | `# ---------------------------------------------------------------- computed values` | Comment: a divider. The functions that compute the values of the generated page follow. |
| 194 | `def level_counts(rates):` | Starts the function `level_counts`. It counts how many rates of a list lie at each level. |
| 195 | `    lv = [decide.level(r) for r in rates]` | `lv`: the level word of each rate, from the function `level` of `decide.py`: `low` below 69.0 GB/s, `high` above 70.5 GB/s, and `changing` for a rate from 69.0 to 70.5 GB/s [Ref4]. |
| 196 | `    return dict(n=len(lv), low=lv.count('low'), between=lv.count('changing'), high=lv.count('high'))` | Returns four counts: `n` (all rates), `low`, `between` (the rates with the word `changing`) and `high`. |
| 199 | `def stable_label(refs):` | Starts the function `stable_label`. It gives the label of a whole process from the rates of its reference intervals. |
| 200 | `    """The label of a process by the rule (plan, rule 4): low or high if ALL reference intervals have it, else None."""` | Docstring: the label of a process by the rule (plan, rule 4): low or high if all reference intervals have it. In every other case the result is `None`. |
| 201 | `    lab = {decide.level(r) for r in refs}` | `lab`: the set of the level words of the reference rates. A set keeps each word once. |
| 202 | `    return lab.pop() if len(lab) == 1 and lab != {'changing'} else None` | Returns the word when the set holds exactly one word and that word is not `changing`. In every other case it returns `None`: the process is not stable. An empty list of rates gives `None` too. |

### Function `describe_pairs`: the values d and e of every process, and the values per CPU (lines 205 to 243)

| Line | Source | Explanation |
|---:|---|---|
| 205 | `def describe_pairs(procs, first, second, aa1, aa2):` | Starts the function `describe_pairs`. It computes the description of one group of processes. `first` and `second` are the two compared entries. `aa1` and `aa2` are the two copies of one loop (the A/A pair). |
| 206 | `    """Description without labels. One record per process: d = median of (first - second) over its pairs, e = median of` | Docstring: a description without labels. One record per process: `d` is the median of `first` minus `second` over its pairs. The sentence on `e` goes on in line 207. |
| 207 | `    (aa1 - aa2). Per CPU: the values that rule 3 of the plan names, as numbers, with no decision word."""` | Docstring: `e` is the median of `aa1` minus `aa2`. Per CPU the function gives the values that rule 3 of the plan names, as numbers, with no decision word. |
| 208 | `    recs, no_pair = [], []` | `recs`: the records of the processes. `no_pair`: the tags of the processes without a pair. Both start empty. |
| 209 | `    for p in procs:` | Loop over the processes. |
| 210 | `        kp, ap = ab.pair_values(p, first, second), ab.pair_values(p, aa1, aa2)` | `kp`: the pairs of the two compared entries. `ap`: the A/A pairs. `ab.pair_values` takes every two neighbouring intervals of the two entries that stand between the same two reference intervals, in every round. The value of a pair is the rate of the first-named entry minus the rate of the second, in GB/s [Ref3]. |
| 211 | `        if not kp or not ap:` | Tests whether the process has no pair of one of the two kinds. |
| 212 | `            no_pair.append(p.tag)` | Then its tag goes to `no_pair`. No other line of this file reads that list. |
| 213 | `            continue` | The process gets no record. The loop goes on. |
| 214 | `        refs = [iv.rate for iv in p.ordered if iv.entry == ab.REF]` | `refs`: the rates of the reference intervals of the process (entry `asmread`), in time order. A rate is field 7 (`bytes`) of the `T` row of the interval divided by field 8 (`elapsed_s`) and by 1e9, in GB/s. `analyze_bwx.py` computes it [Ref3]. |
| 215 | `        aa_pos = [x['value'] if p.seq[x['pos']] == aa1 else -x['value'] for x in ap]      # the copy timed first minus the copy timed second` | `aa_pos`: the A/A pair values, each turned into "the copy timed first minus the copy timed second". `x['pos']` is the position of the first interval of the pair. When `aa1` stands there, the value has this order already. If not, its sign is turned. Comment: the copy timed first minus the copy timed second. |
| 216 | `        f1 = [x['value'] for x in kp if p.seq[x['pos']] == first]` | `f1`: the pair values of the pairs in which `first` is timed first. |
| 217 | `        f2_ = [x['value'] for x in kp if p.seq[x['pos']] != first]` | `f2_`: the pair values of the pairs in which `first` is timed second. The value stays `first` minus `second`. |
| 218 | `        recs.append(dict(tag=p.tag, cpu=p.cpu, session=p.session, d=median(x['value'] for x in kp), e=median(x['value'] for x in ap),` | Starts the record of the process: tag, CPU and session. `d`: the median of its pair values. `e`: the median of its A/A pair values. Both are in GB/s. |
| 219 | `                         n_pairs=len(kp), n_aa_pairs=len(ap), aa_single_max=max(abs(x['value']) for x in ap), aa_pos=aa_pos,` | Continues line 218. `n_pairs` and `n_aa_pairs`: the counts of the two kinds of pairs. `aa_single_max`: the largest absolute value of one A/A pair, before any median. `aa_pos`: the list of line 215. |
| 220 | `                         d_first=median(f1) if f1 else None, d_second=median(f2_) if f2_ else None,` | Continues line 218. `d_first`: the median of `f1`. `d_second`: the median of `f2_`. Each is `None` when its list is empty. |
| 221 | `                         second_rate=median(iv.rate for iv in p.rate_by_entry[second]), first_rate=median(iv.rate for iv in p.rate_by_entry[first]),` | Continues line 218. `second_rate`: the median rate of all intervals of the entry `second` in this process. `first_rate`: the same for `first`. |
| 222 | `                         refs=refs, first_ref=refs[0] if refs else None, stable=stable_label(refs),` | Continues line 218. `refs`: the reference rates. `first_ref`: the first of them. In the sequences of these steps it is the first timed interval of the process. `stable`: the label of the process, or `None`. |
| 223 | `                         stable_without_first=stable_label(refs[1:]) if len(refs) > 1 else None))` | Ends the record. `stable_without_first`: the label that the process would have without its first reference interval. It is `None` for a process with one reference interval. |
| 224 | `    per_cpu = {}` | `per_cpu`: the values per CPU, empty at the start. |
| 225 | `    for cpu in sorted({r['cpu'] for r in recs}):` | Loop over the CPUs of the records, in rising order. The CPU of a process is the value of its option `--cpus`. The runner pins the one thread of the process to that CPU. Processes of different CPUs are never put together. |
| 226 | `        g = [r for r in recs if r['cpu'] == cpu]` | `g`: the records of this CPU. |
| 227 | `        d = [r['d'] for r in g]` | `d`: the list of the `d` values of these processes. |
| 228 | `        spread = max(abs(r['e']) for r in g)` | `spread`: the A/A spread of the CPU: the largest absolute `e` of its processes. This description uses all processes of the CPU, stable or not. |
| 229 | `        per_cpu[cpu] = dict(n=len(g), d=d, median_d=median(d), d_min=min(d), d_max=max(d), aa_spread=spread,` | Starts the values of the CPU: `n` (the process count), the list `d`, its median `median_d`, its lowest and highest value, and `aa_spread`. |
| 230 | `                            aa_single_max=max(r['aa_single_max'] for r in g), above=abs(median(d)) > spread,` | Continues line 229. `aa_single_max`: the largest absolute value of one A/A pair on this CPU. `above`: true when the absolute value of the median `d` is larger than the A/A spread. |
| 231 | `                            one_sign=all(x > 0 for x in d) or all(x < 0 for x in d),` | Continues line 229. `one_sign`: true when all `d` are above 0 or all are below 0. |
| 232 | `                            pct=100 * median(d) / median(r['second_rate'] for r in g),` | Continues line 229. `pct`: the median `d` in percent of the rate of the second loop. It is 100 times the median `d`, divided by the median over the processes of `second_rate`. |
| 233 | `                            d_first=median([r['d_first'] for r in g if r['d_first'] is not None] or [0]),` | Continues line 229. `d_first`: the median over the processes of their `d_first`. A process without that value is left out. The value is 0 when no process has one. |
| 234 | `                            d_second=median([r['d_second'] for r in g if r['d_second'] is not None] or [0]),` | Continues line 229. `d_second`: the same for `d_second`. |
| 235 | `                            aa_pos_n=sum(len(r['aa_pos']) for r in g), aa_pos_neg=sum(1 for r in g for v in r['aa_pos'] if v < 0),` | Continues line 229. `aa_pos_n`: the count of all A/A pairs of the CPU. `aa_pos_neg`: how many of them have a value below 0 in `aa_pos`. In such a pair the copy that was timed first was the slower one. |
| 236 | `                            aa_pos_median=median([v for r in g for v in r['aa_pos']]),` | Continues line 229. `aa_pos_median`: the median of `aa_pos` over all A/A pairs of the CPU, without a median per process first. |
| 237 | `                            n_low=sum(1 for r in g if r['stable'] == 'low'), n_high=sum(1 for r in g if r['stable'] == 'high'),` | Continues line 229. `n_low` and `n_high`: the counts of processes that are stable low and stable high. |
| 238 | `                            n_not_stable=sum(1 for r in g if r['stable'] is None),` | Continues line 229. `n_not_stable`: the count of processes without a stable label. |
| 239 | `                            n_stable_without_first=sum(1 for r in g if r['stable_without_first'] is not None),` | Continues line 229. `n_stable_without_first`: the count of processes that are stable when the first reference interval is left out. No other line reads this value. |
| 240 | `                            first_rate=median(r['first_rate'] for r in g), second_rate=median(r['second_rate'] for r in g))` | Ends the values of the CPU. `first_rate` and `second_rate`: the medians over the processes of the two process medians of line 221. |
| 241 | `    return dict(recs=recs, per_cpu=per_cpu, no_pair=no_pair, first=first, second=second, aa=(aa1, aa2))` | Returns the description: the records, the values per CPU, the list `no_pair` and the names of the compared entries. |

### Function `copy_groups`: the groups of a copy step (lines 244 to 256)

| Line | Source | Explanation |
|---:|---|---|
| 244 | `def copy_groups(procs, step):` | Starts the function `copy_groups`. It sorts the processes of one copy step into the groups that are compared. |
| 245 | `    """The groups of a_copy of analyze_bwx.py: B1 and C2 by size, B2 by variant, B3 by binary. -> {key: (first kernel, size, procs)}."""` | Docstring: these are the groups of the function `a_copy` of `analyze_bwx.py`: steps B1 and C2 by size, B2 by variant, B3 by binary. The result maps a group key to the first kernel, the size and the processes. |
| 246 | `    groups = {}` | `groups`: the result, empty at the start. |
| 247 | `    for p in procs:` | Loop over the processes. |
| 248 | `        if not p.complete:` | Tests whether the process is not complete. A process is complete when the run script recorded no kill and no failure, the parser found no problem, and the process has one interval for every entry and round [Ref3]. |
| 249 | `            continue` | A process that is not complete is skipped. |
| 250 | `        other = [x for x in p.seq if x not in (ab.REF, 'asmcopy', 'asmcopy2')]` | `other`: the entries of the sequence that are not `asmread`, `asmcopy` or `asmcopy2`. |
| 251 | `        first = other[0] if other else None` | `first`: the first of them. It is the loop that is compared with `asmcopy`: `copy` in step B1, a variant in step B2. It is `None` when the sequence has no such entry. |
| 252 | `        key = p.binary if step == 'B3' else first if step == 'B2' else ab.size_name(p.bytes)` | `key`: the name of the group. For step B3 it is the name of the binary. Each build of step B3 is one binary. For step B2 it is the variant. For the other steps it is the buffer size as text, for example `8M`. |
| 253 | `        groups.setdefault(key, (first, p.bytes, []))[2].append(p)` | Adds the process to its group. A new group keeps the compared entry, the buffer size in bytes and an empty list of processes. |
| 254 | `    return groups` | Returns the groups. |

### Function `b4_process`: the facts of one process of step B4 or C1 (lines 257 to 286)

| Line | Source | Explanation |
|---:|---|---|
| 257 | `def b4_process(p):` | Starts the function `b4_process`. It collects the facts of one process of step B4 or C1. Such a process times `asmread` on one buffer of 8 MiB many times. |
| 258 | `    """One process of B4 or C1: rates, coverage, and the intervals before which a vmstat counter rose."""` | Docstring: one process of B4 or C1: the rates, the coverage, and the intervals before which a counter of the file `/proc/vmstat` rose. |
| 259 | `    rates = [iv.rate for iv in p.ordered]` | `rates`: the rate of every interval of the process in time order, in GB/s. |
| 260 | `    pages = [p.page_before(iv) for iv in p.ordered]` | `pages`: for every interval the `P` row of buffer `a` with the same round and position, or `None` when there is none. The runner reads this page state before the interval, after the warm-up pass and outside the timed part [Ref6]. |
| 261 | `    cov = [ab.coverage(x) for x in pages]` | `cov`: the coverage word of every interval, from `ab.coverage`: `full` when field 7 (`kB_huge`) of the `P` row equals field 6 (`kB_total`), `none` when `kB_huge` is 0, `partial` for a value between the two, and `unknown` when the row or one of the two values is missing [Ref3]. |
| 262 | `    ev = {'thp_collapse_alloc': [], 'pgmigrate_success': []}` | `ev`: one empty list for each of the two system counters `thp_collapse_alloc` and `pgmigrate_success`. Each list will hold the intervals before which that counter rose. |
| 263 | `    for i in range(1, len(pages)):` | Loop over the intervals from the second one on. |
| 264 | `        for k in ev:` | Loop over the two counters. |
| 265 | `            a, b = pages[i - 1], pages[i]` | `a`: the `P` row of the interval before. `b`: the `P` row of this interval. |
| 266 | `            if a and b and a[k] is not None and b[k] is not None and b[k] > a[k]:` | Tests whether both rows exist, both hold a value for the counter, and the value of this interval is higher than the value of the interval before. |
| 267 | `                ev[k].append(i)` | If so, the number of this interval is appended to the list of the counter. Intervals are numbered from 0. |
| 268 | `    lv = [decide.level(r) for r in rates]` | `lv`: the level word of every interval, from its own rate. |
| 269 | `    changes, prev = [], None` | `changes`: the level changes, empty at the start. `prev`: the last interval that has a label. It is `None` at the start. |
| 270 | `    for i, l in enumerate(lv):` | Loop over the level words with their interval numbers. |
| 271 | `        if l == 'changing':` | Tests whether the rate lies between the two limits. |
| 272 | `            continue` | Such an interval is skipped. It neither starts nor ends a change. |
| 273 | `        if prev and prev[1] != l:` | Tests whether an earlier labelled interval exists and has the other label. |
| 274 | `            changes.append((prev[0], i))` | If so, one change is recorded: the number of that earlier interval and the number of this one. |
| 275 | `        prev = (i, l)` | This interval becomes the last labelled one. |
| 276 | `    info = [dict(frm=a, to=b, from_level=lv[a], to_level=lv[b], from_rate=rates[a], to_rate=rates[b], gap=b - a - 1) for a, b in changes]` | `info`: one record per change: the two interval numbers (`frm`, `to`), the two labels, the two rates, and `gap`, the count of intervals without a label between the two. |
| 277 | `    kb = [(x['kB_huge'], x['kB_total']) for x in pages if x and x['kB_total'] is not None and x['kB_huge'] is not None]` | `kb`: the pairs of `kB_huge` and `kB_total` of all `P` rows that hold both values. |
| 278 | `    steps = [rates[i] - rates[i - 1] for i in range(1, len(rates))]` | `steps`: the difference between each rate and the rate of the interval before it, in GB/s. |
| 279 | `    si = max(range(len(steps)), key=lambda i: abs(steps[i])) + 1 if steps else None` | `si`: the number of the interval that follows the largest absolute step. It is `None` for a process with one interval. |
| 280 | `    after = rates[si:] if si else rates` | `after`: the rates from interval `si` on. Without a step it is the whole list. |
| 281 | `    return dict(step_at=si, step_size=steps[si - 1] if si else None, after_min=min(after), after_max=max(after), tag=p.tag, cpu=p.cpu, no_thp=p.no_thp, utc=p.utc, rates=rates, median=median(rates), min=min(rates), max=max(rates),` | Starts the result. `step_at` and `step_size`: the interval after the largest step, and the signed size of that step. `after_min` and `after_max`: the lowest and the highest rate from that interval on. Then follow the tag, the CPU, the flag `no_thp` (the process ran with the option `--no-thp`), the UTC time of the header line, the list of rates, and their median, minimum and maximum. |
| 282 | `                cov={c: cov.count(c) for c in ('full', 'partial', 'none', 'unknown')}, events=ev, levels=level_counts(rates),` | Continues line 281. `cov`: the count of intervals for each coverage word. `events`: the two lists of line 262. `levels`: the counts per level. |
| 283 | `                changes=changes, change_info=info, cov_list=cov, kb_total=kb[0][1] if kb else None, kb_huge_min=min((x[0] for x in kb), default=None),` | Continues line 281. `changes` and `change_info`: the level changes. `cov_list`: the coverage word of every interval. `kb_total`: the buffer size in kB, from the first `P` row with values. `kb_huge_min`: the lowest `kB_huge` of the process. |
| 284 | `                kb_huge_max=max((x[0] for x in kb), default=None), step=p.step)` | Ends the result with `kb_huge_max`, the highest `kB_huge` of the process, and the step. |

### Function `b6_by_previous`: the rates of step B6 by the loop that ran before (lines 287 to 299)

| Line | Source | Explanation |
|---:|---|---|
| 287 | `def b6_by_previous(procs):` | Starts the function `b6_by_previous`. It sorts the rates of step B6 by the loop that ran directly before the interval. |
| 288 | `    """B6: the rate of every interval of an old read entry, grouped by CPU, entry and the entry that ran directly before it."""` | Docstring: step B6: the rate of every interval of an old read entry, grouped by CPU, by entry and by the entry that ran directly before it. |
| 289 | `    out = {}` | `out`: the result, empty at the start. |
| 290 | `    for p in procs:` | Loop over the processes. |
| 291 | `        for iv in p.ordered:` | Loop over the intervals of the process in time order. |
| 292 | `            if iv.entry == ab.REF or iv.pos == 0:` | Tests whether the interval is a reference interval (`asmread`) or stands at position 0 of the sequence. |
| 293 | `                continue` | Such an interval is skipped. |
| 294 | `            prev = p.seq[iv.pos - 1]` | `prev`: the entry that stands one position earlier in the sequence. |
| 295 | `            kind = 'asm read' if prev == ab.REF else 'an old read entry'` | `kind`: the text `asm read` when that entry is the reference kernel, and `an old read entry` for every other entry. |
| 296 | `            out.setdefault(p.cpu, {}).setdefault((iv.entry, kind), []).append(iv.rate)` | Appends the rate of the interval to the list for this CPU, this entry and this kind. `setdefault` creates the dictionary of the CPU and the list when they are first needed. |
| 297 | `    return out` | Returns the result. |

### Function `counter_facts`: facts from the counter rows of steps C1 and C2 (lines 300 to 320)

| Line | Source | Explanation |
|---:|---|---|
| 300 | `def counter_facts(procs):` | Starts the function `counter_facts`. It counts facts in the `C` rows of step C1 or C2. |
| 301 | `    """C1 and C2: facts from the C rows that the group table of analyze_bwx.py does not give."""` | Docstring: steps C1 and C2: facts from the `C` rows that the group table of `analyze_bwx.py` does not give. |
| 302 | `    n = used = read_rows = l1_lt_l2 = 0` | Four counts start at 0: `n` (all `C` rows), `used` (the rows that can be used), `read_rows` (the used rows of `asmread` that hold both refill counts) and `l1_lt_l2` (how many of those have fewer L1D refills than L2D refills). |
| 303 | `    cpu_share = []` | `cpu_share`: a list with one value per used row, empty at the start. |
| 304 | `    for p in procs:` | Loop over the processes. |
| 305 | `        for c in p.C:` | Loop over the `C` rows of the process. With the option `--count` the runner prints one `C` row per thread and interval. |
| 306 | `            n += 1` | Counts the row. |
| 307 | `            iv = p.raw.get((c['round'], c['pos']))` | `iv`: the interval with the round and the position of the row, or `None`. |
| 308 | `            t = next((x for x in iv.rows if x['tid'] == c['tid']), None) if iv else None` | `t`: the `T` row of the same thread in that interval, or `None`. |
| 309 | `            if t is None or None in (c['running'], c['enabled'], c['cputime']) or c['running'] < c['enabled'] or c['enabled'] <= 0:` | Tests whether the row cannot be used: no `T` row, a missing value of `running`, `enabled` or `cputime`, a running time below the enabled time, or an enabled time of 0 or less. By the plan, a row whose running time is below its enabled time is not used [Ref1]. |
| 310 | `                continue` | Such a row is skipped. |
| 311 | `            used += 1` | Counts the row as used. |
| 312 | `            cpu_share.append(c['cputime'] / (t['elapsed'] * 1e9))` | Appends the share of the CPU that the thread had: field 9 (`cputime_ns`) of the `C` row, divided by the elapsed time of the `T` row in ns. A value of 1 means that the thread ran on its CPU during the whole timed interval. |
| 313 | `            cnt = dict(zip(ab.EVENTS, c['counts'] + [None] * 5))` | `cnt`: a dictionary from the five event names to the five counts of the row. An event that the row does not hold gets `None`. |
| 314 | `            if iv.entry == ab.REF and cnt['l1d_refill'] is not None and cnt['l2d_refill'] is not None:` | Tests whether the interval is an `asmread` interval and the row holds both refill counts. |
| 315 | `                read_rows += 1` | Counts the row in `read_rows`. |
| 316 | `                l1_lt_l2 += cnt['l1d_refill'] < cnt['l2d_refill']` | Adds 1 to `l1_lt_l2` when the count of `l1d_refill` is lower than the count of `l2d_refill`. |
| 317 | `    return dict(rows=n, used=used, read_rows=read_rows, l1_lt_l2=l1_lt_l2,` | Starts the result: the four counts. |
| 318 | `                cpu_share_min=min(cpu_share) if cpu_share else None, cpu_share_median=median(cpu_share) if cpu_share else None)` | Ends the result. `cpu_share_min`: the lowest share over the used rows. `cpu_share_median`: their median. Both are `None` without a used row. No other line reads the median. |

### Functions `load_facts` and `utc_seconds`: the load readings of each step (lines 321 to 353)

| Line | Source | Explanation |
|---:|---|---|
| 321 | `def load_facts(sess):` | Starts the function `load_facts`. It collects the load readings of one session, per step. |
| 322 | `    """Per step: the load readings of the launches (header lines of the csv files and launches.txt)."""` | Docstring: per step: the load readings of the launches, from the header lines of the csv files and from `launches.txt`. |
| 323 | `    out = {}` | `out`: the result, empty at the start. |
| 324 | `    for step in Q1_STEPS:` | Loop over the seven steps of Q1. |
| 325 | `        g = [p for p in sess['procs'] if p.step == step]` | `g`: the processes of the step, complete or not. |
| 326 | `        if not g:` | Tests whether the step has no process. |
| 327 | `            continue` | Such a step is skipped. |
| 328 | `        l1 = [p.load1 for p in g if p.load1 is not None]` | `l1`: the 1-minute load average of the header line of each process. It is the first value behind the word `loadavg`. |
| 329 | `        run = [int(p.runnable.split('/')[0]) for p in g if re.fullmatch(r'\d+/\d+', p.runnable or '')]` | `run`: the runnable tasks of each header line. It is the number before the slash in the fourth value behind `loadavg`. A header line whose value does not have the form number, slash, number is left out. |
| 330 | `        run2 = [p.launch['runnable'] for p in g if p.launch]` | `run2`: the runnable tasks of the entry of `launches.txt`, for each process that has one. The run script reads this value before it reads the values of the header line [Ref5]. |
| 331 | `        waits = [p.waited_s for p in g if p.waited_s is not None]` | `waits`: the value `waited_s` of each header line. It is the time in seconds that the run script waited before the launch for at most 2 runnable tasks [Ref5]. |
| 332 | `        logins = [int(p.logins) for p in g if (p.logins or '').isdigit()]` | `logins`: the number of logged-in users of each header line, when the value is a number. |
| 333 | `        busy = [b for p in g if p.launch for b in p.launch['busiest'] if b[2] not in ('ps', 'bash')]` | `busy`: all process lines of the launches of the step, without the commands `ps` and `bash`. |
| 334 | `        own = {u for p in g if p.launch for u in p.launch['own_users']}` | `own`: the set of the accounts of the run script (line 131), over the launches of the step. |
| 335 | `        ts = [utc_seconds(p.folder['env'].get('start_utc')) for p in g]` | `ts`: for each process the start time of its step in seconds, from the value `start_utc` of the file `env.txt` of its folder. |
| 336 | `        top = max(busy, default=None)` | `top`: the entry of `busy` with the highest percent value. It is `None` when `busy` is empty. |
| 337 | `        out[step] = dict(n=len(g), first_utc=g[0].utc, last_utc=g[-1].utc, load_first=l1[0] if l1 else None, load_last=l1[-1] if l1 else None,` | Starts the facts of the step. `n`: the count of launches. `first_utc` and `last_utc`: the time of the header line of the first and of the last process. `load_first` and `load_last`: the 1-minute load average of the first and of the last header line. |
| 338 | `                         load_min=min(l1) if l1 else None, load_max=max(l1) if l1 else None, runnable_max=max(run) if run else None,` | Continues line 337. `load_min` and `load_max`: the lowest and the highest 1-minute load average. `runnable_max`: the highest count of runnable tasks of a header line. |
| 339 | `                         runnable2_max=max(run2) if run2 else None, n_launch_txt=len(run2), n_waited=sum(1 for w in waits if w > 0),` | Continues line 337. `runnable2_max`: the highest count of runnable tasks in `launches.txt`. `n_launch_txt`: the count of processes with an entry there. No other line reads it. `n_waited`: the count of launches with a wait above 0 s. |
| 340 | `                         wait_max=max(waits) if waits else None, logins_max=max(logins) if logins else None, top=top, own_users=own, busy_all=busy,` | Continues line 337. `wait_max`: the longest wait in seconds. `logins_max`: the highest number of logged-in users. Then `top`, `own_users` and `busy_all`, the list `busy`. |
| 341 | `                         t_start=min([v for v in ts if v is not None], default=None),` | Continues line 337. `t_start`: the earliest start time of the folders of the step, in seconds, or `None`. |
| 342 | `                         folders=sorted({p.folder['name'] for p in g}))` | Ends the facts with `folders`: the sorted names of the result folders of the step. |
| 343 | `    return out` | Returns the result. |
| 346 | `def utc_seconds(t):` | Starts the function `utc_seconds`. It turns a time text into a number. |
| 347 | `    """'2026-11-14T01:23:15Z' -> seconds since 1970, or None."""` | Docstring: a text such as `2026-11-14T01:23:15Z` becomes the seconds from the start of 1970, or `None`. |
| 348 | `    try:` | Starts a block. Line 350 catches its errors. |
| 349 | `        return calendar.timegm(time.strptime(t, '%Y-%m-%dT%H:%M:%SZ'))` | `time.strptime` reads the text in this form: year, month, day, the letter `T`, hour, minute, second, the letter `Z`. `calendar.timegm` turns the result into the seconds from 1970-01-01 00:00 UTC. |
| 350 | `    except (TypeError, ValueError):` | Catches two errors: `TypeError` for a missing value (`t` is `None`) and `ValueError` for a text of another form. |
| 351 | `        return None` | In both cases the function returns `None`. |

### Function `b4_case_facts`: how near the limits case (a) of a CPU lies (lines 354 to 369)

| Line | Source | Explanation |
|---:|---|---|
| 354 | `def b4_case_facts(P, cpu):` | Starts the function `b4_case_facts`. For one CPU of step B4 it describes case (a): low and high intervals that all have full huge-page coverage. |
| 355 | `    """Case (a) of a CPU: where the low and the high intervals with full coverage lie, and how near the limits they are."""` | Docstring: case (a) of a CPU: where the low and the high intervals with full coverage lie, and how near the limits they are. |
| 356 | `    g = [p for p in P if p['cpu'] == cpu]` | `g`: the records of `b4_process` for the processes of this CPU. |
| 357 | `    lows = [r for p in g for r, c in zip(p['rates'], p['cov_list']) if c == 'full' and r < LOW]` | `lows`: the rates of all intervals of these processes that have full coverage and a rate below `LOW` (69.0 GB/s). |
| 358 | `    highs = [r for p in g for r, c in zip(p['rates'], p['cov_list']) if c == 'full' and r > HIGH]` | `highs`: the rates of all intervals with full coverage and a rate above `HIGH` (70.5 GB/s). |
| 359 | `    lo_p = [p for p in g if sum(1 for r, c in zip(p['rates'], p['cov_list']) if c == 'full' and r < LOW) >= 10]` | `lo_p`: the processes that have at least 10 low intervals with full coverage of their own. |
| 360 | `    hi_p = [p for p in g if sum(1 for r, c in zip(p['rates'], p['cov_list']) if c == 'full' and r > HIGH) >= 10]` | `hi_p`: the processes that have at least 10 high intervals with full coverage of their own. |
| 361 | `    near_lo = sum(1 for r in lows if r > LOW - NEAR)` | `near_lo`: the count of low rates that lie less than `NEAR` (0.2 GB/s) below the low limit. These are the rates above 68.8 GB/s. |
| 362 | `    near_hi = sum(1 for r in highs if r < HIGH + NEAR)` | `near_hi`: the count of high rates that lie less than 0.2 GB/s above the high limit. These are the rates below 70.7 GB/s. |
| 363 | `    both = [p for p in lo_p if p in hi_p]` | `both`: the processes that are in `lo_p` and in `hi_p`. |
| 364 | `    return dict(cpu=cpu, n_low=len(lows), n_high=len(highs), low_min=min(lows, default=None), low_max=max(lows, default=None),` | Starts the result: the CPU, the counts `n_low` and `n_high` of the two lists, and the lowest and the highest low rate. |
| 365 | `                high_min=min(highs, default=None), high_max=max(highs, default=None), near_lo=near_lo, near_hi=near_hi,` | Continues line 364: the lowest and the highest high rate, `near_lo` and `near_hi`. |
| 366 | `                label_dependent=bool(lows and highs) and (near_lo * 2 > len(lows) or near_hi * 2 > len(highs)),` | Continues line 364. `label_dependent`: true when the CPU has low and high rates with full coverage, and more than half of the low rates are near the low limit or more than half of the high rates are near the high limit. The generated page then says that the case depends on the provisional limits. |
| 367 | `                n_lo_procs=len(lo_p), n_hi_procs=len(hi_p), both=both)` | Ends the result: the counts of `lo_p` and `hi_p`, and the list `both`. |

### Function `compute`: every value that the generated page prints (lines 370 to 427)

| Line | Source | Explanation |
|---:|---|---|
| 370 | `def compute(sessions):` | Starts the function `compute`. It computes every value that the generated page prints. |
| 371 | `    """Everything the page prints. sessions: the output of load()."""` | Docstring: `sessions` is the output of `load`. |
| 372 | `    D = dict(sessions={}, names=list(sessions))` | `D`: the result. `sessions`: the values per session, empty at the start. `names`: the session names in the order of the command line. |
| 373 | `    summary = ab.analyze({n: s['procs'] for n, s in sessions.items()})` | `summary`: the result of the decision analysis `ab.analyze` over the processes of all sessions. It holds the result of each step per session, and the word of each hypothesis over the sessions. |
| 374 | `    D['summary'] = summary` | Stores `summary` in `D`. |
| 375 | `    for name, s in sessions.items():` | Loop over the sessions. |
| 376 | `        res = summary['sessions'].get(name, {})` | `res`: the step results of the analysis for this session. |
| 377 | `        used = [p for p in s['procs'] if p.complete]` | `used`: the complete processes of the session. Only these enter the values below. |
| 378 | `        by = lambda st: [p for p in used if p.step == st]` | `by`: a small function that gives the used processes of one step. |
| 379 | `        x = dict(res=res, steps=[st for st in Q1_STEPS if any(p.step == st for p in s['procs'])], folders=s['folders'], other=s['other'],` | Starts `x`, the values of the session. `res`: the step results. `steps`: the steps of Q1 that have at least one process, complete or not. `folders` and `other`: the two folder lists of `load`. |
| 380 | `                 n_procs=len(s['procs']), n_used=len(used), left_out=[(p.step, p.tag, p.status if p.status != 'ok' else '; '.join(p.problems[:2]) or 'no interval')` | Continues line 379. `n_procs` and `n_used`: the counts of all processes and of the used ones. `left_out`: one entry per process that is not complete: the step, the tag and the reason. The reason is the status that the run script wrote (`killed` or `failed`). For a process without such a status it is the first two problems of the parser, or `no interval`. |
| 381 | `                                                                     for p in s['procs'] if not p.complete])` | Ends `left_out`: the loop over the processes that are not complete. |
| 382 | `        x['missing'] = [st for st in Q1_STEPS if st not in x['steps']]` | `missing`: the steps of Q1 without any process. |
| 383 | `        x['load'] = load_facts(s)` | `load`: the load facts per step. |
| 384 | `        x['pairs'] = {}` | `pairs`: the descriptions of the copy steps, empty at the start. |
| 385 | `        for step in ('B1', 'B2', 'B3', 'C2'):` | Loop over the four copy steps B1, B2, B3 and C2. |
| 386 | `            x['pairs'][step] = {k: dict(size=size, **describe_pairs(g, f, 'asmcopy', 'asmcopy2', 'asmcopy'))` | For each group of the step: the buffer size and the description of `describe_pairs`. The compared pair is the first kernel of the group against `asmcopy`. The A/A pair is `asmcopy2` against `asmcopy`. So `d` is the compared loop minus `asmcopy`, and `e` is `asmcopy2` minus `asmcopy`. |
| 387 | `                                for k, (f, size, g) in copy_groups(by(step), step).items()}` | Ends the expression: the groups come from `copy_groups` over the used processes of the step. |
| 388 | `        b18 = [p for p in by('B1') if p.bytes == 8 * MIB]` | `b18`: the used processes of B1 with a buffer of 8 MiB. |
| 389 | `        # the rule of a size without level, applied to 8 MiB: a description, never a decision` | Comment: the rule of a size without level is applied to 8 MiB here. The result is a description and never a decision. |
| 390 | `        x['b1_nolabel'] = ab.one_thread_group(b18, 'copy', 'asmcopy', 'asmcopy2', 'asmcopy', labelled=False)[0]['none'] if b18 else None` | `b1_nolabel`: the result of the decision rule `ab.one_thread_group` with `labelled=False` for these processes. In this form the rule takes every process, stable or not, and gives one result for the label `none`. It is `None` without such processes. |
| 391 | `        x['b6'] = describe_pairs(by('B6'), 'oldread', 'oldread@1M', 'oldread2', 'oldread') if by('B6') else None` | `b6`: the description of step B6. `d` is `oldread` minus `oldread@1M`. `e` is `oldread2` minus `oldread`. It is `None` without B6 processes. |
| 392 | `        x['b6_prev'] = b6_by_previous(by('B6'))` | `b6_prev`: the rates of B6 by the loop that ran before. |
| 393 | `        x['b4'] = [b4_process(p) for p in by('B4')]` | `b4`: one record of `b4_process` per used process of B4. |
| 394 | `        x['c1'] = [b4_process(p) for p in by('C1')]` | `c1`: the same for step C1. |
| 395 | `        x['b4_cases'] = {c: b4_case_facts(x['b4'], c) for c, v in res.get('B4', {}).get('per_cpu', {}).items() if 'a' in v['cases']}` | `b4_cases`: the facts of `b4_case_facts` for every CPU of B4 for which the analysis found case (a). |
| 396 | `        # reference rates per step and CPU: the reference intervals, and for B4 and C1 the intervals themselves` | Comment: the reference rates per step and CPU follow. They are the reference intervals, and for B4 and C1 the intervals themselves. |
| 397 | `        refs = []` | `refs`: the rows of the section on the reference rate, empty at the start. |
| 398 | `        for step in ('B1', 'B2', 'B3', 'B6', 'C2'):` | Loop over the five steps whose sequences hold reference intervals: B1, B2, B3, B6 and C2. |
| 399 | `            for cpu in sorted({p.cpu for p in by(step) if p.bytes == 8 * MIB}):` | Loop over the CPUs that have a used process with a buffer of 8 MiB in the step, in rising order. |
| 400 | `                g = [p for p in by(step) if p.cpu == cpu and p.bytes == 8 * MIB]` | `g`: these processes of the CPU. |
| 401 | `                first = [iv.rate for p in g for iv in p.ordered[:1] if iv.entry == ab.REF]` | `first`: the rate of the first interval of each process, when it is a reference interval. It is the first timed interval after the start of the process. |
| 402 | `                rest = [iv.rate for p in g for iv in p.ordered[1:] if iv.entry == ab.REF]` | `rest`: the rates of all later reference intervals of these processes. |
| 403 | `                st = [stable_label([iv.rate for iv in p.ordered if iv.entry == ab.REF]) for p in g]` | `st`: the stable label of each process, from all its reference intervals. |
| 404 | `                refs.append(dict(step=step, cpu=cpu, kind='reference intervals', first=first, rest=rest, n_procs=len(g),` | Starts one row: the step, the CPU, the kind `reference intervals`, the two lists and the process count. |
| 405 | `                                 n_stable_low=st.count('low'), n_stable_high=st.count('high'), **level_counts(first + rest),` | Continues line 404: the counts of stable low and stable high processes, and the four level counts over all reference rates of the row. |
| 406 | `                                 median=median(first + rest), min=min(first + rest), max=max(first + rest)))` | Ends the row: the median, the lowest and the highest of all reference rates of the row. |
| 407 | `        for step in ('B4', 'C1'):` | Loop over the steps B4 and C1. |
| 408 | `            for cpu in sorted({p.cpu for p in by(step)}):` | Loop over the CPUs of the step, in rising order. |
| 409 | `                for nothp in (False, True):` | Loop over the two page settings: first the processes without `--no-thp`, then those with it. |
| 410 | `                    g = [p for p in by(step) if p.cpu == cpu and p.no_thp == nothp]` | `g`: the used processes of this step, CPU and setting. |
| 411 | `                    if not g:` | Tests whether there is none. |
| 412 | `                        continue` | Then no row is made. |
| 413 | `                    r = [iv.rate for p in g for iv in p.ordered]` | `r`: the rates of all intervals of these processes. In these steps every interval is an `asmread` interval and is its own reference. |
| 414 | `                    st = [stable_label([iv.rate for iv in p.ordered]) for p in g]` | `st`: the stable label of each process, from all its intervals. |
| 415 | `                    refs.append(dict(step=step, cpu=cpu, kind='4 KiB pages asked' if nothp else '2 MiB pages asked', first=[], rest=r, n_procs=len(g),` | Starts one row. Its kind is `4 KiB pages asked` for the processes with `--no-thp` and `2 MiB pages asked` for the others. The list `first` stays empty. |
| 416 | `                                     n_stable_low=st.count('low'), n_stable_high=st.count('high'), **level_counts(r), median=median(r), min=min(r), max=max(r)))` | Ends the row: the counts of stable processes, the level counts, and the median, the lowest and the highest rate. |
| 417 | `        x['refs'] = refs` | Stores the rows in `x`. |
| 418 | `        x['cfacts'] = {st: counter_facts(by(st)) for st in ('C1', 'C2') if by(st)}` | `cfacts`: the facts of `counter_facts` for each of the steps C1 and C2 that has used processes. |
| 419 | `        x['b1_8m_medians'] = [(p.cpu, k, p.no_thp, median(iv.rate for iv in v)) for p in by('B1') if p.bytes == 8 * MIB for k, v in p.rate_by_entry.items()]` | `b1_8m_medians`: one entry for each used process of B1 at 8 MiB and each entry of its sequence: the CPU, the entry, the flag `no_thp` and the median rate of the intervals of that entry in the process. |
| 420 | `        x['proc_medians'] = {st: [(p.cpu, k, p.no_thp, median(iv.rate for iv in v)) for p in by(st) for k, v in p.rate_by_entry.items()] for st in Q1_STEPS}` | `proc_medians`: the same list for every step of Q1, over all its used processes. |
| 421 | `        starts = [utc_seconds(f['env'].get('start_utc')) for f in s['folders']]` | `starts`: the start time of each folder with processes, in seconds. |
| 422 | `        x['t_start'] = min([t for t in starts if t is not None], default=None)` | `t_start`: the earliest of them, or `None`. It is the start of the Q1 steps of the session. |
| 423 | `        D['sessions'][name] = x` | Stores `x` under the session name. |
| 424 | `    D['hyp'] = hypotheses(D)` | `hyp`: the rows of the hypothesis table, from `hypotheses`. |
| 425 | `    return D` | Returns `D`. |

### `rule_word`, `TR` and `cpu_list`: words for the hypothesis table (lines 428 to 442)

| Line | Source | Explanation |
|---:|---|---|
| 428 | `def rule_word(h):` | Starts the function `rule_word`. |
| 429 | `    """The word of analyze_bwx.two_sessions as one of the five words of rule 11, and a note."""` | Docstring: it gives the word of the function `two_sessions` of `analyze_bwx.py` as one of the five words of rule 11, and a note. |
| 430 | `    w = h['word']` | `w`: the word of the analysis for one hypothesis. |
| 431 | `    if w.startswith('not rejected (one session only'):` | Tests whether the word starts with `not rejected (one session only`. The analysis gives this long form when only one session has a result for the hypothesis and that result is not `not observed`. On a page with one session this is the case for every hypothesis with such a result. |
| 432 | `        return 'not rejected', 'One session only. The word "rejected" needs two sessions.'` | Then the function returns the plain word `not rejected` and a note: one session only, and the word `rejected` needs two sessions. |
| 433 | `    return w, ''` | In every other case it returns the word unchanged and an empty note. |
| 436 | `TR = {'fail': 'The bounded prediction failed', 'hold': 'The bounded prediction held', 'not observed': 'Not observed', 'not resolved': 'Not resolved'}` | `TR`: the sentence start that the generated page prints for the flag of one session. `fail`: the bounded prediction failed. `hold`: it held. `not observed` and `not resolved` are printed with a capital letter. |
| 439 | `def cpu_list(pairs, nd=2):` | Starts the function `cpu_list`. It prints one value per CPU. |
| 440 | `    return ', '.join('CPU %s: %s' % (c, f2(a, nd)) for c, a in pairs)` | Returns one text: for each pair the word `CPU`, the CPU number, a colon and the value with `nd` decimals. Commas stand between the pairs. |

### `b6_position`, `b6_caveat`, `change_words`: sentences built from computed values (lines 443 to 487)

| Line | Source | Explanation |
|---:|---|---|
| 443 | `def b6_position(D):` | Starts the function `b6_position`. Over all sessions it collects the values that show whether the place of a loop in the B6 sequence changes its rate. |
| 444 | `    """The position effect of B6 over all sessions, as computed values. None without B6."""` | Docstring: the position effect of B6 over all sessions, as computed values. `None` without B6. |
| 445 | `    G = [(s, x['b6'], x['b6_prev']) for s, x in D['sessions'].items() if x['b6']]` | `G`: one entry per session with B6 data: the session name, the description of line 391 and the rates of line 392. |
| 446 | `    if not G:` | Tests whether no session has B6 data. |
| 447 | `        return None` | Then the function returns `None`. |
| 448 | `    pcs = [v for _, g, _ in G for v in g['per_cpu'].values()]` | `pcs`: the values per CPU of all sessions, one entry per session and CPU. |
| 449 | `    one_mib = [median(bp[c][('oldread@1M', 'asm read')]) - median(bp[c][('oldread@1M', 'an old read entry')])` | Starts `one_mib`: one value per session and CPU. It is the median rate of `oldread@1M` directly after an `asmread` interval, minus its median rate directly after an old read entry, in GB/s. |
| 450 | `               for _, _, bp in G for c in bp if bp[c].get(('oldread@1M', 'asm read')) and bp[c].get(('oldread@1M', 'an old read entry'))]` | Ends `one_mib`: only a CPU that has both lists gives a value. |
| 451 | `    return dict(d=[v['median_d'] for v in pcs], first=[v['d_first'] for v in pcs], second=[v['d_second'] for v in pcs],` | Starts the result. `d`: the median `d` of each CPU. `first`: `d_first` of each CPU, the median pair value with `oldread` at 8 MiB timed first. In the B6 sequence that interval follows a reference interval. `second`: `d_second`, the same with `oldread` at 8 MiB timed second, behind `oldread@1M`. |
| 452 | `                spread=[v['aa_spread'] for v in pcs], single=[v['aa_single_max'] for v in pcs],` | Continues line 451. `spread`: the A/A spread of each CPU. `single`: the largest single A/A pair of each CPU. No other line reads `single`. |
| 453 | `                second_inside=all(abs(v['d_second']) < v['aa_spread'] for v in pcs),` | Continues line 451. `second_inside`: true when on every CPU the absolute `d_second` is smaller than the A/A spread. |
| 454 | `                first_outside=all(abs(v['d_first']) > v['aa_spread'] for v in pcs),` | Continues line 451. `first_outside`: true when on every CPU the absolute `d_first` is larger than the A/A spread. |
| 455 | `                aa_n=sum(v['aa_pos_n'] for v in pcs), aa_neg=sum(v['aa_pos_neg'] for v in pcs), aa_med=[v['aa_pos_median'] for v in pcs], one_mib=one_mib)` | Ends the result. `aa_n`: the count of all A/A pairs. `aa_neg`: how many of them have the interval timed first as the slower one. `aa_med`: the median of `aa_pos` of each CPU. Then `one_mib`. |
| 458 | `def b6_caveat(D):` | Starts the function `b6_caveat`. It writes the sentences that say what the difference of B6 part 2 is made of. |
| 459 | `    """Sentences on what the resolved difference of B6 part 2 consists of. Every sentence is built from computed values."""` | Docstring: sentences on what the resolved difference of B6 part 2 consists of. Every sentence is built from computed values. |
| 460 | `    q = b6_position(D)` | `q`: the values of `b6_position`. |
| 461 | `    if not q:` | Tests whether there are none. |
| 462 | `        return [], False` | Then the function returns an empty list and `False`. |
| 463 | `    t = [f'The median d per CPU is {rng(min(q["d"]), max(q["d"]), signed=True)} GB/s. It is the median over pairs in two orders.',` | Starts `t`, the list of sentences. Sentence 1: the range of the median `d` per CPU in GB/s, and that it is a median over pairs in two orders. |
| 464 | `         f'With old read at 8 MiB timed first, directly after an asm read interval, the median pair value per CPU is {rng(min(q["first"]), max(q["first"]), signed=True)} GB/s.',` | Sentence 2: the range of the median pair value per CPU with `oldread` at 8 MiB timed first, directly after an `asmread` interval. |
| 465 | `         f'With old read at 8 MiB timed second, after old read at 1 MiB, it is {rng(min(q["second"]), max(q["second"]), signed=True)} GB/s.']` | Sentence 3: the same range with `oldread` at 8 MiB timed second, after `oldread@1M`. |
| 466 | `    if q['second_inside']:` | Tests `second_inside`. |
| 467 | `        t.append(f'The second value is inside the A/A spread on every CPU (A/A spreads: {rng(min(q["spread"]), max(q["spread"]))} GB/s).')` | Then a sentence is added: the second value is inside the A/A spread on every CPU, with the range of the A/A spreads. |
| 468 | `    if q['aa_n']:` | Tests whether A/A pairs exist. |
| 469 | `        t.append(f'The A/A pairs are two old read intervals at 8 MiB, one directly after the other, after an asm read interval. In {q["aa_neg"]} of {q["aa_n"]} such pairs the first interval is slower than the second '` | Then two sentences are added. The first says what the A/A pairs of B6 are: two intervals of old read at 8 MiB, one directly after the other, behind an `asmread` interval. The second gives in how many of all such pairs the first interval is slower than the second. |
| 470 | `                 f'(median per CPU: {rng(min(q["aa_med"]), max(q["aa_med"]), signed=True)} GB/s). The A/A spread is a median over both orders, so it does not show this difference.')` | Continues line 469: the range of the median per CPU of that difference. A third sentence follows: the A/A spread is a median over both orders, so it does not show this difference. |
| 471 | `    if q['one_mib']:` | Tests whether `one_mib` has values. |
| 472 | `        t.append(f'Old read at 1 MiB after asm read minus old read at 1 MiB after old read is {rng(min(q["one_mib"]), max(q["one_mib"]), signed=True)} GB/s (median per CPU).')` | Then a sentence is added with the range of the values of line 449. |
| 473 | `    effect = q['second_inside'] and q['first_outside'] and q['aa_n'] and q['aa_neg'] * 10 >= q['aa_n'] * 9` | `effect`: true when four conditions hold: `second_inside`, `first_outside`, A/A pairs exist, and in at least 90 % of them the first interval is the slower one. The last test is written as `aa_neg` times 10 against `aa_n` times 9. |
| 474 | `    if effect:` | Tests `effect`. |
| 475 | `        t.append('So these data do not show that the rate of old read depends on the buffer size. They show that old read at 8 MiB is slower in the interval directly after an asm read interval.')` | Then the conclusion is added in two sentences. These data do not show that the rate of old read depends on the buffer size. They show that old read at 8 MiB is slower in the interval directly after an `asmread` interval. |
| 476 | `    return t, bool(effect)` | Returns the sentences and `effect` as true or false. |
| 479 | `def change_words(p):` | Starts the function `change_words`. It writes one sentence per level change of a process of B4 or C1. |
| 480 | `    out = []` | `out`: the sentences, empty at the start. |
| 481 | `    for ch in p['change_info']:` | Loop over the change records of the process (line 276). |
| 482 | `        gap = f', with {pl(ch["gap"], "interval", "intervals")} between the limits between them' if ch['gap'] else ''` | `gap`: a clause with the count of intervals between the limits that lie between the two intervals of the change. It is empty when there is none. |
| 483 | `        out.append(f'Process {p["tag"]} (step {p["step"]}, CPU {p["cpu"]}) goes from {ch["from_level"]} ({fx(ch["from_rate"])} GB/s, interval {ch["frm"]}) '` | Starts the sentence: the tag, the step and the CPU of the process, then the level, the rate in GB/s and the interval number before the change. |
| 484 | `                   f'to {ch["to_level"]} ({fx(ch["to_rate"])} GB/s, interval {ch["to"]}){gap}.')` | Ends the sentence: the level, the rate and the interval number after the change, then the clause `gap`. |
| 485 | `    return out` | Returns the sentences. |

### `hypotheses`: start, the helper `add` and the note on the limits (lines 488 to 503)

| Line | Source | Explanation |
|---:|---|---|
| 488 | `def hypotheses(D):` | Starts the function `hypotheses`. It builds the rows of the hypothesis table. |
| 489 | `    """One row per hypothesis (H4 has one row per level label). Each row: the word of rule 11 over all sessions, per session the` | Docstring: one row per hypothesis. H4 has one row per level label. The list of what a row holds starts here: the word of rule 11 over all sessions, and values per session. |
| 490 | `    result, the processes that the rule uses and the A/A spread, notes (description and limits), and items open for the user."""` | Docstring: the values per session are the result, the processes that the rule uses and the A/A spread. A row also holds notes (description and limits) and items that are open for the user. |
| 491 | `    S, hy = D['sessions'], D['summary']['hypotheses']` | `S`: the values per session. `hy`: the hypothesis entries of the analysis. Each entry holds the word over the sessions and one flag per session. |
| 492 | `    one = len(S) < 2` | `one`: true when the input holds fewer than 2 sessions. |
| 493 | `    rows = []` | `rows`: the result, empty at the start. |
| 495 | `    def add(h, step, word, per=None, notes=(), open_=(), n=0):` | Starts the inner function `add`. It appends one row. Its arguments: the name `h` of the hypothesis, the step, the word, `per` (the values per session), the notes, `open_` (the items for the user) and `n` (a process count). |
| 496 | `        per = per or {}` | A missing `per` becomes an empty dictionary. |
| 497 | `        basis = ' '.join('Session %s: %s' % (s, v['result']) for s, v in per.items())` | `basis`: the results of all sessions as one text. Each starts with the word `Session` and the session name. |
| 498 | `        rows.append(dict(h=h, step=step, word=word, per=per, notes=[t for t in notes if t], open=[t for t in open_ if t], n=n,` | Starts the row. Empty notes and empty open items are left out. |
| 499 | `                         basis=(basis + ' ' + ' '.join(t for t in notes if t)).strip()))` | Ends the row with `basis`, to which the notes are appended. No line of this file reads `basis`. The tests in `test_q1.py` read it. |
| 501 | `    limits_note = lambda cpus: ('The word depends on the provisional level limits, which are not validated. '` | Starts `limits_note`, a small function that writes one note. Its first sentence: the word depends on the provisional level limits, which are not validated. |
| 502 | `                                + ('Stable processes exist only on CPU %s, and all of them are stable low.' % ', '.join(map(str, cpus)) if cpus else 'No process is stable at one level.'))` | Its second sentence, for a list of CPUs: stable processes exist only on these CPUs, and all of them are stable low. For an empty list: no process is stable at one level. The words "all of them are stable low" are typed. No code tests them: the callers pass every CPU with a stable process, low or high (line 619, line 664). |

### `hypotheses`: the row of H1 (step B6) (lines 504 to 531)

| Line | Source | Explanation |
|---:|---|---|
| 504 | `    # ---- H1` | Comment: the row of H1 follows. |
| 505 | `    h = hy.get('H1 (B6)')` | `h`: the entry of the analysis for H1 from step B6, or `None`. In the analysis a session gets the flag `fail` when a difference is resolved: old read at 8 MiB between stable low and stable high processes of one CPU (part 1), or old read at 8 MiB against old read at 1 MiB (part 2). With two or more sessions the same resolved result must occur in every session. The word over the sessions is `rejected` only when at least 2 sessions are given and every one has the flag `fail` [Ref3]. |
| 506 | `    if h:` | Tests whether the analysis has an entry for H1. |
| 507 | `        w, note = rule_word(h)` | `w`: the word of the entry as one of the five words. `note`: the note for an input with one session, or an empty text. |
| 508 | `        per = {}` | `per`: the values per session, empty at the start. |
| 509 | `        for s, x in S.items():` | Loop over the sessions. |
| 510 | `            if 'B6' not in x['res']:` | Tests whether the session has no result for step B6. |
| 511 | `                continue` | Such a session is skipped. |
| 512 | `            r = x['res']['B6']` | `r`: the result of the analysis for B6 in this session. |
| 513 | `            sz = r['size']['labels']['none']` | `sz`: the result of part 2 of the rule (8 MiB against 1 MiB). It stands under the label `none`: every process is used. |
| 514 | `            p1 = sorted({v['decision'] for v in r['state'].values()})` | `p1`: the decision words of part 1 over the CPUs. Each word stands once, in sorted order. |
| 515 | `            nres = sum(1 for v in sz['per_cpu'].values() if v['decision'] == 'resolved')` | `nres`: the count of CPUs on which part 2 is resolved. |
| 516 | `            per[s] = dict(result='%s. Part 1 (low against high level): %s (stable high processes: %d). Part 2 (8 MiB against 1 MiB): %s%s, with %d of %s resolved.' % (` | Starts the entry of the session with `result`, one text. It holds the sentence for the flag of the session. Then part 1: the decision words and the count of stable high processes. Then part 2: the decision over the CPUs with its sign, and on how many of the CPUs it is resolved. |
| 517 | `                TR.get(h['per_session'].get(s), h['per_session'].get(s)), ' and '.join(p1), sum(v['n_high'] for v in r['state'].values()),` | Continues line 516 with the first three values of the text: the sentence of `TR` for the flag (the flag itself when `TR` does not hold it), the words of `p1` joined with `and`, and the sum over the CPUs of the stable high processes. |
| 518 | `                sz['decision'], ab.sign_txt(sz['sign']), nres, pl(len(sz['per_cpu']), 'CPU', 'CPUs')),` | Continues line 516 with the last values: the decision of part 2, its sign as `(+)` or `(-)` from `ab.sign_txt`, `nres`, and the CPU count with the word `CPU` or `CPUs`. |
| 519 | `                used='%d of %d (part 2 uses every process)' % (len(x['b6']['recs']), len(x['b6']['recs'])),` | Continues line 516. `used`: the count of described B6 processes, printed twice as "N of N", with the remark that part 2 uses every process. |
| 520 | `                spread=cpu_list((c, v['aa_spread']) for c, v in x['b6']['per_cpu'].items()))` | Ends the entry. `spread`: the A/A spread of every CPU from the description (line 228), printed by `cpu_list`. |
| 521 | `        cav, effect = b6_caveat(D)` | `cav`: the sentences of `b6_caveat`. `effect`: its flag for a position effect. |
| 522 | `        part1_none = all(v['decision'] == 'not observed' for x in S.values() if 'B6' in x['res'] for v in x['res']['B6']['state'].values())` | `part1_none`: true when part 1 is `not observed` on every CPU of every session with B6. |
| 523 | `        notes = ['The result comes from part 2 only. Part 1 is "not observed": no CPU has stable high processes.' if part1_none else ''] + cav + [note]` | `notes`: first, when `part1_none` holds, a typed sentence: the result comes from part 2 only, and part 1 is "not observed" for the lack of stable high processes on every CPU. The rule also gives `not observed` for a CPU with fewer than 2 stable low processes, and the sentence does not test which of the two is missing. Then follow the sentences `cav` and the text `note`. |
| 524 | `        open_ = []` | `open_`: the items for the user, empty at the start. |
| 525 | `        if effect and w == 'rejected':` | Tests two things: the position effect is shown, and the word is `rejected`. |
| 526 | `            open_.append('H1. Strict output of the rule: "rejected", because part 2 is resolved in every session. A recount of the words by a second agent gives the same word and adds the limit that the difference is a position effect. No file holds that recount. '` | Then one item is added, as typed text. Its first part names the strict word of the rule, `rejected`, with its reason. It also reports a recount of the words by a second agent, and says that no file holds that recount. |
| 527 | `                         'The check of this page proposes "not resolved" under the last paragraph of handoff B.10, because the pair definition does not fit the B6 data: a pair value contains the position difference. '` | Continues line 526: the item names the other word, `not resolved`, which the check of the generated page proposes under the last paragraph of section B.10 of the handoff note. The reason given: a pair value of B6 holds the position difference, so the pair definition does not fit these data. |
| 528 | `                         'The choice between the two words is a judgment.')` | Ends the item: it leaves the choice between the two words to a judgment. |
| 529 | `        add('H1', 'B6', w, per, notes, open_, n=sum(len(x['b6']['recs']) for x in S.values() if x['b6']))` | Appends the row of H1 for step B6 with the word `w`. `n` is the count of described B6 processes over all sessions. |
| 530 | `    else:` | The next line runs when the analysis has no entry for H1. |
| 531 | `        add('H1', 'B6', 'not tested', notes=['No process of step B6 is in the input.'])` | Appends the row of H1 with the word `not tested` and the note that no process of step B6 is in the input. |

### `hypotheses`: the row of H2 (steps B4 and C1, description only) (lines 532 to 549)

| Line | Source | Explanation |
|---:|---|---|
| 532 | `    # ---- H2: the plan names no bounded prediction for H2 in Parts B and C, so rule 11 gives "not tested"` | Comment: the plan names no bounded prediction for H2 in Parts B and C. So rule 11 gives the word "not tested". |
| 533 | `    per = {}` | `per`: the values per session, empty at the start. |
| 534 | `    for s, x in S.items():` | Loop over the sessions. |
| 535 | `        P = x['b4'] + x['c1']` | `P`: the process records of B4 and of C1 of the session, in one list. |
| 536 | `        if not P:` | Tests whether the session has none. |
| 537 | `            continue` | Such a session is skipped. |
| 538 | `        ch = [t for p in P for t in change_words(p)]` | `ch`: the sentences of `change_words` for all these processes. |
| 539 | `        nh = sum(1 for p in P if p['levels']['high'] == p['levels']['n'])` | `nh`: the count of processes whose intervals are all high. |
| 540 | `        big = sum(1 for p in P if p['step_size'] is not None and abs(p['step_size']) > 1)` | `big`: the count of processes whose largest step between two neighbouring intervals is above 1 GB/s in absolute value. |
| 541 | `        per[s] = dict(result='Description, no decision. %s between low and high inside a process, in %s of B4 and C1. %s%s high in all intervals. In %s the largest step between two neighbouring intervals is above 1 GB/s.' % (` | Starts the entry of the session with `result`. The text starts with the words `Description, no decision.` Then it gives the count of changes between low and high inside a process, the count of processes of B4 and C1, the change sentences, the count of processes that were high in all intervals, and the count of processes whose largest step is above 1 GB/s. |
| 542 | `            pl(sum(len(p['change_info']) for p in P), 'change', 'changes'), pl(len(P), 'process', 'processes'), ''.join(t + ' ' for t in ch), pl(nh, 'process was', 'processes were'), pl(big, 'process', 'processes')),` | Continues line 541 with the five values of the text, each with its singular or plural word from `pl`. |
| 543 | `            used='none (no rule)', spread='no A/A pair')` | Ends the entry. `used` is the text `none (no rule)`. `spread` is the text `no A/A pair`. |
| 544 | `    if per:` | Tests whether at least one session has such processes. |
| 545 | `        add('H2', 'B4, C1', 'not tested', per, ['The plan gives H2 no bounded prediction in Parts B and C. So no rule gives a word, and the word of rule 11 is "not tested". '` | Then the row of H2 is appended for the steps B4 and C1, with the word `not tested`. Its note starts here: the plan gives H2 no bounded prediction in Parts B and C, so no rule gives a word. |
| 546 | `                                                'The second half of H2 (the high level can stay for the next process) has no test here, because each process allocates a new buffer.'],` | Continues the note: the second half of H2 (the high level can stay for the next process) has no test here, for the reason that each process allocates a new buffer. |
| 547 | `            n=sum(len(x['b4']) + len(x['c1']) for x in S.values()))` | Ends the call. `n` is the count of B4 and C1 processes over all sessions. |
| 548 | `    else:` | The next line runs when no session has such processes. |
| 549 | `        add('H2', 'B4, C1', 'not tested', notes=['No process of steps B4 and C1 is in the input.'])` | Appends the row of H2 with the word `not tested` and the note that no process of the steps B4 and C1 is in the input. |

### `hypotheses`: the rows of H3a (step B4) and H3b (lines 550 to 603)

| Line | Source | Explanation |
|---:|---|---|
| 550 | `    # ---- H3a` | Comment: the row of H3a follows. |
| 551 | `    h = hy.get('H3a (B4)')` | `h`: the entry of the analysis for H3a from step B4, or `None`. H3a predicts that every low interval has less than full huge-page coverage and every high interval has full coverage. In the analysis a session gets the flag `fail` when case (a) or case (b) occurs on one of its CPUs, and `not observed` when neither occurs. Case (a): the CPU has at least 10 low and at least 10 high intervals with full coverage. Case (b): the same with no huge page. The word `rejected` also needs one CPU that has a case in every session [Ref2][Ref3]. |
| 552 | `    if h:` | Tests whether the analysis has an entry for H3a. |
| 553 | `        w, note = rule_word(h)` | `w` and `note`: the word as one of the five words, and the note for one session. |
| 554 | `        per, notes, dep = {}, [], {}` | Three empty values: `per` (per session), `notes`, and `dep` (per session the CPUs whose case depends on the limits). |
| 555 | `        for s, x in S.items():` | Loop over the sessions. |
| 556 | `            pc = x['res'].get('B4', {}).get('per_cpu', {})` | `pc`: the result of B4 per CPU from the analysis. It is empty when the session has no B4 result. |
| 557 | `            if not pc:` | Tests whether it is empty. |
| 558 | `                continue` | Such a session is skipped. |
| 559 | `            flag = h['per_session'].get(s)` | `flag`: the flag of the session. |
| 560 | `            casec = [c for c, v in pc.items() if v['cases']]` | `casec`: the CPUs with a case. |
| 561 | `            all_dep = bool(casec) and all(x['b4_cases'].get(c, {}).get('label_dependent') for c in casec)` | `all_dep`: true when there is such a CPU and every such CPU has `label_dependent` set (line 366). A CPU with case (b) alone has no facts in `b4_cases`, and so it makes `all_dep` false. |
| 562 | `            t = ('The rule finds a case, and the case depends on the provisional limits.' if flag == 'fail' and all_dep else` | Starts `t`, the result text of the session. For the flag `fail` with `all_dep`: the rule finds a case, and the case depends on the provisional limits. |
| 563 | `                 'The bounded prediction failed.' if flag == 'fail' else 'Not observed: neither case occurred on a CPU.')` | For the flag `fail` without `all_dep`: the bounded prediction failed. For every other flag: not observed, as neither case occurred on a CPU. |
| 564 | `            for c, v in pc.items():` | Loop over the CPUs of the session. |
| 565 | `                if not v['cases']:` | Tests whether the CPU has no case. |
| 566 | `                    continue` | Such a CPU adds nothing to the text. |
| 567 | `                iv = v['intervals']` | `iv`: the interval counts of the CPU per level and coverage, from the analysis. |
| 568 | `                t += ' CPU %s: case (%s).' % (c, ') and ('.join(v['cases']))` | Adds the CPU and its cases to the text, for example `CPU 2: case (a).` |
| 569 | `                if 'a' in v['cases']:` | Tests whether case (a) occurred. |
| 570 | `                    t += ' %d low and %d high intervals with full coverage.' % (iv['low']['full'], iv['high']['full'])` | Then the counts of low and of high intervals with full coverage are added. |
| 571 | `                if 'b' in v['cases']:` | Tests whether case (b) occurred. |
| 572 | `                    t += ' %d low and %d high intervals with no huge page.' % (iv['low']['none'], iv['high']['none'])` | Then the counts of low and of high intervals with no huge page are added. |
| 573 | `                f = x['b4_cases'].get(c)` | `f`: the facts of `b4_case_facts` for this CPU, or `None`. |
| 574 | `                if f:` | Tests whether the facts exist. |
| 575 | `                    if f['label_dependent']:` | Tests whether the case depends on the limits. |
| 576 | `                        if f['near_lo'] * 2 > f['n_low']:` | Tests whether more than half of the low intervals are near the low limit. |
| 577 | `                            t += ' %d of the %d low intervals lie less than %g GB/s below the limit of %g GB/s.' % (f['near_lo'], f['n_low'], NEAR, LOW)` | Then a sentence is added: how many of the low intervals lie less than 0.2 GB/s below the limit of 69 GB/s. |
| 578 | `                        if f['near_hi'] * 2 > f['n_high']:` | Tests whether more than half of the high intervals are near the high limit. |
| 579 | `                            t += ' %d of the %d high intervals lie less than %g GB/s above the limit of %g GB/s.' % (f['near_hi'], f['n_high'], NEAR, HIGH)` | Then a sentence is added: how many of the high intervals lie less than 0.2 GB/s above the limit of 70.5 GB/s. |
| 580 | `                    notes.append('Session %s, CPU %s: %s' % (s, c, 'one process has at least 10 low and at least 10 high intervals with full coverage.' if len(f['both']) == 1 else '%d processes have at least 10 low and at least 10 high intervals with full coverage.' % len(f['both']) if f['both'] else 'the low and the high intervals are in different processes. No process has both.'))` | Appends one note for this session and CPU. It says where the low and the high intervals with full coverage lie: in one process that has at least 10 of each, in several such processes with their count, or in different processes with no process that has both. |
| 581 | `            dep[s] = [c for c, f in x['b4_cases'].items() if f['label_dependent']], [c for c, v in pc.items() if v['cases']]` | `dep` for the session: the CPUs whose case (a) depends on the limits, and all CPUs with a case. |
| 582 | `            per[s] = dict(result=t, used='%d of %d' % (len(x['b4']), len(x['b4'])), spread='no A/A pair')` | The entry of the session: `result` is `t`. `used` is the count of B4 processes, printed twice as "N of N". `spread` is the text `no A/A pair`. |
| 583 | `        # low intervals with full coverage on one CPU in every session: the first half of the prediction` | Comment: the next lines look for low intervals with full coverage on one CPU in every session. They concern the first half of the prediction. |
| 584 | `        lowfull = {s: {c: v['intervals']['low']['full'] for c, v in x['res'].get('B4', {}).get('per_cpu', {}).items()} for s, x in S.items() if x['res'].get('B4')}` | `lowfull`: for each session with a B4 result, per CPU the count of low intervals with full coverage. |
| 585 | `        if len(lowfull) > 1:` | Tests whether more than one session has a B4 result. |
| 586 | `            for c in sorted(set.intersection(*[set(v) for v in lowfull.values()])):` | Loop over the CPUs that occur in every such session, in rising order. |
| 587 | `                if all(v[c] >= 10 for v in lowfull.values()):` | Tests whether the CPU has at least 10 such intervals in every session. |
| 588 | `                    notes.append('CPU %s has low intervals with full coverage in every session (%s). H3a predicts that every low interval has less than full coverage. The rule of the handoff counts this only together with high intervals.' % (` | Then a note is appended for the CPU. It says that the CPU has low intervals with full coverage in every session, that the first half of the prediction of H3a excludes them, and that the rule of the handoff note counts them only together with high intervals. |
| 589 | `                        c, ', '.join('%s: %d' % (s, v[c]) for s, v in lowfull.items())))` | Continues line 588 with the values of the note: the CPU, and the count for each session. |
| 590 | `        open_ = []` | `open_`: the items for the user, empty at the start. |
| 591 | `        other = h.get('word_without_the_same_cpu_condition')` | `other`: the word that the analysis gives without the same-CPU condition. |
| 592 | `        if other and other != w:` | Tests whether that word exists and differs from `w`. With two failing sessions that have their case on different CPUs, `other` is `rejected` and `w` is `not rejected`. With one session whose flag is `fail`, the analysis gives `other` in the long form of line 431, and `w` is the short form. So the two differ in that case too, and the item of lines 594 to 596 is added for one session. |
| 593 | `            where = ', '.join('session %s: CPU %s' % (s, ' and '.join(map(str, c)) or 'none') for s, c in h['cpus_with_a_case'].items())` | `where`: for each session the CPUs with a case, or the word `none`. |
| 594 | `            open_.append(f'H3a. Strict output of the analysis script: "{w}". The handoff gives "rejected" only if one CPU shows a case in both sessions (handoff B.10, deviation A13). No CPU does ({where}). '` | Appends one item, typed text with computed values. It gives the strict word `w` of the analysis script, the condition of the handoff note for "rejected" (one CPU with a case in both sessions), and the list `where` of the CPUs with a case per session. |
| 595 | `                         f'Second reading: "{other}". The analysis script prints this word as the word without the same-CPU condition. Reason: step B4 of the plan has no same-CPU condition ("H3a is rejected if low and high intervals are both observed with full coverage"), '` | Continues line 594: the item gives the second reading with the word `other`, and starts its reason: step B4 of the plan has no same-CPU condition. A quote of the plan follows. |
| 596 | `                         'and by rule 11 the bounded prediction failed in both sessions. Which wording applies is a judgment.')` | Ends the item: by rule 11 the prediction failed in both sessions, and the choice of the wording is a judgment. The words "No CPU does" of line 594 and "in both sessions" are typed. They fit an input of two sessions. |
| 597 | `        only_dep = [s for s, (d, allc) in dep.items() if allc and set(d) == set(allc)]` | `only_dep`: the sessions that have a case and in which every CPU with a case depends on the limits. |
| 598 | `        if only_dep:` | Tests whether there is such a session. |
| 599 | `            open_.append('H3a and the limits. In session %s every case depends on the provisional limits (see the row above and section B4). If such a case is not counted, that session has no case, and the word is "not rejected" under both readings.' % ' and '.join(only_dep))` | Then a second item is appended: in these sessions every case depends on the provisional limits. If such a case is not counted, the session has no case, and the word is "not rejected" under both readings. The last part is typed and not computed. |
| 600 | `        add('H3a', 'B4', w, per, notes + [note], open_, n=sum(len(x['b4']) for x in S.values()))` | Appends the row of H3a for step B4 with the word `w`. `n` is the count of B4 processes over all sessions. |
| 601 | `    else:` | The next line runs when the analysis has no entry for H3a. |
| 602 | `        add('H3a', 'B4', 'not tested', notes=['No process of step B4 is in the input.'])` | Appends the row of H3a with the word `not tested` and the note that no process of step B4 is in the input. |
| 603 | `    add('H3b', 'D2 (not run)', 'not tested', notes=['Part D was not run. No file has the physical addresses of the buffer pages.'])` | Appends the row of H3b for every input: step `D2 (not run)`, word `not tested`. The note is typed: Part D was not run, and no file has the physical addresses of the buffer pages. |

### `hypotheses`: the two rows of H4 (step B1 at 8 MiB) (lines 604 to 649)

| Line | Source | Explanation |
|---:|---|---|
| 604 | `    # ---- H4` | Comment: the rows of H4 follow. |
| 605 | `    any_h4 = False` | `any_h4`: becomes true when the analysis has an entry for H4. |
| 606 | `    for lab in ('low', 'high'):` | Loop over the two level labels, low and high. H4 gets one row per label. |
| 607 | `        h = hy.get('H4 (B1, 8 MiB, label %s)' % lab)` | `h`: the entry of the analysis for H4 from step B1 at 8 MiB and this label, or `None`. H4 predicts no resolved difference between `copy` and `asmcopy` inside one process. So a session gets the flag `fail` when the rule gives `resolved` for the label, with one sign over the sessions. It gets `not observed` when the rule gives `not observed`, and `hold` in every other case [Ref3]. |
| 608 | `        if not h:` | Tests whether the entry is missing. |
| 609 | `            continue` | Then this label gets no row here. |
| 610 | `        any_h4 = True` | Marks that H4 has an entry. |
| 611 | `        w, note = rule_word(h)` | `w` and `note`: the word as one of the five words, and the note for one session. |
| 612 | `        per, cpus_st = {}, set()` | `per`: the values per session. `cpus_st`: the set of CPUs that have a stable process. Both start empty. |
| 613 | `        for s, x in S.items():` | Loop over the sessions. |
| 614 | `            g = x['pairs']['B1'].get('8M')` | `g`: the description of the group of B1 at 8 MiB, or `None`. |
| 615 | `            r = x['res'].get('B1', {}).get('groups', {}).get('8M', {}).get('labels', {}).get(lab)` | `r`: the result of the rule for this label in that group, or `None`. The rule uses only the processes that are stable at this label. A CPU is resolved when it has at least 3 such processes, the absolute median of their `d` is larger than the largest absolute `e` of these processes, and all their `d` have one sign. The label is resolved when at least 2 CPUs have 3 such processes, every such CPU is resolved, and all have the same sign. With fewer than 2 such CPUs it is `not observed` [Ref2][Ref4]. |
| 616 | `            if not g or not r:` | Tests whether the description or the result is missing. |
| 617 | `                continue` | Such a session is skipped. |
| 618 | `            n = sum(v['n_' + lab] for v in g['per_cpu'].values())` | `n`: the count of processes that are stable at this label, summed over the CPUs of the description. |
| 619 | `            cpus_st \|= {c for c, v in g['per_cpu'].items() if v['n_low'] + v['n_high']}` | Adds to `cpus_st` every CPU with at least one stable process, low or high. |
| 620 | `            t = '%s. Stable %s processes: %s.' % (TR.get(h['per_session'].get(s), h['per_session'].get(s)), lab, ', '.join('CPU %s: %d' % (c, v['n_' + lab]) for c, v in g['per_cpu'].items()))` | `t`: the result text of the session: the sentence for the flag, then the count of stable processes of this label on every CPU. |
| 621 | `            alone = [(c, v) for c, v in r['per_cpu'].items() if v['decision'] != 'not observed']` | `alone`: the CPUs for which the rule gives a word other than `not observed`. Such a CPU has at least 3 stable processes of the label. |
| 622 | `            if alone and r['decision'] == 'not observed':` | Tests whether there is such a CPU while the result over the CPUs is `not observed`. |
| 623 | `                t += ' %s alone: %s. The rule needs 2 CPUs with 3 stable processes.' % (` | Then a sentence is added: the result of these CPUs alone, and that the rule needs 2 CPUs with 3 stable processes. |
| 624 | `                    ', '.join('CPU %s' % c for c, _ in alone), ', '.join(v['decision'] + ab.sign_txt(v['sign']) for _, v in alone))` | Continues line 623 with its values: the CPUs, and the word of each with its sign. |
| 625 | `            sp = ', '.join('CPU %s: %s over the %s (%s over all %d processes)' % (c, f2(v['aa_spread']), pl(v['n_processes'], 'stable %s process' % lab, 'stable %s processes' % lab),` | Starts `sp`, the text of the A/A spreads. For each CPU it gives the A/A spread over the stable processes of this label, with their count, and in brackets the A/A spread over all processes of the CPU. |
| 626 | `                                                                                 f2(g['per_cpu'][c]['aa_spread']), g['per_cpu'][c]['n'])` | Continues line 625: the spread over all processes comes from the description (line 228), with the count of all processes of the CPU. |
| 627 | `                           for c, v in r['per_cpu'].items() if v['aa_spread'] is not None)` | Ends `sp`: only a CPU with at least one stable process of the label gives an entry. |
| 628 | `            per[s] = dict(result=t, used='%d of %d' % (n, len(g['recs'])), spread=sp or 'no stable %s process' % lab)` | The entry of the session: `result` is `t`. `used` is `n` of the count of all described processes. `spread` is `sp`, or a text that says that no process is stable at this label. |
| 629 | `        notes = []` | `notes`: the notes of the row, empty at the start. |
| 630 | `        if lab == 'low':` | The notes of lines 631 to 646 are added to the row of the label low only. |
| 631 | `            notes.append(limits_note(sorted(cpus_st)))` | First the note of `limits_note` with the CPUs that have a stable process. |
| 632 | `            recs = [r for x in S.values() for r in x['pairs']['B1'].get('8M', {}).get('recs', [])]` | `recs`: the records of all processes of B1 at 8 MiB, over all sessions. |
| 633 | `            if recs:` | Tests whether there are records. |
| 634 | `                notes.append('Description without labels, no decision: d is below 0 in %d of %s.' % (sum(1 for r in recs if r['d'] < 0), pl(len(recs), 'process', 'processes')))` | Then a note is added: a description without labels and no decision, with the count of processes in which `d` is below 0. |
| 635 | `            nl = ['%s "%s%s" (%d of %s resolved)' % (s, x['b1_nolabel']['decision'], ab.sign_txt(x['b1_nolabel']['sign']), sum(1 for v in x['b1_nolabel']['per_cpu'].values() if v['decision'] == 'resolved'),` | Starts `nl`: one text per session with a value `b1_nolabel` (line 390): the session, the result of the rule without labels with its sign, and on how many CPUs it is resolved. |
| 636 | `                                                    pl(len(x['b1_nolabel']['per_cpu']), 'CPU', 'CPUs')) for s, x in S.items() if x['b1_nolabel']]` | Ends `nl`: the CPU count with its word, and the loop over the sessions. |
| 637 | `            if nl:` | Tests whether `nl` has an entry. |
| 638 | `                notes.append('Description, no decision: the rule for a size without level, applied to all processes at 8 MiB, gives ' + ', '.join(nl) + '.')` | Then a note is added: a description and no decision: the rule for a size without level, applied to all processes at 8 MiB, gives the texts of `nl`. |
| 639 | `            others = {}` | `others`: the results of the other buffer sizes, empty at the start. |
| 640 | `            for s, x in S.items():` | Loop over the sessions. |
| 641 | `                for k, gr in x['res'].get('B1', {}).get('groups', {}).items():` | Loop over the groups of B1 in the analysis result of the session. |
| 642 | `                    if k != '8M' and 'none' in gr['labels']:` | Tests whether the group is not the group `8M` and has a result under the label `none`. |
| 643 | `                        others.setdefault(k, {})[s] = gr['labels']['none']['decision'] + ab.sign_txt(gr['labels']['none']['sign'])` | Then the decision with its sign is stored under the group and the session. |
| 644 | `            if others:` | Tests whether there is such a result. |
| 645 | `                notes.append('Other sizes, by the rule: ' + '. '.join('%s MiB: %s' % (k.rstrip('M'), ', '.join('%s %s' % (s, v) for s, v in d.items())) for k, d in sorted(others.items(), key=lambda kv: ab.parse_size(kv[0])))` | Then a note is added: the result of the rule for each other size, in the order of the sizes, with the word of each session. |
| 646 | `                             + '. H4 predicts 8 MiB only.')` | Ends the note with a typed sentence: H4 predicts 8 MiB only. |
| 647 | `        add('H4, %s intervals' % lab, 'B1 at 8 MiB', w, per, notes + [note], n=sum(int(v['used'].split()[0]) for v in per.values()))` | Appends the row. Its name is `H4, low intervals` or `H4, high intervals`. Its step text is `B1 at 8 MiB`. `n` is the sum over the sessions of the first number of `used`. |
| 648 | `    if not any_h4:` | Tests whether the analysis had no entry for H4 at all. |
| 649 | `        add('H4', 'B1 at 8 MiB', 'not tested', notes=['No process of step B1 at 8 MiB is in the input.'])` | Then one row `H4` is appended with the word `not tested` and the note that no process of step B1 at 8 MiB is in the input. |

### `hypotheses`: the rows of H5 and H6, and the two checks at the end (lines 650 to 691)

| Line | Source | Explanation |
|---:|---|---|
| 650 | `    # ---- H5, H6` | Comment: the rows of H5 and H6 follow. |
| 651 | `    for name, key, step, grp in (('H5', 'H5 (B2, asmcopy_c, label low)', 'B2', 'asmcopy_c'), ('H6', 'H6 (B3)', 'B3', None)):` | Loop over two hypotheses. Each has a name, the key of its entry in the analysis, a step and a group. H5 uses step B2 and only the group `asmcopy_c`. H6 uses step B3 and all its groups, one per build. |
| 652 | `        h = hy.get(key)` | `h`: the entry of the analysis, or `None`. For H5 a session gets `hold` when the rule gives `resolved` for `asmcopy_c` minus `asmcopy` at the label low, with the sign of B1. For H6 it gets `hold` when the change of the median `d` against B1 is resolved on a CPU for one of the three builds. In both cases the flag is `not observed` when B1 at 8 MiB of the session has no resolved difference, and `fail` when the prediction did not hold [Ref3]. |
| 653 | `        if not h:` | Tests whether the entry is missing. |
| 654 | `            add(name, step, 'not tested', notes=['No process of step %s is in the input.' % step])` | Then the row is appended with the word `not tested` and the note that no process of the step is in the input. |
| 655 | `            continue` | The loop goes on with the next hypothesis. |
| 656 | `        w, note = rule_word(h)` | `w` and `note`: the word as one of the five words, and the note for one session. |
| 657 | `        per, cpus_st, no_b1 = {}, set(), []` | Three empty values: `per`, `cpus_st` (the CPUs with a stable process) and `no_b1` (the sessions without a resolved B1). |
| 658 | `        for s, x in S.items():` | Loop over the sessions. |
| 659 | `            gs = [(k, g) for k, g in x['pairs'][step].items() if grp in (None, k)]` | `gs`: the described groups of the step that belong to the hypothesis: the group `asmcopy_c` for H5, every group for H6. |
| 660 | `            if not gs:` | Tests whether the session has no such group. |
| 661 | `                continue` | Such a session is skipped. |
| 662 | `            n = sum(len(g['recs']) for _, g in gs)` | `n`: the count of described processes in these groups. |
| 663 | `            nst = sum(1 for _, g in gs for r in g['recs'] if r['stable'])` | `nst`: how many of them have a stable label. |
| 664 | `            cpus_st \|= {c for _, g in gs for c, v in g['per_cpu'].items() if v['n_low'] + v['n_high']}` | Adds to `cpus_st` every CPU with at least one stable process, low or high. |
| 665 | `            sps = {}` | `sps`: per CPU a list of A/A spreads of the rule, empty at the start. |
| 666 | `            for k, _ in gs:` | Loop over the groups. |
| 667 | `                for lab, r in x['res'].get(step, {}).get('groups', {}).get(k, {}).get('labels', {}).items():` | Loop over the labels of the group in the analysis result, each with its result `r`. |
| 668 | `                    for c, v in r['per_cpu'].items():` | Loop over the CPUs of that result. |
| 669 | `                        if v['aa_spread'] is not None:` | Tests whether the rule has an A/A spread for the CPU. It has one when at least one process of the CPU is stable at the label. |
| 670 | `                            sps.setdefault(c, []).append(v['aa_spread'])` | Then the spread is appended to the list of the CPU. |
| 671 | `            b1l = x['res'].get('B1', {}).get('groups', {}).get('8M', {}).get('labels', {})` | `b1l`: the results of the rule for B1 at 8 MiB of this session, per label. |
| 672 | `            if not any(v['decision'] == 'resolved' for v in b1l.values()):` | Tests whether no label of B1 is resolved. |
| 673 | `                no_b1.append(s)` | Then the session is added to `no_b1`. |
| 674 | `            per[s] = dict(result='%s. %d of %s %s stable at one level.' % (TR.get(h['per_session'].get(s), h['per_session'].get(s)), nst, pl(n, 'process', 'processes'), 'is' if nst == 1 else 'are'),` | Starts the entry of the session. `result`: the sentence for the flag, then how many of the processes are stable at one level. |
| 675 | `                          used='%d of %d' % (nst, n),` | Continues line 674. `used`: `nst` of `n`. |
| 676 | `                          spread=', '.join('CPU %s: %s over the stable processes' % (c, rng(min(v), max(v))) for c, v in sorted(sps.items())) or 'no stable process')` | Ends the entry. `spread`: for each CPU the range of its A/A spreads in `sps`, with the words "over the stable processes". Without any spread it is the text `no stable process`. |
| 677 | `        notes = [limits_note(sorted(cpus_st))]` | `notes`: starts with the note of `limits_note` for the CPUs that have a stable process. |
| 678 | `        if no_b1:` | Tests whether a session has no resolved B1. |
| 679 | `            notes.append('Step B1 has no resolved difference at 8 MiB by the rule in %s %s. The plan runs step %s only after a resolved difference in B1. The step was run so that the data exist if the limits are revised.' % ('session' if len(no_b1) == 1 else 'sessions', ' and '.join(no_b1), step))` | Then a note is added: step B1 has no resolved difference at 8 MiB by the rule in these sessions. The plan runs this step only after a resolved difference in B1. The last sentence is typed: the step was run to have the data in case the limits are revised. |
| 680 | `        if grp:` | Tests whether the hypothesis has one group (H5). |
| 681 | `            recs = [r for x in S.values() for r in x['pairs'][step].get(grp, {}).get('recs', [])]` | `recs`: the records of all processes of that group, over all sessions. |
| 682 | `            if recs:` | Tests whether there are records. |
| 683 | `                notes.append('Description without labels, no decision: d is below 0 in %d of %s.' % (sum(1 for r in recs if r['d'] < 0), pl(len(recs), 'process', 'processes')))` | Then a note is added: a description without labels and no decision, with the count of processes in which `d` is below 0. |
| 684 | `        add(name, step, w, per, notes + [note], n=sum(int(v['used'].split()[0]) for v in per.values()))` | Appends the row with the word `w`. `n` is the sum over the sessions of the stable processes. |
| 685 | `    for r in rows:` | Loop over all rows of the table. |
| 686 | `        assert r['word'] in WORDS5, r` | Stops the script with an error when the word of a row is not one of the five words of `WORDS5`. |
| 687 | `        if one:` | Tests whether the input holds fewer than 2 sessions (line 492). |
| 688 | `            assert r['word'] != 'rejected'` | Then the script stops with an error when a row has the word `rejected`. By rule 11 that word needs two sessions. |
| 689 | `    return rows` | Returns the rows. |

### Chart helpers `nice_ticks` and `axis_floor` (lines 692 to 709)

| Line | Source | Explanation |
|---:|---|---|
| 692 | `# ---------------------------------------------------------------- charts` | Comment: a divider. The functions that draw the charts follow. |
| 694 | `def nice_ticks(lo, hi, n=7):` | Starts the function `nice_ticks`. It chooses the values at which an axis from `lo` to `hi` gets a tick. `n` is the highest count of steps, 7 unless given. |
| 695 | `    span = hi - lo` | `span`: the length of the axis. |
| 696 | `    step = next((s for s in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50) if span / s <= n), 100)` | `step`: the distance between two ticks. It is the first of the values 0.1, 0.2, 0.5, 1, 2, 5, 10, 20 and 50 for which the axis holds at most `n` steps. If none fits, it is 100. |
| 697 | `    t, v = [], (int(lo / step) - 1) * step` | `t`: the list of ticks, empty at the start. `v`: the first candidate, a multiple of `step` that lies below `lo`. |
| 698 | `    while v <= hi + 1e-9:` | Loop while the candidate is not above `hi`. The small value `1e-9` keeps a rounding error of the sum from losing the last tick. |
| 699 | `        if v >= lo - 1e-9:` | Tests whether the candidate is not below `lo`. |
| 700 | `            t.append(round(v, 6))` | Then it is kept, rounded to 6 decimals. |
| 701 | `        v += step` | Goes to the next candidate. |
| 702 | `    return t` | Returns the ticks. |
| 705 | `def axis_floor(v):` | Starts the function `axis_floor`. |
| 706 | `    """The start of a rate axis: the next lower multiple of 0.5 GB/s, so that the first tick is at the left edge."""` | Docstring: the start of a rate axis is the next lower multiple of 0.5 GB/s. The purpose that the docstring gives: the first tick stands at the left edge. This holds only when that start is also a multiple of the tick step that `nice_ticks` chooses. |
| 707 | `    return math.floor(v * 2) / 2` | Returns `v` rounded down to a multiple of 0.5: the value is doubled, rounded down to a whole number, and halved. |

### Function `strip`: a chart with one row of markers per name, and `short_tag` (lines 710 to 757)

| Line | Source | Explanation |
|---:|---|---|
| 710 | `def strip(rows, xmin, xmax, xlabel, aria, L=250, R=250, groups=None, right_head=None, zero=False):` | Starts the function `strip`. It draws a chart as an SVG drawing: one row per name and one marker per value, on one horizontal axis from `xmin` to `xmax`. `aria` is the label for screen readers. `L` and `R` are the left and the right margin, 250 units each unless given. `groups` holds the numbers of the rows that end a group. `right_head` is the heading of the right column. |
| 711 | `    """rows: [(name, [(value, title, kind)], right_label)]. kind 0: blue dot. kind 1: orange diamond.` | Docstring: `rows` is a list of entries with a name, a list of points and a label for the right side. A point holds a value, a tooltip text and a kind. Kind 0 is a blue dot. Kind 1 is an orange diamond. |
| 712 | `    The band between the two provisional limits is shaded if it lies inside the axis. zero: a dashed line at 0."""` | Docstring: the band between the two provisional limits is shaded if it lies inside the axis. With `zero` a dashed line is drawn at 0. The code draws the band only when `zero` is not set (line 718). |
| 713 | `    W, rh, top = 900, 24, 34` | Three sizes in units of the drawing. `W`: the width, 900. `rh`: the height of one row, 24. `top`: the space above the first row, 34. |
| 714 | `    H = top + len(rows) * rh + 46` | `H`: the height of the drawing: the space above, all rows, and 46 units below for the axis. |
| 715 | `    PW = W - L - R` | `PW`: the width of the plot area between the two margins. |
| 716 | `    X = lambda v: L + (min(max(v, xmin), xmax) - xmin) / (xmax - xmin) * PW` | `X`: a small function that turns a value into a horizontal position. A value outside the axis is drawn at the nearest edge. |
| 717 | `    o = pa.svg_open(W, H, aria)` | `o`: the list of the text lines of the drawing. `pa.svg_open` gives the opening line with the size and the label for screen readers. |
| 718 | `    band = xmin < LOW and xmax > HIGH and not zero` | `band`: true when the axis starts below `LOW`, ends above `HIGH`, and `zero` is not set. |
| 719 | `    if band:` | The next three lines run when `band` is true. |
| 720 | `        o.append(f'<rect x="{fx(X(LOW), 1)}" y="{top-6}" width="{fx(X(HIGH)-X(LOW), 1)}" height="{len(rows)*rh+6}" fill="{BAND}"/>')` | Adds a shaded rectangle between the two limits, over all rows. |
| 721 | `        o.append(f'<text x="{fx(X(LOW)-4, 1)}" y="{top-12}" text-anchor="end" class="ax">low: below {LOW:g}</text>')` | Adds a label above the plot, at the left of the low limit. It names the low level and its limit of 69 GB/s. |
| 722 | `        o.append(f'<text x="{fx(X(HIGH)+4, 1)}" y="{top-12}" class="ax">high: above {HIGH:g}</text>')` | Adds a label at the right of the high limit. It names the high level and its limit of 70.5 GB/s. |
| 723 | `    for t in nice_ticks(xmin, xmax):` | Loop over the tick values of `nice_ticks`. |
| 724 | `        o.append(f'<line x1="{fx(X(t), 1)}" y1="{top-6}" x2="{fx(X(t), 1)}" y2="{H-46}" stroke="{GRID}"/>')` | Adds a thin vertical grid line at the tick. |
| 725 | `        o.append(f'<text x="{fx(X(t), 1)}" y="{H-30}" text-anchor="middle" class="ax">{t:g}</text>')` | Adds the number of the tick below the plot. |
| 726 | `    if band:` | Tests `band` again. |
| 727 | `        for v in (LOW, HIGH):` | Loop over the two limits. |
| 728 | `            o.append(f'<line x1="{fx(X(v), 1)}" y1="{top-6}" x2="{fx(X(v), 1)}" y2="{H-46}" stroke="{MUTED}" stroke-dasharray="4 3"/>')` | Adds a dashed vertical line at the limit. |
| 729 | `    if zero:` | Tests `zero`. |
| 730 | `        o.append(f'<line x1="{fx(X(0), 1)}" y1="{top-6}" x2="{fx(X(0), 1)}" y2="{H-46}" stroke="{MUTED}" stroke-dasharray="3 3"/>')` | Then a dashed vertical line is added at the value 0. |
| 731 | `    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">{e(xlabel)}</text>')` | Adds the title of the axis, centered below the plot. `e` replaces the characters that have a meaning in HTML. |
| 732 | `    if right_head:` | Tests whether a heading for the right column is given. |
| 733 | `        o.append(f'<text x="{L+PW+10}" y="{top-12}" class="ax">{e(right_head)}</text>')` | Then the heading is added above the right column. |
| 734 | `    for i, (name, pts, right) in enumerate(rows):` | Loop over the rows, with the index `i` from 0. |
| 735 | `        y = top + i * rh + rh / 2` | `y`: the vertical middle of the row. |
| 736 | `        o.append(f'<text x="{L-10}" y="{fx(y+4, 1)}" text-anchor="end" class="lab">{e(name)}</text>')` | Adds the name of the row at the left of the plot, with its end at the plot. |
| 737 | `        heavy = groups and i + 1 in groups` | `heavy`: true when `groups` holds the number of this row, counted from 1. Such a row is the last of a group. |
| 738 | `        o.append(f'<line x1="{0 if heavy else L}" y1="{fx(y+rh/2, 1)}" x2="{W if heavy else L+PW}" y2="{fx(y+rh/2, 1)}" stroke="{MUTED if heavy else GRID}"/>')` | Adds the line below the row. Below a heavy row it is dark grey and spans the full width. Below any other row it is light grey and spans the plot area. |
| 739 | `        for kind_now in (1, 0):                                   # diamonds first, so that a dot is never hidden by a diamond` | Loop over the two kinds, first the diamonds and then the dots. Comment: so a dot is never hidden by a diamond. |
| 740 | `            for j, (v, title, kind) in enumerate(pts):` | Loop over the points of the row, with the index `j`. |
| 741 | `                if kind != kind_now:` | Tests whether the point is of the other kind. |
| 742 | `                    continue` | Then it is left for the other pass. |
| 743 | `                yy = y + ((j * 7) % 5 - 2) * 2.2` | `yy`: the vertical place of the marker. The index of the point chooses one of five offsets from the middle of the row: -4.4, -2.2, 0, 2.2 or 4.4 units. So markers with equal values do not cover each other. |
| 744 | `                if kind:` | Tests whether the point is a diamond. |
| 745 | `                    o.append(f'<path d="M{fx(X(v), 1)},{fx(yy-5, 1)} l5,5 l-5,5 l-5,-5 Z" fill="{C1c}" stroke="#fff" stroke-width="1"><title>{e(title)}</title></path>')` | Then an orange diamond of 10 units is drawn at the value, with a white edge and the tooltip text. |
| 746 | `                else:` | The next line runs for a dot. |
| 747 | `                    o.append(f'<circle cx="{fx(X(v), 1)}" cy="{fx(yy, 1)}" r="3.5" fill="{C0}" fill-opacity="0.6" stroke="#fff" stroke-width="0.8"><title>{e(title)}</title></circle>')` | Draws a blue dot with a radius of 3.5 units, 60 % opacity, a white edge and the tooltip text. |
| 748 | `        o.append(f'<text x="{L+PW+10}" y="{fx(y+4, 1)}" class="val">{e(right)}</text>')` | Adds the label of the row at the right of the plot. |
| 749 | `    o.append('</svg>')` | Adds the line that closes the drawing. |
| 750 | `    return '\n'.join(o)` | Returns the drawing as one text, with a line break between its lines. |
| 753 | `def short_tag(tag):` | Starts the function `short_tag`. No line of this file calls it. |
| 754 | `    m = re.search(r'cpu(\d+)-p(\d+)', tag)` | `m`: the result of a search in the tag for the text `cpu`, digits, `-p` and digits. Group 1 holds the CPU number. Group 2 holds the process number. |
| 755 | `    return 'CPU %s, process %s' % (m.group(1), m.group(2)) if m else tag` | Returns the text `CPU`, the CPU number, `process` and the process number. A tag without that form is returned unchanged. |

### Functions `dumbbell` and `legend_pairs`: the chart of d and e per process (lines 758 to 811)

| Line | Source | Explanation |
|---:|---|---|
| 758 | `def dumbbell(items, aria):` | Starts the function `dumbbell`. It draws the chart of the values `d` and `e` of every process of one group. |
| 759 | `    """items: [(session name, desc)]. One row per process: d (blue dot) and e (orange diamond), joined by a line.` | Docstring: `items` is a list of pairs of session name and description. The chart has one row per process: `d` as a blue dot and `e` as an orange diamond, joined by a line. |
| 760 | `    The value of d is printed in blue in a fixed column left of the plot, the value of e in orange in a fixed column right of it.` | Docstring: the value of `d` is printed in blue in a fixed column at the left of the plot. The value of `e` is printed in orange in a fixed column at the right of it. |
| 761 | `    One block per CPU and session: the band from minus to plus the A/A spread of that block, and the median d as a faint line."""` | Docstring: the chart has one block per CPU and session. A block shows the band from minus to plus the A/A spread of that block, and the median `d` as a faint line. |
| 762 | `    W, L, R, rh, gap, top = 900, 196, 256, 16, 8, 26` | Six sizes in units of the drawing. `W`: the width, 900. `L` and `R`: the left and the right margin, 196 and 256. `rh`: the height of one row, 16. `gap`: the space between two blocks, 8. `top`: the space above the first block, 26. |
| 763 | `    blocks = [(s, c, [r for r in d['recs'] if r['cpu'] == c], d['per_cpu'][c]) for c in sorted({c for _, d in items for c in d['per_cpu']})` | Starts `blocks`: one entry per CPU and session. An entry holds the session, the CPU, the process records of that CPU and the values of the CPU. The CPUs stand in rising order. |
| 764 | `              for s, d in items if c in d['per_cpu']]` | Ends `blocks`: inside one CPU the sessions keep the order of `items`. A session whose description lacks the CPU gives no block. |
| 765 | `    many = len(items) > 1` | `many`: true when more than one session is drawn. Inside `dumbbell` the name `many` means this value and not the function `many` of line 923. |
| 766 | `    xmin, xmax = axis_of([d for _, d in items])` | `xmin` and `xmax`: the two ends of the axis, from `axis_of` (lines 1202 to 1204). The axis covers every `d`, every `e`, every A/A spread with both signs, and 0. |
| 767 | `    nrows = sum(len(b[2]) for b in blocks)` | `nrows`: the count of all process rows. |
| 768 | `    H = top + nrows * rh + len(blocks) * gap + 44` | `H`: the height of the drawing: the space above, the rows, one gap per block, and 44 units below for the axis. |
| 769 | `    PW = W - L - R` | `PW`: the width of the plot area. |
| 770 | `    X = lambda v: L + 8 + (v - xmin) / (xmax - xmin) * (PW - 16)` | `X`: a small function that turns a value in GB/s into a horizontal position. It keeps 8 units free at each side of the plot area. |
| 771 | `    o = pa.svg_open(W, H, aria)` | `o`: the list of the text lines of the drawing, with the opening line. |
| 772 | `    ybot = H - 44` | `ybot`: the vertical position of the lower end of the plot. |
| 773 | `    for t in nice_ticks(xmin, xmax, 9):` | Loop over the tick values of `nice_ticks`, with at most 9 steps. |
| 774 | `        o.append(f'<line x1="{fx(X(t), 1)}" y1="{top}" x2="{fx(X(t), 1)}" y2="{ybot}" stroke="{GRID}"/>')` | Adds a vertical grid line at the tick. |
| 775 | `        o.append(f'<text x="{fx(X(t), 1)}" y="{ybot+14}" text-anchor="middle" class="ax">{t:g}</text>')` | Adds the number of the tick below the plot. |
| 776 | `    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">difference of the rates of two neighbouring intervals, GB/s (one value per process: the median of its pairs)</text>')` | Adds the title of the axis: the difference of the rates of two neighbouring intervals in GB/s, with one value per process, the median of its pairs. |
| 777 | `    o.append(f'<text x="{L-6}" y="{top-10}" text-anchor="end" class="lab" style="fill:{TD};font-weight:600">d, GB/s</text>')` | Adds the heading of the left number column for `d`, in dark blue and bold. |
| 778 | `    o.append(f'<text x="{L+PW+6}" y="{top-10}" class="lab" style="fill:{TE};font-weight:600">e, GB/s</text>')` | Adds the heading of the right number column for `e`, in dark orange and bold. |
| 779 | `    y = top` | `y`: the vertical position of the next block, at first the top. |
| 780 | `    for bi, (s, c, g, pc) in enumerate(blocks):` | Loop over the blocks, with the index `bi`. |
| 781 | `        y0, y1 = y + 2, y + len(g) * rh + 2` | `y0` and `y1`: the upper and the lower edge of the block. |
| 782 | `        o.append(f'<rect x="{fx(X(-pc["aa_spread"]), 1)}" y="{y0}" width="{fx(max(X(pc["aa_spread"])-X(-pc["aa_spread"]), 1), 1)}" height="{y1-y0}" fill="#f6d9c9"><title>A/A spread of CPU {c}: plus and minus {fx(pc["aa_spread"])} GB/s</title></rect>')` | Adds the shaded band of the block: a rectangle from minus the A/A spread of the CPU to plus that spread, at least 1 unit wide. Its tooltip gives the CPU and the spread in GB/s. |
| 783 | `        o.append(f'<line x1="{fx(X(0), 1)}" y1="{y0}" x2="{fx(X(0), 1)}" y2="{y1}" stroke="{MUTED}" stroke-dasharray="3 3"/>')` | Adds a dashed vertical line at the value 0, over the height of the block. |
| 784 | `        ym = (y0 + y1) / 2` | `ym`: the vertical middle of the block. |
| 785 | `        o.append(f'<line x1="{fx(X(pc["median_d"]), 1)}" y1="{y0}" x2="{fx(X(pc["median_d"]), 1)}" y2="{y1}" stroke="{C0}" stroke-width="1.5" stroke-opacity="0.4"/>')` | Adds a faint blue vertical line at the median `d` of the CPU. |
| 786 | `        name = (f'{s}, ' if many else '') + f'CPU {c}'` | `name`: the text `CPU` and the number. With several sessions the session name stands in front. |
| 787 | `        o.append(f'<text x="{L+PW+52}" y="{fx(ym-3, 1)}" class="val">{e(name)}: median d {fs(pc["median_d"])} GB/s</text>')` | Adds a text at the right of the plot: `name` and the median `d` of the CPU with its sign, in GB/s. |
| 788 | `        o.append(f'<text x="{L+PW+52}" y="{fx(ym+11, 1)}" class="val">A/A spread {fx(pc["aa_spread"])} GB/s (shaded)</text>')` | Adds a second text below it: the A/A spread of the CPU in GB/s, and that it is the shaded band. |
| 789 | `        for i, r in enumerate(g):` | Loop over the processes of the block, with the index `i`. |
| 790 | `            yy = y + 2 + i * rh + rh / 2` | `yy`: the vertical middle of the row of the process. |
| 791 | `            m = re.search(r'p(\d+)$', r['tag'])` | `m`: the result of a search for the letter `p` and digits at the end of the tag. Group 1 holds the process number. |
| 792 | `            o.append(f'<text x="{L-50}" y="{fx(yy+4, 1)}" text-anchor="end" class="ax">{e(name)}, process {m.group(1) if m else e(r["tag"])}</text>')` | Adds the label of the row at the left: `name` and the process number. When the tag has another form, the whole tag is printed. |
| 793 | `            xd, xe = X(r['d']), X(r['e'])` | `xd` and `xe`: the horizontal positions of `d` and of `e`. |
| 794 | `            o.append(f'<line x1="{fx(xd, 1)}" y1="{fx(yy, 1)}" x2="{fx(xe, 1)}" y2="{fx(yy, 1)}" stroke="{MUTED}" stroke-width="1"/>')` | Adds a grey line that joins the two positions. |
| 795 | `            o.append(pa.marker(xe, yy, 'diamond', C1c, f'{r["tag"]}: e {fs(r["e"], 3)} GB/s', r=3))` | Adds the orange diamond for `e`, from `pa.marker`. Its tooltip gives the tag and `e` with 3 decimals. |
| 796 | `            o.append(pa.marker(xd, yy, 'dot', C0, f'{r["tag"]}: d {fs(r["d"], 3)} GB/s', r=4))        # the dot is drawn last, above the diamond` | Adds the blue dot for `d`. Its tooltip gives the tag and `d` with 3 decimals. Comment: the dot is drawn last, so it lies above the diamond. |
| 797 | `            o.append(f'<text x="{L-6}" y="{fx(yy+4, 1)}" text-anchor="end" class="val" style="fill:{TD}">{fs(r["d"])}</text>')` | Adds the number of `d` with its sign and 2 decimals, in dark blue, in the column at the left of the plot. |
| 798 | `            o.append(f'<text x="{L+PW+6}" y="{fx(yy+4, 1)}" class="val" style="fill:{TE}">{fs(r["e"])}</text>')` | Adds the number of `e` with its sign and 2 decimals, in dark orange, in the column at the right of the plot. |
| 799 | `        y = y1 + gap - 2` | Moves `y` to the top of the next block. |
| 800 | `        last_of_cpu = bi + 1 == len(blocks) or blocks[bi + 1][1] != c` | `last_of_cpu`: true when this is the last block, or the next block belongs to another CPU. |
| 801 | `        o.append(f'<line x1="0" y1="{fx(y-gap/2+1, 1)}" x2="{W}" y2="{fx(y-gap/2+1, 1)}" stroke="{MUTED if last_of_cpu and many else GRID}"/>')` | Adds a horizontal line below the block over the full width. It is dark grey below the last block of a CPU when several sessions are drawn. In every other case it is light grey. |
| 802 | `    o.append('</svg>')` | Adds the line that closes the drawing. |
| 803 | `    return '\n'.join(o)` | Returns the drawing as one text. |
| 806 | `def legend_pairs(dname, ename):` | Starts the function `legend_pairs`. It builds the legend that stands above a chart of `dumbbell`. |
| 807 | `    return (f'<p><span class="lg"><i style="background:{C0}"></i>d = {e(dname)}</span>'` | The first entry: a blue circle and the text `d =` with the name of the compared difference. |
| 808 | `            f'<span class="lg"><i style="background:{C1c};border-radius:0;transform:rotate(45deg)"></i>e = {e(ename)} (two copies of one loop)</span>'` | The second entry: an orange diamond and the text `e =` with the name of the A/A difference, and the remark that these are two copies of one loop. |
| 809 | `            f'<span class="lg"><i style="background:#f6d9c9;border-radius:0"></i>from minus to plus the A/A spread</span></p>')` | The third entry: a shaded square for the band from minus to plus the A/A spread. The line also closes the paragraph. |

### Function `seq_chart`: the rate of every interval of a process (lines 812 to 866)

| Line | Source | Explanation |
|---:|---|---|
| 812 | `def seq_chart(procs, ymin, ymax, aria):` | Starts the function `seq_chart`. It draws one panel per process of step B4. `ymin` and `ymax` are the two ends of the rate axis, the same in every panel. |
| 813 | `    """One panel per process: rate against interval number. Red lines: a vmstat counter rose before that interval.` | Docstring: one panel per process shows the rate against the interval number. A red line means that a counter of `/proc/vmstat` rose before that interval. The code draws the lines of the second counter in purple (line 839). |
| 814 | `    -> (svg text, [(process tag, interval) of every value label that found no free place])."""` | Docstring: the function returns the text of the drawing and a list of the value labels that found no free place. By the docstring an entry of the list holds the process tag and the interval. The code also puts the rate into the entry (line 852). |
| 815 | `    W, L, R, ph, gap, top = 900, 60, 190, 84, 38, 26` | Six sizes in units of the drawing. `W`: the width, 900. `L` and `R`: the left and the right margin, 60 and 190. `ph`: the height of one panel, 84. `gap`: the space between two panels, 38. `top`: the space above the first panel, 26. |
| 816 | `    H = top + len(procs) * (ph + gap)` | `H`: the height of the drawing. |
| 817 | `    nmax = max(max(len(p['rates']) for p in procs), 2)` | `nmax`: the highest count of intervals of a process, and at least 2. |
| 818 | `    X = lambda i: L + i / (nmax - 1) * (W - L - R)` | `X`: a small function that turns an interval number into a horizontal position. Interval 0 lies at the left edge of the panel. |
| 819 | `    o = pa.svg_open(W, H, aria)` | `o`: the list of the text lines of the drawing, with the opening line. |
| 820 | `    left_out = []` | `left_out`: the value labels without a free place, empty at the start. |
| 821 | `    for pi, p in enumerate(procs):` | Loop over the processes, with the index `pi`. |
| 822 | `        y0 = top + pi * (ph + gap)` | `y0`: the upper edge of the panel of this process. |
| 823 | `        Y = lambda v: y0 + ph - (v - ymin) / (ymax - ymin) * ph` | `Y`: a small function that turns a rate into a vertical position. `ymin` lies at the lower edge of the panel and `ymax` at the upper edge. |
| 824 | `        o.append(f'<rect x="{L}" y="{y0}" width="{W-L-R}" height="{ph}" fill="none" stroke="{GRID}"/>')` | Adds the frame of the panel. |
| 825 | `        o.append(f'<rect x="{L}" y="{fx(Y(HIGH), 1)}" width="{W-L-R}" height="{fx(Y(LOW)-Y(HIGH), 1)}" fill="{BAND}"/>')` | Adds the shaded band between the two level limits. |
| 826 | `        asked = '4 KiB pages asked (--no-thp)' if p['no_thp'] else '2 MiB pages asked'` | `asked`: a text that says which page size the process asked for: 4 KiB pages for a process with `--no-thp`, 2 MiB pages for the others. |
| 827 | `        cov = 'no page reading' if p['kb_total'] is None else (` | Starts `cov`, a text on the huge-page coverage. It says that no page state was read when the process has no `P` row with values. |
| 828 | `            f"kB_huge {p['kb_huge_min']} of {p['kb_total']} kB before every interval" if p['kb_huge_min'] == p['kb_huge_max']` | Continues line 827: when the lowest and the highest `kB_huge` of the process are equal, the text gives that value and `kB_total`, with the words "before every interval". |
| 829 | `            else f"kB_huge {p['kb_huge_min']} to {p['kb_huge_max']} of {p['kb_total']} kB")` | Ends `cov`: in the other case the text gives the lowest and the highest `kB_huge` and `kB_total`. |
| 830 | `        o.append(f'<text x="{L}" y="{y0-7}" class="lab">CPU {p["cpu"]}, process {e(p["tag"])}, started {e(p["utc"])} UTC. {asked}. {cov}.</text>')` | Adds the title of the panel: the CPU, the tag, the UTC time of the launch, `asked` and `cov`. |
| 831 | `        for v in (HIGH, LOW):` | Loop over the two level limits. |
| 832 | `            o.append(f'<line x1="{L}" y1="{fx(Y(v), 1)}" x2="{W-R}" y2="{fx(Y(v), 1)}" stroke="{MUTED}" stroke-dasharray="4 3"/>')` | Adds a dashed horizontal line at the limit. |
| 833 | `        boxes = []` | `boxes`: the areas of the panel that hold text already, empty at the start. |
| 834 | `        for v in (ymin, LOW, HIGH, ymax):` | Loop over four values of the rate axis: `ymin`, the two limits and `ymax`. |
| 835 | `            o.append(f'<text x="{L-6}" y="{fx(Y(v)+4, 1)}" text-anchor="end" class="ax">{fx(v, 1)}</text>')` | Adds the number of the value with 1 decimal at the left of the panel. |
| 836 | `            boxes.append((L - 36, Y(v) - 6, L - 6, Y(v) + 6))` | Stores the area of that number in `boxes`. |
| 837 | `        for i in range(0, nmax, 25):` | Loop over the interval numbers 0, 25, 50 and so on. |
| 838 | `            o.append(f'<text x="{fx(X(i), 1)}" y="{y0+ph+13}" text-anchor="middle" class="ax">{i}</text>')` | Adds the interval number below the panel. |
| 839 | `        for k, col in (('thp_collapse_alloc', RED), ('pgmigrate_success', '#7a3fb5')):` | Loop over the two counters with their colors: `thp_collapse_alloc` in red and `pgmigrate_success` in purple. |
| 840 | `            for i in p['events'][k]:` | Loop over the intervals before which the counter rose (lines 262 to 267). |
| 841 | `                o.append(f'<line x1="{fx(X(i), 1)}" y1="{y0}" x2="{fx(X(i), 1)}" y2="{y0+ph}" stroke="{col}" stroke-width="1.5"><title>{k} rose before interval {i}</title></line>')` | Adds a vertical line over the height of the panel at that interval. Its tooltip names the counter and the interval. |
| 842 | `        r = p['rates']` | `r`: the rates of the process. |
| 843 | `        o.append(f'<polyline points="{" ".join(f"{fx(X(i), 1)},{fx(Y(v), 1)}" for i, v in enumerate(r))}" fill="none" stroke="{C0}" stroke-width="1.5"/>')` | Adds the blue line through the rates of all intervals. |
| 844 | `        segs = [(X(i), Y(r[i]), X(i + 1), Y(r[i + 1])) for i in range(len(r) - 1)]` | `segs`: the pieces of that line, each as its two end points. |
| 845 | `        hl = [Y(HIGH), Y(LOW)]` | `hl`: the vertical positions of the two dashed lines. |
| 846 | `        want = list(dict.fromkeys([r.index(min(r)), r.index(max(r)), 0, len(r) - 1]))` | `want`: the intervals that get a value label: the one with the lowest rate, the one with the highest rate, the first and the last. An interval that is named twice stands once. |
| 847 | `        for i in want:` | Loop over these intervals. |
| 848 | `            txt = fx(r[i], 2)` | `txt`: the rate with 2 decimals. |
| 849 | `            o.append(f'<circle cx="{fx(X(i), 1)}" cy="{fx(Y(r[i]), 1)}" r="3" fill="{C0}" stroke="#fff" stroke-width="1"><title>interval {i}: {txt} GB/s</title></circle>')` | Adds a small blue dot at the point. Its tooltip gives the interval and the rate in GB/s. |
| 850 | `            got = pa.place_label(X(i), Y(r[i]), 6.4 * len(txt) + 2, i == 0, i == len(r) - 1, r[i] == min(r), y0, y0 + ph, boxes, segs, hl, (L, W - R))` | `got`: the place of the label, from `pa.place_label`. The function gets the point, an estimate of the text width (6.4 units per character plus 2), three flags (first interval, last interval, lowest rate), the edges of the panel, the areas that already hold text, the line pieces and the dashed lines. It returns `None` when it finds no free place. |
| 851 | `            if not got:` | Tests whether no place was found. |
| 852 | `                left_out.append((p['tag'], i, r[i]))` | Then the tag, the interval and the rate are stored in `left_out`. |
| 853 | `                continue` | No label is drawn for this interval. |
| 854 | `            anchor, tx, base = got` | Takes the three values of the place: the alignment, the horizontal position and the base line of the text. |
| 855 | `            o.append(f'<text x="{fx(tx, 1)}" y="{fx(base, 1)}" text-anchor="{anchor}" class="val">{txt}</text>')` | Adds the label with the rate. |
| 856 | `        nev = len(p['events']['thp_collapse_alloc']) + len(p['events']['pgmigrate_success'])` | `nev`: the count of intervals before which one of the two counters rose. |
| 857 | `        lv = p['levels']` | `lv`: the level counts of the process. |
| 858 | `        for j, t in enumerate((f'median {fx(p["median"])} GB/s', f'{fx(p["min"])} to {fx(p["max"])} GB/s',` | Loop over four text lines for the right side of the panel. This line holds the first two: the median rate, and the lowest and the highest rate, in GB/s. |
| 859 | `                               f'low {lv["low"]}, between {lv["between"]}, high {lv["high"]}', f'counter increases: {nev}')):` | Continues line 858 with the last two: the counts of low intervals, of intervals between the limits and of high intervals, and the count of counter increases. |
| 860 | `            o.append(f'<text x="{W-R+8}" y="{y0+24+j*14}" class="val">{t}</text>')` | Adds each of the four text lines at the right of the panel. |
| 861 | `        o.append(f'<text x="14" y="{y0+ph/2}" text-anchor="middle" class="ax" transform="rotate(-90 14 {y0+ph/2})">GB/s</text>')` | Adds the unit `GB/s` at the left of the panel, turned by 90 degrees. |
| 862 | `    o.append(f'<text x="{L+(W-L-R)/2}" y="{H-8}" text-anchor="middle" class="ax">interval number in the process (each interval is at least 0.3 s)</text>')` | Adds the title below all panels: the interval number in the process, and that each interval is at least 0.3 s. The value 0.3 s is typed. It fits the option `--min-ms 300` of the run script. |
| 863 | `    o.append('</svg>')` | Adds the line that closes the drawing. |
| 864 | `    return '\n'.join(o), left_out` | Returns the drawing as one text, and the list `left_out`. |

### Functions `counter_chart` and `small`: the counter values per group (lines 867 to 920)

| Line | Source | Explanation |
|---:|---|---|
| 867 | `def counter_chart(groups, aria):` | Starts the function `counter_chart`. It draws the counter values of the level groups of step C1 or C2. |
| 868 | `    """Small multiples: one panel per value, one row per group (CPU, kernel, level). The rate panel prints the number only.` | Docstring: small multiples: one panel per value, and one row per group of CPU, kernel and level. The rate panel prints the number only. |
| 869 | `    Every other panel has its own axis from 0 to the value printed under it."""` | Docstring: every other panel has its own axis from 0 to the value that is printed under it. |
| 870 | `    cols = [('median_thread_GBps', 'rate, GB/s', 2)] + [('median_%s_per_line' % k, n + ' per line', 3) for k, n in EV]` | `cols`: the six panels. Each has a key of the analysis result, a title and a count of decimals. The first is the median rate of a thread in GB/s, with 2 decimals. The other five are the median counts per line of the five events of `EV`, with 3 decimals. |
| 871 | `    W, L, rh, top = 900, 236, 19, 40` | Four sizes in units of the drawing. `W`: the width, 900. `L`: the left margin for the group names, 236. `rh`: the height of one row, 19. `top`: the space above the first row, 40. |
| 872 | `    pw = (W - L - 8) / len(cols)` | `pw`: the width of one panel. |
| 873 | `    H = top + len(groups) * rh + 30` | `H`: the height of the drawing. |
| 874 | `    o = pa.svg_open(W, H, aria)` | `o`: the list of the text lines of the drawing, with the opening line. |
| 875 | `    for ci, (key, name, nd) in enumerate(cols):` | Loop over the panels, with the index `ci`. |
| 876 | `        x0 = L + ci * pw` | `x0`: the left edge of the panel. |
| 877 | `        vals = [g[key] for g in groups if g[key] is not None]` | `vals`: the values of this panel for all groups that have one. |
| 878 | `        vmax = max(vals + [1e-12])` | `vmax`: the highest of them. The small value `1e-12` makes sure that the division of line 898 never divides by 0. |
| 879 | `        words = name.split(' per line')` | `words`: the title, split at the text `per line`. |
| 880 | `        o.append(f'<text x="{fx(x0+4, 1)}" y="14" class="lab">{e(words[0])}</text>')` | Adds the first heading line of the panel: the name of the value. |
| 881 | `        o.append(f'<text x="{fx(x0+4, 1)}" y="28" class="ax">{"per 64 B line" if len(words) > 1 else "median"}</text>')` | Adds the second heading line: `per 64 B line` for a counter panel, `median` for the rate panel. |
| 882 | `        if ci:` | The next two lines run for every panel but the rate panel. |
| 883 | `            o.append(f'<line x1="{fx(x0+4, 1)}" y1="{top-4}" x2="{fx(x0+4, 1)}" y2="{H-26}" stroke="{GRID}"/>')` | Adds the vertical axis line of the panel. |
| 884 | `            o.append(f'<text x="{fx(x0+4, 1)}" y="{H-10}" class="ax">{"all values are 0" if max(vals + [0]) == 0 else "axis: 0 to " + small(vmax, nd, chart=True)}</text>')` | Adds a text under the panel: that all values are 0, or the end value of the axis. |
| 885 | `        for gi, g in enumerate(groups):` | Loop over the groups, with the index `gi`. |
| 886 | `            y = top + gi * rh + rh / 2` | `y`: the vertical middle of the row of the group. |
| 887 | `            if ci == 0:` | The next three lines run for the first panel only. |
| 888 | `                o.append(f'<text x="{L-8}" y="{fx(y+4, 1)}" text-anchor="end" class="lab">{e(g["_name"])}</text>')` | Adds the name of the group at the left. |
| 889 | `                heavy = g.get('_last')` | `heavy`: the mark `_last` of the group (line 1557). It is true when the next group belongs to another CPU. |
| 890 | `                o.append(f'<line x1="{0 if heavy else L}" y1="{fx(y+rh/2, 1)}" x2="{W}" y2="{fx(y+rh/2, 1)}" stroke="{MUTED if heavy else GRID}"/>')` | Adds the line below the row. Below a heavy row it is dark grey and starts at the left edge of the drawing. |
| 891 | `            v = g[key]` | `v`: the value of the group for this panel. |
| 892 | `            if v is None:` | Tests whether the value is missing. It is missing when no counter row of the group holds a count for the event. |
| 893 | `                o.append(f'<text x="{fx(x0+10, 1)}" y="{fx(y+4, 1)}" class="ax">not supported</text>')` | Then the text `not supported` is added. |
| 894 | `                continue` | Nothing more is drawn for this group in this panel. |
| 895 | `            if ci == 0:` | Tests whether this is the rate panel. |
| 896 | `                o.append(f'<text x="{fx(x0+4, 1)}" y="{fx(y+4, 1)}" class="val">{fx(v, nd)}</text>')` | Then only the number is added, with 2 decimals. |
| 897 | `                continue` | No line and no dot is drawn in the rate panel. |
| 898 | `            xv = x0 + 4 + v / vmax * (pw - 62)` | `xv`: the horizontal position of the value. The axis of the panel goes from 0 to `vmax`. 62 units of the panel width stay free for the number. |
| 899 | `            o.append(f'<line x1="{fx(x0+4, 1)}" y1="{fx(y, 1)}" x2="{fx(xv, 1)}" y2="{fx(y, 1)}" stroke="{C0}" stroke-width="1.5"/>')` | Adds a blue line from the axis to the value. |
| 900 | `            o.append(f'<circle cx="{fx(xv, 1)}" cy="{fx(y, 1)}" r="3.5" fill="{C0}" stroke="#fff" stroke-width="1"/>')` | Adds a blue dot at the value. |
| 901 | `            o.append(f'<text x="{fx(xv+6, 1)}" y="{fx(y+4, 1)}" class="val">{small(v, nd, chart=True)}</text>')` | Adds the number at the right of the dot, from `small`. |
| 902 | `    o.append('</svg>')` | Adds the line that closes the drawing. |
| 903 | `    return '\n'.join(o)` | Returns the drawing as one text. |
| 906 | `def small(v, nd=3, chart=False):` | Starts the function `small`. It prints a count per line. |
| 907 | `    """A count per line with nd decimals. A value below 0.000001 is printed as 'below 1 per million' (lines).` | Docstring: a count per line with `nd` decimals. A value below 0.000001 is printed as "below 1 per million" (lines). |
| 908 | `    Another value that would print as 0 keeps two significant digits."""` | Docstring: another value that would print as 0 keeps two significant digits. |
| 909 | `    if v is None:` | Tests whether the value is missing. |
| 910 | `        return '-'` | Then the text `-` is returned. |
| 911 | `    if v == 0:` | Tests whether the value is exactly 0. |
| 912 | `        return '0'` | Then the text `0` is returned. |
| 913 | `    if abs(v) < 1e-6:` | Tests whether the absolute value is below 0.000001. |
| 914 | `        return 'below 10^-6' if chart else 'below 1 per million'` | Then a fixed text is returned: `below 10^-6` for a chart, `below 1 per million` for a table. |
| 915 | `    if abs(v) < 0.5 * 10 ** -nd:` | Tests whether the value would print as 0 with `nd` decimals: its absolute value is below half of the last decimal. |
| 916 | `        digits = 1 - math.floor(math.log10(abs(v)))` | `digits`: the count of decimals that shows two significant digits of the value. |
| 917 | `        return '%.*f' % (digits, v)` | Returns the value with that count of decimals. |
| 918 | `    return fx(v, nd)` | Every other value is returned as the text of `fx` with `nd` decimals. |

### Section helpers `many`, `fref` and `frefs` (lines 921 to 934)

| Line | Source | Explanation |
|---:|---|---|
| 921 | `# ---------------------------------------------------------------- sections` | Comment: a divider. The functions that build the sections of the generated page follow. |
| 923 | `def many(D):` | Starts the function `many`. |
| 924 | `    return len(D['names']) > 1` | Returns true when the input holds more than one session. |
| 927 | `def fref(R, D, name, step):` | Starts the function `fref`. It gives the citations of the result folders of one step in one session. |
| 928 | `    return R(*[('folder', name, f) for f in D['sessions'][name]['load'].get(step, {}).get('folders', [])])` | Calls `R` with one key per result folder of the step. So each folder is marked as used, and the text of its citations is returned. A step without a folder gives an empty text. |
| 931 | `def frefs(R, D, *steps):` | Starts the function `frefs`. It does the same for several steps. |
| 932 | `    return ''.join(fref(R, D, n, st) for n in D['names'] for st in steps)` | Returns the citations of `fref` for every session and every given step, as one text. |

### Function `sec_hyp`: the section "Result for each hypothesis" (lines 935 to 962)

| Line | Source | Explanation |
|---:|---|---|
| 935 | `def sec_hyp(D, R):` | Starts the function `sec_hyp`. It builds the section with the hypothesis table. |
| 936 | `    o = ['<h2 id="hyp">Result for each hypothesis</h2>']` | `o`: the list of the HTML pieces of the section. Its first piece is the heading "Result for each hypothesis" with the anchor `hyp`. |
| 937 | `    one = not many(D)` | `one`: true when the input holds one session. |
| 938 | `    o.append('<p>The last column gives one of the five words of rule 11 of the plan ' + R('plan') + '. The word comes from the decision functions of the analysis script, with the provisional level limits unchanged ' + R('analyze', 'decide') + '. '` | Adds the first paragraph. It says where the word of the last column comes from: rule 11 of the plan, applied by the decision functions of the analysis script with the provisional level limits unchanged. It cites the plan, `analyze_bwx.py` and `decide.py`. |
| 939 | `             'Each session has its own column with the result of that session, the processes that the rule uses, and the A/A spread.</p>')` | Continues line 938: the paragraph also says what the column of a session holds: the result of that session, the processes that the rule uses, and the A/A spread. |
| 940 | `    if one:` | The next two lines run for an input with one session. |
| 941 | `        o.append('<p class="take">This page has one session. Rule 11 of the plan needs the failed prediction in two sessions for the word "rejected" ' + R('plan') + '. '` | Adds a highlighted paragraph on the limit of an input with one session: rule 11 needs the failed prediction in two sessions for the word "rejected", with a citation of the plan. |
| 942 | `                 'So no row of this table can say "rejected". A row can say that the bounded prediction failed in this session.</p>')` | Continues line 941 with the consequence: no row of the table can say "rejected", and a row can still say that the bounded prediction failed in this session. |
| 943 | `    o.append('<div class="tw"><table class="pt hy"><tr><th style="width:12%">Hypothesis</th><th style="width:9%">Step</th>' + ''.join(f'<th>Session {e(n)}: result</th>' for n in D['names'])` | Opens the table and its header row: the column `Hypothesis` with 12 % of the width, the column `Step` with 9 %, and one result column per session with the session name. |
| 944 | `             + f'<th style="width:11%">Word over {"both sessions" if len(D["names"]) == 2 else "all sessions" if many(D) else "the session"} (rule 11)</th></tr>')` | Continues line 943 with the last header cell, 11 % wide: the word over the sessions by rule 11. Its text says `both sessions` for two sessions, `all sessions` for more, and `the session` for one. |
| 945 | `    for r in D['hyp']:` | Loop over the rows of the hypothesis table. |
| 946 | `        cells = ''` | `cells`: the cells of the sessions, empty at the start. |
| 947 | `        for n in D['names']:` | Loop over the sessions. |
| 948 | `            v = r['per'].get(n)` | `v`: the values of the row for this session, or `None`. |
| 949 | `            cells += ('<td>-</td>' if not v else f"<td>{e(v['result'])}<br><span class=\"sm\">Processes used by the rule (of all processes): {e(v['used'])}. A/A spread, GB/s: {e(v['spread'])}.</span></td>")` | Adds one cell. Without values it holds `-`. With values it holds the result text and, below it in small text, the processes that the rule used and the A/A spread in GB/s. |
| 950 | `        o.append(f"<tr><td>{e(r['h'])}</td><td>{e(r['step'])}</td>{cells}<td><b>{e(r['word'])}</b></td></tr>")` | Adds the table row: the hypothesis, the step, the cells of the sessions, and the word in bold. |
| 951 | `    o.append('</table></div>')` | Closes the table. |
| 952 | `    notes = [r for r in D['hyp'] if r['notes']]` | `notes`: the rows that have at least one note. |
| 953 | `    if notes:` | Tests whether there is such a row. |
| 954 | `        o.append('<p><b>Notes to the rows.</b> A note is a limit of the word or a description. It changes no word.</p><ul>'` | Then a paragraph is added with the heading "Notes to the rows". It tells the reader that a note limits or describes a word and changes none. |
| 955 | `                 + ''.join(f"<li><b>{e(r['h'])}.</b> {e(' '.join(r['notes']))}</li>" for r in notes) + '</ul>')` | Continues line 954 with a list: one item per such row, with the name of the hypothesis in bold and its notes as one text. |
| 956 | `    opens = [t for r in D['hyp'] for t in r['open']]` | `opens`: the open items of all rows. |
| 957 | `    o.append('<div class="open"><p><b>Open for the user.</b></p><ul>' + ''.join(f'<li>{e(t)} ' + R('plan', 'handoff', 'devscripts') + '</li>' for t in opens)` | Adds the box "Open for the user" as a list. Each open item is followed by the citations of the plan, of the handoff note and of the note on the deviations of the scripts. |
| 958 | `             + '<li>The level limits. Every word that needs a label uses the provisional limits of ' f'{LOW:g}' ' and ' f'{HIGH:g}' ' GB/s. The section on the reference rate describes how they fit the data. This page does not change them.</li></ul></div>')` | Continues line 957 with one more item that every input gets: a reminder that every word that needs a label uses the provisional limits, printed from `LOW` and `HIGH`, and that the generated page does not change them. |
| 959 | `    o.append('<p class="cap">The hypotheses are quoted in "Words used here". H4 has one row per level label, because the rule decides each label alone ' + R('handoff') + '.</p>')` | Adds a caption: it points to the list "Words used here" for the hypotheses and gives the reason for the two rows of H4, with a citation of the handoff note. |
| 960 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `sec_load`: the section "System load of every step" (lines 963 to 1037)

| Line | Source | Explanation |
|---:|---|---|
| 963 | `def sec_load(D, R):` | Starts the function `sec_load`. It builds the section on the system load. |
| 964 | `    o = ['<h2 id="load">System load of every step</h2>']` | `o`: the pieces of the section. The first piece is the heading "System load of every step" with the anchor `load`. |
| 965 | `    rows, takes, extra = [], [], []` | Three empty lists: `rows` (the rows of the table), `takes` (one summary per session) and `extra` (more paragraphs). |
| 966 | `    any_high = False` | `any_high`: becomes true when a session has a high load value. |
| 967 | `    for name in D['names']:` | Loop over the sessions. |
| 968 | `        x = D['sessions'][name]` | `x`: the values of the session. |
| 969 | `        L = x['load']` | `L`: its load facts per step (lines 321 to 343). |
| 970 | `        if not L:` | Tests whether the session has no step of Q1. |
| 971 | `            o.append(miss(f'The system load{" of session " + e(name) if many(D) else ""}: no process of a step of this page is in the input.'))` | Then a block "Insufficient data" is added: no process of a step of this page is in the input. |
| 972 | `            continue` | The loop goes on with the next session. |
| 973 | `        run = max(max(v['runnable_max'] or 0, v['runnable2_max'] or 0) for v in L.values())` | `run`: the highest count of runnable tasks of the session, over all steps and over both readings (header line and `launches.txt`). |
| 974 | `        waited = sum(v['n_waited'] for v in L.values())` | `waited`: the count of launches of the session that waited. |
| 975 | `        n = sum(v['n'] for v in L.values())` | `n`: the count of all launches of the session. |
| 976 | `        logins = max((v['logins_max'] for v in L.values() if v['logins_max'] is not None), default=None)` | `logins`: the highest number of logged-in users over the steps, or `None` when no step has a value. |
| 977 | `        refs = R(*[('folder', name, f['name']) for f in x['folders']])` | `refs`: the citations of all result folders of the session that hold processes. |
| 978 | `        takes.append(f'{"Session " + e(name) + ". " if many(D) else ""}Before each of the {pl(n, "launch", "launches")} the script read at most {pl(run, "runnable task", "runnable tasks")}. '` | Starts the summary of the session. First sentence: before each of the `n` launches the script read at most `run` runnable tasks. With several sessions the session name stands in front. |
| 979 | `                     f'{waited} of the {pl(n, "launch", "launches")} waited for an idle system (at most 2 runnable tasks). '` | Continues line 978: how many of the launches waited for an idle system. The text explains idle as at most 2 runnable tasks. |
| 980 | `                     + ('' if logins is None else 'No user was logged in at any launch. ' if logins == 0 else f'At most {pl(logins, "user was", "users were")} logged in at a launch. ') + refs)` | Ends the summary with the users: nothing when the value is unknown, a sentence that no user was logged in at any launch for the value 0, or the highest count of users. Then the citations follow. |
| 981 | `        hi = max(L.items(), key=lambda kv: kv[1]['load_max'] or 0)` | `hi`: the step with the highest 1-minute load average of the session. |
| 982 | `        if hi[1]['load_max'] is not None and hi[1]['load_max'] > 2:` | Tests whether that highest value is above 2 tasks. |
| 983 | `            any_high = True` | Marks that a high load value exists. |
| 984 | `            v = hi[1]` | `v`: the load facts of that step. |
| 985 | `            before = [f for f in x['other'] + x['folders'] if f['env'].get('end_utc') and f['threads_max'] > 1]` | `before`: the folders of the session, of all steps, that have an end time in `env.txt` and a header line with more than 1 thread. |
| 986 | `            start = next((f['env'].get('start_utc') for f in x['folders'] if hi[0] in f['steps']), None)` | `start`: the start time of the first folder that holds the step with the high load. |
| 987 | `            prev = max((f for f in before if start and f['env']['end_utc'] <= start), key=lambda f: f['env']['end_utc'], default=None)` | `prev`: the folder of `before` with the latest end time that is not later than `start`. The times are compared as text. For this fixed time format the text order is the time order. |
| 988 | `            extra.append(f'<p>{"Session " + e(name) + ". " if many(D) else ""}The 1-minute load average was high at some launches. Its highest value was {fx(v["load_max"])} tasks, in step {hi[0]}. '` | Starts a paragraph for `extra`: the 1-minute load average was high at some launches, with its highest value in tasks and the step. |
| 989 | `                         f'In that step it was {fx(v["load_first"])} tasks at the first launch and {fx(v["load_last"])} tasks at the last launch. '` | Continues line 988: the value at the first and at the last launch of that step. |
| 990 | `                         + (f'The step before, in folder <code>{e(prev["name"])}</code>, ran {prev["threads_max"]} threads of our own benchmark and ended at {e(prev["env"]["end_utc"])} {R(("folder", name, prev["name"]))}. '` | Continues line 988 for the case that `prev` exists: the step before, in the folder `prev`, ran its count of threads of our own benchmark and ended at its end time, with a citation of that folder. |
| 991 | `                            f'Step {hi[0]} started at {e(start)}. ' if prev else` | Continues line 990: the time at which the step with the high load started. |
| 992 | `                            f'Hypothesis: the high values are left from a process with 120 threads of our own benchmark that ended before the launch. The <code>env.txt</code> of the step before would show it. That folder is not in the input of this page. ')` | Continues line 988 for the case without `prev`: a sentence that is marked as a hypothesis. The high values are left from a process with 120 threads of our own benchmark that ended before the launch. The `env.txt` of the step before would show it, and that folder is not in the input. |
| 993 | `                         + '</p>')` | Closes the paragraph. |
| 994 | `        for st, v in sorted(L.items(), key=lambda kv: (kv[1]['t_start'] is None, kv[1]['t_start'] or 0, Q1_STEPS.index(kv[0]))):` | Loop over the steps of the session in the order in which they ran: by the start time of the step. A step without a start time comes last. Steps with equal times keep the order of `Q1_STEPS`. |
| 995 | `            top = f"{fx(v['top'][0], 1)} %: {e(v['top'][2])} ({e(v['top'][1])})" if v['top'] else f'{ID}: no launches.txt entry'` | `top`: the text for the busiest other process: its percent of one CPU with 1 decimal, the command, and the account in brackets. Without an entry of `launches.txt` it is `Insufficient data` with that reason. |
| 996 | `            rows.append((f"<td>{e(name)}</td>" if many(D) else '') + f"<td>{st}</td><td>{v['n']}</td><td class=\"nw\">{e(v['first_utc'])} to {e(v['last_utc'])}</td>"` | Starts the table row of the step: the session (with several sessions), the step, the count of launches, and the UTC time of the first and of the last launch. |
| 997 | `                        f"<td class=\"nw\">{f2(v['load_min'])} to {f2(v['load_max'])}</td><td>{v['runnable_max']} / {'-' if v['runnable2_max'] is None else v['runnable2_max']}</td>"` | Continues line 996: the lowest and the highest 1-minute load average, and the highest count of runnable tasks of the header lines and of `launches.txt`. |
| 998 | `                        f"<td>{v['n_waited']}</td><td>{'-' if v['wait_max'] is None else '%g' % v['wait_max']}</td><td>{'-' if v['logins_max'] is None else v['logins_max']}</td><td class=\"wr\">{top}</td>")` | Ends the row: the count of launches that waited, the longest wait in s, the highest number of logged-in users, and `top`. A missing value is printed as `-`. |
| 999 | `            t = v['top']` | `t`: the busiest other process of the step. |
| 1000 | `            if t and t[0] > 5:` | Tests whether it exists and used more than 5 % of one CPU. |
| 1001 | `                own = t[1] in v['own_users']` | `own`: true when its account is the account of the run script. |
| 1002 | `                oth = [b[0] for b in v['busy_all'] if b != t]` | `oth`: the percent values of all other process lines of the step. |
| 1003 | `                s = (f'<p>{"Session " + e(name) + ", step " if many(D) else "Step "}{st}. The busiest other process is <code>{e(t[2])}</code> of the account <code>{e(t[1])}</code>, with {fx(t[0], 1)} % of one CPU at one launch. '` | Starts a paragraph `s`: the step, the command and the account of the busiest other process, and its percent of one CPU at one launch. |
| 1004 | `                     + (f'At the other launches of the step no other process is above {fx(max(oth), 1)} %. ' if oth else ''))` | Continues line 1003 when other process lines exist: the highest percent value among them, as the value that no other process exceeds. |
| 1005 | `                if own:` | The next two lines run when the account is the account of the run script. |
| 1006 | `                    s += ('The run script runs under the same account, so this is not another user. The tool <code>ps</code> gives the CPU time of a process divided by the time since its start. '` | Adds two typed sentences. The process is not another user, as the run script runs under the same account. And the tool `ps` computes its percent value as the CPU time of a process divided by the time from its start. |
| 1007 | `                          'Hypothesis: this process started seconds before the launch, with the login of our own visit. The start time of the process (<code>ps -o lstart</code>) would confirm or reject it.')` | Adds a sentence that is marked as a hypothesis: the process started seconds before the launch, with the login of our own visit. The start time of the process, which `ps -o lstart` prints, would confirm or reject it. |
| 1008 | `                else:` | The next line runs for any other account. |
| 1009 | `                    s += f'{ID}: what this process did. Its command line and its CPU time during the step would show it.'` | Adds `Insufficient data`: what this process did. Its command line and its CPU time during the step would show it. |
| 1010 | `                extra.append(s + '</p>')` | Appends the paragraph to `extra`. |
| 1011 | `        if x['left_out']:` | Tests whether the analysis left out a process of the session. |
| 1012 | `            extra.append('<p>Processes that the analysis left out: ' + ' '.join(f'{st} {e(tag)} ({e(why)}).' for st, tag, why in x['left_out']) + '</p>')` | Then a paragraph is added to `extra`: the step, the tag and the reason of every process that was left out. |
| 1013 | `        err = [f for f in x['folders'] if f['stderr_bytes']]` | `err`: the folders of the session whose `stderr.txt` is not empty. |
| 1014 | `        if err:` | Tests whether there is such a folder. |
| 1015 | `            extra.append('<p>The file <code>stderr.txt</code> is not empty in: ' + ', '.join(f"<code>{e(f['name'])}</code>" for f in err) + '.</p>')` | Then a paragraph is added to `extra` with the names of these folders. |
| 1016 | `    if takes:` | Tests whether a summary exists. |
| 1017 | `        o.append('<p class="take">' + '<br>'.join(takes) + '</p>')` | Then the summaries of all sessions are added as one highlighted paragraph, with a line break between two sessions. |
| 1018 | `    if rows:` | The next lines run when the table has rows. |
| 1019 | `        o.append('<div class="tw"><table class="c">' + '<tr>' + ('<th>Session</th>' if many(D) else '') + '<th>Step</th><th>Launches</th><th>UTC, first to last launch</th><th>1-minute load (tasks), lowest to highest</th>'` | Opens the table with its header row. This line holds the columns for the session (with several sessions), the step, the launches, the UTC time of the first and the last launch, and the lowest to highest 1-minute load in tasks. |
| 1020 | `                 '<th>Runnable tasks, highest: header line / launches.txt</th><th>Launches that waited</th><th>Longest wait, s</th>'` | Continues line 1019: the columns for the highest count of runnable tasks in the header line and in `launches.txt`, for the launches that waited, and for the longest wait in s. |
| 1021 | `                 '<th>Logged-in users, highest</th><th class="l">Busiest other process (% of one CPU)</th></tr>' + ''.join(f'<tr>{r}</tr>' for r in rows) + '</table></div>')` | Ends the table: the columns for the highest number of logged-in users and for the busiest other process in percent of one CPU, then all rows. |
| 1022 | `        o.append('<p class="cap">The rows are in the order in which the steps ran. The script reads the runnable tasks twice before a launch: first for <code>launches.txt</code>, then for the header line of the process. '` | Starts the caption of the table. It gives the order of the rows (the order in which the steps ran) and explains the two values of runnable tasks: the script reads the value twice before a launch, first for `launches.txt` and then for the header line. |
| 1023 | `                 'So the two values can differ. One of the runnable tasks is the script that reads the value. "Busiest other process" leaves out <code>ps</code> and <code>bash</code>, which are the script itself ' + R('runscript') + '. '` | Continues line 1022: one of the runnable tasks is the script that reads the value, and the column of the busiest other process leaves out `ps` and `bash`. A citation of the run script follows. |
| 1024 | `                 'A name that starts with <code>kworker</code> or <code>rcu</code> is a thread of the Linux kernel.</p>')` | Ends the caption with a hint for the reader: a name that starts with `kworker` or `rcu` is a thread of the Linux kernel. |
| 1025 | `    o += extra` | Adds the paragraphs of `extra`. |
| 1026 | `    if any_high:` | Tests whether a high load value exists. |
| 1027 | `        o.append('<p>The 1-minute load average is an average over about the last minute. So it still counts the threads of a process that has ended. '` | Then a paragraph explains the 1-minute load average: it is an average over about the last minute, so it still counts the threads of a process that has ended. |
| 1028 | `                 'It is therefore no evidence of another user. The evidence of an otherwise idle system is the three readings above: the runnable tasks, the waits and the logged-in users.</p>')` | Continues line 1027 with the conclusion: a high value is no evidence of another user. The evidence of an idle system is the three readings above: the runnable tasks, the waits and the logged-in users. |
| 1029 | `    elif rows:` | Tests the other case: the table has rows and no load value is high. |
| 1030 | `        o.append('<p>No launch on this page had a 1-minute load average above 2 tasks.</p>')` | Then one sentence is added: no launch had a 1-minute load average above 2 tasks. |
| 1031 | `    o.append(f'<p>{ID}: load readings during an interval. The script reads the load only directly before each launch ' + R('runscript') + '. A reading of the runnable tasks of each account during an interval would give it.</p>')` | Adds a paragraph for every input: `Insufficient data` for load readings during an interval. The script reads the load only directly before each launch, with a citation of the run script. A reading of the runnable tasks of each account during an interval would give it. |
| 1032 | `    return '\n'.join(o)` | Returns the section as one text. |
| 1035 | `COPY_STEPS = ('B1', 'B2', 'B3', 'C2')` | `COPY_STEPS`: the four steps whose sequences hold copy loops: B1, B2, B3 and C2. |

### Function `sec_refs`: the section on the reference rate and the two level limits (lines 1038 to 1116)

| Line | Source | Explanation |
|---:|---|---|
| 1038 | `def sec_refs(D, R):` | Starts the function `sec_refs`. It builds the section that compares the two level limits with the measured reference rates. |
| 1039 | `    o = ['<h2 id="level">The reference rate and the two level limits</h2>']` | `o`: the pieces of the section. The first piece is the heading "The reference rate and the two level limits" with the anchor `level`. |
| 1040 | `    o.append('<p>Rule 5 of the plan labels an interval at 8 MiB by its neighbouring reference intervals of asm read: low below ' f'{LOW:g}' ' GB/s, high above ' f'{HIGH:g}' ' GB/s ' + R('plan') + '. '` | Adds the first paragraph, typed text with the two limits printed from `LOW` and `HIGH`. Its first sentence states rule 5 of the plan: an interval at 8 MiB gets its label from its neighbouring reference intervals of asm read. It cites the plan. |
| 1041 | `             'The handoff then uses a process only if all its reference intervals have one label ' + R('handoff') + '. The plan calls the two limits provisional. It asks to check them against the new data before they are used ' + R('plan') + '. '` | Continues line 1040 with two more points: the handoff note uses a process only when all its reference intervals have one label, and the plan calls the two limits provisional and asks for a check against the new data. Both points carry a citation. |
| 1042 | `             'This section is that check. The limits were not changed.</p>')` | Ends the paragraph: it names this section as that check and says that the limits were not changed. |
| 1043 | `    o.append(f'<p><span class="lg"><i style="background:{C0}"></i>one interval</span><span class="lg"><i style="background:{C1c};border-radius:0;transform:rotate(45deg)"></i>first reference interval of a process</span>'` | Adds the legend of the charts. This line: a blue circle for one interval, and an orange diamond for the first reference interval of a process. |
| 1044 | `             f'<span class="lg"><i style="background:{BAND};border-radius:0"></i>between the two limits: no label</span></p>')` | Continues line 1043: a shaded square for the range between the two limits, where an interval gets no label. |
| 1045 | `    allv = [v for x in D['sessions'].values() for r in x['refs'] for v in r['first'] + r['rest']]` | `allv`: the rates of all rows of the section (lines 397 to 417), over all sessions. |
| 1046 | `    takes, tables, desc = [], [], []` | Three empty lists: `takes` (one summary per session), `tables` (the folded tables) and `desc` (one description per session). |
| 1047 | `    thin = False` | `thin`: becomes true when a chart row does not show every interval. |
| 1048 | `    for name in D['names']:` | Loop over the sessions. |
| 1049 | `        x = D['sessions'][name]` | `x`: the values of the session. |
| 1050 | `        rows = x['refs']` | `rows`: its rows of reference rates. |
| 1051 | `        if not rows:` | Tests whether the session has no such row. |
| 1052 | `            o.append(miss(f'The reference rates{" of session " + e(name) if many(D) else ""}: no process at 8 MiB is in the input.'))` | Then a block "Insufficient data" is added: no process at 8 MiB is in the input. |
| 1053 | `            continue` | The loop goes on with the next session. |
| 1054 | `        xmin, xmax = axis_floor(min(min(allv), LOW) - 0.2), max(max(allv), HIGH) + 0.4` | `xmin` and `xmax`: the two ends of the rate axis, the same for all sessions. The start lies 0.2 GB/s below the lower one of the lowest rate and `LOW`, rounded down by `axis_floor`. The end lies 0.4 GB/s above the higher one of the highest rate and `HIGH`. |
| 1055 | `        chart, groups = [], set()` | `chart`: the rows of the chart. `groups`: the row numbers that end a step. Both start empty. |
| 1056 | `        for i, r in enumerate(rows):` | Loop over the rows of reference rates, with the index `i`. |
| 1057 | `            pts = [(v, f'{fx(v)} GB/s', 0) for v in r['rest'][::max(1, len(r['rest']) // 120)]] + [(v, f'first reference interval of a process: {fx(v)} GB/s', 1) for v in r['first']]` | `pts`: the markers of the chart row. A dot is drawn for every k-th rate of the list `rest`. `k` is the count of these rates divided by 120 without the remainder, and at least 1. A diamond is drawn for every rate of the list `first`. Each tooltip gives the rate in GB/s. |
| 1058 | `            chart.append((f"{r['step']} CPU {r['cpu']}, {r['kind']}", pts, f"{fx(r['median'])} GB/s. {r['low']} / {r['between']} / {r['high']}"))` | Appends the chart row: its name (step, CPU and kind), the markers, and the text for the right side: the median rate in GB/s and the three counts low, between and high. |
| 1059 | `            if i + 1 < len(rows) and rows[i + 1]['step'] != r['step']:` | Tests whether the next row belongs to another step. |
| 1060 | `                groups.add(i + 1)` | Then the number of this row, counted from 1, goes to `groups`. `strip` draws a heavy line below it. |
| 1061 | `        if many(D):` | Tests whether several sessions are shown. |
| 1062 | `            o.append(f'<h3>Session {e(name)}</h3>')` | Then a heading with the session name is added. |
| 1063 | `        o.append(strip(chart, xmin, xmax, f'rate of asm read at 8 MiB, GB/s (the axis starts at {xmin:g} GB/s, not at 0)', 'Distribution of the reference rate per step and CPU', groups=groups, right_head='median. low / between / high'))` | Adds the chart of `strip`. The title of its axis names the rate of asm read at 8 MiB in GB/s, gives the start value of the axis and says that the axis does not start at 0. The heading of the right column names the median and the three counts. |
| 1064 | `        thin = thin or max(len(r['rest']) for r in rows) > 120` | `thin` becomes true when a row of this session has more than 120 rates in `rest`. |
| 1065 | `        between = [r for r in rows if r['between'] * 2 > r['n']]` | `between`: the rows in which more than half of the intervals lie between the two limits. |
| 1066 | `        rr = [r for r in rows if r['kind'] == 'reference intervals']` | `rr`: the rows of the kind `reference intervals`. These are the rows of the steps B1, B2, B3, B6 and C2. |
| 1067 | `        t = f'{"Session " + e(name) + ". " if many(D) else ""}In {len(between)} of the {pl(len(rows), "row", "rows")}, more than half of the intervals lie between the two limits, where the rule gives no label. '` | Starts the summary `t` of the session: in how many of the rows more than half of the intervals lie between the two limits, where the rule gives no label. |
| 1068 | `        if rr:` | The next lines run when `rr` has rows. |
| 1069 | `            nst = sum(r['n_stable_low'] + r['n_stable_high'] for r in rr)` | `nst`: the count of stable processes over the rows of `rr`. |
| 1070 | `            steps = list(dict.fromkeys(r['step'] for r in rr))` | `steps`: the steps of these rows, each once, in the order of the rows. |
| 1071 | `            t += (f'Over the {pl(len(rr), "row", "rows")} of {", ".join(steps)} (the steps with reference intervals), the median reference rate of a row is between {fx(min(r["median"] for r in rr))} and {fx(max(r["median"] for r in rr))} GB/s. '` | Adds a sentence: over the rows of these steps, the median reference rate of a row lies between the lowest and the highest row median, in GB/s. |
| 1072 | `                  f'Over all {pl(len(rows), "row", "rows")} it is between {fx(min(r["median"] for r in rows))} and {fx(max(r["median"] for r in rows))} GB/s. '` | Adds the same sentence over all rows of the session. |
| 1073 | `                  f'{nst} of the {pl(sum(r["n_procs"] for r in rr), "process", "processes")} with reference intervals {"is" if nst == 1 else "are"} stable at one level. ')` | Adds a sentence: how many of the processes with reference intervals are stable at one level. |
| 1074 | `        takes.append(t + fref(R, D, name, 'B1') + fref(R, D, name, 'B4'))` | Appends the summary to `takes`, with the citations of the result folders of B1 and B4 of the session. |
| 1075 | `        tb = ['<div class="tw"><table class="c"><tr><th>Step</th><th>CPU</th><th class="l">Intervals</th><th>Count</th><th>Lowest, GB/s</th><th>Median, GB/s</th><th>Highest, GB/s</th><th>Low</th><th>Between</th><th>High</th>'` | Starts `tb`, a table with the counts of every row. This line opens the table and holds the first ten column titles: the step, the CPU, the kind of intervals, their count, the lowest, the median and the highest rate in GB/s, and the counts low, between and high. |
| 1076 | `              '<th>Processes</th><th>Stable low</th><th>Stable high</th><th>Not stable</th></tr>']` | Continues line 1075 with the last four titles: the processes, and how many of them are stable low, stable high and not stable. |
| 1077 | `        for r in rows:` | Loop over the rows. |
| 1078 | `            tb.append(f"<tr><td>{r['step']}</td><td>{r['cpu']}</td><td class=\"l nw\">{e(r['kind'])}</td><td>{r['n']}</td><td>{fx(r['min'])}</td><td>{fx(r['median'])}</td><td>{fx(r['max'])}</td>"` | Starts the table row: the step, the CPU, the kind, the count of intervals, and the lowest, the median and the highest rate. |
| 1079 | `                      f"<td>{r['low']}</td><td>{r['between']}</td><td>{r['high']}</td><td>{r['n_procs']}</td><td>{r['n_stable_low']}</td><td>{r['n_stable_high']}</td>"` | Continues line 1078: the three level counts, the process count, and the counts of stable low and stable high processes. |
| 1080 | `                      f"<td>{r['n_procs']-r['n_stable_low']-r['n_stable_high']}</td></tr>")` | Ends the table row with the count of processes that are not stable: all processes minus the stable low and the stable high ones. |
| 1081 | `        tables.append(f'<details><summary>Counts of every row{", session " + e(name) if many(D) else ""}</summary>' + ''.join(tb) + '</table></div></details>')` | Appends the table to `tables` inside a block that the reader can unfold. Its title is "Counts of every row", with the session name when several sessions are shown. |
| 1082 | `        # how the limits miss: rows of the copy steps whose median lies between the limits, and the first reference interval` | Comment: the next lines describe how the limits miss the data: the rows of the copy steps whose median lies between the limits, and the first reference interval. |
| 1083 | `        mid = [r for r in rr if r['step'] in COPY_STEPS and LOW <= r['median'] <= HIGH]` | `mid`: the rows of `rr` that belong to a copy step and whose median reference rate lies from `LOW` to `HIGH`. |
| 1084 | `        d = f'{"Session " + e(name) + ". " if many(D) else ""}'` | `d`: the description text of the session. It starts with the session name when several sessions are shown. |
| 1085 | `        if mid:` | The next lines run when `mid` has rows. |
| 1086 | `            sh = [100 * r['between'] / r['n'] for r in mid]` | `sh`: for each row of `mid` the percentage of its intervals that lie between the limits. |
| 1087 | `            d += (f'In {len(mid)} of the {pl(sum(1 for r in rr if r["step"] in COPY_STEPS), "row", "rows")} of the copy steps ({", ".join(s for s in COPY_STEPS if any(r["step"] == s for r in rr))}) the median reference rate lies between the two limits. '` | Adds a sentence: in how many of the rows of the copy steps the median reference rate lies between the two limits. The sentence names the copy steps that have rows. |
| 1088 | `                  f'These rows are on {cpus_words(sorted({r["cpu"] for r in mid}))}. Their medians are {rng(min(r["median"] for r in mid), max(r["median"] for r in mid))} GB/s. '` | Adds two sentences: the CPUs of these rows, and the range of their medians in GB/s. |
| 1089 | `                  f'That is {rng(HIGH - max(r["median"] for r in mid), HIGH - min(r["median"] for r in mid))} GB/s below the high limit. In these rows {rng(min(sh), max(sh), 0)} % of the intervals get no label. ')` | Adds two sentences: how far below the high limit these medians lie, as a range in GB/s, and the range of the percentage of intervals without a label, with no decimals. |
| 1090 | `        allrecs = [r2 for st in COPY_STEPS for g in x['pairs'][st].values() if g['size'] == 8 * MIB for r2 in g['recs']]` | `allrecs`: the records of all processes of the copy steps that ran at 8 MiB (lines 218 to 223). |
| 1091 | `        firsts = [r2 for r2 in allrecs if len(r2['refs']) > 2]` | `firsts`: those of them with more than 2 reference intervals. |
| 1092 | `        if firsts:` | The next lines run when `firsts` has records. |
| 1093 | `            nd = sum(1 for r2 in firsts if decide.level(r2['first_ref']) != decide.level(median(r2['refs'][1:])))` | `nd`: in how many of them the level word of the first reference interval differs from the level word of the median of the later reference rates. |
| 1094 | `            sw = sum(1 for r2 in allrecs if r2['stable_without_first'])` | `sw`: how many of all records would be stable without the first reference interval. |
| 1095 | `            d += (f'In {nd} of {pl(len(firsts), "copy process", "copy processes")} at 8 MiB the first reference interval has another label than the median of the later ones. '` | Adds a sentence with `nd` and the count of `firsts`. |
| 1096 | `                  f'Without the first reference interval, {sw} of the {len(allrecs)} processes would have all reference intervals at one level. ')` | Adds a sentence with `sw` and the count of all records. |
| 1097 | `        desc.append(d)` | Appends the description to `desc`. |
| 1098 | `    if takes:` | The next lines run when at least one session gave a summary. |
| 1099 | `        o.append('<p class="take">' + '<br>'.join(takes) + '</p>')` | Adds the summaries as one highlighted paragraph, with a line break between two sessions. |
| 1100 | `        o.append('<p class="cap">Each row has the reference intervals of all processes of one step on one CPU. For B4 and C1 each interval is its own reference, so the row has all intervals. '` | Starts the caption of the charts. It says what a row holds: the reference intervals of all processes of one step on one CPU, and for B4 and C1 all intervals, as each is its own reference. |
| 1101 | `                 + ('A row with more than 120 intervals shows every n-th interval, and the numbers at the right count all intervals. ' if thin else '')` | Continues line 1100 when `thin` is true: a sentence that a row with more than 120 intervals shows only every n-th interval, while the numbers at the right count all intervals. |
| 1102 | `                 + 'The dots are spread vertically so that they do not hide each other.</p>')` | Ends the caption with the reason for the vertical spread of the dots: they do not hide each other. |
| 1103 | `        o += tables` | Adds the folded tables. |
| 1104 | `    o.append('<p><b>Open decision for the user.</b> The limits ' f'{LOW:g}' ' and ' f'{HIGH:g}' ' GB/s come from the sweep of 2026-11-02 ' + R('plan') + '. '` | Starts the last paragraph, with the heading "Open decision for the user". Its first sentence is typed: the limits of 69 and 70.5 GB/s come from a run of 2026-11-02, which the text calls a sweep, with a citation of the plan. The two numbers are printed from `LOW` and `HIGH`. |
| 1105 | `             + ('The list gives how they fit the reference rates of this page (description, no decision).</p><ul>' + ''.join(f'<li>{t}</li>' for t in desc if t) + '</ul><p>' if any(desc) else '')` | Continues line 1104 when a description exists: a sentence that the list gives how the limits fit the reference rates (description, no decision), and the list with one item per session. |
| 1106 | `             + 'The first reference interval is the first timed interval of a new process, and all later ones follow a copy interval. The rule does not leave it out, and this page does not either. '` | Continues line 1104 with typed text on the first reference interval of a process: what it is, and that neither the rule nor the generated page leaves it out. |
| 1107 | `             'This page does not decide whether the limits are revised, or to which values. Until the user decides, every decision that needs a label uses the limits as they are. '` | Continues line 1104 with typed text: the generated page leaves the decision on the limits to the user, and every decision that needs a label uses the limits as they are until then. |
| 1108 | `             'Each step below also gives a description without labels, marked "description, no decision".</p>')` | Ends the paragraph with a pointer: each step below also gives a description without labels, under the mark "description, no decision". |
| 1109 | `    return '\n'.join(o)` | Returns the section as one text. |
| 1112 | `def cpus_words(cpus):` | Starts the function `cpus_words`. It prints a list of CPUs as words. |
| 1113 | `    c = [str(x) for x in cpus]` | `c`: the CPU numbers as texts. |
| 1114 | `    return 'CPU ' + c[0] if len(c) == 1 else 'CPUs ' + ', '.join(c[:-1]) + ' and ' + c[-1]` | Returns `CPU` and the number for one CPU. For several it returns `CPUs`, the numbers with commas, the word `and` and the last number. |

### Functions `sec_howto` and `stable_sentence` (lines 1117 to 1146)

| Line | Source | Explanation |
|---:|---|---|
| 1117 | `def sec_howto(D, R):` | Starts the function `sec_howto`. It returns a box of typed text that explains the charts and tables of the next sections. It does not use `D`. It uses `R` for the citation of line 1124. |
| 1118 | `    return ('<div class="how"><p><b>How to read the charts and tables of B1, B2, B3 and B6.</b></p><ul>'` | Opens the box with its heading "How to read the charts and tables of B1, B2, B3 and B6", and opens a list. |
| 1119 | `            '<li>One row of a chart is one process. The blue dot is d and the orange diamond is e. The blue number at the left is d. The orange number at the right is e. Both are in GB/s.</li>'` | Item 1 explains a chart row: it is one process, with the blue dot for `d`, the orange diamond for `e`, and the two number columns in GB/s. |
| 1120 | `            '<li>The shaded band goes from minus to plus the A/A spread of one CPU in one session. The faint blue line marks the median d of that CPU. Each chart has its own axis.</li>'` | Item 2 explains the shaded band (the A/A spread of one CPU in one session) and the faint blue line (the median `d` of that CPU). It adds that each chart has its own axis. |
| 1121 | `            '<li>In a table, the A/A spread is the largest absolute e of the CPU. "Largest single A/A pair" is the largest absolute difference of one pair of the two copies, before the median of the process is taken.</li>'` | Item 3 explains two table columns: the A/A spread (the largest absolute `e` of the CPU) and the largest single A/A pair (one pair of the two copies, before the median of the process is formed). |
| 1122 | `            '<li>"Order" gives the median pair value with the first loop of "d = X minus Y" timed first, and with it timed second.</li>'` | Item 4 explains the column "Order": the median pair value with the first loop of the difference timed first, and with it timed second. |
| 1123 | `            '<li>All columns before the column "Rule" describe all processes of the CPU and decide nothing. The column "Rule" gives the strict result of the decision rule: the number of processes that the rule uses, and its word. '` | Starts item 5. It separates the description columns, which cover all processes of the CPU and decide nothing, from the column "Rule", which gives the count of processes that the rule uses and its word. |
| 1124 | `            'A CPU needs 3 processes for a word. A result over the CPUs needs 2 such CPUs with one sign ' + R('handoff') + '.</li>'` | Ends item 5 with the two counts that the rule needs: 3 processes on a CPU for a word, and 2 such CPUs with one sign for a result over the CPUs. It cites the handoff note. |
| 1125 | `            '<li>At 8 MiB the rule uses only stable processes. The labels behind "stable" come from the provisional limits, which are not validated. So a word in the column "Rule" at 8 MiB is not a validated decision.</li>'` | Item 6 is a warning: at 8 MiB the rule uses only stable processes, the labels behind "stable" come from the provisional limits, and so a word of the column "Rule" at 8 MiB is not a validated decision. |
| 1126 | `            '</ul></div>')` | Closes the list and the box. |
| 1129 | `def stable_sentence(D):` | Starts the function `stable_sentence`. It writes one or two sentences on where stable processes exist. |
| 1130 | `    """Where stable processes exist, over all steps and sessions. Built from the reference rows."""` | Docstring: where stable processes exist, over all steps and sessions. The text is built from the reference rows. |
| 1131 | `    rows = [(n, r) for n, x in D['sessions'].items() for r in x['refs'] if r['kind'] == 'reference intervals']` | `rows`: pairs of session name and row, for all rows of the kind `reference intervals` of all sessions. |
| 1132 | `    if not rows:` | Tests whether there is no such row. |
| 1133 | `        return ''` | Then an empty text is returned. |
| 1134 | `    hi = sum(r['n_stable_high'] for _, r in rows)` | `hi`: the count of stable high processes over these rows. |
| 1135 | `    lo = sorted({r['cpu'] for _, r in rows if r['n_stable_low']})` | `lo`: the CPUs that have at least one stable low process, in rising order. |
| 1136 | `    t = ('No CPU has a stable high process in any step with reference intervals. ' if hi == 0 else f'{pl(hi, "process is", "processes are")} stable high. ')` | `t`: the first sentence. When `hi` is 0 it says that no CPU has a stable high process in any step with reference intervals. In every other case it gives the count of stable high processes. |
| 1137 | `    if lo:` | The next lines run when a CPU has a stable low process. |
| 1138 | `        main = max(lo, key=lambda c: sum(r['n_stable_low'] for _, r in rows if r['cpu'] == c))` | `main`: the CPU with the most stable low processes over all its rows. |
| 1139 | `        rest = [(n, r) for n, r in rows if r['n_stable_low'] and r['cpu'] != main]` | `rest`: the rows of other CPUs that have a stable low process. |
| 1140 | `        t += f'Stable low processes exist on CPU {main}' + (` | Adds the second sentence: stable low processes exist on the CPU `main`. |
| 1141 | `            ' only.' if not rest else ', and ' + ', '.join(f'{r["n_stable_low"]} on CPU {r["cpu"]} in step {r["step"]}{" of session " + n if many(D) else ""}' for n, r in rest) + '.')` | Ends that sentence: with the word `only` when `rest` is empty. If not, each row of `rest` is listed with its count, its CPU and its step, and with its session when several sessions are shown. |
| 1142 | `    else:` | The next line runs when no CPU has a stable low process. |
| 1143 | `        t += 'No process is stable low.'` | Adds the sentence that no process is stable low. |
| 1144 | `    return t` | Returns the text. |

### `pair_table`, `desc_takeaway`, `order_words`, `axis_of`: table and summary of one group (lines 1147 to 1206)

| Line | Source | Explanation |
|---:|---|---|
| 1147 | `def pair_table(items, labelled):` | Starts the function `pair_table`. It builds the table of one compared group. `labelled` is true for a group at 8 MiB, where the rule uses the level labels. |
| 1148 | `    """items: [(session, desc, labels of the rule)]. Per session and CPU: the description (all processes) and the strict result of the rule."""` | Docstring: `items` is a list of entries with a session, a description and the labels of the rule. The table gives per session and CPU the description (all processes) and the strict result of the rule. |
| 1149 | `    multi = len(items) > 1` | `multi`: true when several sessions are shown. |
| 1150 | `    lab_list = ('low', 'high') if labelled else ('none',)` | `lab_list`: the labels that get a rule column: low and high for a labelled group, `none` for any other group. |
| 1151 | `    if labelled and not any(v['n_high'] for _, d, _ in items for v in d['per_cpu'].values()):` | Tests whether the group is labelled and no CPU of any session has a stable high process. |
| 1152 | `        lab_list = ('low',)` | Then only the column of the label low is shown. |
| 1153 | `    head = {'none': 'Rule: processes, word', 'low': 'Rule, stable low (labels not validated): processes, word', 'high': 'Rule, stable high (labels not validated): processes, word'}` | `head`: the titles of the rule columns. The titles for low and high say that the labels are not validated. |
| 1154 | `    o = ['<div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if multi else '') + '<th>CPU</th><th>Processes</th><th>Median d, GB/s</th><th>d, lowest to highest, GB/s</th><th>Median d, % of the second loop</th>'` | Opens the table and starts its header row: the session (with several sessions), the CPU, the count of processes, the median `d` in GB/s, the lowest to highest `d`, and the median `d` in percent of the second loop. |
| 1155 | `         '<th>A/A spread, GB/s</th><th>Largest single A/A pair, GB/s</th><th>\|Median d\| above the A/A spread</th><th>All d have one sign</th>'` | Continues line 1154: the A/A spread in GB/s, the largest single A/A pair in GB/s, whether the absolute median `d` is above the A/A spread, and whether all `d` have one sign. |
| 1156 | `         '<th>Order: first loop timed first / second, GB/s</th>' + ''.join(f'<th>{head[lab]}</th>' for lab in lab_list) + '</tr>']` | Ends the header row: the column "Order" with the median pair value for the first loop timed first and timed second, and one rule column per label of `lab_list`. |
| 1157 | `    words = []` | `words`: the results of the rule over the CPUs, empty at the start. |
| 1158 | `    for s, desc, labels in items:` | Loop over the sessions of `items`. |
| 1159 | `        for c, v in desc['per_cpu'].items():` | Loop over the CPUs of the description. |
| 1160 | `            t = ('<tr>' + (f'<td>{e(s)}</td>' if multi else '') + f"<td>{c}</td><td>{v['n']}</td><td>{fs(v['median_d'])}</td><td class=\"nw\">{fs(v['d_min'])} to {fs(v['d_max'])}</td><td>{fs(v['pct'])}</td><td>{fx(v['aa_spread'])}</td>"` | Starts the table row with values of the description (lines 229 to 240): the session, the CPU, `n`, `median_d` with its sign, `d_min` to `d_max`, `pct` and `aa_spread`. |
| 1161 | `                 f"<td>{fx(v['aa_single_max'])}</td><td>{yn(v['above'])}</td><td>{yn(v['one_sign'])}</td><td class=\"nw\">{fs(v['d_first'])} / {fs(v['d_second'])}</td>")` | Continues line 1160: `aa_single_max`, the words yes or no for `above` and for `one_sign`, and `d_first` and `d_second` with their signs. |
| 1162 | `            for lab in lab_list:` | Loop over the labels of `lab_list`. |
| 1163 | `                pc = (labels or {}).get(lab, {}).get('per_cpu', {}).get(c)` | `pc`: the result of the rule for this label and this CPU, or `None`. |
| 1164 | `                t += f"<td class=\"nw\">{pc['n_processes']}: {e(pc['decision'] + ab.sign_txt(pc['sign']))}</td>" if pc else '<td>-</td>'` | Adds the rule cell: the count of processes that the rule used on the CPU, a colon, and the word of the rule with its sign. Without a result the cell holds `-`. |
| 1165 | `            o.append(t + '</tr>')` | Closes the table row and appends it. |
| 1166 | `        for lab in lab_list:` | Loop over the labels again, for the result over the CPUs. |
| 1167 | `            r = (labels or {}).get(lab)` | `r`: the result of the rule for this label over all CPUs of the session, or `None`. |
| 1168 | `            if r:` | Tests whether the result exists. |
| 1169 | `                words.append(f'{"Session " + e(s) + ", " if multi else ""}{"all CPUs together" if lab == "none" else "label " + lab + ", all CPUs together"}: <b>{e(r["decision"] + ab.sign_txt(r["sign"]))}</b>.')` | Then one text is added to `words`: the session (with several sessions), the label, the words "all CPUs together", and the word of the rule with its sign in bold. |
| 1170 | `    o.append('</table></div>')` | Closes the table. |
| 1171 | `    if words:` | Tests whether `words` has texts. |
| 1172 | `        o.append('<p class="cap">Result of the rule. ' + ' '.join(words) + '</p>')` | Then a caption is added: "Result of the rule" and the texts of `words`. |
| 1173 | `    return '\n'.join(o)` | Returns the table and the caption as one text. |
| 1176 | `def desc_takeaway(desc):` | Starts the function `desc_takeaway`. It writes the summary sentences of one description. |
| 1177 | `    pc = desc['per_cpu']` | `pc`: the values per CPU. |
| 1178 | `    recs = desc['recs']` | `recs`: the records of the processes. |
| 1179 | `    neg = sum(1 for r in recs if r['d'] < 0)` | `neg`: the count of processes with `d` below 0. |
| 1180 | `    pos = sum(1 for r in recs if r['d'] > 0)` | `pos`: the count of processes with `d` above 0. |
| 1181 | `    meds = [v['median_d'] for v in pc.values()]` | `meds`: the median `d` of each CPU. |
| 1182 | `    n_above = sum(1 for v in pc.values() if v['above'])` | `n_above`: the count of CPUs on which the absolute median `d` is larger than the A/A spread. |
| 1183 | `    n_both = sum(1 for v in pc.values() if v['above'] and v['one_sign'])` | `n_both`: the count of CPUs on which, in addition, all `d` have one sign. |
| 1184 | `    side = f'below 0 in {neg}' if neg >= pos else f'above 0 in {pos}'` | `side`: the text for the more frequent sign. With equal counts the side below 0 is named. |
| 1185 | `    t = (f'd is {side} of {pl(len(recs), "process", "processes")}. The median d of a CPU is between {fs(min(meds))} and {fs(max(meds))} GB/s. '` | Starts `t` with two sentences: in how many of the processes `d` lies on that side of 0, and between which two values the median `d` of a CPU lies, in GB/s. |
| 1186 | `         f'On {n_above} of {pl(len(pc), "CPU", "CPUs")} the absolute value of the median d is larger than the A/A spread.')` | Continues line 1185 with a third sentence: on how many of the CPUs the absolute median `d` is larger than the A/A spread. |
| 1187 | `    if n_above:` | Tests whether there is such a CPU. |
| 1188 | `        t += ' On those CPUs all d have one sign.' if n_both == n_above else f' On {n_both} of those CPUs all d have one sign.'` | Then a sentence is added: on those CPUs all `d` have one sign, or on how many of those CPUs. |
| 1189 | `    return t + order_words(desc)` | Returns the text with the sentences of `order_words` at its end. |
| 1192 | `def order_words(desc):` | Starts the function `order_words`. |
| 1193 | `    """Sentences if the order of the two loops inside a pair changes the pair value by more than the A/A spread."""` | Docstring: sentences that are added if the order of the two loops inside a pair changes the pair value by more than the A/A spread. |
| 1194 | `    pc = desc['per_cpu']` | `pc`: the values per CPU. |
| 1195 | `    big = [abs(v['d_first'] - v['d_second']) for v in pc.values() if abs(v['d_first'] - v['d_second']) > v['aa_spread']]` | `big`: for each CPU the absolute difference between `d_first` and `d_second`. Only a difference that is larger than the A/A spread of the CPU is kept. |
| 1196 | `    if not big:` | Tests whether no CPU has such a difference. |
| 1197 | `        return ''` | Then an empty text is returned. |
| 1198 | `    return (f' The order of the two loops inside a pair changes the pair value on {len(big)} of {pl(len(pc), "CPU", "CPUs")}. There the two orders differ by more than the A/A spread. '` | Starts the result with two sentences: on how many of the CPUs the order of the two loops inside a pair changes the pair value, and that the two orders differ there by more than the A/A spread. |
| 1199 | `            f'The largest difference is {fx(max(big))} GB/s.')` | Ends the result with the largest of these differences in GB/s. |
| 1202 | `def axis_of(descs):` | Starts the function `axis_of`. It finds the two ends of the axis for charts of `d` and `e`. |
| 1203 | `    v = [r[k] for d in descs for r in d['recs'] for k in ('d', 'e')] + [s * v2['aa_spread'] for d in descs for v2 in d['per_cpu'].values() for s in (1, -1)]` | `v`: every `d` and every `e` of all records of the given descriptions, and the A/A spread of every CPU with both signs. |
| 1204 | `    return min(v + [0]) - 0.1, max(v + [0]) + 0.1` | Returns the lowest of these values and 0, minus 0.1, and the highest of these values and 0, plus 0.1. So the axis always holds the value 0, and it extends 0.1 GB/s beyond the outermost value at each end. |

### Functions `group_block` and `proc_details` (lines 1207 to 1236)

| Line | Source | Explanation |
|---:|---|---|
| 1207 | `def group_block(D, R, step, key, title, dname, ename, labelled, res_of, heading='h3', marked=True):` | Starts the function `group_block`. It builds the block of one compared group: a heading, the legend, the chart, a summary and the table. `dname` and `ename` are the names of the two differences for the legend. `res_of` gives the groups of the step in the analysis result of a session. |
| 1208 | `    """One compared group (a size, a variant or a build) over all sessions: chart, takeaway, table. key None: step B6."""` | Docstring: one compared group (a size, a variant or a build) over all sessions: chart, takeaway, table. With `key` set to `None` the block is step B6. |
| 1209 | `    if key is None:` | Tests whether the block is step B6. |
| 1210 | `        items = [(n, D['sessions'][n]['b6'], D['sessions'][n]['res']['B6']['size']['labels']) for n in D['names'] if D['sessions'][n]['b6']]` | Then `items` gets one entry per session with B6 data: the session name, the description of B6, and the results of part 2 of the rule. |
| 1211 | `    else:` | The next line runs for every other step. |
| 1212 | `        items = [(n, D['sessions'][n]['pairs'][step][key], res_of(D['sessions'][n]).get(key, {}).get('labels')) for n in D['names'] if key in D['sessions'][n]['pairs'][step]]` | `items` gets one entry per session that has the group `key`: the session name, the description of the group, and the results of the rule for the group per label. |
| 1213 | `    if not items:` | Tests whether no session has the group. |
| 1214 | `        return ''` | Then an empty text is returned. |
| 1215 | `    o = [f'<{heading}>{e(title)}' + (' (the chart is a description, no decision)' if marked else '') + f'</{heading}>']` | `o`: the pieces of the block. The first piece is the heading with the title. With `marked` it also says that the chart is a description and no decision. |
| 1216 | `    o.append(legend_pairs(dname, ename))` | Adds the legend. |
| 1217 | `    o.append(dumbbell([(n, d) for n, d, _ in items], f'{step} {key}: d and e per process'))` | Adds the chart of `dumbbell` for all sessions. Its label for screen readers names the step, the group and the two values. |
| 1218 | `    o.append('<p class="take">' + ('Description, no decision. ' if marked else '')` | Starts the summary paragraph. With `marked` it starts with the words `Description, no decision.` |
| 1219 | `             + '<br>'.join((f'Session {e(n)}: ' if many(D) else '') + desc_takeaway(d) + ' ' + fref(R, D, n, step) for n, d, _ in items) + '</p>')` | Ends the paragraph: for each session the sentences of `desc_takeaway` and the citations of the result folders of the step. With several sessions the session name stands in front. |
| 1220 | `    o.append(pair_table(items, labelled))` | Adds the table of `pair_table`. |
| 1221 | `    return '\n'.join(o)` | Returns the block as one text. |
| 1224 | `def proc_details(D, step, groups_of, title):` | Starts the function `proc_details`. It builds a table with the values of every process of one step. The reader can unfold it. `groups_of` gives the described groups of a session. |
| 1225 | `    o = [f'<details><summary>{title}</summary><div class="tw"><table><tr>' + ('<th>Session</th>' if many(D) else '') + '<th>Group</th><th>Process</th><th>CPU</th><th>d, GB/s</th><th>e, GB/s</th><th>Pairs</th>'` | `o`: opens the folded block with its title and starts the header row of the table: the session (with several sessions), the group, the process, the CPU, `d` and `e` in GB/s, and the count of pairs. |
| 1226 | `         '<th>Reference rate, lowest to highest, GB/s</th><th>Stable label by the rule</th></tr>']` | Ends the header row: the lowest to highest reference rate in GB/s, and the stable label by the rule. |
| 1227 | `    for n in D['names']:` | Loop over the sessions. |
| 1228 | `        for k, g in groups_of(D['sessions'][n]):` | Loop over the groups of the session. |
| 1229 | `            for r in g['recs']:` | Loop over the records of the processes of the group. |
| 1230 | `                lab = (r['stable'] or 'not stable') if g.get('size', 8 * MIB) == 8 * MIB else 'no level defined at this size'` | `lab`: the text of the last column. For a group at 8 MiB it is the stable label of the process, or `not stable`. For another size it says that no level is defined at this size. A description without a size, as that of B6, counts as 8 MiB. |
| 1231 | `                o.append('<tr>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{e(k)}</td><td>{e(r['tag'])}</td><td>{r['cpu']}</td><td>{fs(r['d'], 3)}</td><td>{fs(r['e'], 3)}</td><td>{r['n_pairs']}</td>"` | Starts the table row: the session, the group, the tag, the CPU, `d` and `e` with their signs and 3 decimals, and the count of pairs. |
| 1232 | `                         f"<td>{fx(min(r['refs']))} to {fx(max(r['refs']))}</td><td>{lab}</td></tr>")` | Ends the table row: the lowest and the highest reference rate of the process, and `lab`. |
| 1233 | `    o.append('</table></div></details>')` | Closes the table and the folded block. |
| 1234 | `    return '\n'.join(o)` | Returns the block as one text. |

### Function `sec_b1`: the section of step B1 (lines 1237 to 1275)

| Line | Source | Explanation |
|---:|---|---|
| 1237 | `def sec_b1(D, R):` | Starts the function `sec_b1`. It builds the section of step B1: `copy` against `asmcopy` inside one process, at four buffer sizes. |
| 1238 | `    o = ['<h2 id="b1">B1: new C copy against asm copy inside one process</h2>']` | `o`: the pieces of the section. The first piece is the heading of B1 with the anchor `b1`. |
| 1239 | `    o.append('<p>Each process times new C copy, asm copy and a second copy of asm copy (asm copy 2) on the same two buffers, with reference intervals of asm read between the pairs ' + R('handoff') + '. '` | Adds the first paragraph. Its first sentence, typed, says what a process of B1 times: the two compared copy loops and the second copy of asm copy on the same two buffers, with reference intervals of asm read between the pairs. It cites the handoff note. |
| 1240 | `             'The loop of new C copy starts at 36 modulo 64 and the loop of asm copy at 52 modulo 64, as in the benchmark of 2026-11-13 ' + R('offsets') + '. '` | Continues line 1239 with typed text on the loop offsets of the two copy loops, 36 and 52. By the text these are the offsets of the benchmark of 2026-11-13. It cites the file of loop offsets. |
| 1241 | `             'The plan asks whether the difference of 2026-11-13 exists inside one process. In that run new C copy was 2.91 % below asm copy at 8 MiB, with the two loops in different processes ' + R('plan') + '.</p>')` | Ends the paragraph with typed text: the plan asks whether the difference of 2026-11-13 exists inside one process. The sentence gives the size of that difference as a typed percentage and says that the two loops ran in different processes then, with a citation of the plan. |
| 1242 | `    have = [n for n in D['names'] if D['sessions'][n]['pairs']['B1']]` | `have`: the sessions that have data of B1. |
| 1243 | `    for n in D['names']:` | Loop over the sessions. |
| 1244 | `        if n not in have:` | Tests whether the session has no data of B1. |
| 1245 | `            o.append(miss(f'Step B1{" of session " + e(n) if many(D) else ""}: no process is in the input. A run of step B1 would give it.'))` | Then a block "Insufficient data" is added: no process of step B1 is in the input, and a run of step B1 would give it. |
| 1246 | `    if not have:` | Tests whether no session has data of B1. |
| 1247 | `        return '\n'.join(o)` | Then the section ends here. |
| 1248 | `    res_of = lambda x: x['res'].get('B1', {}).get('groups', {})` | `res_of`: a small function that gives the groups of B1 in the analysis result of a session. |
| 1249 | `    sizes = sorted({(g['size'], k) for n in have for k, g in D['sessions'][n]['pairs']['B1'].items()})` | `sizes`: the pairs of buffer size in bytes and group key of all groups of B1, over the sessions, each once, in rising order. |
| 1250 | `    dn, en = 'new C copy minus asm copy', 'asm copy 2 minus asm copy'` | `dn` and `en`: the names of the two differences for the legend: new C copy minus asm copy, and asm copy 2 minus asm copy. |
| 1251 | `    if any(s == 8 * MIB for s, _ in sizes):` | Tests whether a group at 8 MiB exists. |
| 1252 | `        o.append(group_block(D, R, 'B1', '8M', '8 MiB', dn, en, True, res_of))` | Then the block of the group `8M` is added, with the title `8 MiB` and with the rule columns per label. |
| 1253 | `        recs = [r for n in have for r in D['sessions'][n]['pairs']['B1'].get('8M', {}).get('recs', [])]` | `recs`: the records of all processes at 8 MiB, over the sessions. |
| 1254 | `        n_st = sum(1 for r in recs if r['stable'])` | `n_st`: how many of them are stable. |
| 1255 | `        o.append(f'<p>At 8 MiB the rule uses only a process whose reference intervals are all low or all high. The rule can use {n_st} of the {pl(len(recs), "process", "processes")}. '` | Starts a paragraph: at 8 MiB the rule uses only a process whose reference intervals are all low or all high. Then it gives how many of the processes the rule can use. |
| 1256 | `                 'The other processes are in the chart and in the description columns, and in no decision. ' + stable_sentence(D) + '</p>')` | Ends the paragraph: the other processes are in the chart and in the description columns, and in no decision. The sentences of `stable_sentence` follow. |
| 1257 | `    rest = [(s, k) for s, k in sizes if s != 8 * MIB]` | `rest`: the pairs of `sizes` for all other buffer sizes. |
| 1258 | `    if rest:` | The next lines run when another size exists. |
| 1259 | `        o.append('<h3>4, 16 and 32 MiB: sizes without a level</h3>' if [s // MIB for s, _ in rest] == [4, 16, 32] else '<h3>The other sizes: no level is defined</h3>')` | Adds a heading. It names the sizes 4, 16 and 32 MiB when exactly these three exist. For any other set of sizes it speaks of the other sizes in general. Both forms say that no level is defined there. |
| 1260 | `        o.append('<div class="tw"><table class="c"><tr><th>Size</th>' + ('<th>Session</th>' if many(D) else '') + '<th>Processes</th><th>Median d per CPU, GB/s</th><th>Median d per CPU, % of asm copy</th><th>Largest A/A spread of a CPU, GB/s</th><th>Rule: word over the CPUs</th></tr>')` | Opens a table and its header row: the size, the session (with several sessions), the count of processes, the median `d` per CPU in GB/s and in percent of asm copy, the largest A/A spread of a CPU in GB/s, and the word of the rule over the CPUs. |
| 1261 | `        for s, k in rest:` | Loop over the other sizes. |
| 1262 | `            for n in have:` | Loop over the sessions with data of B1. |
| 1263 | `                g = D['sessions'][n]['pairs']['B1'].get(k)` | `g`: the description of the group of this size in the session, or `None`. |
| 1264 | `                if not g:` | Tests whether it is missing. |
| 1265 | `                    continue` | Then the session gets no row for this size. |
| 1266 | `                pc = g['per_cpu'].values()` | `pc`: the values per CPU of the group. |
| 1267 | `                r = res_of(D['sessions'][n]).get(k, {}).get('labels', {}).get('none')` | `r`: the result of the rule for this group under the label `none`, or `None`. |
| 1268 | `                o.append(f'<tr><td>{s // MIB} MiB</td>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{len(g['recs'])}</td><td class=\"nw\">{rng(min(v['median_d'] for v in pc), max(v['median_d'] for v in pc), signed=True)}</td>"` | Starts the table row: the size in MiB, the session, the count of processes, and the range of the median `d` over the CPUs with its sign. |
| 1269 | `                         f"<td class=\"nw\">{rng(min(v['pct'] for v in pc), max(v['pct'] for v in pc), signed=True)}</td><td>{fx(max(v['aa_spread'] for v in pc))}</td><td class=\"l\">{e(r['decision'] + ab.sign_txt(r['sign'])) if r else '-'}</td></tr>")` | Ends the table row: the range of `pct` over the CPUs, the largest A/A spread of a CPU, and the word of the rule with its sign. Without a result the last cell holds `-`. |
| 1270 | `        o.append('</table></div><p class="cap">At these sizes the rule uses every process. ' + frefs(R, D, 'B1') + '</p>')` | Closes the table and adds a caption: at these sizes the rule uses every process, with the citations of the result folders of B1. |
| 1271 | `        o.append('<details><summary>Charts and tables per CPU for these sizes</summary>' + ''.join(group_block(D, R, 'B1', k, f'{s // MIB} MiB', dn, en, False, res_of, heading='h4', marked=False) for s, k in rest) + '</details>')` | Adds a folded block with one `group_block` per other size: the chart and the table per CPU, with a heading of level 4, without the description mark, and with one rule column for the label `none`. |
| 1272 | `    o.append(proc_details(D, 'B1', lambda x: sorted(x['pairs']['B1'].items(), key=lambda kv: kv[1]['size']), 'Values of every process of B1'))` | Adds the folded table of `proc_details` for B1, with the groups in the order of their sizes. |
| 1273 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `sec_variants`: the section of step B2 or step B3 (lines 1276 to 1355)

| Line | Source | Explanation |
|---:|---|---|
| 1276 | `def sec_variants(D, R, step, title, intro, dname_of, gname):` | Starts the function `sec_variants`. It builds the section of step B2 (three assembly variants) or of step B3 (three builds with both copy loops at one loop offset). `title` and `intro` are the heading and the first paragraph. `dname_of` gives the name of the difference `d` of a group. `gname` gives the name of a group. |
| 1277 | `    o = [f'<h2 id="{step.lower()}">{title}</h2>', intro]` | `o`: the pieces of the section. The first two are the heading, with the step in small letters as its anchor, and the text `intro`. |
| 1278 | `    have = [n for n in D['names'] if D['sessions'][n]['pairs'][step]]` | `have`: the sessions that have data of the step. |
| 1279 | `    for n in D['names']:` | Loop over the sessions. |
| 1280 | `        if n not in have:` | Tests whether the session has no data of the step. |
| 1281 | `            o.append(miss(f'Step {step}{" of session " + e(n) if many(D) else ""}: no process is in the input. A run of step {step} would give it.'))` | Then a block "Insufficient data" is added: no process of the step is in the input, and a run of the step would give it. |
| 1282 | `    if not have:` | Tests whether no session has data of the step. |
| 1283 | `        return '\n'.join(o)` | Then the section ends here. |
| 1284 | `    keys = sorted({k for n in have for k in D['sessions'][n]['pairs'][step]})` | `keys`: the group keys of the step over the sessions, each once, in sorted order. For B2 these are the variants, for B3 the names of the builds. |
| 1285 | `    res_of = lambda x: x['res'].get(step, {}).get('groups', {})` | `res_of`: a small function that gives the groups of the step in the analysis result of a session. |
| 1286 | `    # summary chart: every process value of every group, with B1 at 8 MiB as the first block` | Comment: the summary chart follows. It shows every process value of every group, with B1 at 8 MiB as the first block. |
| 1287 | `    blocks = [('B1: new C copy', lambda x: x['pairs']['B1'].get('8M'))] + [(gname(k), (lambda k: lambda x: x['pairs'][step].get(k))(k)) for k in keys]` | `blocks`: a list of pairs of a name and a small function that takes the description of one group out of the values of a session. The first block is B1 at 8 MiB. One block per key of the step follows. The two nested `lambda` forms give each function its own value of `k`. |
| 1288 | `    rows, groups, descs = [], set(), []` | Three empty values: `rows` (the chart rows), `groups` (the row numbers that end a block) and `descs` (the descriptions, for the axis). |
| 1289 | `    for bname, get in blocks:` | Loop over the blocks. |
| 1290 | `        cpus = sorted({c for n in have for g in [get(D['sessions'][n])] if g for c in g['per_cpu']})` | `cpus`: the CPUs of the block, over the sessions that have it, in rising order. |
| 1291 | `        for c in cpus:` | Loop over these CPUs. |
| 1292 | `            for n in have:` | Loop over the sessions. |
| 1293 | `                g = get(D['sessions'][n])` | `g`: the description of the block in this session, or `None`. |
| 1294 | `                if not g or c not in g['per_cpu']:` | Tests whether it is missing or lacks this CPU. |
| 1295 | `                    continue` | Then no chart row is made. |
| 1296 | `                descs.append(g)` | Appends the description to `descs`. |
| 1297 | `                v = g['per_cpu'][c]` | `v`: the values of the CPU. |
| 1298 | `                pts = [(r['e'], f'{r["tag"]}: e {fs(r["e"], 3)} GB/s', 1) for r in g['recs'] if r['cpu'] == c] + [(r['d'], f'{r["tag"]}: d {fs(r["d"], 3)} GB/s', 0) for r in g['recs'] if r['cpu'] == c]` | `pts`: the markers of the chart row: one diamond for the `e` of every process of the CPU, and one dot for its `d`. Each tooltip gives the tag and the value with its sign and 3 decimals, in GB/s. |
| 1299 | `                rows.append((f'{bname}, CPU {c}' + (f', {n}' if many(D) else ''), pts, f'{fs(v["median_d"])} GB/s, A/A {fx(v["aa_spread"])} GB/s'))` | Appends the chart row: the name of the block and the CPU, with the session when several are shown, the markers, and the text for the right side: the median `d` with its sign and the A/A spread, in GB/s. |
| 1300 | `        groups.add(len(rows))` | After the rows of a block, the number of its last row goes to `groups`. `strip` draws a heavy line there. |
| 1301 | `    xmin, xmax = axis_of(descs)` | `xmin` and `xmax`: the two ends of the axis, from `axis_of`. |
| 1302 | `    o.append(f'<h3>All process values of {step}, next to B1 at 8 MiB (description, no decision)</h3>')` | Adds a heading: all process values of the step, next to B1 at 8 MiB, with the mark that this is a description and no decision. |
| 1303 | `    o.append(f'<p><span class="lg"><i style="background:{C0}"></i>d of one process: the named loop minus asm copy</span>'` | Adds the legend. This line: a blue circle for `d` of one process, the named loop minus asm copy. |
| 1304 | `             f'<span class="lg"><i style="background:{C1c};border-radius:0;transform:rotate(45deg)"></i>e of one process: asm copy 2 minus asm copy</span></p>')` | Continues line 1303: an orange diamond for `e` of one process, asm copy 2 minus asm copy. |
| 1305 | `    o.append(strip(rows, xmin, xmax, 'difference of the rates of two neighbouring intervals, GB/s (one value per process)', f'{step}: d and e of every process per group, CPU and session',` | Adds the chart of `strip`. The title of its axis: the difference of the rates of two neighbouring intervals in GB/s, one value per process. The label for screen readers names the step and the two values. |
| 1306 | `                   L=250, R=220, groups=groups, right_head='median d, A/A spread', zero=True))` | Continues line 1305 with the options: a left margin of 250 units, a right margin of 220 units, the heavy lines of `groups`, the heading of the right column, and a dashed line at 0. |
| 1307 | `    # one table row per group and session` | Comment: a table with one row per group and session follows. |
| 1308 | `    o.append('<div class="tw"><table class="c"><tr><th>Group</th>' + ('<th>Session</th>' if many(D) else '') + '<th>Processes with d below 0</th><th>Median d per CPU, GB/s</th>'` | Opens the table and starts its header row: the group, the session (with several sessions), the count of processes with `d` below 0, and the median `d` per CPU in GB/s. |
| 1309 | `             '<th>CPUs with \|median d\| above the A/A spread and one sign</th><th>Stable low processes (labels not validated)</th><th>Rule, label low: word over the CPUs</th></tr>')` | Ends the header row: the count of CPUs with an absolute median `d` above the A/A spread and one sign, the count of stable low processes (with the remark that the labels are not validated), and the word of the rule for the label low over the CPUs. |
| 1310 | `    for k in keys:` | Loop over the groups. |
| 1311 | `        for n in have:` | Loop over the sessions. |
| 1312 | `            g = D['sessions'][n]['pairs'][step].get(k)` | `g`: the description of the group in this session, or `None`. |
| 1313 | `            if not g:` | Tests whether it is missing. |
| 1314 | `                continue` | Then no table row is made. |
| 1315 | `            pc = g['per_cpu'].values()` | `pc`: the values per CPU of the group. |
| 1316 | `            r = res_of(D['sessions'][n]).get(k, {}).get('labels', {}).get('low')` | `r`: the result of the rule for this group at the label low, or `None`. |
| 1317 | `            o.append(f'<tr><td>{e(gname(k))}</td>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{sum(1 for q in g['recs'] if q['d'] < 0)} of {len(g['recs'])}</td>"` | Starts the table row: the name of the group, the session, and in how many of all processes of the group `d` is below 0. |
| 1318 | `                     f"<td class=\"nw\">{rng(min(v['median_d'] for v in pc), max(v['median_d'] for v in pc), signed=True)}</td><td>{sum(1 for v in pc if v['above'] and v['one_sign'])} of {len(g['per_cpu'])}</td>"` | Continues line 1317: the range of the median `d` over the CPUs with its sign, and on how many of the CPUs `above` and `one_sign` are both true (lines 230 to 231). |
| 1319 | `                     f"<td>{sum(v['n_low'] for v in pc)} of {len(g['recs'])}</td><td class=\"l\">{e(r['decision'] + ab.sign_txt(r['sign'])) if r else '-'}</td></tr>")` | Ends the table row: how many of the processes are stable low, and the word of the rule with its sign. Without a result the last cell holds `-`. |
| 1320 | `    o.append('</table></div>')` | Closes the table. |
| 1321 | `    o.append('<p class="cap">One dot or diamond is one process. The dashed line is 0. The first block repeats B1 at 8 MiB for comparison. All columns before "Stable low processes" are a description. ' + frefs(R, D, step, 'B1') + '</p>')` | Adds the caption of the chart and of the table: what a marker and the dashed line are, why the first block repeats B1 at 8 MiB, and which columns are a description. The citations of the result folders of the step and of B1 follow. |
| 1322 | `    # comparison with B1 at 8 MiB, description` | Comment: a comparison with B1 at 8 MiB follows, as a description. |
| 1323 | `    n_all = n_big = 0` | Two counts start at 0: `n_all` (all rows of the comparison) and `n_big` (the rows with a large difference). |
| 1324 | `    tb = ['<div class="tw"><table><tr><th>Group</th>' + ('<th>Session</th>' if many(D) else '') + '<th>CPU</th><th>Median d of B1, GB/s</th><th>Median d of the group, GB/s</th><th>B1 minus group, GB/s</th>'` | Starts `tb`, the table of the comparison. This line opens it and holds the first column titles: the group, the session (with several sessions), the CPU, the median `d` of B1, the median `d` of the group, and B1 minus group, all in GB/s. |
| 1325 | `          '<th>Sum of the two A/A spreads, GB/s</th><th>Difference above that sum</th><th>The d of B1 and of the group do not overlap</th></tr>']` | Continues line 1324 with the last titles: the sum of the two A/A spreads in GB/s, whether the difference is above that sum, and whether the `d` values of B1 and of the group do not overlap. |
| 1326 | `    strict = set()` | `strict`: the words of the rule for the change against B1, as a set, empty at the start. |
| 1327 | `    for n in have:` | Loop over the sessions with data of the step. |
| 1328 | `        x = D['sessions'][n]` | `x`: the values of the session. |
| 1329 | `        base = x['pairs']['B1'].get('8M')` | `base`: the description of B1 at 8 MiB in this session, or `None`. |
| 1330 | `        for k in keys:` | Loop over the groups. |
| 1331 | `            g = x['pairs'][step].get(k)` | `g`: the description of the group, or `None`. |
| 1332 | `            if not base or not g:` | Tests whether B1 or the group is missing. |
| 1333 | `                continue` | Then the group gives no row in this session. |
| 1334 | `            for c, v in g['per_cpu'].items():` | Loop over the CPUs of the group. |
| 1335 | `                b = base['per_cpu'].get(c)` | `b`: the values of B1 for the same CPU, or `None`. |
| 1336 | `                if not b:` | Tests whether B1 has no process on this CPU. |
| 1337 | `                    continue` | Then the CPU gives no row. |
| 1338 | `                ch, sp = b['median_d'] - v['median_d'], b['aa_spread'] + v['aa_spread']` | `ch`: the median `d` of B1 minus the median `d` of the group, in GB/s. `sp`: the A/A spread of B1 plus the A/A spread of the group. Both use all processes of the CPU, stable or not. |
| 1339 | `                sep = max(b['d']) < min(v['d']) or min(b['d']) > max(v['d'])` | `sep`: true when the `d` values of B1 and of the group do not overlap: every `d` of one lies below every `d` of the other. |
| 1340 | `                n_all += 1` | Counts the row. |
| 1341 | `                n_big += abs(ch) > sp and sep` | Adds 1 to `n_big` when the absolute value of `ch` is larger than `sp` and `sep` is true. |
| 1342 | `                tb.append(f'<tr><td>{e(gname(k))}</td>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{c}</td><td>{fs(b['median_d'])}</td><td>{fs(v['median_d'])}</td><td>{fs(ch)}</td><td>{fx(sp)}</td><td>{yn(abs(ch) > sp)}</td><td>{yn(sep)}</td></tr>")` | Appends the table row: the group, the session, the CPU, the two medians and `ch` with their signs, `sp`, and the words yes or no for the two tests. |
| 1343 | `        chg = x['res'].get(step, {}).get('change_against_B1')` | `chg`: the part `change_against_B1` of the analysis result of the step. The analysis makes it for step B3 only. |
| 1344 | `        if chg:` | Tests whether it exists. |
| 1345 | `            strict \|= {v['decision'] for b in chg.values() for v in b.values()}` | Then the decision words of all builds, labels and CPUs in it are added to `strict`. |
| 1346 | `    if n_all:` | The next lines run when the comparison has rows. |
| 1347 | `        o.append(f'<p class="take">Description, no decision. In {n_big} of {pl(n_all, "row", "rows")} (one row per group, CPU and session) the median d differs from B1 at 8 MiB by more than the sum of the two A/A spreads, with no overlap of the process values.'` | Adds a highlighted paragraph that starts with the words `Description, no decision.` It gives in how many of the rows the median `d` differs from B1 at 8 MiB by more than the sum of the two A/A spreads, with no overlap of the process values. One row is one group, CPU and session. |
| 1348 | `                 + (' Strict result of the rule for the change against B1, per build, label and CPU: ' + ', '.join(f'"{w}"' for w in sorted(strict)) + '. The rule compares only stable processes with one label, and needs 3 of them on a CPU in B1 and in the build ' + R('devscripts') + '.' if strict else '') + '</p>')` | Continues line 1347 when `strict` has words: the strict result of the rule for the change against B1, as the list of these words. A typed sentence follows: the rule compares only stable processes with one label, and needs 3 of them on a CPU in B1 and in the build, with a citation of the note on the deviations. |
| 1349 | `        o.append(f'<details><summary>Median d of {step} next to B1 at 8 MiB, per CPU</summary>' + ''.join(tb) + '</table></div></details>')` | Adds the table `tb` in a folded block with a title that names the step. |
| 1350 | `    o.append(f'<details><summary>Chart and table per CPU for each group of {step}</summary>'` | Starts a folded block with a chart and a table per CPU for each group of the step. |
| 1351 | `             + ''.join(group_block(D, R, step, k, gname(k), dname_of(k), 'asm copy 2 minus asm copy', True, res_of, heading='h4') for k in keys) + '</details>')` | Ends the block: one `group_block` per group, with the label columns of the rule, a heading of level 4 and the description mark. |
| 1352 | `    o.append(proc_details(D, step, lambda x: sorted(x['pairs'][step].items()), f'Values of every process of {step}'))` | Adds the folded table of `proc_details` for the step, with the groups in the order of their names. |
| 1353 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `proc_table`: one table row per process of step B4 (lines 1356 to 1370)

| Line | Source | Explanation |
|---:|---|---|
| 1356 | `def proc_table(D, key):` | Starts the function `proc_table`. `key` names the list of process records, `b4` or `c1`. This file calls it for `b4` only (line 1461). |
| 1357 | `    """B4 or C1: one row per process, all sessions."""` | Docstring: step B4 or C1: one row per process, over all sessions. |
| 1358 | `    o = ['<div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if many(D) else '') + '<th>Process</th><th>CPU</th><th>Pages asked</th><th>Started, UTC</th><th>Median, GB/s</th><th>Lowest to highest, GB/s</th><th>Intervals low / between / high</th>'` | Opens the table and starts its header row: the session (with several sessions), the process, the CPU, the pages asked, the UTC time of the start, the median rate in GB/s, the lowest to highest rate, and the counts of intervals low, between and high. |
| 1359 | `         '<th>Intervals with full / partial / no coverage</th><th>Counter increases, collapse / migrate</th><th>Changes low to high or back</th><th>Largest step between neighbours, GB/s</th></tr>']` | Ends the header row: the counts of intervals with full, partial and no coverage, the counter increases of the two counters, the count of changes from low to high or back, and the largest step between neighbours in GB/s. |
| 1360 | `    for n in D['names']:` | Loop over the sessions. |
| 1361 | `        for p in D['sessions'][n][key]:` | Loop over the process records of the session (lines 281 to 284). |
| 1362 | `            o.append('<tr>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{e(p['tag'])}</td><td>{p['cpu']}</td><td>{'4 KiB' if p['no_thp'] else '2 MiB'}</td><td>{e(p['utc'])}</td><td>{fx(p['median'])}</td><td class=\"nw\">{fx(p['min'])} to {fx(p['max'])}</td>"` | Starts the table row: the session, the tag, the CPU, `4 KiB` for a process with `--no-thp` and `2 MiB` for any other, the UTC time of the header line, the median rate, and the lowest to highest rate. |
| 1363 | `                     f"<td class=\"nw\">{p['levels']['low']} / {p['levels']['between']} / {p['levels']['high']}</td><td class=\"nw\">{p['cov']['full']} / {p['cov']['partial']} / {p['cov']['none']}</td>"` | Continues line 1362: the three level counts, and the three coverage counts. |
| 1364 | `                     f"<td>{len(p['events']['thp_collapse_alloc'])} / {len(p['events']['pgmigrate_success'])}</td><td>{len(p['changes'])}</td><td class=\"nw\">{s2(p['step_size'])}{'' if p['step_at'] is None else ' into interval %d' % p['step_at']}</td></tr>")` | Ends the table row: the counts of intervals before which each of the two counters rose, the count of level changes, and the largest step with its sign and the number of the interval into which it leads. |
| 1365 | `    o.append('</table></div>')` | Closes the table. |
| 1366 | `    o.append('<p class="cap">Intervals are numbered from 0. "Counter increases" counts the intervals before which <code>thp_collapse_alloc</code> or <code>pgmigrate_success</code> was higher than at the reading before. '` | Starts the caption: it says that intervals are numbered from 0, and defines the column of counter increases as the count of intervals before which one of the two counters was higher than at the reading before. |
| 1367 | `             '"Largest step" is the largest absolute difference between two neighbouring intervals, with the number of the later interval.</p>')` | Ends the caption with the definition of the largest step: the largest absolute difference between two neighbouring intervals, given with the number of the later interval. |
| 1368 | `    return '\n'.join(o)` | Returns the table and the caption as one text. |

### Function `sec_b4`: the section of step B4 (lines 1371 to 1464)

| Line | Source | Explanation |
|---:|---|---|
| 1371 | `def sec_b4(D, R):` | Starts the function `sec_b4`. It builds the section of step B4: 200 intervals of `asmread` on one buffer of 8 MiB, with the page state before every interval. |
| 1372 | `    o = ['<h2 id="b4">B4: 200 intervals of asm read on one buffer, with the page state</h2>']` | `o`: the pieces of the section. The first piece is the heading of B4 with the anchor `b4`. |
| 1373 | `    o.append('<p>One process maps one 8 MiB buffer and times asm read 200 times. Before every interval it reads the huge-page coverage of the buffer (<code>kB_huge</code> of <code>kB_total</code>) and four counters of <code>/proc/vmstat</code> ' + R('handoff') + '. '` | Adds the first paragraph, typed text. Its first two sentences say what a process of B4 does: 200 timed intervals of asm read on one buffer of 8 MiB, and before every interval a reading of the huge-page coverage (`kB_huge` of `kB_total`) and of four counters of `/proc/vmstat`. They cite the handoff note. |
| 1374 | `             'Half of the processes ask for 4 KiB pages with <code>--no-thp</code>. Each interval is its own reference: its label comes from its own rate. '` | Continues line 1373 with two points: half of the processes run with `--no-thp`, and in this step each interval gets its label from its own rate. |
| 1375 | `             'H3a predicts that every low interval has less than full coverage and every high interval has full coverage ' + R('plan') + '.</p>')` | Ends the paragraph with the bounded prediction of H3a for this step, and a citation of the plan. |
| 1376 | `    have = [n for n in D['names'] if D['sessions'][n]['b4']]` | `have`: the sessions that have data of B4. |
| 1377 | `    for n in D['names']:` | Loop over the sessions. |
| 1378 | `        if n not in have:` | Tests whether the session has no data of B4. |
| 1379 | `            o.append(miss(f'Step B4{" of session " + e(n) if many(D) else ""}: no process is in the input. A run of step B4 would give it.'))` | Then a block "Insufficient data" is added: no process of step B4 is in the input, and a run of step B4 would give it. |
| 1380 | `    if not have:` | Tests whether no session has data of B4. |
| 1381 | `        return '\n'.join(o)` | Then the section ends here. |
| 1382 | `    allr = [v for n in have for p in D['sessions'][n]['b4'] for v in p['rates']]` | `allr`: the rates of all intervals of all B4 processes, over the sessions. |
| 1383 | `    ymin, ymax = axis_floor(min(min(allr), LOW) - 0.3), math.ceil((max(max(allr), HIGH) + 0.5) * 2) / 2` | `ymin` and `ymax`: the two ends of the rate axis of all panels. The start lies 0.3 GB/s below the lower one of the lowest rate and `LOW`, rounded down to a multiple of 0.5. The end lies 0.5 GB/s above the higher one of the highest rate and `HIGH`, rounded up to a multiple of 0.5. |
| 1384 | `    o.append(f'<p><span class="lg"><i style="background:{C0}"></i>rate of one interval</span><span class="lg"><i style="background:{RED};border-radius:0;width:3px"></i>thp_collapse_alloc rose before the interval</span>'` | Adds the legend. This line: a blue circle for the rate of one interval, and a red bar for an interval before which `thp_collapse_alloc` rose. |
| 1385 | `             f'<span class="lg"><i style="background:#7a3fb5;border-radius:0;width:3px"></i>pgmigrate_success rose before the interval</span><span class="lg"><i style="background:{BAND};border-radius:0"></i>between the two limits ({LOW:g} and {HIGH:g} GB/s)</span></p>')` | Continues line 1384: a purple bar for an interval before which `pgmigrate_success` rose, and a shaded square for the range between the two limits, with their values in GB/s. |
| 1386 | `    takes, lost, case_txt, h3b = [], [], [], []` | Four empty lists: `takes` (summaries), `lost` (value labels without a place), `case_txt` (texts on the cases) and `h3b` (texts for H3b). |
| 1387 | `    for n in have:` | Loop over the sessions with data of B4. |
| 1388 | `        x = D['sessions'][n]` | `x`: the values of the session. |
| 1389 | `        P = x['b4']` | `P`: the process records of B4. |
| 1390 | `        if many(D):` | Tests whether several sessions are shown. |
| 1391 | `            o.append(f'<h3>Session {e(n)}</h3>')` | Then a heading with the session name is added. |
| 1392 | `        chart, left_out = seq_chart(P, ymin, ymax, 'B4: rate against interval number for each process')` | `chart`: the drawing of `seq_chart` for these processes. `left_out`: its list of value labels without a place. |
| 1393 | `        o.append(chart)` | Adds the drawing. |
| 1394 | `        lost += [(n, t, i, v) for t, i, v in left_out]` | Adds the entries of `left_out` to `lost`, each with the session name. |
| 1395 | `        nev = sum(len(p['events'][k]) for p in P for k in p['events'])` | `nev`: the count of intervals before which one of the two counters rose, over all processes of the session. |
| 1396 | `        nch = sum(len(p['changes']) for p in P)` | `nch`: the count of level changes inside a process, over all processes of the session. |
| 1397 | `        full = [p for p in P if p['cov']['full'] == len(p['rates'])]` | `full`: the processes that had full huge-page coverage before every interval. |
| 1398 | `        none = [p for p in P if p['cov']['none'] == len(p['rates'])]` | `none`: the processes that had no huge page before every interval. |
| 1399 | `        t = f'{"Session " + e(n) + ". " if many(D) else ""}{pl(len(full), "process", "processes")} had full huge-page coverage before every interval, and {pl(len(none), "process", "processes")} had none before every interval. '` | Starts the summary `t` of the session: how many processes had full coverage before every interval, and how many had none before every interval. |
| 1400 | `        if full:` | Tests whether a process had full coverage throughout. |
| 1401 | `            t += f'The median rates of the processes with full coverage are between {fx(min(p["median"] for p in full))} and {fx(max(p["median"] for p in full))} GB/s. '` | Then a sentence is added: the lowest and the highest median rate of these processes, in GB/s. |
| 1402 | `        if none:` | Tests whether a process had no huge page throughout. |
| 1403 | `            t += f'The median rates of the processes with no huge page are between {fx(min(p["median"] for p in none))} and {fx(max(p["median"] for p in none))} GB/s. '` | Then the same sentence is added for those processes. |
| 1404 | `        t += f'The two vmstat counters rose before {pl(nev, "interval", "intervals")}. {pl(nch, "change", "changes")} between low and high occurred inside a process. '` | Adds two sentences: before how many intervals the two counters rose, and how many changes between low and high occurred inside a process. |
| 1405 | `        big = [p for p in P if p['step_size'] is not None and abs(p['step_size']) > 1]` | `big`: the processes whose largest step between two neighbouring intervals is above 1 GB/s in absolute value. |
| 1406 | `        if big:` | The next lines run when there is such a process. |
| 1407 | `            up = sum(1 for p in big if p['step_size'] > 0)` | `up`: how many of these largest steps go upward. |
| 1408 | `            t += (f'Description, no decision: in {len(big)} of {pl(len(P), "process", "processes")} the largest step between two neighbouring intervals is above 1 GB/s. {up} of these steps {"goes" if up == 1 else "go"} upward. '` | Adds two sentences, with the mark `Description, no decision`: in how many of the processes the largest step is above 1 GB/s, and how many of these steps go upward. |
| 1409 | `                  f'All of them occur within the first {max(p["step_at"] for p in big) + 1} intervals of a process. After its largest step, the rate of such a process stays within {fx(max(p["after_max"] - p["after_min"] for p in big))} GB/s. ')` | Adds two sentences. All these steps occur within the first intervals of a process. The count that the sentence gives is the highest interval number of such a step plus 1. After its largest step, the rate of such a process stays within a range. The range that the sentence gives is the largest difference between the highest and the lowest rate after the step, over these processes. |
| 1410 | `        takes.append(t + fref(R, D, n, 'B4'))` | Appends the summary to `takes`, with the citations of the result folders of B4. |
| 1411 | `        pc = x['res'].get('B4', {}).get('per_cpu', {})` | `pc`: the result of B4 per CPU from the analysis. |
| 1412 | `        pre = f'Session {e(n)}. ' if many(D) else ''` | `pre`: the session name as the start of a sentence, when several sessions are shown. |
| 1413 | `        cases = [(c, v['cases']) for c, v in pc.items() if v['cases']]` | `cases`: the CPUs with a case, each with its cases. |
| 1414 | `        if not cases:` | Tests whether no CPU has a case. |
| 1415 | `            case_txt.append(pre + 'Neither case occurred on a CPU. The result of this session for H3a is "not observed".')` | Then a text goes to `case_txt`: neither case occurred on a CPU, and the result of this session for H3a is "not observed". |
| 1416 | `        for c, cs in cases:` | Loop over the CPUs with a case. |
| 1417 | `            t = pre + f'On CPU {c}, case ({") and (".join(cs)}) occurred by the rule. '` | Starts the text `t` of the CPU: on this CPU the named cases occurred by the rule. |
| 1418 | `            f = x['b4_cases'].get(c)` | `f`: the facts of `b4_case_facts` for the CPU, or `None`. They exist for a CPU with case (a). |
| 1419 | `            if f:` | The next lines run when the facts exist. |
| 1420 | `                t += (f'{pl(f["n_lo_procs"], "process has", "processes have")} at least 10 low intervals with full coverage, and {pl(f["n_hi_procs"], "process has", "processes have")} at least 10 high ones. '` | Adds a sentence: how many processes have at least 10 low intervals with full coverage, and how many have at least 10 high ones. |
| 1421 | `                      + ('At least one process has at least 10 of each. ' if f['both'] else 'No process has both: the level differs between processes, not inside one. '))` | Adds one of two sentences: at least one process has at least 10 of each. Or: no process has both, so the level differs between processes and not inside one. |
| 1422 | `                t += f'The low intervals with full coverage are between {fx(f["low_min"])} and {fx(f["low_max"])} GB/s. The high ones are between {fx(f["high_min"])} and {fx(f["high_max"])} GB/s. '` | Adds two sentences: between which rates the low intervals with full coverage lie, and between which rates the high ones lie, in GB/s. |
| 1423 | `                if f['label_dependent']:` | Tests whether the case depends on the limits (line 366). |
| 1424 | `                    t += (f'<b>This case depends on the provisional limits.</b> {f["near_lo"]} of the {f["n_low"]} low intervals lie less than {NEAR:g} GB/s below the limit of {LOW:g} GB/s. '` | Then a sentence in bold says so. The next sentence gives how many of the low intervals lie less than 0.2 GB/s below the limit of 69 GB/s. It names the low side only, also when the high side made the case depend on the limits. |
| 1425 | `                          'So this page does not state that the bounded prediction failed on this CPU before the limits are decided. Description without labels: ')` | Continues line 1424: so the generated page does not state that the bounded prediction failed on this CPU before the limits are decided. The words `Description without labels:` start the next sentences. |
| 1426 | `                    for p in f['both']:` | Loop over the processes that have at least 10 low and at least 10 high intervals with full coverage. |
| 1427 | `                        for ch in p['change_info']:` | Loop over the level changes of the process. |
| 1428 | `                            a, b = p['rates'][:ch['frm'] + 1], p['rates'][ch['to']:]` | `a`: the rates from interval 0 to the last interval before the change. `b`: the rates from the first interval after the change to the end. |
| 1429 | `                            t += (f'with full coverage in all intervals and {pl(sum(len(v) for v in p["events"].values()), "increase", "increases")} of the two vmstat counters, the rate of process {e(p["tag"])} '` | Starts a sentence: with full coverage in all intervals and the count of increases of the two counters, the rate of this process changed. The words on full coverage in all intervals are typed. The code tests only the 10 low and the 10 high intervals of lines 359 to 360. |
| 1430 | `                                  f'went from a median of {fx(median(a))} GB/s (intervals 0 to {ch["frm"]}) to a median of {fx(median(b))} GB/s (intervals {ch["to"]} to {len(p["rates"]) - 1}). ')` | Ends the sentence: the rate went from the median of `a`, with its interval numbers, to the median of `b`, with its interval numbers, in GB/s. |
| 1431 | `                else:` | The next line runs when the case does not depend on the limits. |
| 1432 | `                    t += 'So the bounded prediction of H3a failed in this session on this CPU. '` | Adds the sentence that the bounded prediction of H3a failed in this session on this CPU. |
| 1433 | `            case_txt.append(t)` | Appends the text of the CPU to `case_txt`. |
| 1434 | `        if nch == 0 and nev == 0:` | Tests whether the session has no level change and no counter increase. |
| 1435 | `            h3b.append(pre + 'No interval shows a level change, and none follows an increase of <code>thp_collapse_alloc</code> or <code>pgmigrate_success</code>. So this session has no case of "a level change with no sign of a page change" to report for H3b ' + R('plan') + '.')` | Then a text goes to `h3b`: no interval shows a level change, and none follows an increase of the two counters. So this session has no case of a level change with no sign of a page change to report for H3b, with a citation of the plan. |
| 1436 | `        elif nch:` | Tests the other case: the session has at least one level change. |
| 1437 | `            ns = sum(v['level_changes_with_no_sign_of_a_page_change'] for v in pc.values())` | `ns`: the count of level changes with no sign of a page change, summed over the CPUs of the analysis result. |
| 1438 | `            nn = sum(v['level_changes_low_high'] for v in pc.values())` | `nn`: the count of level changes between low and high, summed over the CPUs. |
| 1439 | `            h3b.append(pre + f'{ns} of the {pl(nn, "level change", "level changes")} between two neighbouring labelled intervals had equal coverage and no increase of the two counters between the two intervals. The plan calls this "no sign of a page change". It is not proof that the physical pages stayed the same ' + R('plan') + '.')` | Appends a text to `h3b`: how many of the level changes between two neighbouring labelled intervals had equal coverage and no increase of the two counters (`ns` of `nn`). It adds that the plan calls this "no sign of a page change" and that it is no proof of unchanged physical pages, with a citation of the plan. |
| 1440 | `    o.append('<p class="take">' + '<br>'.join(takes) + '</p>')` | Adds the summaries of all sessions as one highlighted paragraph. |
| 1441 | `    o.append('<p class="cap">One panel is one process. The vertical axis is the rate in GB/s, and it is the same in all panels of all sessions. It starts at ' f'{ymin:g}' ' GB/s, not at 0. The four numbers at the right of a panel are computed from all intervals. Value labels mark the first, the last, the lowest and the highest interval. '` | Starts the caption of the charts: what a panel is, that the rate axis is the same in all panels and starts at `ymin` and not at 0, what the four numbers at the right are computed from, and which four intervals carry a value label. |
| 1442 | `             + (f'{pl(len(lost), "value label was", "value labels were")} left out, because no free place was found: '` | Continues line 1441 when value labels were left out: their count, and the reason that no free place was found. |
| 1443 | `                + ', '.join(f'{"session " + e(n) + ", " if many(D) else ""}process {e(t)}, interval {i} ({fx(v)} GB/s)' for n, t, i, v in lost) + '. ' if lost else '') +` | Continues line 1442 with the list of these labels: the session, the process, the interval and the rate of each. |
| 1444 | `             'The vmstat counters count for the whole system, not for the buffer ' + R('handoff') + '. The limit of 1 GB/s for a step is a choice of this page for the description.</p>')` | Ends the caption with two remarks: the counters of `/proc/vmstat` count for the whole system and not for the buffer (with a citation of the handoff note), and the limit of 1 GB/s for a step is a choice of the generated page. |
| 1445 | `    o.append('<h3>The counts behind cases (a) and (b)</h3>')` | Adds a heading for the counts behind the cases (a) and (b). |
| 1446 | `    o.append('<p>The handoff names two cases that contradict H3a, each per CPU and session. Case (a): at least 10 low and at least 10 high intervals with full coverage. '` | Adds a paragraph that defines the two cases of the handoff note that contradict H3a, each per CPU and session. This line holds case (a): at least 10 low and at least 10 high intervals with full coverage. |
| 1447 | `             'Case (b): at least 10 low and at least 10 high intervals with no huge page ' + R('handoff', 'devscripts') + '.</p>')` | Ends the paragraph with case (b), the same counts with no huge page, and with citations of the handoff note and of the note on the deviations. |
| 1448 | `    o.append('<div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if many(D) else '') + '<th>CPU</th><th>Processes</th><th>Of them with --no-thp</th><th>Low, full coverage</th><th>High, full coverage</th><th>Case (a)</th>'` | Opens the table of the counts and starts its header row: the session (with several sessions), the CPU, the processes, how many of them ran with `--no-thp`, the low and the high intervals with full coverage, and case (a). |
| 1449 | `             '<th>Low, no huge page</th><th>High, no huge page</th><th>Case (b)</th><th>Between the limits, full / none</th><th>Partial or unknown coverage</th><th>Result of the rule for this CPU</th></tr>')` | Ends the header row: the low and the high intervals with no huge page, case (b), the intervals between the limits with full and with no coverage, the intervals with partial or unknown coverage, and the result of the rule for the CPU. |
| 1450 | `    for n in have:` | Loop over the sessions with data of B4. |
| 1451 | `        for c, v in D['sessions'][n]['res'].get('B4', {}).get('per_cpu', {}).items():` | Loop over the CPUs of the analysis result of B4. |
| 1452 | `            iv = v['intervals']` | `iv`: the interval counts of the CPU per level and coverage. |
| 1453 | `            other = sum(iv[l][k] for l in iv for k in ('partial', 'unknown'))` | `other`: the count of intervals with partial or unknown coverage, over all three levels. |
| 1454 | `            o.append('<tr>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{c}</td><td>{v['n_processes']}</td><td>{v['n_processes_no_thp']}</td><td>{iv['low']['full']}</td><td>{iv['high']['full']}</td><td>{yn('a' in v['cases'])}</td>"` | Starts the table row: the session, the CPU, the count of processes, the count with `--no-thp`, the low and the high intervals with full coverage, and yes or no for case (a). |
| 1455 | `                     f"<td>{iv['low']['none']}</td><td>{iv['high']['none']}</td><td>{yn('b' in v['cases'])}</td><td>{iv['changing']['full']} / {iv['changing']['none']}</td><td>{other}</td>"` | Continues line 1454: the low and the high intervals with no huge page, yes or no for case (b), the intervals between the limits with full and with no coverage, and `other`. |
| 1456 | `                     f"<td class=\"l\">{e(v['decision'])}</td></tr>")` | Ends the table row with the decision text of the analysis for the CPU. |
| 1457 | `    o.append('</table></div>')` | Closes the table. |
| 1458 | `    o.append('<p class="take">' + '<br>'.join(case_txt) + '</p>')` | Adds the texts of `case_txt` as one highlighted paragraph. |
| 1459 | `    o.append(f'<p class="cap">"Depends on the provisional limits" means: more than half of the low intervals with full coverage lie less than {NEAR:g} GB/s below {LOW:g} GB/s, or more than half of the high ones lie less than {NEAR:g} GB/s above {HIGH:g} GB/s. The value {NEAR:g} GB/s is a choice of this page.</p>')` | Adds a caption that defines "depends on the provisional limits": more than half of the low intervals with full coverage lie less than 0.2 GB/s below 69 GB/s, or more than half of the high ones lie less than 0.2 GB/s above 70.5 GB/s. It says that the value 0.2 GB/s is a choice of the generated page. |
| 1460 | `    o += [f'<p>{t}</p>' for t in h3b]` | Adds each text of `h3b` as a paragraph. |
| 1461 | `    o.append('<details><summary>Values of every process of B4</summary>' + proc_table(D, 'b4') + '</details>')` | Adds the table of `proc_table` for B4 in a folded block. |
| 1462 | `    return '\n'.join(o)` | Returns the section as one text. |

### `B6N` and function `sec_b6`: the section of step B6 (lines 1465 to 1542)

| Line | Source | Explanation |
|---:|---|---|
| 1465 | `B6N = {'oldread': 'old read 8 MiB', 'oldread2': 'old read 2, 8 MiB', 'oldread@1M': 'old read 1 MiB'}` | `B6N`: the names of the three old read entries in the rows of the chart of line 1524: old read at 8 MiB, its second copy at 8 MiB, and old read at 1 MiB. |
| 1468 | `def sec_b6(D, R):` | Starts the function `sec_b6`. It builds the section of step B6: `oldread` at 8 MiB and at 1 MiB in one process, with reference intervals. |
| 1469 | `    o = ['<h2 id="b6">B6: old read at 8 MiB and at 1 MiB, with references</h2>']` | `o`: the pieces of the section. The first piece is the heading of B6 with the anchor `b6`. |
| 1470 | `    o.append('<p>Each process times old read at 8 MiB, old read at 1 MiB (a size that fits L2) and a second copy of old read at 8 MiB, with reference intervals of asm read at 8 MiB between the pairs ' + R('handoff') + '. '` | Adds the first paragraph. Its first sentence, typed, says what a process of B6 times: old read at 8 MiB, old read at 1 MiB (a size that fits the L2 cache) and a second copy of old read at 8 MiB, with reference intervals of asm read between the pairs. It cites the handoff note. |
| 1471 | `             'H1 predicts two things: the rate of old read at 8 MiB does not differ between low and high intervals, and it does not differ from its rate at 1 MiB ' + R('plan') + '.</p>')` | Ends the paragraph with the two bounded predictions of H1 for this step: no difference of old read at 8 MiB between low and high intervals, and no difference from its rate at 1 MiB. A citation of the plan follows. |
| 1472 | `    have = [n for n in D['names'] if D['sessions'][n]['b6']]` | `have`: the sessions that have data of B6. |
| 1473 | `    for n in D['names']:` | Loop over the sessions. |
| 1474 | `        if n not in have:` | Tests whether the session has no data of B6. |
| 1475 | `            o.append(miss(f'Step B6{" of session " + e(n) if many(D) else ""}: no process is in the input. A run of step B6 would give it.'))` | Then a block "Insufficient data" is added: no process of step B6 is in the input, and a run of step B6 would give it. |
| 1476 | `    if not have:` | Tests whether no session has data of B6. |
| 1477 | `        return '\n'.join(o)` | Then the section ends here. |
| 1478 | `    o.append('<h3>Part 1: old read in low against high intervals</h3>')` | Adds the heading of part 1: old read in low against high intervals. |
| 1479 | `    o.append('<div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if many(D) else '') + '<th>CPU</th><th>Stable low processes</th><th>Stable high processes</th><th>Processes that are not stable</th><th>A/A spread, GB/s</th><th>Low minus high, GB/s</th>'` | Opens the table of part 1 and starts its header row: the session (with several sessions), the CPU, the counts of stable low, of stable high and of not stable processes, the A/A spread in GB/s, and low minus high in GB/s. |
| 1480 | `             '<th>Old read at 8 MiB, GB/s</th><th>Old read at 1 MiB, GB/s</th><th>Reference (asm read at 8 MiB), GB/s</th><th>Rule: word</th></tr>')` | Ends the header row: the rates of old read at 8 MiB, of old read at 1 MiB and of the reference in GB/s, and the word of the rule. |
| 1481 | `    nobs = nall = 0` | Two counts start at 0: `nobs` (the rows with the word `not observed`) and `nall` (all rows). |
| 1482 | `    for n in have:` | Loop over the sessions with data of B6. |
| 1483 | `        x = D['sessions'][n]` | `x`: the values of the session. |
| 1484 | `        g = x['b6']` | `g`: the description of B6. |
| 1485 | `        for c, v in x['res']['B6']['state'].items():` | Loop over the CPUs of part 1 in the analysis result. For each CPU the rule compares the median rate of `oldread` at 8 MiB of the stable low processes with that of the stable high processes. The difference is resolved when its absolute value is larger than the A/A spread of the CPU and every low value lies on one side of every high value. A CPU with fewer than 2 stable processes of one of the two labels is `not observed` [Ref2][Ref4]. |
| 1486 | `            nall += 1` | Counts the row. |
| 1487 | `            nobs += v['decision'] == 'not observed'` | Adds 1 to `nobs` when the word is `not observed`. |
| 1488 | `            pc = g['per_cpu'].get(c)` | `pc`: the values of the description for this CPU, or `None`. |
| 1489 | `            rf = [median(r['refs']) for r in g['recs'] if r['cpu'] == c]` | `rf`: for each process of the CPU the median of its reference rates. |
| 1490 | `            o.append('<tr>' + (f'<td>{e(n)}</td>' if many(D) else '') + f"<td>{c}</td><td>{v['n_low']}</td><td>{v['n_high']}</td><td>{v['n_changing']}</td><td>{fx(v['aa_spread'])}</td><td>{s2(v['difference'])}</td>"` | Starts the table row with values of the analysis: the session, the CPU, the three process counts, the A/A spread, and the difference low minus high with its sign. A missing difference is printed as `-`. |
| 1491 | `                     + (f"<td>{fx(pc['first_rate'])}</td><td>{fx(pc['second_rate'])}</td><td>{fx(median(rf))}</td>" if pc and rf else '<td>-</td><td>-</td><td>-</td>') + f"<td class=\"l nw\">{e(v['decision'])}</td></tr>")` | Ends the table row. With a description it holds `first_rate`, `second_rate` and the median of `rf`. Without one it holds three cells with `-`. The word of the rule follows. |
| 1492 | `    o.append('</table></div>')` | Closes the table. |
| 1493 | `    o.append(f'<p class="take">In {nobs} of {pl(nall, "row", "rows")} the result is "not observed". The rule needs 2 stable low and 2 stable high processes on one CPU. '` | Starts a highlighted paragraph: in how many of the rows the result is "not observed". A typed sentence follows: the rule needs 2 stable low and 2 stable high processes on one CPU. |
| 1494 | `             + (f'{ID}: old read in stable high intervals. A session in which a CPU has both stable low and stable high processes would give it. ' if nobs else '') + frefs(R, D, 'B6') + '</p>')` | Ends the paragraph. When at least one row is `not observed`, it adds `Insufficient data` for old read in stable high intervals, and the measurement that would give it: a session in which a CPU has both stable low and stable high processes. This reason is typed. The code does not test which label is missing. The citations of the result folders of B6 follow. |
| 1495 | `    o.append('<p class="cap">The three rate columns give the median over the processes of the CPU of the median rate of each process.</p>')` | Adds a caption: the three rate columns give the median over the processes of the CPU of the median rate of each process. |
| 1496 | `    o.append(group_block(D, R, 'B6', None, 'Part 2: old read at 8 MiB minus old read at 1 MiB', 'old read at 8 MiB minus old read at 1 MiB', 'old read 2 minus old read, both at 8 MiB', False, None, marked=False))` | Adds the block of part 2 from `group_block`, with `key` set to `None`: old read at 8 MiB minus old read at 1 MiB as `d`, and old read 2 minus old read, both at 8 MiB, as `e`. The table has one rule column for the label `none`. The block carries no description mark. |
| 1497 | `    # by previous entry` | Comment: the rates by the entry that ran before follow. |
| 1498 | `    o.append('<h3>Old read by the loop that ran directly before it (description, no decision)</h3>')` | Adds a heading: old read by the loop that ran directly before it, with the mark that this is a description and no decision. |
| 1499 | `    allv = [q for n in have for c in D['sessions'][n]['b6_prev'].values() for v in c.values() for q in v]` | `allv`: all rates of `b6_prev` (lines 287 to 297), over the sessions. |
| 1500 | `    xmin, xmax = axis_floor(min(allv) - 0.2), max(allv) + 0.4` | `xmin` and `xmax`: the two ends of the rate axis. The start lies 0.2 GB/s below the lowest rate, rounded down to a multiple of 0.5. The end lies 0.4 GB/s above the highest rate. |
| 1501 | `    takes = []` | `takes`: the summaries, empty at the start. |
| 1502 | `    for n in have:` | Loop over the sessions with data of B6. |
| 1503 | `        x = D['sessions'][n]` | `x`: the values of the session. |
| 1504 | `        bp, g = x['b6_prev'], x['b6']` | `bp`: the rates by the loop before. `g`: the description of B6. |
| 1505 | `        rows, facts, groups = [], [], set()` | Three empty values: `rows` (the chart rows), `facts` (the differences) and `groups` (the row numbers that end a CPU). |
| 1506 | `        for c in sorted(bp):` | Loop over the CPUs, in rising order. |
| 1507 | `            for ent in ('oldread', 'oldread2', 'oldread@1M'):` | Loop over the three old read entries. |
| 1508 | `                for kind in ('asm read', 'an old read entry'):` | Loop over the two kinds of the loop before: asm read, and an old read entry. |
| 1509 | `                    v = bp[c].get((ent, kind))` | `v`: the rates of this CPU, entry and kind. |
| 1510 | `                    if not v:` | Tests whether there is none. |
| 1511 | `                        continue` | Then no chart row is made. |
| 1512 | `                    other = bp[c].get((ent, 'an old read entry' if kind == 'asm read' else 'asm read'))` | `other`: the rates of the same entry after the other kind of loop. |
| 1513 | `                    right = f'{fx(median(v))} GB/s'` | `right`: the text for the right side: the median of `v` in GB/s. |
| 1514 | `                    if kind == 'asm read' and other:` | Tests whether this is the row "after asm read" and the other row exists. |
| 1515 | `                        diff = median(v) - median(other)` | `diff`: the median rate after asm read minus the median rate after an old read entry, in GB/s. |
| 1516 | `                        right = f'{fx(median(v))} GB/s: {zs(diff)} against next row'` | `right` then also gives `diff` with its sign and the words "against next row". |
| 1517 | `                        facts.append((c, ent, diff))` | Stores the CPU, the entry and `diff` in `facts`. |
| 1518 | `                    rows.append((f'CPU {c}: {B6N[ent]}, after {"asm read" if kind == "asm read" else "old read"}', [(q, f'{fx(q)} GB/s', 0) for q in v], right))` | Appends the chart row: the CPU, the name of the entry from `B6N`, and the kind of the loop before. It has one dot per interval, with the rate as tooltip, and the text `right`. |
| 1519 | `            groups.add(len(rows))` | After the rows of a CPU, the number of its last row goes to `groups`. |
| 1520 | `        if not rows:` | Tests whether the session gave no chart row. |
| 1521 | `            continue` | Then the next session follows. |
| 1522 | `        if many(D):` | Tests whether several sessions are shown. |
| 1523 | `            o.append(f'<h4>Session {e(n)}</h4>')` | Then a heading with the session name is added. |
| 1524 | `        o.append(strip(rows, xmin, xmax, f'rate of one interval, GB/s (the axis starts at {xmin:g} GB/s, not at 0)', 'B6: rate of old read by the loop that ran before', L=262, R=230, groups=groups, right_head='median of the row'))` | Adds the chart of `strip`. The title of its axis names the rate of one interval in GB/s, gives the start value of the axis and says that the axis does not start at 0. The margins are 262 and 230 units. The heading of the right column says that the number is the median of the row. |
| 1525 | `        big = [f[2] for f in facts if f[1] in ('oldread', 'oldread2')]` | `big`: the differences `diff` of the two entries at 8 MiB, `oldread` and `oldread2`. |
| 1526 | `        if big:` | Tests whether there is one. |
| 1527 | `            takes.append(f'{"Session " + e(n) + ". " if many(D) else ""}An interval of old read at 8 MiB that follows an asm read interval differs from one that follows an old read interval by {rng(min(big), max(big), signed=True)} GB/s (median, per CPU and copy). '` | Then a summary is added: by how much an interval of old read at 8 MiB that follows an asm read interval differs from one that follows an old read interval. It is the range of `big` in GB/s. The values are medians per CPU and copy. |
| 1528 | `                         f'The largest A/A spread of a CPU is {fx(max(v["aa_spread"] for v in g["per_cpu"].values()))} GB/s, and the largest single A/A pair is {fx(max(v["aa_single_max"] for v in g["per_cpu"].values()))} GB/s. ' + fref(R, D, n, 'B6'))` | Ends the summary: the largest A/A spread of a CPU and the largest single A/A pair, in GB/s, with the citations of the result folders of B6. |
| 1529 | `    if takes:` | Tests whether a summary exists. |
| 1530 | `        o.append('<p class="take">Description, no decision. ' + '<br>'.join(takes) + '</p>')` | Then the summaries are added as one highlighted paragraph that starts with the words `Description, no decision.` |
| 1531 | `    o.append('<p class="cap">One dot is one interval. "After old read" means that the interval before was old read at 8 MiB, its second copy, or old read at 1 MiB. The first interval of a process is not shown, because nothing ran before it.</p>')` | Adds a caption: what a dot is, what "after old read" covers (old read at 8 MiB, its second copy, or old read at 1 MiB), and why the first interval of a process is not shown. |
| 1532 | `    cav, effect = b6_caveat(D)` | `cav`: the sentences of `b6_caveat`. `effect`: its flag for a position effect. |
| 1533 | `    if cav:` | The next lines run when there are such sentences. |
| 1534 | `        o.append('<p><b>What this means for part 2.</b> In the B6 sequence one loop of each pair follows a reference interval of asm read, and the other follows an old read interval ' + R('handoff') + '. '` | Adds a paragraph with the heading "What this means for part 2". Its first sentence, typed, recalls the B6 sequence: one loop of each pair follows a reference interval of asm read, and the other follows an old read interval. It cites the handoff note. |
| 1535 | `                 'So a pair value contains the difference between the two loops and the difference between the two positions.</p><ul>' + ''.join(f'<li>{e(c)}</li>' for c in cav) + '</ul>')` | Ends the paragraph with the consequence: a pair value holds the difference between the two loops and the difference between the two positions. The sentences of `cav` follow as a list. |
| 1536 | `        if effect:` | Tests whether the position effect is shown (line 473). |
| 1537 | `            o.append('<p>The position difference is measured. Its cause is a hypothesis: the loop that ran before leaves a state (cache contents or prefetcher state) that changes the rate of old read at 8 MiB in the next 0.3 s interval. '` | Then a typed paragraph is added. It calls the position difference measured and its cause a hypothesis: the loop that ran before leaves a state, such as cache contents or prefetcher state, that changes the rate of old read at 8 MiB in the next interval of 0.3 s. |
| 1538 | `                     'A counter run of the B6 sequence, as in Part C, would confirm or reject it: it would show whether the refills per line differ between the two positions. The rule and its result were not changed.</p>')` | Ends the paragraph with the measurement that would decide the hypothesis: a counter run of the B6 sequence, which would show whether the refills per line differ between the two positions. It also says that the rule and its result were not changed. |
| 1539 | `    o.append(proc_details(D, 'B6', lambda x: [('B6', x['b6'])] if x['b6'] else [], 'Values of every process of B6'))` | Adds the folded table of `proc_details` for B6, with one group named `B6`. |
| 1540 | `    return '\n'.join(o)` | Returns the section as one text. |

### Counter groups: `ENTRY_ORDER`, `LEVEL_ORDER`, `group_name`, `counter_groups`, `c2_words` (lines 1543 to 1577)

| Line | Source | Explanation |
|---:|---|---|
| 1543 | `ENTRY_ORDER = ['asmcopy', 'asmcopy2', 'copy', 'asmread']` | `ENTRY_ORDER`: the order of the kernels in the charts and tables of the counters: `asmcopy`, `asmcopy2`, `copy`, `asmread`. |
| 1544 | `LEVEL_ORDER = ['-', 'low', 'changing', 'high']` | `LEVEL_ORDER`: the order of the level groups: `-` (no level), `low`, `changing` and `high`. |
| 1547 | `def group_name(g):` | Starts the function `group_name`. It builds the name of one counter group for a chart row. |
| 1548 | `    lev = '' if g['level'] == '-' else ', ' + ('between the limits' if g['level'] == 'changing' else g['level'])` | `lev`: the level part of the name. It is empty for a group without a level. For the level `changing` it is the words "between the limits". For any other level it is the level word. |
| 1549 | `    return f"{g['group'].replace('cpu', 'CPU ')}: {kn(g['entry'])}{lev}"` | Returns the name: the group with `cpu` replaced by `CPU` and a space, a colon, the page name of the kernel from `kn`, and `lev`. |
| 1552 | `def counter_groups(r):` | Starts the function `counter_groups`. It puts the counter groups of one step result into the order of the page. |
| 1553 | `    cpu_no = lambda g: int(re.sub(r'\D', '', g['group']) or 0)` | `cpu_no`: a small function that gives the CPU number of a group. It removes every character that is not a digit from the group name (the pattern `\D` fits one such character) and reads the rest as a number. A name without a digit gives 0. |
| 1554 | `    groups = sorted((dict(g, _name=group_name(g)) for g in r['groups']),` | Starts `groups`: a copy of every group of the analysis result with the added value `_name`, in sorted order. |
| 1555 | `                    key=lambda g: (cpu_no(g), ENTRY_ORDER.index(g['entry']) if g['entry'] in ENTRY_ORDER else 9, LEVEL_ORDER.index(g['level']) if g['level'] in LEVEL_ORDER else 9))` | Ends line 1554 with the sort key: first the CPU number, then the place of the kernel in `ENTRY_ORDER`, then the place of the level in `LEVEL_ORDER`. A kernel or a level that is not in its list gets the place 9 and so comes last. |
| 1556 | `    for i, g in enumerate(groups):` | Loop over the sorted groups, with the index `i`. |
| 1557 | `        g['_last'] = i + 1 < len(groups) and groups[i + 1]['group'] != g['group']` | `_last`: true when a next group exists and belongs to another CPU. The chart draws a heavy line below such a group. |
| 1558 | `    return groups` | Returns the groups. |
| 1561 | `def c2_words(groups):` | Starts the function `c2_words`. It writes sentences that put the counts of `copy` beside those of `asmcopy` in step C2. |
| 1562 | `    """C2: the counts per line of new C copy next to asm copy, as ranges over the CPUs. Description only."""` | Docstring: step C2: the counts per line of new C copy next to asm copy, as ranges over the CPUs. It is a description only. |
| 1563 | `    cp = [g for g in groups if g['entry'] == 'copy']` | `cp`: the groups of the kernel `copy`, one per CPU. |
| 1564 | `    ac = [g for g in groups if g['entry'] == 'asmcopy']` | `ac`: the groups of the kernel `asmcopy`. |
| 1565 | `    if not cp or not ac:` | Tests whether one of the two lists is empty. |
| 1566 | `        return ''` | Then an empty text is returned. |
| 1567 | `    t = []` | `t`: the sentences, empty at the start. |
| 1568 | `    for k, name, nd in (('cycles', 'Cycles per line', 2), ('l2d_refill', 'L2D refills per line', 3), ('l1d_refill', 'L1D refills per line', 3), ('instructions', 'Instructions per line', 3)):` | Loop over four values, each with its key, its name and its count of decimals: cycles per line (2 decimals), then L2D refills, L1D refills and instructions per line (3 decimals each). |
| 1569 | `        a = [g['median_%s_per_line' % k] for g in cp if g['median_%s_per_line' % k] is not None]` | `a`: the median of this value per line for each group of `copy`. A group without the value is left out. |
| 1570 | `        b = [g['median_%s_per_line' % k] for g in ac if g['median_%s_per_line' % k] is not None]` | `b`: the same for each group of `asmcopy`. |
| 1571 | `        if a and b:` | The next lines run when both lists have values. |
| 1572 | `            rel = ('equal at this precision' if rng(min(a), max(a), nd) == rng(min(b), max(b), nd) else 'new C copy is higher on every CPU' if min(a) > max(b) else` | Starts `rel`, the relation of the two ranges in words. It says "equal at this precision" when both ranges print the same text. It says that new C copy is higher on every CPU when the lowest value of `a` is above the highest value of `b`. |
| 1573 | `                   'new C copy is lower on every CPU' if max(a) < min(b) else 'the ranges overlap')` | Ends `rel`: it says that new C copy is lower on every CPU when the highest value of `a` is below the lowest value of `b`. In every other case it says that the ranges overlap. |
| 1574 | `            t.append(f'{name}: new C copy {rng(min(a), max(a), nd)}, asm copy {rng(min(b), max(b), nd)} ({rel}).')` | Appends one sentence: the name of the value, the range of new C copy, the range of asm copy, and `rel` in brackets. |
| 1575 | `    return ' '.join(t)` | Returns the sentences as one text. |

### Function `sec_c`: the section of the counter steps C1 and C2 (lines 1578 to 1661)

| Line | Source | Explanation |
|---:|---|---|
| 1578 | `def sec_c(D, R):` | Starts the function `sec_c`. It builds the section of the steps C1 and C2: the schedules of B4 and of B1 at 8 MiB, run with core counters. |
| 1579 | `    o = ['<h2 id="c">C1 and C2: core counters per 64 B line</h2>']` | `o`: the pieces of the section. The first piece is the heading "C1 and C2: core counters per 64 B line" with the anchor `c`. |
| 1580 | `    o.append('<p>The counter runs repeat the schedule of B4 (C1) and of B1 at 8 MiB (C2). Each thread reads five counters of its own core directly before and after every interval. The counters count only the code of the benchmark, not the Linux kernel ' + R('handoff') + '. '` | Adds the first paragraph, as typed text. It starts with what the counter runs are: the schedule of B4 as C1 and of B1 at 8 MiB as C2, with five counters that each thread reads on its own core directly before and after every interval. It says that the counters count the code of the benchmark and not the Linux kernel, and cites the handoff note. |
| 1581 | `             'A line is 64 B of the bytes that the interval counts. A copy interval counts the bytes read plus the bytes written ' + R('analyze') + '. '` | Continues line 1580 with the definition of a line: 64 B of the bytes that the interval counts, where a copy interval counts the bytes read plus the bytes written. It cites `analyze_bwx.py`. |
| 1582 | `             'The clock is the cycle count divided by the CPU time of the thread. Part C gives a description. The handoff has no decision rule for it ' + R('devscripts') + '. '` | Continues line 1580 with the definition of the clock (the cycle count divided by the CPU time of the thread) and with the remark that Part C gives a description without a decision rule. It cites the note on the deviations. |
| 1583 | `             'The plan asks C1 for the counts per line at the low and at the high level, and C2 whether the memory-side counts per line differ between the two copy loops ' + R('plan') + '.</p>')` | Ends the paragraph with what the plan asks of C1 (the counts per line at both levels) and of C2 (whether the memory-side counts per line differ between the two copy loops), and a citation of the plan. |
| 1584 | `    l1 = []` | `l1`: the facts on the two refill counts, empty at the start. |
| 1585 | `    for step, bstep, what in (('C1', 'B4', 'asm read, 200 intervals'), ('C2', 'B1', 'the copy loops at 8 MiB')):` | Loop over the two counter steps. Each has the step of Part B with the same schedule and a short text: C1 with B4 (asm read, 200 intervals), and C2 with B1 (the copy loops at 8 MiB). |
| 1586 | `        o.append(f'<h3>{step}: {what}</h3>')` | Adds a heading with the step and its short text. |
| 1587 | `        takes, tables, comp, comp_n, no_high = [], [], [], [0, 0], []` | Five start values: the empty lists `takes`, `tables`, `comp` and `no_high`, and `comp_n`, two counts that start at 0. |
| 1588 | `        for name in D['names']:` | Loop over the sessions. |
| 1589 | `            x = D['sessions'][name]` | `x`: the values of the session. |
| 1590 | `            r = x['res'].get(step)` | `r`: the result of the analysis for the step, or `None`. |
| 1591 | `            pre = f'Session {e(name)}. ' if many(D) else ''` | `pre`: the session name as the start of a sentence, when several sessions are shown. |
| 1592 | `            if not r or not r['groups']:` | Tests whether the step has no result or no counter group. |
| 1593 | `                o.append(miss(f'Step {step}{" of session " + e(name) if many(D) else ""}: no counter row is in the input. A run of step {step} would give it.'))` | Then a block "Insufficient data" is added: no counter row is in the input, and a run of the step would give it. |
| 1594 | `                continue` | The loop goes on with the next session. |
| 1595 | `            groups = counter_groups(r)` | `groups`: the counter groups in the order of the page. |
| 1596 | `            f = x['cfacts'][step]` | `f`: the facts of `counter_facts` for the step. |
| 1597 | `            if many(D):` | Tests whether several sessions are shown. |
| 1598 | `                o.append(f'<h4>Session {e(name)}</h4>')` | Then a heading with the session name is added. |
| 1599 | `            o.append(counter_chart(groups, f'{step}: counter values per line for each CPU, kernel and level group'))` | Adds the chart of `counter_chart` for these groups. |
| 1600 | `            ipl = [g['median_instructions_per_line'] for g in groups if g['median_instructions_per_line'] is not None]` | `ipl`: the median count of instructions per line of each group that has one. |
| 1601 | `            clk = [g['median_clock_GHz'] for g in groups if g['median_clock_GHz'] is not None]` | `clk`: the median clock of each group in GHz. The analysis computes the clock of one `C` row as its cycle count divided by its field 9 (`cputime_ns`) [Ref3]. |
| 1602 | `            t = (f'{pre}{f["used"]} of the {pl(f["rows"], "counter row", "counter rows")} are used. '` | Starts the summary `t`: how many of the counter rows are used. |
| 1603 | `                 + (f'The clock of the busy core is {rng(min(clk), max(clk), 3)} GHz over the groups. ' if clk else '')` | Continues line 1602 when clock values exist: the range of the clock of the busy core over the groups, in GHz with 3 decimals. |
| 1604 | `                 + (f'Instructions per line: {rng(min(ipl), max(ipl), 3)} over the groups. ' if ipl else ''))` | Ends line 1602 when the values exist: the range of the instructions per line over the groups, with 3 decimals. |
| 1605 | `            if f['cpu_share_min'] is not None:` | Tests whether a CPU share exists. |
| 1606 | `                t += f'The lowest CPU time of a thread was {fx(math.floor(1e4 * f["cpu_share_min"]) / 100, 2)} % of the elapsed time of its interval (rounded down). '` | Then a sentence is added: the lowest CPU time of a thread in percent of the elapsed time of its interval. The value is cut after 2 decimals and never rounded up. The sentence says so with the words "rounded down". |
| 1607 | `            if step == 'C2':` | Tests whether the step is C2. |
| 1608 | `                w = c2_words(groups)` | `w`: the sentences of `c2_words`. |
| 1609 | `                if w:` | Tests whether there are such sentences. |
| 1610 | `                    t += 'Description, no decision. ' + w + ' '` | Then they are added behind the words `Description, no decision.` |
| 1611 | `            takes.append(t + fref(R, D, name, step))` | Appends the summary to `takes`, with the citations of the result folders of the step. |
| 1612 | `            if step == 'C1' and not any(g['level'] == 'high' for g in groups):` | Tests whether the step is C1 and no group has the level `high`. |
| 1613 | `                no_high.append((name, sorted({'between the limits' if g['level'] == 'changing' else g['level'] for g in groups})))` | Then the session and the level groups that were seen go to `no_high`. The level `changing` is named "between the limits". |
| 1614 | `            if f['read_rows']:` | Tests whether the step has `asmread` rows with both refill counts. |
| 1615 | `                l1.append((name, step, f['l1_lt_l2'], f['read_rows']))` | Then one entry goes to `l1`: the session, the step, the count of such rows with fewer L1D refills than L2D refills, and the count of all such rows. |
| 1616 | `            tb = ['<div class="tw"><table class="c"><tr><th>CPU</th><th>Kernel</th><th>Level group</th><th>Processes</th><th>Intervals</th><th>Rate, GB/s</th><th>Clock, GHz</th>' + ''.join(f'<th>{n} per line</th>' for _, n in EV) + '</tr>']` | Starts `tb`, the table of the groups. Its header row: the CPU, the kernel, the level group, the processes, the intervals, the rate in GB/s, the clock in GHz, and one column per event with the words "per line". |
| 1617 | `            for g in groups:` | Loop over the groups. |
| 1618 | `                lev = {'-': 'no level', 'changing': 'between the limits'}.get(g['level'], g['level'])` | `lev`: the text of the level: "no level" for `-`, "between the limits" for `changing`, and the level word for any other. |
| 1619 | `                tb.append(f"<tr><td>{e(g['group'].replace('cpu', ''))}</td><td>{e(kn(g['entry']))}</td><td class=\"nw\">{lev}</td><td>{g['n_processes']}</td><td>{g['n_rows']}</td><td>{f2(g['median_thread_GBps'])}</td><td>{f2(g['median_clock_GHz'], 3)}</td>"` | Starts the table row: the CPU number, the page name of the kernel, `lev`, the count of processes, the count of counter rows, the median rate of a thread, and the median clock with 3 decimals. |
| 1620 | `                          + ''.join(f"<td class=\"nw\">{small(g['median_%s_per_line' % k], 4) if g['median_%s_per_line' % k] is not None else 'not supported'}</td>" for k, _ in EV) + '</tr>')` | Ends the table row with one cell per event: the median count per line from `small` with 4 decimals, or the text `not supported`. |
| 1621 | `            tables.append(f'<details><summary>Values of every group of {step}{", session " + e(name) if many(D) else ""}</summary>' + ''.join(tb) + '</table></div></details>')` | Appends the table to `tables` in a folded block. Its title names the step, and the session when several are shown. |
| 1622 | `            # rates of the counter run next to Part B` | Comment: the rates of the counter run are put beside those of Part B. |
| 1623 | `            cm, bm = x['proc_medians'][step], x['proc_medians'][bstep]` | `cm`: the process medians of the counter step (line 420). `bm`: those of the step of Part B. |
| 1624 | `            if bstep == 'B1':` | Tests whether the step of Part B is B1. |
| 1625 | `                bm = x['b1_8m_medians']` | Then only its processes at 8 MiB are taken (line 419). |
| 1626 | `            for c, k in sorted({(c, k) for c, k, nt, _ in cm if not nt}):` | Loop over the pairs of CPU and entry of the counter step, in sorted order. Only processes without `--no-thp` count. |
| 1627 | `                a = [v for cc, kk, nt, v in cm if (cc, kk) == (c, k) and not nt]` | `a`: the process medians of the counter run for this CPU and entry. |
| 1628 | `                b = [v for cc, kk, nt, v in bm if (cc, kk) == (c, k) and not nt]` | `b`: the process medians of the step of Part B for the same CPU and entry. |
| 1629 | `                if a and b:` | The next lines run when both lists have values. |
| 1630 | `                    ov = min(a) <= max(b) and min(b) <= max(a)` | `ov`: true when the range of `a` and the range of `b` overlap. |
| 1631 | `                    comp_n[0] += ov` | Adds 1 to the first count of `comp_n` when they overlap. |
| 1632 | `                    comp_n[1] += 1` | Adds 1 to the second count, the count of all comparisons. |
| 1633 | `                    comp.append('<tr>' + (f'<td>{e(name)}</td>' if many(D) else '') + f"<td>{c}</td><td>{e(kn(k))}</td><td>{len(a)}</td><td>{fx(min(a))} to {fx(max(a))}</td><td>{len(b)}</td><td>{fx(min(b))} to {fx(max(b))}</td><td>{yn(ov)}</td></tr>")` | Appends one table row to `comp`: the session, the CPU, the kernel, the count and the range of the process medians of the counter run, the same for Part B, and yes or no for the overlap. |
| 1634 | `            if not any(1 for c, k, nt, _ in bm if not nt):` | Tests whether the step of Part B has no process without `--no-thp`. |
| 1635 | `                o.append(miss(f'{pre}The rates of step {bstep}, to compare with the counter run.'))` | Then a block "Insufficient data" is added: the rates of that step, to compare with the counter run. |
| 1636 | `        if no_high:` | After the sessions: tests whether a session has no high level in C1. |
| 1637 | `            o.append(miss(f'Counters at the high level in a long run. No interval of C1 was above {HIGH:g} GB/s' + (f' in {"session" if len(no_high) == 1 else "sessions"} {" and ".join(e(n) for n, _ in no_high)}' if many(D) else '')` | Then a block "Insufficient data" is added for counters at the high level in a long run. It says that no interval of C1 was above 70.5 GB/s, and names the sessions when several are shown. |
| 1638 | `                          + f'. The level groups that were seen are: {", ".join(sorted({v for _, lv in no_high for v in lv}))}. A C1 process that reaches the high level would give them.'))` | Ends the block: the level groups that were seen, and that a C1 process that reaches the high level would give the missing values. |
| 1639 | `        if takes:` | Tests whether a summary exists. |
| 1640 | `            o.append('<p class="take">' + '<br>'.join(takes) + '</p>')` | Then the summaries are added as one highlighted paragraph. |
| 1641 | `        if comp:` | The next lines run when the comparison has rows. |
| 1642 | `            o.append(f'<p>In {comp_n[0]} of {pl(comp_n[1], "row", "rows")} (one per CPU, kernel and session) the process medians of the counter run overlap those of step {bstep} without counters. ' + frefs(R, D, step, bstep) + '</p>')` | Adds a paragraph: in how many of the rows the process medians of the counter run overlap those of the step of Part B without counters. One row is one CPU, kernel and session. The citations of the result folders of both steps follow. |
| 1643 | `            tables.append(f'<details><summary>Rates of {step} next to step {bstep} without counters</summary><div class="tw"><table class="c"><tr>' + ('<th>Session</th>' if many(D) else '') + f'<th>CPU</th><th>Kernel</th><th>{step}: processes</th><th>{step}: process medians, GB/s</th><th>{bstep}: processes</th><th>{bstep}: process medians, GB/s</th><th>The two ranges overlap</th></tr>'` | Starts a folded table of the comparison, with its title and header row: the session, the CPU, the kernel, and for each of the two steps the count of processes and the range of the process medians in GB/s, then the overlap. |
| 1644 | `                          + ''.join(comp) + '</table></div></details>')` | Ends the table with the rows of `comp`. |
| 1645 | `        o += tables` | Adds the folded tables of the step. |
| 1646 | `    if l1:` | After both steps: tests whether `l1` has entries. |
| 1647 | `        low = [q for q in l1 if q[2]]` | `low`: the entries with at least one row that has fewer L1D refills than L2D refills. |
| 1648 | `        if low:` | The next lines run when there is such an entry. |
| 1649 | `            o.append('<p>Observation: the count of <code>l1d_refill</code> is lower than the count of <code>l2d_refill</code> in '` | Starts a paragraph with the word `Observation`: the count of `l1d_refill` is lower than the count of `l2d_refill` in a number of intervals. |
| 1650 | `                     + ', '.join(f'{a} of the {pl(b, "asm read interval", "asm read intervals")} of {st}{" in session " + e(n) if many(D) else ""}' for n, st, a, b in l1) + '. '` | Continues line 1649 with that number for each entry of `l1`: how many of the `asmread` intervals of the step, with the session when several are shown. |
| 1651 | `                     'A line that enters L2 from the SLC and is then loaded would be expected to enter L1 too. '` | Continues line 1649 with a typed sentence: a line that enters the L2 cache and is then loaded would be expected to enter the L1 cache too. |
| 1652 | `                     'Hypothesis: for this loop the two event names do not count what they say (for example, lines that the prefetcher brings into L1 may not count as L1D refills). '` | Continues line 1649 with a typed hypothesis: for this loop the two event names do not count what they say. An example stands in brackets. |
| 1653 | `                     f'{ID} to decide it: the event definitions of this core, or a run of the same loop on a buffer that fits L1 and one that fits L2, would show what each event counts. The observation was first made in the short run before session 1, in 970 of 973 counter rows of asm read ' + R('short') + '.</p>')` | Ends the paragraph: `Insufficient data` to decide it, and the two sources that would show what each event counts. A typed sentence follows on where the observation was first made, with typed counts and a citation of the short run. |
| 1654 | `        else:` | The next line runs when no entry has such a row. |
| 1655 | `            o.append(f'<p>In none of the {pl(sum(q[3] for q in l1), "asm read interval", "asm read intervals")} is the count of <code>l1d_refill</code> lower than the count of <code>l2d_refill</code>.</p>')` | Adds one sentence: in none of the `asmread` intervals is the count of `l1d_refill` lower than the count of `l2d_refill`. It gives the count of these intervals. |
| 1656 | `    o.append('<p class="cap">Every value is the median over the intervals of the group. The level group of an asm read interval comes from its own rate and the provisional limits. Copy intervals get no level ' + R('devscripts') + '. '` | Starts the caption of the section: every value is a median over the intervals of the group, and only an asm read interval gets a level group, from its own rate and the provisional limits. It cites the note on the deviations. |
| 1657 | `             '"LL read miss" is the event <code>ll_miss_rd</code>, a read that misses the last cache level. A value below 0.000001 is printed as "below 10^-6" in a chart and as "below 1 per million" (lines) in a table. '` | Continues line 1656: the column "LL read miss" is the event `ll_miss_rd`, a read that misses the last cache level. A value below 0.000001 is printed with one fixed text in a chart and another in a table (line 914). |
| 1658 | `             'The rate panel of a chart prints the number only, because all rates are within a few percent of each other. Every other panel has its own axis from 0 to the value printed under it.</p>')` | Ends the caption: the rate panel of a chart prints the number only, and every other panel has its own axis from 0 to the value printed under it. The reason given for the rate panel, that all rates lie within a few percent of each other, is typed and not computed. |
| 1659 | `    return '\n'.join(o)` | Returns the section as one text. |

### `WORDS`: the entries of the list "Words used here" of the generated page (lines 1662 to 1726)

| Line | Source | Explanation |
|---:|---|---|
| 1662 | `WORDS = [` | Starts `WORDS`: the entries of the list "Words used here" of the generated page. Each entry is a pair of a term and its definition. All of it is typed text. |
| 1663 | `    ('CRB', 'the Arm Phoenix Reference Server (128 cores of the Arm 64-bit instruction set AArch64). All measurements ran there.'),` | Entry for CRB: the full name of the server, its 128 cores, and that all measurements ran there. |
| 1664 | `    ('Plan, handoff', 'the files <code>plan.md</code> (the reviewed test plan) and <code>handoff.md</code> (the instructions for its execution, with the numeric decision rules).'),` | Entry for the plan and the handoff note: the two files `plan.md` and `handoff.md`, and what each one is. |
| 1665 | `    ('Part A, B, C, D', 'the parts of the plan. Part A was screening with the existing benchmark. Part B uses the changed benchmark <code>bwx</code>. Part C reads counters of the cores. Part D needs root and was not run.'),` | Entry for the Parts A, B, C and D of the plan, one sentence each. By this text Part D needs root and was not run. |
| 1666 | `    ('Q1', 'the first question of the plan: why one thread with an 8 MiB buffer behaves differently from the other buffer sizes. Q1a is about old read, Q1b about copy, Q1c about two rates of one loop. The second question, Q2, is about many threads and has its own page.'),` | Entry for Q1: the first question of the plan and its three parts Q1a (old read), Q1b (copy) and Q1c (two rates of one loop). It says that the second question, Q2, has its own page. |
| 1667 | `    ('Kernel, loop', 'one timed loop of the benchmark. It is not the Linux kernel.'),` | Entry for "kernel, loop": one timed loop of the benchmark, and not the Linux kernel. |
| 1668 | `    ('<code>bwx</code>', 'the changed copy of the benchmark <code>bandwidth.c</code> that Parts B and C use. <code>bwx_o0</code>, <code>bwx_o36</code>, <code>bwx_o52</code> are three more builds for step B3.'),` | Entry for `bwx`: the changed copy of the benchmark that Parts B and C use, and the three more builds for step B3. |
| 1669 | `    ('asm read (<code>asmread</code>)', 'the read loop written in assembly. Per 256 B it runs 8 load instructions and no add.'),` | Entry for asm read: the read loop in assembly, with its count of load instructions per 256 B. |
| 1670 | `    ('Old read (<code>oldread</code>), old read 2 (<code>oldread2</code>)', 'the C read loop from before 2026-11-13, and a second copy of the same source. <code>oldread@1M</code> is old read on the first 1 MiB of the buffer.'),` | Entry for old read and old read 2: the C read loop from before 2026-11-13 and a second copy of its source. It also says that `oldread@1M` is old read on the first 1 MiB of the buffer. |
| 1671 | `    ('New C copy (<code>copy</code>)', 'the C copy loop since 2026-11-13.'),` | Entry for new C copy: the C copy loop from 2026-11-13 on. |
| 1672 | `    ('asm copy (<code>asmcopy</code>), asm copy 2 (<code>asmcopy2</code>)', 'the copy loop written in assembly, and a second copy of the same source.'),` | Entry for asm copy and asm copy 2: the copy loop in assembly and a second copy of its source. |
| 1673 | `    ('<code>asmcopy_c</code>', 'step B2: an assembly loop with the machine code of the new C copy loop (same instruction order, same registers q16 to q31), placed at the loop offset of asm copy.'),` | Entry for `asmcopy_c`: the assembly loop of step B2 with the machine code of the new C copy loop, placed at the loop offset of asm copy. |
| 1674 | `    ('<code>asmcopy_c_add</code>', 'as <code>asmcopy_c</code>, but the two <code>add</code> instructions are placed after the 8 stores, as in asm copy.'),` | Entry for `asmcopy_c_add`: the same loop with the two `add` instructions placed behind the 8 stores, as in asm copy. |
| 1675 | `    ('<code>asmcopy_c_reg</code>', 'as <code>asmcopy_c</code>, but with the registers q0 to q15, as in asm copy.'),` | Entry for `asmcopy_c_reg`: the same loop with the registers that asm copy uses. |
| 1676 | `    ('Loop offset, "modulo 64"', 'the address of the first instruction of a loop, as the remainder after division by 64 B. 64 B is the size of one cache line.'),` | Entry for the loop offset and "modulo 64": the address of the first instruction of a loop as the remainder after a division by 64 B, the size of one cache line. |
| 1677 | `    ('<code>-falign-loops=1</code>', 'an option of the C compiler gcc that stops the compiler from moving a loop start to an aligned address.'),` | Entry for the compiler option `-falign-loops=1`: it stops the compiler from moving a loop start to an aligned address. |
| 1678 | `    ('Process, launch, tag', 'a process is one start of <code>bwx</code>. It allocates its own buffers. A launch is that start by the run script. The tag of a process is its name in the run script, for example <code>8M-cpu2-p1</code>.'),` | Entry for process, launch and tag, with an example of a tag. |
| 1679 | `    ('Header line', 'the line that the run script writes before the output of each process. It has the tag, the load readings and the options.'),` | Entry for the header line: the line that the run script writes before the output of each process, and what it holds. |
| 1680 | `    ('Interval', 'one timed period of one loop inside a process, here at least 0.3 s. Before the timed period the loop runs once over the buffer without timing (the warm-up pass).'),` | Entry for the interval: one timed period of one loop inside a process, here at least 0.3 s. It also names the warm-up pass: before the timed period the loop runs once over the buffer without timing. |
| 1681 | `    ('Session', 'one run of all steps. The plan asks for two sessions some hours apart.'),` | Entry for the session: one run of all steps. It says that the plan asks for two sessions some hours apart. |
| 1682 | `    ('Rate', 'bytes moved per second, in GB/s (1 GB = 10<sup>9</sup> bytes). A copy counts the bytes read plus the bytes written.'),` | Entry for the rate: bytes moved per second in GB/s, with 1 GB as 1e9 bytes. A copy counts the bytes read plus the bytes written. |
| 1683 | `    ('Median', 'the middle value of a sorted list. With an even count it is the mean of the two middle values.'),` | Entry for the median, with the rule for an even count of values. |
| 1684 | `    ('L1, L2, SLC', 'the three cache levels of a core. SLC is the system-level cache (L3), shared by all cores. An 8 MiB buffer fits the SLC and does not fit L2. A 1 MiB buffer fits L2.'),` | Entry for the three cache levels of a core. It says which of them a buffer of 8 MiB and a buffer of 1 MiB fit. |
| 1685 | `    ('Prefetcher', 'the part of a core that fetches cache lines before the loop asks for them.'),` | Entry for the prefetcher: the part of a core that fetches cache lines ahead of the loop. |
| 1686 | `    ('Level', 'asm read at 8 MiB runs at one of two rates: a lower one (about 67 to 69 GB/s in the sweep of 2026-11-02) or a higher one (about 70.5 to 71.7 GB/s). Which one occurs can differ between processes and can change inside a process.'),` | Entry for the level: the two rates of asm read at 8 MiB. The two rate ranges in the text are typed. By the text the lower range comes from a run of 2026-11-02. |
| 1687 | `    ('Reference interval', 'an interval of asm read at 8 MiB that is timed directly before or after a compared pair. It shows the level at that time.'),` | Entry for the reference interval: an asm read interval at 8 MiB that is timed directly before or after a compared pair. |
| 1688 | `    ('Low, high, between', 'the provisional level labels of an asm read interval at 8 MiB: below 69 GB/s, above 70.5 GB/s, or neither. The analysis script prints "changing" for "between".'),` | Entry for the labels low, high and between. The two limits of 69 and 70.5 GB/s are typed in this line. Other lines print them from `LOW` and `HIGH`. The entry also says that the analysis script prints "changing" for "between". |
| 1689 | `    ('Stable process', 'a process whose reference intervals all have one label, low or high. Only a stable process gives a value to a decision at 8 MiB.'),` | Entry for the stable process: a process whose reference intervals all have one label. |
| 1690 | `    ('Group', 'the processes of one size, one variant or one build that are compared together. A level group of a counter table is the intervals of one CPU, one loop and one label.'),` | Entry for the group of processes, and for the level group of a counter table. |
| 1691 | `    ('Pair, pair value', 'two neighbouring intervals of two loops between the same two reference intervals, and the rate of the first loop of "X minus Y" minus the rate of the second.'),` | Entry for the pair (two neighbouring intervals of two loops between the same two reference intervals) and for the pair value (the rate of the first loop minus the rate of the second). |
| 1692 | `    ('d, e', 'the two values of one process. d is the median of its pair values of the two compared loops. e is the median of its pair values of the two copies of one loop.'),` | Entry for `d` and `e`, the two values of one process: the median of its pair values of the two compared loops, and the median of its pair values of the two copies of one loop. |
| 1693 | `    ('A/A control, A/A spread', 'a loop that exists twice in the program under two names. The A/A spread of a CPU is the largest absolute e of its processes. It shows how much two equal loops differ.'),` | Entry for the A/A control (one loop that exists twice under two names) and for the A/A spread (the largest absolute `e` of the processes of a CPU). |
| 1694 | `    ('Resolved', 'the plan\'s word for a difference whose median is larger than the A/A spread and that has one sign in all processes. It needs 3 processes on a CPU, and 2 such CPUs with the same sign. "(-)" and "(+)" give the sign.'),` | Entry for the word "resolved", with the 3 processes per CPU and the 2 CPUs that it needs, and the meaning of the signs in brackets. |
| 1695 | `    ('The five words', '"rejected" (the bounded prediction failed in both sessions), "not rejected", "not observed" (an event that the test could have shown did not occur), "not resolved" (the difference is inside the A/A spread), "not tested".'),` | Entry for the five words of rule 11, each with its meaning. |
| 1696 | `    ('Bounded prediction', 'the one statement of a hypothesis that a step tests, as the plan words it.'),` | Entry for the bounded prediction: the one statement of a hypothesis that a step tests. |
| 1697 | `    ('Description, no decision', 'values that this page computes for all processes without level labels. They are given next to the rule. They never change a word of the rule.'),` | Entry for "description, no decision": values that the generated page computes for all processes without level labels, and that never change a word of the rule. |
| 1698 | `    ('THP, 2 MiB pages, <code>--no-thp</code>', 'Linux can back memory with pages of 2 MiB instead of 4 KiB (transparent huge pages, THP). With <code>--no-thp</code> the benchmark asks for 4 KiB pages.'),` | Entry for THP, the pages of 2 MiB and the option `--no-thp`. |
| 1699 | `    ('Huge-page coverage, <code>kB_huge</code>, <code>kB_total</code>', 'how many kB of the buffer are backed by 2 MiB pages, of how many kB in total. "Full" means all, "none" means 0 kB.'),` | Entry for the huge-page coverage and the two values `kB_huge` and `kB_total`, with the meaning of "full" and "none". |
| 1700 | `    ('<code>thp_collapse_alloc</code>, <code>pgmigrate_success</code>', 'two counters of <code>/proc/vmstat</code> for the whole system. The first counts huge pages that Linux built from small pages. The second counts pages that Linux moved.'),` | Entry for the two counters `thp_collapse_alloc` and `pgmigrate_success` of `/proc/vmstat`. |
| 1701 | `    ('Page state', 'the huge-page coverage of the buffer and the counters of <code>/proc/vmstat</code>, read before an interval.'),` | Entry for the page state: the huge-page coverage of the buffer and the counters of `/proc/vmstat`, read before an interval. |
| 1702 | `    ('Case (a), case (b)', 'the two outcomes of step B4 that contradict H3a. Case (a): one CPU has at least 10 low and at least 10 high intervals with full coverage. Case (b): the same with no huge page.'),` | Entry for the cases (a) and (b) of step B4, each with its counts of 10 low and 10 high intervals. |
| 1703 | `    ('Counter, PMU', 'a hardware event counter of a core, read with the Linux call <code>perf_event_open</code>. PMU is the counter unit of the core.'),` | Entry for the counter and the PMU, the counter unit of the core. |
| 1704 | `    ('<code>l1d_refill</code>, <code>l2d_refill</code>, <code>ll_miss_rd</code>', 'the event names of the core for a line that is brought into the L1 data cache, into the L2 cache, and for a read that misses the last cache level.'),` | Entry for the three event names of the refills and of the read miss. |
| 1705 | `    ('Per line', 'a count divided by the number of 64 B lines that the interval moved.'),` | Entry for "per line": a count divided by the number of lines of 64 B that the interval moved. |
| 1706 | `    ('Clock', 'cycles of the interval divided by the CPU time of the thread in that interval, in GHz.'),` | Entry for the clock: the cycles of the interval divided by the CPU time of the thread in that interval, in GHz. |
| 1707 | `    ('Load, runnable tasks, waited', 'the Linux 1-minute load average (the average count of tasks that run or wait to run), the count of tasks that can run at one moment, and the time the script waited for at most 2 runnable tasks before a launch.'),` | Entry for the load, the runnable tasks and the wait before a launch. |
| 1708 | `    ('B1', 'step: new C copy against asm copy with the A/A pair, sizes 4, 8, 16, 32 MiB, CPUs 0, 2, 41, 94, 4 processes each.'),` | Entry for step B1, with its typed sizes, CPUs and count of processes. |
| 1709 | `    ('B2', 'step: the three variants <code>asmcopy_c</code>, <code>asmcopy_c_add</code>, <code>asmcopy_c_reg</code> against asm copy, at 8 MiB.'),` | Entry for step B2: the three assembly variants against asm copy, at 8 MiB. |
| 1710 | `    ('B3', 'step: new C copy against asm copy with both loops at offset 0, 36 or 52 modulo 64, at 8 MiB.'),` | Entry for step B3: new C copy against asm copy with both loops at one loop offset, 0, 36 or 52, at 8 MiB. |
| 1711 | `    ('B4', 'step: asm read at 8 MiB for 200 intervals with the page state, CPUs 2 and 41, half of the processes with <code>--no-thp</code>.'),` | Entry for step B4, with its typed count of 200 intervals and its typed CPUs 2 and 41. |
| 1712 | `    ('B6', 'step: old read at 8 MiB and at 1 MiB with reference intervals, CPUs 2, 41, 94.'),` | Entry for step B6, with its typed CPUs 2, 41 and 94. |
| 1713 | `    ('B9', 'a step for question Q2 that runs 120 threads. It ran directly before B1. This page uses only its end time, for the system load.'),` | Entry for step B9, a step of question Q2 with 120 threads. By this typed text it ran directly before B1, and the generated page uses only its end time, for the system load. |
| 1714 | `    ('C1, C2', 'steps: the schedule of B4 and of B1 at 8 MiB with core counters.'),` | Entry for the steps C1 and C2: the schedules of B4 and of B1 at 8 MiB with core counters. |
| 1715 | `    ('D2', 'step of Part D: the physical addresses of the buffer pages. Not run.'),` | Entry for step D2 of Part D, with the typed remark that it was not run. |
| 1716 | `    ('H1', 'hypothesis: old read is limited inside the core at every cache size, and its rate at 8 MiB does not depend on the level of the load-only loop.'),` | Entry for H1, as the plan words it. |
| 1717 | `    ('H2', 'hypothesis: the low level can change to the high level while the stream runs, and the high level can stay for the next process.'),` | Entry for H2: the low level can change to the high level while the loop runs, and the high level can stay for the next process. |
| 1718 | `    ('H3a', 'hypothesis: huge-page coverage decides the level. The low level is a buffer that is not fully on 2 MiB pages.'),` | Entry for H3a: huge-page coverage decides the level. |
| 1719 | `    ('H3b', 'hypothesis: the physical address of the pages decides the level.'),` | Entry for H3b: the physical address of the pages decides the level. |
| 1720 | `    ('H4', 'hypothesis: the copy difference does not come from the kernel code. It comes from something that differs between processes.'),` | Entry for H4: the copy difference comes from something that differs between processes, and not from the kernel code. |
| 1721 | `    ('H5', 'hypothesis: the copy difference comes from the instruction order of the C loop.'),` | Entry for H5: the copy difference comes from the instruction order of the C loop. |
| 1722 | `    ('H6', 'hypothesis: the copy difference comes from the address of the loop (36 against 52 modulo 64).'),` | Entry for H6: the copy difference comes from the address of the loop. |
| 1723 | `    ('est.', 'an estimate, not a measurement.'),` | Entry for `est.`: an estimate, not a measurement. |
| 1724 | `]` | Ends the list. |

### Function `main_table`: the table of the main numbers (lines 1727 to 1813)

| Line | Source | Explanation |
|---:|---|---|
| 1727 | `def main_table(D, R):` | Starts the function `main_table`. It builds the table that stands near the top of the generated page. |
| 1728 | `    """The main numbers: one row per step, one column per session. Every cell is built from computed values."""` | Docstring: the main numbers: one row per step, one column per session. Every cell is built from computed values. |
| 1729 | `    rows = []` | `rows`: the rows of the table, empty at the start. |
| 1731 | `    def cells(fn):` | Starts the inner function `cells`. It applies one cell function to every session. |
| 1732 | `        out = []` | `out`: the cell texts, empty at the start. |
| 1733 | `        for name in D['names']:` | Loop over the sessions. |
| 1734 | `            out.append(fn(D['sessions'][name]) or '-')` | Appends the text that `fn` gives for the session. An empty text becomes `-`. |
| 1735 | `        return out` | Returns the cell texts. |
| 1737 | `    def b1(x):` | Starts the inner function `b1`: the cell of step B1. |
| 1738 | `        G = x['pairs']['B1']` | `G`: the described groups of B1 of the session. |
| 1739 | `        if not G:` | Tests whether there is none. |
| 1740 | `            return ''` | Then the cell is empty. |
| 1741 | `        res, t = x['res'].get('B1', {}).get('groups', {}), []` | `res`: the groups of B1 in the analysis result. `t`: the text lines of the cell, empty at the start. |
| 1742 | `        for k in sorted(G, key=lambda k: G[k]['size']):` | Loop over the groups in the order of their buffer sizes. |
| 1743 | `            meds = [v['median_d'] for v in G[k]['per_cpu'].values()]` | `meds`: the median `d` of each CPU of the group. |
| 1744 | `            lab = res.get(k, {}).get('labels', {})` | `lab`: the results of the rule for the group, per label. |
| 1745 | `            if G[k]['size'] == 8 * MIB:` | Tests whether the group is the one at 8 MiB. |
| 1746 | `                w = sorted({v['decision'] + ab.sign_txt(v['sign']) for v in lab.values()})` | `w`: the words of the rule over the labels, each with its sign, each once, in sorted order. |
| 1747 | `                t.append(f'<b>8 MiB: {rng(min(meds), max(meds), signed=True)} GB/s</b> (description, no decision). Rule at 8 MiB: {", ".join(w)}.')` | Appends the text of 8 MiB: in bold the range of the CPU medians in GB/s, then the mark that this is a description and no decision, then the words of the rule at 8 MiB. |
| 1748 | `            else:` | The next lines run for every other size. |
| 1749 | `                r = lab.get('none')` | `r`: the result of the rule under the label `none`, or `None`. |
| 1750 | `                t.append(f'{G[k]["size"]//MIB} MiB: {rng(min(meds), max(meds), signed=True)} GB/s. Rule: {r["decision"] + ab.sign_txt(r["sign"]) if r else "-"}.')` | Appends the text of the size: the size in MiB, the range of the CPU medians in GB/s, and the word of the rule with its sign, or `-`. |
| 1751 | `        return 'Median d per CPU (new C copy minus asm copy).<br>' + '<br>'.join(t)` | Returns the cell: a first text line that names the value (the median `d` per CPU, new C copy minus asm copy), then the lines of `t`. |
| 1753 | `    def variants(step):` | Starts the inner function `variants`. It returns a cell function for step B2 or B3. |
| 1754 | `        def f(x):` | Starts that cell function `f`. |
| 1755 | `            G = x['pairs'][step]` | `G`: the described groups of the step of the session. |
| 1756 | `            t = []` | `t`: the text lines of the cell, empty at the start. |
| 1757 | `            for k in sorted(G):` | Loop over the groups in the order of their names. |
| 1758 | `                meds = [v['median_d'] for v in G[k]['per_cpu'].values()]` | `meds`: the median `d` of each CPU of the group. |
| 1759 | `                t.append(f'{e(k)}: {rng(min(meds), max(meds), signed=True)} GB/s.')` | Appends one text line: the group and the range of the CPU medians in GB/s. |
| 1760 | `            return 'Median d per CPU against asm copy (description, no decision).<br>' + '<br>'.join(t) if t else ''` | Returns the cell: a first text line that names the value (the median `d` per CPU against asm copy) with the description mark, then the lines of `t`. Without a group the cell is empty. |
| 1761 | `        return f` | Returns the cell function. |
| 1763 | `    def b4(x):` | Starts the inner function `b4`: the cell of step B4. |
| 1764 | `        if not x['b4']:` | Tests whether the session has no process of B4. |
| 1765 | `            return ''` | Then the cell is empty. |
| 1766 | `        t = []` | `t`: the text lines of the cell, empty at the start. |
| 1767 | `        for c, v in x['res']['B4']['per_cpu'].items():` | Loop over the CPUs of the analysis result of B4. |
| 1768 | `            full = [p for p in x['b4'] if p['cpu'] == c and p['cov']['full'] == len(p['rates'])]` | `full`: the processes of this CPU that had full huge-page coverage before every interval. |
| 1769 | `            s = f'CPU {c}: ' + (f'{pl(len(full), "process", "processes")} with full huge-page coverage, medians {rng(min(p["median"] for p in full), max(p["median"] for p in full))} GB/s. ' if full else '')` | `s`: the text of the CPU. When `full` has processes, it gives their count and the range of their median rates in GB/s. |
| 1770 | `            f = x['b4_cases'].get(c)` | `f`: the facts of `b4_case_facts` for the CPU, or `None`. |
| 1771 | `            if v['cases']:` | Tests whether the CPU has a case. |
| 1772 | `                s += f'Case ({") and (".join(v["cases"])}) by the rule' + (', which depends on the provisional limits.' if f and f['label_dependent'] else '. This contradicts H3a in this session.')` | Then the cases are named, by the rule. For a case that depends on the limits the text says so. For any other case it says that this contradicts H3a in this session. |
| 1773 | `            else:` | The next line runs for a CPU without a case. |
| 1774 | `                s += 'No case.'` | Adds the words `No case.` |
| 1775 | `            t.append(s)` | Appends the text of the CPU. |
| 1776 | `        return '<br>'.join(t)` | Returns the cell: one text line per CPU. |
| 1778 | `    def b6(x):` | Starts the inner function `b6`: the cell of step B6. |
| 1779 | `        g = x['b6']` | `g`: the description of B6 of the session. |
| 1780 | `        if not g:` | Tests whether it is missing. |
| 1781 | `            return ''` | Then the cell is empty. |
| 1782 | `        pc = g['per_cpu'].values()` | `pc`: the values per CPU. |
| 1783 | `        sz = x['res']['B6']['size']['labels']['none']` | `sz`: the result of part 2 of the rule in the analysis. |
| 1784 | `        return (f'Median d per CPU (old read at 8 MiB minus old read at 1 MiB): {rng(min(v["median_d"] for v in pc), max(v["median_d"] for v in pc), signed=True)} GB/s. Rule: {sz["decision"] + ab.sign_txt(sz["sign"])}.<br>'` | Starts the cell with its first text line: the range over the CPUs of the median `d` (old read at 8 MiB minus old read at 1 MiB) in GB/s, and the word of the rule with its sign. |
| 1785 | `                f'With old read at 8 MiB timed first: {rng(min(v["d_first"] for v in pc), max(v["d_first"] for v in pc), signed=True)} GB/s. Timed second: {rng(min(v["d_second"] for v in pc), max(v["d_second"] for v in pc), signed=True)} GB/s.')` | Ends the cell with its second text line: the range of `d_first` (old read at 8 MiB timed first) and the range of `d_second` (timed second), in GB/s. |
| 1787 | `    def c1(x):` | Starts the inner function `c1`: the cell of step C1. |
| 1788 | `        r = x['res'].get('C1')` | `r`: the result of the analysis for C1, or `None`. |
| 1789 | `        if not r or not r['groups']:` | Tests whether it is missing or has no group. |
| 1790 | `            return ''` | Then the cell is empty. |
| 1791 | `        cy = [g['median_cycles_per_line'] for g in r['groups'] if g['median_cycles_per_line'] is not None]` | `cy`: the median count of cycles per line of each group that has one. |
| 1792 | `        lv = sorted({'between' if g['level'] == 'changing' else g['level'] for g in r['groups']})` | `lv`: the levels of the groups, each once, in sorted order. The level `changing` is named `between`. |
| 1793 | `        return f'asm read: {rng(min(cy), max(cy))} cycles per line. Levels seen: {", ".join(lv)}.' if cy else ''` | Returns the cell: the range of the cycles per line of asm read, and the levels that were seen. Without a cycle value the cell is empty. |
| 1795 | `    def c2(x):` | Starts the inner function `c2`: the cell of step C2. |
| 1796 | `        r = x['res'].get('C2')` | `r`: the result of the analysis for C2, or `None`. |
| 1797 | `        if not r or not r['groups']:` | Tests whether it is missing or has no group. |
| 1798 | `            return ''` | Then the cell is empty. |
| 1799 | `        a = [g['median_cycles_per_line'] for g in r['groups'] if g['entry'] == 'copy' and g['median_cycles_per_line'] is not None]` | `a`: the median count of cycles per line of each group of the kernel `copy`. |
| 1800 | `        b = [g['median_cycles_per_line'] for g in r['groups'] if g['entry'] == 'asmcopy' and g['median_cycles_per_line'] is not None]` | `b`: the same for each group of `asmcopy`. |
| 1801 | `        return f'Cycles per line: new C copy {rng(min(a), max(a))}, asm copy {rng(min(b), max(b))} (description).' if a and b else ''` | Returns the cell: the range of the cycles per line of new C copy and of asm copy, with the description mark. The cell is empty when one of the two is missing. |
| 1803 | `    for step, what, fn in (('B1', 'copy loops, 4 sizes', b1), ('B2', 'three assembly variants, 8 MiB', variants('B2')), ('B3', 'three loop offsets, 8 MiB', variants('B3')),` | Loop over the seven steps. Each has a short text on what it compares and its cell function. This line holds B1 (the copy loops at 4 sizes), B2 (three assembly variants at 8 MiB) and B3 (three loop offsets at 8 MiB). |
| 1804 | `                           ('B4', 'asm read, 200 intervals', b4), ('B6', 'old read, 8 MiB and 1 MiB', b6), ('C1', 'counters, schedule of B4', c1), ('C2', 'counters, schedule of B1', c2)):` | Continues line 1803: B4 (asm read, 200 intervals), B6 (old read at 8 MiB and at 1 MiB), C1 (counters with the schedule of B4) and C2 (counters with the schedule of B1). |
| 1805 | `        c = cells(fn)` | `c`: the cells of the step, one per session. |
| 1806 | `        if any(v != '-' for v in c):` | Tests whether at least one session has a cell text. |
| 1807 | `            rows.append(f'<tr><td>{step}</td><td>{what}</td>' + ''.join(f'<td>{v}</td>' for v in c) + '</tr>')` | Then the table row is appended: the step, the short text and the cells. |
| 1808 | `    if not rows:` | Tests whether the table has no row. |
| 1809 | `        return ''` | Then an empty text is returned. |
| 1810 | `    return ('<div class="tw"><table class="pt hy"><tr><th style="width:6%">Step</th><th style="width:17%">What it compares</th>' + ''.join(f'<th>Session {e(n)}</th>' for n in D['names']) + '</tr>' + ''.join(rows) + '</table></div>'` | Starts the result: the table with its header row. The column of the step has 6 % of the width, the column "What it compares" has 17 %, and one column per session follows. Then come the rows. |
| 1811 | `            '<p class="cap">d is a difference of rates inside one process. A negative d means that the first loop is slower. The sections below give the charts, the processes and the A/A spread of every value ' + frefs(R, D, *Q1_STEPS) + '</p>')` | Ends the result with a caption: `d` is a difference of rates inside one process, and a negative `d` means that the first loop is slower. The sections below give the charts, the processes and the A/A spread of every value. The citations of the result folders of all seven steps follow. |

### `limits_fit`, `short_version`, `h1_line`, `session_gap`: the top of the generated page (lines 1814 to 1866)

| Line | Source | Explanation |
|---:|---|---|
| 1814 | `def limits_fit(D):` | Starts the function `limits_fit`. It says whether the provisional level limits fit the reference rates of the input. |
| 1815 | `    """True if fewer than half of the processes with reference intervals are stable under the provisional limits. None without data."""` | Docstring: by its words the result is true if fewer than half of the processes with reference intervals are stable under the provisional limits, and `None` without data. The code does the opposite (line 1818): it gives true when at least half of them are stable. |
| 1816 | `    rr = [r for x in D['sessions'].values() for r in x['refs'] if r['kind'] == 'reference intervals']` | `rr`: the rows of the kind `reference intervals` of all sessions (lines 404 to 406). |
| 1817 | `    n = sum(r['n_procs'] for r in rr)` | `n`: the count of processes in these rows. |
| 1818 | `    return None if not n else sum(r['n_stable_low'] + r['n_stable_high'] for r in rr) * 2 >= n` | Returns `None` when `n` is 0. In every other case it returns true when twice the count of stable processes is at least `n`. So true means that at least half of the processes are stable: the limits fit. The one caller, line 1841, reads the value in this sense. |
| 1821 | `def short_version(D):` | Starts the function `short_version`. It writes the text of the paragraph "Short version" of the generated page. |
| 1822 | `    """At most three sentences, built from computed values."""` | Docstring: at most three sentences, built from computed values. |
| 1823 | `    n = len(D['names'])` | `n`: the count of sessions. |
| 1824 | `    recs = [r for x in D['sessions'].values() for r in x['pairs']['B1'].get('8M', {}).get('recs', [])]` | `recs`: the records of all processes of B1 at 8 MiB, over the sessions. |
| 1825 | `    if not recs:` | The next lines run when there is no such record. |
| 1826 | `        steps = sorted({st for x in D['sessions'].values() for st in x['steps']}, key=Q1_STEPS.index)` | `steps`: the steps that have a process in at least one session, in the order of `Q1_STEPS`. |
| 1827 | `        return (f'This page reports the one-thread steps {", ".join(steps) if steps else "(none in the input)"} of {pl(n, "test session", "test sessions")}. '` | Starts the result for this case with one sentence: which one-thread steps the page reports, and of how many test sessions. |
| 1828 | `                f'{ID} for the copy comparison at 8 MiB: no process of step B1 at 8 MiB is in the input.')` | Ends that result with a second sentence: `Insufficient data` for the copy comparison at 8 MiB, with the reason that no process of step B1 at 8 MiB is in the input. |
| 1829 | `    neg = sum(1 for r in recs if r['d'] < 0)` | `neg`: the count of processes of B1 at 8 MiB with `d` below 0. In these `copy` was slower than `asmcopy`. |
| 1830 | `    pcs = [v for x in D['sessions'].values() for v in x['pairs']['B1'].get('8M', {}).get('per_cpu', {}).values()]` | `pcs`: the values per CPU of B1 at 8 MiB, one entry per session and CPU. |
| 1831 | `    md, pct = [v['median_d'] for v in pcs], [v['pct'] for v in pcs]` | `md`: the median `d` of each entry. `pct`: its median `d` in percent of the rate of `asmcopy` (line 232). |
| 1832 | `    if max(md) < 0:` | Tests whether every median `d` is below 0. |
| 1833 | `        size = f'median per CPU: {rng(-max(md), -min(md))} GB/s slower, which is {rng(-max(pct), -min(pct), 1)} %'` | Then `size` is a text with the range of the absolute medians in GB/s and the word "slower", and the range of the percentages with 1 decimal. |
| 1834 | `    else:` | The next line runs when at least one median `d` is 0 or above. |
| 1835 | `        size = f'median difference per CPU: {rng(min(md), max(md), signed=True)} GB/s'` | Then `size` is a text with the range of the median differences with their signs, in GB/s. |
| 1836 | `    st = sum(1 for r in recs if r['stable'])` | `st`: the count of stable processes among `recs`. |
| 1837 | `    h4 = sorted({r['word'] for r in D['hyp'] if r['h'].startswith('H4')})` | `h4`: the words of the rows of H4 in the hypothesis table, each once, in sorted order. |
| 1838 | `    s1 = (f'With one thread and an 8 MiB buffer, the new C copy loop was slower than the assembly copy loop in {neg} of {len(recs)} program runs over {pl(n, "test session", "test sessions")} ({size}). ')` | `s1`: sentence 1. It says in how many of the program runs of B1 at 8 MiB the new C copy loop was slower than the assembly copy loop, over how many test sessions, with the text `size` in brackets. A program run is a process. |
| 1839 | `    s2_ = (f'The agreed decision rule could use only {st} of these {len(recs)} runs, and its formal result for the copy question is "{", ".join(h4)}"' + (' (one session cannot give "rejected")' if n < 2 else '') + '. ')` | `s2_`: sentence 2. It says how many of these runs the agreed decision rule could use, and gives the words of `h4` as its formal result for the copy question. With one session it adds that one session cannot give "rejected". |
| 1840 | `    fit = limits_fit(D)` | `fit`: the result of `limits_fit`. |
| 1841 | `    s3 = ('The two rate limits that the rule uses do not fit the data, and the user must decide whether to change them.' if fit is False else` | `s3`: sentence 3. When `fit` is false, it says that the two rate limits of the rule do not fit the data, and that the user must decide whether to change them. |
| 1842 | `          'The two rate limits that the rule uses are provisional, and the user must decide whether to keep them.')` | In every other case, also without data, it says that the two rate limits are provisional, and that the user must decide whether to keep them. |
| 1843 | `    return s1 + s2_ + s3` | Returns the three sentences as one text. |
| 1846 | `def h1_line(D):` | Starts the function `h1_line`. It writes one paragraph on H1 that stands below the Short version. |
| 1847 | `    """The line under the Short version: what the word of H1 consists of."""` | Docstring: the line under the Short version says what the word of H1 consists of. |
| 1848 | `    r = next((r for r in D['hyp'] if r['h'] == 'H1'), None)` | `r`: the row of H1 in the hypothesis table, or `None`. |
| 1849 | `    q = b6_position(D)` | `q`: the values of `b6_position`. |
| 1850 | `    if not r or not q or r['word'] == 'not tested':` | Tests whether the row or the values are missing, or the word is `not tested`. |
| 1851 | `        return ''` | Then an empty text is returned. |
| 1852 | `    a = sorted(abs(v) for v in q['first'])` | `a`: the absolute values of `d_first` of all CPUs, in rising order. |
| 1853 | `    b = sorted(abs(v) for v in q['second'])` | `b`: the absolute values of `d_second` of all CPUs, in rising order. |
| 1854 | `    return (f'<p>H1 (the rate of the old read loop does not depend on the buffer size) gets the word "{e(r["word"])}" by the rule. '` | Starts the paragraph: H1 in plain words (the rate of the old read loop does not depend on the buffer size), and the word that it gets by the rule. |
| 1855 | `            f'The measured difference depends on which loop ran directly before. Its absolute value is {rng(a[0], a[-1])} GB/s in one order of the two loops and {rng(b[0], b[-1])} GB/s in the other. '` | Continues line 1854: a typed sentence says that the measured difference depends on which loop ran directly before. No code tests that here. The next sentence gives the range of `a` as the absolute value in one order of the two loops, and the range of `b` as the value in the other order, in GB/s. |
| 1856 | `            'The hypothesis table and section B6 give the details.</p>')` | Ends the paragraph with a pointer to the hypothesis table and to section B6. |
| 1859 | `def session_gap(D):` | Starts the function `session_gap`. It gives the time between the starts of the sessions. |
| 1860 | `    t = [(n, x['t_start']) for n, x in D['sessions'].items() if x['t_start'] is not None]` | `t`: pairs of session name and start time in seconds (line 422), for the sessions that have a start time. |
| 1861 | `    if len(t) < 2:` | Tests whether fewer than 2 sessions have a start time. |
| 1862 | `        return None` | Then `None` is returned. |
| 1863 | `    gap = max(v for _, v in t) - min(v for _, v in t)` | `gap`: the latest start time minus the earliest, in seconds. |
| 1864 | `    return gap, time.strftime('%Y-%m-%d %H:%M', time.gmtime(min(v for _, v in t))), time.strftime('%Y-%m-%d %H:%M', time.gmtime(max(v for _, v in t)))` | Returns three values: `gap`, and the earliest and the latest start time as text with the date, the hour and the minute in UTC. |

### Function `build`: put the whole page together (lines 1867 to 1950)

| Line | Source | Explanation |
|---:|---|---|
| 1867 | `def build(D, banner=None, offsets=None):` | Starts the function `build`. It puts the generated page together from the values of `D`. `banner` is a text for a box at the top. `offsets` is the path of the file of loop offsets. |
| 1868 | `    R = Refs()` | `R`: a new, empty reference list. |
| 1869 | `    R.add('plan', '<code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md</code>: the questions Q1 and Q2, the hypotheses H1 to H11, rules 1 to 11, steps B1 to B10 and C1 to C3, Part D.')` | Stores the reference with the key `plan`: the path of `plan.md` in the working tree of the author, and what the file holds: the questions Q1 and Q2, the hypotheses H1 to H11, the rules 1 to 11, the steps B1 to B10 and C1 to C3, and Part D. |
| 1870 | `    R.add('handoff', '<code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md</code>: sections B.3 (output rows), B.6 (page state), B.8 (counters), B.9 (sequences of each step), B.10 (numeric decision rules).')` | Stores the reference `handoff`: the path of `handoff.md` and its sections on the output rows (B.3), the page state (B.6), the counters (B.8), the sequences of each step (B.9) and the numeric decision rules (B.10). |
| 1871 | `    R.add('analyze', '<code>/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/analyze_bwx.py</code>: the parser and the decision analysis. This page imports its functions.')` | Stores the reference `analyze`: the path of `analyze_bwx.py`, the parser and the decision analysis whose functions the page builder imports. |
| 1872 | `    R.add('decide', '<code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/decide.py</code>: the decision rules of handoff B.10 as code, with the two level limits.')` | Stores the reference `decide`: the path of `decide.py`, the decision rules of section B.10 as code, with the two level limits. |
| 1873 | `    R.add('devscripts', '<code>/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/DEVIATIONS-scripts.md</code>: choices of the run script and of the analysis (points A12 to A16, A19, A20, A22, A30, A32).')` | Stores the reference `devscripts`: the path of the note `DEVIATIONS-scripts.md` on the choices of the run script and of the analysis, with the numbers of ten of its points. |
| 1874 | `    R.add('offsets', '<code>/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/crb-build-2/offsets.tsv</code> (loop start of every kernel in the four builds) and <code>build.txt</code> in the same folder (compiler flags, <code>EXTRA_bwx_o52=-falign-loops=1</code>).')` | Stores the reference `offsets`: the path of the file `offsets.tsv` of the build record `crb-build-2` (the loop start of every kernel in the four builds) and of `build.txt` beside it (the compiler flags). |
| 1875 | `    R.add('runscript', '<code>/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/run_bwx.sh</code>: the launches, the wait before each launch, the header line of each process, <code>launches.txt</code> and <code>env.txt</code>.')` | Stores the reference `runscript`: the path of `run_bwx.sh`, with what it does: the launches, the wait before each launch, the header line of each process, `launches.txt` and `env.txt`. |
| 1876 | `    R.add('short', '<code>/home/jhan/workspace/titan/cache-perf/crb/results/SHORT-20261113T214338Z/SHORT.csv</code>: the short run of every sequence before session 1.')` | Stores the reference `short`: the path of the csv file of the short run of every sequence before session 1. |
| 1877 | `    R.add('self', '<code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partBC-analysis/make_q1_html.py</code> and <code>test_q1.py</code>: the script that built this page, and its tests.')` | Stores the reference `self`: the paths of this script and of `test_q1.py`. |
| 1878 | `    for name in D['names']:` | Loop over the sessions. |
| 1879 | `        x = D['sessions'][name]` | `x`: the values of the session. |
| 1880 | `        for f in x['folders'] + x['other']:` | Loop over all folders of the session, with and without processes of Q1. |
| 1881 | `            R.add(('folder', name, f['name']), f"<code>{e(f['path'])}/</code>: " + ', '.join(f'<code>{st}.csv</code>' for st in f['steps']) + f", <code>env.txt</code>, <code>launches.txt</code>, <code>stderr.txt</code>. Session {e(name)}, {'step' if len(f['steps']) == 1 else 'steps'} {', '.join(f['steps'])}.")` | Stores one reference per folder. Its key holds the word `folder`, the session and the folder name. Its text holds the path, the csv file of each step in it, the three other files, the session and the steps. |
| 1882 | `    R('plan', 'handoff', 'analyze', 'decide')` | Cites four references and does not use the returned text: the plan, the handoff note, `analyze_bwx.py` and `decide.py`. So these get the numbers 1 to 4. |
| 1883 | `    for name in D['names']:` | Loop over the sessions. |
| 1884 | `        for st in Q1_STEPS:` | Loop over the seven steps of Q1. |
| 1885 | `            fref(R, D, name, st)` | Cites the result folders of the step and does not use the returned text. So these folders get the next numbers, in the order of the sessions and the steps. |
| 1886 | `    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',` | Starts `o`, the pieces of the page. This line holds the start of the HTML document: the document type, the language English, the character set UTF-8 and the setting that fits the page to the width of the screen. |
| 1887 | `         '<title>Parts B and C, question Q1: result</title>', f'<style>{CSS}</style></head><body>']` | Continues line 1886: the title of the browser tab, the style sheet `CSS` inside the page, the end of the head and the start of the body. |
| 1888 | `    if banner:` | Tests whether a banner text is given. |
| 1889 | `        o.append(f'<p class="banner">{e(banner)}</p>')` | Then a paragraph of the class `banner` with that text is added. The style sheet gives it an orange frame and bold text. |
| 1890 | `    o.append('<h1>Parts B and C, question Q1: one thread at 8 MiB</h1>')` | Adds the main heading: Parts B and C, question Q1, one thread at 8 MiB. |
| 1891 | `    o.append(f'<p class="take"><b>Short version.</b> {short_version(D)}</p>')` | Adds a highlighted paragraph with the words `Short version.` in bold and the text of `short_version`. |
| 1892 | `    o.append(h1_line(D))` | Adds the paragraph of `h1_line`. An empty text is left out in line 1948. |
| 1893 | `    mt = main_table(D, R)` | `mt`: the table of `main_table`. |
| 1894 | `    if mt:` | Tests whether the table has content. |
| 1895 | `        o.append('<p><b>Main numbers of this page.</b> All values are in GB/s unless a unit is given.</p>' + mt)` | Then a paragraph is added in front of it: the heading of the main numbers, and that all values are in GB/s unless a unit is given. |
| 1896 | `    for name in D['names']:` | Loop over the sessions. |
| 1897 | `        x = D['sessions'][name]` | `x`: the values of the session. |
| 1898 | `        t = f'<p>Session {e(name)}: {pl(x["n_procs"], "process", "processes")} of the steps {", ".join(x["steps"]) if x["steps"] else "(none)"} in {pl(len(x["folders"]), "result folder", "result folders")} ' + R(*[('folder', name, f['name']) for f in x['folders']]) + '. '` | `t`: one paragraph per session: how many processes of which steps it holds, in how many result folders, with the citations of these folders. |
| 1899 | `        t += ('Every process is used. ' if x['n_used'] == x['n_procs'] else f'{x["n_procs"] - x["n_used"]} of them are not used, see the section on the system load. ')` | Continues `t`: that every process is used, or how many are not used, with a pointer to the section on the system load. |
| 1900 | `        if x['missing']:` | Tests whether steps of Q1 are missing in the session. |
| 1901 | `            t += f'{ID} for {", ".join(x["missing"])}: no process of {"this step is" if len(x["missing"]) == 1 else "these steps are"} in the input. A run of {"that step" if len(x["missing"]) == 1 else "those steps"} would give it. '` | Then `Insufficient data` is added for these steps: no process of them is in the input, and a run of them would give it. |
| 1902 | `        o.append(t + '</p>')` | Adds the paragraph. |
| 1903 | `    o.append('<h2 id="words">Words used here</h2><ul class="words">' + ''.join(f'<li><b>{k}</b>: {v}</li>' for k, v in WORDS) + '</ul>')` | Adds the section "Words used here" with the anchor `words`: a list with one item per entry of `WORDS`, the term in bold, a colon and the definition. |
| 1904 | `    o.append(sec_hyp(D, R))` | Adds the section of `sec_hyp`, the hypothesis table. |
| 1905 | `    o.append(sec_load(D, R))` | Adds the section of `sec_load`, the system load. |
| 1906 | `    o.append(sec_refs(D, R))` | Adds the section of `sec_refs`, the reference rate and the level limits. |
| 1907 | `    o.append(sec_howto(D, R))` | Adds the box of `sec_howto`. |
| 1908 | `    o.append(sec_b1(D, R))` | Adds the section of `sec_b1`. |
| 1909 | `    o.append(sec_variants(D, R, 'B2', 'B2: three assembly variants of the C copy loop against asm copy',` | Starts the call of `sec_variants` for step B2, with the heading of the section: three assembly variants of the C copy loop against asm copy. |
| 1910 | `                          '<p>Each variant replaces new C copy in the B1 sequence at 8 MiB. All three variants and asm copy have their loop at 52 modulo 64 ' + R('offsets') + '. '` | Continues line 1909 with the first paragraph, as typed text: what a variant replaces in the B1 sequence, and that all three variants and asm copy have their loop at the offset 52. It cites the file of loop offsets. |
| 1911 | `                          'H5 predicts that <code>asmcopy_c</code>, the assembly loop with the instruction order of the C loop, differs from asm copy by a resolved amount of the sign of B1 ' + R('plan') + '. '` | Continues line 1910 with the bounded prediction of H5: `asmcopy_c` differs from asm copy by a resolved amount with the sign of B1. A citation of the plan follows. |
| 1912 | `                          'The plan runs B2 only after a resolved difference in B1. B2 was run although B1 at 8 MiB is not formally resolved. This is a deviation. Its purpose is that the data exist if the level limits are revised.</p>',` | Ends the paragraph with typed text: the plan runs B2 only after a resolved difference in B1. B2 was run although B1 at 8 MiB is not formally resolved. This is a deviation. Its purpose: the data exist if the level limits are revised. No code tests here whether B1 is resolved in the input. |
| 1913 | `                          lambda k: f'{k} minus asm copy', lambda k: k))` | Ends the call with the two name functions: the name of `d` is the group and the words "minus asm copy", and the name of a group is its key. |
| 1914 | `    off = offsets_table(offsets)` | `off`: the folded table of the loop offsets, from `offsets_table`. |
| 1915 | `    o.append(sec_variants(D, R, 'B3', 'B3: new C copy and asm copy with both loops at one offset',` | Starts the call of `sec_variants` for step B3, with the heading of the section: new C copy and asm copy with both loops at one offset. |
| 1916 | `                          '<p>Three more builds place the loops of new C copy, asm copy and asm copy 2 at 0, 36 or 52 modulo 64. H6 predicts that the difference between the two loops changes by a resolved amount when both are at one offset ' + R('plan') + '. '` | Continues line 1915 with the first paragraph, as typed text: the three more builds with the copy loops at the offsets 0, 36 and 52, and the bounded prediction of H6 with a citation of the plan. |
| 1917 | `                          'The build <code>bwx_o52</code> uses the added compiler option <code>-falign-loops=1</code>. Without it gcc moved the C copy loop from offset 52 to offset 0 ' + R('offsets') + '. '` | Continues line 1916 with typed text on the build `bwx_o52`: it has the added compiler option `-falign-loops=1`, and the text says what the compiler gcc did without it. It cites the file of loop offsets. |
| 1918 | `                          'B3 was run although B1 at 8 MiB is not formally resolved, for the same reason as B2.</p>' + off,` | Ends the paragraph with typed text: B3 was run although B1 at 8 MiB is not formally resolved, for the same reason as B2. The table `off` follows. |
| 1919 | `                          lambda k: f'new C copy minus asm copy in {k}', lambda k: k))` | Ends the call with the two name functions: the name of `d` is "new C copy minus asm copy in" and the build, and the name of a group is its key. |
| 1920 | `    o.append(sec_b4(D, R))` | Adds the section of `sec_b4`. |
| 1921 | `    o.append(sec_b6(D, R))` | Adds the section of `sec_b6`. |
| 1922 | `    o.append(sec_c(D, R))` | Adds the section of `sec_c`. |
| 1923 | `    o.append('<h2 id="other">Deviations and decisions that concern this page</h2><ul>'` | Starts the section "Deviations and decisions that concern this page" with the anchor `other`. It is a list of typed text. |
| 1924 | `             '<li>Level limits. The limits of rule 5 of the plan were not changed. The section on the reference rate gives their strict result and the open decision.</li>'` | Item 1, on the level limits: the limits of rule 5 of the plan were not changed, and the section on the reference rate holds their strict result and the open decision. |
| 1925 | `             '<li>B2, B3 and C2 were run although B1 at 8 MiB is not formally resolved. The plan runs them only after a resolved difference in B1 ' + R('plan') + '.</li>'` | Item 2: B2, B3 and C2 were run although B1 at 8 MiB is not formally resolved. The plan runs them only after a resolved difference in B1, with a citation of the plan. No code tests here whether B1 is resolved in the input. |
| 1926 | `             '<li>H3a in the analysis script, corrected on 2026-11-14. Before, the script gave each session the result "not observed" when the two sessions had their case on different CPUs. '` | Starts item 3, typed text on the analysis script: its treatment of H3a was corrected on 2026-11-14. Before, the script gave each session the result "not observed" when the two sessions had their case on different CPUs. |
| 1927 | `             'Now the result of a session comes from that session alone. The word over the sessions still needs one CPU with a case in every session (points A13 and A32) ' + R('devscripts') + '.</li>'` | Ends item 3: now the result of a session comes from that session alone. The word over the sessions still needs one CPU with a case in every session, with the two points of the note on the deviations and a citation. |
| 1928 | `             '<li>H2. The plan gives H2 no bounded prediction in Parts B and C, so its word is "not tested". The level changes that B4 and C1 show are given as a description.</li>'` | Item 4, on H2: its word is "not tested" for lack of a bounded prediction in Parts B and C, and the level changes of B4 and C1 are given as a description. |
| 1929 | `             '</ul>')` | Closes the list. |
| 1930 | `    gap = session_gap(D)` | `gap`: the result of `session_gap`, or `None`. |
| 1931 | `    o.append('<h2 id="limits">Limits of this page</h2><ul>'` | Starts the section "Limits of this page" with the anchor `limits`. It is a list. |
| 1932 | `             '<li>The level limits (' f'{LOW:g}' ' and ' f'{HIGH:g}' ' GB/s) are provisional and are not validated against the reference rates of this page. Every word in the hypothesis table uses them unchanged. A description is not a decision.</li>'` | Item 1, on the level limits: they are provisional and not validated against the reference rates of the page, every word of the hypothesis table uses them unchanged, and a description is no decision. The two values come from `LOW` and `HIGH`. |
| 1933 | `             '<li>B1, B2 and B3 have 4 processes per CPU and group. The rule needs 3 stable processes on each of 2 CPUs. ' + stable_sentence(D) + ' So under the present limits this design could not give H4, H5 and H6 a word other than "not observed".</li>'` | Item 2: B1, B2 and B3 have 4 processes per CPU and group, and the rule needs 3 stable processes on each of 2 CPUs. The computed sentences of `stable_sentence` follow. The last sentence is typed: under the present limits this design could not give H4, H5 and H6 a word other than "not observed". |
| 1934 | `             '<li>The first reference interval of a process is the first timed interval after its start. The section on the reference rate gives the number of processes in which it has another label than the later ones.</li>'` | Item 3, on the first reference interval of a process: it is the first timed interval after the start, and the section on the reference rate counts the processes in which its label differs from the later ones. |
| 1935 | `             + (f'<li>The one-thread steps of the sessions started at {gap[1]} and {gap[2]} UTC, {gap[0] // 3600} h {gap[0] % 3600 // 60} min apart. So "two sessions" does not cover a different day or a restart of the machine.</li>' if gap else '')` | Item 4, only when `gap` exists: the two start times of the one-thread steps of the sessions in UTC, and the time between them in hours and minutes. A typed sentence follows: "two sessions" does not cover a different day or a restart of the machine. No code tests the size of the gap for that sentence. |
| 1936 | `             + '<li>The word for H3a depends on the same-CPU condition of the handoff, which step B4 of the plan does not have. The hypothesis table lists this as open for the user.</li>'` | Item 5, typed: the word for H3a depends on the same-CPU condition of the handoff note, which step B4 of the plan does not have. The hypothesis table lists this as open for the user. |
| 1937 | `             '<li>H3b is "not tested". Part D (counters that need root, physical addresses of the pages) was not run ' + R('plan') + '. This limit applies to every statement on the cause of the two levels.</li>'` | Item 6, typed: H3b is "not tested". Part D (counters that need root, physical addresses of the pages) was not run, with a citation of the plan. This limit applies to every statement on the cause of the two levels. |
| 1938 | `             '<li>The vmstat counters count for the whole system. No increase is no proof that the physical pages of the buffer stayed the same ' + R('plan') + '.</li>'` | Item 7, on the counters of `/proc/vmstat`: they count for the whole system, so a missing increase is no proof of unchanged physical pages of the buffer. It cites the plan. |
| 1939 | `             '<li>A thread that does not run on its CPU for a part of an interval is not flagged in a run without counters. This was found in the short run: one thread of a process with 120 threads had a CPU time of 87.2 % of its elapsed time, and its row has no flag ' + R('short') + '. '` | Starts item 8: a thread that does not run on its CPU for a part of an interval is not flagged in a run without counters. A typed sentence says that this was found in the short run, with a typed percentage and a citation of the short run. |
| 1940 | `             'B1, B2, B3, B4 and B6 ran without counters, so this page cannot exclude such an interval in them. The counter runs C1 and C2 give the CPU time of each interval.</li>'` | Ends item 8: B1, B2, B3, B4 and B6 ran without counters, so the page cannot exclude such an interval in them. The counter runs C1 and C2 give the CPU time of each interval. |
| 1941 | `             '<li>The event names of the counters are taken as the core names them. The section on the counters gives one observation that does not fit the names.</li>'` | Item 9, typed: the event names of the counters are taken as the core names them. The section on the counters gives one observation that does not fit the names. That observation is printed only for some inputs (lines 1648 to 1653). |
| 1942 | `             '<li>In step B6 the two loops of a pair are at different positions after the reference interval. Section B6 shows that the position changes the rate of old read at 8 MiB.</li>'` | Item 10, typed: in step B6 the two loops of a pair are at different positions after the reference interval. Section B6 shows that the position changes the rate of old read at 8 MiB. No code tests the second sentence here. |
| 1943 | `             f'<li>{ID}: the load during an interval. The script reads it only before each launch.</li>'` | Item 11: `Insufficient data` for the load during an interval. The script reads it only before each launch. |
| 1944 | `             '<li>The chart colours were not checked with the palette checker of the chart rules. Every chart also uses position, shape or a text label.</li>'` | Item 12, typed: the colors of the charts were not checked with the palette checker of the chart rules. Every chart also uses position, shape or a text label. |
| 1945 | `             '</ul>')` | Closes the list. |
| 1946 | `    o.append('<p class="cap">The script <code>make_q1_html.py</code> built this page, and <code>test_q1.py</code> tests it ' + R('self') + '.</p>')` | Adds a caption: this script built the page and `test_q1.py` tests it, with the citation `self`. |
| 1947 | `    o.append('<h2 id="refs">References</h2>' + R.html() + '</body></html>')` | Adds the section "References" with the anchor `refs`: the list of all references that were cited, in the order of their numbers. The line also closes the body and the document. |
| 1948 | `    return '\n'.join(t for t in o if t)` | Returns the page: all pieces that are not empty, with a line break between two pieces. |

### `offsets_table`, `make`, `main` and the start of the script (lines 1951 to 1993)

| Line | Source | Explanation |
|---:|---|---|
| 1951 | `def offsets_table(path):` | Starts the function `offsets_table`. It builds the folded table of the loop offsets for the section of B3. |
| 1952 | `    if not path or not os.path.exists(path):` | Tests whether no path is given or the file does not exist. |
| 1953 | `        return miss('The loop offsets of the builds: the file <code>offsets.tsv</code> was not found.')` | Then a block "Insufficient data" is returned: the file `offsets.tsv` with the loop offsets of the builds was not found. |
| 1954 | `    rows = [l.rstrip('\n').split('\t') for l in open(path)][1:]` | `rows`: the lines of the file, each split at the tab characters. The first line, which holds the column names, is left out. |
| 1955 | `    want = ('copy', 'asmcopy', 'asmcopy2', 'asmcopy_c', 'asmcopy_c_add', 'asmcopy_c_reg', 'asmread', 'oldread', 'oldread2')` | `want`: the nine kernels of the table, in the order of its rows. |
| 1956 | `    bins = list(dict.fromkeys(r[0] for r in rows))` | `bins`: the names of the builds (field 1 of each line), each once, in the order of the file. |
| 1957 | `    get = {(r[0], r[1]): r[5] for r in rows if len(r) >= 6}` | `get`: a dictionary from the pair of build and kernel (fields 1 and 2) to field 6 of the line. In the file of the test data field 6 is the column `loop_mod64`, the loop start modulo 64 [Ref9]. A line with fewer than 6 fields is left out. |
| 1958 | `    o = ['<details><summary>Loop start of every kernel in the four builds</summary><div class="tw"><table><tr><th>Kernel</th>' + ''.join(f'<th>{e(b)}: loop start modulo 64</th>' for b in bins) + '</tr>']` | `o`: opens the folded block with its title and the table. The header row holds the column "Kernel" and one column per build for the loop start modulo 64. |
| 1959 | `    for k in want:` | Loop over the nine kernels. |
| 1960 | `        o.append(f'<tr><td>{e(k)}</td>' + ''.join(f'<td>{e(get.get((b, k), "-"))}</td>' for b in bins) + '</tr>')` | Adds one table row: the kernel, and for each build the value of `get`, or `-` when the file has no such line. |
| 1961 | `    o.append('</table></div><p class="cap">Loop offsets from the build on CRB. Steps B1, B2, B4, B6, C1 and C2 use <code>bwx</code>.</p></details>')` | Closes the table and adds a typed caption: the loop offsets come from the build on CRB, and the steps B1, B2, B4, B6, C1 and C2 use the build `bwx`. Then the folded block is closed. |
| 1962 | `    return '\n'.join(o)` | Returns the block as one text. |
| 1965 | `def make(spec, banner=None, offsets=os.path.join(BWX, 'crb-build-2', 'offsets.tsv')):` | Starts the function `make`. It does the whole work for a given list of sessions and returns the values and the page text. The tests call it. Unless given, `offsets` is the file `crb-build-2/offsets.tsv` below `BWX`. |
| 1966 | `    sessions = load(spec)` | `sessions`: the input, read by `load`. |
| 1967 | `    D = compute(sessions)` | `D`: all values of the page, from `compute`. |
| 1968 | `    return D, build(D, banner, offsets)` | Returns `D` and the page text of `build`. |
| 1971 | `def main(argv=None):` | Starts the function `main`. `argv` holds the arguments. `None` means the arguments of the command line. |
| 1972 | `    ap = argparse.ArgumentParser(description='result page of question Q1 (one thread) of Parts B and C')` | `ap`: the parser of the command line, with a short description for its help text. |
| 1973 | `    ap.add_argument('--session', nargs='+', action='append', required=True, metavar=('NAME', 'FOLDER'))` | Defines the option `--session`. It is required and may be given several times. Each use takes one or more values: the session name and the folders. The help text shows them as `NAME` and `FOLDER`. |
| 1974 | `    ap.add_argument('-o', '--out', default='partB-q1-result.html')` | Defines the option `-o` or `--out`: the name of the generated page. Without it the name is `partB-q1-result.html` in the working folder. |
| 1975 | `    ap.add_argument('--banner')` | Defines the option `--banner`: the text of the banner at the top of the page. |
| 1976 | `    ap.add_argument('--offsets', default=os.path.join(BWX, 'crb-build-2', 'offsets.tsv'))` | Defines the option `--offsets`: the path of the file of loop offsets, with the same default as in line 1965. |
| 1977 | `    a = ap.parse_args(argv)` | `a`: the parsed arguments. For a wrong command line the parser prints the usage and an error, and ends the script with exit status 2. |
| 1978 | `    spec = []` | `spec`: the list of sessions, empty at the start. |
| 1979 | `    for s in a.session:` | Loop over the uses of `--session`. |
| 1980 | `        if len(s) < 2:` | Tests whether a use has fewer than 2 values. |
| 1981 | `            ap.error('--session needs a name and at least one folder')` | Then the parser prints that `--session` needs a name and at least one folder, and ends the script with exit status 2. |
| 1982 | `        spec.append((s[0], s[1:]))` | Appends one pair: the session name and the list of its folders. |
| 1983 | `    D, page = make(spec, a.banner, a.offsets)` | `D` and `page`: the values and the page text, from `make`. |
| 1984 | `    with open(a.out, 'w') as fh:` | Opens the output file for writing. An older file with that name is replaced. |
| 1985 | `        fh.write(page)` | Writes the page text. |
| 1986 | `    print('wrote %s (%d bytes), sessions: %s' % (a.out, len(page), ', '.join(D['names'])))` | Prints one line: the word `wrote`, the file name, the length of the page text and the session names. The line calls the length bytes. It is the count of characters, which is the same number for a page of plain ASCII text. |
| 1987 | `    for r in D['hyp']:` | Loop over the rows of the hypothesis table. |
| 1988 | `        print('  %-20s %-14s %s' % (r['h'], r['word'], r['step']))` | Prints one line per row: the hypothesis in a field of 20 characters, the word in a field of 14 characters, and the step. |
| 1989 | `    return 0` | Returns 0. |
| 1992 | `if __name__ == '__main__':` | Tests whether the file runs as a program. The test fails when another file imports it as a module, as `test_q1.py` does. |
| 1993 | `    sys.exit(main())` | Runs `main` and ends the script with its return value as the exit status: 0 after a page was written. |

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
