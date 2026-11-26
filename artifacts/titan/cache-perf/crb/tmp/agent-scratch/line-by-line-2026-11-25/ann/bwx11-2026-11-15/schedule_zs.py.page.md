## Short version: purpose

`schedule_zs.py` writes the schedule and the plan files of one more step of round 4, the step `ZS`, into the schedule folder that `schedule11.py` made. Each of its 52 processes per session runs `asmread` or `oldread` at one of 13 buffer sizes for 6 s, with the counters read for each window. The order of the processes is random, from a fixed seed per session.

## Words used here

- **Round 4**: the fourth set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Z`.
- **Step `ZS`**: a step of round 4 that was added after the other steps. It measures counters at 13 buffer sizes from 1 MiB to 32 MiB.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **Process**: one start of a benchmark binary.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `ZS.tsv`. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Trial, window**: a trial is one timed sequence inside a process. A window is one timed period of the kernel inside a trial.
- **Cell**: one kernel at one buffer size.
- **Nominal kernel work**: the sum of the planned durations of all windows. The real run time of a process is longer.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Run script**: the script `run_bwx11.sh`. It starts the processes of a schedule on CRB.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Set the 13 sizes, the 2 kernels, the 6 counter events and the base number of the seeds ({L7-11}).
2. For each session, start a random number generator with the seed `BASE` plus the session number ({L14-16}).
3. For each CPU of the session, shuffle the 26 cells and write one plan file and one schedule row per cell ({L21-33}).
4. Write the files `ZS.tsv`, `ZS.bin` and `ZS.seed` of the session ({L34-41}).
5. Print the number of processes and the nominal kernel work of the session ({L42}).
6. Stop with an error unless both sessions together have 104 processes ({L44}).

## Behavior a reader must know

- The order of the processes: first all 26 cells on the first CPU of the session, then all 26 cells on the second CPU. Inside a CPU the order is one random shuffle ({L23}). Nothing is balanced beyond this: each cell runs once per CPU and session.
- The seeds are fixed: 2026111505 for session 1 and 2026111506 for session 2 ({L15}). The program has no option. So every run writes the same files.
- The program writes into `sched11/s1` and `sched11/s2` beside the other schedules. It removes no file. It replaces files of the same names.
- The program does not change `MANIFEST.txt`. The seed of the step is recorded in the file `ZS.seed` ({L40-41}) and in the second line of every plan file ({L29}).
- Each process is one trial of 20 windows of 300 ms with the counter mode `read`: 6 s of nominal kernel work ({L31}). A session has 52 processes and 312 s of nominal kernel work.
- The sizes in the plan and in the tag are plain numbers of bytes, not texts such as `8M` ({L31}, {L33}).
- `main` runs whenever the file is loaded, also as a module ({L45}).
- The test file `test_schedule11.py` does not test this program.
