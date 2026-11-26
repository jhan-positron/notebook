## Short version: purpose

`collect.py` reads the result folders of the first test scripts and prints one JSON text with their numbers, for the report. It takes the best latency per buffer size, the best rate per bandwidth run, and the counter events per load. It measures nothing itself.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Main folder**: a result folder of the script `run_crb.sh`.
- **Follow-up folder**: a result folder of the script `run_followup.sh`.
- **Uncore folder**: a result folder of the script `run_uncore.sh`, which counts events of the mesh.
- **JSON**: a text format for structured data.
- **`latency`**: the benchmark that follows a chain of pointers through a buffer with one thread. It prints one row per timed interval and one `best` row per buffer size, in nanoseconds per load.
- **`bandwidth`**: the benchmark whose threads read, write or copy their buffers. It prints one row per repetition and one `best` row per kernel, with the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`best` row**: the row that a benchmark prints with its best value: the smallest ns per load of `latency`, or the highest rate of `bandwidth`.
- **Load**: one read of a pointer in `latency`.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events for it.
- **Short run, long run**: two runs of the same benchmark under `perf stat` that differ only in the number of timed loads.
- **Mesh**: the network inside one half of the chip that connects the cores, the last cache level and the memory. It has counters of its own.
- **`AnonHugePages`**: a value that Linux reports for a process: the memory without a file behind it that lies on 2 MiB pages, in kB.
- **Rate**: bytes divided by time, in GB/s.
- **GB**: 1e9 bytes.

## Main flow

1. Read the three folder names from the arguments. The second and the third are optional ({L89-92}).
2. Main folder: read `latency.csv` and keep the `best` value per size, the rows of the single intervals and the `AnonHugePages` values ({L93-96}).
3. Main folder: compute the core events per load from the short and the long run of each size (`refills_per_load` divides the difference of the counts by the difference of the loads) ({L97}).
4. Main folder: read the `best` rows of `bandwidth.csv` ({L98}).
5. Follow-up folder, when given: read `latency-fresh.csv`, the three bandwidth files `pair.csv`, `asm.csv` and `dram.csv`, and the blocks of `latency-bycpu.csv` ({L99-115}).
6. Uncore folder, when given: compute the mesh events per load, and read the counts and the rates of the two streaming read runs ({L116-120}).
7. Print everything as JSON text to the standard output ({L121}).

## Behavior a reader must know

- Latency numbers come from the `best` rows: column 4 (ns per load) under column 1 (size in bytes). The benchmark itself formed that minimum.
- Bandwidth numbers come from the `best` rows: column 7 (the total rate in GB/s), with the kernel, the thread count and the bytes per thread from the columns 1 to 3. The title line before a run is kept as the context of the row.
- Events per load: the count of the long run minus the count of the short run, divided by the loads of the long run minus the loads of the short run. A count is field 1 of a line of `perf stat`, under the event name in field 3. The loads are column 3 of the `best` rows.
- The script does not read the share of the time for which a counter was running (field 5 of a line of `perf stat`). So it does not notice a multiplexed counter, whose count is a scaled value.
- An event whose count is not a number, for example `<not counted>`, gets no rate. A size gets no rates when a file is missing or when the long run has no more loads than the short run.
- For the two streaming read runs of the uncore folder, the counts are stored unchanged, without a subtraction.
- The script writes no file. The caller sends the output to a file.
- A missing `latency.csv` or `bandwidth.csv` in the main folder stops the script with a Python error.
