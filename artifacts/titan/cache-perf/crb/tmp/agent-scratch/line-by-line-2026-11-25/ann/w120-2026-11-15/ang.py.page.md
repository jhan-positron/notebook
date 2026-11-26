## Short version: purpose

`ang.py` reads one result folder of the script `rg.sh`, which runs groups of processes at the same time. For each group it prints one line: for each process the sum and the range of its thread rates in GB/s and its earliest start time, and at the end the total of the group.

## Words used here

- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Group**: the processes of one line of the spec file, which run at the same time. The output of the item with the tag `TAG` is the file `GROUP.TAG.csv`.
- **`T` row**: the row that the runner prints for one thread in one interval. Field 3 holds the kernel, field 6 the bytes, field 7 the time in seconds, and field 9 the start time of the thread in seconds since the start of the process.

## Main flow

1. Take the folder from the argument and the group names from the `launch` lines of `launches.txt` ({L4-5}).
2. For each group, go through its output files in sorted order ({L6-8}).
3. For each file, read the `T` rows: the rate of each thread, the kernel name and the start time of each thread ({L9-12}).
4. Add one block per process to the output line, and add its rate sum to the total of the group ({L13}).
5. Print the line of the group ({L14}).

## Behavior a reader must know

- The script times nothing. The bytes, the time and the start time of a thread come from the fields 6, 7 and 9 of a `T` row.
- The rate sum of a process is the sum over every `T` row of its file. With one interval per process this is the sum of its thread rates. A file with several intervals would give the sum over all of them.
- The time after `t0=` is counted from the start of its own process. The `t0` values of two processes of a group do not share a zero point, so they do not show by themselves how far the two intervals overlap.
- The total of a group adds processes whose intervals are timed apart from each other.
- A file without a `T` row stops the script with an error ({L13}). The output of a latency probe in a folder of `r4.spec` is such a file.
