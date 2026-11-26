## Short version: purpose

`run_sudo.sh` runs the measurements on CRB that need root rights, in up to five numbered parts. Parts 1 and 2 run `homelat`, which measures the latency from each core to each part of the SLC, the last cache level. Parts 3 to 5 run `bandwidth` under `perf stat` and count events of the mesh and of one core during write and read streams.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh, CMN**: the network inside one half of the chip. It connects the cores, the SLC and the memory. Arm calls it CMN (Coherent Mesh Network).
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Mesh cache**: the word of the source for the SLC.
- **Home node**: a node of the mesh that owns a part of the memory addresses and holds one part of the SLC. Arm calls this node type HN-S. The event names of the home nodes start with `hns`.
- **Slice**: the part of the SLC that one home node holds.
- **Crosspoint**: a junction of the mesh. Cores, home nodes and other nodes are connected to its ports. The event names of a crosspoint start with `mxp`.
- **Flit**: one transfer unit on a link or a port of the mesh. The word is short for flow control unit.
- **Credit stall**: a cycle in which a flit cannot be sent and its sender waits for a credit from the receiver. The events whose names end with `txflit_stall` count these cycles.
- **DTC**: the debug and trace controller, the unit of the mesh that holds its counters. `dtc_cycles` is its cycle counter.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: a counter unit. `arm_cmn_0` and `arm_cmn_1` are the PMUs of the two meshes. `armv8_pmuv3_0` is the PMU of the cores.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events.
- **Event set**: the events that one `perf stat` run counts. The script keeps each set within the number of counters that the hardware has.
- **Multiplexed**: Linux lets several events use the same hardware counter one after the other. A multiplexed event does not count the whole time.
- **Idle control**: a run of `perf stat` over `sleep 2`. It gives the counts of 2 s without a benchmark.
- **`homelat`**: the program built from `homelat.c`. It finds the home node of each line of a buffer and times a pointer chase from each core to the lines of each home node.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`asmread`, `asmwrite`**: two kernels of `bandwidth` that are written in assembly. `asmread` only loads, and `asmwrite` only stores.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Process group**: a set of processes that one signal can reach together.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Set the shell options and start the script again under `taskset -c 0-119` ({L23-26}).
2. Stop with exit status 4 when the user is not root. Stop with exit status 3 when the marker file exists ({L27-30}, {L48}).
3. Create the result folder in the home folder of the user who called `sudo`. Set the command that gives the files back to that user at the end. Send all later output to `log.txt` too, and build the programs ({L49-56}).
4. Read `PARTS`, the list of the parts to run. The default is the parts 1 to 4 ({L57-58}).
5. Part 1: the self-test of `homelat` with a buffer of 16 MiB from CPU 3. Then print the number of home nodes per mesh from `nodes.csv`, and the files `chunks.csv` and `verify.csv` ({L60-67}).
6. Part 2: the full run of `homelat` with a buffer of 32 MiB from the CPUs 0 to 119 ({L69-73}).
7. Part 3: for 5 event sets an idle control, and then 9 cases of `asmwrite` and `asmread`. The function `counted` runs each case once short and once long under each event set ({L91-103}).
8. Part 4: for 4 event sets an idle control, and then 3 cases with 64 threads on one mesh or split over both meshes ({L105-119}).
9. Part 5, only when `PARTS` holds `5`: check that all event names exist, build 9 event sets for the mesh, one crosspoint and CPU 2, run an idle control per set, and then run 6 cases around CPU 2. The function `counted2` runs each case once short and once long under each set ({L133-179}).
10. Print the time and the path of the result folder ({L180}).

## Behavior a reader must know

- The script times nothing itself. The times and rates come from `homelat` and `bandwidth`. The counts come from `perf stat`.
- The function `guard` starts every measurement. It runs the command in a process group of its own and looks for the marker file once per 5 s. When the file appears, it sends the termination signal to the group, waits 1 s, sends the kill signal, and ends the script with exit status 3 ({L34-47}).
- `guard` also looks only once per 5 s whether the command has ended. So up to 5 s pass between the end of one measurement and the start of the next one.
- Exit statuses of the script: 3 for the marker file, 4 when the user is not root, 5 when an event name of part 5 does not exist. Every other failed command ends the script with the status of that command (option `-e`). A failed check of `homelat` is such a case, with status 2.
- A short run asks `bandwidth` for one timed interval of at least 200 ms, and a long run for one of at least 2000 ms. `perf stat` counts for the whole `bandwidth` process, also for the first write of the buffers and the warm-up. The analysis scripts `subtract.py` and `analyze_writepath.py` subtract the short run from the long run to remove that part.
- With `-a`, `perf stat` counts for the whole system. So a count of a mesh event also holds the traffic of other programs. With `-C 2` it counts on CPU 2 only.
- Thread placement: `taskset` limits everything to the CPUs 0 to 119. `bandwidth` pins thread number `i` to entry `i` of its CPU list. In part 3 the threads use the CPUs 0 to 13 at most, all on mesh 0. In part 4 the 64 threads use the CPUs 0 to 63, or the CPUs 0 to 31 and 64 to 95. In part 5 the threads use the CPUs 2, 3, 4, 6 and 8.
- `homelat` in part 1 measures from CPU 3 and in part 2 from each of the CPUs 0 to 119. In both parts it runs its classification on the CPU of the mesh PMU (file `homelat.c`).
- The header comment says that part 1 probes 512 lines again. The command of part 1 asks for 256 ({L63}).
- The trap of {L52} runs at every end of the script. It makes the user who called `sudo` the owner of the result folder and of the folder of the script.
- Files in the result folder: `log.txt`, the folders `selftest` and `full` with the output of `homelat`, `writebw.csv` (part 3), `crossmesh.csv` (part 4), `writepath.csv` (part 5), and one count file of `perf stat` per run (`perf-*.csv` and `perf5-*.csv`). In the three CSV files a line that starts with `--` names the run whose rows follow.

## References

- [Ref1] external source: manual page `perf-stat(1)` (the command runs a program and counts events. `-a` counts on all CPUs of the system. `-C` counts only on the given CPUs. `-x` sets the field separator, `-e` the events and `-o` the output file).
- [Ref2] external source: Linux kernel documentation, page `admin-guide/perf/arm-cmn` (an event counts the sum over all nodes of its type. With `bynodeid=1` and a `nodeid` it counts at one node).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/plan-2026-11-02.md`: the plan note of 2026-11-02. Its section "Part 3" names the home node events: write and read requests received, cache access and miss, fill, memory requests (local), memory requests (remote), evictions and snoop-filter hits. Its section "State at 04:15 UTC" explains the filter `hbt` (home-bound traffic).
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/perf-measurement-tech.html`: a page of the project on its measurement methods. Its section 3.4 gives the pairs of part 4: write requests with write retries, core requests with remote memory requests, gateway requests with local memory requests, and write throttles of the memory nodes with remote retries. Its word list says that the events `mxp_*_txflit_valid` count flits and that the events `mxp_*_txflit_stall` count the cycles in which a flit waited. Its section 3.4 also names the event `stall_backend_mem` as backend memory stalls.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/crb-memory-hierarchy.html`: the report page of the first tests. Its word list defines the flit (one transfer unit on a mesh link or port) and the credit stall (a sender needs one credit from the receiver for each flit, and a credit-stall cycle is one count of the link event for a stalled flit). Its paragraph that starts with "Corrected on 2026-11-11" says that the mesh cycle counter (event `dtc_cycles`) did count the mesh clock, 2.0 GHz, and that the earlier value of about 6,500 per second was what remained after `analyze_writepath.py` subtracted the count of the idle control from the cycle count.
