## Short version: purpose

`run_crb.sh` runs the first measurement plan on CRB without root rights. It measures the load latency per buffer size with `latency`, repeats that sweep under `perf stat` to count cache refills, and measures the read, write and copy throughput with `bandwidth` for several buffer sizes and thread counts. It keeps all processes on the CPUs 0 to 119, stops when the marker file exists, and writes its results into a new result folder.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`latency`**: the program built from `latency.c`. One thread follows a random cycle of pointers through a buffer. The program prints the time per load in nanoseconds.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Cycle**: in `latency`, one walk through all cache lines of the buffer. The event `cpu_cycles` is another thing: it counts the clock cycles of the processor.
- **Chunk**: the loads that `latency` does between two reads of its clock: a whole number of cycles, about 1048576 loads for a small buffer.
- **Sweep**: a row of runs of one program with one setting changed from run to run, for example the buffer size.
- **Case**: the script names four cases by the place where the buffers of the threads fit: L1, L2, L3 and DRAM. The source calls a case a regime.
- **L1, L2, L3, DRAM**: the cache of level 1 and of level 2 of one core, the last cache level, and the main memory.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events for it.
- **Refill**: a line that is brought into a cache from outside.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Governor**: the Linux policy that sets the CPU frequency.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **KiB, MiB, GiB**: 1024 bytes, 1048576 bytes and 1073741824 bytes.

## Main flow

1. Set the shell options: stop on a failed command and on an unset variable ({L21}).
2. Start the script again under `taskset -c 0-119`. Every process of the run then stays on the CPUs 0 to 119 ({L25-27}).
3. Set the paths and read the argument `--quick` ({L29-39}).
4. Check the CPU list of the variable `CPUS`. Stop when it holds a CPU above 119 ({L41-52}).
5. Stop when the marker file exists. Then create the result folder and send all later output to `log.txt` too ({L61-65}).
6. Choose the plan: the quick plan or the full plan with its sizes, times and thread counts ({L69-90}).
7. Build the programs with `make` ({L92-93}).
8. Write the description of the machine to `sysinfo.txt` ({L95-110}).
9. Latency sweep: start one `latency` process per buffer size on CPU 3 (quick plan: on the first CPU of the list `CPUS`) and collect the output in `latency.csv` ({L112-117}).
10. Latency sweep under `perf stat`: for each size, one short and one long run of `latency` with 7 counter events ({L122-140}).
11. Bandwidth sweep: the function `run_bw` starts `bandwidth` once per thread count, for the L1, L2, L3 and DRAM cases ({L142-159}).
12. Print the path of the result folder ({L161-162}).

## Behavior a reader must know

- The script times nothing itself. Every time and every rate comes from `latency` or `bandwidth`.
- Marker checks: once before the result folder is created, then before each `latency` process of the first sweep, once per size before the two runs under `perf stat`, and before each `bandwidth` process. The long run under `perf stat` has no check of its own. A check that finds the file ends the script with exit status 3. A benchmark process that already runs is not stopped.
- Exit status 2 means a wrong argument or a bad CPU list. With the option `-e`, a failed `make`, a failed `latency` of the first sweep or a failed `bandwidth` also ends the script, with the status of that command.
- A failed run under `perf stat` does not end the script. It prints a message and goes on with the next size.
- Thread placement: `taskset` limits the script and all its child processes to the CPUs 0 to 119. `latency` pins its one thread to CPU 3 in the full plan, and to the first CPU of the list `CPUS` in the quick plan. `bandwidth` pins thread number `i` to entry `i` of the CPU list, so `t` threads use the CPUs 0 to `t - 1` with the default list.
- No command passes `--no-thp`. So both programs ask Linux for 2 MiB pages for their buffers.
- `perf stat` counts for the whole `latency` process, also for the build of the buffer and the warm-up. That is why each size has a short and a long run: the analysis script `summarize.py` divides the difference of the counts by the difference of the loads.
- The script runs `perf` without root rights. A comment of `run_sudo.sh` says that the Linux setting `perf_event_paranoid` is 2 on CRB. With this value a normal user can count events in user mode only [Ref3].
- The comment of {L119} says that the short run times exactly 2 cycles. For the sizes of the plan up to 16 MiB the short run times one chunk of about 1048576 loads, which is 4 cycles or more.
- The header comment counts 27 bandwidth configurations. The full plan starts `bandwidth` 33 times ({L153-159}).
- Files in the result folder: `log.txt`, `sysinfo.txt`, `latency.csv`, `latency-perfrun-short.csv`, `latency-perfrun-long.csv`, two files `latency-perf-SIZE-short.csv` and `latency-perf-SIZE-long.csv` per size, and `bandwidth.csv`.

## References

- [Ref1] external source: manual page `perf-stat(1)` (the command runs a program and counts events for it. The options `-e`, `-x` and `-o`).
- [Ref2] external source: Arm Architecture Reference Manual for A-profile architecture, the list of the common events of the performance monitors (`L1D_CACHE_REFILL`, `L2D_CACHE_REFILL`, `L3D_CACHE_REFILL`, `LL_CACHE_MISS_RD`, `DTLB_WALK`, `CPU_CYCLES`, `INST_RETIRED`).
- [Ref3] external source: Linux manual page `perf_event_open(2)`, the file `/proc/sys/kernel/perf_event_paranoid` (the value 2 allows only measurements in user space).
