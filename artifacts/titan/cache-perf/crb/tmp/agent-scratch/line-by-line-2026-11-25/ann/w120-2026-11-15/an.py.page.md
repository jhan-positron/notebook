## Short version: purpose

`an.py` reads the CSV files that a runner wrote into one result folder and prints one line per timed interval. The line holds the total read, write or copy rate in GB/s, the rate and the range of the thread rates of each mesh, and each counter event per 64 B line of each mesh. It is one of the analysis scripts of the 120-thread investigation.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`T` row**: the row that the runner prints for one thread in one interval. Its fields are: `T`, round, position, kernel, thread number, CPU, bytes, time in seconds, three clock times, passes, flags.
- **`C` row**: the counter row of one thread in one interval. Its fields are: `C`, round, position, kernel, thread number, CPU, `enabled_ns`, `running_ns`, `cputime_ns`, then one count per event.
- **`I` row**: the row of one interval. Its last field is the total rate that the runner computed: the bytes of all threads divided by the longest thread time.
- **`enabled_ns`, `running_ns`**: two times in ns that Linux returns with each counter read (the runner source names them `time_enabled` and `time_running`): the time for which the counters of the thread were enabled, and the time for which they really counted.
- **Line**: one cache line, 64 B.

## Main flow

1. Take the folder and the file names from the arguments. Without file names, take every `.csv` file of the folder ({L4}).
2. For each file, read all lines: the event names from the header of the counter rows, the bytes and the time of each thread from the `T` rows, the counts from the `C` rows ({L5-12}).
3. Print the head line of the file ({L13}).
4. For each interval, compute the rate of each thread as bytes divided by time, and sum the rates per mesh and in total ({L14-23}).
5. When the file has counters: for each mesh, divide the sum of each event by the number of 64 B lines of that mesh ({L24-31}).
6. Print the line of the interval ({L32}).

## Behavior a reader must know

- The script times nothing. Every number comes from a CSV file of a runner: the bytes from field 6 and the time from field 7 of a `T` row, the counts from the fields after `cputime_ns` of a `C` row.
- The total of {L23} is the sum of the thread rates, each with its own time. The runner prints another total in its `I` row. With the common stop all threads have nearly the same time, so the two totals are close.
- A thread is put on mesh 0 or mesh 1 by its CPU number alone: below 64 or not.
- Events per line are computed per mesh: the counts of the threads of a mesh divided by the lines of the same threads. For a copy kernel a line counts once, not once for the read and once for the write.
- A `C` row with the value `NA` stops the script with an error ({L12}).
- The mark `RUN` of {L31} means that the counters did not count for the whole interval.
