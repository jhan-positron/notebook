# `test_schedule11.py` explained, line by line

- Source file: `bwx11-2026-11-15/test_schedule11.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1566 lines, 96931 bytes).
- sha256 of the source when this page was built: `43018912681c49c1af198ffa429f1737726247f183110a4b5f92c44c4fba0714`.

## Short version: purpose

`test_schedule11.py` checks the three scripts of round 4 without CRB: the generator `schedule11.py`, the run script `run_bwx11.sh` and the visit script `visit11.sh`. It tests the generated schedules against rules that are written a second time in this file, it puts every plan through a runner that is built on the local machine, and it runs the run script with dummy binaries through its stop cases. The validator and the rule functions of the steps are also applied to inputs that must not pass, to show that they can fail.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 4**: the fourth set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Z`.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation into the buffer size of 8 MiB.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Process**: one start of a benchmark binary.
- **Check**: one call of the function `check`. It prints `PASS` or `FAIL` and one sentence that says what was tested.
- **Generator**: the program `schedule11.py`. It writes the schedules and the plan files of round 4.
- **Run script**: the script `run_bwx11.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Visit script**: the script `visit11.sh`. It makes one login to CRB and starts the run script there.
- **Step**: one batch of processes of a round, for example `ZD`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Prefix, target, window**: the target is the kernel that a trial measures. A window is one timed period of it. The prefix is a phase before the target that prepares the core.
- **`S2` form**: a process of 4 equal trials, each with a prefix of 1200 ms of the target kernel and 4 target windows of 300 ms. Step `S2` of round 1 had this form first.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Cell**: one combination of the factors of a step, for example one kernel with one evict condition.
- **Replicate set, block**: a replicate set is one run of every cell of a step for one size and CPU. A block is the group of processes of one replicate on one CPU in the steps `ZC` and `ZM`.
- **Williams square**: a set of n orders of n items in which every item stands once at every position, and every ordered pair of different items stands once as direct neighbours.
- **Test divisor**: a number by which the generator divides every duration, for local tests only. The test uses 100.
- **Evict step, `E0`, `E512`**: with the option `--evict-mb 512` the runner `bwx11` writes another buffer of 512 MiB twice before the first trial. `E512` is the condition with that option, and `E0` the condition without it.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters for each window.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
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

1. The values that the task expects are written as fixed values: the counts, the nominal work, the kernels, the sizes and the events of each step (lines 46 to 68).
2. The helper `check` prints one line per check and collects the failures (lines 84 to 90).
3. The validator of the plan format and the reader of a generated folder (lines 93 to 176, lines 180 to 222).
4. The rules of the steps, one function per step (lines 263 to 422).
5. Group 1, `schedule_checks`: run the generator. Test the format of every file, the counts and the printed report, the header pairs, the CPU order, the rules of each step with damaged variants, the `.bin` files, the effect of the seed, the saved folder and the test divisor (lines 425 to 722).
6. Group 2, `bwx10_checks`: a locally built `bwx10` refuses the options and the plans that are new in round 4 (lines 796 to 821).
7. Group 3, `bwx11_checks`: a locally built `bwx11` accepts all 870 plans, refuses damaged plans, and runs the 10 real plans of one block of `ZM` (lines 824 to 893).
8. Group 4, `visit_checks`: the visit script with a stand-in for `ssh`: the remote command, bad settings, and the comparison with `visit10.sh` (lines 1073 to 1127).
9. Group 5, `run_checks`: the run script with dummy binaries: syntax, comparison with the older run scripts, step names and the dry run, a normal run, the binary of a step, the digests, the counter settings, the host sampler, the stop controls, `MARGIN`, session 2 and other refusals (lines 1141 to 1537).
10. `main` runs the groups in this order, removes the temporary folder and prints the summary (lines 1540 to 1562).

## Behavior a reader must know

- The test contacts no other machine. The visit script runs with a stand-in for `ssh` and a search path that holds no real `ssh` (line 1090). The run script runs as a copy in a temporary folder, with test paths for the marker file, the stop file, the binaries and the results (lines 1022 to 1023).
- The test starts local programs: the generator, `gcc`, the stand-in runners (4 at a time, and once 10 at a time for 30 s), the copy of the run script, the dummies and the host sampler.
- The exit status is 0 only when every check passed (line 1562). A part that did not run prints a `SKIP` line and does not change the status. The last line of the output gives the number of such parts.
- Four options leave out parts: `--no-run`, `--no-bwx10`, `--no-bwx11` and `--no-long`. The part with the stand-in `bwx11` is also left out when `bwx11.c` is missing or cannot be built (lines 827 to 836).
- The expected values are written a second time in this file (lines 48 to 65). So a change in the generator alone makes a check fail.
- The validator, the rule for the CPU order and the rule functions of the steps are tested twice: once on the real output, and once on an input that must not pass. Not every rule inside a rule function has such a second test.
- The check that starts at line 708 is named for every duration divided by 100. The test compares the nominal work per step and session and the window counts, not each duration.
- The checks of the run script take minutes on a loaded machine. Before each launch the script waits up to 20 s until at most 2 tasks are runnable.
- The check of the saved folder compares every file of `sched11/` beside this file with the output of the generator (lines 695 to 696). It fails when that folder holds the files of step `ZS`, which `schedule_zs.py` adds.
- The check of a wrong `.bin` content tests "nothing starts" with the log of the dry run only (lines 1283 to 1287). For the real run it tests the exit status and the message.
- The stand-in runs need CPU 0, CPU 2 and one more CPU below 120 on the local machine (line 781). CPU 41 is replaced by a local CPU in a copy of the schedule (lines 741 to 744).
- The test reads files of the folders of rounds 1 to 3, which must lie beside the folder of round 4 (lines 34 to 35).
- The test writes into a temporary folder only and removes it at the end (line 1543, line 1557).

## Source and explanation, line by line

- Text shown: the file `bwx11-2026-11-15/test_schedule11.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1566 lines, 96931 bytes, sha256 `43018912681c49c1af198ffa429f1737726247f183110a4b5f92c44c4fba0714`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 96. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Description text and imports (lines 1 to 31)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_schedule11.py - checks of schedule11.py, run_bwx11.sh and visit11.sh (round 4).` | Starts the description text of the file. First line: the name and the purpose. The file holds the checks of the generator `schedule11.py`, of the run script `run_bwx11.sh` and of the visit script `visit11.sh`. These are the three scripts of round 4. |
| 4 | `Usage: test_schedule11.py [--no-run] [--no-bwx10] [--no-long] [--no-bwx11]` | Text of the description: the usage. Each of the four options leaves out one group of checks. |
| 5 | `Prints one line per check. Exit status 0 only if every check passed.` | Text of the description: the program prints one line per check. Its exit status is 0 only when every check passed. |
| 6 | `--no-run leaves out the checks that start run_bwx11.sh with dummy binaries (they take minutes` | Text of the description: `--no-run` leaves out the checks that start `run_bwx11.sh` with dummy binaries. A dummy binary is a small script that stands in for a runner. |
| 7 | `on a loaded machine, because the script waits up to 20 s for a quiet system before a launch).` | Continues the text: those checks take minutes on a loaded machine. The reason: the run script waits up to 20 s for a quiet system before each launch. |
| 8 | `--no-bwx10 leaves out the build of the local stand-in bwx10 (from folder Y of round 3) and the checks that` | Text of the description: `--no-bwx10` leaves out the build of a local stand-in of the runner `bwx10` from the folder `Y` of round 3. A stand-in is a build on the machine of the developer. Its kernels are plain C loops, and its rates mean nothing. |
| 9 | `this older binary refuses the args and the plans of round 4.` | Continues the text: the option also leaves out the checks that this older runner refuses the options and the plans of round 4. |
| 10 | `--no-bwx11 leaves out the run of every plan of ZA, ZD, ZC, ZN and ZM through a local stand-in bwx11. These` | Text of the description: `--no-bwx11` leaves out the run of every plan of the steps `ZA`, `ZD`, `ZC`, `ZN` and `ZM` through a local stand-in of `bwx11`. |
| 11 | `checks also print SKIP when bwx11.c is not beside this file or does not build here: the runner` | Continues the text: these checks also print `SKIP` when the source `bwx11.c` is not in the folder of this file, or when it cannot be built on this machine. |
| 12 | `is the work of another part.` | Continues the text: the reason given is that the runner is the work of another part of the project. |
| 13 | `--no-long leaves out the 10 runs of 30 s that put the real plans of ZM (test divisor 1) through bwx11.` | Text of the description: `--no-long` leaves out the 10 runs of 30 s each that put the real plans of step `ZM`, with the test divisor 1, through `bwx11`. |
| 14 | `Rules are also applied to a defective input, and such a check passes only if that is rejected.` | Text of the description: the test also applies each rule to an input with a defect. Such a check passes only when the rule rejects that input. This shows that the rule can fail. |
| 15 | `This machine has no CPU 41: for the runs through a stand-in the test rewrites CPU 41 to a local CPU` | Text of the description: the machine of the test has no CPU 41. For the runs through a stand-in binary the test replaces CPU 41 with a CPU that the machine has. |
| 16 | `in a copy of the schedule. Nothing else of the copy differs.` | Continues the text: the replacement is made in a copy of the schedule. Nothing else of the copy differs. |
| 17 | `"""` | Ends the description text. |
| 18 | `import collections` | Loads the Python module `collections`: counters and ordered dictionaries. |
| 19 | `import concurrent.futures` | Loads `concurrent.futures`: used to run several stand-in processes at the same time. |
| 20 | `import copy` | Loads `copy`: used to make an independent copy of a schedule before a check damages it. |
| 21 | `import difflib` | Loads `difflib`: used to compare the lines of two script texts. |
| 22 | `import itertools` | Loads `itertools`: used to merge equal neighbours of a list. |
| 23 | `import os` | Loads `os`: paths, folders and CPU lists. |
| 24 | `import re` | Loads `re`: regular expressions. |
| 25 | `import shutil` | Loads `shutil`: copies and removals of folder trees. |
| 26 | `import signal` | Loads `signal`: used to send a signal to the run script. |
| 27 | `import subprocess` | Loads `subprocess`: used to start the scripts under test. |
| 28 | `import sys` | Loads `sys`: the command line, the output and the exit status. |
| 29 | `import tempfile` | Loads `tempfile`: used to make the temporary folder of the test. |
| 30 | `import time` | Loads `time`: the clock, time texts and waits. |

### Paths, expected values of the task, and the functions `skip` and `check` (lines 32 to 92)

| Line | Source | Explanation |
|---:|---|---|
| 32 | `sys.dont_write_bytecode = True` | Tells Python to write no compiled files into a `__pycache__` folder. So the test leaves no file in the code folder. |
| 33 | `Z = os.path.dirname(os.path.abspath(__file__))` | `Z`: the full path of the folder that holds this file, the folder of round 4. |
| 34 | `Y = os.path.join(os.path.dirname(Z), "bwx10-2026-11-15")     # round 3: bwx10.c, run_bwx10.sh, visit10.sh, hostwatch.py` | `Y`: the folder of round 3 beside it, `bwx10-2026-11-15`. The test reads `bwx10.c`, `run_bwx10.sh`, `visit10.sh` and `hostwatch.py` from it. |
| 35 | `X = os.path.join(os.path.dirname(Z), "bwx8-2026-11-14")      # round 1 and 2: run_bwx9.sh` | `X`: the folder of rounds 1 and 2, `bwx8-2026-11-14`. The test reads `run_bwx9.sh` from it. |
| 36 | `SCHED = os.path.join(Z, "schedule11.py")` | `SCHED`: the path of the generator under test, `schedule11.py`. |
| 37 | `RUN = os.path.join(Z, "run_bwx11.sh")` | `RUN`: the path of the run script under test, `run_bwx11.sh`. |
| 38 | `VISIT = os.path.join(Z, "visit11.sh")` | `VISIT`: the path of the visit script under test, `visit11.sh`. |
| 39 | `WATCH = os.path.join(Z, "hostwatch.py")` | `WATCH`: the path of the host sampler `hostwatch.py` in this folder. |
| 40 | `NEW_KERNELS = ["read_nop64", "read_nop96", "read_nop128"]` | `NEW_KERNELS`: the three kernels that the runner `bwx11` adds. |
| 41 | `READ_KERNELS = ["oldread", "read", "asmread", "read_nop4", "read_nop8", "read_nop16", "read_nop32", "read_sparse",` | `READ_KERNELS`: the names of all read kernels that a plan may use. The plan validator of this file accepts only these names. This line holds the first 8. |
| 42 | `                "read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"] + NEW_KERNELS` | Continues the list with 5 more names and adds the three new kernels at the end. The list has 16 names. |
| 43 | `# The flags of build8.sh.` | Comment: the compiler flags that follow are those of the build script `build8.sh`. |
| 44 | `CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "` | `CFLAGS`: the compiler flags for the stand-in builds, split into a list of words. This line: the optimisation level `-O3`, code for the CPU of this machine (`-march=native`), no replacement of a loop by a library call such as `memset` (`-fno-tree-loop-distribute-patterns`), thread support, more warnings, and the C dialect `gnu11`. |
| 45 | `          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()` | Continues the flags: do not merge functions that have equal code (`-fno-ipa-icf`), keep the functions in the order of the source (`-fno-toplevel-reorder`), and align each function to 4 bytes. |
| 46 | `# The task: processes per step and session, trials per process, nominal kernel work in seconds, binary,` | Comment: the table that follows states the task of the generator. For each step it gives the processes per session, the trials per process, the nominal kernel work in seconds and the binary. |
| 47 | `# processes with --evict-mb in session 1.` | Continues the comment: the last value is the number of processes with `--evict-mb` in session 1. |
| 48 | `TABLE = collections.OrderedDict([("ZA", (6, 1, 7.8, "bwx11", 2)), ("ZD", (216, 4, 2073.6, "bwx11", 108)),` | `TABLE`: the expected values, written here as fixed numbers and not taken from the generator. `ZA`: 6 processes of 1 trial, 7.8 s, binary `bwx11`, 2 processes with an evict step. `ZD`: 216 processes of 4 trials, 2073.6 s, 108 with an evict step. |
| 49 | `                                 ("ZC", (32, 1, 192.0, "bwx11", 16)), ("ZN", (144, 4, 1382.4, "bwx11", 0)),` | Continues the table. `ZC`: 32 processes of 1 trial, 192.0 s, 16 with an evict step. `ZN`: 144 processes of 4 trials, 1382.4 s, none with an evict step. |
| 50 | `                                 ("ZM", (40, 1, 1200.0, "bwx11", 0))])` | Ends the table. `ZM`: 40 processes of 1 trial, 1200.0 s, none with an evict step. |
| 51 | `EVENTS = "cpu_cycles=0x11,l1d_cache_lmiss_rd=0x39,l2d_cache_refill=0x17,l2d_cache_wb=0x18,bus_access=0x19,l2d_cache_lmiss_rd=0x4009"` | `EVENTS`: the 6 counter events that step `ZC` must have in its `args` column, written here a second time. So a change of the list in the generator alone makes a check fail. |
| 52 | `# condition name: (megabytes of the evict buffer, the option in args)` | Comment: each entry of `ECOND` maps the name of an evict condition to the MiB of its evict buffer and to its option text in the `args` column. |
| 53 | `ECOND = collections.OrderedDict([("E0", (0, "")), ("E512", (512, " --evict-mb 512"))])` | `ECOND`: the two evict conditions as the test expects them. `E0`: 0 MiB and no option. `E512`: 512 MiB and the option `--evict-mb 512` with a blank before it. |
| 54 | `ZD_KERNELS = ["asmread", "read", "oldread"]` | `ZD_KERNELS`: the three kernels that step `ZD` must use. |
| 55 | `ZD_SIZES = ["4M", "8M", "16M"]` | `ZD_SIZES`: the three buffer sizes that step `ZD` must use: 4, 8 and 16 MiB. |
| 56 | `ZD_CELLS = [(k, e) for k in ZD_KERNELS for e in ECOND]` | `ZD_CELLS`: the 6 cells of step `ZD`: each kernel with each name of an evict condition. |
| 57 | `ZC_KERNELS = ["asmread", "oldread"]` | `ZC_KERNELS`: the two kernels that step `ZC` must use. |
| 58 | `ZC_SIZES = ["8M", "16M"]` | `ZC_SIZES`: the two buffer sizes that step `ZC` must use: 8 and 16 MiB. |
| 59 | `ZN_KERNELS = NEW_KERNELS` | `ZN_KERNELS`: the kernels that step `ZN` must use, the three new kernels. |
| 60 | `ZN_SIZES = ["32K", "1M", "8M", "16M"]` | `ZN_SIZES`: the four buffer sizes that step `ZN` must use: 32 KiB, 1 MiB, 8 MiB and 16 MiB. |
| 61 | `ZM_PADS = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72]` | `ZM_PADS`: the 10 values of `--rec-pad` that step `ZM` must use, in bytes. |
| 62 | `# tag, kernel, size, the options after the plan` | Comment: each entry of the list that follows holds a tag, a kernel, a size and the options that stand after the plan path. |
| 63 | `ZA = [("plain-cpu2", "asmread", "8M", " --trace"), ("evict-cpu2", "asmread", "8M", " --trace --evict-mb 512"),` | `ZA`: the 6 processes that the acceptance step `ZA` must have, in their fixed order. This line: `asmread` without an evict step, and `asmread` with `--evict-mb 512`. Both have `--trace`. |
| 64 | `      ("oldevict-cpu2", "oldread", "8M", " --trace --evict-mb 512"), ("nop64-cpu2", "read_nop64", "8M", " --trace"),` | Continues the list: `oldread` with `--trace` and `--evict-mb 512`, and `read_nop64` with `--trace`. |
| 65 | `      ("nop96-cpu2", "read_nop96", "8M", " --trace"), ("nop128-cpu2", "read_nop128", "8M", " --trace")]` | Ends the list: `read_nop96` and `read_nop128`, each with `--trace`. All 6 processes have a buffer of 8 MiB and a tag that ends with `-cpu2`. |
| 66 | `HEAD_S2 = ["step", "session", "cpu", "bytes", "proc", "rep_set", "kernel", "size", "seed", "test"]` | `HEAD_S2`: the keys of the header pairs of a plan whose trials have the form of step `S2`, in the order that the plan file must have. |
| 67 | `HEAD_ZD = HEAD_S2[:8] + ["econd"] + HEAD_S2[8:]` | `HEAD_ZD`: the same list with the key `econd` put in after `size`. This is the header of a plan of step `ZD`. |
| 68 | `ALL_STEPS = ["ZA", "ZD", "ZC", "ZN", "ZM"]` | `ALL_STEPS`: the names of the 5 steps of round 4. |
| 70 | `FAILS = []` | `FAILS`: the names of the checks that failed, empty at first. |
| 71 | `COUNT = [0]` | `COUNT`: the number of checks. It is kept in a list of one entry, so a function can change it. |
| 74 | `SKIPS = [0]` | `SKIPS`: the number of parts of the test that did not run, kept in the same way. |
| 77 | `def skip(text):` | Starts the function `skip`. It reports one part of the test that did not run. |
| 78 | `    """One part of the test that did not run. The last line of the output gives the number of such parts."""` | Description text: one call stands for one part that did not run. The last line of the output gives the number of such parts. |
| 79 | `    SKIPS[0] += 1` | Counts the part. |
| 80 | `    print("SKIP  " + text)` | Prints a line that starts with `SKIP` and gives the reason. |
| 81 | `    sys.stdout.flush()` | Writes the line to the output immediately. |
| 84 | `def check(name, ok, detail=""):` | Starts the function `check`. Every check of this file calls it. `name`: the sentence that says what is checked. `ok`: the result of the test. `detail`: values to print when the check fails. |
| 85 | `    COUNT[0] += 1` | Counts the check. |
| 86 | `    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail)[:600] + "]") if detail and not ok else ""))` | Prints one line: `PASS` or `FAIL`, and then the name. After a failure it adds the first 600 characters of the detail in square brackets. |
| 87 | `    sys.stdout.flush()` | Writes the line to the output immediately. |
| 88 | `    if not ok:` | When the check failed. |
| 89 | `        FAILS.append(name)` | Keeps its name for the summary at the end. |
| 90 | `    return ok` | Returns the result. A caller can use it to stop a group of checks after a failure. |

### The plan validator of the test: patterns, `nbytes`, `parse_plan`, `rejected` (lines 93 to 178)

| Line | Source | Explanation |
|---:|---|---|
| 93 | `# ---------- an independent validator of plan format v1 (DECISIONS-bwx8.md, "Plan file") ----------` | Comment: the code that follows is a validator of the plan format, version 1. By the comment it is independent: it is written from the section "Plan file" of the notes file `DECISIONS-bwx8.md`, and not from the generator. So it can find a mistake of the generator. |
| 94 | `PHASE = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?):(\d+)$")` | `PHASE`: the pattern of a phase text such as `asmread@8M:1200`. Group 1 holds the kernel name: lower-case letters, digits and `_`. Group 2, after the `@`, holds the size: digits and an optional letter `K`, `M` or `G`. Group 3, after the colon, holds the duration in ms: digits. |
| 95 | `TGT = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?)$")` | `TGT`: the pattern of a target text such as `asmread@8M`. Group 1 holds the kernel name and group 2 the size, as in `PHASE`. A target has no duration. |

Line 96 holds a backslash directly before a `|`. It stands outside the table:

```text
COND = re.compile(r"^[^=|, ]+=[^=|, ]+(\|[^=|, ]+=[^=|, ]+)*$")
```

Explanation of line 96: `COND`: the pattern of a condition label such as `K=asmread|S=8M`. A label is one pair `key=value`, or several pairs with a vertical bar between them. A key and a value have at least one character each. They hold no equals sign, no vertical bar, no comma and no blank.

| Line | Source | Explanation |
|---:|---|---|
| 99 | `def nbytes(tok):` | Starts the function `nbytes`. It converts a size text such as `8M` to a number of bytes. |
| 100 | `    m = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}` | `m`: the factor of each unit letter: 1024 for `K`, 1024 times 1024 for `M`, and 1024 times that for `G`. |
| 101 | `    return int(tok[:-1]) * m[tok[-1]] if tok[-1] in m else int(tok)` | Returns the number before the letter times its factor. A text without a letter is a plain number of bytes. |
| 104 | `def parse_plan(text):` | Starts the function `parse_plan`, the validator. It reads the text of one plan file and tests every rule of the format. |
| 105 | `    """Returns (header dict, header key order, trials) or raises ValueError that names the defect."""` | Description text: the function returns the header pairs as a dictionary, the order of the header keys, and the list of trials. For a defect it raises a `ValueError` whose text names the defect. |
| 106 | `    if not text.endswith("\n"):` | Rule: the file ends with a newline. |
| 107 | `        raise ValueError("no final newline")` | If not: raises the error `no final newline`. |
| 108 | `    lines = text[:-1].split("\n")` | `lines`: the lines of the file, without the last newline. |
| 109 | `    if len(lines) < 4:` | Rule: the file has at least 4 lines. These are 3 header lines and one trial. |
| 110 | `        raise ValueError("fewer than 4 lines")` | If not: raises the error `fewer than 4 lines`. |
| 111 | `    if lines[0] != "# bwx8-plan v1":` | Rule: the first line is exactly `# bwx8-plan v1`. |
| 112 | `        raise ValueError("line 1")` | If not: raises an error with the text `line 1`. |
| 113 | `    if not lines[1].startswith("# "):` | Rule: the second line starts with `#` and a blank. |
| 114 | `        raise ValueError("line 2")` | If not: raises an error with the text `line 2`. |
| 115 | `    head = collections.OrderedDict()` | `head`: the header pairs, kept in the order of the file. |
| 116 | `    for pair in lines[1][2:].split(" "):` | Starts a loop over the pairs of the second line, split at single blanks. |
| 117 | `        k, eq, v = pair.partition("=")` | Splits a pair at the first equals sign into the key `k` and the value `v`. |
| 118 | `        if not k or not eq or not v or k in head or "," in pair:` | Rules for a pair: it has a key, an equals sign and a value. The key was not used before. The pair holds no comma. Two blanks in a row give an empty pair, which fails here. |
| 119 | `            raise ValueError("line 2 pair '%s'" % pair)` | If not: raises an error that shows the pair. |
| 120 | `        head[k] = v` | Stores the pair. |
| 121 | `    for k in ("step", "session", "cpu", "bytes", "proc", "seed", "test"):` | Starts a loop over the 7 keys that every plan must have: `step`, `session`, `cpu`, `bytes`, `proc`, `seed` and `test`. |
| 122 | `        if k not in head:` | Rule: the key is in the header. |
| 123 | `            raise ValueError("line 2 lacks " + k)` | If not: raises an error that names the missing key. |
| 124 | `    if lines[2] != "# trial cond rep prev pfx pred tgt nwin win_ms count bins":` | Rule: the third line is exactly the list of the 11 column names. |
| 125 | `        raise ValueError("line 3")` | If not: raises an error with the text `line 3`. |
| 126 | `    total = int(head["bytes"])` | `total`: the buffer size of the process in bytes, from the header. |
| 127 | `    seen = collections.Counter()` | `seen`: how often each condition label was used up to now. |
| 128 | `    trials = []` | `trials`: the result list, empty at first. |
| 130 | `    def size_ok(tok):` | Starts the inner function `size_ok`. It tests the size of a phase or of a target. |
| 131 | `        b = nbytes(tok)` | `b`: the size in bytes. |
| 132 | `        return b > 0 and b % 256 == 0 and b <= total` | Rule: the size is above 0, a multiple of 256 bytes, and not larger than the buffer of the process. |
| 134 | `    for n, line in enumerate(lines[3:]):` | Starts the loop over the trial lines. `n` counts from 0. |
| 135 | `        f = line.split(" ")` | Splits the line at single blanks. |
| 136 | `        if len(f) != 11 or "" in f:` | Rule: the line has exactly 11 fields, and none is empty. An empty field means two blanks in a row. |
| 137 | `            raise ValueError("trial line %d: fields" % n)` | If not: raises an error that names the trial line and the word `fields`. |
| 138 | `        trial, cond, rep, prev, pfx, pred, tgt, nwin, win_ms, count, bins = f` | Gives the 11 fields their names. |
| 139 | `        if trial != str(n):` | Rule: the trial number is the number of the line, counted from 0. |
| 140 | `            raise ValueError("trial line %d: number" % n)` | If not: raises an error with the word `number`. |
| 141 | `        if not COND.match(cond):` | Rule: the condition label matches the pattern `COND`. |
| 142 | `            raise ValueError("trial line %d: cond" % n)` | If not: raises an error with the word `cond`. |
| 143 | `        seen[cond] += 1` | Counts the use of this label. |
| 144 | `        if rep != str(seen[cond]) or not 1 <= seen[cond] <= 4:` | Rule: `rep` is the number of this use of the label, counted from 1. A label is used at most 4 times. |
| 145 | `            raise ValueError("trial line %d: rep" % n)` | If not: raises an error with the word `rep`. |
| 146 | `        ms = {}` | `ms`: the duration in ms of each of the three phases before the target. |
| 147 | `        for name, tok in (("prev", prev), ("pfx", pfx), ("pred", pred)):` | Starts a loop over the three phases: the previous activity, the prefix and the predecessor. |
| 148 | `            ms[name] = 0` | The duration is 0 unless the phase exists. |
| 149 | `            if tok == "-":` | A `-` means that the trial has no such phase. |
| 150 | `                continue` | Goes on with the next phase. |
| 151 | `            m = PHASE.match(tok)` | Matches the text with the pattern `PHASE`. |
| 152 | `            if not m or m.group(1) not in READ_KERNELS or not size_ok(m.group(2)) or int(m.group(3)) < 1:` | Rules for a phase: the text has the form of `PHASE`, the kernel is one of `READ_KERNELS`, the size passes `size_ok`, and the duration is at least 1 ms. |
| 153 | `                raise ValueError("trial line %d: %s" % (n, name))` | If not: raises an error that names the phase. |
| 154 | `            ms[name] = int(m.group(3))` | Stores the duration. |
| 155 | `        if ms["pfx"] % 4:` | Rule: the duration of the prefix is a multiple of 4 ms. By the notes file the runner records a prefix as 4 windows of a quarter of its duration. |
| 156 | `            raise ValueError("trial line %d: pfx not a multiple of 4" % n)` | If not: raises an error that says so. |
| 157 | `        m = TGT.match(tgt)` | Matches the target text with the pattern `TGT`. |
| 158 | `        if not m or m.group(1) not in READ_KERNELS or not size_ok(m.group(2)):` | Rules for the target: the form of `TGT`, a kernel of `READ_KERNELS`, and a size that passes `size_ok`. |
| 159 | `            raise ValueError("trial line %d: tgt" % n)` | If not: raises an error with the word `tgt`. |
| 160 | `        # The limits of the plan parser of bwx8.c: nwin 1 to 4096 (MAX_NWIN), win_ms 1 to 3600000 (MAX_MS).` | Comment: the next rule uses the limits of the plan parser in the runner source `bwx8.c`: 1 to 4096 windows (`MAX_NWIN`), and a window length of 1 to 3600000 ms (`MAX_MS`), which is one hour. |
| 161 | `        if not (nwin.isdigit() and 1 <= int(nwin) <= 4096 and win_ms.isdigit() and 1 <= int(win_ms) <= 3600000):` | Rule: both values are whole numbers inside these limits. |
| 162 | `            raise ValueError("trial line %d: windows" % n)` | If not: raises an error with the word `windows`. |
| 163 | `        if count not in ("closed", "open", "read") or bins not in ("0", "1"):` | Rule: the counter mode is `closed`, `open` or `read`, and `bins` is `0` or `1`. |
| 164 | `            raise ValueError("trial line %d: count or bins" % n)` | If not: raises an error with the words `count or bins`. |
| 165 | `        trials.append({"cond": cond, "rep": int(rep), "prev": prev, "pfx": pfx, "pred": pred, "tgt": tgt,` | Adds the trial as a dictionary. This line: the label, the repeat number, the three phase texts and the target. |
| 166 | `                       "nwin": int(nwin), "win_ms": int(win_ms), "count": count, "bins": int(bins),` | Continues the dictionary: the number and the length of the windows, the counter mode and the bins value. |
| 167 | `                       "ms": ms["prev"] + ms["pfx"] + ms["pred"] + int(nwin) * int(win_ms)})` | Ends the dictionary with `ms`, the nominal kernel work of the trial in ms: the three phase durations plus the number of windows times the window length. The test computes this value itself, without the generator. |
| 168 | `    return head, list(head), trials` | Returns the header dictionary, the list of its keys in file order, and the trials. |
| 171 | `def rejected(text):` | Starts the function `rejected`. It says whether the validator refuses a plan text. |
| 172 | `    try:` | Starts the block whose error is caught. |
| 173 | `        parse_plan(text)` | Runs the validator. |
| 174 | `    except ValueError:` | The validator raised a `ValueError`. |
| 175 | `        return True` | Returns true: the text was rejected. |
| 176 | `    return False` | Returns false: the text was accepted. |

### Reading a generated folder, and small rule helpers (lines 179 to 262)

| Line | Source | Explanation |
|---:|---|---|
| 179 | `# ---------- reading a generated tree ----------` | Comment: the functions that read a generated folder start here. |
| 180 | `def gen(out, *opts):` | Starts the function `gen`. It runs the generator with the output folder `out` and with more options. |
| 181 | `    return subprocess.run([sys.executable, SCHED, "--out", out] + list(opts), capture_output=True, text=True)` | Starts the generator as a process of its own, with the Python that runs this test. It keeps the output and the error output as text. It returns the result object, which also holds the exit status. |
| 184 | `def load(out):` | Starts the function `load`. It reads every schedule file and every plan file of a generated folder and tests their form. |
| 185 | `    """{(step, session): [process]}; a process holds its schedule row, header and trials."""` | Description text: the result maps each pair of step and session to its list of processes. A process holds its schedule row, its plan header and its trials. |
| 186 | `    tree, errors = {}, []` | `tree`: the result. `errors`: the list of the defects found. Both are empty at first. |
| 187 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 188 | `        sdir = os.path.join(out, "s%d" % session)` | `sdir`: the folder of the session. |
| 189 | `        for name in sorted(os.listdir(sdir)):` | Starts a loop over the names in the session folder, in sorted order. |
| 190 | `            if not name.endswith(".tsv"):` | A name that does not end with `.tsv`. |
| 191 | `                continue` | Skips it. Only schedule files are read here. |
| 192 | `            step = name[:-4]` | `step`: the file name without the ending `.tsv`. |
| 193 | `            rows = open(os.path.join(sdir, name)).read().split("\n")` | `rows`: the lines of the schedule file. |
| 194 | `            if rows[0] != "idx\ttag\tcpu\tbytes\tplan\targs" or rows[-1] != "":` | Rule: the first row is exactly the six column names with tabs between them, and the file ends with a newline. |
| 195 | `                errors.append("%s s%d: header or end of the schedule" % (step, session))` | If not: notes a defect of the header or of the end of the schedule. |
| 196 | `            procs = []` | `procs`: the processes of this step, empty at first. |
| 197 | `            for n, row in enumerate(rows[1:-1]):` | Starts the loop over the data rows. `n` counts from 0. |
| 198 | `                f = row.split("\t")` | Splits the row at the tabs. |
| 199 | `                if len(f) != 6 or f[0] != str(n) or f[4] != "%04d.plan" % n:` | Rule: the row has 6 columns, its `idx` is the row number, and its plan name is that number with 4 digits and the ending `.plan`. |
| 200 | `                    errors.append("%s s%d row %d: columns, idx or plan name" % (step, session, n))` | If not: notes the defect. |
| 201 | `                    continue` | Goes on with the next row. |
| 202 | `                p = {"idx": n, "tag": f[1], "cpu": int(f[2]), "bytes": int(f[3]), "plan": f[4], "args": f[5]}` | `p`: the process as a dictionary of its schedule columns. |
| 203 | `                want = "--trial --cpus %d --bytes %d --plan sched11/s%d/%s/%s" % (p["cpu"], p["bytes"], session, step, f[4])` | `want`: the start that the `args` column must have: `--trial`, `--cpus` with the CPU, `--bytes` with the size, and `--plan` with the path below `sched11/`. The CPU and the size come from the other columns of the row. So the columns must agree with the options. |
| 204 | `                if not (f[5] == want or f[5].startswith(want + " --")):` | Rule: the `args` are exactly `want`, or `want` followed by a blank and more options. |
| 205 | `                    errors.append("%s s%d row %d: args" % (step, session, n))` | If not: notes a defect of the `args`. |
| 206 | `                p["extra"] = f[5][len(want):]` | `extra`: the text of the `args` after `want`, that is the added options. |
| 207 | `                try:` | Starts the block whose errors are caught. |
| 208 | `                    p["head"], p["order"], p["trials"] = parse_plan(open(os.path.join(sdir, step, f[4])).read())` | Reads the plan file of the row and validates it with `parse_plan`. The header, the key order and the trials go into `p`. |
| 209 | `                except (ValueError, OSError) as e:` | A defect of the plan, or a plan file that cannot be read. |
| 210 | `                    errors.append("%s s%d row %d: %s" % (step, session, n, e))` | Notes the defect with the text of the error. |
| 211 | `                    continue` | Goes on with the next row. |
| 212 | `                h = p["head"]` | `h`: the header of the plan. |
| 213 | `                if (h["step"], h["session"], h["cpu"], h["bytes"], h["proc"]) != (step, str(session), f[2], f[3], f[0]):` | Rule: the header of the plan names the same step, session, CPU, size and process number as the schedule row. |
| 214 | `                    errors.append("%s s%d row %d: header pairs differ from the row" % (step, session, n))` | If not: notes that the header pairs differ from the row. |
| 215 | `                procs.append(p)` | Adds the process to the list. |
| 216 | `            tags = [p["tag"] for p in procs]` | `tags`: the tags of all processes of the step. |
| 217 | `            if len(set(tags)) != len(tags) or any(re.search(r"\s", t) for t in tags):` | Rule: no tag occurs twice in a step, and no tag holds a blank or another white-space character (pattern `\s`). |
| 218 | `                errors.append("%s s%d: a tag occurs twice or holds a blank" % (step, session))` | If not: notes the defect. |
| 219 | `            if len(os.listdir(os.path.join(sdir, step))) != len(procs):` | Rule: the plan folder of the step holds exactly as many files as the schedule has rows. |
| 220 | `                errors.append("%s s%d: plan files and rows differ in number" % (step, session))` | If not: notes the defect. |
| 221 | `            tree[step, session] = procs` | Stores the processes of the step and session. |
| 222 | `    return tree, errors` | Returns the result and the list of defects. |
| 225 | `def proc_ms(p):` | Starts the function `proc_ms`: the nominal kernel work of one process in ms. |
| 226 | `    return sum(t["ms"] for t in p["trials"])` | Returns the sum of the `ms` values of its trials. |
| 229 | `def tree_bytes(out):` | Starts the function `tree_bytes`. It reads every file of a folder tree into memory. |
| 230 | `    d = {}` | `d`: the result, empty at first. |
| 231 | `    for root, _, files in os.walk(out):` | Starts a walk through the folder and all folders below it. |
| 232 | `        for f in files:` | Starts a loop over the files of one folder. |
| 233 | `            path = os.path.join(root, f)` | The path of the file. |
| 234 | `            d[os.path.relpath(path, out)] = open(path, "rb").read()` | Stores the bytes of the file under its path relative to the top folder. |
| 235 | `    return d` | Returns the dictionary. Two folder trees are equal when their dictionaries are equal. |
| 238 | `def cpu_blocks(procs, first, second):` | Starts the function `cpu_blocks`, the rule for the CPU order of a schedule. |
| 239 | `    """The CPUs alternate first, second, first, ... when equal neighbours are merged."""` | Description text: when equal neighbours are merged, the CPUs of the processes alternate: the first CPU, the second, the first, and so on. |
| 240 | `    seq = [k for k, _ in itertools.groupby(p["cpu"] for p in procs)]` | `seq`: the CPUs of the processes in schedule order, with each run of equal neighbours merged to one entry. |
| 241 | `    return len(seq) % 2 == 0 and all(c == (first, second)[i % 2] for i, c in enumerate(seq))` | True when the merged list has an even length and alternates, with `first` at its start. |
| 244 | `def cpus_of(session):` | Starts the function `cpus_of`. |
| 245 | `    return (2, 41) if session == 1 else (41, 2)` | Returns the expected CPU order of a session: 2 and then 41 for session 1, and 41 and then 2 for session 2. |
| 248 | `def one_trial(cond, tgt, nwin, win, count="closed", bins=0, pfx=0):` | Starts the function `one_trial`. It builds the trial list that a process with one trial must have, in the form that `parse_plan` returns. |
| 249 | `    return [{"cond": cond, "rep": 1, "prev": "-", "pfx": "%s:%d" % (tgt, pfx) if pfx else "-", "pred": "-", "tgt": tgt,` | Returns a list with one dictionary. This line: the label, repeat 1, no previous activity, a prefix of the target itself when `pfx` is not 0, no predecessor, and the target. |
| 250 | `             "nwin": nwin, "win_ms": win, "count": count, "bins": bins, "ms": pfx + nwin * win}]` | Continues the dictionary: the windows, the counter mode, the bins value and the nominal work in ms. |
| 253 | `def s2_style(p, k, s, tail=""):` | Starts the function `s2_style`, the rule for a process whose trials have the form of step `S2`. `k` is the kernel, `s` the size text, and `tail` the end of the condition label. |
| 254 | `    """4 trials: the kernel at the size, with itself as 1.2 s prefix, 4 windows, uncounted. tail: the end of the cond label."""` | Description text: the process has 4 trials. Each runs the kernel at the size, with itself as a prefix of 1.2 s, in 4 windows, without counters. `tail` is the end of the condition label. |
| 255 | `    t = p["trials"]` | `t`: the trials of the process. |
| 256 | `    return len(t) == 4 and all(` | Starts the result. First condition: exactly 4 trials. |
| 257 | `        x == {"cond": "K=%s\|S=%s%s" % (k, s, tail), "rep": i + 1, "prev": "-", "pfx": "%s@%s:%d" % (k, s, 4 * x["win_ms"]),` | Second condition, for each trial: it is equal to the expected dictionary. This line: the label with the kernel, the size and `tail`. The repeat number, 1 to 4. No previous activity. A prefix of the same kernel and size that lasts 4 times the window length. |
| 258 | `              "pred": "-", "tgt": "%s@%s" % (k, s), "nwin": 4, "win_ms": x["win_ms"], "count": "closed", "bins": 0,` | Continues the expected dictionary: no predecessor, the target, 4 windows, the window length as found, counters closed, bins 0. The window length is not fixed here. So the rule also holds for a folder made with a test divisor. |
| 259 | `              "ms": 8 * x["win_ms"]} for i, x in enumerate(t)) and \` | Ends the expected dictionary: the nominal work is 8 window lengths, 4 for the prefix and 4 for the target. The backslash joins the next line to this statement. |
| 260 | `        p["bytes"] == nbytes(s) and p["head"].get("size") == str(nbytes(s)) and p["head"].get("kernel") == k` | Last conditions: the buffer of the process has the size `s`, and the header names that size and the kernel. |

### Rules of the steps: `set_rules`, the order rules that `ZD` and `ZN` share (lines 263 to 309)

| Line | Source | Explanation |
|---:|---|---|
| 263 | `# ---------- rules of the steps; each returns a list of defects. div: the test divisor of the tree ----------` | Comment: the functions that follow are the rules of the steps. Each one returns a list of defects. `div` is the test divisor of the folder that is tested. |
| 264 | `def set_rules(procs, cpus, items, sizes, item_of, times, what):` | Starts the function `set_rules`. `items`: the items of one replicate set, cells or kernels. `sizes`: the size texts of the step. `item_of`: a function that gives the item of a process. `times`: how often each item must stand at each position. `what`: a word for the messages. |
| 265 | `    """Shared by ZD and ZN. The processes come in 6 replicate sets. A set holds the sizes in one order; a size holds` | Description text: the steps `ZD` and `ZN` share these rules. The processes come in 6 replicate sets. A set holds the sizes in one order. |
| 266 | ``    the first CPU, then the second; a CPU holds every item once. Per size and CPU: every item is `times` times at`` | Continues the text: a size holds the first CPU and then the second. A CPU holds every item once. For each size and CPU, every item stands `times` times at each position. |
| 267 | ``    every position, and every ordered pair of items is `times` times a pair of neighbours."""`` | Continues the text: and every ordered pair of items stands `times` times as a pair of neighbours. |
| 268 | `    bad = []` | `bad`: the list of the defects found. An empty list means that the rules hold. |
| 269 | `    n = len(items)` | `n`: the number of items in one set. |
| 270 | `    sets = collections.defaultdict(lambda: collections.defaultdict(list))` | `sets`: for each pair of size and CPU, and for each replicate set, a list in schedule order. A missing entry is created at its first use. |
| 271 | `    for p in procs:` | Starts the loop over the processes in schedule order. |
| 272 | `        sets[p["tag"].split("-")[1], p["cpu"]][int(p["head"].get("rep_set", 0))].append(item_of(p))` | Adds the item of the process to its list. The size is the second part of the tag, the CPU comes from the schedule row, and the replicate set comes from the plan header. |
| 273 | `    assign = set()` | `assign`: the different tables of orders that were seen, one table per size and CPU. |
| 274 | `    if len(sets) != 2 * len(sizes):` | Rule: there are 2 pairs of size and CPU for each size. |
| 275 | `        bad.append("sizes and CPUs")` | If not: notes the defect `sizes and CPUs`. |
| 276 | `    for (s, cpu), orders in sets.items():` | Starts the loop over the pairs of size and CPU. |
| 277 | `        o = [tuple(orders[r]) for r in sorted(orders)]` | `o`: the orders of the replicate sets of this pair, sorted by the set number. |
| 278 | `        if sorted(orders) != [1, 2, 3, 4, 5, 6] or any(sorted(x) != sorted(items) for x in o):` | Rule: the sets have the numbers 1 to 6, and each set holds every item exactly once. |
| 279 | `            bad.append("size %s cpu %d: not 6 sets of the %d %s" % (s, cpu, n, what))` | If not: notes that this size and CPU does not have 6 sets of the items. |
| 280 | `            continue` | Goes on with the next pair of size and CPU. |
| 281 | `        pos = collections.Counter((k, i) for x in o for i, k in enumerate(x))` | `pos`: how often each item stands at each position, over the 6 sets. |
| 282 | `        if len(pos) != n * n or set(pos.values()) != {times}:` | Rule: every item occurs at every position, and each of these counts is exactly `times`. This is the balance of the position: no item always runs first or always runs last. |
| 283 | `            bad.append("size %s cpu %d: an item is not %d time(s) at each position" % (s, cpu, times))` | If not: notes that an item is not `times` times at each position. |
| 284 | `        pairs = collections.Counter((x[i], x[i + 1]) for x in o for i in range(n - 1))` | `pairs`: how often each ordered pair of items stands as direct neighbours, over the 6 sets. |
| 285 | `        if len(pairs) != n * (n - 1) or set(pairs.values()) != {times}:` | Rule: every ordered pair of different items occurs, and each exactly `times` times. This is the balance of the process that runs directly before: each item follows each other item equally often. |
| 286 | `            bad.append("size %s cpu %d: an ordered pair is not %d time(s) a pair of neighbours" % (s, cpu, times))` | If not: notes that an ordered pair is not `times` times a pair of neighbours. |
| 287 | `        assign.add(tuple(o))` | Remembers the table of this size and CPU. |
| 288 | `    if len(assign) < 2:` | Rule: at least two pairs of size and CPU have different tables. |
| 289 | `        bad.append("every size and CPU uses the same orders")` | If not: notes that every size and CPU uses the same orders. That would show that the tables are not drawn at random for each size and CPU. |
| 290 | `    per_set = 2 * n * len(sizes)` | `per_set`: the number of processes of one replicate set: 2 CPUs times the items times the sizes. |
| 291 | `    size_orders = set()` | `size_orders`: the different size orders of the sets. |
| 292 | `    for r in range(6):` | Starts the loop over the 6 replicate sets, by their place in the schedule. |
| 293 | `        block = procs[per_set * r:per_set * (r + 1)]` | `block`: the processes of this set, a slice of `per_set` processes. |
| 294 | `        if any(p["head"].get("rep_set") != str(r + 1) for p in block):` | Rule: every process of the block names this set in its header. So the sets follow each other and do not mix. |
| 295 | `            bad.append("block %d: rep_set" % (r + 1))` | If not: notes a defect of the `rep_set` value of this block. |
| 296 | `        got = []` | `got`: the sizes of the block in schedule order. |
| 297 | `        for g in range(len(sizes)):` | Starts the loop over the size groups of the block. |
| 298 | `            group = block[2 * n * g:2 * n * (g + 1)]` | `group`: the processes of one size: the items on the first CPU and then the items on the second CPU. |
| 299 | `            if len({p["bytes"] for p in group}) != 1 or [p["cpu"] for p in group] != [cpus[0]] * n + [cpus[1]] * n:` | Rule: the group has one buffer size, and its CPUs are `n` times the first CPU of the session followed by `n` times the second. So the CPUs do not alternate inside a size. |
| 300 | `                bad.append("block %d group %d: size or CPU order" % (r + 1, g))` | If not: notes a defect of the size or of the CPU order of this group. |
| 301 | `            got.append(group[0]["bytes"] if group else None)` | Adds the size of the group to `got`. |
| 302 | `        if sorted(got, key=str) != sorted((nbytes(s) for s in sizes), key=str):` | Rule: the block holds every size of the step once. |
| 303 | `            bad.append("block %d: a size is missing" % (r + 1))` | If not: notes that a size is missing in this block. |
| 304 | `        size_orders.add(tuple(got))` | Remembers the size order of this block. |
| 305 | `    if len(size_orders) < 2:` | Rule: at least two blocks have different size orders. |
| 306 | `        bad.append("the size order is the same in every block")` | If not: notes that the size order is the same in every block. That would show that the sizes are not shuffled. |
| 307 | `    return bad` | Returns the list of defects. |

### Rules of the steps `ZD` and `ZN` (lines 310 to 344)

| Line | Source | Explanation |
|---:|---|---|
| 310 | `def zd_rules(procs, cpus):` | Starts the function `zd_rules`, the rules of step `ZD`. It returns the list of defects. |
| 311 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 312 | `    if len(procs) != 216:` | Rule: the step has 216 processes. |
| 313 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect, with the count found. |
| 314 | `    for p in procs:` | Starts the loop over the processes. |
| 315 | `        h = p["head"]` | `h`: the header of the plan. |
| 316 | `        k, s, e = h.get("kernel"), p["tag"].split("-")[1], h.get("econd")` | `k`: the kernel from the header. `s`: the size text from the tag. `e`: the evict condition from the header. |
| 317 | `        if k not in ZD_KERNELS or s not in ZD_SIZES or e not in ECOND:` | Rule: the kernel, the size and the condition are among those of `ZD`. |
| 318 | `            bad.append("process %d: kernel, size or condition" % p["idx"])` | If not: notes the defect for this process. |
| 319 | `            continue` | Goes on with the next process. |
| 320 | `        if not s2_style(p, k, s, "\|evict=%d" % ECOND[e][0]):` | Rule: the process has 4 trials of the `S2` form, and each label ends with `evict=` and the MiB of the evict buffer of its condition. |
| 321 | `            bad.append("process %d: not 4 trials of one kernel with itself as prefix and the evict label of its condition" % p["idx"])` | If not: notes the defect. |
| 322 | `        if p["order"] != HEAD_ZD or p["extra"] != ECOND[e][1] or p["tag"] != "r%s-%s-cpu%d-%s-%s" % (h.get("rep_set"), s, p["cpu"], k, e):` | Three rules. The header keys are those of `HEAD_ZD`, in that order. The added options are exactly the option of the condition: nothing for `E0`, and `--evict-mb 512` for `E512`. The tag is built from the set, the size, the CPU, the kernel and the condition. |
| 323 | `            bad.append("process %d: header keys, the option of the condition in args, or tag" % p["idx"])` | If not: notes the defect. |
| 324 | `    if bad:` | When a single process has a defect. |
| 325 | `        return bad` | Returns the defects now. The order rules are then not tested. |
| 326 | `    return set_rules(procs, cpus, ZD_CELLS, ZD_SIZES, lambda p: (p["head"]["kernel"], p["head"]["econd"]), 1, "cells")` | Returns the defects of the shared order rules. The items are the 6 cells, each a pair of kernel and condition. `times` is 1: each cell once at each position, and each ordered pair of cells once as neighbours. That is a Williams square. |
| 329 | `def zn_rules(procs, cpus):` | Starts the function `zn_rules`, the rules of step `ZN`. |
| 330 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 331 | `    if len(procs) != 144:` | Rule: the step has 144 processes. |
| 332 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 333 | `    for p in procs:` | Starts the loop over the processes. |
| 334 | `        h = p["head"]` | `h`: the header of the plan. |
| 335 | `        k, s = h.get("kernel"), p["tag"].split("-")[1]` | `k`: the kernel from the header. `s`: the size text from the tag. |
| 336 | `        if k not in ZN_KERNELS or s not in ZN_SIZES or not s2_style(p, k, s):` | Rule: the kernel is one of the three slow kernels, the size is one of the four sizes of `ZN`, and the process has 4 trials of the `S2` form. |
| 337 | `            bad.append("process %d: not 4 trials of one slow load-only kernel with itself as prefix" % p["idx"])` | If not: notes that the process does not have 4 trials of one slow load-only kernel with itself as the prefix. |
| 338 | `        if p["order"] != HEAD_S2 or p["extra"]:` | Rule: the header keys are those of `HEAD_S2`, and the process has no added option. |
| 339 | `            bad.append("process %d: header keys or args" % p["idx"])` | If not: notes the defect. |
| 340 | `    if bad:` | When a single process has a defect. |
| 341 | `        return bad` | Returns the defects now. |
| 342 | `    return set_rules(procs, cpus, ZN_KERNELS, ZN_SIZES, lambda p: p["head"]["kernel"], 2, "kernels")` | Returns the defects of the shared order rules. The items are the 3 kernels. `times` is 2: each kernel twice at each position, and each ordered pair of kernels twice as neighbours. The 6 possible orders of 3 kernels give exactly this. |

### Rules of the steps `ZC`, `ZM` and `ZA`, and the helper `untagged` (lines 345 to 424)

| Line | Source | Explanation |
|---:|---|---|
| 345 | `def zc_rules(procs, cpus, div=1):` | Starts the function `zc_rules`, the rules of step `ZC`. `div` is the test divisor, 1 for a real schedule. |
| 346 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 347 | `    if len(procs) != 32:` | Rule: the step has 32 processes. |
| 348 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 349 | `    cells = sorted((k, s, e) for k in ZC_KERNELS for s in ZC_SIZES for e in ECOND)` | `cells`: the sorted list of the 8 expected cells: each kernel with each size and each evict condition. |
| 350 | `    orders = set()` | `orders`: the different cell orders of the blocks. |
| 351 | `    for b in range(4):` | Starts the loop over the 4 blocks of 8 processes. |
| 352 | `        block = procs[8 * b:8 * b + 8]` | `block`: the 8 processes of this block. |
| 353 | `        r, cpu = b // 2 + 1, cpus[b % 2]` | `r`: the replicate that the block must have: 1 for the first two blocks and 2 for the last two. `cpu`: the CPU that it must have: the first CPU of the session for the blocks 0 and 2, the second for the blocks 1 and 3. |
| 354 | `        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):` | Rule: every process of the block runs on that CPU and names that replicate in its header. |
| 355 | `            bad.append("block %d: CPU or rep_set" % b)` | If not: notes a defect of the CPU or of `rep_set` in this block. |
| 356 | `        got = [tuple(p["trials"][0]["tgt"].split("@")) + (p["head"].get("econd"),) for p in block]` | `got`: for each process of the block its cell: the kernel and the size from the target of its trial, and the evict condition from the header. |
| 357 | `        if sorted(got, key=str) != cells:` | Rule: the block, sorted, is the list of the 8 cells. So each block holds every kernel, size and condition exactly once. |
| 358 | `            bad.append("block %d: does not hold every kernel, size and condition once" % b)` | If not: notes the defect. |
| 359 | `        orders.add(tuple(got))` | Remembers the cell order of this block. |
| 360 | `    for p in procs:` | Starts a loop over all processes. |
| 361 | `        k, s = p["trials"][0]["tgt"].split("@")` | `k`, `s`: the kernel and the size text from the target of the first trial. |
| 362 | `        e = p["head"].get("econd")` | `e`: the evict condition from the header. |
| 363 | `        if e not in ECOND:` | Rule: the condition is one of the two known conditions. |
| 364 | `            bad.append("process %d: econd" % p["idx"])` | If not: notes the defect. |
| 365 | `            continue` | Goes on with the next process. |
| 366 | `        if p["trials"] != one_trial("K=%s\|S=%s\|evict=%d\|count=read" % (k, s, ECOND[e][0]), "%s@%s" % (k, s), 20, 300 // div, "read"):` | Rule: the process has exactly this one trial: the label with kernel, size, the MiB of the evict buffer and `count=read`, no prefix, 20 windows of 300 ms divided by `div`, and the counter mode `read`. |
| 367 | `            bad.append("process %d: trial" % p["idx"])` | If not: notes a defect of the trial. |
| 368 | `        if p["bytes"] != nbytes(s) or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)):` | Rule: the buffer has the size of the target, and the header names that kernel and that size in bytes. |
| 369 | `            bad.append("process %d: bytes or header" % p["idx"])` | If not: notes a defect of the bytes or of the header. |
| 370 | `        if p["extra"] != ECOND[e][1] + " --pmu-type 11 --events " + EVENTS:` | Rule: the added options are exactly the option of the evict condition, then `--pmu-type 11`, then `--events` with the 6 events of `EVENTS`. Without these options the runner would need the counter settings from the environment. |
| 371 | `            bad.append("process %d: the option of the condition or the event set in args" % p["idx"])` | If not: notes the defect. |
| 372 | `    if len(orders) < 2:` | Rule: at least two blocks have different cell orders. |
| 373 | `        bad.append("the cell order is the same in every block")` | If not: notes that the cell order is the same in every block. That would show that the cells are not shuffled. |
| 374 | `    return bad` | Returns the list of defects. |
| 377 | `def zm_rules(procs, cpus, div=1):` | Starts the function `zm_rules`, the rules of step `ZM`. |
| 378 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 379 | `    if len(procs) != 40:` | Rule: the step has 40 processes. |
| 380 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 381 | `    names = ["P%d" % p for p in ZM_PADS]` | `names`: the 10 expected pad labels, `P0` to `P72`. |
| 382 | `    for b in range(4):` | Starts the loop over the 4 blocks of 10 processes. |
| 383 | `        block = procs[10 * b:10 * b + 10]` | `block`: the 10 processes of this block. |
| 384 | `        r, cpu = b // 2 + 1, cpus[b % 2]` | `r` and `cpu`: the replicate and the CPU that the block must have, as in `zc_rules`. |
| 385 | `        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):` | Rule: every process of the block runs on that CPU and names that replicate in its header. |
| 386 | `            bad.append("block %d: CPU or rep_set" % b)` | If not: notes the defect. |
| 387 | `        if sorted(p["head"].get("pcond", "") for p in block) != sorted(names):` | Rule: the pad labels of the block, sorted, are the 10 labels. So each block holds every pad exactly once. |
| 388 | `            bad.append("block %d: does not hold every pad once" % b)` | If not: notes the defect. |
| 389 | `    for p in procs:` | Starts a loop over all processes. |
| 390 | `        name = p["head"].get("pcond")` | `name`: the pad label from the header pair `pcond`. |
| 391 | `        if name not in names:` | Rule: the label is one of the 10 labels. |
| 392 | `            bad.append("process %d: pcond" % p["idx"])` | If not: notes the defect. |
| 393 | `            continue` | Goes on with the next process. |
| 394 | `        if p["trials"] != one_trial("K=asmread\|S=8M\|rec=%s" % name, "asmread@8M", 300, 100 // div):` | Rule: the process has exactly this one trial: the label with `asmread`, 8 MiB and the pad label, no prefix, 300 windows of 100 ms divided by `div`, counters closed. |
| 395 | `            bad.append("process %d (%s): trial" % (p["idx"], name))` | If not: notes a defect of the trial. |
| 396 | `        if p["extra"] != " --rec-pad " + name[1:]:` | Rule: the added option is exactly `--rec-pad` with the number of the label. So the label of a process and the pad that the runner really uses cannot differ. |
| 397 | `            bad.append("process %d (%s): the option in args" % (p["idx"], name))` | If not: notes the defect. |
| 398 | `        if p["bytes"] != 8 << 20 or p["head"].get("kernel") != "asmread" or p["head"].get("size") != str(8 << 20) \` | Rules: the buffer has 8 MiB (`8 << 20` bytes), and the header names `asmread` and that size. The backslash joins the next line. |
| 399 | `                or not p["tag"].startswith(name + "-"):` | Continues the rules: the tag starts with the pad label and a hyphen. |
| 400 | `            bad.append("process %d (%s): bytes, header or tag" % (p["idx"], name))` | If not: notes the defect. |
| 401 | `    if len({tuple(p["head"].get("pcond") for p in procs[10 * b:10 * b + 10]) for b in range(4)}) < 2:` | Rule: at least two of the 4 blocks have different pad orders. |
| 402 | `        bad.append("the pad order is the same in every block")` | If not: notes that the pad order is the same in every block. That would show that the pads are not shuffled. |
| 403 | `    return bad` | Returns the list of defects. |
| 406 | `def za_rules(procs, div=1):` | Starts the function `za_rules`, the rules of the acceptance step. `div` is the test divisor. |
| 407 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 408 | `    if len(procs) != 6:` | Rule: the step has 6 processes. |
| 409 | `        return ["process count %d" % len(procs)]` | If not: returns this one defect. |
| 410 | `    for p, (tag, k, s, extra) in zip(procs, ZA):` | Starts a loop that pairs each process with the expected entry of the list `ZA`, in order. So the order of the processes is fixed. |
| 411 | `        ks = "%s@%s" % (k, s)` | `ks`: the kernel and the size in the form `KERNEL@SIZE`. |
| 412 | `        name = tag[:-5]` | `name`: the tag without its last 5 characters, which are `-cpu2`. |
| 413 | `        if p["tag"] != tag or p["cpu"] != 2 or p["bytes"] != nbytes(s) or p["extra"] != extra \` | Rules: the tag, CPU 2, the buffer size and the added options are those of the expected entry. The backslash joins the next line. |
| 414 | `                or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)) or p["head"].get("acond") != name:` | Continues the rules: the header names the kernel, the size in bytes and, under the key `acond`, the name. |
| 415 | `            bad.append("process %d: tag, CPU, bytes, args or header" % p["idx"])` | If not: notes the defect. |
| 416 | `        if p["trials"] != one_trial("K=%s\|S=%s\|acc=%s" % (k, s, name), ks, 3, 300 // div, "closed", 0, 400 // div):` | Rule: the process has exactly this one trial: a prefix of 400 ms and 3 windows of 300 ms, both divided by `div`, counters closed, bins 0. |
| 417 | `            bad.append("process %d: trial" % p["idx"])` | If not: notes a defect of the trial. |
| 418 | `    return bad` | Returns the list of defects. |
| 421 | `def untagged(procs):` | Starts the function `untagged`. |
| 422 | `    return [p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in procs]` | Returns the tags of the processes with the CPU number removed: `cpu2` and `cpu41` both become `c`. Two schedules can then be compared without regard to the CPUs. |

### `schedule_checks`: the generator runs, the validator can fail, counts and report (lines 425 to 489)

| Line | Source | Explanation |
|---:|---|---|
| 425 | `def schedule_checks(tmp):` | Starts the function `schedule_checks`. It holds all checks of the generator. |
| 426 | `    a, b, c = (os.path.join(tmp, n) for n in ("a", "b", "c"))` | `a`, `b`, `c`: three output folders in the temporary folder `tmp`. |
| 427 | `    r = gen(a)` | Runs the generator with its default options into the folder `a`. |
| 428 | `    check("schedule11.py runs with status 0", r.returncode == 0, r.stderr)` | Check: the generator ends with exit status 0. This proves that it runs to its end and that its own balance checks passed. A failed balance check would give status 1. |
| 429 | `    tree, errors = load(a)` | Reads the generated folder and collects the format defects. |
| 430 | `    check("every schedule row and plan file obeys the format and the plan grammar", not errors, errors[:3])` | Check: `load` found no defect. So every schedule row has the right form, and every plan file passes the validator of this file. This matters: the runner ends with status 2 for a plan with a defect. |
| 431 | `    check("the 5 steps exist in session 1; session 2 has the same steps without ZA",` | Starts a check: the folder holds exactly the right steps. |
| 432 | `          sorted(tree) == sorted([(s, 1) for s in TABLE] + [(s, 2) for s in TABLE if s != "ZA"]), sorted(tree))` | The test of that check: the pairs of step and session are the 5 steps in session 1, and the same steps without `ZA` in session 2. So no step is missing, and no step was written that the task does not name. |
| 434 | `    # The validator itself rejects defective plans.` | Comment: the next checks show that the validator itself rejects plans with a defect. |
| 435 | `    good = open(os.path.join(a, "s1", "ZM", "0000.plan")).read()` | `good`: the text of the first plan of `ZM` in session 1, a plan without a prefix. |
| 436 | `    good1 = open(os.path.join(a, "s1", "ZA", "0000.plan")).read()` | `good1`: the text of the first plan of `ZA` in session 1, a plan with the prefix `asmread@8M:400`. |
| 437 | `    line = good.split("\n")[3]` | `line`: the fourth line of `good`, its one trial line. |
| 438 | `    bad = {"rep not 1": good.replace(line, line.replace(" 1 - ", " 2 - ", 1)),` | `bad`: a dictionary of plan texts with one defect each. The key names the defect. First entry: the repeat number of the trial is 2 in place of 1. |
| 439 | `           "size above bytes": good1.replace("asmread@8M:400", "asmread@16M:400"),` | A prefix at 16 MiB in a process whose buffer has 8 MiB. |
| 440 | `           "unknown kernel": good1.replace("asmread@8M:400", "copy@8M:400"),` | A prefix with the kernel name `copy`, which is not a read kernel. |
| 441 | `           "prefix without a duration": good1.replace("asmread@8M:400", "asmread@8M"),` | A prefix without a colon and a duration. |
| 442 | `           "prefix that is not a multiple of 4 ms": good1.replace("asmread@8M:400", "asmread@8M:401"),` | A prefix of 401 ms, which is not a multiple of 4 ms. |
| 443 | `           "two spaces": good.replace(line, line.replace(" ", "  ", 1)),` | Two blanks in place of the first blank of the trial line. |
| 444 | `           "trial number": good.replace("\n0 ", "\n1 ", 1),` | The first trial has the number 1 in place of 0. |
| 445 | `           "wrong first line": good.replace("plan v1", "plan v2"),` | The first line names version 2 of the format. |
| 446 | `           "count word": good.replace(line, line.replace("closed", "shut")),` | The counter mode is the word `shut`, which does not exist. |
| 447 | `           "bins 2": good.replace(line, line[:-1] + "2"),` | The last field, `bins`, is 2. |
| 448 | `           "4097 windows": good.replace(line, re.sub(r" \d+ (\d+ closed)", r" 4097 \1", line)),` | 4097 windows, one more than the limit. The pattern finds a blank, digits, a blank, and then a group of digits, a blank and the word `closed`. These are the fields `nwin`, `win_ms` and `count`. The replacement puts 4097 in place of the first number and keeps the group (`\1`). |
| 449 | `           "a window of 3600001 ms": good.replace(line, re.sub(r" (\d+) \d+ closed", r" \1 3600001 closed", line)),` | A window length of 3600001 ms, 1 ms above the limit. Here the group holds the number of windows, which is kept. The second number is replaced. |
| 450 | `           "comma in cond": good.replace(line, line.replace("\|", ",", 1)),` | A comma in place of the first vertical bar of the condition label. |
| 451 | `           "blank in cond": good.replace(line, line.replace("\|", " ", 1)),` | A blank in place of the first vertical bar. The trial line then has 12 fields. |
| 452 | `           "header lacks seed": good.replace(" seed=", " sead=")}` | The header key `seed` is written `sead`, so the required key is missing. The brace ends the dictionary. |
| 453 | `    check("validator accepts generated plans", not rejected(good) and not rejected(good1))` | Check: the validator accepts the two plans as the generator wrote them. This is the control for the checks that follow: a rejection there comes from the defect alone. |
| 454 | `    for name, text in bad.items():` | Starts a loop over the damaged plans. |
| 455 | `        check("validator rejects: " + name, text not in (good, good1) and rejected(text))` | Check, once per defect: the damaged text really differs from the two good plans, and the validator rejects it. This proves that each of these rules of the validator can fail. A validator that accepts every text would make the format check of line 430 prove nothing. |
| 457 | `    # Counts and nominal work, from the files and from the printed report.` | Comment: the next checks compare the counts and the nominal work with the task. They take them from the files and from the report that the generator prints. |
| 458 | `    for step, (n, tr, sec, word, ev) in TABLE.items():` | Starts a loop over the rows of `TABLE`: per step the expected processes, trials per process, seconds, word of the binary and evict count. |
| 459 | `        for s in (1, 2):` | Starts a loop over the two sessions. |
| 460 | `            if (step, s) not in tree:` | A step that does not exist in this session. |
| 461 | `                continue` | Skips it. |
| 462 | `            procs = tree[step, s]` | `procs`: the processes of this step and session, as read from the files. |
| 463 | `            ms = sum(proc_ms(p) for p in procs)` | `ms`: the nominal kernel work of the step in ms. The validator of this file computed it from the plan files. |
| 464 | `            nev = sum(1 for p in procs if "--evict-mb" in p["extra"])` | `nev`: the number of processes whose added options hold `--evict-mb`. |
| 465 | `            check("%s session %d: %d processes of %d trial(s), %.1f s of nominal kernel work, %d processes with --evict-mb 512"` | Starts a check, once per step and session. Its name states the expected values. |
| 466 | `                  % (step, s, n, tr, sec, ev),` | The values for the name of the check. |
| 467 | `                  len(procs) == n and all(len(p["trials"]) == tr for p in procs) and ms == round(sec * 1000) and nev == ev` | The test of the check: the number of processes, the number of trials of every process, the nominal work in ms and the evict count are those of `TABLE`. |
| 468 | `                  and all(" --evict-mb 512" in p["extra"] for p in procs if "--evict-mb" in p["extra"]), (len(procs), ms, nev))` | Last condition: every process that has an evict option holds the text `--evict-mb 512`. Together this proves that the files hold the planned task. A wrong count would make a session shorter or longer than planned, and a missing process would leave a cell with too few runs. |
| 469 | `            check("%s session %d: the report prints the binary, the process count, the nominal work and the evict count" % (step, s),` | Starts a second check per step and session: the printed report agrees with the files. |
| 470 | `                  ("\n%s %d %s %d %d %g %d\n" % (step, s, word, n, n * tr, sec, ev)) in r.stdout, r.stdout[:400])` | The test: the output of the generator holds the table row of this step and session with the same values: the word of the binary, the processes, the trials (processes times trials per process), the seconds and the evict count. So the numbers that a person reads before a run are the numbers of the files. |
| 471 | `    check("the report prints the totals of each session: 438 processes and 4855.8 s, 432 processes and 4848 s",` | Starts a check: the report prints the totals of each session. |
| 472 | `          "\nsession 1 total: 438 processes, nominal kernel work 4855.8 s (80.93 min)\n" in r.stdout` | The test, first half: the line of session 1 gives 438 processes and 4855.8 s (80.93 min) of nominal kernel work. |
| 473 | `          and "\nsession 2 total: 432 processes, nominal kernel work 4848 s (80.8 min)\n" in r.stdout, r.stdout[:900])` | Second half: the line of session 2 gives 432 processes and 4848 s (80.8 min). These totals say how long a session lasts at least. |
| 474 | `    check("the report states the evict step of each session: 126 and 124 processes, real time that is not kernel work, "` | Starts a check: the report states the evict step of each session. |
| 475 | `          "est. 0.3 to 1 s per process, not in the nominal work",` | Continues the name of the check. |
| 476 | `          all(re.search(r"^session %d evict step: %d processes run with --evict-mb 512; the evict step is real time that is not "` | The test: a pattern must match one line of the report per session. `re.M` lets `^` match at the start of every line. The pattern is the text of the line, with each dot written as `\.`. This part: the session, the number of processes with `--evict-mb 512`, and the statement that the evict step is real time. |
| 477 | `                        r"kernel work, est\. 0\.3 to 1 s per process, so est\. %s to %d s more in the session; it is not in the "` | Continues the pattern: that time is not kernel work, est. 0.3 to 1 s per process, and the estimated sum for the session. |
| 478 | `                        r"nominal kernel work" % (s, n, lo, n), r.stdout, re.M)` | Ends the pattern: the evict time is not in the nominal kernel work. The values are put in from the list of line 479. |
| 479 | `              for s, n, lo in ((1, 126, r"37\.8"), (2, 124, r"37\.2"))), r.stdout[:1500])` | The expected values: 126 processes and est. 37.8 to 126 s in session 1, 124 processes and est. 37.2 to 124 s in session 2. This matters: the evict step adds real run time that the nominal work does not show. |
| 480 | `    check("the report states the balance of ZD, ZC, ZN and ZM for both sessions, each with 'yes'",` | Starts a check: the report states the balance of the four shuffled steps, each with `yes`. |
| 481 | `          len(re.findall(r"^Z[DCNM] session [12]: .*: yes$", r.stdout, re.M)) == 8 and ": NO" not in r.stdout, r.stdout[-900:])` | The test: exactly 8 lines match the pattern, one for each of the steps `ZD`, `ZC`, `ZN` and `ZM` in each session. The pattern matches a line that starts with `Z` and one of the letters D, C, N, M, then the word `session`, 1 or 2, a colon, any text, and `: yes` at its end. Also no line holds `: NO`. |
| 482 | `    short = copy.deepcopy(tree["ZD", 1])` | `short`: an independent copy of the processes of `ZD` in session 1. |
| 483 | `    short[0]["trials"].pop()` | Removes the last trial of the first process of the copy. |
| 484 | `    check("nominal work: a schedule with one trial missing does not give the ZD value",` | Starts a check: a schedule with one trial missing does not give the nominal work of `ZD`. |
| 485 | `          sum(proc_ms(p) for p in short) != 2073600)` | The test: the sum of the copy is not 2073600 ms. This proves that the work check of lines 465 to 468 can fail. It notices one missing trial. |
| 486 | `    check("one process at a time is at most 30 s of kernel work (ZM)",` | Starts a check: no process has more than 30 s of nominal kernel work. |
| 487 | `          max(proc_ms(p) for procs in tree.values() for p in procs) == 30000` | The test, first half: the largest nominal work of one process, over all steps and sessions, is exactly 30000 ms. |
| 488 | `          and all(proc_ms(p) == 30000 for p in tree["ZM", 1]))` | Second half: every process of `ZM` in session 1 has exactly 30000 ms. The longest process matters: the run script computes `MARGIN` from it. |

### `schedule_checks`: header pairs, evict labels, kernels, CPU order (lines 490 to 533)

| Line | Source | Explanation |
|---:|---|---|
| 490 | `    # Header pairs.` | Comment: the next checks test the header pairs of the plans. |
| 491 | `    check("plan headers: seed is one value per step and session, test=0",` | Starts a check: inside one step and session every plan has the same seed, and every plan has `test=0`. |
| 492 | `          all(len({p["head"]["seed"] for p in procs}) == 1 and all(p["head"]["test"] == "0" for p in procs)` | The test: the set of the seed values of a step and session has one member, and the `test` value of every plan is `0`. |
| 493 | `              for procs in tree.values()))` | The loop of the test runs over all steps and sessions. So a plan file shows which random order it belongs to, and no test plan with shortened durations is among the real plans. |
| 494 | `    check("plan headers: the seeds of the steps and sessions differ",` | Starts a check: the seeds of the steps and sessions differ. |
| 495 | `          len({procs[0]["head"]["seed"] for procs in tree.values()}) == 9)` | The test: the set of the seeds of all steps and sessions has 9 members, one per step and session. Equal seeds would give two steps the same random choices. |
| 496 | `    check("plan headers: kernel and size name the target of every trial",` | Starts a check: the header pairs `kernel` and `size` name the target of every trial. |
| 497 | `          all(all(t["tgt"].split("@")[0] == p["head"]["kernel"] and nbytes(t["tgt"].split("@")[1]) == int(p["head"]["size"])` | The test: for each trial, the kernel of the target is the header value `kernel`, and the size of the target in bytes is the header value `size`. |
| 498 | `                  and int(p["head"]["size"]) == p["bytes"] for t in p["trials"])` | Continues the test: the header value `size` is also the buffer size of the process. |
| 499 | `              for procs in tree.values() for p in procs))` | The loops of the test run over every process of every step and session. This matters: the runner copies the header pairs into its output, so they must describe what the process really runs. |
| 500 | `    check("cond labels are key=value pairs that agree with the trial (kernel, size, counter mode)",` | Starts a check: every condition label agrees with its trial. |
| 501 | `          all(dict(x.split("=") for x in t["cond"].split("\|")).get("count", "closed") == t["count"]` | The test, first half: the label is split at the vertical bars into pairs `key=value`. Its `count` value, or `closed` when the label has none, is the counter mode of the trial. |
| 502 | `              and "K=%s\|S=%s" % tuple(t["tgt"].split("@")) == "\|".join(t["cond"].split("\|")[:2])` | Second half: the first two pairs of the label are `K=` with the kernel of the target and `S=` with its size. |
| 503 | `              for procs in tree.values() for p in procs for t in p["trials"]))` | The loops run over every trial of every process. A label that names another kernel, size or counter mode than the trial would put a measurement under a wrong name. |
| 505 | `    def evict_agrees(p, step):` | Starts the inner function `evict_agrees`. It tests that the evict option of a process agrees with its labels. |
| 506 | `        m = re.search(r" --evict-mb (\d+)", p["extra"])` | Searches the added options for the text `--evict-mb` with a blank before it and a number after it. The group of the pattern holds the digits of the number. |
| 507 | `        mb = m.group(1) if m else "0"` | `mb`: that number as text, or `0` when the process has no such option. |
| 508 | `        labels = {dict(x.split("=") for x in t["cond"].split("\|")).get("evict") for t in p["trials"]}` | `labels`: the set of the `evict` values in the condition labels of all trials of the process. A label without an `evict` pair gives `None`. |
| 509 | `        if step in ("ZD", "ZC"):` | The steps `ZD` and `ZC`, which have evict conditions. |
| 510 | `            return labels == {mb} and p["head"].get("econd") == "E" + mb` | For these steps: every label names exactly the MiB of the option, and the header pair `econd` is `E` followed by that number. |
| 511 | `        return labels == {None} and "econd" not in p["head"] and (mb == "0" or step == "ZA")` | For every other step: no label has an `evict` pair, the header has no `econd` pair, and the process has no evict option. Only the acceptance step `ZA` may have the option without a label. |
| 513 | `    check("the evict option in args agrees with the cond label and the header (ZD, ZC); no other step has the label, "` | Starts a check: the evict option in the `args` column agrees with the condition label and with the header. |
| 514 | `          "and only ZA has the option without it",` | Continues the name of the check. |
| 515 | `          all(evict_agrees(p, st) for (st, _), procs in tree.items() for p in procs))` | The test: `evict_agrees` is true for every process of every step and session. A process whose label says "no evict" while its option says "evict" would count as the wrong condition. |
| 516 | `    m = copy.deepcopy(tree["ZD", 1][0])` | `m`: an independent copy of the first process of `ZD` in session 1. |
| 517 | `    m["extra"] = "" if m["extra"] else " --evict-mb 512"` | Changes its option to the opposite: an evict process loses the option, and a process without it gets `--evict-mb 512`. Its labels stay as they are. |
| 518 | `    check("that rule rejects a process whose option differs from its label", not evict_agrees(m, "ZD"))` | Check: `evict_agrees` rejects this process. So the check of lines 513 to 515 can fail. |
| 519 | `    check("no trial of round 4 has a previous activity, a predecessor or bins",` | Starts a check: no trial of round 4 has a previous activity, a predecessor or bins. |
| 520 | `          all(t["prev"] == "-" and t["pred"] == "-" and t["bins"] == 0` | The test: for every trial the previous activity and the predecessor are `-`, and `bins` is 0. |
| 521 | `              for procs in tree.values() for p in procs for t in p["trials"]))` | The loops run over every trial of every process of every step and session. |
| 522 | `    check("every kernel of the schedules is one of asmread, read, oldread, read_nop64, read_nop96, read_nop128",` | Starts a check: the schedules use exactly the 6 kernels of round 4. |
| 523 | `          {p["head"]["kernel"] for procs in tree.values() for p in procs} == set(["asmread", "read", "oldread"] + NEW_KERNELS))` | The test: the set of the `kernel` values of all plan headers is `asmread`, `read`, `oldread` and the three new kernels. So no step uses a kernel that the task does not name, and each of the 6 is used. |
| 525 | `    # CPU order of the sessions.` | Comment: the next checks test the CPU order of the sessions. |
| 526 | `    for (step, s), procs in sorted(tree.items()):` | Starts a loop over all steps and sessions, in sorted order. |
| 527 | `        if step == "ZA":` | Tests for the acceptance step `ZA`, which uses CPU 2 only. |
| 528 | `            continue` | Skips it. |
| 529 | `        check("%s session %d: CPU order %d then %d" % ((step, s) + cpus_of(s)), cpu_blocks(procs, *cpus_of(s)))` | Check, per step and session: the CPUs of the schedule alternate in the order of that session, 2 and then 41 in session 1, 41 and then 2 in session 2. The design asks that the second session reverses the order of the worker CPUs. |
| 530 | `    check("CPU order rule rejects session 1 read as session 2", not cpu_blocks(tree["ZM", 1], 41, 2))` | Check: the rule rejects the session 1 schedule of `ZM` when it is tested with the CPU order of session 2. So the check of line 529 can fail. |
| 531 | `    check("session 2 is not session 1 with the CPUs exchanged (own random order)",` | Starts a check: the schedule of session 2 is not the schedule of session 1 with the two CPUs exchanged. |
| 532 | `          all(untagged(tree[st, 1]) != untagged(tree[st, 2]) for st in ("ZD", "ZC", "ZN", "ZM")))` | The test: for each of the steps `ZD`, `ZC`, `ZN` and `ZM`, the list of the tags without CPU numbers differs between the two sessions. This proves that session 2 has a random order of its own. |

### `schedule_checks`: step `ZD` (lines 534 to 574)

| Line | Source | Explanation |
|---:|---|---|
| 534 | `    # ZD.` | Comment: the checks of step `ZD` start here. |
| 535 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 536 | `        d = zd_rules(tree["ZD", s], cpus_of(s))` | `d`: the defects that `zd_rules` finds in the schedule of this session, tested with the CPU order of this session. |
| 537 | `        check("ZD session %d: S2-style trials; asmread, read, oldread at 4M, 8M, 16M with E0 (no option) and E512 "` | Starts a check per session: the schedule of `ZD` obeys all its rules. The name lists them: trials of the `S2` form, the three kernels at the three sizes with `E0` (no option) and `E512` (`--evict-mb 512`). |
| 538 | `              "(--evict-mb 512); per size and CPU each (kernel, condition) cell once at each position and each ordered pair of "` | Continues the name: per size and CPU each cell stands once at each position, and each ordered pair of cells stands once as neighbours. |
| 539 | `              "cells once as neighbours; order: replicate set, size, CPU" % s, not d, d[:3])` | Ends the name with the nesting of the order. The test: the list of defects is empty. This proves that the order of the real schedule is a Williams square per size and CPU. So no cell is favoured by its place in the run order or by the process before it. |
| 540 | `    check("ZD: 6 processes per kernel, size, condition and CPU (108 cells)",` | Starts a check: each combination of kernel, size, condition and CPU has 6 processes. There are 36 such combinations: 3 kernels times 3 sizes times 2 conditions times 2 CPUs. The name of the check says 108 cells. That number does not fit the test of lines 541 to 542. |
| 541 | `          collections.Counter((p["head"]["kernel"], p["bytes"], p["head"]["econd"], p["cpu"]) for p in tree["ZD", 1])` | The test, first half: a count of the processes of session 1 per combination of kernel, buffer size, evict condition and CPU. |
| 542 | `          == {(k, nbytes(s), e, c): 6 for k in ZD_KERNELS for s in ZD_SIZES for e in ECOND for c in (2, 41)})` | Second half: the count is equal to a dictionary that gives exactly 6 for each of the 36 combinations. So every cell has its 6 replicates, and no other combination exists. |
| 543 | `    m = copy.deepcopy(tree["ZD", 1])` | `m`: an independent copy of the `ZD` schedule of session 1, for a damaged variant. |
| 544 | `    for i in range(0, 216, 6):                       # every set in the order of ZD_CELLS` | Starts a loop over the 36 groups of 6 processes. By the comment every set gets the cells in the order of `ZD_CELLS`. |
| 545 | `        for p, (k, e) in zip(m[i:i + 6], ZD_CELLS):` | Starts a loop that pairs the 6 processes of a group with the 6 cells in their fixed order. |
| 546 | `            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]` | `s`: the size text from the tag. `ms`: the window length of the first trial. |
| 547 | `            p["head"].update(kernel=k, econd=e)` | Writes the kernel and the evict condition of the cell into the header of the process. |
| 548 | `            p["extra"] = ECOND[e][1]` | Sets the added option to the one of that condition. |
| 549 | `            p["tag"] = "r%s-%s-cpu%d-%s-%s" % (p["head"]["rep_set"], s, p["cpu"], k, e)` | Builds the tag again for the new cell. |
| 550 | `            for t in p["trials"]:` | Starts a loop over the trials of the process. |
| 551 | `                t.update(cond="K=%s\|S=%s\|evict=%d" % (k, s, ECOND[e][0]), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))` | Rewrites the label, the prefix and the target of the trial for the new cell. So each process stays valid by itself, and only the order of the cells is wrong. |
| 552 | `    d = zd_rules(m, (2, 41))` | `d`: the defects that `zd_rules` finds in this variant. |
| 553 | `    check("ZD rules reject a schedule in which every set has one fixed cell order",` | Starts a check: the rules reject a schedule in which every set has one fixed cell order. |
| 554 | `          any("at each position" in x for x in d) and any("neighbours" in x for x in d), d[:3])` | The test: one defect names the positions and one names the neighbours. This proves that both balance rules can fail. A generator that wrote the same cell order in every set would not pass. |
| 555 | `    m = copy.deepcopy(tree["ZD", 1])` | A new copy of the schedule. |
| 556 | `    m[5], m[6] = m[6], m[5]` | Exchanges the processes 5 and 6. They are the last process of the first CPU and the first process of the second CPU in the first size group. |
| 557 | `    check("ZD rules reject CPUs that alternate inside a size", bool(zd_rules(m, (2, 41))))` | Check: the rules reject this variant. So they notice CPUs that alternate inside a size. |
| 558 | `    m = copy.deepcopy(tree["ZD", 1])` | A new copy of the schedule. |
| 559 | `    m[5]["trials"][0]["pfx"] = "asmread@1M:1200" if m[5]["head"]["kernel"] != "asmread" else "read@1M:1200"` | Gives the first trial of process 5 a prefix of another kernel at 1 MiB: `asmread`, or `read` when the process itself runs `asmread`. |
| 560 | `    check("ZD rules reject a prefix of another kernel or size", bool(zd_rules(m, (2, 41))))` | Check: the rules reject this variant. So they notice a prefix that is not the target kernel at the target size. The prefix prepares the core with the kernel that is measured, so another prefix would change the test. |
| 561 | `    m = copy.deepcopy(tree["ZD", 1])` | A new copy of the schedule. |
| 562 | `    p = [x for x in m if x["head"]["econd"] == "E512"][0]` | `p`: the first process whose header names the condition `E512`. |
| 563 | `    p["extra"] = ""` | Removes its option. |
| 564 | `    check("ZD rules reject an E512 process without --evict-mb 512", bool(zd_rules(m, (2, 41))))` | Check: the rules reject an `E512` process without `--evict-mb 512`. Such a process would run without the evict step and still be named as an evict run. |
| 565 | `    m = copy.deepcopy(tree["ZD", 1])` | A new copy of the schedule. |
| 566 | `    p = [x for x in m if x["head"]["econd"] == "E0"][0]` | `p`: the first process whose header names the condition `E0`. |
| 567 | `    p["extra"] = " --evict-mb 512"` | Gives it the option `--evict-mb 512`. |
| 568 | `    check("ZD rules reject an E0 process with --evict-mb 512", bool(zd_rules(m, (2, 41))))` | Check: the rules reject an `E0` process with the option. Such a process would run the evict step and be named as a run without it. |
| 569 | `    m = copy.deepcopy(tree["ZD", 1])` | A new copy of the schedule. |
| 570 | `    p = [x for x in m if x["head"]["econd"] == "E512"][0]` | `p`: the first process of the condition `E512`. |
| 571 | `    p["extra"] = " --evict-mb 256"` | Changes its option to `--evict-mb 256`. |
| 572 | `    check("ZD rules reject another size of the evict buffer", bool(zd_rules(m, (2, 41))))` | Check: the rules reject another size of the evict buffer. |
| 573 | `    check("ZD rules reject the session 1 schedule under the session 2 CPU order", bool(zd_rules(tree["ZD", 1], (41, 2))))` | Check: the rules reject the unchanged session 1 schedule when it is tested with the CPU order of session 2. So the CPU order is really tested. |

### `schedule_checks`: steps `ZN` and `ZC`, and the event list (lines 575 to 628)

| Line | Source | Explanation |
|---:|---|---|
| 575 | `    # ZN.` | Comment: the checks of step `ZN` start here. |
| 576 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 577 | `        d = zn_rules(tree["ZN", s], cpus_of(s))` | `d`: the defects that `zn_rules` finds in the schedule of this session. |
| 578 | `        check("ZN session %d: S2-style trials, header keys as S2, no option; read_nop64, read_nop96, read_nop128 at 32K, 1M, 8M, "` | Starts a check per session: the schedule of `ZN` obeys all its rules. The name lists them: trials of the `S2` form, the header keys of `S2`, no option, the three slow kernels at the four sizes. |
| 579 | `              "16M; per size and CPU each kernel twice at each position and each ordered pair of kernels twice as neighbours; "` | Continues the name: per size and CPU each kernel stands twice at each position, and each ordered pair of kernels stands twice as neighbours. |
| 580 | `              "order: replicate set, size, CPU" % s, not d, d[:3])` | Ends the name with the nesting of the order. The test: the list of defects is empty. So in the real schedule no slow kernel is favoured by its place in a set or by the kernel that ran before it. |
| 581 | `    check("ZN: 6 processes per kernel, size and CPU (24 cells)",` | Starts a check: each combination of kernel, size and CPU has 6 processes. There are 24 such combinations. |
| 582 | `          collections.Counter((p["head"]["kernel"], p["bytes"], p["cpu"]) for p in tree["ZN", 1])` | The test, first half: a count of the processes of session 1 per kernel, buffer size and CPU. |
| 583 | `          == {(k, nbytes(s), c): 6 for k in ZN_KERNELS for s in ZN_SIZES for c in (2, 41)})` | Second half: the count is equal to a dictionary that gives exactly 6 for each of the 24 combinations. |
| 584 | `    m = copy.deepcopy(tree["ZN", 1])` | `m`: an independent copy of the `ZN` schedule of session 1. |
| 585 | `    for i in range(0, 144, 3):` | Starts a loop over the 48 groups of 3 processes. |
| 586 | `        for p, k in zip(m[i:i + 3], ZN_KERNELS):` | Starts a loop that pairs the 3 processes of a group with the 3 kernels in their fixed order. |
| 587 | `            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]` | `s`: the size text from the tag. `ms`: the window length of the first trial. |
| 588 | `            p["head"]["kernel"] = k` | Writes the kernel into the header of the process. |
| 589 | `            for t in p["trials"]:` | Starts a loop over the trials of the process. |
| 590 | `                t.update(cond="K=%s\|S=%s" % (k, s), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))` | Rewrites the label, the prefix and the target of the trial for that kernel. So each process stays valid by itself, and only the order is wrong. |
| 591 | `    d = zn_rules(m, (2, 41))` | `d`: the defects that `zn_rules` finds in this variant. |
| 592 | `    check("ZN rules reject a schedule in which every set has one fixed kernel order",` | Starts a check: the rules reject a schedule in which every set has one fixed kernel order. |
| 593 | `          any("at each position" in x for x in d) and any("neighbours" in x for x in d), d[:3])` | The test: one defect names the positions and one names the neighbours. So both balance rules of `ZN` can fail. |
| 594 | `    m = copy.deepcopy(tree["ZN", 1])` | A new copy of the schedule. |
| 595 | `    m[2], m[3] = m[3], m[2]` | Exchanges the processes 2 and 3: the last process of the first CPU and the first process of the second CPU in the first size group. |
| 596 | `    check("ZN rules reject CPUs that alternate inside a size", bool(zn_rules(m, (2, 41))))` | Check: the rules reject CPUs that alternate inside a size. |
| 597 | `    m = copy.deepcopy(tree["ZN", 1])` | A new copy of the schedule. |
| 598 | `    m[7]["extra"] = " --evict-mb 512"` | Gives process 7 the option `--evict-mb 512`. |
| 599 | `    check("ZN rules reject a process with an option", bool(zn_rules(m, (2, 41))))` | Check: the rules reject a `ZN` process with an option. `ZN` must run without the evict step. |
| 600 | `    check("ZN rules reject the session 1 schedule under the session 2 CPU order", bool(zn_rules(tree["ZN", 1], (41, 2))))` | Check: the rules reject the session 1 schedule when it is tested with the CPU order of session 2. |
| 602 | `    # ZC.` | Comment: the checks of step `ZC` start here. |
| 603 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 604 | `        d = zc_rules(tree["ZC", s], cpus_of(s))` | `d`: the defects that `zc_rules` finds in the schedule of this session. |
| 605 | `        check("ZC session %d: asmread and oldread at 8M and 16M with E0 and E512 once per replicate block and CPU, "` | Starts a check per session: the schedule of `ZC` obeys all its rules. The name lists them: `asmread` and `oldread` at 8 and 16 MiB with `E0` and `E512`, once per replicate block and CPU. |
| 606 | `              "20 windows of 300 ms, count read, --pmu-type 11 and the 6 events in args" % s, not d, d[:3])` | Ends the name: 20 windows of 300 ms, the counter mode `read`, `--pmu-type 11` and the 6 events in the `args` column. The test: the list of defects is empty. |
| 607 | `    check("ZC: 2 processes per kernel, size, condition and CPU (16 cells)",` | Starts a check: each combination of kernel, size, condition and CPU has 2 processes. There are 16 such combinations. |
| 608 | `          collections.Counter((p["head"]["kernel"], p["bytes"], p["head"]["econd"], p["cpu"]) for p in tree["ZC", 1])` | The test, first half: a count of the processes of session 1 per kernel, buffer size, evict condition and CPU. |
| 609 | `          == {(k, nbytes(s), e, c): 2 for k in ZC_KERNELS for s in ZC_SIZES for e in ECOND for c in (2, 41)})` | Second half: the count is equal to a dictionary that gives exactly 2 for each of the 16 combinations. |
| 610 | `    m = copy.deepcopy(tree["ZC", 1])` | `m`: an independent copy of the `ZC` schedule of session 1. |
| 611 | `    m[0]["trials"][0]["count"] = "closed"` | Changes the counter mode of the first trial of the first process to `closed`. |
| 612 | `    check("ZC rules reject a trial with count closed", bool(zc_rules(m, (2, 41))))` | Check: the rules reject a trial with closed counters. Such a process would give no counter values. |
| 613 | `    m = copy.deepcopy(tree["ZC", 1])` | A new copy of the schedule. |
| 614 | `    m[3]["extra"] = m[3]["extra"].replace("0x4009", "0x4008")` | Changes one event code in the options of process 3, from `0x4009` to `0x4008`. |
| 615 | `    check("ZC rules reject another event code", bool(zc_rules(m, (2, 41))))` | Check: the rules reject another event code. A wrong code would count another event under the same name. |
| 616 | `    m = copy.deepcopy(tree["ZC", 1])` | A new copy of the schedule. |
| 617 | `    p = [x for x in m if x["head"]["econd"] == "E512"][0]` | `p`: the first process of the condition `E512`. |
| 618 | `    p["extra"] = p["extra"].replace(" --evict-mb 512", "")` | Removes `--evict-mb 512` from its options. |
| 619 | `    check("ZC rules reject an E512 process without --evict-mb 512", bool(zc_rules(m, (2, 41))))` | Check: the rules reject an `E512` process without the evict option. |
| 620 | `    m = copy.deepcopy(tree["ZC", 1])` | A new copy of the schedule. |
| 621 | `    m[0], m[8] = m[8], m[0]` | Exchanges process 0 with process 8, the first process of the next block. |
| 622 | `    check("ZC rules reject two processes exchanged between blocks", bool(zc_rules(m, (2, 41))))` | Check: the rules reject two processes that were exchanged between blocks. Each block must hold every cell once on its own CPU. |
| 623 | `    check("ZC rules reject the session 1 schedule under the session 2 CPU order", bool(zc_rules(tree["ZC", 1], (41, 2))))` | Check: the rules reject the session 1 schedule when it is tested with the CPU order of session 2. |
| 624 | `    check("the event set: 6 events with l2d_cache_wb=0x18 and bus_access=0x19, names below 32 characters, 6 different names and codes",` | Starts a check of the expected event list `EVENTS` itself. The name: 6 events with `l2d_cache_wb=0x18` and `bus_access=0x19`, names of fewer than 32 characters, 6 different names and 6 different codes. |
| 625 | `          len(EVENTS.split(",")) == 6 and all(re.match(r"^[a-z0-9_]{1,31}=0x[0-9a-f]+$", e) for e in EVENTS.split(","))` | The test, first half: the list has 6 entries. Each matches the pattern: a name of 1 to 31 lower-case letters, digits or `_`, an equals sign, `0x` and hexadecimal digits in lower case. |
| 626 | `          and len({e.split("=")[0] for e in EVENTS.split(",")}) == 6 and len({int(e.split("=")[1], 16) for e in EVENTS.split(",")}) == 6` | Continues the test: the 6 names differ, and the 6 codes differ as numbers. |
| 627 | `          and "l2d_cache_wb=0x18" in EVENTS.split(",") and "bus_access=0x19" in EVENTS.split(","))` | Ends the test: the two events `l2d_cache_wb=0x18` and `bus_access=0x19` are in the list. The limit of the name length matters: the runner keeps an event name in 32 bytes and refuses a longer one. |

### `schedule_checks`: steps `ZM` and `ZA`, `.bin` files, no `.watch` file (lines 629 to 673)

| Line | Source | Explanation |
|---:|---|---|
| 629 | `    # ZM.` | Comment: the checks of step `ZM` start here. |
| 630 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 631 | `        d = zm_rules(tree["ZM", s], cpus_of(s))` | `d`: the defects that `zm_rules` finds in the schedule of this session. |
| 632 | `        check("ZM session %d: asmread at 8M, 300 windows of 100 ms, count closed; --rec-pad 0, 8, 16, 24, 32, 40, 48, 56, 64, 72 "` | Starts a check per session: the schedule of `ZM` obeys all its rules. The name lists them: `asmread` at 8 MiB, 300 windows of 100 ms, counters closed, and the 10 values of `--rec-pad`. |
| 633 | `              "once per replicate block and CPU" % s, not d, d[:3])` | Ends the name: each pad once per replicate block and CPU. The test: the list of defects is empty. |
| 634 | `    check("ZM: 2 processes per pad and CPU (20 cells)",` | Starts a check: each combination of pad and CPU has 2 processes. There are 20 such combinations. |
| 635 | `          collections.Counter((p["head"]["pcond"], p["cpu"]) for p in tree["ZM", 1])` | The test, first half: a count of the processes of session 1 per pad label and CPU. |
| 636 | `          == {("P%d" % x, c): 2 for x in ZM_PADS for c in (2, 41)})` | Second half: the count is equal to a dictionary that gives exactly 2 for each of the 20 combinations. |
| 637 | `    m = copy.deepcopy(tree["ZM", 1])` | `m`: an independent copy of the `ZM` schedule of session 1. |
| 638 | `    [p for p in m if p["head"]["pcond"] == "P8"][0]["extra"] = " --rec-pad 80"` | Gives the first process with the label `P8` the option `--rec-pad 80`. |
| 639 | `    check("ZM rules reject a pad that differs from its label", bool(zm_rules(m, (2, 41))))` | Check: the rules reject a pad that differs from its label. Such a process would be analysed under a pad that it did not run with. |
| 640 | `    m = copy.deepcopy(tree["ZM", 1])` | A new copy of the schedule. |
| 641 | `    m[0]["trials"][0]["nwin"] += 1` | Adds one window to the trial of the first process. |
| 642 | `    check("ZM rules reject a trial with one more window", bool(zm_rules(m, (2, 41))))` | Check: the rules reject a trial with one more window. |
| 643 | `    m = copy.deepcopy(tree["ZM", 1])` | A new copy of the schedule. |
| 644 | `    m[0], m[10] = m[10], m[0]` | Exchanges process 0 with process 10, the first process of the next block. |
| 645 | `    check("ZM rules reject two processes exchanged between blocks", bool(zm_rules(m, (2, 41))))` | Check: the rules reject two processes that were exchanged between blocks. |
| 646 | `    fixed = sorted(tree["ZM", 1], key=lambda p: (int(p["head"]["rep_set"]), p["cpu"], int(p["head"]["pcond"][1:])))` | `fixed`: the `ZM` schedule of session 1 sorted by replicate, CPU and pad number. Every block then has the pads in the same rising order. |
| 647 | `    check("ZM rules reject a fixed pad order in every block",` | Starts a check: the rules reject a fixed pad order in every block. |
| 648 | `          zm_rules(fixed, (2, 41)) == ["the pad order is the same in every block"], zm_rules(fixed, (2, 41))[:3])` | The test: the list of defects is exactly one entry, the one about the same pad order in every block. So the rule that asks for a shuffle can fail, and this variant breaks no other rule. |
| 649 | `    check("ZM rules reject the session 1 schedule under the session 2 CPU order", bool(zm_rules(tree["ZM", 1], (41, 2))))` | Check: the rules reject the session 1 schedule when it is tested with the CPU order of session 2. |
| 651 | `    # ZA.` | Comment: the checks of the acceptance step `ZA` start here. |
| 652 | `    d = za_rules(tree["ZA", 1])` | `d`: the defects that `za_rules` finds in the `ZA` schedule of session 1. |
| 653 | `    check("ZA: CPU 2 only, 6 processes with --trace in the fixed order (asmread plain, asmread and oldread with --evict-mb 512, "` | Starts a check: the schedule of `ZA` obeys its rules. The name lists them: CPU 2 only, 6 processes with `--trace` in the fixed order, all at 8 MiB. |
| 654 | `          "read_nop64, read_nop96, read_nop128, all at 8M), each one trial: prefix 400 ms, 3 windows of 300 ms, count closed, bins 0",` | Continues the name: each process has one trial with a prefix of 400 ms and 3 windows of 300 ms, counters closed, bins 0. |
| 655 | `          not d, d[:3])` | The test: the list of defects is empty. The acceptance step tries each new feature of the runner once: the evict step with two kernels, and the three new kernels. |
| 656 | `    m = copy.deepcopy(tree["ZA", 1])` | `m`: an independent copy of the `ZA` schedule. |
| 657 | `    m[4]["extra"] = ""` | Removes all added options of process 4. |
| 658 | `    check("ZA rules reject a process without --trace", bool(za_rules(m)))` | Check: the rules reject a process without `--trace`. Without the trace log the acceptance run could not show what the runner does around its timed parts. |
| 659 | `    m = copy.deepcopy(tree["ZA", 1])` | A new copy of the schedule. |
| 660 | `    m[1]["extra"] = " --trace"` | Leaves process 1, the evict process, with `--trace` only. |
| 661 | `    check("ZA rules reject the evict process without --evict-mb 512", bool(za_rules(m)))` | Check: the rules reject the evict process without `--evict-mb 512`. |
| 662 | `    check("ZA: session 2 has no schedule, no plan folder and no binary file",` | Starts a check: session 2 has no schedule, no plan folder and no `.bin` file of `ZA`. |
| 663 | `          not [f for f in os.listdir(os.path.join(a, "s2")) if f.startswith("ZA")])` | The test: no name in the folder `s2` starts with `ZA`. So the run script cannot run the acceptance step in session 2: it ends with status 2 for a missing schedule. |
| 665 | `    # Binary files and sampler markers.` | Comment: the next checks test the `.bin` files and the marker files of the host sampler. |
| 666 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 667 | `        sdir = os.path.join(a, "s%d" % s)` | `sdir`: the folder of the session in the generated folder. |
| 668 | `        bins = {f[:-4]: open(os.path.join(sdir, f)).read() for f in os.listdir(sdir) if f.endswith(".bin")}` | `bins`: a dictionary from the step name to the content of its `.bin` file, for every `.bin` file of the session folder. |
| 669 | `        check("session %d: one .bin file per step; every step names bwx11; one word and a newline" % s,` | Starts a check per session: there is one `.bin` file per step, and each holds the one word `bwx11` and a newline. |
| 670 | `              bins == {st: "bwx11\n" for st in TABLE if (st, s) in tree}, bins)` | The test: the dictionary is equal to the expected one, which has the text `bwx11` with a newline for every step of this session. The run script reads this word to choose the binary. Another word would start another runner, or stop the run with status 2. |
| 671 | `        check("session %d: no .watch file (no step of round 4 runs with the host sampler)" % s,` | Starts a check per session: the session folder has no `.watch` file. |
| 672 | `              not [f for f in os.listdir(sdir) if f.endswith(".watch")])` | The test: no name in the session folder ends with `.watch`. So the run script starts no host sampler for these steps. |

### `schedule_checks`: same seed, other seed, `MANIFEST.txt`, saved folder, test divisor (lines 674 to 724)

| Line | Source | Explanation |
|---:|---|---|
| 674 | `    # Determinism.` | Comment: the next checks test that the output is fully fixed by the options. |
| 675 | `    gen(b)` | Runs the generator a second time with the default options, into the folder `b`. |
| 676 | `    r3 = gen(c, "--seed", "7")` | Runs it a third time with `--seed 7`, into the folder `c`. |
| 677 | `    ta, tb, tc = tree_bytes(a), tree_bytes(b), tree_bytes(c)` | `ta`, `tb`, `tc`: the files of the three folders, each as a dictionary from the path to the bytes. |
| 678 | `    nfiles = 1 + sum(TABLE[s][0] + 2 for s in TABLE) + sum(TABLE[s][0] + 2 for s in TABLE if s != "ZA")` | `nfiles`: the expected number of files: 1 for `MANIFEST.txt`, plus for each step of session 1 its plan files and 2 more (the schedule and the `.bin` file), plus the same for each step of session 2 other than `ZA`. |
| 679 | `    check("two runs with one base seed give the same bytes (%d files)" % nfiles, ta == tb and len(ta) == nfiles == 889, len(ta))` | Check: two runs with the same base seed give the same files with the same bytes, and the number of files is 889. This proves that a schedule can be made again from its seed. The order that ran can then be checked later. |
| 680 | `    check("another base seed gives the same file names and other bytes",` | Starts a check: another base seed gives the same file names and other bytes. |
| 681 | `          r3.returncode == 0 and sorted(ta) == sorted(tc) and ta != tc` | The test, first half: the third run ended with status 0, the two folders have the same file names, and their contents differ. |
| 682 | `          and all(ta["s%d/%s.tsv" % (n, s)] != tc["s%d/%s.tsv" % (n, s)] for s in ("ZD", "ZC", "ZN", "ZM") for n in (1, 2)))` | Second half: the schedule files of `ZD`, `ZC`, `ZN` and `ZM` differ in both sessions. This proves that the seed really drives the order of each shuffled step. |
| 683 | `    check("the base seed and the seed of every step and session are saved in MANIFEST.txt",` | Starts a check: the base seed and the seed of every step and session are saved in `MANIFEST.txt`. |
| 684 | `          b"base_seed=20261115\ntest_divisor=1\n" in ta["MANIFEST.txt"] and b"base_seed=7\n" in tc["MANIFEST.txt"]` | The test, first half: the manifest of the default run holds the lines `base_seed=20261115` and `test_divisor=1`, and the manifest of the third run holds `base_seed=7`. |
| 685 | `          and all(("seed %s s%d %s\n" % (st, s, procs[0]["head"]["seed"])).encode() in ta["MANIFEST.txt"]` | Second half: for each step and session the manifest holds a line `seed`, the step, the session and the seed that the plan headers carry. |
| 686 | `                  for (st, s), procs in tree.items()))` | The loop of that test runs over all steps and sessions. So the record of the seeds agrees with the plan files. |
| 687 | `    check("MANIFEST.txt names the binary of every step and session, and states that no step has a sampler marker",` | Starts a check: `MANIFEST.txt` names the binary of every step and session, and it states that no step has a marker file for the host sampler. |
| 688 | `          all(("bin %s s%d bwx11\n" % (st, s)).encode() in ta["MANIFEST.txt"] for (st, s) in tree)` | The test, first part: for each step and session the manifest holds a line `bin`, the step, the session and the word `bwx11`. |
| 689 | `          and ta["MANIFEST.txt"].count(b"\nbin ") == 9 and ta["MANIFEST.txt"].endswith(b"\nwatch none\n"), ta["MANIFEST.txt"][-200:])` | Second part: the manifest has exactly 9 lines that start with `bin`, and it ends with the line `watch none`. |
| 690 | `    tree7, errors7 = load(c)` | `tree7`, `errors7`: the folder of the third run, read and tested with `load`. |
| 691 | `    check("another base seed keeps the rules (grammar, ZD, ZC, ZN, ZM, ZA)",` | Starts a check: another base seed keeps the rules. |
| 692 | `          not errors7 and not zd_rules(tree7["ZD", 2], (41, 2)) and not zn_rules(tree7["ZN", 1], (2, 41))` | The test: no format defect, and no defect from `zd_rules` for session 2 or from `zn_rules` for session 1. |
| 693 | `          and not zm_rules(tree7["ZM", 2], (41, 2)) and not zc_rules(tree7["ZC", 1], (2, 41)) and not za_rules(tree7["ZA", 1]))` | Continues the test: no defect from `zm_rules` for session 2, `zc_rules` for session 1 and `za_rules`. This proves that the balance does not depend on the default seed. The construction gives it for another seed too. |
| 694 | `    saved = os.path.join(Z, "sched11")` | `saved`: the folder `sched11` beside this file. It holds the schedules that are copied to CRB. |
| 695 | `    check("the saved sched11/ beside the scripts is the output of the default base seed",` | Starts a check: the saved folder is the output of the generator with the default base seed. Note for the later step `ZS`: the program `schedule_zs.py` writes its files into the same folder. With those files the folder holds more than the generator writes, and this check then fails. |
| 696 | `          os.path.isdir(saved) and tree_bytes(saved) == ta)` | The test: the saved folder exists, and its files are equal to the files that the generator wrote now, name by name and byte by byte. So the schedules that will run are the ones that this test examined. |
| 697 | `    src = open(SCHED).read()` | `src`: the text of the generator. |
| 698 | `    check("schedule11.py imports the standard library only (no file of an earlier round)",` | Starts a check: the generator imports modules of the Python standard library only, and no file of an earlier round. |
| 699 | `          sorted(set(re.findall(r"^(?:import\|from) (\w+)", src, re.M))) == ["argparse", "hashlib", "itertools", "os", "random", "shutil", "sys"]` | The test, first half: the sorted set of the imported module names is exactly this list of 7. The pattern finds, at the start of a line, the word `import` or `from`, a blank, and then a group with the module name. `re.M` lets `^` match at every line start. |
| 700 | `          and "sys.path" not in src, sorted(set(re.findall(r"^(?:import\|from) (\w+)", src, re.M))))` | Second half: the text of the generator does not hold `sys.path`. So it does not add a folder to the search path of Python to load a file from there. The generator then needs no other file. It also runs where the folders of the earlier rounds are missing. |
| 701 | `    check("hostwatch.py in this folder is the file of round 3, byte for byte",` | Starts a check: the file `hostwatch.py` in this folder is the file of round 3, byte for byte. |
| 702 | `          open(WATCH, "rb").read() == open(os.path.join(Y, "hostwatch.py"), "rb").read())` | The test: the bytes of the two files are equal. So the host sampler that was used before was not changed for round 4. |
| 704 | `    # --test-divisor.` | Comment: the checks of the option `--test-divisor` start here. |
| 705 | `    t = os.path.join(tmp, "t")` | `t`: one more output folder. |
| 706 | `    r6 = gen(t, "--test-divisor", "100")` | Runs the generator with `--test-divisor 100` into `t`. |
| 707 | `    ttree, terr = load(t)` | `ttree`, `terr`: that folder, read and tested with `load`. |
| 708 | `    check("--test-divisor 100: valid plans, test=1, every duration divided by 100, window counts unchanged",` | Starts a check: with the divisor 100 the plans are valid, they carry `test=1`, every duration is divided by 100, and the numbers of windows do not change. |
| 709 | `          r6.returncode == 0 and not terr and sorted(ttree) == sorted(tree)` | The test: the run ended with status 0, there is no format defect, and the steps and sessions are the same as in the real folder. |
| 710 | `          and all(p["head"]["test"] == "1" for pp in ttree.values() for p in pp)` | Continues the test: every plan has `test=1`. |
| 711 | `          and all(sum(proc_ms(p) for p in ttree[k]) * 100 == sum(proc_ms(p) for p in tree[k]) for k in tree)` | Continues the test: for each step and session the nominal work times 100 is the nominal work of the real folder. |
| 712 | `          and all([t_["nwin"] for p in ttree[k] for t_ in p["trials"]] == [t_["nwin"] for p in tree[k] for t_ in p["trials"]]` | Continues the test: the list of the window counts of all trials is the same as in the real folder. |
| 713 | `                  for k in tree)` | The loop of that comparison runs over all steps and sessions. |
| 714 | `          and not zd_rules(ttree["ZD", 1], (2, 41)) and not zn_rules(ttree["ZN", 2], (41, 2))` | Continues the test: the divided folder passes `zd_rules` for session 1 and `zn_rules` for session 2. |
| 715 | `          and not zc_rules(ttree["ZC", 2], (41, 2), 100) and not za_rules(ttree["ZA", 1], 100)` | Continues the test: it passes `zc_rules` for session 2 and `za_rules`, both called with the divisor 100. |
| 716 | `          and not zm_rules(ttree["ZM", 1], (2, 41), 100), terr[:3])` | Ends the test: it passes `zm_rules` for session 1 with the divisor 100. This matters: the later checks run this short folder through the run script and through the stand-in runner. It must be the same schedule in every respect but the durations. |
| 717 | `    check("--test-divisor 100 keeps the order and the args of the processes (only durations and the test mark differ)",` | Starts a check: the divisor keeps the order and the options of the processes. |
| 718 | `          all([(p["tag"], p["args"]) for p in ttree[k]] == [(p["tag"], p["args"]) for p in tree[k]] for k in tree))` | The test: for each step and session the list of the pairs of tag and `args` is the same in the divided folder and in the real folder. So a run of the short folder uses the same command lines in the same order. |
| 719 | `    for div in ("7", "3", "300", "0"):` | Starts a loop over four divisors that must be refused: 7, 3, 300 and 0. |
| 720 | `        check("--test-divisor %s is refused (it does not divide 100 ms, the shortest window)" % div,` | Starts a check per divisor: it is refused. 100 ms, the shortest window, divided by 7, 3 or 300 is not a whole number of ms, and 0 is not a divisor. |
| 721 | `              gen(os.path.join(tmp, "u"), "--test-divisor", div).returncode != 0 and not os.path.exists(os.path.join(tmp, "u")))` | The test: the generator ends with a status other than 0, and the output folder `u` was not created. A divisor that does not divide a window would give windows of another length ratio than the real ones. |
| 722 | `    return a, t` | Returns two folders: the real one (`a`) and the one with the divisor 100 (`t`). The later checks use them. |

### Runs through a stand-in runner: `stand_in_jobs`, `run_job`, `local_cpus`, `build_stand_in` (lines 725 to 795)

| Line | Source | Explanation |
|---:|---|---|
| 725 | `# ---------- plans through a local stand-in binary ----------` | Comment: the functions that put plans through a local stand-in binary start here. |
| 726 | `def stand_in_jobs(d, steps, alt, sessions=(1, 2), only=None):` | Starts the function `stand_in_jobs`. It lists the processes to run through a stand-in. `d`: a folder that holds a copy of the schedule folder. `alt`: the CPU that replaces CPU 41. `only`: an optional set of row numbers. |
| 727 | ``    """Jobs for the plans of `steps` in the tree d/sched11. CPU 41 is rewritten to `alt` in that tree."""`` | Description text: the function returns the jobs for the plans of the given steps in the folder `sched11` of `d`. In that copy CPU 41 is rewritten to `alt`. |
| 728 | `    jobs = []` | `jobs`: the result list, empty at first. |
| 729 | `    for session in sessions:` | Starts a loop over the sessions. |
| 730 | `        sdir = os.path.join(d, "sched11", "s%d" % session)` | `sdir`: the session folder of the copy. |
| 731 | `        for step in steps:` | Starts a loop over the steps. |
| 732 | `            if not os.path.exists(os.path.join(sdir, step + ".tsv")):` | A step without a schedule file in this session. |
| 733 | `                continue` | Skips it. |
| 734 | `            for n, row in enumerate(open(os.path.join(sdir, step + ".tsv")).read().split("\n")[1:-1]):` | Starts a loop over the data rows of the schedule. `n` counts from 0. |
| 735 | `                if only is not None and n not in only:` | When `only` is given and does not hold this row number. |
| 736 | `                    continue` | Skips the row. |
| 737 | `                f = row.split("\t")` | Splits the row at the tabs. |
| 738 | `                args = f[5]` | `args`: the options of the process. |
| 739 | `                plan = os.path.join(sdir, step, f[4])` | `plan`: the path of its plan file. |
| 740 | `                text = open(plan).read()` | `text`: the text of the plan. |
| 741 | `                if f[2] == "41" and alt != 41:` | A process on CPU 41, on a machine where another CPU must be used. |
| 742 | `                    args = args.replace("--cpus 41 ", "--cpus %d " % alt)` | Replaces `--cpus 41` in the options with the other CPU. |
| 743 | `                    with open(plan, "w") as out:` | Opens the plan file of the copy for writing. |
| 744 | `                        out.write(text.replace(" cpu=41 ", " cpu=%d " % alt))` | Writes the plan again with `cpu=41` in its header replaced. The runner refuses a plan whose `cpu` pair differs from `--cpus`, so both must change. |
| 745 | `                trials = [l.split(" ") for l in text.split("\n")[3:-1]]` | `trials`: the trial lines of the plan, each split into its fields. |
| 746 | `                jobs.append((step, session, f[0], args.split(), len(trials), sum(int(t[7]) for t in trials),` | Adds the job. This line: the step, the session, the `idx`, the options as a list, the number of trials, and the sum of the target windows of all trials (field `nwin`). |
| 747 | `                             sum((1 if t[3] != "-" else 0) + (4 if t[4] != "-" else 0) for t in trials),` | Continues the job: the number of other windows that the runner must print: 1 for each previous activity and 4 for each prefix. |
| 748 | `                             sum(int(t[7]) * (int(t[8]) // 10 + 2) for t in trials if t[10] == "1")))` | Ends the job: the number of bin records that the runner must report. Only trials with `bins` equal to 1 count. For each such trial the value is `nwin * (win_ms // 10 + 2)`. |
| 749 | `    return jobs` | Returns the jobs. |
| 752 | `def run_job(binary, d, env, job):` | Starts the function `run_job`. It runs one job through a binary and compares the output with the plan. |
| 753 | `    """None if the binary accepted the plan and printed every planned row, or a tuple that describes the defect."""` | Description text: the result is `None` when the binary accepted the plan and printed every planned row. If not, it is a tuple that describes the defect. |
| 754 | `    step, session, idx, args, ntr, nwin, nother, nbins = job` | Splits the job into its 8 values. |
| 755 | `    try:` | Starts the block whose error is caught. |
| 756 | `        r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True, timeout=600)` | Runs the binary with the options of the job, in the folder `d` and with the environment `env`. The output is kept as text. The run may take at most 600 s. |
| 757 | `    except subprocess.TimeoutExpired:` | The run took longer than 600 s. |
| 758 | `        return (step, session, idx, "timeout")` | Returns a tuple with the word `timeout`. |
| 759 | `    rows = collections.Counter()` | `rows`: a count of the output rows per kind. |
| 760 | `    for l in r.stdout.split("\n"):` | Starts a loop over the output lines. |
| 761 | `        f = l.split(",")` | Splits a line at the commas. The first field is the kind of the row. |
| 762 | `        rows[f[0] if f[0] != "W" else "W." + ("target" if f[2] == "target" else "other")] += 1` | Counts the row under its kind. A `W` row (one window) is counted as `W.target` when its phase field is `target`, and as `W.other` if not. |
| 763 | `    m = dict(l.split(",", 2)[1:] for l in r.stdout.split("\n") if l.startswith("M,") and l.count(",") >= 2)` | `m`: the `M` rows of the output as a dictionary from the key to the value. An `M` row has the form `M,key,value`. |
| 764 | `    ok = r.returncode == 0 and rows["S"] == ntr and rows["E"] == ntr and rows["W.target"] == nwin \` | `ok`, first conditions: exit status 0, one `S` row (start of a trial) and one `E` row (end of a trial) per planned trial, and as many `W` rows of target windows as the plan has windows. |
| 765 | `        and rows["W.other"] == nother and m.get("plan.step") == step and m.get("plan.proc") == idx \` | Continues: the planned number of other windows, and the `M` rows `plan.step` and `plan.proc` name this step and this process. So the runner read the right plan. |
| 766 | `        and m.get("mode") == "trial" and m.get("rec_bins") == str(nbins) and (rows["B"] >= 1) == (nbins > 0)` | Continues: the mode is `trial`, the `M` row `rec_bins` gives the expected number of bin records, and `B` rows exist exactly when bins are planned. |
| 767 | `    if ok and "--events" in args:` | For a process with `--events`. |
| 768 | `        ok = m.get("pmu_type") == "11" and m.get("events", "").count(";") == 5 and rows["C"] + rows["X"] >= 1` | `ok` now needs: the `M` row `pmu_type` is 11, the `M` row `events` holds 6 events (5 semicolons), and at least one `C` row (counter values) or `X` row (a failure that the runner reports) exists. |
| 769 | `    if ok and "--trace" in args:` | For a process with `--trace`. |
| 770 | `        ok = m.get("trace") == "1" and rows["TR"] >= 1` | `ok` now needs: the `M` row `trace` is 1, and at least one `TR` row (one entry of the trace log) exists. |
| 771 | `    if ok and "--rec-pad" in args:` | For a process with `--rec-pad`. |
| 772 | `        ok = m.get("rec_pad") == args[args.index("--rec-pad") + 1]` | `ok` now needs: the `M` row `rec_pad` gives the value of the option. |
| 773 | `    if ok:` | For every process that passed up to here. |
| 774 | `        # The runner records the evict setting of the process in the row M,evict_mb (0 without the option).` | Comment: the runner records the evict setting of the process in the row `M,evict_mb`. The value is 0 without the option. |
| 775 | `        ok = m.get("evict_mb") == (args[args.index("--evict-mb") + 1] if "--evict-mb" in args else "0")` | `ok` now needs: that row gives the value of `--evict-mb`, or `0` when the process has no such option. So the runner really took the option. |
| 776 | `    return None if ok else (step, session, idx, r.returncode, r.stderr[-200:], dict(rows))` | Returns `None` for a good run. If not, it returns the step, the session, the `idx`, the exit status, the last 200 characters of the error output and the row counts. |
| 779 | `def local_cpus():` | Starts the function `local_cpus`. It finds the CPU that stands in for CPU 41 on this machine. |
| 780 | `    allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)` | `allowed`: the CPUs on which this process may run, without those above 119, in sorted order. |
| 781 | `    if not check("this machine allows CPU 0, CPU 2 and one more CPU below 120", 0 in allowed and 2 in allowed and len(allowed) > 2):` | Check: this machine allows CPU 0, CPU 2 and at least one more CPU below 120. The stand-in runs need CPU 2 for the worker and CPU 0 for the controlling thread of the runner. |
| 782 | `        return None` | When the check fails: returns `None`, and the caller runs no stand-in job. |
| 783 | `    return 41 if 41 in allowed else [c for c in allowed if c not in (0, 2)][0]` | Returns 41 when CPU 41 is allowed. If not, it returns the lowest allowed CPU other than 0 and 2. |
| 786 | `def build_stand_in(src, d, word):` | Starts the function `build_stand_in`. It compiles a runner source on this machine. |
| 787 | ``    """Builds `src` as d/<word> with the flags of build8.sh. Returns (path, None) or (None, first line of the compiler output)."""`` | Description text: the function builds `src` as the file `word` in the folder `d`, with the flags of `build8.sh`. It returns the path and `None`, or `None` and the first line of the compiler output. |
| 788 | `    os.makedirs(d)` | Creates the folder `d`. |
| 789 | `    binary = os.path.join(d, word)` | `binary`: the path of the output file. |
| 790 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-o", binary, src], capture_output=True, text=True)` | Runs `gcc` with the flags of `CFLAGS`, the output path and the source. The output of the compiler is kept as text. |
| 791 | `    if r.returncode != 0:` | When the compiler ended with a status other than 0. |
| 792 | `        return None, (r.stdout + r.stderr).strip().split("\n")[0][:200]` | Returns `None` and the first line of the compiler output, cut to 200 characters. |
| 793 | `    return binary, None` | Returns the path of the binary and `None`. |

### `bwx10_checks`: the older runner refuses what is new in round 4 (lines 796 to 823)

| Line | Source | Explanation |
|---:|---|---|
| 796 | `def bwx10_checks(tmp, sched):` | Starts the function `bwx10_checks`. `sched` is the generated folder with the test divisor 100. |
| 797 | `    """The older runner refuses what is new in round 4, so a wrong .bin word cannot run such a process."""` | Description text: the older runner refuses what is new in round 4. So a wrong word in a `.bin` file cannot run such a process with the older binary. |
| 798 | `    binary, why = build_stand_in(os.path.join(Y, "bwx10.c"), os.path.join(tmp, "bwx10"), "bwx10")` | Builds the source `bwx10.c` of round 3 as a stand-in binary `bwx10` in a temporary folder. |
| 799 | `    if not check("stand-in build of bwx10.c of round 3 in a temporary folder (flags of build8.sh)", binary is not None, why):` | Check: the stand-in build worked. The detail of a failure is the first line of the compiler output. |
| 800 | `        return` | Without the binary the rest of the function is left out. |
| 801 | `    d = os.path.dirname(binary)` | `d`: the folder of the stand-in binary. |
| 802 | `    shutil.copytree(sched, os.path.join(d, "sched11"))` | Copies the generated schedule folder to `sched11` in that folder. The plan paths in the `args` column are relative to this place. |
| 803 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment of this test without every variable whose name starts with `BWX_`. So no counter setting reaches the stand-in from outside. |
| 805 | `    def first(step, pred):` | Starts the inner function `first`. It finds the first process of a step that fits a condition. |
| 806 | `        for row in open(os.path.join(d, "sched11", "s1", step + ".tsv")).read().split("\n")[1:-1]:` | Starts a loop over the data rows of the schedule of that step in session 1. |
| 807 | `            f = row.split("\t")` | Splits the row at the tabs. |
| 808 | `            if f[2] == "2" and pred(f):` | The row must be a process on CPU 2, and the condition `pred` must hold for it. |
| 809 | `                return f[5].split()` | Returns the options of that process as a list of words. |
| 811 | `    args = first("ZD", lambda f: "--evict-mb" in f[5] and "asmread" in f[1])` | `args`: the options of the first `ZD` process on CPU 2 that has `--evict-mb` and whose tag names `asmread`. |
| 812 | `    r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True)` | Runs the stand-in `bwx10` with these options, in the folder `d`. |
| 813 | `    check("the old bwx10 refuses the args of a ZD process with --evict-mb 512 (status not 0)",` | Starts a check: the older runner refuses the options of a `ZD` process with `--evict-mb 512`. |
| 814 | `          r.returncode != 0 and "--evict-mb" in args, (r.returncode, r.stderr[-200:]))` | The test: the exit status is not 0, and the options really hold `--evict-mb`. So a step that needs the evict step cannot run by mistake with a runner that does not have it. Such a run would be labelled `E512` without an evict step. |
| 815 | `    args = first("ZD", lambda f: "--evict-mb" not in f[5] and "asmread" in f[1])` | `args`: the options of the first `ZD` process on CPU 2 with `asmread` and without `--evict-mb`. |
| 816 | `    r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True)` | Runs the stand-in `bwx10` with these options. |
| 817 | `    check("the old bwx10 runs the same kind of process without the option (status 0), so the refusal comes from the option",` | Starts a check: the older runner runs the same kind of process without the option. |
| 818 | `          r.returncode == 0 and "--evict-mb" not in args, (r.returncode, r.stderr[-200:]))` | The test: the exit status is 0, and the options hold no `--evict-mb`. This is the control: the refusal of lines 813 to 814 comes from the option and not from the rest of the command line. |
| 819 | `    args = first("ZN", lambda f: "read_nop64" in f[1])` | `args`: the options of the first `ZN` process on CPU 2 whose tag names `read_nop64`. |
| 820 | `    r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True)` | Runs the stand-in `bwx10` with these options. |
| 821 | `    check("the old bwx10 refuses a ZN plan (kernel read_nop64 is unknown to it)", r.returncode != 0, (r.returncode, r.stderr[-200:]))` | Check: the older runner refuses a `ZN` plan. It does not know the kernel `read_nop64`, so its plan parser rejects the plan. |

### `bwx11_checks`: every plan of round 4 through a stand-in `bwx11` (lines 824 to 895)

| Line | Source | Explanation |
|---:|---|---|
| 824 | `def bwx11_checks(tmp, real, sched):` | Starts the function `bwx11_checks`. `real`: the generated folder with the real durations. `sched`: the folder with the test divisor 100. |
| 825 | `    what = "the run of the plans of ZA, ZD, ZC, ZN and ZM through a local stand-in bwx11"` | `what`: the name of this part of the test, for the `SKIP` lines. |
| 826 | `    src = os.path.join(Z, "bwx11.c")` | `src`: the path of the runner source `bwx11.c` in the folder of this file. |
| 827 | `    if "--no-bwx11" in sys.argv[1:]:` | When the option `--no-bwx11` was given. |
| 828 | `        skip("%s (--no-bwx11)" % what)` | Reports the part as not run. |
| 829 | `        return` | Leaves the function. |
| 830 | `    if not os.path.exists(src):` | When the source file is not in the folder. |
| 831 | `        skip("%s (bwx11.c is not in this folder)" % what)` | Reports the part as not run, with that reason. |
| 832 | `        return` | Leaves the function. |
| 833 | `    binary, why = build_stand_in(src, os.path.join(tmp, "bwx11"), "bwx11")` | Builds `bwx11.c` as a stand-in binary `bwx11` in a temporary folder. |
| 834 | `    if binary is None:` | When the build failed. |
| 835 | `        skip("%s (bwx11.c does not build here: %s)" % (what, why))` | Reports the part as not run, with the first line of the compiler output. A failed build is a `SKIP` here and not a failed check. |
| 836 | `        return` | Leaves the function. |
| 837 | `    d = os.path.dirname(binary)` | `d`: the folder of the stand-in binary. |
| 838 | `    alt = local_cpus()` | `alt`: the CPU that stands in for CPU 41 on this machine. |
| 839 | `    if alt is None:` | When this machine does not have the CPUs that the runs need. |
| 840 | `        return` | Leaves the function. The failed check of `local_cpus` is counted. |
| 841 | `    shutil.copytree(sched, os.path.join(d, "sched11"))` | Copies the schedule folder with the test divisor 100 to `sched11` in the folder of the binary. |
| 842 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment without every variable whose name starts with `BWX_`. |
| 843 | `    r = subprocess.run([binary, "--list"], env=env, capture_output=True, text=True)` | Runs the stand-in with `--list`, the option that prints the names of its kernels. |
| 844 | `    check("the stand-in bwx11 lists the kernels of round 4 (asmread, read, oldread, read_nop64, read_nop96, read_nop128)",` | Starts a check: the stand-in `bwx11` lists the 6 kernels of round 4. |
| 845 | `          r.returncode == 0 and set(NEW_KERNELS + ["asmread", "read", "oldread"]) <= set(r.stdout.split()), r.stdout[:300])` | The test: exit status 0, and the three new kernels, `asmread`, `read` and `oldread` are all among the printed words. So the binary under test is one that knows the new kernels. |
| 846 | `    jobs = stand_in_jobs(d, ALL_STEPS, alt)` | `jobs`: one job per process of all 5 steps and both sessions, with CPU 41 replaced. |
| 847 | `    t0 = time.time()` | `t0`: the time before the runs, for the name of a check. |
| 848 | `    # 4 at a time: a process with --evict-mb 512 writes 512 MiB of memory.` | Comment: 4 processes run at the same time. The reason for this limit: a process with `--evict-mb 512` writes 512 MiB of memory. |
| 849 | `    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:` | Creates a pool of 4 worker threads. |
| 850 | `        results = list(pool.map(lambda j: run_job(binary, d, env, j), jobs))` | Runs every job through `run_job` in the pool and collects the results in the order of the jobs. |
| 851 | `    per = collections.defaultdict(list)` | `per`: the results per step and session. |
| 852 | `    for job, res in zip(jobs, results):` | Starts a loop over the jobs with their results. |
| 853 | `        per[job[0], job[1]].append(res)` | Adds the result to the list of its step and session. |
| 854 | `    for (step, session), res in sorted(per.items(), key=lambda x: (x[0][1], ALL_STEPS.index(x[0][0]))):` | Starts a loop over the steps and sessions, sorted by the session and then by the place of the step in `ALL_STEPS`. |
| 855 | `        bad = [x for x in res if x]` | `bad`: the results that describe a defect. |
| 856 | `        check("%s session %d (test divisor 100): the stand-in bwx11 accepts each of the %d plans with its args: status 0, one S and "` | Starts a check per step and session: the stand-in `bwx11` accepts each plan with its options. The name lists what `run_job` tested: status 0, one `S` row and one `E` row per trial. |
| 857 | `              "one E row per trial, every planned window as a W row, the pad and the evict setting in the M rows"` | Continues the name: every planned window as a `W` row, and the pad and the evict setting in the `M` rows. |
| 858 | `              % (step, session, len(res)), len(res) == TABLE[step][0] and not bad, bad[:2])` | The test: the number of results is the number of processes of the step in `TABLE`, and no result describes a defect. This proves that the runner can read every plan and every command line that the generator writes. A plan that the runner refused on CRB would end the step with exit status 1. |
| 859 | `    check("all %d plans of round 4 ran through the stand-in bwx11 (%.0f s)" % (len(jobs), time.time() - t0),` | Starts a check: all plans of round 4 ran through the stand-in. The name gives the number of jobs and the seconds that the runs took. |
| 860 | `          len(jobs) == 438 + 432 and all(x is None for x in results))` | The test: there are 438 plus 432 jobs, the processes of both sessions, and every result is `None`. |
| 861 | `    # The acceptance means something only if bwx11 refuses a defective plan.` | Comment: the acceptance of the good plans means something only if `bwx11` refuses a plan with a defect. |
| 862 | `    plan = os.path.join(d, "sched11", "s1", "ZM", "0000.plan")` | `plan`: the first plan of `ZM` in session 1, in the copy. |
| 863 | `    text = open(plan).read()` | `text`: the text of that plan. |
| 864 | `    line = text.split("\n")[3]` | `line`: its one trial line. |
| 865 | `    args = ["--trial", "--cpus", "2", "--bytes", "8388608", "--plan"]` | `args`: the options for the next runs: one worker on CPU 2 and a buffer of 8388608 bytes (8 MiB). The plan path is added in each run. |
| 866 | `    for name, bad in (("an unknown kernel", text.replace("@", "x@")),` | Starts a loop over four plans with one defect each. First: an unknown kernel, made by an `x` before each `@`. |
| 867 | `                      ("a size above --bytes", text.replace("@8M", "@64M")),` | Second: a size of 64 MiB, which is above `--bytes`. |
| 868 | `                      ("4097 windows", text.replace(line, re.sub(r" \d+ (\d+ closed)", r" 4097 \1", line))),` | Third: 4097 windows, one more than the limit of the runner. |
| 869 | `                      ("bins 2", text.replace(line, line[:-1] + "2"))):` | Fourth: the last field, `bins`, is 2. |
| 870 | `        p = os.path.join(d, "bad.plan")` | `p`: the path of the damaged plan file. |
| 871 | `        with open(p, "w") as f:` | Opens it for writing. |
| 872 | `            f.write(bad)` | Writes the damaged text. |
| 873 | `        r = subprocess.run([binary] + args + [p], env=env, capture_output=True, text=True)` | Runs the stand-in with the damaged plan. |
| 874 | `        check("bwx11 refuses a plan with %s (status 2)" % name, bad != text and r.returncode == 2, (r.returncode, r.stderr))` | Check, once per defect: the damaged text differs from the good one, and `bwx11` ends with exit status 2. So the runner checks its plan and does not run a plan with a defect. |
| 875 | `    r = subprocess.run([binary] + args + [plan, "--evict-mb", "x"], cwd=d, env=env, capture_output=True, text=True)` | Runs the stand-in with the good plan and with `--evict-mb x`. |
| 876 | `    check("bwx11 refuses --evict-mb with a value that is not a number", r.returncode != 0, (r.returncode, r.stderr[-200:]))` | Check: `bwx11` refuses a value of `--evict-mb` that is not a number. The exit status is not 0. |
| 877 | `    # The real plans of ZM, test divisor 1: the first replicate block of session 1 holds every pad once, all on` | Comment: the next part runs the real plans of `ZM`, with the test divisor 1. The first replicate block of session 1 holds every pad once, and all its processes use CPU 2. |
| 878 | `    # CPU 2. Each process is 30 s of kernel work; the 10 run at the same time.` | Continues the comment: each process has 30 s of kernel work, and the 10 processes run at the same time. |
| 879 | `    if "--no-long" in sys.argv[1:]:` | When the option `--no-long` was given. |
| 880 | `        skip("the 10 runs of 30 s of the real ZM plans through bwx11 (--no-long)")` | Reports this part as not run. |
| 881 | `        return` | Leaves the function. |
| 882 | `    dr = os.path.join(tmp, "bwx11real")` | `dr`: one more temporary folder. |
| 883 | `    os.makedirs(dr)` | Creates it. |
| 884 | `    shutil.copytree(real, os.path.join(dr, "sched11"))` | Copies the schedule folder with the real durations to `sched11` in it. |
| 885 | `    jobs = stand_in_jobs(dr, ["ZM"], alt, sessions=(1,), only=set(range(10)))` | `jobs`: the jobs for the first 10 rows of `ZM` in session 1. |
| 886 | `    t0 = time.time()` | `t0`: the time before the runs. |
| 887 | `    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:` | Creates a pool of 10 worker threads. |
| 888 | `        results = list(pool.map(lambda j: run_job(binary, dr, env, j), jobs))` | Runs the 10 jobs at the same time. All 10 workers are pinned to the same CPU, so the rates of these runs mean nothing. Only the rows are tested. |
| 889 | `    bad = [x for x in results if x]` | `bad`: the results that describe a defect. |
| 890 | `    pads = sorted(int(j[3][j[3].index("--rec-pad") + 1]) for j in jobs)` | `pads`: the values of `--rec-pad` of the 10 jobs, sorted. |
| 891 | `    check("ZM real plans (test divisor 1, first block of session 1, %.0f s): bwx11 accepts 300 windows of 100 ms with each of "` | Starts a check: with the real plans, `bwx11` accepts 300 windows of 100 ms with each of the 10 pads and prints every window. The name gives the seconds that the runs took. |
| 892 | `          "the 10 pads and prints every window" % (time.time() - t0),` | Continues the name of the check. |
| 893 | `          pads == ZM_PADS and [j[5] for j in jobs] == [300] * 10 and not bad, (pads, bad[:2]))` | The test: the pads are the 10 values of `ZM_PADS`, each job plans 300 windows, and no result describes a defect. This proves that the longest real plan of the round, 30 s in 300 windows, runs to its end with its real durations. |

### Texts of the dummy runner and of the stand-ins for `ps` and `ssh` (lines 896 to 927)

| Line | Source | Explanation |
|---:|---|---|
| 896 | `# ---------- run_bwx11.sh with dummy binaries ----------` | Comment: the checks of the run script `run_bwx11.sh` with dummy binaries start here. |
| 897 | `DUMMY = """#!/usr/bin/env bash` | `DUMMY`: the text of a Bash script that stands in for a runner. This line is its first line, which tells Linux to run it with `bash`. |
| 898 | `# Stand-in for @WORD@: records its process ids and its own path, checks the plan file, sleeps, ends with DUMMY_EXIT.` | Line of the dummy script: a comment. `@WORD@` is replaced later with the word of the binary. The dummy records its process ids and its own path, checks the plan file, sleeps, and ends with the status in `DUMMY_EXIT`. |
| 899 | `echo "$$ $*" >> "$DUMMY_LOG"` | Line of the dummy script: appends its process id (`$$`) and all its arguments (`$*`) to the file that `DUMMY_LOG` names. The test reads this file to see what was started, and with which options. |
| 900 | `echo "$0" >> "$DUMMY_LOG.bin"` | Line of the dummy script: appends its own path (`$0`) to the file `DUMMY_LOG` with the ending `.bin`. So the test sees which binary each launch used. |
| 901 | `grep Cpus_allowed_list /proc/$$/status >> "$DUMMY_LOG.cpus"` | Line of the dummy script: appends the line `Cpus_allowed_list` of its own status file under `/proc` to the file with the ending `.cpus`. That line is the CPU list of the process. |
| 902 | `echo "PMU=${BWX_PMU_TYPE:-} EV=${BWX_EVENTS:-}" >> "$DUMMY_LOG.env"` | Line of the dummy script: appends the values of `BWX_PMU_TYPE` and `BWX_EVENTS` in its environment to the file with the ending `.env`. |
| 903 | `while (( $# )); do if [[ $1 == --plan && ! -r $2 ]]; then echo "no plan $2" >&2; exit 7; fi; shift; done` | Line of the dummy script: a loop over its arguments. When the argument after `--plan` is not a readable file, it prints `no plan` with the path to the error output and ends with exit status 7. So a wrong plan path fails as it would in a real runner. |
| 904 | `echo "M,dummy,@WORD@"` | Line of the dummy script: prints one output row, `M,dummy,` and the word of the binary. The test finds this row in the output file of the step. |
| 905 | `sleep "${DUMMY_SLEEP:-0}" & echo "$! sleep" >> "$DUMMY_LOG"` | Line of the dummy script: starts `sleep` in the background for the seconds in `DUMMY_SLEEP`, 0 when it is not set or is empty. Then it appends the process id of the sleep and the word `sleep` to the log. |
| 906 | `wait $!` | Line of the dummy script: waits for the sleep. |
| 907 | `# DUMMY_TOUCH=1: the marker file appears when this process ends.` | Line of the dummy script: a comment. With `DUMMY_TOUCH=1` the marker file appears when this process ends. |
| 908 | `[[ -z ${DUMMY_TOUCH:-} ]] \|\| : > "$BWX8_MARKER"` | Line of the dummy script: when `DUMMY_TOUCH` is set, it creates the marker file at the path in `BWX8_MARKER`. The command `:` with `>` writes an empty file. |
| 909 | `exit "${DUMMY_EXIT:-0}"` | Line of the dummy script: ends with the exit status in `DUMMY_EXIT`, 0 when it is not set or is empty. |
| 910 | `"""` | Ends the text `DUMMY`. |
| 912 | `PS_STUB = """#!/usr/bin/env bash` | `PS_STUB`: the text of a Bash script that stands in for the tool `ps`. This line is its first line. |
| 913 | `# Stand-in for ps: its second call creates the file named by PS_TOUCH. Then it runs the real ps.` | Line of the stand-in: a comment. Its second call creates the file that `PS_TOUCH` names. Then it runs the real `ps`. |
| 914 | `# run_bwx11.sh calls ps once for env.txt and then once per launch, after the wait and before the last marker check.` | Line of the stand-in: a comment. `run_bwx11.sh` calls `ps` once for `env.txt` and then once per launch, after the wait and before the last marker check. So the second call is the moment directly before the first launch. |
| 915 | `if [[ -n ${PS_TOUCH:-} ]]; then` | Line of the stand-in: only when `PS_TOUCH` is set and not empty. |
| 916 | `  echo call >> "$PS_TOUCH.calls"` | Line of the stand-in: appends one line to a file that counts the calls. |
| 917 | `  if (( $(wc -l < "$PS_TOUCH.calls") == 2 )); then : > "$PS_TOUCH"; fi` | Line of the stand-in: when that file has 2 lines, it creates the empty file that `PS_TOUCH` names. |
| 918 | `fi` | Line of the stand-in: ends the `if`. |
| 919 | `exec %s "$@"` | Line of the stand-in: replaces itself with the real `ps` and passes all arguments on. The `%s` is filled later with the path of the real `ps`. |
| 920 | `"""` | Ends the text `PS_STUB`. |
| 922 | `SSH_STUB = """#!/bin/bash` | `SSH_STUB`: the text of a Bash script that stands in for `ssh`. This line is its first line. |
| 923 | `# Stand-in for ssh: records the remote command (its last argument). It opens no connection.` | Line of the stand-in: a comment. It records the remote command, which is its last argument. It opens no connection. |
| 924 | `printf '%s\\n' "${@: -1}" >> "$SSH_LOG"` | Line of the stand-in: appends its last argument (`${@: -1}`) and a newline to the file that `SSH_LOG` names. |
| 925 | `"""` | Ends the text `SSH_STUB`. |

### Small helpers: `cpu_list`, `utc`, `sha256`, `samplers`, `dummy` (lines 928 to 969)

| Line | Source | Explanation |
|---:|---|---|
| 928 | `def cpu_list(text):` | Starts the function `cpu_list`. It converts a line `Cpus_allowed_list` to a set of CPU numbers. |
| 929 | `    cpus = set()` | `cpus`: the result set, empty at first. |
| 930 | `    for part in text.split(":")[1].strip().split(","):` | Takes the text after the colon and starts a loop over its parts between commas. A part is one CPU or a range such as `0-5`. |
| 931 | `        a, _, b = part.partition("-")` | Splits a part at the hyphen into the first CPU `a` and the last CPU `b`. `b` is empty for a single CPU. |
| 932 | `        cpus.update(range(int(a), int(b or a) + 1))` | Adds every CPU from `a` to `b`, or `a` alone. |
| 933 | `    return cpus` | Returns the set. |
| 936 | `def utc(offset):` | Starts the function `utc`. |
| 937 | `    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))` | Returns the UTC time `offset` seconds from now, as a text of the form `2026-11-15T03:00:00Z`. |
| 940 | `def sha256(path):` | Starts the function `sha256`. |
| 941 | `    return subprocess.run(["sha256sum", path], capture_output=True, text=True).stdout.split()[0]` | Runs the tool `sha256sum` on a file and returns the first word of its output, the checksum. |
| 944 | `def samplers(path_part):` | Starts the function `samplers`. |
| 945 | `    """Process ids of running hostwatch.py processes whose command line names this path."""` | Description text: the function returns the process ids of the running `hostwatch.py` processes whose command line names the given path. |
| 946 | `    found = []` | `found`: the result list, empty at first. |
| 947 | `    for pid in os.listdir("/proc"):` | Starts a loop over the names in `/proc`. |
| 948 | `        if pid.isdigit():` | Only a name of digits, which is a process id. |
| 949 | `            try:` | Starts the block whose error is caught. |
| 950 | `                cmd = open("/proc/%s/cmdline" % pid, "rb").read().decode("utf-8", "replace")` | Reads the command line of the process from its file `cmdline`. |
| 951 | `            except OSError:` | The process has ended in the meantime. |
| 952 | `                continue` | Skips it. |
| 953 | `            if "hostwatch.py" in cmd and path_part in cmd:` | When the command line holds `hostwatch.py` and the given path. |
| 954 | `                found.append(int(pid))` | Adds the process id. |
| 955 | `    return found` | Returns the list. |
| 958 | `def dummy(folder, word):` | Starts the function `dummy`. |
| 959 | ``    """Writes the dummy binary `word` and its build record into `folder`. Returns the path of the binary."""`` | Description text: the function writes the dummy binary with the name `word` and its build record into `folder`. It returns the path of the binary. |
| 960 | `    os.makedirs(folder, exist_ok=True)` | Creates the folder when it does not exist. |
| 961 | `    path = os.path.join(folder, word)` | `path`: the path of the dummy binary. |
| 962 | `    with open(path, "w") as f:` | Opens it for writing. |
| 963 | `        f.write(DUMMY.replace("@WORD@", word))` | Writes the text `DUMMY` with `@WORD@` replaced by the word. So the dummies of different words differ in their text and in their output row. |
| 964 | `    os.chmod(path, 0o755)` | Makes the file executable. |
| 965 | `    with open(os.path.join(folder, "build.txt"), "w") as f:` | Opens the file `build.txt` in the same folder for writing. |
| 966 | `        f.write("dummy build record of %s\n" % word)` | Writes one line that names the word. The run script copies this file into the result folder, so the test can see from which folder it came. |
| 967 | `    return path` | Returns the path. |

### Class `Box`: a copy of the run script with dummies in a temporary folder (lines 970 to 1072)

| Line | Source | Explanation |
|---:|---|---|
| 970 | `class Box:` | Starts the class `Box`. It is the test setup for the run script. |
| 971 | `    """A copy of run_bwx11.sh and hostwatch.py with a test schedule in a temporary folder. The dummy bwx11 is beside` | Description text: a `Box` holds a copy of `run_bwx11.sh` and of `hostwatch.py` with a test schedule in a temporary folder. The dummy `bwx11` lies beside the script, as on CRB. |
| 972 | `    the script, as on CRB. The dummy bwx8 and the dummy bwx10 are each in an own folder with an own build record."""` | Continues the text: the dummy `bwx8` and the dummy `bwx10` each lie in a folder of their own, with a build record of their own. |
| 974 | `    def __init__(self, tmp, sched):` | Starts the constructor. `sched` is the generated folder with the test divisor 100. |
| 975 | `        self.dir = os.path.join(tmp, "box")` | `dir`: the folder `box` in the temporary folder. |
| 976 | `        os.makedirs(self.dir)` | Creates it. |
| 977 | `        shutil.copy(RUN, self.dir)` | Copies the run script into the box. The test runs this copy, so the script finds its files beside itself. |
| 978 | `        shutil.copy(WATCH, self.dir)` | Copies the host sampler into the box. |
| 979 | `        shutil.copytree(sched, os.path.join(self.dir, "sched11"))` | Copies the schedule folder into the box, with the name `sched11`. |
| 980 | `        self.bin11 = dummy(self.dir, "bwx11")` | `bin11`: a dummy with the word `bwx11`, in the box beside the script. |
| 981 | `        self.bin8 = dummy(os.path.join(tmp, "old8"), "bwx8")` | `bin8`: a dummy with the word `bwx8`, in the folder `old8`. |
| 982 | `        self.bin10 = dummy(os.path.join(tmp, "old10"), "bwx10")` | `bin10`: a dummy with the word `bwx10`, in the folder `old10`. |
| 983 | `        self.bin = {"bwx8": self.bin8, "bwx10": self.bin10, "bwx11": self.bin11}` | `bin`: a dictionary from each of the three words to the path of its dummy. |
| 984 | `        # A home folder with the accepted bwx8 and bwx10 at the paths that run_bwx11.sh uses on CRB.` | Comment: the next lines make a home folder that has the accepted `bwx8` and `bwx10` at the paths that `run_bwx11.sh` uses on CRB. |
| 985 | `        self.home = os.path.join(tmp, "home")` | `home`: the folder `home` in the temporary folder. |
| 986 | `        self.home8 = dummy(os.path.join(self.home, "cache-perf", "bwx8-20261114"), "bwx8")` | `home8`: a dummy `bwx8` at `cache-perf/bwx8-20261114/bwx8` below that home folder. |
| 987 | `        self.home10 = dummy(os.path.join(self.home, "cache-perf", "bwx10-20261115"), "bwx10")` | `home10`: a dummy `bwx10` at `cache-perf/bwx10-20261115/bwx10` below that home folder. |
| 988 | `        os.makedirs(os.path.join(self.dir, "bin"))` | Creates the folder `bin` in the box. |
| 989 | `        stub = os.path.join(self.dir, "bin", "ps")` | `stub`: the path of the stand-in for `ps` in that folder. |
| 990 | `        with open(stub, "w") as f:` | Opens it for writing. |
| 991 | `            f.write(PS_STUB % shutil.which("ps"))` | Writes the text `PS_STUB` with the path of the real `ps` put in. `shutil.which` finds that path. |
| 992 | `        os.chmod(stub, 0o755)` | Makes the stand-in executable. |
| 993 | `        self.watch_cpu = str(sorted(os.sched_getaffinity(0))[-1])` | `watch_cpu`: the highest CPU on which this test may run, as text. It becomes the CPU of the host sampler. |
| 994 | `        self.n = 0` | `n`: the number of the last test case, 0 at first. |
| 996 | `    def sched(self, *parts):` | Starts the method `sched`. |
| 997 | `        return os.path.join(self.dir, "sched11", *parts)` | Returns a path below the folder `sched11` of the box. |
| 999 | `    def set_bin(self, step, content):` | Starts the method `set_bin`. |
| 1000 | `        """Writes the .bin file of a step, in both sessions (the schedules of schedule11.py name bwx11)."""` | Description text: the method writes the `.bin` file of a step in both sessions. The schedules of `schedule11.py` name `bwx11`. |
| 1001 | `        for s in ("s1", "s2"):` | Starts a loop over the two session folders. |
| 1002 | `            if os.path.exists(self.sched(s, step + ".tsv")):` | Only when the step has a schedule in that session. |
| 1003 | `                with open(self.sched(s, step + ".bin"), "w") as f:` | Opens the `.bin` file of the step for writing. |
| 1004 | `                    f.write(content)` | Writes the given content. A check can so give a step another binary, or a wrong word. |
| 1006 | `    def rows(self, step, session=1):` | Starts the method `rows`. |
| 1007 | `        text = open(self.sched("s%d" % session, step + ".tsv")).read()` | Reads the schedule file of a step, of session 1 unless another session is given. |
| 1008 | `        return [r.split("\t") for r in text.split("\n")[1:-1]]` | Returns its data rows, each split at the tabs. |
| 1010 | `    def start(self, args, pre=(), **env):` | Starts the method `start`. `args`: the arguments for the run script. `pre`: words to put before the script, for example a `taskset` command. `env`: settings for its environment. |
| 1011 | `        """Starts the script in fresh result, marker and log paths. Returns the process."""` | Description text: the method starts the script with new paths for the results, the marker file and the log. It returns the process. |
| 1012 | `        self.n += 1` | Counts the test case. |
| 1013 | `        self.case = os.path.join(self.dir, "case%d" % self.n)` | `case`: a folder of its own for this case, `case` plus the number. |
| 1014 | `        os.makedirs(self.case)` | Creates it. |
| 1015 | `        self.results = os.path.join(self.case, "results")` | `results`: the place for the result folders of this case. |
| 1016 | `        self.marker = os.path.join(self.case, "RUNNING")` | `marker`: the path that takes the place of the marker file in this case. |
| 1017 | `        self.stopfile = os.path.join(self.case, "STOP")` | `stopfile`: the path that takes the place of the stop file. |
| 1018 | `        self.log = os.path.join(self.case, "dummy.log")` | `log`: the log file of the dummies. |
| 1019 | `        e = {k: v for k, v in os.environ.items()` | `e`: the environment for the script. It starts as a copy of the environment of the test without the settings that the script reads. |
| 1020 | `             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED", "BWX8_SHA256", "BWX10_SHA256", "BWX11_SHA256",` | The names that are left out: `STOP_AT`, `SESSION`, `SESSION1_END`, `RESERVE`, the internal mark `_PINNED`, and the three digest settings. |
| 1021 | `                          "BWX_PMU_TYPE", "BWX_EVENTS", "WATCH_CPU")}` | More names that are left out: the two counter settings and `WATCH_CPU`. So nothing from the shell of the developer changes a test case. |
| 1022 | `        e.update(HOME=self.case, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_BIN=self.bin8, BWX10_BIN=self.bin10,` | Adds the settings of the case: the case folder as `HOME`, the test paths of the marker file and of the stop file, and the dummies for the words `bwx8` and `bwx10`. |
| 1023 | `                 BWX11_BIN=self.bin11, BWX8_RESULTS=self.results, DUMMY_LOG=self.log, WATCH_CPU=self.watch_cpu)` | Continues the settings: the dummy for the word `bwx11`, the place of the result folders, the log of the dummies, and the CPU of the host sampler. With these test settings the script never touches the real marker file or a real binary. |
| 1024 | `        e.update(env)` | Adds the settings that the caller gave. They replace the defaults of the case. |
| 1025 | `        e = {k: v for k, v in e.items() if v is not None}      # None: leave this setting out` | Removes every setting whose value is `None`. So a caller can take a default away. |
| 1026 | `        return subprocess.Popen(list(pre) + [os.path.join(self.dir, "run_bwx11.sh")] + args, env=e, text=True,` | Starts the copy of `run_bwx11.sh` in the box as a new process, with the words of `pre` before it and the arguments after it. |
| 1027 | `                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)` | Continues the call: the environment `e`, text mode, and pipes for the output and the error output. `start_new_session=True` gives the script a session of its own, so a signal of the test reaches only it. |
| 1029 | `    def run(self, args, pre=(), **env):` | Starts the method `run`: start the script and wait for its end. |
| 1030 | `        p = self.start(args, pre, **env)` | Starts the script. |
| 1031 | `        out, err = p.communicate(timeout=900)` | Waits for its end, at most 900 s, and reads its output and its error output. |
| 1032 | `        return p.returncode, out, err` | Returns the exit status, the output and the error output. |
| 1034 | `    def folders(self):` | Starts the method `folders`. |
| 1035 | `        return sorted(os.path.join(self.results, d) for d in os.listdir(self.results)) if os.path.isdir(self.results) else []` | Returns the sorted paths of the result folders of the case, or an empty list when the script made none. |
| 1037 | `    def folder(self):` | Starts the method `folder`. |
| 1038 | `        d = self.folders()` | `d`: the result folders of the case. |
| 1039 | `        return d[0] if len(d) == 1 else None` | Returns the folder when there is exactly one, and `None` if not. |
| 1041 | `    def file(self, name):` | Starts the method `file`. It reads one file of the result folder. |
| 1042 | `        f = self.folder()` | `f`: the result folder, or `None`. |
| 1043 | `        path = os.path.join(f, name) if f else ""` | `path`: the path of the file, or an empty text without a folder. |
| 1044 | `        return open(path).read() if os.path.exists(path) else ""` | Returns the content of the file, or an empty text when the file does not exist. |
| 1046 | `    def csv(self, step):` | Starts the method `csv`. |
| 1047 | `        return self.file(step + ".csv")` | Returns the content of the output file `<STEP>.csv` of a step. |
| 1049 | `    def launched(self):` | Starts the method `launched`. |
| 1050 | `        return [l for l in open(self.log).read().split("\n") if l] if os.path.exists(self.log) else []` | Returns the lines of the dummy log that are not empty. Each launch gives two lines: the line of the dummy with its process id and options, and the line of its sleep. |
| 1052 | `    def binaries(self):` | Starts the method `binaries`. |
| 1053 | `        """The path of the dummy of each launch, in order."""` | Description text: the method returns the path of the dummy of each launch, in order. |
| 1054 | `        return open(self.log + ".bin").read().split("\n")[:-1] if os.path.exists(self.log + ".bin") else []` | Reads the file with the ending `.bin` that the dummies wrote. Without that file the result is an empty list. |
| 1056 | `    def wait_launch(self):` | Starts the method `wait_launch`. It waits until a dummy has started its sleep. |
| 1057 | `        end = time.time() + 90` | `end`: 90 s from now. |
| 1058 | `        while time.time() < end and len(self.launched()) < 2:` | Loops until the time is over or the log has at least 2 lines. |
| 1059 | `            time.sleep(0.2)` | Waits 0.2 s per turn. |
| 1060 | `        return len(self.launched()) >= 2` | Returns whether the log has at least 2 lines. |
| 1062 | `    def none_alive(self):` | Starts the method `none_alive`. It tests that the script left no process behind. |
| 1063 | `        time.sleep(0.5)` | Waits 0.5 s first. |
| 1064 | `        for l in self.launched():` | Starts a loop over the lines of the dummy log. Each starts with a process id, of a dummy or of its sleep. |
| 1065 | `            try:` | Starts the block whose error is caught. |
| 1066 | `                os.kill(int(l.split()[0]), 0)` | `os.kill` with the signal 0 sends nothing. It only tests whether the process exists. |
| 1067 | `                return False` | The process exists: returns false. |
| 1068 | `            except OSError:` | The process does not exist. |
| 1069 | `                pass` | Goes on with the next line. |
| 1070 | `        return not samplers(self.case)` | Returns true when also no host sampler of this case is running. |

### `visit_checks`: the visit script with a stand-in for `ssh` (lines 1073 to 1129)

| Line | Source | Explanation |
|---:|---|---|
| 1073 | `def visit_checks(tmp):` | Starts the function `visit_checks`: the checks of the visit script. |
| 1074 | `    """visit11.sh with a stand-in ssh. PATH holds only the stand-in and date, so no real ssh can start."""` | Description text: the checks run `visit11.sh` with a stand-in for `ssh`. The search path holds only the stand-in and `date`. So no real `ssh` can start, and the test never contacts CRB. |
| 1075 | `    d = os.path.join(tmp, "visit")` | `d`: the folder `visit` in the temporary folder. |
| 1076 | `    os.makedirs(os.path.join(d, "bin"))` | Creates it with a folder `bin` inside. |
| 1077 | `    text, n = re.subn(r"(?m)^N=.*$", "N=" + d, open(VISIT).read())` | Reads the visit script and replaces its line that starts with `N=`, the log folder, with a line that names `d`. `(?m)` lets `^` and `$` match at the start and the end of every line. `n` is the number of lines replaced. |
| 1078 | `    copy_path = os.path.join(d, "visit11.sh")` | `copy_path`: the path of the changed copy of the visit script. |
| 1079 | `    with open(copy_path, "w") as f:` | Opens the copy for writing. |
| 1080 | `        f.write(text)` | Writes the changed text. |
| 1081 | `    with open(os.path.join(d, "bin", "ssh"), "w") as f:` | Opens the file `ssh` in the folder `bin` for writing. |
| 1082 | `        f.write(SSH_STUB)` | Writes the stand-in text `SSH_STUB`. |
| 1083 | `    os.chmod(os.path.join(d, "bin", "ssh"), 0o755)` | Makes the stand-in executable. |
| 1084 | `    os.symlink(shutil.which("date"), os.path.join(d, "bin", "date"))` | Puts a link to the real tool `date` into the folder `bin`. The visit script needs `date` for its status line. |
| 1085 | `    log = os.path.join(d, "ssh.log")` | `log`: the file in which the stand-in records each remote command. |
| 1087 | `    def visit(name, **env):` | Starts the inner function `visit`. It runs the copy once, with a log name and with settings. |
| 1088 | `        if os.path.exists(log):` | When a record of an earlier call exists. |
| 1089 | `            os.remove(log)` | Removes it. |
| 1090 | `        e = {"PATH": os.path.join(d, "bin"), "SSH_LOG": log, "HOME": d}` | `e`: the whole environment of the script: a search path with only the folder `bin`, the record file for the stand-in, and `d` as the home folder. |
| 1091 | `        e.update(env)` | Adds the settings of the caller. |
| 1092 | `        r = subprocess.run([shutil.which("bash"), copy_path, name, "ZA", "ZD"], env=e, capture_output=True, text=True)` | Runs the copy with `bash`. The arguments are the log name and the two steps `ZA` and `ZD`. |
| 1093 | `        return r.returncode, open(log).read() if os.path.exists(log) else None, r.stderr` | Returns the exit status, the recorded remote command (`None` when the stand-in was never called), and the error output. |
| 1095 | `    rc, cmd, err = visit("ok", STOP_AT="2026-11-15T15:00Z", SESSION="2", SESSION1_END="2026-11-15T03:00Z",` | Runs the copy with a full set of valid settings: a stop time, session 2, the end of session 1. |
| 1096 | `                         BWX8_SHA256="0a1b", BWX10_SHA256="2c3d", BWX11_SHA256="4e5f", ENVV="RESERVE=90")` | Continues the settings: three digests and `ENVV` with `RESERVE=90`. |
| 1097 | `    check("visit11.sh: one login; the marker check is the first remote action, then run_bwx11.sh in ~/cache-perf/bwx11-20261115 "` | Starts a check of the normal case: one login. The marker check is the first remote action. Then comes `run_bwx11.sh` in the folder `~/cache-perf/bwx11-20261115`, with the three digests. |
| 1098 | `          "with the three digests",` | Continues the name of the check. |
| 1099 | `          n == 1 and rc == 0 and cmd is not None and cmd.count("\n") == 1` | The test, first conditions: exactly one `N=` line was replaced, the exit status is 0, the stand-in was called, and its record has exactly one line. One line means one login. |
| 1100 | `          and cmd.startswith("if [ -e /tmp/positron-perf.RUNNING ]; then ")` | Continues: the remote command starts with the test for the marker file `/tmp/positron-perf.RUNNING`. So nothing can start on CRB before the marker file was tested. |
| 1101 | `          and cmd.endswith("exit 3; fi; cd ~/cache-perf/bwx11-20261115 && STOP_AT=2026-11-15T15:00Z SESSION=2 "` | Continues: the remote command ends with this exact text: the end of the marker check with `exit 3`, then `cd` to the folder of round 4, then the settings in a fixed order. |
| 1102 | `                           "SESSION1_END=2026-11-15T03:00Z BWX8_SHA256=0a1b BWX10_SHA256=2c3d BWX11_SHA256=4e5f RESERVE=90 "` | Continues the expected text: the end of session 1, the three digests and `RESERVE=90` from `ENVV`. |
| 1103 | `                           "./run_bwx11.sh ZA ZD\n")` | Ends the expected text: the script `./run_bwx11.sh` with the two steps. This proves that every setting of the caller reaches the run script unchanged. |
| 1104 | `          and open(os.path.join(d, "ok.log")).read().startswith("ssh status 0 utc "), (rc, cmd, err))` | Last condition: the log file `ok.log` starts with `ssh status 0 utc`. So the visit script wrote the status of `ssh` to its log. |
| 1105 | `    rc, cmd, err = visit("plain", STOP_AT="none", SESSION="1")` | Runs the copy with the two required settings only. |
| 1106 | `    check("visit11.sh without digests and SESSION1_END: the four settings are passed empty",` | Starts a check: without digests and without `SESSION1_END`, these four settings are passed as empty values. |
| 1107 | `          rc == 0 and cmd is not None` | The test: exit status 0, and the stand-in was called. |
| 1108 | `          and cmd.endswith("STOP_AT=none SESSION=1 SESSION1_END= BWX8_SHA256= BWX10_SHA256= BWX11_SHA256=  ./run_bwx11.sh ZA ZD\n"),` | Continues: the remote command ends with the four names, each followed by nothing, and the script with the steps. An empty value tells the run script that the setting is not given. |
| 1109 | `          (rc, cmd, err))` | The detail for a failure of the check. |
| 1110 | `    ok = {"STOP_AT": "2026-11-15T15:00Z", "SESSION": "2", "SESSION1_END": "2026-11-15T03:00Z", "BWX8_SHA256": "0a1b",` | `ok`: a full set of valid settings, as a base for the next checks. |
| 1111 | `          "BWX10_SHA256": "2c3d", "BWX11_SHA256": "4e5f"}` | Continues the set: the digests of `bwx10` and `bwx11`. |
| 1112 | `    for var, value in (("SESSION1_END", "2026-11-15 03:00"), ("STOP_AT", "2026-11-15 15:00"),` | Starts a loop over bad values, each for one setting. This line: two times that hold a blank. |
| 1113 | `                       ("STOP_AT", "none;id"), ("SESSION", "1$(id)"), ("BWX8_SHA256", "0a1b\|x"), ("BWX10_SHA256", "2c3d x"),` | Continues the list: a value with a semicolon and a command, a value with a command substitution, a value with a vertical bar, and a value with a blank. |
| 1114 | `                       ("BWX10_SHA256", "2c3d;id"), ("BWX11_SHA256", "4e5f x"), ("BWX11_SHA256", "4e5f;id"), ("BWX11_SHA256", "$(id)")):` | Ends the list with four more bad digests: with a semicolon, with a blank, and a command substitution alone. |
| 1115 | `        rc, cmd, err = visit("bad", **dict(ok, **{var: value}))` | Runs the copy with the valid set in which this one setting has the bad value. |
| 1116 | `        check("visit11.sh: %s='%s' is refused with status 2 before the login, no log file" % (var, value),` | Starts a check per bad value: the visit script refuses it with exit status 2 before the login and writes no log file. |
| 1117 | `              rc == 2 and cmd is None and var in err and not os.path.exists(os.path.join(d, "bad.log")), (rc, cmd, err))` | The test: exit status 2, the stand-in was never called, the error output names the setting, and no file `bad.log` exists. This matters: such a value would become a part of the command line on CRB and could run another command there. |
| 1118 | `    rc, cmd, err = visit("nostop", SESSION="1")` | Runs the copy without `STOP_AT`. |
| 1119 | `    check("visit11.sh: STOP_AT not set: no login", rc != 0 and cmd is None, (rc, cmd, err))` | Check: without `STOP_AT` the script ends with a status other than 0, and the stand-in is never called. So no visit starts without a decision about the stop time. |
| 1120 | `    a, b = open(os.path.join(Y, "visit10.sh")).read().split("\n"), open(VISIT).read().split("\n")` | `a` and `b`: the lines of `visit10.sh`, the visit script of round 3, and of `visit11.sh`. |
| 1121 | `    back = [l.replace("./run_bwx11.sh", "./run_bwx10.sh").replace("bwx11-20261115", "bwx10-20261115")` | `back`: the code lines of `visit11.sh` with the names of round 4 written back to those of round 3: the run script and the folder on CRB. |
| 1122 | `            .replace(" BWX11_SHA256=${BWX11_SHA256:-}", "").replace(" BWX11_SHA256;", ";") for l in b if not l.startswith("#")]` | Continues: the setting `BWX11_SHA256` is removed from the remote command and from the list of checked names. Comment lines are left out. |
| 1123 | `    check("visit11.sh differs from visit10.sh only in comment lines, the folder on CRB, the script that it starts and BWX11_SHA256",` | Starts a check: `visit11.sh` differs from `visit10.sh` only in comment lines, in the folder on CRB, in the script that it starts and in `BWX11_SHA256`. |
| 1124 | `          [l for l in a if not l.startswith("#")] == back and len(back) > 8, [x for x in back if x not in a][:2])` | The test: the code lines of `visit10.sh` are equal to `back`, and there are more than 8 of them. So the visit script of round 4 has no other change to the script that was used before. |
| 1125 | `    check("visit11.sh names one host only, the CRB login of the handoff, and starts ssh once",` | Starts a check: `visit11.sh` names one host only, and it starts `ssh` once. |
| 1126 | `          re.findall(r"\b\d+\.\d+\.\d+\.\d+\b", open(VISIT).read()) == ["192.168.2.45"]` | The test, first half: the only text of the form of an IP address in the script is `192.168.2.45`, the address of CRB. The pattern finds four numbers with dots between them. |
| 1127 | `          and len(re.findall(r"(?m)^ssh ", open(VISIT).read())) == 1 and "scp" not in open(VISIT).read())` | Second half: exactly one line of the script starts with `ssh` and a blank, and the script does not hold the text `scp`. So the script cannot log in to another machine and cannot copy files. |

### `script_diff`, and `run_checks`: syntax and comparison with the older run scripts (lines 1130 to 1165)

| Line | Source | Explanation |
|---:|---|---|
| 1130 | `def script_diff():` | Starts the function `script_diff`. |
| 1131 | `    """The code lines (no comment lines) that run_bwx11.sh adds to and removes from run_bwx10.sh, after the names of` | Description text: the function returns the code lines, without comment lines, that `run_bwx11.sh` adds to `run_bwx10.sh` and removes from it. |
| 1132 | `    round 4 are written back to those of round 3."""` | Continues the text: before the comparison the names of round 4 are written back to those of round 3. |
| 1133 | `    old = [l for l in open(os.path.join(Y, "run_bwx10.sh")).read().split("\n") if not l.lstrip().startswith("#")]` | `old`: the lines of `run_bwx10.sh` that are not comment lines. |
| 1134 | `    new = [l.replace("sched11", "sched10").replace("run_bwx11.sh", "run_bwx10.sh").replace("^Z[A-Z0-9]+$", "^Y[A-Z0-9]+$")` | `new`: the lines of `run_bwx11.sh` with three names written back: the schedule folder, the name of the script, and the pattern of a step name (`Z` back to `Y`). |
| 1135 | `           .replace("$RESULTS/bwx11-$STEP_NAME", "$RESULTS/bwx10-$STEP_NAME")` | Continues: the start of the name of the result folders is written back too. |
| 1136 | `           for l in open(RUN).read().split("\n") if not l.lstrip().startswith("#")]` | The loop of that list: all lines of the run script that are not comment lines. |
| 1137 | `    d = list(difflib.ndiff(old, new))` | `d`: the line by line difference of the two lists, from `difflib.ndiff`. A line that only `new` has starts with a plus sign, and a line that only `old` has starts with a minus sign. |
| 1138 | `    return [l[2:] for l in d if l.startswith("+ ")], [l[2:] for l in d if l.startswith("- ")]` | Returns two lists: the added lines and the removed lines, each without its mark. |
| 1141 | `def run_checks(tmp, sched):` | Starts the function `run_checks`: the checks of the run script. `sched` is the generated folder with the test divisor 100. |
| 1142 | `    for f in ("run_bwx11.sh", "visit11.sh"):` | Starts a loop over the two shell scripts of round 4. |
| 1143 | `        r = subprocess.run(["bash", "-n", os.path.join(Z, f)], capture_output=True, text=True)` | Runs `bash -n` on the script. With `-n` the shell reads the script and reports syntax errors, and it runs no command. |
| 1144 | `        check("bash -n " + f, r.returncode == 0, r.stderr)` | Check, once per script: `bash -n` ends with status 0. So the script has no syntax error. |
| 1145 | `    # The stop controls and the launch function are the text of run_bwx9.sh and run_bwx10.sh.` | Comment: the stop controls and the launch function are the text of `run_bwx9.sh` and of `run_bwx10.sh`. |
| 1146 | `    part = re.compile(r"(?s)\n# ---- stop controls[^\n]*\n(.*?\n)# ---- end of the copied part ----\n")` | `part`: a pattern that cuts the copied part out of a run script. It finds the comment line that starts with `# ---- stop controls`. Its group holds all lines after it, up to the line `# ---- end of the copied part ----`. `(?s)` lets a dot match a newline too. |
| 1147 | `    old, mid, new = (part.search(open(f).read()) for f in (os.path.join(X, "run_bwx9.sh"), os.path.join(Y, "run_bwx10.sh"), RUN))` | `old`, `mid`, `new`: the result of the search in `run_bwx9.sh`, in `run_bwx10.sh` and in the run script under test. |
| 1148 | `    check("run_bwx11.sh keeps the stop controls and the launch function of run_bwx9.sh and run_bwx10.sh unchanged (54 lines: "` | Starts a check: `run_bwx11.sh` keeps the stop controls and the launch function of the two older scripts unchanged. The name gives the size, 54 lines. |
| 1149 | `          "why_stop, check_marker, check_deadline, the trap, settle, one, stop_child, stop_watch)",` | Continues the name with the functions of that part: `why_stop`, `check_marker`, `check_deadline`, the trap, `settle`, `one`, `stop_child` and `stop_watch`. |
| 1150 | `          old is not None and mid is not None and new is not None and old.group(1) == new.group(1) == mid.group(1)` | The test, first half: the part was found in all three scripts, and the three texts are equal. |
| 1151 | `          and old.group(1).count("\n") == 54` | Continues: the part has 54 lines. |
| 1152 | `          and all(w in new.group(1) for w in ("why_stop()", "check_marker()", "check_deadline()", "trap '", "settle()", "one()")),` | Continues: the part holds the definitions of the five functions and the `trap` line. This proves that the stop controls of this run script are the text that the older scripts used. A change there could make the script miss the marker file or a stop time. |
| 1153 | `          old and old.group(1).count("\n"))` | The detail for a failure: the number of lines found. |
| 1154 | `    added, removed = script_diff()` | `added`, `removed`: the code lines that differ between the two run scripts, from `script_diff`. |
| 1155 | `    key = ("for v in BWX8_MARKER", "BIN10=${BWX10_BIN:-$HOME/cache-perf/bwx10-20261115/bwx10}", "BIN11=${BWX11_BIN:-$SRC/bwx11}",` | `key`: seven short texts, one for each line that may be added. This line: the loop over the test variables, the path of `bwx10`, and the path of `bwx11`. |
| 1156 | `           "bwx11) BIN=$BIN11 ;;", "must hold the one word bwx8, bwx10 or bwx11", "case $BIN_WORD in bwx8) WANT=${BWX8_SHA256:-} ;; "` | Continues: the case branch of the word `bwx11`, the error message about the one word, and the start of the line that chooses the digest. |
| 1157 | `           "bwx10) WANT=${BWX10_SHA256:-} ;; *) WANT=${BWX11_SHA256:-} ;; esac", "BWX11_SHA256=${BWX11_SHA256:-} binary=$BIN_WORD")` | Ends the list: the rest of the digest line, and the part of the settings line of `env.txt` that names `BWX11_SHA256`. |
| 1158 | `    check("the code of run_bwx11.sh differs from run_bwx10.sh only in: the names (sched11, step pattern, result folder), the "` | Starts a check: the code of `run_bwx11.sh` differs from `run_bwx10.sh` only in the names, in the path of `bwx10`, in the word `bwx11`, in its test setting and in its digest. |
| 1159 | `          "path of bwx10, the word bwx11, its test setting and its digest (7 lines added, 5 removed)",` | Continues the name: 7 lines added, 5 removed. |
| 1160 | `          len(added) == 7 and len(removed) == 5 and all(sum(k in l for l in added) == 1 for k in key), (added, removed))` | The test: exactly 7 added lines and 5 removed lines, and each of the 7 texts of `key` occurs in exactly one added line. So no other line of the script that ran in round 3 was changed. |
| 1161 | `    check("RESERVE keeps its default of 90 s", open(RUN).read().count("RESERVE=${RESERVE:-90} ") == 1)` | Check: the run script holds the text `RESERVE=${RESERVE:-90}` and a blank exactly once. So the default of `RESERVE` is still 90 s. |
| 1162 | `    box = Box(tmp, sched)` | `box`: a new test setup with a copy of the run script, the dummies and the schedule with the test divisor 100. |
| 1163 | `    absent = os.path.join(box.dir, "absent")` | `absent`: a path in the box at which no file exists. |
| 1164 | `    last = {st: TABLE[st][0] - 1 for st in TABLE}            # the last idx of each step` | `last`: for each step the `idx` of its last process, the number of processes minus 1. |

### `run_checks`: step names and the dry run (lines 1166 to 1203)

| Line | Source | Explanation |
|---:|---|---|
| 1166 | `    # ---- steps and the dry run ----` | Comment: the checks of the step names and of the dry run start here. |
| 1167 | `    for name in ("S2", "YF", "Zd", "Z", "Z-1", "ZD;id"):` | Starts a loop over six names that are not valid step names of round 4: step names of older rounds, a lower-case letter, the letter `Z` alone, a hyphen, and a name with a semicolon and a command. |
| 1168 | `        rc, out, err = box.run(["--dry-run", name], SESSION="1")` | Runs the script in a dry run with that name. |
| 1169 | `        check("step name '%s' is refused with status 2" % name, rc == 2 and "unknown step" in err and not out, (rc, err))` | Check, once per name: exit status 2, the message `unknown step` in the error output, and no output. So only a name of the right form can select a schedule, and a name cannot hold a shell command that would run. |
| 1170 | `    rc, out, err = box.run(["--dry-run", "ZZ9"], SESSION="1")` | Runs a dry run with `ZZ9`, a name of the right form for which no schedule exists. |
| 1171 | `    check("a name of the right form without a schedule: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))` | Check: exit status 2 and the message `missing schedule`. |
| 1172 | `    rc, out, err = box.run(["--dry-run", "ZD", "ZD"], SESSION="1")` | Runs a dry run that names `ZD` twice. |
| 1173 | `    check("a step named twice: status 2", rc == 2 and "twice" in err and "step ZD" not in out, (rc, err))` | Check: exit status 2, the word `twice` in the error output, and no summary of `ZD` in the output. So one call cannot run the processes of a step a second time. |
| 1174 | `    rc, out, err = box.run(["--dry-run"] + ALL_STEPS, SESSION="1", BWX8_BIN=absent, BWX10_BIN=absent, BWX11_BIN=absent)` | Runs a dry run of all 5 steps of session 1. The three binary paths point to a file that does not exist. |
| 1175 | `    want = {"ZA": "6 processes, nominal kernel work 0.078 s", "ZD": "216 processes, nominal kernel work 20.736 s",` | `want`: the summary text that the dry run must print per step. The schedule has the test divisor 100, so `ZA` has 0.078 s and `ZD` 20.736 s of nominal kernel work. |
| 1176 | `            "ZC": "32 processes, nominal kernel work 1.920 s", "ZN": "144 processes, nominal kernel work 13.824 s",` | Continues: `ZC` with 1.920 s and `ZN` with 13.824 s. |
| 1177 | `            "ZM": "40 processes, nominal kernel work 12.000 s"}` | Ends the dictionary: `ZM` with 12.000 s. Each value is the real value of the task divided by 100. |
| 1178 | `    check("--dry-run of all 5 steps, session 1, without the binaries and without counter settings: status 0, the counts of each step "` | Starts a check: a dry run of all steps of session 1 works without the binaries and without counter settings. |
| 1179 | `          "(6, 216, 32, 144, 40)",` | Continues the name: the process counts 6, 216, 32, 144 and 40. |
| 1180 | `          rc == 0 and all(("step %s session 1: %s" % kv) in out for kv in want.items())` | The test, first half: exit status 0, and the output holds the expected summary text of every step. So the script adds up the same counts and the same nominal work as the generator. |
| 1181 | `          and out.count("\nbwx11 --trial ") == 438 and "\nbwx8 " not in out and "\nbwx10 " not in out and "warning" in err,` | Second half: the output has 438 command lines that start with `bwx11 --trial`, no command line of `bwx8` or `bwx10`, and the error output holds a warning about the test settings. |
| 1182 | `          (rc, out[:300], err[-300:]))` | The detail for a failure. |
| 1183 | `    check("--dry-run: the command lines are the binary word of the step and the args column",` | Starts a check: the command lines of the dry run are the word of the binary and the `args` column. |
| 1184 | `          all(("bwx11 %s  # idx %s, tag %s, nominal " % (r[5], r[0], r[1])) in out` | The test, first half: for every schedule row of every step the output holds the line made of `bwx11`, the `args` of the row, and the comment with the `idx` and the tag. |
| 1185 | `              for st in want for r in box.rows(st)) and out.count(" --pmu-type 11 --events ") == 32` | The loop of that test. Then: the option pair `--pmu-type 11 --events` occurs 32 times, once per process of `ZC`. |
| 1186 | `          and out.count(" --rec-pad ") == 40 and out.count(" --evict-mb 512") == 126 and out.count(" --trace") == 6)` | Ends the test: `--rec-pad` occurs 40 times (`ZM`), `--evict-mb 512` 126 times and `--trace` 6 times (`ZA`). So a person can read the exact commands of a session before it runs. |
| 1187 | `    check("--dry-run: the binary of each step is printed (bwx11 for every step)",` | Starts a check: the dry run prints the binary of each step. |
| 1188 | `          sorted(re.findall(r"^step (\S+) binary: (\S+)$", out, re.M)) == sorted((st, "bwx11") for st in TABLE), out[:500])` | The test: the lines of the form `step NAME binary: WORD` give `bwx11` for each of the 5 steps. The two groups of the pattern hold the step name and the word. |
| 1189 | `    check("--dry-run: no host sampler is announced", "host sampler" not in out)` | Check: the output of the dry run does not hold the words `host sampler`. No step of the schedule has a `.watch` file. |
| 1190 | `    check("--dry-run: starts nothing and makes no result folder", not box.launched() and not os.path.exists(box.results))` | Check: the dry run started no dummy and made no result folder. |
| 1191 | `    rc, out, err = box.run(["--dry-run", "ZD", "ZC", "ZN", "ZM"], SESSION="2")` | Runs a dry run of the four steps of session 2. |
| 1192 | `    check("--dry-run session 2: the first command line of each step uses CPU 41, and the steps hold 432 processes",` | Starts a check: in session 2 the first command line of each step uses CPU 41, and the steps hold 432 processes. |
| 1193 | `          rc == 0 and len(re.findall(r"# ---- step \S+ session 2 ----\n.*\n.*\n.*\nbwx11 --trial --cpus 41 ", out)) == 4` | The test: exit status 0, and a pattern matches 4 times. The pattern is the heading line of a step for session 2, three more lines, and then a command line that starts with `bwx11 --trial --cpus 41`. |
| 1194 | `          and out.count("\nbwx11 --trial ") == 432, (rc, out[:500]))` | Ends the test: 432 command lines in all. So the script reads the schedules of the session that `SESSION` names, with the reversed CPU order. |
| 1195 | `    rc, out, err = box.run(["--dry-run", "ZA"], SESSION="2")` | Runs a dry run of `ZA` for session 2. |
| 1196 | `    check("ZA in session 2: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))` | Check: exit status 2 and `missing schedule`. The acceptance step exists in session 1 only. |
| 1197 | `    rc, out, err = box.run(["--dry-run", "ZD"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX10_BIN=None,` | Runs a dry run of `ZD` with every test variable taken out of the environment. |
| 1198 | `                           BWX11_BIN=None, BWX8_RESULTS=None)` | Continues the call. |
| 1199 | `    check("no warning without the test settings", rc == 0 and "warning" not in err, err)` | Check: exit status 0 and no warning. The warnings appear only for test settings. |
| 1200 | `    rc, out, err = box.run(["--dry-run", "ZD"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX10_BIN=None,` | Runs the same dry run with `BWX11_BIN` left in the environment. |
| 1201 | `                           BWX8_RESULTS=None)` | Continues the call. |
| 1202 | `    check("BWX11_BIN alone gives its warning", rc == 0 and err.count("warning") == 1 and "BWX11_BIN" in err, err)` | Check: exactly one warning, and it names `BWX11_BIN`. So a test path for the new binary cannot be used on CRB without a visible warning. |

### `run_checks`: a normal run of step `ZA` (lines 1204 to 1235)

| Line | Source | Explanation |
|---:|---|---|
| 1204 | `    # ---- a normal run of a bwx11 step: ZA ----` | Comment: a normal run of a step that uses `bwx11`, the step `ZA`. |
| 1205 | `    rows = box.rows("ZA")` | `rows`: the schedule rows of `ZA`. |
| 1206 | `    rc, out, err = box.run(["ZA"], SESSION="1", STOP_AT="none")` | Runs the script for real: the step `ZA`, session 1, no stop time. The binaries are the dummies. |
| 1207 | `    f = box.folder()` | `f`: the one result folder of the case. |
| 1208 | `    csv = box.csv("ZA")` | `csv`: the content of the output file `ZA.csv`. |
| 1209 | `    heads = re.findall(r"^-- step ZA session 1 idx (\d+) tag (\S+) waited_s \d+ loadavg .* logins \d+ utc \S+ args (.*)$", csv, re.M)` | `heads`: the header lines of the processes in that file. The pattern matches a line that starts with `-- step ZA session 1 idx`. Its three groups hold the `idx`, the tag and the text after `args`. |
| 1210 | `    check("ZA normal end: status 0, the counts are printed before the result folder is made",` | Starts a check of the normal end: exit status 0, and the counts are printed before the result folder is made. |
| 1211 | `          rc == 0 and 0 <= out.find("step ZA session 1: 6 processes") < out.find("result folder: "), (rc, err, out))` | The test: the summary line of the step stands in the output before the line `result folder:`. The design asks that the runner print the counts before execution. |
| 1212 | `    check("ZA normal end: folder name bwx11-ZA-s1-<UTC> and its six files, no sampler file",` | Starts a check: the name of the result folder and its files. |
| 1213 | `          f is not None and re.match(r"^bwx11-ZA-s1-\d{8}T\d{6}Z$", os.path.basename(f)) is not None` | The test: the folder name is `bwx11-ZA-s1-`, 8 digits, `T`, 6 digits and `Z`. |
| 1214 | `          and sorted(os.listdir(f)) == ["ZA.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv", "stderr.txt"],` | Continues: the folder holds exactly six files: the output file, `build.txt`, `env.txt`, `launches.txt`, `schedule.tsv` and `stderr.txt`. There is no file of the host sampler. |
| 1215 | `          f and os.listdir(f))` | The detail for a failure: the folder and its files. |
| 1216 | `    check("ZA normal end: one header line per process in schedule order, each followed by its output; schedule.tsv is a copy",` | Starts a check: one header line per process in schedule order, each followed by its output, and `schedule.tsv` is a copy. |
| 1217 | `          heads == [(r[0], r[1], r[5]) for r in rows] and csv.count("M,dummy,bwx11\n") == 6 and "-- killed" not in csv` | The test: the header lines give the `idx`, the tag and the `args` of the schedule rows, in order. The output row of the dummy `bwx11` occurs 6 times. No line says `-- killed`. |
| 1218 | `          and "-- failed" not in csv and box.file("schedule.tsv") == open(box.sched("s1", "ZA.tsv")).read(), heads)` | Ends the test: no line says `-- failed`, and `schedule.tsv` is equal to the schedule file. This proves that the script runs each process once, in the order of the schedule, and keeps the schedule beside the results. |
| 1219 | `    launched = [l for l in box.launched() if not l.endswith(" sleep")]` | `launched`: the lines of the dummy log without the lines of the sleeps: one line per launch. |
| 1220 | `    check("ZA normal end: the binary gets the args column (--trace, --evict-mb 512), no counter setting in its environment",` | Starts a check: the binary gets the `args` column, and no counter setting is in its environment. |
| 1221 | `          [l.split(" ", 1)[1] for l in launched] == [r[5] for r in rows] and launched[0].endswith(".plan --trace")` | The test: the arguments of each launch are the `args` of its row. The first launch ends with the plan path and `--trace`. |
| 1222 | `          and launched[1].endswith(" --trace --evict-mb 512") and launched[2].endswith(" --trace --evict-mb 512")` | Continues: the second and the third launch end with `--trace --evict-mb 512`. |
| 1223 | `          and open(box.log + ".env").read() == "PMU= EV=\n" * 6 and box.none_alive(), launched)` | Ends the test: each of the 6 dummies saw empty counter settings, and no process is left after the run. So the script passes the options on unchanged and adds nothing of its own. |
| 1224 | `    check("ZA normal end: every process is the binary named bwx11, and build.txt is the build record beside it",` | Starts a check: every process is the binary with the word `bwx11`, and `build.txt` is the build record beside it. |
| 1225 | `          box.binaries() == [box.bin11] * 6 and box.file("build.txt") == "dummy build record of bwx11\n", box.binaries()[:2])` | The test: all 6 launches used the dummy `bwx11`, and the copied `build.txt` is the record of that dummy. |
| 1226 | `    env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1227 | `    check("ZA normal end: env.txt holds session, from, load, the word and the digests of the binary, of run_bwx11.sh, of the schedule "` | Starts a check of `env.txt`. The name lists what it must hold: the session, the `--from` value, the load, the word and the digests of the binary, of `run_bwx11.sh`, of the schedule and of the build record. |
| 1228 | `          "and of the build record, the three digest settings, paths, end line",` | Continues the name: the three digest settings, the paths and the end line. |
| 1229 | `          "session=1 from=0 " in env and "loadavg=" in env and "## end utc=" in env and "/run_bwx11.sh\n" in env` | The test: the session and `from=0`, a load average, the end line, and a checksum line for `run_bwx11.sh`. |
| 1230 | `          and "/sched11/s1/ZA.tsv\n" in env and "host sampler" not in env and " BWX8_SHA256= BWX10_SHA256= BWX11_SHA256= binary=bwx11 " in env` | Continues: a checksum line for the schedule file, no line about a host sampler, and the three empty digest settings followed by `binary=bwx11`. |
| 1231 | `          and ("%s  %s\n" % (sha256(box.bin11), box.bin11)) in env` | Continues: the line with the sha256 and the path of the dummy `bwx11`. The test computes the sha256 itself. |
| 1232 | `          and ("%s  %s\n" % (sha256(os.path.join(box.dir, "build.txt")), os.path.join(box.dir, "build.txt"))) in env` | Continues: the line with the sha256 and the path of its `build.txt`. |
| 1233 | `          and (" MARKER=%s STOPFILE=%s BIN=%s RESULTS=%s\n" % (box.marker, box.stopfile, box.bin11, box.results)) in env` | Continues: the paths in use, which are the test paths of this case. |
| 1234 | `          and box.file("launches.txt").count("== ZA.csv idx ") == 6, env)` | Ends the test: `launches.txt` holds 6 load records, one per launch. This proves that a result folder records which files ran, with which settings, and the load before every launch. |

### `run_checks`: the binary of a step (lines 1236 to 1297)

| Line | Source | Explanation |
|---:|---|---|
| 1236 | `    # ---- the binary of a step. The schedules name bwx11 for every step. From here to the end of the stop controls the` | Comment: the checks of the binary of a step. The schedules name `bwx11` for every step. |
| 1237 | `    # ---- .bin file of ZM holds bwx8 and that of ZC holds bwx10, so every word is tested with a step. ----` | Continues the comment: from here to the end of the stop controls, the `.bin` file of `ZM` holds `bwx8` and that of `ZC` holds `bwx10`. So each of the three words is tested with a step. |
| 1238 | `    box.set_bin("ZM", "bwx8\n")` | Writes `bwx8` into the `.bin` file of `ZM`. |
| 1239 | `    box.set_bin("ZC", "bwx10\n")` | Writes `bwx10` into the `.bin` file of `ZC`. |
| 1240 | `    word_of = {"ZM": "bwx8", "ZC": "bwx10", "ZA": "bwx11"}` | `word_of`: the word that each of the three steps uses from here on. |
| 1241 | `    for step in ("ZM", "ZC"):` | Starts a loop over `ZM` and `ZC`. |
| 1242 | `        word = word_of[step]` | `word`: the word of the step. |
| 1243 | `        rc, out, err = box.run(["--from", str(last[step] - 1), step], SESSION="1", STOP_AT="none")` | Runs the last two processes of the step, with `--from` set to the last `idx` minus 1. |
| 1244 | `        env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1245 | `        check("%s with the word %s: the two processes are that binary, build.txt is the record from its folder, env.txt names it"` | Starts a check per step: the two processes are the binary of that word, `build.txt` is the record from its folder, and `env.txt` names it. |
| 1246 | `              % (step, word),` | The values for the name of the check. |
| 1247 | `              rc == 0 and box.binaries() == [box.bin[word]] * 2 and box.file("build.txt") == "dummy build record of %s\n" % word` | The test: exit status 0, both launches used the dummy of the word, and `build.txt` is the record of that dummy. |
| 1248 | `              and (" binary=%s " % word) in env and (" BIN=%s RESULTS=" % box.bin[word]) in env` | Continues: `env.txt` names the word and the path of the binary. |
| 1249 | `              and ("%s  %s\n" % (sha256(box.bin[word]), box.bin[word])) in env` | Continues: `env.txt` holds the sha256 line of that binary. |
| 1250 | `              and ("  %s\n" % os.path.join(os.path.dirname(box.bin[word]), "build.txt")) in env` | Continues: `env.txt` holds a checksum line for the `build.txt` of the folder of that binary. |
| 1251 | `              and os.path.basename(box.folder() or "").startswith("bwx11-%s-s1-" % step)` | Continues: the result folder still starts with `bwx11-`, the step and `-s1-`. The name of the folder does not depend on the binary. |
| 1252 | `              and box.csv(step).count("M,dummy,%s\n" % word) == 2` | Continues: the output row of that dummy occurs twice in the output file. |
| 1253 | `              and ("to run from idx %d: 2 processes" % (last[step] - 1)) in out and ("step %s binary: %s\n" % (step, word)) in out,` | Ends the test: the output says that 2 processes run from that `idx`, and it prints the word of the binary. This proves that the word in the `.bin` file selects the binary, and that the result folder shows which binary ran. |
| 1254 | `              (rc, err, box.binaries()))` | The detail for a failure. |
| 1255 | `    # The three words in one call: the schedules of ZM, ZC and ZA are cut to their first two rows for this case.` | Comment: the next case uses the three words in one call. For it the schedules of `ZM`, `ZC` and `ZA` are cut to their first two rows. |
| 1256 | `    saved = {st: open(box.sched("s1", st + ".tsv")).read() for st in ("ZM", "ZC", "ZA")}` | `saved`: the full text of the three schedule files, kept for later. |
| 1257 | `    for st, text in saved.items():` | Starts a loop over the saved texts. |
| 1258 | `        with open(box.sched("s1", st + ".tsv"), "w") as fh:` | Opens the schedule file for writing. |
| 1259 | `            fh.write("\n".join(text.split("\n")[:3]) + "\n")` | Writes its first three lines only: the header row and two processes. |
| 1260 | `    rc, out, err = box.run(["ZM", "ZC", "ZA"], SESSION="1", STOP_AT="none")` | Runs the three steps in one call. |
| 1261 | `    fl = box.folders()` | `fl`: the result folders of the case, sorted by name. |
| 1262 | `    check("one call with a bwx8 step, a bwx10 step and a bwx11 step: each step starts its own binary and copies its own build record",` | Starts a check: in one call with a `bwx8` step, a `bwx10` step and a `bwx11` step, each step starts its own binary and copies its own build record. |
| 1263 | `          rc == 0 and box.binaries() == [box.bin8] * 2 + [box.bin10] * 2 + [box.bin11] * 2 and len(fl) == 3` | The test: exit status 0. The six launches used the dummy `bwx8` twice, then `bwx10` twice, then `bwx11` twice. There are three result folders. |
| 1264 | `          and all(("bwx11-%s-s1-" % st) in fl[i] and open(os.path.join(fl[i], "build.txt")).read() == "dummy build record of %s\n" % w` | Continues: each folder has the name of its step and holds the build record of the binary of that step. |
| 1265 | `                  for i, (st, w) in enumerate((("ZA", "bwx11"), ("ZC", "bwx10"), ("ZM", "bwx8")))),` | The loop of that test: the folders in sorted order belong to `ZA`, `ZC` and `ZM`. |
| 1266 | `          (rc, err, box.binaries(), fl))` | The detail for a failure. |
| 1267 | `    for st, text in saved.items():` | Starts a loop over the saved texts. |
| 1268 | `        with open(box.sched("s1", st + ".tsv"), "w") as fh:` | Opens the schedule file for writing. |
| 1269 | `            fh.write(text)` | Writes the full text back. |
| 1270 | `    for step, path, where in (("ZM", box.home8, "$HOME/cache-perf/bwx8-20261114/bwx8"),` | Starts a loop over three cases without the test settings for the binaries. First: the step `ZM` must use the dummy at the path below the home folder that the script uses for `bwx8` on CRB. |
| 1271 | `                              ("ZC", box.home10, "$HOME/cache-perf/bwx10-20261115/bwx10"),` | Second: the step `ZC` must use the dummy at the path for `bwx10`. |
| 1272 | `                              ("ZA", box.bin11, "bwx11 beside run_bwx11.sh")):` | Third: the step `ZA` must use the file `bwx11` beside the script. |
| 1273 | `        word = word_of[step]` | `word`: the word of the step. |
| 1274 | `        rc, out, err = box.run(["--from", str(last[step]), step], SESSION="1", STOP_AT="none", BWX8_BIN=None, BWX10_BIN=None,` | Runs the last process of the step without the three test settings for the binaries. |
| 1275 | `                               BWX11_BIN=None, HOME=box.home)` | Continues the call: the home folder is the prepared one. |
| 1276 | `        check("without the test settings the word %s is %s, with the build record of that folder" % (word, where),` | Starts a check per case: without the test settings the word stands for the fixed path, and the build record comes from that folder. |
| 1277 | `              rc == 0 and box.binaries() == [path] and box.file("build.txt") == "dummy build record of %s\n" % word` | The test: exit status 0, the one launch used the binary at that path, and `build.txt` is its record. |
| 1278 | `              and (" BIN=%s RESULTS=" % path) in box.file("env.txt"), (rc, err, box.binaries()))` | Ends the test: `env.txt` names that path. This proves the default paths that are used on CRB. The other checks only use the test paths. |
| 1279 | `    made = os.path.join(box.dir, "made-by-bin")` | `made`: the path of a file that must never appear. |
| 1280 | `    for what, content in (("another word", "bwx9\n"), ("two words", "bwx8 bwx11\n"), ("two lines", "bwx8\nbwx11\n"), ("nothing", ""),` | Starts a loop over six wrong contents of a `.bin` file. This line: another word, two words, two lines and an empty file. |
| 1281 | `                          ("a path", "/bin/true\n"), ("a command", "$(touch %s)\n" % made)):` | Continues the list: a path, and a command substitution that would create the file `made`. |
| 1282 | `        box.set_bin("ZM", content)` | Writes the wrong content into the `.bin` file of `ZM`. |
| 1283 | `        rc, out, err = box.run(["--from", "39", "ZM"], SESSION="1", STOP_AT="none")` | Runs the last process of `ZM` for real. |
| 1284 | `        rc2, out2, err2 = box.run(["--dry-run", "ZM"], SESSION="1")` | Runs a dry run of `ZM` too. |
| 1285 | `        check("ZM.bin with %s: status 2 in a run and in a dry run, nothing starts, no result folder" % what,` | Starts a check per content: exit status 2 in a run and in a dry run, nothing starts, and no result folder is made. |
| 1286 | `              rc == 2 and rc2 == 2 and "must hold the one word bwx8, bwx10 or bwx11" in err and "must hold" in err2` | The test: both statuses are 2, and both error outputs hold the message about the one word. |
| 1287 | `              and not box.launched() and not os.path.exists(box.results) and not os.path.exists(made) and "bwx" not in out2, (rc, err, rc2))` | Ends the test: no launch and no result folder in the last case, the file `made` does not exist, and the output of the dry run names no binary. The log and the result path that are tested here belong to the last case that was started, which is the dry run. This proves that only an exact word of the list can select a program, and that the content of the file is never run as a command. |
| 1288 | `    os.remove(box.sched("s1", "ZM.bin"))` | Removes the `.bin` file of `ZM` in session 1. |
| 1289 | `    rc, out, err = box.run(["ZA", "ZM"], SESSION="1", STOP_AT="none")` | Runs `ZA` and then `ZM` in one call. |
| 1290 | `    check("ZM.bin missing, ZM second in the call: status 2 before the first process of the call",` | Starts a check: with the `.bin` file of the second step missing, the script ends with status 2 before the first process of the call. |
| 1291 | `          rc == 2 and "ZM.bin (the binary of step ZM)" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the error output names the missing file, no launch, and no result folder. So the script finds a missing file of a later step before it uses machine time for an earlier step. |
| 1292 | `    for word in ("bwx11", "bwx10", "bwx8"):` | Starts a loop over the three words. |
| 1293 | `        box.set_bin("ZM", word + "\n")` | Writes the word into the `.bin` file of `ZM`. |
| 1294 | `        rc, out, err = box.run(["--from", "39", "ZM"], SESSION="1", STOP_AT="none")` | Runs the last process of `ZM`. |
| 1295 | `        check("the word decides, not the step name: ZM.bin with %s starts the binary %s" % (word, word),` | Starts a check per word: the word decides, and not the step name. |
| 1296 | `              rc == 0 and box.binaries() == [box.bin[word]] and (" binary=%s " % word) in box.file("env.txt"), (rc, err))` | The test: exit status 0, the launch used the dummy of that word, and `env.txt` names the word. After the loop the `.bin` file of `ZM` holds `bwx8` again. |

### `run_checks`: the digest checks, missing binaries and a missing build record (lines 1298 to 1348)

| Line | Source | Explanation |
|---:|---|---|
| 1298 | `    # ---- the digests (ZM uses bwx8, ZC uses bwx10, ZA uses bwx11) ----` | Comment: the checks of the digests. In the box `ZM` uses `bwx8`, `ZC` uses `bwx10` and `ZA` uses `bwx11`. |
| 1299 | `    dig = {w: sha256(box.bin[w]) for w in box.bin}` | `dig`: the sha256 of each of the three dummy binaries. |
| 1300 | `    zero = "0" * 64` | `zero`: a text of 64 zeros, a digest that fits no file. |
| 1301 | `    check("the three dummy binaries differ, so each digest names one of them", len(set(dig.values())) == 3)` | Check: the three dummy binaries have three different digests. So each digest names exactly one of them, and a check with the digest of another binary can fail. |
| 1302 | `    one_proc = {"ZM": ["--from", "39", "ZM"], "ZC": ["--from", "31", "ZC"], "ZA": ["--from", "5", "ZA"]}` | `one_proc`: for each of the three steps the arguments that run its last process only: `--from` with the last `idx`, and the step. |
| 1303 | `    cases = []` | `cases`: the list of test cases, empty at first. A case is a name, the arguments, the digest settings and the expected exit status. |
| 1304 | `    for step, word in sorted(word_of.items()):` | Starts a loop over the three steps with their words. |
| 1305 | `        var = word.upper() + "_SHA256"` | `var`: the name of the digest setting of that word, for example `BWX8_SHA256`. |
| 1306 | `        others = sorted(w for w in dig if w != word)` | `others`: the two other words. |
| 1307 | `        cases.append(("%s wrong, a %s step (%s)" % (var, word, step), one_proc[step], {var: zero}, 2))` | Case 1: the digest of the binary of the step is wrong. Expected: status 2. |
| 1308 | `        cases.append(("%s right, a %s step (%s)" % (var, word, step), one_proc[step], {var: dig[word]}, 0))` | Case 2: the digest of the binary of the step is right. Expected: status 0. |
| 1309 | `        cases.append(("%s holds the digest of %s, a %s step (%s)" % (var, others[0], word, step), one_proc[step],` | Case 3: all three settings hold the digest of another binary. Expected: status 2. |
| 1310 | `                      {w.upper() + "_SHA256": dig[others[0]] for w in dig}, 2))` | Continues case 3. It shows that a digest is compared with the binary of its own word. |
| 1311 | `        cases.append(("the digests of %s and %s wrong, a %s step only (%s; a binary that is not used is not checked)"` | Case 4: the digests of the two other binaries are wrong, and the digest of the binary of the step is not set. Expected: status 0. A binary that the call does not use is not checked. |
| 1312 | `                      % (others[0], others[1], word, step), one_proc[step], {w.upper() + "_SHA256": zero for w in others}, 0))` | Continues case 4. |
| 1313 | `        cases.append(("all three right, a %s step (%s)" % (word, step), one_proc[step], {w.upper() + "_SHA256": dig[w] for w in dig}, 0))` | Case 5: all three digests are right. Expected: status 0. |
| 1314 | `    right = {w.upper() + "_SHA256": dig[w] for w in dig}` | `right`: the three settings with the right digests. |
| 1315 | `    cases += [("BWX11_SHA256 right and BWX8_SHA256 wrong, a call with ZA then ZM", ["ZA", "ZM"], dict(right, BWX8_SHA256=zero), 2),` | Three more cases with several steps in one call. First: the digest of `bwx8` is wrong, in a call with `ZA` and then `ZM`. Expected: status 2. |
| 1316 | `              ("BWX8_SHA256 right and BWX10_SHA256 wrong, a call with ZM then ZC", ["ZM", "ZC"], dict(right, BWX10_SHA256=zero), 2),` | Second: the digest of `bwx10` is wrong, in a call with `ZM` and then `ZC`. Expected: status 2. |
| 1317 | `              ("BWX8_SHA256 and BWX10_SHA256 right and BWX11_SHA256 wrong, a call with ZM, ZC, then ZA", ["ZM", "ZC", "ZA"],` | Third: the digest of `bwx11` is wrong, in a call with `ZM`, `ZC` and then `ZA`. |
| 1318 | `               dict(right, BWX11_SHA256=zero), 2)]` | Ends the third case. Expected: status 2. In each of these calls the wrong binary belongs to the last step. |
| 1319 | `    for name, args, env_, want_rc in cases:` | Starts the loop over the cases. |
| 1320 | `        rc, out, err = box.run(args, SESSION="1", STOP_AT="none", **env_)` | Runs the script with the arguments and the digest settings of the case. |
| 1321 | `        if want_rc:` | A case that must be refused. |
| 1322 | `            check("%s: status 2 before the first process of the call, no result folder" % name,` | Starts a check per such case: status 2 before the first process of the call, and no result folder. |
| 1323 | `                  rc == 2 and "is not the binary with the digest given for it" in err and not box.launched()` | The test: exit status 2, and the error output says that the binary is not the one with the digest given for it. |
| 1324 | `                  and not os.path.exists(box.results), (rc, err))` | Ends the test: no dummy was started, and no result folder exists. This proves that a binary other than the accepted one cannot run when its digest is given. The refusal comes before any step, also when the wrong binary belongs to a later step. |
| 1325 | `        else:` | A case that must run. |
| 1326 | `            e = box.file("env.txt")` | `e`: the content of `env.txt`. |
| 1327 | `            check("%s: runs, and env.txt records the three settings" % name,` | Starts a check per such case: the process runs, and `env.txt` records the three digest settings. |
| 1328 | `                  rc == 0 and len(box.launched()) == 2 and (" BWX8_SHA256=%s BWX10_SHA256=%s BWX11_SHA256=%s binary=" % (` | The test: exit status 0, one launch (two lines in the dummy log), and the settings line of `env.txt` holds the three values as they were given. |
| 1329 | `                      env_.get("BWX8_SHA256", ""), env_.get("BWX10_SHA256", ""), env_.get("BWX11_SHA256", ""))) in e, (rc, err))` | The values for that comparison. A setting that was not given is recorded as empty. |
| 1330 | `    rc, out, err = box.run(["--dry-run", "ZM", "ZC", "ZA"], SESSION="1", BWX8_SHA256=zero, BWX10_SHA256=zero, BWX11_SHA256=zero)` | Runs a dry run of the three steps with three wrong digests. |
| 1331 | `    check("a dry run checks no digest", rc == 0, (rc, err))` | Check: the dry run ends with status 0. A dry run checks no digest, and it does not need the binaries. |
| 1332 | `    for step, word in sorted(word_of.items()):` | Starts a loop over the three steps with their words. |
| 1333 | `        var = word.upper() + "_BIN"` | `var`: the name of the test setting for the path of that binary. |
| 1334 | `        rc, out, err = box.run(one_proc[step], SESSION="1", STOP_AT="none", **{var: absent})` | Runs the last process of the step with that path set to a file that does not exist. |
| 1335 | `        check("the binary of the step is missing (%s, step %s): status 2" % (word, step),` | Starts a check per step: the binary of the step is missing, and the script ends with status 2. |
| 1336 | `              rc == 2 and "missing" in err and word in err and not box.launched(), (rc, err))` | The test: exit status 2, the error output holds `missing` and the word, and nothing was started. |
| 1337 | `    rc, out, err = box.run(one_proc["ZA"], SESSION="1", STOP_AT="none", BWX8_BIN=absent, BWX10_BIN=absent)` | Runs the last process of `ZA` with the paths of `bwx8` and `bwx10` set to a file that does not exist. |
| 1338 | `    check("a missing bwx8 and a missing bwx10 do not stop a call that uses bwx11 only", rc == 0 and len(box.launched()) == 2, (rc, err))` | Check: the run works. A missing `bwx8` and a missing `bwx10` do not stop a call that uses `bwx11` only. |
| 1339 | `    rc, out, err = box.run(["ZM", "ZA"], SESSION="1", STOP_AT="none", BWX11_BIN=absent)` | Runs `ZM` and then `ZA` with the path of `bwx11` set to a file that does not exist. |
| 1340 | `    check("the binary of the second step is missing (bwx11): status 2 before the first process of the call",` | Starts a check: the binary of the second step is missing, and the script ends with status 2 before the first process of the call. |
| 1341 | `          rc == 2 and "missing" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the word `missing` in the error output, no launch and no result folder. |
| 1342 | `    os.rename(os.path.join(os.path.dirname(box.bin10), "build.txt"), os.path.join(os.path.dirname(box.bin10), "build.moved"))` | Renames the file `build.txt` beside the dummy `bwx10`, so the build record is missing. |
| 1343 | `    rc, out, err = box.run(one_proc["ZC"], SESSION="1", STOP_AT="none")` | Runs the last process of `ZC`, the step that uses `bwx10`. |
| 1344 | `    rc2, out2, err2 = box.run(one_proc["ZA"], SESSION="1", STOP_AT="none")` | Runs the last process of `ZA`, the step that uses `bwx11`. |
| 1345 | `    check("build.txt missing beside bwx10: a bwx10 step stops with status 2, a bwx11 step runs",` | Starts a check: without `build.txt` beside `bwx10`, a step of `bwx10` stops with status 2, and a step of `bwx11` runs. |
| 1346 | `          rc == 2 and "build.txt" in err and rc2 == 0 and len(box.launched()) == 2, (rc, err, rc2, err2))` | The test: the first run ended with status 2 and its error output names `build.txt`. The second run ended with status 0 and started its process. So no result folder is made without the record of the build of its binary. |
| 1347 | `    os.rename(os.path.join(os.path.dirname(box.bin10), "build.moved"), os.path.join(os.path.dirname(box.bin10), "build.txt"))` | Gives the file its name back. |

### `run_checks`: the counter settings and the host sampler (lines 1349 to 1394)

| Line | Source | Explanation |
|---:|---|---|
| 1349 | `    # ---- the rule for the counter settings ----` | Comment: the checks of the rule for the counter settings start here. |
| 1350 | `    tsv = box.sched("s1", "ZC.tsv")` | `tsv`: the schedule file of `ZC` in session 1 of the box. |
| 1351 | `    saved_zc = open(tsv).read()` | `saved_zc`: its text, kept for later. |
| 1352 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1353 | `        fh.write(re.sub(r" --pmu-type 11 --events \S+", "", saved_zc))` | Writes the schedule without the options `--pmu-type 11` and `--events` in every row. The pattern matches the two options and the event list, which is the text up to the next blank. |
| 1354 | `    rc, out, err = box.run(["ZC"], SESSION="1", STOP_AT="none")` | Runs the step `ZC` with this schedule and without counter settings in the environment. |
| 1355 | `    check("a counted step without the options in args and without BWX_PMU_TYPE and BWX_EVENTS: status 2, nothing starts",` | Starts a check: a step that uses counters, without the options in the `args` and without the two environment settings, ends with status 2 and starts nothing. |
| 1356 | `          rc == 2 and "needs BWX_PMU_TYPE" in err and not box.launched() and open(tsv).read() != saved_zc, (rc, err))` | The test: exit status 2, the message that the step needs `BWX_PMU_TYPE`, no launch, and the schedule file really differs from the saved text. Without this refusal the first process of the step would start and then fail in the runner, and the run script would stop there with exit status 1. |
| 1357 | `    rc, out, err = box.run(["ZC"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11")` | Runs the same with `BWX_PMU_TYPE` only. |
| 1358 | `    check("the same with BWX_PMU_TYPE only: status 2, nothing starts", rc == 2 and "needs BWX_EVENTS" in err and not box.launched(), (rc, err))` | Check: exit status 2, the message that the step needs `BWX_EVENTS`, and no launch. Both settings are needed. |
| 1359 | `    rc, out, err = box.run(["--from", "31", "ZC"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11", BWX_EVENTS="a=0x11")` | Runs the last process of `ZC` with both settings in the environment. |
| 1360 | `    check("the same with both settings: runs, and the binary finds them in its environment",` | Starts a check: with both settings the process runs, and the binary finds them in its environment. |
| 1361 | `          rc == 0 and len(box.launched()) == 2 and open(box.log + ".env").read() == "PMU=11 EV=a=0x11\n", (rc, err))` | The test: exit status 0, one launch, and the dummy recorded `PMU=11` and the event text. So the script exports the two settings to the runner. |
| 1362 | `    rc, out, err = box.run(["--dry-run", "ZC"], SESSION="1", BWX_PMU_TYPE="eleven", BWX_EVENTS="a=0x11")` | Runs a dry run with `BWX_PMU_TYPE` set to the word `eleven`. |
| 1363 | `    check("BWX_PMU_TYPE that is not a whole number: status 2", rc == 2 and "whole number" in err, (rc, err))` | Check: exit status 2 and the words `whole number`. The type number must hold digits only. |
| 1364 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1365 | `        fh.write(saved_zc)` | Writes the saved text back. |
| 1366 | `    rc, out, err = box.run(["--from", "31", "ZC"], SESSION="1", STOP_AT="none")` | Runs the last process of `ZC` as scheduled, without counter settings in the environment. |
| 1367 | `    check("ZC as scheduled (options in args) needs no counter setting: runs with --pmu-type 11 and the 6 events on the command line",` | Starts a check: `ZC` as scheduled, with the options in the `args`, needs no counter setting. |
| 1368 | `          rc == 0 and len(box.launched()) == 2 and box.launched()[0].endswith(" --pmu-type 11 --events " + EVENTS)` | The test: exit status 0, one launch, and the command line of the dummy ends with `--pmu-type 11 --events` and the 6 events. |
| 1369 | `          and open(box.log + ".env").read() == "PMU= EV=\n", (rc, err))` | Ends the test: the dummy saw empty counter settings in its environment. So the options of the schedule alone give the counter settings to the runner. |
| 1370 | `    rc, out, err = box.run(["--from", "215", "ZD"], SESSION="1", STOP_AT="none")` | Runs the last process of `ZD`, the process with the `idx` 215. |
| 1371 | `    check("an uncounted step (ZD, count closed) needs no counter setting: runs",` | Starts a check: a step without counters (`ZD`, counters closed) needs no counter setting and runs. |
| 1372 | `          rc == 0 and len(box.launched()) == 2 and "--plan sched11/s1/ZD/0215.plan" in box.launched()[0]` | The test: exit status 0, one launch, and the launch got the plan `0215.plan` of session 1. |
| 1373 | `          and re.findall(r"^-- step ZD session 1 idx (\d+) ", box.csv("ZD"), re.M) == ["215"]` | Continues: the output file holds exactly one header line, for the `idx` 215. |
| 1374 | `          and " from=215 " in box.file("env.txt") and "to run from idx 215: 1 processes" in out, (rc, err))` | Ends the test: `env.txt` records `from=215`, and the output says that 1 process runs from that `idx`. This also proves that `--from` runs the named process and no earlier one. |
| 1376 | `    # ---- the host sampler is still started by a .watch file (no schedule of round 4 has one) ----` | Comment: the host sampler is still started by a `.watch` file. No schedule of round 4 has such a file, so the test makes one. |
| 1377 | `    open(box.sched("s1", "ZA.watch"), "w").close()` | Creates an empty file `ZA.watch` in session 1 of the box. |
| 1378 | `    rc, out, err = box.run(["--from", "5", "ZA"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="2")` | Runs the last process of `ZA`. The dummy sleeps 2 s, so the sampler has time for samples. |
| 1379 | `    w = box.file("watch-5.txt")` | `w`: the content of the sampler file `watch-5.txt`. |
| 1380 | `    pid = box.launched()[0].split()[0] if box.launched() else "?"` | `pid`: the process id of the dummy, from the first line of the dummy log. |
| 1381 | `    check("a step with a .watch file runs with hostwatch.py: watch-5.txt names the benchmark process and the CPU of its row, "` | Starts a check: a step with a `.watch` file runs with `hostwatch.py`. The name lists what is tested: the sampler file names the benchmark process and the CPU of its row. |
| 1382 | `          "has samples and its end line; the sampler is gone",` | Continues the name: the file has samples and its end line, and the sampler is gone after the run. |
| 1383 | `          rc == 0 and w.startswith("# hostwatch v1 pid=%s cpu=2 hz=20 max_s=31\n" % pid) and "\n# end reason=" in w` | The test: exit status 0. The sampler file starts with the header of the sampler, with the process id of the dummy, CPU 2, 20 samples per second and a time limit of 31 s. The file holds an end line. The 31 s are the nominal time of the process rounded up to 1 s, plus 30 s. |
| 1384 | `          and " m.run_ns=" in w and box.none_alive() and "host sampler: hostwatch.py on CPU %s " % box.watch_cpu in out` | Continues: the file holds a value `m.run_ns` of the main thread, no process of the case is left, and the output announces the sampler on the CPU of the test. |
| 1385 | `          and re.search(r"^## host sampler: WATCH_CPU=%s Python \S+ sha256 %s$" % (box.watch_cpu, sha256(WATCH)),` | Continues: `env.txt` holds the line about the host sampler. The pattern asks for the CPU, the word `Python` with a version, and the sha256 of `hostwatch.py`, which the test computes itself. |
| 1386 | `                        box.file("env.txt"), re.M) is not None, (rc, err, w[:200]))` | Ends the test. This proves three things: the sampler is started for the right process and CPU, it writes its file, and it is stopped. |
| 1387 | `    rc, out, err = box.run(["--from", "5", "ZA"], SESSION="1", STOP_AT="none", WATCH_CPU="126")` | Runs the same process with `WATCH_CPU=126`. |
| 1388 | `    check("a step with a .watch file and WATCH_CPU=126: status 2, nothing starts",` | Starts a check: with a `.watch` file and the sampler CPU 126, the script ends with status 2 and starts nothing. |
| 1389 | `          rc == 2 and "WATCH_CPU must be a CPU from 0 to 119" in err and not box.launched(), (rc, err))` | The test: exit status 2, the message that the CPU must be from 0 to 119, and no launch. Our runs must not use the CPUs above 119. |
| 1390 | `    os.remove(box.sched("s1", "ZA.watch"))` | Removes the file `ZA.watch`. |
| 1391 | `    rc, out, err = box.run(["--from", "5", "ZA"], SESSION="1", STOP_AT="none", WATCH_CPU="126")` | Runs the same process again with `WATCH_CPU=126`. |
| 1392 | `    check("a step without a .watch file does not read WATCH_CPU and writes no sampler file",` | Starts a check: a step without a `.watch` file does not read `WATCH_CPU` and writes no sampler file. |
| 1393 | `          rc == 0 and len(box.launched()) == 2 and not [f for f in os.listdir(box.folder()) if f.startswith("watch")], (rc, err))` | The test: exit status 0, one launch, and no file of the result folder starts with `watch`. |

### `run_checks`: the stop controls, and `MARGIN` with the real schedules (lines 1395 to 1482)

| Line | Source | Explanation |
|---:|---|---|
| 1395 | `    # ---- stop controls, for a step of each binary ----` | Comment: the checks of the stop controls start here. They run once for a step of each binary. |
| 1396 | `    for step, word in (("ZM", "bwx8"), ("ZC", "bwx10"), ("ZA", "bwx11")):` | Starts the loop over three steps: `ZM` with `bwx8`, `ZC` with `bwx10` and `ZA` with `bwx11`. |
| 1397 | `        rows = box.rows(step)` | `rows`: the schedule rows of the step. |
| 1398 | `        tag = rows[0][1]` | `tag`: the tag of its first process. |
| 1399 | `        note = "%s (%s)" % (step, word)` | `note`: the step and the word, for the names of the checks. |
| 1400 | `        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step without waiting for its end. The dummy sleeps 300 s, so the first process is still running when the test acts. |
| 1401 | `        up = box.wait_launch()` | Waits until the first dummy has started its sleep. |
| 1402 | `        open(box.marker, "w").close()` | Creates the file that stands for the marker file in this case. |
| 1403 | `        out, err = p.communicate(timeout=60)` | Waits for the end of the script, at most 60 s. |
| 1404 | `        csv = box.csv(step)` | `csv`: the content of the output file of the step. |
| 1405 | `        check("%s: marker file appears during a process: status 3, '-- killed', no process left" % note,` | Starts a check: the marker file appears during a process. Expected: status 3, a `-- killed` line, and no process left. |
| 1406 | `              up and p.returncode == 3 and ("-- killed tag %s status 3" % tag) in csv` | The test: the dummy had started, the exit status is 3, and the output file holds the line `-- killed tag` with the tag of the first process and `status 3`. |
| 1407 | `              and csv.count("-- step ") == 1 and box.none_alive(), (up, p.returncode, err, csv))` | Ends the test: only one process was started, and no process of the case is left. This proves that the script ends a running benchmark when the marker file appears, and that it leaves nothing running. The test does not measure how fast the stop is: it waits up to 60 s for the end of the script (line 1403). |
| 1408 | `        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", BWX8_MARKER=box.marker)` | Runs the step again. The marker path of this run is the file that the last case created, so the marker file exists from the start. |
| 1409 | `        check("%s: marker file present at the start: status 3, nothing starts, no result folder" % note,` | Starts a check: the marker file is present at the start. Expected: status 3, nothing starts, and no result folder. |
| 1410 | `              rc == 3 and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 3, no launch and no result folder. |
| 1411 | `        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step again, with a dummy that sleeps 300 s. |
| 1412 | `        up = box.wait_launch()` | Waits until the first dummy has started its sleep. |
| 1413 | `        open(box.stopfile, "w").close()` | Creates the file that stands for the stop file in this case. |
| 1414 | `        out, err = p.communicate(timeout=60)` | Waits for the end of the script. |
| 1415 | `        check("%s: stop file appears during a process: status 5, '-- killed', no process left" % note,` | Starts a check: the stop file appears during a process. Expected: status 5, a `-- killed` line, and no process left. |
| 1416 | `              up and p.returncode == 5 and ("-- killed tag %s status 5" % tag) in box.csv(step) and box.none_alive(),` | The test: the dummy had started, the exit status is 5, the output file holds the `-- killed` line with `status 5`, and no process is left. |
| 1417 | `              (up, p.returncode, err))` | The detail for a failure. |
| 1418 | `        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", BWX8_STOPFILE=box.stopfile)` | Runs the step again. The stop file path of this run is the file that the last case created. |
| 1419 | `        check("%s: stop file present at the start: status 5, nothing starts" % note, rc == 5 and not box.launched(), (rc, err))` | Check: the stop file is present at the start. The exit status is 5, and nothing starts. |
| 1420 | `        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts the step again, with a dummy that sleeps 300 s. |
| 1421 | `        up = box.wait_launch()` | Waits until the first dummy has started its sleep. |
| 1422 | `        os.kill(p.pid, signal.SIGTERM)` | Sends the termination signal SIGTERM to the script. |
| 1423 | `        out, err = p.communicate(timeout=60)` | Waits for the end of the script. |
| 1424 | `        csv = box.csv(step)` | `csv`: the content of the output file of the step. |
| 1425 | `        check("%s: interrupted during a process: status 130, '-- killed' marks the cut process, no process left" % note,` | Starts a check: the script is interrupted during a process. Expected: status 130, a `-- killed` line that marks the interrupted process, and no process left. |
| 1426 | `              up and p.returncode == 130 and box.none_alive()` | The test: the dummy had started, the exit status is 130, and no process of the case is left. |
| 1427 | `              and re.search(r"^-- killed tag %s status 130 utc \S+$" % re.escape(tag), csv, re.M) is not None` | Continues: the output file holds a line `-- killed tag`, the tag, `status 130 utc` and a time. With `re.escape`, no character of the tag acts as a pattern sign. |
| 1428 | `              and csv.count("-- step ") == 1, (up, p.returncode, err, csv))` | Ends the test: only one process was started. So an interrupted process is marked in the output file and cannot be read as a complete one. |
| 1429 | `        rc, out, err = box.run([step], SESSION="1", STOP_AT=utc(30))` | Runs the step with a stop time 30 s from now. |
| 1430 | `        check("%s: STOP_AT nearer than MARGIN: status 4, nothing starts" % note,` | Starts a check: `STOP_AT` is nearer than `MARGIN`. Expected: status 4, and nothing starts. |
| 1431 | `              rc == 4 and not box.launched() and "less than 91 s away" in err, (rc, err))` | The test: exit status 4, no launch, and the message `less than 91 s away`. The 91 s are the longest process of the test schedule, rounded up to 1 s, plus the 90 s of `RESERVE`. |
| 1432 | `        p = box.start([step], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")` | Starts the step with a stop time 45 s from now, `RESERVE` set to 0 and a dummy that sleeps 300 s. With a `MARGIN` of 1 s the first process may start. |
| 1433 | `        up = box.wait_launch()` | Waits until the first dummy has started its sleep. |
| 1434 | `        out, err = p.communicate(timeout=120)` | Waits for the end of the script, at most 120 s. |
| 1435 | `        check("%s: STOP_AT reached during a process: status 4, '-- killed', no process left" % note,` | Starts a check: `STOP_AT` is reached during a process. Expected: status 4, a `-- killed` line, and no process left. |
| 1436 | `              up and p.returncode == 4 and ("-- killed tag %s status 4" % tag) in box.csv(step) and box.none_alive(),` | The test: the dummy had started, the exit status is 4, the output file holds the `-- killed` line with `status 4`, and no process is left. So the stop time also ends a benchmark that is running. |
| 1437 | `              (up, p.returncode, err))` | The detail for a failure. |
| 1438 | `        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", DUMMY_EXIT="3")` | Runs the step with a dummy that ends with exit status 3. |
| 1439 | `        csv = box.csv(step)` | `csv`: the content of the output file of the step. |
| 1440 | `        check("%s: failing benchmark: status 1, '-- failed', the next process does not start" % note,` | Starts a check: a failing benchmark. Expected: status 1, a `-- failed` line, and the next process does not start. |
| 1441 | `              rc == 1 and ("-- failed tag %s exit 3" % tag) in csv and csv.count("-- step ") == 1` | The test: exit status 1, the line `-- failed tag` with the tag and `exit 3`, and only one header line in the output file. |
| 1442 | `              and box.binaries() == [box.bin[word]], (rc, err, csv))` | Ends the test: exactly one launch, with the binary of the word of this step. So after a failed process the script runs nothing more of the step. |
| 1443 | `    rc, out, err = box.run(["ZA"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="0.3", DUMMY_TOUCH="1")` | Runs `ZA` with a dummy that sleeps 0.3 s and creates the marker file when it ends. |
| 1444 | `    csv = box.csv("ZA")` | `csv`: the content of the output file `ZA.csv`. |
| 1445 | `    check("marker file appears between two processes: status 3, the first process ended, the second does not start",` | Starts a check: the marker file appears between two processes. Expected: status 3, the first process ended, and the second does not start. |
| 1446 | `          rc == 3 and csv.count("-- step ") == 1 and csv.count("M,dummy,bwx11\n") == 1 and "-- killed" not in csv` | The test: exit status 3, one header line, one output row of the dummy, and no `-- killed` line. |
| 1447 | `          and len(box.launched()) == 2, (rc, err, csv))` | Ends the test: the dummy log has two lines, which is one launch. This proves the check before a launch: a process that has ended is kept as complete, and no new process starts while the marker file exists. |
| 1448 | `    late = os.path.join(box.dir, "case%d" % (box.n + 1), "RUNNING")       # the marker path of the next case` | `late`: the marker path that the next case will have. The case number is known before the case starts. |
| 1449 | `    rc, out, err = box.run(["ZA"], SESSION="1", STOP_AT="none", PS_TOUCH=late,` | Runs `ZA` with `PS_TOUCH` set to that path. |
| 1450 | `                           PATH=os.path.join(box.dir, "bin") + os.pathsep + os.environ["PATH"])` | Continues the call: the folder `bin` of the box stands first in the search path. So the script calls the stand-in for `ps`, and the second call of it creates the marker file. |
| 1451 | `    check("marker file appears after the wait, directly before the launch: status 3, nothing starts",` | Starts a check: the marker file appears after the wait, directly before the launch. Expected: status 3, and nothing starts. |
| 1452 | `          late == box.marker and os.path.exists(late) and rc == 3 and not box.launched() and "-- step" not in box.csv("ZA")` | The test: the path was the marker path of the case, the file exists, the exit status is 3, no dummy was started, and the output file has no header line. |
| 1453 | `          and box.file("launches.txt").count("== ZA.csv idx ") == 1, (rc, err))` | Ends the test: `launches.txt` holds exactly one load record. So the stop came after the load record and before the header line. This proves the second marker check of the function `one`, the one directly before the launch. |
| 1454 | `    rc, out, err = box.run(["ZA"], SESSION="1")` | Runs `ZA` without `STOP_AT`. |
| 1455 | `    check("STOP_AT not set: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. A real run needs a decision about the stop time. |
| 1456 | `    # MARGIN is the longest process of the step, rounded up to whole seconds, plus RESERVE. With the test` | Comment: `MARGIN` is the longest process of the step, rounded up to whole seconds, plus `RESERVE`. |
| 1457 | `    # divisor 100 the longest process is 0.3 s (1 s); with divisor 1 the processes of ZM are 30 s and those of ZD 9.6 s.` | Continues the comment: with the test divisor 100 the longest process has 0.3 s, which rounds up to 1 s. With the divisor 1 the processes of `ZM` have 30 s and those of `ZD` 9.6 s. |
| 1458 | `    os.rename(box.sched(), os.path.join(box.dir, "sched11-test"))` | Moves the test schedule of the box away, to the name `sched11-test`. |
| 1459 | `    shutil.copytree(os.path.join(Z, "sched11"), box.sched())` | Copies the saved folder `sched11` beside this file, the real schedules, into the box. |
| 1460 | `    rc, out, err = box.run(["ZM"], SESSION="1", STOP_AT=utc(100))` | Runs `ZM` with a stop time 100 s from now. |
| 1461 | `    check("MARGIN follows the longest process of the step: the real ZM schedule refuses at 120 s, not at 91 s",` | Starts a check: `MARGIN` follows the longest process of the step. The real `ZM` schedule refuses a start at 120 s, not at 91 s. |
| 1462 | `          rc == 4 and not box.launched() and "less than 120 s away" in err and "longest process 30 s, MARGIN 120 s" in out,` | The test: exit status 4, no launch, the message `less than 120 s away`, and the summary line says that the longest process has 30 s and that `MARGIN` is 120 s. |
| 1463 | `          (rc, err, out))` | The detail for a failure. |
| 1464 | `    rc, out, err = box.run(["ZD"], SESSION="1", STOP_AT=utc(95))` | Runs `ZD` with a stop time 95 s from now. |
| 1465 | `    check("the real ZD schedule: longest process 10 s (9.6 s of kernel work; the evict step is not in it), MARGIN 100 s",` | Starts a check: for the real `ZD` schedule the longest process counts as 10 s. That is 9.6 s of kernel work rounded up. The evict step is not in it. `MARGIN` is 100 s. |
| 1466 | `          rc == 4 and not box.launched() and "less than 100 s away" in err and "longest process 10 s, MARGIN 100 s" in out,` | The test: exit status 4, no launch, the message `less than 100 s away`, and the summary line with 10 s and 100 s. |
| 1467 | `          (rc, err, out))` | The detail for a failure. This check shows that the evict time is covered only by `RESERVE`. |
| 1468 | `    rc, out, err = box.run(["--dry-run"] + ALL_STEPS, SESSION="1")` | Runs a dry run of all 5 steps of session 1 with the real schedules. |
| 1469 | `    check("--dry-run of the real schedules, session 1: 438 processes of bwx11 and the nominal work of the task "` | Starts a check: the dry run of the real schedules of session 1 gives 438 processes of `bwx11` and the nominal work of the task. |
| 1470 | `          "(7.8, 2073.6, 192, 1382.4, 1200 s)",` | Continues the name: 7.8, 2073.6, 192, 1382.4 and 1200 s. |
| 1471 | `          rc == 0 and out.count("\nbwx11 --trial ") == 438 and "\nbwx8 " not in out and "\nbwx10 " not in out` | The test: exit status 0, 438 command lines of `bwx11`, and none of `bwx8` or `bwx10`. |
| 1472 | `          and all(s in out for s in ("step ZA session 1: 6 processes, nominal kernel work 7.800 s",` | Continues: the summary line of `ZA` with 6 processes and 7.800 s. |
| 1473 | `                                     "step ZD session 1: 216 processes, nominal kernel work 2073.600 s",` | Continues: the summary line of `ZD` with 216 processes and 2073.600 s. |
| 1474 | `                                     "step ZC session 1: 32 processes, nominal kernel work 192.000 s",` | Continues: the summary line of `ZC` with 32 processes and 192.000 s. |
| 1475 | `                                     "step ZN session 1: 144 processes, nominal kernel work 1382.400 s",` | Continues: the summary line of `ZN` with 144 processes and 1382.400 s. |
| 1476 | `                                     "step ZM session 1: 40 processes, nominal kernel work 1200.000 s")), (rc, err, out[:300]))` | Ends the test: the summary line of `ZM` with 40 processes and 1200.000 s. So the run script itself computes the planned numbers from the files that will go to CRB. |
| 1477 | `    rc, out, err = box.run(["--dry-run", "ZD", "ZC", "ZN", "ZM"], SESSION="2")` | Runs a dry run of the four steps of session 2 with the real schedules. |
| 1478 | `    check("--dry-run of the real schedules, session 2: 432 processes of bwx11",` | Starts a check: the dry run of the real schedules of session 2 gives 432 processes of `bwx11`. |
| 1479 | `          rc == 0 and out.count("\nbwx11 --trial ") == 432, (rc, err))` | The test: exit status 0 and 432 command lines of `bwx11`. |
| 1480 | `    shutil.rmtree(box.sched())` | Removes the copy of the real schedules from the box. |
| 1481 | `    os.rename(os.path.join(box.dir, "sched11-test"), box.sched())` | Moves the test schedule back to the name `sched11`. |

### `run_checks`: session 2 and other refusals (lines 1483 to 1539)

| Line | Source | Explanation |
|---:|---|---|
| 1483 | `    # ---- session 2 (ZM still names bwx8, ZC bwx10) ----` | Comment: the checks of session 2. In the box `ZM` still names `bwx8`, and `ZC` names `bwx10`. |
| 1484 | `    rc, out, err = box.run(["ZD"], SESSION="2", STOP_AT="none")` | Runs `ZD` for session 2 without `SESSION1_END`. |
| 1485 | `    check("session 2 without SESSION1_END: status 2, nothing starts",` | Starts a check: session 2 without `SESSION1_END` ends with status 2, and nothing starts. |
| 1486 | `          rc == 2 and "SESSION1_END" in err and not box.launched(), (rc, err))` | The test: exit status 2, the error output names `SESSION1_END`, and no launch. |
| 1487 | `    for step in ("ZM", "ZD"):` | Starts a loop over two steps, `ZM` and `ZD`. |
| 1488 | `        rc, out, err = box.run([step], SESSION="2", STOP_AT="none", SESSION1_END=utc(-3 * 3600 + 120))` | Runs the step for session 2 with an end of session 1 that lies 2 minutes less than 3 hours in the past. |
| 1489 | `        check("session 2 of %s earlier than 3 h after SESSION1_END: refused with status 2, nothing starts" % step,` | Starts a check per step: session 2 earlier than 3 hours after `SESSION1_END` is refused with status 2, and nothing starts. |
| 1490 | `              rc == 2 and "3 hours" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the words `3 hours` in the error output, no launch and no result folder. The design asks for at least 3 hours between the end of the first session and the start of the second. |
| 1491 | `    for value in ("garbage", time.strftime("%Y-%m-%d", time.gmtime()), "yesterday", "@0", "-4 hours",` | Starts a loop over values of `SESSION1_END` that must be refused: a word without meaning, a date without a time, the word `yesterday`, the form `@0`, and a relative time. |
| 1492 | `                  time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - 4 * 3600)), "2026-02-30T00:00Z"):` | Continues the list: a date and a time of 4 hours ago with a blank between them and without `Z`, and the 30th of February in the right form. |
| 1493 | `        rc, out, err = box.run(["--from", "215", "ZD"], SESSION="2", STOP_AT="none", SESSION1_END=value)` | Runs the last process of `ZD` for session 2 with that value. |
| 1494 | `        check("session 2 with SESSION1_END='%s': status 2, nothing starts" % value,` | Starts a check per value: status 2, and nothing starts. |
| 1495 | `              rc == 2 and "bad SESSION1_END" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the message `bad SESSION1_END`, no launch and no result folder. Several of these values are accepted by `date -d`. Without the strict form a wrong text could let session 2 start too early. |
| 1496 | `    s1end = utc(-3 * 3600 - 60)` | `s1end`: a valid end of session 1 that lies 3 hours and 1 minute in the past. |
| 1497 | `    row2 = box.rows("ZD", 2)[215]` | `row2`: the last row of the `ZD` schedule of session 2. |
| 1498 | `    rc, out, err = box.run(["--from", "215", "ZD"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)` | Runs the last process of `ZD` for session 2 with that end time. |
| 1499 | `    env = box.file("env.txt")` | `env`: the content of `env.txt`. |
| 1500 | `    check("session 2 later than 3 h after SESSION1_END: runs the session 2 schedule, folder bwx11-ZD-s2-, SESSION1_END in env.txt",` | Starts a check: session 2 later than 3 hours after `SESSION1_END` runs the schedule of session 2. The folder name starts with `bwx11-ZD-s2-`, and `env.txt` records `SESSION1_END`. |
| 1501 | `          rc == 0 and "bwx11-ZD-s2-" in (box.folder() or "") and ("SESSION1_END=" + s1end) in env` | The test: exit status 0, the name of the result folder, and the recorded end time. |
| 1502 | `          and ("-- step ZD session 2 idx 215 tag %s " % row2[1]) in box.csv("ZD")` | Continues: the header line in the output file names session 2, the `idx` 215 and the tag of the row of session 2. |
| 1503 | `          and "--plan sched11/s2/ZD/0215.plan" in box.launched()[0] and box.binaries() == [box.bin11], (rc, err))` | Ends the test: the launch got the plan of session 2, and it used the dummy `bwx11`. So `SESSION=2` selects the schedules of session 2, which have the reversed CPU order. |
| 1504 | `    for step, word in (("ZM", "bwx8"), ("ZC", "bwx10")):` | Starts a loop over the two steps whose `.bin` file names an older binary. |
| 1505 | `        row2 = box.rows(step, 2)[last[step]]` | `row2`: the last row of the schedule of the step in session 2. |
| 1506 | `        rc, out, err = box.run(["--from", str(last[step]), step], SESSION="2", STOP_AT="none", SESSION1_END=s1end)` | Runs that last process for session 2. |
| 1507 | `        check("session 2 of a step with the word %s (%s): runs the session 2 row with that binary" % (word, step),` | Starts a check per step: session 2 of a step with that word runs the row of session 2 with that binary. |
| 1508 | `              rc == 0 and box.binaries() == [box.bin[word]] and ("-- step %s session 2 idx %d tag %s " % (step, last[step], row2[1])) in box.csv(step)` | The test: exit status 0, the launch used the dummy of the word, and the header line names session 2, the `idx` and the tag of that row. |
| 1509 | `              and box.launched()[0].split(" ", 1)[1] == row2[5], (rc, err))` | Ends the test: the dummy got the `args` of that row. So session 2 starts the binary of the word with the row of session 2. The method `set_bin` writes the same word into the `.bin` files of both sessions (lines 1001 to 1004). So the check does not show from which of the two files the script took the word. |
| 1511 | `    # ---- other refusals ----` | Comment: the checks of other refusals start here. |
| 1512 | `    rc, out, err = box.run(["ZA"], STOP_AT="none")` | Runs `ZA` without `SESSION`. |
| 1513 | `    check("SESSION not set: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. The script does not guess the session. |
| 1514 | `    rc, out, err = box.run(["--from", "6", "ZA"], SESSION="1", STOP_AT="none")` | Runs `ZA` with `--from 6`. The step has the `idx` values 0 to 5. |
| 1515 | `    check("--from past the last idx: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. A `--from` value past the last `idx` runs nothing and is reported. |
| 1516 | `    rc, out, err = box.run(["--from", "1", "ZA", "ZD"], SESSION="1", STOP_AT="none")` | Runs two steps with `--from 1`. |
| 1517 | `    check("--from with two steps: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. `--from` is allowed with one step only. |
| 1518 | `    allowed = sorted(os.sched_getaffinity(0))` | `allowed`: the CPUs on which this test may run, in sorted order. |
| 1519 | `    rc, out, err = box.run(["--from", "5", "ZA"], pre=["taskset", "-c", str(allowed[0])], SESSION="1", STOP_AT="none")` | Runs the last process of `ZA`, with `taskset -c` before the script. So the script starts limited to one CPU, the lowest allowed one. |
| 1520 | `    seen = open(box.log + ".cpus").read() if os.path.exists(box.log + ".cpus") else ""` | `seen`: the CPU list that the dummy recorded, or an empty text. |
| 1521 | `    check("the benchmark is confined to CPUs 0-119, whatever CPU the script was started on",` | Starts a check: the benchmark is limited to the CPUs 0 to 119, on whatever CPU the script was started. |
| 1522 | `          rc == 0 and len(allowed) > 1 and seen.count("\n") == 1 and cpu_list(seen) == {c for c in allowed if c < 120},` | The test: exit status 0, the test may use more than one CPU, the dummy recorded one line, and its CPU list is the set of the allowed CPUs below 120. |
| 1523 | `          (rc, err, seen))` | The detail for a failure. The check proves that the script sets the CPU list itself and does not keep the narrow list of its caller. The runner then finds its worker CPU in the list. |
| 1524 | `    tsv = box.sched("s1", "ZA.tsv")` | `tsv`: the schedule file of `ZA` in session 1 of the box. |
| 1525 | `    saved_za = open(tsv).read()` | `saved_za`: its text, kept for later. |
| 1526 | `    made = os.path.join(box.dir, "made-by-schedule")` | `made`: the path of a file that must never appear. |
| 1527 | `    for what, old_, new_ in (("idx", "\n0\t", "\na[$(touch${IFS}%s)]\t"), ("cpu", "\t2\t", "\ta[$(touch${IFS}%s)]\t")):` | Starts a loop over two damaged schedules. In the first the `idx` of the first row is a text with a command substitution that would create the file `made`. In the second the `cpu` column holds such a text. `${IFS}` takes the place of the blank inside the command, so the column itself holds no blank. |
| 1528 | `        with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1529 | `            fh.write(saved_za.replace(old_, new_ % made, 1))` | Writes the schedule with that one replacement. |
| 1530 | `        rc, out, err = box.run(["--dry-run", "ZA"], SESSION="1")` | Runs a dry run of `ZA`. |
| 1531 | `        check("schedule with a command in %s: status 2, the command does not run" % what,` | Starts a check per case: a schedule with a command in that column gives status 2, and the command does not run. |
| 1532 | `              rc == 2 and not os.path.exists(made) and open(tsv).read() != saved_za, (rc, err))` | The test: exit status 2, the file `made` does not exist, and the schedule file really differs from the saved text. The script uses `idx` in shell arithmetic, which would run such a command, and it gives `cpu` to the host sampler. The check proves that both values are tested before they are used. |
| 1533 | `    with open(tsv, "w") as fh:` | Opens the schedule file for writing. |
| 1534 | `        fh.write(saved_za)` | Writes the saved text back. |
| 1535 | `    os.rename(box.sched("s1", "ZA", "0001.plan"), os.path.join(box.dir, "moved.plan"))` | Moves the plan file of the second process of `ZA` out of the schedule folder. |
| 1536 | `    rc, out, err = box.run(["ZA"], SESSION="1", STOP_AT="none")` | Runs `ZA` for real. |
| 1537 | `    check("missing plan file: status 2 before the first launch", rc == 2 and "missing plan file" in err and not box.launched(), (rc, err))` | Check: exit status 2, the message `missing plan file`, and no launch. So a missing plan stops the step before its first process, and not in the middle of the step. |

### `main`: the order of the groups of checks, and the summary (lines 1540 to 1566)

| Line | Source | Explanation |
|---:|---|---|
| 1540 | `def main():` | Starts the function `main`. |
| 1541 | `    with open("/proc/loadavg") as f:` | Opens the file `/proc/loadavg`. |
| 1542 | `        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))` | Prints the load averages of the last 1, 5 and 15 minutes and the number of CPUs on which the test may run. The load matters: the run script waits for a quiet system before each launch, so the test takes longer on a loaded machine. |
| 1543 | `    tmp = tempfile.mkdtemp(prefix="test_schedule11.")` | `tmp`: a new temporary folder whose name starts with `test_schedule11.`. |
| 1544 | `    try:` | Starts the block whose cleanup is in lines 1556 to 1557. |
| 1545 | `        real, sched = schedule_checks(tmp)` | Runs the checks of the generator. They return the folder with the real durations and the folder with the test divisor 100. |
| 1546 | `        if "--no-bwx10" in sys.argv[1:]:` | When the option `--no-bwx10` was given. |
| 1547 | `            skip("the checks that the local stand-in bwx10 refuses the args and plans of round 4 (--no-bwx10)")` | Reports the checks with the stand-in `bwx10` as not run. |
| 1548 | `        else:` | If not. |
| 1549 | `            bwx10_checks(tmp, sched)` | Runs the checks that the older runner refuses the options and plans of round 4. |
| 1550 | `        bwx11_checks(tmp, real, sched)` | Runs every plan through the stand-in `bwx11`, unless an option or a missing source leaves that part out. |
| 1551 | `        visit_checks(tmp)` | Runs the checks of the visit script. |
| 1552 | `        if "--no-run" in sys.argv[1:]:` | When the option `--no-run` was given. |
| 1553 | `            skip("the checks of run_bwx11.sh with dummy binaries (--no-run)")` | Reports the checks of `run_bwx11.sh` with dummy binaries as not run. |
| 1554 | `        else:` | If not. |
| 1555 | `            run_checks(tmp, sched)` | Runs the checks of the run script. |
| 1556 | `    finally:` | The cleanup. It runs in every case, also after an error. |
| 1557 | `        shutil.rmtree(tmp, ignore_errors=True)` | Removes the temporary folder with everything in it. |
| 1558 | `    with open("/proc/loadavg") as f:` | Opens the file `/proc/loadavg` again. |
| 1559 | `        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))` | Prints the load averages at the end. |
| 1560 | `    print("# checks: %d, passed: %d, failed: %d, parts not run (SKIP lines): %d%s"` | Prints the summary line: the number of checks, of passed checks and of failed checks, and the number of parts that did not run. |
| 1561 | `          % (COUNT[0], COUNT[0] - len(FAILS), len(FAILS), SKIPS[0], "".join("\n#   " + n for n in FAILS)))` | The values of the summary. The name of each failed check follows on a line of its own. |
| 1562 | `    sys.exit(1 if FAILS else 0)` | Ends the program with exit status 1 when a check failed, and with 0 if not. A part that did not run does not change the status. |
| 1565 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 1566 | `    main()` | Runs `main`. |
