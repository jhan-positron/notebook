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

1. Read the options `--seed`, `--test-divisor` and `--out`. End with exit status 1 when the divisor does not divide 100 ms ({L356-362}).
2. Build the processes of every step and session with one `Gen` object each. Each object derives its own seed with `step_seed` and starts its own random number generator ({L363}, {L217-227}, {L107-112}).
3. Each step method fills the list of processes in run order: `ZD` ({L149-165}), `ZC` ({L167-178}), `ZN` ({L180-195}), `ZM` ({L197-207}) and `ZA` ({L209-214}).
4. Build the report text: per step and session the number of processes and trials and the nominal kernel work, then the totals per session, then the result of each balance check ({L364}, {L310-352}).
5. Build the text of `MANIFEST.txt`: the base seed, the test divisor, and the seed and the binary of every step and session ({L365-368}).
6. Remove the folders `s1` and `s2` of the output folder and write the plan files, the schedule files, the `.bin` files and `MANIFEST.txt` ({L369}, {L253-274}).
7. Print the output folder and the report. End with exit status 0, or with 1 when a balance check failed ({L370-372}).

## Behavior a reader must know

- The seed of a step and session is the first 8 hexadecimal digits of the sha256 of the text `BASE/STEP/SESSION`, read as a whole number ({L84-86}). The base seed is 20261115 unless `--seed` gives another one ({L357}).
- Each step and session has its own generator `random.Random(seed)` ({L110}). All shuffles of a step use it, in a fixed sequence. So the same options always give the same files, and session 2 has random orders of its own.
- How the order of `ZD` is made ({L149-165}):
  - First one Williams square of the 6 cells is built for each size and CPU: 3 sizes in a fixed order, and inside a size the 2 CPUs in the order of the session. Each square takes two shuffles: the labels of the cells and the order of its 6 rows ({L136}, {L138}).
  - Then, for each of the 6 replicate sets, the 3 sizes are shuffled once ({L156}).
  - The run order is: replicate set, then size, then CPU, then the 6 cells in the order of row `r` of the square of that size and CPU.
  - Balanced: per size and CPU each cell stands once at each of the 6 positions, and each ordered pair of cells runs once as direct neighbours.
- How the order of `ZN` is made ({L180-195}): the same nesting as in `ZD`. In place of a Williams square, each size and CPU gets the 6 possible orders of the 3 kernels, with the rows shuffled once ({L145}). Balanced: per size and CPU each kernel stands twice at each position, and each ordered pair of kernels runs twice as direct neighbours.
- How the order of `ZC` and `ZM` is made ({L167-178}, {L197-207}): the run order is replicate 1 and then 2, inside a replicate the 2 CPUs in the order of the session, and inside a CPU all cells in a newly shuffled order (8 cells in `ZC`, 10 pads in `ZM`). Balanced: each block holds every cell once. The positions inside a block are random and not balanced.
- `ZA` has a fixed order on CPU 2 and uses no random number ({L209-214}).
- Not random: the order of the two CPUs. Session 1 always runs CPU 2 before CPU 41, and session 2 runs CPU 41 before CPU 2 ({L52}).
- The size order inside a replicate set of `ZD` and `ZN` is shuffled but not balanced.
- The program checks the balance on the finished list of processes ({L277-307}). A failed check gives a line that ends with `NO` and exit status 1. The files are written before the exit status is set ({L369-372}).
- The folders `s1` and `s2` of the output folder are removed before the new files are written ({L256}).
- The plan path in the `args` column always starts with `sched11/`, also when `--out` names another folder ({L266}).
- The nominal kernel work counts planned durations only ({L250}). The evict step of a process is not in it.
- With `--test-divisor N` every duration is divided by N and the plans get `test=1`. The numbers of windows and the order of the processes do not change.
- The program reads no input file and starts nothing on CRB.
