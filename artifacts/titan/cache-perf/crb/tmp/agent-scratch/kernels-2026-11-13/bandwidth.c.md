# `bandwidth.c` explained

- Source file: `bandwidth.c` in this folder (C source, 620 lines, 21499 bytes).
- sha256 of the source when this page was built: `f198507208e0b010739660dbea178096e030c97cbf88e479d8cc3f1f11967824`.
- Role in the whole-chip test: Source of bw_new: the benchmark with the new read kernel (part A)
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>File header, includes, constants and data types</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  /*
  2   * bandwidth.c - multi-thread streaming bandwidth: read, write, copy.
  3   *
  4   * Every thread owns its buffers (allocated and first-touched by that thread),
  5   * so timing contains no page faults. All threads start on a barrier, run
  6   * whole passes over their buffer until --min-ms has elapsed, and record
  7   * bytes moved and their own elapsed time. GB means 1e9 bytes throughout.
  8   */</pre></td><td valign="top">The file comment gives the design of the benchmark.<ul><li>Each thread allocates its own buffers and writes them first. The comment says that a timed interval therefore holds no page fault.</li><li>All threads start an interval together at a barrier.</li><li>Each thread runs whole passes over its buffer until the time of <code>--min-ms</code> has passed.</li><li>GB means 1e9 bytes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  9  #define _GNU_SOURCE
 10  #include &lt;arm_neon.h&gt; /* NEON intrinsics for the C kernels: this file builds on AArch64 only */
 11  #include &lt;pthread.h&gt;
 12  #include &lt;sched.h&gt;
 13  #include &lt;stdint.h&gt;
 14  #include &lt;stdio.h&gt;
 15  #include &lt;stdlib.h&gt;
 16  #include &lt;string.h&gt;
 17  #include &lt;sys/mman.h&gt;
 18  #include &lt;time.h&gt;
 19  #include &lt;unistd.h&gt;
 20</pre></td><td valign="top"><code>_GNU_SOURCE</code> makes Linux-specific calls visible, for example <code>sched_setaffinity</code>. Line 10 includes the header of the NEON intrinsics. This line is new against the old source [Ref2]. The source comment says that the file therefore builds on AArch64 only.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 21  #define HUGE_BYTES (2UL &lt;&lt; 20)
 22  #define MAX_CPUS 1024
 23  #define MAX_REPS 32
 24  #define CHECK_BYTES (8UL &lt;&lt; 20) /* clock is read after at least this many bytes */
 25</pre></td><td valign="top"><ul><li><code>HUGE_BYTES</code>: 2 MiB (2,097,152 bytes), the size of one huge page. Buffers are aligned to it.</li><li><code>MAX_CPUS</code>: the CPU list holds at most 1024 entries.</li><li><code>MAX_REPS</code>: at most 32 timed intervals per kernel.</li><li><code>CHECK_BYTES</code>: 8 MiB (8,388,608 bytes). It sets how many passes a thread runs between two clock reads (lines 452 to 454).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 26  enum kernel { K_READ, K_WRITE, K_COPY, K_ASMREAD, K_ASMWRITE, K_ASMCOPY, K_COUNT };
 27  static const char *kernel_name[K_COUNT] = { "read", "write", "copy", "asmread", "asmwrite", "asmcopy" };
 28</pre></td><td valign="top">The six kernels. The numbers 0 to 5 fix the order in which one process runs the kernels that are selected. Each name is a value of <code>--kernel</code> and the first field of the rows that lines 601 and 605 print.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 29  static struct {
 30      int threads;
 31      int ncpus;
 32      int cpus[MAX_CPUS];
 33      uint64_t bytes;
 34      int run[K_COUNT];
 35      double min_s;
 36      int reps;
 37      int use_thp;
 38      int per_thread; /* --per-thread: one line per thread with its CPU and best GB/s */
 39  } cfg = { .threads = 1, .min_s = 0.5, .reps = 3, .use_thp = 1 };
 40</pre></td><td valign="top"><code>cfg</code> holds the settings of the process. <code>bytes</code> is the buffer size of one thread. <code>run[k]</code> is 1 when kernel <code>k</code> is selected. The defaults in line 39 are 1 thread, a minimum interval of 0.5 s, 3 repetitions and a request for huge pages.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 41  struct result {
 42      uint64_t bytes;
 43      double elapsed_s;
 44  };
 45</pre></td><td valign="top">One <code>result</code> holds one timed interval of one thread: the bytes that the thread moved and its own elapsed time in seconds.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 46  struct thread {
 47      int idx;
 48      int cpu;
 49      uint64_t *a, *b;
 50      struct result res[K_COUNT][MAX_REPS];
 51      pthread_t tid;
 52  };
 53</pre></td><td valign="top">One <code>thread</code> record per benchmark thread: its index, its CPU, its buffers <code>a</code> and <code>b</code>, and one <code>result</code> per kernel and repetition. Only the copy kernels use <code>b</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 54  static pthread_barrier_t bar;
 55</pre></td><td valign="top">The barrier that all benchmark threads and <code>main</code> share. Line 559 sets its size to the number of threads plus 1.</td></tr>
<tr><td colspan="2"><b>Function <code>now_s</code>: the clock</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 56  static double now_s(void)
 57  {
 58      struct timespec ts;
 59      clock_gettime(CLOCK_MONOTONIC, &amp;ts);
 60      return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
 61  }
 62</pre></td><td valign="top">Reads the Linux clock <code>CLOCK_MONOTONIC</code> and returns the time in seconds. This clock only moves forward. A change of the date does not change it. It is the only clock that the file reads: <code>worker</code> calls it in lines 471 and 476.</td></tr>
<tr><td colspan="2"><b>Function <code>parse_bytes</code>: the value of <code>--bytes</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 63  static uint64_t parse_bytes(const char *s)
 64  {
 65      char *end;
 66      double v = strtod(s, &amp;end);
 67      double mul = 1;
 68      switch (*end) {
 69      case 'k': case 'K': mul = 1UL &lt;&lt; 10; end++; break;
 70      case 'm': case 'M': mul = 1UL &lt;&lt; 20; end++; break;
 71      case 'g': case 'G': mul = 1UL &lt;&lt; 30; end++; break;
 72      }
 73      if (end == s || *end != '\0' || v &lt;= 0) {
 74          fprintf(stderr, "bad size: %s\n", s);
 75          exit(2);
 76      }
 77      return (uint64_t)(v * mul);
 78  }
 79</pre></td><td valign="top">Reads a number with an optional suffix <code>k</code>, <code>m</code> or <code>g</code>, in upper or lower case. The suffix multiplies by 2^10, 2^20 or 2^30. <code>256M</code> gives 268,435,456 bytes. A text without a number, other text after the suffix, or a value of 0 or below ends the program with exit status 2.</td></tr>
<tr><td colspan="2"><b>Function <code>parse_cpus</code>: the value of <code>--cpus</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 80  /* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */
 81  static void parse_cpus(char *list)
 82  {
 83      for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
 84          char *e, *e2;
 85          long lo = strtol(tok, &amp;e, 10), hi = lo, step = 1;
 86          if (e != tok &amp;&amp; *e == '-') {
 87              hi = strtol(e + 1, &amp;e2, 10);
 88              e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */
 89              if (e != tok &amp;&amp; *e == ':') {
 90                  step = strtol(e + 1, &amp;e2, 10);
 91                  e = e2 == e + 1 ? tok : e2;
 92              }
 93          }</pre></td><td valign="top"><code>strtok</code> splits the list at each comma. Each item is one number, a range <code>lo-hi</code>, or a range with a step <code>lo-hi:step</code>. <code>strtol</code> reads each number. When no digit follows <code>-</code> or <code>:</code>, lines 88 and 91 set <code>e</code> back to <code>tok</code>, and the test in line 94 then rejects the item.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 94          if (e == tok || *e != '\0' || lo &lt; 0 || hi &lt; lo || hi &gt;= CPU_SETSIZE || step &lt; 1) {
 95              fprintf(stderr, "bad cpu list: %s\n", tok);
 96              exit(2);
 97          }</pre></td><td valign="top">Rejects an item in each of these cases. The program then ends with exit status 2.<ul><li>The item holds no number, or other text follows the numbers.</li><li>The start is negative, or the end is below the start.</li><li>A CPU number is <code>CPU_SETSIZE</code> or above (the number of CPUs that the CPU set type of the C library can hold).</li><li>The step is below 1.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 98          for (long c = lo; c &lt;= hi; c += step) {
 99              if (cfg.ncpus == MAX_CPUS) {
100                  fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);
101                  exit(2);
102              }
103              cfg.cpus[cfg.ncpus++] = (int)c;
104          }
105      }
106  }
107</pre></td><td valign="top">Appends every CPU number of the item to <code>cfg.cpus</code> and counts it in <code>cfg.ncpus</code>. <code>--cpus 0-119</code> gives the 120 entries 0, 1, 2, ... 119. More than 1024 entries end the program with exit status 2.</td></tr>
<tr><td colspan="2"><b>Function <code>pin_cpu</code>: bind the calling thread to one CPU</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">108  static void pin_cpu(int cpu)
109  {
110      cpu_set_t set;
111      CPU_ZERO(&amp;set);
112      CPU_SET(cpu, &amp;set);
113      if (sched_setaffinity(0, sizeof set, &amp;set) != 0) {
114          perror("sched_setaffinity");
115          exit(2);
116      }
117  }
118</pre></td><td valign="top">Builds a CPU set that holds only <code>cpu</code> and passes it to <code>sched_setaffinity</code>. The first argument 0 means the calling thread. After the call Linux runs this thread on that CPU only. A failure ends the program with exit status 2.</td></tr>
<tr><td colspan="2"><b>Function <code>alloc_buf</code>: one buffer, aligned to 2 MiB</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">119  static uint64_t *alloc_buf(uint64_t bytes)
120  {
121      size_t len = (bytes + HUGE_BYTES - 1) &amp; ~(HUGE_BYTES - 1);
122      uint8_t *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ | PROT_WRITE,
123                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
124      if (raw == MAP_FAILED) {
125          perror("mmap");
126          exit(2);
127      }</pre></td><td valign="top"><ul><li>Line 121 rounds the size up to a multiple of 2 MiB.</li><li>Lines 122 to 123 ask Linux for that size plus 2 MiB of new memory that no file backs (<code>mmap</code>). The extra 2 MiB leave room for the alignment in line 128.</li><li>Linux assigns no physical page at this call. It assigns a page at the first access to it.</li><li>A failed <code>mmap</code> ends the program with exit status 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">128      uint8_t *p = (uint8_t *)(((uintptr_t)raw + HUGE_BYTES - 1) &amp; ~(uintptr_t)(HUGE_BYTES - 1));
129      /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp
130       * would still get 2 MiB pages. */
131      if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)
132          perror("madvise (continuing)");
133      return (uint64_t *)p;
134  }
135</pre></td><td valign="top"><ul><li>Line 128 moves the start up to the next multiple of 2 MiB. The buffer then starts at the boundary of a huge page.</li><li>Line 131 asks Linux to use huge pages for the buffer (<code>MADV_HUGEPAGE</code>). With <code>--no-thp</code> it forbids them (<code>MADV_NOHUGEPAGE</code>). Part A does not pass <code>--no-thp</code> [Ref5].</li><li>A failed <code>madvise</code> only prints a message.</li><li>The file never checks whether the buffer lies on huge pages.</li><li>No code releases the buffer.</li></ul></td></tr>
<tr><td colspan="2"><b>Old kernels, kept as text inside a comment (not compiled)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">136  /*
137   * History: k_read, k_write and k_copy as they were until 2026-11-13. They
138   * are replaced by the C kernels below. The old comment of k_read was: "16
139   * independent accumulators keep the loop load-bound: on 128-bit NEON gcc
140   * folds them into 8 vector chains, enough to hide a 2-cycle add latency; on
141   * AVX-512 they become 2 zmm chains."
142   *</pre></td><td valign="top">Line 136 opens a C comment that ends in line 166. The compiler reads nothing between these two lines. No preprocessor condition such as <code>#if</code> is used here. The comment keeps the three kernels of the old source as a record.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">143  __attribute__((noinline)) static uint64_t k_read(const uint64_t *a, size_t n)
144  {
145      uint64_t s[16] = { 0 };
146      for (size_t i = 0; i &lt; n; i += 16)
147          for (int j = 0; j &lt; 16; j++)
148              s[j] += a[i + j];
149      uint64_t sum = 0;
150      for (int j = 0; j &lt; 16; j++)
151          sum += s[j];
152      return sum;
153  }</pre></td><td valign="top">Text of the old read kernel, the same text as in the old source [Ref2]. It is not compiled here. It adds each 8-byte word to one of 16 running sums and returns the total of the sums. The binary bw_old holds this code, and the binary bw_new does not [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">154
155  __attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)
156  {
157      for (size_t i = 0; i &lt; n; i++)
158          a[i] = v;
159  }
160
161  __attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
162  {
163      for (size_t i = 0; i &lt; n; i++)
164          d[i] = s[i];
165  }
166   */
167</pre></td><td valign="top">Text of the old <code>k_write</code> and the old <code>k_copy</code>: plain C loops over 8-byte words. They are not compiled here. Line 166 closes the comment.</td></tr>
<tr><td colspan="2"><b>Comment: design of the kernels that are compiled</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">168  /*
169   * C kernels: the same algorithm as the asm kernels below, written with NEON
170   * intrinsics. Each iteration moves 256 B as 16 vectors of 16 B and does no
171   * arithmetic on the data. Callers guarantee n * 8 is a multiple of 256 and
172   * non-zero. The compiler chooses the machine code: check it with objdump
173   * after a change of compiler or flags.
174   *
175   * k_read and k_copy contain an empty asm statement that takes the 16 loaded
176   * vectors as inputs in NEON registers ("w"). gcc must have all 16 values in
177   * registers at that point. In k_read this keeps gcc from deleting the loads.
178   * The statement adds no instruction. It does not fix the order of the loads
179   * and the stores of k_copy: gcc may move code across it. Observed with gcc
180   * 14.2.0 and the Makefile flags: with the statement, k_copy has its 8 ldp
181   * ahead of its 8 stp, as k_asmcopy has; without it, loads and stores
182   * alternate.
183   */</pre></td><td valign="top"><ul><li>Each loop pass moves 256 B as 16 vectors of 16 B. It does no arithmetic on the data.</li><li>The buffer size must be a multiple of 256 B and must not be 0. <code>main</code> checks this in line 549.</li><li>The compiler chooses the machine code. The listing of the build on CRB shows the result [Ref1].</li><li>Lines 175 to 182 explain the empty <code>asm</code> statement of <code>k_read</code> and <code>k_copy</code>. The rows of lines 205 and 261 repeat it.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_read</code>: the new read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">184  __attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)
185  {</pre></td><td valign="top"><ul><li><code>a</code> is the start of the buffer. <code>n</code> is the number of 8-byte words in it.</li><li><code>noinline</code> forbids the compiler to merge the function into its caller. The listing therefore shows it as a function of its own [Ref1].</li><li>The function returns nothing (<code>void</code>). The old <code>k_read</code> returned a sum.</li><li>This is the only <code>k_read</code> that the compiler reads. The text in lines 143 to 153 is a comment.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">186      const uint64_t *p = a;
187      const uint64_t *end = a + n;</pre></td><td valign="top"><code>p</code> is the read position. <code>end</code> is the first address after the buffer: <code>a</code> plus <code>n</code> words. The machine code computes it with one instruction before the loop: <code>add x1, x0, x1, lsl #3</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">188      do {</pre></td><td valign="top"><code>do</code>: the loop body runs before the first test of the end. <code>main</code> rejects a buffer size of 0 (line 549), so the body never runs on an empty buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">189          uint64x2_t v0 = vld1q_u64(p + 0);
190          uint64x2_t v1 = vld1q_u64(p + 2);
191          uint64x2_t v2 = vld1q_u64(p + 4);
192          uint64x2_t v3 = vld1q_u64(p + 6);
193          uint64x2_t v4 = vld1q_u64(p + 8);
194          uint64x2_t v5 = vld1q_u64(p + 10);</pre></td><td valign="top">Each <code>vld1q_u64(p + k)</code> loads 16 B, which is two 8-byte words, from word <code>k</code> after the read position into a vector variable. These 6 lines load the bytes 0 to 95 of the current block of 256 B.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">195          uint64x2_t v6 = vld1q_u64(p + 12);
196          uint64x2_t v7 = vld1q_u64(p + 14);
197          uint64x2_t v8 = vld1q_u64(p + 16);
198          uint64x2_t v9 = vld1q_u64(p + 18);
199          uint64x2_t v10 = vld1q_u64(p + 20);
200          uint64x2_t v11 = vld1q_u64(p + 22);</pre></td><td valign="top">The loads of the bytes 96 to 191 of the block.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">201          uint64x2_t v12 = vld1q_u64(p + 24);
202          uint64x2_t v13 = vld1q_u64(p + 26);
203          uint64x2_t v14 = vld1q_u64(p + 28);
204          uint64x2_t v15 = vld1q_u64(p + 30);</pre></td><td valign="top"><ul><li>The loads of the bytes 192 to 255. One loop pass has 16 loads in the source. It reads 256 B, each byte once.</li><li>gcc joined each two neighbour loads into one <code>ldp</code> instruction, which loads 32 B into two 16-byte registers.</li><li>The machine loop has 8 <code>ldp</code> instructions at the byte offsets 0, 32, 64, ... 224, in rising order [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">205          __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),
206                           "w"(v4), "w"(v5), "w"(v6), "w"(v7),
207                           "w"(v8), "w"(v9), "w"(v10), "w"(v11),
208                           "w"(v12), "w"(v13), "w"(v14), "w"(v15));</pre></td><td valign="top"><ul><li>The instruction text of this <code>asm</code> statement is empty. It adds no instruction to the loop.</li><li>It names the 16 vectors as inputs that must be in vector registers (<code>"w"</code>). So the compiler must have all 16 values loaded at this point.</li><li>The source comment gives the purpose (lines 175 to 178): the statement keeps gcc from deleting the loads.</li><li>After this line nothing uses the values. They are dropped. The listing shows no instruction that uses a loaded register, and no add of data [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">209          p += 32;</pre></td><td valign="top">Moves the read position forward by 32 words, which is 256 B. Machine code: <code>add x0, x0, #0x100</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">210      } while (p &lt; end);</pre></td><td valign="top">Repeats the loop while the read position is below the end. Machine code: <code>cmp x1, x0</code>, then <code>b.hi</code> back to the first <code>ldp</code>. One loop pass is 11 instructions for 256 B: 8 <code>ldp</code>, 1 <code>add</code>, 1 <code>cmp</code> and 1 branch [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">211  }
212</pre></td><td valign="top">End of the function. No value is returned.</td></tr>
<tr><td colspan="2"><b>Function <code>k_write</code>: new write kernel, also the first write of a buffer</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">213  __attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)
214  {
215      uint64_t *p = a;
216      const uint64_t *end = a + n;
217      uint64x2_t q = vdupq_n_u64(v);</pre></td><td valign="top">Stores the value <code>v</code> to every 8-byte word of the buffer. <code>vdupq_n_u64(v)</code> builds one 16-byte vector that holds <code>v</code> twice. In a process with the kernel <code>read</code> this function runs once per buffer, before any timing (line 459).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">218      do {
219          vst1q_u64(p + 0, q);
220          vst1q_u64(p + 2, q);
221          vst1q_u64(p + 4, q);
222          vst1q_u64(p + 6, q);
223          vst1q_u64(p + 8, q);
224          vst1q_u64(p + 10, q);
225          vst1q_u64(p + 12, q);
226          vst1q_u64(p + 14, q);
227          vst1q_u64(p + 16, q);
228          vst1q_u64(p + 18, q);
229          vst1q_u64(p + 20, q);
230          vst1q_u64(p + 22, q);
231          vst1q_u64(p + 24, q);
232          vst1q_u64(p + 26, q);
233          vst1q_u64(p + 28, q);
234          vst1q_u64(p + 30, q);
235          p += 32;
236      } while (p &lt; end);
237  }
238</pre></td><td valign="top"><ul><li>Each loop pass stores the vector 16 times, which is 256 B. Then the position moves on by 256 B.</li><li>gcc compiled the 16 stores to 8 <code>stp</code> instructions per loop pass. Each <code>stp</code> stores the 16-byte register q31 twice, which is 32 B [Ref1].</li><li>The old <code>k_write</code> was a plain C loop. gcc compiled it to a loop of SVE instructions [Ref1].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_copy</code>: the new copy kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">239  __attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
240  {
241      uint64_t *dp = d;
242      const uint64_t *sp = s;
243      const uint64_t *end = s + n;</pre></td><td valign="top">Copies <code>n</code> words from <code>s</code> to <code>d</code>. <code>restrict</code> tells the compiler that the two buffers do not overlap. A process with the kernel <code>read</code> does not call this function.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">244      do {
245          uint64x2_t v0 = vld1q_u64(sp + 0);
246          uint64x2_t v1 = vld1q_u64(sp + 2);
247          uint64x2_t v2 = vld1q_u64(sp + 4);
248          uint64x2_t v3 = vld1q_u64(sp + 6);
249          uint64x2_t v4 = vld1q_u64(sp + 8);
250          uint64x2_t v5 = vld1q_u64(sp + 10);
251          uint64x2_t v6 = vld1q_u64(sp + 12);
252          uint64x2_t v7 = vld1q_u64(sp + 14);
253          uint64x2_t v8 = vld1q_u64(sp + 16);
254          uint64x2_t v9 = vld1q_u64(sp + 18);
255          uint64x2_t v10 = vld1q_u64(sp + 20);
256          uint64x2_t v11 = vld1q_u64(sp + 22);
257          uint64x2_t v12 = vld1q_u64(sp + 24);
258          uint64x2_t v13 = vld1q_u64(sp + 26);
259          uint64x2_t v14 = vld1q_u64(sp + 28);
260          uint64x2_t v15 = vld1q_u64(sp + 30);</pre></td><td valign="top">16 loads of 16 B from the source buffer. The pattern is the same as in <code>k_read</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">261          __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),
262                           "w"(v4), "w"(v5), "w"(v6), "w"(v7),
263                           "w"(v8), "w"(v9), "w"(v10), "w"(v11),
264                           "w"(v12), "w"(v13), "w"(v14), "w"(v15));</pre></td><td valign="top">The same empty <code>asm</code> statement as in <code>k_read</code>. The source comment (lines 178 to 182) says that the statement does not fix the order of the loads and the stores: gcc may move code across it. The comment reports what was observed with gcc 14.2.0: with the statement the 8 <code>ldp</code> loads of a loop pass come before the 8 <code>stp</code> stores, and without it loads and stores alternate. The listing of bw_new shows the 8 <code>ldp</code> before the 8 <code>stp</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">265          vst1q_u64(dp + 0, v0);
266          vst1q_u64(dp + 2, v1);
267          vst1q_u64(dp + 4, v2);
268          vst1q_u64(dp + 6, v3);
269          vst1q_u64(dp + 8, v4);
270          vst1q_u64(dp + 10, v5);
271          vst1q_u64(dp + 12, v6);
272          vst1q_u64(dp + 14, v7);
273          vst1q_u64(dp + 16, v8);
274          vst1q_u64(dp + 18, v9);
275          vst1q_u64(dp + 20, v10);
276          vst1q_u64(dp + 22, v11);
277          vst1q_u64(dp + 24, v12);
278          vst1q_u64(dp + 26, v13);
279          vst1q_u64(dp + 28, v14);
280          vst1q_u64(dp + 30, v15);
281          sp += 32;
282          dp += 32;
283      } while (sp &lt; end);
284  }
285</pre></td><td valign="top">16 stores of 16 B to the destination buffer. Then both positions move on by 256 B. The loop ends when the source position reaches the end of the source buffer.</td></tr>
<tr><td colspan="2"><b>Hand-written kernels (<code>asm</code> text)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">286  /*
287   * asm kernels: the whole hot loop is one inline-asm block, so the compiler
288   * cannot add arithmetic, reorder, or drop anything. Each iteration moves
289   * 256 B with 8 ldp/stp of q registers (16 B each). The loop body is:
290   * 8 x ldp or stp, add, cmp, b.lo. Callers guarantee n * 8 is a multiple of
291   * 256 and non-zero. v8-v15 are callee-saved in AAPCS64: naming them as
292   * clobbers makes gcc save d8-d15 once per call, which is outside the loop.
293   */</pre></td><td valign="top"><ul><li>The whole loop of these three kernels is assembly text. The compiler copies it. It only puts a register in the place of each name such as <code>%[p]</code> [Ref1].</li><li>One loop pass moves 256 B. <code>k_asmread</code> has 8 <code>ldp</code> and <code>k_asmwrite</code> has 8 <code>stp</code>, followed by <code>add</code>, <code>cmp</code> and <code>b.lo</code>. <code>k_asmcopy</code> has 8 <code>ldp</code>, 8 <code>stp</code> and 2 <code>add</code>, followed by <code>cmp</code> and <code>b.lo</code>.</li><li>The old source holds the same text for these kernels [Ref2]. Both binaries hold the same instructions for them [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">294  #if defined(__aarch64__)
295  #define HAVE_ASM_KERNELS 1
296</pre></td><td valign="top"><code>#if defined(__aarch64__)</code>: lines 295 to 376 are compiled only for AArch64. CRB is an AArch64 machine, so this branch is used and <code>HAVE_ASM_KERNELS</code> is 1. Proof: the listing of bw_new holds <code>k_asmread</code>, <code>k_asmwrite</code> and <code>k_asmcopy</code> [Ref1].</td></tr>
<tr><td colspan="2"><b>Function <code>k_asmread</code>: the kernel <code>asmread</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">297  __attribute__((noinline)) static void k_asmread(const uint64_t *a, size_t n)
298  {
299      const uint64_t *p = a;
300      const uint64_t *end = a + n;</pre></td><td valign="top"><code>p</code> is the read position and <code>end</code> is the first address after the buffer, as in <code>k_read</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">301      __asm__ volatile(
302          "1:\n\t"
303          "ldp q0, q1, [%[p]]\n\t"
304          "ldp q2, q3, [%[p], #32]\n\t"
305          "ldp q4, q5, [%[p], #64]\n\t"
306          "ldp q6, q7, [%[p], #96]\n\t"
307          "ldp q8, q9, [%[p], #128]\n\t"
308          "ldp q10, q11, [%[p], #160]\n\t"
309          "ldp q12, q13, [%[p], #192]\n\t"
310          "ldp q14, q15, [%[p], #224]\n\t"
311          "add %[p], %[p], #256\n\t"
312          "cmp %[p], %[end]\n\t"
313          "b.lo 1b\n\t"</pre></td><td valign="top"><ul><li><code>1:</code> is the label at the start of the loop.</li><li>8 <code>ldp</code> instructions load 32 B each into the registers q0 to q15, at the byte offsets 0, 32, 64, ... 224. One loop pass reads 256 B.</li><li><code>add</code> moves the position on by 256 B.</li><li><code>cmp</code> and <code>b.lo 1b</code> branch back to the label while the position is below the end.</li><li>Nothing uses the loaded values.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">314          : [p] "+r"(p)
315          : [end] "r"(end)
316          : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
317            "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
318            "memory", "cc");
319  }
320</pre></td><td valign="top"><ul><li><code>[p] "+r"(p)</code>: <code>p</code> is in a general register. The assembly text reads it and changes it.</li><li><code>[end] "r"(end)</code>: <code>end</code> is an input in a general register.</li><li>The last list names what the text overwrites: the vector registers v0 to v15 and the condition flags (<code>cc</code>). The word <code>memory</code> in it tells the compiler that the text accesses memory that the other lists do not name.</li><li>v8 to v15 are in that list. The Arm calling convention (AAPCS64) requires a function to keep their low halves d8 to d15 unchanged for its caller (source comment, lines 291 to 292). So gcc saves d8 to d15 before the loop and restores them after it, once per call [Ref1].</li><li>The loop itself has 11 instructions per 256 B, as the loop of <code>k_read</code> has. The two loops differ in the register numbers and in the form of the compare and the branch [Ref1].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_asmwrite</code>: the kernel <code>asmwrite</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">321  __attribute__((noinline)) static void k_asmwrite(uint64_t *a, size_t n, uint64_t v)
322  {
323      uint64_t *p = a;
324      const uint64_t *end = a + n;
325      __asm__ volatile(
326          "dup v0.2d, %[v]\n\t"
327          "1:\n\t"
328          "stp q0, q0, [%[p]]\n\t"
329          "stp q0, q0, [%[p], #32]\n\t"
330          "stp q0, q0, [%[p], #64]\n\t"
331          "stp q0, q0, [%[p], #96]\n\t"
332          "stp q0, q0, [%[p], #128]\n\t"
333          "stp q0, q0, [%[p], #160]\n\t"
334          "stp q0, q0, [%[p], #192]\n\t"
335          "stp q0, q0, [%[p], #224]\n\t"
336          "add %[p], %[p], #256\n\t"
337          "cmp %[p], %[end]\n\t"
338          "b.lo 1b\n\t"
339          : [p] "+r"(p)
340          : [end] "r"(end), [v] "r"(v)
341          : "v0", "memory", "cc");
342  }
343</pre></td><td valign="top"><code>dup</code> copies <code>v</code> into both halves of the register v0. Each loop pass stores 256 B with 8 <code>stp q0, q0</code> instructions. A process with the kernel <code>read</code> does not call this function.</td></tr>
<tr><td colspan="2"><b>Function <code>k_asmcopy</code>: the kernel <code>asmcopy</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">344  __attribute__((noinline)) static void k_asmcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
345  {
346      uint64_t *dp = d;
347      const uint64_t *sp = s;
348      const uint64_t *end = s + n;</pre></td><td valign="top">Copies <code>n</code> words from <code>s</code> to <code>d</code> with a hand-written loop. A process with the kernel <code>read</code> does not call this function.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">349      __asm__ volatile(
350          "1:\n\t"
351          "ldp q0, q1, [%[s]]\n\t"
352          "ldp q2, q3, [%[s], #32]\n\t"
353          "ldp q4, q5, [%[s], #64]\n\t"
354          "ldp q6, q7, [%[s], #96]\n\t"
355          "ldp q8, q9, [%[s], #128]\n\t"
356          "ldp q10, q11, [%[s], #160]\n\t"
357          "ldp q12, q13, [%[s], #192]\n\t"
358          "ldp q14, q15, [%[s], #224]\n\t"
359          "stp q0, q1, [%[d]]\n\t"
360          "stp q2, q3, [%[d], #32]\n\t"
361          "stp q4, q5, [%[d], #64]\n\t"
362          "stp q6, q7, [%[d], #96]\n\t"
363          "stp q8, q9, [%[d], #128]\n\t"
364          "stp q10, q11, [%[d], #160]\n\t"
365          "stp q12, q13, [%[d], #192]\n\t"
366          "stp q14, q15, [%[d], #224]\n\t"
367          "add %[s], %[s], #256\n\t"
368          "add %[d], %[d], #256\n\t"
369          "cmp %[s], %[end]\n\t"
370          "b.lo 1b\n\t"</pre></td><td valign="top">Each loop pass loads 256 B with 8 <code>ldp</code> instructions and then stores them with 8 <code>stp</code> instructions. Then both positions move on by 256 B.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">371          : [s] "+r"(sp), [d] "+r"(dp)
372          : [end] "r"(end)
373          : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
374            "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
375            "memory", "cc");
376  }</pre></td><td valign="top">The operand lists: both positions are read and changed, <code>end</code> is an input, and the text overwrites v0 to v15, memory and the condition flags.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">377  #else
378  #define HAVE_ASM_KERNELS 0
379  #endif
380</pre></td><td valign="top">The other branch of the <code>#if</code> in line 294. It would set <code>HAVE_ASM_KERNELS</code> to 0 on a machine that is not AArch64. The build on CRB does not use it.</td></tr>
<tr><td colspan="2"><b>Old <code>pass</code>, kept as text inside a comment (not compiled)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">381  /*
382   * History: pass() as it was until 2026-11-13, when the old k_read returned a
383   * sum. Its comment was: "One pass over the thread's buffer; returns bytes
384   * moved. The sink is per thread (on its stack) so the read kernels of 120
385   * threads do not all store to one shared cache line." worker() had a local
386   * "volatile uint64_t sink" and passed "&amp;sink" in its two pass() calls.
387   *</pre></td><td valign="top">Line 381 opens a second C comment that ends in line 415. It keeps the old <code>pass</code> as a record. It also says what the old <code>worker</code> had: a local variable <code>sink</code> that received the sum of the old <code>k_read</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">388  static uint64_t pass(enum kernel k, struct thread *t, size_t n, uint64_t v, volatile uint64_t *sink)
389  {
390      switch (k) {
391      case K_READ:
392          *sink = k_read(t-&gt;a, n);
393          return cfg.bytes;
394      case K_WRITE:
395          k_write(t-&gt;a, n, v);
396          return cfg.bytes;
397      case K_COPY:
398          k_copy(t-&gt;b, t-&gt;a, n);
399          return 2 * cfg.bytes;</pre></td><td valign="top">Text of the old <code>pass</code>. It is not compiled. Its fifth parameter <code>sink</code> pointed to a variable on the stack of the thread. Line 392 stored the sum of the old read kernel there, once per pass.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">400  #if HAVE_ASM_KERNELS
401      case K_ASMREAD:
402          k_asmread(t-&gt;a, n);
403          return cfg.bytes;
404      case K_ASMWRITE:
405          k_asmwrite(t-&gt;a, n, v);
406          return cfg.bytes;
407      case K_ASMCOPY:
408          k_asmcopy(t-&gt;b, t-&gt;a, n);
409          return 2 * cfg.bytes;
410  #endif
411      default:
412          return 0;
413      }
414  }
415   */
416</pre></td><td valign="top">The rest of the old text. The <code>#if</code> in line 400 is inside the comment and has no effect. Line 415 closes the comment.</td></tr>
<tr><td colspan="2"><b>Function <code>pass</code>: one pass of one kernel over the buffer</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">417  /* One pass over the thread's buffer; returns bytes moved. */
418  static uint64_t pass(enum kernel k, struct thread *t, size_t n, uint64_t v)
419  {</pre></td><td valign="top"><ul><li>Runs kernel <code>k</code> once over the whole buffer of thread <code>t</code>.</li><li>Returns the number of bytes that this pass moved.</li><li><code>n</code> is the buffer size in 8-byte words. <code>v</code> is the value that the write kernels store.</li><li>This is the only <code>pass</code> that the compiler reads. It has no <code>sink</code> parameter.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">420      switch (k) {
421      case K_READ:
422          k_read(t-&gt;a, n);
423          return cfg.bytes;</pre></td><td valign="top">Kernel <code>read</code>: calls the new read kernel on buffer <code>a</code>. Then it returns <code>cfg.bytes</code>, the buffer size: 268,435,456 bytes (256 MiB) in the whole-chip test. The count is the size that the kernel was asked to read. Nothing is counted inside the kernel.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">424      case K_WRITE:
425          k_write(t-&gt;a, n, v);
426          return cfg.bytes;</pre></td><td valign="top">Kernel <code>write</code>: stores <code>v</code> to the whole buffer and counts the buffer size once.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">427      case K_COPY:
428          k_copy(t-&gt;b, t-&gt;a, n);
429          return 2 * cfg.bytes;</pre></td><td valign="top">Kernel <code>copy</code>: copies buffer <code>a</code> to buffer <code>b</code>. It counts 2 times the buffer size: the bytes read plus the bytes written.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">430  #if HAVE_ASM_KERNELS
431      case K_ASMREAD:
432          k_asmread(t-&gt;a, n);
433          return cfg.bytes;</pre></td><td valign="top"><code>#if HAVE_ASM_KERNELS</code>: true on CRB, so lines 431 to 439 are compiled. Kernel <code>asmread</code>: calls the hand-written read loop and counts the buffer size.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">434      case K_ASMWRITE:
435          k_asmwrite(t-&gt;a, n, v);
436          return cfg.bytes;</pre></td><td valign="top">Kernel <code>asmwrite</code>: counts the buffer size once.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">437      case K_ASMCOPY:
438          k_asmcopy(t-&gt;b, t-&gt;a, n);
439          return 2 * cfg.bytes;
440  #endif</pre></td><td valign="top">Kernel <code>asmcopy</code>: counts 2 times the buffer size. <code>#endif</code> closes the condition of line 430.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">441      default:
442          return 0;
443      }
444  }
445</pre></td><td valign="top">Any other kernel number counts 0 bytes. On CRB all six kernels have a case, so this line is not reached.</td></tr>
<tr><td colspan="2"><b>Function <code>worker</code>: one benchmark thread</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">446  static void *worker(void *arg)
447  {
448      struct thread *t = arg;</pre></td><td valign="top">The start function of every benchmark thread. <code>t</code> is the record of this thread. <code>main</code> filled its index and its CPU in lines 564 to 565.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">449      size_t n = cfg.bytes / 8;</pre></td><td valign="top"><code>n</code> is the buffer size in 8-byte words. <code>--bytes 256M</code> gives 33,554,432 words.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">450      /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */
451      uint64_t v = ((uint64_t)getpid() + (uint64_t)t-&gt;idx + 1) * 0x9E3779B97F4A7C15ULL;</pre></td><td valign="top"><code>v</code> is the value that <code>k_write</code> stores. It depends on the process ID (<code>getpid</code>) and on the thread index. The source comment gives the reason: the compiler cannot replace the store loop by <code>memset</code>. The read kernels do not use <code>v</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">452      uint64_t passes_per_check = CHECK_BYTES / cfg.bytes;
453      if (passes_per_check == 0)
454          passes_per_check = 1;
455</pre></td><td valign="top"><code>passes_per_check</code> is the number of passes between two clock reads: 8 MiB divided by the buffer size, rounded down, and at least 1. With 256 MiB buffers the division gives 0, so the value is 1. A thread of the whole-chip test therefore reads the clock after every pass.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">456      if (cfg.ncpus)
457          pin_cpu(t-&gt;cpu);</pre></td><td valign="top">Binds this thread to its CPU when <code>--cpus</code> was given. In part A thread <code>i</code> is bound to CPU <code>i</code>, for <code>i</code> from 0 to 119 [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">458      t-&gt;a = alloc_buf(cfg.bytes);
459      k_write(t-&gt;a, n, v); /* first touch by this thread */</pre></td><td valign="top"><ul><li>Maps buffer <code>a</code> and stores <code>v</code> to all of it with the new <code>k_write</code>.</li><li>This first write makes Linux assign the physical pages of the buffer.</li><li>It happens after the thread is bound to its CPU and before any timing.</li><li>bw_old runs the old <code>k_write</code> at this place [Ref2].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">460      if (cfg.run[K_COPY] || cfg.run[K_ASMCOPY]) {
461          t-&gt;b = alloc_buf(cfg.bytes);
462          k_write(t-&gt;b, n, v);
463      }
464</pre></td><td valign="top">A second buffer <code>b</code> is mapped and written only when a copy kernel is selected. A process with the kernel <code>read</code> has one buffer per thread.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">465      for (int k = 0; k &lt; K_COUNT; k++) {
466          if (!cfg.run[k])
467              continue;</pre></td><td valign="top">Loop over the six kernels in the order of line 26. A kernel that is not selected is skipped. Every process of part A selects one kernel [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">468          for (int rep = 0; rep &lt; cfg.reps; rep++) {</pre></td><td valign="top">One timed interval per repetition. Part A passes <code>--reps 3</code>, so every process times 3 intervals [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">469              pass(k, t, n, v); /* warm-up */</pre></td><td valign="top">Warm-up: one whole pass of the same kernel over the buffer. It is not timed. It runs before every interval, not only before the first one.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">470              pthread_barrier_wait(&amp;bar);</pre></td><td valign="top">First barrier. The thread waits here until all benchmark threads and <code>main</code> (line 582) have arrived. Then the barrier lets all of them continue.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">471              double t0 = now_s(), t1;</pre></td><td valign="top"><b>Start of the timed interval.</b> The thread reads the clock into <code>t0</code> as its first step after the barrier. Every thread has its own <code>t0</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">472              uint64_t bytes = 0, p = 0;</pre></td><td valign="top"><code>bytes</code> counts the bytes of this interval. <code>p</code> counts its passes.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">473              do {
474                  for (uint64_t c = 0; c &lt; passes_per_check; c++, p++)
475                      bytes += pass(k, t, n, v + p);</pre></td><td valign="top">Runs <code>passes_per_check</code> passes, which is 1 pass in the whole-chip test, and adds the byte count of each pass to <code>bytes</code>. The argument <code>v + p</code> changes the stored value from pass to pass. Only the write kernels use it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">476                  t1 = now_s();</pre></td><td valign="top">Reads the clock into <code>t1</code> after the passes of lines 474 to 475. In the whole-chip test that is after every pass. The clock is never read inside a pass.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">477              } while (t1 - t0 &lt; cfg.min_s);</pre></td><td valign="top"><ul><li><b>Stop rule.</b> The loop repeats until <code>cfg.min_s</code> or more has passed after <code>t0</code>. With <code>--min-ms 500</code> that is 0.5 s.</li><li>The test comes only after a whole pass. So every thread ends its interval at the end of a pass, at its own time.</li><li>The interval of a thread is 0.5 s or longer. It exceeds 0.5 s by less than the time between its last two clock reads, which is one pass here.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">478              t-&gt;res[k][rep].bytes = bytes;
479              t-&gt;res[k][rep].elapsed_s = t1 - t0;</pre></td><td valign="top">Stores the result of this thread for this interval: the bytes of its whole passes and its own elapsed time <code>t1 - t0</code>. The interval ended at the last clock read of line 476.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">480              pthread_barrier_wait(&amp;bar);</pre></td><td valign="top">Second barrier. The thread waits here until all other threads have ended their interval and <code>main</code> (line 583) has arrived. A thread that waits here runs no kernel. The threads that are still in their last pass continue without it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">481          }
482      }
483      return NULL;
484  }
485</pre></td><td valign="top">After the last interval of the last selected kernel the thread ends.</td></tr>
<tr><td colspan="2"><b>Function <code>usage</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">486  static void usage(void)
487  {
488      fprintf(stderr,
489              "usage: bandwidth [--threads T --cpus LIST] [--bytes B] "
490              "[--kernel read|write|copy|all|asmread|asmwrite|asmcopy|asmall] "
491              "[--min-ms MS] [--reps R] [--no-thp] [--per-thread]\n"
492              "  all kernels: loads/stores only, bytes must be a multiple of 256; the program builds on AArch64 only\n");
493      exit(2);
494  }
495</pre></td><td valign="top">Prints the argument list to the error output and ends the program with exit status 2. The text of line 492 is new against the old source [Ref2]. It does not change a measurement.</td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: arguments, threads, rates and output</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">496  int main(int argc, char **argv)
497  {
498      int threads_given = 0;
499      cfg.bytes = 1UL &lt;&lt; 20;
500      cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;
501</pre></td><td valign="top">The defaults before the arguments are read: a buffer of 1 MiB per thread and the three kernels <code>read</code>, <code>write</code> and <code>copy</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">502      for (int i = 1; i &lt; argc; i++) {
503          const char *a = argv[i];
504          int more = i + 1 &lt; argc;</pre></td><td valign="top">Loop over the arguments. <code>more</code> is true when one more argument follows. A flag with a value needs it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">505          if (!strcmp(a, "--no-thp")) {
506              cfg.use_thp = 0;
507          } else if (!strcmp(a, "--per-thread")) {
508              cfg.per_thread = 1;
509          } else if (!strcmp(a, "--threads") &amp;&amp; more) {
510              cfg.threads = atoi(argv[++i]);
511              threads_given = 1;
512          } else if (!strcmp(a, "--cpus") &amp;&amp; more) {
513              parse_cpus(argv[++i]);
514          } else if (!strcmp(a, "--bytes") &amp;&amp; more) {
515              cfg.bytes = parse_bytes(argv[++i]);
516          } else if (!strcmp(a, "--min-ms") &amp;&amp; more) {
517              cfg.min_s = atof(argv[++i]) / 1000.0;
518          } else if (!strcmp(a, "--reps") &amp;&amp; more) {
519              cfg.reps = atoi(argv[++i]);</pre></td><td valign="top"><ul><li><code>--no-thp</code>: forbid huge pages for the buffers.</li><li><code>--per-thread</code>: print one more line per thread and interval.</li><li><code>--threads T</code>: the number of benchmark threads.</li><li><code>--cpus LIST</code>: the CPUs of the threads (<code>parse_cpus</code>).</li><li><code>--bytes B</code>: the buffer size per thread (<code>parse_bytes</code>).</li><li><code>--min-ms MS</code> and <code>--reps R</code>: the minimum length of a timed interval, stored in seconds, and the number of intervals per kernel.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">520          } else if (!strcmp(a, "--kernel") &amp;&amp; more) {
521              const char *k = argv[++i];
522              memset(cfg.run, 0, sizeof cfg.run);
523              if (!strcmp(k, "all"))
524                  cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;
525              else if (!strcmp(k, "read"))
526                  cfg.run[K_READ] = 1;
527              else if (!strcmp(k, "write"))
528                  cfg.run[K_WRITE] = 1;
529              else if (!strcmp(k, "copy"))
530                  cfg.run[K_COPY] = 1;
531              else if (!strcmp(k, "asmall"))
532                  cfg.run[K_ASMREAD] = cfg.run[K_ASMWRITE] = cfg.run[K_ASMCOPY] = 1;
533              else if (!strcmp(k, "asmread"))
534                  cfg.run[K_ASMREAD] = 1;
535              else if (!strcmp(k, "asmwrite"))
536                  cfg.run[K_ASMWRITE] = 1;
537              else if (!strcmp(k, "asmcopy"))
538                  cfg.run[K_ASMCOPY] = 1;
539              else
540                  usage();</pre></td><td valign="top"><code>--kernel NAME</code> clears the selection and then selects one kernel. <code>all</code> and <code>asmall</code> select three kernels. An unknown name prints the usage text and ends the program. Every process of part A gets one of the six names <code>read</code>, <code>write</code>, <code>copy</code>, <code>asmread</code>, <code>asmwrite</code>, <code>asmcopy</code> [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">541          } else {
542              usage();
543          }
544      }</pre></td><td valign="top">Any other argument prints the usage text and ends the program.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">545      if (threads_given &amp;&amp; cfg.ncpus == 0) {
546          fprintf(stderr, "--threads requires --cpus\n");
547          usage();
548      }</pre></td><td valign="top"><code>--threads</code> is accepted only together with <code>--cpus</code>. When <code>--threads</code> is given without <code>--cpus</code>, the program prints a message and the usage text and ends with exit status 2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">549      if (cfg.threads &lt; 1 || cfg.reps &lt; 1 || cfg.reps &gt; MAX_REPS || cfg.bytes == 0 || cfg.bytes % 256 != 0)
550          usage();</pre></td><td valign="top">The value checks: 1 thread or more, 1 to 32 repetitions, and a buffer size that is not 0 and is a multiple of 256 B. A value that fails prints the usage text and ends the program. The kernels need the size check: each loop pass moves 256 B.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">551      if (!HAVE_ASM_KERNELS &amp;&amp; (cfg.run[K_ASMREAD] || cfg.run[K_ASMWRITE] || cfg.run[K_ASMCOPY])) {
552          fprintf(stderr, "asm kernels need aarch64\n");
553          return 2;
554      }</pre></td><td valign="top">Stops a process that selects an <code>asm</code> kernel on a machine without them. On CRB <code>HAVE_ASM_KERNELS</code> is 1, so this test never stops the program there.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">555      if (cfg.ncpus &amp;&amp; cfg.threads &gt; cfg.ncpus)
556          fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);
557</pre></td><td valign="top">Prints a warning, and continues, when there are more threads than CPUs in the list. Part A has 120 threads and 120 CPUs [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">558      struct thread *th = calloc((size_t)cfg.threads, sizeof *th);
559      if (!th || pthread_barrier_init(&amp;bar, NULL, (unsigned)cfg.threads + 1) != 0) {
560          perror("setup");
561          return 2;
562      }</pre></td><td valign="top">Allocates the thread records, filled with 0. Creates the barrier for the number of threads plus 1: the benchmark threads and <code>main</code>. In part A that is 121. A failure of either step ends the program with exit status 2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">563      for (int i = 0; i &lt; cfg.threads; i++) {
564          th[i].idx = i;
565          th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;
566          if (pthread_create(&amp;th[i].tid, NULL, worker, &amp;th[i]) != 0) {
567              perror("pthread_create");
568              return 2;
569          }
570      }
571</pre></td><td valign="top"><ul><li>Starts the benchmark threads. Thread <code>i</code> gets the index <code>i</code> and the CPU <code>cfg.cpus[i % cfg.ncpus]</code>. With <code>--threads 120 --cpus 0-119</code> that is CPU <code>i</code>.</li><li>A thread that cannot be started ends the program with exit status 2.</li><li>This file does not bind <code>main</code> to a CPU.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">572      printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "
573             "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",
574             cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");
575      printf("kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,"
576             "per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps\n");</pre></td><td valign="top">Prints the two header lines of the output: a comment line with the settings and the rate formula, and the line of column names. <code>thp=madvise</code> means that the program asked for huge pages. It does not show that the buffers got them.</td></tr>
<tr><td colspan="2"><b><code>main</code>: rate of each interval and the output rows</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">577      for (int k = 0; k &lt; K_COUNT; k++) {
578          if (!cfg.run[k])
579              continue;</pre></td><td valign="top">Loop over the selected kernels, in the same order as in <code>worker</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">580          double best = -1;
581          for (int rep = 0; rep &lt; cfg.reps; rep++) {</pre></td><td valign="top"><code>best</code> will hold the highest rate of the repetitions of this kernel. The inner loop runs once per timed interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">582              pthread_barrier_wait(&amp;bar); /* release the workers */</pre></td><td valign="top">First barrier wait of <code>main</code>. It ends when all benchmark threads have done their warm-up pass and have reached line 470. The barrier then lets all threads go into the timed interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">583              pthread_barrier_wait(&amp;bar); /* all workers finished this rep */</pre></td><td valign="top">Second barrier wait of <code>main</code>. It ends when every thread has ended its interval and has reached line 480. <code>main</code> waits here during the whole interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">584              uint64_t total = 0;
585              double max_el = 0, mn = 1e30, mx = 0, sum = 0;</pre></td><td valign="top">Start values for this interval: <code>total</code> (bytes of all threads), <code>max_el</code> (longest thread time), <code>mn</code> and <code>mx</code> (lowest and highest thread rate) and <code>sum</code> (sum of the thread rates).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">586              for (int i = 0; i &lt; cfg.threads; i++) {
587                  struct result *r = &amp;th[i].res[k][rep];</pre></td><td valign="top">Loop over the threads. <code>r</code> is the result that thread <code>i</code> stored in lines 478 to 479.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">588                  double g = (double)r-&gt;bytes / r-&gt;elapsed_s / 1e9;</pre></td><td valign="top"><code>g</code> is the rate of this one thread in GB/s: its bytes, divided by its own elapsed time, divided by 1e9.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">589                  total += r-&gt;bytes;
590                  if (r-&gt;elapsed_s &gt; max_el)
591                      max_el = r-&gt;elapsed_s;</pre></td><td valign="top">Adds the bytes of the thread to <code>total</code>. Keeps the longest elapsed time of all threads in <code>max_el</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">592                  if (g &lt; mn)
593                      mn = g;
594                  if (g &gt; mx)
595                      mx = g;
596                  sum += g;
597              }</pre></td><td valign="top">Keeps the lowest and the highest thread rate. Adds the thread rate to <code>sum</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">598              double agg = (double)total / max_el / 1e9;</pre></td><td valign="top"><ul><li><b>The rate of the interval</b>, printed as <code>aggregate_GBps</code>: the bytes of all threads, divided by the longest elapsed time of any thread, divided by 1e9.</li><li>A thread with a shorter elapsed time adds no bytes for the rest of that longest time.</li><li>So this value is at most the sum of the thread rates. It is lower when the elapsed times of the threads differ.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">599              if (agg &gt; best)
600                  best = agg;</pre></td><td valign="top">Keeps the highest interval rate of this kernel in <code>best</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">601              printf("%s,%d,%lu,%d,%lu,%.4f,%.2f,%.2f,%.2f,%.2f\n", kernel_name[k], cfg.threads,
602                     (unsigned long)cfg.bytes, rep, (unsigned long)total, max_el, agg, mn, mx,
603                     sum / cfg.threads);
604          }</pre></td><td valign="top">One output row per interval, with 10 fields.<ul><li>1 to 4: kernel name, number of threads, buffer size per thread in bytes, repetition number counted from 0.</li><li>5: <code>total_bytes</code>, the bytes of all threads.</li><li>6: <code>elapsed_s</code>, the longest thread time, with 4 decimals.</li><li>7: <code>aggregate_GBps</code>, with 2 decimals.</li><li>8 to 10: the lowest, the highest and the mean thread rate in GB/s, with 2 decimals.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">605          printf("%s,%d,%lu,best,,,%.2f,,,\n", kernel_name[k], cfg.threads, (unsigned long)cfg.bytes, best);</pre></td><td valign="top">After the last interval of the kernel: one row with <code>best</code> in field 4 and the highest interval rate in field 7. The fields 5, 6, 8, 9 and 10 are empty. The statistics script of the rerun does not use this row [Ref7].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">606          if (cfg.per_thread) {
607              /* thread,&lt;index&gt;,&lt;cpu&gt;,&lt;kernel&gt;,&lt;rep&gt;,&lt;GB/s&gt;: one line per thread and repetition, so that
608               * concurrent per-group totals can be formed from one repetition (reviewer's request) */</pre></td><td valign="top">Only with <code>--per-thread</code>. Part A does not pass this flag, so its output holds no such lines [Ref5] [Ref6].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">609              for (int i = 0; i &lt; cfg.threads; i++)
610                  for (int rep = 0; rep &lt; cfg.reps; rep++) {
611                      struct result *r = &amp;th[i].res[k][rep];
612                      printf("thread,%d,%d,%s,%d,%.2f\n", i, th[i].cpu, kernel_name[k], rep, (double)r-&gt;bytes / r-&gt;elapsed_s / 1e9);
613                  }
614          }</pre></td><td valign="top">One line per thread and interval: the word <code>thread</code>, the thread index, its CPU, the kernel name, the repetition number and the thread rate in GB/s. The comment of line 38 says "best GB/s", but the code prints the rate of every repetition.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">615          fflush(stdout);
616      }</pre></td><td valign="top"><code>fflush</code> writes the rows that the C library still holds in its buffer to the output.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">617      for (int i = 0; i &lt; cfg.threads; i++)
618          pthread_join(th[i].tid, NULL);
619      return 0;
620  }</pre></td><td valign="top">Waits for the end of all benchmark threads. Then the process ends with exit status 0.</td></tr>
</table>

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
