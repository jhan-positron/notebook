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

1. Load the older generator `schedule8.py` from the folder of this file ({L33-35}).
2. Read the options `--seed`, `--test-divisor` and `--out`. End with exit status 1 when the divisor does not divide 300 ms ({L237-243}).
3. Build the processes of every step and session with one `Gen9` object each ({L244}, {L163-173}). The constructor, which comes from `schedule8.py`, derives the seed of the step and session and starts its random number generator.
4. Each step method fills the list of processes of its step in run order. They are called in the order of `STEPS`: `XEV` ({L120-125}), `XW` ({L78-89}), `XCA`, `XCB` and `XCC` ({L91-118}), `XN` ({L127-150}) and `XF` ({L152-160}).
5. Build the report text: per step and session the number of processes and trials and the nominal kernel work, then the total of session 1, then the result of the balance check of `XN` ({L245}, {L213-233}).
6. Build the text of `MANIFEST.txt`: the base seed, the test divisor, and the seed of every step and session ({L246-248}).
7. Remove the folders `s1` and `s2` of the output folder and write the plan files, the schedule files, the `.watch` files and `MANIFEST.txt` ({L249}, {L176-197}).
8. Print the output folder and the report. End with exit status 0, or with 1 when the balance check failed ({L250-252}).

## Behavior a reader must know

- The seed of a step and session is computed in `schedule8.py` (function `step_seed`): the first 8 hexadecimal digits of the sha256 of the text `BASE/STEP/SESSION`, read as a whole number. The base seed is 20261115 unless `--seed` gives another one ({L238}).
- Each step and session has its own generator `random.Random(seed)`, made by the constructor of `Gen` in `schedule8.py`. All shuffles of a step use it, in a fixed sequence. So the same options always give the same files, and session 2 has random orders of its own.
- The steps and their sizes, from the constants and the loops of this file:
  - `XEV`: 3 processes in session 1 only, each with 0.9 s of nominal kernel work. Sum: 2.7 s.
  - `XW`: 28 processes per session. 20 have 30 s. The 8 processes of the conditions `W1` and `W2` have 33 s: 3 s of previous activity come first. Sum: 864 s.
  - `XCA`, `XCB`, `XCC`: 18 processes each per session: 12 with 30 s and 6 with 6 s. Sum: 396 s for each step.
  - `XN`: 144 processes per session, each with 9.6 s. Sum: 1382.4 s.
  - `XF`: 90 processes per session, each with 9.6 s. Sum: 864 s.
- How the order of `XW` and `XF` is made ({L78-89}, {L152-160}): the run order is the replicate (2 in `XW`, 3 in `XF`), inside a replicate the 2 CPUs in the order of the session, and inside a CPU all conditions or cells in a newly shuffled order (7 in `XW`, 15 in `XF`). So each block holds every condition or cell once. The positions inside a block are random and not balanced.
- How the order of a counter step is made ({L91-109}):
  - First, for each CPU, the three short cells are shuffled and split over the two blocks: 1 and 2, or 2 and 1 ({L96-99}).
  - The run order is block 1 and then block 2, inside a block the 2 CPUs in the order of the session, and inside a CPU the three long cells and the short cells of that block in a shuffled order.
  - So each block of a CPU holds every long cell once, and each CPU runs every short cell once per session.
- How the order of `XN` is made ({L127-150}):
  - First 6 different kernel orders are drawn for each size and CPU: 3 sizes in a fixed order, and inside a size the 2 CPUs in the order of the session. A draw is repeated until each kernel stands once or twice at each of the 4 positions ({L130-133}).
  - Then, for each of the 6 replicate sets, the 3 sizes are shuffled once ({L143}).
  - The run order is: replicate set, then size, then CPU, then the 4 kernels in the order `r` of the selection of that size and CPU.
  - The size order inside a replicate set is shuffled but not balanced.
- `XEV` has a fixed order on CPU 2 and uses no random number ({L120-125}).
- Not random: the order of the two CPUs. Session 1 always runs CPU 2 before CPU 41, and session 2 runs CPU 41 before CPU 2. The table `CPUS` of `schedule8.py` holds these orders.
- Only step `XN` has a balance check ({L200-210}, {L228}). The program runs it on the finished list of processes. A failed check gives a line that ends with `NO` and exit status 1. The files are written before the exit status is set ({L249-252}).
- The folders `s1` and `s2` of the output folder are removed before the new files are written ({L179}).
- The plan path in the `args` column always starts with `sched9/`, also when `--out` names another folder ({L189}).
- Each process gets one worker CPU through `--cpus`, CPU 2 or CPU 41, and its buffer size through `--bytes` ({L189}). The `args` hold no option for the controlling thread of the runner. By the note `DECISIONS-bwx8.md` that thread then uses CPU 0.
- The buffer size of a process is the target size. In the condition `W2` of `XW` the previous activity has the size 1 MiB inside a buffer of 8 MiB. By the note `DECISIONS-bwx8.md` a phase runs whole passes over the first bytes of the buffer, up to its size.
- The rows of the steps `XEV`, `XCA`, `XCB` and `XCC` hold the options `--pmu-type 11` and `--events` with the event set ({L92}, {L125}). So the run script needs no counter setting in its environment for the schedules of this file.
- The nominal kernel work counts planned durations only (function `proc_ms` of `schedule8.py`).
- With a test divisor N above 1 every duration is divided by N and the plans get `test=1`. The numbers of windows and the order of the processes do not change.
- The program reads no input file and starts nothing on CRB. It needs the file `schedule8.py` beside it ({L34-35}).
