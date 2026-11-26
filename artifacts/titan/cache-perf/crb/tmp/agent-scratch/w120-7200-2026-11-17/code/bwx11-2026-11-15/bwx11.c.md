# `bwx11.c` explained, line by line

- Source file: `bwx11-2026-11-15/bwx11.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 2703 lines, 103208 bytes).
- sha256 of the source when this page was built: `a820940b50c5bd736e5eba6285a2856c15be914194434df2c1d81471b96e4c51`.

## Short version: purpose

`bwx11.c` is the source of `bwx11`, the version of the runner that the investigation into the small gain of the new read kernel at a buffer of 8 MiB used in its round 4 [Ref8]. It is `bwx10.c` plus three read kernels, the `asmread` loop with 64, 96 and 128 `nop` instructions per 256 B, and the option `--evict-mb` of the trial mode, which writes other memory before the first trial. As every runner, it times a sequence of kernels in one process and prints the bytes and the times as csv rows.

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
- **Load-only loop**: a read kernel that loads data and computes nothing with it: the new read kernel, `asmread` and the kernels that are built from the `asmread` loop.
- **nop kernels of round 4**: `read_nop64`, `read_nop96` and `read_nop128`, the three kernels that `bwx11` adds: the `asmread` loop with 64, 96 or 128 `nop` instructions after the 8 loads of each 256 B.
- **Evict step**: the step of the option `--evict-mb N` of the trial mode. Before the first trial the worker maps N MiB of other memory, writes one word to every 64 B line of it in two passes and unmaps it. The aim is that the benchmark buffer leaves the caches.
- **Stop rules of the runner**: `--stop pass` selects the whole-pass stop. `--stop common` selects the common stop.
- **Interval mode, trial mode**: the two modes of the program. The interval mode (option `--seq`) runs the number of threads that `--threads` gives and times one interval per round and kernel of the sequence. The trial mode (option `--trial`) runs one worker thread through the trials of a plan file.
- **Kernel table, `kernels[]`**: the array of lines 1051 to 1068. Each entry holds the name of a kernel (the word used in `--seq`), its type (`T_READ`, `T_WRITE`, `T_COPY` or `T_OLDREAD`) and a pointer to its function. In this version it has 29 entries.
- **`cfg`**: the structure that holds the settings from the arguments: thread count, CPU list, buffer size, kernel sequence, rounds, stop rule and counter settings (lines 231 to 249).
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
- **I, T, P, C rows**: the row kinds of the interval mode: one I row per interval, one T row per thread and interval, one P row per buffer and page-state reading, and with `--count` one C row per thread and interval with counter values.
- **Page state**: two values of a buffer from the Linux file `/proc/self/smaps`: the size of its mapping and the part of it on 2 MiB pages, both in kB of 1024 bytes.
- **PMU, PMU type, event code**: PMU means performance monitoring unit, the hardware event counters of a core. The value of `--pmu-type` and the code of an event of `--events` go into the fields `type` and `config` of the structure `perf_event_attr`. The two fields tell Linux which event to count.
- **Counter group, group leader**: the counters that one thread opens form a group. The first one is the leader. One `read` of the leader returns the values of all counters of the group.
- **Enabled time, running time**: two times of a counter group, in ns: how long the counters were enabled, and how long they really counted.
- **File descriptor**: the number that Linux returns when a program opens a file or a counter.
- **AArch64, NEON**: AArch64 is the 64-bit Arm instruction set. NEON is the vector part of it: 32 registers of 16 bytes, written `v0` to `v31`, or `q0` to `q31` when an instruction uses all 16 bytes, or `d0` to `d31` for the low 8 bytes.
- **`ldp`, `ldr`, `stp`, `nop`**: AArch64 instructions. `ldp` loads two registers from memory, `ldr` loads one, and `stp` stores two. With `q` registers these are 32 B, 16 B and 32 B. `nop` does nothing.
- **Loop pass**: one run of the loop body of a kernel. It is not a pass over the whole buffer.
- **64 B line**: a block of 64 bytes of memory, a cache line. The source comments count memory in such lines.
- **Clobber list**: the last list of a gcc `__asm__` statement. It names the registers and the other state that the assembly text changes.
- **Save of `d8` to `d15`**: the Arm calling rules say that a function must keep the registers `d8` to `d15` for its caller. A kernel whose clobber list names `v8` to `v15` stores them on the stack once at its start and loads them back once at its end.
- **`PLACE`, pad, loop offset**: `PLACE(name)` is a macro that stands before each kernel. It adds unused bytes, the pad. The kernel then starts at a chosen address modulo 64. The aim is a fixed loop offset: the address of the first instruction of the loop modulo 64.
- **`LOOP`, `HEAD`, `PAD`**: the values of the loop placement. `LOOP` is the planned loop offset of a kernel. `HEAD` is the number of bytes of code between the start of the function and the start of its loop. `PAD` is the number of zero bytes that `PLACE` adds. The macro `PADOF` computes it as `LOOP` minus `HEAD`, modulo 64.
- **Placement**: the start addresses modulo 64 of the functions from `call` to `timed_sequence_hot`. The pad after the last kernel keeps them equal to those of the versions before. The build record reports the same placement as in `bwx10`, and the same placement up to `timed_sequence` as in `bwx8` [Ref2].
- **Stand-in**: a plain C loop that replaces a NEON kernel or an assembly kernel when the file is compiled for a machine that is not AArch64. The rates of such a build mean nothing.
- **Development machine**: the machine on which the program was written and tested before the build on CRB. The stand-in kernels exist for it.
- **A/A copy**: the same kernel source under a second name, for example `asmread2`.
- **History comment, marker lines**: from `bwx10` on, each version of the runner puts a comment at the top of the file that lists its additions. Every addition of such a version stands between two comment lines, for example `bwx11+` and `bwx11-`. The additions of `bwx8` have no such lines.
- **Round 3, round 4 (in source comments)**: rounds of work on the program on 2026-11-15. They produced the versions `bwx10` and `bwx11`. They are not rounds of the option `--rounds`.
- **`handoff.md`**: the specification of the first runner `bwx`. The comments cite its sections B.4 to B.8 [Ref4].
- **Build record**: the files that the build script `build11.sh` wrote on CRB. `build.txt` holds the compiler, the flags, the placement and the sha256 values [Ref2]. `listing.txt` holds the machine-code listing of every kernel [Ref1].
- **Plan file, trial, window (trial mode)**: the plan file lists the trials of one process. A trial is a list of windows. A window runs one kernel on one range of the buffer for a fixed time.
- **Phase, target window (trial mode)**: a trial has up to four phases, in this order: previous activity (1 window), prefix (4 windows), predecessor (1 window) and target. A target window is a window of the last phase.
- **Timed sequence (trial mode)**: the run of all windows of one trial, done by the function `timed_sequence` or, with the option `--hot-copy`, by `timed_sequence_hot`.
- **Counter state (trial mode)**: the field `count` of a plan line: `closed` (no counter group is open), `open` (the group is open and is not read during the trial) or `read` (the group is read at the boundaries of the target windows).
- **Record block (trial mode)**: one memory block that holds the records of all trials: the trial records, the window records, the counter readings, the bins and, with `--trace`, the event log.
- **Bin, trace (trial mode)**: a bin is a part of a target window with a requested length of 10 ms. The trace (`--trace`) is a log of events with clock times.
- **Controlling thread (trial mode)**: the thread that runs `trial_main`. It pins itself to the CPU of `--ctl-cpu`, starts the one worker of the trial mode and waits for its end.
- **S, W, B, E, X, TR, M, K rows (trial mode)**: row kinds that only the trial mode prints: S (the plan line of a trial), W (one window), B (one bin), E (the summary of a trial), X (a problem), TR (one trace event), M (one setting or one fact of the process) and K (the address of one kernel).
- **Context switch**: Linux stops running a thread on its CPU. It is voluntary when the thread waits by itself, and involuntary when Linux takes the CPU away.
- **Minor page fault**: a page fault that Linux serves without disk access. The first touch of a page is one.

## Main flow

1. Start. `main` reads the clock once for the process start time `t_base_ns`, reads the page size and sets the default buffer size of 1 MiB. Then `restrict_cpus` removes every CPU above 119 from the allowed CPU set of the process (lines 2481 to 2488).
2. Mode choice. `main` compares every argument with the word `--trial`. When one is equal, it calls `trial_main` and returns its result. Otherwise it goes on in the interval mode, which is the rest of `main` (lines 2489 to 2491).
3. Argument parsing. One loop over the arguments fills the settings structure `cfg`: threads, CPU list, bytes per thread, interval length, rounds, the `--seq` list, the stop rule, the start rule and the counter settings. `--selftest` and `--list` end the program in this loop (lines 2493 to 2545).
4. Checks of the settings. A failed check prints the option summary and ends the program with exit status 2. Each `--seq` entry without `@SIZE` gets the size of `--bytes`, and a copy kernel in the list gives each thread a second buffer (lines 2546 to 2577).
5. Threads. `main` creates a barrier for all workers plus itself and starts one thread per worker. Thread `i` gets entry `i` of the CPU list (lines 2579 to 2593).
6. Each worker pins itself to its CPU, opens its counters when `--count` is given, maps its buffer with `alloc_buf` and writes every word of the `--bytes` range of it once with `k_write`. This write is the first touch (lines 1225 to 1234).
7. Header. `main` prints the header lines: the settings and the column names of the I, T, P and C rows (lines 2595 to 2614).
8. Only in a process with more than one thread: when all buffers exist, `main` reads the page state of all buffers and prints P rows with the position -1 (lines 2618 to 2626, lines 2682 to 2696).
9. Loops. The workers and `main` run the same two loops: the rounds, and inside a round the positions of the `--seq` list. One pair of round and position is one interval (lines 1240 to 1241, lines 2616 to 2617).
10. Warm-up pass. Each worker calls the kernel of the position once over the whole range of the entry. This call is not timed (line 1253).
11. Common start, only with `--stop common`. When all workers wait at the barrier, `main` reads the clock, sets the start time to that value plus 2 ms and the deadline to the start time plus the `--min-ms` value, and then adds 1 to `gen` (lines 2634 to 2639). Each worker waits for the new `gen` and then reads the clock in a loop until the start time (lines 1260 to 1267).
12. Start of the timed interval. With `--count` the worker first reads its counter group and its thread CPU time. Then it reads the clock: `t0` (lines 1268 to 1272).
13. Timed loop with `--stop common`. The worker calls the kernel on one chunk of 2 MiB, adds the size of the chunk to its byte count and reads the clock: `t1`. It repeats this with the next chunk until `t1` is at or after the deadline (lines 1274 to 1285).
14. Timed loop with `--stop pass`. The worker runs whole passes over the range of the entry. It reads the clock after a fixed number of passes: 8 MiB divided by the size of the entry, rounded down, and at least 1 pass. It stops when the `--min-ms` time has passed after `t0` (lines 1286 to 1300).
15. End of the interval, worker. The worker reads its thread CPU time and its counter group again. It stores the byte count, `t0`, the last `t1`, the common start time and the late flag, and it waits at the barrier (lines 1301 to 1315).
16. I row. `main` adds the bytes of all threads and takes the longest elapsed time `t1 - t0` of one thread. The last column of the I row is the total divided by that time, in GB/s (lines 2643 to 2655).
17. T rows and C rows. `main` prints one T row per thread with its bytes and its times, and with `--count` one C row per thread with the change of its counters over the interval (lines 2656 to 2680).
18. Page state, in a process with more than one thread. While the workers wait at the barrier, `main` reads the page state of all buffers. Then it releases the workers and prints the P rows and one `# page_read` line (lines 2682 to 2696). In a process with one thread the worker reads the page state itself before each interval, and `main` prints its P rows before the I row (lines 1254 to 1258, lines 2649 to 2653).
19. End. After the last interval `main` waits for the end of all threads and returns 0 (lines 2700 to 2702).

## Behavior a reader must know

- Difference to `bwx10.c`: additions only. The command `diff` shows 138 added lines in nine blocks, each between a `bwx11+` line and a `bwx11-` line: the history comment (lines 1 to 26), the three kernels with a second pad (lines 1008 to 1043), three entries of the kernel table (lines 1064 to 1066), the evict step (lines 1992 to 2032), its rows in `trial_worker` (lines 2081 to 2095), its usage text (lines 2375 to 2380), its option (lines 2411 to 2414) and the two blocks around the include of the self-test file (lines 2472 to 2474, lines 2476 to 2479).
- Difference to the next version: `bwx12.c` is this file plus 423 added lines in five blocks, for 26 more kernels, a third pad and the include of its own self-test file. Every line of this file stands in `bwx12.c`.
- The three kernels of round 4 are the `asmread` loop with 64, 96 and 128 `nop` instructions between the 8 loads and the `add` of the read address: 75, 107 and 139 instructions per 256 B against 11 in `asmread`. They read the same bytes as `asmread`, and the worker counts their bytes in the same way (lines 1029 to 1031, line 1280).
- The evict step runs only in the trial mode, only with `--evict-mb` above 0, and once per process: after the first touch of the buffer and of the record block and before the first trial (lines 2085 to 2091). It lies in no timed sequence. Its duration is printed in the M row `evict_ns`. When it fails, the process prints an X row and ends with exit status 2.
- Apart from the three kernels, the interval mode is the interval mode of `bwx10.c`: the other additions belong to the trial mode and to the include of the self-test file.
- The trial mode follows the design of the investigation: one pinned worker, and trials of prefix, predecessor and target windows [Ref7]. Between two windows lie only the store of the results of the window, the clock reads and, before a target window of a trial with the counter state `read`, one reading of the counter group and of the thread CPU time (lines 1607 to 1610, lines 1587 to 1589). With `--trace` these clock reads and this reading also store events in the trace.
- CRB build of `bwx11`. The source of this page has the sha256 that the build record gives for `bwx11.c` [Ref2]. In the listing the loops of the three new kernels start at 20 modulo 64, the loop offset of `k_asmread` [Ref1]. The function `call` starts at 24 modulo 64, as in `bwx10` and in `bwx8` [Ref2].
- What is timed: only lines 1272 to 1284 or lines 1272 to 1298 of `worker`. The interval starts at the clock read `t0` and ends at the last clock read `t1`. Between them lie the kernel calls through `call`, the byte count and the clock reads. Not timed: allocation, first touch, warm-up pass, barrier waits, the wait for the common start, counter readings, page-state readings and all output.
- Stop rule `--stop common`: all threads get the same deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted (line 1285).
- Rate. The program prints one rate: the last column of the I row, the bytes of all threads divided by the longest elapsed time of one thread, in GB/s with GB = 1e9 bytes (line 2655). A T row holds the bytes and the elapsed time of one thread and no rate (line 2659).
- Kernel calls. With `--stop common` the kernel function is entered once per chunk. A kernel that saves `d8` to `d15` does so once per call, outside its loop. One clock read follows each call (lines 1279 to 1284).
- Thread placement: thread `i` pins itself to entry `i` of the CPU list before it opens its counters and before it maps its buffer (lines 1225 to 1229, line 2588). The main thread is not pinned in the interval mode.
- Buffers: each buffer is a private mapping of its own, and no two threads share a buffer. A thread has one buffer, or two with `--two-buffers` or with a copy kernel in `--seq`. A buffer starts at a 2 MiB boundary, and `alloc_buf` asks Linux for 2 MiB pages for it unless `--no-thp` is given. The pinned thread writes the `--bytes` range of the buffer once before any read. The read kernels never change it (lines 401 to 418, lines 1229 to 1230).
- Order inside a process: the kernels run in the order of `--seq`, and the rounds follow one another directly. The file holds no call of a sleep function. Before each timed interval the worker runs the warm-up pass with the kernel of that interval (line 1253).
- Counters in the interval mode: each thread opens its group once and never resets it. A C row holds the change between a reading directly before `t0` and a reading directly after the last `t1`. An event that does not open is printed as `NA` (line 1184, lines 2674 to 2675).
- What ends a process of the interval mode with exit status 2: a bad argument, a failed `mmap`, a failed call that reads or sets the allowed CPU set, an allowed CPU set without a CPU from 0 to 119, a failed read of the counter group, and a failed setup in `main`. A failed `mprotect` or `madvise` in `alloc_buf` only writes a message, and the run continues (line 412, line 416). The trial mode also ends with exit status 2 on a defect of its plan file.
- The code of this file does not look at the marker file and opens files only for reading. Its output is the csv text on the standard output and the messages on stderr.

## Source and explanation, line by line

- Text shown: the file `bwx11-2026-11-15/bwx11.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (2703 lines, 103208 bytes, sha256 `a820940b50c5bd736e5eba6285a2856c15be914194434df2c1d81471b96e4c51`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### History comment of the version `bwx11`: three kernels and the option `--evict-mb` (lines 1 to 26)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/* bwx11+ */` | Comment: a marker. A block of text that the version `bwx11` added starts here. The marker of line 26 ends the block. |
| 2 | `/*` | Opens a history comment. It tells what the version of the marker in line 1 added. |
| 3 | ` * bwx11.c - bwx10.c plus the additions of round 4 (2026-11-15). Every` | Comment: `bwx11.c` is `bwx10.c` plus the additions of round 4, made on 2026-11-15. Round 4 is a round of work on the program. It is not a round of the option `--rounds`. |
| 4 | ` * addition stands between a line "bwx11+" and a line "bwx11-" (both are` | Comment: every addition of that round stands between a marker line `bwx11+` and a marker line `bwx11-`. |
| 5 | ` * comments). Without these blocks this file is bwx10.c byte for byte:` | Comment: both marker lines are comments. Without these blocks the text of `bwx11.c` is `bwx10.c`, byte for byte. |
| 6 | ` * test_runner11.py checks it. So the 26 kernels of bwx10, call(),` | Comment: the script `test_runner11.py` in the code folder `bwx11-2026-11-15` checks this. So the 26 kernels of `bwx10` and the function `call` (line 1075) are the text of `bwx10.c` without a change. |
| 7 | ` * timed_sequence(), timed_sequence_hot() and the interval mode are the text` | Comment: the same holds for the functions `timed_sequence` (line 1579) and `timed_sequence_hot` (line 1640) and for the interval mode, the mode of the option `--seq`. |
| 8 | ` * of bwx10.c.` | Comment: the end of the sentence of lines 6 to 7. The parts that it names are the text of `bwx10.c`. |
| 9 | ` *` | Comment: an empty line of the comment. |
| 10 | ` * Additions:` | Comment: the heading of the list of additions. |
| 11 | ` *   kernels read_nop64, read_nop96, read_nop128: the asmread loop with 64, 96` | Comment: three kernels: `read_nop64`, `read_nop96` and `read_nop128` (lines 1029 to 1031). Each is the loop of the kernel `asmread` with `nop` instructions added. A `nop` is an instruction that does nothing. |
| 12 | ` *     and 128 nop instructions after the 8 ldp. They stand after the last` | Comment: the three kernels have 64, 96 and 128 `nop` after the 8 `ldp` instructions, which load the data. In the source they stand after the last kernel of `bwx10`. |
| 13 | ` *     kernel of bwx10 in the source and in kernels[], so the kernels of bwx10` | Comment: in the kernel table `kernels[]` they also stand after the kernels of `bwx10` (line 1065). |
| 14 | ` *     keep their machine code and their loop offsets.` | Comment: so the kernels of `bwx10` keep their machine code and their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. |
| 15 | ` *   A second pad after these kernels, so that call() and the code up to the` | Comment: a second pad after these kernels (lines 1039 to 1042). A pad is a run of unused bytes in the code. In the version `bwx11` it sets the start address of the function `call`. |
| 16 | ` *     end of timed_sequence_hot() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence_hot` keeps its placement modulo 64. |
| 17 | ` *   --evict-mb N  (trial mode) before the first trial the worker writes N MiB` | Comment: the option `--evict-mb N` of the trial mode. Before the first trial the worker writes N MiB of other memory, twice (line 2012). |
| 18 | ` *     of other memory twice. This pushes the benchmark buffer out of the` | Comment: after these writes the caches no longer hold the data of the benchmark buffer. |
| 19 | ` *     caches, so its lines are read back from memory.` | Comment: so the next read of the buffer brings its cache lines back from memory. A cache line is a block of 64 B. |
| 20 | ` *   M rows evict_mb and evict_ns. With --trace and N above 0 also the rows` | Comment: two new M rows, `evict_mb` and `evict_ns` (lines 2085 to 2091). An M row prints one setting or one fact of a process in the trial mode. With `--trace` and N above 0 the program also prints two TR rows. |
| 21 | ` *     TR,-1,0,evict_start,<t_ns> and TR,-1,1,evict_end,<t_ns>.` | Comment: the two TR rows are `TR,-1,0,evict_start,<t_ns>` and `TR,-1,1,evict_end,<t_ns>`. They give the clock times of the start and of the end of these writes, in ns (line 2093). |
| 22 | ` * The line that includes the self-test file is changed by additions only: the` | Comment: the line that includes the self-test file is changed by additions only (lines 2472 to 2477). |
| 23 | ` * old line stands inside "#if 0".` | Comment: the old include line stands inside `#if 0`. So the compiler skips it, and no old line was deleted. |
| 24 | ` * The plan file format is unchanged ("# bwx8-plan v1").` | Comment: the format of the plan file is unchanged. Its first line is still `# bwx8-plan v1` (line 1399). |
| 25 | ` */` | Ends the history comment. |
| 26 | `/* bwx11- */` | Comment: a marker. The block that line 1 opened ends here. |

### History comment of the version `bwx10`: five kernels and two options of the trial mode (lines 27 to 51)

| Line | Source | Explanation |
|---:|---|---|
| 27 | `/* bwx10+ */` | Comment: a marker. A block of text that the version `bwx10` added starts here. The marker of line 51 ends the block. |
| 28 | `/*` | Opens a history comment. It tells what the version of the marker in line 27 added. |
| 29 | ` * bwx10.c - bwx8.c plus the additions of round 3 (2026-11-15). Every addition` | Comment: `bwx10.c` is `bwx8.c` plus the additions of round 3, made on 2026-11-15. Round 3 is a round of work on the program. It is not a round of the option `--rounds`. |
| 30 | ` * stands between a line "bwx10+" and a line "bwx10-" (both are comments).` | Comment: every addition of that round stands between a marker line `bwx10+` and a marker line `bwx10-`. Both marker lines are comments. |
| 31 | ` * Without these blocks, and with the name of the included self-test file set` | Comment: one more change separates `bwx10.c` from `bwx8.c`: the name of the included self-test file (line 2475). |
| 32 | ` * back, this file is bwx8.c byte for byte: test_runner10.py checks it. So the` | Comment: without the blocks, and with that name set back, the text of `bwx10.c` is `bwx8.c`, byte for byte. The script `test_runner10.py` in the code folder `bwx10-2026-11-15` checks this. |
| 33 | ` * 21 kernels of bwx8, call(), timed_sequence() and the interval mode are the` | Comment: so the 21 kernels of `bwx8`, the function `call` (line 1075), the function `timed_sequence` (line 1579) and the interval mode are unchanged. The interval mode is the mode of the option `--seq`. |
| 34 | ` * text of bwx8.c.` | Comment: the end of the sentence of line 33. The parts that it names are the text of `bwx8.c`. |
| 35 | ` *` | Comment: an empty line of the comment. |
| 36 | ` * Additions:` | Comment: the heading of the list of additions. |
| 37 | ` *   kernels read_pf256, read_pf512, read_pf1024, read_pf2048, read_1pl. They` | Comment: five kernels: `read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048` (lines 946 to 949) and `read_1pl` (line 955). |
| 38 | ` *     stand after the last kernel of bwx8 in the source and in kernels[], so` | Comment: in the source and in the kernel table `kernels[]` (lines 1061 to 1062) the five kernels stand after the last kernel of `bwx8`. |
| 39 | ` *     the kernels of bwx8 keep their machine code and their loop offsets.` | Comment: so the kernels of `bwx8` keep their machine code and their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. |
| 40 | ` *   --rec-pad BYTES  (trial mode) unused bytes before the win[] array of the` | Comment: the option `--rec-pad BYTES` of the trial mode. It puts that many unused bytes before the array `win[]`, which holds the window records (line 1862). |
| 41 | ` *     record block.` | Comment: the array `win[]` is a part of the record block. That is the one memory block that holds the results of all trials (line 1845). |
| 42 | ` *   --hot-copy       (trial mode) timed_sequence_hot() runs the windows: it` | Comment: the option `--hot-copy` of the trial mode. With it the function `timed_sequence_hot` (line 1640) runs the windows of a trial. |
| 43 | ` *     does not read or write win[i] between the first and the last pass of a` | Comment: between the first pass and the last pass of a window that function does not read or write `win[i]`, the record of the window. |
| 44 | ` *     window.` | Comment: the last word of the sentence of lines 42 to 43. |
| 45 | ` *   M rows rec_pad, hot_copy, rec_addr, win_addr, win_size, stack_addr,` | Comment: new M rows of the trial mode (line 2075): `rec_pad`, `hot_copy`, `rec_addr`, `win_addr`, `win_size` and `stack_addr`. An M row prints one setting or one fact of the process. |
| 46 | ` *     buf_addr, tw_addr.` | Comment: two more new M rows: `buf_addr` and `tw_addr`. |
| 47 | ` *   A pad after the new kernels, so that call() and the code up to the end` | Comment: a pad after the new kernels (lines 1003 to 1006). A pad is a run of unused bytes in the code. In the version `bwx10` it sets the start address of the function `call`. |
| 48 | ` *     of timed_sequence() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence` keeps its placement modulo 64. |
| 49 | ` * The plan file format is unchanged ("# bwx8-plan v1").` | Comment: the format of the plan file is unchanged. Its first line is still `# bwx8-plan v1` (line 1399). |
| 50 | ` */` | Ends the history comment. |
| 51 | `/* bwx10- */` | Comment: a marker. The block that line 27 opened ends here. |

### Comment of the version `bwx8`: the two modes and the stand-in kernels (lines 52 to 72)

| Line | Source | Explanation |
|---:|---|---|
| 52 | `/*` | Opens the comment of the version `bwx8`. It is the first version of the runner that has a trial mode. |
| 53 | ` * bwx8.c - scratch copy of bwx.c (crb/tmp/agent-scratch/bwx-2026-11-13) for` | Comment: `bwx8.c` is a scratch copy of `bwx.c`, the first runner. The path in parentheses is the folder of `bwx.c`. In the code repo that folder has the name `bwx-2026-11-13`. |
| 54 | ` * the design crb/new-test-kernel/tackle-8mb.md. The contract with the other` | Comment: the copy was made for the design document `tackle-8mb.md` in the folder `crb/new-test-kernel`. The sentence about the contract continues in line 55. |
| 55 | ` * parts is DECISIONS-bwx8.md in this folder.` | Comment: the contract with the other parts of that work is the file `DECISIONS-bwx8.md`. It fixes the file formats that the parts exchange. The file lies in the code folder `bwx8-2026-11-14`, the folder of `bwx8.c`. |
| 56 | ` *` | Comment: an empty line of the comment. |
| 57 | ` * Two modes:` | Comment: the program has two modes. |
| 58 | ` *   --seq ...    the interval mode of bwx.c. Its code is the text of bwx.c.` | Comment: the option `--seq` selects the interval mode of `bwx.c`. The comment says that the code of this mode is the text of `bwx.c`. `main` runs this mode when no argument is the word `--trial` (lines 2489 to 2491). |
| 59 | ` *   --trial ...  one pinned worker runs the trials of a plan file. A trial is` | Comment: the option `--trial` selects the trial mode. One pinned worker thread runs the trials of a plan file. All code of this mode stands after the function `parse_events` (lines 1355 to 1377). |
| 60 | ` *                previous activity, prefix, predecessor and target windows` | Comment: a trial is a list of windows in four phases: previous activity, prefix, predecessor and target. A window runs one kernel on one range of the buffer for a fixed time. |
| 61 | ` *                with nothing but clock reads between them.` | Comment: between two windows the worker does nothing but read the clock. The code has one more step there: for a trial with the counter state `read` it also reads the counter group and the thread CPU time before each target window (lines 1587 to 1588). |
| 62 | ` *` | Comment: an empty line of the comment. |
| 63 | ` * Everything from "#define _GNU_SOURCE" to the end of parse_events() is the` | Comment: names a range of this file. It reaches from the line `#define _GNU_SOURCE` (line 73) to the end of the function `parse_events` (line 1377). |
| 64 | ` * text of bwx.c, so the kernels, PLACE, call() and alloc_buf() are unchanged.` | Comment: that range is the text of `bwx.c`. So the kernels, the macro `PLACE` (line 130), the function `call` (line 1075) and the function `alloc_buf` (line 401) are unchanged. The later versions put their marked blocks into this range too. |
| 65 | ` * All code of the trial mode stands after it. The build uses` | Comment: all code of the trial mode stands after that range. The sentence about the build continues in line 66. |
| 66 | ` * -fno-toplevel-reorder, so the kernels keep their place in the binary.` | Comment: the build uses the gcc flag `-fno-toplevel-reorder`. With it gcc writes the functions in the order of the source. So the kernels keep their place in the binary. The build record of CRB for `bwx11` holds this flag [Ref2]. |
| 67 | ` *` | Comment: an empty line of the comment. |
| 68 | ` * On AArch64 the kernels are the real ones. On any other machine every NEON` | Comment: on AArch64, the 64-bit Arm instruction set, the kernels are the real ones. The sentence about other machines starts here. |
| 69 | ` * and asm kernel is replaced by a plain C stand-in, so that the harness can` | Comment: on any other machine a plain C loop replaces every NEON kernel and every assembly kernel. The comment calls this loop a stand-in. NEON is the vector part of AArch64. |
| 70 | ` * be run on the development machine. Rates of a stand-in build mean nothing.` | Comment: the stand-ins have one purpose: the program can then run on the development machine. The rates of a build with stand-ins mean nothing. |
| 71 | ` * GB means 1e9 bytes throughout.` | Comment: GB means 1e9 bytes in the whole file. |
| 72 | ` */` | Ends the comment. |

### Includes, constants and the highest CPU that the process may use (lines 73 to 108)

| Line | Source | Explanation |
|---:|---|---|
| 73 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include. It makes the Linux-specific declarations of the C library visible, for example `sched_setaffinity` and `CPU_SET`. |
| 74 | `#ifdef __aarch64__` | Compiles line 75 only when the compiler builds for AArch64, the 64-bit Arm instruction set. gcc defines the macro `__aarch64__` in that case. |
| 75 | `#include <arm_neon.h>` | Includes `arm_neon.h`. It declares the NEON intrinsics, for example `vld1q_u64`. An intrinsic is a C function that maps to one vector instruction. NEON is the vector part of AArch64. |
| 76 | `#endif` | Ends the `#ifdef` of line 74. |
| 77 | `#include <errno.h>` | Includes `errno.h`. It declares `errno`, the error number that a failed library call sets. `parse_long` tests it (lines 323 to 325). |
| 78 | `#include <linux/perf_event.h>` | Includes `linux/perf_event.h`. It declares the structure `perf_event_attr` and the `PERF_FORMAT` constants. `open_counters` (line 1166) opens the hardware counters with them. |
| 79 | `#include <pthread.h>` | Includes `pthread.h`. It declares the thread functions `pthread_create` and `pthread_join` and the barrier function `pthread_barrier_wait`. |
| 80 | `#include <sched.h>` | Includes `sched.h`. It declares the CPU set type `cpu_set_t` and the calls `sched_getaffinity` and `sched_setaffinity`. They read and set the CPUs on which Linux may run a thread. |
| 81 | `#include <setjmp.h>` | Includes `setjmp.h`. It declares `sigsetjmp` and `siglongjmp`. No other line of this file uses them. The self-test file that this file includes uses them. |
| 82 | `#include <signal.h>` | Includes `signal.h`. It declares `sigaction` and the signal numbers. No other line of this file uses them. The included self-test file uses them to catch `SIGSEGV`, the signal that Linux sends at a forbidden memory access. |
| 83 | `#include <stdatomic.h>` | Includes `stdatomic.h`. It declares the atomic types and the functions `atomic_load`, `atomic_store` and `atomic_fetch_add`. The three variables of the common start use them (lines 290 to 292). |
| 84 | `#include <stdint.h>` | Includes `stdint.h`. It declares the integer types of fixed size, for example `uint64_t` (64 bits, without a sign) and `int64_t` (64 bits, with a sign). |
| 85 | `#include <stdio.h>` | Includes `stdio.h`. It declares the input and output functions, for example `printf`, `fprintf`, `fopen` and `fgets`. |
| 86 | `#include <stdlib.h>` | Includes `stdlib.h`. It declares `exit`, `strtol`, `strtod`, `calloc` and `getenv`. |
| 87 | `#include <string.h>` | Includes `string.h`. It declares the text and memory functions, for example `strcmp`, `strtok`, `memset` and `strerror`. |
| 88 | `#include <sys/mman.h>` | Includes `sys/mman.h`. It declares `mmap`, `mprotect` and `madvise`. `alloc_buf` (line 401) uses them for the buffers. |
| 89 | `#include <sys/syscall.h>` | Includes `sys/syscall.h`. It declares the numbers of the system calls, here `SYS_perf_event_open`. `open_counters` passes this number to `syscall` (line 1179). |
| 90 | `#include <time.h>` | Includes `time.h`. It declares `clock_gettime` and the structure `timespec`. `now_ns` (line 294) reads the clock with them. |
| 91 | `#include <unistd.h>` | Includes `unistd.h`. It declares `sysconf`, `getpid` and `read`. |
| 93 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2097152 bytes (2 MiB), the size of one huge page. The expression is 2 shifted left by 20 bits. Every buffer starts at a multiple of this value (line 409). |
| 94 | `#define MAX_CPUS 1024` | `MAX_CPUS`: the `--cpus` list may hold at most 1024 CPUs (line 373). |
| 95 | `#define MAX_SEQ 64` | `MAX_SEQ`: the `--seq` list may hold at most 64 kernels (line 1343). |
| 96 | `#define MAX_EV 8` | `MAX_EV`: the `--events` list may hold at most 8 counter events (line 1360). |
| 97 | `#define CHECK_BYTES (8UL << 20) /* --stop pass: clock is read after at least this many bytes */` | `CHECK_BYTES`: 8388608 bytes (8 MiB). Comment: with `--stop pass` a thread reads the clock after at least this many bytes. For some sizes the code reads the clock earlier. The number of whole passes between two clock reads is this value divided by the size of the range, rounded down, and at least 1 (lines 1288 to 1290). So with a range of 3 MiB the thread reads the clock after 2 passes, which are 6 MiB. The trial mode computes its passes in the same way (line 1832). |
| 98 | `#define CHUNK_BYTES HUGE_BYTES  /* --stop common: clock is read after each chunk of this size */` | `CHUNK_BYTES`: the value of `HUGE_BYTES`, 2097152 bytes (2 MiB). It is the size of a chunk. Comment: with `--stop common` a worker calls the kernel on one chunk and then reads the clock (lines 1277 to 1284). When the range of a `--seq` entry is below 2 MiB, the chunk is that whole range (line 1277). |
| 99 | `#define LEAD_NS 2000000L        /* --stop common: the common start is this long after the barrier */` | `LEAD_NS`: 2000000 ns (2 ms). With `--stop common` the main thread reads the clock after its barrier wait and sets the common start time of an interval to that clock value plus 2 ms (lines 2634 to 2636). The release at the barrier is not the start of the timed interval. Each worker waits until the clock reaches the common start time (line 1265). Then it starts its timed interval with its own clock read `t0` (line 1272). |
| 100 | `#define LATE_NS 100000L         /* --stop common: flag "late" if a thread starts later than this */` | `LATE_NS`: 100000 ns (100 us, which is 0.1 ms). With `--stop common` a thread gets the flag `late` when its start clock read is more than this after the common start (line 1309). |
| 101 | `/* Highest CPU that the process may use. Rule of the test machine: CPUs 0 to` | Comment: the macro below gives the highest CPU number that the process may use. The rule of the test machine starts here: only the CPUs 0 to 119. |
| 102 | ` * 119 only, never 126 or 127. main() removes every higher CPU from the` | Comment: the end of the rule: never CPU 126 or CPU 127. `main` calls `restrict_cpus` (line 2488), which removes every higher CPU from the set of CPUs that Linux may use for the process. |
| 103 | ` * allowed set of the process, and --cpus rejects one. Another machine can` | Comment: the option `--cpus` also rejects a higher CPU (line 368). |
| 104 | ` * build with -DMAX_USE_CPU=N. */` | Comment: for another machine the build can set another limit with the compiler option `-DMAX_USE_CPU=N`. |
| 105 | `#ifndef MAX_USE_CPU` | Tests whether the build command has already defined `MAX_USE_CPU`. Only if not, line 106 is compiled. `restrict_cpus` (line 335) and `parse_cpus` (line 355) apply the limit. |
| 106 | `#define MAX_USE_CPU 119` | The default value: the highest CPU that the process may use is CPU 119. The CRB build of `bwx11` gave no `-D` option, so this value was used [Ref2]. |
| 107 | `#endif` | Ends the `#ifndef` of line 105. |

### Loop placement: the macros `PLACE` and `PADOF` (lines 109 to 132)

| Line | Source | Explanation |
|---:|---|---|
| 109 | `/*` | Opens the comment about the placement of the kernel loops. |
| 110 | ` * Loop placement (handoff B.7). PLACE(name) stands directly before kernel` | Comment: the topic is the loop placement. The aim is that the loop of each kernel starts at a known address modulo 64, the loop offset. Section B.7 of the file `handoff.md`, the specification of the first runner, treats this offset as a test factor [Ref4]. The macro `PLACE(name)` stands directly before the kernel function. |
| 111 | ` * k_<name>. It pads .text to a 64 B boundary and then adds PAD_<name> zero bytes,` | Comment: the kernel function has the name `k_` plus the kernel name. `PLACE` first pads the code section `.text` to a 64 B boundary. Then it adds zero bytes. The macro `PAD_` plus the kernel name gives their number. |
| 112 | ` * so the function starts at PAD_<name> modulo 64. This needs the gcc flags` | Comment: so the function starts at that pad value modulo 64. The method needs two gcc flags. |
| 113 | ` * -fno-toplevel-reorder -falign-functions=4, and PAD must be a multiple of 4.` | Comment: the two flags are `-fno-toplevel-reorder` and `-falign-functions=4`. A pad must be a multiple of 4. Both flags are in the build record of CRB for `bwx11` [Ref2]. |
| 114 | ` *` | Comment: an empty line of the comment. |
| 115 | ` * For a kernel with a planned loop offset, PAD = (LOOP - HEAD) mod 64. LOOP` | Comment: the rule for a kernel with a planned loop offset: the pad is `(LOOP - HEAD) mod 64`. |
| 116 | ` * is the planned offset of the loop start modulo 64. HEAD is the number of` | Comment: `LOOP` is the planned offset of the loop start, modulo 64. `HEAD` is a number of bytes. |
| 117 | ` * bytes between the function start and the loop start: 4 or 20 in the` | Comment: `HEAD` counts the bytes of code between the start of the function and the start of its loop. The comment gives the values 4 and 20. |
| 118 | ` * listings of bw_new (results/kernels-20261113T181222Z/probe.txt). HEAD is a` | Comment: these two values come from the listings of the binary `bw_new` in the file `probe.txt` of the result folder `kernels-20261113T181222Z`. `bw_new` is the benchmark binary of 2026-11-13 with the new kernels. In that file the loop of `k_copy` starts 4 bytes after the function start, and the loop of `k_asmcopy` 20 bytes after it [Ref3]. |
| 119 | ` * guess until the objdump listing of the CRB build confirms it: override it` | Comment: a `HEAD` value is a guess until the machine-code listing of the CRB build confirms it. |
| 120 | ` * with -DHEAD_<name>=N, or the whole pad with -DPAD_<name>=N.` | Comment: the build can replace one `HEAD` value with `-DHEAD_<name>=N`, or a whole pad with `-DPAD_<name>=N`. The CRB build of `bwx11` used no `-D` option [Ref2]. |
| 121 | ` * -DB3_OFFSET=0\|36\|52 puts the loops of copy, asmcopy and asmcopy2 at that` | Comment: the build option `-DB3_OFFSET=0`, `-DB3_OFFSET=36` or `-DB3_OFFSET=52` moves the loops of the kernels `copy`, `asmcopy` and `asmcopy2`. |
| 122 | ` * offset (step B3).` | Comment: these loops then start at that offset modulo 64 (lines 133 to 135). The option belongs to step B3 of the test plan of the first runner. |
| 123 | ` *` | Comment: an empty line of the comment. |
| 124 | ` * For the other kernels the default PAD is the start offset modulo 64 that` | Comment: the rule for every other kernel: the default pad is a start offset modulo 64 that the function has in an older binary. |
| 125 | ` * the function has in bw_new (new C and asm kernels) or in bw_old (old` | Comment: for a new C kernel or an assembly kernel the older binary is `bw_new`. For an old kernel it is `bw_old`. The old read kernel and the new read kernel show the result. The loop of `k_read` starts at 36 modulo 64 in the CRB build of `bwx11` and in `bw_new`. The loop of `k_oldread` in `bwx11` and the loop of `k_read` in `bw_old` both start at 40 modulo 64 [Ref1] [Ref3]. |
| 126 | ` * kernels). An A/A copy takes the PAD of its original.` | Comment: an A/A copy takes the pad of its original. An A/A copy is the same kernel source under a second name, for example `asmread2`. |
| 127 | ` */` | Ends the comment. |
| 128 | `#define STR2(x) #x` | `STR2(x)` turns its argument into a text in quotes. The preprocessor operator `#` does that. |
| 129 | `#define STR(x) STR2(x)` | `STR(x)` first replaces `x` by its value when `x` is a macro. Then it calls `STR2`. So with the default value 32 of `PAD_read`, `STR(PAD_read)` gives the text `"32"` and not the name in quotes. |
| 130 | `#define PLACE(name) __asm__(".pushsection .text\n.p2align 6\n.fill " STR(PAD_##name) ", 1, 0\n.popsection\n")` | `PLACE(name)` writes an `__asm__` statement outside of a function. gcc passes its text to the assembler without a change. `.pushsection .text` continues in the code section. `.p2align 6` pads the code up to an address that is a multiple of 64. `.fill N, 1, 0` adds N bytes of value 0. N is the value of the macro whose name `PAD_##name` builds from `PAD_` and the argument. `.popsection` returns to the section that was in use before. So the function that follows starts at N modulo 64. |
| 131 | `#define PADOF(loop, head) (((loop) - (head)) & 63)` | `PADOF(loop, head)`: `loop` minus `head`, modulo 64. The operation `& 63` keeps the low 6 bits. So a negative difference also gives a value from 0 to 63. |

### Planned loop offsets, head sizes and pads of the first kernels (lines 133 to 219)

| Line | Source | Explanation |
|---:|---|---|
| 133 | `#ifdef B3_OFFSET` | Tests whether the build command defined `B3_OFFSET`. The CRB build of `bwx11` did not, so the `#else` branch of lines 136 to 138 was compiled [Ref2]. |
| 134 | `#define LOOP_copy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_copy`, the planned loop offset of the kernel `copy`, is N. |
| 135 | `#define LOOP_asmcopy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_asmcopy`, the planned loop offset of the kernel `asmcopy`, is N too. |
| 136 | `#else` | Starts the branch for a build without `B3_OFFSET`. |
| 137 | `#define LOOP_copy 36` | `LOOP_copy`: the loop of the kernel `copy` must start at 36 modulo 64. In the CRB binary of `bwx11` the loop of `k_copy` starts at `0x4324`, which is 36 modulo 64 [Ref1]. |
| 138 | `#define LOOP_asmcopy 52` | `LOOP_asmcopy`: the loop of the kernel `asmcopy` must start at 52 modulo 64. In the CRB binary of `bwx11` the loop of `k_asmcopy` starts at `0x48f4`, which is 52 modulo 64 [Ref1]. |
| 139 | `#endif` | Ends the `#ifdef` of line 133. |
| 140 | `#define LOOP_asmcopy_c 52` | `LOOP_asmcopy_c`: 52 modulo 64, the planned loop offset of the three kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg` (lines 165 to 173). `B3_OFFSET` does not change it. |
| 141 | `#ifndef HEAD_copy` | Compiles line 142 only when the build command has not defined `HEAD_copy`. Every value up to line 218 has this pattern of three lines: a default that a `-D` option of the build can replace. |
| 142 | `#define HEAD_copy 4` | `HEAD_copy`: 4 bytes of code, which is one instruction, stand between the start of `k_copy` and the start of its loop. The listing of the CRB build of `bwx11` shows this distance [Ref1]. |
| 143 | `#endif` | Ends the `#ifndef` of line 141. |
| 144 | `#ifndef HEAD_asmcopy` | Compiles line 145 only when the build command has not defined `HEAD_asmcopy`. |
| 145 | `#define HEAD_asmcopy 20` | `HEAD_asmcopy`: 20 bytes of code, which are 5 instructions, stand before the loop of `k_asmcopy`. The listing of the CRB build of `bwx11` shows them: 4 `stp` instructions that save the registers `d8` to `d15`, and the `add` that computes the end address [Ref1]. |
| 146 | `#endif` | Ends the `#ifndef` of line 144. |
| 147 | `#ifndef HEAD_asmcopy_c` | Compiles line 148 only when the build command has not defined `HEAD_asmcopy_c`. |
| 148 | `#define HEAD_asmcopy_c 4` | `HEAD_asmcopy_c`: 4 bytes of code stand before the loop of `k_asmcopy_c`. The listing of the CRB build of `bwx11` shows this distance [Ref1]. |
| 149 | `#endif` | Ends the `#ifndef` of line 147. |
| 150 | `#ifndef HEAD_asmcopy_c_add` | Compiles line 151 only when the build command has not defined `HEAD_asmcopy_c_add`. |
| 151 | `#define HEAD_asmcopy_c_add 4` | `HEAD_asmcopy_c_add`: 4 bytes of code stand before the loop of `k_asmcopy_c_add`. The listing of the CRB build of `bwx11` shows this distance [Ref1]. |
| 152 | `#endif` | Ends the `#ifndef` of line 150. |
| 153 | `#ifndef HEAD_asmcopy_c_reg` | Compiles line 154 only when the build command has not defined `HEAD_asmcopy_c_reg`. |
| 154 | `#define HEAD_asmcopy_c_reg 20` | `HEAD_asmcopy_c_reg`: 20 bytes of code stand before the loop of `k_asmcopy_c_reg`. This kernel saves `d8` to `d15`, as `asmcopy` does. The listing of the CRB build of `bwx11` shows this distance [Ref1]. |
| 155 | `#endif` | Ends the `#ifndef` of line 153. |
| 156 | `#ifndef PAD_copy` | Compiles line 157 only when the build command has not defined `PAD_copy`. |
| 157 | `#define PAD_copy PADOF(LOOP_copy, HEAD_copy)` | `PAD_copy`: `PADOF` (line 131) computes it from the two values above. With the defaults it is (36 - 4) modulo 64 = 32 bytes. In the CRB binary of `bwx11` the function `k_copy` starts at `0x4320`, which is 32 modulo 64 [Ref1]. |
| 158 | `#endif` | Ends the `#ifndef` of line 156. |
| 159 | `#ifndef PAD_asmcopy` | Compiles line 160 only when the build command has not defined `PAD_asmcopy`. |
| 160 | `#define PAD_asmcopy PADOF(LOOP_asmcopy, HEAD_asmcopy)` | `PAD_asmcopy`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx11` the function `k_asmcopy` starts at `0x48e0`, which is 32 modulo 64 [Ref1]. |
| 161 | `#endif` | Ends the `#ifndef` of line 159. |
| 162 | `#ifndef PAD_asmcopy2` | Compiles line 163 only when the build command has not defined `PAD_asmcopy2`. |
| 163 | `#define PAD_asmcopy2 PAD_asmcopy` | `PAD_asmcopy2`: the A/A copy `asmcopy2` takes the pad of its original `asmcopy`. With the defaults that is 32 bytes. |
| 164 | `#endif` | Ends the `#ifndef` of line 162. |
| 165 | `#ifndef PAD_asmcopy_c` | Compiles line 166 only when the build command has not defined `PAD_asmcopy_c`. |
| 166 | `#define PAD_asmcopy_c PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c)` | `PAD_asmcopy_c`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx11` the function `k_asmcopy_c` starts at `0x4a70`, which is 48 modulo 64 [Ref1]. |
| 167 | `#endif` | Ends the `#ifndef` of line 165. |
| 168 | `#ifndef PAD_asmcopy_c_add` | Compiles line 169 only when the build command has not defined `PAD_asmcopy_c_add`. |
| 169 | `#define PAD_asmcopy_c_add PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_add)` | `PAD_asmcopy_c_add`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx11` the function `k_asmcopy_c_add` starts at `0x4b30`, which is 48 modulo 64 [Ref1]. |
| 170 | `#endif` | Ends the `#ifndef` of line 168. |
| 171 | `#ifndef PAD_asmcopy_c_reg` | Compiles line 172 only when the build command has not defined `PAD_asmcopy_c_reg`. |
| 172 | `#define PAD_asmcopy_c_reg PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_reg)` | `PAD_asmcopy_c_reg`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx11` the function `k_asmcopy_c_reg` starts at `0x4be0`, which is 32 modulo 64 [Ref1]. |
| 173 | `#endif` | Ends the `#ifndef` of line 171. |
| 174 | `#ifndef PAD_read` | Compiles line 175 only when the build command has not defined `PAD_read`. |
| 175 | `#define PAD_read 32` | `PAD_read` = 32: the new read kernel `k_read` starts at 32 modulo 64. In the CRB binary of `bwx11` it starts at the address `0x4260`, which is 32 modulo 64 [Ref1]. |
| 176 | `#endif` | Ends the `#ifndef` of line 174. |
| 177 | `#ifndef PAD_write` | Compiles line 178 only when the build command has not defined `PAD_write`. |
| 178 | `#define PAD_write 0` | `PAD_write` = 0: `k_write`, the function of the first touch, starts at 0 modulo 64. In the CRB binary of `bwx11` it starts at the address `0x42c0` [Ref1]. |
| 179 | `#endif` | Ends the `#ifndef` of line 177. |
| 180 | `#ifndef PAD_asmread` | Compiles line 181 only when the build command has not defined `PAD_asmread`. |
| 181 | `#define PAD_asmread 0` | `PAD_asmread` = 0: `k_asmread` starts at 0 modulo 64. In the CRB binary of `bwx11` it starts at the address `0x4380` [Ref1]. |
| 182 | `#endif` | Ends the `#ifndef` of line 180. |
| 183 | `#ifndef PAD_asmread2` | Compiles line 184 only when the build command has not defined `PAD_asmread2`. |
| 184 | `#define PAD_asmread2 PAD_asmread` | `PAD_asmread2`: the A/A copy `asmread2` takes the pad of `asmread`, which is 0 bytes. |
| 185 | `#endif` | Ends the `#ifndef` of line 183. |
| 186 | `#ifndef PAD_asmwrite` | Compiles line 187 only when the build command has not defined `PAD_asmwrite`. |
| 187 | `#define PAD_asmwrite 32` | `PAD_asmwrite` = 32: `k_asmwrite` starts at 32 modulo 64. |
| 188 | `#endif` | Ends the `#ifndef` of line 186. |
| 189 | `#ifndef PAD_asmwrite2` | Compiles line 190 only when the build command has not defined `PAD_asmwrite2`. |
| 190 | `#define PAD_asmwrite2 PAD_asmwrite` | `PAD_asmwrite2`: the A/A copy `asmwrite2` takes the pad of `asmwrite`, which is 32 bytes. |
| 191 | `#endif` | Ends the `#ifndef` of line 189. |
| 192 | `#ifndef PAD_oldread` | Compiles line 193 only when the build command has not defined `PAD_oldread`. |
| 193 | `#define PAD_oldread 0` | `PAD_oldread` = 0: the old read kernel `k_oldread` starts at 0 modulo 64. In the CRB binary of `bwx11` it starts at the address `0x3ec0` [Ref1]. |
| 194 | `#endif` | Ends the `#ifndef` of line 192. |
| 195 | `#ifndef PAD_oldread2` | Compiles line 196 only when the build command has not defined `PAD_oldread2`. |
| 196 | `#define PAD_oldread2 PAD_oldread` | `PAD_oldread2`: the A/A copy `oldread2` takes the pad of `oldread`, which is 0 bytes. |
| 197 | `#endif` | Ends the `#ifndef` of line 195. |
| 198 | `#ifndef PAD_oldwrite` | Compiles line 199 only when the build command has not defined `PAD_oldwrite`. |
| 199 | `#define PAD_oldwrite 32` | `PAD_oldwrite` = 32: `k_oldwrite` starts at 32 modulo 64. |
| 200 | `#endif` | Ends the `#ifndef` of line 198. |
| 201 | `#ifndef PAD_oldcopy` | Compiles line 202 only when the build command has not defined `PAD_oldcopy`. |
| 202 | `#define PAD_oldcopy 32` | `PAD_oldcopy` = 32: `k_oldcopy` starts at 32 modulo 64. |
| 203 | `#endif` | Ends the `#ifndef` of line 201. |
| 204 | `#ifndef PAD_read_nop4` | Compiles line 205 only when the build command has not defined `PAD_read_nop4`. |
| 205 | `#define PAD_read_nop4 PAD_asmread` | `PAD_read_nop4`: the kernel `read_nop4` takes the pad of `asmread`, which is 0 bytes. |
| 206 | `#endif` | Ends the `#ifndef` of line 204. |
| 207 | `#ifndef PAD_read_nop8` | Compiles line 208 only when the build command has not defined `PAD_read_nop8`. |
| 208 | `#define PAD_read_nop8 PAD_asmread` | `PAD_read_nop8`: the kernel `read_nop8` takes the pad of `asmread`, which is 0 bytes. |
| 209 | `#endif` | Ends the `#ifndef` of line 207. |
| 210 | `#ifndef PAD_read_nop16` | Compiles line 211 only when the build command has not defined `PAD_read_nop16`. |
| 211 | `#define PAD_read_nop16 PAD_asmread` | `PAD_read_nop16`: the kernel `read_nop16` takes the pad of `asmread`, which is 0 bytes. |
| 212 | `#endif` | Ends the `#ifndef` of line 210. |
| 213 | `#ifndef PAD_read_nop32` | Compiles line 214 only when the build command has not defined `PAD_read_nop32`. |
| 214 | `#define PAD_read_nop32 PAD_asmread` | `PAD_read_nop32`: the kernel `read_nop32` takes the pad of `asmread`, which is 0 bytes. |
| 215 | `#endif` | Ends the `#ifndef` of line 213. |
| 216 | `#ifndef PAD_read_sparse` | Compiles line 217 only when the build command has not defined `PAD_read_sparse`. |
| 217 | `#define PAD_read_sparse PAD_asmread` | `PAD_read_sparse`: the kernel `read_sparse` takes the pad of `asmread`, which is 0 bytes. |
| 218 | `#endif` | Ends the `#ifndef` of line 216. |

### Kernel types and one entry of the `--seq` list (lines 220 to 230)

| Line | Source | Explanation |
|---:|---|---|
| 220 | `enum ktype { T_READ, T_WRITE, T_COPY, T_OLDREAD };` | `enum ktype`: the four kernel types `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD`. The function `call` (line 1075) chooses the argument list of a kernel by its type. |
| 221 | `typedef void (*read_fn)(const uint64_t *, size_t);` | `read_fn`: the function type of a read kernel (type `T_READ`). The kernel gets the start address and the number of 8-byte words. It returns nothing. |
| 222 | `typedef uint64_t (*oldread_fn)(const uint64_t *, size_t);` | `oldread_fn`: the function type of an old read kernel (type `T_OLDREAD`). The kernel gets the same two arguments and returns a 64-bit sum. |
| 223 | `typedef void (*write_fn)(uint64_t *, size_t, uint64_t);` | `write_fn`: the function type of a write kernel (type `T_WRITE`). The kernel gets the start address, the number of 8-byte words and the 64-bit value to store. |
| 224 | `typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);` | `copy_fn`: the function type of a copy kernel (type `T_COPY`). The kernel gets the destination address, the source address and the number of 8-byte words. `restrict` tells the compiler that the two ranges do not overlap. |
| 226 | `struct entry {` | Starts `struct entry`: one entry of the `--seq` list. |
| 227 | `    int k;          /* index into kernels[] */` | `k`: the index of the kernel in the kernel table `kernels[]` (line 1051). |
| 228 | `    uint64_t bytes; /* 0 until main() replaces it by --bytes */` | `bytes`: the size of the range that the kernel works on, in bytes. It is 0 when the entry has no `@SIZE` part. `main` then sets it to the `--bytes` value (lines 2566 to 2567). |
| 229 | `};` | Ends `struct entry`. |

### The settings structure `cfg` (lines 231 to 250)

| Line | Source | Explanation |
|---:|---|---|
| 231 | `static struct {` | Starts the structure `cfg`. It holds the settings of the process. The code that reads the arguments fills it. |
| 232 | `    int threads;` | `threads`: the number of worker threads (`--threads`). |
| 233 | `    int ncpus;` | `ncpus`: the number of entries of `cpus`. |
| 234 | `    int cpus[MAX_CPUS];` | `cpus`: the CPU list of `--cpus`, in the order of the list. `parse_cpus` (line 355) fills it. |
| 235 | `    uint64_t bytes;` | `bytes`: the value of `--bytes` in bytes. It is the range of each buffer that the program uses: the first touch writes this many bytes (line 1230), and no `--seq` entry may be larger (line 2568). The mapped buffer is this value rounded up to a multiple of 2 MiB (line 395). |
| 236 | `    double min_s;` | `min_s`: the `--min-ms` value in seconds. With `--stop common` the deadline of an interval is this long after its common start (line 2638). With `--stop pass` a thread runs at least this long (line 1299). |
| 237 | `    int use_thp;` | `use_thp`: 1 when the program asks Linux for 2 MiB pages (transparent huge pages) for the buffers. The option `--no-thp` sets it to 0. |
| 238 | `    struct entry seq[MAX_SEQ];` | `seq`: the kernel list of `--seq`, one `struct entry` per kernel. |
| 239 | `    int nseq;` | `nseq`: the number of entries of `seq`. |
| 240 | `    int rounds;` | `rounds`: how many times the list runs (`--rounds`). |
| 241 | `    int stop_common;  /* --stop common */` | `stop_common`: 1 with `--stop common`. With this stop rule all threads of an interval get the same deadline. |
| 242 | `    int start_offset; /* --start offset */` | `start_offset`: 1 with `--start offset`. Then the place in its buffer at which a thread starts an interval depends on the number of the thread (line 1246). The option chooses a place in the buffer. It does not set the start time of an interval. |
| 243 | `    int two_buffers;  /* buffer b exists: --two-buffers, or a copy kernel in the sequence */` | `two_buffers`: 1 when each thread has a second buffer `b`. The option `--two-buffers` sets it. `main` also sets it when the list holds a copy kernel (lines 2573 to 2574). |
| 244 | `    int count;        /* --count */` | `count`: 1 with `--count`. Then each thread opens hardware counters and reads them before and after each interval. |
| 245 | `    long pmu_type;    /* --pmu-type: the "type" field of perf_event_attr */` | `pmu_type`: the value of `--pmu-type`. It goes into the field `type` of the structure `perf_event_attr` (line 1173). The field tells Linux which counter hardware to use. |
| 246 | `    int nev;` | `nev`: the number of counter events of `--events`. |
| 247 | `    char ev_name[MAX_EV][32];` | `ev_name`: the names of the events, at most 31 characters each. |
| 248 | `    uint64_t ev_code[MAX_EV];` | `ev_code`: the codes of the events. A code goes into the field `config` of `perf_event_attr` (line 1175). |
| 249 | `} cfg = { .threads = 1, .min_s = 0.5, .use_thp = 1, .rounds = 1, .pmu_type = -1 };` | Ends the structure and sets the defaults: 1 thread, 0.5 s per interval, a request for 2 MiB pages, 1 round and no PMU type (the value -1). Every other field starts at 0. |

### Structures `page`, `counts`, `result` and `thread` (lines 251 to 282)

| Line | Source | Explanation |
|---:|---|---|
| 251 | `struct page {` | Starts `struct page`: the page state of one buffer. |
| 252 | `    long kb_total, kb_huge; /* -1: no exact entry in /proc/self/smaps */` | `kb_total`: the size of the mapping of the buffer. `kb_huge`: the part of it that lies on 2 MiB pages. Both are in kB (1 kB is 1024 bytes here). `read_smaps` (line 1099) fills them. Comment: -1 means that the Linux file `/proc/self/smaps` has no exact entry for the buffer. Such a value is printed as `NA`. |
| 253 | `};` | Ends `struct page`. |
| 255 | `struct counts {` | Starts `struct counts`: one reading of the counters of a thread. |
| 256 | `    uint64_t cpu_ns;              /* CLOCK_THREAD_CPUTIME_ID */` | `cpu_ns`: the CPU time that the thread has used, in ns. The Linux clock `CLOCK_THREAD_CPUTIME_ID` gives it (line 1196). |
| 257 | `    uint64_t enabled, running;    /* of the counter group */` | `enabled` and `running`: two times of the counter group in ns. They say how long the counters were enabled and how long they really counted. |
| 258 | `    uint64_t val[MAX_EV];` | `val`: one count per event that opened. |
| 259 | `};` | Ends `struct counts`. |
| 261 | `/* One thread, one interval. Written by the worker between the start barrier` | Comment: the structure below holds the result of one thread for one interval. The worker writes it after the start barrier of the interval. The start barrier is the barrier wait that stands before the timed interval (line 1259). The timed interval of a thread does not start at this barrier. It starts later, at the clock read `t0` of the thread (line 1272). |
| 262 | ` * and the end barrier of the interval; read by main() after the end barrier. */` | Comment: the worker writes it before the end barrier of the interval, and `main` reads it after that barrier. In the code the worker stores the structure at line 1310, before its barrier wait of line 1311. `main` reads it after its barrier wait of line 2641. So the two threads never use it at the same time. |
| 263 | `struct result {` | Starts `struct result`. |
| 264 | `    uint64_t bytes;` | `bytes`: the bytes that the thread counted in the interval (line 1305). |
| 265 | `    int64_t t_sched, t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_sched`: the common start time. `t_start`: the start clock read `t0` of the thread. `t_end`: its last clock read `t1`. All three are values of the clock `CLOCK_MONOTONIC` in ns (lines 1306 to 1308). With `--stop pass` there is no common start, and `t_sched` gets the value of `t0`. |
| 266 | `    int late;` | `late`: the late flag. It is 1 when `t0` of the thread was more than `LATE_NS` after the common start (line 1309). |
| 267 | `    struct page pg[2]; /* one-thread process only: read by the worker before the interval */` | `pg`: the page state of the buffers `a` and `b`. Comment: only a process with one thread uses it. There the worker reads the page state before the interval (lines 1254 to 1258). |
| 268 | `    long long vm[4];` | `vm`: four counters of the Linux file `/proc/vmstat` (line 1129). As for `pg`, only the worker of a process with one thread fills it. |
| 269 | `    struct counts c0, c1;` | `c0` and `c1`: the counter readings before `t0` (lines 1269 to 1270) and after the last `t1` (lines 1302 to 1303). |
| 270 | `};` | Ends `struct result`. |
| 272 | `struct thread {` | Starts `struct thread`: one record per worker. |
| 273 | `    int idx;` | `idx`: the number of the thread, counted from 0 (line 2587). |
| 274 | `    int cpu;` | `cpu`: the CPU that the thread pins itself to, or -1 without `--cpus` (line 2588). |
| 275 | `    uint64_t *a, *b;` | `a`: the buffer of the thread. `b`: the second buffer, which only a copy kernel or `--two-buffers` needs. Without it `b` stays `NULL`. |
| 276 | `    int group_fd;      /* leader of the counter group, -1 if no event opened */` | `group_fd`: the file descriptor of the leader of the counter group. A file descriptor is the number that Linux returns for an open object. Comment: it is -1 when no event opened. `open_counters` (line 1166) sets it. |
| 277 | `    int ev_pos[MAX_EV]; /* position of the event in the group read, -1 if it did not open */` | `ev_pos`: for each event its position among the values of a group read. Comment: -1 when the event did not open. |
| 278 | `    int nopen;` | `nopen`: the number of events that opened. |
| 279 | `    struct result res;` | `res`: the result of the last interval of this thread. |
| 280 | `    pthread_t tid;` | `tid`: the thread handle that `pthread_create` returns (line 2589). |
| 281 | `};` | Ends `struct thread`. |

### Global variables: the barrier, the base time and the common start (lines 283 to 293)

| Line | Source | Explanation |
|---:|---|---|
| 283 | `static pthread_barrier_t bar;` | `bar`: the barrier. A thread that calls `pthread_barrier_wait` on it blocks until all workers and the main thread have called it. `main` creates it for the number of workers plus 1 (line 2582). |
| 284 | `static int64_t t_base_ns; /* clock at process start: printed times are relative to it */` | `t_base_ns`: the clock value at the process start (line 2485). Comment: the printed times are relative to it. |
| 285 | `static long page_bytes;` | `page_bytes`: the page size that Linux reports, in bytes (line 2486). `alloc_buf` uses it (line 409). |
| 287 | `/* --stop common (handoff B.4). gen only grows. main() stores the two times` | Comment: the three variables below belong to `--stop common`. The comment cites section B.4 of the file `handoff.md`, the specification of the first runner. `gen` only grows. |
| 288 | ` * before it increments gen, so a worker that sees the new gen reads the new` | Comment: `main` stores the two times before it adds 1 to `gen` (lines 2637 to 2639). A worker first waits for the new value of `gen` (line 1261). |
| 289 | ` * times. */` | Comment: then the worker loads the two times (lines 1263 to 1264). So it never uses the times of the interval before. |
| 290 | `static _Atomic uint64_t gen;` | `gen`: an atomic counter of intervals. It starts at 0. `_Atomic` makes every load and every store of the variable one indivisible step. |
| 291 | `static _Atomic int64_t t_sched_ns;` | `t_sched_ns`: the common start time of the coming interval, as a value of the clock `CLOCK_MONOTONIC` in ns. With `--stop common` every worker waits until the clock reaches this time (line 1265). The timed interval of a worker starts after that, at its own clock read `t0` (line 1272). |
| 292 | `static _Atomic int64_t deadline_ns;` | `deadline_ns`: the common deadline of the coming interval: the common start time plus the `--min-ms` value (line 2638). With `--stop common` a worker ends its timed interval at its first clock read `t1` at or after this deadline (lines 1284 to 1285). So each worker finishes the chunk that it is in. |

### Function `now_ns`: read the clock (lines 294 to 300)

| Line | Source | Explanation |
|---:|---|---|
| 294 | `static int64_t now_ns(void)` | Starts the function `now_ns`. It reads the clock and returns the time in ns. Every time stamp of the program comes from this function. In a timed interval the worker calls it once for the start `t0` (line 1272). With `--stop common` it then calls it once after each chunk for `t1` (line 1284). A chunk is 2 MiB, or the whole range of the `--seq` entry when that is smaller. So one clock read per chunk is inside the timed interval. This is the same for every kernel. |
| 295 | `{` | Opens the body of `now_ns`. |
| 296 | `    struct timespec ts;` | `ts`: a `timespec`, the structure for a time as whole seconds plus ns. |
| 297 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | `clock_gettime` reads the Linux clock `CLOCK_MONOTONIC` into `ts`. This clock cannot be set. It does not jump when the date or the time of the system is changed. |
| 298 | `    return (int64_t)ts.tv_sec * 1000000000L + ts.tv_nsec;` | Returns the seconds times 1000000000 plus the ns part: the time in ns as one 64-bit number. |
| 299 | `}` | Ends the function `now_ns`. |

### Function `parse_bytes`: a size text such as `256M` (lines 301 to 317)

| Line | Source | Explanation |
|---:|---|---|
| 301 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `256M` into a number of bytes. `main` calls it for `--bytes` (line 2514). `parse_seq` calls it for the `@SIZE` part of a `--seq` entry (line 1348). |
| 302 | `{` | Opens the body of `parse_bytes`. |
| 303 | `    char *end;` | `end`: `strtod` sets it to the first character after the number. |
| 304 | `    double v = strtod(s, &end);` | `strtod` reads a decimal number from the start of the text into `v`. The number may have a fraction, for example `1.5`. |
| 305 | `    double mul = 1;` | `mul`: the factor of the unit letter. It stays 1 when no letter follows the number. |
| 306 | `    switch (*end) {` | Looks at the character after the number. |
| 307 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | The letter `k` or `K`: the factor is 1024. `end++` moves `end` to the character after the letter. |
| 308 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | The letter `m` or `M`: the factor is 1048576, which is 1 MiB. So the text `256M` gives 256 times 1048576, which is 268435456 bytes. |
| 309 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | The letter `g` or `G`: the factor is 1073741824, which is 1024 MiB. |
| 310 | `    }` | Ends the `switch` of line 306. |
| 311 | `    if (end == s \|\| *end != '\0' \|\| v <= 0 \|\| (uint64_t)(v * mul) == 0) { /* 0 bytes after rounding is no size */` | Tests four error cases. The text holds no number (`end == s`). Other text follows the size. The value is 0 or below. The size is 0 bytes after the conversion to a whole number. Comment: 0 bytes after rounding is no size. |
| 312 | `        fprintf(stderr, "bad size: %s\n", s);` | In an error case: prints `bad size:` and the text to stderr, the error output of the program. |
| 313 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 314 | `    }` | Ends the `if` of line 311. |
| 315 | `    return (uint64_t)(v * mul);` | Returns the size in bytes as a whole number. The conversion drops a fraction of a byte. |
| 316 | `}` | Ends the function `parse_bytes`. |

### Function `parse_long`: a whole number inside a range (lines 318 to 331)

| Line | Source | Explanation |
|---:|---|---|
| 318 | `/* A whole number in [lo, hi], with nothing after it. Anything else ends the` | Comment: the function below accepts only a whole number from `lo` to `hi` with no text after it. |
| 319 | ` * program: a malformed value must not run as 0. */` | Comment: any other text ends the program. The reason: a malformed value must not run as the number 0. |
| 320 | `static long parse_long(const char *s, const char *what, long lo, long hi)` | Starts the function `parse_long`. It turns the text `s` into a whole number inside the range `lo` to `hi`. `what` is the name of the option, for the error message. `main` reads `--threads` (allowed 1 to 4096), `--rounds` (1 to 1000000) and `--pmu-type` (0 to 2147483647) with it (line 2509, line 2524, line 2539). |
| 321 | `{` | Opens the body of `parse_long`. |
| 322 | `    char *end;` | `end`: `strtol` sets it to the first character after the number. |
| 323 | `    errno = 0;` | Sets `errno` to 0. `strtol` sets it to an error value when the number does not fit the type `long`. |
| 324 | `    long v = strtol(s, &end, 10);` | `strtol` reads a decimal whole number (base 10) from the start of the text into `v`. |
| 325 | `    if (end == s \|\| *end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi) {` | Tests the error cases: no digit was read, other text follows the number, the number does not fit the type `long`, or it lies outside the range `lo` to `hi`. |
| 326 | `        fprintf(stderr, "bad %s: '%s' (a whole number from %ld to %ld is needed)\n", what, s, lo, hi);` | In an error case: prints `bad`, the option name, the text and the allowed range to stderr. |
| 327 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 328 | `    }` | Ends the `if` of line 325. |
| 329 | `    return v;` | Returns the number. |
| 330 | `}` | Ends the function `parse_long`. |

### Function `restrict_cpus`: no CPU above `MAX_USE_CPU` (lines 332 to 353)

| Line | Source | Explanation |
|---:|---|---|
| 332 | `/* Removes every CPU above MAX_USE_CPU from the allowed set of the calling` | Comment: the function below removes every CPU above `MAX_USE_CPU` from the allowed set of the calling thread. The allowed set is the set of CPUs on which Linux may run the thread. |
| 333 | ` * thread. main() calls it before it starts a thread, so the main thread and` | Comment: `main` calls the function before it starts a thread (line 2488). A new thread takes over the allowed set of the thread that creates it. |
| 334 | ` * every worker (also one without --cpus) stay on the permitted CPUs. */` | Comment: so the main thread and every worker stay on the permitted CPUs. This also holds for a worker of a run without `--cpus`. |
| 335 | `static void restrict_cpus(void)` | Starts the function `restrict_cpus`. |
| 336 | `{` | Opens the body of `restrict_cpus`. |
| 337 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 338 | `    int changed = 0;` | `changed`: becomes 1 when the set held a CPU above the limit. |
| 339 | `    if (sched_getaffinity(0, sizeof set, &set) != 0) {` | `sched_getaffinity` with the first argument 0 reads the allowed set of the calling thread into `set`. A return value other than 0 means that the call failed. |
| 340 | `        perror("sched_getaffinity");` | On failure: `perror` prints the word `sched_getaffinity` and the reason that Linux gave. |
| 341 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 342 | `    }` | Ends the `if` of line 339. |
| 343 | `    for (int c = MAX_USE_CPU + 1; c < CPU_SETSIZE; c++)` | Starts a loop over every CPU number above `MAX_USE_CPU`, up to `CPU_SETSIZE - 1`. `CPU_SETSIZE` is the number of CPUs that the set type of the C library can hold. With the default limit the loop starts at CPU 120. |
| 344 | `        if (CPU_ISSET(c, &set)) {` | Tests whether the set holds the CPU `c`. |
| 345 | `            CPU_CLR(c, &set);` | Removes the CPU `c` from the set. |
| 346 | `            changed = 1;` | Records that the set was changed. |
| 347 | `        }` | Ends the `if` of line 344. |
| 348 | `    if (changed && (CPU_COUNT(&set) == 0 \|\| sched_setaffinity(0, sizeof set, &set) != 0)) {` | Runs only when a CPU was removed. An empty set is an error. If the set is not empty, `sched_setaffinity` passes the smaller set to Linux, and a failed call is an error too. When the process starts with an allowed set that holds no CPU above `MAX_USE_CPU`, `changed` stays 0, and the function changes nothing. |
| 349 | `        fprintf(stderr, "cannot keep the process on CPUs 0-%d\n", MAX_USE_CPU);` | On error: prints `cannot keep the process on CPUs 0-` and the limit to stderr. |
| 350 | `        exit(2);` | On error: the whole program ends with exit status 2. |
| 351 | `    }` | Ends the `if` of line 348. |
| 352 | `}` | Ends the function `restrict_cpus`. |

### Function `parse_cpus`: the value of `--cpus` (lines 354 to 381)

| Line | Source | Explanation |
|---:|---|---|
| 354 | `/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */` | Comment: three examples of a CPU list: `0-119`, `0,2,4-7` and `0-118:2`. The last one is a range with a stride: every second CPU from 0 to 118. |
| 355 | `static void parse_cpus(char *list)` | Starts the function `parse_cpus`. It turns the value of `--cpus` into the array `cfg.cpus`, in the order of the list. |
| 356 | `{` | Opens the body of `parse_cpus`. |
| 357 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Starts a loop over the items of the list. `strtok` splits the text at each comma and returns one item per call. It writes into the text to do that. |
| 358 | `        char *e, *e2;` | `e` and `e2`: positions in the item that `strtol` sets. |
| 359 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the item into `lo`. `hi` starts with the same value and `step` with 1. So an item that is one number names one CPU. |
| 360 | `        if (e != tok && *e == '-') {` | When a number was read and a `-` follows it: the item is a range. |
| 361 | `            hi = strtol(e + 1, &e2, 10);` | Reads the upper bound of the range into `hi`. |
| 362 | `            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */` | When no digit follows the `-`, `e` is set back to `tok`, and the test of line 368 then rejects the item. If a number was read, `e` moves to the character after it. Comment: the item `0-` has no upper bound. |
| 363 | `            if (e != tok && *e == ':') {` | When the upper bound was read and a `:` follows it: the range has a stride. |
| 364 | `                step = strtol(e + 1, &e2, 10);` | Reads the stride into `step`. |
| 365 | `                e = e2 == e + 1 ? tok : e2;` | When no digit follows the `:`, `e` is set back to `tok`, and the test of line 368 rejects the item. If a number was read, `e` moves to the character after it. |
| 366 | `            }` | Ends the `if` of line 363. |
| 367 | `        }` | Ends the `if` of line 360. |
| 368 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| hi > MAX_USE_CPU \|\| step < 1) {` | Rejects an item in six cases: it holds no number, other text follows, the start is negative, the end is below the start, the end is above `MAX_USE_CPU` (119 with the default), or the stride is below 1. |
| 369 | `            fprintf(stderr, "bad cpu list: %s (CPUs 0-%d only)\n", tok, MAX_USE_CPU);` | On such an item: prints `bad cpu list:`, the item and the permitted range to stderr. |
| 370 | `            exit(2);` | On such an item: the whole program ends with exit status 2. |
| 371 | `        }` | Ends the `if` of line 368. |
| 372 | `        for (long c = lo; c <= hi; c += step) {` | Starts a loop over the CPU numbers of the item, from `lo` to `hi` in steps of `step`. |
| 373 | `            if (cfg.ncpus == MAX_CPUS) {` | Tests whether the array `cfg.cpus` is full. It holds at most `MAX_CPUS` entries, which is 1024. |
| 374 | `                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);` | When the array is full: prints `bad cpu list: more than 1024 cpus` to stderr. |
| 375 | `                exit(2);` | When the array is full: the whole program ends with exit status 2. |
| 376 | `            }` | Ends the `if` of line 373. |
| 377 | `            cfg.cpus[cfg.ncpus++] = (int)c;` | Appends the CPU number to `cfg.cpus` and counts it in `cfg.ncpus`. For example the list `0-63,64-119` gives 120 entries in rising order: `cfg.cpus[i]` is `i`. `main` gives thread `i` the CPU `cfg.cpus[i % cfg.ncpus]` (line 2588). |
| 378 | `        }` | Ends the loop of line 372. |
| 379 | `    }` | Ends the loop of line 357. |
| 380 | `}` | Ends the function `parse_cpus`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 382 to 392)

| Line | Source | Explanation |
|---:|---|---|
| 382 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It limits the calling thread to the CPU with the number `cpu`. A worker of a run with `--cpus` calls it at its start (lines 1225 to 1226), before it opens its counters and before it maps its buffer. |
| 383 | `{` | Opens the body of `pin_cpu`. |
| 384 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 385 | `    CPU_ZERO(&set);` | Empties the set. |
| 386 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 387 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 388 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 389 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 390 | `    }` | Ends the `if` of line 387. |
| 391 | `}` | Ends the function `pin_cpu`. |

### Function `buf_len`: the length of one buffer (lines 393 to 397)

| Line | Source | Explanation |
|---:|---|---|
| 393 | `static size_t buf_len(void)` | Starts the function `buf_len`. It returns the length of one buffer in bytes. |
| 394 | `{` | Opens the body of `buf_len`. |
| 395 | `    return (cfg.bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | Returns the `--bytes` value rounded up to a multiple of 2 MiB (`HUGE_BYTES`). The expression adds `HUGE_BYTES - 1` and then clears the low 21 bits. A value of 268435456 bytes (256 MiB) is already 128 times 2 MiB and stays as it is. |
| 396 | `}` | Ends the function `buf_len`. |

### Function `alloc_buf`: map one buffer, aligned to 2 MiB (lines 398 to 419)

| Line | Source | Explanation |
|---:|---|---|
| 398 | `/* The buffer starts at a 2 MiB boundary, at least one page above the start` | Comment: the buffer starts at a 2 MiB boundary. That boundary lies at least one page above the start of the mapping. |
| 399 | ` * of the mapping. The unused parts before and after it are PROT_NONE, so the` | Comment: the unused parts of the mapping before and after the buffer get the access right `PROT_NONE`, which forbids every access. |
| 400 | ` * buffer is one entry of its own in /proc/self/smaps (handoff B.6). */` | Comment: so the buffer is one entry of its own in `/proc/self/smaps`, the Linux file that lists every memory mapping of the process. `read_smaps` (line 1099) looks for an entry with exactly the start and the end of the buffer. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. |
| 401 | `static uint64_t *alloc_buf(void)` | Starts the function `alloc_buf`. It maps one buffer and returns its address. Each worker calls it once (line 1229). A worker of a run with `--cpus` has pinned itself before this call (lines 1225 to 1226). A worker that needs the second buffer calls it once more (line 1232). |
| 402 | `{` | Opens the body of `alloc_buf`. |
| 403 | `    size_t len = buf_len(), maplen = len + 2 * HUGE_BYTES;` | `len`: the buffer length from `buf_len`. `maplen`: 4 MiB more. The extra 4 MiB make room for the alignment of line 409 and for the two no-access ranges of lines 410 to 411. For a buffer of 256 MiB `len` is 268435456 bytes and `maplen` is 272629760 bytes (260 MiB). |
| 404 | `    uint8_t *raw = mmap(NULL, maplen, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `maplen` bytes of new memory that the process may read and write (`PROT_READ \| PROT_WRITE`). `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process only, and no file backs it. `NULL`: Linux chooses the address. `-1` and `0` are the two file arguments, which are not used here. The call does not yet give physical memory to the pages. That happens at the first touch (line 1230). |
| 405 | `    if (raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 406 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 407 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 408 | `    }` | Ends the `if` of line 405. |
| 409 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + (size_t)page_bytes + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the buffer start. It is the first 2 MiB boundary that lies at least one page above the start `raw` of the mapping. The expression adds the page size `page_bytes` and `HUGE_BYTES - 1` to `raw` and then clears the low 21 bits. The buffer is the range from `p` to `p + len`. So it starts at an address that is a multiple of 2 MiB. |
| 410 | `    if (mprotect(raw, (size_t)(p - raw), PROT_NONE) != 0 \|\|` | `mprotect` with `PROT_NONE` forbids every access to the unused range before the buffer, from `raw` to `p`. |
| 411 | `        mprotect(p + len, (size_t)(raw + maplen - (p + len)), PROT_NONE) != 0)` | Continues the test of line 410: the same for the unused range after the buffer, from `p + len` to the end of the mapping. This second call runs only when the first one succeeded. |
| 412 | `        perror("mprotect of the guard ranges (continuing; page state will be NA)");` | When one of the two calls failed: `perror` prints a message which says that the run continues and that the page state will be `NA`. The program does not stop. The message goes to stderr, the error output of the program. |
| 413 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: the advice `MADV_NOHUGEPAGE` matters on a host whose setting for transparent huge pages is `always`. |
| 414 | `     * would still get 2 MiB pages. */` | Comment: without that advice a run with `--no-thp` would still get 2 MiB pages on such a host. |
| 415 | `    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` gives Linux advice about the buffer range. With `cfg.use_thp` set, the advice is `MADV_HUGEPAGE`: use 2 MiB pages for this range. With `--no-thp` it is `MADV_NOHUGEPAGE`: do not use them. The function does not test whether the buffer got 2 MiB pages. The P rows show how much of each buffer lies on 2 MiB pages (line 1158). |
| 416 | `        perror("madvise (continuing)");` | When `madvise` failed: `perror` prints `madvise (continuing)` and the reason that Linux gave. The run continues. |
| 417 | `    return (uint64_t *)p;` | Returns the buffer start as a pointer to 8-byte words. No line of this file unmaps a buffer. So the buffer stays mapped until the process ends. |
| 418 | `}` | Ends the function `alloc_buf`. |

### Old read kernel: the macro `DEF_OLDREAD` and the kernels `oldread` and `oldread2` (lines 420 to 443)

| Line | Source | Explanation |
|---:|---|---|
| 420 | `/*` | Opens the comment about the old kernels. |
| 421 | ` * Old kernels: k_read, k_write and k_copy of bandwidth.orig.c (the benchmark` | Comment: the old kernels below are the functions `k_read`, `k_write` and `k_copy` of the file `bandwidth.orig.c`. |
| 422 | ` * until 2026-11-13), renamed. The old comment of k_read was: "16 independent` | Comment: `bandwidth.orig.c` was the benchmark source until 2026-11-13. Here its three kernels have the new names `k_oldread`, `k_oldwrite` and `k_oldcopy`. `bw_old` is the benchmark binary of 2026-11-13 that was built from that file. Apart from absolute addresses, the machine code of `k_oldread` in the CRB build of `bwx11` has the same instruction text as `k_read` of `bw_old` [Ref1] [Ref3]. A quotation of the old comment of `k_read` starts in this line. |
| 423 | ` * accumulators keep the loop load-bound: on 128-bit NEON gcc folds them into` | Comment, quotation: 16 separate running sums (accumulators) keep the loop load-bound. This means that the loads and not the adds should limit the speed of the loop. This is a statement of the old comment. It is not a measured result. |
| 424 | ` * 8 vector chains, enough to hide a 2-cycle add latency; on AVX-512 they` | Comment, quotation: with the 128-bit NEON registers gcc puts the 16 sums into 8 vector registers. Each register is a chain of adds of its own. The old comment says that 8 chains are enough for an add that takes 2 clock cycles: the adds then do not limit the speed of the loop. The listing of the CRB binary of `bwx11` confirms the 8 registers: the sums are in the registers `v24` to `v31` [Ref1]. |
| 425 | ` * become 2 zmm chains." oldread2 is the A/A copy: the same source under a` | Comment: the end of the quotation: with AVX-512, a vector instruction set of x86 processors, the sums become 2 chains in 512-bit registers. The next sentence: `oldread2` is the A/A copy, the same source under a second name. |
| 426 | ` * second name (the build uses -fno-ipa-icf, so gcc keeps both).` | Comment: the build uses the gcc flag `-fno-ipa-icf`. With it gcc keeps both functions. The flag is in the build record of CRB for `bwx11` [Ref2]. |
| 427 | ` */` | Ends the comment. |
| 428 | `#define DEF_OLDREAD(name) \` | Starts the macro `DEF_OLDREAD(name)`. It writes `PLACE(name)` and one function: the source text of the old read kernel. The backslash at the end of each line continues the macro on the next line. |
| 429 | `    PLACE(name); \` | `PLACE` (line 130) adds the pad of this kernel. So the function starts at the value of `PAD_` plus `name`, modulo 64. |
| 430 | `    __attribute__((noinline)) static uint64_t k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the macro argument into the function name. `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns a 64-bit sum. `noinline`: gcc must keep the function separate from its caller. The listing of the CRB build of `bwx11` shows `k_oldread` as a function of its own [Ref1]. With `--stop common` one call in a timed interval gets one chunk of 2 MiB: `n` is then 262144 words (line 1279). The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1253). |
| 431 | `    { \` | Opens the body of the kernel function. |
| 432 | `        uint64_t s[16] = { 0 }; \` | `s`: the 16 running sums. All start at 0. Machine code of `k_oldread` in `bwx11`, once per call and before the loop: 4 `stp` instructions write 128 B of zeros to the stack (each stores two 16-byte registers), and the 8 registers `v24` to `v31` are set to 0. During the loop these 8 registers hold the 16 sums, two sums per register [Ref1]. |
| 433 | `        for (size_t i = 0; i < n; i += 16) \` | The outer loop. One pass takes 16 words, which are 128 B. Machine code of `k_oldread` in `bwx11`: gcc did not unroll this loop. One pass of the machine loop is one pass of this source loop. Before the loop the code computes the number of passes into the register `x2` [Ref1]. |
| 434 | `            for (int j = 0; j < 16; j++) \` | The inner loop over the 16 words of the block. Machine code of `k_oldread` in `bwx11`: gcc compiled this loop to vector instructions. No loop over `j` is left [Ref1]. |
| 435 | `                s[j] += a[i + j]; \` | Adds word `j` of the block to sum `j`. So every loaded word is an input of one add. Machine code of `k_oldread` in `bwx11`, one loop pass of 16 instructions for 128 B [Ref1]: 4 `ldp` loads of 32 B each, at the byte offsets 0, 32, 64 and 96 from the read position. 8 vector adds: each one adds one loaded register to one of the sum registers `v24` to `v31` and so performs two of the 16 adds of the source. `add x0, x0, #0x80` moves the read position by 128 B. `add x1, x1, #0x1` counts the pass. `cmp` and `b.cc` branch back while the count is below the number of passes. No instruction of the loop stores to memory. |
| 436 | `        uint64_t sum = 0; \` | `sum`: the total of the 16 sums. It starts at 0. |
| 437 | `        for (int j = 0; j < 16; j++) \` | A loop over the 16 sums. It runs once per call, after the read loop. |
| 438 | `            sum += s[j]; \` | Adds the 16 sums into one value. Machine code of `k_oldread` in `bwx11`, once per call [Ref1]: the 8 sum registers are stored to the stack and loaded back. Then 7 vector adds and one `addp` add them into one number. `addp` adds the two 64-bit halves of one register. |
| 439 | `        return sum; \` | Returns the total. Machine code of `k_oldread` in `bwx11`: `fmov x0, d31` copies the result into the return register `x0` [Ref1]. `call` stores the returned value into the volatile variable `sink` (line 1084). So the sum is used, and the compiler cannot remove the loads and the adds as unused work. gcc also added a stack check to this function. It saves a guard value on the stack at the start and compares it before the return. A changed value leads to a call of `__stack_chk_fail` [Ref1]. |
| 440 | `    }` | Ends the kernel function and the macro. In `bwx11` one call of `k_oldread` runs 53 instructions outside the loop [Ref1]. One chunk of 2 MiB is 16384 loop passes, which are 262144 instructions. |
| 441 | `DEF_OLDREAD(oldread)` | Creates the function `k_oldread`. It is the kernel `oldread` of `--seq`, the old read kernel, with the type `T_OLDREAD` in the kernel table (line 1055). In the CRB binary of `bwx11` the function starts at the address `0x3ec0` and its loop at `0x3f28`, which is 40 modulo 64 [Ref1]. For 256 B it runs 2 loop passes: 32 instructions with 8 `ldp` loads, 16 vector adds and 2 branches. The new read kernel runs 11 instructions for 256 B (line 494). Apart from absolute addresses, the machine code of `k_oldread` has the same instruction text as `k_read` of the binary `bw_old` [Ref3]. |
| 442 | `DEF_OLDREAD(oldread2)` | Creates `k_oldread2`, the A/A copy of the old read kernel. The listing of the CRB build of `bwx11` shows the same instruction text for both functions [Ref1]. |

### Old write kernel `oldwrite` and old copy kernel `oldcopy` (lines 444 to 457)

| Line | Source | Explanation |
|---:|---|---|
| 444 | `PLACE(oldwrite);` | `PLACE` adds the pad of the kernel `oldwrite`. `PAD_oldwrite` is 32 (line 199). |
| 445 | `__attribute__((noinline)) static void k_oldwrite(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_oldwrite`, the kernel `oldwrite`: the write kernel of the old benchmark source. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. The first touch of a buffer uses `k_write` (line 498). |
| 446 | `{` | Opens the body of `k_oldwrite`. |
| 447 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 448 | `        a[i] = v;` | Stores `v` to word `i`: one store of 8 B per pass of the source loop. Machine code in the CRB binary of `bwx11`: gcc compiled the loop to instructions of SVE, the scalable vector extension of Arm. One loop pass has 4 instructions with one `st1d` store, which writes one vector of 8-byte words. The program reads the number of words per vector at run time with the instruction `cntd`. The listing does not give this number [Ref1]. |
| 449 | `}` | Ends the function `k_oldwrite`. |
| 451 | `PLACE(oldcopy);` | `PLACE` adds the pad of the kernel `oldcopy`. `PAD_oldcopy` is 32 (line 202). |
| 452 | `__attribute__((noinline)) static void k_oldcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_oldcopy`, the kernel `oldcopy`: the copy kernel of the old benchmark source. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 453 | `{` | Opens the body of `k_oldcopy`. |
| 454 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 455 | `        d[i] = s[i];` | Loads word `i` of the source and stores it to word `i` of the destination. The loaded value is stored and has no other use. Machine code in the CRB binary of `bwx11`: SVE instructions, as in `k_oldwrite`. One loop pass has 5 instructions with one `ld1d` load and one `st1d` store of one vector of 8-byte words [Ref1]. |
| 456 | `}` | Ends the function `k_oldcopy`. |

### AArch64 branch and the function `k_read`: the new read kernel (lines 458 to 496)

| Line | Source | Explanation |
|---:|---|---|
| 458 | `#if defined(__aarch64__)` | The lines from here to the `#else` of line 818 are compiled only for AArch64. The lines from that `#else` to the `#endif` of line 864 hold the stand-ins for other machines. The CRB build of `bwx11` is an AArch64 build: its listing holds AArch64 instructions such as the `ldp` of `k_read` [Ref1]. So it was compiled from this first branch. |
| 459 | `#define STANDIN 0` | `STANDIN` is 0 in the AArch64 branch: the kernels are the real ones. The program then prints `kernels=aarch64` in its header (line 2601). |
| 460 | `/*` | Opens the comment about the C kernels. |
| 461 | ` * C kernels: unchanged from bench/bandwidth.c. Each iteration moves 256 B as` | Comment: the C kernels below are unchanged from the benchmark source `bandwidth.c` in the folder `bench`. One loop pass moves 256 B. |
| 462 | ` * 16 vectors of 16 B and does no arithmetic on the data. Callers guarantee` | Comment: the 256 B move as 16 vectors of 16 B. The loop does no arithmetic on the data. |
| 463 | ` * n * 8 is a multiple of 256 and non-zero. The empty asm statement of k_read` | Comment: the callers guarantee that the size `n * 8` in bytes is a multiple of 256 and is not 0. `main` checks the sizes (line 2550 and line 2568). A chunk of 2 MiB is a multiple of 256. The sentence about the empty `asm` statement starts here. |
| 464 | ` * and k_copy takes the 16 loaded vectors as inputs in NEON registers ("w"):` | Comment: the empty `asm` statement of `k_read` (lines 489 to 492) and of `k_copy` (lines 547 to 550) takes the 16 loaded vectors as inputs. The letter `w` says that each input must be in a NEON register. |
| 465 | ` * see the comment in bench/bandwidth.c.` | Comment: a comment in the file `bandwidth.c` of the folder `bench` explains this statement. |
| 466 | ` */` | Ends the comment. |
| 467 | `PLACE(read);` | `PLACE(read)` with `PAD_read` = 32 (line 175): the function starts at 32 modulo 64. In the CRB binary of `bwx11` the function `k_read` starts at the address `0x4260` and its loop at `0x4264`, which is 36 modulo 64 [Ref1]. The loop of `k_read` in `bw_new` has the same offset 36 [Ref3]. |
| 468 | `__attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)` | Starts the function `k_read`: the kernel `read` of `--seq`, the new read kernel, with the type `T_READ` in the kernel table (line 1053). `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns nothing: it computes no sum. `noinline`: gcc must keep the function separate from its caller. The listing of `bwx11` shows it as a function of 13 instructions [Ref1]. Apart from absolute addresses, its instruction text equals the text of `k_read` in `bw_new`, the benchmark binary of 2026-11-13 with the new kernels [Ref3]. |
| 469 | `{` | Opens the body of `k_read`. With `--stop common` one call of the function in a timed interval gets one chunk of 2 MiB: `n` is then 262144 words (line 1279). The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1253). |
| 470 | `    const uint64_t *p = a;` | `p`: the read position. It starts at `a`. |
| 471 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx11`, once per call and before the loop: `add x1, x0, x1, lsl #3`. Before this instruction the register `x0` holds `a` and `x1` holds `n`. After it `x1` holds `end` [Ref1]. |
| 472 | `    do {` | Starts the loop. With `do` the loop body runs once before the first test of the end. So the range must not be empty. |
| 473 | `        uint64x2_t v0 = vld1q_u64(p + 0);` | `vld1q_u64(p + 0)` loads 16 B, which are two 8-byte words, from the read position into the vector `v0`. These are the bytes 0 to 15 of the current block of 256 B. |
| 474 | `        uint64x2_t v1 = vld1q_u64(p + 2);` | Loads the bytes 16 to 31 of the block, 2 words after the read position, into `v1`. Machine code of `bwx11`: gcc joined this load and the load of line 473 into one instruction, `ldp q31, q30, [x0]`, which loads 32 B [Ref1]. |
| 475 | `        uint64x2_t v2 = vld1q_u64(p + 4);` | Loads the bytes 32 to 47 of the block into `v2`. |
| 476 | `        uint64x2_t v3 = vld1q_u64(p + 6);` | Loads the bytes 48 to 63 of the block into `v3`. Machine code of `bwx11` for this load and the load of line 475: `ldp q29, q28, [x0, #32]` [Ref1]. |
| 477 | `        uint64x2_t v4 = vld1q_u64(p + 8);` | Loads the bytes 64 to 79 of the block into `v4`. |
| 478 | `        uint64x2_t v5 = vld1q_u64(p + 10);` | Loads the bytes 80 to 95 of the block into `v5`. Machine code of `bwx11` for this load and the load of line 477: `ldp q27, q26, [x0, #64]` [Ref1]. |
| 479 | `        uint64x2_t v6 = vld1q_u64(p + 12);` | Loads the bytes 96 to 111 of the block into `v6`. |
| 480 | `        uint64x2_t v7 = vld1q_u64(p + 14);` | Loads the bytes 112 to 127 of the block into `v7`. Machine code of `bwx11` for this load and the load of line 479: `ldp q25, q24, [x0, #96]` [Ref1]. |
| 481 | `        uint64x2_t v8 = vld1q_u64(p + 16);` | Loads the bytes 128 to 143 of the block into `v8`. |
| 482 | `        uint64x2_t v9 = vld1q_u64(p + 18);` | Loads the bytes 144 to 159 of the block into `v9`. Machine code of `bwx11` for this load and the load of line 481: `ldp q23, q22, [x0, #128]` [Ref1]. |
| 483 | `        uint64x2_t v10 = vld1q_u64(p + 20);` | Loads the bytes 160 to 175 of the block into `v10`. |
| 484 | `        uint64x2_t v11 = vld1q_u64(p + 22);` | Loads the bytes 176 to 191 of the block into `v11`. Machine code of `bwx11` for this load and the load of line 483: `ldp q21, q20, [x0, #160]` [Ref1]. |
| 485 | `        uint64x2_t v12 = vld1q_u64(p + 24);` | Loads the bytes 192 to 207 of the block into `v12`. |
| 486 | `        uint64x2_t v13 = vld1q_u64(p + 26);` | Loads the bytes 208 to 223 of the block into `v13`. Machine code of `bwx11` for this load and the load of line 485: `ldp q19, q18, [x0, #192]` [Ref1]. |
| 487 | `        uint64x2_t v14 = vld1q_u64(p + 28);` | Loads the bytes 224 to 239 of the block into `v14`. |
| 488 | `        uint64x2_t v15 = vld1q_u64(p + 30);` | Loads the bytes 240 to 255 of the block into `v15`. Machine code of `bwx11` for this load and the load of line 487: `ldp q17, q16, [x0, #224]`. One loop pass has 16 loads in the source and 8 `ldp` loads in the machine code. It reads 256 B, each byte once, in rising address order [Ref1]. |
| 489 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text. It adds no instruction to the loop. It names the loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. A comment in the benchmark source `bandwidth.c` gives the purpose: gcc must have all 16 values in registers at this point, and this keeps gcc from deleting the loads. After this statement nothing uses the values. They are dropped. The listing of `bwx11` shows no add and no other instruction that uses a loaded register [Ref1]. This is the difference to the old read kernel, which adds every loaded word to a sum. |
| 490 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 489: the inputs `v4` to `v7`. |
| 491 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 489: the inputs `v8` to `v11`. |
| 492 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 489: the inputs `v12` to `v15`. The statement ends here. |
| 493 | `        p += 32;` | Moves the read position forward by 32 words, which are 256 B. Machine code of `bwx11`: `add x0, x0, #0x100` [Ref1]. |
| 494 | `    } while (p < end);` | Repeats the loop while the read position is below the end. Machine code of `bwx11`: `cmp x1, x0`, then `b.hi` back to the first `ldp`. One loop pass is 11 instructions for 256 B: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1]. One chunk of 2 MiB is 8192 loop passes, which are 90112 instructions. |
| 495 | `}` | Ends the function `k_read`. Machine code of `bwx11`: one `ret` instruction. gcc used the registers `q16` to `q31` for the loads, and the function saves and restores no register [Ref1]. The AArch64 branch of line 458 continues after this function, up to line 818. |

### Function `k_write`: the NEON write kernel, used for the first touch (lines 497 to 523)

| Line | Source | Explanation |
|---:|---|---|
| 497 | `PLACE(write);` | `PLACE(write)` adds the pad of this kernel. `PAD_write` is 0 (line 178). So the function starts at a multiple of 64 bytes: the address `0x42c0` in the listing of the CRB build of `bwx11`. The function stands in the AArch64 branch of line 458, and the CRB binary holds this branch: the listing shows the `dup` and `stp` instructions of this function [Ref1]. |
| 498 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_write`, the NEON write kernel. It stores the value `v` to `n` 8-byte words, from the address `a` on. Each worker calls it once per buffer, directly after the allocation (line 1230). This call is the first touch. It happens before the first interval, and it is not timed. The call writes the first `cfg.bytes` bytes of the buffer, the range of `--bytes`. The buffer is this value rounded up to a multiple of 2 MiB (line 395). So the call writes the whole buffer only when `--bytes` is a multiple of 2 MiB. The kernel table also offers this function as the kernel `write` (line 1053). |
| 499 | `{` | Opens the body of `k_write`. |
| 500 | `    uint64_t *p = a;` | `p`: the write position. It starts at `a`. |
| 501 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx11`, before the loop: `add x1, x0, x1, lsl #3` [Ref1]. |
| 502 | `    uint64x2_t q = vdupq_n_u64(v);` | `vdupq_n_u64(v)` builds one 16-byte vector `q` that holds `v` twice. Machine code of `bwx11`, before the loop: `dup v31.2d, x2`. The register `x2` holds `v`. `dup` copies one 8-byte value into both halves of a 16-byte vector register [Ref1]. |
| 503 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 504 | `        vst1q_u64(p + 0, q);` | `vst1q_u64(p + 0, q)` stores the 16 bytes of `q` at the write position. These are the bytes 0 to 15 of the current block of 256 B. |
| 505 | `        vst1q_u64(p + 2, q);` | Stores `q` to the bytes 16 to 31 of the block. Machine code of `bwx11`: gcc joined this store and the store of line 504 into one instruction `stp q31, q31`. `stp` stores two 16-byte registers, which is 32 B. Here both are the register `q31` [Ref1]. |
| 506 | `        vst1q_u64(p + 4, q);` | Stores `q` to the bytes 32 to 47 of the block. |
| 507 | `        vst1q_u64(p + 6, q);` | Stores `q` to the bytes 48 to 63 of the block. |
| 508 | `        vst1q_u64(p + 8, q);` | Stores `q` to the bytes 64 to 79 of the block. |
| 509 | `        vst1q_u64(p + 10, q);` | Stores `q` to the bytes 80 to 95 of the block. |
| 510 | `        vst1q_u64(p + 12, q);` | Stores `q` to the bytes 96 to 111 of the block. |
| 511 | `        vst1q_u64(p + 14, q);` | Stores `q` to the bytes 112 to 127 of the block. |
| 512 | `        vst1q_u64(p + 16, q);` | Stores `q` to the bytes 128 to 143 of the block. |
| 513 | `        vst1q_u64(p + 18, q);` | Stores `q` to the bytes 144 to 159 of the block. |
| 514 | `        vst1q_u64(p + 20, q);` | Stores `q` to the bytes 160 to 175 of the block. |
| 515 | `        vst1q_u64(p + 22, q);` | Stores `q` to the bytes 176 to 191 of the block. |
| 516 | `        vst1q_u64(p + 24, q);` | Stores `q` to the bytes 192 to 207 of the block. |
| 517 | `        vst1q_u64(p + 26, q);` | Stores `q` to the bytes 208 to 223 of the block. |
| 518 | `        vst1q_u64(p + 28, q);` | Stores `q` to the bytes 224 to 239 of the block. |
| 519 | `        vst1q_u64(p + 30, q);` | Stores `q` to the bytes 240 to 255 of the block. The 16 stores of one loop pass fill 256 B. Each byte is written once. The machine loop of `bwx11` has 8 `stp` instructions [Ref1]. |
| 520 | `        p += 32;` | Moves the write position forward by 32 words, which are 256 B. Machine code of `bwx11`: `add x0, x0, #0x100`. gcc put this `add` at the start of the loop pass. So the 8 `stp` instructions use the offsets -256 to -32 [Ref1]. |
| 521 | `    } while (p < end);` | Repeats the loop while the write position is below `end`. Machine code of `bwx11`: `cmp x1, x0` and the branch `b.hi`. One loop pass is 11 instructions for 256 B: 1 `add`, 8 `stp`, 1 `cmp` and 1 branch [Ref1]. With `--bytes 256M` the first touch writes 268435456 bytes in 1048576 loop passes. The binary `bw_new` holds the same instruction text for its `k_write` [Ref3]. |
| 522 | `}` | Ends the function `k_write`. |

### Function `k_copy`: the NEON copy kernel (lines 524 to 571)

| Line | Source | Explanation |
|---:|---|---|
| 524 | `PLACE(copy);` | `PLACE(copy)` adds the pad `PAD_copy`, which is 32 bytes with the default values (line 157). |
| 525 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_copy`, the kernel `copy`: the NEON copy kernel. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 526 | `{` | Opens the body of `k_copy`. |
| 527 | `    uint64_t *dp = d;` | `dp`: the write position in the destination. It starts at `d`. |
| 528 | `    const uint64_t *sp = s;` | `sp`: the read position in the source. It starts at `s`. |
| 529 | `    const uint64_t *end = s + n;` | `end`: the first address after the source range: `s` plus `n` words. |
| 530 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 531 | `        uint64x2_t v0 = vld1q_u64(sp + 0);` | `vld1q_u64(sp + 0)` loads 16 B from the read position into the vector `v0`. These are the bytes 0 to 15 of the current source block of 256 B. |
| 532 | `        uint64x2_t v1 = vld1q_u64(sp + 2);` | Loads the bytes 16 to 31 of the source block into `v1`. |
| 533 | `        uint64x2_t v2 = vld1q_u64(sp + 4);` | Loads the bytes 32 to 47 of the source block into `v2`. |
| 534 | `        uint64x2_t v3 = vld1q_u64(sp + 6);` | Loads the bytes 48 to 63 of the source block into `v3`. |
| 535 | `        uint64x2_t v4 = vld1q_u64(sp + 8);` | Loads the bytes 64 to 79 of the source block into `v4`. |
| 536 | `        uint64x2_t v5 = vld1q_u64(sp + 10);` | Loads the bytes 80 to 95 of the source block into `v5`. |
| 537 | `        uint64x2_t v6 = vld1q_u64(sp + 12);` | Loads the bytes 96 to 111 of the source block into `v6`. |
| 538 | `        uint64x2_t v7 = vld1q_u64(sp + 14);` | Loads the bytes 112 to 127 of the source block into `v7`. |
| 539 | `        uint64x2_t v8 = vld1q_u64(sp + 16);` | Loads the bytes 128 to 143 of the source block into `v8`. |
| 540 | `        uint64x2_t v9 = vld1q_u64(sp + 18);` | Loads the bytes 144 to 159 of the source block into `v9`. |
| 541 | `        uint64x2_t v10 = vld1q_u64(sp + 20);` | Loads the bytes 160 to 175 of the source block into `v10`. |
| 542 | `        uint64x2_t v11 = vld1q_u64(sp + 22);` | Loads the bytes 176 to 191 of the source block into `v11`. |
| 543 | `        uint64x2_t v12 = vld1q_u64(sp + 24);` | Loads the bytes 192 to 207 of the source block into `v12`. |
| 544 | `        uint64x2_t v13 = vld1q_u64(sp + 26);` | Loads the bytes 208 to 223 of the source block into `v13`. |
| 545 | `        uint64x2_t v14 = vld1q_u64(sp + 28);` | Loads the bytes 224 to 239 of the source block into `v14`. |
| 546 | `        uint64x2_t v15 = vld1q_u64(sp + 30);` | Loads the bytes 240 to 255 of the source block into `v15`. One loop pass loads 256 B with 16 NEON loads of 16 B. |
| 547 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text, as in `k_read` (line 489). It adds no instruction. It names the 16 loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. So gcc must have all 16 loaded values in registers at this point. A comment in the benchmark source `bandwidth.c` of the folder `bench` reports the effect on the copy loop with gcc 14.2.0: with the statement the 8 `ldp` stand ahead of the 8 `stp`, and without it loads and stores alternate. |
| 548 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 547: the inputs `v4` to `v7`. |
| 549 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 547: the inputs `v8` to `v11`. |
| 550 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 547: the inputs `v12` to `v15`. The statement ends here. |
| 551 | `        vst1q_u64(dp + 0, v0);` | `vst1q_u64(dp + 0, v0)` stores the vector `v0` to the bytes 0 to 15 of the current destination block. So each loaded value is stored once and has no other use. |
| 552 | `        vst1q_u64(dp + 2, v1);` | Stores `v1` to the bytes 16 to 31 of the destination block. |
| 553 | `        vst1q_u64(dp + 4, v2);` | Stores `v2` to the bytes 32 to 47 of the destination block. |
| 554 | `        vst1q_u64(dp + 6, v3);` | Stores `v3` to the bytes 48 to 63 of the destination block. |
| 555 | `        vst1q_u64(dp + 8, v4);` | Stores `v4` to the bytes 64 to 79 of the destination block. |
| 556 | `        vst1q_u64(dp + 10, v5);` | Stores `v5` to the bytes 80 to 95 of the destination block. |
| 557 | `        vst1q_u64(dp + 12, v6);` | Stores `v6` to the bytes 96 to 111 of the destination block. |
| 558 | `        vst1q_u64(dp + 14, v7);` | Stores `v7` to the bytes 112 to 127 of the destination block. |
| 559 | `        vst1q_u64(dp + 16, v8);` | Stores `v8` to the bytes 128 to 143 of the destination block. |
| 560 | `        vst1q_u64(dp + 18, v9);` | Stores `v9` to the bytes 144 to 159 of the destination block. |
| 561 | `        vst1q_u64(dp + 20, v10);` | Stores `v10` to the bytes 160 to 175 of the destination block. |
| 562 | `        vst1q_u64(dp + 22, v11);` | Stores `v11` to the bytes 176 to 191 of the destination block. |
| 563 | `        vst1q_u64(dp + 24, v12);` | Stores `v12` to the bytes 192 to 207 of the destination block. |
| 564 | `        vst1q_u64(dp + 26, v13);` | Stores `v13` to the bytes 208 to 223 of the destination block. |
| 565 | `        vst1q_u64(dp + 28, v14);` | Stores `v14` to the bytes 224 to 239 of the destination block. |
| 566 | `        vst1q_u64(dp + 30, v15);` | Stores `v15` to the bytes 240 to 255 of the destination block. One loop pass stores 256 B with 16 NEON stores of 16 B. |
| 567 | `        sp += 32;` | Moves the read position forward by 32 words, which are 256 B. |
| 568 | `        dp += 32;` | Moves the write position forward by 32 words, which are 256 B. |
| 569 | `    } while (sp < end);` | Repeats the loop while the read position is below `end`. Machine code of `bwx11`, one loop pass: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.hi`. That is 20 instructions for 256 B loaded and 256 B stored. gcc joined each two neighbour loads into one `ldp` and each two neighbour stores into one `stp` [Ref1]. |
| 570 | `}` | Ends the function `k_copy`. |

### Macro `DEF_ASMREAD`: the hand-written read loop and its first six kernels (lines 572 to 615)

| Line | Source | Explanation |
|---:|---|---|
| 572 | `/*` | Opens the comment about the assembly kernels. |
| 573 | ` * asm kernels: the asm text of bench/bandwidth.c, inside macros so that an` | Comment: the kernels below hold the assembly text of the benchmark source `bandwidth.c` in the folder `bench`. From here to line 816 the loop of each kernel is assembly text inside an `__asm__` statement. gcc copies this text into the function. The text of three loops stands inside macros. |
| 574 | ` * A/A copy is the same source under a second name. Each iteration moves` | Comment: the reason for the macros: one more line then defines the same loop under a second name, an A/A copy. |
| 575 | ` * 256 B with 8 ldp/stp of q registers (16 B each). Callers guarantee n * 8` | Comment: one loop pass moves 256 B with 8 `ldp` or `stp` instructions. Each of them moves two `q` registers of 16 B. The read loop has 8 `ldp`. The write loop has 8 `stp`. The copy loop has 8 `ldp` and 8 `stp`. |
| 576 | ` * is a multiple of 256 and non-zero. v8-v15 are callee-saved in AAPCS64:` | Comment: the callers guarantee that the size in bytes is a multiple of 256 and is not 0. The loop tests the end only after a loop pass. `main` ends the program with status 2 when `--bytes` is 0 or is not a multiple of 256 (line 2550), and when the size of a `--seq` entry is not a multiple of 256 (line 2568). The next sentence: AAPCS64, the calling rules of Arm, say that a function must keep `v8` to `v15` for its caller. |
| 577 | ` * naming them as clobbers makes gcc save d8-d15 once per call, which is` | Comment: the `asm` statement names these registers as changed (clobbers). So gcc saves `d8` to `d15`, the low 8 bytes of these registers, once per call. |
| 578 | ` * outside the loop.` | Comment: this save is outside the loop. |
| 579 | ` *` | Comment: an empty line of the comment. |
| 580 | ` * DEF_ASMREAD(name, nops) puts "nops" nop instructions after the 8 ldp and` | Comment: the macro `DEF_ASMREAD(name, nops)` puts `nops` instructions of the kind `nop` after the 8 `ldp`. |
| 581 | ` * before the add (step B5). asmread and asmread2 have 0 of them.` | Comment: the `nop` instructions stand before the `add`. The comment links them to step B5 of the file `handoff.md`, the specification of the first runner. `asmread` and `asmread2` have 0 `nop`. |
| 582 | ` */` | Ends the comment. |
| 583 | `#define DEF_ASMREAD(name, nops) \` | Starts the macro `DEF_ASMREAD(name, nops)`. It defines one kernel function with a hand-written read loop. The backslash at the end of each line continues the macro on the next line. The kernel `asmread` (line 609) and every `read_nop` kernel come from this macro. |
| 584 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 130). For `asmread` and for every `read_nop` kernel the pad is 0 bytes. So each of these functions starts at a multiple of 64 bytes. |
| 585 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the first macro argument: `DEF_ASMREAD(asmread, 0)` defines the function `k_asmread`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. `noinline` forbids gcc to merge the function into its caller. So the listing of the CRB build of `bwx11` shows each kernel as a function of its own [Ref1]. |
| 586 | `    { \` | Opens the body of the kernel function. |
| 587 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 588 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx11`: `add x1, x0, x1, lsl #3`, which adds 8 times `x1` to `x0` and puts the result into `x1`. It runs once per call, before the loop [Ref1]. |
| 589 | `        __asm__ volatile( \` | Starts a gcc statement that holds assembly text. gcc copies the text into the function. `volatile` tells gcc to keep the statement, although no later code uses `p`. The listing of `bwx11` shows the instructions in the order of the text [Ref1]. |
| 590 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. `\n\t` ends one line of the assembly text and indents the next one. In the CRB binary of `bwx11` the loop of `k_asmread` and the loop of every `read_nop` kernel start at an address of 20 modulo 64 [Ref1]. |
| 591 | `            "ldp q0, q1, [%[p]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 15 of the current block of 256 B into `q0` and the bytes 16 to 31 into `q1`. `%[p]` stands for the register that gcc chose for `p`. In the listing of `bwx11` it is `x0` [Ref1]. |
| 592 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 593 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 594 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. With this instruction the bytes 0 to 127 of the block are loaded. |
| 595 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 596 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 597 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 598 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once, in rising address order. Nothing uses the loaded values: no instruction of the loop takes `q0` to `q15` as an input, and the next loop pass overwrites the registers. The old read kernel `k_oldread` (line 441) differs in this point: its source adds every loaded word to a sum (line 435). The unrolling is part of this text: 8 `ldp` per loop pass. gcc does not change the instructions of assembly text. It only puts register names in the places of `%[p]` and `%[end]`. |
| 599 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the second macro argument into text. For `read_nop4` the assembler sees the three lines `.rept 4`, `nop` and `.endr`. `.rept N` and `.endr` are assembler directives: the assembler repeats the lines between them N times. With `.rept 0` it writes nothing. So the loop of `asmread` has 0 `nop` between the last `ldp` and the `add`, and the loop of `read_nop4` has 4. A `nop` does nothing and loads nothing. So every loop pass still reads 256 B, and only the instruction count of the loop pass grows. |
| 600 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the read pointer forward by 256 B. Machine code of `bwx11`: `add x0, x0, #0x100` [Ref1]. |
| 601 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the read pointer with `end` and sets the condition flags. Machine code of `bwx11`: `cmp x0, x1` [Ref1]. |
| 602 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. `lo` means lower in an unsigned compare. The end test stands after the loop body. So the body runs at least once in every call. Instructions of one loop pass: 8 `ldp`, the `nop` instructions and these 3. That is 11 per 256 B in `asmread`, which has no `nop`. The listing of `bwx11` prints `b.cc` for this branch and names `b.lo` as another name of it [Ref1]. |
| 603 | `            : [p] "+r"(p) \` | Tells gcc which C variables the text uses. `[p] "+r"(p)`: `p` is in a general register, and the text reads it and changes it. |
| 604 | `            : [end] "r"(end) \` | `[end] "r"(end)`: `end` is an input in a general register. In the listing of `bwx11` it is `x1` [Ref1]. |
| 605 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list. It tells gcc what the text changes besides `p`. This line names the vector registers `v0` to `v7`. |
| 606 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` on the stack before the loop and loads them back after it. In the listing of `bwx11` these are 4 `stp` instructions before the loop and 4 `ldp` instructions after it [Ref1]. This save runs once per call of the kernel, not once per loop pass. With `--stop common` one call in a timed interval covers one chunk of 2 MiB (line 1279). That is 8192 loop passes. |
| 607 | `              "memory", "cc"); \` | Ends the clobber list and the statement. `"memory"` says that the text accesses memory that no operand names. `"cc"` says that the text changes the condition flags. |
| 608 | `    }` | Ends the kernel function and the macro. In `bwx11` the function `k_asmread` has 21 instructions: 5 before the loop, 11 in the loop and 5 after it, with `ret` as the last one [Ref1]. |
| 609 | `DEF_ASMREAD(asmread, 0)` | Defines `k_asmread`, the kernel `asmread`: the macro loop with 0 `nop`. One loop pass has 8 `ldp` loads of 32 B, `add`, `cmp` and the branch: 11 instructions per 256 B. In the CRB build of `bwx11` its instruction text equals the text of `k_asmread` in the benchmark binary `bw_new` [Ref1] [Ref3]. `k_read` (line 468), the new read kernel, has the same 8 `ldp` loads and the same 11 instructions per 256 B. The listing shows four differences [Ref1]. Registers: `q0` to `q15` here, `q31` to `q16` in `k_read`. Save of `d8` to `d15`, outside the loop: only here. Loop start: 20 modulo 64 here, 36 in `k_read`. End test: `cmp x0, x1` with `b.cc` here, `cmp x1, x0` with `b.hi` in `k_read`. |
| 610 | `DEF_ASMREAD(asmread2, 0)` | Defines `k_asmread2`, the A/A copy of `asmread`. The listing of the CRB build of `bwx11` shows the same instruction text for both [Ref1]. |
| 611 | `DEF_ASMREAD(read_nop4, 4)` | Defines `k_read_nop4`: the `asmread` loop with 4 `nop` per loop pass. That is 15 instructions per 256 B: 8 `ldp`, 4 `nop`, `add`, `cmp` and the branch. |
| 612 | `DEF_ASMREAD(read_nop8, 8)` | Defines `k_read_nop8`: the `asmread` loop with 8 `nop` per loop pass. That is 19 instructions per 256 B. |
| 613 | `DEF_ASMREAD(read_nop16, 16)` | Defines `k_read_nop16`: the `asmread` loop with 16 `nop` per loop pass. That is 27 instructions per 256 B. |
| 614 | `DEF_ASMREAD(read_nop32, 32)` | Defines `k_read_nop32`: the `asmread` loop with 32 `nop` per loop pass. That is 43 instructions per 256 B. |

### Function `k_read_sparse`: 128 B per loop pass, 4 loads and 9 `nop` (lines 616 to 637)

| Line | Source | Explanation |
|---:|---|---|
| 616 | `/* Step B5. Per 128 B: 4 ldp, 9 nop, add, cmp, b.lo. That is 16 instructions` | Comment: the kernel below belongs to step B5 of the file `handoff.md`, the specification of the first runner. Per 128 B it has 4 `ldp`, 9 `nop`, `add`, `cmp` and `b.lo`. That is 16 instructions. |
| 617 | ` * per 128 B, as the old read loop has, and no vector add. */` | Comment: the old read loop also has 16 instructions per 128 B. This kernel has the same instruction count, and it has no vector add. |
| 618 | `PLACE(read_sparse);` | `PLACE` adds the pad of the kernel `read_sparse`. It is the pad of `asmread`, 0 bytes (line 217). |
| 619 | `__attribute__((noinline)) static void k_read_sparse(const uint64_t *a, size_t n)` | Starts the function `k_read_sparse`, the kernel `read_sparse`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 620 | `{` | Opens the body of `k_read_sparse`. |
| 621 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 622 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. |
| 623 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text of the loop. |
| 624 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx11` the loop starts 4 bytes after the function start, at an address of 4 modulo 64 [Ref1]. |
| 625 | `        "ldp q0, q1, [%[p]]\n\t"` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current block of 128 B into `q0` and `q1`. |
| 626 | `        "ldp q2, q3, [%[p], #32]\n\t"` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 627 | `        "ldp q4, q5, [%[p], #64]\n\t"` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 628 | `        "ldp q6, q7, [%[p], #96]\n\t"` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. One loop pass has 4 load instructions. It reads 128 B, each byte once. Nothing uses the loaded values. |
| 629 | `        ".rept 9\n\tnop\n\t.endr\n\t"` | The assembler writes the instruction `nop` 9 times here. A `nop` does nothing. |
| 630 | `        "add %[p], %[p], #128\n\t"` | Moves the read pointer forward by 128 B. |
| 631 | `        "cmp %[p], %[end]\n\t"` | Compares the read pointer with `end`. |
| 632 | `        "b.lo 1b\n\t"` | Branches back to the label `1` while the pointer is below `end`. One loop pass is 16 instructions per 128 B: 4 `ldp`, 9 `nop`, `add`, `cmp` and the branch. |
| 633 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 634 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 635 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc");` | The clobber list: the vector registers `v0` to `v7`, memory and the condition flags. It names none of `v8` to `v15`. So gcc saves no register in this function. The listing of `bwx11` shows one `add` before the loop and one `ret` after it [Ref1]. |
| 636 | `}` | Ends the function `k_read_sparse`. |

### Macro `DEF_ASMWRITE`: the hand-written write loop, kernels `asmwrite` and `asmwrite2` (lines 638 to 664)

| Line | Source | Explanation |
|---:|---|---|
| 638 | `#define DEF_ASMWRITE(name) \` | Starts the macro `DEF_ASMWRITE(name)`. It defines one kernel function with a hand-written write loop. The backslash at the end of each line continues the macro on the next line. |
| 639 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 130). |
| 640 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. |
| 641 | `    { \` | Opens the body of the kernel function. |
| 642 | `        uint64_t *p = a; \` | `p`: the write pointer. It starts at `a`. |
| 643 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 644 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. gcc copies the text into the function. |
| 645 | `            "dup v0.2d, %[v]\n\t" \` | `dup` copies the 8-byte value `v` into both halves of the 16-byte vector register `v0`. It stands before the loop label, so it runs once per call. `%[v]` stands for the register that gcc chose for `v`. |
| 646 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx11` the loop of `k_asmwrite` starts at an address of 40 modulo 64 [Ref1]. |
| 647 | `            "stp q0, q0, [%[p]]\n\t" \` | `stp` stores two 16-byte vector registers to memory, which is 32 B. Here both are `q0`. This instruction writes the bytes 0 to 31 of the current block of 256 B. `%[p]` stands for the register of the write pointer `p`. |
| 648 | `            "stp q0, q0, [%[p], #32]\n\t" \` | Stores `q0` twice to the bytes 32 to 63 of the block. |
| 649 | `            "stp q0, q0, [%[p], #64]\n\t" \` | Stores `q0` twice to the bytes 64 to 95 of the block. |
| 650 | `            "stp q0, q0, [%[p], #96]\n\t" \` | Stores `q0` twice to the bytes 96 to 127 of the block. |
| 651 | `            "stp q0, q0, [%[p], #128]\n\t" \` | Stores `q0` twice to the bytes 128 to 159 of the block. |
| 652 | `            "stp q0, q0, [%[p], #160]\n\t" \` | Stores `q0` twice to the bytes 160 to 191 of the block. |
| 653 | `            "stp q0, q0, [%[p], #192]\n\t" \` | Stores `q0` twice to the bytes 192 to 223 of the block. |
| 654 | `            "stp q0, q0, [%[p], #224]\n\t" \` | Stores `q0` twice to the bytes 224 to 255 of the block. One loop pass has 8 store instructions. It writes 256 B, each byte once, in rising address order. The unrolling is part of this text: 8 `stp` per loop pass. |
| 655 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the write pointer forward by 256 B. |
| 656 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the write pointer with `end`. |
| 657 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 658 | `            : [p] "+r"(p) \` | `[p] "+r"(p)`: `p` is in a general register. The text reads it and changes it. |
| 659 | `            : [end] "r"(end), [v] "r"(v) \` | `end` and `v` are inputs in general registers. |
| 660 | `            : "v0", "memory", "cc"); \` | The clobber list: the text changes the vector register `v0`, memory and the condition flags. The calling rules do not require a function to keep `v0`. So gcc saves no register in this function. |
| 661 | `    }` | Ends the kernel function and the macro. |
| 662 | `DEF_ASMWRITE(asmwrite)` | Defines `k_asmwrite`, the kernel `asmwrite`. Machine code in `bwx11`: one loop pass is 11 instructions for 256 B: 8 `stp`, `add x0, x0, #0x100`, `cmp x0, x1` and `b.cc`. Before the loop stand the `add` that computes the end address and the `dup`. After it stands `ret` [Ref1]. The first touch uses `k_write` (line 498), not this loop. |
| 663 | `DEF_ASMWRITE(asmwrite2)` | Defines `k_asmwrite2`, the A/A copy of `asmwrite`. The listing of the CRB build of `bwx11` shows the same instruction text for both [Ref1]. |

### Macro `DEF_ASMCOPY`: the hand-written copy loop, kernels `asmcopy` and `asmcopy2` (lines 665 to 702)

| Line | Source | Explanation |
|---:|---|---|
| 665 | `#define DEF_ASMCOPY(name) \` | Starts the macro `DEF_ASMCOPY(name)`. It defines one kernel function with a hand-written copy loop. |
| 666 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 130). |
| 667 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. `noinline`: gcc must keep the function separate from its caller. |
| 668 | `    { \` | Opens the body of the kernel function. |
| 669 | `        uint64_t *dp = d; \` | `dp`: the write pointer in the destination. It starts at `d`. |
| 670 | `        const uint64_t *sp = s; \` | `sp`: the read pointer in the source. It starts at `s`. |
| 671 | `        const uint64_t *end = s + n; \` | `end`: the first address after the source range: `s` plus `n` words. |
| 672 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 673 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx11` the loop of `k_asmcopy` starts at an address of 52 modulo 64 [Ref1]. |
| 674 | `            "ldp q0, q1, [%[s]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. `%[s]` stands for the register of the read pointer `sp`. |
| 675 | `            "ldp q2, q3, [%[s], #32]\n\t" \` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 676 | `            "ldp q4, q5, [%[s], #64]\n\t" \` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 677 | `            "ldp q6, q7, [%[s], #96]\n\t" \` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 678 | `            "ldp q8, q9, [%[s], #128]\n\t" \` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 679 | `            "ldp q10, q11, [%[s], #160]\n\t" \` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 680 | `            "ldp q12, q13, [%[s], #192]\n\t" \` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 681 | `            "ldp q14, q15, [%[s], #224]\n\t" \` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 load instructions for 256 B. |
| 682 | `            "stp q0, q1, [%[d]]\n\t" \` | `stp` stores two 16-byte vector registers to memory: `q0` and `q1` to the bytes 0 to 31 of the current destination block. `%[d]` stands for the register of the write pointer `dp`. Each loaded register is stored once and has no other use. |
| 683 | `            "stp q2, q3, [%[d], #32]\n\t" \` | Stores `q2` and `q3` to the bytes 32 to 63 of the destination block. |
| 684 | `            "stp q4, q5, [%[d], #64]\n\t" \` | Stores `q4` and `q5` to the bytes 64 to 95 of the destination block. |
| 685 | `            "stp q6, q7, [%[d], #96]\n\t" \` | Stores `q6` and `q7` to the bytes 96 to 127 of the destination block. |
| 686 | `            "stp q8, q9, [%[d], #128]\n\t" \` | Stores `q8` and `q9` to the bytes 128 to 159 of the destination block. |
| 687 | `            "stp q10, q11, [%[d], #160]\n\t" \` | Stores `q10` and `q11` to the bytes 160 to 191 of the destination block. |
| 688 | `            "stp q12, q13, [%[d], #192]\n\t" \` | Stores `q12` and `q13` to the bytes 192 to 223 of the destination block. |
| 689 | `            "stp q14, q15, [%[d], #224]\n\t" \` | Stores `q14` and `q15` to the bytes 224 to 255 of the destination block. One loop pass has 8 store instructions for 256 B. The unrolling is part of this text: 8 `ldp` and 8 `stp` per loop pass. |
| 690 | `            "add %[s], %[s], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 691 | `            "add %[d], %[d], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 692 | `            "cmp %[s], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 693 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the read pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 694 | `            : [s] "+r"(sp), [d] "+r"(dp) \` | `sp` and `dp` are in general registers. The text reads them and changes them. |
| 695 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 696 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 697 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop, as in the read loop of line 606. |
| 698 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 699 | `    }` | Ends the kernel function and the macro. |
| 700 | `DEF_ASMCOPY(asmcopy)` | Defines `k_asmcopy`, the kernel `asmcopy`. Machine code in `bwx11`: one loop pass is 20 instructions for 256 B loaded and 256 B stored: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.cc`. The function saves `d8` to `d15` before the loop and loads them back after it [Ref1]. |
| 701 | `DEF_ASMCOPY(asmcopy2)` | Defines `k_asmcopy2`, the A/A copy of `asmcopy`. The listing of the CRB build of `bwx11` shows the same instruction text for both [Ref1]. |

### Function `k_asmcopy_c`: the machine code of the C copy loop as assembly text (lines 703 to 743)

| Line | Source | Explanation |
|---:|---|---|
| 703 | `/*` | Opens the comment about the kernel `asmcopy_c`. |
| 704 | ` * Step B2. asmcopy_c: the loop is the machine code of the C copy loop, from` | Comment: the kernel belongs to step B2 of the file `handoff.md`, the specification of the first runner. Its loop is the machine code of the C copy loop, written as assembly text. |
| 705 | ` * the listing "bw_new k_copy" of probe.txt: same instruction order, same` | Comment: the machine code comes from the listing `bw_new k_copy` of the file `probe.txt` [Ref3]. The loop has the same order of instructions. |
| 706 | ` * offsets, registers q16 to q31, and "cmp end, s; b.hi" as its loop end. The` | Comment: it also has the same offsets and the same registers `q16` to `q31`. Its loop end is `cmp end, s` followed by `b.hi`. |
| 707 | ` * three pointers are bound to x0, x1 and x2, the registers of that listing.` | Comment: the three pointers are bound to the registers `x0`, `x1` and `x2`, the registers of that listing. In the listing of `bwx11` the functions `k_asmcopy_c` and `k_copy` have the same instruction text [Ref1]. |
| 708 | ` */` | Ends the comment. |
| 709 | `PLACE(asmcopy_c);` | `PLACE` adds the pad `PAD_asmcopy_c`, which is 48 bytes with the default values (line 166). |
| 710 | `__attribute__((noinline)) static void k_asmcopy_c(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c`, the kernel `asmcopy_c`. It copies `n` 8-byte words from `s` to `d`. |
| 711 | `{` | Opens the body of `k_asmcopy_c`. |
| 712 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer. `register ... __asm__("x0")` binds this C variable to the register `x0` for the `asm` statement below. |
| 713 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 714 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 715 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 716 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx11` the loop starts 4 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 717 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 718 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 719 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 720 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 721 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 722 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 723 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 724 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 725 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. In this kernel the `add` stands before the stores. |
| 726 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 727 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 728 | `        "stp q29, q28, [%[d], #-224]\n\t"` | Stores `q29` and `q28` at the offset -224 from the moved write pointer. These are the bytes 32 to 63 of the destination block. |
| 729 | `        "stp q27, q26, [%[d], #-192]\n\t"` | Stores `q27` and `q26` at the offset -192: the bytes 64 to 95 of the destination block. |
| 730 | `        "stp q25, q24, [%[d], #-160]\n\t"` | Stores `q25` and `q24` at the offset -160: the bytes 96 to 127 of the destination block. |
| 731 | `        "stp q23, q22, [%[d], #-128]\n\t"` | Stores `q23` and `q22` at the offset -128: the bytes 128 to 159 of the destination block. |
| 732 | `        "stp q21, q20, [%[d], #-96]\n\t"` | Stores `q21` and `q20` at the offset -96: the bytes 160 to 191 of the destination block. |
| 733 | `        "stp q19, q18, [%[d], #-64]\n\t"` | Stores `q19` and `q18` at the offset -64: the bytes 192 to 223 of the destination block. |
| 734 | `        "stp q17, q16, [%[d], #-32]\n\t"` | Stores `q17` and `q16` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 735 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 736 | `        "b.hi 1b\n\t"` | `b.hi 1b` branches back to the label `1` while `end` is higher than the read pointer, as unsigned numbers. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 737 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 738 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 739 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 740 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. The calling rules do not require a function to keep `v16` to `v31`. So gcc saves no register in this function. |
| 741 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 742 | `}` | Ends the function `k_asmcopy_c`. |

### Function `k_asmcopy_c_add`: the same loop with both `add` after the stores (lines 744 to 780)

| Line | Source | Explanation |
|---:|---|---|
| 744 | `/* As asmcopy_c, but the two add stand after the 8 stp, and the 8 stp use the` | Comment: the kernel below is `asmcopy_c` with two changes. The two `add` instructions stand after the 8 `stp`. |
| 745 | ` * offsets 0 to 224, as in asmcopy. Registers stay q16 to q31. */` | Comment: the 8 `stp` use the offsets 0 to 224, as in `asmcopy`. The registers stay `q16` to `q31`. |
| 746 | `PLACE(asmcopy_c_add);` | `PLACE` adds the pad `PAD_asmcopy_c_add`, which is 48 bytes with the default values (line 169). |
| 747 | `__attribute__((noinline)) static void k_asmcopy_c_add(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_add`, the kernel `asmcopy_c_add`. It copies `n` 8-byte words from `s` to `d`. |
| 748 | `{` | Opens the body of `k_asmcopy_c_add`. |
| 749 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 750 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 751 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 752 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 753 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx11` the loop starts at an address of 52 modulo 64 [Ref1]. |
| 754 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 755 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 756 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 757 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 758 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 759 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 760 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 761 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 762 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 763 | `        "stp q29, q28, [%[d], #32]\n\t"` | Stores `q29` and `q28` to the bytes 32 to 63 of the destination block. |
| 764 | `        "stp q27, q26, [%[d], #64]\n\t"` | Stores `q27` and `q26` to the bytes 64 to 95 of the destination block. |
| 765 | `        "stp q25, q24, [%[d], #96]\n\t"` | Stores `q25` and `q24` to the bytes 96 to 127 of the destination block. |
| 766 | `        "stp q23, q22, [%[d], #128]\n\t"` | Stores `q23` and `q22` to the bytes 128 to 159 of the destination block. |
| 767 | `        "stp q21, q20, [%[d], #160]\n\t"` | Stores `q21` and `q20` to the bytes 160 to 191 of the destination block. |
| 768 | `        "stp q19, q18, [%[d], #192]\n\t"` | Stores `q19` and `q18` to the bytes 192 to 223 of the destination block. |
| 769 | `        "stp q17, q16, [%[d], #224]\n\t"` | Stores `q17` and `q16` to the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 770 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. Here both `add` instructions stand after the stores. |
| 771 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. |
| 772 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 773 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 774 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 775 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 776 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 777 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. gcc saves no register for them. |
| 778 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 779 | `}` | Ends the function `k_asmcopy_c_add`. |

### Function `k_asmcopy_c_reg`: the same loop with the registers `q0` to `q15` (lines 781 to 817)

| Line | Source | Explanation |
|---:|---|---|
| 781 | `/* As asmcopy_c, but with the registers q0 to q15 (q31 becomes q0, q30` | Comment: the kernel below is `asmcopy_c` with other registers: `q0` to `q15`. The register `q31` of `asmcopy_c` becomes `q0` here. |
| 782 | ` * becomes q1, and so on), and d8 to d15 named as clobbered, as in asmcopy. */` | Comment: `q30` becomes `q1`, and so on. The clobber list names `v8` to `v15`, as in `asmcopy`. So gcc saves `d8` to `d15`. |
| 783 | `PLACE(asmcopy_c_reg);` | `PLACE` adds the pad `PAD_asmcopy_c_reg`, which is 32 bytes with the default values (line 172). |
| 784 | `__attribute__((noinline)) static void k_asmcopy_c_reg(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_reg`, the kernel `asmcopy_c_reg`. It copies `n` 8-byte words from `s` to `d`. |
| 785 | `{` | Opens the body of `k_asmcopy_c_reg`. |
| 786 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 787 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 788 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 789 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 790 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx11` the loop starts 20 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 791 | `        "ldp q0, q1, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. |
| 792 | `        "ldp q2, q3, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 793 | `        "ldp q4, q5, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 794 | `        "ldp q6, q7, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 795 | `        "ldp q8, q9, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 796 | `        "ldp q10, q11, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 797 | `        "ldp q12, q13, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 798 | `        "ldp q14, q15, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 `ldp` for 256 B. |
| 799 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B, before the stores. |
| 800 | `        "stp q0, q1, [%[d]]\n\t"` | Stores `q0` and `q1` to the bytes 0 to 31 of the current destination block. |
| 801 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 802 | `        "stp q2, q3, [%[d], #-224]\n\t"` | Stores `q2` and `q3` at the offset -224 from the moved write pointer: the bytes 32 to 63 of the destination block. |
| 803 | `        "stp q4, q5, [%[d], #-192]\n\t"` | Stores `q4` and `q5` at the offset -192: the bytes 64 to 95 of the destination block. |
| 804 | `        "stp q6, q7, [%[d], #-160]\n\t"` | Stores `q6` and `q7` at the offset -160: the bytes 96 to 127 of the destination block. |
| 805 | `        "stp q8, q9, [%[d], #-128]\n\t"` | Stores `q8` and `q9` at the offset -128: the bytes 128 to 159 of the destination block. |
| 806 | `        "stp q10, q11, [%[d], #-96]\n\t"` | Stores `q10` and `q11` at the offset -96: the bytes 160 to 191 of the destination block. |
| 807 | `        "stp q12, q13, [%[d], #-64]\n\t"` | Stores `q12` and `q13` at the offset -64: the bytes 192 to 223 of the destination block. |
| 808 | `        "stp q14, q15, [%[d], #-32]\n\t"` | Stores `q14` and `q15` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 809 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 810 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 811 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 812 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 813 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 814 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call: the listing of `bwx11` shows 4 `stp` before the loop and 4 `ldp` after it [Ref1]. |
| 815 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 816 | `}` | Ends the function `k_asmcopy_c_reg`. |

### Stand-ins for a machine that is not AArch64 (lines 818 to 864)

| Line | Source | Explanation |
|---:|---|---|
| 818 | `#else` | `#else` of the `#if defined(__aarch64__)` of line 458. The compiler reads lines 819 to 863 only for a machine that is not AArch64. A build on CRB, an Arm machine, does not compile these lines. |
| 819 | `/*` | Opens the comment about the stand-ins. |
| 820 | ` * Stand-ins for a machine that is not AArch64: plain C loops that touch` | Comment: the stand-ins are for a machine that is not AArch64. They are plain C loops. |
| 821 | ` * exactly the same bytes as the real kernels. They exist only so that the` | Comment: each stand-in touches exactly the same bytes as the real kernel. The stand-ins have one purpose only. |
| 822 | ` * harness can be compiled and run on the development machine.` | Comment: the purpose: the program can be compiled and run on the development machine. |
| 823 | ` */` | Ends the comment. |
| 824 | `#define STANDIN 1` | `STANDIN` is 1 in this branch. It is 0 in the AArch64 branch (line 459). The header of the output then says that the kernels are stand-ins and that the rates mean nothing (line 2601). |
| 825 | `#define DEF_ASMREAD(name, nops) \` | Starts the stand-in form of the macro `DEF_ASMREAD(name, nops)`. It has the name and the arguments of the AArch64 macro of line 583, with a plain C loop over the same range. A build on CRB, an Arm machine, does not compile this branch. |
| 826 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel, as in the AArch64 branch. |
| 827 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range and `n` its length in 8-byte words. |
| 828 | `    { \` | Opens the body of the kernel function. |
| 829 | `        const volatile uint64_t *p = a; \` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 830 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 831 | `            (void)p[i]; \` | Reads word `i` and drops the value. The cast to `void` says that the value is not used. So the loop reads every word of the range once. The macro argument `nops` is not used in this branch. |
| 832 | `    }` | Ends the kernel function and the macro. |
| 833 | `#define DEF_ASMWRITE(name) \` | Starts the stand-in form of the macro `DEF_ASMWRITE(name)`, with a plain C loop. |
| 834 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 835 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores `v` to `n` 8-byte words, from the address `a` on. |
| 836 | `    { \` | Opens the body of the kernel function. |
| 837 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 838 | `            a[i] = v; \` | Stores `v` to word `i`. |
| 839 | `    }` | Ends the kernel function and the macro. |
| 840 | `#define DEF_ASMCOPY(name) \` | Starts the stand-in form of the macro `DEF_ASMCOPY(name)`, with a plain C loop. |
| 841 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 842 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. |
| 843 | `    { \` | Opens the body of the kernel function. |
| 844 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 845 | `            d[i] = s[i]; \` | Copies word `i` from the source to the destination. |
| 846 | `    }` | Ends the kernel function and the macro. |
| 847 | `DEF_ASMREAD(read, 0)` | Stand-in build only: defines `k_read` as the plain read loop of lines 825 to 832. This line and the 16 lines below define all 17 kernels of lines 467 to 816 from the three stand-in macros. |
| 848 | `DEF_ASMWRITE(write)` | Stand-in build only: defines `k_write` as the plain write loop of lines 833 to 839. In such a build this function also does the first touch (line 1230). |
| 849 | `DEF_ASMCOPY(copy)` | Stand-in build only: defines `k_copy` as the plain copy loop of lines 840 to 846. |
| 850 | `DEF_ASMREAD(asmread, 0)` | Stand-in build only: defines `k_asmread` as the plain read loop. |
| 851 | `DEF_ASMREAD(asmread2, 0)` | Stand-in build only: defines `k_asmread2` as the plain read loop. |
| 852 | `DEF_ASMREAD(read_nop4, 4)` | Stand-in build only: defines `k_read_nop4` as the plain read loop. The stand-in macro does not use the number 4. |
| 853 | `DEF_ASMREAD(read_nop8, 8)` | Stand-in build only: defines `k_read_nop8` as the plain read loop. The number 8 is not used. |
| 854 | `DEF_ASMREAD(read_nop16, 16)` | Stand-in build only: defines `k_read_nop16` as the plain read loop. The number 16 is not used. |
| 855 | `DEF_ASMREAD(read_nop32, 32)` | Stand-in build only: defines `k_read_nop32` as the plain read loop. The number 32 is not used. |
| 856 | `DEF_ASMREAD(read_sparse, 9)` | Stand-in build only: defines `k_read_sparse` as the plain read loop. The number 9 is not used. The real kernel also reads every byte of its range. |
| 857 | `DEF_ASMWRITE(asmwrite)` | Stand-in build only: defines `k_asmwrite` as the plain write loop. |
| 858 | `DEF_ASMWRITE(asmwrite2)` | Stand-in build only: defines `k_asmwrite2` as the plain write loop. |
| 859 | `DEF_ASMCOPY(asmcopy)` | Stand-in build only: defines `k_asmcopy` as the plain copy loop. |
| 860 | `DEF_ASMCOPY(asmcopy2)` | Stand-in build only: defines `k_asmcopy2` as the plain copy loop. |
| 861 | `DEF_ASMCOPY(asmcopy_c)` | Stand-in build only: defines `k_asmcopy_c` as the plain copy loop. |
| 862 | `DEF_ASMCOPY(asmcopy_c_add)` | Stand-in build only: defines `k_asmcopy_c_add` as the plain copy loop. |
| 863 | `DEF_ASMCOPY(asmcopy_c_reg)` | Stand-in build only: defines `k_asmcopy_c_reg` as the plain copy loop. |
| 864 | `#endif` | Ends the `#if` of line 458. |

### Kernels of round 3 (version `bwx10`): the comment and the pads (lines 865 to 897)

| Line | Source | Explanation |
|---:|---|---|
| 865 | `/* bwx10+ */` | Comment: a marker. A block of text that the version `bwx10` added starts here. The marker of line 1007 ends the block. |
| 867 | `/*` | Opens the comment about the kernels of round 3. |
| 868 | ` * Kernels of round 3. They stand after every kernel of bwx8, so those keep` | Comment: the kernels below are those of round 3, a round of work on the program (line 29). It is not a round of the option `--rounds`. They stand after every kernel of `bwx8`. |
| 869 | ` * their place. Each one is a read kernel (T_READ) with the loop start at 20` | Comment: so the kernels of `bwx8` keep their place in the binary. Each new kernel is a read kernel, with the type `T_READ`. Its loop must start at 20 modulo 64. |
| 870 | ` * modulo 64, the loop offset of asmread in the accepted build.` | Comment: 20 modulo 64 is the loop offset of `asmread` in the accepted build. The accepted build is the CRB build whose machine-code listing passed the check script. |
| 871 | ` *` | Comment: an empty line of the comment. |
| 872 | ` * read_pf256, read_pf512, read_pf1024, read_pf2048 have the frame of asmread` | Comment: the kernels `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048` (lines 946 to 949) have the frame of `asmread`. The frame is the code at the start of a function that saves registers. |
| 873 | ` * (d8-d15 are saved), so HEAD is 20 and the pad is the pad of asmread.` | Comment: in that frame `d8` to `d15` are saved. So `HEAD`, the number of bytes of code before the loop, is 20, and these kernels take the pad of `asmread`. |
| 874 | ` * read_1pl names v0-v3 only, so gcc saves nothing: HEAD is 4, as read_sparse` | Comment: `read_1pl` names only `v0` to `v3` as changed. So gcc saves nothing. `HEAD` is then 4, as for `read_sparse`. |
| 875 | ` * has it. HEAD_read_1pl is a guess until the listing of the CRB build` | Comment: `HEAD_read_1pl` is a guess until the listing of the CRB build confirms it. The listing of the CRB build of `bwx11` confirms it: 4 bytes of code stand before the loop of `k_read_1pl` [Ref1]. |
| 876 | ` * confirms it (check_listing10.py checks the loop offset).` | Comment: the script `check_listing10.py` in the code folder `bwx10-2026-11-15` checks the loop offset. |
| 877 | ` */` | Ends the comment. |
| 878 | `#ifndef PAD_read_pf256` | Compiles line 879 only when the build command has not defined `PAD_read_pf256`. A `-D` option of the compiler could give another value. The CRB build of `bwx11` has no `-D` option [Ref2]. |
| 879 | `#define PAD_read_pf256 PAD_asmread` | `PAD_read_pf256`: the pad of `asmread`, which is 0 bytes. |
| 880 | `#endif` | Ends the `#ifndef` of line 878. |
| 881 | `#ifndef PAD_read_pf512` | Compiles line 882 only when the build command has not defined `PAD_read_pf512`. |
| 882 | `#define PAD_read_pf512 PAD_asmread` | `PAD_read_pf512`: the pad of `asmread`, which is 0 bytes. |
| 883 | `#endif` | Ends the `#ifndef` of line 881. |
| 884 | `#ifndef PAD_read_pf1024` | Compiles line 885 only when the build command has not defined `PAD_read_pf1024`. |
| 885 | `#define PAD_read_pf1024 PAD_asmread` | `PAD_read_pf1024`: the pad of `asmread`, which is 0 bytes. |
| 886 | `#endif` | Ends the `#ifndef` of line 884. |
| 887 | `#ifndef PAD_read_pf2048` | Compiles line 888 only when the build command has not defined `PAD_read_pf2048`. |
| 888 | `#define PAD_read_pf2048 PAD_asmread` | `PAD_read_pf2048`: the pad of `asmread`, which is 0 bytes. |
| 889 | `#endif` | Ends the `#ifndef` of line 887. |
| 890 | `#define LOOP_read_1pl 20` | `LOOP_read_1pl` is 20: the planned address of the loop start of `read_1pl`, modulo 64. |
| 891 | `#ifndef HEAD_read_1pl` | Compiles line 892 only when the build command has not defined `HEAD_read_1pl`. |
| 892 | `#define HEAD_read_1pl 4` | `HEAD_read_1pl` is 4: the number of bytes between the function start and the loop start. That is one instruction of 4 bytes. Listing of the CRB build of `bwx11`: `k_read_1pl` starts at `0x4e90`, which is 16 modulo 64. Its loop starts at `0x4e94`, which is 20 modulo 64 [Ref1]. |
| 893 | `#endif` | Ends the `#ifndef` of line 891. |
| 894 | `#ifndef PAD_read_1pl` | Compiles line 895 only when the build command has not defined `PAD_read_1pl`. |
| 895 | `#define PAD_read_1pl PADOF(LOOP_read_1pl, HEAD_read_1pl)` | `PAD_read_1pl` is `PADOF(20, 4)` with the default values. `PADOF` (line 131) computes (20 - 4) modulo 64, which is 16. `PLACE(read_1pl)` (line 954) uses this pad. So the function starts at 16 modulo 64 and its loop at 20 modulo 64. In the CRB binary of `bwx11` the kernel `read_1pl` has the same loop offset as `asmread`: 20 [Ref1]. |
| 896 | `#endif` | Ends the `#ifndef` of line 894. |

### Macro `DEF_READ_PF`: the `asmread` loop with four prefetch instructions (lines 898 to 950)

| Line | Source | Explanation |
|---:|---|---|
| 898 | `#if defined(__aarch64__)` | Opens a second block of AArch64 kernels. Its `#else` is at line 972 and its `#endif` at line 989. The CRB binary of `bwx11` holds this first branch: the listing shows the `prfm` and `ldr` instructions of its kernels [Ref1]. |
| 899 | `/*` | Opens the comment about the macro `DEF_READ_PF`. |
| 900 | ` * DEF_READ_PF(name, d0, d1, d2, d3): the loop of asmread (8 ldp of q` | Comment: `DEF_READ_PF(name, d0, d1, d2, d3)` defines a kernel with the loop of `asmread`: 8 `ldp` of `q` registers per 256 B. |
| 901 | ` * registers per 256 B, same registers, same clobbers) plus four software` | Comment: the loop has the same registers and the same clobber list as `asmread`. The macro adds four software prefetches. |
| 902 | ` * prefetches per iteration, one per 64 B line, after the 8 ldp and before the` | Comment: the four prefetches run once per loop pass, one per 64 B line. A 64 B line here is a block of 64 B of memory, a cache line. They stand after the 8 `ldp` and before the `add`. |
| 903 | ` * add. d0 is the prefetch distance D in bytes ahead of the block that the` | Comment: `d0` is the prefetch distance D in bytes: the offset of the first prefetched 64 B line from the start of the block that the loop pass loads. |
| 904 | ` * iteration loads. d1, d2, d3 are D + 64, D + 128, D + 192.` | Comment: `d1`, `d2` and `d3` are D + 64, D + 128 and D + 192. So the four prefetches name four neighbour 64 B lines. |
| 905 | ` *` | Comment: an empty line of the comment. |
| 906 | ` * prfm pldl1keep asks for the line in the first-level data cache (PLD: for a` | Comment: the instruction `prfm pldl1keep` asks the CPU to bring a 64 B line into the first-level data cache. It loads no data into a register. `PLD` in its name means: for a load. |
| 907 | ` * load, L1: first level, KEEP: normal, not streaming). The form` | Comment: `L1` means the first cache level. `KEEP` means normal use, not streaming. The sentence about the address form starts here. |
| 908 | ` * [base, #offset] needs an offset that is a multiple of 8 from 0 to 32760.` | Comment: the address form `[base, #offset]` needs an offset that is a multiple of 8 from 0 to 32760. |
| 909 | ` * In the last iterations of a pass the prefetch address lies past the end of` | Comment: in the last loop passes of a call the prefetch address lies past the end of the range. |
| 910 | ` * the range, and for the last range of the buffer past the end of the` | Comment: for the last range of the buffer the prefetch address lies past the end of the buffer. |
| 911 | ` * buffer. That is allowed: prfm never faults, not even on an address that is` | Comment: that is allowed. A `prfm` never causes a fault, not even with an address that is not mapped. |
| 912 | ` * not mapped. It reads no data, so the kernel touches the same bytes as` | Comment: a `prfm` reads no data. So the kernel touches the same bytes as `asmread`. |
| 913 | ` * asmread.` | Comment: the last word of the sentence of line 912. |
| 914 | ` */` | Ends the comment. |
| 915 | `#define DEF_READ_PF(name, d0, d1, d2, d3) \` | Starts the macro `DEF_READ_PF(name, d0, d1, d2, d3)`. Its text is the text of `DEF_ASMREAD` (line 583) with four `prfm` instructions in place of the `nop` text. |
| 916 | `    _Static_assert((d0) % 8 == 0 && (d0) >= 0 && (d1) == (d0) + 64 && (d2) == (d0) + 128 && (d3) == (d0) + 192 && \` | `_Static_assert` stops the compilation when the four offsets break the rule of the comment. This line tests that `d0` is a multiple of 8 and not negative, and that `d1`, `d2` and `d3` are `d0` plus 64, 128 and 192. |
| 917 | `                   (d3) <= 32760, "prfm offsets: multiples of 8 from 0 to 32760, one per 64 B line"); \` | Continues the test of line 916: `d3` must be at most 32760. The text in quotes is the error message of the compiler. |
| 918 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function. For the four kernels below it is 0 bytes (lines 878 to 889). |
| 919 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 920 | `    { \` | Opens the body of the kernel function. |
| 921 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 922 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 923 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 924 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx11` the loops of the four kernels start at 20 modulo 64, the loop offset of `k_asmread` [Ref1]. |
| 925 | `            "ldp q0, q1, [%[p]]\n\t" \` | Loads the bytes 0 to 31 of the current block of 256 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 926 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 927 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 928 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. |
| 929 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 930 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 931 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 932 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once. Nothing uses the loaded values. |
| 933 | `            "prfm pldl1keep, [%[p], #" #d0 "]\n\t" \` | The first prefetch: `prfm pldl1keep` asks the CPU to bring the 64 B line at the address `p` plus `d0` into the first-level data cache. `#d0` puts the macro argument into the text as a number. The instruction loads no data into a register. |
| 934 | `            "prfm pldl1keep, [%[p], #" #d1 "]\n\t" \` | The second prefetch: the 64 B line at the address `p` plus `d1`, which is 64 B after the first one. |
| 935 | `            "prfm pldl1keep, [%[p], #" #d2 "]\n\t" \` | The third prefetch: the 64 B line at the address `p` plus `d2`. |
| 936 | `            "prfm pldl1keep, [%[p], #" #d3 "]\n\t" \` | The fourth prefetch: the 64 B line at the address `p` plus `d3`. So one loop pass prefetches four neighbour 64 B lines, which are 256 B. |
| 937 | `            "add %[p], %[p], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 938 | `            "cmp %[p], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 939 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. One loop pass is 15 instructions per 256 B: 8 `ldp`, 4 `prfm`, `add`, `cmp` and the branch. |
| 940 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 941 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 942 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 943 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop, as in `asmread`. |
| 944 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 945 | `    }` | Ends the kernel function and the macro. |
| 946 | `DEF_READ_PF(read_pf256, 256, 320, 384, 448)` | Defines `k_read_pf256`, the kernel `read_pf256`. The number in the name is `d0` in bytes. The four prefetch offsets are 256, 320, 384 and 448: the four 64 B lines of the block after the current one. |
| 947 | `DEF_READ_PF(read_pf512, 512, 576, 640, 704)` | Defines `k_read_pf512`, the kernel `read_pf512`. The four prefetch offsets are 512, 576, 640 and 704: the block 512 B after the start of the current one. |
| 948 | `DEF_READ_PF(read_pf1024, 1024, 1088, 1152, 1216)` | Defines `k_read_pf1024`, the kernel `read_pf1024`. The four prefetch offsets are 1024, 1088, 1152 and 1216. |
| 949 | `DEF_READ_PF(read_pf2048, 2048, 2112, 2176, 2240)` | Defines `k_read_pf2048`, the kernel `read_pf2048`. The four prefetch offsets are 2048, 2112, 2176 and 2240. |

### Function `k_read_1pl`: one load of 16 B per 64 B line (lines 951 to 971)

| Line | Source | Explanation |
|---:|---|---|
| 951 | `/* read_1pl, "one load per line". Per 256 B: four loads of 16 B, one at the` | Comment: the name `read_1pl` means one load per line. A line here is a 64 B line, a block of 64 B of memory (a cache line). Per 256 B the loop has four loads of 16 B. |
| 952 | ` * start of each 64 B line, then add, cmp, b.lo. It reads bytes 0 to 15 of` | Comment: one load stands at the start of each 64 B line. Then come `add`, `cmp` and `b.lo`. The sentence about the bytes starts here. |
| 953 | ` * every line and no other byte. */` | Comment: the kernel reads the bytes 0 to 15 of every 64 B line and no other byte. |
| 954 | `PLACE(read_1pl);` | `PLACE(read_1pl)` adds a pad of 16 bytes (line 895). In the CRB binary of `bwx11` the function starts at `0x4e90`, which is 16 modulo 64 [Ref1]. |
| 955 | `__attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)` | Starts the function `k_read_1pl`, the kernel `read_1pl`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. `noinline` forbids gcc to merge it into its caller. |
| 956 | `{` | Opens the body of `k_read_1pl`. |
| 957 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 958 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx11`: `add x1, x0, x1, lsl #3`. It is the only instruction before the loop [Ref1]. |
| 959 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text of the loop, as in `DEF_ASMREAD` (line 589). |
| 960 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx11` the loop starts at an address of 20 modulo 64 [Ref1]. |
| 961 | `        "ldr q0, [%[p]]\n\t"` | `ldr` loads 16 B from memory into one vector register: the bytes 0 to 15 of the current block of 256 B into `q0`. These are the first 16 B of the first 64 B line of the block. |
| 962 | `        "ldr q1, [%[p], #64]\n\t"` | Loads the bytes 64 to 79 of the block into `q1`: the first 16 B of the second 64 B line. |
| 963 | `        "ldr q2, [%[p], #128]\n\t"` | Loads the bytes 128 to 143 of the block into `q2`: the first 16 B of the third 64 B line. |
| 964 | `        "ldr q3, [%[p], #192]\n\t"` | Loads the bytes 192 to 207 of the block into `q3`: the first 16 B of the fourth 64 B line. So one loop pass loads 64 B of its block of 256 B: the bytes 0 to 15 of each 64 B line. It does not load the other 48 B of a 64 B line. `asmread` has 8 load instructions of 32 B per loop pass. This kernel has 4 load instructions of 16 B per loop pass. Nothing uses the loaded values: no instruction of the loop takes `q0` to `q3` as an input. |
| 965 | `        "add %[p], %[p], #256\n\t"` | `add` moves the read pointer forward by 256 B. |
| 966 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the read pointer with `end`. |
| 967 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the pointer is below `end`. One loop pass is 7 instructions per block of 256 B: 4 `ldr`, `add`, `cmp` and the branch. The worker counts the bytes outside the kernel. For each call it adds the size of the range that it passed to the kernel (line 1280, line 1296). So the rate of `read_1pl` counts 256 B per loop pass, although the loop pass loads 64 B. |
| 968 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 969 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 970 | `        : "v0", "v1", "v2", "v3", "memory", "cc");` | The clobber list. Of the vector registers it names only `v0` to `v3`. The calling rules do not require a function to keep these registers. So gcc saves nothing. In `bwx11` the whole function has 9 instructions: 1 before the loop, 7 in the loop, then `ret` [Ref1]. `asmread` differs here: it saves `d8` to `d15` and loads them back at each call. |
| 971 | `}` | Ends the function `k_read_1pl`. |

### Stand-ins of the kernels of round 3 (lines 972 to 990)

| Line | Source | Explanation |
|---:|---|---|
| 972 | `#else` | `#else` of the `#if` of line 898. The compiler reads the lines up to line 988 only for a machine that is not AArch64. |
| 973 | `/* Stand-ins. A prefetch touches no byte, so the stand-in of a read_pf kernel` | Comment: the stand-ins of the kernels of this block. A prefetch touches no byte. |
| 974 | ` * is the stand-in of asmread. The stand-in of read_1pl reads the first two` | Comment: so the stand-in of a `read_pf` kernel is the stand-in of `asmread` (lines 825 to 832). The sentence about `read_1pl` starts here. |
| 975 | ` * words (16 B) of every 64 B line, as the real kernel does. */` | Comment: the stand-in of `read_1pl` reads the first two words, which are 16 B, of every 64 B line. The real kernel reads the same bytes. |
| 976 | `DEF_ASMREAD(read_pf256, 0)` | Stand-in build only: defines `k_read_pf256` as the plain read loop of lines 825 to 832, which reads every word of the range. |
| 977 | `DEF_ASMREAD(read_pf512, 0)` | Stand-in build only: defines `k_read_pf512` as the plain read loop. |
| 978 | `DEF_ASMREAD(read_pf1024, 0)` | Stand-in build only: defines `k_read_pf1024` as the plain read loop. |
| 979 | `DEF_ASMREAD(read_pf2048, 0)` | Stand-in build only: defines `k_read_pf2048` as the plain read loop. |
| 980 | `PLACE(read_1pl);` | `PLACE` adds the pad of `read_1pl`, as in the AArch64 branch. |
| 981 | `__attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)` | Starts the stand-in function `k_read_1pl`. A build on CRB, an Arm machine, does not compile it. |
| 982 | `{` | Opens the body of the stand-in. |
| 983 | `    const volatile uint64_t *p = a;` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 984 | `    for (size_t i = 0; i < n; i += 8) {` | A loop over the range in steps of 8 words, which are 64 B. |
| 985 | `        (void)p[i];` | Reads the first word of the 64 B line and drops the value. |
| 986 | `        (void)p[i + 1];` | Reads the second word of the 64 B line and drops the value. So the loop reads 16 B of every 64 B. |
| 987 | `    }` | Ends the loop of line 984. |
| 988 | `}` | Ends the stand-in function `k_read_1pl`. |
| 989 | `#endif` | Ends the `#if` of line 898. |

### Pad after the kernels of round 3 (lines 991 to 1009)

| Line | Source | Explanation |
|---:|---|---|
| 991 | `/*` | Opens the comment about the placement of the code after the kernels. It explains lines 1003 to 1006. |
| 992 | ` * Placement of the code after the kernels. In the accepted build of bwx8 the` | Comment: the topic is the placement of the code that follows the kernels. The comment first gives a fact about the accepted build of `bwx8`. |
| 993 | ` * last kernel ends at 0x4a14 (ref-bwx8/listing.txt), so the function after` | Comment: in that build the last kernel ends at the address `0x4a14`. The comment names the file `ref-bwx8/listing.txt` as its source. |
| 994 | ` * the kernels starts at 0x4a18: 24 modulo 64. That function is call(), or` | Comment: so the function after the kernels starts at `0x4a18` in that build, which is 24 modulo 64. That function is `call` (line 1075). The build record of CRB reports `call=24` for `bwx11`: its function `call` also starts at 24 modulo 64 [Ref2]. |
| 995 | ` * read_smaps() if gcc inlines every call of call(). The pad below gives it` | Comment: if gcc merges `call` into all of its callers, the function after the kernels is `read_smaps` (line 1099). The pad below gives this function the same start address modulo 64 in `bwx10`. |
| 996 | ` * the same start modulo 64 in bwx10. No code is added between call() and the` | Comment: no code was added between `call` and the end of `timed_sequence` (line 1579), a function of the trial mode. |
| 997 | ` * end of timed_sequence(), so that code keeps the placement modulo 64 that it` | Comment: so the code from `call` to the end of `timed_sequence` keeps its placement modulo 64. |
| 998 | ` * has in bwx8. build10.sh prints the placement of both binaries.` | Comment: it is the placement that this code has in `bwx8`. The script `build10.sh` in the code folder `bwx10-2026-11-15` prints the placement of both binaries. |
| 999 | ` * The value 24 holds for the AArch64 build with the accepted compiler. On` | Comment: the value 24 holds for the AArch64 build with the accepted compiler. |
| 1000 | ` * another machine it is only a pad: test_runner10.py builds one copy with the` | Comment: on another machine the value is only a pad. The script `test_runner10.py` in the code folder `bwx10-2026-11-15` builds one copy with another value. |
| 1001 | ` * local value to check the method.` | Comment: that other value is the value of the local machine. The copy checks the method. |
| 1002 | ` */` | Ends the comment. |
| 1003 | `#ifndef PAD_after_kernels` | Compiles line 1004 only when the build command has not defined `PAD_after_kernels`. |
| 1004 | `#define PAD_after_kernels 24` | `PAD_after_kernels` is 24. A `-D` option could give another value, and the CRB build of `bwx11` has none [Ref2]. |
| 1005 | `#endif` | Ends the `#ifndef` of line 1003. |
| 1006 | `PLACE(after_kernels);` | `PLACE(after_kernels)` fills the code up to a multiple of 64 bytes and then adds 24 bytes of value 0. No function with this name exists: the macro only places the code that follows. In this file more kernels follow this pad, from line 1010 on. So this pad does not stand directly before `call`. A later pad with the same value does that (lines 1039 to 1042). |
| 1007 | `/* bwx10- */` | Comment: a marker. The block that line 865 opened ends here. |
| 1008 | `/* bwx11+ */` | Comment: a marker. A block of text that the version `bwx11` added starts here. The marker of line 1043 ends the block. The block holds the kernels `read_nop64`, `read_nop96` and `read_nop128`. |

### Kernels of round 4 (version `bwx11`): `read_nop64`, `read_nop96`, `read_nop128` (lines 1010 to 1032)

| Line | Source | Explanation |
|---:|---|---|
| 1010 | `/*` | Opens the comment about the kernels of round 4. |
| 1011 | ` * Kernels of round 4. They stand after every kernel of bwx10, so those keep` | Comment: the kernels below are those of round 4, the round of work that produced `bwx11` (line 3). It is not a round of the option `--rounds`. They stand after every kernel of `bwx10`. |
| 1012 | ` * their place. Each one is the asmread loop with more nop instructions` | Comment: so the kernels of `bwx10` keep their place in the binary. Each new kernel is the `asmread` loop with more `nop` instructions. |
| 1013 | ` * between the 8 ldp and the add: 64, 96 and 128. The frame is the frame of` | Comment: the `nop` instructions stand between the 8 `ldp` and the `add` of the read address: 64, 96 or 128 of them. The sentence about the frame starts here. |
| 1014 | ` * asmread (d8-d15 are saved), so the pad is the pad of asmread and the loop` | Comment: the frame is the frame of `asmread`: the function saves `d8` to `d15` before its loop. So each kernel gets the pad of `asmread`. |
| 1015 | ` * starts at 20 modulo 64 (check_listing11.py checks it). DEF_ASMREAD is the` | Comment: the loop then starts at 20 modulo 64. The script `check_listing11.py` in the code folder `bwx11-2026-11-15` checks it. The listing of the CRB build of `bwx11` shows 20 modulo 64 for the three loops [Ref1]. |
| 1016 | ` * macro of the kernels of bwx8: the asm text on AArch64, the stand-in loop on` | Comment: `DEF_ASMREAD` is the macro of the kernels of `bwx8`. On AArch64 it gives the assembly text (line 583). |
| 1017 | ` * another machine. A nop touches no byte, so the stand-in is the stand-in of` | Comment: on another machine it gives the stand-in loop (line 825). A `nop` touches no byte. |
| 1018 | ` * asmread.` | Comment: so the stand-in of these kernels is the stand-in of `asmread`. |
| 1019 | ` */` | Ends the comment. |
| 1020 | `#ifndef PAD_read_nop64` | Compiles line 1021 only when the build command has not defined `PAD_read_nop64`. |
| 1021 | `#define PAD_read_nop64 PAD_asmread` | `PAD_read_nop64`: the value of `PAD_asmread`, which is 0 (line 181). So `PLACE` (line 130) lets the function start on a 64 B boundary. |
| 1022 | `#endif` | Ends the `#ifndef` of line 1020. |
| 1023 | `#ifndef PAD_read_nop96` | Compiles line 1024 only when the build command has not defined `PAD_read_nop96`. |
| 1024 | `#define PAD_read_nop96 PAD_asmread` | `PAD_read_nop96`: the value of `PAD_asmread`, which is 0 (line 181). The CRB build of `bwx11` has no `-D` option that could change it [Ref2]. |
| 1025 | `#endif` | Ends the `#ifndef` of line 1023. |
| 1026 | `#ifndef PAD_read_nop128` | Compiles line 1027 only when the build command has not defined `PAD_read_nop128`. |
| 1027 | `#define PAD_read_nop128 PAD_asmread` | `PAD_read_nop128`: the value of `PAD_asmread`, which is 0 (line 181). |
| 1028 | `#endif` | Ends the `#ifndef` of line 1026. |
| 1029 | `DEF_ASMREAD(read_nop64, 64)` | Creates the kernel `read_nop64` from the macro `DEF_ASMREAD` (lines 583 to 608): the `asmread` loop with 64 `nop` instructions per 256 B. That is 75 instructions per loop pass. |
| 1030 | `DEF_ASMREAD(read_nop96, 96)` | Creates the function `k_read_nop96` from the macro `DEF_ASMREAD` (lines 583 to 608) with 96 `nop`. One loop pass: 8 `ldp` load 256 B into `q0` to `q15`, each byte once, and nothing uses the loaded values. Then come 96 `nop`, the `add` of the read address, `cmp` and the branch. That is 107 instructions (428 B of code) per 256 B of data. Listing of the CRB build of `bwx11` [Ref1]: the function starts at the address `0x5080` (0 modulo 64) and the loop at `0x5094` (20 modulo 64), the loop offset of `k_asmread`. Once per call, outside the loop, 4 `stp` save `d8` to `d15`, one `add` computes the end address, 4 `ldp` load `d8` to `d15` back, and `ret` returns. |
| 1031 | `DEF_ASMREAD(read_nop128, 128)` | Creates the kernel `read_nop128`: the `asmread` loop with 128 `nop` instructions per 256 B. That is 139 instructions per loop pass. |

### Second pad after the kernels (version `bwx11`): the start address of `call` (lines 1033 to 1044)

| Line | Source | Explanation |
|---:|---|---|
| 1033 | `/*` | Opens the comment about the second pad. |
| 1034 | ` * The pad after the kernels, once more. The pad of bwx10 above now stands` | Comment: the pad after the kernels is needed once more. The pad of `bwx10` (line 1006) now stands before the kernels of round 4. |
| 1035 | ` * before the kernels of round 4, so it no longer places call(). This pad has` | Comment: so the pad of `bwx10` no longer sets the start address of `call`. |
| 1036 | ` * the same value, and the function after the kernels starts at that value` | Comment: the new pad has the same value. The function after the kernels then starts at that value modulo 64. |
| 1037 | ` * modulo 64, as in bwx10 and in bwx8. build11.sh prints the placement.` | Comment: that is the start address modulo 64 that this function has in `bwx10` and in `bwx8`. The script `build11.sh` in the code folder `bwx11-2026-11-15` prints the placement. |
| 1038 | ` */` | Ends the comment. |
| 1039 | `#ifndef PAD_after_kernels11` | Compiles line 1040 only when the build command has not defined `PAD_after_kernels11`. |
| 1040 | `#define PAD_after_kernels11 PAD_after_kernels` | `PAD_after_kernels11` gets the value of `PAD_after_kernels`, which is 24 (line 1004). |
| 1041 | `#endif` | Ends the `#ifndef` of line 1039. |
| 1042 | `PLACE(after_kernels11);` | `PLACE(after_kernels11)` pads the code up to a 64 B boundary and then adds 24 bytes of value 0. So the function after it starts at 24 modulo 64. In `bwx11` that function is `call` (line 1075): the build record of CRB gives `call=24` for the start of `call` modulo 64 [Ref2]. |
| 1043 | `/* bwx11- */` | Comment: a marker. The block that line 1008 opened ends here. |

### The kernel table `kernels` (lines 1045 to 1070)

| Line | Source | Explanation |
|---:|---|---|
| 1045 | `/* The function is named k_<name>. The cast to void (*)(void) is undone by` | Comment: the function of a kernel has the name `k_` plus the kernel name. The table stores its address with a cast to the common pointer type `void (*)(void)`. |
| 1046 | ` * call() according to the type. */` | Comment: `call` (line 1075) undoes the cast according to the type of the kernel. |
| 1047 | `static const struct kdef {` | Starts `struct kdef`, the type of one entry of the kernel table. |
| 1048 | `    const char *name;` | `name`: the name of the kernel. It is the word that `--seq` accepts. `parse_seq` (line 1334) compares each word of `--seq` with the names and stores the index of the entry that matches. |
| 1049 | `    enum ktype type;` | `type`: one of `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD` (line 220). It tells `call` which arguments the function takes. |
| 1050 | `    void (*fn)(void);` | `fn`: the pointer to the kernel function, stored as one common pointer type. `call` casts it back to the real type before it calls the function. |
| 1051 | `} kernels[] = {` | Ends the structure and starts the kernel table `kernels[]`. For each interval the worker takes the entry of the kernel from this table (line 1242) and passes it to `call`. |
| 1052 | `#define K(name, type) { #name, type, (void (*)(void))k_##name }` | The macro `K(name, type)` writes one entry. `K(read, T_READ)` becomes `{ "read", T_READ, (void (*)(void))k_read }`. `#name` gives the kernel name as text. `k_##name` gives the function. |
| 1053 | `    K(read, T_READ), K(write, T_WRITE), K(copy, T_COPY),` | Entries 0 to 2: `read`, `write` and `copy`, the C kernels with NEON intrinsics. `read` is entry 0 with the type `T_READ`: the new read kernel. |
| 1054 | `    K(asmread, T_READ), K(asmwrite, T_WRITE), K(asmcopy, T_COPY),` | Entries 3 to 5: `asmread`, `asmwrite` and `asmcopy`, the hand-written assembly kernels. `asmread` is entry 3 with the type `T_READ`. |
| 1055 | `    K(oldread, T_OLDREAD), K(oldwrite, T_WRITE), K(oldcopy, T_COPY),` | Entries 6 to 8: `oldread`, `oldwrite` and `oldcopy`, the old kernels. `oldread` is entry 6 with the type `T_OLDREAD`: the old read kernel. |
| 1056 | `    K(asmread2, T_READ), K(asmwrite2, T_WRITE), K(asmcopy2, T_COPY), K(oldread2, T_OLDREAD),` | Entries 9 to 12: the A/A copies `asmread2`, `asmwrite2`, `asmcopy2` and `oldread2`. |
| 1057 | `    K(asmcopy_c, T_COPY), K(asmcopy_c_add, T_COPY), K(asmcopy_c_reg, T_COPY),` | Entries 13 to 15: the copy kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. |
| 1058 | `    K(read_nop4, T_READ), K(read_nop8, T_READ), K(read_nop16, T_READ), K(read_nop32, T_READ),` | Entries 16 to 19: the read kernels `read_nop4`, `read_nop8`, `read_nop16` and `read_nop32`. |
| 1059 | `    K(read_sparse, T_READ),` | Entry 20: the read kernel `read_sparse`. The entries 0 to 20 are the kernels that the first runner `bwx` and the version `bwx8` already have. |
| 1060 | `/* bwx10+ */` | Comment: a marker. The entries that the version `bwx10` added start here. |
| 1061 | `    K(read_pf256, T_READ), K(read_pf512, T_READ), K(read_pf1024, T_READ), K(read_pf2048, T_READ),` | Entries 21 to 24: the read kernels `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048`. |
| 1062 | `    K(read_1pl, T_READ),` | Entry 25: `read_1pl` with the type `T_READ`. The entries 21 to 25 are the 5 kernels that `bwx10` added. |
| 1063 | `/* bwx10- */` | Comment: a marker. The entries of `bwx10` end here. |
| 1064 | `/* bwx11+ */` | Comment: a marker. The entries that the version `bwx11` added start here. |
| 1065 | `    K(read_nop64, T_READ), K(read_nop96, T_READ), K(read_nop128, T_READ),` | Entries 26 to 28: `read_nop64`, `read_nop96` and `read_nop128`, the 3 kernels that `bwx11` added. |
| 1066 | `/* bwx11- */` | Comment: a marker. The entries of `bwx11` end here. |
| 1067 | `#undef K` | Removes the macro `K`. It is needed only inside the table. |
| 1068 | `};` | Ends the kernel table. |
| 1069 | `#define K_COUNT ((int)(sizeof kernels / sizeof kernels[0]))` | `K_COUNT`: the number of entries of the table. It is the size of the table divided by the size of one entry. In `bwx11` it is 29, and the listing of the CRB build holds 29 kernel functions [Ref1]. The worker calls `k_write` directly for the first touch (line 1230), not through the table. |

### Function `call`: run one kernel on one range of a buffer (lines 1071 to 1094)

| Line | Source | Explanation |
|---:|---|---|
| 1071 | `/* Runs kernel kd on len bytes at byte offset off of the thread's buffers. A` | Comment: the function below runs the kernel `kd` on `len` bytes that start at the byte offset `off` of the buffers of the thread. |
| 1072 | ` * read or write kernel uses buffer a. A copy kernel reads a and writes b. The` | Comment: a read kernel or a write kernel uses the buffer `a`. A copy kernel reads `a` and writes `b`. |
| 1073 | ` * sink of the old read kernel is on the stack of the thread, as it was in the` | Comment: the sink of the old read kernel is the variable that takes its sum. It lies on the stack of the thread (line 1219), as it did in the function `pass` of the old benchmark source. |
| 1074 | ` * old pass(), so the threads do not all store to one shared cache line. */` | Comment: so the threads do not all store to one shared cache line. |
| 1075 | `static void call(const struct kdef *kd, struct thread *t, size_t off, size_t len, uint64_t v, volatile uint64_t *sink)` | Starts the function `call`. It runs one kernel on one range of a buffer. `kd` is the table entry of the kernel. `t` is the record of the calling thread. `off` and `len` give the range in bytes. `v` is the value that a write kernel stores. `sink` points to the variable that takes the sum of an old read kernel. The worker calls this function once per interval for the warm-up pass (line 1253). With `--stop common` it calls it once for each chunk of the timed loop (line 1279). In the timed loop the function runs between the clock reads `t0` and `t1`. So its own instructions are part of the timed interval, once per chunk. |
| 1076 | `{` | Opens the body of `call`. |
| 1077 | `    uint64_t *a = t->a + off / 8;` | `a`: the address of the first word of the range. `t->a` points to 8-byte words. So `off / 8` words are `off` bytes. |
| 1078 | `    size_t n = len / 8;` | `n`: the length of the range in 8-byte words. One chunk of 2 MiB gives 262144 words. The warm-up pass of a `--seq` entry of 256 MiB gives 33554432 words. |
| 1079 | `    switch (kd->type) {` | Chooses the form of the call by the type of the kernel. |
| 1080 | `    case T_READ:` | The case of a read kernel. |
| 1081 | `        ((read_fn)kd->fn)(a, n);` | Casts the pointer to the type `read_fn` (line 221) and calls the kernel with the address and the word count. The kernel returns nothing. |
| 1082 | `        break;` | Leaves the `switch`. |
| 1083 | `    case T_OLDREAD:` | The case of an old read kernel. |
| 1084 | `        *sink = ((oldread_fn)kd->fn)(a, n);` | Calls the kernel, which returns its sum, and stores the sum to `*sink`. `sink` points to a `volatile` variable on the stack of the worker (line 1219). So the compiler must keep the store and must compute the sum. The listing of `k_oldread` in `bwx11` holds the adds [Ref1]. This path has one store of 8 bytes per call that the `T_READ` path does not have. In the timed loop of `--stop common` that is one store per chunk (line 1279). |
| 1085 | `        break;` | Leaves the `switch`. |
| 1086 | `    case T_WRITE:` | The case of a write kernel. |
| 1087 | `        ((write_fn)kd->fn)(a, n, v);` | Casts the pointer to the type `write_fn` and calls the write kernel with the address, the word count and the value `v` to store. |
| 1088 | `        break;` | Leaves the `switch`. |
| 1089 | `    case T_COPY:` | The case of a copy kernel. |
| 1090 | `        ((copy_fn)kd->fn)(t->b + off / 8, a, n);` | Casts the pointer to the type `copy_fn` and calls the copy kernel. The kernel reads the range of the buffer `a` and writes the same range of the buffer `b`. |
| 1091 | `        break;` | Leaves the `switch`. |
| 1092 | `    }` | Ends the `switch` of line 1079. |
| 1093 | `}` | Ends the function `call`. It returns no value. |

### Function `read_smaps`: the page state of the buffers (lines 1095 to 1127)

| Line | Source | Explanation |
|---:|---|---|
| 1095 | `/* Page state (handoff B.6). For each of the n buffers (a NULL entry is` | Comment: the function below reads the page state. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. The function works on `n` buffers and skips an entry that is `NULL`. |
| 1096 | ` * skipped): the entry of /proc/self/smaps whose start is the buffer and whose` | Comment: for each buffer it looks for the entry of the Linux file `/proc/self/smaps` whose start is the buffer address. |
| 1097 | ` * end is the buffer plus buf_len(). Without such an entry both values stay -1` | Comment: the end of that entry must be the buffer address plus `buf_len()`. Without such an entry both values stay -1. |
| 1098 | ` * and are printed as NA. */` | Comment: a value of -1 is printed as `NA`. |
| 1099 | `static void read_smaps(struct page *pg, uint64_t *const *buf, int n)` | Starts the function `read_smaps`. For each of the `n` buffer addresses in `buf` it looks for the mapping of that buffer in `/proc/self/smaps`. It writes two values to `pg`: the size of the mapping and the part of it on 2 MiB pages, both in kB. In a process with more than one thread `main` calls it before the first interval and after each interval (line 2688). During the call all workers wait at the barrier (line 1237 or line 1315). So the call is not timed. |
| 1100 | `{` | Opens the body of `read_smaps`. In a process with one thread the worker calls the function before each interval (line 1256): after the warm-up pass and before its barrier wait of line 1259. The timed interval starts later, at the clock read `t0` (line 1272). This call is not timed either. |
| 1101 | `    char line[256];` | `line`: the buffer for one line of the file, at most 255 characters. |
| 1102 | `    int cur = -1;` | `cur`: the index of the buffer whose mapping the loop below is reading, or -1 for no buffer. |
| 1103 | `    size_t len = buf_len();` | `len`: the buffer length from `buf_len` (line 393). |
| 1104 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 1105 | `        pg[i].kb_total = pg[i].kb_huge = -1;` | Sets both values of the entry to -1. The value -1 means that the buffer was not found. |
| 1106 | `    FILE *f = fopen("/proc/self/smaps", "r");` | Opens `/proc/self/smaps` for reading. The file lists every memory mapping of the process. So it holds the buffers of all threads. |
| 1107 | `    if (!f)` | Tests whether the file did not open. |
| 1108 | `        return;` | In that case the function returns, and all values stay -1. |
| 1109 | `    while (fgets(line, sizeof line, f)) {` | Starts a loop that reads the file line by line. It ends at the end of the file. |
| 1110 | `        unsigned long s, e;` | `s` and `e`: the start address and the end address of a mapping. |
| 1111 | `        char perms[8];` | `perms`: the word after the two addresses, at most 7 characters. In the file it holds the access rights of the mapping. The function does not use its content. |
| 1112 | `        if (sscanf(line, "%lx-%lx %7s", &s, &e, perms) == 3) {` | `sscanf` returns 3 when the line starts with `start-end`, two hexadecimal addresses, and a word after them. Such a line is the first line of a mapping. |
| 1113 | `            cur = -1;` | At the first line of a mapping `cur` is first set back to -1. |
| 1114 | `            for (int i = 0; i < n; i++)` | Then a loop compares the mapping with every buffer. |
| 1115 | `                if (buf[i] && (unsigned long)(uintptr_t)buf[i] == s && e == s + len)` | A buffer matches when its entry is not `NULL`, the mapping starts at the buffer address and the mapping ends exactly `len` bytes after it. The comment of `alloc_buf` (lines 398 to 400) gives the reason for the exact test: no-access ranges stand before and after each buffer, so Linux lists the buffer as one mapping of its own. |
| 1116 | `                    cur = i;` | On a match `cur` becomes the index of that buffer. When no buffer matches, `cur` stays -1. Then the next lines of that mapping store nothing, and they cannot change the values of a buffer that was read before. |
| 1117 | `        } else if (cur >= 0) {` | Every other line belongs to the mapping whose first line was read last. This branch runs only when that mapping is a buffer (`cur >= 0`). |
| 1118 | `            sscanf(line, "Size: %ld kB", &pg[cur].kb_total);` | This `sscanf` stores a number only when the line starts with `Size:`. The number is the size of the mapping in kB and goes to `kb_total`. |
| 1119 | `            sscanf(line, "AnonHugePages: %ld kB", &pg[cur].kb_huge);` | This `sscanf` stores a number only when the line starts with `AnonHugePages:`. The number is the part of the mapping on 2 MiB pages in kB and goes to `kb_huge`. All other lines store nothing. |
| 1120 | `        }` | Ends the `else if` of line 1117. |
| 1121 | `    }` | Ends the loop of line 1109. |
| 1122 | `    fclose(f);` | Closes the file. |
| 1123 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 1124 | `        if (pg[i].kb_total < 0 \|\| pg[i].kb_huge < 0)` | Tests whether one of the two values of the entry is still below 0. |
| 1125 | `            pg[i].kb_total = pg[i].kb_huge = -1;` | In that case both values are set to -1. `print_p` (line 1154) prints a value below 0 as `NA`. |
| 1126 | `}` | Ends the function `read_smaps`. |

### Function `read_vmstat`: four counters of the whole system (lines 1128 to 1145)

| Line | Source | Explanation |
|---:|---|---|
| 1128 | `/* Four counters of /proc/vmstat. They count for the whole system. -1: not found. */` | Comment: the function below reads four counters of the Linux file `/proc/vmstat`. They count for the whole system, not for one buffer. The value -1 means that a counter was not found. |
| 1129 | `static void read_vmstat(long long vm[4])` | Starts the function `read_vmstat`. It reads the four counters into `vm[0]` to `vm[3]`, in the order of the names in line 1131. They become the last four columns of every P row. In a process with more than one thread `main` calls it once before the first interval and once after each interval (line 2689). In a process with one thread the worker calls it before each interval (line 1257): after the warm-up pass and before its barrier wait of line 1259. The timed interval starts later, at the clock read `t0` (line 1272). It is not timed. |
| 1130 | `{` | Opens the body of `read_vmstat`. |
| 1131 | `    static const char *name[4] = { "thp_fault_alloc", "thp_fault_fallback", "thp_collapse_alloc", "pgmigrate_success" };` | `name`: the names of the four counters. The Linux documentation gives their meanings [Ref6]. `thp_fault_alloc` counts the 2 MiB pages that Linux gave at a page fault. `thp_fault_fallback` counts the page faults at which Linux could not give a 2 MiB page and used small pages. `thp_collapse_alloc` counts the 2 MiB pages that Linux made later from a range of small pages. `pgmigrate_success` counts the pages that Linux moved to another place in physical memory. |
| 1132 | `    char key[64];` | `key`: the buffer for one name of the file, at most 63 characters. |
| 1133 | `    long long val;` | `val`: the number that follows the name. |
| 1134 | `    for (int i = 0; i < 4; i++)` | A loop over the four values. |
| 1135 | `        vm[i] = -1;` | Sets the value to -1. The value -1 means that the counter was not found. |
| 1136 | `    FILE *f = fopen("/proc/vmstat", "r");` | Opens `/proc/vmstat` for reading. |
| 1137 | `    if (!f)` | Tests whether the file did not open. |
| 1138 | `        return;` | In that case the function returns with the four values at -1. |
| 1139 | `    while (fscanf(f, "%63s %lld", key, &val) == 2)` | Each line of the file holds a name and a number. `fscanf` reads one such pair per loop pass. The loop ends when `fscanf` finds no further pair, for example at the end of the file. |
| 1140 | `        for (int i = 0; i < 4; i++)` | A loop over the four names. |
| 1141 | `            if (!strcmp(key, name[i]))` | Tests whether the name from the file equals name `i`. `strcmp` returns 0 for equal texts. |
| 1142 | `                vm[i] = val;` | On a match the number goes to the matching place in `vm`. |
| 1143 | `    fclose(f);` | Closes the file. |
| 1144 | `}` | Ends the function `read_vmstat`. |

### Function `print_na`: one csv field, or `NA` (lines 1146 to 1153)

| Line | Source | Explanation |
|---:|---|---|
| 1146 | `static void print_na(long long v)` | Starts the function `print_na`. It prints one more field of a csv row: a comma and then the number `v`. For a negative `v` it prints `,NA`. The functions `read_smaps` (line 1099) and `read_vmstat` (line 1129) store -1 for a value that they did not find. So such a value shows as `NA` in a P row. |
| 1147 | `{` | Opens the body of `print_na`. |
| 1148 | `    if (v < 0)` | Tests whether `v` is negative. |
| 1149 | `        printf(",NA");` | A negative value prints as a comma and the text `NA` (not available). |
| 1150 | `    else` | The case of a value of 0 or more. |
| 1151 | `        printf(",%lld", v);` | Prints a comma and the number in decimal. |
| 1152 | `}` | Ends the function `print_na`. |

### Function `print_p`: one P row, the page state of one buffer (lines 1154 to 1163)

| Line | Source | Explanation |
|---:|---|---|
| 1154 | `static void print_p(int round, int pos, int tid, char buffer, const struct page *pg, const long long vm[4])` | Starts the function `print_p`. It prints one P row: the page state of one buffer at one reading. `round`, `pos` and `tid` are the round, the position and the thread index. `buffer` is the letter `a` or `b`. `pg` holds the two page values of the buffer. `vm` holds four counters of the Linux file `/proc/vmstat`. In a process with more than one thread `main` calls it once per buffer after each reading of the page state (line 2694). In a process with one thread `main` calls it in line 2650 and line 2652. |
| 1155 | `{` | Opens the body of `print_p`. |
| 1156 | `    printf("P,%d,%d,%d,%c", round, pos, tid, buffer);` | Columns 1 to 5 of the row: the letter `P`, the round, the position, the thread index and the buffer letter. The position is -1 in the rows of the reading before the first interval (line 2620). In every other row of a process with more than one thread it is the position of the interval that has ended directly before the reading. In a process with one thread the row holds the state that the worker read before the interval of that position (line 1254). |
| 1157 | `    print_na(pg->kb_total);` | Column 6, `kB_total`: the size of the mapping of the buffer. The unit is kB of 1024 bytes. `read_smaps` (line 1099) took the value from the line `Size` of the Linux file `/proc/self/smaps`. A value that it did not find prints as `NA`. |
| 1158 | `    print_na(pg->kb_huge);` | Column 7, `kB_huge`: the part of the buffer that lies on 2 MiB pages, in kB of 1024 bytes. `read_smaps` took it from the line `AnonHugePages` of the same file. |
| 1159 | `    for (int i = 0; i < 4; i++)` | Loop over the four counters of `/proc/vmstat`. |
| 1160 | `        print_na(vm[i]);` | Columns 8 to 11: the counters `thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc` and `pgmigrate_success`, in this order (line 1131). They count for the whole system, not for this buffer. `main` passes the same array `vm` for all buffers of one reading (line 2694). So all P rows of one reading hold the same four values. |
| 1161 | `    printf("\n");` | Ends the row with a line break. |
| 1162 | `}` | Ends the function `print_p`. |

### Function `open_counters`: open the counter group of one thread (lines 1164 to 1192)

| Line | Source | Explanation |
|---:|---|---|
| 1164 | `/* Counters (handoff B.8): one group per thread, user mode only, opened by the` | Comment: the counters follow section B.8 of the file `handoff.md`, the specification of the first runner. Each thread has one counter group. The counters count in user mode only. The sentence about who opens them goes on in line 1165. |
| 1165 | ` * pinned thread for itself. An event that does not open is printed as NA. */` | Comment: the pinned thread opens the counters for itself. An event that does not open is printed as `NA` (lines 2674 to 2675). |
| 1166 | `static void open_counters(struct thread *t)` | Starts the function `open_counters`. It opens one counter per entry of `--events` for the calling thread and joins the counters into one group. With `--count` each worker calls it once (line 1228), after the pinning and before it maps its buffer. `t` is the record of the calling thread. |
| 1167 | `{` | Opens the body of `open_counters`. |
| 1168 | `    t->group_fd = -1;` | Start state: no group leader (`group_fd` is -1). The group leader is the first counter of a counter group. |
| 1169 | `    t->nopen = 0;` | Start state: 0 open counters. |
| 1170 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `--events`, in the order of the list. `cfg.nev` is their number. |
| 1171 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 1172 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. So every option that the next lines do not set is off. The field `disabled` also stays 0. So a counter counts from the moment it is opened. |
| 1173 | `        a.type = (uint32_t)cfg.pmu_type;` | `type` selects the PMU (performance monitoring unit, the hardware event counters of a core). It is the value of `--pmu-type`. |
| 1174 | `        a.size = sizeof a;` | `size` gives Linux the size of the structure. |
| 1175 | `        a.config = cfg.ev_code[e];` | `config` is the event code of this entry of `--events`. The program passes the code to Linux and does not interpret it. |
| 1176 | `        a.exclude_kernel = 1;` | `exclude_kernel = 1`: the counter does not count while the CPU runs code of the Linux kernel. |
| 1177 | `        a.exclude_hv = 1;` | `exclude_hv = 1`: the counter does not count code of a hypervisor. A hypervisor is the software that runs virtual machines. With these two fields the counter counts in user mode only: while the thread runs the code of the program itself. The specification of the first runner says that counter code without these two fields fails without root rights on CRB [Ref4]. |
| 1178 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | `read_format` chooses what one `read` of the group returns. `PERF_FORMAT_GROUP`: the values of all counters of the group in one reading. The two other flags add the enabled time and the running time of the group [Ref5]. |
| 1179 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, t->group_fd, 0);` | The system call `perf_event_open` opens the counter. It returns a file descriptor: the number that later calls such as `read` use for the open counter. A negative value means failure. The arguments `0` and `-1` are the pid and the cpu argument of the call [Ref4]. Together they mean: count the calling thread, on any CPU that it runs on. With `--cpus` the thread is pinned, so this is one CPU. The argument `t->group_fd` is -1 for the first counter, which starts a new group. A later counter passes the file descriptor of the leader and joins its group. The last argument `0` means no flags. |
| 1180 | `        if (fd < 0) {` | Tests whether the open failed. |
| 1181 | `            if (t->idx == 0)` | Only thread 0 writes a message. So an event that fails in every thread gives one message, not one per thread. |
| 1182 | `                fprintf(stderr, "perf_event_open %s (type %ld code 0x%llx): %s (printed as NA)\n", cfg.ev_name[e],` | The message goes to stderr: the word `perf_event_open`, the event name, the PMU type, the event code in hexadecimal, the error text of Linux and the words `printed as NA`. This line holds the format and the event name. |
| 1183 | `                        cfg.pmu_type, (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 1182: the PMU type, the event code and the error text (`strerror(errno)`). |
| 1184 | `            t->ev_pos[e] = -1;` | The event gets the position -1. `main` prints `NA` for it in the C rows (lines 2673 to 2675). |
| 1185 | `            continue;` | The loop goes on with the next event. The thread does not stop. |
| 1186 | `        }` | Ends the `if` of line 1180. |
| 1187 | `        t->ev_pos[e] = t->nopen++;` | The open succeeded. `ev_pos[e]` gets the position of this event in a group reading: 0 for the first open counter, 1 for the next. `nopen` counts the open counters of the thread. |
| 1188 | `        if (t->group_fd < 0)` | Tests whether the group has no leader yet. |
| 1189 | `            t->group_fd = fd;` | The first counter that opens becomes the leader of the group. `group_fd` keeps its file descriptor, and every group reading uses it (line 1206). The file descriptors of the other counters are not kept. The function `worker` never closes, resets or stops a counter. |
| 1190 | `    }` | Ends the loop over the events (line 1170). |
| 1191 | `}` | Ends the function `open_counters`. |

### Function `cpu_ns`: the CPU time of the calling thread (lines 1193 to 1199)

| Line | Source | Explanation |
|---:|---|---|
| 1193 | `static uint64_t cpu_ns(void)` | Starts the function `cpu_ns`. It returns the CPU time that the calling thread has used so far, in ns. With `--count` the worker calls it once before and once after each timed interval (line 1270, line 1302). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 1194 | `{` | Opens the body of `cpu_ns`. |
| 1195 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 1196 | `    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);` | Reads the Linux clock `CLOCK_THREAD_CPUTIME_ID` into `ts`. This clock counts the CPU time of the calling thread only. |
| 1197 | `    return (uint64_t)ts.tv_sec * 1000000000UL + (uint64_t)ts.tv_nsec;` | Returns the time in ns: the seconds times 1000000000, plus the nanoseconds. |
| 1198 | `}` | Ends the function `cpu_ns`. |

### Function `read_group`: one reading of the counter group (lines 1200 to 1215)

| Line | Source | Explanation |
|---:|---|---|
| 1200 | `/* Group read: nr, time_enabled, time_running, then one value per open event. */` | Comment: the layout of one group reading: the number of counters (`nr`), the enabled time, the running time, then one value per open event [Ref5]. |
| 1201 | `static void read_group(const struct thread *t, struct counts *c)` | Starts the function `read_group`. It takes one reading of all counters of the thread `t` and stores it in `c`. With `--count` the worker calls it once before and once after each timed interval (line 1269, line 1303). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 1202 | `{` | Opens the body of `read_group`. |
| 1203 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest reading: 3 header words plus 8 counter values (`MAX_EV` is 8). Each word has 8 bytes. |
| 1204 | `    if (t->group_fd < 0)` | Tests whether the thread has no open counter. |
| 1205 | `        return;` | Such a thread returns here. Then `c` keeps the zeros that the worker wrote in line 1251. |
| 1206 | `    if (read(t->group_fd, buf, sizeof buf) < (ssize_t)(3 * sizeof buf[0]) \|\| buf[0] != (uint64_t)t->nopen) {` | One `read` system call on the leader returns the whole group: the number of counters `nr`, the enabled time, the running time, then one value per counter [Ref5]. The reading is rejected when it has fewer than 24 bytes (the 3 header words). It is also rejected when `nr` is not the number of counters that this thread opened. |
| 1207 | `        perror("read of the counter group");` | A rejected reading: `perror` prints the words `read of the counter group` and the reason that Linux gave to stderr. |
| 1208 | `        exit(2);` | The whole program then ends with exit status 2. |
| 1209 | `    }` | Ends the `if` of line 1206. |
| 1210 | `    c->enabled = buf[1];` | Stores the enabled time of the group, in ns: how long the counters were enabled. |
| 1211 | `    c->running = buf[2];` | Stores the running time of the group, in ns: how long the counters really counted. `main` prints the difference between the two readings of an interval as `enabled_ns` and `running_ns` in the C row (lines 2669 to 2670). |
| 1212 | `    for (int i = 0; i < t->nopen; i++)` | Loop over the open counters of the thread. |
| 1213 | `        c->val[i] = buf[3 + i];` | Stores one value per open counter, in the order in which the counters were opened. `main` prints for each event the difference between the reading after the interval and the reading before it (line 2677). |
| 1214 | `}` | Ends the function `read_group`. |

### Function `worker`: start values, pinning, counters, buffers and first touch (lines 1216 to 1239)

| Line | Source | Explanation |
|---:|---|---|
| 1216 | `static void *worker(void *arg)` | Starts the function `worker`, the start function of every worker thread. `main` creates the workers in line 2589. `arg` points to the record of the thread. |
| 1217 | `{` | Opens the body of `worker`. |
| 1218 | `    struct thread *t = arg;` | `t`: the record of this thread. `main` has set its index `idx` and its CPU `cpu` (lines 2587 to 2588). |
| 1219 | `    volatile uint64_t sink;` | `sink`: a volatile variable on the stack of this thread. `call` stores there the sum that an old read kernel returns (line 1084). The compiler must keep this store. So it cannot remove the adds of the old read kernel. Each thread has its own `sink`. So the threads do not all store to one shared cache line. |
| 1220 | `    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */` | Comment: the store value is known only when the program runs, and its 8 bytes are not all equal. So the compiler cannot turn the store loop into a call of `memset`, the library function that fills memory with one byte value. |
| 1221 | `    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;` | `v`: the value that `k_write` stores into the 8-byte words of a buffer at the first touch (line 1230). It is the process id (`getpid`) plus the thread index plus 1, times a fixed 64-bit constant. The timed loop gives `v` plus a counter to a write kernel (line 1279, line 1293). The read kernels do not use `v`. |
| 1222 | `    uint64_t k = 0; /* intervals this thread has run (--stop common) */` | `k`: the number of timed intervals that this thread has started. Line 1261 compares it with the shared counter `gen`. The comment says that `--stop common` uses it. |
| 1223 | `    int64_t min_ns = (int64_t)(cfg.min_s * 1e9);` | `min_ns`: the `--min-ms` value in ns. Only the loop of `--stop pass` uses it (line 1299). |
| 1225 | `    if (cfg.ncpus)` | Tests whether a CPU list was given (`--cpus`). |
| 1226 | `        pin_cpu(t->cpu);` | CPU pinning. The thread pins itself to its CPU with `pin_cpu` (line 382). `main` chose the CPU in line 2588. Every later line of the worker runs on that CPU. Without `--cpus` the thread is not pinned. |
| 1227 | `    if (cfg.count)` | Tests whether counting is on (`--count`). |
| 1228 | `        open_counters(t);` | The thread opens its counters with `open_counters` (line 1166). The counters count from this moment on. So they also count during the first touch and the warm-up passes. A C row holds only the change between the two readings of one interval (line 1269, line 1303). |
| 1229 | `    t->a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 401) maps buffer `a` of this thread. The buffer starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. `alloc_buf` also asks Linux for 2 MiB pages for it (with `--no-thp`: for no such pages). Each thread has its own buffer and reads only its own buffer. |
| 1230 | `    k_write(t->a, cfg.bytes / 8, v); /* first touch by this thread */` | First touch. `k_write` (line 498) stores `v` into `cfg.bytes / 8` words of 8 bytes, from the start of the buffer: every word of the `--bytes` range. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 395). Then the worker does not write the rest. No kernel call reaches the rest: the size of a `--seq` entry is at most `--bytes` (line 2568). The pinned thread does this write itself, before any read. Linux assigns the memory pages at this first write. This line is not timed. The comment says: first touch by this thread. |
| 1231 | `    if (cfg.two_buffers) {` | Tests whether the thread needs a second buffer `b`. It exists only with `--two-buffers` or with a copy kernel in `--seq` (lines 2573 to 2574). |
| 1232 | `        t->b = alloc_buf();` | Maps buffer `b` in the same way as buffer `a`. |
| 1233 | `        k_write(t->b, cfg.bytes / 8, v);` | First touch of buffer `b`: the same write as in line 1230. It is not timed. |
| 1234 | `    }` | Ends the `if` of line 1231. |
| 1235 | `    if (cfg.threads > 1) {` | Tests whether the process has more than one worker. Only then the two barrier waits of lines 1236 to 1237 exist. The barrier releases its waiting threads when all workers and the main thread have called it (line 2582). |
| 1236 | `        pthread_barrier_wait(&bar); /* the buffers exist: main() reads the first page state */` | First wait at the barrier. It returns when all workers have mapped and written their buffers and `main` has arrived in line 2622. Then `main` copies the buffer addresses and reads the page state for the P rows with position -1. The comment says: the buffers exist, and `main` reads the first page state. |
| 1237 | `        pthread_barrier_wait(&bar); /* main() has read it */` | Second wait at the barrier. The worker blocks until that reading is done. `main` releases the workers in line 2691. The comment says: `main` has read it. |
| 1238 | `    }` | Ends the `if` of line 1235. |

### Function `worker`: one interval, from the warm-up pass to the clock read `t0` (lines 1240 to 1273)

| Line | Source | Explanation |
|---:|---|---|
| 1240 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds. `--rounds N` runs the `--seq` list N times, and the rounds count from 0. |
| 1241 | `        for (int pos = 0; pos < cfg.nseq; pos++) {` | Loop over the positions of the `--seq` list. One pass of this loop is one timed interval. `main` runs the same two loops (lines 2616 to 2617). |
| 1242 | `            const struct kdef *kd = &kernels[cfg.seq[pos].k];` | `kd`: the entry of the kernel table for this position: name, type and function pointer (line 1051). The kernels run in the order of the `--seq` list. |
| 1243 | `            size_t size = cfg.seq[pos].bytes;` | `size`: the number of bytes of this position. It is the size after `@` in the `--seq` entry, or the `--bytes` value for an entry without `@` (line 2567). |
| 1244 | `            size_t nchunk = size / HUGE_BYTES;` | `nchunk`: the number of whole 2 MiB pieces in `size`. It is 128 for a size of 256 MiB. Only the start offset of line 1246 uses it. |
| 1245 | `            /* --start offset (handoff B.5): thread i starts at (i * 37 mod n) * 2 MiB */` | Comment: with `--start offset` thread i starts at the 2 MiB piece with the number i times 37 modulo n. Here n is `nchunk`. The comment names section B.5 of the file `handoff.md`, the specification of the first runner. |
| 1246 | `            size_t off = cfg.start_offset && nchunk ? ((size_t)t->idx * 37 % nchunk) * HUGE_BYTES : 0;` | `off`: the byte offset in the buffer at which this thread starts its timed work. With `--start common` it is 0. It is also 0 for a size below 2 MiB. With `--start offset` it is `idx * 37 % nchunk` times 2 MiB. So most threads start at a place of their buffer other than byte 0. Thread 0 starts at byte 0, and with one piece (`nchunk` is 1) every thread does. |
| 1247 | `            uint64_t per_byte = kd->type == T_COPY ? 2 : 1; /* copy counts read+write bytes */` | `per_byte`: 2 for a copy kernel, 1 for every other kernel. A copy kernel counts every byte two times: once read, once written. |
| 1248 | `            uint64_t bytes = 0, p = 0;` | `bytes`: the byte count of the timed interval. `p`: the number of kernel calls of the interval with `--stop common`, or of passes with `--stop pass`. Both start at 0. |
| 1249 | `            int64_t sched = 0, deadline = 0, t0, t1;` | Clock values in ns: `sched` (the common start time), `deadline`, `t0` (the start of the timed interval) and `t1` (the clock read after the latest kernel work). |
| 1250 | `            struct result r;` | `r`: the result record of this thread for this interval (line 263). |
| 1251 | `            memset(&r, 0, sizeof r);` | `memset` sets every field of `r` to 0. |
| 1253 | `            call(kd, t, 0, size, v, &sink); /* warm-up */` | Warm-up pass, not timed. One call of the kernel of this position over the range from byte 0 to `size`, through `call` (line 1075). So before every timed interval the thread has run the same kernel once over the whole range. Between this pass and the timed interval lie the barrier wait, the wait for the common start and the first counter reading (lines 1259 to 1271). In a process with one thread the page-state reading of lines 1254 to 1258 also lies between them. |
| 1254 | `            if (cfg.threads == 1) {` | Tests whether the process has one worker only. Only such a process reads the page state here, in the worker: after the warm-up pass and before the barrier. |
| 1255 | `                uint64_t *buf[2] = { t->a, t->b };` | `buf`: the addresses of the two buffers of the thread. `t->b` is NULL when the thread has no second buffer. |
| 1256 | `                read_smaps(r.pg, buf, 2);` | `read_smaps` (line 1099) reads the page state of both buffers into `r.pg`. It skips a NULL entry. |
| 1257 | `                read_vmstat(r.vm);` | `read_vmstat` (line 1129) reads the four counters of `/proc/vmstat` into `r.vm`. `main` prints both readings as P rows after the interval (lines 2649 to 2653). |
| 1258 | `            }` | Ends the `if` of line 1254. |
| 1259 | `            pthread_barrier_wait(&bar);` | Barrier wait after the warm-up pass. The thread blocks until all workers have ended their warm-up pass and `main` has arrived in line 2634. Then all of these threads continue. A thread whose warm-up pass ends early waits here and reads no memory. |
| 1260 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Only then lines 1261 to 1266 run. |
| 1261 | `                while (atomic_load(&gen) != k + 1)` | Common start, step 1. The thread repeats an empty loop until the shared counter `gen` equals `k + 1`. `main` adds 1 to `gen` in line 2639, after it has stored the start time and the deadline of this interval. In this loop the thread stays on its CPU and does not sleep. |
| 1262 | `                    ;` | The empty body of the loop of line 1261. |
| 1263 | `                sched = atomic_load(&t_sched_ns);` | Copies the common start time into `sched`. `main` computed it in line 2636: its clock reading plus 2 ms (`LEAD_NS`). All workers read the same value. |
| 1264 | `                deadline = atomic_load(&deadline_ns);` | Copies the common deadline into `deadline`. `main` computed it in line 2638: the start time plus the `--min-ms` value. All workers read the same value. |
| 1265 | `                while (now_ns() < sched)` | Common start, step 2. The thread reads the clock again and again until the clock reaches `sched`. It leaves the loop at its first clock read at or after the start time. This wait is not timed. |
| 1266 | `                    ;` | The empty body of the loop of line 1265. |
| 1267 | `            }` | Ends the `if` of line 1260. |
| 1268 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). |
| 1269 | `                read_group(t, &r.c0);` | First counter reading (`read_group`, line 1201). It goes into `r.c0`. With `--stop common` it runs after the wait for the common start. With `--stop pass` it runs directly after the barrier. In both cases it runs before the clock read of line 1272. So it is not inside the timed interval. But `t0` is later than the common start time by at least the duration of this line and of line 1270. |
| 1270 | `                r.c0.cpu_ns = cpu_ns();` | Reads the thread CPU time (`cpu_ns`, line 1193) into `r.c0`. |
| 1271 | `            }` | Ends the `if` of line 1268. |
| 1272 | `            t0 = now_ns();` | Start of the timed interval. The thread reads the clock (`now_ns`, line 294) into `t0`. Each thread has its own `t0`. Nothing above this line is inside the timed interval. |
| 1273 | `            k++;` | Counts this interval. At the next interval line 1261 waits for the next value of `gen`. This line runs after the clock read `t0`, so it is the first statement inside the timed interval. |

### Function `worker`: the timed loop and the two stop rules (lines 1274 to 1300)

| Line | Source | Explanation |
|---:|---|---|
| 1274 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Lines 1277 to 1285 are the timed loop of this stop rule. |
| 1275 | `                /* chunks of 2 MiB (or the whole entry if it is smaller); the` | Comment: the kernel runs on chunks of 2 MiB, or on the whole entry when the entry is smaller than 2 MiB. The sentence goes on in line 1276. |
| 1276 | `                 * position continues from chunk to chunk and wraps */` | Comment: the position in the buffer goes on from chunk to chunk. At the end of the entry it returns to the start. |
| 1277 | `                size_t chunk = size < CHUNK_BYTES ? size : CHUNK_BYTES, at = off;` | `chunk`: the number of bytes of one kernel call: 2097152 bytes (2 MiB, `CHUNK_BYTES`), or `size` when `size` is smaller. `at`: the byte offset of the next chunk in the buffer. It starts at `off` (line 1246). |
| 1278 | `                do {` | Starts the timed loop. Its body runs at least once. |
| 1279 | `                    call(kd, t, at, chunk, v + p++, &sink);` | Timed kernel call. `call` (line 1075) runs the kernel on the chunk at byte offset `at`. The kernel gets the address of the chunk and its length in 8-byte words: 262144 words for a chunk of 2 MiB. So the kernel function is entered once per chunk: 128 times per pass over a buffer of 256 MiB. For a kernel of the type `T_OLDREAD`, `call` stores the returned sum in `sink` after each call. A kernel of the type `T_READ` returns nothing. `v + p++` gives a write kernel a new value in every call and counts the calls. A read kernel does not get this argument. |
| 1280 | `                    bytes += per_byte * chunk;` | Bytes counted. Each finished call adds `per_byte * chunk`: 2097152 bytes for a 2 MiB chunk of a read kernel. This is the size of the range that was passed to the kernel. Nothing is counted inside a kernel. So the number is the same for every read kernel. It is also used for `read_1pl`, which loads 16 B of each 64 B line. |
| 1281 | `                    at += chunk;` | Moves `at` to the next chunk. |
| 1282 | `                    if (at == size)` | Tests whether `at` has reached the end of the entry. |
| 1283 | `                        at = 0;` | After the last chunk the offset returns to 0. For a size of 256 MiB this is after chunk 127. So the kernel calls go from the start offset `off` to the end of the range. Then they repeat the whole range from byte 0, until the interval ends. With `--start common` the offset `off` is 0, and the first pass is also a whole pass. |
| 1284 | `                    t1 = now_ns();` | Clock read after every chunk: `t1` is the clock value after this call. The last `t1` is the end of the timed interval. So the timed interval is the code from line 1272 to this line: the kernel calls, the byte count, the step of the offset and one clock read per chunk. |
| 1285 | `                } while (t1 < deadline);` | Stop rule of `--stop common`. The loop repeats while `t1` is before the common deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted. The deadline is the same for all threads. Each thread has its own end time `t1`. |
| 1286 | `            } else {` | The branch of `--stop pass`. Lines 1288 to 1299 are the timed loop of this stop rule. |
| 1287 | `                /* whole passes; with an offset a pass is [off, size) then [0, off) */` | Comment: the thread runs whole passes. With a start offset one pass is the range from `off` to the end of the entry and then the range from 0 to `off`. |
| 1288 | `                uint64_t passes_per_check = CHECK_BYTES / size;` | `passes_per_check`: the number of passes between two clock reads. It is 8 MiB (`CHECK_BYTES`) divided by `size`, rounded down. So for a size below 8 MiB that does not divide 8 MiB, the clock is read after less than 8 MiB. |
| 1289 | `                if (passes_per_check == 0)` | Tests whether the division gave 0. That is the case for every size above 8 MiB. |
| 1290 | `                    passes_per_check = 1;` | The value is then 1: the thread reads the clock after every pass. |
| 1291 | `                do {` | Starts the timed loop of `--stop pass`. Its body runs at least once. |
| 1292 | `                    for (uint64_t c = 0; c < passes_per_check; c++, p++) {` | Runs `passes_per_check` passes without a clock read between them. `p` counts the passes. |
| 1293 | `                        call(kd, t, off, size - off, v + p, &sink);` | Timed kernel call: the range from `off` to the end of the entry. With an `off` of 0 this is the whole entry. `v + p` gives a write kernel a new value in every pass. |
| 1294 | `                        if (off)` | Tests whether the thread has a start offset above 0. |
| 1295 | `                            call(kd, t, 0, off, v + p, &sink);` | Second kernel call of the pass: the range from byte 0 to `off`. So each pass covers every byte of the entry once. |
| 1296 | `                        bytes += per_byte * size;` | Bytes counted: each pass adds `per_byte * size`. This is the size of the entry, or twice the size for a copy kernel. Nothing is counted inside a kernel. |
| 1297 | `                    }` | Ends the `for` of line 1292. |
| 1298 | `                    t1 = now_ns();` | Clock read after the passes: `t1`. The clock is never read inside a pass. The last `t1` is the end of the timed interval. So with this stop rule the timed interval is the code from line 1272 to this line. |
| 1299 | `                } while (t1 - t0 < min_ns);` | Stop rule of `--stop pass`. The loop repeats while less than `min_ns` (the `--min-ms` value) has passed after the `t0` of this thread. So a thread stops only at the end of a whole pass, after a full group of `passes_per_check` passes. The threads stop at different times. |
| 1300 | `            }` | Ends the `if` and `else` of line 1274. |

### Function `worker`: after the timed interval, the result record and the barrier waits (lines 1301 to 1320)

| Line | Source | Explanation |
|---:|---|---|
| 1301 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). The timed interval has ended at the last clock read `t1` (line 1284 or line 1298). |
| 1302 | `                r.c1.cpu_ns = cpu_ns();` | Reads the thread CPU time into `r.c1` (`cpu_ns`). |
| 1303 | `                read_group(t, &r.c1);` | Second counter reading, into `r.c1` (`read_group`). The order is the reverse of lines 1269 to 1270. So the timed interval lies between the two readings of the thread CPU time, and these lie between the two counter readings. The counter values of a C row therefore cover the timed interval plus a few calls around it: the two readings of the thread CPU time and the clock read `t0`. |
| 1304 | `            }` | Ends the `if` of line 1301. |
| 1305 | `            r.bytes = bytes;` | Stores the byte count of the interval in the result record. |
| 1306 | `            r.t_start = t0;` | Stores `t0`, the start of the timed interval. |
| 1307 | `            r.t_end = t1;` | Stores the last `t1`, the end of the timed interval. `main` computes the elapsed time of a thread as `t_end - t_start` (line 2646, line 2659). |
| 1308 | `            r.t_sched = cfg.stop_common ? sched : t0;` | Stores the common start time. `main` prints it in the T row as `t_sched_s` (line 2660). With `--stop pass` there is no common start time, and the field gets `t0`. |
| 1309 | `            r.late = cfg.stop_common && t0 - sched > LATE_NS;` | Late flag. With `--stop common` it is set when `t0` is more than 100000 ns (100 us, `LATE_NS`) after the common start time. `main` then prints `late` in the last column of the T row (line 2661). The program does nothing else with the flag: the interval runs, and its bytes are counted. |
| 1310 | `            t->res = r;` | Copies the record into the thread structure. `main` reads it there after the barrier wait of line 1311. |
| 1311 | `            pthread_barrier_wait(&bar);` | Barrier wait at the end of the interval. The thread blocks until all workers have ended their interval and `main` waits in line 2641. A thread that has stopped reads no memory while other threads finish their last chunk or pass. |
| 1312 | `            /* main() reads the page state of all buffers. The warm-up pass of` | Comment: `main` reads the page state of all buffers at this point. The sentence about the next warm-up pass starts here. |
| 1313 | `             * the next interval starts only after that reading (handoff B.6). */` | Comment: the warm-up pass of the next interval starts only after that reading. The comment names section B.6 of the file `handoff.md`, the specification of the first runner. |
| 1314 | `            if (cfg.threads > 1)` | Tests whether the process has more than one worker. Only then the second barrier wait exists. |
| 1315 | `                pthread_barrier_wait(&bar);` | Second barrier wait at the end of the interval. While the workers block here, `main` prints the I, T and C rows of the interval and reads the page state of all buffers (lines 2643 to 2690). `main` releases the workers in line 2691. Then each worker starts the warm-up pass of the next interval. `main` prints the P rows and the `# page_read` line after the release (lines 2692 to 2695). So this output can run while the workers do their warm-up pass. The output ends before the next timed interval starts: the barrier of line 1259 lets the workers pass only when `main` has finished the output and waits in line 2634. |
| 1316 | `        }` | Ends the loop over the positions (line 1241). The worker calls no sleep function. So between two intervals lie only the waits, the readings and the warm-up pass of the rows above. |
| 1317 | `    }` | Ends the loop over the rounds (line 1240). |
| 1318 | `    return NULL;` | After the last interval of the last round the thread returns. `main` waits for the end of all threads in line 2701. |
| 1319 | `}` | Ends the function `worker`. |

### Function `usage`: option summary, then exit status 2 (lines 1321 to 1333)

| Line | Source | Explanation |
|---:|---|---|
| 1321 | `static void usage(void)` | Starts the function `usage`. It prints the option summary to stderr and ends the program with exit status 2. `main` calls it for an argument that it does not accept and for settings that fail one of its checks (lines 2546 to 2572), for example `--threads` without `--cpus`. |
| 1322 | `{` | Opens the body of `usage`. |
| 1323 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to stderr. Its text stands in lines 1324 to 1330. |
| 1324 | `            "usage: bwx --seq LIST [--threads T --cpus LIST] [--bytes B] [--min-ms MS] [--no-thp]\n"` | Text of the message: the first usage line, with the options `--seq`, `--threads`, `--cpus`, `--bytes`, `--min-ms` and `--no-thp`. The text names the program `bwx`, the name of the first version of the runner. |
| 1325 | `            "           [--rounds N] [--stop pass\|common] [--start common\|offset] [--two-buffers]\n"` | Text of the message: the options `--rounds`, `--stop`, `--start` and `--two-buffers`. |
| 1326 | `            "           [--count --pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options of the counters (`--count`, `--pmu-type`, `--events`), and the two environment variables that can give the counter settings in their place (lines 2553 to 2559). |
| 1327 | `            "       bwx --selftest \| --list\n"` | Text of the message: the second form of the command, with `--selftest` or `--list`. |
| 1328 | `            "  --seq: comma-separated entries KERNEL or KERNEL@SIZE; --list prints the kernel names\n"` | Text of the message: an entry of `--seq` is a kernel name, or a kernel name with `@` and a size. `--list` prints the kernel names. |
| 1329 | `            "  sizes must be multiples of 256; with --stop common: multiples of 2M, or below 2M\n"` | Text of the message: a size must be a multiple of 256. With `--stop common` it must be a multiple of 2M or below 2M (lines 2568 to 2569). |
| 1330 | `            "  --pmu-type and CODE: the perf_event_attr fields type and config of the core PMU (CODE may be 0x..)\n");` | Text of the message: `--pmu-type` and the code of an event go into the fields `type` and `config` of the structure `perf_event_attr` (line 1173, line 1175). A code may be written in hexadecimal with `0x`. This line ends the `fprintf` call. |
| 1331 | `    exit(2);` | Ends the program with exit status 2. |
| 1332 | `}` | Ends the function `usage`. |

### Function `parse_seq`: read the `--seq` list (lines 1334 to 1352)

| Line | Source | Explanation |
|---:|---|---|
| 1334 | `static void parse_seq(char *list)` | Starts the function `parse_seq`. It turns the text after `--seq` into the entries of `cfg.seq`. `main` calls it in line 2527. |
| 1335 | `{` | Opens the body of `parse_seq`. |
| 1336 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. Each pass of the loop handles one entry, in the order of the list. This order is the order in which the kernels run in each round. |
| 1337 | `        char *at = strchr(tok, '@');` | `at`: the place of an `@` in the entry, or NULL when the entry has none. An entry may have the form `KERNEL@SIZE`. |
| 1338 | `        int k = 0;` | `k`: the index into the kernel table. The search of line 1341 starts at entry 0. |
| 1339 | `        if (at)` | Tests whether the entry has an `@`. |
| 1340 | `            *at = '\0';` | Ends the name at the `@`: a zero byte replaces the `@`. |
| 1341 | `        while (k < K_COUNT && strcmp(tok, kernels[k].name))` | Searches the kernel table `kernels[]` (line 1051) for the name, from the first entry on. `strcmp` returns 0 when two texts are equal. The loop stops at the entry with this name. When no entry has the name, it stops with `k` equal to `K_COUNT`, the number of entries. |
| 1342 | `            k++;` | The body of the search loop: goes on to the next entry of the table. |
| 1343 | `        if (k == K_COUNT \|\| cfg.nseq == MAX_SEQ) {` | Tests for two defects: the name is not in the table, or `cfg.seq` already holds 64 entries (`MAX_SEQ`). |
| 1344 | `            fprintf(stderr, "bad --seq entry: %s\n", tok);` | Prints `bad --seq entry:` and the name to stderr. |
| 1345 | `            exit(2);` | Ends the program with exit status 2. |
| 1346 | `        }` | Ends the `if` of line 1343. |
| 1347 | `        cfg.seq[cfg.nseq].k = k;` | Stores the index of the kernel in the next free entry of `cfg.seq`. |
| 1348 | `        cfg.seq[cfg.nseq].bytes = at ? parse_bytes(at + 1) : 0;` | Stores the size of the entry: the text after the `@`, read by `parse_bytes` (line 301). An entry without `@` gets the size 0 here. `main` later replaces 0 by the `--bytes` value (line 2567). |
| 1349 | `        cfg.nseq++;` | Counts the entry. |
| 1350 | `    }` | Ends the loop of line 1336. |
| 1351 | `}` | Ends the function `parse_seq`. |

### Function `parse_events`: read the `--events` list (lines 1353 to 1378)

| Line | Source | Explanation |
|---:|---|---|
| 1353 | `/* "NAME=CODE,..." or "CODE,...". A code without a name gets the name of its` | Comment: the list has the form `NAME=CODE,...` or `CODE,...`. The sentence about a code without a name starts here. |
| 1354 | ` * position in the list of handoff B.8. */` | Comment: a code without a name gets the name of its place in the event list of section B.8 of the file `handoff.md`, the specification of the first runner. The code has one more rule that the comment does not name: from the sixth place on the name is `ev` plus the place number (lines 1368 to 1369). |
| 1355 | `static void parse_events(char *list)` | Starts the function `parse_events`. It turns the text of an event list into the names `cfg.ev_name` and the codes `cfg.ev_code`. `main` calls it with the text after `--events` (line 2541), and with the text of the environment variable `BWX_EVENTS` (line 2557). |
| 1356 | `{` | Opens the body of `parse_events`. |
| 1357 | `    static const char *by_pos[5] = { "cycles", "instructions", "l1d_refill", "l2d_refill", "ll_miss_rd" };` | `by_pos`: the names for an entry without a name at one of the first 5 places of the list: `cycles`, `instructions`, `l1d_refill`, `l2d_refill` and `ll_miss_rd`. |
| 1358 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. One pass of the loop handles one entry. |
| 1359 | `        char *eq = strchr(tok, '='), *code = eq ? eq + 1 : tok, *end;` | `eq`: the place of the `=` sign in the entry, or NULL. `code`: the text of the code. It is the text after the `=`, or the whole entry when the entry has no `=`. `end` is used in line 1370. |
| 1360 | `        if (eq == tok \|\| cfg.nev == MAX_EV \|\| (eq && (size_t)(eq - tok) >= sizeof cfg.ev_name[0])) {` | Tests for three defects: an entry with an empty name (the `=` is its first character), a 9th entry (`MAX_EV` is 8), and a name of 32 characters or more (the size of one entry of `cfg.ev_name`). |
| 1361 | `            fprintf(stderr, "bad --events entry: %s\n", tok);` | Prints `bad --events entry:` and the entry to stderr. |
| 1362 | `            exit(2);` | Ends the program with exit status 2. |
| 1363 | `        }` | Ends the `if` of line 1360. |
| 1364 | `        if (eq)` | Tests whether the entry has a name. |
| 1365 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "%.*s", (int)(eq - tok), tok);` | Copies the text before the `=` as the name of the event. The format `%.*s` prints only the first `eq - tok` characters of the entry. The program uses the name as a column title in the header line of the C rows (line 2608) and in the error message of `open_counters` (line 1182). |
| 1366 | `        else if (cfg.nev < 5)` | The case of an entry without a name at one of the first 5 places of the list. |
| 1367 | `            strcpy(cfg.ev_name[cfg.nev], by_pos[cfg.nev]);` | The entry gets the name of `by_pos` for its place. |
| 1368 | `        else` | The case of an entry without a name at place 6 or later. |
| 1369 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "ev%d", cfg.nev);` | The entry gets the name `ev` plus its place number counted from 0, for example `ev5`. |
| 1370 | `        cfg.ev_code[cfg.nev] = strtoull(code, &end, 0);` | `strtoull` with base 0 turns the code text into a number. With base 0 a text that starts with `0x` is read as hexadecimal. |
| 1371 | `        if (end == code \|\| *end != '\0') {` | Tests whether the text is not a whole number: no digit was read, or other text follows the number. |
| 1372 | `            fprintf(stderr, "bad --events code: %s\n", code);` | Prints `bad --events code:` and the code text to stderr. |
| 1373 | `            exit(2);` | Ends the program with exit status 2. |
| 1374 | `        }` | Ends the `if` of line 1371. |
| 1375 | `        cfg.nev++;` | Counts the entry. |
| 1376 | `    }` | Ends the loop of line 1358. |
| 1377 | `}` | Ends the function `parse_events`. |

### Trial mode: the comment, the constants and the name tables (lines 1379 to 1414)

| Line | Source | Explanation |
|---:|---|---|
| 1379 | `/*` | Comment: starts the comment about the trial mode. The code of the trial mode goes from here to line 2470. `main` enters it only when an argument is the word `--trial` (lines 2489 to 2491). |
| 1380 | ` * Trial mode (--trial). Design: crb/new-test-kernel/tackle-8mb.md, "Runner` | Comment: the option `--trial` selects the trial mode. Its design is the section "Runner design" of the file `tackle-8mb.md`. |
| 1381 | ` * design". Formats: DECISIONS-bwx8.md.` | Comment: the file `DECISIONS-bwx8.md` describes the formats: the plan file and the output rows. |
| 1382 | ` *` | Comment: an empty line inside the comment. |
| 1383 | ` * The plan file gives the trials of the process. The whole plan is read and` | Comment: the plan file lists the trials of the process. The program reads the whole plan first. The sentence goes on in line 1384. |
| 1384 | ` * checked before the process pins, allocates or opens a counter. A defect` | Comment: the program checks the whole plan before it pins a thread, maps a buffer or opens a counter. The sentence about a defect starts here. |
| 1385 | ` * ends the process with status 2.` | Comment: a defect of the plan ends the process with exit status 2 (line 2138). |
| 1386 | ` *` | Comment: an empty line inside the comment. |
| 1387 | ` * One trial is a list of windows: previous activity (1), prefix (4),` | Comment: one trial is a list of windows. A window runs one kernel on one range of the buffer for a fixed time. The list starts with 1 window of previous activity and 4 windows of the prefix. |
| 1388 | ` * predecessor (1), target (nwin). timed_sequence() runs them. It calls only` | Comment: the list goes on with 1 window of the predecessor and `nwin` target windows. The function `timed_sequence` (line 1579) runs the windows. The comment does not name one case: with `--hot-copy` the function `timed_sequence_hot` (line 1640) runs them in its place. The sentence about its calls starts here. |
| 1389 | ` * the kernels and the clock. With count "read" it also reads the counter` | Comment: `timed_sequence` calls only the kernels and the clock. With the counter state `read` it also reads the counter group. The sentence goes on in line 1390. |
| 1390 | ` * group and the thread CPU clock at the boundaries of the target windows.` | Comment: with the counter state `read` it also reads the thread CPU time. Both readings are taken at the boundaries of the target windows. |
| 1391 | ` * Page state, context switches, counter open and close, and all output lie` | Comment: the readings of the page state and of the context switches, the opening and the closing of the counters, and all output are named here. The sentence ends in line 1392. |
| 1392 | ` * outside the timed sequence.` | Comment: all the steps of line 1391 lie outside the timed sequence. |
| 1393 | ` */` | Comment: the end of the comment. |
| 1394 | `#include <stdarg.h>` | Includes the header `stdarg.h`. It gives `va_list`, `va_start` and `va_end` for a function with a variable number of arguments. The function `plan_bad` uses them (line 2138). |
| 1395 | `#include <sys/resource.h>` | Includes the header `sys/resource.h`. It gives the call `getrusage`, which the function `switches` uses (line 1740). |
| 1397 | `#define BIN_NS 10000000L     /* requested width of a bin: 10 ms */` | `BIN_NS`: the requested width of a bin: 10000000 ns (10 ms). A bin is a part of a target window. Its record holds a clock time and the bytes up to that time (line 1430). |
| 1398 | `#define TRACE_CAP (1L << 20) /* --trace: events kept per trial */` | `TRACE_CAP`: the largest number of events that the trace keeps per trial: 1048576 (2 to the power 20). The trace is the event log of the option `--trace`. |
| 1399 | `#define PLAN_LINE1 "# bwx8-plan v1"` | `PLAN_LINE1`: the text that the first line of a plan file must have (line 2344). |
| 1400 | `#define PLAN_LINE3 "# trial cond rep prev pfx pred tgt nwin win_ms count bins"` | `PLAN_LINE3`: the text that the third line of a plan file must have (line 2349). It names the 11 fields of a trial line. |
| 1401 | `#define PLAN_FIELDS 11` | `PLAN_FIELDS`: a trial line of the plan has 11 fields. |
| 1402 | `#define MAX_PAIRS 64` | `MAX_PAIRS`: the second line of a plan holds at most 64 pairs of the form `key=value` (line 2227). |
| 1403 | `#define MAX_NWIN 4096` | `MAX_NWIN`: a trial has at most 4096 target windows (line 2279). |
| 1404 | `#define MAX_MS 3600000L` | `MAX_MS`: a duration of the plan is at most 3600000 ms (1 hour). |
| 1405 | `#define MAX_REC_BYTES (256UL << 20) /* bound of the record storage of one plan */` | `MAX_REC_BYTES`: the records of one plan may need at most 256 MiB (268435456 bytes) of memory (line 2303). |
| 1407 | `enum { PH_PREV, PH_PREFIX, PH_PRED, PH_TARGET };` | Number codes of the four phases of a trial, from 0 to 3: previous activity, prefix, predecessor and target. |
| 1408 | `enum { CS_CLOSED, CS_OPEN, CS_READ, CS_FAIL };` | Number codes of the counter state of a trial, from 0 to 3: closed, open, read and fail. |
| 1409 | `enum { EV_CLOCK, EV_KERNEL_FIRST, EV_COUNT_READ, EV_CPU_CLOCK, EV_PAGE_READ, EV_RUSAGE, EV_OUTPUT, EV_COUNT_OPEN, EV_COUNT_CLOSE };` | Number codes of the nine kinds of trace event: a clock read, the first kernel call of a window, a reading of the counter group, a reading of the thread CPU time, a reading of the page state, a `getrusage` call, an output step, the opening of the counter group and its closing. |
| 1410 | `static const char *const phase_name[] = { "prev", "prefix", "pred", "target" };` | `phase_name`: the printed names of the four phases, in the order of line 1407. The W rows and the TR rows show them (line 1912, line 1978). |
| 1411 | `static const char *const count_name[] = { "closed", "open", "read", "fail" };` | `count_name`: the printed names of the four counter states, in the order of line 1408. The E row shows one of them (line 1973). |
| 1412 | `static const char *const event_name[] = { "clock", "kernel_first", "count_read", "cpu_clock", "page_read",` | `event_name`: the printed names of the trace events, in the order of line 1409. The TR rows show them (line 1978, line 1981). This line holds the first five names. |
| 1413 | `                                          "rusage", "output", "count_open", "count_close" };` | Continues the list of line 1412: the last four names. |

### Trial mode: the structures of the plan, the windows, the records and the trace (lines 1415 to 1470)

| Line | Source | Explanation |
|---:|---|---|
| 1415 | `/* One kernel on a range for a time. k < 0: this part is absent ("-"). */` | Comment: a part is one kernel on one range for a time. A `k` below 0 means that the plan leaves this part out. The plan then holds the text `-` in its place. |
| 1416 | `struct part {` | Starts `struct part`: one kernel field of a trial line of the plan. |
| 1417 | `    int k;` | `k`: the index of the kernel in the kernel table, or -1 for a part that the plan leaves out. |
| 1418 | `    uint64_t size;` | `size`: the number of bytes of the range: the first `size` bytes of the buffer. |
| 1419 | `    long ms;` | `ms`: the duration in ms. The target part has no duration of its own and keeps 0 here. |
| 1420 | `};` | Ends `struct part`. |
| 1422 | `/* One line of the plan. */` | Comment: one line of the plan. |
| 1423 | `struct trial {` | Starts `struct trial`: one trial line of the plan file. |
| 1424 | `    char *f[PLAN_FIELDS]; /* the fields as text, for the S row */` | `f`: the 11 fields of the line as text. `print_s` prints them in the S row (line 1886). The comment says the same. |
| 1425 | `    int nwin, count, bins;` | `nwin`: the number of target windows. `count`: the counter state that the plan asks for (a code of line 1408). `bins`: 1 when the target windows record bins, 0 if not. |
| 1426 | `    long win_ms;` | `win_ms`: the requested duration of one target window, in ms. |
| 1427 | `    struct part prev, pfx, pred, tgt;` | The four parts of the trial: previous activity (`prev`), prefix (`pfx`), predecessor (`pred`) and target (`tgt`). |
| 1428 | `};` | Ends `struct trial`. |
| 1430 | `struct bin {` | Starts `struct bin`: one bin of a target window. |
| 1431 | `    int64_t t_end;  /* a clock read of the window loop */` | `t_end`: the clock time that closed the bin, in ns. The comment says: a clock read of the window loop. The loop reads the clock no more often with bins than without them. |
| 1432 | `    uint64_t bytes; /* bytes since the start of the window */` | `bytes`: the bytes that the window has counted from its start to that clock read. |
| 1433 | `};` | Ends `struct bin`. |
| 1435 | `/* One window. set_windows() fills the first group of fields before the first` | Comment: one window. `set_windows` (line 1815) fills the first group of fields (lines 1438 to 1443) before the first trial. The sentence about the second group starts here. |
| 1436 | ` * trial. timed_sequence() fills the second group. */` | Comment: `timed_sequence` fills the second group of fields (lines 1445 to 1447) when the window runs. The comment does not name one case: with `--hot-copy` the function `timed_sequence_hot` fills them (lines 1670 to 1673). |
| 1437 | `struct win {` | Starts `struct win`: the record of one window. |
| 1438 | `    int k, phase, widx;` | `k`: the index of the kernel in the kernel table. `phase`: the phase of the window (a code of line 1407). `widx`: the number of the window inside its phase, counted from 0. |
| 1439 | `    uint64_t size;` | `size`: the number of bytes that one kernel call covers: the first `size` bytes of the buffer. |
| 1440 | `    uint64_t passes; /* passes between two clock reads */` | `passes`: the number of kernel calls between two clock reads (line 1832). Each call is one whole pass over the range. |
| 1441 | `    int64_t dur_ns;` | `dur_ns`: the requested duration of the window, in ns. |
| 1442 | `    struct bin *bin; /* NULL: no bins */` | `bin`: the storage for the bins of this window. NULL means that the window records no bins. |
| 1443 | `    int bin_cap;` | `bin_cap`: the number of bins that fit into that storage. |
| 1445 | `    int nbin;` | `nbin`: the number of bins that the window closed. |
| 1446 | `    uint64_t bytes;` | `bytes`: the byte count of the window: `size` times the number of kernel calls. |
| 1447 | `    int64_t t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_start`, `t_end`: the clock read at the start of the window and the last clock read of the window, in ns of the Linux clock `CLOCK_MONOTONIC`. |
| 1448 | `};` | Ends `struct win`. |
| 1450 | `/* The record of one trial. */` | Comment: the record of one trial. |
| 1451 | `struct trec {` | Starts `struct trec`: the results of one trial. |
| 1452 | `    struct win *win;` | `win`: the window records of the trial, in the order in which the windows run. |
| 1453 | `    int nw;` | `nw`: the number of windows of the trial. |
| 1454 | `    struct counts *cnt; /* count "read": nwin + 1 readings, one per target boundary */` | `cnt`: the counter readings of the trial, or NULL. Only a trial with the counter state `read` has them: `nwin + 1` readings, one per boundary of the target windows. |
| 1455 | `    struct page pg[2];  /* before and after the timed sequence */` | `pg`: the page state of the buffer before the timed sequence (entry 0) and after it (entry 1). |
| 1456 | `    long long vm[2][4];` | `vm`: the four counters of `/proc/vmstat` before and after the timed sequence. |
| 1457 | `    uint64_t cpu[2];` | `cpu`: the thread CPU time before and after the timed sequence, in ns. |
| 1458 | `    long nvcsw[2], nivcsw[2];` | `nvcsw`, `nivcsw`: the counts of voluntary and of involuntary context switches of the thread, before and after the timed sequence (lines 1741 to 1742). |
| 1459 | `    long minflt[2]; /* minor page faults of the thread, for the --trace check */` | `minflt`: the count of minor page faults of the thread, before and after the timed sequence. A minor page fault is a page fault that Linux serves without disk access. The first touch of a page is one. The comment says that the check of `--trace` uses the count (line 1988). |
| 1460 | `    int state;   /* CS_* */` | `state`: the counter state of the trial as it ran (a code of line 1408). |
| 1461 | `    int sink_ok; /* 1, 0, or -1 if the trial ran no old read */` | `sink_ok`: the result of the sum check of the old read kernel (line 1797): 1 for a right sum, 0 for a wrong sum, -1 when the trial ran no old read kernel. |
| 1462 | `    int read_fail, close_fail;` | `read_fail`: the number of failed counter readings of the trial. `close_fail`: the number of counter file descriptors that did not close when the group was closed for this trial (line 1765). |
| 1463 | `};` | Ends `struct trec`. |
| 1465 | `struct tev {` | Starts `struct tev`: one event of the trace. |
| 1466 | `    int64_t t;` | `t`: the time of the event in ns. It is the time of the latest clock read (line 1516). |
| 1467 | `    int widx;` | `widx`: the window number of the event. Only the event of the first kernel call of a window sets it. |
| 1468 | `    uint8_t ev, phase;` | `ev`: the kind of event (a code of line 1409). `phase`: the phase of the window (a code of line 1407). |
| 1469 | `};` | Ends `struct tev`. |

### Trial mode: the worker state `struct tw` and the global variables (lines 1471 to 1505)

| Line | Source | Explanation |
|---:|---|---|
| 1471 | `/* The worker of the trial mode. */` | Comment: the worker of the trial mode. |
| 1472 | `struct tw {` | Starts `struct tw`: the state of the one worker thread of the trial mode. |
| 1473 | `    struct thread t; /* a, group_fd, ev_pos, nopen: used as in the interval mode */` | `t`: a `struct thread` (line 272), the record that a worker of the interval mode also has. The comment says that the fields `a`, `group_fd`, `ev_pos` and `nopen` are used as in the interval mode. |
| 1474 | `    uint64_t v;      /* every word of the buffer holds v */` | `v`: the value that every 8-byte word of the `--bytes` range of the buffer holds after the first touch (line 2044, line 2050). The comment says: every word of the buffer holds `v`. |
| 1475 | `    int fd[MAX_EV], nfd;` | `fd`: the file descriptors of the open counters. `nfd`: their number. `count_close` closes them (line 1683). |
| 1476 | `    int group_open; /* an open was tried and no close followed */` | `group_open`: 1 when the worker has tried to open the counter group and has not closed it after that. |
| 1477 | `    int open_fail;  /* events that did not open */` | `open_fail`: the number of events that did not open at the last opening of the group. |
| 1478 | `    int close_fail, read_fail;` | `close_fail`, `read_fail`: the numbers of failed `close` calls and of failed group readings. `run_trial` sets both to 0 for each trial (lines 1770 to 1771). |
| 1479 | `    char open_err[160];` | `open_err`: the error text of the first event that did not open. |
| 1480 | `    /* --trace */` | Comment: the fields below belong to the option `--trace`. |
| 1481 | `    struct tev *log;` | `log`: the event log of the trace. It is NULL without `--trace`. |
| 1482 | `    long nlog, ndrop;` | `nlog`: the number of events in the log. `ndrop`: the number of events that did not fit into the log. |
| 1483 | `    int64_t last_t;` | `last_t`: the time of the latest clock read. An event that is not a clock read gets this time. |
| 1484 | `    int cur_phase, cur_widx;` | `cur_phase`, `cur_widx`: the phase and the number of the window whose first kernel call was logged last (line 1540). |
| 1485 | `};` | Ends `struct tw`. |
| 1487 | `static struct {` | Starts the definition of `plan`, the variable that holds the plan and the options of the trial mode. |
| 1488 | `    const char *path;` | `path`: the path of the plan file (option `--plan`). |
| 1489 | `    uint64_t hash;` | `hash`: a 64-bit checksum of the bytes of the plan file (lines 2332 to 2334). |
| 1490 | `    char *pair[MAX_PAIRS];` | `pair`: the `key=value` pairs of the second line of the plan, as text. |
| 1491 | `    int npair;` | `npair`: the number of these pairs. |
| 1492 | `    struct trial *tr;` | `tr`: the trials of the plan, one `struct trial` per trial line. |
| 1493 | `    int n;` | `n`: the number of trials. |
| 1494 | `    int ctl_cpu, trace;` | `ctl_cpu`: the CPU of the controlling thread (option `--ctl-cpu`, default 0). `trace`: 1 with the option `--trace`. |
| 1495 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 1496 | `    size_t rec_pad; /* --rec-pad: unused bytes before win[] in the record block */` | `rec_pad`: the value of `--rec-pad`: the number of unused bytes before the window records in the record block (line 1862). |
| 1497 | `    int hot_copy;   /* --hot-copy: timed_sequence_hot() runs the windows */` | `hot_copy`: 1 with the option `--hot-copy`. Then `timed_sequence_hot` runs the windows (lines 1789 to 1790). |
| 1498 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 1499 | `} plan;` | Ends the definition of `plan`. Every field starts at 0. |
| 1501 | `static struct trec *rec;` | `rec`: the records of all trials, one `struct trec` per trial. `alloc_records` sets the pointer (line 1858). |
| 1502 | `static struct {` | Starts the definition of `recsz`, the sizes of the record storage. |
| 1503 | `    size_t windows, bins, counts, trace, bytes;` | `windows`, `bins`, `counts`, `trace`: the numbers of window records, bins, counter readings and trace events that the plan needs. `bytes`: the size of the record block in bytes. `plan_trial` computes all five (lines 2293 to 2301). |
| 1504 | `} recsz;` | Ends the definition of `recsz`. |

### Trial mode: the trace helpers `tev_add`, `tclock` and `tcpu` (lines 1506 to 1535)

| Line | Source | Explanation |
|---:|---|---|
| 1506 | `/* --trace. An event that is not a clock read carries the time of the latest` | Comment: the option `--trace`. An event that is not a clock read carries the time of the latest clock read. The reason follows in line 1507. |
| 1507 | ` * clock read: the trace adds no clock read of its own. */` | Comment: the trace adds no clock read of its own. |
| 1508 | `static inline void tev_add(struct tw *w, int ev, int phase, int widx)` | Starts the function `tev_add`. It appends one event to the trace: the kind `ev`, the phase and the window number. Without `--trace` it does nothing. |
| 1509 | `{` | Opens the body of `tev_add`. |
| 1510 | `    if (!w->log)` | Tests whether there is no log. That is the case without `--trace`. |
| 1511 | `        return;` | Without a log the function returns immediately. |
| 1512 | `    if (w->nlog == TRACE_CAP) {` | Tests whether the log is full: it holds `TRACE_CAP` (1048576) events. |
| 1513 | `        w->ndrop++;` | A full log does not keep the event. It only counts it in `ndrop`. |
| 1514 | `        return;` | The function then returns and stores nothing. |
| 1515 | `    }` | Ends the `if` of line 1512. |
| 1516 | `    w->log[w->nlog++] = (struct tev){ .t = w->last_t, .widx = widx, .ev = (uint8_t)ev, .phase = (uint8_t)phase };` | Appends the event to the log. Its time is `last_t`, the time of the latest clock read. |
| 1517 | `}` | Ends the function `tev_add`. |
| 1519 | `static inline int64_t tclock(struct tw *w)` | Starts the function `tclock`. It reads the clock for the trial mode and returns the time in ns. Every clock read of a timed sequence goes through it (line 1589, line 1596). |
| 1520 | `{` | Opens the body of `tclock`. |
| 1521 | `    int64_t t = now_ns();` | Reads the clock with `now_ns` (line 294). |
| 1522 | `    if (w->log) {` | Tests whether a log exists (`--trace`). |
| 1523 | `        w->last_t = t;` | Stores the time as the time of the latest clock read. |
| 1524 | `        tev_add(w, EV_CLOCK, 0, 0);` | Logs the clock read as an event. |
| 1525 | `    }` | Ends the `if` of line 1522. |
| 1526 | `    return t;` | Returns the time. |
| 1527 | `}` | Ends the function `tclock`. |
| 1529 | `static uint64_t tcpu(struct tw *w)` | Starts the function `tcpu`. It returns the thread CPU time in ns and logs the reading. |
| 1530 | `{` | Opens the body of `tcpu`. |
| 1531 | `    uint64_t c = cpu_ns();` | Reads the thread CPU time with `cpu_ns` (line 1193). |
| 1532 | `    tev_add(w, EV_CPU_CLOCK, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 1533 | `    return c;` | Returns the CPU time. |
| 1534 | `}` | Ends the function `tcpu`. |

### Trial mode: the functions `tcall` and `tcount` (lines 1536 to 1568)

| Line | Source | Explanation |
|---:|---|---|
| 1536 | `/* Every kernel call of a trial goes through here, and from here through the` | Comment: every kernel call of a trial goes through this function, and from here through the unchanged function `call`. With `--hot-copy` the first part is no longer true: the kernel calls then go through `tcall_hot` (line 1619), and from there through `call`. |
| 1537 | ` * unchanged call(). The trace gets the first call of each window. */` | Comment: the trace gets the first call of each window. |
| 1538 | `static inline void tcall(struct tw *w, const struct win *r, volatile uint64_t *sink)` | Starts the function `tcall`. It runs the kernel of the window `r` once on the first `r->size` bytes of the buffer. |
| 1539 | `{` | Opens the body of `tcall`. |
| 1540 | `    if (w->log && (r->phase != w->cur_phase \|\| r->widx != w->cur_widx)) {` | Tests, only with `--trace`, whether this call belongs to another window than the call before it. |
| 1541 | `        w->cur_phase = r->phase;` | Remembers the phase of the new window. |
| 1542 | `        w->cur_widx = r->widx;` | Remembers the number of the new window. |
| 1543 | `        tev_add(w, EV_KERNEL_FIRST, r->phase, r->widx);` | Logs the first kernel call of the window as an event. |
| 1544 | `    }` | Ends the `if` of line 1540. |
| 1545 | `    call(&kernels[r->k], &w->t, 0, r->size, 0, sink);` | The kernel call. It goes through `call` (line 1075), the function that the interval mode also uses: offset 0, `r->size` bytes, and 0 as the store value. The plan accepts read kernels only (line 2206), and a read kernel does not use the store value. |
| 1546 | `}` | Ends the function `tcall`. |
| 1548 | `/* Group read and thread CPU clock, at a boundary of a target window. Not` | Comment: the function takes a group reading and reads the thread CPU clock, at a boundary of a target window. The sentence about inlining starts here. |
| 1549 | ` * inlined: build8.sh lists the branch targets of timed_sequence(), and this` | Comment: the function is not inlined. The script `build8.sh` lists the branch targets of `timed_sequence`. The sentence goes on in line 1550. |
| 1550 | ` * function must be one name there. */` | Comment: this function must be one name in that list. |
| 1551 | `__attribute__((noinline)) static void tcount(struct tw *w, struct counts *c)` | Starts the function `tcount`. It reads the counter group and then the thread CPU time into `c`. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 1552 | `{` | Opens the body of `tcount`. |
| 1553 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest group reading: 3 header words plus 8 counter values, 8 bytes each. |
| 1554 | `    if (w->t.group_fd >= 0) {` | Tests whether a counter group is open. |
| 1555 | `        ssize_t want = (ssize_t)((3 + (size_t)w->t.nopen) * sizeof buf[0]);` | `want`: the size in bytes that a complete reading must have: 3 header words plus one word per open counter, 8 bytes each. |
| 1556 | `        if (read(w->t.group_fd, buf, sizeof buf) != want \|\| buf[0] != (uint64_t)w->t.nopen) {` | One `read` on the group leader. The reading is rejected when its size is not `want`, or when its counter number `nr` is not the number of open counters. |
| 1557 | `            w->read_fail++;` | A rejected reading only adds 1 to `read_fail`. In `read_group` a rejected reading ends the process (lines 1206 to 1209). |
| 1558 | `        } else {` | The case of a good reading. |
| 1559 | `            c->enabled = buf[1];` | Stores the enabled time of the group, in ns. |
| 1560 | `            c->running = buf[2];` | Stores the running time of the group, in ns. |
| 1561 | `            for (int i = 0; i < w->t.nopen; i++)` | Loop over the open counters. |
| 1562 | `                c->val[i] = buf[3 + i];` | Stores one value per open counter. |
| 1563 | `        }` | Ends the `else` of line 1558. |
| 1564 | `        tev_add(w, EV_COUNT_READ, 0, 0);` | Logs the group reading as an event. Without `--trace` this call does nothing. |
| 1565 | `    }` | Ends the `if` of line 1554. |
| 1566 | `    c->cpu_ns = tcpu(w);` | Reads the thread CPU time through `tcpu` (line 1529) and stores it. This line runs also when no group is open. |
| 1567 | `}` | Ends the function `tcount`. |

### Function `timed_sequence` (trial mode): the timed windows of one trial (lines 1569 to 1615)

| Line | Source | Explanation |
|---:|---|---|
| 1569 | `/*` | Comment: starts the comment of the function `timed_sequence`. The comment ends in line 1578. |
| 1570 | ` * The timed sequence of one trial. Each window runs whole passes over` | Comment: the function is the timed sequence of one trial. Each window runs whole passes over its range. The sentence goes on in line 1571. |
| 1571 | ` * [0, size) and reads the clock after every "passes" passes. It ends at the` | Comment: the range is the first `size` bytes of the buffer. The window reads the clock after every `passes` passes. The sentence about the end of a window starts here. |
| 1572 | ` * first clock read at or after its duration. At a boundary the clock is read` | Comment: a window ends at the first clock read at or after its duration. The sentence about a boundary between two windows starts here. |
| 1573 | ` * for the end of the window and again for the start of the next one, so the` | Comment: at a boundary the clock is read once for the end of the window and once more for the start of the next window. The sentence goes on in line 1574. |
| 1574 | ` * gap is measured. No output, allocation, page read, sleep or warm-up pass` | Comment: so the gap between two windows is measured. The function holds no output, no allocation, no reading of the page state, no sleep and no warm-up pass. This sentence ends in line 1575. |
| 1575 | ` * is in here. Not inlined: build8.sh and test_runner8.py read the branch` | Comment: the function is not inlined. The script `build8.sh` and the test `test_runner8.py` read the branch targets of this function from the machine code. The sentence goes on in line 1576. |
| 1576 | ` * targets of this function from the machine code. Only clock_gettime, the` | Comment: only three branch targets are allowed in this function. The first is the library function `clock_gettime`, which reads the clock. The list goes on in line 1577. |
| 1577 | ` * kernel call of call() and tcount() are allowed there.` | Comment: the other two allowed targets are the kernel call of `call` and the function `tcount`. |
| 1578 | ` */` | Comment: the end of the comment. |
| 1579 | `__attribute__((noinline)) static void timed_sequence(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)` | Starts the function `timed_sequence`. It runs all windows of the trial record `r`, one after another. For each window it stores the byte count and two clock times. `count_read` is 1 for a trial with the counter state `read`. `sink` receives the sum of an old read kernel. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 1580 | `{` | Opens the body of `timed_sequence`. |
| 1581 | `    for (int i = 0; i < r->nw; i++) {` | Loop over the windows of the trial, in the order in which they run. |
| 1582 | `        struct win *x = &r->win[i];` | `x`: the record of this window. |
| 1583 | `        uint64_t bytes = 0;` | `bytes`: the byte count of the window. It starts at 0. |
| 1584 | `        int64_t t0, t1, next_bin;` | Clock values in ns: `t0` (the start of the window), `t1` (the latest clock read) and `next_bin` (the requested end of the bin that is open). |
| 1585 | `        int nbin = 0;` | `nbin`: the number of bins that this window has closed. |
| 1587 | `        if (count_read && x->phase == PH_TARGET)` | Tests whether the trial reads counters and this window is a target window. |
| 1588 | `            tcount(w, &r->cnt[x->widx]);` | Counter reading before a target window: `tcount` (line 1551) reads the counter group and the thread CPU time into the reading with the number `widx`. It runs before the start clock read of line 1589. So it lies outside the window. |
| 1589 | `        t0 = tclock(w);` | Start of the window: the clock read `t0` (`tclock`, line 1519). |
| 1590 | `        next_bin = t0 + BIN_NS;` | The first bin has its requested end 10 ms (`BIN_NS`) after `t0`. |
| 1591 | `        do {` | Starts the timed loop of the window. Its body runs at least once. |
| 1592 | `            for (uint64_t c = 0; c < x->passes; c++) {` | Runs `passes` kernel calls without a clock read between them. |
| 1593 | `                tcall(w, x, sink);` | Timed kernel call: one pass of the kernel of the window over the first `size` bytes of the buffer (`tcall`, line 1538). |
| 1594 | `                bytes += x->size;` | Bytes counted: each call adds `size`, the size of the range that was passed to the kernel. Nothing is counted inside a kernel. |
| 1595 | `            }` | Ends the `for` of line 1592. |
| 1596 | `            t1 = tclock(w);` | Clock read after the passes: `t1`. The clock is never read inside a pass. |
| 1597 | `            /* A bin closes on this clock read if its requested end has` | Comment: a bin closes at this clock read when its requested end has passed. The sentence about the last bin starts here. |
| 1598 | `             * passed. The last clock read of the window closes the last bin. */` | Comment: the last clock read of the window closes the last bin. |
| 1599 | `            if (x->bin && (t1 >= next_bin \|\| t1 - t0 >= x->dur_ns) && nbin < x->bin_cap) {` | Tests three things. The window records bins. A bin can close now: its requested end has passed, or the window is over. The storage has room for one more bin. |
| 1600 | `                x->bin[nbin].t_end = t1;` | Stores the clock time `t1` as the end of the bin. |
| 1601 | `                x->bin[nbin].bytes = bytes;` | Stores the bytes that the window has counted up to this clock read. |
| 1602 | `                nbin++;` | Counts the bin. |
| 1603 | `                while (next_bin <= t1)` | Moves the requested end of the next bin forward in steps of 10 ms until it lies after `t1`. |
| 1604 | `                    next_bin += BIN_NS;` | The body of the loop of line 1603: one step of 10 ms. |
| 1605 | `            }` | Ends the `if` of line 1599. |
| 1606 | `        } while (t1 - t0 < x->dur_ns);` | Stop rule of a window. The loop repeats while less than `dur_ns` has passed after `t0`. So a window ends at its first clock read at or after its requested duration, and only at the end of a whole pass. |
| 1607 | `        x->bytes = bytes;` | Stores the byte count in the window record. The W row prints it (line 1913). This function computes no rate. |
| 1608 | `        x->t_start = t0;` | Stores `t0` as the start time of the window. |
| 1609 | `        x->t_end = t1;` | Stores the last `t1` as the end time of the window. The next window reads the clock again for its own start (line 1589). So the time between two windows is measured and belongs to no window. |
| 1610 | `        x->nbin = nbin;` | Stores the number of bins that the window closed. |
| 1611 | `    }` | Ends the loop over the windows (line 1581). |
| 1612 | `    if (count_read)` | Tests whether the trial reads counters. |
| 1613 | `        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);` | Last counter reading, after the last window. It goes into the reading with the number of the last target window plus 1. So a trial with `nwin` target windows has `nwin + 1` readings. |
| 1614 | `}` | Ends the function `timed_sequence`. |

### Function `tcall_hot` (trial mode): `tcall` with value arguments (lines 1616 to 1628)

| Line | Source | Explanation |
|---:|---|---|
| 1616 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. This block ends in line 1679. |
| 1617 | `/* tcall() for timed_sequence_hot(): the kernel index, the phase, the window` | Comment: this function is the `tcall` of `timed_sequence_hot`. The kernel index, the phase and the window number come as values. The list goes on in line 1618. |
| 1618 | ` * index and the size come by value, so no field of win[i] is read here. */` | Comment: the size also comes as a value. So the function reads no field of the window record. |
| 1619 | `static inline void tcall_hot(struct tw *w, int k, int phase, int widx, uint64_t size, volatile uint64_t *sink)` | Starts the function `tcall_hot`. It does the same as `tcall` (line 1538), but the kernel index `k`, the phase, the window number and the size arrive as arguments. So it reads no field of the window record. |
| 1620 | `{` | Opens the body of `tcall_hot`. |
| 1621 | `    if (w->log && (phase != w->cur_phase \|\| widx != w->cur_widx)) {` | Tests, only with `--trace`, whether this call belongs to another window than the call before it. |
| 1622 | `        w->cur_phase = phase;` | Remembers the phase of the new window. |
| 1623 | `        w->cur_widx = widx;` | Remembers the number of the new window. |
| 1624 | `        tev_add(w, EV_KERNEL_FIRST, phase, widx);` | Logs the first kernel call of the window as an event. |
| 1625 | `    }` | Ends the `if` of line 1621. |
| 1626 | `    call(&kernels[k], &w->t, 0, size, 0, sink);` | The kernel call. It goes through `call` (line 1075): offset 0, `size` bytes, and 0 as the store value. |
| 1627 | `}` | Ends the function `tcall_hot`. |

### Function `timed_sequence_hot` (trial mode): the variant for `--hot-copy` (lines 1629 to 1679)

| Line | Source | Explanation |
|---:|---|---|
| 1629 | `/*` | Comment: starts the comment of the function `timed_sequence_hot`. The comment ends in line 1639. |
| 1630 | ` * --hot-copy: timed_sequence() with one difference. Before the start clock` | Comment: with the option `--hot-copy` this function runs the windows. It is `timed_sequence` with one difference. The sentence about the difference starts here. |
| 1631 | ` * read of a window it copies the fields of win[i] that the window loop needs` | Comment: before the start clock read of a window the function copies the fields of the window record that the window loop needs. The sentence goes on in line 1632. |
| 1632 | ` * into local variables. After the end clock read it stores bytes, t_start,` | Comment: the copies are local variables. After the end clock read the function stores the byte count and the start time. The list goes on in line 1633. |
| 1633 | ` * t_end and nbin. Between the first pass and the last pass of a window it` | Comment: it also stores the end time and the number of bins. The sentence about the time between the first and the last pass starts here. |
| 1634 | ` * does not read or write win[i]. The compiler cannot read a field again` | Comment: between the first pass and the last pass of a window the function does not read or write the window record. The sentence about the compiler starts here. |
| 1635 | ` * inside the loop in place of the local copy: the loop calls a kernel` | Comment: the compiler cannot read a field again inside the loop in place of the local copy. The reason starts here: the loop calls a kernel. |
| 1636 | ` * through a pointer, and such a call may change any memory. The self-test` | Comment: the kernel is called through a pointer, and such a call may change any memory. The sentence about the self-test starts here. |
| 1637 | ` * checks it on the machine code (test_hot_touch). The same rules as for` | Comment: the self-test checks this on the machine code, in its function `test_hot_touch`. The last sentence of the comment starts here. |
| 1638 | ` * timed_sequence() hold for the calls made here.` | Comment: the calls that this function makes follow the same rules as the calls of `timed_sequence` (lines 1575 to 1577). |
| 1639 | ` */` | Comment: the end of the comment. |
| 1640 | `__attribute__((noinline)) static void timed_sequence_hot(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)` | Starts the function `timed_sequence_hot`. It runs the windows of one trial as `timed_sequence` does (line 1579), with the same arguments. The difference: the window loop works on local copies of the fields of the window record. |
| 1641 | `{` | Opens the body of `timed_sequence_hot`. |
| 1642 | `    for (int i = 0; i < r->nw; i++) {` | Loop over the windows of the trial, in the order in which they run. |
| 1643 | `        struct win *x = &r->win[i];` | `x`: the record of this window. |
| 1644 | `        const int k = x->k, phase = x->phase, widx = x->widx, bin_cap = x->bin_cap;` | Local copies of four fields of the window record: the kernel index, the phase, the window number and the room for bins. |
| 1645 | `        const uint64_t size = x->size, passes = x->passes;` | Local copies of the range size and of the number of passes between two clock reads. |
| 1646 | `        const int64_t dur_ns = x->dur_ns;` | Local copy of the requested duration. |
| 1647 | `        struct bin *const bin = x->bin;` | Local copy of the pointer to the bin storage. |
| 1648 | `        uint64_t bytes = 0;` | `bytes`: the byte count of the window. It starts at 0. |
| 1649 | `        int64_t t0, t1, next_bin;` | Clock values in ns: `t0`, `t1` and `next_bin`, as in line 1584. |
| 1650 | `        int nbin = 0;` | `nbin`: the number of bins that this window has closed. |
| 1652 | `        if (count_read && phase == PH_TARGET)` | Tests whether the trial reads counters and this window is a target window. |
| 1653 | `            tcount(w, &r->cnt[widx]);` | Counter reading before a target window, as in line 1588. It lies outside the window. |
| 1654 | `        t0 = tclock(w);` | Start of the window: the clock read `t0`. |
| 1655 | `        next_bin = t0 + BIN_NS;` | The first bin has its requested end 10 ms (`BIN_NS`) after `t0`. |
| 1656 | `        do {` | Starts the timed loop of the window. Its body runs at least once. |
| 1657 | `            for (uint64_t c = 0; c < passes; c++) {` | Runs `passes` kernel calls without a clock read between them. |
| 1658 | `                tcall_hot(w, k, phase, widx, size, sink);` | Timed kernel call through `tcall_hot` (line 1619): one pass of the kernel over the first `size` bytes of the buffer. |
| 1659 | `                bytes += size;` | Bytes counted: each call adds `size`, the size of the range that was passed to the kernel. |
| 1660 | `            }` | Ends the `for` of line 1657. |
| 1661 | `            t1 = tclock(w);` | Clock read after the passes: `t1`. |
| 1662 | `            if (bin && (t1 >= next_bin \|\| t1 - t0 >= dur_ns) && nbin < bin_cap) {` | The bin test of line 1599, with the local copies: the window records bins, a bin can close now, and the storage has room. |
| 1663 | `                bin[nbin].t_end = t1;` | Stores `t1` as the end of the bin. The bin storage is not a part of the window record. |
| 1664 | `                bin[nbin].bytes = bytes;` | Stores the bytes that the window has counted up to this clock read. |
| 1665 | `                nbin++;` | Counts the bin. |
| 1666 | `                while (next_bin <= t1)` | Moves the requested end of the next bin forward in steps of 10 ms until it lies after `t1`. |
| 1667 | `                    next_bin += BIN_NS;` | The body of the loop of line 1666: one step of 10 ms. |
| 1668 | `            }` | Ends the `if` of line 1662. |
| 1669 | `        } while (t1 - t0 < dur_ns);` | Stop rule of a window, as in line 1606: the window ends at its first clock read at or after its requested duration. |
| 1670 | `        x->bytes = bytes;` | After the end clock read: stores the byte count in the window record. |
| 1671 | `        x->t_start = t0;` | Stores `t0` as the start time of the window. |
| 1672 | `        x->t_end = t1;` | Stores the last `t1` as the end time of the window. |
| 1673 | `        x->nbin = nbin;` | Stores the number of bins that the window closed. |
| 1674 | `    }` | Ends the loop over the windows (line 1642). |
| 1675 | `    if (count_read)` | Tests whether the trial reads counters. |
| 1676 | `        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);` | Last counter reading, after the last window, as in line 1613. |
| 1677 | `}` | Ends the function `timed_sequence_hot`. |
| 1679 | `/* bwx10- */` | Comment: marks the end of the block that `bwx10` added. The block starts in line 1616. The code from here to line 2470 also belongs to the trial mode. |

### Function `count_close` (trial mode): close the counter group (lines 1680 to 1692)

| Line | Source | Explanation |
|---:|---|---|
| 1680 | `static void count_close(struct tw *w)` | Starts the function `count_close`. It closes every counter of the worker and sets the group state of the worker back to closed. |
| 1681 | `{` | Opens the body of `count_close`. |
| 1682 | `    for (int i = 0; i < w->nfd; i++)` | Loop over the counter file descriptors that `count_open` stored in `w->fd` (line 1720). |
| 1683 | `        if (close(w->fd[i]) != 0)` | Closes one counter and tests whether the `close` call failed. |
| 1684 | `            w->close_fail++;` | A failed `close` adds 1 to `w->close_fail`. |
| 1685 | `    w->nfd = 0;` | No file descriptor is stored any more. |
| 1686 | `    w->t.group_fd = -1;` | The group has no leader. |
| 1687 | `    w->t.nopen = 0;` | No event is open. |
| 1688 | `    w->group_open = 0;` | The group counts as closed. |
| 1689 | `    w->open_fail = 0;` | The count of events that did not open is 0 again. |
| 1690 | `    tev_add(w, EV_COUNT_CLOSE, 0, 0);` | Logs the closing as an event. Without `--trace` this call does nothing. |
| 1691 | `}` | Ends the function `count_close`. |

### Function `count_open` (trial mode): open the counter group (lines 1693 to 1727)

| Line | Source | Explanation |
|---:|---|---|
| 1693 | `/* One group, user mode only, opened by the pinned worker for itself. The` | Comment: the worker has one counter group, which counts in user mode only. The pinned worker opens it for itself. The next sentence starts here. |
| 1694 | ` * events count from the open on. An event that does not open is counted in` | Comment: the events count from the moment of the open. The sentence about an event that does not open starts here. |
| 1695 | ` * open_fail and is printed as NA. */` | Comment: an event that does not open is counted in `open_fail` and is printed as `NA`. |
| 1696 | `static void count_open(struct tw *w)` | Starts the function `count_open`. It is the version of `open_counters` (line 1166) for the trial mode: it opens one counter per event of `cfg` and joins the counters into one group. Two things differ. It keeps every file descriptor in `w->fd`: `count_close` needs them to close the group. And it writes no message to stderr. |
| 1697 | `{` | Opens the body of `count_open`. |
| 1698 | `    w->t.group_fd = -1;` | Start state: no group leader. |
| 1699 | `    w->t.nopen = 0;` | Start state: 0 open events. |
| 1700 | `    w->nfd = 0;` | Start state: no stored file descriptor. |
| 1701 | `    w->open_fail = 0;` | Start state: 0 events that did not open. |
| 1702 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `cfg`, in the order of the option `--events`. |
| 1703 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 1704 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. The field `disabled` stays 0, so a counter counts from the moment it is opened. |
| 1705 | `        a.type = (uint32_t)cfg.pmu_type;` | `type`: the PMU type (`--pmu-type`). |
| 1706 | `        a.size = sizeof a;` | `size`: the size of the structure. |
| 1707 | `        a.config = cfg.ev_code[e];` | `config`: the event code of this event. |
| 1708 | `        a.exclude_kernel = 1;` | The counter does not count code of the Linux kernel. |
| 1709 | `        a.exclude_hv = 1;` | The counter does not count code of a hypervisor. With line 1708 it counts in user mode only. |
| 1710 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | One `read` of the group returns the values of all its counters, the enabled time and the running time, as in line 1178. |
| 1711 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, w->t.group_fd, 0);` | The system call `perf_event_open` opens the counter for the calling thread, on any CPU that it runs on, as in line 1179. The first counter starts a new group. A later counter joins the group of the leader. |
| 1712 | `        if (fd < 0) {` | Tests whether the open failed. |
| 1713 | `            if (w->open_fail++ == 0)` | Counts the event as not opened. The test is true only for the first such event of this opening. |
| 1714 | `                snprintf(w->open_err, sizeof w->open_err, "%s type %ld code 0x%llx: %s", cfg.ev_name[e], cfg.pmu_type,` | For the first such event: stores an error text in `w->open_err`: the event name, the PMU type, the event code and the error text of Linux. `emit_trial` prints it in an X row (line 1948). |
| 1715 | `                         (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 1714: the event code and the error text (`strerror(errno)`). |
| 1716 | `            w->t.ev_pos[e] = -1;` | The event gets the position -1. Its field in the C rows is `NA` (lines 1934 to 1935). |
| 1717 | `            continue;` | The loop goes on with the next event. |
| 1718 | `        }` | Ends the `if` of line 1712. |
| 1719 | `        w->t.ev_pos[e] = w->t.nopen++;` | The open succeeded. The event gets its position in a group reading, and `nopen` counts it. |
| 1720 | `        w->fd[w->nfd++] = fd;` | Keeps the file descriptor for `count_close` (line 1683). |
| 1721 | `        if (w->t.group_fd < 0)` | Tests whether the group has no leader yet. |
| 1722 | `            w->t.group_fd = fd;` | The first counter that opens becomes the leader of the group. |
| 1723 | `    }` | Ends the loop over the events (line 1702). |
| 1724 | `    w->group_open = 1;` | The group counts as open from here on. This is also the case when no event opened. |
| 1725 | `    tev_add(w, EV_COUNT_OPEN, 0, 0);` | Logs the opening as an event. Without `--trace` this call does nothing. |
| 1726 | `}` | Ends the function `count_open`. |

### Functions `page_read`, `switches` and `first_multiplexed` (trial mode) (lines 1728 to 1756)

| Line | Source | Explanation |
|---:|---|---|
| 1728 | `static void page_read(struct tw *w, struct trec *r, int at)` | Starts the function `page_read`. It reads the page state of the one buffer of the worker and the four counters of `/proc/vmstat` into the trial record `r`. `at` is 0 before the timed sequence and 1 after it. |
| 1729 | `{` | Opens the body of `page_read`. The `# page_read` lines of the interval mode do not come from this function. `main` prints them in line 2695. |
| 1730 | `    uint64_t *buf[1] = { w->t.a };` | `buf`: the address of the one buffer of the worker. |
| 1731 | `    read_smaps(&r->pg[at], buf, 1);` | `read_smaps` (line 1099) reads the size of the buffer and its part on 2 MiB pages into `r->pg[at]`. |
| 1732 | `    read_vmstat(r->vm[at]);` | `read_vmstat` (line 1129) reads the four counters of `/proc/vmstat` into `r->vm[at]`. |
| 1733 | `    tev_add(w, EV_PAGE_READ, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 1734 | `}` | Ends the function `page_read`. |
| 1736 | `/* Context-switch counts of the calling thread. -1: not readable. */` | Comment: the function reads the context-switch counts of the calling thread. A value of -1 means that a count could not be read. The function also stores the count of minor page faults (line 1743), which the comment does not name. |
| 1737 | `static void switches(struct tw *w, struct trec *r, int at)` | Starts the function `switches`. It stores three counts of the calling thread in the trial record `r`: the voluntary context switches, the involuntary context switches and the minor page faults. `at` is 0 before the timed sequence and 1 after it. |
| 1738 | `{` | Opens the body of `switches`. |
| 1739 | `    struct rusage ru;` | `ru`: the structure that `getrusage` fills. |
| 1740 | `    int ok = getrusage(RUSAGE_THREAD, &ru) == 0;` | `getrusage` with `RUSAGE_THREAD` asks Linux for the resource use of the calling thread. `ok` is 1 when the call succeeded. |
| 1741 | `    r->nvcsw[at] = ok ? ru.ru_nvcsw : -1;` | Stores `ru_nvcsw`, the number of voluntary context switches: the thread stopped running by its own request, usually to wait for something. A failed call stores -1. |
| 1742 | `    r->nivcsw[at] = ok ? ru.ru_nivcsw : -1;` | Stores `ru_nivcsw`, the number of involuntary context switches: Linux took the CPU away from the thread. A failed call stores -1. |
| 1743 | `    r->minflt[at] = ok ? ru.ru_minflt : -1;` | Stores `ru_minflt`, the number of minor page faults. These are page faults that need no disk access. The first touch of a page is one. A failed call stores -1. |
| 1744 | `    tev_add(w, EV_RUSAGE, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 1745 | `}` | Ends the function `switches`. |
| 1747 | `/* The index of the first target window whose counters ran for less time` | Comment: the function returns the index of the first target window whose counters ran for less time than they were enabled. The sentence ends in line 1748. |
| 1748 | ` * than they were enabled, or -1. cnt holds nwin + 1 readings. */` | Comment: it returns -1 when there is no such window. `cnt` holds `nwin + 1` readings. |
| 1749 | `static int first_multiplexed(const struct counts *cnt, int nwin)` | Starts the function `first_multiplexed`. `cnt` holds one counter reading per boundary of the `nwin` target windows. The function looks for a target window in which the counters did not count all the time. |
| 1750 | `{` | Opens the body of `first_multiplexed`. |
| 1751 | `    for (int i = 0; i < nwin; i++)` | Loop over the target windows. |
| 1752 | `        if (cnt[i + 1].running - cnt[i].running < cnt[i + 1].enabled - cnt[i].enabled)` | Compares, for one target window, the growth of the running time with the growth of the enabled time between its two readings. A smaller growth of the running time means that the counters did not count all the time in this window. |
| 1753 | `            return i;` | Returns the index of the first such window. |
| 1754 | `    return -1;` | Returns -1 when there is no such window. |
| 1755 | `}` | Ends the function `first_multiplexed`. |

### Function `run_trial` (trial mode): one trial, without output (lines 1757 to 1800)

| Line | Source | Explanation |
|---:|---|---|
| 1757 | `/* One trial: the work before the timed sequence, the timed sequence, the` | Comment: the function runs one trial: the work before the timed sequence, then the timed sequence. The list ends in line 1758. |
| 1758 | ` * work after it. Prints nothing. */` | Comment: then comes the work after the timed sequence. The function prints nothing. |
| 1759 | `static void run_trial(struct tw *w, const struct trial *p, struct trec *r, volatile uint64_t *sink)` | Starts the function `run_trial`. `p` is the trial of the plan. `r` is the record of the trial. `sink` receives the sum of an old read kernel. |
| 1760 | `{` | Opens the body of `run_trial`. |
| 1761 | `    uint64_t expect = 0;` | `expect`: the sum that the last old read kernel of the trial must return. |
| 1762 | `    int old = -1;` | `old`: the index of the last window with an old read kernel, or -1 when the trial has none. |
| 1764 | `    if (p->count == CS_CLOSED && w->group_open)` | Tests whether the plan wants the counters closed for this trial while the group is open. |
| 1765 | `        count_close(w);` | Then the group is closed (`count_close`, line 1680). |
| 1766 | `    else if (p->count != CS_CLOSED && !w->group_open)` | Tests whether the plan wants counters for this trial (state `open` or `read`) while the group is not open. |
| 1767 | `        count_open(w);` | Then the group is opened (`count_open`, line 1696). It stays open over the next trials until a trial wants it closed. |
| 1768 | `    r->state = p->count != CS_CLOSED && w->open_fail ? CS_FAIL : p->count;` | The record keeps the counter state of the trial. It is `fail` when the trial wants counters and an event did not open. In every other case it is the state of the plan. |
| 1769 | `    r->close_fail = w->close_fail;` | Moves the number of failed `close` calls of line 1765 into the record. |
| 1770 | `    w->close_fail = 0;` | Sets the count of failed `close` calls of the worker to 0. |
| 1771 | `    w->read_fail = 0;` | Sets the count of failed group readings of the worker to 0. |
| 1773 | `    /* The last old read of the trial must leave the sum of its range in the` | Comment: the last old read kernel of the trial must leave the sum of its range in the sink. The sentence ends in line 1774. |
| 1774 | `     * sink. The sink starts with another value, so an old value cannot pass. */` | Comment: the sink starts with another value. So a value from an earlier call cannot pass the check. |
| 1775 | `    for (int i = 0; i < r->nw; i++)` | Loop over the windows of the trial. |
| 1776 | `        if (kernels[r->win[i].k].type == T_OLDREAD)` | Tests whether the kernel of the window has the type `T_OLDREAD`. |
| 1777 | `            old = i;` | `old` keeps the index of the last such window. |
| 1778 | `    if (old >= 0) {` | Tests whether the trial has such a window. |
| 1779 | `        expect = w->v * (r->win[old].size / 8);` | The expected sum. Every 8-byte word of the `--bytes` range of the buffer holds `w->v` (line 2050), and the range of a window lies inside it (line 2208). So the kernel must return `w->v` times the number of words of its range. Only the low 64 bits of the product are kept, as in the sum of the kernel. |
| 1780 | `        *sink = expect + 1;` | The sink starts with the expected sum plus 1. |
| 1781 | `    }` | Ends the `if` of line 1778. |
| 1783 | `    page_read(w, r, 0);` | Before the timed sequence: reads the page state (`page_read`, line 1728). |
| 1784 | `    switches(w, r, 0);` | Before the timed sequence: reads the context switches and the minor page faults (`switches`, line 1737). |
| 1785 | `    r->cpu[0] = tcpu(w);` | Before the timed sequence: reads the thread CPU time (`tcpu`, line 1529). This is the last step before the timed sequence. |
| 1786 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 1787 | `    /* --hot-copy selects the other function. The statement after this block` | Comment: the option `--hot-copy` selects the other function. The sentence about the next statement starts here. |
| 1788 | `     * is the else branch. */` | Comment: the statement after this block (line 1793) is the `else` branch. |
| 1789 | `    if (plan.hot_copy)` | Tests for the option `--hot-copy`. |
| 1790 | `        timed_sequence_hot(w, r, p->count == CS_READ, sink);` | With `--hot-copy`: `timed_sequence_hot` (line 1640) runs the timed sequence. The third argument is 1 for the counter state `read`. Then the function also reads the counter group at the boundaries of the target windows. |
| 1791 | `    else` | Starts the `else` branch. Its statement is line 1793. |
| 1792 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 1793 | `    timed_sequence(w, r, p->count == CS_READ, sink);` | `timed_sequence` (line 1579) runs the timed sequence. The clock reads that time the windows are inside that function. The third argument is 1 for the counter state `read`. Then the function also reads the counter group at the boundaries of the target windows. This statement is the `else` branch of line 1789: it runs without `--hot-copy`. |
| 1794 | `    r->cpu[1] = tcpu(w);` | After the timed sequence: reads the thread CPU time again. |
| 1795 | `    switches(w, r, 1);` | After the timed sequence: reads the context switches and the minor page faults again. |
| 1796 | `    page_read(w, r, 1);` | After the timed sequence: reads the page state again. So the three readings come in the reverse order of lines 1783 to 1785. |
| 1797 | `    r->sink_ok = old < 0 ? -1 : *sink == expect;` | `sink_ok`: -1 when the trial ran no old read kernel. For a trial that ran one: 1 when the sink holds the expected sum, 0 when it does not. |
| 1798 | `    r->read_fail = w->read_fail;` | Moves the number of failed group readings of the timed sequence into the record. |
| 1799 | `}` | Ends the function `run_trial`. |

### Functions `trial_windows`, `window_bins` and `set_windows` (trial mode) (lines 1801 to 1841)

| Line | Source | Explanation |
|---:|---|---|
| 1801 | `static int trial_windows(const struct trial *p)` | Starts the function `trial_windows`. It returns the number of windows of one trial. |
| 1802 | `{` | Opens the body of `trial_windows`. |
| 1803 | `    return (p->prev.k >= 0) + 4 * (p->pfx.k >= 0) + (p->pred.k >= 0) + p->nwin;` | Adds the windows of the phases that the trial has: 1 for the previous activity, 4 for the prefix, 1 for the predecessor and `nwin` for the target. The plan may leave out each of the first three. Then the field `k` of that part is -1, and the phase adds 0. |
| 1804 | `}` | Ends the function `trial_windows`. |
| 1806 | `/* Bins that one target window can close: one per 10 ms that ends inside the` | Comment: the number of bins that one target window can close: one per 10 ms that ends inside the window. The list goes on in line 1807. |
| 1807 | ` * window, one at the end of the window, and one spare. */` | Comment: plus one bin at the end of the window, and one extra bin. |
| 1808 | `static int window_bins(const struct trial *p)` | Starts the function `window_bins`. It returns the number of bins for which one target window of the trial gets storage. |
| 1809 | `{` | Opens the body of `window_bins`. |
| 1810 | `    return p->bins ? (int)(p->win_ms / 10) + 2 : 0;` | For a trial with bins: the window duration `win_ms` divided by 10 and rounded down, plus 2. The 10 is the requested length of a bin in ms (`BIN_NS`, line 1397). For a trial without bins: 0. |
| 1811 | `}` | Ends the function `window_bins`. |
| 1813 | `/* Fills the plan part of the windows of one trial. bin: storage for` | Comment: the function fills the plan part of the windows of one trial. The sentence about `bin` starts here. |
| 1814 | ` * nwin * window_bins(p) bins. */` | Comment: `bin` is the storage for `nwin` times `window_bins(p)` bins. |
| 1815 | `static void set_windows(const struct trial *p, struct win *win, struct bin *bin)` | Starts the function `set_windows`. It fills the plan fields of all window records of the trial `p`, in the order in which the windows run. `win` points to the first window record of the trial. |
| 1816 | `{` | Opens the body of `set_windows`. |
| 1817 | `    const struct {` | Starts the definition of the table `ph`, with one entry per phase. |
| 1818 | `        const struct part *part;` | `part`: the part of the trial that the phase runs. |
| 1819 | `        int phase, n;` | `phase`: the code of the phase. `n`: the number of windows of the phase. |
| 1820 | `    } ph[4] = { { &p->prev, PH_PREV, 1 }, { &p->pfx, PH_PREFIX, 4 }, { &p->pred, PH_PRED, 1 }, { &p->tgt, PH_TARGET, p->nwin } };` | The four entries, in the order of the run: previous activity (1 window), prefix (4 windows), predecessor (1 window) and target (`nwin` windows). |
| 1821 | `    struct win *x = win;` | `x`: the window record that is filled next. |
| 1822 | `    for (int i = 0; i < 4; i++) {` | Loop over the four phases. |
| 1823 | `        const struct part *part = ph[i].part;` | `part`: the part of this phase. |
| 1824 | `        if (part->k < 0)` | Tests whether the plan leaves this phase out. |
| 1825 | `            continue;` | Such a phase gets no window. |
| 1826 | `        for (int j = 0; j < ph[i].n; j++, x++) {` | Loop over the windows of the phase. After each window `x` moves on to the next record. |
| 1827 | `            memset(x, 0, sizeof *x);` | Sets every field of the record to 0. |
| 1828 | `            x->k = part->k;` | The kernel of the window. |
| 1829 | `            x->phase = ph[i].phase;` | The phase of the window. |
| 1830 | `            x->widx = j;` | The number of the window inside its phase, counted from 0. |
| 1831 | `            x->size = part->size;` | The size of the range of the window, in bytes. |
| 1832 | `            x->passes = CHECK_BYTES / part->size ? CHECK_BYTES / part->size : 1;` | `passes`: the number of kernel calls between two clock reads. It is 8 MiB (`CHECK_BYTES`, line 97) divided by the range size, rounded down, and at least 1. |
| 1833 | `            x->dur_ns = (ph[i].phase == PH_TARGET ? p->win_ms : part->ms / ph[i].n) * 1000000L;` | `dur_ns`: the requested duration of the window in ns. A target window gets `win_ms`. Every other window gets the duration of its phase divided by the number of windows of the phase. So each of the 4 prefix windows gets a quarter of the prefix duration. |
| 1834 | `            if (ph[i].phase == PH_TARGET && p->bins) {` | Tests whether this is a target window of a trial with bins. |
| 1835 | `                x->bin_cap = window_bins(p);` | `bin_cap`: the number of bins that the window can close (`window_bins`, line 1808). |
| 1836 | `                x->bin = bin + (size_t)j * (size_t)x->bin_cap;` | The window gets its own part of the bin storage: target window `j` starts at bin `j * bin_cap`. |
| 1837 | `            }` | Ends the `if` of line 1834. |
| 1838 | `        }` | Ends the loop over the windows of the phase (line 1826). |
| 1839 | `    }` | Ends the loop over the phases (line 1822). |
| 1840 | `}` | Ends the function `set_windows`. |

### Function `alloc_records` (trial mode): one memory block for all trial records (lines 1842 to 1880)

| Line | Source | Explanation |
|---:|---|---|
| 1842 | `/* The record storage of all trials: one block, sized from the plan, written` | Comment: the record storage of all trials is one block. Its size comes from the plan. The sentence goes on in line 1843. |
| 1843 | ` * once here so that no page of it is first touched during a trial.` | Comment: the block is written once here. So no page of it gets its first touch during a trial. |
| 1844 | ` * plan_trial() has filled recsz and has checked its bound. */` | Comment: `plan_trial` has filled `recsz` and has checked its upper limit (line 2303). |
| 1845 | `static void alloc_records(struct tw *w)` | Starts the function `alloc_records`. It allocates the record block, touches every page of it, and divides it into the arrays of the records. |
| 1846 | `{` | Opens the body of `alloc_records`. |
| 1847 | `    char *mem = malloc(recsz.bytes);` | Allocates one block of `recsz.bytes` bytes with `malloc`. |
| 1848 | `    if (!mem) {` | Tests whether the allocation failed. |
| 1849 | `        fprintf(stderr, "no memory for %zu bytes of records\n", recsz.bytes);` | Prints `no memory for`, the number of bytes and `bytes of records` to stderr. |
| 1850 | `        exit(2);` | Ends the process with exit status 2. |
| 1851 | `    }` | Ends the `if` of line 1848. |
| 1852 | `    memset(mem, 0, recsz.bytes);` | Fills the block with zero bytes. |
| 1853 | `    /* gcc joins malloc and memset into calloc, and calloc does not write a` | Comment: the compiler gcc joins `malloc` and `memset` into one call of `calloc`. `calloc` does not write a new block. The sentence ends in line 1854. |
| 1854 | `     * fresh block. One volatile store per page is the first touch. */` | Comment: one store per page through a `volatile` pointer is the first touch. |
| 1855 | `    for (size_t at = 0; at < recsz.bytes; at += (size_t)page_bytes)` | Loop over the block in steps of one page (`page_bytes`). |
| 1856 | `        ((volatile char *)mem)[at] = 0;` | Stores one zero byte in each page. The pointer is `volatile`, so the compiler must keep the store. |
| 1857 | `    ((volatile char *)mem)[recsz.bytes - 1] = 0;` | Stores one zero byte in the last byte of the block. |
| 1858 | `    rec = (struct trec *)mem;` | `rec`: the trial records stand at the start of the block, one per trial. |
| 1859 | `    struct win *win = (struct win *)(rec + plan.n);` | `win`: the window records follow the trial records. |
| 1860 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 1861 | `    /* --rec-pad: win[] starts this many bytes later. With 0 nothing moves. */` | Comment: with `--rec-pad` the window records start that many bytes later. With 0 nothing moves. |
| 1862 | `    win = (struct win *)((char *)win + plan.rec_pad);` | Moves the start of the window records by `plan.rec_pad` bytes. The default is 0 bytes. |
| 1863 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 1864 | `    struct counts *cnt = (struct counts *)(win + recsz.windows);` | `cnt`: the counter readings follow the window records. |
| 1865 | `    struct bin *bin = (struct bin *)(cnt + recsz.counts);` | `bin`: the bins follow the counter readings. |
| 1866 | `    if (plan.trace)` | Tests for the option `--trace`. |
| 1867 | `        w->log = (struct tev *)(bin + recsz.bins);` | With `--trace` the event log follows the bins. |
| 1868 | `    for (int i = 0; i < plan.n; i++) {` | Loop over the trials of the plan. |
| 1869 | `        const struct trial *p = &plan.tr[i];` | `p`: the trial of the plan. |
| 1870 | `        rec[i].win = win;` | The trial gets the next free window records. |
| 1871 | `        rec[i].nw = trial_windows(p);` | `nw`: the number of windows of the trial (`trial_windows`, line 1801). |
| 1872 | `        rec[i].cnt = p->count == CS_READ ? cnt : NULL;` | Only a trial with the counter state `read` gets counter readings. Every other trial gets NULL. |
| 1873 | `        set_windows(p, win, bin);` | Fills the plan fields of the windows of the trial (`set_windows`, line 1815). |
| 1874 | `        win += rec[i].nw;` | Moves `win` past the windows of this trial. |
| 1875 | `        bin += (size_t)p->nwin * (size_t)window_bins(p);` | Moves `bin` past the bins of this trial: `nwin` times `window_bins(p)`. |
| 1876 | `        if (p->count == CS_READ)` | Tests whether the trial has the counter state `read`. |
| 1877 | `            cnt += p->nwin + 1;` | Moves `cnt` past the `nwin + 1` readings of this trial. |
| 1878 | `    }` | Ends the loop over the trials (line 1868). |
| 1879 | `}` | Ends the function `alloc_records`. |

### Functions `print_s` and `print_p8` (trial mode): the S row and the P row (lines 1881 to 1899)

| Line | Source | Explanation |
|---:|---|---|
| 1881 | `static void print_s(int i)` | Starts the function `print_s`. It prints the S row of trial `i`: the plan line of the trial and two fields of the trial before it. |
| 1882 | `{` | Opens the body of `print_s`. |
| 1883 | `    const struct trial *p = &plan.tr[i];` | `p`: trial `i` of the plan. |
| 1884 | `    printf("S");` | Prints the letter `S`. |
| 1885 | `    for (int f = 0; f < PLAN_FIELDS; f++)` | Loop over the 11 fields of the plan line. |
| 1886 | `        printf(",%s", p->f[f]);` | Prints a comma and one field, as the text of the plan file. |
| 1887 | `    printf(",%s,%s\n", i ? plan.tr[i - 1].f[1] : "none", i ? plan.tr[i - 1].f[6] : "none");` | Prints two more fields and the line break: the fields `cond` and `tgt` of the trial before this one. For trial 0 it prints the word `none` two times. |
| 1888 | `}` | Ends the function `print_s`. |
| 1890 | `static void print_p8(int i, const char *when, const struct page *pg, const long long vm[4])` | Starts the function `print_p8`. It prints the P row of the trial mode: the page state of the buffer before or after the timed sequence of trial `i`. `when` is the word `pre` or `post`. |
| 1891 | `{` | Opens the body of `print_p8`. The P rows of the interval mode have other columns: round, position, thread index and buffer letter come first. Those rows come from `print_p` (line 1154). |
| 1892 | `    printf("P,%d,%s", i, when);` | Prints the letter `P`, the trial number and the word `pre` or `post`. |
| 1893 | `    print_na(pg->kb_total);` | Prints the size of the mapping of the buffer in kB, or `NA` (`print_na`, line 1146). |
| 1894 | `    print_na(pg->kb_huge);` | Prints the part of the buffer that lies on 2 MiB pages in kB, or `NA`. |
| 1895 | `    for (int k = 0; k < 4; k++)` | Loop over the four counters of `/proc/vmstat`. |
| 1896 | `        print_na(vm[k]);` | Prints one counter, or `NA` for a counter that was not found. |
| 1897 | `    printf("\n");` | Ends the row with a line break. |
| 1898 | `}` | Ends the function `print_p8`. |

### Function `emit_trial` (trial mode): the P, W, B and C rows of one trial (lines 1900 to 1942)

| Line | Source | Explanation |
|---:|---|---|
| 1900 | `/* All rows of one trial after its S row. */` | Comment: the function prints all rows of one trial that come after its S row. |
| 1901 | `static void emit_trial(struct tw *w, int i)` | Starts the function `emit_trial`. It prints the result rows of trial `i` from the record of the trial. It prints bytes and times. It computes no rate. |
| 1902 | `{` | Opens the body of `emit_trial`. |
| 1903 | `    const struct trial *p = &plan.tr[i];` | `p`: trial `i` of the plan. |
| 1904 | `    const struct trec *r = &rec[i];` | `r`: the record of trial `i`. |
| 1905 | `    int g = r->nw - p->nwin; /* index of target window 0 */` | `g`: the index of target window 0 in the window list of the trial: the number of all windows minus the number of target windows. The comment says the same. |
| 1906 | `    int64_t max_gap = -1;` | `max_gap`: the longest time between two windows of the trial, in ns. It starts at -1, which prints as `NA`. |
| 1908 | `    tev_add(w, EV_OUTPUT, 0, 0);` | Logs the start of the output as an event. Without `--trace` this call does nothing. |
| 1909 | `    print_p8(i, "pre", &r->pg[0], r->vm[0]);` | P row `pre`: the page state before the timed sequence (`print_p8`, line 1890). |
| 1910 | `    for (int k = 0; k < r->nw; k++) {` | Loop over all windows of the trial. |
| 1911 | `        const struct win *x = &r->win[k];` | `x`: the record of window `k`. |
| 1912 | `        printf("W,%d,%s,%d,%s,%lu,%lu,%lld,%lld\n", i, phase_name[x->phase], x->widx, kernels[x->k].name,` | W row, one per window. Its columns: the letter `W`, the trial number, the name of the phase, the number of the window inside the phase, the kernel name, `pass_bytes`, `bytes`, `t_start_ns` and `t_end_ns`. This line holds the format and the first four values. |
| 1913 | `               (unsigned long)x->size, (unsigned long)x->bytes, (long long)(x->t_start - t_base_ns),` | Continues the call of line 1912. `pass_bytes` is the range size of one kernel call. `bytes` is the byte count of the window: the range size times the number of kernel calls. `t_start_ns` is the start clock read of the window, in ns after the process start (`t_base_ns`). |
| 1914 | `               (long long)(x->t_end - t_base_ns));` | Continues the call of line 1912: `t_end_ns`, the last clock read of the window, in ns after the process start. The row holds no rate. The file `DECISIONS-bwx8.md` defines the rate of a window as `bytes` divided by `t_end_ns - t_start_ns`. |
| 1915 | `        if (k && x->t_start - r->win[k - 1].t_end > max_gap)` | Tests, for every window but the first, whether the time from the end clock read of the window before to the start clock read of this window is the longest so far. |
| 1916 | `            max_gap = x->t_start - r->win[k - 1].t_end;` | Keeps the longest such time in `max_gap`. |
| 1917 | `    }` | Ends the loop over the windows (line 1910). |
| 1918 | `    for (int k = g; k < r->nw; k++)` | Loop over the target windows of the trial. |
| 1919 | `        for (int b = 0; b < r->win[k].nbin; b++)` | Loop over the bins that the window closed. |
| 1920 | `            printf("B,%d,%d,%d,%lld,%lu\n", i, r->win[k].widx, b, (long long)(r->win[k].bin[b].t_end - t_base_ns),` | B row, one per bin. Its columns: the letter `B`, the trial number, the number of the target window, the bin number, `t_end_ns` and the byte count of the bin. `t_end_ns` is the clock read that closed the bin, in ns after the process start. This line holds the format and the first four values. |
| 1921 | `                   (unsigned long)r->win[k].bin[b].bytes);` | Continues the call of line 1920: the bytes that the window counted from its start to that clock read. |
| 1922 | `    for (int k = 0; r->cnt && k < p->nwin; k++) {` | Loop over the target windows. It runs only for a trial with counter readings (counter state `read`). |
| 1923 | `        const struct counts *c0 = &r->cnt[k], *c1 = &r->cnt[k + 1];` | `c0`, `c1`: the reading before the start clock read of the window, and the reading after its end clock read. |
| 1924 | `        int group = w->t.group_fd >= 0 && !r->read_fail;` | `group`: 1 when a counter group is open and no group reading of the trial failed. |
| 1925 | `        printf("C,%d,%d", i, k);` | C row, one per target window. It starts with the letter `C`, the trial number and the window number. Every value after them is the difference of the two readings. The C rows of the interval mode have other columns: round, position, kernel name, thread index and CPU come first. `main` prints those rows (lines 2663 to 2680). |
| 1926 | `        if (group)` | Tests whether the group readings can be used. |
| 1927 | `            printf(",%llu,%llu", (unsigned long long)(c1->enabled - c0->enabled),` | Columns 4 and 5, `enabled_ns` and `running_ns`: the growth of the enabled time and of the running time between the two readings, in ns. This line holds the enabled time. |
| 1928 | `                   (unsigned long long)(c1->running - c0->running));` | Continues the call of line 1927: the growth of the running time. |
| 1929 | `        else` | The case of no open group, or of a failed group reading. |
| 1930 | `            printf(",NA,NA");` | Columns 4 and 5 are then `NA`. |
| 1931 | `        printf(",%llu", (unsigned long long)(c1->cpu_ns - c0->cpu_ns));` | Column 6, `cputime_ns`: the growth of the thread CPU time between the two readings, in ns. |
| 1932 | `        for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `cfg`. |
| 1933 | `            int at = w->t.ev_pos[e];` | `at`: the position of the event in a group reading, or -1 for an event that did not open. |
| 1934 | `            if (!group \|\| at < 0)` | Tests whether the value cannot be given: the group readings cannot be used, or the event did not open. |
| 1935 | `                printf(",NA");` | The field is then `NA`. |
| 1936 | `            else` | The case of a value that can be given. |
| 1937 | `                printf(",%llu", (unsigned long long)(c1->val[at] - c0->val[at]));` | One column per event: the count at the second reading minus the count at the first reading. |
| 1938 | `        }` | Ends the loop over the events (line 1932). |
| 1939 | `        printf("\n");` | Ends the row with a line break. |
| 1940 | `    }` | Ends the loop over the target windows (line 1922). |
| 1941 | `    print_p8(i, "post", &r->pg[1], r->vm[1]);` | P row `post`: the page state after the timed sequence. |

### Function `emit_trial` (trial mode): the X rows, the E row and the trace rows (lines 1943 to 1991)

| Line | Source | Explanation |
|---:|---|---|
| 1943 | `    if (r->pg[0].kb_huge < 0 \|\| r->pg[1].kb_huge < 0)` | Tests whether a reading of the page state found no exact entry for the buffer in `/proc/self/smaps`, before or after the timed sequence. |
| 1944 | `        printf("X,%d,coverage_na,the buffer has no exact entry in /proc/self/smaps\n", i);` | X row with the code `coverage_na`. An X row reports a problem: the letter `X`, the trial number, a code and a text. |
| 1945 | `    if (r->close_fail)` | Tests whether a `close` call failed when the counter group was closed at the start of this trial (line 1765). |
| 1946 | `        printf("X,%d,count_close,%d counter descriptors did not close\n", i, r->close_fail);` | X row with the code `count_close` and the number of counter file descriptors that did not close. |
| 1947 | `    if (r->state == CS_FAIL)` | Tests whether the trial wanted counters and an event did not open. |
| 1948 | `        printf("X,%d,count_open,%d of %d events did not open; first: %s\n", i, w->open_fail, cfg.nev, w->open_err);` | X row with the code `count_open`: how many of the events did not open, and the error text of the first one. |
| 1949 | `    if (r->read_fail)` | Tests whether a group reading failed during the timed sequence. |
| 1950 | `        printf("X,%d,count_read,%d reads of the counter group failed\n", i, r->read_fail);` | X row with the code `count_read` and the number of failed group readings. |
| 1951 | `    if (r->cnt && w->t.group_fd >= 0 && !r->read_fail) {` | Tests whether the trial has counter readings that can be used: readings exist, a group is open, and no reading failed. |
| 1952 | `        int m = first_multiplexed(r->cnt, p->nwin);` | `m`: the first target window in which the counters did not count all the time (`first_multiplexed`, line 1749), or -1. |
| 1953 | `        if (m >= 0)` | Tests whether there is such a window. |
| 1954 | `            printf("X,%d,count_multiplexed,target window %d: running_ns %llu below enabled_ns %llu\n", i, m,` | X row with the code `count_multiplexed`: the number of the target window, and its running time and its enabled time in ns. The running time is the smaller one. |
| 1955 | `                   (unsigned long long)(r->cnt[m + 1].running - r->cnt[m].running),` | Continues the call of line 1954: the growth of the running time in that window. |
| 1956 | `                   (unsigned long long)(r->cnt[m + 1].enabled - r->cnt[m].enabled));` | Continues the call of line 1954: the growth of the enabled time in that window. |
| 1957 | `    }` | Ends the `if` of line 1951. |
| 1958 | `    if (r->sink_ok == 0)` | Tests whether the sum check of the old read kernel failed (line 1797). |
| 1959 | `        printf("X,%d,sink,the last old read did not leave the sum of its range in the sink\n", i);` | X row with the code `sink`: the last old read kernel did not leave the sum of its range in the sink. |
| 1961 | `    printf("E,%d,%lld,%llu", i, (long long)(r->win[r->nw - 1].t_end - r->win[0].t_start),` | E row, one per trial: the summary of the trial. Columns 1 to 4: the letter `E`, the trial number, `wall_ns` and `cpu_ns`. `wall_ns` is the time from the start clock read of the first window to the end clock read of the last window, in ns. |
| 1962 | `           (unsigned long long)(r->cpu[1] - r->cpu[0]));` | Continues the call of line 1961: `cpu_ns`, the growth of the thread CPU time between the two `tcpu` calls of `run_trial` (line 1785, line 1794), in ns. |
| 1963 | `    if (r->nvcsw[0] < 0 \|\| r->nvcsw[1] < 0)` | Tests whether a reading of the context switches failed. |
| 1964 | `        printf(",NA,NA");` | Columns 5 and 6 are then `NA`. |
| 1965 | `    else` | The case of two good readings. |
| 1966 | `        printf(",%ld,%ld", r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]);` | Columns 5 and 6, `nvcsw` and `nivcsw`: the numbers of voluntary and of involuntary context switches of the worker between the two `switches` calls of `run_trial` (line 1784, line 1795). |
| 1967 | `    print_na(g ? r->win[g].t_start - r->win[g - 1].t_end : -1);` | Column 7, `gap_ns`: the time from the end clock read of the window before target window 0 to the start clock read of target window 0. A trial without a window before its first target window prints `NA`. |
| 1968 | `    print_na(max_gap);` | Column 8, `max_boundary_gap_ns`: `max_gap`, the longest time between two windows of the trial (lines 1915 to 1916). A trial with one window prints `NA`. |
| 1969 | `    if (r->sink_ok < 0)` | Tests whether the trial ran no old read kernel. |
| 1970 | `        printf(",NA");` | Column 9, `sink_ok`, is then `NA`. |
| 1971 | `    else` | The case of a trial that ran an old read kernel. |
| 1972 | `        printf(",%d", r->sink_ok);` | Column 9 is then 1 for a right sum and 0 for a wrong sum. |
| 1973 | `    printf(",%s\n", count_name[r->state]);` | Column 10, `count_state`: the counter state of the trial as a word: `closed`, `open`, `read` or `fail`. The line break ends the row. |
| 1975 | `    for (long n = 0; n < w->nlog; n++) {` | Loop over the events of the trace. Without `--trace` the log holds no event. |
| 1976 | `        const struct tev *e = &w->log[n];` | `e`: one event of the log. |
| 1977 | `        if (e->ev == EV_KERNEL_FIRST)` | Tests whether the event is the first kernel call of a window. |
| 1978 | `            printf("TR,%d,%ld,%s:%s:%d,%lld\n", i, n, event_name[e->ev], phase_name[e->phase], e->widx,` | TR row of such an event: the letters `TR`, the trial number, the event number, then the event name with the phase name and the window number (joined by colons), then the time of the event. |
| 1979 | `                   (long long)(e->t - t_base_ns));` | Continues the call of line 1978: the time of the event, in ns after the process start. |
| 1980 | `        else` | The case of every other event. |
| 1981 | `            printf("TR,%d,%ld,%s,%lld\n", i, n, event_name[e->ev], (long long)(e->t - t_base_ns));` | TR row of another event: the letters `TR`, the trial number, the event number, the event name and the time in ns after the process start. For an event that is not a clock read this is the time of the clock read before it. |
| 1982 | `    }` | Ends the loop over the events (line 1975). |
| 1983 | `    if (w->ndrop)` | Tests whether events did not fit into the log. |
| 1984 | `        printf("# trace_dropped,%d,%ld\n", i, w->ndrop);` | Prints the line `# trace_dropped` with the trial number and the number of events that the log did not keep. The log keeps 1048576 events per trial (`TRACE_CAP`, line 1398). |
| 1985 | `    /* --trace: minor page faults of the worker between the two rusage reads.` | Comment: with `--trace` the next statement prints the minor page faults of the worker between the two `getrusage` readings. |
| 1986 | `     * Above 0: a page was first touched inside the timed sequence. */` | Comment: a value above 0 means that a page got its first touch inside the timed sequence. The two readings also enclose the two `tcpu` calls of `run_trial` (line 1785, line 1794). |
| 1987 | `    if (w->log)` | Tests whether a log exists (`--trace`). |
| 1988 | `        printf("# minflt,%d,%ld\n", i, r->minflt[0] < 0 \|\| r->minflt[1] < 0 ? -1 : r->minflt[1] - r->minflt[0]);` | Prints the line `# minflt` with the trial number and the number of minor page faults between the two `switches` calls. It prints -1 when a reading failed. |
| 1989 | `    fflush(stdout);` | `fflush` writes the buffered rows to the output before the next trial starts. |
| 1990 | `}` | Ends the function `emit_trial`. |

### The evict step of `--evict-mb` (trial mode): variables and the function `evict_step` (lines 1992 to 2032)

| Line | Source | Explanation |
|---:|---|---|
| 1992 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. This block ends in line 2032. |
| 1993 | `/*` | Comment: starts the comment about the evict step. The comment ends in line 2007. |
| 1994 | ` * --evict-mb N. evict_step() maps N MiB of anonymous private memory (plain` | Comment: the option `--evict-mb N`. The function `evict_step` maps N MiB of anonymous private memory. The sentence goes on in line 1995. |
| 1995 | ` * mmap, no madvise), stores one 8-byte word to every 64 B line in ascending` | Comment: the function uses a plain `mmap` without `madvise`. It stores one 8-byte word to every 64 B line, from the lowest address up. The sentence goes on in line 1996. |
| 1996 | ` * order, in two passes, and unmaps the range. The stores go through a` | Comment: it does this in two passes and then unmaps the range. The sentence about the stores starts here. |
| 1997 | ` * volatile pointer, so gcc keeps every one of them and does not call memset.` | Comment: the stores go through a `volatile` pointer. So gcc keeps every store and does not call `memset`. |
| 1998 | ` * Purpose: the lines of the benchmark buffer leave the caches. The first` | Comment: the purpose: the 64 B lines of the benchmark buffer leave the caches. The reason starts here. |
| 1999 | ` * touch wrote them, so they were dirty. The next read brings them back from` | Comment: the first touch wrote these lines, so they were dirty. A dirty line holds data that the cache has not yet written back to memory. The sentence about the next read starts here. |
| 2000 | ` * memory, clean.` | Comment: the next read brings the lines back from memory, clean. |
| 2001 | ` * trial_worker() calls it once, after the first touch of the buffer and of` | Comment: `trial_worker` calls the function once, after the first touch of the buffer. The sentence goes on in line 2002. |
| 2002 | ` * the record block and before the first trial. No timed sequence holds it.` | Comment: the call also comes after the first touch of the record block and before the first trial. No timed sequence holds the evict step. |
| 2003 | ` * evict_t holds one clock read before the mmap and one after the munmap.` | Comment: `evict_t` holds one clock read before the `mmap` and one after the `munmap`. |
| 2004 | ` * Returns 0, or -1 with the text of the error in evict_err.` | Comment: the function returns 0. On an error it returns -1 and leaves the text of the error in `evict_err`. |
| 2005 | ` * These definitions stand after timed_sequence_hot() and after every other` | Comment: these definitions stand after `timed_sequence_hot` and after every other variable of the trial mode. The sentence ends in line 2006. |
| 2006 | ` * variable of the trial mode, so nothing before them moves.` | Comment: so nothing that stands before them moves to another address. |
| 2007 | ` */` | Comment: the end of the comment. |
| 2008 | `static long evict_mb;      /* --evict-mb: 0 = no evict step */` | `evict_mb`: the value of `--evict-mb` in MiB. The value 0 means no evict step. |
| 2009 | `static int64_t evict_t[2]; /* CLOCK_MONOTONIC, ns */` | `evict_t`: the two clock reads around the evict step, in ns of the Linux clock `CLOCK_MONOTONIC`. |
| 2010 | `static char evict_err[160];` | `evict_err`: the text of an error of the evict step. |
| 2012 | `__attribute__((noinline)) static int evict_step(void)` | Starts the function `evict_step`. It writes `evict_mb` MiB of other memory two times. The aim: the 64 B lines of the benchmark buffer leave the caches. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 2013 | `{` | Opens the body of `evict_step`. |
| 2014 | `    size_t len = (size_t)evict_mb << 20;` | `len`: the size of the memory in bytes: `evict_mb` times 1048576. |
| 2015 | `    evict_t[0] = now_ns();` | First clock read (`now_ns`, line 294), before the `mmap`. |
| 2016 | `    volatile uint64_t *m = mmap(NULL, len, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `len` bytes of new private anonymous memory. `m` points to `volatile` data. So the compiler must keep every store of line 2023. |
| 2017 | `    if (m == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 2018 | `        snprintf(evict_err, sizeof evict_err, "mmap of %ld MiB failed: %s", evict_mb, strerror(errno));` | Stores the error text in `evict_err`: the words `mmap of`, the size in MiB, the word `failed` and the reason that Linux gave. |
| 2019 | `        return -1;` | Returns -1. |
| 2020 | `    }` | Ends the `if` of line 2017. |
| 2021 | `    for (int pass = 0; pass < 2; pass++)` | Two passes over the whole range. |
| 2022 | `        for (size_t i = 0; i < len / 8; i += 8)` | Loop over the range. `i` counts 8-byte words, so `i += 8` is a step of 64 B: one store per 64 B line, from the lowest address up. |
| 2023 | `            m[i] = (uint64_t)i + (uint64_t)pass + 1;` | Stores one 8-byte word at the start of the 64 B line. The value is the word index plus the pass number plus 1. |
| 2024 | `    if (munmap((void *)m, len) != 0) {` | Unmaps the memory and tests whether `munmap` failed. |
| 2025 | `        snprintf(evict_err, sizeof evict_err, "munmap of %ld MiB failed: %s", evict_mb, strerror(errno));` | Stores the error text in `evict_err`: the words `munmap of`, the size in MiB, the word `failed` and the reason that Linux gave. |
| 2026 | `        return -1;` | Returns -1. |
| 2027 | `    }` | Ends the `if` of line 2024. |
| 2028 | `    evict_t[1] = now_ns();` | Second clock read, after the `munmap`. |
| 2029 | `    return 0;` | Returns 0: the step is done. |
| 2030 | `}` | Ends the function `evict_step`. |
| 2032 | `/* bwx11- */` | Comment: marks the end of the block that `bwx11` added. The block starts in line 1992. |

### Function `trial_worker` (trial mode): pinning, buffer, first touch and records (lines 2033 to 2053)

| Line | Source | Explanation |
|---:|---|---|
| 2033 | `static void *trial_worker(void *arg)` | Starts the function `trial_worker`, the start function of the one worker thread of the trial mode. `trial_main` creates the thread in line 2464. |
| 2034 | `{` | Opens the body of `trial_worker`. |
| 2035 | `    struct tw *w = arg;` | `w`: the state of the worker (line 1472). |
| 2036 | `    volatile uint64_t sink = 0;` | `sink`: the volatile variable on the stack of the worker that receives the sum of an old read kernel. It starts at 0. |
| 2037 | `    int madvise_ok;` | `madvise_ok`: will hold whether the request for the page policy succeeded (line 2049). |
| 2039 | `    pin_cpu(cfg.cpus[0]);` | CPU pinning. The worker pins itself to the one CPU of `--cpus` (`pin_cpu`, line 382). |
| 2040 | `    if (sched_getcpu() != cfg.cpus[0]) {` | Asks Linux on which CPU the thread runs now (`sched_getcpu`) and tests whether it is another CPU than the one of `--cpus`. |
| 2041 | `        fprintf(stderr, "the worker runs on CPU %d, not on CPU %d\n", sched_getcpu(), cfg.cpus[0]);` | Prints both CPU numbers to stderr. |
| 2042 | `        exit(2);` | Ends the process with exit status 2. |
| 2043 | `    }` | Ends the `if` of line 2040. |
| 2044 | `    w->v = ((uint64_t)getpid() + 1) * 0x9E3779B97F4A7C15ULL;` | `w->v`: the value that the first touch of line 2050 stores into the 8-byte words of the buffer: the process id (`getpid`) plus 1, times a fixed 64-bit constant. |
| 2045 | `    w->t.group_fd = -1;` | The worker has no counter group yet. |
| 2046 | `    w->t.a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 401) maps the one buffer of the worker: it starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. |
| 2047 | `    /* alloc_buf() does not return the result of its madvise. The same request` | Comment: `alloc_buf` does not return the result of its `madvise` call. The sentence about the next statement starts here. |
| 2048 | `     * again gives it. */` | Comment: the same request once more gives the result. |
| 2049 | `    madvise_ok = madvise(w->t.a, buf_len(), cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) == 0;` | Repeats the `madvise` request of `alloc_buf` for the buffer: a request for 2 MiB pages, or with `--no-thp` for no such pages. `madvise_ok` is 1 when the call succeeded. |
| 2050 | `    k_write(w->t.a, cfg.bytes / 8, w->v); /* first touch by the pinned worker */` | First touch. The pinned worker stores `w->v` into `cfg.bytes / 8` words of 8 bytes with `k_write` (line 498): every word of the `--bytes` range of the buffer. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 395). This line is not timed. |
| 2051 | `    alloc_records(w);` | `alloc_records` (line 1845) allocates the record block and touches every page of it. |
| 2052 | `    w->last_t = t_base_ns;` | The trace starts with the process start time as the time of the latest clock read. |

### Function `trial_worker` (trial mode): header lines and the rows before the first trial (lines 2054 to 2120)

| Line | Source | Explanation |
|---:|---|---|
| 2054 | `    printf("# bwx8 trial mode: GB = 1e9 bytes; times are whole ns since process start on CLOCK_MONOTONIC\n"` | Starts the `printf` call that prints the header lines of the trial mode. Each header line starts with `#`. This first line says: GB means 1e9 bytes, and times are whole ns after the process start on the clock `CLOCK_MONOTONIC`. The text names `bwx8`, the version of the runner that added the trial mode. |
| 2055 | `           "# S,trial,cond,rep,prev,pfx,pred,tgt,nwin,win_ms,count,bins,prev_cond,prev_tgt\n"` | Text of the header: the column names of the S rows. |
| 2056 | `           "# P,trial,when,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n"` | Text of the header: the column names of the P rows of the trial mode. |
| 2057 | `           "# W,trial,phase,widx,kernel,pass_bytes,bytes,t_start_ns,t_end_ns\n"` | Text of the header: the column names of the W rows. |
| 2058 | `           "# B,trial,widx,bin,t_end_ns,bytes_since_window_start\n"` | Text of the header: the column names of the B rows. |
| 2059 | `           "# C,trial,widx,enabled_ns,running_ns,cputime_ns");` | Text of the header: the first six column names of the C rows of the trial mode. The header line has no line break yet. |
| 2060 | `    for (int e = 0; e < cfg.nev; e++)` | Loop over the events of `cfg`. |
| 2061 | `        printf(",%s", cfg.ev_name[e]);` | Appends one event name per event to the header line of the C rows. |
| 2062 | `    printf("\n# E,trial,wall_ns,cpu_ns,nvcsw,nivcsw,gap_ns,max_boundary_gap_ns,sink_ok,count_state\n"` | Ends the header line of the C rows. Then comes the header line with the column names of the E rows. |
| 2063 | `           "# X,trial,code,text\n"` | Text of the header: the column names of the X rows. |
| 2064 | `           "# TR,trial,n,event,t_ns; t_ns of an event that is not a clock read is the time of the clock read before it\n");` | Text of the header: the column names of the TR rows. The text adds: the time of an event that is not a clock read is the time of the clock read before it. |
| 2065 | `    printf("M,mode,trial\nM,cpu,%d\nM,ctl_cpu,%d\nM,bytes,%lu\nM,thp,%s\nM,madvise_ok,%d\nM,check_bytes,%lu\nM,kernels,%s\n",` | M rows. Each M row holds one setting or one fact in the form `M,name,value`. This call prints `mode` (the word `trial`), `cpu` (the worker CPU), `ctl_cpu` (the CPU of the controlling thread), `bytes` (the buffer size), `thp` (the page policy), `madvise_ok`, `check_bytes` and `kernels`. |
| 2066 | `           cfg.cpus[0], plan.ctl_cpu, (unsigned long)cfg.bytes, cfg.use_thp ? "madvise" : "nohugepage", madvise_ok,` | Continues the call of line 2065: the values of `cpu`, `ctl_cpu`, `bytes`, `thp` (the word `madvise` or `nohugepage`) and `madvise_ok`. |
| 2067 | `           (unsigned long)CHECK_BYTES, STANDIN ? "STAND-IN" : "aarch64");` | Continues the call of line 2065: `check_bytes` is `CHECK_BYTES` (8388608 bytes, which is 8 MiB). `kernels` is `aarch64`, or `STAND-IN` for a build with stand-in kernels. |
| 2068 | `    printf("M,plan_fnv1a64,%016llx\nM,ntrials,%d\nM,rec_windows,%zu\nM,rec_bins,%zu\nM,rec_counts,%zu\nM,rec_trace,%zu\n"` | More M rows: `plan_fnv1a64` (the checksum of the plan file, 16 hexadecimal digits), `ntrials` (the number of trials), and the sizes of the record storage: `rec_windows`, `rec_bins`, `rec_counts` and `rec_trace`. |
| 2069 | `           "M,rec_bytes,%zu\nM,trace,%d\n",` | Continues the format of line 2068: `rec_bytes` (the size of the record block in bytes) and `trace` (0 or 1). |
| 2070 | `           (unsigned long long)plan.hash, plan.n, recsz.windows, recsz.bins, recsz.counts, recsz.trace, recsz.bytes,` | Continues the call of line 2068: the values of the first seven of these rows. |
| 2071 | `           plan.trace);` | Continues the call of line 2068: the value of `trace`. |
| 2072 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2073 | `    /* Addresses in hex without "0x", as in the K rows. rec_addr: the record` | Comment: the addresses are printed in hexadecimal without `0x`, as in the K rows. `rec_addr` is the address of the record block. The list goes on in line 2074. |
| 2074 | `     * block. win_addr: win[0] of trial 0. stack_addr: the sink of the worker. */` | Comment: `win_addr` is the address of the first window record of trial 0. `stack_addr` is the address of the sink of the worker. |
| 2075 | `    printf("M,rec_pad,%zu\nM,hot_copy,%d\nM,rec_addr,%lx\nM,win_addr,%lx\nM,win_size,%zu\nM,stack_addr,%lx\nM,buf_addr,%lx\n"` | More M rows: `rec_pad`, `hot_copy`, `rec_addr`, `win_addr`, `win_size` (the size of one window record in bytes), `stack_addr` and `buf_addr` (the address of the buffer). |
| 2076 | `           "M,tw_addr,%lx\n",` | Continues the format of line 2075: `tw_addr`, the address of the state of the worker. |
| 2077 | `           plan.rec_pad, plan.hot_copy, (unsigned long)(uintptr_t)rec, (unsigned long)(uintptr_t)rec[0].win,` | Continues the call of line 2075: the values of `rec_pad`, `hot_copy`, `rec_addr` and `win_addr`. |
| 2078 | `           sizeof(struct win), (unsigned long)(uintptr_t)&sink, (unsigned long)(uintptr_t)w->t.a,` | Continues the call of line 2075: the values of `win_size`, `stack_addr` and `buf_addr`. |
| 2079 | `           (unsigned long)(uintptr_t)w);` | Continues the call of line 2075: the value of `tw_addr`. |
| 2080 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2081 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2082 | `    /* The evict step. The buffer and the record block are first touched, and` | Comment: the evict step. At this point the buffer and the record block have got their first touch. The sentence goes on in line 2083. |
| 2083 | `     * no trial has started. With --evict-mb 0 no call is made. A failure` | Comment: no trial has started at this point. With `--evict-mb 0` the function is not called. The sentence about a failure starts here. |
| 2084 | `     * ends the process here: the X row is the last row. */` | Comment: a failure ends the process here, and the X row is the last row of the output. |
| 2085 | `    printf("M,evict_mb,%ld\n", evict_mb);` | M row `evict_mb`: the value of `--evict-mb`. |
| 2086 | `    if (evict_mb > 0 && evict_step() != 0) {` | With a value above 0: runs the evict step (`evict_step`, line 2012) and tests whether it failed. |
| 2087 | `        printf("X,-1,evict,%s\n", evict_err);` | X row with the trial number -1, the code `evict` and the error text. |
| 2088 | `        fflush(stdout);` | Writes the buffered rows to the output. |
| 2089 | `        exit(2);` | Ends the process with exit status 2. |
| 2090 | `    }` | Ends the `if` of line 2086. |
| 2091 | `    printf("M,evict_ns,%lld\n", (long long)(evict_t[1] - evict_t[0]));` | M row `evict_ns`: the time between the two clock reads of the evict step, in ns. It is 0 when no step ran. |
| 2092 | `    if (evict_mb > 0 && plan.trace)` | Tests whether a step ran and the trace is on. |
| 2093 | `        printf("TR,-1,0,evict_start,%lld\nTR,-1,1,evict_end,%lld\n", (long long)(evict_t[0] - t_base_ns),` | Two TR rows with the trial number -1: `evict_start` and `evict_end`, with the two clock reads of the step in ns after the process start. This line holds the time of `evict_start`. |
| 2094 | `               (long long)(evict_t[1] - t_base_ns));` | Continues the call of line 2093: the time of `evict_end`. |
| 2095 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2096 | `    if (cfg.pmu_type < 0)` | Tests whether no PMU type was given. |
| 2097 | `        printf("M,pmu_type,none\n");` | M row `pmu_type` with the word `none`. |
| 2098 | `    else` | The case of a given PMU type. |
| 2099 | `        printf("M,pmu_type,%ld\n", cfg.pmu_type);` | M row `pmu_type` with the number. |
| 2100 | `    printf("M,events,%s", cfg.nev ? "" : "none");` | Starts the M row `events`. Without events its value is the word `none`. |
| 2101 | `    for (int e = 0; e < cfg.nev; e++)` | Loop over the events of `cfg`. |
| 2102 | `        printf("%s%s=0x%llx", e ? ";" : "", cfg.ev_name[e], (unsigned long long)cfg.ev_code[e]);` | Prints one event as its name, the sign `=` and its code in hexadecimal with `0x`. A semicolon separates two events. |
| 2103 | `    printf("\n");` | Ends the row with a line break. |
| 2104 | `    for (int i = 0; i < plan.npair; i++) {` | Loop over the `key=value` pairs of the second line of the plan. |
| 2105 | `        char *eq = strchr(plan.pair[i], '=');` | `eq`: the place of the `=` sign in the pair. |
| 2106 | `        printf("M,plan.%.*s,%s\n", (int)(eq - plan.pair[i]), plan.pair[i], eq + 1);` | One M row per pair: the name is `plan.` plus the key, and the value is the text after the `=` sign. |
| 2107 | `    }` | Ends the loop of line 2104. |
| 2108 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the kernel table. |
| 2109 | `        int used = 0;` | `used`: becomes 1 when a trial of the plan uses kernel `k`. |
| 2110 | `        for (int i = 0; i < plan.n && !used; i++) {` | Loop over the trials. It stops at the first trial that uses the kernel. |
| 2111 | `            const struct trial *p = &plan.tr[i];` | `p`: one trial of the plan. |
| 2112 | `            used = p->prev.k == k \|\| p->pfx.k == k \|\| p->pred.k == k \|\| p->tgt.k == k;` | Tests whether one of the four parts of the trial names kernel `k`. |
| 2113 | `        }` | Ends the loop of line 2110. |
| 2114 | `        if (used)` | Tests whether the plan uses the kernel. |
| 2115 | `            printf("K,%s,%lx,%lu\n", kernels[k].name, (unsigned long)(uintptr_t)kernels[k].fn,` | K row, one per kernel that the plan uses: the letter `K`, the kernel name, the address of its function in hexadecimal, and this address modulo 64. |
| 2116 | `                   (unsigned long)((uintptr_t)kernels[k].fn % 64));` | Continues the call of line 2115: the address modulo 64. |
| 2117 | `    }` | Ends the loop over the kernel table (line 2108). |
| 2118 | `    if (!madvise_ok)` | Tests whether the `madvise` request of line 2049 failed. |
| 2119 | `        printf("X,-1,madvise,the page policy request failed\n");` | X row with the trial number -1 and the code `madvise`: the request for the page policy failed. |

### Function `trial_worker` (trial mode): the loop over the trials and the end (lines 2121 to 2137)

| Line | Source | Explanation |
|---:|---|---|
| 2121 | `    for (int i = 0; i < plan.n; i++) {` | Loop over the trials, in the order of the plan. |
| 2122 | `        w->nlog = w->ndrop = 0;` | Empties the trace: no event in the log, and a count of 0 for the events that did not fit. |
| 2123 | `        w->cur_phase = -1;` | No window counts as logged yet. So the first kernel call of the trial is logged (line 1540). |
| 2124 | `        tev_add(w, EV_OUTPUT, 0, 0);` | Logs the start of the output as an event. Without `--trace` this call does nothing. |
| 2125 | `        print_s(i);` | Prints the S row of the trial (`print_s`, line 1881). |
| 2126 | `        fflush(stdout);` | Writes the buffered rows to the output before the trial runs. |
| 2127 | `        run_trial(w, &plan.tr[i], &rec[i], &sink);` | Runs the trial (`run_trial`, line 1759). That function prints nothing. So the process writes no output inside a timed sequence. |
| 2128 | `        emit_trial(w, i);` | Prints the result rows of the trial (`emit_trial`, line 1901). |
| 2129 | `    }` | Ends the loop over the trials (line 2121). |
| 2130 | `    if (w->group_open)` | Tests whether the counter group is still open after the last trial. |
| 2131 | `        count_close(w);` | Then the group is closed (`count_close`, line 1680). |
| 2132 | `    if (w->close_fail)` | Tests whether a `close` call failed. |
| 2133 | `        printf("X,-1,count_close,%d counter descriptors did not close\n", w->close_fail);` | X row with the trial number -1 and the code `count_close`: the number of counter file descriptors that did not close. |
| 2134 | `    fflush(stdout);` | Writes the buffered rows to the output. |
| 2135 | `    return NULL;` | The worker thread ends. `trial_main` waits for its end in line 2468. |
| 2136 | `}` | Ends the function `trial_worker`. |

### Function `plan_bad` (trial mode): report a defect of the plan file (lines 2138 to 2148)

| Line | Source | Explanation |
|---:|---|---|
| 2138 | `static void plan_bad(int line, const char *fmt, ...)` | Starts the function `plan_bad`. It reports a defect of the plan file on stderr and ends the process with exit status 2. `line` is the number of the plan line. `fmt` and the arguments after it form the message, as in `printf`. |
| 2139 | `{` | Opens the body of `plan_bad`. |
| 2140 | `    va_list ap;` | `ap`: the list of the arguments that follow `fmt`. |
| 2141 | `    fprintf(stderr, "bad plan %s, line %d: ", plan.path, line);` | Prints the start of the message to stderr: the words `bad plan`, the path of the plan file, the word `line` and the number of the plan line. |
| 2142 | `    va_start(ap, fmt);` | Starts the reading of the arguments that follow `fmt`. |
| 2143 | `    vfprintf(stderr, fmt, ap);` | `vfprintf` prints the message itself to stderr. It builds the text from `fmt` and these arguments. |
| 2144 | `    va_end(ap);` | Ends the reading of the arguments. |
| 2145 | `    fprintf(stderr, "\n");` | Ends the message with a line break. |
| 2146 | `    exit(2);` | Ends the process with exit status 2. |
| 2147 | `}` | Ends the function `plan_bad`. |

### Functions `plan_long` and `plan_size` (trial mode): a number and a size of the plan (lines 2149 to 2182)

| Line | Source | Explanation |
|---:|---|---|
| 2149 | `/* A whole number in [lo, hi] made of digits only. */` | Comment: the function accepts a whole number from `lo` to `hi` that is made of digits only. |
| 2150 | `static int plan_long(const char *s, long lo, long hi, long *out)` | Starts the function `plan_long`. It turns the text `s` into a whole number. For a good text it stores the number in `*out` and returns 1. For any other text it returns 0. The caller then reports the defect with `plan_bad`. |
| 2151 | `{` | Opens the body of `plan_long`. |
| 2152 | `    char *end;` | `end`: will point to the first character that `strtol` did not read. |
| 2153 | `    if (*s < '0' \|\| *s > '9')` | Tests whether the first character is not a decimal digit. So a sign or a space at the start is rejected. |
| 2154 | `        return 0;` | Such a text returns 0. |
| 2155 | `    errno = 0;` | Sets `errno` to 0. After the next call a value other than 0 shows that the number was too large for the type. |
| 2156 | `    long v = strtol(s, &end, 10);` | `strtol` reads the text as a decimal number. |
| 2157 | `    if (*end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi)` | Tests for four defects: other text follows the number, the number was too large for the type, the number is below `lo`, or it is above `hi`. |
| 2158 | `        return 0;` | A defect returns 0. |
| 2159 | `    *out = v;` | Stores the number. |
| 2160 | `    return 1;` | Returns 1. |
| 2161 | `}` | Ends the function `plan_long`. |
| 2163 | `/* A whole number above 0 with an optional K, M or G. */` | Comment: the function accepts a whole number above 0 with an optional letter `K`, `M` or `G`. |
| 2164 | `static int plan_size(const char *s, uint64_t *out)` | Starts the function `plan_size`. It turns a size text such as `8M` into a number of bytes. For a good text it stores the bytes in `*out` and returns 1. For any other text it returns 0. |
| 2165 | `{` | Opens the body of `plan_size`. |
| 2166 | `    char *end;` | `end`: will point to the first character that `strtoull` did not read. |
| 2167 | `    int shift = 0;` | `shift`: the number of bits by which a letter shifts the number. It is 0 without a letter. |
| 2168 | `    if (*s < '0' \|\| *s > '9')` | Tests whether the first character is not a decimal digit. |
| 2169 | `        return 0;` | Such a text returns 0. |
| 2170 | `    errno = 0;` | Sets `errno` to 0, as in line 2155. |
| 2171 | `    unsigned long long v = strtoull(s, &end, 10);` | `strtoull` reads the text as a decimal number. |
| 2172 | `    switch (*end) {` | Looks at the character after the number. |
| 2173 | `    case 'K': shift = 10; end++; break;` | The letter `K`: the number times 1024 (a shift by 10 bits). |
| 2174 | `    case 'M': shift = 20; end++; break;` | The letter `M`: the number times 1048576, which gives MiB (a shift by 20 bits). |
| 2175 | `    case 'G': shift = 30; end++; break;` | The letter `G`: the number times 1073741824 (a shift by 30 bits). Only capital letters are accepted in a plan. |
| 2176 | `    }` | Ends the `switch` of line 2172. |
| 2177 | `    if (*end != '\0' \|\| errno != 0 \|\| v == 0 \|\| v > (UINT64_MAX >> shift))` | Tests for four defects: other text follows, the number was too large for the type, the number is 0, or the size in bytes does not fit into 64 bits. |
| 2178 | `        return 0;` | A defect returns 0. |
| 2179 | `    *out = (uint64_t)v << shift;` | Stores the size in bytes: the number shifted left by `shift` bits. |
| 2180 | `    return 1;` | Returns 1. |
| 2181 | `}` | Ends the function `plan_size`. |

### Function `plan_part` (trial mode): one kernel field of a trial line (lines 2183 to 2215)

| Line | Source | Explanation |
|---:|---|---|
| 2183 | `/* "KERNEL@SIZE:MS" (with_ms, where "-" is also allowed) or "KERNEL@SIZE". */` | Comment: the field has the form `KERNEL@SIZE:MS` or the form `KERNEL@SIZE`. The first form holds when `with_ms` is set. Then the text `-` is also allowed. |
| 2184 | `static void plan_part(int line, const char *what, const char *s, int with_ms, struct part *p)` | Starts the function `plan_part`. It reads one kernel field `s` of a trial line into `*p`: the index of the kernel, the size in bytes and the duration in ms. `line` is the number of the plan line and `what` the name of the field. Both are for the error message. A defect ends the process through `plan_bad` (line 2138). |
| 2185 | `{` | Opens the body of `plan_part`. |
| 2186 | `    char buf[96];` | `buf`: room for a copy of the field of at most 95 characters. The function cuts the copy into pieces. |
| 2187 | `    p->k = -1;` | Start value: no kernel (`k` is -1). |
| 2188 | `    p->size = 0;` | Start value: the size 0. |
| 2189 | `    p->ms = 0;` | Start value: the duration 0. |
| 2190 | `    if (with_ms && !strcmp(s, "-"))` | Tests whether the field may be left out (`with_ms` is 1) and is the text `-`. |
| 2191 | `        return;` | Then the part is absent, and `p->k` stays -1. |
| 2192 | `    if (strlen(s) >= sizeof buf)` | Tests whether the field has 96 characters or more. |
| 2193 | `        plan_bad(line, "%s is too long", what);` | Such a field is a defect. The message says that the field is too long. |
| 2194 | `    strcpy(buf, s);` | Copies the field into `buf`. |
| 2195 | `    char *at = strchr(buf, '@'), *colon = at ? strchr(at, ':') : NULL;` | `at`: the place of the `@` in the field. `colon`: the place of a colon after the `@`. Each is NULL when the character is missing. |
| 2196 | `    if (!at \|\| with_ms != (colon != NULL))` | Tests for a wrong form. The field has no `@`. Or it has no colon although a duration is needed. Or it has a colon although no duration is allowed. |
| 2197 | `        plan_bad(line, "%s '%s' is not %s", what, s, with_ms ? "'-' or KERNEL@SIZE:MS" : "KERNEL@SIZE");` | The message names the field, its text and the form that is needed. |
| 2198 | `    *at = '\0';` | Ends the kernel name at the `@`: a zero byte replaces the `@`. |
| 2199 | `    if (colon)` | Tests whether the field has a colon. |
| 2200 | `        *colon = '\0';` | Ends the size text at the colon. |
| 2201 | `    int k = 0;` | `k`: the index into the kernel table. The search starts at entry 0. |
| 2202 | `    while (k < K_COUNT && strcmp(buf, kernels[k].name))` | Searches the kernel table for the name, as in line 1341. |
| 2203 | `        k++;` | The body of the search loop: goes on to the next entry of the table. |
| 2204 | `    if (k == K_COUNT)` | Tests whether no entry has the name. |
| 2205 | `        plan_bad(line, "%s: unknown kernel '%s'", what, buf);` | The message says that the kernel is unknown. |
| 2206 | `    if (kernels[k].type != T_READ && kernels[k].type != T_OLDREAD)` | Tests whether the kernel is not a read kernel: its type is not `T_READ` and not `T_OLDREAD`. So the trial mode accepts read kernels only. |
| 2207 | `        plan_bad(line, "%s: '%s' is not a read kernel", what, buf);` | The message says that the kernel is not a read kernel. |
| 2208 | `    if (!plan_size(at + 1, &p->size) \|\| p->size % 256 != 0 \|\| p->size > cfg.bytes)` | Reads the size with `plan_size` (line 2164) and tests for three defects: the text is not a size, the size is not a multiple of 256 bytes, or it is above the `--bytes` value. |
| 2209 | `        plan_bad(line, "%s: size '%s' must be a multiple of 256, above 0 and at most --bytes (%lu)", what, at + 1,` | The message names the size text and the rule: a multiple of 256, above 0 and at most the `--bytes` value. |
| 2210 | `                 (unsigned long)cfg.bytes);` | Continues the call of line 2209: the `--bytes` value. |
| 2211 | `    if (colon && !plan_long(colon + 1, 1, MAX_MS, &p->ms))` | For a field with a duration: reads it with `plan_long` (line 2150). It must be a whole number from 1 to 3600000 ms (`MAX_MS`, 1 hour). |
| 2212 | `        plan_bad(line, "%s: bad duration '%s' (whole ms from 1 to %ld)", what, colon + 1, MAX_MS);` | The message names the bad duration and the allowed range. |
| 2213 | `    p->k = k;` | Stores the index of the kernel. From here on the part exists. |
| 2214 | `}` | Ends the function `plan_part`. |

### Function `plan_pairs` (trial mode): the second line of the plan file (lines 2216 to 2246)

| Line | Source | Explanation |
|---:|---|---|
| 2216 | `/* Line 2: "# key=value key=value ...". bytes and cpu must equal the options. */` | Comment: the second line of the plan has the form `# key=value key=value ...`. The values of `bytes` and `cpu` must equal the options. |
| 2217 | `static void plan_pairs(char *s)` | Starts the function `plan_pairs`. It splits the second line of the plan at each space and keeps a pointer to every pair in `plan.pair`. It also checks the pairs `bytes=` and `cpu=`. |
| 2218 | `{` | Opens the body of `plan_pairs`. |
| 2219 | `    int have_bytes = 0, have_cpu = 0;` | `have_bytes`, `have_cpu`: become 1 when the line holds a pair `bytes=` and a pair `cpu=`. |
| 2220 | `    if (strncmp(s, "# ", 2))` | Tests whether the line does not start with `#` and a space. |
| 2221 | `        plan_bad(2, "the line must start with '# '");` | That is a defect of the plan (`plan_bad`, line 2138). |
| 2222 | `    for (char *tok = s + 2, *sp; tok; tok = sp ? sp + 1 : NULL) {` | Loop over the pairs. `tok` is the start of one pair. `sp` is the space after it, or NULL after the last pair. |
| 2223 | `        sp = strchr(tok, ' ');` | Finds the next space. |
| 2224 | `        if (sp)` | Tests whether a space was found. |
| 2225 | `            *sp = '\0';` | Ends the pair at the space: a zero byte replaces the space. |
| 2226 | `        char *eq = strchr(tok, '=');` | `eq`: the place of the `=` sign in the pair, or NULL. |
| 2227 | `        if (!eq \|\| eq == tok \|\| strchr(tok, ',') \|\| plan.npair == MAX_PAIRS)` | Tests for four defects: no `=` sign, an empty key, a comma in the pair, or a 65th pair (`MAX_PAIRS` is 64). |
| 2228 | `            plan_bad(2, "bad key=value pair '%s'", tok);` | The message names the bad pair. |
| 2229 | `        plan.pair[plan.npair++] = tok;` | Keeps a pointer to the pair. `trial_worker` prints each pair as an M row (lines 2104 to 2107). |
| 2230 | `        if (!strncmp(tok, "bytes=", 6)) {` | Tests whether the pair starts with `bytes=`. |
| 2231 | `            uint64_t b;` | `b`: the size of the pair in bytes. |
| 2232 | `            if (!plan_size(eq + 1, &b) \|\| b != cfg.bytes)` | Reads the size with `plan_size` and tests whether it is no size or differs from the `--bytes` value. |
| 2233 | `                plan_bad(2, "%s differs from --bytes %lu", tok, (unsigned long)cfg.bytes);` | Then the plan has a defect. The message names the pair and the `--bytes` value. |
| 2234 | `            have_bytes = 1;` | Notes that the line has a pair `bytes=`. |
| 2235 | `        }` | Ends the `if` of line 2230. |
| 2236 | `        if (!strncmp(tok, "cpu=", 4)) {` | Tests whether the pair starts with `cpu=`. |
| 2237 | `            long c;` | `c`: the CPU number of the pair. |
| 2238 | `            if (!plan_long(eq + 1, 0, MAX_USE_CPU, &c) \|\| c != cfg.cpus[0])` | Reads the number with `plan_long` (0 to `MAX_USE_CPU`) and tests whether it is no such number or differs from the first CPU of `--cpus`. |
| 2239 | `                plan_bad(2, "%s differs from --cpus %d", tok, cfg.cpus[0]);` | Then the plan has a defect. The message names the pair and the CPU of `--cpus`. |
| 2240 | `            have_cpu = 1;` | Notes that the line has a pair `cpu=`. |
| 2241 | `        }` | Ends the `if` of line 2236. |
| 2242 | `    }` | Ends the loop over the pairs (line 2222). |
| 2243 | `    if (!have_bytes \|\| !have_cpu)` | Tests whether one of the two pairs is missing. |
| 2244 | `        plan_bad(2, "bytes= and cpu= are needed");` | That is a defect. The message says that `bytes=` and `cpu=` are needed. |
| 2245 | `}` | Ends the function `plan_pairs`. |

### Function `plan_trial` (trial mode): one trial line of the plan (lines 2247 to 2307)

| Line | Source | Explanation |
|---:|---|---|
| 2247 | `static void plan_trial(int line, char *s)` | Starts the function `plan_trial`. It reads one trial line `s` of the plan, checks every field and adds one `struct trial` to `plan.tr`. `line` is the number of the plan line. A defect ends the process through `plan_bad` (line 2138). |
| 2248 | `{` | Opens the body of `plan_trial`. |
| 2249 | `    char *f[PLAN_FIELDS];` | `f`: the 11 fields of the line as text. |
| 2250 | `    int nf = 0;` | `nf`: the number of fields found so far. |
| 2251 | `    long v;` | `v`: a number that `plan_long` returns. |
| 2252 | `    for (char *tok = s, *sp; tok; tok = sp ? sp + 1 : NULL) {` | Loop over the fields. `tok` is the start of one field. `sp` is the space after it, or NULL after the last field. |
| 2253 | `        sp = strchr(tok, ' ');` | Finds the next space. |
| 2254 | `        if (sp)` | Tests whether a space was found. |
| 2255 | `            *sp = '\0';` | Ends the field at the space: a zero byte replaces the space. |
| 2256 | `        if (nf == PLAN_FIELDS \|\| *tok == '\0')` | Tests for two defects: a 12th field, or an empty field. An empty field comes from two spaces one after the other, from a space at the start or at the end of the line, or from an empty line. |
| 2257 | `            plan_bad(line, "%d fields separated by single spaces are needed", PLAN_FIELDS);` | The message says that 11 fields separated by single spaces are needed. |
| 2258 | `        f[nf++] = tok;` | Keeps a pointer to the field and counts it. |
| 2259 | `    }` | Ends the loop over the fields (line 2252). |
| 2260 | `    if (nf != PLAN_FIELDS)` | Tests whether the line has fewer than 11 fields. |
| 2261 | `        plan_bad(line, "%d fields separated by single spaces are needed, %d found", PLAN_FIELDS, nf);` | The message says how many fields are needed and how many were found. |
| 2262 | `    plan.tr = realloc(plan.tr, ((size_t)plan.n + 1) * sizeof *plan.tr);` | `realloc` makes the array `plan.tr` one trial longer. |
| 2263 | `    if (!plan.tr)` | Tests whether the memory could not be given. |
| 2264 | `        plan_bad(line, "no memory");` | That ends the process through `plan_bad` with the message `no memory`. |
| 2265 | `    struct trial *p = &plan.tr[plan.n];` | `p`: the new trial. |
| 2266 | `    memcpy(p->f, f, sizeof f);` | Copies the 11 field pointers into the trial. `print_s` prints these texts in the S row (line 1886). |
| 2267 | `    if (!plan_long(f[0], 0, 1000000, &v) \|\| v != plan.n)` | Field 1, `trial`: it must be the number of this trial, counted from 0 in the order of the file. |
| 2268 | `        plan_bad(line, "trial '%s': the trial numbers must be 0, 1, 2, ... (%d expected)", f[0], plan.n);` | The message names the field and the number that was expected. |
| 2269 | `    if (strchr(f[1], ','))` | Field 2, `cond`, a label of the condition: it must hold no comma. |
| 2270 | `        plan_bad(line, "cond '%s' holds a comma", f[1]);` | The message names the label. |
| 2271 | `    if (!plan_long(f[2], 1, 4, &v))` | Field 3, `rep`: a whole number from 1 to 4. The file `DECISIONS-bwx8.md` calls it the number of this repeat of the condition in the process. |
| 2272 | `        plan_bad(line, "rep '%s' is not 1 to 4", f[2]);` | The message names the bad value. |
| 2273 | `    plan_part(line, "prev", f[3], 1, &p->prev);` | Field 4, `prev`: the previous activity. `plan_part` (line 2184) reads it. It has a duration and may be `-`. |
| 2274 | `    plan_part(line, "pfx", f[4], 1, &p->pfx);` | Field 5, `pfx`: the prefix. It has a duration and may be `-`. |
| 2275 | `    plan_part(line, "pred", f[5], 1, &p->pred);` | Field 6, `pred`: the predecessor. It has a duration and may be `-`. |
| 2276 | `    plan_part(line, "tgt", f[6], 0, &p->tgt);` | Field 7, `tgt`: the target. It has no duration field and cannot be left out. |
| 2277 | `    if (p->pfx.k >= 0 && p->pfx.ms % 4 != 0)` | Tests whether the trial has a prefix whose duration is not a multiple of 4 ms. The prefix runs as 4 windows of a quarter of its duration each (line 1833). |
| 2278 | `        plan_bad(line, "pfx duration %ld ms is not a multiple of 4", p->pfx.ms);` | The message names the duration. |
| 2279 | `    if (!plan_long(f[7], 1, MAX_NWIN, &v))` | Field 8, `nwin`: the number of target windows, a whole number from 1 to 4096 (`MAX_NWIN`). |
| 2280 | `        plan_bad(line, "nwin '%s' is not 1 to %d", f[7], MAX_NWIN);` | The message names the bad value. |
| 2281 | `    p->nwin = (int)v;` | Stores the number of target windows. |
| 2282 | `    if (!plan_long(f[8], 1, MAX_MS, &p->win_ms))` | Field 9, `win_ms`: the duration of one target window, a whole number from 1 to 3600000 ms (`MAX_MS`). |
| 2283 | `        plan_bad(line, "win_ms '%s' is not 1 to %ld", f[8], MAX_MS);` | The message names the bad value. |
| 2284 | `    p->count = !strcmp(f[9], "closed") ? CS_CLOSED : !strcmp(f[9], "open") ? CS_OPEN : !strcmp(f[9], "read") ? CS_READ : -1;` | Field 10, `count`: the counter state. The words `closed`, `open` and `read` give the codes of line 1408. Any other word gives -1. |
| 2285 | `    if (p->count < 0)` | Tests whether the word was none of the three. |
| 2286 | `        plan_bad(line, "count '%s' is not closed, open or read", f[9]);` | The message names the bad word. |
| 2287 | `    if (strcmp(f[10], "0") && strcmp(f[10], "1"))` | Field 11, `bins`: tests whether the text is neither `0` nor `1`. |
| 2288 | `        plan_bad(line, "bins '%s' is not 0 or 1", f[10]);` | The message names the bad text. |
| 2289 | `    p->bins = f[10][0] == '1';` | `bins` becomes 1 for the text `1` and 0 for the text `0`. |
| 2290 | `    plan.n++;` | Counts the trial. |
| 2291 | `    /* The record storage is bounded here, before the process pins or` | Comment: the size of the record storage is limited here. The sentence goes on in line 2292. |
| 2292 | `     * allocates. */` | Comment: this happens before the process pins a thread or allocates the records. |
| 2293 | `    recsz.windows += (size_t)trial_windows(p);` | Adds the windows of this trial to the number of window records (`trial_windows`, line 1801). |
| 2294 | `    recsz.bins += (size_t)p->nwin * (size_t)window_bins(p);` | Adds the bins of this trial: `nwin` times `window_bins(p)` (line 1808). |
| 2295 | `    if (p->count == CS_READ)` | Tests whether the trial has the counter state `read`. |
| 2296 | `        recsz.counts += (size_t)p->nwin + 1;` | Adds the `nwin + 1` counter readings of this trial. |
| 2297 | `    recsz.trace = plan.trace ? TRACE_CAP : 0;` | With `--trace` the storage holds `TRACE_CAP` (1048576) trace events. Without `--trace` it holds none. |
| 2298 | `    recsz.bytes = (size_t)plan.n * sizeof(struct trec) + recsz.windows * sizeof(struct win) +` | `recsz.bytes`: the size of the record block for all trials up to this line: the trial records plus the window records. The sum goes on in line 2299. |
| 2299 | `                  recsz.counts * sizeof(struct counts) + recsz.bins * sizeof(struct bin) + recsz.trace * sizeof(struct tev);` | Continues the sum of line 2298: plus the counter readings, the bins and the trace events. |
| 2300 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2301 | `    recsz.bytes += plan.rec_pad;` | Adds the pad of `--rec-pad` to the size. |
| 2302 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2303 | `    if (recsz.bytes > MAX_REC_BYTES)` | Tests whether the size is above 256 MiB (`MAX_REC_BYTES`). |
| 2304 | `        plan_bad(line, "the records of the plan up to this line need %zu bytes, the bound is %lu bytes", recsz.bytes,` | Then the plan has a defect. The message gives the size that the records up to this line need, and the upper limit. |
| 2305 | `                 MAX_REC_BYTES);` | Continues the call of line 2304: the upper limit. |
| 2306 | `}` | Ends the function `plan_trial`. |

### Function `read_plan` (trial mode): read and check the whole plan (lines 2308 to 2360)

| Line | Source | Explanation |
|---:|---|---|
| 2308 | `/* Reads and checks the whole plan. Returns only if it can run. */` | Comment: the function reads and checks the whole plan. It returns only when the plan can run. |
| 2309 | `static void read_plan(void)` | Starts the function `read_plan`. It reads the plan file `plan.path` into memory, computes its checksum and checks it line by line. A defect ends the process with exit status 2. |
| 2310 | `{` | Opens the body of `read_plan`. |
| 2311 | `    size_t cap = 1 << 16, len = 0, got;` | `cap`: the size of the text buffer, 65536 bytes at the start. `len`: the number of bytes read so far. `got`: the number of bytes of one read. |
| 2312 | `    FILE *f = fopen(plan.path, "rb");` | Opens the plan file for reading. |
| 2313 | `    char *text = malloc(cap + 1);` | Allocates the text buffer, with room for one more byte at its end. |
| 2314 | `    int line = 0;` | `line`: the number of the plan line that is checked. |
| 2315 | `    if (!f \|\| !text) {` | Tests whether the file could not be opened or the buffer could not be allocated. |
| 2316 | `        fprintf(stderr, "cannot read the plan %s: %s\n", plan.path, strerror(errno));` | Prints `cannot read the plan`, the path and the reason to stderr. |
| 2317 | `        exit(2);` | Ends the process with exit status 2. |
| 2318 | `    }` | Ends the `if` of line 2315. |
| 2319 | `    while ((got = fread(text + len, 1, cap - len, f)) > 0) {` | Loop that reads the file in pieces until no byte is left. |
| 2320 | `        len += got;` | Counts the bytes of the piece. |
| 2321 | `        if (len == cap && !(text = realloc(text, (cap *= 2) + 1))) {` | When the buffer is full, `realloc` doubles its size. The test is true when that fails. |
| 2322 | `            fprintf(stderr, "no memory for the plan\n");` | Prints `no memory for the plan` to stderr. |
| 2323 | `            exit(2);` | Ends the process with exit status 2. |
| 2324 | `        }` | Ends the `if` of line 2321. |
| 2325 | `    }` | Ends the read loop (line 2319). |
| 2326 | `    if (ferror(f)) {` | Tests whether a read failed. |
| 2327 | `        fprintf(stderr, "cannot read the plan %s\n", plan.path);` | Prints `cannot read the plan` and the path to stderr. |
| 2328 | `        exit(2);` | Ends the process with exit status 2. |
| 2329 | `    }` | Ends the `if` of line 2326. |
| 2330 | `    fclose(f);` | Closes the file. |
| 2331 | `    text[len] = '\0';` | Ends the text with a zero byte. |
| 2332 | `    plan.hash = 14695981039346656037ULL; /* FNV-1a, 64 bit, over the bytes of the file */` | `plan.hash`: the start value of the FNV-1a hash, a 64-bit checksum. The comment says that it is computed over the bytes of the file. |
| 2333 | `    for (size_t i = 0; i < len; i++)` | Loop over the bytes of the file. |
| 2334 | `        plan.hash = (plan.hash ^ (uint8_t)text[i]) * 1099511628211ULL;` | One step of the hash per byte: an exclusive or with the byte, then a multiplication by the constant 1099511628211. `trial_worker` prints the result in the M row `plan_fnv1a64` (line 2068). |
| 2335 | `    if (strlen(text) != len)` | Tests whether the text ends before the end of the file. The file then holds a zero byte. |
| 2336 | `        plan_bad(0, "the file holds a zero byte");` | That is a defect of the plan. |
| 2337 | `    for (char *s = text, *next; *s; s = next) {` | Loop over the lines of the text. `s` is the start of a line. `next` is the start of the line after it. |
| 2338 | `        char *nl = strchr(s, '\n');` | `nl`: the line break at the end of the line, or NULL for a last line without one. |
| 2339 | `        next = nl ? nl + 1 : s + strlen(s);` | The next line starts after the line break. Without a line break `next` points to the end of the text, and the loop ends after this line. |
| 2340 | `        if (nl)` | Tests whether the line has a line break. |
| 2341 | `            *nl = '\0';` | Ends the line there: a zero byte replaces the line break. |
| 2342 | `        line++;` | Counts the line. |
| 2343 | `        if (line == 1) {` | Tests for the first line of the plan. |
| 2344 | `            if (strcmp(s, PLAN_LINE1))` | The first line must be the text of `PLAN_LINE1` (line 1399). |
| 2345 | `                plan_bad(1, "the line must be '%s'", PLAN_LINE1);` | If it is not: a defect of the plan. The message gives the text that is needed. |
| 2346 | `        } else if (line == 2) {` | Tests for the second line. |
| 2347 | `            plan_pairs(s);` | `plan_pairs` (line 2217) reads the second line. |
| 2348 | `        } else if (line == 3) {` | Tests for the third line. |
| 2349 | `            if (strcmp(s, PLAN_LINE3))` | The third line must be the text of `PLAN_LINE3` (line 1400): the names of the 11 fields. |
| 2350 | `                plan_bad(3, "the line must be '%s'", PLAN_LINE3);` | If it is not: a defect of the plan. The message gives the text that is needed. |
| 2351 | `        } else {` | The case of every later line. |
| 2352 | `            plan_trial(line, s);` | Every line from the fourth on is one trial. `plan_trial` (line 2247) reads it. |
| 2353 | `        }` | Ends the chain of tests that starts in line 2343. |
| 2354 | `    }` | Ends the loop over the lines (line 2337). |
| 2355 | `    if (line < 3)` | Tests whether the plan has fewer than three lines. |
| 2356 | `        plan_bad(line + 1, "the three header lines are needed");` | That is a defect: the three header lines are needed. |
| 2357 | `    if (plan.n == 0)` | Tests whether the plan has no trial. |
| 2358 | `        plan_bad(line + 1, "no trial");` | That is a defect too. The message is `no trial`. |
| 2359 | `}` | Ends the function `read_plan`. |

### Function `trial_usage` (trial mode): option summary of the trial mode, then exit status 2 (lines 2361 to 2383)

| Line | Source | Explanation |
|---:|---|---|
| 2361 | `static void trial_usage(void)` | Starts the function `trial_usage`. It prints the option summary of the trial mode to stderr and ends the process with exit status 2. |
| 2362 | `{` | Opens the body of `trial_usage`. |
| 2363 | `    fprintf(stderr,` | Starts the first `fprintf` call that writes to stderr. Its text stands in lines 2364 to 2367. |
| 2364 | `            "usage: bwx8 --trial --cpus C --bytes B --plan FILE [--ctl-cpu N] [--no-thp] [--trace]\n"` | Text of the message: the usage line with the options `--trial`, `--cpus`, `--bytes`, `--plan`, `--ctl-cpu`, `--no-thp` and `--trace`. The text names the program `bwx8`, the version of the runner that added the trial mode. |
| 2365 | `            "            [--pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options `--pmu-type` and `--events`, and the two environment variables that can give the counter settings in their place. |
| 2366 | `            "  --cpus: exactly one CPU. --ctl-cpu: CPU of the controlling thread (default 0), another CPU.\n"` | Text of the message: `--cpus` takes exactly one CPU. `--ctl-cpu` is the CPU of the controlling thread (default 0), and it must be another CPU. |
| 2367 | `            "  the counter settings are required if a trial of the plan has count open or read\n");` | Text of the message: the counter settings are required when a trial of the plan has the counter state `open` or `read`. This line ends the call. |
| 2368 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2369 | `    fprintf(stderr,` | Starts the second `fprintf` call. |
| 2370 | `            "  bwx10 adds: [--rec-pad BYTES] [--hot-copy]\n"` | Text of the message: `bwx10` adds the options `--rec-pad` and `--hot-copy`. |
| 2371 | `            "  --rec-pad: unused bytes before the window records, a multiple of %zu from 0 to 65536 (default 0)\n"` | Text of the message: `--rec-pad` gives a number of unused bytes before the window records. It must be a multiple of a value that line 2373 gives, from 0 to 65536, and its default is 0. |
| 2372 | `            "  --hot-copy: the window loop works on a local copy of its window record\n",` | Text of the message: with `--hot-copy` the window loop works on a local copy of its window record. |
| 2373 | `            _Alignof(struct win));` | The value for the text of line 2371: `_Alignof(struct win)`, the alignment in bytes that the compiler needs for a window record. This line ends the call. |
| 2374 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2375 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2376 | `    fprintf(stderr,` | Starts the third `fprintf` call. |
| 2377 | `            "  bwx11 adds: [--evict-mb N]\n"` | Text of the message: `bwx11` adds the option `--evict-mb`. |
| 2378 | `            "  --evict-mb: before the first trial the worker writes N MiB of other memory twice, a whole number\n"` | Text of the message: with `--evict-mb` the worker writes N MiB of other memory twice before the first trial. N is a whole number. The sentence goes on in line 2379. |
| 2379 | `            "              from 0 to 4096 (default 0: no such step)\n");` | Text of the message: N goes from 0 to 4096, and the default 0 means no such step. This line ends the call. |
| 2380 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2381 | `    exit(2);` | Ends the process with exit status 2. |
| 2382 | `}` | Ends the function `trial_usage`. |

### Function `trial_main` (trial mode): the arguments (lines 2384 to 2431)

| Line | Source | Explanation |
|---:|---|---|
| 2384 | `static int trial_main(int argc, char **argv)` | Starts the function `trial_main`, the entry of the trial mode. `main` calls it only when an argument is the word `--trial` (lines 2489 to 2491). |
| 2385 | `{` | Opens the body of `trial_main`. |
| 2386 | `    struct tw w;` | `w`: the state of the one worker of the trial mode (line 1472). |
| 2387 | `    pthread_t tid;` | `tid`: the handle of the worker thread. |
| 2388 | `    cpu_set_t set;` | `set`: a CPU set, for the check of line 2440. |
| 2389 | `    int bytes_given = 0, counting = 0;` | `bytes_given`: becomes 1 when `--bytes` is given. `counting`: becomes 1 when a trial of the plan wants counters. |
| 2391 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 2392 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 2393 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value needs that. |
| 2394 | `        if (!strcmp(a, "--trial")) {` | The word `--trial` itself needs no action. |
| 2395 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 2396 | `            cfg.use_thp = 0;` | `--no-thp`: the program asks Linux for no 2 MiB pages for the buffer. |
| 2397 | `        } else if (!strcmp(a, "--trace")) {` | Tests for `--trace`. |
| 2398 | `            plan.trace = 1;` | `--trace` enables the event log of the trace. |
| 2399 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2400 | `        } else if (!strcmp(a, "--hot-copy")) {` | Tests for `--hot-copy`. |
| 2401 | `            plan.hot_copy = 1;` | `--hot-copy`: `timed_sequence_hot` runs the windows (lines 1789 to 1790). |
| 2402 | `        } else if (!strcmp(a, "--rec-pad") && more) {` | Tests for `--rec-pad` with a value after it. |
| 2403 | `            long pad = parse_long(argv[++i], "--rec-pad", 0, 65536);` | `pad`: the value in bytes, a whole number from 0 to 65536 (`parse_long`, line 320). |
| 2404 | `            if (pad % (long)_Alignof(struct win) != 0) {` | Tests whether the value is not a multiple of the alignment of a window record. |
| 2405 | `                fprintf(stderr, "bad --rec-pad: '%s' (a multiple of %zu is needed: the window records stay aligned)\n",` | Prints a message to stderr: the bad value and the multiple that is needed. The text gives the reason: the window records stay aligned. |
| 2406 | `                        argv[i], _Alignof(struct win));` | Continues the call of line 2405: the value and the alignment. |
| 2407 | `                exit(2);` | Ends the process with exit status 2. |
| 2408 | `            }` | Ends the `if` of line 2404. |
| 2409 | `            plan.rec_pad = (size_t)pad;` | Stores the pad. |
| 2410 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2411 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2412 | `        } else if (!strcmp(a, "--evict-mb") && more) {` | Tests for `--evict-mb` with a value after it. |
| 2413 | `            evict_mb = parse_long(argv[++i], "--evict-mb", 0, 4096);` | `evict_mb`: the value, a whole number from 0 to 4096 (MiB). |
| 2414 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2415 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 2416 | `            parse_cpus(argv[++i]);` | Reads the CPU list with `parse_cpus` (line 355). The check of line 2432 later demands exactly one CPU. |
| 2417 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 2418 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size, read by `parse_bytes` (line 301). |
| 2419 | `            bytes_given = 1;` | Notes that `--bytes` was given. |
| 2420 | `        } else if (!strcmp(a, "--plan") && more) {` | Tests for `--plan` with a value after it. |
| 2421 | `            plan.path = argv[++i];` | The path of the plan file. |
| 2422 | `        } else if (!strcmp(a, "--ctl-cpu") && more) {` | Tests for `--ctl-cpu` with a value after it. |
| 2423 | `            plan.ctl_cpu = (int)parse_long(argv[++i], "--ctl-cpu", 0, MAX_USE_CPU);` | The CPU of the controlling thread, a whole number from 0 to `MAX_USE_CPU`. |
| 2424 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 2425 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. |
| 2426 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 2427 | `            parse_events(argv[++i]);` | Reads the event list with `parse_events` (line 1355). |
| 2428 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 2429 | `            trial_usage();` | Prints the option summary of the trial mode and ends the process (`trial_usage`, line 2361). Options of the interval mode such as `--threads`, `--seq`, `--stop`, `--start`, `--rounds`, `--min-ms` and `--count` have no branch in this loop. So they end here too. |
| 2430 | `        }` | Ends the chain of tests that starts in line 2394. |
| 2431 | `    }` | Ends the loop over the arguments (line 2391). |

### Function `trial_main` (trial mode): checks, the plan and the start of the worker (lines 2432 to 2471)

| Line | Source | Explanation |
|---:|---|---|
| 2432 | `    if (cfg.ncpus != 1 \|\| !bytes_given \|\| !plan.path \|\| cfg.bytes % 256 != 0) {` | Tests the settings: `--cpus` names exactly one CPU, `--bytes` was given and is a multiple of 256 bytes, and `--plan` was given. |
| 2433 | `        fprintf(stderr, "--trial needs --cpus with exactly one CPU, --bytes (a multiple of 256) and --plan\n");` | If one of them fails: prints the rule to stderr. |
| 2434 | `        trial_usage();` | Then prints the option summary and ends the process with exit status 2 (`trial_usage`). |
| 2435 | `    }` | Ends the `if` of line 2432. |
| 2436 | `    if (plan.ctl_cpu == cfg.cpus[0]) {` | Tests whether the controlling thread and the worker would share one CPU. |
| 2437 | `        fprintf(stderr, "the controlling thread and the worker must not share CPU %d\n", plan.ctl_cpu);` | Prints a message with the CPU number to stderr. |
| 2438 | `        exit(2);` | Ends the process with exit status 2. |
| 2439 | `    }` | Ends the `if` of line 2436. |
| 2440 | `    if (sched_getaffinity(0, sizeof set, &set) != 0 \|\| !CPU_ISSET(cfg.cpus[0], &set) \|\| !CPU_ISSET(plan.ctl_cpu, &set)) {` | Reads the allowed CPU set of the process (`sched_getaffinity`) and tests whether the worker CPU or the CPU of the controlling thread is not in it. A failed call counts as a defect too. |
| 2441 | `        fprintf(stderr, "CPU %d or CPU %d is not in the allowed set of the process\n", cfg.cpus[0], plan.ctl_cpu);` | Prints both CPU numbers to stderr. |
| 2442 | `        exit(2);` | Ends the process with exit status 2. |
| 2443 | `    }` | Ends the `if` of line 2440. |
| 2444 | `    read_plan();` | Reads and checks the whole plan (`read_plan`, line 2309). At this point no thread is pinned and no buffer is mapped. |
| 2445 | `    for (int i = 0; i < plan.n; i++)` | Loop over the trials of the plan. |
| 2446 | `        counting \|= plan.tr[i].count != CS_CLOSED;` | `counting` becomes 1 when a trial has the counter state `open` or `read`. |
| 2447 | `    if (counting && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: a plan with counters, no `--pmu-type`, and the environment variable `BWX_PMU_TYPE` is set. |
| 2448 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 2449 | `    if (counting && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: a plan with counters, no `--events`, and the environment variable `BWX_EVENTS` is set. |
| 2450 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 2451 | `        parse_events(copy);` | Reads the event list from the copy. |
| 2452 | `        free(copy);` | Frees the copy. |
| 2453 | `    }` | Ends the `if` of line 2449. |
| 2454 | `    if (counting && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether a plan with counters still has no PMU type or no event. |
| 2455 | `        fprintf(stderr, "the plan has a trial with count open or read: --pmu-type and --events are needed "` | Prints a message to stderr: the plan has a trial with the counter state `open` or `read`, and `--pmu-type` and `--events` are needed. |
| 2456 | `                        "(or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Continues the text of line 2455: or the two environment variables. |
| 2457 | `        exit(2);` | Ends the process with exit status 2. |
| 2458 | `    }` | Ends the `if` of line 2454. |
| 2460 | `    /* The plan can run. The controlling thread pins itself, starts the` | Comment: the plan can run. The controlling thread pins itself and starts the worker. The sentence goes on in line 2461. |
| 2461 | `     * worker and waits. It never touches the buffer. */` | Comment: then the controlling thread waits. It never touches the buffer. |
| 2462 | `    pin_cpu(plan.ctl_cpu);` | The controlling thread pins itself to the CPU of `--ctl-cpu` (`pin_cpu`, line 382). |
| 2463 | `    memset(&w, 0, sizeof w);` | Sets every field of the worker state to 0. |
| 2464 | `    if (pthread_create(&tid, NULL, trial_worker, &w) != 0) {` | Starts the one worker thread. It runs `trial_worker` (line 2033). |
| 2465 | `        perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 2466 | `        return 2;` | `trial_main` then returns 2, which becomes the exit status of the process (line 2491). |
| 2467 | `    }` | Ends the `if` of line 2464. |
| 2468 | `    pthread_join(tid, NULL);` | Waits for the end of the worker thread (`pthread_join`). |
| 2469 | `    return 0;` | Returns 0, which becomes the exit status of the process (line 2491). |
| 2470 | `}` | Ends the function `trial_main`. |

### The include of the self-test file (lines 2472 to 2480)

| Line | Source | Explanation |
|---:|---|---|
| 2472 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2473 | `#if 0` | `#if 0`: the compiler skips the text from here to the `#endif` of line 2477. |
| 2474 | `/* bwx11- */` | Comment: marks the end of a piece of text that `bwx11` added. |
| 2475 | `#include "bwx10_selftest.c"` | The include line of the self-test file of the version `bwx10`. It stands between the `#if 0` of line 2473 and the `#endif` of line 2477. So the compiler skips it. |
| 2476 | `/* bwx11+ */` | Comment: marks the start of more text that `bwx11` added. |
| 2477 | `#endif` | Ends the `#if 0` of line 2473. |
| 2478 | `#include "bwx11_selftest.c"` | Includes the file `bwx11_selftest.c`. It defines the function `selftest`. `main` calls that function only for the option `--selftest` (line 2497). |
| 2479 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |

### Function `main`: the start of the program (lines 2481 to 2488)

| Line | Source | Explanation |
|---:|---|---|
| 2481 | `int main(int argc, char **argv)` | Starts the function `main`, the entry point of the program. It reads the arguments, starts the workers, sets the common start of each interval and prints all rows. |
| 2482 | `{` | Opens the body of `main`. |
| 2483 | `    int threads_given = 0;` | `threads_given`: becomes 1 when `--threads` is given (line 2510). The check of line 2546 uses it. |
| 2484 | `    char seq_text[1024] = "";` | `seq_text`: will hold a copy of the `--seq` text for the second header line of the output (line 2600). It has room for 1023 characters. |
| 2485 | `    t_base_ns = now_ns();` | Process start time: one reading of the Linux clock `CLOCK_MONOTONIC` through `now_ns` (line 294), in ns. The T rows print the common start, `t0` and `t1` of each thread as seconds after this time (lines 2660 to 2661). |
| 2486 | `    page_bytes = sysconf(_SC_PAGESIZE);` | `page_bytes`: the size of one small memory page in bytes, as Linux reports it (`sysconf`). `alloc_buf` (line 401) uses it when it places a buffer inside its mapping. |
| 2487 | `    cfg.bytes = 1UL << 20;` | `cfg.bytes` gets its default here: 1 MiB (1048576 bytes). The option `--bytes` replaces it (line 2514). |
| 2488 | `    restrict_cpus();` | `restrict_cpus` (line 335) removes every CPU above `MAX_USE_CPU` from the allowed CPU set of the process. `MAX_USE_CPU` is 119 unless the build sets another value (line 106). The build of `bwx11` on CRB set no other value [Ref2]. |

### Function `main`: the choice between the trial mode and the interval mode (lines 2489 to 2492)

| Line | Source | Explanation |
|---:|---|---|
| 2489 | `    for (int i = 1; i < argc; i++)` | Mode choice. The loop compares every argument with the word `--trial`. |
| 2490 | `        if (!strcmp(argv[i], "--trial"))` | Tests whether one argument is the word `--trial`. |
| 2491 | `            return trial_main(argc, argv);` | When an argument is `--trial`, `main` returns the result of `trial_main` (line 2384), and no line below runs. This is the only call of `trial_main` in the file. |

### Function `main`: reading the arguments (lines 2493 to 2545)

| Line | Source | Explanation |
|---:|---|---|
| 2493 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 2494 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 2495 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value is accepted only when `more` is 1, and `argv[++i]` then takes the value. |
| 2496 | `        if (!strcmp(a, "--selftest")) {` | Tests for `--selftest`. |
| 2497 | `            return selftest();` | `--selftest` runs the self-test (the function `selftest` of the included self-test file) and ends the program with its result. |
| 2498 | `        } else if (!strcmp(a, "--list")) {` | Tests for `--list`. |
| 2499 | `            for (int k = 0; k < K_COUNT; k++)` | Loop over the kernel table. |
| 2500 | `                printf("%s\n", kernels[k].name);` | `--list` prints the name of every kernel of the table, one per line. |
| 2501 | `            return 0;` | Then the program ends with exit status 0. |
| 2502 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 2503 | `            cfg.use_thp = 0;` | `--no-thp` sets `cfg.use_thp` to 0. Then `alloc_buf` asks Linux for no 2 MiB pages. |
| 2504 | `        } else if (!strcmp(a, "--two-buffers")) {` | Tests for `--two-buffers`. |
| 2505 | `            cfg.two_buffers = 1;` | `--two-buffers` sets `cfg.two_buffers` to 1. Then every thread gets a second buffer `b`, also without a copy kernel (line 1231). |
| 2506 | `        } else if (!strcmp(a, "--count")) {` | Tests for `--count`. |
| 2507 | `            cfg.count = 1;` | `--count` sets `cfg.count` to 1. Then each worker opens its counter group and reads it before and after every timed interval. `main` prints the C rows from these readings. |
| 2508 | `        } else if (!strcmp(a, "--threads") && more) {` | Tests for `--threads` with a value after it. |
| 2509 | `            cfg.threads = (int)parse_long(argv[++i], "--threads", 1, 4096);` | The number of worker threads. `parse_long` (line 320) accepts a whole number from 1 to 4096. |
| 2510 | `            threads_given = 1;` | Notes that `--threads` was given. |
| 2511 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 2512 | `            parse_cpus(argv[++i]);` | `parse_cpus` (line 355) appends the CPUs of each range of the list to `cfg.cpus`, in the order of the text. `cfg.ncpus` counts them. |
| 2513 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 2514 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size of each thread, read by `parse_bytes` (line 301). That function reads the letter `M` as 2 to the power 20. |
| 2515 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Tests for `--min-ms` with a value after it. |
| 2516 | `            char *end;` | `end`: will point to the first character that `strtod` did not read. |
| 2517 | `            double ms = strtod(argv[++i], &end);` | `strtod` reads the value as a decimal number of milliseconds. A fraction is allowed. |
| 2518 | `            if (end == argv[i] \|\| *end != '\0' \|\| !(ms > 0) \|\| ms > 3.6e6) {` | Tests for a bad value: no number, other text after the number, a value that is not above 0, or a value above 3.6e6 ms (1 hour). |
| 2519 | `                fprintf(stderr, "bad --min-ms: '%s' (a number of milliseconds above 0 is needed)\n", argv[i]);` | Prints a message with the bad value to stderr. |
| 2520 | `                exit(2);` | Ends the program with exit status 2. |
| 2521 | `            }` | Ends the `if` of line 2518. |
| 2522 | `            cfg.min_s = ms / 1000.0;` | `cfg.min_s`: the value in seconds. With `--stop common` it is the time from the common start to the deadline (line 2638). With `--stop pass` it is the least duration of an interval (line 1299). |
| 2523 | `        } else if (!strcmp(a, "--rounds") && more) {` | Tests for `--rounds` with a value after it. |
| 2524 | `            cfg.rounds = (int)parse_long(argv[++i], "--rounds", 1, 1000000);` | The number of rounds, a whole number from 1 to 1000000. The program runs the `--seq` list that many times. |
| 2525 | `        } else if (!strcmp(a, "--seq") && more) {` | Tests for `--seq` with a value after it. |
| 2526 | `            snprintf(seq_text, sizeof seq_text, "%s", argv[++i]);` | Copies the text of the list to `seq_text`, for the second header line (line 2600). The copy is made first: `parse_seq` changes the argument text. |
| 2527 | `            parse_seq(argv[i]);` | `parse_seq` (line 1334) cuts the argument text itself at each comma. It looks up each name in the kernel table and appends its index to `cfg.seq`. An unknown name ends the program. `cfg.nseq` counts the entries. An entry without an `@SIZE` part keeps the size 0 until line 2567. |
| 2528 | `        } else if (!strcmp(a, "--stop") && more) {` | Tests for `--stop` with a value after it. |
| 2529 | `            const char *s = argv[++i];` | `s`: the value. |
| 2530 | `            if (strcmp(s, "pass") && strcmp(s, "common"))` | Tests whether the value is neither `pass` nor `common`. |
| 2531 | `                usage();` | Any other value prints the option summary and ends the program (`usage`, line 1321). |
| 2532 | `            cfg.stop_common = !strcmp(s, "common");` | `cfg.stop_common` becomes 1 for `common` and 0 for `pass`. With 1 all threads get one common start time and one common deadline for each interval (lines 2635 to 2640). |
| 2533 | `        } else if (!strcmp(a, "--start") && more) {` | Tests for `--start` with a value after it. |
| 2534 | `            const char *s = argv[++i];` | `s`: the value. |
| 2535 | `            if (strcmp(s, "common") && strcmp(s, "offset"))` | Tests whether the value is neither `common` nor `offset`. |
| 2536 | `                usage();` | Any other value prints the option summary and ends the program (`usage`). |
| 2537 | `            cfg.start_offset = !strcmp(s, "offset");` | `cfg.start_offset` becomes 1 for `offset` and 0 for `common`. With 0 every worker starts its timed work at byte 0 of its own buffer (line 1246). |
| 2538 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 2539 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. It goes into the field `type` of the structure `perf_event_attr` (line 1173). |
| 2540 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 2541 | `            parse_events(argv[++i]);` | `parse_events` (line 1355) stores the names in `cfg.ev_name` and the codes in `cfg.ev_code`. `cfg.nev` becomes the number of events. `main` does not interpret the codes. Each worker passes them to Linux in `open_counters` (line 1166). |
| 2542 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 2543 | `            usage();` | `usage` (line 1321) prints the option summary to stderr and ends the process with exit status 2. |
| 2544 | `        }` | Ends the chain of tests that starts in line 2496. |
| 2545 | `    }` | Ends the loop over the arguments (line 2493). |

### Function `main`: checks of the settings (lines 2546 to 2578)

| Line | Source | Explanation |
|---:|---|---|
| 2546 | `    if (threads_given && cfg.ncpus == 0) {` | Check: `--threads` is accepted only together with `--cpus`. The test is true when `--threads` was given and the CPU list is empty. |
| 2547 | `        fprintf(stderr, "--threads requires --cpus\n");` | Prints `--threads requires --cpus` to stderr. |
| 2548 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 2549 | `    }` | Ends the `if` of line 2546. |
| 2550 | `    if (cfg.threads < 1 \|\| cfg.rounds < 1 \|\| cfg.nseq < 1 \|\| cfg.bytes == 0 \|\| cfg.bytes % 256 != 0)` | Checks of the values: the thread count, the round count and the number of `--seq` entries are at least 1, and `--bytes` is above 0 and a multiple of 256 bytes. |
| 2551 | `        usage();` | A failed check prints the option summary and ends the program with exit status 2 (`usage`). |
| 2552 | `    /* run_bwx.sh passes the counter settings in the environment */` | Comment: the script `run_bwx.sh`, the run script of the first runner, passes the counter settings in the environment. |
| 2553 | `    if (cfg.count && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: with `--count`, without `--pmu-type`, and when the environment variable `BWX_PMU_TYPE` is set. |
| 2554 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 2555 | `    if (cfg.count && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: with `--count`, without `--events`, and when the environment variable `BWX_EVENTS` is set. |
| 2556 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 2557 | `        parse_events(copy);` | Reads the event list from the copy. |
| 2558 | `        free(copy);` | Frees the copy. |
| 2559 | `    }` | Ends the `if` of line 2555. |
| 2560 | `    if (cfg.count && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether `--count` is given and the PMU type or the events are still missing. |
| 2561 | `        fprintf(stderr, "--count requires --pmu-type and --events (or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Prints a message to stderr: `--count` requires `--pmu-type` and `--events`, or the two environment variables. |
| 2562 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 2563 | `    }` | Ends the `if` of line 2560. |
| 2564 | `    for (int s = 0; s < cfg.nseq; s++) {` | Loop over the `--seq` entries. |
| 2565 | `        struct entry *e = &cfg.seq[s];` | `e`: one entry. |
| 2566 | `        if (e->bytes == 0)` | Tests whether the entry has no size of its own (no `@SIZE` part). |
| 2567 | `            e->bytes = cfg.bytes;` | Such an entry gets the size of `--bytes`. |
| 2568 | `        if (e->bytes > cfg.bytes \|\| e->bytes % 256 != 0 \|\|` | Size check of an entry. The size must be at most `--bytes` and a multiple of 256 bytes. The check goes on in line 2569. |
| 2569 | `            (cfg.stop_common && e->bytes > CHUNK_BYTES && e->bytes % CHUNK_BYTES != 0)) {` | With `--stop common` a size above 2 MiB (`CHUNK_BYTES`) must also be a multiple of 2 MiB. With this stop rule the worker calls the kernel on chunks of 2 MiB (line 1277). A size of 256 MiB passes: 268435456 bytes is 128 times 2 MiB. |
| 2570 | `            fprintf(stderr, "bad size of --seq entry %d (%s): %lu\n", s, kernels[e->k].name, (unsigned long)e->bytes);` | A bad size prints a message to stderr: the number of the entry, the kernel name and the size. |
| 2571 | `            usage();` | Then the option summary is printed, and the program ends with exit status 2 (`usage`). |
| 2572 | `        }` | Ends the `if` of line 2568. |
| 2573 | `        if (kernels[e->k].type == T_COPY)` | Tests whether the kernel of the entry is a copy kernel (type `T_COPY`). |
| 2574 | `            cfg.two_buffers = 1;` | A copy kernel in the list sets `cfg.two_buffers` to 1. Then each thread gets a second buffer `b` (line 1231). |
| 2575 | `    }` | Ends the loop over the entries (line 2564). |
| 2576 | `    if (cfg.ncpus && cfg.threads > cfg.ncpus)` | Tests whether a CPU list was given and has fewer CPUs than the process has threads. |
| 2577 | `        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);` | This only gives a warning on stderr, with both numbers. The CPU list is then used again from its start (line 2588). |

### Function `main`: thread records, barrier and start of the workers (lines 2579 to 2594)

| Line | Source | Explanation |
|---:|---|---|
| 2579 | `    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);` | `th`: one record per thread, filled with zeros by `calloc`. |
| 2580 | `    uint64_t **bufs = calloc((size_t)cfg.threads * 2, sizeof *bufs);` | `bufs`: two buffer addresses per thread, for buffer `a` and buffer `b`, filled with zeros. |
| 2581 | `    struct page *pg = calloc((size_t)cfg.threads * 2, sizeof *pg);` | `pg`: one page-state record per entry of `bufs`. |
| 2582 | `    if (!th \|\| !bufs \|\| !pg \|\| pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {` | Tests the three allocations and creates the barrier `bar` for the thread count plus 1: the workers and the main thread. |
| 2583 | `        perror("setup");` | On a failure: `perror` prints the word `setup` and the reason. |
| 2584 | `        return 2;` | On a failure: the program ends with exit status 2. |
| 2585 | `    }` | Ends the `if` of line 2582. |
| 2586 | `    for (int i = 0; i < cfg.threads; i++) {` | Loop that starts the workers. |
| 2587 | `        th[i].idx = i;` | Thread `i` gets the index `i`. |
| 2588 | `        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;` | Thread placement. Thread `i` gets the CPU `cfg.cpus[i % cfg.ncpus]`: entry `i` of the CPU list. The list is used again from its start when there are more threads than entries. Without a CPU list the value is -1, and the thread is not pinned (line 1225). |
| 2589 | `        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {` | Creates the thread. It runs `worker` (line 1216): it pins itself, opens its counters, maps its buffer and writes it. `main` does not wait for that here. It goes on with the header lines. The function `main` does not pin the main thread. So the main thread may run on any CPU of the allowed CPU set of the process. |
| 2590 | `            perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 2591 | `            return 2;` | The program then ends with exit status 2. |
| 2592 | `        }` | Ends the `if` of line 2589. |
| 2593 | `    }` | Ends the loop of line 2586. |

### Function `main`: the header lines of the csv file (lines 2595 to 2615)

| Line | Source | Explanation |
|---:|---|---|
| 2595 | `    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "` | Starts the `printf` call of the first header line. The line starts with `# bandwidth:`. It gives the meaning of GB (1e9 bytes) and the formula of the rate of the I rows: `aggregate_GBps` is the sum of the bytes of all threads divided by the longest elapsed time of one thread. |
| 2596 | `           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",` | Continues the text of the first header line: a copy kernel counts the bytes read plus the bytes written. Then come four settings: the thread count, the bytes per thread, `min_ms` and `thp`. |
| 2597 | `           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");` | The four values. `min_ms` is `cfg.min_s` times 1000, printed without decimals. `thp` is `madvise` when the program asks for 2 MiB pages, and `nohugepage` with `--no-thp`. It only says what the program asked for. The P rows show what the buffers got. |
| 2598 | `    printf("# bwx: seq=%s rounds=%d stop=%s start=%s two_buffers=%d count=%d kernels=%s; "` | Starts the `printf` call of the second header line. The line starts with `# bwx:`. It holds the `--seq` text, the rounds, the stop rule, the start rule, `two_buffers`, `count` and the build kind (`kernels=`). |
| 2599 | `           "round and pos count from 0; times are seconds since process start\n",` | Continues the text of the second header line: round and position count from 0, and the times are seconds after the process start. |
| 2600 | `           seq_text, cfg.rounds, cfg.stop_common ? "common" : "pass", cfg.start_offset ? "offset" : "common",` | The values: the `--seq` text, the number of rounds, `common` or `pass` for the stop rule, and `offset` or `common` for the start rule. |
| 2601 | `           cfg.two_buffers, cfg.count, STANDIN ? "STAND-IN (not AArch64: rates mean nothing)" : "aarch64");` | The values of `two_buffers`, `count` and the build kind. `STANDIN` is 0 in the AArch64 build (line 459), and the build kind is then `aarch64`. A build with stand-in kernels prints a text that starts with `STAND-IN` and says that the rates mean nothing. |
| 2602 | `    printf("# I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps\n"` | Starts the `printf` call of the third, fourth and fifth header line. This line holds the column names of the I rows (line 2654). |
| 2603 | `           "# T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags\n"` | The fourth header line: the column names of the T rows (line 2658). |
| 2604 | `           "# P,round,pos,tid,buffer,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n");` | The fifth header line: the column names of the P rows. `print_p` (line 1154) prints these rows. |
| 2605 | `    if (cfg.count) {` | Tests whether counting is on (`--count`). Only then the header has a sixth line. |
| 2606 | `        printf("# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns");` | Starts the sixth header line: the first nine column names of the C rows, up to `cputime_ns`. |
| 2607 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 2608 | `            printf(",%s", cfg.ev_name[e]);` | Appends the event names in the order of `--events`, one column per event. |
| 2609 | `        printf("; pmu_type=%ld codes=", cfg.pmu_type);` | Appends the PMU type (`pmu_type=`) and the word `codes=`. |
| 2610 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 2611 | `            printf("%s0x%llx", e ? "," : "", (unsigned long long)cfg.ev_code[e]);` | Appends the event codes in hexadecimal, with commas between them. |
| 2612 | `        printf("\n");` | Ends the header line with a line break. |
| 2613 | `    }` | Ends the `if` of line 2605. |
| 2614 | `    fflush(stdout);` | `fflush` writes the header lines to the standard output now. |

### Function `main`: the loop over rounds and positions, and the common start (lines 2616 to 2642)

| Line | Source | Explanation |
|---:|---|---|
| 2616 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds, as in `worker` (line 1240). |
| 2617 | `        for (int pos = -1; pos < cfg.nseq; pos++) {` | Loop over the positions. `pos` starts at -1, not at 0. Position -1 is one extra pass of the loop before the first interval. Each position from 0 up is one timed interval. `main` and the workers go through the same rounds and positions. At each barrier call below a thread waits until all workers and `main` have arrived. |
| 2618 | `            if (pos < 0 && (round > 0 \|\| cfg.threads == 1))` | Tests whether the pass with position -1 must be skipped: in every round after round 0, and in a process with one thread. |
| 2619 | `                continue;` | Skips that pass. So in a process with more than one thread it runs once, before the first interval. |
| 2620 | `            if (pos < 0) {` | The case of position -1. |
| 2621 | `                /* the workers have allocated and first touched their buffers */` | Comment: at this point the workers have allocated their buffers and have written them for the first time. |
| 2622 | `                pthread_barrier_wait(&bar);` | `main` calls the barrier. The call returns when all workers have mapped and written their buffers and wait in line 1236. |
| 2623 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 2624 | `                    bufs[2 * i] = th[i].a;` | Copies the address of buffer `a` of thread `i` into entry `2 * i` of `bufs`. |
| 2625 | `                    bufs[2 * i + 1] = th[i].b;` | Copies the address of buffer `b` of thread `i` into entry `2 * i + 1`. The entry stays NULL when the thread has no second buffer. |
| 2626 | `                }` | Ends the loop of line 2623. This pass of the position loop goes on with the page-state block in line 2682. That block prints the page state before the first interval. |
| 2627 | `            } else {` | The case of a position from 0 up: one interval. |
| 2628 | `                const struct entry *e = &cfg.seq[pos];` | `e`: the `--seq` entry of this position. |
| 2629 | `                const char *name = kernels[e->k].name;` | `name`: the name of its kernel. |
| 2630 | `                double per_pass = (double)e->bytes * (kernels[e->k].type == T_COPY ? 2 : 1);` | `per_pass`: the byte count of one pass over the range of the entry: its size, or twice its size for a copy kernel. The column `passes` of the T rows uses it (line 2661). |
| 2631 | `                uint64_t total = 0;` | `total`: the sum of the byte counts of all threads. It starts at 0. |
| 2632 | `                int64_t max_el = 0;` | `max_el`: the longest elapsed time of one thread, in ns. It starts at 0. |
| 2634 | `                pthread_barrier_wait(&bar); /* release the workers */` | First barrier call of the interval. It returns when all workers have finished the warm-up pass of this kernel and wait in line 1259. The barrier then lets all of these threads continue. With `--stop common` the workers do not start the kernel yet: each worker waits in an empty loop until `gen` changes (line 1261). The comment says: release the workers. |
| 2635 | `                if (cfg.stop_common) {` | Tests for `--stop common`. Only then `main` sets a common start (lines 2636 to 2639). With `--stop pass` each worker starts its timed interval directly after the barrier. |
| 2636 | `                    int64_t sched = now_ns() + LEAD_NS;` | Common start, set by the main thread. `main` reads the clock once and adds `LEAD_NS` (2 ms, line 99). The result `sched` is the common start time of all threads. `main` is not pinned. |
| 2637 | `                    atomic_store(&t_sched_ns, sched);` | Stores `sched` in the shared variable `t_sched_ns`. The lead of 2 ms is the time that `main` has for lines 2637 to 2639 and that the workers have to see the new `gen`. A worker that sees it only after `sched` has passed starts after the common start time. When its `t0` is then more than 100 us after `sched`, the late flag shows it (line 1309). |
| 2638 | `                    atomic_store(&deadline_ns, sched + (int64_t)(cfg.min_s * 1e9));` | Stores the deadline in the shared variable `deadline_ns`: `sched` plus `cfg.min_s`. |
| 2639 | `                    atomic_fetch_add(&gen, 1);` | Only after both stores `main` adds 1 to `gen`. So a worker that sees the new `gen` reads the new start time and the new deadline. Each worker then reads the clock in a loop until `sched`, and then reads its own start time `t0` (lines 1265 to 1272). After this line `main` passes nothing more to the workers. Each worker stops by itself, at its first clock read at or after the deadline (lines 1284 to 1285). |
| 2640 | `                }` | Ends the `if` of line 2635. |
| 2641 | `                pthread_barrier_wait(&bar); /* all workers finished this interval */` | Second barrier call of the interval. `main` blocks here until all workers have stored their results and wait in line 1311. So between the change of `gen` and the end of the timed interval this call is the only code that `main` runs. It prints nothing in that time. The comment says: all workers finished this interval. |

### Function `main`: the I row, the T rows and the C rows (lines 2643 to 2681)

| Line | Source | Explanation |
|---:|---|---|
| 2643 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the results of the threads. In a process with more than one thread every worker waits at the barrier of line 1315 from here to line 2691. So no kernel runs while `main` prints the I, T and C rows. |
| 2644 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i` for this interval (line 1310). |
| 2645 | `                    total += r->bytes;` | `total` becomes the sum of the byte counts of all threads. |
| 2646 | `                    if (r->t_end - r->t_start > max_el)` | Tests whether the elapsed time of this thread, `t_end - t_start` in ns, is the longest so far. `t_start` is the `t0` of the worker, and `t_end` is its last `t1` (lines 1306 to 1307). |
| 2647 | `                        max_el = r->t_end - r->t_start;` | Keeps the longest elapsed time in `max_el`. |
| 2648 | `                }` | Ends the loop of line 2643. |
| 2649 | `                if (cfg.threads == 1) { /* read by the worker before the interval */` | The branch of a process with one thread. There the worker has read the page state itself before the interval (lines 1254 to 1258), and `main` prints it here. The comment says: read by the worker before the interval. |
| 2650 | `                    print_p(round, pos, 0, 'a', &th[0].res.pg[0], th[0].res.vm);` | Prints the P row of buffer `a` (`print_p`, line 1154). |
| 2651 | `                    if (th[0].b)` | Tests whether the thread has a second buffer. |
| 2652 | `                        print_p(round, pos, 0, 'b', &th[0].res.pg[1], th[0].res.vm);` | Prints the P row of buffer `b`. It holds the same four counter values as the row of buffer `a`. |
| 2653 | `                }` | Ends the `if` of line 2649. |
| 2654 | `                printf("I,%d,%d,%s,%lu,%d,%lu,%.6f,%.2f\n", round, pos, name, (unsigned long)e->bytes, cfg.threads,` | I row, one per interval, with 9 fields: the letter `I`, round, position, kernel name, `bytes_per_thread`, thread count, `total_bytes`, `max_elapsed_s` and `aggregate_GBps`. `bytes_per_thread` is the size of the `--seq` entry. It is a setting, not a measured value. |
| 2655 | `                       (unsigned long)total, (double)max_el * 1e-9, (double)total / (double)max_el);` | Continues the call of line 2654. `total_bytes` is `total`. `max_elapsed_s` is `max_el` in seconds, with 6 decimals. `aggregate_GBps` is `total` in bytes divided by `max_el` in ns, with 2 decimals. One byte per ns is 1 GB/s with GB = 1e9 bytes. So this rate is the bytes of all threads divided by the longest elapsed time of one thread. |
| 2656 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 2657 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 2658 | `                    printf("T,%d,%d,%s,%d,%d,%lu,%.6f,%.6f,%.6f,%.6f,%.3f,%s\n", round, pos, name, i, th[i].cpu,` | T row, one per thread and interval, with 13 fields. Fields 1 to 6: the letter `T`, round, position, kernel name, thread index (`tid`) and the CPU of the thread. A thread without a CPU list shows -1. |
| 2659 | `                           (unsigned long)r->bytes, (double)(r->t_end - r->t_start) * 1e-9,` | Continues the call of line 2658. Field 7, `bytes`: the byte count of the worker (line 1280, line 1296). Field 8, `elapsed_s`: `t_end - t_start` in seconds, with 6 decimals. The rate of a thread is field 7 divided by field 8, in bytes per second. The program does not print it. |
| 2660 | `                           (double)(r->t_sched - t_base_ns) * 1e-9, (double)(r->t_start - t_base_ns) * 1e-9,` | Continues the call of line 2658. Fields 9 and 10, `t_sched_s` and `t_start_s`: the common start time and `t0`, in seconds after the process start `t_base_ns`, with 6 decimals. With `--stop pass` field 9 equals field 10 (line 1308). |
| 2661 | `                           (double)(r->t_end - t_base_ns) * 1e-9, (double)r->bytes / per_pass, r->late ? "late" : "-");` | Continues the call of line 2658. Field 11, `t_end_s`: the last `t1`, in seconds after the process start. Field 12, `passes`: `bytes / per_pass`, the number of passes over the range of the entry, with 3 decimals. Field 13, `flags`: `late` when `t0` came more than 100 us after the common start (line 1309), and `-` if not. |
| 2662 | `                }` | Ends the loop of line 2656. |
| 2663 | `                for (int i = 0; cfg.count && i < cfg.threads; i++) {` | Loop over the threads. It runs only with `--count`. It prints the C rows: one per thread and interval. |
| 2664 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 2665 | `                    printf("C,%d,%d,%s,%d,%d", round, pos, name, i, th[i].cpu);` | Starts a C row. Fields 1 to 6: the letter `C`, round, position, kernel name, thread index and CPU. |
| 2666 | `                    if (th[i].group_fd < 0)` | Tests whether the thread has no open counter group. |
| 2667 | `                        printf(",NA,NA");` | Fields 7 and 8 are then `NA`. |
| 2668 | `                    else` | The case of a thread with an open group. |
| 2669 | `                        printf(",%llu,%llu", (unsigned long long)(r->c1.enabled - r->c0.enabled),` | Fields 7 and 8, `enabled_ns` and `running_ns`: the enabled time and the running time of the counter group at the second reading minus the same values at the first reading. This line holds the enabled time. |
| 2670 | `                               (unsigned long long)(r->c1.running - r->c0.running));` | Continues the call of line 2669: the running time. |
| 2671 | `                    printf(",%llu", (unsigned long long)(r->c1.cpu_ns - r->c0.cpu_ns));` | Field 9, `cputime_ns`: the thread CPU time at the second reading minus the value at the first reading. The worker takes the first reading (`c0`) directly before `t0` and the second reading (`c1`) directly after its last `t1` (lines 1268 to 1271, lines 1301 to 1304). |
| 2672 | `                    for (int ev = 0; ev < cfg.nev; ev++) {` | Loop over the events, in the order of `--events`. |
| 2673 | `                        int at = th[i].ev_pos[ev];` | `at`: the place of the event in a group reading. It is -1 when the event did not open (line 1184). |
| 2674 | `                        if (at < 0)` | Tests whether the event did not open. |
| 2675 | `                            printf(",NA");` | Its field is then `NA`. |
| 2676 | `                        else` | The case of an event that opened. |
| 2677 | `                            printf(",%llu", (unsigned long long)(r->c1.val[at] - r->c0.val[at]));` | One field per event: the count at the second reading minus the count at the first reading. |
| 2678 | `                    }` | Ends the loop over the events (line 2672). |
| 2679 | `                    printf("\n");` | Ends the row with a line break. |
| 2680 | `                }` | Ends the loop of line 2663. |
| 2681 | `            }` | Ends the `else` of line 2627. |

### Function `main`: the page state, the P rows and the end (lines 2682 to 2703)

| Line | Source | Explanation |
|---:|---|---|
| 2682 | `            if (cfg.threads > 1) {` | Page-state block. It runs only in a process with more than one thread: once at position -1 and once after every interval. At this time every worker waits at a barrier: in line 1237 after position -1, in line 1315 after an interval. So no kernel runs while `main` reads the page state. |
| 2683 | `                /* Page state of all buffers, read between two intervals. It is` | Comment: the page state of all buffers is read between two intervals. The sentence goes on in line 2684. |
| 2684 | `                 * the state after interval pos (pos -1: before the first). The` | Comment: it is the state after interval `pos`. For `pos` -1 it is the state before the first interval. The sentence about the workers starts here. |
| 2685 | `                 * workers wait on the barrier below until it is read. */` | Comment: the workers wait at the barrier below (line 2691) until the state is read. |
| 2686 | `                long long vm[4];` | `vm`: will hold the four counters of `/proc/vmstat`. |
| 2687 | `                int64_t r0 = now_ns();` | `r0`: the clock value before the reading (`now_ns`, line 294). |
| 2688 | `                read_smaps(pg, bufs, 2 * cfg.threads);` | `read_smaps` (line 1099) looks up each entry of `bufs` in `/proc/self/smaps` and skips the NULL entries. It stores the size of each buffer and its part on 2 MiB pages in `pg`. |
| 2689 | `                read_vmstat(vm);` | `read_vmstat` (line 1129) reads the four counters of `/proc/vmstat`, once for the whole block. |
| 2690 | `                double ms = (double)(now_ns() - r0) * 1e-6;` | `ms`: the duration of both readings in ms: the clock value now minus `r0`. |
| 2691 | `                pthread_barrier_wait(&bar); /* the reading is done: the workers go on */` | Barrier call that lets the workers continue. Each worker then starts the warm-up pass of the next interval, while `main` prints the P rows below. After the last interval the workers end at this point. The comment says: the reading is done, and the workers go on. |
| 2692 | `                for (int i = 0; i < 2 * cfg.threads; i++)` | Loop over the entries of `bufs`. Entry `i` belongs to thread `i / 2`. An even `i` is buffer `a`, and an odd `i` is buffer `b`. |
| 2693 | `                    if (bufs[i])` | Skips an entry without a buffer. |
| 2694 | `                        print_p(round, pos, i / 2, i % 2 ? 'b' : 'a', &pg[i], vm);` | P row, one per existing buffer, printed by `print_p` (line 1154). The fields: the letter `P`, round, position, thread index, buffer letter, size of the buffer in kB, part on 2 MiB pages in kB, then the four counters of `/proc/vmstat`. The position is that of the interval before the reading, or -1 for the reading before the first interval. All rows of one block carry the same four counter values: they count for the whole system and were read once (line 2689). |
| 2695 | `                printf("# page_read,%d,%d,%.3f ms\n", round, pos, ms);` | Prints the line `# page_read` with the round, the position and `ms`, the duration of the page-state reading of this block, with 3 decimals and the unit `ms`. |
| 2696 | `            }` | Ends the `if` of line 2682. |
| 2697 | `            fflush(stdout);` | `fflush` writes all rows that are still in the output buffer to the standard output. Then the loops go on with the next position. A new timed interval cannot start before `main` has passed line 2634 again, and with `--stop common` also line 2639. So `main` writes no output during a timed interval. |
| 2698 | `        }` | Ends the loop over the positions (line 2617). Between two intervals lie the output of the rows, the page-state reading, the barrier calls, the warm-up pass of the next kernel and, with `--stop common`, the 2 ms lead. No code of the interval mode calls a sleep function. |
| 2699 | `    }` | Ends the loop over the rounds (line 2616). |
| 2700 | `    for (int i = 0; i < cfg.threads; i++)` | Loop over the threads, after the last interval. |
| 2701 | `        pthread_join(th[i].tid, NULL);` | Waits for the end of worker thread `i` (`pthread_join`). |
| 2702 | `    return 0;` | Returns 0: the process ends with exit status 0. |
| 2703 | `}` | Ends the function `main`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx11-crb-build-1/listing.txt`: objdump text of the 29 kernel functions of the `bwx11` binary that was built on CRB on 2026-11-15. Source of the start addresses, the loop starts and the instruction counts. Each function stands under a heading such as `=== bwx11 read ===`. The file `offsets.tsv` of the same folder lists the start address and the loop start of each kernel.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx11-crb-build-1/build.txt`: build record of CRB. The row `## cc=` names the compiler, gcc 14.2.0. The row `## CFLAGS=` gives the flags. They hold no `-D` option, and the build command of `build11.sh` adds none. The rows `## placement bwx11`, `## placement bwx10` and `## placement bwx8` all hold `call=24`: the function `call` starts at 24 modulo 64 in the three binaries. The block `## sha256:` gives the sha256 of `bwx11.c` at the build. It is the sha256 of the source file of this page.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/probe.txt`: objdump text of the kernels of `bw_new` (sections `=== bw_new ... ===`) and of `bw_old` (sections `=== bw_old ... ===`). Compared with the listing of [Ref1] by a script on 2026-11-25, with absolute code addresses and data addresses left out. `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite` and `k_asmcopy` of `bw_new` have the instruction text of the functions with the same names in `bwx11`. `k_read`, `k_write` and `k_copy` of `bw_old` have the instruction text of `k_oldread`, `k_oldwrite` and `k_oldcopy` of `bwx11`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: sections B.4 to B.8, the specification of the first runner `bwx` that the comments cite: the two stop methods (B.4), the start offsets (B.5), the page state (B.6), the loop addresses (B.7) and the counters (B.8). B.7 names the loop offset as a factor of step B3. B.8 says that counter code without user-mode counting fails without root on CRB, and that a counter is opened with `pid = 0` and `cpu = -1`.
- [Ref5] `/usr/include/linux/perf_event.h`: the comment above `enum perf_event_read_format` (header of the machine on which this page was written). With `PERF_FORMAT_GROUP` the data of one `read` are `nr`, `time_enabled`, `time_running` and then one value per counter.
- [Ref6] external source: Linux kernel documentation on docs.kernel.org, read on 2026-11-25. Page https://docs.kernel.org/admin-guide/mm/transhuge.html: `thp_fault_alloc` "is incremented every time a huge page is successfully allocated and charged to handle a page fault". `thp_fault_fallback` "is incremented if a page fault fails to allocate or charge a huge page and instead falls back to using small pages". `thp_collapse_alloc` is incremented when the Linux thread khugepaged has allocated a huge page for a range of pages that it joins. Page https://docs.kernel.org/mm/page_migration.html: page migration moves the physical location of pages, and for the counter of successful migrations "Each count means that a page was migrated".
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design of the investigation into the small gain of the new read kernel at 8 MiB. Its section "Runner design" describes the trial mode: one pinned worker, the trial with prefix, predecessor and target windows, and the required records.
- [Ref8] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb-results.md`: the result handoff of that investigation. Its table "What ran" names `bwx11` as the binary of round 4, with the first 8 digits of its sha256, `f1215f9e`. The build record gives a sha256 with these first digits for the binary `bwx11` [Ref2].
