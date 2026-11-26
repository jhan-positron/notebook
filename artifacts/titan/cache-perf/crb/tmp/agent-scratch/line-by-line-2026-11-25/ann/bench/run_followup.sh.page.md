## Short version: purpose

`run_followup.sh` runs five more experiments on CRB after the first sweep of 2026-10-30, without root rights. It starts `latency` and `bandwidth` with other settings: fresh chains, pairs of CPUs, the asm kernels, more thread counts and three different CPUs. Each part writes one CSV file into a new result folder.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`latency`**: the program built from `latency.c`. One thread follows a cycle of pointers through a buffer. The program prints the time per load in nanoseconds.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Asm kernels**: the kernels `asmread`, `asmwrite` and `asmcopy` of `bandwidth`. They are written in assembly and hold only loads and stores. `asmall` selects all three.
- **Compiled kernels**: the kernels `read`, `write` and `copy` of `bandwidth`, which are written in C. `all` selects all three.
- **Chain**: one cycle of pointers through all cache lines of the buffer of `latency`.
- **Fresh mode**: the mode of the option `--fresh` of `latency`. Each timed pass walks a chain that was never walked before.
- **Standard mode**: the mode of `latency` without `--fresh`. Each timed repetition walks the same chain repeatedly.
- **Temporal prefetcher**: the part of a core that records the order of earlier cache misses and fetches the same lines in the same order again.
- **L2 case, DRAM case**: buffer sizes that fit into the L2 cache of a core, or that are far larger than all caches. The source calls a case a regime.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **KiB, MiB, GiB**: 1024 bytes, 1048576 bytes and 1073741824 bytes.

## Main flow

1. Set the shell options and start the script again under `taskset -c 0-119` ({L9-12}).
2. Stop when the marker file exists. Then create the result folder, send all later output to `log.txt` too, and build the programs ({L13-22}).
3. Part A: `latency` in the fresh mode on CPU 3, one process per size, 25 sizes from 256 KiB to 2 GiB ({L24-31}).
4. Part B: `bandwidth` with 2 reading threads on 9 pairs of CPUs with 8 MiB per thread, and then three more runs with 1 MiB and 1 GiB ({L33-44}).
5. Part C: the asm kernels for buffer sizes from 32 KiB to 1 GiB and 1 to 120 threads, on the CPUs 0 to 119 and on the even CPUs ({L46-59}).
6. Part D: the compiled kernels with 256 MiB per thread: 48, 80 and 112 threads on the CPUs 0 to 119, and 32, 48 and 60 threads on the even CPUs ({L61-66}).
7. Part E: `latency` in the standard mode and in the fresh mode from the CPUs 3, 64 and 119 ({L68-75}).
8. Print the path of the result folder ({L76}).

## Behavior a reader must know

- The script times nothing itself. Every time and every rate comes from `latency` or `bandwidth`.
- Marker checks: once at the start and then once per loop pass, before the first benchmark process of the pass. A loop pass of part E starts two `latency` processes, and the second one ({L74}) has no check of its own. The three single runs of {L39-44} have no check of their own either. A check that finds the file ends the script with exit status 3. A process that already runs is not stopped.
- With the option `-e` a failed `make` or a failed benchmark process ends the script with the status of that command.
- Thread placement: `taskset` limits everything to the CPUs 0 to 119. `latency` pins its one thread to the CPU of `--cpu`. `bandwidth` pins thread number `i` to entry `i` of its CPU list. So `t` threads on the list `0-119` use the CPUs 0 to `t - 1`, and `t` threads on the list `0-118:2` use the even CPUs 0 to 2 times `t` minus 2.
- No command passes `--no-thp`. So both programs ask Linux for 2 MiB pages for their buffers.
- Files in the result folder: `log.txt`, `latency-fresh.csv` (part A), `pair.csv` (part B), `asm.csv` (part C), `dram.csv` (part D) and `latency-bycpu.csv` (part E). In the files of the parts B to E a line that starts with `--` names the run whose rows follow.
