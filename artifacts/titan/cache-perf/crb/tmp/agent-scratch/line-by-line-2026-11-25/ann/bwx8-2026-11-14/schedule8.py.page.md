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

1. Read the options `--seed`, `--select`, `--test-divisor`, `--out` and `--report`. End with exit status 1 when the divisor does not divide 300 ms or when an entry of `--select` is wrong ({L393-403}).
2. Build the processes of every step and session with one `Gen` object each ({L404}, {L239-252}). The constructor derives the seed of the step and session and starts its random number generator ({L56-61}).
3. Each step method fills the list of processes of its step in run order. They are called in the order of `STEPS`: `B6W` ({L102-108}), `S2` ({L110-128}), `S4` ({L143-144}), `P3G` ({L159-170}), `P3` ({L149-157}), `S3G` ({L172-182}), `S3` ({L196-198}), `BIN` ({L216-224}), `CS` ({L226-236}), `CM` ({L200-203}) and `C4` ({L146-147}).
4. Build the report text: per step and session the number of processes and trials and the nominal kernel work, then the totals of both sessions, then the results of the balance checks ({L405}, {L344-374}).
5. Without `--report`: build the text of `MANIFEST.txt`, remove the folders `s1` and `s2` of the output folder, and write the plan files, the schedule files and `MANIFEST.txt` ({L406-411}, {L283-308}).
6. Print the report. End with exit status 0, or with 1 when a balance check failed ({L412-413}).

## Behavior a reader must know

- The seed of a step and session is the first 8 hexadecimal digits of the sha256 of the text `BASE/STEP/SESSION`, read as a whole number ({L48-50}). The base seed is 20261114 unless `--seed` gives another one ({L395}).
- Each step and session has its own generator `random.Random(seed)` ({L59}). All shuffles of a step use it, in a fixed sequence. So the same options always give the same files, and session 2 has random orders of its own.
- With the base seed 20261114 this rule gives the seed 1926220671 for step `S2` in session 1 and 1183365339 for step `S4` in session 1. The output files of these two steps on CRB record the same two values in their rows `M,plan.seed` [Ref1].
- Not random: the order of the two CPUs. Session 1 always runs CPU 2 before CPU 41, and session 2 runs CPU 41 before CPU 2 ({L26}).
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
- `B6W` has a fixed order and uses no random number ({L102-108}): process 1 on both CPUs, then process 2 on both CPUs.
- How the order of `S2` is made ({L110-128}):
  - First, for each size and CPU, the list of the 6 orders of the 3 kernels is shuffled once: 5 sizes in the fixed order of `S2_SIZES`, and inside a size the 2 CPUs in the order of the session ({L113-117}). Entry `r` of the shuffled list is the kernel order of the replicate set `r+1`.
  - So this part is balanced: for each size and CPU every one of the 6 kernel orders is used exactly once. Each kernel is the first of its replicate set 2 times, the second 2 times and the third 2 times.
  - Then, for each of the 6 replicate sets, the 5 sizes are shuffled once ({L119-120}). This part is random and not balanced.
  - The run order is: replicate set, then size, then CPU, then the 3 kernels in the order of that size, CPU and replicate set.
- How the order of `S4` and `C4` is made ({L130-141}): 3 passes, inside a pass the 2 CPUs in the order of the session, and for each CPU the 3 kernels in a newly shuffled order. This order is random and not balanced.
- In the steps `P3`, `P3G`, `S3G`, `S3` and `CM` every process runs all conditions on one buffer of 8 MiB. The processes run in this order: process 1 on both CPUs, then process 2 on both CPUs, up to process 6 ({L97-99}, {L161-162}). What is random is the order of the trials inside a process:
  - `P3` and `S3G`: the method `perm_rows` gives 24 rows per CPU: each of the 6 orders of three items 4 times, in a shuffled sequence ({L80-84}). Process `i` takes the rows `4i` to `4i+3` ({L99}). So over the 6 processes of a CPU each order is used 4 times. The 4 rows of one process are not balanced.
  - `P3G`: each of the 4 cycles of a process holds the 9 conditions once, in a newly shuffled order ({L164-166}). This order is random and not balanced.
  - `S3` and `CM`: the method `williams_rows` gives 24 rows of 12 conditions per CPU ({L86-92}). It takes the start order of the design, shifts it 12 times, gives the conditions new random numbers, makes two copies and shuffles the 24 rows. Inside the rows every ordered pair of two different conditions is neighbours 2 times, and every condition stands 2 times at every position. The pairs across the end of one row and the start of the next are not balanced.
- How the order of `BIN` and `CS` is made ({L205-214}): 6 passes, inside a pass the pairs of `--select` in a newly shuffled order, and for each pair the 2 CPUs in the order of the session. In `BIN` the order of the two modes inside a process is fixed: ABBA BAAB in the passes 1, 3 and 5, and the mirror in the passes 2, 4 and 6 ({L219-221}). In `CS` the order of the three counter modes comes from `perm_rows`, one set of 24 rows per pair and CPU ({L227}).
- The program has three balance checks, and the report runs them on the finished lists of processes ({L360-373}): the kernel orders of `S2` ({L333-341}), and the two rules of the rows of `S3` and `CM` ({L320-330}). The other shuffled orders have no check. A failed check gives a line with `NO` and exit status 1. The files are written before the exit status is set ({L410-413}).
- The folders `s1` and `s2` of the output folder are removed before the new files are written ({L286}). With `--report` nothing is removed and nothing is written.
- The plan path in the `args` column always starts with `sched/`, also when `--out` names another folder ({L300}).
- Each process gets one worker CPU through `--cpus`, CPU 2 or CPU 41, and its buffer size through `--bytes` ({L105}, {L300}). The `args` of a process with a plan file hold no option `--ctl-cpu` for the controlling thread of the trial mode. By the note `DECISIONS-bwx8.md` that thread then uses CPU 0. The output files of `S2` and `S4` on CRB record `M,ctl_cpu,0` for every process [Ref1]. The processes of `B6W` run the interval mode, which has no such option. In that mode the source `bwx8.c` pins only the worker thread.
- The buffer size of a process is 8 MiB in every step other than `S2`, `BIN` and `CS`. There it is the size of the condition. A phase with a smaller size, such as the predecessor `oldread@1M` of `S3`, runs on the first bytes of the buffer.
- No row of a schedule holds a counter option. So for the steps `CS`, `CM` and `C4`, whose trials use the counters, the run script needs the settings `BWX_PMU_TYPE` and `BWX_EVENTS` in its environment.
- The nominal kernel work counts planned durations only ({L273-280}).
- With a test divisor N above 1 every duration is divided by N and the plans get `test=1` ({L258}). The numbers of windows and the order of the processes do not change. The rows of `B6W` have no plan and so no such mark: only their `--min-ms` value is smaller ({L106}).
- In the output files of the steps `S2` and `S4` on CRB every process has the row `M,plan.test,0` [Ref1]. So these schedules were made without a test divisor.
- The program reads no input file and starts nothing on CRB.

## References

- [Ref1] the 6 result folders `bwx8-<step>-s<session>-<UTC>` in `tests/2026-11-15-tackle-8mb/` of the repo `arm-crb`: the steps `B6W`, `S2` and `S4`, each in session 1 and 2. The files `S2.csv` and `S4.csv` hold one row `M,plan.seed` and one row `M,plan.test` per process. The seed values are 1926220671 (`S2`, session 1), 3593202156 (`S2`, session 2), 1183365339 (`S4`, session 1) and 3032361834 (`S4`, session 2). Every row `M,plan.test` has the value 0. The same two files hold one row `M,ctl_cpu,0` per process: 180 rows in each `S2.csv` and 18 rows in each `S4.csv`. The files `B6W.csv` hold no row `M,ctl_cpu`. Each folder also holds `schedule.tsv`, the copy of the schedule that ran.
