## Short version: purpose

`run_followup3.sh` runs three experiments of 2026-11-02 on CRB without root rights. Parts A and B measure the write rate and the read rate to main memory while the number of threads on each of the two meshes changes. Part C measures, for each of the CPUs 0 to 119 alone, the latency at a buffer of 16 MiB and the read rate at a buffer of 8 MiB.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Mesh cache**: the word of the source for the SLC.
- **DRAM**: the main memory.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`latency`**: the program built from `latency.c`. One thread follows a cycle of pointers through a buffer. The program prints the time per load in nanoseconds.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`asmread`, `asmwrite`**: two kernels of `bandwidth` that are written in assembly. `asmread` only loads, and `asmwrite` only stores.
- **Grid**: the set of pairs of thread counts: `a` threads on mesh 0 and `b` threads on mesh 1.
- **Standard mode, fresh mode**: two modes of `latency`. In the standard mode each timed repetition walks the same cycle of pointers repeatedly. In the fresh mode (option `--fresh`) each timed pass walks a cycle that was never walked before.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **MiB**: 1048576 bytes.

## Main flow

1. Set the shell options and start the script again under `taskset -c 0-119` ({L10-13}).
2. Stop when the marker file exists. Then create the result folder, send all later output to `log.txt` too, and build the programs ({L14-23}).
3. Define the two helper functions. `cpulist` builds the CPU list for `a` threads on mesh 0 and `b` threads on mesh 1, and `grid` starts `bandwidth` once per pair ({L25-33}).
4. Part A: the kernel `asmwrite` with 256 MiB per thread for 24 pairs of thread counts ({L35-37}).
5. Part B: the kernel `asmread` with 256 MiB per thread for 6 of these pairs ({L39-41}).
6. Part C, two times: for each CPU from 0 to 119, `latency` at 16 MiB in the standard mode and in the fresh mode, and then `bandwidth` with one `asmread` thread at 8 MiB ({L43-54}).
7. Print the time and the path of the result folder ({L55}).

## Behavior a reader must know

- The script times nothing itself. Every time and every rate comes from `latency` or `bandwidth`.
- Marker checks: once at the start, then before each `bandwidth` process of the grids, and once per CPU in part C. A check that finds the file ends the script with exit status 3. A process that already runs is not stopped.
- With the option `-e` a failed `make` or a failed benchmark process ends the script with the status of that command.
- Thread placement in the parts A and B: `bandwidth` pins thread number `i` to entry `i` of the CPU list. The list holds the first `a` CPUs of mesh 0 and then the first `b` CPUs of mesh 1. The highest CPU in use is 119.
- Thread placement in part C: one process at a time, with its one thread pinned to the CPU of the loop. No other benchmark runs at the same time.
- No command passes `--no-thp`. So both programs ask Linux for 2 MiB pages for their buffers.
- Files in the result folder: `log.txt`, `writegrid.csv` (part A), `readgrid.csv` (part B), and for each of the two sweeps of part C `percore-latency-N.csv` and `percore-asmread-N.csv`. A line that starts with `--` names the run whose rows follow.
