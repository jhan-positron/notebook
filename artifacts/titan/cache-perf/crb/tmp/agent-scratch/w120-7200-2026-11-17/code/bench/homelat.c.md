# `homelat.c` explained, line by line

- Source file: `bench/homelat.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 1137 lines, 50350 bytes).
- sha256 of the source when this page was built: `961e4781bf883f386c13640a988c9705e59d36d4182bf57a41bf5ba094a12590`.

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

1. `main` sets the defaults, reads the arguments and checks the settings (lines 927 to 961).
2. It creates the four output files in the folder of `--out` (lines 963 to 973).
3. It pins the thread to the first core of the core list. Then it reserves the main buffer and the evictor buffer (`alloc_buf` asks for 2 MiB pages and fills the buffer with zeros) (lines 975 to 988).
4. For each mesh it reads the type number and the CPU of the PMU and the description of the event, and it finds the home nodes (`discover` tries to open a counter for each of the 65536 possible node ids) (lines 990 to 1000).
5. It stops unless each mesh has the expected number of home nodes, 64 by default. Then `decode_ids` splits each node id into column, row, port and device (lines 1001 to 1010).
6. It pins the thread to the CPU of the PMU and runs the classification (`classify` probes every line, in passes with at most 8 open counters per mesh and DTC domain) (lines 1011 to 1018).
7. It stops when more than 5 percent of the lines have no home. Then `verify_classification` probes random lines again with a single counter, and the program stops below 98 percent agreement (lines 1019 to 1031).
8. It writes `nodes.csv`, `chunks.csv` and `homes.csv`. `chunks.csv` holds, for each 2 MiB chunk, the physical page frame and the split of its lines over the two meshes (lines 1036 to 1073).
9. It builds the mixed set from the same number of random lines of every home node, and it reports the home nodes with too few lines (lines 1075 to 1103).
10. Cache-state check: `verify_slices` measures 8 slices from the first core with counters open and stops the run when a slice fails (lines 1104 to 1105).
11. Latency loop: for each core of the list the thread is pinned to that core. Then `measure` runs for the mixed set and for the set of every home node, and one row per set goes to `latency.csv`. For each timed pass `measure` uses a new chain, loads the set once, reads the evictor and then times one pass (lines 1106 to 1134).
12. It closes `latency.csv` and returns 0 (lines 1135 to 1136).

## Behavior a reader must know

- What is timed: in `measure`, one call of `chase` per repeat. It is `n` loads, one from each line of the set, over a chain that was never walked. The clock `CLOCK_MONOTONIC` is read directly before and directly after this call (line 749, line 751).
- What is not timed: the build of the chains, the load of the set, the reads of the evictor, the reads of the counters, the classification and the cache-state counters.
- The latency of a repeat is the elapsed time divided by the `n` loads, in ns per load. A row of `latency.csv` holds the median, the minimum, the maximum and the value of every repeat. There are 7 repeats by default.
- Before each timed pass every line of the set is loaded once, and then 8 MiB of other memory is read in a new random order. By the header comment the lines of the set are then in the SLC and no longer in L1 or L2. The cache-state check tests this with counters, for 8 slices and from the first core only.
- The set of a home node is the first 2048 lines of its line list by default (128 KiB). A home node with fewer lines uses fewer, and a home node with fewer than 64 lines gets no row.
- The buffer: 16 MiB by default, always a multiple of 2 MiB. It is filled with zeros on the first core of the core list. The program asks Linux for 2 MiB pages. It warns and goes on when the buffer is not on such pages.
- Thread placement: the program has one thread. It is pinned to the first core of the list for the buffers and the cache-state check, to the CPU of the PMU of mesh 0 for the classification, and then to each core of the list, one after the other, for the latency loop.
- The classification uses counts only. A line gets a home when exactly one open counter rose by at least three quarters of the loads of the probe and no other open counter rose by more than one quarter.
- A counter of a mesh counts every event of its type at its node, whichever process causes it. So other activity on the machine during a probe changes the counts.
- The program ends with exit status 2 in each of these cases: a wrong argument, no right to open a counter, a mesh without the expected number of home nodes, no home for any of the first 256 lines, a multiplexed counter group, more than 5 percent of the lines without a home, a failed verification, a line that is twice in a chain, or a failed cache-state check without `--verify-lenient`.
- The program ends with exit status 3 when the marker file exists. It looks for the file at most once per second, and only at the places where `check_marker` is called (lines 465 to 466, line 556, line 900, line 1125).
- By the comments of the source, a line whose home is on the other mesh is served by a proxy on the mesh of the core. So a row for a home node of the other mesh does not show the distance to that node (lines 895 to 898).
- The cache-state check takes mesh 0 as the local mesh (line 877). This fits only when the first core of the core list is a CPU of mesh 0.
- Some comments do not fit the code: the list of the output files (line 24), the range of the node positions (line 305), the marker check once per second (line 350), the value -2 in the array `home` (line 424), the array name `cstate_group` (line 716), and two limits for the misses of the whole meshes (line 889, line 893).
- With `--no-perf` the program needs no root rights and opens no counter. The home nodes are invented, and by the header comment the latency values mean nothing.

## Source and explanation, line by line

- Text shown: the file `bench/homelat.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1137 lines, 50350 bytes, sha256 `961e4781bf883f386c13640a988c9705e59d36d4182bf57a41bf5ba094a12590`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment (lines 1 to 27)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Comment: starts the header comment of the file. It ends in line 27. |
| 2 | ` * homelat.c - mesh-cache latency from each core to each home-node slice.` | Comment: the name and the purpose of the program: the latency of the mesh cache from each core to the slice of each home node. Mesh cache is the word of the source for the SLC (the system level cache, the last cache level of the chip). A home node is a node of the mesh that owns a part of the memory addresses. Its slice is the part of the SLC that it holds. |
| 3 | ` *` | Comment: an empty line inside the header comment. |
| 4 | ` * Needs root for the mesh counters (perf_event_paranoid is 2 on CRB) and for` | Comment: the program needs root rights for two things. The first is the mesh counters. `perf_event_paranoid`, the Linux setting that decides who may open counters, is 2 on CRB. The sentence ends in line 5. |
| 5 | ` * /proc/self/pagemap. Three steps:` | Comment: the second is the file `/proc/self/pagemap`, from which the program reads the numbers of physical memory pages (lines 176 to 183). Then the comment announces the three steps of the program. |
| 6 | ` *` | Comment: an empty line inside the header comment. |
| 7 | ` * 1. Discover the home nodes (HN-S) of each mesh PMU (arm_cmn_0, arm_cmn_1):` | Comment: step 1 finds the home nodes of each mesh PMU. `HN-S` is the Arm name of this node type. A PMU is a counter unit. Linux shows the counters of the two meshes as the PMUs `arm_cmn_0` and `arm_cmn_1`. |
| 8 | ` *    perf_event_open with bynodeid=1 fails with EINVAL for a node id that does` | Comment: `perf_event_open` is the Linux call that opens a counter. With `bynodeid=1` the counter belongs to one node, which the caller names by its node id. For a node id that does not exist the call fails with the error `EINVAL` (invalid argument). The sentence ends in line 9. |
| 9 | ` *    not exist, so every id from 0 to 0xffff is tried once.` | Comment: so the program tries every id from 0 to `0xffff` (65535) once. The ids that open are the home nodes (lines 273 to 301). |
| 10 | ` * 2. Classify every 64 B line of a buffer by home node: flush the line (dc` | Comment: step 2 finds the home node of every 64-byte line of a buffer (the comment says classify). First the line is flushed: the instruction `dc civac` removes it from the caches. The sentence goes on in line 11. |
| 11 | ` *    civac), read the per-node "home-bound requests received" counters, flush and` | Comment: then the program reads the counters of the open nodes. Each of them counts the requests that its node received as the home of a line (the comment says home-bound). Then comes a flush and a load of the line, which the next comment line continues. |
| 12 | ` *    load the line 256 times, read the counters again. The one node whose count` | Comment: the flush and the load are done 256 times, and then the counters are read again. The next sentence starts here: the one node whose count ... |
| 13 | ` *    rose by about 256 is the home of that line. The probes run on the PMU's` | Comment: ... rose by about 256 is the home of the line. The next sentence starts here: the probes run on the CPU of the PMU. A probe is this test of one line. |
| 14 | ` *    own CPU and read 8 counters per syscall, to keep the kernel's traffic low. At most 8 nodes per DTC domain can be counted` | Comment: a probe reads 8 counters with one system call. By the comment, both choices keep the memory traffic of the Linux kernel low. The next sentence starts here: at most 8 nodes per DTC domain can be counted. A DTC (debug and trace controller) is the unit of the mesh that holds the counters. By the notes of the project a mesh has 4 of them, one per quarter of the mesh [Ref7]. |
| 15 | ` *    at once (hardware limit), so classification runs in passes.` | Comment: ... at the same time, which is a limit of the hardware. So the classification runs in several passes, each with another set of nodes (lines 430 to 511). |
| 16 | ` * 3. For each core and each home node: build a pointer chase over lines of` | Comment: step 3 runs for each core and each home node. It builds a pointer chase over lines of one node. A pointer chase is a loop in which each load reads the address of the next load. |
| 17 | ` *    that node only, load each line once to fill, push the lines out of L1 and L2` | Comment: the chase uses lines of that node only. Then each line is loaded once (the comment says fill). Then the lines are pushed out of L1 and L2, the two caches that belong to one core. |
| 18 | ` *    with 8 MiB of random-order loads (they stay in the slice, 1 MiB per node;` | Comment: the push is done with loads over 8 MiB of other memory in a random order. By the comment the lines stay in the slice, and a slice has 1 MiB per node. |
| 19 | ` *    a sequential evictor read was found not to replace L2 lines), then time` | Comment: by the comment, a read of that memory in address order did not replace the lines in L2. The source calls the 8 MiB buffer the evictor. Then the program times one pass, which the next comment line names. |
| 20 | ` *    one pass over a never-walked chain through the same lines. Every timed` | Comment: the timed pass goes over a chain through the same lines that was never walked before. A chain is one cycle of pointers. The next sentence starts here. |
| 21 | ` *    chain is used exactly once, because the cores learn a repeated chain` | Comment: every timed chain is used exactly once. The reason by the comment: the cores learn a chain that is repeated. |
| 22 | ` *    (temporal prefetcher) and the latency then drops to L2 level.` | Comment: the comment names the temporal prefetcher: the part of a core that records the order of earlier cache misses and fetches the same lines in the same order again. By the comment the latency then falls to the level of L2. |
| 23 | ` *` | Comment: an empty line inside the header comment. |
| 24 | ` * Output (CSV files in --out DIR): nodes.csv, chunks.csv, homes.csv, latency.csv.` | Comment: the output is four CSV files in the folder of the option `--out`: `nodes.csv`, `chunks.csv`, `homes.csv` and `latency.csv`. The program also writes `verify.csv` (line 823), which the comment does not name. |
| 25 | ` * --no-perf assigns fake homes (line index modulo 128) so the chase code can be` | Comment: the option `--no-perf` gives every line an invented home node: the line index modulo 128 (lines 564 to 577). So the chase code can run without root rights. |
| 26 | ` * tested without root; its latency numbers mean nothing.` | Comment: the end of the sentence. The latency values of such a run mean nothing. |
| 27 | ` */` | Comment: the end of the header comment. |

### Include lines, constants and settings (lines 28 to 54)

| Line | Source | Explanation |
|---:|---|---|
| 28 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include line. This makes the Linux-only calls of the headers visible, for example `sched_setaffinity` and `CPU_SET` (lines 142 to 145). |
| 29 | `#include <errno.h>` | Includes `errno`, the variable that holds the error number of the last failed call, and the error names `EACCES` and `EPERM` (line 281). |
| 30 | `#include <fcntl.h>` | Includes `open` and the flag `O_RDONLY` (line 1043). |
| 31 | `#include <linux/perf_event.h>` | Includes the types and constants of the Linux counter interface: `struct perf_event_attr`, the `PERF_FORMAT` flags and `PERF_TYPE_RAW`. |
| 32 | `#include <sched.h>` | Includes the header for the CPU pinning: the type `cpu_set_t`, the macros `CPU_ZERO` and `CPU_SET`, and the call `sched_setaffinity`. |
| 33 | `#include <stdint.h>` | Includes the integer types of fixed size, for example `uint64_t` (64 bits), `int16_t` (16 bits with a sign) and `uintptr_t` (an integer that can hold an address). |
| 34 | `#include <stdio.h>` | Includes the output and file functions: `printf`, `fprintf`, `perror`, `snprintf`, `fopen`, `fgets`, `fscanf`, `sscanf`, `fflush` and `fclose`. |
| 35 | `#include <stdlib.h>` | Includes `exit`, the memory functions `malloc`, `realloc` and `free`, the sort function `qsort`, and the functions that turn text into a number: `strtod`, `strtol` and `atoi`. |
| 36 | `#include <string.h>` | Includes the text functions `strcmp`, `strtok` and `strerror`, and the memory functions `memset` and `memcpy`. |
| 37 | `#include <sys/ioctl.h>` | Includes the declaration of the call `ioctl`. No line of this file calls it. |
| 38 | `#include <sys/mman.h>` | Includes `mmap` and `madvise`, the two Linux calls that `alloc_buf` uses for a buffer. |
| 39 | `#include <sys/stat.h>` | Includes the declarations for the status of a file. No line of this file uses them. |
| 40 | `#include <sys/syscall.h>` | Includes `SYS_perf_event_open`, the number of the system call that opens a counter. The C library has no function for this call. So the program makes it with `syscall` (line 233). |
| 41 | `#include <time.h>` | Includes `clock_gettime` and the type `struct timespec`. The function `now_s` reads the clock with them. |
| 42 | `#include <unistd.h>` | Includes the calls `syscall`, `read`, `pread`, `close` and `access`. |
| 44 | `#define LINE 64` | `LINE`: 64, the size of one cache line in bytes. |
| 45 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2 MiB (2097152 bytes), the size of one huge page. The expression shifts the number 2 left by 20 bits. |
| 46 | `#define NMESH 2` | `NMESH`: 2, the number of meshes. Each mesh has its own PMU. |
| 47 | `#define MAX_NODES 256 /* both meshes together */` | `MAX_NODES`: the node table has room for 256 home nodes. By the comment this covers both meshes together. |
| 48 | `#define MESH_X 9` | `MESH_X`: 9, the number of columns of crosspoints of one mesh. A crosspoint is a junction of the mesh. Cores, home nodes and other nodes are connected to its ports. |
| 49 | `#define MESH_Y 8` | `MESH_Y`: 8, the number of rows of crosspoints of one mesh. |
| 50 | `static uint64_t evict_bytes = 8UL << 20; /* --evict-bytes */` | `evict_bytes`: the size of the evictor buffer, 8 MiB (8388608 bytes) unless the option `--evict-bytes` changes it. The evictor is the buffer that the program reads to push the measured lines out of L1 and L2 (lines 649 to 658). |
| 51 | `static int evict_reshuffle = 1;            /* --evict-fixed keeps one order; a repeated order gets learned and replayed */` | `evict_reshuffle`: 1 means that every call of `evict` reads the evictor in a new random order. The option `--evict-fixed` sets it to 0 and keeps one order. By the comment, a core learns an order that repeats and fetches it in advance. |
| 52 | `#define DTC_LIMIT 8  /* counters per DTC domain, CMN_DT_NUM_COUNTERS in drivers/perf/arm-cmn.c */` | `DTC_LIMIT`: 8, the number of counters of one DTC domain. By the comment it is the constant `CMN_DT_NUM_COUNTERS` of the Linux driver file `drivers/perf/arm-cmn.c`. |
| 53 | `#define MAX_CORES 1024` | `MAX_CORES`: the core list of the option `--cores` holds at most 1024 entries (line 928). |

### `struct node` and the global variables (lines 55 to 72)

| Line | Source | Explanation |
|---:|---|---|
| 55 | `struct node {` | Starts `struct node`: one entry per home node. |
| 56 | `    int mesh;` | `mesh`: the mesh of the node, 0 or 1. |
| 57 | `    uint16_t id;` | `id`: the node id, a 16-bit number. It packs the position of the node (lines 303 to 305). |
| 58 | `    int x, y, port, dev, dtc;` | `x`, `y`: the column and the row of the crosspoint of the node. `port`: the port of the crosspoint. `dev`: the device number on that port. `dtc`: the DTC domain of the crosspoint (lines 266 to 271). `decode_ids` fills all five. |
| 59 | `    int fd;         /* open counter, or -1 */` | `fd`: the file descriptor of the open counter of this node. By the comment it is -1 when no counter is open. |
| 60 | `    int done;       /* already used in a classification pass */` | `done`: 1 when the node already had its counter in a classification pass. |
| 61 | `    uint64_t before;` | `before`: a 64-bit value. No line of the file uses this field. The counter groups have a field of the same name (line 243). |
| 62 | `    uint32_t *lines; /* line indices homed here */` | `lines`: the list of the lines whose home is this node. Each entry is the index of a line in the buffer. |
| 63 | `    int nlines, cap;` | `nlines`: the number of entries in the list. `cap`: the number of entries that the reserved memory can hold. |
| 64 | `};` | Ends `struct node`. |
| 66 | `static struct node nodes[MAX_NODES];` | `nodes`: the table of all home nodes, at most 256. |
| 67 | `static int nnodes;` | `nnodes`: the number of entries of the table that are in use. |
| 68 | `static int pmu_type[NMESH], pmu_cpu[NMESH];` | `pmu_type`: for each mesh, the type number that Linux gave to the PMU of the mesh. `pmu_cpu`: for each mesh, the CPU on which a counter of this PMU is opened. `main` reads both from files of Linux (lines 992 to 995). |
| 69 | `static uint64_t event_cfg[NMESH];` | `event_cfg`: for each mesh, the configuration word of the event that the classification counts (line 996). |
| 70 | `static void *volatile sink;` | `sink`: a global pointer variable. `volatile` stands after the star, so the variable itself is volatile: the compiler must carry out every store to it. The program stores results of loads there, so the compiler has no reason to remove the loads. |
| 71 | `static uint64_t rng_state = 0x9E3779B97F4A7C15ULL;` | `rng_state`: the 64-bit state of the random number generator `xorshift64`. It starts at a fixed constant, and no line sets it again. So the generator gives the same row of numbers in every run. |

### Functions `die`, `now_s` and `xorshift64` (lines 73 to 93)

| Line | Source | Explanation |
|---:|---|---|
| 73 | `static void die(const char *what)` | Starts the function `die`. It prints an error message and ends the program with exit status 2. `what` names the step that failed. |
| 74 | `{` | Opens the body of `die`. |
| 75 | `    fprintf(stderr, "homelat: %s: %s\n", what, strerror(errno));` | Prints `homelat:`, the text `what` and the reason of the last failed call to the error output. `strerror(errno)` turns the error number into text. |
| 76 | `    exit(2);` | Ends the program with exit status 2. |
| 77 | `}` | Ends the function `die`. |
| 79 | `static double now_s(void)` | Starts the function `now_s`. It reads the clock and returns the time in seconds. Every time value of the program comes from this function. |
| 80 | `{` | Opens the body of `now_s`. |
| 81 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 82 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | Reads `CLOCK_MONOTONIC` into `ts`. This is the Linux clock that only moves forward. A change of the date of the machine does not change it. It is the only clock that the file reads. |
| 83 | `    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;` | Returns the time in seconds as a `double`: the seconds plus the nanoseconds times 1e-9. |
| 84 | `}` | Ends the function `now_s`. |
| 86 | `static uint64_t xorshift64(void)` | Starts the function `xorshift64`. It is a small generator of pseudo-random numbers. Each call changes the state `rng_state` in three steps and returns the new state. |
| 87 | `{` | Opens the body of `xorshift64`. |
| 88 | `    rng_state ^= rng_state << 13;` | Step 1: shifts the state left by 13 bits and combines the result with the state by exclusive or (the operator `^=`). |
| 89 | `    rng_state ^= rng_state >> 7;` | Step 2: the same with a shift right by 7 bits. |
| 90 | `    rng_state ^= rng_state << 17;` | Step 3: the same with a shift left by 17 bits. |
| 91 | `    return rng_state;` | Returns the new state as the random number. |
| 92 | `}` | Ends the function `xorshift64`. |

### Function `parse_bytes`: read a size such as `16M` (lines 94 to 109)

| Line | Source | Explanation |
|---:|---|---|
| 94 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `16M` into a number of bytes. `main` calls it for the options `--bytes` and `--evict-bytes` (line 939, line 947). |
| 95 | `{` | Opens the body of `parse_bytes`. |
| 96 | `    char *end;` | `end`: will point to the first character after the number. |
| 97 | `    double v = strtod(s, &end), mul = 1;` | `strtod` reads a number from the start of the text `s` into `v`. The number may have a decimal point. `strtod` sets `end` to the first character that is not part of the number. `mul`: the factor of the suffix. It stays 1 when the text has no suffix. |
| 98 | `    switch (*end) {` | Looks at the character after the number. |
| 99 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | `k` or `K`: the factor is 1024 (2 to the power 10). `end++` steps over the suffix. |
| 100 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | `m` or `M`: the factor is 1048576 (2 to the power 20, which is 1 MiB). So `16M` gives 16777216 bytes. |
| 101 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | `g` or `G`: the factor is 1073741824 (2 to the power 30). |
| 102 | `    }` | Ends the `switch` of line 98. |
| 103 | `    if (end == s \|\| *end != '\0' \|\| v <= 0) {` | Tests three error cases. No number was read (`end == s`). Or other text follows the number and its suffix. Or the value is 0 or below. |
| 104 | `        fprintf(stderr, "bad size: %s\n", s);` | On an error: prints `bad size:` and the text to the error output. |
| 105 | `        exit(2);` | On an error: the program ends with exit status 2. |
| 106 | `    }` | Ends the `if` of line 103. |
| 107 | `    return (uint64_t)(v * mul);` | Returns the number times the factor as a whole number of bytes. A fraction of a byte is cut off. |
| 108 | `}` | Ends the function `parse_bytes`. |

### Function `parse_list`: read a list of numbers such as `0-119` (lines 110 to 139)

| Line | Source | Explanation |
|---:|---|---|
| 110 | `/* "0-119", "0-118:2", "3,64,119" */` | Comment: three examples of a list. `0-119` is a range. `0-118:2` is a range with a step: every second number from 0 to 118. `3,64,119` is a list of single numbers. |
| 111 | `static int parse_list(char *list, int *out, int max)` | Starts the function `parse_list`. It reads a list text, writes every number of the list to the array `out` in the order of the list, and returns how many numbers it wrote. `max` is the room of the array. `main` calls it for the core list (line 940, line 958). |
| 112 | `{` | Opens the body of `parse_list`. |
| 113 | `    int n = 0;` | `n`: the number of entries written so far. |
| 114 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Loop over the pieces of the list. `strtok` cuts the text at each comma and returns one piece per call. After the last piece it returns `NULL`, which ends the loop. |
| 115 | `        char *e, *e2;` | `e`, `e2`: each will point to the first character after a number that was read. |
| 116 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the piece (base 10) into `lo`. `hi` starts equal to `lo`, and `step` starts at 1. So a piece that is one number gives one entry. |
| 117 | `        if (e != tok && *e == '-') {` | Tests whether a number was read and a hyphen follows it. The piece is then a range. |
| 118 | `            hi = strtol(e + 1, &e2, 10);` | Reads the number after the hyphen into `hi`, the last number of the range. |
| 119 | `            e = e2;` | Moves `e` to the first character after the second number. |
| 120 | `            if (*e == ':') {` | Tests whether a colon follows. The piece then has a step. |
| 121 | `                step = strtol(e + 1, &e2, 10);` | Reads the number after the colon into `step`. |
| 122 | `                e = e2;` | Moves `e` to the first character after the step. |
| 123 | `            }` | Ends the `if` of line 120. |
| 124 | `        }` | Ends the `if` of line 117. |
| 125 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| step < 1) {` | Tests the piece. It is bad in each of these cases: no number was read at its start, or other text follows the numbers, or `lo` is below 0, or `hi` is below `lo`, or `step` is below 1. |
| 126 | `            fprintf(stderr, "bad list: %s\n", tok);` | On a bad piece: prints `bad list:` and the piece to the error output. |
| 127 | `            exit(2);` | On a bad piece: the program ends with exit status 2. |
| 128 | `        }` | Ends the `if` of line 125. |
| 129 | `        for (long c = lo; c <= hi; c += step) {` | Loop over the numbers of the piece: from `lo` to `hi` in steps of `step`. |
| 130 | `            if (n == max) {` | Tests whether the array is full. |
| 131 | `                fprintf(stderr, "list too long\n");` | When it is full: prints `list too long` to the error output. |
| 132 | `                exit(2);` | When it is full: the program ends with exit status 2. |
| 133 | `            }` | Ends the `if` of line 130. |
| 134 | `            out[n++] = (int)c;` | Appends the number to the array and adds 1 to the count. |
| 135 | `        }` | Ends the loop of line 129. |
| 136 | `    }` | Ends the loop of line 114. |
| 137 | `    return n;` | Returns the number of entries. |
| 138 | `}` | Ends the function `parse_list`. |

### Functions `pin_cpu` and `alloc_buf`: pin the thread, reserve and write a buffer (lines 140 to 161)

| Line | Source | Explanation |
|---:|---|---|
| 140 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It pins the calling thread to the CPU with the number `cpu`: Linux then runs the thread on that CPU only. The program has one thread, so each call moves the whole program to that CPU. |
| 141 | `{` | Opens the body of `pin_cpu`. |
| 142 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 143 | `    CPU_ZERO(&set);` | Empties the set. |
| 144 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 145 | `    if (sched_setaffinity(0, sizeof set, &set) != 0)` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 146 | `        die("sched_setaffinity");` | On failure: `die` prints `homelat: sched_setaffinity:` with the reason that Linux gave and ends the program with exit status 2. |
| 147 | `}` | Ends the function `pin_cpu`. |
| 149 | `static uint8_t *alloc_buf(uint64_t bytes)` | Starts the function `alloc_buf`. It reserves a buffer of at least `bytes` bytes, asks Linux for 2 MiB pages, fills the buffer with zeros and returns its address. The buffer starts at a multiple of 2 MiB. |
| 150 | `{` | Opens the body of `alloc_buf`. |
| 151 | `    size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | `len`: `bytes` rounded up to the next multiple of `HUGE_BYTES` (2 MiB). The expression adds `HUGE_BYTES - 1` and then clears the low bits. This gives the right value when `HUGE_BYTES` is a power of two. |
| 152 | `    void *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `len + HUGE_BYTES` bytes of new memory. The extra 2 MiB make it possible to move the start to an aligned address (line 155). `NULL`: Linux chooses the address. `PROT_READ \| PROT_WRITE`: the program may read and write the memory. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. |
| 153 | `    if (raw == MAP_FAILED)` | Tests whether `mmap` failed. |
| 154 | `        die("mmap");` | On failure: `die` prints `homelat: mmap:` with the reason and ends the program with exit status 2. |
| 155 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the first address in the reserved range that is a multiple of 2 MiB. The buffer starts there. The expression rounds the address `raw` up in the same way as line 151 rounds the size. |
| 156 | `    if (madvise(p, len, MADV_HUGEPAGE) != 0)` | `madvise` with `MADV_HUGEPAGE` asks Linux to use 2 MiB pages for the `len` bytes that start at `p`. The program has no option that turns this request off. A return value other than 0 means that the call failed. |
| 157 | `        perror("madvise (continuing)");` | On failure: `perror` prints a message that starts with `madvise (continuing)`. The program goes on. |
| 158 | `    memset(p, 0, len);` | Writes zeros to all `len` bytes. This is the first write to the buffer (first touch): Linux assigns the memory pages at this moment. The thread is pinned to the first core of the core list at that time (line 975). |
| 159 | `    return p;` | Returns the aligned address. The program never releases the buffer. |
| 160 | `}` | Ends the function `alloc_buf`. |

### Functions `anon_huge_kb` and `pfn_of`: huge page memory and physical page numbers (lines 162 to 184)

| Line | Source | Explanation |
|---:|---|---|
| 162 | `static long anon_huge_kb(void)` | Starts the function `anon_huge_kb`. It returns how many kB of the memory of this process lie on transparent huge pages at this moment. These are the 2 MiB pages that Linux can use in place of its smaller standard pages. The function returns -1 when it cannot find the value. |
| 163 | `{` | Opens the body of `anon_huge_kb`. |
| 164 | `    FILE *f = fopen("/proc/self/smaps_rollup", "r");` | Opens the file `/proc/self/smaps_rollup` for reading. Linux provides this file for each process. It holds one line per memory value, each summed over all memory ranges of the process. |
| 165 | `    if (!f)` | Tests whether the file could not be opened. |
| 166 | `        return -1;` | Then the function returns -1. |
| 167 | `    char line[256];` | `line`: room for one text line of at most 255 characters. |
| 168 | `    long kb = -1;` | `kb`: the result. It stays -1 when no line fits. |
| 169 | `    while (fgets(line, sizeof line, f))` | Reads the file line by line. `fgets` returns `NULL` at the end of the file, which ends the loop. |
| 170 | `        if (sscanf(line, "AnonHugePages: %ld kB", &kb) == 1)` | `sscanf` tests whether the line has the form `AnonHugePages:`, then a number, then `kB`. When it has, the number goes to `kb` and `sscanf` returns 1. `AnonHugePages` is the memory without a file behind it that lies on transparent huge pages. |
| 171 | `            break;` | Leaves the loop at the first such line. |
| 172 | `    fclose(f);` | Closes the file. |
| 173 | `    return kb;` | Returns the value in kB, or -1. |
| 174 | `}` | Ends the function `anon_huge_kb`. |
| 176 | `static uint64_t pfn_of(int pagemap_fd, const void *addr)` | Starts the function `pfn_of`. It returns the page frame number of the memory page that holds the address `addr`. The page frame number is the number of the physical page. `pagemap_fd` is the open file `/proc/self/pagemap`. The function returns 0 when it cannot get the number. |
| 177 | `{` | Opens the body of `pfn_of`. |
| 178 | `    uint64_t entry = 0;` | `entry`: the 8-byte entry of the page in the file. It starts at 0. |
| 179 | `    off_t off = (off_t)((uintptr_t)addr / 4096) * 8;` | `off`: the place of the entry in the file. The file holds one 8-byte entry per page, in the order of the addresses [Ref2]. The code takes 4096 bytes as the page size. So the place is the address divided by 4096, times 8. |
| 180 | `    if (pread(pagemap_fd, &entry, 8, off) != 8)` | `pread` reads the 8 bytes at that place. The line tests whether it did not get 8 bytes. |
| 181 | `        return 0;` | Then the function returns 0. |
| 182 | `    return (entry >> 63) ? (entry & ((1ULL << 55) - 1)) : 0;` | Bit 63 of the entry says whether the page is present in memory. When it is set, the function returns the bits 0 to 54 of the entry, which hold the page frame number [Ref2]. When it is not set, the function returns 0. Linux gives 0 in these bits to a process without the needed rights [Ref2]. That is the second reason for root rights that the header comment names (line 5). |
| 183 | `}` | Ends the function `pfn_of`. |

### Functions `read_sysfs_int` and `event_config`: read the PMU files of Linux (lines 185 to 224)

| Line | Source | Explanation |
|---:|---|---|
| 185 | `/* ---- perf ---- */` | Comment: a section title. The functions that follow use the counter interface of Linux, whose name is perf. |
| 187 | `static int read_sysfs_int(const char *path)` | Starts the function `read_sysfs_int`. It reads one whole number from the start of a file and returns it. `main` uses it for two files of each PMU (line 993, line 995). |
| 188 | `{` | Opens the body of `read_sysfs_int`. |
| 189 | `    FILE *f = fopen(path, "r");` | Opens the file for reading. |
| 190 | `    int v = -1;` | `v`: the number that will be read. |
| 191 | `    if (!f \|\| fscanf(f, "%d", &v) != 1) {` | Tests whether the file could not be opened or does not start with a number. `fscanf` returns 1 when it has read one number. |
| 192 | `        fprintf(stderr, "homelat: cannot read %s\n", path);` | In that case: prints `homelat: cannot read` and the path to the error output. |
| 193 | `        exit(2);` | In that case: the program ends with exit status 2. |
| 194 | `    }` | Ends the `if` of line 191. |
| 195 | `    fclose(f);` | Closes the file. |
| 196 | `    return v;` | Returns the number. |
| 197 | `}` | Ends the function `read_sysfs_int`. |
| 199 | `/* Builds the config word from the sysfs event description "type=0x200,eventid=0x5,filter=0x1"` | Comment: the function builds the configuration word of an event from the description that Linux gives for the event. The description is a text such as `type=0x200,eventid=0x5,filter=0x1`. The sentence ends in line 200. |
| 200 | ` * using the arm_cmn format: type bits 0-15, eventid 16-26, filter 27-30, bynodeid 31, nodeid 32-47. */` | Comment: the word has the format of the Linux driver `arm_cmn`: the node type in the bits 0 to 15, the event id in the bits 16 to 26, the filter in the bits 27 to 30, the flag `bynodeid` in bit 31 and the node id in the bits 32 to 47. |
| 201 | `static uint64_t event_config(int mesh, const char *event)` | Starts the function `event_config`. `mesh` selects the PMU, and `event` is the name of the event. The function returns the bits 0 to 30 of the configuration word: type, event id and filter. The callers add the two node fields (line 231, line 842). |
| 202 | `{` | Opens the body of `event_config`. |
| 203 | `    char path[256], text[256];` | `path`: room for the file name. `text`: room for the description. |
| 204 | `    snprintf(path, sizeof path, "/sys/bus/event_source/devices/arm_cmn_%d/events/%s", mesh, event);` | Builds the file name `/sys/bus/event_source/devices/arm_cmn_N/events/NAME`. `N` is the mesh number, and `NAME` is the event name. |
| 205 | `    FILE *f = fopen(path, "r");` | Opens the file for reading. |
| 206 | `    if (!f \|\| !fgets(text, sizeof text, f)) {` | Tests whether the file could not be opened or its first line could not be read. |
| 207 | `        fprintf(stderr, "homelat: cannot read %s\n", path);` | In that case: prints `homelat: cannot read` and the path to the error output. |
| 208 | `        exit(2);` | In that case: the program ends with exit status 2. |
| 209 | `    }` | Ends the `if` of line 206. |
| 210 | `    fclose(f);` | Closes the file. |
| 211 | `    uint64_t cfg = 0;` | `cfg`: the configuration word. It starts at 0. |
| 212 | `    unsigned v;` | `v`: the value of one field of the description. |
| 213 | `    for (char *tok = strtok(text, ",\n"); tok; tok = strtok(NULL, ",\n")) {` | Loop over the fields of the description. `strtok` cuts the text at each comma and at the end of the line. |
| 214 | `        if (sscanf(tok, "type=0x%x", &v) == 1) cfg \|= (uint64_t)v;` | A field of the form `type=0x...`: `sscanf` reads the hexadecimal value into `v` and returns 1. The value goes into the lowest bits of `cfg`. It is the node type. |
| 215 | `        else if (sscanf(tok, "eventid=0x%x", &v) == 1) cfg \|= (uint64_t)v << 16;` | A field of the form `eventid=0x...`: the value goes into `cfg` shifted left by 16 bits. |
| 216 | `        else if (sscanf(tok, "filter=0x%x", &v) == 1) cfg \|= (uint64_t)v << 27;` | A field of the form `filter=0x...`: the value goes into `cfg` shifted left by 27 bits. |
| 217 | `        else {` | Every other field is an error. |
| 218 | `            fprintf(stderr, "homelat: unknown field in %s: %s\n", path, tok);` | Prints `homelat: unknown field in`, the path and the field to the error output. |
| 219 | `            exit(2);` | The program ends with exit status 2. |
| 220 | `        }` | Ends the `else` of line 217. |
| 221 | `    }` | Ends the loop of line 213. |
| 222 | `    return cfg;` | Returns the configuration word. |
| 223 | `}` | Ends the function `event_config`. |

### Function `perf_open`: open the counter of one home node (lines 225 to 235)

| Line | Source | Explanation |
|---:|---|---|
| 225 | `static int perf_open(int mesh, uint16_t nodeid, int group_fd)` | Starts the function `perf_open`. It opens one counter of the classification event for one home node. It returns the file descriptor of the counter, or -1 on failure. `nodeid` selects the node. `group_fd` is -1 for the first counter of a group. For each further counter of the group it is the file descriptor of the first one. |
| 226 | `{` | Opens the body of `perf_open`. |
| 227 | `    struct perf_event_attr a;` | `a`: the description of the counter that the system call takes. |
| 228 | `    memset(&a, 0, sizeof a);` | Sets every field of the description to 0. |
| 229 | `    a.type = (uint32_t)pmu_type[mesh];` | The PMU: the type number of the PMU of this mesh. |
| 230 | `    a.size = sizeof a;` | The size of the description in bytes. Linux uses it to tell the versions of this structure apart. |
| 231 | `    a.config = event_cfg[mesh] \| (1ULL << 31) \| ((uint64_t)nodeid << 32);` | The configuration word: the event bits of this mesh (line 996), plus bit 31 (`bynodeid`), plus the node id in the bits 32 to 47. With `bynodeid` set, the counter counts at this one node only. Without it, an `arm_cmn` event gives the sum over all nodes of the type [Ref3]. |
| 232 | `    a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | `read_format` sets what a read of the counter returns. `PERF_FORMAT_GROUP`: one read of the first counter of a group returns the values of all counters of the group. `PERF_FORMAT_TOTAL_TIME_ENABLED` and `PERF_FORMAT_TOTAL_TIME_RUNNING`: the read also returns the time for which the counter was enabled and the time for which it was really counting [Ref4]. |
| 233 | `    return (int)syscall(SYS_perf_event_open, &a, -1, pmu_cpu[mesh], group_fd, 0);` | Makes the system call `perf_event_open`. The arguments after the description are: the process (-1 stands for all processes), the CPU (`pmu_cpu` of this mesh), the group, and the flags (0, none). A counter with these values counts the events of all processes on that CPU [Ref4]. The call returns a file descriptor, or -1 with the reason in `errno`. |
| 234 | `}` | Ends the function `perf_open`. |

### Counter groups: `struct group` and the function `group_read` (lines 236 to 263)

| Line | Source | Explanation |
|---:|---|---|
| 236 | `/* One group per (mesh, DTC quadrant): up to DTC_LIMIT counters read with one syscall.` | Comment: the counters are opened as groups, one group per mesh and DTC domain (the comment says quadrant). A group has up to `DTC_LIMIT` (8) counters, and one system call reads all of them. |
| 237 | ` * Fewer syscalls matter: each read on a CPU other than the PMU's CPU is an interrupt to` | Comment: fewer system calls matter. By the comment, each read on a CPU other than the CPU of the PMU causes an interrupt to that CPU. The sentence goes on in line 238. |
| 238 | ` * that CPU, and the kernel's memory traffic from 128 such reads per probe (measured` | Comment: by the comment, 128 such reads per probe made the Linux kernel produce memory traffic of its own. The comment dates the measurement 2026-11-02. |
| 239 | ` * 2026-11-02) buried the one load being classified under hundreds of requests. */` | Comment: the end of the sentence: this traffic caused hundreds of requests, and the request of the one load under test could not be told from them. |
| 240 | `struct group {` | Starts `struct group`: one group of counters. |
| 241 | `    int leader_fd, n;` | `leader_fd`: the file descriptor of the first counter of the group, which perf calls the leader. A read of it returns the whole group. `n`: the number of counters in the group. |
| 242 | `    int node_idx[DTC_LIMIT];` | `node_idx`: for each counter of the group, the index of its node in the table `nodes`. |
| 243 | `    uint64_t before[DTC_LIMIT];` | `before`: for each counter of the group, its value at the start of a probe (line 381). |
| 244 | `};` | Ends `struct group`. |
| 245 | `static struct group groups[NMESH * 4];` | `groups`: room for 8 groups: 2 meshes times 4 DTC domains. |
| 246 | `static int ngroups;` | `ngroups`: the number of groups that are open at this moment. |
| 248 | `/* reads a group: values[0..n-1], and enabled/running of the leader */` | Comment: the function reads a group. `values[0]` to `values[n-1]` receive the counts. `enabled` and `running` receive the two times of the leader. |
| 249 | `static void group_read(struct group *g, uint64_t *values, uint64_t *enabled, uint64_t *running)` | Starts the function `group_read`. It reads all counters of the group `g` with one `read` call. |
| 250 | `{` | Opens the body of `group_read`. |
| 251 | `    uint64_t r[3 + DTC_LIMIT];` | `r`: room for the answer of Linux: 3 numbers at the start and up to 8 counts, 8 bytes each. |
| 252 | `    ssize_t want = (ssize_t)((3 + (size_t)g->n) * sizeof(uint64_t));` | `want`: the number of bytes that the answer must have: 3 plus `n` numbers of 8 bytes each. |
| 253 | `    if (read(g->leader_fd, r, sizeof r) != want)` | Reads the group through its leader. The answer holds, in this order: the number of counters, the time enabled, the time running, and one count per counter in the order in which the counters were opened [Ref4]. The line tests whether the answer does not have the wanted length. |
| 254 | `        die("perf group read");` | In that case: `die` prints `homelat: perf group read:` with the reason and ends the program with exit status 2. |
| 255 | `    if ((int)r[0] != g->n) {` | Tests whether the first number of the answer, the number of counters, differs from `n`. |
| 256 | `        fprintf(stderr, "homelat: group read returned %d counters, expected %d\n", (int)r[0], g->n);` | In that case: prints both numbers to the error output. |
| 257 | `        exit(2);` | In that case: the program ends with exit status 2. |
| 258 | `    }` | Ends the `if` of line 255. |
| 259 | `    *enabled = r[1]; *running = r[2];` | Gives the time enabled and the time running back to the caller. When the two differ, the group did not count the whole time (line 491). |
| 260 | `    for (int i = 0; i < g->n; i++)` | Loop over the counters of the group. |
| 261 | `        values[i] = r[3 + i];` | Copies the count of counter `i` to the caller. |
| 262 | `}` | Ends the function `group_read`. |

### Function `dtc_of`: the DTC domain of a crosspoint (lines 264 to 272)

| Line | Source | Explanation |
|---:|---|---|
| 264 | `/* DTC domain of a crosspoint, from crb/results/cmn-map.txt (both meshes identical):` | Comment: the function gives the DTC domain of a crosspoint. The rule comes from the file `crb/results/cmn-map.txt`, the map of the meshes that the Linux driver prints. By the comment both meshes are identical. The copy of that map in the test data shows the same domains for both meshes [Ref5]. |
| 265 | ` * rows 4-7: columns 0-4 are DTC 1, columns 5-8 DTC 0; rows 0-3: columns 0-4 DTC 2, columns 5-8 DTC 3. */` | Comment: the rule. In the rows 4 to 7, the columns 0 to 4 belong to DTC 1 and the columns 5 to 8 to DTC 0. In the rows 0 to 3, the columns 0 to 4 belong to DTC 2 and the columns 5 to 8 to DTC 3. |
| 266 | `static int dtc_of(int x, int y)` | Starts the function `dtc_of`. It returns the number of the DTC domain, 0 to 3, of the crosspoint in column `x` and row `y`. |
| 267 | `{` | Opens the body of `dtc_of`. |
| 268 | `    if (y >= 4)` | Tests whether the row is 4 or above. |
| 269 | `        return x <= 4 ? 1 : 0;` | Then returns 1 for the columns 0 to 4, and 0 for the columns 5 to 8. |
| 270 | `    return x <= 4 ? 2 : 3;` | For the rows 0 to 3: returns 2 for the columns 0 to 4, and 3 for the columns 5 to 8. |
| 271 | `}` | Ends the function `dtc_of`. |

### Function `discover`: find the home nodes of one mesh (lines 273 to 302)

| Line | Source | Explanation |
|---:|---|---|
| 273 | `static void discover(int mesh)` | Starts the function `discover`. It finds the home nodes of the mesh `mesh`. It tries to open a counter for every possible node id and adds each id that opens to the table `nodes`. |
| 274 | `{` | Opens the body of `discover`. |
| 275 | `    int found = 0, first_errno = 0;` | `found`: the number of home nodes found on this mesh. `first_errno`: the error number of the first id that did not open. |
| 276 | `    for (unsigned id = 0; id < 0x10000; id++) {` | Loop over all 65536 possible node ids, from 0 to `0xffff`. |
| 277 | `        int fd = perf_open(mesh, (uint16_t)id, -1);` | Tries to open a counter of the classification event for this id (`perf_open`). `-1`: the counter is not part of a group. |
| 278 | `        if (fd < 0) {` | Tests whether the call failed. |
| 279 | `            if (!first_errno)` | Tests whether this is the first failure. |
| 280 | `                first_errno = errno;` | Then keeps its error number for the message of line 296. |
| 281 | `            if (errno == EACCES \|\| errno == EPERM)` | Tests whether the reason is `EACCES` or `EPERM`. Both mean that the process has no right to open the counter. |
| 282 | `                die("perf_event_open (run as root)");` | Then `die` prints `homelat: perf_event_open (run as root):` with the reason and ends the program with exit status 2. |
| 283 | `            continue;` | Every other failure is taken to mean that no home node has this id. The loop goes on with the next id. |
| 284 | `        }` | Ends the `if` of line 278. |
| 285 | `        close(fd);` | The counter opened, so a home node with this id exists. The counter is closed again immediately. |
| 286 | `        if (nnodes == MAX_NODES) {` | Tests whether the table is full (256 nodes). |
| 287 | `            fprintf(stderr, "homelat: more than %d nodes\n", MAX_NODES);` | Then prints `homelat: more than 256 nodes` to the error output. |
| 288 | `            exit(2);` | Then the program ends with exit status 2. |
| 289 | `        }` | Ends the `if` of line 286. |
| 290 | `        nodes[nnodes].mesh = mesh;` | Stores the mesh of the new node in the next free entry of the table. |
| 291 | `        nodes[nnodes].id = (uint16_t)id;` | Stores its id. |
| 292 | `        nodes[nnodes].fd = -1;` | Marks that no counter of the node is open. |
| 293 | `        nnodes++;` | Adds 1 to the number of nodes in the table. |
| 294 | `        found++;` | Adds 1 to the number of nodes found on this mesh. |
| 295 | `    }` | Ends the loop of line 276. The nodes of a mesh stand in the table in rising order of their ids. |
| 296 | `    fprintf(stderr, "mesh %d: %d home nodes found (first error on a bad id: %s)\n", mesh, found, strerror(first_errno));` | Prints one line to the error output: the mesh, the number of home nodes found, and the reason of the first id that did not open. The header comment expects `EINVAL` there (line 8). |
| 297 | `    if (found == 0) {` | Tests whether no node was found. |
| 298 | `        fprintf(stderr, "homelat: no home node answered on mesh %d\n", mesh);` | Then prints `homelat: no home node answered on mesh` and the mesh number. |
| 299 | `        exit(2);` | Then the program ends with exit status 2. |
| 300 | `    }` | Ends the `if` of line 297. |
| 301 | `}` | Ends the function `discover`. |

### Function `decode_ids`: split each node id into column, row, port and device (lines 303 to 332)

| Line | Source | Explanation |
|---:|---|---|
| 303 | `/* The node id packs x, y, port and device. Two layouts occur in the driver: port 3 bits +` | Comment: the node id packs four values: `x`, `y`, the port and the device. By the comment the driver knows two layouts. In the first, the port has 3 bits and the device 2 bits. |
| 304 | ` * device 2 bits, or port 2 bits + device 1 bit; x and y use 4 bits each on a 9 x 8 mesh. The` | Comment: in the second layout the port has 2 bits and the device 1 bit. In both, `x` and `y` have 4 bits each on a mesh of 9 by 8 crosspoints. The next sentence starts at the end of this line. |
| 305 | ` * layout under which every id lands on a crosspoint of the map (x 1..7, y 1..5) is kept. */` | Comment: the function keeps the layout under which every id gives a position that is a crosspoint of the map. The comment gives the range `x` from 1 to 7 and `y` from 1 to 5. The code tests a wider range: `x` from 0 to 8 and `y` from 0 to 7 (line 316). |
| 306 | `static void decode_ids(void)` | Starts the function `decode_ids`. It splits the id of every node into column, row, port and device, and it sets the DTC domain of every node. |
| 307 | `{` | Opens the body of `decode_ids`. |
| 308 | `    const int layouts[2][2] = { { 3, 2 }, { 2, 1 } };` | `layouts`: the two layouts to try. Each entry holds the number of port bits and the number of device bits: first 3 and 2, then 2 and 1. |
| 309 | `    for (int l = 0; l < 2; l++) {` | Loop over the two layouts, in this order. |
| 310 | `        int pb = layouts[l][0], db = layouts[l][1], ok = 1;` | `pb`: the port bits of this layout. `db`: its device bits. `ok`: stays 1 as long as every id fits the mesh. |
| 311 | `        for (int i = 0; i < nnodes && ok; i++) {` | Loop over all nodes of both meshes. It stops at the first node that does not fit. |
| 312 | `            unsigned id = nodes[i].id;` | `id`: the id of the node. |
| 313 | `            int dev = id & ((1 << db) - 1), port = (id >> db) & ((1 << pb) - 1);` | `dev`: the lowest `db` bits of the id. `port`: the next `pb` bits above them. |
| 314 | `            unsigned xy = id >> (pb + db);` | `xy`: the bits of the id above the port and the device. |
| 315 | `            int x = (int)(xy >> 4), y = (int)(xy & 15);` | `x`: the bits of `xy` above its lowest 4 bits. `y`: the lowest 4 bits of `xy`. |
| 316 | `            if (x < 0 \|\| x >= MESH_X \|\| y < 0 \|\| y >= MESH_Y)` | Tests whether the position lies outside the mesh: `x` is not in 0 to 8, or `y` is not in 0 to 7. |
| 317 | `                ok = 0;` | Then this layout does not fit. |
| 318 | `            nodes[i].x = x; nodes[i].y = y; nodes[i].port = port; nodes[i].dev = dev;` | Stores column, row, port and device in the node. When the layout does not fit, the next layout writes these fields again. |
| 319 | `            nodes[i].dtc = dtc_of(x, y);` | Stores the DTC domain of the crosspoint (`dtc_of`). |
| 320 | `        }` | Ends the loop of line 311. |
| 321 | `        if (ok) {` | Tests whether every node fits under this layout. |
| 322 | `            fprintf(stderr, "node id layout: x 4 bits, y 4 bits, port %d bits, device %d bits\n", pb, db);` | Then prints the layout to the error output: 4 bits for `x`, 4 bits for `y`, and the numbers of port bits and device bits. |
| 323 | `            return;` | Then the function returns. The nodes keep the values of this layout. |
| 324 | `        }` | Ends the `if` of line 321. |
| 325 | `    }` | Ends the loop of line 309. |
| 326 | `    fprintf(stderr, "homelat: node ids do not decode onto a %d x %d mesh:", MESH_X, MESH_Y);` | No layout fits: prints the start of an error message with the size of the mesh, 9 x 8. |
| 327 | `    for (int i = 0; i < nnodes; i++)` | Loop over all nodes. |
| 328 | `        fprintf(stderr, " %d:0x%x", nodes[i].mesh, nodes[i].id);` | Adds the mesh and the id (hexadecimal) of each node to the message. |
| 329 | `    fprintf(stderr, "\n");` | Ends the message with a line break. |
| 330 | `    exit(2);` | The program ends with exit status 2. |
| 331 | `}` | Ends the function `decode_ids`. |

### Functions `flush_line` and `load_line`: the two instructions of a probe (lines 333 to 346)

| Line | Source | Explanation |
|---:|---|---|
| 333 | `/* ---- classification ---- */` | Comment: a section title. The functions that follow find the home node of each line, which the source calls classification. |
| 335 | `static inline void flush_line(const void *p)` | Starts the function `flush_line`. It removes the cache line that holds the address `p` from the caches. `inline` lets the compiler put the instructions directly into the caller. |
| 336 | `{` | Opens the body of `flush_line`. |
| 337 | `    __asm__ volatile("dc civac, %0\n\tdsb sy" : : "r"(p) : "memory");` | An asm statement with two Arm instructions. `dc civac` cleans and invalidates the cache line of the address in the register of `p`: when the line was changed, it is written back to memory, and then it is removed from the caches [Ref6]. `dsb sy` is a barrier: the core runs no later instruction before the flush and all memory accesses before it are complete [Ref6]. `volatile` forbids the compiler to remove the statement. `"r"(p)` puts `p` into a general register. `memory` tells the compiler that the statement touches memory. |
| 338 | `}` | Ends the function `flush_line`. |
| 340 | `static inline uint64_t load_line(const void *p)` | Starts the function `load_line`. It loads the 8 bytes at the address `p` and returns them. It returns only when the load is complete. |
| 341 | `{` | Opens the body of `load_line`. |
| 342 | `    uint64_t v;` | `v`: the loaded value. |
| 343 | `    __asm__ volatile("ldr %0, [%1]\n\tdsb sy" : "=r"(v) : "r"(p) : "memory");` | An asm statement with two Arm instructions. `ldr` loads 8 bytes from the address in the register of `p` into the register of `v`. `dsb sy` is the same barrier as in line 337: the core runs no later instruction before the load is complete. So a load of a probe is finished before the next flush starts. The load is written as an instruction, so the compiler cannot remove or move it. |
| 344 | `    return v;` | Returns the loaded value. |
| 345 | `}` | Ends the function `load_line`. |

### The marker file and the function `check_marker` (lines 347 to 362)

| Line | Source | Explanation |
|---:|---|---|
| 347 | `static const char *marker_path = "/tmp/positron-perf.RUNNING"; /* --marker PATH: stop if it appears */` | `marker_path`: the path of the marker file, `/tmp/positron-perf.RUNNING` unless the option `--marker` gives another path. The marker file exists while another user runs a performance test on CRB. By the comment the program stops when the file appears. |
| 348 | `static double marker_checked;` | `marker_checked`: the time of the last look at the marker file, on the clock of `now_s`. It starts at 0. |
| 350 | `/* Checked at least once per second inside every long loop: the shared-host rule. */` | Comment: the marker is checked at least once per second inside every long loop. The comment calls this the rule of the shared machine. The function itself looks at the file at most once per second. How often a loop calls it differs (lines 465 to 466, line 556, line 900, line 1125). |
| 351 | `static void check_marker(void)` | Starts the function `check_marker`. It ends the program with exit status 3 when the marker file exists. |
| 352 | `{` | Opens the body of `check_marker`. |
| 353 | `    double now = now_s();` | `now`: the time of this call. |
| 354 | `    if (now - marker_checked < 1.0)` | Tests whether the last look at the file was less than 1.0 s ago. |
| 355 | `        return;` | Then the function returns without a look. So a call from a fast loop costs little more than one clock read. |
| 356 | `    marker_checked = now;` | Keeps the time of this look. |
| 357 | `    if (access(marker_path, F_OK) == 0) {` | `access` with `F_OK` tests whether the file exists. It returns 0 when the file exists. |
| 358 | `        fprintf(stderr, "homelat: %s exists: stopping\n", marker_path);` | Then prints `homelat:`, the path and `exists: stopping` to the error output. |
| 359 | `        exit(3);` | Then the program ends with exit status 3. `exit` first writes the buffered rows of the open output files. |
| 360 | `    }` | Ends the `if` of line 357. |
| 361 | `}` | Ends the function `check_marker`. |

### Function `probe`: find the home node of one line with the counters (lines 363 to 412)

| Line | Source | Explanation |
|---:|---|---|
| 363 | `static int probe_loads = 256; /* --probe-loads: flush+load repeats inside one counter window */` | `probe_loads`: how many times one probe loads and flushes its line between the two reads of the counters, 256 by default (option `--probe-loads`). The comment calls the time between the two reads the counter window. |
| 364 | `static int probe_verbose = 3;  /* raw deltas of the first probes go to stderr */` | `probe_verbose`: the number of probes that still print their raw counter differences to the error output. It starts at 3. |
| 366 | `/* Returns the index in nodes[] of the home node of line i: the open node whose counter rose by` | Comment: the function returns the index in `nodes` of the home node of line `i`. The home node is the open node whose counter rose by ... The sentence goes on in line 367. An open node is a node whose counter is open at this moment. |
| 367 | ` * at least 3/4 of probe_loads while every other open node rose by at most 1/4 of it. Returns -1` | Comment: ... at least three quarters of `probe_loads`, while every other open node rose by at most one quarter of it. With 256 loads the two limits are 192 and 64. The next sentence starts here: the function returns -1 ... |
| 368 | ` * if no node rose that much (the home is not among the open nodes) and -2 if the rule fails` | Comment: ... when no node rose that much. The home is then not among the open nodes. The function returns -2 when the rule fails in another way. |
| 369 | ` * otherwise (noise; the caller retries). */` | Comment: the comment calls that case noise. The caller then repeats the probe (lines 468 to 469). |
| 370 | `static int probe(uint8_t *buf, uint64_t nlines, uint64_t i)` | Starts the function `probe`. It tests one line. `buf` is the buffer, `nlines` its number of lines, and `i` the index of the line. Nothing in a probe is timed. The result comes from the counters only. |
| 371 | `{` | Opens the body of `probe`. |
| 372 | `    uint8_t *p = buf + i * LINE;` | `p`: the address of line `i`. |
| 373 | `    uint64_t vals[DTC_LIMIT], en, run;` | `vals`: room for the counts of one group. `en`, `run`: the two times of a group. This function does not use them. |
| 374 | `    /* make the neighbours resident so a next-line prefetch adds no mesh request */` | Comment: the two neighbour lines are loaded first. They are then in the caches (the comment says resident). A load of the tested line can make the core fetch the next line in advance. With the neighbours in the caches, such a fetch sends no request to the mesh. |
| 375 | `    if (i > 0) sink = (void *)(uintptr_t)load_line(p - LINE);` | When the line is not the first of the buffer: loads the line before it (`load_line`) and stores the value into `sink`. |
| 376 | `    if (i + 1 < nlines) sink = (void *)(uintptr_t)load_line(p + LINE);` | When the line is not the last of the buffer: loads the line after it. |
| 377 | `    flush_line(p);` | Flushes the tested line (`flush_line`), before the first read of the counters. |
| 378 | `    for (int g = 0; g < ngroups; g++) {` | Loop over the open groups: the first read of the counters. |
| 379 | `        group_read(&groups[g], vals, &en, &run);` | Reads all counters of the group with one system call (`group_read`). |
| 380 | `        for (int k = 0; k < groups[g].n; k++)` | Loop over the counters of the group. |
| 381 | `            groups[g].before[k] = vals[k];` | Keeps each count as the start value `before`. |
| 382 | `    }` | Ends the loop of line 378. |
| 383 | `    for (int r = 0; r < probe_loads; r++) {` | Loop: `probe_loads` times (256 by default). |
| 384 | `        sink = (void *)(uintptr_t)load_line(p);` | Loads the tested line. The flush before it removed the line from the caches, so the core must fetch it again. The method assumes that this fetch is one request to the home node of the line, and that the counter of that node counts it. |
| 385 | `        flush_line(p);` | Flushes the line again. So the next load must fetch it again. |
| 386 | `    }` | Ends the loop of line 383. |
| 387 | `    int hit = -1, over_high = 0, over_low = 0;` | `hit`: the node of a counter that reached the upper limit. `over_high`: the number of counters that rose by at least three quarters of `probe_loads`. `over_low`: the number of counters whose rise lies between the two limits. |
| 388 | `    uint64_t best = 0, second = 0;` | `best`, `second`: the largest and the second largest rise. Only the message of line 402 uses them. |
| 389 | `    int best_node = -1, second_node = -1;` | `best_node`, `second_node`: the nodes with these two rises. |
| 390 | `    for (int g = 0; g < ngroups; g++) {` | Loop over the open groups: the second read of the counters. |
| 391 | `        group_read(&groups[g], vals, &en, &run);` | Reads all counters of the group. |
| 392 | `        for (int k = 0; k < groups[g].n; k++) {` | Loop over the counters of the group. |
| 393 | `            uint64_t d = vals[k] - groups[g].before[k];` | `d`: the rise of this counter between the two reads. The counter counts every event of its type at this node in that time. So `d` also holds requests that other programs or the Linux kernel caused. |
| 394 | `            int node = groups[g].node_idx[k];` | `node`: the index of the node of this counter. |
| 395 | `            if (d >= (uint64_t)probe_loads * 3 / 4) { over_high++; hit = node; }` | A rise of at least `probe_loads * 3 / 4` (192 with 256 loads): counts the counter in `over_high` and keeps its node in `hit`. |
| 396 | `            else if (d > (uint64_t)probe_loads / 4) over_low++;` | A rise above `probe_loads / 4` (64 with 256 loads) that is below the upper limit: counts the counter in `over_low`. |
| 397 | `            if (d > best) { second = best; second_node = best_node; best = d; best_node = node; }` | Keeps the largest rise. The value that was the largest before moves to second place. |
| 398 | `            else if (d > second) { second = d; second_node = node; }` | Or keeps the second largest rise. |
| 399 | `        }` | Ends the loop of line 392. |
| 400 | `    }` | Ends the loop of line 390. |
| 401 | `    if (probe_verbose > 0) {` | Tests whether raw values must still be printed. |
| 402 | `        fprintf(stderr, "  probe line %lu: best mesh %d node 0x%x +%lu, second mesh %d node 0x%x +%lu, %d node(s) >= %d, %d node(s) in between\n",` | Prints one line to the error output: the line index, then mesh, node id and rise of the best node, then the same for the second node, then the number of nodes at or above the upper limit, that limit, and the number of nodes between the two limits. |
| 403 | `                (unsigned long)i, best_node >= 0 ? nodes[best_node].mesh : -1, best_node >= 0 ? nodes[best_node].id : 0, (unsigned long)best,` | Continues the call of line 402: the values of the best node. Mesh -1 and id 0 are printed when no counter rose. |
| 404 | `                second_node >= 0 ? nodes[second_node].mesh : -1, second_node >= 0 ? nodes[second_node].id : 0, (unsigned long)second,` | Continues the call: the values of the second node. |
| 405 | `                over_high, probe_loads * 3 / 4, over_low);` | Continues the call: `over_high`, the upper limit and `over_low`. |
| 406 | `        probe_verbose--;` | Counts down. So only the first 3 probes of the run print this line. |
| 407 | `    }` | Ends the `if` of line 401. |
| 408 | `    if (over_high == 1 && over_low == 0)` | The rule: exactly one counter reached the upper limit, and no counter lies between the two limits. |
| 409 | `        return hit;` | Then returns the node of that counter. It is taken as the home of the line. |
| 410 | `    return over_high == 0 && over_low == 0 ? -1 : -2;` | In every other case: returns -1 when no counter rose above the lower limit. Returns -2 when the result is unclear: two or more counters reached the upper limit, or a counter lies between the limits. |
| 411 | `}` | Ends the function `probe`. |

### Function `node_add_line`: append a line to the list of a node (lines 413 to 423)

| Line | Source | Explanation |
|---:|---|---|
| 413 | `static void node_add_line(struct node *n, uint32_t line)` | Starts the function `node_add_line`. It appends the line index `line` to the line list of the node `n`. |
| 414 | `{` | Opens the body of `node_add_line`. |
| 415 | `    if (n->nlines == n->cap) {` | Tests whether the list is full. |
| 416 | `        n->cap = n->cap ? n->cap * 2 : 1024;` | Then doubles the room of the list. An empty list gets room for 1024 entries. |
| 417 | `        n->lines = realloc(n->lines, (size_t)n->cap * sizeof *n->lines);` | `realloc` makes the list that large and keeps its content. |
| 418 | `        if (!n->lines)` | Tests whether `realloc` failed. |
| 419 | `            die("realloc");` | Then `die` prints `homelat: realloc:` with the reason and ends the program with exit status 2. |
| 420 | `    }` | Ends the `if` of line 415. |
| 421 | `    n->lines[n->nlines++] = line;` | Stores the line index at the end of the list and adds 1 to the count. |
| 422 | `}` | Ends the function `node_add_line`. |

### Function `classify`: start of a pass, open at most 8 counters per mesh and DTC domain (lines 424 to 456)

| Line | Source | Explanation |
|---:|---|---|
| 424 | `/* home[i] = node index, -1 = not found by any node, -2 = ambiguous after retries */` | Comment: the meaning of the array `home`. `home[i]` is the index of the home node of line `i`. -1 means that no node was found. By the comment -2 means unclear after the retries. The code never stores -2: such a line keeps -1 (lines 474 to 475). |
| 425 | `static void classify(uint8_t *buf, uint64_t nlines, int16_t *home, int retries)` | Starts the function `classify`. It finds the home node of every line of the buffer. `home` receives the result. `retries` is the number of extra probes for a line with an unclear result. |
| 426 | `{` | Opens the body of `classify`. |
| 427 | `    for (uint64_t i = 0; i < nlines; i++)` | Loop over all lines of the buffer. |
| 428 | `        home[i] = -1;` | Marks every line as not classified (-1). |
| 429 | `    int pass = 0, left;` | `pass`: the number of the pass, counted from 1. `left`: the number of lines without a home after a pass. |
| 430 | `    for (;;) {` | Starts the loop over the passes. The loop has no end condition of its own. Line 458 and line 510 leave it. |
| 431 | `        /* open the next batch: one group per (mesh, dtc) with at most DTC_LIMIT nodes */` | Comment: each pass opens the next batch of counters: one group per mesh and DTC domain, with at most `DTC_LIMIT` (8) nodes. |
| 432 | `        int opened = 0;` | `opened`: the number of counters opened in this pass. |
| 433 | `        ngroups = 0;` | No group is open yet. |
| 434 | `        for (int m = 0; m < NMESH; m++)` | Loop over the two meshes. |
| 435 | `            for (int d = 0; d < 4; d++) {` | Loop over the 4 DTC domains of the mesh. Its body ends in line 456. |
| 436 | `                struct group *g = &groups[ngroups];` | `g`: the next free group. |
| 437 | `                g->n = 0; g->leader_fd = -1;` | The group is empty and has no leader yet. |
| 438 | `                for (int k = 0; k < nnodes && g->n < DTC_LIMIT; k++) {` | Loop over all nodes, as long as the group has fewer than 8 counters. |
| 439 | `                    struct node *n = &nodes[k];` | `n`: the node. |
| 440 | `                    if (n->done \|\| n->mesh != m \|\| n->dtc != d)` | Tests whether the node already had its pass (`done`), or lies on another mesh, or lies in another DTC domain. |
| 441 | `                        continue;` | Then skips the node. |
| 442 | `                    n->fd = perf_open(m, n->id, g->leader_fd);` | Opens the counter of the node (`perf_open`). For the first node of the group `leader_fd` is -1, so this counter becomes the leader. Each further counter joins the group of the leader. |
| 443 | `                    if (n->fd < 0) {` | Tests whether the counter did not open. |
| 444 | `                        if (g->n == 0)` | Tests whether it was the first counter of the group. |
| 445 | `                            die("perf_event_open for a discovered node");` | Then `die` prints `homelat: perf_event_open for a discovered node:` with the reason and ends the program with exit status 2. |
| 446 | `                        fprintf(stderr, "mesh %d node 0x%x: cannot join its group (%s), left for a later pass\n", m, n->id, strerror(errno));` | For a later counter of the group: prints to the error output that the node cannot join its group, with the reason, and that it is left for a later pass. |
| 447 | `                        break;` | Stops filling this group. The node is not marked `done`, so a later pass takes it. |
| 448 | `                    }` | Ends the `if` of line 443. |
| 449 | `                    if (g->n == 0)` | Tests whether this is the first counter of the group. |
| 450 | `                        g->leader_fd = n->fd;` | Then keeps its file descriptor as the leader of the group. |
| 451 | `                    g->node_idx[g->n++] = k;` | Adds the node to the group. |
| 452 | `                    opened++;` | Counts the opened counter. |
| 453 | `                }` | Ends the loop of line 438. |
| 454 | `                if (g->n)` | Tests whether the group got at least one counter. |
| 455 | `                    ngroups++;` | Then the group counts as open. |
| 456 | `            }` | Ends the loop of line 435. This is also the end of one pass of the loop of line 434. |

### Function `classify`: probe every line that has no home yet (lines 457 to 486)

| Line | Source | Explanation |
|---:|---|---|
| 457 | `        if (!opened)` | Tests whether no counter was opened. Every node has had its pass in that case. |
| 458 | `            break;` | Then leaves the loop over the passes. |
| 459 | `        pass++;` | Counts the pass. |
| 460 | `        double t0 = now_s();` | Reads the clock: `t0`, the start of the pass. Only the message of line 507 uses it, for the duration of the pass. |
| 461 | `        long classified = 0, ambiguous = 0, none = 0;` | Three counts for this pass: lines that got a home (`classified`), lines that stayed unclear after the retries (`ambiguous`), and lines for which no open node rose (`none`). |
| 462 | `        for (uint64_t i = 0; i < nlines; i++) {` | Loop over all lines of the buffer, in address order. |
| 463 | `            if (home[i] != -1)` | Tests whether the line already has a home. |
| 464 | `                continue;` | Then skips the line. |
| 465 | `            if ((i & 1023) == 0)` | Tests whether the line index is a multiple of 1024. This test stands after the skip of lines 463 to 464. So in a later pass it is reached only for a line that has no home yet. |
| 466 | `                check_marker();` | Then looks for the marker file (`check_marker`). |
| 467 | `            int r = probe(buf, nlines, i);` | Probes the line (`probe`). `r` is a node index, or -1, or -2. |
| 468 | `            for (int t = 0; t < retries && r == -2; t++)` | Loop for the retries: at most `retries` more probes (3 by default), as long as the result is -2. |
| 469 | `                r = probe(buf, nlines, i);` | Probes the line again. |
| 470 | `            if (r >= 0) {` | Tests whether a home node was found. |
| 471 | `                home[i] = (int16_t)r;` | Then stores the node index as the home of the line. |
| 472 | `                node_add_line(&nodes[r], (uint32_t)i);` | Then appends the line to the line list of that node (`node_add_line`). |
| 473 | `                classified++;` | Then counts the line as classified. |
| 474 | `            } else if (r == -2) {` | The other case: the result is still -2 after the retries. |
| 475 | `                ambiguous++;` | Counts the line as unclear. `home[i]` stays -1, so the next pass probes the line again. |
| 476 | `            } else {` | The last case: no open node rose. The home of the line is then a node whose counter is not open in this pass. |
| 477 | `                none++;` | Counts it. The next pass probes the line again. |
| 478 | `            }` | Ends the chain of tests that began in line 470. |
| 479 | `            /* half of the nodes are open in pass 1, so about half of the first lines must classify */` | Comment: half of the nodes have their counter open in pass 1. So about half of the first lines must get a home in pass 1. |
| 480 | `            if (pass == 1 && i == 255 && classified == 0) {` | Tests in pass 1, at the line with the index 255: did none of the first 256 lines get a home? |
| 481 | `                fprintf(stderr, "homelat: none of the first 256 lines was classified (%ld ambiguous, the rest raised no counter). "` | Then prints an error message. It says that none of the first 256 lines was classified, gives the number of unclear lines, and says that the other lines raised no counter. |
| 482 | `                        "If the probes above show one node far ahead, raise --probe-loads; if none stands out, the event does not count these loads: "` | Continues the message with advice. When the printed probes show one node with a much larger rise than the others, raise `--probe-loads`. When no node shows that, the event does not count these loads. |
| 483 | `                        "try --event hns_pocq_reqs_recvd_all or hns_slc_sf_cache_access_all\n", ambiguous);` | Continues the message: try the event `hns_pocq_reqs_recvd_all` or `hns_slc_sf_cache_access_all` with the option `--event`. `ambiguous` is the value for the message. |
| 484 | `                exit(2);` | Then the program ends with exit status 2. |
| 485 | `            }` | Ends the `if` of line 480. |
| 486 | `        }` | Ends the loop of line 462. |

### Function `classify`: check the counters of the pass, close them and report (lines 487 to 518)

| Line | Source | Explanation |
|---:|---|---|
| 487 | `        /* a group that was not running the whole time was multiplexed: results unusable */` | Comment: a group that was not counting during the whole pass was multiplexed. That means Linux let its counters and other counters use the same hardware counters one after the other. The results of the pass cannot be used then. |
| 488 | `        for (int g = 0; g < ngroups; g++) {` | Loop over the open groups. |
| 489 | `            uint64_t vals[DTC_LIMIT], en, run;` | `vals`, `en`, `run`: room for the counts and the two times of one group. |
| 490 | `            group_read(&groups[g], vals, &en, &run);` | Reads the group once more, for its two times. |
| 491 | `            if (en != run) {` | Tests whether the time enabled differs from the time running. |
| 492 | `                fprintf(stderr, "homelat: a counter group (mesh %d node 0x%x) ran %.1f%% of the time: multiplexed, too many counters per DTC\n",` | Then prints an error message: the mesh and the id of the first node of the group, and the share of the time for which the group counted, in percent. The message names the cause: multiplexed, too many counters per DTC. |
| 493 | `                        nodes[groups[g].node_idx[0]].mesh, nodes[groups[g].node_idx[0]].id, 100.0 * (double)run / (double)en);` | Continues the call of line 492: the values. |
| 494 | `                exit(2);` | Then the program ends with exit status 2. |
| 495 | `            }` | Ends the `if` of line 491. |
| 496 | `            for (int k = 0; k < groups[g].n; k++) {` | Loop over the counters of the group. |
| 497 | `                struct node *n = &nodes[groups[g].node_idx[k]];` | `n`: the node of the counter. |
| 498 | `                close(n->fd);` | Closes the counter. |
| 499 | `                n->fd = -1;` | Marks that no counter of the node is open. |
| 500 | `                n->done = 1;` | Marks that the node has had its pass. |
| 501 | `            }` | Ends the loop of line 496. |
| 502 | `        }` | Ends the loop of line 488. |
| 503 | `        ngroups = 0;` | No group is open any more. |
| 504 | `        left = 0;` | Sets the count of lines without a home to 0. |
| 505 | `        for (uint64_t i = 0; i < nlines; i++)` | Loop over all lines. |
| 506 | `            left += home[i] == -1;` | Counts the lines that still have no home. |
| 507 | `        fprintf(stderr, "pass %d: %d counters, %ld lines classified, %ld ambiguous after retries, %ld raised no open node, %d left, %.1f s\n",` | Prints the summary of the pass to the error output: the pass number, the counters opened, the lines classified, the lines unclear after the retries, the lines for which no open node rose, the lines left, and the duration of the pass in seconds. |
| 508 | `                pass, opened, classified, ambiguous, none, left, now_s() - t0);` | Continues the call of line 507: the values. `now_s() - t0` is the duration. |
| 509 | `        if (!left)` | Tests whether every line has a home. |
| 510 | `            break;` | Then leaves the loop over the passes. |
| 511 | `    }` | Ends the loop of line 430. |
| 512 | `    long unknown = 0;` | `unknown`: the number of lines without a home at the end. |
| 513 | `    for (uint64_t i = 0; i < nlines; i++)` | Loop over all lines. |
| 514 | `        unknown += home[i] < 0;` | Counts every line whose `home` value is below 0. |
| 515 | `    fprintf(stderr, "classification: %lu lines, %ld without a home (%.2f%%)\n", (unsigned long)nlines, unknown,` | Prints the result to the error output: the number of lines, the number without a home, and their share in percent. |
| 516 | `            100.0 * (double)unknown / (double)nlines);` | Continues the call of line 515: the share. |
| 517 | `}` | Ends the function `classify`. |

### Function `verify_classification`: probe a sample of lines again with a single counter (lines 519 to 562)

| Line | Source | Explanation |
|---:|---|---|
| 519 | `/* Verification (reviewer's request): a sample of classified lines is probed again with only the` | Comment: the verification, which a reviewer asked for. A sample of the classified lines is probed again. This time only the counter of the node that the line was assigned to is open. The sentence goes on in line 520. |
| 520 | ` * assigned node's counter open (plus one control node that is not the home). The assigned node` | Comment: one more counter is open: that of a control node, a node that is not the home of the line. The next sentence starts here: the assigned node ... |
| 521 | ` * must rise by >= 3/4 of the loads and the control by <= 1/4. Returns the agreement rate. */` | Comment: ... must rise by at least three quarters of the loads, and the control node by at most one quarter. The function returns the agreement rate: the share of the tested lines whose second probe gave the same home. |
| 522 | `static double verify_classification(uint8_t *buf, uint64_t nlines, const int16_t *home, int sample, long *control_false)` | Starts the function `verify_classification`. `sample` is the number of random lines to draw. `control_false` receives the number of probes in which the control node rose. The other parameters are the buffer, its number of lines and the array of the homes. |
| 523 | `{` | Opens the body of `verify_classification`. |
| 524 | `    long agree = 0, tested = 0;` | `agree`: the number of lines whose second probe gave the same home. `tested`: the number of lines that were probed again. |
| 525 | `    *control_false = 0;` | Sets the count of the caller to 0. |
| 526 | `    for (int s = 0; s < sample; s++) {` | Loop: `sample` draws. |
| 527 | `        uint64_t i = xorshift64() % nlines;` | `i`: a random line index: the next random number modulo the number of lines. |
| 528 | `        if (home[i] < 0)` | Tests whether the line has no home. |
| 529 | `            continue;` | Then skips this draw. It does not count as tested. So fewer than `sample` lines can be tested. |
| 530 | `        int k = home[i], c = (k + 1 + (int)(xorshift64() % (uint64_t)(nnodes - 1))) % nnodes; /* a different node */` | `k`: the home node of the line. `c`: the control node. It is `k` plus a random offset from 1 to `nnodes - 1`, modulo `nnodes`. So it is a random node that is never `k`. |
| 531 | `        struct node *n = &nodes[k], *cn = &nodes[c];` | `n`, `cn`: the table entries of the home node and of the control node. |
| 532 | `        struct group *g = &groups[0], *cg = &groups[1];` | `g`, `cg`: the first two entries of the group table. They are used for the home node and for the control node. |
| 533 | `        n->fd = perf_open(n->mesh, n->id, -1);` | Opens the counter of the home node as a group of its own (`perf_open` with `-1`). |
| 534 | `        cn->fd = perf_open(cn->mesh, cn->id, -1);` | Opens the counter of the control node as a group of its own. |
| 535 | `        if (n->fd < 0 \|\| cn->fd < 0)` | Tests whether one of the two did not open. |
| 536 | `            die("perf_event_open in verification");` | Then `die` prints `homelat: perf_event_open in verification:` with the reason and ends the program with exit status 2. |
| 537 | `        g->leader_fd = n->fd; g->n = 1; g->node_idx[0] = k;` | Sets up group 0: its leader is the counter of the home node, and it has 1 counter. |
| 538 | `        cg->leader_fd = cn->fd; cg->n = 1; cg->node_idx[0] = c;` | Sets up group 1: its leader is the counter of the control node, and it has 1 counter. |
| 539 | `        ngroups = 2;` | Two groups are open. `probe` reads exactly these two. |
| 540 | `        int saved = probe_verbose;` | Keeps the value of `probe_verbose`. |
| 541 | `        probe_verbose = 0;` | Sets it to 0. So the probes of the verification print no raw values. |
| 542 | `        uint64_t vals[DTC_LIMIT], en, run, c0;` | `vals`, `en`, `run`: room for one group read. `c0`: the count of the control node before the probe. |
| 543 | `        group_read(cg, vals, &en, &run);` | Reads the counter of the control node (`group_read`). |
| 544 | `        c0 = vals[0];` | Keeps its count in `c0`. |
| 545 | `        int r = probe(buf, nlines, i);` | Probes the line again (`probe`), now with these two counters only. |
| 546 | `        probe_verbose = saved;` | Restores `probe_verbose`. |
| 547 | `        group_read(cg, vals, &en, &run);` | Reads the counter of the control node again. |
| 548 | `        tested++;` | Counts the line as tested. |
| 549 | `        if (r == k)` | Tests whether the probe returned the assigned home node. |
| 550 | `            agree++;` | Then counts the line as confirmed. |
| 551 | `        if (vals[0] - c0 > (uint64_t)probe_loads / 4) /* the control rose, whatever the verdict (reviewer's request) */` | Tests whether the control node rose by more than one quarter of `probe_loads` between the reads of line 543 and line 547. By the comment this is counted whatever the probe returned, as a reviewer asked. |
| 552 | `            (*control_false)++;` | Then adds 1 to the count of the caller. |
| 553 | `        close(n->fd); close(cn->fd);` | Closes both counters. |
| 554 | `        n->fd = cn->fd = -1;` | Marks both nodes as having no open counter. |
| 555 | `        ngroups = 0;` | No group is open any more. |
| 556 | `        check_marker();` | Looks for the marker file once per tested line (`check_marker`). |
| 557 | `    }` | Ends the loop of line 526. |
| 558 | `    fprintf(stderr, "verification: %ld of %ld sampled lines confirmed by a lone counter (%.2f%%), the control node rose in %ld probes\n",` | Prints the result to the error output: how many of the tested lines were confirmed by a counter that was alone in its group, the share in percent, and the number of probes in which the control node rose. |
| 559 | `            agree, tested, tested ? 100.0 * (double)agree / (double)tested : 0.0, *control_false);` | Continues the call of line 558: the values. The share is printed as 0 when no line was tested. |
| 560 | `    return tested ? (double)agree / (double)tested : 0.0;` | Returns the share of confirmed lines as a number from 0 to 1. It is 0 when no line was tested. |
| 561 | `}` | Ends the function `verify_classification`. |

### Function `classify_fake`: invented home nodes for the option `--no-perf` (lines 563 to 578)

| Line | Source | Explanation |
|---:|---|---|
| 563 | `/* --no-perf: fake homes so the chase code can be exercised without root */` | Comment: the option `--no-perf` gives invented homes. So the chase code can be run without root rights. |
| 564 | `static void classify_fake(uint64_t nlines, int16_t *home)` | Starts the function `classify_fake`. It invents 128 nodes and gives every line one of them. It opens no counter. |
| 565 | `{` | Opens the body of `classify_fake`. |
| 566 | `    nnodes = 128;` | The node table gets 128 entries. |
| 567 | `    for (int k = 0; k < nnodes; k++) {` | Loop over the 128 invented nodes. |
| 568 | `        nodes[k].mesh = k / 64;` | `mesh`: 0 for the nodes 0 to 63, and 1 for the nodes 64 to 127. |
| 569 | `        nodes[k].id = (uint16_t)k;` | `id`: the number of the node itself. |
| 570 | `        nodes[k].x = 1 + (k % 64) / 10; nodes[k].y = 1 + (k % 64) % 5; nodes[k].dev = k & 1;` | Made-up positions. With `m` for `k % 64`: `x` is 1 plus `m / 10`, so 1 to 7. `y` is 1 plus `m % 5`, so 1 to 5. `dev` is the lowest bit of `k`. |
| 571 | `        nodes[k].fd = -1;` | Marks that no counter of the node is open. |
| 572 | `    }` | Ends the loop of line 567. |
| 573 | `    for (uint64_t i = 0; i < nlines; i++) {` | Loop over all lines of the buffer. |
| 574 | `        home[i] = (int16_t)(i % 128);` | The home of line `i` is the node `i % 128`. |
| 575 | `        node_add_line(&nodes[i % 128], (uint32_t)i);` | Appends the line to the line list of that node (`node_add_line`). |
| 576 | `    }` | Ends the loop of line 573. |
| 577 | `}` | Ends the function `classify_fake`. |

### Functions `cmp_u32` and `build_chain`: one cycle of pointers through the lines of a set (lines 579 to 618)

| Line | Source | Explanation |
|---:|---|---|
| 579 | `/* ---- latency ---- */` | Comment: a section title. The functions that follow measure the latency. |
| 581 | `static int cmp_u32(const void *a, const void *b)` | Starts the function `cmp_u32`. `qsort` calls it to compare two 32-bit numbers (line 597). |
| 582 | `{` | Opens the body of `cmp_u32`. |
| 583 | `    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;` | `x`, `y`: the two numbers. |
| 584 | `    return x < y ? -1 : x > y;` | Returns -1 when `x` is smaller, 1 when `x` is larger, and 0 when both are equal. This gives a rising order. |
| 585 | `}` | Ends the function `cmp_u32`. |
| 587 | `/* Sattolo cycle over the given lines, stored in 8-byte slot s of each line. The lines must be` | Comment: the function builds a cycle of the kind of Sattolo over the given lines. The pointers are stored in one 8-byte word of each line, which the comment calls slot `s` and the code calls `slot`. The next sentence starts here: the lines must be ... |
| 588 | ` * distinct: a duplicate would overwrite a successor and close a shorter cycle, so the timed pass` | Comment: ... distinct. A line that stands in the list twice would have its pointer overwritten. That would close a shorter cycle. So the timed pass ... |
| 589 | ` * would repeat lines (reviewer's catch, 2026-11-02). Sattolo's shuffle yields one n-cycle over the` | Comment: ... would visit some lines again. By the comment a reviewer found this on 2026-11-02. The next sentence starts here: the shuffle of Sattolo gives one cycle of length `n` over the ... |
| 590 | ` * indices, so with distinct lines every line is visited exactly once before the start recurs. */` | Comment: ... indices. So with distinct lines every line is visited exactly once before the walk is back at its start. |
| 591 | `static void build_chain(uint8_t *buf, const uint32_t *lines, int n, int slot)` | Starts the function `build_chain`. It writes one chain into the buffer `buf`: a cycle of pointers through the `n` lines whose indices stand in `lines`. `slot` is the 8-byte word of each line that holds the pointer of this chain. No part of this function is timed. |
| 592 | `{` | Opens the body of `build_chain`. |
| 593 | `    uint32_t *perm = malloc((size_t)n * sizeof *perm), *sorted = malloc((size_t)n * sizeof *sorted);` | `perm`: will hold the numbers 0 to `n - 1` in a random order. `sorted`: will hold a sorted copy of the line indices. `malloc` reserves both. |
| 594 | `    if (!perm \|\| !sorted)` | Tests whether a `malloc` call failed. |
| 595 | `        die("malloc");` | Then `die` prints `homelat: malloc:` with the reason and ends the program with exit status 2. |
| 596 | `    memcpy(sorted, lines, (size_t)n * sizeof *sorted);` | Copies the line indices to `sorted`. |
| 597 | `    qsort(sorted, (size_t)n, sizeof *sorted, cmp_u32);` | Sorts the copy in rising order. |
| 598 | `    for (int i = 1; i < n; i++)` | Loop over the sorted copy, from its second entry. |
| 599 | `        if (sorted[i] == sorted[i - 1]) {` | Tests whether two neighbours are equal. Such a line stands in the list twice. |
| 600 | `            fprintf(stderr, "homelat: duplicate line %u in a chain of %d lines\n", sorted[i], n);` | Then prints `homelat: duplicate line`, the line index and the length of the chain to the error output. |
| 601 | `            exit(2);` | Then the program ends with exit status 2. |
| 602 | `        }` | Ends the `if` of line 599. |
| 603 | `    free(sorted);` | Releases the sorted copy. |
| 604 | `    for (int i = 0; i < n; i++)` | Loop over the `n` positions. |
| 605 | `        perm[i] = (uint32_t)i;` | Fills `perm` with 0, 1, 2 and so on. |
| 606 | `    for (int i = n - 1; i > 0; i--) {` | The shuffle of Sattolo: `i` goes from `n - 1` down to 1. |
| 607 | `        int j = (int)(xorshift64() % (uint64_t)i);` | `j`: a random position from 0 to `i - 1`. |
| 608 | `        uint32_t t = perm[i]; perm[i] = perm[j]; perm[j] = t;` | Swaps the entries `i` and `j` of `perm`. |
| 609 | `    }` | Ends the loop of line 606. |
| 610 | `    /* perm is a single cycle: line lines[perm[i]] points to line lines[perm[(i+1) % n]] */` | Comment: `perm` is a single cycle. The line `lines[perm[i]]` points to the line `lines[perm[(i+1) % n]]`. So the code uses `perm` as the order of the walk: each line points to the line at the next place of the order, and the line at the last place points to the line at the first place. |
| 611 | `    for (int i = 0; i < n; i++) {` | Loop over the `n` places of the order. |
| 612 | `        uint8_t *from = buf + (uint64_t)lines[perm[i]] * LINE + slot * 8;` | `from`: the address of word `slot` of the line at place `i` of the order. |
| 613 | `        uint8_t *to = buf + (uint64_t)lines[perm[(i + 1) % n]] * LINE + slot * 8;` | `to`: the address of word `slot` of the line at the next place. After the last place comes the first (`% n`). |
| 614 | `        *(uint64_t *)from = (uint64_t)(uintptr_t)to;` | Stores the address `to` into the word at `from`. This is a write to the line. |
| 615 | `    }` | Ends the loop of line 611. |
| 616 | `    free(perm);` | Releases `perm`. |
| 617 | `}` | Ends the function `build_chain`. |

### Function `chase`: the loads that are timed (lines 619 to 627)

| Line | Source | Explanation |
|---:|---|---|
| 619 | `__attribute__((noinline)) static void *chase(void *p, int loads)` | Starts the function `chase`, the loop that is timed. It follows the pointers that start at `p` for `loads` loads and returns the last pointer. `noinline` forbids the compiler to merge the function into its caller. |
| 620 | `{` | Opens the body of `chase`. |
| 621 | `    for (int i = 0; i < loads; i += 8) {` | The loop. One loop pass does 8 loads (lines 622 to 623), and `i` grows by 8. So the loop is unrolled 8 times. Every count that reaches this function is a multiple of 8 (line 839, line 961, line 1091, line 1122). So the function does exactly `loads` loads. |
| 622 | `        p = *(void **)p; p = *(void **)p; p = *(void **)p; p = *(void **)p;` | Loads 1 to 4 of the loop pass. Each statement loads the 8-byte pointer that is stored at the address `p` and makes it the new `p`. The loaded value is the address of the next load. So a load cannot start before the load before it has delivered its value. |
| 623 | `        p = *(void **)p; p = *(void **)p; p = *(void **)p; p = *(void **)p;` | Loads 5 to 8 of the loop pass: the same statement four more times. A loaded value is used for nothing but the next address. |
| 624 | `    }` | Ends the loop of line 621. |
| 625 | `    return p;` | Returns the pointer that the last load delivered. After a whole cycle this is the start pointer again. |
| 626 | `}` | Ends the function `chase`. |

### The evictor order and the function `evict_init` (lines 628 to 645)

| Line | Source | Explanation |
|---:|---|---|
| 628 | `static uint32_t *evict_order; /* random permutation of the evictor's lines */` | `evict_order`: the order in which `evict` reads the lines of the evictor buffer. By the comment it is a random order (permutation) of the line numbers of the evictor. |
| 630 | `static void evict_init(void)` | Starts the function `evict_init`. It puts the line numbers of the evictor buffer into a new random order. |
| 631 | `{` | Opens the body of `evict_init`. |
| 632 | `    uint32_t n = (uint32_t)(evict_bytes / LINE);` | `n`: the number of 64-byte lines of the evictor buffer. 8 MiB gives 131072 lines. |
| 633 | `    if (!evict_order) {` | Tests whether the order array does not exist yet. |
| 634 | `        evict_order = malloc((n ? n : 1) * sizeof *evict_order);` | Then reserves it: one 4-byte entry per line, and at least one entry. |
| 635 | `        if (!evict_order)` | Tests whether `malloc` failed. |
| 636 | `            die("malloc");` | Then `die` prints `homelat: malloc:` with the reason and ends the program with exit status 2. |
| 637 | `    }` | Ends the `if` of line 633. |
| 638 | `    for (uint32_t i = 0; i < n; i++)` | Loop over the `n` entries. |
| 639 | `        evict_order[i] = i;` | Fills the array with 0, 1, 2 and so on. |
| 640 | `    for (uint32_t i = n - 1; i > 0; i--) {` | A Fisher-Yates shuffle: `i` goes from the last entry down to 1. |
| 641 | `        uint32_t j = (uint32_t)(xorshift64() % (i + 1)), t = evict_order[i];` | `j`: a random position from 0 to `i`. `t`: the entry at position `i`. |
| 642 | `        evict_order[i] = evict_order[j]; evict_order[j] = t;` | Swaps the entries `i` and `j`. |
| 643 | `    }` | Ends the loop of line 640. |
| 644 | `}` | Ends the function `evict_init`. |

### Functions `evict` and `cmp_double`: push the lines of the set out of L1 and L2 (lines 646 to 665)

| Line | Source | Explanation |
|---:|---|---|
| 646 | `/* Independent loads in random order, a new order every call: no stream for a prefetcher to` | Comment: the loads of the evictor are independent of each other and run in a random order, and every call uses a new order. So a prefetcher finds no stream of addresses that it could follow. The sentence goes on in line 647. |
| 647 | ` * detect, and no repeated sequence for the temporal prefetcher to learn. Measured 2026-11-02:` | Comment: and the temporal prefetcher finds no order that repeats and that it could learn. Then the comment gives a measurement of 2026-11-02, which line 648 holds. |
| 648 | ` * with one fixed order the timed passes fell from 30 ns to 7 ns from the second repeat on. */` | Comment: with one fixed order, the timed passes fell from 30 ns to 7 ns per load from the second repeat on. |
| 649 | `static void evict(const uint8_t *ev)` | Starts the function `evict`. It loads one 8-byte value from every line of the evictor buffer `ev`, in a random order. Its purpose is to push the lines of the measured set out of L1 and L2 of the core (lines 17 to 19). It is not timed. |
| 650 | `{` | Opens the body of `evict`. |
| 651 | `    uint64_t s = 0;` | `s`: the sum of the loaded values. |
| 652 | `    uint32_t n = (uint32_t)(evict_bytes / LINE);` | `n`: the number of lines of the evictor buffer. |
| 653 | `    if (evict_reshuffle)` | Tests whether every call must use a new order. This is the default (line 51). |
| 654 | `        evict_init();` | Then shuffles the order again (`evict_init`). |
| 655 | `    for (uint32_t i = 0; i < n; i++)` | Loop over all `n` lines of the evictor. |
| 656 | `        s += *(const uint64_t *)(ev + (uint64_t)evict_order[i] * LINE);` | Loads the first 8 bytes of the line whose number stands at place `i` of the order, and adds the value to `s`. The address of a load does not depend on the value of another load. The comment calls such loads independent. |
| 657 | `    sink = (void *)(uintptr_t)s;` | Stores the sum into `sink`. So the loads have a result that is used. |
| 658 | `}` | Ends the function `evict`. |
| 660 | `static int cmp_double(const void *a, const void *b)` | Starts the function `cmp_double`. `qsort` calls it to compare two `double` values (line 759). |
| 661 | `{` | Opens the body of `cmp_double`. |
| 662 | `    double x = *(const double *)a, y = *(const double *)b;` | `x`, `y`: the two values. |
| 663 | `    return x < y ? -1 : x > y;` | Returns -1 when `x` is smaller, 1 when `x` is larger, and 0 when both are equal. This gives a rising order. |
| 664 | `}` | Ends the function `cmp_double`. |

### Function `fill_random`: load every line of the set once (lines 666 to 685)

| Line | Source | Explanation |
|---:|---|---|
| 666 | `/* Loads every line of the set once, independent loads in a new random order each call. A` | Comment: the function loads every line of the set once. The loads are independent of each other, and each call uses a new random order. The next sentence starts at the end of this line. |
| 667 | ` * dependent fill chain walked every repeat was learned by the temporal prefetcher, which then` | Comment: an earlier fill walked a chain of dependent loads in every repeat. By the comment the temporal prefetcher learned that chain. |
| 668 | ` * replayed it during the timed pass and pulled the whole set into L2. */` | Comment: by the comment the prefetcher then fetched the chain again during the timed pass. This brought the whole set into L2. |
| 669 | `static void fill_random(const uint8_t *buf, const uint32_t *lines, int n)` | Starts the function `fill_random`. It loads one 8-byte value from each of the `n` lines whose indices stand in `lines`. This is the fill step of a measurement. It is not timed. |
| 670 | `{` | Opens the body of `fill_random`. |
| 671 | `    uint64_t s = 0, start = xorshift64() % (uint64_t)n, step = (xorshift64() % (uint64_t)(n - 1)) \| 1;` | `s`: the sum of the loaded values. `start`: a random place in the list. `step`: a random odd number below `n`. It is the distance in the list between two lines that are loaded one after the other. |
| 672 | `    for (;;) { /* step must be coprime with n to visit every line once (reviewer's catch, 2026-11-02) */` | Starts a loop that changes `step` until `step` and `n` have no common divisor above 1. The comment gives the reason: only then does the walk visit every line once. By the comment a reviewer found this on 2026-11-02. |
| 673 | `        uint64_t a = (uint64_t)n, b = step % (uint64_t)n;` | `a`, `b`: the two numbers for the algorithm of Euclid: `n`, and `step` modulo `n`. |
| 674 | `        while (b) { uint64_t r = a % b; a = b; b = r; }` | The algorithm of Euclid. When its loop ends, `a` is the greatest common divisor of `n` and `step`. |
| 675 | `        if (a == 1)` | Tests whether the greatest common divisor is 1. |
| 676 | `            break;` | Then `step` can be used, and the loop of line 672 ends. |
| 677 | `        step = (step + 2) % (uint64_t)n;` | If not: adds 2 to `step`, modulo `n`. |
| 678 | `        if (step < 2)` | Tests whether `step` became 0 or 1. |
| 679 | `            step = 3;` | Then sets it to 3. |
| 680 | `    }` | Ends the loop of line 672. |
| 681 | `    for (int i = 0; i < n; i++)` | Loop: `n` loads. |
| 682 | `        s += *(const uint64_t *)(buf + (uint64_t)lines[(start + (uint64_t)i * step) % (uint64_t)n] * LINE);` | Loads the first 8 bytes of the line at the list place `(start + i * step) % n` and adds the value to `s`. The places run through the whole list once, in jumps of `step`. The address of a load does not depend on the value of another load. |
| 683 | `    sink = (void *)(uintptr_t)s;` | Stores the sum into `sink`. So the loads have a result that is used. |
| 684 | `}` | Ends the function `fill_random`. |

### Counters of the cache-state check: variables, `group_values` and `cstate_read` (lines 686 to 734)

| Line | Source | Explanation |
|---:|---|---|
| 686 | `/* Fresh-chain latency over the given lines. Chains 0..reps-1 (one 8-byte slot of each line per` | Comment: this comment describes the function `measure`, which starts 50 source lines below (line 736). The latency is measured over the given lines with chains that were never walked, which the comment calls fresh. The chains 0 to `reps - 1` each use one 8-byte word of each line. |
| 687 | ` * chain) are each timed exactly once: fill the set with random independent loads, evict L1/L2,` | Comment: each chain is timed exactly once. One repeat has three steps: load the set with random independent loads, push it out of L1 and L2, and then the step of line 688. |
| 688 | ` * time one pass of chain r. Returns median, min and max in ns per load. reps is at most 8. */` | Comment: time one pass of chain `r`. The function gives back the median, the minimum and the maximum in ns per load. `reps` is at most 8. A 64-byte line has 8 words of 8 bytes. |
| 689 | `#define NCSTATE 5` | `NCSTATE`: 5, the number of counters that the cache-state check can have open at the same time. |
| 690 | `static int cstate_fds[NCSTATE] = { -1, -1, -1, -1, -1 }; /* --verify-slices counters, see verify_slices() */` | `cstate_fds`: the file descriptors of these counters. All are -1 at the start: no counter is open. By the comment they belong to the option `--verify-slices` and the function `verify_slices`. |
| 691 | `static uint64_t cstate_delta[NCSTATE];` | `cstate_delta`: for each counter, the sum of its rises over the timed passes (line 754). |
| 692 | `static int cstate_multiplexed;` | `cstate_multiplexed`: becomes 1 when a group of these counters did not count the whole time (lines 710 to 711). |
| 693 | `static int verify_lenient; /* --verify-lenient: a failed cache-state check is recorded (valid=0 in verify.csv) and the run continues; off in run_sudo.sh */` | `verify_lenient`: 1 with the option `--verify-lenient`. By the comment a failed cache-state check is then only recorded (`valid=0` in `verify.csv`) and the run goes on. The comment says that the option is off in `run_sudo.sh`. That script does not pass it. |
| 695 | `/* Reads a group through its leader and returns its n values in open order. A read through a member` | Comment: the function reads a group through its leader and gives back its `n` values in the order in which the counters were opened. The next sentence starts here. |
| 696 | ` * descriptor also returns the whole group with the leader first, which is why an earlier version` | Comment: a read through a member (a counter that is not the leader) also returns the whole group, with the leader first. By the comment that is the reason for an error of an earlier version, which line 697 names. |
| 697 | ` * reported the leader's count under the member's name (reviewer's catch, 2026-11-02). */` | Comment: the earlier version reported the count of the leader under the name of the member. By the comment a reviewer found this on 2026-11-02. |
| 698 | `static void group_values(int leader_fd, int n, uint64_t *out)` | Starts the function `group_values`. It reads the `n` counters of a group through the file descriptor `leader_fd` and writes their counts to `out`. |
| 699 | `{` | Opens the body of `group_values`. |
| 700 | `    uint64_t r[3 + DTC_LIMIT];` | `r`: room for the answer of Linux: 3 numbers at the start and up to 8 counts. |
| 701 | `    ssize_t want = (ssize_t)((3 + (size_t)n) * sizeof(uint64_t)), got = read(leader_fd, r, sizeof r);` | `want`: the number of bytes that the answer must have: 3 plus `n` numbers of 8 bytes each. `got`: the number of bytes that `read` returned. |
| 702 | `    if (got != want) {` | Tests whether the two differ. |
| 703 | `        fprintf(stderr, "homelat: cache-state group read returned %zd bytes, expected %zd for %d counters\n", got, want, n);` | Then prints an error message with both byte counts and the number of counters. |
| 704 | `        exit(2);` | Then the program ends with exit status 2. |
| 705 | `    }` | Ends the `if` of line 702. |
| 706 | `    if ((int)r[0] != n) {` | Tests whether the first number of the answer, the number of counters, differs from `n`. |
| 707 | `        fprintf(stderr, "homelat: group read returned %d counters, expected %d\n", (int)r[0], n);` | Then prints both numbers to the error output. |
| 708 | `        exit(2);` | Then the program ends with exit status 2. |
| 709 | `    }` | Ends the `if` of line 706. |
| 710 | `    if (r[1] != r[2])` | Tests whether the time enabled (`r[1]`) differs from the time running (`r[2]`). |
| 711 | `        cstate_multiplexed = 1;` | Then notes that a group was multiplexed. The cache-state check then fails for this slice (line 879). |
| 712 | `    for (int i = 0; i < n; i++)` | Loop over the `n` counters. |
| 713 | `        out[i] = r[3 + i];` | Copies each count to the caller. |
| 714 | `}` | Ends the function `group_values`. |
| 716 | `/* cstate counters are organised as groups: cstate_group[j] is the leader index for value j */` | Comment: the counters of the cache-state check are organised as groups. The comment names an array `cstate_group`. The code calls it `cstate_leader`: `cstate_leader[j]` is the index of the leader of counter `j`. |
| 717 | `static int cstate_leader[NCSTATE] = { -1, -1, -1, -1, -1 }, cstate_pos[NCSTATE];` | `cstate_leader`: for each counter, the index of the leader of its group, -1 at the start. A leader holds its own index. `cstate_pos`: for each counter, its place in the answer of its group, counted from 0. |
| 719 | `static void cstate_read(uint64_t *vals)` | Starts the function `cstate_read`. It reads all open counters of the cache-state check and writes the 5 counts to `vals`. It makes one `read` call per group. |
| 720 | `{` | Opens the body of `cstate_read`. |
| 721 | `    for (int j = 0; j < NCSTATE; j++) {` | Loop over the 5 counters. |
| 722 | `        if (cstate_fds[j] < 0) { vals[j] = 0; continue; }` | A counter that is not open gets the value 0, and the loop goes on. |
| 723 | `        if (cstate_leader[j] != j)` | Tests whether counter `j` is a member of a group and not its leader. |
| 724 | `            continue; /* a member: filled when its leader is read */` | Then goes on. By the comment a member gets its value when its leader is read. |
| 725 | `        uint64_t v[DTC_LIMIT];` | `v`: room for the counts of one group. |
| 726 | `        int n = 0;` | `n`: the number of counters in the group of leader `j`. |
| 727 | `        for (int k = j; k < NCSTATE; k++) n += cstate_fds[k] >= 0 && cstate_leader[k] == j;` | Counts the open counters whose leader is `j`. The leader counts itself. |
| 728 | `        group_values(cstate_fds[j], n, v);` | Reads the group through the leader (`group_values`). |
| 729 | `        for (int k = j; k < NCSTATE; k++)` | Loop over the counters from `j` on. |
| 730 | `            if (cstate_fds[k] >= 0 && cstate_leader[k] == j)` | Tests whether counter `k` is open and belongs to this group. |
| 731 | `                vals[k] = v[cstate_pos[k]];` | Then gives it its value from the answer, by its place `cstate_pos`. |
| 732 | `    }` | Ends the loop of line 721. |
| 733 | `}` | Ends the function `cstate_read`. |

### Function `measure`: time one pass over each chain of a set of lines (lines 735 to 762)

| Line | Source | Explanation |
|---:|---|---|
| 735 | `/* ns_all receives every repeat in run order (reviewer's request: keep each repeat). */` | Comment: `ns_all` receives the value of every repeat, in the order in which the repeats ran. By the comment a reviewer asked to keep each repeat. |
| 736 | `static void measure(uint8_t *buf, const uint8_t *ev, const uint32_t *lines, int n, int reps,` | Starts the function `measure`. It measures the latency of one set of lines from the CPU that the thread is pinned to at this moment. `buf`: the buffer. `ev`: the evictor buffer. `lines`: the indices of the `n` lines of the set. `reps`: the number of timed passes, at most 8. |
| 737 | `                    double *med, double *mn, double *mx, double *ns_all)` | Continues the parameter list: `med`, `mn` and `mx` receive the median, the minimum and the maximum in ns per load. `ns_all` receives the value of every repeat. |
| 738 | `{` | Opens the body of `measure`. |
| 739 | `    for (int s = 0; s < reps; s++)` | Loop over the chains: one chain per repeat. |
| 740 | `        build_chain(buf, lines, n, s);` | Builds chain `s` in word `s` of each line of the set (`build_chain`). All chains are built before the first load. Each chain goes through the same lines in another random order. |
| 741 | `    double ns[8];` | `ns`: the latency of each repeat, at most 8 values. |
| 742 | `    uint8_t *p0 = buf + (uint64_t)lines[0] * LINE;` | `p0`: the address of the first line of the list. Every timed pass starts at this line. |
| 743 | `    for (int r = 0; r < reps; r++) {` | Loop over the repeats. Each repeat times another chain, so no chain is walked twice. |
| 744 | `        fill_random(buf, lines, n);` | Step 1 of a repeat, not timed: loads every line of the set once (`fill_random`). |
| 745 | `        evict(ev);` | Step 2, not timed: reads the evictor buffer in a random order (`evict`). The header comment says what this is for: the lines of the set are pushed out of L1 and L2 and stay in the slice of the SLC (lines 17 to 18). |
| 746 | `        uint64_t before[NCSTATE], after[NCSTATE];` | `before`, `after`: the counts of the cache-state counters before and after the timed pass. |
| 747 | `        if (cstate_fds[0] >= 0)` | Tests whether cache-state counters are open. They are open only inside `verify_slices`. |
| 748 | `            cstate_read(before);` | Then reads them (`cstate_read`). This read stands before the first clock read. |
| 749 | `        double t0 = now_s();` | Reads the clock: `t0`, the start of the timed interval. |
| 750 | `        sink = chase(p0 + 8 * r, n);` | The timed work: one pass over chain `r`. The pass starts at word `r` of the first line of the list and does `n` loads, one from each line of the set. The last pointer goes to `sink`. |
| 751 | `        double t1 = now_s();` | Reads the clock again: `t1`, the end of the timed interval. The interval holds the one call of `chase` and the store to `sink`, and nothing else. |
| 752 | `        if (cstate_fds[0] >= 0) {` | Tests again whether cache-state counters are open. |
| 753 | `            cstate_read(after);` | Then reads them again. This read stands after the second clock read. So the counter window is a little wider than the timed interval: it also holds the two clock reads. |
| 754 | `            for (int j = 0; j < NCSTATE; j++) cstate_delta[j] += after[j] - before[j];` | Then adds the rise of each counter to `cstate_delta`. |
| 755 | `        }` | Ends the `if` of line 752. |
| 756 | `        ns[r] = (t1 - t0) * 1e9 / (double)n;` | The latency of this repeat in nanoseconds per load: the elapsed time `t1 - t0` in seconds, times 1e9, divided by the `n` loads. |
| 757 | `        ns_all[r] = ns[r];` | Keeps the value in the order of the runs, for the caller. |
| 758 | `    }` | Ends the loop of line 743. |
| 759 | `    qsort(ns, (size_t)reps, sizeof ns[0], cmp_double);` | Sorts the values of the repeats in rising order (`qsort` with `cmp_double`). |
| 760 | `    *mn = ns[0]; *mx = ns[reps - 1]; *med = ns[reps / 2];` | Gives back the minimum (the first value), the maximum (the last value) and the median (the value at the place `reps / 2`, counted from 0). With 7 repeats the median is the fourth value. With an even number of repeats it is the upper one of the two middle values. |
| 761 | `}` | Ends the function `measure`. |

### Functions `open_counter`, `cstate_open_group` and `cstate_close` (lines 763 to 798)

| Line | Source | Explanation |
|---:|---|---|
| 763 | `/* Cache-state check (reviewer's request): for a few real slices, half on each mesh, count during the` | Comment: the cache-state check, which a reviewer asked for. This comment describes the function `verify_slices` (line 820). For a few real slices, half of them on each mesh, the program counts during the ... The sentence goes on in line 764. |
| 764 | ` * timed chains only: SLC accesses summed over every node of mesh 0 and of mesh 1 (bynodeid=0), the` | Comment: ... timed chains only. It counts the accesses to the SLC summed over every node of mesh 0 and of mesh 1. `bynodeid=0` means that such a counter is not limited to one node. The list goes on in line 765. |
| 765 | ` * home node's own accesses and misses, and this core's L2 refills (raw event 0x17). Expected per timed` | Comment: it also counts the accesses and the misses of the home node itself, and the L2 refills of this core (the raw event `0x17`). An L2 refill is a line that is brought into L2 from outside. The next sentence starts here: expected per timed ... |
| 766 | ` * load: about one SLC access somewhere, no miss at the home, about one L2 refill. A line homed on the` | Comment: ... load are about one access to the SLC at some node, no miss at the home node, and about one L2 refill. The next sentence starts here: a line whose home is on the ... |
| 767 | ` * other mesh is served by the local proxy's cache partition (the LCC of a local HN-S, CMN S3 TRM page` | Comment: ... other mesh is served from a part of the cache of a local proxy. A proxy is a home node on the mesh of the core that handles the line in place of its home. The comment calls that cache part the LCC of a local HN-S, and it cites the manual of the mesh, the CMN S3 TRM. |
| 768 | ` * 1216), so for a remote slice the home itself may see no access while the local mesh's total shows one` | Comment: the citation ends with the page number 1216. So for a remote slice (a slice on the other mesh) the home node itself may see no access, while the sum of the local mesh shows one. |
| 769 | ` * (measured 2026-11-02: 0.00 to 0.04 accesses at four remote homes, 1.3 L2 refills, 11 to 29 ns). */` | Comment: the comment gives a measurement of 2026-11-02: 0.00 to 0.04 accesses per load at four remote home nodes, 1.3 L2 refills per load, and 11 to 29 ns per load. |
| 770 | `static int open_counter(uint32_t type, uint64_t config, int cpu, int pid, int group_fd)` | Starts the function `open_counter`. It opens one counter and returns its file descriptor, or -1 on failure. `type` is the PMU and `config` the event. `cpu` and `pid` say on which CPU and for which process to count. `group_fd` is the leader of the group, or -1. |
| 771 | `{` | Opens the body of `open_counter`. |
| 772 | `    struct perf_event_attr a;` | `a`: the description of the counter. |
| 773 | `    memset(&a, 0, sizeof a);` | Sets every field of the description to 0. |
| 774 | `    a.type = type; a.size = sizeof a; a.config = config;` | Sets the PMU, the size of the description and the event. |
| 775 | `    a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | The same `read_format` as in line 232: a read of a leader returns all counts of its group and the two times. |
| 776 | `    return (int)syscall(SYS_perf_event_open, &a, pid, cpu, group_fd, 0);` | Makes the system call `perf_event_open` with these values and no flags. |
| 777 | `}` | Ends the function `open_counter`. |
| 779 | `static void cstate_open_group(int j, uint32_t type, uint64_t config, int cpu, int pid, int leader)` | Starts the function `cstate_open_group`. It opens counter number `j` of the cache-state check. `leader` is -1 when the counter starts a new group. In the other case it is the number of the counter that leads the group. |
| 780 | `{` | Opens the body of `cstate_open_group`. |
| 781 | `    cstate_leader[j] = leader < 0 ? j : leader;` | Notes the leader of counter `j`: itself for a new group, or `leader`. |
| 782 | `    cstate_pos[j] = 0;` | The place of the counter in the answer of its group starts at 0. |
| 783 | `    if (leader >= 0)` | Tests whether the counter joins an existing group. |
| 784 | `        for (int k = leader; k < j; k++) cstate_pos[j] += cstate_leader[k] == leader;` | Then its place is the number of counters from `leader` to `j - 1` that belong to that group. The leader itself has the place 0. |
| 785 | `    cstate_fds[j] = open_counter(type, config, cpu, pid, leader < 0 ? -1 : cstate_fds[leader]);` | Opens the counter (`open_counter`). A new group gets -1 as the group argument. A member gets the file descriptor of its leader. |
| 786 | `    if (cstate_fds[j] < 0)` | Tests whether the counter did not open. |
| 787 | `        die("perf_event_open for the cache-state check");` | Then `die` prints `homelat: perf_event_open for the cache-state check:` with the reason and ends the program with exit status 2. |
| 788 | `}` | Ends the function `cstate_open_group`. |
| 790 | `static void cstate_close(void)` | Starts the function `cstate_close`. It closes all counters of the cache-state check. |
| 791 | `{` | Opens the body of `cstate_close`. |
| 792 | `    for (int j = 0; j < NCSTATE; j++) {` | Loop over the 5 counters. |
| 793 | `        if (cstate_fds[j] >= 0) close(cstate_fds[j]);` | Closes the counter when it is open. |
| 794 | `        cstate_fds[j] = -1;` | Marks it as not open. |
| 795 | `        cstate_leader[j] = -1; /* a stale leader entry made the next pass count a closed member (2026-11-02) */` | Clears its leader entry. By the comment, an old leader entry made the next pass count a closed member (2026-11-02). |
| 796 | `    }` | Ends the loop of line 792. |
| 797 | `}` | Ends the function `cstate_close`. |

### Function `cstate_baseline`: what the counters count in a window without a chase (lines 799 to 819)

| Line | Source | Explanation |
|---:|---|---|
| 799 | `/* An empty counter window with the same cache state as the timed one: fill the set and read the` | Comment: the function measures an empty counter window with the same cache state as the timed one. It loads the set and reads the evictor, which line 800 continues. |
| 800 | ` * evictor exactly as measure() does, then take the two counter snapshots and the two clock reads` | Comment: it does both exactly as `measure` does. Then it takes the two counter snapshots and the two clock reads ... |
| 801 | ` * with no chase between them, reps times. What the window counts is the overhead of the reads` | Comment: ... with no chase between them. It does this `reps` times. The next sentence starts here: what the window counts is the cost of the reads ... |
| 802 | ` * themselves under the post-eviction cache state (reviewer's request, 2026-11-02). */` | Comment: ... themselves, in the cache state after the eviction. By the comment a reviewer asked for this on 2026-11-02. |
| 803 | `static void cstate_baseline(uint8_t *buf, const uint8_t *ev, const uint32_t *lines, int n, int reps, uint64_t *base)` | Starts the function `cstate_baseline`. `base` receives, for each counter, the sum of its rises over `reps` empty windows. The caller subtracts these sums from the counts of the timed windows (lines 854 to 855). The other parameters are those of `measure`. |
| 804 | `{` | Opens the body of `cstate_baseline`. |
| 805 | `    uint64_t b[NCSTATE], a[NCSTATE];` | `b`, `a`: the counts before and after one empty window. |
| 806 | `    memset(base, 0, NCSTATE * sizeof *base);` | Sets the 5 sums to 0. |
| 807 | `    for (int r = 0; r < reps; r++) {` | Loop: `reps` empty windows. |
| 808 | `        fill_random(buf, lines, n);` | Loads every line of the set once (`fill_random`), as in line 744. |
| 809 | `        evict(ev);` | Reads the evictor buffer (`evict`), as in line 745. |
| 810 | `        cstate_read(b);` | The first snapshot of the counters (`cstate_read`). |
| 811 | `        double t0 = now_s();` | The first clock read. |
| 812 | `        sink = (void *)(uintptr_t)t0;` | Stores the time into `sink`. This statement stands where `measure` has the chase. |
| 813 | `        double t1 = now_s();` | The second clock read. |
| 814 | `        sink = (void *)(uintptr_t)t1;` | Stores it into `sink` too. |
| 815 | `        cstate_read(a);` | The second snapshot of the counters. |
| 816 | `        for (int j = 0; j < NCSTATE; j++) base[j] += a[j] - b[j];` | Adds the rise of each counter to its sum. |
| 817 | `    }` | Ends the loop of line 807. |
| 818 | `}` | Ends the function `cstate_baseline`. |

### Function `verify_slices`: the output file, the choice of a slice, and pass A (lines 820 to 857)

| Line | Source | Explanation |
|---:|---|---|
| 820 | `static void verify_slices(uint8_t *buf, const uint8_t *ev, int core, int count, int lines_per_node, int reps, const char *out)` | Starts the function `verify_slices`, the cache-state check. It measures `count` slices from the CPU `core` with counters open, writes one row per slice to the file `verify.csv`, and tests each slice against fixed limits. `lines_per_node` and `reps` are the values of the main measurement. `out` is the output folder. |
| 821 | `{` | Opens the body of `verify_slices`. |
| 822 | `    char path[512];` | `path`: room for the file name. |
| 823 | `    snprintf(path, sizeof path, "%s/verify.csv", out);` | Builds the file name: `verify.csv` in the output folder. |
| 824 | `    FILE *f = fopen(path, "w");` | Opens the file for writing. An old file of that name is emptied. |
| 825 | `    if (!f)` | Tests whether the file could not be opened. |
| 826 | `        die("verify.csv");` | Then `die` prints `homelat: verify.csv:` with the reason and ends the program with exit status 2. |
| 827 | `    fprintf(f, "core,mesh,node_id_hex,x,y,dev,lines,timed_loads,home_acc,home_miss,l2_refills_a,ns_median_a,"` | Writes the first half of the header row: the core, the mesh, the node id, `x`, `y`, the device, the number of lines, the number of timed loads, and the values of pass A: accesses and misses at the home node, L2 refills, and the median latency in ns. |
| 828 | `               "acc_mesh0,miss_mesh0,acc_mesh1,miss_mesh1,l2_refills_b,ns_median_b,baseline_slc_accesses_per_window,baseline_l2_refills_per_window,multiplexed,valid\n");` | The second half of the header row: the values of pass B (accesses and misses of mesh 0 and of mesh 1, L2 refills, median latency), the two baseline values per window, the flag `multiplexed` and the flag `valid`. |
| 829 | `    uint64_t acc_cfg[NMESH], miss_cfg[NMESH];` | `acc_cfg`, `miss_cfg`: for each mesh, the configuration words of the access event and of the miss event. |
| 830 | `    for (int m = 0; m < NMESH; m++) {` | Loop over the two meshes. |
| 831 | `        acc_cfg[m] = event_config(m, "hns_slc_sf_cache_access_all");` | The access event `hns_slc_sf_cache_access_all` (`event_config` reads its description). The comment of line 764 calls its counts SLC accesses. |
| 832 | `        miss_cfg[m] = event_config(m, "hns_cache_miss_all");` | The miss event `hns_cache_miss_all`. |
| 833 | `    }` | Ends the loop of line 830. |
| 834 | `    pin_cpu(core);` | Pins the thread to `core`. The caller passes the first core of the core list (line 1105). The whole check runs on this CPU. |
| 835 | `    int bad = 0;` | `bad`: the number of slices that fail the check. |
| 836 | `    for (int s = 0; s < count; s++) {` | Loop over the `count` slices. |
| 837 | `        int k = (int)(((uint64_t)s * (uint64_t)nnodes + xorshift64() % (uint64_t)(nnodes / count)) / (uint64_t)count) % nnodes;` | `k`: the index of the node to check. The expression adds a random number below `nnodes / count` to `s * nnodes` and divides the sum by `count`. With 128 nodes and 8 slices the result is 16 times `s`, or one more. So the checked nodes are spread evenly over the node table: 4 on mesh 0 and 4 on mesh 1. |
| 838 | `        struct node *n = &nodes[k];` | `n`: the table entry of that node. |
| 839 | `        int cn = n->nlines < lines_per_node ? n->nlines & ~7 : lines_per_node;` | `cn`: the number of lines of the set. It is `lines_per_node`. For a node with fewer lines it is the number of its lines, rounded down to a multiple of 8. |
| 840 | `        if (cn < 64)` | Tests whether the set has fewer than 64 lines. |
| 841 | `            continue;` | Then skips the slice. It gets no row in `verify.csv` and does not count as failed. |
| 842 | `        uint64_t nid = (1ULL << 31) \| ((uint64_t)n->id << 32);` | `nid`: the two node fields of a configuration word: bit 31 (`bynodeid`) and the node id in the bits 32 to 47. A counter with these bits counts at this home node only. |
| 843 | `        double loads = (double)cn * (double)reps, med_a, med_b, mn, mx, all[8];` | `loads`: the number of timed loads of one pass: the lines of the set times the repeats. With 2048 lines and 7 repeats that is 14336. The other variables of the line receive latency values. |
| 844 | `        uint64_t base_a[NCSTATE], base_b[NCSTATE];` | `base_a`, `base_b`: the sums of the empty windows of pass A and of pass B. |
| 845 | `        int mux = 0;` | `mux`: becomes 1 when a counter group was multiplexed in pass A or in pass B. |
| 846 | `        /* pass A: the home node's own accesses and misses, and this core's L2 refills */` | Comment: pass A counts the accesses and the misses of the home node itself, and the L2 refills of this core. |
| 847 | `        cstate_multiplexed = 0;` | Clears the flag before pass A. |
| 848 | `        cstate_open_group(0, (uint32_t)pmu_type[n->mesh], acc_cfg[n->mesh] \| nid, pmu_cpu[n->mesh], -1, -1);` | Counter 0: the access event at the home node only (`\| nid`). It is opened on the CPU of the PMU of that mesh, for all processes (`-1`), and it starts a new group. |
| 849 | `        cstate_open_group(1, (uint32_t)pmu_type[n->mesh], miss_cfg[n->mesh] \| nid, pmu_cpu[n->mesh], -1, 0);` | Counter 1: the miss event at the home node only. It joins the group of counter 0. |
| 850 | `        cstate_open_group(2, PERF_TYPE_RAW, 0x17, -1, 0, -1);` | Counter 2: the raw event `0x17` of the core (`PERF_TYPE_RAW`), which the comment of line 765 calls the L2 refills of this core. With the CPU -1 and the process 0 it counts for the calling thread on any CPU [Ref4]. It is a group of its own. |
| 851 | `        cstate_baseline(buf, ev, n->lines, cn, reps, base_a);` | Measures the empty windows of pass A (`cstate_baseline`). |
| 852 | `        memset(cstate_delta, 0, sizeof cstate_delta);` | Sets the sums of the timed windows to 0. |
| 853 | `        measure(buf, ev, n->lines, cn, reps, &med_a, &mn, &mx, all);` | Runs the measurement with the counters open (`measure`): `reps` timed passes over the first `cn` lines of the list of this node. `med_a` receives the median latency. |
| 854 | `        double ha = ((double)cstate_delta[0] - (double)base_a[0]) / loads, hm = ((double)cstate_delta[1] - (double)base_a[1]) / loads,` | `ha`: the accesses at the home node per timed load. It is the sum of the timed windows minus the sum of the empty windows, divided by the timed loads. `hm`: the same for the misses at the home node. |
| 855 | `               rfa = ((double)cstate_delta[2] - (double)base_a[2]) / loads;` | Continues the statement of line 854. `rfa`: the same for the L2 refills of pass A. |
| 856 | `        mux \|= cstate_multiplexed;` | Keeps a multiplex flag of pass A. |
| 857 | `        cstate_close();` | Closes the counters of pass A. |

### Function `verify_slices`: pass B, the test of the slice and its row (lines 858 to 899)

| Line | Source | Explanation |
|---:|---|---|
| 858 | `        /* pass B: accesses and misses summed over every home node of each mesh (two groups), and L2 refills.` | Comment: pass B counts accesses and misses summed over every home node of each mesh, in two groups, and again the L2 refills. |
| 859 | `         * Four events per crosspoint is the DTM limit, so the home's own counters cannot join this pass. */` | Comment: by the comment a crosspoint can count four events at the same time, which it calls the DTM limit. So the counters of the home node itself cannot be open in this pass. |
| 860 | `        cstate_multiplexed = 0;` | Clears the flag before pass B. |
| 861 | `        cstate_open_group(0, (uint32_t)pmu_type[0], acc_cfg[0], pmu_cpu[0], -1, -1);` | Counter 0: the access event of mesh 0 without a node id. It counts the sum over all home nodes of mesh 0. It starts a group. |
| 862 | `        cstate_open_group(1, (uint32_t)pmu_type[0], miss_cfg[0], pmu_cpu[0], -1, 0);` | Counter 1: the miss event of mesh 0, summed over all its home nodes. It joins the group of counter 0. |
| 863 | `        cstate_open_group(2, (uint32_t)pmu_type[1], acc_cfg[1], pmu_cpu[1], -1, -1);` | Counter 2: the access event of mesh 1, summed over all its home nodes. It starts a second group. |
| 864 | `        cstate_open_group(3, (uint32_t)pmu_type[1], miss_cfg[1], pmu_cpu[1], -1, 2);` | Counter 3: the miss event of mesh 1. It joins the group of counter 2. |
| 865 | `        cstate_open_group(4, PERF_TYPE_RAW, 0x17, -1, 0, -1);` | Counter 4: the raw event `0x17` for the calling thread, as in line 850. |
| 866 | `        cstate_baseline(buf, ev, n->lines, cn, reps, base_b);` | Measures the empty windows of pass B (`cstate_baseline`). |
| 867 | `        memset(cstate_delta, 0, sizeof cstate_delta);` | Sets the sums of the timed windows to 0. |
| 868 | `        measure(buf, ev, n->lines, cn, reps, &med_b, &mn, &mx, all);` | Runs the measurement again (`measure`). It builds new chains over the same lines. `med_b` receives the median latency of pass B. |
| 869 | `        double a0 = ((double)cstate_delta[0] - (double)base_b[0]) / loads, m0 = ((double)cstate_delta[1] - (double)base_b[1]) / loads,` | `a0`, `m0`: the accesses and the misses of mesh 0 per timed load. Each is the sum of the timed windows minus the sum of the empty windows, divided by the timed loads. |
| 870 | `               a1 = ((double)cstate_delta[2] - (double)base_b[2]) / loads, m1 = ((double)cstate_delta[3] - (double)base_b[3]) / loads,` | Continues the statement of line 869. `a1`, `m1`: the same for mesh 1. |
| 871 | `               rfb = ((double)cstate_delta[4] - (double)base_b[4]) / loads;` | Continues the statement. `rfb`: the L2 refills per timed load in pass B. |
| 872 | `        mux \|= cstate_multiplexed;` | Keeps a multiplex flag of pass B. |
| 873 | `        cstate_close();` | Closes the counters of pass B. |
| 874 | `        /* The decisive test for a local slice is its home's own counters: about 1 access and under 0.1 misses` | Comment: the test that decides for a local slice uses the counters of its home node: about 1 access and fewer than 0.1 misses per timed load. The comment adds a measurement, which line 875 starts. |
| 875 | `         * per timed load (measured 0.000 to 0.027 misses in every run). Whole-mesh misses (0.03 to 0.35 per load` | Comment: by the comment every run measured 0.000 to 0.027 misses per load there. The misses of the whole meshes were 0.03 to 0.35 per load, summed over both meshes, on 2026-11-02. |
| 876 | `         * summed over both meshes, 2026-11-02) are recorded with no attribution. */` | Comment: these misses of the whole meshes are recorded, and no cause is assigned to them. |
| 877 | `        int local = n->mesh == 0; /* the probing core (CPU 0 or 3) is on arm_cmn_0 */` | `local`: 1 when the node is on mesh 0. By the comment the checking core (CPU 0 or 3) is on `arm_cmn_0`. So the code takes mesh 0 as the local mesh. That fits only when the first core of the core list is a CPU of mesh 0. |
| 878 | `        int ok = 1;` | `ok`: 1 as long as the slice passes. |
| 879 | `        if (rfa < 0.8 \|\| rfb < 0.8 \|\| med_a < 8.0 \|\| med_a > 100.0 \|\| a0 + a1 < 0.8 \|\| mux \|\|` | The test of the slice. It fails in each of these cases: fewer than 0.8 L2 refills per timed load in pass A or in pass B, a median latency of pass A below 8.0 ns or above 100.0 ns, fewer than 0.8 SLC accesses per load on both meshes together, or a multiplexed counter group. |
| 880 | `            (local && (ha < 0.8 \|\| hm > 0.1)))` | Continues the test, for a local slice only: it also fails with fewer than 0.8 accesses or more than 0.1 misses per load at the home node. The misses of the whole meshes (`m0`, `m1`) and the latency of pass B are not tested. |
| 881 | `        { ok = 0; bad++; }` | On a failure: `ok` becomes 0, and `bad` counts the slice. |
| 882 | `        double base_acc = ((double)base_b[0] + (double)base_b[2]) / (double)reps, base_rf = (double)base_b[4] / (double)reps;` | `base_acc`: the SLC accesses of one empty window of pass B, both meshes together. It is the two sums divided by `reps`. `base_rf`: the L2 refills of one empty window of pass B. |
| 883 | `        fprintf(f, "%d,%d,0x%x,%d,%d,%d,%d,%.0f,%.3f,%.3f,%.3f,%.2f,%.3f,%.3f,%.3f,%.3f,%.3f,%.2f,%.1f,%.1f,%d,%d\n", core, n->mesh, n->id, n->x, n->y, n->dev, cn, loads,` | Writes the row of the slice to `verify.csv`: 22 values in the order of the header (lines 827 to 828). The line holds the first 8: the core, the mesh, the node id, `x`, `y`, the device, the lines and the timed loads. |
| 884 | `                ha, hm, rfa, med_a, a0, m0, a1, m1, rfb, med_b, base_acc, base_rf, mux, ok);` | Continues the call of line 883: the values from `ha` to `ok`. The last column, `valid`, is 1 when the slice passed and 0 when it failed. |
| 885 | `        fprintf(stderr, "cache state, mesh %d node 0x%x from core %d, per timed load: home acc %.2f miss %.3f, L2 refills %.2f, %.1f ns \| "` | Prints the values of the slice to the error output too. The first half of the text: the node, the core, the accesses, misses and L2 refills at the home node, and the latency of pass A. |
| 886 | `                        "mesh0 acc %.2f miss %.3f, mesh1 acc %.2f miss %.3f, L2 refills %.2f, %.1f ns%s\n",` | The second half of the text: the accesses and misses of both meshes, the L2 refills and the latency of pass B. |
| 887 | `                n->mesh, n->id, core, ha, hm, rfa, med_a, a0, m0, a1, m1, rfb, med_b, mux ? " (multiplexed!)" : "");` | Continues the call: the values. The text `(multiplexed!)` is added when a group was multiplexed. |
| 888 | `        /* Acceptance: the loads must miss L2 (refills about 1), reach the mesh (accesses on the two meshes` | Comment: the rules of acceptance. The loads must miss L2 (about 1 refill per load). They must reach the mesh (about 1 access or more on the two meshes together). |
| 889 | `         * about 1 or more), hit in the serving cache (misses on the two meshes under 0.1 per load), and take` | Comment: they must hit in the cache that serves them. The comment gives the limit as fewer than 0.1 misses per load on the two meshes. The code has no test of the misses of the whole meshes (lines 879 to 880). The loads must also take ... |
| 890 | `         * mesh latency (8 to 100 ns). For a local slice the home itself must see about 1 access per load. */` | Comment: ... a latency of the mesh, 8 to 100 ns. For a local slice the home node itself must see about 1 access per load. |
| 891 | `        /* Measured 2026-11-02 04:33 UTC on CRB: local slices show 1.06 to 1.08 accesses and 0.005 to 0.030 misses` | Comment: a measurement of 2026-11-02 04:33 UTC on CRB, by the comment: local slices showed 1.06 to 1.08 accesses and 0.005 to 0.030 misses ... |
| 892 | `         * per load at the home; the whole-mesh totals add 0.6 to 0.8 accesses and 0.05 to 0.14 misses per load from` | Comment: ... per load at the home node. The sums of the whole meshes added 0.6 to 0.8 accesses and 0.05 to 0.14 misses per load. By the comment these come from ... |
| 893 | `         * the other traffic a load triggers, so the whole-mesh miss limit is 0.2 and the decisive test for a local` | Comment: ... the other traffic that a load causes. The comment concludes that the miss limit of the whole meshes is 0.2. The code has no such limit. The comment goes on: the test that decides for a local ... |
| 894 | `         * slice is the home's own miss rate. */` | Comment: ... slice is the miss rate of the home node itself. |
| 895 | `        /* A local slice (the probing core's own mesh) must serve its loads itself: about 1 access and under 0.1` | Comment: a local slice is a slice on the mesh of the checking core. It must serve its loads itself: about 1 access and fewer than 0.1 ... |
| 896 | `         * misses at the home. A remote slice is served elsewhere and its home sees about 0 accesses; the remote` | Comment: ... misses at the home node. A remote slice is served at another place, and its home node sees about 0 accesses. The remote ... |
| 897 | `         * rows are "latency by home group" and carry no slice-distance claim. Whole-mesh accesses and misses` | Comment: ... rows are named latency by home group. By the comment they make no claim about the distance to a slice. The accesses and misses of the whole meshes ... |
| 898 | `         * (pass B) exceed the timed loads by amounts that are recorded but not attributed (reviewer, 2026-11-02). */` | Comment: ... (pass B) are higher than the number of timed loads. The amounts are recorded, and no cause is assigned to them (a reviewer, 2026-11-02). |

### Function `verify_slices`: the marker check and the verdict (lines 900 to 913)

| Line | Source | Explanation |
|---:|---|---|
| 900 | `        check_marker();` | Looks for the marker file once per slice (`check_marker`). |
| 901 | `    }` | Ends the loop of line 836. |
| 902 | `    fclose(f);` | Closes `verify.csv`. |
| 903 | `    if (bad) {` | Tests whether a slice failed. |
| 904 | `        fprintf(stderr, "homelat: cache-state check failed for %d of %d slices (per timed load: about 1 L2 refill, about 1 mesh access, "` | Then prints an error message: the number of failed slices and `count`, and the rules per timed load: about 1 L2 refill, about 1 mesh access. The text goes on in line 905. |
| 905 | `                        "8 to 100 ns, no multiplexing, and for a local slice about 1 access and under 0.1 misses at the home)%s\n",` | The rest of the rules in the message: 8 to 100 ns, no multiplexing, and for a local slice about 1 access and fewer than 0.1 misses at the home node. |
| 906 | `                bad, count, verify_lenient ? "; --verify-lenient: recorded, continuing" : "");` | Continues the call: the values. With `--verify-lenient` the text `; --verify-lenient: recorded, continuing` is added. |
| 907 | `        if (!verify_lenient)` | Tests whether `--verify-lenient` is off. |
| 908 | `            exit(2);` | Then the program ends with exit status 2. So without that option a failed slice stops the run before the latency measurement of lines 1111 to 1134. |
| 909 | `        return;` | With `--verify-lenient` the function returns, and the run goes on. |
| 910 | `    }` | Ends the `if` of line 903. |
| 911 | `    fprintf(stderr, "cache-state check passed for %d slices\n", count);` | Prints `cache-state check passed for` and `count` to the error output. `count` is the number of slices that were asked for. A slice that lines 840 to 841 skipped is inside this number too. |
| 912 | `}` | Ends the function `verify_slices`. |

### Function `usage`: print the usage text and stop (lines 914 to 924)

| Line | Source | Explanation |
|---:|---|---|
| 914 | `static void usage(void)` | Starts the function `usage`. It prints the usage text to the error output and ends the program with exit status 2. |
| 915 | `{` | Opens the body of `usage`. |
| 916 | `    fprintf(stderr,` | Starts the `fprintf` call to the error output. Lines 917 to 921 are one text. |
| 917 | `            "usage: homelat [--bytes B] [--cores LIST] [--lines-per-node N] [--reps R] [--retries K]\n"` | Usage text: the options `--bytes`, `--cores`, `--lines-per-node`, `--reps` and `--retries`. |
| 918 | `            "               [--event NAME] [--out DIR] [--no-perf] [--evict-bytes B] [--evict-fixed] [--probe-loads K]\n"` | Usage text: the options `--event`, `--out`, `--no-perf`, `--evict-bytes`, `--evict-fixed` and `--probe-loads`. |
| 919 | `            "               [--expect-nodes N] [--verify-sample N] [--verify-slices K] [--verify-lenient] [--marker PATH]\n"` | Usage text: the options `--expect-nodes`, `--verify-sample`, `--verify-slices`, `--verify-lenient` and `--marker`. |
| 920 | `            "  defaults: 16M, cores 0-119, 2048 lines per node, 7 reps, 3 retries, event hns_pocq_reqs_recvd_hbt,\n"` | Usage text: the defaults. A buffer of 16 MiB, the cores 0 to 119, 2048 lines per node, 7 repeats, 3 retries, and the event `hns_pocq_reqs_recvd_hbt`. |
| 921 | `            "            out ., 64 home nodes per mesh expected, 512 lines re-verified, 8 slices cache-state checked\n");` | Usage text: more defaults. The current folder as the output folder, 64 home nodes expected per mesh, 512 lines for the verification, and 8 slices for the cache-state check. The closing parenthesis ends the call. |
| 922 | `    exit(2);` | Ends the program with exit status 2. |
| 923 | `}` | Ends the function `usage`. |

### Function `main`: the defaults and the arguments (lines 925 to 962)

| Line | Source | Explanation |
|---:|---|---|
| 925 | `int main(int argc, char **argv)` | Starts `main`. `argc` and `argv` hold the arguments of the command line. |
| 926 | `{` | Opens the body of `main`. |
| 927 | `    uint64_t bytes = 16UL << 20;` | `bytes`: the size of the buffer, 16 MiB (16777216 bytes) by default. |
| 928 | `    int cores[MAX_CORES], ncores = 0, lines_per_node = 2048, reps = 7, retries = 3, use_perf = 1;` | `cores`: the core list, at most 1024 entries. `ncores`: its length, 0 until `--cores` is read. `lines_per_node`: the number of lines of one measured set, 2048 by default (128 KiB of lines). `reps`: 7 timed passes per set. `retries`: 3 extra probes for a line with an unclear result. `use_perf`: 1 means that the counters are used. |
| 929 | `    /* hbt = home-bound traffic. With the plain "read" filter a load of a line homed on the other` | Comment: `hbt` stands for home-bound traffic. Then the comment tells what happened with the plain filter `read`: a load of a line whose home is on the other ... |
| 930 | `     * mesh counted at two nodes: the local proxy (the LCN role of a local HN-S) and the true home` | Comment: ... mesh was counted at two nodes: at the local proxy, which the comment calls the LCN role of a local HN-S, and at the true home. |
| 931 | `     * (measured 2026-11-02: +255 at mesh 0 node 0x288 and +255 at mesh 1 node 0xa0 for one line` | Comment: the measurement of 2026-11-02 that showed it: a rise of 255 at node `0x288` of mesh 0 and a rise of 255 at node `0xa0` of mesh 1, for one line ... |
| 932 | `     * probed from CPU 0). The proxy's share is LCN-bound traffic, which hbt excludes. */` | Comment: ... that was probed from CPU 0. The share of the proxy is traffic bound for the LCN, and the filter `hbt` leaves it out. |
| 933 | `    const char *event = "hns_pocq_reqs_recvd_hbt", *out = ".";` | `event`: the name of the event that the classification counts, `hns_pocq_reqs_recvd_hbt` by default. The header comment calls its counts home-bound requests received (line 11). `out`: the output folder, the current folder by default. |
| 934 | `    int expect_nodes = 64, verify_sample = 512, verify_count = 8;` | `expect_nodes`: the number of home nodes that each mesh must have, 64. `verify_sample`: 512 random lines for the verification. `verify_count`: 8 slices for the cache-state check. |
| 935 | `    char default_cores[] = "0-119";` | `default_cores`: the core list that is used without `--cores`: the CPUs 0 to 119. |
| 936 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments. `argv[0]` is the program name, so the loop starts at 1. |
| 937 | `        const char *a = argv[i];` | `a`: the argument that is handled in this loop pass. |
| 938 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value needs it. |
| 939 | `        if (!strcmp(a, "--bytes") && more) bytes = parse_bytes(argv[++i]);` | `--bytes B`: the size of the buffer (`parse_bytes`). `++i` steps over the value. |
| 940 | `        else if (!strcmp(a, "--cores") && more) ncores = parse_list(argv[++i], cores, MAX_CORES);` | `--cores LIST`: the cores to measure from (`parse_list`). |
| 941 | `        else if (!strcmp(a, "--lines-per-node") && more) lines_per_node = atoi(argv[++i]);` | `--lines-per-node N`: the number of lines of one measured set. |
| 942 | `        else if (!strcmp(a, "--reps") && more) reps = atoi(argv[++i]);` | `--reps R`: the number of timed passes per set. |
| 943 | `        else if (!strcmp(a, "--retries") && more) retries = atoi(argv[++i]);` | `--retries K`: the number of extra probes for a line with an unclear result. |
| 944 | `        else if (!strcmp(a, "--event") && more) event = argv[++i];` | `--event NAME`: the event that the classification counts. |
| 945 | `        else if (!strcmp(a, "--out") && more) out = argv[++i];` | `--out DIR`: the output folder. The program does not create the folder. |
| 946 | `        else if (!strcmp(a, "--no-perf")) use_perf = 0;` | `--no-perf`: no counters. The lines get invented homes (line 1033). |
| 947 | `        else if (!strcmp(a, "--evict-bytes") && more) evict_bytes = parse_bytes(argv[++i]);` | `--evict-bytes B`: the size of the evictor buffer. |
| 948 | `        else if (!strcmp(a, "--evict-fixed")) evict_reshuffle = 0;` | `--evict-fixed`: one fixed order of the evictor loads in place of a new order per call (line 51). |
| 949 | `        else if (!strcmp(a, "--probe-loads") && more) probe_loads = atoi(argv[++i]);` | `--probe-loads K`: the number of loads of one probe. |
| 950 | `        else if (!strcmp(a, "--expect-nodes") && more) expect_nodes = atoi(argv[++i]);` | `--expect-nodes N`: the number of home nodes that each mesh must have. |
| 951 | `        else if (!strcmp(a, "--verify-sample") && more) verify_sample = atoi(argv[++i]);` | `--verify-sample N`: the number of random lines for the verification. |
| 952 | `        else if (!strcmp(a, "--verify-slices") && more) verify_count = atoi(argv[++i]);` | `--verify-slices K`: the number of slices for the cache-state check. 0 turns the check off (line 1104). |
| 953 | `        else if (!strcmp(a, "--marker") && more) marker_path = argv[++i];` | `--marker PATH`: another path for the marker file. |
| 954 | `        else if (!strcmp(a, "--verify-lenient")) verify_lenient = 1;` | `--verify-lenient`: a failed cache-state check does not stop the run (lines 907 to 909). |
| 955 | `        else usage();` | Every other argument, and also an option whose value is missing: prints the usage text and ends the program with exit status 2 (`usage`). |
| 956 | `    }` | Ends the loop of line 936. |
| 957 | `    if (!ncores)` | Tests whether no core list was given. |
| 958 | `        ncores = parse_list(default_cores, cores, MAX_CORES);` | Then reads the default list `0-119`. So the default uses the CPUs 0 to 119 only, the CPUs that our runs may use. |
| 959 | `    if (reps < 1 \|\| reps > 8 \|\| lines_per_node < 64 \|\| bytes % HUGE_BYTES \|\| probe_loads < 2)` | Tests the settings. Each of these is an error: `reps` below 1 or above 8, fewer than 64 lines per node, a buffer size that is not a multiple of 2 MiB, or fewer than 2 loads per probe. |
| 960 | `        usage();` | Then prints the usage text and ends the program. |
| 961 | `    lines_per_node &= ~7;` | Rounds `lines_per_node` down to a multiple of 8: the expression clears its lowest 3 bits. The loop of `chase` does 8 loads per pass. |

### Function `main`: the output files, the first pinning and the two buffers (lines 963 to 989)

| Line | Source | Explanation |
|---:|---|---|
| 963 | `    char path[512];` | `path`: room for a file name. |
| 964 | `    snprintf(path, sizeof path, "%s/nodes.csv", out);` | Builds the file name `nodes.csv` in the output folder. |
| 965 | `    FILE *fnodes = fopen(path, "w");` | Opens it for writing: `fnodes`. An old file of that name is emptied. |
| 966 | `    snprintf(path, sizeof path, "%s/chunks.csv", out);` | Builds the file name `chunks.csv` in the output folder. |
| 967 | `    FILE *fchunks = fopen(path, "w");` | Opens it for writing: `fchunks`. |
| 968 | `    snprintf(path, sizeof path, "%s/homes.csv", out);` | Builds the file name `homes.csv` in the output folder. |
| 969 | `    FILE *fhomes = fopen(path, "w");` | Opens it for writing: `fhomes`. |
| 970 | `    snprintf(path, sizeof path, "%s/latency.csv", out);` | Builds the file name `latency.csv` in the output folder. |
| 971 | `    FILE *flat = fopen(path, "w");` | Opens it for writing: `flat`. |
| 972 | `    if (!fnodes \|\| !fchunks \|\| !fhomes \|\| !flat)` | Tests whether one of the four files could not be opened. |
| 973 | `        die("cannot create output files in --out");` | Then `die` prints `homelat: cannot create output files in --out:` with the reason and ends the program with exit status 2. |
| 975 | `    pin_cpu(cores[0]);` | Pins the thread to the first core of the core list (`pin_cpu`). The two buffers are reserved and written for the first time on this CPU (lines 977 to 978). |
| 976 | `    uint64_t nlines = bytes / LINE;` | `nlines`: the number of 64-byte lines of the buffer. 16 MiB gives 262144 lines. |
| 977 | `    uint8_t *buf = alloc_buf(bytes);` | Reserves the main buffer and fills it with zeros (`alloc_buf`). |
| 978 | `    uint8_t *ev = alloc_buf(evict_bytes ? evict_bytes : HUGE_BYTES);` | Reserves the evictor buffer of `evict_bytes` bytes (8 MiB by default) and fills it with zeros. When `evict_bytes` is 0, the buffer gets 2 MiB. |
| 979 | `    evict_init();` | Makes the first random order of the evictor lines (`evict_init`). |
| 980 | `    long huge_kb = anon_huge_kb();` | `huge_kb`: the memory of the process that lies on transparent huge pages, in kB (`anon_huge_kb`). It is read after both buffers were written. |
| 981 | `    fprintf(stderr, "buffer %lu MiB, %lu lines, AnonHugePages %ld kB\n", (unsigned long)(bytes >> 20),` | Prints to the error output: the size of the main buffer in MiB, its number of lines, and `huge_kb`. |
| 982 | `            (unsigned long)nlines, huge_kb);` | Continues the call of line 981: the last two values. |
| 983 | `    if (huge_kb < (long)(bytes >> 10))` | Tests whether `huge_kb` is below the size of the main buffer in kB. `huge_kb` covers both buffers. So the test can pass when a part of the main buffer is not on 2 MiB pages. Lines 1052 to 1058 test each 2 MiB piece of the main buffer. |
| 984 | `        fprintf(stderr, "warning: not all of the buffer is on 2 MiB pages; physical bits 12-20 are then unknown\n");` | Then prints a warning: not all of the buffer is on 2 MiB pages, and the bits 12 to 20 of the physical addresses are then unknown. The program goes on. |
| 986 | `    int16_t *home = malloc(nlines * sizeof *home);` | `home`: one 16-bit entry per line of the buffer: the index of the home node of the line, or a negative value. |
| 987 | `    if (!home)` | Tests whether `malloc` failed. |
| 988 | `        die("malloc");` | Then `die` prints `homelat: malloc:` with the reason and ends the program with exit status 2. |

### Function `main`: find the home nodes, classify the lines and check the result (lines 990 to 1035)

| Line | Source | Explanation |
|---:|---|---|
| 990 | `    if (use_perf) {` | Tests whether the counters are used (no `--no-perf`). Lines 991 to 1031 run in that case. |
| 991 | `        for (int m = 0; m < NMESH; m++) {` | Loop over the two meshes. |
| 992 | `            snprintf(path, sizeof path, "/sys/bus/event_source/devices/arm_cmn_%d/type", m);` | Builds the file name `/sys/bus/event_source/devices/arm_cmn_N/type`, with the mesh number for `N`. |
| 993 | `            pmu_type[m] = read_sysfs_int(path);` | Reads the type number of the PMU from that file (`read_sysfs_int`). |
| 994 | `            snprintf(path, sizeof path, "/sys/bus/event_source/devices/arm_cmn_%d/cpumask", m);` | Builds the file name `/sys/bus/event_source/devices/arm_cmn_N/cpumask`. |
| 995 | `            pmu_cpu[m] = read_sysfs_int(path);` | Reads the first number of that file as the CPU of this PMU: the CPU on which the program opens the counters of this mesh. The log of the run of 2026-11-02 05:49 UTC shows CPU 0 for both meshes [Ref1]. |
| 996 | `            event_cfg[m] = event_config(m, event);` | Builds the configuration word of the classification event for this mesh (`event_config`). |
| 997 | `            fprintf(stderr, "arm_cmn_%d: perf type %d, cpu %d, %s config 0x%llx\n", m, pmu_type[m], pmu_cpu[m], event,` | Prints to the error output: the PMU, its type number, its CPU, the event name and the configuration word in hexadecimal. |
| 998 | `                    (unsigned long long)event_cfg[m]);` | Continues the call of line 997: the configuration word. |
| 999 | `            discover(m);` | Finds the home nodes of this mesh (`discover`). |
| 1000 | `        }` | Ends the loop of line 991. |
| 1001 | `        for (int m = 0; m < NMESH; m++) {` | Loop over the two meshes. |
| 1002 | `            int found = 0;` | `found`: the number of home nodes of this mesh. |
| 1003 | `            for (int k = 0; k < nnodes; k++)` | Loop over all nodes of the table. |
| 1004 | `                found += nodes[k].mesh == m;` | Counts the nodes of this mesh. |
| 1005 | `            if (found != expect_nodes) {` | Tests whether the count differs from `expect_nodes` (64 by default). |
| 1006 | `                fprintf(stderr, "homelat: mesh %d has %d home nodes, expected %d (--expect-nodes)\n", m, found, expect_nodes);` | Then prints the mesh, the count and the expected number to the error output. |
| 1007 | `                exit(2);` | Then the program ends with exit status 2. |
| 1008 | `            }` | Ends the `if` of line 1005. |
| 1009 | `        }` | Ends the loop of line 1001. |
| 1010 | `        decode_ids();` | Splits the node ids into column, row, port and device (`decode_ids`). |
| 1011 | `        /* probe on the PMU's own CPU: a counter read from any other CPU is an interrupt to it */` | Comment: the probes run on the CPU of the PMU. By the comment a read of a counter from any other CPU causes an interrupt to the CPU of the PMU. |
| 1012 | `        if (pmu_cpu[0] != pmu_cpu[1])` | Tests whether the two PMUs have different CPUs. |
| 1013 | `            fprintf(stderr, "warning: the two mesh PMUs use different CPUs (%d, %d); probing on %d\n", pmu_cpu[0], pmu_cpu[1], pmu_cpu[0]);` | Then prints a warning with both CPUs. It says that the probes run on the CPU of the PMU of mesh 0. |
| 1014 | `        pin_cpu(pmu_cpu[0]);` | Pins the thread to the CPU of the PMU of mesh 0. The classification and its verification run there (line 1017, line 1027). |
| 1015 | `        fprintf(stderr, "classification runs on CPU %d, %d loads per probe\n", pmu_cpu[0], probe_loads);` | Prints the CPU of the classification and the number of loads per probe to the error output. |
| 1016 | `        double t0 = now_s();` | Reads the clock: `t0`. Only the message of line 1018 uses it. |
| 1017 | `        classify(buf, nlines, home, retries);` | Runs the classification (`classify`): it finds the home node of every line of the main buffer. |
| 1018 | `        fprintf(stderr, "classification took %.1f s\n", now_s() - t0);` | Prints how long the classification took, in seconds. |
| 1019 | `        long unknown = 0;` | `unknown`: the number of lines without a home. |
| 1020 | `        for (uint64_t i = 0; i < nlines; i++)` | Loop over all lines. |
| 1021 | `            unknown += home[i] < 0;` | Counts every line whose `home` value is below 0. |
| 1022 | `        if ((uint64_t)unknown > nlines / 20) {` | Tests whether more than one twentieth of the lines (5 percent) have no home. |
| 1023 | `            fprintf(stderr, "homelat: %.1f%% of the lines have no home: classification rejected (limit 5%%)\n", 100.0 * (double)unknown / (double)nlines);` | Then prints the share in percent and that the classification is rejected (limit 5 percent). |
| 1024 | `            exit(2);` | Then the program ends with exit status 2. |
| 1025 | `        }` | Ends the `if` of line 1022. |
| 1026 | `        long control_false;` | `control_false`: will hold the number of probes in which a control node rose. |
| 1027 | `        double agree = verify_classification(buf, nlines, home, verify_sample, &control_false);` | Probes `verify_sample` random lines again, each with a single counter and one control counter (`verify_classification`). `agree` is the share of confirmed lines, from 0 to 1. |
| 1028 | `        if (agree < 0.98 \|\| control_false > verify_sample / 100) {` | Tests two limits: an agreement below 0.98 (98 percent), or more control hits than `verify_sample / 100`. The division drops the remainder: 512 samples allow 5 control hits. |
| 1029 | `            fprintf(stderr, "homelat: classification rejected (%.1f%% agreement, %ld control hits; limits 98%% and 1%%)\n", 100.0 * agree, control_false);` | Then prints the agreement in percent, the number of control hits and the two limits (98 percent and 1 percent), and that the classification is rejected. |
| 1030 | `            exit(2);` | Then the program ends with exit status 2. |
| 1031 | `        }` | Ends the `if` of line 1028. |
| 1032 | `    } else {` | The other case: the option `--no-perf`. |
| 1033 | `        classify_fake(nlines, home);` | Gives the lines invented homes (`classify_fake`). |
| 1034 | `    }` | Ends the `if` and `else` that began in line 990. |

### Function `main`: the files `nodes.csv`, `chunks.csv` and `homes.csv` (lines 1036 to 1074)

| Line | Source | Explanation |
|---:|---|---|
| 1036 | `    fprintf(fnodes, "mesh,node_id_hex,x,y,port,dev,dtc,lines\n");` | Writes the header row of `nodes.csv`: `mesh,node_id_hex,x,y,port,dev,dtc,lines`. |
| 1037 | `    for (int k = 0; k < nnodes; k++)` | Loop over all home nodes. |
| 1038 | `        fprintf(fnodes, "%d,0x%x,%d,%d,%d,%d,%d,%d\n", nodes[k].mesh, nodes[k].id, nodes[k].x, nodes[k].y, nodes[k].port,` | Writes one row per home node: the mesh, the node id in hexadecimal, the column `x`, the row `y`, and the port. The list goes on in line 1039. |
| 1039 | `                nodes[k].dev, nodes[k].dtc, nodes[k].nlines);` | Continues the call of line 1038: the device, the DTC domain, and the number of lines whose home is this node. |
| 1040 | `    fclose(fnodes);` | Closes `nodes.csv`. |
| 1042 | `    /* per 2 MiB chunk: physical frame and how its lines split over the two meshes */` | Comment: for each 2 MiB chunk of the buffer, the program records its physical page frame and how its lines are split over the two meshes. |
| 1043 | `    int pagemap = open("/proc/self/pagemap", O_RDONLY);` | Opens `/proc/self/pagemap` for reading. A failure does not stop the program: the page frame numbers are then 0 (line 1052). |
| 1044 | `    fprintf(fchunks, "chunk,virt_hex,pfn_hex,contiguous,lines_mesh0,lines_mesh1,lines_unknown\n");` | Writes the header row of `chunks.csv`: `chunk,virt_hex,pfn_hex,contiguous,lines_mesh0,lines_mesh1,lines_unknown`. |
| 1045 | `    for (uint64_t c = 0; c < bytes / HUGE_BYTES; c++) {` | Loop over the 2 MiB chunks of the main buffer. |
| 1046 | `        long m0 = 0, m1 = 0, un = 0;` | `m0`, `m1`, `un`: the lines of the chunk whose home is on mesh 0, on mesh 1, or unknown. |
| 1047 | `        for (uint64_t i = c * (HUGE_BYTES / LINE); i < (c + 1) * (HUGE_BYTES / LINE); i++) {` | Loop over the 32768 lines of the chunk. |
| 1048 | `            if (home[i] < 0) un++;` | A line without a home counts in `un`. |
| 1049 | `            else if (nodes[home[i]].mesh == 0) m0++;` | A line whose home node is on mesh 0 counts in `m0`. |
| 1050 | `            else m1++;` | Every other line counts in `m1`. |
| 1051 | `        }` | Ends the loop of line 1047. |
| 1052 | `        uint64_t pfn = pagemap >= 0 ? pfn_of(pagemap, buf + c * HUGE_BYTES) : 0;` | `pfn`: the page frame number of the first 4096-byte page of the chunk (`pfn_of`). It is 0 when the pagemap file is not open. |
| 1053 | `        int contiguous = pfn != 0;` | `contiguous`: starts at 1 when a page frame number was read, and at 0 when not. |
| 1054 | `        uint64_t pfn_last = pfn;` | `pfn_last`: the last page frame number that was read. |
| 1055 | `        for (uint64_t pg = 1; contiguous && pg < HUGE_BYTES / 4096; pg++) { /* every page (reviewer's request) */` | Loop over the other 511 pages of 4096 bytes of the chunk, as long as `contiguous` is 1. By the comment a reviewer asked for the test of every page. |
| 1056 | `            pfn_last = pfn_of(pagemap, buf + c * HUGE_BYTES + pg * 4096);` | Reads the page frame number of page `pg` of the chunk. |
| 1057 | `            contiguous = pfn_last == pfn + pg;` | `contiguous` stays 1 only when this number is the first number plus `pg`. So it is 1 at the end when the 512 pages follow each other in physical memory, as the parts of one 2 MiB page do. |
| 1058 | `        }` | Ends the loop of line 1055. |
| 1059 | `        fprintf(fchunks, "%lu,0x%lx,0x%lx,%d,%ld,%ld,%ld\n", (unsigned long)c, (unsigned long)(uintptr_t)(buf + c * HUGE_BYTES),` | Writes the row of the chunk: its number and its virtual address in hexadecimal. The list goes on in line 1060. |
| 1060 | `                (unsigned long)pfn, contiguous, m0, m1, un);` | Continues the call of line 1059: the first page frame number in hexadecimal, the flag `contiguous`, and the three line counts. |
| 1061 | `        if (!contiguous)` | Tests whether the chunk is not contiguous. |
| 1062 | `            fprintf(stderr, "warning: chunk %lu is not one physically contiguous 2 MiB page (first pfn 0x%lx, last 0x%lx)\n",` | Then prints a warning to the error output: the chunk is not one physically contiguous 2 MiB page. It gives the first and the last page frame number that were read. |
| 1063 | `                    (unsigned long)c, (unsigned long)pfn, (unsigned long)pfn_last);` | Continues the call of line 1062: the values. |
| 1064 | `    }` | Ends the loop of line 1045. |
| 1065 | `    fclose(fchunks);` | Closes `chunks.csv`. |
| 1066 | `    fprintf(fhomes, "line,mesh,node_id_hex\n");` | Writes the header row of `homes.csv`: `line,mesh,node_id_hex`. |
| 1067 | `    for (uint64_t i = 0; i < nlines; i++) {` | Loop over all lines of the buffer. |
| 1068 | `        if (home[i] < 0)` | Tests whether the line has no home. |
| 1069 | `            fprintf(fhomes, "%lu,-1,%d\n", (unsigned long)i, home[i]);` | Then writes the line index, -1 as the mesh, and the `home` value in the third column. That value is -1 (line 424). |
| 1070 | `        else` | The other case: the line has a home. |
| 1071 | `            fprintf(fhomes, "%lu,%d,0x%x\n", (unsigned long)i, nodes[home[i]].mesh, nodes[home[i]].id);` | Writes the line index, the mesh of the home node and its node id in hexadecimal. |
| 1072 | `    }` | Ends the loop of line 1067. |
| 1073 | `    fclose(fhomes);` | Closes `homes.csv`. |

### Function `main`: the mixed set, the coverage report and the cache-state check (lines 1075 to 1105)

| Line | Source | Explanation |
|---:|---|---|
| 1075 | `    /* latency: from each core to each node, plus a mixed chain over all classified lines */` | Comment: the latency part measures from each core to each node. It also measures one mixed chain over all classified lines. The mixed set of the code does not hold every classified line: it holds at most `lines_per_node` lines, the same number from every node (lines 1079 to 1090). |
| 1076 | `    uint32_t *mixed = malloc((size_t)lines_per_node * sizeof *mixed);` | `mixed`: room for the line indices of the mixed set: `lines_per_node` entries. |
| 1077 | `    if (!mixed)` | Tests whether `malloc` failed. |
| 1078 | `        die("malloc");` | Then `die` prints `homelat: malloc:` with the reason and ends the program with exit status 2. |
| 1079 | `    int nmixed = 0, per = lines_per_node / nnodes; /* the same number of lines from every node, without replacement */` | `nmixed`: the number of lines in the mixed set. `per`: the number of lines that each node gives: `lines_per_node` divided by the number of nodes. With 2048 and 128 nodes that is 16. By the comment every node gives the same number, and no line is taken twice. |
| 1080 | `    if (per < 1) per = 1;` | Each node gives at least 1 line. |
| 1081 | `    for (int k = 0; k < nnodes && nmixed < lines_per_node; k++) {` | Loop over the nodes, until the mixed set is full. |
| 1082 | ``        /* partial Fisher-Yates over this node's line list: the first `take` entries are distinct */`` | Comment: a partial Fisher-Yates shuffle over the line list of this node. After it, the first `take` entries of the list are distinct lines in a random choice. |
| 1083 | `        int take = per < nodes[k].nlines ? per : nodes[k].nlines;` | `take`: `per`, or the number of lines of the node when it has fewer. |
| 1084 | `        for (int j = 0; j < take; j++) {` | Loop over the first `take` places of the line list of the node. |
| 1085 | `            int r = j + (int)(xorshift64() % (uint64_t)(nodes[k].nlines - j));` | `r`: a random place from `j` to the end of the list. |
| 1086 | `            uint32_t tmp = nodes[k].lines[j]; nodes[k].lines[j] = nodes[k].lines[r]; nodes[k].lines[r] = tmp;` | Swaps the entries `j` and `r` of the line list of the node. The measurement of the node later takes the first entries of this same list (line 1126). |
| 1087 | `        }` | Ends the loop of line 1084. |
| 1088 | `        for (int j = 0; j < take && nmixed < lines_per_node; j++)` | Loop over the first `take` entries, as long as the mixed set has room. |
| 1089 | `            mixed[nmixed++] = nodes[k].lines[j];` | Appends the line to the mixed set. |
| 1090 | `    }` | Ends the loop of line 1081. |
| 1091 | `    nmixed &= ~7;` | Rounds `nmixed` down to a multiple of 8, as the loop of `chase` needs. |
| 1092 | `    int short_nodes = 0;` | `short_nodes`: the number of nodes with fewer than `lines_per_node` lines. |
| 1093 | `    for (int k = 0; k < nnodes; k++)` | Loop over all nodes. |
| 1094 | `        if (nodes[k].nlines < lines_per_node) {` | Tests whether the node has fewer than `lines_per_node` lines. |
| 1095 | `            if (!short_nodes)` | Tests whether it is the first such node. |
| 1096 | `                fprintf(stderr, "coverage: nodes with fewer than %d lines:", lines_per_node);` | Then prints the start of a line to the error output: `coverage: nodes with fewer than`, the number, and `lines:`. |
| 1097 | `            fprintf(stderr, " mesh%d/0x%x=%d", nodes[k].mesh, nodes[k].id, nodes[k].nlines);` | Adds the mesh, the node id and the number of lines of the node to that line. |
| 1098 | `            short_nodes++;` | Counts the node. |
| 1099 | `        }` | Ends the `if` of line 1094. |
| 1100 | `    if (short_nodes)` | Tests whether a node is short. |
| 1101 | `        fprintf(stderr, "\ncoverage: %d of %d nodes are short; their rows use fewer lines or are missing (under 64)\n", short_nodes, nnodes);` | Then ends the line and prints how many of the nodes are short. The text says that the rows of these nodes use fewer lines, or are missing when the node has fewer than 64 lines. |
| 1102 | `    else` | The other case: no node is short. |
| 1103 | `        fprintf(stderr, "coverage: every node has at least %d lines\n", lines_per_node);` | Prints that every node has at least `lines_per_node` lines. |
| 1104 | `    if (use_perf && verify_count > 0)` | Tests whether the counters are used and the cache-state check is on (`--verify-slices` above 0). |
| 1105 | `        verify_slices(buf, ev, cores[0], verify_count, lines_per_node, reps, out);` | Then runs the cache-state check from the first core of the core list (`verify_slices`). The function pins the thread to that core. Without `--verify-lenient` a failed slice ends the program there. |

### Function `main`: the latency loop over the cores and the home nodes (lines 1106 to 1137)

| Line | Source | Explanation |
|---:|---|---|
| 1106 | `    fprintf(flat, "core,mesh,node_id_hex,x,y,dev,lines,ns_median,ns_min,ns_max");` | Writes the start of the header row of `latency.csv`: the core, the mesh, the node id, `x`, `y`, the device, the number of lines, and the median, the minimum and the maximum latency in ns per load. |
| 1107 | `    for (int r = 0; r < reps; r++)` | Loop over the repeats. |
| 1108 | `        fprintf(flat, ",ns_rep%d", r + 1);` | Adds one column per repeat to the header: `ns_rep1`, `ns_rep2` and so on. |
| 1109 | `    fprintf(flat, "\n");` | Ends the header row. |
| 1110 | `    double t0 = now_s();` | Reads the clock: `t0`. Only the progress message of line 1133 uses it. |
| 1111 | `    for (int ci = 0; ci < ncores; ci++) {` | Loop over the cores of the core list, in the order of the list. |
| 1112 | `        int core = cores[ci];` | `core`: the CPU number of this pass. |
| 1113 | `        pin_cpu(core);` | Pins the thread to this core. Everything up to the next pass of this loop runs on this CPU: the build of the chains, the fill loads, the evictor reads and the timed passes. |
| 1114 | `        double med, mn, mx, all[8];` | `med`, `mn`, `mx`: the median, the minimum and the maximum of one set. `all`: the value of every repeat. |
| 1115 | `        if (nmixed >= 64) {` | Tests whether the mixed set has at least 64 lines. |
| 1116 | `            measure(buf, ev, mixed, nmixed, reps, &med, &mn, &mx, all);` | Then measures the mixed set from this core (`measure`): `reps` timed passes, each over a new chain through the `nmixed` lines. |
| 1117 | `            fprintf(flat, "%d,-1,mixed,-1,-1,-1,%d,%.2f,%.2f,%.2f", core, nmixed, med, mn, mx);` | Writes the row of the mixed set: the core, -1 as the mesh, the word `mixed` in place of a node id, -1 for `x`, `y` and the device, the number of lines, and the median, minimum and maximum in ns per load with 2 decimals. |
| 1118 | `            for (int r = 0; r < reps; r++) fprintf(flat, ",%.2f", all[r]);` | Adds the value of every repeat to the row, in the order of the runs. |
| 1119 | `            fprintf(flat, "\n");` | Ends the row. |
| 1120 | `        }` | Ends the `if` of line 1115. |
| 1121 | `        for (int k = 0; k < nnodes; k++) {` | Loop over all home nodes of both meshes, in the order of the node table. |
| 1122 | `            int n = nodes[k].nlines < lines_per_node ? nodes[k].nlines & ~7 : lines_per_node;` | `n`: the number of lines of the set of this node. It is `lines_per_node`. For a node with fewer lines it is the number of its lines, rounded down to a multiple of 8. |
| 1123 | `            if (n < 64)` | Tests whether the set has fewer than 64 lines. |
| 1124 | `                continue;` | Then skips the node. It gets no row for this core. |
| 1125 | `            check_marker();` | Looks for the marker file once per node (`check_marker`). |
| 1126 | `            measure(buf, ev, nodes[k].lines, n, reps, &med, &mn, &mx, all);` | Measures the set of this node from this core (`measure`). The set is the first `n` lines of the line list of the node. There are `reps` timed passes, each over a new chain. |
| 1127 | `            fprintf(flat, "%d,%d,0x%x,%d,%d,%d,%d,%.2f,%.2f,%.2f", core, nodes[k].mesh, nodes[k].id, nodes[k].x, nodes[k].y,` | Writes the row: the core, the mesh of the node, its node id in hexadecimal, `x` and `y`. The list goes on in line 1128. |
| 1128 | `                    nodes[k].dev, n, med, mn, mx);` | Continues the call of line 1127: the device, the number of lines, and the median, minimum and maximum latency in ns per load with 2 decimals. |
| 1129 | `            for (int r = 0; r < reps; r++) fprintf(flat, ",%.2f", all[r]);` | Adds the value of every repeat to the row. |
| 1130 | `            fprintf(flat, "\n");` | Ends the row. |
| 1131 | `        }` | Ends the loop of line 1121. |
| 1132 | `        fflush(flat);` | Writes the buffered rows of this core to the file now (`fflush`). |
| 1133 | `        fprintf(stderr, "core %d done (%.0f s)\n", core, now_s() - t0);` | Prints `core`, the CPU number, `done` and the seconds that passed after the clock read of line 1110 to the error output. |
| 1134 | `    }` | Ends the loop of line 1111. |
| 1135 | `    fclose(flat);` | Closes `latency.csv`. |
| 1136 | `    return 0;` | Returns 0, the exit status for success. |
| 1137 | `}` | Ends `main`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/sudo-20261102T054936Z/log.txt`: the log of a run of `run_sudo.sh` on CRB that started on 2026-11-02 at 05:49 UTC. Its lines `arm_cmn_0: perf type 9, cpu 0, ...` and `arm_cmn_1: perf type 10, cpu 0, ...` show the CPU of both PMUs. The log also holds the line `classification runs on CPU 0, 256 loads per probe`.
- [Ref2] external source: Linux kernel documentation, page `admin-guide/mm/pagemap` (the file `/proc/pid/pagemap` holds one 64-bit entry per page. The bits 0 to 54 are the page frame number, and bit 63 says that the page is present. The page frame number is 0 for a process without the capability `CAP_SYS_ADMIN`).
- [Ref3] external source: Linux kernel documentation, page `admin-guide/perf/arm-cmn` (an event counts the sum over all nodes of its type. With `bynodeid` set to 1 and a `nodeid` it counts at one node).
- [Ref4] external source: Linux manual page `perf_event_open(2)` (the arguments `pid`, `cpu` and `group_fd`, and the data that a read returns with `PERF_FORMAT_GROUP`).
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/cmn-map.txt`: the maps of the two meshes, as printed from the files `map` and `map_1` of the Linux driver. Each crosspoint shows its DTC number. Both maps show DTC 1 and DTC 0 in the rows 4 to 7 and DTC 2 and DTC 3 in the rows 0 to 3.
- [Ref6] external source: Arm Architecture Reference Manual for A-profile architecture, the instructions `DC CIVAC` (clean and invalidate a data cache line by address) and `DSB` (data synchronization barrier).
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/plan-2026-11-02.md`: the plan note of 2026-11-02. Its word list defines the mesh (Arm CMN S3, one mesh of 9 by 8 crosspoints per half of the chip), the home node (HN-S), the slice and the DTC (one per quarter of a mesh, 4 per mesh, each with 8 counters).
