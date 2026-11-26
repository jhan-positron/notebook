## Short version: purpose

`anc4.py` reads one result folder of the counter script `rgc.sh`, taken with the watchpoint sets of `sets4.txt`. For each group of processes and each mesh it prints the mean rate of a thread, the data flits and the response flits per second that reach 4 core ports, and the share of these flits that carries each busy level from 0 to 3. The script reads the busy level from the match value of each watchpoint.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
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
- **Flit**: one unit of traffic on the mesh. The mesh moves requests, responses and data as flits.
- **Channel**: the kind of a flit. The script reads the channel number 3 as the data channel (`DAT`) and every other number as the response channel (`RSP`).
- **Core port**: a port of the mesh to which cores are joined. The watchpoints of `sets4.txt` sit at 4 of them per mesh.
- **Watchpoint**: a counter event that counts the flits of one channel at one port. A match value (`wp_val`) and a mask (`wp_mask`) choose the flits. A mask of all ones hides every bit, so every flit counts.
- **Busy level**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. This definition comes from the notes of the ASCT cross-check in the same repo.

## Main flow

1. Take the folder from the argument and the group names from the `launch` lines of `launches.txt` ({L4-5}).
2. Define the function `rows`, which reads the data rows of one `.perf` file ({L6-10}).
3. For each group, read the two runner outputs and compute the mean thread rate of each mesh ({L11-18}).
4. Read every counter file of the group. For each watchpoint row, find the mesh, the channel and the busy level, and add the count per second to the sum of that key ({L19-28}).
5. For each mesh and channel, sum the four levels and compute the share of each level ({L29-35}).
6. Print one line per group ({L36}).

## Behavior a reader must know

- The script times nothing. The bytes and the time of a thread come from the fields 6 and 7 of a `T` row. A count and the run time of its counter come from the fields 0 and 3 of a row of a `.perf` file.
- The four levels of one channel come from two counter windows (`dat01` and `dat23`, or `rsp01` and `rsp23`), which `rgc.sh` takes one after the other. So a share compares counts of two different times.
- The value after `all` comes from a third window (`datA3` or `rspA3`). The sum of the four levels and this value are counted at different times, so they need not be equal.
- The bit positions of the busy level are fixed in {L26}: a shift by 44 bits for data flits, by 28 bits for response flits.
- The counts are sums over 4 core ports of a mesh, not over all core ports.
- A row that `perf` could not count is left out of the sums. The line shows the number of such rows after `NS`.
