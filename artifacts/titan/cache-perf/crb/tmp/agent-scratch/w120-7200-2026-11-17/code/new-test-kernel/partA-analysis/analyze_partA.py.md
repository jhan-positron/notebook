# `analyze_partA.py` explained, line by line

- Source file: `new-test-kernel/partA-analysis/analyze_partA.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 727 lines, 43713 bytes).
- sha256 of the source when this page was built: `d82f50aeb3b9488d2a919d05205c81fcb7abca00a099119b2e1ac27fd2fcb5e0`.

## Short version: purpose

`analyze_partA.py` reads the result folders that `run_partA.sh` wrote and computes the values of Part A, the screening part of the test plan of 2026-11-13. For each repetition it gives the passes per thread, the thread rates of each mesh and the ratio q of slow to fast threads, and for each step a summary. It writes all of this to one json file, from which `make_partA_html.py` builds the result page.

## Words used here

- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan. Its section "How to analyse Part A" gives the rules that this script follows.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. By the plan it closes no hypothesis. This is not the part A of the later rerun.
- **Step**: one named batch of Part A, `A1` to `A7`. The steps A1 to A6 each have a csv file. Step A7 only reads system files.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel names of the tags**: `read_old` and `write_old` are the C kernels of `bw_old`. `read_new` and `write_new` are the C kernels of `bw_new`. `asmread` and `asmwrite` are the hand-written kernels, taken from `bw_new`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`. The option `--reps` gives the number of repetitions per kernel, and `--min-ms` gives the shortest length of each.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Pass**: one sweep of a thread over its whole buffer.
- **2 % check**: rule 7 of the plan: one pass may take at most 2 % of the interval. That means at least 50 passes per thread.
- **Launch, tag**: a launch is one start of a process by the run script. The tag is the short name of the launch, for example `read_old-r1`.
- **Busiest processes, CPU use (`pcpu`)**: the 5 processes that the run script lists in the file `launches.txt` before each launch, each with the value of the column `pcpu` of the tool `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. So it is an average over the life of the process, not the CPU use at the launch.
- **Block**: the lines of one process in a csv file: the header line of the run script and the output of the benchmark.
- **Header line**: the line that the run script writes before the output of a process. It starts with `-- step` and holds the tag, the binary, the waited seconds, the load, the logins, the UTC time and the options.
- **Data line**: an output line of the benchmark for one repetition, with 10 fields. The fields used here are the kernel, the threads, the bytes per thread, the repetition, `total_bytes`, `elapsed_s` and `aggregate_GBps`.
- **Thread line**: an output line of the benchmark for one thread and one repetition, printed with `--per-thread`. Its 6 fields are the word `thread`, the thread index, the CPU, the kernel, the repetition and the thread rate.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate of a repetition as the benchmark prints it: the bytes of all threads divided by the longest elapsed time of a thread.
- **Thread rate**: the bytes of one thread divided by its own elapsed time. The benchmark prints it with 2 decimals.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Thread count `a+b`**: a threads on mesh 0 and b threads on mesh 1, for example `64+56`.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one repetition. It has no unit.
- **Pattern labels: split, uniform, between**: the provisional labels of a repetition: q below 0.65, q above 0.85, or neither.
- **Fastest half**: the `n//2` threads with the highest rates of one repetition with n threads.
- **Bracket**: the two neighbouring thread counts of step A4 between which the pattern label changes.
- **Level labels: low, high, changing**: the provisional labels of an interval with one thread at 8 MiB: a rate below 69 GB/s, above 70.5 GB/s, or neither.
- **Choice C1 to C11**: a definition that this script had to fix where the plan and the handoff note give none. The header text of the file lists them.
- **Json file**: the output of this script, `partA-summary.json` unless the caller names another file. The format json stores nested lists and dictionaries as text.
- **Range**: in the json file, four values of a list of numbers: the count, the lowest value, the median and the highest value.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: performance monitoring unit, the counter hardware of a core. Linux shows it as a counter device with a type number.
- **SVE**: the scalable vector instruction set of Arm.
- **UTC**: Coordinated Universal Time.

## Main flow

1. `main` reads the arguments: one or more result folders and the optional output path `--out` (lines 702 to 710).
2. `analyse` reads each folder in time order (lines 633 to 642). `parse_env` reads `env.txt`, the files of step A7 and `stderr.txt`. `parse_launches` reads `launches.txt`. `parse_csv` splits each csv file into blocks. `finish_block` turns each data line into a repetition with its passes per thread, its thread rates per mesh, q and the fastest half, and it marks a block that is not complete.
3. Of each step and tag the last complete block is used. The other blocks go to the list `not_used` (lines 643 to 656).
4. q is collected over all repetitions with at least 2 threads. `two_groups` tests whether q falls into two groups. Only then do the repetitions get a pattern label (lines 657 to 668).
5. The steps are summarised (lines 669 to 698): A1 and A2 per kernel (`step_a12`) and against each other (`compare_a1_a2`), A3 (`step_a3`), A4 with its bracket (`step_a4`), A5 (`step_a5`), A6 (`step_a6`), the check of the level limits (`level_check`), and the load readings (`load_check`, `load_summary`).
6. `main` writes the summary to the json file and prints a few lines about it (lines 711 to 723).

## Behavior a reader must know

- The script measures nothing. It reads the files of the result folders and writes one json file. It replaces an older file of the same name.
- Where each number comes from:
  - The total of a repetition is field 7, `aggregate_GBps`, of its data line in the csv file of the step. The script does not compute it again.
  - The passes per thread are field 5, `total_bytes`, divided by field 2, `threads`, times field 3, `bytes_per_thread`. For a copy kernel the result is halved. This is an average over the threads.
  - A thread rate is field 6 of a thread line, and its CPU is field 3. A CPU below 64 is on mesh 0.
  - The sum and the median per mesh are the sum and the median of these thread rates. The sum of thread rates is not the total.
  - q is the thread rate at the 10th percentile divided by the one at the 90th percentile, by the nearest-rank rule.
  - The rates of the steps A5 and A6 are the totals of their data lines. With one thread the total is the rate of the thread.
  - The interval length and the page setting come from the comment line of the benchmark that starts with `# bandwidth:`.
  - The load readings come from the header lines and from `launches.txt`. The run script wrote both directly before each launch.
- Values are combined as ranges and medians. A change between two cases is always a difference of two medians.
- One test decides for all of Part A whether the pattern labels are used (line 664). When it fails, every label stays empty, step A4 gets no bracket, and the page gives q without labels.
- For the data of 2026-11-13 the stored json file gives `two_groups` false and `labels_usable` false, over 152 q values [Ref1].
- A block is used only when it is complete: no `killed` or `failed` line, the number of repetitions that `--reps` asked for, a best line per kernel, all thread lines, and no line that was not understood (lines 204 to 218).
- The best line of the benchmark is not used as a value. It only shows that a kernel ran to its end.
- A missing file is not an error. The part of the summary that needs it stays empty, and the step is listed under `steps_missing`.
- The exit status is 0 after a run that worked, and 2 when no folder is given or a path is not a folder.
- The four limits (0.65 and 0.85 for q, 69 and 70.5 GB/s for the level) are provisional. The json file records them under `limits`.
- The comment of line 460 says that a change over a missing thread count is not a change between neighbouring counts. The code only records the missing counts and can still give such a change as the bracket (line 462).
- The result folder `partA-20261113T205055Z` holds a copy of this file with the same sha256, beside the json file `partA-summary.json` [Ref1].

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partA-analysis/analyze_partA.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (727 lines, 43713 bytes, sha256 `d82f50aeb3b9488d2a919d05205c81fcb7abca00a099119b2e1ac27fd2fcb5e0`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header text: purpose, input, output and the choices C1 to C11 (lines 1 to 50)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""analyze_partA.py <result folder>... [--out partA-summary.json]` | Starts the header text of the file (a docstring, a text that Python keeps but does not run). This line is the usage: the arguments are one or more result folders, and the option `--out` names the output file. Without the option the output file is `partA-summary.json`. |
| 4 | `Analysis of Part A (screening) of new-test-kernel/plan.md, as handoff.md says in` | Header text: the file is the analysis of Part A of the plan. Part A is screening: a first look with the two existing benchmark binaries. The analysis follows the section of the handoff note that line 5 names. |
| 5 | `"How to analyse Part A". Input: one or more folders partA-<UTC>/ written by run_partA.sh` | Header text: that section is `How to analyse Part A`. The input is one or more result folders with the name `partA-<UTC>/`, which the run script `run_partA.sh` wrote. |
| 6 | `(A1.csv ... A6.csv, env.txt, launches.txt, stderr.txt, A7-*.txt). Output: partA-summary.json.` | Header text: the files of such a folder: one csv file for each of the steps A1 to A6, `env.txt`, `launches.txt`, `stderr.txt` and the files of step A7. The output is one json file, `partA-summary.json`. |
| 8 | `Part A is screening. Nothing computed here closes a hypothesis.` | Header text: Part A is screening. No value that this script computes closes a hypothesis of the plan. |
| 10 | `Choices of this script where the handoff gives no exact definition (also written to the json,` | Header text: the list of the choices starts here. A choice is a definition that this script had to fix where the handoff note gives no exact one. The json file holds the same list (line 11). |
| 11 | `key "choices"):` | Header text: in the json file the list stands under the key `choices`. |
| 12 | `  C1 percentile: nearest rank. Rates sorted upward, the value at the P-th percentile is the` | Choice C1, the percentile: the nearest-rank rule. The rates are sorted upward. The sentence ends in line 13. |
| 13 | `     value number ceil(P/100 x n), counted from 1. With 120 threads: number 12 and number 108.` | Continues C1: the value at the P-th percentile is value number `ceil(P/100 x n)` of the n sorted rates, counted from 1. `ceil` rounds up to a whole number. With 120 threads the 10th percentile is value number 12, and the 90th is value number 108. |
| 14 | `  C2 "two groups" of q: all q of repetitions with at least 2 threads are sorted. The largest` | Choice C2, the test for two groups of q. q is the rate of the thread at the 10th percentile divided by the rate of the thread at the 90th percentile, in one repetition. All q of repetitions with at least 2 threads are sorted. The sentence that starts here ends in line 15. |
| 15 | `     distance between two neighbouring values divides them into a lower and an upper group.` | Continues C2: the largest distance between two neighbouring values divides the sorted values into a lower and an upper group. |
| 16 | `     q "falls into two groups" if each group has at least 2 values, the distance is at least` | Continues C2: q falls into two groups when three conditions hold. First, each group has at least 2 values. The second condition ends in line 17. |
| 17 | `     0.10, and the distance is larger than the width of each group. The labels are used only` | Continues C2: second, the distance is at least 0.10. Third, the distance is larger than the width of each group. The width is the highest value of a group minus its lowest. The sentence about the labels ends in line 19. |
| 18 | `     if, in addition, every value of the lower group is below 0.65 and every value of the upper` | Continues C2: the pattern labels are used only when, in addition, every value of the lower group is below 0.65. The condition for the upper group follows in line 19. |
| 19 | `     group is above 0.85.` | Continues C2: and every value of the upper group is above 0.85. |
| 20 | `  C3 fastest half: the n//2 threads with the highest rates. Thread rates are printed with 2` | Choice C3, the fastest half: the `n//2` threads with the highest rates of a repetition with n threads. `//` divides and drops the fraction. The sentence about equal rates ends in line 22. |
| 21 | `     decimals, so several threads can have the rate of the last place. The count of each mesh` | Continues C3: the benchmark prints a thread rate with 2 decimals. So several threads can have the same rate as the last thread of the fastest half. |
| 22 | `     is then given as a lowest and a highest possible value.` | Continues C3: the count of the threads of each mesh in the fastest half is then given as a lowest and a highest possible value. |
| 23 | `  C4 repeated launch: if one (step, tag) has several blocks, the last complete block is used.` | Choice C4, a repeated launch: when one pair of step and tag has several blocks, the last complete block is used. A block is the lines of one process in a csv file. |
| 24 | `     The other blocks are listed under "not_used".` | Continues C4: the other blocks are listed in the json file under the key `not_used`. |
| 25 | `  C5 a count of A4 (for example 64+48) has the label of its repetitions if all have the same` | Choice C5: a thread count of step A4, for example 64+48, gets the label of its repetitions when all of them have the same label. The sentence ends in line 26. |
| 26 | `     label, and "mixed" otherwise.` | Continues C5: when the labels differ, the count gets the label `mixed`. |
| 27 | `  C7 A4 bracket: looked for among the counts with threads on both meshes (64+0 is left out). A` | Choice C7, the bracket of step A4: the two neighbouring thread counts between which the pattern changes. It is looked for among the counts with threads on both meshes. The count 64+0 is left out. |
| 28 | `     bracket is given only if there is exactly one change and it is between split and uniform.` | Continues C7: a bracket is given only when the labels change exactly once, and that change is between `split` and `uniform`. |
| 29 | `  C8 q of A3: the write and copy repetitions of the A3 processes with two buffers` | Choice C8, the q values of step A3: the write and copy repetitions of the A3 processes with two buffers are left out of the test of the two groups. The sentence ends in line 30. |
| 30 | `     (--kernel all) are not used for the test of the two groups. The handoff says to compare` | Continues C8: those processes ran with `--kernel all`. The reason starts here and ends in line 31: the handoff note says to compare only the rows of the read kernel for A3. |
| 31 | `     only the rows of the read kernel for A3. They are listed in the json under q.rows_left_out.` | Continues C8: the rows that are left out are listed in the json file under `q.rows_left_out`. |
| 32 | `  C6 A5 level change: the labels "low" and "high" of the intervals in time order, with` | Choice C6, a level change in step A5: the script takes the labels `low` and `high` of the intervals in time order. The sentence ends in line 33. |
| 33 | `     "changing" intervals left out. A change is a place where this sequence goes from one` | Continues C6: intervals with the label `changing` are left out. A change is a place where this sequence goes from one label to the other. |
| 34 | `     label to the other. Its position is the number of the first interval with the new label.` | Continues C6: the position of a change is the number of the first interval with the new label. |
| 35 | `  C9 check of the level limits (plan rule 5: "checked against the distribution of the new data` | Choice C9, the check of the two level limits. Rule 5 of the plan asks that the limits are checked against the distribution of the new data before they are used. The quotation ends in line 36. |
| 36 | `     before they are used"): done for each CPU over its A5 and A6 rates. A limit does not` | Continues C9: the check is made for each CPU, over all its rates of the steps A5 and A6. The rule for a limit that does not separate the rates starts at the end of this line. |
| 37 | `     separate the rates of a CPU if rates lie on both sides of it and the empty range around it` | Continues C9: a limit does not separate the rates of a CPU when rates lie on both sides of it and the empty range around it is too small. The sentence ends in line 39. |
| 38 | `     (from the nearest rate below the limit to the nearest rate at or above it) is smaller than` | Continues C9: the empty range goes from the nearest rate below the limit to the nearest rate at or above it. |
| 39 | `     0.25 GB/s. The level labels of a CPU are usable only if both limits separate its rates.` | Continues C9: the range is too small when it is smaller than 0.25 GB/s. The level labels of a CPU are usable only when both limits separate its rates. |
| 40 | `     Level changes (C6) are given only for a CPU with usable labels.` | Continues C9: level changes (choice C6) are given only for a CPU whose labels are usable. |
| 41 | `  C10 event names for the five events of handoff B.8, looked up in A7-core-events.txt:` | Choice C10: the event names for the five counter events that section B.8 of the handoff note names in words. The script looks them up in the file `A7-core-events.txt` of step A7. |
| 42 | `     cycles = cpu_cycles, instructions = inst_retired, L1 data refills = l1d_cache_refill,` | Continues C10: cycles are the event `cpu_cycles`, instructions are `inst_retired`, and L1 data refills are `l1d_cache_refill`. |
| 43 | `     L2 data refills = l2d_cache_refill, last-level read misses = ll_cache_miss_rd.` | Continues C10: L2 data refills are `l2d_cache_refill`, and last-level read misses are `ll_cache_miss_rd`. |
| 44 | `     l3d_cache_refill is listed as a second candidate for the last one. No choice is made.` | Continues C10: the event `l3d_cache_refill` is listed as a second candidate for the last-level read misses. The script does not choose between the two. |
| 45 | `  C11 "A2 changed the totals" (plan, "Order and decision points", item 2; the plan gives no` | Choice C11: the meaning of the words `A2 changed the totals`. They come from item 2 of the section `Order and decision points` of the plan. The plan gives no number for them. |
| 46 | `     number): for each interval the range of the difference old read minus new read goes from` | Continues C11: for each interval length the script forms the range of the difference between the total of the old read kernel and the total of the new read kernel. Line 47 gives the two ends of the range. |
| 47 | `     (lowest old total - highest new total) to (highest old total - lowest new total). The` | Continues C11: the range goes from the lowest old total minus the highest new total to the highest old total minus the lowest new total. |
| 48 | `     totals count as changed only if the range with the long interval does not overlap the` | Continues C11: the totals count as changed only when the range with the long interval does not overlap the range with the short interval. The sentence ends in line 49. |
| 49 | `     range with the short interval.` | Ends the text of C11. |
| 50 | `"""` | Ends the header text. |

### Imports, limits and fixed lists (lines 51 to 63)

| Line | Source | Explanation |
|---:|---|---|
| 51 | `import sys, os, re, json, math, glob, statistics as st` | Loads seven modules of the Python standard library: `sys` (arguments and exit status), `os` (paths), `re` (regular expressions), `json` (the output format), `math` (rounding up), `glob` (file name patterns) and `statistics` under the short name `st` (the median). |
| 53 | `Q_SPLIT, Q_UNIFORM = 0.65, 0.85          # handoff, "How to analyse Part A", item 3 (provisional)` | `Q_SPLIT` is 0.65 and `Q_UNIFORM` is 0.85: the two limits of the pattern rule for q. A repetition is split when q is below 0.65 and uniform when q is above 0.85. By the comment they come from item 3 of the section `How to analyse Part A` of the handoff note, and they are provisional. |
| 54 | `LOW_BELOW, HIGH_ABOVE = 69.0, 70.5       # GB/s, plan rule 5 (provisional)` | `LOW_BELOW` is 69.0 and `HIGH_ABOVE` is 70.5, in GB/s: the two limits of the level of one thread with a buffer of 8 MiB. By the comment they come from rule 5 of the plan, and they are provisional. |
| 55 | `MIN_PASSES = 50                          # plan rule 7: interval/passes <= 2 % of the interval` | `MIN_PASSES` is 50: the smallest number of passes per thread that a repetition must have. A pass is one sweep of a thread over its whole buffer. By the comment this is rule 7 of the plan: one pass may take at most 2 % of the interval, and 1 pass of 50 is 2 %. |
| 56 | `GAP_MIN = 0.10` | `GAP_MIN` is 0.10: the smallest distance between the two groups of q that choice C2 accepts. q is a ratio and has no unit. |
| 57 | `LEVEL_GAP_MIN = 0.25                     # GB/s, choice C9` | `LEVEL_GAP_MIN` is 0.25 GB/s: the smallest empty range around a level limit that choice C9 accepts. |
| 58 | `B8_EVENTS = [('cycles', 'cpu_cycles'), ('instructions', 'inst_retired'), ('L1 data refills', 'l1d_cache_refill'),` | `B8_EVENTS`: the five counter events of section B.8 of the handoff note. Each entry is a pair: the words of the handoff note, and the event name that choice C10 picked. This line holds the pairs for the cycles, the instructions and the L1 data refills. |
| 59 | `             ('L2 data refills', 'l2d_cache_refill'), ('last-level read misses', 'll_cache_miss_rd')]      # choice C10` | Continues the list of line 58: the pairs for the L2 data refills and for the last-level read misses. |
| 60 | `B8_OTHER = [('last-level read misses', 'l3d_cache_refill')]` | `B8_OTHER`: the second candidate for the last-level read misses, the event name `l3d_cache_refill`. |
| 61 | `STEPS = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7']` | `STEPS`: the names of the seven steps of Part A. The first six have a csv file. |
| 62 | `A4_SERIES = {'64+b': ['64+0', '64+16', '64+32', '64+40', '64+48', '64+52', '64+56'],` | `A4_SERIES`: the two series of thread counts of step A4, in rising order. A count `a+b` means a threads on mesh 0 and b threads on mesh 1. The series `64+b` has 64 threads on mesh 0 and 0, 16, 32, 40, 48, 52 or 56 threads on mesh 1. |
| 63 | `             'a+a': ['32+32', '40+40', '48+48', '56+56']}` | Continues line 62: the series `a+a` has the same number of threads on each mesh: 32, 40, 48 or 56. |

### The texts of the choices and the pattern of the header line (lines 64 to 91)

| Line | Source | Explanation |
|---:|---|---|
| 64 | `CHOICES = {` | `CHOICES`: a dictionary with one short text per choice. Line 681 writes it to the json file under the key `choices`. A reader of the json file then sees the choices beside the results. The texts repeat the header text of lines 12 to 49 in short form. |
| 65 | `    'C1_percentile': 'nearest rank: value number ceil(P/100 x n) of the rates sorted upward',` | Text for choice C1: the nearest-rank percentile (lines 12 to 13). |
| 66 | `    'C2_two_groups': 'largest distance between neighbouring q values divides them; two groups if each side has '` | Text for choice C2, first piece: the largest distance between neighbouring q values divides them. The conditions for two groups start here (lines 14 to 19). |
| 67 | `                     'at least 2 values, the distance is at least 0.10 and larger than the width of each group; '` | Text for choice C2, second piece: each side has at least 2 values, and the distance is at least 0.10 and larger than the width of each group. |
| 68 | `                     'labels are used only if also the lower group is below 0.65 and the upper group above 0.85',` | Text for choice C2, last piece: the labels are used only when the lower group is also below 0.65 and the upper group above 0.85. |
| 69 | `    'C3_fastest_half': 'n//2 fastest threads; with equal rates at the last place the count per mesh is a lowest and a highest value',` | Text for choice C3: the fastest half and the lowest and highest count per mesh (lines 20 to 22). |
| 70 | `    'C4_repeated_launch': 'the last complete block of a (step, tag) is used; the others are listed under not_used',` | Text for choice C4: the last complete block of a pair of step and tag is used (lines 23 to 24). |
| 71 | `    'C5_A4_count_label': 'label of a count = label of its repetitions if all are equal, else mixed',` | Text for choice C5: the label of a thread count of step A4 (lines 25 to 26). |
| 72 | `    'C7_A4_bracket': 'the two neighbouring counts between which the label changes are looked for among the counts with threads '` | Text for choice C7, first piece: where the change of the label is looked for (lines 27 to 28). |
| 73 | `                     'on both meshes; 64+0 keeps its own label and is left out; a bracket is given only if there is exactly one '` | Text for choice C7, second piece: the count 64+0 keeps its own label and is left out. The condition for a bracket starts here. |
| 74 | `                     'change and it is between split and uniform',` | Text for choice C7, last piece: a bracket needs exactly one change, between `split` and `uniform`. |
| 75 | `    'C8_q_of_A3': 'the write and copy repetitions of the A3 processes with two buffers (--kernel all) are not used for the '` | Text for choice C8, first piece: which repetitions of step A3 are left out of the test of the two groups (lines 29 to 31). |
| 76 | `                  'test of the two groups, because the handoff says to compare only the rows of the read kernel for A3; '` | Text for choice C8, second piece: the reason, the sentence of the handoff note about the rows of the read kernel. |
| 77 | `                  'they are listed under q.rows_left_out',` | Text for choice C8, last piece: the rows are listed under `q.rows_left_out`. |
| 78 | `    'C6_A5_change': 'low/high sequence without the changing intervals; position = first interval with the new label',` | Text for choice C6: the sequence of low and high without the changing intervals, and the position of a change (lines 32 to 34). |
| 79 | `    'C9_level_limits': 'per CPU over its A5 and A6 rates: a limit does not separate the rates if rates lie on both sides of it and the '` | Text for choice C9, first piece: per CPU, when a limit does not separate the rates (lines 35 to 40). |
| 80 | `                       'empty range around it is smaller than 0.25 GB/s; level labels and level changes are used only for a CPU '` | Text for choice C9, second piece: the empty range must be at least 0.25 GB/s wide. The use of the labels starts here. |
| 81 | `                       'where both limits separate the rates',` | Text for choice C9, last piece: labels and level changes are used only for a CPU where both limits separate the rates. |
| 82 | `    'C10_event_names': 'cycles = cpu_cycles, instructions = inst_retired, L1 data refills = l1d_cache_refill, L2 data refills = '` | Text for choice C10, first piece: the event names for cycles, instructions, L1 data refills and L2 data refills (lines 41 to 44). |
| 83 | `                       'l2d_cache_refill, last-level read misses = ll_cache_miss_rd; l3d_cache_refill is a second candidate for the last',` | Text for choice C10, last piece: the event name for the last-level read misses and its second candidate. |
| 84 | `    'C11_A2_changed_totals': 'range of (old read total - new read total) per interval = lowest old - highest new to highest old - lowest new; '` | Text for choice C11, first piece: how the range of the difference between the old read total and the new read total is formed (lines 45 to 49). |
| 85 | `                             'the totals count as changed only if the range with the long interval does not overlap the range with the short interval',` | Text for choice C11, last piece: the totals count as changed only when the two ranges do not overlap. |
| 86 | `}` | Ends the dictionary `CHOICES`. |
| 88 | `HDR = re.compile(r'^-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) '` | `HDR`: a compiled pattern for the header line that `run_partA.sh` writes before the output of each process. The line starts with `-- step`. `\S+` matches a run of characters without a space. The pattern has 11 groups. This line holds the first eight: the step, the tag, the binary, the seconds that the script waited before the launch (`waited_s`), and the first four fields of `/proc/loadavg`. These are the load averages over 1, 5 and 15 minutes, and the field with the runnable tasks and the number of all tasks. |
| 89 | `                 r'logins (\S+) utc (\S+) args (.*)$')` | Continues the pattern of line 88 with the last three groups: the number of logins, the UTC time of the launch, and after the word `args` the rest of the line, which holds all options of the benchmark. |

### Small helpers: `pct`, `mesh_of`, `level`, `rule_label`, `arg_of` (lines 92 to 114)

| Line | Source | Explanation |
|---:|---|---|
| 92 | `def pct(sorted_vals, p):` | Starts the function `pct`. It returns the value at the percentile `p` of a list that is sorted upward. |
| 93 | `    """Nearest-rank percentile (choice C1)."""` | Text of the function: it is the nearest-rank percentile of choice C1. |
| 94 | `    n = len(sorted_vals)` | `n`: the number of values. |
| 95 | `    return sorted_vals[min(n, max(1, math.ceil(p / 100.0 * n))) - 1]` | Computes the rank `ceil(p/100 x n)`. `math.ceil` rounds up to a whole number. `max` and `min` keep the rank from 1 to `n`. The function returns the value with that rank. Python counts list places from 0, so 1 is subtracted. With 120 values the rank is 12 for `p` of 10 and 108 for `p` of 90. |
| 98 | `def mesh_of(cpu):` | Starts the function `mesh_of`. It gives the mesh of a CPU number. |
| 99 | `    return 0 if cpu < 64 else 1` | Returns 0 for the CPUs 0 to 63 and 1 for every CPU from 64 on. |
| 102 | `def level(rate):` | Starts the function `level`. It gives the level label of one rate in GB/s. |
| 103 | `    return 'low' if rate < LOW_BELOW else 'high' if rate > HIGH_ABOVE else 'changing'` | Returns `low` for a rate below 69.0 GB/s, `high` for a rate above 70.5 GB/s, and `changing` for every rate from 69.0 to 70.5 GB/s, the two limits included. |
| 106 | `def rule_label(q):` | Starts the function `rule_label`. It applies the provisional pattern rule of the handoff note to one q value. |
| 107 | `    return 'split' if q < Q_SPLIT else 'uniform' if q > Q_UNIFORM else 'between'` | Returns `split` for q below 0.65, `uniform` for q above 0.85, and `between` for every q from 0.65 to 0.85, the two limits included. |
| 110 | `def arg_of(args, name, default=None):` | Starts the function `arg_of`. It finds the value of one option in the options text of a header line. |
| 111 | `    a = args.split()` | `a`: the options text, split at spaces into words. |
| 112 | `    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default` | Returns the word that follows the option `name`, for example `3` after `--reps`. When the option is missing or is the last word, the function returns `default`. |

### Function `parse_csv`: the blocks of one csv file (lines 115 to 160)

| Line | Source | Explanation |
|---:|---|---|
| 115 | `def parse_csv(path, folder):` | Starts the function `parse_csv`. It reads one csv file of a result folder, for example `A1.csv`, and splits it into blocks, one per process. `folder` is the name of the result folder. It is stored in each block. |
| 116 | `    """Return the list of blocks (one per process) of one csv file, in file order."""` | Text of the function: it returns the list of the blocks of one csv file, in file order. |
| 117 | `    blocks, cur = [], None` | `blocks`: the blocks found so far. `cur`: the block whose lines are read now. It is `None` before the first header line. |
| 118 | `    with open(path) as f:` | Opens the csv file for reading. Python closes the file when the indented part that follows ends (line 157). |
| 119 | `        for ln, line in enumerate(f, 1):` | Loop over the lines of the file. `ln` is the line number, counted from 1. |
| 120 | `            line = line.rstrip('\n')` | Removes the line end from the line. |
| 121 | `            m = HDR.match(line)` | Tests whether the line is a header line of a process (line 88). |
| 122 | `            if m:` | A header line starts a new block. |
| 123 | `                step, tag, binary, waited, l1, l5, l15, run, logins, utc, args = m.groups()` | Takes the 11 groups of the pattern into 11 names: step, tag, binary, waited seconds, the three load averages, the field with the runnable tasks, logins, UTC time and options. |
| 124 | `                cur = dict(folder=folder, file=os.path.basename(path), line=ln, step=step, tag=tag, binary=binary,` | `cur`: the new block, a dictionary. This line stores the name of the result folder, the file name without its path, the line number of the header line, the step, the tag and the binary. |
| 125 | `                           waited_s=float(waited), load1=float(l1), load5=float(l5), load15=float(l15),` | Continues the block: the waited seconds and the load averages over 1, 5 and 15 minutes, as numbers. |
| 126 | `                           runnable=int(run.split('/')[0]), logins=int(logins), utc=utc, args=args,` | Continues the block: `runnable` is the number before the slash in the fourth load field. It is the number of tasks that were runnable when the run script wrote the header line. Then come the number of logins, the UTC time and the options text. |
| 127 | `                           min_ms=None, thp=None, killed=None, failed=None, rows={}, best={}, thr={}, bad_lines=[])` | Continues the block with empty places that later lines fill: the interval length `min_ms`, the page setting `thp`, the texts of a `killed` line and of a `failed` line, the data lines (`rows`), the best lines (`best`), the thread lines (`thr`), and the numbers of the lines that were not understood (`bad_lines`). |
| 128 | `                blocks.append(cur)` | Adds the new block to the list. |
| 129 | `                continue` | Goes to the next line of the file. |
| 130 | `            if cur is None:` | Tests whether no header line was seen yet. |
| 131 | `                continue` | A line before the first header line is skipped. |
| 132 | `            if line.startswith('-- killed'):` | A line that starts with `-- killed`. The run script writes it when it stops this process for the marker file, the stop file or the stop time. |
| 133 | `                cur['killed'] = line[3:]` | Stores the text of the line without its first three characters (two hyphens and a space). |
| 134 | `                continue` | Goes to the next line. |
| 135 | `            if line.startswith('-- failed'):` | A line that starts with `-- failed`. The run script writes it when the process ended with an exit status other than 0. |
| 136 | `                cur['failed'] = line[3:]` | Stores the text of the line without its first three characters. |
| 137 | `                continue` | Goes to the next line. |
| 138 | `            if line.startswith('# bandwidth:'):` | The comment line that the benchmark prints first. It starts with `# bandwidth:` and names the units and the settings of the process. |
| 139 | `                m = re.search(r'min_ms=(\S+) thp=(\S+)', line)` | Searches the line for the text `min_ms=`, a value, a space, `thp=` and a value. Group 1 holds the shortest interval length in ms (the option `--min-ms`). Group 2 holds the page setting that the benchmark printed: `madvise` when it asked Linux for huge pages, and `nohugepage` when it ran with `--no-thp`. |
| 140 | `                if m:` | Tests whether the text was found. |
| 141 | `                    cur['min_ms'] = float(m.group(1)); cur['thp'] = m.group(2)` | Stores the interval length as a number and the page setting as text. |
| 142 | `                continue` | Goes to the next line. |
| 143 | `            p = line.split(',')` | `p`: the fields of the line, split at commas. |
| 144 | `            try:` | Starts a part whose number conversions can fail. Line 156 handles a failure. |
| 145 | `                if p[0] == 'thread' and len(p) == 6:` | A thread line: the first field is the word `thread`, and the line has 6 fields. They are the word, the thread index, the CPU, the kernel, the repetition and the rate of the thread in GB/s. The benchmark prints these lines with `--per-thread`. |
| 146 | `                    cur['thr'].setdefault((p[3], int(p[4])), []).append((int(p[2]), float(p[5])))` | Stores the pair of CPU (field 3) and thread rate (field 6) in the list of its kernel and repetition (fields 4 and 5). `setdefault` creates the list at the first thread. The benchmark computes a thread rate as the bytes of that thread divided by its own elapsed time, and prints it with 2 decimals. |
| 147 | `                elif len(p) == 10 and p[3].isdigit():      # a data line: the 4th field is a number` | A data line: 10 fields, and the 4th field, the repetition, holds digits only. The benchmark prints one such line per repetition. |
| 148 | `                    cur['rows'][(p[0], int(p[3]))] = dict(threads=int(p[1]), bytes_per_thread=int(p[2]),` | Stores the data line under its kernel (field 1) and its repetition (field 4). This line takes field 2, the number of threads, and field 3, the buffer size of one thread in bytes. |
| 149 | `                                                           total_bytes=int(p[4]), elapsed_s=float(p[5]),` | Continues the row: field 5, `total_bytes`, the bytes that all threads moved in the repetition. Field 6, `elapsed_s`, the longest elapsed time of a thread, in seconds. |
| 150 | `                                                           total_GBps=float(p[6]), thr_min=float(p[7]),` | Continues the row: field 7, `aggregate_GBps`, is stored as `total_GBps`. It is the total of the repetition: the benchmark divides the bytes of all threads by the longest elapsed time of a thread, in GB/s. Field 8 is the lowest thread rate. |
| 151 | `                                                           thr_max=float(p[8]), thr_avg=float(p[9]))` | Continues the row: field 9, the highest thread rate, and field 10, the mean of the thread rates, in GB/s. |
| 152 | `                elif len(p) == 10 and p[3] == 'best':` | A best line: 10 fields with the word `best` in the 4th field. The benchmark prints one per kernel. |
| 153 | `                    cur['best'][p[0]] = float(p[6])` | Stores field 7, the highest total among the repetitions of that kernel, under the kernel name. The analysis uses the best line only to test that the block is complete (line 211). |
| 154 | `                elif line.strip() and not line.startswith('kernel,'):` | Every other line that is not empty and is not the line with the column names, which starts with `kernel,`. |
| 155 | `                    cur['bad_lines'].append(ln)` | Stores its line number as a line that was not understood. |
| 156 | `            except ValueError:` | Catches a field that is not a number where one is expected. |
| 157 | `                cur['bad_lines'].append(ln)                 # a line cut by a kill` | Stores the line number as not understood. By the comment this is a line that a kill cut short. |
| 158 | `    return blocks` | Returns the list of the blocks. |

### Function `fastest_half`: threads of each mesh among the fastest half (lines 161 to 176)

| Line | Source | Explanation |
|---:|---|---|
| 161 | `def fastest_half(threads):` | Starts the function `fastest_half` (choice C3). `threads` is the list of the pairs of CPU and rate of one repetition. The function counts how many threads of each mesh are among the fastest half. |
| 162 | `    """Choice C3. threads: list of (cpu, rate). Lowest and highest possible count of each mesh."""` | Text of the function: the result gives the lowest and the highest possible count of each mesh. |
| 163 | `    n = len(threads); h = n // 2` | `n`: the number of threads. `h`: the size of the fastest half, `n` divided by 2 without the fraction. With 120 threads `h` is 60. |
| 164 | `    if h == 0:` | Tests whether the half is empty. This is the case with fewer than 2 threads. |
| 165 | `        return None` | Such a repetition has no fastest half: the function returns `None`. |
| 166 | `    s = sorted(threads, key=lambda t: -t[1])` | `s`: the threads sorted by rate, fastest first. |
| 167 | `    cut = s[h - 1][1]` | `cut`: the rate of the last thread of the fastest half, which is thread number `h` of the sorted list. |
| 168 | `    sure = [t for t in s if t[1] > cut]; tied = [t for t in s if t[1] == cut]` | `sure`: the threads with a rate above `cut`. They belong to the fastest half in every case. `tied`: the threads whose printed rate is equal to `cut`. |
| 169 | `    free = h - len(sure)` | `free`: the number of places of the fastest half that the tied threads fill. |
| 170 | `    out = dict(n_half=h, cut_rate=cut, tied_at_cut=len(tied) if len(tied) > free else 0)` | `out`: the result. `n_half` is the size of the half, and `cut_rate` is the rate at its limit. `tied_at_cut` is the number of tied threads when there are more of them than free places. It is 0 when the tied threads fit exactly. The rates then define the half fully. |
| 171 | `    for m in (0, 1):` | Loop over mesh 0 and mesh 1. |
| 172 | `        a = sum(1 for t in sure if mesh_of(t[0]) == m); tm = sum(1 for t in tied if mesh_of(t[0]) == m)` | `a`: the number of sure threads on this mesh. `tm`: the number of tied threads on this mesh. |
| 173 | `        out[f'mesh{m}'] = [a + max(0, free - (len(tied) - tm)), a + min(free, tm)]` | Stores the lowest and the highest possible count of this mesh in the fastest half, under the key `mesh0` or `mesh1`. Lowest: the tied threads of the other mesh take as many free places as they can, and this mesh gets the rest. Highest: the tied threads of this mesh take as many free places as they can. When the tied threads fit exactly, the two values are equal. |
| 174 | `    return out` | Returns the result. |

### Function `analyse_rep`: the values of one repetition (lines 177 to 198)

| Line | Source | Explanation |
|---:|---|---|
| 177 | `def analyse_rep(kernel, rep, row, threads):` | Starts the function `analyse_rep`. It computes all values of one repetition. `row` is its data line (lines 148 to 151). `threads` is the list of the pairs of CPU and rate from its thread lines (line 146). |
| 178 | `    d = dict(kernel=kernel, rep=rep, **row)` | `d`: the result, a dictionary. It starts with the kernel name, the repetition number and all values of the data line. |
| 179 | `    div = row['threads'] * row['bytes_per_thread'] * (2 if 'copy' in kernel else 1)` | `div`: the bytes of one pass of all threads: the number of threads times the buffer size of one thread. For a copy kernel the value is doubled: the benchmark counts the bytes read plus the bytes written of a copy. |
| 180 | `    d['passes_per_thread'] = row['total_bytes'] / div` | `passes_per_thread`: the column `total_bytes` divided by `div`. It is the average number of passes per thread in the repetition. The data line does not give the passes of a single thread. |
| 181 | `    d['below_50_passes'] = d['passes_per_thread'] < MIN_PASSES` | `below_50_passes`: true when the average is below 50 passes. Such a repetition fails the 2 % check of rule 7 of the plan. |
| 182 | `    d['thread_lines'] = len(threads)` | `thread_lines`: the number of thread lines found for this repetition. |
| 183 | `    d['threads_cpu_rate'] = [[c, r] for c, r in threads]` | `threads_cpu_rate`: the pairs of CPU and thread rate as lists, a form that a json file can hold. |
| 184 | `    for m in (0, 1):` | Loop over mesh 0 and mesh 1. |
| 185 | `        v = [r for c, r in threads if mesh_of(c) == m]` | `v`: the rates of the threads whose CPU is on this mesh. |
| 186 | `        d[f'mesh{m}'] = dict(n=len(v), sum=round(sum(v), 2), median=st.median(v)) if v else dict(n=0, sum=None, median=None)` | Stores under `mesh0` or `mesh1`: the number of threads on the mesh, the sum of their rates rounded to 2 decimals, and the median of their rates, in GB/s. Each thread rate is the bytes of that thread divided by its own time. So this sum is not the total of the benchmark, which divides all bytes by the longest time of a thread. A mesh without threads gets the count 0 and no values. |
| 187 | `    if len(threads) >= 2:` | The values of lines 188 to 192 need at least 2 thread lines. |
| 188 | `        s = sorted(r for _, r in threads)` | `s`: all thread rates of the repetition, sorted upward. |
| 189 | `        d['p10'], d['p90'] = pct(s, 10), pct(s, 90)` | `p10` and `p90`: the thread rates at the 10th and at the 90th percentile, by the nearest-rank rule (line 92). |
| 190 | `        d['q'] = d['p10'] / d['p90'] if d['p90'] > 0 else None` | `q`: `p10` divided by `p90`. A value near 1 means that the slow and the fast threads have nearly the same rate. A value near 0.5 means that the slow threads have half the rate of the fast ones. `q` is empty when `p90` is 0. |
| 191 | `        d['label_rule'] = rule_label(d['q']) if d['q'] is not None else None` | `label_rule`: the label that the provisional rule gives for this `q`: `split`, `between` or `uniform` (line 106). |
| 192 | `        d['fastest_half'] = fastest_half(threads)` | `fastest_half`: the counts per mesh among the fastest half (line 161). |
| 193 | `    else:` | The case with fewer than 2 thread lines. |
| 194 | `        d['p10'] = d['p90'] = d['q'] = d['label_rule'] = d['fastest_half'] = None` | The five values are then empty. This is the case for the steps A5 and A6, which run one thread without `--per-thread`. |
| 195 | `    d['label'] = None                                  # set later, only if the labels may be used` | `label`: the pattern label that the result page may use. It stays empty here. Line 668 copies `label_rule` into it only when the test of the two groups allows the labels. |
| 196 | `    return d` | Returns the values of the repetition. |

### Function `finish_block`: repetitions of a block and the test for a complete block (lines 199 to 224)

| Line | Source | Explanation |
|---:|---|---|
| 199 | `def finish_block(b):` | Starts the function `finish_block`. It turns the raw lines of one block into repetitions and decides whether the block is complete. |
| 200 | `    """Turn the raw rows of a block into repetitions, and decide whether the block is complete."""` | Text of the function: the same in one sentence. |
| 201 | `    reps = [analyse_rep(k, r, row, b['thr'].get((k, r), [])) for (k, r), row in b['rows'].items()]` | `reps`: one analysed repetition per data line of the block, in file order (line 177). Each gets the thread lines of its kernel and repetition, or an empty list when there are none. |
| 202 | `    want = arg_of(b['args'], '--reps'); want = int(want) if want else None` | `want`: the number of repetitions that the launch asked for, from the option `--reps` of the header line. It is `None` when the option is missing. |
| 203 | `    kernels = list(dict.fromkeys(r['kernel'] for r in reps))` | `kernels`: the kernel names of the repetitions, each once, in the order of their first data line. |
| 204 | `    problems = []` | `problems`: the list of reasons why the block is not complete, empty at first. |
| 205 | `    if b['killed']: problems.append('killed')` | Problem: the block has a `-- killed` line. |
| 206 | `    if b['failed']: problems.append('failed')` | Problem: the block has a `-- failed` line. |
| 207 | `    if not reps: problems.append('no data line')` | Problem: the block has no data line. |
| 208 | `    for k in kernels:` | Loop over the kernels of the block. |
| 209 | `        n = sum(1 for r in reps if r['kernel'] == k)` | `n`: the number of data lines of this kernel. |
| 210 | `        if want and n != want: problems.append(f'{k}: {n} of {want} repetitions')` | Problem: the kernel has another number of repetitions than `--reps` asked for. The text names the kernel and the two numbers. |
| 211 | `        if k not in b['best']: problems.append(f'{k}: no best line')` | Problem: the kernel has no best line. The benchmark prints that line after the last repetition of a kernel, so a missing one shows a process that ended early. |
| 212 | `    if '--per-thread' in b['args'].split():` | Tests whether the launch asked for thread lines (`--per-thread` among the options). |
| 213 | `        for r in reps:` | Loop over the repetitions. |
| 214 | `            if r['thread_lines'] != r['threads']:` | Tests whether the number of thread lines differs from the number of threads of the repetition. |
| 215 | `                problems.append(f"{r['kernel']} rep {r['rep']}: {r['thread_lines']} of {r['threads']} thread lines")` | Problem: thread lines are missing or too many. The text names the kernel, the repetition and the two numbers. |
| 216 | `    if b['bad_lines']: problems.append(f"{len(b['bad_lines'])} lines not understood")` | Problem: the block has lines that were not understood. The text gives their number. |
| 217 | `    ak = arg_of(b['args'], '--kernel')` | `ak`: the value of the option `--kernel` of the launch. |
| 218 | `    if ak and ak != 'all' and kernels and kernels != [ak]: problems.append(f'kernel {kernels} is not --kernel {ak}')` | Problem: the kernels in the output are not the kernel that `--kernel` asked for. The test is skipped for `--kernel all`, which runs three kernels. |
| 219 | `    out = {k: b[k] for k in ('folder', 'file', 'line', 'step', 'tag', 'binary', 'waited_s', 'load1', 'load5', 'load15',` | `out`: the result. It copies the header values of the block. This line names the first ten: folder, file, line number, step, tag, binary, waited seconds and the three load averages. |
| 220 | `                             'runnable', 'logins', 'utc', 'args', 'min_ms', 'thp', 'killed', 'failed')}` | Continues the list of copied values: the runnable tasks, the logins, the UTC time, the options, the interval length, the page setting and the texts of the `killed` and `failed` lines. |
| 221 | `    out.update(reps=reps, complete=not problems, problems=problems, cpus=arg_of(b['args'], '--cpus'))` | Adds four values. `reps`: the repetitions. `complete`: true when the list of problems is empty. `problems`: the list. `cpus`: the value of the option `--cpus`. |
| 222 | `    return out` | Returns the finished block. |

### Function `parse_launches`: the load record of each launch (lines 225 to 242)

| Line | Source | Explanation |
|---:|---|---|
| 225 | `def parse_launches(path, folder):` | Starts the function `parse_launches`. It reads the file `launches.txt` of one result folder. Before every launch the run script appends to that file one line that starts with `==` and the 6 lines of the list of the busiest processes. |
| 226 | `    out, cur = [], None` | `out`: the launches found so far. `cur`: the launch whose process lines are read now. |
| 227 | `    if not os.path.exists(path):` | Tests whether the file is missing. |
| 228 | `        return out` | Without the file the result is an empty list. |
| 229 | `    for line in open(path):` | Loop over the lines of the file. |
| 230 | `        m = re.match(r'^== (\S+)\.csv (\S+) utc (\S+) loadavg (\S+) (\S+) (\S+) (\S+) logins (\S+)', line)` | Tests whether the line is the first line of a launch. The pattern matches `==`, the name of the csv file, the tag, the word `utc` with the time, the word `loadavg` with the first four fields of `/proc/loadavg`, and the word `logins` with a value. It has 8 groups: the step (the file name without `.csv`), the tag, the UTC time, the load averages over 1, 5 and 15 minutes, the field with the runnable tasks, and the number of logins. |
| 231 | `        if m:` | A first line of a launch was found. |
| 232 | `            cur = dict(folder=folder, step=m.group(1), tag=m.group(2), utc=m.group(3), load1=float(m.group(4)),` | `cur`: a new launch entry with the folder, the step, the tag, the UTC time and the load average over 1 minute. |
| 233 | `                       runnable=int(m.group(7).split('/')[0]), logins=int(m.group(8)), busiest=[])` | Continues the entry: `runnable` is the number before the slash in group 7, the tasks that were runnable at this reading. Then come the number of logins and the empty list `busiest` for the process lines. |
| 234 | `            out.append(cur)` | Adds the entry to the list. |
| 235 | `        elif cur is not None:` | Every other line after the first launch line: a line of the process list of `ps`. |
| 236 | `            p = line.split(None, 2)` | `p`: the line split at white space into at most 3 pieces: the CPU use in percent, the user and the command name. |
| 237 | `            if len(p) == 3 and p[0] != '%CPU':` | Takes a line with 3 pieces that is not the title line of `ps`. That title line starts with `%CPU`. |
| 238 | `                try: cur['busiest'].append(dict(pcpu=float(p[0]), user=p[1], comm=p[2].strip()))` | Adds one process to the list `busiest` of the launch: its CPU use as a number (`pcpu`), its user and its command name. |
| 239 | `                except ValueError: pass` | A line whose first piece is not a number is skipped. |
| 240 | `    return out` | Returns the list of the launches. |

### Function `parse_core_events`: type number and event codes of the core counters (lines 243 to 260)

| Line | Source | Explanation |
|---:|---|---|
| 243 | `def parse_core_events(lines):` | Starts the function `parse_core_events`. It reads the lines of the file `A7-core-events.txt`, which step A7 of the run script wrote. |
| 244 | `    """A7-core-events.txt: one line '== <path of the PMU> type=<n>' per core PMU, then '<path>/events/<name>:event=<code>'."""` | Text of the function: the format of the file. For each core PMU it has one line with `==`, the path of the PMU and `type=` with a number. Then follow lines of the form `<path>/events/<name>:event=<code>`. PMU means performance monitoring unit: the counter hardware of a core. |
| 245 | `    pmus = []` | `pmus`: the list of the PMU entries, empty at first. |
| 246 | `    for ln, l in enumerate(lines, 1):` | Loop over the lines. `ln` is the line number, counted from 1. |
| 247 | `        m = re.match(r'^== (\S+) type=(\S*)', l)` | Tests for a PMU line. Group 1 holds the path of the PMU. Group 2 holds the type number that Linux gives to this counter device. It can be empty. |
| 248 | `        if m:` | A PMU line was found. |
| 249 | `            pmus.append(dict(name=os.path.basename(m.group(1)), type=m.group(2) or None, line=ln, events={}))` | Adds a PMU entry: its name (the last part of the path, for example `armv8_pmuv3_0`), its type number or `None`, the line number, and an empty dictionary for its events. |
| 250 | `            continue` | Goes to the next line. |
| 251 | `        m = re.match(r'^\S*/events/([^:/]+):event=(\S+)', l)` | Tests for an event line. The pattern matches a path that ends with `/events/`, then a name without colon and slash, then `:event=` and a code. Group 1 holds the event name, and group 2 holds its code, a text such as `0x0011`. |
| 252 | `        if m and pmus:` | An event line counts only after a PMU line. |
| 253 | `            pmus[-1]['events'][m.group(1)] = dict(code=m.group(2), line=ln)` | Stores the code and the line number under the event name, in the last PMU entry. |
| 254 | `    for p in pmus:` | Loop over the PMU entries. |
| 255 | `        p['n_events'] = len(p['events'])` | `n_events`: the number of events that the file lists for this PMU. |
| 256 | `        p['b8'] = [dict(event=ev, name=nm, **(p['events'].get(nm) or dict(code=None, line=None))) for ev, nm in B8_EVENTS]` | `b8`: one entry for each of the five events of lines 58 to 59: the words of the handoff note, the event name, and the code and the line number from the file. An event that the file does not list gets the code `None`. The script never fills in a code of its own. |
| 257 | `        p['b8_other'] = [dict(event=ev, name=nm, **p['events'][nm]) for ev, nm in B8_OTHER if nm in p['events']]` | `b8_other`: the same for the second candidate of line 60, only when the file lists it. |
| 258 | `    return pmus` | Returns the list of the PMU entries. |

### Function `parse_env`: `env.txt`, the files of step A7 and `stderr.txt` (lines 261 to 289)

| Line | Source | Explanation |
|---:|---|---|
| 261 | `def parse_env(folder):` | Starts the function `parse_env`. It reads `env.txt`, the files of step A7 and `stderr.txt` of one result folder. |
| 262 | `    d = dict(folder=os.path.basename(os.path.normpath(folder)), present=False, a7={})` | `d`: the result. `folder` is the last part of the folder path. `present` says whether `env.txt` exists. `a7` gets one entry per file of step A7. |
| 263 | `    p = os.path.join(folder, 'env.txt')` | `p`: the path of `env.txt`. |
| 264 | `    if os.path.exists(p):` | Tests whether `env.txt` exists. |
| 265 | `        d['present'] = True` | Marks the file as present. |
| 266 | `        t = open(p).read()` | `t`: the whole text of `env.txt`. |
| 267 | `        for key, rx in (('host', r'## host=(\S+)'), ('start_utc', r'## host=\S+ utc=(\S+)'),` | Starts a loop over nine pairs of a key and a pattern. Each pattern has one group, which holds the value. `host`: the word after `## host=` in the first line of `env.txt`. `start_utc`: the word after `utc=` in the same line, the UTC time at which the run script started. |
| 268 | `                        ('start_loadavg', r'## host=.* loadavg=(\S+ \S+ \S+ \S+)'), ('start_logins', r'## host=.* logins=(\d+)'),` | `start_loadavg`: the first four fields after `loadavg=` in the first line: the three load averages and the field with the runnable tasks. `start_logins`: the digits after `logins=`. |
| 269 | `                        ('steps', r' steps=(.*)'), ('thp', r'## thp=(.*?) defrag='), ('end_utc', r'## end utc=(\S+)'),` | `steps`: the rest of the line after ` steps=`, the list of the steps of the call. `thp`: the text from `## thp=` up to ` defrag=`, the system setting for transparent huge pages. `end_utc`: the word after `## end utc=`, the time of the end line. |
| 270 | `                        ('end_loadavg', r'## end utc=\S+ loadavg=(\S+ \S+ \S+ \S+)'), ('mem_available_kB', r'MemAvailable: (\d+)')):` | `end_loadavg`: the first four load fields of the end line. `mem_available_kB`: the digits after `MemAvailable: `, the available memory in kB at the start of the run script. |
| 271 | `            m = re.search(rx, t)` | Searches the text for the pattern. |
| 272 | `            d[key] = m.group(1) if m else None` | Stores the value under the key, or `None` when the text has no match. The run script writes the end line only after its last step. So a run that stopped early has `None` for the two end values. |
| 273 | `        d['skipped'] = re.findall(r'^(A\d skipped.*)$', t, re.M)` | `skipped`: every whole line that starts with `A`, one digit and the word `skipped`. The run script writes such a line when it skips step A3 for lack of memory. `re.M` lets the pattern match at each line of the text. |
| 274 | `        m = re.search(r'## busiest processes.*\n((?:.*\n){1,6})', t)` | Searches for the title line `## busiest processes`. The group holds up to 6 lines that follow it: the title line of `ps` and 5 processes. |
| 275 | `        d['busiest_at_start'] = [l.strip() for l in m.group(1).splitlines()[1:]] if m else []` | `busiest_at_start`: these lines without the first one (the title line of `ps`), each without spaces at its ends. Without a match the list is empty. |
| 276 | `    for f in sorted(glob.glob(os.path.join(folder, 'A7-*.txt'))):` | Loop over the files of the folder whose name starts with `A7-` and ends with `.txt`, in name order. |
| 277 | `        lines = open(f, errors='replace').read().splitlines()` | `lines`: the lines of the file. `errors='replace'` puts a mark in place of a byte that is not valid text. So the reading does not fail on such a byte. |
| 278 | `        e = dict(lines=len(lines))` | `e`: the entry of this file. It starts with the number of lines. |
| 279 | `        if f.endswith('A7-sve.txt'):` | The file `A7-sve.txt`. |
| 280 | `            e['sve_vector_length_bytes'] = next((l.strip() for l in lines if l.strip().isdigit()), None)` | `sve_vector_length_bytes`: the first line that holds digits only, kept as text. It is the default SVE vector length in bytes. SVE is the scalable vector instruction set of Arm. The value is `None` when no such line exists. |
| 281 | `        if f.endswith('A7-core-events.txt'):` | The file `A7-core-events.txt`. |
| 282 | `            e['pmus'] = [l for l in lines if l.startswith('== ')]` | `pmus`: the lines that start with `==`, one per counter device of the cores. |
| 283 | `            e['pmu_list'] = parse_core_events(lines)` | `pmu_list`: the PMU entries with their events (line 243). |
| 284 | `        d['a7'][os.path.basename(f)] = e` | Stores the entry under the file name. |
| 285 | `    p = os.path.join(folder, 'stderr.txt')` | `p`: the path of `stderr.txt`. |
| 286 | `    d['stderr_lines'] = len(open(p, errors='replace').read().splitlines()) if os.path.exists(p) else None` | `stderr_lines`: the number of lines of `stderr.txt`, the file with the error output of all benchmark processes of the folder. It is `None` when the file is missing. |
| 287 | `    return d` | Returns the result. |

### Function `two_groups`: may the pattern labels be used (choice C2) (lines 290 to 317)

| Line | Source | Explanation |
|---:|---|---|
| 290 | `def two_groups(qs):` | Starts the function `two_groups` (choice C2). `qs` is the list of the q values. The function decides whether q falls into two groups and whether the pattern labels may be used. |
| 291 | `    """Choice C2. qs: list of q values. Returns the verdict and its numbers."""` | Text of the function: it returns the verdict and its numbers. |
| 292 | `    r = dict(n=len(qs), two_groups=False, limits_fit=False, labels_usable=False, reason='')` | `r`: the result. It holds the number of values and three answers that start as false: `two_groups`, `limits_fit` and `labels_usable`. `reason` gets the text that says why an answer is false. |
| 293 | `    if len(qs) < 4:` | Fewer than 4 values cannot form two groups of at least 2 values each. |
| 294 | `        r['reason'] = f'only {len(qs)} repetitions with a q value' if qs else 'no repetition with a q value'` | The reason is then the number of repetitions with a q value, or the text `no repetition with a q value` for an empty list. |
| 295 | `        return r` | Returns the result with all answers false. |
| 296 | `    s = sorted(qs)` | `s`: the q values sorted upward. |
| 297 | `    gaps = [(s[i + 1] - s[i], i) for i in range(len(s) - 1)]` | `gaps`: for each pair of neighbours, the distance between the two values and the place of the lower one. |
| 298 | `    g, i = max(gaps)` | `g`: the largest distance. `i`: its place. When two distances are equal, the one at the higher place is taken. |
| 299 | `    lo, hi = s[:i + 1], s[i + 1:]` | `lo`: the lower group, the values up to that place. `hi`: the upper group, the values above the distance. |
| 300 | `    r.update(gap=g, gap_from=lo[-1], gap_to=hi[0], n_lower=len(lo), n_upper=len(hi), lower_min=lo[0], lower_max=lo[-1],` | Stores the numbers of the test: the distance (`gap`), the two values at its ends, the sizes of the two groups, and the lowest and the highest value of the lower group. |
| 301 | `             upper_min=hi[0], upper_max=hi[-1], q_min=s[0], q_max=s[-1],` | Continues the numbers: the lowest and the highest value of the upper group, and the lowest and the highest q of all. |
| 302 | `             n_split=sum(q < Q_SPLIT for q in s), n_uniform=sum(q > Q_UNIFORM for q in s),` | Continues the numbers: how many q are below 0.65 (`n_split`) and how many are above 0.85 (`n_uniform`). These are the counts that the pattern rule alone would give. |
| 303 | `             n_between=sum(Q_SPLIT <= q <= Q_UNIFORM for q in s))` | Continues the numbers: how many q lie from 0.65 to 0.85 (`n_between`). |
| 304 | `    why = []` | `why`: the list of the conditions that fail, empty at first. |
| 305 | `    if min(len(lo), len(hi)) < 2: why.append('one side of the largest distance has fewer than 2 values')` | Condition 1 fails when one of the two groups has fewer than 2 values. |
| 306 | `    if g < GAP_MIN: why.append(f'the largest distance between neighbouring q values is {g:.3f}, below {GAP_MIN:.2f}')` | Condition 2 fails when the largest distance is below 0.10. The text gives the distance with 3 decimals. |
| 307 | `    if g <= max(lo[-1] - lo[0], hi[-1] - hi[0]): why.append('the largest distance is not larger than the width of each group')` | Condition 3 fails when the distance is not larger than the width of the wider group. The width of a group is its highest value minus its lowest. |
| 308 | `    r['two_groups'] = not why` | `two_groups`: true when no condition failed. |
| 309 | `    if r['two_groups']:` | Only for two groups: the test of the limits. |
| 310 | `        r['limits_fit'] = lo[-1] < Q_SPLIT and hi[0] > Q_UNIFORM` | `limits_fit`: true when the highest value of the lower group is below 0.65 and the lowest value of the upper group is above 0.85. |
| 311 | `        if not r['limits_fit']:` | Tests whether the limits do not fit. |
| 312 | `            why.append(f'the groups do not lie on the two sides of the limits {Q_SPLIT} and {Q_UNIFORM}')` | Adds the reason: the groups do not lie on the two sides of the limits 0.65 and 0.85. |
| 313 | `    r['labels_usable'] = r['two_groups'] and r['limits_fit']` | `labels_usable`: true only when q falls into two groups and the limits fit. Only then does the analysis give a repetition the label split or uniform (lines 665 to 668). |
| 314 | `    r['reason'] = '; '.join(why)` | `reason`: all reasons in one text, joined with a semicolon and a space. |
| 315 | `    return r` | Returns the result. |

### Small helpers: `rng`, `labels_of`, `one_label`, `rep_brief`, `kernel_name`, `kname_of` (lines 318 to 349)

| Line | Source | Explanation |
|---:|---|---|
| 318 | `def rng(v):` | Starts the function `rng`. It describes a list of numbers by four values. |
| 319 | `    return dict(n=len(v), min=min(v), median=st.median(v), max=max(v)) if v else dict(n=0, min=None, median=None, max=None)` | Returns the count, the lowest value, the median and the highest value of the list. For an empty list the count is 0 and the three values are `None`. Many results of this file have this form. |
| 322 | `def labels_of(reps):` | Starts the function `labels_of`. |
| 323 | `    return [r['label'] for r in reps]` | Returns the pattern labels of a list of repetitions. |
| 326 | `def one_label(labels):` | Starts the function `one_label` (choice C5). It gives one label for a list of labels. |
| 327 | `    """Choice C5."""` | Text of the function: it names choice C5. |
| 328 | `    if not labels or any(l is None for l in labels): return None` | Returns `None` for an empty list, or when one label is missing. The labels are missing when the test of the two groups did not allow them. |
| 329 | `    return labels[0] if len(set(labels)) == 1 else 'mixed'` | Returns the label when all labels are equal, and the word `mixed` when they differ. |
| 332 | `def rep_brief(b, r):` | Starts the function `rep_brief`. It makes the short form of one repetition `r` of the block `b` for the json file. |
| 333 | `    return dict(tag=b['tag'], rep=r['rep'], total_GBps=r['total_GBps'], q=r['q'], label=r['label'], label_rule=r['label_rule'],` | The short form starts with the tag of the block, the repetition number, the total in GB/s, q, the label that may be used and the label of the rule. |
| 334 | `                passes_per_thread=r['passes_per_thread'], below_50_passes=r['below_50_passes'],` | Continues the short form: the passes per thread and the mark for fewer than 50 passes. |
| 335 | `                mesh0=r['mesh0'], mesh1=r['mesh1'], fastest_half=r['fastest_half'])` | Continues the short form: the two mesh entries (count, sum and median of the thread rates) and the counts of the fastest half. |
| 338 | `def kernel_name(tag):` | Starts the function `kernel_name`. It takes the kernel name from a tag of step A1 or A2. |
| 339 | `    return tag.rsplit('-r', 1)[0]` | Cuts the tag at its last `-r` and returns the part before it. The tag `read_old-r1` gives `read_old`. |
| 342 | `def kname_of(b, r):` | Starts the function `kname_of`. It gives the kernel name of a repetition of any step in the form of the A1 tags. |
| 343 | `    """Kernel name as in the A1 tags (read_old, read_new, asmread, ...), for a repetition of any step."""` | Text of the function: the names are those of the A1 tags, such as `read_old`, `read_new` and `asmread`. |
| 344 | `    if b['step'] in ('A1', 'A2'): return kernel_name(b['tag'])` | For the steps A1 and A2: the kernel name from the tag (line 338). |
| 345 | `    if b['step'] == 'A4': return b['tag'].rsplit('-', 1)[0]` | For step A4: the tag without its last part, the thread count. The tag `read_old-64+16` gives `read_old`. |
| 346 | `    if b['step'] == 'A3': return r['kernel'] + ('_old' if b['binary'] == 'bw_old' else '_new')` | For step A3: the kernel name of the output line with `_old` or `_new` added, by the binary of the block. The read rows of `bw_old` give `read_old`. |
| 347 | `    return r['kernel']` | For every other step: the kernel name of the output line. |

### Function `q_groups`: where the q values lie (lines 350 to 366)

| Line | Source | Explanation |
|---:|---|---|
| 350 | `def q_groups(qrows):` | Starts the function `q_groups`. It describes where the q values lie. `qrows` is the list of the q rows that line 662 builds. |
| 351 | `    """Where the q values lie: the read kernels at the full count 64+56, and the rows below the split limit."""` | Text of the function: it looks at the read kernels at the full thread count 64+56, and at the rows below the split limit. |
| 352 | `    def grp(names):` | Starts the inner function `grp`. It summarises the rows of the given kernel names. |
| 353 | `        v = [x for x in qrows if x['count'] == '64+56' and x['kname'] in names]` | `v`: the rows with 64 threads on mesh 0 and 56 on mesh 1 whose kernel name is in `names`. Rows of all steps count. |
| 354 | `        return dict(n=len(v), q=rng([x['q'] for x in v]), mesh0_median=rng([x['mesh0_median'] for x in v]), mesh1_median=rng([x['mesh1_median'] for x in v]),` | Returns the number of rows, the range of their q, and the ranges of their median thread rate on mesh 0 and on mesh 1. |
| 355 | `                    n_split=sum(x['q'] < Q_SPLIT for x in v), n_uniform=sum(x['q'] > Q_UNIFORM for x in v))` | Continues the result: how many of these q are below 0.65 and how many are above 0.85. |
| 356 | `    old, lo = grp(['read_old']), grp(['read_new', 'asmread'])` | `old`: the summary for the old read kernel. `lo`: the summary for the two load-only read kernels together, the new read kernel and `asmread`. |
| 357 | `    below, between = {}, {}` | `below` and `between`: two dictionaries of counters, empty at first. |
| 358 | `    for x in qrows:` | Loop over all q rows. |
| 359 | `        if x['q'] < Q_SPLIT: below[(x['kname'], x['count'])] = below.get((x['kname'], x['count']), 0) + 1` | A q below 0.65: adds 1 to the counter of its kernel name and thread count. |
| 360 | `        elif x['q'] <= Q_UNIFORM: between[(x['kname'], x['step'])] = between.get((x['kname'], x['step']), 0) + 1` | A q from 0.65 to 0.85: adds 1 to the counter of its kernel name and step. |
| 361 | `    sep = bool(old['n'] and lo['n'] and (old['q']['max'] < lo['q']['min'] or lo['q']['max'] < old['q']['min']))` | `sep`: true when both summaries have rows and their ranges of q do not overlap: the highest q of one lies below the lowest q of the other. |
| 362 | `    return dict(count='64+56', read_old=old, load_only_read=lo, ranges_separate=sep,` | Returns the result: the thread count `64+56`, the two summaries and the answer `ranges_separate`. |
| 363 | `                below_split=[dict(kname=k, count=c, n=n) for (k, c), n in sorted(below.items(), key=lambda z: -z[1])],` | Continues the result: `below_split`, the counters of line 359 as a list, largest count first. |
| 364 | `                between=[dict(kname=k, step=s_, n=n) for (k, s_), n in sorted(between.items(), key=lambda z: -z[1])])` | Continues the result: `between`, the counters of line 360 as a list, largest count first. |

### Function `step_a12`: the six kernels of step A1 or A2 (lines 367 to 385)

| Line | Source | Explanation |
|---:|---|---|
| 367 | `def step_a12(blocks):` | Starts the function `step_a12`. It summarises step A1 or step A2: for each of the six kernels, the repetitions of both rounds. |
| 368 | `    """A1 or A2: per kernel (read_old ... asmwrite) the repetitions of both rounds."""` | Text of the function: the same in one sentence. The kernel names run from `read_old` to `asmwrite`. |
| 369 | `    out = {}` | `out`: the result, one entry per kernel. |
| 370 | `    for b in blocks:` | Loop over the blocks of the step. |
| 371 | `        k = out.setdefault(kernel_name(b['tag']), dict(binary=b['binary'], min_ms=b['min_ms'], reps=[]))` | `k`: the entry of the kernel of this block. The key is the kernel name from the tag, for example `read_old`. The entry is made at the first block of the kernel, with the binary, the interval length and an empty list of repetitions. |
| 372 | `        k['reps'] += [rep_brief(b, r) for r in b['reps']]` | Adds the short forms of the repetitions of the block. With 2 rounds of 3 repetitions a kernel gets 6 entries. |
| 373 | `    for k in out.values():` | Loop over the kernels. |
| 374 | `        r = k['reps']` | `r`: the repetitions of the kernel. |
| 375 | `        k['total_GBps'] = rng([x['total_GBps'] for x in r])` | `total_GBps`: the count, the lowest, the median and the highest of the totals of the repetitions. A total is the column `aggregate_GBps` of a data line (line 150). |
| 376 | `        k['q'] = rng([x['q'] for x in r if x['q'] is not None])` | `q`: the same four values for q. |
| 377 | `        k['labels'] = sorted(set(str(x['label']) for x in r)) if all(x['label'] for x in r) else None` | `labels`: the different pattern labels of the repetitions, sorted. It is `None` when a repetition has no label, that is when the labels are not used. |
| 378 | `        k['passes_per_thread'] = rng([x['passes_per_thread'] for x in r])` | `passes_per_thread`: the range of the passes per thread. |
| 379 | `        k['n_below_50_passes'] = sum(x['below_50_passes'] for x in r)` | `n_below_50_passes`: the number of repetitions with fewer than 50 passes per thread. |
| 380 | `        for m in ('mesh0', 'mesh1'):` | Loop over the two mesh names. |
| 381 | `            k[m + '_median'] = rng([x[m]['median'] for x in r if x[m]['median'] is not None])` | `mesh0_median` or `mesh1_median`: the range of the medians of the thread rates of this mesh, one median per repetition. Its entry `median` is the median over the repetitions of the median over the threads. |
| 382 | `            k[m + '_sum'] = rng([x[m]['sum'] for x in r if x[m]['sum'] is not None])` | `mesh0_sum` or `mesh1_sum`: the range of the sums of the thread rates of this mesh, one sum per repetition. |
| 383 | `    return out` | Returns the result. |

### Function `compare_a1_a2`: short interval against long interval (choice C11) (lines 386 to 409)

| Line | Source | Explanation |
|---:|---|---|
| 386 | `def compare_a1_a2(a1, a2):` | Starts the function `compare_a1_a2`. It compares the totals of step A1 (repetitions of at least 0.5 s) with those of step A2 (at least 6 s or 15 s), kernel by kernel. It also forms the reading of choice C11. |
| 387 | `    out = {}` | `out`: one entry per kernel. |
| 388 | `    for k in a1:` | Loop over the kernels of step A1. |
| 389 | `        if k in a2 and a1[k]['total_GBps']['n'] and a2[k]['total_GBps']['n']:` | Takes a kernel only when both steps have totals for it. |
| 390 | `            s, l = a1[k]['total_GBps'], a2[k]['total_GBps']` | `s`: the range of the totals with the short interval (A1). `l`: the range with the long interval (A2). |
| 391 | `            lt = [x['total_GBps'] for x in a2[k]['reps']]` | `lt`: the single totals of the repetitions of A2. |
| 392 | `            out[k] = dict(short_ms=a1[k]['min_ms'], long_ms=a2[k]['min_ms'], short=s, long=l, n_long=len(lt),` | The entry of the kernel starts with the two interval lengths in ms, the two ranges and the number of totals of A2. |
| 393 | `                          n_long_outside_short=sum(1 for v in lt if v < s['min'] or v > s['max']),` | `n_long_outside_short`: how many totals of A2 lie below the lowest total of A1 or above its highest. |
| 394 | `                          change_GBps=l['median'] - s['median'], change_pct=100 * (l['median'] / s['median'] - 1),` | `change_GBps`: the median total of A2 minus the median total of A1. `change_pct`: the same change in percent of the A1 median. |
| 395 | `                          ranges_overlap=not (l['min'] > s['max'] or l['max'] < s['min']))` | `ranges_overlap`: false only when all totals of A2 lie above all totals of A1, or all lie below. |
| 396 | `    d = {}` | `d`: the values for the difference between the old and the new read kernel. |
| 397 | `    for name, a in (('short', a1), ('long', a2)):` | Loop over the two steps under the names `short` (A1) and `long` (A2). |
| 398 | `        if 'read_old' in a and 'read_new' in a and a['read_old']['total_GBps']['n'] and a['read_new']['total_GBps']['n']:` | Takes a step only when it has totals for both `read_old` and `read_new`. |
| 399 | `            d[name] = a['read_old']['total_GBps']['median'] - a['read_new']['total_GBps']['median']` | `short` or `long`: the median total of the old read kernel minus the median total of the new read kernel in that step, in GB/s. The two medians come from different processes and different binaries. |
| 400 | `            o, n = a['read_old']['total_GBps'], a['read_new']['total_GBps']` | `o`: the range of the totals of the old read kernel. `n`: the range for the new read kernel. |
| 401 | `            d[name + '_range'] = [o['min'] - n['max'], o['max'] - n['min']]` | `short_range` or `long_range`: the range in which this difference can lie. It goes from the lowest old total minus the highest new total to the highest old total minus the lowest new total. |
| 402 | `    order = None` | `order`: the reading for the order of the later steps. It is `None` when a range is missing. |
| 403 | `    if 'short_range' in d and 'long_range' in d:        # choice C11` | Only when both ranges exist. The comment names choice C11. |
| 404 | `        s, l = d['short_range'], d['long_range']` | `s`: the range of the difference with the short interval. `l`: the range with the long interval. |
| 405 | `        changed = l[0] > s[1] or l[1] < s[0]` | `changed`: true when the two ranges do not overlap: the long range lies wholly above or wholly below the short range. |
| 406 | `        order = dict(changed=changed, difference_smaller_with_long=abs(d['long']) < abs(d['short']))` | `order`: two answers. `changed` is the answer of choice C11 to the question whether A2 changed the totals. `difference_smaller_with_long` is true when the absolute difference of the medians is smaller with the long interval. |
| 407 | `    return dict(kernels=out, old_minus_new_read_GBps=d, order_reading=order)` | Returns the entries per kernel, the values of the difference and the reading. |

### Function `step_a3`: old read with one and with two buffers per thread (lines 410 to 437)

| Line | Source | Explanation |
|---:|---|---|
| 410 | `def step_a3(blocks):` | Starts the function `step_a3`. It summarises step A3: the old read kernel with one buffer per thread and with two, at two interval lengths. |
| 411 | `    groups = {}` | `groups`: one entry per case, such as one buffer at 500 ms. |
| 412 | `    for b in blocks:` | Loop over the blocks of the step. |
| 413 | `        m = re.match(r'(onebuf\|twobuf)-ms(\d+)-(\d+)$', b['tag'])` | Tests the tag of the block. The pattern matches `onebuf` or `twobuf`, then `-ms` with the interval length in ms, then a hyphen with the process number. Group 1 holds the buffer word, group 2 the interval length and group 3 the process number. |
| 414 | `        if not m: continue` | A block with another tag is skipped. |
| 415 | `        g = groups.setdefault(f'{m.group(1)}-ms{m.group(2)}', dict(buffers=1 if m.group(1) == 'onebuf' else 2, min_ms=int(m.group(2)), processes=[]))` | `g`: the group of this block, with a key such as `onebuf-ms500`. It is made at the first block of the case, with the number of buffers (1 or 2), the interval length and an empty list of processes. |
| 416 | `        rr = [r for r in b['reps'] if r['kernel'] == 'read']          # compare only the rows of the read kernel` | `rr`: the repetitions of the read kernel only. A process with two buffers also has repetitions of write and copy. By the comment only the rows of the read kernel are compared. |
| 417 | `        g['processes'].append(dict(tag=b['tag'], reps=[rep_brief(b, r) for r in rr],` | Adds the process to its group: the tag and the short forms of its read repetitions. |
| 418 | `                                   total_median_GBps=st.median([r['total_GBps'] for r in rr]) if rr else None,` | Continues the process entry: the median of the totals of its read repetitions, in GB/s. |
| 419 | `                                   q_median=st.median([r['q'] for r in rr if r['q'] is not None]) if rr else None,` | Continues the process entry: the median of the q values of its read repetitions. |
| 420 | `                                   label=one_label(labels_of(rr)), other_kernels=sorted(set(r['kernel'] for r in b['reps']) - {'read'})))` | Continues the process entry: one label for its read repetitions (line 326), and the names of the other kernels that the process also timed. |
| 421 | `    for g in groups.values():` | Loop over the groups. |
| 422 | `        g['total_GBps'] = rng([r['total_GBps'] for p in g['processes'] for r in p['reps']])` | `total_GBps`: the range of the totals of all read repetitions of the group. |
| 423 | `        g['q'] = rng([r['q'] for p in g['processes'] for r in p['reps'] if r['q'] is not None])` | `q`: the range of their q values. |
| 424 | `        g['label'] = one_label([r['label'] for p in g['processes'] for r in p['reps']])` | `label`: one label for all read repetitions of the group, or `mixed`, or `None`. |
| 425 | `        g['n_below_50_passes'] = sum(r['below_50_passes'] for p in g['processes'] for r in p['reps'])` | `n_below_50_passes`: the number of read repetitions of the group with fewer than 50 passes per thread. |
| 426 | `    cmp = {}` | `cmp`: the comparison of one buffer with two buffers, one entry per interval length. |
| 427 | `    for ms in sorted(set(g['min_ms'] for g in groups.values())):` | Loop over the interval lengths that occur, in rising order. |
| 428 | `        a, b2 = groups.get(f'onebuf-ms{ms}'), groups.get(f'twobuf-ms{ms}')` | `a`: the group with one buffer at this interval length. `b2`: the group with two buffers. |
| 429 | `        if a and b2 and a['total_GBps']['n'] and b2['total_GBps']['n']:` | Compares only when both groups exist and have totals. |
| 430 | `            cmp[str(ms)] = dict(one_label=a['label'], two_label=b2['label'],` | The entry starts with the labels of the two groups. |
| 431 | `                                same_label=(a['label'] == b2['label']) if a['label'] and b2['label'] else None,` | `same_label`: whether the two labels are equal. It is `None` when a label is missing. |
| 432 | `                                q_one=a['q'], q_two=b2['q'], total_one=a['total_GBps'], total_two=b2['total_GBps'],` | Continues the entry: the two ranges of q and the two ranges of the totals. |
| 433 | `                                total_change_GBps=b2['total_GBps']['median'] - a['total_GBps']['median'],` | `total_change_GBps`: the median total with two buffers minus the median total with one buffer. |
| 434 | `                                q_ranges_overlap=not (a['q']['min'] > b2['q']['max'] or a['q']['max'] < b2['q']['min']))` | `q_ranges_overlap`: false only when all q of one group lie above all q of the other. |
| 435 | `    return dict(groups=groups, compare=cmp)` | Returns the groups and the comparison. |

### Function `step_a4`: q against the thread count, and the bracket of choice C7 (lines 438 to 485)

| Line | Source | Explanation |
|---:|---|---|
| 438 | `def step_a4(blocks):` | Starts the function `step_a4`. It summarises step A4: the pattern against the thread count per mesh, for the old read kernel and for `asmread`. It also looks for the bracket of choice C7. |
| 439 | `    out = {}` | `out`: one entry per kernel. |
| 440 | `    for b in blocks:` | Loop over the blocks of the step. |
| 441 | `        m = re.match(r'(.+)-(\d+\+\d+)$', b['tag'])` | Tests the tag. The pattern matches a kernel name, a hyphen, and at the end a thread count of the form digits, `+`, digits. Group 1 holds the kernel name. Group 2 holds the count, for example `64+16`. |
| 442 | `        if not m: continue` | A block with another tag is skipped. |
| 443 | `        k = out.setdefault(m.group(1), dict(binary=b['binary'], counts={}))` | `k`: the entry of the kernel, made at its first block with the binary and an empty dictionary of counts. |
| 444 | `        k['counts'][m.group(2)] = dict(reps=[rep_brief(b, r) for r in b['reps']], label=one_label(labels_of(b['reps'])),` | The entry of this thread count starts with the short forms of its repetitions and with one label for them (line 326): the common label, `mixed`, or `None` when the labels are not used. |
| 445 | `                                       q=rng([r['q'] for r in b['reps'] if r['q'] is not None]),` | Continues the entry: the range of the q values of the repetitions. |
| 446 | `                                       total_GBps=rng([r['total_GBps'] for r in b['reps']]),` | Continues the entry: the range of their totals in GB/s. |
| 447 | `                                       n_below_50_passes=sum(r['below_50_passes'] for r in b['reps']))` | Continues the entry: the number of repetitions with fewer than 50 passes per thread. |
| 448 | `    for k in out.values():` | Loop over the kernels. |
| 449 | `        k['series'] = {}` | `series`: one entry for each of the two series of lines 62 to 63. |
| 450 | `        for sname, order in A4_SERIES.items():` | Loop over the two series. `sname` is the name of the series, and `order` is its list of counts in rising order. |
| 451 | `            have = [c for c in order if c in k['counts']]` | `have`: the counts of the series that have a block, in the order of the series. |
| 452 | `            missing = [c for c in order if c not in k['counts']]` | `missing`: the counts of the series without a block. |
| 453 | `            labels = [k['counts'][c]['label'] for c in have]` | `labels`: the labels of the counts in `have`. |
| 454 | `            s = dict(counts=have, missing=missing, labels=labels, changes=[], bracket=None, note='')` | `s`: the entry of the series, with these three lists, an empty list of changes, no bracket and an empty note. |
| 455 | `            if not have or any(l is None for l in labels):` | Tests whether the series has no count, or a count without a label. |
| 456 | `                s['note'] = 'labels not available'` | The note is then `labels not available`. No change and no bracket is looked for. This is the case whenever the labels are not used. |
| 457 | `            else:` | The case that every count has a label. |
| 458 | `                s['changes'] = [dict(lower=have[i], upper=have[i + 1], from_label=labels[i], to_label=labels[i + 1])` | `changes`: one entry for each pair of neighbouring counts in `have` whose labels differ: the lower count, the upper count, the label of the lower and the label of the upper. |
| 459 | `                                for i in range(len(have) - 1) if labels[i] != labels[i + 1]]` | Continues the list of line 458: the loop over the neighbours and the test that the two labels differ. |
| 460 | `                # a change over a missing count is not a change between two neighbouring tested counts of the plan's grid` | Comment: a change over a missing count is not a change between two neighbouring tested counts of the grid of the plan. |
| 461 | `                for c in s['changes']:` | Loop over the changes. |
| 462 | `                    c['counts_missing_between'] = [x for x in order[order.index(c['lower']) + 1:order.index(c['upper'])]]` | `counts_missing_between`: the counts of the series that lie between the two counts of the change and have no block. The code only stores this list. It does not drop such a change, and neither this file nor the page generator reads the list again. So a bracket can span a missing count (line 467). |
| 463 | `                # choice C7: the bracket is looked for among the counts with threads on both meshes (64+0 is left out)` | Comment: choice C7. The bracket is looked for among the counts with threads on both meshes. The count 64+0 is left out. |
| 464 | `                both = [c for c in s['changes'] if not c['lower'].endswith('+0')]` | `both`: the changes whose lower count does not end with `+0`. So the change from 64+0 to the next count is left out. |
| 465 | `                pure = len(both) == 1 and {both[0]['from_label'], both[0]['to_label']} == {'split', 'uniform'}` | `pure`: true when exactly one change is left and its two labels are `split` and `uniform`, in any order. |
| 466 | `                if pure:` | The case of one clear change. |
| 467 | `                    s['bracket'] = [both[0]['lower'], both[0]['upper']]` | `bracket`: the lower and the upper count of that change. The pattern changes between these two counts. |
| 468 | `                elif not both:` | The case that no change is left. |
| 469 | `                    two = [l for c, l in zip(have, labels) if not c.endswith('+0')]` | `two`: the labels of the counts with threads on both meshes. |
| 470 | `                    s['note'] = f'no change of pattern: every count with threads on both meshes is {two[0]}' if two else 'no count with threads on both meshes'` | The note says that there is no change of pattern, and names the one label that all these counts have. When the series has no such count, the note says so. |
| 471 | `                else:` | The case of more than one change, or of a change that involves the label `between` or `mixed`. |
| 472 | `                    s['note'] = 'more than one change, or a change that is not between split and uniform'` | The note names this case. No bracket is given. |
| 473 | `            k['series'][sname] = s` | Stores the entry of the series. |
| 474 | `    cmp = {}` | `cmp`: the comparison of the brackets of the two kernels, one entry per series. |
| 475 | `    ks = list(out)` | `ks`: the kernel names in the order in which their first blocks were read. |
| 476 | `    if 'read_old' in out and 'asmread' in out:` | Compares only when both kernels are present. |
| 477 | `        for sname in A4_SERIES:` | Loop over the two series. |
| 478 | `            a, b2 = out['read_old']['series'][sname], out['asmread']['series'][sname]` | `a`: the entry of the series for the old read kernel. `b2`: the entry for `asmread`. |
| 479 | `            if a['bracket'] and b2['bracket']:` | Tests whether both kernels have a bracket in this series. |
| 480 | `                cmp[sname] = 'equal' if a['bracket'] == b2['bracket'] else 'different'` | The answer is `equal` when the two brackets are the same pair of counts, and `different` when they are not. The plan calls equal brackets not resolved at this grid. |
| 481 | `            else:` | The case that at least one kernel has no bracket. |
| 482 | `                cmp[sname] = 'no bracket for at least one kernel'` | The answer is then the text `no bracket for at least one kernel`. |
| 483 | `    return dict(kernels=out, bracket_compare=cmp, kernel_order=ks)` | Returns the entries per kernel, the comparison and the order of the kernels. |

### Functions `limit_check`, `level_check`, `a5_changes`: the level limits (C9, C6) (lines 486 to 521)

| Line | Source | Explanation |
|---:|---|---|
| 486 | `def limit_check(rates):` | Starts the function `limit_check` (choice C9). `rates` holds all rates of one CPU, in GB/s. For each of the two level limits the function finds the nearest rates on both sides and decides whether the limit separates the rates. |
| 487 | `    """Choice C9. rates: all rates of one CPU. For each limit: the nearest rates on its two sides, and whether it separates them."""` | Text of the function: the same in one sentence. |
| 488 | `    out = dict(n=len(rates), min=min(rates), max=max(rates), limits=[], labels_usable=True)` | `out`: the result. It starts with the number of rates, the lowest and the highest rate, an empty list for the two limits, and `labels_usable` as true. |
| 489 | `    for L in (LOW_BELOW, HIGH_ABOVE):` | Loop over the two limits, 69.0 GB/s and 70.5 GB/s. |
| 490 | `        below = [v for v in rates if v < L]; above = [v for v in rates if v >= L]` | `below`: the rates below the limit. `above`: the rates at or above the limit. |
| 491 | `        e = dict(limit=L, n_below=len(below), n_at_or_above=len(above), nearest_below=max(below) if below else None,` | `e`: the entry of this limit. It holds the limit, the two counts, and `nearest_below`, the highest rate below the limit. |
| 492 | `                 nearest_at_or_above=min(above) if above else None, n_within=sum(1 for v in rates if abs(v - L) <= LEVEL_GAP_MIN))` | Continues the entry: `nearest_at_or_above`, the lowest rate at or above the limit. `n_within`: the number of rates that lie at most 0.25 GB/s away from the limit. |
| 493 | `        e['empty_range'] = e['nearest_at_or_above'] - e['nearest_below'] if below and above else None` | `empty_range`: the nearest rate at or above the limit minus the nearest rate below it, in GB/s. It is `None` when all rates lie on one side. |
| 494 | `        e['separates'] = e['empty_range'] is None or e['empty_range'] >= LEVEL_GAP_MIN` | `separates`: true when all rates lie on one side of the limit, or when the empty range is at least 0.25 GB/s wide. |
| 495 | `        out['labels_usable'] = out['labels_usable'] and e['separates']` | `labels_usable` stays true only when both limits separate the rates. |
| 496 | `        out['limits'].append(e)` | Adds the entry of the limit to the result. |
| 497 | `    return out` | Returns the result for this CPU. |
| 500 | `def level_check(a5, a6):` | Starts the function `level_check`. It applies the limit check to each CPU of the steps A5 and A6. It also removes the level changes of a CPU whose labels are not usable. |
| 501 | `    by = {}` | `by`: the rates per CPU. |
| 502 | `    for p in a5['processes'] + a6['processes']:` | Loop over all processes of step A5 and of step A6. |
| 503 | `        if p.get('cpu') is not None:` | Takes a process only when its CPU is known. |
| 504 | `            by.setdefault(p['cpu'], []).extend(p['rates_GBps'])` | Adds the rates of the process to the list of its CPU. So the rates of A5 and A6 on one CPU are taken together. The rates of the A6 processes with `--no-thp` are among them. |
| 505 | `    cpus = {str(c): limit_check(v) for c, v in sorted(by.items()) if v}` | `cpus`: the limit check of each CPU that has rates, under the CPU number as text. |
| 506 | `    allr = sorted(x for v in by.values() for x in v)` | `allr`: all rates of all CPUs, sorted upward. |
| 507 | `    gaps = sorted(((allr[i + 1] - allr[i], allr[i], allr[i + 1]) for i in range(len(allr) - 1)), reverse=True)[:2]` | `gaps`: the two widest empty ranges between neighbouring rates of `allr`, each with its width and its two ends. |
| 508 | `    for p in a5['processes']:` | Loop over the processes of step A5. |
| 509 | `        ok = cpus.get(str(p['cpu']), {}).get('labels_usable', True)` | `ok`: whether the labels of the CPU of this process are usable. It is true when the CPU has no entry. |
| 510 | `        p['labels_usable'] = ok` | Stores the answer in the process. |
| 511 | `        p['n_below_low_limit'] = sum(1 for v in p['rates_GBps'] if v < LOW_BELOW)` | `n_below_low_limit`: the number of intervals of the process with a rate below 69.0 GB/s. |
| 512 | `        if not ok:` | The case that the labels of the CPU are not usable. |
| 513 | `            p['changes'] = []                      # choice C9: no level change is given where the limit does not separate the rates` | Empties the list of level changes of the process. By the comment this is choice C9: no level change is given where a limit does not separate the rates. |
| 514 | `    return dict(gap_min_GBps=LEVEL_GAP_MIN, cpus=cpus, largest_empty_ranges=[dict(width=g, low=a, high=b) for g, a, b in gaps])` | Returns the smallest accepted empty range (0.25 GB/s), the check per CPU, and the two widest empty ranges of all rates. |
| 517 | `def a5_changes(levels):` | Starts the function `a5_changes` (choice C6). `levels` is the list of the level labels of the intervals of one process, in time order. |
| 518 | `    seq = [(i, l) for i, l in enumerate(levels) if l != 'changing']` | `seq`: the intervals with the label `low` or `high`, each with its number, counted from 0. Intervals with the label `changing` are left out. |
| 519 | `    return [dict(at_interval=seq[j][0], from_level=seq[j - 1][1], to_level=seq[j][1]) for j in range(1, len(seq)) if seq[j][1] != seq[j - 1][1]]` | Returns one entry for each place where a label of `seq` differs from the label before it: the number of the first interval with the new label, the old label and the new label. |

### Function `step_a5`: 30 intervals of one thread at 8 MiB (lines 522 to 542)

| Line | Source | Explanation |
|---:|---|---|
| 522 | `def step_a5(blocks):` | Starts the function `step_a5`. It summarises step A5: `asmread` with one thread and a buffer of 8 MiB, 30 intervals per process, 2 processes on each of 2 CPUs. |
| 523 | `    procs = []` | `procs`: one entry per process. |
| 524 | `    for b in blocks:` | Loop over the blocks of the step. |
| 525 | `        m = re.match(r'cpu(\d+)-proc(\d+)$', b['tag'])` | Tests the tag. The pattern matches `cpu`, a number, `-proc` and a number. Group 1 holds the CPU and group 2 the process number, 1 or 2. |
| 526 | `        if not m: continue` | A block with another tag is skipped. |
| 527 | `        rates = [r['total_GBps'] for r in b['reps']]` | `rates`: the totals of the repetitions of the block, in file order, which is time order. With one thread the total is the rate of the thread: its bytes divided by its elapsed time, in GB/s. |
| 528 | `        lv = [level(x) for x in rates]` | `lv`: the level label of each rate (line 102). |
| 529 | `        procs.append(dict(tag=b['tag'], cpu=int(m.group(1)), proc=int(m.group(2)), waited_s=b['waited_s'], utc=b['utc'], thp=b['thp'],` | The entry of the process starts with the tag, the CPU, the process number, the seconds that the run script waited before the launch, the UTC time of the launch and the page setting. |
| 530 | `                          rates_GBps=rates, levels=lv, n_low=lv.count('low'), n_changing=lv.count('changing'), n_high=lv.count('high'),` | Continues the entry: the rates, their labels, and the numbers of low, changing and high intervals. |
| 531 | `                          changes=a5_changes(lv), first_level=lv[0] if lv else None, last_level=lv[-1] if lv else None,` | Continues the entry: the level changes (line 517), and the labels of the first and of the last interval. |
| 532 | `                          rate=rng(rates), n_intervals=len(rates)))` | Continues the entry: the range of the rates and the number of intervals. |
| 533 | `    pairs = []` | `pairs`: one entry per CPU, for the first and the second process on it. |
| 534 | `    for cpu in sorted(set(p['cpu'] for p in procs)):` | Loop over the CPUs, in rising order. |
| 535 | `        p1 = next((p for p in procs if p['cpu'] == cpu and p['proc'] == 1), None)` | `p1`: process 1 of this CPU, or `None`. |
| 536 | `        p2 = next((p for p in procs if p['cpu'] == cpu and p['proc'] == 2), None)` | `p2`: process 2 of this CPU, or `None`. |
| 537 | `        pairs.append(dict(cpu=cpu, have_both=bool(p1 and p2), second_waited_s=p2['waited_s'] if p2 else None,` | The entry of the pair: the CPU, whether both processes exist, and the seconds that the second process waited. |
| 538 | `                          second_not_at_once=bool(p2 and p2['waited_s'] > 0),` | `second_not_at_once`: true when the second process waited more than 0 s. The handoff note asks to report such a pair: the second process did not follow the first at once. |
| 539 | `                          last_level_first=p1['last_level'] if p1 else None, first_level_second=p2['first_level'] if p2 else None))` | Continues the entry: the label of the last interval of the first process, and the label of the first interval of the second. |
| 540 | `    return dict(processes=procs, pairs=pairs)` | Returns the processes and the pairs. |

### Function `step_a6`: with and without huge pages (lines 543 to 567)

| Line | Source | Explanation |
|---:|---|---|
| 543 | `def step_a6(blocks):` | Starts the function `step_a6`. It summarises step A6: `asmread` with one thread at 8 MiB, with huge pages allowed and with `--no-thp`. |
| 544 | `    procs = []` | `procs`: one entry per process. |
| 545 | `    for b in blocks:` | Loop over the blocks of the step. |
| 546 | `        m = re.match(r'(thp\|nothp)-(\d+)$', b['tag'])` | Tests the tag. The pattern matches `thp` or `nothp`, a hyphen and a number. Group 1 holds the kind and group 2 the pair number. |
| 547 | `        if not m: continue` | A block with another tag is skipped. |
| 548 | `        rates = [r['total_GBps'] for r in b['reps']]` | `rates`: the totals of the repetitions, in time order. With one thread they are the rates of the thread. |
| 549 | `        want = 'nohugepage' if m.group(1) == 'nothp' else 'madvise'` | `want`: the page setting that the benchmark must print for this kind: `nohugepage` for a process with `--no-thp`, and `madvise` for the other kind. |
| 550 | `        cpu = b['cpus'] if b['cpus'] and b['cpus'].isdigit() else None` | `cpu`: the value of the option `--cpus` when it is one CPU number. If not, it is `None`. |
| 551 | `        procs.append(dict(tag=b['tag'], kind=m.group(1), index=int(m.group(2)), cpu=int(cpu) if cpu else None, rates_GBps=rates, levels=[level(x) for x in rates],` | The entry of the process: the tag, the kind, the pair number, the CPU, the rates and the level label of each rate. |
| 552 | `                          median_GBps=st.median(rates) if rates else None, thp_line=b['thp'], thp_line_ok=b['thp'] == want,` | Continues the entry: `median_GBps`, the median of the rates of the process. `thp_line`: the page setting that the benchmark printed. `thp_line_ok`: whether it is the setting that the launch asked for. |
| 553 | `                          waited_s=b['waited_s']))` | Continues the entry: the seconds that the run script waited before the launch. |
| 554 | `    out = dict(processes=procs)` | `out`: the result. It starts with the list of the processes. |
| 555 | `    for kind in ('thp', 'nothp'):` | Loop over the two kinds. |
| 556 | `        pp = [p for p in procs if p['kind'] == kind and p['median_GBps'] is not None]` | `pp`: the processes of this kind that have a median. |
| 557 | `        lv = [l for p in pp for l in p['levels']]` | `lv`: the level labels of all intervals of these processes. |
| 558 | `        out[kind] = dict(process_medians=rng([p['median_GBps'] for p in pp]), all_intervals=rng([x for p in pp for x in p['rates_GBps']]),` | The entry of the kind: `process_medians`, the range of the medians of its processes, and `all_intervals`, the range of all its interval rates. |
| 559 | `                         n_low=lv.count('low'), n_changing=lv.count('changing'), n_high=lv.count('high'))` | Continues the entry: the numbers of low, changing and high intervals. |
| 560 | `    a, b2 = out['thp']['process_medians'], out['nothp']['process_medians']` | `a`: the range of the process medians with huge pages allowed. `b2`: the range with `--no-thp`. |
| 561 | `    if a['n'] and b2['n']:` | Compares only when both kinds have processes. |
| 562 | `        out['nothp_minus_thp_GBps'] = b2['median'] - a['median']` | `nothp_minus_thp_GBps`: the median of the process medians with `--no-thp` minus the median of the process medians with huge pages allowed, in GB/s. |
| 563 | `        out['nothp_minus_thp_pct'] = 100 * (b2['median'] / a['median'] - 1)` | `nothp_minus_thp_pct`: the same difference in percent of the value with huge pages allowed. |
| 564 | `        out['process_ranges_overlap'] = not (a['min'] > b2['max'] or a['max'] < b2['min'])` | `process_ranges_overlap`: false only when all process medians of one kind lie above all process medians of the other. |
| 565 | `    return out` | Returns the result. |

### Functions `own_user_of` and `load_check`: signs of load from other users (lines 568 to 610)

| Line | Source | Explanation |
|---:|---|---|
| 568 | `def own_user_of(launches, envs):` | Starts the function `own_user_of`. It finds the account that ran the run script. |
| 569 | `    """The account of the run script: the user of the ps process that the script itself starts to write the list of busiest processes."""` | Text of the function: the run script itself starts `ps` to write the list of the busiest processes. So the user of a `ps` process in that list is the account of the run script. |
| 570 | `    users = [p['user'] for l in launches for p in l['busiest'] if p['comm'] == 'ps']` | `users`: the users of all processes with the command name `ps` in the lists of `launches.txt`. |
| 571 | `    for x in envs:` | Loop over the `env.txt` entries of the folders. |
| 572 | `        for l in x.get('busiest_at_start', []):` | Loop over the lines of the list of busiest processes at the start of the run script (line 275). |
| 573 | `            p = l.split(None, 2)` | `p`: the line split into CPU use, user and command name. |
| 574 | `            if len(p) == 3 and p[2].strip() == 'ps': users.append(p[1])` | Adds the user when the command name is `ps`. |
| 575 | `    return users[0] if users and len(set(users)) == 1 else None` | Returns the user when at least one was found and all are the same. If not, the result is `None`. |
| 578 | `def load_check(blocks, launches, envs):` | Starts the function `load_check`. It collects the readings that can show load from other users: the runnable tasks, the logins, the waits and the busiest processes. |
| 579 | `    """Readings that can show load from other users: runnable tasks (two readings per launch), logins, waits, busiest processes."""` | Text of the function: the runnable tasks have two readings per launch, one in `launches.txt` and one in the header line. |
| 580 | `    own = own_user_of(launches, envs)` | `own`: the account of the run script, or `None`. |
| 581 | `    lt = {(l['folder'], l['step'], l['tag']): l for l in launches}` | `lt`: the launch entries of `launches.txt`, each under its folder, step and tag. |
| 582 | `    for b in blocks:` | Loop over the blocks. |
| 583 | `        l = lt.get((b['folder'], b['step'], b['tag']))` | `l`: the entry of `launches.txt` for this block, or `None`. |
| 584 | `        b['runnable_launches_txt'] = l['runnable'] if l else None` | `runnable_launches_txt`: the runnable tasks of that entry. The run script takes this reading a moment before it writes the header line. |
| 585 | `    both = [b for b in blocks if b['runnable_launches_txt'] is not None]` | `both`: the blocks that have this second reading. |
| 586 | `    top = {}` | `top`: the highest CPU use per pair of user and command name. |
| 587 | `    for l in launches:` | Loop over all launch entries. |
| 588 | `        for p in l['busiest']:` | Loop over the processes of the list of the launch. |
| 589 | `            key = (p['user'], p['comm'])` | `key`: the pair of user and command name. |
| 590 | `            top[key] = max(top.get(key, 0), p['pcpu'])` | Keeps the highest CPU use that this pair showed at any launch, in percent of one CPU. |
| 591 | `    other = sorted(((v, u, c) for (u, c), v in top.items() if own is None or u != own), reverse=True)` | `other`: the pairs of other accounts, highest CPU use first. When the own account is not known, all pairs count as other. |
| 592 | `    mine = sorted(((v, u, c) for (u, c), v in top.items() if own is not None and u == own), reverse=True)` | `mine`: the pairs of the own account, highest CPU use first. |
| 593 | `    many = [b for b in blocks if (b['reps'][0]['threads'] if b['reps'] else 0) > 1]` | `many`: the blocks whose first repetition has more than one thread. |
| 594 | `    one = [b for b in blocks if (b['reps'][0]['threads'] if b['reps'] else 0) == 1]` | `one`: the blocks whose first repetition has one thread. |
| 595 | `    d = dict(own_user=own, n_launches=len(blocks), n_many_threads=len(many), n_one_thread=len(one),` | `d`: the result. It starts with the own account and the numbers of launches: all, with many threads, and with one thread. |
| 596 | `             runnable_header_max_many=max((b['runnable'] for b in many), default=None),` | `runnable_header_max_many`: the highest number of runnable tasks in a header line of a launch with many threads. |
| 597 | `             runnable_header_max_one=max((b['runnable'] for b in one), default=None),` | `runnable_header_max_one`: the same for the launches with one thread. |
| 598 | `             runnable_header_max=max((b['runnable'] for b in blocks), default=None),` | `runnable_header_max`: the same for all launches. |
| 599 | `             runnable_launches_txt_max=max((b['runnable_launches_txt'] for b in both), default=None),` | `runnable_launches_txt_max`: the highest number of runnable tasks in the readings of `launches.txt`. |
| 600 | `             n_with_launches_txt=len(both), n_runnable_differ=sum(1 for b in both if b['runnable'] != b['runnable_launches_txt']),` | `n_with_launches_txt`: the number of launches with both readings. `n_runnable_differ`: the number of launches at which the two readings differ. |
| 601 | `             logins_max=max((b['logins'] for b in blocks), default=None), n_waited=sum(1 for b in blocks if b['waited_s'] > 0),` | `logins_max`: the highest number of logins at a launch. `n_waited`: the number of launches that waited more than 0 s for a quiet system. |
| 602 | `             load1_max=max((b['load1'] for b in blocks), default=None), threads_max=max((r['threads'] for b in blocks for r in b['reps']), default=None),` | `load1_max`: the highest load average over 1 minute in a header line. `threads_max`: the highest thread count of a repetition. |
| 603 | `             busiest_other=[dict(pcpu=v, user=u, comm=c) for v, u, c in other[:3]], busiest_own=[dict(pcpu=v, user=u, comm=c) for v, u, c in mine[:4]])` | `busiest_other`: the 3 busiest pairs of other accounts. `busiest_own`: the 4 busiest pairs of the own account. |
| 604 | `    rmax = max([x for x in (d['runnable_header_max'], d['runnable_launches_txt_max']) if x is not None], default=None)` | `rmax`: the highest number of runnable tasks of both kinds of reading. |
| 605 | `    d['runnable_max'] = rmax` | Stores it as `runnable_max`. |
| 606 | `    d['no_other_load_seen'] = bool(blocks) and own is not None and rmax is not None and rmax <= 2 and d['logins_max'] == 0 and d['n_waited'] == 0 \` | `no_other_load_seen`: true only when all of these hold. There are blocks. The own account is known. No reading shows more than 2 runnable tasks. No user was logged in at any launch. No launch waited. The last condition follows in line 607. |
| 607 | `        and (not other or other[0][0] < 1.0)` | Continues the condition: no process of another account reached 1.0 % of one CPU in any list. |
| 608 | `    return d` | Returns the result. |

### Function `load_summary`: the load readings per step (lines 611 to 631)

| Line | Source | Explanation |
|---:|---|---|
| 611 | `def load_summary(blocks, launches):` | Starts the function `load_summary`. It gives the load readings for each step. |
| 612 | `    """System load per step from the header lines; busiest processes from launches.txt."""` | Text of the function: the load comes from the header lines, and the busiest processes come from `launches.txt`. |
| 613 | `    out = {}` | `out`: one entry per step. |
| 614 | `    for s in STEPS[:6]:` | Loop over the six steps that have a csv file, A1 to A6. |
| 615 | `        bb = [b for b in blocks if b['step'] == s]` | `bb`: the blocks of this step. |
| 616 | `        if not bb: continue` | A step without blocks gets no entry. |
| 617 | `        ll = [l for l in launches if l['step'] == s]` | `ll`: the entries of `launches.txt` for this step. |
| 618 | `        top = {}` | `top`: the highest CPU use per pair of user and command name, for this step. |
| 619 | `        for l in ll:` | Loop over these launch entries. |
| 620 | `            for p in l['busiest']:` | Loop over the processes of each list. |
| 621 | `                key = (p['user'], p['comm'])` | `key`: the pair of user and command name. |
| 622 | `                top[key] = max(top.get(key, 0), p['pcpu'])` | Keeps the highest CPU use of the pair. |
| 623 | `        out[s] = dict(launches=len(bb), load1=rng([b['load1'] for b in bb]), runnable=rng([b['runnable'] for b in bb]),` | The entry of the step starts with the number of launches, the range of the load average over 1 minute and the range of the runnable tasks, all from the header lines. |
| 624 | `                      runnable_launches_txt=rng([b['runnable_launches_txt'] for b in bb if b.get('runnable_launches_txt') is not None]),` | Continues the entry: the range of the runnable tasks in the readings of `launches.txt`. |
| 625 | `                      waited_s=rng([b['waited_s'] for b in bb]), n_waited=sum(b['waited_s'] > 0 for b in bb),` | Continues the entry: the range of the waited seconds, and the number of launches that waited more than 0 s. |
| 626 | `                      n_waited_20s=sum(b['waited_s'] >= 20 for b in bb), logins=rng([b['logins'] for b in bb]),` | Continues the entry: the number of launches that waited the full 20 s, and the range of the logins. |
| 627 | `                      first_utc=bb[0]['utc'], last_utc=bb[-1]['utc'], launches_txt_entries=len(ll),` | Continues the entry: the UTC times of the first and of the last launch of the step, and the number of entries of `launches.txt`. |
| 628 | `                      busiest=[dict(user=u, comm=c, max_pcpu=v) for (u, c), v in sorted(top.items(), key=lambda x: -x[1])[:5]])` | Continues the entry: the 5 busiest pairs of user and command name, with their highest CPU use. |
| 629 | `    return out` | Returns the result. |

### Function `analyse`: read the folders, choose the blocks, test q, set the labels (lines 632 to 669)

| Line | Source | Explanation |
|---:|---|---|
| 632 | `def analyse(folders):` | Starts the function `analyse`. It reads the result folders and builds the summary that becomes the json file. |
| 633 | `    folders = sorted(folders, key=lambda f: os.path.basename(os.path.normpath(f)))` | Sorts the folders by the last part of their path. The names of result folders end with the start time in UTC, so this is time order. |
| 634 | `    all_blocks, launches, envs = [], [], []` | `all_blocks`: every block of every csv file. `launches`: every entry of the files `launches.txt`. `envs`: one `env.txt` entry per folder. |
| 635 | `    for f in folders:` | Loop over the folders. |
| 636 | `        name = os.path.basename(os.path.normpath(f))` | `name`: the last part of the folder path. |
| 637 | `        envs.append(parse_env(f))` | Reads `env.txt`, the files of step A7 and `stderr.txt` of the folder (line 261). |
| 638 | `        launches += parse_launches(os.path.join(f, 'launches.txt'), name)` | Reads `launches.txt` of the folder (line 225) and adds its entries. |
| 639 | `        for s in STEPS[:6]:` | Loop over the six steps that have a csv file, A1 to A6. |
| 640 | `            p = os.path.join(f, s + '.csv')` | `p`: the path of the csv file of the step, for example `A1.csv`. |
| 641 | `            if os.path.exists(p):` | Reads the file only when it exists. |
| 642 | `                all_blocks += [finish_block(b) for b in parse_csv(p, name)]` | Splits the file into blocks (line 115), finishes each block (line 199) and adds the blocks to `all_blocks`. |
| 643 | `    # choice C4: the last complete block of each (step, tag) is used` | Comment: choice C4. Of each pair of step and tag, the last complete block is used. |
| 644 | `    used, not_used, seen = [], [], {}` | `used`: the blocks that the analysis uses. `not_used`: the list of the others. `seen`: the blocks per pair of step and tag. |
| 645 | `    for b in all_blocks:` | Loop over all blocks. |
| 646 | `        seen.setdefault((b['step'], b['tag']), []).append(b)` | Adds the block to the list of its step and tag. The lists keep the reading order: folders in time order, and file order inside a folder. |
| 647 | `    for (step, tag), bb in seen.items():` | Loop over the pairs of step and tag. |
| 648 | `        good = [b for b in bb if b['complete']]` | `good`: the complete blocks of this pair. |
| 649 | `        for b in bb:` | Loop over the blocks of the pair. |
| 650 | `            if good and b is good[-1]:` | Tests whether this block is the last complete one. |
| 651 | `                used.append(b)` | That block is used. |
| 652 | `            else:` | Every other block of the pair is not used. |
| 653 | `                why = '; '.join(b['problems']) if b['problems'] else 'a later complete block of the same step and tag exists'` | `why`: the reason. It is the list of the problems of the block, joined with a semicolon. A complete block that is not the last one gets the text `a later complete block of the same step and tag exists`. |
| 654 | `                not_used.append(dict(folder=b['folder'], step=step, tag=tag, utc=b['utc'], reason=why, killed=b['killed'], failed=b['failed'],` | Adds an entry to `not_used`: the folder, the step, the tag, the UTC time, the reason and the texts of the `killed` and `failed` lines. |
| 655 | `                                     replaced=bool(good), n_blocks_of_tag=len(bb)))` | Continues the entry: `replaced` says whether a complete block of the same launch is used. `n_blocks_of_tag` is the number of blocks of the pair. |
| 656 | `    used.sort(key=lambda b: all_blocks.index(b))` | Puts the used blocks back into the order in which they were read. |
| 657 | `    # q over all repetitions with at least 2 threads, and the decision whether the labels are used.` | Comment: q is collected over all repetitions with at least 2 threads. Then the script decides whether the labels are used. |
| 658 | `    # Choice C8: of A3 only the rows of the read kernel count (handoff: "Compare only the rows of the read kernel").` | Comment: choice C8. Of step A3 only the rows of the read kernel count, by the sentence of the handoff note that the comment quotes. |
| 659 | `    qall = [dict(step=b['step'], tag=b['tag'], kernel=r['kernel'], rep=r['rep'], threads=r['threads'], q=r['q'], label_rule=r['label_rule'],` | `qall`: one row for every repetition of the used blocks that has a q. This line gives the row its step, tag, kernel, repetition number, thread count, q and the label of the rule. |
| 660 | `                 kname=kname_of(b, r), count=f"{r['mesh0']['n']}+{r['mesh1']['n']}", mesh0_median=r['mesh0']['median'], mesh1_median=r['mesh1']['median'])` | Continues the row: the kernel name in the form of the A1 tags (line 342). `count`: the number of thread lines on mesh 0, a `+`, and the number on mesh 1, for example `64+56`. It is counted from the CPUs of the thread lines, not taken from the tag. Then the median thread rate of each mesh. |
| 661 | `            for b in used for r in b['reps'] if r['q'] is not None]` | Continues line 659: the loops over the used blocks and their repetitions, and the test that q exists. A repetition of one thread has no q. |
| 662 | `    qrows = [x for x in qall if not (x['step'] == 'A3' and x['kernel'] != 'read')]` | `qrows`: the rows that take part in the test of the two groups: all rows other than the write and copy rows of step A3. |
| 663 | `    qleft = [x for x in qall if x['step'] == 'A3' and x['kernel'] != 'read']` | `qleft`: the rows that are left out: the rows of step A3 whose kernel is not `read`. |
| 664 | `    qd = two_groups([x['q'] for x in qrows])` | `qd`: the decision of the test of the two groups over the q values of `qrows` (line 290). One decision holds for all steps and kernels of Part A. |
| 665 | `    if qd['labels_usable']:` | Only when the decision allows the labels. |
| 666 | `        for b in used:` | Loop over the used blocks. |
| 667 | `            for r in b['reps']:` | Loop over the repetitions of each block. |
| 668 | `                r['label'] = r['label_rule']` | Copies the label of the rule into `label`. When the labels are not allowed, every `label` stays `None`, and the result page gives q without a label. |
| 669 | `    by = {s: [b for b in used if b['step'] == s] for s in STEPS[:6]}` | `by`: the used blocks per step, for the steps A1 to A6. |

### Function `analyse`: the summary (lines 670 to 701)

| Line | Source | Explanation |
|---:|---|---|
| 670 | `    low_reps = [dict(step=b['step'], tag=b['tag'], kernel=r['kernel'], kname=kname_of(b, r), rep=r['rep'], passes_per_thread=r['passes_per_thread'], min_ms=b['min_ms'])` | `low_reps`: one entry for every repetition that fails the 2 % check: its step, tag, kernel, kernel name, repetition number, passes per thread and interval length. The condition follows in line 671. |
| 671 | `                for b in used for r in b['reps'] if r['below_50_passes'] and r['threads'] >= 2]` | Continues line 670: the repetition has fewer than 50 passes per thread, and its data line names at least 2 threads. The one-thread steps A5 and A6 are left out. |
| 672 | `    a1, a2 = step_a12(by['A1']), step_a12(by['A2'])` | `a1` and `a2`: the summaries of step A1 and of step A2 (line 367). They are built after line 668, so their short forms hold the labels. |
| 673 | `    steps_present = [s for s in STEPS[:6] if by[s]] + (['A7'] if any(e['a7'] for e in envs) else [])` | `steps_present`: the steps of A1 to A6 that have a used block, plus `A7` when a folder holds a file of step A7. |
| 674 | `    lc_ = load_check(used, launches, envs)` | `lc_`: the readings for load from other users (line 578). The call also stores the second reading of the runnable tasks in each used block. |
| 675 | `    a5_, a6_ = step_a5(by['A5']), step_a6(by['A6'])` | `a5_` and `a6_`: the summaries of step A5 and of step A6. |
| 676 | `    lvl = level_check(a5_, a6_)` | `lvl`: the check of the level limits (line 500). The call also stores in each A5 process whether its labels are usable, and it empties the level changes where they are not. |
| 677 | `    summary = dict(` | Starts the summary, one dictionary with all results. |
| 678 | `        generated_by='analyze_partA.py', folders=[os.path.basename(os.path.normpath(f)) for f in folders],` | `generated_by`: the name of this script. `folders`: the names of the result folders, in time order. |
| 679 | `        limits=dict(q_split_below=Q_SPLIT, q_uniform_above=Q_UNIFORM, low_below_GBps=LOW_BELOW, high_above_GBps=HIGH_ABOVE, min_passes=MIN_PASSES,` | `limits`: the limits that the script used: 0.65 and 0.85 for q, 69.0 and 70.5 GB/s for the level, and 50 passes. |
| 680 | `                    q_gap_min=GAP_MIN, level_gap_min_GBps=LEVEL_GAP_MIN),` | Continues the limits: the smallest distance of 0.10 for q and the smallest empty range of 0.25 GB/s for a level limit. |
| 681 | `        choices=CHOICES, env=envs, steps_present=steps_present, steps_missing=[s for s in STEPS if s not in steps_present],` | `choices`: the texts of lines 64 to 86. `env`: the `env.txt` entries. `steps_present`, and `steps_missing`: the steps of A1 to A7 that are not present. |
| 682 | `        counts=dict(blocks_found=len(all_blocks), blocks_used=len(used), blocks_not_used=len(not_used),` | `counts`: the numbers of blocks: found, used and not used. |
| 683 | `                    killed=sum(1 for b in all_blocks if b['killed']), failed=sum(1 for b in all_blocks if b['failed']),` | Continues the counts: the blocks with a `killed` line and the blocks with a `failed` line, among all blocks found. |
| 684 | `                    repeated_tags=sum(1 for v in seen.values() if len(v) > 1), repetitions_used=sum(len(b['reps']) for b in used)),` | Continues the counts: `repeated_tags`, the pairs of step and tag with more than one block, and `repetitions_used`, the repetitions of all used blocks. |
| 685 | `        not_used=not_used, load=load_summary(used, launches), load_check=lc_, level_check=lvl,` | `not_used`: the list of line 654. `load`: the load readings per step (line 611). `load_check` and `level_check`: the results of line 674 and line 676. |
| 686 | `        launches=[dict(folder=b['folder'], step=b['step'], tag=b['tag'], utc=b['utc'], waited_s=b['waited_s'], load1=b['load1'], load5=b['load5'],` | `launches`: one entry per used block with its load readings: the folder, the step, the tag, the UTC time, the waited seconds and the load averages over 1 and 5 minutes. |
| 687 | `                       load15=b['load15'], runnable=b['runnable'], runnable_launches_txt=b['runnable_launches_txt'], logins=b['logins'],` | Continues the entry: the load average over 15 minutes, the two readings of the runnable tasks and the number of logins. |
| 688 | `                       threads=b['reps'][0]['threads'] if b['reps'] else None) for b in used],` | Continues the entry: the thread count of the first repetition of the block, or `None` for a block without repetitions. The loop over the used blocks ends the list. |
| 689 | `        q=dict(decision=qd, rows=qrows, rows_left_out=qleft, groups=q_groups(qrows)), passes=dict(n_below_50=len(low_reps), below_50=low_reps),` | `q`: the decision, the rows of the test, the rows that were left out, and the description of line 350. `passes`: the number and the list of the repetitions below 50 passes. |
| 690 | `        A1=a1, A2=a2, A1_A2=compare_a1_a2(a1, a2), A3=step_a3(by['A3']), A4=step_a4(by['A4']), A5=a5_, A6=a6_,` | The summaries of the steps: A1, A2, the comparison of A1 with A2 (line 386), A3 (line 410), A4 (line 438), A5 and A6. |
| 691 | `        level_counts_8MiB=None,` | `level_counts_8MiB`: an empty place. Line 698 fills it. |
| 692 | `        thread_rates={s: [dict(tag=b['tag'], kernel=r['kernel'], rep=r['rep'], threads=r['threads_cpu_rate']) for b in by[s] for r in b['reps']]` | `thread_rates`: for the steps A1 and A2, one entry per repetition with the tag, the kernel, the repetition number and the pairs of CPU and thread rate. The result page draws the rate of each thread against its CPU from this list. |
| 693 | `                      for s in ('A1', 'A2')},` | Continues line 692: the loop over the two steps. |
| 694 | `        blocks=[{k: v for k, v in b.items() if k != 'reps'} \| dict(n_reps=len(b['reps'])) for b in used],` | `blocks`: every used block without its repetitions, plus the number of its repetitions. The `\|` joins the two dictionaries. |
| 695 | `    )` | Ends the summary. |
| 696 | `    lv = [l for p in summary['A5']['processes'] for l in p['levels']] + [l for p in summary['A6']['processes'] for l in p['levels']]` | `lv`: the level labels of all intervals of step A5 and of step A6. |
| 697 | `    rates = [x for p in summary['A5']['processes'] + summary['A6']['processes'] for x in p['rates_GBps']]` | `rates`: the rates of all intervals of the two steps, in GB/s. |
| 698 | `    summary['level_counts_8MiB'] = dict(n=len(lv), low=lv.count('low'), changing=lv.count('changing'), high=lv.count('high'), rate=rng(rates))` | `level_counts_8MiB`: the number of these intervals, how many are low, changing and high by the two provisional limits alone, and the range of the rates. The A6 processes with `--no-thp` are counted too. |
| 699 | `    return summary` | Returns the summary. |

### Function `main`: arguments, the json file, the printed summary (lines 702 to 727)

| Line | Source | Explanation |
|---:|---|---|
| 702 | `def main(argv):` | Starts the function `main`. `argv` is the list of the arguments of the call. |
| 703 | `    out = 'partA-summary.json'` | `out`: the path of the output file. It is `partA-summary.json` in the working folder unless `--out` gives another path. |
| 704 | `    if '--out' in argv:` | Tests whether the arguments hold `--out`. |
| 705 | `        i = argv.index('--out'); out = argv[i + 1]; argv = argv[:i] + argv[i + 2:]` | Takes the word after `--out` as the output path and removes the two words from the list. What is left are the result folders. |
| 706 | `    if not argv:` | Tests whether no folder was given. |
| 707 | `        print(__doc__); return 2` | Prints the header text of the file (lines 2 to 50) as the usage and returns 2. This becomes the exit status (line 727). |
| 708 | `    for f in argv:` | Loop over the folders. |
| 709 | `        if not os.path.isdir(f):` | Tests whether the path is not a folder. |
| 710 | `            print(f'not a folder: {f}', file=sys.stderr); return 2` | Prints `not a folder:` with the path to the error output and returns 2. |
| 711 | `    s = analyse(argv)` | `s`: the summary of all folders (line 632). |
| 712 | `    with open(out, 'w') as f:` | Opens the output file for writing. An older file of that name is replaced. |
| 713 | `        json.dump(s, f, indent=1)` | Writes the summary as json text, indented by 1 space per level. |
| 714 | `    c = s['counts']; d = s['q']['decision']` | `c`: the counts of the blocks. `d`: the decision of the test of the two groups. |
| 715 | `    print(f"folders: {', '.join(s['folders'])}")` | Prints the names of the folders, joined with commas. |
| 716 | `    print(f"blocks found {c['blocks_found']}, used {c['blocks_used']}, not used {c['blocks_not_used']} (killed {c['killed']}, failed {c['failed']}, repeated tags {c['repeated_tags']})")` | Prints the numbers of blocks: found, used and not used, and in brackets the blocks with a `killed` line, with a `failed` line, and the tags that occur more than once. |
| 717 | `    print(f"steps present: {' '.join(s['steps_present'])}; missing: {' '.join(s['steps_missing']) or 'none'}")` | Prints the steps that are present and the steps that are missing. With no missing step it prints the word `none`. |
| 718 | `    print(f"q: n {d['n']}, two groups {d['two_groups']}, labels usable {d['labels_usable']}" + (f" ({d['reason']})" if d['reason'] else ''))` | Prints the result of the test of q: the number of q values, whether they fall into two groups, whether the labels are usable, and the reason in brackets when there is one. |
| 719 | `    print(f"repetitions with fewer than {MIN_PASSES} passes per thread (2 or more threads): {s['passes']['n_below_50']}")` | Prints the number of repetitions with fewer than 50 passes per thread, counted over the repetitions with 2 or more threads. |
| 720 | `    for x in s['not_used']:` | Loop over the blocks that are not used. |
| 721 | `        print(f"not used: {x['folder']} {x['step']} {x['tag']}: {x['reason']}")` | Prints one line per such block: the folder, the step, the tag and the reason. |
| 722 | `    print(f'wrote {out}')` | Prints `wrote` and the path of the output file. |
| 723 | `    return 0` | Returns 0, the exit status of a run that worked. |
| 726 | `if __name__ == '__main__':` | This test is true when the file is started as a program. It is false when another file imports it. The tests in `test_partA.py` import it. |
| 727 | `    sys.exit(main(sys.argv[1:]))` | Calls `main` with the arguments of the command line, without the program name. The return value becomes the exit status: 0 after a run that worked, 2 for a missing argument or a path that is not a folder. |

## References

- [Ref1] the result folder `partA-20261113T205055Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`: the files `analyze_partA.py` (sha256 `d82f50aeb3b9488d2a919d05205c81fcb7abca00a099119b2e1ac27fd2fcb5e0`, as the file in the code folder) and `partA-summary.json` (key `q.decision`: `n` 152, `two_groups` false, `labels_usable` false).
