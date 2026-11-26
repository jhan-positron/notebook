# `bandwidth.orig.c` explained

- Source file: `bandwidth.orig.c` in this folder (C source, 463 lines, 15917 bytes).
- sha256 of the source when this page was built: `61228754162c504e37faab3da7f423630ab66e32064ba5911455999347c2fe1b`.
- Role in the whole-chip test: Source of bw_old: the benchmark with the old read kernel, run in part A.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>File header</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  /*
  2   * bandwidth.c - multi-thread streaming bandwidth: read, write, copy.
  3   *
  4   * Every thread owns its buffers (allocated and first-touched by that thread),
  5   * so timing contains no page faults. All threads start on a barrier, run
  6   * whole passes over their buffer until --min-ms has elapsed, and record
  7   * bytes moved and their own elapsed time. GB means 1e9 bytes throughout.
  8   */</pre></td><td valign="top"><ul><li>The comment still names <code>bandwidth.c</code>. This file is the benchmark source before the change of 2026-11-13, and run_kernels.sh built the binary bw_old from it [Ref2].</li><li>The design: each thread owns its buffers. All threads start together. Each thread runs whole passes over its buffer until the minimum time has passed.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  9  #define _GNU_SOURCE
 10  #include &lt;pthread.h&gt;
 11  #include &lt;sched.h&gt;
 12  #include &lt;stdint.h&gt;
 13  #include &lt;stdio.h&gt;
 14  #include &lt;stdlib.h&gt;
 15  #include &lt;string.h&gt;
 16  #include &lt;sys/mman.h&gt;
 17  #include &lt;time.h&gt;
 18  #include &lt;unistd.h&gt;
 19</pre></td><td valign="top"><code>_GNU_SOURCE</code> makes the Linux-only calls visible, for example <code>sched_setaffinity</code> and <code>CPU_SET</code> (lines 109 to 112). The headers give the threads (<code>pthread.h</code>), the CPU pinning (<code>sched.h</code>), <code>mmap</code> and <code>madvise</code> (<code>sys/mman.h</code>), and the clock (<code>time.h</code>).</td></tr>
<tr><td colspan="2"><b>Constants</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 20  #define HUGE_BYTES (2UL &lt;&lt; 20)
 21  #define MAX_CPUS 1024
 22  #define MAX_REPS 32
 23  #define CHECK_BYTES (8UL &lt;&lt; 20) /* clock is read after at least this many bytes */
 24</pre></td><td valign="top"><ul><li><code>HUGE_BYTES</code>: 2 MiB (2097152 bytes), the size of one huge page.</li><li><code>MAX_CPUS</code>: the CPU list holds at most 1024 entries.</li><li><code>MAX_REPS</code>: at most 32 timed intervals per kernel.</li><li><code>CHECK_BYTES</code>: 8 MiB. Line 295 divides it by the buffer size. The result, or 1 when the result is 0 (line 297), is the number of passes between two clock reads.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 25  enum kernel { K_READ, K_WRITE, K_COPY, K_ASMREAD, K_ASMWRITE, K_ASMCOPY, K_COUNT };
 26  static const char *kernel_name[K_COUNT] = { "read", "write", "copy", "asmread", "asmwrite", "asmcopy" };
 27</pre></td><td valign="top">The six kernels of the program. A process runs its selected kernels in this order (loop at line 308). <code>kernel_name</code> holds the text that the first column of an output row shows.</td></tr>
<tr><td colspan="2"><b>Settings and per-thread data</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 28  static struct {
 29      int threads;
 30      int ncpus;
 31      int cpus[MAX_CPUS];
 32      uint64_t bytes;
 33      int run[K_COUNT];
 34      double min_s;
 35      int reps;
 36      int use_thp;
 37      int per_thread; /* --per-thread: one line per thread with its CPU and best GB/s */
 38  } cfg = { .threads = 1, .min_s = 0.5, .reps = 3, .use_thp = 1 };
 39</pre></td><td valign="top"><code>cfg</code> holds the settings of the process. The defaults are 1 thread, a minimum time of 0.5 s per interval, 3 intervals per kernel, and a request for 2 MiB pages.<ul><li><code>cpus</code>, <code>ncpus</code>: the CPU list of the option <code>--cpus</code>.</li><li><code>bytes</code>: the buffer size of each thread.</li><li><code>run[k]</code>: 1 when kernel k is selected.</li><li><code>per_thread</code>: 1 with the option <code>--per-thread</code>. The comment in line 37 is out of date. The code prints one line per thread and repetition, with the rate of that repetition (lines 452 to 456).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 40  struct result {
 41      uint64_t bytes;
 42      double elapsed_s;
 43  };
 44
 45  struct thread {
 46      int idx;
 47      int cpu;
 48      uint64_t *a, *b;
 49      struct result res[K_COUNT][MAX_REPS];
 50      pthread_t tid;
 51  };
 52</pre></td><td valign="top"><ul><li><code>struct result</code>: the bytes that one thread moved in one timed interval, and the time that the same thread measured for it.</li><li><code>struct thread</code>: one entry per thread. It holds the thread index, the CPU, the buffers <code>a</code> and <code>b</code>, and one result per kernel and interval.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 53  static pthread_barrier_t bar;
 54</pre></td><td valign="top"><code>bar</code> is a barrier. A thread that calls <code>pthread_barrier_wait(&amp;bar)</code> waits until all worker threads and the main thread have called it. Then all of them continue together. Line 402 sets how many threads must arrive.</td></tr>
<tr><td colspan="2"><b>Function <code>now_s</code>: read the clock</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 55  static double now_s(void)
 56  {
 57      struct timespec ts;
 58      clock_gettime(CLOCK_MONOTONIC, &amp;ts);
 59      return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
 60  }
 61</pre></td><td valign="top">Reads <code>CLOCK_MONOTONIC</code> (the Linux clock that only moves forward) and returns it in seconds as a <code>double</code>. Every time value of the program comes from this function.</td></tr>
<tr><td colspan="2"><b>Function <code>parse_bytes</code>: read a size such as <code>256M</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 62  static uint64_t parse_bytes(const char *s)
 63  {
 64      char *end;
 65      double v = strtod(s, &amp;end);
 66      double mul = 1;
 67      switch (*end) {
 68      case 'k': case 'K': mul = 1UL &lt;&lt; 10; end++; break;
 69      case 'm': case 'M': mul = 1UL &lt;&lt; 20; end++; break;
 70      case 'g': case 'G': mul = 1UL &lt;&lt; 30; end++; break;
 71      }
 72      if (end == s || *end != '\0' || v &lt;= 0) {
 73          fprintf(stderr, "bad size: %s\n", s);
 74          exit(2);
 75      }
 76      return (uint64_t)(v * mul);
 77  }
 78</pre></td><td valign="top">Reads a number and an optional suffix: <code>k</code> means 2^10, <code>m</code> means 2^20, <code>g</code> means 2^30 (upper case too). <code>256M</code> gives 268435456 bytes (256 MiB). A text that is not a positive size ends the program with exit status 2.</td></tr>
<tr><td colspan="2"><b>Function <code>parse_cpus</code>: read the CPU list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 79  /* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */
 80  static void parse_cpus(char *list)
 81  {
 82      for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
 83          char *e, *e2;
 84          long lo = strtol(tok, &amp;e, 10), hi = lo, step = 1;
 85          if (e != tok &amp;&amp; *e == '-') {
 86              hi = strtol(e + 1, &amp;e2, 10);
 87              e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */
 88              if (e != tok &amp;&amp; *e == ':') {
 89                  step = strtol(e + 1, &amp;e2, 10);
 90                  e = e2 == e + 1 ? tok : e2;
 91              }
 92          }
 93          if (e == tok || *e != '\0' || lo &lt; 0 || hi &lt; lo || hi &gt;= CPU_SETSIZE || step &lt; 1) {
 94              fprintf(stderr, "bad cpu list: %s\n", tok);
 95              exit(2);
 96          }
 97          for (long c = lo; c &lt;= hi; c += step) {
 98              if (cfg.ncpus == MAX_CPUS) {
 99                  fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);
100                  exit(2);
101              }
102              cfg.cpus[cfg.ncpus++] = (int)c;
103          }
104      }
105  }
106</pre></td><td valign="top"><ul><li>Cuts the list at each comma.</li><li>Each piece is one number, a range <code>lo-hi</code>, or a range with a step <code>lo-hi:step</code>.</li><li>Every CPU number is appended to <code>cfg.cpus</code> in the order of the list.</li><li><code>0-119</code> gives the 120 entries 0, 1, 2 and so on up to 119.</li><li>A bad piece ends the program with exit status 2.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>pin_cpu</code>: pin the calling thread to one CPU</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">107  static void pin_cpu(int cpu)
108  {
109      cpu_set_t set;
110      CPU_ZERO(&amp;set);
111      CPU_SET(cpu, &amp;set);
112      if (sched_setaffinity(0, sizeof set, &amp;set) != 0) {
113          perror("sched_setaffinity");
114          exit(2);
115      }
116  }
117</pre></td><td valign="top">Builds a CPU set that holds one CPU and passes it to <code>sched_setaffinity</code>. The first argument 0 means the calling thread, so only this thread is pinned. After the call Linux runs the thread only on that CPU. If the call fails, the program ends with exit status 2.</td></tr>
<tr><td colspan="2"><b>Function <code>alloc_buf</code>: reserve one buffer on a 2 MiB boundary</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">118  static uint64_t *alloc_buf(uint64_t bytes)
119  {
120      size_t len = (bytes + HUGE_BYTES - 1) &amp; ~(HUGE_BYTES - 1);
121      uint8_t *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ | PROT_WRITE,
122                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
123      if (raw == MAP_FAILED) {
124          perror("mmap");
125          exit(2);
126      }</pre></td><td valign="top"><ul><li><code>len</code>: the size rounded up to a multiple of 2 MiB. 256 MiB stays 256 MiB.</li><li><code>mmap</code> reserves <code>len</code> plus 2 MiB of private memory that belongs to no file.</li><li><code>mmap</code> reserves addresses only. Linux assigns the physical memory when a page is first written (line 302).</li><li>If <code>mmap</code> fails, the program ends with exit status 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">127      uint8_t *p = (uint8_t *)(((uintptr_t)raw + HUGE_BYTES - 1) &amp; ~(uintptr_t)(HUGE_BYTES - 1));
128      /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp
129       * would still get 2 MiB pages. */
130      if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)
131          perror("madvise (continuing)");
132      return (uint64_t *)p;
133  }
134</pre></td><td valign="top"><ul><li><code>p</code>: the first address in the reserved range that is a multiple of 2 MiB. The buffer starts there.</li><li><code>madvise</code> with <code>MADV_HUGEPAGE</code> asks Linux to use 2 MiB pages for the buffer. With the option <code>--no-thp</code> it passes <code>MADV_NOHUGEPAGE</code>, which forbids them.</li><li>ra.sh does not pass <code>--no-thp</code>, so the whole-chip test asks for 2 MiB pages [Ref3].</li><li>A failed <code>madvise</code> only prints a message. The program never checks whether the buffer in fact lies on 2 MiB pages.</li><li>The program never releases the buffer.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_read</code>: the OLD read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">135  /* 16 independent accumulators keep the loop load-bound: on 128-bit NEON gcc
136   * folds them into 8 vector chains, enough to hide a 2-cycle add latency;
137   * on AVX-512 they become 2 zmm chains. */</pre></td><td valign="top"><ul><li>The comment gives the intent of the 16 sums. An add to one sum does not wait for an add to another sum. So the loads, not the adds, are meant to set the speed of the loop. This file holds no measurement of that.</li><li>The NEON sentence names 8 vector chains. This count holds for bw_old: its machine code has 8 vector registers for the sums, each with two 64-bit sums [Ref1].</li><li>The AVX-512 sentence is about x86 processors. It does not apply to CRB.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">138  __attribute__((noinline)) static uint64_t k_read(const uint64_t *a, size_t n)
139  {</pre></td><td valign="top"><code>noinline</code> forbids the compiler to merge the kernel into its caller. So the binary holds <code>k_read</code> as a function of its own, and run_kernels.sh printed its machine code by name [Ref1]. <code>a</code> is the buffer of the thread. <code>n</code> is the number of 8-byte elements in the buffer (line 291).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">140      uint64_t s[16] = { 0 };</pre></td><td valign="top">16 running sums of 64 bits each, all 0 at the start. In bw_old the compiler keeps them in the 8 vector registers <code>v24</code> to <code>v31</code> during the loop. Each register holds two of the sums [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">141      for (size_t i = 0; i &lt; n; i += 16)</pre></td><td valign="top">The outer loop. One loop pass handles 16 elements, which is 128 B. A buffer of 256 MiB needs 2097152 loop passes. <code>main</code> accepts only buffer sizes that are a multiple of 256 B (line 392), so the loop ends exactly at the end of the buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">142          for (int j = 0; j &lt; 16; j++)</pre></td><td valign="top">The inner loop of the source: 16 steps per outer loop pass, one step per sum. The machine code of bw_old has no inner loop. gcc turned its 16 loads and 16 adds into vector instructions [Ref1]. One loop pass of the machine code is one pass of the outer loop (128 B).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">143              s[j] += a[i + j];</pre></td><td valign="top">Source: load one 8-byte element and add it to its own sum. Every loaded value is used. One loop pass of the machine code of bw_old has 16 instructions [Ref1]:<ul><li>4 <code>ldp q</code> loads. Each one loads two 16-byte vector registers, so each one reads 32 B.</li><li>8 vector <code>add</code> instructions. Each one adds one loaded register (two 64-bit values) to one of the 8 sum registers.</li><li>2 scalar <code>add</code> instructions: the loop counter plus 1, and the buffer pointer plus 128 B.</li><li>1 <code>cmp</code> and 1 conditional branch back to the first load.</li><li>Per 256 B this is 8 <code>ldp q</code> loads and 16 vector adds, 32 instructions in total. The new read kernel of bw_new has the same 8 <code>ldp q</code> loads per 256 B and no vector add, 11 instructions in total [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">144      uint64_t sum = 0;
145      for (int j = 0; j &lt; 16; j++)
146          sum += s[j];
147      return sum;
148  }
149</pre></td><td valign="top">After the loop: add the 16 sums to one value and return it. This runs once per call, so once per pass over the buffer. In bw_old the code outside the loop also sets the sums to 0 and stores them to the stack. It also holds a stack check that is not in the source (a call of <code>__stack_chk_fail</code>) [Ref1].</td></tr>
<tr><td colspan="2"><b>Function <code>k_write</code>: C write kernel, also used for the first touch</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">150  __attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)
151  {
152      for (size_t i = 0; i &lt; n; i++)
153          a[i] = v;
154  }
155</pre></td><td valign="top">Stores the value <code>v</code> into each of the <code>n</code> elements. The worker also calls it once per buffer for the first touch (lines 302 and 305). In bw_old gcc made an SVE loop from it, with one <code>st1d</code> vector store per loop pass [Ref1]. The objdump text does not show the vector length.</td></tr>
<tr><td colspan="2"><b>Function <code>k_copy</code>: C copy kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">156  __attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
157  {
158      for (size_t i = 0; i &lt; n; i++)
159          d[i] = s[i];
160  }
161</pre></td><td valign="top">Copies <code>n</code> elements from <code>s</code> to <code>d</code>. <code>restrict</code> tells the compiler that the two buffers do not overlap. In bw_old gcc made an SVE loop from it, with one <code>ld1d</code> vector load and one <code>st1d</code> vector store per loop pass [Ref1].</td></tr>
<tr><td colspan="2"><b>The asm kernels (64-bit Arm only)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">162  /*
163   * asm kernels: the whole hot loop is one inline-asm block, so the compiler
164   * cannot add arithmetic, reorder, or drop anything. Each iteration moves
165   * 256 B with 8 ldp/stp of q registers (16 B each). The loop body is:
166   * 8 x ldp or stp, add, cmp, b.lo. Callers guarantee n * 8 is a multiple of
167   * 256 and non-zero. v8-v15 are callee-saved in AAPCS64: naming them as
168   * clobbers makes gcc save d8-d15 once per call, which is outside the loop.
169   */
170  #if defined(__aarch64__)
171  #define HAVE_ASM_KERNELS 1
172</pre></td><td valign="top"><ul><li>These three kernels are assembly text inside a C function. The compiler copies the loop. It only puts a register in the place of each name such as <code>%[p]</code> [Ref1]. It cannot add, reorder or remove an instruction.</li><li>Each loop pass handles 256 B of the buffer: with 8 <code>ldp q</code> loads, with 8 <code>stp q</code> stores, or with both in <code>k_asmcopy</code>.</li><li>The Arm calling rules say that a function must keep the lower halves (<code>d8</code> to <code>d15</code>) of the registers <code>v8</code> to <code>v15</code> for its caller. So the compiler saves and restores them once per call, outside the loop. The objdump text of <code>k_asmread</code> and <code>k_asmcopy</code> shows this [Ref1].</li><li><code>HAVE_ASM_KERNELS</code> is 1 when the three kernels exist.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_asmread</code>: hand-written load-only loop</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">173  __attribute__((noinline)) static void k_asmread(const uint64_t *a, size_t n)
174  {
175      const uint64_t *p = a;
176      const uint64_t *end = a + n;</pre></td><td valign="top"><code>p</code> starts at the first element of the buffer. <code>end</code> is the address directly after the last element. The function returns nothing.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">177      __asm__ volatile(
178          "1:\n\t"
179          "ldp q0, q1, [%[p]]\n\t"
180          "ldp q2, q3, [%[p], #32]\n\t"
181          "ldp q4, q5, [%[p], #64]\n\t"
182          "ldp q6, q7, [%[p], #96]\n\t"
183          "ldp q8, q9, [%[p], #128]\n\t"
184          "ldp q10, q11, [%[p], #160]\n\t"
185          "ldp q12, q13, [%[p], #192]\n\t"
186          "ldp q14, q15, [%[p], #224]\n\t"
187          "add %[p], %[p], #256\n\t"
188          "cmp %[p], %[end]\n\t"
189          "b.lo 1b\n\t"</pre></td><td valign="top">One loop pass:<ul><li>8 <code>ldp q</code> loads read 256 B into the registers <code>q0</code> to <code>q15</code>. Each load reads 32 B.</li><li><code>add</code> moves the pointer forward by 256 B.</li><li><code>cmp</code> and <code>b.lo</code> repeat the loop while the pointer is below <code>end</code>.</li><li>The loaded values are never used. The next loop pass overwrites them.</li><li>This is 11 instructions per 256 B. The objdump text of bw_old shows the same 11 instructions [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">190          : [p] "+r"(p)
191          : [end] "r"(end)
192          : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
193            "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
194            "memory", "cc");
195  }
196</pre></td><td valign="top">These three lists tell the compiler what the assembly text uses. <code>p</code> is read and changed in a register. <code>end</code> is read in a register. The last list names what the text changes or accesses without an operand: the registers <code>v0</code> to <code>v15</code>, memory, and the condition flags (<code>cc</code>).</td></tr>
<tr><td colspan="2"><b>Function <code>k_asmwrite</code>: hand-written store-only loop</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">197  __attribute__((noinline)) static void k_asmwrite(uint64_t *a, size_t n, uint64_t v)
198  {
199      uint64_t *p = a;
200      const uint64_t *end = a + n;
201      __asm__ volatile(
202          "dup v0.2d, %[v]\n\t"
203          "1:\n\t"
204          "stp q0, q0, [%[p]]\n\t"
205          "stp q0, q0, [%[p], #32]\n\t"
206          "stp q0, q0, [%[p], #64]\n\t"
207          "stp q0, q0, [%[p], #96]\n\t"
208          "stp q0, q0, [%[p], #128]\n\t"
209          "stp q0, q0, [%[p], #160]\n\t"
210          "stp q0, q0, [%[p], #192]\n\t"
211          "stp q0, q0, [%[p], #224]\n\t"
212          "add %[p], %[p], #256\n\t"
213          "cmp %[p], %[end]\n\t"
214          "b.lo 1b\n\t"
215          : [p] "+r"(p)
216          : [end] "r"(end), [v] "r"(v)
217          : "v0", "memory", "cc");
218  }
219</pre></td><td valign="top"><code>dup</code> fills the register <code>v0</code> with two copies of the 64-bit value <code>v</code>, once before the loop. Each loop pass stores 256 B with 8 <code>stp q0, q0</code> instructions of 32 B each. Then <code>add</code> moves the pointer forward by 256 B, and the loop repeats while the pointer is below <code>end</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>k_asmcopy</code>: hand-written copy loop</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">220  __attribute__((noinline)) static void k_asmcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
221  {
222      uint64_t *dp = d;
223      const uint64_t *sp = s;
224      const uint64_t *end = s + n;
225      __asm__ volatile(
226          "1:\n\t"
227          "ldp q0, q1, [%[s]]\n\t"
228          "ldp q2, q3, [%[s], #32]\n\t"
229          "ldp q4, q5, [%[s], #64]\n\t"
230          "ldp q6, q7, [%[s], #96]\n\t"
231          "ldp q8, q9, [%[s], #128]\n\t"
232          "ldp q10, q11, [%[s], #160]\n\t"
233          "ldp q12, q13, [%[s], #192]\n\t"
234          "ldp q14, q15, [%[s], #224]\n\t"
235          "stp q0, q1, [%[d]]\n\t"
236          "stp q2, q3, [%[d], #32]\n\t"
237          "stp q4, q5, [%[d], #64]\n\t"
238          "stp q6, q7, [%[d], #96]\n\t"
239          "stp q8, q9, [%[d], #128]\n\t"
240          "stp q10, q11, [%[d], #160]\n\t"
241          "stp q12, q13, [%[d], #192]\n\t"
242          "stp q14, q15, [%[d], #224]\n\t"
243          "add %[s], %[s], #256\n\t"
244          "add %[d], %[d], #256\n\t"
245          "cmp %[s], %[end]\n\t"
246          "b.lo 1b\n\t"
247          : [s] "+r"(sp), [d] "+r"(dp)
248          : [end] "r"(end)
249          : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
250            "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
251            "memory", "cc");
252  }</pre></td><td valign="top">Each loop pass first loads 256 B from <code>s</code> with 8 <code>ldp q</code> instructions. It then stores the same 16 registers to <code>d</code> with 8 <code>stp q</code> instructions. Both pointers move forward by 256 B, and the loop repeats while the source pointer is below <code>end</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">253  #else
254  #define HAVE_ASM_KERNELS 0
255  #endif
256</pre></td><td valign="top">On a processor that is not 64-bit Arm the three asm kernels are not compiled. <code>HAVE_ASM_KERNELS</code> is then 0, and <code>main</code> refuses to run them (line 394).</td></tr>
<tr><td colspan="2"><b>Function <code>pass</code>: one pass of kernel <code>k</code> over the buffer</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">257  /* One pass over the thread's buffer; returns bytes moved. The sink is per
258   * thread (on its stack) so the read kernels of 120 threads do not all store
259   * to one shared cache line. */
260  static uint64_t pass(enum kernel k, struct thread *t, size_t n, uint64_t v, volatile uint64_t *sink)
261  {</pre></td><td valign="top">Runs the kernel <code>k</code> once over the whole buffer of thread <code>t</code>. It returns the number of bytes that the caller counts for this pass.<ul><li><code>n</code>: the number of 8-byte elements.</li><li><code>v</code>: the value for the write kernels.</li><li><code>sink</code>: a pointer to a variable on the stack of the calling thread (line 292).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">262      switch (k) {
263      case K_READ:
264          *sink = k_read(t-&gt;a, n);
265          return cfg.bytes;</pre></td><td valign="top">Kernel <code>read</code>: call <code>k_read</code>, the old read kernel, on buffer <code>a</code>, and store the returned sum to <code>*sink</code>.<ul><li><code>sink</code> is <code>volatile</code>, so the compiler must do this store. It therefore cannot remove the sum, the adds or the loads.</li><li>This is one 8-byte store per pass over the buffer.</li><li>The pass counts <code>cfg.bytes</code>, the buffer size. It is 268435456 bytes in the whole-chip test.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">266      case K_WRITE:
267          k_write(t-&gt;a, n, v);
268          return cfg.bytes;</pre></td><td valign="top">Kernel <code>write</code>: fill buffer <code>a</code> with the value <code>v</code>. The pass counts the buffer size once.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">269      case K_COPY:
270          k_copy(t-&gt;b, t-&gt;a, n);
271          return 2 * cfg.bytes;</pre></td><td valign="top">Kernel <code>copy</code>: copy buffer <code>a</code> to buffer <code>b</code>. The pass counts the buffer size twice: the bytes read plus the bytes written.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">272  #if HAVE_ASM_KERNELS
273      case K_ASMREAD:
274          k_asmread(t-&gt;a, n);
275          return cfg.bytes;</pre></td><td valign="top">Kernel <code>asmread</code> (compiled on 64-bit Arm only): call <code>k_asmread</code> on buffer <code>a</code>. <code>k_asmread</code> returns no value, so nothing is stored to <code>sink</code>. The pass counts the buffer size once.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">276      case K_ASMWRITE:
277          k_asmwrite(t-&gt;a, n, v);
278          return cfg.bytes;</pre></td><td valign="top">Kernel <code>asmwrite</code>: the same as <code>write</code>, with the hand-written loop.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">279      case K_ASMCOPY:
280          k_asmcopy(t-&gt;b, t-&gt;a, n);
281          return 2 * cfg.bytes;
282  #endif</pre></td><td valign="top">Kernel <code>asmcopy</code>: the same as <code>copy</code>, with the hand-written loop. It also counts the buffer size twice.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">283      default:
284          return 0;
285      }
286  }
287</pre></td><td valign="top">Any other value counts 0 bytes. This line is reached only for an asm kernel in a build without the asm kernels. <code>main</code> stops such a run before it creates the threads (line 394).</td></tr>
<tr><td colspan="2"><b>Function <code>worker</code>: one benchmark thread</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">288  static void *worker(void *arg)
289  {
290      struct thread *t = arg;</pre></td><td valign="top">Each thread that <code>main</code> creates (line 409) runs this function once. <code>t</code> is the entry of this thread in the thread table.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">291      size_t n = cfg.bytes / 8;</pre></td><td valign="top"><code>n</code>: the number of 8-byte elements in the buffer. It is 33554432 for a buffer of 256 MiB.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">292      volatile uint64_t sink;</pre></td><td valign="top"><code>sink</code>: the variable that receives the sum of <code>k_read</code> (line 264). It lies on the stack of this thread. So the 120 threads do not store to one shared cache line.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">293      /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */
294      uint64_t v = ((uint64_t)getpid() + (uint64_t)t-&gt;idx + 1) * 0x9E3779B97F4A7C15ULL;</pre></td><td valign="top"><code>v</code>: the value that the write kernels store. It is computed from the process id and the thread index, so the compiler does not know it. The read kernels do not use it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">295      uint64_t passes_per_check = CHECK_BYTES / cfg.bytes;
296      if (passes_per_check == 0)
297          passes_per_check = 1;
298</pre></td><td valign="top"><code>passes_per_check</code>: the number of passes between two clock reads. It is 8 MiB divided by the buffer size, and at least 1. For a buffer of 256 MiB the division gives 0, so the value is 1. The thread then reads the clock after every pass.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">299      if (cfg.ncpus)
300          pin_cpu(t-&gt;cpu);</pre></td><td valign="top">When a CPU list was given, the thread pins itself to its CPU. In the whole-chip test thread i runs on CPU i (line 408). The thread does this before it reserves its buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">301      t-&gt;a = alloc_buf(cfg.bytes);
302      k_write(t-&gt;a, n, v); /* first touch by this thread */</pre></td><td valign="top">Reserve buffer <code>a</code> and write <code>v</code> into every element with <code>k_write</code>. This write is the first touch: Linux assigns the physical memory of the buffer now, while the thread already runs on its CPU. It is not timed.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">303      if (cfg.run[K_COPY] || cfg.run[K_ASMCOPY]) {
304          t-&gt;b = alloc_buf(cfg.bytes);
305          k_write(t-&gt;b, n, v);
306      }
307</pre></td><td valign="top">Only when <code>copy</code> or <code>asmcopy</code> is selected: reserve and write a second buffer <code>b</code>. In the whole-chip test a process of the read kernel has one buffer of 256 MiB per thread.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">308      for (int k = 0; k &lt; K_COUNT; k++) {
309          if (!cfg.run[k])
310              continue;</pre></td><td valign="top">Loop over the six kernels in the order of the <code>enum</code> (line 25). A kernel that is not selected is skipped. ra.sh selects one kernel per process. So in the whole-chip test no kernel is timed after another kernel in the same process [Ref3].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">311          for (int rep = 0; rep &lt; cfg.reps; rep++) {
312              pass(k, t, n, v, &amp;sink); /* warm-up */</pre></td><td valign="top">For each repetition (3 in the whole-chip test): first run one pass that is not timed (warm-up).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">313              pthread_barrier_wait(&amp;bar);</pre></td><td valign="top">Wait at the barrier until all 120 workers and the main thread have arrived. A thread that arrives early waits here and reads no memory. The barrier then releases all threads at the same time. This is the common start of the timed interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">314              double t0 = now_s(), t1;
315              uint64_t bytes = 0, p = 0;</pre></td><td valign="top"><code>t0</code>: the clock read directly after the barrier. It is the start of the timed interval of this thread. Each thread has its own <code>t0</code>. <code>bytes</code> counts the bytes of this interval, and <code>p</code> counts its passes.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">316              do {
317                  for (uint64_t c = 0; c &lt; passes_per_check; c++, p++)
318                      bytes += pass(k, t, n, v + p, &amp;sink);</pre></td><td valign="top">The timed work. The inner <code>for</code> runs <code>passes_per_check</code> passes (1 in the whole-chip test) and adds the byte count of each pass to <code>bytes</code>. For kernel <code>read</code> each pass is one call of <code>k_read</code> over the whole buffer. <code>v + p</code> gives the write kernels a new value in every pass.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">319                  t1 = now_s();
320              } while (t1 - t0 &lt; cfg.min_s);</pre></td><td valign="top"><code>t1</code>: the clock read after the passes. The loop repeats while less than <code>cfg.min_s</code> has passed since <code>t0</code> (0.5 s in the whole-chip test).<ul><li>A thread never stops inside a pass. In the whole-chip test its interval ends at the first end of a pass that lies 0.5 s or more after <code>t0</code>.</li><li>The threads therefore stop at different times.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">321              t-&gt;res[k][rep].bytes = bytes;
322              t-&gt;res[k][rep].elapsed_s = t1 - t0;</pre></td><td valign="top">Store the result of this thread for this kernel and repetition: the bytes counted and the time <code>t1 - t0</code>. The time covers the passes and the clock reads between them. It does not cover the warm-up pass or the waits at the barrier.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">323              pthread_barrier_wait(&amp;bar);</pre></td><td valign="top">Wait at the barrier until all workers have finished the interval and the main thread has arrived. A thread that stopped early waits here and reads no memory while the other threads finish their last pass.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">324          }
325      }
326      return NULL;
327  }
328</pre></td><td valign="top">End of the repetition loop and of the kernel loop. The next repetition starts with its warm-up pass directly after the barrier. The code has no sleep there. The thread ends after the last repetition of the last selected kernel.</td></tr>
<tr><td colspan="2"><b>Function <code>usage</code>: print the options and stop</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">329  static void usage(void)
330  {
331      fprintf(stderr,
332              "usage: bandwidth [--threads T --cpus LIST] [--bytes B] "
333              "[--kernel read|write|copy|all|asmread|asmwrite|asmcopy|asmall] "
334              "[--min-ms MS] [--reps R] [--no-thp] [--per-thread]\n"
335              "  asm* kernels: aarch64 only, loads/stores only, bytes must be a multiple of 256\n");
336      exit(2);
337  }
338</pre></td><td valign="top">Prints the list of options to the error output and ends the program with exit status 2.</td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: arguments, threads, rates</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">339  int main(int argc, char **argv)
340  {
341      int threads_given = 0;
342      cfg.bytes = 1UL &lt;&lt; 20;
343      cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;
344</pre></td><td valign="top">Defaults before the arguments are read: a buffer of 1 MiB per thread, and the three C kernels <code>read</code>, <code>write</code> and <code>copy</code> selected.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">345      for (int i = 1; i &lt; argc; i++) {
346          const char *a = argv[i];
347          int more = i + 1 &lt; argc;
348          if (!strcmp(a, "--no-thp")) {
349              cfg.use_thp = 0;
350          } else if (!strcmp(a, "--per-thread")) {
351              cfg.per_thread = 1;</pre></td><td valign="top">Loop over the arguments. <code>more</code> is true when one more argument follows, which an option with a value needs.<ul><li><code>--no-thp</code> forbids 2 MiB pages (line 130).</li><li><code>--per-thread</code> adds one output line per thread and repetition (line 449).</li><li>ra.sh passes neither of the two [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">352          } else if (!strcmp(a, "--threads") &amp;&amp; more) {
353              cfg.threads = atoi(argv[++i]);
354              threads_given = 1;
355          } else if (!strcmp(a, "--cpus") &amp;&amp; more) {
356              parse_cpus(argv[++i]);
357          } else if (!strcmp(a, "--bytes") &amp;&amp; more) {
358              cfg.bytes = parse_bytes(argv[++i]);
359          } else if (!strcmp(a, "--min-ms") &amp;&amp; more) {
360              cfg.min_s = atof(argv[++i]) / 1000.0;
361          } else if (!strcmp(a, "--reps") &amp;&amp; more) {
362              cfg.reps = atoi(argv[++i]);</pre></td><td valign="top">Options with a value. The values of the whole-chip test come from ra.sh [Ref3].<ul><li><code>--threads</code>: the number of threads. ra.sh passes 120.</li><li><code>--cpus</code>: the CPU list, read by <code>parse_cpus</code>. ra.sh passes <code>0-119</code>.</li><li><code>--bytes</code>: the buffer size of each thread, read by <code>parse_bytes</code>. ra.sh passes <code>256M</code> (256 MiB).</li><li><code>--min-ms</code>: the minimum time of an interval, changed from ms to seconds. ra.sh passes 500, which gives 0.5 s.</li><li><code>--reps</code>: the number of timed intervals per kernel. ra.sh passes 3.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">363          } else if (!strcmp(a, "--kernel") &amp;&amp; more) {
364              const char *k = argv[++i];
365              memset(cfg.run, 0, sizeof cfg.run);
366              if (!strcmp(k, "all"))
367                  cfg.run[K_READ] = cfg.run[K_WRITE] = cfg.run[K_COPY] = 1;
368              else if (!strcmp(k, "read"))
369                  cfg.run[K_READ] = 1;
370              else if (!strcmp(k, "write"))
371                  cfg.run[K_WRITE] = 1;
372              else if (!strcmp(k, "copy"))
373                  cfg.run[K_COPY] = 1;
374              else if (!strcmp(k, "asmall"))
375                  cfg.run[K_ASMREAD] = cfg.run[K_ASMWRITE] = cfg.run[K_ASMCOPY] = 1;
376              else if (!strcmp(k, "asmread"))
377                  cfg.run[K_ASMREAD] = 1;
378              else if (!strcmp(k, "asmwrite"))
379                  cfg.run[K_ASMWRITE] = 1;
380              else if (!strcmp(k, "asmcopy"))
381                  cfg.run[K_ASMCOPY] = 1;
382              else
383                  usage();</pre></td><td valign="top"><ul><li><code>--kernel</code>: first clear every selection, then select the named kernel.</li><li><code>all</code> selects the three C kernels, and <code>asmall</code> selects the three asm kernels.</li><li>Any other name prints the option list and stops.</li><li>ra.sh passes one kernel name per process. One call of ra.sh starts bw_old with each of the six names twice, once per round [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">384          } else {
385              usage();
386          }
387      }</pre></td><td valign="top">An unknown argument, or an option without its value, prints the option list and stops.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">388      if (threads_given &amp;&amp; cfg.ncpus == 0) {
389          fprintf(stderr, "--threads requires --cpus\n");
390          usage();
391      }
392      if (cfg.threads &lt; 1 || cfg.reps &lt; 1 || cfg.reps &gt; MAX_REPS || cfg.bytes == 0 || cfg.bytes % 256 != 0)
393          usage();</pre></td><td valign="top">Checks of the arguments. A failed check prints the option list and ends the program with exit status 2.<ul><li><code>--threads</code> is accepted only together with <code>--cpus</code>.</li><li>The thread count must be 1 or more. The repetitions must be 1 to 32.</li><li>The buffer size must be a multiple of 256 B. Every kernel then ends exactly at the end of the buffer: <code>k_read</code> moves in steps of 128 B, the asm kernels in steps of 256 B.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">394      if (!HAVE_ASM_KERNELS &amp;&amp; (cfg.run[K_ASMREAD] || cfg.run[K_ASMWRITE] || cfg.run[K_ASMCOPY])) {
395          fprintf(stderr, "asm kernels need aarch64\n");
396          return 2;
397      }
398      if (cfg.ncpus &amp;&amp; cfg.threads &gt; cfg.ncpus)
399          fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);
400</pre></td><td valign="top">An asm kernel on a processor that is not 64-bit Arm ends the program with exit status 2. More threads than CPUs in the list only gives a warning. The list is then used again from its start (line 408). The whole-chip test has 120 threads on 120 CPUs.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">401      struct thread *th = calloc((size_t)cfg.threads, sizeof *th);
402      if (!th || pthread_barrier_init(&amp;bar, NULL, (unsigned)cfg.threads + 1) != 0) {
403          perror("setup");
404          return 2;
405      }</pre></td><td valign="top">Allocate the thread table, filled with zeros. Create the barrier for <code>cfg.threads + 1</code> threads: the workers plus the main thread. In the whole-chip test this is 121. A failure ends the program with exit status 2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">406      for (int i = 0; i &lt; cfg.threads; i++) {
407          th[i].idx = i;
408          th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;
409          if (pthread_create(&amp;th[i].tid, NULL, worker, &amp;th[i]) != 0) {
410              perror("pthread_create");
411              return 2;
412          }
413      }
414</pre></td><td valign="top">Create the threads.<ul><li>Thread <code>i</code> gets the index <code>i</code> and the CPU <code>cfg.cpus[i % cfg.ncpus]</code>. With the list <code>0-119</code> and 120 threads, thread i gets CPU i.</li><li>Each thread starts <code>worker</code> immediately: it pins itself, reserves and writes its buffer, runs the first warm-up pass and then waits at the barrier.</li><li>If a thread cannot be created, the program ends with exit status 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">415      printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "
416             "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",
417             cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");
418      printf("kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,"
419             "per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps\n");</pre></td><td valign="top">Print two header lines to the standard output. The first starts with <code>#</code> and gives the rate formula and the settings of the process. The second holds the 10 column names of the interval rows.</td></tr>
<tr><td colspan="2"><b>Rate computation: one row per timed interval</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">420      for (int k = 0; k &lt; K_COUNT; k++) {
421          if (!cfg.run[k])
422              continue;
423          double best = -1;</pre></td><td valign="top">Loop over the kernels in the same order as the workers (line 308), with the same skip rule. <code>best</code> will hold the highest total rate of the repetitions of this kernel.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">424          for (int rep = 0; rep &lt; cfg.reps; rep++) {
425              pthread_barrier_wait(&amp;bar); /* release the workers */
426              pthread_barrier_wait(&amp;bar); /* all workers finished this rep */</pre></td><td valign="top">One repetition, as the main thread sees it:<ul><li>First wait: the barrier opens when the main thread and all workers have arrived. The workers then start their timed interval (line 314).</li><li>Second wait: it returns when every worker has finished its interval (line 323).</li><li>The main thread does no work during the interval. The program does not pin the main thread.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">427              uint64_t total = 0;
428              double max_el = 0, mn = 1e30, mx = 0, sum = 0;</pre></td><td valign="top">Start values for one row: <code>total</code> (bytes of all threads), <code>max_el</code> (longest thread time), and <code>mn</code>, <code>mx</code>, <code>sum</code> (lowest, highest and sum of the thread rates).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">429              for (int i = 0; i &lt; cfg.threads; i++) {
430                  struct result *r = &amp;th[i].res[k][rep];
431                  double g = (double)r-&gt;bytes / r-&gt;elapsed_s / 1e9;</pre></td><td valign="top">For each thread: <code>g</code> is the rate of this thread in GB/s. It is the bytes of the thread, divided by the time of the same thread, divided by 1e9.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">432                  total += r-&gt;bytes;
433                  if (r-&gt;elapsed_s &gt; max_el)
434                      max_el = r-&gt;elapsed_s;</pre></td><td valign="top">Add the bytes of the thread to <code>total</code>. Keep the longest thread time in <code>max_el</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">435                  if (g &lt; mn)
436                      mn = g;
437                  if (g &gt; mx)
438                      mx = g;
439                  sum += g;
440              }</pre></td><td valign="top">Keep the lowest and the highest thread rate. Add the thread rate to <code>sum</code> for the mean.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">441              double agg = (double)total / max_el / 1e9;</pre></td><td valign="top"><ul><li><code>agg</code>: the total rate of the interval in GB/s. It is the bytes of all threads, divided by the longest thread time, divided by 1e9.</li><li>The output column is <code>aggregate_GBps</code>.</li><li>A thread with a shorter time adds no bytes after its own stop. So <code>agg</code> is never above the sum of the thread rates.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">442              if (agg &gt; best)
443                  best = agg;</pre></td><td valign="top">Keep the highest <code>agg</code> of the repetitions in <code>best</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">444              printf("%s,%d,%lu,%d,%lu,%.4f,%.2f,%.2f,%.2f,%.2f\n", kernel_name[k], cfg.threads,
445                     (unsigned long)cfg.bytes, rep, (unsigned long)total, max_el, agg, mn, mx,
446                     sum / cfg.threads);
447          }</pre></td><td valign="top">Print one interval row. Its columns are:<ul><li>the kernel name, the thread count, the buffer size per thread in bytes, the repetition number (counted from 0)</li><li><code>total_bytes</code>: <code>total</code></li><li><code>elapsed_s</code>: <code>max_el</code>, with 4 decimals</li><li><code>aggregate_GBps</code>: <code>agg</code>, with 2 decimals</li><li>the lowest, the highest and the mean thread rate in GB/s, with 2 decimals. The mean is <code>sum / cfg.threads</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">448          printf("%s,%d,%lu,best,,,%.2f,,,\n", kernel_name[k], cfg.threads, (unsigned long)cfg.bytes, best);</pre></td><td valign="top">After the last repetition: print the <code>best</code> row. Its column <code>aggregate_GBps</code> holds the highest <code>agg</code> of the repetitions. The columns <code>total_bytes</code> and <code>elapsed_s</code> and the three thread-rate columns are empty. The analysis scripts stat_k120.py and facts_data.py do not use this row [Ref4].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">449          if (cfg.per_thread) {
450              /* thread,&lt;index&gt;,&lt;cpu&gt;,&lt;kernel&gt;,&lt;rep&gt;,&lt;GB/s&gt;: one line per thread and repetition, so that
451               * concurrent per-group totals can be formed from one repetition (reviewer's request) */</pre></td><td valign="top">Only with <code>--per-thread</code>: print one more line per thread and repetition. ra.sh does not pass this option, and the files of the whole-chip test hold no such line [Ref3] [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">452              for (int i = 0; i &lt; cfg.threads; i++)
453                  for (int rep = 0; rep &lt; cfg.reps; rep++) {
454                      struct result *r = &amp;th[i].res[k][rep];
455                      printf("thread,%d,%d,%s,%d,%.2f\n", i, th[i].cpu, kernel_name[k], rep, (double)r-&gt;bytes / r-&gt;elapsed_s / 1e9);
456                  }
457          }</pre></td><td valign="top">Each line holds the word <code>thread</code>, the thread index, the CPU, the kernel, the repetition and the thread rate in GB/s. The rate is the bytes of the thread, divided by the time of the same thread, divided by 1e9.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">458          fflush(stdout);
459      }</pre></td><td valign="top"><code>fflush</code> writes the buffered rows of this kernel to the output now.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">460      for (int i = 0; i &lt; cfg.threads; i++)
461          pthread_join(th[i].tid, NULL);
462      return 0;
463  }</pre></td><td valign="top">Wait until every worker thread has ended. Then end the process with exit status 0.</td></tr>
</table>

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
