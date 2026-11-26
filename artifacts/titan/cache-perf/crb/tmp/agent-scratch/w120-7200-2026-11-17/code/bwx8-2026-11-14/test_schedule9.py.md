# `test_schedule9.py` explained, line by line

- Source file: `bwx8-2026-11-14/test_schedule9.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1401 lines, 86875 bytes).
- sha256 of the source when this page was built: `b975f99e7df26a348c0323c8897ebdf0efddd187bd5e9e8b06eef3ae89b32c3d`.

## Short version: purpose

`test_schedule9.py` checks the four scripts of round 2 without CRB: the generator `schedule9.py`, the host sampler `hostwatch.py`, the run script `run_bwx9.sh` and the visit script `visit9.sh`. It tests the generated schedules against rules that are written a second time in this file, it puts every plan through a runner that is built on the local machine, it runs the sampler beside busy test processes, and it runs the run script with a dummy binary through these stop cases: the marker file, the stop file, a signal, `STOP_AT` and a failing process. The validator and the rule functions of the steps are also applied to inputs that must not pass, to show that they can fail.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 1, round 2**: the first and the second set of tests of the investigation into the buffer size of 8 MiB. The steps of round 2 have names that start with `X`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`read_nop16`, `read_nop32`**: two kernels of the runner `bwx8`. Each is the `asmread` loop with 16 or 32 `nop` instructions added to each loop pass of 256 B. A `nop` is an instruction that does nothing.
- **`read_sparse`**: a kernel of the runner `bwx8`. Each loop pass handles 128 B with 4 `ldp q` loads and 9 `nop` instructions.
- **Process**: one start of a benchmark binary.
- **Check**: one call of the function `check`. It prints `PASS` or `FAIL` and one sentence that says what was tested.
- **Generator**: the program `schedule9.py`. It writes the schedules, the plan files and the `.watch` files of round 2.
- **Run script**: the script `run_bwx9.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Visit script**: the script `visit9.sh`. It makes one login to CRB and starts the run script there.
- **Host sampler**: the program `hostwatch.py`. It records what the Linux kernel does on one CPU while one process runs. The run script starts it beside a process when the step has a `.watch` file.
- **Step**: one batch of processes of a round, for example `XW`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **`.watch` file**: the empty file `<STEP>.watch` of a step. When it exists, the step runs with the host sampler.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Header pairs**: the pairs of the form `key=value` in the second line of a plan file, for example `kernel=asmread`.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Target, window**: the target is the kernel that a trial measures. A window is one timed period of it.
- **`S2` form**: a process of 4 equal trials, each with a prefix of 1200 ms of the target kernel and 4 target windows of 300 ms. Step `S2` of round 1 had this form first.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Condition**: one setting that a step compares, and the label that names it in the plan. In `XW` it is one target kernel at one size with or without a previous activity.
- **Cell**: one combination of the factors of a step, for example one kernel at one buffer size.
- **Replicate set, block**: a replicate set is one run of every kernel of step `XN` for one size and CPU. A block is the group of processes of one replicate on one CPU in the other steps.
- **Event set**: one of the three lists A, B and C of 6 counter events each.
- **Test divisor**: a number by which the generator divides every duration, for local tests only. The test uses 100.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters at the boundaries of the target windows.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`--pmu-type`, `--events`**: the two counter options of the runner. `--pmu-type` gives the type number that Linux gives to the counter device of the cores, 11 on CRB by the notes of the project. `--events` gives the list of counter events, each as a name and a code. The variables `BWX_PMU_TYPE` and `BWX_EVENTS` carry the same two values in the environment.
- **Validator**: the function `parse_plan` of this file. It tests a plan file against the rules of the plan format.
- **Stand-in**: a program that takes the place of another one in the test. The stand-in runner is built from the runner source on the local machine. Its kernels are plain C loops, and its rates mean nothing.
- **Dummy binary**: a small shell script that stands in for the runner. It records how it was started, sleeps, and ends with a chosen exit status.
- **Box**: the test setup of the run script: a copy of the script and of the sampler, the dummies and a schedule in a temporary folder.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop the run script.
- **`STOP_AT`**: a UTC time that the caller sets. The run script starts a process only when this time is more than `MARGIN` seconds away, and it ends a process that still runs at this time.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s by default. `MARGIN` is the nominal work of the longest process of a step, rounded up to whole seconds, plus `RESERVE`.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Sample**: one reading of all watched files of the sampler at one time.
- **Key**: the name of one value in the output of the sampler, for example `w.run_ns`. The prefix `m.` stands for the main thread of the watched process and `w.` for its worker thread.
- **Absolute line**: a sample line with the word `ABS` that holds the full value of every key.
- **Delta line**: a sample line that holds only the values that changed, each as a difference to the last sample.
- **State item**: an item of the form `key:=value`. It gives a new state and not a difference.
- **Scan**: one pass of the sampler over all threads of the host. It finds the threads of other processes whose last CPU is the watched CPU.
- **Footer**: the last line of a sampler file. It starts with `# end reason=` and gives the reason of the end and four values: the samples taken, the sample times that were missed, the longest time of one sample in microseconds, and the errors.
- **Context switch**: the moment at which Linux takes a thread off a CPU. It is voluntary when the thread waits for something, and involuntary when Linux takes the CPU away.
- **Time slice**: one uninterrupted period in which a thread runs on a CPU.
- **Clock tick**: the unit in which Linux reports the CPU time and the start time of a process. `SC_CLK_TCK` gives the number of ticks per second.
- **Soft interrupt**: a piece of work that the Linux kernel puts off to a later moment, for example work for timers or for the network.
- **Dry run**: a call of the run script with `--dry-run`. It prints what would run and starts nothing.
- **Output file, header line**: the output file of a step is `<STEP>.csv` in the result folder. Before the output of each process the run script writes a header line into it. That line starts with `-- step`.
- **Load record**: the lines that the run script appends to the file `launches.txt` before a launch: the load averages, the number of logins and the 5 processes with the highest `pcpu` value of `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent.
- **Start check**: a run of the host sampler of 0.3 s that the run script makes before the first process of a step with a sampler.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB**: 1024 bytes.

## Main flow

1. The values that the task expects are written as fixed values: the counts and the nominal work, the steps with a `.watch` file, the event sets, the conditions, the kernels and the sizes of each step (lines 37 to 54).
2. The helper `check` prints one line per check and collects the failures (lines 60 to 66).
3. The validator of the plan format and the reader of a generated folder (lines 69 to 151, lines 154 to 197).
4. The rules of the steps, in four functions: one for `XW`, one for the three counter steps, one for `XN` and one for `XF` (lines 233 to 365). The step `XEV` has no rule function. One check of group 1 tests the form of its processes (lines 479 to 485).
5. Group 1, `schedule_checks`: run the generator. Test the format of every file, the counts and the printed report, the header pairs, the CPU order, the rules of each step with damaged variants, the `.watch` files, the effect of the seed, the saved folder and the test divisor (lines 368 to 567).
6. Group 2, `bwx8_checks`: a locally built `bwx8` accepts all 635 plans of both sessions in their form with the test divisor 100, refuses three damaged plans, and refuses the plan of `XEV` without its event options (lines 571 to 648).
7. Group 3, `hostwatch_checks`: the host sampler beside a busy test process: the header, the absolute line, whole-file reads, errors inside the sampler, the sample rate, a shared CPU, the time limit, a signal, a missing process, a missing CPU, the usage and the source text (lines 686 to 841).
8. Group 4, `visit_checks`: the visit script with a stand-in for `ssh`: the remote command, bad settings, and the comparison with `visit8.sh` (lines 992 to 1032).
9. Group 5, `run_checks`: the run script with a dummy binary: syntax, comparison of the stop controls with `run_bwx8.sh`, step names and the dry run, a normal run, the counter settings, the host sampler, the stop controls with and without a sampler, `MARGIN`, session 2 and other refusals (lines 1035 to 1372).
10. `main` prints the system load, runs the groups in this order, removes the temporary folder and prints the summary (lines 1375 to 1397).

## Behavior a reader must know

- The test contacts no other machine. The visit script runs with a stand-in for `ssh` and a search path that holds no real `ssh` (line 1009). The run script runs as a copy in a temporary folder, with test paths for the marker file, the stop file, the binary and the results (lines 947 to 948).
- The test starts local programs: the generator, `gcc`, the stand-in runner (6 at a time, line 621), two busy test processes on one CPU, the host sampler, the copy of the run script and the dummies.
- The exit status is 0 only when every check passed (line 1397). A part that did not run prints a `SKIP` line and does not change the status. The summary line does not count the `SKIP` lines.
- Two options leave out parts: `--no-run` and `--no-bwx8` (lines 1381 to 1390). The checks of the generator, of the sampler and of the visit script always run. A failed build of the stand-in `bwx8` is a failed check and ends that group (lines 577 to 578).
- The expected values are written a second time in this file (lines 38 to 53). So a change in the generator alone makes a check fail.
- The validator, the comparison of the nominal work, the rule for the CPU order and the four rule functions of the steps are tested twice: once on the real output, and once on an input that must not pass. Such an input is a damaged copy, or the real output with a wrong expectation, for example the CPU order of the other session. These second tests are 25 checks. Not every rule inside a rule function has such a second test. For example, no check gives a rule function a schedule with a wrong number of processes.
- The checks of the run script take minutes on a loaded machine. Before each launch the script waits up to 20 s until at most 2 tasks are runnable.
- The stop cases run twice. With the sampler, on step `XW` (lines 1160 to 1193): the stop file, the marker file, a signal, `STOP_AT` during a process, and a failing process. Without the sampler, on step `XEV` (lines 1233 to 1312): the same five, and also the marker file at the start, between two processes and directly before a launch, the stop file at the start, and a `STOP_AT` that is nearer than `MARGIN`.
- What a stop case tests depends on the case. Every case tests the exit status. A case that ends a running process also tests the `-- killed` line and that no process is left. A case in which nothing may start tests that no dummy was started. The case of the marker file between two processes tests that the first process was not cut and that no second one started. A case of a failing process tests the `-- failed` line.
- The checks of `MARGIN` use stop times that lie far inside or far outside the margin: 30 s against 91 s, 100 s against 123 s, and 45 s against 1 s (lines 1275 to 1277, lines 1283 to 1285, line 1301). No check tests a stop time that is exactly `MARGIN` seconds away.
- The check of the saved folder compares every file of `sched9/` beside this file with the output of the generator (lines 550 to 552). The repo README lists the folders `sched*` among those that were left out of the repo. So in the repo folder this check fails, and the copy in line 1282 raises an error that ends the test without its summary.
- Two checks test less than their names say. By the name of the first, every item of a delta line is `key=number` or `key:=state`. The test accepts a state item only when its value is a number (lines 786 to 788). The second, which starts at line 558, is named for every duration divided by 100. The test compares the nominal work per step and session and the window counts, not each duration.
- The check that the sampler follows a thread of the other process takes the busiest followed thread of any process (lines 778 to 781). It does not test which process that thread belongs to.
- The check of the source text of the sampler reads the text only (lines 837 to 841). It does not watch which files the sampler opens when it runs.
- The stand-in runs need CPU 0, CPU 2 and one more CPU below 120 on the local machine (line 579). CPU 41 is replaced by a local CPU in a copy of the schedule (lines 593 to 596). The checks of the sampler need 3 allowed CPUs (line 688).
- The box gives the run script the highest allowed CPU as `WATCH_CPU` (line 928). The case of an empty `WATCH_CPU` has two expected results: it runs when the machine allows CPU 100, and it stops at the start check of the sampler when not (lines 1202 to 1206).
- The variable `real` of line 1280 is set and never used.
- The test reads these files of its own folder: `schedule9.py`, `hostwatch.py`, `run_bwx9.sh`, `visit9.sh`, `bwx8.c`, `run_bwx8.sh`, `visit8.sh` and the folder `sched9`.
- The test writes into a temporary folder only and removes it at the end (line 1378, line 1392).

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/test_schedule9.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1401 lines, 86875 bytes, sha256 `b975f99e7df26a348c0323c8897ebdf0efddd187bd5e9e8b06eef3ae89b32c3d`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 72. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Description text and imports (lines 1 to 26)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_schedule9.py - checks of schedule9.py, hostwatch.py, run_bwx9.sh and visit9.sh (round 2).` | Starts the description text of the file. First line: the name and the purpose. The file holds the checks of the generator `schedule9.py`, of the host sampler `hostwatch.py`, of the run script `run_bwx9.sh` and of the visit script `visit9.sh`. These are the four scripts of round 2. |
| 4 | `Usage: test_schedule9.py [--no-run] [--no-bwx8]` | Text of the description: the usage. Each of the two options leaves out one group of checks. |
| 5 | `Prints one line per check. Exit status 0 only if every check passed.` | Text of the description: the program prints one line per check. Its exit status is 0 only when every check passed. |
| 6 | `--no-run leaves out the checks that start run_bwx9.sh with a dummy bwx8 (they take minutes` | Text of the description: `--no-run` leaves out the checks that start `run_bwx9.sh` with a dummy `bwx8`. A dummy `bwx8` is a small script that stands in for the runner. |
| 7 | `on a loaded machine, because the script waits up to 20 s for a quiet system before a launch).` | Continues the text: those checks take minutes on a loaded machine. The reason: the run script waits up to 20 s for a quiet system before each launch. |
| 8 | `--no-bwx8 leaves out the build of the local stand-in bwx8 and the run of every plan through it.` | Text of the description: `--no-bwx8` leaves out the build of a local stand-in of the runner `bwx8`, and the run of every plan through it. A stand-in is a build on the machine of the developer. Its kernels are plain C loops, and its rates mean nothing. |
| 9 | `Rules are also applied to a defective input, and such a check passes only if that is rejected.` | Text of the description: the test also applies each rule to an input with a defect. Such a check passes only when the rule rejects that input. This shows that the rule can fail. |
| 10 | `This machine has no CPU 41: for the run through bwx8 the test rewrites CPU 41 to a local CPU` | Text of the description: the machine of the test has no CPU 41. For the runs through the stand-in the test replaces CPU 41 with a CPU that this machine has. |
| 11 | `in a copy of the schedule. Nothing else of the copy differs.` | Continues the text: the replacement is made in a copy of the schedule. Nothing else of the copy differs. |
| 12 | `"""` | Ends the description text. |
| 13 | `import collections` | Loads the Python module `collections`: counters and ordered dictionaries. |
| 14 | `import concurrent.futures` | Loads `concurrent.futures`: used to run several stand-in processes at the same time. |
| 15 | `import copy` | Loads `copy`: used to make an independent copy of a schedule before a check damages it. |
| 16 | `import itertools` | Loads `itertools`: used to merge equal neighbours of a list. |
| 17 | `import os` | Loads `os`: paths, folders and CPU lists. |
| 18 | `import re` | Loads `re`: regular expressions. |
| 19 | `import shutil` | Loads `shutil`: copies and removals of folder trees. |
| 20 | `import signal` | Loads `signal`: used to send a signal to the run script. |
| 21 | `import statistics` | Loads `statistics`: used for the median of the gaps between two sample lines of the host sampler. |
| 22 | `import subprocess` | Loads `subprocess`: used to start the scripts under test. |
| 23 | `import sys` | Loads `sys`: the command line, the output and the exit status. |
| 24 | `import tempfile` | Loads `tempfile`: used to make the temporary folder of the test. |
| 25 | `import time` | Loads `time`: the clock, time texts and waits. |

### Paths, expected values of the task, and the function `check` (lines 27 to 68)

| Line | Source | Explanation |
|---:|---|---|
| 27 | `sys.dont_write_bytecode = True` | Tells Python to write no compiled files into a `__pycache__` folder. So the test leaves no file in the code folder. |
| 28 | `X = os.path.dirname(os.path.abspath(__file__))` | `X`: the full path of the folder that holds this file. |
| 29 | `SCHED = os.path.join(X, "schedule9.py")` | `SCHED`: the path of the generator under test, `schedule9.py`. |
| 30 | `RUN = os.path.join(X, "run_bwx9.sh")` | `RUN`: the path of the run script under test, `run_bwx9.sh`. |
| 31 | `VISIT = os.path.join(X, "visit9.sh")` | `VISIT`: the path of the visit script under test, `visit9.sh`. |
| 32 | `WATCH = os.path.join(X, "hostwatch.py")` | `WATCH`: the path of the host sampler under test, `hostwatch.py`. |
| 33 | `READ_KERNELS = ["oldread", "read", "asmread", "read_nop4", "read_nop8", "read_nop16", "read_nop32", "read_sparse"]` | `READ_KERNELS`: the 8 kernel names that the plan validator of this file accepts in a plan. |
| 34 | `# The flags of build8.sh.` | Comment: the compiler flags that follow are those of the build script `build8.sh`. |
| 35 | `CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "` | `CFLAGS`: the compiler flags for the stand-in build, split into a list of words. This line: the optimisation level `-O3`, code for the CPU of this machine (`-march=native`), no replacement of a loop by a library call such as `memset` (`-fno-tree-loop-distribute-patterns`), thread support, more warnings, and the C dialect `gnu11`. |
| 36 | `          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()` | Continues the flags: do not merge functions that have equal code (`-fno-ipa-icf`), keep the functions in the order of the source (`-fno-toplevel-reorder`), and align each function to 4 bytes. |
| 37 | `# The task: processes per step and session, trials per process, nominal kernel work in seconds.` | Comment: the table that follows states the task of the generator. For each step it gives the processes per session, the trials per process and the nominal kernel work in seconds. |
| 38 | `TABLE = {"XW": (28, 1, 864.0), "XCA": (18, 1, 396.0), "XCB": (18, 1, 396.0), "XCC": (18, 1, 396.0),` | `TABLE`: the expected values, written here as fixed numbers and not taken from the generator. `XW`: 28 processes of 1 trial, 864.0 s. `XCA`, `XCB` and `XCC`: 18 processes of 1 trial and 396.0 s each. |
| 39 | `         "XEV": (3, 1, 2.7), "XN": (144, 4, 1382.4), "XF": (90, 4, 864.0)}` | Ends the table. `XEV`: 3 processes of 1 trial, 2.7 s. `XN`: 144 processes of 4 trials, 1382.4 s. `XF`: 90 processes of 4 trials, 864.0 s. |
| 40 | `WATCH_STEPS = ["XCA", "XCB", "XCC", "XW"]` | `WATCH_STEPS`: the four steps that must have a `.watch` file, in sorted order. The run script starts the host sampler for a step with such a file. |
| 41 | `EVENTS = {` | `EVENTS`: the three event sets that the counter steps must have in their `args` column, written here a second time. So a change of a set in the generator alone makes a check fail. |
| 42 | `    "A": "cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17,l3d_cache_refill=0x2a,stall_backend_mem=0x4005",` | Set A as one text: the 6 events `cpu_cycles`, `inst_retired`, `l1d_cache_refill`, `l2d_cache_refill`, `l3d_cache_refill` and `stall_backend_mem`, each with its event code. |
| 43 | `    "B": "l1d_cache_lmiss_rd=0x39,l2d_cache_lmiss_rd=0x4009,l3d_cache_lmiss_rd=0x400b,ll_cache_miss_rd=0x37,l2d_cache=0x16,bus_access=0x19",` | Set B: `l1d_cache_lmiss_rd`, `l2d_cache_lmiss_rd`, `l3d_cache_lmiss_rd`, `ll_cache_miss_rd`, `l2d_cache` and `bus_access`. |
| 44 | `    "C": "exc_taken=0x09,l1d_tlb_refill=0x05,dtlb_walk=0x34,l2d_cache_wb=0x18,l3d_cache_allocate=0x29,mem_access=0x13",` | Set C: `exc_taken`, `l1d_tlb_refill`, `dtlb_walk`, `l2d_cache_wb`, `l3d_cache_allocate` and `mem_access`. |
| 45 | `}` | Ends the dictionary `EVENTS`. |
| 46 | `# name: (kernel, size, previous activity)` | Comment: each entry of `XW` maps the name of a condition to its kernel, its size and its previous activity. |
| 47 | `XW = {"W0": ("read", "8M", None), "W1": ("read", "8M", "oldread@8M"), "W2": ("read", "8M", "read@1M"),` | `XW`: the seven conditions of step `XW` as the test expects them. `W0`: `read` at 8 MiB with no previous activity. `W1`: `read` at 8 MiB after `oldread` at 8 MiB. `W2`: `read` at 8 MiB after `read` at 1 MiB. |
| 48 | `      "W3": ("asmread", "8M", None), "W4": ("oldread", "8M", None), "W5": ("read", "4M", None),` | Continues the list, all without a previous activity: `W3` is `asmread` at 8 MiB, `W4` is `oldread` at 8 MiB, and `W5` is `read` at 4 MiB. |
| 49 | `      "W6": ("read", "16M", None)}` | Ends the list: `W6` is `read` at 16 MiB, with no previous activity. |
| 50 | `XN_KERNELS = ["asmread", "read_nop16", "read_nop32", "read_sparse"]` | `XN_KERNELS`: the four kernels that step `XN` must use: `asmread`, `read_nop16`, `read_nop32` and `read_sparse`. |
| 51 | `XN_SIZES = ["32K", "1M", "8M"]` | `XN_SIZES`: the three buffer sizes that step `XN` must use: 32 KiB, 1 MiB and 8 MiB. |
| 52 | `XF_CELLS = [("read", s) for s in ("1572864", "2M", "2621440", "3M", "5M", "6M", "12M", "24M", "32M", "64M")] + \` | `XF_CELLS`: the 15 cells that step `XF` must have. This line: `read` at 10 sizes from 1.5 MiB to 64 MiB. The sizes 1.5 MiB and 2.5 MiB are written in bytes. The backslash joins the next line to this statement. |
| 53 | `           [("oldread", s) for s in ("2M", "3M", "6M", "12M", "32M")]` | Ends the list: `oldread` at 2, 3, 6, 12 and 32 MiB. |
| 54 | `HEAD_S2 = ["step", "session", "cpu", "bytes", "proc", "rep_set", "kernel", "size", "seed", "test"]` | `HEAD_S2`: the keys of the header pairs of a plan whose trials have the form of step `S2`, in the order that the plan file must have. |
| 56 | `FAILS = []` | `FAILS`: the names of the checks that failed, empty at first. |
| 57 | `COUNT = [0]` | `COUNT`: the number of checks. It is kept in a list of one entry, so a function can change it. |
| 60 | `def check(name, ok, detail=""):` | Starts the function `check`. Every check of this file calls it. `name`: the sentence that says what is checked. `ok`: the result of the test. `detail`: values to print when the check fails. |
| 61 | `    COUNT[0] += 1` | Counts the check. |
| 62 | `    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail)[:600] + "]") if detail and not ok else ""))` | Prints one line: `PASS` or `FAIL`, and then the name. After a failure it adds the first 600 characters of the detail in square brackets. |
| 63 | `    sys.stdout.flush()` | Writes the line to the output immediately. |
| 64 | `    if not ok:` | When the check failed. |
| 65 | `        FAILS.append(name)` | Keeps its name for the summary at the end. |
| 66 | `    return ok` | Returns the result. A caller can use it to stop a group of checks after a failure. |

### The plan validator of the test: patterns, `nbytes`, `parse_plan`, `rejected` (lines 69 to 153)

| Line | Source | Explanation |
|---:|---|---|
| 69 | `# ---------- an independent validator of plan format v1 (DECISIONS-bwx8.md, "Plan file") ----------` | Comment: the code that follows is a validator of the plan format, version 1. By the comment it is independent: it is written from the section "Plan file" of the notes file `DECISIONS-bwx8.md`, and not from the generator. So it can find a mistake of the generator. |
| 70 | `PHASE = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?):(\d+)$")` | `PHASE`: the pattern of a phase text such as `asmread@8M:1200`. Group 1 holds the kernel name: lower-case letters, digits and `_`. Group 2, after the `@`, holds the size: digits and an optional letter `K`, `M` or `G`. Group 3, after the colon, holds the duration in ms: digits. |
| 71 | `TGT = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?)$")` | `TGT`: the pattern of a target text such as `asmread@8M`. Group 1 holds the kernel name and group 2 the size, as in `PHASE`. A target has no duration. |

Line 72 holds a backslash directly before a `|`. It stands outside the table:

```text
COND = re.compile(r"^[^=|, ]+=[^=|, ]+(\|[^=|, ]+=[^=|, ]+)*$")
```

Explanation of line 72: `COND`: the pattern of a condition label such as `K=asmread|S=8M`. A label is one pair `key=value`, or several pairs with a vertical bar between them. A key and a value have at least one character each. They hold no equals sign, no vertical bar, no comma and no blank.

| Line | Source | Explanation |
|---:|---|---|
| 75 | `def nbytes(tok):` | Starts the function `nbytes`. It converts a size text such as `8M` to a number of bytes. |
| 76 | `    m = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}` | `m`: the factor of each unit letter: 1024 for `K`, 1024 times 1024 for `M`, and 1024 times that for `G`. |
| 77 | `    return int(tok[:-1]) * m[tok[-1]] if tok[-1] in m else int(tok)` | Returns the number before the letter times its factor. A text without a letter is a plain number of bytes. |
| 80 | `def parse_plan(text):` | Starts the function `parse_plan`, the validator. It reads the text of one plan file and tests every rule of the format. |
| 81 | `    """Returns (header dict, header key order, trials) or raises ValueError that names the defect."""` | Description text: the function returns the header pairs as a dictionary, the order of the header keys, and the list of trials. For a defect it raises a `ValueError` whose text names the defect. |
| 82 | `    if not text.endswith("\n"):` | Rule: the file ends with a newline. |
| 83 | `        raise ValueError("no final newline")` | If not: raises the error `no final newline`. |
| 84 | `    lines = text[:-1].split("\n")` | `lines`: the lines of the file, without the last newline. |
| 85 | `    if len(lines) < 4:` | Rule: the file has at least 4 lines. These are 3 header lines and one trial. |
| 86 | `        raise ValueError("fewer than 4 lines")` | If not: raises the error `fewer than 4 lines`. |
| 87 | `    if lines[0] != "# bwx8-plan v1":` | Rule: the first line is exactly `# bwx8-plan v1`. |
| 88 | `        raise ValueError("line 1")` | If not: raises an error with the text `line 1`. |
| 89 | `    if not lines[1].startswith("# "):` | Rule: the second line starts with `#` and a blank. |
| 90 | `        raise ValueError("line 2")` | If not: raises an error with the text `line 2`. |
| 91 | `    head = collections.OrderedDict()` | `head`: the header pairs, kept in the order of the file. |
| 92 | `    for pair in lines[1][2:].split(" "):` | Starts a loop over the pairs of the second line, split at single blanks. |
| 93 | `        k, eq, v = pair.partition("=")` | Splits a pair at the first equals sign into the key `k` and the value `v`. |
| 94 | `        if not k or not eq or not v or k in head or "," in pair:` | Rules for a pair: it has a key, an equals sign and a value. The key was not used before. The pair holds no comma. Two blanks in a row give an empty pair, which fails here. |
| 95 | `            raise ValueError("line 2 pair '%s'" % pair)` | If not: raises an error that shows the pair. |
| 96 | `        head[k] = v` | Stores the pair. |
| 97 | `    for k in ("step", "session", "cpu", "bytes", "proc", "seed", "test"):` | Starts a loop over the 7 keys that every plan must have: `step`, `session`, `cpu`, `bytes`, `proc`, `seed` and `test`. |
| 98 | `        if k not in head:` | Rule: the key is in the header. |
| 99 | `            raise ValueError("line 2 lacks " + k)` | If not: raises an error that names the missing key. |
| 100 | `    if lines[2] != "# trial cond rep prev pfx pred tgt nwin win_ms count bins":` | Rule: the third line is exactly the list of the 11 column names. |
| 101 | `        raise ValueError("line 3")` | If not: raises an error with the text `line 3`. |
| 102 | `    total = int(head["bytes"])` | `total`: the buffer size of the process in bytes, from the header. |
| 103 | `    seen = collections.Counter()` | `seen`: how often each condition label was used up to now. |
| 104 | `    trials = []` | `trials`: the result list, empty at first. |
| 106 | `    def size_ok(tok):` | Starts the inner function `size_ok`. It tests the size of a phase or of a target. |
| 107 | `        b = nbytes(tok)` | `b`: the size in bytes. |
| 108 | `        return b > 0 and b % 256 == 0 and b <= total` | Rule: the size is above 0, a multiple of 256 bytes, and not larger than the buffer of the process. |
| 110 | `    for n, line in enumerate(lines[3:]):` | Starts the loop over the trial lines. `n` counts from 0. |
| 111 | `        f = line.split(" ")` | Splits the line at single blanks. |
| 112 | `        if len(f) != 11 or "" in f:` | Rule: the line has exactly 11 fields, and none is empty. An empty field means two blanks in a row. |
| 113 | `            raise ValueError("trial line %d: fields" % n)` | If not: raises an error that names the trial line and the word `fields`. |
| 114 | `        trial, cond, rep, prev, pfx, pred, tgt, nwin, win_ms, count, bins = f` | Gives the 11 fields their names. |
| 115 | `        if trial != str(n):` | Rule: the trial number is the number of the line, counted from 0. |
| 116 | `            raise ValueError("trial line %d: number" % n)` | If not: raises an error with the word `number`. |
| 117 | `        if not COND.match(cond):` | Rule: the condition label matches the pattern `COND`. |
| 118 | `            raise ValueError("trial line %d: cond" % n)` | If not: raises an error with the word `cond`. |
| 119 | `        seen[cond] += 1` | Counts the use of this label. |
| 120 | `        if rep != str(seen[cond]) or not 1 <= seen[cond] <= 4:` | Rule: `rep` is the number of this use of the label, counted from 1. A label is used at most 4 times. |
| 121 | `            raise ValueError("trial line %d: rep" % n)` | If not: raises an error with the word `rep`. |
| 122 | `        ms = {}` | `ms`: the duration in ms of each of the three phases before the target. |
| 123 | `        for name, tok in (("prev", prev), ("pfx", pfx), ("pred", pred)):` | Starts a loop over the three phases: the previous activity, the prefix and the predecessor. |
| 124 | `            ms[name] = 0` | The duration is 0 unless the phase exists. |
| 125 | `            if tok == "-":` | A `-` means that the trial has no such phase. |
| 126 | `                continue` | Goes on with the next phase. |
| 127 | `            m = PHASE.match(tok)` | Matches the text with the pattern `PHASE`. |
| 128 | `            if not m or m.group(1) not in READ_KERNELS or not size_ok(m.group(2)) or int(m.group(3)) < 1:` | Rules for a phase: the text has the form of `PHASE`, the kernel is one of `READ_KERNELS`, the size passes `size_ok`, and the duration is at least 1 ms. |
| 129 | `                raise ValueError("trial line %d: %s" % (n, name))` | If not: raises an error that names the phase. |
| 130 | `            ms[name] = int(m.group(3))` | Stores the duration. |
| 131 | `        if ms["pfx"] % 4:` | Rule: the duration of the prefix is a multiple of 4 ms. By the notes file the runner records a prefix as 4 windows of a quarter of its duration. |
| 132 | `            raise ValueError("trial line %d: pfx not a multiple of 4" % n)` | If not: raises an error that says so. |
| 133 | `        m = TGT.match(tgt)` | Matches the target text with the pattern `TGT`. |
| 134 | `        if not m or m.group(1) not in READ_KERNELS or not size_ok(m.group(2)):` | Rules for the target: the form of `TGT`, a kernel of `READ_KERNELS`, and a size that passes `size_ok`. |
| 135 | `            raise ValueError("trial line %d: tgt" % n)` | If not: raises an error with the word `tgt`. |
| 136 | `        if not (nwin.isdigit() and 1 <= int(nwin) <= 4096 and win_ms.isdigit() and int(win_ms) >= 1):` | Rule: the number of windows is a whole number from 1 to 4096, and the window length is a whole number of at least 1 ms. |
| 137 | `            raise ValueError("trial line %d: windows" % n)` | If not: raises an error with the word `windows`. |
| 138 | `        if count not in ("closed", "open", "read") or bins not in ("0", "1"):` | Rule: the counter mode is `closed`, `open` or `read`, and `bins` is `0` or `1`. |
| 139 | `            raise ValueError("trial line %d: count or bins" % n)` | If not: raises an error with the words `count or bins`. |
| 140 | `        trials.append({"cond": cond, "rep": int(rep), "prev": prev, "pfx": pfx, "pred": pred, "tgt": tgt,` | Adds the trial as a dictionary. This line: the label, the repeat number, the three phase texts and the target. |
| 141 | `                       "nwin": int(nwin), "win_ms": int(win_ms), "count": count, "bins": int(bins),` | Continues the dictionary: the number and the length of the windows, the counter mode and the bins value. |
| 142 | `                       "ms": ms["prev"] + ms["pfx"] + ms["pred"] + int(nwin) * int(win_ms)})` | Ends the dictionary with `ms`, the nominal kernel work of the trial in ms: the three phase durations plus the number of windows times the window length. The test computes this value itself, without the generator. |
| 143 | `    return head, list(head), trials` | Returns the header dictionary, the list of its keys in file order, and the trials. |
| 146 | `def rejected(text):` | Starts the function `rejected`. It says whether the validator refuses a plan text. |
| 147 | `    try:` | Starts the block whose error is caught. |
| 148 | `        parse_plan(text)` | Runs the validator. |
| 149 | `    except ValueError:` | The validator raised a `ValueError`. |
| 150 | `        return True` | Returns true: the text was rejected. |
| 151 | `    return False` | Returns false: the text was accepted. |

### Reading a generated folder, and small rule helpers (lines 154 to 232)

| Line | Source | Explanation |
|---:|---|---|
| 154 | `# ---------- reading a generated tree ----------` | Comment: the functions that read a generated folder start here. |
| 155 | `def gen(out, *opts):` | Starts the function `gen`. It runs the generator with the output folder `out` and with more options. |
| 156 | `    return subprocess.run([sys.executable, SCHED, "--out", out] + list(opts), capture_output=True, text=True)` | Starts the generator as a process of its own, with the Python that runs this test. It keeps the output and the error output as text. It returns the result object, which also holds the exit status. |
| 159 | `def load(out):` | Starts the function `load`. It reads every schedule file and every plan file of a generated folder and tests their form. |
| 160 | `    """{(step, session): [process]}; a process holds its schedule row, header and trials."""` | Description text: the result maps each pair of step and session to its list of processes. A process holds its schedule row, its plan header and its trials. |
| 161 | `    tree, errors = {}, []` | `tree`: the result. `errors`: the list of the defects found. Both are empty at first. |
| 162 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 163 | `        sdir = os.path.join(out, "s%d" % session)` | `sdir`: the folder of the session. |
| 164 | `        for name in sorted(os.listdir(sdir)):` | Starts a loop over the names in the session folder, in sorted order. |
| 165 | `            if not name.endswith(".tsv"):` | A name that does not end with `.tsv`. |
| 166 | `                continue` | Skips it. Only schedule files are read here. |
| 167 | `            step = name[:-4]` | `step`: the file name without the ending `.tsv`. |
| 168 | `            rows = open(os.path.join(sdir, name)).read().split("\n")` | `rows`: the lines of the schedule file. |
| 169 | `            if rows[0] != "idx\ttag\tcpu\tbytes\tplan\targs" or rows[-1] != "":` | Rule: the first row is exactly the six column names with tabs between them, and the file ends with a newline. |
| 170 | `                errors.append("%s s%d: header or end of the schedule" % (step, session))` | If not: notes a defect of the header or of the end of the schedule. |
| 171 | `            procs = []` | `procs`: the processes of this step, empty at first. |
| 172 | `            for n, row in enumerate(rows[1:-1]):` | Starts the loop over the data rows. `n` counts from 0. |
| 173 | `                f = row.split("\t")` | Splits the row at the tabs. |
| 174 | `                if len(f) != 6 or f[0] != str(n) or f[4] != "%04d.plan" % n:` | Rule: the row has 6 columns, its `idx` is the row number, and its plan name is that number with 4 digits and the ending `.plan`. |
| 175 | `                    errors.append("%s s%d row %d: columns, idx or plan name" % (step, session, n))` | If not: notes the defect. |
| 176 | `                    continue` | Goes on with the next row. |
| 177 | `                p = {"idx": n, "tag": f[1], "cpu": int(f[2]), "bytes": int(f[3]), "plan": f[4], "args": f[5]}` | `p`: the process as a dictionary of its schedule columns. |
| 178 | `                want = "--trial --cpus %d --bytes %d --plan sched9/s%d/%s/%s" % (p["cpu"], p["bytes"], session, step, f[4])` | `want`: the `args` text that the row must start with: `--trial`, `--cpus` with the CPU of the row, `--bytes` with its size, and `--plan` with the path `sched9/s<session>/<STEP>/<plan name>`. |
| 179 | `                if not (f[5] == want or f[5].startswith(want + " --pmu-type ")):` | Rule: the `args` are exactly that text, or that text followed by a blank and `--pmu-type` with more options. So only the counter options may be added. |
| 180 | `                    errors.append("%s s%d row %d: args" % (step, session, n))` | If not: notes a defect of the `args`. |
| 181 | `                p["extra"] = f[5][len(want):]` | `extra`: the text of the `args` after `want`, that is the added options. |
| 182 | `                try:` | Starts the block whose errors are caught. |
| 183 | `                    p["head"], p["order"], p["trials"] = parse_plan(open(os.path.join(sdir, step, f[4])).read())` | Reads the plan file of the row and validates it with `parse_plan`. The header, the key order and the trials go into `p`. |
| 184 | `                except (ValueError, OSError) as e:` | A defect of the plan, or a plan file that cannot be read. |
| 185 | `                    errors.append("%s s%d row %d: %s" % (step, session, n, e))` | Notes the defect with the text of the error. |
| 186 | `                    continue` | Goes on with the next row. |
| 187 | `                h = p["head"]` | `h`: the header of the plan. |
| 188 | `                if (h["step"], h["session"], h["cpu"], h["bytes"], h["proc"]) != (step, str(session), f[2], f[3], f[0]):` | Rule: the header of the plan names the same step, session, CPU, size and process number as the schedule row. |
| 189 | `                    errors.append("%s s%d row %d: header pairs differ from the row" % (step, session, n))` | If not: notes that the header pairs differ from the row. |
| 190 | `                procs.append(p)` | Adds the process to the list. |
| 191 | `            tags = [p["tag"] for p in procs]` | `tags`: the tags of all processes of the step. |
| 192 | `            if len(set(tags)) != len(tags) or any(re.search(r"\s", t) for t in tags):` | Rule: no tag occurs twice in a step, and no tag holds a blank or another white-space character (pattern `\s`). |
| 193 | `                errors.append("%s s%d: a tag occurs twice or holds a blank" % (step, session))` | If not: notes the defect. |
| 194 | `            if len(os.listdir(os.path.join(sdir, step))) != len(procs):` | Rule: the plan folder of the step holds exactly as many files as the schedule has rows. |
| 195 | `                errors.append("%s s%d: plan files and rows differ in number" % (step, session))` | If not: notes the defect. |
| 196 | `            tree[step, session] = procs` | Stores the processes of the step and session. |
| 197 | `    return tree, errors` | Returns the result and the list of defects. |
| 200 | `def proc_ms(p):` | Starts the function `proc_ms`: the nominal kernel work of one process in ms. |
| 201 | `    return sum(t["ms"] for t in p["trials"])` | Returns the sum of the `ms` values of its trials. |
| 204 | `def tree_bytes(out):` | Starts the function `tree_bytes`. It reads every file of a folder tree into memory. |
| 205 | `    d = {}` | `d`: the result, empty at first. |
| 206 | `    for root, _, files in os.walk(out):` | Starts a walk through the folder and all folders below it. |
| 207 | `        for f in files:` | Starts a loop over the files of one folder. |
| 208 | `            path = os.path.join(root, f)` | The path of the file. |
| 209 | `            d[os.path.relpath(path, out)] = open(path, "rb").read()` | Stores the bytes of the file under its path relative to the top folder. |
| 210 | `    return d` | Returns the dictionary. Two folder trees are equal when their dictionaries are equal. |
| 213 | `def cpu_blocks(procs, first, second):` | Starts the function `cpu_blocks`, the rule for the CPU order of a schedule. |
| 214 | `    """The CPUs alternate first, second, first, ... when equal neighbours are merged."""` | Description text: when equal neighbours are merged, the CPUs of the processes alternate: the first CPU, the second, the first, and so on. |
| 215 | `    seq = [k for k, _ in itertools.groupby(p["cpu"] for p in procs)]` | `seq`: the CPUs of the processes in schedule order, with each run of equal neighbours merged to one entry. |
| 216 | `    return len(seq) % 2 == 0 and all(c == (first, second)[i % 2] for i, c in enumerate(seq))` | True when the merged list has an even length and alternates, with `first` at its start. |
| 219 | `def cpus_of(session):` | Starts the function `cpus_of`. |
| 220 | `    return (2, 41) if session == 1 else (41, 2)` | Returns the expected CPU order of a session: 2 and then 41 for session 1, and 41 and then 2 for session 2. |
| 223 | `def s2_style(p, k, s):` | Starts the function `s2_style`, the rule for a process whose trials have the form of step `S2`. `k` is the kernel and `s` the size text. |
| 224 | `    """4 trials: the kernel at the size, with itself as 1.2 s prefix, 4 windows, uncounted."""` | Description text: the process has 4 trials. Each runs the kernel at the size, with itself as a prefix of 1.2 s, in 4 windows, without counters. |
| 225 | `    t = p["trials"]` | `t`: the trials of the process. |
| 226 | `    return len(t) == 4 and all(` | Starts the result. First condition: exactly 4 trials. |
| 227 | `        x == {"cond": "K=%s\|S=%s" % (k, s), "rep": i + 1, "prev": "-", "pfx": "%s@%s:%d" % (k, s, 4 * x["win_ms"]),` | Second condition, for each trial: it is equal to the expected dictionary. This line: the label with the kernel and the size. The repeat number, 1 to 4. No previous activity. A prefix of the same kernel and size that lasts 4 times the window length. |
| 228 | `              "pred": "-", "tgt": "%s@%s" % (k, s), "nwin": 4, "win_ms": x["win_ms"], "count": "closed", "bins": 0,` | Continues the expected dictionary: no predecessor, the target, 4 windows, the window length as found, counters closed, bins 0. The window length is not fixed here. So the rule also holds for a folder made with a test divisor. |
| 229 | `              "ms": 8 * x["win_ms"]} for i, x in enumerate(t)) and \` | Ends the expected dictionary: the nominal work is 8 window lengths, 4 for the prefix and 4 for the target. The backslash joins the next line to this statement. |
| 230 | `        p["bytes"] == nbytes(s) and p["head"].get("size") == str(nbytes(s)) and p["head"].get("kernel") == k` | Last conditions: the buffer of the process has the size `s`, and the header names that size and the kernel. |

### Rules of the step `XW` (lines 233 to 263)

| Line | Source | Explanation |
|---:|---|---|
| 233 | `# ---------- rules of the steps; each returns a list of defects ----------` | Comment: the rules of the steps start here. Each rule function returns a list of defects. An empty list means that the schedule obeys the rule. |
| 234 | `def xw_rules(procs, cpus, win=300, prev_ms=3000):` | Starts the function `xw_rules`, the rules of step `XW`. `procs`: the processes of one session. `cpus`: the expected CPU order. `win`: the expected window length in ms. `prev_ms`: the expected length of a previous activity in ms. The two defaults are the real values. A folder made with a test divisor has smaller ones. |
| 235 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 236 | `    if len(procs) != 28:` | Rule: the step has 28 processes. |
| 237 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 238 | `    for b in range(4):` | Starts the loop over the 4 blocks of 7 processes. |
| 239 | `        block = procs[7 * b:7 * b + 7]` | `block`: the 7 processes of this block. |
| 240 | `        r, cpu = b // 2 + 1, cpus[b % 2]` | `r`: the replicate that the block must have: 1 for the first two blocks and 2 for the last two. `cpu`: the CPU that it must have: the first CPU of the session for the blocks 0 and 2, the second for the blocks 1 and 3. |
| 241 | `        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):` | Rule: every process of the block runs on that CPU and names that replicate in its header. |
| 242 | `            bad.append("block %d: CPU or rep_set" % b)` | If not: notes a defect of the CPU or of `rep_set` in this block. |
| 243 | `        if sorted(p["head"].get("wcond") for p in block) != sorted(XW):` | Rule: the block holds each of the 7 conditions exactly once. The condition of a process is the header value `wcond`. |
| 244 | `            bad.append("block %d: does not hold every condition once" % b)` | If not: notes the defect. |
| 245 | `    for p in procs:` | Starts a loop over all processes. |
| 246 | `        name = p["head"].get("wcond")` | `name`: the condition of the process, from its plan header. |
| 247 | `        if name not in XW:` | A name that is not one of the 7 conditions. |
| 248 | `            bad.append("process %d: wcond" % p["idx"])` | Notes a defect of `wcond` for this process. |
| 249 | `            continue` | Goes on with the next process. |
| 250 | `        k, s, prev = XW[name]` | `k`, `s`, `prev`: the kernel, the size and the previous activity that this condition must have. |
| 251 | `        want = {"cond": "K=%s\|S=%s\|prev=%s" % (k, s, prev or "none"), "rep": 1,` | `want`: the one trial that the process must have, as a dictionary. This line: the condition label with the kernel, the size and the previous activity (or `none`), and the repeat number 1. |
| 252 | `                "prev": "%s:%d" % (prev, prev_ms) if prev else "-", "pfx": "-", "pred": "-", "tgt": "%s@%s" % (k, s),` | Continues the dictionary: the previous activity with its length in ms, or `-` when the condition has none. No prefix and no predecessor. The target is the kernel at the size. |
| 253 | `                "nwin": 100, "win_ms": win, "count": "closed", "bins": 0, "ms": 100 * win + (prev_ms if prev else 0)}` | Ends the dictionary: 100 windows of `win` ms, counters closed, bins 0. The nominal work is 100 windows plus the previous activity when there is one. With the real values that is 30000 ms or 33000 ms. |
| 254 | `        if p["trials"] != [want]:` | Rule: the process has exactly this one trial. |
| 255 | `            bad.append("process %d (%s): trial" % (p["idx"], name))` | If not: notes a defect of the trial. |
| 256 | `        if p["bytes"] != nbytes(s) or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)) \` | Rules for the rest of the process: the buffer has the size of the condition, and the header names the kernel and that size in bytes. The backslash joins the next line to this statement. |
| 257 | `                or p["head"].get("prev") != (prev or "none") or p["extra"] or not p["tag"].startswith(name + "-"):` | Continues the rules: the header value `prev` is the previous activity or `none`, the `args` hold no added option, and the tag starts with the name of the condition and a hyphen. |
| 258 | `            bad.append("process %d (%s): bytes, header, args or tag" % (p["idx"], name))` | If not: notes a defect of the bytes, the header, the `args` or the tag. |
| 259 | `    if len({tuple(p["head"].get("wcond") for p in procs[7 * b:7 * b + 7]) for b in range(4)}) < 2:` | Rule: at least two of the 4 blocks have different orders of the conditions. The set comprehension keeps each different order once. |
| 260 | `        bad.append("the condition order is the same in every block")` | If not: notes that the condition order is the same in every block. That would show that the conditions are not shuffled. |
| 261 | `    return bad` | Returns the list of defects. |

### Rules of the counter steps `XCA`, `XCB` and `XCC` (lines 264 to 297)

| Line | Source | Explanation |
|---:|---|---|
| 264 | `def xc_rules(procs, cpus, evset, win=300):` | Starts the function `xc_rules`, the rules of a counter step. `evset` is the letter of the event set that the step must use. `win`: the expected window length in ms. |
| 265 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 266 | `    if len(procs) != 18:` | Rule: the step has 18 processes. |
| 267 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect, with the count found. |
| 268 | `    if [k for k, _ in itertools.groupby(p["cpu"] for p in procs)] != [cpus[0], cpus[1], cpus[0], cpus[1]]:` | Rule: when equal neighbours are merged, the CPUs of the processes are the first CPU, the second, the first and the second. `itertools.groupby` merges each run of equal neighbours. So the step has four CPU blocks. |
| 269 | `        bad.append("CPU blocks are not first, second, first, second")` | If not: notes that the CPU blocks do not have this order. |
| 270 | `    want = collections.Counter()` | `want`: the expected number of processes for each combination of CPU, kernel, size and number of windows. It is empty at first. |
| 271 | `    for cpu in cpus:` | Starts a loop over the two CPUs. |
| 272 | `        for k in ("read", "asmread", "oldread"):` | Starts a loop over the three kernels of the long cells. |
| 273 | `            want[cpu, k, "8M", 100] = 2` | Expected: 2 processes of this kernel at 8 MiB with 100 windows on this CPU. |
| 274 | `        for s in ("1M", "32K", "16M"):` | Starts a loop over the three sizes of the short cells. |
| 275 | `            want[cpu, "read", s, 20] = 1` | Expected: 1 process of `read` at this size with 20 windows on this CPU. |
| 276 | `    got = collections.Counter()` | `got`: the same counts as found in the schedule. |
| 277 | `    for p in procs:` | Starts a loop over all processes. |
| 278 | `        t = p["trials"][0]` | `t`: the first trial of the process. |
| 279 | `        k, s = t["tgt"].split("@")` | `k`, `s`: the kernel and the size text of its target. |
| 280 | `        got[p["cpu"], k, s, t["nwin"]] += 1` | Counts the process under its CPU, kernel, size and number of windows. |
| 281 | `        if p["trials"] != [{"cond": "K=%s\|S=%s\|count=read" % (k, s), "rep": 1, "prev": "-", "pfx": "-", "pred": "-",` | Rule: the process has exactly one trial, equal to the expected dictionary. This line: the label with the kernel, the size and `count=read`, the repeat number 1, and no phase before the target. |
| 282 | `                            "tgt": t["tgt"], "nwin": t["nwin"], "win_ms": win, "count": "read", "bins": 0,` | Continues the dictionary: the target and the number of windows as found, the window length `win`, the counter mode `read`, and bins 0. |
| 283 | `                            "ms": t["nwin"] * win}]:` | Ends the dictionary: the nominal work is the number of windows times the window length. |
| 284 | `            bad.append("process %d: trial" % p["idx"])` | If not: notes a defect of the trial. |
| 285 | `        if p["bytes"] != nbytes(s) or p["head"].get("evset") != evset or p["head"].get("kernel") != k:` | Rule: the buffer has the size of the target, and the header names the event set of the step and the kernel. |
| 286 | `            bad.append("process %d: bytes or header" % p["idx"])` | If not: notes a defect of the bytes or of the header. |
| 287 | `        if p["extra"] != " --pmu-type 11 --events " + EVENTS[evset]:` | Rule: the added options of the `args` are exactly `--pmu-type 11` and `--events` with the 6 events of this set, as `EVENTS` of this file lists them. |
| 288 | `            bad.append("process %d: event set in args" % p["idx"])` | If not: notes a defect of the event set in the `args`. |
| 289 | `    if got != want:` | Rule: the counts found are the expected counts. So each CPU has 2 processes of each long cell and 1 of each short cell, and nothing else. |
| 290 | `        bad.append("kernels, sizes and window counts per CPU")` | If not: notes a defect of the kernels, sizes and window counts per CPU. |
| 291 | `    for b, cpu in enumerate([cpus[0], cpus[1], cpus[0], cpus[1]]):` | Starts a loop over the four blocks, each with its CPU. |
| 292 | `        block = [p for p in procs if p["cpu"] == cpu and p["head"].get("rep_set") == str(b // 2 + 1)]` | `block`: the processes on this CPU whose header names the replicate of this block: 1 for the blocks 0 and 1, 2 for the blocks 2 and 3. |
| 293 | `        if sorted(p["trials"][0]["tgt"] for p in block if p["trials"][0]["nwin"] == 100) != ["asmread@8M", "oldread@8M", "read@8M"]:` | Rule: the long processes of the block, those with 100 windows, are `asmread`, `oldread` and `read` at 8 MiB, once each. |
| 294 | `            bad.append("block %d: the three 8M kernels are not there once each" % b)` | If not: notes that the three 8 MiB kernels are not there once each in this block. |
| 295 | `    return bad` | Returns the list of defects. |

### Rules of the step `XN` (lines 298 to 345)

| Line | Source | Explanation |
|---:|---|---|
| 298 | `def xn_rules(procs, cpus):` | Starts the function `xn_rules`, the rules of step `XN`. |
| 299 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 300 | `    if len(procs) != 144:` | Rule: the step has 144 processes. |
| 301 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 302 | `    sets = collections.defaultdict(lambda: collections.defaultdict(list))` | `sets`: for each pair of size and CPU, and for each replicate set, a list in schedule order. A missing entry is created at its first use. |
| 303 | `    for p in procs:` | Starts the loop over the processes in schedule order. |
| 304 | `        h = p["head"]` | `h`: the header of the plan. |
| 305 | `        k, s = h.get("kernel"), p["tag"].split("-")[1]` | `k`: the kernel from the header. `s`: the size text from the tag, its second part. |
| 306 | `        if k not in XN_KERNELS or s not in XN_SIZES or not s2_style(p, k, s):` | Rule: the kernel is one of the 4 kernels of the family, the size is one of the 3 sizes, and the process passes `s2_style` for them. |
| 307 | `            bad.append("process %d: not 4 trials of one kernel of the family with itself as prefix" % p["idx"])` | If not: notes that the process does not have 4 trials of one kernel of the family with itself as the prefix. |
| 308 | `        if p["order"] != HEAD_S2 or p["extra"]:` | Rule: the header keys are those of `HEAD_S2`, in that order, and the process has no added option. |
| 309 | `            bad.append("process %d: header keys or args" % p["idx"])` | If not: notes the defect. |
| 310 | `        sets[s, p["cpu"]][int(h.get("rep_set", 0))].append(k)` | Adds the kernel of the process to its list. The size comes from the tag, the CPU from the schedule row, and the replicate set from the plan header. |
| 311 | `    assign = set()` | `assign`: the different tables of orders that were seen, one table per size and CPU. |
| 312 | `    if len(sets) != 6:` | Rule: there are 6 pairs of size and CPU, 3 sizes times 2 CPUs. |
| 313 | `        bad.append("sizes and CPUs")` | If not: notes the defect `sizes and CPUs`. |
| 314 | `    for (s, cpu), orders in sets.items():` | Starts the loop over the pairs of size and CPU. |
| 315 | `        o = [tuple(orders[r]) for r in sorted(orders)]` | `o`: the orders of the replicate sets of this pair, sorted by the set number. |
| 316 | `        if sorted(orders) != [1, 2, 3, 4, 5, 6] or any(sorted(x) != sorted(XN_KERNELS) for x in o):` | Rule: the pair has the replicate sets 1 to 6, and every set holds each of the 4 kernels once. |
| 317 | `            bad.append("size %s cpu %d: not 6 sets of the 4 kernels" % (s, cpu))` | If not: notes that this size and CPU does not have 6 sets of the 4 kernels. |
| 318 | `            continue` | Goes on with the next pair of size and CPU. |
| 319 | `        if len(set(o)) != 6:` | Rule: the 6 kernel orders of the pair are all different. |
| 320 | `            bad.append("size %s cpu %d: a kernel order occurs twice" % (s, cpu))` | If not: notes that a kernel order occurs twice. |
| 321 | `        pos = collections.Counter((k, i) for x in o for i, k in enumerate(x))` | `pos`: how often each item stands at each position, over the 6 sets. |
| 322 | `        if len(pos) != 16 or not set(pos.values()) <= {1, 2}:` | Rule: all 16 combinations of a kernel and a position occur, and each occurs once or twice. With 6 sets and 4 positions this is the most equal spread. |
| 323 | `            bad.append("size %s cpu %d: a kernel is not once or twice at each position" % (s, cpu))` | If not: notes that a kernel is not once or twice at each position. |
| 324 | `        assign.add(tuple(o))` | Remembers the table of this size and CPU. |
| 325 | `    if len(assign) < 2:` | Rule: at least two pairs of size and CPU have different tables. |
| 326 | `        bad.append("every size and CPU uses the same kernel orders")` | If not: notes that every size and CPU uses the same kernel orders. That would show that the tables are not drawn at random for each size and CPU. |
| 327 | `    size_orders = set()` | `size_orders`: the different size orders of the sets. |
| 328 | `    for r in range(6):` | Starts the loop over the 6 replicate sets, by their place in the schedule. |
| 329 | `        block = procs[24 * r:24 * r + 24]` | `block`: the 24 processes of this set: 3 sizes times 2 CPUs times 4 kernels. |
| 330 | `        if any(p["head"].get("rep_set") != str(r + 1) for p in block):` | Rule: every process of the block names this set in its header. So the sets follow each other and do not mix. |
| 331 | `            bad.append("block %d: rep_set" % (r + 1))` | If not: notes a defect of the `rep_set` value of this block. |
| 332 | `        sizes = []` | `sizes`: the sizes of the block in schedule order. |
| 333 | `        for g in range(3):` | Starts a loop over the 3 size groups of the block. |
| 334 | `            eight = block[8 * g:8 * g + 8]` | `eight`: the 8 processes of one size group. |
| 335 | `            if len({p["bytes"] for p in eight}) != 1 or [p["cpu"] for p in eight] != [cpus[0]] * 4 + [cpus[1]] * 4:` | Rule: the 8 processes have one buffer size, and their CPUs are 4 times the first CPU of the session and then 4 times the second. |
| 336 | `                bad.append("block %d group %d: size or CPU order" % (r + 1, g))` | If not: notes a defect of the size or of the CPU order of this group. |
| 337 | `            sizes.append(eight[0]["bytes"])` | Adds the size of this group. |
| 338 | `        if len(set(sizes)) != 3:` | Rule: the three groups of the block have three different sizes. |
| 339 | `            bad.append("block %d: a size is missing" % (r + 1))` | If not: notes that a size is missing in this block. |
| 340 | `        size_orders.add(tuple(sizes))` | Remembers the size order of this block. |
| 341 | `    if len(size_orders) < 2:` | Rule: at least two blocks have different size orders. |
| 342 | `        bad.append("the size order is the same in every block")` | If not: notes that the size order is the same in every block. That would show that the sizes are not shuffled. |
| 343 | `    return bad` | Returns the list of defects. |

### Rules of the step `XF` (lines 346 to 367)

| Line | Source | Explanation |
|---:|---|---|
| 346 | `def xf_rules(procs, cpus):` | Starts the function `xf_rules`, the rules of step `XF`. |
| 347 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 348 | `    if len(procs) != 90:` | Rule: the step has 90 processes. |
| 349 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect, with the count found. |
| 350 | `    orders = set()` | `orders`: the different cell orders of the blocks. |
| 351 | `    for b in range(6):` | Starts the loop over the 6 blocks of 15 processes. |
| 352 | `        block = procs[15 * b:15 * b + 15]` | `block`: the 15 processes of this block. |
| 353 | `        r, cpu = b // 2 + 1, cpus[b % 2]` | `r`: the replicate that the block must have: 1, 1, 2, 2, 3, 3. `cpu`: the CPU that it must have: the first CPU of the session for the blocks 0, 2 and 4, the second for the others. |
| 354 | `        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):` | Rule: every process of the block runs on that CPU and names that replicate in its header. |
| 355 | `            bad.append("block %d: CPU or rep_set" % b)` | If not: notes a defect of the CPU or of `rep_set` in this block. |
| 356 | `        cells = [(p["head"].get("kernel"), p["tag"].split("-")[1]) for p in block]` | `cells`: the cell of each process of the block: the kernel from the header and the size text from the tag. |
| 357 | `        if sorted(cells) != sorted(XF_CELLS):` | Rule: the block holds each of the 15 cells exactly once. |
| 358 | `            bad.append("block %d: does not hold every kernel and size once" % b)` | If not: notes the defect. |
| 359 | `        orders.add(tuple(cells))` | Remembers the cell order of this block. |
| 360 | `    for p in procs:` | Starts a loop over all processes. |
| 361 | `        if not s2_style(p, p["head"].get("kernel"), p["tag"].split("-")[1]) or p["order"] != HEAD_S2 or p["extra"]:` | Rule: the process passes `s2_style` for its kernel and size, its header keys are those of `HEAD_S2` in that order, and the `args` hold no added option. |
| 362 | `            bad.append("process %d: trials, header keys or args" % p["idx"])` | If not: notes a defect of the trials, the header keys or the `args`. |
| 363 | `    if len(orders) != 6:` | Rule: the 6 blocks have 6 different cell orders. |
| 364 | `        bad.append("two blocks have the same order")` | If not: notes that two blocks have the same order. That would show that the cells are not shuffled for each block. |
| 365 | `    return bad` | Returns the list of defects. |

### `schedule_checks`: the generator runs, the validator can fail, counts and report (lines 368 to 415)

| Line | Source | Explanation |
|---:|---|---|
| 368 | `def schedule_checks(tmp):` | Starts the function `schedule_checks`. It holds all checks of the generator. |
| 369 | `    a, b, c = (os.path.join(tmp, n) for n in ("a", "b", "c"))` | `a`, `b`, `c`: three output folders in the temporary folder `tmp`. |
| 370 | `    r = gen(a)` | Runs the generator with its default options into the folder `a`. |
| 371 | `    check("schedule9.py runs with status 0", r.returncode == 0, r.stderr)` | Check: the generator ends with exit status 0. So the balance check of the generator itself passed. The detail for a failure is its error output. |
| 372 | `    tree, errors = load(a)` | Reads the generated folder and collects the format defects. |
| 373 | `    check("every schedule row and plan file obeys the format and the plan grammar", not errors, errors[:3])` | Check: `load` found no defect. So every schedule row has the right form, and every plan file passes the validator of this file. This matters: the runner ends with status 2 for a plan with a defect. |
| 374 | `    check("the 7 steps exist in session 1; session 2 has the same steps without XEV",` | Starts a check: session 1 has the 7 steps, and session 2 has the same steps without `XEV`. |
| 375 | `          sorted(tree) == sorted([(s, 1) for s in TABLE] + [(s, 2) for s in TABLE if s != "XEV"]), sorted(tree))` | The test: the pairs of step and session that were read are exactly the 7 steps of `TABLE` for session 1 and the 6 steps without `XEV` for session 2. So no schedule is missing, and no other schedule was written. |
| 377 | `    # The validator itself rejects defective plans.` | Comment: the next checks show that the validator itself rejects plans with a defect. |
| 378 | `    good = open(os.path.join(a, "s1", "XW", "0000.plan")).read()` | `good`: the text of the first plan of step `XW` in session 1. |
| 379 | `    w1 = [p for p in tree["XW", 1] if p["head"]["wcond"] == "W1"][0]` | `w1`: the first process of that step with the condition `W1`, which has a previous activity. |
| 380 | `    good1 = open(os.path.join(a, "s1", "XW", w1["plan"])).read()` | `good1`: the text of its plan. It holds the phase text `oldread@8M:3000`. |
| 381 | `    line = good.split("\n")[3]` | `line`: the fourth line of `good`, its one trial line. |
| 382 | `    bad = {"rep not 1": good.replace(line, line.replace(" 1 - ", " 2 - ", 1)),` | `bad`: a dictionary of plan texts with one defect each. The key names the defect. First entry: the repeat number of the trial is 2 in place of 1. |
| 383 | `           "size above bytes": good1.replace("oldread@8M:3000", "oldread@16M:3000"),` | The previous activity has the size 16 MiB, which is above the buffer of 8 MiB. |
| 384 | `           "unknown kernel": good1.replace("oldread@8M:3000", "copy@8M:3000"),` | The previous activity names the kernel `copy`, which is not one of `READ_KERNELS`. |
| 385 | `           "previous activity without a duration": good1.replace("oldread@8M:3000", "oldread@8M"),` | The previous activity has no duration. |
| 386 | `           "two spaces": good.replace(line, line.replace(" ", "  ", 1)),` | Two blanks in place of the first blank of the trial line. |
| 387 | `           "trial number": good.replace("\n0 ", "\n1 ", 1),` | The first trial has the number 1 in place of 0. |
| 388 | `           "wrong first line": good.replace("plan v1", "plan v2"),` | The first line names version 2 of the format. |
| 389 | `           "count word": good.replace(line, line.replace("closed", "shut")),` | The counter mode is the word `shut`, which does not exist. |
| 390 | `           "comma in cond": good.replace(line, line.replace("\|", ",", 1)),` | A comma in place of the first vertical bar of the condition label. |
| 391 | `           "blank in cond": good.replace(line, line.replace("\|", " ", 1)),` | A blank in place of the first vertical bar. The trial line then has 12 fields. |
| 392 | `           "header lacks seed": good.replace(" seed=", " sead=")}` | The header key `seed` is written `sead`, so the required key is missing. The brace ends the dictionary. |
| 393 | `    check("validator accepts generated plans", not rejected(good) and not rejected(good1))` | Check: the validator accepts the two plans as the generator wrote them. This is the control for the checks that follow: a rejection there comes from the defect alone. |
| 394 | `    for name, text in bad.items():` | Starts a loop over the damaged plans. |
| 395 | `        check("validator rejects: " + name, text not in (good, good1) and rejected(text))` | Check, once per defect: the damaged text really differs from the two good plans, and the validator rejects it. This proves that each of these rules of the validator can fail. A validator that accepts every text would make the format check of line 373 prove nothing. |
| 397 | `    # Counts and nominal work, from the files and from the printed report.` | Comment: the next checks compare the counts and the nominal work with the task. They take them from the files and from the report that the generator prints. |
| 398 | `    for step, (n, tr, sec) in TABLE.items():` | Starts a loop over the steps of `TABLE`. `n`: the expected processes. `tr`: the expected trials per process. `sec`: the expected nominal work in seconds. |
| 399 | `        for s in (1, 2):` | Starts a loop over the two sessions. |
| 400 | `            if (step, s) not in tree:` | A step that does not exist in this session. |
| 401 | `                continue` | Skips it. |
| 402 | `            procs = tree[step, s]` | `procs`: the processes of this step and session, as read from the files. |
| 403 | `            ms = sum(proc_ms(p) for p in procs)` | `ms`: the nominal kernel work of the step in ms. The validator of this file computed it from the plan files. |
| 404 | `            check("%s session %d: %d processes of %d trial(s), %.1f s of nominal kernel work" % (step, s, n, tr, sec),` | Starts a check, once per step and session. Its name states the expected values. |
| 405 | `                  len(procs) == n and all(len(p["trials"]) == tr for p in procs) and ms == round(sec * 1000),` | The test of the check: the number of processes, the number of trials of every process and the nominal work in ms are those of `TABLE`. This proves that the files hold the planned task. A wrong count would make a session shorter or longer than planned, and a missing process would leave a condition with too few runs. |
| 406 | `                  (len(procs), ms))` | The detail for a failure: the number of processes and the nominal work that were found. |
| 407 | `            check("%s session %d: the report prints the process count and the nominal work" % (step, s),` | Starts a second check per step and session: the report of the generator prints the process count and the nominal work. |
| 408 | `                  ("\n%s %d %d %d %g\n" % (step, s, n, n * tr, sec)) in r.stdout, r.stdout[:400])` | The test: the output of the generator holds the table row of the step: its name, the session, the processes, the trials of all processes, and the nominal work in seconds. So the printed report agrees with the files. |
| 409 | `    short = copy.deepcopy(tree["XN", 1])` | `short`: an independent copy of the processes of step `XN` in session 1. |
| 410 | `    short[0]["trials"].pop()` | Removes the last trial of the first process of the copy. |
| 411 | `    check("nominal work: a schedule with one trial missing does not give the XN value",` | Starts a check: a schedule with one trial missing does not give the nominal work of `XN`. |
| 412 | `          sum(proc_ms(p) for p in short) != 1382400)` | The test: the sum over the damaged copy is not 1382400 ms. This shows that the comparison of the nominal work in lines 404 to 406 can fail. |
| 413 | `    check("one process at a time is at most 33 s of kernel work (the longest: XW with a previous activity)",` | Starts a check: no process has more than 33 s of nominal kernel work. |
| 414 | `          max(proc_ms(p) for procs in tree.values() for p in procs) == 33000)` | The test: the largest nominal work of one process, over all steps and sessions, is exactly 33000 ms. That is a process of `XW` with a previous activity. This value matters for the run script: it adds `RESERVE` to the longest process of a step to get `MARGIN`. |

### `schedule_checks`: header pairs and CPU order (lines 416 to 443)

| Line | Source | Explanation |
|---:|---|---|
| 416 | `    # Header pairs.` | Comment: the next checks test the header pairs of the plans. |
| 417 | `    check("plan headers: seed is one value per step and session, test=0",` | Starts a check: inside one step and session every plan has the same seed, and every plan has `test=0`. |
| 418 | `          all(len({p["head"]["seed"] for p in procs}) == 1 and all(p["head"]["test"] == "0" for p in procs)` | The test: the set of the seed values of a step and session has one member, and the `test` value of every plan is `0`. |
| 419 | `              for procs in tree.values()))` | The loop of the test runs over all steps and sessions. So a plan file shows which random order it belongs to, and no test plan with shortened durations is among the real plans. |
| 420 | `    check("plan headers: the seeds of the steps and sessions differ",` | Starts a check: the seeds of the steps and sessions differ. |
| 421 | `          len({procs[0]["head"]["seed"] for procs in tree.values()}) == 13)` | The test: the seeds of the 13 pairs of step and session are 13 different values. So each step and session has a random order of its own. |
| 422 | `    check("plan headers: kernel and size name the target of every trial",` | Starts a check: the header pairs `kernel` and `size` name the target of every trial. |
| 423 | `          all(all(t["tgt"].split("@")[0] == p["head"]["kernel"] and nbytes(t["tgt"].split("@")[1]) == int(p["head"]["size"])` | The test: for each trial, the kernel of the target is the header value `kernel`, and the size of the target in bytes is the header value `size`. |
| 424 | `                  and int(p["head"]["size"]) == p["bytes"] for t in p["trials"])` | Continues the test: the header value `size` is also the buffer size of the process. |
| 425 | `              for procs in tree.values() for p in procs))` | The loops of the test run over every process of every step and session. This matters: the runner copies the header pairs into its output, so they must describe what the process really runs. |
| 426 | `    check("cond labels are key=value pairs that agree with the trial (kernel, size, counter mode, previous activity)",` | Starts a check: every condition label is made of pairs `key=value` that agree with the trial: the kernel, the size, the counter mode and the previous activity. |
| 427 | `          all(dict(x.split("=") for x in t["cond"].split("\|")).get("count", "closed") == t["count"]` | The test, first half: the label is split at the vertical bars into pairs `key=value`. Its `count` value, or `closed` when the label has none, is the counter mode of the trial. |
| 428 | `              and "K=%s\|S=%s" % tuple(t["tgt"].split("@")) == "\|".join(t["cond"].split("\|")[:2])` | Second half: the first two pairs of the label are `K=` with the kernel of the target and `S=` with its size. |
| 429 | `              and dict(x.split("=") for x in t["cond"].split("\|")).get("prev", "none") ==` | Third part: the `prev` value of the label, or `none` when the label has none, is compared with the value of the next line. |
| 430 | `              (t["prev"].split(":")[0] if t["prev"] != "-" else "none")` | The value that it must equal: the kernel and the size of the previous activity of the trial, without the duration, or `none` when the trial has no previous activity. This matters: the runner prints the label in its output row of the trial, so the label must say what the trial really runs. |
| 431 | `              for procs in tree.values() for p in procs for t in p["trials"]))` | The loops run over every trial of every process of every step and session. |
| 433 | `    # CPU order of the sessions.` | Comment: the next checks test the CPU order of the sessions. |
| 434 | `    for (step, s), procs in sorted(tree.items()):` | Starts a loop over all steps and sessions, in sorted order. |
| 435 | `        if step == "XEV":` | The step `XEV`, which runs on CPU 2 only. |
| 436 | `            continue` | Skips it. |
| 437 | `        check("%s session %d: CPU order %d then %d" % ((step, s) + cpus_of(s)), cpu_blocks(procs, *cpus_of(s)))` | Check, per step and session: the CPUs of the schedule alternate in the order of that session, 2 and then 41 in session 1, 41 and then 2 in session 2. The design file `tackle-8mb.md`, the plan of the investigation, asks that the second session reverses the order of the worker CPUs. |
| 438 | `    check("CPU order rule rejects session 1 read as session 2", not cpu_blocks(tree["XW", 1], 41, 2))` | Check: the rule `cpu_blocks` rejects the schedule of `XW` in session 1 when it is tested with the CPU order of session 2. This shows that the rule can fail. |
| 439 | `    check("session 2 is not session 1 with the CPUs exchanged (own random order)",` | Starts a check: the schedule of session 2 is not the schedule of session 1 with the two CPUs exchanged. |
| 440 | `          [p["head"]["wcond"] for p in tree["XW", 1]] != [p["head"]["wcond"] for p in tree["XW", 2]]` | The test, first half: the sequence of the conditions of `XW` differs between the two sessions. |
| 441 | `          and [p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in tree["XF", 1]] !=` | Second half: the tags of `XF` in session 1, with the CPU name in each tag replaced by the letter `c`, are compared with the list of the next line. |
| 442 | `          [p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in tree["XF", 2]])` | The same list for session 2. The two lists must differ. So session 2 has a random order of its own and is not session 1 with the two CPUs exchanged. |

### `schedule_checks`: steps `XW`, `XCA`, `XCB`, `XCC` and `XEV` (lines 444 to 488)

| Line | Source | Explanation |
|---:|---|---|
| 444 | `    # XW.` | Comment: the checks of step `XW` start here. |
| 445 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 446 | `        d = xw_rules(tree["XW", s], cpus_of(s))` | `d`: the defects that `xw_rules` finds in the schedule of this session. |
| 447 | `        check("XW session %d: 7 conditions once per replicate block and CPU, trials as specified" % s, not d, d[:3])` | Check, per session: no defect. So each block of a replicate and a CPU holds the 7 conditions once, and every trial is as the task states. The detail shows the first 3 defects. |
| 448 | `    check("XW rules reject the session 1 schedule under the session 2 CPU order", bool(xw_rules(tree["XW", 1], (41, 2))))` | Check: the rules reject the schedule of session 1 when they expect the CPU order of session 2. So the rule for the CPU order can fail. |
| 449 | `    m = copy.deepcopy(tree["XW", 1])` | `m`: an independent copy of the schedule of session 1. The next lines damage it. |
| 450 | `    m[0]["trials"][0]["nwin"] = 99` | Changes the number of windows of the first process to 99. |
| 451 | `    check("XW rules reject a trial of 99 windows", bool(xw_rules(m, (2, 41))))` | Check: the rules reject a trial of 99 windows. So a wrong number of windows cannot pass. |
| 452 | `    m = copy.deepcopy(tree["XW", 1])` | A new copy. |
| 453 | `    m[0], m[7] = m[7], m[0]` | Exchanges the first process of block 0 with the first process of block 1. The two blocks run on different CPUs. |
| 454 | `    check("XW rules reject two processes exchanged between blocks", bool(xw_rules(m, (2, 41))))` | Check: the rules reject two processes that were exchanged between blocks. |
| 455 | `    m = copy.deepcopy(tree["XW", 1])` | A new copy. |
| 456 | `    for p in m:` | Starts a loop over its processes. |
| 457 | `        if p["head"]["wcond"] == "W1":` | A process of the condition `W1`. |
| 458 | `            p["trials"][0]["prev"] = "-"` | Removes its previous activity. |
| 459 | `    check("XW rules reject W1 without its previous activity", bool(xw_rules(m, (2, 41))))` | Check: the rules reject `W1` without its previous activity. So a plan that leaves out the 3 s of old read cannot pass. |
| 460 | `    fixed = sorted(tree["XW", 1], key=lambda p: (int(p["head"]["rep_set"]), p["cpu"], p["head"]["wcond"]))` | `fixed`: the processes of session 1 sorted by the replicate, the CPU and the name of the condition. So every block has the order `W0` to `W6`. |
| 461 | `    check("XW rules reject a fixed condition order in every block",` | Starts a check: the rules reject a schedule in which every block has the same condition order. |
| 462 | `          xw_rules(fixed, (2, 41)) == ["the condition order is the same in every block"], xw_rules(fixed, (2, 41))[:3])` | The test: the rules report exactly this one defect and no other. So the rule for the shuffle can fail, and the sorted copy is valid in every other way. |
| 464 | `    # XCA, XCB, XCC, XEV.` | Comment: the checks of the three counter steps and of `XEV` start here. |
| 465 | `    for step, evset in (("XCA", "A"), ("XCB", "B"), ("XCC", "C")):` | Starts a loop over the three counter steps, each with the letter of its event set. |
| 466 | `        for s in (1, 2):` | Starts a loop over the two sessions. |
| 467 | `            d = xc_rules(tree[step, s], cpus_of(s), evset)` | `d`: the defects that `xc_rules` finds for this step and session. |
| 468 | `            check("%s session %d: per CPU 2 x 3 kernels at 8M (100 windows) and read at 1M, 32K, 16M (20 windows), "` | Starts a check per step and session. Its name states the task: per CPU 2 processes of each of the 3 kernels at 8 MiB with 100 windows, and `read` at 1 MiB, 32 KiB and 16 MiB with 20 windows. |
| 469 | `                  "count read, event set %s in args" % (step, s, evset), not d, d[:3])` | Ends the name: the counter mode `read` and the event set in the `args`. The test: no defect. So every process of a counter step counts the events of the set of that step. |
| 470 | `    check("XC rules reject the event set of another step", bool(xc_rules(tree["XCA", 1], (2, 41), "B")))` | Check: the rules reject the schedule of `XCA` when they expect the event set B. |
| 471 | `    m = copy.deepcopy(tree["XCA", 1])` | `m`: an independent copy of the schedule of `XCA` in session 1. |
| 472 | `    m[0]["trials"][0]["count"] = "closed"` | Sets the counter mode of the first process to `closed`. |
| 473 | `    check("XC rules reject a trial with count closed", bool(xc_rules(m, (2, 41), "A")))` | Check: the rules reject a trial with the counter mode `closed`. |
| 474 | `    check("the event sets: 6 events each, names below 32 characters, 18 different names and codes",` | Starts a check of the event sets of this file: 6 events each, names below 32 characters, and 18 different names and codes. |
| 475 | `          all(len(v.split(",")) == 6 and all(re.match(r"^[a-z0-9_]{1,31}=0x[0-9a-f]+$", e) for e in v.split(","))` | The test, first part: each set has 6 entries, and each entry matches the pattern: a name of 1 to 31 lower-case letters, digits or `_`, an equals sign, and a hexadecimal number that starts with `0x`. The source `bwx8.c` keeps an event name in a field of 32 bytes. So a name can have at most 31 characters. |
| 476 | `              for v in EVENTS.values())` | The loop of that test runs over the three sets. |
| 477 | `          and len({e.split("=")[0] for v in EVENTS.values() for e in v.split(",")}) == 18` | Second part: the names of all events are 18 different names. |
| 478 | `          and len({int(e.split("=")[1], 16) for v in EVENTS.values() for e in v.split(",")}) == 18)` | Third part: the codes, read as hexadecimal numbers, are 18 different values. So no event is counted in two sets. |
| 479 | `    ev = tree["XEV", 1]` | `ev`: the processes of step `XEV` in session 1. |
| 480 | `    check("XEV: CPU 2 only, one process per event set, one trial read@8M, 3 windows of 300 ms, count read",` | Starts a check of `XEV`: CPU 2 only, one process per event set, and one trial of `read` at 8 MiB with 3 windows of 300 ms and the counter mode `read`. |
| 481 | `          [p["cpu"] for p in ev] == [2, 2, 2] and [p["head"]["evset"] for p in ev] == ["A", "B", "C"]` | The test, first part: the three processes run on CPU 2, and their header values `evset` are A, B and C in this order. |
| 482 | `          and all(p["extra"] == " --pmu-type 11 --events " + EVENTS[p["head"]["evset"]] and p["bytes"] == 8 << 20` | Second part, for each process: the added options are `--pmu-type 11` and `--events` with its set, and the buffer has 8 MiB (`8 << 20` bytes). |
| 483 | `                  and p["trials"] == [{"cond": "K=read\|S=8M\|count=read", "rep": 1, "prev": "-", "pfx": "-", "pred": "-",` | Third part: the one trial equals the expected dictionary. This line: the label, the repeat number 1, and no phase before the target. |
| 484 | `                                       "tgt": "read@8M", "nwin": 3, "win_ms": 300, "count": "read", "bins": 0, "ms": 900}]` | Ends the dictionary: the target `read@8M`, 3 windows of 300 ms, the counter mode `read`, bins 0, and 900 ms of nominal work. |
| 485 | `                  for p in ev))` | The loop of the second and the third part runs over the three processes. |
| 486 | `    check("XEV: session 2 has no schedule, no plan folder and no marker",` | Starts a check: session 2 has no schedule, no plan folder and no `.watch` file of `XEV`. |
| 487 | `          not [f for f in os.listdir(os.path.join(a, "s2")) if f.startswith("XEV")])` | The test: no name in the folder `s2` starts with `XEV`. |

### `schedule_checks`: steps `XN` and `XF` (lines 489 to 525)

| Line | Source | Explanation |
|---:|---|---|
| 489 | `    # XN.` | Comment: the checks of step `XN` start here. |
| 490 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 491 | `        d = xn_rules(tree["XN", s], cpus_of(s))` | `d`: the defects that `xn_rules` finds in the schedule of this session. |
| 492 | `        check("XN session %d: S2-style trials, header keys as S2, 6 different kernel orders per size and CPU, "` | Starts a check per session. Its name states the task: trials of the `S2` form, the header keys of `S2`, and 6 different kernel orders per size and CPU. |
| 493 | `              "each kernel once or twice at each position, block order as S2" % s, not d, d[:3])` | Ends the name: each kernel once or twice at each position, and the block order of `S2`. The test: no defect. So the place of a kernel inside a set is spread over the 4 positions as evenly as 6 sets allow. |
| 494 | `    m = copy.deepcopy(tree["XN", 1])` | `m`: an independent copy of the schedule of session 1. |
| 495 | `    for i in range(0, 144, 4):                       # every set in the order of XN_KERNELS` | Starts a loop over the groups of 4 processes. By the comment every set gets the kernel order of `XN_KERNELS`. |
| 496 | `        for p, k in zip(m[i:i + 4], XN_KERNELS):` | Starts a loop over the 4 processes of the group, each paired with the kernel that it gets. |
| 497 | `            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]` | `s`: the size text from the tag. `ms`: the window length of the first trial. |
| 498 | `            p["head"]["kernel"] = k` | Writes the kernel into the header of the process. |
| 499 | `            for t in p["trials"]:` | Starts a loop over the trials of the process. |
| 500 | `                t.update(cond="K=%s\|S=%s" % (k, s), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))` | Rewrites the label, the prefix and the target of the trial for that kernel. So each process stays valid by itself, and only the order is wrong. |
| 501 | `    d = xn_rules(m, (2, 41))` | `d`: the defects that the rules find in the changed copy. |
| 502 | `    check("XN rules reject a schedule in which every set has one fixed kernel order",` | Starts a check: the rules reject a schedule in which every set has one fixed kernel order. |
| 503 | `          any("occurs twice" in x for x in d) and any("once or twice" in x for x in d), d[:3])` | The test: the defects hold one about an order that occurs twice, and one about the positions. So both balance rules can fail. |
| 504 | `    m = copy.deepcopy(tree["XN", 1])` | A new copy. |
| 505 | `    m[3], m[4] = m[4], m[3]` | Exchanges the processes 3 and 4. Process 3 is the last one of the first CPU in the first size group, and process 4 is the first one of the second CPU. |
| 506 | `    check("XN rules reject CPUs that alternate inside a size", bool(xn_rules(m, (2, 41))))` | Check: the rules reject CPUs that alternate inside a size. |
| 507 | `    m = copy.deepcopy(tree["XN", 1])` | A new copy. |
| 508 | `    m[5]["trials"][0]["pfx"] = "asmread@1M:1200" if m[5]["head"]["kernel"] != "asmread" else "read_nop16@1M:1200"` | Gives the first trial of process 5 a prefix of another kernel: `asmread`, or `read_nop16` when the process itself runs `asmread`. The prefix has the size 1 MiB, which can also differ from the size of the process. |
| 509 | `    check("XN rules reject a prefix of another kernel or size", bool(xn_rules(m, (2, 41))))` | Check: the rules reject a prefix of another kernel or size. So the phase before the target must be the target kernel itself. |
| 510 | `    check("XN rules reject the session 1 schedule under the session 2 CPU order", bool(xn_rules(tree["XN", 1], (41, 2))))` | Check: the rules reject the schedule of session 1 when they expect the CPU order of session 2. So the rule for the CPU order of `XN` can fail. |
| 512 | `    # XF.` | Comment: the checks of step `XF` start here. |
| 513 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 514 | `        d = xf_rules(tree["XF", s], cpus_of(s))` | `d`: the defects that `xf_rules` finds in the schedule of this session. |
| 515 | `        check("XF session %d: 15 kernel and size cells once per replicate block and CPU, S2-style trials, "` | Starts a check per session. Its name states the task: the 15 cells of a kernel and a size once per block of a replicate and a CPU, and trials of the `S2` form. |
| 516 | `              "the order differs between blocks" % s, not d, d[:3])` | Ends the name: the order differs between the blocks. The test: no defect. |
| 517 | `    m = copy.deepcopy(tree["XF", 1])` | `m`: an independent copy of the schedule of session 1. |
| 518 | `    m[0], m[15] = m[15], m[0]` | Exchanges the first process of block 0 with the first process of block 1. |
| 519 | `    check("XF rules reject two processes exchanged between blocks", bool(xf_rules(m, (2, 41))))` | Check: the rules reject two processes that were exchanged between blocks. |
| 520 | `    check("XF: the sizes in bytes are the listed ones (1.5, 2, 2.5, 3, 5, 6, 12, 24, 32, 64 MiB for read)",` | Starts a check: the buffer sizes of `XF` in bytes are the listed ones. |
| 521 | `          sorted({p["bytes"] for p in tree["XF", 1] if p["head"]["kernel"] == "read"}) ==` | The test, first half: the different buffer sizes of the `read` processes, in sorted order, are compared with the list of the next line. |
| 522 | `          [int(x * 1048576) for x in (1.5, 2, 2.5, 3, 5, 6, 12, 24, 32, 64)]` | The 10 expected sizes: 1.5, 2, 2.5, 3, 5, 6, 12, 24, 32 and 64 MiB, each as a number of bytes. |
| 523 | `          and sorted({p["bytes"] for p in tree["XF", 1] if p["head"]["kernel"] == "oldread"}) ==` | Second half: the different buffer sizes of the `oldread` processes are compared with the list of the next line. |
| 524 | `          [x << 20 for x in (2, 3, 6, 12, 32)])` | The 5 expected sizes: 2, 3, 6, 12 and 32 MiB. `x << 20` multiplies by 1048576. This check proves that the two sizes that the generator writes as byte counts, 1572864 and 2621440, are 1.5 MiB and 2.5 MiB. |

### `schedule_checks`: `.watch` files, seeds, `MANIFEST.txt`, saved folder, test divisor (lines 526 to 569)

| Line | Source | Explanation |
|---:|---|---|
| 526 | `    # Marker files of the host sampler.` | Comment: the checks of the `.watch` files start here. The comment calls them the marker files of the host sampler. They are not the marker file of CRB. |
| 527 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 528 | `        sdir = os.path.join(a, "s%d" % s)` | `sdir`: the folder of the session in the generated folder. |
| 529 | `        marks = sorted(f[:-6] for f in os.listdir(sdir) if f.endswith(".watch"))` | `marks`: the names in the session folder that end with `.watch`, without that ending, in sorted order. |
| 530 | `        check("session %d: empty .watch markers for XW, XCA, XCB, XCC and for no other step" % s,` | Starts a check per session: empty `.watch` files exist for `XW`, `XCA`, `XCB` and `XCC`, and for no other step. |
| 531 | `              marks == WATCH_STEPS and all(os.path.getsize(os.path.join(sdir, m + ".watch")) == 0 for m in marks), marks)` | The test: the names are exactly the four of `WATCH_STEPS`, and each file has a size of 0 bytes. So the run script starts the host sampler for these four steps and for no other. |
| 533 | `    # Determinism.` | Comment: the next checks test that the output is fully fixed by the options. |
| 534 | `    gen(b)` | Runs the generator a second time with the default options, into the folder `b`. |
| 535 | `    r3 = gen(c, "--seed", "7")` | Runs it a third time with `--seed 7`, into the folder `c`. |
| 536 | `    ta, tb, tc = tree_bytes(a), tree_bytes(b), tree_bytes(c)` | `ta`, `tb`, `tc`: the files of the three folders, each as a dictionary from the path to the bytes. |
| 537 | `    nfiles = 1 + sum(TABLE[s][0] + 1 for s in TABLE) + sum(TABLE[s][0] + 1 for s in TABLE if s != "XEV") + 8` | `nfiles`: the expected number of files in the output folder, 657. It is 1 for `MANIFEST.txt`, then for each step of session 1 its plan files and its schedule file, then the same for session 2 without `XEV`, then 8 `.watch` files. |
| 538 | `    check("two runs with one base seed give the same bytes (%d files)" % nfiles, ta == tb and len(ta) == nfiles, len(ta))` | Check: two runs with the same base seed give the same files with the same bytes, and the number of files is `nfiles`. This proves that a schedule can be made again from its seed. The order that ran can then be checked later. |
| 539 | `    check("another base seed gives the same file names and other bytes",` | Starts a check: another base seed gives the same file names and other bytes. |
| 540 | `          r3.returncode == 0 and sorted(ta) == sorted(tc) and ta != tc` | The test, first half: the third run ended with status 0, the two folders have the same file names, and their contents differ. |
| 541 | `          and all(ta["s1/%s.tsv" % s] != tc["s1/%s.tsv" % s] for s in ("XW", "XCA", "XN", "XF")))` | Second half: the schedule files of `XW`, `XCA`, `XN` and `XF` in session 1 each differ between the two base seeds. So the seed changes the order of each of these steps. |
| 542 | `    check("the base seed and the seed of every step and session are saved in MANIFEST.txt",` | Starts a check: the base seed and the seed of every step and session are saved in `MANIFEST.txt`. |
| 543 | `          b"base_seed=20261115\ntest_divisor=1\n" in ta["MANIFEST.txt"] and b"base_seed=7\n" in tc["MANIFEST.txt"]` | The test, first half: the manifest of the default run holds the lines `base_seed=20261115` and `test_divisor=1`, and the manifest of the third run holds `base_seed=7`. |
| 544 | `          and all(("seed %s s%d %s\n" % (st, s, procs[0]["head"]["seed"])).encode() in ta["MANIFEST.txt"]` | Second half: for each step and session the manifest holds a line `seed`, the step, the session and the seed that the plan headers carry. |
| 545 | `                  for (st, s), procs in tree.items()))` | The loop of that test runs over all steps and sessions. So the record of the seeds agrees with the plan files. |
| 546 | `    tree7, errors7 = load(c)` | `tree7`, `errors7`: the folder of the third run, read and tested with `load`. |
| 547 | `    check("another base seed keeps the rules (grammar, XW, XN, XF, XCB)",` | Starts a check: with another base seed the rules still hold. |
| 548 | `          not errors7 and not xw_rules(tree7["XW", 2], (41, 2)) and not xn_rules(tree7["XN", 1], (2, 41))` | The test, first half: no format defect, no defect of `XW` in session 2, and no defect of `XN` in session 1. |
| 549 | `          and not xf_rules(tree7["XF", 2], (41, 2)) and not xc_rules(tree7["XCB", 1], (2, 41), "B"))` | Second half: no defect of `XF` in session 2, and no defect of `XCB` in session 1. So the rules do not hold for the default seed alone. |
| 550 | `    saved = os.path.join(X, "sched9")` | `saved`: the folder `sched9` beside this file. It holds the schedules that the run script uses. |
| 551 | `    check("the saved sched9/ beside the scripts is the output of the default base seed",` | Starts a check: the saved folder `sched9` is the output of the generator with the default base seed. |
| 552 | `          os.path.isdir(saved) and tree_bytes(saved) == ta)` | The test: the saved folder exists, and its files are equal to the files that the generator wrote now, name by name and byte by byte. So the schedules that will run are the ones that this test examined. |
| 554 | `    # --test-divisor.` | Comment: the checks of the option `--test-divisor` start here. |
| 555 | `    t = os.path.join(tmp, "t")` | `t`: one more output folder. |
| 556 | `    r6 = gen(t, "--test-divisor", "100")` | Runs the generator with `--test-divisor 100` into `t`. |
| 557 | `    ttree, terr = load(t)` | `ttree`, `terr`: that folder, read and tested with `load`. |
| 558 | `    check("--test-divisor 100: valid plans, test=1, every duration divided by 100, window counts unchanged",` | Starts a check: with the divisor 100 the plans are valid, they carry `test=1`, every duration is divided by 100, and the numbers of windows do not change. |
| 559 | `          r6.returncode == 0 and not terr and sorted(ttree) == sorted(tree)` | The test: the run ended with status 0, there is no format defect, and the steps and sessions are the same as in the real folder. |
| 560 | `          and all(p["head"]["test"] == "1" for pp in ttree.values() for p in pp)` | Continues the test: every plan has `test=1`. |
| 561 | `          and all(sum(proc_ms(p) for p in ttree[k]) * 100 == sum(proc_ms(p) for p in tree[k]) for k in tree)` | Continues the test: for each step and session the nominal work times 100 is the nominal work of the real folder. |
| 562 | `          and all([t_["nwin"] for p in ttree[k] for t_ in p["trials"]] == [t_["nwin"] for p in tree[k] for t_ in p["trials"]]` | Continues the test: the list of the window counts of all trials is the same as in the real folder. |
| 563 | `                  for k in tree)` | The loop of that comparison runs over all steps and sessions. |
| 564 | `          and not xw_rules(ttree["XW", 1], (2, 41), 3, 30), terr[:3])` | Ends the test: the schedule of `XW` passes its rules with a window of 3 ms and a previous activity of 30 ms. These are 300 ms and 3000 ms divided by 100. The detail for a failure is the first 3 format defects. |
| 565 | `    check("--test-divisor 7 is refused (it does not divide 300 ms)",` | Starts a check: the generator refuses the test divisor 7, which does not divide 300 ms. |
| 566 | `          gen(os.path.join(tmp, "u"), "--test-divisor", "7").returncode != 0)` | The test: the generator ends with an exit status other than 0. A window of 300 ms cannot be divided by 7 without a rest. |
| 567 | `    return t` | Returns the folder that was made with the test divisor 100. The later groups of checks use it as their schedule. |

### `bwx8_checks`: every plan through a stand-in `bwx8` (lines 570 to 650)

| Line | Source | Explanation |
|---:|---|---|
| 570 | `# ---------- every plan through the local stand-in bwx8 ----------` | Comment: the checks that put every plan through the local stand-in of `bwx8` start here. |
| 571 | `def bwx8_checks(tmp, sched):` | Starts the function `bwx8_checks`. `sched` is the generated folder with the test divisor 100. So every duration is one hundredth of the real one. |
| 572 | `    allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)` | `allowed`: the CPUs on which this test may run, without the CPUs above 119, in sorted order. |
| 573 | `    d = os.path.join(tmp, "bwx8")` | `d`: the folder `bwx8` in the temporary folder. |
| 574 | `    os.makedirs(d)` | Creates it. |
| 575 | `    binary = os.path.join(d, "bwx8")` | `binary`: the path of the stand-in binary. |
| 576 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-o", binary, os.path.join(X, "bwx8.c")], capture_output=True, text=True)` | Builds the stand-in: `gcc` with the flags of `CFLAGS` compiles the runner source `bwx8.c` of this folder into that binary. |
| 577 | `    if not check("stand-in build of bwx8.c in a temporary folder (flags of build8.sh)", r.returncode == 0, r.stdout + r.stderr):` | Check: the build ends with status 0. The detail for a failure is the output of the compiler. |
| 578 | `        return` | After a failed build: leaves the function. The other checks of this group do not run. |
| 579 | `    if not check("this machine allows CPU 0, CPU 2 and one more CPU below 120", 0 in allowed and 2 in allowed and len(allowed) > 2):` | Check: this machine allows CPU 0, CPU 2 and at least one more CPU below 120. The plans use CPU 2 as a worker CPU. By the note `DECISIONS-bwx8.md` the runner puts its controlling thread on CPU 0 when no option names another CPU. |
| 580 | `        return` | If not: leaves the function. |
| 581 | `    alt = 41 if 41 in allowed else [c for c in allowed if c not in (0, 2)][0]` | `alt`: the CPU that takes the place of CPU 41. It is 41 when this machine allows it. If not, it is the first allowed CPU that is neither 0 nor 2. |
| 582 | `    shutil.copytree(sched, os.path.join(d, "sched9"))` | Copies the generated folder to `sched9` inside `d`. So the plan paths of the `args` column, which start with `sched9/`, are valid in `d`. |
| 583 | `    jobs = []` | `jobs`: the list of the runs to make, one per schedule row. It is empty at first. |
| 584 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 585 | `        sdir = os.path.join(d, "sched9", "s%d" % session)` | `sdir`: the folder of the session in the copy. |
| 586 | `        for name in sorted(f for f in os.listdir(sdir) if f.endswith(".tsv")):` | Starts a loop over the schedule files of the session, in sorted order. |
| 587 | `            step = name[:-4]` | `step`: the file name without the ending `.tsv`. |
| 588 | `            for row in open(os.path.join(sdir, name)).read().split("\n")[1:-1]:` | Starts a loop over the data rows of the schedule. |
| 589 | `                f = row.split("\t")` | Splits the row at the tabs. |
| 590 | `                args = f[5]` | `args`: the options of the process. |
| 591 | `                plan = os.path.join(sdir, step, f[4])` | `plan`: the path of its plan file. |
| 592 | `                text = open(plan).read()` | `text`: the text of the plan. |
| 593 | `                if f[2] == "41" and alt != 41:` | A process on CPU 41, on a machine where another CPU must be used. |
| 594 | `                    args = args.replace("--cpus 41 ", "--cpus %d " % alt)` | Replaces `--cpus 41` in the options with the other CPU. |
| 595 | `                    with open(plan, "w") as out:` | Opens the plan file of the copy for writing. |
| 596 | `                        out.write(text.replace(" cpu=41 ", " cpu=%d " % alt))` | Writes the plan again with `cpu=41` in its header replaced. The runner refuses a plan whose `cpu` pair differs from `--cpus`, so both must change. |
| 597 | `                trials = [l.split(" ") for l in text.split("\n")[3:-1]]` | `trials`: the trial lines of the plan, each split into its fields. |
| 598 | `                jobs.append((step, session, f[0], args.split(), len(trials), sum(int(t[7]) for t in trials),` | Adds the job. This line: the step, the session, the `idx`, the options as a list, the number of trials, and the sum of the target windows of all trials (field `nwin`). |
| 599 | `                             sum((1 if t[3] != "-" else 0) + (4 if t[4] != "-" else 0) for t in trials)))` | Ends the job with the number of windows that are not target windows: 1 for a previous activity and 4 for a prefix. A predecessor is not counted here. No plan of round 2 has one. |
| 600 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment for the stand-in: the environment of the test without every variable whose name starts with `BWX_`. So no counter setting of the developer reaches the runner. |
| 602 | `    def one(job):` | Starts the inner function `one`. It runs one job through the stand-in and tests its output. |
| 603 | `        step, session, idx, args, ntr, nwin, nother = job` | Takes the 7 values of the job: the step, the session, the `idx`, the options, the number of trials, the number of target windows and the number of other windows. |
| 604 | `        try:` | Starts the block whose error is caught. |
| 605 | `            r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True, timeout=300)` | Runs the stand-in with the options of the row, in the folder `d`, for at most 300 s. It keeps the output and the error output as text. |
| 606 | `        except subprocess.TimeoutExpired:` | The run took longer than 300 s. |
| 607 | `            return (step, session, idx, "timeout")` | Returns a result that names the job and the word `timeout`. |
| 608 | `        rows = collections.Counter()` | `rows`: how many output rows of each kind the run printed. |
| 609 | `        for l in r.stdout.split("\n"):` | Starts a loop over the output lines. |
| 610 | `            f = l.split(",")` | Splits the line at the commas. |
| 611 | `            rows[f[0] if f[0] != "W" else "W." + ("target" if f[2] == "target" else "other")] += 1` | Counts the line under its first field, the kind of the row. A `W` row is the row of one window. It is counted as `W.target` when its phase field is `target`, and as `W.other` for every other phase. |
| 612 | `        m = dict(l.split(",", 2)[1:] for l in r.stdout.split("\n") if l.startswith("M,") and l.count(",") >= 2)` | `m`: the `M` rows of the output as a dictionary from the key to the value. An `M` row has the form `M,key,value`. |
| 613 | `        ok = r.returncode == 0 and rows["S"] == ntr and rows["E"] == ntr and rows["W.target"] == nwin \` | `ok`: the test of the run. This line: exit status 0, one `S` row and one `E` row per trial, and one `W` row per planned target window. By the note `DECISIONS-bwx8.md` the runner prints the `S` row before a trial and the `E` row after it. The backslash joins the next line to this statement. |
| 614 | `            and rows["W.other"] == nother and m.get("plan.step") == step and m.get("plan.proc") == idx \` | Continues the test: one `W` row per planned window of the other phases, and the `M` rows `plan.step` and `plan.proc` name the step and the `idx` of the job. So the runner read the plan that the row names. |
| 615 | `            and m.get("mode") == "trial"` | Ends the test: the `M` row `mode` says `trial`. |
| 616 | `        if ok and "--events" in args:` | For a job with counter options. |
| 617 | `            ok = m.get("pmu_type") == "11" and m.get("events", "").count(";") == 5 and rows["C"] + rows["X"] >= 1` | More tests: the `M` row `pmu_type` is 11, the `M` row `events` holds 6 events (5 semicolons between them), and the output has at least one `C` row or one `X` row. By the note `DECISIONS-bwx8.md` a `C` row holds the counts of one target window, and an `X` row reports a failure, for example a counter that could not be opened. So this test does not need working counters on the local machine. |
| 618 | `        return None if ok else (step, session, idx, r.returncode, r.stderr[-200:], dict(rows))` | Returns `None` for a good run. For a bad one it returns the job, the exit status, the end of the error output and the row counts. |
| 620 | `    t0 = time.time()` | `t0`: the time before the runs, for the name of a check. |
| 621 | `    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:` | Creates a pool of 6 worker threads. So up to 6 stand-in processes run at the same time. |
| 622 | `        results = list(pool.map(one, jobs))` | Runs `one` for every job and collects the results in the order of the jobs. |
| 623 | `    per = collections.defaultdict(list)` | `per`: the results of each step and session. |
| 624 | `    for job, res in zip(jobs, results):` | Starts a loop over the jobs with their results. |
| 625 | `        per[job[0], job[1]].append(res)` | Adds the result to the list of its step and session. |
| 626 | `    for (step, session), res in sorted(per.items(), key=lambda x: (x[0][1], x[0][0])):` | Starts a loop over the steps and sessions, sorted by the session and then by the step name. |
| 627 | `        bad = [x for x in res if x]` | `bad`: the results that describe a defect. |
| 628 | `        check("%s session %d: bwx8 accepts each of the %d plans with its args: status 0, one S and one E row per trial, "` | Starts a check per step and session: the stand-in accepts each plan with its options. The name states the test: status 0, and one `S` row and one `E` row per trial. |
| 629 | `              "every planned window as a W row" % (step, session, len(res)),` | Ends the name: every planned window as a `W` row. |
| 630 | `              len(res) == TABLE[step][0] and not bad, bad[:2])` | The test: the number of jobs is the process count of `TABLE`, and no job gave a defect. This proves that the runner source accepts every plan and every option text that the generator writes with the test divisor 100. Such a plan differs from the real one only in its durations and in `test=1`. On a machine without CPU 41 the test has also changed the CPU. This matters: a runner that refuses its plan ends with status 2, and the run script then stops the step. |
| 631 | `    check("all %d plans of both sessions ran through bwx8 (%.0f s)" % (len(jobs), time.time() - t0),` | Starts a check: all plans of both sessions ran through the stand-in. The name also shows the seconds that the runs took. |
| 632 | `          len(jobs) == sum(v[0] for v in TABLE.values()) * 2 - 3 and all(x is None for x in results))` | The test: the number of jobs is twice the sum of the process counts of `TABLE` minus 3, that is 635, and every result is `None`. The 3 processes of `XEV` exist in session 1 only. |
| 633 | `    # The acceptance means something only if bwx8 refuses a defective plan and missing counter settings.` | Comment: the acceptance above proves something only when the runner refuses a plan with a defect, and a counter step without counter settings. |
| 634 | `    plan = os.path.join(d, "sched9", "s1", "XN", "0000.plan")` | `plan`: the first plan of step `XN` in session 1, in the copy. |
| 635 | `    text = open(plan).read()` | `text`: the text of that plan. |
| 636 | `    args = ["--trial", "--cpus", "2", "--bytes", re.search(r" bytes=(\d+) ", text).group(1), "--plan"]` | `args`: the options for the damaged plans: the trial mode, CPU 2, and the buffer size that the header of the plan names. The pattern takes the digits after `bytes=`. The path of the plan is added later. |
| 637 | `    for name, bad in (("an unknown kernel", text.replace("@", "x@")),` | Starts a loop over plans with one defect each. First: an unknown kernel, made by an `x` before each `@`. |
| 638 | `                      ("a size above --bytes", re.sub(r"@(32K\|1M\|8M)", "@64M", text)),` | Second: every size of the plan becomes 64 MiB, which is above the buffer of the process. |
| 639 | `                      ("a prefix that is not a multiple of 4 ms", re.sub(r":12 ", ":13 ", text))):` | Third: the prefix lasts 13 ms in place of 12 ms. With the test divisor 100 a prefix has 12 ms, and 13 is not a multiple of 4. |
| 640 | `        p = os.path.join(d, "bad.plan")` | `p`: the path of the damaged plan file. |
| 641 | `        with open(p, "w") as f:` | Opens it for writing. |
| 642 | `            f.write(bad)` | Writes the damaged text. |
| 643 | `        r = subprocess.run([binary] + args + [p], env=env, capture_output=True, text=True)` | Runs the stand-in with the damaged plan. |
| 644 | `        check("bwx8 refuses a plan with %s (status 2)" % name, bad != text and r.returncode == 2, (r.returncode, r.stderr))` | Check, once per defect: the damaged text differs from the good one, and `bwx8` ends with exit status 2. So the runner checks its plan and does not run a plan with a defect. |
| 645 | `    ev = os.path.join(d, "sched9", "s1", "XEV", "0000.plan")` | `ev`: the first plan of step `XEV`, whose trial has the counter mode `read`. |
| 646 | `    r = subprocess.run([binary, "--trial", "--cpus", "2", "--bytes", "8388608", "--plan", ev], env=env, capture_output=True, text=True)` | Runs the stand-in with that plan but without the options `--pmu-type` and `--events`. The environment holds no counter setting. |
| 647 | `    check("bwx8 refuses the XEV plan when the event options are left out of the args (status 2)",` | Starts a check: the runner refuses the plan of `XEV` when the event options are left out. |
| 648 | `          r.returncode == 2 and "--events" in r.stderr, (r.returncode, r.stderr))` | The test: exit status 2, and the error output names `--events`. So a trial that counts cannot run without its event list. The schedules of the generator give both options in the `args` column. |

### Host sampler checks: the busy test program `CHILD`, `read_watch`, `delta_sum` (lines 651 to 685)

| Line | Source | Explanation |
|---:|---|---|
| 651 | `# ---------- hostwatch.py ----------` | Comment: the checks of the host sampler `hostwatch.py` start here. |
| 652 | `CHILD = """` | `CHILD`: the text of a small Python program that the test starts as a busy process. Two places of the text are filled later: a CPU and a number of seconds. |
| 653 | `import os, sys, threading, time` | Line of the program: loads four modules. |
| 654 | `os.sched_setaffinity(0, {%d})` | Line of the program: limits the process to one CPU. The `%d` is filled with the number of that CPU. |
| 655 | `def spin():` | Line of the program: starts the function `spin`. |
| 656 | `    end = time.time() + %g` | Line of the program: the end time, which is the given number of seconds from now. The `%g` is filled with that number. |
| 657 | `    while time.time() < end:` | Line of the program: a loop that runs until the end time. |
| 658 | `        pass` | Line of the program: the loop does nothing. So the thread uses its CPU all the time. |
| 659 | `t = threading.Thread(target=spin)` | Line of the program: creates a second thread that runs `spin`. |
| 660 | `t.start()` | Line of the program: starts that thread. |
| 661 | `t.join()` | Line of the program: the main thread waits for it. So the process has a waiting main thread and one busy worker thread. By the note `DECISIONS-bwx8.md` a runner in the trial mode has the same two threads. |
| 662 | `"""` | Ends the text `CHILD`. |
| 665 | `def read_watch(path):` | Starts the function `read_watch`. It reads an output file of the host sampler. |
| 666 | `    """(header and footer lines, sample lines as (t, is absolute, dict))."""` | Description text: the function returns the header and footer lines, and the sample lines. A sample line is given as its time, a flag for an absolute line, and a dictionary of its items. |
| 667 | `    head, samples = [], []` | `head`: the lines that start with `#`. `samples`: the sample lines. Both are empty at first. |
| 668 | `    for l in open(path).read().split("\n"):` | Starts a loop over the lines of the file. |
| 669 | `        if l.startswith("#"):` | A header or footer line. |
| 670 | `            head.append(l)` | Keeps it as it is. |
| 671 | `        elif l:` | Any other line that is not empty: a sample line. |
| 672 | `            f = l.split(" ")` | Splits the line at the blanks. |
| 673 | `            absolute = f[1] == "ABS"` | `absolute`: true when the second field is the word `ABS`. Such a line holds the full value of every key. |
| 674 | `            d = collections.OrderedDict()` | `d`: the items of the line, in the order of the file. |
| 675 | `            for item in f[2 if absolute else 1:]:` | Starts a loop over the items: from the third field of an absolute line, and from the second field of a delta line. |
| 676 | `                k, _, v = item.partition("=")` | Splits an item at its first equals sign into the key `k` and the value `v`. For a state item of the form `key:=value` the key then ends with a colon. |
| 677 | `                d[k] = v` | Stores the item. |
| 678 | `            samples.append((int(f[0]), absolute, d))` | Adds the sample: the time in ns from the first field, the flag, and the dictionary. |
| 679 | `    return head, samples` | Returns the two lists. |
| 682 | `def delta_sum(samples, key):` | Starts the function `delta_sum`. |
| 683 | `    return sum(int(d[key]) for _, absolute, d in samples if not absolute and key in d)` | Returns the sum of the values of one key over all delta lines. A delta line holds the change of a counter after the last sample. So the sum is the whole change of that counter over the file. |

### `hostwatch_checks`: a busy process, the header, the absolute line, whole-file reads (lines 686 to 748)

| Line | Source | Explanation |
|---:|---|---|
| 686 | `def hostwatch_checks(tmp):` | Starts the function `hostwatch_checks`: the checks of the host sampler. They run the sampler on this machine beside test processes. |
| 687 | `    allowed = sorted(os.sched_getaffinity(0))` | `allowed`: the CPUs on which this test may run, in sorted order. |
| 688 | `    if not check("hostwatch: this machine allows 3 or more CPUs", len(allowed) >= 3):` | Check: the test may use at least 3 CPUs. |
| 689 | `        return` | If not: leaves the function. The other checks of the sampler do not run. |
| 690 | `    c_work, c_watch = allowed[-1], allowed[-2]` | `c_work`: the watched CPU, the highest allowed one. The busy test processes run on it. `c_watch`: the CPU of the sampler, the second highest. |
| 691 | `    d = os.path.join(tmp, "hw")` | `d`: the folder `hw` in the temporary folder. |
| 692 | `    os.makedirs(d)` | Creates it. |
| 693 | `    out = os.path.join(d, "busy.txt")` | `out`: the output file of the first sampler run. |
| 694 | `    # A second process on the same CPU: a thread of another process that the sampler must find and follow.` | Comment: a second process runs on the same CPU. Its thread is a thread of another process, which the sampler must find and follow. |
| 695 | `    other = subprocess.Popen([sys.executable, "-c", CHILD % (c_work, 60)])` | `other`: starts the program `CHILD` on the watched CPU for 60 s. It is the other process. |
| 696 | `    time.sleep(0.5)` | Waits 0.5 s. |
| 697 | `    child = subprocess.Popen([sys.executable, "-c", CHILD % (c_work, 3.0)])` | `child`: starts the program `CHILD` on the same CPU for 3 s. It is the process that the sampler will watch. The two busy threads now share one CPU. |
| 698 | `    time.sleep(0.3)                                  # the worker thread exists and is on its CPU` | Waits 0.3 s. By the comment the worker thread of `child` then exists and runs on its CPU. |
| 699 | `    start_ticks = open("/proc/%d/stat" % child.pid).read().rsplit(")", 1)[1].split()[19]` | `start_ticks`: the start time of `child` in clock ticks after the boot. The test reads it from the file `stat` of the process: the text after the last `)` is split at blanks, and entry 19 of that list is field 22 of the file. |
| 700 | `    t0 = time.time()` | `t0`: the time before the sampler starts. |
| 701 | `    r = subprocess.run(["taskset", "-c", str(c_watch), sys.executable, WATCH, "--pid", str(child.pid), "--cpu", str(c_work),` | Runs the sampler and waits for its end. `taskset -c` limits it to the CPU `c_watch`. It watches the process `child` and the CPU `c_work`. |
| 702 | `                        "--out", out], capture_output=True, text=True, timeout=60)` | Continues the call: the output file, the kept output and error output, and a time limit of 60 s for this call. |
| 703 | `    took = time.time() - t0` | `took`: the seconds that the sampler ran. |
| 704 | `    child.wait()` | Collects the ended process `child`. |
| 705 | `    head, samples = read_watch(out)` | Reads the output file of the sampler. |
| 706 | `    text = "\n".join(head)` | `text`: the header and footer lines as one text. |
| 707 | `    check("hostwatch on a busy child: status 0, no message, ends by itself when the child is gone",` | Starts a check: on a busy process the sampler ends with status 0, prints nothing, and ends by itself when the process is gone. |
| 708 | `          r.returncode == 0 and r.stdout == "" and r.stderr == "" and took < 6 and` | The test, first part: exit status 0, an empty output and an empty error output, and a run time below 6 s. The process lives about 3 s. Without an end of its own the sampler would run to its time limit of 120 s. |
| 709 | `          re.search(r"^# end reason=pid_gone samples=\d+ missed=\d+ max_sample_us=\d+ errors=0$", text, re.M) is not None,` | Second part: the file holds a footer line of this form: `# end reason=pid_gone`, then the counts `samples`, `missed` and `max_sample_us` as digits, then `errors=0`. `re.M` lets `^` and `$` match at the start and the end of each line. So the sampler names the right reason and had no error. |
| 710 | `          (r.returncode, r.stderr, took, head[-1:]))` | The detail for a failure: the exit status, the error output, the run time and the last header or footer line. |
| 711 | `    m = re.search(r"^# clocks mono_ns=(\d+) boot_ns=(\d+) real_ns=(\d+)$", text, re.M)` | `m`: the clock line of the header. Group 1 holds the value of `mono_ns`, group 2 of `boot_ns` and group 3 of `real_ns`, each as digits. |
| 712 | `    check("hostwatch header: version line with pid and cpu; CLOCK_MONOTONIC, CLOCK_BOOTTIME and CLOCK_REALTIME in ns",` | Starts a check of the header: the version line with the process id and the CPU, and the three clocks `CLOCK_MONOTONIC`, `CLOCK_BOOTTIME` and `CLOCK_REALTIME` in ns. |
| 713 | `          head[0] == "# hostwatch v1 pid=%d cpu=%d hz=20 max_s=120" % (child.pid, c_work) and m is not None` | The test, first part: the first line is exactly `# hostwatch v1` with the process id of `child`, the watched CPU, 20 samples per second and a time limit of 120 s. The last two are the defaults of the sampler. And the clock line exists. |
| 714 | `          and abs(int(m.group(3)) / 1e9 - t0) < 5 and int(m.group(2)) >= int(m.group(1)) > 0, head[:3])` | Second part: the real-time clock of the header is within 5 s of the time `t0` of the test. The boot-time clock is at least the monotonic clock, and both are above 0. This matters: every sample line carries a monotonic time, and these three values let a reader place it on the time of day. |
| 715 | `    check("hostwatch header: the start time of the process (field 22 of its stat file) with the clock tick rate",` | Starts a check of the header: the start time of the process, which is field 22 of its `stat` file, with the clock tick rate. |
| 716 | `          ("# target starttime_ticks=%s clk_tck=%d comm=" % (start_ticks, os.sysconf("SC_CLK_TCK"))) in text, head[:4])` | The test: the header holds a line `# target` with the start time that the test read itself in line 699, and with the number of clock ticks per second of this machine (`SC_CLK_TCK`). The detail shows the first 4 header lines. |
| 717 | `    check("hostwatch header: the thread of the other process on the watched CPU is listed with its comm, then the scan line",` | Starts a check of the header: the thread of the other process on the watched CPU is listed with its command name, and the scan line follows. |
| 718 | `          re.search(r"^# th tid=\d+ pid=%d comm=\S+$" % other.pid, text, re.M) is not None` | The test, first half: a line `# th` exists with a thread id, the process id of `other` and a command name without blanks. So the first scan found a thread of the other process on the watched CPU. |
| 719 | `          and re.search(r"^# scan threads=\d+ on_cpu=\d+ took_ms=[\d.]+$", text, re.M) is not None, head[:8])` | Second half: a line `# scan` exists with the number of threads that were looked at, the number found on the CPU, and the time of the scan in ms. |
| 720 | `    first = samples[0] if samples else (0, False, {})` | `first`: the first sample line, or an empty stand-in when the file has none. |
| 721 | `    keys = ["m.run_ns", "m.nvcsw", "m.nivcsw", "m.minflt", "m.majflt", "m.utime", "m.stime", "m.cpu", "m.slices",` | `keys`: the keys that the first sample line must hold. This line: 9 keys of the main thread (prefix `m.`): the run time, the voluntary and the involuntary context switches, the minor and the major page faults, the user and the system CPU time, the last CPU, and the number of time slices. |
| 722 | `            "w.run_ns", "w.wait_ns", "w.slices", "w.nvcsw", "w.nivcsw", "w.minflt", "w.majflt", "w.utime", "w.stime"]` | Continues the list with 9 keys of the worker thread (prefix `w.`): the run time, the wait time, the time slices, the two kinds of context switches, the two kinds of page faults, and the two CPU times. |
| 723 | `    check("hostwatch: the first sample line holds the absolute values of the main thread (m.) and the worker thread (w.)",` | Starts a check: the first sample line holds the absolute values of the main thread and of the worker thread. |
| 724 | `          first[1] and all(k in first[2] for k in keys) and first[2].get("w.cpu") == str(c_work),` | The test: the first sample line is an absolute line, it holds all 18 keys, and its value `w.cpu` is the watched CPU. So the sampler found the worker thread of the process and saw it on the CPU to which it is limited. |
| 725 | `          [k for k in keys if k not in first[2]])` | The detail for a failure: the keys that are missing. |
| 726 | `    check("hostwatch: the absolute line holds the cpuN line of /proc/schedstat, column N of /proc/softirqs, "` | Starts a check: the absolute line also holds values of the watched CPU and of the host. The name lists the first two sources: the line of the CPU in `/proc/schedstat` and its column in `/proc/softirqs`. |
| 727 | `          "/proc/vmstat and /proc/interrupts",` | Ends the name: `/proc/vmstat` and `/proc/interrupts`. |
| 728 | `          first[1] and all(k in first[2] for k in ("cpu.pcount", "cpu.run_ns", "sirq.TIMER", "sirq.SCHED", "sirq.RCU"))` | The test, first part: the line is absolute and holds two keys of the scheduler line of the CPU (`cpu.pcount`, `cpu.run_ns`) and three soft interrupt keys (`sirq.TIMER`, `sirq.SCHED`, `sirq.RCU`). |
| 729 | `          and sum(k.startswith("vm.") for k in first[2]) > 20 and any(k.startswith("irq.") for k in first[2]),` | Second part: it holds more than 20 keys that start with `vm.`, and at least one key that starts with `irq.`. |
| 730 | `          [k for k in first[2] if not k.startswith(("vm.", "th."))][:40])` | The detail for a failure: the first 40 keys of the line that start neither with `vm.` nor with `th.`. |
| 731 | `    # Why: the kernel gives /proc/vmstat in pieces of about one memory page. A reader that stops after a` | Comment: the reason for the next check. The Linux kernel gives the file `/proc/vmstat` in pieces of about one memory page. The sentence about a reader that stops too early ends in the next line. |
| 732 | `    # short first piece loses the last keys (found in review: 175 of 178 keys on this machine).` | Continues the comment: a reader that stops after a short first piece loses the last keys. By the comment a review found this defect: such a reader got 175 of 178 keys on the machine of the developer. |
| 733 | `    vm_keys = {l.split()[0] for l in open("/proc/vmstat").read().split("\n") if len(l.split()) == 2 and l.split()[1].isdigit()}` | `vm_keys`: the keys of `/proc/vmstat` as the test reads them itself: the first word of every line that has two words, the second of which is a number. |
| 734 | `    got_keys = {k[3:] for k in first[2] if k.startswith("vm.")}` | `got_keys`: the keys of the absolute line that start with `vm.`, without that prefix. |
| 735 | `    check("hostwatch: the absolute line holds every key of /proc/vmstat (the file is read to its end, not only its first piece)",` | Starts a check: the absolute line holds every key of `/proc/vmstat`. |
| 736 | `          len(vm_keys) > 20 and got_keys == vm_keys, (len(vm_keys), len(got_keys), sorted(vm_keys ^ got_keys)[:8]))` | The test: the file has more than 20 keys, and the two sets of keys are equal. So the sampler reads the file to its end. The detail shows the two counts and up to 8 keys that only one of the two sets has. |
| 737 | `    for path, single in (("/proc/vmstat", False), ("/proc/softirqs", False), ("/proc/schedstat", False),` | Starts a loop over five files of `/proc`, each with the flag `single` of the reader. This line: three files with the flag false. The reader then reads until a read returns nothing. |
| 738 | `                         ("/proc/interrupts", False), ("/proc/self/status", True)):` | Continues the list: `/proc/interrupts` with the flag false, and `/proc/self/status`, a file of one process, with the flag true. With that flag the reader takes one read as the whole file. |
| 739 | `        try:` | Starts the block whose error is caught. |
| 740 | `            want_lines = open(path, "rb").read().count(b"\n")` | `want_lines`: the number of lines of the file, as the test reads it. |
| 741 | `        except OSError:` | The file cannot be read on this machine. |
| 742 | `            want_lines = None` | Then the line count is unknown. |
| 743 | `        r = subprocess.run([sys.executable, "-B", "-c", "import sys; sys.path.insert(0, %r); import hostwatch as h; "` | Starts a small Python program. `-B` writes no compiled file. The program loads `hostwatch.py` from the folder of this file as the module `h`. |
| 744 | `                            "d = h.Src(%r, %r).read(); print(-1 if d is None else d.count(b'\\n'))" % (X, path, single)],` | Continues the program: it reads the file with the reader class `Src` of the sampler. It prints the number of lines that it got, or -1 when the read failed. |
| 745 | `                           capture_output=True, text=True)` | Keeps the output and the error output of that program as text. |
| 746 | `        check("hostwatch reader: %s is read whole (%s lines)" % (path, want_lines),` | Starts a check per file: the reader of the sampler reads the whole file. |
| 747 | `              r.returncode == 0 and (want_lines is None or abs(int(r.stdout) - want_lines) <= 2) and (want_lines is None or want_lines < 3 or int(r.stdout) >= 3),` | The test: the program ended with status 0. When the test could read the file, the two line counts differ by at most 2, and the reader got at least 3 lines of a file that has 3 or more. The two reads come from two processes at two moments, so the counts can differ a little. |
| 748 | `              (r.returncode, r.stdout, r.stderr[-200:]))` | The detail for a failure: the exit status, the output and the end of the error output. |

### `hostwatch_checks`: errors inside the sampler, the sample rate, a shared CPU, item form (lines 749 to 789)

| Line | Source | Explanation |
|---:|---|---|
| 749 | `    # Why: an error inside a sample must not end the sampling, and must not be recorded as "the process is gone".` | Comment: the reason for the next checks. An error inside a sample must not end the sampling, and it must not be recorded as the end of the watched process. |
| 750 | `    sl = subprocess.Popen(["sleep", "30"])` | `sl`: starts a `sleep` of 30 s as the watched process of these checks. |
| 751 | `    for name, patch, want_rc, want in (` | Starts a loop over two cases. Each has a name, a line of Python that damages the sampler, the expected exit status, and the pattern of the expected footer line. |
| 752 | `            ("sample", "h.Watch.vm = lambda self, cur: int('x')", 0, r"^# end reason=max_s samples=\d+ missed=\d+ max_sample_us=\d+ errors=[1-9]\d*$"),` | Case `sample`: the method `vm` of the sampler, which reads `/proc/vmstat` in every sample, is replaced by a function that raises a `ValueError`. Expected: exit status 0, and a footer with `reason=max_s` and an error count of 1 or more. |
| 753 | `            ("first scan", "h.Watch.scanner = lambda self, first: int('x')", 1, r"^# end reason=error samples=0 missed=0 max_sample_us=0 errors=0$")):` | Case `first scan`: the method `scanner`, which walks all threads of the host, is replaced in the same way. The first scan runs before the first sample. Expected: exit status 1, and a footer with `reason=error` and all counts 0. |
| 754 | `        oute = os.path.join(d, "err-%s.txt" % name.replace(" ", ""))` | `oute`: the output file of this case, `err-sample.txt` or `err-firstscan.txt`. |
| 755 | `        r = subprocess.run([sys.executable, "-B", "-c", "import sys; sys.path.insert(0, %r); import hostwatch as h; %s; "` | Starts a small Python program that loads the sampler as the module `h` and then runs the damaging line. |
| 756 | `                            "sys.argv = ['hostwatch.py', '--pid', '%d', '--cpu', '%d', '--out', %r, '--max-s', '0.5']; sys.exit(h.main())"` | Continues the program: it sets the command line of the sampler (the process `sl`, the watched CPU, the output file and a time limit of 0.5 s) and runs its `main`. The exit status of the program is the return value of `main`. |
| 757 | `                            % (X, patch, sl.pid, c_work, oute)], capture_output=True, text=True, timeout=60)` | The values for the program text, and the options of the call: kept output, text mode and a limit of 60 s. |
| 758 | `        texte = open(oute).read() if os.path.exists(oute) else ""` | `texte`: the content of the output file, or an empty text when no file was written. |
| 759 | `        check("hostwatch with an error in the %s: status %d, the footer names it (not pid_gone)%s" % (` | Starts a check per case: the exit status is as expected, and the footer names the real reason and not `pid_gone`. |
| 760 | `              name, want_rc, ", every sample line is 'hw.error:=ValueError', the sampling goes on to --max-s" if want_rc == 0 else ", the message is on stderr"),` | The values for the name of the check. For the case `sample` the name adds: every sample line is `hw.error:=ValueError`, and the sampling goes on to the time limit. For the other case it adds: the message is in the error output. |
| 761 | `              r.returncode == want_rc and re.search(want, texte, re.M) is not None` | The test, first part: the exit status is the expected one, and the output file holds a footer line that matches the pattern of the case. |
| 762 | `              and ((want_rc == 0 and texte.count(" hw.error:=ValueError\n") >= 5 and r.stderr == "") or (want_rc == 1 and "ValueError" in r.stderr)),` | Second part. Case `sample`: at least 5 sample lines end with the item `hw.error:=ValueError`, and the error output is empty. So each sample reported its error, and the sampling went on for the 0.5 s. Case `first scan`: the error output names `ValueError`. |
| 763 | `              (r.returncode, r.stderr[-200:], texte[-300:]))` | The detail for a failure: the exit status, the end of the error output and the end of the output file. |
| 764 | `    sl.kill()` | Ends the `sleep` process. |
| 765 | `    sl.wait()` | Collects it. |
| 766 | `    deltas = [s for s in samples if not s[1]]` | `deltas`: the delta lines of the first sampler run, the run on the busy process. |
| 767 | `    gaps = [b[0] - a[0] for a, b in zip(deltas, deltas[1:])]` | `gaps`: the time in ns from each delta line to the next. |
| 768 | `    check("hostwatch: delta lines at 20 Hz (median gap 45 to 55 ms), times rising, 30 or more lines in 2.7 s",` | Starts a check of the sample rate: the delta lines come 20 times per second, their times rise, and the run of about 2.7 s gives 30 or more of them. |
| 769 | `          len(deltas) >= 30 and all(g > 0 for g in gaps) and 45e6 <= statistics.median(gaps) <= 55e6,` | The test: at least 30 delta lines, every gap above 0, and a median gap from 45 ms to 55 ms. The planned gap at 20 samples per second is 50 ms. So the sampler keeps its rate while two busy threads share the watched CPU. |
| 770 | `          (len(deltas), sorted(gaps)[:3], gaps and statistics.median(gaps)))` | The detail for a failure: the number of delta lines, the 3 smallest gaps and the median gap. |
| 771 | `    span = (samples[-1][0] - samples[0][0]) / 1e9 if samples else 0` | `span`: the time from the first to the last sample line, in seconds. |
| 772 | `    run = delta_sum(samples, "w.run_ns") / 1e9` | `run`: the run time of the worker thread over the file, in seconds: the sum of all changes of `w.run_ns`. |
| 773 | `    check("hostwatch: the worker thread shares its CPU with the other process: w.run_ns is 25 to 75 % of the time, "` | Starts a check: the sampler shows that the worker thread shares its CPU with the other process. The name gives the first part: the run time of the worker is 25 to 75 % of the time. |
| 774 | `          "w.nivcsw and w.slices rise",` | Ends the name: the involuntary context switches and the time slices of the worker rise. |
| 775 | `          span > 2 and 0.25 * span <= run <= 0.75 * span and delta_sum(samples, "w.nivcsw") > 5` | The test, first part: the file covers more than 2 s, the worker ran for 25 to 75 % of that time, and its involuntary context switches rose by more than 5. Two busy threads on one CPU get about half of the time each. |
| 776 | `          and delta_sum(samples, "w.slices") > 5, (span, run, delta_sum(samples, "w.nivcsw")))` | Second part: the number of time slices of the worker rose by more than 5. This check proves the main use of the sampler: its file shows when another thread takes the CPU of the watched process. |
| 777 | `    thkeys = {k for _, absolute, dd in samples if not absolute for k in dd if k.startswith("th.%d." % (other.pid + 0))}` | `thkeys`: the keys of the delta lines that start with `th.` and the process id of `other`. They are used only in the detail of the next check. |
| 778 | `    th_any = {k for _, absolute, dd in samples if not absolute for k in dd if k.startswith("th.") and k.endswith(".run_ns")}` | `th_any`: every key of the delta lines that starts with `th.` and ends with `.run_ns`. Each is the run time of one thread of another process on the watched CPU. |
| 779 | `    th_run = max([delta_sum(samples, k) for k in th_any] or [0]) / 1e9` | `th_run`: the largest run time of one such thread over the file, in seconds, or 0 when there is none. |
| 780 | `    check("hostwatch: a thread of the other process on the CPU is followed (th.<tid>.<comm>.run_ns is 25 to 75 % of the time)",` | Starts a check: the sampler follows a thread of the other process on the watched CPU. |
| 781 | `          0.25 * span <= th_run <= 0.75 * span, (span, th_run, sorted(thkeys)[:5]))` | The test: the busiest thread of another process ran for 25 to 75 % of the time of the file. The test takes the largest value of any followed thread. It does not test that this thread belongs to the process `other`. |
| 782 | `    check("hostwatch: the CPU counters move (cpu.pcount, cpu.run_ns, sirq.TIMER) and vmstat keys are reported as vm.<key>",` | Starts a check: the counters of the watched CPU move, and the keys of `/proc/vmstat` appear with the prefix `vm.`. |
| 783 | `          delta_sum(samples, "cpu.pcount") > 5 and delta_sum(samples, "cpu.run_ns") > 5e8` | The test, first part: over the file `cpu.pcount` rose by more than 5, and `cpu.run_ns` rose by more than 0.5 s. Both are values of the line of the watched CPU in `/proc/schedstat`. |
| 784 | `          and delta_sum(samples, "sirq.TIMER") > 5` | Second part: the count of the timer soft interrupt of the CPU, `sirq.TIMER`, rose by more than 5. |
| 785 | `          and any(k.startswith("vm.") for _, absolute, dd in samples if not absolute for k in dd))` | Third part: at least one delta line holds a key that starts with `vm.`. |
| 786 | `    check("hostwatch: every item of a delta line is key=number or key:=state",` | Starts a check of the form of the items of a delta line. By its name every item is `key=number` or `key:=state`. |
| 787 | `          all(re.match(r"^-?\d+$", v) or v.startswith("=") for _, absolute, dd in samples if not absolute for v in dd.values())` | The test, first part: for every item of every delta line, the text after the first equals sign is a whole number with an optional minus sign (pattern `^-?\d+$`), or it starts with a second equals sign. `read_watch` splits a state item `key:=value` at its one equals sign (line 676). So a state item passes only when its value is a number. A state such as `na` would fail this check, although the name of the check allows it. |
| 788 | `          and all(dd for _, _, dd in samples))` | Second part: no sample line is without an item. |

### `hostwatch_checks`: time limit, signal, missing process or CPU, usage, source text (lines 790 to 843)

| Line | Source | Explanation |
|---:|---|---|
| 790 | `    # --max-s, SIGTERM, a process that does not exist, a CPU that does not exist.` | Comment: the next checks test the time limit `--max-s`, the signal SIGTERM, a process that does not exist and a CPU that does not exist. |
| 791 | `    out2 = os.path.join(d, "max.txt")` | `out2`: the output file of the next run. |
| 792 | `    t0 = time.time()` | `t0`: the time before that run. |
| 793 | `    r = subprocess.run([sys.executable, WATCH, "--pid", str(other.pid), "--cpu", str(c_work), "--out", out2, "--max-s", "1",` | Runs the sampler on the process `other`, which keeps running, with a time limit of 1 s. This run is not limited to one CPU with `taskset`. |
| 794 | `                        "--hz", "50"], capture_output=True, text=True, timeout=60)` | Continues the call: 50 samples per second. |
| 795 | `    head2, samples2 = read_watch(out2)` | Reads the output file. |
| 796 | `    check("hostwatch --max-s 1 --hz 50 on a process that keeps running: status 0 after about 1 s, reason=max_s, 35 or more samples",` | Starts a check of the time limit: the sampler ends with status 0 after about 1 s, names the reason `max_s`, and took 35 or more samples. |
| 797 | `          r.returncode == 0 and 0.9 < time.time() - t0 < 4 and "reason=max_s" in head2[-1]` | The test, first part: exit status 0, a run time between 0.9 s and 4 s, and a footer with `reason=max_s`. |
| 798 | `          and int(re.search(r"samples=(\d+)", head2[-1]).group(1)) >= 35 and "hz=50 max_s=1" in head2[0],` | Second part: the footer gives at least 35 samples, and the first line records `hz=50 max_s=1`. At 50 samples per second 1 s has 50 sample times. So the limit ends a sampler whose process does not end, and the rate option is used. |
| 799 | `          (r.returncode, time.time() - t0, head2[-1:]))` | The detail for a failure: the exit status, the run time and the footer. |
| 800 | `    check("hostwatch: an absolute line is the first line only (the next one is due after 5 s)",` | Starts a check: in this run of 1 s only the first sample line is an absolute line. The next absolute line is due after 5 s. |
| 801 | `          [s[1] for s in samples2].count(True) == 1 and samples2[0][1])` | The test: exactly one sample line is absolute, and it is the first one. |
| 802 | `    out3 = os.path.join(d, "term.txt")` | `out3`: the output file of the next run. |
| 803 | `    p = subprocess.Popen([sys.executable, WATCH, "--pid", str(other.pid), "--cpu", str(c_work), "--out", out3])` | `p`: starts the sampler on the process `other` in the background, with its default rate and time limit. |
| 804 | `    end = time.time() + 20` | `end`: 20 s from now. |
| 805 | `    while time.time() < end and not (os.path.exists(out3) and "# scan" in open(out3).read()):` | Starts a wait of at most 20 s until the output file holds the scan line. The sampler writes that line after its first scan, directly before the first sample. |
| 806 | `        time.sleep(0.05)` | Waits 0.05 s per turn. |
| 807 | `    time.sleep(5.3)` | Waits 5.3 s more. So the sampler has sampled for more than 5 s. |
| 808 | `    p.send_signal(signal.SIGTERM)` | Sends the signal SIGTERM to the sampler. |
| 809 | `    rc = p.wait(timeout=20)` | `rc`: the exit status of the sampler. The test waits at most 20 s for its end. |
| 810 | `    head3, samples3 = read_watch(out3)` | Reads the output file. |
| 811 | `    check("hostwatch: SIGTERM ends it with status 0 and the footer reason=signal",` | Starts a check: SIGTERM ends the sampler with status 0 and the footer `reason=signal`. |
| 812 | `          rc == 0 and head3 and "reason=signal" in head3[-1], (rc, head3[-1:]))` | The test: exit status 0, and the last header or footer line names `reason=signal`. This matters: the run script sends this signal to a sampler that still runs after its benchmark has ended or was stopped. The file must still get its footer. |
| 813 | `    check("hostwatch: after 5 s a second absolute line follows",` | Starts a check: after 5 s a second absolute line follows. |
| 814 | `          [s[1] for s in samples3].count(True) == 2, [s[1] for s in samples3].count(True))` | The test: this run of about 5.3 s holds exactly 2 absolute lines. So a reader finds the full values again every 5 s. |
| 815 | `    other.kill()` | Ends the process `other`. |
| 816 | `    other.wait()` | Collects it. |
| 817 | `    out4 = os.path.join(d, "gone.txt")` | `out4`: the output file of the next run. |
| 818 | `    r = subprocess.run([sys.executable, WATCH, "--pid", str(other.pid), "--cpu", str(c_work), "--out", out4],` | Runs the sampler on the process id of `other`, which no longer exists. |
| 819 | `                       capture_output=True, text=True, timeout=60)` | Keeps the output and the error output, with a limit of 60 s. |
| 820 | `    head4, _ = read_watch(out4)` | Reads the header and footer lines of the output file. |
| 821 | `    check("hostwatch on a process that is gone: status 0, start time 'na', reason=pid_gone, no error text",` | Starts a check: for a process that is gone the sampler ends with status 0, writes `na` as the start time, names the reason `pid_gone` and prints no error text. |
| 822 | `          r.returncode == 0 and r.stderr == "" and "starttime_ticks=na " in "\n".join(head4)` | The test, first part: exit status 0, an empty error output, and `starttime_ticks=na` in the header. |
| 823 | `          and "reason=pid_gone" in head4[-1], (r.returncode, r.stderr, head4))` | Second part: the footer names `reason=pid_gone`. So a benchmark that has ended before the sampler looks at it gives a complete file and no error. |
| 824 | `    sleeper = subprocess.Popen(["sleep", "30"])` | `sleeper`: starts a `sleep` of 30 s as the watched process of the next run. |
| 825 | `    out5 = os.path.join(d, "nocpu.txt")` | `out5`: the output file of that run. |
| 826 | `    r = subprocess.run([sys.executable, WATCH, "--pid", str(sleeper.pid), "--cpu", "9999", "--out", out5, "--max-s", "0.5"],` | Runs the sampler with the watched CPU 9999 for 0.5 s. By the name of the next check the host does not have such a CPU. |
| 827 | `                       capture_output=True, text=True, timeout=60)` | Keeps the output and the error output, with a limit of 60 s. |
| 828 | `    sleeper.kill()` | Ends the `sleep` process. |
| 829 | `    sleeper.wait()` | Collects it. |
| 830 | `    head5, samples5 = read_watch(out5)` | Reads the output file. |
| 831 | `    check("hostwatch with a CPU that the host does not have: no crash, the missing values are 'na'",` | Starts a check: with a CPU that the host does not have, the sampler does not fail, and the missing values are `na`. |
| 832 | `          r.returncode == 0 and r.stderr == "" and samples5 and samples5[0][2].get("cpu.pcount") == "na"` | The test, first part: exit status 0, an empty error output, at least one sample line, and the value `na` for `cpu.pcount` in the first sample line. |
| 833 | `          and samples5[0][2].get("sirq.TIMER") == "na" and "m.run_ns" in samples5[0][2], (r.returncode, r.stderr))` | Second part: `sirq.TIMER` is `na` too, and the line still holds `m.run_ns` of the watched process. So a wrong CPU number loses the values of the CPU only. The values of the process are still recorded. |
| 834 | `    r = subprocess.run([sys.executable, WATCH, "--pid", "1", "--out", os.path.join(d, "x.txt")], capture_output=True, text=True)` | Runs the sampler without the option `--cpu`. |
| 835 | `    check("hostwatch without --cpu: status 2, no output file", r.returncode == 2 and not os.path.exists(os.path.join(d, "x.txt")))` | Check: exit status 2, and no output file was written. So a wrong command line is reported before the sampler opens its output file. |
| 836 | `    src = open(WATCH).read()` | `src`: the source text of the sampler. |
| 837 | `    check("hostwatch source: opens only files under /proc and the output file, and starts no process",` | Starts a check of the source text: the sampler opens only files under `/proc` and its output file, and it starts no process. |
| 838 | `          not re.search(r"\b(subprocess\|os\.system\|os\.popen\|os\.kill\|sched_setaffinity\|os\.fork\|os\.exec)", src)` | The test, first part: the source holds none of these names at the start of a word: `subprocess`, `os.system`, `os.popen`, `os.kill`, `sched_setaffinity`, `os.fork` and `os.exec`. So the text names no call that starts a process, sends a signal or changes a CPU list. |
| 839 | `          and re.findall(r"os\.open\(([^,]+),", src) == ["self.path", "path"]` | Second part: the source holds exactly two calls of `os.open`, and their first arguments are `self.path` and `path`. The pattern takes the text from the bracket to the first comma. |
| 840 | `          and re.findall(r"\bopen\(([^,)]+)", src.replace("os.open(", "")) == ["a.out"]` | Third part: with the `os.open` calls removed, the source holds exactly one call of `open`, and its first argument is `a.out`, the output file from the command line. |
| 841 | `          and all(x.startswith("/proc") for x in re.findall(r"\"(/[a-z][^\"]*)\"", src)), re.findall(r"\"(/[a-z][^\"]*)\"", src))` | Fourth part: every text in double quotes that starts with a slash and a lower-case letter starts with `/proc`. So every path that is written in the source lies under `/proc`. This check reads the text of the source. It does not watch what the program opens when it runs. The detail lists these texts. |

### Texts of the dummy runner and of the stand-ins for `ps` and `ssh` (lines 844 to 877)

| Line | Source | Explanation |
|---:|---|---|
| 844 | `# ---------- run_bwx9.sh with a dummy bwx8 ----------` | Comment: the texts and helpers for the checks of `run_bwx9.sh` with a dummy `bwx8` start here. |
| 845 | `DUMMY = """#!/usr/bin/env bash` | `DUMMY`: the text of a Bash script that stands in for a runner. This line is its first line, which tells Linux to run it with `bash`. |
| 846 | `# Stand-in for bwx8: records its process ids, checks the plan file, sleeps, ends with DUMMY_EXIT.` | Line of the dummy script: a comment. The script stands in for `bwx8`. It records its process ids, checks the plan file, sleeps, and ends with the exit status in `DUMMY_EXIT`. |
| 847 | `echo "$$ $*" >> "$DUMMY_LOG"` | Line of the dummy script: appends its process id (`$$`) and all its arguments (`$*`) to the file that `DUMMY_LOG` names. The test reads this file to see what was started, and with which options. |
| 848 | `grep Cpus_allowed_list /proc/$$/status >> "$DUMMY_LOG.cpus"` | Line of the dummy script: appends the line `Cpus_allowed_list` of its own status file under `/proc` to the file with the ending `.cpus`. That line is the CPU list of the process. |
| 849 | `echo "PMU=${BWX_PMU_TYPE:-} EV=${BWX_EVENTS:-}" >> "$DUMMY_LOG.env"` | Line of the dummy script: appends the values of `BWX_PMU_TYPE` and `BWX_EVENTS` in its environment to the file with the ending `.env`. |
| 850 | `while (( $# )); do if [[ $1 == --plan && ! -r $2 ]]; then echo "no plan $2" >&2; exit 7; fi; shift; done` | Line of the dummy script: a loop over its arguments. When the argument after `--plan` is not a readable file, it prints `no plan` with the path to the error output and ends with exit status 7. So a wrong plan path fails as it would in a real runner. |
| 851 | `echo "M,dummy,1"` | Line of the dummy script: prints the one output line `M,dummy,1`. The run script appends it to the output file of the step. The test counts these lines to see how many dummies came to this point. |
| 852 | `sleep "${DUMMY_SLEEP:-0}" & echo "$! sleep" >> "$DUMMY_LOG"` | Line of the dummy script: starts `sleep` in the background for the seconds in `DUMMY_SLEEP`, or for 0 s when that variable is not set or is empty. Then it appends the process id of the sleep and the word `sleep` to the log. |
| 853 | `wait $!` | Line of the dummy script: waits for the sleep. |
| 854 | `# DUMMY_TOUCH=1: the marker file appears when this process ends.` | Line of the dummy script: a comment. With `DUMMY_TOUCH=1` the marker file appears when this process ends. |
| 855 | `[[ -z ${DUMMY_TOUCH:-} ]] \|\| : > "$BWX8_MARKER"` | Line of the dummy script: when `DUMMY_TOUCH` is set and not empty, it creates the marker file at the path in `BWX8_MARKER`. The command `:` with `>` writes an empty file. |
| 856 | `exit "${DUMMY_EXIT:-0}"` | Line of the dummy script: ends with the exit status in `DUMMY_EXIT`, or with 0 when that variable is not set or is empty. |
| 857 | `"""` | Ends the text `DUMMY`. |
| 859 | `PS_STUB = """#!/usr/bin/env bash` | `PS_STUB`: the text of a Bash script that stands in for the tool `ps`. This line is its first line. |
| 860 | `# Stand-in for ps: its second call creates the file named by PS_TOUCH. Then it runs the real ps.` | Line of the stand-in: a comment. Its second call creates the file that `PS_TOUCH` names. Then it runs the real `ps`. |
| 861 | `# run_bwx9.sh calls ps once for env.txt and then once per launch, after the wait and before the last marker check.` | Line of the stand-in: a comment. The run script `run_bwx9.sh` calls `ps` once for `env.txt` and then once per launch, after the wait for a quiet system and before the last check of the marker file. So the second call of `ps` comes directly before the first launch. |
| 862 | `if [[ -n ${PS_TOUCH:-} ]]; then` | Line of the stand-in: only when `PS_TOUCH` is set and not empty. |
| 863 | `  echo call >> "$PS_TOUCH.calls"` | Line of the stand-in: appends one line to a file that counts the calls. |
| 864 | `  if (( $(wc -l < "$PS_TOUCH.calls") == 2 )); then : > "$PS_TOUCH"; fi` | Line of the stand-in: when that file has 2 lines, it creates the empty file that `PS_TOUCH` names. |
| 865 | `fi` | Line of the stand-in: ends the `if`. |
| 866 | `exec %s "$@"` | Line of the stand-in: replaces itself with the real `ps` and passes all arguments on. The `%s` is filled later with the path of the real `ps`. |
| 867 | `"""` | Ends the text `PS_STUB`. |
| 869 | `SSH_STUB = """#!/bin/bash` | `SSH_STUB`: the text of a Bash script that stands in for `ssh`. This line is its first line. |
| 870 | `# Stand-in for ssh: records the remote command (its last argument). It opens no connection.` | Line of the stand-in: a comment. It records the remote command, which is its last argument. It opens no connection. |
| 871 | `printf '%s\\n' "${@: -1}" >> "$SSH_LOG"` | Line of the stand-in: appends its last argument (`${@: -1}`) and a newline to the file that `SSH_LOG` names. |
| 872 | `"""` | Ends the text `SSH_STUB`. |
| 873 | `# Every program that run_bwx9.sh and the dummy start, except python3.` | Comment: the list that follows names every program that `run_bwx9.sh` and the dummy start, except `python3`. |
| 874 | `TOOLS = ["env", "bash", "taskset", "date", "sleep", "cut", "who", "wc", "ps", "head", "setsid", "dirname", "awk",` | `TOOLS`: the names of these programs. The test links them into a folder that it then uses as the whole search path. `python3` cannot be found there. So the script runs as on a machine without `python3`. |
| 875 | `         "sha256sum", "sort", "tr", "mkdir", "cp", "hostname", "cat", "grep"]` | Ends the list of the 21 program names. |

### Small helpers: `cpu_list`, `utc`, `samplers` (lines 878 to 903)

| Line | Source | Explanation |
|---:|---|---|
| 878 | `def cpu_list(text):` | Starts the function `cpu_list`. It converts a line `Cpus_allowed_list` to a set of CPU numbers. |
| 879 | `    cpus = set()` | `cpus`: the result set, empty at first. |
| 880 | `    for part in text.split(":")[1].strip().split(","):` | Takes the text after the colon and starts a loop over its parts between commas. A part is one CPU or a range such as `0-5`. |
| 881 | `        a, _, b = part.partition("-")` | Splits a part at the hyphen into the first CPU `a` and the last CPU `b`. `b` is empty for a single CPU. |
| 882 | `        cpus.update(range(int(a), int(b or a) + 1))` | Adds every CPU from `a` to `b`, or `a` alone. |
| 883 | `    return cpus` | Returns the set. |
| 886 | `def utc(offset):` | Starts the function `utc`. |
| 887 | `    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))` | Returns the UTC time `offset` seconds from now, as a text of the form `2026-11-15T03:00:00Z`. |
| 890 | `def samplers(path_part):` | Starts the function `samplers`. |
| 891 | `    """Process ids of running hostwatch.py processes whose command line names this path."""` | Description text: the function returns the process ids of the running `hostwatch.py` processes whose command line names the given path. |
| 892 | `    found = []` | `found`: the result list, empty at first. |
| 893 | `    for pid in os.listdir("/proc"):` | Starts a loop over the names in `/proc`. |
| 894 | `        if pid.isdigit():` | Only a name of digits, which is a process id. |
| 895 | `            try:` | Starts the block whose error is caught. |
| 896 | `                cmd = open("/proc/%s/cmdline" % pid, "rb").read().decode("utf-8", "replace")` | Reads the command line of the process from its file `cmdline`. |
| 897 | `            except OSError:` | The process has ended in the meantime. |
| 898 | `                continue` | Skips it. |
| 899 | `            if "hostwatch.py" in cmd and path_part in cmd:` | When the command line holds `hostwatch.py` and the given path. |
| 900 | `                found.append(int(pid))` | Adds the process id. |
| 901 | `    return found` | Returns the list. |

### Class `Box`: a copy of the run script with dummies in a temporary folder (lines 904 to 991)

| Line | Source | Explanation |
|---:|---|---|
| 904 | `class Box:` | Starts the class `Box`. It is the test setup for the run script. |
| 905 | `    """A copy of run_bwx9.sh and hostwatch.py with a test schedule and the dummy binary in a temporary folder."""` | Description text of the class: a copy of `run_bwx9.sh` and of `hostwatch.py`, with a test schedule and the dummy binary, in a temporary folder. |
| 907 | `    def __init__(self, tmp, sched):` | Starts the constructor. `sched` is the generated folder with the test divisor 100. |
| 908 | `        self.dir = os.path.join(tmp, "box")` | `dir`: the folder `box` in the temporary folder. |
| 909 | `        os.makedirs(self.dir)` | Creates it. |
| 910 | `        shutil.copy(RUN, self.dir)` | Copies the run script into the box. The test runs this copy, so the script finds its files beside itself. |
| 911 | `        shutil.copy(WATCH, self.dir)` | Copies the host sampler into the box. |
| 912 | `        shutil.copytree(sched, os.path.join(self.dir, "sched9"))` | Copies the generated folder into the box under the name `sched9`, the folder name that the run script reads. |
| 913 | `        self.bin = os.path.join(self.dir, "bwx8")` | `bin`: the path of the dummy binary in the box, with the file name `bwx8`. |
| 914 | `        with open(self.bin, "w") as f:` | Opens it for writing. |
| 915 | `            f.write(DUMMY)` | Writes the text `DUMMY`. |
| 916 | `        os.chmod(self.bin, 0o755)` | Makes the dummy executable. |
| 917 | `        with open(os.path.join(self.dir, "build.txt"), "w") as f:` | Opens the file `build.txt` in the box for writing. The run script asks for a build record beside the binary. |
| 918 | `            f.write("dummy build record\n")` | Writes one line of text as a dummy build record. |
| 919 | `        os.makedirs(os.path.join(self.dir, "bin"))` | Creates the folder `bin` in the box. |
| 920 | `        stub = os.path.join(self.dir, "bin", "ps")` | `stub`: the path of the stand-in for `ps` in that folder. |
| 921 | `        with open(stub, "w") as f:` | Opens it for writing. |
| 922 | `            f.write(PS_STUB % shutil.which("ps"))` | Writes the text `PS_STUB` with the path of the real `ps` put in. `shutil.which` finds that path. |
| 923 | `        os.chmod(stub, 0o755)` | Makes the stand-in executable. |
| 924 | `        os.makedirs(os.path.join(self.dir, "nopy"))` | Creates the folder `nopy` in the box. It becomes a search path without `python3`. |
| 925 | `        for t in TOOLS:` | Starts a loop over the program names of `TOOLS`. |
| 926 | `            os.symlink(shutil.which(t), os.path.join(self.dir, "nopy", t))` | Puts a link to the real program into the folder `nopy`. |
| 927 | `        allowed = sorted(os.sched_getaffinity(0))` | `allowed`: the CPUs on which this test may run, in sorted order. |
| 928 | `        self.watch_cpu = str(allowed[-1])` | `watch_cpu`: the highest allowed CPU, as text. The cases of the box use it as `WATCH_CPU`, the CPU of the host sampler. The default of the run script, CPU 100, does not exist on every machine. |
| 929 | `        self.n = 0` | `n`: the number of the last test case, 0 at first. |
| 931 | `    def rows(self, step, session=1):` | Starts the method `rows`. |
| 932 | `        text = open(os.path.join(self.dir, "sched9", "s%d" % session, step + ".tsv")).read()` | Reads the schedule file of a step and session from the box. |
| 933 | `        return [r.split("\t") for r in text.split("\n")[1:-1]]` | Returns its data rows, each split at the tabs. |
| 935 | `    def start(self, args, pre=(), **env):` | Starts the method `start`. `args`: the arguments for the run script. `pre`: words to put before the script, for example a `taskset` command. `env`: settings for its environment. |
| 936 | `        """Starts the script in fresh result, marker and log paths. Returns the process."""` | Description text: the method starts the script with new paths for the results, the marker file and the log. It returns the process. |
| 937 | `        self.n += 1` | Counts the test case. |
| 938 | `        self.case = os.path.join(self.dir, "case%d" % self.n)` | `case`: a folder of its own for this case, `case` plus the number. |
| 939 | `        os.makedirs(self.case)` | Creates it. |
| 940 | `        self.results = os.path.join(self.case, "results")` | `results`: the place for the result folders of this case. |
| 941 | `        self.marker = os.path.join(self.case, "RUNNING")` | `marker`: the path that takes the place of the marker file in this case. |
| 942 | `        self.stopfile = os.path.join(self.case, "STOP")` | `stopfile`: the path that takes the place of the stop file. |
| 943 | `        self.log = os.path.join(self.case, "dummy.log")` | `log`: the log file of the dummies. |
| 944 | `        e = {k: v for k, v in os.environ.items()` | `e`: the environment for the script. It starts as a copy of the environment of the test without the settings that the script reads. |
| 945 | `             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED", "BWX8_SHA256",` | The names that are left out, first part: the stop time, the two session settings, `RESERVE`, the variable `_PINNED` of the CPU limit, and the digest setting. |
| 946 | `                          "BWX_PMU_TYPE", "BWX_EVENTS", "WATCH_CPU")}` | More names that are left out: the two counter settings and `WATCH_CPU`. So nothing from the shell of the developer changes a test case. |
| 947 | `        e.update(HOME=self.case, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_BIN=self.bin,` | Adds the settings of the case: the case folder as the home folder, and the test paths of the marker file, of the stop file and of the binary. |
| 948 | `                 BWX8_RESULTS=self.results, DUMMY_LOG=self.log, WATCH_CPU=self.watch_cpu)` | Continues the settings: the place of the result folders, the log of the dummies, and the CPU of the host sampler. With these test settings the script never touches the real marker file or a real binary. |
| 949 | `        e.update(env)` | Adds the settings that the caller gave. They replace the defaults of the case. |
| 950 | `        e = {k: v for k, v in e.items() if v is not None}      # None: leave this setting out` | Removes every setting whose value is `None`. So a caller can take a default away. |
| 951 | `        return subprocess.Popen(list(pre) + [os.path.join(self.dir, "run_bwx9.sh")] + args, env=e, text=True,` | Starts the copy of the run script in the box with the arguments, after the words of `pre`, and returns the process object. The call does not wait for the end of the script. |
| 952 | `                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)` | Continues the call: the environment `e`, text mode, and pipes for the output and the error output. `start_new_session=True` gives the script a session of its own, so a signal of the test reaches only it. |
| 954 | `    def run(self, args, pre=(), **env):` | Starts the method `run`: start the script and wait for its end. |
| 955 | `        p = self.start(args, pre, **env)` | Starts the script. |
| 956 | `        out, err = p.communicate(timeout=600)` | Waits for the end, for at most 600 s, and reads the output and the error output. |
| 957 | `        return p.returncode, out, err` | Returns the exit status, the output and the error output. |
| 959 | `    def folder(self):` | Starts the method `folder`. |
| 960 | `        d = os.listdir(self.results) if os.path.isdir(self.results) else []` | `d`: the names in the results place of the case, or an empty list when that folder does not exist. |
| 961 | `        return os.path.join(self.results, d[0]) if len(d) == 1 else None` | Returns the path of the result folder when exactly one exists, and `None` in every other case. |
| 963 | `    def file(self, name):` | Starts the method `file`. It reads one file of the result folder. |
| 964 | `        f = self.folder()` | `f`: the result folder, or `None`. |
| 965 | `        path = os.path.join(f, name) if f else ""` | `path`: the path of the file, or an empty text without a folder. |
| 966 | `        return open(path).read() if os.path.exists(path) else ""` | Returns the content of the file, or an empty text when the file does not exist. |
| 968 | `    def csv(self, step):` | Starts the method `csv`. |
| 969 | `        return self.file(step + ".csv")` | Returns the content of the output file `<STEP>.csv` of a step. |
| 971 | `    def launched(self):` | Starts the method `launched`. |
| 972 | `        return [l for l in open(self.log).read().split("\n") if l] if os.path.exists(self.log) else []` | Returns the lines of the dummy log that are not empty. Each launch gives two lines: the line of the dummy with its process id and options, and the line of its sleep. |
| 974 | `    def wait_launch(self, watch=None):` | Starts the method `wait_launch`. It waits until the run script has started a dummy. |
| 975 | `        """Waits for the dummy and its sleep. watch: also for the scan line of this sampler file."""` | Description text: the method waits for the dummy and its sleep. With `watch` it also waits until the sampler file of that name holds its scan line. |
| 976 | `        end = time.time() + 90` | `end`: 90 s from now. |
| 977 | `        while time.time() < end and (len(self.launched()) < 2 or (watch and "# scan" not in self.file(watch))):` | Starts the wait loop. It ends at the latest when the 90 s are over. Before that it runs while the dummy log has fewer than 2 lines. With `watch` it also runs while the named sampler file does not yet hold the text `# scan`. |
| 978 | `            time.sleep(0.2)` | Waits 0.2 s per turn. |
| 979 | `        return len(self.launched()) >= 2 and (not watch or "# scan" in self.file(watch))` | Returns true when the dummy and its sleep were logged and, with `watch`, the sampler wrote its scan line. So the case that follows acts on a process and a sampler that really run. |
| 981 | `    def none_alive(self):` | Starts the method `none_alive`. It tests that the script left no process behind. |
| 982 | `        time.sleep(0.5)` | Waits 0.5 s first. |
| 983 | `        for l in self.launched():` | Starts a loop over the lines of the dummy log. Each starts with a process id, of a dummy or of its sleep. |
| 984 | `            try:` | Starts the block whose error is caught. |
| 985 | `                os.kill(int(l.split()[0]), 0)` | `os.kill` with the signal 0 sends nothing. It only tests whether the process exists. |
| 986 | `                return False` | The process exists: returns false. |
| 987 | `            except OSError:` | The process does not exist. |
| 988 | `                pass` | Goes on with the next line. |
| 989 | `        return not samplers(self.case)` | Returns true when also no host sampler of this case is running. |

### `visit_checks`: the visit script with a stand-in for `ssh` (lines 992 to 1034)

| Line | Source | Explanation |
|---:|---|---|
| 992 | `def visit_checks(tmp):` | Starts the function `visit_checks`: the checks of the visit script. |
| 993 | `    """visit9.sh with a stand-in ssh. PATH holds only the stand-in and date, so no real ssh can start."""` | Description text: the function tests `visit9.sh` with a stand-in for `ssh`. The search path holds only the stand-in and `date`. So no real `ssh` can start. |
| 994 | `    d = os.path.join(tmp, "visit")` | `d`: the folder `visit` in the temporary folder. |
| 995 | `    os.makedirs(os.path.join(d, "bin"))` | Creates it with a folder `bin` inside. |
| 996 | `    text, n = re.subn(r"(?m)^N=.*$", "N=" + d, open(VISIT).read())` | Reads the visit script and replaces its line that starts with `N=`, the log folder, with a line that names `d`. `(?m)` lets `^` and `$` match at the start and the end of every line. `n` is the number of lines replaced. |
| 997 | `    copy_path = os.path.join(d, "visit9.sh")` | `copy_path`: the path of the changed copy of the visit script. |
| 998 | `    with open(copy_path, "w") as f:` | Opens the copy for writing. |
| 999 | `        f.write(text)` | Writes the changed text. |
| 1000 | `    with open(os.path.join(d, "bin", "ssh"), "w") as f:` | Opens the file `ssh` in the folder `bin` for writing. |
| 1001 | `        f.write(SSH_STUB)` | Writes the stand-in text `SSH_STUB`. |
| 1002 | `    os.chmod(os.path.join(d, "bin", "ssh"), 0o755)` | Makes the stand-in executable. |
| 1003 | `    os.symlink(shutil.which("date"), os.path.join(d, "bin", "date"))` | Puts a link to the real tool `date` into the folder `bin`. The visit script needs `date` for its status line. |
| 1004 | `    log = os.path.join(d, "ssh.log")` | `log`: the file in which the stand-in records each remote command. |
| 1006 | `    def visit(name, **env):` | Starts the inner function `visit`. It runs the copy once, with a log name and with settings. |
| 1007 | `        if os.path.exists(log):` | When a record of an earlier call exists. |
| 1008 | `            os.remove(log)` | Removes it. |
| 1009 | `        e = {"PATH": os.path.join(d, "bin"), "SSH_LOG": log, "HOME": d}` | `e`: the whole environment of the script: a search path with only the folder `bin`, the record file for the stand-in, and `d` as the home folder. |
| 1010 | `        e.update(env)` | Adds the settings of the caller. |
| 1011 | `        r = subprocess.run([shutil.which("bash"), copy_path, name, "XEV", "XW"], env=e, capture_output=True, text=True)` | Runs the copy with `bash`, with the log name and the two step names `XEV` and `XW` as arguments. The test finds the path of `bash` itself. The search path that the copy gets does not hold `bash`. |
| 1012 | `        return r.returncode, open(log).read() if os.path.exists(log) else None, r.stderr` | Returns the exit status, the recorded remote command (`None` when the stand-in was never called), and the error output. |
| 1014 | `    rc, cmd, err = visit("ok", STOP_AT="2026-11-15T15:00Z", SESSION="2", SESSION1_END="2026-11-15T03:00Z",` | Runs the copy with a full set of valid settings: a stop time, session 2, the end of session 1. |
| 1015 | `                         BWX8_SHA256="0a1b", ENVV="WATCH_CPU=100")` | Continues the settings: a digest value, and the text `WATCH_CPU=100` in `ENVV`. |
| 1016 | `    check("visit9.sh: one login; the marker check is the first remote action, then run_bwx9.sh in ~/cache-perf/bwx8-20261114",` | Starts a check: the visit script makes one login. The marker check is the first remote action, and `run_bwx9.sh` in the folder `~/cache-perf/bwx8-20261114` follows. |
| 1017 | `          n == 1 and rc == 0 and cmd is not None and cmd.count("\n") == 1` | The test, first conditions: exactly one `N=` line was replaced, the exit status is 0, the stand-in was called, and its record has exactly one line. One line means one login. |
| 1018 | `          and cmd.startswith("if [ -e /tmp/positron-perf.RUNNING ]; then ")` | Continues: the remote command starts with the test for the marker file `/tmp/positron-perf.RUNNING`. So nothing can start on CRB before the marker file was tested. |
| 1019 | `          and cmd.endswith("exit 3; fi; cd ~/cache-perf/bwx8-20261114 && STOP_AT=2026-11-15T15:00Z SESSION=2 "` | Continues: the remote command ends with the exact text that is expected. This line: the end of the marker check with `exit 3`, the `cd` into the folder on CRB, and the settings `STOP_AT` and `SESSION`. |
| 1020 | `                           "SESSION1_END=2026-11-15T03:00Z BWX8_SHA256=0a1b WATCH_CPU=100 ./run_bwx9.sh XEV XW\n")` | Ends the expected text: `SESSION1_END`, the digest, the text of `ENVV`, and the script `./run_bwx9.sh` with the two step names. So every setting reaches the run script, and the steps keep their order. |
| 1021 | `          and open(os.path.join(d, "ok.log")).read().startswith("ssh status 0 utc "), (rc, cmd, err))` | Last condition: the log file `ok.log` starts with `ssh status 0 utc`. So the visit script wrote the status of `ssh` to its log. |
| 1022 | `    ok = {"STOP_AT": "2026-11-15T15:00Z", "SESSION": "2", "SESSION1_END": "2026-11-15T03:00Z", "BWX8_SHA256": "0a1b"}` | `ok`: a set of valid values for the four settings that the visit script checks. |
| 1023 | `    for var, value in (("SESSION1_END", "2026-11-15 03:00"), ("STOP_AT", "2026-11-15 15:00"),` | Starts a loop over bad values, each for one setting. This line: two times that hold a blank. |
| 1024 | `                       ("STOP_AT", "none;id"), ("SESSION", "1$(id)"), ("BWX8_SHA256", "0a1b\|x")):` | Continues the list with three values that hold a shell character: a semicolon with a second command, a command substitution, and a vertical bar. |
| 1025 | `        rc, cmd, err = visit("bad", **dict(ok, **{var: value}))` | Runs the copy with the valid set in which this one setting has the bad value. |
| 1026 | `        check("visit9.sh: %s='%s' is refused with status 2 before the login, no log file" % (var, value),` | Starts a check per value: the visit script refuses it with status 2 before the login and writes no log file. |
| 1027 | `              rc == 2 and cmd is None and var in err and not os.path.exists(os.path.join(d, "bad.log")), (rc, cmd, err))` | The test: exit status 2, the stand-in was never called, the error output names the setting, and no file `bad.log` exists. This matters: such a value would become a part of the command line on CRB and could run another command there. |
| 1028 | `    rc, cmd, err = visit("nostop", SESSION="1")` | Runs the copy without `STOP_AT`. |
| 1029 | `    check("visit9.sh: STOP_AT not set: no login", rc != 0 and cmd is None, (rc, cmd, err))` | Check: without `STOP_AT` the exit status is not 0, and the stand-in was never called. So no login is made without a decision about the stop time. |
| 1030 | `    a, b = open(os.path.join(X, "visit8.sh")).read().split("\n"), open(VISIT).read().split("\n")` | `a`: the lines of `visit8.sh`, the visit script of round 1 in the same folder. `b`: the lines of `visit9.sh`. |
| 1031 | `    check("visit9.sh differs from visit8.sh only in comment lines and in the name of the script that it starts",` | Starts a check: `visit9.sh` differs from `visit8.sh` only in comment lines and in the name of the script that it starts. |
| 1032 | `          [l for l in a if not l.startswith("#")] == [l.replace("./run_bwx9.sh", "./run_bwx8.sh") for l in b if not l.startswith("#")])` | The test: the lines of `visit8.sh` that do not start with `#` are equal to those of `visit9.sh`, when `./run_bwx9.sh` is replaced by `./run_bwx8.sh` in them. So the checks before the login are the same as in the visit script of round 1. |

### `run_checks`: syntax, the copied stop controls, step names and the dry run (lines 1035 to 1077)

| Line | Source | Explanation |
|---:|---|---|
| 1035 | `def run_checks(tmp, sched):` | Starts the function `run_checks`: the checks of the run script. `sched` is the generated folder with the test divisor 100. |
| 1036 | `    for f in ("run_bwx9.sh", "visit9.sh"):` | Starts a loop over the two shell scripts under test. |
| 1037 | `        r = subprocess.run(["bash", "-n", os.path.join(X, f)], capture_output=True, text=True)` | Runs `bash -n` on the script. With `-n` the shell reads the whole script and reports syntax errors, but it runs none of its commands. |
| 1038 | `        check("bash -n " + f, r.returncode == 0, r.stderr)` | Check, once per script: `bash -n` ends with status 0. So the script has no syntax error. |
| 1039 | `    # The stop controls are the text of run_bwx8.sh: every line of these functions is in both files.` | Comment: the stop controls are the text of `run_bwx8.sh`, the run script of round 1. Every line of these functions stands in both files. |
| 1040 | `    old, new = open(os.path.join(X, "run_bwx8.sh")).read(), open(RUN).read()` | `old`: the text of `run_bwx8.sh`. `new`: the text of `run_bwx9.sh`. |
| 1041 | `    kept = [l for l in old.split("\n") if re.match(r"^(why_stop\|check_marker\|check_deadline\|trap\|settle)\b\|^  (if \[\[ -e \$(MARKER\|STOPFILE)\|if \(\( STOP_EPOCH)", l)]` | `kept`: the lines of the older script that hold the stop controls. The pattern selects a line that starts with one of the words `why_stop`, `check_marker`, `check_deadline`, `trap` or `settle`. It also selects a line that starts with two blanks and one of the three tests inside `why_stop`: the marker file, the stop file or `STOP_EPOCH`. |
| 1042 | `    check("run_bwx9.sh keeps the lines of why_stop, check_marker, check_deadline, settle and the trap of run_bwx8.sh unchanged",` | Starts a check: `run_bwx9.sh` keeps the lines of `why_stop`, `check_marker`, `check_deadline`, `settle` and of the trap unchanged from `run_bwx8.sh`. |
| 1043 | `          len(kept) == 8 and all(new.count(l) == 1 for l in kept), [l[:60] for l in kept if new.count(l) != 1])` | The test: the pattern found 8 lines in the older script, and each of them stands exactly once in the new script. So the stop rules of round 1 are the same text in round 2. The detail lists the lines that are missing or doubled. |
| 1044 | `    check("run_bwx9.sh: stop_child is the line of run_bwx8.sh with the stop of the sampler added at its end",` | Starts a check: the line of `stop_child` is the line of `run_bwx8.sh` with the stop of the sampler added at its end. |
| 1045 | `          re.search(r"(?m)^stop_child\(\) .*$", old).group(0)[:-2] + " stop_watch; }" == re.search(r"(?m)^stop_child\(\) .*$", new).group(0))` | The test: the old line without its last two characters, plus the text `stop_watch` with a semicolon and the closing brace, is equal to the new line. The pattern finds the line that starts with `stop_child()`. So the only change of `stop_child` is the added call of `stop_watch`. |
| 1046 | `    box = Box(tmp, sched)` | `box`: a new test setup with a copy of the run script, the dummies and the schedule with the test divisor 100. |
| 1048 | `    # ---- steps and the dry run ----` | Comment: the checks of the step names and of the dry run start here. |
| 1049 | `    for name in ("S2", "C4", "Xw", "X", "X-1", "XW;id"):` | Starts a loop over six step names that must be refused: two step names of round 1 (`S2`, `C4`), a name with a lower-case letter (`Xw`), the letter `X` alone, a name with a hyphen, and a name with a semicolon and a second command. |
| 1050 | `        rc, out, err = box.run(["--dry-run", name], SESSION="1")` | Runs the script in a dry run with that name. |
| 1051 | `        check("step name '%s' is refused with status 2" % name, rc == 2 and "unknown step" in err and not out, (rc, err))` | Check, once per name: exit status 2, the message `unknown step` in the error output, and no output. So only a name of the right form can select a schedule, and a name cannot hold a shell command that would run. |
| 1052 | `    rc, out, err = box.run(["--dry-run", "XZ9"], SESSION="1")` | Runs a dry run with the name `XZ9`, which has the right form but no schedule. |
| 1053 | `    check("a name of the right form without a schedule: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))` | Check: exit status 2 and the message `missing schedule`. |
| 1054 | `    rc, out, err = box.run(["--dry-run", "XN", "XN"], SESSION="1")` | Runs a dry run that names the step `XN` twice. |
| 1055 | `    check("a step named twice: status 2", rc == 2 and "twice" in err and "step XN" not in out, (rc, err))` | Check: exit status 2, the word `twice` in the error output, and no summary line of the step in the output. So the script refuses the call before it prints or runs anything of the step. A step that runs twice in one call would repeat its processes. |
| 1056 | `    rc, out, err = box.run(["--dry-run", "XEV", "XW", "XCA", "XCB", "XCC", "XN", "XF"], SESSION="1")` | Runs a dry run of all 7 steps for session 1. The environment holds no counter setting. |
| 1057 | `    want = {"XEV": "3 processes, nominal kernel work 0.027 s", "XW": "28 processes, nominal kernel work 8.640 s",` | `want`: the summary text that the script must print for each step. The schedule of the box has the test divisor 100, so the nominal work is one hundredth of the real value: 0.027 s for `XEV` and 8.640 s for `XW`. |
| 1058 | `            "XCA": "18 processes, nominal kernel work 3.960 s", "XCB": "18 processes, nominal kernel work 3.960 s",` | Continues the texts: 18 processes and 3.960 s for `XCA` and for `XCB`. |
| 1059 | `            "XCC": "18 processes, nominal kernel work 3.960 s", "XN": "144 processes, nominal kernel work 13.824 s",` | Continues the texts: 18 processes and 3.960 s for `XCC`, and 144 processes and 13.824 s for `XN`. |
| 1060 | `            "XF": "90 processes, nominal kernel work 8.640 s"}` | Ends the texts: 90 processes and 8.640 s for `XF`. |
| 1061 | `    check("--dry-run of all 7 steps, session 1, without counter settings in the environment: status 0, the counts of each step",` | Starts a check: the dry run of all 7 steps, without counter settings in the environment, ends with status 0 and prints the counts of each step. |
| 1062 | `          rc == 0 and all(("step %s session 1: %s" % kv) in out for kv in want.items())` | The test, first half: exit status 0, and the output holds the expected summary text of every step. So the script adds up the same counts and the same nominal work as the generator. |
| 1063 | `          and out.count("\nbwx8 --trial ") == 319 and "warning" in err, (rc, out[:300], err[-300:]))` | Second half: the output holds 319 command lines that start with `bwx8 --trial`, one per process of session 1, and the error output holds a warning. The box sets the four test settings, and the script warns about each of them. |
| 1064 | `    check("--dry-run: the command lines are the args column, with the event options of the counter steps",` | Starts a check: the command lines of the dry run are the `args` column, with the event options of the counter steps. |
| 1065 | `          all(("bwx8 %s  # idx %s, tag %s, nominal " % (r[5], r[0], r[1])) in out` | The test, first half: for every row of every schedule, the output holds a line with the word `bwx8`, the `args` of the row, and after `#` its `idx` and its tag. |
| 1066 | `              for st in want for r in box.rows(st)) and out.count(" --pmu-type 11 --events ") == 57)` | The loops run over the 7 steps and their rows. Second half: the text `--pmu-type 11 --events` stands 57 times in the output. That is 3 processes of `XEV` and 18 of each of the three counter steps. |
| 1067 | `    check("--dry-run: the host sampler is announced for XW, XCA, XCB, XCC and for no other step",` | Starts a check: the dry run announces the host sampler for `XW`, `XCA`, `XCB` and `XCC`, and for no other step. |
| 1068 | `          sorted(re.findall(r"^step (\S+) host sampler: hostwatch.py on CPU %s " % box.watch_cpu, out, re.M)) == WATCH_STEPS, out[:500])` | The test: the lines of the form `step <name> host sampler: hostwatch.py on CPU <n>`, with the CPU of the box, name exactly the four steps of `WATCH_STEPS`. Group 1 of the pattern holds the step name. |
| 1069 | `    check("--dry-run: starts nothing and makes no result folder", not box.launched() and not os.path.exists(box.results))` | Check: the dry run started no dummy and made no result folder. |
| 1070 | `    rc, out, err = box.run(["--dry-run", "XW", "XN", "XF"], SESSION="2")` | Runs a dry run of three steps for session 2. |
| 1071 | `    check("--dry-run session 2: the first command line of each step uses CPU 41",` | Starts a check: in session 2 the first command line of each step uses CPU 41. |
| 1072 | `          rc == 0 and len(re.findall(r"# ---- step \S+ session 2 ----\n.*\n.*\n(?:step \S+ host sampler.*\n)?bwx8 --trial --cpus 41 ", out)) == 3, (rc, out[:500]))` | The test: exit status 0, and the pattern matches 3 times. It matches the heading line of a step for session 2, then two lines (the summary and the conditions), then an optional line about the host sampler, then a command line that starts with `bwx8 --trial --cpus 41`. So in session 2 each of the three steps starts on CPU 41, which is the reversed CPU order. |
| 1073 | `    rc, out, err = box.run(["--dry-run", "XEV"], SESSION="2")` | Runs a dry run of `XEV` for session 2. |
| 1074 | `    check("XEV in session 2: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))` | Check: exit status 2 and the message `missing schedule`. The step `XEV` has no schedule in session 2, so it cannot run there. |
| 1075 | `    rc, out, err = box.run(["--dry-run", "XN"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX8_RESULTS=None)` | Runs a dry run of `XN` with the four test settings taken away. The value `None` leaves a setting out. |
| 1076 | `    check("no warning without the test settings", rc == 0 and "warning" not in err, err)` | Check: exit status 0 and no warning. The warnings appear only for test settings. |

### `run_checks`: a normal run of step `XEV` (lines 1078 to 1103)

| Line | Source | Explanation |
|---:|---|---|
| 1078 | `    # ---- a normal run without sampler: XEV ----` | Comment: the checks of a normal run without the host sampler start here. The step is `XEV`. |
| 1079 | `    rows = box.rows("XEV")` | `rows`: the 3 rows of the schedule of `XEV` in the box. |
| 1080 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none")` | Runs the step `XEV` for real, with the dummy as the binary and without a stop time. |
| 1081 | `    f = box.folder()` | `f`: the one result folder of the case. |
| 1082 | `    csv = box.csv("XEV")` | `csv`: the content of the output file `XEV.csv`. |
| 1083 | `    heads = re.findall(r"^-- step XEV session 1 idx (\d+) tag (\S+) waited_s \d+ loadavg .* logins \d+ utc \S+ args (.*)$", csv, re.M)` | `heads`: the header lines of the processes in the output file. The pattern matches a line that starts with `-- step XEV session 1 idx`. Group 1 holds the `idx`, group 2 the tag, and group 3 the options after the word `args`. Between them the pattern asks for the fields `waited_s`, `loadavg`, `logins` and `utc`. |
| 1084 | `    check("XEV normal end: status 0, the counts are printed before the result folder is made",` | Starts a check of the normal end: status 0, and the counts are printed before the result folder is made. |
| 1085 | `          rc == 0 and 0 <= out.find("step XEV session 1: 3 processes") < out.find("result folder: "), (rc, err, out))` | The test: exit status 0, and the summary line of the step stands in the output before the line `result folder:`. So the script prints what it will run before it starts anything. |
| 1086 | `    check("XEV normal end: folder name bwx9-XEV-s1-<UTC> and its six files, no sampler file",` | Starts a check: the result folder has the name `bwx9-XEV-s1-<UTC>` and its six files, and no sampler file. |
| 1087 | `          f is not None and re.match(r"^bwx9-XEV-s1-\d{8}T\d{6}Z$", os.path.basename(f)) is not None` | The test, first half: exactly one result folder exists, and its name matches the pattern: `bwx9-XEV-s1-`, 8 digits, the letter `T`, 6 digits and the letter `Z`. |
| 1088 | `          and sorted(os.listdir(f)) == ["XEV.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv", "stderr.txt"],` | Second half: the folder holds exactly the six files `XEV.csv`, `build.txt`, `env.txt`, `launches.txt`, `schedule.tsv` and `stderr.txt`. A step without a `.watch` file gets no file of the sampler. |
| 1089 | `          f and os.listdir(f))` | The detail for a failure: the folder and its files. |
| 1090 | `    check("XEV normal end: one header line per process in schedule order, each followed by its output; schedule.tsv is a copy",` | Starts a check: the output file has one header line per process in schedule order, each followed by the output of its process, and `schedule.tsv` is a copy of the schedule. |
| 1091 | `          heads == [(r[0], r[1], r[5]) for r in rows] and csv.count("M,dummy,1\n") == 3 and "-- killed" not in csv` | The test, first part: the `idx`, the tag and the options of the header lines are those of the schedule rows, in the same order. The output line of the dummy stands 3 times. No line `-- killed` exists. |
| 1092 | `          and "-- failed" not in csv and box.file("schedule.tsv") == open(os.path.join(box.dir, "sched9", "s1", "XEV.tsv")).read(), heads)` | Second part: no line `-- failed` exists, and `schedule.tsv` in the result folder is equal to the schedule file of the box. So the result folder shows which schedule ran and in which order. |
| 1093 | `    launched = [l for l in box.launched() if not l.endswith(" sleep")]` | `launched`: the lines of the dummy log without the lines of the sleeps: one line per launch. |
| 1094 | `    check("XEV normal end: the binary gets the args column, with --pmu-type 11 and the event set, and no counter setting in its environment",` | Starts a check: the binary gets the `args` column as its options, with `--pmu-type 11` and the event set, and its environment holds no counter setting. |
| 1095 | `          [l.split(" ", 1)[1] for l in launched] == [r[5] for r in rows] and all(" --events " + EVENTS[e] in l for l, e in zip(launched, "ABC"))` | The test, first part: the options that each dummy recorded are the `args` of its schedule row, and the three launches hold the event sets A, B and C in this order. |
| 1096 | `          and open(box.log + ".env").read() == "PMU= EV=\n" * 3 and box.none_alive(), launched)` | Second part: each of the 3 dummies recorded empty values of `BWX_PMU_TYPE` and `BWX_EVENTS`, and no process is left. So for these schedules the counter options reach the binary through the `args` column alone. |
| 1097 | `    env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1098 | `    check("XEV normal end: env.txt holds session, from, load, digests of bwx8, run_bwx9.sh, schedule and build record, paths, end line",` | Starts a check of `env.txt`: it holds the session, the `--from` value, the load, the digests of the binary, of `run_bwx9.sh`, of the schedule and of the build record, the paths and the end line. |
| 1099 | `          "session=1 from=0 " in env and "loadavg=" in env and "## end utc=" in env and "/run_bwx9.sh\n" in env` | The test, first part: the file holds `session=1 from=0`, a `loadavg=` value, the end line `## end utc=`, and a digest line that ends with `/run_bwx9.sh`. |
| 1100 | `          and "/sched9/s1/XEV.tsv\n" in env and "host sampler" not in env` | Second part: a digest line ends with the path of the schedule file, and the file holds no line about the host sampler. |
| 1101 | `          and (" MARKER=%s STOPFILE=%s BIN=%s RESULTS=%s\n" % (box.marker, box.stopfile, box.bin, box.results)) in env` | Third part: the settings line ends with the four paths in use: the marker file, the stop file, the binary and the results place of this case. So the record shows whether a run used test paths or the real ones. |
| 1102 | `          and box.file("launches.txt").count("== XEV.csv idx ") == 3, env)` | Last part: `launches.txt` holds 3 load records, one per launch. So the load of the machine is recorded before every process. |

### `run_checks`: the rule for the counter settings (lines 1104 to 1126)

| Line | Source | Explanation |
|---:|---|---|
| 1104 | `    # ---- the rule for the counter settings ----` | Comment: the checks of the rule for the counter settings start here. |
| 1105 | `    tsv = os.path.join(box.dir, "sched9", "s1", "XEV.tsv")` | `tsv`: the path of the schedule file of `XEV` in the box. |
| 1106 | `    saved = open(tsv).read()` | `saved`: its content, kept to restore it later. |
| 1107 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1108 | `        fh.write(re.sub(r" --pmu-type 11 --events \S+", "", saved))` | Writes the schedule without the counter options: the pattern removes `--pmu-type 11 --events` and the event text from every row. The plans still have the counter mode `read`. |
| 1109 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none")` | Runs the step with this schedule and without counter settings in the environment. |
| 1110 | `    check("a counted step without the options in args and without BWX_PMU_TYPE and BWX_EVENTS: status 2, nothing starts",` | Starts a check: a step that uses counters, without the options in the `args` and without the two environment settings, ends with status 2 and starts nothing. |
| 1111 | `          rc == 2 and "needs BWX_PMU_TYPE" in err and not box.launched() and open(tsv).read() != saved, (rc, err))` | The test: exit status 2, the message that the step needs `BWX_PMU_TYPE`, no launch, and a schedule file that really differs from the saved one. So the script finds a trial that counts without counter options before it starts anything. |
| 1112 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11")` | Runs the same again with `BWX_PMU_TYPE` set and `BWX_EVENTS` missing. |
| 1113 | `    check("the same with BWX_PMU_TYPE only: status 2, nothing starts", rc == 2 and "needs BWX_EVENTS" in err and not box.launched(), (rc, err))` | Check: exit status 2, the message that the step needs `BWX_EVENTS`, and no launch. Both settings are needed. |
| 1114 | `    rc, out, err = box.run(["--from", "2", "XEV"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11", BWX_EVENTS="a=0x11")` | Runs the last process of the step (`--from 2`) with both settings in the environment. |
| 1115 | `    check("the same with both settings: runs, and the binary finds them in its environment",` | Starts a check: with both settings the process runs, and the binary finds them in its environment. |
| 1116 | `          rc == 0 and len(box.launched()) == 2 and open(box.log + ".env").read() == "PMU=11 EV=a=0x11\n", (rc, err))` | The test: exit status 0, one launch, and the dummy recorded `PMU=11` and the event text. So the script exports the two settings to the runner. |
| 1117 | `    rc, out, err = box.run(["--dry-run", "XEV"], SESSION="1", BWX_PMU_TYPE="eleven", BWX_EVENTS="a=0x11")` | Runs a dry run with the word `eleven` as `BWX_PMU_TYPE`. |
| 1118 | `    check("BWX_PMU_TYPE that is not a whole number: status 2", rc == 2 and "whole number" in err, (rc, err))` | Check: exit status 2 and the words `whole number`. The type number must hold digits only. |
| 1119 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1120 | `        fh.write(saved)` | Writes the saved content back. The schedule of `XEV` has its counter options again. |
| 1121 | `    rc, out, err = box.run(["--from", "143", "XN"], SESSION="1", STOP_AT="none")` | Runs the last process of step `XN` (`--from 143`), without counter settings. |
| 1122 | `    check("an uncounted step (XN, count closed, no options in args) needs no counter setting: runs",` | Starts a check: a step without counters needs no counter setting. `XN` has the counter mode `closed` and no counter options in its `args`. |
| 1123 | `          rc == 0 and len(box.launched()) == 2 and "--plan sched9/s1/XN/0143.plan" in box.launched()[0]` | The test, first part: exit status 0, one launch, and the dummy got the plan path of process 143. |
| 1124 | `          and re.findall(r"^-- step XN session 1 idx (\d+) ", box.csv("XN"), re.M) == ["143"]` | Second part: the output file holds exactly one header line, with the `idx` 143. |
| 1125 | `          and " from=143 " in box.file("env.txt") and "to run from idx 143: 1 processes" in out, (rc, err))` | Third part: `env.txt` records `from=143`, and the summary says that 1 process runs from `idx` 143. So `--from` runs the rest of a step only and leaves a record of it. |

### `run_checks`: the host sampler beside a process (lines 1127 to 1159)

| Line | Source | Explanation |
|---:|---|---|
| 1127 | `    # ---- the host sampler ----` | Comment: the checks of the host sampler beside a process start here. |
| 1128 | `    row = box.rows("XW")[27]` | `row`: the last row of the schedule of `XW`, the one with the `idx` 27. |
| 1129 | `    rc, out, err = box.run(["--from", "27", "XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="2")` | Runs that one process. The dummy sleeps 2 s, so the sampler has time to take samples. |
| 1130 | `    f = box.folder()` | `f`: the one result folder of the case. |
| 1131 | `    w = box.file("watch-27.txt")` | `w`: the content of the sampler file of this process. |
| 1132 | `    pid = box.launched()[0].split()[0] if box.launched() else "?"` | `pid`: the process id of the dummy, from the first line of the dummy log. |
| 1133 | `    check("XW with the sampler: status 0, watch-27.txt and watch-stderr.txt beside the six files, nothing in watch-stderr.txt",` | Starts a check: with the sampler the script ends with status 0, the sampler files lie beside the six files, and `watch-stderr.txt` is empty. |
| 1134 | `          rc == 0 and f is not None and sorted(os.listdir(f)) == ["XW.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv",` | The test, first part: exit status 0, one result folder, and exactly this list of files. This line: the five files `XW.csv`, `build.txt`, `env.txt`, `launches.txt` and `schedule.tsv`. |
| 1135 | `                                                                   "stderr.txt", "watch-27.txt", "watch-selftest.txt", "watch-stderr.txt"]` | Ends the list: `stderr.txt`, the sampler file `watch-27.txt`, the file of the start check `watch-selftest.txt`, and `watch-stderr.txt`. |
| 1136 | `          and box.file("watch-stderr.txt") == "" and box.file("stderr.txt") == "", (rc, err, f and os.listdir(f), box.file("watch-stderr.txt")))` | Second part: `watch-stderr.txt` and `stderr.txt` are empty. So neither the sampler nor the dummy printed a message. |
| 1137 | `    check("XW with the sampler: it watched the benchmark process and the CPU of the schedule row, for at most nominal time + 30 s",` | Starts a check: the sampler watched the benchmark process and the CPU of the schedule row, for at most the nominal time plus 30 s. |
| 1138 | `          w.startswith("# hostwatch v1 pid=%s cpu=%s hz=20 max_s=31\n" % (pid, row[2])), w[:200])` | The test: the first line of the sampler file names the process id of the dummy, the CPU of the schedule row and `max_s=31`. With the test divisor 100 the process has less than 1 s of nominal work, which the script rounds up to 1 s. Then it adds 30 s. |
| 1139 | `    m = re.search(r"\n# end reason=(\w+) samples=(\d+) ", w)` | `m`: the footer line of the sampler file. Group 1 holds the end reason and group 2 the number of samples. |
| 1140 | `    check("XW with the sampler: it sampled while the benchmark ran (20 or more samples in 2 s) and ended with the benchmark",` | Starts a check: the sampler took samples while the benchmark ran, and it ended with the benchmark. |
| 1141 | `          m is not None and m.group(1) in ("pid_gone", "signal") and int(m.group(2)) >= 20 and w.endswith("\n")` | The test, first part: the footer exists, its reason is `pid_gone` or `signal`, it counts at least 20 samples, and the file ends with a newline. Both reasons are a normal end here: the sampler saw that the process was gone, or the script ended the sampler first. 2 s at 20 samples per second give about 40 samples. |
| 1142 | `          and box.none_alive(), (m and m.groups(), w[-200:]))` | Second part: no dummy and no sampler of the case is left. |
| 1143 | `    check("XW with the sampler: the samples hold the threads of the benchmark process (m. keys)",` | Starts a check: the samples hold the values of the threads of the benchmark process. |
| 1144 | `          " ABS " in w and " m.run_ns=" in w and " m.nivcsw=" in w)` | The test: the file holds an absolute line and the keys `m.run_ns` and `m.nivcsw` of the main thread. So the sampler could read the threads of the process whose id the script gave it. |
| 1145 | `    env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1146 | `    check("XW with the sampler: env.txt records the CPU of the sampler and the digest of hostwatch.py",` | Starts a check: `env.txt` records the CPU of the sampler and the digest of `hostwatch.py`. |
| 1147 | `          re.search(r"^## host sampler: WATCH_CPU=%s Python \S+ sha256 %s$" % (` | The test: `env.txt` holds a line `## host sampler:` with `WATCH_CPU=` and a CPU, the word `Python` with a version, and `sha256` with a digest. |
| 1148 | `              box.watch_cpu, subprocess.run(["sha256sum", WATCH], capture_output=True, text=True).stdout.split()[0]), env, re.M) is not None, env)` | The two values of the pattern: the CPU of the box, and the sha256 of `hostwatch.py` that the test computes itself with `sha256sum`. So the result folder shows which sampler text ran and on which CPU. |
| 1149 | `    cpus = open(box.log + ".cpus").read()` | `cpus`: the CPU list that the dummy recorded. |
| 1150 | `    check("XW with the sampler: the sampler ran pinned to WATCH_CPU only, and the benchmark kept the CPUs 0-119",` | Starts a check: the sampler ran on `WATCH_CPU` only, and the benchmark kept the CPUs 0 to 119. |
| 1151 | `          cpu_list(cpus) == {c for c in os.sched_getaffinity(0) if c < 120}` | The test, first half: the CPU list of the dummy is the set of the CPUs below 120 on which the test may run. So the start of the sampler did not change the CPU list of the benchmark. |
| 1152 | `          and re.search(r"^# sampler pid=\d+ allowed_cpus=%s$" % box.watch_cpu, w, re.M) is not None, (cpus, w[:400]))` | Second half: the header of the sampler file records `allowed_cpus=` with the one CPU of the box. So `taskset` limited the sampler to that CPU, and the sampler cannot run on the CPU of the benchmark. |
| 1154 | `    rc, out, err = box.run(["--from", "26", "XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="1")` | Runs the last two processes of `XW` (`--from 26`), each with a sleep of 1 s. |
| 1155 | `    check("XW, two processes: one sampler file per process, named by idx, each with header and footer",` | Starts a check: two processes give one sampler file each, named by the `idx`, each with its header and its footer. |
| 1156 | `          rc == 0 and all(box.file("watch-%d.txt" % i).startswith("# hostwatch v1 pid=") and "\n# end reason=" in box.file("watch-%d.txt" % i)` | The test, first part: exit status 0, and each of the two files starts with the version line and holds a footer line. |
| 1157 | `                          for i in (26, 27)) and box.file("watch-26.txt").split("\n")[0] != box.file("watch-27.txt").split("\n")[0]` | The loop runs over the files `watch-26.txt` and `watch-27.txt`. Second part: their first lines differ. So each sampler watched its own process. |
| 1158 | `          and box.none_alive(), (rc, err))` | Third part: no process of the case is left. |

### `run_checks`: stops with a sampler, `WATCH_CPU`, missing `python3` or `hostwatch.py` (lines 1160 to 1232)

| Line | Source | Explanation |
|---:|---|---|
| 1160 | `    p = box.start(["XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the whole step `XW` in the background. The dummy sleeps 300 s, so the first process still runs when the test acts. |
| 1161 | `    up = box.wait_launch("watch-0.txt")` | `up`: true when the first dummy runs and the sampler file `watch-0.txt` holds its scan line. |
| 1162 | `    alive_before = len(samplers(box.case))` | `alive_before`: the number of running samplers of this case, before the stop. |
| 1163 | `    open(box.stopfile, "w").close()` | Creates the stop file of the case. |
| 1164 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script, for at most 60 s. |
| 1165 | `    tag = box.rows("XW")[0][1]` | `tag`: the tag of the first process of `XW`. |
| 1166 | `    check("XW, stop file during a process: status 5, '-- killed', the benchmark and its sampler are gone, the sampler file has its footer",` | Starts a check: the stop file appears during a process. Expected: status 5, a line `-- killed`, no benchmark and no sampler left, and a footer in the sampler file. |
| 1167 | `          up and alive_before == 1 and p.returncode == 5 and ("-- killed tag %s status 5" % tag) in box.csv("XW")` | The test, first part: the process and the sampler ran, exactly one sampler ran before the stop, the exit status is 5, and the output file holds `-- killed` with the tag and the status 5. |
| 1168 | `          and box.none_alive() and "\n# end reason=" in box.file("watch-0.txt"), (up, alive_before, p.returncode, err))` | Second part: no dummy and no sampler is left, and the sampler file has its footer. So a stop ends the sampler together with the benchmark, and the sampler file is complete. |
| 1169 | `    p = box.start(["XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step again in a new case. |
| 1170 | `    up = box.wait_launch("watch-0.txt")` | Waits for the first dummy and its sampler. |
| 1171 | `    open(box.marker, "w").close()` | Creates the marker file of the case. |
| 1172 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script. |
| 1173 | `    check("XW, marker file during a process: status 3, '-- killed', one process started, benchmark and sampler gone",` | Starts a check: the marker file appears during a process. Expected: status 3, a line `-- killed`, one process started, and no benchmark and no sampler left. |
| 1174 | `          up and p.returncode == 3 and ("-- killed tag %s status 3" % tag) in box.csv("XW") and box.csv("XW").count("-- step ") == 1` | The test, first part: exit status 3, the line `-- killed` with the tag and the status 3, and exactly one header line in the output file. So no second process started. |
| 1175 | `          and box.none_alive(), (up, p.returncode, err))` | Second part: no process of the case is left. This is the main rule of the shared machine: our process must end when the marker file appears. |
| 1176 | `    p = box.start(["XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step again in a new case. |
| 1177 | `    up = box.wait_launch("watch-0.txt")` | Waits for the first dummy and its sampler. |
| 1178 | `    os.kill(p.pid, signal.SIGTERM)` | Sends the signal SIGTERM to the run script. |
| 1179 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script. |
| 1180 | `    csv = box.csv("XW")` | `csv`: the content of the output file. |
| 1181 | `    check("XW, interrupted during a process: status 130, '-- killed' marks the cut process, benchmark and sampler gone",` | Starts a check: a signal interrupts the script during a process. Expected: status 130, a line `-- killed` that marks the cut process, and no benchmark and no sampler left. |
| 1182 | `          up and p.returncode == 130 and box.none_alive()` | The test, first part: exit status 130, and no process of the case is left. |
| 1183 | `          and re.search(r"^-- killed tag %s status 130 utc \S+$" % re.escape(tag), csv, re.M) is not None` | Second part: the output file holds a line `-- killed tag`, the tag, `status 130 utc` and a time. `re.escape` makes the pattern take the tag as plain text. |
| 1184 | `          and csv.count("-- step ") == 1, (up, p.returncode, err, csv))` | Third part: exactly one header line. So the output file shows which process was cut, and a reader does not take its rows for a complete process. |
| 1185 | `    p = box.start(["XW"], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")` | Starts the step with a stop time 45 s from now and `RESERVE=0`. So `MARGIN` is 1 s, the first process may start, and the stop time comes while the dummy sleeps. |
| 1186 | `    up = box.wait_launch("watch-0.txt")` | Waits for the first dummy and its sampler. |
| 1187 | `    out, err = p.communicate(timeout=120)` | Waits for the end of the script, for at most 120 s. |
| 1188 | `    check("XW, STOP_AT reached during a process: status 4, '-- killed', benchmark and sampler gone",` | Starts a check: the time `STOP_AT` is reached during a process. Expected: status 4, a line `-- killed`, and no benchmark and no sampler left. |
| 1189 | `          up and p.returncode == 4 and ("-- killed tag %s status 4" % tag) in box.csv("XW") and box.none_alive(), (up, p.returncode, err))` | The test: exit status 4, the line `-- killed` with the tag and the status 4, and no process left. So the stop time ends a running process and is not only a rule for new launches. |
| 1190 | `    rc, out, err = box.run(["--from", "27", "XW"], SESSION="1", STOP_AT="none", DUMMY_EXIT="3", DUMMY_SLEEP="1")` | Runs the last process of `XW` with a dummy that sleeps 1 s and then ends with exit status 3. |
| 1191 | `    check("XW, failing binary: status 1, '-- failed', the sampler is gone and its file has the footer",` | Starts a check: a failing binary. Expected: status 1, a line `-- failed`, no sampler left, and a footer in the sampler file. |
| 1192 | `          rc == 1 and ("-- failed tag %s exit 3" % row[1]) in box.csv("XW") and box.none_alive()` | The test, first part: exit status 1, the line `-- failed` with the tag of the row and the exit status 3 of the dummy, and no process left. |
| 1193 | `          and "\n# end reason=" in box.file("watch-27.txt"), (rc, err))` | Second part: the sampler file has its footer. |
| 1194 | `    check("XW with the sampler: the start check of the sampler ran on the script before the first process and ended cleanly",` | Starts a check: the start check of the sampler ran before the first process and ended without an error. |
| 1195 | `          re.search(r"^# end reason=max_s samples=\d+ missed=\d+ max_sample_us=\d+ errors=0$", box.file("watch-selftest.txt"), re.M) is not None` | The test, first part: the file `watch-selftest.txt` of the last case holds a footer with `reason=max_s` and `errors=0`. |
| 1196 | `          and "max_s=0.3\n" in box.file("watch-selftest.txt") and "warning: the sampler file" not in err, box.file("watch-selftest.txt")[-200:])` | Second part: its first line records the time limit of 0.3 s, and the script printed no warning about a sampler file. So the sampler was shown to work on its CPU before the benchmark started. |
| 1197 | `    # Why: taskset can leave the CPUs 0-119 of the script, and the machine rule forbids CPUs 126 and 127.` | Comment: the reason for the next checks. `taskset` can place a program outside the CPUs 0 to 119 of the script, and the rule of the test machine forbids the CPUs 126 and 127. |
| 1198 | `    for value in ("120", "126", "127", "100000", "-1", "1,126", "100-127", "a[$(id)]", ""):` | Starts a loop over 9 values of `WATCH_CPU`. The first 8 must be refused: three CPUs above 119, a number that is too long, a negative number, a list, a range, and a text with a command substitution. The last value is the empty text. |
| 1199 | `        rc, out, err = box.run(["--from", "27", "XW"], SESSION="1", STOP_AT="none", WATCH_CPU=value)` | Runs the last process of `XW` with this value. |
| 1200 | `        if value == "":` | The case of the empty value. |
| 1201 | `            # An empty WATCH_CPU means the default 100: on a machine without CPU 100 the start check must stop the step.` | Comment: an empty `WATCH_CPU` means the default, CPU 100. On a machine without CPU 100 the start check of the sampler must stop the step. |
| 1202 | `            usable = 100 in os.sched_getaffinity(0)` | `usable`: true when this test may run on CPU 100. |
| 1203 | `            check("WATCH_CPU empty (default 100)%s" % (": runs" if usable else ", and this machine has no CPU 100: the start check stops "` | Starts a check whose name depends on `usable`. With CPU 100 the name says that the process runs. Without it the name says that the start check stops the step. |
| 1204 | `                                                         "the step with status 2 before the first process, watch-stderr.txt holds the message"),` | Ends the second name: status 2 before the first process, and `watch-stderr.txt` holds the message. |
| 1205 | `                  (rc == 0) if usable else (rc == 2 and "start check of the host sampler failed" in err and not box.launched()` | The test. With CPU 100: exit status 0. Without it: exit status 2, the message that the start check of the host sampler failed, and no launch. |
| 1206 | `                                            and box.file("watch-stderr.txt") != "" and box.csv("XW") == ""), (rc, err))` | Continues the second case: `watch-stderr.txt` is not empty, and the output file of the step is empty. So a CPU that cannot be used is found before any benchmark starts. The check also proves that an empty `WATCH_CPU` gets the default and is not refused. |
| 1207 | `        else:` | The 8 other values. |
| 1208 | `            check("WATCH_CPU='%s': status 2, nothing starts, no result folder" % value,` | Starts a check per value: status 2, nothing starts, and no result folder is made. |
| 1209 | `                  rc == 2 and "WATCH_CPU must be a CPU from 0 to 119" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the message `WATCH_CPU must be a CPU from 0 to 119`, no launch, and no results place. So the sampler can never be put on a CPU above 119, and a text with a command in it is refused before the shell uses it as a number. |
| 1210 | `    rc, out, err = box.run(["--from", "27", "XW"], SESSION="1", STOP_AT="none", WATCH_CPU=row[2])` | Runs the process with `WATCH_CPU` set to the CPU of the schedule row itself. |
| 1211 | `    check("WATCH_CPU equal to a CPU of the schedule: status 2, nothing starts",` | Starts a check: a `WATCH_CPU` that is a CPU of the schedule gives status 2, and nothing starts. |
| 1212 | `          rc == 2 and "is a CPU of the schedule" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the message `is a CPU of the schedule`, no launch and no results place. This matters for the measurement: a sampler on the CPU of the benchmark would take CPU time from the timed kernel. |
| 1213 | `    rc, out, err = box.run(["--from", "2", "XEV"], SESSION="1", STOP_AT="none", WATCH_CPU="126")` | Runs the last process of `XEV`, a step without a sampler, with `WATCH_CPU=126`. |
| 1214 | `    check("a step without sampler does not read WATCH_CPU: runs", rc == 0 and len(box.launched()) == 2, (rc, err))` | Check: exit status 0 and one launch. A step without a sampler does not test `WATCH_CPU`. |
| 1216 | `    nopy = os.path.join(box.dir, "nopy")` | `nopy`: the folder of the box with links to every needed program except `python3`. |
| 1217 | `    rc, out, err = box.run(["--from", "143", "XN"], pre=[os.path.join(nopy, "env")], SESSION="1", STOP_AT="none", PATH=nopy)` | Runs the last process of `XN`, a step without a sampler, with `nopy` as the whole search path. The script is started through the `env` of that folder. |
| 1218 | `    ok_without = rc == 0 and len(box.launched()) == 2` | `ok_without`: true when that run ended with status 0 and one launch. It is the control: the script works under this search path when no sampler is needed. |
| 1219 | `    rc, out, err = box.run(["XEV", "XW"], pre=[os.path.join(nopy, "env")], SESSION="1", STOP_AT="none", PATH=nopy)` | Runs the steps `XEV` and `XW` in one call under the same search path. `XW` needs the sampler, and `XEV` stands first. |
| 1220 | `    check("python3 missing: a step with the sampler stops with status 2 before the first process of the call "` | Starts a check: without `python3` a step with the sampler stops with status 2 before the first process of the call. |
| 1221 | `          "(a step without sampler runs under the same PATH)",` | Ends the name: a step without a sampler runs under the same search path. |
| 1222 | `          ok_without and rc == 2 and "python3 is missing" in err and not box.launched() and not os.path.exists(box.results), (ok_without, rc, err))` | The test: the control passed, the exit status is 2, the message says that `python3` is missing, nothing was launched and no results place exists. So `XEV`, which stands first and needs no sampler, did not start either. The call is refused as a whole before its first process. |
| 1223 | `    rc, out, err = box.run(["--dry-run", "XW"], pre=[os.path.join(nopy, "env")], SESSION="1", PATH=nopy)` | Runs a dry run of `XW` under the same search path. |
| 1224 | `    check("python3 missing: the dry run still prints the step", rc == 0 and out.count("\nbwx8 --trial ") == 28, (rc, err))` | Check: exit status 0 and 28 command lines. A dry run does not need `python3`. |
| 1225 | `    os.rename(os.path.join(box.dir, "hostwatch.py"), os.path.join(box.dir, "hostwatch.moved"))` | Renames `hostwatch.py` in the box. So the run script does not find the sampler. |
| 1226 | `    rc, out, err = box.run(["XW"], SESSION="1", STOP_AT="none")` | Runs the step `XW`. |
| 1227 | `    check("hostwatch.py missing: a step with the sampler stops with status 2, nothing starts",` | Starts a check: without `hostwatch.py` a step with the sampler stops with status 2, and nothing starts. |
| 1228 | `          rc == 2 and "hostwatch.py" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, an error text that names `hostwatch.py`, no launch and no results place. |
| 1229 | `    rc, out, err = box.run(["--from", "2", "XEV"], SESSION="1", STOP_AT="none")` | Runs the last process of `XEV` while `hostwatch.py` is still missing. |
| 1230 | `    check("hostwatch.py missing: a step without sampler runs", rc == 0 and len(box.launched()) == 2, (rc, err))` | Check: exit status 0 and one launch. A step without a sampler does not need `hostwatch.py`. |
| 1231 | `    os.rename(os.path.join(box.dir, "hostwatch.moved"), os.path.join(box.dir, "hostwatch.py"))` | Gives `hostwatch.py` its name back. |

### `run_checks`: the stop controls without a sampler, and `MARGIN` with the real schedules (lines 1233 to 1313)

| Line | Source | Explanation |
|---:|---|---|
| 1233 | `    # ---- stop controls without sampler (as test_schedule8.py tests run_bwx8.sh) ----` | Comment: the checks of the stop controls without a sampler start here. By the comment they are the checks that `test_schedule8.py` makes for `run_bwx8.sh`. |
| 1234 | `    tag = rows[0][1]` | `tag`: the tag of the first process of `XEV`. |
| 1235 | `    p = box.start(["XEV"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step `XEV` in the background. The dummy sleeps 300 s, so the first process still runs when the test acts. |
| 1236 | `    up = box.wait_launch()` | `up`: true when the first dummy and its sleep run. |
| 1237 | `    open(box.marker, "w").close()` | Creates the marker file of the case. |
| 1238 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script, for at most 60 s. |
| 1239 | `    csv = box.csv("XEV")` | `csv`: the content of the output file. |
| 1240 | `    check("marker file appears during a process: status 3, '-- killed', no process left",` | Starts a check: the marker file appears during a process. Expected: status 3, a line `-- killed`, and no process left. |
| 1241 | `          up and p.returncode == 3 and ("-- killed tag %s status 3" % tag) in csv` | The test, first part: the process ran, the exit status is 3, and the output file holds `-- killed` with the tag and the status 3. |
| 1242 | `          and csv.count("-- step ") == 1 and box.none_alive(), (up, p.returncode, err, csv))` | Second part: exactly one header line, so no second process started, and no dummy and no sleep is left. This proves the rule of the shared machine: when the marker file appears, the script ends its process and starts no other. |
| 1243 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX8_MARKER=box.marker)` | Runs the step again with the marker path of the case before, where the file still exists. |
| 1244 | `    check("marker file present at the start: status 3, nothing starts, no result folder",` | Starts a check: the marker file exists at the start. Expected: status 3, nothing starts, and no result folder. |
| 1245 | `          rc == 3 and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 3, no launch, and no results place. So with the marker file present the script writes nothing and starts nothing. |
| 1246 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="0.3", DUMMY_TOUCH="1")` | Runs the step with a dummy that sleeps 0.3 s and creates the marker file when it ends. |
| 1247 | `    csv = box.csv("XEV")` | `csv`: the content of the output file. |
| 1248 | `    check("marker file appears between two processes: status 3, the first process ended, the second does not start",` | Starts a check: the marker file appears between two processes. Expected: status 3, the first process ended, and the second does not start. |
| 1249 | `          rc == 3 and csv.count("-- step ") == 1 and csv.count("M,dummy,1\n") == 1 and "-- killed" not in csv` | The test, first part: exit status 3, one header line, one output line of the dummy, and no line `-- killed`. So the first process was not cut. |
| 1250 | `          and len(box.launched()) == 2, (rc, err, csv))` | Ends the test: the dummy log has two lines, which is one launch. This proves the check before a launch: a process that has ended is kept as complete, and no new process starts while the marker file exists. |
| 1251 | `    late = os.path.join(box.dir, "case%d" % (box.n + 1), "RUNNING")       # the marker path of the next case` | `late`: the marker path that the next case will have. The case number is known before the case starts. |
| 1252 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", PS_TOUCH=late,` | Runs the step with `PS_TOUCH` set to that path. The stand-in for `ps` then creates the marker file at its second call. |
| 1253 | `                           PATH=os.path.join(box.dir, "bin") + os.pathsep + os.environ["PATH"])` | Continues the call: the folder `bin` of the box stands first in the search path. So the script calls the stand-in for `ps`, and the second call of it creates the marker file. |
| 1254 | `    check("marker file appears after the wait, directly before the launch: status 3, nothing starts",` | Starts a check: the marker file appears after the wait, directly before the launch. Expected: status 3, and nothing starts. |
| 1255 | `          late == box.marker and os.path.exists(late) and rc == 3 and not box.launched() and "-- step" not in box.csv("XEV")` | The test, first part: the path was the marker path of the case, the file exists, the exit status is 3, nothing was launched, and the output file holds no header line. |
| 1256 | `          and box.file("launches.txt").count("== XEV.csv idx ") == 1, (rc, err))` | Second part: `launches.txt` holds one load record. So the script had passed the wait and had written the load record of the first launch. The last check before the launch then found the marker file. This proves that the script tests the marker file again directly before each launch. |
| 1257 | `    p = box.start(["XEV"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step in the background, with a dummy that sleeps 300 s. |
| 1258 | `    up = box.wait_launch()` | Waits until the first dummy and its sleep run. |
| 1259 | `    open(box.stopfile, "w").close()` | Creates the stop file of the case. |
| 1260 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script, for at most 60 s. |
| 1261 | `    check("stop file appears during a process: status 5, '-- killed', no process left",` | Starts a check: the stop file appears during a process. Expected: status 5, a line `-- killed`, and no process left. |
| 1262 | `          up and p.returncode == 5 and ("-- killed tag %s status 5" % tag) in box.csv("XEV") and box.none_alive(),` | The test: the process ran, the exit status is 5, the output file holds `-- killed` with the tag and the status 5, and no process is left. So a run can be stopped from another login with one file. |
| 1263 | `          (up, p.returncode, err))` | The detail for a failure: the launch flag, the exit status and the error output. |
| 1264 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX8_STOPFILE=box.stopfile)` | Runs the step again with the stop file path of the case before, where the file still exists. |
| 1265 | `    check("stop file present at the start: status 5, nothing starts", rc == 5 and not box.launched(), (rc, err))` | Check: exit status 5 and no launch. A stop file that was not removed keeps every new run from starting. |
| 1266 | `    p = box.start(["XEV"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step in the background again. |
| 1267 | `    up = box.wait_launch()` | Waits until the first dummy and its sleep run. |
| 1268 | `    os.kill(p.pid, signal.SIGTERM)` | Sends the signal SIGTERM to the run script. |
| 1269 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script, for at most 60 s. |
| 1270 | `    csv = box.csv("XEV")` | `csv`: the content of the output file. |
| 1271 | `    check("interrupted during a process: status 130, '-- killed' marks the cut process, no process left",` | Starts a check: a signal interrupts the script during a process. Expected: status 130, a line `-- killed` that marks the cut process, and no process left. |
| 1272 | `          up and p.returncode == 130 and box.none_alive()` | The test, first part: the process ran, the exit status is 130, and no process is left. |
| 1273 | `          and re.search(r"^-- killed tag %s status 130 utc \S+$" % re.escape(tag), csv, re.M) is not None` | Second part: the output file holds a line `-- killed tag`, the tag, `status 130 utc` and a time. |
| 1274 | `          and csv.count("-- step ") == 1, (up, p.returncode, err, csv))` | Third part: exactly one header line. So an interrupted run leaves no benchmark behind, and its output file marks the process that was cut. |
| 1275 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT=utc(30))` | Runs the step with a stop time 30 s from now and the default `RESERVE` of 90 s. |
| 1276 | `    check("STOP_AT nearer than MARGIN: status 4, nothing starts",` | Starts a check: a stop time that is nearer than `MARGIN` gives status 4, and nothing starts. |
| 1277 | `          rc == 4 and not box.launched() and "less than 91 s away" in err, (rc, err))` | The test: exit status 4, no launch, and the message `less than 91 s away`. 91 s is the `MARGIN` of the step: 1 s for its longest process, rounded up, plus the 90 s of `RESERVE`. So no process starts that could still run at the stop time. |
| 1278 | `    # MARGIN is the longest process of the step, rounded up to whole seconds, plus RESERVE. With the` | Comment: `MARGIN` is the longest process of the step, rounded up to whole seconds, plus `RESERVE`. The sentence about the test divisor ends in the next line. |
| 1279 | `    # test divisor 100 the longest XEV process is 0.009 s (1 s); with divisor 1 the longest XW process is 33 s.` | Continues the comment: with the test divisor 100 the longest process of `XEV` has 0.009 s, which rounds up to 1 s. With the divisor 1 the longest process of `XW` has 33 s. |
| 1280 | `    real = os.path.join(box.dir, "sched9-real")` | `real`: a path in the box. No later line uses it. |
| 1281 | `    os.rename(os.path.join(box.dir, "sched9"), os.path.join(box.dir, "sched9-test"))` | Renames the schedule folder of the box to `sched9-test`. A later line gives it its name back. |
| 1282 | `    shutil.copytree(os.path.join(X, "sched9"), os.path.join(box.dir, "sched9"))` | Copies the saved folder `sched9`, which lies beside this file, into the box. It holds the real schedules, made with the divisor 1. When that folder is missing, this call raises an error, and the test ends here without its summary. |
| 1283 | `    rc, out, err = box.run(["XW"], SESSION="1", STOP_AT=utc(100))` | Runs the step `XW` of the real schedules with a stop time 100 s from now. |
| 1284 | `    check("MARGIN follows the longest process of the step: the real XW schedule refuses at 123 s, not at 91 s",` | Starts a check: `MARGIN` follows the longest process of the step. The real schedule of `XW` refuses a launch at 123 s, not at 91 s. |
| 1285 | `          rc == 4 and not box.launched() and "less than 123 s away" in err and "longest process 33 s, MARGIN 123 s" in out,` | The test: exit status 4, no launch, the message `less than 123 s away`, and the summary text `longest process 33 s, MARGIN 123 s`. The stop time is 100 s away, which a margin of 91 s would allow. So the script computes `MARGIN` from the schedule of the step: 33 s plus the 90 s of `RESERVE`. |
| 1286 | `          (rc, err, out))` | The detail for a failure: the exit status, the error output and the output. |
| 1287 | `    rc, out, err = box.run(["--dry-run", "XEV", "XW", "XCA", "XCB", "XCC", "XN", "XF"], SESSION="1")` | Runs a dry run of all 7 steps of the real schedules for session 1. |
| 1288 | `    check("--dry-run of the real schedules, session 1: 319 processes and the nominal work of the task (864, 396 x 3, 2.7, 1382.4, 864 s)",` | Starts a check: the dry run of the real schedules for session 1 gives 319 processes and the nominal work of the task. |
| 1289 | `          rc == 0 and out.count("\nbwx8 --trial ") == 319` | The test, first part: exit status 0 and 319 command lines. |
| 1290 | `          and all(s in out for s in ("step XW session 1: 28 processes, nominal kernel work 864.000 s",` | Second part: the output holds each of 7 summary texts. This line: 28 processes and 864.000 s for `XW`. |
| 1291 | `                                     "step XCA session 1: 18 processes, nominal kernel work 396.000 s",` | 18 processes and 396.000 s for `XCA`. |
| 1292 | `                                     "step XCB session 1: 18 processes, nominal kernel work 396.000 s",` | 18 processes and 396.000 s for `XCB`. |
| 1293 | `                                     "step XCC session 1: 18 processes, nominal kernel work 396.000 s",` | 18 processes and 396.000 s for `XCC`. |
| 1294 | `                                     "step XEV session 1: 3 processes, nominal kernel work 2.700 s",` | 3 processes and 2.700 s for `XEV`. |
| 1295 | `                                     "step XN session 1: 144 processes, nominal kernel work 1382.400 s",` | 144 processes and 1382.400 s for `XN`. |
| 1296 | `                                     "step XF session 1: 90 processes, nominal kernel work 864.000 s")), (rc, err, out[:300]))` | 90 processes and 864.000 s for `XF`. So the run script adds up the saved schedules to the same values as the table of the task in this file. |
| 1297 | `    rc, out, err = box.run(["--dry-run", "XW", "XCA", "XCB", "XCC", "XN", "XF"], SESSION="2")` | Runs a dry run of the 6 steps of session 2 of the real schedules. |
| 1298 | `    check("--dry-run of the real schedules, session 2: 316 processes", rc == 0 and out.count("\nbwx8 --trial ") == 316, (rc, err))` | Check: exit status 0 and 316 command lines. That is the 319 of session 1 without the 3 processes of `XEV`. |
| 1299 | `    shutil.rmtree(os.path.join(box.dir, "sched9"))` | Removes the copy of the real schedules from the box. |
| 1300 | `    os.rename(os.path.join(box.dir, "sched9-test"), os.path.join(box.dir, "sched9"))` | Gives the test schedules their name `sched9` back. |
| 1301 | `    p = box.start(["XEV"], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")` | Starts the step `XEV` with a stop time 45 s from now and `RESERVE=0`. So `MARGIN` is 1 s, the first process may start, and the stop time comes while the dummy sleeps. |
| 1302 | `    up = box.wait_launch()` | Waits until the first dummy and its sleep run. |
| 1303 | `    out, err = p.communicate(timeout=120)` | Waits for the end of the script, for at most 120 s. |
| 1304 | `    check("STOP_AT reached during a process: status 4, '-- killed', no process left",` | Starts a check: the time `STOP_AT` is reached during a process. Expected: status 4, a line `-- killed`, and no process left. |
| 1305 | `          up and p.returncode == 4 and ("-- killed tag %s status 4" % tag) in box.csv("XEV") and box.none_alive(),` | The test: the process ran, the exit status is 4, the output file holds `-- killed` with the tag and the status 4, and no process is left. So no process of ours runs past the stop time. |
| 1306 | `          (up, p.returncode, err))` | The detail for a failure: the launch flag, the exit status and the error output. |
| 1307 | `    rc, out, err = box.run(["XEV"], SESSION="1")` | Runs the step without `STOP_AT`. |
| 1308 | `    check("STOP_AT not set: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. A real run needs a decision about the stop time. |
| 1309 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", DUMMY_EXIT="3")` | Runs the step with a dummy that ends with exit status 3. |
| 1310 | `    csv = box.csv("XEV")` | `csv`: the content of the output file. |
| 1311 | `    check("failing binary: status 1, '-- failed', the next process does not start",` | Starts a check: a failing binary gives status 1 and a line `-- failed`, and the next process does not start. |
| 1312 | `          rc == 1 and ("-- failed tag %s exit 3" % tag) in csv and csv.count("-- step ") == 1, (rc, err, csv))` | The test: exit status 1, the line `-- failed` with the tag and the exit status 3 of the dummy, and exactly one header line. So a failed process stops the step, and the output file marks it. |

### `run_checks`: session 2 and other refusals (lines 1314 to 1374)

| Line | Source | Explanation |
|---:|---|---|
| 1314 | `    # ---- session 2 ----` | Comment: the checks of session 2 start here. |
| 1315 | `    rc, out, err = box.run(["XN"], SESSION="2", STOP_AT="none")` | Runs step `XN` for session 2 without `SESSION1_END`. |
| 1316 | `    check("session 2 without SESSION1_END: status 2, nothing starts",` | Starts a check: session 2 without `SESSION1_END` ends with status 2, and nothing starts. |
| 1317 | `          rc == 2 and "SESSION1_END" in err and not box.launched(), (rc, err))` | The test: exit status 2, the error output names `SESSION1_END`, and no launch. |
| 1318 | `    rc, out, err = box.run(["XN"], SESSION="2", STOP_AT="none", SESSION1_END=utc(-3 * 3600 + 120))` | Runs it with an end of session 1 that lies 2 hours and 58 minutes in the past. |
| 1319 | `    check("session 2 earlier than 3 h after SESSION1_END: refused with status 2, nothing starts",` | Starts a check: a session 2 that would start earlier than 3 hours after `SESSION1_END` is refused with status 2, and nothing starts. |
| 1320 | `          rc == 2 and "3 hours" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the words `3 hours` in the error output, no launch and no results place. So the script itself enforces the gap of 3 hours between the two sessions. |
| 1321 | `    for value in ("garbage", time.strftime("%Y-%m-%d", time.gmtime()), "yesterday", "@0", "-4 hours",` | Starts a loop over values of `SESSION1_END` that must be refused: a word without meaning, a date without a time, the word `yesterday`, the form `@0`, and a relative time. |
| 1322 | `                  time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - 4 * 3600)), "2026-02-30T00:00Z"):` | Continues the list: a date and a time of 4 hours ago with a blank between them and without `Z`, and the 30th of February in the right form. |
| 1323 | `        rc, out, err = box.run(["--from", "143", "XN"], SESSION="2", STOP_AT="none", SESSION1_END=value)` | Runs the last process of `XN` for session 2 with this value of `SESSION1_END`. |
| 1324 | `        check("session 2 with SESSION1_END='%s': status 2, nothing starts" % value,` | Starts a check per value: status 2, and nothing starts. |
| 1325 | `              rc == 2 and "bad SESSION1_END" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the message `bad SESSION1_END`, no launch and no result folder. Several of these values are accepted by `date -d`. Without the strict form a wrong text could let session 2 start too early. |
| 1326 | `    s1end = utc(-3 * 3600 - 60)` | `s1end`: a valid end of session 1 that lies 3 hours and 1 minute in the past. |
| 1327 | `    row2 = box.rows("XN", 2)[143]` | `row2`: the last row of the schedule of `XN` in session 2. |
| 1328 | `    rc, out, err = box.run(["--from", "143", "XN"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)` | Runs that process with the valid end of session 1. |
| 1329 | `    env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1330 | `    check("session 2 later than 3 h after SESSION1_END: runs the session 2 schedule, folder bwx9-XN-s2-, SESSION1_END in env.txt",` | Starts a check: later than 3 hours after `SESSION1_END` the script runs the schedule of session 2. The name of the result folder starts with `bwx9-XN-s2-`, and `env.txt` records `SESSION1_END`. |
| 1331 | `          rc == 0 and "bwx9-XN-s2-" in (box.folder() or "") and ("SESSION1_END=" + s1end) in env` | The test, first part: exit status 0, the folder name holds `bwx9-XN-s2-`, and `env.txt` holds the given end time. |
| 1332 | `          and ("-- step XN session 2 idx 143 tag %s " % row2[1]) in box.csv("XN")` | Second part: the header line of the process names session 2, the `idx` 143 and the tag of the session 2 row. |
| 1333 | `          and "--plan sched9/s2/XN/0143.plan" in box.launched()[0], (rc, err))` | Third part: the dummy got the plan path of session 2. So session 2 runs its own schedule with its own order, not the one of session 1. |
| 1334 | `    row2 = box.rows("XW", 2)[27]` | `row2`: now the last row of the schedule of `XW` in session 2. |
| 1335 | `    rc, out, err = box.run(["--from", "27", "XW"], SESSION="2", STOP_AT="none", SESSION1_END=s1end, DUMMY_SLEEP="1")` | Runs that process for session 2, with a sleep of 1 s. |
| 1336 | `    check("session 2 with the sampler: the sampler watches the CPU of the session 2 row",` | Starts a check: in session 2 the sampler watches the CPU of the session 2 row. |
| 1337 | `          rc == 0 and ("cpu=%s hz=20" % row2[2]) in box.file("watch-27.txt").split("\n")[0] and box.none_alive(), (rc, err))` | The test: exit status 0, the first line of the sampler file names the CPU of that row, and no process is left. The CPU order is reversed in session 2. So the watched CPU must come from the row of the process and not from a fixed value. |
| 1339 | `    # ---- other refusals ----` | Comment: the checks of other refusals start here. |
| 1340 | `    rc, out, err = box.run(["XEV"], STOP_AT="none")` | Runs the step without `SESSION`. |
| 1341 | `    check("SESSION not set: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. The script does not guess the session. |
| 1342 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX8_SHA256="0" * 64)` | Runs the step with a digest of 64 zeros, which the dummy does not have. |
| 1343 | `    check("bwx8 differs from BWX8_SHA256: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. So a binary that is not the expected one cannot run when the digest is given. |
| 1344 | `    digest = subprocess.run(["sha256sum", box.bin], capture_output=True, text=True).stdout.split()[0]` | `digest`: the sha256 of the dummy binary, computed with `sha256sum`. |
| 1345 | `    rc, out, err = box.run(["--from", "2", "XEV"], SESSION="1", STOP_AT="none", BWX8_SHA256=digest)` | Runs the last process of `XEV` with that digest. |
| 1346 | `    check("bwx8 equals BWX8_SHA256: runs", rc == 0 and len(box.launched()) == 2, (rc, err))` | Check: exit status 0 and one launch. With the right digest the script runs. So the refusal of line 1343 came from the digest and from nothing else. |
| 1347 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX8_BIN=os.path.join(box.dir, "absent"))` | Runs the step with a binary path that does not exist. |
| 1348 | `    check("missing binary: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. So a missing binary is reported, and nothing starts. |
| 1349 | `    rc, out, err = box.run(["--from", "3", "XEV"], SESSION="1", STOP_AT="none")` | Runs `XEV` from the `idx` 3. The step has the processes 0, 1 and 2 only. |
| 1350 | `    check("--from past the last idx: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. A `--from` value past the last `idx` runs nothing and is reported. |
| 1351 | `    rc, out, err = box.run(["--from", "1", "XEV", "XN"], SESSION="1", STOP_AT="none")` | Runs two steps with `--from 1`. |
| 1352 | `    check("--from with two steps: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. `--from` is allowed with one step only. |
| 1353 | `    allowed = sorted(os.sched_getaffinity(0))` | `allowed`: the CPUs on which this test may run, in sorted order. |
| 1354 | `    rc, out, err = box.run(["--from", "2", "XEV"], pre=["taskset", "-c", str(allowed[0])], SESSION="1", STOP_AT="none")` | Runs the last process of `XEV` with `taskset -c` before the script. So the script itself starts on one CPU only, the lowest allowed one. |
| 1355 | `    seen = open(box.log + ".cpus").read() if os.path.exists(box.log + ".cpus") else ""` | `seen`: the CPU list that the dummy recorded, or an empty text. |
| 1356 | `    check("the benchmark is confined to CPUs 0-119, whatever CPU the script was started on",` | Starts a check: the benchmark is limited to the CPUs 0 to 119, on whatever CPU the script was started. |
| 1357 | `          rc == 0 and len(allowed) > 1 and seen.count("\n") == 1 and cpu_list(seen) == {c for c in allowed if c < 120},` | The test: exit status 0, the test may use more than one CPU, the dummy recorded one line, and its CPU list is the set of the allowed CPUs below 120. |
| 1358 | `          (rc, err, seen))` | The detail for a failure. The check proves that the script sets the CPU list itself and does not keep the narrow list of its caller. The runner then finds its worker CPU in the list. |
| 1359 | `    tsv = os.path.join(box.dir, "sched9", "s1", "XEV.tsv")` | `tsv`: the path of the schedule file of `XEV` in the box. |
| 1360 | `    saved = open(tsv).read()` | `saved`: its content, kept to restore it later. |
| 1361 | `    made = os.path.join(box.dir, "made-by-schedule")` | `made`: the path of a file that must never appear. |
| 1362 | `    for what, old_, new_ in (("idx", "\n0\t", "\na[$(touch${IFS}%s)]\t"), ("cpu", "\t2\t", "\ta[$(touch${IFS}%s)]\t")):` | Starts a loop over two damaged schedules. In the first the `idx` of the first row is a text with a command substitution that would create the file `made`. In the second the `cpu` column holds such a text. `${IFS}` takes the place of the blank inside the command, so the column itself holds no blank. |
| 1363 | `        with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1364 | `            fh.write(saved.replace(old_, new_ % made, 1))` | Writes the schedule with the first match of the old text replaced by the damaged text, which names the path `made`. |
| 1365 | `        rc, out, err = box.run(["--dry-run", "XEV"], SESSION="1")` | Runs a dry run of `XEV` with the damaged schedule. |
| 1366 | `        check("schedule with a command in %s: status 2, the command does not run" % what,` | Starts a check per case: a schedule with a command in that column gives status 2, and the command does not run. |
| 1367 | `              rc == 2 and not os.path.exists(made) and open(tsv).read() != saved, (rc, err))` | The test: exit status 2, the file `made` does not exist, and the schedule file really differs from the saved one. This matters: the script uses the `idx` in shell arithmetic, which would run a command that is written inside the value. The `cpu` value goes to the host sampler as an option. The check proves that the script tests the form of both values before it uses them. |
| 1368 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1369 | `        fh.write(saved)` | Writes the saved content back. |
| 1370 | `    os.rename(os.path.join(box.dir, "sched9", "s1", "XEV", "0001.plan"), os.path.join(box.dir, "moved.plan"))` | Moves the plan file of process 1 of `XEV` out of the schedule folder. |
| 1371 | `    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none")` | Runs the step `XEV` with that plan file missing. |
| 1372 | `    check("missing plan file: status 2 before the first launch", rc == 2 and "missing plan file" in err and not box.launched(), (rc, err))` | Check: exit status 2, the message `missing plan file`, and no launch. So a missing plan stops the step before its first process, and not in the middle of the step. |

### `main`: the order of the groups of checks, and the summary (lines 1375 to 1401)

| Line | Source | Explanation |
|---:|---|---|
| 1375 | `def main():` | Starts the function `main`. |
| 1376 | `    with open("/proc/loadavg") as f:` | Opens the file `/proc/loadavg`. |
| 1377 | `        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))` | Prints the load averages of the last 1, 5 and 15 minutes and the number of CPUs on which the test may run. The load matters: the run script waits for a quiet system before each launch, so the test takes longer on a loaded machine. |
| 1378 | `    tmp = tempfile.mkdtemp(prefix="test_schedule9.")` | `tmp`: a new temporary folder whose name starts with `test_schedule9.`. Every file of the test goes into it. |
| 1379 | `    try:` | Starts the block that is followed by the cleanup. |
| 1380 | `        sched = schedule_checks(tmp)` | Runs the checks of the generator. `sched` gets the folder that was generated with the test divisor 100. |
| 1381 | `        if "--no-bwx8" in sys.argv[1:]:` | When the option `--no-bwx8` was given. |
| 1382 | `            print("SKIP  the run of every plan through the local stand-in bwx8 (--no-bwx8)")` | Prints a line that starts with `SKIP` and names the part that is left out. It is not counted as a check. |
| 1383 | `        else:` | If not. |
| 1384 | `            bwx8_checks(tmp, sched)` | Runs the checks with the stand-in `bwx8`. |
| 1385 | `        hostwatch_checks(tmp)` | Runs the checks of the host sampler. No option leaves them out. |
| 1386 | `        visit_checks(tmp)` | Runs the checks of the visit script. |
| 1387 | `        if "--no-run" in sys.argv[1:]:` | When the option `--no-run` was given. |
| 1388 | `            print("SKIP  the checks of run_bwx9.sh with a dummy bwx8 (--no-run)")` | Prints a `SKIP` line for the checks of the run script. |
| 1389 | `        else:` | If not. |
| 1390 | `            run_checks(tmp, sched)` | Runs the checks of the run script. |
| 1391 | `    finally:` | The cleanup. It runs in every case, also after an error. |
| 1392 | `        shutil.rmtree(tmp, ignore_errors=True)` | Removes the temporary folder with everything in it. |
| 1393 | `    with open("/proc/loadavg") as f:` | Opens the file `/proc/loadavg` again. |
| 1394 | `        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))` | Prints the load averages at the end. |
| 1395 | `    print("# checks: %d, passed: %d, failed: %d%s" % (COUNT[0], COUNT[0] - len(FAILS), len(FAILS),` | Prints the summary line: the number of checks, of passed checks and of failed checks. |
| 1396 | `                                                      "".join("\n#   " + n for n in FAILS)))` | The last value of the summary: the name of each failed check, on a line of its own. |
| 1397 | `    sys.exit(1 if FAILS else 0)` | Ends the program with exit status 1 when a check failed, and with 0 if not. A part that did not run does not change the status. |
| 1400 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 1401 | `    main()` | Runs `main`. |
