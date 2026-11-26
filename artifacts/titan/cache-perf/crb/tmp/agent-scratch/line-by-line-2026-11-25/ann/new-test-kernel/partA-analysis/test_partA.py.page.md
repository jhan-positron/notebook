## Short version: purpose

`test_partA.py` tests the analysis script `analyze_partA.py` and the page generator `make_partA_html.py` without any measurement. It builds invented result folders in the format of the run script, runs both scripts on them, and checks the computed values and the text of the pages. The tests fix the choices of the analysis: which blocks are used, when the labels are used, and that missing data is reported as missing.

## Words used here

- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan and how to analyse Part A.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. By the plan it closes no hypothesis. This is not the part A of the later rerun.
- **Step**: one named batch of Part A, `A1` to `A7`. B7 and B8 are steps of the later Part B, and Part C is the part with counters.
- **Run script**: the script `run_partA.sh`. It starts the processes of Part A on the test machine and writes the result folders.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Data set 1, data set 2**: the two sets of invented result folders of this file. Set 1 has clear patterns. Set 2 has patterns between the limits.
- **Summary, json file**: the result of the analysis script, one dictionary. It is stored as the file `partA-summary.json`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Kernel names of the tags**: `read_old` and `write_old` are the C kernels of the binary `bw_old`. `read_new` and `write_new` are the C kernels of the binary `bw_new`. `asmread` and `asmwrite` are the hand-written kernels, taken from `bw_new`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`.
- **Launch, tag**: a launch is one start of a process by the run script. The tag is the short name of the launch, for example `read_old-r1`.
- **Block**: the lines of one process in a csv file: the header line of the run script and the output of the benchmark.
- **Header line**: the line that the run script writes before the output of a process. It starts with `-- step`.
- **Data line**: an output line of the benchmark for one repetition, with 10 fields.
- **Thread line**: an output line of the benchmark for one thread and one repetition, printed with `--per-thread`.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate of a repetition as the benchmark prints it: the bytes of all threads divided by the longest elapsed time of a thread.
- **Thread rate**: the bytes of one thread divided by its own elapsed time. The benchmark prints it with 2 decimals.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Thread count `a+b`**: a threads on mesh 0 and b threads on mesh 1, for example `64+56`.
- **Pass**: one sweep of a thread over its whole buffer.
- **2 % check**: rule 7 of the plan: one pass may take at most 2 % of the interval. That means at least 50 passes per thread.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one repetition. It has no unit.
- **Pattern labels: split, uniform, between**: the provisional labels of a repetition: q below 0.65, q above 0.85, or neither.
- **Fastest half**: the half of the threads of one repetition that has the highest rates.
- **Bracket**: the two neighbouring thread counts of step A4 between which the pattern label changes.
- **Level labels: low, high, changing**: the provisional labels of an interval with one thread at 8 MiB: a rate below 69 GB/s, above 70.5 GB/s, or neither.
- **Choice C1 to C11**: a definition that the analysis script had to fix where the plan and the handoff note give none.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **PMU**: performance monitoring unit, the counter hardware of a core. Linux shows it as a counter device with a type number.
- **SVE**: the scalable vector instruction set of Arm.
- **`assert`**: the Python statement of a test. It stops the program with an error when its condition is false.

## Main flow

1. Helpers for invented data ({L27-144}): CPU lists, rate functions for a split and for a uniform distribution, the class `Folder` that writes one result folder with its blocks, and `long_steps` that writes the steps A1 to A4.
2. `build_set1` builds data set 1 in three folders: a split and a uniform kernel, a killed launch that a later folder repeats, a skipped step A3, a level change in one A5 process, and a second A5 process that waited ({L147-179}).
3. `build_set2` builds data set 2 in one folder: distributions between the limits, step A3 present, a failed A5 process, no A6 and no A7 ({L182-193}).
4. `check_set1` tests the json values of set 1: missing steps, the choice of the blocks, passes, mesh values, q, fastest half, percentile, labels, brackets of A4, level changes of A5, A6 and the load ({L200-275}).
5. `check_set2` tests the json values of set 2: labels not used, the rows of A3 that are left out, no bracket, the passes of copy rows, and the failed process ({L278-311}).
6. `check_two_groups` and `check_units` test single functions on small inputs: the test of the two groups, the number format, the check of the level limits and the reading of the event codes ({L314-348}).
7. `check_set1_more` and `check_set2_more` test json values together with the text of the page ({L351-389}).
8. `check_page` tests rules that every page must meet: no forbidden word, no outside file, a short version of at most 3 sentences, and `Insufficient data` for every missing step ({L392-403}).
9. `main` runs all of this in order: the single functions, then set 1, then set 2, then one empty folder ({L406-431}).

## Behavior a reader must know

- The file needs no test machine and no result folder. Every rate in its data is invented, and each test page carries a banner that says so.
- The file is started as a program. `main` calls the check functions one after the other. The first failed `assert` ends the program with an error. The line `all tests passed` is printed only when none failed.
- Without `--keep` the data is written to a new temporary folder, which is deleted at the end, also after a failed test ({L429-431}).
- With `--keep DIR` the folder `DIR` is first deleted with all its content and then created new ({L410}). The files of the test stay there.
- The summary is tested after it was written to a json file and read back ({L414-415}). So the tests see the values as the page generator sees them.
- The header text says that two pages stay with `--keep`. The code keeps three: the page of the empty folder is written too ({L427}).
- The comment of {L302} speaks of 60 and 120 passes for the copy rows. The generator and the tests use 40 passes, and 80 without the division by 2.
- The text of {L183} gives rough q values for set 2. The tests do not depend on these numbers.
- The two scripts are loaded from the folder of this file ({L18-21}). The test writes no compiled copy of them ({L16}).
