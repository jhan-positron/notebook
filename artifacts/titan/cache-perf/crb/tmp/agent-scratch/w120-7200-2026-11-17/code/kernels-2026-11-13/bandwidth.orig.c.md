# `bandwidth.orig.c` explained

- Source file: `kernels-2026-11-13/bandwidth.orig.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 463 lines, 15917 bytes).
- sha256 of the source when this page was built: `61228754162c504e37faab3da7f423630ab66e32064ba5911455999347c2fe1b`.
- Role in the whole-chip test: Source of bw_old: the benchmark with the old read kernel, run in part A.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

## Short version: purpose

This C program is the benchmark before the change of 2026-11-13: each thread runs one kernel (read, write or copy) over its own buffer for at least a set time, and the program prints the total rate in GB/s. Its function `k_read` is the old read kernel: portable C code with 16 running sums, where each load is followed by an add.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Rerun**: the whole-chip read test of 2026-11-17, run after the memory speed was lowered from 8000 MT/s to 7200 MT/s.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Kernel**: one of the six inner loops of this benchmark: read, write, copy, asmread, asmwrite, asmcopy. It never means the Linux kernel.
- **Read kernel**: the inner loop of the benchmark that reads memory. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12. In this file it is the function `k_read`.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers. In this file it is the function `k_asmread`.
- **Load-only loop**: the new read kernel or asmread.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source. This file, bandwidth.orig.c, is the old source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process. The code calls it a repetition (`rep`). The option `--reps 3` gives 3 intervals per kernel.
- **Round**: in part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Pass, loop pass**: a pass is one call of a kernel. It goes once over the whole buffer of a thread. A loop pass is one execution of the loop body inside a kernel (128 B in `k_read`, 256 B in the asm kernels).
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Warm-up pass**: one pass that a thread runs before each timed interval. It is not timed.
- **GB, MiB**: GB = 1e9 bytes. MiB = 2^20 bytes (1048576 bytes). 256 MiB = 268435456 bytes.
- **Pin**: bind a thread to one CPU. Linux then runs the thread only on that CPU.
- **First touch**: the first write to the pages of a new buffer. Linux assigns the physical memory at that moment.
- **2 MiB pages, huge pages**: memory pages of 2 MiB, larger than the base pages of Linux. The option name `--no-thp` uses the Linux name "transparent huge pages" (THP).
- **Barrier**: an object of the POSIX thread library. A thread that calls `pthread_barrier_wait` waits until a set number of threads have called it. Then all of them continue together.
- **NEON**: the 128-bit vector instructions of Arm. A NEON register (`v0` to `v31`, written `q0` to `q31` when all 16 bytes are used) holds for example two 64-bit integers.
- **SVE**: Scalable Vector Extension, a second set of vector instructions of Arm. The processor fixes its vector length.
- **ldp q, stp q**: `ldp q` is the Arm instruction that loads two 16-byte vector registers (32 B). `stp q` is the Arm instruction that stores two 16-byte vector registers (32 B).
- **64-bit Arm (aarch64)**: the instruction set of CRB. The asm kernels exist only in a build for it.
- **ra.sh**: the script of part A. It starts bw_old and bw_new with 120 threads, one process per kernel, binary and round.
- **run_kernels.sh**: the script of 2026-11-13. It built bw_old and bw_new and wrote the machine code of their kernels to the file probe.txt.
- **objdump text**: the machine code of a binary, printed as assembly text by the tool objdump.
- **Stack check**: code in the machine code of `k_read` of bw_old that is not in the source. At the start of the function it copies a guard value to the stack. Before the return it compares the copy with the guard value. If the two differ, it calls `__stack_chk_fail`.
- **gcc**: the GNU C compiler. run_kernels.sh built bw_old and bw_new with its version 14.2.0.
- **taskset**: a Linux command. It starts a program that may run only on the CPUs of the given list.
- **diff**: a command that prints the lines in which two text files differ.
- **stat_k120.py, facts_data.py**: analysis scripts of the rerun. They read the interval rows that this program prints.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.

</details>

## Main flow

1. `main` sets the defaults and reads the arguments. In the whole-chip test ra.sh passes `--threads 120 --cpus 0-119 --bytes 256M --kernel K --reps 3 --min-ms 500`, with one kernel name K per process [Ref3] (lines 339-387).
2. `main` checks the arguments. The buffer size must be a multiple of 256 B (lines 388-399).
3. `main` creates a barrier for 121 threads (120 workers plus itself) and starts the 120 worker threads. Thread i gets CPU i (lines 401-413).
4. Each worker pins itself to its CPU, reserves a buffer of 256 MiB and writes every element once (first touch). None of this is timed (lines 299-306).
5. For each of the 3 repetitions, each worker runs one warm-up pass that is not timed and then waits at the barrier (lines 311-313).
6. All workers leave the barrier together. Each worker reads the clock, runs whole passes of the kernel over its buffer, and reads the clock after every pass. It stops after the first pass that ends 0.5 s or more after its start (lines 314-322).
7. For kernel `read`, each pass is one call of `k_read`: 16 running sums, one add per loaded 8-byte element, and one stored sum per pass (lines 138-148).
8. `main` waits until all workers have stopped. It divides the bytes of all threads by the longest thread time and prints one row with this rate (`aggregate_GBps`) (lines 424-446).
9. After the last repetition `main` prints a `best` row, waits for the end of the threads and exits (lines 448-463).

## Behavior a reader must know

- What is timed: the passes of the kernel and the clock reads between them (lines 314 to 320). Pinning, buffer allocation, first touch, the warm-up pass and the waits at the barrier are not timed.
- Stop rule (whole-pass stop): in the whole-chip test a thread reads the clock after every pass. It stops at the first end of a pass that lies 0.5 s or more after its own start. The threads stop at different times. Between the first stop and the last stop, fewer than 120 threads read memory.
- Rate: `aggregate_GBps` = bytes of all threads / longest thread time / 1e9 (GB = 1e9 bytes). It is never above the sum of the thread rates. Example: the first `read` row of bw_old in the result folder k120-T72A1-20261117T221209Z shows 467.83 GB/s. In the same row, 120 times the mean thread rate of 3.99 GB/s is about 479 GB/s [Ref5].
- Few passes per interval: in that example row the 120 threads completed 954 passes together, which is 7.95 passes per thread on average. The longest thread time was 0.5474 s [Ref5]. So one pass is about one eighth of the bytes that a thread counts in an interval.
- The old read kernel in the machine code of bw_old: one loop pass reads 128 B with 4 `ldp q` loads. It adds the loaded values to 8 vector registers with 8 `add` instructions [Ref1]. Per 256 B this is 8 loads and 16 vector adds, 32 instructions in total. The new read kernel of bw_new has the same 8 loads per 256 B and no vector add, 11 instructions in total [Ref1].
- `k_read` is portable C, so the compiler chooses the machine code. The statements about the machine code hold for the binary bw_old only (gcc 14.2.0, flags in [Ref1]).
- The sum that `k_read` returns is stored to a `volatile` variable once per pass over the buffer (line 264). This store is the reason why the compiler must keep the loads and the adds.
- Kernels that the whole-chip test runs from bw_old: all six (`read`, `write`, `copy`, `asmread`, `asmwrite`, `asmcopy`). ra.sh starts one process per kernel and round, which gives 12 processes of bw_old per call of ra.sh, each with 3 timed intervals [Ref3]. The rerun of 2026-11-17 has 3 result folders of part A with 12 processes of bw_old each [Ref5]. The comparison of the old with the new read kernel uses the kernel `read` of both binaries [Ref6].
- The six kernels in bw_old and in bw_new: the machine code of the three C kernels `k_read`, `k_write` and `k_copy` differs between the two binaries. The three asm kernels (`k_asmread`, `k_asmwrite` and `k_asmcopy`, written as assembly text) have the same instructions in both binaries, at other addresses [Ref1]. So a comparison of bw_old with bw_new for `write` or `copy` also compares different code. For an asm kernel it compares the same instructions of the kernel.
- Code around the kernels in the old and the new source: the new source is the file bandwidth.c of the same folder. The command `diff` on the two files shows every difference [Ref8]. In the new source the old `k_read`, `k_write` and `k_copy` (lines 138 to 160) and the old `pass` (lines 260 to 286) are text inside comments, and new versions of these four functions follow them. The comments of lines 135 to 137 and 257 to 259 are replaced. The variable `sink` (line 292) is removed, and the calls of `pass` in lines 312 and 318 have no `&sink`. One include line is new, and line 335 of the usage text differs. No other line of this file differs in the new source. So `now_s`, `pin_cpu`, `alloc_buf`, the three asm kernels, the clock reads and the stop rule of `worker`, and the whole function `main` with the rate computation are the same source text in both files. This is a statement about the source text. For bw_old and bw_new the objdump text of the build shows the six kernels only [Ref1].
- Which text of bandwidth.c was compared: the local file [Ref8]. Its sha256 is the value that the build of 18:32:18 UTC on 2026-11-13 recorded for bandwidth.c [Ref9]. The build of 18:12:22 UTC recorded another sha256 for bandwidth.c [Ref1]. The timed runs of 2026-11-13 followed that build. Both builds recorded the same sha256 for bw_new, and ra.sh runs bw_new only with this sha256 [Ref1] [Ref9] [Ref3]. So the machine code of bw_new is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref10]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs. None exists under the folder cache-perf.
- Order inside a process: buffer write (first touch), then for each repetition one warm-up pass and one timed interval. The code has no sleep between them: a thread only waits at the barrier for the other threads. ra.sh selects one kernel per process, so no kernel is timed after another kernel in the same process [Ref3].
- Build: run_kernels.sh built bw_old on 2026-11-13 with gcc 14.2.0 and the flags `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11` [Ref1] [Ref2]. ra.sh builds nothing. It checks the sha256 of bw_old and stops when the value differs [Ref3]. The value that ra.sh expects is the value that the build recorded for bw_old [Ref1]. Each of the 3 calls of ra.sh in the rerun recorded the same value for bw_old [Ref7]. So the objdump text of that build shows the machine code of bw_old that ran in part A. The binary bw_old is not in the local folders. Its sha256 value is known only from these records. The sha256 of this source file, computed on 2026-11-21, equals the value that the build recorded [Ref1].
- 2 MiB pages: the program asks for them with `madvise` and never checks the result. The header line of each process prints `thp=madvise`. This text shows the request only. The Linux setting for transparent huge pages was `always` at the start of each of the 3 calls of ra.sh [Ref7]. With `always`, Linux may use 2 MiB pages for a buffer without a request. Insufficient data: whether the buffers of part A lay on 2 MiB pages. A run of the same kernel with bwx12 would record it. bwx12 prints rows of the kind P, and a P row holds the page state of one buffer [Ref6].
- Main thread: the program does not pin it. ra.sh runs under `taskset -c 0-119`, so the main thread may run on any of the CPUs 0 to 119 [Ref3]. It waits at the barrier during every timed interval.

## Call sequence in the whole-chip test

- `ra.sh:one`: part A: starts one bw_old process per kernel and round
  - `main` (line 339): started by ra.sh: one process per kernel and round
    - `parse_cpus` (line 80): reads the list 0-119: 120 CPUs
    - `parse_bytes` (line 62): reads 256M: 268435456 bytes per thread
    - `worker` (line 288): 120 threads, each runs this function once
      - `pin_cpu` (line 107): thread i pins itself to CPU i
      - `alloc_buf` (line 118): reserves the 256 MiB buffer and asks for 2 MiB pages
      - `k_write` (line 150): first touch of the buffer, not timed
      - `pass` (line 260): warm-up pass before each interval, not timed
        - `k_read` (line 138): the selected kernel, here the old read kernel
      - `now_s` (line 55): clock read at the start of the timed interval
      - `pass` (line 260): timed passes, repeated until 0.5 s have passed
        - `k_read` (line 138): kernel read: the old read kernel
        - `k_write` (line 150): kernel write, in its own process
        - `k_copy` (line 156): kernel copy, in its own process
        - `k_asmread` (line 173): kernel asmread, in its own process
        - `k_asmwrite` (line 197): kernel asmwrite, in its own process
        - `k_asmcopy` (line 220): kernel asmcopy, in its own process
      - `now_s` (line 55): clock read after every pass
    - `main: rate loop` (line 420): waits at the barrier twice, then prints one row per interval

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `now_s` | 55-60 | Reads the monotonic clock of Linux and returns seconds. | - | yes |
| `parse_bytes` | 62-77 | Turns a size text such as 256M into bytes. | - | no |
| `parse_cpus` | 80-105 | Turns a CPU list such as 0-119 into the entries of cfg.cpus. | - | no |
| `pin_cpu` | 107-116 | Pins the calling thread to one CPU. | - | no |
| `alloc_buf` | 118-133 | Reserves one buffer on a 2 MiB boundary and asks Linux for 2 MiB pages. | - | no |
| `k_read` | 138-148 | The old read kernel: adds every 8-byte element of the buffer to one of 16 sums and returns the total. | - | yes |
| `k_write` | 150-154 | C write kernel: stores one value into every element. Also used, not timed, for the first touch. | - | yes |
| `k_copy` | 156-160 | C copy kernel: copies every element from one buffer to the other. | - | yes |
| `k_asmread` | 173-195 | Hand-written load-only loop: 8 ldp q loads per 256 B, loaded values not used. | - | yes |
| `k_asmwrite` | 197-218 | Hand-written store-only loop: 8 stp q stores per 256 B. | - | yes |
| `k_asmcopy` | 220-252 | Hand-written copy loop: 8 ldp q loads, then 8 stp q stores per 256 B. | - | yes |
| `pass` | 260-286 | Runs the selected kernel once over the buffer of a thread and returns the bytes to count. | `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite`, `k_asmcopy` | yes |
| `worker` | 288-327 | One thread: pins itself, writes its buffer, then per repetition runs a warm-up pass and times whole passes. | `pin_cpu`, `alloc_buf`, `k_write`, `pass`, `now_s` | yes |
| `usage` | 329-337 | Prints the list of options and ends the program with exit status 2. | - | no |
| `main` | 339-463 | Reads the arguments, starts the threads, and prints one rate row per timed interval. | `parse_cpus`, `parse_bytes`, `usage`, `worker` | no |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `kernels-2026-11-13/bandwidth.orig.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (463 lines, 15917 bytes, sha256 `61228754162c504e37faab3da7f423630ab66e32064ba5911455999347c2fe1b`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and include lines (lines 1 to 19)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Comment: starts the header comment of the file. It ends in line 8. |
| 2 | ` * bandwidth.c - multi-thread streaming bandwidth: read, write, copy.` | Comment: the name and the purpose of the program. It measures with several threads how fast memory is read, written and copied in address order (streaming). The comment still names `bandwidth.c`. This file is the benchmark source before the change of 2026-11-13, and `run_kernels.sh` built the binary `bw_old` from it [Ref2]. |
| 3 | ` *` | Comment: an empty line inside the header comment. |
| 4 | ` * Every thread owns its buffers (allocated and first-touched by that thread),` | Comment: each thread owns its buffers. The thread itself reserves them and writes them first (first touch). |
| 5 | ` * so timing contains no page faults. All threads start on a barrier, run` | Comment: so a timed interval holds no page fault. A page fault is the work that Linux does when a memory page is used for the first time. All threads start a timed interval together at a barrier (line 53). |
| 6 | ` * whole passes over their buffer until --min-ms has elapsed, and record` | Comment: each thread runs whole passes over its buffer until the time of the option `--min-ms` has passed. A pass is one run of a kernel over the whole buffer. |
| 7 | ` * bytes moved and their own elapsed time. GB means 1e9 bytes throughout.` | Comment: each thread records the bytes that it moved and the time that it measured itself. GB means 1e9 bytes everywhere in this program. |
| 8 | ` */` | Comment: the end of the header comment. |
| 9 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include line. This makes the Linux-only calls of the headers visible, for example `sched_setaffinity` and `CPU_SET` (lines 109 to 112). |
| 10 | `#include <pthread.h>` | Includes the header of the POSIX thread library. It gives the threads (`pthread_create`, `pthread_join`) and the barrier (`pthread_barrier_wait`). |
| 11 | `#include <sched.h>` | Includes the header for the CPU pinning: the type `cpu_set_t`, the macros `CPU_ZERO` and `CPU_SET`, and the call `sched_setaffinity`. |
| 12 | `#include <stdint.h>` | Includes the integer types of fixed size: `uint64_t` (64 bits), `uint8_t` (8 bits) and `uintptr_t` (an integer that can hold an address). |
| 13 | `#include <stdio.h>` | Includes the output functions `printf`, `fprintf`, `perror` and `fflush`. |
| 14 | `#include <stdlib.h>` | Includes `exit`, `calloc` and the functions that turn text into a number: `strtod`, `strtol`, `atoi` and `atof`. |
| 15 | `#include <string.h>` | Includes the text functions `strcmp` and `strtok`, and `memset`. |
| 16 | `#include <sys/mman.h>` | Includes `mmap` and `madvise`, the two Linux calls that `alloc_buf` uses for a buffer. |
| 17 | `#include <time.h>` | Includes `clock_gettime` and the type `struct timespec`. The function `now_s` reads the clock with them. |
| 18 | `#include <unistd.h>` | Includes `getpid`, which gives the process id. The worker uses it for the value that it stores (line 294). |

### Constants and the list of the kernels (lines 20 to 27)

| Line | Source | Explanation |
|---:|---|---|
| 20 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2 MiB (2097152 bytes), the size of one huge page. The expression shifts the number 2 left by 20 bits. `alloc_buf` aligns every buffer to this size (line 120, line 127). |
| 21 | `#define MAX_CPUS 1024` | `MAX_CPUS`: the CPU list holds at most 1024 entries (line 31, line 98). |
| 22 | `#define MAX_REPS 32` | `MAX_REPS`: at most 32 timed intervals per kernel (line 49, line 392). |
| 23 | `#define CHECK_BYTES (8UL << 20) /* clock is read after at least this many bytes */` | `CHECK_BYTES`: 8 MiB (8388608 bytes). Line 295 divides it by the buffer size. The result, or 1 when the result is 0 (line 297), is the number of passes between two clock reads. The comment says that the clock is read after at least this many bytes. For the bytes of the buffer this holds only when 8 MiB is a multiple of the buffer size, or when the buffer is larger than 8 MiB. For every other size the passes between two clock reads cover less than 8 MiB (line 295). |
| 25 | `enum kernel { K_READ, K_WRITE, K_COPY, K_ASMREAD, K_ASMWRITE, K_ASMCOPY, K_COUNT };` | The six kernels of the program, numbered 0 to 5. `K_COUNT` is 6, the number of kernels. A process runs its selected kernels in this order (loop of line 308). |
| 26 | `static const char *kernel_name[K_COUNT] = { "read", "write", "copy", "asmread", "asmwrite", "asmcopy" };` | `kernel_name`: the name of each kernel as text, in the order of line 25. It is the text that the first column of an output row shows (line 444, line 448). The option `--kernel` takes the same six names, and also `all` and `asmall` (lines 366 to 381). |

### Settings, per-thread data and the barrier (lines 28 to 54)

| Line | Source | Explanation |
|---:|---|---|
| 28 | `static struct {` | Starts the definition of `cfg`, the variable that holds the settings of the process. The definition ends in line 38. |
| 29 | `    int threads;` | `threads`: the number of worker threads (option `--threads`). |
| 30 | `    int ncpus;` | `ncpus`: the number of entries in the CPU list. It is 0 when no option `--cpus` was given. |
| 31 | `    int cpus[MAX_CPUS];` | `cpus`: the CPU list of the option `--cpus`, one CPU number per entry. |
| 32 | `    uint64_t bytes;` | `bytes`: the buffer size of each thread, in bytes (option `--bytes`). |
| 33 | `    int run[K_COUNT];` | `run`: one flag per kernel. `run[k]` is 1 when kernel `k` is selected (option `--kernel`). |
| 34 | `    double min_s;` | `min_s`: the minimum time of a timed interval, in seconds (option `--min-ms`). |
| 35 | `    int reps;` | `reps`: the number of timed intervals per kernel (option `--reps`). |
| 36 | `    int use_thp;` | `use_thp`: 1 when the program asks Linux for 2 MiB pages, 0 with the option `--no-thp` (line 130). |
| 37 | `    int per_thread; /* --per-thread: one line per thread with its CPU and best GB/s */` | `per_thread`: 1 with the option `--per-thread`. The comment says: one line per thread with its CPU and its best rate in GB/s. The comment is out of date. The code prints one line per thread and repetition, with the rate of that repetition (lines 452 to 456). |
| 38 | `} cfg = { .threads = 1, .min_s = 0.5, .reps = 3, .use_thp = 1 };` | Ends the definition and sets the defaults: 1 thread, a minimum time of 0.5 s per interval, 3 intervals per kernel, and a request for 2 MiB pages. Every other field starts at 0. |
| 40 | `struct result {` | Starts `struct result`: the result of one thread for one timed interval. |
| 41 | `    uint64_t bytes;` | `bytes`: the bytes that the thread counted in the interval. |
| 42 | `    double elapsed_s;` | `elapsed_s`: the time that the same thread measured for the interval, in seconds. |
| 43 | `};` | Ends `struct result`. |
| 45 | `struct thread {` | Starts `struct thread`: one entry per worker thread. |
| 46 | `    int idx;` | `idx`: the thread index, counted from 0. |
| 47 | `    int cpu;` | `cpu`: the CPU of the thread, or -1 when no CPU list was given (line 408). |
| 48 | `    uint64_t *a, *b;` | `a`, `b`: the addresses of the two buffers of the thread. Each buffer is an array of 8-byte elements. Only the copy kernels use `b` (line 303). |
| 49 | `    struct result res[K_COUNT][MAX_REPS];` | `res`: one result per kernel and interval: 6 kernels times at most 32 intervals. |
| 50 | `    pthread_t tid;` | `tid`: the handle of the thread. `pthread_create` fills it (line 409), and `pthread_join` uses it (line 461). |
| 51 | `};` | Ends `struct thread`. |
| 53 | `static pthread_barrier_t bar;` | `bar`: a barrier. A thread that calls `pthread_barrier_wait` on it waits until all worker threads and the main thread have called it. Then all of them continue together. Line 402 sets how many threads must arrive. |

### Function `now_s`: read the clock (lines 55 to 61)

| Line | Source | Explanation |
|---:|---|---|
| 55 | `static double now_s(void)` | Starts the function `now_s`. It reads the clock and returns the time in seconds. Every time value of the program comes from this function. The worker calls it at the start of a timed interval (line 314) and after the passes (line 319). |
| 56 | `{` | Opens the body of `now_s`. |
| 57 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 58 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | Reads `CLOCK_MONOTONIC` into `ts`. This is the Linux clock that only moves forward. A change of the date of the machine does not change it. It is the only clock that the file reads. |
| 59 | `    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;` | Returns the time in seconds as a `double`: the seconds plus the nanoseconds times 1e-9. |
| 60 | `}` | Ends the function `now_s`. |

### Function `parse_bytes`: read a size such as `256M` (lines 62 to 78)

| Line | Source | Explanation |
|---:|---|---|
| 62 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `256M` into a number of bytes. `main` calls it for the option `--bytes` (line 358). |
| 63 | `{` | Opens the body of `parse_bytes`. |
| 64 | `    char *end;` | `end`: will point to the first character after the number. |
| 65 | `    double v = strtod(s, &end);` | `strtod` reads a number from the start of the text `s` into `v`. The number may have a decimal point. `strtod` sets `end` to the first character that is not part of the number. |
| 66 | `    double mul = 1;` | `mul`: the factor of the suffix. It stays 1 when the text has no suffix. |
| 67 | `    switch (*end) {` | Looks at the character after the number. |
| 68 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | `k` or `K`: the factor is 1024 (2 to the power 10). `end++` steps over the suffix. |
| 69 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | `m` or `M`: the factor is 1048576 (2 to the power 20, which is 1 MiB). So `256M` gives 268435456 bytes (256 MiB). |
| 70 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | `g` or `G`: the factor is 1073741824 (2 to the power 30). |
| 71 | `    }` | Ends the `switch` of line 67. |
| 72 | `    if (end == s \|\| *end != '\0' \|\| v <= 0) {` | Tests three error cases. No number was read (`end == s`). Or other text follows the number and its suffix. Or the value is 0 or below. |
| 73 | `        fprintf(stderr, "bad size: %s\n", s);` | On an error: prints `bad size:` and the text to the error output. |
| 74 | `        exit(2);` | On an error: the program ends with exit status 2. |
| 75 | `    }` | Ends the `if` of line 72. |
| 76 | `    return (uint64_t)(v * mul);` | Returns the number times the factor as a whole number of bytes. A fraction of a byte is cut off. |
| 77 | `}` | Ends the function `parse_bytes`. |

### Function `parse_cpus`: read the CPU list (lines 79 to 106)

| Line | Source | Explanation |
|---:|---|---|
| 79 | `/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */` | Comment: three examples of a CPU list. `0-119` is a range. `0,2,4-7` is a list of numbers and ranges. `0-118:2` is a range with a step (the comment says stride): every second CPU from 0 to 118. |
| 80 | `static void parse_cpus(char *list)` | Starts the function `parse_cpus`. It reads the text of the option `--cpus` and appends every CPU number to `cfg.cpus`, in the order of the list. `0-119` gives the 120 entries 0, 1, 2 and so on up to 119. |
| 81 | `{` | Opens the body of `parse_cpus`. |
| 82 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Loop over the pieces of the list. `strtok` cuts the text at each comma and returns one piece per call. After the last piece it returns `NULL`, which ends the loop. |
| 83 | `        char *e, *e2;` | `e`, `e2`: each will point to the first character after a number that was read. |
| 84 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the piece (base 10) into `lo`. `hi` starts equal to `lo`, and `step` starts at 1. So a piece that is one number gives one CPU. |
| 85 | `        if (e != tok && *e == '-') {` | Tests whether a number was read and a hyphen follows it. The piece is then a range. |
| 86 | `            hi = strtol(e + 1, &e2, 10);` | Reads the number after the hyphen into `hi`, the last CPU of the range. |
| 87 | `            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */` | When no digit followed the hyphen (`e2 == e + 1`), `e` is set back to `tok`. The test of line 93 then rejects the piece. In every other case `e` moves to the first character after the second number. The comment gives the example `0-`, a range without an upper bound. |
| 88 | `            if (e != tok && *e == ':') {` | Tests whether the range is valid so far and a colon follows it. The piece then has a step. |
| 89 | `                step = strtol(e + 1, &e2, 10);` | Reads the number after the colon into `step`. |
| 90 | `                e = e2 == e + 1 ? tok : e2;` | The same rule as in line 87: when no digit followed the colon, `e` is set back to `tok`. |
| 91 | `            }` | Ends the `if` of line 88. |
| 92 | `        }` | Ends the `if` of line 85. |
| 93 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| hi >= CPU_SETSIZE \|\| step < 1) {` | Tests the piece. It is bad in each of these cases: no number was read, or line 87 or line 90 set `e` back (`e == tok`), or other text follows the numbers, or `lo` is below 0, or `hi` is below `lo`, or `hi` is `CPU_SETSIZE` or above (the number of CPUs that the type `cpu_set_t` can hold), or `step` is below 1. |
| 94 | `            fprintf(stderr, "bad cpu list: %s\n", tok);` | On a bad piece: prints `bad cpu list:` and the piece to the error output. |
| 95 | `            exit(2);` | On a bad piece: the program ends with exit status 2. |
| 96 | `        }` | Ends the `if` of line 93. |
| 97 | `        for (long c = lo; c <= hi; c += step) {` | Loop over the CPU numbers of the piece: from `lo` to `hi` in steps of `step`. |
| 98 | `            if (cfg.ncpus == MAX_CPUS) {` | Tests whether the list already holds 1024 entries (`MAX_CPUS`). |
| 99 | `                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);` | When the list is full: prints `bad cpu list: more than 1024 cpus` to the error output. |
| 100 | `                exit(2);` | When the list is full: the program ends with exit status 2. |
| 101 | `            }` | Ends the `if` of line 98. |
| 102 | `            cfg.cpus[cfg.ncpus++] = (int)c;` | Appends the CPU number to `cfg.cpus` and adds 1 to the count `cfg.ncpus`. |
| 103 | `        }` | Ends the loop of line 97. |
| 104 | `    }` | Ends the loop of line 82. |
| 105 | `}` | Ends the function `parse_cpus`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 107 to 117)

| Line | Source | Explanation |
|---:|---|---|
| 107 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It pins the calling thread to the CPU with the number `cpu`: Linux then runs the thread on that CPU only. |
| 108 | `{` | Opens the body of `pin_cpu`. |
| 109 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 110 | `    CPU_ZERO(&set);` | Empties the set. |
| 111 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 112 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. So only this thread is pinned. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 113 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 114 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 115 | `    }` | Ends the `if` of line 112. |
| 116 | `}` | Ends the function `pin_cpu`. |

### Function `alloc_buf`: one buffer, aligned for huge pages (lines 118 to 134)

| Line | Source | Explanation |
|---:|---|---|
| 118 | `static uint64_t *alloc_buf(uint64_t bytes)` | Starts the function `alloc_buf`. It reserves a buffer of at least `bytes` bytes and returns its address. The buffer starts at a multiple of 2 MiB. |
| 119 | `{` | Opens the body of `alloc_buf`. |
| 120 | `    size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | `len`: `bytes` rounded up to the next multiple of `HUGE_BYTES` (2 MiB). The expression adds `HUGE_BYTES - 1` and then clears the low bits. This gives the right value when `HUGE_BYTES` is a power of two. 256 MiB stays 256 MiB. |
| 121 | `    uint8_t *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ \| PROT_WRITE,` | `mmap` asks Linux for `len + HUGE_BYTES` bytes of new memory. The extra `HUGE_BYTES` bytes make it possible to move the start to an aligned address later (line 127). `NULL`: Linux chooses the address. `PROT_READ \| PROT_WRITE`: the program may read and write the memory. |
| 122 | `                        MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | Continues the call of line 121. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. `mmap` reserves addresses only. Linux assigns the physical memory when a page is first written (line 302). |
| 123 | `    if (raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 124 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 125 | `        exit(2);` | On failure: the program ends with exit status 2. |
| 126 | `    }` | Ends the `if` of line 123. |
| 127 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the first address in the reserved range that is a multiple of 2 MiB. The buffer starts there. The expression rounds the address `raw` up in the same way as line 120 rounds the size. |
| 128 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: `MADV_NOHUGEPAGE` matters on a machine where the Linux setting for transparent huge pages (THP) is `always`. |
| 129 | `     * would still get 2 MiB pages. */` | Comment: without it, the buffers of a run with `--no-thp` would still get 2 MiB pages. |
| 130 | `    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` with `MADV_HUGEPAGE` asks Linux to use 2 MiB pages for the `len` bytes that start at `p`. With the option `--no-thp` it passes `MADV_NOHUGEPAGE`, which forbids them. `ra.sh` does not pass `--no-thp`, so the whole-chip test asks for 2 MiB pages [Ref3]. |
| 131 | `        perror("madvise (continuing)");` | A failed `madvise` only prints a message that starts with `madvise (continuing)`. The program goes on. It never checks whether the buffer in fact lies on 2 MiB pages. |
| 132 | `    return (uint64_t *)p;` | Returns the aligned address as a pointer to 8-byte elements. The program never releases the buffer. |
| 133 | `}` | Ends the function `alloc_buf`. |

### Function `k_read`: the old read kernel (16 running sums, one add per load) (lines 135 to 149)

| Line | Source | Explanation |
|---:|---|---|
| 135 | `/* 16 independent accumulators keep the loop load-bound: on 128-bit NEON gcc` | Comment: the intent of the 16 sums (the comment calls them accumulators). An add to one sum does not wait for an add to another sum. So the loads, not the adds, are meant to set the speed of the loop. This file holds no measurement of that. |
| 136 | ` * folds them into 8 vector chains, enough to hide a 2-cycle add latency;` | Comment: with NEON, the 128-bit vector instructions of Arm, gcc makes 8 chains of vector adds from the 16 sums. The comment says that this is enough for an add that takes 2 cycles: the adds then do not limit the speed of the loop. The count of 8 holds for `bw_old`: its machine code has 8 vector registers for the sums, each with two 64-bit sums [Ref1]. |
| 137 | ` * on AVX-512 they become 2 zmm chains. */` | Comment: with AVX-512 the sums become 2 chains in `zmm` registers. This sentence is about x86 processors. It does not apply to CRB. |
| 138 | `__attribute__((noinline)) static uint64_t k_read(const uint64_t *a, size_t n)` | Starts the function `k_read`, the old read kernel. It adds every 8-byte element of the buffer to one of 16 sums and returns the total. `noinline` forbids the compiler to merge the kernel into its caller. So the binary holds `k_read` as a function of its own, and `run_kernels.sh` printed its machine code by name [Ref1]. `a` is the buffer of the thread. `n` is the number of 8-byte elements in the buffer (line 291). |
| 139 | `{` | Opens the body of `k_read`. |
| 140 | `    uint64_t s[16] = { 0 };` | `s`: 16 running sums of 64 bits each, all 0 at the start. In `bw_old` the compiler keeps them in the 8 vector registers `v24` to `v31` during the loop. Each register holds two of the sums [Ref1]. |
| 141 | `    for (size_t i = 0; i < n; i += 16)` | The outer loop. One loop pass handles 16 elements, which is 128 B. A buffer of 256 MiB needs 2097152 loop passes. `main` accepts only buffer sizes that are a multiple of 256 B (line 392), so the loop ends exactly at the end of the buffer. |
| 142 | `        for (int j = 0; j < 16; j++)` | The inner loop of the source: 16 steps per outer loop pass, one step per sum. The machine code of `bw_old` has no inner loop. gcc turned its 16 loads and 16 adds into vector instructions [Ref1]. One loop pass of the machine code is one loop pass of the outer loop of the source (128 B). |
| 143 | `            s[j] += a[i + j];` | Loads one 8-byte element and adds it to its own sum. Every loaded value is used. One loop pass of the machine code of `bw_old` has 16 instructions [Ref1]. 4 are `ldp q` loads: each one loads two 16-byte vector registers (32 B). 8 are vector `add` instructions: each one adds a loaded register (two 64-bit values) to its sum register. 2 are scalar `add` instructions: the loop counter plus 1 and the buffer pointer plus 128 B. The last 2 are `cmp` and a conditional branch back to the first load. Per 256 B this is 8 `ldp q` loads and 16 vector adds, 32 instructions in total. The new read kernel of `bw_new` has the same 8 `ldp q` loads per 256 B and no vector add, 11 instructions in total [Ref1]. |
| 144 | `    uint64_t sum = 0;` | After the loop: `sum` will hold the total of the 16 sums. |
| 145 | `    for (int j = 0; j < 16; j++)` | Loop over the 16 sums. It runs once per call of `k_read`, so once per pass over the buffer. |
| 146 | `        sum += s[j];` | Adds one of the 16 sums to `sum`. |
| 147 | `    return sum;` | Returns the total. The caller stores it once per pass (line 264). In `bw_old` the code outside the loop also sets the sums to 0 and stores them to the stack. It also holds a stack check that is not in the source (a call of `__stack_chk_fail`) [Ref1]. |
| 148 | `}` | Ends the function `k_read`. |

### Function `k_write`: the C write kernel, also used for the first touch (lines 150 to 155)

| Line | Source | Explanation |
|---:|---|---|
| 150 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_write`, the C write kernel. It stores the value `v` into each of the `n` elements of the buffer `a`. The worker also calls it once per buffer for the first touch (line 302, line 305). `noinline` keeps it a function of its own, as in line 138. |
| 151 | `{` | Opens the body of `k_write`. |
| 152 | `    for (size_t i = 0; i < n; i++)` | Loop over the `n` elements. One step of the source handles one 8-byte element. |
| 153 | `        a[i] = v;` | Stores `v` into element `i`. In `bw_old` gcc made an SVE loop from this loop, with one `st1d` vector store per loop pass [Ref1]. The objdump text does not show the vector length. So it does not show how many bytes one loop pass writes. |
| 154 | `}` | Ends the function `k_write`. |

### Function `k_copy`: the C copy kernel (lines 156 to 161)

| Line | Source | Explanation |
|---:|---|---|
| 156 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_copy`, the C copy kernel. It copies `n` elements from `s` to `d`. `restrict` tells the compiler that the two buffers do not overlap. |
| 157 | `{` | Opens the body of `k_copy`. |
| 158 | `    for (size_t i = 0; i < n; i++)` | Loop over the `n` elements. One step of the source handles one 8-byte element. |
| 159 | `        d[i] = s[i];` | Loads element `i` of `s` and stores it to element `i` of `d`. In `bw_old` gcc made an SVE loop from this loop, with one `ld1d` vector load and one `st1d` vector store per loop pass [Ref1]. The objdump text does not show the vector length. So it does not show how many bytes one loop pass copies. |
| 160 | `}` | Ends the function `k_copy`. |

### The asm kernels: comment and the test for 64-bit Arm (lines 162 to 172)

| Line | Source | Explanation |
|---:|---|---|
| 162 | `/*` | Comment: starts the comment on the three asm kernels. It ends in line 169. |
| 163 | ` * asm kernels: the whole hot loop is one inline-asm block, so the compiler` | Comment: in an asm kernel the whole loop is one block of assembly text inside a C function (inline asm). The compiler copies the loop. It only puts a register in the place of each name such as `%[p]` [Ref1]. |
| 164 | ` * cannot add arithmetic, reorder, or drop anything. Each iteration moves` | Comment: so the compiler cannot add arithmetic, change the order or remove an instruction. The next sentence of the comment starts here: each loop pass (iteration) moves 256 B. |
| 165 | ` * 256 B with 8 ldp/stp of q registers (16 B each). The loop body is:` | Comment: the 256 B are moved with 8 `ldp` or `stp` instructions on `q` registers of 16 B each. `ldp q` loads two such registers (32 B), and `stp q` stores two (32 B). |
| 166 | ` * 8 x ldp or stp, add, cmp, b.lo. Callers guarantee n * 8 is a multiple of` | Comment: the loop body is 8 `ldp` or `stp`, then `add`, `cmp` and the branch `b.lo`. This fits `k_asmread` and `k_asmwrite`. `k_asmcopy` has 8 `ldp`, 8 `stp` and 2 `add` (lines 227 to 244). The callers guarantee that `n * 8` bytes is a multiple of 256 and not 0. `main` checks this (line 392). |
| 167 | ` * 256 and non-zero. v8-v15 are callee-saved in AAPCS64: naming them as` | Comment: `v8` to `v15` are callee-saved in AAPCS64, the calling rules of 64-bit Arm. These rules say that a function must keep the lower halves (`d8` to `d15`) of the registers `v8` to `v15` for its caller. |
| 168 | ` * clobbers makes gcc save d8-d15 once per call, which is outside the loop.` | Comment: the asm blocks name these registers as changed (as clobbers, line 193). So the compiler saves and restores `d8` to `d15` once per call, outside the loop. The objdump text of `k_asmread` and `k_asmcopy` shows this [Ref1]. |
| 169 | ` */` | Comment: the end of the comment on the asm kernels. |
| 170 | `#if defined(__aarch64__)` | Compiles lines 171 to 252 only for 64-bit Arm (AArch64). The compiler defines `__aarch64__` for that instruction set. |
| 171 | `#define HAVE_ASM_KERNELS 1` | `HAVE_ASM_KERNELS` is 1 when the three asm kernels exist. Line 272 and line 394 test it. |

### Function `k_asmread`: the hand-written load-only loop (lines 173 to 196)

| Line | Source | Explanation |
|---:|---|---|
| 173 | `__attribute__((noinline)) static void k_asmread(const uint64_t *a, size_t n)` | Starts the function `k_asmread`, the hand-written load-only loop. `a` is the buffer, and `n` is its number of 8-byte elements. The function returns nothing. |
| 174 | `{` | Opens the body of `k_asmread`. |
| 175 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at the first element of the buffer. |
| 176 | `    const uint64_t *end = a + n;` | `end`: the address directly after the last element. |
| 177 | `    __asm__ volatile(` | Starts the asm statement: the assembly text (lines 178 to 189) and its three operand lists (lines 190 to 194). `volatile` forbids the compiler to remove the statement. |
| 178 | `        "1:\n\t"` | The label `1`: the start of the loop. The characters `\n\t` end each line of the assembly text with a line break and a tab. |
| 179 | `        "ldp q0, q1, [%[p]]\n\t"` | `ldp` loads 32 B from the address in `p` into the two 16-byte vector registers `q0` and `q1`. The compiler puts the register that holds `p` in the place of `%[p]`. |
| 180 | `        "ldp q2, q3, [%[p], #32]\n\t"` | Loads the 32 B at the address `p` plus 32 into `q2` and `q3`. |
| 181 | `        "ldp q4, q5, [%[p], #64]\n\t"` | Loads the 32 B at `p` plus 64 into `q4` and `q5`. |
| 182 | `        "ldp q6, q7, [%[p], #96]\n\t"` | Loads the 32 B at `p` plus 96 into `q6` and `q7`. |
| 183 | `        "ldp q8, q9, [%[p], #128]\n\t"` | Loads the 32 B at `p` plus 128 into `q8` and `q9`. |
| 184 | `        "ldp q10, q11, [%[p], #160]\n\t"` | Loads the 32 B at `p` plus 160 into `q10` and `q11`. |
| 185 | `        "ldp q12, q13, [%[p], #192]\n\t"` | Loads the 32 B at `p` plus 192 into `q12` and `q13`. |
| 186 | `        "ldp q14, q15, [%[p], #224]\n\t"` | Loads the 32 B at `p` plus 224 into `q14` and `q15`. The 8 loads of lines 179 to 186 read 256 B, each byte once. The loaded values are never used. The next loop pass overwrites them. |
| 187 | `        "add %[p], %[p], #256\n\t"` | `add` moves the pointer forward by 256 B. |
| 188 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the pointer with `end` and sets the condition flags. |
| 189 | `        "b.lo 1b\n\t"` | `b.lo 1b` jumps back to the label `1` (line 178) while the pointer is below `end`. So one loop pass is 11 instructions per 256 B: 8 loads, `add`, `cmp` and the branch. The objdump text of `bw_old` shows the same 11 instructions [Ref1]. |
| 190 | `        : [p] "+r"(p)` | First operand list, the outputs: `p` is read and changed in a register (`+r`). In the assembly text its name is `%[p]`. |
| 191 | `        : [end] "r"(end)` | Second list, the inputs: `end` is read in a register (`r`). |
| 192 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | Third list: what the text changes or accesses without an operand. This line names the registers `v0` to `v7`. `v0` and `q0` are two names of the same 16-byte register. |
| 193 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the list: the registers `v8` to `v15`. The compiler saves the lower halves of these 8 registers once per call (lines 167 to 168). |
| 194 | `          "memory", "cc");` | Ends the list and the asm statement. `memory`: the text accesses memory that no operand names. `cc`: the text changes the condition flags. |
| 195 | `}` | Ends the function `k_asmread`. |

### Function `k_asmwrite`: the hand-written store-only loop (lines 197 to 219)

| Line | Source | Explanation |
|---:|---|---|
| 197 | `__attribute__((noinline)) static void k_asmwrite(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_asmwrite`, the hand-written store-only loop. It stores the value `v` into all `n` elements of the buffer `a`. |
| 198 | `{` | Opens the body of `k_asmwrite`. |
| 199 | `    uint64_t *p = a;` | `p`: the write pointer. It starts at the first element of the buffer. |
| 200 | `    const uint64_t *end = a + n;` | `end`: the address directly after the last element. |
| 201 | `    __asm__ volatile(` | Starts the asm statement: the assembly text and its operand lists, as in line 177. |
| 202 | `        "dup v0.2d, %[v]\n\t"` | `dup` fills the register `v0` with two copies of the 64-bit value `v`. It runs once, before the loop. |
| 203 | `        "1:\n\t"` | The label `1`: the start of the loop. |
| 204 | `        "stp q0, q0, [%[p]]\n\t"` | `stp` stores the register `q0` twice, which is 32 B, to the address in `p`. |
| 205 | `        "stp q0, q0, [%[p], #32]\n\t"` | Stores `q0` twice (32 B) to the address `p` plus 32. |
| 206 | `        "stp q0, q0, [%[p], #64]\n\t"` | Stores `q0` twice (32 B) to `p` plus 64. |
| 207 | `        "stp q0, q0, [%[p], #96]\n\t"` | Stores `q0` twice (32 B) to `p` plus 96. |
| 208 | `        "stp q0, q0, [%[p], #128]\n\t"` | Stores `q0` twice (32 B) to `p` plus 128. |
| 209 | `        "stp q0, q0, [%[p], #160]\n\t"` | Stores `q0` twice (32 B) to `p` plus 160. |
| 210 | `        "stp q0, q0, [%[p], #192]\n\t"` | Stores `q0` twice (32 B) to `p` plus 192. |
| 211 | `        "stp q0, q0, [%[p], #224]\n\t"` | Stores `q0` twice (32 B) to `p` plus 224. The 8 stores of lines 204 to 211 write 256 B, each byte once. |
| 212 | `        "add %[p], %[p], #256\n\t"` | `add` moves the pointer forward by 256 B. |
| 213 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the pointer with `end`. |
| 214 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the pointer is below `end`. One loop pass is 11 instructions per 256 B: 8 stores, `add`, `cmp` and the branch. |
| 215 | `        : [p] "+r"(p)` | The outputs: `p` is read and changed in a register. |
| 216 | `        : [end] "r"(end), [v] "r"(v)` | The inputs: `end` and `v` are read in registers. |
| 217 | `        : "v0", "memory", "cc");` | What the text changes without an operand: the register `v0`, memory and the condition flags. This ends the asm statement. |
| 218 | `}` | Ends the function `k_asmwrite`. |

### Function `k_asmcopy`: the hand-written copy loop (lines 220 to 256)

| Line | Source | Explanation |
|---:|---|---|
| 220 | `__attribute__((noinline)) static void k_asmcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy`, the hand-written copy loop. It copies `n` elements from `s` to `d`. `restrict` tells the compiler that the two buffers do not overlap. |
| 221 | `{` | Opens the body of `k_asmcopy`. |
| 222 | `    uint64_t *dp = d;` | `dp`: the write pointer. It starts at the first element of `d`. |
| 223 | `    const uint64_t *sp = s;` | `sp`: the read pointer. It starts at the first element of `s`. |
| 224 | `    const uint64_t *end = s + n;` | `end`: the address directly after the last element of `s`. |
| 225 | `    __asm__ volatile(` | Starts the asm statement: the assembly text and its operand lists, as in line 177. |
| 226 | `        "1:\n\t"` | The label `1`: the start of the loop. |
| 227 | `        "ldp q0, q1, [%[s]]\n\t"` | `ldp` loads 32 B from the address in the read pointer into `q0` and `q1`. In the assembly text the read pointer has the name `%[s]`. |
| 228 | `        "ldp q2, q3, [%[s], #32]\n\t"` | Loads the 32 B at the read pointer plus 32 into `q2` and `q3`. |
| 229 | `        "ldp q4, q5, [%[s], #64]\n\t"` | Loads the 32 B at the read pointer plus 64 into `q4` and `q5`. |
| 230 | `        "ldp q6, q7, [%[s], #96]\n\t"` | Loads the 32 B at the read pointer plus 96 into `q6` and `q7`. |
| 231 | `        "ldp q8, q9, [%[s], #128]\n\t"` | Loads the 32 B at the read pointer plus 128 into `q8` and `q9`. |
| 232 | `        "ldp q10, q11, [%[s], #160]\n\t"` | Loads the 32 B at the read pointer plus 160 into `q10` and `q11`. |
| 233 | `        "ldp q12, q13, [%[s], #192]\n\t"` | Loads the 32 B at the read pointer plus 192 into `q12` and `q13`. |
| 234 | `        "ldp q14, q15, [%[s], #224]\n\t"` | Loads the 32 B at the read pointer plus 224 into `q14` and `q15`. The 8 loads of lines 227 to 234 read 256 B. All of them come before the first store. |
| 235 | `        "stp q0, q1, [%[d]]\n\t"` | `stp` stores `q0` and `q1` (32 B) to the address in the write pointer. In the assembly text the write pointer has the name `%[d]`. |
| 236 | `        "stp q2, q3, [%[d], #32]\n\t"` | Stores `q2` and `q3` to the write pointer plus 32. |
| 237 | `        "stp q4, q5, [%[d], #64]\n\t"` | Stores `q4` and `q5` to the write pointer plus 64. |
| 238 | `        "stp q6, q7, [%[d], #96]\n\t"` | Stores `q6` and `q7` to the write pointer plus 96. |
| 239 | `        "stp q8, q9, [%[d], #128]\n\t"` | Stores `q8` and `q9` to the write pointer plus 128. |
| 240 | `        "stp q10, q11, [%[d], #160]\n\t"` | Stores `q10` and `q11` to the write pointer plus 160. |
| 241 | `        "stp q12, q13, [%[d], #192]\n\t"` | Stores `q12` and `q13` to the write pointer plus 192. |
| 242 | `        "stp q14, q15, [%[d], #224]\n\t"` | Stores `q14` and `q15` to the write pointer plus 224. The 8 stores of lines 235 to 242 write the 256 B that the 8 loads read. |
| 243 | `        "add %[s], %[s], #256\n\t"` | `add` moves the read pointer forward by 256 B. |
| 244 | `        "add %[d], %[d], #256\n\t"` | `add` moves the write pointer forward by 256 B. |
| 245 | `        "cmp %[s], %[end]\n\t"` | `cmp` compares the read pointer with `end`. |
| 246 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the read pointer is below `end`. One loop pass is 20 instructions per 256 B: 8 loads, 8 stores, 2 `add`, `cmp` and the branch. |
| 247 | `        : [s] "+r"(sp), [d] "+r"(dp)` | The outputs: the two pointers `sp` and `dp` are read and changed in registers. In the assembly text their names are `%[s]` and `%[d]`. |
| 248 | `        : [end] "r"(end)` | The input: `end` is read in a register. |
| 249 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | What the text changes without an operand. This line names the registers `v0` to `v7`. |
| 250 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the list: the registers `v8` to `v15`. |
| 251 | `          "memory", "cc");` | Ends the list and the asm statement: memory and the condition flags. |
| 252 | `}` | Ends the function `k_asmcopy`. |
| 253 | `#else` | The other case of the `#if` of line 170: a processor that is not 64-bit Arm. The three asm kernels are then not compiled. |
| 254 | `#define HAVE_ASM_KERNELS 0` | `HAVE_ASM_KERNELS` is then 0, and `main` refuses to run the asm kernels (line 394). |
| 255 | `#endif` | Ends the `#if` of line 170. |

### Function `pass`: one pass of the kernel `k` over the buffer (lines 257 to 287)

| Line | Source | Explanation |
|---:|---|---|
| 257 | `/* One pass over the thread's buffer; returns bytes moved. The sink is per` | Comment: `pass` makes one pass over the buffer of the thread and returns the bytes moved. The sink is the variable that receives the sum of the read kernel. The sentence about the sink starts here. |
| 258 | ` * thread (on its stack) so the read kernels of 120 threads do not all store` | Comment: each thread has its own sink, on its stack (line 292). |
| 259 | ` * to one shared cache line. */` | Comment: so the read kernels of 120 threads do not all store to one shared cache line. |
| 260 | `static uint64_t pass(enum kernel k, struct thread *t, size_t n, uint64_t v, volatile uint64_t *sink)` | Starts the function `pass`. It runs the kernel `k` once over the whole buffer of thread `t`. It returns the number of bytes that the caller counts for this pass. `n` is the number of 8-byte elements. `v` is the value for the write kernels. `sink` points to a variable on the stack of the calling thread (line 292). |
| 261 | `{` | Opens the body of `pass`. |
| 262 | `    switch (k) {` | Chooses the kernel by the value of `k`. |
| 263 | `    case K_READ:` | The case of the kernel `read`. |
| 264 | `        *sink = k_read(t->a, n);` | Calls `k_read`, the old read kernel, on buffer `a` and stores the returned sum to the variable that `sink` points to. That variable is `volatile`, so the compiler must do this store. It therefore cannot remove the sum, the adds or the loads. This is one 8-byte store per pass over the buffer. |
| 265 | `        return cfg.bytes;` | The pass counts `cfg.bytes`, the buffer size, once. It is 268435456 bytes in the whole-chip test [Ref3]. The count is the size that the kernel was asked to read. Nothing is counted inside the kernel. |
| 266 | `    case K_WRITE:` | The case of the kernel `write`. |
| 267 | `        k_write(t->a, n, v);` | Fills buffer `a` with the value `v` (`k_write`). |
| 268 | `        return cfg.bytes;` | The pass counts the buffer size once. |
| 269 | `    case K_COPY:` | The case of the kernel `copy`. |
| 270 | `        k_copy(t->b, t->a, n);` | Copies buffer `a` to buffer `b` (`k_copy`). |
| 271 | `        return 2 * cfg.bytes;` | The pass counts the buffer size twice: the bytes read plus the bytes written. |
| 272 | `#if HAVE_ASM_KERNELS` | Compiles lines 273 to 281 only when the asm kernels exist (`HAVE_ASM_KERNELS` is 1, on 64-bit Arm). |
| 273 | `    case K_ASMREAD:` | The case of the kernel `asmread`. |
| 274 | `        k_asmread(t->a, n);` | Calls `k_asmread` on buffer `a`. `k_asmread` returns no value, so nothing is stored to `sink`. |
| 275 | `        return cfg.bytes;` | The pass counts the buffer size once. |
| 276 | `    case K_ASMWRITE:` | The case of the kernel `asmwrite`. |
| 277 | `        k_asmwrite(t->a, n, v);` | Fills buffer `a` with the value `v`, with the hand-written loop (`k_asmwrite`). |
| 278 | `        return cfg.bytes;` | The pass counts the buffer size once, as for `write`. |
| 279 | `    case K_ASMCOPY:` | The case of the kernel `asmcopy`. |
| 280 | `        k_asmcopy(t->b, t->a, n);` | Copies buffer `a` to buffer `b`, with the hand-written loop (`k_asmcopy`). |
| 281 | `        return 2 * cfg.bytes;` | The pass counts the buffer size twice, as for `copy`. |
| 282 | `#endif` | Ends the `#if` of line 272. |
| 283 | `    default:` | The case of every other value of `k`. |
| 284 | `        return 0;` | Counts 0 bytes. This line is reached only for an asm kernel in a build without the asm kernels. `main` stops such a run before it creates the threads (line 394). |
| 285 | `    }` | Ends the `switch` of line 262. |
| 286 | `}` | Ends the function `pass`. |

### Function `worker`: start values, pinning and first touch of the buffers (lines 288 to 307)

| Line | Source | Explanation |
|---:|---|---|
| 288 | `static void *worker(void *arg)` | Starts the function `worker`. Each thread that `main` creates (line 409) runs it once. |
| 289 | `{` | Opens the body of `worker`. |
| 290 | `    struct thread *t = arg;` | `t`: the entry of this thread in the thread table. `main` filled its index and its CPU (lines 407 to 408). |
| 291 | `    size_t n = cfg.bytes / 8;` | `n`: the number of 8-byte elements in the buffer. It is 33554432 for a buffer of 256 MiB. |
| 292 | `    volatile uint64_t sink;` | `sink`: the variable that receives the sum of `k_read` (line 264). It lies on the stack of this thread. So the 120 threads do not store to one shared cache line. |
| 293 | `    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */` | Comment: the store value is known only when the program runs, and its 8 bytes are not all equal. So the compiler cannot turn the write loop into a call of `memset`, the library function that fills memory with one byte value. |
| 294 | `    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;` | `v`: the value that the write kernels store. It is the process id plus the thread index plus 1, times a fixed 64-bit constant. So the compiler does not know it. The read kernels do not use it. |
| 295 | `    uint64_t passes_per_check = CHECK_BYTES / cfg.bytes;` | `passes_per_check`: the number of passes between two clock reads. It is 8 MiB (`CHECK_BYTES`) divided by the buffer size, rounded down. A buffer of 3 MiB, for example, gives 2 passes, which is 6 MiB. So for a buffer below 8 MiB that does not divide 8 MiB, the clock is read after less than 8 MiB. The comment of line 23 says at least 8 MiB. |
| 296 | `    if (passes_per_check == 0)` | Tests whether the division gave 0. That is the case for every buffer above 8 MiB. |
| 297 | `        passes_per_check = 1;` | The value is then 1. For a buffer of 256 MiB the thread therefore reads the clock after every pass. |
| 299 | `    if (cfg.ncpus)` | Tests whether a CPU list was given (option `--cpus`). |
| 300 | `        pin_cpu(t->cpu);` | If so, the thread pins itself to its CPU (`pin_cpu`). In the whole-chip test thread i runs on CPU i (line 408) [Ref3]. The thread does this before it reserves its buffer. |
| 301 | `    t->a = alloc_buf(cfg.bytes);` | Reserves buffer `a` with `alloc_buf`: `cfg.bytes` bytes that start at a multiple of 2 MiB. |
| 302 | `    k_write(t->a, n, v); /* first touch by this thread */` | Writes `v` into every element of buffer `a` with `k_write`. This write is the first touch: Linux assigns the physical memory of the buffer now, while the thread already runs on its CPU. It is not timed. The comment says: first touch by this thread. |
| 303 | `    if (cfg.run[K_COPY] \|\| cfg.run[K_ASMCOPY]) {` | Tests whether `copy` or `asmcopy` is selected. Only these two kernels use a second buffer. |
| 304 | `        t->b = alloc_buf(cfg.bytes);` | If so, the thread reserves the second buffer `b` of the same size. |
| 305 | `        k_write(t->b, n, v);` | Writes `v` into every element of `b` (first touch, not timed). In the whole-chip test a process of the read kernel has one buffer of 256 MiB per thread [Ref3]. |
| 306 | `    }` | Ends the `if` of line 303. |

### Function `worker`: the warm-up pass, the timed interval and the stop rule (lines 308 to 328)

| Line | Source | Explanation |
|---:|---|---|
| 308 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the six kernels in the order of line 25. |
| 309 | `        if (!cfg.run[k])` | Tests whether kernel `k` is selected. |
| 310 | `            continue;` | A kernel that is not selected is skipped. `ra.sh` selects one kernel per process. So in the whole-chip test no kernel is timed after another kernel in the same process [Ref3]. |
| 311 | `        for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions of this kernel. Each repetition is one timed interval. The whole-chip test has 3 per process [Ref3]. |
| 312 | `            pass(k, t, n, v, &sink); /* warm-up */` | The warm-up: one whole pass of the same kernel over the buffer. It runs before every timed interval, not only before the first one. It is not timed, and its byte count is dropped. |
| 313 | `            pthread_barrier_wait(&bar);` | Waits at the barrier until all workers and the main thread (line 425) have arrived: 120 workers in the whole-chip test [Ref3]. A thread that arrives early waits here and reads no memory. The barrier then releases all threads in one step. The timed interval of a thread starts after this release, at its own clock read (line 314). The program does not store the start times. So it does not show how far apart the starts of the threads are. |
| 314 | `            double t0 = now_s(), t1;` | `t0`: the clock read directly after the barrier. It is the start of the timed interval of this thread. Each thread has its own `t0`. `t1` will hold the clock read after the passes (line 319). |
| 315 | `            uint64_t bytes = 0, p = 0;` | `bytes` counts the bytes of this interval, and `p` counts its passes. Both start at 0. |
| 316 | `            do {` | Starts the loop of the timed work. Its body runs at least once. |
| 317 | `                for (uint64_t c = 0; c < passes_per_check; c++, p++)` | The inner `for` runs `passes_per_check` passes without a clock read between them. This is 1 pass in the whole-chip test (line 297). |
| 318 | `                    bytes += pass(k, t, n, v + p, &sink);` | Runs one pass and adds its byte count to `bytes`. For the kernel `read` each pass is one call of `k_read` over the whole buffer. `v + p` gives the write kernels a new value in every pass. |
| 319 | `                t1 = now_s();` | `t1`: the clock read after the passes. The clock is never read inside a pass. |
| 320 | `            } while (t1 - t0 < cfg.min_s);` | The loop repeats while less than `cfg.min_s` has passed after `t0`: 0.5 s in the whole-chip test [Ref3]. A thread never stops inside a pass. In the whole-chip test its interval ends at the first end of a pass that lies 0.5 s or more after `t0`. So the interval is 0.5 s or longer, and it exceeds 0.5 s by less than the time of one pass. The threads therefore stop at different times. |
| 321 | `            t->res[k][rep].bytes = bytes;` | Stores the bytes that this thread counted, for this kernel and repetition. |
| 322 | `            t->res[k][rep].elapsed_s = t1 - t0;` | Stores the time `t1 - t0` of this thread. The interval ended at the last clock read of line 319. The time covers the passes and the clock reads between them. It does not cover the warm-up pass or the waits at the barrier. |
| 323 | `            pthread_barrier_wait(&bar);` | Waits at the barrier until all workers have finished the interval and the main thread (line 426) has arrived. A thread that stopped early waits here and reads no memory while the other threads finish their last pass. |
| 324 | `        }` | Ends the repetition loop of line 311. The next repetition starts with its warm-up pass directly after the barrier. The code has no sleep there. |
| 325 | `    }` | Ends the kernel loop of line 308. |
| 326 | `    return NULL;` | The thread ends after the last repetition of the last selected kernel. |
| 327 | `}` | Ends the function `worker`. |

### Function `usage`: print the options and stop (lines 329 to 338)

| Line | Source | Explanation |
|---:|---|---|
| 329 | `static void usage(void)` | Starts the function `usage`. It prints the list of options to the error output and ends the program with exit status 2. |
| 330 | `{` | Opens the body of `usage`. |
| 331 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to the error output. Its text is in lines 332 to 335. |
| 332 | `            "usage: bandwidth [--threads T --cpus LIST] [--bytes B] "` | Text of the message: the options for the thread count, the CPU list and the buffer size. |
| 333 | `            "[--kernel read\|write\|copy\|all\|asmread\|asmwrite\|asmcopy\|asmall] "` | Text of the message: the names that the option `--kernel` accepts. |
| 334 | `            "[--min-ms MS] [--reps R] [--no-thp] [--per-thread]\n"` | Text of the message: the options for the minimum time in ms, the number of repetitions, no 2 MiB pages, and one line per thread. |
| 335 | `            "  asm* kernels: aarch64 only, loads/stores only, bytes must be a multiple of 256\n");` | Text of the message, second line: the asm kernels exist only on 64-bit Arm (`aarch64`), they hold loads and stores only, and the buffer size must be a multiple of 256. The check of line 392 applies the rule of 256 to every kernel, not only to the asm kernels. This line ends the `fprintf` call. |
| 336 | `    exit(2);` | Ends the program with exit status 2. |
| 337 | `}` | Ends the function `usage`. |

### Function `main`: defaults and arguments (lines 339 to 387)

| Line | Source | Explanation |
|---:|---|---|
| 339 | `int main(int argc, char **argv)` | Starts the function `main`. It reads the arguments, starts the threads, and prints one rate row per timed interval. |
| 340 | `{` | Opens the body of `main`. |
| 341 | `    int threads_given = 0;` | `threads_given`: becomes 1 when the option `--threads` is given (line 354). The check of line 388 uses it. |
| 342 | `    cfg.bytes = 1UL << 20;` | Default before the arguments are read: a buffer of 1 MiB (1048576 bytes) per thread. |
| 343 | `    cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;` | Default: the three C kernels `read`, `write` and `copy` are selected. |
| 345 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments of the command line. |
| 346 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 347 | `        int more = i + 1 < argc;` | `more`: true when one more argument follows, which an option with a value needs. |
| 348 | `        if (!strcmp(a, "--no-thp")) {` | Tests whether the argument is `--no-thp`. `strcmp` returns 0 when two texts are equal. |
| 349 | `            cfg.use_thp = 0;` | `--no-thp` forbids 2 MiB pages for the buffers (line 130). `ra.sh` does not pass it [Ref3]. |
| 350 | `        } else if (!strcmp(a, "--per-thread")) {` | Tests for `--per-thread`. |
| 351 | `            cfg.per_thread = 1;` | `--per-thread` adds one output line per thread and repetition (line 449). `ra.sh` does not pass it [Ref3]. |
| 352 | `        } else if (!strcmp(a, "--threads") && more) {` | Tests for `--threads` with a value after it. |
| 353 | `            cfg.threads = atoi(argv[++i]);` | The number of threads. `atoi` turns the next argument into an integer, and `++i` steps over that argument. `ra.sh` passes 120 [Ref3]. |
| 354 | `            threads_given = 1;` | Notes that `--threads` was given. |
| 355 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 356 | `            parse_cpus(argv[++i]);` | The CPU list, read by `parse_cpus`. `ra.sh` passes `0-119` [Ref3]. |
| 357 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 358 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size of each thread, read by `parse_bytes`. `ra.sh` passes `256M` (256 MiB) [Ref3]. |
| 359 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Tests for `--min-ms` with a value after it. |
| 360 | `            cfg.min_s = atof(argv[++i]) / 1000.0;` | The minimum time of an interval. `atof` reads the value in ms, and the division by 1000 gives seconds. `ra.sh` passes 500, which gives 0.5 s [Ref3]. |
| 361 | `        } else if (!strcmp(a, "--reps") && more) {` | Tests for `--reps` with a value after it. |
| 362 | `            cfg.reps = atoi(argv[++i]);` | The number of timed intervals per kernel. `ra.sh` passes 3 [Ref3]. |
| 363 | `        } else if (!strcmp(a, "--kernel") && more) {` | Tests for `--kernel` with a value after it. |
| 364 | `            const char *k = argv[++i];` | `k`: the kernel name that follows `--kernel`. `ra.sh` passes one kernel name per process. One call of `ra.sh` starts `bw_old` with each of the six names twice, once per round [Ref3]. |
| 365 | `            memset(cfg.run, 0, sizeof cfg.run);` | First clears every selection: `memset` sets all flags of `cfg.run` to 0. Then one of the next lines selects by the name. |
| 366 | `            if (!strcmp(k, "all"))` | Tests for the name `all`. |
| 367 | `                cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;` | `all` selects the three C kernels `read`, `write` and `copy`. |
| 368 | `            else if (!strcmp(k, "read"))` | Tests for the name `read`. |
| 369 | `                cfg.run[K_READ] = 1;` | Selects the kernel `read` only. It is the function `k_read`. |
| 370 | `            else if (!strcmp(k, "write"))` | Tests for the name `write`. |
| 371 | `                cfg.run[K_WRITE] = 1;` | Selects the kernel `write` only. |
| 372 | `            else if (!strcmp(k, "copy"))` | Tests for the name `copy`. |
| 373 | `                cfg.run[K_COPY] = 1;` | Selects the kernel `copy` only. |
| 374 | `            else if (!strcmp(k, "asmall"))` | Tests for the name `asmall`. |
| 375 | `                cfg.run[K_ASMREAD] = cfg.run[K_ASMWRITE] = cfg.run[K_ASMCOPY] = 1;` | `asmall` selects the three asm kernels. |
| 376 | `            else if (!strcmp(k, "asmread"))` | Tests for the name `asmread`. |
| 377 | `                cfg.run[K_ASMREAD] = 1;` | Selects the kernel `asmread` only. |
| 378 | `            else if (!strcmp(k, "asmwrite"))` | Tests for the name `asmwrite`. |
| 379 | `                cfg.run[K_ASMWRITE] = 1;` | Selects the kernel `asmwrite` only. |
| 380 | `            else if (!strcmp(k, "asmcopy"))` | Tests for the name `asmcopy`. |
| 381 | `                cfg.run[K_ASMCOPY] = 1;` | Selects the kernel `asmcopy` only. |
| 382 | `            else` | The case of every other name. |
| 383 | `                usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 384 | `        } else {` | The case of every other argument: an unknown option, or an option without its value. |
| 385 | `            usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 386 | `        }` | Ends the chain of tests that starts in line 348. |
| 387 | `    }` | Ends the loop over the arguments (line 345). |

### Function `main`: checks of the arguments (lines 388 to 400)

| Line | Source | Explanation |
|---:|---|---|
| 388 | `    if (threads_given && cfg.ncpus == 0) {` | Check: `--threads` is accepted only together with `--cpus`. The test is true when `--threads` was given and the CPU list is empty. |
| 389 | `        fprintf(stderr, "--threads requires --cpus\n");` | Prints `--threads requires --cpus` to the error output. |
| 390 | `        usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 391 | `    }` | Ends the `if` of line 388. |
| 392 | `    if (cfg.threads < 1 \|\| cfg.reps < 1 \|\| cfg.reps > MAX_REPS \|\| cfg.bytes == 0 \|\| cfg.bytes % 256 != 0)` | Checks of the values. The thread count must be 1 or more. The repetitions must be 1 to 32. The buffer size must not be 0, and it must be a multiple of 256 B. Every kernel then ends exactly at the end of the buffer: `k_read` moves in steps of 128 B, the asm kernels in steps of 256 B. |
| 393 | `        usage();` | A failed check prints the option list and ends the program with exit status 2 (`usage`). |
| 394 | `    if (!HAVE_ASM_KERNELS && (cfg.run[K_ASMREAD] \|\| cfg.run[K_ASMWRITE] \|\| cfg.run[K_ASMCOPY])) {` | Tests whether an asm kernel is selected in a build without the asm kernels (a processor that is not 64-bit Arm). |
| 395 | `        fprintf(stderr, "asm kernels need aarch64\n");` | Prints `asm kernels need aarch64` to the error output. |
| 396 | `        return 2;` | The program ends with exit status 2. |
| 397 | `    }` | Ends the `if` of line 394. |
| 398 | `    if (cfg.ncpus && cfg.threads > cfg.ncpus)` | Tests whether a CPU list was given and there are more threads than CPUs in it. |
| 399 | `        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);` | This only gives a warning on the error output, with both numbers. The list is then used again from its start (line 408). The whole-chip test has 120 threads on 120 CPUs [Ref3]. |

### Function `main`: thread table, barrier, threads and header lines (lines 401 to 419)

| Line | Source | Explanation |
|---:|---|---|
| 401 | `    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);` | Allocates the thread table with `calloc`: one `struct thread` per thread, filled with zeros. |
| 402 | `    if (!th \|\| pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {` | Tests the allocation and creates the barrier for `cfg.threads + 1` threads: the workers plus the main thread. In the whole-chip test this is 121 [Ref3]. |
| 403 | `        perror("setup");` | On a failure of one of the two steps: `perror` prints the word `setup` and an error text. |
| 404 | `        return 2;` | On a failure: the program ends with exit status 2. |
| 405 | `    }` | Ends the `if` of line 402. |
| 406 | `    for (int i = 0; i < cfg.threads; i++) {` | Loop that creates the threads. |
| 407 | `        th[i].idx = i;` | Thread `i` gets the index `i`. |
| 408 | `        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;` | Thread `i` gets the CPU `cfg.cpus[i % cfg.ncpus]`: entry `i` of the CPU list. The list is used again from its start when there are more threads than entries. With the list `0-119` and 120 threads, thread i gets CPU i. Without a CPU list the value is -1, and the thread is not pinned (line 299). |
| 409 | `        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {` | Creates the thread. It starts `worker` immediately: the thread pins itself, reserves and writes its buffer, runs the first warm-up pass and then waits at the barrier. |
| 410 | `            perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and an error text. |
| 411 | `            return 2;` | The program then ends with exit status 2. |
| 412 | `        }` | Ends the `if` of line 409. |
| 413 | `    }` | Ends the loop of line 406. |
| 415 | `    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "` | Prints the first header line to the standard output. It starts with `#` and gives the rate formula: GB = 1e9 bytes, and `aggregate_GBps` is the sum of the bytes of all threads divided by the longest thread time. |
| 416 | `           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",` | Continues the text of the header line: copy counts the bytes read plus the bytes written. Then come the settings of the process: the thread count, the buffer size per thread in bytes, the minimum time in ms and the request for 2 MiB pages. |
| 417 | `           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");` | The four values of the header line. `thp=` shows `madvise` when the program asks for 2 MiB pages and `nohugepage` with `--no-thp`. This text shows the request only. It does not show that the buffers got such pages. |
| 418 | `    printf("kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,"` | Prints the second header line: the 10 column names of the interval rows. This line holds the first 7 names. |
| 419 | `           "per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps\n");` | Continues the column names: the lowest, the highest and the mean thread rate. |

### Function `main`: rate of each interval, output rows and end (lines 420 to 463)

| Line | Source | Explanation |
|---:|---|---|
| 420 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the kernels in the same order as the workers (line 308). |
| 421 | `        if (!cfg.run[k])` | The same skip rule as in the workers (line 309). |
| 422 | `            continue;` | Skips a kernel that is not selected. |
| 423 | `        double best = -1;` | `best`: will hold the highest total rate of the repetitions of this kernel. |
| 424 | `        for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions, as the main thread sees them. |
| 425 | `            pthread_barrier_wait(&bar); /* release the workers */` | First wait: the barrier opens when the main thread and all workers have arrived. Each worker arrives after its warm-up pass (line 313). The workers then start their timed interval (line 314). The comment says: release the workers. |
| 426 | `            pthread_barrier_wait(&bar); /* all workers finished this rep */` | Second wait: it returns when every worker has finished its interval (line 323). The main thread does no work during the interval. The program does not pin the main thread. The comment says: all workers finished this repetition. |
| 427 | `            uint64_t total = 0;` | `total`: the bytes of all threads in this interval. It starts at 0. While the main thread computes and prints the row (lines 427 to 446), the workers already run the warm-up pass of the next interval, when there is one. The next timed interval starts only after the main thread waits at the barrier again (line 425). |
| 428 | `            double max_el = 0, mn = 1e30, mx = 0, sum = 0;` | Start values for one row: `max_el` (the longest thread time), `mn` and `mx` (the lowest and the highest thread rate) and `sum` (the sum of the thread rates). `mn` starts at 1e30, a value above every rate. |
| 429 | `            for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 430 | `                struct result *r = &th[i].res[k][rep];` | `r`: the result of thread `i` for this kernel and repetition (lines 321 to 322). |
| 431 | `                double g = (double)r->bytes / r->elapsed_s / 1e9;` | `g`: the rate of this thread in GB/s. It is the bytes of the thread, divided by the time of the same thread, divided by 1e9. |
| 432 | `                total += r->bytes;` | Adds the bytes of the thread to `total`. |
| 433 | `                if (r->elapsed_s > max_el)` | Tests whether the time of this thread is the longest so far. |
| 434 | `                    max_el = r->elapsed_s;` | Keeps the longest thread time in `max_el`. |
| 435 | `                if (g < mn)` | Tests whether the rate of this thread is the lowest so far. |
| 436 | `                    mn = g;` | Keeps the lowest thread rate in `mn`. |
| 437 | `                if (g > mx)` | Tests whether the rate of this thread is the highest so far. |
| 438 | `                    mx = g;` | Keeps the highest thread rate in `mx`. |
| 439 | `                sum += g;` | Adds the thread rate to `sum` for the mean. |
| 440 | `            }` | Ends the loop over the threads (line 429). |
| 441 | `            double agg = (double)total / max_el / 1e9;` | `agg`: the total rate of the interval in GB/s. It is the bytes of all threads, divided by the longest thread time, divided by 1e9. The output column is `aggregate_GBps`. A thread with a shorter time adds no bytes after its own stop. So `agg` is never above the sum of the thread rates. It is lower when the times of the threads differ. |
| 442 | `            if (agg > best)` | Tests whether this `agg` is the highest of the repetitions so far. |
| 443 | `                best = agg;` | Keeps the highest `agg` in `best`. |
| 444 | `            printf("%s,%d,%lu,%d,%lu,%.4f,%.2f,%.2f,%.2f,%.2f\n", kernel_name[k], cfg.threads,` | Prints one interval row with 10 columns, separated by commas. This line holds the format and the values of columns 1 and 2: the kernel name and the thread count. |
| 445 | `                   (unsigned long)cfg.bytes, rep, (unsigned long)total, max_el, agg, mn, mx,` | The values of columns 3 to 9: the buffer size per thread in bytes, the repetition number (counted from 0), `total_bytes` (`total`), `elapsed_s` (`max_el`, with 4 decimals), `aggregate_GBps` (`agg`, with 2 decimals), and the lowest and the highest thread rate in GB/s (2 decimals each). |
| 446 | `                   sum / cfg.threads);` | The value of column 10: the mean thread rate in GB/s, which is `sum / cfg.threads`, with 2 decimals. |
| 447 | `        }` | Ends the repetition loop of line 424. |
| 448 | `        printf("%s,%d,%lu,best,,,%.2f,,,\n", kernel_name[k], cfg.threads, (unsigned long)cfg.bytes, best);` | After the last repetition: prints the `best` row. Its column `aggregate_GBps` holds the highest `agg` of the repetitions. The columns `total_bytes` and `elapsed_s` and the three thread-rate columns are empty. The analysis scripts `stat_k120.py` and `facts_data.py` do not use this row [Ref4]. |
| 449 | `        if (cfg.per_thread) {` | Only with `--per-thread`: lines 452 to 456 print one more line per thread and repetition. `ra.sh` does not pass this option, and the files of the whole-chip test hold no such line [Ref3] [Ref5]. |
| 450 | `            /* thread,<index>,<cpu>,<kernel>,<rep>,<GB/s>: one line per thread and repetition, so that` | Comment: the form of the line: the word `thread`, the thread index, the CPU, the kernel, the repetition and the rate in GB/s. One line per thread and repetition. |
| 451 | `             * concurrent per-group totals can be formed from one repetition (reviewer's request) */` | Comment: the purpose of these lines. The rates of a group of threads that ran at the same time can be added from one repetition. The comment says that a reviewer asked for this. |
| 452 | `            for (int i = 0; i < cfg.threads; i++)` | Loop over the threads. |
| 453 | `                for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions. |
| 454 | `                    struct result *r = &th[i].res[k][rep];` | `r`: the result of thread `i` for this kernel and repetition. |
| 455 | `                    printf("thread,%d,%d,%s,%d,%.2f\n", i, th[i].cpu, kernel_name[k], rep, (double)r->bytes / r->elapsed_s / 1e9);` | Prints the line: the word `thread`, the thread index, the CPU, the kernel name, the repetition and the thread rate in GB/s with 2 decimals. The rate is the bytes of the thread, divided by the time of the same thread, divided by 1e9. |
| 456 | `                }` | Ends the loop of line 453. |
| 457 | `        }` | Ends the `if` of line 449. |
| 458 | `        fflush(stdout);` | `fflush` writes the buffered rows of this kernel to the output now. |
| 459 | `    }` | Ends the kernel loop of line 420. |
| 460 | `    for (int i = 0; i < cfg.threads; i++)` | Loop over the threads. |
| 461 | `        pthread_join(th[i].tid, NULL);` | Waits until worker thread `i` has ended (`pthread_join`). After the loop every worker has ended. |
| 462 | `    return 0;` | Ends the process with exit status 0. |
| 463 | `}` | Ends the function `main`. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: Build record of 2026-11-13, 18:12:22 UTC. Line 1: the time and `mode=all`. In this mode run_kernels.sh goes on to the timed runs after the build. Line 2: gcc 14.2.0. Line 3: the compiler flags. Lines 14 to 22: sha256 of the sources and the binaries (line 14 this file, line 15 bandwidth.c, line 19 bw_old, line 20 bw_new). Lines 155 to 226: objdump text of `k_read` of bw_old, with the loop in lines 183 to 198. Lines 228 to 329: the other five kernels of bw_old. Lines 23 to 37: `k_read` of bw_new. Lines 39 to 153: the other five kernels of bw_new.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: The build script. Line 19: the compiler flags. Line 28: the comment that calls this file the source before the change. Line 31: the build of bw_old from bandwidth.orig.c. Lines 39 to 44: the commands that wrote the objdump text of the kernels.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: The script of part A. Line 9: the script runs under `taskset -c 0-119`. Lines 16 to 20: the sha256 check of bw_old and bw_new. Line 17 holds the expected value for bw_old. It equals line 19 of [Ref1]. Line 18 holds the expected value for bw_new. It equals line 20 of [Ref1]. Line 41: the script writes a line that starts with `-- binary` to the output file before each process. Line 42: the arguments of each process. Lines 44 to 48: the kernel order, the two rounds, 120 threads, CPUs 0-119, 256M.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`: Lines 36 to 41: the parser takes only the rows whose fourth field is a number, so it skips the `best` row. The script facts_data.py in the same folder has the same rule in lines 298 to 303.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/threads120.csv`: Output of part A, first call of ra.sh in the rerun. Lines 1 to 7: the first process of bw_old with kernel `read`. Line 4 is the example row: total_bytes 256087425024, elapsed_s 0.5474, aggregate_GBps 467.83, thread rates 2.98 to 4.93 GB/s, mean 3.99 GB/s. This file and the files of the folders k120-T72A2-20261117T221518Z and k120-T72A3-20261117T221827Z each hold 12 lines that start with `-- binary bw_old` and no line that starts with `thread,`. ra.sh writes one line that starts with `-- binary` before each process [Ref3].
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: Lines 38 to 89: the project word list. The definitions of the project terms under "Words used here" are taken from it. Lines 44 and 45: the names of the old and the new read kernel in bw_old and bw_new. Lines 241 and 937: the page state of the buffers of part A is not recorded.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/probe.txt`: The state that ra.sh recorded before the first process of its first call in the rerun. Line 3: `thp=[always] madvise never`. The value in brackets is the active Linux setting for transparent huge pages. Line 12: the sha256 of bw_old, computed by ra.sh before the first process. It equals line 19 of [Ref1]. Lines 3 and 12 of the same file in the folders k120-T72A2-20261117T221518Z and k120-T72A3-20261117T221827Z hold the same text.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: The new source. It lies in the same folder as bandwidth.orig.c. Its sha256, computed on 2026-11-21, starts with f1985072. The command `diff bandwidth.orig.c bandwidth.c` prints 9 places. Counted in lines of bandwidth.orig.c: one new line after line 9, the changed lines 135 to 137, new lines after line 160, the changed lines 257 to 259, new lines after line 286, the removed line 292, and the changed lines 312, 318 and 335. In bandwidth.c the comments that hold the old functions are lines 136 to 166 and lines 381 to 415.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: Build record of 2026-11-13, 18:32:18 UTC. Line 1: the time and `mode=probe` (build, machine code and self-test, no timed runs). Line 15: the sha256 of bandwidth.c. It equals the sha256 of the local file [Ref8]. Line 20: the sha256 of bw_new. It equals line 20 of [Ref1].
- [Ref10] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
