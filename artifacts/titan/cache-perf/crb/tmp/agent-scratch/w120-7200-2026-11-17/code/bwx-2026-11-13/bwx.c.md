# `bwx.c` explained, line by line

- Source file: `bwx-2026-11-13/bwx.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 1358 lines, 50894 bytes).
- sha256 of the source when this page was built: `4ed33a8b8f6e5b817dac6367aed84139781ee217072e53da42f73c59322ce10d`.

## Short version: purpose

`bwx.c` is the source of `bwx`, the first runner: the benchmark program for Parts B and C of the test plan of 2026-11-13. It is a copy of the benchmark `bandwidth.c` that times a sequence of kernels in one process (option `--seq`), one timed interval per entry and round, and prints one row per interval and one row per thread. It follows the sections B.1 to B.8 of the file `handoff.md` [Ref4], with the deviations that the file `DEVIATIONS-bwx.md` lists [Ref7].

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
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
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop rules of the runner**: `--stop pass` selects the whole-pass stop. `--stop common` selects the common stop.
- **Kernel table, `kernels[]`**: the array of lines 816 to 826. Each entry holds the name of a kernel (the word used in `--seq`), its type (`T_READ`, `T_WRITE`, `T_COPY` or `T_OLDREAD`) and a pointer to its function. It has 21 entries.
- **`cfg`**: the structure that holds the settings from the arguments: thread count, CPU list, buffer size, kernel sequence, rounds, stop rule and counter settings (lines 175 to 193).
- **CPU list of `--cpus`**: the CPUs that the option `--cpus` names, in the order of its text. Thread `i` is pinned to entry `i` of the list. When the process has more threads than the list has entries, the list is used again from its start.
- **Allowed CPU set**: the set of CPUs on which Linux may run a thread.
- **Worker, main thread**: a worker is one benchmark thread (function `worker`). The main thread runs `main`: it starts the workers, sets the start time of each interval and prints all rows.
- **Barrier**: a POSIX thread barrier (`pthread_barrier_wait`). A thread that calls it blocks until all workers and the main thread have called it. Then all of them continue.
- **Warm-up pass**: one call of the kernel of the coming interval over its whole range, before the start of that interval. It is not timed.
- **Chunk**: a piece of 2 MiB of a buffer (`CHUNK_BYTES`), or the whole range of a `--seq` entry when that is smaller. With `--stop common` the worker calls the kernel on one chunk and then reads the clock.
- **Common start, lead**: with `--stop common` the main thread sets the start time of an interval to its clock reading plus 2 ms (`LEAD_NS`, the lead). Every worker waits for this time in a loop that only reads the clock.
- **Deadline**: the common start time plus the `--min-ms` value. A worker stops at its first clock read at or after the deadline.
- **`gen`**: an atomic counter of intervals. The main thread adds 1 after it has stored the start time and the deadline of the next interval. A worker waits until `gen` equals its own interval count plus 1.
- **Late flag**: the word `late` in the last column of a T row. It marks a thread whose start clock read was more than 100 us after the common start time.
- **us**: microsecond. 1 us is 1000 ns.
- **`sink`**: a volatile variable on the stack of each worker. `call` stores there the sum that an old read kernel returns. So the compiler cannot remove the adds of the old read kernel.
- **I, T, P, C rows**: the row kinds of the output: one I row per interval, one T row per thread and interval, one P row per buffer and page-state reading, and with `--count` one C row per thread and interval with counter values.
- **Page state**: two values of a buffer from the Linux file `/proc/self/smaps`: the size of its mapping and the part of it on 2 MiB pages, both in kB of 1024 bytes.
- **PMU, PMU type, event code**: PMU means performance monitoring unit, the hardware event counters of a core. The value of `--pmu-type` and the code of an event of `--events` go into the fields `type` and `config` of the structure `perf_event_attr`. The two fields tell Linux which event to count.
- **Counter group, group leader**: the counters that one thread opens form a group. The first one is the leader. One `read` of the leader returns the values of all counters of the group.
- **Enabled time, running time**: two times of a counter group, in ns: how long the counters were enabled, and how long they really counted.
- **File descriptor**: the number that Linux returns when a program opens a file or a counter.
- **AArch64, NEON**: AArch64 is the 64-bit Arm instruction set. NEON is the vector part of it: 32 registers of 16 bytes, written `v0` to `v31`, or `q0` to `q31` when an instruction uses all 16 bytes, or `d0` to `d31` for the low 8 bytes.
- **`ldp`, `stp`, `nop`**: AArch64 instructions. `ldp` loads two registers from memory, and `stp` stores two. With `q` registers each of them moves 32 B. `nop` does nothing.
- **Loop pass**: one run of the loop body of a kernel. It is not a pass over the whole buffer.
- **64 B line**: a block of 64 bytes of memory, a cache line. The source comments count memory in such lines.
- **Clobber list**: the last list of a gcc `__asm__` statement. It names the registers and the other state that the assembly text changes.
- **Save of `d8` to `d15`**: the Arm calling rules say that a function must keep the registers `d8` to `d15` for its caller. A kernel whose clobber list names `v8` to `v15` stores them on the stack once at its start and loads them back once at its end.
- **`PLACE`, pad, loop offset**: `PLACE(name)` is a macro that stands before each kernel. It adds unused bytes, the pad. The kernel then starts at a chosen address modulo 64. The aim is a fixed loop offset: the address of the first instruction of the loop modulo 64.
- **`LOOP`, `HEAD`, `PAD`**: the values of the loop placement. `LOOP` is the planned loop offset of a kernel. `HEAD` is the number of bytes of code between the start of the function and the start of its loop. `PAD` is the number of zero bytes that `PLACE` adds. The macro `PADOF` computes it as `LOOP` minus `HEAD`, modulo 64.
- **Stand-in**: a plain C loop that replaces a NEON kernel or an assembly kernel when the file is compiled for a machine that is not AArch64. The rates of such a build mean nothing.
- **Development machine**: the machine on which the program was written and tested before the build on CRB. The stand-in kernels exist for it.
- **A/A copy**: the same kernel source under a second name, for example `asmread2`.
- **First runner**: `bwx`, the program of this file. It is the first version of the runner. A row that says "the first runner" means this program.
- **`handoff.md`, specification v1**: `handoff.md` is the handoff note of the test plan. Its sections B.1 to B.8 are the specification of this program, called specification v1. The comments cite the sections B.4 to B.8 [Ref4].
- **`DEVIATIONS-bwx.md`**: the note in the folder of `bwx.c` that lists every difference between the program and specification v1 [Ref7].
- **Steps B2, B3 and B5**: steps of Part B of the test plan [Ref4]. Step B2 uses the kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. Step B3 uses the builds with the copy loops at 0, 36 and 52 modulo 64. Step B5 uses the kernels `read_nop4` to `read_nop32` and `read_sparse`.
- **Build record**: the files that the build script `build.sh` wrote on CRB. `build.txt` holds the compiler, the flags and the sha256 values [Ref2]. `listing.txt` holds the machine-code listing of every kernel of every binary [Ref1]. There are two build records, of two builds on 2026-11-13.
- **The four binaries**: `build.sh` compiles `bwx.c` four times: `bwx` without `B3_OFFSET`, and `bwx_o0`, `bwx_o36` and `bwx_o52` with `-DB3_OFFSET=0`, `-DB3_OFFSET=36` and `-DB3_OFFSET=52`. A machine-code fact of this page is a fact of the binary `bwx` unless the text names another binary.

## Main flow

1. Start. `main` reads the clock once for the process start time `t_base_ns`, reads the page size and sets the default buffer size of 1 MiB. Then `restrict_cpus` removes every CPU above 119 from the allowed CPU set of the process (lines 1139 to 1146).
2. Argument parsing. One loop over the arguments fills the settings structure `cfg`: threads, CPU list, bytes per thread, interval length, rounds, the `--seq` list, the stop rule, the start rule and the counter settings. `--selftest` and `--list` end the program in this loop (lines 1148 to 1200).
3. Checks of the settings. A failed check prints the option summary and ends the program with exit status 2. Each `--seq` entry without `@SIZE` gets the size of `--bytes`, and a copy kernel in the list gives each thread a second buffer (lines 1201 to 1232).
4. Threads. `main` creates a barrier for all workers plus itself and starts one thread per worker. Thread `i` gets entry `i` of the CPU list (lines 1234 to 1248).
5. Each worker pins itself to its CPU, opens its counters when `--count` is given, maps its buffer with `alloc_buf` and writes every word of the `--bytes` range of it once with `k_write`. This write is the first touch (lines 983 to 992).
6. Header. `main` prints the header lines: the settings and the column names of the I, T, P and C rows (lines 1250 to 1269).
7. Only in a process with more than one thread: when all buffers exist, `main` reads the page state of all buffers and prints P rows with the position -1 (lines 1273 to 1281, lines 1337 to 1351).
8. Loops. The workers and `main` run the same two loops: the rounds, and inside a round the positions of the `--seq` list. One pair of round and position is one interval (lines 998 to 999, lines 1271 to 1272).
9. Warm-up pass. Each worker calls the kernel of the position once over the whole range of the entry. This call is not timed (line 1011).
10. Common start, only with `--stop common`. When all workers wait at the barrier, `main` reads the clock, sets the start time to that value plus 2 ms and the deadline to the start time plus the `--min-ms` value, and then adds 1 to `gen` (lines 1289 to 1294). Each worker waits for the new `gen` and then reads the clock in a loop until the start time (lines 1018 to 1025).
11. Start of the timed interval. With `--count` the worker first reads its counter group and its thread CPU time. Then it reads the clock: `t0` (lines 1026 to 1030).
12. Timed loop with `--stop common`. The worker calls the kernel on one chunk of 2 MiB, adds the size of the chunk to its byte count and reads the clock: `t1`. It repeats this with the next chunk until `t1` is at or after the deadline (lines 1032 to 1043).
13. Timed loop with `--stop pass`. The worker runs whole passes over the range of the entry. It reads the clock after each group of passes: 8 MiB divided by the size of the range, rounded down, and at least 1 pass. It repeats this until the `--min-ms` time has passed after `t0` (lines 1044 to 1058).
14. End of the interval, worker. The worker reads its thread CPU time and its counter group again. It stores the byte count, `t0`, the last `t1`, the common start time and the late flag, and it waits at the barrier (lines 1059 to 1073).
15. I row. `main` adds the bytes of all threads and takes the longest elapsed time `t1 - t0` of one thread. The last column of the I row is the total divided by that time, in GB/s (lines 1298 to 1310).
16. T rows and C rows. `main` prints one T row per thread with its bytes and its times, and with `--count` one C row per thread with the change of its counters over the interval (lines 1311 to 1335).
17. Page state, in a process with more than one thread. While the workers wait at the barrier, `main` reads the page state of all buffers. Then it releases the workers and prints the P rows and one `# page_read` line (lines 1337 to 1351). In a process with one thread the worker reads the page state itself before each interval, and `main` prints its P rows before the I row (lines 1012 to 1016, lines 1304 to 1308).
18. End. After the last interval `main` waits for the end of all threads and returns 0 (lines 1355 to 1357).

## Behavior a reader must know

- Relation to the specification. The file `DEVIATIONS-bwx.md` lists 24 deviations from specification v1 [Ref7]. Three of them that a reader of results must know: in a process with more than one thread every worker waits at a second barrier after each interval, until `main` has read the page state (deviation 21, lines 1069 to 1073). The process keeps itself on the CPUs 0 to 119 (deviation 22, lines 276 to 279). The values of `--threads`, `--rounds` and `--pmu-type` must be whole numbers in a range, and a bad value ends the program with exit status 2 (deviation 23).
- A known limit from the same file: in a run with 120 threads the main thread has no CPU of its own. The 120 workers are pinned to all CPUs that the process may use, and the main thread is not pinned [Ref7].
- Difference to the next version: `bwx8.c` is this file with another header comment, with a second mode (the trial mode) in the place of the include of `bwx_selftest.c` (line 1137), and with three more lines in `main`. Every other line of this file stands in `bwx8.c`, in the same order.
- The four binaries. The binary `bwx` is the same in both build records: they give the same sha256 for it [Ref2] [Ref9]. In the listings the loops of `k_copy`, `k_asmcopy` and `k_asmcopy2` start at 0 modulo 64 in `bwx_o0` and at 36 modulo 64 in `bwx_o36` [Ref8].
- The binary `bwx_o52` differs between the two builds. In the first build the loop of `k_copy` started at 0 modulo 64: the listing of that build shows 3 `nop` instructions before the loop [Ref10]. The second build compiled `bwx_o52` with the added flag `-falign-loops=1`. Its loops of `k_copy`, `k_asmcopy` and `k_asmcopy2` start at 52 modulo 64. The same flag moved the loop of `k_oldwrite` in `bwx_o52` from 0 to 52 modulo 64 [Ref2] [Ref8] [Ref9].
- CRB build of `bwx`. The source of this page has the sha256 that both build records give for `bwx.c` [Ref2] [Ref9]. The listing holds the 21 kernels of each binary [Ref1]. Apart from absolute addresses, the kernels of the binary `bwx` have the instruction text of the kernels of `bw_new` and `bw_old` with the same source [Ref3].
- What is timed: only lines 1030 to 1042 or lines 1030 to 1056 of `worker`. The interval starts at the clock read `t0` and ends at the last clock read `t1`. Between them lie the kernel calls through `call`, the byte count and the clock reads. Not timed: allocation, first touch, warm-up pass, barrier waits, the wait for the common start, counter readings, page-state readings and all output.
- Stop rule `--stop common`: all threads get the same deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted (line 1043).
- Rate. The program prints one rate: the last column of the I row, the bytes of all threads divided by the longest elapsed time of one thread, in GB/s with GB = 1e9 bytes (line 1310). A T row holds the bytes and the elapsed time of one thread and no rate (line 1314).
- Kernel calls. With `--stop common` the kernel function is entered once per chunk. A kernel that saves `d8` to `d15` does so once per call, outside its loop. One clock read follows each call (lines 1037 to 1042).
- Thread placement: thread `i` pins itself to entry `i` of the CPU list before it opens its counters and before it maps its buffer (lines 983 to 987, line 1243). The main thread is not pinned.
- Buffers: each buffer is a private mapping of its own, and no two threads share a buffer. A thread has one buffer, or two with `--two-buffers` or with a copy kernel in `--seq`. A buffer starts at a 2 MiB boundary, and `alloc_buf` asks Linux for 2 MiB pages for it unless `--no-thp` is given. The pinned thread writes the `--bytes` range of the buffer once before any read. The read kernels never change it (lines 345 to 362, lines 987 to 988).
- Order inside a process: the kernels run in the order of `--seq`, and the rounds follow one another directly. The file holds no call of a sleep function. Before each timed interval the worker runs the warm-up pass with the kernel of that interval (line 1011).
- Counters: each thread opens its group once and never resets it. A C row holds the change between a reading directly before `t0` and a reading directly after the last `t1`. An event that does not open is printed as `NA` (line 942, lines 1329 to 1330).
- What ends a process with exit status 2: a bad argument, a failed `mmap`, a failed call that reads or sets the allowed CPU set, an allowed CPU set without a CPU from 0 to 119, a failed read of the counter group, and a failed setup in `main`. A failed `mprotect` or `madvise` in `alloc_buf` only writes a message, and the run continues (line 356, line 360).
- The code of this file does not look at the marker file and opens files only for reading. Its output is the csv text on the standard output and the messages on stderr.

## Source and explanation, line by line

- Text shown: the file `bwx-2026-11-13/bwx.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1358 lines, 50894 bytes, sha256 `4ed33a8b8f6e5b817dac6367aed84139781ee217072e53da42f73c59322ce10d`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: what `bwx.c` is, and the stand-in kernels (lines 1 to 16)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Opens the header comment of the file. It says what `bwx.c` is and which specification it follows. |
| 2 | ` * bwx.c - scratch copy of bench/bandwidth.c for Parts B and C of` | Comment: `bwx.c` is a scratch copy of the benchmark source `bandwidth.c` in the folder `bench`. It was made for Parts B and C of a test plan. The name of the plan follows in line 3. |
| 3 | ` * crb/new-test-kernel/plan.md. It follows "specification v1" of` | Comment: the test plan is the file `plan.md` in the folder `crb/new-test-kernel`. The next sentence starts here: the program follows a text that the comment calls specification v1. |
| 4 | ` * crb/new-test-kernel/handoff.md, sections B.1 to B.8. Every difference from` | Comment: specification v1 is the sections B.1 to B.8 of the file `handoff.md` in the same folder [Ref4]. The sentence about differences starts here. |
| 5 | ` * that specification is listed in DEVIATIONS-bwx.md.` | Comment: the file `DEVIATIONS-bwx.md` lists every difference between the program and that specification. It lies in the code folder `bwx-2026-11-13`, the folder of `bwx.c`. |
| 6 | ` *` | Comment: an empty line of the comment. |
| 7 | ` * Every thread owns its buffers (allocated and first-touched by that thread),` | Comment: every thread owns its buffers. The thread itself maps them and writes them for the first time (lines 987 to 988). |
| 8 | ` * so timing contains no page faults. One process times a sequence of kernels` | Comment: so, as the comment says, the timing contains no page faults. The first touch gives the pages their memory, and it is not timed (line 988). The next sentence starts here: one process times a sequence of kernels. |
| 9 | ` * (--seq), one interval per entry. All threads start an interval on a` | Comment: the option `--seq` gives the sequence. Each entry of the sequence is one timed interval. With `--rounds` above 1 the program runs the sequence again (line 998). The sentence about the start of an interval begins here. |
| 10 | ` * barrier. GB means 1e9 bytes throughout.` | Comment: all threads start an interval at a barrier (line 1017). The barrier wait is not the start of the timed interval: that is the clock read `t0` of each thread (line 1030). GB means 1e9 bytes in the whole file. |
| 11 | ` *` | Comment: an empty line of the comment. |
| 12 | ` * On AArch64 the kernels are the real ones. On any other machine every NEON` | Comment: on AArch64, the 64-bit Arm instruction set, the kernels are the real ones. The sentence about other machines starts here. |
| 13 | ` * and asm kernel is replaced by a plain C stand-in, so that the harness (rows,` | Comment: on any other machine a plain C loop replaces every NEON kernel and every assembly kernel. The comment calls this loop a stand-in. NEON is the vector part of AArch64. The reason starts here: the harness can then run on the development machine. The harness is the code around the kernels. |
| 14 | ` * barriers, page state, self-test) can be run on the development machine.` | Comment: the comment names the parts of the harness: the rows, the barriers, the page state and the self-test. With the stand-ins these parts can run on the development machine. |
| 15 | ` * Rates of a stand-in build mean nothing.` | Comment: the rates of a build with stand-ins mean nothing. |
| 16 | ` */` | Ends the comment. |

### Includes, constants and the highest CPU that the process may use (lines 17 to 52)

| Line | Source | Explanation |
|---:|---|---|
| 17 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include. It makes the Linux-specific declarations of the C library visible, for example `sched_setaffinity` and `CPU_SET`. |
| 18 | `#ifdef __aarch64__` | Compiles line 19 only when the compiler builds for AArch64, the 64-bit Arm instruction set. gcc defines the macro `__aarch64__` in that case. |
| 19 | `#include <arm_neon.h>` | Includes `arm_neon.h`. It declares the NEON intrinsics, for example `vld1q_u64`. An intrinsic is a C function that maps to one vector instruction. NEON is the vector part of AArch64. |
| 20 | `#endif` | Ends the `#ifdef` of line 18. |
| 21 | `#include <errno.h>` | Includes `errno.h`. It declares `errno`, the error number that a failed library call sets. `parse_long` tests it (lines 267 to 269). |
| 22 | `#include <linux/perf_event.h>` | Includes `linux/perf_event.h`. It declares the structure `perf_event_attr` and the `PERF_FORMAT` constants. `open_counters` (line 924) opens the hardware counters with them. |
| 23 | `#include <pthread.h>` | Includes `pthread.h`. It declares the thread functions `pthread_create` and `pthread_join` and the barrier function `pthread_barrier_wait`. |
| 24 | `#include <sched.h>` | Includes `sched.h`. It declares the CPU set type `cpu_set_t` and the calls `sched_getaffinity` and `sched_setaffinity`. They read and set the CPUs on which Linux may run a thread. |
| 25 | `#include <setjmp.h>` | Includes `setjmp.h`. It declares `sigsetjmp` and `siglongjmp`. No other line of this file uses them. The self-test file that this file includes uses them. |
| 26 | `#include <signal.h>` | Includes `signal.h`. It declares `sigaction` and the signal numbers. No other line of this file uses them. The included self-test file uses them to catch `SIGSEGV`, the signal that Linux sends at a forbidden memory access. |
| 27 | `#include <stdatomic.h>` | Includes `stdatomic.h`. It declares the atomic types and the functions `atomic_load`, `atomic_store` and `atomic_fetch_add`. The three variables of the common start use them (lines 234 to 236). |
| 28 | `#include <stdint.h>` | Includes `stdint.h`. It declares the integer types of fixed size, for example `uint64_t` (64 bits, without a sign) and `int64_t` (64 bits, with a sign). |
| 29 | `#include <stdio.h>` | Includes `stdio.h`. It declares the input and output functions, for example `printf`, `fprintf`, `fopen` and `fgets`. |
| 30 | `#include <stdlib.h>` | Includes `stdlib.h`. It declares `exit`, `strtol`, `strtod`, `calloc` and `getenv`. |
| 31 | `#include <string.h>` | Includes `string.h`. It declares the text and memory functions, for example `strcmp`, `strtok`, `memset` and `strerror`. |
| 32 | `#include <sys/mman.h>` | Includes `sys/mman.h`. It declares `mmap`, `mprotect` and `madvise`. `alloc_buf` (line 345) uses them for the buffers. |
| 33 | `#include <sys/syscall.h>` | Includes `sys/syscall.h`. It declares the numbers of the system calls, here `SYS_perf_event_open`. `open_counters` passes this number to `syscall` (line 937). |
| 34 | `#include <time.h>` | Includes `time.h`. It declares `clock_gettime` and the structure `timespec`. `now_ns` (line 238) reads the clock with them. |
| 35 | `#include <unistd.h>` | Includes `unistd.h`. It declares `sysconf`, `getpid` and `read`. |
| 37 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2097152 bytes (2 MiB), the size of one huge page. The expression is 2 shifted left by 20 bits. Every buffer starts at a multiple of this value (line 353). |
| 38 | `#define MAX_CPUS 1024` | `MAX_CPUS`: the `--cpus` list may hold at most 1024 CPUs (line 317). |
| 39 | `#define MAX_SEQ 64` | `MAX_SEQ`: the `--seq` list may hold at most 64 kernels (line 1101). |
| 40 | `#define MAX_EV 8` | `MAX_EV`: the `--events` list may hold at most 8 counter events (line 1118). |
| 41 | `#define CHECK_BYTES (8UL << 20) /* --stop pass: clock is read after at least this many bytes */` | `CHECK_BYTES`: 8388608 bytes (8 MiB). Comment: with `--stop pass` a thread reads the clock after at least this many bytes. For some sizes the code reads the clock earlier. The number of whole passes between two clock reads is this value divided by the size of the range, rounded down, and at least 1 (lines 1046 to 1048). So with a range of 3 MiB the thread reads the clock after 2 passes, which are 6 MiB. |
| 42 | `#define CHUNK_BYTES HUGE_BYTES  /* --stop common: clock is read after each chunk of this size */` | `CHUNK_BYTES`: the value of `HUGE_BYTES`, 2097152 bytes (2 MiB). It is the size of a chunk. Comment: with `--stop common` a worker calls the kernel on one chunk and then reads the clock (lines 1035 to 1042). When the range of a `--seq` entry is below 2 MiB, the chunk is that whole range (line 1035). |
| 43 | `#define LEAD_NS 2000000L        /* --stop common: the common start is this long after the barrier */` | `LEAD_NS`: 2000000 ns (2 ms). With `--stop common` the main thread reads the clock after its barrier wait and sets the common start time of an interval to that clock value plus 2 ms (lines 1289 to 1291). The release at the barrier is not the start of the timed interval. Each worker waits until the clock reaches the common start time (line 1023). Then it starts its timed interval with its own clock read `t0` (line 1030). |
| 44 | `#define LATE_NS 100000L         /* --stop common: flag "late" if a thread starts later than this */` | `LATE_NS`: 100000 ns (100 us, which is 0.1 ms). With `--stop common` a thread gets the flag `late` when its start clock read is more than this after the common start (line 1067). |
| 45 | `/* Highest CPU that the process may use. Rule of the test machine: CPUs 0 to` | Comment: the macro below gives the highest CPU number that the process may use. The rule of the test machine starts here: only the CPUs 0 to 119. |
| 46 | ` * 119 only, never 126 or 127. main() removes every higher CPU from the` | Comment: the end of the rule: never CPU 126 or CPU 127. `main` calls `restrict_cpus` (line 1146), which removes every higher CPU from the set of CPUs that Linux may use for the process. |
| 47 | ` * allowed set of the process, and --cpus rejects one. Another machine can` | Comment: the option `--cpus` also rejects a higher CPU (line 312). |
| 48 | ` * build with -DMAX_USE_CPU=N. */` | Comment: for another machine the build can set another limit with the compiler option `-DMAX_USE_CPU=N`. |
| 49 | `#ifndef MAX_USE_CPU` | Tests whether the build command has already defined `MAX_USE_CPU`. Only if not, line 50 is compiled. `restrict_cpus` (line 279) and `parse_cpus` (line 299) apply the limit. |
| 50 | `#define MAX_USE_CPU 119` | The default value: the highest CPU that the process may use is CPU 119. The CRB build of `bwx.c` gave no `-DMAX_USE_CPU` option, so this value was used [Ref2]. |
| 51 | `#endif` | Ends the `#ifndef` of line 49. |

### Loop placement: the macros `PLACE` and `PADOF` (lines 53 to 76)

| Line | Source | Explanation |
|---:|---|---|
| 53 | `/*` | Opens the comment about the placement of the kernel loops. |
| 54 | ` * Loop placement (handoff B.7). PLACE(name) stands directly before kernel` | Comment: the topic is the loop placement. The aim is that the loop of each kernel starts at a known address modulo 64, the loop offset. Section B.7 of the file `handoff.md`, the specification of this program, treats this offset as a test factor [Ref4]. The macro `PLACE(name)` stands directly before the kernel function. |
| 55 | ` * k_<name>. It pads .text to a 64 B boundary and then adds PAD_<name> zero bytes,` | Comment: the kernel function has the name `k_` plus the kernel name. `PLACE` first pads the code section `.text` to a 64 B boundary. Then it adds zero bytes. The macro `PAD_` plus the kernel name gives their number. |
| 56 | ` * so the function starts at PAD_<name> modulo 64. This needs the gcc flags` | Comment: so the function starts at that pad value modulo 64. The method needs two gcc flags. |
| 57 | ` * -fno-toplevel-reorder -falign-functions=4, and PAD must be a multiple of 4.` | Comment: the two flags are `-fno-toplevel-reorder` and `-falign-functions=4`. A pad must be a multiple of 4. Both flags are in the build record of CRB for `bwx.c` [Ref2]. |
| 58 | ` *` | Comment: an empty line of the comment. |
| 59 | ` * For a kernel with a planned loop offset, PAD = (LOOP - HEAD) mod 64. LOOP` | Comment: the rule for a kernel with a planned loop offset: the pad is `(LOOP - HEAD) mod 64`. |
| 60 | ` * is the planned offset of the loop start modulo 64. HEAD is the number of` | Comment: `LOOP` is the planned offset of the loop start, modulo 64. `HEAD` is a number of bytes. |
| 61 | ` * bytes between the function start and the loop start: 4 or 20 in the` | Comment: `HEAD` counts the bytes of code between the start of the function and the start of its loop. The comment gives the values 4 and 20. |
| 62 | ` * listings of bw_new (results/kernels-20261113T181222Z/probe.txt). HEAD is a` | Comment: these two values come from the listings of the binary `bw_new` in the file `probe.txt` of the result folder `kernels-20261113T181222Z`. `bw_new` is the benchmark binary of 2026-11-13 with the new kernels. In that file the loop of `k_copy` starts 4 bytes after the function start, and the loop of `k_asmcopy` 20 bytes after it [Ref3]. |
| 63 | ` * guess until the objdump listing of the CRB build confirms it: override it` | Comment: a `HEAD` value is a guess until the machine-code listing of the CRB build confirms it. |
| 64 | ` * with -DHEAD_<name>=N, or the whole pad with -DPAD_<name>=N.` | Comment: the build can replace one `HEAD` value with `-DHEAD_<name>=N`, or a whole pad with `-DPAD_<name>=N`. The CRB build of `bwx.c` used no such option: the variable `EXTRA` of the build script was empty [Ref2]. |
| 65 | ` * -DB3_OFFSET=0\|36\|52 puts the loops of copy, asmcopy and asmcopy2 at that` | Comment: the build option `-DB3_OFFSET=0`, `-DB3_OFFSET=36` or `-DB3_OFFSET=52` moves the loops of the kernels `copy`, `asmcopy` and `asmcopy2`. |
| 66 | ` * offset (step B3).` | Comment: these loops then start at that offset modulo 64 (lines 77 to 79). The option belongs to step B3 of the test plan of the first runner. |
| 67 | ` *` | Comment: an empty line of the comment. |
| 68 | ` * For the other kernels the default PAD is the start offset modulo 64 that` | Comment: the rule for every other kernel: the default pad is a start offset modulo 64 that the function has in an older binary. |
| 69 | ` * the function has in bw_new (new C and asm kernels) or in bw_old (old` | Comment: for a new C kernel or an assembly kernel the older binary is `bw_new`. For an old kernel it is `bw_old`. The old read kernel and the new read kernel show the result. The loop of `k_read` starts at 36 modulo 64 in the CRB binary `bwx` and in `bw_new`. The loop of `k_oldread` in `bwx` and the loop of `k_read` in `bw_old` both start at 40 modulo 64 [Ref1] [Ref3]. |
| 70 | ` * kernels). An A/A copy takes the PAD of its original.` | Comment: an A/A copy takes the pad of its original. An A/A copy is the same kernel source under a second name, for example `asmread2`. |
| 71 | ` */` | Ends the comment. |
| 72 | `#define STR2(x) #x` | `STR2(x)` turns its argument into a text in quotes. The preprocessor operator `#` does that. |
| 73 | `#define STR(x) STR2(x)` | `STR(x)` first replaces `x` by its value when `x` is a macro. Then it calls `STR2`. So with the default value 32 of `PAD_read`, `STR(PAD_read)` gives the text `"32"` and not the name in quotes. |
| 74 | `#define PLACE(name) __asm__(".pushsection .text\n.p2align 6\n.fill " STR(PAD_##name) ", 1, 0\n.popsection\n")` | `PLACE(name)` writes an `__asm__` statement outside of a function. gcc passes its text to the assembler without a change. `.pushsection .text` continues in the code section. `.p2align 6` pads the code up to an address that is a multiple of 64. `.fill N, 1, 0` adds N bytes of value 0. N is the value of the macro whose name `PAD_##name` builds from `PAD_` and the argument. `.popsection` returns to the section that was in use before. So the function that follows starts at N modulo 64. |
| 75 | `#define PADOF(loop, head) (((loop) - (head)) & 63)` | `PADOF(loop, head)`: `loop` minus `head`, modulo 64. The operation `& 63` keeps the low 6 bits. So a negative difference also gives a value from 0 to 63. |

### Planned loop offsets, head sizes and pads of the kernels (lines 77 to 163)

| Line | Source | Explanation |
|---:|---|---|
| 77 | `#ifdef B3_OFFSET` | Tests whether the build command defined `B3_OFFSET`. The build script compiles this file four times [Ref2]. The binary `bwx` gets no `B3_OFFSET`, so the `#else` branch of lines 80 to 82 is compiled for it. The binaries `bwx_o0`, `bwx_o36` and `bwx_o52` get `-DB3_OFFSET=0`, `-DB3_OFFSET=36` and `-DB3_OFFSET=52`. |
| 78 | `#define LOOP_copy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_copy`, the planned loop offset of the kernel `copy`, is N. |
| 79 | `#define LOOP_asmcopy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_asmcopy`, the planned loop offset of the kernel `asmcopy`, is N too. |
| 80 | `#else` | Starts the branch for a build without `B3_OFFSET`. |
| 81 | `#define LOOP_copy 36` | `LOOP_copy`: the loop of the kernel `copy` must start at 36 modulo 64. In the CRB binary of `bwx` the loop of `k_copy` starts at `0x3ae4`, which is 36 modulo 64 [Ref1]. |
| 82 | `#define LOOP_asmcopy 52` | `LOOP_asmcopy`: the loop of the kernel `asmcopy` must start at 52 modulo 64. In the CRB binary of `bwx` the loop of `k_asmcopy` starts at `0x40b4`, which is 52 modulo 64 [Ref1]. |
| 83 | `#endif` | Ends the `#ifdef` of line 77. |
| 84 | `#define LOOP_asmcopy_c 52` | `LOOP_asmcopy_c`: 52 modulo 64, the planned loop offset of the three kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg` (lines 109 to 117). `B3_OFFSET` does not change it. |
| 85 | `#ifndef HEAD_copy` | Compiles line 86 only when the build command has not defined `HEAD_copy`. Every value up to line 162 has this pattern of three lines: a default that a `-D` option of the build can replace. |
| 86 | `#define HEAD_copy 4` | `HEAD_copy`: 4 bytes of code, which is one instruction, stand between the start of `k_copy` and the start of its loop. The listing of the CRB build of `bwx` shows this distance [Ref1]. |
| 87 | `#endif` | Ends the `#ifndef` of line 85. |
| 88 | `#ifndef HEAD_asmcopy` | Compiles line 89 only when the build command has not defined `HEAD_asmcopy`. |
| 89 | `#define HEAD_asmcopy 20` | `HEAD_asmcopy`: 20 bytes of code, which are 5 instructions, stand before the loop of `k_asmcopy`. The listing of the CRB build of `bwx` shows them: 4 `stp` instructions that save the registers `d8` to `d15`, and the `add` that computes the end address [Ref1]. |
| 90 | `#endif` | Ends the `#ifndef` of line 88. |
| 91 | `#ifndef HEAD_asmcopy_c` | Compiles line 92 only when the build command has not defined `HEAD_asmcopy_c`. |
| 92 | `#define HEAD_asmcopy_c 4` | `HEAD_asmcopy_c`: 4 bytes of code stand before the loop of `k_asmcopy_c`. The listing of the CRB build of `bwx` shows this distance [Ref1]. |
| 93 | `#endif` | Ends the `#ifndef` of line 91. |
| 94 | `#ifndef HEAD_asmcopy_c_add` | Compiles line 95 only when the build command has not defined `HEAD_asmcopy_c_add`. |
| 95 | `#define HEAD_asmcopy_c_add 4` | `HEAD_asmcopy_c_add`: 4 bytes of code stand before the loop of `k_asmcopy_c_add`. The listing of the CRB build of `bwx` shows this distance [Ref1]. |
| 96 | `#endif` | Ends the `#ifndef` of line 94. |
| 97 | `#ifndef HEAD_asmcopy_c_reg` | Compiles line 98 only when the build command has not defined `HEAD_asmcopy_c_reg`. |
| 98 | `#define HEAD_asmcopy_c_reg 20` | `HEAD_asmcopy_c_reg`: 20 bytes of code stand before the loop of `k_asmcopy_c_reg`. This kernel saves `d8` to `d15`, as `asmcopy` does. The listing of the CRB build of `bwx` shows this distance [Ref1]. |
| 99 | `#endif` | Ends the `#ifndef` of line 97. |
| 100 | `#ifndef PAD_copy` | Compiles line 101 only when the build command has not defined `PAD_copy`. |
| 101 | `#define PAD_copy PADOF(LOOP_copy, HEAD_copy)` | `PAD_copy`: `PADOF` (line 75) computes it from the two values above. With the defaults it is (36 - 4) modulo 64 = 32 bytes. In the CRB binary of `bwx` the function `k_copy` starts at `0x3ae0`, which is 32 modulo 64 [Ref1]. |
| 102 | `#endif` | Ends the `#ifndef` of line 100. |
| 103 | `#ifndef PAD_asmcopy` | Compiles line 104 only when the build command has not defined `PAD_asmcopy`. |
| 104 | `#define PAD_asmcopy PADOF(LOOP_asmcopy, HEAD_asmcopy)` | `PAD_asmcopy`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx` the function `k_asmcopy` starts at `0x40a0`, which is 32 modulo 64 [Ref1]. |
| 105 | `#endif` | Ends the `#ifndef` of line 103. |
| 106 | `#ifndef PAD_asmcopy2` | Compiles line 107 only when the build command has not defined `PAD_asmcopy2`. |
| 107 | `#define PAD_asmcopy2 PAD_asmcopy` | `PAD_asmcopy2`: the A/A copy `asmcopy2` takes the pad of its original `asmcopy`. With the defaults that is 32 bytes. |
| 108 | `#endif` | Ends the `#ifndef` of line 106. |
| 109 | `#ifndef PAD_asmcopy_c` | Compiles line 110 only when the build command has not defined `PAD_asmcopy_c`. |
| 110 | `#define PAD_asmcopy_c PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c)` | `PAD_asmcopy_c`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx` the function `k_asmcopy_c` starts at `0x4230`, which is 48 modulo 64 [Ref1]. |
| 111 | `#endif` | Ends the `#ifndef` of line 109. |
| 112 | `#ifndef PAD_asmcopy_c_add` | Compiles line 113 only when the build command has not defined `PAD_asmcopy_c_add`. |
| 113 | `#define PAD_asmcopy_c_add PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_add)` | `PAD_asmcopy_c_add`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx` the function `k_asmcopy_c_add` starts at `0x42f0`, which is 48 modulo 64 [Ref1]. |
| 114 | `#endif` | Ends the `#ifndef` of line 112. |
| 115 | `#ifndef PAD_asmcopy_c_reg` | Compiles line 116 only when the build command has not defined `PAD_asmcopy_c_reg`. |
| 116 | `#define PAD_asmcopy_c_reg PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_reg)` | `PAD_asmcopy_c_reg`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx` the function `k_asmcopy_c_reg` starts at `0x43a0`, which is 32 modulo 64 [Ref1]. |
| 117 | `#endif` | Ends the `#ifndef` of line 115. |
| 118 | `#ifndef PAD_read` | Compiles line 119 only when the build command has not defined `PAD_read`. |
| 119 | `#define PAD_read 32` | `PAD_read` = 32: the new read kernel `k_read` starts at 32 modulo 64. In the CRB binary of `bwx` it starts at the address `0x3a20`, which is 32 modulo 64 [Ref1]. |
| 120 | `#endif` | Ends the `#ifndef` of line 118. |
| 121 | `#ifndef PAD_write` | Compiles line 122 only when the build command has not defined `PAD_write`. |
| 122 | `#define PAD_write 0` | `PAD_write` = 0: `k_write`, the function of the first touch, starts at 0 modulo 64. In the CRB binary of `bwx` it starts at the address `0x3a80` [Ref1]. |
| 123 | `#endif` | Ends the `#ifndef` of line 121. |
| 124 | `#ifndef PAD_asmread` | Compiles line 125 only when the build command has not defined `PAD_asmread`. |
| 125 | `#define PAD_asmread 0` | `PAD_asmread` = 0: `k_asmread` starts at 0 modulo 64. In the CRB binary of `bwx` it starts at the address `0x3b40` [Ref1]. |
| 126 | `#endif` | Ends the `#ifndef` of line 124. |
| 127 | `#ifndef PAD_asmread2` | Compiles line 128 only when the build command has not defined `PAD_asmread2`. |
| 128 | `#define PAD_asmread2 PAD_asmread` | `PAD_asmread2`: the A/A copy `asmread2` takes the pad of `asmread`, which is 0 bytes. |
| 129 | `#endif` | Ends the `#ifndef` of line 127. |
| 130 | `#ifndef PAD_asmwrite` | Compiles line 131 only when the build command has not defined `PAD_asmwrite`. |
| 131 | `#define PAD_asmwrite 32` | `PAD_asmwrite` = 32: `k_asmwrite` starts at 32 modulo 64. |
| 132 | `#endif` | Ends the `#ifndef` of line 130. |
| 133 | `#ifndef PAD_asmwrite2` | Compiles line 134 only when the build command has not defined `PAD_asmwrite2`. |
| 134 | `#define PAD_asmwrite2 PAD_asmwrite` | `PAD_asmwrite2`: the A/A copy `asmwrite2` takes the pad of `asmwrite`, which is 32 bytes. |
| 135 | `#endif` | Ends the `#ifndef` of line 133. |
| 136 | `#ifndef PAD_oldread` | Compiles line 137 only when the build command has not defined `PAD_oldread`. |
| 137 | `#define PAD_oldread 0` | `PAD_oldread` = 0: the old read kernel `k_oldread` starts at 0 modulo 64. In the CRB binary of `bwx` it starts at the address `0x3680` [Ref1]. |
| 138 | `#endif` | Ends the `#ifndef` of line 136. |
| 139 | `#ifndef PAD_oldread2` | Compiles line 140 only when the build command has not defined `PAD_oldread2`. |
| 140 | `#define PAD_oldread2 PAD_oldread` | `PAD_oldread2`: the A/A copy `oldread2` takes the pad of `oldread`, which is 0 bytes. |
| 141 | `#endif` | Ends the `#ifndef` of line 139. |
| 142 | `#ifndef PAD_oldwrite` | Compiles line 143 only when the build command has not defined `PAD_oldwrite`. |
| 143 | `#define PAD_oldwrite 32` | `PAD_oldwrite` = 32: `k_oldwrite` starts at 32 modulo 64. |
| 144 | `#endif` | Ends the `#ifndef` of line 142. |
| 145 | `#ifndef PAD_oldcopy` | Compiles line 146 only when the build command has not defined `PAD_oldcopy`. |
| 146 | `#define PAD_oldcopy 32` | `PAD_oldcopy` = 32: `k_oldcopy` starts at 32 modulo 64. |
| 147 | `#endif` | Ends the `#ifndef` of line 145. |
| 148 | `#ifndef PAD_read_nop4` | Compiles line 149 only when the build command has not defined `PAD_read_nop4`. |
| 149 | `#define PAD_read_nop4 PAD_asmread` | `PAD_read_nop4`: the kernel `read_nop4` takes the pad of `asmread`, which is 0 bytes. |
| 150 | `#endif` | Ends the `#ifndef` of line 148. |
| 151 | `#ifndef PAD_read_nop8` | Compiles line 152 only when the build command has not defined `PAD_read_nop8`. |
| 152 | `#define PAD_read_nop8 PAD_asmread` | `PAD_read_nop8`: the kernel `read_nop8` takes the pad of `asmread`, which is 0 bytes. |
| 153 | `#endif` | Ends the `#ifndef` of line 151. |
| 154 | `#ifndef PAD_read_nop16` | Compiles line 155 only when the build command has not defined `PAD_read_nop16`. |
| 155 | `#define PAD_read_nop16 PAD_asmread` | `PAD_read_nop16`: the kernel `read_nop16` takes the pad of `asmread`, which is 0 bytes. |
| 156 | `#endif` | Ends the `#ifndef` of line 154. |
| 157 | `#ifndef PAD_read_nop32` | Compiles line 158 only when the build command has not defined `PAD_read_nop32`. |
| 158 | `#define PAD_read_nop32 PAD_asmread` | `PAD_read_nop32`: the kernel `read_nop32` takes the pad of `asmread`, which is 0 bytes. |
| 159 | `#endif` | Ends the `#ifndef` of line 157. |
| 160 | `#ifndef PAD_read_sparse` | Compiles line 161 only when the build command has not defined `PAD_read_sparse`. |
| 161 | `#define PAD_read_sparse PAD_asmread` | `PAD_read_sparse`: the kernel `read_sparse` takes the pad of `asmread`, which is 0 bytes. |
| 162 | `#endif` | Ends the `#ifndef` of line 160. |

### Kernel types and one entry of the `--seq` list (lines 164 to 174)

| Line | Source | Explanation |
|---:|---|---|
| 164 | `enum ktype { T_READ, T_WRITE, T_COPY, T_OLDREAD };` | `enum ktype`: the four kernel types `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD`. The function `call` (line 833) chooses the argument list of a kernel by its type. |
| 165 | `typedef void (*read_fn)(const uint64_t *, size_t);` | `read_fn`: the function type of a read kernel (type `T_READ`). The kernel gets the start address and the number of 8-byte words. It returns nothing. |
| 166 | `typedef uint64_t (*oldread_fn)(const uint64_t *, size_t);` | `oldread_fn`: the function type of an old read kernel (type `T_OLDREAD`). The kernel gets the same two arguments and returns a 64-bit sum. |
| 167 | `typedef void (*write_fn)(uint64_t *, size_t, uint64_t);` | `write_fn`: the function type of a write kernel (type `T_WRITE`). The kernel gets the start address, the number of 8-byte words and the 64-bit value to store. |
| 168 | `typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);` | `copy_fn`: the function type of a copy kernel (type `T_COPY`). The kernel gets the destination address, the source address and the number of 8-byte words. `restrict` tells the compiler that the two ranges do not overlap. |
| 170 | `struct entry {` | Starts `struct entry`: one entry of the `--seq` list. |
| 171 | `    int k;          /* index into kernels[] */` | `k`: the index of the kernel in the kernel table `kernels[]` (line 816). |
| 172 | `    uint64_t bytes; /* 0 until main() replaces it by --bytes */` | `bytes`: the size of the range that the kernel works on, in bytes. It is 0 when the entry has no `@SIZE` part. `main` then sets it to the `--bytes` value (lines 1221 to 1222). |
| 173 | `};` | Ends `struct entry`. |

### The settings structure `cfg` (lines 175 to 194)

| Line | Source | Explanation |
|---:|---|---|
| 175 | `static struct {` | Starts the structure `cfg`. It holds the settings of the process. The code that reads the arguments fills it. |
| 176 | `    int threads;` | `threads`: the number of worker threads (`--threads`). |
| 177 | `    int ncpus;` | `ncpus`: the number of entries of `cpus`. |
| 178 | `    int cpus[MAX_CPUS];` | `cpus`: the CPU list of `--cpus`, in the order of the list. `parse_cpus` (line 299) fills it. |
| 179 | `    uint64_t bytes;` | `bytes`: the value of `--bytes` in bytes. It is the range of each buffer that the program uses: the first touch writes this many bytes (line 988), and no `--seq` entry may be larger (line 1223). The mapped buffer is this value rounded up to a multiple of 2 MiB (line 339). |
| 180 | `    double min_s;` | `min_s`: the `--min-ms` value in seconds. With `--stop common` the deadline of an interval is this long after its common start (line 1293). With `--stop pass` a thread runs at least this long (line 1057). |
| 181 | `    int use_thp;` | `use_thp`: 1 when the program asks Linux for 2 MiB pages (transparent huge pages) for the buffers. The option `--no-thp` sets it to 0. |
| 182 | `    struct entry seq[MAX_SEQ];` | `seq`: the kernel list of `--seq`, one `struct entry` per kernel. |
| 183 | `    int nseq;` | `nseq`: the number of entries of `seq`. |
| 184 | `    int rounds;` | `rounds`: how many times the list runs (`--rounds`). |
| 185 | `    int stop_common;  /* --stop common */` | `stop_common`: 1 with `--stop common`. With this stop rule all threads of an interval get the same deadline. |
| 186 | `    int start_offset; /* --start offset */` | `start_offset`: 1 with `--start offset`. Then the place in its buffer at which a thread starts an interval depends on the number of the thread (line 1004). The option chooses a place in the buffer. It does not set the start time of an interval. |
| 187 | `    int two_buffers;  /* buffer b exists: --two-buffers, or a copy kernel in the sequence */` | `two_buffers`: 1 when each thread has a second buffer `b`. The option `--two-buffers` sets it. `main` also sets it when the list holds a copy kernel (lines 1228 to 1229). |
| 188 | `    int count;        /* --count */` | `count`: 1 with `--count`. Then each thread opens hardware counters and reads them before and after each interval. |
| 189 | `    long pmu_type;    /* --pmu-type: the "type" field of perf_event_attr */` | `pmu_type`: the value of `--pmu-type`. It goes into the field `type` of the structure `perf_event_attr` (line 931). The field tells Linux which counter hardware to use. |
| 190 | `    int nev;` | `nev`: the number of counter events of `--events`. |
| 191 | `    char ev_name[MAX_EV][32];` | `ev_name`: the names of the events, at most 31 characters each. |
| 192 | `    uint64_t ev_code[MAX_EV];` | `ev_code`: the codes of the events. A code goes into the field `config` of `perf_event_attr` (line 933). |
| 193 | `} cfg = { .threads = 1, .min_s = 0.5, .use_thp = 1, .rounds = 1, .pmu_type = -1 };` | Ends the structure and sets the defaults: 1 thread, 0.5 s per interval, a request for 2 MiB pages, 1 round and no PMU type (the value -1). Every other field starts at 0. |

### Structures `page`, `counts`, `result` and `thread` (lines 195 to 226)

| Line | Source | Explanation |
|---:|---|---|
| 195 | `struct page {` | Starts `struct page`: the page state of one buffer. |
| 196 | `    long kb_total, kb_huge; /* -1: no exact entry in /proc/self/smaps */` | `kb_total`: the size of the mapping of the buffer. `kb_huge`: the part of it that lies on 2 MiB pages. Both are in kB (1 kB is 1024 bytes here). `read_smaps` (line 857) fills them. Comment: -1 means that the Linux file `/proc/self/smaps` has no exact entry for the buffer. Such a value is printed as `NA`. |
| 197 | `};` | Ends `struct page`. |
| 199 | `struct counts {` | Starts `struct counts`: one reading of the counters of a thread. |
| 200 | `    uint64_t cpu_ns;              /* CLOCK_THREAD_CPUTIME_ID */` | `cpu_ns`: the CPU time that the thread has used, in ns. The Linux clock `CLOCK_THREAD_CPUTIME_ID` gives it (line 954). |
| 201 | `    uint64_t enabled, running;    /* of the counter group */` | `enabled` and `running`: two times of the counter group in ns. They say how long the counters were enabled and how long they really counted. |
| 202 | `    uint64_t val[MAX_EV];` | `val`: one count per event that opened. |
| 203 | `};` | Ends `struct counts`. |
| 205 | `/* One thread, one interval. Written by the worker between the start barrier` | Comment: the structure below holds the result of one thread for one interval. The worker writes it after the start barrier of the interval. The start barrier is the barrier wait that stands before the timed interval (line 1017). The timed interval of a thread does not start at this barrier. It starts later, at the clock read `t0` of the thread (line 1030). |
| 206 | ` * and the end barrier of the interval; read by main() after the end barrier. */` | Comment: the worker writes it before the end barrier of the interval, and `main` reads it after that barrier. In the code the worker stores the structure at line 1068, before its barrier wait of line 1069. `main` reads it after its barrier wait of line 1296. So the two threads never use it at the same time. |
| 207 | `struct result {` | Starts `struct result`. |
| 208 | `    uint64_t bytes;` | `bytes`: the bytes that the thread counted in the interval (line 1063). |
| 209 | `    int64_t t_sched, t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_sched`: the common start time. `t_start`: the start clock read `t0` of the thread. `t_end`: its last clock read `t1`. All three are values of the clock `CLOCK_MONOTONIC` in ns (lines 1064 to 1066). With `--stop pass` there is no common start, and `t_sched` gets the value of `t0`. |
| 210 | `    int late;` | `late`: the late flag. It is 1 when `t0` of the thread was more than `LATE_NS` after the common start (line 1067). |
| 211 | `    struct page pg[2]; /* one-thread process only: read by the worker before the interval */` | `pg`: the page state of the buffers `a` and `b`. Comment: only a process with one thread uses it. There the worker reads the page state before the interval (lines 1012 to 1016). |
| 212 | `    long long vm[4];` | `vm`: four counters of the Linux file `/proc/vmstat` (line 887). As for `pg`, only the worker of a process with one thread fills it. |
| 213 | `    struct counts c0, c1;` | `c0` and `c1`: the counter readings before `t0` (lines 1027 to 1028) and after the last `t1` (lines 1060 to 1061). |
| 214 | `};` | Ends `struct result`. |
| 216 | `struct thread {` | Starts `struct thread`: one record per worker. |
| 217 | `    int idx;` | `idx`: the number of the thread, counted from 0 (line 1242). |
| 218 | `    int cpu;` | `cpu`: the CPU that the thread pins itself to, or -1 without `--cpus` (line 1243). |
| 219 | `    uint64_t *a, *b;` | `a`: the buffer of the thread. `b`: the second buffer, which only a copy kernel or `--two-buffers` needs. Without it `b` stays `NULL`. |
| 220 | `    int group_fd;      /* leader of the counter group, -1 if no event opened */` | `group_fd`: the file descriptor of the leader of the counter group. A file descriptor is the number that Linux returns for an open object. Comment: it is -1 when no event opened. `open_counters` (line 924) sets it. |
| 221 | `    int ev_pos[MAX_EV]; /* position of the event in the group read, -1 if it did not open */` | `ev_pos`: for each event its position among the values of a group read. Comment: -1 when the event did not open. |
| 222 | `    int nopen;` | `nopen`: the number of events that opened. |
| 223 | `    struct result res;` | `res`: the result of the last interval of this thread. |
| 224 | `    pthread_t tid;` | `tid`: the thread handle that `pthread_create` returns (line 1244). |
| 225 | `};` | Ends `struct thread`. |

### Global variables: the barrier, the base time and the common start (lines 227 to 237)

| Line | Source | Explanation |
|---:|---|---|
| 227 | `static pthread_barrier_t bar;` | `bar`: the barrier. A thread that calls `pthread_barrier_wait` on it blocks until all workers and the main thread have called it. `main` creates it for the number of workers plus 1 (line 1237). |
| 228 | `static int64_t t_base_ns; /* clock at process start: printed times are relative to it */` | `t_base_ns`: the clock value at the process start (line 1143). Comment: the printed times are relative to it. |
| 229 | `static long page_bytes;` | `page_bytes`: the page size that Linux reports, in bytes (line 1144). `alloc_buf` uses it (line 353). |
| 231 | `/* --stop common (handoff B.4). gen only grows. main() stores the two times` | Comment: the three variables below belong to `--stop common`. The comment cites section B.4 of the file `handoff.md`, the specification of the first runner. `gen` only grows. |
| 232 | ` * before it increments gen, so a worker that sees the new gen reads the new` | Comment: `main` stores the two times before it adds 1 to `gen` (lines 1292 to 1294). A worker first waits for the new value of `gen` (line 1019). |
| 233 | ` * times. */` | Comment: then the worker loads the two times (lines 1021 to 1022). So it never uses the times of the interval before. |
| 234 | `static _Atomic uint64_t gen;` | `gen`: an atomic counter of intervals. It starts at 0. `_Atomic` makes every load and every store of the variable one indivisible step. |
| 235 | `static _Atomic int64_t t_sched_ns;` | `t_sched_ns`: the common start time of the coming interval, as a value of the clock `CLOCK_MONOTONIC` in ns. With `--stop common` every worker waits until the clock reaches this time (line 1023). The timed interval of a worker starts after that, at its own clock read `t0` (line 1030). |
| 236 | `static _Atomic int64_t deadline_ns;` | `deadline_ns`: the common deadline of the coming interval: the common start time plus the `--min-ms` value (line 1293). With `--stop common` a worker ends its timed interval at its first clock read `t1` at or after this deadline (lines 1042 to 1043). So each worker finishes the chunk that it is in. |

### Function `now_ns`: read the clock (lines 238 to 244)

| Line | Source | Explanation |
|---:|---|---|
| 238 | `static int64_t now_ns(void)` | Starts the function `now_ns`. It reads the clock and returns the time in ns. Every time stamp of the program comes from this function. In a timed interval the worker calls it once for the start `t0` (line 1030). With `--stop common` it then calls it once after each chunk for `t1` (line 1042). A chunk is 2 MiB, or the whole range of the `--seq` entry when that is smaller. So one clock read per chunk is inside the timed interval. This is the same for every kernel. |
| 239 | `{` | Opens the body of `now_ns`. |
| 240 | `    struct timespec ts;` | `ts`: a `timespec`, the structure for a time as whole seconds plus ns. |
| 241 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | `clock_gettime` reads the Linux clock `CLOCK_MONOTONIC` into `ts`. This clock cannot be set. It does not jump when the date or the time of the system is changed. |
| 242 | `    return (int64_t)ts.tv_sec * 1000000000L + ts.tv_nsec;` | Returns the seconds times 1000000000 plus the ns part: the time in ns as one 64-bit number. |
| 243 | `}` | Ends the function `now_ns`. |

### Function `parse_bytes`: a size text such as `256M` (lines 245 to 261)

| Line | Source | Explanation |
|---:|---|---|
| 245 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `256M` into a number of bytes. `main` calls it for `--bytes` (line 1169). `parse_seq` calls it for the `@SIZE` part of a `--seq` entry (line 1106). |
| 246 | `{` | Opens the body of `parse_bytes`. |
| 247 | `    char *end;` | `end`: `strtod` sets it to the first character after the number. |
| 248 | `    double v = strtod(s, &end);` | `strtod` reads a decimal number from the start of the text into `v`. The number may have a fraction, for example `1.5`. |
| 249 | `    double mul = 1;` | `mul`: the factor of the unit letter. It stays 1 when no letter follows the number. |
| 250 | `    switch (*end) {` | Looks at the character after the number. |
| 251 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | The letter `k` or `K`: the factor is 1024. `end++` moves `end` to the character after the letter. |
| 252 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | The letter `m` or `M`: the factor is 1048576, which is 1 MiB. So the text `256M` gives 256 times 1048576, which is 268435456 bytes. |
| 253 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | The letter `g` or `G`: the factor is 1073741824, which is 1024 MiB. |
| 254 | `    }` | Ends the `switch` of line 250. |
| 255 | `    if (end == s \|\| *end != '\0' \|\| v <= 0 \|\| (uint64_t)(v * mul) == 0) { /* 0 bytes after rounding is no size */` | Tests four error cases. The text holds no number (`end == s`). Other text follows the size. The value is 0 or below. The size is 0 bytes after the conversion to a whole number. Comment: 0 bytes after rounding is no size. |
| 256 | `        fprintf(stderr, "bad size: %s\n", s);` | In an error case: prints `bad size:` and the text to stderr, the error output of the program. |
| 257 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 258 | `    }` | Ends the `if` of line 255. |
| 259 | `    return (uint64_t)(v * mul);` | Returns the size in bytes as a whole number. The conversion drops a fraction of a byte. |
| 260 | `}` | Ends the function `parse_bytes`. |

### Function `parse_long`: a whole number inside a range (lines 262 to 275)

| Line | Source | Explanation |
|---:|---|---|
| 262 | `/* A whole number in [lo, hi], with nothing after it. Anything else ends the` | Comment: the function below accepts only a whole number from `lo` to `hi` with no text after it. |
| 263 | ` * program: a malformed value must not run as 0. */` | Comment: any other text ends the program. The reason: a malformed value must not run as the number 0. |
| 264 | `static long parse_long(const char *s, const char *what, long lo, long hi)` | Starts the function `parse_long`. It turns the text `s` into a whole number inside the range `lo` to `hi`. `what` is the name of the option, for the error message. `main` reads `--threads` (allowed 1 to 4096), `--rounds` (1 to 1000000) and `--pmu-type` (0 to 2147483647) with it (line 1164, line 1179, line 1194). |
| 265 | `{` | Opens the body of `parse_long`. |
| 266 | `    char *end;` | `end`: `strtol` sets it to the first character after the number. |
| 267 | `    errno = 0;` | Sets `errno` to 0. `strtol` sets it to an error value when the number does not fit the type `long`. |
| 268 | `    long v = strtol(s, &end, 10);` | `strtol` reads a decimal whole number (base 10) from the start of the text into `v`. |
| 269 | `    if (end == s \|\| *end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi) {` | Tests the error cases: no digit was read, other text follows the number, the number does not fit the type `long`, or it lies outside the range `lo` to `hi`. |
| 270 | `        fprintf(stderr, "bad %s: '%s' (a whole number from %ld to %ld is needed)\n", what, s, lo, hi);` | In an error case: prints `bad`, the option name, the text and the allowed range to stderr. |
| 271 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 272 | `    }` | Ends the `if` of line 269. |
| 273 | `    return v;` | Returns the number. |
| 274 | `}` | Ends the function `parse_long`. |

### Function `restrict_cpus`: no CPU above `MAX_USE_CPU` (lines 276 to 297)

| Line | Source | Explanation |
|---:|---|---|
| 276 | `/* Removes every CPU above MAX_USE_CPU from the allowed set of the calling` | Comment: the function below removes every CPU above `MAX_USE_CPU` from the allowed set of the calling thread. The allowed set is the set of CPUs on which Linux may run the thread. |
| 277 | ` * thread. main() calls it before it starts a thread, so the main thread and` | Comment: `main` calls the function before it starts a thread (line 1146). A new thread takes over the allowed set of the thread that creates it. |
| 278 | ` * every worker (also one without --cpus) stay on the permitted CPUs. */` | Comment: so the main thread and every worker stay on the permitted CPUs. This also holds for a worker of a run without `--cpus`. |
| 279 | `static void restrict_cpus(void)` | Starts the function `restrict_cpus`. |
| 280 | `{` | Opens the body of `restrict_cpus`. |
| 281 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 282 | `    int changed = 0;` | `changed`: becomes 1 when the set held a CPU above the limit. |
| 283 | `    if (sched_getaffinity(0, sizeof set, &set) != 0) {` | `sched_getaffinity` with the first argument 0 reads the allowed set of the calling thread into `set`. A return value other than 0 means that the call failed. |
| 284 | `        perror("sched_getaffinity");` | On failure: `perror` prints the word `sched_getaffinity` and the reason that Linux gave. |
| 285 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 286 | `    }` | Ends the `if` of line 283. |
| 287 | `    for (int c = MAX_USE_CPU + 1; c < CPU_SETSIZE; c++)` | Starts a loop over every CPU number above `MAX_USE_CPU`, up to `CPU_SETSIZE - 1`. `CPU_SETSIZE` is the number of CPUs that the set type of the C library can hold. With the default limit the loop starts at CPU 120. |
| 288 | `        if (CPU_ISSET(c, &set)) {` | Tests whether the set holds the CPU `c`. |
| 289 | `            CPU_CLR(c, &set);` | Removes the CPU `c` from the set. |
| 290 | `            changed = 1;` | Records that the set was changed. |
| 291 | `        }` | Ends the `if` of line 288. |
| 292 | `    if (changed && (CPU_COUNT(&set) == 0 \|\| sched_setaffinity(0, sizeof set, &set) != 0)) {` | Runs only when a CPU was removed. An empty set is an error. If the set is not empty, `sched_setaffinity` passes the smaller set to Linux, and a failed call is an error too. When the process starts with an allowed set that holds no CPU above `MAX_USE_CPU`, `changed` stays 0, and the function changes nothing. |
| 293 | `        fprintf(stderr, "cannot keep the process on CPUs 0-%d\n", MAX_USE_CPU);` | On error: prints `cannot keep the process on CPUs 0-` and the limit to stderr. |
| 294 | `        exit(2);` | On error: the whole program ends with exit status 2. |
| 295 | `    }` | Ends the `if` of line 292. |
| 296 | `}` | Ends the function `restrict_cpus`. |

### Function `parse_cpus`: the value of `--cpus` (lines 298 to 325)

| Line | Source | Explanation |
|---:|---|---|
| 298 | `/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */` | Comment: three examples of a CPU list: `0-119`, `0,2,4-7` and `0-118:2`. The last one is a range with a stride: every second CPU from 0 to 118. |
| 299 | `static void parse_cpus(char *list)` | Starts the function `parse_cpus`. It turns the value of `--cpus` into the array `cfg.cpus`, in the order of the list. |
| 300 | `{` | Opens the body of `parse_cpus`. |
| 301 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Starts a loop over the items of the list. `strtok` splits the text at each comma and returns one item per call. It writes into the text to do that. |
| 302 | `        char *e, *e2;` | `e` and `e2`: positions in the item that `strtol` sets. |
| 303 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the item into `lo`. `hi` starts with the same value and `step` with 1. So an item that is one number names one CPU. |
| 304 | `        if (e != tok && *e == '-') {` | When a number was read and a `-` follows it: the item is a range. |
| 305 | `            hi = strtol(e + 1, &e2, 10);` | Reads the upper bound of the range into `hi`. |
| 306 | `            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */` | When no digit follows the `-`, `e` is set back to `tok`, and the test of line 312 then rejects the item. If a number was read, `e` moves to the character after it. Comment: the item `0-` has no upper bound. |
| 307 | `            if (e != tok && *e == ':') {` | When the upper bound was read and a `:` follows it: the range has a stride. |
| 308 | `                step = strtol(e + 1, &e2, 10);` | Reads the stride into `step`. |
| 309 | `                e = e2 == e + 1 ? tok : e2;` | When no digit follows the `:`, `e` is set back to `tok`, and the test of line 312 rejects the item. If a number was read, `e` moves to the character after it. |
| 310 | `            }` | Ends the `if` of line 307. |
| 311 | `        }` | Ends the `if` of line 304. |
| 312 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| hi > MAX_USE_CPU \|\| step < 1) {` | Rejects an item in six cases: it holds no number, other text follows, the start is negative, the end is below the start, the end is above `MAX_USE_CPU` (119 with the default), or the stride is below 1. |
| 313 | `            fprintf(stderr, "bad cpu list: %s (CPUs 0-%d only)\n", tok, MAX_USE_CPU);` | On such an item: prints `bad cpu list:`, the item and the permitted range to stderr. |
| 314 | `            exit(2);` | On such an item: the whole program ends with exit status 2. |
| 315 | `        }` | Ends the `if` of line 312. |
| 316 | `        for (long c = lo; c <= hi; c += step) {` | Starts a loop over the CPU numbers of the item, from `lo` to `hi` in steps of `step`. |
| 317 | `            if (cfg.ncpus == MAX_CPUS) {` | Tests whether the array `cfg.cpus` is full. It holds at most `MAX_CPUS` entries, which is 1024. |
| 318 | `                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);` | When the array is full: prints `bad cpu list: more than 1024 cpus` to stderr. |
| 319 | `                exit(2);` | When the array is full: the whole program ends with exit status 2. |
| 320 | `            }` | Ends the `if` of line 317. |
| 321 | `            cfg.cpus[cfg.ncpus++] = (int)c;` | Appends the CPU number to `cfg.cpus` and counts it in `cfg.ncpus`. For example the list `0-63,64-119` gives 120 entries in rising order: `cfg.cpus[i]` is `i`. `main` gives thread `i` the CPU `cfg.cpus[i % cfg.ncpus]` (line 1243). |
| 322 | `        }` | Ends the loop of line 316. |
| 323 | `    }` | Ends the loop of line 301. |
| 324 | `}` | Ends the function `parse_cpus`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 326 to 336)

| Line | Source | Explanation |
|---:|---|---|
| 326 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It limits the calling thread to the CPU with the number `cpu`. A worker of a run with `--cpus` calls it at its start (lines 983 to 984), before it opens its counters and before it maps its buffer. |
| 327 | `{` | Opens the body of `pin_cpu`. |
| 328 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 329 | `    CPU_ZERO(&set);` | Empties the set. |
| 330 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 331 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 332 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 333 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 334 | `    }` | Ends the `if` of line 331. |
| 335 | `}` | Ends the function `pin_cpu`. |

### Function `buf_len`: the length of one buffer (lines 337 to 341)

| Line | Source | Explanation |
|---:|---|---|
| 337 | `static size_t buf_len(void)` | Starts the function `buf_len`. It returns the length of one buffer in bytes. |
| 338 | `{` | Opens the body of `buf_len`. |
| 339 | `    return (cfg.bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | Returns the `--bytes` value rounded up to a multiple of 2 MiB (`HUGE_BYTES`). The expression adds `HUGE_BYTES - 1` and then clears the low 21 bits. A value of 268435456 bytes (256 MiB) is already 128 times 2 MiB and stays as it is. |
| 340 | `}` | Ends the function `buf_len`. |

### Function `alloc_buf`: map one buffer, aligned to 2 MiB (lines 342 to 363)

| Line | Source | Explanation |
|---:|---|---|
| 342 | `/* The buffer starts at a 2 MiB boundary, at least one page above the start` | Comment: the buffer starts at a 2 MiB boundary. That boundary lies at least one page above the start of the mapping. |
| 343 | ` * of the mapping. The unused parts before and after it are PROT_NONE, so the` | Comment: the unused parts of the mapping before and after the buffer get the access right `PROT_NONE`, which forbids every access. |
| 344 | ` * buffer is one entry of its own in /proc/self/smaps (handoff B.6). */` | Comment: so the buffer is one entry of its own in `/proc/self/smaps`, the Linux file that lists every memory mapping of the process. `read_smaps` (line 857) looks for an entry with exactly the start and the end of the buffer. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. |
| 345 | `static uint64_t *alloc_buf(void)` | Starts the function `alloc_buf`. It maps one buffer and returns its address. Each worker calls it once (line 987). A worker of a run with `--cpus` has pinned itself before this call (lines 983 to 984). A worker that needs the second buffer calls it once more (line 990). |
| 346 | `{` | Opens the body of `alloc_buf`. |
| 347 | `    size_t len = buf_len(), maplen = len + 2 * HUGE_BYTES;` | `len`: the buffer length from `buf_len`. `maplen`: 4 MiB more. The extra 4 MiB make room for the alignment of line 353 and for the two no-access ranges of lines 354 to 355. For a buffer of 256 MiB `len` is 268435456 bytes and `maplen` is 272629760 bytes (260 MiB). |
| 348 | `    uint8_t *raw = mmap(NULL, maplen, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `maplen` bytes of new memory that the process may read and write (`PROT_READ \| PROT_WRITE`). `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process only, and no file backs it. `NULL`: Linux chooses the address. `-1` and `0` are the two file arguments, which are not used here. The call does not yet give physical memory to the pages. That happens at the first touch (line 988). |
| 349 | `    if (raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 350 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 351 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 352 | `    }` | Ends the `if` of line 349. |
| 353 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + (size_t)page_bytes + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the buffer start. It is the first 2 MiB boundary that lies at least one page above the start `raw` of the mapping. The expression adds the page size `page_bytes` and `HUGE_BYTES - 1` to `raw` and then clears the low 21 bits. The buffer is the range from `p` to `p + len`. So it starts at an address that is a multiple of 2 MiB. |
| 354 | `    if (mprotect(raw, (size_t)(p - raw), PROT_NONE) != 0 \|\|` | `mprotect` with `PROT_NONE` forbids every access to the unused range before the buffer, from `raw` to `p`. |
| 355 | `        mprotect(p + len, (size_t)(raw + maplen - (p + len)), PROT_NONE) != 0)` | Continues the test of line 354: the same for the unused range after the buffer, from `p + len` to the end of the mapping. This second call runs only when the first one succeeded. |
| 356 | `        perror("mprotect of the guard ranges (continuing; page state will be NA)");` | When one of the two calls failed: `perror` prints a message which says that the run continues and that the page state will be `NA`. The program does not stop. The message goes to stderr, the error output of the program. |
| 357 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: the advice `MADV_NOHUGEPAGE` matters on a host whose setting for transparent huge pages is `always`. |
| 358 | `     * would still get 2 MiB pages. */` | Comment: without that advice a run with `--no-thp` would still get 2 MiB pages on such a host. |
| 359 | `    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` gives Linux advice about the buffer range. With `cfg.use_thp` set, the advice is `MADV_HUGEPAGE`: use 2 MiB pages for this range. With `--no-thp` it is `MADV_NOHUGEPAGE`: do not use them. The function does not test whether the buffer got 2 MiB pages. The P rows show how much of each buffer lies on 2 MiB pages (line 916). |
| 360 | `        perror("madvise (continuing)");` | When `madvise` failed: `perror` prints `madvise (continuing)` and the reason that Linux gave. The run continues. |
| 361 | `    return (uint64_t *)p;` | Returns the buffer start as a pointer to 8-byte words. No line of this file unmaps a buffer. So the buffer stays mapped until the process ends. |
| 362 | `}` | Ends the function `alloc_buf`. |

### Old read kernel: the macro `DEF_OLDREAD` and the kernels `oldread` and `oldread2` (lines 364 to 387)

| Line | Source | Explanation |
|---:|---|---|
| 364 | `/*` | Opens the comment about the old kernels. |
| 365 | ` * Old kernels: k_read, k_write and k_copy of bandwidth.orig.c (the benchmark` | Comment: the old kernels below are the functions `k_read`, `k_write` and `k_copy` of the file `bandwidth.orig.c`. |
| 366 | ` * until 2026-11-13), renamed. The old comment of k_read was: "16 independent` | Comment: `bandwidth.orig.c` was the benchmark source until 2026-11-13. Here its three kernels have the new names `k_oldread`, `k_oldwrite` and `k_oldcopy`. `bw_old` is the benchmark binary of 2026-11-13 that was built from that file. Apart from absolute addresses, the machine code of `k_oldread` in the CRB build of `bwx` has the same instruction text as `k_read` of `bw_old` [Ref1] [Ref3]. A quotation of the old comment of `k_read` starts in this line. |
| 367 | ` * accumulators keep the loop load-bound: on 128-bit NEON gcc folds them into` | Comment, quotation: 16 separate running sums (accumulators) keep the loop load-bound. This means that the loads and not the adds should limit the speed of the loop. This is a statement of the old comment. It is not a measured result. |
| 368 | ` * 8 vector chains, enough to hide a 2-cycle add latency; on AVX-512 they` | Comment, quotation: with the 128-bit NEON registers gcc puts the 16 sums into 8 vector registers. Each register is a chain of adds of its own. The old comment says that 8 chains are enough for an add that takes 2 clock cycles: the adds then do not limit the speed of the loop. The listing of the CRB binary of `bwx` confirms the 8 registers: the sums are in the registers `v24` to `v31` [Ref1]. |
| 369 | ` * become 2 zmm chains." oldread2 is the A/A copy: the same source under a` | Comment: the end of the quotation: with AVX-512, a vector instruction set of x86 processors, the sums become 2 chains in 512-bit registers. The next sentence: `oldread2` is the A/A copy, the same source under a second name. |
| 370 | ` * second name (the build uses -fno-ipa-icf, so gcc keeps both).` | Comment: the build uses the gcc flag `-fno-ipa-icf`. With it gcc keeps both functions. The flag is in the build record of CRB for `bwx` [Ref2]. |
| 371 | ` */` | Ends the comment. |
| 372 | `#define DEF_OLDREAD(name) \` | Starts the macro `DEF_OLDREAD(name)`. It writes `PLACE(name)` and one function: the source text of the old read kernel. The backslash at the end of each line continues the macro on the next line. |
| 373 | `    PLACE(name); \` | `PLACE` (line 74) adds the pad of this kernel. So the function starts at the value of `PAD_` plus `name`, modulo 64. |
| 374 | `    __attribute__((noinline)) static uint64_t k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the macro argument into the function name. `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns a 64-bit sum. `noinline`: gcc must keep the function separate from its caller. The listing of the CRB build of `bwx` shows `k_oldread` as a function of its own [Ref1]. With `--stop common` one call in a timed interval gets one chunk of 2 MiB: `n` is then 262144 words (line 1037). The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1011). |
| 375 | `    { \` | Opens the body of the kernel function. |
| 376 | `        uint64_t s[16] = { 0 }; \` | `s`: the 16 running sums. All start at 0. Machine code of `k_oldread` in `bwx`, once per call and before the loop: 4 `stp` instructions write 128 B of zeros to the stack (each stores two 16-byte registers), and the 8 registers `v24` to `v31` are set to 0. During the loop these 8 registers hold the 16 sums, two sums per register [Ref1]. |
| 377 | `        for (size_t i = 0; i < n; i += 16) \` | The outer loop. One pass takes 16 words, which are 128 B. Machine code of `k_oldread` in `bwx`: gcc did not unroll this loop. One pass of the machine loop is one pass of this source loop. Before the loop the code computes the number of passes into the register `x2` [Ref1]. |
| 378 | `            for (int j = 0; j < 16; j++) \` | The inner loop over the 16 words of the block. Machine code of `k_oldread` in `bwx`: gcc compiled this loop to vector instructions. No loop over `j` is left [Ref1]. |
| 379 | `                s[j] += a[i + j]; \` | Adds word `j` of the block to sum `j`. So every loaded word is an input of one add. Machine code of `k_oldread` in `bwx`, one loop pass of 16 instructions for 128 B [Ref1]: 4 `ldp` loads of 32 B each, at the byte offsets 0, 32, 64 and 96 from the read position. 8 vector adds: each one adds one loaded register to one of the sum registers `v24` to `v31` and so performs two of the 16 adds of the source. `add x0, x0, #0x80` moves the read position by 128 B. `add x1, x1, #0x1` counts the pass. `cmp` and `b.cc` branch back while the count is below the number of passes. No instruction of the loop stores to memory. |
| 380 | `        uint64_t sum = 0; \` | `sum`: the total of the 16 sums. It starts at 0. |
| 381 | `        for (int j = 0; j < 16; j++) \` | A loop over the 16 sums. It runs once per call, after the read loop. |
| 382 | `            sum += s[j]; \` | Adds the 16 sums into one value. Machine code of `k_oldread` in `bwx`, once per call [Ref1]: the 8 sum registers are stored to the stack and loaded back. Then 7 vector adds and one `addp` add them into one number. `addp` adds the two 64-bit halves of one register. |
| 383 | `        return sum; \` | Returns the total. Machine code of `k_oldread` in `bwx`: `fmov x0, d31` copies the result into the return register `x0` [Ref1]. `call` stores the returned value into the volatile variable `sink` (line 842). So the sum is used, and the compiler cannot remove the loads and the adds as unused work. gcc also added a stack check to this function. It saves a guard value on the stack at the start and compares it before the return. A changed value leads to a call of `__stack_chk_fail` [Ref1]. |
| 384 | `    }` | Ends the kernel function and the macro. In `bwx` one call of `k_oldread` runs 53 instructions outside the loop [Ref1]. One chunk of 2 MiB is 16384 loop passes, which are 262144 instructions. |
| 385 | `DEF_OLDREAD(oldread)` | Creates the function `k_oldread`. It is the kernel `oldread` of `--seq`, the old read kernel, with the type `T_OLDREAD` in the kernel table (line 820). In the CRB binary of `bwx` the function starts at the address `0x3680` and its loop at `0x36e8`, which is 40 modulo 64 [Ref1]. For 256 B it runs 2 loop passes: 32 instructions with 8 `ldp` loads, 16 vector adds and 2 branches. The new read kernel runs 11 instructions for 256 B (line 438). Apart from absolute addresses, the machine code of `k_oldread` has the same instruction text as `k_read` of the binary `bw_old` [Ref3]. |
| 386 | `DEF_OLDREAD(oldread2)` | Creates `k_oldread2`, the A/A copy of the old read kernel. The listing of the CRB build of `bwx` shows the same instruction text for both functions [Ref1]. |

### Old write kernel `oldwrite` and old copy kernel `oldcopy` (lines 388 to 401)

| Line | Source | Explanation |
|---:|---|---|
| 388 | `PLACE(oldwrite);` | `PLACE` adds the pad of the kernel `oldwrite`. `PAD_oldwrite` is 32 (line 143). |
| 389 | `__attribute__((noinline)) static void k_oldwrite(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_oldwrite`, the kernel `oldwrite`: the write kernel of the old benchmark source. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. The first touch of a buffer uses `k_write` (line 442). |
| 390 | `{` | Opens the body of `k_oldwrite`. |
| 391 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 392 | `        a[i] = v;` | Stores `v` to word `i`: one store of 8 B per pass of the source loop. Machine code in the CRB binary of `bwx`: gcc compiled the loop to instructions of SVE, the scalable vector extension of Arm. One loop pass has 4 instructions with one `st1d` store, which writes one vector of 8-byte words. The program reads the number of words per vector at run time with the instruction `cntd`. The listing does not give this number [Ref1]. |
| 393 | `}` | Ends the function `k_oldwrite`. |
| 395 | `PLACE(oldcopy);` | `PLACE` adds the pad of the kernel `oldcopy`. `PAD_oldcopy` is 32 (line 146). |
| 396 | `__attribute__((noinline)) static void k_oldcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_oldcopy`, the kernel `oldcopy`: the copy kernel of the old benchmark source. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 397 | `{` | Opens the body of `k_oldcopy`. |
| 398 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 399 | `        d[i] = s[i];` | Loads word `i` of the source and stores it to word `i` of the destination. The loaded value is stored and has no other use. Machine code in the CRB binary of `bwx`: SVE instructions, as in `k_oldwrite`. One loop pass has 5 instructions with one `ld1d` load and one `st1d` store of one vector of 8-byte words [Ref1]. |
| 400 | `}` | Ends the function `k_oldcopy`. |

### AArch64 branch and the function `k_read`: the new read kernel (lines 402 to 440)

| Line | Source | Explanation |
|---:|---|---|
| 402 | `#if defined(__aarch64__)` | The lines from here to the `#else` of line 762 are compiled only for AArch64. The lines from that `#else` to the `#endif` of line 808 hold the stand-ins for other machines. The CRB build of `bwx` is an AArch64 build: its listing holds AArch64 instructions such as the `ldp` of `k_read` [Ref1]. So it was compiled from this first branch. |
| 403 | `#define STANDIN 0` | `STANDIN` is 0 in the AArch64 branch: the kernels are the real ones. The program then prints `kernels=aarch64` in its header (line 1256). |
| 404 | `/*` | Opens the comment about the C kernels. |
| 405 | ` * C kernels: unchanged from bench/bandwidth.c. Each iteration moves 256 B as` | Comment: the C kernels below are unchanged from the benchmark source `bandwidth.c` in the folder `bench`. One loop pass moves 256 B. |
| 406 | ` * 16 vectors of 16 B and does no arithmetic on the data. Callers guarantee` | Comment: the 256 B move as 16 vectors of 16 B. The loop does no arithmetic on the data. |
| 407 | ` * n * 8 is a multiple of 256 and non-zero. The empty asm statement of k_read` | Comment: the callers guarantee that the size `n * 8` in bytes is a multiple of 256 and is not 0. `main` checks the sizes (line 1205 and line 1223). A chunk of 2 MiB is a multiple of 256. The sentence about the empty `asm` statement starts here. |
| 408 | ` * and k_copy takes the 16 loaded vectors as inputs in NEON registers ("w"):` | Comment: the empty `asm` statement of `k_read` (lines 433 to 436) and of `k_copy` (lines 491 to 494) takes the 16 loaded vectors as inputs. The letter `w` says that each input must be in a NEON register. |
| 409 | ` * see the comment in bench/bandwidth.c.` | Comment: a comment in the file `bandwidth.c` of the folder `bench` explains this statement. |
| 410 | ` */` | Ends the comment. |
| 411 | `PLACE(read);` | `PLACE(read)` with `PAD_read` = 32 (line 119): the function starts at 32 modulo 64. In the CRB binary of `bwx` the function `k_read` starts at the address `0x3a20` and its loop at `0x3a24`, which is 36 modulo 64 [Ref1]. The loop of `k_read` in `bw_new` has the same offset 36 [Ref3]. |
| 412 | `__attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)` | Starts the function `k_read`: the kernel `read` of `--seq`, the new read kernel, with the type `T_READ` in the kernel table (line 818). `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns nothing: it computes no sum. `noinline`: gcc must keep the function separate from its caller. The listing of `bwx` shows it as a function of 13 instructions [Ref1]. Apart from absolute addresses, its instruction text equals the text of `k_read` in `bw_new`, the benchmark binary of 2026-11-13 with the new kernels [Ref3]. |
| 413 | `{` | Opens the body of `k_read`. With `--stop common` one call of the function in a timed interval gets one chunk of 2 MiB: `n` is then 262144 words (line 1037). The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1011). |
| 414 | `    const uint64_t *p = a;` | `p`: the read position. It starts at `a`. |
| 415 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx`, once per call and before the loop: `add x1, x0, x1, lsl #3`. Before this instruction the register `x0` holds `a` and `x1` holds `n`. After it `x1` holds `end` [Ref1]. |
| 416 | `    do {` | Starts the loop. With `do` the loop body runs once before the first test of the end. So the range must not be empty. |
| 417 | `        uint64x2_t v0 = vld1q_u64(p + 0);` | `vld1q_u64(p + 0)` loads 16 B, which are two 8-byte words, from the read position into the vector `v0`. These are the bytes 0 to 15 of the current block of 256 B. |
| 418 | `        uint64x2_t v1 = vld1q_u64(p + 2);` | Loads the bytes 16 to 31 of the block, 2 words after the read position, into `v1`. Machine code of `bwx`: gcc joined this load and the load of line 417 into one instruction, `ldp q31, q30, [x0]`, which loads 32 B [Ref1]. |
| 419 | `        uint64x2_t v2 = vld1q_u64(p + 4);` | Loads the bytes 32 to 47 of the block into `v2`. |
| 420 | `        uint64x2_t v3 = vld1q_u64(p + 6);` | Loads the bytes 48 to 63 of the block into `v3`. Machine code of `bwx` for this load and the load of line 419: `ldp q29, q28, [x0, #32]` [Ref1]. |
| 421 | `        uint64x2_t v4 = vld1q_u64(p + 8);` | Loads the bytes 64 to 79 of the block into `v4`. |
| 422 | `        uint64x2_t v5 = vld1q_u64(p + 10);` | Loads the bytes 80 to 95 of the block into `v5`. Machine code of `bwx` for this load and the load of line 421: `ldp q27, q26, [x0, #64]` [Ref1]. |
| 423 | `        uint64x2_t v6 = vld1q_u64(p + 12);` | Loads the bytes 96 to 111 of the block into `v6`. |
| 424 | `        uint64x2_t v7 = vld1q_u64(p + 14);` | Loads the bytes 112 to 127 of the block into `v7`. Machine code of `bwx` for this load and the load of line 423: `ldp q25, q24, [x0, #96]` [Ref1]. |
| 425 | `        uint64x2_t v8 = vld1q_u64(p + 16);` | Loads the bytes 128 to 143 of the block into `v8`. |
| 426 | `        uint64x2_t v9 = vld1q_u64(p + 18);` | Loads the bytes 144 to 159 of the block into `v9`. Machine code of `bwx` for this load and the load of line 425: `ldp q23, q22, [x0, #128]` [Ref1]. |
| 427 | `        uint64x2_t v10 = vld1q_u64(p + 20);` | Loads the bytes 160 to 175 of the block into `v10`. |
| 428 | `        uint64x2_t v11 = vld1q_u64(p + 22);` | Loads the bytes 176 to 191 of the block into `v11`. Machine code of `bwx` for this load and the load of line 427: `ldp q21, q20, [x0, #160]` [Ref1]. |
| 429 | `        uint64x2_t v12 = vld1q_u64(p + 24);` | Loads the bytes 192 to 207 of the block into `v12`. |
| 430 | `        uint64x2_t v13 = vld1q_u64(p + 26);` | Loads the bytes 208 to 223 of the block into `v13`. Machine code of `bwx` for this load and the load of line 429: `ldp q19, q18, [x0, #192]` [Ref1]. |
| 431 | `        uint64x2_t v14 = vld1q_u64(p + 28);` | Loads the bytes 224 to 239 of the block into `v14`. |
| 432 | `        uint64x2_t v15 = vld1q_u64(p + 30);` | Loads the bytes 240 to 255 of the block into `v15`. Machine code of `bwx` for this load and the load of line 431: `ldp q17, q16, [x0, #224]`. One loop pass has 16 loads in the source and 8 `ldp` loads in the machine code. It reads 256 B, each byte once, in rising address order [Ref1]. |
| 433 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text. It adds no instruction to the loop. It names the loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. A comment in the benchmark source `bandwidth.c` gives the purpose: gcc must have all 16 values in registers at this point, and this keeps gcc from deleting the loads. After this statement nothing uses the values. They are dropped. The listing of `bwx` shows no add and no other instruction that uses a loaded register [Ref1]. This is the difference to the old read kernel, which adds every loaded word to a sum. |
| 434 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 433: the inputs `v4` to `v7`. |
| 435 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 433: the inputs `v8` to `v11`. |
| 436 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 433: the inputs `v12` to `v15`. The statement ends here. |
| 437 | `        p += 32;` | Moves the read position forward by 32 words, which are 256 B. Machine code of `bwx`: `add x0, x0, #0x100` [Ref1]. |
| 438 | `    } while (p < end);` | Repeats the loop while the read position is below the end. Machine code of `bwx`: `cmp x1, x0`, then `b.hi` back to the first `ldp`. One loop pass is 11 instructions for 256 B: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1]. One chunk of 2 MiB is 8192 loop passes, which are 90112 instructions. |
| 439 | `}` | Ends the function `k_read`. Machine code of `bwx`: one `ret` instruction. gcc used the registers `q16` to `q31` for the loads, and the function saves and restores no register [Ref1]. The AArch64 branch of line 402 continues after this function, up to line 762. |

### Function `k_write`: the NEON write kernel, used for the first touch (lines 441 to 467)

| Line | Source | Explanation |
|---:|---|---|
| 441 | `PLACE(write);` | `PLACE(write)` adds the pad of this kernel. `PAD_write` is 0 (line 122). So the function starts at a multiple of 64 bytes: the address `0x3a80` in the listing of the CRB build of `bwx`. The function stands in the AArch64 branch of line 402, and the CRB binary holds this branch: the listing shows the `dup` and `stp` instructions of this function [Ref1]. |
| 442 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_write`, the NEON write kernel. It stores the value `v` to `n` 8-byte words, from the address `a` on. Each worker calls it once per buffer, directly after the allocation (line 988). This call is the first touch. It happens before the first interval, and it is not timed. The call writes the first `cfg.bytes` bytes of the buffer, the range of `--bytes`. The buffer is this value rounded up to a multiple of 2 MiB (line 339). So the call writes the whole buffer only when `--bytes` is a multiple of 2 MiB. The kernel table also offers this function as the kernel `write` (line 818). |
| 443 | `{` | Opens the body of `k_write`. |
| 444 | `    uint64_t *p = a;` | `p`: the write position. It starts at `a`. |
| 445 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx`, before the loop: `add x1, x0, x1, lsl #3` [Ref1]. |
| 446 | `    uint64x2_t q = vdupq_n_u64(v);` | `vdupq_n_u64(v)` builds one 16-byte vector `q` that holds `v` twice. Machine code of `bwx`, before the loop: `dup v31.2d, x2`. The register `x2` holds `v`. `dup` copies one 8-byte value into both halves of a 16-byte vector register [Ref1]. |
| 447 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 448 | `        vst1q_u64(p + 0, q);` | `vst1q_u64(p + 0, q)` stores the 16 bytes of `q` at the write position. These are the bytes 0 to 15 of the current block of 256 B. |
| 449 | `        vst1q_u64(p + 2, q);` | Stores `q` to the bytes 16 to 31 of the block. Machine code of `bwx`: gcc joined this store and the store of line 448 into one instruction `stp q31, q31`. `stp` stores two 16-byte registers, which is 32 B. Here both are the register `q31` [Ref1]. |
| 450 | `        vst1q_u64(p + 4, q);` | Stores `q` to the bytes 32 to 47 of the block. |
| 451 | `        vst1q_u64(p + 6, q);` | Stores `q` to the bytes 48 to 63 of the block. |
| 452 | `        vst1q_u64(p + 8, q);` | Stores `q` to the bytes 64 to 79 of the block. |
| 453 | `        vst1q_u64(p + 10, q);` | Stores `q` to the bytes 80 to 95 of the block. |
| 454 | `        vst1q_u64(p + 12, q);` | Stores `q` to the bytes 96 to 111 of the block. |
| 455 | `        vst1q_u64(p + 14, q);` | Stores `q` to the bytes 112 to 127 of the block. |
| 456 | `        vst1q_u64(p + 16, q);` | Stores `q` to the bytes 128 to 143 of the block. |
| 457 | `        vst1q_u64(p + 18, q);` | Stores `q` to the bytes 144 to 159 of the block. |
| 458 | `        vst1q_u64(p + 20, q);` | Stores `q` to the bytes 160 to 175 of the block. |
| 459 | `        vst1q_u64(p + 22, q);` | Stores `q` to the bytes 176 to 191 of the block. |
| 460 | `        vst1q_u64(p + 24, q);` | Stores `q` to the bytes 192 to 207 of the block. |
| 461 | `        vst1q_u64(p + 26, q);` | Stores `q` to the bytes 208 to 223 of the block. |
| 462 | `        vst1q_u64(p + 28, q);` | Stores `q` to the bytes 224 to 239 of the block. |
| 463 | `        vst1q_u64(p + 30, q);` | Stores `q` to the bytes 240 to 255 of the block. The 16 stores of one loop pass fill 256 B. Each byte is written once. The machine loop of `bwx` has 8 `stp` instructions [Ref1]. |
| 464 | `        p += 32;` | Moves the write position forward by 32 words, which are 256 B. Machine code of `bwx`: `add x0, x0, #0x100`. gcc put this `add` at the start of the loop pass. So the 8 `stp` instructions use the offsets -256 to -32 [Ref1]. |
| 465 | `    } while (p < end);` | Repeats the loop while the write position is below `end`. Machine code of `bwx`: `cmp x1, x0` and the branch `b.hi`. One loop pass is 11 instructions for 256 B: 1 `add`, 8 `stp`, 1 `cmp` and 1 branch [Ref1]. With `--bytes 256M` the first touch writes 268435456 bytes in 1048576 loop passes. The binary `bw_new` holds the same instruction text for its `k_write` [Ref3]. |
| 466 | `}` | Ends the function `k_write`. |

### Function `k_copy`: the NEON copy kernel (lines 468 to 515)

| Line | Source | Explanation |
|---:|---|---|
| 468 | `PLACE(copy);` | `PLACE(copy)` adds the pad `PAD_copy`, which is 32 bytes with the default values (line 101). |
| 469 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_copy`, the kernel `copy`: the NEON copy kernel. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 470 | `{` | Opens the body of `k_copy`. |
| 471 | `    uint64_t *dp = d;` | `dp`: the write position in the destination. It starts at `d`. |
| 472 | `    const uint64_t *sp = s;` | `sp`: the read position in the source. It starts at `s`. |
| 473 | `    const uint64_t *end = s + n;` | `end`: the first address after the source range: `s` plus `n` words. |
| 474 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 475 | `        uint64x2_t v0 = vld1q_u64(sp + 0);` | `vld1q_u64(sp + 0)` loads 16 B from the read position into the vector `v0`. These are the bytes 0 to 15 of the current source block of 256 B. |
| 476 | `        uint64x2_t v1 = vld1q_u64(sp + 2);` | Loads the bytes 16 to 31 of the source block into `v1`. |
| 477 | `        uint64x2_t v2 = vld1q_u64(sp + 4);` | Loads the bytes 32 to 47 of the source block into `v2`. |
| 478 | `        uint64x2_t v3 = vld1q_u64(sp + 6);` | Loads the bytes 48 to 63 of the source block into `v3`. |
| 479 | `        uint64x2_t v4 = vld1q_u64(sp + 8);` | Loads the bytes 64 to 79 of the source block into `v4`. |
| 480 | `        uint64x2_t v5 = vld1q_u64(sp + 10);` | Loads the bytes 80 to 95 of the source block into `v5`. |
| 481 | `        uint64x2_t v6 = vld1q_u64(sp + 12);` | Loads the bytes 96 to 111 of the source block into `v6`. |
| 482 | `        uint64x2_t v7 = vld1q_u64(sp + 14);` | Loads the bytes 112 to 127 of the source block into `v7`. |
| 483 | `        uint64x2_t v8 = vld1q_u64(sp + 16);` | Loads the bytes 128 to 143 of the source block into `v8`. |
| 484 | `        uint64x2_t v9 = vld1q_u64(sp + 18);` | Loads the bytes 144 to 159 of the source block into `v9`. |
| 485 | `        uint64x2_t v10 = vld1q_u64(sp + 20);` | Loads the bytes 160 to 175 of the source block into `v10`. |
| 486 | `        uint64x2_t v11 = vld1q_u64(sp + 22);` | Loads the bytes 176 to 191 of the source block into `v11`. |
| 487 | `        uint64x2_t v12 = vld1q_u64(sp + 24);` | Loads the bytes 192 to 207 of the source block into `v12`. |
| 488 | `        uint64x2_t v13 = vld1q_u64(sp + 26);` | Loads the bytes 208 to 223 of the source block into `v13`. |
| 489 | `        uint64x2_t v14 = vld1q_u64(sp + 28);` | Loads the bytes 224 to 239 of the source block into `v14`. |
| 490 | `        uint64x2_t v15 = vld1q_u64(sp + 30);` | Loads the bytes 240 to 255 of the source block into `v15`. One loop pass loads 256 B with 16 NEON loads of 16 B. |
| 491 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text, as in `k_read` (line 433). It adds no instruction. It names the 16 loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. So gcc must have all 16 loaded values in registers at this point. A comment in the benchmark source `bandwidth.c` of the folder `bench` reports the effect on the copy loop with gcc 14.2.0: with the statement the 8 `ldp` stand ahead of the 8 `stp`, and without it loads and stores alternate. |
| 492 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 491: the inputs `v4` to `v7`. |
| 493 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 491: the inputs `v8` to `v11`. |
| 494 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 491: the inputs `v12` to `v15`. The statement ends here. |
| 495 | `        vst1q_u64(dp + 0, v0);` | `vst1q_u64(dp + 0, v0)` stores the vector `v0` to the bytes 0 to 15 of the current destination block. So each loaded value is stored once and has no other use. |
| 496 | `        vst1q_u64(dp + 2, v1);` | Stores `v1` to the bytes 16 to 31 of the destination block. |
| 497 | `        vst1q_u64(dp + 4, v2);` | Stores `v2` to the bytes 32 to 47 of the destination block. |
| 498 | `        vst1q_u64(dp + 6, v3);` | Stores `v3` to the bytes 48 to 63 of the destination block. |
| 499 | `        vst1q_u64(dp + 8, v4);` | Stores `v4` to the bytes 64 to 79 of the destination block. |
| 500 | `        vst1q_u64(dp + 10, v5);` | Stores `v5` to the bytes 80 to 95 of the destination block. |
| 501 | `        vst1q_u64(dp + 12, v6);` | Stores `v6` to the bytes 96 to 111 of the destination block. |
| 502 | `        vst1q_u64(dp + 14, v7);` | Stores `v7` to the bytes 112 to 127 of the destination block. |
| 503 | `        vst1q_u64(dp + 16, v8);` | Stores `v8` to the bytes 128 to 143 of the destination block. |
| 504 | `        vst1q_u64(dp + 18, v9);` | Stores `v9` to the bytes 144 to 159 of the destination block. |
| 505 | `        vst1q_u64(dp + 20, v10);` | Stores `v10` to the bytes 160 to 175 of the destination block. |
| 506 | `        vst1q_u64(dp + 22, v11);` | Stores `v11` to the bytes 176 to 191 of the destination block. |
| 507 | `        vst1q_u64(dp + 24, v12);` | Stores `v12` to the bytes 192 to 207 of the destination block. |
| 508 | `        vst1q_u64(dp + 26, v13);` | Stores `v13` to the bytes 208 to 223 of the destination block. |
| 509 | `        vst1q_u64(dp + 28, v14);` | Stores `v14` to the bytes 224 to 239 of the destination block. |
| 510 | `        vst1q_u64(dp + 30, v15);` | Stores `v15` to the bytes 240 to 255 of the destination block. One loop pass stores 256 B with 16 NEON stores of 16 B. |
| 511 | `        sp += 32;` | Moves the read position forward by 32 words, which are 256 B. |
| 512 | `        dp += 32;` | Moves the write position forward by 32 words, which are 256 B. |
| 513 | `    } while (sp < end);` | Repeats the loop while the read position is below `end`. Machine code of `bwx`, one loop pass: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.hi`. That is 20 instructions for 256 B loaded and 256 B stored. gcc joined each two neighbour loads into one `ldp` and each two neighbour stores into one `stp` [Ref1]. |
| 514 | `}` | Ends the function `k_copy`. |

### Macro `DEF_ASMREAD`: the hand-written read loop and its six kernels (lines 516 to 559)

| Line | Source | Explanation |
|---:|---|---|
| 516 | `/*` | Opens the comment about the assembly kernels. |
| 517 | ` * asm kernels: the asm text of bench/bandwidth.c, inside macros so that an` | Comment: the kernels below hold the assembly text of the benchmark source `bandwidth.c` in the folder `bench`. From here to line 760 the loop of each kernel is assembly text inside an `__asm__` statement. gcc copies this text into the function. The text of three loops stands inside macros. |
| 518 | ` * A/A copy is the same source under a second name. Each iteration moves` | Comment: the reason for the macros: one more line then defines the same loop under a second name, an A/A copy. |
| 519 | ` * 256 B with 8 ldp/stp of q registers (16 B each). Callers guarantee n * 8` | Comment: one loop pass moves 256 B with 8 `ldp` or `stp` instructions. Each of them moves two `q` registers of 16 B. The read loop has 8 `ldp`. The write loop has 8 `stp`. The copy loop has 8 `ldp` and 8 `stp`. |
| 520 | ` * is a multiple of 256 and non-zero. v8-v15 are callee-saved in AAPCS64:` | Comment: the callers guarantee that the size in bytes is a multiple of 256 and is not 0. The loop tests the end only after a loop pass. `main` ends the program with status 2 when `--bytes` is 0 or is not a multiple of 256 (line 1205), and when the size of a `--seq` entry is not a multiple of 256 (line 1223). The next sentence: AAPCS64, the calling rules of Arm, say that a function must keep `v8` to `v15` for its caller. |
| 521 | ` * naming them as clobbers makes gcc save d8-d15 once per call, which is` | Comment: the `asm` statement names these registers as changed (clobbers). So gcc saves `d8` to `d15`, the low 8 bytes of these registers, once per call. |
| 522 | ` * outside the loop.` | Comment: this save is outside the loop. |
| 523 | ` *` | Comment: an empty line of the comment. |
| 524 | ` * DEF_ASMREAD(name, nops) puts "nops" nop instructions after the 8 ldp and` | Comment: the macro `DEF_ASMREAD(name, nops)` puts `nops` instructions of the kind `nop` after the 8 `ldp`. |
| 525 | ` * before the add (step B5). asmread and asmread2 have 0 of them.` | Comment: the `nop` instructions stand before the `add`. The comment links them to step B5 of the file `handoff.md`, the specification of the first runner. `asmread` and `asmread2` have 0 `nop`. |
| 526 | ` */` | Ends the comment. |
| 527 | `#define DEF_ASMREAD(name, nops) \` | Starts the macro `DEF_ASMREAD(name, nops)`. It defines one kernel function with a hand-written read loop. The backslash at the end of each line continues the macro on the next line. The kernel `asmread` (line 553) and every `read_nop` kernel come from this macro. |
| 528 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 74). For `asmread` and for every `read_nop` kernel the pad is 0 bytes. So each of these functions starts at a multiple of 64 bytes. |
| 529 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the first macro argument: `DEF_ASMREAD(asmread, 0)` defines the function `k_asmread`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. `noinline` forbids gcc to merge the function into its caller. So the listing of the CRB build of `bwx` shows each kernel as a function of its own [Ref1]. |
| 530 | `    { \` | Opens the body of the kernel function. |
| 531 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 532 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx`: `add x1, x0, x1, lsl #3`, which adds 8 times `x1` to `x0` and puts the result into `x1`. It runs once per call, before the loop [Ref1]. |
| 533 | `        __asm__ volatile( \` | Starts a gcc statement that holds assembly text. gcc copies the text into the function. `volatile` tells gcc to keep the statement, although no later code uses `p`. The listing of `bwx` shows the instructions in the order of the text [Ref1]. |
| 534 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. `\n\t` ends one line of the assembly text and indents the next one. In the CRB binary of `bwx` the loop of `k_asmread` and the loop of every `read_nop` kernel start at an address of 20 modulo 64 [Ref1]. |
| 535 | `            "ldp q0, q1, [%[p]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 15 of the current block of 256 B into `q0` and the bytes 16 to 31 into `q1`. `%[p]` stands for the register that gcc chose for `p`. In the listing of `bwx` it is `x0` [Ref1]. |
| 536 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 537 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 538 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. With this instruction the bytes 0 to 127 of the block are loaded. |
| 539 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 540 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 541 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 542 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once, in rising address order. Nothing uses the loaded values: no instruction of the loop takes `q0` to `q15` as an input, and the next loop pass overwrites the registers. The old read kernel `k_oldread` (line 385) differs in this point: its source adds every loaded word to a sum (line 379). The unrolling is part of this text: 8 `ldp` per loop pass. gcc does not change the instructions of assembly text. It only puts register names in the places of `%[p]` and `%[end]`. |
| 543 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the second macro argument into text. For `read_nop4` the assembler sees the three lines `.rept 4`, `nop` and `.endr`. `.rept N` and `.endr` are assembler directives: the assembler repeats the lines between them N times. With `.rept 0` it writes nothing. So the loop of `asmread` has 0 `nop` between the last `ldp` and the `add`, and the loop of `read_nop4` has 4. A `nop` does nothing and loads nothing. So every loop pass still reads 256 B, and only the instruction count of the loop pass grows. |
| 544 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the read pointer forward by 256 B. Machine code of `bwx`: `add x0, x0, #0x100` [Ref1]. |
| 545 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the read pointer with `end` and sets the condition flags. Machine code of `bwx`: `cmp x0, x1` [Ref1]. |
| 546 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. `lo` means lower in an unsigned compare. The end test stands after the loop body. So the body runs at least once in every call. Instructions of one loop pass: 8 `ldp`, the `nop` instructions and these 3. That is 11 per 256 B in `asmread`, which has no `nop`. The listing of `bwx` prints `b.cc` for this branch and names `b.lo` as another name of it [Ref1]. |
| 547 | `            : [p] "+r"(p) \` | Tells gcc which C variables the text uses. `[p] "+r"(p)`: `p` is in a general register, and the text reads it and changes it. |
| 548 | `            : [end] "r"(end) \` | `[end] "r"(end)`: `end` is an input in a general register. In the listing of `bwx` it is `x1` [Ref1]. |
| 549 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list. It tells gcc what the text changes besides `p`. This line names the vector registers `v0` to `v7`. |
| 550 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` on the stack before the loop and loads them back after it. In the listing of `bwx` these are 4 `stp` instructions before the loop and 4 `ldp` instructions after it [Ref1]. This save runs once per call of the kernel, not once per loop pass. With `--stop common` one call in a timed interval covers one chunk of 2 MiB (line 1037). That is 8192 loop passes. |
| 551 | `              "memory", "cc"); \` | Ends the clobber list and the statement. `"memory"` says that the text accesses memory that no operand names. `"cc"` says that the text changes the condition flags. |
| 552 | `    }` | Ends the kernel function and the macro. In `bwx` the function `k_asmread` has 21 instructions: 5 before the loop, 11 in the loop and 5 after it, with `ret` as the last one [Ref1]. |
| 553 | `DEF_ASMREAD(asmread, 0)` | Defines `k_asmread`, the kernel `asmread`: the macro loop with 0 `nop`. One loop pass has 8 `ldp` loads of 32 B, `add`, `cmp` and the branch: 11 instructions per 256 B. In the CRB build of `bwx` its instruction text equals the text of `k_asmread` in the benchmark binary `bw_new` [Ref1] [Ref3]. `k_read` (line 412), the new read kernel, has the same 8 `ldp` loads and the same 11 instructions per 256 B. The listing shows four differences [Ref1]. Registers: `q0` to `q15` here, `q31` to `q16` in `k_read`. Save of `d8` to `d15`, outside the loop: only here. Loop start: 20 modulo 64 here, 36 in `k_read`. End test: `cmp x0, x1` with `b.cc` here, `cmp x1, x0` with `b.hi` in `k_read`. |
| 554 | `DEF_ASMREAD(asmread2, 0)` | Defines `k_asmread2`, the A/A copy of `asmread`. The listing of the CRB build of `bwx` shows the same instruction text for both [Ref1]. |
| 555 | `DEF_ASMREAD(read_nop4, 4)` | Defines `k_read_nop4`: the `asmread` loop with 4 `nop` per loop pass. That is 15 instructions per 256 B: 8 `ldp`, 4 `nop`, `add`, `cmp` and the branch. |
| 556 | `DEF_ASMREAD(read_nop8, 8)` | Defines `k_read_nop8`: the `asmread` loop with 8 `nop` per loop pass. That is 19 instructions per 256 B. |
| 557 | `DEF_ASMREAD(read_nop16, 16)` | Defines `k_read_nop16`: the `asmread` loop with 16 `nop` per loop pass. That is 27 instructions per 256 B. |
| 558 | `DEF_ASMREAD(read_nop32, 32)` | Defines `k_read_nop32`: the `asmread` loop with 32 `nop` per loop pass. That is 43 instructions per 256 B. |

### Function `k_read_sparse`: 128 B per loop pass, 4 loads and 9 `nop` (lines 560 to 581)

| Line | Source | Explanation |
|---:|---|---|
| 560 | `/* Step B5. Per 128 B: 4 ldp, 9 nop, add, cmp, b.lo. That is 16 instructions` | Comment: the kernel below belongs to step B5 of the file `handoff.md`, the specification of the first runner. Per 128 B it has 4 `ldp`, 9 `nop`, `add`, `cmp` and `b.lo`. That is 16 instructions. |
| 561 | ` * per 128 B, as the old read loop has, and no vector add. */` | Comment: the old read loop also has 16 instructions per 128 B. This kernel has the same instruction count, and it has no vector add. |
| 562 | `PLACE(read_sparse);` | `PLACE` adds the pad of the kernel `read_sparse`. It is the pad of `asmread`, 0 bytes (line 161). |
| 563 | `__attribute__((noinline)) static void k_read_sparse(const uint64_t *a, size_t n)` | Starts the function `k_read_sparse`, the kernel `read_sparse`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 564 | `{` | Opens the body of `k_read_sparse`. |
| 565 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 566 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. |
| 567 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text of the loop. |
| 568 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx` the loop starts 4 bytes after the function start, at an address of 4 modulo 64 [Ref1]. |
| 569 | `        "ldp q0, q1, [%[p]]\n\t"` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current block of 128 B into `q0` and `q1`. |
| 570 | `        "ldp q2, q3, [%[p], #32]\n\t"` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 571 | `        "ldp q4, q5, [%[p], #64]\n\t"` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 572 | `        "ldp q6, q7, [%[p], #96]\n\t"` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. One loop pass has 4 load instructions. It reads 128 B, each byte once. Nothing uses the loaded values. |
| 573 | `        ".rept 9\n\tnop\n\t.endr\n\t"` | The assembler writes the instruction `nop` 9 times here. A `nop` does nothing. |
| 574 | `        "add %[p], %[p], #128\n\t"` | Moves the read pointer forward by 128 B. |
| 575 | `        "cmp %[p], %[end]\n\t"` | Compares the read pointer with `end`. |
| 576 | `        "b.lo 1b\n\t"` | Branches back to the label `1` while the pointer is below `end`. One loop pass is 16 instructions per 128 B: 4 `ldp`, 9 `nop`, `add`, `cmp` and the branch. |
| 577 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 578 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 579 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc");` | The clobber list: the vector registers `v0` to `v7`, memory and the condition flags. It names none of `v8` to `v15`. So gcc saves no register in this function. The listing of `bwx` shows one `add` before the loop and one `ret` after it [Ref1]. |
| 580 | `}` | Ends the function `k_read_sparse`. |

### Macro `DEF_ASMWRITE`: the hand-written write loop, kernels `asmwrite` and `asmwrite2` (lines 582 to 608)

| Line | Source | Explanation |
|---:|---|---|
| 582 | `#define DEF_ASMWRITE(name) \` | Starts the macro `DEF_ASMWRITE(name)`. It defines one kernel function with a hand-written write loop. The backslash at the end of each line continues the macro on the next line. |
| 583 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 74). |
| 584 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. |
| 585 | `    { \` | Opens the body of the kernel function. |
| 586 | `        uint64_t *p = a; \` | `p`: the write pointer. It starts at `a`. |
| 587 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 588 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. gcc copies the text into the function. |
| 589 | `            "dup v0.2d, %[v]\n\t" \` | `dup` copies the 8-byte value `v` into both halves of the 16-byte vector register `v0`. It stands before the loop label, so it runs once per call. `%[v]` stands for the register that gcc chose for `v`. |
| 590 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx` the loop of `k_asmwrite` starts at an address of 40 modulo 64 [Ref1]. |
| 591 | `            "stp q0, q0, [%[p]]\n\t" \` | `stp` stores two 16-byte vector registers to memory, which is 32 B. Here both are `q0`. This instruction writes the bytes 0 to 31 of the current block of 256 B. `%[p]` stands for the register of the write pointer `p`. |
| 592 | `            "stp q0, q0, [%[p], #32]\n\t" \` | Stores `q0` twice to the bytes 32 to 63 of the block. |
| 593 | `            "stp q0, q0, [%[p], #64]\n\t" \` | Stores `q0` twice to the bytes 64 to 95 of the block. |
| 594 | `            "stp q0, q0, [%[p], #96]\n\t" \` | Stores `q0` twice to the bytes 96 to 127 of the block. |
| 595 | `            "stp q0, q0, [%[p], #128]\n\t" \` | Stores `q0` twice to the bytes 128 to 159 of the block. |
| 596 | `            "stp q0, q0, [%[p], #160]\n\t" \` | Stores `q0` twice to the bytes 160 to 191 of the block. |
| 597 | `            "stp q0, q0, [%[p], #192]\n\t" \` | Stores `q0` twice to the bytes 192 to 223 of the block. |
| 598 | `            "stp q0, q0, [%[p], #224]\n\t" \` | Stores `q0` twice to the bytes 224 to 255 of the block. One loop pass has 8 store instructions. It writes 256 B, each byte once, in rising address order. The unrolling is part of this text: 8 `stp` per loop pass. |
| 599 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the write pointer forward by 256 B. |
| 600 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the write pointer with `end`. |
| 601 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 602 | `            : [p] "+r"(p) \` | `[p] "+r"(p)`: `p` is in a general register. The text reads it and changes it. |
| 603 | `            : [end] "r"(end), [v] "r"(v) \` | `end` and `v` are inputs in general registers. |
| 604 | `            : "v0", "memory", "cc"); \` | The clobber list: the text changes the vector register `v0`, memory and the condition flags. The calling rules do not require a function to keep `v0`. So gcc saves no register in this function. |
| 605 | `    }` | Ends the kernel function and the macro. |
| 606 | `DEF_ASMWRITE(asmwrite)` | Defines `k_asmwrite`, the kernel `asmwrite`. Machine code in `bwx`: one loop pass is 11 instructions for 256 B: 8 `stp`, `add x0, x0, #0x100`, `cmp x0, x1` and `b.cc`. Before the loop stand the `add` that computes the end address and the `dup`. After it stands `ret` [Ref1]. The first touch uses `k_write` (line 442), not this loop. |
| 607 | `DEF_ASMWRITE(asmwrite2)` | Defines `k_asmwrite2`, the A/A copy of `asmwrite`. The listing of the CRB build of `bwx` shows the same instruction text for both [Ref1]. |

### Macro `DEF_ASMCOPY`: the hand-written copy loop, kernels `asmcopy` and `asmcopy2` (lines 609 to 646)

| Line | Source | Explanation |
|---:|---|---|
| 609 | `#define DEF_ASMCOPY(name) \` | Starts the macro `DEF_ASMCOPY(name)`. It defines one kernel function with a hand-written copy loop. |
| 610 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 74). |
| 611 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. `noinline`: gcc must keep the function separate from its caller. |
| 612 | `    { \` | Opens the body of the kernel function. |
| 613 | `        uint64_t *dp = d; \` | `dp`: the write pointer in the destination. It starts at `d`. |
| 614 | `        const uint64_t *sp = s; \` | `sp`: the read pointer in the source. It starts at `s`. |
| 615 | `        const uint64_t *end = s + n; \` | `end`: the first address after the source range: `s` plus `n` words. |
| 616 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 617 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx` the loop of `k_asmcopy` starts at an address of 52 modulo 64 [Ref1]. |
| 618 | `            "ldp q0, q1, [%[s]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. `%[s]` stands for the register of the read pointer `sp`. |
| 619 | `            "ldp q2, q3, [%[s], #32]\n\t" \` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 620 | `            "ldp q4, q5, [%[s], #64]\n\t" \` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 621 | `            "ldp q6, q7, [%[s], #96]\n\t" \` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 622 | `            "ldp q8, q9, [%[s], #128]\n\t" \` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 623 | `            "ldp q10, q11, [%[s], #160]\n\t" \` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 624 | `            "ldp q12, q13, [%[s], #192]\n\t" \` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 625 | `            "ldp q14, q15, [%[s], #224]\n\t" \` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 load instructions for 256 B. |
| 626 | `            "stp q0, q1, [%[d]]\n\t" \` | `stp` stores two 16-byte vector registers to memory: `q0` and `q1` to the bytes 0 to 31 of the current destination block. `%[d]` stands for the register of the write pointer `dp`. Each loaded register is stored once and has no other use. |
| 627 | `            "stp q2, q3, [%[d], #32]\n\t" \` | Stores `q2` and `q3` to the bytes 32 to 63 of the destination block. |
| 628 | `            "stp q4, q5, [%[d], #64]\n\t" \` | Stores `q4` and `q5` to the bytes 64 to 95 of the destination block. |
| 629 | `            "stp q6, q7, [%[d], #96]\n\t" \` | Stores `q6` and `q7` to the bytes 96 to 127 of the destination block. |
| 630 | `            "stp q8, q9, [%[d], #128]\n\t" \` | Stores `q8` and `q9` to the bytes 128 to 159 of the destination block. |
| 631 | `            "stp q10, q11, [%[d], #160]\n\t" \` | Stores `q10` and `q11` to the bytes 160 to 191 of the destination block. |
| 632 | `            "stp q12, q13, [%[d], #192]\n\t" \` | Stores `q12` and `q13` to the bytes 192 to 223 of the destination block. |
| 633 | `            "stp q14, q15, [%[d], #224]\n\t" \` | Stores `q14` and `q15` to the bytes 224 to 255 of the destination block. One loop pass has 8 store instructions for 256 B. The unrolling is part of this text: 8 `ldp` and 8 `stp` per loop pass. |
| 634 | `            "add %[s], %[s], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 635 | `            "add %[d], %[d], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 636 | `            "cmp %[s], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 637 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the read pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 638 | `            : [s] "+r"(sp), [d] "+r"(dp) \` | `sp` and `dp` are in general registers. The text reads them and changes them. |
| 639 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 640 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 641 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop, as in the read loop of line 550. |
| 642 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 643 | `    }` | Ends the kernel function and the macro. |
| 644 | `DEF_ASMCOPY(asmcopy)` | Defines `k_asmcopy`, the kernel `asmcopy`. Machine code in `bwx`: one loop pass is 20 instructions for 256 B loaded and 256 B stored: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.cc`. The function saves `d8` to `d15` before the loop and loads them back after it [Ref1]. |
| 645 | `DEF_ASMCOPY(asmcopy2)` | Defines `k_asmcopy2`, the A/A copy of `asmcopy`. The listing of the CRB build of `bwx` shows the same instruction text for both [Ref1]. |

### Function `k_asmcopy_c`: the machine code of the C copy loop as assembly text (lines 647 to 687)

| Line | Source | Explanation |
|---:|---|---|
| 647 | `/*` | Opens the comment about the kernel `asmcopy_c`. |
| 648 | ` * Step B2. asmcopy_c: the loop is the machine code of the C copy loop, from` | Comment: the kernel belongs to step B2 of the file `handoff.md`, the specification of the first runner. Its loop is the machine code of the C copy loop, written as assembly text. |
| 649 | ` * the listing "bw_new k_copy" of probe.txt: same instruction order, same` | Comment: the machine code comes from the listing `bw_new k_copy` of the file `probe.txt` [Ref3]. The loop has the same order of instructions. |
| 650 | ` * offsets, registers q16 to q31, and "cmp end, s; b.hi" as its loop end. The` | Comment: it also has the same offsets and the same registers `q16` to `q31`. Its loop end is `cmp end, s` followed by `b.hi`. |
| 651 | ` * three pointers are bound to x0, x1 and x2, the registers of that listing.` | Comment: the three pointers are bound to the registers `x0`, `x1` and `x2`, the registers of that listing. In the listing of `bwx` the functions `k_asmcopy_c` and `k_copy` have the same instruction text [Ref1]. |
| 652 | ` */` | Ends the comment. |
| 653 | `PLACE(asmcopy_c);` | `PLACE` adds the pad `PAD_asmcopy_c`, which is 48 bytes with the default values (line 110). |
| 654 | `__attribute__((noinline)) static void k_asmcopy_c(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c`, the kernel `asmcopy_c`. It copies `n` 8-byte words from `s` to `d`. |
| 655 | `{` | Opens the body of `k_asmcopy_c`. |
| 656 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer. `register ... __asm__("x0")` binds this C variable to the register `x0` for the `asm` statement below. |
| 657 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 658 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 659 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 660 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx` the loop starts 4 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 661 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 662 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 663 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 664 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 665 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 666 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 667 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 668 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 669 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. In this kernel the `add` stands before the stores. |
| 670 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 671 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 672 | `        "stp q29, q28, [%[d], #-224]\n\t"` | Stores `q29` and `q28` at the offset -224 from the moved write pointer. These are the bytes 32 to 63 of the destination block. |
| 673 | `        "stp q27, q26, [%[d], #-192]\n\t"` | Stores `q27` and `q26` at the offset -192: the bytes 64 to 95 of the destination block. |
| 674 | `        "stp q25, q24, [%[d], #-160]\n\t"` | Stores `q25` and `q24` at the offset -160: the bytes 96 to 127 of the destination block. |
| 675 | `        "stp q23, q22, [%[d], #-128]\n\t"` | Stores `q23` and `q22` at the offset -128: the bytes 128 to 159 of the destination block. |
| 676 | `        "stp q21, q20, [%[d], #-96]\n\t"` | Stores `q21` and `q20` at the offset -96: the bytes 160 to 191 of the destination block. |
| 677 | `        "stp q19, q18, [%[d], #-64]\n\t"` | Stores `q19` and `q18` at the offset -64: the bytes 192 to 223 of the destination block. |
| 678 | `        "stp q17, q16, [%[d], #-32]\n\t"` | Stores `q17` and `q16` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 679 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 680 | `        "b.hi 1b\n\t"` | `b.hi 1b` branches back to the label `1` while `end` is higher than the read pointer, as unsigned numbers. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 681 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 682 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 683 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 684 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. The calling rules do not require a function to keep `v16` to `v31`. So gcc saves no register in this function. |
| 685 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 686 | `}` | Ends the function `k_asmcopy_c`. |

### Function `k_asmcopy_c_add`: the same loop with both `add` after the stores (lines 688 to 724)

| Line | Source | Explanation |
|---:|---|---|
| 688 | `/* As asmcopy_c, but the two add stand after the 8 stp, and the 8 stp use the` | Comment: the kernel below is `asmcopy_c` with two changes. The two `add` instructions stand after the 8 `stp`. |
| 689 | ` * offsets 0 to 224, as in asmcopy. Registers stay q16 to q31. */` | Comment: the 8 `stp` use the offsets 0 to 224, as in `asmcopy`. The registers stay `q16` to `q31`. |
| 690 | `PLACE(asmcopy_c_add);` | `PLACE` adds the pad `PAD_asmcopy_c_add`, which is 48 bytes with the default values (line 113). |
| 691 | `__attribute__((noinline)) static void k_asmcopy_c_add(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_add`, the kernel `asmcopy_c_add`. It copies `n` 8-byte words from `s` to `d`. |
| 692 | `{` | Opens the body of `k_asmcopy_c_add`. |
| 693 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 694 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 695 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 696 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 697 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx` the loop starts at an address of 52 modulo 64 [Ref1]. |
| 698 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 699 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 700 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 701 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 702 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 703 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 704 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 705 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 706 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 707 | `        "stp q29, q28, [%[d], #32]\n\t"` | Stores `q29` and `q28` to the bytes 32 to 63 of the destination block. |
| 708 | `        "stp q27, q26, [%[d], #64]\n\t"` | Stores `q27` and `q26` to the bytes 64 to 95 of the destination block. |
| 709 | `        "stp q25, q24, [%[d], #96]\n\t"` | Stores `q25` and `q24` to the bytes 96 to 127 of the destination block. |
| 710 | `        "stp q23, q22, [%[d], #128]\n\t"` | Stores `q23` and `q22` to the bytes 128 to 159 of the destination block. |
| 711 | `        "stp q21, q20, [%[d], #160]\n\t"` | Stores `q21` and `q20` to the bytes 160 to 191 of the destination block. |
| 712 | `        "stp q19, q18, [%[d], #192]\n\t"` | Stores `q19` and `q18` to the bytes 192 to 223 of the destination block. |
| 713 | `        "stp q17, q16, [%[d], #224]\n\t"` | Stores `q17` and `q16` to the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 714 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. Here both `add` instructions stand after the stores. |
| 715 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. |
| 716 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 717 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 718 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 719 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 720 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 721 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. gcc saves no register for them. |
| 722 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 723 | `}` | Ends the function `k_asmcopy_c_add`. |

### Function `k_asmcopy_c_reg`: the same loop with the registers `q0` to `q15` (lines 725 to 761)

| Line | Source | Explanation |
|---:|---|---|
| 725 | `/* As asmcopy_c, but with the registers q0 to q15 (q31 becomes q0, q30` | Comment: the kernel below is `asmcopy_c` with other registers: `q0` to `q15`. The register `q31` of `asmcopy_c` becomes `q0` here. |
| 726 | ` * becomes q1, and so on), and d8 to d15 named as clobbered, as in asmcopy. */` | Comment: `q30` becomes `q1`, and so on. The clobber list names `v8` to `v15`, as in `asmcopy`. So gcc saves `d8` to `d15`. |
| 727 | `PLACE(asmcopy_c_reg);` | `PLACE` adds the pad `PAD_asmcopy_c_reg`, which is 32 bytes with the default values (line 116). |
| 728 | `__attribute__((noinline)) static void k_asmcopy_c_reg(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_reg`, the kernel `asmcopy_c_reg`. It copies `n` 8-byte words from `s` to `d`. |
| 729 | `{` | Opens the body of `k_asmcopy_c_reg`. |
| 730 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 731 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 732 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 733 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 734 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx` the loop starts 20 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 735 | `        "ldp q0, q1, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. |
| 736 | `        "ldp q2, q3, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 737 | `        "ldp q4, q5, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 738 | `        "ldp q6, q7, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 739 | `        "ldp q8, q9, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 740 | `        "ldp q10, q11, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 741 | `        "ldp q12, q13, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 742 | `        "ldp q14, q15, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 `ldp` for 256 B. |
| 743 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B, before the stores. |
| 744 | `        "stp q0, q1, [%[d]]\n\t"` | Stores `q0` and `q1` to the bytes 0 to 31 of the current destination block. |
| 745 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 746 | `        "stp q2, q3, [%[d], #-224]\n\t"` | Stores `q2` and `q3` at the offset -224 from the moved write pointer: the bytes 32 to 63 of the destination block. |
| 747 | `        "stp q4, q5, [%[d], #-192]\n\t"` | Stores `q4` and `q5` at the offset -192: the bytes 64 to 95 of the destination block. |
| 748 | `        "stp q6, q7, [%[d], #-160]\n\t"` | Stores `q6` and `q7` at the offset -160: the bytes 96 to 127 of the destination block. |
| 749 | `        "stp q8, q9, [%[d], #-128]\n\t"` | Stores `q8` and `q9` at the offset -128: the bytes 128 to 159 of the destination block. |
| 750 | `        "stp q10, q11, [%[d], #-96]\n\t"` | Stores `q10` and `q11` at the offset -96: the bytes 160 to 191 of the destination block. |
| 751 | `        "stp q12, q13, [%[d], #-64]\n\t"` | Stores `q12` and `q13` at the offset -64: the bytes 192 to 223 of the destination block. |
| 752 | `        "stp q14, q15, [%[d], #-32]\n\t"` | Stores `q14` and `q15` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 753 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 754 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 755 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 756 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 757 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 758 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call: the listing of `bwx` shows 4 `stp` before the loop and 4 `ldp` after it [Ref1]. |
| 759 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 760 | `}` | Ends the function `k_asmcopy_c_reg`. |

### Stand-ins for a machine that is not AArch64 (lines 762 to 809)

| Line | Source | Explanation |
|---:|---|---|
| 762 | `#else` | `#else` of the `#if defined(__aarch64__)` of line 402. The compiler reads lines 763 to 807 only for a machine that is not AArch64. A build on CRB, an Arm machine, does not compile these lines. |
| 763 | `/*` | Opens the comment about the stand-ins. |
| 764 | ` * Stand-ins for a machine that is not AArch64: plain C loops that touch` | Comment: the stand-ins are for a machine that is not AArch64. They are plain C loops. |
| 765 | ` * exactly the same bytes as the real kernels. They exist only so that the` | Comment: each stand-in touches exactly the same bytes as the real kernel. The stand-ins have one purpose only. |
| 766 | ` * harness can be compiled and run on the development machine.` | Comment: the purpose: the program can be compiled and run on the development machine. |
| 767 | ` */` | Ends the comment. |
| 768 | `#define STANDIN 1` | `STANDIN` is 1 in this branch. It is 0 in the AArch64 branch (line 403). The header of the output then says that the kernels are stand-ins and that the rates mean nothing (line 1256). |
| 769 | `#define DEF_ASMREAD(name, nops) \` | Starts the stand-in form of the macro `DEF_ASMREAD(name, nops)`. It has the name and the arguments of the AArch64 macro of line 527, with a plain C loop over the same range. A build on CRB, an Arm machine, does not compile this branch. |
| 770 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel, as in the AArch64 branch. |
| 771 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range and `n` its length in 8-byte words. |
| 772 | `    { \` | Opens the body of the kernel function. |
| 773 | `        const volatile uint64_t *p = a; \` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 774 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 775 | `            (void)p[i]; \` | Reads word `i` and drops the value. The cast to `void` says that the value is not used. So the loop reads every word of the range once. The macro argument `nops` is not used in this branch. |
| 776 | `    }` | Ends the kernel function and the macro. |
| 777 | `#define DEF_ASMWRITE(name) \` | Starts the stand-in form of the macro `DEF_ASMWRITE(name)`, with a plain C loop. |
| 778 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 779 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores `v` to `n` 8-byte words, from the address `a` on. |
| 780 | `    { \` | Opens the body of the kernel function. |
| 781 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 782 | `            a[i] = v; \` | Stores `v` to word `i`. |
| 783 | `    }` | Ends the kernel function and the macro. |
| 784 | `#define DEF_ASMCOPY(name) \` | Starts the stand-in form of the macro `DEF_ASMCOPY(name)`, with a plain C loop. |
| 785 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 786 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. |
| 787 | `    { \` | Opens the body of the kernel function. |
| 788 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 789 | `            d[i] = s[i]; \` | Copies word `i` from the source to the destination. |
| 790 | `    }` | Ends the kernel function and the macro. |
| 791 | `DEF_ASMREAD(read, 0)` | Stand-in build only: defines `k_read` as the plain read loop of lines 769 to 776. This line and the 16 lines below define all 17 kernels of lines 411 to 760 from the three stand-in macros. |
| 792 | `DEF_ASMWRITE(write)` | Stand-in build only: defines `k_write` as the plain write loop of lines 777 to 783. In such a build this function also does the first touch (line 988). |
| 793 | `DEF_ASMCOPY(copy)` | Stand-in build only: defines `k_copy` as the plain copy loop of lines 784 to 790. |
| 794 | `DEF_ASMREAD(asmread, 0)` | Stand-in build only: defines `k_asmread` as the plain read loop. |
| 795 | `DEF_ASMREAD(asmread2, 0)` | Stand-in build only: defines `k_asmread2` as the plain read loop. |
| 796 | `DEF_ASMREAD(read_nop4, 4)` | Stand-in build only: defines `k_read_nop4` as the plain read loop. The stand-in macro does not use the number 4. |
| 797 | `DEF_ASMREAD(read_nop8, 8)` | Stand-in build only: defines `k_read_nop8` as the plain read loop. The number 8 is not used. |
| 798 | `DEF_ASMREAD(read_nop16, 16)` | Stand-in build only: defines `k_read_nop16` as the plain read loop. The number 16 is not used. |
| 799 | `DEF_ASMREAD(read_nop32, 32)` | Stand-in build only: defines `k_read_nop32` as the plain read loop. The number 32 is not used. |
| 800 | `DEF_ASMREAD(read_sparse, 9)` | Stand-in build only: defines `k_read_sparse` as the plain read loop. The number 9 is not used. The real kernel also reads every byte of its range. |
| 801 | `DEF_ASMWRITE(asmwrite)` | Stand-in build only: defines `k_asmwrite` as the plain write loop. |
| 802 | `DEF_ASMWRITE(asmwrite2)` | Stand-in build only: defines `k_asmwrite2` as the plain write loop. |
| 803 | `DEF_ASMCOPY(asmcopy)` | Stand-in build only: defines `k_asmcopy` as the plain copy loop. |
| 804 | `DEF_ASMCOPY(asmcopy2)` | Stand-in build only: defines `k_asmcopy2` as the plain copy loop. |
| 805 | `DEF_ASMCOPY(asmcopy_c)` | Stand-in build only: defines `k_asmcopy_c` as the plain copy loop. |
| 806 | `DEF_ASMCOPY(asmcopy_c_add)` | Stand-in build only: defines `k_asmcopy_c_add` as the plain copy loop. |
| 807 | `DEF_ASMCOPY(asmcopy_c_reg)` | Stand-in build only: defines `k_asmcopy_c_reg` as the plain copy loop. |
| 808 | `#endif` | Ends the `#if` of line 402. |

### The kernel table `kernels` (lines 810 to 828)

| Line | Source | Explanation |
|---:|---|---|
| 810 | `/* The function is named k_<name>. The cast to void (*)(void) is undone by` | Comment: the function of a kernel has the name `k_` plus the kernel name. The table stores its address with a cast to the common pointer type `void (*)(void)`. |
| 811 | ` * call() according to the type. */` | Comment: `call` (line 833) undoes the cast according to the type of the kernel. |
| 812 | `static const struct kdef {` | Starts `struct kdef`, the type of one entry of the kernel table. |
| 813 | `    const char *name;` | `name`: the name of the kernel. It is the word that `--seq` accepts. `parse_seq` (line 1092) compares each word of `--seq` with the names and stores the index of the entry that matches. |
| 814 | `    enum ktype type;` | `type`: one of `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD` (line 164). It tells `call` which arguments the function takes. |
| 815 | `    void (*fn)(void);` | `fn`: the pointer to the kernel function, stored as one common pointer type. `call` casts it back to the real type before it calls the function. |
| 816 | `} kernels[] = {` | Ends the structure and starts the kernel table `kernels[]`. For each interval the worker takes the entry of the kernel from this table (line 1000) and passes it to `call`. |
| 817 | `#define K(name, type) { #name, type, (void (*)(void))k_##name }` | The macro `K(name, type)` writes one entry. `K(read, T_READ)` becomes `{ "read", T_READ, (void (*)(void))k_read }`. `#name` gives the kernel name as text. `k_##name` gives the function. |
| 818 | `    K(read, T_READ), K(write, T_WRITE), K(copy, T_COPY),` | Entries 0 to 2: `read`, `write` and `copy`, the C kernels with NEON intrinsics. `read` is entry 0 with the type `T_READ`: the new read kernel. |
| 819 | `    K(asmread, T_READ), K(asmwrite, T_WRITE), K(asmcopy, T_COPY),` | Entries 3 to 5: `asmread`, `asmwrite` and `asmcopy`, the hand-written assembly kernels. `asmread` is entry 3 with the type `T_READ`. |
| 820 | `    K(oldread, T_OLDREAD), K(oldwrite, T_WRITE), K(oldcopy, T_COPY),` | Entries 6 to 8: `oldread`, `oldwrite` and `oldcopy`, the old kernels. `oldread` is entry 6 with the type `T_OLDREAD`: the old read kernel. |
| 821 | `    K(asmread2, T_READ), K(asmwrite2, T_WRITE), K(asmcopy2, T_COPY), K(oldread2, T_OLDREAD),` | Entries 9 to 12: the A/A copies `asmread2`, `asmwrite2`, `asmcopy2` and `oldread2`. |
| 822 | `    K(asmcopy_c, T_COPY), K(asmcopy_c_add, T_COPY), K(asmcopy_c_reg, T_COPY),` | Entries 13 to 15: the copy kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. |
| 823 | `    K(read_nop4, T_READ), K(read_nop8, T_READ), K(read_nop16, T_READ), K(read_nop32, T_READ),` | Entries 16 to 19: the read kernels `read_nop4`, `read_nop8`, `read_nop16` and `read_nop32`. |
| 824 | `    K(read_sparse, T_READ),` | Entry 20: the read kernel `read_sparse`. In this version of the runner it is the last entry of the table. |
| 825 | `#undef K` | Removes the macro `K`. It is needed only inside the table. |
| 826 | `};` | Ends the kernel table. |
| 827 | `#define K_COUNT ((int)(sizeof kernels / sizeof kernels[0]))` | `K_COUNT`: the number of entries of the table. It is the size of the table divided by the size of one entry. In `bwx` it is 21, and the listing of the CRB build holds 21 kernel functions for each of its binaries [Ref1]. The worker calls `k_write` directly for the first touch (line 988), not through the table. |

### Function `call`: run one kernel on one range of a buffer (lines 829 to 852)

| Line | Source | Explanation |
|---:|---|---|
| 829 | `/* Runs kernel kd on len bytes at byte offset off of the thread's buffers. A` | Comment: the function below runs the kernel `kd` on `len` bytes that start at the byte offset `off` of the buffers of the thread. |
| 830 | ` * read or write kernel uses buffer a. A copy kernel reads a and writes b. The` | Comment: a read kernel or a write kernel uses the buffer `a`. A copy kernel reads `a` and writes `b`. |
| 831 | ` * sink of the old read kernel is on the stack of the thread, as it was in the` | Comment: the sink of the old read kernel is the variable that takes its sum. It lies on the stack of the thread (line 977), as it did in the function `pass` of the old benchmark source. |
| 832 | ` * old pass(), so the threads do not all store to one shared cache line. */` | Comment: so the threads do not all store to one shared cache line. |
| 833 | `static void call(const struct kdef *kd, struct thread *t, size_t off, size_t len, uint64_t v, volatile uint64_t *sink)` | Starts the function `call`. It runs one kernel on one range of a buffer. `kd` is the table entry of the kernel. `t` is the record of the calling thread. `off` and `len` give the range in bytes. `v` is the value that a write kernel stores. `sink` points to the variable that takes the sum of an old read kernel. The worker calls this function once per interval for the warm-up pass (line 1011). With `--stop common` it calls it once for each chunk of the timed loop (line 1037). In the timed loop the function runs between the clock reads `t0` and `t1`. So its own instructions are part of the timed interval, once per chunk. |
| 834 | `{` | Opens the body of `call`. |
| 835 | `    uint64_t *a = t->a + off / 8;` | `a`: the address of the first word of the range. `t->a` points to 8-byte words. So `off / 8` words are `off` bytes. |
| 836 | `    size_t n = len / 8;` | `n`: the length of the range in 8-byte words. One chunk of 2 MiB gives 262144 words. The warm-up pass of a `--seq` entry of 256 MiB gives 33554432 words. |
| 837 | `    switch (kd->type) {` | Chooses the form of the call by the type of the kernel. |
| 838 | `    case T_READ:` | The case of a read kernel. |
| 839 | `        ((read_fn)kd->fn)(a, n);` | Casts the pointer to the type `read_fn` (line 165) and calls the kernel with the address and the word count. The kernel returns nothing. |
| 840 | `        break;` | Leaves the `switch`. |
| 841 | `    case T_OLDREAD:` | The case of an old read kernel. |
| 842 | `        *sink = ((oldread_fn)kd->fn)(a, n);` | Calls the kernel, which returns its sum, and stores the sum to `*sink`. `sink` points to a `volatile` variable on the stack of the worker (line 977). So the compiler must keep the store and must compute the sum. The listing of `k_oldread` in `bwx` holds the adds [Ref1]. This path has one store of 8 bytes per call that the `T_READ` path does not have. In the timed loop of `--stop common` that is one store per chunk (line 1037). |
| 843 | `        break;` | Leaves the `switch`. |
| 844 | `    case T_WRITE:` | The case of a write kernel. |
| 845 | `        ((write_fn)kd->fn)(a, n, v);` | Casts the pointer to the type `write_fn` and calls the write kernel with the address, the word count and the value `v` to store. |
| 846 | `        break;` | Leaves the `switch`. |
| 847 | `    case T_COPY:` | The case of a copy kernel. |
| 848 | `        ((copy_fn)kd->fn)(t->b + off / 8, a, n);` | Casts the pointer to the type `copy_fn` and calls the copy kernel. The kernel reads the range of the buffer `a` and writes the same range of the buffer `b`. |
| 849 | `        break;` | Leaves the `switch`. |
| 850 | `    }` | Ends the `switch` of line 837. |
| 851 | `}` | Ends the function `call`. It returns no value. |

### Function `read_smaps`: the page state of the buffers (lines 853 to 885)

| Line | Source | Explanation |
|---:|---|---|
| 853 | `/* Page state (handoff B.6). For each of the n buffers (a NULL entry is` | Comment: the function below reads the page state. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. The function works on `n` buffers and skips an entry that is `NULL`. |
| 854 | ` * skipped): the entry of /proc/self/smaps whose start is the buffer and whose` | Comment: for each buffer it looks for the entry of the Linux file `/proc/self/smaps` whose start is the buffer address. |
| 855 | ` * end is the buffer plus buf_len(). Without such an entry both values stay -1` | Comment: the end of that entry must be the buffer address plus `buf_len()`. Without such an entry both values stay -1. |
| 856 | ` * and are printed as NA. */` | Comment: a value of -1 is printed as `NA`. |
| 857 | `static void read_smaps(struct page *pg, uint64_t *const *buf, int n)` | Starts the function `read_smaps`. For each of the `n` buffer addresses in `buf` it looks for the mapping of that buffer in `/proc/self/smaps`. It writes two values to `pg`: the size of the mapping and the part of it on 2 MiB pages, both in kB. In a process with more than one thread `main` calls it before the first interval and after each interval (line 1343). During the call all workers wait at the barrier (line 995 or line 1073). So the call is not timed. |
| 858 | `{` | Opens the body of `read_smaps`. In a process with one thread the worker calls the function before each interval (line 1014): after the warm-up pass and before its barrier wait of line 1017. The timed interval starts later, at the clock read `t0` (line 1030). This call is not timed either. |
| 859 | `    char line[256];` | `line`: the buffer for one line of the file, at most 255 characters. |
| 860 | `    int cur = -1;` | `cur`: the index of the buffer whose mapping the loop below is reading, or -1 for no buffer. |
| 861 | `    size_t len = buf_len();` | `len`: the buffer length from `buf_len` (line 337). |
| 862 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 863 | `        pg[i].kb_total = pg[i].kb_huge = -1;` | Sets both values of the entry to -1. The value -1 means that the buffer was not found. |
| 864 | `    FILE *f = fopen("/proc/self/smaps", "r");` | Opens `/proc/self/smaps` for reading. The file lists every memory mapping of the process. So it holds the buffers of all threads. |
| 865 | `    if (!f)` | Tests whether the file did not open. |
| 866 | `        return;` | In that case the function returns, and all values stay -1. |
| 867 | `    while (fgets(line, sizeof line, f)) {` | Starts a loop that reads the file line by line. It ends at the end of the file. |
| 868 | `        unsigned long s, e;` | `s` and `e`: the start address and the end address of a mapping. |
| 869 | `        char perms[8];` | `perms`: the word after the two addresses, at most 7 characters. In the file it holds the access rights of the mapping. The function does not use its content. |
| 870 | `        if (sscanf(line, "%lx-%lx %7s", &s, &e, perms) == 3) {` | `sscanf` returns 3 when the line starts with `start-end`, two hexadecimal addresses, and a word after them. Such a line is the first line of a mapping. |
| 871 | `            cur = -1;` | At the first line of a mapping `cur` is first set back to -1. |
| 872 | `            for (int i = 0; i < n; i++)` | Then a loop compares the mapping with every buffer. |
| 873 | `                if (buf[i] && (unsigned long)(uintptr_t)buf[i] == s && e == s + len)` | A buffer matches when its entry is not `NULL`, the mapping starts at the buffer address and the mapping ends exactly `len` bytes after it. The comment of `alloc_buf` (lines 342 to 344) gives the reason for the exact test: no-access ranges stand before and after each buffer, so Linux lists the buffer as one mapping of its own. |
| 874 | `                    cur = i;` | On a match `cur` becomes the index of that buffer. When no buffer matches, `cur` stays -1. Then the next lines of that mapping store nothing, and they cannot change the values of a buffer that was read before. |
| 875 | `        } else if (cur >= 0) {` | Every other line belongs to the mapping whose first line was read last. This branch runs only when that mapping is a buffer (`cur >= 0`). |
| 876 | `            sscanf(line, "Size: %ld kB", &pg[cur].kb_total);` | This `sscanf` stores a number only when the line starts with `Size:`. The number is the size of the mapping in kB and goes to `kb_total`. |
| 877 | `            sscanf(line, "AnonHugePages: %ld kB", &pg[cur].kb_huge);` | This `sscanf` stores a number only when the line starts with `AnonHugePages:`. The number is the part of the mapping on 2 MiB pages in kB and goes to `kb_huge`. All other lines store nothing. |
| 878 | `        }` | Ends the `else if` of line 875. |
| 879 | `    }` | Ends the loop of line 867. |
| 880 | `    fclose(f);` | Closes the file. |
| 881 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 882 | `        if (pg[i].kb_total < 0 \|\| pg[i].kb_huge < 0)` | Tests whether one of the two values of the entry is still below 0. |
| 883 | `            pg[i].kb_total = pg[i].kb_huge = -1;` | In that case both values are set to -1. `print_p` (line 912) prints a value below 0 as `NA`. |
| 884 | `}` | Ends the function `read_smaps`. |

### Function `read_vmstat`: four counters of the whole system (lines 886 to 903)

| Line | Source | Explanation |
|---:|---|---|
| 886 | `/* Four counters of /proc/vmstat. They count for the whole system. -1: not found. */` | Comment: the function below reads four counters of the Linux file `/proc/vmstat`. They count for the whole system, not for one buffer. The value -1 means that a counter was not found. |
| 887 | `static void read_vmstat(long long vm[4])` | Starts the function `read_vmstat`. It reads the four counters into `vm[0]` to `vm[3]`, in the order of the names in line 889. They become the last four columns of every P row. In a process with more than one thread `main` calls it once before the first interval and once after each interval (line 1344). In a process with one thread the worker calls it before each interval (line 1015): after the warm-up pass and before its barrier wait of line 1017. The timed interval starts later, at the clock read `t0` (line 1030). It is not timed. |
| 888 | `{` | Opens the body of `read_vmstat`. |
| 889 | `    static const char *name[4] = { "thp_fault_alloc", "thp_fault_fallback", "thp_collapse_alloc", "pgmigrate_success" };` | `name`: the names of the four counters. The Linux documentation gives their meanings [Ref6]. `thp_fault_alloc` counts the 2 MiB pages that Linux gave at a page fault. `thp_fault_fallback` counts the page faults at which Linux could not give a 2 MiB page and used small pages. `thp_collapse_alloc` counts the 2 MiB pages that Linux made later from a range of small pages. `pgmigrate_success` counts the pages that Linux moved to another place in physical memory. |
| 890 | `    char key[64];` | `key`: the buffer for one name of the file, at most 63 characters. |
| 891 | `    long long val;` | `val`: the number that follows the name. |
| 892 | `    for (int i = 0; i < 4; i++)` | A loop over the four values. |
| 893 | `        vm[i] = -1;` | Sets the value to -1. The value -1 means that the counter was not found. |
| 894 | `    FILE *f = fopen("/proc/vmstat", "r");` | Opens `/proc/vmstat` for reading. |
| 895 | `    if (!f)` | Tests whether the file did not open. |
| 896 | `        return;` | In that case the function returns with the four values at -1. |
| 897 | `    while (fscanf(f, "%63s %lld", key, &val) == 2)` | Each line of the file holds a name and a number. `fscanf` reads one such pair per loop pass. The loop ends when `fscanf` finds no further pair, for example at the end of the file. |
| 898 | `        for (int i = 0; i < 4; i++)` | A loop over the four names. |
| 899 | `            if (!strcmp(key, name[i]))` | Tests whether the name from the file equals name `i`. `strcmp` returns 0 for equal texts. |
| 900 | `                vm[i] = val;` | On a match the number goes to the matching place in `vm`. |
| 901 | `    fclose(f);` | Closes the file. |
| 902 | `}` | Ends the function `read_vmstat`. |

### Function `print_na`: one csv field, or `NA` (lines 904 to 911)

| Line | Source | Explanation |
|---:|---|---|
| 904 | `static void print_na(long long v)` | Starts the function `print_na`. It prints one more field of a csv row: a comma and then the number `v`. For a negative `v` it prints `,NA`. The functions `read_smaps` (line 857) and `read_vmstat` (line 887) store -1 for a value that they did not find. So such a value shows as `NA` in a P row. |
| 905 | `{` | Opens the body of `print_na`. |
| 906 | `    if (v < 0)` | Tests whether `v` is negative. |
| 907 | `        printf(",NA");` | A negative value prints as a comma and the text `NA` (not available). |
| 908 | `    else` | The case of a value of 0 or more. |
| 909 | `        printf(",%lld", v);` | Prints a comma and the number in decimal. |
| 910 | `}` | Ends the function `print_na`. |

### Function `print_p`: one P row, the page state of one buffer (lines 912 to 921)

| Line | Source | Explanation |
|---:|---|---|
| 912 | `static void print_p(int round, int pos, int tid, char buffer, const struct page *pg, const long long vm[4])` | Starts the function `print_p`. It prints one P row: the page state of one buffer at one reading. `round`, `pos` and `tid` are the round, the position and the thread index. `buffer` is the letter `a` or `b`. `pg` holds the two page values of the buffer. `vm` holds four counters of the Linux file `/proc/vmstat`. In a process with more than one thread `main` calls it once per buffer after each reading of the page state (line 1349). In a process with one thread `main` calls it in line 1305 and line 1307. |
| 913 | `{` | Opens the body of `print_p`. |
| 914 | `    printf("P,%d,%d,%d,%c", round, pos, tid, buffer);` | Columns 1 to 5 of the row: the letter `P`, the round, the position, the thread index and the buffer letter. The position is -1 in the rows of the reading before the first interval (line 1275). In every other row of a process with more than one thread it is the position of the interval that has ended directly before the reading. In a process with one thread the row holds the state that the worker read before the interval of that position (line 1012). |
| 915 | `    print_na(pg->kb_total);` | Column 6, `kB_total`: the size of the mapping of the buffer. The unit is kB of 1024 bytes. `read_smaps` (line 857) took the value from the line `Size` of the Linux file `/proc/self/smaps`. A value that it did not find prints as `NA`. |
| 916 | `    print_na(pg->kb_huge);` | Column 7, `kB_huge`: the part of the buffer that lies on 2 MiB pages, in kB of 1024 bytes. `read_smaps` took it from the line `AnonHugePages` of the same file. |
| 917 | `    for (int i = 0; i < 4; i++)` | Loop over the four counters of `/proc/vmstat`. |
| 918 | `        print_na(vm[i]);` | Columns 8 to 11: the counters `thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc` and `pgmigrate_success`, in this order (line 889). They count for the whole system, not for this buffer. `main` passes the same array `vm` for all buffers of one reading (line 1349). So all P rows of one reading hold the same four values. |
| 919 | `    printf("\n");` | Ends the row with a line break. |
| 920 | `}` | Ends the function `print_p`. |

### Function `open_counters`: open the counter group of one thread (lines 922 to 950)

| Line | Source | Explanation |
|---:|---|---|
| 922 | `/* Counters (handoff B.8): one group per thread, user mode only, opened by the` | Comment: the counters follow section B.8 of the file `handoff.md`, the specification of the first runner. Each thread has one counter group. The counters count in user mode only. The sentence about who opens them goes on in line 923. |
| 923 | ` * pinned thread for itself. An event that does not open is printed as NA. */` | Comment: the pinned thread opens the counters for itself. An event that does not open is printed as `NA` (lines 1329 to 1330). |
| 924 | `static void open_counters(struct thread *t)` | Starts the function `open_counters`. It opens one counter per entry of `--events` for the calling thread and joins the counters into one group. With `--count` each worker calls it once (line 986), after the pinning and before it maps its buffer. `t` is the record of the calling thread. |
| 925 | `{` | Opens the body of `open_counters`. |
| 926 | `    t->group_fd = -1;` | Start state: no group leader (`group_fd` is -1). The group leader is the first counter of a counter group. |
| 927 | `    t->nopen = 0;` | Start state: 0 open counters. |
| 928 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `--events`, in the order of the list. `cfg.nev` is their number. |
| 929 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 930 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. So every option that the next lines do not set is off. The field `disabled` also stays 0. So a counter counts from the moment it is opened. |
| 931 | `        a.type = (uint32_t)cfg.pmu_type;` | `type` selects the PMU (performance monitoring unit, the hardware event counters of a core). It is the value of `--pmu-type`. |
| 932 | `        a.size = sizeof a;` | `size` gives Linux the size of the structure. |
| 933 | `        a.config = cfg.ev_code[e];` | `config` is the event code of this entry of `--events`. The program passes the code to Linux and does not interpret it. |
| 934 | `        a.exclude_kernel = 1;` | `exclude_kernel = 1`: the counter does not count while the CPU runs code of the Linux kernel. |
| 935 | `        a.exclude_hv = 1;` | `exclude_hv = 1`: the counter does not count code of a hypervisor. A hypervisor is the software that runs virtual machines. With these two fields the counter counts in user mode only: while the thread runs the code of the program itself. The specification of this program says that counter code without these two fields fails without root rights on CRB [Ref4]. |
| 936 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | `read_format` chooses what one `read` of the group returns. `PERF_FORMAT_GROUP`: the values of all counters of the group in one reading. The two other flags add the enabled time and the running time of the group [Ref5]. |
| 937 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, t->group_fd, 0);` | The system call `perf_event_open` opens the counter. It returns a file descriptor: the number that later calls such as `read` use for the open counter. A negative value means failure. The arguments `0` and `-1` are the pid and the cpu argument of the call [Ref4]. Together they mean: count the calling thread, on any CPU that it runs on. With `--cpus` the thread is pinned, so this is one CPU. The argument `t->group_fd` is -1 for the first counter, which starts a new group. A later counter passes the file descriptor of the leader and joins its group. The last argument `0` means no flags. |
| 938 | `        if (fd < 0) {` | Tests whether the open failed. |
| 939 | `            if (t->idx == 0)` | Only thread 0 writes a message. So an event that fails in every thread gives one message, not one per thread. |
| 940 | `                fprintf(stderr, "perf_event_open %s (type %ld code 0x%llx): %s (printed as NA)\n", cfg.ev_name[e],` | The message goes to stderr: the word `perf_event_open`, the event name, the PMU type, the event code in hexadecimal, the error text of Linux and the words `printed as NA`. This line holds the format and the event name. |
| 941 | `                        cfg.pmu_type, (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 940: the PMU type, the event code and the error text (`strerror(errno)`). |
| 942 | `            t->ev_pos[e] = -1;` | The event gets the position -1. `main` prints `NA` for it in the C rows (lines 1328 to 1330). |
| 943 | `            continue;` | The loop goes on with the next event. The thread does not stop. |
| 944 | `        }` | Ends the `if` of line 938. |
| 945 | `        t->ev_pos[e] = t->nopen++;` | The open succeeded. `ev_pos[e]` gets the position of this event in a group reading: 0 for the first open counter, 1 for the next. `nopen` counts the open counters of the thread. |
| 946 | `        if (t->group_fd < 0)` | Tests whether the group has no leader yet. |
| 947 | `            t->group_fd = fd;` | The first counter that opens becomes the leader of the group. `group_fd` keeps its file descriptor, and every group reading uses it (line 964). The file descriptors of the other counters are not kept. The function `worker` never closes, resets or stops a counter. |
| 948 | `    }` | Ends the loop over the events (line 928). |
| 949 | `}` | Ends the function `open_counters`. |

### Function `cpu_ns`: the CPU time of the calling thread (lines 951 to 957)

| Line | Source | Explanation |
|---:|---|---|
| 951 | `static uint64_t cpu_ns(void)` | Starts the function `cpu_ns`. It returns the CPU time that the calling thread has used so far, in ns. With `--count` the worker calls it once before and once after each timed interval (line 1028, line 1060). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 952 | `{` | Opens the body of `cpu_ns`. |
| 953 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 954 | `    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);` | Reads the Linux clock `CLOCK_THREAD_CPUTIME_ID` into `ts`. This clock counts the CPU time of the calling thread only. |
| 955 | `    return (uint64_t)ts.tv_sec * 1000000000UL + (uint64_t)ts.tv_nsec;` | Returns the time in ns: the seconds times 1000000000, plus the nanoseconds. |
| 956 | `}` | Ends the function `cpu_ns`. |

### Function `read_group`: one reading of the counter group (lines 958 to 973)

| Line | Source | Explanation |
|---:|---|---|
| 958 | `/* Group read: nr, time_enabled, time_running, then one value per open event. */` | Comment: the layout of one group reading: the number of counters (`nr`), the enabled time, the running time, then one value per open event [Ref5]. |
| 959 | `static void read_group(const struct thread *t, struct counts *c)` | Starts the function `read_group`. It takes one reading of all counters of the thread `t` and stores it in `c`. With `--count` the worker calls it once before and once after each timed interval (line 1027, line 1061). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 960 | `{` | Opens the body of `read_group`. |
| 961 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest reading: 3 header words plus 8 counter values (`MAX_EV` is 8). Each word has 8 bytes. |
| 962 | `    if (t->group_fd < 0)` | Tests whether the thread has no open counter. |
| 963 | `        return;` | Such a thread returns here. Then `c` keeps the zeros that the worker wrote in line 1009. |
| 964 | `    if (read(t->group_fd, buf, sizeof buf) < (ssize_t)(3 * sizeof buf[0]) \|\| buf[0] != (uint64_t)t->nopen) {` | One `read` system call on the leader returns the whole group: the number of counters `nr`, the enabled time, the running time, then one value per counter [Ref5]. The reading is rejected when it has fewer than 24 bytes (the 3 header words). It is also rejected when `nr` is not the number of counters that this thread opened. |
| 965 | `        perror("read of the counter group");` | A rejected reading: `perror` prints the words `read of the counter group` and the reason that Linux gave to stderr. |
| 966 | `        exit(2);` | The whole program then ends with exit status 2. |
| 967 | `    }` | Ends the `if` of line 964. |
| 968 | `    c->enabled = buf[1];` | Stores the enabled time of the group, in ns: how long the counters were enabled. |
| 969 | `    c->running = buf[2];` | Stores the running time of the group, in ns: how long the counters really counted. `main` prints the difference between the two readings of an interval as `enabled_ns` and `running_ns` in the C row (lines 1324 to 1325). |
| 970 | `    for (int i = 0; i < t->nopen; i++)` | Loop over the open counters of the thread. |
| 971 | `        c->val[i] = buf[3 + i];` | Stores one value per open counter, in the order in which the counters were opened. `main` prints for each event the difference between the reading after the interval and the reading before it (line 1332). |
| 972 | `}` | Ends the function `read_group`. |

### Function `worker`: start values, pinning, counters, buffers and first touch (lines 974 to 997)

| Line | Source | Explanation |
|---:|---|---|
| 974 | `static void *worker(void *arg)` | Starts the function `worker`, the start function of every worker thread. `main` creates the workers in line 1244. `arg` points to the record of the thread. |
| 975 | `{` | Opens the body of `worker`. |
| 976 | `    struct thread *t = arg;` | `t`: the record of this thread. `main` has set its index `idx` and its CPU `cpu` (lines 1242 to 1243). |
| 977 | `    volatile uint64_t sink;` | `sink`: a volatile variable on the stack of this thread. `call` stores there the sum that an old read kernel returns (line 842). The compiler must keep this store. So it cannot remove the adds of the old read kernel. Each thread has its own `sink`. So the threads do not all store to one shared cache line. |
| 978 | `    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */` | Comment: the store value is known only when the program runs, and its 8 bytes are not all equal. So the compiler cannot turn the store loop into a call of `memset`, the library function that fills memory with one byte value. |
| 979 | `    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;` | `v`: the value that `k_write` stores into the 8-byte words of a buffer at the first touch (line 988). It is the process id (`getpid`) plus the thread index plus 1, times a fixed 64-bit constant. The timed loop gives `v` plus a counter to a write kernel (line 1037, line 1051). The read kernels do not use `v`. |
| 980 | `    uint64_t k = 0; /* intervals this thread has run (--stop common) */` | `k`: the number of timed intervals that this thread has started. Line 1019 compares it with the shared counter `gen`. The comment says that `--stop common` uses it. |
| 981 | `    int64_t min_ns = (int64_t)(cfg.min_s * 1e9);` | `min_ns`: the `--min-ms` value in ns. Only the loop of `--stop pass` uses it (line 1057). |
| 983 | `    if (cfg.ncpus)` | Tests whether a CPU list was given (`--cpus`). |
| 984 | `        pin_cpu(t->cpu);` | CPU pinning. The thread pins itself to its CPU with `pin_cpu` (line 326). `main` chose the CPU in line 1243. Every later line of the worker runs on that CPU. Without `--cpus` the thread is not pinned. |
| 985 | `    if (cfg.count)` | Tests whether counting is on (`--count`). |
| 986 | `        open_counters(t);` | The thread opens its counters with `open_counters` (line 924). The counters count from this moment on. So they also count during the first touch and the warm-up passes. A C row holds only the change between the two readings of one interval (line 1027, line 1061). |
| 987 | `    t->a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 345) maps buffer `a` of this thread. The buffer starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. `alloc_buf` also asks Linux for 2 MiB pages for it (with `--no-thp`: for no such pages). Each thread has its own buffer and reads only its own buffer. |
| 988 | `    k_write(t->a, cfg.bytes / 8, v); /* first touch by this thread */` | First touch. `k_write` (line 442) stores `v` into `cfg.bytes / 8` words of 8 bytes, from the start of the buffer: every word of the `--bytes` range. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 339). Then the worker does not write the rest. No kernel call reaches the rest: the size of a `--seq` entry is at most `--bytes` (line 1223). The pinned thread does this write itself, before any read. Linux assigns the memory pages at this first write. This line is not timed. The comment says: first touch by this thread. |
| 989 | `    if (cfg.two_buffers) {` | Tests whether the thread needs a second buffer `b`. It exists only with `--two-buffers` or with a copy kernel in `--seq` (lines 1228 to 1229). |
| 990 | `        t->b = alloc_buf();` | Maps buffer `b` in the same way as buffer `a`. |
| 991 | `        k_write(t->b, cfg.bytes / 8, v);` | First touch of buffer `b`: the same write as in line 988. It is not timed. |
| 992 | `    }` | Ends the `if` of line 989. |
| 993 | `    if (cfg.threads > 1) {` | Tests whether the process has more than one worker. Only then the two barrier waits of lines 994 to 995 exist. The barrier releases its waiting threads when all workers and the main thread have called it (line 1237). |
| 994 | `        pthread_barrier_wait(&bar); /* the buffers exist: main() reads the first page state */` | First wait at the barrier. It returns when all workers have mapped and written their buffers and `main` has arrived in line 1277. Then `main` copies the buffer addresses and reads the page state for the P rows with position -1. The comment says: the buffers exist, and `main` reads the first page state. |
| 995 | `        pthread_barrier_wait(&bar); /* main() has read it */` | Second wait at the barrier. The worker blocks until that reading is done. `main` releases the workers in line 1346. The comment says: `main` has read it. |
| 996 | `    }` | Ends the `if` of line 993. |

### Function `worker`: one interval, from the warm-up pass to the clock read `t0` (lines 998 to 1031)

| Line | Source | Explanation |
|---:|---|---|
| 998 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds. `--rounds N` runs the `--seq` list N times, and the rounds count from 0. |
| 999 | `        for (int pos = 0; pos < cfg.nseq; pos++) {` | Loop over the positions of the `--seq` list. One pass of this loop is one timed interval. `main` runs the same two loops (lines 1271 to 1272). |
| 1000 | `            const struct kdef *kd = &kernels[cfg.seq[pos].k];` | `kd`: the entry of the kernel table for this position: name, type and function pointer (line 816). The kernels run in the order of the `--seq` list. |
| 1001 | `            size_t size = cfg.seq[pos].bytes;` | `size`: the number of bytes of this position. It is the size after `@` in the `--seq` entry, or the `--bytes` value for an entry without `@` (line 1222). |
| 1002 | `            size_t nchunk = size / HUGE_BYTES;` | `nchunk`: the number of whole 2 MiB pieces in `size`. It is 128 for a size of 256 MiB. Only the start offset of line 1004 uses it. |
| 1003 | `            /* --start offset (handoff B.5): thread i starts at (i * 37 mod n) * 2 MiB */` | Comment: with `--start offset` thread i starts at the 2 MiB piece with the number i times 37 modulo n. Here n is `nchunk`. The comment names section B.5 of the file `handoff.md`, the specification of the first runner. |
| 1004 | `            size_t off = cfg.start_offset && nchunk ? ((size_t)t->idx * 37 % nchunk) * HUGE_BYTES : 0;` | `off`: the byte offset in the buffer at which this thread starts its timed work. With `--start common` it is 0. It is also 0 for a size below 2 MiB. With `--start offset` it is `idx * 37 % nchunk` times 2 MiB. So most threads start at a place of their buffer other than byte 0. Thread 0 starts at byte 0, and with one piece (`nchunk` is 1) every thread does. |
| 1005 | `            uint64_t per_byte = kd->type == T_COPY ? 2 : 1; /* copy counts read+write bytes */` | `per_byte`: 2 for a copy kernel, 1 for every other kernel. A copy kernel counts every byte two times: once read, once written. |
| 1006 | `            uint64_t bytes = 0, p = 0;` | `bytes`: the byte count of the timed interval. `p`: the number of kernel calls of the interval with `--stop common`, or of passes with `--stop pass`. Both start at 0. |
| 1007 | `            int64_t sched = 0, deadline = 0, t0, t1;` | Clock values in ns: `sched` (the common start time), `deadline`, `t0` (the start of the timed interval) and `t1` (the clock read after the latest kernel work). |
| 1008 | `            struct result r;` | `r`: the result record of this thread for this interval (line 207). |
| 1009 | `            memset(&r, 0, sizeof r);` | `memset` sets every field of `r` to 0. |
| 1011 | `            call(kd, t, 0, size, v, &sink); /* warm-up */` | Warm-up pass, not timed. One call of the kernel of this position over the range from byte 0 to `size`, through `call` (line 833). So before every timed interval the thread has run the same kernel once over the whole range. Between this pass and the timed interval lie the barrier wait, the wait for the common start and the first counter reading (lines 1017 to 1029). In a process with one thread the page-state reading of lines 1012 to 1016 also lies between them. |
| 1012 | `            if (cfg.threads == 1) {` | Tests whether the process has one worker only. Only such a process reads the page state here, in the worker: after the warm-up pass and before the barrier. |
| 1013 | `                uint64_t *buf[2] = { t->a, t->b };` | `buf`: the addresses of the two buffers of the thread. `t->b` is NULL when the thread has no second buffer. |
| 1014 | `                read_smaps(r.pg, buf, 2);` | `read_smaps` (line 857) reads the page state of both buffers into `r.pg`. It skips a NULL entry. |
| 1015 | `                read_vmstat(r.vm);` | `read_vmstat` (line 887) reads the four counters of `/proc/vmstat` into `r.vm`. `main` prints both readings as P rows after the interval (lines 1304 to 1308). |
| 1016 | `            }` | Ends the `if` of line 1012. |
| 1017 | `            pthread_barrier_wait(&bar);` | Barrier wait after the warm-up pass. The thread blocks until all workers have ended their warm-up pass and `main` has arrived in line 1289. Then all of these threads continue. A thread whose warm-up pass ends early waits here and reads no memory. |
| 1018 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Only then lines 1019 to 1024 run. |
| 1019 | `                while (atomic_load(&gen) != k + 1)` | Common start, step 1. The thread repeats an empty loop until the shared counter `gen` equals `k + 1`. `main` adds 1 to `gen` in line 1294, after it has stored the start time and the deadline of this interval. In this loop the thread stays on its CPU and does not sleep. |
| 1020 | `                    ;` | The empty body of the loop of line 1019. |
| 1021 | `                sched = atomic_load(&t_sched_ns);` | Copies the common start time into `sched`. `main` computed it in line 1291: its clock reading plus 2 ms (`LEAD_NS`). All workers read the same value. |
| 1022 | `                deadline = atomic_load(&deadline_ns);` | Copies the common deadline into `deadline`. `main` computed it in line 1293: the start time plus the `--min-ms` value. All workers read the same value. |
| 1023 | `                while (now_ns() < sched)` | Common start, step 2. The thread reads the clock again and again until the clock reaches `sched`. It leaves the loop at its first clock read at or after the start time. This wait is not timed. |
| 1024 | `                    ;` | The empty body of the loop of line 1023. |
| 1025 | `            }` | Ends the `if` of line 1018. |
| 1026 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). |
| 1027 | `                read_group(t, &r.c0);` | First counter reading (`read_group`, line 959). It goes into `r.c0`. With `--stop common` it runs after the wait for the common start. With `--stop pass` it runs directly after the barrier. In both cases it runs before the clock read of line 1030. So it is not inside the timed interval. But `t0` is later than the common start time by at least the duration of this line and of line 1028. |
| 1028 | `                r.c0.cpu_ns = cpu_ns();` | Reads the thread CPU time (`cpu_ns`, line 951) into `r.c0`. |
| 1029 | `            }` | Ends the `if` of line 1026. |
| 1030 | `            t0 = now_ns();` | Start of the timed interval. The thread reads the clock (`now_ns`, line 238) into `t0`. Each thread has its own `t0`. Nothing above this line is inside the timed interval. |
| 1031 | `            k++;` | Counts this interval. At the next interval line 1019 waits for the next value of `gen`. This line runs after the clock read `t0`, so it is the first statement inside the timed interval. |

### Function `worker`: the timed loop and the two stop rules (lines 1032 to 1058)

| Line | Source | Explanation |
|---:|---|---|
| 1032 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Lines 1035 to 1043 are the timed loop of this stop rule. |
| 1033 | `                /* chunks of 2 MiB (or the whole entry if it is smaller); the` | Comment: the kernel runs on chunks of 2 MiB, or on the whole entry when the entry is smaller than 2 MiB. The sentence goes on in line 1034. |
| 1034 | `                 * position continues from chunk to chunk and wraps */` | Comment: the position in the buffer goes on from chunk to chunk. At the end of the entry it returns to the start. |
| 1035 | `                size_t chunk = size < CHUNK_BYTES ? size : CHUNK_BYTES, at = off;` | `chunk`: the number of bytes of one kernel call: 2097152 bytes (2 MiB, `CHUNK_BYTES`), or `size` when `size` is smaller. `at`: the byte offset of the next chunk in the buffer. It starts at `off` (line 1004). |
| 1036 | `                do {` | Starts the timed loop. Its body runs at least once. |
| 1037 | `                    call(kd, t, at, chunk, v + p++, &sink);` | Timed kernel call. `call` (line 833) runs the kernel on the chunk at byte offset `at`. The kernel gets the address of the chunk and its length in 8-byte words: 262144 words for a chunk of 2 MiB. So the kernel function is entered once per chunk: 128 times per pass over a buffer of 256 MiB. For a kernel of the type `T_OLDREAD`, `call` stores the returned sum in `sink` after each call. A kernel of the type `T_READ` returns nothing. `v + p++` gives a write kernel a new value in every call and counts the calls. A read kernel does not get this argument. |
| 1038 | `                    bytes += per_byte * chunk;` | Bytes counted. Each finished call adds `per_byte * chunk`: 2097152 bytes for a 2 MiB chunk of a read kernel. This is the size of the range that was passed to the kernel. Nothing is counted inside a kernel. So the number is the same for every read kernel. |
| 1039 | `                    at += chunk;` | Moves `at` to the next chunk. |
| 1040 | `                    if (at == size)` | Tests whether `at` has reached the end of the entry. |
| 1041 | `                        at = 0;` | After the last chunk the offset returns to 0. For a size of 256 MiB this is after chunk 127. So the kernel calls go from the start offset `off` to the end of the range. Then they repeat the whole range from byte 0, until the interval ends. With `--start common` the offset `off` is 0, and the first pass is also a whole pass. |
| 1042 | `                    t1 = now_ns();` | Clock read after every chunk: `t1` is the clock value after this call. The last `t1` is the end of the timed interval. So the timed interval is the code from line 1030 to this line: the kernel calls, the byte count, the step of the offset and one clock read per chunk. |
| 1043 | `                } while (t1 < deadline);` | Stop rule of `--stop common`. The loop repeats while `t1` is before the common deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted. The deadline is the same for all threads. Each thread has its own end time `t1`. |
| 1044 | `            } else {` | The branch of `--stop pass`. Lines 1046 to 1057 are the timed loop of this stop rule. |
| 1045 | `                /* whole passes; with an offset a pass is [off, size) then [0, off) */` | Comment: the thread runs whole passes. With a start offset one pass is the range from `off` to the end of the entry and then the range from 0 to `off`. |
| 1046 | `                uint64_t passes_per_check = CHECK_BYTES / size;` | `passes_per_check`: the number of passes between two clock reads. It is 8 MiB (`CHECK_BYTES`) divided by `size`, rounded down. So for a size below 8 MiB that does not divide 8 MiB, the clock is read after less than 8 MiB. |
| 1047 | `                if (passes_per_check == 0)` | Tests whether the division gave 0. That is the case for every size above 8 MiB. |
| 1048 | `                    passes_per_check = 1;` | The value is then 1: the thread reads the clock after every pass. |
| 1049 | `                do {` | Starts the timed loop of `--stop pass`. Its body runs at least once. |
| 1050 | `                    for (uint64_t c = 0; c < passes_per_check; c++, p++) {` | Runs `passes_per_check` passes without a clock read between them. `p` counts the passes. |
| 1051 | `                        call(kd, t, off, size - off, v + p, &sink);` | Timed kernel call: the range from `off` to the end of the entry. With an `off` of 0 this is the whole entry. `v + p` gives a write kernel a new value in every pass. |
| 1052 | `                        if (off)` | Tests whether the thread has a start offset above 0. |
| 1053 | `                            call(kd, t, 0, off, v + p, &sink);` | Second kernel call of the pass: the range from byte 0 to `off`. So each pass covers every byte of the entry once. |
| 1054 | `                        bytes += per_byte * size;` | Bytes counted: each pass adds `per_byte * size`. This is the size of the entry, or twice the size for a copy kernel. Nothing is counted inside a kernel. |
| 1055 | `                    }` | Ends the `for` of line 1050. |
| 1056 | `                    t1 = now_ns();` | Clock read after the passes: `t1`. The clock is never read inside a pass. The last `t1` is the end of the timed interval. So with this stop rule the timed interval is the code from line 1030 to this line. |
| 1057 | `                } while (t1 - t0 < min_ns);` | Stop rule of `--stop pass`. The loop repeats while less than `min_ns` (the `--min-ms` value) has passed after the `t0` of this thread. So a thread stops only at the end of a whole pass, after a full group of `passes_per_check` passes. The threads stop at different times. |
| 1058 | `            }` | Ends the `if` and `else` of line 1032. |

### Function `worker`: after the timed interval, the result record and the barrier waits (lines 1059 to 1078)

| Line | Source | Explanation |
|---:|---|---|
| 1059 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). The timed interval has ended at the last clock read `t1` (line 1042 or line 1056). |
| 1060 | `                r.c1.cpu_ns = cpu_ns();` | Reads the thread CPU time into `r.c1` (`cpu_ns`). |
| 1061 | `                read_group(t, &r.c1);` | Second counter reading, into `r.c1` (`read_group`). The order is the reverse of lines 1027 to 1028. So the timed interval lies between the two readings of the thread CPU time, and these lie between the two counter readings. The counter values of a C row therefore cover the timed interval plus a few calls around it: the two readings of the thread CPU time and the clock read `t0`. |
| 1062 | `            }` | Ends the `if` of line 1059. |
| 1063 | `            r.bytes = bytes;` | Stores the byte count of the interval in the result record. |
| 1064 | `            r.t_start = t0;` | Stores `t0`, the start of the timed interval. |
| 1065 | `            r.t_end = t1;` | Stores the last `t1`, the end of the timed interval. `main` computes the elapsed time of a thread as `t_end - t_start` (line 1301, line 1314). |
| 1066 | `            r.t_sched = cfg.stop_common ? sched : t0;` | Stores the common start time. `main` prints it in the T row as `t_sched_s` (line 1315). With `--stop pass` there is no common start time, and the field gets `t0`. |
| 1067 | `            r.late = cfg.stop_common && t0 - sched > LATE_NS;` | Late flag. With `--stop common` it is set when `t0` is more than 100000 ns (100 us, `LATE_NS`) after the common start time. `main` then prints `late` in the last column of the T row (line 1316). The program does nothing else with the flag: the interval runs, and its bytes are counted. |
| 1068 | `            t->res = r;` | Copies the record into the thread structure. `main` reads it there after the barrier wait of line 1069. |
| 1069 | `            pthread_barrier_wait(&bar);` | Barrier wait at the end of the interval. The thread blocks until all workers have ended their interval and `main` waits in line 1296. A thread that has stopped reads no memory while other threads finish their last chunk or pass. |
| 1070 | `            /* main() reads the page state of all buffers. The warm-up pass of` | Comment: `main` reads the page state of all buffers at this point. The sentence about the next warm-up pass starts here. |
| 1071 | `             * the next interval starts only after that reading (handoff B.6). */` | Comment: the warm-up pass of the next interval starts only after that reading. The comment names section B.6 of the file `handoff.md`, the specification of the first runner. |
| 1072 | `            if (cfg.threads > 1)` | Tests whether the process has more than one worker. Only then the second barrier wait exists. |
| 1073 | `                pthread_barrier_wait(&bar);` | Second barrier wait at the end of the interval. While the workers block here, `main` prints the I, T and C rows of the interval and reads the page state of all buffers (lines 1298 to 1345). `main` releases the workers in line 1346. Then each worker starts the warm-up pass of the next interval. `main` prints the P rows and the `# page_read` line after the release (lines 1347 to 1350). So this output can run while the workers do their warm-up pass. The output ends before the next timed interval starts: the barrier of line 1017 lets the workers pass only when `main` has finished the output and waits in line 1289. |
| 1074 | `        }` | Ends the loop over the positions (line 999). The worker calls no sleep function. So between two intervals lie only the waits, the readings and the warm-up pass of the rows above. |
| 1075 | `    }` | Ends the loop over the rounds (line 998). |
| 1076 | `    return NULL;` | After the last interval of the last round the thread returns. `main` waits for the end of all threads in line 1356. |
| 1077 | `}` | Ends the function `worker`. |

### Function `usage`: option summary, then exit status 2 (lines 1079 to 1091)

| Line | Source | Explanation |
|---:|---|---|
| 1079 | `static void usage(void)` | Starts the function `usage`. It prints the option summary to stderr and ends the program with exit status 2. `main` calls it for an argument that it does not accept and for settings that fail one of its checks (lines 1201 to 1227), for example `--threads` without `--cpus`. |
| 1080 | `{` | Opens the body of `usage`. |
| 1081 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to stderr. Its text stands in lines 1082 to 1088. |
| 1082 | `            "usage: bwx --seq LIST [--threads T --cpus LIST] [--bytes B] [--min-ms MS] [--no-thp]\n"` | Text of the message: the first usage line, with the options `--seq`, `--threads`, `--cpus`, `--bytes`, `--min-ms` and `--no-thp`. The text names the program `bwx`, the name of the first version of the runner. |
| 1083 | `            "           [--rounds N] [--stop pass\|common] [--start common\|offset] [--two-buffers]\n"` | Text of the message: the options `--rounds`, `--stop`, `--start` and `--two-buffers`. |
| 1084 | `            "           [--count --pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options of the counters (`--count`, `--pmu-type`, `--events`), and the two environment variables that can give the counter settings in their place (lines 1208 to 1214). |
| 1085 | `            "       bwx --selftest \| --list\n"` | Text of the message: the second form of the command, with `--selftest` or `--list`. |
| 1086 | `            "  --seq: comma-separated entries KERNEL or KERNEL@SIZE; --list prints the kernel names\n"` | Text of the message: an entry of `--seq` is a kernel name, or a kernel name with `@` and a size. `--list` prints the kernel names. |
| 1087 | `            "  sizes must be multiples of 256; with --stop common: multiples of 2M, or below 2M\n"` | Text of the message: a size must be a multiple of 256. With `--stop common` it must be a multiple of 2M or below 2M (lines 1223 to 1224). |
| 1088 | `            "  --pmu-type and CODE: the perf_event_attr fields type and config of the core PMU (CODE may be 0x..)\n");` | Text of the message: `--pmu-type` and the code of an event go into the fields `type` and `config` of the structure `perf_event_attr` (line 931, line 933). A code may be written in hexadecimal with `0x`. This line ends the `fprintf` call. |
| 1089 | `    exit(2);` | Ends the program with exit status 2. |
| 1090 | `}` | Ends the function `usage`. |

### Function `parse_seq`: read the `--seq` list (lines 1092 to 1110)

| Line | Source | Explanation |
|---:|---|---|
| 1092 | `static void parse_seq(char *list)` | Starts the function `parse_seq`. It turns the text after `--seq` into the entries of `cfg.seq`. `main` calls it in line 1182. |
| 1093 | `{` | Opens the body of `parse_seq`. |
| 1094 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. Each pass of the loop handles one entry, in the order of the list. This order is the order in which the kernels run in each round. |
| 1095 | `        char *at = strchr(tok, '@');` | `at`: the place of an `@` in the entry, or NULL when the entry has none. An entry may have the form `KERNEL@SIZE`. |
| 1096 | `        int k = 0;` | `k`: the index into the kernel table. The search of line 1099 starts at entry 0. |
| 1097 | `        if (at)` | Tests whether the entry has an `@`. |
| 1098 | `            *at = '\0';` | Ends the name at the `@`: a zero byte replaces the `@`. |
| 1099 | `        while (k < K_COUNT && strcmp(tok, kernels[k].name))` | Searches the kernel table `kernels[]` (line 816) for the name, from the first entry on. `strcmp` returns 0 when two texts are equal. The loop stops at the entry with this name. When no entry has the name, it stops with `k` equal to `K_COUNT`, the number of entries. |
| 1100 | `            k++;` | The body of the search loop: goes on to the next entry of the table. |
| 1101 | `        if (k == K_COUNT \|\| cfg.nseq == MAX_SEQ) {` | Tests for two defects: the name is not in the table, or `cfg.seq` already holds 64 entries (`MAX_SEQ`). |
| 1102 | `            fprintf(stderr, "bad --seq entry: %s\n", tok);` | Prints `bad --seq entry:` and the name to stderr. |
| 1103 | `            exit(2);` | Ends the program with exit status 2. |
| 1104 | `        }` | Ends the `if` of line 1101. |
| 1105 | `        cfg.seq[cfg.nseq].k = k;` | Stores the index of the kernel in the next free entry of `cfg.seq`. |
| 1106 | `        cfg.seq[cfg.nseq].bytes = at ? parse_bytes(at + 1) : 0;` | Stores the size of the entry: the text after the `@`, read by `parse_bytes` (line 245). An entry without `@` gets the size 0 here. `main` later replaces 0 by the `--bytes` value (line 1222). |
| 1107 | `        cfg.nseq++;` | Counts the entry. |
| 1108 | `    }` | Ends the loop of line 1094. |
| 1109 | `}` | Ends the function `parse_seq`. |

### Function `parse_events`: read the `--events` list (lines 1111 to 1136)

| Line | Source | Explanation |
|---:|---|---|
| 1111 | `/* "NAME=CODE,..." or "CODE,...". A code without a name gets the name of its` | Comment: the list has the form `NAME=CODE,...` or `CODE,...`. The sentence about a code without a name starts here. |
| 1112 | ` * position in the list of handoff B.8. */` | Comment: a code without a name gets the name of its place in the event list of section B.8 of the file `handoff.md`, the specification of the first runner. The code has one more rule that the comment does not name: from the sixth place on the name is `ev` plus the place number (lines 1126 to 1127). |
| 1113 | `static void parse_events(char *list)` | Starts the function `parse_events`. It turns the text of an event list into the names `cfg.ev_name` and the codes `cfg.ev_code`. `main` calls it with the text after `--events` (line 1196), and with the text of the environment variable `BWX_EVENTS` (line 1212). |
| 1114 | `{` | Opens the body of `parse_events`. |
| 1115 | `    static const char *by_pos[5] = { "cycles", "instructions", "l1d_refill", "l2d_refill", "ll_miss_rd" };` | `by_pos`: the names for an entry without a name at one of the first 5 places of the list: `cycles`, `instructions`, `l1d_refill`, `l2d_refill` and `ll_miss_rd`. |
| 1116 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. One pass of the loop handles one entry. |
| 1117 | `        char *eq = strchr(tok, '='), *code = eq ? eq + 1 : tok, *end;` | `eq`: the place of the `=` sign in the entry, or NULL. `code`: the text of the code. It is the text after the `=`, or the whole entry when the entry has no `=`. `end` is used in line 1128. |
| 1118 | `        if (eq == tok \|\| cfg.nev == MAX_EV \|\| (eq && (size_t)(eq - tok) >= sizeof cfg.ev_name[0])) {` | Tests for three defects: an entry with an empty name (the `=` is its first character), a 9th entry (`MAX_EV` is 8), and a name of 32 characters or more (the size of one entry of `cfg.ev_name`). |
| 1119 | `            fprintf(stderr, "bad --events entry: %s\n", tok);` | Prints `bad --events entry:` and the entry to stderr. |
| 1120 | `            exit(2);` | Ends the program with exit status 2. |
| 1121 | `        }` | Ends the `if` of line 1118. |
| 1122 | `        if (eq)` | Tests whether the entry has a name. |
| 1123 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "%.*s", (int)(eq - tok), tok);` | Copies the text before the `=` as the name of the event. The format `%.*s` prints only the first `eq - tok` characters of the entry. The program uses the name as a column title in the header line of the C rows (line 1263) and in the error message of `open_counters` (line 940). |
| 1124 | `        else if (cfg.nev < 5)` | The case of an entry without a name at one of the first 5 places of the list. |
| 1125 | `            strcpy(cfg.ev_name[cfg.nev], by_pos[cfg.nev]);` | The entry gets the name of `by_pos` for its place. |
| 1126 | `        else` | The case of an entry without a name at place 6 or later. |
| 1127 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "ev%d", cfg.nev);` | The entry gets the name `ev` plus its place number counted from 0, for example `ev5`. |
| 1128 | `        cfg.ev_code[cfg.nev] = strtoull(code, &end, 0);` | `strtoull` with base 0 turns the code text into a number. With base 0 a text that starts with `0x` is read as hexadecimal. |
| 1129 | `        if (end == code \|\| *end != '\0') {` | Tests whether the text is not a whole number: no digit was read, or other text follows the number. |
| 1130 | `            fprintf(stderr, "bad --events code: %s\n", code);` | Prints `bad --events code:` and the code text to stderr. |
| 1131 | `            exit(2);` | Ends the program with exit status 2. |
| 1132 | `        }` | Ends the `if` of line 1129. |
| 1133 | `        cfg.nev++;` | Counts the entry. |
| 1134 | `    }` | Ends the loop of line 1116. |
| 1135 | `}` | Ends the function `parse_events`. |

### The include of the self-test file (lines 1137 to 1138)

| Line | Source | Explanation |
|---:|---|---|
| 1137 | `#include "bwx_selftest.c"` | Includes the file `bwx_selftest.c`. It defines the function `selftest`. `main` calls that function only for the option `--selftest` (line 1152). |

### Function `main`: the start of the program (lines 1139 to 1147)

| Line | Source | Explanation |
|---:|---|---|
| 1139 | `int main(int argc, char **argv)` | Starts the function `main`, the entry point of the program. It reads the arguments, starts the workers, sets the common start of each interval and prints all rows. |
| 1140 | `{` | Opens the body of `main`. |
| 1141 | `    int threads_given = 0;` | `threads_given`: becomes 1 when `--threads` is given (line 1165). The check of line 1201 uses it. |
| 1142 | `    char seq_text[1024] = "";` | `seq_text`: will hold a copy of the `--seq` text for the second header line of the output (line 1255). It has room for 1023 characters. |
| 1143 | `    t_base_ns = now_ns();` | Process start time: one reading of the Linux clock `CLOCK_MONOTONIC` through `now_ns` (line 238), in ns. The T rows print the common start, `t0` and `t1` of each thread as seconds after this time (lines 1315 to 1316). |
| 1144 | `    page_bytes = sysconf(_SC_PAGESIZE);` | `page_bytes`: the size of one small memory page in bytes, as Linux reports it (`sysconf`). `alloc_buf` (line 345) uses it when it places a buffer inside its mapping. |
| 1145 | `    cfg.bytes = 1UL << 20;` | `cfg.bytes` gets its default here: 1 MiB (1048576 bytes). The option `--bytes` replaces it (line 1169). |
| 1146 | `    restrict_cpus();` | `restrict_cpus` (line 279) removes every CPU above `MAX_USE_CPU` from the allowed CPU set of the process. `MAX_USE_CPU` is 119 unless the build sets another value (line 50). The CRB build of `bwx.c` set no other value [Ref2]. |

### Function `main`: reading the arguments (lines 1148 to 1200)

| Line | Source | Explanation |
|---:|---|---|
| 1148 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 1149 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 1150 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value is accepted only when `more` is 1, and `argv[++i]` then takes the value. |
| 1151 | `        if (!strcmp(a, "--selftest")) {` | Tests for `--selftest`. |
| 1152 | `            return selftest();` | `--selftest` runs the self-test (the function `selftest` of the included self-test file) and ends the program with its result. |
| 1153 | `        } else if (!strcmp(a, "--list")) {` | Tests for `--list`. |
| 1154 | `            for (int k = 0; k < K_COUNT; k++)` | Loop over the kernel table. |
| 1155 | `                printf("%s\n", kernels[k].name);` | `--list` prints the name of every kernel of the table, one per line. |
| 1156 | `            return 0;` | Then the program ends with exit status 0. |
| 1157 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 1158 | `            cfg.use_thp = 0;` | `--no-thp` sets `cfg.use_thp` to 0. Then `alloc_buf` asks Linux for no 2 MiB pages. |
| 1159 | `        } else if (!strcmp(a, "--two-buffers")) {` | Tests for `--two-buffers`. |
| 1160 | `            cfg.two_buffers = 1;` | `--two-buffers` sets `cfg.two_buffers` to 1. Then every thread gets a second buffer `b`, also without a copy kernel (line 989). |
| 1161 | `        } else if (!strcmp(a, "--count")) {` | Tests for `--count`. |
| 1162 | `            cfg.count = 1;` | `--count` sets `cfg.count` to 1. Then each worker opens its counter group and reads it before and after every timed interval. `main` prints the C rows from these readings. |
| 1163 | `        } else if (!strcmp(a, "--threads") && more) {` | Tests for `--threads` with a value after it. |
| 1164 | `            cfg.threads = (int)parse_long(argv[++i], "--threads", 1, 4096);` | The number of worker threads. `parse_long` (line 264) accepts a whole number from 1 to 4096. |
| 1165 | `            threads_given = 1;` | Notes that `--threads` was given. |
| 1166 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 1167 | `            parse_cpus(argv[++i]);` | `parse_cpus` (line 299) appends the CPUs of each range of the list to `cfg.cpus`, in the order of the text. `cfg.ncpus` counts them. |
| 1168 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 1169 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size of each thread, read by `parse_bytes` (line 245). That function reads the letter `M` as 2 to the power 20. |
| 1170 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Tests for `--min-ms` with a value after it. |
| 1171 | `            char *end;` | `end`: will point to the first character that `strtod` did not read. |
| 1172 | `            double ms = strtod(argv[++i], &end);` | `strtod` reads the value as a decimal number of milliseconds. A fraction is allowed. |
| 1173 | `            if (end == argv[i] \|\| *end != '\0' \|\| !(ms > 0) \|\| ms > 3.6e6) {` | Tests for a bad value: no number, other text after the number, a value that is not above 0, or a value above 3.6e6 ms (1 hour). |
| 1174 | `                fprintf(stderr, "bad --min-ms: '%s' (a number of milliseconds above 0 is needed)\n", argv[i]);` | Prints a message with the bad value to stderr. |
| 1175 | `                exit(2);` | Ends the program with exit status 2. |
| 1176 | `            }` | Ends the `if` of line 1173. |
| 1177 | `            cfg.min_s = ms / 1000.0;` | `cfg.min_s`: the value in seconds. With `--stop common` it is the time from the common start to the deadline (line 1293). With `--stop pass` it is the least duration of an interval (line 1057). |
| 1178 | `        } else if (!strcmp(a, "--rounds") && more) {` | Tests for `--rounds` with a value after it. |
| 1179 | `            cfg.rounds = (int)parse_long(argv[++i], "--rounds", 1, 1000000);` | The number of rounds, a whole number from 1 to 1000000. The program runs the `--seq` list that many times. |
| 1180 | `        } else if (!strcmp(a, "--seq") && more) {` | Tests for `--seq` with a value after it. |
| 1181 | `            snprintf(seq_text, sizeof seq_text, "%s", argv[++i]);` | Copies the text of the list to `seq_text`, for the second header line (line 1255). The copy is made first: `parse_seq` changes the argument text. |
| 1182 | `            parse_seq(argv[i]);` | `parse_seq` (line 1092) cuts the argument text itself at each comma. It looks up each name in the kernel table and appends its index to `cfg.seq`. An unknown name ends the program. `cfg.nseq` counts the entries. An entry without an `@SIZE` part keeps the size 0 until line 1222. |
| 1183 | `        } else if (!strcmp(a, "--stop") && more) {` | Tests for `--stop` with a value after it. |
| 1184 | `            const char *s = argv[++i];` | `s`: the value. |
| 1185 | `            if (strcmp(s, "pass") && strcmp(s, "common"))` | Tests whether the value is neither `pass` nor `common`. |
| 1186 | `                usage();` | Any other value prints the option summary and ends the program (`usage`, line 1079). |
| 1187 | `            cfg.stop_common = !strcmp(s, "common");` | `cfg.stop_common` becomes 1 for `common` and 0 for `pass`. With 1 all threads get one common start time and one common deadline for each interval (lines 1290 to 1295). |
| 1188 | `        } else if (!strcmp(a, "--start") && more) {` | Tests for `--start` with a value after it. |
| 1189 | `            const char *s = argv[++i];` | `s`: the value. |
| 1190 | `            if (strcmp(s, "common") && strcmp(s, "offset"))` | Tests whether the value is neither `common` nor `offset`. |
| 1191 | `                usage();` | Any other value prints the option summary and ends the program (`usage`). |
| 1192 | `            cfg.start_offset = !strcmp(s, "offset");` | `cfg.start_offset` becomes 1 for `offset` and 0 for `common`. With 0 every worker starts its timed work at byte 0 of its own buffer (line 1004). |
| 1193 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 1194 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. It goes into the field `type` of the structure `perf_event_attr` (line 931). |
| 1195 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 1196 | `            parse_events(argv[++i]);` | `parse_events` (line 1113) stores the names in `cfg.ev_name` and the codes in `cfg.ev_code`. `cfg.nev` becomes the number of events. `main` does not interpret the codes. Each worker passes them to Linux in `open_counters` (line 924). |
| 1197 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 1198 | `            usage();` | `usage` (line 1079) prints the option summary to stderr and ends the process with exit status 2. |
| 1199 | `        }` | Ends the chain of tests that starts in line 1151. |
| 1200 | `    }` | Ends the loop over the arguments (line 1148). |

### Function `main`: checks of the settings (lines 1201 to 1233)

| Line | Source | Explanation |
|---:|---|---|
| 1201 | `    if (threads_given && cfg.ncpus == 0) {` | Check: `--threads` is accepted only together with `--cpus`. The test is true when `--threads` was given and the CPU list is empty. |
| 1202 | `        fprintf(stderr, "--threads requires --cpus\n");` | Prints `--threads requires --cpus` to stderr. |
| 1203 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 1204 | `    }` | Ends the `if` of line 1201. |
| 1205 | `    if (cfg.threads < 1 \|\| cfg.rounds < 1 \|\| cfg.nseq < 1 \|\| cfg.bytes == 0 \|\| cfg.bytes % 256 != 0)` | Checks of the values: the thread count, the round count and the number of `--seq` entries are at least 1, and `--bytes` is above 0 and a multiple of 256 bytes. |
| 1206 | `        usage();` | A failed check prints the option summary and ends the program with exit status 2 (`usage`). |
| 1207 | `    /* run_bwx.sh passes the counter settings in the environment */` | Comment: the script `run_bwx.sh`, the run script of the first runner, passes the counter settings in the environment. |
| 1208 | `    if (cfg.count && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: with `--count`, without `--pmu-type`, and when the environment variable `BWX_PMU_TYPE` is set. |
| 1209 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 1210 | `    if (cfg.count && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: with `--count`, without `--events`, and when the environment variable `BWX_EVENTS` is set. |
| 1211 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 1212 | `        parse_events(copy);` | Reads the event list from the copy. |
| 1213 | `        free(copy);` | Frees the copy. |
| 1214 | `    }` | Ends the `if` of line 1210. |
| 1215 | `    if (cfg.count && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether `--count` is given and the PMU type or the events are still missing. |
| 1216 | `        fprintf(stderr, "--count requires --pmu-type and --events (or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Prints a message to stderr: `--count` requires `--pmu-type` and `--events`, or the two environment variables. |
| 1217 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 1218 | `    }` | Ends the `if` of line 1215. |
| 1219 | `    for (int s = 0; s < cfg.nseq; s++) {` | Loop over the `--seq` entries. |
| 1220 | `        struct entry *e = &cfg.seq[s];` | `e`: one entry. |
| 1221 | `        if (e->bytes == 0)` | Tests whether the entry has no size of its own (no `@SIZE` part). |
| 1222 | `            e->bytes = cfg.bytes;` | Such an entry gets the size of `--bytes`. |
| 1223 | `        if (e->bytes > cfg.bytes \|\| e->bytes % 256 != 0 \|\|` | Size check of an entry. The size must be at most `--bytes` and a multiple of 256 bytes. The check goes on in line 1224. |
| 1224 | `            (cfg.stop_common && e->bytes > CHUNK_BYTES && e->bytes % CHUNK_BYTES != 0)) {` | With `--stop common` a size above 2 MiB (`CHUNK_BYTES`) must also be a multiple of 2 MiB. With this stop rule the worker calls the kernel on chunks of 2 MiB (line 1035). A size of 256 MiB passes: 268435456 bytes is 128 times 2 MiB. |
| 1225 | `            fprintf(stderr, "bad size of --seq entry %d (%s): %lu\n", s, kernels[e->k].name, (unsigned long)e->bytes);` | A bad size prints a message to stderr: the number of the entry, the kernel name and the size. |
| 1226 | `            usage();` | Then the option summary is printed, and the program ends with exit status 2 (`usage`). |
| 1227 | `        }` | Ends the `if` of line 1223. |
| 1228 | `        if (kernels[e->k].type == T_COPY)` | Tests whether the kernel of the entry is a copy kernel (type `T_COPY`). |
| 1229 | `            cfg.two_buffers = 1;` | A copy kernel in the list sets `cfg.two_buffers` to 1. Then each thread gets a second buffer `b` (line 989). |
| 1230 | `    }` | Ends the loop over the entries (line 1219). |
| 1231 | `    if (cfg.ncpus && cfg.threads > cfg.ncpus)` | Tests whether a CPU list was given and has fewer CPUs than the process has threads. |
| 1232 | `        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);` | This only gives a warning on stderr, with both numbers. The CPU list is then used again from its start (line 1243). |

### Function `main`: thread records, barrier and start of the workers (lines 1234 to 1249)

| Line | Source | Explanation |
|---:|---|---|
| 1234 | `    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);` | `th`: one record per thread, filled with zeros by `calloc`. |
| 1235 | `    uint64_t **bufs = calloc((size_t)cfg.threads * 2, sizeof *bufs);` | `bufs`: two buffer addresses per thread, for buffer `a` and buffer `b`, filled with zeros. |
| 1236 | `    struct page *pg = calloc((size_t)cfg.threads * 2, sizeof *pg);` | `pg`: one page-state record per entry of `bufs`. |
| 1237 | `    if (!th \|\| !bufs \|\| !pg \|\| pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {` | Tests the three allocations and creates the barrier `bar` for the thread count plus 1: the workers and the main thread. |
| 1238 | `        perror("setup");` | On a failure: `perror` prints the word `setup` and the reason. |
| 1239 | `        return 2;` | On a failure: the program ends with exit status 2. |
| 1240 | `    }` | Ends the `if` of line 1237. |
| 1241 | `    for (int i = 0; i < cfg.threads; i++) {` | Loop that starts the workers. |
| 1242 | `        th[i].idx = i;` | Thread `i` gets the index `i`. |
| 1243 | `        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;` | Thread placement. Thread `i` gets the CPU `cfg.cpus[i % cfg.ncpus]`: entry `i` of the CPU list. The list is used again from its start when there are more threads than entries. Without a CPU list the value is -1, and the thread is not pinned (line 983). |
| 1244 | `        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {` | Creates the thread. It runs `worker` (line 974): it pins itself, opens its counters, maps its buffer and writes it. `main` does not wait for that here. It goes on with the header lines. The function `main` does not pin the main thread. So the main thread may run on any CPU of the allowed CPU set of the process. |
| 1245 | `            perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 1246 | `            return 2;` | The program then ends with exit status 2. |
| 1247 | `        }` | Ends the `if` of line 1244. |
| 1248 | `    }` | Ends the loop of line 1241. |

### Function `main`: the header lines of the csv file (lines 1250 to 1270)

| Line | Source | Explanation |
|---:|---|---|
| 1250 | `    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "` | Starts the `printf` call of the first header line. The line starts with `# bandwidth:`. It gives the meaning of GB (1e9 bytes) and the formula of the rate of the I rows: `aggregate_GBps` is the sum of the bytes of all threads divided by the longest elapsed time of one thread. |
| 1251 | `           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",` | Continues the text of the first header line: a copy kernel counts the bytes read plus the bytes written. Then come four settings: the thread count, the bytes per thread, `min_ms` and `thp`. |
| 1252 | `           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");` | The four values. `min_ms` is `cfg.min_s` times 1000, printed without decimals. `thp` is `madvise` when the program asks for 2 MiB pages, and `nohugepage` with `--no-thp`. It only says what the program asked for. The P rows show what the buffers got. |
| 1253 | `    printf("# bwx: seq=%s rounds=%d stop=%s start=%s two_buffers=%d count=%d kernels=%s; "` | Starts the `printf` call of the second header line. The line starts with `# bwx:`. It holds the `--seq` text, the rounds, the stop rule, the start rule, `two_buffers`, `count` and the build kind (`kernels=`). |
| 1254 | `           "round and pos count from 0; times are seconds since process start\n",` | Continues the text of the second header line: round and position count from 0, and the times are seconds after the process start. |
| 1255 | `           seq_text, cfg.rounds, cfg.stop_common ? "common" : "pass", cfg.start_offset ? "offset" : "common",` | The values: the `--seq` text, the number of rounds, `common` or `pass` for the stop rule, and `offset` or `common` for the start rule. |
| 1256 | `           cfg.two_buffers, cfg.count, STANDIN ? "STAND-IN (not AArch64: rates mean nothing)" : "aarch64");` | The values of `two_buffers`, `count` and the build kind. `STANDIN` is 0 in the AArch64 build (line 403), and the build kind is then `aarch64`. A build with stand-in kernels prints a text that starts with `STAND-IN` and says that the rates mean nothing. |
| 1257 | `    printf("# I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps\n"` | Starts the `printf` call of the third, fourth and fifth header line. This line holds the column names of the I rows (line 1309). |
| 1258 | `           "# T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags\n"` | The fourth header line: the column names of the T rows (line 1313). |
| 1259 | `           "# P,round,pos,tid,buffer,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n");` | The fifth header line: the column names of the P rows. `print_p` (line 912) prints these rows. |
| 1260 | `    if (cfg.count) {` | Tests whether counting is on (`--count`). Only then the header has a sixth line. |
| 1261 | `        printf("# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns");` | Starts the sixth header line: the first nine column names of the C rows, up to `cputime_ns`. |
| 1262 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 1263 | `            printf(",%s", cfg.ev_name[e]);` | Appends the event names in the order of `--events`, one column per event. |
| 1264 | `        printf("; pmu_type=%ld codes=", cfg.pmu_type);` | Appends the PMU type (`pmu_type=`) and the word `codes=`. |
| 1265 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 1266 | `            printf("%s0x%llx", e ? "," : "", (unsigned long long)cfg.ev_code[e]);` | Appends the event codes in hexadecimal, with commas between them. |
| 1267 | `        printf("\n");` | Ends the header line with a line break. |
| 1268 | `    }` | Ends the `if` of line 1260. |
| 1269 | `    fflush(stdout);` | `fflush` writes the header lines to the standard output now. |

### Function `main`: the loop over rounds and positions, and the common start (lines 1271 to 1297)

| Line | Source | Explanation |
|---:|---|---|
| 1271 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds, as in `worker` (line 998). |
| 1272 | `        for (int pos = -1; pos < cfg.nseq; pos++) {` | Loop over the positions. `pos` starts at -1, not at 0. Position -1 is one extra pass of the loop before the first interval. Each position from 0 up is one timed interval. `main` and the workers go through the same rounds and positions. At each barrier call below a thread waits until all workers and `main` have arrived. |
| 1273 | `            if (pos < 0 && (round > 0 \|\| cfg.threads == 1))` | Tests whether the pass with position -1 must be skipped: in every round after round 0, and in a process with one thread. |
| 1274 | `                continue;` | Skips that pass. So in a process with more than one thread it runs once, before the first interval. |
| 1275 | `            if (pos < 0) {` | The case of position -1. |
| 1276 | `                /* the workers have allocated and first touched their buffers */` | Comment: at this point the workers have allocated their buffers and have written them for the first time. |
| 1277 | `                pthread_barrier_wait(&bar);` | `main` calls the barrier. The call returns when all workers have mapped and written their buffers and wait in line 994. |
| 1278 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 1279 | `                    bufs[2 * i] = th[i].a;` | Copies the address of buffer `a` of thread `i` into entry `2 * i` of `bufs`. |
| 1280 | `                    bufs[2 * i + 1] = th[i].b;` | Copies the address of buffer `b` of thread `i` into entry `2 * i + 1`. The entry stays NULL when the thread has no second buffer. |
| 1281 | `                }` | Ends the loop of line 1278. This pass of the position loop goes on with the page-state block in line 1337. That block prints the page state before the first interval. |
| 1282 | `            } else {` | The case of a position from 0 up: one interval. |
| 1283 | `                const struct entry *e = &cfg.seq[pos];` | `e`: the `--seq` entry of this position. |
| 1284 | `                const char *name = kernels[e->k].name;` | `name`: the name of its kernel. |
| 1285 | `                double per_pass = (double)e->bytes * (kernels[e->k].type == T_COPY ? 2 : 1);` | `per_pass`: the byte count of one pass over the range of the entry: its size, or twice its size for a copy kernel. The column `passes` of the T rows uses it (line 1316). |
| 1286 | `                uint64_t total = 0;` | `total`: the sum of the byte counts of all threads. It starts at 0. |
| 1287 | `                int64_t max_el = 0;` | `max_el`: the longest elapsed time of one thread, in ns. It starts at 0. |
| 1289 | `                pthread_barrier_wait(&bar); /* release the workers */` | First barrier call of the interval. It returns when all workers have finished the warm-up pass of this kernel and wait in line 1017. The barrier then lets all of these threads continue. With `--stop common` the workers do not start the kernel yet: each worker waits in an empty loop until `gen` changes (line 1019). The comment says: release the workers. |
| 1290 | `                if (cfg.stop_common) {` | Tests for `--stop common`. Only then `main` sets a common start (lines 1291 to 1294). With `--stop pass` each worker starts its timed interval directly after the barrier. |
| 1291 | `                    int64_t sched = now_ns() + LEAD_NS;` | Common start, set by the main thread. `main` reads the clock once and adds `LEAD_NS` (2 ms, line 43). The result `sched` is the common start time of all threads. `main` is not pinned. |
| 1292 | `                    atomic_store(&t_sched_ns, sched);` | Stores `sched` in the shared variable `t_sched_ns`. The lead of 2 ms is the time that `main` has for lines 1292 to 1294 and that the workers have to see the new `gen`. A worker that sees it only after `sched` has passed starts after the common start time. When its `t0` is then more than 100 us after `sched`, the late flag shows it (line 1067). |
| 1293 | `                    atomic_store(&deadline_ns, sched + (int64_t)(cfg.min_s * 1e9));` | Stores the deadline in the shared variable `deadline_ns`: `sched` plus `cfg.min_s`. |
| 1294 | `                    atomic_fetch_add(&gen, 1);` | Only after both stores `main` adds 1 to `gen`. So a worker that sees the new `gen` reads the new start time and the new deadline. Each worker then reads the clock in a loop until `sched`, and then reads its own start time `t0` (lines 1023 to 1030). After this line `main` passes nothing more to the workers. Each worker stops by itself, at its first clock read at or after the deadline (lines 1042 to 1043). |
| 1295 | `                }` | Ends the `if` of line 1290. |
| 1296 | `                pthread_barrier_wait(&bar); /* all workers finished this interval */` | Second barrier call of the interval. `main` blocks here until all workers have stored their results and wait in line 1069. So between the change of `gen` and the end of the timed interval this call is the only code that `main` runs. It prints nothing in that time. The comment says: all workers finished this interval. |

### Function `main`: the I row, the T rows and the C rows (lines 1298 to 1336)

| Line | Source | Explanation |
|---:|---|---|
| 1298 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the results of the threads. In a process with more than one thread every worker waits at the barrier of line 1073 from here to line 1346. So no kernel runs while `main` prints the I, T and C rows. |
| 1299 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i` for this interval (line 1068). |
| 1300 | `                    total += r->bytes;` | `total` becomes the sum of the byte counts of all threads. |
| 1301 | `                    if (r->t_end - r->t_start > max_el)` | Tests whether the elapsed time of this thread, `t_end - t_start` in ns, is the longest so far. `t_start` is the `t0` of the worker, and `t_end` is its last `t1` (lines 1064 to 1065). |
| 1302 | `                        max_el = r->t_end - r->t_start;` | Keeps the longest elapsed time in `max_el`. |
| 1303 | `                }` | Ends the loop of line 1298. |
| 1304 | `                if (cfg.threads == 1) { /* read by the worker before the interval */` | The branch of a process with one thread. There the worker has read the page state itself before the interval (lines 1012 to 1016), and `main` prints it here. The comment says: read by the worker before the interval. |
| 1305 | `                    print_p(round, pos, 0, 'a', &th[0].res.pg[0], th[0].res.vm);` | Prints the P row of buffer `a` (`print_p`, line 912). |
| 1306 | `                    if (th[0].b)` | Tests whether the thread has a second buffer. |
| 1307 | `                        print_p(round, pos, 0, 'b', &th[0].res.pg[1], th[0].res.vm);` | Prints the P row of buffer `b`. It holds the same four counter values as the row of buffer `a`. |
| 1308 | `                }` | Ends the `if` of line 1304. |
| 1309 | `                printf("I,%d,%d,%s,%lu,%d,%lu,%.6f,%.2f\n", round, pos, name, (unsigned long)e->bytes, cfg.threads,` | I row, one per interval, with 9 fields: the letter `I`, round, position, kernel name, `bytes_per_thread`, thread count, `total_bytes`, `max_elapsed_s` and `aggregate_GBps`. `bytes_per_thread` is the size of the `--seq` entry. It is a setting, not a measured value. |
| 1310 | `                       (unsigned long)total, (double)max_el * 1e-9, (double)total / (double)max_el);` | Continues the call of line 1309. `total_bytes` is `total`. `max_elapsed_s` is `max_el` in seconds, with 6 decimals. `aggregate_GBps` is `total` in bytes divided by `max_el` in ns, with 2 decimals. One byte per ns is 1 GB/s with GB = 1e9 bytes. So this rate is the bytes of all threads divided by the longest elapsed time of one thread. |
| 1311 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 1312 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 1313 | `                    printf("T,%d,%d,%s,%d,%d,%lu,%.6f,%.6f,%.6f,%.6f,%.3f,%s\n", round, pos, name, i, th[i].cpu,` | T row, one per thread and interval, with 13 fields. Fields 1 to 6: the letter `T`, round, position, kernel name, thread index (`tid`) and the CPU of the thread. A thread without a CPU list shows -1. |
| 1314 | `                           (unsigned long)r->bytes, (double)(r->t_end - r->t_start) * 1e-9,` | Continues the call of line 1313. Field 7, `bytes`: the byte count of the worker (line 1038, line 1054). Field 8, `elapsed_s`: `t_end - t_start` in seconds, with 6 decimals. The rate of a thread is field 7 divided by field 8, in bytes per second. The program does not print it. |
| 1315 | `                           (double)(r->t_sched - t_base_ns) * 1e-9, (double)(r->t_start - t_base_ns) * 1e-9,` | Continues the call of line 1313. Fields 9 and 10, `t_sched_s` and `t_start_s`: the common start time and `t0`, in seconds after the process start `t_base_ns`, with 6 decimals. With `--stop pass` field 9 equals field 10 (line 1066). |
| 1316 | `                           (double)(r->t_end - t_base_ns) * 1e-9, (double)r->bytes / per_pass, r->late ? "late" : "-");` | Continues the call of line 1313. Field 11, `t_end_s`: the last `t1`, in seconds after the process start. Field 12, `passes`: `bytes / per_pass`, the number of passes over the range of the entry, with 3 decimals. Field 13, `flags`: `late` when `t0` came more than 100 us after the common start (line 1067), and `-` if not. |
| 1317 | `                }` | Ends the loop of line 1311. |
| 1318 | `                for (int i = 0; cfg.count && i < cfg.threads; i++) {` | Loop over the threads. It runs only with `--count`. It prints the C rows: one per thread and interval. |
| 1319 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 1320 | `                    printf("C,%d,%d,%s,%d,%d", round, pos, name, i, th[i].cpu);` | Starts a C row. Fields 1 to 6: the letter `C`, round, position, kernel name, thread index and CPU. |
| 1321 | `                    if (th[i].group_fd < 0)` | Tests whether the thread has no open counter group. |
| 1322 | `                        printf(",NA,NA");` | Fields 7 and 8 are then `NA`. |
| 1323 | `                    else` | The case of a thread with an open group. |
| 1324 | `                        printf(",%llu,%llu", (unsigned long long)(r->c1.enabled - r->c0.enabled),` | Fields 7 and 8, `enabled_ns` and `running_ns`: the enabled time and the running time of the counter group at the second reading minus the same values at the first reading. This line holds the enabled time. |
| 1325 | `                               (unsigned long long)(r->c1.running - r->c0.running));` | Continues the call of line 1324: the running time. |
| 1326 | `                    printf(",%llu", (unsigned long long)(r->c1.cpu_ns - r->c0.cpu_ns));` | Field 9, `cputime_ns`: the thread CPU time at the second reading minus the value at the first reading. The worker takes the first reading (`c0`) directly before `t0` and the second reading (`c1`) directly after its last `t1` (lines 1026 to 1029, lines 1059 to 1062). |
| 1327 | `                    for (int ev = 0; ev < cfg.nev; ev++) {` | Loop over the events, in the order of `--events`. |
| 1328 | `                        int at = th[i].ev_pos[ev];` | `at`: the place of the event in a group reading. It is -1 when the event did not open (line 942). |
| 1329 | `                        if (at < 0)` | Tests whether the event did not open. |
| 1330 | `                            printf(",NA");` | Its field is then `NA`. |
| 1331 | `                        else` | The case of an event that opened. |
| 1332 | `                            printf(",%llu", (unsigned long long)(r->c1.val[at] - r->c0.val[at]));` | One field per event: the count at the second reading minus the count at the first reading. |
| 1333 | `                    }` | Ends the loop over the events (line 1327). |
| 1334 | `                    printf("\n");` | Ends the row with a line break. |
| 1335 | `                }` | Ends the loop of line 1318. |
| 1336 | `            }` | Ends the `else` of line 1282. |

### Function `main`: the page state, the P rows and the end (lines 1337 to 1358)

| Line | Source | Explanation |
|---:|---|---|
| 1337 | `            if (cfg.threads > 1) {` | Page-state block. It runs only in a process with more than one thread: once at position -1 and once after every interval. At this time every worker waits at a barrier: in line 995 after position -1, in line 1073 after an interval. So no kernel runs while `main` reads the page state. |
| 1338 | `                /* Page state of all buffers, read between two intervals. It is` | Comment: the page state of all buffers is read between two intervals. The sentence goes on in line 1339. |
| 1339 | `                 * the state after interval pos (pos -1: before the first). The` | Comment: it is the state after interval `pos`. For `pos` -1 it is the state before the first interval. The sentence about the workers starts here. |
| 1340 | `                 * workers wait on the barrier below until it is read. */` | Comment: the workers wait at the barrier below (line 1346) until the state is read. |
| 1341 | `                long long vm[4];` | `vm`: will hold the four counters of `/proc/vmstat`. |
| 1342 | `                int64_t r0 = now_ns();` | `r0`: the clock value before the reading (`now_ns`, line 238). |
| 1343 | `                read_smaps(pg, bufs, 2 * cfg.threads);` | `read_smaps` (line 857) looks up each entry of `bufs` in `/proc/self/smaps` and skips the NULL entries. It stores the size of each buffer and its part on 2 MiB pages in `pg`. |
| 1344 | `                read_vmstat(vm);` | `read_vmstat` (line 887) reads the four counters of `/proc/vmstat`, once for the whole block. |
| 1345 | `                double ms = (double)(now_ns() - r0) * 1e-6;` | `ms`: the duration of both readings in ms: the clock value now minus `r0`. |
| 1346 | `                pthread_barrier_wait(&bar); /* the reading is done: the workers go on */` | Barrier call that lets the workers continue. Each worker then starts the warm-up pass of the next interval, while `main` prints the P rows below. After the last interval the workers end at this point. The comment says: the reading is done, and the workers go on. |
| 1347 | `                for (int i = 0; i < 2 * cfg.threads; i++)` | Loop over the entries of `bufs`. Entry `i` belongs to thread `i / 2`. An even `i` is buffer `a`, and an odd `i` is buffer `b`. |
| 1348 | `                    if (bufs[i])` | Skips an entry without a buffer. |
| 1349 | `                        print_p(round, pos, i / 2, i % 2 ? 'b' : 'a', &pg[i], vm);` | P row, one per existing buffer, printed by `print_p` (line 912). The fields: the letter `P`, round, position, thread index, buffer letter, size of the buffer in kB, part on 2 MiB pages in kB, then the four counters of `/proc/vmstat`. The position is that of the interval before the reading, or -1 for the reading before the first interval. All rows of one block carry the same four counter values: they count for the whole system and were read once (line 1344). |
| 1350 | `                printf("# page_read,%d,%d,%.3f ms\n", round, pos, ms);` | Prints the line `# page_read` with the round, the position and `ms`, the duration of the page-state reading of this block, with 3 decimals and the unit `ms`. |
| 1351 | `            }` | Ends the `if` of line 1337. |
| 1352 | `            fflush(stdout);` | `fflush` writes all rows that are still in the output buffer to the standard output. Then the loops go on with the next position. A new timed interval cannot start before `main` has passed line 1289 again, and with `--stop common` also line 1294. So `main` writes no output during a timed interval. |
| 1353 | `        }` | Ends the loop over the positions (line 1272). Between two intervals lie the output of the rows, the page-state reading, the barrier calls, the warm-up pass of the next kernel and, with `--stop common`, the 2 ms lead. No code of this file calls a sleep function. |
| 1354 | `    }` | Ends the loop over the rounds (line 1271). |
| 1355 | `    for (int i = 0; i < cfg.threads; i++)` | Loop over the threads, after the last interval. |
| 1356 | `        pthread_join(th[i].tid, NULL);` | Waits for the end of worker thread `i` (`pthread_join`). |
| 1357 | `    return 0;` | Returns 0: the process ends with exit status 0. |
| 1358 | `}` | Ends the function `main`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/listing.txt`: objdump text of the 21 kernel functions of each of the four binaries of the second build on CRB, 2026-11-13: 84 sections. The sections of the binary `bwx` have headings such as `=== bwx read ===`. Source of the start addresses, the loop starts and the instruction counts. The listing of the first build (`bwx-crb-build-1/listing.txt`) holds the same text for the sections of `bwx`, `bwx_o0` and `bwx_o36`. A script compared the sections of `bwx` with the listing of `bwx8` on 2026-11-25: apart from absolute addresses, the 21 kernels have the same instruction text in both.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/build.txt`: record of the second build on CRB. The row `## cc=` names the compiler, gcc 14.2.0. The row `## CFLAGS=` gives the flags. They hold no `-D` option. The rows `## EXTRA=` and `## EXTRA_bwx=` are empty, and the row `## EXTRA_bwx_o52=` holds `-falign-loops=1`. The build script `build.sh` adds `-DB3_OFFSET=0`, `-DB3_OFFSET=36` and `-DB3_OFFSET=52` for the binaries `bwx_o0`, `bwx_o36` and `bwx_o52`, and no `-D` option for `bwx`. The block `## sha256:` gives the sha256 of `bwx.c`. It is the sha256 of the source file of this page.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/probe.txt`: objdump text of the kernels of `bw_new` (sections `=== bw_new ... ===`) and of `bw_old` (sections `=== bw_old ... ===`). Compared with the sections of `bwx` in [Ref1] by a script on 2026-11-25, with absolute code addresses and data addresses left out. `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite` and `k_asmcopy` of `bw_new` have the instruction text of the functions with the same names in `bwx`. `k_read`, `k_write` and `k_copy` of `bw_old` have the instruction text of `k_oldread`, `k_oldwrite` and `k_oldcopy` of `bwx`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the section "Parts B and C: specification v1 of `bwx`". B.1 lists the kernels and the steps B2 and B5 that they belong to. B.4 gives the two stop methods, B.5 the start offsets, B.6 the page state, B.7 the loop addresses and B.8 the counters. B.7 names the loop offset as a factor of step B3. B.8 says that counter code without user-mode counting fails without root on CRB, and that a counter is opened with `pid = 0` and `cpu = -1`. B.9 gives the sequence of each step.
- [Ref5] `/usr/include/linux/perf_event.h`: the comment above `enum perf_event_read_format` (header of the machine on which this page was written). With `PERF_FORMAT_GROUP` the data of one `read` are `nr`, `time_enabled`, `time_running` and then one value per counter.
- [Ref6] external source: Linux kernel documentation on docs.kernel.org, read on 2026-11-25. Page https://docs.kernel.org/admin-guide/mm/transhuge.html: `thp_fault_alloc` "is incremented every time a huge page is successfully allocated and charged to handle a page fault". `thp_fault_fallback` "is incremented if a page fault fails to allocate or charge a huge page and instead falls back to using small pages". `thp_collapse_alloc` "is incremented by khugepaged when it has found a range of pages to collapse into one huge page and has successfully allocated a new huge page to store the data". Page https://docs.kernel.org/mm/page_migration.html: page migration moves the physical location of pages, and for the counter of successful migrations "Each count means that a page was migrated".
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-bwx.md`: the note of the writer of `bwx.c`. Its section "Deviations" lists 24 numbered deviations from specification v1 with their reasons. Its section "Known limits" says that the main thread shares a CPU with a worker in every run with 120 threads.
- [Ref8] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/offsets.tsv` and `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-1/offsets.tsv`: one row per binary and kernel with the start address, the loop start and the loop start modulo 64. Source of the loop offsets of the binaries `bwx_o0`, `bwx_o36` and `bwx_o52`. The rows of `bwx_o52` for `copy` and `oldwrite` differ between the two files.
- [Ref9] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-1/build.txt`: record of the first build on CRB, about one minute before the second build. Its row `## EXTRA_bwx_o52=` is empty. Its block `## sha256:` gives the same sha256 as [Ref2] for `bwx.c` and for the binaries `bwx`, `bwx_o0` and `bwx_o36`, and another sha256 for `bwx_o52`.
- [Ref10] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-1/listing.txt`: objdump text of the kernel functions of the four binaries of the first build on CRB. Its section `=== bwx_o52 copy ===` holds 3 `nop` instructions between the first instruction of `k_copy` and the loop. The loop starts at `0x3b00`, which is 0 modulo 64.
