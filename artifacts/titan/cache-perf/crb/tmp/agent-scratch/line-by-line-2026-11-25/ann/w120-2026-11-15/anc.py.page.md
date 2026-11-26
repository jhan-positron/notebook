## Short version: purpose

`anc.py` reads one result folder of the counter script `rc.sh` and prints a table of the mesh counters. Each row is one event, each column one process, and each cell holds the count of mesh 0 and of mesh 1, divided by the number of 64 B lines that the process read during the counter window. With the mode `cyc` the counts are divided by the clock cycles of the mesh.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip. The script `rc.sh` reads it with `sudo perf stat`.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. The digit in the name is the mesh number.
- **Counter window**: the time for which one `perf stat` command of `rc.sh` counts one set of events. Its counts stand in one file `TAG.SET.perf`.
- **Tag**: the name of a process in the spec file. It is the first part of the names of its output files.
- **`I` row**: the row that the runner prints for one interval. Its last field is the total rate in GB/s: the bytes of all threads divided by the longest thread time.
- **`dtc_cycles`**: the event that `rc.sh` adds to every window. This script uses its count as the number of clock cycles of a mesh.
- **Line**: one cache line, 64 B.

## Main flow

1. Take the folder and the mode from the arguments ({L4}).
2. Read the tags of the processes from the `launch` lines of `launches.txt` ({L5-8}).
3. Read the rate of each process from the `I` rows of its CSV file ({L9-11}).
4. For each process and each counter file `TAG.s*.perf`, read every row: the mesh, the event, the count, the run time of the counter and the percentage ({L13-21}).
5. Divide each count by the number of lines of the process in that run time, or by the cycles of the mesh ({L22-25}).
6. Print the rates and the table, and a warning when a counter did not run the whole window ({L26-30}).

## Behavior a reader must know

- The script times nothing. The rate comes from the last field of an `I` row. The count comes from field 0, the run time from field 3 and the percentage from field 4 of a row of a `.perf` file.
- The number of lines is an estimate. The script takes the mean rate of the whole interval and the run time of the counter. It does not know how many bytes were read inside the window.
- Both values of a cell are divided by the lines of all threads of the process, on both meshes. So `m0` is the count of mesh 0 per line that any thread read.
- The script reads only the sets whose name starts with `s` ({L14}). These are the set names of the file `sets1.txt`.
- A process without an `I` row in its CSV file has no rate, and the script stops with an error at {L23}.
- A row that `perf` could not count is skipped without a message ({L19}).
