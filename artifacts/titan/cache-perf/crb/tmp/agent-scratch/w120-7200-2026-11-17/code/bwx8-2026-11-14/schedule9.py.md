# `schedule9.py` explained, line by line

- Source file: `bwx8-2026-11-14/schedule9.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 256 lines, 12122 bytes).
- sha256 of the source when this page was built: `db8feac08509211e8bff451d1510a9cbf64d6d21a15c06fc70bcde48f8a50fc5`.

## Short version: purpose

`schedule9.py` writes the input files of round 2 for the run script `run_bwx9.sh`: for each step and session one schedule file with one row per process, one plan file per process, and an empty `.watch` file for each step that runs with the host sampler. It fixes the order of the processes with a random number generator whose seed depends only on the base seed, the step and the session. It also checks the balance of the kernel orders of step `XN`, and it prints the counts and the nominal kernel work.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 2**: the second set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `X`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`read_nop16`, `read_nop32`**: two kernels of the runner `bwx8`. Each is the `asmread` loop with 16 or 32 `nop` instructions added to each loop pass of 256 B. A `nop` is an instruction that does nothing.
- **`read_sparse`**: a kernel of the runner `bwx8`. Each loop pass handles 128 B with 4 `ldp q` loads and 9 `nop` instructions.
- **Process**: one start of a benchmark binary.
- **Run script**: the script `run_bwx9.sh`. It starts the processes of a schedule on CRB, one at a time.
- **`schedule8.py`**: the generator of round 1, in the same folder. This file loads it as a module and uses its class `Gen` and three of its functions.
- **Step**: one batch of processes of a round, for example `XW`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time. Round 2 uses a previous activity in two conditions of `XW`, and a prefix in `XN` and `XF`. No trial of round 2 has a predecessor.
- **Target, window**: the target is the kernel that a trial measures. A window is one timed period of it. Every window of round 2 has a planned length of 300 ms.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Condition**: one setting that a step compares, and the label that names it in the plan. In `XW` it is one target kernel at one size with or without a previous activity.
- **Cell**: one combination of the factors of a step, for example one kernel at one buffer size.
- **Replicate set, replicate**: a replicate set is one run of every kernel of step `XN` for one size and CPU. A replicate of `XW` or `XF` is one pass through all conditions or cells on both CPUs. A replicate of a counter step holds, for each CPU, each of the 3 long cells (100 windows) and 1 or 2 of the 3 short cells (20 windows).
- **Block**: the processes of one replicate on one CPU.
- **Event set**: one of the three lists A, B and C of 6 counter events each.
- **Base seed, seed**: the base seed is the one number that the caller can set with `--seed`. The seed of a step and session is derived from it.
- **Test divisor**: a number by which every duration is divided, for local tests only.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters at the boundaries of the target windows.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter device**: the hardware counters of the CPU cores, as Linux lists them. Linux gives the device a type number. The option `--pmu-type` carries that number.
- **Host sampler**: the program `hostwatch.py`. The run script starts it beside a process when the step has a `.watch` file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB**: 1024 bytes.

## Main flow

1. Load the older generator `schedule8.py` from the folder of this file (lines 33 to 35).
2. Read the options `--seed`, `--test-divisor` and `--out`. End with exit status 1 when the divisor does not divide 300 ms (lines 237 to 243).
3. Build the processes of every step and session with one `Gen9` object each (line 244, lines 163 to 173). The constructor, which comes from `schedule8.py`, derives the seed of the step and session and starts its random number generator.
4. Each step method fills the list of processes of its step in run order. They are called in the order of `STEPS`: `XEV` (lines 120 to 125), `XW` (lines 78 to 89), `XCA`, `XCB` and `XCC` (lines 91 to 118), `XN` (lines 127 to 150) and `XF` (lines 152 to 160).
5. Build the report text: per step and session the number of processes and trials and the nominal kernel work, then the total of session 1, then the result of the balance check of `XN` (line 245, lines 213 to 233).
6. Build the text of `MANIFEST.txt`: the base seed, the test divisor, and the seed of every step and session (lines 246 to 248).
7. Remove the folders `s1` and `s2` of the output folder and write the plan files, the schedule files, the `.watch` files and `MANIFEST.txt` (line 249, lines 176 to 197).
8. Print the output folder and the report. End with exit status 0, or with 1 when the balance check failed (lines 250 to 252).

## Behavior a reader must know

- The seed of a step and session is computed in `schedule8.py` (function `step_seed`): the first 8 hexadecimal digits of the sha256 of the text `BASE/STEP/SESSION`, read as a whole number. The base seed is 20261115 unless `--seed` gives another one (line 238).
- Each step and session has its own generator `random.Random(seed)`, made by the constructor of `Gen` in `schedule8.py`. All shuffles of a step use it, in a fixed sequence. So the same options always give the same files, and session 2 has random orders of its own.
- The steps and their sizes, from the constants and the loops of this file:
  - `XEV`: 3 processes in session 1 only, each with 0.9 s of nominal kernel work. Sum: 2.7 s.
  - `XW`: 28 processes per session. 20 have 30 s. The 8 processes of the conditions `W1` and `W2` have 33 s: 3 s of previous activity come first. Sum: 864 s.
  - `XCA`, `XCB`, `XCC`: 18 processes each per session: 12 with 30 s and 6 with 6 s. Sum: 396 s for each step.
  - `XN`: 144 processes per session, each with 9.6 s. Sum: 1382.4 s.
  - `XF`: 90 processes per session, each with 9.6 s. Sum: 864 s.
- How the order of `XW` and `XF` is made (lines 78 to 89, lines 152 to 160): the run order is the replicate (2 in `XW`, 3 in `XF`), inside a replicate the 2 CPUs in the order of the session, and inside a CPU all conditions or cells in a newly shuffled order (7 in `XW`, 15 in `XF`). So each block holds every condition or cell once. The positions inside a block are random and not balanced.
- How the order of a counter step is made (lines 91 to 109):
  - First, for each CPU, the three short cells are shuffled and split over the two blocks: 1 and 2, or 2 and 1 (lines 96 to 99).
  - The run order is block 1 and then block 2, inside a block the 2 CPUs in the order of the session, and inside a CPU the three long cells and the short cells of that block in a shuffled order.
  - So each block of a CPU holds every long cell once, and each CPU runs every short cell once per session.
- How the order of `XN` is made (lines 127 to 150):
  - First 6 different kernel orders are drawn for each size and CPU: 3 sizes in a fixed order, and inside a size the 2 CPUs in the order of the session. A draw is repeated until each kernel stands once or twice at each of the 4 positions (lines 130 to 133).
  - Then, for each of the 6 replicate sets, the 3 sizes are shuffled once (line 143).
  - The run order is: replicate set, then size, then CPU, then the 4 kernels in the order `r` of the selection of that size and CPU.
  - The size order inside a replicate set is shuffled but not balanced.
- `XEV` has a fixed order on CPU 2 and uses no random number (lines 120 to 125).
- Not random: the order of the two CPUs. Session 1 always runs CPU 2 before CPU 41, and session 2 runs CPU 41 before CPU 2. The table `CPUS` of `schedule8.py` holds these orders.
- Only step `XN` has a balance check (lines 200 to 210, line 228). The program runs it on the finished list of processes. A failed check gives a line that ends with `NO` and exit status 1. The files are written before the exit status is set (lines 249 to 252).
- The folders `s1` and `s2` of the output folder are removed before the new files are written (line 179).
- The plan path in the `args` column always starts with `sched9/`, also when `--out` names another folder (line 189).
- Each process gets one worker CPU through `--cpus`, CPU 2 or CPU 41, and its buffer size through `--bytes` (line 189). The `args` hold no option for the controlling thread of the runner. By the note `DECISIONS-bwx8.md` that thread then uses CPU 0.
- The buffer size of a process is the target size. In the condition `W2` of `XW` the previous activity has the size 1 MiB inside a buffer of 8 MiB. By the note `DECISIONS-bwx8.md` a phase runs whole passes over the first bytes of the buffer, up to its size.
- The rows of the steps `XEV`, `XCA`, `XCB` and `XCC` hold the options `--pmu-type 11` and `--events` with the event set (line 92, line 125). So the run script needs no counter setting in its environment for the schedules of this file.
- The nominal kernel work counts planned durations only (function `proc_ms` of `schedule8.py`).
- With a test divisor N above 1 every duration is divided by N and the plans get `test=1`. The numbers of windows and the order of the processes do not change.
- The program reads no input file and starts nothing on CRB. It needs the file `schedule8.py` beside it (lines 34 to 35).

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/schedule9.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (256 lines, 12122 bytes, sha256 `db8feac08509211e8bff451d1510a9cbf64d6d21a15c06fc70bcde48f8a50fc5`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text: files written, options, the seven steps (lines 1 to 26)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""schedule9.py - schedules and plan files of round 2 (steps XW XCA XCB XCC XEV XN XF).` | Starts the description text of the file. First line: the name and the purpose. The program writes the schedules and the plan files of round 2, for the steps `XW`, `XCA`, `XCB`, `XCC`, `XEV`, `XN` and `XF`. `main` uses this line as the description in the help text. |
| 4 | `Usage: schedule9.py [--seed N] [--test-divisor N] [--out DIR]` | Text of the description: the usage. The three options are optional: the base seed, the test divisor and the output folder. |
| 6 | `It writes, for session 1 and 2 and for each step:` | Text of the description: the list of the files that the program writes for session 1, for session 2 and for each step. |
| 7 | `  DIR/s<session>/<STEP>.tsv        one row per process (idx, tag, cpu, bytes, plan, args)` | Text of the description: the schedule file of a step. It has one row per process, with the columns `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`. |
| 8 | `  DIR/s<session>/<STEP>/NNNN.plan  one plan file per process (plan format v1 of bwx8)` | Text of the description: one plan file per process, in a folder with the name of the step. The plan format is version 1, which the runner `bwx8` reads. |
| 9 | `  DIR/s<session>/<STEP>.watch      empty; only for the steps that run with the host sampler` | Text of the description: the `.watch` file of a step. It is empty, and the program writes it only for the steps that run with the host sampler. The file tells the run script to start the program `hostwatch.py` beside each process of the step. |
| 10 | `  DIR/MANIFEST.txt                 base seed, test divisor, and the seed of each step and session` | Text of the description: the file `MANIFEST.txt`. It holds the base seed, the test divisor, and the seed of each step and session. |
| 11 | `DIR is "sched9" beside this file by default. The folders DIR/s1 and DIR/s2 are replaced.` | Text of the description: the output folder is `sched9` in the folder of this file, unless `--out` names another one. The program removes the folders `s1` and `s2` in it and writes them new. |
| 12 | `The step XEV exists in session 1 only.` | Text of the description: the step `XEV` exists in session 1 only. |
| 13 | `--test-divisor N divides every duration by N and marks the plans test=1 (local chain tests only).` | Text of the description: `--test-divisor N` divides every duration by N and writes `test=1` into the plans. It is only for local tests of the whole chain of scripts. |
| 14 | `The same options give the same bytes. Exit status 1 if a balance check fails.` | Text of the description: two runs with the same options write the same bytes. The exit status is 1 when a balance check fails. |
| 16 | `Steps (CPUs 2 and 41; session 2 uses the reversed CPU order; one process at a time):` | Text of the description: the heading of the list of steps. The worker CPUs are 2 and 41. Session 2 uses the two CPUs in the reverse order. One process runs at a time. |
| 17 | `  XW   watch and onset: one trial, 100 windows of 300 ms, count closed, 7 conditions W0 to W6,` | Step `XW`: one trial per process with 100 target windows of 300 ms, that is 30 s. The counter mode is `closed`, so the runner uses no counters. The 7 conditions have the names `W0` to `W6` (lines 49 to 51). The text names the step watch and onset. The host sampler runs beside each process of this step (line 38). By the note `DECISIONS-bwx8.md` the onset rule of this step looks at the time at which the rate of a kernel first rises inside a process. |
| 18 | `       2 processes per condition and CPU. Order: replicate, then CPU, then the 7 conditions shuffled.` | Continues the text on the step: each condition runs 2 processes per CPU. The order is the replicate, then the CPU, then the 7 conditions in a shuffled order. |
| 19 | `  XCA XCB XCC   sustained with counters (count read), one event set per step, given in the args` | Steps `XCA`, `XCB` and `XCC`: long trials with counters. The counter mode is `read`: the runner reads the counters for each window. Each step has one event set (A, B or C), a list of 6 counter events. The sentence about the place of the set ends in the next line. |
| 20 | `       column. Per CPU: 2 processes each of read, asmread, oldread at 8M with 100 windows, and one` | Continues the text: the event set stands in the `args` column of the schedule. Per CPU, each of the kernels `read`, `asmread` and `oldread` runs 2 processes at a buffer size of 8 MiB with 100 windows. |
| 21 | `       process each of read at 1M, 32K and 16M with 20 windows.` | Continues the text: and the kernel `read` runs one process each at 1 MiB, 32 KiB and 16 MiB with 20 windows. So a CPU has 9 processes in each of these steps. |
| 22 | `  XEV  event acceptance: CPU 2 only, one process per event set, 3 windows, count read.` | Step `XEV`, the acceptance of the counter events: 3 processes on CPU 2 only, one per event set, each with 3 windows and the counter mode `read`. By the note `DECISIONS-bwx8.md` the three steps with counters start only after the output of this step shows that every event opened. |
| 23 | `  XN   core-limit family: trials as step S2 of schedule8.py; kernels asmread, read_nop16,` | Step `XN`, the core-limit family. Its trials have the form of step `S2` of the older generator `schedule8.py`: 4 trials per process, each with a prefix of 1200 ms and 4 target windows of 300 ms of the same kernel. The list of the 4 kernels starts here: `asmread` and `read_nop16`. |
| 24 | `       read_nop32, read_sparse; sizes 32K, 1M, 8M; 6 replicate sets per size and CPU.` | Continues the text on `XN`: the kernels `read_nop32` and `read_sparse`. The buffer sizes are 32 KiB, 1 MiB and 8 MiB. Each size and CPU has 6 replicate sets. A replicate set is one run of every kernel. |
| 25 | `  XF   finer sizes: trials as step S2; 3 processes per kernel, size and CPU.` | Step `XF`, the finer buffer sizes: trials of the same form as in `XN`. Each cell of a kernel and a size (lines 57 to 58) runs 3 processes per CPU. |
| 26 | `"""` | Ends the description text. |

### Imports and constants (lines 27 to 62)

| Line | Source | Explanation |
|---:|---|---|
| 27 | `import argparse` | Loads the Python module `argparse`, which reads the command line options. |
| 28 | `import itertools` | Loads `itertools`: used to build every order of a small set of items. |
| 29 | `import os` | Loads `os`: paths and folders. |
| 30 | `import shutil` | Loads `shutil`: used to remove a folder tree. |
| 31 | `import sys` | Loads `sys`: the standard output and the exit status. |
| 33 | `sys.dont_write_bytecode = True           # the import below must not write a file into this folder` | Tells Python to write no compiled copy of a module that it loads. Such a copy is a `.pyc` file in a folder `__pycache__`. By the comment the import of line 35 must not write a file into this folder. |
| 34 | `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` | Puts the folder of this file at the front of the list of folders in which Python looks for a module. So line 35 finds `schedule8.py` beside this file, also when the program is started from another folder. |
| 35 | `import schedule8                         # noqa: E402  (Gen, plan_text, proc_ms, size_bytes)` | Loads the older generator `schedule8.py` as a module. By the comment this file uses four things of it: the class `Gen`, and the functions `plan_text`, `proc_ms` and `size_bytes`. `noqa: E402` tells a style checker to accept an import that does not stand at the top of the file. |
| 37 | `STEPS = ["XEV", "XW", "XCA", "XCB", "XCC", "XN", "XF"]` | `STEPS`: the names of the 7 steps, in the order in which the program builds and reports them. |
| 38 | `WATCH_STEPS = ["XW", "XCA", "XCB", "XCC"]          # steps that run with hostwatch.py` | `WATCH_STEPS`: the 4 steps that run with the host sampler `hostwatch.py`. The function `write` makes a `.watch` file for each of them (lines 194 to 195). |
| 39 | `PMU_TYPE = 11                                      # armv8_pmuv3_0 on CRB (DECISIONS-bwx8.md)` | `PMU_TYPE`: 11, the type number that Linux gives to the counter device `armv8_pmuv3_0` of the cores on CRB. By the comment the value comes from the notes file `DECISIONS-bwx8.md`. It goes into the option `--pmu-type` of the processes that use counters. |
| 40 | `EVENTS = {` | `EVENTS`: the three event sets A, B and C. Each is a text of 6 counter events in the form `NAME=CODE`, with commas between them. The text goes into the option `--events` of the runner. |
| 41 | `    "A": "cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17,"` | Set A, first part: the cycles of the core (`cpu_cycles`), the completed instructions (`inst_retired`), the refills of the first-level data cache (`l1d_cache_refill`) and the refills of the L2 cache (`l2d_cache_refill`). The number after each name is the event code. |
| 42 | `         "l3d_cache_refill=0x2a,stall_backend_mem=0x4005",` | Set A, second part: the events `l3d_cache_refill` and `stall_backend_mem`. Python joins the two text pieces of lines 41 to 42 into one text. So the set holds 6 events. |
| 43 | `    "B": "l1d_cache_lmiss_rd=0x39,l2d_cache_lmiss_rd=0x4009,l3d_cache_lmiss_rd=0x400b,"` | Set B, first part: `l1d_cache_lmiss_rd`, `l2d_cache_lmiss_rd` and `l3d_cache_lmiss_rd`. The note `DECISIONS-bwx8.md` calls the first two the L1 long miss and the L2 long miss. |
| 44 | `         "ll_cache_miss_rd=0x37,l2d_cache=0x16,bus_access=0x19",` | Set B, second part: `ll_cache_miss_rd`, `l2d_cache` and `bus_access`. |
| 45 | `    "C": "exc_taken=0x09,l1d_tlb_refill=0x05,dtlb_walk=0x34,l2d_cache_wb=0x18,"` | Set C, first part: `exc_taken`, `l1d_tlb_refill`, `dtlb_walk` and `l2d_cache_wb`. The note `DECISIONS-bwx8.md` calls the last one the L2 write-back. |
| 46 | `         "l3d_cache_allocate=0x29,mem_access=0x13",` | Set C, second part: `l3d_cache_allocate` and `mem_access`. |
| 47 | `}` | Ends the dictionary `EVENTS`. By the note `DECISIONS-bwx8.md` the codes come from the folder `events` of the counter device on CRB. The same note treats the events as raw names: what a count means for the caches is a hypothesis there. |
| 48 | `# XW: name, target kernel, target size, previous activity (3000 ms) or None.` | Comment: each entry of `XW_CONDS` holds the name of the condition, the target kernel, the target size, and the previous activity or `None`. A previous activity lasts 3000 ms. |
| 49 | `XW_CONDS = [("W0", "read", "8M", None), ("W1", "read", "8M", "oldread@8M"),` | `XW_CONDS`: the 7 conditions of step `XW`. `W0`: the new read kernel `read` at 8 MiB with no previous activity. `W1`: `read` at 8 MiB after 3 s of the old read kernel `oldread` at 8 MiB. |
| 50 | `            ("W2", "read", "8M", "read@1M"), ("W3", "asmread", "8M", None),` | `W2`: `read` at 8 MiB after 3 s of `read` at 1 MiB. `W3`: the hand-written loop `asmread` at 8 MiB. |
| 51 | `            ("W4", "oldread", "8M", None), ("W5", "read", "4M", None), ("W6", "read", "16M", None)]` | `W4`: `oldread` at 8 MiB. `W5`: `read` at 4 MiB. `W6`: `read` at 16 MiB. The conditions `W3` to `W6` have no previous activity. |
| 52 | `XC_LONG = [("read", "8M"), ("asmread", "8M"), ("oldread", "8M")]     # 2 processes each, 100 windows` | `XC_LONG`: the three long cells of a counter step: `read`, `asmread` and `oldread` at 8 MiB. By the comment each runs 2 processes per CPU, with 100 windows. |
| 53 | `XC_SHORT = [("read", "1M"), ("read", "32K"), ("read", "16M")]        # 1 process each, 20 windows` | `XC_SHORT`: the three short cells: `read` at 1 MiB, 32 KiB and 16 MiB. By the comment each runs 1 process per CPU, with 20 windows. The note `DECISIONS-bwx8.md` calls them references. |
| 54 | `XN_KERNELS = ["asmread", "read_nop16", "read_nop32", "read_sparse"]` | `XN_KERNELS`: the four kernels of step `XN`. In the source `bwx8.c`, `read_nop16` and `read_nop32` are the `asmread` loop with 16 or 32 `nop` instructions in each loop pass of 256 B. A `nop` does nothing. `read_sparse` has 4 loads of 32 B each and 9 `nop` in each loop pass of 128 B. |
| 55 | `XN_SIZES = ["32K", "1M", "8M"]` | `XN_SIZES`: the three buffer sizes of step `XN`: 32 KiB, 1 MiB and 8 MiB. |
| 56 | `XN_PERMS = list(itertools.permutations(range(4)))` | `XN_PERMS`: all 24 orders of the numbers 0, 1, 2 and 3. A number stands for a kernel of `XN_KERNELS`. |
| 57 | `XF_CELLS = [("read", s) for s in ("1572864", "2M", "2621440", "3M", "5M", "6M", "12M", "24M", "32M", "64M")] + \` | `XF_CELLS`: the 15 cells of step `XF`. The first comprehension builds 10 cells of the kernel `read`, at 1.5, 2, 2.5, 3, 5, 6, 12, 24, 32 and 64 MiB. The sizes 1.5 MiB and 2.5 MiB are written in bytes: 1572864 and 2621440. The backslash joins the next line to this statement. |
| 58 | `           [("oldread", s) for s in ("2M", "3M", "6M", "12M", "32M")]` | The second comprehension adds 5 cells of the old read kernel `oldread`, at 2, 3, 6, 12 and 32 MiB. |
| 59 | `UNITS = 6` | `UNITS`: 6, the number of replicate sets per size and CPU in the step `XN`. |
| 60 | `size_bytes = schedule8.size_bytes` | Gives the function `size_bytes` of `schedule8.py` a short name in this file. It turns a size text into a number of bytes: a number with the letter `K`, `M` or `G` at its end is multiplied by 1024, by 1048576 or by 1073741824. A text without such a letter is a number of bytes. |

### Helper function `positions_balanced` (lines 63 to 70)

| Line | Source | Explanation |
|---:|---|---|
| 63 | `def positions_balanced(orders, n):` | Starts the function `positions_balanced`. `orders` is a list of orders of the items 0 to `n` minus 1. The function tests whether every item stands at every position about equally often. |
| 64 | `    """Every item 0..n-1 takes every position floor or ceil of len(orders)/n times."""` | Description text: every item takes every position a number of times that is the number of orders divided by `n`, rounded down or rounded up. |
| 65 | `    lo = len(orders) // n` | `lo`: the smallest allowed count: the number of orders divided by `n`, rounded down. For 6 orders of 4 items it is 1. |
| 66 | `    hi = lo + (1 if len(orders) % n else 0)` | `hi`: the largest allowed count. It is `lo` plus 1 when the division leaves a rest, and `lo` if not. For 6 orders of 4 items it is 2. |
| 67 | `    return all(lo <= sum(1 for o in orders if o[pos] == item) <= hi` | Returns true when the test holds for every item and every position: the number of orders that have the item at that position is at least `lo` and at most `hi`. The inner `sum` counts these orders. |
| 68 | `               for item in range(n) for pos in range(n))` | Continues the expression: the two loops over all items and all positions. |

### Class `Gen9`: `add9` and the step methods `XW`, `counted`, `XCA`, `XCB`, `XCC`, `XEV` (lines 71 to 126)

| Line | Source | Explanation |
|---:|---|---|
| 71 | `class Gen9(schedule8.Gen):` | Starts the class `Gen9`. It extends the class `Gen` of `schedule8.py` and takes the constructor and the helper methods from it. The constructor of `Gen` derives the seed of the step and session from the base seed and starts the random number generator `rng` with it. It sets the CPU order `cpus` of the session: 2 then 41 in session 1, 41 then 2 in session 2. It starts the empty list `procs`. |
| 72 | `    """Builds the processes of one round 2 step and session."""` | Description text of the class: it builds the processes of one step of round 2 in one session. |
| 74 | `    def add9(self, tag, cpu, size, keys, trials, extra=""):` | Starts the method `add9`. It appends one process to the list `procs`. `size` is a size text such as `8M`. `keys`: more pairs for the header of the plan. `extra`: options that are added to the command line of the process. |
| 75 | `        self.add(tag, cpu, size_bytes(size), keys, trials)` | Calls the method `add` of `Gen` with the size in bytes. `add` appends a dictionary with the tag, the CPU, the buffer size, the header pairs and the list of trials. |
| 76 | `        self.procs[-1]["extra"] = extra` | Stores the extra options in the dictionary of the process that line 75 appended. `procs[-1]` is the last entry of the list. |
| 78 | `    def XW(self):` | Starts the method `XW`. It builds the 28 processes of step `XW` for this session. |
| 79 | `        for r in (1, 2):` | Starts the loop over the two replicates, 1 and 2. |
| 80 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 81 | `                conds = list(XW_CONDS)` | A copy of the list of the 7 conditions for this replicate and CPU. |
| 82 | `                self.rng.shuffle(conds)` | Shuffles the copy. So each block of 7 processes has its own random order of the conditions. |
| 83 | `                for name, k, s, prev in conds:` | Starts the loop over the conditions in the shuffled order. `name` is the name of the condition, `k` the target kernel, `s` the target size and `prev` the previous activity or `None`. |
| 84 | `                    cond = "K=%s\|S=%s\|prev=%s" % (k, s, prev or "none")` | `cond`: the condition label of the trial. It names the kernel, the size and the previous activity, for example `K=read\|S=8M\|prev=oldread@8M`. Without a previous activity the last part is `prev=none`. |
| 85 | `                    t = [self.trial(cond, self.at(prev, 3000) if prev else "-", "-", "-",` | `t`: the one trial of the process. `trial` is a method of `Gen` that returns the fields of one plan line. Its second argument is the previous activity. With one, the method `at` of `Gen` builds the text `KERNEL@SIZE:3000`, that is 3000 ms of that kernel. `at` divides the 3000 by the test divisor. Without a previous activity the text is `-`. The two `-` that follow mean no prefix and no predecessor. |
| 86 | `                                    "%s@%s" % (k, s), 100, "closed")]` | Continues the call of line 85: the target `KERNEL@SIZE`, 100 target windows, and the counter mode `closed`. `trial` sets the window length to 300 ms, divided by the test divisor. So without a test divisor the target has 30000 ms of nominal kernel work, and a previous activity adds 3000 ms. |
| 87 | `                    self.add9("%s-cpu%d-p%d" % (name, cpu, r), cpu, s,` | Appends the process. Its tag holds the name of the condition, the CPU and the replicate, for example `W1-cpu2-p1`. The buffer size of the process is the target size `s`. |
| 88 | `                              [("rep_set", r), ("kernel", k), ("size", size_bytes(s)),` | The header pairs of the plan: the replicate, the kernel and the size in bytes. |
| 89 | `                               ("wcond", name), ("prev", prev or "none")], t)` | Continues the header pairs: the name of the condition under the key `wcond`, and the previous activity or `none` under the key `prev`. The last argument is the trial. |
| 91 | `    def counted(self, evset):` | Starts the method `counted`. It builds the 18 processes of one counter step for this session. `evset` is the letter of the event set: `A`, `B` or `C`. |
| 92 | `        extra = " --pmu-type %d --events %s" % (PMU_TYPE, EVENTS[evset])` | `extra`: the counter options for the command line: `--pmu-type 11`, and `--events` with the 6 events of the set. |
| 93 | `        short = {}` | `short`: for each CPU, the split of the three short cells into two groups. It is empty at first. |
| 94 | `        for cpu in self.cpus:` | Starts a loop over the two CPUs, in the order of the session. |
| 95 | `            # The three short processes of a CPU are drawn into its two replicate blocks: 2 and 1, or 1 and 2.` | Comment: the three short processes of a CPU are spread at random over its two replicate blocks. One block gets 2 of them and the other gets 1. |
| 96 | `            s = list(XC_SHORT)` | A copy of the list of the three short cells. |
| 97 | `            self.rng.shuffle(s)` | Shuffles the copy. |
| 98 | `            cut = self.rng.choice([1, 2])` | `cut`: 1 or 2, drawn at random. It is the number of short cells of the first block. |
| 99 | `            short[cpu] = [s[:cut], s[cut:]]` | Stores the two groups for this CPU: the first `cut` cells for block 1, and the rest for block 2. |
| 100 | `        for r in (1, 2):` | Starts the loop over the two replicates, 1 and 2. |
| 101 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 102 | `                items = [(k, s, 100) for k, s in XC_LONG] + [(k, s, 20) for k, s in short[cpu][r - 1]]` | `items`: the processes of this block: the three long cells with 100 windows each, and the short cells of this CPU and block with 20 windows each. So a block has 4 or 5 processes. |
| 103 | `                self.rng.shuffle(items)` | Shuffles the block. So each block has its own random order. |
| 104 | `                for k, s, nwin in items:` | Starts the loop over the processes of the block: the kernel, the size and the number of windows. |
| 105 | `                    cond = "K=%s\|S=%s\|count=read" % (k, s)` | `cond`: the condition label. It names the kernel, the size and the counter mode, for example `K=oldread\|S=8M\|count=read`. |
| 106 | `                    t = [self.trial(cond, "-", "-", "-", "%s@%s" % (k, s), nwin, "read")]` | `t`: the one trial of the process. It has no previous activity, no prefix and no predecessor. The target has `nwin` windows of 300 ms: 30000 ms for a long cell and 6000 ms for a short one. The counter mode is `read`: the runner reads the counters for each window. |
| 107 | `                    self.add9("%s-%s-cpu%d-p%d" % (k, s, cpu, r), cpu, s,` | Appends the process. Its tag holds the kernel, the size, the CPU and the block, for example `asmread-8M-cpu2-p1`. |
| 108 | `                              [("rep_set", r), ("kernel", k), ("size", size_bytes(s)), ("evset", evset)],` | The header pairs of the plan: the block, the kernel, the size in bytes, and the letter of the event set under the key `evset`. |
| 109 | `                              t, extra)` | The last arguments: the trial and the counter options. |
| 111 | `    def XCA(self):` | Starts the method `XCA`, the counter step with the event set A. |
| 112 | `        self.counted("A")` | Builds the step with `counted` and the event set A. |
| 114 | `    def XCB(self):` | Starts the method `XCB`, the counter step with the event set B. |
| 115 | `        self.counted("B")` | Builds the step with `counted` and the event set B. |
| 117 | `    def XCC(self):` | Starts the method `XCC`, the counter step with the event set C. |
| 118 | `        self.counted("C")` | Builds the step with `counted` and the event set C. |
| 120 | `    def XEV(self):` | Starts the method `XEV`. It builds the 3 processes of the acceptance step for the counter events. It does not use `rng`, so their order is fixed. |
| 121 | `        for evset in "ABC":` | Starts the loop over the three event sets, in the order A, B, C. |
| 122 | `            t = [self.trial("K=read\|S=8M\|count=read", "-", "-", "-", "read@8M", 3, "read")]` | `t`: the one trial of the process: the kernel `read` at 8 MiB, with no phase before the target, 3 target windows of 300 ms and the counter mode `read`. That is 900 ms of nominal kernel work. |
| 123 | `            self.add9("ev%s-cpu2" % evset, 2, "8M",` | Appends the process on CPU 2, with a buffer of 8 MiB. Its tag is `evA-cpu2`, `evB-cpu2` or `evC-cpu2`. The CPU is fixed here. It does not come from the CPU order of the session. |
| 124 | `                      [("kernel", "read"), ("size", size_bytes("8M")), ("evset", evset)], t,` | The header pairs of the plan (the kernel, the size in bytes and the letter of the event set), and the trial. |
| 125 | `                      " --pmu-type %d --events %s" % (PMU_TYPE, EVENTS[evset]))` | The counter options of the process: `--pmu-type 11`, and `--events` with the 6 events of the set. |

### `Gen9`: the methods `xn_orders`, `XN` and `XF` (lines 127 to 162)

| Line | Source | Explanation |
|---:|---|---|
| 127 | `    def xn_orders(self):` | Starts the method `xn_orders`. It returns 6 kernel orders for one size and CPU of step `XN`. |
| 128 | `        # A saved random selection of 6 of the 24 kernel orders, in which each kernel takes` | Comment: the method picks 6 of the 24 possible orders of the 4 kernels at random. The seed of the step fixes the selection, and the program writes that seed to `MANIFEST.txt` (line 247). The sentence ends in the next line. |
| 129 | `        # each position once or twice (6 sets over 4 positions cannot be more equal).` | Continues the comment: in the selection each kernel stands at each of the 4 positions once or twice. With 6 sets and 4 positions the counts cannot be more equal: 6 divided by 4 is 1.5. |
| 130 | `        while True:` | Starts a loop that repeats until a selection passes the test. |
| 131 | `            pick = self.rng.sample(XN_PERMS, UNITS)` | `pick`: 6 different orders, drawn at random from the 24 orders of `XN_PERMS`. `sample` draws without putting back, so no order is drawn twice. |
| 132 | `            if positions_balanced(pick, 4):` | Tests the selection with `positions_balanced` for 4 items. |
| 133 | `                return pick` | Returns the selection when it passes. If not, the loop draws a new one. So the number of draws from `rng` is not fixed. It depends on the seed. |
| 135 | `    def XN(self):` | Starts the method `XN`. It builds the 144 processes of step `XN` for this session. |
| 136 | `        # As S2 of schedule8.py: replicate set, then size (shuffled), then CPU, then the kernels.` | Comment: the order follows step `S2` of `schedule8.py`: the replicate set, then the size in a shuffled order, then the CPU, then the kernels. |
| 137 | `        order = {}` | `order`: one table of orders per size and CPU, empty at first. |
| 138 | `        for s in XN_SIZES:` | Starts a loop over the three sizes, in their fixed order. |
| 139 | `            for cpu in self.cpus:` | Starts a loop over the two CPUs, in the order of the session. |
| 140 | `                order[s, cpu] = self.xn_orders()` | Draws the 6 kernel orders of this size and CPU with `xn_orders`. So each size and CPU has its own random selection. |
| 141 | `        for r in range(UNITS):` | Starts the loop over the 6 replicate sets. `r` runs from 0 to 5. |
| 142 | `            sizes = list(XN_SIZES)` | A copy of the list of sizes for this set. |
| 143 | `            self.rng.shuffle(sizes)` | Shuffles the copy. So each replicate set has its own random order of the sizes. |
| 144 | `            for s in sizes:` | Starts the loop over the sizes in that order. |
| 145 | `                for cpu in self.cpus:` | Starts the loop over the CPUs in the order of the session. All processes of the first CPU at this size come before those of the second CPU. |
| 146 | `                    for ki in order[s, cpu][r]:` | Starts the loop over the kernels, in the order that row `r` of the table of this size and CPU gives. `ki` is the number of a kernel. |
| 147 | `                        k = XN_KERNELS[ki]` | `k`: the name of the kernel with that number. |
| 148 | `                        t = [self.same_kernel_trial("K=%s\|S=%s" % (k, s), "%s@%s" % (k, s))] * 4` | `t`: the 4 trials of the process, all equal. `same_kernel_trial` is a method of `Gen`: the trial has a prefix of 1200 ms of the target kernel itself and 4 target windows of 300 ms, with the counters closed. So one trial has 2400 ms and the process 9600 ms of nominal kernel work. The condition label names the kernel and the size, for example `K=read_nop16\|S=8M`. |
| 149 | `                        self.add9("r%d-%s-cpu%d-%s" % (r + 1, s, cpu, k), cpu, s,` | Appends the process. Its tag holds the replicate set (counted from 1), the size, the CPU and the kernel, for example `r1-8M-cpu2-asmread`. |
| 150 | `                                  [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s))], t)` | The header pairs of the plan (the replicate set, the kernel and the size in bytes), and the trials. |
| 152 | `    def XF(self):` | Starts the method `XF`. It builds the 90 processes of step `XF` for this session. |
| 153 | `        for r in (1, 2, 3):` | Starts the loop over the three replicates, 1 to 3. |
| 154 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 155 | `                cells = list(XF_CELLS)` | A copy of the list of the 15 cells for this replicate and CPU. |
| 156 | `                self.rng.shuffle(cells)` | Shuffles the copy. So each block of 15 processes has its own random order of the cells. |
| 157 | `                for k, s in cells:` | Starts the loop over the cells in the shuffled order: the kernel and the size. |
| 158 | `                    t = [self.same_kernel_trial("K=%s\|S=%s" % (k, s), "%s@%s" % (k, s))] * 4` | `t`: 4 equal trials of the same form as in line 148: a prefix of 1200 ms of the kernel itself and 4 target windows of 300 ms. That is 9600 ms of nominal kernel work per process. |
| 159 | `                    self.add9("r%d-%s-cpu%d-%s" % (r, s, cpu, k), cpu, s,` | Appends the process. Its tag holds the replicate, the size, the CPU and the kernel, for example `r1-12M-cpu2-oldread`. For the sizes 1.5 MiB and 2.5 MiB the tag holds the byte count, for example `r1-1572864-cpu2-read`. |
| 160 | `                              [("rep_set", r), ("kernel", k), ("size", size_bytes(s))], t)` | The header pairs of the plan (the replicate, the kernel and the size in bytes), and the trials. |

### Functions `generate` and `write` (lines 163 to 199)

| Line | Source | Explanation |
|---:|---|---|
| 163 | `def generate(base, div):` | Starts the function `generate`. It builds the processes of every step and session. |
| 164 | `    """Returns {(step, session): Gen9}. XEV only in session 1."""` | Description text: the function returns a dictionary from a pair of step and session to its `Gen9` object. The step `XEV` exists in session 1 only. |
| 165 | `    out = {}` | `out`: the result dictionary, empty at first. |
| 166 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 167 | `        for step in STEPS:` | Starts the loop over the steps, in the order of `STEPS`. |
| 168 | `            if step == "XEV" and session == 2:` | Tests for the acceptance step `XEV` in session 2. |
| 169 | `                continue` | Skips it. The acceptance step exists in session 1 only. |
| 170 | `            g = Gen9(step, session, base, div)` | `g`: a new `Gen9` object for this step and session. Its constructor derives the seed from the base seed, the step and the session, and starts the random number generator of the step. |
| 171 | `            getattr(g, step)()` | Calls the method of `g` whose name is the step name. That method fills `g.procs`. |
| 172 | `            out[step, session] = g` | Stores the object. |
| 173 | `    return out` | Returns the dictionary. |
| 176 | `def write(gens, out, manifest):` | Starts the function `write`. It writes all files into the folder `out`. `manifest` is the text of the file `MANIFEST.txt`. |
| 177 | `    os.makedirs(out, exist_ok=True)` | Creates the output folder when it does not exist. |
| 178 | `    for session in (1, 2):` | Starts a loop over the two sessions. |
| 179 | `        shutil.rmtree(os.path.join(out, "s%d" % session), ignore_errors=True)` | Removes the folder `s1` or `s2` with everything in it. A folder that does not exist gives no error. So no file of an older run stays in these folders. |
| 180 | `    for (step, session), g in gens.items():` | Starts the loop over all steps and sessions. |
| 181 | `        sdir = os.path.join(out, "s%d" % session)` | `sdir`: the folder of the session. |
| 182 | `        os.makedirs(os.path.join(sdir, step))` | Creates the folder for the plan files of the step, and the session folder with it. |
| 183 | `        rows = ["idx\ttag\tcpu\tbytes\tplan\targs"]` | `rows`: the rows of the schedule file. The first row holds the six column names, with tabs between them. |
| 184 | `        for idx, p in enumerate(g.procs):` | Starts the loop over the processes, in the order in which they will run. `idx` counts from 0. |
| 185 | `            name = "%04d.plan" % idx` | `name`: the name of the plan file: the `idx` with 4 digits and the ending `.plan`, for example `0017.plan`. |
| 186 | `            with open(os.path.join(sdir, step, name), "w") as f:` | Opens the plan file for writing. |
| 187 | `                f.write(schedule8.plan_text(g, idx, p))` | Writes the text of the plan, which the function `plan_text` of `schedule8.py` builds. The text has three header lines and then one line per trial. The second header line holds the pairs `step`, `session`, `cpu`, `bytes` and `proc`, then the header pairs of the process, then `seed` and `test`. |
| 188 | `            # The plan path is relative to the folder of run_bwx9.sh.` | Comment: the path of the plan in the `args` column is relative to the folder of the run script `run_bwx9.sh`. |
| 189 | `            args = "--trial --cpus %d --bytes %d --plan sched9/s%d/%s/%s%s" % (` | `args`: the options of the process for the runner: `--trial` (the mode that runs a plan), `--cpus` with the one worker CPU, `--bytes` with the buffer size, and `--plan` with the path `sched9/s<session>/<STEP>/<name>`. The folder name `sched9` is fixed here, also when `--out` names another folder. |
| 190 | `                p["cpu"], p["bytes"], session, step, name, p["extra"])` | The values for that text: the CPU, the size in bytes, the session, the step, the name of the plan file, and at the end the extra options of the process. |
| 191 | `            rows.append("%d\t%s\t%d\t%d\t%s\t%s" % (idx, p["tag"], p["cpu"], p["bytes"], name, args))` | Adds the schedule row of the process: its `idx`, its tag, its CPU, its size in bytes, the name of its plan file and its options, with tabs between them. |
| 192 | `        with open(os.path.join(sdir, step + ".tsv"), "w") as f:` | Opens the schedule file `<STEP>.tsv` of the step for writing. |
| 193 | `            f.write("\n".join(rows) + "\n")` | Writes all rows, each with a newline at its end. |
| 194 | `        if step in WATCH_STEPS:` | Tests whether the step runs with the host sampler. |
| 195 | `            open(os.path.join(sdir, step + ".watch"), "w").close()` | If so, creates the empty file `<STEP>.watch` in the session folder. The run script starts the host sampler for a step that has this file. |
| 196 | `    with open(os.path.join(out, "MANIFEST.txt"), "w") as f:` | Opens the file `MANIFEST.txt` in the output folder for writing. |
| 197 | `        f.write(manifest)` | Writes the manifest text. |

### Balance check `xn_orders_ok` (lines 200 to 212)

| Line | Source | Explanation |
|---:|---|---|
| 200 | `def xn_orders_ok(g):` | Starts the function `xn_orders_ok`, the balance check of step `XN`. It reads the kernel orders from the finished list of processes. |
| 201 | `    """Per size and CPU: 6 sets of 4 kernels, 6 different orders, positions balanced."""` | Description text: for each size and CPU there are 6 sets of 4 kernels, the 6 kernel orders differ, and the positions are balanced. |
| 202 | `    seen = {}` | `seen`: the collected orders, empty at first. |
| 203 | `    for p in g.procs:` | Starts the loop over the processes in schedule order. |
| 204 | `        k = dict(p["keys"])` | `k`: the header pairs of the process as a dictionary. |
| 205 | `        seen.setdefault((k["size"], p["cpu"]), {}).setdefault(k["rep_set"], []).append(` | Appends a value for this process to the list of its size, CPU and replicate set. The value stands in the next line. `setdefault` creates an entry that is missing. So `seen` maps each pair of size and CPU to a dictionary, which maps each replicate set to a list in schedule order. |
| 206 | `            XN_KERNELS.index(k["kernel"]))` | The value that is appended: the number of the kernel of the process, which is the place of the kernel in `XN_KERNELS`. |
| 207 | `    return len(seen) == len(XN_SIZES) * 2 and all(` | Starts the result. First condition: there are 6 pairs of size and CPU, 3 sizes times 2 CPUs. |
| 208 | `        len(sets) == UNITS and len({tuple(o) for o in sets.values()}) == UNITS` | Second condition, for every pair of size and CPU: it has 6 replicate sets, and their 6 kernel orders are all different. The set comprehension keeps each different order once. |
| 209 | `        and all(sorted(o) == [0, 1, 2, 3] for o in sets.values())` | Third condition: every order holds each of the 4 kernels exactly once. |
| 210 | `        and positions_balanced(list(sets.values()), 4) for sets in seen.values())` | Fourth condition: the 6 orders pass `positions_balanced`. So each kernel stands once or twice at each position. The loop at the end goes over all pairs of size and CPU. |

### Function `report`: counts, nominal kernel work and the balance line (lines 213 to 235)

| Line | Source | Explanation |
|---:|---|---|
| 213 | `def report(gens):` | Starts the function `report`. It builds the text that the program prints, and it runs the balance checks. |
| 214 | `    ok = True` | `ok`: stays true while every balance check passes. |
| 215 | `    lines = ["step session processes trials nominal_kernel_work_s"]` | `lines`: the lines of the report. The first one is the head of the table: step, session, number of processes, number of trials, and nominal kernel work in seconds. |
| 216 | `    total = [0, 0]` | `total`: two sums for session 1: the processes and the nominal work in ms. |
| 217 | `    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):` | Starts the loop over all steps and sessions, sorted by the session and then by the place of the step in `STEPS`. |
| 218 | `        n, tr = len(g.procs), sum(len(p["trials"]) for p in g.procs)` | `n`: the number of processes of the step. `tr`: the number of trials of all its processes. |
| 219 | `        ms = sum(map(schedule8.proc_ms, g.procs))` | `ms`: the nominal kernel work of the step in ms. The function `proc_ms` of `schedule8.py` gives the work of one process: over all its trials, the sum of the previous activity, the prefix, the predecessor and the number of windows times the window length. |
| 220 | `        lines.append("%s %d %d %d %g" % (step, session, n, tr, ms / 1000))` | Adds the table row of the step: its name, the session, `n`, `tr` and the nominal work in seconds. `%g` prints a number with at most 6 significant digits and without zeros at its end. |
| 221 | `        if session == 1:` | Only the steps of session 1 go into the totals. |
| 222 | `            total[0] += n` | Adds the processes of the step. |
| 223 | `            total[1] += ms` | Adds the nominal work of the step. |
| 224 | `    lines.append("session 1 total: %d processes, nominal kernel work %g s (%g min)"` | Adds the total line of session 1 to the report. |
| 225 | `                 % (total[0], total[1] / 1000, round(total[1] / 60000, 2)))` | The values of that line: the number of processes, the nominal work in seconds, and the nominal work in minutes, rounded to two decimal places. |
| 226 | `    lines.append("balance:")` | Adds the heading of the balance part. |
| 227 | `    for (step, session), g in sorted(gens.items()):` | Starts a second loop over all steps and sessions, sorted by the step name and then by the session. |
| 228 | `        if step == "XN":` | The check of step `XN`. No other step has a balance check. |
| 229 | `            a = xn_orders_ok(g)` | `a`: the result of `xn_orders_ok`. |
| 230 | `            ok = ok and a` | `ok` becomes false when the check failed. |
| 231 | `            lines.append("XN session %d: per size and CPU 6 different kernel orders, each kernel "` | Adds the sentence of the report for this check. It says that per size and CPU there are 6 different kernel orders. |
| 232 | `                         "once or twice at each position: %s" % (session, "yes" if a else "NO"))` | Ends the sentence: and each kernel stands once or twice at each position. The line ends with `yes` when the check passed, and with `NO` when it failed. |
| 233 | `    return "\n".join(lines) + "\n", ok` | Returns the report text and the result of all checks. |

### Function `main` (lines 236 to 256)

| Line | Source | Explanation |
|---:|---|---|
| 236 | `def main():` | Starts the function `main`. |
| 237 | `    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])` | Creates the reader of the command line. Its description is the first line of the description text of the file. |
| 238 | `    ap.add_argument("--seed", type=int, default=20261115, help="base seed")` | The option `--seed`: the base seed, a whole number. It is 20261115 when the option is not given. |
| 239 | `    ap.add_argument("--test-divisor", type=int, default=1)` | The option `--test-divisor`: the number by which every duration is divided. It is 1 when the option is not given, which changes nothing. |
| 240 | `    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sched9"))` | The option `--out`: the output folder. When it is not given, it is the folder `sched9` in the folder of this file. |
| 241 | `    a = ap.parse_args()` | Reads the command line. |
| 242 | `    if a.test_divisor < 1 or 300 % a.test_divisor:` | Tests the divisor: it must be at least 1, and 300 divided by it must leave no rest. 300 ms is the length of a window. |
| 243 | `        sys.exit("--test-divisor must divide 300 ms")` | If not, `sys.exit` with a text prints `--test-divisor must divide 300 ms` to the error output and ends the program with exit status 1. |
| 244 | `    gens = generate(a.seed, a.test_divisor)` | Builds the processes of all steps and sessions. |
| 245 | `    text, ok = report(gens)` | Builds the report text and runs the balance checks. |
| 246 | `    manifest = "base_seed=%d\ntest_divisor=%d\n" % (a.seed, a.test_divisor)` | `manifest`: the text of `MANIFEST.txt`. Its first two lines give the base seed and the test divisor. |
| 247 | `    manifest += "".join("seed %s s%d %d\n" % (step, session, g.seed)` | Adds one line per step and session to the manifest: the word `seed`, the step, the session as `s1` or `s2`, and the seed of that step and session. |
| 248 | `                        for (step, session), g in gens.items())` | Continues the expression: the loop over all steps and sessions, in the order in which they were built. |
| 249 | `    write(gens, a.out, manifest)` | Writes all files. This happens before the result of the balance checks is used. |
| 250 | `    print("written: %s" % a.out)` | Prints the output folder. |
| 251 | `    sys.stdout.write(text)` | Prints the report. |
| 252 | `    sys.exit(0 if ok else 1)` | Ends the program with exit status 0 when every balance check passed, and with 1 when one failed. The files are written in both cases. |
| 255 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 256 | `    main()` | Runs `main`. |
