## Short version: purpose

`r8g.spec` is a spec file for the script `rg.sh`: 4 lines, and each line gives one group of two runner processes that run at the same time, one on mesh 0 and one on mesh 1. The four groups are the four combinations of the kernels `asmread` and `read_nop256`. Every thread counts how many answers arrive at its core with each busy level.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. This file has the form of the script `rg.sh`: each line gives one group of processes.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Group**: the processes of one line. The script `rg.sh` starts them one after the other and waits until all of them have ended.
- **Item**: one process of a group, in the form `tag=arguments`. The items of a line are separated by ` ;; `. The script writes the output of an item to the file `GROUP.TAG.csv`.
- **`read_nop256`**: the `asmread` loop with 256 `nop` instructions after the 8 loads of each 256 B. A `nop` is an instruction that does nothing.
- **Busy level**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. This definition comes from the notes of the ASCT cross-check in the same repo.
- **`cbusy0` to `cbusy3`**: the names that this file gives to the event codes `0x198` to `0x19b`. The analysis script `an8.py` reads them as the answers with the busy level 0 to 3.
- **`cbusy_mt`**: the name that this file gives to the event code `0x19c`. No file of this folder says what it counts, and `an8.py` does not read it.
- **`bus_access`**: the name that this file gives to the event code `0x19`. In the table of the common Arm events this code counts bus accesses [Ref3].

## Main flow

1. Read one line as one group. The text before the first `|` is the group name. The rest holds the two items, with ` ;; ` between them ({L1}).
2. Read one item as one process. The text before the first `=` is the tag of the item: `m0` for the process on mesh 0, `m1` for the process on mesh 1. The rest holds the arguments of the runner, as the function `main` of `bwx12.c` reads them. An `=` inside the arguments, as in `cbusy0=0x198`, belongs to the arguments.
3. `--threads` and `--cpus` give the number of threads and the CPU of each thread.
4. `--bytes` gives the size of the buffer that each thread owns and reads. `256M` means 256 MiB.
5. `--stop common` and `--min-ms` give the timing of the one interval of a process. The main thread of the process sets one start time and one stop time for its threads. Each thread reads its buffer in chunks of 2 MiB, reads the clock after each chunk and stops at the first clock reading at or after the stop time.
6. `--start common` makes each thread begin at the first byte of its buffer.
7. `--seq` names the kernel, and `--rounds 1` runs it for one interval.
8. `--count`, `--pmu-type` and `--events` turn on the core counters. Each thread counts the six named events during the interval. An event is written `name=code`. The runner uses the name as the head of a column and gives the code and the number of `--pmu-type` to Linux.

## Behavior a reader must know

- The file holds no command. The script `rg.sh` starts the processes of a line one after the other and limits each one to the CPUs 0 to 119.
- The common stop holds inside one process only. Each of the two processes sets its own start time and stop time. So the two intervals of a group overlap, but they do not begin at the same moment.
- The counters are counters of the cores. Each thread counts for itself, in its own process, during its own interval.
- The launch record of the result folder `w120-R8g-20261117T020823Z` holds 4 launch lines with the group names and the items of this file. Its `env.txt` names the binary `bwx12` [Ref1].
- Three result folders of the test `2026-11-17-firmware-and-dimm` hold the same 4 launch lines: `w120-X1d10g-20261117T035150Z`, `w120-X2d12g-20261117T041155Z` and `w120-w120-F72d12g-20261117T200504Z` [Ref2].

## References

- [Ref1] test data: the files `launches.txt` and `env.txt` in the folder `tests/2026-11-15-whole-chip-read-drop/w120-R8g-20261117T020823Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`.
- [Ref2] test data: the files `launches.txt` of the three named folders in `tests/2026-11-17-firmware-and-dimm` of the same repo.
- [Ref3] external source: Linux source tree, file `tools/perf/pmu-events/arch/arm64/common-and-microarch.json`. It lists the common Arm counter events with code, name and a short description.
