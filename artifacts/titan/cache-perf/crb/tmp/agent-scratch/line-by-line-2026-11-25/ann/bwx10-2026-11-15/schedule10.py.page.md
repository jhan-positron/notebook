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

1. Read the options `--seed`, `--test-divisor` and `--out`. End with exit status 1 when the divisor does not divide 100 ms ({L296-302}).
2. Build the processes of every step and session with one `Gen` object each. Each object derives its own seed with `step_seed` and starts its own random number generator ({L303}, {L183-193}, {L91-96}).
3. Each step method fills the list of processes of its step in run order. They are called in the order of `STEPS`: `YA` ({L175-180}), `YL` ({L126-135}), `YP` ({L137-146}), `YF` ({L148-163}) and `YC` ({L165-173}).
4. Build the report text: per step and session the number of processes and trials and the nominal kernel work, then the totals per session, then the result of each balance check ({L304}, {L263-292}).
5. Build the text of `MANIFEST.txt`: the base seed, the test divisor, and the seed and the binary of every step and session ({L305-308}).
6. Remove the folders `s1` and `s2` of the output folder and write the plan files, the schedule files, the `.bin` files and `MANIFEST.txt` ({L309}, {L219-240}).
7. Print the output folder and the report. End with exit status 0, or with 1 when a balance check failed ({L310-312}).

## Behavior a reader must know

- The seed of a step and session is the first 8 hexadecimal digits of the sha256 of the text `BASE/STEP/SESSION`, read as a whole number ({L74-76}). The base seed is 20261115 unless `--seed` gives another one ({L297}).
- Each step and session has its own generator `random.Random(seed)` ({L94}). All shuffles of a step use it, in a fixed sequence. So the same options always give the same files, and session 2 has random orders of its own.
- The steps and their sizes, from the constants and the loops of this file:
  - `YL`: 32 processes per session, each with 30 s of nominal kernel work. Binary `bwx8`.
  - `YP`: 28 processes per session, each with 30 s. Binary `bwx10`.
  - `YF`: 288 processes per session, each with 9.6 s. Binary `bwx10`.
  - `YC`: 42 processes per session, each with 6 s. Binary `bwx10`.
  - `YA`: 9 processes in session 1 only, each with 1.3 s. Binary `bwx10`.
- How the order of `YF` is made ({L148-163}):
  - First one Williams square of the 6 kernels is built for each size and CPU: 4 sizes in a fixed order, and inside a size the 2 CPUs in the order of the session. Each square takes two shuffles: the labels of the kernels and the order of its 6 rows ({L120}, {L122}).
  - Then, for each of the 6 replicate sets, the 4 sizes are shuffled once ({L155}).
  - The run order is: replicate set, then size, then CPU, then the 6 kernels in the order of row `r` of the square of that size and CPU.
  - Balanced: per size and CPU each kernel stands once at each of the 6 positions, and each ordered pair of kernels runs once as direct neighbours.
- How the order of `YL` and `YP` is made ({L126-135}, {L137-146}): the run order is replicate 1 and then 2, inside a replicate the 2 CPUs in the order of the session, and inside a CPU all conditions in a newly shuffled order (8 in `YL`, 7 in `YP`). Balanced: each block holds every condition once. The positions inside a block are random and not balanced.
- How the order of `YC` is made ({L165-173}): all 21 cells run on the first CPU of the session, then all 21 cells on the second CPU. Each CPU has its own shuffled order. The step has no balance check.
- `YA` has a fixed order on CPU 2 and uses no random number ({L175-180}).
- Not random: the order of the two CPUs. Session 1 always runs CPU 2 before CPU 41, and session 2 runs CPU 41 before CPU 2 ({L44}).
- The size order inside a replicate set of `YF` is shuffled but not balanced.
- The program checks the balance on the finished list of processes ({L243-260}). A failed check gives a line that ends with `NO` and exit status 1. The files are written before the exit status is set ({L309-312}).
- The folders `s1` and `s2` of the output folder are removed before the new files are written ({L222}).
- The plan path in the `args` column always starts with `sched10/`, also when `--out` names another folder ({L232}).
- Each process gets one worker CPU through `--cpus`, CPU 2 or CPU 41, and its buffer size through `--bytes` ({L232}). The `args` hold no option for the controlling thread of the runner. By the note `DECISIONS-bwx8.md` that thread then uses CPU 0.
- The nominal kernel work counts planned durations only ({L216}).
- With `--test-divisor N` every duration is divided by N and the plans get `test=1`. The numbers of windows and the order of the processes do not change.
- The program reads no input file and starts nothing on CRB.
