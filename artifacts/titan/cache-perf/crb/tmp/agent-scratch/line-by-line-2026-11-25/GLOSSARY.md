# Glossary for the line-by-line pages

Use these definitions word for word in the list "Words used here" of a page, and when you define one of these terms inside an explanation. Add the terms of your own file after them. Take only the terms that your page uses.

## The machine

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Whole chip, 120 threads**: our runs use the CPUs 0 to 119 only: 64 threads on mesh 0 plus 56 threads on mesh 1.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM, a plug-in memory board.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Boot id**: a random identifier that Linux creates once per boot. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports in the file `/proc/meminfo`, in kB.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Governor**: the Linux policy that sets the CPU frequency.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.

## The benchmarks

- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).

## The scripts and the tests

- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Session**: one pass of `go.sh` through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the binaries `bw_old` and `bw_new`.
- **Part L**: one `bwx12` process with the kernel sequence `oldread`, `asmread`, `read_nop96`, `read_nop256`, `read_1pl`.
- **Part C**: one `bwx12` process with the sequence `oldread`, `read`, `asmread` (spec file `cfwd.spec`) or the reverse order (`crev.spec`).
- **Rerun**: the run of the whole-chip test on 2026-11-17, at a memory speed of 7200 MT/s.
- **Hardware record**: the record of the clock rate of the cores, of the signs of throttling and of the power that the file `hw.sh` makes beside a test since 2026-11-24.
- **`atx`**: Arm Telemetrix, a tool of the chip vendor. It reads power, temperature and frequency values of the firmware.
- **ASCT**: a measurement tool from Arm.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Facts sheet**: the file `FACTS.md` of the rerun. It holds every number of the report with its source.
