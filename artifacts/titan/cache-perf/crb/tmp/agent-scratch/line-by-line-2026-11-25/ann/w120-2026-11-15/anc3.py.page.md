## Short version: purpose

`anc3.py` reads one result folder of the counter script `rgc.sh`, in which each group has one runner process on mesh 0 and one on mesh 1. It prints a table with one column per group: the read rate of each mesh, and every mesh counter event as a count in millions per second for mesh 0 and for mesh 1. The line rate of each mesh stands in the same table, in millions of lines per second.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Group**: the processes of one line of the spec file, which run at the same time. The output of the item `m0` is the file `GROUP.m0.csv`, that of the item `m1` is `GROUP.m1.csv`.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. The digit in the name is the mesh number.
- **Counter window**: the time for which one `perf stat` command of `rgc.sh` counts one event set. Its counts stand in one file `GROUP.SET.perf`.
- **`T` row**: the row that the runner prints for one thread in one interval. Field 6 holds the bytes and field 7 the time in seconds.
- **Memory port**: a place where a mesh hands requests to the memory and takes data back.
- **Line**: one cache line, 64 B.

## Main flow

1. Take the folder from the argument and the group names from the `launch` lines of `launches.txt` ({L5-6}).
2. Define the function `rows`, which reads the data rows of one `.perf` file ({L7-11}).
3. For each group, read the two runner outputs and sum the thread rates per mesh ({L13-20}).
4. For each counter file of the group, read every row and add the count per second to the sum of its event and its mesh ({L21-28}).
5. Print the table: the head, the rates in GB/s, the rates in millions of lines per second, and one line per event ({L29-34}).

## Behavior a reader must know

- The script times nothing. The bytes and the time of a thread come from the fields 6 and 7 of a `T` row. A count and the run time of its counter come from the fields 0 and 3 of a row of a `.perf` file.
- The counts are per second, not per line. The count of a window is divided by the run time of its counter. The line rate stands in its own table line, so the division per line is left to the reader.
- The rate of a mesh is taken from the whole interval of the process. The counts are taken from one window inside that interval.
- A group with a process on one mesh only stops the script with an error at {L31}.
- A row that `perf` could not count is skipped without a message ({L25}).
- The mark `*` in a cell means that at least one counter of the cell ran for less than 99.9 % of its window.
