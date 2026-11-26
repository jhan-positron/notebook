# `schedule11.py` explained, line by line

- Source file: `bwx11-2026-11-15/schedule11.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 376 lines, 18975 bytes).
- sha256 of the source when this page was built: `c04a79f5f7aba65091124d69119a8d550b6b687d39b89b7dfe786f1ea1fb2387`.

## Short version: purpose

`schedule11.py` writes the input files of round 4 for the run script `run_bwx11.sh`: for each step and session one schedule file with one row per process, one plan file per process, and one file that names the runner binary. It fixes the order of the processes with a random number generator whose seed depends only on the base seed, the step and the session. It also checks that the orders are balanced, and it prints the counts and the nominal kernel work.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 4**: the fourth set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Z`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`read_nop64`, `read_nop96`, `read_nop128`**: three slow load-only kernels of the runner `bwx11`. Each is the `asmread` loop with 64, 96 or 128 added `nop` instructions.
- **Process**: one start of a benchmark binary.
- **Run script**: the script `run_bwx11.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Step**: one batch of processes of a round, for example `ZD`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Prefix**: a phase before the target that prepares the core. In round 4 it runs the target kernel itself.
- **Target, window**: the target is the kernel that a trial measures. A window is one timed period of it.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Cell**: one combination of the factors of a step, for example one kernel with one evict condition.
- **Replicate set, replicate**: one run of every cell of a step for one size and CPU (`ZD`, `ZN`), or one pass through all cells on both CPUs (`ZC`, `ZM`).
- **Block**: the processes of one replicate on one CPU in `ZC` and `ZM`. Each block holds every cell once.
- **Williams square**: a set of n orders of n items in which every item stands once at every position, and every ordered pair of different items stands once as direct neighbours.
- **Base seed, seed**: the base seed is the one number that the caller can set with `--seed`. The seed of a step and session is derived from it.
- **Test divisor**: a number by which every duration is divided, for local tests only.
- **Evict step, `E0`, `E512`**: with the option `--evict-mb 512` the runner writes another buffer of 512 MiB twice before the first trial. The aim is that the test buffer leaves the caches. `E512` is the condition with that option, and `E0` the condition without it.
- **`--rec-pad P`**: an option of the runner. It puts P unused bytes before the records in which the runner stores the times of its windows.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters for each window.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Host sampler**: the program `hostwatch.py`. The run script starts it beside a process when the step has a `.watch` file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Read the options `--seed`, `--test-divisor` and `--out`. End with exit status 1 when the divisor does not divide 100 ms (lines 356 to 362).
2. Build the processes of every step and session with one `Gen` object each. Each object derives its own seed with `step_seed` and starts its own random number generator (line 363, lines 217 to 227, lines 107 to 112).
3. Each step method fills the list of processes in run order: `ZD` (lines 149 to 165), `ZC` (lines 167 to 178), `ZN` (lines 180 to 195), `ZM` (lines 197 to 207) and `ZA` (lines 209 to 214).
4. Build the report text: per step and session the number of processes and trials and the nominal kernel work, then the totals per session, then the result of each balance check (line 364, lines 310 to 352).
5. Build the text of `MANIFEST.txt`: the base seed, the test divisor, and the seed and the binary of every step and session (lines 365 to 368).
6. Remove the folders `s1` and `s2` of the output folder and write the plan files, the schedule files, the `.bin` files and `MANIFEST.txt` (line 369, lines 253 to 274).
7. Print the output folder and the report. End with exit status 0, or with 1 when a balance check failed (lines 370 to 372).

## Behavior a reader must know

- The seed of a step and session is the first 8 hexadecimal digits of the sha256 of the text `BASE/STEP/SESSION`, read as a whole number (lines 84 to 86). The base seed is 20261115 unless `--seed` gives another one (line 357).
- Each step and session has its own generator `random.Random(seed)` (line 110). All shuffles of a step use it, in a fixed sequence. So the same options always give the same files, and session 2 has random orders of its own.
- How the order of `ZD` is made (lines 149 to 165):
  - First one Williams square of the 6 cells is built for each size and CPU: 3 sizes in a fixed order, and inside a size the 2 CPUs in the order of the session. Each square takes two shuffles: the labels of the cells and the order of its 6 rows (line 136, line 138).
  - Then, for each of the 6 replicate sets, the 3 sizes are shuffled once (line 156).
  - The run order is: replicate set, then size, then CPU, then the 6 cells in the order of row `r` of the square of that size and CPU.
  - Balanced: per size and CPU each cell stands once at each of the 6 positions, and each ordered pair of cells runs once as direct neighbours.
- How the order of `ZN` is made (lines 180 to 195): the same nesting as in `ZD`. In place of a Williams square, each size and CPU gets the 6 possible orders of the 3 kernels, with the rows shuffled once (line 145). Balanced: per size and CPU each kernel stands twice at each position, and each ordered pair of kernels runs twice as direct neighbours.
- How the order of `ZC` and `ZM` is made (lines 167 to 178, lines 197 to 207): the run order is replicate 1 and then 2, inside a replicate the 2 CPUs in the order of the session, and inside a CPU all cells in a newly shuffled order (8 cells in `ZC`, 10 pads in `ZM`). Balanced: each block holds every cell once. The positions inside a block are random and not balanced.
- `ZA` has a fixed order on CPU 2 and uses no random number (lines 209 to 214).
- Not random: the order of the two CPUs. Session 1 always runs CPU 2 before CPU 41, and session 2 runs CPU 41 before CPU 2 (line 52).
- The size order inside a replicate set of `ZD` and `ZN` is shuffled but not balanced.
- The program checks the balance on the finished list of processes (lines 277 to 307). A failed check gives a line that ends with `NO` and exit status 1. The files are written before the exit status is set (lines 369 to 372).
- The folders `s1` and `s2` of the output folder are removed before the new files are written (line 256).
- The plan path in the `args` column always starts with `sched11/`, also when `--out` names another folder (line 266).
- The nominal kernel work counts planned durations only (line 250). The evict step of a process is not in it.
- With `--test-divisor N` every duration is divided by N and the plans get `test=1`. The numbers of windows and the order of the processes do not change.
- The program reads no input file and starts nothing on CRB.

## Source and explanation, line by line

- Text shown: the file `bwx11-2026-11-15/schedule11.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (376 lines, 18975 bytes, sha256 `c04a79f5f7aba65091124d69119a8d550b6b687d39b89b7dfe786f1ea1fb2387`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text: files written, options, evict condition, the five steps (lines 1 to 41)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""schedule11.py - schedules and plan files of round 4 (steps ZA ZD ZC ZN ZM).` | Starts the description text of the file. First line: the name and the purpose. The program writes the schedules and the plan files of round 4, for the steps `ZA`, `ZD`, `ZC`, `ZN` and `ZM`. `main` uses this line as the description in the help text. |
| 4 | `Usage: schedule11.py [--seed N] [--test-divisor N] [--out DIR]` | Text of the description: the usage. The three options are optional: the base seed, the test divisor and the output folder. |
| 6 | `It writes, for session 1 and 2 and for each step:` | Text of the description: the list of the files that the program writes for session 1, for session 2 and for each step. |
| 7 | `  DIR/s<session>/<STEP>.tsv        one row per process (idx, tag, cpu, bytes, plan, args)` | Text of the description: the schedule file of a step. It has one row per process, with the columns `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`. |
| 8 | `  DIR/s<session>/<STEP>/NNNN.plan  one plan file per process (plan format v1 of bwx8, bwx10 and bwx11)` | Text of the description: one plan file per process, in a folder with the name of the step. The plan format is version 1, which the runners `bwx8`, `bwx10` and `bwx11` read. |
| 9 | `  DIR/s<session>/<STEP>.bin        one word: the binary that run_bwx11.sh starts for the step (bwx11 for every step)` | Text of the description: the `.bin` file of a step. It holds one word, the name of the binary that the run script `run_bwx11.sh` starts for the step. The word is `bwx11` for every step. |
| 10 | `  DIR/MANIFEST.txt                 base seed, test divisor, the seed and the binary of each step and session` | Text of the description: the file `MANIFEST.txt`. It records the base seed, the test divisor, and the seed and the binary of each step and session. |
| 11 | `DIR is "sched11" beside this file by default. The folders DIR/s1 and DIR/s2 are replaced.` | Text of the description: the output folder is `sched11` in the folder of this file, unless `--out` names another one. The program removes the folders `s1` and `s2` in it and writes them new. |
| 12 | `No step of round 4 runs with the host sampler, so no .watch file is written.` | Text of the description: no step of round 4 runs with the host sampler. So the program writes no `.watch` file. Such a file tells the run script to start the program `hostwatch.py` beside each process of the step. |
| 13 | `The step ZA exists in session 1 only.` | Text of the description: the step `ZA` exists in session 1 only. |
| 14 | `--test-divisor N divides every duration by N and marks the plans test=1 (local chain tests only).` | Text of the description: `--test-divisor N` divides every duration by N and writes `test=1` into the plans. It is only for local tests of the whole chain of scripts. |
| 15 | `N must divide 100 ms, the shortest window of round 4.` | Text of the description: N must divide 100 ms without a rest. 100 ms is the shortest window of round 4. |
| 16 | `The same options give the same bytes. Exit status 1 if a balance check fails.` | Text of the description: two runs with the same options write the same bytes. The exit status is 1 when a balance check fails. |
| 17 | `This file needs no file of an earlier round: the parts taken from schedule10.py are copied here.` | Text of the description: the program needs no file of an earlier round. The parts that come from `schedule10.py`, the generator of round 3, are copied into this file. |
| 19 | `"--evict-mb 512" (condition E512) is an option of bwx11: after first touch the worker writes another buffer` | Text of the description: the condition `E512`. A process of this condition runs with the option `--evict-mb 512` of the runner `bwx11`. After the first touch the worker thread writes another buffer. |
| 20 | `of 512 MiB twice and unmaps it, so that the lines of the test buffer leave all caches and come back from memory clean.` | Continues the text: that buffer has 512 MiB. The worker writes it twice and gives it back to Linux. The aim: the cache lines of the test buffer leave all caches, and the next read brings them back from memory in a clean state. A clean line is one that was not written after it was loaded. |
| 21 | `Condition E0 has no option. The evict step is real time that is not kernel work (est. 0.3 to 1 s per process).` | Continues the text: the condition `E0` adds no option. The evict step takes real time that is not kernel work, est. 0.3 to 1 s per process. |
| 22 | `It is not part of the nominal kernel work that this file and run_bwx11.sh print.` | Continues the text: that time is not part of the nominal kernel work that this program and `run_bwx11.sh` print. |
| 24 | `Steps (binary bwx11; CPUs 2 and 41; session 2 uses the reversed CPU order; one process at a time):` | Text of the description: the heading of the list of steps. All steps use the binary `bwx11` and the CPUs 2 and 41. Session 2 uses the two CPUs in the reverse order. One process runs at a time. |
| 25 | `  ZD   clean lines: trials as step S2 of schedule8.py (4 trials per process: prefix K@S 1200 ms, target K@S` | Step `ZD`, the test of clean lines. Its trials have the form of step `S2` of the older generator `schedule8.py`: 4 trials per process, each with a prefix of 1200 ms of the kernel K at the size S. |
| 26 | `       4 x 300 ms). Kernels asmread, read, oldread; sizes 4M, 8M, 16M; conditions E0 and E512. The 6 cells` | Continues the text on `ZD`: the target of a trial is the same kernel at the same size, in 4 windows of 300 ms. The kernels are `asmread`, `read` and `oldread`. The sizes are 4, 8 and 16 MiB. The conditions are `E0` and `E512`. |
| 27 | `       (kernel, condition) run in 6 replicate sets per size and CPU.` | Continues the text on `ZD`: a cell is one pair of a kernel and a condition. The 6 cells run in 6 replicate sets per size and CPU. A replicate set is one run of every cell. |
| 28 | `       Order: replicate set, then size (shuffled), then CPU, then the 6 cells. Per size and CPU the cell` | Continues the text on `ZD`: the order of the processes. The outer level is the replicate set, then the size in a shuffled order, then the CPU, then the 6 cells. |
| 29 | `       orders of the 6 sets form a Williams square (defined at williams_square below).` | Continues the text on `ZD`: for each size and CPU, the cell orders of the 6 sets form a Williams square. The method `williams_square` defines it (lines 125 to 139). |
| 30 | `  ZC   clean lines, counters: one trial, 20 windows of 300 ms, count read, the event set in the args column.` | Step `ZC`, clean lines with counters: one trial per process with 20 windows of 300 ms. The counter mode is `read`: the runner reads the counters for each window. The list of counter events stands in the `args` column. |
| 31 | `       Kernels asmread, oldread; sizes 8M, 16M; conditions E0 and E512; 2 processes per cell and CPU.` | Continues the text on `ZC`: the kernels `asmread` and `oldread`, the sizes 8 and 16 MiB, the conditions `E0` and `E512`. Each cell runs 2 processes per CPU. |
| 32 | `       Order: replicate, then CPU, then the 8 cells shuffled.` | Continues the text on `ZC`: the order is the replicate, then the CPU, then the 8 cells in a shuffled order. |
| 33 | `  ZN   slow load-only kernels: trials as S2. Kernels read_nop64, read_nop96, read_nop128; sizes 32K, 1M, 8M,` | Step `ZN`, the slow load-only kernels: trials of the same form as in `ZD`. The kernels are `read_nop64`, `read_nop96` and `read_nop128`. Each is the `asmread` loop with 64, 96 or 128 added `nop` instructions. A `nop` does nothing. |
| 34 | `       16M; 6 replicate sets per size and CPU. Order: replicate set, then size (shuffled), then CPU, then the` | Continues the text on `ZN`: the sizes are 32 KiB, 1 MiB, 8 MiB and 16 MiB, with 6 replicate sets per size and CPU. The order is the replicate set, then the size in a shuffled order, then the CPU, then the kernels. |
| 35 | `       3 kernels. Per size and CPU the 6 sets use the 6 possible orders of 3 kernels once each: every kernel` | Continues the text on `ZN`: for each size and CPU, the 6 sets use the 6 possible orders of the 3 kernels, each order once. |
| 36 | `       is twice at every position, and every ordered pair of kernels is twice a pair of neighbours.` | Continues the text on `ZN`: so every kernel stands twice at every position, and every ordered pair of kernels runs twice as direct neighbours. |
| 37 | `  ZM   kick map: asmread at 8M, one trial of 300 windows of 100 ms, count closed, "--rec-pad P" with` | Step `ZM`, the kick map: `asmread` at 8 MiB, one trial of 300 windows of 100 ms, without counters. Each process gets the option `--rec-pad P`. The option puts P unused bytes before the window records of the runner, so the records move by P bytes. The notes of the project use the word kick for a change of the read rate at an access to such a record. |
| 38 | `       P = 0, 8, 16, 24, 32, 40, 48, 56, 64, 72. 2 processes per pad and CPU.` | Continues the text on `ZM`: P is one of 10 values from 0 to 72 bytes, in steps of 8 bytes. Each pad runs 2 processes per CPU. |
| 39 | `       Order: replicate, then CPU, then the 10 pads shuffled.` | Continues the text on `ZM`: the order is the replicate, then the CPU, then the 10 pads in a shuffled order. |
| 40 | `  ZA   acceptance of bwx11: CPU 2 only, 6 short processes with --trace, in a fixed order.` | Step `ZA`, the acceptance of the runner `bwx11`: 6 short processes on CPU 2 only, with the option `--trace`, in a fixed order. With `--trace` the runner prints a log of the events around its timed parts. The rates of such a run are not used. |
| 41 | `"""` | Ends the description text. |

### Imports and constants (lines 42 to 76)

| Line | Source | Explanation |
|---:|---|---|
| 42 | `import argparse` | Loads the Python module `argparse`, which reads the command line options. |
| 43 | `import hashlib` | Loads `hashlib`: the sha256 function, used to derive the seeds. |
| 44 | `import itertools` | Loads `itertools`: used to list all orders of a set of items. |
| 45 | `import os` | Loads `os`: paths and folders. |
| 46 | `import random` | Loads `random`: the random number generator that shuffles the orders. |
| 47 | `import shutil` | Loads `shutil`: used to remove a folder tree. |
| 48 | `import sys` | Loads `sys`: the standard output and the exit status. |
| 50 | `STEPS = ["ZA", "ZD", "ZC", "ZN", "ZM"]` | `STEPS`: the names of the 5 steps, in the order in which the program builds and reports them. |
| 51 | `BINARY = {"ZA": "bwx11", "ZD": "bwx11", "ZC": "bwx11", "ZN": "bwx11", "ZM": "bwx11"}` | `BINARY`: the word of the binary of each step. It is `bwx11` for all 5 steps. The word goes into the `.bin` file of the step. |
| 52 | `CPUS = {1: [2, 41], 2: [41, 2]}                    # session 2 uses the reversed order` | `CPUS`: the two worker CPUs in the order of each session. Session 1 uses CPU 2 first and then CPU 41. Session 2 uses CPU 41 first. |
| 53 | `PMU_TYPE = 11                                      # armv8_pmuv3_0 on CRB (DECISIONS-bwx8.md)` | `PMU_TYPE`: 11, the type number that Linux gives to the counter device `armv8_pmuv3_0` of the cores on CRB. By the comment the value comes from the notes file `DECISIONS-bwx8.md`. It goes into the option `--pmu-type` of the processes that use counters. |
| 54 | `ZC_EVENTS = ("cpu_cycles=0x11,l1d_cache_lmiss_rd=0x39,l2d_cache_refill=0x17,l2d_cache_wb=0x18,"` | `ZC_EVENTS`: the counter events of step `ZC`, each as a name and an event code. This line holds four: the cycles of the core (`cpu_cycles`), long misses of loads in the first-level cache (`l1d_cache_lmiss_rd`), refills of the L2 cache (`l2d_cache_refill`) and write-backs from the L2 cache (`l2d_cache_wb`). |
| 55 | `             "bus_access=0x19,l2d_cache_lmiss_rd=0x4009")` | Continues the text of line 54 with two more events: bus accesses (`bus_access`) and long misses of loads in the L2 cache (`l2d_cache_lmiss_rd`). The 6 events go into the option `--events`. |
| 56 | `EVICT_MB = 512` | `EVICT_MB`: 512, the size in MiB of the buffer that the evict step writes. |
| 57 | `# name, megabytes of the evict buffer (0: no option), the options added to the command line` | Comment: each entry of the list in line 58 holds a name, the size of the evict buffer in MiB (0 means no evict step), and the option text that is added to the command line. |
| 58 | `ECONDS = [("E0", 0, ""), ("E%d" % EVICT_MB, EVICT_MB, " --evict-mb %d" % EVICT_MB)]` | `ECONDS`: the two evict conditions. `E0`: no evict step and no option. `E512`: an evict buffer of 512 MiB and the option `--evict-mb 512`. |
| 59 | `ZD_KERNELS = ["asmread", "read", "oldread"]` | `ZD_KERNELS`: the three kernels of step `ZD`: the hand-written load-only loop `asmread`, the new read kernel `read` and the old read kernel `oldread`. |
| 60 | `ZD_SIZES = ["4M", "8M", "16M"]` | `ZD_SIZES`: the three buffer sizes of step `ZD`: 4, 8 and 16 MiB. |
| 61 | `ZD_CELLS = [(k, e) for k in ZD_KERNELS for e in ECONDS]` | `ZD_CELLS`: the 6 cells of step `ZD`. The comprehension builds one pair for each of the 3 kernels and each of the 2 evict conditions, with the kernel as the outer loop. |
| 62 | `ZC_KERNELS = ["asmread", "oldread"]` | `ZC_KERNELS`: the two kernels of step `ZC`. |
| 63 | `ZC_SIZES = ["8M", "16M"]` | `ZC_SIZES`: the two buffer sizes of step `ZC`: 8 and 16 MiB. |
| 64 | `ZN_KERNELS = ["read_nop64", "read_nop96", "read_nop128"]` | `ZN_KERNELS`: the three slow load-only kernels of step `ZN`. |
| 65 | `ZN_SIZES = ["32K", "1M", "8M", "16M"]` | `ZN_SIZES`: the four buffer sizes of step `ZN`: 32 KiB, 1 MiB, 8 MiB and 16 MiB. |
| 66 | `ZM_PADS = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72]` | `ZM_PADS`: the 10 values of `--rec-pad` in step `ZM`, in bytes. |
| 67 | `# name, kernel, size, megabytes of the evict buffer, the options added after --trace` | Comment: each entry of `ZA_PROCS` holds a name, a kernel, a buffer size, the size of the evict buffer in MiB, and the options that follow `--trace`. |
| 68 | `ZA_PROCS = [("plain", "asmread", "8M", 0, ""), ("evict", "asmread", "8M", EVICT_MB, " --evict-mb %d" % EVICT_MB),` | `ZA_PROCS`: the 6 processes of the acceptance step `ZA`, all at 8 MiB. This line holds two: `plain` (`asmread` without an option) and `evict` (`asmread` with `--evict-mb 512`). |
| 69 | `            ("oldevict", "oldread", "8M", EVICT_MB, " --evict-mb %d" % EVICT_MB),` | Continues the list: `oldevict`, the old read kernel with `--evict-mb 512`. |
| 70 | `            ("nop64", "read_nop64", "8M", 0, ""), ("nop96", "read_nop96", "8M", 0, ""),` | Continues the list: `nop64` and `nop96`, two of the slow kernels, without an option. |
| 71 | `            ("nop128", "read_nop128", "8M", 0, "")]` | Ends the list with `nop128`, the third slow kernel. |
| 72 | `UNITS = 6                                          # replicate sets per size and CPU in ZD and ZN` | `UNITS`: 6, the number of replicate sets per size and CPU in the steps `ZD` and `ZN`. |
| 73 | `MIN_WIN_MS = 100                                   # the shortest window of round 4` | `MIN_WIN_MS`: 100 ms, the shortest window of round 4. The test divisor must divide it (line 361). |
| 74 | `EVICT_EST_S = (0.3, 1.0)                           # est. real time of the evict step of one process, in seconds` | `EVICT_EST_S`: the estimated real time of the evict step of one process: 0.3 s to 1.0 s (est.). Only the report text uses it. |

### Helper functions: `size_bytes`, `step_seed`, `williams_ok`, `all_orders_ok` (lines 77 to 103)

| Line | Source | Explanation |
|---:|---|---|
| 77 | `def size_bytes(tok):` | Starts the function `size_bytes`. It converts a size text such as `8M` to a number of bytes. |
| 78 | `    mult = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}` | `mult`: the factor of each unit letter: `K` is 1024, `M` is 1048576 (1 MiB) and `G` is 1073741824. |
| 79 | `    if tok and tok[-1] in mult:` | Tests whether the text is not empty and ends with one of the three letters. |
| 80 | `        return int(tok[:-1]) * mult[tok[-1]]` | If so: returns the number before the letter times the factor. `8M` gives 8388608. |
| 81 | `    return int(tok)` | If not: the text is a plain number of bytes. |
| 84 | `def step_seed(base, step, session):` | Starts the function `step_seed`. It derives the random seed of one step and session from the base seed. |
| 85 | `    h = hashlib.sha256(("%d/%s/%d" % (base, step, session)).encode()).hexdigest()` | `h`: the sha256 of a short text, written as 64 hexadecimal digits. The text is the base seed, the step name and the session number, with a slash between them. |
| 86 | `    return int(h[:8], 16)` | Returns the first 8 hexadecimal digits as a whole number, a value from 0 to 4294967295. So each step and session gets its own seed, and one base seed always gives the same seeds. |
| 89 | `def williams_ok(orders, n):` | Starts the function `williams_ok`. It tests whether a list of orders is a Williams square of `n` items. |
| 90 | `    """orders: n orders of the items 0..n-1. True if every item is once at every position and` | Description text: `orders` holds `n` orders of the items 0 to `n - 1`. The result is true when every item stands once at every position. |
| 91 | `    every ordered pair of different items is once a pair of neighbours."""` | Continues the text: and when every ordered pair of different items stands once as direct neighbours. In an ordered pair (a, b), b follows directly after a. |
| 92 | `    pos = {(o[i], i) for o in orders for i in range(n)}` | `pos`: the set of all pairs of an item and its position, over all orders. |
| 93 | `    pairs = [(o[i], o[i + 1]) for o in orders for i in range(n - 1)]` | `pairs`: the list of all pairs of direct neighbours, over all orders: an item and the item after it. |
| 94 | `    return (len(orders) == n and all(sorted(o) == list(range(n)) for o in orders)` | Starts the result. The first two conditions: there are exactly `n` orders, and each order holds every item from 0 to `n - 1` exactly once. |
| 95 | `            and len(pos) == n * n and len(set(pairs)) == len(pairs) == n * (n - 1))` | The last two conditions. The set `pos` has `n * n` members, so every item stands at every position. The list `pairs` has `n * (n - 1)` entries and no entry twice, so every ordered pair of different items is a pair of neighbours exactly once. |
| 98 | `def all_orders_ok(orders, n):` | Starts the function `all_orders_ok`. It tests whether a list of orders holds every possible order of `n` items exactly once. |
| 99 | `    """orders: the orders of the items 0..n-1 of the replicate sets. True if they are all n! possible` | Description text: `orders` holds the orders of the items 0 to `n - 1` of the replicate sets. The result is true when they are all possible orders. `n` items have `n!` orders, which is 6 for 3 items. |
| 100 | `    orders, each one once."""` | Continues the text: each order must stand once. |
| 101 | `    return sorted(tuple(o) for o in orders) == sorted(itertools.permutations(range(n)))` | Compares the sorted list of the given orders with the sorted list of all orders that `itertools.permutations` builds. The two are equal only when every possible order is there exactly once. |

### Class `Gen`: constructor, `ms`, `trial`, `add`, `williams_square`, `all_orders` (lines 104 to 147)

| Line | Source | Explanation |
|---:|---|---|
| 104 | `class Gen:` | Starts the class `Gen`. One object builds the list of the processes of one step in one session. |
| 105 | `    """Builds the processes of one round 4 step and session."""` | Description text of the class: it builds the processes of one step of round 4 in one session. |
| 107 | `    def __init__(self, step, session, base, div):` | Starts the constructor. `base` is the base seed, and `div` is the test divisor. |
| 108 | `        self.step, self.session, self.div = step, session, div` | Stores the step, the session and the divisor. |
| 109 | `        self.seed = step_seed(base, step, session)` | `seed`: the seed of this step and session, derived from the base seed by `step_seed`. |
| 110 | `        self.rng = random.Random(self.seed)` | `rng`: a random number generator of its own for this step and session, started with that seed. Every shuffle of the step uses it. So the order of the processes depends only on the base seed, the step and the session. |
| 111 | `        self.cpus = CPUS[session]` | `cpus`: the two CPUs in the order of this session. |
| 112 | `        self.procs = []` | `procs`: the list of the processes of the step, in the order in which they will run. It is empty at first. |
| 114 | `    def ms(self, v):` | Starts the method `ms`. It scales a duration in ms by the test divisor. |
| 115 | `        return v // self.div` | Returns the duration divided by the divisor, as a whole number. With the divisor 1 the duration stays as it is. |
| 117 | `    def trial(self, cond, pfx, tgt, nwin, win_ms, count="closed", bins=0):` | Starts the method `trial`. It builds one trial of a plan. `cond`: the condition label. `pfx`: the duration of the prefix in ms, or `None`. `tgt`: the target in the form `KERNEL@SIZE`. `nwin` and `win_ms`: the number and the length of the target windows. `count`: the counter mode, `closed` unless given. `bins`: 0 unless given. |
| 118 | `        # (cond, prev, pfx, pred, tgt, nwin, win_ms, count, bins); pfx: None or the ms of a prefix of the target.` | Comment: the result is a tuple of 9 values in the order of the plan columns. `pfx` is `None`, or the ms of a prefix that runs the target kernel itself. |
| 119 | `        return (cond, "-", "%s:%d" % (tgt, self.ms(pfx)) if pfx else "-", "-", tgt, nwin, self.ms(win_ms), count, bins)` | Returns the tuple. The previous activity and the predecessor are always `-`, the mark for none. The prefix is `-`, or the target followed by a colon and its scaled duration. The window length is scaled too. The number of windows is not scaled. |
| 121 | `    def add(self, tag, cpu, size, keys, trials, extra="", evict=0):` | Starts the method `add`. It appends one process to the list. `keys`: more pairs for the header of the plan. `extra`: options that are added to the command line. `evict`: the size of the evict buffer in MiB, 0 for none. |
| 122 | `        self.procs.append({"tag": tag, "cpu": cpu, "bytes": size_bytes(size), "keys": keys,` | Appends a dictionary with the tag, the CPU, the buffer size in bytes and the header pairs. |
| 123 | `                           "trials": trials, "extra": extra, "evict": evict})` | Continues the dictionary: the list of trials, the extra options and the size of the evict buffer. |
| 125 | `    def williams_square(self, n):` | Starts the method `williams_square`. It returns `n` orders of `n` items that form a Williams square. The random choices come from `rng`. |
| 126 | `        # A Williams square for an even n: n orders of n items in which every item takes every position` | Comment: a Williams square for an even `n` holds `n` orders of `n` items. Every item takes every position once. |
| 127 | `        # once, and every ordered pair of different items is once a pair of neighbours. Built from the` | Continues the comment: and every ordered pair of different items is once a pair of direct neighbours. The square is built from one start order. |
| 128 | `        # start order 0, 1, n-1, 2, n-2, ... shifted by 0 to n-1, with random item labels and row order.` | Continues the comment: the start order is 0, 1, `n-1`, 2, `n-2` and so on. Each row shifts it by a value from 0 to `n-1`. Then the items get random labels, and the rows get a random order. |
| 129 | `        start, lo, hi = [0], 1, n - 1` | `start`: the start order, which begins with 0. `lo` and `hi`: the next low number and the next high number to add, 1 and `n - 1` at first. |
| 130 | `        while lo <= hi:` | Starts a loop that runs until the low number has passed the high number. |
| 131 | `            start.append(lo)` | Adds the low number. |
| 132 | `            if lo != hi:` | Unless both numbers are the same. |
| 133 | `                start.append(hi)` | Adds the high number. |
| 134 | `            lo, hi = lo + 1, hi - 1` | Moves the low number up and the high number down. For 6 items the start order becomes 0, 1, 5, 2, 4, 3. |
| 135 | `        label = list(range(n))` | `label`: the list of the numbers 0 to `n - 1`. |
| 136 | `        self.rng.shuffle(label)` | First random choice: shuffles `label`. Entry `x` of the list is now the real item for which the number `x` of the construction stands. |
| 137 | `        rows = [[label[(x + r) % n] for x in start] for r in range(n)]` | `rows`: the `n` orders. Row `r` takes each number of the start order, adds `r`, keeps the rest of the division by `n`, and replaces the result with its label. |
| 138 | `        self.rng.shuffle(rows)` | Second random choice: shuffles the order of the rows. So it is random which row stands at which place of the result. |
| 139 | `        return rows` | Returns the rows. |
| 141 | `    def all_orders(self, n):` | Starts the method `all_orders`. It returns every possible order of `n` items once. The rows stand in a random order. |
| 142 | `        # Every possible order of n items once, in a random row order. For n = 3 these are 6 orders: every` | Comment: every possible order of `n` items stands once, and the rows have a random order. For 3 items these are 6 orders. |
| 143 | `        # item is twice at every position, and every ordered pair of items is twice a pair of neighbours.` | Continues the comment: in these 6 orders every item stands twice at every position, and every ordered pair of items is twice a pair of direct neighbours. |
| 144 | `        rows = [list(o) for o in itertools.permutations(range(n))]` | `rows`: all orders of the numbers 0 to `n - 1`, each as a list. |
| 145 | `        self.rng.shuffle(rows)` | The one random choice of this method: shuffles the order of the rows. |
| 146 | `        return rows` | Returns the rows. |

### `Gen`: the step methods `ZD`, `ZC`, `ZN`, `ZM`, `ZA` (lines 148 to 216)

| Line | Source | Explanation |
|---:|---|---|
| 148 | `    # ---- steps ----` | Comment: the methods that build the steps start here. Each method has the name of its step. |
| 149 | `    def ZD(self):` | Starts the method `ZD`. It builds the 216 processes of step `ZD` for this session. |
| 150 | `        order = {}` | `order`: one Williams square per size and CPU, empty at first. |
| 151 | `        for s in ZD_SIZES:` | Starts a loop over the three sizes, in the fixed order 4, 8 and 16 MiB. |
| 152 | `            for cpu in self.cpus:` | Starts a loop over the two CPUs, in the order of the session. |
| 153 | `                order[s, cpu] = self.williams_square(len(ZD_CELLS))` | Builds a Williams square of the 6 cells for this size and CPU. Each call makes two shuffles with `rng`: the labels and the row order. So each size and CPU gets its own random square. |
| 154 | `        for r in range(UNITS):` | Starts the loop over the 6 replicate sets. `r` runs from 0 to 5. |
| 155 | `            sizes = list(ZD_SIZES)` | A copy of the list of sizes for this set. |
| 156 | `            self.rng.shuffle(sizes)` | Shuffles the copy. So each replicate set has its own random order of the three sizes. |
| 157 | `            for s in sizes:` | Starts the loop over the sizes in that order. |
| 158 | `                for cpu in self.cpus:` | Starts the loop over the CPUs in the order of the session. All processes of the first CPU at this size come before those of the second CPU. |
| 159 | `                    for ci in order[s, cpu][r]:` | Starts the loop over the 6 cells, in the order that row `r` of the Williams square of this size and CPU gives. `ci` is the number of a cell. |
| 160 | `                        k, (ename, mb, extra) = ZD_CELLS[ci]` | Splits the cell into its parts: the kernel `k`, and the name, the buffer size and the option of its evict condition. |
| 161 | `                        ks = "%s@%s" % (k, s)` | `ks`: the kernel and the size in the form `KERNEL@SIZE`, for example `asmread@8M`. |
| 162 | `                        t = [self.trial("K=%s\|S=%s\|evict=%d" % (k, s, mb), 1200, ks, 4, 300)] * 4` | `t`: the 4 trials of the process, all equal. The condition label names the kernel, the size and the MiB of the evict buffer, for example `K=asmread\|S=8M\|evict=512`. Each trial has a prefix of 1200 ms of the same kernel at the same size, and then 4 target windows of 300 ms. The counters are closed. So one process has 9600 ms of nominal kernel work. |
| 163 | `                        self.add("r%d-%s-cpu%d-%s-%s" % (r + 1, s, cpu, k, ename), cpu, s,` | Appends the process. Its tag holds the replicate set counted from 1, the size, the CPU, the kernel and the evict condition, for example `r1-8M-cpu2-asmread-E512`. |
| 164 | `                                 [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s)), ("econd", ename)],` | The header pairs of the plan: the replicate set, the kernel, the size in bytes and the evict condition. |
| 165 | `                                 t, extra, mb)` | The last arguments: the trials, the option of the evict condition and the MiB of the evict buffer. |
| 167 | `    def ZC(self):` | Starts the method `ZC`. It builds the 32 processes of step `ZC` for this session. |
| 168 | `        events = " --pmu-type %d --events %s" % (PMU_TYPE, ZC_EVENTS)` | `events`: the counter options for the command line: `--pmu-type 11`, and `--events` with the 6 events of `ZC_EVENTS`. |
| 169 | `        cells = [(k, s, e) for k in ZC_KERNELS for s in ZC_SIZES for e in ECONDS]` | `cells`: the 8 cells of the step: each of the 2 kernels at each of the 2 sizes with each of the 2 evict conditions. |
| 170 | `        for r in (1, 2):` | Starts the loop over the two replicates, 1 and 2. |
| 171 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 172 | `                block = list(cells)` | A copy of the list of cells for this replicate and CPU. |
| 173 | `                self.rng.shuffle(block)` | Shuffles the copy. So each block of one replicate and one CPU has its own random order. |
| 174 | `                for k, s, (ename, mb, extra) in block:` | Starts the loop over the 8 cells in the shuffled order. |
| 175 | `                    t = [self.trial("K=%s\|S=%s\|evict=%d\|count=read" % (k, s, mb), None, "%s@%s" % (k, s), 20, 300, "read")]` | `t`: the one trial of the process. It has no prefix and 20 target windows of 300 ms, that is 6000 ms of nominal kernel work. The counter mode is `read`: the runner reads the counters for each window. The condition label names the kernel, the size, the MiB of the evict buffer and the counter mode. |
| 176 | `                    self.add("%s-%s-%s-cpu%d-p%d" % (k, s, ename, cpu, r), cpu, s,` | Appends the process. Its tag holds the kernel, the size, the evict condition, the CPU and the replicate, for example `asmread-8M-E0-cpu2-p1`. |
| 177 | `                             [("rep_set", r), ("kernel", k), ("size", size_bytes(s)), ("econd", ename)],` | The header pairs of the plan: the replicate, the kernel, the size in bytes and the evict condition. |
| 178 | `                             t, extra + events, mb)` | The last arguments: the trial, the option of the evict condition followed by the counter options, and the MiB of the evict buffer. |
| 180 | `    def ZN(self):` | Starts the method `ZN`. It builds the 144 processes of step `ZN` for this session. |
| 181 | `        order = {}` | `order`: one table of orders per size and CPU, empty at first. |
| 182 | `        for s in ZN_SIZES:` | Starts a loop over the four sizes, in their fixed order. |
| 183 | `            for cpu in self.cpus:` | Starts a loop over the two CPUs, in the order of the session. |
| 184 | `                order[s, cpu] = self.all_orders(len(ZN_KERNELS))` | Builds the table for this size and CPU: the 6 possible orders of the 3 kernels, with the rows in a random order. Each call makes one shuffle with `rng`. |
| 185 | `        for r in range(UNITS):` | Starts the loop over the 6 replicate sets. `r` runs from 0 to 5. |
| 186 | `            sizes = list(ZN_SIZES)` | A copy of the list of sizes for this set. |
| 187 | `            self.rng.shuffle(sizes)` | Shuffles the copy. So each replicate set has its own random order of the sizes. |
| 188 | `            for s in sizes:` | Starts the loop over the sizes in that order. |
| 189 | `                for cpu in self.cpus:` | Starts the loop over the CPUs in the order of the session. All processes of the first CPU at this size come before those of the second CPU. |
| 190 | `                    for ki in order[s, cpu][r]:` | Starts the loop over the kernels, in the order that row `r` of the table of this size and CPU gives. `ki` is the number of a kernel. |
| 191 | `                        k = ZN_KERNELS[ki]` | `k`: the name of the kernel with that number. |
| 192 | `                        ks = "%s@%s" % (k, s)` | `ks`: the kernel and the size in the form `KERNEL@SIZE`. |
| 193 | `                        t = [self.trial("K=%s\|S=%s" % (k, s), 1200, ks, 4, 300)] * 4` | `t`: the 4 trials of the process, all equal. The condition label names the kernel and the size. Each trial has a prefix of 1200 ms of the same kernel at the same size, and then 4 target windows of 300 ms. The counters are closed. So one process has 9600 ms of nominal kernel work. |
| 194 | `                        self.add("r%d-%s-cpu%d-%s" % (r + 1, s, cpu, k), cpu, s,` | Appends the process. Its tag holds the replicate set counted from 1, the size, the CPU and the kernel. |
| 195 | `                                 [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s))], t)` | The header pairs of the plan (the replicate set, the kernel and the size in bytes), and the trials. |
| 197 | `    def ZM(self):` | Starts the method `ZM`. It builds the 40 processes of step `ZM` for this session. |
| 198 | `        for r in (1, 2):` | Starts the loop over the two replicates, 1 and 2. |
| 199 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 200 | `                block = list(ZM_PADS)` | A copy of the list of the 10 pads for this replicate and CPU. |
| 201 | `                self.rng.shuffle(block)` | Shuffles the copy. So each block of 10 processes has its own random order of the pads. |
| 202 | `                for pad in block:` | Starts the loop over the pads in the shuffled order. |
| 203 | `                    name = "P%d" % pad` | `name`: the label of the pad, for example `P8`. |
| 204 | `                    t = [self.trial("K=asmread\|S=8M\|rec=%s" % name, None, "asmread@8M", 300, 100)]` | `t`: the one trial of the process: `asmread` at 8 MiB, no prefix, 300 target windows of 100 ms. That is 30000 ms of nominal kernel work. The counters are closed. |
| 205 | `                    self.add("%s-cpu%d-p%d" % (name, cpu, r), cpu, "8M",` | Appends the process. Its tag holds the pad label, the CPU and the replicate, for example `P8-cpu2-p1`. |
| 206 | `                             [("rep_set", r), ("kernel", "asmread"), ("size", size_bytes("8M")), ("pcond", name)],` | The header pairs of the plan: the replicate, the kernel, the size in bytes, and the pad label under the key `pcond`. |
| 207 | `                             t, " --rec-pad %d" % pad)` | The last arguments: the trial, and the option `--rec-pad` with the pad in bytes. |
| 209 | `    def ZA(self):` | Starts the method `ZA`. It builds the 6 processes of the acceptance step, in the fixed order of `ZA_PROCS`. It does not use `rng`. |
| 210 | `        for name, k, s, mb, opts in ZA_PROCS:` | Starts the loop over the 6 entries of `ZA_PROCS`. |
| 211 | `            ks = "%s@%s" % (k, s)` | `ks`: the kernel and the size in the form `KERNEL@SIZE`. |
| 212 | `            t = [self.trial("K=%s\|S=%s\|acc=%s" % (k, s, name), 400, ks, 3, 300)]` | `t`: the one trial of the process: a prefix of 400 ms of the same kernel, and then 3 target windows of 300 ms. The condition label names the kernel, the size and the name of the process. |
| 213 | `            self.add("%s-cpu2" % name, 2, s,` | Appends the process. Its tag is the name followed by `-cpu2`, and its CPU is 2. |
| 214 | `                     [("kernel", k), ("size", size_bytes(s)), ("acond", name)], t, " --trace" + opts, mb)` | The header pairs (the kernel, the size in bytes, and the name under the key `acond`), the trial, the option `--trace` followed by the options of the entry, and the MiB of the evict buffer. |

### Functions `generate`, `plan_text`, `phase_ms`, `proc_ms`, `write` (lines 217 to 276)

| Line | Source | Explanation |
|---:|---|---|
| 217 | `def generate(base, div):` | Starts the function `generate`. It builds the processes of every step and session. |
| 218 | `    """Returns {(step, session): Gen}. ZA only in session 1."""` | Description text: the function returns a dictionary from a pair of step and session to its `Gen` object. The step `ZA` exists in session 1 only. |
| 219 | `    out = {}` | `out`: the result dictionary, empty at first. |
| 220 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 221 | `        for step in STEPS:` | Starts the loop over the steps, in the order of `STEPS`. |
| 222 | `            if step == "ZA" and session == 2:` | Tests for the acceptance step `ZA` in session 2. |
| 223 | `                continue` | Skips it. The acceptance step exists in session 1 only. |
| 224 | `            g = Gen(step, session, base, div)` | Creates the `Gen` object of this step and session. It gets its own seed and its own random number generator. |
| 225 | `            getattr(g, step)()` | Calls the method of `g` whose name is the step name. That method fills `g.procs`. |
| 226 | `            out[step, session] = g` | Stores the object. |
| 227 | `    return out` | Returns the dictionary. |
| 230 | `def plan_text(g, idx, p):` | Starts the function `plan_text`. It returns the text of the plan file of the process `p`, which has the number `idx` in the step of `g`. |
| 231 | `    pairs = [("step", g.step), ("session", g.session), ("cpu", p["cpu"]),` | `pairs`: the header pairs of the plan. First the step, the session and the CPU. |
| 232 | `             ("bytes", p["bytes"]), ("proc", idx)] + p["keys"] + \` | Continues the list: the buffer size in bytes and the number of the process, then the pairs of the process itself. The backslash joins the next line to this statement. |
| 233 | `            [("seed", g.seed), ("test", 0 if g.div == 1 else 1)]` | Ends the list: the seed of the step and session, and `test`. `test` is 0 for a real plan and 1 when the durations were divided by a test divisor above 1. |
| 234 | `    lines = ["# bwx8-plan v1",` | `lines`: the lines of the plan file. The first one is the fixed text `# bwx8-plan v1`, the name and the version of the format. |
| 235 | `             "# " + " ".join("%s=%s" % kv for kv in pairs),` | The second one: `#` and all header pairs as `key=value`, with one blank between them. |
| 236 | `             "# trial cond rep prev pfx pred tgt nwin win_ms count bins"]` | The third one: the names of the 11 columns of a trial line. |
| 237 | `    seen = {}` | `seen`: how often each condition label was used up to now, empty at first. |
| 238 | `    for n, t in enumerate(p["trials"]):` | Starts the loop over the trials. `n` is the number of the trial, counted from 0. |
| 239 | `        seen[t[0]] = seen.get(t[0], 0) + 1      # rep: repeat number of this cond` | Counts the use of the condition label of this trial. The count is the value of the column `rep`: 1 for the first trial with this label, 2 for the second, and so on. |
| 240 | `        lines.append("%d %s %d %s %s %s %s %d %d %s %d" % ((n, t[0], seen[t[0]]) + t[1:]))` | Adds the trial line: the trial number, the condition label, the repeat number, and then the other 8 values of the trial tuple. These are the previous activity, the prefix, the predecessor, the target, the number of windows, the window length in ms, the counter mode and the bins value. One blank separates the fields. |
| 241 | `    return "\n".join(lines) + "\n"` | Returns the lines joined with newlines, with a newline at the end. |
| 244 | `def phase_ms(tok):` | Starts the function `phase_ms`. It returns the duration in ms of one phase text of a trial. |
| 245 | `    return 0 if tok == "-" else int(tok.split(":")[1])` | Returns 0 for `-`, the mark of a phase that the trial does not have. In every other case it returns the number after the colon of a text such as `asmread@8M:1200`. |
| 248 | `def proc_ms(p):` | Starts the function `proc_ms`. |
| 249 | `    """Nominal kernel work of one process, in ms. The evict step of a process is not kernel work."""` | Description text: the function returns the nominal kernel work of one process in ms. The evict step of a process is not counted as kernel work. |
| 250 | `    return sum(phase_ms(t[1]) + phase_ms(t[2]) + phase_ms(t[3]) + t[5] * t[6] for t in p["trials"])` | Adds up over all trials: the durations of the previous activity, the prefix and the predecessor, plus the number of target windows times the window length. This is the planned time of the timed parts. The real run time of a process is longer. |
| 253 | `def write(gens, out, manifest):` | Starts the function `write`. It writes all files into the folder `out`. `manifest` is the text of the file `MANIFEST.txt`. |
| 254 | `    os.makedirs(out, exist_ok=True)` | Creates the output folder when it does not exist. |
| 255 | `    for session in (1, 2):` | Starts a loop over the two sessions. |
| 256 | `        shutil.rmtree(os.path.join(out, "s%d" % session), ignore_errors=True)` | Removes the folder `s1` or `s2` with everything in it. A folder that does not exist gives no error. So no file of an older run stays in these folders. |
| 257 | `    for (step, session), g in gens.items():` | Starts the loop over all steps and sessions. |
| 258 | `        sdir = os.path.join(out, "s%d" % session)` | `sdir`: the folder of the session. |
| 259 | `        os.makedirs(os.path.join(sdir, step))` | Creates the folder for the plan files of the step, and the session folder with it. |
| 260 | `        rows = ["idx\ttag\tcpu\tbytes\tplan\targs"]` | `rows`: the rows of the schedule file. The first row holds the six column names, with tabs between them. |
| 261 | `        for idx, p in enumerate(g.procs):` | Starts the loop over the processes, in the order in which they will run. `idx` counts from 0. |
| 262 | `            name = "%04d.plan" % idx` | `name`: the name of the plan file: the `idx` with 4 digits and the ending `.plan`, for example `0017.plan`. |
| 263 | `            with open(os.path.join(sdir, step, name), "w") as f:` | Opens the plan file for writing. |
| 264 | `                f.write(plan_text(g, idx, p))` | Writes the text of the plan. |
| 265 | `            # The plan path is relative to the folder of run_bwx11.sh.` | Comment: the path of the plan in the `args` column is relative to the folder of the run script `run_bwx11.sh`. |
| 266 | `            args = "--trial --cpus %d --bytes %d --plan sched11/s%d/%s/%s%s" % (` | `args`: the options of the process for the runner: `--trial` (the mode that runs a plan), `--cpus` with the one worker CPU, `--bytes` with the buffer size, and `--plan` with the path `sched11/s<session>/<STEP>/<name>`. The folder name `sched11` is fixed here, also when `--out` names another folder. |
| 267 | `                p["cpu"], p["bytes"], session, step, name, p["extra"])` | The values for that text: the CPU, the size in bytes, the session, the step, the name of the plan file, and at the end the extra options of the process. |
| 268 | `            rows.append("%d\t%s\t%d\t%d\t%s\t%s" % (idx, p["tag"], p["cpu"], p["bytes"], name, args))` | Adds the schedule row of the process: its `idx`, its tag, its CPU, its size in bytes, the name of its plan file and its options, with tabs between them. |
| 269 | `        with open(os.path.join(sdir, step + ".tsv"), "w") as f:` | Opens the schedule file `<STEP>.tsv` of the step for writing. |
| 270 | `            f.write("\n".join(rows) + "\n")` | Writes all rows, each with a newline at its end. |
| 271 | `        with open(os.path.join(sdir, step + ".bin"), "w") as f:` | Opens the file `<STEP>.bin` for writing. |
| 272 | `            f.write(BINARY[step] + "\n")` | Writes the word of the binary of the step and a newline. |
| 273 | `    with open(os.path.join(out, "MANIFEST.txt"), "w") as f:` | Opens the file `MANIFEST.txt` in the output folder for writing. |
| 274 | `        f.write(manifest)` | Writes the manifest text. |

### Balance checks: `set_orders`, `zd_orders_ok`, `zn_orders_ok`, `blocks_ok` (lines 277 to 309)

| Line | Source | Explanation |
|---:|---|---|
| 277 | `def set_orders(g, item):` | Starts the function `set_orders`. It collects, from the finished list of processes, the order of the items inside each replicate set. `item` is a function that gives the number of the item of one process. |
| 278 | `    """{(size, cpu): {rep_set: [item index, in schedule order]}}; item(header keys) gives the index."""` | Description text: the result maps each pair of size and CPU to a dictionary. That dictionary maps each replicate set to the list of item numbers in schedule order. |
| 279 | `    seen = {}` | `seen`: the collected orders, empty at first. |
| 280 | `    for p in g.procs:` | Starts the loop over the processes in schedule order. |
| 281 | `        k = dict(p["keys"])` | `k`: the header pairs of the process as a dictionary. |
| 282 | `        seen.setdefault((k["size"], p["cpu"]), {}).setdefault(k["rep_set"], []).append(item(k))` | Appends the item number of this process to the list of its size, CPU and replicate set. `setdefault` creates an entry that is missing. |
| 283 | `    return seen` | Returns the collected orders. |
| 286 | `def zd_orders_ok(g):` | Starts the function `zd_orders_ok`, the balance check of step `ZD`. |
| 287 | `    """Per size and CPU: the (kernel, condition) orders of the 6 replicate sets form a Williams square."""` | Description text: for each size and CPU, the orders of the pairs of kernel and condition in the 6 replicate sets form a Williams square. |
| 288 | `    names = [(k, e[0]) for k, e in ZD_CELLS]` | `names`: the 6 cells as pairs of the kernel and the name of the evict condition. |
| 289 | `    seen = set_orders(g, lambda k: names.index((k["kernel"], k["econd"])))` | Collects the cell orders from the finished schedule. The item number of a process is the place of its cell in `names`. |
| 290 | `    return len(seen) == len(ZD_SIZES) * 2 and all(` | Starts the result. First condition: there are 6 pairs of size and CPU, 3 sizes times 2 CPUs. |
| 291 | `        len(sets) == UNITS and williams_ok(list(sets.values()), len(ZD_CELLS)) for sets in seen.values())` | Second condition, for every pair of size and CPU: it has 6 replicate sets, and their orders pass `williams_ok` for 6 items. |
| 294 | `def zn_orders_ok(g):` | Starts the function `zn_orders_ok`, the balance check of step `ZN`. |
| 295 | `    """Per size and CPU: the kernel orders of the 6 replicate sets are the 6 possible orders, each one once."""` | Description text: for each size and CPU, the kernel orders of the 6 replicate sets are the 6 possible orders, each one once. |
| 296 | `    seen = set_orders(g, lambda k: ZN_KERNELS.index(k["kernel"]))` | Collects the kernel orders from the finished schedule. The item number of a process is the place of its kernel in `ZN_KERNELS`. |
| 297 | `    return len(seen) == len(ZN_SIZES) * 2 and all(` | Starts the result. First condition: there are 8 pairs of size and CPU, 4 sizes times 2 CPUs. |
| 298 | `        len(sets) == UNITS and all_orders_ok(list(sets.values()), len(ZN_KERNELS)) for sets in seen.values())` | Second condition, for every pair of size and CPU: it has 6 replicate sets, and their orders pass `all_orders_ok` for 3 items. |
| 301 | `def blocks_ok(g, keys, conds):` | Starts the function `blocks_ok`, the balance check of a step whose processes come in shuffled blocks. |
| 302 | `    """The processes come in blocks of len(conds), and every block holds each condition once.` | Description text: the processes come in blocks of as many processes as there are conditions, and every block holds each condition once. |
| 303 | ``    A condition is the tuple of the header values named by `keys`."""`` | Continues the text: a condition is the tuple of the header values that `keys` names. |
| 304 | `    got = [tuple(dict(p["keys"]).get(k) for k in keys) for p in g.procs]` | `got`: the condition of every process in schedule order, as a tuple of its header values for the given keys. |
| 305 | `    size = len(conds)` | `size`: the number of conditions, which is the length of one block. |
| 306 | `    return len(got) % size == 0 and all(` | Starts the result. First condition: the number of processes is a multiple of the block length. |
| 307 | `        sorted(got[i:i + size]) == sorted(conds) for i in range(0, len(got), size))` | Second condition: each block, sorted, is equal to the sorted list of the conditions. So each block holds every condition exactly once. |

### Function `report`: counts, nominal kernel work and balance lines (lines 310 to 354)

| Line | Source | Explanation |
|---:|---|---|
| 310 | `def report(gens):` | Starts the function `report`. It builds the text that the program prints, and it runs the balance checks. |
| 311 | `    ok = True` | `ok`: stays true while every balance check passes. |
| 312 | `    lines = ["step session binary processes trials nominal_kernel_work_s evict_processes"]` | `lines`: the lines of the report. The first one is the head of the table: step, session, binary, number of processes, number of trials, nominal kernel work in seconds, and number of processes with an evict step. |
| 313 | `    total = {1: [0, 0, 0], 2: [0, 0, 0]}` | `total`: three sums per session: the processes, the nominal work in ms, and the processes with an evict step. |
| 314 | `    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):` | Starts the loop over all steps and sessions, sorted by the session and then by the place of the step in `STEPS`. |
| 315 | `        n, tr = len(g.procs), sum(len(p["trials"]) for p in g.procs)` | `n`: the number of processes of the step. `tr`: the number of trials of all its processes. |
| 316 | `        ms = sum(map(proc_ms, g.procs))` | `ms`: the nominal kernel work of the step in ms, the sum of `proc_ms` over its processes. |
| 317 | `        ev = sum(1 for p in g.procs if p["evict"])` | `ev`: the number of processes of the step that have an evict step. |
| 318 | `        lines.append("%s %d %s %d %d %g %d" % (step, session, BINARY[step], n, tr, ms / 1000, ev))` | Adds the table row of the step: its name, the session, the word of the binary, `n`, `tr`, the nominal work in seconds and `ev`. `%g` prints a number in its shortest form. |
| 319 | `        total[session][0] += n` | Adds the processes to the sum of the session. |
| 320 | `        total[session][1] += ms` | Adds the nominal work to the sum of the session. |
| 321 | `        total[session][2] += ev` | Adds the processes with an evict step to the sum of the session. |
| 322 | `    for session in (1, 2):` | Starts a loop over the two sessions, for the total lines. |
| 323 | `        n, ms, ev = total[session]` | Takes the three sums of the session. |
| 324 | `        lines.append("session %d total: %d processes, nominal kernel work %g s (%g min)"` | Adds the total line of the session: the number of processes, and the nominal kernel work in seconds and in minutes. |
| 325 | `                     % (session, n, ms / 1000, round(ms / 60000, 2)))` | The values of that line. The minutes are rounded to two decimal places. |
| 326 | `        lines.append("session %d evict step: %d processes run with --evict-mb %d; the evict step is real time that is "` | Starts the line about the evict step of the session: the number of processes that run with `--evict-mb 512`, and the statement that the evict step is real time. |
| 327 | `                     "not kernel work, est. %g to %g s per process, so est. %g to %g s more in the session; "` | Continues the text of the line: that time is not kernel work. Then the estimate per process and the estimated sum for the session. |
| 328 | `                     "it is not in the nominal kernel work and not in the longest process that gives MARGIN "` | Continues the text of the line: the evict time is not in the nominal kernel work, and not in the longest process from which the run script computes `MARGIN`. |
| 329 | `                     "(RESERVE of run_bwx11.sh, default 90 s, covers it)"` | Ends the text of the line: the setting `RESERVE` of `run_bwx11.sh`, 90 s when it is not set, covers the evict time. |
| 330 | `                     % (session, ev, EVICT_MB, EVICT_EST_S[0], EVICT_EST_S[1], ev * EVICT_EST_S[0], ev * EVICT_EST_S[1]))` | The values of the line: the session, the number of processes, 512, the two estimates per process (0.3 s and 1 s, est.), and the number of processes times each estimate. |
| 331 | `    lines.append("balance:")` | Adds the heading of the balance part. |
| 332 | `    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):` | Starts a second loop over all steps and sessions, in the same order, for the balance checks. |
| 333 | `        if step == "ZD":` | The check of step `ZD`. |
| 334 | `            a = zd_orders_ok(g)` | `a`: the result of `zd_orders_ok`. |
| 335 | `            text = ("per size and CPU the orders of the 6 sets put each (kernel, condition) cell once at each "` | `text`: the sentence of the report for this check. It says that per size and CPU the orders of the 6 sets put each cell once at each position. |
| 336 | `                    "position, and each ordered pair of cells is neighbours once")` | Ends the sentence: and each ordered pair of cells is once a pair of neighbours. |
| 337 | `        elif step == "ZN":` | The check of step `ZN`. |
| 338 | `            a = zn_orders_ok(g)` | `a`: the result of `zn_orders_ok`. |
| 339 | `            text = ("per size and CPU the 6 sets use the 6 orders of the 3 kernels once each (each kernel twice at "` | `text`: the sentence for this check. It says that per size and CPU the 6 sets use the 6 orders of the 3 kernels once each. |
| 340 | `                    "each position, each ordered pair of kernels neighbours twice)")` | Ends the sentence: so each kernel stands twice at each position, and each ordered pair of kernels is twice a pair of neighbours. |
| 341 | `        elif step == "ZC":` | The check of step `ZC`. |
| 342 | `            a = blocks_ok(g, ("kernel", "size", "econd"),` | `a`: the result of `blocks_ok` with the header keys `kernel`, `size` and `econd`. |
| 343 | `                          [(k, size_bytes(s), e[0]) for k in ZC_KERNELS for s in ZC_SIZES for e in ECONDS])` | The list of the 8 conditions for that check: each kernel with each size in bytes and each evict condition. |
| 344 | `            text = "each block of 8 processes holds every kernel, size and condition once"` | `text`: the sentence for this check: each block of 8 processes holds every kernel, size and condition once. |
| 345 | `        elif step == "ZM":` | The check of step `ZM`. |
| 346 | `            a = blocks_ok(g, ("pcond",), [("P%d" % p,) for p in ZM_PADS])` | `a`: the result of `blocks_ok` with the header key `pcond` and the 10 pad labels as the conditions. |
| 347 | `            text = "each block of 10 processes holds every pad once"` | `text`: the sentence for this check: each block of 10 processes holds every pad once. |
| 348 | `        else:` | Every other step has no balance check. |
| 349 | `            continue` | Skips it. |
| 350 | `        ok = ok and a` | `ok` becomes false when this check failed. |
| 351 | `        lines.append("%s session %d: %s: %s" % (step, session, text, "yes" if a else "NO"))` | Adds the balance line of the step and session: the sentence, and then `yes` when the check passed or `NO` when it failed. |
| 352 | `    return "\n".join(lines) + "\n", ok` | Returns the report text and the result of all checks. |

### Function `main` (lines 355 to 376)

| Line | Source | Explanation |
|---:|---|---|
| 355 | `def main():` | Starts the function `main`. |
| 356 | `    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])` | Creates the reader of the command line. Its description is the first line of the description text of the file. |
| 357 | `    ap.add_argument("--seed", type=int, default=20261115, help="base seed")` | The option `--seed`: the base seed, a whole number. It is 20261115 when the option is not given. |
| 358 | `    ap.add_argument("--test-divisor", type=int, default=1)` | The option `--test-divisor`: the number by which every duration is divided. It is 1 when the option is not given, which changes nothing. |
| 359 | `    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sched11"))` | The option `--out`: the output folder. When it is not given, it is the folder `sched11` in the folder of this file. |
| 360 | `    a = ap.parse_args()` | Reads the command line. |
| 361 | `    if a.test_divisor < 1 or MIN_WIN_MS % a.test_divisor:` | Tests the divisor: it must be at least 1, and it must divide `MIN_WIN_MS` without a rest. |
| 362 | `        sys.exit("--test-divisor must divide %d ms" % MIN_WIN_MS)` | If not: prints the message to the error output and ends the program with exit status 1. No file is written. |
| 363 | `    gens = generate(a.seed, a.test_divisor)` | Builds the processes of all steps and sessions. |
| 364 | `    text, ok = report(gens)` | Builds the report text and runs the balance checks. |
| 365 | `    manifest = "base_seed=%d\ntest_divisor=%d\n" % (a.seed, a.test_divisor)` | `manifest`: the text of `MANIFEST.txt`. Its first two lines give the base seed and the test divisor. |
| 366 | `    manifest += "".join("seed %s s%d %d\n" % (step, session, g.seed) for (step, session), g in gens.items())` | Adds one line per step and session with its seed, in the form `seed STEP sN SEED`. |
| 367 | `    manifest += "".join("bin %s s%d %s\n" % (step, session, BINARY[step]) for (step, session) in gens)` | Adds one line per step and session with the word of its binary, in the form `bin STEP sN WORD`. |
| 368 | `    manifest += "watch none\n"` | Adds the line `watch none`: no step has a `.watch` file. |
| 369 | `    write(gens, a.out, manifest)` | Writes all files. This happens before the result of the balance checks is used. |
| 370 | `    print("written: %s" % a.out)` | Prints the output folder. |
| 371 | `    sys.stdout.write(text)` | Prints the report. |
| 372 | `    sys.exit(0 if ok else 1)` | Ends the program with exit status 0 when every balance check passed, and with 1 when one failed. The files are written in both cases. |
| 375 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 376 | `    main()` | Runs `main`. |
