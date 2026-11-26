# `schedule10.py` explained, line by line

- Source file: `bwx10-2026-11-15/schedule10.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 316 lines, 15560 bytes).
- sha256 of the source when this page was built: `c454bd87bc980b56ef36b34fe903d54fa7afd76fcb246210ab5a20d2b53fdeff`.

## Short version: purpose

`schedule10.py` writes the input files of round 3 for the run script `run_bwx10.sh`: for each step and session one schedule file with one row per process, one plan file per process, and one file that names the runner binary. It fixes the order of the processes with a random number generator whose seed depends only on the base seed, the step and the session. It also checks that the orders are balanced, and it prints the counts and the nominal kernel work.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 3**: the third set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Y`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048`**: the four prefetch kernels of the runner `bwx10`. Each is the `asmread` loop with one software prefetch per 64 B line, 256, 512, 1024 or 2048 bytes ahead. A software prefetch is an instruction that asks for a line in the first-level data cache and reads no data.
- **`read_1pl`**: a kernel of the runner `bwx10` that makes one load of 16 bytes at the start of each 64 B line.
- **Process**: one start of a benchmark binary.
- **Run script**: the script `run_bwx10.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Step**: one batch of processes of a round, for example `YP`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Prefix**: a phase before the target that gives every trial the same preparation. In round 3 it runs the target kernel itself.
- **Target, window**: the target is the kernel that a trial measures. A window is one timed period of it.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Window plan**: one of the four ways in which step `YL` cuts 30 s of target time into windows: `L100`, `L300`, `L1000` and `L30000`.
- **Condition**: one setting that a step compares. In `YL` it is one kernel with one window plan. In `YP` it is one record pad or `hot`.
- **Cell**: one combination of the factors of a step, for example one kernel at one buffer size.
- **Replicate set, replicate**: one run of every kernel of step `YF` for one size and CPU, or one pass through all conditions on both CPUs (`YL`, `YP`).
- **Block**: the processes of one replicate on one CPU in `YL` and `YP`. Each block holds every condition once.
- **Williams square**: a set of n orders of n items in which every item stands once at every position, and every ordered pair of different items stands once as direct neighbours.
- **Base seed, seed**: the base seed is the one number that the caller can set with `--seed`. The seed of a step and session is derived from it.
- **Test divisor**: a number by which every duration is divided, for local tests only.
- **`--rec-pad P`**: an option of the runner `bwx10`. It puts P unused bytes before the records in which the runner stores the times of its windows.
- **`--hot-copy`**: an option of the runner `bwx10`. The window loop then works on a local copy of its window record.
- **`--trace`**: an option of the runner. The runner then prints a log of the events around its timed parts. The rates of such a run are not used.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters for each window.
- **`bins`**: a field of a trial, 0 or 1. With 1 the runner also stores the time and the byte count about every 10 ms inside a target window.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter device**: the hardware counters of the CPU cores, as Linux lists them. Linux gives the device a type number. The option `--pmu-type` carries that number.
- **Host sampler**: the program `hostwatch.py`. The run script starts it beside a process when the step has a `.watch` file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Read the options `--seed`, `--test-divisor` and `--out`. End with exit status 1 when the divisor does not divide 100 ms (lines 296 to 302).
2. Build the processes of every step and session with one `Gen` object each. Each object derives its own seed with `step_seed` and starts its own random number generator (line 303, lines 183 to 193, lines 91 to 96).
3. Each step method fills the list of processes of its step in run order. They are called in the order of `STEPS`: `YA` (lines 175 to 180), `YL` (lines 126 to 135), `YP` (lines 137 to 146), `YF` (lines 148 to 163) and `YC` (lines 165 to 173).
4. Build the report text: per step and session the number of processes and trials and the nominal kernel work, then the totals per session, then the result of each balance check (line 304, lines 263 to 292).
5. Build the text of `MANIFEST.txt`: the base seed, the test divisor, and the seed and the binary of every step and session (lines 305 to 308).
6. Remove the folders `s1` and `s2` of the output folder and write the plan files, the schedule files, the `.bin` files and `MANIFEST.txt` (line 309, lines 219 to 240).
7. Print the output folder and the report. End with exit status 0, or with 1 when a balance check failed (lines 310 to 312).

## Behavior a reader must know

- The seed of a step and session is the first 8 hexadecimal digits of the sha256 of the text `BASE/STEP/SESSION`, read as a whole number (lines 74 to 76). The base seed is 20261115 unless `--seed` gives another one (line 297).
- Each step and session has its own generator `random.Random(seed)` (line 94). All shuffles of a step use it, in a fixed sequence. So the same options always give the same files, and session 2 has random orders of its own.
- The steps and their sizes, from the constants and the loops of this file:
  - `YL`: 32 processes per session, each with 30 s of nominal kernel work. Binary `bwx8`.
  - `YP`: 28 processes per session, each with 30 s. Binary `bwx10`.
  - `YF`: 288 processes per session, each with 9.6 s. Binary `bwx10`.
  - `YC`: 42 processes per session, each with 6 s. Binary `bwx10`.
  - `YA`: 9 processes in session 1 only, each with 1.3 s. Binary `bwx10`.
- How the order of `YF` is made (lines 148 to 163):
  - First one Williams square of the 6 kernels is built for each size and CPU: 4 sizes in a fixed order, and inside a size the 2 CPUs in the order of the session. Each square takes two shuffles: the labels of the kernels and the order of its 6 rows (line 120, line 122).
  - Then, for each of the 6 replicate sets, the 4 sizes are shuffled once (line 155).
  - The run order is: replicate set, then size, then CPU, then the 6 kernels in the order of row `r` of the square of that size and CPU.
  - Balanced: per size and CPU each kernel stands once at each of the 6 positions, and each ordered pair of kernels runs once as direct neighbours.
- How the order of `YL` and `YP` is made (lines 126 to 135, lines 137 to 146): the run order is replicate 1 and then 2, inside a replicate the 2 CPUs in the order of the session, and inside a CPU all conditions in a newly shuffled order (8 in `YL`, 7 in `YP`). Balanced: each block holds every condition once. The positions inside a block are random and not balanced.
- How the order of `YC` is made (lines 165 to 173): all 21 cells run on the first CPU of the session, then all 21 cells on the second CPU. Each CPU has its own shuffled order. The step has no balance check.
- `YA` has a fixed order on CPU 2 and uses no random number (lines 175 to 180).
- Not random: the order of the two CPUs. Session 1 always runs CPU 2 before CPU 41, and session 2 runs CPU 41 before CPU 2 (line 44).
- The size order inside a replicate set of `YF` is shuffled but not balanced.
- The program checks the balance on the finished list of processes (lines 243 to 260). A failed check gives a line that ends with `NO` and exit status 1. The files are written before the exit status is set (lines 309 to 312).
- The folders `s1` and `s2` of the output folder are removed before the new files are written (line 222).
- The plan path in the `args` column always starts with `sched10/`, also when `--out` names another folder (line 232).
- Each process gets one worker CPU through `--cpus`, CPU 2 or CPU 41, and its buffer size through `--bytes` (line 232). The `args` hold no option for the controlling thread of the runner. By the note `DECISIONS-bwx8.md` that thread then uses CPU 0.
- The nominal kernel work counts planned durations only (line 216).
- With `--test-divisor N` every duration is divided by N and the plans get `test=1`. The numbers of windows and the order of the processes do not change.
- The program reads no input file and starts nothing on CRB.

## Source and explanation, line by line

- Text shown: the file `bwx10-2026-11-15/schedule10.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (316 lines, 15560 bytes, sha256 `c454bd87bc980b56ef36b34fe903d54fa7afd76fcb246210ab5a20d2b53fdeff`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text: files written, options, the five steps (lines 1 to 34)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""schedule10.py - schedules and plan files of round 3 (steps YA YL YP YF YC).` | Starts the description text of the file. First line: the name and the purpose. The program writes the schedules and the plan files of round 3, for the steps `YA`, `YL`, `YP`, `YF` and `YC`. `main` uses this line as the description in the help text. |
| 4 | `Usage: schedule10.py [--seed N] [--test-divisor N] [--out DIR]` | Text of the description: the usage. The three options are optional: the base seed, the test divisor and the output folder. |
| 6 | `It writes, for session 1 and 2 and for each step:` | Text of the description: the list of the files that the program writes for session 1, for session 2 and for each step. |
| 7 | `  DIR/s<session>/<STEP>.tsv        one row per process (idx, tag, cpu, bytes, plan, args)` | Text of the description: the schedule file of a step. It has one row per process, with the columns `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`. |
| 8 | `  DIR/s<session>/<STEP>/NNNN.plan  one plan file per process (plan format v1 of bwx8 and bwx10)` | Text of the description: one plan file per process, in a folder with the name of the step. The plan format is version 1, which the runners `bwx8` and `bwx10` read. |
| 9 | `  DIR/s<session>/<STEP>.bin        one word, bwx8 or bwx10: the binary that run_bwx10.sh starts for the step` | Text of the description: the `.bin` file of a step. It holds one word, `bwx8` or `bwx10`. The word names the binary that the run script `run_bwx10.sh` starts for the step. |
| 10 | `  DIR/MANIFEST.txt                 base seed, test divisor, the seed and the binary of each step and session` | Text of the description: the file `MANIFEST.txt`. It records the base seed, the test divisor, and the seed and the binary of each step and session. |
| 11 | `DIR is "sched10" beside this file by default. The folders DIR/s1 and DIR/s2 are replaced.` | Text of the description: the output folder is `sched10` in the folder of this file, unless `--out` names another one. The program removes the folders `s1` and `s2` in it and writes them new. |
| 12 | `No step of round 3 runs with the host sampler, so no .watch file is written.` | Text of the description: no step of round 3 runs with the host sampler. So the program writes no `.watch` file. Such a file tells the run script to start the program `hostwatch.py` beside each process of the step. |
| 13 | `The step YA exists in session 1 only.` | Text of the description: the step `YA` exists in session 1 only. |
| 14 | `--test-divisor N divides every duration by N and marks the plans test=1 (local chain tests only).` | Text of the description: `--test-divisor N` divides every duration by N and writes `test=1` into the plans. It is only for local tests of the whole chain of scripts. |
| 15 | `N must divide 100 ms, the shortest window of round 3.` | Text of the description: N must divide 100 ms without a rest. 100 ms is the shortest window of round 3. |
| 16 | `The same options give the same bytes. Exit status 1 if a balance check fails.` | Text of the description: two runs with the same options write the same bytes. The exit status is 1 when a balance check fails. |
| 17 | `This file needs no other file of round 1 or 2: the parts taken from schedule8.py and schedule9.py are copied here.` | Text of the description: the program needs no other file of round 1 or round 2. The parts that come from `schedule8.py` and `schedule9.py`, the generators of these two rounds, are copied into this file. |
| 19 | `Steps (CPUs 2 and 41; session 2 uses the reversed CPU order; one process at a time):` | Text of the description: the heading of the list of steps. The worker CPUs are 2 and 41. Session 2 uses the two CPUs in the reverse order. One process runs at a time. |
| 20 | `  YL   window length (bwx8): one trial of 30 s per process, count closed. Kernels asmread and read at 8M.` | Step `YL`, the test of the window length, with the binary `bwx8`: one trial of 30 s per process. The counter mode is `closed`, so the runner uses no counters. The kernels are `asmread` and the new read kernel `read`, both at a buffer size of 8 MiB. |
| 21 | `       Window plans: L100 = 300 windows of 100 ms, L300 = 100 of 300 ms, L1000 = 30 of 1000 ms (bins 0),` | Continues the text on `YL`: three of the four window plans. `L100` has 300 windows of 100 ms, `L300` has 100 windows of 300 ms, and `L1000` has 30 windows of 1000 ms. Each gives 30 s. `bins 0` means that the runner stores no 10 ms bins for these three. |
| 22 | `       L30000 = 1 window of 30000 ms with 10 ms bins (bins 1). 2 processes per kernel, plan and CPU.` | Continues the text on `YL`: the fourth window plan, `L30000`, is one window of 30000 ms with `bins` equal to 1. With that value the runner also stores the time and the byte count about every 10 ms inside the window. Each kernel runs 2 processes per window plan and CPU. |
| 23 | `       Order: replicate, then CPU, then the 8 conditions shuffled.` | Continues the text on `YL`: the order is the replicate, then the CPU, then the 8 conditions in a shuffled order. A condition is one kernel with one window plan. |
| 24 | `  YP   record pad (bwx10): asmread at 8M, one trial of 100 windows of 300 ms, count closed. Conditions:` | Step `YP`, the test of the record pad, with the binary `bwx10`: `asmread` at 8 MiB, one trial of 100 windows of 300 ms, without counters. The list of the conditions starts at the end of this line. |
| 25 | `       "--rec-pad P" with P = 0, 80, 400, 1040, 2080, 4000, and "--hot-copy" (label hot, pad left at 0).` | Continues the text on `YP`: six conditions have the option `--rec-pad P` with P = 0, 80, 400, 1040, 2080 or 4000 bytes. The option puts P unused bytes before the window records of the runner. The seventh condition has the option `--hot-copy` and the label `hot`. With that option the window loop of the runner works on a local copy of its window record. The pad of this condition stays 0. |
| 26 | `       2 processes per condition and CPU. Order: replicate, then CPU, then the 7 conditions shuffled.` | Continues the text on the step: each condition runs 2 processes per CPU. The order is the replicate, then the CPU, then the 7 conditions in a shuffled order. |
| 27 | `  YF   software prefetch family (bwx10): trials as step S2 of schedule8.py (4 trials per process:` | Step `YF`, the software prefetch family, with the binary `bwx10`. Its trials have the form of step `S2` of the older generator `schedule8.py`: 4 trials per process. |
| 28 | `       prefix K@S 1200 ms, target K@S 4 x 300 ms). 6 kernels, 4 sizes, 6 replicate sets per size and CPU.` | Continues the text on `YF`: each trial has a prefix of 1200 ms of the kernel K at the size S. The target of the trial is the same kernel at the same size, in 4 windows of 300 ms. The step has 6 kernels and 4 sizes, with 6 replicate sets per size and CPU. A replicate set is one run of every kernel. |
| 29 | `       Order: replicate set, then size (shuffled), then CPU, then the 6 kernels. Per size and CPU the` | Continues the text on `YF`: the order of the processes. The outer level is the replicate set, then the size in a shuffled order, then the CPU, then the 6 kernels. The sentence about the kernel orders starts at the end of this line. |
| 30 | `       kernel orders of the 6 sets form a Williams square (defined at williams_square below).` | Continues the text on `YF`: for each size and CPU, the kernel orders of the 6 sets form a Williams square. The method `williams_square` defines it (lines 109 to 123). |
| 31 | `  YC   prefetch family counters (bwx10): one trial, 20 windows of 300 ms, count read, the event set in the` | Step `YC`, the counters of the prefetch family, with the binary `bwx10`: one trial per process with 20 windows of 300 ms. The counter mode is `read`: the runner reads the counters for each window. The list of counter events stands in the `args` column. |
| 32 | `       args column. 7 kernels at 3 sizes, 1 process per cell and CPU. Order: CPU, then the 21 cells shuffled.` | Continues the text on `YC`: 7 kernels at 3 sizes give 21 cells. Each cell runs 1 process per CPU. The order is the CPU, then the 21 cells in a shuffled order. |
| 33 | `  YA   acceptance of bwx10: CPU 2 only, 9 short processes with --trace, in a fixed order.` | Step `YA`, the acceptance of the runner `bwx10`: 9 short processes on CPU 2 only, with the option `--trace`, in a fixed order. With `--trace` the runner prints a log of the events around its timed parts. The rates of such a run are not used. |
| 34 | `"""` | Ends the description text. |

### Imports and constants (lines 35 to 66)

| Line | Source | Explanation |
|---:|---|---|
| 35 | `import argparse` | Loads the Python module `argparse`, which reads the command line options. |
| 36 | `import hashlib` | Loads `hashlib`: the sha256 function, used to derive the seeds. |
| 37 | `import os` | Loads `os`: paths and folders. |
| 38 | `import random` | Loads `random`: the random number generator that shuffles the orders. |
| 39 | `import shutil` | Loads `shutil`: used to remove a folder tree. |
| 40 | `import sys` | Loads `sys`: the standard output and the exit status. |
| 42 | `STEPS = ["YA", "YL", "YP", "YF", "YC"]` | `STEPS`: the names of the 5 steps, in the order in which the program builds and reports them. |
| 43 | `BINARY = {"YA": "bwx10", "YL": "bwx8", "YP": "bwx10", "YF": "bwx10", "YC": "bwx10"}` | `BINARY`: the word of the binary of each step. It is `bwx8` for the step `YL` and `bwx10` for the other four steps. The word goes into the `.bin` file of the step. |
| 44 | `CPUS = {1: [2, 41], 2: [41, 2]}                    # session 2 uses the reversed order` | `CPUS`: the two worker CPUs in the order of each session. Session 1 uses CPU 2 first and then CPU 41. Session 2 uses CPU 41 first. |
| 45 | `PMU_TYPE = 11                                      # armv8_pmuv3_0 on CRB (DECISIONS-bwx8.md)` | `PMU_TYPE`: 11, the type number that Linux gives to the counter device `armv8_pmuv3_0` of the cores on CRB. By the comment the value comes from the notes file `DECISIONS-bwx8.md`. It goes into the option `--pmu-type` of the processes that use counters. |
| 46 | `YC_EVENTS = ("cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17,"` | `YC_EVENTS`: the counter events of step `YC`, each as a name and an event code. This line holds four: the cycles of the core (`cpu_cycles`), the completed instructions (`inst_retired`), the refills of the first-level data cache (`l1d_cache_refill`) and the refills of the L2 cache (`l2d_cache_refill`). |
| 47 | `             "l1d_cache_lmiss_rd=0x39,l2d_cache_lmiss_rd=0x4009")` | Continues the text of line 46 with two more events: `l1d_cache_lmiss_rd` and `l2d_cache_lmiss_rd`. The note `DECISIONS-bwx8.md` names them the L1 long miss and the L2 long miss. The 6 events go into the option `--events`. |
| 48 | `YL_KERNELS = ["asmread", "read"]` | `YL_KERNELS`: the two kernels of step `YL`: the hand-written load-only loop `asmread` and the new read kernel `read`. |
| 49 | `# name, windows, window length in ms, bins` | Comment: each entry of the list in line 50 holds a name, the number of windows, the window length in ms and the `bins` value. |
| 50 | `YL_PLANS = [("L100", 300, 100, 0), ("L300", 100, 300, 0), ("L1000", 30, 1000, 0), ("L30000", 1, 30000, 1)]` | `YL_PLANS`: the four window plans of step `YL`. `L100`: 300 windows of 100 ms. `L300`: 100 windows of 300 ms. `L1000`: 30 windows of 1000 ms. `L30000`: 1 window of 30000 ms, the only plan with `bins` equal to 1. Each plan gives 30000 ms of target time. |
| 51 | `# name, the options added to the command line` | Comment: each entry of the list in line 52 holds a name and the option text that is added to the command line. |
| 52 | `YP_CONDS = [("P%d" % p, " --rec-pad %d" % p) for p in (0, 80, 400, 1040, 2080, 4000)] + [("hot", " --hot-copy")]` | `YP_CONDS`: the seven conditions of step `YP`. The comprehension builds six pairs, one for each pad of 0, 80, 400, 1040, 2080 and 4000 bytes: the label `P` with the number, and the option `--rec-pad` with the number. So the pad 0 also gets the option. The last entry is the label `hot` with the option `--hot-copy`. |
| 53 | `YF_KERNELS = ["asmread", "read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"]` | `YF_KERNELS`: the six kernels of step `YF`: `asmread`, the four prefetch kernels `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048`, and `read_1pl`. In the source `bwx10.c` a prefetch kernel is the `asmread` loop with one software prefetch per 64 B line, 256, 512, 1024 or 2048 bytes ahead. `read_1pl` makes one load of 16 bytes per 64 B line. |
| 54 | `YF_SIZES = ["32K", "1M", "8M", "16M"]` | `YF_SIZES`: the four buffer sizes of step `YF`: 32 KiB, 1 MiB, 8 MiB and 16 MiB. |
| 55 | `YC_KERNELS = YF_KERNELS + ["oldread"]` | `YC_KERNELS`: the seven kernels of step `YC`: the six of `YF_KERNELS` and the old read kernel `oldread`. |
| 56 | `YC_SIZES = ["1M", "8M", "16M"]` | `YC_SIZES`: the three buffer sizes of step `YC`: 1, 8 and 16 MiB. |
| 57 | `# name, kernel, size, the options added after --trace` | Comment: each entry of `YA_PROCS` holds a name, a kernel, a buffer size, and the options that follow `--trace`. |
| 58 | `YA_PROCS = [("plain", "asmread", "8M", ""), ("pad80", "asmread", "8M", " --rec-pad 80"),` | `YA_PROCS`: the 9 processes of the acceptance step `YA`. This line holds two, both with `asmread` at 8 MiB: `plain` without an option and `pad80` with `--rec-pad 80`. |
| 59 | `            ("hot", "asmread", "8M", " --hot-copy"), ("pf256", "read_pf256", "8M", ""),` | Continues the list: `hot`, which is `asmread` at 8 MiB with `--hot-copy`, and `pf256`, the kernel `read_pf256` at 8 MiB. |
| 60 | `            ("pf512", "read_pf512", "8M", ""), ("pf1024", "read_pf1024", "8M", ""),` | Continues the list: `pf512` and `pf1024`, the kernels `read_pf512` and `read_pf1024` at 8 MiB. |
| 61 | `            ("pf2048", "read_pf2048", "8M", ""), ("1pl", "read_1pl", "8M", ""),` | Continues the list: `pf2048` and `1pl`, the kernels `read_pf2048` and `read_1pl` at 8 MiB. |
| 62 | `            ("pf1024s", "read_pf1024", "32K", "")]` | Ends the list with `pf1024s`: the kernel `read_pf1024` at the small size of 32 KiB. |
| 63 | `UNITS = 6                                          # replicate sets per size and CPU in YF` | `UNITS`: 6, the number of replicate sets per size and CPU in the step `YF`. |
| 64 | `MIN_WIN_MS = 100                                   # the shortest window of round 3` | `MIN_WIN_MS`: 100 ms, the shortest window of round 3. The test divisor must divide it (line 301). |

### Helper functions: `size_bytes`, `step_seed`, `williams_ok` (lines 67 to 87)

| Line | Source | Explanation |
|---:|---|---|
| 67 | `def size_bytes(tok):` | Starts the function `size_bytes`. It converts a size text such as `8M` to a number of bytes. |
| 68 | `    mult = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}` | `mult`: the factor of each unit letter: `K` is 1024, `M` is 1048576 (1 MiB) and `G` is 1073741824. |
| 69 | `    if tok and tok[-1] in mult:` | Tests whether the text is not empty and ends with one of the three letters. |
| 70 | `        return int(tok[:-1]) * mult[tok[-1]]` | If so: returns the number before the letter times the factor. `8M` gives 8388608. |
| 71 | `    return int(tok)` | If not: the text is a plain number of bytes. |
| 74 | `def step_seed(base, step, session):` | Starts the function `step_seed`. It derives the random seed of one step and session from the base seed. |
| 75 | `    h = hashlib.sha256(("%d/%s/%d" % (base, step, session)).encode()).hexdigest()` | `h`: the sha256 of a short text, written as 64 hexadecimal digits. The text is the base seed, the step name and the session number, with a slash between them. |
| 76 | `    return int(h[:8], 16)` | Returns the first 8 hexadecimal digits as a whole number, a value from 0 to 4294967295. So each step and session gets its own seed, and one base seed always gives the same seeds. |
| 79 | `def williams_ok(orders, n):` | Starts the function `williams_ok`. It tests whether a list of orders is a Williams square of `n` items. |
| 80 | `    """orders: n orders of the items 0..n-1. True if every item is once at every position and` | Description text: `orders` holds `n` orders of the items 0 to `n - 1`. The result is true when every item stands once at every position. |
| 81 | `    every ordered pair of different items is once a pair of neighbours."""` | Continues the text: and when every ordered pair of different items stands once as direct neighbours. In an ordered pair (a, b), b follows directly after a. |
| 82 | `    pos = {(o[i], i) for o in orders for i in range(n)}` | `pos`: the set of all pairs of an item and its position, over all orders. |
| 83 | `    pairs = [(o[i], o[i + 1]) for o in orders for i in range(n - 1)]` | `pairs`: the list of all pairs of direct neighbours, over all orders: an item and the item after it. |
| 84 | `    return (len(orders) == n and all(sorted(o) == list(range(n)) for o in orders)` | Starts the result. The first two conditions: there are exactly `n` orders, and each order holds every item from 0 to `n - 1` exactly once. |
| 85 | `            and len(pos) == n * n and len(set(pairs)) == len(pairs) == n * (n - 1))` | The last two conditions. The set `pos` has `n * n` members, so every item stands at every position. The list `pairs` has `n * (n - 1)` entries and no entry twice, so every ordered pair of different items is a pair of neighbours exactly once. |

### Class `Gen`: constructor, `ms`, `trial`, `add`, `williams_square` (lines 88 to 124)

| Line | Source | Explanation |
|---:|---|---|
| 88 | `class Gen:` | Starts the class `Gen`. One object builds the list of the processes of one step in one session. |
| 89 | `    """Builds the processes of one round 3 step and session."""` | Description text of the class: it builds the processes of one step of round 3 in one session. |
| 91 | `    def __init__(self, step, session, base, div):` | Starts the constructor. `base` is the base seed, and `div` is the test divisor. |
| 92 | `        self.step, self.session, self.div = step, session, div` | Stores the step, the session and the divisor. |
| 93 | `        self.seed = step_seed(base, step, session)` | `seed`: the seed of this step and session, derived from the base seed by `step_seed`. |
| 94 | `        self.rng = random.Random(self.seed)` | `rng`: a random number generator of its own for this step and session, started with that seed. Every shuffle of the step uses it. So the order of the processes depends only on the base seed, the step and the session. |
| 95 | `        self.cpus = CPUS[session]` | `cpus`: the two CPUs in the order of this session. |
| 96 | `        self.procs = []` | `procs`: the list of the processes of the step, in the order in which they will run. It is empty at first. |
| 98 | `    def ms(self, v):` | Starts the method `ms`. It scales a duration in ms by the test divisor. |
| 99 | `        return v // self.div` | Returns the duration divided by the divisor, as a whole number. With the divisor 1 the duration stays as it is. |
| 101 | `    def trial(self, cond, pfx, tgt, nwin, win_ms, count="closed", bins=0):` | Starts the method `trial`. It builds one trial of a plan. `cond`: the condition label. `pfx`: the duration of the prefix in ms, or `None`. `tgt`: the target in the form `KERNEL@SIZE`. `nwin` and `win_ms`: the number and the length of the target windows. `count`: the counter mode, `closed` unless given. `bins`: 0 unless given. |
| 102 | `        # (cond, prev, pfx, pred, tgt, nwin, win_ms, count, bins); pfx: None or the ms of a prefix of the target.` | Comment: the result is a tuple of 9 values in the order of the plan columns. `pfx` is `None`, or the ms of a prefix that runs the target kernel itself. |
| 103 | `        return (cond, "-", "%s:%d" % (tgt, self.ms(pfx)) if pfx else "-", "-", tgt, nwin, self.ms(win_ms), count, bins)` | Returns the tuple. The previous activity and the predecessor are always `-`, the mark for none. The prefix is `-`, or the target followed by a colon and its scaled duration. The window length is scaled too. The number of windows is not scaled. |
| 105 | `    def add(self, tag, cpu, size, keys, trials, extra=""):` | Starts the method `add`. It appends one process to the list. `keys`: more pairs for the header of the plan. `extra`: options that are added to the command line. |
| 106 | `        self.procs.append({"tag": tag, "cpu": cpu, "bytes": size_bytes(size), "keys": keys,` | Appends a dictionary with the tag, the CPU, the buffer size in bytes and the header pairs. |
| 107 | `                           "trials": trials, "extra": extra})` | Continues the dictionary: the list of trials and the extra options. |
| 109 | `    def williams_square(self, n):` | Starts the method `williams_square`. It returns `n` orders of `n` items that form a Williams square. The random choices come from `rng`. |
| 110 | `        # A Williams square for an even n: n orders of n items in which every item takes every position` | Comment: a Williams square for an even `n` holds `n` orders of `n` items. Every item takes every position once. |
| 111 | `        # once, and every ordered pair of different items is once a pair of neighbours. Built from the` | Continues the comment: and every ordered pair of different items is once a pair of direct neighbours. The square is built from one start order. |
| 112 | `        # start order 0, 1, n-1, 2, n-2, ... shifted by 0 to n-1, with random item labels and row order.` | Continues the comment: the start order is 0, 1, `n-1`, 2, `n-2` and so on. Each row shifts it by a value from 0 to `n-1`. Then the items get random labels, and the rows get a random order. |
| 113 | `        start, lo, hi = [0], 1, n - 1` | `start`: the start order, which begins with 0. `lo` and `hi`: the next low number and the next high number to add, 1 and `n - 1` at first. |
| 114 | `        while lo <= hi:` | Starts a loop that runs until the low number has passed the high number. |
| 115 | `            start.append(lo)` | Adds the low number. |
| 116 | `            if lo != hi:` | Unless both numbers are the same. |
| 117 | `                start.append(hi)` | Adds the high number. |
| 118 | `            lo, hi = lo + 1, hi - 1` | Moves the low number up and the high number down. For 6 items the start order becomes 0, 1, 5, 2, 4, 3. |
| 119 | `        label = list(range(n))` | `label`: the list of the numbers 0 to `n - 1`. |
| 120 | `        self.rng.shuffle(label)` | First random choice: shuffles `label`. Entry `x` of the list is now the real item for which the number `x` of the construction stands. |
| 121 | `        rows = [[label[(x + r) % n] for x in start] for r in range(n)]` | `rows`: the `n` orders. Row `r` takes each number of the start order, adds `r`, keeps the rest of the division by `n`, and replaces the result with its label. |
| 122 | `        self.rng.shuffle(rows)` | Second random choice: shuffles the order of the rows. So it is random which row stands at which place of the result. |
| 123 | `        return rows` | Returns the rows. |

### `Gen`: the step methods `YL`, `YP`, `YF`, `YC`, `YA` (lines 125 to 182)

| Line | Source | Explanation |
|---:|---|---|
| 125 | `    # ---- steps ----` | Comment: the methods that build the steps start here. Each method has the name of its step. |
| 126 | `    def YL(self):` | Starts the method `YL`. It builds the 32 processes of step `YL` for this session. |
| 127 | `        conds = [(k, p) for k in YL_KERNELS for p in YL_PLANS]` | `conds`: the 8 conditions of the step. The comprehension builds one pair for each of the 2 kernels and each of the 4 window plans, with the kernel as the outer loop. |
| 128 | `        for r in (1, 2):` | Starts the loop over the two replicates, 1 and 2. |
| 129 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 130 | `                block = list(conds)` | A copy of the list of conditions for this replicate and CPU. |
| 131 | `                self.rng.shuffle(block)` | Shuffles the copy. So each block of one replicate and one CPU has its own random order. |
| 132 | `                for k, (name, nwin, win_ms, bins) in block:` | Starts the loop over the 8 conditions in the shuffled order. Each one gives the kernel `k` and the parts of its window plan: the name, the number of windows, the window length in ms and the `bins` value. |
| 133 | `                    t = [self.trial("K=%s\|S=8M\|L=%d" % (k, win_ms), None, k + "@8M", nwin, win_ms, "closed", bins)]` | `t`: the one trial of the process. It has no prefix. The target is the kernel at 8 MiB with `nwin` windows of `win_ms` ms. That is 30000 ms of nominal kernel work for each of the four window plans. The counter mode is `closed`, and `bins` comes from the window plan. The condition label names the kernel, the size and the window length in ms, for example `K=asmread\|S=8M\|L=100`. |
| 134 | `                    self.add("%s-%s-cpu%d-p%d" % (name, k, cpu, r), cpu, "8M",` | Appends the process. Its tag holds the name of the window plan, the kernel, the CPU and the replicate, for example `L100-asmread-cpu2-p1`. |
| 135 | `                             [("rep_set", r), ("kernel", k), ("size", size_bytes("8M")), ("lcond", name)], t)` | The header pairs of the plan (the replicate, the kernel, the size in bytes, and the name of the window plan under the key `lcond`), and the trial. |
| 137 | `    def YP(self):` | Starts the method `YP`. It builds the 28 processes of step `YP` for this session. |
| 138 | `        for r in (1, 2):` | Starts the loop over the two replicates, 1 and 2. |
| 139 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 140 | `                block = list(YP_CONDS)` | A copy of the list of the 7 conditions for this replicate and CPU. |
| 141 | `                self.rng.shuffle(block)` | Shuffles the copy. So each block of 7 processes has its own random order of the conditions. |
| 142 | `                for name, extra in block:` | Starts the loop over the conditions in the shuffled order. `name` is the label of the condition, and `extra` is its option text. |
| 143 | `                    t = [self.trial("K=asmread\|S=8M\|rec=%s" % name, None, "asmread@8M", 100, 300)]` | `t`: the one trial of the process: `asmread` at 8 MiB, no prefix, 100 target windows of 300 ms. That is 30000 ms of nominal kernel work. The counters are closed. The condition label ends with the label of the condition, for example `K=asmread\|S=8M\|rec=P80`. |
| 144 | `                    self.add("%s-cpu%d-p%d" % (name, cpu, r), cpu, "8M",` | Appends the process. Its tag holds the label of the condition, the CPU and the replicate, for example `P80-cpu2-p1`. |
| 145 | `                             [("rep_set", r), ("kernel", "asmread"), ("size", size_bytes("8M")), ("pcond", name)],` | The header pairs of the plan: the replicate, the kernel, the size in bytes, and the label of the condition under the key `pcond`. |
| 146 | `                             t, extra)` | The last arguments: the trial, and the option text of the condition. That text is `--rec-pad` with the pad in bytes, or `--hot-copy`. |
| 148 | `    def YF(self):` | Starts the method `YF`. It builds the 288 processes of step `YF` for this session. |
| 149 | `        order = {}` | `order`: one table of orders per size and CPU, empty at first. |
| 150 | `        for s in YF_SIZES:` | Starts a loop over the four sizes, in their fixed order. |
| 151 | `            for cpu in self.cpus:` | Starts a loop over the two CPUs, in the order of the session. |
| 152 | `                order[s, cpu] = self.williams_square(len(YF_KERNELS))` | Builds a Williams square of the 6 kernels for this size and CPU. Each call makes two shuffles with `rng`: the labels and the row order. So each size and CPU gets its own random square. |
| 153 | `        for r in range(UNITS):` | Starts the loop over the 6 replicate sets. `r` runs from 0 to 5. |
| 154 | `            sizes = list(YF_SIZES)` | A copy of the list of sizes for this set. |
| 155 | `            self.rng.shuffle(sizes)` | Shuffles the copy. So each replicate set has its own random order of the sizes. |
| 156 | `            for s in sizes:` | Starts the loop over the sizes in that order. |
| 157 | `                for cpu in self.cpus:` | Starts the loop over the CPUs in the order of the session. All processes of the first CPU at this size come before those of the second CPU. |
| 158 | `                    for ki in order[s, cpu][r]:` | Starts the loop over the kernels, in the order that row `r` of the table of this size and CPU gives. `ki` is the number of a kernel. |
| 159 | `                        k = YF_KERNELS[ki]` | `k`: the name of the kernel with that number. |
| 160 | `                        ks = "%s@%s" % (k, s)` | `ks`: the kernel and the size in the form `KERNEL@SIZE`. |
| 161 | `                        t = [self.trial("K=%s\|S=%s" % (k, s), 1200, ks, 4, 300)] * 4` | `t`: the 4 trials of the process, all equal. The condition label names the kernel and the size. Each trial has a prefix of 1200 ms of the same kernel at the same size, and then 4 target windows of 300 ms. The counters are closed. So one process has 9600 ms of nominal kernel work. |
| 162 | `                        self.add("r%d-%s-cpu%d-%s" % (r + 1, s, cpu, k), cpu, s,` | Appends the process. Its tag holds the replicate set counted from 1, the size, the CPU and the kernel. |
| 163 | `                                 [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s))], t)` | The header pairs of the plan (the replicate set, the kernel and the size in bytes), and the trials. |
| 165 | `    def YC(self):` | Starts the method `YC`. It builds the 42 processes of step `YC` for this session. |
| 166 | `        extra = " --pmu-type %d --events %s" % (PMU_TYPE, YC_EVENTS)` | `extra`: the counter options for the command line: `--pmu-type 11`, and `--events` with the 6 events of `YC_EVENTS`. |
| 167 | `        for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. So all processes of the first CPU come before those of the second CPU. |
| 168 | `            cells = [(k, s) for k in YC_KERNELS for s in YC_SIZES]` | `cells`: the 21 cells of the step, built new for each CPU: each of the 7 kernels at each of the 3 sizes. |
| 169 | `            self.rng.shuffle(cells)` | Shuffles the cells. So each CPU has its own random order of the 21 cells. |
| 170 | `            for k, s in cells:` | Starts the loop over the 21 cells in the shuffled order. |
| 171 | `                t = [self.trial("K=%s\|S=%s\|count=read" % (k, s), None, "%s@%s" % (k, s), 20, 300, "read")]` | `t`: the one trial of the process. It has no prefix and 20 target windows of 300 ms, that is 6000 ms of nominal kernel work. The counter mode is `read`: the runner reads the counters for each window. The condition label names the kernel, the size and the counter mode, for example `K=oldread\|S=8M\|count=read`. |
| 172 | `                self.add("%s-%s-cpu%d" % (k, s, cpu), cpu, s,` | Appends the process. Its tag holds the kernel, the size and the CPU, for example `oldread-8M-cpu2`. |
| 173 | `                         [("rep_set", 1), ("kernel", k), ("size", size_bytes(s))], t, extra)` | The header pairs of the plan (the replicate set, which is always 1 here, the kernel and the size in bytes), the trial, and the counter options. |
| 175 | `    def YA(self):` | Starts the method `YA`. It builds the 9 processes of the acceptance step, in the fixed order of `YA_PROCS`. It does not use `rng`. |
| 176 | `        for name, k, s, opts in YA_PROCS:` | Starts the loop over the 9 entries of `YA_PROCS`. |
| 177 | `            ks = "%s@%s" % (k, s)` | `ks`: the kernel and the size in the form `KERNEL@SIZE`. |
| 178 | `            t = [self.trial("K=%s\|S=%s\|acc=%s" % (k, s, name), 400, ks, 3, 300)]` | `t`: the one trial of the process: a prefix of 400 ms of the same kernel, and then 3 target windows of 300 ms. The condition label names the kernel, the size and the name of the process. |
| 179 | `            self.add("%s-cpu2" % name, 2, s,` | Appends the process. Its tag is the name followed by `-cpu2`, and its CPU is 2. |
| 180 | `                     [("kernel", k), ("size", size_bytes(s)), ("acond", name)], t, " --trace" + opts)` | The header pairs (the kernel, the size in bytes, and the name under the key `acond`), the trial, and the option `--trace` followed by the options of the entry. |

### Functions `generate`, `plan_text`, `phase_ms`, `proc_ms`, `write` (lines 183 to 242)

| Line | Source | Explanation |
|---:|---|---|
| 183 | `def generate(base, div):` | Starts the function `generate`. It builds the processes of every step and session. |
| 184 | `    """Returns {(step, session): Gen}. YA only in session 1."""` | Description text: the function returns a dictionary from a pair of step and session to its `Gen` object. The step `YA` exists in session 1 only. |
| 185 | `    out = {}` | `out`: the result dictionary, empty at first. |
| 186 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 187 | `        for step in STEPS:` | Starts the loop over the steps, in the order of `STEPS`. |
| 188 | `            if step == "YA" and session == 2:` | Tests for the acceptance step `YA` in session 2. |
| 189 | `                continue` | Skips it. The acceptance step exists in session 1 only. |
| 190 | `            g = Gen(step, session, base, div)` | Creates the `Gen` object of this step and session. It gets its own seed and its own random number generator. |
| 191 | `            getattr(g, step)()` | Calls the method of `g` whose name is the step name. That method fills `g.procs`. |
| 192 | `            out[step, session] = g` | Stores the object. |
| 193 | `    return out` | Returns the dictionary. |
| 196 | `def plan_text(g, idx, p):` | Starts the function `plan_text`. It returns the text of the plan file of the process `p`, which has the number `idx` in the step of `g`. |
| 197 | `    pairs = [("step", g.step), ("session", g.session), ("cpu", p["cpu"]),` | `pairs`: the header pairs of the plan. First the step, the session and the CPU. |
| 198 | `             ("bytes", p["bytes"]), ("proc", idx)] + p["keys"] + \` | Continues the list: the buffer size in bytes and the number of the process, then the pairs of the process itself. The backslash joins the next line to this statement. |
| 199 | `            [("seed", g.seed), ("test", 0 if g.div == 1 else 1)]` | Ends the list: the seed of the step and session, and `test`. `test` is 0 for a real plan and 1 when the durations were divided by a test divisor above 1. |
| 200 | `    lines = ["# bwx8-plan v1",` | `lines`: the lines of the plan file. The first one is the fixed text `# bwx8-plan v1`, the name and the version of the format. |
| 201 | `             "# " + " ".join("%s=%s" % kv for kv in pairs),` | The second one: `#` and all header pairs as `key=value`, with one blank between them. |
| 202 | `             "# trial cond rep prev pfx pred tgt nwin win_ms count bins"]` | The third one: the names of the 11 columns of a trial line. |
| 203 | `    seen = {}` | `seen`: how often each condition label was used up to now, empty at first. |
| 204 | `    for n, t in enumerate(p["trials"]):` | Starts the loop over the trials. `n` is the number of the trial, counted from 0. |
| 205 | `        seen[t[0]] = seen.get(t[0], 0) + 1      # rep: repeat number of this cond` | Counts the use of the condition label of this trial. The count is the value of the column `rep`: 1 for the first trial with this label, 2 for the second, and so on. |
| 206 | `        lines.append("%d %s %d %s %s %s %s %d %d %s %d" % ((n, t[0], seen[t[0]]) + t[1:]))` | Adds the trial line: the trial number, the condition label, the repeat number, and then the other 8 values of the trial tuple. These are the previous activity, the prefix, the predecessor, the target, the number of windows, the window length in ms, the counter mode and the bins value. One blank separates the fields. |
| 207 | `    return "\n".join(lines) + "\n"` | Returns the lines joined with newlines, with a newline at the end. |
| 210 | `def phase_ms(tok):` | Starts the function `phase_ms`. It returns the duration in ms of one phase text of a trial. |
| 211 | `    return 0 if tok == "-" else int(tok.split(":")[1])` | Returns 0 for `-`, the mark of a phase that the trial does not have. In every other case it returns the number after the colon of a text such as `asmread@8M:1200`. |
| 214 | `def proc_ms(p):` | Starts the function `proc_ms`. |
| 215 | `    """Nominal kernel work of one process, in ms."""` | Description text: the function returns the nominal kernel work of one process in ms. |
| 216 | `    return sum(phase_ms(t[1]) + phase_ms(t[2]) + phase_ms(t[3]) + t[5] * t[6] for t in p["trials"])` | Adds up over all trials: the durations of the previous activity, the prefix and the predecessor, plus the number of target windows times the window length. This is the planned time of the timed parts. The real run time of a process is longer. |
| 219 | `def write(gens, out, manifest):` | Starts the function `write`. It writes all files into the folder `out`. `manifest` is the text of the file `MANIFEST.txt`. |
| 220 | `    os.makedirs(out, exist_ok=True)` | Creates the output folder when it does not exist. |
| 221 | `    for session in (1, 2):` | Starts a loop over the two sessions. |
| 222 | `        shutil.rmtree(os.path.join(out, "s%d" % session), ignore_errors=True)` | Removes the folder `s1` or `s2` with everything in it. A folder that does not exist gives no error. So no file of an older run stays in these folders. |
| 223 | `    for (step, session), g in gens.items():` | Starts the loop over all steps and sessions. |
| 224 | `        sdir = os.path.join(out, "s%d" % session)` | `sdir`: the folder of the session. |
| 225 | `        os.makedirs(os.path.join(sdir, step))` | Creates the folder for the plan files of the step, and the session folder with it. |
| 226 | `        rows = ["idx\ttag\tcpu\tbytes\tplan\targs"]` | `rows`: the rows of the schedule file. The first row holds the six column names, with tabs between them. |
| 227 | `        for idx, p in enumerate(g.procs):` | Starts the loop over the processes, in the order in which they will run. `idx` counts from 0. |
| 228 | `            name = "%04d.plan" % idx` | `name`: the name of the plan file: the `idx` with 4 digits and the ending `.plan`, for example `0017.plan`. |
| 229 | `            with open(os.path.join(sdir, step, name), "w") as f:` | Opens the plan file for writing. |
| 230 | `                f.write(plan_text(g, idx, p))` | Writes the text of the plan. |
| 231 | `            # The plan path is relative to the folder of run_bwx10.sh.` | Comment: the path of the plan in the `args` column is relative to the folder of the run script `run_bwx10.sh`. |
| 232 | `            args = "--trial --cpus %d --bytes %d --plan sched10/s%d/%s/%s%s" % (` | `args`: the options of the process for the runner: `--trial` (the mode that runs a plan), `--cpus` with the one worker CPU, `--bytes` with the buffer size, and `--plan` with the path `sched10/s<session>/<STEP>/<name>`. The folder name `sched10` is fixed here, also when `--out` names another folder. |
| 233 | `                p["cpu"], p["bytes"], session, step, name, p["extra"])` | The values for that text: the CPU, the size in bytes, the session, the step, the name of the plan file, and at the end the extra options of the process. |
| 234 | `            rows.append("%d\t%s\t%d\t%d\t%s\t%s" % (idx, p["tag"], p["cpu"], p["bytes"], name, args))` | Adds the schedule row of the process: its `idx`, its tag, its CPU, its size in bytes, the name of its plan file and its options, with tabs between them. |
| 235 | `        with open(os.path.join(sdir, step + ".tsv"), "w") as f:` | Opens the schedule file `<STEP>.tsv` of the step for writing. |
| 236 | `            f.write("\n".join(rows) + "\n")` | Writes all rows, each with a newline at its end. |
| 237 | `        with open(os.path.join(sdir, step + ".bin"), "w") as f:` | Opens the file `<STEP>.bin` for writing. |
| 238 | `            f.write(BINARY[step] + "\n")` | Writes the word of the binary of the step and a newline. |
| 239 | `    with open(os.path.join(out, "MANIFEST.txt"), "w") as f:` | Opens the file `MANIFEST.txt` in the output folder for writing. |
| 240 | `        f.write(manifest)` | Writes the manifest text. |

### Balance checks: `yf_orders_ok`, `blocks_ok` (lines 243 to 262)

| Line | Source | Explanation |
|---:|---|---|
| 243 | `def yf_orders_ok(g):` | Starts the function `yf_orders_ok`, the balance check of step `YF`. It reads the kernel orders from the finished list of processes. |
| 244 | `    """Per size and CPU: the kernel orders of the 6 replicate sets form a Williams square."""` | Description text: for each size and CPU, the kernel orders of the 6 replicate sets form a Williams square. |
| 245 | `    seen = {}` | `seen`: the collected orders, empty at first. |
| 246 | `    for p in g.procs:` | Starts the loop over the processes in schedule order. |
| 247 | `        k = dict(p["keys"])` | `k`: the header pairs of the process as a dictionary. |
| 248 | `        seen.setdefault((k["size"], p["cpu"]), {}).setdefault(k["rep_set"], []).append(` | Appends a value for this process to the list of its size, CPU and replicate set. The value stands in the next line. `setdefault` creates an entry that is missing. So `seen` maps each pair of size and CPU to a dictionary, which maps each replicate set to a list in schedule order. |
| 249 | `            YF_KERNELS.index(k["kernel"]))` | The value that is appended: the number of the kernel of the process, which is the place of the kernel in `YF_KERNELS`. |
| 250 | `    return len(seen) == len(YF_SIZES) * 2 and all(` | Starts the result. First condition: there are 8 pairs of size and CPU, 4 sizes times 2 CPUs. |
| 251 | `        len(sets) == UNITS and williams_ok(list(sets.values()), len(YF_KERNELS)) for sets in seen.values())` | Second condition, for every pair of size and CPU: it has 6 replicate sets, and their orders pass `williams_ok` for 6 items. |
| 254 | `def blocks_ok(g, keys, conds):` | Starts the function `blocks_ok`, the balance check of a step whose processes come in shuffled blocks. |
| 255 | `    """The processes come in blocks of len(conds), and every block holds each condition once.` | Description text: the processes come in blocks of as many processes as there are conditions, and every block holds each condition once. |
| 256 | ``    A condition is the tuple of the header values named by `keys`."""`` | Continues the text: a condition is the tuple of the header values that `keys` names. |
| 257 | `    got = [tuple(dict(p["keys"]).get(k) for k in keys) for p in g.procs]` | `got`: the condition of every process in schedule order, as a tuple of its header values for the given keys. |
| 258 | `    size = len(conds)` | `size`: the number of conditions, which is the length of one block. |
| 259 | `    return len(got) % size == 0 and all(` | Starts the result. First condition: the number of processes is a multiple of the block length. |
| 260 | `        sorted(got[i:i + size]) == sorted(conds) for i in range(0, len(got), size))` | Second condition: each block, sorted, is equal to the sorted list of the conditions. So each block holds every condition exactly once. |

### Function `report`: counts, nominal kernel work and balance lines (lines 263 to 294)

| Line | Source | Explanation |
|---:|---|---|
| 263 | `def report(gens):` | Starts the function `report`. It builds the text that the program prints, and it runs the balance checks. |
| 264 | `    ok = True` | `ok`: stays true while every balance check passes. |
| 265 | `    lines = ["step session binary processes trials nominal_kernel_work_s"]` | `lines`: the lines of the report. The first one is the head of the table: step, session, binary, number of processes, number of trials, and nominal kernel work in seconds. |
| 266 | `    total = {1: [0, 0], 2: [0, 0]}` | `total`: two sums per session: the processes and the nominal work in ms. |
| 267 | `    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):` | Starts the loop over all steps and sessions, sorted by the session and then by the place of the step in `STEPS`. |
| 268 | `        n, tr = len(g.procs), sum(len(p["trials"]) for p in g.procs)` | `n`: the number of processes of the step. `tr`: the number of trials of all its processes. |
| 269 | `        ms = sum(map(proc_ms, g.procs))` | `ms`: the nominal kernel work of the step in ms, the sum of `proc_ms` over its processes. |
| 270 | `        lines.append("%s %d %s %d %d %g" % (step, session, BINARY[step], n, tr, ms / 1000))` | Adds the table row of the step: its name, the session, the word of the binary, `n`, `tr` and the nominal work in seconds. `%g` prints a number with at most 6 significant digits and without zeros at its end. |
| 271 | `        total[session][0] += n` | Adds the processes to the sum of the session. |
| 272 | `        total[session][1] += ms` | Adds the nominal work to the sum of the session. |
| 273 | `    for session in (1, 2):` | Starts a loop over the two sessions, for the total lines. |
| 274 | `        lines.append("session %d total: %d processes, nominal kernel work %g s (%g min)"` | Adds the total line of the session: the number of processes, and the nominal kernel work in seconds and in minutes. |
| 275 | `                     % (session, total[session][0], total[session][1] / 1000, round(total[session][1] / 60000, 2)))` | The values of that line: the session, the number of processes, the nominal work in seconds, and the nominal work in minutes, rounded to two decimal places. |
| 276 | `    lines.append("balance:")` | Adds the heading of the balance part. |
| 277 | `    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):` | Starts a second loop over all steps and sessions, in the same order, for the balance checks. |
| 278 | `        if step == "YF":` | The check of step `YF`. |
| 279 | `            a = yf_orders_ok(g)` | `a`: the result of `yf_orders_ok`. |
| 280 | `            text = ("per size and CPU the kernel orders of the 6 sets put each kernel once at each position, "` | `text`: the sentence of the report for this check. It says that per size and CPU the kernel orders of the 6 sets put each kernel once at each position. |
| 281 | `                    "and each ordered pair of kernels is neighbours once")` | Ends the sentence: and each ordered pair of kernels is once a pair of neighbours. |
| 282 | `        elif step == "YL":` | The check of step `YL`. |
| 283 | `            a = blocks_ok(g, ("kernel", "lcond"), [(k, p[0]) for k in YL_KERNELS for p in YL_PLANS])` | `a`: the result of `blocks_ok` with the header keys `kernel` and `lcond`. The list of the 8 conditions for that check holds each kernel with the name of each window plan. |
| 284 | `            text = "each block of 8 processes holds every kernel and window plan once"` | `text`: the sentence for this check: each block of 8 processes holds every kernel and window plan once. |
| 285 | `        elif step == "YP":` | The check of step `YP`. |
| 286 | `            a = blocks_ok(g, ("pcond",), [(c[0],) for c in YP_CONDS])` | `a`: the result of `blocks_ok` with the header key `pcond` and the 7 labels of `YP_CONDS` as the conditions. |
| 287 | `            text = "each block of 7 processes holds every condition once"` | `text`: the sentence for this check: each block of 7 processes holds every condition once. |
| 288 | `        else:` | Every other step has no balance check. |
| 289 | `            continue` | Skips it. |
| 290 | `        ok = ok and a` | `ok` becomes false when this check failed. |
| 291 | `        lines.append("%s session %d: %s: %s" % (step, session, text, "yes" if a else "NO"))` | Adds the balance line of the step and session: the sentence, and then `yes` when the check passed or `NO` when it failed. |
| 292 | `    return "\n".join(lines) + "\n", ok` | Returns the report text and the result of all checks. |

### Function `main` (lines 295 to 316)

| Line | Source | Explanation |
|---:|---|---|
| 295 | `def main():` | Starts the function `main`. |
| 296 | `    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])` | Creates the reader of the command line. Its description is the first line of the description text of the file. |
| 297 | `    ap.add_argument("--seed", type=int, default=20261115, help="base seed")` | The option `--seed`: the base seed, a whole number. It is 20261115 when the option is not given. |
| 298 | `    ap.add_argument("--test-divisor", type=int, default=1)` | The option `--test-divisor`: the number by which every duration is divided. It is 1 when the option is not given, which changes nothing. |
| 299 | `    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sched10"))` | The option `--out`: the output folder. When it is not given, it is the folder `sched10` in the folder of this file. |
| 300 | `    a = ap.parse_args()` | Reads the command line. |
| 301 | `    if a.test_divisor < 1 or MIN_WIN_MS % a.test_divisor:` | Tests the divisor: it must be at least 1, and it must divide `MIN_WIN_MS` without a rest. |
| 302 | `        sys.exit("--test-divisor must divide %d ms" % MIN_WIN_MS)` | If not: prints the message to the error output and ends the program with exit status 1. No file is written. |
| 303 | `    gens = generate(a.seed, a.test_divisor)` | Builds the processes of all steps and sessions. |
| 304 | `    text, ok = report(gens)` | Builds the report text and runs the balance checks. |
| 305 | `    manifest = "base_seed=%d\ntest_divisor=%d\n" % (a.seed, a.test_divisor)` | `manifest`: the text of `MANIFEST.txt`. Its first two lines give the base seed and the test divisor. |
| 306 | `    manifest += "".join("seed %s s%d %d\n" % (step, session, g.seed) for (step, session), g in gens.items())` | Adds one line per step and session with its seed, in the form `seed STEP sN SEED`. |
| 307 | `    manifest += "".join("bin %s s%d %s\n" % (step, session, BINARY[step]) for (step, session) in gens)` | Adds one line per step and session with the word of its binary, in the form `bin STEP sN WORD`. |
| 308 | `    manifest += "watch none\n"` | Adds the line `watch none`: no step has a `.watch` file. |
| 309 | `    write(gens, a.out, manifest)` | Writes all files. This happens before the result of the balance checks is used. |
| 310 | `    print("written: %s" % a.out)` | Prints the output folder. |
| 311 | `    sys.stdout.write(text)` | Prints the report. |
| 312 | `    sys.exit(0 if ok else 1)` | Ends the program with exit status 0 when every balance check passed, and with 1 when one failed. The files are written in both cases. |
| 315 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 316 | `    main()` | Runs `main`. |
