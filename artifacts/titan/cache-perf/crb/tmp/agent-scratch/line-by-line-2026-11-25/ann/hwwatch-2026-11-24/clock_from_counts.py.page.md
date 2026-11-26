## Short version: purpose

`clock_from_counts.py` is an analysis script that computes clock rates from cycle counts that earlier result files already hold. For a core it divides the cycles that one thread counted in one timed interval by the time for which the counter was enabled, and for a mesh it divides the count of the mesh cycle counter by the time for which that counter ran. It prints the lowest, the median and the highest clock rate of each csv file and of each group of mesh values (one group per result folder, kernel and mesh), and it starts no benchmark.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Trial**: one measurement in the trial layout of a runner csv file. By the design note, a file of this layout comes from a process with one pinned worker thread [Ref1].
- **Tag**: the name that a run script gives to one process. It starts the names of the files of that process.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Cycle counter**: a counter that counts clock cycles. For a core it is the event `CPU_CYCLES`. For a mesh it is the event `dtc_cycles`.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Clock rate**: the frequency at which a core or a mesh runs. This script gives it in GHz, which is 1e9 cycles per second.
- **`C` row**: a row of a runner csv file that starts with `C`. It holds the counter values of one thread in one interval or trial.
- **Enabled time, running time**: two times of a counter in ns. `enabled_ns` is the time for which the counter was enabled. `running_ns` is the time for which it counted.
- **Scaled**: the word of this script for a row or a line whose counter did not run for the whole time. The script does not use such a value.
- **User mode**: the code of the program itself, in contrast to the code of the Linux kernel that works for the program.
- **`perf stat`**: a Linux tool that counts events for a time and prints the counts.
- **Median**: the middle value of a sorted list of numbers.
- **Docstring**: a text literal at the top of a Python file or function that describes it.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `main` takes the result folders from the command line. Without a folder it prints the docstring and ends with exit status 1 ({L86-88}).
2. For each folder it reads each csv file that lies directly in the folder. `core_clock` gives one clock rate per usable `C` row: the cycles divided by the enabled time ({L92-95}, {L33-56}).
3. For each folder it reads the `.perf` files. `mesh_clock` gives one clock rate per usable line of the event `dtc_cycles`, grouped by kernel and mesh. The kernel comes from `launches.txt` ({L96-97}, {L59-82}).
4. With `--json` it prints every value as JSON and ends ({L98-101}).
5. Without `--json` it prints the core table: one row per csv file with the lowest, the median and the highest clock rate, then a summary line ({L102-113}).
6. Then it prints the mesh table: one row per folder, kernel and mesh, then a summary line ({L114-125}).
7. When no file gave a value, it prints that no cycle counts were found ({L126-127}).

## Behavior a reader must know

- The script only reads result files and prints text. It starts no benchmark and writes no file.
- How a core clock rate is computed ({L53}): one value per `C` row, which is one thread in one timed interval or trial. The value is the counted cycles divided by `enabled_ns`. Cycles per ns are GHz.
- The time of this division is the enabled time of the counter in the same row. It is not the length of the timed interval that the benchmark uses for its rates.
- By the docstring, the counter counts in user mode only. So each value is a lower bound of the clock rate ({L11-12}).
- A `C` row whose `running_ns` differs from `enabled_ns` is not used, and it is counted as scaled ({L46-48}). A row whose cycle count is not a number, for example `NA`, or whose enabled time is 0 is skipped without a count ({L44-45}).
- How a mesh clock rate is computed ({L81}): one value per line of the event `dtc_cycles`. The value is the count divided by the time in ns for which the counter ran.
- A line of a `.perf` file whose share of the time is not exactly `100.00` is not used, and it is counted as scaled ({L78-79}).
- The docstring says that the output has one line per folder and kernel for the `.perf` files. The code prints one line per folder, kernel and mesh ({L96-97}).
- The output of one run of this script over the result folders of the repo is kept [Ref2]. Section 2 of the design note takes its numbers from that file [Ref1].

## References

- [Ref1] The design note of this code: the file `status/2026-11-24-hw-record-handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its section 2 describes the analysis with this script and says that the files of the test `2026-11-15-tackle-8mb` have the trial layout, with one pinned worker thread per process.
- [Ref2] The file `status/2026-11-24-hw-record-evidence/clock_from_counts.out` of the same repo: the output of the command `python3 code/hwwatch-2026-11-24/clock_from_counts.py tests/*/*`. Its first line gives the time of the run: 2026-11-25T01:38:28Z.
