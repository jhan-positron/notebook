# `test_schedule8.py` explained, line by line

- Source file: `bwx8-2026-11-14/test_schedule8.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 993 lines, 54927 bytes).
- sha256 of the source when this page was built: `916e5b472f54082d951f9bcf82d67de4629214594dda2a3445c2f16924da516e`.

## Short version: purpose

`test_schedule8.py` checks the three scripts of round 1 without CRB: the generator `schedule8.py`, the run script `run_bwx8.sh` and the visit script `visit8.sh`. It tests the generated schedules against rules that are written a second time in this file, and it runs the run script with a dummy binary through its stop cases. The validator, the comparison of the nominal work and seven rule functions are also applied to inputs that must not pass, to show that they can fail.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 1**: the first set of tests of the investigation into the buffer size of 8 MiB. The three scripts under test belong to it.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation. Its parts are called stages. Stage 2 is the size comparison of step `S2`, and Stage 3 is the test of mixed sequences of step `S3`.
- **Contract**: the note `DECISIONS-bwx8.md`. It fixes what the parts of the implementation share: the plan format, the table of the steps and the nominal kernel work of each step.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Process**: one start of a benchmark binary.
- **Check**: one call of the function `check`. It prints `PASS` or `FAIL` and one sentence that says what was tested.
- **Generator**: the program `schedule8.py`. It writes the schedules and the plan files of round 1.
- **Run script**: the script `run_bwx8.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Visit script**: the script `visit8.sh`. It makes one login to CRB and starts the run script there.
- **Step**: one batch of processes of a round, for example `S2`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Header pairs**: the pairs of the form `key=value` in the second line of a plan file, for example `kernel=asmread`.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Target, window**: the target is the kernel that a trial measures. A window is one timed period of it.
- **Same-kernel trial**: a trial in which the target kernel is also the prefix: a prefix of 4 window lengths and then 4 target windows. The trials of step `S2` have this form.
- **Interval mode**: the mode of the runner that times a kernel sequence from the option `--seq`. The processes of step `B6W` use it and have no plan file.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Condition**: one setting that a step compares, and the label that names it in the plan, for example `K=read|S=8M`.
- **Cycle, row**: a cycle is a group of trials of one process that holds every condition of the step once. A row is the list of the condition labels of one cycle, in run order.
- **Replicate set, block**: a replicate set is the three processes of step `S2` that have the same size, CPU and replicate number, one per kernel. A block is the 30 processes of one replicate number.
- **Start order, shift**: the start order is the fixed order of 12 condition numbers that the design gives for step `S3`. A shift adds one number to every entry and takes the rest of a division by 12.
- **Base seed, seed**: the base seed is the one number that the caller of the generator can set with `--seed`. The seed of a step and session is derived from it.
- **Test divisor**: a number by which the generator divides every duration, for local tests only. The test uses 100.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `open` means that the counters are open and are not read at the window boundaries. `read` means that the runner reads them at the boundaries of the target windows.
- **Bins**: records of 10 ms inside a target window. The field `bins` of a trial turns them on (1) or off (0).
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`BWX_PMU_TYPE`, `BWX_EVENTS`**: the two counter settings that the run script needs in its environment for the steps `CS`, `CM` and `C4`: the type number of the counter device, and the list of the counter events.
- **Validator**: the function `parse_plan` of this file. It tests a plan file against the rules of the plan format.
- **Dummy binary**: a small shell script that stands in for the runner. It records how it was started, sleeps, and ends with a chosen exit status.
- **Stand-in**: a program that takes the place of another one in the test, here of `ps` and of `ssh`.
- **Box**: the test setup of the run script: a copy of the script, the dummies and a schedule in a temporary folder.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop the run script.
- **`STOP_AT`**: a UTC time that the caller sets. The run script starts a process only when this time is more than `MARGIN` seconds away, and it ends a process that still runs at this time.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s by default. `MARGIN` is the nominal work of the longest process of a step, rounded up to whole seconds, plus `RESERVE`.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Dry run**: a call of the run script with `--dry-run`. It prints what would run and starts nothing.
- **Output file, header line**: the output file of a step is `<STEP>.csv` in the result folder. Before the output of each process the run script writes a header line into it. That line starts with `-- step`.
- **Load record**: the lines that the run script appends to the file `launches.txt` before a launch: the load averages, the number of logins and the 5 processes with the highest `pcpu` value of `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB**: 1024 bytes.

## Main flow

1. The values that the contract expects are written as fixed values: the nominal work of 7 steps and the counts of all 11 steps (lines 30 to 35).
2. The helper `check` prints one line per check and collects the failures (lines 40 to 43).
3. The validator of the plan format and the reader of a generated folder (lines 46 to 128, lines 131 to 193).
4. The rules of the rows, of the CPU order and of step `S2`, each as a function (lines 196 to 350).
5. Group 1, `schedule_checks`: run the generator. Test the format of every file, the counts and the printed report, the header pairs, the CPU order, the rules of each step with damaged variants, the effect of the seed, the option `--select`, the saved folder, `--report` and the test divisor (lines 353 to 613).
6. Group 2, `visit_checks`: the visit script with a stand-in for `ssh`: the remote command, and five bad settings (lines 733 to 770).
7. Group 3, `run_checks`: the run script with a dummy binary: syntax, a step named twice, the warnings, damaged schedule fields, the dry run, a normal run, `--from`, the CPU limit, the stop controls, `MARGIN`, session 2 and other refusals (lines 773 to 974).
8. `main` runs the groups in this order, removes the temporary folder and prints the summary (lines 977 to 989).

## Behavior a reader must know

- The test contacts no other machine. The visit script runs with a stand-in for `ssh` and a search path that holds no real `ssh` (line 750). The run script runs as a copy in a temporary folder, with test paths for the marker file, the stop file, the binary and the results (lines 692 to 693).
- The test starts local programs: the generator, `bash`, the copy of the run script and the dummies. The copy of the run script sets its own CPU list to the CPUs 0 to 119 with `taskset`, as the real script does.
- The exit status is 0 only when every check passed (line 989). With `--no-run` the checks of the run script are left out: the test prints a `SKIP` line, and the status does not change (lines 982 to 983).
- The expected values are written a second time in this file (lines 31 to 35, line 226, lines 445 to 448). So a change in the generator alone makes a check fail.
- The validator, the comparison of the nominal work and seven rule functions are tested twice: once on the real output, and once on an input that must not pass. The seven are `cpu_blocks`, `s2_rules`, `williams`, `from_start_order`, `rows_shuffled`, `order_varies` and `perms_four_times`.
- These second tests are 24 checks: 11 damaged plans for the validator (lines 364 to 377), a copy of `S2` with one trial removed for the nominal work (lines 385 to 388), the schedule of `S3` of session 1 read with the CPU order of session 2 for the rule of the CPU order (line 420), 5 variants for the rules of `S2` (lines 426 to 442), and 6 checks with changed rows for the rules of the balance, of the start order, of the shuffle, of the row order and of the order count (lines 471 to 480, lines 555 to 561). One of the 5 variants is the unchanged schedule of session 1, read with the CPU order of session 2.
- The other rules of this file have no such second test. Examples: the header pairs (lines 401 to 409), the conditions of a cycle (lines 453 to 454), the trial form of `S3` and `CM` (lines 455 to 459) and the alternating orders of `BIN` (lines 540 to 541). Inside `s2_rules`, no variant makes the rules of the sizes (lines 281 to 285) or of the `rep_set` value (lines 301 to 302) fail.
- No check of this file gives a plan to the runner. The plans are tested against the validator of this file only (lines 57 to 120).
- The only selection that the generator accepts in this test is `read@1M,asmread@8M` (line 28, line 355). So the steps `BIN` and `CS` are tested for these two pairs only. Two base seeds are used: 20261114 and 7 (line 572).
- The run script is tested with a schedule that was made with the test divisor 100 (line 605, line 613). So the durations in its summaries are a hundredth of the real ones, for example 0.624 s for `B6W`.
- The checks of the run script take minutes on a loaded machine. Before each launch the script waits up to 20 s until at most 2 tasks are runnable.
- The stop cases that are tested (lines 863 to 928): the marker file during a process, at the start, between two processes and directly before a launch. The stop file during a process. The signal TERM during a process. A `STOP_AT` that is nearer than `MARGIN`, and a `STOP_AT` that is reached during a process. A failing process. The cases with a running process test the exit status, the `-- killed` line and that no process is left.
- Not tested: a stop file that exists before a launch, and the signals INT and HUP.
- The checks of `MARGIN` use stop times that lie far inside or far outside the margin: 30 s against 91 s and against 92 s, and 45 s against 1 s (lines 907 to 920). No check tests a stop time that is exactly `MARGIN` seconds away.
- The check of the saved folder compares every file of `sched/` beside this file with the output of the generator (lines 594 to 596). The repo README lists the folders `sched*` among those that were left out of the repo. So in the repo folder this check fails. The other checks do not need that folder: the box gets a newly generated schedule (line 666).
- The check of step `B6W` reads the kernel sequence from `run_bwx.sh` in the folder `bwx-2026-11-13` beside the folder of this file (line 26, line 564).
- Some checks test less than their names say. This item and the next one name five of them. The check of lines 833 to 834 is named for header lines that are each followed by their output. It counts the output lines and does not test their places. The check of lines 474 to 475 is named for rows that are not shifts. Its input is 24 equal rows, which the rule rejects for the count of the shifts.
- The check of lines 607 to 610 is named for every duration divided by 100. It compares the sums of the nominal work of each step and session. The check of lines 410 to 414 is named for labels that agree with the trial. It compares the counter mode, the bins flag and the target kernel, and no other key of a label. The check of lines 836 to 838 is named for the digests in `env.txt`. It tests the heading `## sha256:` and not the digest lines.
- The check of the CPU limit compares the CPU list of the dummy with the CPUs that the test itself may use (lines 852 to 857). It needs a machine with 2 or more CPUs. A machine that has no CPU with the number 120 or higher cannot show that such CPUs are left out. Hypothesis, not tested: when the test itself was started with a narrower CPU list by `taskset`, the script still sets the list 0 to 119, the dummy then sees more CPUs than the test may use, and the check fails. One run of the test under such a narrower list would confirm or reject it.
- The test reads these files: `schedule8.py`, `run_bwx8.sh`, `visit8.sh` and the folder `sched` of its own folder, and `run_bwx.sh` of the folder `bwx-2026-11-13`.
- The test writes into a temporary folder only and removes it at the end (line 978, line 987).
- The name `M8` of line 29 is set and never used.

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/test_schedule8.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (993 lines, 54927 bytes, sha256 `916e5b472f54082d951f9bcf82d67de4629214594dda2a3445c2f16924da516e`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 49. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Description text and imports (lines 1 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_schedule8.py - checks of schedule8.py, run_bwx8.sh and visit8.sh.` | Starts the description text of the file. First line: the name and the purpose. The file holds the checks of the generator `schedule8.py`, of the run script `run_bwx8.sh` and of the visit script `visit8.sh`. |
| 4 | `Usage: test_schedule8.py [--no-run]` | Text of the description: the usage. The one option `--no-run` leaves out one group of checks. |
| 5 | `Prints one line per check. Exit status 0 only if every check passed.` | Text of the description: the program prints one line per check. Its exit status is 0 only when every check passed. |
| 6 | `--no-run leaves out the checks that start run_bwx8.sh with a dummy bwx8 (they take minutes` | Text of the description: `--no-run` leaves out the checks that start `run_bwx8.sh` with a dummy `bwx8`. A dummy `bwx8` is a small script that stands in for the runner. |
| 7 | `on a loaded machine, because the script waits up to 20 s for a quiet system before a launch).` | Continues the text: those checks take minutes on a loaded machine. The reason: the run script waits up to 20 s for a quiet system before each launch. |
| 8 | `Every rule is also applied to a defective input, and the check passes only if that is rejected.` | Text of the description: every rule is also applied to an input with a defect. Such a check passes only when the rule rejects that input. The code does not do this for every rule. It does it for the validator, for the comparison of the nominal work and for seven rule functions. Other checks have no input that must fail, for example the check of the trial form of `S3` and `CM` (lines 455 to 459). |
| 9 | `"""` | Ends the description text. |
| 10 | `import collections` | Loads the Python module `collections`: counters, and dictionaries that create a missing entry at its first use. |
| 11 | `import copy` | Loads `copy`: used to make an independent copy of a schedule before a check damages it. |
| 12 | `import itertools` | Loads `itertools`: used to build all orders of three items, to join rows into one sequence, and to merge equal neighbours of a list. |
| 13 | `import os` | Loads `os`: paths, folders and CPU lists. |
| 14 | `import re` | Loads `re`: regular expressions. |
| 15 | `import shutil` | Loads `shutil`: copies and removals of folder trees. |
| 16 | `import signal` | Loads `signal`: used to send a signal to the run script. |
| 17 | `import subprocess` | Loads `subprocess`: used to start the scripts under test. |
| 18 | `import sys` | Loads `sys`: the command line, the output and the exit status. |
| 19 | `import tempfile` | Loads `tempfile`: used to make the temporary folder of the test. |
| 20 | `import time` | Loads `time`: the clock, time texts and waits. |

### Paths, expected values of the contract, and the function `check` (lines 22 to 45)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `X = os.path.dirname(os.path.abspath(__file__))` | `X`: the full path of the folder that holds this file. |
| 23 | `SCHED = os.path.join(X, "schedule8.py")` | `SCHED`: the path of the generator under test, `schedule8.py`. |
| 24 | `RUN = os.path.join(X, "run_bwx8.sh")` | `RUN`: the path of the run script under test, `run_bwx8.sh`. |
| 25 | `VISIT = os.path.join(X, "visit8.sh")` | `VISIT`: the path of the visit script under test, `visit8.sh`. |
| 26 | `OLD_RUN = os.path.join(X, "..", "bwx-2026-11-13", "run_bwx.sh")` | `OLD_RUN`: the path of `run_bwx.sh`, the run script of the first runner, in the folder `bwx-2026-11-13` beside the folder of this file. The check of step `B6W` reads the kernel sequence from it (line 564). |
| 27 | `KERNELS = ["oldread", "read", "asmread"]` | `KERNELS`: the three kernel names that the plan validator of this file accepts: `oldread`, `read` and `asmread`. |
| 28 | `SELECT = "read@1M,asmread@8M"` | `SELECT`: the text that 4 of the 9 runs of the generator in this test give to the option `--select` (line 355, lines 571 to 572, line 605): the kernel `read` on 1 MiB and the kernel `asmread` on 8 MiB. With it the generator also writes the steps `BIN` and `CS`. |
| 29 | `M8 = 8 << 20` | `M8`: 8 MiB in bytes, 8388608. No other line of this file uses the name. |
| 30 | `# Contract, "Nominal kernel work that schedule8.py must print": processes and seconds, both sessions.` | Comment: the table that follows comes from the contract, the note `DECISIONS-bwx8.md`. Its section on the nominal kernel work gives, for both sessions together, the number of processes and the seconds that the generator must print for a step. |
| 31 | `NOMINAL = {"S2": (360, 3456.0), "S4": (36, 2160.0), "P3": (24, 691.2), "S3": (24, 3110.4),` | `NOMINAL`: the expected values, written here as fixed numbers and not taken from the generator. `S2`: 360 processes and 3456.0 s. `S4`: 36 and 2160.0 s. `P3`: 24 and 691.2 s. `S3`: 24 and 3110.4 s. |
| 32 | `           "P3G": (24, 4147.2), "S3G": (24, 1123.2), "B6W": (8, 124.8)}` | Ends the table. `P3G`: 24 processes and 4147.2 s. `S3G`: 24 and 1123.2 s. `B6W`: 8 and 124.8 s. The steps `BIN`, `CS`, `CM` and `C4` are not in this table. |
| 33 | `# Contract table: processes per session and trials per process.` | Comment: the second table comes from the step table of the contract. For each step it gives the processes per session and the trials per process. |
| 34 | `TABLE = {"B6W": (4, 0), "S2": (180, 4), "S4": (18, 1), "P3G": (12, 36), "P3": (12, 12),` | `TABLE`: the expected counts, again as fixed numbers. `B6W`: 4 processes with no trial, as they have no plan. `S2`: 180 processes of 4 trials. `S4`: 18 of 1. `P3G`: 12 of 36. `P3`: 12 of 12. |
| 35 | `         "S3G": (12, 12), "S3": (12, 48), "BIN": (24, 8), "CS": (24, 12), "CM": (12, 48), "C4": (18, 1)}` | Ends the table. `S3G`: 12 processes of 12 trials. `S3`: 12 of 48. `BIN`: 24 of 8 and `CS`: 24 of 12, which is 12 processes for each of the two pairs of `SELECT`. `CM`: 12 of 48. `C4`: 18 of 1. |
| 37 | `FAILS = []` | `FAILS`: the names of the checks that failed, empty at first. |
| 40 | `def check(name, ok, detail=""):` | Starts the function `check`. Every check of this file calls it. `name`: the sentence that says what is checked. `ok`: the result of the test. `detail`: values to print when the check fails. |
| 41 | `    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail) + "]") if detail and not ok else ""))` | Prints one line: `PASS` or `FAIL`, and then the name. After a failure it adds the detail in square brackets, when the caller gave one. |
| 42 | `    if not ok:` | When the check failed. |
| 43 | `        FAILS.append(name)` | Keeps its name for the summary at the end. |

### The plan validator of the test: patterns, `nbytes`, `parse_plan`, `rejected` (lines 46 to 130)

| Line | Source | Explanation |
|---:|---|---|
| 46 | `# ---------- an independent validator of the plan grammar of the contract ----------` | Comment: the next part is a validator of the plan format that the contract defines. It is written here a second time, without any code of the generator or of the runner. So a plan passes only when two independent texts agree on the format. |
| 47 | `PHASE = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?):(\d+)$")` | `PHASE`: the pattern of a phase text such as `asmread@8M:1200`. Group 1 holds the kernel name: lower-case letters, digits and `_`. Group 2, after the `@`, holds the size: digits and an optional letter `K`, `M` or `G`. Group 3, after the colon, holds the duration in ms: digits. |
| 48 | `TGT = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?)$")` | `TGT`: the pattern of a target text such as `asmread@8M`. Group 1 holds the kernel name and group 2 the size, as in `PHASE`. A target has no duration. |

Line 49 holds a backslash directly before a `|`. It stands outside the table:

```text
COND = re.compile(r"^[^=|, ]+=[^=|, ]+(\|[^=|, ]+=[^=|, ]+)*$")
```

Explanation of line 49: `COND`: the pattern of a condition label such as `K=asmread|S=8M`. A label is one pair `key=value`, or several pairs with a vertical bar between them. A key and a value have at least one character each. They hold no equals sign, no vertical bar, no comma and no blank.

| Line | Source | Explanation |
|---:|---|---|
| 52 | `def nbytes(tok):` | Starts the function `nbytes`. It converts a size text such as `8M` to a number of bytes. |
| 53 | `    m = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}` | `m`: the factor of each unit letter: 1024 for `K`, 1024 times 1024 for `M`, and 1024 times that for `G`. |
| 54 | `    return int(tok[:-1]) * m[tok[-1]] if tok[-1] in m else int(tok)` | Returns the number before the letter times its factor. A text without a letter is a plain number of bytes. |
| 57 | `def parse_plan(text):` | Starts the function `parse_plan`, the validator. It reads the text of one plan file and tests every rule of the format. |
| 58 | `    """Returns (header dict, trials) or raises ValueError that names the defect."""` | Description text: the function returns the header pairs as a dictionary and the list of the trials. For a plan with a defect it raises a `ValueError` whose text names the defect. |
| 59 | `    if not text.endswith("\n"):` | Rule: the file ends with a newline. |
| 60 | `        raise ValueError("no final newline")` | If not: raises the error `no final newline`. |
| 61 | `    lines = text[:-1].split("\n")` | `lines`: the lines of the file, without the last newline. |
| 62 | `    if len(lines) < 4:` | Rule: the file has at least 4 lines. These are 3 header lines and one trial. |
| 63 | `        raise ValueError("fewer than 4 lines")` | If not: raises the error `fewer than 4 lines`. |
| 64 | `    if lines[0] != "# bwx8-plan v1":` | Rule: the first line is exactly `# bwx8-plan v1`. |
| 65 | `        raise ValueError("line 1")` | If not: raises an error with the text `line 1`. |
| 66 | `    if not lines[1].startswith("# "):` | Rule: the second line starts with `#` and a blank. |
| 67 | `        raise ValueError("line 2")` | If not: raises an error with the text `line 2`. |
| 68 | `    head = {}` | `head`: the header pairs, empty at first. |
| 69 | `    for pair in lines[1][2:].split(" "):` | Starts a loop over the pairs of the second line, split at single blanks. |
| 70 | `        k, eq, v = pair.partition("=")` | Splits a pair at the first equals sign into the key `k` and the value `v`. |
| 71 | `        if not k or not eq or not v or k in head:` | Rule for a pair: it has a key, an equals sign and a value, and its key was not used before in the line. |
| 72 | `            raise ValueError("line 2 pair '%s'" % pair)` | If not: raises an error that shows the pair. |
| 73 | `        head[k] = v` | Stores the pair. |
| 74 | `    for k in ("step", "session", "cpu", "bytes", "proc", "seed", "test"):` | Starts a loop over the 7 keys that every plan must have: `step`, `session`, `cpu`, `bytes`, `proc`, `seed` and `test`. |
| 75 | `        if k not in head:` | Rule: the key is in the header. |
| 76 | `            raise ValueError("line 2 lacks " + k)` | If not: raises an error that names the missing key. |
| 77 | `    if lines[2] != "# trial cond rep prev pfx pred tgt nwin win_ms count bins":` | Rule: the third line is exactly the list of the 11 column names. |
| 78 | `        raise ValueError("line 3")` | If not: raises an error with the text `line 3`. |
| 79 | `    total = int(head["bytes"])` | `total`: the buffer size of the process in bytes, from the header. |
| 80 | `    seen = collections.Counter()` | `seen`: how often each condition label was used up to now. |
| 81 | `    trials = []` | `trials`: the result list, empty at first. |
| 83 | `    def size_ok(tok):` | Starts the inner function `size_ok`. It tests the size of a phase or of a target. |
| 84 | `        b = nbytes(tok)` | `b`: the size in bytes. |
| 85 | `        return b > 0 and b % 256 == 0 and b <= total` | Rule: the size is above 0, a multiple of 256 bytes, and not larger than the buffer of the process. |
| 87 | `    for n, line in enumerate(lines[3:]):` | Starts the loop over the trial lines. `n` counts from 0. |
| 88 | `        f = line.split(" ")` | Splits the line at single blanks. |
| 89 | `        if len(f) != 11 or "" in f:` | Rule: the line has exactly 11 fields, and none is empty. An empty field means two blanks in a row. |
| 90 | `            raise ValueError("trial line %d: fields" % n)` | If not: raises an error that names the trial line and the word `fields`. |
| 91 | `        trial, cond, rep, prev, pfx, pred, tgt, nwin, win_ms, count, bins = f` | Gives the 11 fields their names. |
| 92 | `        if trial != str(n):` | Rule: the trial number is the number of the line, counted from 0. |
| 93 | `            raise ValueError("trial line %d: number" % n)` | If not: raises an error with the word `number`. |
| 94 | `        if not COND.match(cond):` | Rule: the condition label matches the pattern `COND`. |
| 95 | `            raise ValueError("trial line %d: cond" % n)` | If not: raises an error with the word `cond`. |
| 96 | `        seen[cond] += 1` | Counts the use of this label. |
| 97 | `        if rep != str(seen[cond]) or not 1 <= seen[cond] <= 4:` | Rule: `rep` is the number of this use of the label, counted from 1. A label is used at most 4 times. |
| 98 | `            raise ValueError("trial line %d: rep" % n)` | If not: raises an error with the word `rep`. |
| 99 | `        ms = {}` | `ms`: the duration in ms of each of the three phases before the target. |
| 100 | `        for name, tok in (("prev", prev), ("pfx", pfx), ("pred", pred)):` | Starts a loop over the three phases: the previous activity, the prefix and the predecessor. |
| 101 | `            ms[name] = 0` | The duration is 0 unless the phase exists. |
| 102 | `            if tok == "-":` | A `-` means that the trial has no such phase. |
| 103 | `                continue` | Goes on with the next phase. |
| 104 | `            m = PHASE.match(tok)` | Matches the text with the pattern `PHASE`. |
| 105 | `            if not m or m.group(1) not in KERNELS or not size_ok(m.group(2)) or int(m.group(3)) < 1:` | Rules for a phase: the text has the form of `PHASE`, the kernel is one of `KERNELS`, the size passes `size_ok`, and the duration is at least 1 ms. |
| 106 | `                raise ValueError("trial line %d: %s" % (n, name))` | If not: raises an error that names the phase. |
| 107 | `            ms[name] = int(m.group(3))` | Stores the duration. |
| 108 | `        if ms["pfx"] % 4:` | Rule: the duration of the prefix is a multiple of 4 ms. By the contract the runner records a prefix as 4 windows of a quarter of its duration. |
| 109 | `            raise ValueError("trial line %d: pfx not a multiple of 4" % n)` | If not: raises an error that says so. |
| 110 | `        m = TGT.match(tgt)` | Matches the target text with the pattern `TGT`. |
| 111 | `        if not m or m.group(1) not in KERNELS or not size_ok(m.group(2)):` | Rules for the target: the form of `TGT`, a kernel of `KERNELS`, and a size that passes `size_ok`. |
| 112 | `            raise ValueError("trial line %d: tgt" % n)` | If not: raises an error with the word `tgt`. |
| 113 | `        if not (nwin.isdigit() and 1 <= int(nwin) <= 4096 and win_ms.isdigit() and int(win_ms) >= 1):` | Rule: the number of windows is a whole number from 1 to 4096, and the window length is a whole number of at least 1 ms. |
| 114 | `            raise ValueError("trial line %d: windows" % n)` | If not: raises an error with the word `windows`. |
| 115 | `        if count not in ("closed", "open", "read") or bins not in ("0", "1"):` | Rule: the counter mode is `closed`, `open` or `read`, and `bins` is `0` or `1`. |
| 116 | `            raise ValueError("trial line %d: count or bins" % n)` | If not: raises an error with the words `count or bins`. |
| 117 | `        trials.append({"cond": cond, "rep": int(rep), "prev": prev, "pfx": pfx, "pred": pred, "tgt": tgt,` | Adds the trial as a dictionary. This line: the label, the repeat number, the three phase texts and the target. |
| 118 | `                       "nwin": int(nwin), "win_ms": int(win_ms), "count": count, "bins": int(bins),` | Continues the dictionary: the number and the length of the windows, the counter mode and the bins value. |
| 119 | `                       "ms": ms["prev"] + ms["pfx"] + ms["pred"] + int(nwin) * int(win_ms)})` | Ends the dictionary with `ms`, the nominal kernel work of the trial in ms: the three phase durations plus the number of windows times the window length. The test computes this value itself, without the generator. |
| 120 | `    return head, trials` | Returns the header dictionary and the trials. |
| 123 | `def rejected(text):` | Starts the function `rejected`. It says whether the validator refuses a plan text. |
| 124 | `    try:` | Starts the block whose error is caught. |
| 125 | `        parse_plan(text)` | Runs the validator. |
| 126 | `    except ValueError:` | The validator raised a `ValueError`. |
| 127 | `        return True` | Returns true: the text was rejected. |
| 128 | `    return False` | Returns false: the text was accepted. |

### Reading a generated folder: `gen`, `load`, `proc_ms`, `tree_bytes` (lines 131 to 195)

| Line | Source | Explanation |
|---:|---|---|
| 131 | `# ---------- reading a generated tree ----------` | Comment: the functions that read a generated folder start here. |
| 132 | `def gen(out, *opts):` | Starts the function `gen`. It runs the generator with the output folder `out` and with more options. |
| 133 | `    return subprocess.run([sys.executable, SCHED, "--out", out] + list(opts),` | Starts the generator as a new Python process and waits for its end. `sys.executable` is the Python that runs this test. The arguments are the generator, `--out` with the folder, and the other options. |
| 134 | `                          capture_output=True, text=True)` | Continues the call: the output and the error output are kept as text. The function returns the result object with the exit status and the two texts. |
| 137 | `def load(out):` | Starts the function `load`. It reads every schedule file and every plan file of a generated folder and tests their form. |
| 138 | `    """{(step, session): [process]}; a process holds its schedule row, header and trials."""` | Description text: the result maps each pair of step and session to its list of processes. A process holds its schedule row, its plan header and its trials. |
| 139 | `    tree, errors = {}, []` | `tree`: the result. `errors`: the list of the defects found. Both are empty at first. |
| 140 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 141 | `        sdir = os.path.join(out, "s%d" % session)` | `sdir`: the folder of the session. |
| 142 | `        for name in sorted(os.listdir(sdir)):` | Starts a loop over the names in the session folder, in sorted order. |
| 143 | `            if not name.endswith(".tsv"):` | A name that does not end with `.tsv`. |
| 144 | `                continue` | Skips it. Only schedule files are read here. |
| 145 | `            step = name[:-4]` | `step`: the file name without the ending `.tsv`. |
| 146 | `            rows = open(os.path.join(sdir, name)).read().split("\n")` | `rows`: the lines of the schedule file. |
| 147 | `            if rows[0] != "idx\ttag\tcpu\tbytes\tplan\targs" or rows[-1] != "":` | Rule: the first row is exactly the six column names with tabs between them, and the file ends with a newline. |
| 148 | `                errors.append("%s s%d: header or end of the schedule" % (step, session))` | If not: notes a defect of the header or of the end of the schedule. |
| 149 | `            procs = []` | `procs`: the processes of this step, empty at first. |
| 150 | `            for n, row in enumerate(rows[1:-1]):` | Starts the loop over the data rows. `n` counts from 0. |
| 151 | `                f = row.split("\t")` | Splits the row at the tabs. |
| 152 | `                if len(f) != 6 or f[0] != str(n):` | Rule for a row: it has exactly 6 columns, and its first column is the row number, counted from 0. |
| 153 | `                    errors.append("%s s%d row %d: columns or idx" % (step, session, n))` | If not: notes a defect of the columns or of the `idx` of this row. |
| 154 | `                    continue` | Goes on with the next row. |
| 155 | `                p = {"idx": n, "tag": f[1], "cpu": int(f[2]), "bytes": int(f[3]), "plan": f[4],` | `p`: the process as a dictionary: its `idx`, its tag, its CPU and its buffer size in bytes as numbers, the `plan` column. |
| 156 | `                     "args": f[5], "head": {}, "trials": []}` | Continues the dictionary: the `args` column, and an empty header and an empty list of trials. They stay empty for a process without a plan. |
| 157 | `                if f[4] != "-":` | The checks of lines 158 to 170 apply to a row with a plan file. A row of step `B6W` has `-` in the `plan` column. |
| 158 | `                    rel = "sched/s%d/%s/%s" % (session, step, f[4])` | `rel`: the plan path that the options must hold: `sched/s<session>/<step>/<plan name>`. It is relative to the folder of the run script. |
| 159 | `                    want = "--trial --cpus %d --bytes %d --plan %s" % (p["cpu"], p["bytes"], rel)` | `want`: the `args` text that the row must have: `--trial`, `--cpus` with the CPU of the row, `--bytes` with its size, and `--plan` with that path. |
| 160 | `                    if f[5] != want:` | Rule: the `args` are exactly that text. So a row of round 1 holds no other option, and the CPU and the size in the options agree with the columns. |
| 161 | `                        errors.append("%s s%d row %d: args" % (step, session, n))` | If not: notes a defect of the `args` of this row. |
| 162 | `                    try:` | Starts the block whose errors are caught. |
| 163 | `                        p["head"], p["trials"] = parse_plan(open(os.path.join(sdir, step, f[4])).read())` | Reads the plan file from the folder of the step and puts it through the validator. The header pairs and the trials go into the process. |
| 164 | `                    except (ValueError, OSError) as e:` | Catches a defect that the validator found, and a file that cannot be read. |
| 165 | `                        errors.append("%s s%d row %d: %s" % (step, session, n, e))` | Notes the defect with its text. |
| 166 | `                        continue` | Goes on with the next row. The process is not added to the list. |
| 167 | `                    h = p["head"]` | `h`: the header pairs of the plan. |
| 168 | `                    if (h["step"], h["session"], h["cpu"], h["bytes"], h["proc"]) != \` | Rule: five header pairs agree with the schedule: `step`, `session`, `cpu`, `bytes` and `proc`. |
| 169 | `                            (step, str(session), f[2], f[3], f[0]):` | Continues the comparison: the step and the session of the file name, and the columns `cpu`, `bytes` and `idx` of the row as texts. |
| 170 | `                        errors.append("%s s%d row %d: header pairs differ from the row" % (step, session, n))` | If not: notes that the header pairs differ from the row. So a plan file cannot belong to another row. |
| 171 | `                procs.append(p)` | Adds the process to the list. |
| 172 | `            tags = [p["tag"] for p in procs]` | `tags`: the tags of all processes of the step. |
| 173 | `            if len(set(tags)) != len(tags):` | Rule: no tag occurs twice in a step. |
| 174 | `                errors.append("%s s%d: a tag occurs twice" % (step, session))` | If not: notes that a tag occurs twice. The run script `run_bwx8.sh` writes the tag, and not the `idx`, into the lines `-- killed` and `-- failed` of the output file. |
| 175 | `            tree[step, session] = procs` | Stores the processes of the step and session. |
| 176 | `    return tree, errors` | Returns the result and the list of defects. |
| 179 | `def proc_ms(p):` | Starts the function `proc_ms`: the nominal kernel work of one process in ms. |
| 180 | `    if p["plan"] == "-":` | Tests whether the process has no plan. Then it is a process of the interval mode. |
| 181 | `        a = p["args"].split()` | `a`: its options, split at the blanks into words. |
| 182 | `        return len(a[a.index("--seq") + 1].split(",")) * int(a[a.index("--rounds") + 1]) * \` | Returns the nominal kernel work: the number of entries of the kernel sequence after `--seq`, times the number after `--rounds`. The backslash joins the next line to this statement. |
| 183 | `            int(a[a.index("--min-ms") + 1])` | Continues the product: times the number of ms after `--min-ms`. The test computes this value itself, without the generator. |
| 184 | `    return sum(t["ms"] for t in p["trials"])` | Returns the sum of the `ms` values of its trials. |
| 187 | `def tree_bytes(out):` | Starts the function `tree_bytes`. It reads every file of a folder tree into memory. |
| 188 | `    d = {}` | `d`: the result, empty at first. |
| 189 | `    for root, _, files in os.walk(out):` | Starts a walk through the folder and all folders below it. |
| 190 | `        for f in files:` | Starts a loop over the files of one folder. |
| 191 | `            path = os.path.join(root, f)` | The path of the file. |
| 192 | `            d[os.path.relpath(path, out)] = open(path, "rb").read()` | Stores the bytes of the file under its path relative to the top folder. |
| 193 | `    return d` | Returns the dictionary. Two folder trees are equal when their dictionaries are equal. |

### Rules of the rows and of the CPU order: `rows_of` to `cpu_blocks` (lines 196 to 265)

| Line | Source | Explanation |
|---:|---|---|
| 196 | `# ---------- rules, each returns True if the processes obey it ----------` | Comment: the rule functions start here. By the comment each returns true when the processes obey the rule. One rule function does not: `s2_rules` (line 267) returns a list of defects, and the list is empty when the processes obey the rules. Helpers that are no rules stand between the rule functions, such as `rows_of` and `mutate_swap`. |
| 197 | `def rows_of(procs, n):` | Starts the function `rows_of`. It cuts the trials of each process into rows of `n` trials. |
| 198 | `    """{cpu: [row]}: rows of n cond labels, in schedule order."""` | Description text: the result maps each CPU to its list of rows. A row holds the condition labels of `n` trials, and the rows stand in schedule order. |
| 199 | `    rows = collections.defaultdict(list)` | `rows`: the result. `defaultdict(list)` gives a new empty list for a CPU at its first use. |
| 200 | `    for p in procs:` | Starts the loop over the processes in schedule order. |
| 201 | `        c = [t["cond"] for t in p["trials"]]` | `c`: the condition labels of all trials of the process, in order. |
| 202 | `        rows[p["cpu"]].extend(tuple(c[i:i + n]) for i in range(0, len(c), n))` | Appends the rows of this process to the list of its CPU: tuples of `n` labels that follow each other. |
| 203 | `    return rows` | Returns the dictionary. |
| 206 | `def perms_four_times(rows):` | Starts the function `perms_four_times`, the rule of the method `perm_rows` of the generator. |
| 207 | `    """24 rows: each of the six orders of three labels four times."""` | Description text: there are 24 rows, and each of the six orders of three labels occurs four times. |
| 208 | `    labels = sorted(set(itertools.chain(*rows)))` | `labels`: all different labels of the rows, in sorted order. `itertools.chain(*rows)` joins the rows into one sequence. |
| 209 | `    want = collections.Counter({p: 4 for p in itertools.permutations(labels)})` | `want`: the expected count: the number 4 for each order of the labels. |
| 210 | `    return len(labels) == 3 and collections.Counter(rows) == want` | True when there are exactly 3 different labels and the counts of the rows equal `want`. So the 24 cycles of a CPU hold each of the 6 orders exactly 4 times. |
| 213 | `def williams(rows):` | Starts the function `williams`, the two balance rules of the design for 24 rows of 12 conditions. |
| 214 | `    """Design line 242: each ordered pair of distinct conditions twice as neighbours inside rows,` | Description text, first part: by the design (`Design line 242`), each ordered pair of two different conditions occurs twice as neighbours inside the rows. |
| 215 | `    every condition twice at every position."""` | Continues the description text: and every condition stands twice at every position. |
| 216 | `    pairs, pos = collections.Counter(), collections.Counter()` | `pairs`: how often each ordered pair of neighbours occurs. `pos`: how often each condition stands at each position. Both are counters that start empty. |
| 217 | `    for r in rows:` | Starts the loop over the rows. |
| 218 | `        for i, c in enumerate(r):` | Starts the loop over the conditions of a row. `i` is the position, counted from 0. |
| 219 | `            pos[c, i] += 1` | Counts the condition at this position. |
| 220 | `            if i:` | Tests whether the condition is not the first one of its row. |
| 221 | `                pairs[r[i - 1], c] += 1` | If so: counts the ordered pair of the condition before it and this condition. A pair across two rows is not counted. |
| 222 | `    return len(rows) == 24 and len(pairs) == 132 and set(pairs.values()) == {2} and \` | True when there are 24 rows and 132 different pairs, and every pair occurs exactly 2 times. 132 is 12 times 11. The backslash joins the next line. |
| 223 | `        len(pos) == 144 and set(pos.values()) == {2}` | Continues the condition: and there are 144 different combinations of a condition and a position, each exactly 2 times. So the order of the trials is balanced for the condition before a trial and for the position in a cycle. |
| 226 | `START = [0, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6]` | `START`: the start order of the design, written here a second time: 0, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6. |
| 229 | `def from_start_order(rows):` | Starts the function `from_start_order`. It tests that the rows were built in the way that the design gives. |
| 230 | `    """The 24 rows are the 12 shifts of the start order under one relabelling, each twice."""` | Description text: the 24 rows are the 12 shifts of the start order under one new numbering of the conditions, each shift twice. |
| 231 | `    if len(rows) != 24 or len(set(rows[0])) != 12:` | Tests the shape first: 24 rows, and 12 different labels in the first row. |
| 232 | `        return False` | If not: returns false. |
| 233 | `    label = {START[i]: rows[0][i] for i in range(12)}` | `label`: the numbering that makes the first row the start order without a shift: the number at place `i` of `START` stands for the label at place `i` of the first row. |
| 234 | `    shifts = {tuple(label[(x + d) % 12] for x in START): d for d in range(12)}` | `shifts`: the 12 rows that the shifts 0 to 11 give under this numbering, each mapped to its shift number `d`. A shift adds `d` to every number of the start order and takes the rest of a division by 12. |
| 235 | `    return all(r in shifts for r in rows) and \` | True when every row is one of these 12 shifted rows. The second condition follows in the next line. |
| 236 | `        collections.Counter(shifts[r] for r in rows) == collections.Counter({d: 2 for d in range(12)})` | Continues the condition: and each shift number occurs exactly 2 times. This is stronger than the balance rule: it ties the rows to the construction of the design. |
| 239 | `def shift_seq(rows):` | Starts the function `shift_seq`. |
| 240 | `    """The shift number of each row, counted from the first row (which gets 0)."""` | Description text: it returns the shift number of each row, counted from the first row, which gets 0. |
| 241 | `    label = {START[i]: rows[0][i] for i in range(12)}` | `label`: the numbering of line 233, built from the first row in the same way. |
| 242 | `    shifts = {tuple(label[(x + d) % 12] for x in START): d for d in range(12)}` | `shifts`: the 12 shifted rows with their shift numbers, as in line 234. |
| 243 | `    return [shifts.get(r) for r in rows]` | Returns the list of the shift numbers of the rows. A row that is no shift gives `None`. |
| 246 | `def rows_shuffled(rows):` | Starts the function `rows_shuffled`, the rule for the shuffle of the 24 rows. |
| 247 | `    """Design line 242, 'shuffle the 24 rows, and assign them to the 6 processes x 4 cycles': the rows` | Description text, first part: the design asks to shuffle the 24 rows and to give them to the 6 processes with 4 cycles each (`Design line 242`). The rule itself starts at the end of this line and goes on in the next one. |
| 248 | `    are not the 12 shifts in order, twice, and no two processes (4 rows each) hold the same rows in` | Continues the text with the rule: the rows are not the 12 shifts in order, twice. And no two processes, with 4 rows each, hold the same rows in the same order. |
| 249 | `    the same order. Without the shuffle, processes 1 to 3 and 4 to 6 of a CPU would run the same cycles."""` | Continues the text with the reason: without the shuffle, the processes 1 to 3 and the processes 4 to 6 of a CPU would run the same cycles. |
| 250 | `    groups = [tuple(rows[i:i + 4]) for i in range(0, len(rows), 4)]` | `groups`: the rows in groups of 4. Each group holds the 4 rows of one process. |
| 251 | `    return shift_seq(rows) != list(range(12)) * 2 and len(set(groups)) == len(groups)` | True when the shift numbers are not 0 to 11 in order, twice, and all groups differ. |
| 254 | `def order_varies(seqs):` | Starts the function `order_varies`, the rule that the sequences of rows are drawn at random. |
| 255 | `    """Design lines 209 and 226, 'saved random assignment': the row sequences of the CPUs and sessions` | Description text, first part: the design asks for a saved random assignment (the text gives the places as `Design lines 209 and 226`). The rule itself starts at the end of this line and goes on in the next one. |
| 256 | `    are not one fixed list. All sequences differ, and none repeats its first 6 rows."""` | Continues the text with the rule: the row sequences of the CPUs and sessions are not one fixed list. All sequences differ, and no sequence is its own first 6 rows repeated. |
| 257 | `    seqs = [tuple(q) for q in seqs]` | Turns each sequence into a tuple. Tuples can be compared and can be put into a set. |
| 258 | `    return len(set(seqs)) == len(seqs) and all(q[:6] * (len(q) // 6) != q for q in seqs)` | True when all sequences differ, and no sequence equals its first 6 rows repeated to its full length. |
| 261 | `def cpu_blocks(procs, first, second):` | Starts the function `cpu_blocks`, the rule for the CPU order of a schedule. |
| 262 | `    """The CPUs alternate first, second, first, ... when equal neighbours are merged."""` | Description text: when equal neighbours are merged, the CPUs of the processes alternate: the first CPU, the second, the first, and so on. |
| 263 | `    seq = [k for k, _ in itertools.groupby(p["cpu"] for p in procs)]` | `seq`: the CPUs of the processes in schedule order, with each run of equal neighbours merged to one entry. |
| 264 | `    return len(seq) % 2 == 0 and all(c == (first, second)[i % 2] for i, c in enumerate(seq))` | True when the merged list has an even length and alternates, with `first` at its start. |

### Rules of step `S2` and small helpers (lines 266 to 352)

| Line | Source | Explanation |
|---:|---|---|
| 267 | `def s2_rules(procs, cpus):` | Starts the function `s2_rules`, the rules of step `S2`. `procs`: the processes of one session. `cpus`: the expected CPU order. |
| 268 | `    """Stage 2 order rules (design lines 207 to 209). Returns a list of defects."""` | Description text: the order rules of Stage 2 of the design (the text gives the place as `design lines 207 to 209`). The function returns a list of defects. An empty list means that the schedule obeys the rules. |
| 269 | `    bad = []` | `bad`: the list of defects, empty at first. |
| 270 | `    assign = set()` | `assign`: for each size and CPU, the table that says which replicate set has which kernel order. It is a set, so equal tables count once. |
| 271 | `    sets = collections.defaultdict(list)` | `sets`: for each size and CPU, the list of its processes. |
| 272 | `    for p in procs:` | Starts a loop over all processes. |
| 273 | `        h, t = p["head"], p["trials"]` | `h`: the header pairs of the process. `t`: its trials. |
| 274 | `        k, s = h.get("kernel"), p["tag"].split("-")[1]` | `k`: the kernel from the header. `s`: the size text from the tag, its second part. |
| 275 | `        if len(t) != 4 or any(x != {"cond": "K=%s\|S=%s" % (k, s), "rep": i + 1, "prev": "-",` | Rule for the trials: the process has exactly 4 trials, and each equals the expected trial. The expected trial has the label `K=<kernel>\|S=<size>`, the repeat number 1 to 4, and no previous activity. |
| 276 | `                                    "pfx": "%s@%s:%d" % (k, s, t[0]["win_ms"] * 4), "pred": "-",` | Continues the expected trial: the prefix is the same kernel and size for 4 times the window length, and there is no predecessor. The window length is taken from the first trial, so the rule also fits a folder made with a test divisor. |
| 277 | `                                    "tgt": "%s@%s" % (k, s), "nwin": 4, "win_ms": t[0]["win_ms"],` | Continues: the target is the same kernel and size, with 4 windows of that length. |
| 278 | `                                    "count": "closed", "bins": 0, "ms": t[0]["win_ms"] * 8}` | Continues: the counter mode `closed`, no bins, and a nominal work of 8 times the window length. |
| 279 | `                              for i, x in enumerate(t)):` | Ends the test: the loop over the 4 trials with their numbers. |
| 280 | `            bad.append("process %d: not 4 trials of one kernel with itself as prefix" % p["idx"])` | If not: notes that the process is not 4 trials of one kernel with itself as the prefix. This is the form that the design gives for Stage 2: one read kernel per process. |
| 281 | `        if nbytes(s) != p["bytes"] or h.get("size") != str(p["bytes"]):` | Rule: the size text of the tag gives the buffer size of the row, and the header pair `size` holds the same number. |
| 282 | `            bad.append("process %d: size" % p["idx"])` | If not: notes a defect of the size of this process. |
| 283 | `        sets[s, p["cpu"]].append((int(h.get("rep_set", 0)), k, p["idx"]))` | Adds the process to the list of its size and CPU: its replicate set as a number (0 when the header has none), its kernel and its `idx`. |
| 284 | `    if sorted({s for s, _ in sets}, key=nbytes) != ["32K", "1M", "4M", "8M", "16M"]:` | Rule: the sizes of the step, sorted by their bytes, are exactly 32 KiB, 1 MiB, 4 MiB, 8 MiB and 16 MiB. |
| 285 | `        bad.append("sizes")` | If not: notes the defect `sizes`. |
| 286 | `    for (s, cpu), members in sets.items():` | Starts the loop over the pairs of a size and a CPU. |
| 287 | `        orders = collections.defaultdict(list)` | `orders`: for each replicate set of this size and CPU, the list of its kernels in schedule order. |
| 288 | `        for r, k, _ in members:` | Starts the loop over the processes of this size and CPU. |
| 289 | `            orders[r].append(k)` | Appends the kernel to the list of its replicate set. |
| 290 | `        if sorted(orders) != [1, 2, 3, 4, 5, 6] or \` | Rule, first half: the replicate sets have exactly the numbers 1 to 6. The backslash joins the next line. |
| 291 | `                {tuple(o) for o in orders.values()} != set(itertools.permutations(KERNELS)):` | Second half: the kernel orders of the 6 sets are exactly the 6 possible orders of the three kernels. So each order is used once, and each kernel is first, second and third equally often. |
| 292 | `            bad.append("size %s cpu %d: the six sets do not use the six kernel orders once each" % (s, cpu))` | If not: notes that the six sets of this size and CPU do not use the six kernel orders once each. |
| 293 | `        assign.add(tuple(tuple(orders[r]) for r in sorted(orders)))` | Adds the table of this size and CPU to `assign`: the kernel orders of its sets 1 to 6. |
| 294 | `    # Design line 209, 'with a saved random assignment': which set gets which order is drawn per size and CPU.` | Comment: the design asks for a saved random assignment (`Design line 209`). So the choice of which set gets which order is drawn again for each size and CPU. |
| 295 | `    if len(assign) < 2:` | Rule: at least two pairs of size and CPU have different tables. |
| 296 | `        bad.append("every size and CPU gives the same kernel order to the same set")` | If not: notes that every size and CPU gives the same kernel order to the same set. That would show that the assignment is fixed and not drawn. |
| 297 | `    # Process order: replicate block, then size, then CPU in session order, then the three kernels.` | Comment: the order of the processes: the replicate block, then the size, then the CPU in the order of the session, then the three kernels. |
| 298 | `    size_orders = set()` | `size_orders`: the different size orders of the 6 blocks, as a set. |
| 299 | `    for r in range(6):` | Starts the loop over the 6 replicate sets, by their place in the schedule. |
| 300 | `        block = procs[30 * r:30 * r + 30]` | `block`: the 30 processes of the replicate set `r+1`: the places `30 * r` to `30 * r + 29` of the schedule. 30 is 5 sizes times 2 CPUs times 3 kernels. |
| 301 | `        if any(p["head"].get("rep_set") != str(r + 1) for p in block) or len(block) != 30:` | Rule: the block has 30 processes, and each has the header pair `rep_set` with the value `r+1`. |
| 302 | `            bad.append("block %d: rep_set" % (r + 1))` | If not: notes a defect of the `rep_set` value of this block. |
| 303 | `            continue` | Goes on with the next block. |
| 304 | `        sizes = []` | `sizes`: the sizes of the block in schedule order. |
| 305 | `        for g in range(5):` | Starts the loop over the 5 groups of the block. A group is the 6 processes of one size. |
| 306 | `            six = block[6 * g:6 * g + 6]` | `six`: the 6 processes of the group. |
| 307 | `            if len({p["bytes"] for p in six}) != 1 or [p["cpu"] for p in six] != [cpus[0]] * 3 + [cpus[1]] * 3:` | Rule: the 6 processes have one size, and their CPUs are the first CPU of the session 3 times and then the second CPU 3 times. |
| 308 | `                bad.append("block %d group %d: size or CPU order" % (r + 1, g))` | If not: notes a defect of the size or of the CPU order of this group. |
| 309 | `            sizes.append(six[0]["bytes"])` | Adds the size of the group to `sizes`. |
| 310 | `        if len(set(sizes)) != 5:` | Rule: the 5 groups of the block have 5 different sizes. |
| 311 | `            bad.append("block %d: a size is missing" % (r + 1))` | If not: notes that a size is missing in this block. |
| 312 | `        size_orders.add(tuple(sizes))` | Remembers the size order of this block. |
| 313 | `    if len(size_orders) < 2:` | Rule: at least two blocks have different size orders. |
| 314 | `        bad.append("the size order is the same in every block")` | If not: notes that the size order is the same in every block. That would show that the sizes are not shuffled. |
| 315 | `    return bad` | Returns the list of defects. |
| 318 | `def s2_fixed_assignment(procs):` | Starts the function `s2_fixed_assignment`. It builds a damaged schedule for the check of lines 439 to 442. |
| 319 | `    """A copy of a Stage 2 schedule in which set r of every size and CPU uses the same kernel order."""` | Description text: a copy of a schedule of Stage 2 in which the set `r` of every size and CPU uses the same kernel order. |
| 320 | `    m = copy.deepcopy(procs)` | `m`: an independent copy of the processes. |
| 321 | `    fixed = list(itertools.permutations(KERNELS))` | `fixed`: the 6 orders of the three kernels as a fixed list. |
| 322 | `    for i in range(0, len(m), 3):` | Starts the loop over the schedule in steps of 3. The 3 processes from `i` on are one replicate set of one size and CPU. |
| 323 | `        for p, k in zip(m[i:i + 3], fixed[int(m[i]["head"]["rep_set"]) - 1]):` | Starts the loop over the 3 processes and over the 3 kernels of the fixed order with the number of the replicate set minus 1. |
| 324 | `            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]` | `s`: the size text from the tag. `ms`: the window length of the first trial. |
| 325 | `            p["tag"] = "-".join(p["tag"].split("-")[:3] + [k])` | Puts the new kernel into the tag, in place of its last part. |
| 326 | `            p["head"]["kernel"] = k` | Puts the new kernel into the header. |
| 327 | `            for t in p["trials"]:` | Starts the loop over the trials of the process. |
| 328 | `                t.update(cond="K=%s\|S=%s" % (k, s), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))` | Puts the new kernel into the label, the prefix and the target of the trial. |
| 329 | `    return m` | Returns the changed copy. Each size and CPU still uses the six orders once each. Only the random assignment is gone. |
| 332 | `def same_kernel(t, k, s):` | Starts the function `same_kernel`. It tests whether the trial `t` has the form of a same-kernel trial for the kernel `k` and the size `s`. |
| 333 | `    return t["prev"] == "-" and t["pred"] == "-" and t["tgt"] == "%s@%s" % (k, s) and \` | True when the trial has no previous activity and no predecessor, and its target is `k@s`. The backslash joins the next line. |
| 334 | `        t["pfx"] == "%s@%s:%d" % (k, s, 4 * t["win_ms"]) and t["nwin"] == 4` | Continues the condition: the prefix is `k@s` for 4 times the window length, and the trial has 4 windows. |
| 337 | `def cond_dict(cond):` | Starts the function `cond_dict`. |
| 338 | `    return dict(x.split("=") for x in cond.split("\|"))` | Returns the pairs of a condition label as a dictionary. The label is split at each vertical bar, and each part at its equals sign. `K=read\|S=8M` gives the key `K` with the value `read` and the key `S` with the value `8M`. |
| 341 | `def per_cpu_count(procs, n):` | Starts the function `per_cpu_count`. |
| 342 | `    return collections.Counter(p["cpu"] for p in procs) == collections.Counter({2: n, 41: n})` | True when exactly `n` processes run on CPU 2 and exactly `n` on CPU 41, and none on another CPU. |
| 345 | `def mutate_swap(procs):` | Starts the function `mutate_swap`. It builds a damaged schedule for the checks that a rule can fail. |
| 346 | `    """A copy with the first two trials of the first process exchanged."""` | Description text: a copy with the first two trials of the first process exchanged. |
| 347 | `    m = copy.deepcopy(procs)` | `m`: an independent copy of the processes. |
| 348 | `    t = m[0]["trials"]` | `t`: the trials of the first process of the copy. |
| 349 | `    t[0], t[1] = t[1], t[0]` | Exchanges its first two trials. |
| 350 | `    return m` | Returns the copy. |

### `schedule_checks`: the generator runs, the validator can fail, counts and report (lines 353 to 399)

| Line | Source | Explanation |
|---:|---|---|
| 353 | `def schedule_checks(tmp):` | Starts the function `schedule_checks`. It holds all checks of the generator. |
| 354 | `    a, b, c = (os.path.join(tmp, n) for n in ("a", "b", "c"))` | `a`, `b`, `c`: three output folders in the temporary folder `tmp`. |
| 355 | `    r = gen(a, "--select", SELECT)` | Runs the generator into the folder `a`, with `--select` and the two pairs of `SELECT`. `r` keeps its exit status and its output. |
| 356 | `    check("schedule8.py runs with status 0", r.returncode == 0, r.stderr)` | Check: the generator ends with exit status 0. The generator gives status 1 when one of its own balance checks fails. So this check also shows that those checks passed. |
| 357 | `    tree, errors = load(a)` | Reads the generated folder and collects the format defects. |
| 358 | `    check("every schedule row and plan file obeys the format and the plan grammar", not errors, errors[:3])` | Check: `load` found no defect. So every schedule row has the right form, and every plan file passes the validator of this file. This matters: the runner ends with status 2 for a plan with a defect. |
| 359 | `    check("all 11 steps exist in both sessions", len(tree) == 22, sorted(tree))` | Check: the folder holds 22 schedules, that is 11 steps in 2 sessions. With `--select` the steps `BIN` and `CS` are written too. The detail for a failure lists the steps and sessions that were found. |
| 361 | `    # The validator itself rejects defective plans.` | Comment: the next checks show that the validator itself rejects plans with a defect. |
| 362 | `    good = open(os.path.join(a, "s1", "S3", "0000.plan")).read()` | `good`: the text of a generated plan: the plan of the first process of step `S3` in session 1. It has 48 trial lines. |
| 363 | `    line = good.split("\n")[3]` | `line`: the fourth line of `good`, the line of its first trial. |
| 364 | `    bad = {"rep out of order": good.replace(" 1 - ", " 2 - ", 1),` | `bad`: 11 damaged copies of `good`, each under a name that says what is wrong. The first: the repeat number of the first trial is 2 in place of 1. The replaced text is the repeat number 1 and the `-` of the missing previous activity. It occurs first in the first trial line. |
| 365 | `           "prefix not a multiple of 4": good.replace("oldread@8M:1200", "oldread@8M:1202", 1),` | The first prefix `oldread@8M:1200` gets the duration 1202 ms, which is not a multiple of 4. |
| 366 | `           "size above bytes": good.replace(line, line.replace("oldread@8M:1200", "oldread@16M:1200")),` | In the first trial line the prefix gets the size 16 MiB. That is above the buffer size of 8 MiB in the header. |
| 367 | `           "unknown kernel": good.replace(line, line.replace("oldread@8M:1200", "copy@8M:1200")),` | In the first trial line the prefix gets the kernel `copy`, which the validator does not accept. |
| 368 | `           "two spaces": good.replace(line, line.replace(" ", "  ", 1)),` | Two blanks in place of the first blank of the trial line. |
| 369 | `           "trial number": good.replace("\n1 ", "\n7 ", 1),` | The second trial line gets the trial number 7 in place of 1. |
| 370 | `           "wrong first line": good.replace("plan v1", "plan v2"),` | The first line names version 2 of the format. |
| 371 | `           "count word": good.replace(line, line.replace("closed", "shut")),` | The counter mode is the word `shut`, which does not exist. |
| 372 | `           "size not a multiple of 256": good.replace(line, line[:line.rindex("@8M")] + "@1000" + line[line.rindex("@8M") + 3:]),` | The last size of the first trial line, which is the size of the target, becomes 1000 bytes. `rindex` finds the last `@8M` of the line. 1000 is not a multiple of 256. |
| 373 | `           "comma in cond": good.replace(line, line.replace("\|", ",", 1)),` | A comma in place of the first vertical bar of the condition label. |
| 374 | `           "header lacks seed": good.replace(" seed=", " sead=")}` | The header key `seed` is written `sead`, so the required key is missing. The brace ends the dictionary. |
| 375 | `    check("validator accepts a generated plan", not rejected(good))` | Check: the validator accepts the plan as the generator wrote it. So a rejection in the next checks comes from the damage and from nothing else. |
| 376 | `    for name, text in bad.items():` | Starts a loop over the damaged plans. |
| 377 | `        check("validator rejects: " + name, text != good and rejected(text))` | Check, once per damaged plan: the damage changed the text, and the validator rejects it. The first condition catches a replacement that found nothing to replace. These checks show that the validator can fail. Without them a validator that accepts everything would pass the check of line 358. |
| 379 | `    # Counts and nominal work, from the files.` | Comment: the next checks take the counts and the nominal work from the generated files, not from the report of the generator. |
| 380 | `    for step, (n, sec) in NOMINAL.items():` | Starts a loop over the 7 steps of `NOMINAL`. `n` is the expected number of processes and `sec` the expected seconds, both for the two sessions together. |
| 381 | `        procs = tree[step, 1] + tree[step, 2]` | `procs`: the processes of the step in both sessions, as read from the files. |
| 382 | `        ms = sum(proc_ms(p) for p in procs)` | `ms`: the sum of their nominal kernel work in ms, computed by `proc_ms` of this file. |
| 383 | `        check("%s: %d processes and %.1f s of nominal kernel work in both sessions" % (step, n, sec),` | Starts a check per step: the number of processes and the seconds of nominal kernel work in both sessions are the values of the contract. |
| 384 | `              len(procs) == n and ms == round(sec * 1000), (len(procs), ms))` | The test: the number of processes equals `n`, and the ms equal `sec` times 1000, rounded to a whole number. The detail for a failure shows both found values. So the files hold the work that the design plans for the step, no more and no less. |
| 385 | `    short = copy.deepcopy(tree["S2", 1] + tree["S2", 2])` | `short`: an independent copy of the processes of `S2` in both sessions. |
| 386 | `    short[0]["trials"].pop()` | Removes the last trial of its first process. |
| 387 | `    check("nominal work: a schedule with one trial missing does not give the S2 value",` | Starts a check: a schedule with one trial missing does not give the value of `S2`. |
| 388 | `          sum(proc_ms(p) for p in short) != 3456000)` | The test: the sum of the copy is not 3456000 ms. So the check of lines 383 to 384 can fail: it sees one missing trial among the 1440 trials of `S2`. |
| 389 | `    for step, (n, tr) in TABLE.items():` | Starts a loop over the 11 steps of `TABLE`. `n` is the expected number of processes per session and `tr` the expected number of trials per process. |
| 390 | `        for s in (1, 2):` | Starts a loop over the two sessions. |
| 391 | `            procs = tree[step, s]` | `procs`: the processes of this step and session, as read from the files. |
| 392 | `            check("%s session %d: %d processes of %d trials" % (step, s, n, tr),` | Starts a check per step and session: the number of processes and the trials per process are the values of the contract. |
| 393 | `                  len(procs) == n and all(len(p["trials"]) == tr for p in procs))` | The test: the step has `n` processes, and every process has `tr` trials. |
| 394 | `    for step, (n, sec) in NOMINAL.items():` | Starts a second loop over the steps of `NOMINAL`. It tests the report that the generator printed. |
| 395 | `        want = "%s total: %d processes, " % (step, n)` | `want`: the start of the total line that the report must hold for the step: the step, the word `total:` and the number of processes. |
| 396 | `        hit = [l for l in r.stdout.split("\n") if l.startswith(want)]` | `hit`: the lines of the output of the generator that start with this text. |
| 397 | `        check("report prints the %s total" % step,` | Starts a check per step: the report prints the total of the step. |
| 398 | `              len(hit) == 1 and ("nominal kernel work %g s " % sec) in hit[0], hit)` | The test: exactly one such line exists, and it holds the words `nominal kernel work` with the expected seconds. So the numbers that a person reads in the report are the numbers of the contract. The detail for a failure shows the lines that were found. |

### `schedule_checks`: header pairs and CPU order (lines 400 to 421)

| Line | Source | Explanation |
|---:|---|---|
| 400 | `    # Header pairs that the analysis groups by.` | Comment: the next checks test the header pairs by which the analysis groups the processes. |
| 401 | `    check("plan headers: seed is one value per step and session, test=0",` | Starts a check: inside one step and session every plan has the same seed, and every plan has `test=0`. |
| 402 | `          all(len({p["head"]["seed"] for p in procs}) == 1 and all(p["head"]["test"] == "0" for p in procs)` | The test: the set of the seed values of a step and session has one member, and the `test` value of every plan is `0`. |
| 403 | `              for (step, _), procs in tree.items() if step != "B6W"))` | Continues the test: the loop over all steps and sessions other than `B6W`, which has no plan files. |
| 404 | `    check("plan headers: the seeds of the steps and sessions differ",` | Starts a check: the seeds of the steps and sessions differ. |
| 405 | `          len({procs[0]["head"]["seed"] for (step, _), procs in tree.items() if step != "B6W"}) == 20)` | The test: the seeds of all steps and sessions other than `B6W` form a set of 20 members. That is 10 steps times 2 sessions. So each step and session has a random sequence of its own. |
| 406 | `    check("plan headers: kernel and size where a process has one kernel",` | Starts a check: a process with one kernel names that kernel and its size in the header. |
| 407 | `          all(all(p["head"].get("kernel") in KERNELS and p["head"].get("size") == str(p["bytes"])` | The test, for every process of the five steps that line 409 names: the header pair `kernel` is one of the three kernels, and the pair `size` equals the buffer size of the row. |
| 408 | `                  and {t["tgt"].split("@")[0] for t in p["trials"]} == {p["head"]["kernel"]} for p in procs)` | Continues: the target kernel of every trial of the process is that kernel. So the analysis can trust the header when it groups the processes by kernel and size. |
| 409 | `              for (step, _), procs in tree.items() if step in ("S2", "S4", "C4", "BIN", "CS")))` | The loop: the steps `S2`, `S4`, `C4`, `BIN` and `CS`. In these steps each process runs one kernel. |
| 410 | `    check("cond labels are key=value pairs that agree with the trial",` | Starts a check: the condition labels are pairs of a key and a value that agree with the fields of their trial. |
| 411 | `          all(cond_dict(t["cond"]).get("count", "closed") == t["count"]` | The test, first part: the counter mode in the label (the key `count`, or `closed` when the label has none) equals the field `count` of the trial. |
| 412 | `              and int(cond_dict(t["cond"]).get("bins", 0)) == t["bins"]` | Second part: the bins flag in the label (0 when the label has none) equals the field `bins`. |
| 413 | `              and cond_dict(t["cond"]).get("K", cond_dict(t["cond"]).get("T")) == t["tgt"].split("@")[0]` | Third part: the target kernel in the label (the key `K`, or the key `T` when there is no `K`) equals the kernel of the field `tgt`. So the label and the trial agree on the counter mode, on the bins flag and on the target kernel. This check compares no other key of the label, such as the size `S` or the predecessor `P`. The analysis reads the label. |
| 414 | `              for procs in tree.values() for p in procs for t in p["trials"]))` | The loops run over every trial of every process of every step and session. |
| 416 | `    # Session order of the CPUs.` | Comment: the checks of the CPU order of each session. |
| 417 | `    for (step, s), procs in sorted(tree.items()):` | Starts a loop over all steps and sessions, in sorted order. |
| 418 | `        first, second = (2, 41) if s == 1 else (41, 2)` | `first`, `second`: the expected CPU order: 2 then 41 in session 1, and 41 then 2 in session 2. |
| 419 | `        check("%s session %d: CPU order %d then %d" % (step, s, first, second), cpu_blocks(procs, first, second))` | Check per step and session: the CPUs of the schedule alternate in this order, with `first` at the start (`cpu_blocks`). The design asks to reverse the order of the worker CPUs in the second session. |
| 420 | `    check("CPU order rule rejects session 1 read as session 2", not cpu_blocks(tree["S3", 1], 41, 2))` | Check: the rule rejects the schedule of `S3` in session 1 when it is read with the order of session 2. So the rule of the CPU order can fail. |

### `schedule_checks`: steps `S2`, `S3` and `CM` (lines 422 to 481)

| Line | Source | Explanation |
|---:|---|---|
| 422 | `    # Stage 2.` | Comment: the checks of step `S2`, which is Stage 2 of the design. |
| 423 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 424 | `        defects = s2_rules(tree["S2", s], (2, 41) if s == 1 else (41, 2))` | `defects`: the list of defects that `s2_rules` finds in the schedule of `S2` of this session, with the CPU order of the session. |
| 425 | `        check("S2 session %d: order rules" % s, not defects, defects[:3])` | Check: the list is empty. So the schedule has the trial form, the sizes, the balanced kernel orders and the process order that the design gives for Stage 2. The detail for a failure shows the first three defects. |
| 426 | `    m = copy.deepcopy(tree["S2", 1])` | `m`: an independent copy of the schedule of `S2` in session 1, for a damaged variant. |
| 427 | `    m[0]["head"]["kernel"], m[1]["head"]["kernel"] = m[1]["head"]["kernel"], m[0]["head"]["kernel"]` | Exchanges the header pair `kernel` of the first two processes. |
| 428 | `    m[0]["trials"], m[1]["trials"] = m[1]["trials"], m[0]["trials"]` | Exchanges their trials. |
| 429 | `    m[0]["tag"], m[1]["tag"] = m[1]["tag"], m[0]["tag"]` | Exchanges their tags. Now the first replicate set of its size and CPU runs its first two kernels in the other order. |
| 430 | `    check("S2 rules reject a set whose kernel order repeats another set", bool(s2_rules(m, (2, 41))))` | Check: `s2_rules` finds a defect in this variant. The changed order equals the order of another set of the same size and CPU. So one of the six orders is used twice and one is missing. |
| 431 | `    m = copy.deepcopy(tree["S2", 1])` | `m`: a new copy. |
| 432 | `    m[2], m[3] = m[3], m[2]` | Exchanges the third and the fourth process. The third is the last process of the first CPU at the first size, and the fourth is the first process of the second CPU. |
| 433 | `    check("S2 rules reject CPUs that alternate inside a size", bool(s2_rules(m, (2, 41))))` | Check: `s2_rules` finds a defect. Inside this size the CPUs now alternate, and the rule asks for three processes on the first CPU and then three on the second. |
| 434 | `    check("S2 rules reject the session 1 schedule under the session 2 CPU order",` | Starts a check: the rules reject the schedule of session 1 when it is tested with the CPU order of session 2. |
| 435 | `          bool(s2_rules(tree["S2", 1], (41, 2))))` | The test: `s2_rules` with the order 41 then 2 returns a list that is not empty. |
| 436 | `    m = copy.deepcopy(tree["S2", 1])` | `m`: a new copy. |
| 437 | `    m[5]["trials"][0]["pfx"] = "oldread@1M:1200" if m[5]["head"]["kernel"] != "oldread" else "read@1M:1200"` | Gives the first trial of the sixth process the prefix of another kernel: `oldread` when the process runs `read` or `asmread`, and `read` when it runs `oldread`. The new prefix text names the size 1 MiB. |
| 438 | `    check("S2 rules reject a prefix of another kernel", bool(s2_rules(m, (2, 41))))` | Check: `s2_rules` finds a defect. So a process in which another kernel runs before the target does not pass as a process of one kernel. |
| 439 | `    check("S2 rules reject a schedule whose sets have the same kernel order in every size and CPU",` | Starts a check: the rules reject a schedule whose sets have the same kernel order in every size and CPU. |
| 440 | `          s2_rules(s2_fixed_assignment(tree["S2", 1]), (2, 41)) ==` | The test: `s2_rules` on the variant of `s2_fixed_assignment` returns exactly one defect. |
| 441 | `          ["every size and CPU gives the same kernel order to the same set"],` | The one expected defect: every size and CPU gives the same kernel order to the same set. So this rule alone sees the missing random assignment. All other rules still pass on this variant. |
| 442 | `          s2_rules(s2_fixed_assignment(tree["S2", 1]), (2, 41))[:3])` | The detail for a failure: the first three defects that were found. |
| 444 | `    # Stage 3 and the mixed-sequence counters: 12 conditions, design line 242.` | Comment: the checks of step `S3` (Stage 3) and of step `CM` (the mixed-sequence counters). Both have 12 conditions and follow the construction of the design. |
| 445 | `    preds = ["oldread@8M", "read@8M", "asmread@8M", "oldread@1M"]` | `preds`: the four predecessors that step `S3` must use. |
| 446 | `    s3_conds = {"P=%s\|T=%s" % (p, t) for p in preds for t in KERNELS}` | `s3_conds`: the 12 labels that step `S3` must have: each predecessor with each of the three kernels as the target. |
| 447 | `    cm_conds = {"P=%s@8M\|T=%s\|count=%s" % (p, t, m) for p in ("oldread", "read")` | `cm_conds`: the 12 labels that step `CM` must have. This line: the predecessors `oldread` and `read` on 8 MiB. |
| 448 | `                for t in ("oldread", "read") for m in ("closed", "open", "read")}` | Continues the set: with the targets `oldread` and `read`, and with the three counter modes. |
| 449 | `    for step, conds in (("S3", s3_conds), ("CM", cm_conds)):` | Starts a loop over the two steps with their expected labels. |
| 450 | `        for s in (1, 2):` | Starts a loop over the two sessions. |
| 451 | `            procs = tree[step, s]` | `procs`: the processes of this step and session. |
| 452 | `            rows = rows_of(procs, 12)` | `rows`: for each CPU, its rows of 12 labels. A row is one cycle of a process. |
| 453 | `            check("%s session %d: 6 processes per CPU, each cycle holds the 12 conditions once" % (step, s),` | Starts a check: each CPU has 6 processes, and each cycle holds the 12 conditions once. |
| 454 | `                  per_cpu_count(procs, 6) and all(set(r) == conds for rr in rows.values() for r in rr))` | The test: 6 processes on each of the CPUs 2 and 41, and the set of the labels of every row equals the expected set. A row has 12 labels. So no condition is missing, and none stands twice in a cycle. |
| 455 | `            check("%s session %d: trial is prefix oldread@8M, predecessor P, target T@8M" % (step, s),` | Starts a check of the form of every trial: the prefix is `oldread` on 8 MiB, then the predecessor of the label, then the target of the label on 8 MiB. |
| 456 | `                  all(t["prev"] == "-" and t["pfx"] == "oldread@8M:%d" % (4 * t["win_ms"])` | The test, first part: no previous activity, and the prefix `oldread@8M` for 4 times the window length. |
| 457 | `                      and t["pred"] == "%s:%d" % (cond_dict(t["cond"])["P"], t["win_ms"])` | Second part: the predecessor is the value `P` of the label, for one window length. |
| 458 | `                      and t["tgt"] == cond_dict(t["cond"])["T"] + "@8M" and t["nwin"] == 4` | Third part: the target is the value `T` of the label on 8 MiB, with 4 windows. |
| 459 | `                      for p in procs for t in p["trials"]))` | The loops run over every trial of every process of the step. So the same old read prefix stands before every predecessor, as the design asks for the mixed sequences. |
| 460 | `            for cpu in (2, 41):` | Starts a loop over the two CPUs. |
| 461 | `                check("%s session %d cpu %d: pair and position balance of line 242" % (step, s, cpu),` | Starts a check per CPU: the balance of pairs and positions that the design asks for. |
| 462 | `                      williams(rows[cpu]))` | The test: the 24 rows of the CPU pass `williams`. This matters for the question whether a predecessor changes the next rate: each condition comes equally often after each other condition and at each place of a cycle. |
| 463 | `                check("%s session %d cpu %d: rows are the shifted start order, relabelled, twice" % (step, s, cpu),` | Starts a check per CPU: the rows are the shifted start order under a new numbering, each shift twice. |
| 464 | `                      from_start_order(rows[cpu]))` | The test: the rows pass `from_start_order`. |
| 465 | `                check("%s session %d cpu %d: the 24 rows are shuffled over the processes" % (step, s, cpu),` | Starts a check per CPU: the 24 rows are shuffled over the processes. |
| 466 | `                      rows_shuffled(rows[cpu]), shift_seq(rows[cpu]))` | The test: the rows pass `rows_shuffled`. The detail for a failure shows the shift numbers of the rows. |
| 467 | `        check("%s: the order of the shifted rows differs between CPUs and sessions" % step,` | Starts a check per step: the sequence of the shifted rows differs between the CPUs and the sessions. |
| 468 | `              len({tuple(shift_seq(rows_of(tree[step, s], 12)[cpu])) for s in (1, 2) for cpu in (2, 41)}) == 4)` | The test: the four sequences of shift numbers (2 sessions times 2 CPUs) are all different. So each CPU and session has a shuffle of its own. |
| 469 | `        check("%s: the relabelling differs between CPUs and sessions" % step,` | Starts a check per step: the new numbering of the conditions differs between the CPUs and the sessions. |
| 470 | `              len({tuple(sorted(rows_of(tree[step, s], 12)[cpu])) for s in (1, 2) for cpu in (2, 41)}) == 4)` | The test: the four sorted lists of rows are all different. Sorting removes the effect of the shuffle. So two lists differ only when the numbering differs. |
| 471 | `    bad_rows = rows_of(mutate_swap([p for p in tree["S3", 1] if p["cpu"] == 2]), 12)[2]` | `bad_rows`: the rows of CPU 2 of step `S3` in session 1, after the first two trials of its first process were exchanged (`mutate_swap`). |
| 472 | `    check("balance rule rejects a schedule with two trials exchanged", not williams(bad_rows))` | Check: `williams` rejects these rows. So the balance rule sees an exchange of two trials. |
| 473 | `    check("start-order rule rejects a schedule with two trials exchanged", not from_start_order(bad_rows))` | Check: `from_start_order` rejects these rows too. |
| 474 | `    rnd = [tuple(sorted(r)) for r in rows_of(tree["S3", 1], 12)[2]]` | `rnd`: the rows of CPU 2 of step `S3` in session 1, each with its labels sorted. So all 24 rows are the same row. |
| 475 | `    check("start-order rule rejects rows that are not shifts", not from_start_order(rnd))` | Check: `from_start_order` rejects these rows. With this input every row equals the first row. The rule then finds 24 rows with the shift number 0 and rejects them, as each shift must occur exactly 2 times. So this input tests the count of the shifts. It does not test the first half of the rule, that every row is one of the 12 shifts. |
| 476 | `    good_rows = rows_of(tree["S3", 1], 12)[2]` | `good_rows`: the rows of CPU 2 of step `S3` in session 1, unchanged. |
| 477 | `    by_shift = dict(zip(shift_seq(good_rows), good_rows))` | `by_shift`: a dictionary from each shift number to one row with that number. |
| 478 | `    plain = [by_shift[d] for d in range(12)] * 2` | `plain`: the 12 shifted rows in the order of their shift numbers, and then the same 12 rows again. |
| 479 | `    check("shuffle rule rejects the 12 shifted rows in order, twice (it still obeys the balance rule)",` | Starts a check: the shuffle rule rejects the 12 shifted rows in order, twice, although these rows still obey the balance rule. |
| 480 | `          williams(plain) and from_start_order(plain) and not rows_shuffled(plain))` | The test: `plain` passes `williams` and `from_start_order`, and it does not pass `rows_shuffled`. So only the shuffle rule sees a generator that leaves out the shuffle of the rows. |

### `schedule_checks`: steps `P3`, `S3G`, `CS`, `P3G`, `S4`, `C4`, `BIN` and `B6W` (lines 482 to 569)

| Line | Source | Explanation |
|---:|---|---|
| 482 | `    # P3, S3G, CS: all six orders four times per CPU and session (CS: per kernel and size too).` | Comment: the checks of the steps `P3`, `S3G` and `CS`: all six orders four times per CPU and session, and in `CS` also per kernel and size. |
| 483 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 484 | `        for step in ("P3", "S3G"):` | Starts a loop over the steps `P3` and `S3G`. |
| 485 | `            rows = rows_of(tree[step, s], 3)` | `rows`: for each CPU, its rows of 3 labels. A row is one cycle of a process. |
| 486 | `            check("%s session %d: 6 processes per CPU; six orders four times each per CPU" % (step, s),` | Starts a check per step and session: 6 processes per CPU, and each of the six orders four times per CPU. |
| 487 | `                  per_cpu_count(tree[step, s], 6) and all(perms_four_times(rows[c]) for c in (2, 41)))` | The test: 6 processes on each of the CPUs 2 and 41, and the 24 rows of each CPU pass `perms_four_times`. So over a CPU and session no order of the three items is used more often than another. |
| 488 | `        check("P3 session %d: every trial is a kernel at 8M with itself as prefix" % s,` | Starts a check: every trial of `P3` is one kernel on 8 MiB with itself as the prefix. |
| 489 | `              all(same_kernel(t, cond_dict(t["cond"])["K"], "8M") and cond_dict(t["cond"])["S"] == "8M"` | The test: each trial passes `same_kernel` for the kernel `K` of its label and the size 8 MiB, and the label names the size 8 MiB. |
| 490 | `                  for p in tree["P3", s] for t in p["trials"]))` | The loops run over every trial of every process of `P3` in this session. |
| 491 | `        check("S3G session %d: previous J 1.2 s, prefix, predecessor and target old read" % s,` | Starts a check of the form of the trials of `S3G`: a previous activity `J` of 1.2 s, and then old read as the prefix, the predecessor and the target. |
| 492 | `              all(t["prev"] == "%s@8M:%d" % (cond_dict(t["cond"])["J"], 4 * t["win_ms"])` | The test, first part: the previous activity is the kernel `J` of the label on 8 MiB, for 4 times the window length. |
| 493 | `                  and t["pfx"] == "oldread@8M:%d" % (4 * t["win_ms"])` | Second part: the prefix is `oldread` on 8 MiB for 4 times the window length. |
| 494 | `                  and t["pred"] == "oldread@8M:%d" % t["win_ms"] and t["tgt"] == "oldread@8M"` | Third part: the predecessor is `oldread` on 8 MiB for one window length, and the target is `oldread` on 8 MiB. |
| 495 | `                  for p in tree["S3G", s] for t in p["trials"]))` | The loops run over every trial of every process of `S3G` in this session. |
| 496 | `        groups = collections.defaultdict(list)` | `groups`: the processes of `CS`, grouped by kernel, size and CPU. It is empty at first. |
| 497 | `        for p in tree["CS", s]:` | Starts the loop over the processes of `CS` in this session. |
| 498 | `            groups[p["head"]["kernel"], p["head"]["size"], p["cpu"]].append(p)` | Adds the process to the group of its header pairs `kernel` and `size` and of its CPU. |
| 499 | `        check("CS session %d: 6 processes per kernel, size and CPU; six mode orders four times each" % s,` | Starts a check: `CS` has 6 processes per kernel, size and CPU, and each of the six orders of the three counter modes four times. |
| 500 | `              len(groups) == 4 and all(len(g) == 6 and perms_four_times(rows_of(g, 3)[g[0]["cpu"]])` | The test: there are 4 groups (the 2 pairs of `SELECT` on 2 CPUs), each group has 6 processes, and its 24 rows of 3 labels pass `perms_four_times`. |
| 501 | `                                       for g in groups.values()))` | The loop runs over the groups. |
| 502 | `        check("CS session %d: modes closed, open, read on one kernel and size per process" % s,` | Starts a check: each process of `CS` runs the modes `closed`, `open` and `read` on one kernel and one size. |
| 503 | `              all({t["count"] for t in p["trials"]} == {"closed", "open", "read"}` | The test, first part: the counter modes of the trials of a process are exactly these three. |
| 504 | `                  and all(same_kernel(t, p["head"]["kernel"], cond_dict(t["cond"])["S"])` | Second part: every trial is a same-kernel trial for the kernel of the header and the size `S` of its label. |
| 505 | `                          and nbytes(cond_dict(t["cond"])["S"]) == p["bytes"] for t in p["trials"])` | Third part: that size in bytes equals the buffer size of the row. |
| 506 | `                  for p in tree["CS", s]))` | The loop runs over the processes of `CS` in this session. So the three modes are compared inside one process, with the kernel and the buffer unchanged. |
| 507 | `        # P3G: 9 conditions in each of 4 cycles.` | Comment: the checks of step `P3G`: 9 conditions in each of 4 cycles. |
| 508 | `        nine = {"J=%s\|K=%s" % (j, k) for j in KERNELS for k in KERNELS}` | `nine`: the 9 labels that `P3G` must have: each kernel as the previous activity `J` with each kernel as the target `K`. |
| 509 | `        rows = rows_of(tree["P3G", s], 9)` | `rows`: for each CPU, its rows of 9 labels. |
| 510 | `        check("P3G session %d: 6 processes per CPU, each cycle holds the 9 conditions once" % s,` | Starts a check: 6 processes per CPU, and each cycle holds the 9 conditions once. |
| 511 | `              per_cpu_count(tree["P3G", s], 6) and all(set(r) == nine for rr in rows.values() for r in rr))` | The test: 6 processes on each CPU, and the set of the labels of every row equals `nine`. |
| 512 | `        check("P3G session %d: the cycles are not all in one order" % s,` | Starts a check: the cycles are not all in one order. |
| 513 | `              all(len(set(rows[c])) > 12 for c in (2, 41)))` | The test: each CPU has more than 12 different rows among its 24. So the 9 conditions are shuffled again for the cycles. The test asks for no balance of this order, and the generator makes none. |
| 514 | `        check("P3G session %d: previous J 2.4 s, then K as prefix and target" % s,` | Starts a check of the form of the trials: a previous activity `J` of 2.4 s, then the kernel `K` as the prefix and as the target. |
| 515 | `              all(t["prev"] == "%s@8M:%d" % (cond_dict(t["cond"])["J"], 8 * t["win_ms"])` | The test, first part: the previous activity is the kernel `J` of the label on 8 MiB, for 8 times the window length. |
| 516 | `                  and t["pfx"] == "%s@8M:%d" % (cond_dict(t["cond"])["K"], 4 * t["win_ms"])` | Second part: the prefix is the kernel `K` of the label on 8 MiB, for 4 times the window length. |
| 517 | `                  and t["pred"] == "-" and t["tgt"] == cond_dict(t["cond"])["K"] + "@8M"` | Third part: there is no predecessor, and the target is `K` on 8 MiB. |
| 518 | `                  for p in tree["P3G", s] for t in p["trials"]))` | The loops run over every trial of every process of `P3G` in this session. |
| 519 | `        # S4 and C4.` | Comment: the checks of the sustained steps `S4` and `C4`. |
| 520 | `        for step, count in (("S4", "closed"), ("C4", "read")):` | Starts a loop over the two steps with their expected counter mode: `closed` for `S4` and `read` for `C4`. |
| 521 | `            procs = tree[step, s]` | `procs`: the processes of this step and session. |
| 522 | `            per = collections.Counter((p["head"]["kernel"], p["cpu"]) for p in procs)` | `per`: the number of processes for each pair of a kernel and a CPU. |
| 523 | `            triples = [procs[i:i + 3] for i in range(0, 18, 3)]` | `triples`: the 18 processes in groups of 3, in schedule order. A group is one pass of the three kernels on one CPU. |
| 524 | `            check("%s session %d: 3 processes per kernel and CPU, the three kernels in each replicate" % (step, s),` | Starts a check: 3 processes per kernel and CPU, and the three kernels in each group of 3. The name of the check calls such a group a replicate. |
| 525 | `                  set(per.values()) == {3} and len(per) == 6 and` | The test, first part: every count is 3, and there are 6 pairs of a kernel and a CPU. |
| 526 | `                  all(len({p["cpu"] for p in t}) == 1 and {p["head"]["kernel"] for p in t} == set(KERNELS)` | Second part: each group of 3 runs on one CPU and holds the three kernels once each. |
| 527 | `                      for t in triples))` | The loop runs over the groups. |
| 528 | `            check("%s session %d: one trial, no prefix, 200 windows at 8M, count %s" % (step, s, count),` | Starts a check of the form of the trials: one trial with no phase before the target, 200 windows on 8 MiB, and the counter mode of the step. |
| 529 | `                  all((t["prev"], t["pfx"], t["pred"], t["nwin"], t["count"], t["tgt"]) ==` | The test: for every trial, six of its fields are compared: the previous activity, the prefix, the predecessor, the number of windows, the counter mode and the target. |
| 530 | `                      ("-", "-", "-", 200, count, p["head"]["kernel"] + "@8M")` | The expected values: three times `-`, 200 windows, the mode of the step, and the kernel of the header on 8 MiB. |
| 531 | `                      for p in procs for t in p["trials"]))` | The loops run over every trial of every process. With the count of lines 392 to 393, which is 1 trial per process, this shows that a process runs one kernel for 200 windows and nothing before them. |
| 532 | `            check("%s session %d: the kernel order differs between replicates" % (step, s),` | Starts a check: the kernel order differs between the groups of 3. |
| 533 | `                  len({tuple(p["head"]["kernel"] for p in t) for t in triples}) > 1)` | The test: the 6 groups hold more than one kernel order. So the three kernels are not started in one fixed order. One fixed order in every group would fail. |
| 534 | `        # BIN.` | Comment: the checks of step `BIN`. |
| 535 | `        groups = collections.defaultdict(list)` | `groups`: for each kernel, size and CPU, the list of the bins orders of its processes. It is empty at first. |
| 536 | `        for p in tree["BIN", s]:` | Starts the loop over the processes of `BIN` in this session. |
| 537 | `            groups[p["head"]["kernel"], p["head"]["size"], p["cpu"]].append(` | Appends to the group of the kernel, the size and the CPU of the process. The value follows in the next line. |
| 538 | `                tuple(t["bins"] for t in p["trials"]))` | The value: the bins flags of the 8 trials of the process, as a tuple. |
| 539 | `        ab, ba = (0, 1, 1, 0, 1, 0, 0, 1), (1, 0, 0, 1, 0, 1, 1, 0)` | `ab`, `ba`: the two expected orders of the bins flag: 0, 1, 1, 0, 1, 0, 0, 1, and its mirror 1, 0, 0, 1, 0, 1, 1, 0. |
| 540 | `        check("BIN session %d: orders ABBA BAAB and BAAB ABBA alternate between processes" % s,` | Starts a check: the orders ABBA BAAB and BAAB ABBA alternate between the processes. |
| 541 | `              len(groups) == 4 and all(g == [ab, ba] * 3 for g in groups.values()), dict(groups))` | The test: there are 4 groups, and the 6 processes of each group have the orders `ab`, `ba`, `ab`, `ba`, `ab`, `ba`. So each of the two record modes is the first trial in half of the processes of a group. The detail for a failure shows the groups. |
| 542 | `        check("BIN session %d: trials as S2" % s,` | Starts a check: the trials of `BIN` have the form of the trials of `S2`. |
| 543 | `              all(same_kernel(t, p["head"]["kernel"], cond_dict(t["cond"])["S"])` | The test: every trial passes `same_kernel` for the kernel of the header and the size `S` of its label. |
| 544 | `                  for p in tree["BIN", s] for t in p["trials"]))` | The loops run over every trial of every process of `BIN` in this session. |
| 545 | `    for step in ("P3", "S3G"):` | Starts a loop over the steps `P3` and `S3G`. It runs after the loop over the sessions has ended. |
| 546 | `        check("%s: the order of the 24 rows differs between CPUs and sessions and is not one fixed list" % step,` | Starts a check per step: the sequence of the 24 rows differs between the CPUs and the sessions and is not one fixed list. |
| 547 | `              order_varies([rows_of(tree[step, s], 3)[c] for s in (1, 2) for c in (2, 41)]))` | The test: the four row sequences (2 sessions times 2 CPUs) pass `order_varies`. So the rows are drawn again for each CPU and session. |
| 548 | `    cs = collections.defaultdict(list)` | `cs`: for each session, kernel, size and CPU of step `CS`, the sequence of its rows. It is empty at first. |
| 549 | `    for s in (1, 2):` | Starts a loop over the two sessions. |
| 550 | `        for p in tree["CS", s]:` | Starts the loop over the processes of `CS`. |
| 551 | `            cs[s, p["head"]["kernel"], p["head"]["size"], p["cpu"]].extend(` | Appends to the sequence of the session, the kernel, the size and the CPU of the process. The value follows in the next line. |
| 552 | `                tuple(t["count"] for t in p["trials"][i:i + 3]) for i in range(0, 12, 3))` | The value: the 4 rows of the process, each the counter modes of 3 trials that follow each other. |
| 553 | `    check("CS: the order of the 24 rows differs between kernels, sizes, CPUs and sessions and is not one fixed list",` | Starts a check: in `CS` the sequence of the 24 rows differs between the kernels, the sizes, the CPUs and the sessions and is not one fixed list. |
| 554 | `          len(cs) == 8 and order_varies(cs.values()))` | The test: there are 8 sequences (2 sessions, 2 pairs of `SELECT`, 2 CPUs), and they pass `order_varies`. |
| 555 | `    p3 = rows_of(tree["P3", 1], 3)` | `p3`: the rows of step `P3` in session 1, for each CPU. |
| 556 | `    plain = sorted(set(p3[2])) * 4` | `plain`: the six orders of CPU 2 as a sorted list, repeated four times. A generator without a shuffle of the rows would write such a list. |
| 557 | `    check("row-order rule rejects the six orders as a fixed list, four times (it still obeys the order count)",` | Starts a check: the row-order rule rejects the six orders as a fixed list, four times, although this list still obeys the count rule. |
| 558 | `          perms_four_times(plain) and not order_varies([plain, p3[41]])` | The test, first part: `plain` passes `perms_four_times`. And `order_varies` rejects `plain` beside the real rows of CPU 41, as `plain` repeats its first 6 rows. |
| 559 | `          and not order_varies([p3[2], p3[2]]))` | Second part: `order_varies` rejects two equal sequences, here the rows of CPU 2 twice. So both halves of the rule can fail. |
| 560 | `    bad_rows = rows_of(mutate_swap(tree["P3", 1]), 3)[tree["P3", 1][0]["cpu"]]` | `bad_rows`: the rows of the CPU of the first process of `P3` in session 1, after the first two trials of that process were exchanged. |
| 561 | `    check("order-count rule rejects a schedule with two trials exchanged", not perms_four_times(bad_rows))` | Check: `perms_four_times` rejects these rows. So the count rule sees an exchange of two trials. |
| 563 | `    # B6W: the unchanged sequence of run_bwx.sh.` | Comment: the check of step `B6W`: its sequence must be the sequence of `run_bwx.sh`, without a change. |
| 564 | `    seq = re.search(r"^B6SEQ=(\S+)$", open(OLD_RUN).read(), re.M).group(1)` | `seq`: the kernel sequence from the older run script. The pattern `^B6SEQ=(\S+)$` matches a line that starts with `B6SEQ=`. Its one group holds the rest of the line, which must have no blank. `re.M` lets `^` and `$` match at every line. |
| 565 | `    check("B6W: 2 processes per CPU, arguments with the B6 sequence of run_bwx.sh",` | Starts a check: `B6W` has 2 processes per CPU, and their options hold the sequence of `run_bwx.sh`. |
| 566 | `          all([p["args"] for p in tree["B6W", s]] ==` | The test, for both sessions: the list of the `args` of the 4 processes equals the expected list. |
| 567 | `              ["--threads 1 --cpus %d --seq %s --bytes 8M --rounds 4 --min-ms 300 --stop pass" % (c, seq)` | The expected options of a process: one thread on the CPU `c`, the sequence `seq`, a buffer of 8 MiB, 4 rounds, at least 300 ms per interval, and the whole-pass stop. |
| 568 | `               for c in ((2, 41) if s == 1 else (41, 2)) * 2] for s in (1, 2)))` | The expected CPUs: the CPU order of the session, two times. So the processes alternate between the two CPUs. The check ties step `B6W` to the sequence of the earlier test. By the design this step replays that sequence. |

### `schedule_checks`: seeds, `--select`, saved folder, `--report`, test divisor (lines 570 to 615)

| Line | Source | Explanation |
|---:|---|---|
| 570 | `    # Determinism.` | Comment: the next checks test that the output is fully fixed by the options. |
| 571 | `    gen(b, "--select", SELECT)` | Runs the generator a second time with the same options, into the folder `b`. |
| 572 | `    r3 = gen(c, "--select", SELECT, "--seed", "7")` | `r3`: a third run with the base seed 7, into the folder `c`. |
| 573 | `    ta, tb, tc = tree_bytes(a), tree_bytes(b), tree_bytes(c)` | `ta`, `tb`, `tc`: the files of the three folders, each as a dictionary from the path to the bytes. |
| 574 | `    check("two runs with one base seed give the same bytes", ta == tb and len(ta) == 671, len(ta))` | Check: the first two folders hold the same files with the same bytes, and the folder holds 671 files. That is 11 schedules and 324 plans per session, and the file `MANIFEST.txt`. So the options fix the output: a schedule can be made again and compared. |
| 575 | `    check("another base seed gives the same file names and other bytes",` | Starts a check: another base seed gives the same file names and other bytes. |
| 576 | `          r3.returncode == 0 and sorted(ta) == sorted(tc) and ta != tc` | The test, first half: the third run ended with status 0, the two folders have the same file names, and their contents differ. |
| 577 | `          and ta["s1/S2.tsv"] != tc["s1/S2.tsv"] and ta["s1/S3/0000.plan"] != tc["s1/S3/0000.plan"])` | Second half: the schedule of `S2` in session 1 differs, and the first plan of `S3` in session 1 differs. So the seed changes the order of the processes and the order of the trials. |
| 578 | `    check("the base seed is saved in MANIFEST.txt", b"base_seed=20261114\n" in ta["MANIFEST.txt"]` | Starts a check: the base seed is saved in `MANIFEST.txt`. First half of the test: the file of the first run holds the line `base_seed=20261114`. |
| 579 | `          and b"base_seed=7\n" in tc["MANIFEST.txt"])` | Second half: the file of the third run holds the line `base_seed=7`. So a saved folder says from which seed it was made. |
| 580 | `    tree7, errors7 = load(c)` | `tree7`, `errors7`: the folder of the third run, read and tested with `load`. |
| 581 | `    check("another base seed keeps the rules (grammar, S2 order, S3 balance)",` | Starts a check: with another base seed the rules still hold: the plan format, the order of `S2` and the balance of `S3`. |
| 582 | `          not errors7 and not s2_rules(tree7["S2", 2], (41, 2))` | The test, first part: `load` found no defect, and `s2_rules` finds none in `S2` of session 2 with the CPU order 41 then 2. |
| 583 | `          and all(williams(rows_of(tree7["S3", 2], 12)[cpu]) for cpu in (2, 41)))` | Second part: the rows of `S3` in session 2 pass `williams` on both CPUs. So the rules do not hold by chance of one seed. |
| 585 | `    # Without --select the optional steps are not written.` | Comment: without `--select` the generator does not write the two optional steps. |
| 586 | `    d = os.path.join(tmp, "d")` | `d`: one more output folder. |
| 587 | `    r4 = gen(d)` | `r4`: a run of the generator with no option but the folder. |
| 588 | `    td = tree_bytes(d)` | `td`: the files of that folder. |
| 589 | `    check("without --select: no BIN and no CS, the other steps unchanged",` | Starts a check: without `--select` there is no `BIN` and no `CS`, and the other steps are unchanged. |
| 590 | `          r4.returncode == 0 and not any("/BIN" in k or "/CS" in k for k in td)` | The test, first part: exit status 0, and no file path holds `/BIN` or `/CS`. |
| 591 | `          and all(td[k] == ta[k] for k in td if k != "MANIFEST.txt"))` | Second part: every file other than `MANIFEST.txt` has the same bytes as in the first run. So the selection does not change the schedules of the other steps. |
| 592 | `    check("a bad --select entry is refused", gen(d, "--select", "copy@8M").returncode != 0` | Starts a check: a bad entry of `--select` is refused. First half: the generator ends with a status other than 0 for the kernel `copy`, which is not one of the three kernels. |
| 593 | `          and gen(d, "--select", "read@1000").returncode != 0)` | Second half: it also ends with a status other than 0 for the size 1000, which is not a multiple of 256 bytes. |
| 594 | `    saved = os.path.join(X, "sched")` | `saved`: the folder `sched` beside this file. The run script takes its schedules from that folder. |
| 595 | `    check("the saved sched/ beside the scripts is the output of the default base seed",` | Starts a check: the saved folder `sched` is the output of the generator with the default base seed. |
| 596 | `          os.path.isdir(saved) and tree_bytes(saved) == td)` | The test: the folder exists, and its files equal the files of the run without options, byte for byte. So the schedules that the run script would use are the ones that this generator writes. The repo README lists the folders `sched*` among those that were left out of the repo. So in the repo folder this check fails. |
| 597 | `    e = os.path.join(tmp, "e")` | `e`: the path of a folder that does not exist yet. |
| 598 | `    r5 = subprocess.run([sys.executable, SCHED, "--out", e, "--report"], capture_output=True, text=True)` | `r5`: a run of the generator with `--out` and that path and with `--report`. |
| 599 | `    check("--report prints the counts and writes nothing",` | Starts a check: `--report` prints the counts and writes nothing. |
| 600 | `          r5.returncode == 0 and not os.path.exists(e) and "S2 total: 360 processes" in r5.stdout` | The test, first part: exit status 0, the folder still does not exist, and the output holds the total line of `S2` with 360 processes. |
| 601 | `          and "pair of distinct conditions" in r5.stdout and "each kernel order once" in r5.stdout)` | Second part: the output holds the words of the two kinds of balance lines: `pair of distinct conditions` and `each kernel order once`. |
| 603 | `    # --test-divisor.` | Comment: the checks of the option `--test-divisor` start here. |
| 604 | `    t = os.path.join(tmp, "t")` | `t`: one more output folder. |
| 605 | `    r6 = gen(t, "--select", SELECT, "--test-divisor", "100")` | `r6`: a run of the generator with the selection and with `--test-divisor 100`, into the folder `t`. |
| 606 | `    ttree, terr = load(t)` | `ttree`, `terr`: that folder, read and tested with `load`. |
| 607 | `    check("--test-divisor 100: valid plans, test=1, every duration divided by 100",` | Starts a check: with the test divisor 100 the plans are valid, they hold `test=1`, and every duration is divided by 100. |
| 608 | `          r6.returncode == 0 and not terr` | The test, first part: exit status 0, and `load` found no defect. |
| 609 | `          and all(p["head"]["test"] == "1" for (st, _), pp in ttree.items() if st != "B6W" for p in pp)` | Second part: every plan of every step other than `B6W` has the header pair `test=1`. So the analysis can tell test data from real data. |
| 610 | `          and all(sum(proc_ms(p) for p in ttree[k]) * 100 == sum(proc_ms(p) for p in tree[k]) for k in tree))` | Third part: for every step and session, the nominal work of this folder times 100 equals the nominal work of the first folder. |
| 611 | `    check("--test-divisor 7 is refused (it does not divide 300 ms)",` | Starts a check: the generator refuses the test divisor 7, which does not divide 300 ms. |
| 612 | `          gen(os.path.join(tmp, "u"), "--test-divisor", "7").returncode != 0)` | The test: the generator ends with an exit status other than 0. A window of 300 ms cannot be divided by 7 without a rest. |
| 613 | `    return t` | Returns the folder that was made with the test divisor 100. The checks of the run script use it as their schedule. |

### Texts of the dummy runner and of the stand-ins for `ps` and `ssh` (lines 616 to 645)

| Line | Source | Explanation |
|---:|---|---|
| 616 | `# ---------- run_bwx8.sh with a dummy bwx8 ----------` | Comment: the texts and the helpers that follow serve the checks of `run_bwx8.sh` with a dummy `bwx8`. |
| 617 | `DUMMY = """#!/usr/bin/env bash` | `DUMMY`: the text of a Bash script that stands in for a runner. This line is its first line, which tells Linux to run it with `bash`. |
| 618 | `# Stand-in for bwx8: records its process ids, checks the plan file, sleeps, ends with DUMMY_EXIT.` | Line of the dummy script: a comment. The script stands in for `bwx8`. It records its process ids, checks the plan file, sleeps, and ends with the exit status in `DUMMY_EXIT`. |
| 619 | `echo "$$ $*" >> "$DUMMY_LOG"` | Line of the dummy script: appends its process id (`$$`) and all its arguments (`$*`) to the file that `DUMMY_LOG` names. The test reads this file to see what was started, and with which options. |
| 620 | `grep Cpus_allowed_list /proc/$$/status >> "$DUMMY_LOG.cpus"` | Line of the dummy script: appends the line `Cpus_allowed_list` of its own status file under `/proc` to the file with the ending `.cpus`. That line is the CPU list of the process. |
| 621 | `while (( $# )); do if [[ $1 == --plan && ! -r $2 ]]; then echo "no plan $2" >&2; exit 7; fi; shift; done` | Line of the dummy script: a loop over its arguments. When the argument after `--plan` is not a readable file, it prints `no plan` with the path to the error output and ends with exit status 7. So a wrong plan path fails as it would in a real runner. |
| 622 | `echo "M,dummy,1"` | Line of the dummy script: prints the one output line `M,dummy,1`. The run script appends it to the output file of the step. The test counts these lines to see how many dummies came to this point. |
| 623 | `sleep "${DUMMY_SLEEP:-0}" & echo "$! sleep" >> "$DUMMY_LOG"` | Line of the dummy script: starts `sleep` in the background for the seconds in `DUMMY_SLEEP`, or for 0 s when that variable is not set or is empty. Then it appends the process id of the sleep and the word `sleep` to the log. |
| 624 | `wait $!` | Line of the dummy script: waits for the sleep. |
| 625 | `# DUMMY_TOUCH=1: the marker file appears when this process ends.` | Line of the dummy script: a comment. With `DUMMY_TOUCH=1` the marker file appears when this process ends. |
| 626 | `[[ -z ${DUMMY_TOUCH:-} ]] \|\| : > "$BWX8_MARKER"` | Line of the dummy script: when `DUMMY_TOUCH` is set and not empty, it creates the marker file at the path in `BWX8_MARKER`. The command `:` with `>` writes an empty file. |
| 627 | `exit "${DUMMY_EXIT:-0}"` | Line of the dummy script: ends with the exit status in `DUMMY_EXIT`, or with 0 when that variable is not set or is empty. |
| 628 | `"""` | Ends the text `DUMMY`. |
| 630 | `PS_STUB = """#!/usr/bin/env bash` | `PS_STUB`: the text of a Bash script that stands in for the tool `ps`. This line is its first line. |
| 631 | `# Stand-in for ps: its second call creates the file named by PS_TOUCH. Then it runs the real ps.` | Line of the stand-in: a comment. Its second call creates the file that `PS_TOUCH` names. Then it runs the real `ps`. |
| 632 | `# run_bwx8.sh calls ps once for env.txt and then once per launch, after the wait and before the last marker check.` | Line of the stand-in: a comment. The run script calls `ps` once for `env.txt` and then once per launch, after the wait and before the last test of the marker file. So the second call of `ps` belongs to the first launch. |
| 633 | `if [[ -n ${PS_TOUCH:-} ]]; then` | Line of the stand-in: only when `PS_TOUCH` is set and not empty. |
| 634 | `  echo call >> "$PS_TOUCH.calls"` | Line of the stand-in: appends one line to a file that counts the calls. |
| 635 | `  if (( $(wc -l < "$PS_TOUCH.calls") == 2 )); then : > "$PS_TOUCH"; fi` | Line of the stand-in: when that file has 2 lines, it creates the empty file that `PS_TOUCH` names. |
| 636 | `fi` | Line of the stand-in: ends the `if`. |
| 637 | `exec %s "$@"` | Line of the stand-in: replaces itself with the real `ps` and passes all arguments on. The `%s` is filled later with the path of the real `ps`. |
| 638 | `"""` | Ends the text `PS_STUB`. |
| 640 | `SSH_STUB = """#!/bin/bash` | `SSH_STUB`: the text of a Bash script that stands in for `ssh`. This line is its first line. |
| 641 | `# Stand-in for ssh: records the remote command (its last argument). It opens no connection.` | Line of the stand-in: a comment. It records the remote command, which is its last argument. It opens no connection. |
| 642 | `printf '%s\\n' "${@: -1}" >> "$SSH_LOG"` | Line of the stand-in: appends its last argument (`${@: -1}`) and a newline to the file that `SSH_LOG` names. |
| 643 | `"""` | Ends the text `SSH_STUB`. |

### Small helpers: `cpu_list`, `utc` (lines 646 to 658)

| Line | Source | Explanation |
|---:|---|---|
| 646 | `def cpu_list(text):` | Starts the function `cpu_list`. It converts a line `Cpus_allowed_list` to a set of CPU numbers. |
| 647 | `    """'Cpus_allowed_list: 0-3,8' as a set of CPU numbers."""` | Description text: an example. The line `Cpus_allowed_list: 0-3,8` gives the set of the CPUs 0, 1, 2, 3 and 8. |
| 648 | `    cpus = set()` | `cpus`: the result set, empty at first. |
| 649 | `    for part in text.split(":")[1].strip().split(","):` | Takes the text after the colon and starts a loop over its parts between commas. A part is one CPU or a range such as `0-5`. |
| 650 | `        a, _, b = part.partition("-")` | Splits a part at the hyphen into the first CPU `a` and the last CPU `b`. `b` is empty for a single CPU. |
| 651 | `        cpus.update(range(int(a), int(b or a) + 1))` | Adds every CPU from `a` to `b`, or `a` alone. |
| 652 | `    return cpus` | Returns the set. |
| 655 | `def utc(offset):` | Starts the function `utc`. |
| 656 | `    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))` | Returns the UTC time `offset` seconds from now, as a text of the form `2026-11-15T03:00:00Z`. |

### Class `Box`: a copy of the run script with dummies in a temporary folder (lines 659 to 732)

| Line | Source | Explanation |
|---:|---|---|
| 659 | `class Box:` | Starts the class `Box`. It is the test setup for the run script. |
| 660 | `    """A copy of run_bwx8.sh with a test schedule and the dummy binary in a temporary folder."""` | Description text of the class: a copy of `run_bwx8.sh` with a test schedule and the dummy binary in a temporary folder. |
| 662 | `    def __init__(self, tmp, sched):` | Starts the constructor. `sched` is the generated folder with the test divisor 100. |
| 663 | `        self.dir = os.path.join(tmp, "box")` | `dir`: the folder `box` in the temporary folder. |
| 664 | `        os.makedirs(self.dir)` | Creates it. |
| 665 | `        shutil.copy(RUN, self.dir)` | Copies the run script into the box. The test runs this copy, so the script finds its files beside itself. |
| 666 | `        shutil.copytree(sched, os.path.join(self.dir, "sched"))` | Copies the generated folder (the argument `sched`) into the box as the folder `sched`. That is the name that the run script expects beside itself. |
| 667 | `        self.bin = os.path.join(self.dir, "bwx8")` | `bin`: the path of the dummy binary in the box, with the file name `bwx8`. |
| 668 | `        with open(self.bin, "w") as f:` | Opens it for writing. |
| 669 | `            f.write(DUMMY)` | Writes the text `DUMMY`. |
| 670 | `        os.chmod(self.bin, 0o755)` | Makes the dummy executable. |
| 671 | `        with open(os.path.join(self.dir, "build.txt"), "w") as f:` | Opens the file `build.txt` in the box for writing. The run script asks for a build record beside the binary. |
| 672 | `            f.write("dummy build record\n")` | Writes one line of text as a dummy build record. |
| 673 | `        os.makedirs(os.path.join(self.dir, "bin"))` | Creates the folder `bin` in the box. |
| 674 | `        stub = os.path.join(self.dir, "bin", "ps")` | `stub`: the path of the stand-in for `ps` in that folder. |
| 675 | `        with open(stub, "w") as f:` | Opens it for writing. |
| 676 | `            f.write(PS_STUB % shutil.which("ps"))` | Writes the text `PS_STUB` with the path of the real `ps` put in. `shutil.which` finds that path. |
| 677 | `        os.chmod(stub, 0o755)` | Makes the stand-in executable. |
| 678 | `        self.n = 0` | `n`: the number of the last test case, 0 at first. |
| 680 | `    def start(self, args, pre=(), **env):` | Starts the method `start`. `args`: the arguments for the run script. `pre`: words to put before the script, for example a `taskset` command. `env`: settings for its environment. |
| 681 | `        """Starts the script in fresh result, marker and log paths. Returns the process."""` | Description text: the method starts the script with new paths for the results, the marker file and the log. It returns the process. |
| 682 | `        self.n += 1` | Counts the test case. |
| 683 | `        self.case = os.path.join(self.dir, "case%d" % self.n)` | `case`: a folder of its own for this case, `case` plus the number. |
| 684 | `        os.makedirs(self.case)` | Creates it. |
| 685 | `        self.results = os.path.join(self.case, "results")` | `results`: the place for the result folders of this case. |
| 686 | `        self.marker = os.path.join(self.case, "RUNNING")` | `marker`: the path that takes the place of the marker file in this case. |
| 687 | `        self.stopfile = os.path.join(self.case, "STOP")` | `stopfile`: the path that takes the place of the stop file. |
| 688 | `        self.log = os.path.join(self.case, "dummy.log")` | `log`: the log file of the dummies. |
| 689 | `        e = {k: v for k, v in os.environ.items()` | `e`: the environment for the script. It starts as a copy of the environment of the test without the settings that the script reads. |
| 690 | `             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED", "BWX8_SHA256",` | The names that are left out, first part: the stop time, the two session settings, `RESERVE`, the variable `_PINNED` of the CPU limit, and the digest setting. |
| 691 | `                          "BWX_PMU_TYPE", "BWX_EVENTS")}` | Continues the list of the names that are left out: the two counter settings `BWX_PMU_TYPE` and `BWX_EVENTS`. So a setting of the person who runs the test cannot change a case. |
| 692 | `        e.update(HOME=self.case, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_BIN=self.bin,` | Adds the settings of the case: the case folder as the home folder, and the test paths of the marker file, of the stop file and of the binary. |
| 693 | `                 BWX8_RESULTS=self.results, DUMMY_LOG=self.log)` | Continues the call: the test path for the results, and the log file of the dummies in `DUMMY_LOG`. |
| 694 | `        e.update(env)` | Adds the settings that the caller gave. They replace the defaults of the case. |
| 695 | `        e = {k: v for k, v in e.items() if v is not None}      # None: leave this setting out` | Removes every setting whose value is `None`. So a caller can take a default away. |
| 696 | `        return subprocess.Popen(list(pre) + [os.path.join(self.dir, "run_bwx8.sh")] + args, env=e, text=True,` | Starts the copy of the run script as a new process and returns it without waiting. The command line is the words of `pre`, the script in the box and the arguments. |
| 697 | `                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)` | Continues the call: the environment `e`, text mode, and pipes for the output and the error output. `start_new_session=True` gives the script a session of its own, so a signal of the test reaches only it. |
| 699 | `    def run(self, args, pre=(), **env):` | Starts the method `run`: start the script and wait for its end. |
| 700 | `        p = self.start(args, pre, **env)` | Starts the script. |
| 701 | `        out, err = p.communicate(timeout=400)` | Waits for the end of the script, for at most 400 s, and reads its output and its error output. |
| 702 | `        return p.returncode, out, err` | Returns the exit status, the output and the error output. |
| 704 | `    def folder(self):` | Starts the method `folder`. |
| 705 | `        d = os.listdir(self.results) if os.path.isdir(self.results) else []` | `d`: the names in the results place of the case, or an empty list when that folder does not exist. |
| 706 | `        return os.path.join(self.results, d[0]) if len(d) == 1 else None` | Returns the path of the result folder when exactly one exists, and `None` in every other case. |
| 708 | `    def csv(self, step):` | Starts the method `csv`. It returns the content of the output file of a step. |
| 709 | `        f = self.folder()` | `f`: the result folder, or `None`. |
| 710 | `        path = os.path.join(f, step + ".csv") if f else ""` | `path`: the file `<step>.csv` in the result folder, or an empty text when there is no result folder. |
| 711 | `        return open(path).read() if os.path.exists(path) else ""` | Returns the content of the file, or an empty text when the file does not exist. |
| 713 | `    def launched(self):` | Starts the method `launched`. |
| 714 | `        return [l for l in open(self.log).read().split("\n") if l] if os.path.exists(self.log) else []` | Returns the lines of the dummy log that are not empty. Each launch gives two lines: the line of the dummy with its process id and options, and the line of its sleep. |
| 716 | `    def wait_launch(self):` | Starts the method `wait_launch`. It waits until the first dummy runs. |
| 717 | `        end = time.time() + 90` | `end`: 90 s from now. |
| 718 | `        while time.time() < end and len(self.launched()) < 2:` | Loops while the 90 s are not over and the dummy log has fewer than 2 lines. |
| 719 | `            time.sleep(0.2)` | Waits 0.2 s per turn. |
| 720 | `        return len(self.launched()) >= 2` | Returns true when the log has at least 2 lines: the line of the first dummy and the line of its sleep. |
| 722 | `    def none_alive(self):` | Starts the method `none_alive`. It tests that the script left no process behind. |
| 723 | `        time.sleep(0.5)` | Waits 0.5 s first. |
| 724 | `        for l in self.launched():` | Starts a loop over the lines of the dummy log. Each starts with a process id, of a dummy or of its sleep. |
| 725 | `            try:` | Starts the block whose error is caught. |
| 726 | `                os.kill(int(l.split()[0]), 0)` | `os.kill` with the signal 0 sends nothing. It only tests whether the process exists. |
| 727 | `                return False` | The process exists: returns false. |
| 728 | `            except OSError:` | The process does not exist. |
| 729 | `                pass` | Does nothing and goes on with the next line of the log. |
| 730 | `        return True` | No process of the log exists any more: returns true. |

### `visit_checks`: the visit script with a stand-in for `ssh` (lines 733 to 772)

| Line | Source | Explanation |
|---:|---|---|
| 733 | `def visit_checks(tmp):` | Starts the function `visit_checks`: the checks of the visit script. |
| 734 | `    """visit8.sh with a stand-in ssh. PATH holds only the stand-in and date, so no real ssh can start."""` | Description text: the function tests `visit8.sh` with a stand-in for `ssh`. The search path holds only the stand-in and `date`. So no real `ssh` can start. |
| 735 | `    d = os.path.join(tmp, "visit")` | `d`: the folder `visit` in the temporary folder. |
| 736 | `    os.makedirs(os.path.join(d, "bin"))` | Creates it with a folder `bin` inside. |
| 737 | `    text, n = re.subn(r"(?m)^N=.*$", "N=" + d, open(VISIT).read())` | Reads the visit script and replaces its line that starts with `N=`, the log folder, with a line that names `d`. `(?m)` lets `^` and `$` match at the start and the end of every line. `n` is the number of lines replaced. |
| 738 | `    copy_path = os.path.join(d, "visit8.sh")` | `copy_path`: the path of the changed copy of the visit script in `d`. |
| 739 | `    with open(copy_path, "w") as f:` | Opens the copy for writing. |
| 740 | `        f.write(text)` | Writes the changed text. |
| 741 | `    with open(os.path.join(d, "bin", "ssh"), "w") as f:` | Opens the file `ssh` in the folder `bin` for writing. |
| 742 | `        f.write(SSH_STUB)` | Writes the stand-in text `SSH_STUB`. |
| 743 | `    os.chmod(os.path.join(d, "bin", "ssh"), 0o755)` | Makes the stand-in executable. |
| 744 | `    os.symlink(shutil.which("date"), os.path.join(d, "bin", "date"))` | Puts a link to the real tool `date` into the folder `bin`. The visit script needs `date` for its status line. |
| 745 | `    log = os.path.join(d, "ssh.log")` | `log`: the file in which the stand-in records each remote command. |
| 747 | `    def visit(name, **env):` | Starts the inner function `visit`. It runs the copy once, with a log name and with settings. |
| 748 | `        if os.path.exists(log):` | When a record of an earlier call exists. |
| 749 | `            os.remove(log)` | Removes it. |
| 750 | `        e = {"PATH": os.path.join(d, "bin"), "SSH_LOG": log, "HOME": d}` | `e`: the whole environment of the script: a search path with only the folder `bin`, the record file for the stand-in, and `d` as the home folder. |
| 751 | `        e.update(env)` | Adds the settings of the caller. |
| 752 | `        r = subprocess.run([shutil.which("bash"), copy_path, name, "S2"], env=e, capture_output=True, text=True)` | Runs the copy with `bash`, with the log name and the step `S2` as its arguments and with the environment `e`. `shutil.which` finds `bash` in the search path of the test, as the search path of the script holds no `bash`. |
| 753 | `        return r.returncode, open(log).read() if os.path.exists(log) else None, r.stderr` | Returns the exit status, the recorded remote command (`None` when the stand-in was never called), and the error output. |
| 755 | `    rc, cmd, err = visit("ok", STOP_AT="2026-11-15T15:00Z", SESSION="2", SESSION1_END="2026-11-15T03:00Z",` | Runs the copy with a full set of valid settings: a stop time, session 2, the end of session 1. |
| 756 | `                         BWX8_SHA256="0a1b")` | Continues the call: the digest setting `0a1b`. |
| 757 | `    check("visit8.sh: one login; the marker check is the first remote action, then run_bwx8.sh with the settings",` | Starts a check: the visit makes one login. The marker check is the first remote action, and then `run_bwx8.sh` starts with the settings. |
| 758 | `          n == 1 and rc == 0 and cmd is not None and cmd.count("\n") == 1` | The test, first conditions: exactly one `N=` line was replaced, the exit status is 0, the stand-in was called, and its record has exactly one line. One line means one login. |
| 759 | `          and cmd.startswith("if [ -e /tmp/positron-perf.RUNNING ]; then ")` | Continues: the remote command starts with the test for the marker file `/tmp/positron-perf.RUNNING`. So nothing can start on CRB before the marker file was tested. |
| 760 | `          and cmd.endswith("&& STOP_AT=2026-11-15T15:00Z SESSION=2 SESSION1_END=2026-11-15T03:00Z "` | Continues: the remote command ends with `&&`, the four settings with their values, and `./run_bwx8.sh S2`. |
| 761 | `                           "BWX8_SHA256=0a1b  ./run_bwx8.sh S2\n"), (rc, cmd, err))` | Ends the expected text. The two blanks before `./run_bwx8.sh` are the place of the empty `ENVV`. So the settings reach the run script unchanged, and the step name is passed on. The detail for a failure shows the status, the command and the error output. |
| 762 | `    # A value with a blank or a shell character would split or change the remote command line:` | Comment: a value with a blank or a shell character would split or change the remote command line. |
| 763 | `    # the login would do nothing, or run something else. Handoff rule: keep the number of logins small.` | Continues the comment: the login would then do nothing, or run another command. The comment names a rule of the handoff note: keep the number of logins small. |
| 764 | `    ok = {"STOP_AT": "2026-11-15T15:00Z", "SESSION": "2", "SESSION1_END": "2026-11-15T03:00Z", "BWX8_SHA256": "0a1b"}` | `ok`: a set of valid values for the four settings that the visit script checks. |
| 765 | `    for var, value in (("SESSION1_END", "2026-11-15 03:00"), ("STOP_AT", "2026-11-15 15:00"),` | Starts a loop over bad values, each for one setting. This line: two times that hold a blank. |
| 766 | `                       ("STOP_AT", "none;id"), ("SESSION", "1$(id)"), ("BWX8_SHA256", "0a1b\|x")):` | Continues the list with three values that hold a shell character: a semicolon with a second command, a command substitution, and a vertical bar. |
| 767 | `        rc, cmd, err = visit("bad", **dict(ok, **{var: value}))` | Runs the copy with the valid set in which this one setting has the bad value. |
| 768 | `        check("visit8.sh: %s='%s' is refused with status 2 before the login, no log file" % (var, value),` | Starts a check per bad value: the visit script refuses it with status 2 before the login, and it writes no log file. |
| 769 | `              rc == 2 and cmd is None and var in err and not os.path.exists(os.path.join(d, "bad.log")),` | The test: exit status 2, the stand-in was never called, the error output names the setting, and no file `bad.log` exists. So a bad value causes no login at all. |
| 770 | `              (rc, cmd, err))` | The detail for a failure: the status, the recorded command and the error output. |

### `run_checks`: syntax, a step named twice, test settings, schedule fields, the dry run (lines 773 to 814)

| Line | Source | Explanation |
|---:|---|---|
| 773 | `def run_checks(tmp, sched):` | Starts the function `run_checks`: the checks of the run script. `sched` is the generated folder with the test divisor 100. |
| 774 | `    for f in ("run_bwx8.sh", "visit8.sh"):` | Starts a loop over the two shell scripts under test, the originals in the folder of this file. |
| 775 | `        r = subprocess.run(["bash", "-n", os.path.join(X, f)], capture_output=True, text=True)` | Runs `bash -n` on the script. With `-n` the shell reads the whole script and reports syntax errors, but it runs none of its commands. |
| 776 | `        check("bash -n " + f, r.returncode == 0, r.stderr)` | Check, once per script: `bash -n` ends with status 0. So the script has no syntax error. |
| 777 | `    box = Box(tmp, sched)` | `box`: a new test setup with a copy of the run script, the dummies and the schedule with the test divisor 100. |
| 779 | `    rc, out, err = box.run(["--dry-run", "P3", "P3"], SESSION="1")` | A dry run with the step `P3` named twice, in session 1. |
| 780 | `    check("a step named twice: status 2, nothing is printed for it (the script never repeats a process)",` | Starts a check: a step named twice gives status 2, and nothing is printed for it. The run script never repeats a process. |
| 781 | `          rc == 2 and "twice" in err and "step P3" not in out, (rc, out[:200], err))` | The test: exit status 2, the word `twice` in the error output, and no summary line of `P3` in the output. |
| 782 | `    rc, out, err = box.run(["--dry-run", "P3"], SESSION="1")` | A dry run of `P3` in session 1 with the settings of the box. The box sets the four test variables. |
| 783 | `    rc2, out2, err2 = box.run(["--dry-run", "P3"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None,` | The same dry run with the four test variables taken away (`None`). |
| 784 | `                              BWX8_BIN=None, BWX8_RESULTS=None)` | Continues the call: the test variables of the binary and of the results. |
| 785 | `    check("a warning names each test setting that moves the marker, the stop file, the binary or the results",` | Starts a check: the run script prints a warning for each test variable that moves the marker file, the stop file, the binary or the results. |
| 786 | `          rc == 0 and all(("warning: %s is set" % v) in err for v in` | The test, first part: the first run ended with status 0, and its error output holds the warning for each of the four names. |
| 787 | `                          ("BWX8_MARKER", "BWX8_STOPFILE", "BWX8_BIN", "BWX8_RESULTS"))` | The four names of the test variables. |
| 788 | `          and rc2 == 0 and "warning" not in err2 and out2 == out, (rc, err, rc2, err2))` | Second part: the second run ended with status 0, printed no warning and printed the same output. So a run that uses a test path says so, and the test variables do not change what a dry run prints. |
| 790 | `    # Schedule fields that reach shell arithmetic must be plain numbers: arithmetic runs a command` | Comment: the fields of a schedule that reach shell arithmetic must be plain numbers. The reason follows in the next line. |
| 791 | `    # that is written inside an array subscript, in a dry run too.` | Continues the comment: shell arithmetic runs a command that is written inside an array subscript, in a dry run too. |
| 792 | `    tsv = os.path.join(box.dir, "sched", "s1", "B6W.tsv")` | `tsv`: the schedule of `B6W` in session 1 in the box. |
| 793 | `    saved_tsv = open(tsv).read()` | `saved_tsv`: its text, kept to restore the file later. |
| 794 | `    for what, old, new in (("idx", "\n0\t", "\na[$(touch${IFS}%s)]\t"), ("--rounds", "--rounds 4", "--rounds a[$(touch${IFS}%s)]"),` | Starts a loop over three damaged fields. Each replacement puts an array subscript with a command into a field: `a[$(touch${IFS}PATH)]`. The command would create the file `PATH`. `${IFS}` stands in for the blank, as a blank would split the field. This line: the `idx` of the first row, and the value of `--rounds`. |
| 795 | `                           ("--min-ms", "--min-ms 3", "--min-ms a[$(touch${IFS}%s)]3")):` | Continues the list: the value of `--min-ms`. With the test divisor 100 that value is 3. |
| 796 | `        made = os.path.join(box.dir, "made-by-schedule")` | `made`: the path of the file that the command would create. |
| 797 | `        with open(tsv, "w") as f:` | Opens the schedule in the box for writing. |
| 798 | `            f.write(saved_tsv.replace(old, new % made, 1))` | Writes the text with the first match replaced, and with `made` as the path in the command. |
| 799 | `        rc, out, err = box.run(["--dry-run", "B6W"], SESSION="1")` | A dry run of `B6W` in session 1 with the damaged schedule. |
| 800 | `        check("schedule with a command in %s: status 2, the command does not run" % what,` | Starts a check per field: a schedule with a command in this field gives status 2, and the command does not run. |
| 801 | `              rc == 2 and not os.path.exists(made) and open(tsv).read() != saved_tsv, (rc, err))` | The test: exit status 2, the file `made` does not exist, and the schedule on disk differs from the saved text. The last condition shows that the replacement took place. So a damaged schedule cannot make the run script run a command. |
| 802 | `        if os.path.exists(made):` | Tests whether the file exists, which it does only after a failed check. |
| 803 | `            os.remove(made)` | Removes it. The next case then starts without it. |
| 804 | `    with open(tsv, "w") as f:` | After the loop: opens the schedule in the box for writing again. |
| 805 | `        f.write(saved_tsv)` | Writes the saved text back. |
| 807 | `    rc, out, err = box.run(["--dry-run", "S2", "S3"], SESSION="1")` | A dry run of the steps `S2` and `S3` in session 1. |
| 808 | `    check("--dry-run: status 0, prints the counts of each step",` | Starts a check: the dry run ends with status 0 and prints the counts of each step. |
| 809 | `          rc == 0 and "step S2 session 1: 180 processes, nominal kernel work 17.280 s" in out` | The test, first part: exit status 0, and the summary of `S2`: 180 processes and 17.280 s of nominal kernel work. That is 1728 s divided by the test divisor 100. |
| 810 | `          and "step S3 session 1: 12 processes, nominal kernel work 15.552 s" in out` | Second part: the summary of `S3`: 12 processes and 15.552 s. |
| 811 | `          and "selected conditions (15):" in out and "selected conditions (12):" in out` | Third part: the two lines of the selected conditions with their counts: 15 for `S2` and 12 for `S3`. |
| 812 | `          and out.count("\nbwx8 --trial ") == 192, (rc, out[:300], err))` | Fourth part: 192 command lines that start with `bwx8 --trial`, one for each process of the two steps. So the run script prints the selected conditions, the process count and the nominal work before execution, as the design asks. The detail for a failure shows the status, the first 300 characters of the output and the error output. |
| 813 | `    check("--dry-run: starts nothing and makes no result folder", not box.launched() and not os.path.exists(box.results))` | Check: the dry run started no dummy and made no result folder. |

### `run_checks`: a normal run of step `B6W`, `--from` and the CPU limit (lines 815 to 862)

| Line | Source | Explanation |
|---:|---|---|
| 815 | `    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none")` | A run of step `B6W` without `--dry-run`, in session 1 and with `STOP_AT=none`. The script now starts the dummies. `DUMMY_SLEEP` is not set, so each dummy ends at once. |
| 816 | `    f = box.folder()` | `f`: the one result folder of the case. |
| 817 | `    csv = box.csv("B6W")` | `csv`: the content of the output file `B6W.csv`. |
| 818 | `    heads = re.findall(r"^-- step B6W session 1 idx (\d+) tag (\S+) waited_s \d+ loadavg .* logins \d+ utc \S+ args (.*)$", csv, re.M)` | `heads`: the header lines of the output file. The pattern matches a line that starts with `-- step B6W session 1 idx` and then holds the words `tag`, `waited_s`, `loadavg`, `logins`, `utc` and `args`, each with its value. Group 1 holds the `idx` (digits), group 2 the tag (no blank), and group 3 the options after `args`. |
| 819 | `    check("normal end: status 0", rc == 0, (rc, err))` | Check: the run ends with status 0. |
| 820 | `    check("normal end: the counts are printed before the result folder is made",` | Starts a check: the counts are printed before the result folder is made. |
| 821 | `          "step B6W session 1: 4 processes, nominal kernel work 0.624 s" in out` | The test, first part: the output holds the summary of `B6W`: 4 processes and 0.624 s of nominal kernel work. |
| 822 | `          and 0 <= out.find("step B6W session 1: 4 processes") < out.find("result folder: "), out)` | Second part: the summary stands before the line `result folder:` in the output. So a person sees the counts of a step before the first process of that step starts. |
| 823 | `    check("normal end: folder name and its six files",` | Starts a check: the name of the result folder and its six files. |
| 824 | `          f is not None and re.match(r"^bwx8-B6W-s1-\d{8}T\d{6}Z$", os.path.basename(f)) is not None` | The test, first part: one result folder exists, and its name matches `^bwx8-B6W-s1-\d{8}T\d{6}Z$`: the step, the session, and a UTC time of 8 digits, the letter `T`, 6 digits and the letter `Z`. |
| 825 | `          and sorted(os.listdir(f)) == ["B6W.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv", "stderr.txt"],` | Second part: the folder holds exactly the files `B6W.csv`, `build.txt`, `env.txt`, `launches.txt`, `schedule.tsv` and `stderr.txt`. |
| 826 | `          f and os.listdir(f))` | The detail for a failure: the folder and its files. |
| 827 | `    if f:` | The next checks run only when the result folder exists. |
| 828 | `        rows = open(os.path.join(box.dir, "sched", "s1", "B6W.tsv")).read()` | `rows`: the text of the schedule of `B6W` in the box. |
| 829 | `        check("normal end: schedule.tsv and build.txt are copies",` | Starts a check: `schedule.tsv` and `build.txt` in the result folder are copies. |
| 830 | `              open(os.path.join(f, "schedule.tsv")).read() == rows` | The test, first half: `schedule.tsv` equals the schedule in the box. |
| 831 | `              and open(os.path.join(f, "build.txt")).read() == "dummy build record\n")` | Second half: `build.txt` holds the one line of the dummy build record. So a result folder shows which schedule and which build ran. |
| 832 | `        want = [tuple(r.split("\t")[i] for i in (0, 1, 5)) for r in rows.split("\n")[1:-1]]` | `want`: for each row of the schedule, its `idx`, its tag and its options (the columns 0, 1 and 5). |
| 833 | `        check("normal end: one header line per process, in schedule order, each followed by its output",` | Starts a check: one header line per process, in schedule order, each followed by its output. |
| 834 | `              heads == want and csv.count("M,dummy,1\n") == 4 and "-- killed" not in csv and "-- failed" not in csv, heads)` | The test: the header lines equal `want`, the output file holds 4 output lines of the dummy, and it holds no line `-- killed` or `-- failed`. The test counts the output lines. It does not test that each one stands directly after its header line. |
| 835 | `        env = open(os.path.join(f, "env.txt")).read()` | `env`: the content of `env.txt`. |
| 836 | `        check("normal end: env.txt holds session, from, load, digests and the end line",` | Starts a check: `env.txt` holds the session, the `--from` value, the load, the digests and the end line. |
| 837 | `              "session=1 from=0 " in env and "loadavg=" in env and "## sha256:" in env and "## end utc=" in env` | The test, first part: the texts `session=1 from=0`, `loadavg=`, `## sha256:` and `## end utc=` are in the file. |
| 838 | `              and open(os.path.join(f, "launches.txt")).read().count("== B6W.csv idx ") == 4, env)` | Second part: `launches.txt` holds 4 load records, one per launch. So the load of the machine is recorded for every process. |
| 839 | `        check("normal end: env.txt records the marker, stop file, binary and result paths in use",` | Starts a check: `env.txt` records the paths of the marker file, the stop file, the binary and the results that the run used. |
| 840 | `              (" MARKER=%s STOPFILE=%s BIN=%s RESULTS=%s\n" % (box.marker, box.stopfile, box.bin, box.results)) in env, env)` | The test: `env.txt` holds a line that ends with the four paths of this case. So a run with test paths can be told from a real run. |
| 841 | `    check("normal end: each process ran once", len(box.launched()) == 8 and box.none_alive())` | Check: each process ran once. The dummy log has 8 lines, that is 2 for each of the 4 launches, and no process is left. |
| 843 | `    rc, out, err = box.run(["--from", "11", "P3"], SESSION="1", STOP_AT="none")` | A run of step `P3` with `--from 11`, again without `--dry-run`. |
| 844 | `    csv = box.csv("P3")` | `csv`: the content of `P3.csv`. |
| 845 | `    env = open(os.path.join(box.folder(), "env.txt")).read() if box.folder() else ""` | `env`: the content of `env.txt`, or an empty text when there is no result folder. |
| 846 | `    check("--from 11: only idx 11 runs, with its plan file, and env.txt records from=11",` | Starts a check: with `--from 11` only the process with the `idx` 11 runs, with its own plan file, and `env.txt` records the value. |
| 847 | `          rc == 0 and re.findall(r"^-- step P3 session 1 idx (\d+) ", csv, re.M) == ["11"]` | The test, first part: exit status 0, and the output file has one header line, with the `idx` 11. |
| 848 | `          and " from=11 " in env and "to run from idx 11: 1 processes" in out` | Second part: `env.txt` holds `from=11`, and the summary says that 1 process is to run from `idx` 11. |
| 849 | `          and len(box.launched()) == 2 and "--plan sched/s1/P3/0011.plan" in box.launched()[0], (rc, err, csv))` | Third part: one launch, and its options name the plan `sched/s1/P3/0011.plan`. So a stopped step can be continued at a chosen process, and no other process is repeated. |
| 850 | `    # Design line 364, "use only the permitted CPUs": the script moves itself to CPUs 0-119, whatever` | Comment: the design asks to use only the permitted CPUs (`Design line 364`). The script moves itself to the CPUs 0 to 119, whatever CPU it was started on. |
| 851 | `    # it was started on. Started on one CPU, the benchmark must see every CPU of this machine below 120.` | Continues the comment: when the script is started on one CPU, the benchmark must see every CPU of this machine below 120. |
| 852 | `    allowed = sorted(os.sched_getaffinity(0))` | `allowed`: the CPUs on which Linux may run this test, in sorted order. |
| 853 | `    rc, out, err = box.run(["--from", "3", "B6W"], pre=["taskset", "-c", str(allowed[0])], SESSION="1", STOP_AT="none")` | Runs the last process of `B6W` with the script started under `taskset -c` on the first allowed CPU alone. |
| 854 | `    seen = open(box.log + ".cpus").read() if os.path.exists(box.log + ".cpus") else ""` | `seen`: the CPU list that the dummy recorded, or an empty text. |
| 855 | `    check("the benchmark is confined to CPUs 0-119 (needs a machine with 2 or more CPUs to tell)",` | Starts a check: the benchmark is limited to the CPUs 0 to 119. By its name the check needs a machine with 2 or more CPUs. |
| 856 | `          rc == 0 and len(allowed) > 1 and seen.count("\n") == 1` | The test, first part: exit status 0, the test may use more than one CPU, and the dummy recorded one line. |
| 857 | `          and cpu_list(seen) == {c for c in allowed if c < 120}, (rc, err, seen, allowed))` | Second part: the CPU list of the dummy equals the allowed CPUs of the test that are below 120. So the script does not stay on the one CPU of its caller: it sets its own CPU list. A machine that has no CPU with the number 120 or higher cannot show that such CPUs are left out. |
| 858 | `    rc, out, err = box.run(["--from", "12", "P3"], SESSION="1", STOP_AT="none")` | A run of `P3` with `--from 12`. The step has the `idx` values 0 to 11. |
| 859 | `    check("--from past the last idx: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2, and nothing starts. |
| 860 | `    rc, out, err = box.run(["--from", "1", "P3", "S3"], SESSION="1", STOP_AT="none")` | A run with `--from 1` and two steps. |
| 861 | `    check("--from with two steps: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2, and nothing starts. The option is allowed with one step only. |

### `run_checks`: the stop controls and `MARGIN` (lines 863 to 929)

| Line | Source | Explanation |
|---:|---|---|
| 863 | `    p = box.start(["B6W"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts `B6W` with dummies that sleep 300 s, and does not wait for its end. |
| 864 | `    up = box.wait_launch()` | `up`: true when the first dummy and its sleep run. |
| 865 | `    open(box.marker, "w").close()` | Creates the marker file of the case. |
| 866 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script, for at most 60 s. |
| 867 | `    csv = box.csv("B6W")` | `csv`: the content of `B6W.csv`. |
| 868 | `    check("marker file appears during a process: status 3, '-- killed', no process left",` | Starts a check: the marker file appears during a process. Expected: status 3, a line `-- killed`, and no process left. |
| 869 | `          up and p.returncode == 3 and "-- killed tag cpu2-p1 status 3" in csv` | The test, first part: the first dummy ran, the exit status is 3, and the output file holds the line `-- killed tag cpu2-p1 status 3`. |
| 870 | `          and csv.count("-- step ") == 1 and box.none_alive(), (up, p.returncode, err, csv))` | Second part: exactly one header line, so no second process started, and no dummy and no sleep is left. This proves the rule of the shared machine: when the marker file appears, the script ends its process and starts no other. |
| 871 | `    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", BWX8_MARKER=box.marker)` | A new run with the marker path of the case before, where the marker file still exists. Python reads `box.marker` before the new case sets a path of its own. |
| 872 | `    check("marker file present at the start: status 3, nothing starts, no result folder",` | Starts a check: the marker file exists at the start. Expected: status 3, nothing starts, and no result folder. |
| 873 | `          rc == 3 and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 3, no launch, and no results place. So with the marker file present the script writes nothing and starts nothing. |
| 875 | `    # Design line 364: check the marker file "before each process".` | Comment: the design asks to check the marker file before each process (`Design line 364`). |
| 876 | `    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="0.3", DUMMY_TOUCH="1")` | A run with dummies that sleep 0.3 s and create the marker file when they end (`DUMMY_TOUCH=1`). So the marker file appears between the first and the second process. |
| 877 | `    csv = box.csv("B6W")` | `csv`: the content of `B6W.csv`. |
| 878 | `    check("marker file appears between two processes: status 3, the first process ended, the second does not start",` | Starts a check: the marker file appears between two processes. Expected: status 3, the first process ended, and the second does not start. |
| 879 | `          rc == 3 and csv.count("-- step ") == 1 and csv.count("M,dummy,1\n") == 1 and "-- killed" not in csv` | The test, first part: exit status 3, one header line, one output line of the dummy, and no line `-- killed`. So the first process was not cut. |
| 880 | `          and len(box.launched()) == 2, (rc, err, csv))` | Ends the test: the dummy log has two lines, which is one launch. This proves the check before a launch: a process that has ended is kept as complete, and no new process starts while the marker file exists. |
| 881 | `    late = os.path.join(box.dir, "case%d" % (box.n + 1), "RUNNING")       # the marker path of the next case` | `late`: the marker path that the next case will have. The case number is known before the case starts. |
| 882 | `    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", PS_TOUCH=late,` | A run with `PS_TOUCH` set to that path. |
| 883 | `                           PATH=os.path.join(box.dir, "bin") + os.pathsep + os.environ["PATH"])` | Continues the call: the folder `bin` of the box stands first in the search path. So the script calls the stand-in for `ps`, and the second call of it creates the marker file. |
| 884 | `    launches = os.path.join(box.folder() or "", "launches.txt")` | `launches`: the path of `launches.txt` in the result folder. |
| 885 | `    check("marker file appears after the wait, directly before the launch: status 3, nothing starts",` | Starts a check: the marker file appears after the wait, directly before the launch. Expected: status 3, and nothing starts. |
| 886 | `          late == box.marker and os.path.exists(late) and rc == 3 and not box.launched() and "-- step" not in box.csv("B6W")` | The test, first part: the marker path of the case is the one that was computed, the marker file exists, the exit status is 3, no dummy started, and the output file has no header line. |
| 887 | `          and os.path.exists(launches) and open(launches).read().count("== B6W.csv idx ") == 1, (rc, err))` | Second part: `launches.txt` holds exactly one load record. So the script came to the load record of the first launch, and the second test of the stop reasons, directly before the launch, ended it. |
| 889 | `    p = box.start(["B6W"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts `B6W` with dummies that sleep 300 s. |
| 890 | `    up = box.wait_launch()` | Waits until the first dummy and its sleep run. |
| 891 | `    open(box.stopfile, "w").close()` | Creates the stop file of the case. |
| 892 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script, for at most 60 s. |
| 893 | `    check("stop file appears during a process: status 5, '-- killed', no process left",` | Starts a check: the stop file appears during a process. Expected: status 5, a line `-- killed`, and no process left. |
| 894 | `          up and p.returncode == 5 and "-- killed tag cpu2-p1 status 5" in box.csv("B6W") and box.none_alive(),` | The test: the first dummy ran, the exit status is 5, the output file holds `-- killed tag cpu2-p1 status 5`, and no process is left. So our own stop file ends a running benchmark. |
| 895 | `          (up, p.returncode, err))` | The detail for a failure: the launch flag, the exit status and the error output. |
| 897 | `    p = box.start(["B6W"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")` | Starts `B6W` with dummies that sleep 300 s. |
| 898 | `    up = box.wait_launch()` | Waits until the first dummy and its sleep run. |
| 899 | `    os.kill(p.pid, signal.SIGTERM)` | Sends the signal SIGTERM to the run script. |
| 900 | `    out, err = p.communicate(timeout=60)` | Waits for the end of the script, for at most 60 s. |
| 901 | `    csv = box.csv("B6W")` | `csv`: the content of `B6W.csv`. |
| 902 | `    check("interrupted during a process: status 130, '-- killed' marks the cut process, no process left",` | Starts a check: a signal interrupts the script during a process. Expected: status 130, a line `-- killed` that marks the cut process, and no process left. |
| 903 | `          up and p.returncode == 130 and box.none_alive()` | The test, first part: the process ran, the exit status is 130, and no process is left. |
| 904 | `          and re.search(r"^-- killed tag cpu2-p1 status 130 utc \S+$", csv, re.M) is not None` | Second part: the output file holds a line that matches `^-- killed tag cpu2-p1 status 130 utc \S+$`: the tag of the cut process, the status 130 and a time without a blank. |
| 905 | `          and csv.count("-- step ") == 1, (up, p.returncode, err, csv))` | Third part: exactly one header line. So an interrupted run leaves no benchmark behind, and its output file marks the process that was cut. |
| 907 | `    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT=utc(30))` | A run of `B6W` with a stop time 30 s from now. |
| 908 | `    check("STOP_AT nearer than MARGIN: status 4, nothing starts",` | Starts a check: a stop time that is nearer than `MARGIN` gives status 4, and nothing starts. |
| 909 | `          rc == 4 and not box.launched() and "less than 91 s away" in err, (rc, err))` | The test: exit status 4, no launch, and the message `less than 91 s away`. 91 s is the `MARGIN` of the step: 1 s for its longest process, rounded up, plus the 90 s of `RESERVE`. So no process starts that could still run at the stop time. |
| 910 | `    # MARGIN is the longest process of the step, rounded up to whole seconds, plus RESERVE. With the` | Comment: `MARGIN` is the longest process of the step, rounded up to whole seconds, plus `RESERVE`. The sentence about the test divisor ends in the next line. |
| 911 | `    # test divisor 100 the longest B6W process is 0.156 s (1 s) and the longest P3G process 1.728 s (2 s).` | Continues the comment: with the test divisor 100 the longest process of `B6W` has 0.156 s, which rounds up to 1 s. The longest process of `P3G` has 1.728 s, which rounds up to 2 s. |
| 912 | `    rc, out, err = box.run(["P3G"], SESSION="1", STOP_AT=utc(30))` | A run of `P3G` with a stop time 30 s from now. |
| 913 | `    check("MARGIN follows the longest process of the step: P3G refuses at 92 s, not at 91 s",` | Starts a check: `MARGIN` follows the longest process of the step. `P3G` refuses at 92 s, not at 91 s. |
| 914 | `          rc == 4 and not box.launched() and "less than 92 s away" in err and "longest process 2 s, MARGIN 92 s" in out,` | The test: exit status 4, no launch, the message `less than 92 s away`, and the summary text `longest process 2 s, MARGIN 92 s`. So the margin is computed for each step from its own schedule. |
| 915 | `          (rc, err, out))` | The detail for a failure: the exit status, the error output and the output. |
| 916 | `    p = box.start(["B6W"], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")` | Starts `B6W` with a stop time 45 s from now, `RESERVE=0` and dummies that sleep 300 s. `MARGIN` is then 1 s, so the first process may start. |
| 917 | `    up = box.wait_launch()` | Waits until the first dummy and its sleep run. |
| 918 | `    out, err = p.communicate(timeout=120)` | Waits for the end of the script, for at most 120 s. |
| 919 | `    check("STOP_AT reached during a process: status 4, '-- killed', no process left",` | Starts a check: the time `STOP_AT` is reached during a process. Expected: status 4, a line `-- killed`, and no process left. |
| 920 | `          up and p.returncode == 4 and "-- killed tag cpu2-p1 status 4" in box.csv("B6W") and box.none_alive(),` | The test: the first dummy ran, the exit status is 4, the output file holds `-- killed tag cpu2-p1 status 4`, and no process is left. So the stop time also ends a process that is running. |
| 921 | `          (up, p.returncode, err))` | The detail for a failure: the launch flag, the exit status and the error output. |
| 922 | `    rc, out, err = box.run(["B6W"], SESSION="1")` | A run of `B6W` without `STOP_AT`. |
| 923 | `    check("STOP_AT not set: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. A real run needs a decision about the stop time. |
| 925 | `    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", DUMMY_EXIT="3")` | A run of `B6W` with dummies that end with exit status 3 (`DUMMY_EXIT=3`). |
| 926 | `    csv = box.csv("B6W")` | `csv`: the content of `B6W.csv`. |
| 927 | `    check("failing binary: status 1, '-- failed', the next process does not start",` | Starts a check: a failing binary gives status 1 and a line `-- failed`, and the next process does not start. |
| 928 | `          rc == 1 and "-- failed tag cpu2-p1 exit 3" in csv and csv.count("-- step ") == 1, (rc, err, csv))` | The test: exit status 1, the line `-- failed tag cpu2-p1 exit 3` in the output file, and one header line. So a failed process is marked, and the rest of the step does not run. |

### `run_checks`: session 2 and other refusals (lines 930 to 976)

| Line | Source | Explanation |
|---:|---|---|
| 930 | `    rc, out, err = box.run(["B6W"], SESSION="2", STOP_AT="none")` | A run of `B6W` in session 2 without `SESSION1_END`. |
| 931 | `    check("session 2 without SESSION1_END: status 2, nothing starts",` | Starts a check: session 2 without `SESSION1_END` ends with status 2, and nothing starts. |
| 932 | `          rc == 2 and "SESSION1_END" in err and not box.launched(), (rc, err))` | The test: exit status 2, the error output names `SESSION1_END`, and no launch. |
| 933 | `    rc, out, err = box.run(["B6W"], SESSION="2", STOP_AT="none", SESSION1_END=utc(-3 * 3600 + 120))` | A run in session 2 with a `SESSION1_END` that lies 2 hours and 58 minutes in the past. |
| 934 | `    check("session 2 earlier than 3 h after SESSION1_END: refused with status 2, nothing starts",` | Starts a check: a session 2 that would start earlier than 3 hours after `SESSION1_END` is refused with status 2, and nothing starts. |
| 935 | `          rc == 2 and "3 hours" in err and not box.launched() and not os.path.exists(box.results), (rc, err))` | The test: exit status 2, the words `3 hours` in the error output, no launch and no results place. So the script itself enforces the gap of 3 hours between the two sessions. |
| 936 | `    # SESSION1_END must be a full UTC time. "date -d" alone reads a bare date as 00:00 and accepts` | Comment: `SESSION1_END` must be a full UTC time. The reason starts here: `date -d` alone reads a date without a time as 00:00. |
| 937 | `    # relative words, and each of these values would let session 2 start now.` | Continues the comment: and it accepts relative words. Each of the values of the next lines would let session 2 start now. |
| 938 | `    for value in ("garbage", time.strftime("%Y-%m-%d", time.gmtime()), "yesterday", "1", "@0", "-4 hours",` | Starts a loop over 9 bad values. This line: the word `garbage`, the date of today without a time, the word `yesterday`, the text `1`, the text `@0` and the text `-4 hours`. |
| 939 | `                  time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - 4 * 3600)),` | Continues the list: a date and a time of 4 hours ago with a blank between them. |
| 940 | `                  "2026-13-45T25:00Z", "2026-02-30T00:00Z"):` | Ends the list: a text with the month 13, the day 45 and the hour 25, and the 30th of February. Both have the right form, and neither is a real time. |
| 941 | `        rc, out, err = box.run(["--from", "3", "B6W"], SESSION="2", STOP_AT="none", SESSION1_END=value)` | A run of the last process of `B6W` in session 2 with this value. |
| 942 | `        check("session 2 with SESSION1_END='%s': status 2, nothing starts" % value,` | Starts a check per value: status 2, and nothing starts. |
| 943 | `              rc == 2 and "bad SESSION1_END" in err and not box.launched() and not os.path.exists(box.results),` | The test: exit status 2, the words `bad SESSION1_END` in the error output, no launch and no results place. So no loose form of the time can shorten the gap of 3 hours. |
| 944 | `              (rc, err))` | The detail for a failure: the exit status and the error output. |
| 945 | `    rc, out, err = box.run(["--from", "3", "B6W"], SESSION="2", STOP_AT="none",` | A run in session 2 with a `SESSION1_END` in the form with hours and minutes and without seconds. |
| 946 | `                           SESSION1_END=time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(time.time() - 3 * 3600 - 120)))` | Continues the call: the time lies 3 hours and 2 minutes in the past and is written in the form `2026-11-15T03:00Z`. |
| 947 | `    check("session 2 with SESSION1_END as hours and minutes, more than 3 h ago: runs",` | Starts a check: session 2 runs with a `SESSION1_END` in hours and minutes that lies more than 3 hours in the past. |
| 948 | `          rc == 0 and len(box.launched()) == 2, (rc, err))` | The test: exit status 0 and one launch. So the shorter of the two allowed forms is accepted. |
| 949 | `    s1end = utc(-3 * 3600 - 60)` | `s1end`: a valid end of session 1 that lies 3 hours and 1 minute in the past. |
| 950 | `    rc, out, err = box.run(["--from", "3", "B6W"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)` | A run of the last process of `B6W` in session 2 with that time. |
| 951 | `    env = open(os.path.join(box.folder(), "env.txt")).read() if box.folder() else ""` | `env`: the content of `env.txt`, or an empty text when there is no result folder. |
| 952 | `    check("session 2 later than 3 h after SESSION1_END: runs, folder -s2-, SESSION1_END in env.txt",` | Starts a check: session 2 runs later than 3 hours after `SESSION1_END`. The folder name holds `-s2-`, and `env.txt` records `SESSION1_END`. |
| 953 | `          rc == 0 and "bwx8-B6W-s2-" in (box.folder() or "") and ("SESSION1_END=" + s1end) in env` | The test, first part: exit status 0, the name of the result folder holds `bwx8-B6W-s2-`, and `env.txt` holds `SESSION1_END=` with the given time. |
| 954 | `          and "-- step B6W session 2 idx 3 tag cpu2-p2 " in box.csv("B6W"), (rc, err))` | Second part: the output file holds the header line of session 2 for the `idx` 3 with the tag `cpu2-p2`. In session 2 the CPU order is 41 then 2, so the fourth process runs on CPU 2. |
| 956 | `    rc, out, err = box.run(["B6W"], STOP_AT="none")` | A run of `B6W` without `SESSION`. |
| 957 | `    check("SESSION not set: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. The script does not guess the session. |
| 958 | `    rc, out, err = box.run(["B6"], SESSION="1", STOP_AT="none")` | A run with the step name `B6`, which the run script does not accept. |
| 959 | `    check("unknown step: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. |
| 960 | `    rc, out, err = box.run(["CM"], SESSION="1", STOP_AT="none")` | A run of the counter step `CM` without the two counter settings. |
| 961 | `    check("counter step without BWX_PMU_TYPE and BWX_EVENTS: status 2, nothing starts",` | Starts a check: a counter step without `BWX_PMU_TYPE` and `BWX_EVENTS` gives status 2, and nothing starts. |
| 962 | `          rc == 2 and "BWX_PMU_TYPE" in err and not box.launched(), (rc, err))` | The test: exit status 2, the error output names `BWX_PMU_TYPE`, and no launch. So the missing settings are found before the first process, not by a runner that fails. |
| 963 | `    rc, out, err = box.run(["--from", "11", "CM"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="10", BWX_EVENTS="a=0x11")` | A run of the last process of `CM` with both settings: the type number 10 and one event. |
| 964 | `    check("counter step with both settings: runs", rc == 0 and len(box.launched()) == 2, (rc, err))` | Check: exit status 0 and one launch. So the refusal of lines 961 to 962 came from the missing settings. |
| 965 | `    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", BWX8_SHA256="0" * 64)` | A run with a `BWX8_SHA256` of 64 zeros, which is not the digest of the dummy. |
| 966 | `    check("bwx8 differs from BWX8_SHA256: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. So a binary that is not the expected one cannot run when the digest is given. |
| 967 | `    digest = subprocess.run(["sha256sum", box.bin], capture_output=True, text=True).stdout.split()[0]` | `digest`: the sha256 of the dummy binary, computed with `sha256sum`. |
| 968 | `    rc, out, err = box.run(["--from", "3", "B6W"], SESSION="1", STOP_AT="none", BWX8_SHA256=digest)` | A run of the last process of `B6W` with the right digest. |
| 969 | `    check("bwx8 equals BWX8_SHA256: runs", rc == 0 and len(box.launched()) == 2, (rc, err))` | Check: exit status 0 and one launch. With the right digest the script runs. So the refusal of line 966 came from the digest and from nothing else. |
| 970 | `    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", BWX8_BIN=os.path.join(box.dir, "absent"))` | A run with `BWX8_BIN` set to a path that does not exist. |
| 971 | `    check("missing binary: status 2", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. So a missing binary is reported, and nothing starts. |
| 972 | `    os.rename(os.path.join(box.dir, "sched", "s1", "P3", "0004.plan"), os.path.join(box.dir, "moved.plan"))` | Moves the plan file `0004.plan` of `P3` in session 1 out of the schedule folder of the box. |
| 973 | `    rc, out, err = box.run(["P3"], SESSION="1", STOP_AT="none")` | A run of `P3`. |
| 974 | `    check("missing plan file: status 2 before the first launch", rc == 2 and not box.launched(), (rc, err))` | Check: exit status 2 and no launch. So the run script tests every plan file of a step before its first process. A missing plan is not found only after 4 processes have run. |

### `main`: the order of the groups of checks, and the summary (lines 977 to 993)

| Line | Source | Explanation |
|---:|---|---|
| 977 | `def main():` | Starts the function `main`. |
| 978 | `    tmp = tempfile.mkdtemp(prefix="test_schedule8.")` | `tmp`: a new temporary folder whose name starts with `test_schedule8.`. |
| 979 | `    try:` | Starts the block whose end is the cleanup of lines 986 to 987. |
| 980 | `        sched = schedule_checks(tmp)` | Runs the checks of the generator. `sched` gets the folder that was generated with the test divisor 100. |
| 981 | `        visit_checks(tmp)` | Runs the checks of the visit script. |
| 982 | `        if "--no-run" in sys.argv[1:]:` | When the option `--no-run` was given. |
| 983 | `            print("SKIP  the checks of run_bwx8.sh with a dummy bwx8 (--no-run)")` | Prints a line that starts with `SKIP` and says that the checks of `run_bwx8.sh` with a dummy `bwx8` were left out. |
| 984 | `        else:` | If not. |
| 985 | `            run_checks(tmp, sched)` | Runs the checks of the run script. |
| 986 | `    finally:` | The cleanup. It runs in every case, also after an error. |
| 987 | `        shutil.rmtree(tmp, ignore_errors=True)` | Removes the temporary folder with everything in it. |
| 988 | `    print("%d check(s) failed" % len(FAILS) if FAILS else "all checks passed")` | Prints the summary: the number of the failed checks, or `all checks passed`. |
| 989 | `    sys.exit(1 if FAILS else 0)` | Ends the program with exit status 1 when a check failed, and with 0 if not. A part that did not run does not change the status. |
| 992 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 993 | `    main()` | Runs `main`. |
