## Short version: purpose

`an8.py` reads the runner CSV files of one or more result folders in which the threads counted the busy-level events of their cores. For each interval and each mesh it prints the read rate in GB/s, the number of responses per 64 B line, and the share of the busy levels 0 to 3 among these responses. It fits the runs of the spec files `r8.spec` and `r8g.spec`.

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
- **Busy level**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. This definition comes from the notes of the ASCT cross-check in the same repo.
- **Response**: an answer of the mesh that a core receives. The core counts the answers of each busy level in its own event.
- **Line**: one cache line, 64 B.

## Main flow

1. For each folder of the arguments, take every `.csv` file in sorted order ({L4-5}).
2. Read the file: the bytes and the time of each thread from the `T` rows, the counts from the `C` rows ({L6-10}).
3. For each interval and each mesh, take the threads that have both kinds of row ({L11-14}).
4. Compute the rate of the mesh, its number of 64 B lines, and the sums of the first four events ({L15-18}).
5. Print one line with the rate, the responses per line and the share of each busy level ({L19}).

## Behavior a reader must know

- The script times nothing. The bytes come from field 6 and the time from field 7 of a `T` row. The counts come from the first four event columns of a `C` row.
- The script takes the first four events as the busy levels 0 to 3 without a test. A CSV file with another order of events gives numbers under the wrong names.
- The rate of a mesh is the sum of its thread rates, each with its own time.
- A share is a count divided by the sum of the four counts, not by the number of lines.
- A `C` row with the value `NA` stops the script with an error ({L10}). A mesh whose four sums are all 0 stops it with a division by zero ({L19}).
