## Short version: purpose

`run_uncore.sh` counts events of the SLC, the last cache level, with the counters of the two meshes while a benchmark runs. It runs the pointer chase of `latency` at 12 buffer sizes, each once short and once long, and then two streaming reads of `bandwidth`. It starts only when the Linux setting `perf_event_paranoid` is 0 or below, and it stops when the marker file exists.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh, CMN**: the network inside one half of the chip. It connects the cores, the SLC and the memory. Arm calls it CMN (Coherent Mesh Network).
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Home node**: a node of the mesh that owns a part of the memory addresses and holds one part of the SLC. Arm calls this node type HN-S. The event names of the home nodes start with `hns`.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: a counter unit. Linux shows the counters of the two meshes as the PMUs `arm_cmn_0` and `arm_cmn_1`.
- **Uncore PMU**: a counter unit that does not belong to one core. Its counters count for the whole system.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events.
- **`perf_event_paranoid`**: the Linux setting that decides what a user without root rights may count.
- **Multiplexed**: Linux lets several events use the same hardware counter one after the other. A multiplexed event does not count the whole time, and `perf` prints a scaled count for it.
- **`latency`**: the program built from `latency.c`. One thread follows a cycle of pointers through a buffer (the pointer chase). The program prints the time per load in nanoseconds.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Cycle**: in `latency`, one walk through all cache lines of the buffer.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **MiB, GiB**: 1048576 bytes and 1073741824 bytes.

## Main flow

1. Set the shell options and start the script again under `taskset -c 0-119` ({L9-12}).
2. Stop when the marker file exists ({L13-16}).
3. Stop with exit status 4 when `perf_event_paranoid` is above 0 ({L17-18}).
4. Create the result folder, send all later output to `log.txt` too, and build the programs ({L19-23}).
5. Build the event list: 7 events of the home nodes on each of the two meshes ({L24-30}).
6. For each of 12 buffer sizes: run `latency` on CPU 3 under `perf stat`, first short and then long ({L33-40}).
7. Run `bandwidth` under `perf stat` twice: 14 reading threads with 8 MiB each, then 64 reading threads with 256 MiB each ({L42-47}).
8. Print the path of the result folder ({L48}).

## Behavior a reader must know

- The script times nothing itself. The times come from `latency` and `bandwidth`. The counts come from `perf stat`.
- `perf stat -a` counts for the whole system from the start to the end of the benchmark process. So a count also holds the events of other programs, and it holds the build of the buffer and the warm-up of the benchmark. The short and the long run of a size exist to subtract the build and the warm-up.
- The script asks for 7 events per mesh in one `perf stat` run. In the result files of the run of 2026-10-30, 2 of 364 event rows show 100.00 in the field for the share of the running time. The other rows show 0 to 58 percent, and 10 rows hold `<not counted>` in place of a count [Ref3]. So the events were multiplexed in that run, and its counts are scaled values [Ref1].
- The comment of {L31} says that the short run has 2 cycles. For the sizes 1 MiB, 8 MiB and 16 MiB the short run does one chunk of 1048576 loads, which is 64, 8 and 4 cycles.
- Marker checks: once at the start, once before the two runs of each size, and once before each `bandwidth` run. A check that finds the file ends the script with exit status 3. A process that already runs is not stopped.
- With the option `-e` a failed `make` or a failed `perf stat` ends the script with the status of that command.
- Thread placement: `taskset` limits everything to the CPUs 0 to 119. `latency` pins its one thread to CPU 3. `bandwidth` pins thread number `i` to entry `i` of the list `0-119`: 14 threads use the CPUs 0 to 13, and 64 threads use the CPUs 0 to 63.
- Files in the result folder: `log.txt`, `chase-short.csv` and `chase-long.csv` (output of `latency`), `cmn-SIZE-short.csv` and `cmn-SIZE-long.csv` per size (counts), `bw-8M-14T.csv` and `bw-256M-64T.csv` (output of `bandwidth`), and `cmn-bw-8M-14T.csv` and `cmn-bw-256M-64T.csv` (counts).

## References

- [Ref1] external source: manual page `perf-stat(1)` (the command runs a program and counts events. `-a` counts on all CPUs of the system. The fields of an output line with `-x` are the count, the unit, the event name, the running time of the counter and the share of the measurement time for which the counter was running. The option `--no-scale` turns the scaling of the counts off).
- [Ref2] external source: Linux kernel documentation, page `admin-guide/perf/arm-cmn` (an event counts the sum over all nodes of its type, unless `bynodeid` and `nodeid` select one node).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/uncore-20261030T203537Z`: a result folder with the file names of this script, started on 2026-10-30 at 20:35 UTC. Its 26 files `cmn-*.csv` hold 364 event rows. 2 rows show 100.00 in the fifth field, the share of the running time. The other rows show 0.00 to 58.00, and 10 rows hold `<not counted>` in the first field (counted with a script on 2026-11-25).
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/plan-2026-11-02.md`: the plan note of 2026-11-02. Its section "Part 3" names the home node events: write and read requests received, cache access and miss, fill, memory requests (local), memory requests (remote), evictions and snoop-filter hits.
