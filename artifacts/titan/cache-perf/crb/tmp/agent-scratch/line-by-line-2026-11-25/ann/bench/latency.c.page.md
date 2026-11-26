## Short version: purpose

`latency.c` is a benchmark with one thread that measures the latency of a load for each buffer size, in nanoseconds per load. It fills the buffer with one random cycle of pointers, one pointer per 64-byte cache line, and times how long the thread needs to follow them. Each load needs the result of the load before it, so the time per load shows how long one load takes from the cache level, or from the memory, that holds a buffer of this size.

## Words used here

- **Line**: a cache line, 64 bytes. The caches of the chip hold memory in pieces of this size.
- **Pointer chase**: a loop in which each load reads the address of the next load.
- **Dependent load**: a load whose address is the value that the load before it delivered.
- **Load-to-use latency**: the time from the start of a load until the next instruction can use the loaded value.
- **Chain**: one cycle of pointers through all lines of the buffer. Chain number `c` uses the 8-byte word number `c` of each line.
- **Cycle**: a closed walk along the pointers. It starts at any line, visits every line of the buffer once and arrives at its start again. One cycle has as many loads as the buffer has lines.
- **Shuffle of Sattolo**: an algorithm that puts the lines into a random order that forms one single cycle.
- **Prefetcher**: the part of a core that loads memory in advance when it finds a pattern in the addresses.
- **Temporal prefetcher**: a prefetcher that records the order of earlier cache misses and fetches the same lines in the same order again.
- **Standard mode**: the mode without the option `--fresh`. Every timed interval walks chain 0 repeatedly.
- **Fresh mode**: the mode of the option `--fresh`. Every timed interval is one pass over a chain that was never walked before.
- **Chunk**: the loads between two clock reads in the standard mode. A chunk is a whole number of cycles, about 1048576 loads for a small buffer.
- **Warm-up**: loads that run before a timed interval and are not timed.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **`AnonHugePages`**: a value that Linux reports for a process: the memory without a file behind it that lies on transparent huge pages, in kB.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **KiB, MiB, GiB**: 1024 bytes, 1048576 bytes and 1073741824 bytes.

## Main flow

1. `main` sets the defaults and reads the arguments ({L230-268}).
2. It adds the sizes of the doubling range of `--min` and `--max` to the size list and checks the settings ({L269-279}).
3. It pins the thread to the CPU of `--cpu` when that option was given ({L280-282}).
4. It prints the two header lines of the output ({L284-286}).
5. It calls `run_size` once per size, in the order of the list ({L287-288}). The steps 6 to 11 happen inside `run_size`.
6. Reserve the buffer and build the chains: `alloc_buf` reserves a range whose start is a multiple of 2 MiB, and `build_cycle` writes every line for the first time and builds one random cycle of pointers per chain ({L144-156}).
7. With `--build-cpu`: walk chain 0 once on the build CPU, then pin the thread to the CPU of `--cpu` ({L157-160}).
8. Print a comment line with the size and the `AnonHugePages` value of the process ({L161}).
9. Fresh mode: walk chain 0 twice as a warm-up, then time exactly one pass over each other chain ({L166-188}). With `--build-cpu` the two warm-up walks are left out, and the walk of step 7 is the only warm-up.
10. Standard mode: walk one cycle as a warm-up, then run the timed intervals. Each interval is a row of chunks, with one clock read after each chunk ({L189-210}).
11. Print the `best` row and release the buffer ({L211-213}).

## Behavior a reader must know

- What is timed: only the calls of `chase` and, in the standard mode, one clock read per chunk. The build of the buffer, the first write, the warm-up walks and the output are outside every timed interval.
- The clock is `CLOCK_MONOTONIC`. It is read directly before the first load of an interval and directly after each chunk ({L196}, {L200}), or directly before and after the one pass of the fresh mode ({L178}, {L180}).
- The latency of a row is the elapsed time divided by the number of loads of the interval, in nanoseconds per load. The `best` row holds the smallest value of the size.
- The time per load also holds the loop control of `chase`: one step of the counter and one test per 8 loads.
- In the standard mode an interval ends at the first clock read at which two conditions hold: the time of `--min-ms` has passed (300 ms by default), and the cycles of `--min-cycles` were walked (2 by default). There are 3 intervals per size by default.
- In the fresh mode an interval is one pass of `n` loads, where `n` is the number of lines. The options `--reps`, `--min-ms` and `--min-cycles` have no effect there.
- Thread placement: the program has one thread. With `--cpu` it is pinned to that CPU for the whole run. With `--build-cpu` the buffer is written and built on the build CPU, and the timed chase runs on the CPU of `--cpu`. Without `--cpu` nothing is pinned.
- The buffer: one new buffer per size. The reserved range is rounded up to a multiple of 2 MiB, but the chains use only the bytes of the size. By default the program asks Linux for 2 MiB pages (`MADV_HUGEPAGE`). With `--no-thp` it asks for no 2 MiB pages (`MADV_NOHUGEPAGE`). It does not test the result. It prints the `AnonHugePages` value in the comment line of each size.
- The order of the pointers is random but fixed: the start value of the random numbers is a constant. So a size has the same order of the lines in every run.
- A size must be a multiple of 512 bytes. If not, the program ends with exit status 2. A wrong argument also ends it with exit status 2, after the usage text.
