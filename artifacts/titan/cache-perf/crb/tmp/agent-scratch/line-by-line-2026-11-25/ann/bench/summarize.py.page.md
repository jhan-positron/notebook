## Short version: purpose

`summarize.py` reads one result folder of the script `run_crb.sh` and prints three groups of Markdown tables. The tables show the latency per buffer size with the counter events per load, the bandwidth per buffer size and thread count, and one summary row per cache level. It measures nothing itself.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`latency`**: the benchmark that follows a chain of pointers through a buffer with one thread. It prints one row per timed interval and one `best` row per buffer size, in nanoseconds per load.
- **`bandwidth`**: the benchmark whose threads read, write or copy their buffers. It prints one row per repetition, with the total rate and the smallest and the largest rate of a single thread.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Load**: one read of a pointer in `latency`.
- **`best` row**: the row that `latency` prints with the smallest ns per load of a buffer size.
- **Total rate**: the column `aggregate_GBps` of `bandwidth`: the bytes of all threads divided by the time of the slowest thread, in GB/s.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events for it.
- **Short run, long run**: two runs of `latency` under `perf stat` that differ only in the number of timed loads.
- **Refill**: a line that is brought into a cache from outside.
- **Case**: `run_crb.sh` names its bandwidth runs by the place where the buffers fit: L1, L2, L3 or DRAM. The source calls a case a regime.
- **L1, L2, L3, DRAM**: the cache of level 1 and of level 2 of one core, the last cache level, and the main memory.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Clock cycles**: the latency in ns times the clock rate of the cores in GHz.
- **Markdown**: a plain text format in which a table is written with vertical bars.
- **GB**: 1e9 bytes.
- **KiB, MiB, GiB**: 1024 bytes, 1048576 bytes and 1073741824 bytes.

## Main flow

1. Read the arguments: the result folder and the option `--ghz`, the clock rate of the cores ({L97-105}).
2. Read the input files: `latency.csv`, the count files and the load numbers of the short and the long runs, and `bandwidth.csv` ({L107-114}).
3. Print the latency table: one row per buffer size with the best ns per load, the clock cycles and 5 events per load ({L116-137}).
4. Print one bandwidth table per buffer size per thread: for each kernel the best total rate and the range of the per-thread rates, per thread count ({L139-150}).
5. Print the summary: one row per cache level with its latency and its read, write and copy rates ({L152-170}).

## Behavior a reader must know

- Latency per size: the `best` row of `latency.csv`, column 4. `latency` formed that minimum over its timed intervals.
- Events per load: the count of the long run minus the count of the short run, divided by the loads of the long run minus the loads of the short run. The counts are field 1 of the files `latency-perf-SIZE-short.csv` and `latency-perf-SIZE-long.csv`. The loads are column 3 of the `best` rows of `latency-perfrun-short.csv` and `latency-perfrun-long.csv`. A missing value gives `n/a`.
- The script does not read the share of the time for which a counter was running (field 5 of a line of `perf stat`).
- Bandwidth per run: of the repetition rows of `bandwidth.csv`, the script keeps the repetition with the highest total rate (column 7), together with the smallest and the largest per-thread rate of that same repetition (columns 8 and 9). It does not use the `best` rows of `bandwidth`.
- Only the kernels `read`, `write` and `copy` are read. Rows of other kernels are skipped.
- Latency of a level: the smallest best value of the sizes in the range of the level: 16 KiB to 32 KiB for L1, 256 KiB to 1 MiB for L2, 8 MiB to 64 MiB for L3, and 1 GiB to 2 GiB for DRAM.
- Rate of a level: the highest best total rate of all runs whose size per thread belongs to the level (32 KiB, 1 MiB, 8 MiB, and 256 MiB or 1 GiB), over all thread counts. The cell also shows the rate of the run with 1 thread.
- Clock cycles are computed, not measured: ns times the value of `--ghz`, which is 2.8 by default.
- With no argument or more than one argument the script prints its description text and ends with exit status 1.
