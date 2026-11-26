# `bandwidth.c` explained

- Source file: `bench/bandwidth.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 620 lines, 21499 bytes).
- sha256 of the source when this page was built: `f198507208e0b010739660dbea178096e030c97cbf88e479d8cc3f1f11967824`.
- Role in the whole-chip test: Source of bw_new: the benchmark with the new read kernel (part A)
- This file is equal to `kernels-2026-11-13/bandwidth.c` of the same repo (same sha256). Both pages hold the same explanation.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

## Short version: purpose

bandwidth.c is a benchmark: each thread runs one kernel (read, write or copy) in whole passes over its own buffer for a minimum time, and `main` prints one rate in GB/s per timed interval. This version holds the new read kernel: 16 NEON loads per 256 B and no arithmetic.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel**: the inner loop of the benchmark that reads memory. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Rerun**: the whole-chip read test of 2026-11-17. It was run after the memory speed of CRB was lowered from 8000 MT/s to 7200 MT/s (MT/s = million transfers per second, the unit of memory speed). Part A, part L and part C are parts of it. Only part A runs bw_old and bw_new.
- **go.sh**: the driver script of the rerun. It calls ra.sh once per session.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Kernel**: one of the six inner loops of this benchmark: read, write, copy, asmread, asmwrite, asmcopy. It never means the Linux kernel.
- **Pass**: one run of a kernel over the whole buffer of one thread. The function `pass` runs one.
- **Loop pass**: one run of the loop body of a kernel. The new read kernel reads 256 B in one loop pass.
- **B, MiB, GB**: B = byte. MiB = 2^20 bytes = 1,048,576 bytes. GB = 1e9 bytes.
- **aggregate_GBps**: the rate that this file prints for one interval: the bytes of all threads, divided by the longest elapsed time of any thread. Unit GB/s.
- **Thread rate**: the bytes of one thread in one interval, divided by the elapsed time of that thread. Unit GB/s.
- **AArch64**: the 64-bit instruction set of Arm processors. gcc defines the macro `__aarch64__` when it compiles for it.
- **NEON**: the vector instructions of AArch64 with registers of 16 B.
- **Intrinsic**: a C function that maps to a machine instruction. `vld1q_u64` loads 16 B into a vector. `vst1q_u64` stores 16 B from a vector.
- **SVE**: Scalable Vector Extension: a second set of vector instructions of Arm processors. The listing shows its registers as z and p registers.
- **`ldp`, `stp`**: the Arm instructions "load pair" and "store pair". With q registers one instruction moves 32 B: two registers of 16 B.
- **q, v and d registers**: names of the vector registers of AArch64. q5 and v5 are the same register of 16 B. d5 is its low 8 bytes.
- **gcc**: the C compiler that built the binaries: version 14.2.0 on CRB [Ref1].
- **`asm` statement**: a gcc extension that puts assembly text into a C function. The lists after the text tell the compiler which values the text reads, changes and overwrites.
- **Listing**: the text that the tool objdump printed from a binary: one line per machine instruction. The listings of bw_old and bw_new are in the build record [Ref1].
- **Build record**: the file probe.txt that run_kernels.sh wrote at a build: compiler, flags, sha256 values and listings [Ref1].
- **run_kernels.sh, ra.sh**: run_kernels.sh is the script of 2026-11-13 that built bw_old and bw_new [Ref4]. ra.sh is the script that runs part A of the rerun [Ref5].
- **Preprocessor condition**: a line such as `#if`. The compiler reads the lines up to `#else` or `#endif` only when the condition is true.
- **Barrier**: an object of the thread library (`pthread_barrier_t`). A thread that calls `pthread_barrier_wait` waits until a fixed number of threads have called it. Then all of them continue.
- **Page fault, first write**: Linux assigns a physical page to new memory at the first access to that page. This event is a page fault. Here the first access is a write.
- **Huge page**: a memory page of 2 MiB. Linux can use such pages for normal memory by itself (transparent huge pages, THP).
- **Bind**: to restrict a thread to one CPU.
- **taskset**: a Linux tool that starts a command with a fixed set of allowed CPUs.
- **memset**: the C library function that fills memory with one byte value.
- **Warm-up pass**: a pass that runs before the timed interval. Its bytes and its time are not counted.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **sha256**: a checksum. Two files with the same sha256 have the same content.

</details>

## Main flow

1. `main` sets the defaults and reads the arguments. Part A passes `--threads 120 --cpus 0-119 --bytes 256M --kernel NAME --reps 3 --min-ms 500` [Ref5] (lines 496-544).
2. `main` checks the values. The buffer size must be a multiple of 256 B (lines 545-556).
3. `main` creates the barrier for all benchmark threads plus itself and starts the threads (lines 558-570).
4. Each thread binds itself to its CPU, maps its buffer and writes the whole buffer once. This is not timed (lines 456-463).
5. For each selected kernel and each repetition, each thread runs one warm-up pass and then waits at the barrier (lines 465-470).
6. `main` waits at the same barrier. When all benchmark threads and `main` wait there, the barrier releases them, and the threads start the timed interval (line 582).
7. Each thread reads the clock and runs whole passes of the kernel. With the 256 MiB buffers of part A it reads the clock after each pass. It stops after the first pass that ends 0.5 s or more after its start (lines 471-477).
8. Each thread stores its bytes and its elapsed time. Then it waits at the barrier for the other threads and for `main` (lines 478-480).
9. `main` computes the rate of the interval from the results of all threads and prints one row (lines 583-603).
10. After the last repetition of a kernel `main` prints the `best` row and writes the output (lines 605-615).
11. After the last kernel the threads end, and `main` ends the process (lines 617-619).

## Behavior a reader must know

- **Which definitions are compiled.** The first `k_read`, `k_write` and `k_copy` are in lines 143 to 165. The first `pass` is in lines 388 to 414. Both blocks are text inside C comments (lines 136 to 166 and lines 381 to 415). They are not under a preprocessor condition. The compiler reads only the definitions of lines 184, 213, 239 and 418 [Ref8].
- **Proof from the binary.** The loop of `k_read` in bw_new has 11 instructions: 8 `ldp` loads, 1 `add` of 256 to the address, 1 `cmp` and 1 branch. After the loop comes `ret`. The function has no add of data, and it returns no value. That is the definition of line 184. The old definition adds every word to a sum: `k_read` in bw_old has 8 vector `add` instructions per 128 B and returns the sum [Ref1].
- **Preprocessor conditions.** Only two are active: `#if defined(__aarch64__)` in line 294 and `#if HAVE_ASM_KERNELS` in line 430. Both are true on CRB. Proof: bw_new holds `k_asmread`, `k_asmwrite` and `k_asmcopy` [Ref1].
- **Build.** gcc 14.2.0 on CRB with the flags `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11`. The same command built bw_old and bw_new [Ref1] [Ref4].
- **Is this file the source of bw_new?** A build from a file with the sha256 of this file gave a bw_new with the sha256 of the binary that the rerun used. The proof has three steps. The build record of 18:32:18 UTC on 2026-11-13 lists the sha256 of this file (f1985072...) for bandwidth.c and fd7c14df... for bw_new [Ref3]. ra.sh runs bw_new only when it has the sha256 fd7c14df... [Ref5]. The three result folders of part A record that value for bw_new [Ref9]. The binary bw_new is not in the local folders. Its sha256 is known only from records such as these. One limit: the earlier build record of 18:12:22 UTC lists another sha256 for bandwidth.c (c1406e02...), with the same sha256 of bw_new and the same listings [Ref1]. So the source text changed between the two builds, and the binary did not change. The run of 18:12:22 had the mode `all`: it is the run that timed the test of 2026-11-13 [Ref1]. The run of 18:32:18 had the mode `probe`: it built the binaries and timed nothing [Ref3] [Ref4]. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref10]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- **What is timed.** The time from the clock read of line 471 to the last clock read of line 476. It holds the passes and the clock reads between them. Not timed: the start of the threads, the binding, the mapping and the first write of the buffer, the warm-up pass before every interval, and the waits at the barrier.
- **Stop rule (whole-pass stop).** A thread tests the time only after a whole pass over its 256 MiB buffer. Every thread therefore ends at its own time, 0.5 s or more after its own start. A thread that has ended waits at the barrier and runs no kernel while the other threads end their last pass. During that time fewer than 120 threads run the kernel.
- **Rate.** `aggregate_GBps` = sum of the bytes of all threads / longest elapsed time of any thread / 1e9. With the kernel `read` every thread counts 268,435,456 bytes (the buffer size) per whole pass. A copy kernel counts 2 times that. The value is at most the sum of the thread rates. Example: the first interval of bw_new with the kernel `read` in session 1 shows 330.59 GB/s. In the same row, 120 times the mean thread rate (2.84 GB/s) is about 340.8 GB/s [Ref6].
- **Few passes per interval.** The example row of the note **Rate** counts 178,241,142,784 bytes. That is 664 passes for 120 threads, or about 5.5 passes per thread on average. 16 of the 18 intervals of bw_new with the kernel `read` in the three sessions of part A count exactly this number of bytes. In these 16 rows the rate differs only through `elapsed_s`, the longest thread time [Ref6].
- **Threads and buffers in part A.** 120 threads. Thread `i` is bound to CPU `i` (0 to 119). Each thread maps its own 256 MiB buffer, asks for huge pages, and writes the whole buffer once after it is bound. In a process with the kernel `copy` or `asmcopy` each thread maps and writes a second buffer of the same size. The huge page setting of CRB was `[always]` at the start of each session of part A [Ref9]. The source comment of lines 129 to 130 says that on a machine with this setting a buffer gets 2 MiB pages also without a request from the program. Insufficient data: whether the buffers of part A lay on huge pages. This file prints no page state. The field AnonHugePages in the file /proc/PID/smaps of a running bw_new process would resolve it.
- **The thread of `main`.** This file does not bind it to a CPU. ra.sh runs the process under `taskset -c 0-119`, so Linux may run `main` on any of these CPUs [Ref5]. During a timed interval `main` waits at the barrier.
- **Order inside one process of part A.** One kernel only. For each of the 3 intervals: one warm-up pass, the barrier, then the timed passes. The file holds no sleep call. A thread starts the warm-up pass of the next interval as soon as the second barrier releases it. ra.sh sets the order of the processes [Ref5].
- **Difference to the old source, 1 of 6: the read kernel.** Old: portable C, every 8-byte word is added to one of 16 running sums, and the function returns the total. New: 16 NEON loads per 256 B, no arithmetic, no return value. Machine code on CRB: the old loop reads 128 B per loop pass, so 256 B need 2 loop passes. These 2 loop passes hold 32 instructions: 8 `ldp`, 16 vector `add`, and 8 more for the address, the counter, the compare and the branch. The new loop reads 256 B in 1 loop pass of 11 instructions: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1].
- **Difference 2 of 6: the result of the read kernel.** After its loop the old `k_read` adds its 16 sums to one value, once per pass. The old `pass` stored that value into the variable `sink` on the stack of the thread, once per pass. The new code has neither step [Ref2].
- **Difference 3 of 6: `k_write`.** Old: a plain C loop that gcc compiled to a loop of SVE store instructions. New: 16 NEON stores per 256 B, compiled to 8 `stp`. This changes the kernel `write`. In a process with the kernel `read` it changes only the code of the first write of the buffer, which is not timed. Both versions leave the same content: every 8-byte word holds `v` [Ref1] [Ref2].
- **Difference 4 of 6: `k_copy`.** Old: a plain C loop that gcc compiled to a loop of SVE load and store instructions. New: 8 `ldp`, then 8 `stp`, per 256 B. This changes the kernel `copy` only [Ref1].
- **Difference 5 of 6: the place of the code in the binary.** The three `asm` kernels have the same source text and the same instructions in both binaries, at other addresses. Example: `k_asmread` starts at the address 0x1b40 in bw_new and at 0x1c88 in bw_old [Ref1]. Part A runs `asmread` with both binaries, so its output compares the same loop in the two binaries [Ref5].
- **Difference 6 of 6: lines that cannot change a rate.** Line 10 (the include), line 492 (the usage text) and the two comments that hold the old text. Apart from the differences 1 to 4 and these lines, both files hold the same text: `worker` apart from `sink`, the stop rule, `alloc_buf`, `pin_cpu`, `now_s` and the rate computation in `main` [Ref2].

## Call sequence in the whole-chip test

- `ra.sh:one`: part A: starts one bw_new process per kernel and round
  - `main` (line 496): reads the arguments, starts 120 threads, computes and prints the rates
    - `parse_cpus` (line 81): `--cpus 0-119` becomes the CPU numbers 0 to 119
    - `parse_bytes` (line 63): `--bytes 256M` becomes 268,435,456 bytes
    - `worker` (line 446): one thread per CPU, started by `pthread_create` in line 566
      - `pin_cpu` (line 108): binds thread i to CPU i
      - `alloc_buf` (line 119): maps the 256 MiB buffer of the thread
      - `k_write` (line 213): first write of the buffer, not timed
      - `pass` (line 418): warm-up pass before every interval, not timed
        - `k_read` (line 184): the selected kernel, here the new read kernel
      - `now_s` (line 56): clock read at the start of the timed interval
      - `pass` (line 418): timed passes, repeated until 0.5 s have passed
        - `k_read` (line 184): new read kernel: the process with `--kernel read`
        - `k_write` (line 213): the process with `--kernel write`
        - `k_copy` (line 239): the process with `--kernel copy`
        - `k_asmread` (line 297): hand-written read loop: the process with `--kernel asmread`
        - `k_asmwrite` (line 321): the process with `--kernel asmwrite`
        - `k_asmcopy` (line 344): the process with `--kernel asmcopy`
      - `now_s` (line 56): clock read after every pass, and the last read ends the interval
    - `main (rate and output rows)` (line 577): bytes of all threads / longest thread time, one row per interval

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `now_s` | 56-61 | Reads the Linux clock `CLOCK_MONOTONIC` in seconds. `worker` calls it at the start of an interval and, in the whole-chip test, after each pass. | - | yes |
| `parse_bytes` | 63-78 | Turns a size such as `256M` into bytes. The suffix k, m or g multiplies by 2^10, 2^20 or 2^30. | - | no |
| `parse_cpus` | 81-106 | Turns a CPU list such as `0-119` into the array `cfg.cpus`. | - | no |
| `pin_cpu` | 108-117 | Binds the calling thread to one CPU with `sched_setaffinity`. | - | no |
| `alloc_buf` | 119-134 | Maps one buffer, aligned to 2 MiB, and asks Linux for huge pages. Linux assigns no physical page here. | - | no |
| `k_read (old text inside a comment)` | 143-153 | Text of the old read kernel with 16 running sums. It is inside a comment. The compiler does not read it. | - | no |
| `k_write (old text inside a comment)` | 155-159 | Text of the old write kernel. It is inside a comment. The compiler does not read it. | - | no |
| `k_copy (old text inside a comment)` | 161-165 | Text of the old copy kernel. It is inside a comment. The compiler does not read it. | - | no |
| `k_read` | 184-211 | New read kernel. One loop pass loads 256 B with 16 NEON loads (8 `ldp` instructions on CRB) and drops the values. | - | yes |
| `k_write` | 213-237 | New write kernel: 256 B of stores per loop pass. It also writes every buffer once before any timing. | - | yes |
| `k_copy` | 239-284 | New copy kernel: one loop pass loads 256 B and then stores 256 B. | - | yes |
| `k_asmread` | 297-319 | Kernel `asmread`: hand-written loop with 8 `ldp` loads per 256 B. The old source holds the same text. | - | yes |
| `k_asmwrite` | 321-342 | Kernel `asmwrite`: hand-written loop with 8 `stp` stores per 256 B. The old source holds the same text. | - | yes |
| `k_asmcopy` | 344-376 | Kernel `asmcopy`: hand-written loop with 8 `ldp` and 8 `stp` per 256 B. The old source holds the same text. | - | yes |
| `pass (old text inside a comment)` | 388-414 | Text of the old `pass` with the `sink` parameter. It is inside a comment. The compiler does not read it. | - | no |
| `pass` | 418-444 | Runs the selected kernel once over the buffer. Returns the bytes moved: the buffer size, or 2 times the buffer size for a copy kernel. | `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite`, `k_asmcopy` | yes |
| `worker` | 446-484 | One benchmark thread. It binds itself, maps and writes its buffer. Per interval it runs a warm-up pass and the timed passes. | `pin_cpu`, `alloc_buf`, `k_write`, `pass`, `now_s` | yes |
| `usage` | 486-494 | Prints the argument list and ends the program with exit status 2. | - | no |
| `main` | 496-620 | Reads the arguments, starts the threads, starts each interval at the barrier, computes the rates and prints the rows. | `parse_cpus`, `parse_bytes`, `usage`, `worker` | no |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `bench/bandwidth.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (620 lines, 21499 bytes, sha256 `f198507208e0b010739660dbea178096e030c97cbf88e479d8cc3f1f11967824`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and include lines (lines 1 to 20)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Comment: starts the header comment of the file. It ends in line 8. |
| 2 | ` * bandwidth.c - multi-thread streaming bandwidth: read, write, copy.` | Comment: the name and the purpose of the program. It measures with several threads how fast memory is read, written and copied in address order (streaming). |
| 3 | ` *` | Comment: an empty line inside the header comment. |
| 4 | ` * Every thread owns its buffers (allocated and first-touched by that thread),` | Comment: each thread owns its buffers. The thread itself reserves them and writes them first (first touch). |
| 5 | ` * so timing contains no page faults. All threads start on a barrier, run` | Comment: so a timed interval holds no page fault. A page fault is the work that Linux does when a memory page is used for the first time. All threads start a timed interval together at a barrier (line 54). |
| 6 | ` * whole passes over their buffer until --min-ms has elapsed, and record` | Comment: each thread runs whole passes over its buffer until the time of the option `--min-ms` has passed. A pass is one run of a kernel over the whole buffer. |
| 7 | ` * bytes moved and their own elapsed time. GB means 1e9 bytes throughout.` | Comment: each thread records the bytes that it moved and the time that it measured itself. GB means 1e9 bytes everywhere in this program. |
| 8 | ` */` | Comment: the end of the header comment. |
| 9 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include line. This makes the Linux-only calls of the headers visible, for example `sched_setaffinity` and `CPU_SET` (lines 110 to 113). |
| 10 | `#include <arm_neon.h> /* NEON intrinsics for the C kernels: this file builds on AArch64 only */` | Includes the header of the NEON intrinsics (C functions that map to Arm vector instructions). The C kernels use its type `uint64x2_t` and its functions `vld1q_u64`, `vst1q_u64` and `vdupq_n_u64` (lines 184 to 284). This line is new against the old source [Ref2]. The comment says that the file therefore builds on AArch64 only. |
| 11 | `#include <pthread.h>` | Includes the header of the POSIX thread library. It gives the threads (`pthread_create`, `pthread_join`) and the barrier (`pthread_barrier_wait`). |
| 12 | `#include <sched.h>` | Includes the header for the CPU pinning: the type `cpu_set_t`, the macros `CPU_ZERO` and `CPU_SET`, and the call `sched_setaffinity`. |
| 13 | `#include <stdint.h>` | Includes the integer types of fixed size: `uint64_t` (64 bits), `uint8_t` (8 bits) and `uintptr_t` (an integer that can hold an address). |
| 14 | `#include <stdio.h>` | Includes the output functions `printf`, `fprintf`, `perror` and `fflush`. |
| 15 | `#include <stdlib.h>` | Includes `exit`, `calloc` and the functions that turn text into a number: `strtod`, `strtol`, `atoi` and `atof`. |
| 16 | `#include <string.h>` | Includes the text functions `strcmp` and `strtok`, and `memset`. |
| 17 | `#include <sys/mman.h>` | Includes `mmap` and `madvise`, the two Linux calls that `alloc_buf` uses for a buffer. |
| 18 | `#include <time.h>` | Includes `clock_gettime` and the type `struct timespec`. The function `now_s` reads the clock with them. |
| 19 | `#include <unistd.h>` | Includes `getpid`, which gives the process id. The worker uses it for the value that it stores (line 451). |

### Constants and the list of the kernels (lines 21 to 28)

| Line | Source | Explanation |
|---:|---|---|
| 21 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2 MiB (2097152 bytes), the size of one huge page. The expression shifts the number 2 left by 20 bits. `alloc_buf` aligns every buffer to this size (line 121, line 128). |
| 22 | `#define MAX_CPUS 1024` | `MAX_CPUS`: the CPU list holds at most 1024 entries (line 32, line 99). |
| 23 | `#define MAX_REPS 32` | `MAX_REPS`: at most 32 timed intervals per kernel (line 50, line 549). |
| 24 | `#define CHECK_BYTES (8UL << 20) /* clock is read after at least this many bytes */` | `CHECK_BYTES`: 8 MiB (8388608 bytes). Line 452 divides it by the buffer size. The result, or 1 when the result is 0 (line 454), is the number of passes between two clock reads. The comment says that the clock is read after at least this many bytes. For the bytes of the buffer this holds only when 8 MiB is a multiple of the buffer size, or when the buffer is larger than 8 MiB. For every other size the passes between two clock reads cover less than 8 MiB (line 452). |
| 26 | `enum kernel { K_READ, K_WRITE, K_COPY, K_ASMREAD, K_ASMWRITE, K_ASMCOPY, K_COUNT };` | The six kernels of the program, numbered 0 to 5. `K_COUNT` is 6, the number of kernels. A process runs its selected kernels in this order (loop of line 465). |
| 27 | `static const char *kernel_name[K_COUNT] = { "read", "write", "copy", "asmread", "asmwrite", "asmcopy" };` | `kernel_name`: the name of each kernel as text, in the order of line 26. It is the text that the first column of an output row shows (line 601, line 605). The option `--kernel` takes the same six names, and also `all` and `asmall` (lines 523 to 538). |

### Settings, per-thread data and the barrier (lines 29 to 55)

| Line | Source | Explanation |
|---:|---|---|
| 29 | `static struct {` | Starts the definition of `cfg`, the variable that holds the settings of the process. The definition ends in line 39. |
| 30 | `    int threads;` | `threads`: the number of worker threads (option `--threads`). |
| 31 | `    int ncpus;` | `ncpus`: the number of entries in the CPU list. It is 0 when no option `--cpus` was given. |
| 32 | `    int cpus[MAX_CPUS];` | `cpus`: the CPU list of the option `--cpus`, one CPU number per entry. |
| 33 | `    uint64_t bytes;` | `bytes`: the buffer size of each thread, in bytes (option `--bytes`). |
| 34 | `    int run[K_COUNT];` | `run`: one flag per kernel. `run[k]` is 1 when kernel `k` is selected (option `--kernel`). |
| 35 | `    double min_s;` | `min_s`: the minimum time of a timed interval, in seconds (option `--min-ms`). |
| 36 | `    int reps;` | `reps`: the number of timed intervals per kernel (option `--reps`). |
| 37 | `    int use_thp;` | `use_thp`: 1 when the program asks Linux for 2 MiB pages, 0 with the option `--no-thp` (line 131). |
| 38 | `    int per_thread; /* --per-thread: one line per thread with its CPU and best GB/s */` | `per_thread`: 1 with the option `--per-thread`. The comment says: one line per thread with its CPU and its best rate in GB/s. The comment is out of date. The code prints one line per thread and repetition, with the rate of that repetition (lines 609 to 613). |
| 39 | `} cfg = { .threads = 1, .min_s = 0.5, .reps = 3, .use_thp = 1 };` | Ends the definition and sets the defaults: 1 thread, a minimum time of 0.5 s per interval, 3 intervals per kernel, and a request for 2 MiB pages. Every other field starts at 0. |
| 41 | `struct result {` | Starts `struct result`: the result of one thread for one timed interval. |
| 42 | `    uint64_t bytes;` | `bytes`: the bytes that the thread counted in the interval. |
| 43 | `    double elapsed_s;` | `elapsed_s`: the time that the same thread measured for the interval, in seconds. |
| 44 | `};` | Ends `struct result`. |
| 46 | `struct thread {` | Starts `struct thread`: one entry per worker thread. |
| 47 | `    int idx;` | `idx`: the thread index, counted from 0. |
| 48 | `    int cpu;` | `cpu`: the CPU of the thread, or -1 when no CPU list was given (line 565). |
| 49 | `    uint64_t *a, *b;` | `a`, `b`: the addresses of the two buffers of the thread. Each buffer is an array of 8-byte elements. Only the copy kernels use `b` (line 460). |
| 50 | `    struct result res[K_COUNT][MAX_REPS];` | `res`: one result per kernel and interval: 6 kernels times at most 32 intervals. |
| 51 | `    pthread_t tid;` | `tid`: the handle of the thread. `pthread_create` fills it (line 566), and `pthread_join` uses it (line 618). |
| 52 | `};` | Ends `struct thread`. |
| 54 | `static pthread_barrier_t bar;` | `bar`: a barrier. A thread that calls `pthread_barrier_wait` on it waits until all worker threads and the main thread have called it. Then all of them continue together. Line 559 sets how many threads must arrive. |

### Function `now_s`: read the clock (lines 56 to 62)

| Line | Source | Explanation |
|---:|---|---|
| 56 | `static double now_s(void)` | Starts the function `now_s`. It reads the clock and returns the time in seconds. Every time value of the program comes from this function. The worker calls it at the start of a timed interval (line 471) and after the passes (line 476). |
| 57 | `{` | Opens the body of `now_s`. |
| 58 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 59 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | Reads `CLOCK_MONOTONIC` into `ts`. This is the Linux clock that only moves forward. A change of the date of the machine does not change it. It is the only clock that the file reads. |
| 60 | `    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;` | Returns the time in seconds as a `double`: the seconds plus the nanoseconds times 1e-9. |
| 61 | `}` | Ends the function `now_s`. |

### Function `parse_bytes`: read a size such as `256M` (lines 63 to 79)

| Line | Source | Explanation |
|---:|---|---|
| 63 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `256M` into a number of bytes. `main` calls it for the option `--bytes` (line 515). |
| 64 | `{` | Opens the body of `parse_bytes`. |
| 65 | `    char *end;` | `end`: will point to the first character after the number. |
| 66 | `    double v = strtod(s, &end);` | `strtod` reads a number from the start of the text `s` into `v`. The number may have a decimal point. `strtod` sets `end` to the first character that is not part of the number. |
| 67 | `    double mul = 1;` | `mul`: the factor of the suffix. It stays 1 when the text has no suffix. |
| 68 | `    switch (*end) {` | Looks at the character after the number. |
| 69 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | `k` or `K`: the factor is 1024 (2 to the power 10). `end++` steps over the suffix. |
| 70 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | `m` or `M`: the factor is 1048576 (2 to the power 20, which is 1 MiB). So `256M` gives 268435456 bytes (256 MiB). |
| 71 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | `g` or `G`: the factor is 1073741824 (2 to the power 30). |
| 72 | `    }` | Ends the `switch` of line 68. |
| 73 | `    if (end == s \|\| *end != '\0' \|\| v <= 0) {` | Tests three error cases. No number was read (`end == s`). Or other text follows the number and its suffix. Or the value is 0 or below. |
| 74 | `        fprintf(stderr, "bad size: %s\n", s);` | On an error: prints `bad size:` and the text to the error output. |
| 75 | `        exit(2);` | On an error: the program ends with exit status 2. |
| 76 | `    }` | Ends the `if` of line 73. |
| 77 | `    return (uint64_t)(v * mul);` | Returns the number times the factor as a whole number of bytes. A fraction of a byte is cut off. |
| 78 | `}` | Ends the function `parse_bytes`. |

### Function `parse_cpus`: read the CPU list (lines 80 to 107)

| Line | Source | Explanation |
|---:|---|---|
| 80 | `/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */` | Comment: three examples of a CPU list. `0-119` is a range. `0,2,4-7` is a list of numbers and ranges. `0-118:2` is a range with a step (the comment says stride): every second CPU from 0 to 118. |
| 81 | `static void parse_cpus(char *list)` | Starts the function `parse_cpus`. It reads the text of the option `--cpus` and appends every CPU number to `cfg.cpus`, in the order of the list. `0-119` gives the 120 entries 0, 1, 2 and so on up to 119. |
| 82 | `{` | Opens the body of `parse_cpus`. |
| 83 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Loop over the pieces of the list. `strtok` cuts the text at each comma and returns one piece per call. After the last piece it returns `NULL`, which ends the loop. |
| 84 | `        char *e, *e2;` | `e`, `e2`: each will point to the first character after a number that was read. |
| 85 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the piece (base 10) into `lo`. `hi` starts equal to `lo`, and `step` starts at 1. So a piece that is one number gives one CPU. |
| 86 | `        if (e != tok && *e == '-') {` | Tests whether a number was read and a hyphen follows it. The piece is then a range. |
| 87 | `            hi = strtol(e + 1, &e2, 10);` | Reads the number after the hyphen into `hi`, the last CPU of the range. |
| 88 | `            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */` | When no digit followed the hyphen (`e2 == e + 1`), `e` is set back to `tok`. The test of line 94 then rejects the piece. In every other case `e` moves to the first character after the second number. The comment gives the example `0-`, a range without an upper bound. |
| 89 | `            if (e != tok && *e == ':') {` | Tests whether the range is valid so far and a colon follows it. The piece then has a step. |
| 90 | `                step = strtol(e + 1, &e2, 10);` | Reads the number after the colon into `step`. |
| 91 | `                e = e2 == e + 1 ? tok : e2;` | The same rule as in line 88: when no digit followed the colon, `e` is set back to `tok`. |
| 92 | `            }` | Ends the `if` of line 89. |
| 93 | `        }` | Ends the `if` of line 86. |
| 94 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| hi >= CPU_SETSIZE \|\| step < 1) {` | Tests the piece. It is bad in each of these cases: no number was read, or line 88 or line 91 set `e` back (`e == tok`), or other text follows the numbers, or `lo` is below 0, or `hi` is below `lo`, or `hi` is `CPU_SETSIZE` or above (the number of CPUs that the type `cpu_set_t` can hold), or `step` is below 1. |
| 95 | `            fprintf(stderr, "bad cpu list: %s\n", tok);` | On a bad piece: prints `bad cpu list:` and the piece to the error output. |
| 96 | `            exit(2);` | On a bad piece: the program ends with exit status 2. |
| 97 | `        }` | Ends the `if` of line 94. |
| 98 | `        for (long c = lo; c <= hi; c += step) {` | Loop over the CPU numbers of the piece: from `lo` to `hi` in steps of `step`. |
| 99 | `            if (cfg.ncpus == MAX_CPUS) {` | Tests whether the list already holds 1024 entries (`MAX_CPUS`). |
| 100 | `                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);` | When the list is full: prints `bad cpu list: more than 1024 cpus` to the error output. |
| 101 | `                exit(2);` | When the list is full: the program ends with exit status 2. |
| 102 | `            }` | Ends the `if` of line 99. |
| 103 | `            cfg.cpus[cfg.ncpus++] = (int)c;` | Appends the CPU number to `cfg.cpus` and adds 1 to the count `cfg.ncpus`. |
| 104 | `        }` | Ends the loop of line 98. |
| 105 | `    }` | Ends the loop of line 83. |
| 106 | `}` | Ends the function `parse_cpus`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 108 to 118)

| Line | Source | Explanation |
|---:|---|---|
| 108 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It pins the calling thread to the CPU with the number `cpu`: Linux then runs the thread on that CPU only. |
| 109 | `{` | Opens the body of `pin_cpu`. |
| 110 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 111 | `    CPU_ZERO(&set);` | Empties the set. |
| 112 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 113 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. So only this thread is pinned. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 114 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 115 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 116 | `    }` | Ends the `if` of line 113. |
| 117 | `}` | Ends the function `pin_cpu`. |

### Function `alloc_buf`: one buffer, aligned for huge pages (lines 119 to 135)

| Line | Source | Explanation |
|---:|---|---|
| 119 | `static uint64_t *alloc_buf(uint64_t bytes)` | Starts the function `alloc_buf`. It reserves a buffer of at least `bytes` bytes and returns its address. The buffer starts at a multiple of 2 MiB. |
| 120 | `{` | Opens the body of `alloc_buf`. |
| 121 | `    size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | `len`: `bytes` rounded up to the next multiple of `HUGE_BYTES` (2 MiB). The expression adds `HUGE_BYTES - 1` and then clears the low bits. This gives the right value when `HUGE_BYTES` is a power of two. 256 MiB stays 256 MiB. |
| 122 | `    uint8_t *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ \| PROT_WRITE,` | `mmap` asks Linux for `len + HUGE_BYTES` bytes of new memory. The extra `HUGE_BYTES` bytes make it possible to move the start to an aligned address later (line 128). `NULL`: Linux chooses the address. `PROT_READ \| PROT_WRITE`: the program may read and write the memory. |
| 123 | `                        MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | Continues the call of line 122. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. `mmap` reserves addresses only. Linux assigns the physical memory when a page is first written (line 459). |
| 124 | `    if (raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 125 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 126 | `        exit(2);` | On failure: the program ends with exit status 2. |
| 127 | `    }` | Ends the `if` of line 124. |
| 128 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the first address in the reserved range that is a multiple of 2 MiB. The buffer starts there. The expression rounds the address `raw` up in the same way as line 121 rounds the size. |
| 129 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: `MADV_NOHUGEPAGE` matters on a machine where the Linux setting for transparent huge pages (THP) is `always`. |
| 130 | `     * would still get 2 MiB pages. */` | Comment: without it, the buffers of a run with `--no-thp` would still get 2 MiB pages. |
| 131 | `    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` with `MADV_HUGEPAGE` asks Linux to use 2 MiB pages for the `len` bytes that start at `p`. With the option `--no-thp` it passes `MADV_NOHUGEPAGE`, which forbids them. Part A does not pass `--no-thp` [Ref5]. |
| 132 | `        perror("madvise (continuing)");` | A failed `madvise` only prints a message that starts with `madvise (continuing)`. The program goes on. It never checks whether the buffer in fact lies on 2 MiB pages. |
| 133 | `    return (uint64_t *)p;` | Returns the aligned address as a pointer to 8-byte elements. The program never releases the buffer. |
| 134 | `}` | Ends the function `alloc_buf`. |

### The old kernels, kept as text inside a comment (not compiled) (lines 136 to 167)

| Line | Source | Explanation |
|---:|---|---|
| 136 | `/*` | Comment: opens a C comment that ends in line 166. The compiler reads nothing between these two lines. No preprocessor condition such as `#if` is used here. The comment keeps the three kernels of the old source as a record. |
| 137 | ` * History: k_read, k_write and k_copy as they were until 2026-11-13. They` | Comment: history. The comment holds `k_read`, `k_write` and `k_copy` as they were until 2026-11-13. |
| 138 | ` * are replaced by the C kernels below. The old comment of k_read was: "16` | Comment: the C kernels below (lines 184 to 284) replace them. Then the comment starts to quote the old comment of `k_read`. |
| 139 | ` * independent accumulators keep the loop load-bound: on 128-bit NEON gcc` | Comment, quoted old text: 16 independent accumulators (running sums) keep the loop load-bound. The old comment means that the loads, not the adds, set the speed of the loop. This file holds no measurement of that. |
| 140 | ` * folds them into 8 vector chains, enough to hide a 2-cycle add latency; on` | Comment, quoted old text: with 128-bit NEON, gcc makes 8 chains of vector adds from the 16 sums. The old comment says that this is enough for an add that takes 2 cycles: the adds then do not limit the speed of the loop. |
| 141 | ` * AVX-512 they become 2 zmm chains."` | Comment, quoted old text: with AVX-512 the sums become 2 chains in `zmm` registers. AVX-512 belongs to x86 processors. This sentence does not apply to CRB. |
| 142 | ` *` | Comment: an empty line inside the comment. The text of the three old kernels follows. |
| 143 | `__attribute__((noinline)) static uint64_t k_read(const uint64_t *a, size_t n)` | Comment, old code that is not compiled: the first line of the old read kernel, the same text as in the old source [Ref2]. The old `k_read` returned a sum (`uint64_t`). The binary `bw_old` holds this code, and the binary `bw_new` does not [Ref1]. |
| 144 | `{` | Comment, old code that is not compiled: opens the body of the old `k_read`. |
| 145 | `    uint64_t s[16] = { 0 };` | Comment, old code that is not compiled: the 16 running sums of the old read kernel, all 0 at the start. |
| 146 | `    for (size_t i = 0; i < n; i += 16)` | Comment, old code that is not compiled: the outer loop of the old read kernel. One loop pass handled 16 elements of 8 bytes, which is 128 B. |
| 147 | `        for (int j = 0; j < 16; j++)` | Comment, old code that is not compiled: the inner loop of the old read kernel, 16 steps, one step per sum. |
| 148 | `            s[j] += a[i + j];` | Comment, old code that is not compiled: the old read kernel loaded one 8-byte element and added it to its own sum. So each load was followed by an add. |
| 149 | `    uint64_t sum = 0;` | Comment, old code that is not compiled: `sum`, for the total of the 16 sums. |
| 150 | `    for (int j = 0; j < 16; j++)` | Comment, old code that is not compiled: the loop over the 16 sums, once per pass over the buffer. |
| 151 | `        sum += s[j];` | Comment, old code that is not compiled: adds one of the 16 sums to `sum`. |
| 152 | `    return sum;` | Comment, old code that is not compiled: the old read kernel returned the total of the sums. |
| 153 | `}` | Comment, old code that is not compiled: ends the old `k_read`. |
| 155 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Comment, old code that is not compiled: the first line of the old `k_write`, a plain C loop over 8-byte elements. |
| 156 | `{` | Comment, old code that is not compiled: opens the body of the old `k_write`. |
| 157 | `    for (size_t i = 0; i < n; i++)` | Comment, old code that is not compiled: the loop of the old `k_write` over the `n` elements. |
| 158 | `        a[i] = v;` | Comment, old code that is not compiled: the old `k_write` stored `v` into element `i`. |
| 159 | `}` | Comment, old code that is not compiled: ends the old `k_write`. |
| 161 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Comment, old code that is not compiled: the first line of the old `k_copy`, a plain C loop over 8-byte elements. |
| 162 | `{` | Comment, old code that is not compiled: opens the body of the old `k_copy`. |
| 163 | `    for (size_t i = 0; i < n; i++)` | Comment, old code that is not compiled: the loop of the old `k_copy` over the `n` elements. |
| 164 | `        d[i] = s[i];` | Comment, old code that is not compiled: the old `k_copy` loaded element `i` of `s` and stored it to element `i` of `d`. |
| 165 | `}` | Comment, old code that is not compiled: ends the old `k_copy`. |
| 166 | ` */` | Comment: closes the comment that starts in line 136. |

### Comment: the design of the C kernels that are compiled (lines 168 to 183)

| Line | Source | Explanation |
|---:|---|---|
| 168 | `/*` | Comment: starts the comment on the three C kernels that are compiled (lines 184 to 284). It ends in line 183. |
| 169 | ` * C kernels: the same algorithm as the asm kernels below, written with NEON` | Comment: the C kernels use the same algorithm as the asm kernels below (lines 297 to 376). They are written with NEON intrinsics, which are C functions that map to Arm vector instructions. |
| 170 | ` * intrinsics. Each iteration moves 256 B as 16 vectors of 16 B and does no` | Comment: each loop pass (iteration) moves 256 B as 16 vectors of 16 B. |
| 171 | ` * arithmetic on the data. Callers guarantee n * 8 is a multiple of 256 and` | Comment: a loop pass does no arithmetic on the data. The callers guarantee that `n * 8` bytes is a multiple of 256 (the sentence ends in line 172). `main` checks this (line 549). |
| 172 | ` * non-zero. The compiler chooses the machine code: check it with objdump` | Comment: and that it is not 0. The next sentence: the compiler chooses the machine code. The comment asks to check it with `objdump`, the tool that prints the machine code of a binary. The listing of the build on CRB shows the result [Ref1]. |
| 173 | ` * after a change of compiler or flags.` | Comment: the check with `objdump` must be made again after a change of the compiler or of its flags. |
| 174 | ` *` | Comment: an empty line inside the comment. |
| 175 | ` * k_read and k_copy contain an empty asm statement that takes the 16 loaded` | Comment: `k_read` and `k_copy` hold an empty asm statement (lines 205 to 208, lines 261 to 264). It takes the 16 loaded vectors as inputs. |
| 176 | ` * vectors as inputs in NEON registers ("w"). gcc must have all 16 values in` | Comment: the inputs must be in NEON registers (the letter `w` in the statement). So gcc must have all 16 values in registers at that point. |
| 177 | ` * registers at that point. In k_read this keeps gcc from deleting the loads.` | Comment: in `k_read` this keeps gcc from deleting the loads. Nothing else in `k_read` uses the loaded values. |
| 178 | ` * The statement adds no instruction. It does not fix the order of the loads` | Comment: the statement adds no instruction. It does not fix the order of the loads and the stores of `k_copy` (the sentence goes on in line 179). Lines 178 to 182 were edited after the timed build of 2026-11-13. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with these 5 comment lines [Ref10]. The build record of 18:12:22 UTC, which the timed runs followed, lists another sha256 for `bandwidth.c` and the same sha256 for `bw_new` as the later build record [Ref1] [Ref3]. With the edit reversed, the text has the sha256 of the earlier text [Ref10]. No code line differs. |
| 179 | ` * and the stores of k_copy: gcc may move code across it. Observed with gcc` | Comment: gcc may move code across the statement. The next sentence starts here: what was observed with gcc (continued in line 180). |
| 180 | ` * 14.2.0 and the Makefile flags: with the statement, k_copy has its 8 ldp` | Comment: the observation was made with gcc 14.2.0 and the flags of the Makefile. The `Makefile` of the folder `bench` holds the same flags as the build script `run_kernels.sh`. With the statement, `k_copy` has its 8 `ldp` loads (continued in line 181). |
| 181 | ` * ahead of its 8 stp, as k_asmcopy has; without it, loads and stores` | Comment: ahead of its 8 `stp` stores, as `k_asmcopy` has. Without the statement, loads and stores (continued in line 182). |
| 182 | ` * alternate.` | Comment: alternate. This ends the sentence of line 181. |
| 183 | ` */` | Comment: the end of the comment on the C kernels. |

### Function `k_read`: the new read kernel (16 loads per 256 B, no arithmetic) (lines 184 to 212)

| Line | Source | Explanation |
|---:|---|---|
| 184 | `__attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)` | Starts the function `k_read`, the new read kernel. It only loads the buffer: 256 B per loop pass, and no arithmetic. `a` is the start of the buffer. `n` is the number of 8-byte elements (words) in it. `noinline` forbids the compiler to merge the function into its caller. The listing therefore shows it as a function of its own [Ref1]. The function returns nothing (`void`). The old `k_read` returned a sum. This is the only `k_read` that the compiler reads. The text in lines 143 to 153 is a comment [Ref8]. |
| 185 | `{` | Opens the body of `k_read`. |
| 186 | `    const uint64_t *p = a;` | `p`: the read position. It starts at the first element of the buffer. |
| 187 | `    const uint64_t *end = a + n;` | `end`: the first address after the buffer, which is `a` plus `n` elements. The machine code computes it with one instruction before the loop: `add x1, x0, x1, lsl #3` [Ref1]. |
| 188 | `    do {` | `do`: the loop body runs before the first test of the end (line 210). `main` rejects a buffer size of 0 (line 549), so the body never runs on an empty buffer. |
| 189 | `        uint64x2_t v0 = vld1q_u64(p + 0);` | `vld1q_u64(p + 0)` loads 16 B, which is two 8-byte elements, from the read position into the vector variable `v0`. The type `uint64x2_t` is a vector of two 64-bit integers. This load reads the bytes 0 to 15 of the current block of 256 B. |
| 190 | `        uint64x2_t v1 = vld1q_u64(p + 2);` | Loads the 16 B at element 2 after the read position into `v1`: the bytes 16 to 31 of the block. |
| 191 | `        uint64x2_t v2 = vld1q_u64(p + 4);` | Loads the bytes 32 to 47 of the block into `v2`. |
| 192 | `        uint64x2_t v3 = vld1q_u64(p + 6);` | Loads the bytes 48 to 63 of the block into `v3`. |
| 193 | `        uint64x2_t v4 = vld1q_u64(p + 8);` | Loads the bytes 64 to 79 of the block into `v4`. |
| 194 | `        uint64x2_t v5 = vld1q_u64(p + 10);` | Loads the bytes 80 to 95 of the block into `v5`. |
| 195 | `        uint64x2_t v6 = vld1q_u64(p + 12);` | Loads the bytes 96 to 111 of the block into `v6`. |
| 196 | `        uint64x2_t v7 = vld1q_u64(p + 14);` | Loads the bytes 112 to 127 of the block into `v7`. |
| 197 | `        uint64x2_t v8 = vld1q_u64(p + 16);` | Loads the bytes 128 to 143 of the block into `v8`. |
| 198 | `        uint64x2_t v9 = vld1q_u64(p + 18);` | Loads the bytes 144 to 159 of the block into `v9`. |
| 199 | `        uint64x2_t v10 = vld1q_u64(p + 20);` | Loads the bytes 160 to 175 of the block into `v10`. |
| 200 | `        uint64x2_t v11 = vld1q_u64(p + 22);` | Loads the bytes 176 to 191 of the block into `v11`. |
| 201 | `        uint64x2_t v12 = vld1q_u64(p + 24);` | Loads the bytes 192 to 207 of the block into `v12`. |
| 202 | `        uint64x2_t v13 = vld1q_u64(p + 26);` | Loads the bytes 208 to 223 of the block into `v13`. |
| 203 | `        uint64x2_t v14 = vld1q_u64(p + 28);` | Loads the bytes 224 to 239 of the block into `v14`. |
| 204 | `        uint64x2_t v15 = vld1q_u64(p + 30);` | Loads the bytes 240 to 255 of the block into `v15`. One loop pass has 16 loads in the source. It reads 256 B, each byte once. gcc joined each two neighbour loads into one `ldp` instruction, which loads 32 B into two 16-byte registers. The machine loop has 8 `ldp` instructions at the byte offsets 0, 32, 64 and so on up to 224, in rising order [Ref1]. |
| 205 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | The empty asm statement. Its instruction text (`""`) is empty, so it adds no instruction to the loop. It names the 16 vectors as inputs that must be in vector registers (`"w"`). So the compiler must have all 16 values loaded at this point. The source comment gives the purpose (lines 175 to 177): the statement keeps gcc from deleting the loads. `volatile` tells the compiler to keep the statement. This line names `v0` to `v3`. |
| 206 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the list of inputs: `v4` to `v7`. |
| 207 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the list of inputs: `v8` to `v11`. |
| 208 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Ends the list of inputs and the statement: `v12` to `v15`. After this line nothing uses the values. They are dropped. The listing shows no instruction that uses a loaded register, and no add of data [Ref1]. |
| 209 | `        p += 32;` | Moves the read position forward by 32 elements, which is 256 B. Machine code: `add x0, x0, #0x100` [Ref1]. |
| 210 | `    } while (p < end);` | Repeats the loop while the read position is below the end. Machine code: `cmp x1, x0`, then `b.hi` back to the first `ldp`. One loop pass is 11 instructions for 256 B: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1]. |
| 211 | `}` | Ends the function `k_read`. No value is returned. |

### Function `k_write`: the new write kernel, also used for the first touch (lines 213 to 238)

| Line | Source | Explanation |
|---:|---|---|
| 213 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_write`, the new write kernel. It stores the value `v` to every 8-byte element of the buffer `a`. In a process with the kernel `read` this function runs once per buffer, before any timing (line 459). `noinline` keeps it a function of its own, as in line 184. |
| 214 | `{` | Opens the body of `k_write`. |
| 215 | `    uint64_t *p = a;` | `p`: the write position. It starts at the first element of the buffer. |
| 216 | `    const uint64_t *end = a + n;` | `end`: the first address after the buffer. |
| 217 | `    uint64x2_t q = vdupq_n_u64(v);` | `vdupq_n_u64(v)` builds one 16-byte vector `q` that holds `v` twice. |
| 218 | `    do {` | `do`: starts the loop. One loop pass stores the vector 16 times, which is 256 B. |
| 219 | `        vst1q_u64(p + 0, q);` | `vst1q_u64(p + 0, q)` stores the 16 B of `q` to the write position: the bytes 0 to 15 of the current block of 256 B. |
| 220 | `        vst1q_u64(p + 2, q);` | Stores `q` to the bytes 16 to 31 of the block. |
| 221 | `        vst1q_u64(p + 4, q);` | Stores `q` to the bytes 32 to 47 of the block. |
| 222 | `        vst1q_u64(p + 6, q);` | Stores `q` to the bytes 48 to 63 of the block. |
| 223 | `        vst1q_u64(p + 8, q);` | Stores `q` to the bytes 64 to 79 of the block. |
| 224 | `        vst1q_u64(p + 10, q);` | Stores `q` to the bytes 80 to 95 of the block. |
| 225 | `        vst1q_u64(p + 12, q);` | Stores `q` to the bytes 96 to 111 of the block. |
| 226 | `        vst1q_u64(p + 14, q);` | Stores `q` to the bytes 112 to 127 of the block. |
| 227 | `        vst1q_u64(p + 16, q);` | Stores `q` to the bytes 128 to 143 of the block. |
| 228 | `        vst1q_u64(p + 18, q);` | Stores `q` to the bytes 144 to 159 of the block. |
| 229 | `        vst1q_u64(p + 20, q);` | Stores `q` to the bytes 160 to 175 of the block. |
| 230 | `        vst1q_u64(p + 22, q);` | Stores `q` to the bytes 176 to 191 of the block. |
| 231 | `        vst1q_u64(p + 24, q);` | Stores `q` to the bytes 192 to 207 of the block. |
| 232 | `        vst1q_u64(p + 26, q);` | Stores `q` to the bytes 208 to 223 of the block. |
| 233 | `        vst1q_u64(p + 28, q);` | Stores `q` to the bytes 224 to 239 of the block. |
| 234 | `        vst1q_u64(p + 30, q);` | Stores `q` to the bytes 240 to 255 of the block. gcc compiled the 16 stores to 8 `stp` instructions per loop pass. Each `stp` stores the 16-byte register `q31` twice, which is 32 B [Ref1]. The old `k_write` was a plain C loop. gcc compiled it to a loop of SVE instructions [Ref1]. |
| 235 | `        p += 32;` | Moves the write position forward by 32 elements, which is 256 B. |
| 236 | `    } while (p < end);` | Repeats the loop while the write position is below the end. In the listing one loop pass is 11 instructions for 256 B: 1 `add`, 8 `stp`, 1 `cmp` and 1 branch [Ref1]. |
| 237 | `}` | Ends the function `k_write`. |

### Function `k_copy`: the new copy kernel (lines 239 to 285)

| Line | Source | Explanation |
|---:|---|---|
| 239 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_copy`, the new copy kernel. It copies `n` elements from `s` to `d`. `restrict` tells the compiler that the two buffers do not overlap. A process with the kernel `read` does not call this function. |
| 240 | `{` | Opens the body of `k_copy`. |
| 241 | `    uint64_t *dp = d;` | `dp`: the write position. It starts at the first element of `d`. |
| 242 | `    const uint64_t *sp = s;` | `sp`: the read position. It starts at the first element of `s`. |
| 243 | `    const uint64_t *end = s + n;` | `end`: the first address after the source buffer `s`. |
| 244 | `    do {` | `do`: starts the loop. One loop pass loads 256 B from the source buffer and then stores them to the destination buffer. |
| 245 | `        uint64x2_t v0 = vld1q_u64(sp + 0);` | `vld1q_u64(sp + 0)` loads the bytes 0 to 15 of the current source block of 256 B into the vector variable `v0`. The 16 loads follow the same pattern as in `k_read` (lines 189 to 204). |
| 246 | `        uint64x2_t v1 = vld1q_u64(sp + 2);` | Loads the bytes 16 to 31 of the source block into `v1`. |
| 247 | `        uint64x2_t v2 = vld1q_u64(sp + 4);` | Loads the bytes 32 to 47 of the source block into `v2`. |
| 248 | `        uint64x2_t v3 = vld1q_u64(sp + 6);` | Loads the bytes 48 to 63 of the source block into `v3`. |
| 249 | `        uint64x2_t v4 = vld1q_u64(sp + 8);` | Loads the bytes 64 to 79 of the source block into `v4`. |
| 250 | `        uint64x2_t v5 = vld1q_u64(sp + 10);` | Loads the bytes 80 to 95 of the source block into `v5`. |
| 251 | `        uint64x2_t v6 = vld1q_u64(sp + 12);` | Loads the bytes 96 to 111 of the source block into `v6`. |
| 252 | `        uint64x2_t v7 = vld1q_u64(sp + 14);` | Loads the bytes 112 to 127 of the source block into `v7`. |
| 253 | `        uint64x2_t v8 = vld1q_u64(sp + 16);` | Loads the bytes 128 to 143 of the source block into `v8`. |
| 254 | `        uint64x2_t v9 = vld1q_u64(sp + 18);` | Loads the bytes 144 to 159 of the source block into `v9`. |
| 255 | `        uint64x2_t v10 = vld1q_u64(sp + 20);` | Loads the bytes 160 to 175 of the source block into `v10`. |
| 256 | `        uint64x2_t v11 = vld1q_u64(sp + 22);` | Loads the bytes 176 to 191 of the source block into `v11`. |
| 257 | `        uint64x2_t v12 = vld1q_u64(sp + 24);` | Loads the bytes 192 to 207 of the source block into `v12`. |
| 258 | `        uint64x2_t v13 = vld1q_u64(sp + 26);` | Loads the bytes 208 to 223 of the source block into `v13`. |
| 259 | `        uint64x2_t v14 = vld1q_u64(sp + 28);` | Loads the bytes 224 to 239 of the source block into `v14`. |
| 260 | `        uint64x2_t v15 = vld1q_u64(sp + 30);` | Loads the bytes 240 to 255 of the source block into `v15`. These are the 16 loads of one loop pass: 256 B, each byte once. |
| 261 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | The same empty asm statement as in `k_read` (line 205). It names the 16 loaded vectors as inputs in vector registers and adds no instruction. The source comment (lines 178 to 182) says that the statement does not fix the order of the loads and the stores: gcc may move code across it. The comment reports what was observed with gcc 14.2.0: with the statement the 8 `ldp` loads of a loop pass come before the 8 `stp` stores, and without it loads and stores alternate. The listing of `bw_new` shows the 8 `ldp` before the 8 `stp` [Ref1]. This line names `v0` to `v3`. |
| 262 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the list of inputs: `v4` to `v7`. |
| 263 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the list of inputs: `v8` to `v11`. |
| 264 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Ends the list of inputs and the statement: `v12` to `v15`. |
| 265 | `        vst1q_u64(dp + 0, v0);` | `vst1q_u64(dp + 0, v0)` stores the 16 B of `v0` to the write position: the bytes 0 to 15 of the current destination block of 256 B. |
| 266 | `        vst1q_u64(dp + 2, v1);` | Stores `v1` to the bytes 16 to 31 of the destination block. |
| 267 | `        vst1q_u64(dp + 4, v2);` | Stores `v2` to the bytes 32 to 47 of the destination block. |
| 268 | `        vst1q_u64(dp + 6, v3);` | Stores `v3` to the bytes 48 to 63 of the destination block. |
| 269 | `        vst1q_u64(dp + 8, v4);` | Stores `v4` to the bytes 64 to 79 of the destination block. |
| 270 | `        vst1q_u64(dp + 10, v5);` | Stores `v5` to the bytes 80 to 95 of the destination block. |
| 271 | `        vst1q_u64(dp + 12, v6);` | Stores `v6` to the bytes 96 to 111 of the destination block. |
| 272 | `        vst1q_u64(dp + 14, v7);` | Stores `v7` to the bytes 112 to 127 of the destination block. |
| 273 | `        vst1q_u64(dp + 16, v8);` | Stores `v8` to the bytes 128 to 143 of the destination block. |
| 274 | `        vst1q_u64(dp + 18, v9);` | Stores `v9` to the bytes 144 to 159 of the destination block. |
| 275 | `        vst1q_u64(dp + 20, v10);` | Stores `v10` to the bytes 160 to 175 of the destination block. |
| 276 | `        vst1q_u64(dp + 22, v11);` | Stores `v11` to the bytes 176 to 191 of the destination block. |
| 277 | `        vst1q_u64(dp + 24, v12);` | Stores `v12` to the bytes 192 to 207 of the destination block. |
| 278 | `        vst1q_u64(dp + 26, v13);` | Stores `v13` to the bytes 208 to 223 of the destination block. |
| 279 | `        vst1q_u64(dp + 28, v14);` | Stores `v14` to the bytes 224 to 239 of the destination block. |
| 280 | `        vst1q_u64(dp + 30, v15);` | Stores `v15` to the bytes 240 to 255 of the destination block. The 16 stores write the 256 B that the 16 loads read. |
| 281 | `        sp += 32;` | Moves the read position forward by 32 elements, which is 256 B. |
| 282 | `        dp += 32;` | Moves the write position forward by 32 elements, which is 256 B. |
| 283 | `    } while (sp < end);` | Repeats the loop while the read position is below the end of the source buffer. In the listing one loop pass is 20 instructions for 256 B: 8 `ldp`, 8 `stp`, 2 `add`, 1 `cmp` and 1 branch [Ref1]. |
| 284 | `}` | Ends the function `k_copy`. |

### The asm kernels: comment and the test for 64-bit Arm (lines 286 to 296)

| Line | Source | Explanation |
|---:|---|---|
| 286 | `/*` | Comment: starts the comment on the three asm kernels. It ends in line 293. |
| 287 | ` * asm kernels: the whole hot loop is one inline-asm block, so the compiler` | Comment: in an asm kernel the whole loop is one block of assembly text inside a C function (inline asm). The compiler copies the loop. It only puts a register in the place of each name such as `%[p]` [Ref1]. The old source holds the same text for these kernels [Ref2]. Both binaries hold the same instructions for them [Ref1]. |
| 288 | ` * cannot add arithmetic, reorder, or drop anything. Each iteration moves` | Comment: so the compiler cannot add arithmetic, change the order or remove an instruction. The next sentence of the comment starts here: each loop pass (iteration) moves 256 B. |
| 289 | ` * 256 B with 8 ldp/stp of q registers (16 B each). The loop body is:` | Comment: the 256 B are moved with 8 `ldp` or `stp` instructions on `q` registers of 16 B each. `ldp q` loads two such registers (32 B), and `stp q` stores two (32 B). |
| 290 | ` * 8 x ldp or stp, add, cmp, b.lo. Callers guarantee n * 8 is a multiple of` | Comment: the loop body is 8 `ldp` or `stp`, then `add`, `cmp` and the branch `b.lo`. This fits `k_asmread` and `k_asmwrite`. `k_asmcopy` has 8 `ldp`, 8 `stp` and 2 `add` (lines 351 to 368). The callers guarantee that `n * 8` bytes is a multiple of 256 and not 0. `main` checks this (line 549). |
| 291 | ` * 256 and non-zero. v8-v15 are callee-saved in AAPCS64: naming them as` | Comment: `v8` to `v15` are callee-saved in AAPCS64, the calling rules of 64-bit Arm. These rules say that a function must keep the lower halves (`d8` to `d15`) of the registers `v8` to `v15` for its caller. |
| 292 | ` * clobbers makes gcc save d8-d15 once per call, which is outside the loop.` | Comment: the asm blocks name these registers as changed (as clobbers, line 317). So gcc saves `d8` to `d15` before the loop and restores them after it, once per call [Ref1]. |
| 293 | ` */` | Comment: the end of the comment on the asm kernels. |
| 294 | `#if defined(__aarch64__)` | Compiles lines 295 to 376 only for 64-bit Arm (AArch64). The compiler defines `__aarch64__` for that instruction set. CRB is an AArch64 machine, so this branch is used and `HAVE_ASM_KERNELS` is 1. Proof: the listing of `bw_new` holds `k_asmread`, `k_asmwrite` and `k_asmcopy` [Ref1]. |
| 295 | `#define HAVE_ASM_KERNELS 1` | `HAVE_ASM_KERNELS` is 1 when the three asm kernels exist. Line 430 and line 551 test it. |

### Function `k_asmread`: the hand-written load-only loop (lines 297 to 320)

| Line | Source | Explanation |
|---:|---|---|
| 297 | `__attribute__((noinline)) static void k_asmread(const uint64_t *a, size_t n)` | Starts the function `k_asmread`, the hand-written load-only loop. `a` is the buffer, and `n` is its number of 8-byte elements. The function returns nothing. |
| 298 | `{` | Opens the body of `k_asmread`. |
| 299 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at the first element of the buffer. |
| 300 | `    const uint64_t *end = a + n;` | `end`: the address directly after the last element. |
| 301 | `    __asm__ volatile(` | Starts the asm statement: the assembly text (lines 302 to 313) and its three operand lists (lines 314 to 318). `volatile` forbids the compiler to remove the statement. |
| 302 | `        "1:\n\t"` | The label `1`: the start of the loop. The characters `\n\t` end each line of the assembly text with a line break and a tab. |
| 303 | `        "ldp q0, q1, [%[p]]\n\t"` | `ldp` loads 32 B from the address in `p` into the two 16-byte vector registers `q0` and `q1`. The compiler puts the register that holds `p` in the place of `%[p]`. |
| 304 | `        "ldp q2, q3, [%[p], #32]\n\t"` | Loads the 32 B at the address `p` plus 32 into `q2` and `q3`. |
| 305 | `        "ldp q4, q5, [%[p], #64]\n\t"` | Loads the 32 B at `p` plus 64 into `q4` and `q5`. |
| 306 | `        "ldp q6, q7, [%[p], #96]\n\t"` | Loads the 32 B at `p` plus 96 into `q6` and `q7`. |
| 307 | `        "ldp q8, q9, [%[p], #128]\n\t"` | Loads the 32 B at `p` plus 128 into `q8` and `q9`. |
| 308 | `        "ldp q10, q11, [%[p], #160]\n\t"` | Loads the 32 B at `p` plus 160 into `q10` and `q11`. |
| 309 | `        "ldp q12, q13, [%[p], #192]\n\t"` | Loads the 32 B at `p` plus 192 into `q12` and `q13`. |
| 310 | `        "ldp q14, q15, [%[p], #224]\n\t"` | Loads the 32 B at `p` plus 224 into `q14` and `q15`. The 8 loads of lines 303 to 310 read 256 B, each byte once. The loaded values are never used. The next loop pass overwrites them. |
| 311 | `        "add %[p], %[p], #256\n\t"` | `add` moves the pointer forward by 256 B. |
| 312 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the pointer with `end` and sets the condition flags. |
| 313 | `        "b.lo 1b\n\t"` | `b.lo 1b` jumps back to the label `1` (line 302) while the pointer is below `end`. So one loop pass is 11 instructions per 256 B: 8 loads, `add`, `cmp` and the branch. The loop of `k_read` also has 11 instructions per 256 B. In the listing the two loops differ in the register numbers and in the form of the compare and the branch [Ref1]. |
| 314 | `        : [p] "+r"(p)` | First operand list, the outputs: `p` is read and changed in a register (`+r`). In the assembly text its name is `%[p]`. |
| 315 | `        : [end] "r"(end)` | Second list, the inputs: `end` is read in a register (`r`). |
| 316 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | Third list: what the text changes or accesses without an operand. This line names the registers `v0` to `v7`. `v0` and `q0` are two names of the same 16-byte register. |
| 317 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the list: the registers `v8` to `v15`. The compiler saves the lower halves of these 8 registers once per call (lines 291 to 292). |
| 318 | `          "memory", "cc");` | Ends the list and the asm statement. `memory`: the text accesses memory that no operand names. `cc`: the text changes the condition flags. |
| 319 | `}` | Ends the function `k_asmread`. |

### Function `k_asmwrite`: the hand-written store-only loop (lines 321 to 343)

| Line | Source | Explanation |
|---:|---|---|
| 321 | `__attribute__((noinline)) static void k_asmwrite(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_asmwrite`, the hand-written store-only loop. It stores the value `v` into all `n` elements of the buffer `a`. A process with the kernel `read` does not call this function. |
| 322 | `{` | Opens the body of `k_asmwrite`. |
| 323 | `    uint64_t *p = a;` | `p`: the write pointer. It starts at the first element of the buffer. |
| 324 | `    const uint64_t *end = a + n;` | `end`: the address directly after the last element. |
| 325 | `    __asm__ volatile(` | Starts the asm statement: the assembly text and its operand lists, as in line 301. |
| 326 | `        "dup v0.2d, %[v]\n\t"` | `dup` fills the register `v0` with two copies of the 64-bit value `v`. It runs once, before the loop. |
| 327 | `        "1:\n\t"` | The label `1`: the start of the loop. |
| 328 | `        "stp q0, q0, [%[p]]\n\t"` | `stp` stores the register `q0` twice, which is 32 B, to the address in `p`. |
| 329 | `        "stp q0, q0, [%[p], #32]\n\t"` | Stores `q0` twice (32 B) to the address `p` plus 32. |
| 330 | `        "stp q0, q0, [%[p], #64]\n\t"` | Stores `q0` twice (32 B) to `p` plus 64. |
| 331 | `        "stp q0, q0, [%[p], #96]\n\t"` | Stores `q0` twice (32 B) to `p` plus 96. |
| 332 | `        "stp q0, q0, [%[p], #128]\n\t"` | Stores `q0` twice (32 B) to `p` plus 128. |
| 333 | `        "stp q0, q0, [%[p], #160]\n\t"` | Stores `q0` twice (32 B) to `p` plus 160. |
| 334 | `        "stp q0, q0, [%[p], #192]\n\t"` | Stores `q0` twice (32 B) to `p` plus 192. |
| 335 | `        "stp q0, q0, [%[p], #224]\n\t"` | Stores `q0` twice (32 B) to `p` plus 224. The 8 stores of lines 328 to 335 write 256 B, each byte once. |
| 336 | `        "add %[p], %[p], #256\n\t"` | `add` moves the pointer forward by 256 B. |
| 337 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the pointer with `end`. |
| 338 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the pointer is below `end`. One loop pass is 11 instructions per 256 B: 8 stores, `add`, `cmp` and the branch. |
| 339 | `        : [p] "+r"(p)` | The outputs: `p` is read and changed in a register. |
| 340 | `        : [end] "r"(end), [v] "r"(v)` | The inputs: `end` and `v` are read in registers. |
| 341 | `        : "v0", "memory", "cc");` | What the text changes without an operand: the register `v0`, memory and the condition flags. This ends the asm statement. |
| 342 | `}` | Ends the function `k_asmwrite`. |

### Function `k_asmcopy`: the hand-written copy loop (lines 344 to 380)

| Line | Source | Explanation |
|---:|---|---|
| 344 | `__attribute__((noinline)) static void k_asmcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy`, the hand-written copy loop. It copies `n` elements from `s` to `d`. `restrict` tells the compiler that the two buffers do not overlap. A process with the kernel `read` does not call this function. |
| 345 | `{` | Opens the body of `k_asmcopy`. |
| 346 | `    uint64_t *dp = d;` | `dp`: the write pointer. It starts at the first element of `d`. |
| 347 | `    const uint64_t *sp = s;` | `sp`: the read pointer. It starts at the first element of `s`. |
| 348 | `    const uint64_t *end = s + n;` | `end`: the address directly after the last element of `s`. |
| 349 | `    __asm__ volatile(` | Starts the asm statement: the assembly text and its operand lists, as in line 301. |
| 350 | `        "1:\n\t"` | The label `1`: the start of the loop. |
| 351 | `        "ldp q0, q1, [%[s]]\n\t"` | `ldp` loads 32 B from the address in the read pointer into `q0` and `q1`. In the assembly text the read pointer has the name `%[s]`. |
| 352 | `        "ldp q2, q3, [%[s], #32]\n\t"` | Loads the 32 B at the read pointer plus 32 into `q2` and `q3`. |
| 353 | `        "ldp q4, q5, [%[s], #64]\n\t"` | Loads the 32 B at the read pointer plus 64 into `q4` and `q5`. |
| 354 | `        "ldp q6, q7, [%[s], #96]\n\t"` | Loads the 32 B at the read pointer plus 96 into `q6` and `q7`. |
| 355 | `        "ldp q8, q9, [%[s], #128]\n\t"` | Loads the 32 B at the read pointer plus 128 into `q8` and `q9`. |
| 356 | `        "ldp q10, q11, [%[s], #160]\n\t"` | Loads the 32 B at the read pointer plus 160 into `q10` and `q11`. |
| 357 | `        "ldp q12, q13, [%[s], #192]\n\t"` | Loads the 32 B at the read pointer plus 192 into `q12` and `q13`. |
| 358 | `        "ldp q14, q15, [%[s], #224]\n\t"` | Loads the 32 B at the read pointer plus 224 into `q14` and `q15`. The 8 loads of lines 351 to 358 read 256 B. All of them come before the first store. |
| 359 | `        "stp q0, q1, [%[d]]\n\t"` | `stp` stores `q0` and `q1` (32 B) to the address in the write pointer. In the assembly text the write pointer has the name `%[d]`. |
| 360 | `        "stp q2, q3, [%[d], #32]\n\t"` | Stores `q2` and `q3` to the write pointer plus 32. |
| 361 | `        "stp q4, q5, [%[d], #64]\n\t"` | Stores `q4` and `q5` to the write pointer plus 64. |
| 362 | `        "stp q6, q7, [%[d], #96]\n\t"` | Stores `q6` and `q7` to the write pointer plus 96. |
| 363 | `        "stp q8, q9, [%[d], #128]\n\t"` | Stores `q8` and `q9` to the write pointer plus 128. |
| 364 | `        "stp q10, q11, [%[d], #160]\n\t"` | Stores `q10` and `q11` to the write pointer plus 160. |
| 365 | `        "stp q12, q13, [%[d], #192]\n\t"` | Stores `q12` and `q13` to the write pointer plus 192. |
| 366 | `        "stp q14, q15, [%[d], #224]\n\t"` | Stores `q14` and `q15` to the write pointer plus 224. The 8 stores of lines 359 to 366 write the 256 B that the 8 loads read. |
| 367 | `        "add %[s], %[s], #256\n\t"` | `add` moves the read pointer forward by 256 B. |
| 368 | `        "add %[d], %[d], #256\n\t"` | `add` moves the write pointer forward by 256 B. |
| 369 | `        "cmp %[s], %[end]\n\t"` | `cmp` compares the read pointer with `end`. |
| 370 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the read pointer is below `end`. One loop pass is 20 instructions per 256 B: 8 loads, 8 stores, 2 `add`, `cmp` and the branch. |
| 371 | `        : [s] "+r"(sp), [d] "+r"(dp)` | The outputs: the two pointers `sp` and `dp` are read and changed in registers. In the assembly text their names are `%[s]` and `%[d]`. |
| 372 | `        : [end] "r"(end)` | The input: `end` is read in a register. |
| 373 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | What the text changes without an operand. This line names the registers `v0` to `v7`. |
| 374 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the list: the registers `v8` to `v15`. |
| 375 | `          "memory", "cc");` | Ends the list and the asm statement: memory and the condition flags. |
| 376 | `}` | Ends the function `k_asmcopy`. |
| 377 | `#else` | The other case of the `#if` of line 294: a machine that is not 64-bit Arm. The three asm kernels would then not be compiled. The build on CRB does not use this case. |
| 378 | `#define HAVE_ASM_KERNELS 0` | `HAVE_ASM_KERNELS` would then be 0, and `main` would refuse to run the asm kernels (line 551). |
| 379 | `#endif` | Ends the `#if` of line 294. |

### The old `pass`, kept as text inside a comment (not compiled) (lines 381 to 416)

| Line | Source | Explanation |
|---:|---|---|
| 381 | `/*` | Comment: opens a second C comment that ends in line 415. It keeps the old `pass` as a record. The compiler reads nothing between these two lines. |
| 382 | ` * History: pass() as it was until 2026-11-13, when the old k_read returned a` | Comment: history. The comment holds `pass` as it was until 2026-11-13, when the old `k_read` returned a sum. |
| 383 | ` * sum. Its comment was: "One pass over the thread's buffer; returns bytes` | Comment: quotes the old comment of `pass`. One pass over the buffer of the thread, and `pass` returns the bytes moved. |
| 384 | ` * moved. The sink is per thread (on its stack) so the read kernels of 120` | Comment, quoted old text: the sink is per thread, on its stack. The sink is the variable that received the sum of the old `k_read`. |
| 385 | ` * threads do not all store to one shared cache line." worker() had a local` | Comment, quoted old text: so the read kernels of 120 threads do not all store to one shared cache line. The next sentence starts here: the old `worker` had a local variable (continued in line 386). |
| 386 | ` * "volatile uint64_t sink" and passed "&sink" in its two pass() calls.` | Comment: that variable was `volatile uint64_t sink`. The old `worker` passed its address (`&sink`) in its two calls of `pass`. |
| 387 | ` *` | Comment: an empty line inside the comment. The text of the old `pass` follows. |
| 388 | `static uint64_t pass(enum kernel k, struct thread *t, size_t n, uint64_t v, volatile uint64_t *sink)` | Comment, old code that is not compiled: the first line of the old `pass`. Its fifth parameter `sink` pointed to a variable on the stack of the thread. |
| 389 | `{` | Comment, old code that is not compiled: opens the body of the old `pass`. |
| 390 | `    switch (k) {` | Comment, old code that is not compiled: the old `pass` chose the kernel by the value of `k`. |
| 391 | `    case K_READ:` | Comment, old code that is not compiled: the case of the kernel `read`. |
| 392 | `        *sink = k_read(t->a, n);` | Comment, old code that is not compiled: the old `pass` stored the sum of the old read kernel to the variable that `sink` pointed to, once per pass. |
| 393 | `        return cfg.bytes;` | Comment, old code that is not compiled: the old `pass` counted the buffer size once for `read`. |
| 394 | `    case K_WRITE:` | Comment, old code that is not compiled: the case of the kernel `write`. |
| 395 | `        k_write(t->a, n, v);` | Comment, old code that is not compiled: the call of `k_write`. |
| 396 | `        return cfg.bytes;` | Comment, old code that is not compiled: the buffer size was counted once. |
| 397 | `    case K_COPY:` | Comment, old code that is not compiled: the case of the kernel `copy`. |
| 398 | `        k_copy(t->b, t->a, n);` | Comment, old code that is not compiled: the call of `k_copy`. |
| 399 | `        return 2 * cfg.bytes;` | Comment, old code that is not compiled: the buffer size was counted twice. |
| 400 | `#if HAVE_ASM_KERNELS` | Comment, old code that is not compiled: this `#if` is inside the comment and has no effect. |
| 401 | `    case K_ASMREAD:` | Comment, old code that is not compiled: the case of the kernel `asmread`. |
| 402 | `        k_asmread(t->a, n);` | Comment, old code that is not compiled: the call of `k_asmread`. |
| 403 | `        return cfg.bytes;` | Comment, old code that is not compiled: the buffer size was counted once. |
| 404 | `    case K_ASMWRITE:` | Comment, old code that is not compiled: the case of the kernel `asmwrite`. |
| 405 | `        k_asmwrite(t->a, n, v);` | Comment, old code that is not compiled: the call of `k_asmwrite`. |
| 406 | `        return cfg.bytes;` | Comment, old code that is not compiled: the buffer size was counted once. |
| 407 | `    case K_ASMCOPY:` | Comment, old code that is not compiled: the case of the kernel `asmcopy`. |
| 408 | `        k_asmcopy(t->b, t->a, n);` | Comment, old code that is not compiled: the call of `k_asmcopy`. |
| 409 | `        return 2 * cfg.bytes;` | Comment, old code that is not compiled: the buffer size was counted twice. |
| 410 | `#endif` | Comment, old code that is not compiled: this `#endif` is inside the comment and has no effect. |
| 411 | `    default:` | Comment, old code that is not compiled: the case of every other value of `k`. |
| 412 | `        return 0;` | Comment, old code that is not compiled: 0 bytes were counted. |
| 413 | `    }` | Comment, old code that is not compiled: ends the `switch` of the old `pass`. |
| 414 | `}` | Comment, old code that is not compiled: ends the old `pass`. |
| 415 | ` */` | Comment: closes the comment that starts in line 381. |

### Function `pass`: one pass of the kernel `k` over the buffer (lines 417 to 445)

| Line | Source | Explanation |
|---:|---|---|
| 417 | `/* One pass over the thread's buffer; returns bytes moved. */` | Comment: `pass` makes one pass over the buffer of the thread and returns the bytes moved. |
| 418 | `static uint64_t pass(enum kernel k, struct thread *t, size_t n, uint64_t v)` | Starts the function `pass`. It runs the kernel `k` once over the whole buffer of thread `t`. It returns the number of bytes that the caller counts for this pass. `n` is the number of 8-byte elements. `v` is the value for the write kernels. This is the only `pass` that the compiler reads [Ref8]. It has no `sink` parameter. |
| 419 | `{` | Opens the body of `pass`. |
| 420 | `    switch (k) {` | Chooses the kernel by the value of `k`. |
| 421 | `    case K_READ:` | The case of the kernel `read`. |
| 422 | `        k_read(t->a, n);` | Calls `k_read`, the new read kernel, on buffer `a`. `k_read` returns no value, and nothing is stored after the call. The old `pass` stored the sum of the old `k_read` at this place [Ref2]. |
| 423 | `        return cfg.bytes;` | The pass counts `cfg.bytes`, the buffer size, once. It is 268435456 bytes (256 MiB) in the whole-chip test [Ref5]. The count is the size that the kernel was asked to read. Nothing is counted inside the kernel. |
| 424 | `    case K_WRITE:` | The case of the kernel `write`. |
| 425 | `        k_write(t->a, n, v);` | Fills buffer `a` with the value `v` (`k_write`). |
| 426 | `        return cfg.bytes;` | The pass counts the buffer size once. |
| 427 | `    case K_COPY:` | The case of the kernel `copy`. |
| 428 | `        k_copy(t->b, t->a, n);` | Copies buffer `a` to buffer `b` (`k_copy`). |
| 429 | `        return 2 * cfg.bytes;` | The pass counts the buffer size twice: the bytes read plus the bytes written. |
| 430 | `#if HAVE_ASM_KERNELS` | Compiles lines 431 to 439 only when the asm kernels exist (`HAVE_ASM_KERNELS` is 1, on 64-bit Arm). This is true on CRB: `bw_new` holds the three asm kernels [Ref1]. |
| 431 | `    case K_ASMREAD:` | The case of the kernel `asmread`. |
| 432 | `        k_asmread(t->a, n);` | Calls `k_asmread`, the hand-written load-only loop, on buffer `a`. |
| 433 | `        return cfg.bytes;` | The pass counts the buffer size once. |
| 434 | `    case K_ASMWRITE:` | The case of the kernel `asmwrite`. |
| 435 | `        k_asmwrite(t->a, n, v);` | Fills buffer `a` with the value `v`, with the hand-written loop (`k_asmwrite`). |
| 436 | `        return cfg.bytes;` | The pass counts the buffer size once, as for `write`. |
| 437 | `    case K_ASMCOPY:` | The case of the kernel `asmcopy`. |
| 438 | `        k_asmcopy(t->b, t->a, n);` | Copies buffer `a` to buffer `b`, with the hand-written loop (`k_asmcopy`). |
| 439 | `        return 2 * cfg.bytes;` | The pass counts the buffer size twice, as for `copy`. |
| 440 | `#endif` | Ends the `#if` of line 430. |
| 441 | `    default:` | The case of every other value of `k`. |
| 442 | `        return 0;` | Counts 0 bytes. This line is reached only for an asm kernel in a build without the asm kernels. `main` stops such a run before it creates the threads (line 551). On CRB all six kernels have a case, so this line is not reached there. |
| 443 | `    }` | Ends the `switch` of line 420. |
| 444 | `}` | Ends the function `pass`. |

### Function `worker`: start values, pinning and first touch of the buffers (lines 446 to 464)

| Line | Source | Explanation |
|---:|---|---|
| 446 | `static void *worker(void *arg)` | Starts the function `worker`. Each thread that `main` creates (line 566) runs it once. |
| 447 | `{` | Opens the body of `worker`. |
| 448 | `    struct thread *t = arg;` | `t`: the entry of this thread in the thread table. `main` filled its index and its CPU (lines 564 to 565). |
| 449 | `    size_t n = cfg.bytes / 8;` | `n`: the number of 8-byte elements in the buffer. It is 33554432 for a buffer of 256 MiB. |
| 450 | `    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */` | Comment: the store value is known only when the program runs, and its 8 bytes are not all equal. So the compiler cannot turn the write loop into a call of `memset`, the library function that fills memory with one byte value. |
| 451 | `    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;` | `v`: the value that the write kernels store. It is the process id plus the thread index plus 1, times a fixed 64-bit constant. So the compiler does not know it. The read kernels do not use it. |
| 452 | `    uint64_t passes_per_check = CHECK_BYTES / cfg.bytes;` | `passes_per_check`: the number of passes between two clock reads. It is 8 MiB (`CHECK_BYTES`) divided by the buffer size, rounded down. A buffer of 3 MiB, for example, gives 2 passes, which is 6 MiB. So for a buffer below 8 MiB that does not divide 8 MiB, the clock is read after less than 8 MiB. The comment of line 24 says at least 8 MiB. |
| 453 | `    if (passes_per_check == 0)` | Tests whether the division gave 0. That is the case for every buffer above 8 MiB. |
| 454 | `        passes_per_check = 1;` | The value is then 1. For a buffer of 256 MiB the thread therefore reads the clock after every pass. |
| 456 | `    if (cfg.ncpus)` | Tests whether a CPU list was given (option `--cpus`). |
| 457 | `        pin_cpu(t->cpu);` | If so, the thread pins itself to its CPU (`pin_cpu`). In part A thread i is pinned to CPU i, for i from 0 to 119 [Ref5]. The thread does this before it reserves its buffer. |
| 458 | `    t->a = alloc_buf(cfg.bytes);` | Reserves buffer `a` with `alloc_buf`: `cfg.bytes` bytes that start at a multiple of 2 MiB. |
| 459 | `    k_write(t->a, n, v); /* first touch by this thread */` | Writes `v` into every element of buffer `a` with the new `k_write` (line 213). This write is the first touch: Linux assigns the physical memory of the buffer now, while the thread already runs on its CPU. It is not timed. `bw_old` runs the old `k_write` at this place [Ref2]. The comment says: first touch by this thread. |
| 460 | `    if (cfg.run[K_COPY] \|\| cfg.run[K_ASMCOPY]) {` | Tests whether `copy` or `asmcopy` is selected. Only these two kernels use a second buffer. |
| 461 | `        t->b = alloc_buf(cfg.bytes);` | If so, the thread reserves the second buffer `b` of the same size. |
| 462 | `        k_write(t->b, n, v);` | Writes `v` into every element of `b` (first touch, not timed). A process with the kernel `read` has one buffer per thread. In part A it has a size of 256 MiB [Ref5]. |
| 463 | `    }` | Ends the `if` of line 460. |

### Function `worker`: the warm-up pass, the timed interval and the stop rule (lines 465 to 485)

| Line | Source | Explanation |
|---:|---|---|
| 465 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the six kernels in the order of line 26. |
| 466 | `        if (!cfg.run[k])` | Tests whether kernel `k` is selected. |
| 467 | `            continue;` | A kernel that is not selected is skipped. Every process of part A selects one kernel [Ref5]. So in part A no kernel is timed after another kernel in the same process. |
| 468 | `        for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions of this kernel. Each repetition is one timed interval. Part A passes `--reps 3`, so every process times 3 intervals [Ref5]. |
| 469 | `            pass(k, t, n, v); /* warm-up */` | The warm-up: one whole pass of the same kernel over the buffer. It runs before every timed interval, not only before the first one. It is not timed, and its byte count is dropped. |
| 470 | `            pthread_barrier_wait(&bar);` | First barrier. The thread waits here until all workers and the main thread (line 582) have arrived: 120 workers in part A [Ref5]. A thread that arrives early waits here and reads no memory. The barrier then releases all threads in one step. The timed interval of a thread starts after this release, at its own clock read (line 471). The program does not store the start times. So it does not show how far apart the starts of the threads are. |
| 471 | `            double t0 = now_s(), t1;` | `t0`: the clock read directly after the barrier. It is the start of the timed interval of this thread. Each thread has its own `t0`. `t1` will hold the clock read after the passes (line 476). |
| 472 | `            uint64_t bytes = 0, p = 0;` | `bytes` counts the bytes of this interval, and `p` counts its passes. Both start at 0. |
| 473 | `            do {` | Starts the loop of the timed work. Its body runs at least once. |
| 474 | `                for (uint64_t c = 0; c < passes_per_check; c++, p++)` | The inner `for` runs `passes_per_check` passes without a clock read between them. This is 1 pass in the whole-chip test (line 454). |
| 475 | `                    bytes += pass(k, t, n, v + p);` | Runs one pass and adds its byte count to `bytes`. For the kernel `read` each pass is one call of `k_read` over the whole buffer. `v + p` changes the stored value from pass to pass. Only the write kernels use it. |
| 476 | `                t1 = now_s();` | `t1`: the clock read after the passes. The clock is never read inside a pass. |
| 477 | `            } while (t1 - t0 < cfg.min_s);` | The stop rule. The loop repeats while less than `cfg.min_s` has passed after `t0`. With `--min-ms 500` that is 0.5 s [Ref5]. The test comes only after a whole pass. So every thread ends its interval at the end of a pass, at its own time. The interval of a thread is 0.5 s or longer. It exceeds 0.5 s by less than the time between its last two clock reads, which is one pass here. |
| 478 | `            t->res[k][rep].bytes = bytes;` | Stores the bytes that this thread counted, for this kernel and repetition. |
| 479 | `            t->res[k][rep].elapsed_s = t1 - t0;` | Stores the time `t1 - t0` of this thread. The interval ended at the last clock read of line 476. The time covers the passes and the clock reads between them. It does not cover the warm-up pass or the waits at the barrier. |
| 480 | `            pthread_barrier_wait(&bar);` | Second barrier. The thread waits here until all other workers have ended their interval and the main thread (line 583) has arrived. A thread that waits here runs no kernel. The threads that are still in their last pass continue without it. |
| 481 | `        }` | Ends the repetition loop of line 468. The next repetition starts with its warm-up pass directly after the barrier. The code has no sleep there. |
| 482 | `    }` | Ends the kernel loop of line 465. |
| 483 | `    return NULL;` | The thread ends after the last repetition of the last selected kernel. |
| 484 | `}` | Ends the function `worker`. |

### Function `usage`: print the options and stop (lines 486 to 495)

| Line | Source | Explanation |
|---:|---|---|
| 486 | `static void usage(void)` | Starts the function `usage`. It prints the list of options to the error output and ends the program with exit status 2. |
| 487 | `{` | Opens the body of `usage`. |
| 488 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to the error output. Its text is in lines 489 to 492. |
| 489 | `            "usage: bandwidth [--threads T --cpus LIST] [--bytes B] "` | Text of the message: the options for the thread count, the CPU list and the buffer size. |
| 490 | `            "[--kernel read\|write\|copy\|all\|asmread\|asmwrite\|asmcopy\|asmall] "` | Text of the message: the names that the option `--kernel` accepts. |
| 491 | `            "[--min-ms MS] [--reps R] [--no-thp] [--per-thread]\n"` | Text of the message: the options for the minimum time in ms, the number of repetitions, no 2 MiB pages, and one line per thread. |
| 492 | `            "  all kernels: loads/stores only, bytes must be a multiple of 256; the program builds on AArch64 only\n");` | Text of the message, second line: all kernels hold loads and stores only, the buffer size must be a multiple of 256, and the program builds on AArch64 only. This text is new against the old source [Ref2]. It does not change a measurement. This line ends the `fprintf` call. |
| 493 | `    exit(2);` | Ends the program with exit status 2. |
| 494 | `}` | Ends the function `usage`. |

### Function `main`: defaults and arguments (lines 496 to 544)

| Line | Source | Explanation |
|---:|---|---|
| 496 | `int main(int argc, char **argv)` | Starts the function `main`. It reads the arguments, starts the threads, and prints one rate row per timed interval. |
| 497 | `{` | Opens the body of `main`. |
| 498 | `    int threads_given = 0;` | `threads_given`: becomes 1 when the option `--threads` is given (line 511). The check of line 545 uses it. |
| 499 | `    cfg.bytes = 1UL << 20;` | Default before the arguments are read: a buffer of 1 MiB (1048576 bytes) per thread. |
| 500 | `    cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;` | Default: the three C kernels `read`, `write` and `copy` are selected. |
| 502 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments of the command line. |
| 503 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 504 | `        int more = i + 1 < argc;` | `more`: true when one more argument follows, which an option with a value needs. |
| 505 | `        if (!strcmp(a, "--no-thp")) {` | Tests whether the argument is `--no-thp`. `strcmp` returns 0 when two texts are equal. |
| 506 | `            cfg.use_thp = 0;` | `--no-thp` forbids 2 MiB pages for the buffers (line 131). Part A does not pass it [Ref5]. |
| 507 | `        } else if (!strcmp(a, "--per-thread")) {` | Tests for `--per-thread`. |
| 508 | `            cfg.per_thread = 1;` | `--per-thread` adds one output line per thread and repetition (line 606). Part A does not pass it [Ref5]. |
| 509 | `        } else if (!strcmp(a, "--threads") && more) {` | Tests for `--threads` with a value after it. |
| 510 | `            cfg.threads = atoi(argv[++i]);` | The number of threads. `atoi` turns the next argument into an integer, and `++i` steps over that argument. Part A passes 120 [Ref5]. |
| 511 | `            threads_given = 1;` | Notes that `--threads` was given. |
| 512 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 513 | `            parse_cpus(argv[++i]);` | The CPU list, read by `parse_cpus`. Part A passes `0-119` [Ref5]. |
| 514 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 515 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size of each thread, read by `parse_bytes`. Part A passes `256M` (256 MiB) [Ref5]. |
| 516 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Tests for `--min-ms` with a value after it. |
| 517 | `            cfg.min_s = atof(argv[++i]) / 1000.0;` | The minimum time of an interval. `atof` reads the value in ms, and the division by 1000 gives seconds. Part A passes 500, which gives 0.5 s [Ref5]. |
| 518 | `        } else if (!strcmp(a, "--reps") && more) {` | Tests for `--reps` with a value after it. |
| 519 | `            cfg.reps = atoi(argv[++i]);` | The number of timed intervals per kernel. Part A passes 3 [Ref5]. |
| 520 | `        } else if (!strcmp(a, "--kernel") && more) {` | Tests for `--kernel` with a value after it. |
| 521 | `            const char *k = argv[++i];` | `k`: the kernel name that follows `--kernel`. Every process of part A gets one of the six names `read`, `write`, `copy`, `asmread`, `asmwrite`, `asmcopy` [Ref5]. |
| 522 | `            memset(cfg.run, 0, sizeof cfg.run);` | First clears every selection: `memset` sets all flags of `cfg.run` to 0. Then one of the next lines selects by the name. |
| 523 | `            if (!strcmp(k, "all"))` | Tests for the name `all`. |
| 524 | `                cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;` | `all` selects the three C kernels `read`, `write` and `copy`. |
| 525 | `            else if (!strcmp(k, "read"))` | Tests for the name `read`. |
| 526 | `                cfg.run[K_READ] = 1;` | Selects the kernel `read` only. It is the function `k_read` of line 184, the new read kernel. |
| 527 | `            else if (!strcmp(k, "write"))` | Tests for the name `write`. |
| 528 | `                cfg.run[K_WRITE] = 1;` | Selects the kernel `write` only. |
| 529 | `            else if (!strcmp(k, "copy"))` | Tests for the name `copy`. |
| 530 | `                cfg.run[K_COPY] = 1;` | Selects the kernel `copy` only. |
| 531 | `            else if (!strcmp(k, "asmall"))` | Tests for the name `asmall`. |
| 532 | `                cfg.run[K_ASMREAD] = cfg.run[K_ASMWRITE] = cfg.run[K_ASMCOPY] = 1;` | `asmall` selects the three asm kernels. |
| 533 | `            else if (!strcmp(k, "asmread"))` | Tests for the name `asmread`. |
| 534 | `                cfg.run[K_ASMREAD] = 1;` | Selects the kernel `asmread` only. |
| 535 | `            else if (!strcmp(k, "asmwrite"))` | Tests for the name `asmwrite`. |
| 536 | `                cfg.run[K_ASMWRITE] = 1;` | Selects the kernel `asmwrite` only. |
| 537 | `            else if (!strcmp(k, "asmcopy"))` | Tests for the name `asmcopy`. |
| 538 | `                cfg.run[K_ASMCOPY] = 1;` | Selects the kernel `asmcopy` only. |
| 539 | `            else` | The case of every other name. |
| 540 | `                usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 541 | `        } else {` | The case of every other argument: an unknown option, or an option without its value. |
| 542 | `            usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 543 | `        }` | Ends the chain of tests that starts in line 505. |
| 544 | `    }` | Ends the loop over the arguments (line 502). |

### Function `main`: checks of the arguments (lines 545 to 557)

| Line | Source | Explanation |
|---:|---|---|
| 545 | `    if (threads_given && cfg.ncpus == 0) {` | Check: `--threads` is accepted only together with `--cpus`. The test is true when `--threads` was given and the CPU list is empty. |
| 546 | `        fprintf(stderr, "--threads requires --cpus\n");` | Prints `--threads requires --cpus` to the error output. |
| 547 | `        usage();` | Prints the option list and ends the program with exit status 2 (`usage`). |
| 548 | `    }` | Ends the `if` of line 545. |
| 549 | `    if (cfg.threads < 1 \|\| cfg.reps < 1 \|\| cfg.reps > MAX_REPS \|\| cfg.bytes == 0 \|\| cfg.bytes % 256 != 0)` | Checks of the values. The thread count must be 1 or more. The repetitions must be 1 to 32. The buffer size must not be 0, and it must be a multiple of 256 B. The kernels need the size check: each loop pass moves 256 B. |
| 550 | `        usage();` | A failed check prints the option list and ends the program with exit status 2 (`usage`). |
| 551 | `    if (!HAVE_ASM_KERNELS && (cfg.run[K_ASMREAD] \|\| cfg.run[K_ASMWRITE] \|\| cfg.run[K_ASMCOPY])) {` | Tests whether an asm kernel is selected in a build without the asm kernels (a machine that is not 64-bit Arm). On CRB `HAVE_ASM_KERNELS` is 1, so this test never stops the program there. |
| 552 | `        fprintf(stderr, "asm kernels need aarch64\n");` | Prints `asm kernels need aarch64` to the error output. |
| 553 | `        return 2;` | The program ends with exit status 2. |
| 554 | `    }` | Ends the `if` of line 551. |
| 555 | `    if (cfg.ncpus && cfg.threads > cfg.ncpus)` | Tests whether a CPU list was given and there are more threads than CPUs in it. |
| 556 | `        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);` | This only gives a warning on the error output, with both numbers. The program goes on. The list is then used again from its start (line 565). Part A has 120 threads and 120 CPUs [Ref5]. |

### Function `main`: thread table, barrier, threads and header lines (lines 558 to 576)

| Line | Source | Explanation |
|---:|---|---|
| 558 | `    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);` | Allocates the thread table with `calloc`: one `struct thread` per thread, filled with zeros. |
| 559 | `    if (!th \|\| pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {` | Tests the allocation and creates the barrier for `cfg.threads + 1` threads: the workers plus the main thread. In part A that is 121 [Ref5]. |
| 560 | `        perror("setup");` | On a failure of one of the two steps: `perror` prints the word `setup` and an error text. |
| 561 | `        return 2;` | On a failure: the program ends with exit status 2. |
| 562 | `    }` | Ends the `if` of line 559. |
| 563 | `    for (int i = 0; i < cfg.threads; i++) {` | Loop that creates the threads. |
| 564 | `        th[i].idx = i;` | Thread `i` gets the index `i`. |
| 565 | `        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;` | Thread `i` gets the CPU `cfg.cpus[i % cfg.ncpus]`: entry `i` of the CPU list. The list is used again from its start when there are more threads than entries. With the list `0-119` and 120 threads, thread i gets CPU i. Without a CPU list the value is -1, and the thread is not pinned (line 456). |
| 566 | `        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {` | Creates the thread. It starts `worker` immediately: the thread pins itself, reserves and writes its buffer, runs the first warm-up pass and then waits at the barrier. |
| 567 | `            perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and an error text. |
| 568 | `            return 2;` | The program then ends with exit status 2. |
| 569 | `        }` | Ends the `if` of line 566. |
| 570 | `    }` | Ends the loop of line 563. |
| 572 | `    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "` | Prints the first header line to the standard output. It starts with `#` and gives the rate formula: GB = 1e9 bytes, and `aggregate_GBps` is the sum of the bytes of all threads divided by the longest thread time. |
| 573 | `           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",` | Continues the text of the header line: copy counts the bytes read plus the bytes written. Then come the settings of the process: the thread count, the buffer size per thread in bytes, the minimum time in ms and the request for 2 MiB pages. |
| 574 | `           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");` | The four values of the header line. `thp=` shows `madvise` when the program asks for 2 MiB pages and `nohugepage` with `--no-thp`. This text shows the request only. It does not show that the buffers got such pages. |
| 575 | `    printf("kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,"` | Prints the second header line: the 10 column names of the interval rows. This line holds the first 7 names. |
| 576 | `           "per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps\n");` | Continues the column names: the lowest, the highest and the mean thread rate. |

### Function `main`: rate of each interval, output rows and end (lines 577 to 620)

| Line | Source | Explanation |
|---:|---|---|
| 577 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the kernels in the same order as the workers (line 465). |
| 578 | `        if (!cfg.run[k])` | The same skip rule as in the workers (line 466). |
| 579 | `            continue;` | Skips a kernel that is not selected. |
| 580 | `        double best = -1;` | `best`: will hold the highest total rate of the repetitions of this kernel. |
| 581 | `        for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions, as the main thread sees them. |
| 582 | `            pthread_barrier_wait(&bar); /* release the workers */` | First wait: the barrier opens when the main thread and all workers have arrived. Each worker arrives after its warm-up pass (line 470). The workers then start their timed interval (line 471). The comment says: release the workers. |
| 583 | `            pthread_barrier_wait(&bar); /* all workers finished this rep */` | Second wait: it returns when every worker has finished its interval (line 480). The main thread does no work during the interval. The program does not pin the main thread. The comment says: all workers finished this repetition. |
| 584 | `            uint64_t total = 0;` | `total`: the bytes of all threads in this interval. It starts at 0. While the main thread computes and prints the row (lines 584 to 603), the workers already run the warm-up pass of the next interval, when there is one. The next timed interval starts only after the main thread waits at the barrier again (line 582). |
| 585 | `            double max_el = 0, mn = 1e30, mx = 0, sum = 0;` | Start values for one row: `max_el` (the longest thread time), `mn` and `mx` (the lowest and the highest thread rate) and `sum` (the sum of the thread rates). `mn` starts at 1e30, a value above every rate. |
| 586 | `            for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 587 | `                struct result *r = &th[i].res[k][rep];` | `r`: the result of thread `i` for this kernel and repetition (lines 478 to 479). |
| 588 | `                double g = (double)r->bytes / r->elapsed_s / 1e9;` | `g`: the rate of this thread in GB/s. It is the bytes of the thread, divided by the time of the same thread, divided by 1e9. |
| 589 | `                total += r->bytes;` | Adds the bytes of the thread to `total`. |
| 590 | `                if (r->elapsed_s > max_el)` | Tests whether the time of this thread is the longest so far. |
| 591 | `                    max_el = r->elapsed_s;` | Keeps the longest thread time in `max_el`. |
| 592 | `                if (g < mn)` | Tests whether the rate of this thread is the lowest so far. |
| 593 | `                    mn = g;` | Keeps the lowest thread rate in `mn`. |
| 594 | `                if (g > mx)` | Tests whether the rate of this thread is the highest so far. |
| 595 | `                    mx = g;` | Keeps the highest thread rate in `mx`. |
| 596 | `                sum += g;` | Adds the thread rate to `sum` for the mean. |
| 597 | `            }` | Ends the loop over the threads (line 586). |
| 598 | `            double agg = (double)total / max_el / 1e9;` | `agg`: the total rate of the interval in GB/s. It is the bytes of all threads, divided by the longest thread time, divided by 1e9. The output column is `aggregate_GBps`. A thread with a shorter time adds no bytes after its own stop. So `agg` is never above the sum of the thread rates. It is lower when the times of the threads differ. |
| 599 | `            if (agg > best)` | Tests whether this `agg` is the highest of the repetitions so far. |
| 600 | `                best = agg;` | Keeps the highest `agg` in `best`. |
| 601 | `            printf("%s,%d,%lu,%d,%lu,%.4f,%.2f,%.2f,%.2f,%.2f\n", kernel_name[k], cfg.threads,` | Prints one interval row with 10 columns, separated by commas. This line holds the format and the values of columns 1 and 2: the kernel name and the thread count. |
| 602 | `                   (unsigned long)cfg.bytes, rep, (unsigned long)total, max_el, agg, mn, mx,` | The values of columns 3 to 9: the buffer size per thread in bytes, the repetition number (counted from 0), `total_bytes` (`total`), `elapsed_s` (`max_el`, with 4 decimals), `aggregate_GBps` (`agg`, with 2 decimals), and the lowest and the highest thread rate in GB/s (2 decimals each). |
| 603 | `                   sum / cfg.threads);` | The value of column 10: the mean thread rate in GB/s, which is `sum / cfg.threads`, with 2 decimals. |
| 604 | `        }` | Ends the repetition loop of line 581. |
| 605 | `        printf("%s,%d,%lu,best,,,%.2f,,,\n", kernel_name[k], cfg.threads, (unsigned long)cfg.bytes, best);` | After the last repetition: prints the `best` row. It has the word `best` in column 4 and the highest `agg` of the repetitions in column 7 (`aggregate_GBps`). The columns 5, 6, 8, 9 and 10 are empty. The statistics script of the rerun does not use this row [Ref7]. |
| 606 | `        if (cfg.per_thread) {` | Only with `--per-thread`: lines 609 to 613 print one more line per thread and repetition. Part A does not pass this option, so its output holds no such line [Ref5] [Ref6]. |
| 607 | `            /* thread,<index>,<cpu>,<kernel>,<rep>,<GB/s>: one line per thread and repetition, so that` | Comment: the form of the line: the word `thread`, the thread index, the CPU, the kernel, the repetition and the rate in GB/s. One line per thread and repetition. |
| 608 | `             * concurrent per-group totals can be formed from one repetition (reviewer's request) */` | Comment: the purpose of these lines. The rates of a group of threads that ran at the same time can be added from one repetition. The comment says that a reviewer asked for this. |
| 609 | `            for (int i = 0; i < cfg.threads; i++)` | Loop over the threads. |
| 610 | `                for (int rep = 0; rep < cfg.reps; rep++) {` | Loop over the repetitions. |
| 611 | `                    struct result *r = &th[i].res[k][rep];` | `r`: the result of thread `i` for this kernel and repetition. |
| 612 | `                    printf("thread,%d,%d,%s,%d,%.2f\n", i, th[i].cpu, kernel_name[k], rep, (double)r->bytes / r->elapsed_s / 1e9);` | Prints the line: the word `thread`, the thread index, the CPU, the kernel name, the repetition and the thread rate in GB/s with 2 decimals. The rate is the bytes of the thread, divided by the time of the same thread, divided by 1e9. |
| 613 | `                }` | Ends the loop of line 610. |
| 614 | `        }` | Ends the `if` of line 606. |
| 615 | `        fflush(stdout);` | `fflush` writes the buffered rows of this kernel to the output now. |
| 616 | `    }` | Ends the kernel loop of line 577. |
| 617 | `    for (int i = 0; i < cfg.threads; i++)` | Loop over the threads. |
| 618 | `        pthread_join(th[i].tid, NULL);` | Waits until worker thread `i` has ended (`pthread_join`). After the loop every worker has ended. |
| 619 | `    return 0;` | Ends the process with exit status 0. |
| 620 | `}` | Ends the function `main`. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: Build record of 2026-11-13, 18:12:22 UTC. Line 1: `mode=all`. Line 2: gcc 14.2.0. Line 3: the compiler flags. Line 15: sha256 of bandwidth.c at that build. Line 20: sha256 of bw_new. Lines 23 to 37: listing of `k_read` in bw_new. Lines 39 to 54: `k_write` in bw_new. Lines 56 to 79: `k_copy` in bw_new. Lines 81 to 153: the three `asm` kernels in bw_new. Lines 155 to 226: `k_read` in bw_old, with its loop in lines 183 to 198. Lines 228 to 255: `k_write` and `k_copy` in bw_old. Lines 257 to 329: the three `asm` kernels in bw_old.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c`: The old source. The command `diff bandwidth.orig.c bandwidth.c` shows every difference. New lines in this file: 10 (the include), 136 to 142 (start of the comment around the old kernels), 166 to 284 (end of that comment and the new kernels), 381 to 387 (start of the comment around the old `pass`) and 415 to 444 (end of that comment and the new `pass`). Changed lines in this file: 469 and 475 (the calls of `pass` without `&sink`) and 492 (the usage text). Removed: line 292 of the old source, the variable `sink` of the old `worker`. Line 264 of the old source is the store of the sum to `sink`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: Build record of 2026-11-13, 18:32:18 UTC. Line 1: `mode=probe`. Line 15: sha256 of bandwidth.c (f1985072...), equal to the sha256 of the source file that this page explains. Line 20: sha256 of bw_new (fd7c14df...), equal to line 20 of [Ref1]. The command `diff` of the two build records shows differences only in lines 1, 7, 10, 11 and 15 and in the load lines at the end. The listings are equal.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: Lines 19, 29 and 32: the gcc command that built bw_new from bandwidth.c. Line 31: the same command for bw_old. Lines 5, 6 and 56: with the mode `probe` the script ends before the timed runs, and with the mode `all` it goes on to them.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: The script of part A. Line 9: the script and its processes run under `taskset -c 0-119`. Lines 16 to 20: the sha256 check of bw_old and bw_new. Line 42: the arguments of every process. Lines 44 to 48: the 24 processes of one session and their order.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/threads120.csv`: Output of part A, session 1. Lines 8 to 14: the first bw_new process with the kernel `read`. Line 11 is the example row. The files of the same name under `k120-T72A2-20261117T221518Z` and `k120-T72A3-20261117T221827Z` hold the sessions 2 and 3. In each of the three files, lines 11 to 13 and lines 158 to 160 are the intervals of bw_new with the kernel `read`: 18 intervals in all. 16 of them have 178241142784 in field 5. The 2 others are lines 158 and 160 of session 3. No line of the three files starts with `thread,`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`: Lines 36 to 41: the statistics script reads the fields 1, 3, 4, 5, 7, 8 and 9 of the interval rows. It skips a row whose field 4 is not a number. The `best` row is such a row.
- [Ref8] Check made for this page: the command `gcc -fpreprocessed -dD -E -P bandwidth.c` (gcc 11.4.0) removes the comments and expands nothing. Its output holds one definition each of `k_read`, `k_write`, `k_copy` and `pass`: the ones of lines 184, 213, 239 and 418.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/probe.txt`: Line 3: `thp=[always] madvise never`, the huge page setting of CRB at the start of session 1 of part A. Lines 12 and 13: sha256 of bw_old and bw_new. The files of the same name under `k120-T72A2-20261117T221518Z` and `k120-T72A3-20261117T221827Z` hold the same text in their lines 3, 12 and 13.
- [Ref10] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
