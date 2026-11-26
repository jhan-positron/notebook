## Short version: purpose

`homelat.c` measures the latency of the SLC, the last cache level of the chip, from each core to the part of the SLC that each home node holds, in nanoseconds per load. It first uses the counters of the two meshes to find the home node of every 64-byte line of a buffer, and then it times pointer chases over lines of one home node only, for each core and each home node (7 timed passes by default, each over a new chain). It has one thread, needs root rights for the counters, and writes its results as CSV files.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Mesh cache**: the word of the source for the SLC.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh**: the network inside one half of the chip. It connects the cores, the SLC and the memory. The notes of the project name it Arm CMN S3.
- **Crosspoint**: a junction of the mesh. A mesh has 9 columns and 8 rows of crosspoints. Cores, home nodes and other nodes are connected to the ports of a crosspoint.
- **Home node**: a node of the mesh that owns a part of the memory addresses. Arm calls this node type HN-S.
- **Slice**: the part of the SLC that one home node holds.
- **Home of a line**: the home node that owns the address of the line.
- **Local slice, remote slice**: a slice on the mesh of the measuring core, or a slice on the other mesh.
- **Proxy**: by the comments of the source, a home node on the mesh of the core that handles a line whose home is on the other mesh.
- **Line**: a cache line, 64 bytes.
- **L1, L2**: the two caches that belong to one core.
- **L2 refill**: a line that is brought into L2 from outside.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Mesh counter**: a hardware counter of a mesh. It counts events at the nodes of the mesh, for example the requests that a home node received.
- **PMU**: a counter unit. Linux shows the counters of the two meshes as the PMUs `arm_cmn_0` and `arm_cmn_1`.
- **`perf_event_open`**: the Linux system call that opens a counter.
- **Group, leader**: counters that are opened together. One system call reads all counters of a group. The first counter of a group is its leader.
- **Multiplexed**: Linux lets several counters use the same hardware counter one after the other. A multiplexed counter does not count the whole time.
- **DTC domain**: one of the 4 parts of a mesh. Each has its own debug and trace controller (DTC) with 8 counters.
- **Classification**: the step that finds the home node of every line of the buffer.
- **Probe**: the test of one line. The line is loaded and flushed 256 times between two reads of the counters.
- **Flush**: the instruction `dc civac` removes a line from the caches.
- **Window**: the time between two reads of the counters.
- **Pointer chase**: a loop in which each load reads the address of the next load.
- **Chain**: one cycle of pointers through all lines of a set. Chain number `r` uses the 8-byte word number `r` of each line.
- **Set**: the lines that one measurement uses: lines of one home node, or the mixed set with lines of every home node.
- **Evictor**: a second buffer of 8 MiB. The program reads it to push the lines of the set out of L1 and L2.
- **Temporal prefetcher**: the part of a core that records the order of earlier cache misses and fetches the same lines in the same order again.
- **Cache-state check**: the function `verify_slices`. It counts SLC accesses, SLC misses and L2 refills during timed passes of 8 slices.
- **Page frame number**: the number of a physical memory page.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **MiB**: 1048576 bytes.

## Main flow

1. `main` sets the defaults, reads the arguments and checks the settings ({L927-961}).
2. It creates the four output files in the folder of `--out` ({L963-973}).
3. It pins the thread to the first core of the core list. Then it reserves the main buffer and the evictor buffer (`alloc_buf` asks for 2 MiB pages and fills the buffer with zeros) ({L975-988}).
4. For each mesh it reads the type number and the CPU of the PMU and the description of the event, and it finds the home nodes (`discover` tries to open a counter for each of the 65536 possible node ids) ({L990-1000}).
5. It stops unless each mesh has the expected number of home nodes, 64 by default. Then `decode_ids` splits each node id into column, row, port and device ({L1001-1010}).
6. It pins the thread to the CPU of the PMU and runs the classification (`classify` probes every line, in passes with at most 8 open counters per mesh and DTC domain) ({L1011-1018}).
7. It stops when more than 5 percent of the lines have no home. Then `verify_classification` probes random lines again with a single counter, and the program stops below 98 percent agreement ({L1019-1031}).
8. It writes `nodes.csv`, `chunks.csv` and `homes.csv`. `chunks.csv` holds, for each 2 MiB chunk, the physical page frame and the split of its lines over the two meshes ({L1036-1073}).
9. It builds the mixed set from the same number of random lines of every home node, and it reports the home nodes with too few lines ({L1075-1103}).
10. Cache-state check: `verify_slices` measures 8 slices from the first core with counters open and stops the run when a slice fails ({L1104-1105}).
11. Latency loop: for each core of the list the thread is pinned to that core. Then `measure` runs for the mixed set and for the set of every home node, and one row per set goes to `latency.csv`. For each timed pass `measure` uses a new chain, loads the set once, reads the evictor and then times one pass ({L1106-1134}).
12. It closes `latency.csv` and returns 0 ({L1135-1136}).

## Behavior a reader must know

- What is timed: in `measure`, one call of `chase` per repeat. It is `n` loads, one from each line of the set, over a chain that was never walked. The clock `CLOCK_MONOTONIC` is read directly before and directly after this call ({L749}, {L751}).
- What is not timed: the build of the chains, the load of the set, the reads of the evictor, the reads of the counters, the classification and the cache-state counters.
- The latency of a repeat is the elapsed time divided by the `n` loads, in ns per load. A row of `latency.csv` holds the median, the minimum, the maximum and the value of every repeat. There are 7 repeats by default.
- Before each timed pass every line of the set is loaded once, and then 8 MiB of other memory is read in a new random order. By the header comment the lines of the set are then in the SLC and no longer in L1 or L2. The cache-state check tests this with counters, for 8 slices and from the first core only.
- The set of a home node is the first 2048 lines of its line list by default (128 KiB). A home node with fewer lines uses fewer, and a home node with fewer than 64 lines gets no row.
- The buffer: 16 MiB by default, always a multiple of 2 MiB. It is filled with zeros on the first core of the core list. The program asks Linux for 2 MiB pages. It warns and goes on when the buffer is not on such pages.
- Thread placement: the program has one thread. It is pinned to the first core of the list for the buffers and the cache-state check, to the CPU of the PMU of mesh 0 for the classification, and then to each core of the list, one after the other, for the latency loop.
- The classification uses counts only. A line gets a home when exactly one open counter rose by at least three quarters of the loads of the probe and no other open counter rose by more than one quarter.
- A counter of a mesh counts every event of its type at its node, whichever process causes it. So other activity on the machine during a probe changes the counts.
- The program ends with exit status 2 in each of these cases: a wrong argument, no right to open a counter, a mesh without the expected number of home nodes, no home for any of the first 256 lines, a multiplexed counter group, more than 5 percent of the lines without a home, a failed verification, a line that is twice in a chain, or a failed cache-state check without `--verify-lenient`.
- The program ends with exit status 3 when the marker file exists. It looks for the file at most once per second, and only at the places where `check_marker` is called ({L465-466}, {L556}, {L900}, {L1125}).
- By the comments of the source, a line whose home is on the other mesh is served by a proxy on the mesh of the core. So a row for a home node of the other mesh does not show the distance to that node ({L895-898}).
- The cache-state check takes mesh 0 as the local mesh ({L877}). This fits only when the first core of the core list is a CPU of mesh 0.
- Some comments do not fit the code: the list of the output files ({L24}), the range of the node positions ({L305}), the marker check once per second ({L350}), the value -2 in the array `home` ({L424}), the array name `cstate_group` ({L716}), and two limits for the misses of the whole meshes ({L889}, {L893}).
- With `--no-perf` the program needs no root rights and opens no counter. The home nodes are invented, and by the header comment the latency values mean nothing.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/sudo-20261102T054936Z/log.txt`: the log of a run of `run_sudo.sh` on CRB that started on 2026-11-02 at 05:49 UTC. Its lines `arm_cmn_0: perf type 9, cpu 0, ...` and `arm_cmn_1: perf type 10, cpu 0, ...` show the CPU of both PMUs. The log also holds the line `classification runs on CPU 0, 256 loads per probe`.
- [Ref2] external source: Linux kernel documentation, page `admin-guide/mm/pagemap` (the file `/proc/pid/pagemap` holds one 64-bit entry per page. The bits 0 to 54 are the page frame number, and bit 63 says that the page is present. The page frame number is 0 for a process without the capability `CAP_SYS_ADMIN`).
- [Ref3] external source: Linux kernel documentation, page `admin-guide/perf/arm-cmn` (an event counts the sum over all nodes of its type. With `bynodeid` set to 1 and a `nodeid` it counts at one node).
- [Ref4] external source: Linux manual page `perf_event_open(2)` (the arguments `pid`, `cpu` and `group_fd`, and the data that a read returns with `PERF_FORMAT_GROUP`).
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/cmn-map.txt`: the maps of the two meshes, as printed from the files `map` and `map_1` of the Linux driver. Each crosspoint shows its DTC number. Both maps show DTC 1 and DTC 0 in the rows 4 to 7 and DTC 2 and DTC 3 in the rows 0 to 3.
- [Ref6] external source: Arm Architecture Reference Manual for A-profile architecture, the instructions `DC CIVAC` (clean and invalidate a data cache line by address) and `DSB` (data synchronization barrier).
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/plan-2026-11-02.md`: the plan note of 2026-11-02. Its word list defines the mesh (Arm CMN S3, one mesh of 9 by 8 crosspoints per half of the chip), the home node (HN-S), the slice and the DTC (one per quarter of a mesh, 4 per mesh, each with 8 counters).
