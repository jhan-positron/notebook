# `schedule8.py` explained, line by line

- Source file: `bwx8-2026-11-14/schedule8.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 417 lines, 17172 bytes).
- sha256 of the source when this page was built: `ddcdb0c4bc12b2e2da26f76cf94a11f601f7e6283bcb029fbe50da48a2ee8009`.

## Short version: purpose

`schedule8.py` writes the input files of round 1 for the run script `run_bwx8.sh`: for each step and session one schedule file with one row per process, and one plan file per process of every step other than `B6W`. It fixes the order of the processes, and of the trials inside a process, with a random number generator whose seed depends only on the base seed, the step and the session. It also checks the balance of the kernel orders of step `S2` and of the condition orders of the steps `S3` and `CM`, and it prints the counts and the nominal kernel work.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 1**: the first set of tests of the investigation into the buffer size of 8 MiB. This file can write the schedules of its 11 steps. The repo holds result folders of three of them: `B6W`, `S2` and `S4` [Ref1].
- **Design**: the file `tackle-8mb.md`, the plan of the investigation.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`oldread2`**: a second copy of the old read kernel under another name. The kernel sequence of step `B6W` uses it.
- **Process**: one start of a benchmark binary.
- **Run script**: the script `run_bwx8.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Step**: one batch of processes of a round, for example `S2`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Header pairs**: the pairs of a key and a value in the second line of a plan file, for example `step=S2` and `seed=1926220671`.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Target, window**: the target is the kernel that a trial measures. A window is one timed period of it. Every window of round 1 has a planned length of 300 ms.
- **Trial mode, interval mode**: the two modes of a runner. In the trial mode (`--trial`) one process runs the trials of a plan file. In the interval mode (`--seq`) it times a sequence of kernels and has no plan file.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Condition**: one setting that a step compares, and the label that names it in the plan, for example `K=read|S=8M`.
- **Cycle, row**: a cycle is a group of trials of one process that holds every condition of the step once. A row is the order of the conditions in one cycle, as a list of numbers.
- **Replicate set**: the three processes of step `S2` that have the same size, CPU and replicate number: one process per kernel.
- **Unit**: the thing that the design counts 6 times per CPU and session. In step `S2` it is a replicate set. In every other step it is one process.
- **Balanced**: each item takes each place equally often. A shuffled order is random. It is balanced only where the code builds it so.
- **Base seed, seed**: the base seed is the one number that the caller can set with `--seed`. The seed of a step and session is derived from it.
- **Test divisor**: a number by which every duration is divided, for local tests only.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `open` means that the counters are open and are not read at the window boundaries. `read` means that the runner reads them at the boundaries of the target windows.
- **Bins**: records of 10 ms inside a target window. The field `bins` of a trial turns them on (1) or off (0).
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB**: 1024 bytes.

## Main flow

1. Read the options `--seed`, `--select`, `--test-divisor`, `--out` and `--report`. End with exit status 1 when the divisor does not divide 300 ms or when an entry of `--select` is wrong (lines 393 to 403).
2. Build the processes of every step and session with one `Gen` object each (line 404, lines 239 to 252). The constructor derives the seed of the step and session and starts its random number generator (lines 56 to 61).
3. Each step method fills the list of processes of its step in run order. They are called in the order of `STEPS`: `B6W` (lines 102 to 108), `S2` (lines 110 to 128), `S4` (lines 143 to 144), `P3G` (lines 159 to 170), `P3` (lines 149 to 157), `S3G` (lines 172 to 182), `S3` (lines 196 to 198), `BIN` (lines 216 to 224), `CS` (lines 226 to 236), `CM` (lines 200 to 203) and `C4` (lines 146 to 147).
4. Build the report text: per step and session the number of processes and trials and the nominal kernel work, then the totals of both sessions, then the results of the balance checks (line 405, lines 344 to 374).
5. Without `--report`: build the text of `MANIFEST.txt`, remove the folders `s1` and `s2` of the output folder, and write the plan files, the schedule files and `MANIFEST.txt` (lines 406 to 411, lines 283 to 308).
6. Print the report. End with exit status 0, or with 1 when a balance check failed (lines 412 to 413).

## Behavior a reader must know

- The seed of a step and session is the first 8 hexadecimal digits of the sha256 of the text `BASE/STEP/SESSION`, read as a whole number (lines 48 to 50). The base seed is 20261114 unless `--seed` gives another one (line 395).
- Each step and session has its own generator `random.Random(seed)` (line 59). All shuffles of a step use it, in a fixed sequence. So the same options always give the same files, and session 2 has random orders of its own.
- With the base seed 20261114 this rule gives the seed 1926220671 for step `S2` in session 1 and 1183365339 for step `S4` in session 1. The output files of these two steps on CRB record the same two values in their rows `M,plan.seed` [Ref1].
- Not random: the order of the two CPUs. Session 1 always runs CPU 2 before CPU 41, and session 2 runs CPU 41 before CPU 2 (line 26).
- The steps and their sizes per session, from the constants and the loops of this file:
  - `B6W`: 4 processes in the interval mode, each with 15.6 s of nominal kernel work (13 entries, 4 rounds, 300 ms). Sum: 62.4 s.
  - `S2`: 180 processes, each with 4 trials and 9.6 s. Sum: 1728 s.
  - `S4` and `C4`: 18 processes each, each with one trial of 60 s. Sum: 1080 s for each step.
  - `P3G`: 12 processes, each with 36 trials of 4.8 s, that is 172.8 s. Sum: 2073.6 s.
  - `P3`: 12 processes, each with 12 trials of 2.4 s, that is 28.8 s. Sum: 345.6 s.
  - `S3G`: 12 processes, each with 12 trials of 3.9 s, that is 46.8 s. Sum: 561.6 s.
  - `S3` and `CM`: 12 processes each, each with 48 trials of 2.7 s, that is 129.6 s. Sum: 1555.2 s for each step.
  - `BIN`: 12 processes for each pair of `--select`, each with 8 trials of 2.4 s, that is 19.2 s.
  - `CS`: 12 processes for each pair of `--select`, each with 12 trials of 2.4 s, that is 28.8 s.
- `B6W` has a fixed order and uses no random number (lines 102 to 108): process 1 on both CPUs, then process 2 on both CPUs.
- How the order of `S2` is made (lines 110 to 128):
  - First, for each size and CPU, the list of the 6 orders of the 3 kernels is shuffled once: 5 sizes in the fixed order of `S2_SIZES`, and inside a size the 2 CPUs in the order of the session (lines 113 to 117). Entry `r` of the shuffled list is the kernel order of the replicate set `r+1`.
  - So this part is balanced: for each size and CPU every one of the 6 kernel orders is used exactly once. Each kernel is the first of its replicate set 2 times, the second 2 times and the third 2 times.
  - Then, for each of the 6 replicate sets, the 5 sizes are shuffled once (lines 119 to 120). This part is random and not balanced.
  - The run order is: replicate set, then size, then CPU, then the 3 kernels in the order of that size, CPU and replicate set.
- How the order of `S4` and `C4` is made (lines 130 to 141): 3 passes, inside a pass the 2 CPUs in the order of the session, and for each CPU the 3 kernels in a newly shuffled order. This order is random and not balanced.
- In the steps `P3`, `P3G`, `S3G`, `S3` and `CM` every process runs all conditions on one buffer of 8 MiB. The processes run in this order: process 1 on both CPUs, then process 2 on both CPUs, up to process 6 (lines 97 to 99, lines 161 to 162). What is random is the order of the trials inside a process:
  - `P3` and `S3G`: the method `perm_rows` gives 24 rows per CPU: each of the 6 orders of three items 4 times, in a shuffled sequence (lines 80 to 84). Process `i` takes the rows `4i` to `4i+3` (line 99). So over the 6 processes of a CPU each order is used 4 times. The 4 rows of one process are not balanced.
  - `P3G`: each of the 4 cycles of a process holds the 9 conditions once, in a newly shuffled order (lines 164 to 166). This order is random and not balanced.
  - `S3` and `CM`: the method `williams_rows` gives 24 rows of 12 conditions per CPU (lines 86 to 92). It takes the start order of the design, shifts it 12 times, gives the conditions new random numbers, makes two copies and shuffles the 24 rows. Inside the rows every ordered pair of two different conditions is neighbours 2 times, and every condition stands 2 times at every position. The pairs across the end of one row and the start of the next are not balanced.
- How the order of `BIN` and `CS` is made (lines 205 to 214): 6 passes, inside a pass the pairs of `--select` in a newly shuffled order, and for each pair the 2 CPUs in the order of the session. In `BIN` the order of the two modes inside a process is fixed: ABBA BAAB in the passes 1, 3 and 5, and the mirror in the passes 2, 4 and 6 (lines 219 to 221). In `CS` the order of the three counter modes comes from `perm_rows`, one set of 24 rows per pair and CPU (line 227).
- The program has three balance checks, and the report runs them on the finished lists of processes (lines 360 to 373): the kernel orders of `S2` (lines 333 to 341), and the two rules of the rows of `S3` and `CM` (lines 320 to 330). The other shuffled orders have no check. A failed check gives a line with `NO` and exit status 1. The files are written before the exit status is set (lines 410 to 413).
- The folders `s1` and `s2` of the output folder are removed before the new files are written (line 286). With `--report` nothing is removed and nothing is written.
- The plan path in the `args` column always starts with `sched/`, also when `--out` names another folder (line 300).
- Each process gets one worker CPU through `--cpus`, CPU 2 or CPU 41, and its buffer size through `--bytes` (line 105, line 300). The `args` of a process with a plan file hold no option `--ctl-cpu` for the controlling thread of the trial mode. By the note `DECISIONS-bwx8.md` that thread then uses CPU 0. The output files of `S2` and `S4` on CRB record `M,ctl_cpu,0` for every process [Ref1]. The processes of `B6W` run the interval mode, which has no such option. In that mode the source `bwx8.c` pins only the worker thread.
- The buffer size of a process is 8 MiB in every step other than `S2`, `BIN` and `CS`. There it is the size of the condition. A phase with a smaller size, such as the predecessor `oldread@1M` of `S3`, runs on the first bytes of the buffer.
- No row of a schedule holds a counter option. So for the steps `CS`, `CM` and `C4`, whose trials use the counters, the run script needs the settings `BWX_PMU_TYPE` and `BWX_EVENTS` in its environment.
- The nominal kernel work counts planned durations only (lines 273 to 280).
- With a test divisor N above 1 every duration is divided by N and the plans get `test=1` (line 258). The numbers of windows and the order of the processes do not change. The rows of `B6W` have no plan and so no such mark: only their `--min-ms` value is smaller (line 106).
- In the output files of the steps `S2` and `S4` on CRB every process has the row `M,plan.test,0` [Ref1]. So these schedules were made without a test divisor.
- The program reads no input file and starts nothing on CRB.

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/schedule8.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (417 lines, 17172 bytes, sha256 `ddcdb0c4bc12b2e2da26f76cf94a11f601f7e6283bcb029fbe50da48a2ee8009`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text: files written and options (lines 1 to 16)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""schedule8.py - schedules and plan files of the design tackle-8mb.md.` | Starts the description text of the file. First line: the name and the purpose. The program writes the schedules and the plan files of the design `tackle-8mb.md`, the plan of the investigation into the buffer size of 8 MiB. `main` uses this line as the description in the help text. |
| 4 | `Usage: schedule8.py [--seed N] [--select KERNEL@SIZE,...] [--test-divisor N]` | Text of the description: the usage. All options are optional. This line names three: the base seed (`--seed`), the selection for two steps (`--select`) and the test divisor (`--test-divisor`). |
| 5 | `                    [--out DIR] [--report]` | Continues the usage: the output folder (`--out DIR`) and the switch `--report`. |
| 7 | `It writes, for session 1 and 2 and for each step:` | Text of the description: the list of the files that the program writes for session 1, for session 2 and for each step. |
| 8 | `  DIR/s<session>/<step>.tsv      one row per process (idx, tag, cpu, bytes, plan, args)` | Text of the description: the schedule file of a step. It has one row per process, with the columns `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`. |
| 9 | `  DIR/s<session>/<step>/NNNN.plan  one plan file per process (not for B6W)` | Text of the description: one plan file per process, in a folder with the name of the step. The step `B6W` has no plan files. Its processes run the interval mode of the runner, which takes its kernel sequence from the command line. |
| 10 | `  DIR/MANIFEST.txt               base seed, options, and the seed of each step and session` | Text of the description: the file `MANIFEST.txt`. It holds the base seed, the options `--test-divisor` and `--select`, and the seed of each step and session. |
| 11 | `DIR is "sched" beside this file by default. The folders DIR/s1 and DIR/s2 are replaced.` | Text of the description: the output folder is `sched` in the folder of this file, unless `--out` names another one. The program removes the folders `s1` and `s2` in it and writes them new. |
| 12 | `The steps BIN and CS are written only for the kernels and sizes named by --select.` | Text of the description: the program writes the steps `BIN` and `CS` only for the kernels and sizes that `--select` names. Without `--select` it does not write these two steps. |
| 13 | `--report prints the counts and the balance checks and writes nothing.` | Text of the description: with `--report` the program prints the counts and the results of the balance checks, and it writes no file. |
| 14 | `--test-divisor N divides every duration by N and marks the plans test=1.` | Text of the description: `--test-divisor N` divides every duration by N and writes `test=1` into the plans. By the note `DECISIONS-bwx8.md` the option exists only for the local test of the whole chain of scripts. |
| 15 | `The same options give the same bytes. Exit status 1 if a balance check fails.` | Text of the description: two runs with the same options write the same bytes. The exit status is 1 when a balance check fails. |
| 16 | `"""` | Ends the description text. |

### Imports and constants (lines 17 to 40)

| Line | Source | Explanation |
|---:|---|---|
| 17 | `import argparse` | Loads the Python module `argparse`, which reads the command line options. |
| 18 | `import hashlib` | Loads `hashlib`: the sha256 function, from which `step_seed` derives a seed. |
| 19 | `import itertools` | Loads `itertools`: used to build every order of a small set of items. |
| 20 | `import os` | Loads `os`: paths and folders. |
| 21 | `import random` | Loads `random`: the random number generator that shuffles the orders. |
| 22 | `import shutil` | Loads `shutil`: used to remove a folder tree. |
| 23 | `import sys` | Loads `sys`: the standard output and the exit status. |
| 25 | `KERNELS = ["oldread", "read", "asmread"]` | `KERNELS`: the names of the three read kernels of the design, in a fixed order: `oldread` (the old read kernel), `read` (the new read kernel) and `asmread` (a hand-written loop with loads only). Other lines name a kernel by its place in this list: 0, 1 or 2. |
| 26 | `CPUS = {1: [2, 41], 2: [41, 2]}          # session 2 uses the reversed order` | `CPUS`: the two worker CPUs in the order of each session. Session 1 runs CPU 2 before CPU 41. Session 2 runs CPU 41 before CPU 2. The comment says that session 2 uses the reversed order. |
| 27 | `M8 = 8 << 20` | `M8`: 8 MiB in bytes. `8 << 20` shifts the number 8 by 20 bits to the left, which gives 8388608. |
| 28 | `S2_SIZES = ["32K", "1M", "4M", "8M", "16M"]` | `S2_SIZES`: the five buffer sizes of step `S2`: 32 KiB, 1 MiB, 4 MiB, 8 MiB and 16 MiB. |
| 29 | `MODES = ["closed", "open", "read"]       # counter modes` | `MODES`: the three counter modes of a trial. By the design, `closed` means that no counter is open. `open` means that the counters are open and are not read at the window boundaries. `read` means that the counters are open and are read at the boundaries of the target windows. |
| 30 | `UNITS = 6                                # processes per CPU and session` | `UNITS`: 6, the number of units per CPU and session. By the comment a unit is a process. In step `S2` a unit is a replicate set of 3 processes, one per kernel. |
| 31 | `PERMS = list(itertools.permutations(range(3)))` | `PERMS`: all 6 orders of the numbers 0, 1 and 2, as a list of tuples. A number stands for a kernel of `KERNELS`, or in step `CS` for a counter mode of `MODES`. |
| 32 | `STEPS = ["B6W", "S2", "S4", "P3G", "P3", "S3G", "S3", "BIN", "CS", "CM", "C4"]` | `STEPS`: the names of the 11 steps, in the order in which the program builds and reports them. |
| 33 | `# B6SEQ of run_bwx.sh, unchanged.` | Comment: `B6SEQ` is the sequence of the same name in `run_bwx.sh`, the run script of the first runner, without a change. The two texts are equal. |
| 34 | `B6SEQ = ("asmread,oldread,oldread@1M,asmread,oldread@1M,oldread,asmread,"` | `B6SEQ`: the kernel sequence of step `B6W`, first part. The whole sequence has 13 entries: `asmread`, `oldread`, `oldread@1M`, `asmread`, `oldread@1M`, `oldread`, `asmread`, `oldread`, `oldread2`, `asmread`, `oldread2`, `oldread`, `asmread`. An entry `KERNEL@SIZE` runs the kernel on the first `SIZE` bytes of the buffer. `oldread2` is a second copy of the old read kernel under another name. |
| 35 | `         "oldread,oldread2,asmread,oldread2,oldread,asmread")` | Continues `B6SEQ`: the second part of the text. Python joins the two text pieces of lines 34 to 35 into one text. |
| 36 | `# Start order of design line 242.` | Comment: `S3_START` is the start order that the design gives for the schedule of step `S3`. The comment gives the place as `design line 242`. |
| 37 | `S3_START = [0, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6]` | `S3_START`: the start order of the 12 condition numbers: 0, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6. The method `williams_rows` builds its rows from it (line 90). |
| 38 | `S3_PREDS = ["oldread@8M", "read@8M", "asmread@8M", "oldread@1M"]` | `S3_PREDS`: the four predecessors of step `S3`: `oldread`, `read` and `asmread` on 8 MiB, and `oldread` on 1 MiB. The last one runs on the first 1 MiB of the buffer of 8 MiB. |

### Helper functions `size_bytes` and `step_seed` (lines 41 to 52)

| Line | Source | Explanation |
|---:|---|---|
| 41 | `def size_bytes(tok):` | Starts the function `size_bytes`. It turns a size text such as `8M` into a number of bytes. |
| 42 | `    mult = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}` | `mult`: the factor of each unit letter. `K` is 1024 (`1 << 10`), `M` is 1048576 (`1 << 20`) and `G` is 1073741824 (`1 << 30`). |
| 43 | `    if tok and tok[-1] in mult:` | Tests whether the text is not empty and ends with one of the three letters. |
| 44 | `        return int(tok[:-1]) * mult[tok[-1]]` | If so: returns the number before the letter times the factor. `8M` gives 8388608. |
| 45 | `    return int(tok)` | If not: returns the text as a whole number of bytes. A text that is not a whole number raises the error `ValueError`. |
| 48 | `def step_seed(base, step, session):` | Starts the function `step_seed`. It derives the seed of one step and session from the base seed. |
| 49 | `    h = hashlib.sha256(("%d/%s/%d" % (base, step, session)).encode()).hexdigest()` | `h`: the sha256 of the text `BASE/STEP/SESSION`, for example `20261114/S2/1`, as 64 hexadecimal digits. `encode` turns the text into bytes, and `hexdigest` gives the digits. |
| 50 | `    return int(h[:8], 16)` | Returns the first 8 hexadecimal digits as a whole number, a value from 0 to 4294967295. So each step and session has a seed of its own, and the same base seed always gives the same seeds. |

### Class `Gen`: constructor, trial helpers, `perm_rows`, `williams_rows`, `by_process` (lines 53 to 100)

| Line | Source | Explanation |
|---:|---|---|
| 53 | `class Gen:` | Starts the class `Gen`. One object builds the list of the processes of one step in one session. |
| 54 | `    """Builds the processes of one step and session."""` | Description text of the class: it builds the processes of one step and session. |
| 56 | `    def __init__(self, step, session, base, div):` | Starts the constructor. `step` is the step name, `session` is 1 or 2, `base` is the base seed and `div` is the test divisor. |
| 57 | `        self.step, self.session, self.div = step, session, div` | Stores the step, the session and the test divisor in the object. |
| 58 | `        self.seed = step_seed(base, step, session)` | `seed`: the seed of this step and session, from `step_seed`. |
| 59 | `        self.rng = random.Random(self.seed)` | `rng`: a random number generator of its own for this object (`random.Random`), started with that seed. Every shuffle of the step uses it. So the order of a step depends only on the base seed, the step, the session and the fixed sequence of the calls. |
| 60 | `        self.cpus = CPUS[session]` | `cpus`: the two worker CPUs in the order of this session (line 26). |
| 61 | `        self.procs = []` | `procs`: the list of the processes of the step, in the order in which they will run. It is empty at first. |
| 63 | `    def ms(self, v):` | Starts the method `ms`. It applies the test divisor to a duration in ms. |
| 64 | `        return v // self.div` | Returns the duration divided by the test divisor, as a whole number (`//` drops the rest). Without the option `--test-divisor` the divisor is 1 and the value does not change. |
| 66 | `    def at(self, kernel_size, ms):` | Starts the method `at`. It builds the text of one phase of a trial: a kernel, a size and a duration. |
| 67 | `        return "%s:%d" % (kernel_size, self.ms(ms))` | Returns the text `KERNEL@SIZE:MS`, for example `oldread@8M:1200`. The duration is divided by the test divisor. |
| 69 | `    def trial(self, cond, prev, pfx, pred, tgt, nwin=4, count="closed", bins=0):` | Starts the method `trial`. It returns the fields of one trial. The arguments are the condition label `cond`, the previous activity `prev`, the prefix `pfx`, the predecessor `pred`, the target `tgt`, the number of target windows `nwin`, the counter mode `count` and the flag `bins`. When the caller leaves the last three out, they are 4 windows, the mode `closed` and no bins (0). |
| 70 | `        return (cond, prev, pfx, pred, tgt, nwin, self.ms(300), count, bins)` | Returns a tuple of 9 fields in the order of a plan line: the label, the three phases before the target, the target, the number of windows, the window length, the counter mode and the bins flag. The window length is always 300 ms, divided by the test divisor. |
| 72 | `    def same_kernel_trial(self, cond, ks, count="closed", bins=0):` | Starts the method `same_kernel_trial`. It builds a trial in which the target kernel is also the prefix. `ks` is the text `KERNEL@SIZE`. |
| 73 | `        # The target kernel is its own 1.2 s prefix (design line 207).` | Comment: the target kernel is its own prefix of 1.2 s. The comment gives the place in the design as `design line 207`. That place describes the trials of step `S2`: a prefix of 1.2 s of the kernel itself, then four target windows of 0.3 s. |
| 74 | `        return self.trial(cond, "-", self.at(ks, 1200), "-", ks, 4, count, bins)` | Returns the trial: no previous activity (`-`), a prefix of 1200 ms of `ks`, no predecessor (`-`), and the target `ks` with 4 windows of 300 ms. So without a test divisor one such trial has 2400 ms of nominal kernel work. |
| 76 | `    def add(self, tag, cpu, nbytes, keys, trials):` | Starts the method `add`. It appends one process with a plan file to the list `procs`. |
| 77 | `        self.procs.append({"tag": tag, "cpu": cpu, "bytes": nbytes,` | Appends a dictionary with the tag, the worker CPU, the buffer size in bytes, the header pairs `keys` and the list of trials. `keys` holds more pairs of a key and a value for the second line of the plan file. |
| 78 | `                           "keys": keys, "trials": trials, "args": None})` | Continues the dictionary: the entry `args` is `None`. That marks a process whose options the function `write` builds, with a plan file (lines 295 to 301). |
| 80 | `    def perm_rows(self):` | Starts the method `perm_rows`. It returns 24 rows. Each row is an order of the numbers 0, 1 and 2. |
| 81 | `        # 24 cycles: each of the six orders of three items four times, shuffled.` | Comment: the 24 rows are 24 cycles: each of the six orders of three items four times, in a shuffled sequence. |
| 82 | `        rows = PERMS * 4` | `rows`: the list `PERMS` four times in a row, that is 24 tuples. |
| 83 | `        self.rng.shuffle(rows)` | Shuffles the 24 rows with the generator of the step. So the content is balanced: each of the 6 orders occurs 4 times. Only the sequence of the rows is random. |
| 84 | `        return rows` | Returns the rows. |
| 86 | `    def williams_rows(self):` | Starts the method `williams_rows`. It returns 24 rows. Each row is an order of the 12 condition numbers 0 to 11. |
| 87 | `        # Design line 242: 12 shifted rows, random relabel, two copies, shuffled.` | Comment: the construction that the design gives for step `S3` (`Design line 242`): 12 shifted rows, a random new numbering of the conditions, two copies, and a shuffle of the rows. |
| 88 | `        label = list(range(12))` | `label`: the numbers 0 to 11 in order. |
| 89 | `        self.rng.shuffle(label)` | Shuffles `label`. Entry `x` is now the condition that takes the place of the number `x` of the construction. This is the random new numbering. |
| 90 | `        rows = [[label[(x + r) % 12] for x in S3_START] for r in range(12)] * 2` | `rows`: 12 rows, one for each shift `r` from 0 to 11. Row `r` takes each entry `x` of `S3_START`, adds `r`, takes the rest of a division by 12, and looks the result up in `label`. `* 2` then repeats the list of the 12 rows, which gives 24 rows. |
| 91 | `        self.rng.shuffle(rows)` | Shuffles the 24 rows. |
| 92 | `        return rows` | Returns the rows. |
| 94 | `    def by_process(self, make_rows, emit):` | Starts the method `by_process`. `make_rows` is a method that returns 24 rows. `emit` is a function that builds one process from 4 rows. |
| 95 | `        # One saved row set per CPU. Process i takes rows 4i to 4i+3 as its cycles.` | Comment: there is one saved set of rows per CPU. Process `i` takes the rows `4i` to `4i+3` as its 4 cycles. |
| 96 | `        rows = {cpu: make_rows() for cpu in self.cpus}` | `rows`: for each CPU of the session, in the order of the session, one new set of 24 rows from `make_rows`. So the first CPU of the session draws its rows first. |
| 97 | `        for i in range(UNITS):` | Starts the loop over the 6 processes of a CPU. `i` runs from 0 to 5. |
| 98 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 99 | `                emit(i, cpu, rows[cpu][4 * i:4 * i + 4])` | Calls `emit` with the process number, the CPU and 4 rows of that CPU: the rows `4 * i` to `4 * i + 3`. So the run order is process 1 on both CPUs, then process 2 on both CPUs, and so on. |

### `Gen`: the steps `B6W`, `S2`, `S4` and `C4` (lines 101 to 148)

| Line | Source | Explanation |
|---:|---|---|
| 101 | `    # ---- steps ----` | Comment: the step methods follow. Each has the name of its step. |
| 102 | `    def B6W(self):` | Starts the method `B6W`. It builds the 4 processes of step `B6W` for this session. It uses no random number, so their order is fixed. |
| 103 | `        for i in (1, 2):` | Starts the loop over the two processes of a CPU, 1 and 2. |
| 104 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 105 | `                args = ("--threads 1 --cpus %d --seq %s --bytes 8M --rounds 4 "` | `args`: the command line options of the process, first part. `--threads 1`: one thread. `--cpus`: the worker CPU. `--seq`: the kernel sequence `B6SEQ`. `--bytes 8M`: a buffer of 8 MiB. `--rounds 4`: the runner repeats the sequence 4 times. |
| 106 | `                        "--min-ms %d --stop pass" % (cpu, B6SEQ, self.ms(300)))` | Continues the options. `--min-ms`: each timed interval lasts at least 300 ms, divided by the test divisor. `--stop pass`: the whole-pass stop, in which the thread finishes the pass over its range that it is in. The `%` operator puts in the CPU, the sequence and the duration. |
| 107 | `                self.procs.append({"tag": "cpu%d-p%d" % (cpu, i), "cpu": cpu,` | Appends the process directly to `procs`. Its tag holds the CPU and the process number, for example `cpu2-p1`. |
| 108 | `                                   "bytes": M8, "keys": [], "trials": [], "args": args})` | Continues the dictionary: a buffer size of 8 MiB, no header pairs, no trials, and the options in `args`. A process with `args` gets no plan file (lines 302 to 303). |
| 110 | `    def S2(self):` | Starts the method `S2`. It builds the 180 processes of step `S2` for this session: 6 replicate sets, 5 sizes, 2 CPUs and 3 kernels. |
| 111 | `        # order[size][cpu][r]: the kernel order of replicate set r+1.` | Comment: `order[size][cpu][r]` is the kernel order of the replicate set `r+1`. |
| 112 | `        order = {}` | `order`: one table of orders per size and CPU, empty at first. |
| 113 | `        for s in S2_SIZES:` | Starts a loop over the five sizes, in the fixed order of `S2_SIZES`. |
| 114 | `            for cpu in self.cpus:` | Starts a loop over the two CPUs, in the order of the session. |
| 115 | `                p = list(PERMS)` | `p`: a copy of the list of the 6 orders of the three kernels. |
| 116 | `                self.rng.shuffle(p)` | Shuffles the copy with the generator of the step. |
| 117 | `                order[s, cpu] = p` | Stores the shuffled list for this size and CPU. Entry `r` is the kernel order of the replicate set `r+1`. So the 6 replicate sets of a size and CPU use each of the 6 orders exactly once. Each kernel is then the first of its set 2 times, the second 2 times and the third 2 times. |
| 118 | `        for r in range(UNITS):` | Starts the loop over the 6 replicate sets. `r` runs from 0 to 5. |
| 119 | `            sizes = list(S2_SIZES)` | `sizes`: a copy of the list of the five sizes for this replicate set. |
| 120 | `            self.rng.shuffle(sizes)` | Shuffles the copy. So each replicate set has its own random order of the sizes. |
| 121 | `            for s in sizes:` | Starts the loop over the sizes in that order. |
| 122 | `                for cpu in self.cpus:` | Starts the loop over the CPUs in the order of the session. All processes of the first CPU at this size come before those of the second CPU. |
| 123 | `                    for ki in order[s, cpu][r]:` | Starts the loop over the kernels, in the order that row `r` of the table of this size and CPU gives. `ki` is the number of a kernel. |
| 124 | `                        k = KERNELS[ki]` | `k`: the name of the kernel with the number `ki`. |
| 125 | `                        cond = "K=%s\|S=%s" % (k, s)` | `cond`: the condition label of the trials. It names the kernel and the size, for example `K=read\|S=8M`. |
| 126 | `                        t = [self.same_kernel_trial(cond, "%s@%s" % (k, s))] * 4` | `t`: the 4 trials of the process. `* 4` repeats the one trial four times. Each trial is a prefix of 1200 ms and 4 target windows of 300 ms of the same kernel on the same size. So a process has 9600 ms of nominal kernel work. |
| 127 | `                        self.add("r%d-%s-cpu%d-%s" % (r + 1, s, cpu, k), cpu, size_bytes(s),` | Appends the process. Its tag holds the replicate set, the size, the CPU and the kernel, for example `r1-8M-cpu2-read`. The buffer size of the process is the size `s` in bytes. |
| 128 | `                                 [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s))], t)` | The header pairs of the plan: the replicate set (`rep_set`, counted from 1), the kernel and the size in bytes. The last argument is the list of trials. |
| 130 | `    def sustained(self, count):` | Starts the method `sustained`. It builds the 18 processes of a sustained step for this session: 3 passes, 2 CPUs and 3 kernels. `count` is the counter mode of the trials. |
| 131 | `        for i in range(3):` | Starts the loop over the 3 passes. `i` runs from 0 to 2. |
| 132 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 133 | `                ks = list(KERNELS)` | `ks`: a copy of the list of the three kernels. |
| 134 | `                self.rng.shuffle(ks)` | Shuffles the copy. So each pass on each CPU has its own random order of the three kernels. This order is not balanced. |
| 135 | `                for k in ks:` | Starts the loop over the kernels in the shuffled order. |
| 136 | `                    cond = "K=%s\|S=8M" % k` | `cond`: the condition label, for example `K=asmread\|S=8M`. |
| 137 | `                    if count != "closed":` | Tests whether the counter mode is another one than `closed`. |
| 138 | `                        cond += "\|count=%s" % count` | If so: adds the mode to the label, for example `K=asmread\|S=8M\|count=read`. |
| 139 | `                    t = [self.trial(cond, "-", "-", "-", k + "@8M", 200, count)]` | `t`: the one trial of the process. It has no previous activity, no prefix and no predecessor. The target is the kernel on 8 MiB with 200 windows of 300 ms. That is 60000 ms of nominal kernel work with one kernel. |
| 140 | `                    self.add("%s-cpu%d-p%d" % (k, cpu, i + 1), cpu, M8,` | Appends the process on a buffer of 8 MiB. Its tag holds the kernel, the CPU and the pass, for example `asmread-cpu2-p1`. |
| 141 | `                             [("kernel", k), ("size", M8)], t)` | The header pairs of the plan (the kernel and the size in bytes), and the trial. |
| 143 | `    def S4(self):` | Starts the method `S4`, the sustained step without counters. |
| 144 | `        self.sustained("closed")` | Builds the step with `sustained` and the counter mode `closed`. |
| 146 | `    def C4(self):` | Starts the method `C4`, the sustained step with counters. |
| 147 | `        self.sustained("read")` | Builds the step with `sustained` and the counter mode `read`: the runner reads the counters at the boundaries of the target windows. |

### `Gen`: the steps `P3`, `P3G`, `S3G`, `S3` and `CM` (lines 149 to 204)

| Line | Source | Explanation |
|---:|---|---|
| 149 | `    def P3(self):` | Starts the method `P3`. It builds the 12 processes of step `P3` for this session. In each process the three kernels take turns on one buffer of 8 MiB. |
| 150 | `        def emit(i, cpu, cycles):` | Starts the inner function `emit`. It builds process `i` of the CPU `cpu` from its 4 rows `cycles`. |
| 151 | `            t = []` | `t`: the list of the trials of the process, empty at first. |
| 152 | `            for row in cycles:` | Starts the loop over the 4 rows of the process. |
| 153 | `                for ki in row:` | Starts the loop over the three kernel numbers of the row, in the order of the row. |
| 154 | `                    k = KERNELS[ki]` | `k`: the name of the kernel. |
| 155 | `                    t.append(self.same_kernel_trial("K=%s\|S=8M" % k, k + "@8M"))` | Appends one trial: a prefix of 1200 ms and 4 target windows of 300 ms of this kernel on 8 MiB. Its label is `K=<kernel>\|S=8M`. So a process has 12 trials, 4 per kernel. |
| 156 | `            self.add("cpu%d-p%d" % (cpu, i + 1), cpu, M8, [], t)` | Appends the process on a buffer of 8 MiB, with no header pairs. Its tag holds the CPU and the process number, for example `cpu2-p1`. |
| 157 | `        self.by_process(self.perm_rows, emit)` | Builds the processes with `by_process` and the rows of `perm_rows`. So over the 24 cycles of a CPU each of the 6 kernel orders is used 4 times, in a shuffled sequence. |
| 159 | `    def P3G(self):` | Starts the method `P3G`. It builds the 12 processes of step `P3G` for this session. By the design the step is the check of the prefix for step `P3`: each trial runs a previous activity of 2.4 s before the prefix and the target. |
| 160 | `        conds = [(j, k) for j in KERNELS for k in KERNELS]` | `conds`: the 9 pairs of a previous activity `j` and a target kernel `k`: every kernel of `KERNELS` with every kernel. |
| 161 | `        for i in range(UNITS):` | Starts the loop over the 6 processes of a CPU. |
| 162 | `            for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 163 | `                t = []` | `t`: the list of the trials of the process, empty at first. |
| 164 | `                for _ in range(4):` | Starts the loop over the 4 cycles of the process. The loop variable `_` is not used. |
| 165 | `                    cyc = list(conds)` | `cyc`: a copy of the list of the 9 pairs. |
| 166 | `                    self.rng.shuffle(cyc)` | Shuffles the copy. So each cycle has its own random order of the 9 conditions. This order is not balanced. |
| 167 | `                    for j, k in cyc:` | Starts the loop over the pairs in the shuffled order. |
| 168 | `                        t.append(self.trial("J=%s\|K=%s" % (j, k), self.at(j + "@8M", 2400),` | Appends one trial. Its label is `J=<previous kernel>\|K=<target kernel>`. The previous activity is 2400 ms of the kernel `j` on 8 MiB. |
| 169 | `                                            self.at(k + "@8M", 1200), "-", k + "@8M"))` | Continues the call: a prefix of 1200 ms of the target kernel `k` on 8 MiB, no predecessor, and the target `k` on 8 MiB with 4 windows of 300 ms. So one trial has 4800 ms of nominal kernel work, and a process has 36 trials. |
| 170 | `                self.add("cpu%d-p%d" % (cpu, i + 1), cpu, M8, [], t)` | Appends the process on a buffer of 8 MiB, with no header pairs. Its tag holds the CPU and the process number. |
| 172 | `    def S3G(self):` | Starts the method `S3G`. It builds the 12 processes of step `S3G` for this session. By the design the step is the check of the old read prefix that step `S3` uses. |
| 173 | `        def emit(i, cpu, cycles):` | Starts the inner function `emit`. It builds process `i` of the CPU `cpu` from its 4 rows `cycles`. |
| 174 | `            t = []` | `t`: the list of the trials of the process, empty at first. |
| 175 | `            for row in cycles:` | Starts the loop over the 4 rows of the process. |
| 176 | `                for ji in row:` | Starts the loop over the three kernel numbers of the row. Here a number selects the kernel of the previous activity. |
| 177 | `                    j = KERNELS[ji]` | `j`: the name of the kernel of the previous activity. |
| 178 | `                    t.append(self.trial("J=%s\|K=oldread" % j, self.at(j + "@8M", 1200),` | Appends one trial. Its label is `J=<previous kernel>\|K=oldread`. The previous activity is 1200 ms of the kernel `j` on 8 MiB. |
| 179 | `                                        self.at("oldread@8M", 1200),` | Continues the call: a prefix of 1200 ms of `oldread` on 8 MiB. |
| 180 | `                                        self.at("oldread@8M", 300), "oldread@8M"))` | Continues the call: a predecessor of 300 ms of `oldread` on 8 MiB, and the target `oldread` on 8 MiB with 4 windows of 300 ms. So one trial has 3900 ms of nominal kernel work, and a process has 12 trials. |
| 181 | `            self.add("cpu%d-p%d" % (cpu, i + 1), cpu, M8, [], t)` | Appends the process on a buffer of 8 MiB, with no header pairs. Its tag holds the CPU and the process number. |
| 182 | `        self.by_process(self.perm_rows, emit)` | Builds the processes with `by_process` and the rows of `perm_rows`. So over the 24 cycles of a CPU each of the 6 orders of the three previous activities is used 4 times. |
| 184 | `    def twelve(self, cells):` | Starts the method `twelve`. It builds the 12 processes of a step with 12 conditions. `cells` is the list of the 12 conditions. |
| 185 | `        # cells: 12 tuples (cond, predecessor, target kernel, counter mode).` | Comment: each entry of `cells` is a tuple of 4 values: the condition label, the predecessor, the target kernel and the counter mode. |
| 186 | `        def emit(i, cpu, cycles):` | Starts the inner function `emit`. It builds process `i` of the CPU `cpu` from its 4 rows `cycles`. |
| 187 | `            t = []` | `t`: the list of the trials of the process, empty at first. |
| 188 | `            for row in cycles:` | Starts the loop over the 4 rows of the process. Each row is an order of the 12 condition numbers. |
| 189 | `                for c in row:` | Starts the loop over the 12 condition numbers of the row. |
| 190 | `                    cond, pred, tgt, count = cells[c]` | Takes the four values of the condition with the number `c`. |
| 191 | `                    t.append(self.trial(cond, "-", self.at("oldread@8M", 1200),` | Appends one trial: no previous activity, and a prefix of 1200 ms of `oldread` on 8 MiB. |
| 192 | `                                        self.at(pred, 300), tgt + "@8M", 4, count))` | Continues the call: the predecessor `pred` for 300 ms, the target kernel on 8 MiB with 4 windows of 300 ms, and the counter mode. So one trial has 2700 ms of nominal kernel work, and a process has 48 trials. |
| 193 | `            self.add("cpu%d-p%d" % (cpu, i + 1), cpu, M8, [], t)` | Appends the process on a buffer of 8 MiB, with no header pairs. Its tag holds the CPU and the process number. |
| 194 | `        self.by_process(self.williams_rows, emit)` | Builds the processes with `by_process` and the rows of `williams_rows`. So each CPU has its own 24 rows, and each process runs 4 of them. |
| 196 | `    def S3(self):` | Starts the method `S3`, the step with mixed sequences: a predecessor, then a target. |
| 197 | `        self.twelve([("P=%s\|T=%s" % (p, t), p, t, "closed")` | Builds the step with `twelve`. The comprehension makes the 12 conditions: each of the 4 predecessors of `S3_PREDS` with each of the 3 kernels as the target. The label is `P=<predecessor>\|T=<target>`, for example `P=oldread@1M\|T=read`. The counter mode is `closed`. |
| 198 | `                     for p in S3_PREDS for t in KERNELS])` | Continues the comprehension: the two loops, over the predecessors and inside them over the target kernels. |
| 200 | `    def CM(self):` | Starts the method `CM`, the mixed-sequence step with counters. |
| 201 | `        two = ["oldread", "read"]` | `two`: the two kernels of this step, `oldread` and `read`. |
| 202 | `        self.twelve([("P=%s@8M\|T=%s\|count=%s" % (p, t, m), p + "@8M", t, m)` | Builds the step with `twelve`. The comprehension makes the 12 conditions: each of the 3 counter modes with each of the 2 predecessors and each of the 2 targets. The predecessor runs on 8 MiB. The label is `P=<predecessor>@8M\|T=<target>\|count=<mode>`. |
| 203 | `                     for m in MODES for p in two for t in two])` | Continues the comprehension: the three loops, over the modes, the predecessors and the targets. |

### `Gen`: the helper `selected` and the steps `BIN` and `CS` (lines 205 to 238)

| Line | Source | Explanation |
|---:|---|---|
| 205 | `    def selected(self, select, make_trials):` | Starts the method `selected`. It builds the processes of a step that runs only the kernels and sizes of `--select`. `select` is the list of the pairs of a kernel and a size text. `make_trials` is a function that returns the trials of one process. |
| 206 | `        # One kernel and size per process. make_trials(i, cpu, kernel, size token).` | Comment: each process has one kernel and one size. `make_trials` gets the pass number `i`, the CPU, the kernel and the size text. |
| 207 | `        for i in range(UNITS):` | Starts the loop over 6 passes. `i` runs from 0 to 5. |
| 208 | `            sel = list(select)` | `sel`: a copy of the selection. |
| 209 | `            self.rng.shuffle(sel)` | Shuffles the copy. So each pass has its own random order of the selected pairs. This order is not balanced. |
| 210 | `            for k, s in sel:` | Starts the loop over the pairs of a kernel `k` and a size `s`, in the shuffled order. |
| 211 | `                for cpu in self.cpus:` | Starts the loop over the two CPUs, in the order of the session. |
| 212 | `                    self.add("%s-%s-cpu%d-p%d" % (k, s, cpu, i + 1), cpu, size_bytes(s),` | Appends the process. Its tag holds the kernel, the size, the CPU and the pass, for example `read-8M-cpu2-p1`. The buffer size is the size in bytes. |
| 213 | `                             [("kernel", k), ("size", size_bytes(s))],` | The header pairs of the plan: the kernel and the size in bytes. |
| 214 | `                             make_trials(i, cpu, k, s))` | The last argument: the trials that `make_trials` returns for this process. |
| 216 | `    def BIN(self, select):` | Starts the method `BIN`. It builds the step that compares two record modes of the runner for the selected kernels and sizes. |
| 217 | `        # Modes A (window records only) and B (10 ms bins). ABBA BAAB, or its mirror.` | Comment: mode A keeps only the window records. Mode B also records bins of 10 ms inside each target window. The order of the 8 trials of a process is ABBA BAAB, or its mirror. |
| 218 | `        def trials(i, cpu, k, s):` | Starts the inner function `trials`. It returns the 8 trials of one process. |
| 219 | `            order = [0, 1, 1, 0, 1, 0, 0, 1]` | `order`: the bins flag of the 8 trials: 0, 1, 1, 0, 1, 0, 0, 1. The flag 0 is mode A and the flag 1 is mode B. |
| 220 | `            if i % 2:` | Tests whether the pass number `i` is odd. |
| 221 | `                order = [1 - b for b in order]` | If so: every flag is turned over, which gives the mirror order 1, 0, 0, 1, 0, 1, 1, 0. So the passes 2, 4 and 6 of a kernel, size and CPU start with mode B, and the passes 1, 3 and 5 start with mode A. |
| 222 | `            return [self.same_kernel_trial("K=%s\|S=%s\|bins=%d" % (k, s, b),` | Returns the 8 trials. Each is a same-kernel trial (a prefix of 1200 ms and 4 target windows of 300 ms) with the label `K=<kernel>\|S=<size>\|bins=<flag>`. |
| 223 | `                                           "%s@%s" % (k, s), "closed", b) for b in order]` | Continues the call: the kernel and the size, the counter mode `closed` and the bins flag `b`. The comprehension runs over the 8 flags of `order`. |
| 224 | `        self.selected(select, trials)` | Builds the processes with `selected`: 12 per selected pair, 6 on each CPU. |
| 226 | `    def CS(self, select):` | Starts the method `CS`. It builds the step that compares the three counter modes for the selected kernels and sizes. |
| 227 | `        rows = {(k, s, cpu): self.perm_rows() for k, s in select for cpu in self.cpus}` | `rows`: for each selected pair and each CPU, one set of 24 rows from `perm_rows`. Here the numbers 0, 1 and 2 of a row stand for the counter modes `closed`, `open` and `read`. All sets are drawn before the shuffles of `selected`. |
| 229 | `        def trials(i, cpu, k, s):` | Starts the inner function `trials`. It returns the 12 trials of one process. |
| 230 | `            t = []` | `t`: the list of the trials of the process, empty at first. |
| 231 | `            for row in rows[k, s, cpu][4 * i:4 * i + 4]:` | Starts the loop over the 4 rows of this process: the rows `4 * i` to `4 * i + 3` of the set of its kernel, size and CPU. |
| 232 | `                for mi in row:` | Starts the loop over the three mode numbers of the row. |
| 233 | `                    t.append(self.same_kernel_trial("K=%s\|S=%s\|count=%s" % (k, s, MODES[mi]),` | Appends one same-kernel trial with the label `K=<kernel>\|S=<size>\|count=<mode>`. |
| 234 | `                                                    "%s@%s" % (k, s), MODES[mi]))` | Continues the call: the kernel and the size, and the counter mode with the number `mi`. |
| 235 | `            return t` | Returns the trials. So a process runs each counter mode 4 times. Over the 24 cycles of a kernel, size and CPU each of the 6 orders of the three modes is used 4 times. |
| 236 | `        self.selected(select, trials)` | Builds the processes with `selected`: 12 per selected pair, 6 on each CPU. |

### Functions `generate`, `plan_text`, `phase_ms` and `proc_ms` (lines 239 to 282)

| Line | Source | Explanation |
|---:|---|---|
| 239 | `def generate(base, div, select):` | Starts the function `generate`. `base` is the base seed, `div` the test divisor and `select` the list of the selected kernels and sizes. |
| 240 | `    """Returns {(step, session): Gen}. BIN and CS only if select is not empty."""` | Description text: the function returns a dictionary with one `Gen` object per step and session. The steps `BIN` and `CS` are in it only when `select` is not empty. |
| 241 | `    out = {}` | `out`: the result dictionary, empty at first. |
| 242 | `    for session in (1, 2):` | Starts the loop over the two sessions. |
| 243 | `        for step in STEPS:` | Starts the loop over the steps, in the order of `STEPS`. |
| 244 | `            g = Gen(step, session, base, div)` | `g`: a new `Gen` object for this step and session. Its constructor derives the seed and starts the random number generator. |
| 245 | `            if step in ("BIN", "CS"):` | Tests whether the step is `BIN` or `CS`. |
| 246 | `                if not select:` | Tests whether the selection is empty. |
| 247 | `                    continue` | If so: skips the step. It gets no entry in the dictionary and no files. |
| 248 | `                getattr(g, step)(select)` | If not: calls the method that has the name of the step, with the selection. `getattr(g, step)` finds the method by its name. |
| 249 | `            else:` | The other case: every step other than `BIN` and `CS`. |
| 250 | `                getattr(g, step)()` | Calls the method that has the name of the step. It fills the list `g.procs`. |
| 251 | `            out[step, session] = g` | Stores the object. |
| 252 | `    return out` | Returns the dictionary. |
| 255 | `def plan_text(g, idx, p):` | Starts the function `plan_text`. It returns the text of the plan file of one process. `g` is the object of the step, `idx` the number of the process and `p` its dictionary. |
| 256 | `    pairs = [("step", g.step), ("session", g.session), ("cpu", p["cpu"]),` | `pairs`: the pairs of the second header line, first part: the step, the session and the worker CPU. |
| 257 | `             ("bytes", p["bytes"]), ("proc", idx)] + p["keys"] + \` | Continues the list: the buffer size in bytes and the process number `proc`. Then come the header pairs of the process itself (`keys`). |
| 258 | `            [("seed", g.seed), ("test", 0 if g.div == 1 else 1)]` | Continues the list: the seed of the step and session, and `test`. `test` is 0 without a test divisor and 1 with one. |
| 259 | `    lines = ["# bwx8-plan v1",` | `lines`: the lines of the plan file. The first one is exactly `# bwx8-plan v1`, the name and the version of the format. |
| 260 | `             "# " + " ".join("%s=%s" % kv for kv in pairs),` | The second one: `#` and all pairs in the form `key=value`, with blanks between them. |
| 261 | `             "# trial cond rep prev pfx pred tgt nwin win_ms count bins"]` | The third one: the names of the 11 fields of a trial line. |
| 262 | `    seen = {}` | `seen`: how many times each condition label has occurred so far in this process. It is empty at first. |
| 263 | `    for n, t in enumerate(p["trials"]):` | Starts the loop over the trials. `n` is the trial number, counted from 0. |
| 264 | `        seen[t[0]] = seen.get(t[0], 0) + 1      # rep: repeat number of this cond` | Counts the label of this trial (`t[0]`). By the comment the count is the field `rep`: the repeat number of this condition in the process, counted from 1. |
| 265 | `        lines.append("%d %s %d %s %s %s %s %d %d %s %d" % ((n, t[0], seen[t[0]]) + t[1:]))` | Adds the trial line with 11 fields that blanks separate: the trial number, the label, the repeat number, the previous activity, the prefix, the predecessor, the target, the number of windows, the window length in ms, the counter mode and the bins flag. |
| 266 | `    return "\n".join(lines) + "\n"` | Returns the lines as one text, each with a newline at its end. |
| 269 | `def phase_ms(tok):` | Starts the function `phase_ms`. It returns the duration of one phase text in ms. |
| 270 | `    return 0 if tok == "-" else int(tok.split(":")[1])` | Returns 0 for the text `-`, which stands for no phase. For a text `KERNEL@SIZE:MS` it returns the number after the colon. |
| 273 | `def proc_ms(p):` | Starts the function `proc_ms`. |
| 274 | `    """Nominal kernel work of one process, in ms."""` | Description text: the function returns the nominal kernel work of one process in ms. |
| 275 | `    if p["args"]:` | Tests whether the process has options of its own in `args`. Only the processes of step `B6W` have them. |
| 276 | `        a = p["args"].split()` | `a`: the options, split at the blanks into words. |
| 277 | `        get = lambda o: a[a.index(o) + 1]` | `get`: a small function that returns the word after the option `o`. |
| 278 | `        return len(get("--seq").split(",")) * int(get("--rounds")) * int(get("--min-ms"))` | Returns the number of entries of the kernel sequence times the rounds times the `--min-ms` value. For `B6W` that is 13 times 4 times 300 ms, which is 15600 ms. |
| 279 | `    return sum(phase_ms(t[1]) + phase_ms(t[2]) + phase_ms(t[3]) + t[5] * t[6]` | For a process with a plan: returns the sum over its trials of four parts. The first three are the durations of the previous activity (`t[1]`), of the prefix (`t[2]`) and of the predecessor (`t[3]`). The fourth is the number of windows times the window length (`t[5] * t[6]`). The sum holds planned durations only. It is not a measured time. |
| 280 | `               for t in p["trials"])` | Continues the expression: the loop over the trials of the process. |

### Function `write`: the plan files, the schedule files and `MANIFEST.txt` (lines 283 to 310)

| Line | Source | Explanation |
|---:|---|---|
| 283 | `def write(gens, out, manifest):` | Starts the function `write`. It writes all files into the folder `out`. `manifest` is the text of the file `MANIFEST.txt`. |
| 284 | `    os.makedirs(out, exist_ok=True)` | Creates the output folder when it does not exist. |
| 285 | `    for session in (1, 2):` | Starts a loop over the two sessions. |
| 286 | `        shutil.rmtree(os.path.join(out, "s%d" % session), ignore_errors=True)` | Removes the folder `s1` or `s2` with everything in it. A folder that does not exist gives no error. So no file of an older run stays in these folders. |
| 287 | `    for (step, session), g in gens.items():` | Starts the loop over all steps and sessions. |
| 288 | `        sdir = os.path.join(out, "s%d" % session)` | `sdir`: the folder of the session. |
| 289 | `        rows = ["idx\ttag\tcpu\tbytes\tplan\targs"]` | `rows`: the rows of the schedule file. The first row holds the six column names, with tabs between them. |
| 290 | `        if g.procs[0]["args"] is None:` | Tests whether the first process of the step has no options of its own. Then the step has plan files. |
| 291 | `            os.makedirs(os.path.join(sdir, step))` | If so: creates the folder of the plan files, `s<session>/<step>`, and with it the session folder. |
| 292 | `        else:` | The other case, which is step `B6W`. |
| 293 | `            os.makedirs(sdir, exist_ok=True)` | Creates only the session folder. `exist_ok=True`: no error when another step has created it before. |
| 294 | `        for idx, p in enumerate(g.procs):` | Starts the loop over the processes, in the order in which they will run. `idx` counts from 0. |
| 295 | `            if p["args"] is None:` | Tests whether the process gets a plan file. |
| 296 | `                name = "%04d.plan" % idx` | `name`: the name of the plan file: the `idx` with 4 digits and the ending `.plan`, for example `0017.plan`. |
| 297 | `                with open(os.path.join(sdir, step, name), "w") as f:` | Opens the plan file in the folder of the step for writing. |
| 298 | `                    f.write(plan_text(g, idx, p))` | Writes the plan text of the process. |
| 299 | `                # The plan path is relative to the folder of run_bwx8.sh.` | Comment: the plan path in the options is relative to the folder of the run script `run_bwx8.sh`. |
| 300 | `                args = "--trial --cpus %d --bytes %d --plan sched/s%d/%s/%s" % (` | `args`: the options of the process. `--trial` selects the trial mode of the runner, `--cpus` gives the one worker CPU, `--bytes` the buffer size in bytes, and `--plan` the path of the plan file. The path always starts with `sched/`, also when `--out` names another folder. |
| 301 | `                    p["cpu"], p["bytes"], session, step, name)` | Continues the statement: the values for the CPU, the size, the session, the step and the file name. |
| 302 | `            else:` | The other case: a process with options of its own. |
| 303 | `                name, args = "-", p["args"]` | The `plan` column gets `-`, and the options are those that the step method wrote (lines 105 to 106). |
| 304 | `            rows.append("%d\t%s\t%d\t%d\t%s\t%s" % (idx, p["tag"], p["cpu"], p["bytes"], name, args))` | Adds the schedule row of the process: its `idx`, its tag, its CPU, its size in bytes, the name of its plan file or `-`, and its options, with tabs between them. |
| 305 | `        with open(os.path.join(sdir, step + ".tsv"), "w") as f:` | Opens the schedule file `<STEP>.tsv` of the step for writing. |
| 306 | `            f.write("\n".join(rows) + "\n")` | Writes all rows, each with a newline at its end. |
| 307 | `    with open(os.path.join(out, "MANIFEST.txt"), "w") as f:` | Opens the file `MANIFEST.txt` in the output folder for writing. |
| 308 | `        f.write(manifest)` | Writes the manifest text. |

### Balance checks: `cycles_by_cpu`, `williams_ok`, `s2_orders_ok` (lines 311 to 343)

| Line | Source | Explanation |
|---:|---|---|
| 311 | `def cycles_by_cpu(g, n):` | Starts the function `cycles_by_cpu`. It cuts the trials of each process of the step `g` into rows of `n` trials. |
| 312 | `    """{cpu: rows}, a row being the cond labels of n successive trials of a process."""` | Description text: the function returns a dictionary with the rows of each CPU. A row is the list of the condition labels of `n` trials that follow each other in one process. |
| 313 | `    rows = {}` | `rows`: the result, empty at first. |
| 314 | `    for p in g.procs:` | Starts the loop over the processes in schedule order. |
| 315 | `        c = [t[0] for t in p["trials"]]` | `c`: the condition labels of all trials of the process, in order. |
| 316 | `        rows.setdefault(p["cpu"], []).extend(c[i:i + n] for i in range(0, len(c), n))` | Appends the rows of this process to the list of its CPU: slices of `n` labels each. `setdefault` creates the list of a CPU at its first use. |
| 317 | `    return rows` | Returns the dictionary. |
| 320 | `def williams_ok(rows):` | Starts the function `williams_ok`. It tests the two balance rules of the design for the rows of one CPU. |
| 321 | `    """Design line 242: every ordered pair of distinct conditions twice as neighbours` | Description text, first part: by the design (`Design line 242`), every ordered pair of two different conditions must be neighbours twice inside the rows. |
| 322 | `    inside rows, and every condition twice at every position."""` | Continues the description text: and every condition must stand twice at every position of a row. |
| 323 | `    pairs, pos = {}, {}` | `pairs`: how often each ordered pair of neighbours occurs. `pos`: how often each condition stands at each position. Both are empty at first. |
| 324 | `    for row in rows:` | Starts the loop over the rows. |
| 325 | `        for i, c in enumerate(row):` | Starts the loop over the conditions of a row. `i` is the position, counted from 0, and `c` is the label. |
| 326 | `            pos[c, i] = pos.get((c, i), 0) + 1` | Counts the condition `c` at the position `i`. |
| 327 | `            if i:` | Tests whether the condition is not the first one of its row. |
| 328 | `                pairs[row[i - 1], c] = pairs.get((row[i - 1], c), 0) + 1` | If so: counts the ordered pair of the condition before it in the same row and `c`. A pair across the end of one row and the start of the next row is not counted. |
| 329 | `    return (len(rows) == 24 and len(pairs) == 132 and set(pairs.values()) == {2},` | Returns two results. The first is true when there are exactly 24 rows and 132 different pairs, and every pair occurs exactly 2 times. 132 is 12 times 11, the number of ordered pairs of two different conditions out of 12. The function does not test that the two conditions of a pair differ. |
| 330 | `            len(pos) == 144 and set(pos.values()) == {2})` | The second result is true when there are 144 different combinations of a condition and a position, and each occurs exactly 2 times. 144 is 12 times 12. |
| 333 | `def s2_orders_ok(g):` | Starts the function `s2_orders_ok`. It tests the kernel orders of step `S2`. |
| 334 | `    """Each of the six kernel orders once per size and CPU."""` | Description text: each of the six kernel orders must occur once per size and CPU. |
| 335 | `    seen = {}` | `seen`: the collected orders, empty at first. |
| 336 | `    for p in g.procs:` | Starts the loop over the processes in schedule order. |
| 337 | `        k = dict(p["keys"])` | `k`: the header pairs of the process as a dictionary. |
| 338 | `        seen.setdefault((k["size"], p["cpu"]), {}).setdefault(k["rep_set"], []).append(k["kernel"])` | Appends the kernel of the process to the list of its replicate set, inside the group of its size and CPU. So each list holds the kernels of one replicate set in the order in which they run. |
| 339 | `    return len(seen) == len(S2_SIZES) * 2 and all(` | Returns true when two things hold. First: there are 10 groups, one per size and CPU (5 sizes times 2 CPUs). The second condition follows in lines 340 to 341. |
| 340 | `        len(sets) == 6 and len({tuple(o) for o in sets.values()}) == 6` | Second, for every group: it has 6 replicate sets, and the 6 kernel orders of these sets are all different. |
| 341 | `        and all(len(o) == 3 for o in sets.values()) for sets in seen.values())` | Continues the condition: and every order holds 3 kernels. The last part is the loop over the groups. The function does not test that the 3 kernels of an order differ. |

### Function `report`: counts, nominal kernel work and the balance lines (lines 344 to 376)

| Line | Source | Explanation |
|---:|---|---|
| 344 | `def report(gens):` | Starts the function `report`. It builds the text that the program prints, and it runs the balance checks. |
| 345 | `    ok = True` | `ok`: stays true while every balance check passes. |
| 346 | `    lines = ["step session processes trials nominal_kernel_work_s"]` | `lines`: the lines of the report. The first one is the head of the table: step, session, number of processes, number of trials, and nominal kernel work in seconds. |
| 347 | `    total = {}` | `total`: the sums of both sessions per step, empty at first. |
| 348 | `    for (step, session), g in sorted(gens.items(), key=lambda x: (STEPS.index(x[0][0]), x[0][1])):` | Starts the loop over all steps and sessions. `sorted` puts them in the order of `STEPS`, and for each step session 1 before session 2. |
| 349 | `        n, tr, ms = len(g.procs), sum(len(p["trials"]) for p in g.procs), sum(map(proc_ms, g.procs))` | `n`: the number of processes of the step. `tr`: the number of trials of all its processes. `ms`: the nominal kernel work of all its processes in ms, the sum of `proc_ms`. |
| 350 | `        lines.append("%s %d %d %d %g" % (step, session, n, tr, ms / 1000))` | Adds the table row of the step: its name, the session, `n`, `tr` and the nominal work in seconds. `%g` prints a number with at most 6 significant digits and without zeros at its end. |
| 351 | `        t = total.setdefault(step, [0, 0, 0])` | `t`: the entry of the step in `total`: three sums, each 0 at first. |
| 352 | `        t[0] += n; t[1] += tr; t[2] += ms` | Adds the processes, the trials and the ms of this session to the three sums. |
| 353 | `    lines.append("both sessions together:")` | Adds the heading of the totals: `both sessions together:`. |
| 354 | `    for step in STEPS:` | Starts the loop over the steps in the order of `STEPS`. |
| 355 | `        if step in total:` | Skips a step that was not built: `BIN` or `CS` without a selection. |
| 356 | `            n, tr, ms = total[step]` | Takes the three sums of the step. |
| 357 | `            lines.append("%s total: %d processes, %d trials, nominal kernel work %g s (%g min)"` | Adds the total line of the step: the processes, the trials, and the nominal kernel work in seconds and in minutes. |
| 358 | `                         % (step, n, tr, ms / 1000, round(ms / 60000, 2)))` | Continues the statement: the values. The minutes are rounded to 2 decimal places. |
| 359 | `    lines.append("balance:")` | Adds the heading of the balance part. |
| 360 | `    for (step, session), g in sorted(gens.items(), key=lambda x: (STEPS.index(x[0][0]), x[0][1])):` | Starts a second loop over all steps and sessions, in the same order as line 348. |
| 361 | `        if step in ("S3", "CM"):` | Tests whether the step is `S3` or `CM`, the two steps that `twelve` builds. |
| 362 | `            for cpu, rows in cycles_by_cpu(g, 12).items():` | Starts the loop over the CPUs. `cycles_by_cpu` with 12 gives the rows of 12 trials of each CPU: 24 rows from its 6 processes. |
| 363 | `                a, b = williams_ok(rows)` | `a`, `b`: the two results of `williams_ok` for these rows. |
| 364 | `                ok = ok and a and b` | `ok` becomes false when one of the two checks failed. |
| 365 | `                lines.append("%s session %d cpu %d: each ordered pair of distinct conditions "` | Adds the balance line of this step, session and CPU. First part of its text: each ordered pair of different conditions is neighbours twice inside the rows. |
| 366 | `                             "is neighbours twice inside rows: %s; every condition is twice "` | Continues the text: the place of the first result, and the words for the second check: every condition is twice at every position. |
| 367 | `                             "at every position: %s" % (step, session, cpu,` | Continues the statement: the last piece of the text with the place of the second result, then the values for the step, the session and the CPU. |
| 368 | `                                                        "yes" if a else "NO", "yes" if b else "NO"))` | Continues the statement: the two results as words: `yes` when a check passed, `NO` when it failed. |
| 369 | `        if step == "S2":` | Tests whether the step is `S2`. |
| 370 | `            a = s2_orders_ok(g)` | `a`: the result of `s2_orders_ok` for this session. |
| 371 | `            ok = ok and a` | `ok` becomes false when the check failed. |
| 372 | `            lines.append("S2 session %d: each kernel order once per size and CPU: %s"` | Adds the balance line of `S2`: each kernel order once per size and CPU, with `yes` or `NO`. |
| 373 | `                         % (session, "yes" if a else "NO"))` | Continues the statement: the session and the word. |
| 374 | `    return "\n".join(lines) + "\n", ok` | Returns the report text and the result of all checks. |

### Function `parse_select`: read the option `--select` (lines 377 to 392)

| Line | Source | Explanation |
|---:|---|---|
| 377 | `def parse_select(text):` | Starts the function `parse_select`. It reads the text of the option `--select`. |
| 378 | `    sel = []` | `sel`: the list of the selected pairs, empty at first. |
| 379 | `    for item in filter(None, text.split(",")):` | Starts the loop over the entries, which commas separate. `filter(None, ...)` drops empty entries. So an empty text gives no entry. |
| 380 | `        k, _, s = item.partition("@")` | Splits the entry at the first `@`: `k` is the kernel name and `s` the size text. `_` takes the `@` and is not used. |
| 381 | `        try:` | Starts a block that catches an error. |
| 382 | `            b = size_bytes(s)` | `b`: the size in bytes. |
| 383 | `        except ValueError:` | Catches the error of a size text that is not a number. |
| 384 | `            b = 0` | Then `b` is 0, which the next line rejects. |
| 385 | `        if k not in KERNELS or b <= 0 or b % 256:` | Tests the entry. The kernel must be one of `KERNELS`. The size must be above 0 and a multiple of 256 bytes: `b % 256` is the rest of a division by 256. |
| 386 | `            sys.exit("bad --select entry '%s': use KERNEL@SIZE, kernels %s" % (item, KERNELS))` | If not: prints `bad --select entry` with the entry and the allowed kernels to the error output and ends the program with exit status 1. |
| 387 | `        if (k, s) in sel:` | Tests whether the same pair is already in the list. |
| 388 | `            sys.exit("--select names '%s' twice" % item)` | If so: prints that `--select` names the entry twice and ends the program with exit status 1. |
| 389 | `        sel.append((k, s))` | Adds the pair of the kernel name and the size text. |
| 390 | `    return sel` | Returns the list. |

### Function `main` (lines 393 to 417)

| Line | Source | Explanation |
|---:|---|---|
| 393 | `def main():` | Starts the function `main`. |
| 394 | `    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])` | Creates the reader of the command line. Its description is the first line of the description text of the file. |
| 395 | `    ap.add_argument("--seed", type=int, default=20261114, help="base seed")` | The option `--seed`: the base seed, a whole number. It is 20261114 when the option is not given. |
| 396 | `    ap.add_argument("--select", default="", help="KERNEL@SIZE,... for the steps BIN and CS")` | The option `--select`: a text of entries `KERNEL@SIZE` with commas between them, for the steps `BIN` and `CS`. It is empty when the option is not given. |
| 397 | `    ap.add_argument("--test-divisor", type=int, default=1)` | The option `--test-divisor`: the number by which every duration is divided. It is 1 when the option is not given, which changes nothing. |
| 398 | `    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sched"))` | The option `--out`: the output folder. When the option is not given, it is the folder `sched` in the folder of this file. |
| 399 | `    ap.add_argument("--report", action="store_true", help="print the report, write nothing")` | The option `--report`: a switch. With it the program prints the report and writes nothing. |
| 400 | `    a = ap.parse_args()` | Reads the command line. |
| 401 | `    if a.test_divisor < 1 or 300 % a.test_divisor:` | Tests the divisor: it must be at least 1, and 300 divided by it must leave no rest. 300 ms is the length of a window. |
| 402 | `        sys.exit("--test-divisor must divide 300 ms")` | If not, `sys.exit` with a text prints `--test-divisor must divide 300 ms` to the error output and ends the program with exit status 1. |
| 403 | `    select = parse_select(a.select)` | `select`: the list of the selected pairs, from the text of `--select`. |
| 404 | `    gens = generate(a.seed, a.test_divisor, select)` | `gens`: the processes of every step and session. |
| 405 | `    text, ok = report(gens)` | Builds the report text and runs the balance checks. |
| 406 | `    if not a.report:` | The files are written only without `--report`. |
| 407 | `        manifest = "base_seed=%d\ntest_divisor=%d\nselect=%s\n" % (a.seed, a.test_divisor, a.select)` | `manifest`: the text of `MANIFEST.txt`, first part: three lines with the base seed, the test divisor and the text of `--select`. |
| 408 | `        manifest += "".join("seed %s s%d %d\n" % (step, session, g.seed)` | Adds one line per step and session: the word `seed`, the step, the letter `s` with the session, and the seed. |
| 409 | `                            for (step, session), g in gens.items())` | Continues the expression: the loop over all steps and sessions. |
| 410 | `        write(gens, a.out, manifest)` | Writes all files into the output folder. |
| 411 | `        print("written: %s" % a.out)` | Prints `written:` and the output folder. |
| 412 | `    sys.stdout.write(text)` | Prints the report. |
| 413 | `    sys.exit(0 if ok else 1)` | Ends the program with exit status 0 when every balance check passed, and with 1 when one failed. Without `--report` the files are written in both cases. |
| 416 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 417 | `    main()` | Runs `main`. |

## References

- [Ref1] the 6 result folders `bwx8-<step>-s<session>-<UTC>` in `tests/2026-11-15-tackle-8mb/` of the repo `arm-crb`: the steps `B6W`, `S2` and `S4`, each in session 1 and 2. The files `S2.csv` and `S4.csv` hold one row `M,plan.seed` and one row `M,plan.test` per process. The seed values are 1926220671 (`S2`, session 1), 3593202156 (`S2`, session 2), 1183365339 (`S4`, session 1) and 3032361834 (`S4`, session 2). Every row `M,plan.test` has the value 0. The same two files hold one row `M,ctl_cpu,0` per process: 180 rows in each `S2.csv` and 18 rows in each `S4.csv`. The files `B6W.csv` hold no row `M,ctl_cpu`. Each folder also holds `schedule.tsv`, the copy of the schedule that ran.
