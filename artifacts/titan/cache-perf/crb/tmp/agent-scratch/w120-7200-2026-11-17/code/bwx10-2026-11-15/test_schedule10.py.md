# `test_schedule10.py` explained, line by line

- Source file: `bwx10-2026-11-15/test_schedule10.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1394 lines, 85983 bytes).
- sha256 of the source when this page was built: `2835f32efa051518efd3bb9c97846515ff9a042ff643c074f6240637070cd1ce`.

## Short version: purpose

`test_schedule10.py` checks the three scripts of round 3 without CRB: the generator `schedule10.py`, the run script `run_bwx10.sh` and the visit script `visit10.sh`. It tests the generated schedules against rules that are written a second time in this file, it puts every plan through a runner that is built on the local machine, and it runs the run script with dummy binaries through its stop cases. The validator and the rule functions of the steps are also applied to inputs that must not pass, to show that they can fail.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 3**: the third set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Y`.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation into the buffer size of 8 MiB.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048`**: the four prefetch kernels of the runner `bwx10`. Each is the `asmread` loop with one software prefetch per 64 B line, 256, 512, 1024 or 2048 bytes ahead.
- **`read_1pl`**: a kernel of the runner `bwx10` that makes one load of 16 bytes at the start of each 64 B line.
- **Process**: one start of a benchmark binary.
- **Check**: one call of the function `check`. It prints `PASS` or `FAIL` and one sentence that says what was tested.
- **Generator**: the program `schedule10.py`. It writes the schedules, the plan files and the `.bin` files of round 3.
- **Run script**: the script `run_bwx10.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Visit script**: the script `visit10.sh`. It makes one login to CRB and starts the run script there.
- **Step**: one batch of processes of a round, for example `YP`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **`.bin` file**: the file `<STEP>.bin` of a step. It holds one word, `bwx8` or `bwx10`, the name of the runner that the step uses.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Header pairs**: the pairs of the form `key=value` in the second line of a plan file, for example `kernel=asmread`.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Prefix, target, window**: the target is the kernel that a trial measures. A window is one timed period of it. The prefix is a phase before the target that gives every trial the same preparation.
- **`S2` form**: a process of 4 equal trials, each with a prefix of 1200 ms of the target kernel and 4 target windows of 300 ms. Step `S2` of round 1 had this form first.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Window plan**: one of the four ways in which step `YL` cuts 30 s of target time into windows: `L100`, `L300`, `L1000` and `L30000`.
- **Condition**: one setting that a step compares. In `YL` it is one kernel with one window plan. In `YP` it is one record pad or `hot`.
- **Cell**: one combination of the factors of a step, for example one kernel at one buffer size.
- **Replicate set, block**: a replicate set is one run of every kernel of step `YF` for one size and CPU. A block is the group of processes of one replicate on one CPU in the steps `YL` and `YP`, or the processes of one CPU in `YC`.
- **Williams square**: a set of n orders of n items in which every item stands once at every position, and every ordered pair of different items stands once as direct neighbours.
- **Test divisor**: a number by which the generator divides every duration, for local tests only. The test uses 100.
- **`--rec-pad P`**: an option of the runner `bwx10`. It puts P unused bytes before the records in which the runner stores the times of its windows.
- **`--hot-copy`**: an option of the runner `bwx10`. The window loop then works on a local copy of its window record.
- **`--trace`**: an option of the runner. The runner then prints a log of the events around its timed parts. The rates of such a run are not used.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters for each window.
- **`bins`**: a field of a trial, 0 or 1. With 1 the runner also stores the time and the byte count about every 10 ms inside a target window. One such entry is a bin record.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`--pmu-type`, `--events`**: the two counter options of the runner. `--pmu-type` gives the type number that Linux gives to the counter device of the cores, 11 on CRB by the notes of the project. `--events` gives the list of counter events, each as a name and a code. The variables `BWX_PMU_TYPE` and `BWX_EVENTS` carry the same two values in the environment.
- **Validator**: the function `parse_plan` of this file. It tests a plan file against the rules of the plan format.
- **Stand-in**: a program that takes the place of another one in the test. The stand-in runners are built from the runner sources on the local machine. Their kernels are plain C loops, and their rates mean nothing.
- **Dummy binary**: a small shell script that stands in for a runner. It records how it was started, sleeps, and ends with a chosen exit status.
- **Box**: the test setup of the run script: a copy of the script, the dummies and a schedule in a temporary folder.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop the run script.
- **`STOP_AT`**: a UTC time that the caller sets. The run script starts no process that could run past it.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s by default. `MARGIN` is the nominal work of the longest process of a step plus `RESERVE`.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Host sampler**: the program `hostwatch.py`. The run script starts it beside a process when the step has a `.watch` file.
- **Dry run**: a call of the run script with `--dry-run`. It prints what would run and starts nothing.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. The values that the task expects are written as fixed values: the counts, the nominal work, the binary, the kernels, the sizes, the options and the events of each step (lines 43 to 64).
2. The helper `check` prints one line per check and collects the failures (lines 70 to 76).
3. The validator of the plan format and the reader of a generated folder (lines 79 to 162, lines 165 to 208).
4. The rules of the steps, one function per step (lines 249 to 394).
5. Group 1, `schedule_checks`: run the generator. Test the format of every file, the counts and the printed report, the header pairs, the CPU order, the rules of each step with damaged variants, the `.bin` files, the effect of the seed, the saved folder and the test divisor (lines 397 to 624).
6. Group 2, `bwx8_checks`: a locally built `bwx8` accepts all 64 plans of `YL`, runs the 8 real window plans of one block for 30 s each, refuses damaged plans, and refuses the options of a `YP` process (lines 683 to 742).
7. Group 3, `bwx10_checks`: a locally built `bwx10` lists the new kernels and accepts all 725 plans of `YA`, `YP`, `YF` and `YC` (lines 745 to 782).
8. Group 4, `visit_checks`: the visit script with a stand-in for `ssh`: the remote command, bad settings, and the comparison with `visit9.sh` (lines 952 to 1003).
9. Group 5, `run_checks`: the run script with dummy binaries: syntax, comparison of the stop controls with `run_bwx9.sh`, step names and the dry run, a normal run, the binary of a step, the digests, the counter settings, the host sampler, the stop controls, `MARGIN`, session 2 and other refusals (lines 1006 to 1365).
10. `main` runs the groups in this order, removes the temporary folder and prints the summary (lines 1368 to 1390).

## Behavior a reader must know

- The test contacts no other machine. The visit script runs with a stand-in for `ssh` and a search path that holds no real `ssh` (line 969). The run script runs as a copy in a temporary folder, with test paths for the marker file, the stop file, the binaries and the results (lines 901 to 902).
- The test starts local programs: the generator, `gcc`, the stand-in runners (6 at a time, and once 8 at a time for 30 s), the copy of the run script, the dummies and the host sampler.
- The exit status is 0 only when every check passed (line 1390). A part that did not run prints a `SKIP` line and does not change the status. The summary line does not count the `SKIP` lines.
- Four options leave out parts: `--no-run`, `--no-bwx8`, `--no-long` and `--no-bwx10`. The part with the stand-in `bwx10` is also left out when `bwx10.c` is missing or cannot be built (lines 750 to 760). A failed build of the stand-in `bwx8` is a failed check (line 688).
- The expected values are written a second time in this file (lines 44 to 63). So a change in the generator alone makes a check fail.
- The validator, the rule for the CPU order and the rule functions of the steps are tested twice: once on the real output, and once on an input that must not pass. Not every rule inside a rule function has such a second test.
- The check that starts at line 612 is named for every duration divided by 100. The test compares the nominal work per step and session and the window counts, not each duration.
- The checks of the run script take minutes on a loaded machine. Before each launch the script waits up to 20 s until at most 2 tasks are runnable.
- The stop cases run once for a step of each binary, `YL` with the dummy `bwx8` and `YA` with the dummy `bwx10` (line 1229): the marker file and the stop file during a process and at the start, a signal, `STOP_AT` before and during a process, and a failing process. Each case tests the exit status. The four cases that stop a running process also test the `-- killed` line and that no process is left. The three cases with a stop reason before the first launch test that nothing starts. The case of a failing process tests the `-- failed` line and that the next process does not start.
- The check of the saved folder compares every file of `sched10/` beside this file with the output of the generator (lines 598 to 600). The repo README lists the folders `sched*` among those that were left out of the repo. So in the repo folder this check fails, and the copy in line 1292 raises an error that ends the test without its summary.
- The check of a wrong `.bin` content tests "nothing starts" with the log of the dry run only (lines 1124 to 1128). For the real run it tests the exit status and the message.
- The stand-in runs need CPU 0, CPU 2 and one more CPU below 120 on the local machine (line 678). CPU 41 is replaced by a local CPU in a copy of the schedule (lines 643 to 646).
- The test reads four files of the folder `bwx8-2026-11-14`, which must lie beside the folder of round 3 (line 33): `bwx8.c`, `run_bwx9.sh`, `visit9.sh` and `hostwatch.py`.
- The test writes into a temporary folder only and removes it at the end (line 1371, line 1385).

## Source and explanation, line by line

- Text shown: the file `bwx10-2026-11-15/test_schedule10.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1394 lines, 85983 bytes, sha256 `2835f32efa051518efd3bb9c97846515ff9a042ff643c074f6240637070cd1ce`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 82. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Description text and imports (lines 1 to 30)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_schedule10.py - checks of schedule10.py, run_bwx10.sh and visit10.sh (round 3).` | Starts the description text of the file. First line: the name and the purpose. The file holds the checks of the generator `schedule10.py`, of the run script `run_bwx10.sh` and of the visit script `visit10.sh`. These are the three scripts of round 3. |
| 4 | `Usage: test_schedule10.py [--no-run] [--no-bwx8] [--no-long] [--no-bwx10]` | Text of the description: the usage. Each of the four options leaves out one group of checks. |
| 5 | `Prints one line per check. Exit status 0 only if every check passed.` | Text of the description: the program prints one line per check. Its exit status is 0 only when every check passed. |
| 6 | `--no-run leaves out the checks that start run_bwx10.sh with dummy binaries (they take minutes` | Text of the description: `--no-run` leaves out the checks that start `run_bwx10.sh` with dummy binaries. A dummy binary is a small script that stands in for a runner. |
| 7 | `on a loaded machine, because the script waits up to 20 s for a quiet system before a launch).` | Continues the text: those checks take minutes on a loaded machine. The reason: the run script waits up to 20 s for a quiet system before each launch. |
| 8 | `--no-bwx8 leaves out the build of the local stand-in bwx8 (from folder X of round 1) and the run of` | Text of the description: `--no-bwx8` leaves out the build of a local stand-in of the runner `bwx8` from the folder `X` of round 1. A stand-in is a build on the machine of the developer. Its kernels are plain C loops, and its rates mean nothing. |
| 9 | `every plan of the bwx8 step YL through it.` | Continues the text: the option also leaves out the run of every plan of step `YL`, the step that uses `bwx8`, through that stand-in. |
| 10 | `--no-long leaves out the 8 runs of 30 s that put the real window plans of YL (test divisor 1) through bwx8.` | Text of the description: `--no-long` leaves out the 8 runs of 30 s each that put the real window plans of step `YL`, with the test divisor 1, through `bwx8`. |
| 11 | `--no-bwx10 leaves out the run of the plans of YA, YP, YF and YC through a local stand-in bwx10. These` | Text of the description: `--no-bwx10` leaves out the run of the plans of the steps `YA`, `YP`, `YF` and `YC` through a local stand-in of `bwx10`. |
| 12 | `checks also print SKIP when bwx10.c is not beside this file or does not build here: the runner` | Continues the text: these checks also print `SKIP` when the source `bwx10.c` is not in the folder of this file, or when it cannot be built on this machine. |
| 13 | `is the work of another part.` | Continues the text: the reason given is that the runner is the work of another part of the project. |
| 14 | `Rules are also applied to a defective input, and such a check passes only if that is rejected.` | Text of the description: the test also applies each rule to an input with a defect. Such a check passes only when the rule rejects that input. This shows that the rule can fail. |
| 15 | `This machine has no CPU 41: for the runs through a stand-in the test rewrites CPU 41 to a local CPU` | Text of the description: the machine of the test has no CPU 41. For the runs through a stand-in binary the test replaces CPU 41 with a CPU that the machine has. |
| 16 | `in a copy of the schedule. Nothing else of the copy differs.` | Continues the text: the replacement is made in a copy of the schedule. Nothing else of the copy differs. |
| 17 | `"""` | Ends the description text. |
| 18 | `import collections` | Loads the Python module `collections`: counters and ordered dictionaries. |
| 19 | `import concurrent.futures` | Loads `concurrent.futures`: used to run several stand-in processes at the same time. |
| 20 | `import copy` | Loads `copy`: used to make an independent copy of a schedule before a check damages it. |
| 21 | `import itertools` | Loads `itertools`: used to merge equal neighbours of a list. |
| 22 | `import os` | Loads `os`: paths, folders and CPU lists. |
| 23 | `import re` | Loads `re`: regular expressions. |
| 24 | `import shutil` | Loads `shutil`: copies and removals of folder trees. |
| 25 | `import signal` | Loads `signal`: used to send a signal to the run script. |
| 26 | `import subprocess` | Loads `subprocess`: used to start the scripts under test. |
| 27 | `import sys` | Loads `sys`: the command line, the output and the exit status. |
| 28 | `import tempfile` | Loads `tempfile`: used to make the temporary folder of the test. |
| 29 | `import time` | Loads `time`: the clock, time texts and waits. |

### Paths, expected values of the task, and the function `check` (lines 31 to 78)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `sys.dont_write_bytecode = True` | Tells Python to write no compiled files into a `__pycache__` folder. So the test leaves no file in the code folder. |
| 32 | `Y = os.path.dirname(os.path.abspath(__file__))` | `Y`: the full path of the folder that holds this file, the folder of round 3. |
| 33 | `X = os.path.join(os.path.dirname(Y), "bwx8-2026-11-14")      # round 1 and 2: bwx8.c, run_bwx9.sh, visit9.sh, hostwatch.py` | `X`: the folder of rounds 1 and 2 beside it, `bwx8-2026-11-14`. The test reads `bwx8.c`, `run_bwx9.sh`, `visit9.sh` and `hostwatch.py` from it. |
| 34 | `SCHED = os.path.join(Y, "schedule10.py")` | `SCHED`: the path of the generator under test, `schedule10.py`. |
| 35 | `RUN = os.path.join(Y, "run_bwx10.sh")` | `RUN`: the path of the run script under test, `run_bwx10.sh`. |
| 36 | `VISIT = os.path.join(Y, "visit10.sh")` | `VISIT`: the path of the visit script under test, `visit10.sh`. |
| 37 | `WATCH = os.path.join(Y, "hostwatch.py")` | `WATCH`: the path of the host sampler `hostwatch.py` in this folder. |
| 38 | `NEW_KERNELS = ["read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"]` | `NEW_KERNELS`: the five kernels that the runner `bwx10` adds: the four prefetch kernels and `read_1pl`. |
| 39 | `READ_KERNELS = ["oldread", "read", "asmread", "read_nop4", "read_nop8", "read_nop16", "read_nop32", "read_sparse"] + NEW_KERNELS` | `READ_KERNELS`: the names of all read kernels that a plan may use. The plan validator of this file accepts only these names. The list holds 8 older names and the five new kernels, 13 names in all. |
| 40 | `# The flags of build8.sh.` | Comment: the compiler flags that follow are those of the build script `build8.sh`. |
| 41 | `CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "` | `CFLAGS`: the compiler flags for the stand-in builds, split into a list of words. This line: the optimisation level `-O3`, code for the CPU of this machine (`-march=native`), no replacement of a loop by a library call such as `memset` (`-fno-tree-loop-distribute-patterns`), thread support, more warnings, and the C dialect `gnu11`. |
| 42 | `          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()` | Continues the flags: do not merge functions that have equal code (`-fno-ipa-icf`), keep the functions in the order of the source (`-fno-toplevel-reorder`), and align each function to 4 bytes. |
| 43 | `# The task: processes per step and session, trials per process, nominal kernel work in seconds, binary.` | Comment: the table that follows states the task of the generator. For each step it gives the processes per session, the trials per process, the nominal kernel work in seconds and the binary. |
| 44 | `TABLE = collections.OrderedDict([("YA", (9, 1, 11.7, "bwx10")), ("YL", (32, 1, 960.0, "bwx8")), ("YP", (28, 1, 840.0, "bwx10")),` | `TABLE`: the expected values, written here as fixed numbers and not taken from the generator. `YA`: 9 processes of 1 trial, 11.7 s, binary `bwx10`. `YL`: 32 processes of 1 trial, 960.0 s, binary `bwx8`. `YP`: 28 processes of 1 trial, 840.0 s, binary `bwx10`. |
| 45 | `                                 ("YF", (288, 4, 2764.8, "bwx10")), ("YC", (42, 1, 252.0, "bwx10"))])` | Ends the table. `YF`: 288 processes of 4 trials, 2764.8 s, binary `bwx10`. `YC`: 42 processes of 1 trial, 252.0 s, binary `bwx10`. |
| 46 | `EVENTS = "cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17,l1d_cache_lmiss_rd=0x39,l2d_cache_lmiss_rd=0x4009"` | `EVENTS`: the 6 counter events that step `YC` must have in its `args` column, written here a second time. So a change of the list in the generator alone makes a check fail. |
| 47 | `# name: (windows, window length in ms, bins)` | Comment: each entry of `YL` maps the name of a window plan to its number of windows, its window length in ms and its `bins` value. |
| 48 | `YL = collections.OrderedDict([("L100", (300, 100, 0)), ("L300", (100, 300, 0)), ("L1000", (30, 1000, 0)), ("L30000", (1, 30000, 1))])` | `YL`: the four window plans as the test expects them. `L100`: 300 windows of 100 ms. `L300`: 100 windows of 300 ms. `L1000`: 30 windows of 1000 ms. `L30000`: 1 window of 30000 ms with `bins` equal to 1. The first three have `bins` equal to 0. |
| 49 | `YL_KERNELS = ["asmread", "read"]` | `YL_KERNELS`: the two kernels that step `YL` must use: `asmread` and `read`. |
| 50 | `# name: the options after the plan` | Comment: each entry of `YP` maps the label of a condition to the options that must stand after the plan path. |
| 51 | `YP = collections.OrderedDict([("P0", " --rec-pad 0"), ("P80", " --rec-pad 80"), ("P400", " --rec-pad 400"),` | `YP`: the seven conditions of step `YP` as the test expects them, each with its option text. This line: the pads of 0, 80 and 400 bytes. |
| 52 | `                              ("P1040", " --rec-pad 1040"), ("P2080", " --rec-pad 2080"), ("P4000", " --rec-pad 4000"),` | Continues the list: the pads of 1040, 2080 and 4000 bytes. |
| 53 | `                              ("hot", " --hot-copy")])` | Ends the list: the label `hot` with the option `--hot-copy`. |
| 54 | `YF_KERNELS = ["asmread"] + NEW_KERNELS` | `YF_KERNELS`: the six kernels that step `YF` must use: `asmread` and the five new kernels. |
| 55 | `YF_SIZES = ["32K", "1M", "8M", "16M"]` | `YF_SIZES`: the four buffer sizes that step `YF` must use: 32 KiB, 1 MiB, 8 MiB and 16 MiB. |
| 56 | `YC_KERNELS = YF_KERNELS + ["oldread"]` | `YC_KERNELS`: the seven kernels that step `YC` must use: those of `YF` and `oldread`. |
| 57 | `YC_SIZES = ["1M", "8M", "16M"]` | `YC_SIZES`: the three buffer sizes that step `YC` must use: 1, 8 and 16 MiB. |
| 58 | `# tag, kernel, size, the options after the plan` | Comment: each entry of the list that follows holds a tag, a kernel, a size and the options that stand after the plan path. |
| 59 | `YA = [("plain-cpu2", "asmread", "8M", " --trace"), ("pad80-cpu2", "asmread", "8M", " --trace --rec-pad 80"),` | `YA`: the 9 processes that the acceptance step `YA` must have, in their fixed order. This line: `asmread` at 8 MiB with `--trace` only, and `asmread` at 8 MiB with `--trace --rec-pad 80`. |
| 60 | `      ("hot-cpu2", "asmread", "8M", " --trace --hot-copy"), ("pf256-cpu2", "read_pf256", "8M", " --trace"),` | Continues the list: `asmread` with `--trace --hot-copy`, and `read_pf256` with `--trace`, both at 8 MiB. |
| 61 | `      ("pf512-cpu2", "read_pf512", "8M", " --trace"), ("pf1024-cpu2", "read_pf1024", "8M", " --trace"),` | Continues the list: `read_pf512` and `read_pf1024` at 8 MiB, each with `--trace`. |
| 62 | `      ("pf2048-cpu2", "read_pf2048", "8M", " --trace"), ("1pl-cpu2", "read_1pl", "8M", " --trace"),` | Continues the list: `read_pf2048` and `read_1pl` at 8 MiB, each with `--trace`. |
| 63 | `      ("pf1024s-cpu2", "read_pf1024", "32K", " --trace")]` | Ends the list: `read_pf1024` at 32 KiB with `--trace`. Every tag ends with `-cpu2`. |
| 64 | `HEAD_S2 = ["step", "session", "cpu", "bytes", "proc", "rep_set", "kernel", "size", "seed", "test"]` | `HEAD_S2`: the keys of the header pairs of a plan whose trials have the form of step `S2`, in the order that the plan file must have. |
| 66 | `FAILS = []` | `FAILS`: the names of the checks that failed, empty at first. |
| 67 | `COUNT = [0]` | `COUNT`: the number of checks. It is kept in a list of one entry, so a function can change it. |
| 70 | `def check(name, ok, detail=""):` | Starts the function `check`. Every check of this file calls it. `name`: the sentence that says what is checked. `ok`: the result of the test. `detail`: values to print when the check fails. |
| 71 | `    COUNT[0] += 1` | Counts the check. |
| 72 | `    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail)[:600] + "]") if detail and not ok else ""))` | Prints one line: `PASS` or `FAIL`, and then the name. After a failure it adds the first 600 characters of the detail in square brackets. |
| 73 | `    sys.stdout.flush()` | Writes the line to the output immediately. |
| 74 | `    if not ok:` | When the check failed. |
| 75 | `        FAILS.append(name)` | Keeps its name for the summary at the end. |
| 76 | `    return ok` | Returns the result. A caller can use it to stop a group of checks after a failure. |

### The plan validator of the test: patterns, `nbytes`, `parse_plan`, `rejected` (lines 79 to 164)

| Line | Source | Explanation |
|---:|---|---|
| 79 | `# ---------- an independent validator of plan format v1 (DECISIONS-bwx8.md, "Plan file") ----------` | Comment: the code that follows is a validator of the plan format, version 1. By the comment it is independent: it is written from the section "Plan file" of the notes file `DECISIONS-bwx8.md`, and not from the generator. So it can find a mistake of the generator. |
| 80 | `PHASE = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?):(\d+)$")` | `PHASE`: the pattern of a phase text such as `asmread@8M:1200`. Group 1 holds the kernel name: lower-case letters, digits and `_`. Group 2, after the `@`, holds the size: digits and an optional letter `K`, `M` or `G`. Group 3, after the colon, holds the duration in ms: digits. |
| 81 | `TGT = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?)$")` | `TGT`: the pattern of a target text such as `asmread@8M`. Group 1 holds the kernel name and group 2 the size, as in `PHASE`. A target has no duration. |

Line 82 holds a backslash directly before a `|`. It stands outside the table:

```text
COND = re.compile(r"^[^=|, ]+=[^=|, ]+(\|[^=|, ]+=[^=|, ]+)*$")
```

Explanation of line 82: `COND`: the pattern of a condition label such as `K=asmread|S=8M`. A label is one pair `key=value`, or several pairs with a vertical bar between them. A key and a value have at least one character each. They hold no equals sign, no vertical bar, no comma and no blank.

| Line | Source | Explanation |
|---:|---|---|
| 85 | `def nbytes(tok):` | Starts the function `nbytes`. It converts a size text such as `8M` to a number of bytes. |
| 86 | `    m = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}` | `m`: the factor of each unit letter: 1024 for `K`, 1024 times 1024 for `M`, and 1024 times that for `G`. |
| 87 | `    return int(tok[:-1]) * m[tok[-1]] if tok[-1] in m else int(tok)` | Returns the number before the letter times its factor. A text without a letter is a plain number of bytes. |
| 90 | `def parse_plan(text):` | Starts the function `parse_plan`, the validator. It reads the text of one plan file and tests every rule of the format. |
| 91 | `    """Returns (header dict, header key order, trials) or raises ValueError that names the defect."""` | Description text: the function returns the header pairs as a dictionary, the order of the header keys, and the list of trials. For a defect it raises a `ValueError` whose text names the defect. |
| 92 | `    if not text.endswith("\n"):` | Rule: the file ends with a newline. |
| 93 | `        raise ValueError("no final newline")` | If not: raises the error `no final newline`. |
| 94 | `    lines = text[:-1].split("\n")` | `lines`: the lines of the file, without the last newline. |
| 95 | `    if len(lines) < 4:` | Rule: the file has at least 4 lines. These are 3 header lines and one trial. |
| 96 | `        raise ValueError("fewer than 4 lines")` | If not: raises the error `fewer than 4 lines`. |
| 97 | `    if lines[0] != "# bwx8-plan v1":` | Rule: the first line is exactly `# bwx8-plan v1`. |
| 98 | `        raise ValueError("line 1")` | If not: raises an error with the text `line 1`. |
| 99 | `    if not lines[1].startswith("# "):` | Rule: the second line starts with `#` and a blank. |
| 100 | `        raise ValueError("line 2")` | If not: raises an error with the text `line 2`. |
| 101 | `    head = collections.OrderedDict()` | `head`: the header pairs, kept in the order of the file. |
| 102 | `    for pair in lines[1][2:].split(" "):` | Starts a loop over the pairs of the second line, split at single blanks. |
| 103 | `        k, eq, v = pair.partition("=")` | Splits a pair at the first equals sign into the key `k` and the value `v`. |
| 104 | `        if not k or not eq or not v or k in head or "," in pair:` | Rules for a pair: it has a key, an equals sign and a value. The key was not used before. The pair holds no comma. Two blanks in a row give an empty pair, which fails here. |
| 105 | `            raise ValueError("line 2 pair '%s'" % pair)` | If not: raises an error that shows the pair. |
| 106 | `        head[k] = v` | Stores the pair. |
| 107 | `    for k in ("step", "session", "cpu", "bytes", "proc", "seed", "test"):` | Starts a loop over the 7 keys that every plan must have: `step`, `session`, `cpu`, `bytes`, `proc`, `seed` and `test`. |
| 108 | `        if k not in head:` | Rule: the key is in the header. |
| 109 | `            raise ValueError("line 2 lacks " + k)` | If not: raises an error that names the missing key. |
| 110 | `    if lines[2] != "# trial cond rep prev pfx pred tgt nwin win_ms count bins":` | Rule: the third line is exactly the list of the 11 column names. |
| 111 | `        raise ValueError("line 3")` | If not: raises an error with the text `line 3`. |
| 112 | `    total = int(head["bytes"])` | `total`: the buffer size of the process in bytes, from the header. |
| 113 | `    seen = collections.Counter()` | `seen`: how often each condition label was used up to now. |
| 114 | `    trials = []` | `trials`: the result list, empty at first. |
| 116 | `    def size_ok(tok):` | Starts the inner function `size_ok`. It tests the size of a phase or of a target. |
| 117 | `        b = nbytes(tok)` | `b`: the size in bytes. |
| 118 | `        return b > 0 and b % 256 == 0 and b <= total` | Rule: the size is above 0, a multiple of 256 bytes, and not larger than the buffer of the process. |
| 120 | `    for n, line in enumerate(lines[3:]):` | Starts the loop over the trial lines. `n` counts from 0. |
| 121 | `        f = line.split(" ")` | Splits the line at single blanks. |
| 122 | `        if len(f) != 11 or "" in f:` | Rule: the line has exactly 11 fields, and none is empty. An empty field means two blanks in a row. |
| 123 | `            raise ValueError("trial line %d: fields" % n)` | If not: raises an error that names the trial line and the word `fields`. |
| 124 | `        trial, cond, rep, prev, pfx, pred, tgt, nwin, win_ms, count, bins = f` | Gives the 11 fields their names. |
| 125 | `        if trial != str(n):` | Rule: the trial number is the number of the line, counted from 0. |
| 126 | `            raise ValueError("trial line %d: number" % n)` | If not: raises an error with the word `number`. |
| 127 | `        if not COND.match(cond):` | Rule: the condition label matches the pattern `COND`. |
| 128 | `            raise ValueError("trial line %d: cond" % n)` | If not: raises an error with the word `cond`. |
| 129 | `        seen[cond] += 1` | Counts the use of this label. |
| 130 | `        if rep != str(seen[cond]) or not 1 <= seen[cond] <= 4:` | Rule: `rep` is the number of this use of the label, counted from 1. A label is used at most 4 times. |
| 131 | `            raise ValueError("trial line %d: rep" % n)` | If not: raises an error with the word `rep`. |
| 132 | `        ms = {}` | `ms`: the duration in ms of each of the three phases before the target. |
| 133 | `        for name, tok in (("prev", prev), ("pfx", pfx), ("pred", pred)):` | Starts a loop over the three phases: the previous activity, the prefix and the predecessor. |
| 134 | `            ms[name] = 0` | The duration is 0 unless the phase exists. |
| 135 | `            if tok == "-":` | A `-` means that the trial has no such phase. |
| 136 | `                continue` | Goes on with the next phase. |
| 137 | `            m = PHASE.match(tok)` | Matches the text with the pattern `PHASE`. |
| 138 | `            if not m or m.group(1) not in READ_KERNELS or not size_ok(m.group(2)) or int(m.group(3)) < 1:` | Rules for a phase: the text has the form of `PHASE`, the kernel is one of `READ_KERNELS`, the size passes `size_ok`, and the duration is at least 1 ms. |
| 139 | `                raise ValueError("trial line %d: %s" % (n, name))` | If not: raises an error that names the phase. |
| 140 | `            ms[name] = int(m.group(3))` | Stores the duration. |
| 141 | `        if ms["pfx"] % 4:` | Rule: the duration of the prefix is a multiple of 4 ms. By the notes file the runner records a prefix as 4 windows of a quarter of its duration. |
| 142 | `            raise ValueError("trial line %d: pfx not a multiple of 4" % n)` | If not: raises an error that says so. |
| 143 | `        m = TGT.match(tgt)` | Matches the target text with the pattern `TGT`. |
| 144 | `        if not m or m.group(1) not in READ_KERNELS or not size_ok(m.group(2)):` | Rules for the target: the form of `TGT`, a kernel of `READ_KERNELS`, and a size that passes `size_ok`. |
| 145 | `            raise ValueError("trial line %d: tgt" % n)` | If not: raises an error with the word `tgt`. |
| 146 | `        # The limits of the plan parser of bwx8.c: nwin 1 to 4096 (MAX_NWIN), win_ms 1 to 3600000 (MAX_MS).` | Comment: the next rule uses the limits of the plan parser in the runner source `bwx8.c`: 1 to 4096 windows (`MAX_NWIN`), and a window length of 1 to 3600000 ms (`MAX_MS`), which is one hour. |
| 147 | `        if not (nwin.isdigit() and 1 <= int(nwin) <= 4096 and win_ms.isdigit() and 1 <= int(win_ms) <= 3600000):` | Rule: both values are whole numbers inside these limits. |
| 148 | `            raise ValueError("trial line %d: windows" % n)` | If not: raises an error with the word `windows`. |
| 149 | `        if count not in ("closed", "open", "read") or bins not in ("0", "1"):` | Rule: the counter mode is `closed`, `open` or `read`, and `bins` is `0` or `1`. |
| 150 | `            raise ValueError("trial line %d: count or bins" % n)` | If not: raises an error with the words `count or bins`. |
| 151 | `        trials.append({"cond": cond, "rep": int(rep), "prev": prev, "pfx": pfx, "pred": pred, "tgt": tgt,` | Adds the trial as a dictionary. This line: the label, the repeat number, the three phase texts and the target. |
| 152 | `                       "nwin": int(nwin), "win_ms": int(win_ms), "count": count, "bins": int(bins),` | Continues the dictionary: the number and the length of the windows, the counter mode and the bins value. |
| 153 | `                       "ms": ms["prev"] + ms["pfx"] + ms["pred"] + int(nwin) * int(win_ms)})` | Ends the dictionary with `ms`, the nominal kernel work of the trial in ms: the three phase durations plus the number of windows times the window length. The test computes this value itself, without the generator. |
| 154 | `    return head, list(head), trials` | Returns the header dictionary, the list of its keys in file order, and the trials. |
| 157 | `def rejected(text):` | Starts the function `rejected`. It says whether the validator refuses a plan text. |
| 158 | `    try:` | Starts the block whose error is caught. |
| 159 | `        parse_plan(text)` | Runs the validator. |
| 160 | `    except ValueError:` | The validator raised a `ValueError`. |
| 161 | `        return True` | Returns true: the text was rejected. |
| 162 | `    return False` | Returns false: the text was accepted. |

### Reading a generated folder, and small rule helpers (lines 165 to 248)

| Line | Source | Explanation |
|---:|---|---|
| 165 | `# ---------- reading a generated tree ----------` | Comment: the functions that read a generated folder start here. |
| 166 | `def gen(out, *opts):` | Starts the function `gen`. It runs the generator with the output folder `out` and with more options. |
| 167 | `    return subprocess.run([sys.executable, SCHED, "--out", out] + list(opts), capture_output=True, text=True)` | Starts the generator as a process of its own, with the Python that runs this test. It keeps the output and the error output as text. It returns the result object, which also holds the exit status. |
| 170 | `def load(out):` | Starts the function `load`. It reads every schedule file and every plan file of a generated folder and tests their form. |
| 171 | `    """{(step, session): [process]}; a process holds its schedule row, header and trials."""` | Description text: the result maps each pair of step and session to its list of processes. A process holds its schedule row, its plan header and its trials. |
| 172 | `    tree, errors = {}, []` | `tree`: the result. `errors`: the list of the defects found. Both are empty at first. |
| 173 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 174 | `        sdir = os.path.join(out, "s%d" % session)` | `sdir`: the folder of the session. |
| 175 | `        for name in sorted(os.listdir(sdir)):` | Starts a loop over the names in the session folder, in sorted order. |
| 176 | `            if not name.endswith(".tsv"):` | A name that does not end with `.tsv`. |
| 177 | `                continue` | Skips it. Only schedule files are read here. |
| 178 | `            step = name[:-4]` | `step`: the file name without the ending `.tsv`. |
| 179 | `            rows = open(os.path.join(sdir, name)).read().split("\n")` | `rows`: the lines of the schedule file. |
| 180 | `            if rows[0] != "idx\ttag\tcpu\tbytes\tplan\targs" or rows[-1] != "":` | Rule: the first row is exactly the six column names with tabs between them, and the file ends with a newline. |
| 181 | `                errors.append("%s s%d: header or end of the schedule" % (step, session))` | If not: notes a defect of the header or of the end of the schedule. |
| 182 | `            procs = []` | `procs`: the processes of this step, empty at first. |
| 183 | `            for n, row in enumerate(rows[1:-1]):` | Starts the loop over the data rows. `n` counts from 0. |
| 184 | `                f = row.split("\t")` | Splits the row at the tabs. |
| 185 | `                if len(f) != 6 or f[0] != str(n) or f[4] != "%04d.plan" % n:` | Rule: the row has 6 columns, its `idx` is the row number, and its plan name is that number with 4 digits and the ending `.plan`. |
| 186 | `                    errors.append("%s s%d row %d: columns, idx or plan name" % (step, session, n))` | If not: notes the defect. |
| 187 | `                    continue` | Goes on with the next row. |
| 188 | `                p = {"idx": n, "tag": f[1], "cpu": int(f[2]), "bytes": int(f[3]), "plan": f[4], "args": f[5]}` | `p`: the process as a dictionary of its schedule columns. |
| 189 | `                want = "--trial --cpus %d --bytes %d --plan sched10/s%d/%s/%s" % (p["cpu"], p["bytes"], session, step, f[4])` | `want`: the start that the `args` column must have: `--trial`, `--cpus` with the CPU, `--bytes` with the size, and `--plan` with the path below `sched10/`. The CPU and the size come from the other columns of the row. So the columns must agree with the options. |
| 190 | `                if not (f[5] == want or f[5].startswith(want + " --")):` | Rule: the `args` are exactly `want`, or `want` followed by a blank and more options. |
| 191 | `                    errors.append("%s s%d row %d: args" % (step, session, n))` | If not: notes a defect of the `args`. |
| 192 | `                p["extra"] = f[5][len(want):]` | `extra`: the text of the `args` after `want`, that is the added options. |
| 193 | `                try:` | Starts the block whose errors are caught. |
| 194 | `                    p["head"], p["order"], p["trials"] = parse_plan(open(os.path.join(sdir, step, f[4])).read())` | Reads the plan file of the row and validates it with `parse_plan`. The header, the key order and the trials go into `p`. |
| 195 | `                except (ValueError, OSError) as e:` | A defect of the plan, or a plan file that cannot be read. |
| 196 | `                    errors.append("%s s%d row %d: %s" % (step, session, n, e))` | Notes the defect with the text of the error. |
| 197 | `                    continue` | Goes on with the next row. |
| 198 | `                h = p["head"]` | `h`: the header of the plan. |
| 199 | `                if (h["step"], h["session"], h["cpu"], h["bytes"], h["proc"]) != (step, str(session), f[2], f[3], f[0]):` | Rule: the header of the plan names the same step, session, CPU, size and process number as the schedule row. |
| 200 | `                    errors.append("%s s%d row %d: header pairs differ from the row" % (step, session, n))` | If not: notes that the header pairs differ from the row. |
| 201 | `                procs.append(p)` | Adds the process to the list. |
| 202 | `            tags = [p["tag"] for p in procs]` | `tags`: the tags of all processes of the step. |
| 203 | `            if len(set(tags)) != len(tags) or any(re.search(r"\s", t) for t in tags):` | Rule: no tag occurs twice in a step, and no tag holds a blank or another white-space character (pattern `\s`). |
| 204 | `                errors.append("%s s%d: a tag occurs twice or holds a blank" % (step, session))` | If not: notes the defect. |
| 205 | `            if len(os.listdir(os.path.join(sdir, step))) != len(procs):` | Rule: the plan folder of the step holds exactly as many files as the schedule has rows. |
| 206 | `                errors.append("%s s%d: plan files and rows differ in number" % (step, session))` | If not: notes the defect. |
| 207 | `            tree[step, session] = procs` | Stores the processes of the step and session. |
| 208 | `    return tree, errors` | Returns the result and the list of defects. |
| 211 | `def proc_ms(p):` | Starts the function `proc_ms`: the nominal kernel work of one process in ms. |
| 212 | `    return sum(t["ms"] for t in p["trials"])` | Returns the sum of the `ms` values of its trials. |
| 215 | `def tree_bytes(out):` | Starts the function `tree_bytes`. It reads every file of a folder tree into memory. |
| 216 | `    d = {}` | `d`: the result, empty at first. |
| 217 | `    for root, _, files in os.walk(out):` | Starts a walk through the folder and all folders below it. |
| 218 | `        for f in files:` | Starts a loop over the files of one folder. |
| 219 | `            path = os.path.join(root, f)` | The path of the file. |
| 220 | `            d[os.path.relpath(path, out)] = open(path, "rb").read()` | Stores the bytes of the file under its path relative to the top folder. |
| 221 | `    return d` | Returns the dictionary. Two folder trees are equal when their dictionaries are equal. |
| 224 | `def cpu_blocks(procs, first, second):` | Starts the function `cpu_blocks`, the rule for the CPU order of a schedule. |
| 225 | `    """The CPUs alternate first, second, first, ... when equal neighbours are merged."""` | Description text: when equal neighbours are merged, the CPUs of the processes alternate: the first CPU, the second, the first, and so on. |
| 226 | `    seq = [k for k, _ in itertools.groupby(p["cpu"] for p in procs)]` | `seq`: the CPUs of the processes in schedule order, with each run of equal neighbours merged to one entry. |
| 227 | `    return len(seq) % 2 == 0 and all(c == (first, second)[i % 2] for i, c in enumerate(seq))` | True when the merged list has an even length and alternates, with `first` at its start. |
| 230 | `def cpus_of(session):` | Starts the function `cpus_of`. |
| 231 | `    return (2, 41) if session == 1 else (41, 2)` | Returns the expected CPU order of a session: 2 and then 41 for session 1, and 41 and then 2 for session 2. |
| 234 | `def one_trial(cond, tgt, nwin, win, count="closed", bins=0, pfx=0):` | Starts the function `one_trial`. It builds the trial list that a process with one trial must have, in the form that `parse_plan` returns. |
| 235 | `    return [{"cond": cond, "rep": 1, "prev": "-", "pfx": "%s:%d" % (tgt, pfx) if pfx else "-", "pred": "-", "tgt": tgt,` | Returns a list with one dictionary. This line: the label, repeat 1, no previous activity, a prefix of the target itself when `pfx` is not 0, no predecessor, and the target. |
| 236 | `             "nwin": nwin, "win_ms": win, "count": count, "bins": bins, "ms": pfx + nwin * win}]` | Continues the dictionary: the windows, the counter mode, the bins value and the nominal work in ms. |
| 239 | `def s2_style(p, k, s):` | Starts the function `s2_style`, the rule for a process whose trials have the form of step `S2`. `k` is the kernel and `s` the size text. |
| 240 | `    """4 trials: the kernel at the size, with itself as 1.2 s prefix, 4 windows, uncounted."""` | Description text: the process has 4 trials. Each runs the kernel at the size, with itself as a prefix of 1.2 s, in 4 windows, without counters. |
| 241 | `    t = p["trials"]` | `t`: the trials of the process. |
| 242 | `    return len(t) == 4 and all(` | Starts the result. First condition: exactly 4 trials. |
| 243 | `        x == {"cond": "K=%s\|S=%s" % (k, s), "rep": i + 1, "prev": "-", "pfx": "%s@%s:%d" % (k, s, 4 * x["win_ms"]),` | Second condition, for each trial: it is equal to the expected dictionary. This line: the label with the kernel and the size. The repeat number, 1 to 4. No previous activity. A prefix of the same kernel and size that lasts 4 times the window length. |
| 244 | `              "pred": "-", "tgt": "%s@%s" % (k, s), "nwin": 4, "win_ms": x["win_ms"], "count": "closed", "bins": 0,` | Continues the expected dictionary: no predecessor, the target, 4 windows, the window length as found, counters closed, bins 0. The window length is not fixed here. So the rule also holds for a folder made with a test divisor. |
| 245 | `              "ms": 8 * x["win_ms"]} for i, x in enumerate(t)) and \` | Ends the expected dictionary: the nominal work is 8 window lengths, 4 for the prefix and 4 for the target. The backslash joins the next line to this statement. |
| 246 | `        p["bytes"] == nbytes(s) and p["head"].get("size") == str(nbytes(s)) and p["head"].get("kernel") == k` | Last conditions: the buffer of the process has the size `s`, and the header names that size and the kernel. |

### Rules of the steps `YL` and `YP` (lines 249 to 305)

| Line | Source | Explanation |
|---:|---|---|
| 249 | `# ---------- rules of the steps; each returns a list of defects. div: the test divisor of the tree ----------` | Comment: the functions that follow are the rules of the steps. Each one returns a list of defects. `div` is the test divisor of the folder that is tested. |
| 250 | `def yl_rules(procs, cpus, div=1):` | Starts the function `yl_rules`, the rules of step `YL`. `cpus` is the CPU order that the session must have, and `div` is the test divisor, 1 for a real schedule. The function returns the list of defects. |
| 251 | `    bad = []` | `bad`: the list of the defects found. An empty list means that the rules hold. |
| 252 | `    if len(procs) != 32:` | Rule: the step has 32 processes. |
| 253 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect, with the count found. |
| 254 | `    conds = sorted((k, n) for k in YL_KERNELS for n in YL)` | `conds`: the sorted list of the 8 expected conditions: each of the two kernels with the name of each window plan. |
| 255 | `    for b in range(4):` | Starts the loop over the 4 blocks of 8 processes. |
| 256 | `        block = procs[8 * b:8 * b + 8]` | `block`: the 8 processes of this block. |
| 257 | `        r, cpu = b // 2 + 1, cpus[b % 2]` | `r`: the replicate that the block must have: 1 for the first two blocks and 2 for the last two. `cpu`: the CPU that it must have: the first CPU of the session for the blocks 0 and 2, the second for the blocks 1 and 3. |
| 258 | `        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):` | Rule: every process of the block runs on that CPU and names that replicate in its header. |
| 259 | `            bad.append("block %d: CPU or rep_set" % b)` | If not: notes a defect of the CPU or of `rep_set` in this block. |
| 260 | `        if sorted((p["head"].get("kernel"), p["head"].get("lcond")) for p in block) != conds:` | Rule: the pairs of kernel and window plan in the headers of the block, sorted, are the 8 conditions. So each block holds every kernel with every window plan exactly once. |
| 261 | `            bad.append("block %d: does not hold every kernel and window plan once" % b)` | If not: notes the defect. |
| 262 | `    for p in procs:` | Starts a loop over all processes. |
| 263 | `        k, name = p["head"].get("kernel"), p["head"].get("lcond")` | `k`: the kernel from the header. `name`: the name of the window plan, from the header pair `lcond`. |
| 264 | `        if k not in YL_KERNELS or name not in YL:` | Rule: the kernel is one of the two kernels of `YL`, and the name is one of the four window plans. |
| 265 | `            bad.append("process %d: kernel or lcond" % p["idx"])` | If not: notes the defect for this process. |
| 266 | `            continue` | Goes on with the next process. |
| 267 | `        nwin, win, bins = YL[name]` | `nwin`, `win`, `bins`: the number of windows, the window length in ms and the `bins` value of that window plan, from the table `YL`. |
| 268 | `        if p["trials"] != one_trial("K=%s\|S=8M\|L=%d" % (k, win), k + "@8M", nwin, win // div, "closed", bins):` | Rule: the process has exactly this one trial: the label with the kernel, `S=8M` and the window length of the plan, no prefix, the target at 8 MiB, `nwin` windows of `win` ms divided by `div`, counters closed, and the `bins` value of the plan. The label holds the real window length, also with a test divisor. |
| 269 | `            bad.append("process %d (%s): trial" % (p["idx"], name))` | If not: notes a defect of the trial. |
| 270 | `        if p["bytes"] != 8 << 20 or p["head"].get("size") != str(8 << 20) or p["extra"] \` | Rules: the buffer has 8 MiB (`8 << 20` bytes), the header names that size, and the process has no added option. The backslash joins the next line. |
| 271 | `                or not p["tag"].startswith("%s-%s-" % (name, k)):` | Continues the rules: the tag starts with the name of the window plan, a hyphen, the kernel and a hyphen. |
| 272 | `            bad.append("process %d (%s): bytes, header, args or tag" % (p["idx"], name))` | If not: notes the defect. |
| 273 | `    if len({tuple((p["head"].get("kernel"), p["head"].get("lcond")) for p in procs[8 * b:8 * b + 8]) for b in range(4)}) < 2:` | Rule: at least two of the 4 blocks have different orders of their conditions. |
| 274 | `        bad.append("the condition order is the same in every block")` | If not: notes that the condition order is the same in every block. That would show that the conditions are not shuffled. |
| 275 | `    return bad` | Returns the list of defects. |
| 278 | `def yp_rules(procs, cpus, div=1):` | Starts the function `yp_rules`, the rules of step `YP`. `div` is the test divisor. |
| 279 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 280 | `    if len(procs) != 28:` | Rule: the step has 28 processes. |
| 281 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 282 | `    for b in range(4):` | Starts the loop over the 4 blocks of 7 processes. |
| 283 | `        block = procs[7 * b:7 * b + 7]` | `block`: the 7 processes of this block. |
| 284 | `        r, cpu = b // 2 + 1, cpus[b % 2]` | `r`: the replicate that the block must have: 1 for the first two blocks and 2 for the last two. `cpu`: the CPU that it must have: the first CPU of the session for the blocks 0 and 2, the second for the blocks 1 and 3. |
| 285 | `        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):` | Rule: every process of the block runs on that CPU and names that replicate in its header. |
| 286 | `            bad.append("block %d: CPU or rep_set" % b)` | If not: notes a defect of the CPU or of `rep_set` in this block. |
| 287 | `        if sorted(p["head"].get("pcond") for p in block) != sorted(YP):` | Rule: the condition labels of the block, sorted, are the 7 labels of `YP`. So each block holds every condition exactly once. |
| 288 | `            bad.append("block %d: does not hold every condition once" % b)` | If not: notes the defect. |
| 289 | `    for p in procs:` | Starts a loop over all processes. |
| 290 | `        name = p["head"].get("pcond")` | `name`: the label of the condition, from the header pair `pcond`. |
| 291 | `        if name not in YP:` | Rule: the label is one of the 7 labels. |
| 292 | `            bad.append("process %d: pcond" % p["idx"])` | If not: notes the defect. |
| 293 | `            continue` | Goes on with the next process. |
| 294 | `        if p["trials"] != one_trial("K=asmread\|S=8M\|rec=%s" % name, "asmread@8M", 100, 300 // div):` | Rule: the process has exactly this one trial: the label with `asmread`, 8 MiB and the label of the condition, no prefix, 100 windows of 300 ms divided by `div`, counters closed. |
| 295 | `            bad.append("process %d (%s): trial" % (p["idx"], name))` | If not: notes a defect of the trial. |
| 296 | `        if p["extra"] != YP[name]:` | Rule: the added options are exactly the option text of the label: `--rec-pad` with the number of the label, or `--hot-copy` for the label `hot`. So the label of a process and the option that the runner really gets cannot differ. |
| 297 | `            bad.append("process %d (%s): the options in args" % (p["idx"], name))` | If not: notes the defect. |
| 298 | `        if p["bytes"] != 8 << 20 or p["head"].get("kernel") != "asmread" or p["head"].get("size") != str(8 << 20) \` | Rules: the buffer has 8 MiB (`8 << 20` bytes), and the header names `asmread` and that size. The backslash joins the next line. |
| 299 | `                or not p["tag"].startswith(name + "-"):` | Continues the rules: the tag starts with the label of the condition and a hyphen. |
| 300 | `            bad.append("process %d (%s): bytes, header or tag" % (p["idx"], name))` | If not: notes the defect. |
| 301 | `    if len({tuple(p["head"].get("pcond") for p in procs[7 * b:7 * b + 7]) for b in range(4)}) < 2:` | Rule: at least two of the 4 blocks have different orders of their conditions. |
| 302 | `        bad.append("the condition order is the same in every block")` | If not: notes that the condition order is the same in every block. That would show that the conditions are not shuffled. |
| 303 | `    return bad` | Returns the list of defects. |

### Rules of the step `YF` (lines 306 to 354)

| Line | Source | Explanation |
|---:|---|---|
| 306 | `def yf_rules(procs, cpus):` | Starts the function `yf_rules`, the rules of step `YF`. It returns the list of defects. |
| 307 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 308 | `    if len(procs) != 288:` | Rule: the step has 288 processes. |
| 309 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 310 | `    sets = collections.defaultdict(lambda: collections.defaultdict(list))` | `sets`: for each pair of size and CPU, and for each replicate set, a list in schedule order. A missing entry is created at its first use. |
| 311 | `    for p in procs:` | Starts the loop over the processes in schedule order. |
| 312 | `        h = p["head"]` | `h`: the header of the plan. |
| 313 | `        k, s = h.get("kernel"), p["tag"].split("-")[1]` | `k`: the kernel from the header. `s`: the size text from the tag, its second part. |
| 314 | `        if k not in YF_KERNELS or s not in YF_SIZES or not s2_style(p, k, s):` | Rule: the kernel is one of the six kernels of `YF`, the size is one of its four sizes, and the process has 4 trials of the `S2` form. |
| 315 | `            bad.append("process %d: not 4 trials of one kernel of the family with itself as prefix" % p["idx"])` | If not: notes that the process does not have 4 trials of one kernel of the family with itself as the prefix. |
| 316 | `        if p["order"] != HEAD_S2 or p["extra"]:` | Rule: the header keys are those of `HEAD_S2`, in that order, and the process has no added option. |
| 317 | `            bad.append("process %d: header keys or args" % p["idx"])` | If not: notes the defect. |
| 318 | `        sets[s, p["cpu"]][int(h.get("rep_set", 0))].append(k)` | Adds the kernel of the process to its list. The size comes from the tag, the CPU from the schedule row, and the replicate set from the plan header. |
| 319 | `    assign = set()` | `assign`: the different tables of orders that were seen, one table per size and CPU. |
| 320 | `    if len(sets) != 8:` | Rule: there are 8 pairs of size and CPU, 4 sizes times 2 CPUs. |
| 321 | `        bad.append("sizes and CPUs")` | If not: notes the defect `sizes and CPUs`. |
| 322 | `    for (s, cpu), orders in sets.items():` | Starts the loop over the pairs of size and CPU. |
| 323 | `        o = [tuple(orders[r]) for r in sorted(orders)]` | `o`: the orders of the replicate sets of this pair, sorted by the set number. |
| 324 | `        if sorted(orders) != [1, 2, 3, 4, 5, 6] or any(sorted(x) != sorted(YF_KERNELS) for x in o):` | Rule: the sets have the numbers 1 to 6, and each set holds every one of the six kernels exactly once. |
| 325 | `            bad.append("size %s cpu %d: not 6 sets of the 6 kernels" % (s, cpu))` | If not: notes that this size and CPU does not have 6 sets of the 6 kernels. |
| 326 | `            continue` | Goes on with the next pair of size and CPU. |
| 327 | `        pos = collections.Counter((k, i) for x in o for i, k in enumerate(x))` | `pos`: how often each item stands at each position, over the 6 sets. |
| 328 | `        if len(pos) != 36 or set(pos.values()) != {1}:` | Rule: every kernel occurs at every position, which gives 36 pairs of kernel and position, and each of these counts is exactly 1. This is the balance of the position: no kernel always runs first or always runs last. |
| 329 | `            bad.append("size %s cpu %d: a kernel is not once at each position" % (s, cpu))` | If not: notes that a kernel is not once at each position. |
| 330 | `        pairs = collections.Counter((x[i], x[i + 1]) for x in o for i in range(5))` | `pairs`: how often each ordered pair of kernels stands as direct neighbours, over the 6 sets. A set of 6 kernels has 5 such pairs. |
| 331 | `        if len(pairs) != 30 or set(pairs.values()) != {1}:` | Rule: every ordered pair of different kernels occurs, which gives 30 pairs, and each exactly once. This is the balance of the process that runs directly before: each kernel follows each other kernel equally often. |
| 332 | `            bad.append("size %s cpu %d: an ordered pair of kernels is not once a pair of neighbours" % (s, cpu))` | If not: notes that an ordered pair of kernels is not once a pair of neighbours. |
| 333 | `        assign.add(tuple(o))` | Remembers the table of this size and CPU. |
| 334 | `    if len(assign) < 2:` | Rule: at least two pairs of size and CPU have different tables. |
| 335 | `        bad.append("every size and CPU uses the same kernel orders")` | If not: notes that every size and CPU uses the same kernel orders. That would show that the tables are not drawn at random for each size and CPU. |
| 336 | `    size_orders = set()` | `size_orders`: the different size orders of the sets. |
| 337 | `    for r in range(6):` | Starts the loop over the 6 replicate sets, by their place in the schedule. |
| 338 | `        block = procs[48 * r:48 * r + 48]` | `block`: the 48 processes of this set: 4 sizes times 2 CPUs times 6 kernels. |
| 339 | `        if any(p["head"].get("rep_set") != str(r + 1) for p in block):` | Rule: every process of the block names this set in its header. So the sets follow each other and do not mix. |
| 340 | `            bad.append("block %d: rep_set" % (r + 1))` | If not: notes a defect of the `rep_set` value of this block. |
| 341 | `        sizes = []` | `sizes`: the sizes of the block in schedule order. |
| 342 | `        for g in range(4):` | Starts the loop over the 4 size groups of the block. |
| 343 | `            twelve = block[12 * g:12 * g + 12]` | `twelve`: the 12 processes of one size: the 6 kernels on the first CPU and then the 6 kernels on the second CPU. |
| 344 | `            if len({p["bytes"] for p in twelve}) != 1 or [p["cpu"] for p in twelve] != [cpus[0]] * 6 + [cpus[1]] * 6:` | Rule: the group has one buffer size, and its CPUs are 6 times the first CPU of the session followed by 6 times the second. So the CPUs do not alternate inside a size. |
| 345 | `                bad.append("block %d group %d: size or CPU order" % (r + 1, g))` | If not: notes a defect of the size or of the CPU order of this group. |
| 346 | `            sizes.append(twelve[0]["bytes"])` | Adds the size of the group to `sizes`. |
| 347 | `        if len(set(sizes)) != 4:` | Rule: the block holds 4 different sizes. |
| 348 | `            bad.append("block %d: a size is missing" % (r + 1))` | If not: notes that a size is missing in this block. |
| 349 | `        size_orders.add(tuple(sizes))` | Remembers the size order of this block. |
| 350 | `    if len(size_orders) < 2:` | Rule: at least two blocks have different size orders. |
| 351 | `        bad.append("the size order is the same in every block")` | If not: notes that the size order is the same in every block. That would show that the sizes are not shuffled. |
| 352 | `    return bad` | Returns the list of defects. |

### Rules of the steps `YC` and `YA` (lines 355 to 396)

| Line | Source | Explanation |
|---:|---|---|
| 355 | `def yc_rules(procs, cpus, div=1):` | Starts the function `yc_rules`, the rules of step `YC`. `div` is the test divisor, 1 for a real schedule. |
| 356 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 357 | `    if len(procs) != 42:` | Rule: the step has 42 processes. |
| 358 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect, with the count found. |
| 359 | `    if [p["cpu"] for p in procs] != [cpus[0]] * 21 + [cpus[1]] * 21:` | Rule: the first 21 processes run on the first CPU of the session, and the last 21 on the second. |
| 360 | `        bad.append("CPU blocks are not 21 processes of the first CPU, then 21 of the second")` | If not: notes that the CPU blocks are not 21 processes of the first CPU and then 21 of the second. |
| 361 | `    cells = sorted((k, s) for k in YC_KERNELS for s in YC_SIZES)` | `cells`: the sorted list of the 21 expected cells: each of the seven kernels with each of the three sizes. |
| 362 | `    orders = []` | `orders`: the cell order of each of the two blocks, empty at first. |
| 363 | `    for b in range(2):` | Starts the loop over the 2 blocks of 21 processes, one block per CPU. |
| 364 | `        block = procs[21 * b:21 * b + 21]` | `block`: the 21 processes of this block. |
| 365 | `        got = [tuple(p["trials"][0]["tgt"].split("@")) for p in block]` | `got`: for each process of the block its cell: the kernel and the size text from the target of its first trial. |
| 366 | `        if sorted(got) != cells:` | Rule: the block, sorted, is the list of the 21 cells. So each block holds every kernel at every size exactly once. |
| 367 | `            bad.append("block %d: does not hold every kernel and size once" % b)` | If not: notes the defect. |
| 368 | `        orders.append(got)` | Keeps the cell order of this block. |
| 369 | `    for p in procs:` | Starts a loop over all processes. |
| 370 | `        k, s = p["trials"][0]["tgt"].split("@")` | `k`, `s`: the kernel and the size text from the target of the first trial. |
| 371 | `        if p["trials"] != one_trial("K=%s\|S=%s\|count=read" % (k, s), "%s@%s" % (k, s), 20, 300 // div, "read"):` | Rule: the process has exactly this one trial: the label with the kernel, the size and `count=read`, no prefix, 20 windows of 300 ms divided by `div`, and the counter mode `read`. |
| 372 | `            bad.append("process %d: trial" % p["idx"])` | If not: notes a defect of the trial. |
| 373 | `        if p["bytes"] != nbytes(s) or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)):` | Rule: the buffer has the size of the target, and the header names that kernel and that size in bytes. |
| 374 | `            bad.append("process %d: bytes or header" % p["idx"])` | If not: notes a defect of the bytes or of the header. |
| 375 | `        if p["extra"] != " --pmu-type 11 --events " + EVENTS:` | Rule: the added options are exactly `--pmu-type 11` and `--events` with the 6 events of `EVENTS`. Without these options the runner would need the counter settings from the environment. |
| 376 | `            bad.append("process %d: event set in args" % p["idx"])` | If not: notes a defect of the event set in the `args`. |
| 377 | `    if orders[0] == orders[1]:` | Rule: the two CPUs have different cell orders. |
| 378 | `        bad.append("the cell order is the same for both CPUs")` | If not: notes that the cell order is the same for both CPUs. That would show that the cells are not shuffled anew for the second CPU. |
| 379 | `    return bad` | Returns the list of defects. |
| 382 | `def ya_rules(procs, div=1):` | Starts the function `ya_rules`, the rules of the acceptance step. `div` is the test divisor. |
| 383 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 384 | `    if len(procs) != 9:` | Rule: the step has 9 processes. |
| 385 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 386 | `    for p, (tag, k, s, extra) in zip(procs, YA):` | Starts a loop that pairs each process with the expected entry of the list `YA`, in order. So the order of the processes is fixed. |
| 387 | `        ks = "%s@%s" % (k, s)` | `ks`: the kernel and the size in the form `KERNEL@SIZE`. |
| 388 | `        name = tag[:-5]` | `name`: the tag without its last 5 characters, which are `-cpu2`. |
| 389 | `        if p["tag"] != tag or p["cpu"] != 2 or p["bytes"] != nbytes(s) or p["extra"] != extra \` | Rules: the tag, CPU 2, the buffer size and the added options are those of the expected entry. The backslash joins the next line. |
| 390 | `                or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)) or p["head"].get("acond") != name:` | Continues the rules: the header names the kernel, the size in bytes and, under the key `acond`, the name. |
| 391 | `            bad.append("process %d: tag, CPU, bytes, args or header" % p["idx"])` | If not: notes the defect. |
| 392 | `        if p["trials"] != one_trial("K=%s\|S=%s\|acc=%s" % (k, s, name), ks, 3, 300 // div, "closed", 0, 400 // div):` | Rule: the process has exactly this one trial: a prefix of 400 ms and 3 windows of 300 ms, both divided by `div`, counters closed, bins 0. |
| 393 | `            bad.append("process %d: trial" % p["idx"])` | If not: notes a defect of the trial. |
| 394 | `    return bad` | Returns the list of defects. |

### `schedule_checks`: the generator runs, the validator can fail, counts and report (lines 397 to 453)

| Line | Source | Explanation |
|---:|---|---|
| 397 | `def schedule_checks(tmp):` | Starts the function `schedule_checks`. It holds all checks of the generator. |
| 398 | `    a, b, c = (os.path.join(tmp, n) for n in ("a", "b", "c"))` | `a`, `b`, `c`: three output folders in the temporary folder `tmp`. |
| 399 | `    r = gen(a)` | Runs the generator with its default options into the folder `a`. |
| 400 | `    check("schedule10.py runs with status 0", r.returncode == 0, r.stderr)` | Check: the generator ends with exit status 0. This proves that it runs to its end and that its own balance checks passed. A failed balance check would give status 1. |
| 401 | `    tree, errors = load(a)` | Reads the generated folder and collects the format defects. |
| 402 | `    check("every schedule row and plan file obeys the format and the plan grammar", not errors, errors[:3])` | Check: `load` found no defect. So every schedule row has the right form, and every plan file passes the validator of this file. This matters: the runner ends with status 2 for a plan with a defect. |
| 403 | `    check("the 5 steps exist in session 1; session 2 has the same steps without YA",` | Starts a check: the folder holds exactly the right steps. |
| 404 | `          sorted(tree) == sorted([(s, 1) for s in TABLE] + [(s, 2) for s in TABLE if s != "YA"]), sorted(tree))` | The test of that check: the pairs of step and session are the 5 steps in session 1, and the same steps without `YA` in session 2. So no step is missing, and no step was written that the task does not name. |
| 406 | `    # The validator itself rejects defective plans.` | Comment: the next checks show that the validator itself rejects plans with a defect. |
| 407 | `    good = open(os.path.join(a, "s1", "YL", "0000.plan")).read()` | `good`: the text of the first plan of `YL` in session 1, a plan with one trial and without a prefix. |
| 408 | `    good1 = open(os.path.join(a, "s1", "YA", "0000.plan")).read()` | `good1`: the text of the first plan of `YA` in session 1, a plan with the prefix `asmread@8M:400`. |
| 409 | `    line = good.split("\n")[3]` | `line`: the fourth line of `good`, its one trial line. |
| 410 | `    bad = {"rep not 1": good.replace(line, line.replace(" 1 - ", " 2 - ", 1)),` | `bad`: a dictionary of plan texts with one defect each. The key names the defect. First entry: the repeat number of the trial is 2 in place of 1. |
| 411 | `           "size above bytes": good1.replace("asmread@8M:400", "asmread@16M:400"),` | A prefix at 16 MiB in a process whose buffer has 8 MiB. |
| 412 | `           "unknown kernel": good1.replace("asmread@8M:400", "copy@8M:400"),` | A prefix with the kernel name `copy`, which is not a read kernel. |
| 413 | `           "prefix without a duration": good1.replace("asmread@8M:400", "asmread@8M"),` | A prefix without a colon and a duration. |
| 414 | `           "prefix that is not a multiple of 4 ms": good1.replace("asmread@8M:400", "asmread@8M:401"),` | A prefix of 401 ms, which is not a multiple of 4 ms. |
| 415 | `           "two spaces": good.replace(line, line.replace(" ", "  ", 1)),` | Two blanks in place of the first blank of the trial line. |
| 416 | `           "trial number": good.replace("\n0 ", "\n1 ", 1),` | The first trial has the number 1 in place of 0. |
| 417 | `           "wrong first line": good.replace("plan v1", "plan v2"),` | The first line names version 2 of the format. |
| 418 | `           "count word": good.replace(line, line.replace("closed", "shut")),` | The counter mode is the word `shut`, which does not exist. |
| 419 | `           "bins 2": good.replace(line, line[:-1] + "2"),` | The last field, `bins`, is 2. |
| 420 | `           "4097 windows": good.replace(line, re.sub(r" \d+ (\d+ closed)", r" 4097 \1", line)),` | 4097 windows, one more than the limit. The pattern finds a blank, digits, a blank, and then a group of digits, a blank and the word `closed`. These are the fields `nwin`, `win_ms` and `count`. The replacement puts 4097 in place of the first number and keeps the group (`\1`). |
| 421 | `           "a window of 3600001 ms": good.replace(line, re.sub(r" (\d+) \d+ closed", r" \1 3600001 closed", line)),` | A window length of 3600001 ms, 1 ms above the limit. Here the group holds the number of windows, which is kept. The second number is replaced. |
| 422 | `           "comma in cond": good.replace(line, line.replace("\|", ",", 1)),` | A comma in place of the first vertical bar of the condition label. |
| 423 | `           "blank in cond": good.replace(line, line.replace("\|", " ", 1)),` | A blank in place of the first vertical bar. The trial line then has 12 fields. |
| 424 | `           "header lacks seed": good.replace(" seed=", " sead=")}` | The header key `seed` is written `sead`, so the required key is missing. The brace ends the dictionary. |
| 425 | `    check("validator accepts generated plans", not rejected(good) and not rejected(good1))` | Check: the validator accepts the two plans as the generator wrote them. This is the control for the checks that follow: a rejection there comes from the defect alone. |
| 426 | `    for name, text in bad.items():` | Starts a loop over the damaged plans. |
| 427 | `        check("validator rejects: " + name, text not in (good, good1) and rejected(text))` | Check, once per defect: the damaged text really differs from the two good plans, and the validator rejects it. This proves that each of these rules of the validator can fail. A validator that accepts every text would make the format check of line 402 prove nothing. |
| 429 | `    # Counts and nominal work, from the files and from the printed report.` | Comment: the next checks compare the counts and the nominal work with the task. They take them from the files and from the report that the generator prints. |
| 430 | `    for step, (n, tr, sec, word) in TABLE.items():` | Starts a loop over the rows of `TABLE`: per step the expected processes, trials per process, seconds and word of the binary. |
| 431 | `        for s in (1, 2):` | Starts a loop over the two sessions. |
| 432 | `            if (step, s) not in tree:` | A step that does not exist in this session. |
| 433 | `                continue` | Skips it. |
| 434 | `            procs = tree[step, s]` | `procs`: the processes of this step and session, as read from the files. |
| 435 | `            ms = sum(proc_ms(p) for p in procs)` | `ms`: the nominal kernel work of the step in ms. The validator of this file computed it from the plan files. |
| 436 | `            check("%s session %d: %d processes of %d trial(s), %.1f s of nominal kernel work" % (step, s, n, tr, sec),` | Starts a check, once per step and session. Its name states the expected values. |
| 437 | `                  len(procs) == n and all(len(p["trials"]) == tr for p in procs) and ms == round(sec * 1000),` | The test of the check: the number of processes, the number of trials of every process and the nominal work in ms are those of `TABLE`. This proves that the files hold the planned task. A wrong count would make a session shorter or longer than planned, and a missing process would leave a condition with too few runs. |
| 438 | `                  (len(procs), ms))` | The detail for a failure: the number of processes and the nominal work that were found. |
| 439 | `            check("%s session %d: the report prints the binary, the process count and the nominal work" % (step, s),` | Starts a second check per step and session: the printed report agrees with the files. |
| 440 | `                  ("\n%s %d %s %d %d %g\n" % (step, s, word, n, n * tr, sec)) in r.stdout, r.stdout[:400])` | The test: the output of the generator holds the table row of this step and session with the same values: the word of the binary, the processes, the trials (processes times trials per process) and the seconds. So the numbers that a person reads before a run are the numbers of the files. |
| 441 | `    check("the report prints the totals of each session: 399 processes and 4828.5 s, 390 processes and 4816.8 s",` | Starts a check: the report prints the totals of each session. |
| 442 | `          "\nsession 1 total: 399 processes, nominal kernel work 4828.5 s (80.47 min)\n" in r.stdout` | The test, first half: the line of session 1 gives 399 processes and 4828.5 s (80.47 min) of nominal kernel work. |
| 443 | `          and "\nsession 2 total: 390 processes, nominal kernel work 4816.8 s (80.28 min)\n" in r.stdout, r.stdout[:900])` | Second half: the line of session 2 gives 390 processes and 4816.8 s (80.28 min). These totals say how long a session lasts at least. |
| 444 | `    check("the report states the balance of YL, YP and YF for both sessions, each with 'yes'",` | Starts a check: the report states the balance of the three steps that have a balance check, each with `yes`. |
| 445 | `          len(re.findall(r"^Y[LPF] session [12]: .*: yes$", r.stdout, re.M)) == 6 and ": NO" not in r.stdout, r.stdout[-900:])` | The test: exactly 6 lines match the pattern, one for each of the steps `YL`, `YP` and `YF` in each session. The pattern matches a line that starts with `Y` and one of the letters L, P, F, then the word `session`, 1 or 2, a colon, any text, and `: yes` at its end. `re.M` lets `^` and `$` match at the start and the end of every line. Also no line holds `: NO`. |
| 446 | `    short = copy.deepcopy(tree["YF", 1])` | `short`: an independent copy of the processes of `YF` in session 1. |
| 447 | `    short[0]["trials"].pop()` | Removes the last trial of the first process of the copy. |
| 448 | `    check("nominal work: a schedule with one trial missing does not give the YF value",` | Starts a check: a schedule with one trial missing does not give the nominal work of `YF`. |
| 449 | `          sum(proc_ms(p) for p in short) != 2764800)` | The test: the sum of the copy is not 2764800 ms. This proves that the work check of lines 436 to 438 can fail. It notices one missing trial. |
| 450 | `    check("one process at a time is at most 30 s of kernel work (YL and YP)",` | Starts a check: no process has more than 30 s of nominal kernel work. |
| 451 | `          max(proc_ms(p) for procs in tree.values() for p in procs) == 30000` | The test, first half: the largest nominal work of one process, over all steps and sessions, is exactly 30000 ms. |
| 452 | `          and all(proc_ms(p) == 30000 for st in ("YL", "YP") for p in tree[st, 1]))` | Second half: every process of `YL` and of `YP` in session 1 has exactly 30000 ms. The longest process matters: the run script computes `MARGIN` from it. |

### `schedule_checks`: header pairs and CPU order (lines 454 to 481)

| Line | Source | Explanation |
|---:|---|---|
| 454 | `    # Header pairs.` | Comment: the next checks test the header pairs of the plans. |
| 455 | `    check("plan headers: seed is one value per step and session, test=0",` | Starts a check: inside one step and session every plan has the same seed, and every plan has `test=0`. |
| 456 | `          all(len({p["head"]["seed"] for p in procs}) == 1 and all(p["head"]["test"] == "0" for p in procs)` | The test: the set of the seed values of a step and session has one member, and the `test` value of every plan is `0`. |
| 457 | `              for procs in tree.values()))` | The loop of the test runs over all steps and sessions. So a plan file shows which random order it belongs to, and no test plan with shortened durations is among the real plans. |
| 458 | `    check("plan headers: the seeds of the steps and sessions differ",` | Starts a check: the seeds of the steps and sessions differ. |
| 459 | `          len({procs[0]["head"]["seed"] for procs in tree.values()}) == 9)` | The test: the set of the seeds of all steps and sessions has 9 members, one per step and session. Equal seeds would give two steps the same random choices. |
| 460 | `    check("plan headers: kernel and size name the target of every trial",` | Starts a check: the header pairs `kernel` and `size` name the target of every trial. |
| 461 | `          all(all(t["tgt"].split("@")[0] == p["head"]["kernel"] and nbytes(t["tgt"].split("@")[1]) == int(p["head"]["size"])` | The test: for each trial, the kernel of the target is the header value `kernel`, and the size of the target in bytes is the header value `size`. |
| 462 | `                  and int(p["head"]["size"]) == p["bytes"] for t in p["trials"])` | Continues the test: the header value `size` is also the buffer size of the process. |
| 463 | `              for procs in tree.values() for p in procs))` | The loops of the test run over every process of every step and session. This matters: the runner copies the header pairs into its output, so they must describe what the process really runs. |
| 464 | `    check("cond labels are key=value pairs that agree with the trial (kernel, size, counter mode)",` | Starts a check: every condition label agrees with its trial. |
| 465 | `          all(dict(x.split("=") for x in t["cond"].split("\|")).get("count", "closed") == t["count"]` | The test, first half: the label is split at the vertical bars into pairs `key=value`. Its `count` value, or `closed` when the label has none, is the counter mode of the trial. |
| 466 | `              and "K=%s\|S=%s" % tuple(t["tgt"].split("@")) == "\|".join(t["cond"].split("\|")[:2])` | Second half: the first two pairs of the label are `K=` with the kernel of the target and `S=` with its size. |
| 467 | `              for procs in tree.values() for p in procs for t in p["trials"]))` | The loops run over every trial of every process. A label that names another kernel, size or counter mode than the trial would put a measurement under a wrong name. |
| 468 | `    check("no trial of round 3 has a previous activity or a predecessor, and only YL L30000 has bins",` | Starts a check: no trial of round 3 has a previous activity or a predecessor, and only the window plan `L30000` of `YL` has bins. |
| 469 | `          all(t["prev"] == "-" and t["pred"] == "-" and (t["bins"] == 1) == (p["head"].get("lcond") == "L30000")` | The test: for every trial the previous activity and the predecessor are `-`. `bins` is 1 exactly when the header pair `lcond` of the process is `L30000`. |
| 470 | `              for procs in tree.values() for p in procs for t in p["trials"]))` | The loops run over every trial of every process of every step and session. |
| 472 | `    # CPU order of the sessions.` | Comment: the next checks test the CPU order of the sessions. |
| 473 | `    for (step, s), procs in sorted(tree.items()):` | Starts a loop over all steps and sessions, in sorted order. |
| 474 | `        if step == "YA":` | Tests for the acceptance step `YA`, which uses CPU 2 only. |
| 475 | `            continue` | Skips it. |
| 476 | `        check("%s session %d: CPU order %d then %d" % ((step, s) + cpus_of(s)), cpu_blocks(procs, *cpus_of(s)))` | Check, per step and session: the CPUs of the schedule alternate in the order of that session, 2 and then 41 in session 1, 41 and then 2 in session 2. The design asks that the second session reverses the order of the worker CPUs. |
| 477 | `    check("CPU order rule rejects session 1 read as session 2", not cpu_blocks(tree["YL", 1], 41, 2))` | Check: the rule rejects the session 1 schedule of `YL` when it is tested with the CPU order of session 2. So the check of line 476 can fail. |
| 478 | `    check("session 2 is not session 1 with the CPUs exchanged (own random order)",` | Starts a check: the schedule of session 2 is not the schedule of session 1 with the two CPUs exchanged. |
| 479 | `          all([p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in tree[st, 1]] !=` | The test, left side: for a step, the list of the tags of session 1 with the CPU number removed. `cpu2` and `cpu41` both become `c`. |
| 480 | `              [p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in tree[st, 2]] for st in ("YL", "YP", "YF", "YC")))` | Right side: the same list for session 2. The two lists must differ for each of the steps `YL`, `YP`, `YF` and `YC`. This proves that session 2 has a random order of its own. |

### `schedule_checks`: steps `YL` and `YP` (lines 482 to 518)

| Line | Source | Explanation |
|---:|---|---|
| 482 | `    # YL.` | Comment: the checks of step `YL` start here. |
| 483 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 484 | `        d = yl_rules(tree["YL", s], cpus_of(s))` | `d`: the defects that `yl_rules` finds in the schedule of this session, tested with the CPU order of this session. |
| 485 | `        check("YL session %d: asmread and read at 8M with the 4 window plans once per replicate block and CPU, each trial "` | Starts a check per session: the schedule of `YL` obeys all its rules. The name lists them: `asmread` and `read` at 8 MiB with the 4 window plans, once per replicate block and CPU. |
| 486 | `              "30 s (300 x 100, 100 x 300, 30 x 1000 ms without bins, 1 x 30000 ms with bins), no option in args" % s, not d, d[:3])` | Ends the name: each trial has 30 s, as 300 windows of 100 ms, 100 of 300 ms or 30 of 1000 ms without bins, or as 1 window of 30000 ms with bins, and no option stands in the `args`. The test: the list of defects is empty. |
| 487 | `    check("YL rules reject the session 1 schedule under the session 2 CPU order", bool(yl_rules(tree["YL", 1], (41, 2))))` | Check: the rules reject the unchanged session 1 schedule when it is tested with the CPU order of session 2. So the CPU order is really tested. |
| 488 | `    m = copy.deepcopy(tree["YL", 1])` | `m`: an independent copy of the `YL` schedule of session 1, for a damaged variant. |
| 489 | `    m[0]["trials"][0]["nwin"] += 1` | Adds one window to the trial of the first process. |
| 490 | `    check("YL rules reject a trial with one more window", bool(yl_rules(m, (2, 41))))` | Check: the rules reject a trial with one more window. |
| 491 | `    m = copy.deepcopy(tree["YL", 1])` | A new copy of the schedule. |
| 492 | `    for p in m:` | Starts a loop over its processes. |
| 493 | `        if p["head"]["lcond"] == "L30000":` | Only a process with the window plan `L30000`. |
| 494 | `            p["trials"][0]["bins"] = 0` | Sets `bins` of its trial to 0. |
| 495 | `    check("YL rules reject L30000 without bins", bool(yl_rules(m, (2, 41))))` | Check: the rules reject `L30000` without bins. Such a process would give one rate for the whole 30 s and no values from inside the window. |
| 496 | `    m = copy.deepcopy(tree["YL", 1])` | A new copy of the schedule. |
| 497 | `    m[0], m[8] = m[8], m[0]` | Exchanges process 0 with process 8, the first process of the next block. |
| 498 | `    check("YL rules reject two processes exchanged between blocks", bool(yl_rules(m, (2, 41))))` | Check: the rules reject two processes that were exchanged between blocks. Each block must hold every condition once on its own CPU. |
| 499 | `    fixed = sorted(tree["YL", 1], key=lambda p: (int(p["head"]["rep_set"]), p["cpu"], p["head"]["kernel"], p["head"]["lcond"]))` | `fixed`: the `YL` schedule of session 1 sorted by replicate, CPU, kernel and name of the window plan. Every block then has its conditions in the same order. |
| 500 | `    check("YL rules reject a fixed condition order in every block",` | Starts a check: the rules reject a fixed condition order in every block. |
| 501 | `          yl_rules(fixed, (2, 41)) == ["the condition order is the same in every block"], yl_rules(fixed, (2, 41))[:3])` | The test: the list of defects is exactly one entry, the one about the same condition order in every block. So the rule that asks for a shuffle can fail, and this variant breaks no other rule. |
| 503 | `    # YP.` | Comment: the checks of step `YP` start here. |
| 504 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 505 | `        d = yp_rules(tree["YP", s], cpus_of(s))` | `d`: the defects that `yp_rules` finds in the schedule of this session. |
| 506 | `        check("YP session %d: asmread at 8M, 100 windows of 300 ms; --rec-pad 0, 80, 400, 1040, 2080, 4000 and --hot-copy "` | Starts a check per session: the schedule of `YP` obeys all its rules. The name lists them: `asmread` at 8 MiB, 100 windows of 300 ms, and the options `--rec-pad` with 0, 80, 400, 1040, 2080 and 4000 and `--hot-copy`. |
| 507 | `              "once per replicate block and CPU" % s, not d, d[:3])` | Ends the name: each condition once per replicate block and CPU. The test: the list of defects is empty. |
| 508 | `    check("YP rules reject the session 1 schedule under the session 2 CPU order", bool(yp_rules(tree["YP", 1], (41, 2))))` | Check: the rules reject the session 1 schedule when it is tested with the CPU order of session 2. |
| 509 | `    m = copy.deepcopy(tree["YP", 1])` | `m`: an independent copy of the `YP` schedule of session 1. |
| 510 | `    [p for p in m if p["head"]["pcond"] == "P80"][0]["extra"] = " --rec-pad 800"` | Gives the first process with the label `P80` the option `--rec-pad 800`. |
| 511 | `    check("YP rules reject a pad that differs from its label", bool(yp_rules(m, (2, 41))))` | Check: the rules reject a pad that differs from its label. Such a process would be analysed under a pad that it did not run with. |
| 512 | `    m = copy.deepcopy(tree["YP", 1])` | A new copy of the schedule. |
| 513 | `    [p for p in m if p["head"]["pcond"] == "hot"][0]["extra"] = ""` | Removes the option of the first process with the label `hot`. |
| 514 | `    check("YP rules reject the hot condition without --hot-copy", bool(yp_rules(m, (2, 41))))` | Check: the rules reject the `hot` condition without `--hot-copy`. Such a process would run the normal window loop and still have the name `hot`. |
| 515 | `    m = copy.deepcopy(tree["YP", 1])` | A new copy of the schedule. |
| 516 | `    m[0], m[7] = m[7], m[0]` | Exchanges process 0 with process 7, the first process of the next block. |
| 517 | `    check("YP rules reject two processes exchanged between blocks", bool(yp_rules(m, (2, 41))))` | Check: the rules reject two processes that were exchanged between blocks. |

### `schedule_checks`: steps `YF`, `YC` and `YA`, and the event list (lines 519 to 568)

| Line | Source | Explanation |
|---:|---|---|
| 519 | `    # YF.` | Comment: the checks of step `YF` start here. |
| 520 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 521 | `        d = yf_rules(tree["YF", s], cpus_of(s))` | `d`: the defects that `yf_rules` finds in the schedule of this session. |
| 522 | `        check("YF session %d: S2-style trials, header keys as S2, 6 kernels at 32K, 1M, 8M, 16M; per size and CPU each kernel "` | Starts a check per session: the schedule of `YF` obeys all its rules. The name lists them: trials of the `S2` form, the header keys of `S2`, the 6 kernels at the four sizes, and per size and CPU each kernel once at each position. |
| 523 | `              "once at each position and each ordered pair of kernels once as neighbours; block order as S2" % s, not d, d[:3])` | Ends the name: each ordered pair of kernels once as neighbours, and the order of the blocks as in `S2`. The test: the list of defects is empty. This proves that the order of the real schedule is a Williams square per size and CPU. So no kernel is favoured by its place in the run order or by the process before it. |
| 524 | `    m = copy.deepcopy(tree["YF", 1])` | `m`: an independent copy of the `YF` schedule of session 1, for a damaged variant. |
| 525 | `    for i in range(0, 288, 6):                       # every set in the order of YF_KERNELS` | Starts a loop over the 48 groups of 6 processes. By the comment every set gets the kernels in the order of `YF_KERNELS`. |
| 526 | `        for p, k in zip(m[i:i + 6], YF_KERNELS):` | Starts a loop that pairs the 6 processes of a group with the 6 kernels in their fixed order. |
| 527 | `            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]` | `s`: the size text from the tag. `ms`: the window length of the first trial. |
| 528 | `            p["head"]["kernel"] = k` | Writes the kernel into the header of the process. |
| 529 | `            for t in p["trials"]:` | Starts a loop over the trials of the process. |
| 530 | `                t.update(cond="K=%s\|S=%s" % (k, s), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))` | Rewrites the label, the prefix and the target of the trial for that kernel. So each process stays valid by itself, and only the order is wrong. |
| 531 | `    d = yf_rules(m, (2, 41))` | `d`: the defects that `yf_rules` finds in this variant. |
| 532 | `    check("YF rules reject a schedule in which every set has one fixed kernel order",` | Starts a check: the rules reject a schedule in which every set has one fixed kernel order. |
| 533 | `          any("once at each position" in x for x in d) and any("neighbours" in x for x in d), d[:3])` | The test: one defect names the positions and one names the neighbours. This proves that both balance rules can fail. A generator that wrote the same kernel order in every set would not pass. |
| 534 | `    m = copy.deepcopy(tree["YF", 1])` | A new copy of the schedule. |
| 535 | `    m[5], m[6] = m[6], m[5]` | Exchanges the processes 5 and 6. They are the last process of the first CPU and the first process of the second CPU in the first size group. |
| 536 | `    check("YF rules reject CPUs that alternate inside a size", bool(yf_rules(m, (2, 41))))` | Check: the rules reject this variant. So they notice CPUs that alternate inside a size. |
| 537 | `    m = copy.deepcopy(tree["YF", 1])` | A new copy of the schedule. |
| 538 | `    m[5]["trials"][0]["pfx"] = "asmread@1M:1200" if m[5]["head"]["kernel"] != "asmread" else "read_1pl@1M:1200"` | Gives the first trial of process 5 a prefix of another kernel at 1 MiB: `asmread`, or `read_1pl` when the process itself runs `asmread`. |
| 539 | `    check("YF rules reject a prefix of another kernel or size", bool(yf_rules(m, (2, 41))))` | Check: the rules reject this variant. So they notice a prefix that is not the target kernel at the target size. |
| 540 | `    check("YF rules reject the session 1 schedule under the session 2 CPU order", bool(yf_rules(tree["YF", 1], (41, 2))))` | Check: the rules reject the unchanged session 1 schedule when it is tested with the CPU order of session 2. |
| 541 | `    check("YF: 6 processes per kernel, size and CPU",` | Starts a check: each combination of kernel, size and CPU has 6 processes. |
| 542 | `          set(collections.Counter((p["head"]["kernel"], p["bytes"], p["cpu"]) for p in tree["YF", 1]).values()) == {6}` | The test, first half: a count of the processes of session 1 per kernel, buffer size and CPU. Every count is exactly 6. |
| 543 | `          and len({(p["head"]["kernel"], p["bytes"], p["cpu"]) for p in tree["YF", 1]}) == 48)` | Second half: there are 48 such combinations, 6 kernels times 4 sizes times 2 CPUs. So every combination has its 6 replicates. |
| 545 | `    # YC, YA.` | Comment: the checks of the steps `YC` and `YA` start here. |
| 546 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 547 | `        d = yc_rules(tree["YC", s], cpus_of(s))` | `d`: the defects that `yc_rules` finds in the schedule of this session. |
| 548 | `        check("YC session %d: 7 kernels at 1M, 8M, 16M once per CPU, 20 windows of 300 ms, count read, "` | Starts a check per session: the schedule of `YC` obeys all its rules. The name lists them: 7 kernels at 1, 8 and 16 MiB once per CPU, 20 windows of 300 ms, and the counter mode `read`. |
| 549 | `              "--pmu-type 11 and the 6 events in args" % s, not d, d[:3])` | Ends the name: `--pmu-type 11` and the 6 events in the `args` column. The test: the list of defects is empty. |
| 550 | `    m = copy.deepcopy(tree["YC", 1])` | `m`: an independent copy of the `YC` schedule of session 1. |
| 551 | `    m[0]["trials"][0]["count"] = "closed"` | Changes the counter mode of the first trial of the first process to `closed`. |
| 552 | `    check("YC rules reject a trial with count closed", bool(yc_rules(m, (2, 41))))` | Check: the rules reject a trial with closed counters. Such a process would give no counter values. |
| 553 | `    m = copy.deepcopy(tree["YC", 1])` | A new copy of the schedule. |
| 554 | `    m[3]["extra"] = m[3]["extra"].replace("0x4009", "0x4008")` | Changes one event code in the options of process 3, from `0x4009` to `0x4008`. |
| 555 | `    check("YC rules reject another event code", bool(yc_rules(m, (2, 41))))` | Check: the rules reject another event code. A wrong code would count another event under the same name. |
| 556 | `    check("YC rules reject the session 1 schedule under the session 2 CPU order", bool(yc_rules(tree["YC", 1], (41, 2))))` | Check: the rules reject the session 1 schedule when it is tested with the CPU order of session 2. |
| 557 | `    check("the event set: 6 events, names below 32 characters, 6 different names and codes",` | Starts a check of the expected event list `EVENTS` itself: 6 events, names of fewer than 32 characters, 6 different names and 6 different codes. |
| 558 | `          len(EVENTS.split(",")) == 6 and all(re.match(r"^[a-z0-9_]{1,31}=0x[0-9a-f]+$", e) for e in EVENTS.split(","))` | The test, first half: the list has 6 entries. Each matches the pattern: a name of 1 to 31 lower-case letters, digits or `_`, an equals sign, `0x` and hexadecimal digits in lower case. |
| 559 | `          and len({e.split("=")[0] for e in EVENTS.split(",")}) == 6 and len({int(e.split("=")[1], 16) for e in EVENTS.split(",")}) == 6)` | Second half: the 6 names differ, and the 6 codes differ as numbers. The limit of the name length matters: the runner keeps an event name in 32 bytes and refuses a name of 32 or more characters. |
| 560 | `    d = ya_rules(tree["YA", 1])` | `d`: the defects that `ya_rules` finds in the `YA` schedule of session 1. |
| 561 | `    check("YA: CPU 2 only, 9 processes with --trace in the fixed order (plain, --rec-pad 80, --hot-copy, the 5 new kernels at 8M, "` | Starts a check: the schedule of `YA` obeys its rules. The name lists them: CPU 2 only, and 9 processes with `--trace` in the fixed order: plain, `--rec-pad 80`, `--hot-copy`, and the 5 new kernels at 8 MiB. |
| 562 | `          "read_pf1024 at 32K), each one trial: prefix 400 ms, 3 windows of 300 ms, count closed, bins 0", not d, d[:3])` | Ends the name: `read_pf1024` at 32 KiB as the last process, and each process with one trial: a prefix of 400 ms and 3 windows of 300 ms, counters closed, bins 0. The test: the list of defects is empty. The acceptance step tries each new feature of the runner once: the two new options and the five new kernels. |
| 563 | `    m = copy.deepcopy(tree["YA", 1])` | `m`: an independent copy of the `YA` schedule. |
| 564 | `    m[4]["extra"] = ""` | Removes all added options of process 4. |
| 565 | `    check("YA rules reject a process without --trace", bool(ya_rules(m)))` | Check: the rules reject a process without `--trace`. Without the trace log the acceptance run could not show what the runner does around its timed parts. |
| 566 | `    check("YA: session 2 has no schedule, no plan folder and no binary file",` | Starts a check: session 2 has no schedule, no plan folder and no `.bin` file of `YA`. |
| 567 | `          not [f for f in os.listdir(os.path.join(a, "s2")) if f.startswith("YA")])` | The test: no name in the folder `s2` starts with `YA`. So the run script cannot run the acceptance step in session 2: it ends with status 2 for a missing schedule. |

### `schedule_checks`: `.bin` files, seeds, `MANIFEST.txt`, saved folder, test divisor (lines 569 to 626)

| Line | Source | Explanation |
|---:|---|---|
| 569 | `    # Binary files and sampler markers.` | Comment: the next checks test the `.bin` files and the marker files of the host sampler. |
| 570 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 571 | `        sdir = os.path.join(a, "s%d" % s)` | `sdir`: the folder of the session in the generated folder. |
| 572 | `        bins = {f[:-4]: open(os.path.join(sdir, f)).read() for f in os.listdir(sdir) if f.endswith(".bin")}` | `bins`: a dictionary from the step name to the content of its `.bin` file, for every `.bin` file of the session folder. |
| 573 | `        check("session %d: one .bin file per step; YL names bwx8, every other step names bwx10; one word and a newline" % s,` | Starts a check per session: there is one `.bin` file per step. The file of `YL` holds the word `bwx8`, and every other file holds `bwx10`, each as one word and a newline. |
| 574 | `              bins == {st: TABLE[st][3] + "\n" for st in TABLE if (st, s) in tree}, bins)` | The test: the dictionary is equal to the expected one, which has the word of `TABLE` with a newline for every step of this session. The run script reads this word to choose the binary. Another word would start another runner, or stop the run with status 2. |
| 575 | `        check("session %d: no .watch file (no step of round 3 runs with the host sampler)" % s,` | Starts a check per session: the session folder has no `.watch` file. |
| 576 | `              not [f for f in os.listdir(sdir) if f.endswith(".watch")])` | The test: no name in the session folder ends with `.watch`. So the run script starts no host sampler for these steps. |
| 578 | `    # Determinism.` | Comment: the next checks test that the output is fully fixed by the options. |
| 579 | `    gen(b)` | Runs the generator a second time with the default options, into the folder `b`. |
| 580 | `    r3 = gen(c, "--seed", "7")` | Runs it a third time with `--seed 7`, into the folder `c`. |
| 581 | `    ta, tb, tc = tree_bytes(a), tree_bytes(b), tree_bytes(c)` | `ta`, `tb`, `tc`: the files of the three folders, each as a dictionary from the path to the bytes. |
| 582 | `    nfiles = 1 + sum(TABLE[s][0] + 2 for s in TABLE) + sum(TABLE[s][0] + 2 for s in TABLE if s != "YA")` | `nfiles`: the expected number of files: 1 for `MANIFEST.txt`, plus for each step of session 1 its plan files and 2 more (the schedule and the `.bin` file), plus the same for each step of session 2 other than `YA`. With the values of `TABLE` that is 808 files. |
| 583 | `    check("two runs with one base seed give the same bytes (%d files)" % nfiles, ta == tb and len(ta) == nfiles, len(ta))` | Check: two runs with the same base seed give the same files with the same bytes, and the number of files is `nfiles`. This proves that a schedule can be made again from its seed. The order that ran can then be checked later. |
| 584 | `    check("another base seed gives the same file names and other bytes",` | Starts a check: another base seed gives the same file names and other bytes. |
| 585 | `          r3.returncode == 0 and sorted(ta) == sorted(tc) and ta != tc` | The test, first half: the third run ended with status 0, the two folders have the same file names, and their contents differ. |
| 586 | `          and all(ta["s1/%s.tsv" % s] != tc["s1/%s.tsv" % s] for s in ("YL", "YP", "YF", "YC")))` | Second half: the schedule files of `YL`, `YP`, `YF` and `YC` in session 1 differ between the two seeds. This proves that the seed really drives the order of each shuffled step. |
| 587 | `    check("the base seed and the seed of every step and session are saved in MANIFEST.txt",` | Starts a check: the base seed and the seed of every step and session are saved in `MANIFEST.txt`. |
| 588 | `          b"base_seed=20261115\ntest_divisor=1\n" in ta["MANIFEST.txt"] and b"base_seed=7\n" in tc["MANIFEST.txt"]` | The test, first half: the manifest of the default run holds the lines `base_seed=20261115` and `test_divisor=1`, and the manifest of the third run holds `base_seed=7`. |
| 589 | `          and all(("seed %s s%d %s\n" % (st, s, procs[0]["head"]["seed"])).encode() in ta["MANIFEST.txt"]` | Second half: for each step and session the manifest holds a line `seed`, the step, the session and the seed that the plan headers carry. |
| 590 | `                  for (st, s), procs in tree.items()))` | The loop of that test runs over all steps and sessions. So the record of the seeds agrees with the plan files. |
| 591 | `    check("MANIFEST.txt names the binary of every step and session, and states that no step has a sampler marker",` | Starts a check: `MANIFEST.txt` names the binary of every step and session, and it states that no step has a marker file for the host sampler. |
| 592 | `          all(("bin %s s%d %s\n" % (st, s, TABLE[st][3])).encode() in ta["MANIFEST.txt"] for (st, s) in tree)` | The test, first part: for each step and session the manifest holds a line `bin`, the step, the session and the word of the binary from `TABLE`. |
| 593 | `          and ta["MANIFEST.txt"].count(b"\nbin ") == 9 and ta["MANIFEST.txt"].endswith(b"\nwatch none\n"), ta["MANIFEST.txt"][-200:])` | Second part: the manifest has exactly 9 lines that start with `bin`, and it ends with the line `watch none`. |
| 594 | `    tree7, errors7 = load(c)` | `tree7`, `errors7`: the folder of the third run, read and tested with `load`. |
| 595 | `    check("another base seed keeps the rules (grammar, YL, YP, YF, YC, YA)",` | Starts a check: another base seed keeps the rules. |
| 596 | `          not errors7 and not yl_rules(tree7["YL", 2], (41, 2)) and not yf_rules(tree7["YF", 1], (2, 41))` | The test: no format defect, and no defect from `yl_rules` for session 2 or from `yf_rules` for session 1. |
| 597 | `          and not yp_rules(tree7["YP", 2], (41, 2)) and not yc_rules(tree7["YC", 1], (2, 41)) and not ya_rules(tree7["YA", 1]))` | Continues the test: no defect from `yp_rules` for session 2, `yc_rules` for session 1 and `ya_rules`. This proves that the balance does not depend on the default seed. The construction gives it for another seed too. |
| 598 | `    saved = os.path.join(Y, "sched10")` | `saved`: the folder `sched10` beside this file. It holds the schedules that the run script reads. |
| 599 | `    check("the saved sched10/ beside the scripts is the output of the default base seed",` | Starts a check: the saved folder is the output of the generator with the default base seed. The repo README lists the folders `sched*` among those that were left out of the repo. So the repo folder has no `sched10`, and from there this check fails. |
| 600 | `          os.path.isdir(saved) and tree_bytes(saved) == ta)` | The test: the saved folder exists, and its files are equal to the files that the generator wrote now, name by name and byte by byte. So the schedules that will run are the ones that this test examined. |
| 601 | `    src = open(SCHED).read()` | `src`: the text of the generator. |
| 602 | `    check("schedule10.py imports the standard library only (no file of round 1 or 2)",` | Starts a check: the generator imports modules of the Python standard library only, and no file of round 1 or 2. |
| 603 | `          sorted(set(re.findall(r"^(?:import\|from) (\w+)", src, re.M))) == ["argparse", "hashlib", "os", "random", "shutil", "sys"]` | The test, first half: the sorted set of the imported module names is exactly this list of 6. The pattern finds, at the start of a line, the word `import` or `from`, a blank, and then a group with the module name. `re.M` lets `^` match at every line start. |
| 604 | `          and "sys.path" not in src, sorted(set(re.findall(r"^(?:import\|from) (\w+)", src, re.M))))` | Second half: the text of the generator does not hold `sys.path`. So it does not add a folder to the search path of Python to load a file from there. The generator then needs no other file. It also runs where the folders of the earlier rounds are missing. |
| 605 | `    check("hostwatch.py in this folder is the file of round 2, byte for byte",` | Starts a check: the file `hostwatch.py` in this folder is the file of round 2, byte for byte. |
| 606 | `          open(WATCH, "rb").read() == open(os.path.join(X, "hostwatch.py"), "rb").read())` | The test: the bytes of the two files are equal. So the host sampler that was used before was not changed for round 3. |
| 608 | `    # --test-divisor.` | Comment: the checks of the option `--test-divisor` start here. |
| 609 | `    t = os.path.join(tmp, "t")` | `t`: one more output folder. |
| 610 | `    r6 = gen(t, "--test-divisor", "100")` | Runs the generator with `--test-divisor 100` into `t`. |
| 611 | `    ttree, terr = load(t)` | `ttree`, `terr`: that folder, read and tested with `load`. |
| 612 | `    check("--test-divisor 100: valid plans, test=1, every duration divided by 100, window counts unchanged",` | Starts a check: with the divisor 100 the plans are valid, they carry `test=1`, every duration is divided by 100, and the numbers of windows do not change. |
| 613 | `          r6.returncode == 0 and not terr and sorted(ttree) == sorted(tree)` | The test: the run ended with status 0, there is no format defect, and the steps and sessions are the same as in the real folder. |
| 614 | `          and all(p["head"]["test"] == "1" for pp in ttree.values() for p in pp)` | Continues the test: every plan has `test=1`. |
| 615 | `          and all(sum(proc_ms(p) for p in ttree[k]) * 100 == sum(proc_ms(p) for p in tree[k]) for k in tree)` | Continues the test: for each step and session the nominal work times 100 is the nominal work of the real folder. |
| 616 | `          and all([t_["nwin"] for p in ttree[k] for t_ in p["trials"]] == [t_["nwin"] for p in tree[k] for t_ in p["trials"]]` | Continues the test: the list of the window counts of all trials is the same as in the real folder. |
| 617 | `                  for k in tree)` | The loop of that comparison runs over all steps and sessions. |
| 618 | `          and not yl_rules(ttree["YL", 1], (2, 41), 100) and not yp_rules(ttree["YP", 1], (2, 41), 100)` | Continues the test: the divided folder passes `yl_rules` and `yp_rules` for session 1, both called with the divisor 100. |
| 619 | `          and not yc_rules(ttree["YC", 2], (41, 2), 100) and not ya_rules(ttree["YA", 1], 100)` | Continues the test: it passes `yc_rules` for session 2 and `ya_rules`, both called with the divisor 100. |
| 620 | `          and not yf_rules(ttree["YF", 1], (2, 41)), terr[:3])` | Ends the test: it passes `yf_rules` for session 1. That function takes no divisor: it does not fix the window length. This matters: the later checks run this short folder through the run script and through the stand-in runners. It must be the same schedule in every respect but the durations. |
| 621 | `    for div in ("7", "3", "300", "0"):` | Starts a loop over four divisors that must be refused: 7, 3, 300 and 0. |
| 622 | `        check("--test-divisor %s is refused (it does not divide 100 ms, the shortest window)" % div,` | Starts a check per divisor: it is refused. 100 ms, the shortest window, divided by 7, 3 or 300 is not a whole number of ms, and 0 is not a divisor. |
| 623 | `              gen(os.path.join(tmp, "u"), "--test-divisor", div).returncode != 0 and not os.path.exists(os.path.join(tmp, "u")))` | The test: the generator ends with a status other than 0, and the output folder `u` was not created. A divisor that does not divide a window would give windows of another length ratio than the real ones. |
| 624 | `    return a, t` | Returns two folders: the real one (`a`) and the one with the divisor 100 (`t`). The later checks use them. |

### Runs through a stand-in runner: `stand_in_jobs`, `run_job`, `local_cpus` (lines 627 to 682)

| Line | Source | Explanation |
|---:|---|---|
| 627 | `# ---------- plans through a local stand-in binary ----------` | Comment: the functions that put plans through a local stand-in binary start here. |
| 628 | `def stand_in_jobs(d, steps, alt, sessions=(1, 2), only=None):` | Starts the function `stand_in_jobs`. It lists the processes to run through a stand-in. `d`: a folder that holds a copy of the schedule folder. `steps`: the steps whose plans are wanted. `alt`: the CPU that replaces CPU 41. `sessions`: the sessions to read, both unless given. `only`: an optional set of row numbers. |
| 629 | ``    """Jobs for the plans of `steps` in the tree d/sched10. CPU 41 is rewritten to `alt` in that tree."""`` | Description text: the function returns the jobs for the plans of the given steps in the folder `sched10` of `d`. In that copy CPU 41 is rewritten to `alt`. |
| 630 | `    jobs = []` | `jobs`: the result list, empty at first. |
| 631 | `    for session in sessions:` | Starts a loop over the sessions. |
| 632 | `        sdir = os.path.join(d, "sched10", "s%d" % session)` | `sdir`: the session folder of the copy. |
| 633 | `        for step in steps:` | Starts a loop over the steps. |
| 634 | `            if not os.path.exists(os.path.join(sdir, step + ".tsv")):` | A step without a schedule file in this session. |
| 635 | `                continue` | Skips it. |
| 636 | `            for n, row in enumerate(open(os.path.join(sdir, step + ".tsv")).read().split("\n")[1:-1]):` | Starts a loop over the data rows of the schedule. `n` counts from 0. |
| 637 | `                if only is not None and n not in only:` | When `only` is given and does not hold this row number. |
| 638 | `                    continue` | Skips the row. |
| 639 | `                f = row.split("\t")` | Splits the row at the tabs. |
| 640 | `                args = f[5]` | `args`: the options of the process. |
| 641 | `                plan = os.path.join(sdir, step, f[4])` | `plan`: the path of its plan file. |
| 642 | `                text = open(plan).read()` | `text`: the text of the plan. |
| 643 | `                if f[2] == "41" and alt != 41:` | A process on CPU 41, on a machine where another CPU must be used. |
| 644 | `                    args = args.replace("--cpus 41 ", "--cpus %d " % alt)` | Replaces `--cpus 41` in the options with the other CPU. |
| 645 | `                    with open(plan, "w") as out:` | Opens the plan file of the copy for writing. |
| 646 | `                        out.write(text.replace(" cpu=41 ", " cpu=%d " % alt))` | Writes the plan again with `cpu=41` in its header replaced. The runner refuses a plan whose `cpu` pair differs from `--cpus`, so both must change. |
| 647 | `                trials = [l.split(" ") for l in text.split("\n")[3:-1]]` | `trials`: the trial lines of the plan, each split into its fields. |
| 648 | `                jobs.append((step, session, f[0], args.split(), len(trials), sum(int(t[7]) for t in trials),` | Adds the job. This line: the step, the session, the `idx`, the options as a list, the number of trials, and the sum of the target windows of all trials (field `nwin`). |
| 649 | `                             sum((1 if t[3] != "-" else 0) + (4 if t[4] != "-" else 0) for t in trials),` | Continues the job: the number of other windows that the runner must print: 1 for each previous activity and 4 for each prefix. |
| 650 | `                             sum(int(t[7]) * (int(t[8]) // 10 + 2) for t in trials if t[10] == "1")))` | Ends the job: the number of bin records that the runner must report. Only trials with `bins` equal to 1 count. For each such trial the value is `nwin * (win_ms // 10 + 2)`. |
| 651 | `    return jobs` | Returns the jobs. |
| 654 | `def run_job(binary, d, env, job):` | Starts the function `run_job`. It runs one job through a binary and compares the output with the plan. |
| 655 | `    """None if the binary accepted the plan and printed every planned row, or a tuple that describes the defect."""` | Description text: the result is `None` when the binary accepted the plan and printed every planned row. If not, it is a tuple that describes the defect. |
| 656 | `    step, session, idx, args, ntr, nwin, nother, nbins = job` | Splits the job into its 8 values. |
| 657 | `    try:` | Starts the block whose timeout is caught. |
| 658 | `        r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True, timeout=300)` | Runs the binary with the options of the job, in the folder `d` and with the environment `env`. The output is kept as text. The run may take at most 300 s. |
| 659 | `    except subprocess.TimeoutExpired:` | The run took longer than 300 s. |
| 660 | `        return (step, session, idx, "timeout")` | Returns a tuple with the word `timeout`. |
| 661 | `    rows = collections.Counter()` | `rows`: a count of the output rows per kind. |
| 662 | `    for l in r.stdout.split("\n"):` | Starts a loop over the output lines. |
| 663 | `        f = l.split(",")` | Splits a line at the commas. The first field is the kind of the row. |
| 664 | `        rows[f[0] if f[0] != "W" else "W." + ("target" if f[2] == "target" else "other")] += 1` | Counts the row under its kind. A `W` row (one window) is counted as `W.target` when its phase field is `target`, and as `W.other` if not. |
| 665 | `    m = dict(l.split(",", 2)[1:] for l in r.stdout.split("\n") if l.startswith("M,") and l.count(",") >= 2)` | `m`: the `M` rows of the output as a dictionary from the key to the value. An `M` row has the form `M,key,value`. |
| 666 | `    ok = r.returncode == 0 and rows["S"] == ntr and rows["E"] == ntr and rows["W.target"] == nwin \` | `ok`, first conditions: exit status 0, one `S` row (start of a trial) and one `E` row (end of a trial) per planned trial, and as many `W` rows of target windows as the plan has windows. |
| 667 | `        and rows["W.other"] == nother and m.get("plan.step") == step and m.get("plan.proc") == idx \` | Continues: the planned number of other windows, and the `M` rows `plan.step` and `plan.proc` name this step and this process. So the runner read the right plan. |
| 668 | `        and m.get("mode") == "trial" and m.get("rec_bins") == str(nbins) and (rows["B"] >= 1) == (nbins > 0)` | Continues: the mode is `trial`, the `M` row `rec_bins` gives the expected number of bin records, and `B` rows exist exactly when bins are planned. |
| 669 | `    if ok and "--events" in args:` | For a process with `--events`. |
| 670 | `        ok = m.get("pmu_type") == "11" and m.get("events", "").count(";") == 5 and rows["C"] + rows["X"] >= 1` | `ok` now needs: the `M` row `pmu_type` is 11, the `M` row `events` holds 6 events (5 semicolons), and at least one `C` row (counter values) or `X` row (a failure that the runner reports) exists. |
| 671 | `    if ok and "--trace" in args:` | For a process with `--trace`. |
| 672 | `        ok = m.get("trace") == "1" and rows["TR"] >= 1` | `ok` now needs: the `M` row `trace` is 1, and at least one `TR` row (one entry of the trace log) exists. |
| 673 | `    return None if ok else (step, session, idx, r.returncode, r.stderr[-200:], dict(rows))` | Returns `None` for a good run. If not, it returns the step, the session, the `idx`, the exit status, the last 200 characters of the error output and the row counts. |
| 676 | `def local_cpus():` | Starts the function `local_cpus`. It finds the CPU that stands in for CPU 41 on this machine. |
| 677 | `    allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)` | `allowed`: the CPUs on which this process may run, without those above 119, in sorted order. |
| 678 | `    if not check("this machine allows CPU 0, CPU 2 and one more CPU below 120", 0 in allowed and 2 in allowed and len(allowed) > 2):` | Check: this machine allows CPU 0, CPU 2 and at least one more CPU below 120. The stand-in runs need CPU 2 for the worker and CPU 0 for the controlling thread of the runner. |
| 679 | `        return None` | When the check fails: returns `None`, and the caller runs no stand-in job. |
| 680 | `    return 41 if 41 in allowed else [c for c in allowed if c not in (0, 2)][0]` | Returns 41 when CPU 41 is allowed. If not, it returns the lowest allowed CPU other than 0 and 2. |

### `bwx8_checks`: the plans of step `YL` through a stand-in `bwx8` (lines 683 to 744)

| Line | Source | Explanation |
|---:|---|---|
| 683 | `def bwx8_checks(tmp, real, sched):` | Starts the function `bwx8_checks`: the checks with a stand-in of the runner `bwx8`. `real`: the generated folder with the real durations. `sched`: the folder with the test divisor 100. |
| 684 | `    d = os.path.join(tmp, "bwx8")` | `d`: the folder `bwx8` in the temporary folder. |
| 685 | `    os.makedirs(d)` | Creates the folder `d`. |
| 686 | `    binary = os.path.join(d, "bwx8")` | `binary`: the path of the stand-in binary in that folder. |
| 687 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-o", binary, os.path.join(X, "bwx8.c")], capture_output=True, text=True)` | Runs `gcc` with the flags of `CFLAGS`, the output path and the source `bwx8.c` from the folder of round 1. The output of the compiler is kept as text. |
| 688 | `    if not check("stand-in build of bwx8.c of round 1 in a temporary folder (flags of build8.sh)", r.returncode == 0, r.stdout + r.stderr):` | Check: the stand-in build of `bwx8.c` worked, that is `gcc` ended with status 0. The detail of a failure is the output of the compiler. A failed build is a failed check here, and not a `SKIP`. |
| 689 | `        return` | Without the binary the rest of the function is left out. |
| 690 | `    alt = local_cpus()` | `alt`: the CPU that stands in for CPU 41 on this machine. |
| 691 | `    if alt is None:` | When this machine does not have the CPUs that the runs need. |
| 692 | `        return` | Leaves the function. The failed check of `local_cpus` is counted. |
| 693 | `    shutil.copytree(sched, os.path.join(d, "sched10"))` | Copies the schedule folder with the test divisor 100 to `sched10` in the folder of the binary. The plan paths in the `args` column are relative to this place. |
| 694 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment without every variable whose name starts with `BWX_`. |
| 695 | `    jobs = stand_in_jobs(d, ["YL"], alt)` | `jobs`: one job per process of step `YL` in both sessions, with CPU 41 replaced. |
| 696 | `    t0 = time.time()` | `t0`: the time before the runs, for the name of a check. |
| 697 | `    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:` | Creates a pool of 6 worker threads. So up to 6 stand-in processes run at the same time. |
| 698 | `        results = list(pool.map(lambda j: run_job(binary, d, env, j), jobs))` | Runs every job through `run_job` in the pool and collects the results in the order of the jobs. |
| 699 | `    for session in (1, 2):` | Starts a loop over the two sessions. |
| 700 | `        res = [x for j, x in zip(jobs, results) if j[1] == session]` | `res`: the results of the jobs of this session. |
| 701 | `        bad = [x for x in res if x]` | `bad`: the results that describe a defect. |
| 702 | `        check("YL session %d (test divisor 100): bwx8 accepts each of the %d plans with its args: status 0, one S and one E row "` | Starts a check per session: the stand-in `bwx8` accepts each plan of `YL` with its options. The name lists what `run_job` tested: status 0, one `S` row and one `E` row per trial. |
| 703 | `              "per trial, every planned window as a W row, B rows only for the plan with bins" % (session, len(res)),` | Continues the name: every planned window as a `W` row, and `B` rows, which are the bin records, only for the plan with bins. |
| 704 | `              len(res) == 32 and not bad, bad[:2])` | The test: there are 32 results, and none describes a defect. This proves that the runner can read every plan and every command line that the generator writes for this step. A plan that the runner refused on CRB would end the step with exit status 1. |
| 705 | `    check("all %d plans of the bwx8 step ran through bwx8 (%.0f s)" % (len(jobs), time.time() - t0),` | Starts a check: all plans of the step that uses `bwx8` ran through the stand-in. The name gives the number of jobs and the seconds that the runs took. |
| 706 | `          len(jobs) == 64 and all(x is None for x in results))` | The test: there are 64 jobs, 32 per session, and every result is `None`. |
| 707 | `    # The real window plans, test divisor 1: the first replicate block of session 1 holds every kernel and` | Comment: the next part runs the real window plans, with the test divisor 1. The first replicate block of session 1 holds every kernel with every window plan once. |
| 708 | `    # window plan once, all on CPU 2. Each process is 30 s of kernel work; the 8 run at the same time.` | Continues the comment: all processes of that block use CPU 2. Each process has 30 s of kernel work, and the 8 processes run at the same time. |
| 709 | `    if "--no-long" in sys.argv[1:]:` | When the option `--no-long` was given. |
| 710 | `        print("SKIP  the 8 runs of 30 s of the real YL window plans through bwx8 (--no-long)")` | Prints a `SKIP` line for this part. The part does not run, and no check is counted for it. |
| 711 | `    else:` | If not. |
| 712 | `        dr = os.path.join(tmp, "bwx8real")` | `dr`: one more temporary folder. |
| 713 | `        os.makedirs(dr)` | Creates it. |
| 714 | `        shutil.copytree(real, os.path.join(dr, "sched10"))` | Copies the schedule folder with the real durations to `sched10` in it. |
| 715 | `        jobs = stand_in_jobs(dr, ["YL"], alt, sessions=(1,), only=set(range(8)))` | `jobs`: the jobs for the first 8 rows of `YL` in session 1. |
| 716 | `        t0 = time.time()` | `t0`: the time before the runs. |
| 717 | `        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:` | Creates a pool of 8 worker threads. |
| 718 | `            results = list(pool.map(lambda j: run_job(binary, dr, env, j), jobs))` | Runs the jobs in the pool, all at the same time, and collects the results in the order of the jobs. All workers are pinned to the same CPU, so the rates of these runs mean nothing. Only the printed rows are tested. |
| 719 | `        bad = [x for x in results if x]` | `bad`: the results that describe a defect. |
| 720 | `        forms = sorted((j[5], j[7]) for j in jobs)` | `forms`: for each job the pair of its number of target windows and its number of bin records, in sorted order. |
| 721 | `        check("YL real plans (test divisor 1, first block of session 1, %.0f s): bwx8 accepts 300 x 100 ms, 100 x 300 ms, "` | Starts a check: with the real plans, `bwx8` accepts 300 windows of 100 ms, 100 windows of 300 ms, 30 windows of 1000 ms, and 1 window of 30000 ms with bins. The name gives the seconds that the runs took. |
| 722 | `              "30 x 1000 ms and 1 x 30000 ms with bins (3002 bin records) for both kernels and prints every window" % (time.time() - t0),` | Continues the name: the window with bins has 3002 bin records, the check covers both kernels, and the runner prints every window. 3002 is 30000 ms divided by 10 ms, plus 2. |
| 723 | `              forms == [(1, 3002)] * 2 + [(30, 0)] * 2 + [(100, 0)] * 2 + [(300, 0)] * 2 and not bad, (forms, bad[:2]))` | The test: the 8 jobs are two of each window plan, one per kernel: 1 window with 3002 bin records, and 30, 100 and 300 windows without bins. No result describes a defect. This proves that the real plans of `YL`, each 30 s long, run to their end with their real durations. |
| 724 | `    # The acceptance means something only if bwx8 refuses a defective plan.` | Comment: the acceptance of the good plans means something only if `bwx8` refuses a plan with a defect. |
| 725 | `    plan = os.path.join(d, "sched10", "s1", "YL", "0000.plan")` | `plan`: the first plan of `YL` in session 1, in the copy with the test divisor 100. |
| 726 | `    text = open(plan).read()` | `text`: the text of that plan. |
| 727 | `    line = text.split("\n")[3]` | `line`: its one trial line. |
| 728 | `    args = ["--trial", "--cpus", "2", "--bytes", "8388608", "--plan"]` | `args`: the options for the next runs: one worker on CPU 2 and a buffer of 8388608 bytes (8 MiB). The plan path is added in each run. |
| 729 | `    for name, bad in (("an unknown kernel", text.replace("@", "x@")),` | Starts a loop over plans with one defect each. First: an unknown kernel, made by an `x` before each `@`. |
| 730 | `                      ("a size above --bytes", text.replace("@8M", "@64M")),` | Second: a size of 64 MiB, which is above `--bytes`. |
| 731 | `                      ("4097 windows", text.replace(line, re.sub(r" \d+ (\d+ closed)", r" 4097 \1", line))),` | Third: 4097 windows, one more than the limit of the runner. |
| 732 | `                      ("a window of 3600001 ms", text.replace(line, re.sub(r" (\d+) \d+ closed", r" \1 3600001 closed", line))),` | Fourth: a window length of 3600001 ms, 1 ms above the limit of the runner. |
| 733 | `                      ("bins 2", text.replace(line, line[:-1] + "2"))):` | Fifth and last: the last field, `bins`, is 2. So the loop has five plans. |
| 734 | `        p = os.path.join(d, "bad.plan")` | `p`: the path of the damaged plan file. |
| 735 | `        with open(p, "w") as f:` | Opens it for writing. |
| 736 | `            f.write(bad)` | Writes the damaged text. |
| 737 | `        r = subprocess.run([binary] + args + [p], env=env, capture_output=True, text=True)` | Runs the stand-in with the damaged plan. |
| 738 | `        check("bwx8 refuses a plan with %s (status 2)" % name, bad != text and r.returncode == 2, (r.returncode, r.stderr))` | Check, once per defect: the damaged text differs from the good one, and `bwx8` ends with exit status 2. So the runner checks its plan and does not run a plan with a defect. |
| 739 | `    row = open(os.path.join(d, "sched10", "s1", "YP.tsv")).read().split("\n")[1].split("\t")` | `row`: the first data row of the `YP` schedule of session 1, split at the tabs. |
| 740 | `    r = subprocess.run([binary] + row[5].split(), cwd=d, env=env, capture_output=True, text=True)` | Runs the stand-in `bwx8` with the options of that row, in the folder `d`. |
| 741 | `    check("the old bwx8 refuses the args of a YP process (--rec-pad or --hot-copy): a wrong .bin word cannot run such a step",` | Starts a check: the older runner `bwx8` refuses the options of a `YP` process, which hold `--rec-pad` or `--hot-copy`. |
| 742 | `          r.returncode != 0 and ("--rec-pad" in row[5] or "--hot-copy" in row[5]), (r.returncode, r.stderr[-200:]))` | The test: the exit status is not 0, and the options really hold one of the two new options. So a step that needs a new option cannot run by mistake with the older runner when its `.bin` file holds the wrong word. |

### `bwx10_checks`: the plans of the other four steps through a stand-in `bwx10` (lines 745 to 784)

| Line | Source | Explanation |
|---:|---|---|
| 745 | `def bwx10_checks(tmp, sched):` | Starts the function `bwx10_checks`: the checks with a stand-in of the runner `bwx10`. `sched` is the generated folder with the test divisor 100. |
| 746 | `    src = os.path.join(Y, "bwx10.c")` | `src`: the path of the runner source `bwx10.c` in the folder of this file. |
| 747 | `    if "--no-bwx10" in sys.argv[1:]:` | When the option `--no-bwx10` was given. |
| 748 | `        print("SKIP  the run of the plans of YA, YP, YF and YC through a local stand-in bwx10 (--no-bwx10)")` | Prints a `SKIP` line for this part, with the option as the reason. |
| 749 | `        return` | Leaves the function. |
| 750 | `    if not os.path.exists(src):` | When the source file is not in the folder. |
| 751 | `        print("SKIP  the run of the plans of YA, YP, YF and YC through a local stand-in bwx10 (bwx10.c is not in this folder)")` | Prints a `SKIP` line with that reason. |
| 752 | `        return` | Leaves the function. |
| 753 | `    d = os.path.join(tmp, "bwx10")` | `d`: the folder `bwx10` in the temporary folder. |
| 754 | `    os.makedirs(d)` | Creates it. |
| 755 | `    binary = os.path.join(d, "bwx10")` | `binary`: the path of the stand-in binary in that folder. |
| 756 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-o", binary, src], capture_output=True, text=True)` | Runs `gcc` with the flags of `CFLAGS`, the output path and the source. The output of the compiler is kept as text. |
| 757 | `    if r.returncode != 0:` | When the compiler ended with a status other than 0. |
| 758 | `        print("SKIP  the run of the plans of YA, YP, YF and YC through a local stand-in bwx10 (bwx10.c does not build here: %s)"` | Prints a `SKIP` line that says that `bwx10.c` does not build here. A failed build is a `SKIP` here and not a failed check. |
| 759 | `              % (r.stdout + r.stderr).strip().split("\n")[0][:200])` | The value for that line: the first line of the compiler output, cut to 200 characters. |
| 760 | `        return` | Leaves the function. |
| 761 | `    alt = local_cpus()` | `alt`: the CPU that stands in for CPU 41 on this machine. |
| 762 | `    if alt is None:` | When this machine does not have the CPUs that the runs need. |
| 763 | `        return` | Leaves the function. The failed check of `local_cpus` is counted. |
| 764 | `    shutil.copytree(sched, os.path.join(d, "sched10"))` | Copies the schedule folder with the test divisor 100 to `sched10` in the folder of the binary. |
| 765 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment of this test without every variable whose name starts with `BWX_`. So no counter setting reaches the stand-in from outside. |
| 766 | `    r = subprocess.run([binary, "--list"], env=env, capture_output=True, text=True)` | Runs the stand-in with `--list`, the option that prints the names of its kernels. |
| 767 | `    check("the stand-in bwx10 lists the kernels of round 3 (asmread, read, oldread and the 5 new ones)",` | Starts a check: the stand-in `bwx10` lists the kernels of round 3. |
| 768 | `          r.returncode == 0 and set(NEW_KERNELS + ["asmread", "read", "oldread"]) <= set(r.stdout.split()), r.stdout[:300])` | The test: exit status 0, and the five new kernels, `asmread`, `read` and `oldread` are all among the printed words. So the binary under test is one that knows the new kernels. |
| 769 | `    jobs = stand_in_jobs(d, ["YA", "YP", "YF", "YC"], alt)` | `jobs`: one job per process of the four steps that use `bwx10`, in both sessions, with CPU 41 replaced. |
| 770 | `    t0 = time.time()` | `t0`: the time before the runs. |
| 771 | `    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:` | Creates a pool of 6 worker threads. |
| 772 | `        results = list(pool.map(lambda j: run_job(binary, d, env, j), jobs))` | Runs every job through `run_job` in the pool and collects the results in the order of the jobs. |
| 773 | `    per = collections.defaultdict(list)` | `per`: the results per step and session. |
| 774 | `    for job, res in zip(jobs, results):` | Starts a loop over the jobs with their results. |
| 775 | `        per[job[0], job[1]].append(res)` | Adds the result to the list of its step and session. |
| 776 | `    for (step, session), res in sorted(per.items(), key=lambda x: (x[0][1], x[0][0])):` | Starts a loop over the steps and sessions, sorted by the session and then by the step name. |
| 777 | `        bad = [x for x in res if x]` | `bad`: the results that describe a defect. |
| 778 | `        check("%s session %d (test divisor 100): the stand-in bwx10 accepts each of the %d plans with its args: status 0, one S and "` | Starts a check per step and session: the stand-in `bwx10` accepts each plan with its options. The name lists what `run_job` tested: status 0, one `S` row and one `E` row per trial. |
| 779 | `              "one E row per trial, every planned window as a W row" % (step, session, len(res)),` | Continues the name: every planned window as a `W` row. |
| 780 | `              len(res) == TABLE[step][0] and not bad, bad[:2])` | The test: the number of results is the number of processes of the step in `TABLE`, and no result describes a defect. This proves that the runner can read every plan and every command line that the generator writes for these steps. |
| 781 | `    check("all %d plans of the bwx10 steps ran through the stand-in bwx10 (%.0f s)" % (len(jobs), time.time() - t0),` | Starts a check: all plans of the steps that use `bwx10` ran through the stand-in. The name gives the number of jobs and the seconds that the runs took. |
| 782 | `          len(jobs) == 9 + 2 * (28 + 288 + 42) and all(x is None for x in results))` | The test: there are 725 jobs, the 9 of `YA` and twice the 358 of `YP`, `YF` and `YC`, and every result is `None`. |

### Texts of the dummy runner and of the stand-ins for `ps` and `ssh` (lines 785 to 816)

| Line | Source | Explanation |
|---:|---|---|
| 785 | `# ---------- run_bwx10.sh with dummy binaries ----------` | Comment: the checks of the run script `run_bwx10.sh` with dummy binaries start here. |
| 786 | `DUMMY = """#!/usr/bin/env bash` | `DUMMY`: the text of a Bash script that stands in for a runner. This line is its first line, which tells Linux to run it with `bash`. |
| 787 | `# Stand-in for @WORD@: records its process ids and its own path, checks the plan file, sleeps, ends with DUMMY_EXIT.` | Line of the dummy script: a comment. `@WORD@` is replaced later with the word of the binary. The dummy records its process ids and its own path, checks the plan file, sleeps, and ends with the status in `DUMMY_EXIT`. |
| 788 | `echo "$$ $*" >> "$DUMMY_LOG"` | Line of the dummy script: appends its process id (`$$`) and all its arguments (`$*`) to the file that `DUMMY_LOG` names. The test reads this file to see what was started, and with which options. |
| 789 | `echo "$0" >> "$DUMMY_LOG.bin"` | Line of the dummy script: appends its own path (`$0`) to the file `DUMMY_LOG` with the ending `.bin`. So the test sees which binary each launch used. |
| 790 | `grep Cpus_allowed_list /proc/$$/status >> "$DUMMY_LOG.cpus"` | Line of the dummy script: appends the line `Cpus_allowed_list` of its own status file under `/proc` to the file with the ending `.cpus`. That line is the CPU list of the process. |
| 791 | `echo "PMU=${BWX_PMU_TYPE:-} EV=${BWX_EVENTS:-}" >> "$DUMMY_LOG.env"` | Line of the dummy script: appends the values of `BWX_PMU_TYPE` and `BWX_EVENTS` in its environment to the file with the ending `.env`. |
| 792 | `while (( $# )); do if [[ $1 == --plan && ! -r $2 ]]; then echo "no plan $2" >&2; exit 7; fi; shift; done` | Line of the dummy script: a loop over its arguments. When the argument after `--plan` is not a readable file, it prints `no plan` with the path to the error output and ends with exit status 7. So a wrong plan path fails as it would in a real runner. |
| 793 | `echo "M,dummy,@WORD@"` | Line of the dummy script: prints one output row, `M,dummy,` and the word of the binary. The test finds this row in the output file of the step. |
| 794 | `sleep "${DUMMY_SLEEP:-0}" & echo "$! sleep" >> "$DUMMY_LOG"` | Line of the dummy script: starts `sleep` in the background for the seconds in `DUMMY_SLEEP`, 0 when it is not set or is empty. Then it appends the process id of the sleep and the word `sleep` to the log. |
| 795 | `wait $!` | Line of the dummy script: waits for the sleep. |
| 796 | `# DUMMY_TOUCH=1: the marker file appears when this process ends.` | Line of the dummy script: a comment. With `DUMMY_TOUCH=1` the marker file appears when this process ends. |
| 797 | `[[ -z ${DUMMY_TOUCH:-} ]] \|\| : > "$BWX8_MARKER"` | Line of the dummy script: when `DUMMY_TOUCH` is set, it creates the marker file at the path in `BWX8_MARKER`. The command `:` with `>` writes an empty file. |
| 798 | `exit "${DUMMY_EXIT:-0}"` | Line of the dummy script: ends with the exit status in `DUMMY_EXIT`, 0 when it is not set or is empty. |
| 799 | `"""` | Ends the text `DUMMY`. |
| 801 | `PS_STUB = """#!/usr/bin/env bash` | `PS_STUB`: the text of a Bash script that stands in for the tool `ps`. This line is its first line. |
| 802 | `# Stand-in for ps: its second call creates the file named by PS_TOUCH. Then it runs the real ps.` | Line of the stand-in: a comment. Its second call creates the file that `PS_TOUCH` names. Then it runs the real `ps`. |
| 803 | `# run_bwx10.sh calls ps once for env.txt and then once per launch, after the wait and before the last marker check.` | Line of the stand-in: a comment. `run_bwx10.sh` calls `ps` once for `env.txt` and then once per launch, after the wait and before the last marker check. So the second call is the moment directly before the first launch. |
| 804 | `if [[ -n ${PS_TOUCH:-} ]]; then` | Line of the stand-in: only when `PS_TOUCH` is set and not empty. |
| 805 | `  echo call >> "$PS_TOUCH.calls"` | Line of the stand-in: appends one line to a file that counts the calls. |
| 806 | `  if (( $(wc -l < "$PS_TOUCH.calls") == 2 )); then : > "$PS_TOUCH"; fi` | Line of the stand-in: when that file has 2 lines, it creates the empty file that `PS_TOUCH` names. |
| 807 | `fi` | Line of the stand-in: ends the `if`. |
| 808 | `exec %s "$@"` | Line of the stand-in: replaces itself with the real `ps` and passes all arguments on. The `%s` is filled later with the path of the real `ps`. |
| 809 | `"""` | Ends the text `PS_STUB`. |
| 811 | `SSH_STUB = """#!/bin/bash` | `SSH_STUB`: the text of a Bash script that stands in for `ssh`. This line is its first line. |
| 812 | `# Stand-in for ssh: records the remote command (its last argument). It opens no connection.` | Line of the stand-in: a comment. It records the remote command, which is its last argument. It opens no connection. |
| 813 | `printf '%s\\n' "${@: -1}" >> "$SSH_LOG"` | Line of the stand-in: appends its last argument (`${@: -1}`) and a newline to the file that `SSH_LOG` names. |
| 814 | `"""` | Ends the text `SSH_STUB`. |

### Small helpers: `cpu_list`, `utc`, `sha256`, `samplers`, `dummy` (lines 817 to 858)

| Line | Source | Explanation |
|---:|---|---|
| 817 | `def cpu_list(text):` | Starts the function `cpu_list`. It converts a line `Cpus_allowed_list` to a set of CPU numbers. |
| 818 | `    cpus = set()` | `cpus`: the result set, empty at first. |
| 819 | `    for part in text.split(":")[1].strip().split(","):` | Takes the text after the colon and starts a loop over its parts between commas. A part is one CPU or a range such as `0-5`. |
| 820 | `        a, _, b = part.partition("-")` | Splits a part at the hyphen into the first CPU `a` and the last CPU `b`. `b` is empty for a single CPU. |
| 821 | `        cpus.update(range(int(a), int(b or a) + 1))` | Adds every CPU from `a` to `b`, or `a` alone. |
| 822 | `    return cpus` | Returns the set. |
| 825 | `def utc(offset):` | Starts the function `utc`. |
| 826 | `    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))` | Returns the UTC time `offset` seconds from now, as a text of the form `2026-11-15T03:00:00Z`. |
| 829 | `def sha256(path):` | Starts the function `sha256`. |
| 830 | `    return subprocess.run(["sha256sum", path], capture_output=True, text=True).stdout.split()[0]` | Runs the tool `sha256sum` on a file and returns the first word of its output, the checksum. |
| 833 | `def samplers(path_part):` | Starts the function `samplers`. |
| 834 | `    """Process ids of running hostwatch.py processes whose command line names this path."""` | Description text: the function returns the process ids of the running `hostwatch.py` processes whose command line names the given path. |
| 835 | `    found = []` | `found`: the result list, empty at first. |
| 836 | `    for pid in os.listdir("/proc"):` | Starts a loop over the names in `/proc`. |
| 837 | `        if pid.isdigit():` | Only a name of digits, which is a process id. |
| 838 | `            try:` | Starts the block whose error is caught. |
| 839 | `                cmd = open("/proc/%s/cmdline" % pid, "rb").read().decode("utf-8", "replace")` | Reads the command line of the process from its file `cmdline`. |
| 840 | `            except OSError:` | The process has ended in the meantime. |
| 841 | `                continue` | Skips it. |
| 842 | `            if "hostwatch.py" in cmd and path_part in cmd:` | When the command line holds `hostwatch.py` and the given path. |
| 843 | `                found.append(int(pid))` | Adds the process id. |
| 844 | `    return found` | Returns the list. |
| 847 | `def dummy(folder, word):` | Starts the function `dummy`. |
| 848 | ``    """Writes the dummy binary `word` and its build record into `folder`. Returns the path of the binary."""`` | Description text: the function writes the dummy binary with the name `word` and its build record into `folder`. It returns the path of the binary. |
| 849 | `    os.makedirs(folder, exist_ok=True)` | Creates the folder when it does not exist. |
| 850 | `    path = os.path.join(folder, word)` | `path`: the path of the dummy binary. |
| 851 | `    with open(path, "w") as f:` | Opens it for writing. |
| 852 | `        f.write(DUMMY.replace("@WORD@", word))` | Writes the text `DUMMY` with `@WORD@` replaced by the word. So the dummies of different words differ in their text and in their output row. |
| 853 | `    os.chmod(path, 0o755)` | Makes the file executable. |
| 854 | `    with open(os.path.join(folder, "build.txt"), "w") as f:` | Opens the file `build.txt` in the same folder for writing. |
| 855 | `        f.write("dummy build record of %s\n" % word)` | Writes one line that names the word. The run script copies this file into the result folder, so the test can see from which folder it came. |
| 856 | `    return path` | Returns the path. |

### Class `Box`: a copy of the run script with dummies in a temporary folder (lines 859 to 951)

| Line | Source | Explanation |
|---:|---|---|
| 859 | `class Box:` | Starts the class `Box`. It is the test setup for the run script. |
| 860 | `    """A copy of run_bwx10.sh and hostwatch.py with a test schedule in a temporary folder. The dummy bwx10 is beside` | Description text: a `Box` holds a copy of `run_bwx10.sh` and of `hostwatch.py` with a test schedule in a temporary folder. The dummy `bwx10` lies beside the script, as on CRB. |
| 861 | `    the script, as on CRB. The dummy bwx8 is in its own folder with its own build record."""` | Continues the text: the dummy `bwx8` lies in a folder of its own, with a build record of its own. |
| 863 | `    def __init__(self, tmp, sched):` | Starts the constructor. `sched` is the generated folder with the test divisor 100. |
| 864 | `        self.dir = os.path.join(tmp, "box")` | `dir`: the folder `box` in the temporary folder. |
| 865 | `        os.makedirs(self.dir)` | Creates it. |
| 866 | `        shutil.copy(RUN, self.dir)` | Copies the run script into the box. The test runs this copy, so the script finds its files beside itself. |
| 867 | `        shutil.copy(WATCH, self.dir)` | Copies the host sampler into the box. |
| 868 | `        shutil.copytree(sched, os.path.join(self.dir, "sched10"))` | Copies the schedule folder into the box, with the name `sched10`. |
| 869 | `        self.bin10 = dummy(self.dir, "bwx10")` | `bin10`: a dummy with the word `bwx10`, in the box beside the script. |
| 870 | `        self.bin8 = dummy(os.path.join(tmp, "old8"), "bwx8")` | `bin8`: a dummy with the word `bwx8`, in the folder `old8`. |
| 871 | `        # A home folder with the accepted bwx8 at the path that run_bwx10.sh uses on CRB.` | Comment: the next lines make a home folder that has the accepted `bwx8` at the path that `run_bwx10.sh` uses on CRB. |
| 872 | `        self.home = os.path.join(tmp, "home")` | `home`: the folder `home` in the temporary folder. |
| 873 | `        self.home8 = dummy(os.path.join(self.home, "cache-perf", "bwx8-20261114"), "bwx8")` | `home8`: a dummy `bwx8` at `cache-perf/bwx8-20261114/bwx8` below that home folder. |
| 874 | `        os.makedirs(os.path.join(self.dir, "bin"))` | Creates the folder `bin` in the box. |
| 875 | `        stub = os.path.join(self.dir, "bin", "ps")` | `stub`: the path of the stand-in for `ps` in that folder. |
| 876 | `        with open(stub, "w") as f:` | Opens it for writing. |
| 877 | `            f.write(PS_STUB % shutil.which("ps"))` | Writes the text `PS_STUB` with the path of the real `ps` put in. `shutil.which` finds that path. |
| 878 | `        os.chmod(stub, 0o755)` | Makes the stand-in executable. |
| 879 | `        self.watch_cpu = str(sorted(os.sched_getaffinity(0))[-1])` | `watch_cpu`: the highest CPU on which this test may run, as text. It becomes the CPU of the host sampler. |
| 880 | `        self.n = 0` | `n`: the number of the last test case, 0 at first. |
| 882 | `    def sched(self, *parts):` | Starts the method `sched`. |
| 883 | `        return os.path.join(self.dir, "sched10", *parts)` | Returns a path below the folder `sched10` of the box. |
| 885 | `    def rows(self, step, session=1):` | Starts the method `rows`. |
| 886 | `        text = open(self.sched("s%d" % session, step + ".tsv")).read()` | Reads the schedule file of a step, of session 1 unless another session is given. |
| 887 | `        return [r.split("\t") for r in text.split("\n")[1:-1]]` | Returns its data rows, each split at the tabs. |
| 889 | `    def start(self, args, pre=(), **env):` | Starts the method `start`. `args`: the arguments for the run script. `pre`: words to put before the script, for example a `taskset` command. `env`: settings for its environment. |
| 890 | `        """Starts the script in fresh result, marker and log paths. Returns the process."""` | Description text: the method starts the script with new paths for the results, the marker file and the log. It returns the process. |
| 891 | `        self.n += 1` | Counts the test case. |
| 892 | `        self.case = os.path.join(self.dir, "case%d" % self.n)` | `case`: a folder of its own for this case, `case` plus the number. |
| 893 | `        os.makedirs(self.case)` | Creates it. |
| 894 | `        self.results = os.path.join(self.case, "results")` | `results`: the place for the result folders of this case. |
| 895 | `        self.marker = os.path.join(self.case, "RUNNING")` | `marker`: the path that takes the place of the marker file in this case. |
| 896 | `        self.stopfile = os.path.join(self.case, "STOP")` | `stopfile`: the path that takes the place of the stop file. |
| 897 | `        self.log = os.path.join(self.case, "dummy.log")` | `log`: the log file of the dummies. |
| 898 | `        e = {k: v for k, v in os.environ.items()` | `e`: the environment for the script. It starts as a copy of the environment of the test without the settings that the script reads. |
| 899 | `             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED", "BWX8_SHA256", "BWX10_SHA256",` | The names that are left out: `STOP_AT`, `SESSION`, `SESSION1_END`, `RESERVE`, the internal mark `_PINNED`, and the two digest settings. |
| 900 | `                          "BWX_PMU_TYPE", "BWX_EVENTS", "WATCH_CPU")}` | More names that are left out: the two counter settings and `WATCH_CPU`. So nothing from the shell of the developer changes a test case. |
| 901 | `        e.update(HOME=self.case, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_BIN=self.bin8, BWX10_BIN=self.bin10,` | Adds the settings of the case: the case folder as `HOME`, the test paths of the marker file and of the stop file, and the dummies for the words `bwx8` and `bwx10`. |
| 902 | `                 BWX8_RESULTS=self.results, DUMMY_LOG=self.log, WATCH_CPU=self.watch_cpu)` | Continues the settings: the place of the result folders, the log of the dummies, and the CPU of the host sampler. With these test settings the script never touches the real marker file or a real binary. |
| 903 | `        e.update(env)` | Adds the settings that the caller gave. They replace the defaults of the case. |
| 904 | `        e = {k: v for k, v in e.items() if v is not None}      # None: leave this setting out` | Removes every setting whose value is `None`. So a caller can take a default away. |
| 905 | `        return subprocess.Popen(list(pre) + [os.path.join(self.dir, "run_bwx10.sh")] + args, env=e, text=True,` | Starts the copy of `run_bwx10.sh` in the box as a new process, with the words of `pre` before it and the arguments after it. |
| 906 | `                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)` | Continues the call: the environment `e`, text mode, and pipes for the output and the error output. `start_new_session=True` gives the script a session of its own, so a signal of the test reaches only it. |
| 908 | `    def run(self, args, pre=(), **env):` | Starts the method `run`: start the script and wait for its end. |
| 909 | `        p = self.start(args, pre, **env)` | Starts the script. |
| 910 | `        out, err = p.communicate(timeout=900)` | Waits for its end, at most 900 s, and reads its output and its error output. |
| 911 | `        return p.returncode, out, err` | Returns the exit status, the output and the error output. |
| 913 | `    def folders(self):` | Starts the method `folders`. |
| 914 | `        return sorted(os.path.join(self.results, d) for d in os.listdir(self.results)) if os.path.isdir(self.results) else []` | Returns the sorted paths of the result folders of the case, or an empty list when the script made none. |
| 916 | `    def folder(self):` | Starts the method `folder`. |
| 917 | `        d = self.folders()` | `d`: the result folders of the case. |
| 918 | `        return d[0] if len(d) == 1 else None` | Returns the folder when there is exactly one, and `None` if not. |
| 920 | `    def file(self, name):` | Starts the method `file`. It reads one file of the result folder. |
| 921 | `        f = self.folder()` | `f`: the result folder, or `None`. |
| 922 | `        path = os.path.join(f, name) if f else ""` | `path`: the path of the file, or an empty text without a folder. |
| 923 | `        return open(path).read() if os.path.exists(path) else ""` | Returns the content of the file, or an empty text when the file does not exist. |
| 925 | `    def csv(self, step):` | Starts the method `csv`. |
| 926 | `        return self.file(step + ".csv")` | Returns the content of the output file `<STEP>.csv` of a step. |
| 928 | `    def launched(self):` | Starts the method `launched`. |
| 929 | `        return [l for l in open(self.log).read().split("\n") if l] if os.path.exists(self.log) else []` | Returns the lines of the dummy log that are not empty. Each launch gives two lines: the line of the dummy with its process id and options, and the line of its sleep. |
| 931 | `    def binaries(self):` | Starts the method `binaries`. |
| 932 | `        """The path of the dummy of each launch, in order."""` | Description text: the method returns the path of the dummy of each launch, in order. |
| 933 | `        return open(self.log + ".bin").read().split("\n")[:-1] if os.path.exists(self.log + ".bin") else []` | Reads the file with the ending `.bin` that the dummies wrote. Without that file the result is an empty list. |
| 935 | `    def wait_launch(self):` | Starts the method `wait_launch`. It waits until a dummy has started its sleep. |
| 936 | `        end = time.time() + 90` | `end`: 90 s from now. |
| 937 | `        while time.time() < end and len(self.launched()) < 2:` | Loops until the time is over or the log has at least 2 lines. |
| 938 | `            time.sleep(0.2)` | Waits 0.2 s per turn. |
| 939 | `        return len(self.launched()) >= 2` | Returns whether the log has at least 2 lines. |
| 941 | `    def none_alive(self):` | Starts the method `none_alive`. It tests that the script left no process behind. |
| 942 | `        time.sleep(0.5)` | Waits 0.5 s first. |
| 943 | `        for l in self.launched():` | Starts a loop over the lines of the dummy log. Each starts with a process id, of a dummy or of its sleep. |
| 944 | `            try:` | Starts the block whose error is caught. |
| 945 | `                os.kill(int(l.split()[0]), 0)` | `os.kill` with the signal 0 sends nothing. It only tests whether the process exists. |
| 946 | `                return False` | The process exists: returns false. |
| 947 | `            except OSError:` | The process does not exist. |
| 948 | `                pass` | Goes on with the next line. |
| 949 | `        return not samplers(self.case)` | Returns true when also no host sampler of this case is running. |

### `visit_checks`: the visit script with a stand-in for `ssh` (lines 952 to 1005)

| Line | Source | Explanation |
|---:|---|---|
| 952 | `def visit_checks(tmp):` | Starts the function `visit_checks`: the checks of the visit script. |
| 953 | `    """visit10.sh with a stand-in ssh. PATH holds only the stand-in and date, so no real ssh can start."""` | Description text: the checks run `visit10.sh` with a stand-in for `ssh`. The search path holds only the stand-in and `date`. So no real `ssh` can start, and the test never contacts CRB. |
| 954 | `    d = os.path.join(tmp, "visit")` | `d`: the folder `visit` in the temporary folder. |
| 955 | `    os.makedirs(os.path.join(d, "bin"))` | Creates it with a folder `bin` inside. |
| 956 | `    text, n = re.subn(r"(?m)^N=.*$", "N=" + d, open(VISIT).read())` | Reads the visit script and replaces its line that starts with `N=`, the log folder, with a line that names `d`. `(?m)` lets `^` and `$` match at the start and the end of every line. `n` is the number of lines replaced. |
| 957 | `    copy_path = os.path.join(d, "visit10.sh")` | `copy_path`: the path of the changed copy of the visit script. |
| 958 | `    with open(copy_path, "w") as f:` | Opens the copy for writing. |
| 959 | `        f.write(text)` | Writes the changed text. |
| 960 | `    with open(os.path.join(d, "bin", "ssh"), "w") as f:` | Opens the file `ssh` in the folder `bin` for writing. |
| 961 | `        f.write(SSH_STUB)` | Writes the stand-in text `SSH_STUB`. |
| 962 | `    os.chmod(os.path.join(d, "bin", "ssh"), 0o755)` | Makes the stand-in executable. |
| 963 | `    os.symlink(shutil.which("date"), os.path.join(d, "bin", "date"))` | Puts a link to the real tool `date` into the folder `bin`. The visit script needs `date` for its status line. |
| 964 | `    log = os.path.join(d, "ssh.log")` | `log`: the file in which the stand-in records each remote command. |
| 966 | `    def visit(name, **env):` | Starts the inner function `visit`. It runs the copy once, with a log name and with settings. |
| 967 | `        if os.path.exists(log):` | When a record of an earlier call exists. |
| 968 | `            os.remove(log)` | Removes it. |
| 969 | `        e = {"PATH": os.path.join(d, "bin"), "SSH_LOG": log, "HOME": d}` | `e`: the whole environment of the script: a search path with only the folder `bin`, the record file for the stand-in, and `d` as the home folder. |
| 970 | `        e.update(env)` | Adds the settings of the caller. |
| 971 | `        r = subprocess.run([shutil.which("bash"), copy_path, name, "YA", "YL"], env=e, capture_output=True, text=True)` | Runs the copy with `bash`. The arguments are the log name and the two steps `YA` and `YL`. |
| 972 | `        return r.returncode, open(log).read() if os.path.exists(log) else None, r.stderr` | Returns the exit status, the recorded remote command (`None` when the stand-in was never called), and the error output. |
| 974 | `    rc, cmd, err = visit("ok", STOP_AT="2026-11-15T15:00Z", SESSION="2", SESSION1_END="2026-11-15T03:00Z",` | Runs the copy with a full set of valid settings: a stop time, session 2, the end of session 1. |
| 975 | `                         BWX8_SHA256="0a1b", BWX10_SHA256="2c3d", ENVV="RESERVE=90")` | Continues the settings: two digests and `ENVV` with `RESERVE=90`. |
| 976 | `    check("visit10.sh: one login; the marker check is the first remote action, then run_bwx10.sh in ~/cache-perf/bwx10-20261115 "` | Starts a check of the normal case: one login. The marker check is the first remote action. Then comes `run_bwx10.sh` in the folder `~/cache-perf/bwx10-20261115`, with both digests. |
| 977 | `          "with both digests",` | Continues the name of the check. |
| 978 | `          n == 1 and rc == 0 and cmd is not None and cmd.count("\n") == 1` | The test, first conditions: exactly one `N=` line was replaced, the exit status is 0, the stand-in was called, and its record has exactly one line. One line means one login. |
| 979 | `          and cmd.startswith("if [ -e /tmp/positron-perf.RUNNING ]; then ")` | Continues: the remote command starts with the test for the marker file `/tmp/positron-perf.RUNNING`. So nothing can start on CRB before the marker file was tested. |
| 980 | `          and cmd.endswith("exit 3; fi; cd ~/cache-perf/bwx10-20261115 && STOP_AT=2026-11-15T15:00Z SESSION=2 "` | Continues: the remote command ends with this exact text: the end of the marker check with `exit 3`, then `cd` to the folder of round 3, then the settings in a fixed order. |
| 981 | `                           "SESSION1_END=2026-11-15T03:00Z BWX8_SHA256=0a1b BWX10_SHA256=2c3d RESERVE=90 ./run_bwx10.sh YA YL\n")` | Ends the expected text: the end of session 1, the two digests, `RESERVE=90` from `ENVV`, and the script `./run_bwx10.sh` with the two steps. This proves that every setting of the caller reaches the run script unchanged. |
| 982 | `          and open(os.path.join(d, "ok.log")).read().startswith("ssh status 0 utc "), (rc, cmd, err))` | Last condition: the log file `ok.log` starts with `ssh status 0 utc`. So the visit script wrote the status of `ssh` to its log. |
| 983 | `    rc, cmd, err = visit("plain", STOP_AT="none", SESSION="1")` | Runs the copy with the two required settings only. |
| 984 | `    check("visit10.sh without digests and SESSION1_END: the three settings are passed empty",` | Starts a check: without digests and without `SESSION1_END`, these three settings are passed as empty values. |
| 985 | `          rc == 0 and cmd is not None and cmd.endswith("STOP_AT=none SESSION=1 SESSION1_END= BWX8_SHA256= BWX10_SHA256=  ./run_bwx10.sh YA YL\n"),` | The test: exit status 0, the stand-in was called, and the remote command ends with the three names, each followed by nothing, and the script with the steps. An empty value tells the run script that the setting is not given. |
| 986 | `          (rc, cmd, err))` | The detail for a failure of the check. |
| 987 | `    ok = {"STOP_AT": "2026-11-15T15:00Z", "SESSION": "2", "SESSION1_END": "2026-11-15T03:00Z", "BWX8_SHA256": "0a1b", "BWX10_SHA256": "2c3d"}` | `ok`: a full set of valid settings, as a base for the next checks. |
| 988 | `    for var, value in (("SESSION1_END", "2026-11-15 03:00"), ("STOP_AT", "2026-11-15 15:00"),` | Starts a loop over bad values, each for one setting. This line: two times that hold a blank. |
| 989 | `                       ("STOP_AT", "none;id"), ("SESSION", "1$(id)"), ("BWX8_SHA256", "0a1b\|x"), ("BWX10_SHA256", "2c3d x"),` | Continues the list: a value with a semicolon and a command, a value with a command substitution, a value with a vertical bar, and a value with a blank. |
| 990 | `                       ("BWX10_SHA256", "2c3d;id")):` | Ends the list with one more bad digest: a value with a semicolon and a command. |
| 991 | `        rc, cmd, err = visit("bad", **dict(ok, **{var: value}))` | Runs the copy with the valid set in which this one setting has the bad value. |
| 992 | `        check("visit10.sh: %s='%s' is refused with status 2 before the login, no log file" % (var, value),` | Starts a check per bad value: the visit script refuses it with exit status 2 before the login and writes no log file. |
| 993 | `              rc == 2 and cmd is None and var in err and not os.path.exists(os.path.join(d, "bad.log")), (rc, cmd, err))` | The test: exit status 2, the stand-in was never called, the error output names the setting, and no file `bad.log` exists. This matters: such a value would become a part of the command line on CRB and could run another command there. |
| 994 | `    rc, cmd, err = visit("nostop", SESSION="1")` | Runs the copy without `STOP_AT`. |
| 995 | `    check("visit10.sh: STOP_AT not set: no login", rc != 0 and cmd is None, (rc, cmd, err))` | Check: without `STOP_AT` the script ends with a status other than 0, and the stand-in is never called. So no visit starts without a decision about the stop time. |
| 996 | `    a, b = open(os.path.join(X, "visit9.sh")).read().split("\n"), open(VISIT).read().split("\n")` | `a` and `b`: the lines of `visit9.sh`, the visit script of round 2, and of `visit10.sh`. |
| 997 | `    back = [l.replace("./run_bwx10.sh", "./run_bwx9.sh").replace("bwx10-20261115", "bwx8-20261114")` | `back`: the code lines of `visit10.sh` with the names of round 3 written back to those of round 2: the run script and the folder on CRB. |
| 998 | `            .replace(" BWX10_SHA256=${BWX10_SHA256:-}", "").replace(" BWX10_SHA256;", ";") for l in b if not l.startswith("#")]` | Continues: the setting `BWX10_SHA256` is removed from the remote command and from the list of checked names. Comment lines are left out. |
| 999 | `    check("visit10.sh differs from visit9.sh only in comment lines, the folder on CRB, the script that it starts and BWX10_SHA256",` | Starts a check: `visit10.sh` differs from `visit9.sh` only in comment lines, in the folder on CRB, in the script that it starts and in `BWX10_SHA256`. |
| 1000 | `          [l for l in a if not l.startswith("#")] == back, [x for x in back if x not in a][:2])` | The test: the code lines of `visit9.sh` are equal to `back`. So the visit script of round 3 has no other change to the script that was used before. |
| 1001 | `    check("visit10.sh names one host only, the CRB login of the handoff, and starts ssh once",` | Starts a check: `visit10.sh` names one host only, and it starts `ssh` once. |
| 1002 | `          re.findall(r"\b\d+\.\d+\.\d+\.\d+\b", open(VISIT).read()) == ["192.168.2.45"]` | The test, first half: the only text of the form of an IP address in the script is `192.168.2.45`, the address of CRB. The pattern finds four numbers with dots between them. |
| 1003 | `          and len(re.findall(r"(?m)^ssh ", open(VISIT).read())) == 1 and "scp" not in open(VISIT).read())` | Second half: exactly one line of the script starts with `ssh` and a blank, and the script does not hold the text `scp`. So the script cannot log in to another machine and cannot copy files. |

### `run_checks`: syntax, the copied stop controls, step names and the dry run (lines 1006 to 1055)

| Line | Source | Explanation |
|---:|---|---|
| 1006 | `def run_checks(tmp, sched):` | Starts the function `run_checks`: the checks of the run script. `sched` is the generated folder with the test divisor 100. |
| 1007 | `    for f in ("run_bwx10.sh", "visit10.sh"):` | Starts a loop over the two shell scripts of round 3. |
| 1008 | `        r = subprocess.run(["bash", "-n", os.path.join(Y, f)], capture_output=True, text=True)` | Runs `bash -n` on the script. With `-n` the shell reads the script and reports syntax errors, and it runs no command. |
| 1009 | `        check("bash -n " + f, r.returncode == 0, r.stderr)` | Check, once per script: `bash -n` ends with status 0. So the script has no syntax error. |
| 1010 | `    # The stop controls and the launch function are the text of run_bwx9.sh.` | Comment: the stop controls and the launch function are the text of `run_bwx9.sh`. |
| 1011 | `    part = re.compile(r"(?s)\n# ---- stop controls[^\n]*\n(.*?\n)# ---- end of the copied part ----\n")` | `part`: a pattern that cuts the copied part out of a run script. It finds the comment line that starts with `# ---- stop controls`. Its group holds all lines after it, up to the line `# ---- end of the copied part ----`. `(?s)` lets a dot match a newline too. |
| 1012 | `    old, new = part.search(open(os.path.join(X, "run_bwx9.sh")).read()), part.search(open(RUN).read())` | `old`, `new`: the result of the search in `run_bwx9.sh` and in the run script under test. |
| 1013 | `    check("run_bwx10.sh keeps the stop controls and the launch function of run_bwx9.sh unchanged (54 lines: why_stop, "` | Starts a check: `run_bwx10.sh` keeps the stop controls and the launch function of `run_bwx9.sh` unchanged. The name gives the size, 54 lines. |
| 1014 | `          "check_marker, check_deadline, the trap, settle, one, stop_child, stop_watch)",` | Continues the name with the functions of that part: `why_stop`, `check_marker`, `check_deadline`, the trap, `settle`, `one`, `stop_child` and `stop_watch`. |
| 1015 | `          old is not None and new is not None and old.group(1) == new.group(1) and old.group(1).count("\n") == 54` | The test, first half: the part was found in both scripts, the two texts are equal, and the part has 54 lines. |
| 1016 | `          and all(w in new.group(1) for w in ("why_stop()", "check_marker()", "check_deadline()", "trap '", "settle()", "one()")),` | Continues: the part holds the definitions of the five functions and the `trap` line. This proves that the stop controls of this run script are the text that the older run script used. A change there could make the script miss the marker file or a stop time. |
| 1017 | `          old and old.group(1).count("\n"))` | The detail for a failure: the number of lines found. |
| 1018 | `    box = Box(tmp, sched)` | `box`: a new test setup with a copy of the run script, the dummies and the schedule with the test divisor 100. |
| 1019 | `    absent = os.path.join(box.dir, "absent")` | `absent`: a path in the box at which no file exists. |
| 1021 | `    # ---- steps and the dry run ----` | Comment: the checks of the step names and of the dry run start here. |
| 1022 | `    for name in ("S2", "XW", "Yl", "Y", "Y-1", "YL;id"):` | Starts a loop over six names that are not valid step names of round 3: step names of older rounds, a lower-case letter, the letter `Y` alone, a hyphen, and a name with a semicolon and a command. |
| 1023 | `        rc, out, err = box.run(["--dry-run", name], SESSION="1")` | Runs the script in a dry run with that name. |
| 1024 | `        check("step name '%s' is refused with status 2" % name, rc == 2 and "unknown step" in err and not out, (rc, err))` | Check, once per name: exit status 2, the message `unknown step` in the error output, and no output. So only a name of the right form can select a schedule, and a name cannot hold a shell command that would run. |
| 1025 | `    rc, out, err = box.run(["--dry-run", "YZ9"], SESSION="1")` | Runs a dry run with `YZ9`, a name of the right form for which no schedule exists. |
| 1026 | `    check("a name of the right form without a schedule: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))` | Check: exit status 2 and the message `missing schedule`. |
| 1027 | `    rc, out, err = box.run(["--dry-run", "YF", "YF"], SESSION="1")` | Runs a dry run that names `YF` twice. |
| 1028 | `    check("a step named twice: status 2", rc == 2 and "twice" in err and "step YF" not in out, (rc, err))` | Check: exit status 2, the word `twice` in the error output, and no summary of `YF` in the output. So one call cannot run the processes of a step a second time. |
| 1029 | `    rc, out, err = box.run(["--dry-run", "YA", "YL", "YP", "YF", "YC"], SESSION="1", BWX8_BIN=absent, BWX10_BIN=absent)` | Runs a dry run of all 5 steps of session 1. The two binary paths point to a file that does not exist. |
| 1030 | `    want = {"YA": "9 processes, nominal kernel work 0.117 s", "YL": "32 processes, nominal kernel work 9.600 s",` | `want`: the summary text that the dry run must print per step. The schedule has the test divisor 100, so `YA` has 0.117 s and `YL` 9.600 s of nominal kernel work. |
| 1031 | `            "YP": "28 processes, nominal kernel work 8.400 s", "YF": "288 processes, nominal kernel work 27.648 s",` | Continues: `YP` with 8.400 s and `YF` with 27.648 s. |
| 1032 | `            "YC": "42 processes, nominal kernel work 2.520 s"}` | Ends the dictionary: `YC` with 2.520 s. Each value is the real value of the task divided by 100. |
| 1033 | `    check("--dry-run of all 5 steps, session 1, without the binaries and without counter settings: status 0, the counts of each step "` | Starts a check: a dry run of all steps of session 1 works without the binaries and without counter settings. |
| 1034 | `          "(9, 32, 28, 288, 42)",` | Continues the name: the process counts 9, 32, 28, 288 and 42. |
| 1035 | `          rc == 0 and all(("step %s session 1: %s" % kv) in out for kv in want.items())` | The test, first half: exit status 0, and the output holds the expected summary text of every step. So the script adds up the same counts and the same nominal work as the generator. |
| 1036 | `          and out.count("\nbwx8 --trial ") == 32 and out.count("\nbwx10 --trial ") == 367 and "warning" in err, (rc, out[:300], err[-300:]))` | Second half: the output has 32 command lines that start with `bwx8 --trial`, the processes of `YL`, and 367 that start with `bwx10 --trial`. The error output holds a warning about the test settings. |
| 1037 | `    check("--dry-run: the command lines are the binary word of the step and the args column",` | Starts a check: the command lines of the dry run are the word of the binary and the `args` column. |
| 1038 | `          all(("%s %s  # idx %s, tag %s, nominal " % (TABLE[st][3], r[5], r[0], r[1])) in out` | The test, first half: for every schedule row of every step the output holds the line made of the word of the binary of the step, the `args` of the row, and the comment with the `idx` and the tag. |
| 1039 | `              for st in want for r in box.rows(st)) and out.count(" --pmu-type 11 --events ") == 42` | The loop of that test. Then: the option pair `--pmu-type 11 --events` occurs 42 times, once per process of `YC`. |
| 1040 | `          and out.count(" --rec-pad ") == 25 and out.count(" --hot-copy") == 5 and out.count(" --trace") == 9)` | Ends the test: `--rec-pad` occurs 25 times (24 in `YP` and 1 in `YA`), `--hot-copy` 5 times (4 in `YP` and 1 in `YA`) and `--trace` 9 times (`YA`). So a person can read the exact commands of a session before it runs. |
| 1041 | `    check("--dry-run: the binary of each step is printed (YL bwx8, the others bwx10)",` | Starts a check: the dry run prints the binary of each step. |
| 1042 | `          sorted(re.findall(r"^step (\S+) binary: (\S+)$", out, re.M)) == sorted((st, TABLE[st][3]) for st in TABLE), out[:500])` | The test: the lines of the form `step NAME binary: WORD` give the word of `TABLE` for each of the 5 steps: `bwx8` for `YL` and `bwx10` for the others. The two groups of the pattern hold the step name and the word. |
| 1043 | `    check("--dry-run: no host sampler is announced", "host sampler" not in out)` | Check: the output of the dry run does not hold the words `host sampler`. No step of the schedule has a `.watch` file. |
| 1044 | `    check("--dry-run: starts nothing and makes no result folder", not box.launched() and not os.path.exists(box.results))` | Check: the dry run started no dummy and made no result folder. |
| 1045 | `    rc, out, err = box.run(["--dry-run", "YL", "YP", "YF", "YC"], SESSION="2")` | Runs a dry run of the four steps of session 2. |
| 1046 | `    check("--dry-run session 2: the first command line of each step uses CPU 41",` | Starts a check: in session 2 the first command line of each step uses CPU 41. |
| 1047 | `          rc == 0 and len(re.findall(r"# ---- step \S+ session 2 ----\n.*\n.*\n.*\nbwx(?:8\|10) --trial --cpus 41 ", out)) == 4, (rc, out[:500]))` | The test: exit status 0, and a pattern matches 4 times. The pattern is the heading line of a step for session 2, three more lines, and then a command line that starts with `bwx8` or `bwx10` and `--trial --cpus 41`. So the script reads the schedules of the session that `SESSION` names, with the reversed CPU order. |
| 1048 | `    rc, out, err = box.run(["--dry-run", "YA"], SESSION="2")` | Runs a dry run of `YA` for session 2. |
| 1049 | `    check("YA in session 2: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))` | Check: exit status 2 and `missing schedule`. The acceptance step exists in session 1 only. |
| 1050 | `    rc, out, err = box.run(["--dry-run", "YF"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX10_BIN=None,` | Runs a dry run of `YF` with every test variable taken out of the environment. |
| 1051 | `                           BWX8_RESULTS=None)` | Continues the call. |
| 1052 | `    check("no warning without the test settings", rc == 0 and "warning" not in err, err)` | Check: exit status 0 and no warning. The warnings appear only for test settings. |
| 1053 | `    rc, out, err = box.run(["--dry-run", "YF"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX8_RESULTS=None)` | Runs the same dry run with `BWX10_BIN` left in the environment. |
| 1054 | `    check("BWX10_BIN alone gives its warning", rc == 0 and err.count("warning") == 1 and "BWX10_BIN" in err, err)` | Check: exactly one warning, and it names `BWX10_BIN`. So a test path for the new binary cannot be used on CRB without a visible warning. |

### `run_checks`: a normal run of step `YA` (lines 1056 to 1086)

| Line | Source | Explanation |
|---:|---|---|
| 1056 | `    # ---- a normal run of a bwx10 step: YA ----` | Comment: a normal run of a step that uses `bwx10`, the step `YA`. |
| 1057 | `    rows = box.rows("YA")` | `rows`: the schedule rows of `YA`. |
| 1058 | `    rc, out, err = box.run(["YA"], SESSION="1", STOP_AT="none")` | Runs the script for real: the step `YA`, session 1, no stop time. The binaries are the dummies. |
| 1059 | `    f = box.folder()` | `f`: the one result folder of the case. |
| 1060 | `    csv = box.csv("YA")` | `csv`: the content of the output file `YA.csv`. |
| 1061 | `    heads = re.findall(r"^-- step YA session 1 idx (\d+) tag (\S+) waited_s \d+ loadavg .* logins \d+ utc \S+ args (.*)$", csv, re.M)` | `heads`: the header lines of the processes in that file. The pattern matches a line that starts with `-- step YA session 1 idx`. Its three groups hold the `idx`, the tag and the text after `args`. |
| 1062 | `    check("YA normal end: status 0, the counts are printed before the result folder is made",` | Starts a check of the normal end: exit status 0, and the counts are printed before the result folder is made. |
| 1063 | `          rc == 0 and 0 <= out.find("step YA session 1: 9 processes") < out.find("result folder: "), (rc, err, out))` | The test: the summary line of the step stands in the output before the line `result folder:`. The design asks that the runner print the counts before execution. |
| 1064 | `    check("YA normal end: folder name bwx10-YA-s1-<UTC> and its six files, no sampler file",` | Starts a check: the name of the result folder and its files. |
| 1065 | `          f is not None and re.match(r"^bwx10-YA-s1-\d{8}T\d{6}Z$", os.path.basename(f)) is not None` | The test: the folder name is `bwx10-YA-s1-`, 8 digits, `T`, 6 digits and `Z`. |
| 1066 | `          and sorted(os.listdir(f)) == ["YA.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv", "stderr.txt"],` | Continues: the folder holds exactly six files: the output file, `build.txt`, `env.txt`, `launches.txt`, `schedule.tsv` and `stderr.txt`. There is no file of the host sampler. |
| 1067 | `          f and os.listdir(f))` | The detail for a failure: the folder and its files. |
| 1068 | `    check("YA normal end: one header line per process in schedule order, each followed by its output; schedule.tsv is a copy",` | Starts a check: one header line per process in schedule order, each followed by its output, and `schedule.tsv` is a copy. |
| 1069 | `          heads == [(r[0], r[1], r[5]) for r in rows] and csv.count("M,dummy,bwx10\n") == 9 and "-- killed" not in csv` | The test: the header lines give the `idx`, the tag and the `args` of the schedule rows, in order. The output row of the dummy `bwx10` occurs 9 times. No line says `-- killed`. |
| 1070 | `          and "-- failed" not in csv and box.file("schedule.tsv") == open(box.sched("s1", "YA.tsv")).read(), heads)` | Ends the test: no line says `-- failed`, and `schedule.tsv` is equal to the schedule file. This proves that the script runs each process once, in the order of the schedule, and keeps the schedule beside the results. |
| 1071 | `    launched = [l for l in box.launched() if not l.endswith(" sleep")]` | `launched`: the lines of the dummy log without the lines of the sleeps: one line per launch. |
| 1072 | `    check("YA normal end: the binary gets the args column (--trace, --rec-pad 80, --hot-copy), no counter setting in its environment",` | Starts a check: the binary gets the `args` column, and no counter setting is in its environment. |
| 1073 | `          [l.split(" ", 1)[1] for l in launched] == [r[5] for r in rows] and launched[1].endswith(" --trace --rec-pad 80")` | The test: the arguments of each launch are the `args` of its row. The second launch ends with `--trace --rec-pad 80`. |
| 1074 | `          and launched[2].endswith(" --trace --hot-copy") and open(box.log + ".env").read() == "PMU= EV=\n" * 9 and box.none_alive(), launched)` | Ends the test: the third launch ends with `--trace --hot-copy`, each of the 9 dummies saw empty counter settings, and no process is left after the run. So the script passes the options on unchanged and adds nothing of its own. |
| 1075 | `    check("YA normal end: every process is the binary named bwx10, and build.txt is the build record beside it",` | Starts a check: every process is the binary with the word `bwx10`, and `build.txt` is the build record beside it. |
| 1076 | `          box.binaries() == [box.bin10] * 9 and box.file("build.txt") == "dummy build record of bwx10\n", box.binaries()[:2])` | The test: all 9 launches used the dummy `bwx10`, and the copied `build.txt` is the record of that dummy. |
| 1077 | `    env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1078 | `    check("YA normal end: env.txt holds session, from, load, the word and the digests of the binary, of run_bwx10.sh, of the schedule "` | Starts a check of `env.txt`. The name lists what it must hold: the session, the `--from` value, the load, the word and the digests of the binary, of `run_bwx10.sh`, of the schedule and of the build record. |
| 1079 | `          "and of the build record, paths, end line",` | Continues the name: the paths and the end line. |
| 1080 | `          "session=1 from=0 " in env and "loadavg=" in env and "## end utc=" in env and "/run_bwx10.sh\n" in env` | The test: the session and `from=0`, a load average, the end line, and a checksum line for `run_bwx10.sh`. |
| 1081 | `          and "/sched10/s1/YA.tsv\n" in env and "host sampler" not in env and " binary=bwx10 " in env` | Continues: a checksum line for the schedule file, no line about a host sampler, and the text `binary=bwx10`. |
| 1082 | `          and ("%s  %s\n" % (sha256(box.bin10), box.bin10)) in env` | Continues: the line with the sha256 and the path of the dummy `bwx10`. The test computes the sha256 itself. |
| 1083 | `          and ("%s  %s\n" % (sha256(os.path.join(box.dir, "build.txt")), os.path.join(box.dir, "build.txt"))) in env` | Continues: the line with the sha256 and the path of its `build.txt`. |
| 1084 | `          and (" MARKER=%s STOPFILE=%s BIN=%s RESULTS=%s\n" % (box.marker, box.stopfile, box.bin10, box.results)) in env` | Continues: the paths in use, which are the test paths of this case. |
| 1085 | `          and box.file("launches.txt").count("== YA.csv idx ") == 9, env)` | Ends the test: `launches.txt` holds 9 load records, one per launch. This proves that a result folder records which files ran, with which settings, and the load before every launch. |

### `run_checks`: the binary of a step (lines 1087 to 1140)

| Line | Source | Explanation |
|---:|---|---|
| 1087 | `    # ---- the binary of a step ----` | Comment: the checks of the binary of a step start here. |
| 1088 | `    rc, out, err = box.run(["--from", "30", "YL"], SESSION="1", STOP_AT="none")` | Runs the last two processes of `YL`, the step whose `.bin` file holds `bwx8`, with `--from 30`. |
| 1089 | `    env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1090 | `    check("YL (word bwx8): the two processes are the old binary, build.txt is the record from its folder, env.txt names it",` | Starts a check: with the word `bwx8` the two processes are the older binary, `build.txt` is the record from its folder, and `env.txt` names it. |
| 1091 | `          rc == 0 and box.binaries() == [box.bin8] * 2 and box.file("build.txt") == "dummy build record of bwx8\n"` | The test: exit status 0, both launches used the dummy `bwx8`, and `build.txt` is the record of that dummy. |
| 1092 | `          and " binary=bwx8 " in env and (" BIN=%s RESULTS=" % box.bin8) in env and ("%s  %s\n" % (sha256(box.bin8), box.bin8)) in env` | Continues: `env.txt` names the word and the path of the binary, and it holds the sha256 line of that binary. |
| 1093 | `          and ("  %s\n" % os.path.join(os.path.dirname(box.bin8), "build.txt")) in env` | Continues: `env.txt` holds a checksum line for the `build.txt` of the folder of that binary. |
| 1094 | `          and os.path.basename(box.folder() or "").startswith("bwx10-YL-s1-") and box.csv("YL").count("M,dummy,bwx8\n") == 2` | Continues: the name of the result folder still starts with `bwx10-YL-s1-`. So the name of the folder does not depend on the binary. The output row of the dummy `bwx8` occurs twice in the output file. |
| 1095 | `          and "to run from idx 30: 2 processes" in out, (rc, err, box.binaries()))` | Ends the test: the output says that 2 processes run from the `idx` 30. This proves that the word in the `.bin` file selects the binary, and that the result folder shows which binary ran. |
| 1096 | `    # Both words in one call: the schedules of YL and YA are cut to their first two rows for this case.` | Comment: the next case uses both words in one call. For it the schedules of `YL` and `YA` are cut to their first two rows. |
| 1097 | `    saved = {st: open(box.sched("s1", st + ".tsv")).read() for st in ("YL", "YA")}` | `saved`: the full text of the two schedule files, kept for later. |
| 1098 | `    for st, text in saved.items():` | Starts a loop over the saved texts. |
| 1099 | `        with open(box.sched("s1", st + ".tsv"), "w") as fh:` | Opens the schedule file for writing. |
| 1100 | `            fh.write("\n".join(text.split("\n")[:3]) + "\n")` | Writes its first three lines only: the header row and two processes. |
| 1101 | `    rc, out, err = box.run(["YL", "YA"], SESSION="1", STOP_AT="none")` | Runs the two steps in one call, `YL` first. |
| 1102 | `    fl = box.folders()` | `fl`: the result folders of the case, sorted by name. |
| 1103 | `    check("one call with a bwx8 step and a bwx10 step: each step starts its own binary and copies its own build record",` | Starts a check: in one call with a `bwx8` step and a `bwx10` step, each step starts its own binary and copies its own build record. |
| 1104 | `          rc == 0 and box.binaries() == [box.bin8] * 2 + [box.bin10] * 2 and len(fl) == 2` | The test: exit status 0. The four launches used the dummy `bwx8` twice and then the dummy `bwx10` twice. There are two result folders. |
| 1105 | `          and open(os.path.join(fl[0], "build.txt")).read() == "dummy build record of bwx10\n" and "bwx10-YA-s1-" in fl[0]` | Continues: the first folder in sorted order is the one of `YA`, and it holds the build record of `bwx10`. |
| 1106 | `          and open(os.path.join(fl[1], "build.txt")).read() == "dummy build record of bwx8\n" and "bwx10-YL-s1-" in fl[1],` | Continues: the second folder is the one of `YL`, and it holds the build record of `bwx8`. |
| 1107 | `          (rc, err, box.binaries(), fl))` | The detail for a failure. |
| 1108 | `    for st, text in saved.items():` | Starts a loop over the saved texts. |
| 1109 | `        with open(box.sched("s1", st + ".tsv"), "w") as fh:` | Opens the schedule file for writing. |
| 1110 | `            fh.write(text)` | Writes the full text back. |
| 1111 | `    rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none", BWX8_BIN=None, BWX10_BIN=None, HOME=box.home)` | Runs the last process of `YL` without the two test settings for the binaries. The home folder is the prepared one. |
| 1112 | `    check("without the test settings the word bwx8 is $HOME/cache-perf/bwx8-20261114/bwx8, with the build record of that folder",` | Starts a check: without the test settings the word `bwx8` stands for the path `$HOME/cache-perf/bwx8-20261114/bwx8`, and the build record comes from that folder. |
| 1113 | `          rc == 0 and box.binaries() == [box.home8] and box.file("build.txt") == "dummy build record of bwx8\n"` | The test: exit status 0, the one launch used the binary at that path, and `build.txt` is its record. |
| 1114 | `          and (" BIN=%s RESULTS=" % box.home8) in box.file("env.txt"), (rc, err, box.binaries()))` | Ends the test: `env.txt` names that path. This proves the default path that is used on CRB. The other checks only use the test paths. |
| 1115 | `    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", BWX8_BIN=None, BWX10_BIN=None, HOME=box.home)` | Runs the last process of `YA` in the same way. |
| 1116 | `    check("without the test settings the word bwx10 is bwx10 beside run_bwx10.sh",` | Starts a check: without the test settings the word `bwx10` stands for the file `bwx10` beside the run script. |
| 1117 | `          rc == 0 and box.binaries() == [box.bin10] and (" BIN=%s RESULTS=" % box.bin10) in box.file("env.txt"), (rc, err, box.binaries()))` | The test: exit status 0, the one launch used the dummy `bwx10` in the box, and `env.txt` names that path. |
| 1118 | `    binfile = box.sched("s1", "YL.bin")` | `binfile`: the `.bin` file of `YL` in session 1 of the box. |
| 1119 | `    made = os.path.join(box.dir, "made-by-bin")` | `made`: the path of a file that must never appear. |
| 1120 | `    for what, content in (("another word", "bwx9\n"), ("two words", "bwx8 bwx10\n"), ("two lines", "bwx8\nbwx10\n"), ("nothing", ""),` | Starts a loop over six wrong contents of a `.bin` file. This line: another word, two words, two lines and an empty file. |
| 1121 | `                          ("a path", "/bin/true\n"), ("a command", "$(touch %s)\n" % made)):` | Continues the list: a path, and a command substitution that would create the file `made`. |
| 1122 | `        with open(binfile, "w") as fh:` | Opens the `.bin` file for writing. |
| 1123 | `            fh.write(content)` | Writes the wrong content. |
| 1124 | `        rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none")` | Runs the last process of `YL` for real. |
| 1125 | `        rc2, out2, err2 = box.run(["--dry-run", "YL"], SESSION="1")` | Runs a dry run of `YL` too. |
| 1126 | `        check("YL.bin with %s: status 2 in a run and in a dry run, nothing starts, no result folder" % what,` | Starts a check per content: exit status 2 in a run and in a dry run, nothing starts, and no result folder is made. |
| 1127 | `              rc == 2 and rc2 == 2 and "must hold the one word bwx8 or bwx10" in err and "must hold" in err2` | The test: both statuses are 2, and both error outputs hold the message about the one word. |
| 1128 | `              and not box.launched() and not os.path.exists(box.results) and not os.path.exists(made) and "bwx" not in out2, (rc, err, rc2))` | Ends the test: no launch and no result folder in the last case, the file `made` does not exist, and the output of the dry run names no binary. The log and the result path that are tested here belong to the last case that was started, which is the dry run. This proves that only an exact word of the list can select a program, and that the content of the file is never run as a command. |
| 1129 | `    os.remove(binfile)` | Removes the `.bin` file of `YL` in session 1. |
| 1130 | `    rc, out, err = box.run(["YA", "YL"], SESSION="1", STOP_AT="none")` | Runs `YA` and then `YL` in one call. |
| 1131 | `    check("YL.bin missing, YL second in the call: status 2 before the first process of the call",` | Starts a check: with the `.bin` file of the second step missing, the script ends with status 2 before the first process of the call. |
| 1132 | `          rc == 2 and "YL.bin (the binary of step YL)" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the error output names the missing file, no launch, and no result folder. So the script finds a missing file of a later step before it uses machine time for an earlier step. |
| 1133 | `    with open(binfile, "w") as fh:` | Opens the `.bin` file for writing. |
| 1134 | `        fh.write("bwx10\n")` | Writes the word `bwx10`. |
| 1135 | `    rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none")` | Runs the last process of `YL`. |
| 1136 | `    check("the word decides, not the step name: YL.bin with bwx10 starts the binary bwx10",` | Starts a check: the word decides, and not the step name. |
| 1137 | `          rc == 0 and box.binaries() == [box.bin10] and " binary=bwx10 " in box.file("env.txt"), (rc, err))` | The test: exit status 0, the launch used the dummy `bwx10`, and `env.txt` names the word `bwx10`. |
| 1138 | `    with open(binfile, "w") as fh:` | Opens the `.bin` file for writing. |
| 1139 | `        fh.write("bwx8\n")` | Writes the word `bwx8` back. So the later checks find `YL` with the older binary again. |

### `run_checks`: the digest checks, missing binaries and a missing build record (lines 1141 to 1181)

| Line | Source | Explanation |
|---:|---|---|
| 1141 | `    # ---- the digests ----` | Comment: the checks of the digests start here. |
| 1142 | `    d8, d10, zero = sha256(box.bin8), sha256(box.bin10), "0" * 64` | `d8`, `d10`: the sha256 of the two dummy binaries. `zero`: a text of 64 zeros, a digest that fits no file. |
| 1143 | `    check("the two dummy binaries differ, so each digest names one of them", d8 != d10)` | Check: the two dummy binaries have different digests. So each digest names exactly one of them, and a check with the digest of the other binary can fail. |
| 1144 | `    cases = [("BWX8_SHA256 wrong, a bwx8 step", ["--from", "31", "YL"], dict(BWX8_SHA256=zero), 2),` | `cases`: the list of test cases. A case is a name, the arguments, the digest settings and the expected exit status. Case 1: the digest of `bwx8` is wrong, and the call runs the last process of `YL`, a step of `bwx8`. Expected: status 2. |
| 1145 | `             ("BWX8_SHA256 wrong, a bwx10 step only (bwx8 is not used, so it is not checked)", ["--from", "8", "YA"], dict(BWX8_SHA256=zero), 0),` | Case 2: the digest of `bwx8` is wrong, and the call runs the last process of `YA`, a step of `bwx10`. Expected: status 0. A binary that the call does not use is not checked. |
| 1146 | `             ("BWX10_SHA256 wrong, a bwx10 step", ["--from", "8", "YA"], dict(BWX10_SHA256=zero), 2),` | Case 3: the digest of `bwx10` is wrong, with a step of `bwx10`. Expected: status 2. |
| 1147 | `             ("BWX10_SHA256 wrong, a bwx8 step only (bwx10 is not used, so it is not checked)", ["--from", "31", "YL"], dict(BWX10_SHA256=zero), 0),` | Case 4: the digest of `bwx10` is wrong, with a step of `bwx8` only. Expected: status 0. |
| 1148 | `             ("BWX8_SHA256 right, a bwx8 step", ["--from", "31", "YL"], dict(BWX8_SHA256=d8), 0),` | Case 5: the digest of `bwx8` is right, with a step of `bwx8`. Expected: status 0. |
| 1149 | `             ("BWX10_SHA256 right, a bwx10 step", ["--from", "8", "YA"], dict(BWX10_SHA256=d10), 0),` | Case 6: the digest of `bwx10` is right, with a step of `bwx10`. Expected: status 0. |
| 1150 | `             ("both right, a bwx8 step", ["--from", "31", "YL"], dict(BWX8_SHA256=d8, BWX10_SHA256=d10), 0),` | Case 7: both digests are right, with a step of `bwx8`. Expected: status 0. |
| 1151 | `             ("BWX8_SHA256 holds the digest of bwx10, a bwx8 step", ["--from", "31", "YL"], dict(BWX8_SHA256=d10, BWX10_SHA256=d10), 2),` | Case 8: both settings hold the digest of `bwx10`, with a step of `bwx8`. Expected: status 2. It shows that a digest is compared with the binary of its own word. |
| 1152 | `             ("BWX10_SHA256 holds the digest of bwx8, a bwx10 step", ["--from", "8", "YA"], dict(BWX8_SHA256=d8, BWX10_SHA256=d8), 2),` | Case 9: both settings hold the digest of `bwx8`, with a step of `bwx10`. Expected: status 2. |
| 1153 | `             ("BWX10_SHA256 right and BWX8_SHA256 wrong, a call with YA then YL", ["YA", "YL"], dict(BWX8_SHA256=zero, BWX10_SHA256=d10), 2),` | Case 10: the digest of `bwx10` is right and that of `bwx8` is wrong, in a call with `YA` and then `YL`. Expected: status 2. |
| 1154 | `             ("BWX8_SHA256 right and BWX10_SHA256 wrong, a call with YL then YP", ["YL", "YP"], dict(BWX8_SHA256=d8, BWX10_SHA256=zero), 2)]` | Case 11, the last one: the digest of `bwx8` is right and that of `bwx10` is wrong, in a call with `YL` and then `YP`. Expected: status 2. In each of the last two calls the wrong binary belongs to the second step. |
| 1155 | `    for name, args, env_, want_rc in cases:` | Starts the loop over the cases. |
| 1156 | `        rc, out, err = box.run(args, SESSION="1", STOP_AT="none", **env_)` | Runs the script with the arguments and the digest settings of the case. |
| 1157 | `        if want_rc:` | A case that must be refused. |
| 1158 | `            check("%s: status 2 before the first process of the call, no result folder" % name,` | Starts a check per such case: status 2 before the first process of the call, and no result folder. |
| 1159 | `                  rc == 2 and "is not the binary with the digest given for it" in err and not box.launched()` | The test: exit status 2, and the error output says that the binary is not the one with the digest given for it. |
| 1160 | `                  and not os.path.exists(box.results), (rc, err))` | Ends the test: no dummy was started, and no result folder exists. This proves that a binary other than the accepted one cannot run when its digest is given. The refusal comes before any step, also when the wrong binary belongs to a later step. |
| 1161 | `        else:` | A case that must run. |
| 1162 | `            e = box.file("env.txt")` | `e`: the content of `env.txt`. |
| 1163 | `            check("%s: runs, and env.txt records both settings" % name,` | Starts a check per such case: the process runs, and `env.txt` records both digest settings. |
| 1164 | `                  rc == 0 and len(box.launched()) == 2 and (" BWX8_SHA256=%s BWX10_SHA256=%s binary=" % (` | The test: exit status 0, one launch (two lines in the dummy log), and the settings line of `env.txt` holds the two values as they were given. |
| 1165 | `                      env_.get("BWX8_SHA256", ""), env_.get("BWX10_SHA256", ""))) in e, (rc, err))` | The values for that comparison. A setting that was not given is recorded as empty. |
| 1166 | `    rc, out, err = box.run(["--dry-run", "YL", "YA"], SESSION="1", BWX8_SHA256=zero, BWX10_SHA256=zero)` | Runs a dry run of the two steps with two wrong digests. |
| 1167 | `    check("a dry run checks no digest", rc == 0, (rc, err))` | Check: the dry run ends with status 0. A dry run checks no digest, and it does not need the binaries. |
| 1168 | `    rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none", BWX8_BIN=absent)` | Runs the last process of `YL` with the path of `bwx8` set to a file that does not exist. |
| 1169 | `    check("the binary of the step is missing (bwx8): status 2", rc == 2 and "missing" in err and "bwx8" in err and not box.launched(), (rc, err))` | Check: exit status 2, the error output holds `missing` and `bwx8`, and nothing was started. |
| 1170 | `    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", BWX8_BIN=absent)` | Runs the last process of `YA` with the path of `bwx8` set to a file that does not exist. |
| 1171 | `    check("a missing bwx8 does not stop a call that uses bwx10 only", rc == 0 and len(box.launched()) == 2, (rc, err))` | Check: the run works, with one launch. A missing `bwx8` does not stop a call that uses `bwx10` only. |
| 1172 | `    rc, out, err = box.run(["YL", "YA"], SESSION="1", STOP_AT="none", BWX10_BIN=absent)` | Runs `YL` and then `YA` with the path of `bwx10` set to a file that does not exist. |
| 1173 | `    check("the binary of the second step is missing (bwx10): status 2 before the first process of the call",` | Starts a check: the binary of the second step is missing, and the script ends with status 2 before the first process of the call. |
| 1174 | `          rc == 2 and "missing" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the word `missing` in the error output, no launch and no result folder. |
| 1175 | `    os.rename(os.path.join(os.path.dirname(box.bin8), "build.txt"), os.path.join(os.path.dirname(box.bin8), "build.moved"))` | Renames the file `build.txt` beside the dummy `bwx8`, so the build record is missing. |
| 1176 | `    rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none")` | Runs the last process of `YL`, the step that uses `bwx8`. |
| 1177 | `    rc2, out2, err2 = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none")` | Runs the last process of `YA`, the step that uses `bwx10`. |
| 1178 | `    check("build.txt missing beside bwx8: a bwx8 step stops with status 2, a bwx10 step runs",` | Starts a check: without `build.txt` beside `bwx8`, a step of `bwx8` stops with status 2, and a step of `bwx10` runs. |
| 1179 | `          rc == 2 and "build.txt" in err and rc2 == 0 and len(box.launched()) == 2, (rc, err, rc2, err2))` | The test: the first run ended with status 2 and its error output names `build.txt`. The second run ended with status 0 and started its process. So no result folder is made without the record of the build of its binary. |
| 1180 | `    os.rename(os.path.join(os.path.dirname(box.bin8), "build.moved"), os.path.join(os.path.dirname(box.bin8), "build.txt"))` | Gives the file its name back. |

### `run_checks`: the counter settings and the host sampler (lines 1182 to 1227)

| Line | Source | Explanation |
|---:|---|---|
| 1182 | `    # ---- the rule for the counter settings ----` | Comment: the checks of the rule for the counter settings start here. |
| 1183 | `    tsv = box.sched("s1", "YC.tsv")` | `tsv`: the schedule file of `YC` in session 1 of the box. |
| 1184 | `    saved_yc = open(tsv).read()` | `saved_yc`: its text, kept for later. |
| 1185 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1186 | `        fh.write(re.sub(r" --pmu-type 11 --events \S+", "", saved_yc))` | Writes the schedule without the options `--pmu-type 11` and `--events` in every row. The pattern matches the two options and the event list, which is the text up to the next blank. |
| 1187 | `    rc, out, err = box.run(["YC"], SESSION="1", STOP_AT="none")` | Runs the step `YC` with this schedule and without counter settings in the environment. |
| 1188 | `    check("a counted step without the options in args and without BWX_PMU_TYPE and BWX_EVENTS: status 2, nothing starts",` | Starts a check: a step that uses counters, without the options in the `args` and without the two environment settings, ends with status 2 and starts nothing. |
| 1189 | `          rc == 2 and "needs BWX_PMU_TYPE" in err and not box.launched() and open(tsv).read() != saved_yc, (rc, err))` | The test: exit status 2, the message that the step needs `BWX_PMU_TYPE`, no launch, and the schedule file really differs from the saved text. Without this refusal the first process of the step would start and then fail in the runner. |
| 1190 | `    rc, out, err = box.run(["YC"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11")` | Runs the same with `BWX_PMU_TYPE` only. |
| 1191 | `    check("the same with BWX_PMU_TYPE only: status 2, nothing starts", rc == 2 and "needs BWX_EVENTS" in err and not box.launched(), (rc, err))` | Check: exit status 2, the message that the step needs `BWX_EVENTS`, and no launch. Both settings are needed. |
| 1192 | `    rc, out, err = box.run(["--from", "41", "YC"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11", BWX_EVENTS="a=0x11")` | Runs the last process of `YC` with both settings in the environment. |
| 1193 | `    check("the same with both settings: runs, and the binary finds them in its environment",` | Starts a check: with both settings the process runs, and the binary finds them in its environment. |
| 1194 | `          rc == 0 and len(box.launched()) == 2 and open(box.log + ".env").read() == "PMU=11 EV=a=0x11\n", (rc, err))` | The test: exit status 0, one launch, and the dummy recorded `PMU=11` and the event text. So the script exports the two settings to the runner. |
| 1195 | `    rc, out, err = box.run(["--dry-run", "YC"], SESSION="1", BWX_PMU_TYPE="eleven", BWX_EVENTS="a=0x11")` | Runs a dry run with `BWX_PMU_TYPE` set to the word `eleven`. |
| 1196 | `    check("BWX_PMU_TYPE that is not a whole number: status 2", rc == 2 and "whole number" in err, (rc, err))` | Check: exit status 2 and the words `whole number`. The type number must hold digits only. |
| 1197 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1198 | `        fh.write(saved_yc)` | Writes the saved text back. |
| 1199 | `    rc, out, err = box.run(["--from", "41", "YC"], SESSION="1", STOP_AT="none")` | Runs the last process of `YC` as scheduled, without counter settings in the environment. |
| 1200 | `    check("YC as scheduled (options in args) needs no counter setting: runs with --pmu-type 11 and the 6 events on the command line",` | Starts a check: `YC` as scheduled, with the options in the `args`, needs no counter setting. |
| 1201 | `          rc == 0 and len(box.launched()) == 2 and box.launched()[0].endswith(" --pmu-type 11 --events " + EVENTS)` | The test: exit status 0, one launch, and the command line of the dummy ends with `--pmu-type 11 --events` and the 6 events. |
| 1202 | `          and open(box.log + ".env").read() == "PMU= EV=\n", (rc, err))` | Ends the test: the dummy saw empty counter settings in its environment. So the options of the schedule alone give the counter settings to the runner. |
| 1203 | `    rc, out, err = box.run(["--from", "287", "YF"], SESSION="1", STOP_AT="none")` | Runs the last process of `YF`, the process with the `idx` 287. |
| 1204 | `    check("an uncounted step (YF, count closed, no options in args) needs no counter setting: runs",` | Starts a check: a step without counters (`YF`, counters closed, no options in the `args`) needs no counter setting and runs. |
| 1205 | `          rc == 0 and len(box.launched()) == 2 and "--plan sched10/s1/YF/0287.plan" in box.launched()[0]` | The test: exit status 0, one launch, and the launch got the plan `0287.plan` of session 1. |
| 1206 | `          and re.findall(r"^-- step YF session 1 idx (\d+) ", box.csv("YF"), re.M) == ["287"]` | Continues: the output file holds exactly one header line, for the `idx` 287. |
| 1207 | `          and " from=287 " in box.file("env.txt") and "to run from idx 287: 1 processes" in out, (rc, err))` | Ends the test: `env.txt` records `from=287`, and the output says that 1 process runs from that `idx`. This also proves that `--from` runs the named process and no earlier one. |
| 1209 | `    # ---- the host sampler is still started by a .watch file (no schedule of round 3 has one) ----` | Comment: the host sampler is still started by a `.watch` file. No schedule of round 3 has such a file, so the test makes one. |
| 1210 | `    open(box.sched("s1", "YA.watch"), "w").close()` | Creates an empty file `YA.watch` in session 1 of the box. |
| 1211 | `    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="2")` | Runs the last process of `YA`. The dummy sleeps 2 s, so the sampler has time for samples. |
| 1212 | `    w = box.file("watch-8.txt")` | `w`: the content of the sampler file `watch-8.txt`. |
| 1213 | `    pid = box.launched()[0].split()[0] if box.launched() else "?"` | `pid`: the process id of the dummy, from the first line of the dummy log. |
| 1214 | `    check("a step with a .watch file runs with hostwatch.py: watch-8.txt names the benchmark process and the CPU of its row, "` | Starts a check: a step with a `.watch` file runs with `hostwatch.py`. The name lists what is tested: the sampler file names the benchmark process and the CPU of its row. |
| 1215 | `          "has samples and its end line; the sampler is gone",` | Continues the name: the file has samples and its end line, and the sampler is gone after the run. |
| 1216 | `          rc == 0 and w.startswith("# hostwatch v1 pid=%s cpu=2 hz=20 max_s=31\n" % pid) and "\n# end reason=" in w` | The test: exit status 0. The sampler file starts with the header of the sampler, with the process id of the dummy, CPU 2, 20 samples per second and a time limit of 31 s. The file holds an end line. The 31 s are the nominal time of the process rounded up to 1 s, plus 30 s. |
| 1217 | `          and " m.run_ns=" in w and box.none_alive() and "host sampler: hostwatch.py on CPU %s " % box.watch_cpu in out` | Continues: the file holds a value `m.run_ns` of the main thread, no process of the case is left, and the output announces the sampler on the CPU of the test. |
| 1218 | `          and re.search(r"^## host sampler: WATCH_CPU=%s Python \S+ sha256 %s$" % (box.watch_cpu, sha256(WATCH)),` | Continues: `env.txt` holds the line about the host sampler. The pattern asks for the CPU, the word `Python` with a version, and the sha256 of `hostwatch.py`, which the test computes itself. |
| 1219 | `                        box.file("env.txt"), re.M) is not None, (rc, err, w[:200]))` | Ends the test. This proves three things: the sampler is started for the right process and CPU, it writes its file, and it is stopped. |
| 1220 | `    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", WATCH_CPU="126")` | Runs the same process with `WATCH_CPU=126`. |
| 1221 | `    check("a step with a .watch file and WATCH_CPU=126: status 2, nothing starts",` | Starts a check: with a `.watch` file and the sampler CPU 126, the script ends with status 2 and starts nothing. |
| 1222 | `          rc == 2 and "WATCH_CPU must be a CPU from 0 to 119" in err and not box.launched(), (rc, err))` | The test: exit status 2, the message that the CPU must be from 0 to 119, and no launch. Our runs must not use the CPUs above 119. |
| 1223 | `    os.remove(box.sched("s1", "YA.watch"))` | Removes the file `YA.watch`. |
| 1224 | `    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", WATCH_CPU="126")` | Runs the same process again with `WATCH_CPU=126`. |
| 1225 | `    check("a step without a .watch file does not read WATCH_CPU and writes no sampler file",` | Starts a check: a step without a `.watch` file does not read `WATCH_CPU` and writes no sampler file. |
| 1226 | `          rc == 0 and len(box.launched()) == 2 and not [f for f in os.listdir(box.folder()) if f.startswith("watch")], (rc, err))` | The test: exit status 0, one launch, and no file of the result folder starts with `watch`. |

### `run_checks`: the stop controls, and `MARGIN` with the real schedules (lines 1228 to 1311)

| Line | Source | Explanation |
|---:|---|---|
| 1228 | `    # ---- stop controls, for a step of each binary ----` | Comment: the checks of the stop controls start here. They run once for a step of each binary. |
| 1229 | `    for step, word in (("YL", "bwx8"), ("YA", "bwx10")):` | Starts the loop over two steps: `YL` with `bwx8` and `YA` with `bwx10`. |
| 1230 | `        rows = box.rows(step)` | `rows`: the schedule rows of the step. |
| 1231 | `        tag = rows[0][1]` | `tag`: the tag of its first process. |
| 1232 | `        note = "%s (%s)" % (step, word)` | `note`: the step and the word, for the names of the checks. |
| 1233 | `        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step without waiting for its end. The dummy sleeps 300 s, so the first process is still running when the test acts. |
| 1234 | `        up = box.wait_launch()` | Waits until the first dummy has started its sleep. |
| 1235 | `        open(box.marker, "w").close()` | Creates the file that stands for the marker file in this case. |
| 1236 | `        out, err = p.communicate(timeout=60)` | Waits for the end of the script, at most 60 s. |
| 1237 | `        csv = box.csv(step)` | `csv`: the content of the output file of the step. |
| 1238 | `        check("%s: marker file appears during a process: status 3, '-- killed', no process left" % note,` | Starts a check: the marker file appears during a process. Expected: status 3, a `-- killed` line, and no process left. |
| 1239 | `              up and p.returncode == 3 and ("-- killed tag %s status 3" % tag) in csv` | The test: the dummy had started, the exit status is 3, and the output file holds the line `-- killed tag` with the tag of the first process and `status 3`. |
| 1240 | `              and csv.count("-- step ") == 1 and box.none_alive(), (up, p.returncode, err, csv))` | Ends the test: only one process was started, and no process of the case is left. This proves that the script ends a running benchmark when the marker file appears, and that it leaves nothing running. The test does not measure how fast the stop is: it waits up to 60 s for the end of the script (line 1236). |
| 1241 | `        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", BWX8_MARKER=box.marker)` | Runs the step again. The marker path of this run is the file that the last case created, so the marker file exists from the start. |
| 1242 | `        check("%s: marker file present at the start: status 3, nothing starts, no result folder" % note,` | Starts a check: the marker file is present at the start. Expected: status 3, nothing starts, and no result folder. |
| 1243 | `              rc == 3 and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 3, no launch and no result folder. |
| 1244 | `        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step again, with a dummy that sleeps 300 s. |
| 1245 | `        up = box.wait_launch()` | Waits until the first dummy has started its sleep. |
| 1246 | `        open(box.stopfile, "w").close()` | Creates the file that stands for the stop file in this case. |
| 1247 | `        out, err = p.communicate(timeout=60)` | Waits for the end of the script. |
| 1248 | `        check("%s: stop file appears during a process: status 5, '-- killed', no process left" % note,` | Starts a check: the stop file appears during a process. Expected: status 5, a `-- killed` line, and no process left. |
| 1249 | `              up and p.returncode == 5 and ("-- killed tag %s status 5" % tag) in box.csv(step) and box.none_alive(),` | The test: the dummy had started, the exit status is 5, the output file holds the `-- killed` line with `status 5`, and no process is left. |
| 1250 | `              (up, p.returncode, err))` | The detail for a failure. |
| 1251 | `        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", BWX8_STOPFILE=box.stopfile)` | Runs the step again. The stop file path of this run is the file that the last case created. |
| 1252 | `        check("%s: stop file present at the start: status 5, nothing starts" % note, rc == 5 and not box.launched(), (rc, err))` | Check: the stop file is present at the start. The exit status is 5, and nothing starts. |
| 1253 | `        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step again, with a dummy that sleeps 300 s. |
| 1254 | `        up = box.wait_launch()` | Waits until the first dummy has started its sleep. |
| 1255 | `        os.kill(p.pid, signal.SIGTERM)` | Sends the termination signal SIGTERM to the script. |
| 1256 | `        out, err = p.communicate(timeout=60)` | Waits for the end of the script. |
| 1257 | `        csv = box.csv(step)` | `csv`: the content of the output file of the step. |
| 1258 | `        check("%s: interrupted during a process: status 130, '-- killed' marks the cut process, no process left" % note,` | Starts a check: the script is interrupted during a process. Expected: status 130, a `-- killed` line that marks the interrupted process, and no process left. |
| 1259 | `              up and p.returncode == 130 and box.none_alive()` | The test: the dummy had started, the exit status is 130, and no process of the case is left. |
| 1260 | `              and re.search(r"^-- killed tag %s status 130 utc \S+$" % re.escape(tag), csv, re.M) is not None` | Continues: the output file holds a line `-- killed tag`, the tag, `status 130 utc` and a time. With `re.escape`, no character of the tag acts as a pattern sign. |
| 1261 | `              and csv.count("-- step ") == 1, (up, p.returncode, err, csv))` | Ends the test: only one process was started. So an interrupted process is marked in the output file and cannot be read as a complete one. |
| 1262 | `        rc, out, err = box.run([step], SESSION="1", STOP_AT=utc(30))` | Runs the step with a stop time 30 s from now. |
| 1263 | `        check("%s: STOP_AT nearer than MARGIN: status 4, nothing starts" % note,` | Starts a check: `STOP_AT` is nearer than `MARGIN`. Expected: status 4, and nothing starts. |
| 1264 | `              rc == 4 and not box.launched() and "less than 91 s away" in err, (rc, err))` | The test: exit status 4, no launch, and the message `less than 91 s away`. The 91 s are the longest process of the test schedule, rounded up to 1 s, plus the 90 s of `RESERVE`. |
| 1265 | `        p = box.start([step], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")` | Starts the step with a stop time 45 s from now, `RESERVE` set to 0 and a dummy that sleeps 300 s. With a `MARGIN` of 1 s the first process may start. |
| 1266 | `        up = box.wait_launch()` | Waits until the first dummy has started its sleep. |
| 1267 | `        out, err = p.communicate(timeout=120)` | Waits for the end of the script, at most 120 s. |
| 1268 | `        check("%s: STOP_AT reached during a process: status 4, '-- killed', no process left" % note,` | Starts a check: `STOP_AT` is reached during a process. Expected: status 4, a `-- killed` line, and no process left. |
| 1269 | `              up and p.returncode == 4 and ("-- killed tag %s status 4" % tag) in box.csv(step) and box.none_alive(),` | The test: the dummy had started, the exit status is 4, the output file holds the `-- killed` line with `status 4`, and no process is left. So the stop time also ends a benchmark that is running. |
| 1270 | `              (up, p.returncode, err))` | The detail for a failure. |
| 1271 | `        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", DUMMY_EXIT="3")` | Runs the step with a dummy that ends with exit status 3. |
| 1272 | `        csv = box.csv(step)` | `csv`: the content of the output file of the step. |
| 1273 | `        check("%s: failing benchmark: status 1, '-- failed', the next process does not start" % note,` | Starts a check: a failing benchmark. Expected: status 1, a `-- failed` line, and the next process does not start. |
| 1274 | `              rc == 1 and ("-- failed tag %s exit 3" % tag) in csv and csv.count("-- step ") == 1` | The test: exit status 1, the line `-- failed tag` with the tag and `exit 3`, and only one header line in the output file. |
| 1275 | `              and box.binaries() == [box.bin8 if word == "bwx8" else box.bin10], (rc, err, csv))` | Ends the test: exactly one launch, with the binary of the word of this step. So after a failed process the script runs nothing more of the step. |
| 1276 | `    rc, out, err = box.run(["YA"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="0.3", DUMMY_TOUCH="1")` | Runs `YA` with a dummy that sleeps 0.3 s and creates the marker file when it ends. |
| 1277 | `    csv = box.csv("YA")` | `csv`: the content of the output file `YA.csv`. |
| 1278 | `    check("marker file appears between two processes: status 3, the first process ended, the second does not start",` | Starts a check: the marker file appears between two processes. Expected: status 3, the first process ended, and the second does not start. |
| 1279 | `          rc == 3 and csv.count("-- step ") == 1 and csv.count("M,dummy,bwx10\n") == 1 and "-- killed" not in csv` | The test: exit status 3, one header line, one output row of the dummy, and no `-- killed` line. |
| 1280 | `          and len(box.launched()) == 2, (rc, err, csv))` | Ends the test: the dummy log has two lines, which is one launch. This proves the check before a launch: a process that has ended is kept as complete, and no new process starts while the marker file exists. |
| 1281 | `    late = os.path.join(box.dir, "case%d" % (box.n + 1), "RUNNING")       # the marker path of the next case` | `late`: the marker path that the next case will have. The case number is known before the case starts. |
| 1282 | `    rc, out, err = box.run(["YA"], SESSION="1", STOP_AT="none", PS_TOUCH=late,` | Runs `YA` with `PS_TOUCH` set to that path. |
| 1283 | `                           PATH=os.path.join(box.dir, "bin") + os.pathsep + os.environ["PATH"])` | Continues the call: the folder `bin` of the box stands first in the search path. So the script calls the stand-in for `ps`, and the second call of it creates the marker file. |
| 1284 | `    check("marker file appears after the wait, directly before the launch: status 3, nothing starts",` | Starts a check: the marker file appears after the wait, directly before the launch. Expected: status 3, and nothing starts. |
| 1285 | `          late == box.marker and os.path.exists(late) and rc == 3 and not box.launched() and "-- step" not in box.csv("YA")` | The test: the path was the marker path of the case, the file exists, the exit status is 3, no dummy was started, and the output file has no header line. |
| 1286 | `          and box.file("launches.txt").count("== YA.csv idx ") == 1, (rc, err))` | Ends the test: `launches.txt` holds exactly one load record. So the stop came after the load record and before the header line. This proves the second marker check of the function `one`, the one directly before the launch. |
| 1287 | `    rc, out, err = box.run(["YA"], SESSION="1")` | Runs `YA` without `STOP_AT`. |
| 1288 | `    check("STOP_AT not set: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. A real run needs a decision about the stop time. |
| 1289 | `    # MARGIN is the longest process of the step, rounded up to whole seconds, plus RESERVE. With the test` | Comment: `MARGIN` is the longest process of the step, rounded up to whole seconds, plus `RESERVE`. |
| 1290 | `    # divisor 100 the longest process is 0.3 s (1 s); with divisor 1 the processes of YL and YP are 30 s.` | Continues the comment: with the test divisor 100 the longest process has 0.3 s, which rounds up to 1 s. With the divisor 1 the processes of `YL` and `YP` have 30 s. |
| 1291 | `    os.rename(box.sched(), os.path.join(box.dir, "sched10-test"))` | Moves the test schedule of the box away, to the name `sched10-test`. |
| 1292 | `    shutil.copytree(os.path.join(Y, "sched10"), box.sched())` | Copies the saved folder `sched10` beside this file, the real schedules, into the box. When that folder is missing, as in the repo copy, this line raises an error, and the test ends here without its summary. |
| 1293 | `    rc, out, err = box.run(["YL"], SESSION="1", STOP_AT=utc(100))` | Runs `YL` with a stop time 100 s from now. |
| 1294 | `    check("MARGIN follows the longest process of the step: the real YL schedule refuses at 120 s, not at 91 s",` | Starts a check: `MARGIN` follows the longest process of the step. The real `YL` schedule refuses a start at 120 s, not at 91 s. |
| 1295 | `          rc == 4 and not box.launched() and "less than 120 s away" in err and "longest process 30 s, MARGIN 120 s" in out,` | The test: exit status 4, no launch, the message `less than 120 s away`, and the summary line says that the longest process has 30 s and that `MARGIN` is 120 s. |
| 1296 | `          (rc, err, out))` | The detail for a failure. |
| 1297 | `    rc, out, err = box.run(["--dry-run", "YA", "YL", "YP", "YF", "YC"], SESSION="1")` | Runs a dry run of all 5 steps of session 1 with the real schedules. |
| 1298 | `    check("--dry-run of the real schedules, session 1: 399 processes (32 of bwx8) and the nominal work of the task "` | Starts a check: the dry run of the real schedules of session 1 gives 399 processes, 32 of them of `bwx8`, and the nominal work of the task. |
| 1299 | `          "(11.7, 960, 840, 2764.8, 252 s)",` | Continues the name: 11.7, 960, 840, 2764.8 and 252 s. |
| 1300 | `          rc == 0 and out.count("\nbwx8 --trial ") == 32 and out.count("\nbwx10 --trial ") == 367` | The test: exit status 0, 32 command lines of `bwx8` and 367 of `bwx10`. |
| 1301 | `          and all(s in out for s in ("step YA session 1: 9 processes, nominal kernel work 11.700 s",` | Continues: the summary line of `YA` with 9 processes and 11.700 s. |
| 1302 | `                                     "step YL session 1: 32 processes, nominal kernel work 960.000 s",` | Continues: the summary line of `YL` with 32 processes and 960.000 s. |
| 1303 | `                                     "step YP session 1: 28 processes, nominal kernel work 840.000 s",` | Continues: the summary line of `YP` with 28 processes and 840.000 s. |
| 1304 | `                                     "step YF session 1: 288 processes, nominal kernel work 2764.800 s",` | Continues: the summary line of `YF` with 288 processes and 2764.800 s. |
| 1305 | `                                     "step YC session 1: 42 processes, nominal kernel work 252.000 s")), (rc, err, out[:300]))` | Ends the test: the summary line of `YC` with 42 processes and 252.000 s. So the run script itself computes the planned numbers from the files that will go to CRB. |
| 1306 | `    rc, out, err = box.run(["--dry-run", "YL", "YP", "YF", "YC"], SESSION="2")` | Runs a dry run of the four steps of session 2 with the real schedules. |
| 1307 | `    check("--dry-run of the real schedules, session 2: 390 processes (32 of bwx8)",` | Starts a check: the dry run of the real schedules of session 2 gives 390 processes, 32 of them of `bwx8`. |
| 1308 | `          rc == 0 and out.count("\nbwx8 --trial ") == 32 and out.count("\nbwx10 --trial ") == 358, (rc, err))` | The test: exit status 0, 32 command lines of `bwx8` and 358 of `bwx10`. |
| 1309 | `    shutil.rmtree(box.sched())` | Removes the copy of the real schedules from the box. |
| 1310 | `    os.rename(os.path.join(box.dir, "sched10-test"), box.sched())` | Moves the test schedule back to the name `sched10`. |

### `run_checks`: session 2 and other refusals (lines 1312 to 1367)

| Line | Source | Explanation |
|---:|---|---|
| 1312 | `    # ---- session 2 ----` | Comment: the checks of session 2 start here. |
| 1313 | `    rc, out, err = box.run(["YF"], SESSION="2", STOP_AT="none")` | Runs `YF` for session 2 without `SESSION1_END`. |
| 1314 | `    check("session 2 without SESSION1_END: status 2, nothing starts",` | Starts a check: session 2 without `SESSION1_END` ends with status 2, and nothing starts. |
| 1315 | `          rc == 2 and "SESSION1_END" in err and not box.launched(), (rc, err))` | The test: exit status 2, the error output names `SESSION1_END`, and no launch. |
| 1316 | `    for step in ("YL", "YF"):` | Starts a loop over two steps, `YL` and `YF`. |
| 1317 | `        rc, out, err = box.run([step], SESSION="2", STOP_AT="none", SESSION1_END=utc(-3 * 3600 + 120))` | Runs the step for session 2 with an end of session 1 that lies 2 minutes less than 3 hours in the past. |
| 1318 | `        check("session 2 of %s earlier than 3 h after SESSION1_END: refused with status 2, nothing starts" % step,` | Starts a check per step: session 2 earlier than 3 hours after `SESSION1_END` is refused with status 2, and nothing starts. |
| 1319 | `              rc == 2 and "3 hours" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the words `3 hours` in the error output, no launch and no result folder. The design asks for at least 3 hours between the end of the first session and the start of the second. |
| 1320 | `    for value in ("garbage", time.strftime("%Y-%m-%d", time.gmtime()), "yesterday", "@0", "-4 hours",` | Starts a loop over values of `SESSION1_END` that must be refused: a word without meaning, a date without a time, the word `yesterday`, the form `@0`, and a relative time. |
| 1321 | `                  time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - 4 * 3600)), "2026-02-30T00:00Z"):` | Continues the list: a date and a time of 4 hours ago with a blank between them and without `Z`, and the 30th of February in the right form. |
| 1322 | `        rc, out, err = box.run(["--from", "287", "YF"], SESSION="2", STOP_AT="none", SESSION1_END=value)` | Runs the last process of `YF` for session 2 with that value. |
| 1323 | `        check("session 2 with SESSION1_END='%s': status 2, nothing starts" % value,` | Starts a check per value: status 2, and nothing starts. |
| 1324 | `              rc == 2 and "bad SESSION1_END" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the message `bad SESSION1_END`, no launch and no result folder. Several of these values are accepted by `date -d`. Without the strict form a wrong text could let session 2 start too early. |
| 1325 | `    s1end = utc(-3 * 3600 - 60)` | `s1end`: a valid end of session 1 that lies 3 hours and 1 minute in the past. |
| 1326 | `    row2 = box.rows("YF", 2)[287]` | `row2`: the last row of the `YF` schedule of session 2. |
| 1327 | `    rc, out, err = box.run(["--from", "287", "YF"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)` | Runs the last process of `YF` for session 2 with that end time. |
| 1328 | `    env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1329 | `    check("session 2 later than 3 h after SESSION1_END: runs the session 2 schedule, folder bwx10-YF-s2-, SESSION1_END in env.txt",` | Starts a check: session 2 later than 3 hours after `SESSION1_END` runs the schedule of session 2. The folder name starts with `bwx10-YF-s2-`, and `env.txt` records `SESSION1_END`. |
| 1330 | `          rc == 0 and "bwx10-YF-s2-" in (box.folder() or "") and ("SESSION1_END=" + s1end) in env` | The test: exit status 0, the name of the result folder, and the recorded end time. |
| 1331 | `          and ("-- step YF session 2 idx 287 tag %s " % row2[1]) in box.csv("YF")` | Continues: the header line in the output file names session 2, the `idx` 287 and the tag of the row of session 2. |
| 1332 | `          and "--plan sched10/s2/YF/0287.plan" in box.launched()[0], (rc, err))` | Ends the test: the launch got the plan of session 2. So `SESSION=2` selects the schedules of session 2, which have the reversed CPU order. |
| 1333 | `    row2 = box.rows("YL", 2)[31]` | `row2`: the last row of the `YL` schedule of session 2. |
| 1334 | `    rc, out, err = box.run(["--from", "31", "YL"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)` | Runs that last process for session 2. |
| 1335 | `    check("session 2 of the bwx8 step: runs the session 2 row with the old binary",` | Starts a check: session 2 of the step that uses `bwx8` runs the row of session 2 with the older binary. |
| 1336 | `          rc == 0 and box.binaries() == [box.bin8] and ("-- step YL session 2 idx 31 tag %s " % row2[1]) in box.csv("YL")` | The test: exit status 0, the launch used the dummy `bwx8`, and the header line names session 2, the `idx` 31 and the tag of that row. |
| 1337 | `          and box.launched()[0].split(" ", 1)[1] == row2[5], (rc, err))` | Ends the test: the dummy got the `args` of that row. So the `.bin` file of session 2 is read too. |
| 1339 | `    # ---- other refusals ----` | Comment: the checks of other refusals start here. |
| 1340 | `    rc, out, err = box.run(["YA"], STOP_AT="none")` | Runs `YA` without `SESSION`. |
| 1341 | `    check("SESSION not set: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. The script does not guess the session. |
| 1342 | `    rc, out, err = box.run(["--from", "9", "YA"], SESSION="1", STOP_AT="none")` | Runs `YA` with `--from 9`. The step has the `idx` values 0 to 8. |
| 1343 | `    check("--from past the last idx: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. A `--from` value past the last `idx` runs nothing and is reported. |
| 1344 | `    rc, out, err = box.run(["--from", "1", "YA", "YF"], SESSION="1", STOP_AT="none")` | Runs two steps with `--from 1`. |
| 1345 | `    check("--from with two steps: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. `--from` is allowed with one step only. |
| 1346 | `    allowed = sorted(os.sched_getaffinity(0))` | `allowed`: the CPUs on which this test may run, in sorted order. |
| 1347 | `    rc, out, err = box.run(["--from", "8", "YA"], pre=["taskset", "-c", str(allowed[0])], SESSION="1", STOP_AT="none")` | Runs the last process of `YA`, with `taskset -c` before the script. So the script starts limited to one CPU, the lowest allowed one. |
| 1348 | `    seen = open(box.log + ".cpus").read() if os.path.exists(box.log + ".cpus") else ""` | `seen`: the CPU list that the dummy recorded, or an empty text. |
| 1349 | `    check("the benchmark is confined to CPUs 0-119, whatever CPU the script was started on",` | Starts a check: the benchmark is limited to the CPUs 0 to 119, on whatever CPU the script was started. |
| 1350 | `          rc == 0 and len(allowed) > 1 and seen.count("\n") == 1 and cpu_list(seen) == {c for c in allowed if c < 120},` | The test: exit status 0, the test may use more than one CPU, the dummy recorded one line, and its CPU list is the set of the allowed CPUs below 120. |
| 1351 | `          (rc, err, seen))` | The detail for a failure. The check proves that the script sets the CPU list itself and does not keep the narrow list of its caller. The runner then finds its worker CPU in the list. |
| 1352 | `    tsv = box.sched("s1", "YA.tsv")` | `tsv`: the schedule file of `YA` in session 1 of the box. |
| 1353 | `    saved_ya = open(tsv).read()` | `saved_ya`: its text, kept for later. |
| 1354 | `    made = os.path.join(box.dir, "made-by-schedule")` | `made`: the path of a file that must never appear. |
| 1355 | `    for what, old_, new_ in (("idx", "\n0\t", "\na[$(touch${IFS}%s)]\t"), ("cpu", "\t2\t", "\ta[$(touch${IFS}%s)]\t")):` | Starts a loop over two damaged schedules. In the first the `idx` of the first row is a text with a command substitution that would create the file `made`. In the second the `cpu` column holds such a text. `${IFS}` takes the place of the blank inside the command, so the column itself holds no blank. |
| 1356 | `        with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1357 | `            fh.write(saved_ya.replace(old_, new_ % made, 1))` | Writes the schedule with that one replacement. |
| 1358 | `        rc, out, err = box.run(["--dry-run", "YA"], SESSION="1")` | Runs a dry run of `YA`. |
| 1359 | `        check("schedule with a command in %s: status 2, the command does not run" % what,` | Starts a check per case: a schedule with a command in that column gives status 2, and the command does not run. |
| 1360 | `              rc == 2 and not os.path.exists(made) and open(tsv).read() != saved_ya, (rc, err))` | The test: exit status 2, the file `made` does not exist, and the schedule file really differs from the saved text. The script uses `idx` in shell arithmetic, which would run such a command, and it gives `cpu` to the host sampler. The check proves that both values are tested before they are used. |
| 1361 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1362 | `        fh.write(saved_ya)` | Writes the saved text back. |
| 1363 | `    os.rename(box.sched("s1", "YA", "0001.plan"), os.path.join(box.dir, "moved.plan"))` | Moves the plan file of the second process of `YA` out of the schedule folder. |
| 1364 | `    rc, out, err = box.run(["YA"], SESSION="1", STOP_AT="none")` | Runs `YA` for real. |
| 1365 | `    check("missing plan file: status 2 before the first launch", rc == 2 and "missing plan file" in err and not box.launched(), (rc, err))` | Check: exit status 2, the message `missing plan file`, and no launch. So a missing plan stops the step before its first process, and not in the middle of the step. |

### `main`: the order of the groups of checks, and the summary (lines 1368 to 1394)

| Line | Source | Explanation |
|---:|---|---|
| 1368 | `def main():` | Starts the function `main`. |
| 1369 | `    with open("/proc/loadavg") as f:` | Opens the file `/proc/loadavg`. |
| 1370 | `        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))` | Prints the load averages of the last 1, 5 and 15 minutes and the number of CPUs on which the test may run. The load matters: the run script waits for a quiet system before each launch, so the test takes longer on a loaded machine. |
| 1371 | `    tmp = tempfile.mkdtemp(prefix="test_schedule10.")` | `tmp`: a new temporary folder whose name starts with `test_schedule10.`. |
| 1372 | `    try:` | Starts the block that the cleanup follows in every case. |
| 1373 | `        real, sched = schedule_checks(tmp)` | Runs the checks of the generator. They return the folder with the real durations and the folder with the test divisor 100. |
| 1374 | `        if "--no-bwx8" in sys.argv[1:]:` | When the option `--no-bwx8` was given. |
| 1375 | `            print("SKIP  the run of every plan of YL through the local stand-in bwx8 (--no-bwx8)")` | Prints a `SKIP` line for the checks with the stand-in `bwx8`. |
| 1376 | `        else:` | If not. |
| 1377 | `            bwx8_checks(tmp, real, sched)` | Runs the checks with the stand-in `bwx8`: the build, every plan of `YL`, the real window plans and the plans with a defect. |
| 1378 | `        bwx10_checks(tmp, sched)` | Runs the plans of the other four steps through the stand-in `bwx10`, unless an option, a missing source or a failed build leaves that part out. |
| 1379 | `        visit_checks(tmp)` | Runs the checks of the visit script. |
| 1380 | `        if "--no-run" in sys.argv[1:]:` | When the option `--no-run` was given. |
| 1381 | `            print("SKIP  the checks of run_bwx10.sh with dummy binaries (--no-run)")` | Prints a `SKIP` line for the checks of `run_bwx10.sh` with dummy binaries. |
| 1382 | `        else:` | If not. |
| 1383 | `            run_checks(tmp, sched)` | Runs the checks of the run script. |
| 1384 | `    finally:` | The cleanup. It runs in every case, also after an error. |
| 1385 | `        shutil.rmtree(tmp, ignore_errors=True)` | Removes the temporary folder with everything in it. |
| 1386 | `    with open("/proc/loadavg") as f:` | Opens the file `/proc/loadavg` again. |
| 1387 | `        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))` | Prints the load averages at the end. |
| 1388 | `    print("# checks: %d, passed: %d, failed: %d%s" % (COUNT[0], COUNT[0] - len(FAILS), len(FAILS),` | Prints the summary line: the number of checks, of passed checks and of failed checks. |
| 1389 | `                                                      "".join("\n#   " + n for n in FAILS)))` | The last value of the summary: the name of each failed check, on a line of its own. |
| 1390 | `    sys.exit(1 if FAILS else 0)` | Ends the program with exit status 1 when a check failed, and with 0 if not. A part that did not run does not change the status. |
| 1393 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 1394 | `    main()` | Runs `main`. |
