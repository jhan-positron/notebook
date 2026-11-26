# `bwx13.c` explained, line by line

- Source file: `bwx13-2026-11-15/bwx13.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 3289 lines, 126072 bytes).
- sha256 of the source when this page was built: `72cb3b7b5a5043f1fd67050f2dbf8167d0271a5f593fc498675640b9f2fb25ca`.

## Short version: purpose

`bwx13.c` is the last version of the runner: one process starts the threads, each thread runs the kernels of a list on its own buffer, and the program prints the bytes and the times of every thread and interval as csv rows. It is `bwx12.c` plus three read kernels, `rand_nop0`, `rand_nop96` and `rand_nop256`, which read the 256 B blocks of a range in a scrambled order and not in address order. The notes of the investigation of the whole-chip read rate of 2026-11-15 give their purpose: to test whether the lower rate of a load-only loop needs a read in address order [Ref8].

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
- **Load-only loop**: a read kernel that loads data and computes nothing with the loaded values, for example the new read kernel, `asmread` and the `rand_nop` kernels.
- **`rand_nop` kernels**: `rand_nop0`, `rand_nop96` and `rand_nop256`, the three kernels that `bwx13` adds. Each reads every 256 B block of its range once, in a scrambled order, with 0, 96 or 256 `nop` instructions after the loads of each block.
- **Block**: 256 B of a range: the bytes that one loop pass of `asmread` or of a `rand_nop` kernel loads.
- **Scrambled order**: the order in which a `rand_nop` kernel reads the blocks of one call. Step `i` reads the block `(i * (2 * i + 1)) mod nb`. `nb` is the number of blocks of the call and must be a power of two. The source comment calls the order random. It is the same in every call.
- **Prefetcher, stride**: a prefetcher is the part of a core that loads memory ahead of the program. A stride is a fixed distance between two accesses.
- **Stop rules of the runner**: `--stop pass` selects the whole-pass stop. `--stop common` selects the common stop.
- **Interval mode, trial mode**: the two modes of the program. The interval mode (option `--seq`) runs the number of threads that `--threads` gives and times one interval per round and kernel of the sequence. The trial mode (option `--trial`) runs one worker thread through the trials of a plan file.
- **Kernel table, `kernels[]`**: the array of lines 1611 to 1640. Each entry holds the name of a kernel (the word used in `--seq`), its type (`T_READ`, `T_WRITE`, `T_COPY` or `T_OLDREAD`) and a pointer to its function. In this version it has 58 entries.
- **`cfg`**: the structure that holds the settings from the arguments: thread count, CPU list, buffer size, kernel sequence, rounds, stop rule and counter settings (lines 295 to 313).
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
- **Placement**: the start addresses modulo 64 of the functions from `call` to `timed_sequence_hot`. The pad after the last kernel keeps them equal to those of the versions before. The build record reports the same placement as in `bwx12`, `bwx11` and `bwx10`, and the same placement up to `timed_sequence` as in `bwx8` [Ref2].
- **Stand-in**: a plain C loop that replaces a NEON kernel or an assembly kernel when the file is compiled for a machine that is not AArch64. The rates of such a build mean nothing.
- **Development machine**: the machine on which the program was written and tested before the build on CRB. The stand-in kernels exist for it.
- **A/A copy**: the same kernel source under a second name, for example `asmread2`.
- **History comment, marker lines**: from `bwx10` on, each version of the runner puts a comment at the top of the file that lists its additions. Every addition of such a version stands between two comment lines, for example `bwx13+` and `bwx13-`. The additions of `bwx8` have no such lines.
- **Round 3, round 4, round 5 (in source comments)**: rounds of work on the program on 2026-11-15. They produced the versions `bwx10`, `bwx11` and `bwx12`. They are not rounds of the option `--rounds`.
- **`handoff.md`**: the specification of the first runner `bwx`. The comments cite its sections B.4 to B.8 [Ref5].
- **Build record**: the files that the build script `build13.sh` wrote on CRB. `build.txt` holds the compiler, the flags, the placement and the sha256 values [Ref2]. `listing.txt` holds the machine-code listing of every kernel [Ref1].
- **Plan file, trial, window (trial mode)**: the plan file lists the trials of one process. A trial is a list of windows. A window runs one kernel on one range of the buffer for a fixed time.
- **Phase, target window (trial mode)**: a trial has up to four phases, in this order: previous activity (1 window), prefix (4 windows), predecessor (1 window) and target. A target window is a window of the last phase.
- **Timed sequence (trial mode)**: the run of all windows of one trial, done by the function `timed_sequence` or, with the option `--hot-copy`, by `timed_sequence_hot`.
- **Counter state (trial mode)**: the field `count` of a plan line: `closed` (no counter group is open), `open` (the group is open and is not read during the trial) or `read` (the group is read at the boundaries of the target windows).
- **Record block (trial mode)**: one memory block that holds the records of all trials: the trial records, the window records, the counter readings, the bins and, with `--trace`, the event log.
- **Bin, trace, evict step (trial mode)**: a bin is a part of a target window with a requested length of 10 ms. The trace (`--trace`) is a log of events with clock times. The evict step (`--evict-mb`) writes other memory before the first trial. The aim is that the buffer leaves the caches.
- **Controlling thread (trial mode)**: the thread that runs `trial_main`. It pins itself to the CPU of `--ctl-cpu`, starts the one worker of the trial mode and waits for its end.
- **S, W, B, E, X, TR, M, K rows (trial mode)**: row kinds that only the trial mode prints: S (the plan line of a trial), W (one window), B (one bin), E (the summary of a trial), X (a problem), TR (one trace event), M (one setting or one fact of the process) and K (the address of one kernel).
- **Context switch**: Linux stops running a thread on its CPU. It is voluntary when the thread waits by itself, and involuntary when Linux takes the CPU away.
- **Minor page fault**: a page fault that Linux serves without disk access. The first touch of a page is one.

## Main flow

1. Start. `main` reads the clock once for the process start time `t_base_ns`, reads the page size and sets the default buffer size of 1 MiB. Then `restrict_cpus` removes every CPU above 119 from the allowed CPU set of the process (lines 3067 to 3074).
2. Mode choice. `main` compares every argument with the word `--trial`. When one is equal, it calls `trial_main` and returns its result. Otherwise it goes on in the interval mode, which is the rest of `main` (lines 3075 to 3077).
3. Argument parsing. One loop over the arguments fills the settings structure `cfg`: threads, CPU list, bytes per thread, interval length, rounds, the `--seq` list, the stop rule, the start rule and the counter settings. `--selftest` and `--list` end the program in this loop (lines 3079 to 3131).
4. Checks of the settings. A failed check prints the option summary and ends the program with exit status 2. Each `--seq` entry without `@SIZE` gets the size of `--bytes`, and a copy kernel in the list gives each thread a second buffer (lines 3132 to 3163).
5. Threads. `main` creates a barrier for all workers plus itself and starts one thread per worker. Thread `i` gets entry `i` of the CPU list (lines 3165 to 3179).
6. Each worker pins itself to its CPU, opens its counters when `--count` is given, maps its buffer with `alloc_buf` and writes every word of the `--bytes` range of it once with `k_write`. This write is the first touch (lines 1797 to 1806).
7. Header. `main` prints the header lines: the settings and the column names of the I, T, P and C rows (lines 3181 to 3200).
8. Only in a process with more than one thread: when all buffers exist, `main` reads the page state of all buffers and prints P rows with the position -1 (lines 3204 to 3212, lines 3268 to 3282).
9. Loops. The workers and `main` run the same two loops: the rounds, and inside a round the positions of the `--seq` list. One pair of round and position is one interval (lines 1812 to 1813, lines 3202 to 3203).
10. Warm-up pass. Each worker calls the kernel of the position once over the whole range of the entry. This call is not timed (line 1825).
11. Common start, only with `--stop common`. When all workers wait at the barrier, `main` reads the clock, sets the start time to that value plus 2 ms and the deadline to the start time plus the `--min-ms` value, and then adds 1 to `gen` (lines 3220 to 3225). Each worker waits for the new `gen` and then reads the clock in a loop until the start time (lines 1832 to 1839).
12. Start of the timed interval. With `--count` the worker first reads its counter group and its thread CPU time. Then it reads the clock: `t0` (lines 1840 to 1844).
13. Timed loop with `--stop common`. The worker calls the kernel on one chunk of 2 MiB, adds the size of the chunk to its byte count and reads the clock: `t1`. It repeats this with the next chunk until `t1` is at or after the deadline (lines 1846 to 1857).
14. Timed loop with `--stop pass`. The worker runs whole passes over the range of the entry. It reads the clock after a fixed number of passes: 8 MiB divided by the size of the entry, rounded down, and at least 1 pass. It stops when the `--min-ms` time has passed after `t0` (lines 1858 to 1872).
15. End of the interval, worker. The worker reads its thread CPU time and its counter group again. It stores the byte count, `t0`, the last `t1`, the common start time and the late flag, and it waits at the barrier (lines 1873 to 1887).
16. I row. `main` adds the bytes of all threads and takes the longest elapsed time `t1 - t0` of one thread. The last column of the I row is the total divided by that time, in GB/s (lines 3229 to 3241).
17. T rows and C rows. `main` prints one T row per thread with its bytes and its times, and with `--count` one C row per thread with the change of its counters over the interval (lines 3242 to 3266).
18. Page state, in a process with more than one thread. While the workers wait at the barrier, `main` reads the page state of all buffers. Then it releases the workers and prints the P rows and one `# page_read` line (lines 3268 to 3282). In a process with one thread the worker reads the page state itself before each interval, and `main` prints its P rows before the I row (lines 1826 to 1830, lines 3235 to 3239).
19. End. After the last interval `main` waits for the end of all threads and returns 0 (lines 3286 to 3288).

## Behavior a reader must know

- Difference to `bwx12.c`: additions only. The command `diff` shows 163 added lines in five blocks, each between a `bwx13+` line and a `bwx13-` line: the history comment (lines 1 to 31), the three kernels with their pads (lines 1482 to 1603), three entries of the kernel table (lines 1636 to 1638) and the two blocks around the include of the self-test file (lines 3056 to 3058, lines 3060 to 3063). No option and no output row changed.
- What a `rand_nop` kernel reads: the same bytes as `asmread`, every 256 B block of the range of one call once, with 8 `ldp` loads per block. Only the order differs. With `--stop common` one call is one chunk of 2 MiB, which is 8192 blocks. So the order is scrambled inside a chunk, and the chunks follow one another in address order (lines 1849 to 1855).
- The scrambled order needs a number of blocks that is a power of two. For any other number the kernel reads the blocks in address order, as `asmread` does (line 1542, lines 1555 to 1561). With `--stop pass` the number of blocks is that of the whole `--seq` entry. When `--start offset` is given too, a thread whose start offset is not 0 makes two calls in each pass, and each call orders the blocks of its own part (lines 1865 to 1867).
- A `rand_nop` kernel has 5 more instructions per block than the kernel with the same number of `nop`: 16, 112 and 272 instructions against 11 in `asmread`, 107 in `read_nop96` and 267 in `read_nop256`. The 5 instructions compute the address of the block (lines 1544 to 1548).
- The byte count of a `rand_nop` kernel is the count of every read kernel: the size of the range of each finished call (line 1852). Nothing is counted inside a kernel.
- CRB build of `bwx13`. The source of this page has the sha256 that the build record gives for `bwx13.c` [Ref2]. The listing check reports for each of the 55 kernels of `bwx12` the instruction text and the loop offset of the `bwx12` build, and the expected code and the loop offset 20 for the three new kernels [Ref4]. The function `call` starts at 24 modulo 64, as in `bwx12` [Ref2].
- Limit of the self-test, from the header comment of `bwx13_selftest.c`: on AArch64 the self-test cannot see in which order the assembly text reads the blocks, as a read changes no memory. The machine-code listing and its check are the evidence for the order [Ref1] [Ref4].
- What is timed: only lines 1844 to 1856 or lines 1844 to 1870 of `worker`. The interval starts at the clock read `t0` and ends at the last clock read `t1`. Between them lie the kernel calls through `call`, the byte count and the clock reads. Not timed: allocation, first touch, warm-up pass, barrier waits, the wait for the common start, counter readings, page-state readings and all output.
- Stop rule `--stop common`: all threads get the same deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted (line 1857).
- Rate. The program prints one rate: the last column of the I row, the bytes of all threads divided by the longest elapsed time of one thread, in GB/s with GB = 1e9 bytes (line 3241). A T row holds the bytes and the elapsed time of one thread and no rate (line 3245).
- Kernel calls. With `--stop common` the kernel function is entered once per chunk. A kernel that saves `d8` to `d15` does so once per call, outside its loop. One clock read follows each call (lines 1851 to 1856).
- Thread placement: thread `i` pins itself to entry `i` of the CPU list before it opens its counters and before it maps its buffer (lines 1797 to 1801, line 3174). The main thread is not pinned in the interval mode.
- Buffers: each buffer is a private mapping of its own, and no two threads share a buffer. A thread has one buffer, or two with `--two-buffers` or with a copy kernel in `--seq`. A buffer starts at a 2 MiB boundary, and `alloc_buf` asks Linux for 2 MiB pages for it unless `--no-thp` is given. The pinned thread writes the `--bytes` range of the buffer once before any read. The read kernels never change it (lines 465 to 482, lines 1801 to 1802).
- Order inside a process: the kernels run in the order of `--seq`, and the rounds follow one another directly. The file holds no call of a sleep function. Before each timed interval the worker runs the warm-up pass with the kernel of that interval (line 1825).
- Counters in the interval mode: each thread opens its group once and never resets it. A C row holds the change between a reading directly before `t0` and a reading directly after the last `t1`. An event that does not open is printed as `NA` (line 1756, lines 3260 to 3261).
- What ends a process of the interval mode with exit status 2: a bad argument, a failed `mmap`, a failed call that reads or sets the allowed CPU set, an allowed CPU set without a CPU from 0 to 119, a failed read of the counter group, and a failed setup in `main`. A failed `mprotect` or `madvise` in `alloc_buf` only writes a message, and the run continues (line 476, line 480). The trial mode also ends with exit status 2 on a defect of its plan file.
- The code of this file does not look at the marker file and opens files only for reading. Its output is the csv text on the standard output and the messages on stderr.

## Source and explanation, line by line

- Text shown: the file `bwx13-2026-11-15/bwx13.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (3289 lines, 126072 bytes, sha256 `72cb3b7b5a5043f1fd67050f2dbf8167d0271a5f593fc498675640b9f2fb25ca`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### History comment of the version `bwx13`: three `rand_nop` kernels and a fourth pad (lines 1 to 31)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/* bwx13+ */` | Comment: a marker. A block of text that the version `bwx13` added starts here. The marker of line 31 ends the block. |
| 2 | `/*` | Opens a history comment. It tells what the version `bwx13` added to the runner. |
| 3 | ` * bwx13.c - bwx12.c plus three read kernels (2026-11-15). Every addition` | Comment: `bwx13.c` is `bwx12.c` plus three read kernels, made on 2026-11-15. This file holds five history comments, one per version of the runner. This is the first one. |
| 4 | ` * stands between a line "bwx13+" and a line "bwx13-" (both are comments).` | Comment: every addition stands between a marker line `bwx13+` and a marker line `bwx13-`. Both marker lines are comments. |
| 5 | ` * Without these blocks this file is bwx12.c byte for byte. So the 55 kernels` | Comment: without these blocks the text of this file is `bwx12.c`, byte for byte. The command `diff` confirms it: every difference between the two files is a block of added lines, 163 lines in all, and each block starts with a `bwx13+` line and ends with a `bwx13-` line. The sentence about the 55 kernels starts here. |
| 6 | ` * of bwx12, call(), timed_sequence(), timed_sequence_hot(), the interval mode` | Comment: so some parts are the text of `bwx12.c` without a change. This line names the 55 kernels of `bwx12` and the functions `call` (line 1647), `timed_sequence` (line 2151) and `timed_sequence_hot` (line 2212). The list goes on in line 7. |
| 7 | ` * and the trial mode are the text of bwx12.c.` | Comment: the same holds for the two modes of the program. The interval mode (option `--seq`) times one interval for each kernel of a list, in each round of the option `--rounds`. The trial mode (option `--trial`) runs one worker thread through the trials of a plan file. |
| 8 | ` *` | Comment: an empty line of the comment. |
| 9 | ` * Additions: rand_nop0, rand_nop96, rand_nop256. They stand after the last` | Comment: the additions are the three kernels `rand_nop0`, `rand_nop96` and `rand_nop256` (lines 1590 to 1592). In the source they stand after the last kernel of `bwx12`. |
| 10 | ` * kernel of bwx12 in the source and in kernels[], so the kernels of bwx12` | Comment: in the kernel table `kernels[]` they also stand after the last kernel of `bwx12` (line 1637). The reason follows in line 11. |
| 11 | ` * keep their machine code and their loop offsets. No option and no output` | Comment: so the kernels of `bwx12` keep their machine code and their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. The listing check of the CRB build of `bwx13` reports for each of the 55 kernels the instruction text and the loop offset of the `bwx12` build [Ref4]. The sentence about options starts here. |
| 12 | ` * row is added.` | Comment: this version adds no option and no kind of output row. |
| 13 | ` *   rand_nopN reads the bytes that asmread reads: every 256 B block of the` | Comment: a `rand_nop` kernel reads the bytes that the kernel `asmread` reads: every block of 256 B of its range. The sentence goes on in line 14. |
| 14 | ` *     range once, with 8 ldp of q registers per block. The order of the` | Comment: it reads each block once, with 8 `ldp` instructions per block. An `ldp` of `q` registers loads 32 B into two 16-byte vector registers. The sentence about the order starts here. |
| 15 | ` *     blocks differs. With nb = bytes / 256 blocks and nb a power of two,` | Comment: only the order of the blocks differs from `asmread`. `nb` is the number of blocks: the bytes of one call divided by 256. The rule of line 16 holds when `nb` is a power of two. |
| 16 | ` *     step i (0 to nb - 1) reads block (i * (2 * i + 1)) & (nb - 1). The` | Comment: step `i`, counted from 0 to `nb - 1`, reads the block with the number `(i * (2 * i + 1)) & (nb - 1)`. The operation `& (nb - 1)` keeps the low bits of the product: the remainder of a division by `nb`. For 8 blocks this gives the order 0, 3, 2, 5, 4, 7, 6, 1. |
| 17 | ` *     distance between two blocks read one after the other changes at every` | Comment: the distance between two blocks that are read one after the other changes at every step. The sentence goes on in line 18. |
| 18 | ` *     step, so a prefetcher that follows a constant stride cannot follow it.` | Comment: so a prefetcher that follows a constant stride cannot follow this order. A prefetcher is the part of a core that loads memory ahead of the program. A stride is a fixed distance between two accesses. This is the aim of the design. The comment gives no measurement for it. |
| 19 | ` *     If nb is not a power of two, the order is that of asmread (block i at` | Comment: when `nb` is not a power of two, the order is that of `asmread`: step `i` reads block `i`. |
| 20 | ` *     step i). After the 8 ldp of a block stand N nop instructions.` | Comment: after the 8 `ldp` of a block stand N `nop` instructions. N is the number in the kernel name: 0, 96 or 256. A `nop` is an instruction that does nothing. |
| 21 | ` *   A kernel orders the blocks of one call. In the interval mode with` | Comment: a kernel orders only the blocks of one call. The sentence about the interval mode starts here. |
| 22 | ` *     --stop common one call is one chunk of 2 MiB (8192 blocks), so the` | Comment: in the interval mode with `--stop common` one call covers one chunk of 2 MiB, which is 8192 blocks (lines 1849 to 1851). |
| 23 | ` *     order is random inside a chunk, and the chunks follow in address order.` | Comment: so the order is scrambled inside a chunk, and the chunks follow one another in rising address order. The comment calls the order random. It is a fixed order: every call with the same number of blocks uses the same order. |
| 24 | ` *     With --stop pass one call is the whole size.` | Comment: with `--stop pass` one call covers the whole size of the `--seq` entry (line 1865). The comment leaves out one case. When `--start offset` is given too, a thread whose start offset is not 0 makes two calls in each pass, one for each part of the range (lines 1865 to 1867). Each call orders its own blocks. A call whose number of blocks is not a power of two reads them in address order (line 1542). |
| 25 | ` *   A fourth pad after these kernels, so that call() and the code up to the` | Comment: the last addition is a fourth pad after these kernels (lines 1599 to 1602). A pad is a run of unused bytes in the code. This pad sets the start address of the function `call`, which follows the kernels. |
| 26 | ` *     end of timed_sequence_hot() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence_hot` keeps its placement modulo 64. The build record of CRB gives 24 as the start address of `call` modulo 64, for `bwx13` and for `bwx12` [Ref2]. |
| 27 | ` * The line that includes the self-test file is changed by additions only: the` | Comment: the line that includes the self-test file is changed by additions only (lines 3056 to 3063). |
| 28 | ` * old line stands inside "#if 0".` | Comment: the old include line stands inside `#if 0`. So the compiler skips it, and no old line was deleted. |
| 29 | ` * MAX_SEQ stays 64: the 58 kernels fit in one --seq list.` | Comment: `MAX_SEQ` (line 159) stays 64. It is the largest number of entries of a `--seq` list. So one list can name all 58 kernels of `bwx13`. |
| 30 | ` */` | Ends the history comment. |
| 31 | `/* bwx13- */` | Comment: a marker. The block that line 1 opened ends here. |

### History comment of the version `bwx12`: 26 more kernels and a third pad (lines 32 to 64)

| Line | Source | Explanation |
|---:|---|---|
| 32 | `/* bwx12+ */` | Comment: a marker. A block of text that the version `bwx12` added starts here. The marker of line 64 ends the block. |
| 33 | `/*` | Opens a history comment. It tells what one version of the runner added. Here it is the version that the marker of line 32 names. |
| 34 | ` * bwx12.c - bwx11.c plus the additions of round 5 (2026-11-15). Every` | Comment: `bwx12.c` is `bwx11.c` plus the additions of round 5, made on 2026-11-15. Round 5 is a round of work on the program. It is not a round of the option `--rounds`. This is the second of the five history comments of this file. |
| 35 | ` * addition stands between a line "bwx12+" and a line "bwx12-" (both are` | Comment: every addition of that round stands between a marker line `bwx12+` and a marker line `bwx12-`. |
| 36 | ` * comments). Without these blocks this file is bwx11.c byte for byte. So the` | Comment: both marker lines are comments. Without the `bwx12` blocks the text of `bwx12.c` is `bwx11.c`, byte for byte. The script `test_kernels12.py` in the code folder `bwx12-2026-11-15` tests this for `bwx12.c`. |
| 37 | ` * 29 kernels of bwx11, call(), timed_sequence(), timed_sequence_hot(), the` | Comment: so some parts are the text of `bwx11.c` without a change. This line names the 29 kernels of `bwx11` and the functions `call` (line 1647), `timed_sequence` (line 2151) and `timed_sequence_hot` (line 2212). |
| 38 | ` * interval mode and the trial mode are the text of bwx11.c.` | Comment: the same holds for the two modes of the program. The interval mode (option `--seq`) times one interval for each kernel of a list, in each round of the option `--rounds`. The trial mode (option `--trial`) runs one worker thread through the trials of a plan file. |
| 39 | ` *` | Comment: an empty line of the comment. |
| 40 | ` * Additions: 26 kernels. They stand after the last kernel of bwx11 in the` | Comment: the additions are 26 kernels. In the source they stand after the last kernel of `bwx11`. |
| 41 | ` * source and in kernels[], so the kernels of bwx11 keep their machine code` | Comment: in the kernel table `kernels[]` the new kernels also stand after the last kernel of `bwx11` (lines 1628 to 1634). So the kernels of `bwx11` keep their machine code. |
| 42 | ` * and their loop offsets. No option and no output row is added.` | Comment: the kernels of `bwx11` also keep their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. Round 5 adds no option and no kind of output row. |
| 43 | ` *   read_nop48, read_nop56, read_nop72, read_nop80, read_nop88, read_nop112,` | Comment: names 6 of the 9 new `read_nop` kernels: `read_nop48`, `read_nop56`, `read_nop72`, `read_nop80`, `read_nop88` and `read_nop112` (lines 1222 to 1227). |
| 44 | ` *     read_nop160, read_nop192, read_nop256: the asmread loop with that many` | Comment: names the other 3: `read_nop160`, `read_nop192` and `read_nop256` (lines 1228 to 1230). Each of the 9 is the loop of the kernel `asmread` with as many `nop` instructions as its name says. A `nop` is an instruction that does nothing. |
| 45 | ` *     nop instructions after the 8 ldp (the macro of read_nop64).` | Comment: the `nop` instructions stand after the 8 `ldp` instructions, which load the data. The 9 kernels come from the macro `DEF_ASMREAD` (line 647). The same macro defines `read_nop64` (line 1093). |
| 46 | ` *   read_dadd2, read_dadd4, read_dadd8, read_dadd16: the asmread loop with 2,` | Comment: names the kernels `read_dadd2`, `read_dadd4`, `read_dadd8` and `read_dadd16` (lines 1304 to 1310). Each is the `asmread` loop with vector adds. |
| 47 | ` *     4, 8 or 16 vector adds after the 8 ldp. Each add takes a register that` | Comment: they have 2, 4, 8 or 16 vector adds after the 8 `ldp`. Each add takes as an input a register that the same loop pass loaded. |
| 48 | ` *     this iteration loaded, so it cannot run before the load data arrives.` | Comment: so the core cannot execute such an add before the data of the load has arrived. |
| 49 | ` *   read_iadd16: the asmread loop with 16 vector adds that take no loaded` | Comment: the kernel `read_iadd16` (line 1311) is the `asmread` loop with 16 vector adds that take no loaded register as an input. |
| 50 | ` *     register. It is the control of read_dadd16.` | Comment: `read_iadd16` is the control of `read_dadd16`. It has the same number of adds, but no add waits for a load. |
| 51 | ` *   read_sp24, read_sp32, read_sp40, read_sp48, read_sp56: the read_sparse` | Comment: names the kernels `read_sp24`, `read_sp32`, `read_sp40`, `read_sp48` and `read_sp56` (lines 1337 to 1341). Each is the loop of the kernel `read_sparse` (line 683) with another number of `nop`. |
| 52 | ` *     loop (128 B per iteration, 4 ldp) with that many nop in place of 9.` | Comment: the `read_sparse` loop handles 128 B per loop pass with 4 `ldp`. It has 9 `nop`. The new kernels have 24, 32, 40, 48 or 56 `nop` in their place. |
| 53 | ` *   read_1pl_nop96: the read_1pl loop with 96 nop after the 4 loads.` | Comment: the kernel `read_1pl_nop96` (line 1346) is the loop of the kernel `read_1pl` (line 1019) with 96 `nop` after its 4 loads. |
| 54 | ` *   write_nop32, write_nop96, write_nop128, write_nop256: the asmwrite loop` | Comment: names the kernels `write_nop32`, `write_nop96`, `write_nop128` and `write_nop256` (lines 1392 to 1395). Each is the loop of the kernel `asmwrite`. |
| 55 | ` *     with that many nop after the 8 stp.` | Comment: they have 32, 96, 128 or 256 `nop` after the 8 `stp` instructions, which store the data. |
| 56 | ` *   copy_nop96, copy_nop192: the asmcopy loop with that many nop after the` | Comment: the kernels `copy_nop96` and `copy_nop192` (lines 1435 to 1436) are the loop of the kernel `asmcopy` with 96 or 192 `nop`. |
| 57 | ` *     8 stp.` | Comment: in the two copy kernels the `nop` instructions stand after the 8 `stp`. |
| 58 | ` *   A third pad after these kernels, so that call() and the code up to the` | Comment: the last addition of the list is a third pad after the new kernels (lines 1477 to 1480). A pad is a run of unused bytes in the code. In `bwx12.c` the function `call` follows this pad, so there the pad sets the start address of `call`. In this file the kernels of `bwx13` follow it. |
| 59 | ` *     end of timed_sequence_hot() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence_hot` keeps its placement modulo 64. The build record of the CRB build of `bwx13` gives 24 as the start address of `call` modulo 64, for `bwx13`, for `bwx12` and for `bwx11` [Ref2]. |
| 60 | ` * The line that includes the self-test file is changed by additions only: the` | Comment: in `bwx12.c` the line that includes the self-test file is changed by additions only. In this file the additions of `bwx12` stand in lines 3050 to 3052, lines 3054 to 3055, line 3059 and line 3064. The old line is line 3053. |
| 61 | ` * old line stands inside "#if 0".` | Comment: the old include line stands inside `#if 0`. So the compiler skips it, and no old line was deleted. |
| 62 | ` * MAX_SEQ stays 64: the 55 kernels fit in one --seq list.` | Comment: `MAX_SEQ` (line 159) stays 64. It is the largest number of entries of a `--seq` list. So one list can name all 55 kernels of `bwx12`. |
| 63 | ` */` | Ends the history comment. |
| 64 | `/* bwx12- */` | Comment: a marker. The block that line 32 opened ends here. |

### History comment of the version `bwx11`: three kernels and the option `--evict-mb` (lines 65 to 90)

| Line | Source | Explanation |
|---:|---|---|
| 65 | `/* bwx11+ */` | Comment: a marker. A block of text that the version `bwx11` added starts here. The marker of line 90 ends the block. |
| 66 | `/*` | Opens a history comment. It tells what the version of the marker in line 65 added. |
| 67 | ` * bwx11.c - bwx10.c plus the additions of round 4 (2026-11-15). Every` | Comment: `bwx11.c` is `bwx10.c` plus the additions of round 4, made on 2026-11-15. Round 4 is a round of work on the program. It is not a round of the option `--rounds`. |
| 68 | ` * addition stands between a line "bwx11+" and a line "bwx11-" (both are` | Comment: every addition of that round stands between a marker line `bwx11+` and a marker line `bwx11-`. |
| 69 | ` * comments). Without these blocks this file is bwx10.c byte for byte:` | Comment: both marker lines are comments. Without these blocks the text of `bwx11.c` is `bwx10.c`, byte for byte. |
| 70 | ` * test_runner11.py checks it. So the 26 kernels of bwx10, call(),` | Comment: the script `test_runner11.py` in the code folder `bwx11-2026-11-15` checks this. So the 26 kernels of `bwx10` and the function `call` (line 1647) are the text of `bwx10.c` without a change. |
| 71 | ` * timed_sequence(), timed_sequence_hot() and the interval mode are the text` | Comment: the same holds for the functions `timed_sequence` (line 2151) and `timed_sequence_hot` (line 2212) and for the interval mode, the mode of the option `--seq`. |
| 72 | ` * of bwx10.c.` | Comment: the end of the sentence of lines 70 to 71. The parts that it names are the text of `bwx10.c`. |
| 73 | ` *` | Comment: an empty line of the comment. |
| 74 | ` * Additions:` | Comment: the heading of the list of additions. |
| 75 | ` *   kernels read_nop64, read_nop96, read_nop128: the asmread loop with 64, 96` | Comment: three kernels: `read_nop64`, `read_nop96` and `read_nop128` (lines 1093 to 1095). Each is the loop of the kernel `asmread` with `nop` instructions added. A `nop` is an instruction that does nothing. |
| 76 | ` *     and 128 nop instructions after the 8 ldp. They stand after the last` | Comment: the three kernels have 64, 96 and 128 `nop` after the 8 `ldp` instructions, which load the data. In the source they stand after the last kernel of `bwx10`. |
| 77 | ` *     kernel of bwx10 in the source and in kernels[], so the kernels of bwx10` | Comment: in the kernel table `kernels[]` they also stand after the kernels of `bwx10` (line 1625). |
| 78 | ` *     keep their machine code and their loop offsets.` | Comment: so the kernels of `bwx10` keep their machine code and their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. |
| 79 | ` *   A second pad after these kernels, so that call() and the code up to the` | Comment: a second pad after these kernels (lines 1103 to 1106). A pad is a run of unused bytes in the code. In the version `bwx11` it sets the start address of the function `call`. |
| 80 | ` *     end of timed_sequence_hot() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence_hot` keeps its placement modulo 64. |
| 81 | ` *   --evict-mb N  (trial mode) before the first trial the worker writes N MiB` | Comment: the option `--evict-mb N` of the trial mode. Before the first trial the worker writes N MiB of other memory, twice (line 2584). |
| 82 | ` *     of other memory twice. This pushes the benchmark buffer out of the` | Comment: after these writes the caches no longer hold the data of the benchmark buffer. |
| 83 | ` *     caches, so its lines are read back from memory.` | Comment: so the next read of the buffer brings its cache lines back from memory. A cache line is a block of 64 B. |
| 84 | ` *   M rows evict_mb and evict_ns. With --trace and N above 0 also the rows` | Comment: two new M rows, `evict_mb` and `evict_ns` (lines 2657 to 2663). An M row prints one setting or one fact of a process in the trial mode. With `--trace` and N above 0 the program also prints two TR rows. |
| 85 | ` *     TR,-1,0,evict_start,<t_ns> and TR,-1,1,evict_end,<t_ns>.` | Comment: the two TR rows are `TR,-1,0,evict_start,<t_ns>` and `TR,-1,1,evict_end,<t_ns>`. They give the clock times of the start and of the end of these writes, in ns (line 2665). |
| 86 | ` * The line that includes the self-test file is changed by additions only: the` | Comment: the line that includes the self-test file is changed by additions only (lines 3044 to 3049). |
| 87 | ` * old line stands inside "#if 0".` | Comment: the old include line stands inside `#if 0`. So the compiler skips it, and no old line was deleted. |
| 88 | ` * The plan file format is unchanged ("# bwx8-plan v1").` | Comment: the format of the plan file is unchanged. Its first line is still `# bwx8-plan v1` (line 1971). |
| 89 | ` */` | Ends the history comment. |
| 90 | `/* bwx11- */` | Comment: a marker. The block that line 65 opened ends here. |

### History comment of the version `bwx10`: five kernels and two options of the trial mode (lines 91 to 115)

| Line | Source | Explanation |
|---:|---|---|
| 91 | `/* bwx10+ */` | Comment: a marker. A block of text that the version `bwx10` added starts here. The marker of line 115 ends the block. |
| 92 | `/*` | Opens a history comment. It tells what the version of the marker in line 91 added. |
| 93 | ` * bwx10.c - bwx8.c plus the additions of round 3 (2026-11-15). Every addition` | Comment: `bwx10.c` is `bwx8.c` plus the additions of round 3, made on 2026-11-15. Round 3 is a round of work on the program. It is not a round of the option `--rounds`. |
| 94 | ` * stands between a line "bwx10+" and a line "bwx10-" (both are comments).` | Comment: every addition of that round stands between a marker line `bwx10+` and a marker line `bwx10-`. Both marker lines are comments. |
| 95 | ` * Without these blocks, and with the name of the included self-test file set` | Comment: one more change separates `bwx10.c` from `bwx8.c`: the name of the included self-test file (line 3047). |
| 96 | ` * back, this file is bwx8.c byte for byte: test_runner10.py checks it. So the` | Comment: without the blocks, and with that name set back, the text of `bwx10.c` is `bwx8.c`, byte for byte. The script `test_runner10.py` in the code folder `bwx10-2026-11-15` checks this. |
| 97 | ` * 21 kernels of bwx8, call(), timed_sequence() and the interval mode are the` | Comment: so the 21 kernels of `bwx8`, the function `call` (line 1647), the function `timed_sequence` (line 2151) and the interval mode are unchanged. The interval mode is the mode of the option `--seq`. |
| 98 | ` * text of bwx8.c.` | Comment: the end of the sentence of line 97. The parts that it names are the text of `bwx8.c`. |
| 99 | ` *` | Comment: an empty line of the comment. |
| 100 | ` * Additions:` | Comment: the heading of the list of additions. |
| 101 | ` *   kernels read_pf256, read_pf512, read_pf1024, read_pf2048, read_1pl. They` | Comment: five kernels: `read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048` (lines 1010 to 1013) and `read_1pl` (line 1019). |
| 102 | ` *     stand after the last kernel of bwx8 in the source and in kernels[], so` | Comment: in the source and in the kernel table `kernels[]` (lines 1621 to 1622) the five kernels stand after the last kernel of `bwx8`. |
| 103 | ` *     the kernels of bwx8 keep their machine code and their loop offsets.` | Comment: so the kernels of `bwx8` keep their machine code and their loop offsets. A loop offset is the address of the first instruction of a kernel loop, modulo 64. |
| 104 | ` *   --rec-pad BYTES  (trial mode) unused bytes before the win[] array of the` | Comment: the option `--rec-pad BYTES` of the trial mode. It puts that many unused bytes before the array `win[]`, which holds the window records (line 2434). |
| 105 | ` *     record block.` | Comment: the array `win[]` is a part of the record block. That is the one memory block that holds the results of all trials (line 2417). |
| 106 | ` *   --hot-copy       (trial mode) timed_sequence_hot() runs the windows: it` | Comment: the option `--hot-copy` of the trial mode. With it the function `timed_sequence_hot` (line 2212) runs the windows of a trial. |
| 107 | ` *     does not read or write win[i] between the first and the last pass of a` | Comment: between the first pass and the last pass of a window that function does not read or write `win[i]`, the record of the window. |
| 108 | ` *     window.` | Comment: the last word of the sentence of lines 106 to 107. |
| 109 | ` *   M rows rec_pad, hot_copy, rec_addr, win_addr, win_size, stack_addr,` | Comment: new M rows of the trial mode (line 2647): `rec_pad`, `hot_copy`, `rec_addr`, `win_addr`, `win_size` and `stack_addr`. An M row prints one setting or one fact of the process. |
| 110 | ` *     buf_addr, tw_addr.` | Comment: two more new M rows: `buf_addr` and `tw_addr`. |
| 111 | ` *   A pad after the new kernels, so that call() and the code up to the end` | Comment: a pad after the new kernels (lines 1067 to 1070). A pad is a run of unused bytes in the code. In the version `bwx10` it sets the start address of the function `call`. |
| 112 | ` *     of timed_sequence() keep their placement modulo 64.` | Comment: the aim of the pad is that the code from `call` to the end of `timed_sequence` keeps its placement modulo 64. |
| 113 | ` * The plan file format is unchanged ("# bwx8-plan v1").` | Comment: the format of the plan file is unchanged. Its first line is still `# bwx8-plan v1` (line 1971). |
| 114 | ` */` | Ends the history comment. |
| 115 | `/* bwx10- */` | Comment: a marker. The block that line 91 opened ends here. |

### Comment of the version `bwx8`: the two modes and the stand-in kernels (lines 116 to 136)

| Line | Source | Explanation |
|---:|---|---|
| 116 | `/*` | Opens the comment of the version `bwx8`. It is the first version of the runner that has a trial mode. |
| 117 | ` * bwx8.c - scratch copy of bwx.c (crb/tmp/agent-scratch/bwx-2026-11-13) for` | Comment: `bwx8.c` is a scratch copy of `bwx.c`, the first runner. The path in parentheses is the folder of `bwx.c`. In the code repo that folder has the name `bwx-2026-11-13`. |
| 118 | ` * the design crb/new-test-kernel/tackle-8mb.md. The contract with the other` | Comment: the copy was made for the design document `tackle-8mb.md` in the folder `crb/new-test-kernel`. The sentence about the contract continues in line 119. |
| 119 | ` * parts is DECISIONS-bwx8.md in this folder.` | Comment: the contract with the other parts of that work is the file `DECISIONS-bwx8.md`. It fixes the file formats that the parts exchange. The file lies in the code folder `bwx8-2026-11-14`, the folder of `bwx8.c`. |
| 120 | ` *` | Comment: an empty line of the comment. |
| 121 | ` * Two modes:` | Comment: the program has two modes. |
| 122 | ` *   --seq ...    the interval mode of bwx.c. Its code is the text of bwx.c.` | Comment: the option `--seq` selects the interval mode of `bwx.c`. The comment says that the code of this mode is the text of `bwx.c`. `main` runs this mode when no argument is the word `--trial` (lines 3075 to 3077). |
| 123 | ` *   --trial ...  one pinned worker runs the trials of a plan file. A trial is` | Comment: the option `--trial` selects the trial mode. One pinned worker thread runs the trials of a plan file. All code of this mode stands after the function `parse_events` (lines 1927 to 1949). |
| 124 | ` *                previous activity, prefix, predecessor and target windows` | Comment: a trial is a list of windows in four phases: previous activity, prefix, predecessor and target. A window runs one kernel on one range of the buffer for a fixed time. |
| 125 | ` *                with nothing but clock reads between them.` | Comment: between two windows the worker does nothing but read the clock. The code has one more step there: for a trial with the counter state `read` it also reads the counter group and the thread CPU time before each target window (lines 2159 to 2160). |
| 126 | ` *` | Comment: an empty line of the comment. |
| 127 | ` * Everything from "#define _GNU_SOURCE" to the end of parse_events() is the` | Comment: names a range of this file. It reaches from the line `#define _GNU_SOURCE` (line 137) to the end of the function `parse_events` (line 1949). |
| 128 | ` * text of bwx.c, so the kernels, PLACE, call() and alloc_buf() are unchanged.` | Comment: that range is the text of `bwx.c`. So the kernels, the macro `PLACE` (line 194), the function `call` (line 1647) and the function `alloc_buf` (line 465) are unchanged. The later versions put their marked blocks into this range too. |
| 129 | ` * All code of the trial mode stands after it. The build uses` | Comment: all code of the trial mode stands after that range. The sentence about the build continues in line 130. |
| 130 | ` * -fno-toplevel-reorder, so the kernels keep their place in the binary.` | Comment: the build uses the gcc flag `-fno-toplevel-reorder`. With it gcc writes the functions in the order of the source. So the kernels keep their place in the binary. The build record of CRB for `bwx13` holds this flag [Ref2]. |
| 131 | ` *` | Comment: an empty line of the comment. |
| 132 | ` * On AArch64 the kernels are the real ones. On any other machine every NEON` | Comment: on AArch64, the 64-bit Arm instruction set, the kernels are the real ones. The sentence about other machines starts here. |
| 133 | ` * and asm kernel is replaced by a plain C stand-in, so that the harness can` | Comment: on any other machine a plain C loop replaces every NEON kernel and every assembly kernel. The comment calls this loop a stand-in. NEON is the vector part of AArch64. |
| 134 | ` * be run on the development machine. Rates of a stand-in build mean nothing.` | Comment: the stand-ins have one purpose: the program can then run on the development machine. The rates of a build with stand-ins mean nothing. |
| 135 | ` * GB means 1e9 bytes throughout.` | Comment: GB means 1e9 bytes in the whole file. |
| 136 | ` */` | Ends the comment. |

### Includes, constants and the highest CPU that the process may use (lines 137 to 172)

| Line | Source | Explanation |
|---:|---|---|
| 137 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include. It makes the Linux-specific declarations of the C library visible, for example `sched_setaffinity` and `CPU_SET`. |
| 138 | `#ifdef __aarch64__` | Compiles line 139 only when the compiler builds for AArch64, the 64-bit Arm instruction set. gcc defines the macro `__aarch64__` in that case. |
| 139 | `#include <arm_neon.h>` | Includes `arm_neon.h`. It declares the NEON intrinsics, for example `vld1q_u64`. An intrinsic is a C function that maps to one vector instruction. NEON is the vector part of AArch64. |
| 140 | `#endif` | Ends the `#ifdef` of line 138. |
| 141 | `#include <errno.h>` | Includes `errno.h`. It declares `errno`, the error number that a failed library call sets. `parse_long` tests it (lines 387 to 389). |
| 142 | `#include <linux/perf_event.h>` | Includes `linux/perf_event.h`. It declares the structure `perf_event_attr` and the `PERF_FORMAT` constants. `open_counters` (line 1738) opens the hardware counters with them. |
| 143 | `#include <pthread.h>` | Includes `pthread.h`. It declares the thread functions `pthread_create` and `pthread_join` and the barrier function `pthread_barrier_wait`. |
| 144 | `#include <sched.h>` | Includes `sched.h`. It declares the CPU set type `cpu_set_t` and the calls `sched_getaffinity` and `sched_setaffinity`. They read and set the CPUs on which Linux may run a thread. |
| 145 | `#include <setjmp.h>` | Includes `setjmp.h`. It declares `sigsetjmp` and `siglongjmp`. No other line of this file uses them. The self-test file that this file includes uses them. |
| 146 | `#include <signal.h>` | Includes `signal.h`. It declares `sigaction` and the signal numbers. No other line of this file uses them. The included self-test file uses them to catch `SIGSEGV`, the signal that Linux sends at a forbidden memory access. |
| 147 | `#include <stdatomic.h>` | Includes `stdatomic.h`. It declares the atomic types and the functions `atomic_load`, `atomic_store` and `atomic_fetch_add`. The three variables of the common start use them (lines 354 to 356). |
| 148 | `#include <stdint.h>` | Includes `stdint.h`. It declares the integer types of fixed size, for example `uint64_t` (64 bits, without a sign) and `int64_t` (64 bits, with a sign). |
| 149 | `#include <stdio.h>` | Includes `stdio.h`. It declares the input and output functions, for example `printf`, `fprintf`, `fopen` and `fgets`. |
| 150 | `#include <stdlib.h>` | Includes `stdlib.h`. It declares `exit`, `strtol`, `strtod`, `calloc` and `getenv`. |
| 151 | `#include <string.h>` | Includes `string.h`. It declares the text and memory functions, for example `strcmp`, `strtok`, `memset` and `strerror`. |
| 152 | `#include <sys/mman.h>` | Includes `sys/mman.h`. It declares `mmap`, `mprotect` and `madvise`. `alloc_buf` (line 465) uses them for the buffers. |
| 153 | `#include <sys/syscall.h>` | Includes `sys/syscall.h`. It declares the numbers of the system calls, here `SYS_perf_event_open`. `open_counters` passes this number to `syscall` (line 1751). |
| 154 | `#include <time.h>` | Includes `time.h`. It declares `clock_gettime` and the structure `timespec`. `now_ns` (line 358) reads the clock with them. |
| 155 | `#include <unistd.h>` | Includes `unistd.h`. It declares `sysconf`, `getpid` and `read`. |
| 157 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2097152 bytes (2 MiB), the size of one huge page. The expression is 2 shifted left by 20 bits. Every buffer starts at a multiple of this value (line 473). |
| 158 | `#define MAX_CPUS 1024` | `MAX_CPUS`: the `--cpus` list may hold at most 1024 CPUs (line 437). |
| 159 | `#define MAX_SEQ 64` | `MAX_SEQ`: the `--seq` list may hold at most 64 kernels (line 1915). |
| 160 | `#define MAX_EV 8` | `MAX_EV`: the `--events` list may hold at most 8 counter events (line 1932). |
| 161 | `#define CHECK_BYTES (8UL << 20) /* --stop pass: clock is read after at least this many bytes */` | `CHECK_BYTES`: 8388608 bytes (8 MiB). Comment: with `--stop pass` a thread reads the clock after at least this many bytes. For some sizes the code reads the clock earlier. The number of whole passes between two clock reads is this value divided by the size of the range, rounded down, and at least 1 (lines 1860 to 1862). So with a range of 3 MiB the thread reads the clock after 2 passes, which are 6 MiB. The trial mode computes its passes in the same way (line 2404). |
| 162 | `#define CHUNK_BYTES HUGE_BYTES  /* --stop common: clock is read after each chunk of this size */` | `CHUNK_BYTES`: the value of `HUGE_BYTES`, 2097152 bytes (2 MiB). It is the size of a chunk. Comment: with `--stop common` a worker calls the kernel on one chunk and then reads the clock (lines 1849 to 1856). When the range of a `--seq` entry is below 2 MiB, the chunk is that whole range (line 1849). |
| 163 | `#define LEAD_NS 2000000L        /* --stop common: the common start is this long after the barrier */` | `LEAD_NS`: 2000000 ns (2 ms). With `--stop common` the main thread reads the clock after its barrier wait and sets the common start time of an interval to that clock value plus 2 ms (lines 3220 to 3222). The release at the barrier is not the start of the timed interval. Each worker waits until the clock reaches the common start time (line 1837). Then it starts its timed interval with its own clock read `t0` (line 1844). |
| 164 | `#define LATE_NS 100000L         /* --stop common: flag "late" if a thread starts later than this */` | `LATE_NS`: 100000 ns (100 us, which is 0.1 ms). With `--stop common` a thread gets the flag `late` when its start clock read is more than this after the common start (line 1881). |
| 165 | `/* Highest CPU that the process may use. Rule of the test machine: CPUs 0 to` | Comment: the macro below gives the highest CPU number that the process may use. The rule of the test machine starts here: only the CPUs 0 to 119. |
| 166 | ` * 119 only, never 126 or 127. main() removes every higher CPU from the` | Comment: the end of the rule: never CPU 126 or CPU 127. `main` calls `restrict_cpus` (line 3074), which removes every higher CPU from the set of CPUs that Linux may use for the process. |
| 167 | ` * allowed set of the process, and --cpus rejects one. Another machine can` | Comment: the option `--cpus` also rejects a higher CPU (line 432). |
| 168 | ` * build with -DMAX_USE_CPU=N. */` | Comment: for another machine the build can set another limit with the compiler option `-DMAX_USE_CPU=N`. |
| 169 | `#ifndef MAX_USE_CPU` | Tests whether the build command has already defined `MAX_USE_CPU`. Only if not, line 170 is compiled. `restrict_cpus` (line 399) and `parse_cpus` (line 419) apply the limit. |
| 170 | `#define MAX_USE_CPU 119` | The default value: the highest CPU that the process may use is CPU 119. The CRB build of `bwx13` gave no `-D` option, so this value was used [Ref2]. |
| 171 | `#endif` | Ends the `#ifndef` of line 169. |

### Loop placement: the macros `PLACE` and `PADOF` (lines 173 to 196)

| Line | Source | Explanation |
|---:|---|---|
| 173 | `/*` | Opens the comment about the placement of the kernel loops. |
| 174 | ` * Loop placement (handoff B.7). PLACE(name) stands directly before kernel` | Comment: the topic is the loop placement. The aim is that the loop of each kernel starts at a known address modulo 64, the loop offset. Section B.7 of the file `handoff.md`, the specification of the first runner, treats this offset as a test factor [Ref5]. The macro `PLACE(name)` stands directly before the kernel function. |
| 175 | ` * k_<name>. It pads .text to a 64 B boundary and then adds PAD_<name> zero bytes,` | Comment: the kernel function has the name `k_` plus the kernel name. `PLACE` first pads the code section `.text` to a 64 B boundary. Then it adds zero bytes. The macro `PAD_` plus the kernel name gives their number. |
| 176 | ` * so the function starts at PAD_<name> modulo 64. This needs the gcc flags` | Comment: so the function starts at that pad value modulo 64. The method needs two gcc flags. |
| 177 | ` * -fno-toplevel-reorder -falign-functions=4, and PAD must be a multiple of 4.` | Comment: the two flags are `-fno-toplevel-reorder` and `-falign-functions=4`. A pad must be a multiple of 4. Both flags are in the build record of CRB for `bwx13` [Ref2]. |
| 178 | ` *` | Comment: an empty line of the comment. |
| 179 | ` * For a kernel with a planned loop offset, PAD = (LOOP - HEAD) mod 64. LOOP` | Comment: the rule for a kernel with a planned loop offset: the pad is `(LOOP - HEAD) mod 64`. |
| 180 | ` * is the planned offset of the loop start modulo 64. HEAD is the number of` | Comment: `LOOP` is the planned offset of the loop start, modulo 64. `HEAD` is a number of bytes. |
| 181 | ` * bytes between the function start and the loop start: 4 or 20 in the` | Comment: `HEAD` counts the bytes of code between the start of the function and the start of its loop. The comment gives the values 4 and 20. |
| 182 | ` * listings of bw_new (results/kernels-20261113T181222Z/probe.txt). HEAD is a` | Comment: these two values come from the listings of the binary `bw_new` in the file `probe.txt` of the result folder `kernels-20261113T181222Z`. `bw_new` is the benchmark binary of 2026-11-13 with the new kernels. In that file the loop of `k_copy` starts 4 bytes after the function start, and the loop of `k_asmcopy` 20 bytes after it [Ref3]. |
| 183 | ` * guess until the objdump listing of the CRB build confirms it: override it` | Comment: a `HEAD` value is a guess until the machine-code listing of the CRB build confirms it. |
| 184 | ` * with -DHEAD_<name>=N, or the whole pad with -DPAD_<name>=N.` | Comment: the build can replace one `HEAD` value with `-DHEAD_<name>=N`, or a whole pad with `-DPAD_<name>=N`. The CRB build of `bwx13` used no `-D` option [Ref2]. |
| 185 | ` * -DB3_OFFSET=0\|36\|52 puts the loops of copy, asmcopy and asmcopy2 at that` | Comment: the build option `-DB3_OFFSET=0`, `-DB3_OFFSET=36` or `-DB3_OFFSET=52` moves the loops of the kernels `copy`, `asmcopy` and `asmcopy2`. |
| 186 | ` * offset (step B3).` | Comment: these loops then start at that offset modulo 64 (lines 197 to 199). The option belongs to step B3 of the test plan of the first runner. |
| 187 | ` *` | Comment: an empty line of the comment. |
| 188 | ` * For the other kernels the default PAD is the start offset modulo 64 that` | Comment: the rule for every other kernel: the default pad is a start offset modulo 64 that the function has in an older binary. |
| 189 | ` * the function has in bw_new (new C and asm kernels) or in bw_old (old` | Comment: for a new C kernel or an assembly kernel the older binary is `bw_new`. For an old kernel it is `bw_old`. The old read kernel and the new read kernel show the result. The loop of `k_read` starts at 36 modulo 64 in the CRB build of `bwx13` and in `bw_new`. The loop of `k_oldread` in `bwx13` and the loop of `k_read` in `bw_old` both start at 40 modulo 64 [Ref1] [Ref3]. |
| 190 | ` * kernels). An A/A copy takes the PAD of its original.` | Comment: an A/A copy takes the pad of its original. An A/A copy is the same kernel source under a second name, for example `asmread2`. |
| 191 | ` */` | Ends the comment. |
| 192 | `#define STR2(x) #x` | `STR2(x)` turns its argument into a text in quotes. The preprocessor operator `#` does that. |
| 193 | `#define STR(x) STR2(x)` | `STR(x)` first replaces `x` by its value when `x` is a macro. Then it calls `STR2`. So with the default value 32 of `PAD_read`, `STR(PAD_read)` gives the text `"32"` and not the name in quotes. |
| 194 | `#define PLACE(name) __asm__(".pushsection .text\n.p2align 6\n.fill " STR(PAD_##name) ", 1, 0\n.popsection\n")` | `PLACE(name)` writes an `__asm__` statement outside of a function. gcc passes its text to the assembler without a change. `.pushsection .text` continues in the code section. `.p2align 6` pads the code up to an address that is a multiple of 64. `.fill N, 1, 0` adds N bytes of value 0. N is the value of the macro whose name `PAD_##name` builds from `PAD_` and the argument. `.popsection` returns to the section that was in use before. So the function that follows starts at N modulo 64. |
| 195 | `#define PADOF(loop, head) (((loop) - (head)) & 63)` | `PADOF(loop, head)`: `loop` minus `head`, modulo 64. The operation `& 63` keeps the low 6 bits. So a negative difference also gives a value from 0 to 63. |

### Planned loop offsets, head sizes and pads of the first kernels (lines 197 to 283)

| Line | Source | Explanation |
|---:|---|---|
| 197 | `#ifdef B3_OFFSET` | Tests whether the build command defined `B3_OFFSET`. The CRB build of `bwx13` did not, so the `#else` branch of lines 200 to 202 was compiled [Ref2]. |
| 198 | `#define LOOP_copy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_copy`, the planned loop offset of the kernel `copy`, is N. |
| 199 | `#define LOOP_asmcopy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_asmcopy`, the planned loop offset of the kernel `asmcopy`, is N too. |
| 200 | `#else` | Starts the branch for a build without `B3_OFFSET`. |
| 201 | `#define LOOP_copy 36` | `LOOP_copy`: the loop of the kernel `copy` must start at 36 modulo 64. In the CRB binary of `bwx13` the loop of `k_copy` starts at `0x4b64`, which is 36 modulo 64 [Ref1]. |
| 202 | `#define LOOP_asmcopy 52` | `LOOP_asmcopy`: the loop of the kernel `asmcopy` must start at 52 modulo 64. In the CRB binary of `bwx13` the loop of `k_asmcopy` starts at `0x5134`, which is 52 modulo 64 [Ref1]. |
| 203 | `#endif` | Ends the `#ifdef` of line 197. |
| 204 | `#define LOOP_asmcopy_c 52` | `LOOP_asmcopy_c`: 52 modulo 64, the planned loop offset of the three kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg` (lines 229 to 237). `B3_OFFSET` does not change it. |
| 205 | `#ifndef HEAD_copy` | Compiles line 206 only when the build command has not defined `HEAD_copy`. Every value up to line 282 has this pattern of three lines: a default that a `-D` option of the build can replace. |
| 206 | `#define HEAD_copy 4` | `HEAD_copy`: 4 bytes of code, which is one instruction, stand between the start of `k_copy` and the start of its loop. The listing of the CRB build of `bwx13` shows this distance [Ref1]. |
| 207 | `#endif` | Ends the `#ifndef` of line 205. |
| 208 | `#ifndef HEAD_asmcopy` | Compiles line 209 only when the build command has not defined `HEAD_asmcopy`. |
| 209 | `#define HEAD_asmcopy 20` | `HEAD_asmcopy`: 20 bytes of code, which are 5 instructions, stand before the loop of `k_asmcopy`. The listing of the CRB build of `bwx13` shows them: 4 `stp` instructions that save the registers `d8` to `d15`, and the `add` that computes the end address [Ref1]. |
| 210 | `#endif` | Ends the `#ifndef` of line 208. |
| 211 | `#ifndef HEAD_asmcopy_c` | Compiles line 212 only when the build command has not defined `HEAD_asmcopy_c`. |
| 212 | `#define HEAD_asmcopy_c 4` | `HEAD_asmcopy_c`: 4 bytes of code stand before the loop of `k_asmcopy_c`. The listing of the CRB build of `bwx13` shows this distance [Ref1]. |
| 213 | `#endif` | Ends the `#ifndef` of line 211. |
| 214 | `#ifndef HEAD_asmcopy_c_add` | Compiles line 215 only when the build command has not defined `HEAD_asmcopy_c_add`. |
| 215 | `#define HEAD_asmcopy_c_add 4` | `HEAD_asmcopy_c_add`: 4 bytes of code stand before the loop of `k_asmcopy_c_add`. The listing of the CRB build of `bwx13` shows this distance [Ref1]. |
| 216 | `#endif` | Ends the `#ifndef` of line 214. |
| 217 | `#ifndef HEAD_asmcopy_c_reg` | Compiles line 218 only when the build command has not defined `HEAD_asmcopy_c_reg`. |
| 218 | `#define HEAD_asmcopy_c_reg 20` | `HEAD_asmcopy_c_reg`: 20 bytes of code stand before the loop of `k_asmcopy_c_reg`. This kernel saves `d8` to `d15`, as `asmcopy` does. The listing of the CRB build of `bwx13` shows this distance [Ref1]. |
| 219 | `#endif` | Ends the `#ifndef` of line 217. |
| 220 | `#ifndef PAD_copy` | Compiles line 221 only when the build command has not defined `PAD_copy`. |
| 221 | `#define PAD_copy PADOF(LOOP_copy, HEAD_copy)` | `PAD_copy`: `PADOF` (line 195) computes it from the two values above. With the defaults it is (36 - 4) modulo 64 = 32 bytes. In the CRB binary of `bwx13` the function `k_copy` starts at `0x4b60`, which is 32 modulo 64 [Ref1]. |
| 222 | `#endif` | Ends the `#ifndef` of line 220. |
| 223 | `#ifndef PAD_asmcopy` | Compiles line 224 only when the build command has not defined `PAD_asmcopy`. |
| 224 | `#define PAD_asmcopy PADOF(LOOP_asmcopy, HEAD_asmcopy)` | `PAD_asmcopy`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx13` the function `k_asmcopy` starts at `0x5120`, which is 32 modulo 64 [Ref1]. |
| 225 | `#endif` | Ends the `#ifndef` of line 223. |
| 226 | `#ifndef PAD_asmcopy2` | Compiles line 227 only when the build command has not defined `PAD_asmcopy2`. |
| 227 | `#define PAD_asmcopy2 PAD_asmcopy` | `PAD_asmcopy2`: the A/A copy `asmcopy2` takes the pad of its original `asmcopy`. With the defaults that is 32 bytes. |
| 228 | `#endif` | Ends the `#ifndef` of line 226. |
| 229 | `#ifndef PAD_asmcopy_c` | Compiles line 230 only when the build command has not defined `PAD_asmcopy_c`. |
| 230 | `#define PAD_asmcopy_c PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c)` | `PAD_asmcopy_c`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx13` the function `k_asmcopy_c` starts at `0x52b0`, which is 48 modulo 64 [Ref1]. |
| 231 | `#endif` | Ends the `#ifndef` of line 229. |
| 232 | `#ifndef PAD_asmcopy_c_add` | Compiles line 233 only when the build command has not defined `PAD_asmcopy_c_add`. |
| 233 | `#define PAD_asmcopy_c_add PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_add)` | `PAD_asmcopy_c_add`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx13` the function `k_asmcopy_c_add` starts at `0x5370`, which is 48 modulo 64 [Ref1]. |
| 234 | `#endif` | Ends the `#ifndef` of line 232. |
| 235 | `#ifndef PAD_asmcopy_c_reg` | Compiles line 236 only when the build command has not defined `PAD_asmcopy_c_reg`. |
| 236 | `#define PAD_asmcopy_c_reg PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_reg)` | `PAD_asmcopy_c_reg`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx13` the function `k_asmcopy_c_reg` starts at `0x5420`, which is 32 modulo 64 [Ref1]. |
| 237 | `#endif` | Ends the `#ifndef` of line 235. |
| 238 | `#ifndef PAD_read` | Compiles line 239 only when the build command has not defined `PAD_read`. |
| 239 | `#define PAD_read 32` | `PAD_read` = 32: the new read kernel `k_read` starts at 32 modulo 64. In the CRB binary of `bwx13` it starts at the address `0x4aa0`, which is 32 modulo 64 [Ref1]. |
| 240 | `#endif` | Ends the `#ifndef` of line 238. |
| 241 | `#ifndef PAD_write` | Compiles line 242 only when the build command has not defined `PAD_write`. |
| 242 | `#define PAD_write 0` | `PAD_write` = 0: `k_write`, the function of the first touch, starts at 0 modulo 64. In the CRB binary of `bwx13` it starts at the address `0x4b00` [Ref1]. |
| 243 | `#endif` | Ends the `#ifndef` of line 241. |
| 244 | `#ifndef PAD_asmread` | Compiles line 245 only when the build command has not defined `PAD_asmread`. |
| 245 | `#define PAD_asmread 0` | `PAD_asmread` = 0: `k_asmread` starts at 0 modulo 64. In the CRB binary of `bwx13` it starts at the address `0x4bc0` [Ref1]. |
| 246 | `#endif` | Ends the `#ifndef` of line 244. |
| 247 | `#ifndef PAD_asmread2` | Compiles line 248 only when the build command has not defined `PAD_asmread2`. |
| 248 | `#define PAD_asmread2 PAD_asmread` | `PAD_asmread2`: the A/A copy `asmread2` takes the pad of `asmread`, which is 0 bytes. |
| 249 | `#endif` | Ends the `#ifndef` of line 247. |
| 250 | `#ifndef PAD_asmwrite` | Compiles line 251 only when the build command has not defined `PAD_asmwrite`. |
| 251 | `#define PAD_asmwrite 32` | `PAD_asmwrite` = 32: `k_asmwrite` starts at 32 modulo 64. |
| 252 | `#endif` | Ends the `#ifndef` of line 250. |
| 253 | `#ifndef PAD_asmwrite2` | Compiles line 254 only when the build command has not defined `PAD_asmwrite2`. |
| 254 | `#define PAD_asmwrite2 PAD_asmwrite` | `PAD_asmwrite2`: the A/A copy `asmwrite2` takes the pad of `asmwrite`, which is 32 bytes. |
| 255 | `#endif` | Ends the `#ifndef` of line 253. |
| 256 | `#ifndef PAD_oldread` | Compiles line 257 only when the build command has not defined `PAD_oldread`. |
| 257 | `#define PAD_oldread 0` | `PAD_oldread` = 0: the old read kernel `k_oldread` starts at 0 modulo 64. In the CRB binary of `bwx13` it starts at the address `0x4700` [Ref1]. |
| 258 | `#endif` | Ends the `#ifndef` of line 256. |
| 259 | `#ifndef PAD_oldread2` | Compiles line 260 only when the build command has not defined `PAD_oldread2`. |
| 260 | `#define PAD_oldread2 PAD_oldread` | `PAD_oldread2`: the A/A copy `oldread2` takes the pad of `oldread`, which is 0 bytes. |
| 261 | `#endif` | Ends the `#ifndef` of line 259. |
| 262 | `#ifndef PAD_oldwrite` | Compiles line 263 only when the build command has not defined `PAD_oldwrite`. |
| 263 | `#define PAD_oldwrite 32` | `PAD_oldwrite` = 32: `k_oldwrite` starts at 32 modulo 64. |
| 264 | `#endif` | Ends the `#ifndef` of line 262. |
| 265 | `#ifndef PAD_oldcopy` | Compiles line 266 only when the build command has not defined `PAD_oldcopy`. |
| 266 | `#define PAD_oldcopy 32` | `PAD_oldcopy` = 32: `k_oldcopy` starts at 32 modulo 64. |
| 267 | `#endif` | Ends the `#ifndef` of line 265. |
| 268 | `#ifndef PAD_read_nop4` | Compiles line 269 only when the build command has not defined `PAD_read_nop4`. |
| 269 | `#define PAD_read_nop4 PAD_asmread` | `PAD_read_nop4`: the kernel `read_nop4` takes the pad of `asmread`, which is 0 bytes. |
| 270 | `#endif` | Ends the `#ifndef` of line 268. |
| 271 | `#ifndef PAD_read_nop8` | Compiles line 272 only when the build command has not defined `PAD_read_nop8`. |
| 272 | `#define PAD_read_nop8 PAD_asmread` | `PAD_read_nop8`: the kernel `read_nop8` takes the pad of `asmread`, which is 0 bytes. |
| 273 | `#endif` | Ends the `#ifndef` of line 271. |
| 274 | `#ifndef PAD_read_nop16` | Compiles line 275 only when the build command has not defined `PAD_read_nop16`. |
| 275 | `#define PAD_read_nop16 PAD_asmread` | `PAD_read_nop16`: the kernel `read_nop16` takes the pad of `asmread`, which is 0 bytes. |
| 276 | `#endif` | Ends the `#ifndef` of line 274. |
| 277 | `#ifndef PAD_read_nop32` | Compiles line 278 only when the build command has not defined `PAD_read_nop32`. |
| 278 | `#define PAD_read_nop32 PAD_asmread` | `PAD_read_nop32`: the kernel `read_nop32` takes the pad of `asmread`, which is 0 bytes. |
| 279 | `#endif` | Ends the `#ifndef` of line 277. |
| 280 | `#ifndef PAD_read_sparse` | Compiles line 281 only when the build command has not defined `PAD_read_sparse`. |
| 281 | `#define PAD_read_sparse PAD_asmread` | `PAD_read_sparse`: the kernel `read_sparse` takes the pad of `asmread`, which is 0 bytes. |
| 282 | `#endif` | Ends the `#ifndef` of line 280. |

### Kernel types and one entry of the `--seq` list (lines 284 to 294)

| Line | Source | Explanation |
|---:|---|---|
| 284 | `enum ktype { T_READ, T_WRITE, T_COPY, T_OLDREAD };` | `enum ktype`: the four kernel types `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD`. The function `call` (line 1647) chooses the argument list of a kernel by its type. |
| 285 | `typedef void (*read_fn)(const uint64_t *, size_t);` | `read_fn`: the function type of a read kernel (type `T_READ`). The kernel gets the start address and the number of 8-byte words. It returns nothing. |
| 286 | `typedef uint64_t (*oldread_fn)(const uint64_t *, size_t);` | `oldread_fn`: the function type of an old read kernel (type `T_OLDREAD`). The kernel gets the same two arguments and returns a 64-bit sum. |
| 287 | `typedef void (*write_fn)(uint64_t *, size_t, uint64_t);` | `write_fn`: the function type of a write kernel (type `T_WRITE`). The kernel gets the start address, the number of 8-byte words and the 64-bit value to store. |
| 288 | `typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);` | `copy_fn`: the function type of a copy kernel (type `T_COPY`). The kernel gets the destination address, the source address and the number of 8-byte words. `restrict` tells the compiler that the two ranges do not overlap. |
| 290 | `struct entry {` | Starts `struct entry`: one entry of the `--seq` list. |
| 291 | `    int k;          /* index into kernels[] */` | `k`: the index of the kernel in the kernel table `kernels[]` (line 1611). |
| 292 | `    uint64_t bytes; /* 0 until main() replaces it by --bytes */` | `bytes`: the size of the range that the kernel works on, in bytes. It is 0 when the entry has no `@SIZE` part. `main` then sets it to the `--bytes` value (lines 3152 to 3153). |
| 293 | `};` | Ends `struct entry`. |

### The settings structure `cfg` (lines 295 to 314)

| Line | Source | Explanation |
|---:|---|---|
| 295 | `static struct {` | Starts the structure `cfg`. It holds the settings of the process. The code that reads the arguments fills it. |
| 296 | `    int threads;` | `threads`: the number of worker threads (`--threads`). |
| 297 | `    int ncpus;` | `ncpus`: the number of entries of `cpus`. |
| 298 | `    int cpus[MAX_CPUS];` | `cpus`: the CPU list of `--cpus`, in the order of the list. `parse_cpus` (line 419) fills it. |
| 299 | `    uint64_t bytes;` | `bytes`: the value of `--bytes` in bytes. It is the range of each buffer that the program uses: the first touch writes this many bytes (line 1802), and no `--seq` entry may be larger (line 3154). The mapped buffer is this value rounded up to a multiple of 2 MiB (line 459). |
| 300 | `    double min_s;` | `min_s`: the `--min-ms` value in seconds. With `--stop common` the deadline of an interval is this long after its common start (line 3224). With `--stop pass` a thread runs at least this long (line 1871). |
| 301 | `    int use_thp;` | `use_thp`: 1 when the program asks Linux for 2 MiB pages (transparent huge pages) for the buffers. The option `--no-thp` sets it to 0. |
| 302 | `    struct entry seq[MAX_SEQ];` | `seq`: the kernel list of `--seq`, one `struct entry` per kernel. |
| 303 | `    int nseq;` | `nseq`: the number of entries of `seq`. |
| 304 | `    int rounds;` | `rounds`: how many times the list runs (`--rounds`). |
| 305 | `    int stop_common;  /* --stop common */` | `stop_common`: 1 with `--stop common`. With this stop rule all threads of an interval get the same deadline. |
| 306 | `    int start_offset; /* --start offset */` | `start_offset`: 1 with `--start offset`. Then the place in its buffer at which a thread starts an interval depends on the number of the thread (line 1818). The option chooses a place in the buffer. It does not set the start time of an interval. |
| 307 | `    int two_buffers;  /* buffer b exists: --two-buffers, or a copy kernel in the sequence */` | `two_buffers`: 1 when each thread has a second buffer `b`. The option `--two-buffers` sets it. `main` also sets it when the list holds a copy kernel (lines 3159 to 3160). |
| 308 | `    int count;        /* --count */` | `count`: 1 with `--count`. Then each thread opens hardware counters and reads them before and after each interval. |
| 309 | `    long pmu_type;    /* --pmu-type: the "type" field of perf_event_attr */` | `pmu_type`: the value of `--pmu-type`. It goes into the field `type` of the structure `perf_event_attr` (line 1745). The field tells Linux which counter hardware to use. |
| 310 | `    int nev;` | `nev`: the number of counter events of `--events`. |
| 311 | `    char ev_name[MAX_EV][32];` | `ev_name`: the names of the events, at most 31 characters each. |
| 312 | `    uint64_t ev_code[MAX_EV];` | `ev_code`: the codes of the events. A code goes into the field `config` of `perf_event_attr` (line 1747). |
| 313 | `} cfg = { .threads = 1, .min_s = 0.5, .use_thp = 1, .rounds = 1, .pmu_type = -1 };` | Ends the structure and sets the defaults: 1 thread, 0.5 s per interval, a request for 2 MiB pages, 1 round and no PMU type (the value -1). Every other field starts at 0. |

### Structures `page`, `counts`, `result` and `thread` (lines 315 to 346)

| Line | Source | Explanation |
|---:|---|---|
| 315 | `struct page {` | Starts `struct page`: the page state of one buffer. |
| 316 | `    long kb_total, kb_huge; /* -1: no exact entry in /proc/self/smaps */` | `kb_total`: the size of the mapping of the buffer. `kb_huge`: the part of it that lies on 2 MiB pages. Both are in kB (1 kB is 1024 bytes here). `read_smaps` (line 1671) fills them. Comment: -1 means that the Linux file `/proc/self/smaps` has no exact entry for the buffer. Such a value is printed as `NA`. |
| 317 | `};` | Ends `struct page`. |
| 319 | `struct counts {` | Starts `struct counts`: one reading of the counters of a thread. |
| 320 | `    uint64_t cpu_ns;              /* CLOCK_THREAD_CPUTIME_ID */` | `cpu_ns`: the CPU time that the thread has used, in ns. The Linux clock `CLOCK_THREAD_CPUTIME_ID` gives it (line 1768). |
| 321 | `    uint64_t enabled, running;    /* of the counter group */` | `enabled` and `running`: two times of the counter group in ns. They say how long the counters were enabled and how long they really counted. |
| 322 | `    uint64_t val[MAX_EV];` | `val`: one count per event that opened. |
| 323 | `};` | Ends `struct counts`. |
| 325 | `/* One thread, one interval. Written by the worker between the start barrier` | Comment: the structure below holds the result of one thread for one interval. The worker writes it after the start barrier of the interval. The start barrier is the barrier wait that stands before the timed interval (line 1831). The timed interval of a thread does not start at this barrier. It starts later, at the clock read `t0` of the thread (line 1844). |
| 326 | ` * and the end barrier of the interval; read by main() after the end barrier. */` | Comment: the worker writes it before the end barrier of the interval, and `main` reads it after that barrier. In the code the worker stores the structure at line 1882, before its barrier wait of line 1883. `main` reads it after its barrier wait of line 3227. So the two threads never use it at the same time. |
| 327 | `struct result {` | Starts `struct result`. |
| 328 | `    uint64_t bytes;` | `bytes`: the bytes that the thread counted in the interval (line 1877). |
| 329 | `    int64_t t_sched, t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_sched`: the common start time. `t_start`: the start clock read `t0` of the thread. `t_end`: its last clock read `t1`. All three are values of the clock `CLOCK_MONOTONIC` in ns (lines 1878 to 1880). With `--stop pass` there is no common start, and `t_sched` gets the value of `t0`. |
| 330 | `    int late;` | `late`: the late flag. It is 1 when `t0` of the thread was more than `LATE_NS` after the common start (line 1881). |
| 331 | `    struct page pg[2]; /* one-thread process only: read by the worker before the interval */` | `pg`: the page state of the buffers `a` and `b`. Comment: only a process with one thread uses it. There the worker reads the page state before the interval (lines 1826 to 1830). |
| 332 | `    long long vm[4];` | `vm`: four counters of the Linux file `/proc/vmstat` (line 1701). As for `pg`, only the worker of a process with one thread fills it. |
| 333 | `    struct counts c0, c1;` | `c0` and `c1`: the counter readings before `t0` (lines 1841 to 1842) and after the last `t1` (lines 1874 to 1875). |
| 334 | `};` | Ends `struct result`. |
| 336 | `struct thread {` | Starts `struct thread`: one record per worker. |
| 337 | `    int idx;` | `idx`: the number of the thread, counted from 0 (line 3173). |
| 338 | `    int cpu;` | `cpu`: the CPU that the thread pins itself to, or -1 without `--cpus` (line 3174). |
| 339 | `    uint64_t *a, *b;` | `a`: the buffer of the thread. `b`: the second buffer, which only a copy kernel or `--two-buffers` needs. Without it `b` stays `NULL`. |
| 340 | `    int group_fd;      /* leader of the counter group, -1 if no event opened */` | `group_fd`: the file descriptor of the leader of the counter group. A file descriptor is the number that Linux returns for an open object. Comment: it is -1 when no event opened. `open_counters` (line 1738) sets it. |
| 341 | `    int ev_pos[MAX_EV]; /* position of the event in the group read, -1 if it did not open */` | `ev_pos`: for each event its position among the values of a group read. Comment: -1 when the event did not open. |
| 342 | `    int nopen;` | `nopen`: the number of events that opened. |
| 343 | `    struct result res;` | `res`: the result of the last interval of this thread. |
| 344 | `    pthread_t tid;` | `tid`: the thread handle that `pthread_create` returns (line 3175). |
| 345 | `};` | Ends `struct thread`. |

### Global variables: the barrier, the base time and the common start (lines 347 to 357)

| Line | Source | Explanation |
|---:|---|---|
| 347 | `static pthread_barrier_t bar;` | `bar`: the barrier. A thread that calls `pthread_barrier_wait` on it blocks until all workers and the main thread have called it. `main` creates it for the number of workers plus 1 (line 3168). |
| 348 | `static int64_t t_base_ns; /* clock at process start: printed times are relative to it */` | `t_base_ns`: the clock value at the process start (line 3071). Comment: the printed times are relative to it. |
| 349 | `static long page_bytes;` | `page_bytes`: the page size that Linux reports, in bytes (line 3072). `alloc_buf` uses it (line 473). |
| 351 | `/* --stop common (handoff B.4). gen only grows. main() stores the two times` | Comment: the three variables below belong to `--stop common`. The comment cites section B.4 of the file `handoff.md`, the specification of the first runner. `gen` only grows. |
| 352 | ` * before it increments gen, so a worker that sees the new gen reads the new` | Comment: `main` stores the two times before it adds 1 to `gen` (lines 3223 to 3225). A worker first waits for the new value of `gen` (line 1833). |
| 353 | ` * times. */` | Comment: then the worker loads the two times (lines 1835 to 1836). So it never uses the times of the interval before. |
| 354 | `static _Atomic uint64_t gen;` | `gen`: an atomic counter of intervals. It starts at 0. `_Atomic` makes every load and every store of the variable one indivisible step. |
| 355 | `static _Atomic int64_t t_sched_ns;` | `t_sched_ns`: the common start time of the coming interval, as a value of the clock `CLOCK_MONOTONIC` in ns. With `--stop common` every worker waits until the clock reaches this time (line 1837). The timed interval of a worker starts after that, at its own clock read `t0` (line 1844). |
| 356 | `static _Atomic int64_t deadline_ns;` | `deadline_ns`: the common deadline of the coming interval: the common start time plus the `--min-ms` value (line 3224). With `--stop common` a worker ends its timed interval at its first clock read `t1` at or after this deadline (lines 1856 to 1857). So each worker finishes the chunk that it is in. |

### Function `now_ns`: read the clock (lines 358 to 364)

| Line | Source | Explanation |
|---:|---|---|
| 358 | `static int64_t now_ns(void)` | Starts the function `now_ns`. It reads the clock and returns the time in ns. Every time stamp of the program comes from this function. In a timed interval the worker calls it once for the start `t0` (line 1844). With `--stop common` it then calls it once after each chunk for `t1` (line 1856). A chunk is 2 MiB, or the whole range of the `--seq` entry when that is smaller. So one clock read per chunk is inside the timed interval. This is the same for every kernel. |
| 359 | `{` | Opens the body of `now_ns`. |
| 360 | `    struct timespec ts;` | `ts`: a `timespec`, the structure for a time as whole seconds plus ns. |
| 361 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | `clock_gettime` reads the Linux clock `CLOCK_MONOTONIC` into `ts`. This clock cannot be set. It does not jump when the date or the time of the system is changed. |
| 362 | `    return (int64_t)ts.tv_sec * 1000000000L + ts.tv_nsec;` | Returns the seconds times 1000000000 plus the ns part: the time in ns as one 64-bit number. |
| 363 | `}` | Ends the function `now_ns`. |

### Function `parse_bytes`: a size text such as `256M` (lines 365 to 381)

| Line | Source | Explanation |
|---:|---|---|
| 365 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `256M` into a number of bytes. `main` calls it for `--bytes` (line 3100). `parse_seq` calls it for the `@SIZE` part of a `--seq` entry (line 1920). |
| 366 | `{` | Opens the body of `parse_bytes`. |
| 367 | `    char *end;` | `end`: `strtod` sets it to the first character after the number. |
| 368 | `    double v = strtod(s, &end);` | `strtod` reads a decimal number from the start of the text into `v`. The number may have a fraction, for example `1.5`. |
| 369 | `    double mul = 1;` | `mul`: the factor of the unit letter. It stays 1 when no letter follows the number. |
| 370 | `    switch (*end) {` | Looks at the character after the number. |
| 371 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | The letter `k` or `K`: the factor is 1024. `end++` moves `end` to the character after the letter. |
| 372 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | The letter `m` or `M`: the factor is 1048576, which is 1 MiB. So the text `256M` gives 256 times 1048576, which is 268435456 bytes. |
| 373 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | The letter `g` or `G`: the factor is 1073741824, which is 1024 MiB. |
| 374 | `    }` | Ends the `switch` of line 370. |
| 375 | `    if (end == s \|\| *end != '\0' \|\| v <= 0 \|\| (uint64_t)(v * mul) == 0) { /* 0 bytes after rounding is no size */` | Tests four error cases. The text holds no number (`end == s`). Other text follows the size. The value is 0 or below. The size is 0 bytes after the conversion to a whole number. Comment: 0 bytes after rounding is no size. |
| 376 | `        fprintf(stderr, "bad size: %s\n", s);` | In an error case: prints `bad size:` and the text to stderr, the error output of the program. |
| 377 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 378 | `    }` | Ends the `if` of line 375. |
| 379 | `    return (uint64_t)(v * mul);` | Returns the size in bytes as a whole number. The conversion drops a fraction of a byte. |
| 380 | `}` | Ends the function `parse_bytes`. |

### Function `parse_long`: a whole number inside a range (lines 382 to 395)

| Line | Source | Explanation |
|---:|---|---|
| 382 | `/* A whole number in [lo, hi], with nothing after it. Anything else ends the` | Comment: the function below accepts only a whole number from `lo` to `hi` with no text after it. |
| 383 | ` * program: a malformed value must not run as 0. */` | Comment: any other text ends the program. The reason: a malformed value must not run as the number 0. |
| 384 | `static long parse_long(const char *s, const char *what, long lo, long hi)` | Starts the function `parse_long`. It turns the text `s` into a whole number inside the range `lo` to `hi`. `what` is the name of the option, for the error message. `main` reads `--threads` (allowed 1 to 4096), `--rounds` (1 to 1000000) and `--pmu-type` (0 to 2147483647) with it (line 3095, line 3110, line 3125). |
| 385 | `{` | Opens the body of `parse_long`. |
| 386 | `    char *end;` | `end`: `strtol` sets it to the first character after the number. |
| 387 | `    errno = 0;` | Sets `errno` to 0. `strtol` sets it to an error value when the number does not fit the type `long`. |
| 388 | `    long v = strtol(s, &end, 10);` | `strtol` reads a decimal whole number (base 10) from the start of the text into `v`. |
| 389 | `    if (end == s \|\| *end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi) {` | Tests the error cases: no digit was read, other text follows the number, the number does not fit the type `long`, or it lies outside the range `lo` to `hi`. |
| 390 | `        fprintf(stderr, "bad %s: '%s' (a whole number from %ld to %ld is needed)\n", what, s, lo, hi);` | In an error case: prints `bad`, the option name, the text and the allowed range to stderr. |
| 391 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 392 | `    }` | Ends the `if` of line 389. |
| 393 | `    return v;` | Returns the number. |
| 394 | `}` | Ends the function `parse_long`. |

### Function `restrict_cpus`: no CPU above `MAX_USE_CPU` (lines 396 to 417)

| Line | Source | Explanation |
|---:|---|---|
| 396 | `/* Removes every CPU above MAX_USE_CPU from the allowed set of the calling` | Comment: the function below removes every CPU above `MAX_USE_CPU` from the allowed set of the calling thread. The allowed set is the set of CPUs on which Linux may run the thread. |
| 397 | ` * thread. main() calls it before it starts a thread, so the main thread and` | Comment: `main` calls the function before it starts a thread (line 3074). A new thread takes over the allowed set of the thread that creates it. |
| 398 | ` * every worker (also one without --cpus) stay on the permitted CPUs. */` | Comment: so the main thread and every worker stay on the permitted CPUs. This also holds for a worker of a run without `--cpus`. |
| 399 | `static void restrict_cpus(void)` | Starts the function `restrict_cpus`. |
| 400 | `{` | Opens the body of `restrict_cpus`. |
| 401 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 402 | `    int changed = 0;` | `changed`: becomes 1 when the set held a CPU above the limit. |
| 403 | `    if (sched_getaffinity(0, sizeof set, &set) != 0) {` | `sched_getaffinity` with the first argument 0 reads the allowed set of the calling thread into `set`. A return value other than 0 means that the call failed. |
| 404 | `        perror("sched_getaffinity");` | On failure: `perror` prints the word `sched_getaffinity` and the reason that Linux gave. |
| 405 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 406 | `    }` | Ends the `if` of line 403. |
| 407 | `    for (int c = MAX_USE_CPU + 1; c < CPU_SETSIZE; c++)` | Starts a loop over every CPU number above `MAX_USE_CPU`, up to `CPU_SETSIZE - 1`. `CPU_SETSIZE` is the number of CPUs that the set type of the C library can hold. With the default limit the loop starts at CPU 120. |
| 408 | `        if (CPU_ISSET(c, &set)) {` | Tests whether the set holds the CPU `c`. |
| 409 | `            CPU_CLR(c, &set);` | Removes the CPU `c` from the set. |
| 410 | `            changed = 1;` | Records that the set was changed. |
| 411 | `        }` | Ends the `if` of line 408. |
| 412 | `    if (changed && (CPU_COUNT(&set) == 0 \|\| sched_setaffinity(0, sizeof set, &set) != 0)) {` | Runs only when a CPU was removed. An empty set is an error. If the set is not empty, `sched_setaffinity` passes the smaller set to Linux, and a failed call is an error too. When the process starts with an allowed set that holds no CPU above `MAX_USE_CPU`, `changed` stays 0, and the function changes nothing. |
| 413 | `        fprintf(stderr, "cannot keep the process on CPUs 0-%d\n", MAX_USE_CPU);` | On error: prints `cannot keep the process on CPUs 0-` and the limit to stderr. |
| 414 | `        exit(2);` | On error: the whole program ends with exit status 2. |
| 415 | `    }` | Ends the `if` of line 412. |
| 416 | `}` | Ends the function `restrict_cpus`. |

### Function `parse_cpus`: the value of `--cpus` (lines 418 to 445)

| Line | Source | Explanation |
|---:|---|---|
| 418 | `/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */` | Comment: three examples of a CPU list: `0-119`, `0,2,4-7` and `0-118:2`. The last one is a range with a stride: every second CPU from 0 to 118. |
| 419 | `static void parse_cpus(char *list)` | Starts the function `parse_cpus`. It turns the value of `--cpus` into the array `cfg.cpus`, in the order of the list. |
| 420 | `{` | Opens the body of `parse_cpus`. |
| 421 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Starts a loop over the items of the list. `strtok` splits the text at each comma and returns one item per call. It writes into the text to do that. |
| 422 | `        char *e, *e2;` | `e` and `e2`: positions in the item that `strtol` sets. |
| 423 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the item into `lo`. `hi` starts with the same value and `step` with 1. So an item that is one number names one CPU. |
| 424 | `        if (e != tok && *e == '-') {` | When a number was read and a `-` follows it: the item is a range. |
| 425 | `            hi = strtol(e + 1, &e2, 10);` | Reads the upper bound of the range into `hi`. |
| 426 | `            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */` | When no digit follows the `-`, `e` is set back to `tok`, and the test of line 432 then rejects the item. If a number was read, `e` moves to the character after it. Comment: the item `0-` has no upper bound. |
| 427 | `            if (e != tok && *e == ':') {` | When the upper bound was read and a `:` follows it: the range has a stride. |
| 428 | `                step = strtol(e + 1, &e2, 10);` | Reads the stride into `step`. |
| 429 | `                e = e2 == e + 1 ? tok : e2;` | When no digit follows the `:`, `e` is set back to `tok`, and the test of line 432 rejects the item. If a number was read, `e` moves to the character after it. |
| 430 | `            }` | Ends the `if` of line 427. |
| 431 | `        }` | Ends the `if` of line 424. |
| 432 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| hi > MAX_USE_CPU \|\| step < 1) {` | Rejects an item in six cases: it holds no number, other text follows, the start is negative, the end is below the start, the end is above `MAX_USE_CPU` (119 with the default), or the stride is below 1. |
| 433 | `            fprintf(stderr, "bad cpu list: %s (CPUs 0-%d only)\n", tok, MAX_USE_CPU);` | On such an item: prints `bad cpu list:`, the item and the permitted range to stderr. |
| 434 | `            exit(2);` | On such an item: the whole program ends with exit status 2. |
| 435 | `        }` | Ends the `if` of line 432. |
| 436 | `        for (long c = lo; c <= hi; c += step) {` | Starts a loop over the CPU numbers of the item, from `lo` to `hi` in steps of `step`. |
| 437 | `            if (cfg.ncpus == MAX_CPUS) {` | Tests whether the array `cfg.cpus` is full. It holds at most `MAX_CPUS` entries, which is 1024. |
| 438 | `                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);` | When the array is full: prints `bad cpu list: more than 1024 cpus` to stderr. |
| 439 | `                exit(2);` | When the array is full: the whole program ends with exit status 2. |
| 440 | `            }` | Ends the `if` of line 437. |
| 441 | `            cfg.cpus[cfg.ncpus++] = (int)c;` | Appends the CPU number to `cfg.cpus` and counts it in `cfg.ncpus`. For example the list `0-63,64-119` gives 120 entries in rising order: `cfg.cpus[i]` is `i`. `main` gives thread `i` the CPU `cfg.cpus[i % cfg.ncpus]` (line 3174). |
| 442 | `        }` | Ends the loop of line 436. |
| 443 | `    }` | Ends the loop of line 421. |
| 444 | `}` | Ends the function `parse_cpus`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 446 to 456)

| Line | Source | Explanation |
|---:|---|---|
| 446 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It limits the calling thread to the CPU with the number `cpu`. A worker of a run with `--cpus` calls it at its start (lines 1797 to 1798), before it opens its counters and before it maps its buffer. |
| 447 | `{` | Opens the body of `pin_cpu`. |
| 448 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 449 | `    CPU_ZERO(&set);` | Empties the set. |
| 450 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 451 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 452 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 453 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 454 | `    }` | Ends the `if` of line 451. |
| 455 | `}` | Ends the function `pin_cpu`. |

### Function `buf_len`: the length of one buffer (lines 457 to 461)

| Line | Source | Explanation |
|---:|---|---|
| 457 | `static size_t buf_len(void)` | Starts the function `buf_len`. It returns the length of one buffer in bytes. |
| 458 | `{` | Opens the body of `buf_len`. |
| 459 | `    return (cfg.bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | Returns the `--bytes` value rounded up to a multiple of 2 MiB (`HUGE_BYTES`). The expression adds `HUGE_BYTES - 1` and then clears the low 21 bits. A value of 268435456 bytes (256 MiB) is already 128 times 2 MiB and stays as it is. |
| 460 | `}` | Ends the function `buf_len`. |

### Function `alloc_buf`: map one buffer, aligned to 2 MiB (lines 462 to 483)

| Line | Source | Explanation |
|---:|---|---|
| 462 | `/* The buffer starts at a 2 MiB boundary, at least one page above the start` | Comment: the buffer starts at a 2 MiB boundary. That boundary lies at least one page above the start of the mapping. |
| 463 | ` * of the mapping. The unused parts before and after it are PROT_NONE, so the` | Comment: the unused parts of the mapping before and after the buffer get the access right `PROT_NONE`, which forbids every access. |
| 464 | ` * buffer is one entry of its own in /proc/self/smaps (handoff B.6). */` | Comment: so the buffer is one entry of its own in `/proc/self/smaps`, the Linux file that lists every memory mapping of the process. `read_smaps` (line 1671) looks for an entry with exactly the start and the end of the buffer. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. |
| 465 | `static uint64_t *alloc_buf(void)` | Starts the function `alloc_buf`. It maps one buffer and returns its address. Each worker calls it once (line 1801). A worker of a run with `--cpus` has pinned itself before this call (lines 1797 to 1798). A worker that needs the second buffer calls it once more (line 1804). |
| 466 | `{` | Opens the body of `alloc_buf`. |
| 467 | `    size_t len = buf_len(), maplen = len + 2 * HUGE_BYTES;` | `len`: the buffer length from `buf_len`. `maplen`: 4 MiB more. The extra 4 MiB make room for the alignment of line 473 and for the two no-access ranges of lines 474 to 475. For a buffer of 256 MiB `len` is 268435456 bytes and `maplen` is 272629760 bytes (260 MiB). |
| 468 | `    uint8_t *raw = mmap(NULL, maplen, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `maplen` bytes of new memory that the process may read and write (`PROT_READ \| PROT_WRITE`). `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process only, and no file backs it. `NULL`: Linux chooses the address. `-1` and `0` are the two file arguments, which are not used here. The call does not yet give physical memory to the pages. That happens at the first touch (line 1802). |
| 469 | `    if (raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 470 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 471 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 472 | `    }` | Ends the `if` of line 469. |
| 473 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + (size_t)page_bytes + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the buffer start. It is the first 2 MiB boundary that lies at least one page above the start `raw` of the mapping. The expression adds the page size `page_bytes` and `HUGE_BYTES - 1` to `raw` and then clears the low 21 bits. The buffer is the range from `p` to `p + len`. So it starts at an address that is a multiple of 2 MiB. |
| 474 | `    if (mprotect(raw, (size_t)(p - raw), PROT_NONE) != 0 \|\|` | `mprotect` with `PROT_NONE` forbids every access to the unused range before the buffer, from `raw` to `p`. |
| 475 | `        mprotect(p + len, (size_t)(raw + maplen - (p + len)), PROT_NONE) != 0)` | Continues the test of line 474: the same for the unused range after the buffer, from `p + len` to the end of the mapping. This second call runs only when the first one succeeded. |
| 476 | `        perror("mprotect of the guard ranges (continuing; page state will be NA)");` | When one of the two calls failed: `perror` prints a message which says that the run continues and that the page state will be `NA`. The program does not stop. The message goes to stderr, the error output of the program. |
| 477 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: the advice `MADV_NOHUGEPAGE` matters on a host whose setting for transparent huge pages is `always`. |
| 478 | `     * would still get 2 MiB pages. */` | Comment: without that advice a run with `--no-thp` would still get 2 MiB pages on such a host. |
| 479 | `    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` gives Linux advice about the buffer range. With `cfg.use_thp` set, the advice is `MADV_HUGEPAGE`: use 2 MiB pages for this range. With `--no-thp` it is `MADV_NOHUGEPAGE`: do not use them. The function does not test whether the buffer got 2 MiB pages. The P rows show how much of each buffer lies on 2 MiB pages (line 1730). |
| 480 | `        perror("madvise (continuing)");` | When `madvise` failed: `perror` prints `madvise (continuing)` and the reason that Linux gave. The run continues. |
| 481 | `    return (uint64_t *)p;` | Returns the buffer start as a pointer to 8-byte words. No line of this file unmaps a buffer. So the buffer stays mapped until the process ends. |
| 482 | `}` | Ends the function `alloc_buf`. |

### Old read kernel: the macro `DEF_OLDREAD` and the kernels `oldread` and `oldread2` (lines 484 to 507)

| Line | Source | Explanation |
|---:|---|---|
| 484 | `/*` | Opens the comment about the old kernels. |
| 485 | ` * Old kernels: k_read, k_write and k_copy of bandwidth.orig.c (the benchmark` | Comment: the old kernels below are the functions `k_read`, `k_write` and `k_copy` of the file `bandwidth.orig.c`. |
| 486 | ` * until 2026-11-13), renamed. The old comment of k_read was: "16 independent` | Comment: `bandwidth.orig.c` was the benchmark source until 2026-11-13. Here its three kernels have the new names `k_oldread`, `k_oldwrite` and `k_oldcopy`. `bw_old` is the benchmark binary of 2026-11-13 that was built from that file. Apart from absolute addresses, the machine code of `k_oldread` in the CRB build of `bwx13` has the same instruction text as `k_read` of `bw_old` [Ref1] [Ref3]. A quotation of the old comment of `k_read` starts in this line. |
| 487 | ` * accumulators keep the loop load-bound: on 128-bit NEON gcc folds them into` | Comment, quotation: 16 separate running sums (accumulators) keep the loop load-bound. This means that the loads and not the adds should limit the speed of the loop. This is a statement of the old comment. It is not a measured result. |
| 488 | ` * 8 vector chains, enough to hide a 2-cycle add latency; on AVX-512 they` | Comment, quotation: with the 128-bit NEON registers gcc puts the 16 sums into 8 vector registers. Each register is a chain of adds of its own. The old comment says that 8 chains are enough for an add that takes 2 clock cycles: the adds then do not limit the speed of the loop. The listing of the CRB binary of `bwx13` confirms the 8 registers: the sums are in the registers `v24` to `v31` [Ref1]. |
| 489 | ` * become 2 zmm chains." oldread2 is the A/A copy: the same source under a` | Comment: the end of the quotation: with AVX-512, a vector instruction set of x86 processors, the sums become 2 chains in 512-bit registers. The next sentence: `oldread2` is the A/A copy, the same source under a second name. |
| 490 | ` * second name (the build uses -fno-ipa-icf, so gcc keeps both).` | Comment: the build uses the gcc flag `-fno-ipa-icf`. With it gcc keeps both functions. The flag is in the build record of CRB for `bwx13` [Ref2]. |
| 491 | ` */` | Ends the comment. |
| 492 | `#define DEF_OLDREAD(name) \` | Starts the macro `DEF_OLDREAD(name)`. It writes `PLACE(name)` and one function: the source text of the old read kernel. The backslash at the end of each line continues the macro on the next line. |
| 493 | `    PLACE(name); \` | `PLACE` (line 194) adds the pad of this kernel. So the function starts at the value of `PAD_` plus `name`, modulo 64. |
| 494 | `    __attribute__((noinline)) static uint64_t k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the macro argument into the function name. `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns a 64-bit sum. `noinline`: gcc must keep the function separate from its caller. The listing of the CRB build of `bwx13` shows `k_oldread` as a function of its own [Ref1]. With `--stop common` one call in a timed interval gets one chunk of 2 MiB: `n` is then 262144 words (line 1851). The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1825). |
| 495 | `    { \` | Opens the body of the kernel function. |
| 496 | `        uint64_t s[16] = { 0 }; \` | `s`: the 16 running sums. All start at 0. Machine code of `k_oldread` in `bwx13`, once per call and before the loop: 4 `stp` instructions write 128 B of zeros to the stack (each stores two 16-byte registers), and the 8 registers `v24` to `v31` are set to 0. During the loop these 8 registers hold the 16 sums, two sums per register [Ref1]. |
| 497 | `        for (size_t i = 0; i < n; i += 16) \` | The outer loop. One pass takes 16 words, which are 128 B. Machine code of `k_oldread` in `bwx13`: gcc did not unroll this loop. One pass of the machine loop is one pass of this source loop. Before the loop the code computes the number of passes into the register `x2` [Ref1]. |
| 498 | `            for (int j = 0; j < 16; j++) \` | The inner loop over the 16 words of the block. Machine code of `k_oldread` in `bwx13`: gcc compiled this loop to vector instructions. No loop over `j` is left [Ref1]. |
| 499 | `                s[j] += a[i + j]; \` | Adds word `j` of the block to sum `j`. So every loaded word is an input of one add. Machine code of `k_oldread` in `bwx13`, one loop pass of 16 instructions for 128 B [Ref1]: 4 `ldp` loads of 32 B each, at the byte offsets 0, 32, 64 and 96 from the read position. 8 vector adds: each one adds one loaded register to one of the sum registers `v24` to `v31` and so performs two of the 16 adds of the source. `add x0, x0, #0x80` moves the read position by 128 B. `add x1, x1, #0x1` counts the pass. `cmp` and `b.cc` branch back while the count is below the number of passes. No instruction of the loop stores to memory. |
| 500 | `        uint64_t sum = 0; \` | `sum`: the total of the 16 sums. It starts at 0. |
| 501 | `        for (int j = 0; j < 16; j++) \` | A loop over the 16 sums. It runs once per call, after the read loop. |
| 502 | `            sum += s[j]; \` | Adds the 16 sums into one value. Machine code of `k_oldread` in `bwx13`, once per call [Ref1]: the 8 sum registers are stored to the stack and loaded back. Then 7 vector adds and one `addp` add them into one number. `addp` adds the two 64-bit halves of one register. |
| 503 | `        return sum; \` | Returns the total. Machine code of `k_oldread` in `bwx13`: `fmov x0, d31` copies the result into the return register `x0` [Ref1]. `call` stores the returned value into the volatile variable `sink` (line 1656). So the sum is used, and the compiler cannot remove the loads and the adds as unused work. gcc also added a stack check to this function. It saves a guard value on the stack at the start and compares it before the return. A changed value leads to a call of `__stack_chk_fail` [Ref1]. |
| 504 | `    }` | Ends the kernel function and the macro. In `bwx13` one call of `k_oldread` runs 53 instructions outside the loop [Ref1]. One chunk of 2 MiB is 16384 loop passes, which are 262144 instructions. |
| 505 | `DEF_OLDREAD(oldread)` | Creates the function `k_oldread`. It is the kernel `oldread` of `--seq`, the old read kernel, with the type `T_OLDREAD` in the kernel table (line 1615). In the CRB binary of `bwx13` the function starts at the address `0x4700` and its loop at `0x4768`, which is 40 modulo 64 [Ref1]. For 256 B it runs 2 loop passes: 32 instructions with 8 `ldp` loads, 16 vector adds and 2 branches. The new read kernel runs 11 instructions for 256 B (line 558). Apart from absolute addresses, the machine code of `k_oldread` has the same instruction text as `k_read` of the binary `bw_old` [Ref3]. |
| 506 | `DEF_OLDREAD(oldread2)` | Creates `k_oldread2`, the A/A copy of the old read kernel. The listing of the CRB build of `bwx13` shows the same instruction text for both functions [Ref1]. |

### Old write kernel `oldwrite` and old copy kernel `oldcopy` (lines 508 to 521)

| Line | Source | Explanation |
|---:|---|---|
| 508 | `PLACE(oldwrite);` | `PLACE` adds the pad of the kernel `oldwrite`. `PAD_oldwrite` is 32 (line 263). |
| 509 | `__attribute__((noinline)) static void k_oldwrite(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_oldwrite`, the kernel `oldwrite`: the write kernel of the old benchmark source. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. The first touch of a buffer uses `k_write` (line 562). |
| 510 | `{` | Opens the body of `k_oldwrite`. |
| 511 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 512 | `        a[i] = v;` | Stores `v` to word `i`: one store of 8 B per pass of the source loop. Machine code in the CRB binary of `bwx13`: gcc compiled the loop to instructions of SVE, the scalable vector extension of Arm. One loop pass has 4 instructions with one `st1d` store, which writes one vector of 8-byte words. The program reads the number of words per vector at run time with the instruction `cntd`. The listing does not give this number [Ref1]. |
| 513 | `}` | Ends the function `k_oldwrite`. |
| 515 | `PLACE(oldcopy);` | `PLACE` adds the pad of the kernel `oldcopy`. `PAD_oldcopy` is 32 (line 266). |
| 516 | `__attribute__((noinline)) static void k_oldcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_oldcopy`, the kernel `oldcopy`: the copy kernel of the old benchmark source. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 517 | `{` | Opens the body of `k_oldcopy`. |
| 518 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 519 | `        d[i] = s[i];` | Loads word `i` of the source and stores it to word `i` of the destination. The loaded value is stored and has no other use. Machine code in the CRB binary of `bwx13`: SVE instructions, as in `k_oldwrite`. One loop pass has 5 instructions with one `ld1d` load and one `st1d` store of one vector of 8-byte words [Ref1]. |
| 520 | `}` | Ends the function `k_oldcopy`. |

### AArch64 branch and the function `k_read`: the new read kernel (lines 522 to 560)

| Line | Source | Explanation |
|---:|---|---|
| 522 | `#if defined(__aarch64__)` | The lines from here to the `#else` of line 882 are compiled only for AArch64. The lines from that `#else` to the `#endif` of line 928 hold the stand-ins for other machines. The CRB build of `bwx13` is an AArch64 build: its listing holds AArch64 instructions such as the `ldp` of `k_read` [Ref1]. So it was compiled from this first branch. |
| 523 | `#define STANDIN 0` | `STANDIN` is 0 in the AArch64 branch: the kernels are the real ones. The program then prints `kernels=aarch64` in its header (line 3187). |
| 524 | `/*` | Opens the comment about the C kernels. |
| 525 | ` * C kernels: unchanged from bench/bandwidth.c. Each iteration moves 256 B as` | Comment: the C kernels below are unchanged from the benchmark source `bandwidth.c` in the folder `bench`. One loop pass moves 256 B. |
| 526 | ` * 16 vectors of 16 B and does no arithmetic on the data. Callers guarantee` | Comment: the 256 B move as 16 vectors of 16 B. The loop does no arithmetic on the data. |
| 527 | ` * n * 8 is a multiple of 256 and non-zero. The empty asm statement of k_read` | Comment: the callers guarantee that the size `n * 8` in bytes is a multiple of 256 and is not 0. `main` checks the sizes (line 3136 and line 3154). A chunk of 2 MiB is a multiple of 256. The sentence about the empty `asm` statement starts here. |
| 528 | ` * and k_copy takes the 16 loaded vectors as inputs in NEON registers ("w"):` | Comment: the empty `asm` statement of `k_read` (lines 553 to 556) and of `k_copy` (lines 611 to 614) takes the 16 loaded vectors as inputs. The letter `w` says that each input must be in a NEON register. |
| 529 | ` * see the comment in bench/bandwidth.c.` | Comment: a comment in the file `bandwidth.c` of the folder `bench` explains this statement. |
| 530 | ` */` | Ends the comment. |
| 531 | `PLACE(read);` | `PLACE(read)` with `PAD_read` = 32 (line 239): the function starts at 32 modulo 64. In the CRB binary of `bwx13` the function `k_read` starts at the address `0x4aa0` and its loop at `0x4aa4`, which is 36 modulo 64 [Ref1]. The loop of `k_read` in `bw_new` has the same offset 36 [Ref3]. |
| 532 | `__attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)` | Starts the function `k_read`: the kernel `read` of `--seq`, the new read kernel, with the type `T_READ` in the kernel table (line 1613). `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns nothing: it computes no sum. `noinline`: gcc must keep the function separate from its caller. The listing of `bwx13` shows it as a function of 13 instructions [Ref1]. Apart from absolute addresses, its instruction text equals the text of `k_read` in `bw_new`, the benchmark binary of 2026-11-13 with the new kernels [Ref3]. |
| 533 | `{` | Opens the body of `k_read`. With `--stop common` one call of the function in a timed interval gets one chunk of 2 MiB: `n` is then 262144 words (line 1851). The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1825). |
| 534 | `    const uint64_t *p = a;` | `p`: the read position. It starts at `a`. |
| 535 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx13`, once per call and before the loop: `add x1, x0, x1, lsl #3`. Before this instruction the register `x0` holds `a` and `x1` holds `n`. After it `x1` holds `end` [Ref1]. |
| 536 | `    do {` | Starts the loop. With `do` the loop body runs once before the first test of the end. So the range must not be empty. |
| 537 | `        uint64x2_t v0 = vld1q_u64(p + 0);` | `vld1q_u64(p + 0)` loads 16 B, which are two 8-byte words, from the read position into the vector `v0`. These are the bytes 0 to 15 of the current block of 256 B. |
| 538 | `        uint64x2_t v1 = vld1q_u64(p + 2);` | Loads the bytes 16 to 31 of the block, 2 words after the read position, into `v1`. Machine code of `bwx13`: gcc joined this load and the load of line 537 into one instruction, `ldp q31, q30, [x0]`, which loads 32 B [Ref1]. |
| 539 | `        uint64x2_t v2 = vld1q_u64(p + 4);` | Loads the bytes 32 to 47 of the block into `v2`. |
| 540 | `        uint64x2_t v3 = vld1q_u64(p + 6);` | Loads the bytes 48 to 63 of the block into `v3`. Machine code of `bwx13` for this load and the load of line 539: `ldp q29, q28, [x0, #32]` [Ref1]. |
| 541 | `        uint64x2_t v4 = vld1q_u64(p + 8);` | Loads the bytes 64 to 79 of the block into `v4`. |
| 542 | `        uint64x2_t v5 = vld1q_u64(p + 10);` | Loads the bytes 80 to 95 of the block into `v5`. Machine code of `bwx13` for this load and the load of line 541: `ldp q27, q26, [x0, #64]` [Ref1]. |
| 543 | `        uint64x2_t v6 = vld1q_u64(p + 12);` | Loads the bytes 96 to 111 of the block into `v6`. |
| 544 | `        uint64x2_t v7 = vld1q_u64(p + 14);` | Loads the bytes 112 to 127 of the block into `v7`. Machine code of `bwx13` for this load and the load of line 543: `ldp q25, q24, [x0, #96]` [Ref1]. |
| 545 | `        uint64x2_t v8 = vld1q_u64(p + 16);` | Loads the bytes 128 to 143 of the block into `v8`. |
| 546 | `        uint64x2_t v9 = vld1q_u64(p + 18);` | Loads the bytes 144 to 159 of the block into `v9`. Machine code of `bwx13` for this load and the load of line 545: `ldp q23, q22, [x0, #128]` [Ref1]. |
| 547 | `        uint64x2_t v10 = vld1q_u64(p + 20);` | Loads the bytes 160 to 175 of the block into `v10`. |
| 548 | `        uint64x2_t v11 = vld1q_u64(p + 22);` | Loads the bytes 176 to 191 of the block into `v11`. Machine code of `bwx13` for this load and the load of line 547: `ldp q21, q20, [x0, #160]` [Ref1]. |
| 549 | `        uint64x2_t v12 = vld1q_u64(p + 24);` | Loads the bytes 192 to 207 of the block into `v12`. |
| 550 | `        uint64x2_t v13 = vld1q_u64(p + 26);` | Loads the bytes 208 to 223 of the block into `v13`. Machine code of `bwx13` for this load and the load of line 549: `ldp q19, q18, [x0, #192]` [Ref1]. |
| 551 | `        uint64x2_t v14 = vld1q_u64(p + 28);` | Loads the bytes 224 to 239 of the block into `v14`. |
| 552 | `        uint64x2_t v15 = vld1q_u64(p + 30);` | Loads the bytes 240 to 255 of the block into `v15`. Machine code of `bwx13` for this load and the load of line 551: `ldp q17, q16, [x0, #224]`. One loop pass has 16 loads in the source and 8 `ldp` loads in the machine code. It reads 256 B, each byte once, in rising address order [Ref1]. |
| 553 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text. It adds no instruction to the loop. It names the loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. A comment in the benchmark source `bandwidth.c` gives the purpose: gcc must have all 16 values in registers at this point, and this keeps gcc from deleting the loads. After this statement nothing uses the values. They are dropped. The listing of `bwx13` shows no add and no other instruction that uses a loaded register [Ref1]. This is the difference to the old read kernel, which adds every loaded word to a sum. |
| 554 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 553: the inputs `v4` to `v7`. |
| 555 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 553: the inputs `v8` to `v11`. |
| 556 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 553: the inputs `v12` to `v15`. The statement ends here. |
| 557 | `        p += 32;` | Moves the read position forward by 32 words, which are 256 B. Machine code of `bwx13`: `add x0, x0, #0x100` [Ref1]. |
| 558 | `    } while (p < end);` | Repeats the loop while the read position is below the end. Machine code of `bwx13`: `cmp x1, x0`, then `b.hi` back to the first `ldp`. One loop pass is 11 instructions for 256 B: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1]. One chunk of 2 MiB is 8192 loop passes, which are 90112 instructions. |
| 559 | `}` | Ends the function `k_read`. Machine code of `bwx13`: one `ret` instruction. gcc used the registers `q16` to `q31` for the loads, and the function saves and restores no register [Ref1]. The AArch64 branch of line 522 continues after this function, up to line 882. |

### Function `k_write`: the NEON write kernel, used for the first touch (lines 561 to 587)

| Line | Source | Explanation |
|---:|---|---|
| 561 | `PLACE(write);` | `PLACE(write)` adds the pad of this kernel. `PAD_write` is 0 (line 242). So the function starts at a multiple of 64 bytes: the address `0x4b00` in the listing of the CRB build of `bwx13`. The function stands in the AArch64 branch of line 522, and the CRB binary holds this branch: the listing shows the `dup` and `stp` instructions of this function [Ref1]. |
| 562 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_write`, the NEON write kernel. It stores the value `v` to `n` 8-byte words, from the address `a` on. Each worker calls it once per buffer, directly after the allocation (line 1802). This call is the first touch. It happens before the first interval, and it is not timed. The call writes the first `cfg.bytes` bytes of the buffer, the range of `--bytes`. The buffer is this value rounded up to a multiple of 2 MiB (line 459). So the call writes the whole buffer only when `--bytes` is a multiple of 2 MiB. The kernel table also offers this function as the kernel `write` (line 1613). |
| 563 | `{` | Opens the body of `k_write`. |
| 564 | `    uint64_t *p = a;` | `p`: the write position. It starts at `a`. |
| 565 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx13`, before the loop: `add x1, x0, x1, lsl #3` [Ref1]. |
| 566 | `    uint64x2_t q = vdupq_n_u64(v);` | `vdupq_n_u64(v)` builds one 16-byte vector `q` that holds `v` twice. Machine code of `bwx13`, before the loop: `dup v31.2d, x2`. The register `x2` holds `v`. `dup` copies one 8-byte value into both halves of a 16-byte vector register [Ref1]. |
| 567 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 568 | `        vst1q_u64(p + 0, q);` | `vst1q_u64(p + 0, q)` stores the 16 bytes of `q` at the write position. These are the bytes 0 to 15 of the current block of 256 B. |
| 569 | `        vst1q_u64(p + 2, q);` | Stores `q` to the bytes 16 to 31 of the block. Machine code of `bwx13`: gcc joined this store and the store of line 568 into one instruction `stp q31, q31`. `stp` stores two 16-byte registers, which is 32 B. Here both are the register `q31` [Ref1]. |
| 570 | `        vst1q_u64(p + 4, q);` | Stores `q` to the bytes 32 to 47 of the block. |
| 571 | `        vst1q_u64(p + 6, q);` | Stores `q` to the bytes 48 to 63 of the block. |
| 572 | `        vst1q_u64(p + 8, q);` | Stores `q` to the bytes 64 to 79 of the block. |
| 573 | `        vst1q_u64(p + 10, q);` | Stores `q` to the bytes 80 to 95 of the block. |
| 574 | `        vst1q_u64(p + 12, q);` | Stores `q` to the bytes 96 to 111 of the block. |
| 575 | `        vst1q_u64(p + 14, q);` | Stores `q` to the bytes 112 to 127 of the block. |
| 576 | `        vst1q_u64(p + 16, q);` | Stores `q` to the bytes 128 to 143 of the block. |
| 577 | `        vst1q_u64(p + 18, q);` | Stores `q` to the bytes 144 to 159 of the block. |
| 578 | `        vst1q_u64(p + 20, q);` | Stores `q` to the bytes 160 to 175 of the block. |
| 579 | `        vst1q_u64(p + 22, q);` | Stores `q` to the bytes 176 to 191 of the block. |
| 580 | `        vst1q_u64(p + 24, q);` | Stores `q` to the bytes 192 to 207 of the block. |
| 581 | `        vst1q_u64(p + 26, q);` | Stores `q` to the bytes 208 to 223 of the block. |
| 582 | `        vst1q_u64(p + 28, q);` | Stores `q` to the bytes 224 to 239 of the block. |
| 583 | `        vst1q_u64(p + 30, q);` | Stores `q` to the bytes 240 to 255 of the block. The 16 stores of one loop pass fill 256 B. Each byte is written once. The machine loop of `bwx13` has 8 `stp` instructions [Ref1]. |
| 584 | `        p += 32;` | Moves the write position forward by 32 words, which are 256 B. Machine code of `bwx13`: `add x0, x0, #0x100`. gcc put this `add` at the start of the loop pass. So the 8 `stp` instructions use the offsets -256 to -32 [Ref1]. |
| 585 | `    } while (p < end);` | Repeats the loop while the write position is below `end`. Machine code of `bwx13`: `cmp x1, x0` and the branch `b.hi`. One loop pass is 11 instructions for 256 B: 1 `add`, 8 `stp`, 1 `cmp` and 1 branch [Ref1]. With `--bytes 256M` the first touch writes 268435456 bytes in 1048576 loop passes. The binary `bw_new` holds the same instruction text for its `k_write` [Ref3]. |
| 586 | `}` | Ends the function `k_write`. |

### Function `k_copy`: the NEON copy kernel (lines 588 to 635)

| Line | Source | Explanation |
|---:|---|---|
| 588 | `PLACE(copy);` | `PLACE(copy)` adds the pad `PAD_copy`, which is 32 bytes with the default values (line 221). |
| 589 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_copy`, the kernel `copy`: the NEON copy kernel. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 590 | `{` | Opens the body of `k_copy`. |
| 591 | `    uint64_t *dp = d;` | `dp`: the write position in the destination. It starts at `d`. |
| 592 | `    const uint64_t *sp = s;` | `sp`: the read position in the source. It starts at `s`. |
| 593 | `    const uint64_t *end = s + n;` | `end`: the first address after the source range: `s` plus `n` words. |
| 594 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 595 | `        uint64x2_t v0 = vld1q_u64(sp + 0);` | `vld1q_u64(sp + 0)` loads 16 B from the read position into the vector `v0`. These are the bytes 0 to 15 of the current source block of 256 B. |
| 596 | `        uint64x2_t v1 = vld1q_u64(sp + 2);` | Loads the bytes 16 to 31 of the source block into `v1`. |
| 597 | `        uint64x2_t v2 = vld1q_u64(sp + 4);` | Loads the bytes 32 to 47 of the source block into `v2`. |
| 598 | `        uint64x2_t v3 = vld1q_u64(sp + 6);` | Loads the bytes 48 to 63 of the source block into `v3`. |
| 599 | `        uint64x2_t v4 = vld1q_u64(sp + 8);` | Loads the bytes 64 to 79 of the source block into `v4`. |
| 600 | `        uint64x2_t v5 = vld1q_u64(sp + 10);` | Loads the bytes 80 to 95 of the source block into `v5`. |
| 601 | `        uint64x2_t v6 = vld1q_u64(sp + 12);` | Loads the bytes 96 to 111 of the source block into `v6`. |
| 602 | `        uint64x2_t v7 = vld1q_u64(sp + 14);` | Loads the bytes 112 to 127 of the source block into `v7`. |
| 603 | `        uint64x2_t v8 = vld1q_u64(sp + 16);` | Loads the bytes 128 to 143 of the source block into `v8`. |
| 604 | `        uint64x2_t v9 = vld1q_u64(sp + 18);` | Loads the bytes 144 to 159 of the source block into `v9`. |
| 605 | `        uint64x2_t v10 = vld1q_u64(sp + 20);` | Loads the bytes 160 to 175 of the source block into `v10`. |
| 606 | `        uint64x2_t v11 = vld1q_u64(sp + 22);` | Loads the bytes 176 to 191 of the source block into `v11`. |
| 607 | `        uint64x2_t v12 = vld1q_u64(sp + 24);` | Loads the bytes 192 to 207 of the source block into `v12`. |
| 608 | `        uint64x2_t v13 = vld1q_u64(sp + 26);` | Loads the bytes 208 to 223 of the source block into `v13`. |
| 609 | `        uint64x2_t v14 = vld1q_u64(sp + 28);` | Loads the bytes 224 to 239 of the source block into `v14`. |
| 610 | `        uint64x2_t v15 = vld1q_u64(sp + 30);` | Loads the bytes 240 to 255 of the source block into `v15`. One loop pass loads 256 B with 16 NEON loads of 16 B. |
| 611 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text, as in `k_read` (line 553). It adds no instruction. It names the 16 loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. So gcc must have all 16 loaded values in registers at this point. A comment in the benchmark source `bandwidth.c` of the folder `bench` reports the effect on the copy loop with gcc 14.2.0: with the statement the 8 `ldp` stand ahead of the 8 `stp`, and without it loads and stores alternate. |
| 612 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 611: the inputs `v4` to `v7`. |
| 613 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 611: the inputs `v8` to `v11`. |
| 614 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 611: the inputs `v12` to `v15`. The statement ends here. |
| 615 | `        vst1q_u64(dp + 0, v0);` | `vst1q_u64(dp + 0, v0)` stores the vector `v0` to the bytes 0 to 15 of the current destination block. So each loaded value is stored once and has no other use. |
| 616 | `        vst1q_u64(dp + 2, v1);` | Stores `v1` to the bytes 16 to 31 of the destination block. |
| 617 | `        vst1q_u64(dp + 4, v2);` | Stores `v2` to the bytes 32 to 47 of the destination block. |
| 618 | `        vst1q_u64(dp + 6, v3);` | Stores `v3` to the bytes 48 to 63 of the destination block. |
| 619 | `        vst1q_u64(dp + 8, v4);` | Stores `v4` to the bytes 64 to 79 of the destination block. |
| 620 | `        vst1q_u64(dp + 10, v5);` | Stores `v5` to the bytes 80 to 95 of the destination block. |
| 621 | `        vst1q_u64(dp + 12, v6);` | Stores `v6` to the bytes 96 to 111 of the destination block. |
| 622 | `        vst1q_u64(dp + 14, v7);` | Stores `v7` to the bytes 112 to 127 of the destination block. |
| 623 | `        vst1q_u64(dp + 16, v8);` | Stores `v8` to the bytes 128 to 143 of the destination block. |
| 624 | `        vst1q_u64(dp + 18, v9);` | Stores `v9` to the bytes 144 to 159 of the destination block. |
| 625 | `        vst1q_u64(dp + 20, v10);` | Stores `v10` to the bytes 160 to 175 of the destination block. |
| 626 | `        vst1q_u64(dp + 22, v11);` | Stores `v11` to the bytes 176 to 191 of the destination block. |
| 627 | `        vst1q_u64(dp + 24, v12);` | Stores `v12` to the bytes 192 to 207 of the destination block. |
| 628 | `        vst1q_u64(dp + 26, v13);` | Stores `v13` to the bytes 208 to 223 of the destination block. |
| 629 | `        vst1q_u64(dp + 28, v14);` | Stores `v14` to the bytes 224 to 239 of the destination block. |
| 630 | `        vst1q_u64(dp + 30, v15);` | Stores `v15` to the bytes 240 to 255 of the destination block. One loop pass stores 256 B with 16 NEON stores of 16 B. |
| 631 | `        sp += 32;` | Moves the read position forward by 32 words, which are 256 B. |
| 632 | `        dp += 32;` | Moves the write position forward by 32 words, which are 256 B. |
| 633 | `    } while (sp < end);` | Repeats the loop while the read position is below `end`. Machine code of `bwx13`, one loop pass: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.hi`. That is 20 instructions for 256 B loaded and 256 B stored. gcc joined each two neighbour loads into one `ldp` and each two neighbour stores into one `stp` [Ref1]. |
| 634 | `}` | Ends the function `k_copy`. |

### Macro `DEF_ASMREAD`: the hand-written read loop and its first six kernels (lines 636 to 679)

| Line | Source | Explanation |
|---:|---|---|
| 636 | `/*` | Opens the comment about the assembly kernels. |
| 637 | ` * asm kernels: the asm text of bench/bandwidth.c, inside macros so that an` | Comment: the kernels below hold the assembly text of the benchmark source `bandwidth.c` in the folder `bench`. From here to line 880 the loop of each kernel is assembly text inside an `__asm__` statement. gcc copies this text into the function. The text of three loops stands inside macros. |
| 638 | ` * A/A copy is the same source under a second name. Each iteration moves` | Comment: the reason for the macros: one more line then defines the same loop under a second name, an A/A copy. |
| 639 | ` * 256 B with 8 ldp/stp of q registers (16 B each). Callers guarantee n * 8` | Comment: one loop pass moves 256 B with 8 `ldp` or `stp` instructions. Each of them moves two `q` registers of 16 B. The read loop has 8 `ldp`. The write loop has 8 `stp`. The copy loop has 8 `ldp` and 8 `stp`. |
| 640 | ` * is a multiple of 256 and non-zero. v8-v15 are callee-saved in AAPCS64:` | Comment: the callers guarantee that the size in bytes is a multiple of 256 and is not 0. The loop tests the end only after a loop pass. `main` ends the program with status 2 when `--bytes` is 0 or is not a multiple of 256 (line 3136), and when the size of a `--seq` entry is not a multiple of 256 (line 3154). The next sentence: AAPCS64, the calling rules of Arm, say that a function must keep `v8` to `v15` for its caller. |
| 641 | ` * naming them as clobbers makes gcc save d8-d15 once per call, which is` | Comment: the `asm` statement names these registers as changed (clobbers). So gcc saves `d8` to `d15`, the low 8 bytes of these registers, once per call. |
| 642 | ` * outside the loop.` | Comment: this save is outside the loop. |
| 643 | ` *` | Comment: an empty line of the comment. |
| 644 | ` * DEF_ASMREAD(name, nops) puts "nops" nop instructions after the 8 ldp and` | Comment: the macro `DEF_ASMREAD(name, nops)` puts `nops` instructions of the kind `nop` after the 8 `ldp`. |
| 645 | ` * before the add (step B5). asmread and asmread2 have 0 of them.` | Comment: the `nop` instructions stand before the `add`. The comment links them to step B5 of the file `handoff.md`, the specification of the first runner. `asmread` and `asmread2` have 0 `nop`. |
| 646 | ` */` | Ends the comment. |
| 647 | `#define DEF_ASMREAD(name, nops) \` | Starts the macro `DEF_ASMREAD(name, nops)`. It defines one kernel function with a hand-written read loop. The backslash at the end of each line continues the macro on the next line. The kernel `asmread` (line 673) and every `read_nop` kernel come from this macro. |
| 648 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 194). For `asmread` and for every `read_nop` kernel the pad is 0 bytes. So each of these functions starts at a multiple of 64 bytes. |
| 649 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the first macro argument: `DEF_ASMREAD(asmread, 0)` defines the function `k_asmread`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. `noinline` forbids gcc to merge the function into its caller. So the listing of the CRB build of `bwx13` shows each kernel as a function of its own [Ref1]. |
| 650 | `    { \` | Opens the body of the kernel function. |
| 651 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 652 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx13`: `add x1, x0, x1, lsl #3`, which adds 8 times `x1` to `x0` and puts the result into `x1`. It runs once per call, before the loop [Ref1]. |
| 653 | `        __asm__ volatile( \` | Starts a gcc statement that holds assembly text. gcc copies the text into the function. `volatile` tells gcc to keep the statement, although no later code uses `p`. The listing of `bwx13` shows the instructions in the order of the text [Ref1]. |
| 654 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. `\n\t` ends one line of the assembly text and indents the next one. In the CRB binary of `bwx13` the loop of `k_asmread` and the loop of every `read_nop` kernel start at an address of 20 modulo 64 [Ref1]. |
| 655 | `            "ldp q0, q1, [%[p]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 15 of the current block of 256 B into `q0` and the bytes 16 to 31 into `q1`. `%[p]` stands for the register that gcc chose for `p`. In the listing of `bwx13` it is `x0` [Ref1]. |
| 656 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 657 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 658 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. With this instruction the bytes 0 to 127 of the block are loaded. |
| 659 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 660 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 661 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 662 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once, in rising address order. Nothing uses the loaded values: no instruction of the loop takes `q0` to `q15` as an input, and the next loop pass overwrites the registers. The old read kernel `k_oldread` (line 505) differs in this point: its source adds every loaded word to a sum (line 499). The unrolling is part of this text: 8 `ldp` per loop pass. gcc does not change the instructions of assembly text. It only puts register names in the places of `%[p]` and `%[end]`. |
| 663 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the second macro argument into text. For `read_nop4` the assembler sees the three lines `.rept 4`, `nop` and `.endr`. `.rept N` and `.endr` are assembler directives: the assembler repeats the lines between them N times. With `.rept 0` it writes nothing. So the loop of `asmread` has 0 `nop` between the last `ldp` and the `add`, and the loop of `read_nop4` has 4. A `nop` does nothing and loads nothing. So every loop pass still reads 256 B, and only the instruction count of the loop pass grows. |
| 664 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the read pointer forward by 256 B. Machine code of `bwx13`: `add x0, x0, #0x100` [Ref1]. |
| 665 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the read pointer with `end` and sets the condition flags. Machine code of `bwx13`: `cmp x0, x1` [Ref1]. |
| 666 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. `lo` means lower in an unsigned compare. The end test stands after the loop body. So the body runs at least once in every call. Instructions of one loop pass: 8 `ldp`, the `nop` instructions and these 3. That is 11 per 256 B in `asmread`, which has no `nop`. The listing of `bwx13` prints `b.cc` for this branch and names `b.lo` as another name of it [Ref1]. |
| 667 | `            : [p] "+r"(p) \` | Tells gcc which C variables the text uses. `[p] "+r"(p)`: `p` is in a general register, and the text reads it and changes it. |
| 668 | `            : [end] "r"(end) \` | `[end] "r"(end)`: `end` is an input in a general register. In the listing of `bwx13` it is `x1` [Ref1]. |
| 669 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list. It tells gcc what the text changes besides `p`. This line names the vector registers `v0` to `v7`. |
| 670 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` on the stack before the loop and loads them back after it. In the listing of `bwx13` these are 4 `stp` instructions before the loop and 4 `ldp` instructions after it [Ref1]. This save runs once per call of the kernel, not once per loop pass. With `--stop common` one call in a timed interval covers one chunk of 2 MiB (line 1851). That is 8192 loop passes. |
| 671 | `              "memory", "cc"); \` | Ends the clobber list and the statement. `"memory"` says that the text accesses memory that no operand names. `"cc"` says that the text changes the condition flags. |
| 672 | `    }` | Ends the kernel function and the macro. In `bwx13` the function `k_asmread` has 21 instructions: 5 before the loop, 11 in the loop and 5 after it, with `ret` as the last one [Ref1]. |
| 673 | `DEF_ASMREAD(asmread, 0)` | Defines `k_asmread`, the kernel `asmread`: the macro loop with 0 `nop`. One loop pass has 8 `ldp` loads of 32 B, `add`, `cmp` and the branch: 11 instructions per 256 B. In the CRB build of `bwx13` its instruction text equals the text of `k_asmread` in the benchmark binary `bw_new` [Ref1] [Ref3]. `k_read` (line 532), the new read kernel, has the same 8 `ldp` loads and the same 11 instructions per 256 B. The listing shows four differences [Ref1]. Registers: `q0` to `q15` here, `q31` to `q16` in `k_read`. Save of `d8` to `d15`, outside the loop: only here. Loop start: 20 modulo 64 here, 36 in `k_read`. End test: `cmp x0, x1` with `b.cc` here, `cmp x1, x0` with `b.hi` in `k_read`. |
| 674 | `DEF_ASMREAD(asmread2, 0)` | Defines `k_asmread2`, the A/A copy of `asmread`. The listing of the CRB build of `bwx13` shows the same instruction text for both [Ref1]. |
| 675 | `DEF_ASMREAD(read_nop4, 4)` | Defines `k_read_nop4`: the `asmread` loop with 4 `nop` per loop pass. That is 15 instructions per 256 B: 8 `ldp`, 4 `nop`, `add`, `cmp` and the branch. |
| 676 | `DEF_ASMREAD(read_nop8, 8)` | Defines `k_read_nop8`: the `asmread` loop with 8 `nop` per loop pass. That is 19 instructions per 256 B. |
| 677 | `DEF_ASMREAD(read_nop16, 16)` | Defines `k_read_nop16`: the `asmread` loop with 16 `nop` per loop pass. That is 27 instructions per 256 B. |
| 678 | `DEF_ASMREAD(read_nop32, 32)` | Defines `k_read_nop32`: the `asmread` loop with 32 `nop` per loop pass. That is 43 instructions per 256 B. |

### Function `k_read_sparse`: 128 B per loop pass, 4 loads and 9 `nop` (lines 680 to 701)

| Line | Source | Explanation |
|---:|---|---|
| 680 | `/* Step B5. Per 128 B: 4 ldp, 9 nop, add, cmp, b.lo. That is 16 instructions` | Comment: the kernel below belongs to step B5 of the file `handoff.md`, the specification of the first runner. Per 128 B it has 4 `ldp`, 9 `nop`, `add`, `cmp` and `b.lo`. That is 16 instructions. |
| 681 | ` * per 128 B, as the old read loop has, and no vector add. */` | Comment: the old read loop also has 16 instructions per 128 B. This kernel has the same instruction count, and it has no vector add. |
| 682 | `PLACE(read_sparse);` | `PLACE` adds the pad of the kernel `read_sparse`. It is the pad of `asmread`, 0 bytes (line 281). |
| 683 | `__attribute__((noinline)) static void k_read_sparse(const uint64_t *a, size_t n)` | Starts the function `k_read_sparse`, the kernel `read_sparse`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 684 | `{` | Opens the body of `k_read_sparse`. |
| 685 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 686 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. |
| 687 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text of the loop. |
| 688 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loop starts 4 bytes after the function start, at an address of 4 modulo 64 [Ref1]. |
| 689 | `        "ldp q0, q1, [%[p]]\n\t"` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current block of 128 B into `q0` and `q1`. |
| 690 | `        "ldp q2, q3, [%[p], #32]\n\t"` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 691 | `        "ldp q4, q5, [%[p], #64]\n\t"` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 692 | `        "ldp q6, q7, [%[p], #96]\n\t"` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. One loop pass has 4 load instructions. It reads 128 B, each byte once. Nothing uses the loaded values. |
| 693 | `        ".rept 9\n\tnop\n\t.endr\n\t"` | The assembler writes the instruction `nop` 9 times here. A `nop` does nothing. |
| 694 | `        "add %[p], %[p], #128\n\t"` | Moves the read pointer forward by 128 B. |
| 695 | `        "cmp %[p], %[end]\n\t"` | Compares the read pointer with `end`. |
| 696 | `        "b.lo 1b\n\t"` | Branches back to the label `1` while the pointer is below `end`. One loop pass is 16 instructions per 128 B: 4 `ldp`, 9 `nop`, `add`, `cmp` and the branch. |
| 697 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 698 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 699 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc");` | The clobber list: the vector registers `v0` to `v7`, memory and the condition flags. It names none of `v8` to `v15`. So gcc saves no register in this function. The listing of `bwx13` shows one `add` before the loop and one `ret` after it [Ref1]. |
| 700 | `}` | Ends the function `k_read_sparse`. |

### Macro `DEF_ASMWRITE`: the hand-written write loop, kernels `asmwrite` and `asmwrite2` (lines 702 to 728)

| Line | Source | Explanation |
|---:|---|---|
| 702 | `#define DEF_ASMWRITE(name) \` | Starts the macro `DEF_ASMWRITE(name)`. It defines one kernel function with a hand-written write loop. The backslash at the end of each line continues the macro on the next line. |
| 703 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 194). |
| 704 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. |
| 705 | `    { \` | Opens the body of the kernel function. |
| 706 | `        uint64_t *p = a; \` | `p`: the write pointer. It starts at `a`. |
| 707 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 708 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. gcc copies the text into the function. |
| 709 | `            "dup v0.2d, %[v]\n\t" \` | `dup` copies the 8-byte value `v` into both halves of the 16-byte vector register `v0`. It stands before the loop label, so it runs once per call. `%[v]` stands for the register that gcc chose for `v`. |
| 710 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loop of `k_asmwrite` starts at an address of 40 modulo 64 [Ref1]. |
| 711 | `            "stp q0, q0, [%[p]]\n\t" \` | `stp` stores two 16-byte vector registers to memory, which is 32 B. Here both are `q0`. This instruction writes the bytes 0 to 31 of the current block of 256 B. `%[p]` stands for the register of the write pointer `p`. |
| 712 | `            "stp q0, q0, [%[p], #32]\n\t" \` | Stores `q0` twice to the bytes 32 to 63 of the block. |
| 713 | `            "stp q0, q0, [%[p], #64]\n\t" \` | Stores `q0` twice to the bytes 64 to 95 of the block. |
| 714 | `            "stp q0, q0, [%[p], #96]\n\t" \` | Stores `q0` twice to the bytes 96 to 127 of the block. |
| 715 | `            "stp q0, q0, [%[p], #128]\n\t" \` | Stores `q0` twice to the bytes 128 to 159 of the block. |
| 716 | `            "stp q0, q0, [%[p], #160]\n\t" \` | Stores `q0` twice to the bytes 160 to 191 of the block. |
| 717 | `            "stp q0, q0, [%[p], #192]\n\t" \` | Stores `q0` twice to the bytes 192 to 223 of the block. |
| 718 | `            "stp q0, q0, [%[p], #224]\n\t" \` | Stores `q0` twice to the bytes 224 to 255 of the block. One loop pass has 8 store instructions. It writes 256 B, each byte once, in rising address order. The unrolling is part of this text: 8 `stp` per loop pass. |
| 719 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the write pointer forward by 256 B. |
| 720 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the write pointer with `end`. |
| 721 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 722 | `            : [p] "+r"(p) \` | `[p] "+r"(p)`: `p` is in a general register. The text reads it and changes it. |
| 723 | `            : [end] "r"(end), [v] "r"(v) \` | `end` and `v` are inputs in general registers. |
| 724 | `            : "v0", "memory", "cc"); \` | The clobber list: the text changes the vector register `v0`, memory and the condition flags. The calling rules do not require a function to keep `v0`. So gcc saves no register in this function. |
| 725 | `    }` | Ends the kernel function and the macro. |
| 726 | `DEF_ASMWRITE(asmwrite)` | Defines `k_asmwrite`, the kernel `asmwrite`. Machine code in `bwx13`: one loop pass is 11 instructions for 256 B: 8 `stp`, `add x0, x0, #0x100`, `cmp x0, x1` and `b.cc`. Before the loop stand the `add` that computes the end address and the `dup`. After it stands `ret` [Ref1]. The first touch uses `k_write` (line 562), not this loop. |
| 727 | `DEF_ASMWRITE(asmwrite2)` | Defines `k_asmwrite2`, the A/A copy of `asmwrite`. The listing of the CRB build of `bwx13` shows the same instruction text for both [Ref1]. |

### Macro `DEF_ASMCOPY`: the hand-written copy loop, kernels `asmcopy` and `asmcopy2` (lines 729 to 766)

| Line | Source | Explanation |
|---:|---|---|
| 729 | `#define DEF_ASMCOPY(name) \` | Starts the macro `DEF_ASMCOPY(name)`. It defines one kernel function with a hand-written copy loop. |
| 730 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 194). |
| 731 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. `noinline`: gcc must keep the function separate from its caller. |
| 732 | `    { \` | Opens the body of the kernel function. |
| 733 | `        uint64_t *dp = d; \` | `dp`: the write pointer in the destination. It starts at `d`. |
| 734 | `        const uint64_t *sp = s; \` | `sp`: the read pointer in the source. It starts at `s`. |
| 735 | `        const uint64_t *end = s + n; \` | `end`: the first address after the source range: `s` plus `n` words. |
| 736 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 737 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loop of `k_asmcopy` starts at an address of 52 modulo 64 [Ref1]. |
| 738 | `            "ldp q0, q1, [%[s]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. `%[s]` stands for the register of the read pointer `sp`. |
| 739 | `            "ldp q2, q3, [%[s], #32]\n\t" \` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 740 | `            "ldp q4, q5, [%[s], #64]\n\t" \` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 741 | `            "ldp q6, q7, [%[s], #96]\n\t" \` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 742 | `            "ldp q8, q9, [%[s], #128]\n\t" \` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 743 | `            "ldp q10, q11, [%[s], #160]\n\t" \` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 744 | `            "ldp q12, q13, [%[s], #192]\n\t" \` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 745 | `            "ldp q14, q15, [%[s], #224]\n\t" \` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 load instructions for 256 B. |
| 746 | `            "stp q0, q1, [%[d]]\n\t" \` | `stp` stores two 16-byte vector registers to memory: `q0` and `q1` to the bytes 0 to 31 of the current destination block. `%[d]` stands for the register of the write pointer `dp`. Each loaded register is stored once and has no other use. |
| 747 | `            "stp q2, q3, [%[d], #32]\n\t" \` | Stores `q2` and `q3` to the bytes 32 to 63 of the destination block. |
| 748 | `            "stp q4, q5, [%[d], #64]\n\t" \` | Stores `q4` and `q5` to the bytes 64 to 95 of the destination block. |
| 749 | `            "stp q6, q7, [%[d], #96]\n\t" \` | Stores `q6` and `q7` to the bytes 96 to 127 of the destination block. |
| 750 | `            "stp q8, q9, [%[d], #128]\n\t" \` | Stores `q8` and `q9` to the bytes 128 to 159 of the destination block. |
| 751 | `            "stp q10, q11, [%[d], #160]\n\t" \` | Stores `q10` and `q11` to the bytes 160 to 191 of the destination block. |
| 752 | `            "stp q12, q13, [%[d], #192]\n\t" \` | Stores `q12` and `q13` to the bytes 192 to 223 of the destination block. |
| 753 | `            "stp q14, q15, [%[d], #224]\n\t" \` | Stores `q14` and `q15` to the bytes 224 to 255 of the destination block. One loop pass has 8 store instructions for 256 B. The unrolling is part of this text: 8 `ldp` and 8 `stp` per loop pass. |
| 754 | `            "add %[s], %[s], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 755 | `            "add %[d], %[d], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 756 | `            "cmp %[s], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 757 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the read pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 758 | `            : [s] "+r"(sp), [d] "+r"(dp) \` | `sp` and `dp` are in general registers. The text reads them and changes them. |
| 759 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 760 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 761 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop, as in the read loop of line 670. |
| 762 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 763 | `    }` | Ends the kernel function and the macro. |
| 764 | `DEF_ASMCOPY(asmcopy)` | Defines `k_asmcopy`, the kernel `asmcopy`. Machine code in `bwx13`: one loop pass is 20 instructions for 256 B loaded and 256 B stored: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.cc`. The function saves `d8` to `d15` before the loop and loads them back after it [Ref1]. |
| 765 | `DEF_ASMCOPY(asmcopy2)` | Defines `k_asmcopy2`, the A/A copy of `asmcopy`. The listing of the CRB build of `bwx13` shows the same instruction text for both [Ref1]. |

### Function `k_asmcopy_c`: the machine code of the C copy loop as assembly text (lines 767 to 807)

| Line | Source | Explanation |
|---:|---|---|
| 767 | `/*` | Opens the comment about the kernel `asmcopy_c`. |
| 768 | ` * Step B2. asmcopy_c: the loop is the machine code of the C copy loop, from` | Comment: the kernel belongs to step B2 of the file `handoff.md`, the specification of the first runner. Its loop is the machine code of the C copy loop, written as assembly text. |
| 769 | ` * the listing "bw_new k_copy" of probe.txt: same instruction order, same` | Comment: the machine code comes from the listing `bw_new k_copy` of the file `probe.txt` [Ref3]. The loop has the same order of instructions. |
| 770 | ` * offsets, registers q16 to q31, and "cmp end, s; b.hi" as its loop end. The` | Comment: it also has the same offsets and the same registers `q16` to `q31`. Its loop end is `cmp end, s` followed by `b.hi`. |
| 771 | ` * three pointers are bound to x0, x1 and x2, the registers of that listing.` | Comment: the three pointers are bound to the registers `x0`, `x1` and `x2`, the registers of that listing. In the listing of `bwx13` the functions `k_asmcopy_c` and `k_copy` have the same instruction text [Ref1]. |
| 772 | ` */` | Ends the comment. |
| 773 | `PLACE(asmcopy_c);` | `PLACE` adds the pad `PAD_asmcopy_c`, which is 48 bytes with the default values (line 230). |
| 774 | `__attribute__((noinline)) static void k_asmcopy_c(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c`, the kernel `asmcopy_c`. It copies `n` 8-byte words from `s` to `d`. |
| 775 | `{` | Opens the body of `k_asmcopy_c`. |
| 776 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer. `register ... __asm__("x0")` binds this C variable to the register `x0` for the `asm` statement below. |
| 777 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 778 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 779 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 780 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loop starts 4 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 781 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 782 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 783 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 784 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 785 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 786 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 787 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 788 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 789 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. In this kernel the `add` stands before the stores. |
| 790 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 791 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 792 | `        "stp q29, q28, [%[d], #-224]\n\t"` | Stores `q29` and `q28` at the offset -224 from the moved write pointer. These are the bytes 32 to 63 of the destination block. |
| 793 | `        "stp q27, q26, [%[d], #-192]\n\t"` | Stores `q27` and `q26` at the offset -192: the bytes 64 to 95 of the destination block. |
| 794 | `        "stp q25, q24, [%[d], #-160]\n\t"` | Stores `q25` and `q24` at the offset -160: the bytes 96 to 127 of the destination block. |
| 795 | `        "stp q23, q22, [%[d], #-128]\n\t"` | Stores `q23` and `q22` at the offset -128: the bytes 128 to 159 of the destination block. |
| 796 | `        "stp q21, q20, [%[d], #-96]\n\t"` | Stores `q21` and `q20` at the offset -96: the bytes 160 to 191 of the destination block. |
| 797 | `        "stp q19, q18, [%[d], #-64]\n\t"` | Stores `q19` and `q18` at the offset -64: the bytes 192 to 223 of the destination block. |
| 798 | `        "stp q17, q16, [%[d], #-32]\n\t"` | Stores `q17` and `q16` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 799 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 800 | `        "b.hi 1b\n\t"` | `b.hi 1b` branches back to the label `1` while `end` is higher than the read pointer, as unsigned numbers. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 801 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 802 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 803 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 804 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. The calling rules do not require a function to keep `v16` to `v31`. So gcc saves no register in this function. |
| 805 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 806 | `}` | Ends the function `k_asmcopy_c`. |

### Function `k_asmcopy_c_add`: the same loop with both `add` after the stores (lines 808 to 844)

| Line | Source | Explanation |
|---:|---|---|
| 808 | `/* As asmcopy_c, but the two add stand after the 8 stp, and the 8 stp use the` | Comment: the kernel below is `asmcopy_c` with two changes. The two `add` instructions stand after the 8 `stp`. |
| 809 | ` * offsets 0 to 224, as in asmcopy. Registers stay q16 to q31. */` | Comment: the 8 `stp` use the offsets 0 to 224, as in `asmcopy`. The registers stay `q16` to `q31`. |
| 810 | `PLACE(asmcopy_c_add);` | `PLACE` adds the pad `PAD_asmcopy_c_add`, which is 48 bytes with the default values (line 233). |
| 811 | `__attribute__((noinline)) static void k_asmcopy_c_add(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_add`, the kernel `asmcopy_c_add`. It copies `n` 8-byte words from `s` to `d`. |
| 812 | `{` | Opens the body of `k_asmcopy_c_add`. |
| 813 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 814 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 815 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 816 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 817 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loop starts at an address of 52 modulo 64 [Ref1]. |
| 818 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 819 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 820 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 821 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 822 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 823 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 824 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 825 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 826 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 827 | `        "stp q29, q28, [%[d], #32]\n\t"` | Stores `q29` and `q28` to the bytes 32 to 63 of the destination block. |
| 828 | `        "stp q27, q26, [%[d], #64]\n\t"` | Stores `q27` and `q26` to the bytes 64 to 95 of the destination block. |
| 829 | `        "stp q25, q24, [%[d], #96]\n\t"` | Stores `q25` and `q24` to the bytes 96 to 127 of the destination block. |
| 830 | `        "stp q23, q22, [%[d], #128]\n\t"` | Stores `q23` and `q22` to the bytes 128 to 159 of the destination block. |
| 831 | `        "stp q21, q20, [%[d], #160]\n\t"` | Stores `q21` and `q20` to the bytes 160 to 191 of the destination block. |
| 832 | `        "stp q19, q18, [%[d], #192]\n\t"` | Stores `q19` and `q18` to the bytes 192 to 223 of the destination block. |
| 833 | `        "stp q17, q16, [%[d], #224]\n\t"` | Stores `q17` and `q16` to the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 834 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. Here both `add` instructions stand after the stores. |
| 835 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. |
| 836 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 837 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 838 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 839 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 840 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 841 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. gcc saves no register for them. |
| 842 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 843 | `}` | Ends the function `k_asmcopy_c_add`. |

### Function `k_asmcopy_c_reg`: the same loop with the registers `q0` to `q15` (lines 845 to 881)

| Line | Source | Explanation |
|---:|---|---|
| 845 | `/* As asmcopy_c, but with the registers q0 to q15 (q31 becomes q0, q30` | Comment: the kernel below is `asmcopy_c` with other registers: `q0` to `q15`. The register `q31` of `asmcopy_c` becomes `q0` here. |
| 846 | ` * becomes q1, and so on), and d8 to d15 named as clobbered, as in asmcopy. */` | Comment: `q30` becomes `q1`, and so on. The clobber list names `v8` to `v15`, as in `asmcopy`. So gcc saves `d8` to `d15`. |
| 847 | `PLACE(asmcopy_c_reg);` | `PLACE` adds the pad `PAD_asmcopy_c_reg`, which is 32 bytes with the default values (line 236). |
| 848 | `__attribute__((noinline)) static void k_asmcopy_c_reg(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_reg`, the kernel `asmcopy_c_reg`. It copies `n` 8-byte words from `s` to `d`. |
| 849 | `{` | Opens the body of `k_asmcopy_c_reg`. |
| 850 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 851 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 852 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 853 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 854 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loop starts 20 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 855 | `        "ldp q0, q1, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. |
| 856 | `        "ldp q2, q3, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 857 | `        "ldp q4, q5, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 858 | `        "ldp q6, q7, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 859 | `        "ldp q8, q9, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 860 | `        "ldp q10, q11, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 861 | `        "ldp q12, q13, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 862 | `        "ldp q14, q15, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 `ldp` for 256 B. |
| 863 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B, before the stores. |
| 864 | `        "stp q0, q1, [%[d]]\n\t"` | Stores `q0` and `q1` to the bytes 0 to 31 of the current destination block. |
| 865 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 866 | `        "stp q2, q3, [%[d], #-224]\n\t"` | Stores `q2` and `q3` at the offset -224 from the moved write pointer: the bytes 32 to 63 of the destination block. |
| 867 | `        "stp q4, q5, [%[d], #-192]\n\t"` | Stores `q4` and `q5` at the offset -192: the bytes 64 to 95 of the destination block. |
| 868 | `        "stp q6, q7, [%[d], #-160]\n\t"` | Stores `q6` and `q7` at the offset -160: the bytes 96 to 127 of the destination block. |
| 869 | `        "stp q8, q9, [%[d], #-128]\n\t"` | Stores `q8` and `q9` at the offset -128: the bytes 128 to 159 of the destination block. |
| 870 | `        "stp q10, q11, [%[d], #-96]\n\t"` | Stores `q10` and `q11` at the offset -96: the bytes 160 to 191 of the destination block. |
| 871 | `        "stp q12, q13, [%[d], #-64]\n\t"` | Stores `q12` and `q13` at the offset -64: the bytes 192 to 223 of the destination block. |
| 872 | `        "stp q14, q15, [%[d], #-32]\n\t"` | Stores `q14` and `q15` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 873 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 874 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 875 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 876 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 877 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 878 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call: the listing of `bwx13` shows 4 `stp` before the loop and 4 `ldp` after it [Ref1]. |
| 879 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 880 | `}` | Ends the function `k_asmcopy_c_reg`. |

### Stand-ins for a machine that is not AArch64 (lines 882 to 928)

| Line | Source | Explanation |
|---:|---|---|
| 882 | `#else` | `#else` of the `#if defined(__aarch64__)` of line 522. The compiler reads lines 883 to 927 only for a machine that is not AArch64. A build on CRB, an Arm machine, does not compile these lines. |
| 883 | `/*` | Opens the comment about the stand-ins. |
| 884 | ` * Stand-ins for a machine that is not AArch64: plain C loops that touch` | Comment: the stand-ins are for a machine that is not AArch64. They are plain C loops. |
| 885 | ` * exactly the same bytes as the real kernels. They exist only so that the` | Comment: each stand-in touches exactly the same bytes as the real kernel. The stand-ins have one purpose only. |
| 886 | ` * harness can be compiled and run on the development machine.` | Comment: the purpose: the program can be compiled and run on the development machine. |
| 887 | ` */` | Ends the comment. |
| 888 | `#define STANDIN 1` | `STANDIN` is 1 in this branch. It is 0 in the AArch64 branch (line 523). The header of the output then says that the kernels are stand-ins and that the rates mean nothing (line 3187). |
| 889 | `#define DEF_ASMREAD(name, nops) \` | Starts the stand-in form of the macro `DEF_ASMREAD(name, nops)`. It has the name and the arguments of the AArch64 macro of line 647, with a plain C loop over the same range. A build on CRB, an Arm machine, does not compile this branch. |
| 890 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel, as in the AArch64 branch. |
| 891 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range and `n` its length in 8-byte words. |
| 892 | `    { \` | Opens the body of the kernel function. |
| 893 | `        const volatile uint64_t *p = a; \` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 894 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 895 | `            (void)p[i]; \` | Reads word `i` and drops the value. The cast to `void` says that the value is not used. So the loop reads every word of the range once. The macro argument `nops` is not used in this branch. |
| 896 | `    }` | Ends the kernel function and the macro. |
| 897 | `#define DEF_ASMWRITE(name) \` | Starts the stand-in form of the macro `DEF_ASMWRITE(name)`, with a plain C loop. |
| 898 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 899 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores `v` to `n` 8-byte words, from the address `a` on. |
| 900 | `    { \` | Opens the body of the kernel function. |
| 901 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 902 | `            a[i] = v; \` | Stores `v` to word `i`. |
| 903 | `    }` | Ends the kernel function and the macro. |
| 904 | `#define DEF_ASMCOPY(name) \` | Starts the stand-in form of the macro `DEF_ASMCOPY(name)`, with a plain C loop. |
| 905 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 906 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. |
| 907 | `    { \` | Opens the body of the kernel function. |
| 908 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 909 | `            d[i] = s[i]; \` | Copies word `i` from the source to the destination. |
| 910 | `    }` | Ends the kernel function and the macro. |
| 911 | `DEF_ASMREAD(read, 0)` | Stand-in build only: defines `k_read` as the plain read loop of lines 889 to 896. This line and the 16 lines below define all 17 kernels of lines 531 to 880 from the three stand-in macros. |
| 912 | `DEF_ASMWRITE(write)` | Stand-in build only: defines `k_write` as the plain write loop of lines 897 to 903. In such a build this function also does the first touch (line 1802). |
| 913 | `DEF_ASMCOPY(copy)` | Stand-in build only: defines `k_copy` as the plain copy loop of lines 904 to 910. |
| 914 | `DEF_ASMREAD(asmread, 0)` | Stand-in build only: defines `k_asmread` as the plain read loop. |
| 915 | `DEF_ASMREAD(asmread2, 0)` | Stand-in build only: defines `k_asmread2` as the plain read loop. |
| 916 | `DEF_ASMREAD(read_nop4, 4)` | Stand-in build only: defines `k_read_nop4` as the plain read loop. The stand-in macro does not use the number 4. |
| 917 | `DEF_ASMREAD(read_nop8, 8)` | Stand-in build only: defines `k_read_nop8` as the plain read loop. The number 8 is not used. |
| 918 | `DEF_ASMREAD(read_nop16, 16)` | Stand-in build only: defines `k_read_nop16` as the plain read loop. The number 16 is not used. |
| 919 | `DEF_ASMREAD(read_nop32, 32)` | Stand-in build only: defines `k_read_nop32` as the plain read loop. The number 32 is not used. |
| 920 | `DEF_ASMREAD(read_sparse, 9)` | Stand-in build only: defines `k_read_sparse` as the plain read loop. The number 9 is not used. The real kernel also reads every byte of its range. |
| 921 | `DEF_ASMWRITE(asmwrite)` | Stand-in build only: defines `k_asmwrite` as the plain write loop. |
| 922 | `DEF_ASMWRITE(asmwrite2)` | Stand-in build only: defines `k_asmwrite2` as the plain write loop. |
| 923 | `DEF_ASMCOPY(asmcopy)` | Stand-in build only: defines `k_asmcopy` as the plain copy loop. |
| 924 | `DEF_ASMCOPY(asmcopy2)` | Stand-in build only: defines `k_asmcopy2` as the plain copy loop. |
| 925 | `DEF_ASMCOPY(asmcopy_c)` | Stand-in build only: defines `k_asmcopy_c` as the plain copy loop. |
| 926 | `DEF_ASMCOPY(asmcopy_c_add)` | Stand-in build only: defines `k_asmcopy_c_add` as the plain copy loop. |
| 927 | `DEF_ASMCOPY(asmcopy_c_reg)` | Stand-in build only: defines `k_asmcopy_c_reg` as the plain copy loop. |
| 928 | `#endif` | Ends the `#if` of line 522. |

### Kernels of round 3 (version `bwx10`): the comment and the pads (lines 929 to 961)

| Line | Source | Explanation |
|---:|---|---|
| 929 | `/* bwx10+ */` | Comment: a marker. A block of text that the version `bwx10` added starts here. The marker of line 1071 ends the block. |
| 931 | `/*` | Opens the comment about the kernels of round 3. |
| 932 | ` * Kernels of round 3. They stand after every kernel of bwx8, so those keep` | Comment: the kernels below are those of round 3, a round of work on the program (line 93). It is not a round of the option `--rounds`. They stand after every kernel of `bwx8`. |
| 933 | ` * their place. Each one is a read kernel (T_READ) with the loop start at 20` | Comment: so the kernels of `bwx8` keep their place in the binary. Each new kernel is a read kernel, with the type `T_READ`. Its loop must start at 20 modulo 64. |
| 934 | ` * modulo 64, the loop offset of asmread in the accepted build.` | Comment: 20 modulo 64 is the loop offset of `asmread` in the accepted build. The accepted build is the CRB build whose machine-code listing passed the check script. |
| 935 | ` *` | Comment: an empty line of the comment. |
| 936 | ` * read_pf256, read_pf512, read_pf1024, read_pf2048 have the frame of asmread` | Comment: the kernels `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048` (lines 1010 to 1013) have the frame of `asmread`. The frame is the code at the start of a function that saves registers. |
| 937 | ` * (d8-d15 are saved), so HEAD is 20 and the pad is the pad of asmread.` | Comment: in that frame `d8` to `d15` are saved. So `HEAD`, the number of bytes of code before the loop, is 20, and these kernels take the pad of `asmread`. |
| 938 | ` * read_1pl names v0-v3 only, so gcc saves nothing: HEAD is 4, as read_sparse` | Comment: `read_1pl` names only `v0` to `v3` as changed. So gcc saves nothing. `HEAD` is then 4, as for `read_sparse`. |
| 939 | ` * has it. HEAD_read_1pl is a guess until the listing of the CRB build` | Comment: `HEAD_read_1pl` is a guess until the listing of the CRB build confirms it. The listing of the CRB build of `bwx13` confirms it: 4 bytes of code stand before the loop of `k_read_1pl` [Ref1]. |
| 940 | ` * confirms it (check_listing10.py checks the loop offset).` | Comment: the script `check_listing10.py` in the code folder `bwx10-2026-11-15` checks the loop offset. |
| 941 | ` */` | Ends the comment. |
| 942 | `#ifndef PAD_read_pf256` | Compiles line 943 only when the build command has not defined `PAD_read_pf256`. A `-D` option of the compiler could give another value. The CRB build of `bwx13` has no `-D` option [Ref2]. |
| 943 | `#define PAD_read_pf256 PAD_asmread` | `PAD_read_pf256`: the pad of `asmread`, which is 0 bytes. |
| 944 | `#endif` | Ends the `#ifndef` of line 942. |
| 945 | `#ifndef PAD_read_pf512` | Compiles line 946 only when the build command has not defined `PAD_read_pf512`. |
| 946 | `#define PAD_read_pf512 PAD_asmread` | `PAD_read_pf512`: the pad of `asmread`, which is 0 bytes. |
| 947 | `#endif` | Ends the `#ifndef` of line 945. |
| 948 | `#ifndef PAD_read_pf1024` | Compiles line 949 only when the build command has not defined `PAD_read_pf1024`. |
| 949 | `#define PAD_read_pf1024 PAD_asmread` | `PAD_read_pf1024`: the pad of `asmread`, which is 0 bytes. |
| 950 | `#endif` | Ends the `#ifndef` of line 948. |
| 951 | `#ifndef PAD_read_pf2048` | Compiles line 952 only when the build command has not defined `PAD_read_pf2048`. |
| 952 | `#define PAD_read_pf2048 PAD_asmread` | `PAD_read_pf2048`: the pad of `asmread`, which is 0 bytes. |
| 953 | `#endif` | Ends the `#ifndef` of line 951. |
| 954 | `#define LOOP_read_1pl 20` | `LOOP_read_1pl` is 20: the planned address of the loop start of `read_1pl`, modulo 64. |
| 955 | `#ifndef HEAD_read_1pl` | Compiles line 956 only when the build command has not defined `HEAD_read_1pl`. |
| 956 | `#define HEAD_read_1pl 4` | `HEAD_read_1pl` is 4: the number of bytes between the function start and the loop start. That is one instruction of 4 bytes. Listing of the CRB build of `bwx13`: `k_read_1pl` starts at `0x56d0`, which is 16 modulo 64. Its loop starts at `0x56d4`, which is 20 modulo 64 [Ref1]. |
| 957 | `#endif` | Ends the `#ifndef` of line 955. |
| 958 | `#ifndef PAD_read_1pl` | Compiles line 959 only when the build command has not defined `PAD_read_1pl`. |
| 959 | `#define PAD_read_1pl PADOF(LOOP_read_1pl, HEAD_read_1pl)` | `PAD_read_1pl` is `PADOF(20, 4)` with the default values. `PADOF` (line 195) computes (20 - 4) modulo 64, which is 16. `PLACE(read_1pl)` (line 1018) uses this pad. So the function starts at 16 modulo 64 and its loop at 20 modulo 64. In the CRB binary of `bwx13` the kernel `read_1pl` has the same loop offset as `asmread`: 20 [Ref1]. |
| 960 | `#endif` | Ends the `#ifndef` of line 958. |

### Macro `DEF_READ_PF`: the `asmread` loop with four prefetch instructions (lines 962 to 1014)

| Line | Source | Explanation |
|---:|---|---|
| 962 | `#if defined(__aarch64__)` | Opens a second block of AArch64 kernels. Its `#else` is at line 1036 and its `#endif` at line 1053. The CRB binary of `bwx13` holds this first branch: the listing shows the `prfm` and `ldr` instructions of its kernels [Ref1]. |
| 963 | `/*` | Opens the comment about the macro `DEF_READ_PF`. |
| 964 | ` * DEF_READ_PF(name, d0, d1, d2, d3): the loop of asmread (8 ldp of q` | Comment: `DEF_READ_PF(name, d0, d1, d2, d3)` defines a kernel with the loop of `asmread`: 8 `ldp` of `q` registers per 256 B. |
| 965 | ` * registers per 256 B, same registers, same clobbers) plus four software` | Comment: the loop has the same registers and the same clobber list as `asmread`. The macro adds four software prefetches. |
| 966 | ` * prefetches per iteration, one per 64 B line, after the 8 ldp and before the` | Comment: the four prefetches run once per loop pass, one per 64 B line. A 64 B line here is a block of 64 B of memory, a cache line. They stand after the 8 `ldp` and before the `add`. |
| 967 | ` * add. d0 is the prefetch distance D in bytes ahead of the block that the` | Comment: `d0` is the prefetch distance D in bytes: the offset of the first prefetched 64 B line from the start of the block that the loop pass loads. |
| 968 | ` * iteration loads. d1, d2, d3 are D + 64, D + 128, D + 192.` | Comment: `d1`, `d2` and `d3` are D + 64, D + 128 and D + 192. So the four prefetches name four neighbour 64 B lines. |
| 969 | ` *` | Comment: an empty line of the comment. |
| 970 | ` * prfm pldl1keep asks for the line in the first-level data cache (PLD: for a` | Comment: the instruction `prfm pldl1keep` asks the CPU to bring a 64 B line into the first-level data cache. It loads no data into a register. `PLD` in its name means: for a load. |
| 971 | ` * load, L1: first level, KEEP: normal, not streaming). The form` | Comment: `L1` means the first cache level. `KEEP` means normal use, not streaming. The sentence about the address form starts here. |
| 972 | ` * [base, #offset] needs an offset that is a multiple of 8 from 0 to 32760.` | Comment: the address form `[base, #offset]` needs an offset that is a multiple of 8 from 0 to 32760. |
| 973 | ` * In the last iterations of a pass the prefetch address lies past the end of` | Comment: in the last loop passes of a call the prefetch address lies past the end of the range. |
| 974 | ` * the range, and for the last range of the buffer past the end of the` | Comment: for the last range of the buffer the prefetch address lies past the end of the buffer. |
| 975 | ` * buffer. That is allowed: prfm never faults, not even on an address that is` | Comment: that is allowed. A `prfm` never causes a fault, not even with an address that is not mapped. |
| 976 | ` * not mapped. It reads no data, so the kernel touches the same bytes as` | Comment: a `prfm` reads no data. So the kernel touches the same bytes as `asmread`. |
| 977 | ` * asmread.` | Comment: the last word of the sentence of line 976. |
| 978 | ` */` | Ends the comment. |
| 979 | `#define DEF_READ_PF(name, d0, d1, d2, d3) \` | Starts the macro `DEF_READ_PF(name, d0, d1, d2, d3)`. Its text is the text of `DEF_ASMREAD` (line 647) with four `prfm` instructions in place of the `nop` text. |
| 980 | `    _Static_assert((d0) % 8 == 0 && (d0) >= 0 && (d1) == (d0) + 64 && (d2) == (d0) + 128 && (d3) == (d0) + 192 && \` | `_Static_assert` stops the compilation when the four offsets break the rule of the comment. This line tests that `d0` is a multiple of 8 and not negative, and that `d1`, `d2` and `d3` are `d0` plus 64, 128 and 192. |
| 981 | `                   (d3) <= 32760, "prfm offsets: multiples of 8 from 0 to 32760, one per 64 B line"); \` | Continues the test of line 980: `d3` must be at most 32760. The text in quotes is the error message of the compiler. |
| 982 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function. For the four kernels below it is 0 bytes (lines 942 to 953). |
| 983 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 984 | `    { \` | Opens the body of the kernel function. |
| 985 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 986 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 987 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 988 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loops of the four kernels start at 20 modulo 64, the loop offset of `k_asmread` [Ref1]. |
| 989 | `            "ldp q0, q1, [%[p]]\n\t" \` | Loads the bytes 0 to 31 of the current block of 256 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 990 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 991 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 992 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. |
| 993 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 994 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 995 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 996 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once. Nothing uses the loaded values. |
| 997 | `            "prfm pldl1keep, [%[p], #" #d0 "]\n\t" \` | The first prefetch: `prfm pldl1keep` asks the CPU to bring the 64 B line at the address `p` plus `d0` into the first-level data cache. `#d0` puts the macro argument into the text as a number. The instruction loads no data into a register. |
| 998 | `            "prfm pldl1keep, [%[p], #" #d1 "]\n\t" \` | The second prefetch: the 64 B line at the address `p` plus `d1`, which is 64 B after the first one. |
| 999 | `            "prfm pldl1keep, [%[p], #" #d2 "]\n\t" \` | The third prefetch: the 64 B line at the address `p` plus `d2`. |
| 1000 | `            "prfm pldl1keep, [%[p], #" #d3 "]\n\t" \` | The fourth prefetch: the 64 B line at the address `p` plus `d3`. So one loop pass prefetches four neighbour 64 B lines, which are 256 B. |
| 1001 | `            "add %[p], %[p], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 1002 | `            "cmp %[p], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 1003 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. One loop pass is 15 instructions per 256 B: 8 `ldp`, 4 `prfm`, `add`, `cmp` and the branch. |
| 1004 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 1005 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 1006 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 1007 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop, as in `asmread`. |
| 1008 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 1009 | `    }` | Ends the kernel function and the macro. |
| 1010 | `DEF_READ_PF(read_pf256, 256, 320, 384, 448)` | Defines `k_read_pf256`, the kernel `read_pf256`. The number in the name is `d0` in bytes. The four prefetch offsets are 256, 320, 384 and 448: the four 64 B lines of the block after the current one. |
| 1011 | `DEF_READ_PF(read_pf512, 512, 576, 640, 704)` | Defines `k_read_pf512`, the kernel `read_pf512`. The four prefetch offsets are 512, 576, 640 and 704: the block 512 B after the start of the current one. |
| 1012 | `DEF_READ_PF(read_pf1024, 1024, 1088, 1152, 1216)` | Defines `k_read_pf1024`, the kernel `read_pf1024`. The four prefetch offsets are 1024, 1088, 1152 and 1216. |
| 1013 | `DEF_READ_PF(read_pf2048, 2048, 2112, 2176, 2240)` | Defines `k_read_pf2048`, the kernel `read_pf2048`. The four prefetch offsets are 2048, 2112, 2176 and 2240. |

### Function `k_read_1pl`: one load of 16 B per 64 B line (lines 1015 to 1035)

| Line | Source | Explanation |
|---:|---|---|
| 1015 | `/* read_1pl, "one load per line". Per 256 B: four loads of 16 B, one at the` | Comment: the name `read_1pl` means one load per line. A line here is a 64 B line, a block of 64 B of memory (a cache line). Per 256 B the loop has four loads of 16 B. |
| 1016 | ` * start of each 64 B line, then add, cmp, b.lo. It reads bytes 0 to 15 of` | Comment: one load stands at the start of each 64 B line. Then come `add`, `cmp` and `b.lo`. The sentence about the bytes starts here. |
| 1017 | ` * every line and no other byte. */` | Comment: the kernel reads the bytes 0 to 15 of every 64 B line and no other byte. |
| 1018 | `PLACE(read_1pl);` | `PLACE(read_1pl)` adds a pad of 16 bytes (line 959). In the CRB binary of `bwx13` the function starts at `0x56d0`, which is 16 modulo 64 [Ref1]. |
| 1019 | `__attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)` | Starts the function `k_read_1pl`, the kernel `read_1pl`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. `noinline` forbids gcc to merge it into its caller. |
| 1020 | `{` | Opens the body of `k_read_1pl`. |
| 1021 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 1022 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx13`: `add x1, x0, x1, lsl #3`. It is the only instruction before the loop [Ref1]. |
| 1023 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text of the loop, as in `DEF_ASMREAD` (line 653). |
| 1024 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loop starts at an address of 20 modulo 64 [Ref1]. |
| 1025 | `        "ldr q0, [%[p]]\n\t"` | `ldr` loads 16 B from memory into one vector register: the bytes 0 to 15 of the current block of 256 B into `q0`. These are the first 16 B of the first 64 B line of the block. |
| 1026 | `        "ldr q1, [%[p], #64]\n\t"` | Loads the bytes 64 to 79 of the block into `q1`: the first 16 B of the second 64 B line. |
| 1027 | `        "ldr q2, [%[p], #128]\n\t"` | Loads the bytes 128 to 143 of the block into `q2`: the first 16 B of the third 64 B line. |
| 1028 | `        "ldr q3, [%[p], #192]\n\t"` | Loads the bytes 192 to 207 of the block into `q3`: the first 16 B of the fourth 64 B line. So one loop pass loads 64 B of its block of 256 B: the bytes 0 to 15 of each 64 B line. It does not load the other 48 B of a 64 B line. `asmread` has 8 load instructions of 32 B per loop pass. This kernel has 4 load instructions of 16 B per loop pass. Nothing uses the loaded values: no instruction of the loop takes `q0` to `q3` as an input. |
| 1029 | `        "add %[p], %[p], #256\n\t"` | `add` moves the read pointer forward by 256 B. |
| 1030 | `        "cmp %[p], %[end]\n\t"` | `cmp` compares the read pointer with `end`. |
| 1031 | `        "b.lo 1b\n\t"` | `b.lo 1b` repeats the loop while the pointer is below `end`. One loop pass is 7 instructions per block of 256 B: 4 `ldr`, `add`, `cmp` and the branch. The worker counts the bytes outside the kernel. For each call it adds the size of the range that it passed to the kernel (line 1852, line 1868). So the rate of `read_1pl` counts 256 B per loop pass, although the loop pass loads 64 B. |
| 1032 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 1033 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 1034 | `        : "v0", "v1", "v2", "v3", "memory", "cc");` | The clobber list. Of the vector registers it names only `v0` to `v3`. The calling rules do not require a function to keep these registers. So gcc saves nothing. In `bwx13` the whole function has 9 instructions: 1 before the loop, 7 in the loop, then `ret` [Ref1]. `asmread` differs here: it saves `d8` to `d15` and loads them back at each call. |
| 1035 | `}` | Ends the function `k_read_1pl`. |

### Stand-ins of the kernels of round 3 (lines 1036 to 1054)

| Line | Source | Explanation |
|---:|---|---|
| 1036 | `#else` | `#else` of the `#if` of line 962. The compiler reads the lines up to line 1052 only for a machine that is not AArch64. |
| 1037 | `/* Stand-ins. A prefetch touches no byte, so the stand-in of a read_pf kernel` | Comment: the stand-ins of the kernels of this block. A prefetch touches no byte. |
| 1038 | ` * is the stand-in of asmread. The stand-in of read_1pl reads the first two` | Comment: so the stand-in of a `read_pf` kernel is the stand-in of `asmread` (lines 889 to 896). The sentence about `read_1pl` starts here. |
| 1039 | ` * words (16 B) of every 64 B line, as the real kernel does. */` | Comment: the stand-in of `read_1pl` reads the first two words, which are 16 B, of every 64 B line. The real kernel reads the same bytes. |
| 1040 | `DEF_ASMREAD(read_pf256, 0)` | Stand-in build only: defines `k_read_pf256` as the plain read loop of lines 889 to 896, which reads every word of the range. |
| 1041 | `DEF_ASMREAD(read_pf512, 0)` | Stand-in build only: defines `k_read_pf512` as the plain read loop. |
| 1042 | `DEF_ASMREAD(read_pf1024, 0)` | Stand-in build only: defines `k_read_pf1024` as the plain read loop. |
| 1043 | `DEF_ASMREAD(read_pf2048, 0)` | Stand-in build only: defines `k_read_pf2048` as the plain read loop. |
| 1044 | `PLACE(read_1pl);` | `PLACE` adds the pad of `read_1pl`, as in the AArch64 branch. |
| 1045 | `__attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)` | Starts the stand-in function `k_read_1pl`. A build on CRB, an Arm machine, does not compile it. |
| 1046 | `{` | Opens the body of the stand-in. |
| 1047 | `    const volatile uint64_t *p = a;` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 1048 | `    for (size_t i = 0; i < n; i += 8) {` | A loop over the range in steps of 8 words, which are 64 B. |
| 1049 | `        (void)p[i];` | Reads the first word of the 64 B line and drops the value. |
| 1050 | `        (void)p[i + 1];` | Reads the second word of the 64 B line and drops the value. So the loop reads 16 B of every 64 B. |
| 1051 | `    }` | Ends the loop of line 1048. |
| 1052 | `}` | Ends the stand-in function `k_read_1pl`. |
| 1053 | `#endif` | Ends the `#if` of line 962. |

### Pad after the kernels of round 3 (lines 1055 to 1073)

| Line | Source | Explanation |
|---:|---|---|
| 1055 | `/*` | Opens the comment about the placement of the code after the kernels. It explains lines 1067 to 1070. |
| 1056 | ` * Placement of the code after the kernels. In the accepted build of bwx8 the` | Comment: the topic is the placement of the code that follows the kernels. The comment first gives a fact about the accepted build of `bwx8`. |
| 1057 | ` * last kernel ends at 0x4a14 (ref-bwx8/listing.txt), so the function after` | Comment: in that build the last kernel ends at the address `0x4a14`. The comment names the file `ref-bwx8/listing.txt` as its source. |
| 1058 | ` * the kernels starts at 0x4a18: 24 modulo 64. That function is call(), or` | Comment: so the function after the kernels starts at `0x4a18` in that build, which is 24 modulo 64. That function is `call` (line 1647). The build record of CRB reports `call=24` for `bwx13`: its function `call` also starts at 24 modulo 64 [Ref2]. |
| 1059 | ` * read_smaps() if gcc inlines every call of call(). The pad below gives it` | Comment: if gcc merges `call` into all of its callers, the function after the kernels is `read_smaps` (line 1671). The pad below gives this function the same start address modulo 64 in `bwx10`. |
| 1060 | ` * the same start modulo 64 in bwx10. No code is added between call() and the` | Comment: no code was added between `call` and the end of `timed_sequence` (line 2151), a function of the trial mode. |
| 1061 | ` * end of timed_sequence(), so that code keeps the placement modulo 64 that it` | Comment: so the code from `call` to the end of `timed_sequence` keeps its placement modulo 64. |
| 1062 | ` * has in bwx8. build10.sh prints the placement of both binaries.` | Comment: it is the placement that this code has in `bwx8`. The script `build10.sh` in the code folder `bwx10-2026-11-15` prints the placement of both binaries. |
| 1063 | ` * The value 24 holds for the AArch64 build with the accepted compiler. On` | Comment: the value 24 holds for the AArch64 build with the accepted compiler. |
| 1064 | ` * another machine it is only a pad: test_runner10.py builds one copy with the` | Comment: on another machine the value is only a pad. The script `test_runner10.py` in the code folder `bwx10-2026-11-15` builds one copy with another value. |
| 1065 | ` * local value to check the method.` | Comment: that other value is the value of the local machine. The copy checks the method. |
| 1066 | ` */` | Ends the comment. |
| 1067 | `#ifndef PAD_after_kernels` | Compiles line 1068 only when the build command has not defined `PAD_after_kernels`. |
| 1068 | `#define PAD_after_kernels 24` | `PAD_after_kernels` is 24. A `-D` option could give another value, and the CRB build of `bwx13` has none [Ref2]. |
| 1069 | `#endif` | Ends the `#ifndef` of line 1067. |
| 1070 | `PLACE(after_kernels);` | `PLACE(after_kernels)` fills the code up to a multiple of 64 bytes and then adds 24 bytes of value 0. No function with this name exists: the macro only places the code that follows. In this file more kernels follow this pad, from line 1074 on. So this pad does not stand directly before `call`. The last pad with the same value does that (lines 1599 to 1602). |
| 1071 | `/* bwx10- */` | Comment: a marker. The block that line 929 opened ends here. |
| 1072 | `/* bwx11+ */` | Comment: a marker. A block of text that the version `bwx11` added starts here. The marker of line 1107 ends the block. The block holds the kernels `read_nop64`, `read_nop96` and `read_nop128`. |

### Kernels of round 4 (version `bwx11`): `read_nop64`, `read_nop96`, `read_nop128` (lines 1074 to 1096)

| Line | Source | Explanation |
|---:|---|---|
| 1074 | `/*` | Opens the comment about the kernels of round 4. |
| 1075 | ` * Kernels of round 4. They stand after every kernel of bwx10, so those keep` | Comment: the kernels below are those of round 4, the round of work that produced `bwx11` (line 67). It is not a round of the option `--rounds`. They stand after every kernel of `bwx10`. |
| 1076 | ` * their place. Each one is the asmread loop with more nop instructions` | Comment: so the kernels of `bwx10` keep their place in the binary. Each new kernel is the `asmread` loop with more `nop` instructions. |
| 1077 | ` * between the 8 ldp and the add: 64, 96 and 128. The frame is the frame of` | Comment: the `nop` instructions stand between the 8 `ldp` and the `add` of the read address: 64, 96 or 128 of them. The sentence about the frame starts here. |
| 1078 | ` * asmread (d8-d15 are saved), so the pad is the pad of asmread and the loop` | Comment: the frame is the frame of `asmread`: the function saves `d8` to `d15` before its loop. So each kernel gets the pad of `asmread`. |
| 1079 | ` * starts at 20 modulo 64 (check_listing11.py checks it). DEF_ASMREAD is the` | Comment: the loop then starts at 20 modulo 64. The script `check_listing11.py` in the code folder `bwx11-2026-11-15` checks it. The listing of the CRB build of `bwx13` shows 20 modulo 64 for the three loops [Ref1]. |
| 1080 | ` * macro of the kernels of bwx8: the asm text on AArch64, the stand-in loop on` | Comment: `DEF_ASMREAD` is the macro of the kernels of `bwx8`. On AArch64 it gives the assembly text (line 647). |
| 1081 | ` * another machine. A nop touches no byte, so the stand-in is the stand-in of` | Comment: on another machine it gives the stand-in loop (line 889). A `nop` touches no byte. |
| 1082 | ` * asmread.` | Comment: so the stand-in of these kernels is the stand-in of `asmread`. |
| 1083 | ` */` | Ends the comment. |
| 1084 | `#ifndef PAD_read_nop64` | Compiles line 1085 only when the build command has not defined `PAD_read_nop64`. |
| 1085 | `#define PAD_read_nop64 PAD_asmread` | `PAD_read_nop64`: the value of `PAD_asmread`, which is 0 (line 245). So `PLACE` (line 194) lets the function start on a 64 B boundary. |
| 1086 | `#endif` | Ends the `#ifndef` of line 1084. |
| 1087 | `#ifndef PAD_read_nop96` | Compiles line 1088 only when the build command has not defined `PAD_read_nop96`. |
| 1088 | `#define PAD_read_nop96 PAD_asmread` | `PAD_read_nop96`: the value of `PAD_asmread`, which is 0 (line 245). The CRB build of `bwx13` has no `-D` option that could change it [Ref2]. |
| 1089 | `#endif` | Ends the `#ifndef` of line 1087. |
| 1090 | `#ifndef PAD_read_nop128` | Compiles line 1091 only when the build command has not defined `PAD_read_nop128`. |
| 1091 | `#define PAD_read_nop128 PAD_asmread` | `PAD_read_nop128`: the value of `PAD_asmread`, which is 0 (line 245). |
| 1092 | `#endif` | Ends the `#ifndef` of line 1090. |
| 1093 | `DEF_ASMREAD(read_nop64, 64)` | Creates the kernel `read_nop64` from the macro `DEF_ASMREAD` (lines 647 to 672): the `asmread` loop with 64 `nop` instructions per 256 B. That is 75 instructions per loop pass. |
| 1094 | `DEF_ASMREAD(read_nop96, 96)` | Creates the function `k_read_nop96` from the macro `DEF_ASMREAD` (lines 647 to 672) with 96 `nop`. One loop pass: 8 `ldp` load 256 B into `q0` to `q15`, each byte once, and nothing uses the loaded values. Then come 96 `nop`, the `add` of the read address, `cmp` and the branch. That is 107 instructions (428 B of code) per 256 B of data. Listing of the CRB build of `bwx13` [Ref1]: the function starts at the address `0x58c0` (0 modulo 64) and the loop at `0x58d4` (20 modulo 64), the loop offset of `k_asmread`. Once per call, outside the loop, 4 `stp` save `d8` to `d15`, one `add` computes the end address, 4 `ldp` load `d8` to `d15` back, and `ret` returns. |
| 1095 | `DEF_ASMREAD(read_nop128, 128)` | Creates the kernel `read_nop128`: the `asmread` loop with 128 `nop` instructions per 256 B. That is 139 instructions per loop pass. |

### Second pad after the kernels (version `bwx11`) (lines 1097 to 1109)

| Line | Source | Explanation |
|---:|---|---|
| 1097 | `/*` | Opens the comment about the second pad. |
| 1098 | ` * The pad after the kernels, once more. The pad of bwx10 above now stands` | Comment: the pad after the kernels is needed once more. The pad of `bwx10` (line 1070) now stands before the kernels of round 4. |
| 1099 | ` * before the kernels of round 4, so it no longer places call(). This pad has` | Comment: so the pad of `bwx10` no longer sets the start address of `call`. |
| 1100 | ` * the same value, and the function after the kernels starts at that value` | Comment: the new pad has the same value. The function after the kernels then starts at that value modulo 64. |
| 1101 | ` * modulo 64, as in bwx10 and in bwx8. build11.sh prints the placement.` | Comment: that is the start address modulo 64 that this function has in `bwx10` and in `bwx8`. The script `build11.sh` in the code folder `bwx11-2026-11-15` prints the placement. |
| 1102 | ` */` | Ends the comment. |
| 1103 | `#ifndef PAD_after_kernels11` | Compiles line 1104 only when the build command has not defined `PAD_after_kernels11`. |
| 1104 | `#define PAD_after_kernels11 PAD_after_kernels` | `PAD_after_kernels11` gets the value of `PAD_after_kernels`, which is 24 (line 1068). |
| 1105 | `#endif` | Ends the `#ifndef` of line 1103. |
| 1106 | `PLACE(after_kernels11);` | `PLACE(after_kernels11)` pads the code up to a 64 B boundary and then adds 24 bytes of value 0. In `bwx11.c` this pad sets the start address of the function that follows the kernels. In this file more kernels follow here, and the pad of line 1602 sets that start address. |
| 1107 | `/* bwx11- */` | Comment: a marker. The block that line 1072 opened ends here. |
| 1108 | `/* bwx12+ */` | Comment: a marker. A block of text that the version `bwx12` added starts here. The marker of line 1481 ends the block. |

### Kernels of round 5 (version `bwx12`): loop offsets, head sizes and pads (lines 1110 to 1219)

| Line | Source | Explanation |
|---:|---|---|
| 1110 | `/*` | Opens the comment about the placement of the kernels of round 5. |
| 1111 | ` * Kernels of round 5. They stand after every kernel of bwx11, so those keep` | Comment: the kernels below are those of round 5, a round of work on the program (line 34). It is not a round of the option `--rounds`. There are 26 of them (line 40). They stand after every kernel of `bwx11`. |
| 1112 | ` * their place. The pad of each one puts the loop start at the loop offset` | Comment: so the kernels of `bwx11` keep their place in the binary. The pad of each new kernel puts its loop start at a planned address modulo 64. |
| 1113 | ` * modulo 64 of its original in the accepted build: 20 for a read kernel (the` | Comment: the planned address is the loop offset that the original kernel has in the accepted build. For a read kernel it is 20, the loop offset of `asmread`. |
| 1114 | ` * offset of asmread), 40 for a write kernel (asmwrite), 52 for a copy kernel` | Comment: for a write kernel it is 40, the loop offset of `asmwrite`. For a copy kernel it is 52, the loop offset of `asmcopy`. |
| 1115 | ` * (asmcopy). PAD = (LOOP - HEAD) mod 64, where HEAD is the number of bytes` | Comment: the rule is `PAD = (LOOP - HEAD) mod 64`. `LOOP` is the planned loop offset. `HEAD` is the number of bytes of code between the function start and the loop start. |
| 1116 | ` * between the function start and the loop start. Every HEAD below is a guess` | Comment: every `HEAD` value below is a guess until the listing of the CRB build confirms it. |
| 1117 | ` * until the listing of the CRB build confirms it (check_listing12.py checks` | Comment: the script `check_listing12.py` in the code folder `bwx12-2026-11-15` checks the loop offset. The listing of the CRB binary of `bwx13` shows the planned loop offset for each of the 26 kernels [Ref1]. |
| 1118 | ` * the loop offset). Override one with -DHEAD_<group>=N or -DPAD_<name>=N.` | Comment: the build can replace one value with `-DHEAD_<group>=N` or `-DPAD_<name>=N`. |
| 1119 | ` *` | Comment: an empty line of the comment. |
| 1120 | ` *   read_nopN       frame of asmread (gcc saves d8-d15): HEAD 20, pad of asmread.` | Comment: the `read_nop` kernels have the frame of `asmread`: gcc saves `d8` to `d15`. So `HEAD` is 20, and they take the pad of `asmread`. |
| 1121 | ` *   read_daddK      frame of asmread, then 8 movi: HEAD 20 + 32 = 52.` | Comment: the `read_dadd` kernels have the frame of `asmread` and then 8 `movi` instructions of 4 bytes each. So `HEAD` is 20 + 32 = 52. |
| 1122 | ` *   read_iadd16     frame of asmread, then 16 movi: HEAD 20 + 64 = 84.` | Comment: `read_iadd16` has the frame of `asmread` and then 16 `movi` instructions. So `HEAD` is 20 + 64 = 84. |
| 1123 | ` *   read_spN        no frame, as read_sparse: HEAD 4. read_sparse itself has` | Comment: the `read_sp` kernels have no frame, as `read_sparse`. So `HEAD` is 4. The sentence about `read_sparse` starts here. |
| 1124 | ` *                   its loop at 4 modulo 64 (pad of asmread, HEAD 4). The new` | Comment: `read_sparse` itself has its loop at 4 modulo 64. It takes the pad of `asmread`, which is 0, and its `HEAD` is 4. |
| 1125 | ` *                   kernels get 20, the offset of asmread.` | Comment: the new `read_sp` kernels get the loop offset 20, the offset of `asmread`. |
| 1126 | ` *                   -DHEAD_read_sp=20 gives them the offset of read_sparse.` | Comment: a build with `-DHEAD_read_sp=20` gives them the loop offset of `read_sparse`: the pad is then 0, and the loop starts at 4 modulo 64. |
| 1127 | ` *   read_1pl_nop96  no frame, as read_1pl: HEAD 4, pad of read_1pl.` | Comment: `read_1pl_nop96` has no frame, as `read_1pl`. So `HEAD` is 4, and it takes the pad of `read_1pl`. |
| 1128 | ` *   write_nopN      as asmwrite (end pointer, dup): pad of asmwrite.` | Comment: the `write_nop` kernels start as `asmwrite` does, with the computation of the end pointer and the `dup`. So they take the pad of `asmwrite`. |
| 1129 | ` *   copy_nopN       frame of asmcopy: pad of asmcopy.` | Comment: the `copy_nop` kernels have the frame of `asmcopy`. So they take the pad of `asmcopy`. |
| 1130 | ` */` | Ends the comment. |
| 1131 | `#define LOOP_read12 20` | `LOOP_read12`: 20, the planned loop offset modulo 64 of the new read kernels. It is the loop offset of `asmread`. |
| 1132 | `#ifndef HEAD_read_dadd` | Compiles line 1133 only when the build command has not defined `HEAD_read_dadd`. |
| 1133 | `#define HEAD_read_dadd 52` | `HEAD_read_dadd`: 52 bytes of code stand before the loop of a `read_dadd` kernel. The listing of the CRB binary of `bwx13` shows this distance: 13 instructions, which are the save of `d8` to `d15`, the `add` of the end address and 8 `movi` [Ref1]. |
| 1134 | `#endif` | Ends the `#ifndef` of line 1132. |
| 1135 | `#ifndef HEAD_read_iadd` | Compiles line 1136 only when the build command has not defined `HEAD_read_iadd`. |
| 1136 | `#define HEAD_read_iadd 84` | `HEAD_read_iadd`: 84 bytes of code stand before the loop of `read_iadd16`. The listing of the CRB binary of `bwx13` shows this distance: 21 instructions, of which 16 are `movi` [Ref1]. |
| 1137 | `#endif` | Ends the `#ifndef` of line 1135. |
| 1138 | `#ifndef HEAD_read_sp` | Compiles line 1139 only when the build command has not defined `HEAD_read_sp`. |
| 1139 | `#define HEAD_read_sp 4` | `HEAD_read_sp`: 4 bytes of code, one instruction, stand before the loop of a `read_sp` kernel. The listing of the CRB binary of `bwx13` shows this distance [Ref1]. |
| 1140 | `#endif` | Ends the `#ifndef` of line 1138. |
| 1141 | `#ifndef PAD_read_nop48` | Compiles line 1142 only when the build command has not defined `PAD_read_nop48`. |
| 1142 | `#define PAD_read_nop48 PAD_asmread` | `PAD_read_nop48`: the value of `PAD_asmread`, 0 bytes. |
| 1143 | `#endif` | Ends the `#ifndef` of line 1141. |
| 1144 | `#ifndef PAD_read_nop56` | Compiles line 1145 only when the build command has not defined `PAD_read_nop56`. |
| 1145 | `#define PAD_read_nop56 PAD_asmread` | `PAD_read_nop56`: the value of `PAD_asmread`, 0 bytes. |
| 1146 | `#endif` | Ends the `#ifndef` of line 1144. |
| 1147 | `#ifndef PAD_read_nop72` | Compiles line 1148 only when the build command has not defined `PAD_read_nop72`. |
| 1148 | `#define PAD_read_nop72 PAD_asmread` | `PAD_read_nop72`: the value of `PAD_asmread`, 0 bytes. |
| 1149 | `#endif` | Ends the `#ifndef` of line 1147. |
| 1150 | `#ifndef PAD_read_nop80` | Compiles line 1151 only when the build command has not defined `PAD_read_nop80`. |
| 1151 | `#define PAD_read_nop80 PAD_asmread` | `PAD_read_nop80`: the value of `PAD_asmread`, 0 bytes. |
| 1152 | `#endif` | Ends the `#ifndef` of line 1150. |
| 1153 | `#ifndef PAD_read_nop88` | Compiles line 1154 only when the build command has not defined `PAD_read_nop88`. |
| 1154 | `#define PAD_read_nop88 PAD_asmread` | `PAD_read_nop88`: the value of `PAD_asmread`, 0 bytes. |
| 1155 | `#endif` | Ends the `#ifndef` of line 1153. |
| 1156 | `#ifndef PAD_read_nop112` | Compiles line 1157 only when the build command has not defined `PAD_read_nop112`. |
| 1157 | `#define PAD_read_nop112 PAD_asmread` | `PAD_read_nop112`: the value of `PAD_asmread`, 0 bytes. |
| 1158 | `#endif` | Ends the `#ifndef` of line 1156. |
| 1159 | `#ifndef PAD_read_nop160` | Compiles line 1160 only when the build command has not defined `PAD_read_nop160`. |
| 1160 | `#define PAD_read_nop160 PAD_asmread` | `PAD_read_nop160`: the value of `PAD_asmread`, 0 bytes. |
| 1161 | `#endif` | Ends the `#ifndef` of line 1159. |
| 1162 | `#ifndef PAD_read_nop192` | Compiles line 1163 only when the build command has not defined `PAD_read_nop192`. |
| 1163 | `#define PAD_read_nop192 PAD_asmread` | `PAD_read_nop192`: the value of `PAD_asmread`, 0 bytes. |
| 1164 | `#endif` | Ends the `#ifndef` of line 1162. |
| 1165 | `#ifndef PAD_read_nop256` | Compiles line 1166 only when the build command has not defined `PAD_read_nop256`. |
| 1166 | `#define PAD_read_nop256 PAD_asmread` | `PAD_read_nop256`: the value of `PAD_asmread`, 0 bytes. So `k_read_nop256` starts on a 64 B boundary. The listing of the CRB binary of `bwx13` shows the start address `0x6dc0`, which is 0 modulo 64 [Ref1]. |
| 1167 | `#endif` | Ends the `#ifndef` of line 1165. |
| 1168 | `#ifndef PAD_read_dadd2` | Compiles line 1169 only when the build command has not defined `PAD_read_dadd2`. |
| 1169 | `#define PAD_read_dadd2 PADOF(LOOP_read12, HEAD_read_dadd)` | `PAD_read_dadd2`: `PADOF` (line 195) computes (20 - 52) modulo 64, which is 32 bytes with the default values. |
| 1170 | `#endif` | Ends the `#ifndef` of line 1168. |
| 1171 | `#ifndef PAD_read_dadd4` | Compiles line 1172 only when the build command has not defined `PAD_read_dadd4`. |
| 1172 | `#define PAD_read_dadd4 PADOF(LOOP_read12, HEAD_read_dadd)` | `PAD_read_dadd4`: (20 - 52) modulo 64, which is 32 bytes with the default values. |
| 1173 | `#endif` | Ends the `#ifndef` of line 1171. |
| 1174 | `#ifndef PAD_read_dadd8` | Compiles line 1175 only when the build command has not defined `PAD_read_dadd8`. |
| 1175 | `#define PAD_read_dadd8 PADOF(LOOP_read12, HEAD_read_dadd)` | `PAD_read_dadd8`: (20 - 52) modulo 64, which is 32 bytes with the default values. |
| 1176 | `#endif` | Ends the `#ifndef` of line 1174. |
| 1177 | `#ifndef PAD_read_dadd16` | Compiles line 1178 only when the build command has not defined `PAD_read_dadd16`. |
| 1178 | `#define PAD_read_dadd16 PADOF(LOOP_read12, HEAD_read_dadd)` | `PAD_read_dadd16`: (20 - 52) modulo 64, which is 32 bytes with the default values. |
| 1179 | `#endif` | Ends the `#ifndef` of line 1177. |
| 1180 | `#ifndef PAD_read_iadd16` | Compiles line 1181 only when the build command has not defined `PAD_read_iadd16`. |
| 1181 | `#define PAD_read_iadd16 PADOF(LOOP_read12, HEAD_read_iadd)` | `PAD_read_iadd16`: (20 - 84) modulo 64, which is 0 bytes with the default values. |
| 1182 | `#endif` | Ends the `#ifndef` of line 1180. |
| 1183 | `#ifndef PAD_read_sp24` | Compiles line 1184 only when the build command has not defined `PAD_read_sp24`. |
| 1184 | `#define PAD_read_sp24 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp24`: (20 - 4) modulo 64, which is 16 bytes with the default values. |
| 1185 | `#endif` | Ends the `#ifndef` of line 1183. |
| 1186 | `#ifndef PAD_read_sp32` | Compiles line 1187 only when the build command has not defined `PAD_read_sp32`. |
| 1187 | `#define PAD_read_sp32 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp32`: (20 - 4) modulo 64, which is 16 bytes with the default values. |
| 1188 | `#endif` | Ends the `#ifndef` of line 1186. |
| 1189 | `#ifndef PAD_read_sp40` | Compiles line 1190 only when the build command has not defined `PAD_read_sp40`. |
| 1190 | `#define PAD_read_sp40 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp40`: (20 - 4) modulo 64, which is 16 bytes with the default values. |
| 1191 | `#endif` | Ends the `#ifndef` of line 1189. |
| 1192 | `#ifndef PAD_read_sp48` | Compiles line 1193 only when the build command has not defined `PAD_read_sp48`. |
| 1193 | `#define PAD_read_sp48 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp48`: (20 - 4) modulo 64, which is 16 bytes with the default values. |
| 1194 | `#endif` | Ends the `#ifndef` of line 1192. |
| 1195 | `#ifndef PAD_read_sp56` | Compiles line 1196 only when the build command has not defined `PAD_read_sp56`. |
| 1196 | `#define PAD_read_sp56 PADOF(LOOP_read12, HEAD_read_sp)` | `PAD_read_sp56`: (20 - 4) modulo 64, which is 16 bytes with the default values. |
| 1197 | `#endif` | Ends the `#ifndef` of line 1195. |
| 1198 | `#ifndef PAD_read_1pl_nop96` | Compiles line 1199 only when the build command has not defined `PAD_read_1pl_nop96`. |
| 1199 | `#define PAD_read_1pl_nop96 PAD_read_1pl` | `PAD_read_1pl_nop96`: the pad of `read_1pl`, which is 16 bytes with the default values (line 959). |
| 1200 | `#endif` | Ends the `#ifndef` of line 1198. |
| 1201 | `#ifndef PAD_write_nop32` | Compiles line 1202 only when the build command has not defined `PAD_write_nop32`. |
| 1202 | `#define PAD_write_nop32 PAD_asmwrite` | `PAD_write_nop32`: the pad of `asmwrite`, which is 32 bytes (line 251). |
| 1203 | `#endif` | Ends the `#ifndef` of line 1201. |
| 1204 | `#ifndef PAD_write_nop96` | Compiles line 1205 only when the build command has not defined `PAD_write_nop96`. |
| 1205 | `#define PAD_write_nop96 PAD_asmwrite` | `PAD_write_nop96`: the pad of `asmwrite`, which is 32 bytes (line 251). |
| 1206 | `#endif` | Ends the `#ifndef` of line 1204. |
| 1207 | `#ifndef PAD_write_nop128` | Compiles line 1208 only when the build command has not defined `PAD_write_nop128`. |
| 1208 | `#define PAD_write_nop128 PAD_asmwrite` | `PAD_write_nop128`: the pad of `asmwrite`, which is 32 bytes (line 251). |
| 1209 | `#endif` | Ends the `#ifndef` of line 1207. |
| 1210 | `#ifndef PAD_write_nop256` | Compiles line 1211 only when the build command has not defined `PAD_write_nop256`. |
| 1211 | `#define PAD_write_nop256 PAD_asmwrite` | `PAD_write_nop256`: the pad of `asmwrite`, which is 32 bytes (line 251). |
| 1212 | `#endif` | Ends the `#ifndef` of line 1210. |
| 1213 | `#ifndef PAD_copy_nop96` | Compiles line 1214 only when the build command has not defined `PAD_copy_nop96`. |
| 1214 | `#define PAD_copy_nop96 PAD_asmcopy` | `PAD_copy_nop96`: the pad of `asmcopy`, which is 32 bytes with the default values (line 224). |
| 1215 | `#endif` | Ends the `#ifndef` of line 1213. |
| 1216 | `#ifndef PAD_copy_nop192` | Compiles line 1217 only when the build command has not defined `PAD_copy_nop192`. |
| 1217 | `#define PAD_copy_nop192 PAD_asmcopy` | `PAD_copy_nop192`: the pad of `asmcopy`, which is 32 bytes with the default values (line 224). |
| 1218 | `#endif` | Ends the `#ifndef` of line 1216. |

### Kernels of round 5: nine more `read_nop` kernels (lines 1220 to 1231)

| Line | Source | Explanation |
|---:|---|---|
| 1220 | `/* DEF_ASMREAD is the macro of the kernels of bwx8: the asm text on AArch64,` | Comment: `DEF_ASMREAD` is the macro of the kernels of `bwx8`. On AArch64 it gives the assembly text (line 647). |
| 1221 | ` * the stand-in loop on another machine. */` | Comment: on another machine it gives the stand-in loop (line 889). |
| 1222 | `DEF_ASMREAD(read_nop48, 48)` | Creates the kernel `read_nop48` from the macro `DEF_ASMREAD` (lines 647 to 672): the `asmread` loop with 48 `nop` per loop pass. That is 59 instructions per 256 B. |
| 1223 | `DEF_ASMREAD(read_nop56, 56)` | Creates the kernel `read_nop56`: the `asmread` loop with 56 `nop` per loop pass. That is 67 instructions per 256 B. |
| 1224 | `DEF_ASMREAD(read_nop72, 72)` | Creates the kernel `read_nop72`: the `asmread` loop with 72 `nop` per loop pass. That is 83 instructions per 256 B. |
| 1225 | `DEF_ASMREAD(read_nop80, 80)` | Creates the kernel `read_nop80`: the `asmread` loop with 80 `nop` per loop pass. That is 91 instructions per 256 B. |
| 1226 | `DEF_ASMREAD(read_nop88, 88)` | Creates the kernel `read_nop88`: the `asmread` loop with 88 `nop` per loop pass. That is 99 instructions per 256 B. |
| 1227 | `DEF_ASMREAD(read_nop112, 112)` | Creates the kernel `read_nop112`: the `asmread` loop with 112 `nop` per loop pass. That is 123 instructions per 256 B. |
| 1228 | `DEF_ASMREAD(read_nop160, 160)` | Creates the kernel `read_nop160`: the `asmread` loop with 160 `nop` per loop pass. That is 171 instructions per 256 B. |
| 1229 | `DEF_ASMREAD(read_nop192, 192)` | Creates the kernel `read_nop192`: the `asmread` loop with 192 `nop` per loop pass. That is 203 instructions per 256 B. |
| 1230 | `DEF_ASMREAD(read_nop256, 256)` | Creates the function `k_read_nop256` from the macro `DEF_ASMREAD` (lines 647 to 672) with 256 `nop`. The loop is the loop of `k_read_nop96` (line 1094) with 256 `nop` in place of 96: 8 `ldp` that load 256 B, 256 `nop`, the `add` of the read address, `cmp` and the branch. That is 267 instructions (1068 B of code) per 256 B of data. Listing of the CRB build of `bwx13` [Ref1]: the function starts at the address `0x6dc0` (0 modulo 64) and the loop at `0x6dd4` (20 modulo 64), the loop offset of `k_asmread`. The save of `d8` to `d15` runs once per call, outside the loop, as in `k_read_nop96`. |

### Kernels with vector adds: the comment and the text pieces `ACC_ZERO`, `CONST_ONE`, `VADD` (lines 1232 to 1274)

| Line | Source | Explanation |
|---:|---|---|
| 1232 | `#if defined(__aarch64__)` | Opens a third block of AArch64 kernels: lines 1233 to 1436 are compiled only for AArch64. Its `#else` is at line 1437. The CRB binary of `bwx13` holds this branch: its listing holds `k_read_dadd2` with the `movi` and vector `add` instructions of line 1304 [Ref1]. |
| 1233 | `/*` | Opens the comment about the macro `DEF_READ_ADD` and its five kernels. |
| 1234 | ` * DEF_READ_ADD(name, init, adds): the loop of asmread (8 ldp of q registers` | Comment: `DEF_READ_ADD(name, init, adds)` defines a kernel with the loop of `asmread`: 8 `ldp` of `q` registers per 256 B. |
| 1235 | ` * per 256 B, same registers) with the text "adds" after the 8 ldp and before` | Comment: the loop uses the same registers as `asmread`. The assembly text `adds` stands after the 8 `ldp`. |
| 1236 | ` * the add of the pointer. "init" runs once per call, before the loop.` | Comment: the text `adds` stands before the `add` of the read pointer. The text `init` runs once per call, before the loop. |
| 1237 | ` * v16-v31 are caller-saved in AAPCS64, so gcc saves nothing for them. v8-v15` | Comment: AAPCS64, the calling rules of Arm, do not require a function to keep `v16` to `v31`. So gcc saves nothing for these registers. |
| 1238 | ` * are named as clobbers, so gcc saves d8-d15 once per call, as in asmread.` | Comment: `v8` to `v15` are named as changed (clobbers). So gcc saves `d8` to `d15` once per call, as in `asmread`. |
| 1239 | ` *` | Comment: an empty line of the comment. |
| 1240 | ` * ACC_ZERO sets the accumulators v16-v23 to 0. CONST_ONE sets v24-v31 to the` | Comment: `ACC_ZERO` sets the accumulators `v16` to `v23` to 0. An accumulator is a register that holds a running sum. `CONST_ONE` sets `v24` to `v31` to a constant. |
| 1241 | ` * value 1 in every 32-bit lane.` | Comment: the constant is the value 1 in every 32-bit lane. A lane is one of the equal parts of a vector register. |
| 1242 | ` * VADD(a, b) is "add va.2d, va.2d, vb.2d": two 64-bit adds, the instruction` | Comment: `VADD(a, b)` stands for the instruction `add va.2d, va.2d, vb.2d`. It performs two 64-bit adds. |
| 1243 | ` * of the old read loop (listing of k_oldread).` | Comment: it is the add instruction of the old read loop. The comment names the listing of `k_oldread` as the source. In the listing of `bwx13` the loop of `k_oldread` has 8 adds of this form [Ref1]. |
| 1244 | ` *` | Comment: an empty line of the comment. |
| 1245 | ` * read_daddK: every add takes a register that the 8 ldp of this iteration` | Comment: in a `read_dadd` kernel every add takes as an input a register that the 8 `ldp` of the same loop pass loaded. |
| 1246 | ` * loaded. So the add waits for the load data, and it stays in the` | Comment: so the add waits for the data of the load. Until then it stays in the out-of-order window of the core. |
| 1247 | ` * out-of-order window (the instructions that the core has issued and not yet` | Comment: the comment defines the out-of-order window: the instructions that the core has issued and has not yet retired. |
| 1248 | ` * retired) until the data arrives.` | Comment: the end of the sentence of line 1246: the add stays there until the data arrives. |
| 1249 | ` *   K = 16: v0 to v15, two per accumulator. 8 adds per 128 B, as oldread has.` | Comment: with K = 16 the adds take `v0` to `v15`, two registers per accumulator. That is 8 adds per 128 B, as in `oldread`. |
| 1250 | ` *   K = 8:  v0, v2, ..., v14, one per accumulator.` | Comment: with K = 8 the adds take `v0`, `v2` and so on to `v14`, one register per accumulator. |
| 1251 | ` *   K = 4:  v0, v4, v8, v12 into v16-v19.` | Comment: with K = 4 the adds take `v0`, `v4`, `v8` and `v12` and add them to `v16` to `v19`. |
| 1252 | ` *   K = 2:  v0, v8 into v16, v17.` | Comment: with K = 2 the adds take `v0` and `v8` and add them to `v16` and `v17`. |
| 1253 | ` * read_iadd16: 16 adds of v24-v31 to v16-v23. No add takes a loaded` | Comment: `read_iadd16` has 16 adds of `v24` to `v31` to `v16` to `v23`. No add takes a loaded register. |
| 1254 | ` * register. Same instruction count and same add instruction as read_dadd16.` | Comment: `read_iadd16` has the same instruction count and the same add instruction as `read_dadd16`. The listing of `bwx13` shows 27 instructions per loop pass for both [Ref1]. |
| 1255 | ` */` | Ends the comment. |
| 1256 | `#define ACC_ZERO \` | Starts the macro `ACC_ZERO`: a piece of assembly text with 8 `movi` instructions. `movi` writes a constant into a vector register. The backslash at the end of a line continues the macro on the next line. |
| 1257 | `    "movi v16.4s, #0\n\t" \` | `movi v16.4s, #0` sets the four 32-bit lanes of the sum register `v16` to 0. So the whole register is 0. |
| 1258 | `    "movi v17.4s, #0\n\t" \` | Sets the sum register `v17` to 0. |
| 1259 | `    "movi v18.4s, #0\n\t" \` | Sets the sum register `v18` to 0. |
| 1260 | `    "movi v19.4s, #0\n\t" \` | Sets the sum register `v19` to 0. |
| 1261 | `    "movi v20.4s, #0\n\t" \` | Sets the sum register `v20` to 0. |
| 1262 | `    "movi v21.4s, #0\n\t" \` | Sets the sum register `v21` to 0. |
| 1263 | `    "movi v22.4s, #0\n\t" \` | Sets the sum register `v22` to 0. |
| 1264 | `    "movi v23.4s, #0\n\t"` | Sets the sum register `v23` to 0. This is the last line of `ACC_ZERO`. |
| 1265 | `#define CONST_ONE \` | Starts the macro `CONST_ONE`: a piece of assembly text with 8 `movi` instructions. |
| 1266 | `    "movi v24.4s, #1\n\t" \` | `movi v24.4s, #1` sets each of the four 32-bit lanes of `v24` to 1. |
| 1267 | `    "movi v25.4s, #1\n\t" \` | Sets each 32-bit lane of `v25` to 1. |
| 1268 | `    "movi v26.4s, #1\n\t" \` | Sets each 32-bit lane of `v26` to 1. |
| 1269 | `    "movi v27.4s, #1\n\t" \` | Sets each 32-bit lane of `v27` to 1. |
| 1270 | `    "movi v28.4s, #1\n\t" \` | Sets each 32-bit lane of `v28` to 1. |
| 1271 | `    "movi v29.4s, #1\n\t" \` | Sets each 32-bit lane of `v29` to 1. |
| 1272 | `    "movi v30.4s, #1\n\t" \` | Sets each 32-bit lane of `v30` to 1. |
| 1273 | `    "movi v31.4s, #1\n\t"` | Sets each 32-bit lane of `v31` to 1. This is the last line of `CONST_ONE`. |
| 1274 | `#define VADD(a, b) "add v" #a ".2d, v" #a ".2d, v" #b ".2d\n\t"` | `VADD(a, b)` writes the text of one instruction: `add va.2d, va.2d, vb.2d`. `#a` and `#b` put the two numbers into the register names. The instruction adds the register b to the register a as two 64-bit numbers. |

### Macro `DEF_READ_ADD` and the kernels `read_dadd2` to `read_dadd16` and `read_iadd16` (lines 1275 to 1314)

| Line | Source | Explanation |
|---:|---|---|
| 1275 | `#define DEF_READ_ADD(name, init, adds) \` | Starts the macro `DEF_READ_ADD(name, init, adds)`. It creates one kernel function: the `asmread` loop with vector adds. |
| 1276 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (lines 1168 to 1182). |
| 1277 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 1278 | `    { \` | Opens the body of the kernel function. |
| 1279 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 1280 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 1281 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 1282 | `            init \` | `init`: the assembly text of the second macro argument. It stands before the loop label. So it runs once per call. |
| 1283 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loops of the five kernels start at an address of 20 modulo 64 [Ref1]. |
| 1284 | `            "ldp q0, q1, [%[p]]\n\t" \` | Loads the bytes 0 to 31 of the current block of 256 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 1285 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 1286 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 1287 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. |
| 1288 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 1289 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 1290 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 1291 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once. |
| 1292 | `            adds \` | `adds`: the assembly text of the third macro argument, the vector adds. They run in every loop pass, after the 8 loads. |
| 1293 | `            "add %[p], %[p], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 1294 | `            "cmp %[p], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 1295 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. |
| 1296 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 1297 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 1298 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 1299 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call. The listing of `bwx13` shows the same save as in `k_asmread` for each of the five functions [Ref1]. |
| 1300 | `              "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23", \` | Continues the clobber list: `v16` to `v23`, the sum registers. The function does not store the sums and does not return them. In the listing of `bwx13` only the load of `d8` to `d15` and `ret` follow the loop [Ref1]. |
| 1301 | `              "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31", \` | Continues the clobber list: `v24` to `v31`, the registers of the constants. |
| 1302 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 1303 | `    }` | Ends the kernel function and the macro. |
| 1304 | `DEF_READ_ADD(read_dadd2, ACC_ZERO, VADD(16, 0) VADD(17, 8))` | Creates `k_read_dadd2`, the kernel `read_dadd2`. `init` is `ACC_ZERO`. The loop has 2 vector adds per 256 B: `v0` is added to `v16`, and `v8` to `v17`. So 2 of the 16 loaded registers are inputs of an add. The other 14 loaded values are not used. One loop pass is 13 instructions. |
| 1305 | `DEF_READ_ADD(read_dadd4, ACC_ZERO, VADD(16, 0) VADD(17, 4) VADD(18, 8) VADD(19, 12))` | Creates `k_read_dadd4`, the kernel `read_dadd4`. `init` is `ACC_ZERO`. The loop has 4 vector adds per 256 B: `v0`, `v4`, `v8` and `v12` are added to `v16`, `v17`, `v18` and `v19`. The other 12 loaded values are not used. One loop pass is 15 instructions. |
| 1306 | `DEF_READ_ADD(read_dadd8, ACC_ZERO,` | Starts the definition of `k_read_dadd8`, the kernel `read_dadd8`. `init` is `ACC_ZERO`. |
| 1307 | `             VADD(16, 0) VADD(17, 2) VADD(18, 4) VADD(19, 6) VADD(20, 8) VADD(21, 10) VADD(22, 12) VADD(23, 14))` | The third argument: 8 vector adds per 256 B. `v0`, `v2`, `v4`, `v6`, `v8`, `v10`, `v12` and `v14` are added to `v16` to `v23`. So every second loaded register is an input of an add. The other 8 loaded values are not used. One loop pass is 19 instructions. |
| 1308 | `DEF_READ_ADD(read_dadd16, ACC_ZERO,` | Starts the definition of `k_read_dadd16`, the kernel `read_dadd16`. `init` is `ACC_ZERO`. |
| 1309 | `             VADD(16, 0) VADD(17, 1) VADD(18, 2) VADD(19, 3) VADD(20, 4) VADD(21, 5) VADD(22, 6) VADD(23, 7)` | The first 8 of its 16 vector adds: `v0` to `v7` are added to `v16` to `v23`. |
| 1310 | `             VADD(16, 8) VADD(17, 9) VADD(18, 10) VADD(19, 11) VADD(20, 12) VADD(21, 13) VADD(22, 14) VADD(23, 15))` | The other 8 vector adds: `v8` to `v15` are added to `v16` to `v23`. So every loaded register is an input of one add: 16 adds per 256 B. One loop pass is 27 instructions. |
| 1311 | `DEF_READ_ADD(read_iadd16, ACC_ZERO CONST_ONE,` | Starts the definition of `k_read_iadd16`, the kernel `read_iadd16`. `init` is `ACC_ZERO` followed by `CONST_ONE`: 16 `movi` instructions run once per call. |
| 1312 | `             VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27) VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31)` | The first 8 of its 16 vector adds: the constants `v24` to `v31` are added to `v16` to `v23`. |
| 1313 | `             VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27) VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31))` | The same 8 adds once more. So the loop has 16 vector adds per 256 B, and no add takes a loaded register. The 16 loaded values are not used. One loop pass is 27 instructions, as in `k_read_dadd16`. |

### Macro `DEF_READ_SP`: the `read_sparse` loop with another number of `nop` (lines 1315 to 1342)

| Line | Source | Explanation |
|---:|---|---|
| 1315 | `/* DEF_READ_SP(name, nops): the text of read_sparse with "nops" nop` | Comment: `DEF_READ_SP(name, nops)` is the text of `read_sparse` (line 683) with another number of `nop` instructions. The macro argument `nops` gives the number. |
| 1316 | ` * instructions in place of 9. Per 128 B: 4 ldp, the nop, add, cmp, b.lo. */` | Comment: `read_sparse` has 9 `nop` in that place. Per 128 B the loop has 4 `ldp`, the `nop` instructions, `add`, `cmp` and `b.lo`. |
| 1317 | `#define DEF_READ_SP(name, nops) \` | Starts the macro `DEF_READ_SP(name, nops)`. It creates one kernel function. |
| 1318 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (lines 1183 to 1197). |
| 1319 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 1320 | `    { \` | Opens the body of the kernel function. |
| 1321 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 1322 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 1323 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 1324 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loops of the five kernels start at an address of 20 modulo 64 [Ref1]. |
| 1325 | `            "ldp q0, q1, [%[p]]\n\t" \` | Loads the bytes 0 to 31 of the current block of 128 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 1326 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 1327 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 1328 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. One loop pass has 4 load instructions. It reads 128 B, each byte once. Nothing uses the loaded values. |
| 1329 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the macro argument into text. The assembler writes the instruction `nop` that many times. A `nop` does nothing. |
| 1330 | `            "add %[p], %[p], #128\n\t" \` | Moves the read pointer forward by 128 B. |
| 1331 | `            "cmp %[p], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 1332 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. |
| 1333 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 1334 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 1335 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc"); \` | The clobber list: the vector registers `v0` to `v7`, memory and the condition flags. It names none of `v8` to `v15`. So gcc saves no register in these functions. The listing of `bwx13` shows one `add` before the loop and one `ret` after it in each of them [Ref1]. |
| 1336 | `    }` | Ends the kernel function and the macro. |
| 1337 | `DEF_READ_SP(read_sp24, 24)` | Creates the kernel `read_sp24`: 4 `ldp` and 24 `nop` per 128 B. One loop pass is 31 instructions. |
| 1338 | `DEF_READ_SP(read_sp32, 32)` | Creates the kernel `read_sp32`: 4 `ldp` and 32 `nop` per 128 B. One loop pass is 39 instructions. |
| 1339 | `DEF_READ_SP(read_sp40, 40)` | Creates the kernel `read_sp40`: 4 `ldp` and 40 `nop` per 128 B. One loop pass is 47 instructions. |
| 1340 | `DEF_READ_SP(read_sp48, 48)` | Creates the kernel `read_sp48`: 4 `ldp` and 48 `nop` per 128 B. One loop pass is 55 instructions. |
| 1341 | `DEF_READ_SP(read_sp56, 56)` | Creates the kernel `read_sp56`: 4 `ldp` and 56 `nop` per 128 B. One loop pass is 63 instructions. |

### Function `k_read_1pl_nop96`: the `read_1pl` loop with 96 `nop` (lines 1343 to 1364)

| Line | Source | Explanation |
|---:|---|---|
| 1343 | `/* read_1pl_nop96: the text of read_1pl with 96 nop after the four loads. It` | Comment: `read_1pl_nop96` is the text of `read_1pl` (line 1019) with 96 `nop` after the four loads. |
| 1344 | ` * reads bytes 0 to 15 of every 64 B line and no other byte. */` | Comment: the kernel reads the bytes 0 to 15 of every 64 B line and no other byte. A 64 B line is a block of 64 B of memory, a cache line. |
| 1345 | `PLACE(read_1pl_nop96);` | `PLACE` adds the pad of this kernel. It is the pad of `read_1pl`, 16 bytes with the default values (line 1199). |
| 1346 | `__attribute__((noinline)) static void k_read_1pl_nop96(const uint64_t *a, size_t n)` | Starts the function `k_read_1pl_nop96`, the kernel `read_1pl_nop96`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. |
| 1347 | `{` | Opens the body of `k_read_1pl_nop96`. |
| 1348 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 1349 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. |
| 1350 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 1351 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loop starts at an address of 20 modulo 64 [Ref1]. |
| 1352 | `        "ldr q0, [%[p]]\n\t"` | `ldr` loads 16 B from memory into one vector register: the bytes 0 to 15 of the current block of 256 B into `q0`. |
| 1353 | `        "ldr q1, [%[p], #64]\n\t"` | Loads the bytes 64 to 79 of the block into `q1`. |
| 1354 | `        "ldr q2, [%[p], #128]\n\t"` | Loads the bytes 128 to 143 of the block into `q2`. |
| 1355 | `        "ldr q3, [%[p], #192]\n\t"` | Loads the bytes 192 to 207 of the block into `q3`. So one loop pass handles a block of 256 B and loads 16 B at the start of each of its four 64 B lines: 64 B in all. Nothing uses the loaded values. |
| 1356 | `        ".rept 96\n\tnop\n\t.endr\n\t"` | The assembler writes the instruction `nop` 96 times here. A `nop` does nothing. |
| 1357 | `        "add %[p], %[p], #256\n\t"` | Moves the read pointer forward by 256 B. |
| 1358 | `        "cmp %[p], %[end]\n\t"` | Compares the read pointer with `end`. |
| 1359 | `        "b.lo 1b\n\t"` | Branches back to the label `1` while the pointer is below `end`. One loop pass is 103 instructions: 4 `ldr`, 96 `nop`, `add`, `cmp` and the branch. |
| 1360 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 1361 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 1362 | `        : "v0", "v1", "v2", "v3", "memory", "cc");` | The clobber list: the vector registers `v0` to `v3`, memory and the condition flags. gcc saves no register in this function. |
| 1363 | `}` | Ends the function `k_read_1pl_nop96`. |

### Macro `DEF_ASMWRITE_NOP`: the write loop with `nop` (lines 1365 to 1396)

| Line | Source | Explanation |
|---:|---|---|
| 1365 | `/* DEF_ASMWRITE_NOP(name, nops): the text of DEF_ASMWRITE with "nops" nop` | Comment: `DEF_ASMWRITE_NOP(name, nops)` is the text of `DEF_ASMWRITE` (line 702) with `nop` instructions added. The macro argument `nops` gives their number. |
| 1366 | ` * instructions after the 8 stp and before the add. */` | Comment: the `nop` instructions stand after the 8 `stp` and before the `add`. |
| 1367 | `#define DEF_ASMWRITE_NOP(name, nops) \` | Starts the macro `DEF_ASMWRITE_NOP(name, nops)`. It creates one write kernel. |
| 1368 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (lines 1201 to 1212). |
| 1369 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores the value `v` to `n` 8-byte words, from the address `a` on. |
| 1370 | `    { \` | Opens the body of the kernel function. |
| 1371 | `        uint64_t *p = a; \` | `p`: the write pointer. It starts at `a`. |
| 1372 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 1373 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 1374 | `            "dup v0.2d, %[v]\n\t" \` | `dup` copies the 8-byte value `v` into both halves of the 16-byte vector register `v0`. It stands before the loop label, so it runs once per call. |
| 1375 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loops of the four kernels start at an address of 40 modulo 64, the loop offset of `k_asmwrite` [Ref1]. |
| 1376 | `            "stp q0, q0, [%[p]]\n\t" \` | `stp` stores two 16-byte vector registers to memory, which is 32 B. Here both are `q0`. This instruction writes the bytes 0 to 31 of the current block of 256 B. |
| 1377 | `            "stp q0, q0, [%[p], #32]\n\t" \` | Stores `q0` twice to the bytes 32 to 63 of the block. |
| 1378 | `            "stp q0, q0, [%[p], #64]\n\t" \` | Stores `q0` twice to the bytes 64 to 95 of the block. |
| 1379 | `            "stp q0, q0, [%[p], #96]\n\t" \` | Stores `q0` twice to the bytes 96 to 127 of the block. |
| 1380 | `            "stp q0, q0, [%[p], #128]\n\t" \` | Stores `q0` twice to the bytes 128 to 159 of the block. |
| 1381 | `            "stp q0, q0, [%[p], #160]\n\t" \` | Stores `q0` twice to the bytes 160 to 191 of the block. |
| 1382 | `            "stp q0, q0, [%[p], #192]\n\t" \` | Stores `q0` twice to the bytes 192 to 223 of the block. |
| 1383 | `            "stp q0, q0, [%[p], #224]\n\t" \` | Stores `q0` twice to the bytes 224 to 255 of the block. One loop pass has 8 store instructions. It writes 256 B, each byte once. |
| 1384 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the macro argument into text. The assembler writes the instruction `nop` that many times. |
| 1385 | `            "add %[p], %[p], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 1386 | `            "cmp %[p], %[end]\n\t" \` | Compares the write pointer with `end`. |
| 1387 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the pointer is below `end`. |
| 1388 | `            : [p] "+r"(p) \` | `p` is in a general register. The text reads it and changes it. |
| 1389 | `            : [end] "r"(end), [v] "r"(v) \` | `end` and `v` are inputs in general registers. |
| 1390 | `            : "v0", "memory", "cc"); \` | The clobber list: the vector register `v0`, memory and the condition flags. gcc saves no register in these functions. |
| 1391 | `    }` | Ends the kernel function and the macro. |
| 1392 | `DEF_ASMWRITE_NOP(write_nop32, 32)` | Creates the kernel `write_nop32`: 8 `stp` and 32 `nop` per 256 B. One loop pass is 43 instructions. |
| 1393 | `DEF_ASMWRITE_NOP(write_nop96, 96)` | Creates the kernel `write_nop96`: 8 `stp` and 96 `nop` per 256 B. One loop pass is 107 instructions. |
| 1394 | `DEF_ASMWRITE_NOP(write_nop128, 128)` | Creates the kernel `write_nop128`: 8 `stp` and 128 `nop` per 256 B. One loop pass is 139 instructions. |
| 1395 | `DEF_ASMWRITE_NOP(write_nop256, 256)` | Creates the kernel `write_nop256`: 8 `stp` and 256 `nop` per 256 B. One loop pass is 267 instructions. |

### Macro `DEF_ASMCOPY_NOP`: the copy loop with `nop` (lines 1397 to 1436)

| Line | Source | Explanation |
|---:|---|---|
| 1397 | `/* DEF_ASMCOPY_NOP(name, nops): the text of DEF_ASMCOPY with "nops" nop` | Comment: `DEF_ASMCOPY_NOP(name, nops)` is the text of `DEF_ASMCOPY` (line 729) with `nop` instructions added. The macro argument `nops` gives their number. |
| 1398 | ` * instructions after the 8 stp and before the two adds. */` | Comment: the `nop` instructions stand after the 8 `stp` and before the two `add`. |
| 1399 | `#define DEF_ASMCOPY_NOP(name, nops) \` | Starts the macro `DEF_ASMCOPY_NOP(name, nops)`. It creates one copy kernel. |
| 1400 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (lines 1213 to 1218). |
| 1401 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 1402 | `    { \` | Opens the body of the kernel function. |
| 1403 | `        uint64_t *dp = d; \` | `dp`: the write pointer in the destination. It starts at `d`. |
| 1404 | `        const uint64_t *sp = s; \` | `sp`: the read pointer in the source. It starts at `s`. |
| 1405 | `        const uint64_t *end = s + n; \` | `end`: the first address after the source range: `s` plus `n` words. |
| 1406 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 1407 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx13` the loops of the two kernels start at an address of 52 modulo 64, the loop offset of `k_asmcopy` [Ref1]. |
| 1408 | `            "ldp q0, q1, [%[s]]\n\t" \` | Loads the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. `ldp` loads 32 B into two 16-byte vector registers. |
| 1409 | `            "ldp q2, q3, [%[s], #32]\n\t" \` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 1410 | `            "ldp q4, q5, [%[s], #64]\n\t" \` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 1411 | `            "ldp q6, q7, [%[s], #96]\n\t" \` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 1412 | `            "ldp q8, q9, [%[s], #128]\n\t" \` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 1413 | `            "ldp q10, q11, [%[s], #160]\n\t" \` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 1414 | `            "ldp q12, q13, [%[s], #192]\n\t" \` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 1415 | `            "ldp q14, q15, [%[s], #224]\n\t" \` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass loads 256 B from the source buffer with 8 `ldp`. |
| 1416 | `            "stp q0, q1, [%[d]]\n\t" \` | Stores `q0` and `q1` to the bytes 0 to 31 of the current destination block. `stp` stores two 16-byte vector registers. |
| 1417 | `            "stp q2, q3, [%[d], #32]\n\t" \` | Stores `q2` and `q3` to the bytes 32 to 63 of the destination block. |
| 1418 | `            "stp q4, q5, [%[d], #64]\n\t" \` | Stores `q4` and `q5` to the bytes 64 to 95 of the destination block. |
| 1419 | `            "stp q6, q7, [%[d], #96]\n\t" \` | Stores `q6` and `q7` to the bytes 96 to 127 of the destination block. |
| 1420 | `            "stp q8, q9, [%[d], #128]\n\t" \` | Stores `q8` and `q9` to the bytes 128 to 159 of the destination block. |
| 1421 | `            "stp q10, q11, [%[d], #160]\n\t" \` | Stores `q10` and `q11` to the bytes 160 to 191 of the destination block. |
| 1422 | `            "stp q12, q13, [%[d], #192]\n\t" \` | Stores `q12` and `q13` to the bytes 192 to 223 of the destination block. |
| 1423 | `            "stp q14, q15, [%[d], #224]\n\t" \` | Stores `q14` and `q15` to the bytes 224 to 255 of the destination block. One loop pass stores 256 B to the destination buffer with 8 `stp`. Each loaded register is stored once and has no other use. |
| 1424 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the macro argument into text. The assembler writes the instruction `nop` that many times. |
| 1425 | `            "add %[s], %[s], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 1426 | `            "add %[d], %[d], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 1427 | `            "cmp %[s], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 1428 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the read pointer is below `end`. |
| 1429 | `            : [s] "+r"(sp), [d] "+r"(dp) \` | `sp` and `dp` are in general registers. The text reads them and changes them. |
| 1430 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 1431 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 1432 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop. |
| 1433 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 1434 | `    }` | Ends the kernel function and the macro. |
| 1435 | `DEF_ASMCOPY_NOP(copy_nop96, 96)` | Creates the copy kernel `copy_nop96`: 8 `ldp`, 8 `stp` and 96 `nop` per 256 B. One loop pass is 116 instructions. |
| 1436 | `DEF_ASMCOPY_NOP(copy_nop192, 192)` | Creates the copy kernel `copy_nop192`: 8 `ldp`, 8 `stp` and 192 `nop` per 256 B. One loop pass is 212 instructions. |

### Stand-ins of the kernels of round 5 (lines 1437 to 1470)

| Line | Source | Explanation |
|---:|---|---|
| 1437 | `#else` | `#else` of the `#if` of line 1232. The lines up to line 1468 are compiled only when the target is not AArch64. In that case each kernel of lines 1304 to 1436 becomes a plain C loop. |
| 1438 | `/* Stand-ins. A nop and a vector add of registers touch no byte. So the` | Comment: the stand-ins of the kernels of this block. A `nop` and a vector add of registers touch no byte of memory. |
| 1439 | ` * stand-in of a read_dadd, read_iadd or read_sp kernel is the stand-in of` | Comment: so the stand-in of a `read_dadd`, `read_iadd` or `read_sp` kernel is the stand-in of `asmread` (lines 889 to 896). |
| 1440 | ` * asmread: these kernels read every byte of the range. The stand-in of` | Comment: the reason: these kernels read every byte of the range. The sentence about `read_1pl_nop96` starts here. |
| 1441 | ` * read_1pl_nop96 is the stand-in of read_1pl: the first two words (16 B) of` | Comment: the stand-in of `read_1pl_nop96` has the loop of the stand-in of `read_1pl` (lines 1045 to 1052). It reads the first two words, which are 16 B, of every 64 B line. |
| 1442 | ` * every 64 B line. The stand-ins of the write and copy kernels are the` | Comment: the stand-ins of the `write_nop` kernels and of the `copy_nop` kernels are the stand-ins of `asmwrite` and `asmcopy`. |
| 1443 | ` * stand-ins of asmwrite and asmcopy. */` | Comment: the end of the sentence of line 1442. |
| 1444 | `DEF_ASMREAD(read_dadd2, 0)` | Stand-in build only: defines `k_read_dadd2` as the plain read loop of lines 889 to 896, which reads every word of the range. |
| 1445 | `DEF_ASMREAD(read_dadd4, 0)` | Stand-in build only: defines `k_read_dadd4` as the plain read loop. |
| 1446 | `DEF_ASMREAD(read_dadd8, 0)` | Stand-in build only: defines `k_read_dadd8` as the plain read loop. |
| 1447 | `DEF_ASMREAD(read_dadd16, 0)` | Stand-in build only: defines `k_read_dadd16` as the plain read loop. |
| 1448 | `DEF_ASMREAD(read_iadd16, 0)` | Stand-in build only: defines `k_read_iadd16` as the plain read loop. |
| 1449 | `DEF_ASMREAD(read_sp24, 24)` | Stand-in build only: defines `k_read_sp24` as the plain read loop. The stand-in macro does not use the number 24. |
| 1450 | `DEF_ASMREAD(read_sp32, 32)` | Stand-in build only: defines `k_read_sp32` as the plain read loop. The number 32 is not used. |
| 1451 | `DEF_ASMREAD(read_sp40, 40)` | Stand-in build only: defines `k_read_sp40` as the plain read loop. The number 40 is not used. |
| 1452 | `DEF_ASMREAD(read_sp48, 48)` | Stand-in build only: defines `k_read_sp48` as the plain read loop. The number 48 is not used. |
| 1453 | `DEF_ASMREAD(read_sp56, 56)` | Stand-in build only: defines `k_read_sp56` as the plain read loop. The number 56 is not used. |
| 1454 | `PLACE(read_1pl_nop96);` | `PLACE` adds the pad of `read_1pl_nop96`, as in the AArch64 branch. |
| 1455 | `__attribute__((noinline)) static void k_read_1pl_nop96(const uint64_t *a, size_t n)` | Starts the stand-in function `k_read_1pl_nop96`. A build on CRB, an Arm machine, does not compile it. |
| 1456 | `{` | Opens the body of the stand-in. |
| 1457 | `    const volatile uint64_t *p = a;` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 1458 | `    for (size_t i = 0; i < n; i += 8) {` | A loop over the range in steps of 8 words, which are 64 B. |
| 1459 | `        (void)p[i];` | Reads the first word of the 64 B line and drops the value. |
| 1460 | `        (void)p[i + 1];` | Reads the second word of the 64 B line and drops the value. So the loop reads 16 B of every 64 B. |
| 1461 | `    }` | Ends the loop of line 1458. |
| 1462 | `}` | Ends the stand-in function `k_read_1pl_nop96`. |
| 1463 | `DEF_ASMWRITE(write_nop32)` | Stand-in build only: defines `k_write_nop32` as the plain write loop of lines 897 to 903. |
| 1464 | `DEF_ASMWRITE(write_nop96)` | Stand-in build only: defines `k_write_nop96` as the plain write loop. |
| 1465 | `DEF_ASMWRITE(write_nop128)` | Stand-in build only: defines `k_write_nop128` as the plain write loop. |
| 1466 | `DEF_ASMWRITE(write_nop256)` | Stand-in build only: defines `k_write_nop256` as the plain write loop. |
| 1467 | `DEF_ASMCOPY(copy_nop96)` | Stand-in build only: defines `k_copy_nop96` as the plain copy loop of lines 904 to 910. |
| 1468 | `DEF_ASMCOPY(copy_nop192)` | Stand-in build only: defines `k_copy_nop192` as the plain copy loop. |
| 1469 | `#endif` | Ends the `#if` of line 1232. |

### Third pad after the kernels (version `bwx12`) (lines 1471 to 1481)

| Line | Source | Explanation |
|---:|---|---|
| 1471 | `/*` | Opens the comment about the third pad. |
| 1472 | ` * The pad after the kernels, a third time. The pad of bwx11 above now stands` | Comment: the pad after the kernels is needed a third time. The pad of `bwx11` (line 1106) now stands before the kernels of round 5. |
| 1473 | ` * before the kernels of round 5, so it no longer places call(). This pad has` | Comment: so the pad of `bwx11` no longer sets the start address of `call`. |
| 1474 | ` * the same value, and the function after the kernels starts at that value` | Comment: the new pad has the same value. The function after the kernels then starts at that value modulo 64. This describes `bwx12.c`. In this file more kernels follow the pad, and the pad of line 1602 does this work. |
| 1475 | ` * modulo 64, as in bwx11, bwx10 and bwx8. build12.sh prints the placement.` | Comment: that is the start address modulo 64 that this function has in `bwx11`, `bwx10` and `bwx8`. The script `build12.sh` in the code folder `bwx12-2026-11-15` prints the placement. |
| 1476 | ` */` | Ends the comment. |
| 1477 | `#ifndef PAD_after_kernels12` | Compiles line 1478 only when the build command has not defined `PAD_after_kernels12`. |
| 1478 | `#define PAD_after_kernels12 PAD_after_kernels` | `PAD_after_kernels12` gets the value of `PAD_after_kernels`, which is 24 (line 1068). |
| 1479 | `#endif` | Ends the `#ifndef` of line 1477. |
| 1480 | `PLACE(after_kernels12);` | `PLACE(after_kernels12)` pads the code up to a 64 B boundary and then adds 24 bytes of value 0. In `bwx12.c` the function `call` follows this pad. In this file the function `rand_index` (line 1507) and the kernels of `bwx13` (lines 1590 to 1592) follow it. Each kernel has a pad of its own. So this pad places no kernel here. `rand_index` is a `static inline` function. The build record does not show whether the binary holds code for it at this place. The pad of line 1602 places `call`. |
| 1481 | `/* bwx12- */` | Comment: a marker. The block that line 1108 opened ends here. |

### Kernels of the version `bwx13`: the comment, the function `rand_index` and the pads (lines 1482 to 1522)

| Line | Source | Explanation |
|---:|---|---|
| 1482 | `/* bwx13+ */` | Comment: a marker. A block of text that the version `bwx13` added starts here. The marker of line 1603 ends the block. The block holds the three `rand_nop` kernels and a fourth pad. |
| 1484 | `/*` | Opens the comment about the three `rand_nop` kernels. |
| 1485 | ` * Kernels rand_nop0, rand_nop96, rand_nop256. They stand after every kernel` | Comment: the kernels below are `rand_nop0`, `rand_nop96` and `rand_nop256`. They stand after every kernel of `bwx12`. |
| 1486 | ` * of bwx12, so those keep their place.` | Comment: so the kernels of `bwx12` keep their place in the binary. |
| 1487 | ` *` | Comment: an empty line of the comment. |
| 1488 | ` * rand_index(i, nb) is the block that step i reads. For nb a power of two it` | Comment: the function `rand_index(i, nb)` (line 1507) gives the number of the block that step `i` reads. `nb` is the number of blocks of 256 B in the range of one call. The rule for a power of two starts here. |
| 1489 | ` * is (i * (2 * i + 1)) mod nb. This map sends 0 .. nb - 1 onto 0 .. nb - 1,` | Comment: when `nb` is a power of two, the block number is `(i * (2 * i + 1)) mod nb`. This rule maps the step numbers 0 to `nb - 1` onto the block numbers 0 to `nb - 1`. |
| 1490 | ` * each value once: if i * (2 * i + 1) = j * (2 * j + 1) mod nb, then` | Comment: each block number comes up exactly once. So every block is read once per call. The comment gives the proof. It starts here: assume that two steps `i` and `j` give the same block number. |
| 1491 | ` * (i - j) * (2 * (i + j) + 1) = 0 mod nb, the second factor is odd, so` | Comment: then `(i - j) * (2 * (i + j) + 1)` is a multiple of `nb`. The second factor is odd. So it shares no factor with `nb`, which is a power of two. |
| 1492 | ` * i = j mod nb. The self-test checks it for nb = 1, 2, 8, 8192 and 2^20.` | Comment: so `i - j` is a multiple of `nb`, and the two steps are the same step. The self-test checks the rule for 1, 2, 8, 8192 and 1048576 blocks. The function `test_rand` of the file `bwx13_selftest.c` holds this check. |
| 1493 | ` * For another nb the order is 0, 1, 2, ...` | Comment: for every other `nb` the order is 0, 1, 2 and so on: step `i` reads block `i`. |
| 1494 | ` *` | Comment: an empty line of the comment. |
| 1495 | ` * The asm text: x9 = i, x10 = nb, x11 = block index, x12 = nb - 1,` | Comment: the registers of the assembly text. `x9` holds the step number `i`. `x10` holds `nb`. `x11` holds the block number. `x12` holds `nb - 1`. |
| 1496 | ` * x13 = address of the block. Loop 1 is the random order. Loop 2 is the` | Comment: `x13` holds the address of the block. The text has two loops. Loop 1 reads the blocks in the scrambled order (lines 1543 to 1553). |
| 1497 | ` * order of asmread, for nb not a power of two. Both have the N nop after the` | Comment: loop 2 reads the blocks in the order of `asmread`: rising addresses (lines 1555 to 1561). It runs when `nb` is not a power of two. Both loops have the N `nop` instructions after the 8 `ldp`. |
| 1498 | ` * 8 ldp. v8-v15 are named as clobbers, so gcc saves d8-d15 once per call, as` | Comment: the clobber list names `v8` to `v15` (line 1567). So gcc saves `d8` to `d15`, the low 8 bytes of these registers, once per call. |
| 1499 | ` * in asmread.` | Comment: `asmread` has the same save (line 670). |
| 1500 | ` *` | Comment: an empty line of the comment. |
| 1501 | ` * Placement: the planned loop start of loop 1 is 20 modulo 64, the offset of` | Comment: the placement. Loop 1 must start at 20 modulo 64. This is the loop offset of `asmread`. |
| 1502 | ` * asmread. HEAD is 36: 4 stores of d registers and the 5 instructions before` | Comment: `HEAD`, the number of bytes of code before loop 1, is 36. These are 9 instructions of 4 bytes: 4 stores of `d` registers and the 5 instructions of lines 1538 to 1542. |
| 1503 | ` * loop 1. It is a guess until the listing of the CRB build confirms it` | Comment: the value is a guess until the listing of the CRB build confirms it. The listing of the CRB build of `bwx13` confirms it: in each of the three functions loop 1 starts 36 bytes after the function start, at 20 modulo 64 [Ref1]. |
| 1504 | ` * (check_listing13.py checks the loop offset). Override it with` | Comment: the script `check_listing13.py` in the same folder checks the loop offset. Its output for the CRB build reports the loop offset 20 and the expected code for all three kernels [Ref4]. The sentence about other values starts here. |
| 1505 | ` * -DHEAD_rand=N or -DPAD_rand_nopN=N.` | Comment: the build can replace the value with `-DHEAD_rand=N`, or a whole pad with `-DPAD_rand_nopN=N`. |
| 1506 | ` */` | Ends the comment. |
| 1507 | `static inline size_t rand_index(size_t i, size_t nb)` | Starts the function `rand_index`. It returns the number of the block that step `i` reads when a range has `nb` blocks. It is the C model of the block order. The stand-in kernels call it (line 1581), and the self-test calls it. The assembly text of lines 1544 to 1547 computes the same value without a call. |
| 1508 | `{` | Opens the body of `rand_index`. |
| 1509 | `    return (nb & (nb - 1)) == 0 ? (i * (2 * i + 1)) & (nb - 1) : i;` | `(nb & (nb - 1)) == 0` is true when `nb` is a power of two. In that case the function returns `i * (2 * i + 1)` with only its low bits kept (`& (nb - 1)`): the remainder of a division by `nb`. In every other case it returns `i`. |
| 1510 | `}` | Ends the function `rand_index`. |
| 1511 | `#ifndef HEAD_rand` | Compiles line 1512 only when the build command has not defined `HEAD_rand`. |
| 1512 | `#define HEAD_rand 36` | `HEAD_rand`: 36 bytes of code stand between the start of a `rand_nop` function and the start of its loop 1. In the listing of the CRB build of `bwx13` these are 9 instructions: 4 `stp` that save `d8` to `d15`, then `lsr`, `sub`, `tst`, `mov` and `b.ne` [Ref1]. |
| 1513 | `#endif` | Ends the `#ifndef` of line 1511. |
| 1514 | `#ifndef PAD_rand_nop0` | Compiles line 1515 only when the build command has not defined `PAD_rand_nop0`. |
| 1515 | `#define PAD_rand_nop0 PADOF(LOOP_read12, HEAD_rand)` | `PAD_rand_nop0`: `PADOF` (line 195) computes (20 - 36) modulo 64, which is 48 bytes with the default values. `LOOP_read12` is 20 (line 1131). In the CRB binary of `bwx13` the function `k_rand_nop0` starts at `0x8d70`, which is 48 modulo 64, and its loop 1 at `0x8d94`, which is 20 modulo 64 [Ref1]. |
| 1516 | `#endif` | Ends the `#ifndef` of line 1514. |
| 1517 | `#ifndef PAD_rand_nop96` | Compiles line 1518 only when the build command has not defined `PAD_rand_nop96`. |
| 1518 | `#define PAD_rand_nop96 PADOF(LOOP_read12, HEAD_rand)` | `PAD_rand_nop96`: (20 - 36) modulo 64, which is 48 bytes with the default values. In the CRB binary of `bwx13` the function `k_rand_nop96` starts at `0x8e70` (48 modulo 64) and its loop 1 at `0x8e94` (20 modulo 64) [Ref1]. |
| 1519 | `#endif` | Ends the `#ifndef` of line 1517. |
| 1520 | `#ifndef PAD_rand_nop256` | Compiles line 1521 only when the build command has not defined `PAD_rand_nop256`. |
| 1521 | `#define PAD_rand_nop256 PADOF(LOOP_read12, HEAD_rand)` | `PAD_rand_nop256`: (20 - 36) modulo 64, which is 48 bytes with the default values. In the CRB binary of `bwx13` the function `k_rand_nop256` starts at `0x9270` (48 modulo 64) and its loop 1 at `0x9294` (20 modulo 64) [Ref1]. |
| 1522 | `#endif` | Ends the `#ifndef` of line 1520. |

### Macro `DEF_RANDREAD`: the read loop with a scrambled order of the blocks (lines 1523 to 1569)

| Line | Source | Explanation |
|---:|---|---|
| 1523 | `#if defined(__aarch64__)` | Opens the AArch64 branch of the `rand_nop` kernels. Its `#else` is at line 1570 and its `#endif` at line 1589. The CRB binary of `bwx13` holds this branch: its listing shows the instructions of lines 1538 to 1561 [Ref1]. |
| 1524 | `#define RAND_LDP8 \` | Starts the macro `RAND_LDP8`: a piece of assembly text with the 8 `ldp` instructions of one block. Both loops use it (line 1549, line 1557). The backslash at the end of a line continues the macro on the next line. |
| 1525 | `    "ldp q0, q1, [x13]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the block at the address in `x13` into `q0` and `q1`. `\n\t` ends one line of the assembly text and indents the next one. |
| 1526 | `    "ldp q2, q3, [x13, #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 1527 | `    "ldp q4, q5, [x13, #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 1528 | `    "ldp q6, q7, [x13, #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. |
| 1529 | `    "ldp q8, q9, [x13, #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 1530 | `    "ldp q10, q11, [x13, #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 1531 | `    "ldp q12, q13, [x13, #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 1532 | `    "ldp q14, q15, [x13, #224]\n\t"` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. So the 8 instructions load the 256 B of one block, each byte once. Nothing uses the loaded values. This is the last line of `RAND_LDP8`. |
| 1533 | `#define DEF_RANDREAD(name, nops) \` | Starts the macro `DEF_RANDREAD(name, nops)`. It defines one kernel function that reads the blocks of its range in the order of `rand_index`, with `nops` instructions of the kind `nop` after the loads of each block. |
| 1534 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 194). For the three kernels it is 48 bytes with the default values (lines 1514 to 1522). |
| 1535 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. `noinline`: gcc must keep the function separate from its caller. The three kernels have the type `T_READ` in the kernel table (line 1637). So the worker calls them and counts their bytes as it does for every read kernel. With `--stop common` each call gets one chunk of 2 MiB, and each finished call adds the size of the chunk to the byte count (lines 1851 to 1852). |
| 1536 | `    { \` | Opens the body of the kernel function. It holds one `asm` statement and no C variable. |
| 1537 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. gcc copies the text into the function. `volatile` tells gcc to keep the statement. |
| 1538 | `            "lsr x10, %[n], #5\n\t" \` | `lsr` shifts `n` right by 5 bits and puts the result into `x10`: the number of words divided by 32. This is `nb`, the number of blocks of 256 B. `%[n]` stands for the register that gcc chose for `n`. In the listing of `bwx13` it is `x1` [Ref1]. |
| 1539 | `            "sub x12, x10, #1\n\t" \` | `sub` puts `nb - 1` into `x12`. Loop 1 uses it as a mask for the block number. |
| 1540 | `            "tst x10, x12\n\t" \` | `tst` computes `nb & (nb - 1)` and sets the condition flags. The result is 0 only when `nb` is a power of two. |
| 1541 | `            "mov x9, #0\n\t" \` | `mov` sets the step number `i` in `x9` to 0. |
| 1542 | `            "b.ne 2f\n\t" \` | `b.ne 2f` branches forward to the label `2` when the result of line 1540 was not 0. So a range whose `nb` is not a power of two runs loop 2. Every other range goes on with loop 1. These 5 instructions run once per call, before the loops. |
| 1543 | `            "1:\n\t" \` | `1:` is the label at the start of loop 1, the loop of the scrambled order. In the CRB binary of `bwx13` loop 1 of each of the three functions starts at an address of 20 modulo 64, the loop offset of `k_asmread` [Ref1]. |
| 1544 | `            "add x11, x9, x9\n\t" \` | `add` puts `2 * i` into `x11`. |
| 1545 | `            "add x11, x11, #1\n\t" \` | Adds 1: `x11` holds `2 * i + 1`. |
| 1546 | `            "mul x11, x11, x9\n\t" \` | `mul` multiplies by `i`: `x11` holds `i * (2 * i + 1)`. Only the low 64 bits of the product are kept. |
| 1547 | `            "and x11, x11, x12\n\t" \` | `and` keeps the low bits with the mask `nb - 1`: `x11` holds the block number of this step, the value of `rand_index` (line 1509). |
| 1548 | `            "add x13, %[a], x11, lsl #8\n\t" \` | `add` puts the address of the block into `x13`: the start `a` of the range plus 256 times the block number. `lsl #8` shifts the block number left by 8 bits, which multiplies it by 256. `%[a]` stands for the register of `a`. The 5 instructions of lines 1544 to 1548 compute the address from the step number in every loop pass. They load no data. |
| 1549 | `            RAND_LDP8 \` | The 8 `ldp` of `RAND_LDP8` (lines 1524 to 1532): they load the 256 B of the block at the address in `x13`. Each byte of the block is read once, and nothing uses the loaded values. |
| 1550 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the second macro argument into text. The assembler writes the instruction `nop` that many times here: 0, 96 or 256 times. A `nop` does nothing and loads nothing. |
| 1551 | `            "add x9, x9, #1\n\t" \` | Adds 1 to the step number `i`. |
| 1552 | `            "cmp x9, x10\n\t" \` | `cmp` compares the step number with `nb`. |
| 1553 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the step number is below `nb`. The end test stands after the loop body, so the body runs at least once. One pass of loop 1 handles one block of 256 B: 5 instructions for the address, 8 `ldp`, the `nop` instructions and these 3. That is 16 instructions in `rand_nop0`, 112 in `rand_nop96` and 272 in `rand_nop256`. The loop of `asmread` has 11 instructions per 256 B, `read_nop96` has 107 and `read_nop256` has 267. So a `rand_nop` kernel has 5 more instructions per block than the kernel with the same number of `nop`. |
| 1554 | `            "b 3f\n\t" \` | After loop 1: `b 3f` branches forward to the label `3` at the end of the text. So loop 2 does not run after loop 1. |
| 1555 | `            "2:\n\t" \` | `2:` is the label at the start of loop 2, the loop for a range whose `nb` is not a power of two. It reads the blocks in rising address order. |
| 1556 | `            "add x13, %[a], x9, lsl #8\n\t" \` | `add` puts the address of block `i` into `x13`: the start `a` plus 256 times the step number. |
| 1557 | `            RAND_LDP8 \` | The 8 `ldp` of `RAND_LDP8`: they load the 256 B of block `i`. |
| 1558 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | The same number of `nop` instructions as in loop 1 (line 1550). |
| 1559 | `            "add x9, x9, #1\n\t" \` | Adds 1 to the step number `i`. |
| 1560 | `            "cmp x9, x10\n\t" \` | `cmp` compares the step number with `nb`. |
| 1561 | `            "b.lo 2b\n\t" \` | `b.lo 2b` branches back to the label `2` while the step number is below `nb`. One pass of loop 2 has one `add` for the address, 8 `ldp`, the `nop` instructions and these 3: 12 instructions in `rand_nop0`. |
| 1562 | `            "3:\n\t" \` | `3:` is the label at the end of the assembly text. Both loops end here. |
| 1563 | `            : \` | The list of outputs of the statement is empty: the text changes no C variable. |
| 1564 | `            : [a] "r"(a), [n] "r"(n) \` | The inputs: `a` and `n`, each in a general register. The text reads them and does not change them. |
| 1565 | `            : "x9", "x10", "x11", "x12", "x13", \` | Starts the clobber list. It tells gcc what the text changes. This line names the general registers `x9` to `x13`. They hold the step number, `nb`, the block number, the mask and the block address. |
| 1566 | `              "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Continues the clobber list: the vector registers `v0` to `v7`. |
| 1567 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call. In the listing of `bwx13` these are 4 `stp` instructions at the start of the function and 4 `ldp` instructions before `ret` [Ref1]. |
| 1568 | `              "memory", "cc"); \` | Ends the clobber list and the statement. `"memory"` says that the text accesses memory that no operand names. `"cc"` says that the text changes the condition flags. |
| 1569 | `    }` | Ends the kernel function and the macro. |

### Stand-in of `DEF_RANDREAD` and the kernels `rand_nop0`, `rand_nop96`, `rand_nop256` (lines 1570 to 1593)

| Line | Source | Explanation |
|---:|---|---|
| 1570 | `#else` | `#else` of the `#if` of line 1523. The compiler reads the lines up to line 1588 only for a machine that is not AArch64. A build on CRB, an Arm machine, does not compile them. |
| 1571 | `/* Stand-in: the same blocks in the same order, every word of a block. If` | Comment: the stand-in reads the same blocks in the same order, and it reads every word of a block. The sentence about `rand_visit` starts here. |
| 1572 | ` * rand_visit is not NULL, the stand-in also counts the visits of each block` | Comment: when `rand_visit` is not `NULL`, the stand-in also counts how many times it visits each block. |
| 1573 | ` * there (the self-test sets it). */` | Comment: the counts go into the array that `rand_visit` points to. The self-test sets the pointer. |
| 1574 | `static uint8_t *rand_visit;` | `rand_visit`: a pointer to one count per block, or `NULL`. It starts as `NULL`, so a normal run counts nothing. The variable exists only in a stand-in build. |
| 1575 | `#define DEF_RANDREAD(name, nops) \` | Starts the stand-in form of the macro `DEF_RANDREAD(name, nops)`: a plain C loop over the same blocks in the same order. The macro argument `nops` is not used in this branch. |
| 1576 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel, as in the AArch64 branch. |
| 1577 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range and `n` its length in 8-byte words. |
| 1578 | `    { \` | Opens the body of the kernel function. |
| 1579 | `        size_t nb = n / 32; \` | `nb`: the number of blocks of 256 B in the range: the word count divided by 32. |
| 1580 | `        for (size_t i = 0; i < nb; i++) { \` | A loop over the steps, from 0 to `nb - 1`. |
| 1581 | `            size_t j = rand_index(i, nb); \` | `j`: the number of the block that this step reads (`rand_index`, line 1507). |
| 1582 | `            const volatile uint64_t *p = a + 32 * j; \` | `p` points to the first word of block `j`: 32 words per block after `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 1583 | `            if (rand_visit) \` | Tests whether the self-test has set `rand_visit`. |
| 1584 | `                rand_visit[j]++; \` | Then the count of block `j` grows by 1. |
| 1585 | `            for (size_t w = 0; w < 32; w++) \` | A loop over the 32 words of the block. |
| 1586 | `                (void)p[w]; \` | Reads word `w` and drops the value. So the stand-in reads every byte of the block once. |
| 1587 | `        } \` | Ends the loop of line 1580. |
| 1588 | `    }` | Ends the kernel function and the macro. |
| 1589 | `#endif` | Ends the `#if` of line 1523. |
| 1590 | `DEF_RANDREAD(rand_nop0, 0)` | Creates `k_rand_nop0`, the kernel `rand_nop0`: the blocks in the scrambled order, with no `nop`. The listing of the CRB build of `bwx13` shows the function with 43 instructions: 9 before loop 1, 16 in loop 1, one branch to the end, 12 in loop 2, then 4 `ldp` and `ret` [Ref1]. |
| 1591 | `DEF_RANDREAD(rand_nop96, 96)` | Creates `k_rand_nop96`, the kernel `rand_nop96`: the same loops with 96 `nop` after the 8 `ldp` of each block. In the listing of `bwx13` one pass of loop 1 has 112 instructions and one pass of loop 2 has 108 [Ref1]. |
| 1592 | `DEF_RANDREAD(rand_nop256, 256)` | Creates `k_rand_nop256`, the kernel `rand_nop256`: the same loops with 256 `nop` per block. In the listing of `bwx13` one pass of loop 1 has 272 instructions and one pass of loop 2 has 268 [Ref1]. |

### Fourth pad after the kernels: the start address of `call` (lines 1594 to 1604)

| Line | Source | Explanation |
|---:|---|---|
| 1594 | `/*` | Opens the comment about the fourth pad. |
| 1595 | ` * The pad after the kernels, a fourth time, with the same value. The function` | Comment: the pad after the kernels is needed a fourth time. The pad of `bwx12` (line 1480) now stands before the `rand_nop` kernels. The new pad has the same value. |
| 1596 | ` * after the kernels starts at that value modulo 64, as in bwx12. build13.sh` | Comment: the function after the kernels then starts at that value modulo 64, as it does in `bwx12`. The sentence about the build script starts here. |
| 1597 | ` * prints the placement.` | Comment: the script `build13.sh` in the same folder prints the placement. Its build record of CRB holds `call=24` for `bwx13` and for `bwx12`, and it says that the placement up to `timed_sequence_hot` is the same [Ref2]. |
| 1598 | ` */` | Ends the comment. |
| 1599 | `#ifndef PAD_after_kernels13` | Compiles line 1600 only when the build command has not defined `PAD_after_kernels13`. |
| 1600 | `#define PAD_after_kernels13 PAD_after_kernels` | `PAD_after_kernels13` gets the value of `PAD_after_kernels`, which is 24 (line 1068). |
| 1601 | `#endif` | Ends the `#ifndef` of line 1599. |
| 1602 | `PLACE(after_kernels13);` | `PLACE(after_kernels13)` pads the code up to a 64 B boundary and then adds 24 bytes of value 0. So the function after it starts at 24 modulo 64. In `bwx13` that function is `call` (line 1647): the build record of CRB gives `call=24` for the start of `call` modulo 64 [Ref2]. |
| 1603 | `/* bwx13- */` | Comment: a marker. The block that line 1482 opened ends here. |

### The kernel table `kernels` (lines 1605 to 1642)

| Line | Source | Explanation |
|---:|---|---|
| 1605 | `/* The function is named k_<name>. The cast to void (*)(void) is undone by` | Comment: the function of a kernel has the name `k_` plus the kernel name. The table stores its address with a cast to the common pointer type `void (*)(void)`. |
| 1606 | ` * call() according to the type. */` | Comment: `call` (line 1647) undoes the cast according to the type of the kernel. |
| 1607 | `static const struct kdef {` | Starts `struct kdef`, the type of one entry of the kernel table. |
| 1608 | `    const char *name;` | `name`: the name of the kernel. It is the word that `--seq` accepts. `parse_seq` (line 1906) compares each word of `--seq` with the names and stores the index of the entry that matches. |
| 1609 | `    enum ktype type;` | `type`: one of `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD` (line 284). It tells `call` which arguments the function takes. |
| 1610 | `    void (*fn)(void);` | `fn`: the pointer to the kernel function, stored as one common pointer type. `call` casts it back to the real type before it calls the function. |
| 1611 | `} kernels[] = {` | Ends the structure and starts the kernel table `kernels[]`. For each interval the worker takes the entry of the kernel from this table (line 1814) and passes it to `call`. |
| 1612 | `#define K(name, type) { #name, type, (void (*)(void))k_##name }` | The macro `K(name, type)` writes one entry. `K(read, T_READ)` becomes `{ "read", T_READ, (void (*)(void))k_read }`. `#name` gives the kernel name as text. `k_##name` gives the function. |
| 1613 | `    K(read, T_READ), K(write, T_WRITE), K(copy, T_COPY),` | Entries 0 to 2: `read`, `write` and `copy`, the C kernels with NEON intrinsics. `read` is entry 0 with the type `T_READ`: the new read kernel. |
| 1614 | `    K(asmread, T_READ), K(asmwrite, T_WRITE), K(asmcopy, T_COPY),` | Entries 3 to 5: `asmread`, `asmwrite` and `asmcopy`, the hand-written assembly kernels. `asmread` is entry 3 with the type `T_READ`. |
| 1615 | `    K(oldread, T_OLDREAD), K(oldwrite, T_WRITE), K(oldcopy, T_COPY),` | Entries 6 to 8: `oldread`, `oldwrite` and `oldcopy`, the old kernels. `oldread` is entry 6 with the type `T_OLDREAD`: the old read kernel. |
| 1616 | `    K(asmread2, T_READ), K(asmwrite2, T_WRITE), K(asmcopy2, T_COPY), K(oldread2, T_OLDREAD),` | Entries 9 to 12: the A/A copies `asmread2`, `asmwrite2`, `asmcopy2` and `oldread2`. |
| 1617 | `    K(asmcopy_c, T_COPY), K(asmcopy_c_add, T_COPY), K(asmcopy_c_reg, T_COPY),` | Entries 13 to 15: the copy kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. |
| 1618 | `    K(read_nop4, T_READ), K(read_nop8, T_READ), K(read_nop16, T_READ), K(read_nop32, T_READ),` | Entries 16 to 19: the read kernels `read_nop4`, `read_nop8`, `read_nop16` and `read_nop32`. |
| 1619 | `    K(read_sparse, T_READ),` | Entry 20: the read kernel `read_sparse`. The entries 0 to 20 are the kernels that the first runner `bwx` and the version `bwx8` already have. |
| 1620 | `/* bwx10+ */` | Comment: a marker. The entries that the version `bwx10` added start here. |
| 1621 | `    K(read_pf256, T_READ), K(read_pf512, T_READ), K(read_pf1024, T_READ), K(read_pf2048, T_READ),` | Entries 21 to 24: the read kernels `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048`. |
| 1622 | `    K(read_1pl, T_READ),` | Entry 25: `read_1pl` with the type `T_READ`. The entries 21 to 25 are the 5 kernels that `bwx10` added. |
| 1623 | `/* bwx10- */` | Comment: a marker. The entries of `bwx10` end here. |
| 1624 | `/* bwx11+ */` | Comment: a marker. The entries that the version `bwx11` added start here. |
| 1625 | `    K(read_nop64, T_READ), K(read_nop96, T_READ), K(read_nop128, T_READ),` | Entries 26 to 28: `read_nop64`, `read_nop96` and `read_nop128`, the 3 kernels that `bwx11` added. |
| 1626 | `/* bwx11- */` | Comment: a marker. The entries of `bwx11` end here. |
| 1627 | `/* bwx12+ */` | Comment: a marker. The entries that the version `bwx12` added start here. |
| 1628 | `    K(read_nop48, T_READ), K(read_nop56, T_READ), K(read_nop72, T_READ), K(read_nop80, T_READ), K(read_nop88, T_READ),` | Entries 29 to 33: the read kernels `read_nop48`, `read_nop56`, `read_nop72`, `read_nop80` and `read_nop88`. |
| 1629 | `    K(read_nop112, T_READ), K(read_nop160, T_READ), K(read_nop192, T_READ), K(read_nop256, T_READ),` | Entries 34 to 37: `read_nop112`, `read_nop160`, `read_nop192` and `read_nop256`. |
| 1630 | `    K(read_dadd2, T_READ), K(read_dadd4, T_READ), K(read_dadd8, T_READ), K(read_dadd16, T_READ), K(read_iadd16, T_READ),` | Entries 38 to 42: the read kernels `read_dadd2`, `read_dadd4`, `read_dadd8`, `read_dadd16` and `read_iadd16`. |
| 1631 | `    K(read_sp24, T_READ), K(read_sp32, T_READ), K(read_sp40, T_READ), K(read_sp48, T_READ), K(read_sp56, T_READ),` | Entries 43 to 47: the read kernels `read_sp24`, `read_sp32`, `read_sp40`, `read_sp48` and `read_sp56`. |
| 1632 | `    K(read_1pl_nop96, T_READ),` | Entry 48: the read kernel `read_1pl_nop96`. |
| 1633 | `    K(write_nop32, T_WRITE), K(write_nop96, T_WRITE), K(write_nop128, T_WRITE), K(write_nop256, T_WRITE),` | Entries 49 to 52: the write kernels `write_nop32`, `write_nop96`, `write_nop128` and `write_nop256`, with the type `T_WRITE`. |
| 1634 | `    K(copy_nop96, T_COPY), K(copy_nop192, T_COPY),` | Entries 53 and 54: the copy kernels `copy_nop96` and `copy_nop192`, with the type `T_COPY`. The entries 29 to 54 are the 26 kernels of round 5 (line 40). |
| 1635 | `/* bwx12- */` | Comment: a marker. The entries of `bwx12` end here. |
| 1636 | `/* bwx13+ */` | Comment: a marker. The entries that the version `bwx13` added start here. |
| 1637 | `    K(rand_nop0, T_READ), K(rand_nop96, T_READ), K(rand_nop256, T_READ),` | Entries 55 to 57: `rand_nop0`, `rand_nop96` and `rand_nop256`, the 3 kernels that `bwx13` added. Each has the type `T_READ`. So `call` gives them the arguments of a read kernel (lines 1652 to 1653). |
| 1638 | `/* bwx13- */` | Comment: a marker. The entries of `bwx13` end here. |
| 1639 | `#undef K` | Removes the macro `K`. It is needed only inside the table. |
| 1640 | `};` | Ends the kernel table. |
| 1641 | `#define K_COUNT ((int)(sizeof kernels / sizeof kernels[0]))` | `K_COUNT`: the number of entries of the table. It is the size of the table divided by the size of one entry. In `bwx13` it is 58, and the listing of the CRB build holds 58 kernel functions [Ref1]. The worker calls `k_write` directly for the first touch (line 1802), not through the table. |

### Function `call`: run one kernel on one range of a buffer (lines 1643 to 1666)

| Line | Source | Explanation |
|---:|---|---|
| 1643 | `/* Runs kernel kd on len bytes at byte offset off of the thread's buffers. A` | Comment: the function below runs the kernel `kd` on `len` bytes that start at the byte offset `off` of the buffers of the thread. |
| 1644 | ` * read or write kernel uses buffer a. A copy kernel reads a and writes b. The` | Comment: a read kernel or a write kernel uses the buffer `a`. A copy kernel reads `a` and writes `b`. |
| 1645 | ` * sink of the old read kernel is on the stack of the thread, as it was in the` | Comment: the sink of the old read kernel is the variable that takes its sum. It lies on the stack of the thread (line 1791), as it did in the function `pass` of the old benchmark source. |
| 1646 | ` * old pass(), so the threads do not all store to one shared cache line. */` | Comment: so the threads do not all store to one shared cache line. |
| 1647 | `static void call(const struct kdef *kd, struct thread *t, size_t off, size_t len, uint64_t v, volatile uint64_t *sink)` | Starts the function `call`. It runs one kernel on one range of a buffer. `kd` is the table entry of the kernel. `t` is the record of the calling thread. `off` and `len` give the range in bytes. `v` is the value that a write kernel stores. `sink` points to the variable that takes the sum of an old read kernel. The worker calls this function once per interval for the warm-up pass (line 1825). With `--stop common` it calls it once for each chunk of the timed loop (line 1851). In the timed loop the function runs between the clock reads `t0` and `t1`. So its own instructions are part of the timed interval, once per chunk. |
| 1648 | `{` | Opens the body of `call`. |
| 1649 | `    uint64_t *a = t->a + off / 8;` | `a`: the address of the first word of the range. `t->a` points to 8-byte words. So `off / 8` words are `off` bytes. |
| 1650 | `    size_t n = len / 8;` | `n`: the length of the range in 8-byte words. One chunk of 2 MiB gives 262144 words. The warm-up pass of a `--seq` entry of 256 MiB gives 33554432 words. |
| 1651 | `    switch (kd->type) {` | Chooses the form of the call by the type of the kernel. |
| 1652 | `    case T_READ:` | The case of a read kernel. |
| 1653 | `        ((read_fn)kd->fn)(a, n);` | Casts the pointer to the type `read_fn` (line 285) and calls the kernel with the address and the word count. The kernel returns nothing. |
| 1654 | `        break;` | Leaves the `switch`. |
| 1655 | `    case T_OLDREAD:` | The case of an old read kernel. |
| 1656 | `        *sink = ((oldread_fn)kd->fn)(a, n);` | Calls the kernel, which returns its sum, and stores the sum to `*sink`. `sink` points to a `volatile` variable on the stack of the worker (line 1791). So the compiler must keep the store and must compute the sum. The listing of `k_oldread` in `bwx13` holds the adds [Ref1]. This path has one store of 8 bytes per call that the `T_READ` path does not have. In the timed loop of `--stop common` that is one store per chunk (line 1851). |
| 1657 | `        break;` | Leaves the `switch`. |
| 1658 | `    case T_WRITE:` | The case of a write kernel. |
| 1659 | `        ((write_fn)kd->fn)(a, n, v);` | Casts the pointer to the type `write_fn` and calls the write kernel with the address, the word count and the value `v` to store. |
| 1660 | `        break;` | Leaves the `switch`. |
| 1661 | `    case T_COPY:` | The case of a copy kernel. |
| 1662 | `        ((copy_fn)kd->fn)(t->b + off / 8, a, n);` | Casts the pointer to the type `copy_fn` and calls the copy kernel. The kernel reads the range of the buffer `a` and writes the same range of the buffer `b`. |
| 1663 | `        break;` | Leaves the `switch`. |
| 1664 | `    }` | Ends the `switch` of line 1651. |
| 1665 | `}` | Ends the function `call`. It returns no value. |

### Function `read_smaps`: the page state of the buffers (lines 1667 to 1699)

| Line | Source | Explanation |
|---:|---|---|
| 1667 | `/* Page state (handoff B.6). For each of the n buffers (a NULL entry is` | Comment: the function below reads the page state. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. The function works on `n` buffers and skips an entry that is `NULL`. |
| 1668 | ` * skipped): the entry of /proc/self/smaps whose start is the buffer and whose` | Comment: for each buffer it looks for the entry of the Linux file `/proc/self/smaps` whose start is the buffer address. |
| 1669 | ` * end is the buffer plus buf_len(). Without such an entry both values stay -1` | Comment: the end of that entry must be the buffer address plus `buf_len()`. Without such an entry both values stay -1. |
| 1670 | ` * and are printed as NA. */` | Comment: a value of -1 is printed as `NA`. |
| 1671 | `static void read_smaps(struct page *pg, uint64_t *const *buf, int n)` | Starts the function `read_smaps`. For each of the `n` buffer addresses in `buf` it looks for the mapping of that buffer in `/proc/self/smaps`. It writes two values to `pg`: the size of the mapping and the part of it on 2 MiB pages, both in kB. In a process with more than one thread `main` calls it before the first interval and after each interval (line 3274). During the call all workers wait at the barrier (line 1809 or line 1887). So the call is not timed. |
| 1672 | `{` | Opens the body of `read_smaps`. In a process with one thread the worker calls the function before each interval (line 1828): after the warm-up pass and before its barrier wait of line 1831. The timed interval starts later, at the clock read `t0` (line 1844). This call is not timed either. |
| 1673 | `    char line[256];` | `line`: the buffer for one line of the file, at most 255 characters. |
| 1674 | `    int cur = -1;` | `cur`: the index of the buffer whose mapping the loop below is reading, or -1 for no buffer. |
| 1675 | `    size_t len = buf_len();` | `len`: the buffer length from `buf_len` (line 457). |
| 1676 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 1677 | `        pg[i].kb_total = pg[i].kb_huge = -1;` | Sets both values of the entry to -1. The value -1 means that the buffer was not found. |
| 1678 | `    FILE *f = fopen("/proc/self/smaps", "r");` | Opens `/proc/self/smaps` for reading. The file lists every memory mapping of the process. So it holds the buffers of all threads. |
| 1679 | `    if (!f)` | Tests whether the file did not open. |
| 1680 | `        return;` | In that case the function returns, and all values stay -1. |
| 1681 | `    while (fgets(line, sizeof line, f)) {` | Starts a loop that reads the file line by line. It ends at the end of the file. |
| 1682 | `        unsigned long s, e;` | `s` and `e`: the start address and the end address of a mapping. |
| 1683 | `        char perms[8];` | `perms`: the word after the two addresses, at most 7 characters. In the file it holds the access rights of the mapping. The function does not use its content. |
| 1684 | `        if (sscanf(line, "%lx-%lx %7s", &s, &e, perms) == 3) {` | `sscanf` returns 3 when the line starts with `start-end`, two hexadecimal addresses, and a word after them. Such a line is the first line of a mapping. |
| 1685 | `            cur = -1;` | At the first line of a mapping `cur` is first set back to -1. |
| 1686 | `            for (int i = 0; i < n; i++)` | Then a loop compares the mapping with every buffer. |
| 1687 | `                if (buf[i] && (unsigned long)(uintptr_t)buf[i] == s && e == s + len)` | A buffer matches when its entry is not `NULL`, the mapping starts at the buffer address and the mapping ends exactly `len` bytes after it. The comment of `alloc_buf` (lines 462 to 464) gives the reason for the exact test: no-access ranges stand before and after each buffer, so Linux lists the buffer as one mapping of its own. |
| 1688 | `                    cur = i;` | On a match `cur` becomes the index of that buffer. When no buffer matches, `cur` stays -1. Then the next lines of that mapping store nothing, and they cannot change the values of a buffer that was read before. |
| 1689 | `        } else if (cur >= 0) {` | Every other line belongs to the mapping whose first line was read last. This branch runs only when that mapping is a buffer (`cur >= 0`). |
| 1690 | `            sscanf(line, "Size: %ld kB", &pg[cur].kb_total);` | This `sscanf` stores a number only when the line starts with `Size:`. The number is the size of the mapping in kB and goes to `kb_total`. |
| 1691 | `            sscanf(line, "AnonHugePages: %ld kB", &pg[cur].kb_huge);` | This `sscanf` stores a number only when the line starts with `AnonHugePages:`. The number is the part of the mapping on 2 MiB pages in kB and goes to `kb_huge`. All other lines store nothing. |
| 1692 | `        }` | Ends the `else if` of line 1689. |
| 1693 | `    }` | Ends the loop of line 1681. |
| 1694 | `    fclose(f);` | Closes the file. |
| 1695 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 1696 | `        if (pg[i].kb_total < 0 \|\| pg[i].kb_huge < 0)` | Tests whether one of the two values of the entry is still below 0. |
| 1697 | `            pg[i].kb_total = pg[i].kb_huge = -1;` | In that case both values are set to -1. `print_p` (line 1726) prints a value below 0 as `NA`. |
| 1698 | `}` | Ends the function `read_smaps`. |

### Function `read_vmstat`: four counters of the whole system (lines 1700 to 1717)

| Line | Source | Explanation |
|---:|---|---|
| 1700 | `/* Four counters of /proc/vmstat. They count for the whole system. -1: not found. */` | Comment: the function below reads four counters of the Linux file `/proc/vmstat`. They count for the whole system, not for one buffer. The value -1 means that a counter was not found. |
| 1701 | `static void read_vmstat(long long vm[4])` | Starts the function `read_vmstat`. It reads the four counters into `vm[0]` to `vm[3]`, in the order of the names in line 1703. They become the last four columns of every P row. In a process with more than one thread `main` calls it once before the first interval and once after each interval (line 3275). In a process with one thread the worker calls it before each interval (line 1829): after the warm-up pass and before its barrier wait of line 1831. The timed interval starts later, at the clock read `t0` (line 1844). It is not timed. |
| 1702 | `{` | Opens the body of `read_vmstat`. |
| 1703 | `    static const char *name[4] = { "thp_fault_alloc", "thp_fault_fallback", "thp_collapse_alloc", "pgmigrate_success" };` | `name`: the names of the four counters. The Linux documentation gives their meanings [Ref7]. `thp_fault_alloc` counts the 2 MiB pages that Linux gave at a page fault. `thp_fault_fallback` counts the page faults at which Linux could not give a 2 MiB page and used small pages. `thp_collapse_alloc` counts the 2 MiB pages that Linux made later from a range of small pages. `pgmigrate_success` counts the pages that Linux moved to another place in physical memory. |
| 1704 | `    char key[64];` | `key`: the buffer for one name of the file, at most 63 characters. |
| 1705 | `    long long val;` | `val`: the number that follows the name. |
| 1706 | `    for (int i = 0; i < 4; i++)` | A loop over the four values. |
| 1707 | `        vm[i] = -1;` | Sets the value to -1. The value -1 means that the counter was not found. |
| 1708 | `    FILE *f = fopen("/proc/vmstat", "r");` | Opens `/proc/vmstat` for reading. |
| 1709 | `    if (!f)` | Tests whether the file did not open. |
| 1710 | `        return;` | In that case the function returns with the four values at -1. |
| 1711 | `    while (fscanf(f, "%63s %lld", key, &val) == 2)` | Each line of the file holds a name and a number. `fscanf` reads one such pair per loop pass. The loop ends when `fscanf` finds no further pair, for example at the end of the file. |
| 1712 | `        for (int i = 0; i < 4; i++)` | A loop over the four names. |
| 1713 | `            if (!strcmp(key, name[i]))` | Tests whether the name from the file equals name `i`. `strcmp` returns 0 for equal texts. |
| 1714 | `                vm[i] = val;` | On a match the number goes to the matching place in `vm`. |
| 1715 | `    fclose(f);` | Closes the file. |
| 1716 | `}` | Ends the function `read_vmstat`. |

### Function `print_na`: one csv field, or `NA` (lines 1718 to 1725)

| Line | Source | Explanation |
|---:|---|---|
| 1718 | `static void print_na(long long v)` | Starts the function `print_na`. It prints one more field of a csv row: a comma and then the number `v`. For a negative `v` it prints `,NA`. The functions `read_smaps` (line 1671) and `read_vmstat` (line 1701) store -1 for a value that they did not find. So such a value shows as `NA` in a P row. |
| 1719 | `{` | Opens the body of `print_na`. |
| 1720 | `    if (v < 0)` | Tests whether `v` is negative. |
| 1721 | `        printf(",NA");` | A negative value prints as a comma and the text `NA` (not available). |
| 1722 | `    else` | The case of a value of 0 or more. |
| 1723 | `        printf(",%lld", v);` | Prints a comma and the number in decimal. |
| 1724 | `}` | Ends the function `print_na`. |

### Function `print_p`: one P row, the page state of one buffer (lines 1726 to 1735)

| Line | Source | Explanation |
|---:|---|---|
| 1726 | `static void print_p(int round, int pos, int tid, char buffer, const struct page *pg, const long long vm[4])` | Starts the function `print_p`. It prints one P row: the page state of one buffer at one reading. `round`, `pos` and `tid` are the round, the position and the thread index. `buffer` is the letter `a` or `b`. `pg` holds the two page values of the buffer. `vm` holds four counters of the Linux file `/proc/vmstat`. In a process with more than one thread `main` calls it once per buffer after each reading of the page state (line 3280). In a process with one thread `main` calls it in line 3236 and line 3238. |
| 1727 | `{` | Opens the body of `print_p`. |
| 1728 | `    printf("P,%d,%d,%d,%c", round, pos, tid, buffer);` | Columns 1 to 5 of the row: the letter `P`, the round, the position, the thread index and the buffer letter. The position is -1 in the rows of the reading before the first interval (line 3206). In every other row of a process with more than one thread it is the position of the interval that has ended directly before the reading. In a process with one thread the row holds the state that the worker read before the interval of that position (line 1826). |
| 1729 | `    print_na(pg->kb_total);` | Column 6, `kB_total`: the size of the mapping of the buffer. The unit is kB of 1024 bytes. `read_smaps` (line 1671) took the value from the line `Size` of the Linux file `/proc/self/smaps`. A value that it did not find prints as `NA`. |
| 1730 | `    print_na(pg->kb_huge);` | Column 7, `kB_huge`: the part of the buffer that lies on 2 MiB pages, in kB of 1024 bytes. `read_smaps` took it from the line `AnonHugePages` of the same file. |
| 1731 | `    for (int i = 0; i < 4; i++)` | Loop over the four counters of `/proc/vmstat`. |
| 1732 | `        print_na(vm[i]);` | Columns 8 to 11: the counters `thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc` and `pgmigrate_success`, in this order (line 1703). They count for the whole system, not for this buffer. `main` passes the same array `vm` for all buffers of one reading (line 3280). So all P rows of one reading hold the same four values. |
| 1733 | `    printf("\n");` | Ends the row with a line break. |
| 1734 | `}` | Ends the function `print_p`. |

### Function `open_counters`: open the counter group of one thread (lines 1736 to 1764)

| Line | Source | Explanation |
|---:|---|---|
| 1736 | `/* Counters (handoff B.8): one group per thread, user mode only, opened by the` | Comment: the counters follow section B.8 of the file `handoff.md`, the specification of the first runner. Each thread has one counter group. The counters count in user mode only. The sentence about who opens them goes on in line 1737. |
| 1737 | ` * pinned thread for itself. An event that does not open is printed as NA. */` | Comment: the pinned thread opens the counters for itself. An event that does not open is printed as `NA` (lines 3260 to 3261). |
| 1738 | `static void open_counters(struct thread *t)` | Starts the function `open_counters`. It opens one counter per entry of `--events` for the calling thread and joins the counters into one group. With `--count` each worker calls it once (line 1800), after the pinning and before it maps its buffer. `t` is the record of the calling thread. |
| 1739 | `{` | Opens the body of `open_counters`. |
| 1740 | `    t->group_fd = -1;` | Start state: no group leader (`group_fd` is -1). The group leader is the first counter of a counter group. |
| 1741 | `    t->nopen = 0;` | Start state: 0 open counters. |
| 1742 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `--events`, in the order of the list. `cfg.nev` is their number. |
| 1743 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 1744 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. So every option that the next lines do not set is off. The field `disabled` also stays 0. So a counter counts from the moment it is opened. |
| 1745 | `        a.type = (uint32_t)cfg.pmu_type;` | `type` selects the PMU (performance monitoring unit, the hardware event counters of a core). It is the value of `--pmu-type`. |
| 1746 | `        a.size = sizeof a;` | `size` gives Linux the size of the structure. |
| 1747 | `        a.config = cfg.ev_code[e];` | `config` is the event code of this entry of `--events`. The program passes the code to Linux and does not interpret it. |
| 1748 | `        a.exclude_kernel = 1;` | `exclude_kernel = 1`: the counter does not count while the CPU runs code of the Linux kernel. |
| 1749 | `        a.exclude_hv = 1;` | `exclude_hv = 1`: the counter does not count code of a hypervisor. A hypervisor is the software that runs virtual machines. With these two fields the counter counts in user mode only: while the thread runs the code of the program itself. The specification of the first runner says that counter code without these two fields fails without root rights on CRB [Ref5]. |
| 1750 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | `read_format` chooses what one `read` of the group returns. `PERF_FORMAT_GROUP`: the values of all counters of the group in one reading. The two other flags add the enabled time and the running time of the group [Ref6]. |
| 1751 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, t->group_fd, 0);` | The system call `perf_event_open` opens the counter. It returns a file descriptor: the number that later calls such as `read` use for the open counter. A negative value means failure. The arguments `0` and `-1` are the pid and the cpu argument of the call [Ref5]. Together they mean: count the calling thread, on any CPU that it runs on. With `--cpus` the thread is pinned, so this is one CPU. The argument `t->group_fd` is -1 for the first counter, which starts a new group. A later counter passes the file descriptor of the leader and joins its group. The last argument `0` means no flags. |
| 1752 | `        if (fd < 0) {` | Tests whether the open failed. |
| 1753 | `            if (t->idx == 0)` | Only thread 0 writes a message. So an event that fails in every thread gives one message, not one per thread. |
| 1754 | `                fprintf(stderr, "perf_event_open %s (type %ld code 0x%llx): %s (printed as NA)\n", cfg.ev_name[e],` | The message goes to stderr: the word `perf_event_open`, the event name, the PMU type, the event code in hexadecimal, the error text of Linux and the words `printed as NA`. This line holds the format and the event name. |
| 1755 | `                        cfg.pmu_type, (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 1754: the PMU type, the event code and the error text (`strerror(errno)`). |
| 1756 | `            t->ev_pos[e] = -1;` | The event gets the position -1. `main` prints `NA` for it in the C rows (lines 3259 to 3261). |
| 1757 | `            continue;` | The loop goes on with the next event. The thread does not stop. |
| 1758 | `        }` | Ends the `if` of line 1752. |
| 1759 | `        t->ev_pos[e] = t->nopen++;` | The open succeeded. `ev_pos[e]` gets the position of this event in a group reading: 0 for the first open counter, 1 for the next. `nopen` counts the open counters of the thread. |
| 1760 | `        if (t->group_fd < 0)` | Tests whether the group has no leader yet. |
| 1761 | `            t->group_fd = fd;` | The first counter that opens becomes the leader of the group. `group_fd` keeps its file descriptor, and every group reading uses it (line 1778). The file descriptors of the other counters are not kept. The function `worker` never closes, resets or stops a counter. |
| 1762 | `    }` | Ends the loop over the events (line 1742). |
| 1763 | `}` | Ends the function `open_counters`. |

### Function `cpu_ns`: the CPU time of the calling thread (lines 1765 to 1771)

| Line | Source | Explanation |
|---:|---|---|
| 1765 | `static uint64_t cpu_ns(void)` | Starts the function `cpu_ns`. It returns the CPU time that the calling thread has used so far, in ns. With `--count` the worker calls it once before and once after each timed interval (line 1842, line 1874). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 1766 | `{` | Opens the body of `cpu_ns`. |
| 1767 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 1768 | `    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);` | Reads the Linux clock `CLOCK_THREAD_CPUTIME_ID` into `ts`. This clock counts the CPU time of the calling thread only. |
| 1769 | `    return (uint64_t)ts.tv_sec * 1000000000UL + (uint64_t)ts.tv_nsec;` | Returns the time in ns: the seconds times 1000000000, plus the nanoseconds. |
| 1770 | `}` | Ends the function `cpu_ns`. |

### Function `read_group`: one reading of the counter group (lines 1772 to 1787)

| Line | Source | Explanation |
|---:|---|---|
| 1772 | `/* Group read: nr, time_enabled, time_running, then one value per open event. */` | Comment: the layout of one group reading: the number of counters (`nr`), the enabled time, the running time, then one value per open event [Ref6]. |
| 1773 | `static void read_group(const struct thread *t, struct counts *c)` | Starts the function `read_group`. It takes one reading of all counters of the thread `t` and stores it in `c`. With `--count` the worker calls it once before and once after each timed interval (line 1841, line 1875). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 1774 | `{` | Opens the body of `read_group`. |
| 1775 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest reading: 3 header words plus 8 counter values (`MAX_EV` is 8). Each word has 8 bytes. |
| 1776 | `    if (t->group_fd < 0)` | Tests whether the thread has no open counter. |
| 1777 | `        return;` | Such a thread returns here. Then `c` keeps the zeros that the worker wrote in line 1823. |
| 1778 | `    if (read(t->group_fd, buf, sizeof buf) < (ssize_t)(3 * sizeof buf[0]) \|\| buf[0] != (uint64_t)t->nopen) {` | One `read` system call on the leader returns the whole group: the number of counters `nr`, the enabled time, the running time, then one value per counter [Ref6]. The reading is rejected when it has fewer than 24 bytes (the 3 header words). It is also rejected when `nr` is not the number of counters that this thread opened. |
| 1779 | `        perror("read of the counter group");` | A rejected reading: `perror` prints the words `read of the counter group` and the reason that Linux gave to stderr. |
| 1780 | `        exit(2);` | The whole program then ends with exit status 2. |
| 1781 | `    }` | Ends the `if` of line 1778. |
| 1782 | `    c->enabled = buf[1];` | Stores the enabled time of the group, in ns: how long the counters were enabled. |
| 1783 | `    c->running = buf[2];` | Stores the running time of the group, in ns: how long the counters really counted. `main` prints the difference between the two readings of an interval as `enabled_ns` and `running_ns` in the C row (lines 3255 to 3256). |
| 1784 | `    for (int i = 0; i < t->nopen; i++)` | Loop over the open counters of the thread. |
| 1785 | `        c->val[i] = buf[3 + i];` | Stores one value per open counter, in the order in which the counters were opened. `main` prints for each event the difference between the reading after the interval and the reading before it (line 3263). |
| 1786 | `}` | Ends the function `read_group`. |

### Function `worker`: start values, pinning, counters, buffers and first touch (lines 1788 to 1811)

| Line | Source | Explanation |
|---:|---|---|
| 1788 | `static void *worker(void *arg)` | Starts the function `worker`, the start function of every worker thread. `main` creates the workers in line 3175. `arg` points to the record of the thread. |
| 1789 | `{` | Opens the body of `worker`. |
| 1790 | `    struct thread *t = arg;` | `t`: the record of this thread. `main` has set its index `idx` and its CPU `cpu` (lines 3173 to 3174). |
| 1791 | `    volatile uint64_t sink;` | `sink`: a volatile variable on the stack of this thread. `call` stores there the sum that an old read kernel returns (line 1656). The compiler must keep this store. So it cannot remove the adds of the old read kernel. Each thread has its own `sink`. So the threads do not all store to one shared cache line. |
| 1792 | `    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */` | Comment: the store value is known only when the program runs, and its 8 bytes are not all equal. So the compiler cannot turn the store loop into a call of `memset`, the library function that fills memory with one byte value. |
| 1793 | `    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;` | `v`: the value that `k_write` stores into the 8-byte words of a buffer at the first touch (line 1802). It is the process id (`getpid`) plus the thread index plus 1, times a fixed 64-bit constant. The timed loop gives `v` plus a counter to a write kernel (line 1851, line 1865). The read kernels do not use `v`. |
| 1794 | `    uint64_t k = 0; /* intervals this thread has run (--stop common) */` | `k`: the number of timed intervals that this thread has started. Line 1833 compares it with the shared counter `gen`. The comment says that `--stop common` uses it. |
| 1795 | `    int64_t min_ns = (int64_t)(cfg.min_s * 1e9);` | `min_ns`: the `--min-ms` value in ns. Only the loop of `--stop pass` uses it (line 1871). |
| 1797 | `    if (cfg.ncpus)` | Tests whether a CPU list was given (`--cpus`). |
| 1798 | `        pin_cpu(t->cpu);` | CPU pinning. The thread pins itself to its CPU with `pin_cpu` (line 446). `main` chose the CPU in line 3174. Every later line of the worker runs on that CPU. Without `--cpus` the thread is not pinned. |
| 1799 | `    if (cfg.count)` | Tests whether counting is on (`--count`). |
| 1800 | `        open_counters(t);` | The thread opens its counters with `open_counters` (line 1738). The counters count from this moment on. So they also count during the first touch and the warm-up passes. A C row holds only the change between the two readings of one interval (line 1841, line 1875). |
| 1801 | `    t->a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 465) maps buffer `a` of this thread. The buffer starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. `alloc_buf` also asks Linux for 2 MiB pages for it (with `--no-thp`: for no such pages). Each thread has its own buffer and reads only its own buffer. |
| 1802 | `    k_write(t->a, cfg.bytes / 8, v); /* first touch by this thread */` | First touch. `k_write` (line 562) stores `v` into `cfg.bytes / 8` words of 8 bytes, from the start of the buffer: every word of the `--bytes` range. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 459). Then the worker does not write the rest. No kernel call reaches the rest: the size of a `--seq` entry is at most `--bytes` (line 3154). The pinned thread does this write itself, before any read. Linux assigns the memory pages at this first write. This line is not timed. The comment says: first touch by this thread. |
| 1803 | `    if (cfg.two_buffers) {` | Tests whether the thread needs a second buffer `b`. It exists only with `--two-buffers` or with a copy kernel in `--seq` (lines 3159 to 3160). |
| 1804 | `        t->b = alloc_buf();` | Maps buffer `b` in the same way as buffer `a`. |
| 1805 | `        k_write(t->b, cfg.bytes / 8, v);` | First touch of buffer `b`: the same write as in line 1802. It is not timed. |
| 1806 | `    }` | Ends the `if` of line 1803. |
| 1807 | `    if (cfg.threads > 1) {` | Tests whether the process has more than one worker. Only then the two barrier waits of lines 1808 to 1809 exist. The barrier releases its waiting threads when all workers and the main thread have called it (line 3168). |
| 1808 | `        pthread_barrier_wait(&bar); /* the buffers exist: main() reads the first page state */` | First wait at the barrier. It returns when all workers have mapped and written their buffers and `main` has arrived in line 3208. Then `main` copies the buffer addresses and reads the page state for the P rows with position -1. The comment says: the buffers exist, and `main` reads the first page state. |
| 1809 | `        pthread_barrier_wait(&bar); /* main() has read it */` | Second wait at the barrier. The worker blocks until that reading is done. `main` releases the workers in line 3277. The comment says: `main` has read it. |
| 1810 | `    }` | Ends the `if` of line 1807. |

### Function `worker`: one interval, from the warm-up pass to the clock read `t0` (lines 1812 to 1845)

| Line | Source | Explanation |
|---:|---|---|
| 1812 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds. `--rounds N` runs the `--seq` list N times, and the rounds count from 0. |
| 1813 | `        for (int pos = 0; pos < cfg.nseq; pos++) {` | Loop over the positions of the `--seq` list. One pass of this loop is one timed interval. `main` runs the same two loops (lines 3202 to 3203). |
| 1814 | `            const struct kdef *kd = &kernels[cfg.seq[pos].k];` | `kd`: the entry of the kernel table for this position: name, type and function pointer (line 1611). The kernels run in the order of the `--seq` list. |
| 1815 | `            size_t size = cfg.seq[pos].bytes;` | `size`: the number of bytes of this position. It is the size after `@` in the `--seq` entry, or the `--bytes` value for an entry without `@` (line 3153). |
| 1816 | `            size_t nchunk = size / HUGE_BYTES;` | `nchunk`: the number of whole 2 MiB pieces in `size`. It is 128 for a size of 256 MiB. Only the start offset of line 1818 uses it. |
| 1817 | `            /* --start offset (handoff B.5): thread i starts at (i * 37 mod n) * 2 MiB */` | Comment: with `--start offset` thread i starts at the 2 MiB piece with the number i times 37 modulo n. Here n is `nchunk`. The comment names section B.5 of the file `handoff.md`, the specification of the first runner. |
| 1818 | `            size_t off = cfg.start_offset && nchunk ? ((size_t)t->idx * 37 % nchunk) * HUGE_BYTES : 0;` | `off`: the byte offset in the buffer at which this thread starts its timed work. With `--start common` it is 0. It is also 0 for a size below 2 MiB. With `--start offset` it is `idx * 37 % nchunk` times 2 MiB. So most threads start at a place of their buffer other than byte 0. Thread 0 starts at byte 0, and with one piece (`nchunk` is 1) every thread does. |
| 1819 | `            uint64_t per_byte = kd->type == T_COPY ? 2 : 1; /* copy counts read+write bytes */` | `per_byte`: 2 for a copy kernel, 1 for every other kernel. A copy kernel counts every byte two times: once read, once written. |
| 1820 | `            uint64_t bytes = 0, p = 0;` | `bytes`: the byte count of the timed interval. `p`: the number of kernel calls of the interval with `--stop common`, or of passes with `--stop pass`. Both start at 0. |
| 1821 | `            int64_t sched = 0, deadline = 0, t0, t1;` | Clock values in ns: `sched` (the common start time), `deadline`, `t0` (the start of the timed interval) and `t1` (the clock read after the latest kernel work). |
| 1822 | `            struct result r;` | `r`: the result record of this thread for this interval (line 327). |
| 1823 | `            memset(&r, 0, sizeof r);` | `memset` sets every field of `r` to 0. |
| 1825 | `            call(kd, t, 0, size, v, &sink); /* warm-up */` | Warm-up pass, not timed. One call of the kernel of this position over the range from byte 0 to `size`, through `call` (line 1647). So before every timed interval the thread has run the same kernel once over the whole range. Between this pass and the timed interval lie the barrier wait, the wait for the common start and the first counter reading (lines 1831 to 1843). In a process with one thread the page-state reading of lines 1826 to 1830 also lies between them. |
| 1826 | `            if (cfg.threads == 1) {` | Tests whether the process has one worker only. Only such a process reads the page state here, in the worker: after the warm-up pass and before the barrier. |
| 1827 | `                uint64_t *buf[2] = { t->a, t->b };` | `buf`: the addresses of the two buffers of the thread. `t->b` is NULL when the thread has no second buffer. |
| 1828 | `                read_smaps(r.pg, buf, 2);` | `read_smaps` (line 1671) reads the page state of both buffers into `r.pg`. It skips a NULL entry. |
| 1829 | `                read_vmstat(r.vm);` | `read_vmstat` (line 1701) reads the four counters of `/proc/vmstat` into `r.vm`. `main` prints both readings as P rows after the interval (lines 3235 to 3239). |
| 1830 | `            }` | Ends the `if` of line 1826. |
| 1831 | `            pthread_barrier_wait(&bar);` | Barrier wait after the warm-up pass. The thread blocks until all workers have ended their warm-up pass and `main` has arrived in line 3220. Then all of these threads continue. A thread whose warm-up pass ends early waits here and reads no memory. |
| 1832 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Only then lines 1833 to 1838 run. |
| 1833 | `                while (atomic_load(&gen) != k + 1)` | Common start, step 1. The thread repeats an empty loop until the shared counter `gen` equals `k + 1`. `main` adds 1 to `gen` in line 3225, after it has stored the start time and the deadline of this interval. In this loop the thread stays on its CPU and does not sleep. |
| 1834 | `                    ;` | The empty body of the loop of line 1833. |
| 1835 | `                sched = atomic_load(&t_sched_ns);` | Copies the common start time into `sched`. `main` computed it in line 3222: its clock reading plus 2 ms (`LEAD_NS`). All workers read the same value. |
| 1836 | `                deadline = atomic_load(&deadline_ns);` | Copies the common deadline into `deadline`. `main` computed it in line 3224: the start time plus the `--min-ms` value. All workers read the same value. |
| 1837 | `                while (now_ns() < sched)` | Common start, step 2. The thread reads the clock again and again until the clock reaches `sched`. It leaves the loop at its first clock read at or after the start time. This wait is not timed. |
| 1838 | `                    ;` | The empty body of the loop of line 1837. |
| 1839 | `            }` | Ends the `if` of line 1832. |
| 1840 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). |
| 1841 | `                read_group(t, &r.c0);` | First counter reading (`read_group`, line 1773). It goes into `r.c0`. With `--stop common` it runs after the wait for the common start. With `--stop pass` it runs directly after the barrier. In both cases it runs before the clock read of line 1844. So it is not inside the timed interval. But `t0` is later than the common start time by at least the duration of this line and of line 1842. |
| 1842 | `                r.c0.cpu_ns = cpu_ns();` | Reads the thread CPU time (`cpu_ns`, line 1765) into `r.c0`. |
| 1843 | `            }` | Ends the `if` of line 1840. |
| 1844 | `            t0 = now_ns();` | Start of the timed interval. The thread reads the clock (`now_ns`, line 358) into `t0`. Each thread has its own `t0`. Nothing above this line is inside the timed interval. |
| 1845 | `            k++;` | Counts this interval. At the next interval line 1833 waits for the next value of `gen`. This line runs after the clock read `t0`, so it is the first statement inside the timed interval. |

### Function `worker`: the timed loop and the two stop rules (lines 1846 to 1872)

| Line | Source | Explanation |
|---:|---|---|
| 1846 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Lines 1849 to 1857 are the timed loop of this stop rule. |
| 1847 | `                /* chunks of 2 MiB (or the whole entry if it is smaller); the` | Comment: the kernel runs on chunks of 2 MiB, or on the whole entry when the entry is smaller than 2 MiB. The sentence goes on in line 1848. |
| 1848 | `                 * position continues from chunk to chunk and wraps */` | Comment: the position in the buffer goes on from chunk to chunk. At the end of the entry it returns to the start. |
| 1849 | `                size_t chunk = size < CHUNK_BYTES ? size : CHUNK_BYTES, at = off;` | `chunk`: the number of bytes of one kernel call: 2097152 bytes (2 MiB, `CHUNK_BYTES`), or `size` when `size` is smaller. `at`: the byte offset of the next chunk in the buffer. It starts at `off` (line 1818). |
| 1850 | `                do {` | Starts the timed loop. Its body runs at least once. |
| 1851 | `                    call(kd, t, at, chunk, v + p++, &sink);` | Timed kernel call. `call` (line 1647) runs the kernel on the chunk at byte offset `at`. The kernel gets the address of the chunk and its length in 8-byte words: 262144 words for a chunk of 2 MiB. So the kernel function is entered once per chunk: 128 times per pass over a buffer of 256 MiB. For a kernel of the type `T_OLDREAD`, `call` stores the returned sum in `sink` after each call. A kernel of the type `T_READ` returns nothing. `v + p++` gives a write kernel a new value in every call and counts the calls. A read kernel does not get this argument. |
| 1852 | `                    bytes += per_byte * chunk;` | Bytes counted. Each finished call adds `per_byte * chunk`: 2097152 bytes for a 2 MiB chunk of a read kernel. This is the size of the range that was passed to the kernel. Nothing is counted inside a kernel. So the number is the same for every read kernel. It is also used for `read_1pl`, which loads 16 B of each 64 B line. |
| 1853 | `                    at += chunk;` | Moves `at` to the next chunk. |
| 1854 | `                    if (at == size)` | Tests whether `at` has reached the end of the entry. |
| 1855 | `                        at = 0;` | After the last chunk the offset returns to 0. For a size of 256 MiB this is after chunk 127. So the kernel calls go from the start offset `off` to the end of the range. Then they repeat the whole range from byte 0, until the interval ends. With `--start common` the offset `off` is 0, and the first pass is also a whole pass. |
| 1856 | `                    t1 = now_ns();` | Clock read after every chunk: `t1` is the clock value after this call. The last `t1` is the end of the timed interval. So the timed interval is the code from line 1844 to this line: the kernel calls, the byte count, the step of the offset and one clock read per chunk. |
| 1857 | `                } while (t1 < deadline);` | Stop rule of `--stop common`. The loop repeats while `t1` is before the common deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted. The deadline is the same for all threads. Each thread has its own end time `t1`. |
| 1858 | `            } else {` | The branch of `--stop pass`. Lines 1860 to 1871 are the timed loop of this stop rule. |
| 1859 | `                /* whole passes; with an offset a pass is [off, size) then [0, off) */` | Comment: the thread runs whole passes. With a start offset one pass is the range from `off` to the end of the entry and then the range from 0 to `off`. |
| 1860 | `                uint64_t passes_per_check = CHECK_BYTES / size;` | `passes_per_check`: the number of passes between two clock reads. It is 8 MiB (`CHECK_BYTES`) divided by `size`, rounded down. So for a size below 8 MiB that does not divide 8 MiB, the clock is read after less than 8 MiB. |
| 1861 | `                if (passes_per_check == 0)` | Tests whether the division gave 0. That is the case for every size above 8 MiB. |
| 1862 | `                    passes_per_check = 1;` | The value is then 1: the thread reads the clock after every pass. |
| 1863 | `                do {` | Starts the timed loop of `--stop pass`. Its body runs at least once. |
| 1864 | `                    for (uint64_t c = 0; c < passes_per_check; c++, p++) {` | Runs `passes_per_check` passes without a clock read between them. `p` counts the passes. |
| 1865 | `                        call(kd, t, off, size - off, v + p, &sink);` | Timed kernel call: the range from `off` to the end of the entry. With an `off` of 0 this is the whole entry. `v + p` gives a write kernel a new value in every pass. |
| 1866 | `                        if (off)` | Tests whether the thread has a start offset above 0. |
| 1867 | `                            call(kd, t, 0, off, v + p, &sink);` | Second kernel call of the pass: the range from byte 0 to `off`. So each pass covers every byte of the entry once. |
| 1868 | `                        bytes += per_byte * size;` | Bytes counted: each pass adds `per_byte * size`. This is the size of the entry, or twice the size for a copy kernel. Nothing is counted inside a kernel. |
| 1869 | `                    }` | Ends the `for` of line 1864. |
| 1870 | `                    t1 = now_ns();` | Clock read after the passes: `t1`. The clock is never read inside a pass. The last `t1` is the end of the timed interval. So with this stop rule the timed interval is the code from line 1844 to this line. |
| 1871 | `                } while (t1 - t0 < min_ns);` | Stop rule of `--stop pass`. The loop repeats while less than `min_ns` (the `--min-ms` value) has passed after the `t0` of this thread. So a thread stops only at the end of a whole pass, after a full group of `passes_per_check` passes. The threads stop at different times. |
| 1872 | `            }` | Ends the `if` and `else` of line 1846. |

### Function `worker`: after the timed interval, the result record and the barrier waits (lines 1873 to 1892)

| Line | Source | Explanation |
|---:|---|---|
| 1873 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). The timed interval has ended at the last clock read `t1` (line 1856 or line 1870). |
| 1874 | `                r.c1.cpu_ns = cpu_ns();` | Reads the thread CPU time into `r.c1` (`cpu_ns`). |
| 1875 | `                read_group(t, &r.c1);` | Second counter reading, into `r.c1` (`read_group`). The order is the reverse of lines 1841 to 1842. So the timed interval lies between the two readings of the thread CPU time, and these lie between the two counter readings. The counter values of a C row therefore cover the timed interval plus a few calls around it: the two readings of the thread CPU time and the clock read `t0`. |
| 1876 | `            }` | Ends the `if` of line 1873. |
| 1877 | `            r.bytes = bytes;` | Stores the byte count of the interval in the result record. |
| 1878 | `            r.t_start = t0;` | Stores `t0`, the start of the timed interval. |
| 1879 | `            r.t_end = t1;` | Stores the last `t1`, the end of the timed interval. `main` computes the elapsed time of a thread as `t_end - t_start` (line 3232, line 3245). |
| 1880 | `            r.t_sched = cfg.stop_common ? sched : t0;` | Stores the common start time. `main` prints it in the T row as `t_sched_s` (line 3246). With `--stop pass` there is no common start time, and the field gets `t0`. |
| 1881 | `            r.late = cfg.stop_common && t0 - sched > LATE_NS;` | Late flag. With `--stop common` it is set when `t0` is more than 100000 ns (100 us, `LATE_NS`) after the common start time. `main` then prints `late` in the last column of the T row (line 3247). The program does nothing else with the flag: the interval runs, and its bytes are counted. |
| 1882 | `            t->res = r;` | Copies the record into the thread structure. `main` reads it there after the barrier wait of line 1883. |
| 1883 | `            pthread_barrier_wait(&bar);` | Barrier wait at the end of the interval. The thread blocks until all workers have ended their interval and `main` waits in line 3227. A thread that has stopped reads no memory while other threads finish their last chunk or pass. |
| 1884 | `            /* main() reads the page state of all buffers. The warm-up pass of` | Comment: `main` reads the page state of all buffers at this point. The sentence about the next warm-up pass starts here. |
| 1885 | `             * the next interval starts only after that reading (handoff B.6). */` | Comment: the warm-up pass of the next interval starts only after that reading. The comment names section B.6 of the file `handoff.md`, the specification of the first runner. |
| 1886 | `            if (cfg.threads > 1)` | Tests whether the process has more than one worker. Only then the second barrier wait exists. |
| 1887 | `                pthread_barrier_wait(&bar);` | Second barrier wait at the end of the interval. While the workers block here, `main` prints the I, T and C rows of the interval and reads the page state of all buffers (lines 3229 to 3276). `main` releases the workers in line 3277. Then each worker starts the warm-up pass of the next interval. `main` prints the P rows and the `# page_read` line after the release (lines 3278 to 3281). So this output can run while the workers do their warm-up pass. The output ends before the next timed interval starts: the barrier of line 1831 lets the workers pass only when `main` has finished the output and waits in line 3220. |
| 1888 | `        }` | Ends the loop over the positions (line 1813). The worker calls no sleep function. So between two intervals lie only the waits, the readings and the warm-up pass of the rows above. |
| 1889 | `    }` | Ends the loop over the rounds (line 1812). |
| 1890 | `    return NULL;` | After the last interval of the last round the thread returns. `main` waits for the end of all threads in line 3287. |
| 1891 | `}` | Ends the function `worker`. |

### Function `usage`: option summary, then exit status 2 (lines 1893 to 1905)

| Line | Source | Explanation |
|---:|---|---|
| 1893 | `static void usage(void)` | Starts the function `usage`. It prints the option summary to stderr and ends the program with exit status 2. `main` calls it for an argument that it does not accept and for settings that fail one of its checks (lines 3132 to 3158), for example `--threads` without `--cpus`. |
| 1894 | `{` | Opens the body of `usage`. |
| 1895 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to stderr. Its text stands in lines 1896 to 1902. |
| 1896 | `            "usage: bwx --seq LIST [--threads T --cpus LIST] [--bytes B] [--min-ms MS] [--no-thp]\n"` | Text of the message: the first usage line, with the options `--seq`, `--threads`, `--cpus`, `--bytes`, `--min-ms` and `--no-thp`. The text names the program `bwx`, the name of the first version of the runner. |
| 1897 | `            "           [--rounds N] [--stop pass\|common] [--start common\|offset] [--two-buffers]\n"` | Text of the message: the options `--rounds`, `--stop`, `--start` and `--two-buffers`. |
| 1898 | `            "           [--count --pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options of the counters (`--count`, `--pmu-type`, `--events`), and the two environment variables that can give the counter settings in their place (lines 3139 to 3145). |
| 1899 | `            "       bwx --selftest \| --list\n"` | Text of the message: the second form of the command, with `--selftest` or `--list`. |
| 1900 | `            "  --seq: comma-separated entries KERNEL or KERNEL@SIZE; --list prints the kernel names\n"` | Text of the message: an entry of `--seq` is a kernel name, or a kernel name with `@` and a size. `--list` prints the kernel names. |
| 1901 | `            "  sizes must be multiples of 256; with --stop common: multiples of 2M, or below 2M\n"` | Text of the message: a size must be a multiple of 256. With `--stop common` it must be a multiple of 2M or below 2M (lines 3154 to 3155). |
| 1902 | `            "  --pmu-type and CODE: the perf_event_attr fields type and config of the core PMU (CODE may be 0x..)\n");` | Text of the message: `--pmu-type` and the code of an event go into the fields `type` and `config` of the structure `perf_event_attr` (line 1745, line 1747). A code may be written in hexadecimal with `0x`. This line ends the `fprintf` call. |
| 1903 | `    exit(2);` | Ends the program with exit status 2. |
| 1904 | `}` | Ends the function `usage`. |

### Function `parse_seq`: read the `--seq` list (lines 1906 to 1924)

| Line | Source | Explanation |
|---:|---|---|
| 1906 | `static void parse_seq(char *list)` | Starts the function `parse_seq`. It turns the text after `--seq` into the entries of `cfg.seq`. `main` calls it in line 3113. |
| 1907 | `{` | Opens the body of `parse_seq`. |
| 1908 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. Each pass of the loop handles one entry, in the order of the list. This order is the order in which the kernels run in each round. |
| 1909 | `        char *at = strchr(tok, '@');` | `at`: the place of an `@` in the entry, or NULL when the entry has none. An entry may have the form `KERNEL@SIZE`. |
| 1910 | `        int k = 0;` | `k`: the index into the kernel table. The search of line 1913 starts at entry 0. |
| 1911 | `        if (at)` | Tests whether the entry has an `@`. |
| 1912 | `            *at = '\0';` | Ends the name at the `@`: a zero byte replaces the `@`. |
| 1913 | `        while (k < K_COUNT && strcmp(tok, kernels[k].name))` | Searches the kernel table `kernels[]` (line 1611) for the name, from the first entry on. `strcmp` returns 0 when two texts are equal. The loop stops at the entry with this name. When no entry has the name, it stops with `k` equal to `K_COUNT`, the number of entries. |
| 1914 | `            k++;` | The body of the search loop: goes on to the next entry of the table. |
| 1915 | `        if (k == K_COUNT \|\| cfg.nseq == MAX_SEQ) {` | Tests for two defects: the name is not in the table, or `cfg.seq` already holds 64 entries (`MAX_SEQ`). |
| 1916 | `            fprintf(stderr, "bad --seq entry: %s\n", tok);` | Prints `bad --seq entry:` and the name to stderr. |
| 1917 | `            exit(2);` | Ends the program with exit status 2. |
| 1918 | `        }` | Ends the `if` of line 1915. |
| 1919 | `        cfg.seq[cfg.nseq].k = k;` | Stores the index of the kernel in the next free entry of `cfg.seq`. |
| 1920 | `        cfg.seq[cfg.nseq].bytes = at ? parse_bytes(at + 1) : 0;` | Stores the size of the entry: the text after the `@`, read by `parse_bytes` (line 365). An entry without `@` gets the size 0 here. `main` later replaces 0 by the `--bytes` value (line 3153). |
| 1921 | `        cfg.nseq++;` | Counts the entry. |
| 1922 | `    }` | Ends the loop of line 1908. |
| 1923 | `}` | Ends the function `parse_seq`. |

### Function `parse_events`: read the `--events` list (lines 1925 to 1950)

| Line | Source | Explanation |
|---:|---|---|
| 1925 | `/* "NAME=CODE,..." or "CODE,...". A code without a name gets the name of its` | Comment: the list has the form `NAME=CODE,...` or `CODE,...`. The sentence about a code without a name starts here. |
| 1926 | ` * position in the list of handoff B.8. */` | Comment: a code without a name gets the name of its place in the event list of section B.8 of the file `handoff.md`, the specification of the first runner. The code has one more rule that the comment does not name: from the sixth place on the name is `ev` plus the place number (lines 1940 to 1941). |
| 1927 | `static void parse_events(char *list)` | Starts the function `parse_events`. It turns the text of an event list into the names `cfg.ev_name` and the codes `cfg.ev_code`. `main` calls it with the text after `--events` (line 3127), and with the text of the environment variable `BWX_EVENTS` (line 3143). |
| 1928 | `{` | Opens the body of `parse_events`. |
| 1929 | `    static const char *by_pos[5] = { "cycles", "instructions", "l1d_refill", "l2d_refill", "ll_miss_rd" };` | `by_pos`: the names for an entry without a name at one of the first 5 places of the list: `cycles`, `instructions`, `l1d_refill`, `l2d_refill` and `ll_miss_rd`. |
| 1930 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. One pass of the loop handles one entry. |
| 1931 | `        char *eq = strchr(tok, '='), *code = eq ? eq + 1 : tok, *end;` | `eq`: the place of the `=` sign in the entry, or NULL. `code`: the text of the code. It is the text after the `=`, or the whole entry when the entry has no `=`. `end` is used in line 1942. |
| 1932 | `        if (eq == tok \|\| cfg.nev == MAX_EV \|\| (eq && (size_t)(eq - tok) >= sizeof cfg.ev_name[0])) {` | Tests for three defects: an entry with an empty name (the `=` is its first character), a 9th entry (`MAX_EV` is 8), and a name of 32 characters or more (the size of one entry of `cfg.ev_name`). |
| 1933 | `            fprintf(stderr, "bad --events entry: %s\n", tok);` | Prints `bad --events entry:` and the entry to stderr. |
| 1934 | `            exit(2);` | Ends the program with exit status 2. |
| 1935 | `        }` | Ends the `if` of line 1932. |
| 1936 | `        if (eq)` | Tests whether the entry has a name. |
| 1937 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "%.*s", (int)(eq - tok), tok);` | Copies the text before the `=` as the name of the event. The format `%.*s` prints only the first `eq - tok` characters of the entry. The program uses the name as a column title in the header line of the C rows (line 3194) and in the error message of `open_counters` (line 1754). |
| 1938 | `        else if (cfg.nev < 5)` | The case of an entry without a name at one of the first 5 places of the list. |
| 1939 | `            strcpy(cfg.ev_name[cfg.nev], by_pos[cfg.nev]);` | The entry gets the name of `by_pos` for its place. |
| 1940 | `        else` | The case of an entry without a name at place 6 or later. |
| 1941 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "ev%d", cfg.nev);` | The entry gets the name `ev` plus its place number counted from 0, for example `ev5`. |
| 1942 | `        cfg.ev_code[cfg.nev] = strtoull(code, &end, 0);` | `strtoull` with base 0 turns the code text into a number. With base 0 a text that starts with `0x` is read as hexadecimal. |
| 1943 | `        if (end == code \|\| *end != '\0') {` | Tests whether the text is not a whole number: no digit was read, or other text follows the number. |
| 1944 | `            fprintf(stderr, "bad --events code: %s\n", code);` | Prints `bad --events code:` and the code text to stderr. |
| 1945 | `            exit(2);` | Ends the program with exit status 2. |
| 1946 | `        }` | Ends the `if` of line 1943. |
| 1947 | `        cfg.nev++;` | Counts the entry. |
| 1948 | `    }` | Ends the loop of line 1930. |
| 1949 | `}` | Ends the function `parse_events`. |

### Trial mode: the comment, the constants and the name tables (lines 1951 to 1986)

| Line | Source | Explanation |
|---:|---|---|
| 1951 | `/*` | Comment: starts the comment about the trial mode. The code of the trial mode goes from here to line 3042. `main` enters it only when an argument is the word `--trial` (lines 3075 to 3077). |
| 1952 | ` * Trial mode (--trial). Design: crb/new-test-kernel/tackle-8mb.md, "Runner` | Comment: the option `--trial` selects the trial mode. Its design is the section "Runner design" of the file `tackle-8mb.md`. |
| 1953 | ` * design". Formats: DECISIONS-bwx8.md.` | Comment: the file `DECISIONS-bwx8.md` describes the formats: the plan file and the output rows. |
| 1954 | ` *` | Comment: an empty line inside the comment. |
| 1955 | ` * The plan file gives the trials of the process. The whole plan is read and` | Comment: the plan file lists the trials of the process. The program reads the whole plan first. The sentence goes on in line 1956. |
| 1956 | ` * checked before the process pins, allocates or opens a counter. A defect` | Comment: the program checks the whole plan before it pins a thread, maps a buffer or opens a counter. The sentence about a defect starts here. |
| 1957 | ` * ends the process with status 2.` | Comment: a defect of the plan ends the process with exit status 2 (line 2710). |
| 1958 | ` *` | Comment: an empty line inside the comment. |
| 1959 | ` * One trial is a list of windows: previous activity (1), prefix (4),` | Comment: one trial is a list of windows. A window runs one kernel on one range of the buffer for a fixed time. The list starts with 1 window of previous activity and 4 windows of the prefix. |
| 1960 | ` * predecessor (1), target (nwin). timed_sequence() runs them. It calls only` | Comment: the list goes on with 1 window of the predecessor and `nwin` target windows. The function `timed_sequence` (line 2151) runs the windows. The comment does not name one case: with `--hot-copy` the function `timed_sequence_hot` (line 2212) runs them in its place. The sentence about its calls starts here. |
| 1961 | ` * the kernels and the clock. With count "read" it also reads the counter` | Comment: `timed_sequence` calls only the kernels and the clock. With the counter state `read` it also reads the counter group. The sentence goes on in line 1962. |
| 1962 | ` * group and the thread CPU clock at the boundaries of the target windows.` | Comment: with the counter state `read` it also reads the thread CPU time. Both readings are taken at the boundaries of the target windows. |
| 1963 | ` * Page state, context switches, counter open and close, and all output lie` | Comment: the readings of the page state and of the context switches, the opening and the closing of the counters, and all output are named here. The sentence ends in line 1964. |
| 1964 | ` * outside the timed sequence.` | Comment: all the steps of line 1963 lie outside the timed sequence. |
| 1965 | ` */` | Comment: the end of the comment. |
| 1966 | `#include <stdarg.h>` | Includes the header `stdarg.h`. It gives `va_list`, `va_start` and `va_end` for a function with a variable number of arguments. The function `plan_bad` uses them (line 2710). |
| 1967 | `#include <sys/resource.h>` | Includes the header `sys/resource.h`. It gives the call `getrusage`, which the function `switches` uses (line 2312). |
| 1969 | `#define BIN_NS 10000000L     /* requested width of a bin: 10 ms */` | `BIN_NS`: the requested width of a bin: 10000000 ns (10 ms). A bin is a part of a target window. Its record holds a clock time and the bytes up to that time (line 2002). |
| 1970 | `#define TRACE_CAP (1L << 20) /* --trace: events kept per trial */` | `TRACE_CAP`: the largest number of events that the trace keeps per trial: 1048576 (2 to the power 20). The trace is the event log of the option `--trace`. |
| 1971 | `#define PLAN_LINE1 "# bwx8-plan v1"` | `PLAN_LINE1`: the text that the first line of a plan file must have (line 2916). |
| 1972 | `#define PLAN_LINE3 "# trial cond rep prev pfx pred tgt nwin win_ms count bins"` | `PLAN_LINE3`: the text that the third line of a plan file must have (line 2921). It names the 11 fields of a trial line. |
| 1973 | `#define PLAN_FIELDS 11` | `PLAN_FIELDS`: a trial line of the plan has 11 fields. |
| 1974 | `#define MAX_PAIRS 64` | `MAX_PAIRS`: the second line of a plan holds at most 64 pairs of the form `key=value` (line 2799). |
| 1975 | `#define MAX_NWIN 4096` | `MAX_NWIN`: a trial has at most 4096 target windows (line 2851). |
| 1976 | `#define MAX_MS 3600000L` | `MAX_MS`: a duration of the plan is at most 3600000 ms (1 hour). |
| 1977 | `#define MAX_REC_BYTES (256UL << 20) /* bound of the record storage of one plan */` | `MAX_REC_BYTES`: the records of one plan may need at most 256 MiB (268435456 bytes) of memory (line 2875). |
| 1979 | `enum { PH_PREV, PH_PREFIX, PH_PRED, PH_TARGET };` | Number codes of the four phases of a trial, from 0 to 3: previous activity, prefix, predecessor and target. |
| 1980 | `enum { CS_CLOSED, CS_OPEN, CS_READ, CS_FAIL };` | Number codes of the counter state of a trial, from 0 to 3: closed, open, read and fail. |
| 1981 | `enum { EV_CLOCK, EV_KERNEL_FIRST, EV_COUNT_READ, EV_CPU_CLOCK, EV_PAGE_READ, EV_RUSAGE, EV_OUTPUT, EV_COUNT_OPEN, EV_COUNT_CLOSE };` | Number codes of the nine kinds of trace event: a clock read, the first kernel call of a window, a reading of the counter group, a reading of the thread CPU time, a reading of the page state, a `getrusage` call, an output step, the opening of the counter group and its closing. |
| 1982 | `static const char *const phase_name[] = { "prev", "prefix", "pred", "target" };` | `phase_name`: the printed names of the four phases, in the order of line 1979. The W rows and the TR rows show them (line 2484, line 2550). |
| 1983 | `static const char *const count_name[] = { "closed", "open", "read", "fail" };` | `count_name`: the printed names of the four counter states, in the order of line 1980. The E row shows one of them (line 2545). |
| 1984 | `static const char *const event_name[] = { "clock", "kernel_first", "count_read", "cpu_clock", "page_read",` | `event_name`: the printed names of the trace events, in the order of line 1981. The TR rows show them (line 2550, line 2553). This line holds the first five names. |
| 1985 | `                                          "rusage", "output", "count_open", "count_close" };` | Continues the list of line 1984: the last four names. |

### Trial mode: the structures of the plan, the windows, the records and the trace (lines 1987 to 2042)

| Line | Source | Explanation |
|---:|---|---|
| 1987 | `/* One kernel on a range for a time. k < 0: this part is absent ("-"). */` | Comment: a part is one kernel on one range for a time. A `k` below 0 means that the plan leaves this part out. The plan then holds the text `-` in its place. |
| 1988 | `struct part {` | Starts `struct part`: one kernel field of a trial line of the plan. |
| 1989 | `    int k;` | `k`: the index of the kernel in the kernel table, or -1 for a part that the plan leaves out. |
| 1990 | `    uint64_t size;` | `size`: the number of bytes of the range: the first `size` bytes of the buffer. |
| 1991 | `    long ms;` | `ms`: the duration in ms. The target part has no duration of its own and keeps 0 here. |
| 1992 | `};` | Ends `struct part`. |
| 1994 | `/* One line of the plan. */` | Comment: one line of the plan. |
| 1995 | `struct trial {` | Starts `struct trial`: one trial line of the plan file. |
| 1996 | `    char *f[PLAN_FIELDS]; /* the fields as text, for the S row */` | `f`: the 11 fields of the line as text. `print_s` prints them in the S row (line 2458). The comment says the same. |
| 1997 | `    int nwin, count, bins;` | `nwin`: the number of target windows. `count`: the counter state that the plan asks for (a code of line 1980). `bins`: 1 when the target windows record bins, 0 if not. |
| 1998 | `    long win_ms;` | `win_ms`: the requested duration of one target window, in ms. |
| 1999 | `    struct part prev, pfx, pred, tgt;` | The four parts of the trial: previous activity (`prev`), prefix (`pfx`), predecessor (`pred`) and target (`tgt`). |
| 2000 | `};` | Ends `struct trial`. |
| 2002 | `struct bin {` | Starts `struct bin`: one bin of a target window. |
| 2003 | `    int64_t t_end;  /* a clock read of the window loop */` | `t_end`: the clock time that closed the bin, in ns. The comment says: a clock read of the window loop. The loop reads the clock no more often with bins than without them. |
| 2004 | `    uint64_t bytes; /* bytes since the start of the window */` | `bytes`: the bytes that the window has counted from its start to that clock read. |
| 2005 | `};` | Ends `struct bin`. |
| 2007 | `/* One window. set_windows() fills the first group of fields before the first` | Comment: one window. `set_windows` (line 2387) fills the first group of fields (lines 2010 to 2015) before the first trial. The sentence about the second group starts here. |
| 2008 | ` * trial. timed_sequence() fills the second group. */` | Comment: `timed_sequence` fills the second group of fields (lines 2017 to 2019) when the window runs. The comment does not name one case: with `--hot-copy` the function `timed_sequence_hot` fills them (lines 2242 to 2245). |
| 2009 | `struct win {` | Starts `struct win`: the record of one window. |
| 2010 | `    int k, phase, widx;` | `k`: the index of the kernel in the kernel table. `phase`: the phase of the window (a code of line 1979). `widx`: the number of the window inside its phase, counted from 0. |
| 2011 | `    uint64_t size;` | `size`: the number of bytes that one kernel call covers: the first `size` bytes of the buffer. |
| 2012 | `    uint64_t passes; /* passes between two clock reads */` | `passes`: the number of kernel calls between two clock reads (line 2404). Each call is one whole pass over the range. |
| 2013 | `    int64_t dur_ns;` | `dur_ns`: the requested duration of the window, in ns. |
| 2014 | `    struct bin *bin; /* NULL: no bins */` | `bin`: the storage for the bins of this window. NULL means that the window records no bins. |
| 2015 | `    int bin_cap;` | `bin_cap`: the number of bins that fit into that storage. |
| 2017 | `    int nbin;` | `nbin`: the number of bins that the window closed. |
| 2018 | `    uint64_t bytes;` | `bytes`: the byte count of the window: `size` times the number of kernel calls. |
| 2019 | `    int64_t t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_start`, `t_end`: the clock read at the start of the window and the last clock read of the window, in ns of the Linux clock `CLOCK_MONOTONIC`. |
| 2020 | `};` | Ends `struct win`. |
| 2022 | `/* The record of one trial. */` | Comment: the record of one trial. |
| 2023 | `struct trec {` | Starts `struct trec`: the results of one trial. |
| 2024 | `    struct win *win;` | `win`: the window records of the trial, in the order in which the windows run. |
| 2025 | `    int nw;` | `nw`: the number of windows of the trial. |
| 2026 | `    struct counts *cnt; /* count "read": nwin + 1 readings, one per target boundary */` | `cnt`: the counter readings of the trial, or NULL. Only a trial with the counter state `read` has them: `nwin + 1` readings, one per boundary of the target windows. |
| 2027 | `    struct page pg[2];  /* before and after the timed sequence */` | `pg`: the page state of the buffer before the timed sequence (entry 0) and after it (entry 1). |
| 2028 | `    long long vm[2][4];` | `vm`: the four counters of `/proc/vmstat` before and after the timed sequence. |
| 2029 | `    uint64_t cpu[2];` | `cpu`: the thread CPU time before and after the timed sequence, in ns. |
| 2030 | `    long nvcsw[2], nivcsw[2];` | `nvcsw`, `nivcsw`: the counts of voluntary and of involuntary context switches of the thread, before and after the timed sequence (lines 2313 to 2314). |
| 2031 | `    long minflt[2]; /* minor page faults of the thread, for the --trace check */` | `minflt`: the count of minor page faults of the thread, before and after the timed sequence. A minor page fault is a page fault that Linux serves without disk access. The first touch of a page is one. The comment says that the check of `--trace` uses the count (line 2560). |
| 2032 | `    int state;   /* CS_* */` | `state`: the counter state of the trial as it ran (a code of line 1980). |
| 2033 | `    int sink_ok; /* 1, 0, or -1 if the trial ran no old read */` | `sink_ok`: the result of the sum check of the old read kernel (line 2369): 1 for a right sum, 0 for a wrong sum, -1 when the trial ran no old read kernel. |
| 2034 | `    int read_fail, close_fail;` | `read_fail`: the number of failed counter readings of the trial. `close_fail`: the number of counter file descriptors that did not close when the group was closed for this trial (line 2337). |
| 2035 | `};` | Ends `struct trec`. |
| 2037 | `struct tev {` | Starts `struct tev`: one event of the trace. |
| 2038 | `    int64_t t;` | `t`: the time of the event in ns. It is the time of the latest clock read (line 2088). |
| 2039 | `    int widx;` | `widx`: the window number of the event. Only the event of the first kernel call of a window sets it. |
| 2040 | `    uint8_t ev, phase;` | `ev`: the kind of event (a code of line 1981). `phase`: the phase of the window (a code of line 1979). |
| 2041 | `};` | Ends `struct tev`. |

### Trial mode: the worker state `struct tw` and the global variables (lines 2043 to 2077)

| Line | Source | Explanation |
|---:|---|---|
| 2043 | `/* The worker of the trial mode. */` | Comment: the worker of the trial mode. |
| 2044 | `struct tw {` | Starts `struct tw`: the state of the one worker thread of the trial mode. |
| 2045 | `    struct thread t; /* a, group_fd, ev_pos, nopen: used as in the interval mode */` | `t`: a `struct thread` (line 336), the record that a worker of the interval mode also has. The comment says that the fields `a`, `group_fd`, `ev_pos` and `nopen` are used as in the interval mode. |
| 2046 | `    uint64_t v;      /* every word of the buffer holds v */` | `v`: the value that every 8-byte word of the `--bytes` range of the buffer holds after the first touch (line 2616, line 2622). The comment says: every word of the buffer holds `v`. |
| 2047 | `    int fd[MAX_EV], nfd;` | `fd`: the file descriptors of the open counters. `nfd`: their number. `count_close` closes them (line 2255). |
| 2048 | `    int group_open; /* an open was tried and no close followed */` | `group_open`: 1 when the worker has tried to open the counter group and has not closed it after that. |
| 2049 | `    int open_fail;  /* events that did not open */` | `open_fail`: the number of events that did not open at the last opening of the group. |
| 2050 | `    int close_fail, read_fail;` | `close_fail`, `read_fail`: the numbers of failed `close` calls and of failed group readings. `run_trial` sets both to 0 for each trial (lines 2342 to 2343). |
| 2051 | `    char open_err[160];` | `open_err`: the error text of the first event that did not open. |
| 2052 | `    /* --trace */` | Comment: the fields below belong to the option `--trace`. |
| 2053 | `    struct tev *log;` | `log`: the event log of the trace. It is NULL without `--trace`. |
| 2054 | `    long nlog, ndrop;` | `nlog`: the number of events in the log. `ndrop`: the number of events that did not fit into the log. |
| 2055 | `    int64_t last_t;` | `last_t`: the time of the latest clock read. An event that is not a clock read gets this time. |
| 2056 | `    int cur_phase, cur_widx;` | `cur_phase`, `cur_widx`: the phase and the number of the window whose first kernel call was logged last (line 2112). |
| 2057 | `};` | Ends `struct tw`. |
| 2059 | `static struct {` | Starts the definition of `plan`, the variable that holds the plan and the options of the trial mode. |
| 2060 | `    const char *path;` | `path`: the path of the plan file (option `--plan`). |
| 2061 | `    uint64_t hash;` | `hash`: a 64-bit checksum of the bytes of the plan file (lines 2904 to 2906). |
| 2062 | `    char *pair[MAX_PAIRS];` | `pair`: the `key=value` pairs of the second line of the plan, as text. |
| 2063 | `    int npair;` | `npair`: the number of these pairs. |
| 2064 | `    struct trial *tr;` | `tr`: the trials of the plan, one `struct trial` per trial line. |
| 2065 | `    int n;` | `n`: the number of trials. |
| 2066 | `    int ctl_cpu, trace;` | `ctl_cpu`: the CPU of the controlling thread (option `--ctl-cpu`, default 0). `trace`: 1 with the option `--trace`. |
| 2067 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2068 | `    size_t rec_pad; /* --rec-pad: unused bytes before win[] in the record block */` | `rec_pad`: the value of `--rec-pad`: the number of unused bytes before the window records in the record block (line 2434). |
| 2069 | `    int hot_copy;   /* --hot-copy: timed_sequence_hot() runs the windows */` | `hot_copy`: 1 with the option `--hot-copy`. Then `timed_sequence_hot` runs the windows (lines 2361 to 2362). |
| 2070 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2071 | `} plan;` | Ends the definition of `plan`. Every field starts at 0. |
| 2073 | `static struct trec *rec;` | `rec`: the records of all trials, one `struct trec` per trial. `alloc_records` sets the pointer (line 2430). |
| 2074 | `static struct {` | Starts the definition of `recsz`, the sizes of the record storage. |
| 2075 | `    size_t windows, bins, counts, trace, bytes;` | `windows`, `bins`, `counts`, `trace`: the numbers of window records, bins, counter readings and trace events that the plan needs. `bytes`: the size of the record block in bytes. `plan_trial` computes all five (lines 2865 to 2873). |
| 2076 | `} recsz;` | Ends the definition of `recsz`. |

### Trial mode: the trace helpers `tev_add`, `tclock` and `tcpu` (lines 2078 to 2107)

| Line | Source | Explanation |
|---:|---|---|
| 2078 | `/* --trace. An event that is not a clock read carries the time of the latest` | Comment: the option `--trace`. An event that is not a clock read carries the time of the latest clock read. The reason follows in line 2079. |
| 2079 | ` * clock read: the trace adds no clock read of its own. */` | Comment: the trace adds no clock read of its own. |
| 2080 | `static inline void tev_add(struct tw *w, int ev, int phase, int widx)` | Starts the function `tev_add`. It appends one event to the trace: the kind `ev`, the phase and the window number. Without `--trace` it does nothing. |
| 2081 | `{` | Opens the body of `tev_add`. |
| 2082 | `    if (!w->log)` | Tests whether there is no log. That is the case without `--trace`. |
| 2083 | `        return;` | Without a log the function returns immediately. |
| 2084 | `    if (w->nlog == TRACE_CAP) {` | Tests whether the log is full: it holds `TRACE_CAP` (1048576) events. |
| 2085 | `        w->ndrop++;` | A full log does not keep the event. It only counts it in `ndrop`. |
| 2086 | `        return;` | The function then returns and stores nothing. |
| 2087 | `    }` | Ends the `if` of line 2084. |
| 2088 | `    w->log[w->nlog++] = (struct tev){ .t = w->last_t, .widx = widx, .ev = (uint8_t)ev, .phase = (uint8_t)phase };` | Appends the event to the log. Its time is `last_t`, the time of the latest clock read. |
| 2089 | `}` | Ends the function `tev_add`. |
| 2091 | `static inline int64_t tclock(struct tw *w)` | Starts the function `tclock`. It reads the clock for the trial mode and returns the time in ns. Every clock read of a timed sequence goes through it (line 2161, line 2168). |
| 2092 | `{` | Opens the body of `tclock`. |
| 2093 | `    int64_t t = now_ns();` | Reads the clock with `now_ns` (line 358). |
| 2094 | `    if (w->log) {` | Tests whether a log exists (`--trace`). |
| 2095 | `        w->last_t = t;` | Stores the time as the time of the latest clock read. |
| 2096 | `        tev_add(w, EV_CLOCK, 0, 0);` | Logs the clock read as an event. |
| 2097 | `    }` | Ends the `if` of line 2094. |
| 2098 | `    return t;` | Returns the time. |
| 2099 | `}` | Ends the function `tclock`. |
| 2101 | `static uint64_t tcpu(struct tw *w)` | Starts the function `tcpu`. It returns the thread CPU time in ns and logs the reading. |
| 2102 | `{` | Opens the body of `tcpu`. |
| 2103 | `    uint64_t c = cpu_ns();` | Reads the thread CPU time with `cpu_ns` (line 1765). |
| 2104 | `    tev_add(w, EV_CPU_CLOCK, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 2105 | `    return c;` | Returns the CPU time. |
| 2106 | `}` | Ends the function `tcpu`. |

### Trial mode: the functions `tcall` and `tcount` (lines 2108 to 2140)

| Line | Source | Explanation |
|---:|---|---|
| 2108 | `/* Every kernel call of a trial goes through here, and from here through the` | Comment: every kernel call of a trial goes through this function, and from here through the unchanged function `call`. With `--hot-copy` the first part is no longer true: the kernel calls then go through `tcall_hot` (line 2191), and from there through `call`. |
| 2109 | ` * unchanged call(). The trace gets the first call of each window. */` | Comment: the trace gets the first call of each window. |
| 2110 | `static inline void tcall(struct tw *w, const struct win *r, volatile uint64_t *sink)` | Starts the function `tcall`. It runs the kernel of the window `r` once on the first `r->size` bytes of the buffer. |
| 2111 | `{` | Opens the body of `tcall`. |
| 2112 | `    if (w->log && (r->phase != w->cur_phase \|\| r->widx != w->cur_widx)) {` | Tests, only with `--trace`, whether this call belongs to another window than the call before it. |
| 2113 | `        w->cur_phase = r->phase;` | Remembers the phase of the new window. |
| 2114 | `        w->cur_widx = r->widx;` | Remembers the number of the new window. |
| 2115 | `        tev_add(w, EV_KERNEL_FIRST, r->phase, r->widx);` | Logs the first kernel call of the window as an event. |
| 2116 | `    }` | Ends the `if` of line 2112. |
| 2117 | `    call(&kernels[r->k], &w->t, 0, r->size, 0, sink);` | The kernel call. It goes through `call` (line 1647), the function that the interval mode also uses: offset 0, `r->size` bytes, and 0 as the store value. The plan accepts read kernels only (line 2778), and a read kernel does not use the store value. |
| 2118 | `}` | Ends the function `tcall`. |
| 2120 | `/* Group read and thread CPU clock, at a boundary of a target window. Not` | Comment: the function takes a group reading and reads the thread CPU clock, at a boundary of a target window. The sentence about inlining starts here. |
| 2121 | ` * inlined: build8.sh lists the branch targets of timed_sequence(), and this` | Comment: the function is not inlined. The script `build8.sh` lists the branch targets of `timed_sequence`. The sentence goes on in line 2122. |
| 2122 | ` * function must be one name there. */` | Comment: this function must be one name in that list. |
| 2123 | `__attribute__((noinline)) static void tcount(struct tw *w, struct counts *c)` | Starts the function `tcount`. It reads the counter group and then the thread CPU time into `c`. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 2124 | `{` | Opens the body of `tcount`. |
| 2125 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest group reading: 3 header words plus 8 counter values, 8 bytes each. |
| 2126 | `    if (w->t.group_fd >= 0) {` | Tests whether a counter group is open. |
| 2127 | `        ssize_t want = (ssize_t)((3 + (size_t)w->t.nopen) * sizeof buf[0]);` | `want`: the size in bytes that a complete reading must have: 3 header words plus one word per open counter, 8 bytes each. |
| 2128 | `        if (read(w->t.group_fd, buf, sizeof buf) != want \|\| buf[0] != (uint64_t)w->t.nopen) {` | One `read` on the group leader. The reading is rejected when its size is not `want`, or when its counter number `nr` is not the number of open counters. |
| 2129 | `            w->read_fail++;` | A rejected reading only adds 1 to `read_fail`. In `read_group` a rejected reading ends the process (lines 1778 to 1781). |
| 2130 | `        } else {` | The case of a good reading. |
| 2131 | `            c->enabled = buf[1];` | Stores the enabled time of the group, in ns. |
| 2132 | `            c->running = buf[2];` | Stores the running time of the group, in ns. |
| 2133 | `            for (int i = 0; i < w->t.nopen; i++)` | Loop over the open counters. |
| 2134 | `                c->val[i] = buf[3 + i];` | Stores one value per open counter. |
| 2135 | `        }` | Ends the `else` of line 2130. |
| 2136 | `        tev_add(w, EV_COUNT_READ, 0, 0);` | Logs the group reading as an event. Without `--trace` this call does nothing. |
| 2137 | `    }` | Ends the `if` of line 2126. |
| 2138 | `    c->cpu_ns = tcpu(w);` | Reads the thread CPU time through `tcpu` (line 2101) and stores it. This line runs also when no group is open. |
| 2139 | `}` | Ends the function `tcount`. |

### Function `timed_sequence` (trial mode): the timed windows of one trial (lines 2141 to 2187)

| Line | Source | Explanation |
|---:|---|---|
| 2141 | `/*` | Comment: starts the comment of the function `timed_sequence`. The comment ends in line 2150. |
| 2142 | ` * The timed sequence of one trial. Each window runs whole passes over` | Comment: the function is the timed sequence of one trial. Each window runs whole passes over its range. The sentence goes on in line 2143. |
| 2143 | ` * [0, size) and reads the clock after every "passes" passes. It ends at the` | Comment: the range is the first `size` bytes of the buffer. The window reads the clock after every `passes` passes. The sentence about the end of a window starts here. |
| 2144 | ` * first clock read at or after its duration. At a boundary the clock is read` | Comment: a window ends at the first clock read at or after its duration. The sentence about a boundary between two windows starts here. |
| 2145 | ` * for the end of the window and again for the start of the next one, so the` | Comment: at a boundary the clock is read once for the end of the window and once more for the start of the next window. The sentence goes on in line 2146. |
| 2146 | ` * gap is measured. No output, allocation, page read, sleep or warm-up pass` | Comment: so the gap between two windows is measured. The function holds no output, no allocation, no reading of the page state, no sleep and no warm-up pass. This sentence ends in line 2147. |
| 2147 | ` * is in here. Not inlined: build8.sh and test_runner8.py read the branch` | Comment: the function is not inlined. The script `build8.sh` and the test `test_runner8.py` read the branch targets of this function from the machine code. The sentence goes on in line 2148. |
| 2148 | ` * targets of this function from the machine code. Only clock_gettime, the` | Comment: only three branch targets are allowed in this function. The first is the library function `clock_gettime`, which reads the clock. The list goes on in line 2149. |
| 2149 | ` * kernel call of call() and tcount() are allowed there.` | Comment: the other two allowed targets are the kernel call of `call` and the function `tcount`. |
| 2150 | ` */` | Comment: the end of the comment. |
| 2151 | `__attribute__((noinline)) static void timed_sequence(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)` | Starts the function `timed_sequence`. It runs all windows of the trial record `r`, one after another. For each window it stores the byte count and two clock times. `count_read` is 1 for a trial with the counter state `read`. `sink` receives the sum of an old read kernel. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 2152 | `{` | Opens the body of `timed_sequence`. |
| 2153 | `    for (int i = 0; i < r->nw; i++) {` | Loop over the windows of the trial, in the order in which they run. |
| 2154 | `        struct win *x = &r->win[i];` | `x`: the record of this window. |
| 2155 | `        uint64_t bytes = 0;` | `bytes`: the byte count of the window. It starts at 0. |
| 2156 | `        int64_t t0, t1, next_bin;` | Clock values in ns: `t0` (the start of the window), `t1` (the latest clock read) and `next_bin` (the requested end of the bin that is open). |
| 2157 | `        int nbin = 0;` | `nbin`: the number of bins that this window has closed. |
| 2159 | `        if (count_read && x->phase == PH_TARGET)` | Tests whether the trial reads counters and this window is a target window. |
| 2160 | `            tcount(w, &r->cnt[x->widx]);` | Counter reading before a target window: `tcount` (line 2123) reads the counter group and the thread CPU time into the reading with the number `widx`. It runs before the start clock read of line 2161. So it lies outside the window. |
| 2161 | `        t0 = tclock(w);` | Start of the window: the clock read `t0` (`tclock`, line 2091). |
| 2162 | `        next_bin = t0 + BIN_NS;` | The first bin has its requested end 10 ms (`BIN_NS`) after `t0`. |
| 2163 | `        do {` | Starts the timed loop of the window. Its body runs at least once. |
| 2164 | `            for (uint64_t c = 0; c < x->passes; c++) {` | Runs `passes` kernel calls without a clock read between them. |
| 2165 | `                tcall(w, x, sink);` | Timed kernel call: one pass of the kernel of the window over the first `size` bytes of the buffer (`tcall`, line 2110). |
| 2166 | `                bytes += x->size;` | Bytes counted: each call adds `size`, the size of the range that was passed to the kernel. Nothing is counted inside a kernel. |
| 2167 | `            }` | Ends the `for` of line 2164. |
| 2168 | `            t1 = tclock(w);` | Clock read after the passes: `t1`. The clock is never read inside a pass. |
| 2169 | `            /* A bin closes on this clock read if its requested end has` | Comment: a bin closes at this clock read when its requested end has passed. The sentence about the last bin starts here. |
| 2170 | `             * passed. The last clock read of the window closes the last bin. */` | Comment: the last clock read of the window closes the last bin. |
| 2171 | `            if (x->bin && (t1 >= next_bin \|\| t1 - t0 >= x->dur_ns) && nbin < x->bin_cap) {` | Tests three things. The window records bins. A bin can close now: its requested end has passed, or the window is over. The storage has room for one more bin. |
| 2172 | `                x->bin[nbin].t_end = t1;` | Stores the clock time `t1` as the end of the bin. |
| 2173 | `                x->bin[nbin].bytes = bytes;` | Stores the bytes that the window has counted up to this clock read. |
| 2174 | `                nbin++;` | Counts the bin. |
| 2175 | `                while (next_bin <= t1)` | Moves the requested end of the next bin forward in steps of 10 ms until it lies after `t1`. |
| 2176 | `                    next_bin += BIN_NS;` | The body of the loop of line 2175: one step of 10 ms. |
| 2177 | `            }` | Ends the `if` of line 2171. |
| 2178 | `        } while (t1 - t0 < x->dur_ns);` | Stop rule of a window. The loop repeats while less than `dur_ns` has passed after `t0`. So a window ends at its first clock read at or after its requested duration, and only at the end of a whole pass. |
| 2179 | `        x->bytes = bytes;` | Stores the byte count in the window record. The W row prints it (line 2485). This function computes no rate. |
| 2180 | `        x->t_start = t0;` | Stores `t0` as the start time of the window. |
| 2181 | `        x->t_end = t1;` | Stores the last `t1` as the end time of the window. The next window reads the clock again for its own start (line 2161). So the time between two windows is measured and belongs to no window. |
| 2182 | `        x->nbin = nbin;` | Stores the number of bins that the window closed. |
| 2183 | `    }` | Ends the loop over the windows (line 2153). |
| 2184 | `    if (count_read)` | Tests whether the trial reads counters. |
| 2185 | `        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);` | Last counter reading, after the last window. It goes into the reading with the number of the last target window plus 1. So a trial with `nwin` target windows has `nwin + 1` readings. |
| 2186 | `}` | Ends the function `timed_sequence`. |

### Function `tcall_hot` (trial mode): `tcall` with value arguments (lines 2188 to 2200)

| Line | Source | Explanation |
|---:|---|---|
| 2188 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. This block ends in line 2251. |
| 2189 | `/* tcall() for timed_sequence_hot(): the kernel index, the phase, the window` | Comment: this function is the `tcall` of `timed_sequence_hot`. The kernel index, the phase and the window number come as values. The list goes on in line 2190. |
| 2190 | ` * index and the size come by value, so no field of win[i] is read here. */` | Comment: the size also comes as a value. So the function reads no field of the window record. |
| 2191 | `static inline void tcall_hot(struct tw *w, int k, int phase, int widx, uint64_t size, volatile uint64_t *sink)` | Starts the function `tcall_hot`. It does the same as `tcall` (line 2110), but the kernel index `k`, the phase, the window number and the size arrive as arguments. So it reads no field of the window record. |
| 2192 | `{` | Opens the body of `tcall_hot`. |
| 2193 | `    if (w->log && (phase != w->cur_phase \|\| widx != w->cur_widx)) {` | Tests, only with `--trace`, whether this call belongs to another window than the call before it. |
| 2194 | `        w->cur_phase = phase;` | Remembers the phase of the new window. |
| 2195 | `        w->cur_widx = widx;` | Remembers the number of the new window. |
| 2196 | `        tev_add(w, EV_KERNEL_FIRST, phase, widx);` | Logs the first kernel call of the window as an event. |
| 2197 | `    }` | Ends the `if` of line 2193. |
| 2198 | `    call(&kernels[k], &w->t, 0, size, 0, sink);` | The kernel call. It goes through `call` (line 1647): offset 0, `size` bytes, and 0 as the store value. |
| 2199 | `}` | Ends the function `tcall_hot`. |

### Function `timed_sequence_hot` (trial mode): the variant for `--hot-copy` (lines 2201 to 2251)

| Line | Source | Explanation |
|---:|---|---|
| 2201 | `/*` | Comment: starts the comment of the function `timed_sequence_hot`. The comment ends in line 2211. |
| 2202 | ` * --hot-copy: timed_sequence() with one difference. Before the start clock` | Comment: with the option `--hot-copy` this function runs the windows. It is `timed_sequence` with one difference. The sentence about the difference starts here. |
| 2203 | ` * read of a window it copies the fields of win[i] that the window loop needs` | Comment: before the start clock read of a window the function copies the fields of the window record that the window loop needs. The sentence goes on in line 2204. |
| 2204 | ` * into local variables. After the end clock read it stores bytes, t_start,` | Comment: the copies are local variables. After the end clock read the function stores the byte count and the start time. The list goes on in line 2205. |
| 2205 | ` * t_end and nbin. Between the first pass and the last pass of a window it` | Comment: it also stores the end time and the number of bins. The sentence about the time between the first and the last pass starts here. |
| 2206 | ` * does not read or write win[i]. The compiler cannot read a field again` | Comment: between the first pass and the last pass of a window the function does not read or write the window record. The sentence about the compiler starts here. |
| 2207 | ` * inside the loop in place of the local copy: the loop calls a kernel` | Comment: the compiler cannot read a field again inside the loop in place of the local copy. The reason starts here: the loop calls a kernel. |
| 2208 | ` * through a pointer, and such a call may change any memory. The self-test` | Comment: the kernel is called through a pointer, and such a call may change any memory. The sentence about the self-test starts here. |
| 2209 | ` * checks it on the machine code (test_hot_touch). The same rules as for` | Comment: the self-test checks this on the machine code, in its function `test_hot_touch`. The last sentence of the comment starts here. |
| 2210 | ` * timed_sequence() hold for the calls made here.` | Comment: the calls that this function makes follow the same rules as the calls of `timed_sequence` (lines 2147 to 2149). |
| 2211 | ` */` | Comment: the end of the comment. |
| 2212 | `__attribute__((noinline)) static void timed_sequence_hot(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)` | Starts the function `timed_sequence_hot`. It runs the windows of one trial as `timed_sequence` does (line 2151), with the same arguments. The difference: the window loop works on local copies of the fields of the window record. |
| 2213 | `{` | Opens the body of `timed_sequence_hot`. |
| 2214 | `    for (int i = 0; i < r->nw; i++) {` | Loop over the windows of the trial, in the order in which they run. |
| 2215 | `        struct win *x = &r->win[i];` | `x`: the record of this window. |
| 2216 | `        const int k = x->k, phase = x->phase, widx = x->widx, bin_cap = x->bin_cap;` | Local copies of four fields of the window record: the kernel index, the phase, the window number and the room for bins. |
| 2217 | `        const uint64_t size = x->size, passes = x->passes;` | Local copies of the range size and of the number of passes between two clock reads. |
| 2218 | `        const int64_t dur_ns = x->dur_ns;` | Local copy of the requested duration. |
| 2219 | `        struct bin *const bin = x->bin;` | Local copy of the pointer to the bin storage. |
| 2220 | `        uint64_t bytes = 0;` | `bytes`: the byte count of the window. It starts at 0. |
| 2221 | `        int64_t t0, t1, next_bin;` | Clock values in ns: `t0`, `t1` and `next_bin`, as in line 2156. |
| 2222 | `        int nbin = 0;` | `nbin`: the number of bins that this window has closed. |
| 2224 | `        if (count_read && phase == PH_TARGET)` | Tests whether the trial reads counters and this window is a target window. |
| 2225 | `            tcount(w, &r->cnt[widx]);` | Counter reading before a target window, as in line 2160. It lies outside the window. |
| 2226 | `        t0 = tclock(w);` | Start of the window: the clock read `t0`. |
| 2227 | `        next_bin = t0 + BIN_NS;` | The first bin has its requested end 10 ms (`BIN_NS`) after `t0`. |
| 2228 | `        do {` | Starts the timed loop of the window. Its body runs at least once. |
| 2229 | `            for (uint64_t c = 0; c < passes; c++) {` | Runs `passes` kernel calls without a clock read between them. |
| 2230 | `                tcall_hot(w, k, phase, widx, size, sink);` | Timed kernel call through `tcall_hot` (line 2191): one pass of the kernel over the first `size` bytes of the buffer. |
| 2231 | `                bytes += size;` | Bytes counted: each call adds `size`, the size of the range that was passed to the kernel. |
| 2232 | `            }` | Ends the `for` of line 2229. |
| 2233 | `            t1 = tclock(w);` | Clock read after the passes: `t1`. |
| 2234 | `            if (bin && (t1 >= next_bin \|\| t1 - t0 >= dur_ns) && nbin < bin_cap) {` | The bin test of line 2171, with the local copies: the window records bins, a bin can close now, and the storage has room. |
| 2235 | `                bin[nbin].t_end = t1;` | Stores `t1` as the end of the bin. The bin storage is not a part of the window record. |
| 2236 | `                bin[nbin].bytes = bytes;` | Stores the bytes that the window has counted up to this clock read. |
| 2237 | `                nbin++;` | Counts the bin. |
| 2238 | `                while (next_bin <= t1)` | Moves the requested end of the next bin forward in steps of 10 ms until it lies after `t1`. |
| 2239 | `                    next_bin += BIN_NS;` | The body of the loop of line 2238: one step of 10 ms. |
| 2240 | `            }` | Ends the `if` of line 2234. |
| 2241 | `        } while (t1 - t0 < dur_ns);` | Stop rule of a window, as in line 2178: the window ends at its first clock read at or after its requested duration. |
| 2242 | `        x->bytes = bytes;` | After the end clock read: stores the byte count in the window record. |
| 2243 | `        x->t_start = t0;` | Stores `t0` as the start time of the window. |
| 2244 | `        x->t_end = t1;` | Stores the last `t1` as the end time of the window. |
| 2245 | `        x->nbin = nbin;` | Stores the number of bins that the window closed. |
| 2246 | `    }` | Ends the loop over the windows (line 2214). |
| 2247 | `    if (count_read)` | Tests whether the trial reads counters. |
| 2248 | `        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);` | Last counter reading, after the last window, as in line 2185. |
| 2249 | `}` | Ends the function `timed_sequence_hot`. |
| 2251 | `/* bwx10- */` | Comment: marks the end of the block that `bwx10` added. The block starts in line 2188. The code from here to line 3042 also belongs to the trial mode. |

### Function `count_close` (trial mode): close the counter group (lines 2252 to 2264)

| Line | Source | Explanation |
|---:|---|---|
| 2252 | `static void count_close(struct tw *w)` | Starts the function `count_close`. It closes every counter of the worker and sets the group state of the worker back to closed. |
| 2253 | `{` | Opens the body of `count_close`. |
| 2254 | `    for (int i = 0; i < w->nfd; i++)` | Loop over the counter file descriptors that `count_open` stored in `w->fd` (line 2292). |
| 2255 | `        if (close(w->fd[i]) != 0)` | Closes one counter and tests whether the `close` call failed. |
| 2256 | `            w->close_fail++;` | A failed `close` adds 1 to `w->close_fail`. |
| 2257 | `    w->nfd = 0;` | No file descriptor is stored any more. |
| 2258 | `    w->t.group_fd = -1;` | The group has no leader. |
| 2259 | `    w->t.nopen = 0;` | No event is open. |
| 2260 | `    w->group_open = 0;` | The group counts as closed. |
| 2261 | `    w->open_fail = 0;` | The count of events that did not open is 0 again. |
| 2262 | `    tev_add(w, EV_COUNT_CLOSE, 0, 0);` | Logs the closing as an event. Without `--trace` this call does nothing. |
| 2263 | `}` | Ends the function `count_close`. |

### Function `count_open` (trial mode): open the counter group (lines 2265 to 2299)

| Line | Source | Explanation |
|---:|---|---|
| 2265 | `/* One group, user mode only, opened by the pinned worker for itself. The` | Comment: the worker has one counter group, which counts in user mode only. The pinned worker opens it for itself. The next sentence starts here. |
| 2266 | ` * events count from the open on. An event that does not open is counted in` | Comment: the events count from the moment of the open. The sentence about an event that does not open starts here. |
| 2267 | ` * open_fail and is printed as NA. */` | Comment: an event that does not open is counted in `open_fail` and is printed as `NA`. |
| 2268 | `static void count_open(struct tw *w)` | Starts the function `count_open`. It is the version of `open_counters` (line 1738) for the trial mode: it opens one counter per event of `cfg` and joins the counters into one group. Two things differ. It keeps every file descriptor in `w->fd`: `count_close` needs them to close the group. And it writes no message to stderr. |
| 2269 | `{` | Opens the body of `count_open`. |
| 2270 | `    w->t.group_fd = -1;` | Start state: no group leader. |
| 2271 | `    w->t.nopen = 0;` | Start state: 0 open events. |
| 2272 | `    w->nfd = 0;` | Start state: no stored file descriptor. |
| 2273 | `    w->open_fail = 0;` | Start state: 0 events that did not open. |
| 2274 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `cfg`, in the order of the option `--events`. |
| 2275 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 2276 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. The field `disabled` stays 0, so a counter counts from the moment it is opened. |
| 2277 | `        a.type = (uint32_t)cfg.pmu_type;` | `type`: the PMU type (`--pmu-type`). |
| 2278 | `        a.size = sizeof a;` | `size`: the size of the structure. |
| 2279 | `        a.config = cfg.ev_code[e];` | `config`: the event code of this event. |
| 2280 | `        a.exclude_kernel = 1;` | The counter does not count code of the Linux kernel. |
| 2281 | `        a.exclude_hv = 1;` | The counter does not count code of a hypervisor. With line 2280 it counts in user mode only. |
| 2282 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | One `read` of the group returns the values of all its counters, the enabled time and the running time, as in line 1750. |
| 2283 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, w->t.group_fd, 0);` | The system call `perf_event_open` opens the counter for the calling thread, on any CPU that it runs on, as in line 1751. The first counter starts a new group. A later counter joins the group of the leader. |
| 2284 | `        if (fd < 0) {` | Tests whether the open failed. |
| 2285 | `            if (w->open_fail++ == 0)` | Counts the event as not opened. The test is true only for the first such event of this opening. |
| 2286 | `                snprintf(w->open_err, sizeof w->open_err, "%s type %ld code 0x%llx: %s", cfg.ev_name[e], cfg.pmu_type,` | For the first such event: stores an error text in `w->open_err`: the event name, the PMU type, the event code and the error text of Linux. `emit_trial` prints it in an X row (line 2520). |
| 2287 | `                         (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 2286: the event code and the error text (`strerror(errno)`). |
| 2288 | `            w->t.ev_pos[e] = -1;` | The event gets the position -1. Its field in the C rows is `NA` (lines 2506 to 2507). |
| 2289 | `            continue;` | The loop goes on with the next event. |
| 2290 | `        }` | Ends the `if` of line 2284. |
| 2291 | `        w->t.ev_pos[e] = w->t.nopen++;` | The open succeeded. The event gets its position in a group reading, and `nopen` counts it. |
| 2292 | `        w->fd[w->nfd++] = fd;` | Keeps the file descriptor for `count_close` (line 2255). |
| 2293 | `        if (w->t.group_fd < 0)` | Tests whether the group has no leader yet. |
| 2294 | `            w->t.group_fd = fd;` | The first counter that opens becomes the leader of the group. |
| 2295 | `    }` | Ends the loop over the events (line 2274). |
| 2296 | `    w->group_open = 1;` | The group counts as open from here on. This is also the case when no event opened. |
| 2297 | `    tev_add(w, EV_COUNT_OPEN, 0, 0);` | Logs the opening as an event. Without `--trace` this call does nothing. |
| 2298 | `}` | Ends the function `count_open`. |

### Functions `page_read`, `switches` and `first_multiplexed` (trial mode) (lines 2300 to 2328)

| Line | Source | Explanation |
|---:|---|---|
| 2300 | `static void page_read(struct tw *w, struct trec *r, int at)` | Starts the function `page_read`. It reads the page state of the one buffer of the worker and the four counters of `/proc/vmstat` into the trial record `r`. `at` is 0 before the timed sequence and 1 after it. |
| 2301 | `{` | Opens the body of `page_read`. The `# page_read` lines of the interval mode do not come from this function. `main` prints them in line 3281. |
| 2302 | `    uint64_t *buf[1] = { w->t.a };` | `buf`: the address of the one buffer of the worker. |
| 2303 | `    read_smaps(&r->pg[at], buf, 1);` | `read_smaps` (line 1671) reads the size of the buffer and its part on 2 MiB pages into `r->pg[at]`. |
| 2304 | `    read_vmstat(r->vm[at]);` | `read_vmstat` (line 1701) reads the four counters of `/proc/vmstat` into `r->vm[at]`. |
| 2305 | `    tev_add(w, EV_PAGE_READ, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 2306 | `}` | Ends the function `page_read`. |
| 2308 | `/* Context-switch counts of the calling thread. -1: not readable. */` | Comment: the function reads the context-switch counts of the calling thread. A value of -1 means that a count could not be read. The function also stores the count of minor page faults (line 2315), which the comment does not name. |
| 2309 | `static void switches(struct tw *w, struct trec *r, int at)` | Starts the function `switches`. It stores three counts of the calling thread in the trial record `r`: the voluntary context switches, the involuntary context switches and the minor page faults. `at` is 0 before the timed sequence and 1 after it. |
| 2310 | `{` | Opens the body of `switches`. |
| 2311 | `    struct rusage ru;` | `ru`: the structure that `getrusage` fills. |
| 2312 | `    int ok = getrusage(RUSAGE_THREAD, &ru) == 0;` | `getrusage` with `RUSAGE_THREAD` asks Linux for the resource use of the calling thread. `ok` is 1 when the call succeeded. |
| 2313 | `    r->nvcsw[at] = ok ? ru.ru_nvcsw : -1;` | Stores `ru_nvcsw`, the number of voluntary context switches: the thread stopped running by its own request, usually to wait for something. A failed call stores -1. |
| 2314 | `    r->nivcsw[at] = ok ? ru.ru_nivcsw : -1;` | Stores `ru_nivcsw`, the number of involuntary context switches: Linux took the CPU away from the thread. A failed call stores -1. |
| 2315 | `    r->minflt[at] = ok ? ru.ru_minflt : -1;` | Stores `ru_minflt`, the number of minor page faults. These are page faults that need no disk access. The first touch of a page is one. A failed call stores -1. |
| 2316 | `    tev_add(w, EV_RUSAGE, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 2317 | `}` | Ends the function `switches`. |
| 2319 | `/* The index of the first target window whose counters ran for less time` | Comment: the function returns the index of the first target window whose counters ran for less time than they were enabled. The sentence ends in line 2320. |
| 2320 | ` * than they were enabled, or -1. cnt holds nwin + 1 readings. */` | Comment: it returns -1 when there is no such window. `cnt` holds `nwin + 1` readings. |
| 2321 | `static int first_multiplexed(const struct counts *cnt, int nwin)` | Starts the function `first_multiplexed`. `cnt` holds one counter reading per boundary of the `nwin` target windows. The function looks for a target window in which the counters did not count all the time. |
| 2322 | `{` | Opens the body of `first_multiplexed`. |
| 2323 | `    for (int i = 0; i < nwin; i++)` | Loop over the target windows. |
| 2324 | `        if (cnt[i + 1].running - cnt[i].running < cnt[i + 1].enabled - cnt[i].enabled)` | Compares, for one target window, the growth of the running time with the growth of the enabled time between its two readings. A smaller growth of the running time means that the counters did not count all the time in this window. |
| 2325 | `            return i;` | Returns the index of the first such window. |
| 2326 | `    return -1;` | Returns -1 when there is no such window. |
| 2327 | `}` | Ends the function `first_multiplexed`. |

### Function `run_trial` (trial mode): one trial, without output (lines 2329 to 2372)

| Line | Source | Explanation |
|---:|---|---|
| 2329 | `/* One trial: the work before the timed sequence, the timed sequence, the` | Comment: the function runs one trial: the work before the timed sequence, then the timed sequence. The list ends in line 2330. |
| 2330 | ` * work after it. Prints nothing. */` | Comment: then comes the work after the timed sequence. The function prints nothing. |
| 2331 | `static void run_trial(struct tw *w, const struct trial *p, struct trec *r, volatile uint64_t *sink)` | Starts the function `run_trial`. `p` is the trial of the plan. `r` is the record of the trial. `sink` receives the sum of an old read kernel. |
| 2332 | `{` | Opens the body of `run_trial`. |
| 2333 | `    uint64_t expect = 0;` | `expect`: the sum that the last old read kernel of the trial must return. |
| 2334 | `    int old = -1;` | `old`: the index of the last window with an old read kernel, or -1 when the trial has none. |
| 2336 | `    if (p->count == CS_CLOSED && w->group_open)` | Tests whether the plan wants the counters closed for this trial while the group is open. |
| 2337 | `        count_close(w);` | Then the group is closed (`count_close`, line 2252). |
| 2338 | `    else if (p->count != CS_CLOSED && !w->group_open)` | Tests whether the plan wants counters for this trial (state `open` or `read`) while the group is not open. |
| 2339 | `        count_open(w);` | Then the group is opened (`count_open`, line 2268). It stays open over the next trials until a trial wants it closed. |
| 2340 | `    r->state = p->count != CS_CLOSED && w->open_fail ? CS_FAIL : p->count;` | The record keeps the counter state of the trial. It is `fail` when the trial wants counters and an event did not open. In every other case it is the state of the plan. |
| 2341 | `    r->close_fail = w->close_fail;` | Moves the number of failed `close` calls of line 2337 into the record. |
| 2342 | `    w->close_fail = 0;` | Sets the count of failed `close` calls of the worker to 0. |
| 2343 | `    w->read_fail = 0;` | Sets the count of failed group readings of the worker to 0. |
| 2345 | `    /* The last old read of the trial must leave the sum of its range in the` | Comment: the last old read kernel of the trial must leave the sum of its range in the sink. The sentence ends in line 2346. |
| 2346 | `     * sink. The sink starts with another value, so an old value cannot pass. */` | Comment: the sink starts with another value. So a value from an earlier call cannot pass the check. |
| 2347 | `    for (int i = 0; i < r->nw; i++)` | Loop over the windows of the trial. |
| 2348 | `        if (kernels[r->win[i].k].type == T_OLDREAD)` | Tests whether the kernel of the window has the type `T_OLDREAD`. |
| 2349 | `            old = i;` | `old` keeps the index of the last such window. |
| 2350 | `    if (old >= 0) {` | Tests whether the trial has such a window. |
| 2351 | `        expect = w->v * (r->win[old].size / 8);` | The expected sum. Every 8-byte word of the `--bytes` range of the buffer holds `w->v` (line 2622), and the range of a window lies inside it (line 2780). So the kernel must return `w->v` times the number of words of its range. Only the low 64 bits of the product are kept, as in the sum of the kernel. |
| 2352 | `        *sink = expect + 1;` | The sink starts with the expected sum plus 1. |
| 2353 | `    }` | Ends the `if` of line 2350. |
| 2355 | `    page_read(w, r, 0);` | Before the timed sequence: reads the page state (`page_read`, line 2300). |
| 2356 | `    switches(w, r, 0);` | Before the timed sequence: reads the context switches and the minor page faults (`switches`, line 2309). |
| 2357 | `    r->cpu[0] = tcpu(w);` | Before the timed sequence: reads the thread CPU time (`tcpu`, line 2101). This is the last step before the timed sequence. |
| 2358 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2359 | `    /* --hot-copy selects the other function. The statement after this block` | Comment: the option `--hot-copy` selects the other function. The sentence about the next statement starts here. |
| 2360 | `     * is the else branch. */` | Comment: the statement after this block (line 2365) is the `else` branch. |
| 2361 | `    if (plan.hot_copy)` | Tests for the option `--hot-copy`. |
| 2362 | `        timed_sequence_hot(w, r, p->count == CS_READ, sink);` | With `--hot-copy`: `timed_sequence_hot` (line 2212) runs the timed sequence. The third argument is 1 for the counter state `read`. Then the function also reads the counter group at the boundaries of the target windows. |
| 2363 | `    else` | Starts the `else` branch. Its statement is line 2365. |
| 2364 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2365 | `    timed_sequence(w, r, p->count == CS_READ, sink);` | `timed_sequence` (line 2151) runs the timed sequence. The clock reads that time the windows are inside that function. The third argument is 1 for the counter state `read`. Then the function also reads the counter group at the boundaries of the target windows. This statement is the `else` branch of line 2361: it runs without `--hot-copy`. |
| 2366 | `    r->cpu[1] = tcpu(w);` | After the timed sequence: reads the thread CPU time again. |
| 2367 | `    switches(w, r, 1);` | After the timed sequence: reads the context switches and the minor page faults again. |
| 2368 | `    page_read(w, r, 1);` | After the timed sequence: reads the page state again. So the three readings come in the reverse order of lines 2355 to 2357. |
| 2369 | `    r->sink_ok = old < 0 ? -1 : *sink == expect;` | `sink_ok`: -1 when the trial ran no old read kernel. For a trial that ran one: 1 when the sink holds the expected sum, 0 when it does not. |
| 2370 | `    r->read_fail = w->read_fail;` | Moves the number of failed group readings of the timed sequence into the record. |
| 2371 | `}` | Ends the function `run_trial`. |

### Functions `trial_windows`, `window_bins` and `set_windows` (trial mode) (lines 2373 to 2413)

| Line | Source | Explanation |
|---:|---|---|
| 2373 | `static int trial_windows(const struct trial *p)` | Starts the function `trial_windows`. It returns the number of windows of one trial. |
| 2374 | `{` | Opens the body of `trial_windows`. |
| 2375 | `    return (p->prev.k >= 0) + 4 * (p->pfx.k >= 0) + (p->pred.k >= 0) + p->nwin;` | Adds the windows of the phases that the trial has: 1 for the previous activity, 4 for the prefix, 1 for the predecessor and `nwin` for the target. The plan may leave out each of the first three. Then the field `k` of that part is -1, and the phase adds 0. |
| 2376 | `}` | Ends the function `trial_windows`. |
| 2378 | `/* Bins that one target window can close: one per 10 ms that ends inside the` | Comment: the number of bins that one target window can close: one per 10 ms that ends inside the window. The list goes on in line 2379. |
| 2379 | ` * window, one at the end of the window, and one spare. */` | Comment: plus one bin at the end of the window, and one extra bin. |
| 2380 | `static int window_bins(const struct trial *p)` | Starts the function `window_bins`. It returns the number of bins for which one target window of the trial gets storage. |
| 2381 | `{` | Opens the body of `window_bins`. |
| 2382 | `    return p->bins ? (int)(p->win_ms / 10) + 2 : 0;` | For a trial with bins: the window duration `win_ms` divided by 10 and rounded down, plus 2. The 10 is the requested length of a bin in ms (`BIN_NS`, line 1969). For a trial without bins: 0. |
| 2383 | `}` | Ends the function `window_bins`. |
| 2385 | `/* Fills the plan part of the windows of one trial. bin: storage for` | Comment: the function fills the plan part of the windows of one trial. The sentence about `bin` starts here. |
| 2386 | ` * nwin * window_bins(p) bins. */` | Comment: `bin` is the storage for `nwin` times `window_bins(p)` bins. |
| 2387 | `static void set_windows(const struct trial *p, struct win *win, struct bin *bin)` | Starts the function `set_windows`. It fills the plan fields of all window records of the trial `p`, in the order in which the windows run. `win` points to the first window record of the trial. |
| 2388 | `{` | Opens the body of `set_windows`. |
| 2389 | `    const struct {` | Starts the definition of the table `ph`, with one entry per phase. |
| 2390 | `        const struct part *part;` | `part`: the part of the trial that the phase runs. |
| 2391 | `        int phase, n;` | `phase`: the code of the phase. `n`: the number of windows of the phase. |
| 2392 | `    } ph[4] = { { &p->prev, PH_PREV, 1 }, { &p->pfx, PH_PREFIX, 4 }, { &p->pred, PH_PRED, 1 }, { &p->tgt, PH_TARGET, p->nwin } };` | The four entries, in the order of the run: previous activity (1 window), prefix (4 windows), predecessor (1 window) and target (`nwin` windows). |
| 2393 | `    struct win *x = win;` | `x`: the window record that is filled next. |
| 2394 | `    for (int i = 0; i < 4; i++) {` | Loop over the four phases. |
| 2395 | `        const struct part *part = ph[i].part;` | `part`: the part of this phase. |
| 2396 | `        if (part->k < 0)` | Tests whether the plan leaves this phase out. |
| 2397 | `            continue;` | Such a phase gets no window. |
| 2398 | `        for (int j = 0; j < ph[i].n; j++, x++) {` | Loop over the windows of the phase. After each window `x` moves on to the next record. |
| 2399 | `            memset(x, 0, sizeof *x);` | Sets every field of the record to 0. |
| 2400 | `            x->k = part->k;` | The kernel of the window. |
| 2401 | `            x->phase = ph[i].phase;` | The phase of the window. |
| 2402 | `            x->widx = j;` | The number of the window inside its phase, counted from 0. |
| 2403 | `            x->size = part->size;` | The size of the range of the window, in bytes. |
| 2404 | `            x->passes = CHECK_BYTES / part->size ? CHECK_BYTES / part->size : 1;` | `passes`: the number of kernel calls between two clock reads. It is 8 MiB (`CHECK_BYTES`, line 161) divided by the range size, rounded down, and at least 1. |
| 2405 | `            x->dur_ns = (ph[i].phase == PH_TARGET ? p->win_ms : part->ms / ph[i].n) * 1000000L;` | `dur_ns`: the requested duration of the window in ns. A target window gets `win_ms`. Every other window gets the duration of its phase divided by the number of windows of the phase. So each of the 4 prefix windows gets a quarter of the prefix duration. |
| 2406 | `            if (ph[i].phase == PH_TARGET && p->bins) {` | Tests whether this is a target window of a trial with bins. |
| 2407 | `                x->bin_cap = window_bins(p);` | `bin_cap`: the number of bins that the window can close (`window_bins`, line 2380). |
| 2408 | `                x->bin = bin + (size_t)j * (size_t)x->bin_cap;` | The window gets its own part of the bin storage: target window `j` starts at bin `j * bin_cap`. |
| 2409 | `            }` | Ends the `if` of line 2406. |
| 2410 | `        }` | Ends the loop over the windows of the phase (line 2398). |
| 2411 | `    }` | Ends the loop over the phases (line 2394). |
| 2412 | `}` | Ends the function `set_windows`. |

### Function `alloc_records` (trial mode): one memory block for all trial records (lines 2414 to 2452)

| Line | Source | Explanation |
|---:|---|---|
| 2414 | `/* The record storage of all trials: one block, sized from the plan, written` | Comment: the record storage of all trials is one block. Its size comes from the plan. The sentence goes on in line 2415. |
| 2415 | ` * once here so that no page of it is first touched during a trial.` | Comment: the block is written once here. So no page of it gets its first touch during a trial. |
| 2416 | ` * plan_trial() has filled recsz and has checked its bound. */` | Comment: `plan_trial` has filled `recsz` and has checked its upper limit (line 2875). |
| 2417 | `static void alloc_records(struct tw *w)` | Starts the function `alloc_records`. It allocates the record block, touches every page of it, and divides it into the arrays of the records. |
| 2418 | `{` | Opens the body of `alloc_records`. |
| 2419 | `    char *mem = malloc(recsz.bytes);` | Allocates one block of `recsz.bytes` bytes with `malloc`. |
| 2420 | `    if (!mem) {` | Tests whether the allocation failed. |
| 2421 | `        fprintf(stderr, "no memory for %zu bytes of records\n", recsz.bytes);` | Prints `no memory for`, the number of bytes and `bytes of records` to stderr. |
| 2422 | `        exit(2);` | Ends the process with exit status 2. |
| 2423 | `    }` | Ends the `if` of line 2420. |
| 2424 | `    memset(mem, 0, recsz.bytes);` | Fills the block with zero bytes. |
| 2425 | `    /* gcc joins malloc and memset into calloc, and calloc does not write a` | Comment: the compiler gcc joins `malloc` and `memset` into one call of `calloc`. `calloc` does not write a new block. The sentence ends in line 2426. |
| 2426 | `     * fresh block. One volatile store per page is the first touch. */` | Comment: one store per page through a `volatile` pointer is the first touch. |
| 2427 | `    for (size_t at = 0; at < recsz.bytes; at += (size_t)page_bytes)` | Loop over the block in steps of one page (`page_bytes`). |
| 2428 | `        ((volatile char *)mem)[at] = 0;` | Stores one zero byte in each page. The pointer is `volatile`, so the compiler must keep the store. |
| 2429 | `    ((volatile char *)mem)[recsz.bytes - 1] = 0;` | Stores one zero byte in the last byte of the block. |
| 2430 | `    rec = (struct trec *)mem;` | `rec`: the trial records stand at the start of the block, one per trial. |
| 2431 | `    struct win *win = (struct win *)(rec + plan.n);` | `win`: the window records follow the trial records. |
| 2432 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2433 | `    /* --rec-pad: win[] starts this many bytes later. With 0 nothing moves. */` | Comment: with `--rec-pad` the window records start that many bytes later. With 0 nothing moves. |
| 2434 | `    win = (struct win *)((char *)win + plan.rec_pad);` | Moves the start of the window records by `plan.rec_pad` bytes. The default is 0 bytes. |
| 2435 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2436 | `    struct counts *cnt = (struct counts *)(win + recsz.windows);` | `cnt`: the counter readings follow the window records. |
| 2437 | `    struct bin *bin = (struct bin *)(cnt + recsz.counts);` | `bin`: the bins follow the counter readings. |
| 2438 | `    if (plan.trace)` | Tests for the option `--trace`. |
| 2439 | `        w->log = (struct tev *)(bin + recsz.bins);` | With `--trace` the event log follows the bins. |
| 2440 | `    for (int i = 0; i < plan.n; i++) {` | Loop over the trials of the plan. |
| 2441 | `        const struct trial *p = &plan.tr[i];` | `p`: the trial of the plan. |
| 2442 | `        rec[i].win = win;` | The trial gets the next free window records. |
| 2443 | `        rec[i].nw = trial_windows(p);` | `nw`: the number of windows of the trial (`trial_windows`, line 2373). |
| 2444 | `        rec[i].cnt = p->count == CS_READ ? cnt : NULL;` | Only a trial with the counter state `read` gets counter readings. Every other trial gets NULL. |
| 2445 | `        set_windows(p, win, bin);` | Fills the plan fields of the windows of the trial (`set_windows`, line 2387). |
| 2446 | `        win += rec[i].nw;` | Moves `win` past the windows of this trial. |
| 2447 | `        bin += (size_t)p->nwin * (size_t)window_bins(p);` | Moves `bin` past the bins of this trial: `nwin` times `window_bins(p)`. |
| 2448 | `        if (p->count == CS_READ)` | Tests whether the trial has the counter state `read`. |
| 2449 | `            cnt += p->nwin + 1;` | Moves `cnt` past the `nwin + 1` readings of this trial. |
| 2450 | `    }` | Ends the loop over the trials (line 2440). |
| 2451 | `}` | Ends the function `alloc_records`. |

### Functions `print_s` and `print_p8` (trial mode): the S row and the P row (lines 2453 to 2471)

| Line | Source | Explanation |
|---:|---|---|
| 2453 | `static void print_s(int i)` | Starts the function `print_s`. It prints the S row of trial `i`: the plan line of the trial and two fields of the trial before it. |
| 2454 | `{` | Opens the body of `print_s`. |
| 2455 | `    const struct trial *p = &plan.tr[i];` | `p`: trial `i` of the plan. |
| 2456 | `    printf("S");` | Prints the letter `S`. |
| 2457 | `    for (int f = 0; f < PLAN_FIELDS; f++)` | Loop over the 11 fields of the plan line. |
| 2458 | `        printf(",%s", p->f[f]);` | Prints a comma and one field, as the text of the plan file. |
| 2459 | `    printf(",%s,%s\n", i ? plan.tr[i - 1].f[1] : "none", i ? plan.tr[i - 1].f[6] : "none");` | Prints two more fields and the line break: the fields `cond` and `tgt` of the trial before this one. For trial 0 it prints the word `none` two times. |
| 2460 | `}` | Ends the function `print_s`. |
| 2462 | `static void print_p8(int i, const char *when, const struct page *pg, const long long vm[4])` | Starts the function `print_p8`. It prints the P row of the trial mode: the page state of the buffer before or after the timed sequence of trial `i`. `when` is the word `pre` or `post`. |
| 2463 | `{` | Opens the body of `print_p8`. The P rows of the interval mode have other columns: round, position, thread index and buffer letter come first. Those rows come from `print_p` (line 1726). |
| 2464 | `    printf("P,%d,%s", i, when);` | Prints the letter `P`, the trial number and the word `pre` or `post`. |
| 2465 | `    print_na(pg->kb_total);` | Prints the size of the mapping of the buffer in kB, or `NA` (`print_na`, line 1718). |
| 2466 | `    print_na(pg->kb_huge);` | Prints the part of the buffer that lies on 2 MiB pages in kB, or `NA`. |
| 2467 | `    for (int k = 0; k < 4; k++)` | Loop over the four counters of `/proc/vmstat`. |
| 2468 | `        print_na(vm[k]);` | Prints one counter, or `NA` for a counter that was not found. |
| 2469 | `    printf("\n");` | Ends the row with a line break. |
| 2470 | `}` | Ends the function `print_p8`. |

### Function `emit_trial` (trial mode): the P, W, B and C rows of one trial (lines 2472 to 2514)

| Line | Source | Explanation |
|---:|---|---|
| 2472 | `/* All rows of one trial after its S row. */` | Comment: the function prints all rows of one trial that come after its S row. |
| 2473 | `static void emit_trial(struct tw *w, int i)` | Starts the function `emit_trial`. It prints the result rows of trial `i` from the record of the trial. It prints bytes and times. It computes no rate. |
| 2474 | `{` | Opens the body of `emit_trial`. |
| 2475 | `    const struct trial *p = &plan.tr[i];` | `p`: trial `i` of the plan. |
| 2476 | `    const struct trec *r = &rec[i];` | `r`: the record of trial `i`. |
| 2477 | `    int g = r->nw - p->nwin; /* index of target window 0 */` | `g`: the index of target window 0 in the window list of the trial: the number of all windows minus the number of target windows. The comment says the same. |
| 2478 | `    int64_t max_gap = -1;` | `max_gap`: the longest time between two windows of the trial, in ns. It starts at -1, which prints as `NA`. |
| 2480 | `    tev_add(w, EV_OUTPUT, 0, 0);` | Logs the start of the output as an event. Without `--trace` this call does nothing. |
| 2481 | `    print_p8(i, "pre", &r->pg[0], r->vm[0]);` | P row `pre`: the page state before the timed sequence (`print_p8`, line 2462). |
| 2482 | `    for (int k = 0; k < r->nw; k++) {` | Loop over all windows of the trial. |
| 2483 | `        const struct win *x = &r->win[k];` | `x`: the record of window `k`. |
| 2484 | `        printf("W,%d,%s,%d,%s,%lu,%lu,%lld,%lld\n", i, phase_name[x->phase], x->widx, kernels[x->k].name,` | W row, one per window. Its columns: the letter `W`, the trial number, the name of the phase, the number of the window inside the phase, the kernel name, `pass_bytes`, `bytes`, `t_start_ns` and `t_end_ns`. This line holds the format and the first four values. |
| 2485 | `               (unsigned long)x->size, (unsigned long)x->bytes, (long long)(x->t_start - t_base_ns),` | Continues the call of line 2484. `pass_bytes` is the range size of one kernel call. `bytes` is the byte count of the window: the range size times the number of kernel calls. `t_start_ns` is the start clock read of the window, in ns after the process start (`t_base_ns`). |
| 2486 | `               (long long)(x->t_end - t_base_ns));` | Continues the call of line 2484: `t_end_ns`, the last clock read of the window, in ns after the process start. The row holds no rate. The file `DECISIONS-bwx8.md` defines the rate of a window as `bytes` divided by `t_end_ns - t_start_ns`. |
| 2487 | `        if (k && x->t_start - r->win[k - 1].t_end > max_gap)` | Tests, for every window but the first, whether the time from the end clock read of the window before to the start clock read of this window is the longest so far. |
| 2488 | `            max_gap = x->t_start - r->win[k - 1].t_end;` | Keeps the longest such time in `max_gap`. |
| 2489 | `    }` | Ends the loop over the windows (line 2482). |
| 2490 | `    for (int k = g; k < r->nw; k++)` | Loop over the target windows of the trial. |
| 2491 | `        for (int b = 0; b < r->win[k].nbin; b++)` | Loop over the bins that the window closed. |
| 2492 | `            printf("B,%d,%d,%d,%lld,%lu\n", i, r->win[k].widx, b, (long long)(r->win[k].bin[b].t_end - t_base_ns),` | B row, one per bin. Its columns: the letter `B`, the trial number, the number of the target window, the bin number, `t_end_ns` and the byte count of the bin. `t_end_ns` is the clock read that closed the bin, in ns after the process start. This line holds the format and the first four values. |
| 2493 | `                   (unsigned long)r->win[k].bin[b].bytes);` | Continues the call of line 2492: the bytes that the window counted from its start to that clock read. |
| 2494 | `    for (int k = 0; r->cnt && k < p->nwin; k++) {` | Loop over the target windows. It runs only for a trial with counter readings (counter state `read`). |
| 2495 | `        const struct counts *c0 = &r->cnt[k], *c1 = &r->cnt[k + 1];` | `c0`, `c1`: the reading before the start clock read of the window, and the reading after its end clock read. |
| 2496 | `        int group = w->t.group_fd >= 0 && !r->read_fail;` | `group`: 1 when a counter group is open and no group reading of the trial failed. |
| 2497 | `        printf("C,%d,%d", i, k);` | C row, one per target window. It starts with the letter `C`, the trial number and the window number. Every value after them is the difference of the two readings. The C rows of the interval mode have other columns: round, position, kernel name, thread index and CPU come first. `main` prints those rows (lines 3249 to 3266). |
| 2498 | `        if (group)` | Tests whether the group readings can be used. |
| 2499 | `            printf(",%llu,%llu", (unsigned long long)(c1->enabled - c0->enabled),` | Columns 4 and 5, `enabled_ns` and `running_ns`: the growth of the enabled time and of the running time between the two readings, in ns. This line holds the enabled time. |
| 2500 | `                   (unsigned long long)(c1->running - c0->running));` | Continues the call of line 2499: the growth of the running time. |
| 2501 | `        else` | The case of no open group, or of a failed group reading. |
| 2502 | `            printf(",NA,NA");` | Columns 4 and 5 are then `NA`. |
| 2503 | `        printf(",%llu", (unsigned long long)(c1->cpu_ns - c0->cpu_ns));` | Column 6, `cputime_ns`: the growth of the thread CPU time between the two readings, in ns. |
| 2504 | `        for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `cfg`. |
| 2505 | `            int at = w->t.ev_pos[e];` | `at`: the position of the event in a group reading, or -1 for an event that did not open. |
| 2506 | `            if (!group \|\| at < 0)` | Tests whether the value cannot be given: the group readings cannot be used, or the event did not open. |
| 2507 | `                printf(",NA");` | The field is then `NA`. |
| 2508 | `            else` | The case of a value that can be given. |
| 2509 | `                printf(",%llu", (unsigned long long)(c1->val[at] - c0->val[at]));` | One column per event: the count at the second reading minus the count at the first reading. |
| 2510 | `        }` | Ends the loop over the events (line 2504). |
| 2511 | `        printf("\n");` | Ends the row with a line break. |
| 2512 | `    }` | Ends the loop over the target windows (line 2494). |
| 2513 | `    print_p8(i, "post", &r->pg[1], r->vm[1]);` | P row `post`: the page state after the timed sequence. |

### Function `emit_trial` (trial mode): the X rows, the E row and the trace rows (lines 2515 to 2563)

| Line | Source | Explanation |
|---:|---|---|
| 2515 | `    if (r->pg[0].kb_huge < 0 \|\| r->pg[1].kb_huge < 0)` | Tests whether a reading of the page state found no exact entry for the buffer in `/proc/self/smaps`, before or after the timed sequence. |
| 2516 | `        printf("X,%d,coverage_na,the buffer has no exact entry in /proc/self/smaps\n", i);` | X row with the code `coverage_na`. An X row reports a problem: the letter `X`, the trial number, a code and a text. |
| 2517 | `    if (r->close_fail)` | Tests whether a `close` call failed when the counter group was closed at the start of this trial (line 2337). |
| 2518 | `        printf("X,%d,count_close,%d counter descriptors did not close\n", i, r->close_fail);` | X row with the code `count_close` and the number of counter file descriptors that did not close. |
| 2519 | `    if (r->state == CS_FAIL)` | Tests whether the trial wanted counters and an event did not open. |
| 2520 | `        printf("X,%d,count_open,%d of %d events did not open; first: %s\n", i, w->open_fail, cfg.nev, w->open_err);` | X row with the code `count_open`: how many of the events did not open, and the error text of the first one. |
| 2521 | `    if (r->read_fail)` | Tests whether a group reading failed during the timed sequence. |
| 2522 | `        printf("X,%d,count_read,%d reads of the counter group failed\n", i, r->read_fail);` | X row with the code `count_read` and the number of failed group readings. |
| 2523 | `    if (r->cnt && w->t.group_fd >= 0 && !r->read_fail) {` | Tests whether the trial has counter readings that can be used: readings exist, a group is open, and no reading failed. |
| 2524 | `        int m = first_multiplexed(r->cnt, p->nwin);` | `m`: the first target window in which the counters did not count all the time (`first_multiplexed`, line 2321), or -1. |
| 2525 | `        if (m >= 0)` | Tests whether there is such a window. |
| 2526 | `            printf("X,%d,count_multiplexed,target window %d: running_ns %llu below enabled_ns %llu\n", i, m,` | X row with the code `count_multiplexed`: the number of the target window, and its running time and its enabled time in ns. The running time is the smaller one. |
| 2527 | `                   (unsigned long long)(r->cnt[m + 1].running - r->cnt[m].running),` | Continues the call of line 2526: the growth of the running time in that window. |
| 2528 | `                   (unsigned long long)(r->cnt[m + 1].enabled - r->cnt[m].enabled));` | Continues the call of line 2526: the growth of the enabled time in that window. |
| 2529 | `    }` | Ends the `if` of line 2523. |
| 2530 | `    if (r->sink_ok == 0)` | Tests whether the sum check of the old read kernel failed (line 2369). |
| 2531 | `        printf("X,%d,sink,the last old read did not leave the sum of its range in the sink\n", i);` | X row with the code `sink`: the last old read kernel did not leave the sum of its range in the sink. |
| 2533 | `    printf("E,%d,%lld,%llu", i, (long long)(r->win[r->nw - 1].t_end - r->win[0].t_start),` | E row, one per trial: the summary of the trial. Columns 1 to 4: the letter `E`, the trial number, `wall_ns` and `cpu_ns`. `wall_ns` is the time from the start clock read of the first window to the end clock read of the last window, in ns. |
| 2534 | `           (unsigned long long)(r->cpu[1] - r->cpu[0]));` | Continues the call of line 2533: `cpu_ns`, the growth of the thread CPU time between the two `tcpu` calls of `run_trial` (line 2357, line 2366), in ns. |
| 2535 | `    if (r->nvcsw[0] < 0 \|\| r->nvcsw[1] < 0)` | Tests whether a reading of the context switches failed. |
| 2536 | `        printf(",NA,NA");` | Columns 5 and 6 are then `NA`. |
| 2537 | `    else` | The case of two good readings. |
| 2538 | `        printf(",%ld,%ld", r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]);` | Columns 5 and 6, `nvcsw` and `nivcsw`: the numbers of voluntary and of involuntary context switches of the worker between the two `switches` calls of `run_trial` (line 2356, line 2367). |
| 2539 | `    print_na(g ? r->win[g].t_start - r->win[g - 1].t_end : -1);` | Column 7, `gap_ns`: the time from the end clock read of the window before target window 0 to the start clock read of target window 0. A trial without a window before its first target window prints `NA`. |
| 2540 | `    print_na(max_gap);` | Column 8, `max_boundary_gap_ns`: `max_gap`, the longest time between two windows of the trial (lines 2487 to 2488). A trial with one window prints `NA`. |
| 2541 | `    if (r->sink_ok < 0)` | Tests whether the trial ran no old read kernel. |
| 2542 | `        printf(",NA");` | Column 9, `sink_ok`, is then `NA`. |
| 2543 | `    else` | The case of a trial that ran an old read kernel. |
| 2544 | `        printf(",%d", r->sink_ok);` | Column 9 is then 1 for a right sum and 0 for a wrong sum. |
| 2545 | `    printf(",%s\n", count_name[r->state]);` | Column 10, `count_state`: the counter state of the trial as a word: `closed`, `open`, `read` or `fail`. The line break ends the row. |
| 2547 | `    for (long n = 0; n < w->nlog; n++) {` | Loop over the events of the trace. Without `--trace` the log holds no event. |
| 2548 | `        const struct tev *e = &w->log[n];` | `e`: one event of the log. |
| 2549 | `        if (e->ev == EV_KERNEL_FIRST)` | Tests whether the event is the first kernel call of a window. |
| 2550 | `            printf("TR,%d,%ld,%s:%s:%d,%lld\n", i, n, event_name[e->ev], phase_name[e->phase], e->widx,` | TR row of such an event: the letters `TR`, the trial number, the event number, then the event name with the phase name and the window number (joined by colons), then the time of the event. |
| 2551 | `                   (long long)(e->t - t_base_ns));` | Continues the call of line 2550: the time of the event, in ns after the process start. |
| 2552 | `        else` | The case of every other event. |
| 2553 | `            printf("TR,%d,%ld,%s,%lld\n", i, n, event_name[e->ev], (long long)(e->t - t_base_ns));` | TR row of another event: the letters `TR`, the trial number, the event number, the event name and the time in ns after the process start. For an event that is not a clock read this is the time of the clock read before it. |
| 2554 | `    }` | Ends the loop over the events (line 2547). |
| 2555 | `    if (w->ndrop)` | Tests whether events did not fit into the log. |
| 2556 | `        printf("# trace_dropped,%d,%ld\n", i, w->ndrop);` | Prints the line `# trace_dropped` with the trial number and the number of events that the log did not keep. The log keeps 1048576 events per trial (`TRACE_CAP`, line 1970). |
| 2557 | `    /* --trace: minor page faults of the worker between the two rusage reads.` | Comment: with `--trace` the next statement prints the minor page faults of the worker between the two `getrusage` readings. |
| 2558 | `     * Above 0: a page was first touched inside the timed sequence. */` | Comment: a value above 0 means that a page got its first touch inside the timed sequence. The two readings also enclose the two `tcpu` calls of `run_trial` (line 2357, line 2366). |
| 2559 | `    if (w->log)` | Tests whether a log exists (`--trace`). |
| 2560 | `        printf("# minflt,%d,%ld\n", i, r->minflt[0] < 0 \|\| r->minflt[1] < 0 ? -1 : r->minflt[1] - r->minflt[0]);` | Prints the line `# minflt` with the trial number and the number of minor page faults between the two `switches` calls. It prints -1 when a reading failed. |
| 2561 | `    fflush(stdout);` | `fflush` writes the buffered rows to the output before the next trial starts. |
| 2562 | `}` | Ends the function `emit_trial`. |

### The evict step of `--evict-mb` (trial mode): variables and the function `evict_step` (lines 2564 to 2604)

| Line | Source | Explanation |
|---:|---|---|
| 2564 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. This block ends in line 2604. |
| 2565 | `/*` | Comment: starts the comment about the evict step. The comment ends in line 2579. |
| 2566 | ` * --evict-mb N. evict_step() maps N MiB of anonymous private memory (plain` | Comment: the option `--evict-mb N`. The function `evict_step` maps N MiB of anonymous private memory. The sentence goes on in line 2567. |
| 2567 | ` * mmap, no madvise), stores one 8-byte word to every 64 B line in ascending` | Comment: the function uses a plain `mmap` without `madvise`. It stores one 8-byte word to every 64 B line, from the lowest address up. The sentence goes on in line 2568. |
| 2568 | ` * order, in two passes, and unmaps the range. The stores go through a` | Comment: it does this in two passes and then unmaps the range. The sentence about the stores starts here. |
| 2569 | ` * volatile pointer, so gcc keeps every one of them and does not call memset.` | Comment: the stores go through a `volatile` pointer. So gcc keeps every store and does not call `memset`. |
| 2570 | ` * Purpose: the lines of the benchmark buffer leave the caches. The first` | Comment: the purpose: the 64 B lines of the benchmark buffer leave the caches. The reason starts here. |
| 2571 | ` * touch wrote them, so they were dirty. The next read brings them back from` | Comment: the first touch wrote these lines, so they were dirty. A dirty line holds data that the cache has not yet written back to memory. The sentence about the next read starts here. |
| 2572 | ` * memory, clean.` | Comment: the next read brings the lines back from memory, clean. |
| 2573 | ` * trial_worker() calls it once, after the first touch of the buffer and of` | Comment: `trial_worker` calls the function once, after the first touch of the buffer. The sentence goes on in line 2574. |
| 2574 | ` * the record block and before the first trial. No timed sequence holds it.` | Comment: the call also comes after the first touch of the record block and before the first trial. No timed sequence holds the evict step. |
| 2575 | ` * evict_t holds one clock read before the mmap and one after the munmap.` | Comment: `evict_t` holds one clock read before the `mmap` and one after the `munmap`. |
| 2576 | ` * Returns 0, or -1 with the text of the error in evict_err.` | Comment: the function returns 0. On an error it returns -1 and leaves the text of the error in `evict_err`. |
| 2577 | ` * These definitions stand after timed_sequence_hot() and after every other` | Comment: these definitions stand after `timed_sequence_hot` and after every other variable of the trial mode. The sentence ends in line 2578. |
| 2578 | ` * variable of the trial mode, so nothing before them moves.` | Comment: so nothing that stands before them moves to another address. |
| 2579 | ` */` | Comment: the end of the comment. |
| 2580 | `static long evict_mb;      /* --evict-mb: 0 = no evict step */` | `evict_mb`: the value of `--evict-mb` in MiB. The value 0 means no evict step. |
| 2581 | `static int64_t evict_t[2]; /* CLOCK_MONOTONIC, ns */` | `evict_t`: the two clock reads around the evict step, in ns of the Linux clock `CLOCK_MONOTONIC`. |
| 2582 | `static char evict_err[160];` | `evict_err`: the text of an error of the evict step. |
| 2584 | `__attribute__((noinline)) static int evict_step(void)` | Starts the function `evict_step`. It writes `evict_mb` MiB of other memory two times. The aim: the 64 B lines of the benchmark buffer leave the caches. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 2585 | `{` | Opens the body of `evict_step`. |
| 2586 | `    size_t len = (size_t)evict_mb << 20;` | `len`: the size of the memory in bytes: `evict_mb` times 1048576. |
| 2587 | `    evict_t[0] = now_ns();` | First clock read (`now_ns`, line 358), before the `mmap`. |
| 2588 | `    volatile uint64_t *m = mmap(NULL, len, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `len` bytes of new private anonymous memory. `m` points to `volatile` data. So the compiler must keep every store of line 2595. |
| 2589 | `    if (m == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 2590 | `        snprintf(evict_err, sizeof evict_err, "mmap of %ld MiB failed: %s", evict_mb, strerror(errno));` | Stores the error text in `evict_err`: the words `mmap of`, the size in MiB, the word `failed` and the reason that Linux gave. |
| 2591 | `        return -1;` | Returns -1. |
| 2592 | `    }` | Ends the `if` of line 2589. |
| 2593 | `    for (int pass = 0; pass < 2; pass++)` | Two passes over the whole range. |
| 2594 | `        for (size_t i = 0; i < len / 8; i += 8)` | Loop over the range. `i` counts 8-byte words, so `i += 8` is a step of 64 B: one store per 64 B line, from the lowest address up. |
| 2595 | `            m[i] = (uint64_t)i + (uint64_t)pass + 1;` | Stores one 8-byte word at the start of the 64 B line. The value is the word index plus the pass number plus 1. |
| 2596 | `    if (munmap((void *)m, len) != 0) {` | Unmaps the memory and tests whether `munmap` failed. |
| 2597 | `        snprintf(evict_err, sizeof evict_err, "munmap of %ld MiB failed: %s", evict_mb, strerror(errno));` | Stores the error text in `evict_err`: the words `munmap of`, the size in MiB, the word `failed` and the reason that Linux gave. |
| 2598 | `        return -1;` | Returns -1. |
| 2599 | `    }` | Ends the `if` of line 2596. |
| 2600 | `    evict_t[1] = now_ns();` | Second clock read, after the `munmap`. |
| 2601 | `    return 0;` | Returns 0: the step is done. |
| 2602 | `}` | Ends the function `evict_step`. |
| 2604 | `/* bwx11- */` | Comment: marks the end of the block that `bwx11` added. The block starts in line 2564. |

### Function `trial_worker` (trial mode): pinning, buffer, first touch and records (lines 2605 to 2625)

| Line | Source | Explanation |
|---:|---|---|
| 2605 | `static void *trial_worker(void *arg)` | Starts the function `trial_worker`, the start function of the one worker thread of the trial mode. `trial_main` creates the thread in line 3036. |
| 2606 | `{` | Opens the body of `trial_worker`. |
| 2607 | `    struct tw *w = arg;` | `w`: the state of the worker (line 2044). |
| 2608 | `    volatile uint64_t sink = 0;` | `sink`: the volatile variable on the stack of the worker that receives the sum of an old read kernel. It starts at 0. |
| 2609 | `    int madvise_ok;` | `madvise_ok`: will hold whether the request for the page policy succeeded (line 2621). |
| 2611 | `    pin_cpu(cfg.cpus[0]);` | CPU pinning. The worker pins itself to the one CPU of `--cpus` (`pin_cpu`, line 446). |
| 2612 | `    if (sched_getcpu() != cfg.cpus[0]) {` | Asks Linux on which CPU the thread runs now (`sched_getcpu`) and tests whether it is another CPU than the one of `--cpus`. |
| 2613 | `        fprintf(stderr, "the worker runs on CPU %d, not on CPU %d\n", sched_getcpu(), cfg.cpus[0]);` | Prints both CPU numbers to stderr. |
| 2614 | `        exit(2);` | Ends the process with exit status 2. |
| 2615 | `    }` | Ends the `if` of line 2612. |
| 2616 | `    w->v = ((uint64_t)getpid() + 1) * 0x9E3779B97F4A7C15ULL;` | `w->v`: the value that the first touch of line 2622 stores into the 8-byte words of the buffer: the process id (`getpid`) plus 1, times a fixed 64-bit constant. |
| 2617 | `    w->t.group_fd = -1;` | The worker has no counter group yet. |
| 2618 | `    w->t.a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 465) maps the one buffer of the worker: it starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. |
| 2619 | `    /* alloc_buf() does not return the result of its madvise. The same request` | Comment: `alloc_buf` does not return the result of its `madvise` call. The sentence about the next statement starts here. |
| 2620 | `     * again gives it. */` | Comment: the same request once more gives the result. |
| 2621 | `    madvise_ok = madvise(w->t.a, buf_len(), cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) == 0;` | Repeats the `madvise` request of `alloc_buf` for the buffer: a request for 2 MiB pages, or with `--no-thp` for no such pages. `madvise_ok` is 1 when the call succeeded. |
| 2622 | `    k_write(w->t.a, cfg.bytes / 8, w->v); /* first touch by the pinned worker */` | First touch. The pinned worker stores `w->v` into `cfg.bytes / 8` words of 8 bytes with `k_write` (line 562): every word of the `--bytes` range of the buffer. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 459). This line is not timed. |
| 2623 | `    alloc_records(w);` | `alloc_records` (line 2417) allocates the record block and touches every page of it. |
| 2624 | `    w->last_t = t_base_ns;` | The trace starts with the process start time as the time of the latest clock read. |

### Function `trial_worker` (trial mode): header lines and the rows before the first trial (lines 2626 to 2692)

| Line | Source | Explanation |
|---:|---|---|
| 2626 | `    printf("# bwx8 trial mode: GB = 1e9 bytes; times are whole ns since process start on CLOCK_MONOTONIC\n"` | Starts the `printf` call that prints the header lines of the trial mode. Each header line starts with `#`. This first line says: GB means 1e9 bytes, and times are whole ns after the process start on the clock `CLOCK_MONOTONIC`. The text names `bwx8`, the version of the runner that added the trial mode. |
| 2627 | `           "# S,trial,cond,rep,prev,pfx,pred,tgt,nwin,win_ms,count,bins,prev_cond,prev_tgt\n"` | Text of the header: the column names of the S rows. |
| 2628 | `           "# P,trial,when,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n"` | Text of the header: the column names of the P rows of the trial mode. |
| 2629 | `           "# W,trial,phase,widx,kernel,pass_bytes,bytes,t_start_ns,t_end_ns\n"` | Text of the header: the column names of the W rows. |
| 2630 | `           "# B,trial,widx,bin,t_end_ns,bytes_since_window_start\n"` | Text of the header: the column names of the B rows. |
| 2631 | `           "# C,trial,widx,enabled_ns,running_ns,cputime_ns");` | Text of the header: the first six column names of the C rows of the trial mode. The header line has no line break yet. |
| 2632 | `    for (int e = 0; e < cfg.nev; e++)` | Loop over the events of `cfg`. |
| 2633 | `        printf(",%s", cfg.ev_name[e]);` | Appends one event name per event to the header line of the C rows. |
| 2634 | `    printf("\n# E,trial,wall_ns,cpu_ns,nvcsw,nivcsw,gap_ns,max_boundary_gap_ns,sink_ok,count_state\n"` | Ends the header line of the C rows. Then comes the header line with the column names of the E rows. |
| 2635 | `           "# X,trial,code,text\n"` | Text of the header: the column names of the X rows. |
| 2636 | `           "# TR,trial,n,event,t_ns; t_ns of an event that is not a clock read is the time of the clock read before it\n");` | Text of the header: the column names of the TR rows. The text adds: the time of an event that is not a clock read is the time of the clock read before it. |
| 2637 | `    printf("M,mode,trial\nM,cpu,%d\nM,ctl_cpu,%d\nM,bytes,%lu\nM,thp,%s\nM,madvise_ok,%d\nM,check_bytes,%lu\nM,kernels,%s\n",` | M rows. Each M row holds one setting or one fact in the form `M,name,value`. This call prints `mode` (the word `trial`), `cpu` (the worker CPU), `ctl_cpu` (the CPU of the controlling thread), `bytes` (the buffer size), `thp` (the page policy), `madvise_ok`, `check_bytes` and `kernels`. |
| 2638 | `           cfg.cpus[0], plan.ctl_cpu, (unsigned long)cfg.bytes, cfg.use_thp ? "madvise" : "nohugepage", madvise_ok,` | Continues the call of line 2637: the values of `cpu`, `ctl_cpu`, `bytes`, `thp` (the word `madvise` or `nohugepage`) and `madvise_ok`. |
| 2639 | `           (unsigned long)CHECK_BYTES, STANDIN ? "STAND-IN" : "aarch64");` | Continues the call of line 2637: `check_bytes` is `CHECK_BYTES` (8388608 bytes, which is 8 MiB). `kernels` is `aarch64`, or `STAND-IN` for a build with stand-in kernels. |
| 2640 | `    printf("M,plan_fnv1a64,%016llx\nM,ntrials,%d\nM,rec_windows,%zu\nM,rec_bins,%zu\nM,rec_counts,%zu\nM,rec_trace,%zu\n"` | More M rows: `plan_fnv1a64` (the checksum of the plan file, 16 hexadecimal digits), `ntrials` (the number of trials), and the sizes of the record storage: `rec_windows`, `rec_bins`, `rec_counts` and `rec_trace`. |
| 2641 | `           "M,rec_bytes,%zu\nM,trace,%d\n",` | Continues the format of line 2640: `rec_bytes` (the size of the record block in bytes) and `trace` (0 or 1). |
| 2642 | `           (unsigned long long)plan.hash, plan.n, recsz.windows, recsz.bins, recsz.counts, recsz.trace, recsz.bytes,` | Continues the call of line 2640: the values of the first seven of these rows. |
| 2643 | `           plan.trace);` | Continues the call of line 2640: the value of `trace`. |
| 2644 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2645 | `    /* Addresses in hex without "0x", as in the K rows. rec_addr: the record` | Comment: the addresses are printed in hexadecimal without `0x`, as in the K rows. `rec_addr` is the address of the record block. The list goes on in line 2646. |
| 2646 | `     * block. win_addr: win[0] of trial 0. stack_addr: the sink of the worker. */` | Comment: `win_addr` is the address of the first window record of trial 0. `stack_addr` is the address of the sink of the worker. |
| 2647 | `    printf("M,rec_pad,%zu\nM,hot_copy,%d\nM,rec_addr,%lx\nM,win_addr,%lx\nM,win_size,%zu\nM,stack_addr,%lx\nM,buf_addr,%lx\n"` | More M rows: `rec_pad`, `hot_copy`, `rec_addr`, `win_addr`, `win_size` (the size of one window record in bytes), `stack_addr` and `buf_addr` (the address of the buffer). |
| 2648 | `           "M,tw_addr,%lx\n",` | Continues the format of line 2647: `tw_addr`, the address of the state of the worker. |
| 2649 | `           plan.rec_pad, plan.hot_copy, (unsigned long)(uintptr_t)rec, (unsigned long)(uintptr_t)rec[0].win,` | Continues the call of line 2647: the values of `rec_pad`, `hot_copy`, `rec_addr` and `win_addr`. |
| 2650 | `           sizeof(struct win), (unsigned long)(uintptr_t)&sink, (unsigned long)(uintptr_t)w->t.a,` | Continues the call of line 2647: the values of `win_size`, `stack_addr` and `buf_addr`. |
| 2651 | `           (unsigned long)(uintptr_t)w);` | Continues the call of line 2647: the value of `tw_addr`. |
| 2652 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2653 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2654 | `    /* The evict step. The buffer and the record block are first touched, and` | Comment: the evict step. At this point the buffer and the record block have got their first touch. The sentence goes on in line 2655. |
| 2655 | `     * no trial has started. With --evict-mb 0 no call is made. A failure` | Comment: no trial has started at this point. With `--evict-mb 0` the function is not called. The sentence about a failure starts here. |
| 2656 | `     * ends the process here: the X row is the last row. */` | Comment: a failure ends the process here, and the X row is the last row of the output. |
| 2657 | `    printf("M,evict_mb,%ld\n", evict_mb);` | M row `evict_mb`: the value of `--evict-mb`. |
| 2658 | `    if (evict_mb > 0 && evict_step() != 0) {` | With a value above 0: runs the evict step (`evict_step`, line 2584) and tests whether it failed. |
| 2659 | `        printf("X,-1,evict,%s\n", evict_err);` | X row with the trial number -1, the code `evict` and the error text. |
| 2660 | `        fflush(stdout);` | Writes the buffered rows to the output. |
| 2661 | `        exit(2);` | Ends the process with exit status 2. |
| 2662 | `    }` | Ends the `if` of line 2658. |
| 2663 | `    printf("M,evict_ns,%lld\n", (long long)(evict_t[1] - evict_t[0]));` | M row `evict_ns`: the time between the two clock reads of the evict step, in ns. It is 0 when no step ran. |
| 2664 | `    if (evict_mb > 0 && plan.trace)` | Tests whether a step ran and the trace is on. |
| 2665 | `        printf("TR,-1,0,evict_start,%lld\nTR,-1,1,evict_end,%lld\n", (long long)(evict_t[0] - t_base_ns),` | Two TR rows with the trial number -1: `evict_start` and `evict_end`, with the two clock reads of the step in ns after the process start. This line holds the time of `evict_start`. |
| 2666 | `               (long long)(evict_t[1] - t_base_ns));` | Continues the call of line 2665: the time of `evict_end`. |
| 2667 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2668 | `    if (cfg.pmu_type < 0)` | Tests whether no PMU type was given. |
| 2669 | `        printf("M,pmu_type,none\n");` | M row `pmu_type` with the word `none`. |
| 2670 | `    else` | The case of a given PMU type. |
| 2671 | `        printf("M,pmu_type,%ld\n", cfg.pmu_type);` | M row `pmu_type` with the number. |
| 2672 | `    printf("M,events,%s", cfg.nev ? "" : "none");` | Starts the M row `events`. Without events its value is the word `none`. |
| 2673 | `    for (int e = 0; e < cfg.nev; e++)` | Loop over the events of `cfg`. |
| 2674 | `        printf("%s%s=0x%llx", e ? ";" : "", cfg.ev_name[e], (unsigned long long)cfg.ev_code[e]);` | Prints one event as its name, the sign `=` and its code in hexadecimal with `0x`. A semicolon separates two events. |
| 2675 | `    printf("\n");` | Ends the row with a line break. |
| 2676 | `    for (int i = 0; i < plan.npair; i++) {` | Loop over the `key=value` pairs of the second line of the plan. |
| 2677 | `        char *eq = strchr(plan.pair[i], '=');` | `eq`: the place of the `=` sign in the pair. |
| 2678 | `        printf("M,plan.%.*s,%s\n", (int)(eq - plan.pair[i]), plan.pair[i], eq + 1);` | One M row per pair: the name is `plan.` plus the key, and the value is the text after the `=` sign. |
| 2679 | `    }` | Ends the loop of line 2676. |
| 2680 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the kernel table. |
| 2681 | `        int used = 0;` | `used`: becomes 1 when a trial of the plan uses kernel `k`. |
| 2682 | `        for (int i = 0; i < plan.n && !used; i++) {` | Loop over the trials. It stops at the first trial that uses the kernel. |
| 2683 | `            const struct trial *p = &plan.tr[i];` | `p`: one trial of the plan. |
| 2684 | `            used = p->prev.k == k \|\| p->pfx.k == k \|\| p->pred.k == k \|\| p->tgt.k == k;` | Tests whether one of the four parts of the trial names kernel `k`. |
| 2685 | `        }` | Ends the loop of line 2682. |
| 2686 | `        if (used)` | Tests whether the plan uses the kernel. |
| 2687 | `            printf("K,%s,%lx,%lu\n", kernels[k].name, (unsigned long)(uintptr_t)kernels[k].fn,` | K row, one per kernel that the plan uses: the letter `K`, the kernel name, the address of its function in hexadecimal, and this address modulo 64. |
| 2688 | `                   (unsigned long)((uintptr_t)kernels[k].fn % 64));` | Continues the call of line 2687: the address modulo 64. |
| 2689 | `    }` | Ends the loop over the kernel table (line 2680). |
| 2690 | `    if (!madvise_ok)` | Tests whether the `madvise` request of line 2621 failed. |
| 2691 | `        printf("X,-1,madvise,the page policy request failed\n");` | X row with the trial number -1 and the code `madvise`: the request for the page policy failed. |

### Function `trial_worker` (trial mode): the loop over the trials and the end (lines 2693 to 2709)

| Line | Source | Explanation |
|---:|---|---|
| 2693 | `    for (int i = 0; i < plan.n; i++) {` | Loop over the trials, in the order of the plan. |
| 2694 | `        w->nlog = w->ndrop = 0;` | Empties the trace: no event in the log, and a count of 0 for the events that did not fit. |
| 2695 | `        w->cur_phase = -1;` | No window counts as logged yet. So the first kernel call of the trial is logged (line 2112). |
| 2696 | `        tev_add(w, EV_OUTPUT, 0, 0);` | Logs the start of the output as an event. Without `--trace` this call does nothing. |
| 2697 | `        print_s(i);` | Prints the S row of the trial (`print_s`, line 2453). |
| 2698 | `        fflush(stdout);` | Writes the buffered rows to the output before the trial runs. |
| 2699 | `        run_trial(w, &plan.tr[i], &rec[i], &sink);` | Runs the trial (`run_trial`, line 2331). That function prints nothing. So the process writes no output inside a timed sequence. |
| 2700 | `        emit_trial(w, i);` | Prints the result rows of the trial (`emit_trial`, line 2473). |
| 2701 | `    }` | Ends the loop over the trials (line 2693). |
| 2702 | `    if (w->group_open)` | Tests whether the counter group is still open after the last trial. |
| 2703 | `        count_close(w);` | Then the group is closed (`count_close`, line 2252). |
| 2704 | `    if (w->close_fail)` | Tests whether a `close` call failed. |
| 2705 | `        printf("X,-1,count_close,%d counter descriptors did not close\n", w->close_fail);` | X row with the trial number -1 and the code `count_close`: the number of counter file descriptors that did not close. |
| 2706 | `    fflush(stdout);` | Writes the buffered rows to the output. |
| 2707 | `    return NULL;` | The worker thread ends. `trial_main` waits for its end in line 3040. |
| 2708 | `}` | Ends the function `trial_worker`. |

### Function `plan_bad` (trial mode): report a defect of the plan file (lines 2710 to 2720)

| Line | Source | Explanation |
|---:|---|---|
| 2710 | `static void plan_bad(int line, const char *fmt, ...)` | Starts the function `plan_bad`. It reports a defect of the plan file on stderr and ends the process with exit status 2. `line` is the number of the plan line. `fmt` and the arguments after it form the message, as in `printf`. |
| 2711 | `{` | Opens the body of `plan_bad`. |
| 2712 | `    va_list ap;` | `ap`: the list of the arguments that follow `fmt`. |
| 2713 | `    fprintf(stderr, "bad plan %s, line %d: ", plan.path, line);` | Prints the start of the message to stderr: the words `bad plan`, the path of the plan file, the word `line` and the number of the plan line. |
| 2714 | `    va_start(ap, fmt);` | Starts the reading of the arguments that follow `fmt`. |
| 2715 | `    vfprintf(stderr, fmt, ap);` | `vfprintf` prints the message itself to stderr. It builds the text from `fmt` and these arguments. |
| 2716 | `    va_end(ap);` | Ends the reading of the arguments. |
| 2717 | `    fprintf(stderr, "\n");` | Ends the message with a line break. |
| 2718 | `    exit(2);` | Ends the process with exit status 2. |
| 2719 | `}` | Ends the function `plan_bad`. |

### Functions `plan_long` and `plan_size` (trial mode): a number and a size of the plan (lines 2721 to 2754)

| Line | Source | Explanation |
|---:|---|---|
| 2721 | `/* A whole number in [lo, hi] made of digits only. */` | Comment: the function accepts a whole number from `lo` to `hi` that is made of digits only. |
| 2722 | `static int plan_long(const char *s, long lo, long hi, long *out)` | Starts the function `plan_long`. It turns the text `s` into a whole number. For a good text it stores the number in `*out` and returns 1. For any other text it returns 0. The caller then reports the defect with `plan_bad`. |
| 2723 | `{` | Opens the body of `plan_long`. |
| 2724 | `    char *end;` | `end`: will point to the first character that `strtol` did not read. |
| 2725 | `    if (*s < '0' \|\| *s > '9')` | Tests whether the first character is not a decimal digit. So a sign or a space at the start is rejected. |
| 2726 | `        return 0;` | Such a text returns 0. |
| 2727 | `    errno = 0;` | Sets `errno` to 0. After the next call a value other than 0 shows that the number was too large for the type. |
| 2728 | `    long v = strtol(s, &end, 10);` | `strtol` reads the text as a decimal number. |
| 2729 | `    if (*end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi)` | Tests for four defects: other text follows the number, the number was too large for the type, the number is below `lo`, or it is above `hi`. |
| 2730 | `        return 0;` | A defect returns 0. |
| 2731 | `    *out = v;` | Stores the number. |
| 2732 | `    return 1;` | Returns 1. |
| 2733 | `}` | Ends the function `plan_long`. |
| 2735 | `/* A whole number above 0 with an optional K, M or G. */` | Comment: the function accepts a whole number above 0 with an optional letter `K`, `M` or `G`. |
| 2736 | `static int plan_size(const char *s, uint64_t *out)` | Starts the function `plan_size`. It turns a size text such as `8M` into a number of bytes. For a good text it stores the bytes in `*out` and returns 1. For any other text it returns 0. |
| 2737 | `{` | Opens the body of `plan_size`. |
| 2738 | `    char *end;` | `end`: will point to the first character that `strtoull` did not read. |
| 2739 | `    int shift = 0;` | `shift`: the number of bits by which a letter shifts the number. It is 0 without a letter. |
| 2740 | `    if (*s < '0' \|\| *s > '9')` | Tests whether the first character is not a decimal digit. |
| 2741 | `        return 0;` | Such a text returns 0. |
| 2742 | `    errno = 0;` | Sets `errno` to 0, as in line 2727. |
| 2743 | `    unsigned long long v = strtoull(s, &end, 10);` | `strtoull` reads the text as a decimal number. |
| 2744 | `    switch (*end) {` | Looks at the character after the number. |
| 2745 | `    case 'K': shift = 10; end++; break;` | The letter `K`: the number times 1024 (a shift by 10 bits). |
| 2746 | `    case 'M': shift = 20; end++; break;` | The letter `M`: the number times 1048576, which gives MiB (a shift by 20 bits). |
| 2747 | `    case 'G': shift = 30; end++; break;` | The letter `G`: the number times 1073741824 (a shift by 30 bits). Only capital letters are accepted in a plan. |
| 2748 | `    }` | Ends the `switch` of line 2744. |
| 2749 | `    if (*end != '\0' \|\| errno != 0 \|\| v == 0 \|\| v > (UINT64_MAX >> shift))` | Tests for four defects: other text follows, the number was too large for the type, the number is 0, or the size in bytes does not fit into 64 bits. |
| 2750 | `        return 0;` | A defect returns 0. |
| 2751 | `    *out = (uint64_t)v << shift;` | Stores the size in bytes: the number shifted left by `shift` bits. |
| 2752 | `    return 1;` | Returns 1. |
| 2753 | `}` | Ends the function `plan_size`. |

### Function `plan_part` (trial mode): one kernel field of a trial line (lines 2755 to 2787)

| Line | Source | Explanation |
|---:|---|---|
| 2755 | `/* "KERNEL@SIZE:MS" (with_ms, where "-" is also allowed) or "KERNEL@SIZE". */` | Comment: the field has the form `KERNEL@SIZE:MS` or the form `KERNEL@SIZE`. The first form holds when `with_ms` is set. Then the text `-` is also allowed. |
| 2756 | `static void plan_part(int line, const char *what, const char *s, int with_ms, struct part *p)` | Starts the function `plan_part`. It reads one kernel field `s` of a trial line into `*p`: the index of the kernel, the size in bytes and the duration in ms. `line` is the number of the plan line and `what` the name of the field. Both are for the error message. A defect ends the process through `plan_bad` (line 2710). |
| 2757 | `{` | Opens the body of `plan_part`. |
| 2758 | `    char buf[96];` | `buf`: room for a copy of the field of at most 95 characters. The function cuts the copy into pieces. |
| 2759 | `    p->k = -1;` | Start value: no kernel (`k` is -1). |
| 2760 | `    p->size = 0;` | Start value: the size 0. |
| 2761 | `    p->ms = 0;` | Start value: the duration 0. |
| 2762 | `    if (with_ms && !strcmp(s, "-"))` | Tests whether the field may be left out (`with_ms` is 1) and is the text `-`. |
| 2763 | `        return;` | Then the part is absent, and `p->k` stays -1. |
| 2764 | `    if (strlen(s) >= sizeof buf)` | Tests whether the field has 96 characters or more. |
| 2765 | `        plan_bad(line, "%s is too long", what);` | Such a field is a defect. The message says that the field is too long. |
| 2766 | `    strcpy(buf, s);` | Copies the field into `buf`. |
| 2767 | `    char *at = strchr(buf, '@'), *colon = at ? strchr(at, ':') : NULL;` | `at`: the place of the `@` in the field. `colon`: the place of a colon after the `@`. Each is NULL when the character is missing. |
| 2768 | `    if (!at \|\| with_ms != (colon != NULL))` | Tests for a wrong form. The field has no `@`. Or it has no colon although a duration is needed. Or it has a colon although no duration is allowed. |
| 2769 | `        plan_bad(line, "%s '%s' is not %s", what, s, with_ms ? "'-' or KERNEL@SIZE:MS" : "KERNEL@SIZE");` | The message names the field, its text and the form that is needed. |
| 2770 | `    *at = '\0';` | Ends the kernel name at the `@`: a zero byte replaces the `@`. |
| 2771 | `    if (colon)` | Tests whether the field has a colon. |
| 2772 | `        *colon = '\0';` | Ends the size text at the colon. |
| 2773 | `    int k = 0;` | `k`: the index into the kernel table. The search starts at entry 0. |
| 2774 | `    while (k < K_COUNT && strcmp(buf, kernels[k].name))` | Searches the kernel table for the name, as in line 1913. |
| 2775 | `        k++;` | The body of the search loop: goes on to the next entry of the table. |
| 2776 | `    if (k == K_COUNT)` | Tests whether no entry has the name. |
| 2777 | `        plan_bad(line, "%s: unknown kernel '%s'", what, buf);` | The message says that the kernel is unknown. |
| 2778 | `    if (kernels[k].type != T_READ && kernels[k].type != T_OLDREAD)` | Tests whether the kernel is not a read kernel: its type is not `T_READ` and not `T_OLDREAD`. So the trial mode accepts read kernels only. |
| 2779 | `        plan_bad(line, "%s: '%s' is not a read kernel", what, buf);` | The message says that the kernel is not a read kernel. |
| 2780 | `    if (!plan_size(at + 1, &p->size) \|\| p->size % 256 != 0 \|\| p->size > cfg.bytes)` | Reads the size with `plan_size` (line 2736) and tests for three defects: the text is not a size, the size is not a multiple of 256 bytes, or it is above the `--bytes` value. |
| 2781 | `        plan_bad(line, "%s: size '%s' must be a multiple of 256, above 0 and at most --bytes (%lu)", what, at + 1,` | The message names the size text and the rule: a multiple of 256, above 0 and at most the `--bytes` value. |
| 2782 | `                 (unsigned long)cfg.bytes);` | Continues the call of line 2781: the `--bytes` value. |
| 2783 | `    if (colon && !plan_long(colon + 1, 1, MAX_MS, &p->ms))` | For a field with a duration: reads it with `plan_long` (line 2722). It must be a whole number from 1 to 3600000 ms (`MAX_MS`, 1 hour). |
| 2784 | `        plan_bad(line, "%s: bad duration '%s' (whole ms from 1 to %ld)", what, colon + 1, MAX_MS);` | The message names the bad duration and the allowed range. |
| 2785 | `    p->k = k;` | Stores the index of the kernel. From here on the part exists. |
| 2786 | `}` | Ends the function `plan_part`. |

### Function `plan_pairs` (trial mode): the second line of the plan file (lines 2788 to 2818)

| Line | Source | Explanation |
|---:|---|---|
| 2788 | `/* Line 2: "# key=value key=value ...". bytes and cpu must equal the options. */` | Comment: the second line of the plan has the form `# key=value key=value ...`. The values of `bytes` and `cpu` must equal the options. |
| 2789 | `static void plan_pairs(char *s)` | Starts the function `plan_pairs`. It splits the second line of the plan at each space and keeps a pointer to every pair in `plan.pair`. It also checks the pairs `bytes=` and `cpu=`. |
| 2790 | `{` | Opens the body of `plan_pairs`. |
| 2791 | `    int have_bytes = 0, have_cpu = 0;` | `have_bytes`, `have_cpu`: become 1 when the line holds a pair `bytes=` and a pair `cpu=`. |
| 2792 | `    if (strncmp(s, "# ", 2))` | Tests whether the line does not start with `#` and a space. |
| 2793 | `        plan_bad(2, "the line must start with '# '");` | That is a defect of the plan (`plan_bad`, line 2710). |
| 2794 | `    for (char *tok = s + 2, *sp; tok; tok = sp ? sp + 1 : NULL) {` | Loop over the pairs. `tok` is the start of one pair. `sp` is the space after it, or NULL after the last pair. |
| 2795 | `        sp = strchr(tok, ' ');` | Finds the next space. |
| 2796 | `        if (sp)` | Tests whether a space was found. |
| 2797 | `            *sp = '\0';` | Ends the pair at the space: a zero byte replaces the space. |
| 2798 | `        char *eq = strchr(tok, '=');` | `eq`: the place of the `=` sign in the pair, or NULL. |
| 2799 | `        if (!eq \|\| eq == tok \|\| strchr(tok, ',') \|\| plan.npair == MAX_PAIRS)` | Tests for four defects: no `=` sign, an empty key, a comma in the pair, or a 65th pair (`MAX_PAIRS` is 64). |
| 2800 | `            plan_bad(2, "bad key=value pair '%s'", tok);` | The message names the bad pair. |
| 2801 | `        plan.pair[plan.npair++] = tok;` | Keeps a pointer to the pair. `trial_worker` prints each pair as an M row (lines 2676 to 2679). |
| 2802 | `        if (!strncmp(tok, "bytes=", 6)) {` | Tests whether the pair starts with `bytes=`. |
| 2803 | `            uint64_t b;` | `b`: the size of the pair in bytes. |
| 2804 | `            if (!plan_size(eq + 1, &b) \|\| b != cfg.bytes)` | Reads the size with `plan_size` and tests whether it is no size or differs from the `--bytes` value. |
| 2805 | `                plan_bad(2, "%s differs from --bytes %lu", tok, (unsigned long)cfg.bytes);` | Then the plan has a defect. The message names the pair and the `--bytes` value. |
| 2806 | `            have_bytes = 1;` | Notes that the line has a pair `bytes=`. |
| 2807 | `        }` | Ends the `if` of line 2802. |
| 2808 | `        if (!strncmp(tok, "cpu=", 4)) {` | Tests whether the pair starts with `cpu=`. |
| 2809 | `            long c;` | `c`: the CPU number of the pair. |
| 2810 | `            if (!plan_long(eq + 1, 0, MAX_USE_CPU, &c) \|\| c != cfg.cpus[0])` | Reads the number with `plan_long` (0 to `MAX_USE_CPU`) and tests whether it is no such number or differs from the first CPU of `--cpus`. |
| 2811 | `                plan_bad(2, "%s differs from --cpus %d", tok, cfg.cpus[0]);` | Then the plan has a defect. The message names the pair and the CPU of `--cpus`. |
| 2812 | `            have_cpu = 1;` | Notes that the line has a pair `cpu=`. |
| 2813 | `        }` | Ends the `if` of line 2808. |
| 2814 | `    }` | Ends the loop over the pairs (line 2794). |
| 2815 | `    if (!have_bytes \|\| !have_cpu)` | Tests whether one of the two pairs is missing. |
| 2816 | `        plan_bad(2, "bytes= and cpu= are needed");` | That is a defect. The message says that `bytes=` and `cpu=` are needed. |
| 2817 | `}` | Ends the function `plan_pairs`. |

### Function `plan_trial` (trial mode): one trial line of the plan (lines 2819 to 2879)

| Line | Source | Explanation |
|---:|---|---|
| 2819 | `static void plan_trial(int line, char *s)` | Starts the function `plan_trial`. It reads one trial line `s` of the plan, checks every field and adds one `struct trial` to `plan.tr`. `line` is the number of the plan line. A defect ends the process through `plan_bad` (line 2710). |
| 2820 | `{` | Opens the body of `plan_trial`. |
| 2821 | `    char *f[PLAN_FIELDS];` | `f`: the 11 fields of the line as text. |
| 2822 | `    int nf = 0;` | `nf`: the number of fields found so far. |
| 2823 | `    long v;` | `v`: a number that `plan_long` returns. |
| 2824 | `    for (char *tok = s, *sp; tok; tok = sp ? sp + 1 : NULL) {` | Loop over the fields. `tok` is the start of one field. `sp` is the space after it, or NULL after the last field. |
| 2825 | `        sp = strchr(tok, ' ');` | Finds the next space. |
| 2826 | `        if (sp)` | Tests whether a space was found. |
| 2827 | `            *sp = '\0';` | Ends the field at the space: a zero byte replaces the space. |
| 2828 | `        if (nf == PLAN_FIELDS \|\| *tok == '\0')` | Tests for two defects: a 12th field, or an empty field. An empty field comes from two spaces one after the other, from a space at the start or at the end of the line, or from an empty line. |
| 2829 | `            plan_bad(line, "%d fields separated by single spaces are needed", PLAN_FIELDS);` | The message says that 11 fields separated by single spaces are needed. |
| 2830 | `        f[nf++] = tok;` | Keeps a pointer to the field and counts it. |
| 2831 | `    }` | Ends the loop over the fields (line 2824). |
| 2832 | `    if (nf != PLAN_FIELDS)` | Tests whether the line has fewer than 11 fields. |
| 2833 | `        plan_bad(line, "%d fields separated by single spaces are needed, %d found", PLAN_FIELDS, nf);` | The message says how many fields are needed and how many were found. |
| 2834 | `    plan.tr = realloc(plan.tr, ((size_t)plan.n + 1) * sizeof *plan.tr);` | `realloc` makes the array `plan.tr` one trial longer. |
| 2835 | `    if (!plan.tr)` | Tests whether the memory could not be given. |
| 2836 | `        plan_bad(line, "no memory");` | That ends the process through `plan_bad` with the message `no memory`. |
| 2837 | `    struct trial *p = &plan.tr[plan.n];` | `p`: the new trial. |
| 2838 | `    memcpy(p->f, f, sizeof f);` | Copies the 11 field pointers into the trial. `print_s` prints these texts in the S row (line 2458). |
| 2839 | `    if (!plan_long(f[0], 0, 1000000, &v) \|\| v != plan.n)` | Field 1, `trial`: it must be the number of this trial, counted from 0 in the order of the file. |
| 2840 | `        plan_bad(line, "trial '%s': the trial numbers must be 0, 1, 2, ... (%d expected)", f[0], plan.n);` | The message names the field and the number that was expected. |
| 2841 | `    if (strchr(f[1], ','))` | Field 2, `cond`, a label of the condition: it must hold no comma. |
| 2842 | `        plan_bad(line, "cond '%s' holds a comma", f[1]);` | The message names the label. |
| 2843 | `    if (!plan_long(f[2], 1, 4, &v))` | Field 3, `rep`: a whole number from 1 to 4. The file `DECISIONS-bwx8.md` calls it the number of this repeat of the condition in the process. |
| 2844 | `        plan_bad(line, "rep '%s' is not 1 to 4", f[2]);` | The message names the bad value. |
| 2845 | `    plan_part(line, "prev", f[3], 1, &p->prev);` | Field 4, `prev`: the previous activity. `plan_part` (line 2756) reads it. It has a duration and may be `-`. |
| 2846 | `    plan_part(line, "pfx", f[4], 1, &p->pfx);` | Field 5, `pfx`: the prefix. It has a duration and may be `-`. |
| 2847 | `    plan_part(line, "pred", f[5], 1, &p->pred);` | Field 6, `pred`: the predecessor. It has a duration and may be `-`. |
| 2848 | `    plan_part(line, "tgt", f[6], 0, &p->tgt);` | Field 7, `tgt`: the target. It has no duration field and cannot be left out. |
| 2849 | `    if (p->pfx.k >= 0 && p->pfx.ms % 4 != 0)` | Tests whether the trial has a prefix whose duration is not a multiple of 4 ms. The prefix runs as 4 windows of a quarter of its duration each (line 2405). |
| 2850 | `        plan_bad(line, "pfx duration %ld ms is not a multiple of 4", p->pfx.ms);` | The message names the duration. |
| 2851 | `    if (!plan_long(f[7], 1, MAX_NWIN, &v))` | Field 8, `nwin`: the number of target windows, a whole number from 1 to 4096 (`MAX_NWIN`). |
| 2852 | `        plan_bad(line, "nwin '%s' is not 1 to %d", f[7], MAX_NWIN);` | The message names the bad value. |
| 2853 | `    p->nwin = (int)v;` | Stores the number of target windows. |
| 2854 | `    if (!plan_long(f[8], 1, MAX_MS, &p->win_ms))` | Field 9, `win_ms`: the duration of one target window, a whole number from 1 to 3600000 ms (`MAX_MS`). |
| 2855 | `        plan_bad(line, "win_ms '%s' is not 1 to %ld", f[8], MAX_MS);` | The message names the bad value. |
| 2856 | `    p->count = !strcmp(f[9], "closed") ? CS_CLOSED : !strcmp(f[9], "open") ? CS_OPEN : !strcmp(f[9], "read") ? CS_READ : -1;` | Field 10, `count`: the counter state. The words `closed`, `open` and `read` give the codes of line 1980. Any other word gives -1. |
| 2857 | `    if (p->count < 0)` | Tests whether the word was none of the three. |
| 2858 | `        plan_bad(line, "count '%s' is not closed, open or read", f[9]);` | The message names the bad word. |
| 2859 | `    if (strcmp(f[10], "0") && strcmp(f[10], "1"))` | Field 11, `bins`: tests whether the text is neither `0` nor `1`. |
| 2860 | `        plan_bad(line, "bins '%s' is not 0 or 1", f[10]);` | The message names the bad text. |
| 2861 | `    p->bins = f[10][0] == '1';` | `bins` becomes 1 for the text `1` and 0 for the text `0`. |
| 2862 | `    plan.n++;` | Counts the trial. |
| 2863 | `    /* The record storage is bounded here, before the process pins or` | Comment: the size of the record storage is limited here. The sentence goes on in line 2864. |
| 2864 | `     * allocates. */` | Comment: this happens before the process pins a thread or allocates the records. |
| 2865 | `    recsz.windows += (size_t)trial_windows(p);` | Adds the windows of this trial to the number of window records (`trial_windows`, line 2373). |
| 2866 | `    recsz.bins += (size_t)p->nwin * (size_t)window_bins(p);` | Adds the bins of this trial: `nwin` times `window_bins(p)` (line 2380). |
| 2867 | `    if (p->count == CS_READ)` | Tests whether the trial has the counter state `read`. |
| 2868 | `        recsz.counts += (size_t)p->nwin + 1;` | Adds the `nwin + 1` counter readings of this trial. |
| 2869 | `    recsz.trace = plan.trace ? TRACE_CAP : 0;` | With `--trace` the storage holds `TRACE_CAP` (1048576) trace events. Without `--trace` it holds none. |
| 2870 | `    recsz.bytes = (size_t)plan.n * sizeof(struct trec) + recsz.windows * sizeof(struct win) +` | `recsz.bytes`: the size of the record block for all trials up to this line: the trial records plus the window records. The sum goes on in line 2871. |
| 2871 | `                  recsz.counts * sizeof(struct counts) + recsz.bins * sizeof(struct bin) + recsz.trace * sizeof(struct tev);` | Continues the sum of line 2870: plus the counter readings, the bins and the trace events. |
| 2872 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2873 | `    recsz.bytes += plan.rec_pad;` | Adds the pad of `--rec-pad` to the size. |
| 2874 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2875 | `    if (recsz.bytes > MAX_REC_BYTES)` | Tests whether the size is above 256 MiB (`MAX_REC_BYTES`). |
| 2876 | `        plan_bad(line, "the records of the plan up to this line need %zu bytes, the bound is %lu bytes", recsz.bytes,` | Then the plan has a defect. The message gives the size that the records up to this line need, and the upper limit. |
| 2877 | `                 MAX_REC_BYTES);` | Continues the call of line 2876: the upper limit. |
| 2878 | `}` | Ends the function `plan_trial`. |

### Function `read_plan` (trial mode): read and check the whole plan (lines 2880 to 2932)

| Line | Source | Explanation |
|---:|---|---|
| 2880 | `/* Reads and checks the whole plan. Returns only if it can run. */` | Comment: the function reads and checks the whole plan. It returns only when the plan can run. |
| 2881 | `static void read_plan(void)` | Starts the function `read_plan`. It reads the plan file `plan.path` into memory, computes its checksum and checks it line by line. A defect ends the process with exit status 2. |
| 2882 | `{` | Opens the body of `read_plan`. |
| 2883 | `    size_t cap = 1 << 16, len = 0, got;` | `cap`: the size of the text buffer, 65536 bytes at the start. `len`: the number of bytes read so far. `got`: the number of bytes of one read. |
| 2884 | `    FILE *f = fopen(plan.path, "rb");` | Opens the plan file for reading. |
| 2885 | `    char *text = malloc(cap + 1);` | Allocates the text buffer, with room for one more byte at its end. |
| 2886 | `    int line = 0;` | `line`: the number of the plan line that is checked. |
| 2887 | `    if (!f \|\| !text) {` | Tests whether the file could not be opened or the buffer could not be allocated. |
| 2888 | `        fprintf(stderr, "cannot read the plan %s: %s\n", plan.path, strerror(errno));` | Prints `cannot read the plan`, the path and the reason to stderr. |
| 2889 | `        exit(2);` | Ends the process with exit status 2. |
| 2890 | `    }` | Ends the `if` of line 2887. |
| 2891 | `    while ((got = fread(text + len, 1, cap - len, f)) > 0) {` | Loop that reads the file in pieces until no byte is left. |
| 2892 | `        len += got;` | Counts the bytes of the piece. |
| 2893 | `        if (len == cap && !(text = realloc(text, (cap *= 2) + 1))) {` | When the buffer is full, `realloc` doubles its size. The test is true when that fails. |
| 2894 | `            fprintf(stderr, "no memory for the plan\n");` | Prints `no memory for the plan` to stderr. |
| 2895 | `            exit(2);` | Ends the process with exit status 2. |
| 2896 | `        }` | Ends the `if` of line 2893. |
| 2897 | `    }` | Ends the read loop (line 2891). |
| 2898 | `    if (ferror(f)) {` | Tests whether a read failed. |
| 2899 | `        fprintf(stderr, "cannot read the plan %s\n", plan.path);` | Prints `cannot read the plan` and the path to stderr. |
| 2900 | `        exit(2);` | Ends the process with exit status 2. |
| 2901 | `    }` | Ends the `if` of line 2898. |
| 2902 | `    fclose(f);` | Closes the file. |
| 2903 | `    text[len] = '\0';` | Ends the text with a zero byte. |
| 2904 | `    plan.hash = 14695981039346656037ULL; /* FNV-1a, 64 bit, over the bytes of the file */` | `plan.hash`: the start value of the FNV-1a hash, a 64-bit checksum. The comment says that it is computed over the bytes of the file. |
| 2905 | `    for (size_t i = 0; i < len; i++)` | Loop over the bytes of the file. |
| 2906 | `        plan.hash = (plan.hash ^ (uint8_t)text[i]) * 1099511628211ULL;` | One step of the hash per byte: an exclusive or with the byte, then a multiplication by the constant 1099511628211. `trial_worker` prints the result in the M row `plan_fnv1a64` (line 2640). |
| 2907 | `    if (strlen(text) != len)` | Tests whether the text ends before the end of the file. The file then holds a zero byte. |
| 2908 | `        plan_bad(0, "the file holds a zero byte");` | That is a defect of the plan. |
| 2909 | `    for (char *s = text, *next; *s; s = next) {` | Loop over the lines of the text. `s` is the start of a line. `next` is the start of the line after it. |
| 2910 | `        char *nl = strchr(s, '\n');` | `nl`: the line break at the end of the line, or NULL for a last line without one. |
| 2911 | `        next = nl ? nl + 1 : s + strlen(s);` | The next line starts after the line break. Without a line break `next` points to the end of the text, and the loop ends after this line. |
| 2912 | `        if (nl)` | Tests whether the line has a line break. |
| 2913 | `            *nl = '\0';` | Ends the line there: a zero byte replaces the line break. |
| 2914 | `        line++;` | Counts the line. |
| 2915 | `        if (line == 1) {` | Tests for the first line of the plan. |
| 2916 | `            if (strcmp(s, PLAN_LINE1))` | The first line must be the text of `PLAN_LINE1` (line 1971). |
| 2917 | `                plan_bad(1, "the line must be '%s'", PLAN_LINE1);` | If it is not: a defect of the plan. The message gives the text that is needed. |
| 2918 | `        } else if (line == 2) {` | Tests for the second line. |
| 2919 | `            plan_pairs(s);` | `plan_pairs` (line 2789) reads the second line. |
| 2920 | `        } else if (line == 3) {` | Tests for the third line. |
| 2921 | `            if (strcmp(s, PLAN_LINE3))` | The third line must be the text of `PLAN_LINE3` (line 1972): the names of the 11 fields. |
| 2922 | `                plan_bad(3, "the line must be '%s'", PLAN_LINE3);` | If it is not: a defect of the plan. The message gives the text that is needed. |
| 2923 | `        } else {` | The case of every later line. |
| 2924 | `            plan_trial(line, s);` | Every line from the fourth on is one trial. `plan_trial` (line 2819) reads it. |
| 2925 | `        }` | Ends the chain of tests that starts in line 2915. |
| 2926 | `    }` | Ends the loop over the lines (line 2909). |
| 2927 | `    if (line < 3)` | Tests whether the plan has fewer than three lines. |
| 2928 | `        plan_bad(line + 1, "the three header lines are needed");` | That is a defect: the three header lines are needed. |
| 2929 | `    if (plan.n == 0)` | Tests whether the plan has no trial. |
| 2930 | `        plan_bad(line + 1, "no trial");` | That is a defect too. The message is `no trial`. |
| 2931 | `}` | Ends the function `read_plan`. |

### Function `trial_usage` (trial mode): option summary of the trial mode, then exit status 2 (lines 2933 to 2955)

| Line | Source | Explanation |
|---:|---|---|
| 2933 | `static void trial_usage(void)` | Starts the function `trial_usage`. It prints the option summary of the trial mode to stderr and ends the process with exit status 2. |
| 2934 | `{` | Opens the body of `trial_usage`. |
| 2935 | `    fprintf(stderr,` | Starts the first `fprintf` call that writes to stderr. Its text stands in lines 2936 to 2939. |
| 2936 | `            "usage: bwx8 --trial --cpus C --bytes B --plan FILE [--ctl-cpu N] [--no-thp] [--trace]\n"` | Text of the message: the usage line with the options `--trial`, `--cpus`, `--bytes`, `--plan`, `--ctl-cpu`, `--no-thp` and `--trace`. The text names the program `bwx8`, the version of the runner that added the trial mode. |
| 2937 | `            "            [--pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options `--pmu-type` and `--events`, and the two environment variables that can give the counter settings in their place. |
| 2938 | `            "  --cpus: exactly one CPU. --ctl-cpu: CPU of the controlling thread (default 0), another CPU.\n"` | Text of the message: `--cpus` takes exactly one CPU. `--ctl-cpu` is the CPU of the controlling thread (default 0), and it must be another CPU. |
| 2939 | `            "  the counter settings are required if a trial of the plan has count open or read\n");` | Text of the message: the counter settings are required when a trial of the plan has the counter state `open` or `read`. This line ends the call. |
| 2940 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2941 | `    fprintf(stderr,` | Starts the second `fprintf` call. |
| 2942 | `            "  bwx10 adds: [--rec-pad BYTES] [--hot-copy]\n"` | Text of the message: `bwx10` adds the options `--rec-pad` and `--hot-copy`. |
| 2943 | `            "  --rec-pad: unused bytes before the window records, a multiple of %zu from 0 to 65536 (default 0)\n"` | Text of the message: `--rec-pad` gives a number of unused bytes before the window records. It must be a multiple of a value that line 2945 gives, from 0 to 65536, and its default is 0. |
| 2944 | `            "  --hot-copy: the window loop works on a local copy of its window record\n",` | Text of the message: with `--hot-copy` the window loop works on a local copy of its window record. |
| 2945 | `            _Alignof(struct win));` | The value for the text of line 2943: `_Alignof(struct win)`, the alignment in bytes that the compiler needs for a window record. This line ends the call. |
| 2946 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2947 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2948 | `    fprintf(stderr,` | Starts the third `fprintf` call. |
| 2949 | `            "  bwx11 adds: [--evict-mb N]\n"` | Text of the message: `bwx11` adds the option `--evict-mb`. |
| 2950 | `            "  --evict-mb: before the first trial the worker writes N MiB of other memory twice, a whole number\n"` | Text of the message: with `--evict-mb` the worker writes N MiB of other memory twice before the first trial. N is a whole number. The sentence goes on in line 2951. |
| 2951 | `            "              from 0 to 4096 (default 0: no such step)\n");` | Text of the message: N goes from 0 to 4096, and the default 0 means no such step. This line ends the call. |
| 2952 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2953 | `    exit(2);` | Ends the process with exit status 2. |
| 2954 | `}` | Ends the function `trial_usage`. |

### Function `trial_main` (trial mode): the arguments (lines 2956 to 3003)

| Line | Source | Explanation |
|---:|---|---|
| 2956 | `static int trial_main(int argc, char **argv)` | Starts the function `trial_main`, the entry of the trial mode. `main` calls it only when an argument is the word `--trial` (lines 3075 to 3077). |
| 2957 | `{` | Opens the body of `trial_main`. |
| 2958 | `    struct tw w;` | `w`: the state of the one worker of the trial mode (line 2044). |
| 2959 | `    pthread_t tid;` | `tid`: the handle of the worker thread. |
| 2960 | `    cpu_set_t set;` | `set`: a CPU set, for the check of line 3012. |
| 2961 | `    int bytes_given = 0, counting = 0;` | `bytes_given`: becomes 1 when `--bytes` is given. `counting`: becomes 1 when a trial of the plan wants counters. |
| 2963 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 2964 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 2965 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value needs that. |
| 2966 | `        if (!strcmp(a, "--trial")) {` | The word `--trial` itself needs no action. |
| 2967 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 2968 | `            cfg.use_thp = 0;` | `--no-thp`: the program asks Linux for no 2 MiB pages for the buffer. |
| 2969 | `        } else if (!strcmp(a, "--trace")) {` | Tests for `--trace`. |
| 2970 | `            plan.trace = 1;` | `--trace` enables the event log of the trace. |
| 2971 | `/* bwx10+ */` | Comment: marks the start of text that the version `bwx10` of the runner added. |
| 2972 | `        } else if (!strcmp(a, "--hot-copy")) {` | Tests for `--hot-copy`. |
| 2973 | `            plan.hot_copy = 1;` | `--hot-copy`: `timed_sequence_hot` runs the windows (lines 2361 to 2362). |
| 2974 | `        } else if (!strcmp(a, "--rec-pad") && more) {` | Tests for `--rec-pad` with a value after it. |
| 2975 | `            long pad = parse_long(argv[++i], "--rec-pad", 0, 65536);` | `pad`: the value in bytes, a whole number from 0 to 65536 (`parse_long`, line 384). |
| 2976 | `            if (pad % (long)_Alignof(struct win) != 0) {` | Tests whether the value is not a multiple of the alignment of a window record. |
| 2977 | `                fprintf(stderr, "bad --rec-pad: '%s' (a multiple of %zu is needed: the window records stay aligned)\n",` | Prints a message to stderr: the bad value and the multiple that is needed. The text gives the reason: the window records stay aligned. |
| 2978 | `                        argv[i], _Alignof(struct win));` | Continues the call of line 2977: the value and the alignment. |
| 2979 | `                exit(2);` | Ends the process with exit status 2. |
| 2980 | `            }` | Ends the `if` of line 2976. |
| 2981 | `            plan.rec_pad = (size_t)pad;` | Stores the pad. |
| 2982 | `/* bwx10- */` | Comment: marks the end of the text that `bwx10` added. |
| 2983 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 2984 | `        } else if (!strcmp(a, "--evict-mb") && more) {` | Tests for `--evict-mb` with a value after it. |
| 2985 | `            evict_mb = parse_long(argv[++i], "--evict-mb", 0, 4096);` | `evict_mb`: the value, a whole number from 0 to 4096 (MiB). |
| 2986 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |
| 2987 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 2988 | `            parse_cpus(argv[++i]);` | Reads the CPU list with `parse_cpus` (line 419). The check of line 3004 later demands exactly one CPU. |
| 2989 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 2990 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size, read by `parse_bytes` (line 365). |
| 2991 | `            bytes_given = 1;` | Notes that `--bytes` was given. |
| 2992 | `        } else if (!strcmp(a, "--plan") && more) {` | Tests for `--plan` with a value after it. |
| 2993 | `            plan.path = argv[++i];` | The path of the plan file. |
| 2994 | `        } else if (!strcmp(a, "--ctl-cpu") && more) {` | Tests for `--ctl-cpu` with a value after it. |
| 2995 | `            plan.ctl_cpu = (int)parse_long(argv[++i], "--ctl-cpu", 0, MAX_USE_CPU);` | The CPU of the controlling thread, a whole number from 0 to `MAX_USE_CPU`. |
| 2996 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 2997 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. |
| 2998 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 2999 | `            parse_events(argv[++i]);` | Reads the event list with `parse_events` (line 1927). |
| 3000 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 3001 | `            trial_usage();` | Prints the option summary of the trial mode and ends the process (`trial_usage`, line 2933). Options of the interval mode such as `--threads`, `--seq`, `--stop`, `--start`, `--rounds`, `--min-ms` and `--count` have no branch in this loop. So they end here too. |
| 3002 | `        }` | Ends the chain of tests that starts in line 2966. |
| 3003 | `    }` | Ends the loop over the arguments (line 2963). |

### Function `trial_main` (trial mode): checks, the plan and the start of the worker (lines 3004 to 3043)

| Line | Source | Explanation |
|---:|---|---|
| 3004 | `    if (cfg.ncpus != 1 \|\| !bytes_given \|\| !plan.path \|\| cfg.bytes % 256 != 0) {` | Tests the settings: `--cpus` names exactly one CPU, `--bytes` was given and is a multiple of 256 bytes, and `--plan` was given. |
| 3005 | `        fprintf(stderr, "--trial needs --cpus with exactly one CPU, --bytes (a multiple of 256) and --plan\n");` | If one of them fails: prints the rule to stderr. |
| 3006 | `        trial_usage();` | Then prints the option summary and ends the process with exit status 2 (`trial_usage`). |
| 3007 | `    }` | Ends the `if` of line 3004. |
| 3008 | `    if (plan.ctl_cpu == cfg.cpus[0]) {` | Tests whether the controlling thread and the worker would share one CPU. |
| 3009 | `        fprintf(stderr, "the controlling thread and the worker must not share CPU %d\n", plan.ctl_cpu);` | Prints a message with the CPU number to stderr. |
| 3010 | `        exit(2);` | Ends the process with exit status 2. |
| 3011 | `    }` | Ends the `if` of line 3008. |
| 3012 | `    if (sched_getaffinity(0, sizeof set, &set) != 0 \|\| !CPU_ISSET(cfg.cpus[0], &set) \|\| !CPU_ISSET(plan.ctl_cpu, &set)) {` | Reads the allowed CPU set of the process (`sched_getaffinity`) and tests whether the worker CPU or the CPU of the controlling thread is not in it. A failed call counts as a defect too. |
| 3013 | `        fprintf(stderr, "CPU %d or CPU %d is not in the allowed set of the process\n", cfg.cpus[0], plan.ctl_cpu);` | Prints both CPU numbers to stderr. |
| 3014 | `        exit(2);` | Ends the process with exit status 2. |
| 3015 | `    }` | Ends the `if` of line 3012. |
| 3016 | `    read_plan();` | Reads and checks the whole plan (`read_plan`, line 2881). At this point no thread is pinned and no buffer is mapped. |
| 3017 | `    for (int i = 0; i < plan.n; i++)` | Loop over the trials of the plan. |
| 3018 | `        counting \|= plan.tr[i].count != CS_CLOSED;` | `counting` becomes 1 when a trial has the counter state `open` or `read`. |
| 3019 | `    if (counting && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: a plan with counters, no `--pmu-type`, and the environment variable `BWX_PMU_TYPE` is set. |
| 3020 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 3021 | `    if (counting && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: a plan with counters, no `--events`, and the environment variable `BWX_EVENTS` is set. |
| 3022 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 3023 | `        parse_events(copy);` | Reads the event list from the copy. |
| 3024 | `        free(copy);` | Frees the copy. |
| 3025 | `    }` | Ends the `if` of line 3021. |
| 3026 | `    if (counting && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether a plan with counters still has no PMU type or no event. |
| 3027 | `        fprintf(stderr, "the plan has a trial with count open or read: --pmu-type and --events are needed "` | Prints a message to stderr: the plan has a trial with the counter state `open` or `read`, and `--pmu-type` and `--events` are needed. |
| 3028 | `                        "(or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Continues the text of line 3027: or the two environment variables. |
| 3029 | `        exit(2);` | Ends the process with exit status 2. |
| 3030 | `    }` | Ends the `if` of line 3026. |
| 3032 | `    /* The plan can run. The controlling thread pins itself, starts the` | Comment: the plan can run. The controlling thread pins itself and starts the worker. The sentence goes on in line 3033. |
| 3033 | `     * worker and waits. It never touches the buffer. */` | Comment: then the controlling thread waits. It never touches the buffer. |
| 3034 | `    pin_cpu(plan.ctl_cpu);` | The controlling thread pins itself to the CPU of `--ctl-cpu` (`pin_cpu`, line 446). |
| 3035 | `    memset(&w, 0, sizeof w);` | Sets every field of the worker state to 0. |
| 3036 | `    if (pthread_create(&tid, NULL, trial_worker, &w) != 0) {` | Starts the one worker thread. It runs `trial_worker` (line 2605). |
| 3037 | `        perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 3038 | `        return 2;` | `trial_main` then returns 2, which becomes the exit status of the process (line 3077). |
| 3039 | `    }` | Ends the `if` of line 3036. |
| 3040 | `    pthread_join(tid, NULL);` | Waits for the end of the worker thread (`pthread_join`). |
| 3041 | `    return 0;` | Returns 0, which becomes the exit status of the process (line 3077). |
| 3042 | `}` | Ends the function `trial_main`. |

### The include of the self-test file (lines 3044 to 3066)

| Line | Source | Explanation |
|---:|---|---|
| 3044 | `/* bwx11+ */` | Comment: marks the start of text that the version `bwx11` of the runner added. |
| 3045 | `#if 0` | `#if 0`: the compiler skips the text from here to the `#endif` of line 3049. |
| 3046 | `/* bwx11- */` | Comment: marks the end of a piece of text that `bwx11` added. |
| 3047 | `#include "bwx10_selftest.c"` | The include line of the self-test file of the version `bwx10`. It stands between the `#if 0` of line 3045 and the `#endif` of line 3049. So the compiler skips it. |
| 3048 | `/* bwx11+ */` | Comment: marks the start of more text that `bwx11` added. |
| 3049 | `#endif` | Ends the `#if 0` of line 3045. |
| 3050 | `/* bwx12+ */` | Comment: marks the start of text that the version `bwx12` of the runner added. |
| 3051 | `#if 0` | `#if 0`: the compiler skips the text from here to the `#endif` of line 3055. |
| 3052 | `/* bwx12- */` | Comment: marks the end of a piece of text that `bwx12` added. |
| 3053 | `#include "bwx11_selftest.c"` | The include line of the self-test file of the version `bwx11`. It stands between the `#if 0` of line 3051 and the `#endif` of line 3055. So the compiler skips it too. |
| 3054 | `/* bwx12+ */` | Comment: marks the start of more text that `bwx12` added. |
| 3055 | `#endif` | Ends the `#if 0` of line 3051. |
| 3056 | `/* bwx13+ */` | Comment: marks the start of text that the version `bwx13` of the runner added. |
| 3057 | `#if 0` | `#if 0`: the compiler skips the text from here to the `#endif` of line 3061. |
| 3058 | `/* bwx13- */` | Comment: marks the end of a piece of text that `bwx13` added. |
| 3059 | `#include "bwx12_selftest.c"` | The include line of the self-test file of the version `bwx12`. It stands between the `#if 0` of line 3057 and the `#endif` of line 3061. So the compiler skips it too. |
| 3060 | `/* bwx13+ */` | Comment: marks the start of more text that `bwx13` added. |
| 3061 | `#endif` | Ends the `#if 0` of line 3057. |
| 3062 | `#include "bwx13_selftest.c"` | Includes the file `bwx13_selftest.c`. It defines the function `selftest`. `main` calls that function only for the option `--selftest` (line 3083). |
| 3063 | `/* bwx13- */` | Comment: marks the end of the text that `bwx13` added. |
| 3064 | `/* bwx12- */` | Comment: marks the end of the text that `bwx12` added. |
| 3065 | `/* bwx11- */` | Comment: marks the end of the text that `bwx11` added. |

### Function `main`: the start of the program (lines 3067 to 3074)

| Line | Source | Explanation |
|---:|---|---|
| 3067 | `int main(int argc, char **argv)` | Starts the function `main`, the entry point of the program. It reads the arguments, starts the workers, sets the common start of each interval and prints all rows. |
| 3068 | `{` | Opens the body of `main`. |
| 3069 | `    int threads_given = 0;` | `threads_given`: becomes 1 when `--threads` is given (line 3096). The check of line 3132 uses it. |
| 3070 | `    char seq_text[1024] = "";` | `seq_text`: will hold a copy of the `--seq` text for the second header line of the output (line 3186). It has room for 1023 characters. |
| 3071 | `    t_base_ns = now_ns();` | Process start time: one reading of the Linux clock `CLOCK_MONOTONIC` through `now_ns` (line 358), in ns. The T rows print the common start, `t0` and `t1` of each thread as seconds after this time (lines 3246 to 3247). |
| 3072 | `    page_bytes = sysconf(_SC_PAGESIZE);` | `page_bytes`: the size of one small memory page in bytes, as Linux reports it (`sysconf`). `alloc_buf` (line 465) uses it when it places a buffer inside its mapping. |
| 3073 | `    cfg.bytes = 1UL << 20;` | `cfg.bytes` gets its default here: 1 MiB (1048576 bytes). The option `--bytes` replaces it (line 3100). |
| 3074 | `    restrict_cpus();` | `restrict_cpus` (line 399) removes every CPU above `MAX_USE_CPU` from the allowed CPU set of the process. `MAX_USE_CPU` is 119 unless the build sets another value (line 170). The build of `bwx13` on CRB set no other value [Ref2]. |

### Function `main`: the choice between the trial mode and the interval mode (lines 3075 to 3078)

| Line | Source | Explanation |
|---:|---|---|
| 3075 | `    for (int i = 1; i < argc; i++)` | Mode choice. The loop compares every argument with the word `--trial`. |
| 3076 | `        if (!strcmp(argv[i], "--trial"))` | Tests whether one argument is the word `--trial`. |
| 3077 | `            return trial_main(argc, argv);` | When an argument is `--trial`, `main` returns the result of `trial_main` (line 2956), and no line below runs. This is the only call of `trial_main` in the file. |

### Function `main`: reading the arguments (lines 3079 to 3131)

| Line | Source | Explanation |
|---:|---|---|
| 3079 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 3080 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 3081 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value is accepted only when `more` is 1, and `argv[++i]` then takes the value. |
| 3082 | `        if (!strcmp(a, "--selftest")) {` | Tests for `--selftest`. |
| 3083 | `            return selftest();` | `--selftest` runs the self-test (the function `selftest` of the included self-test file) and ends the program with its result. |
| 3084 | `        } else if (!strcmp(a, "--list")) {` | Tests for `--list`. |
| 3085 | `            for (int k = 0; k < K_COUNT; k++)` | Loop over the kernel table. |
| 3086 | `                printf("%s\n", kernels[k].name);` | `--list` prints the name of every kernel of the table, one per line. |
| 3087 | `            return 0;` | Then the program ends with exit status 0. |
| 3088 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 3089 | `            cfg.use_thp = 0;` | `--no-thp` sets `cfg.use_thp` to 0. Then `alloc_buf` asks Linux for no 2 MiB pages. |
| 3090 | `        } else if (!strcmp(a, "--two-buffers")) {` | Tests for `--two-buffers`. |
| 3091 | `            cfg.two_buffers = 1;` | `--two-buffers` sets `cfg.two_buffers` to 1. Then every thread gets a second buffer `b`, also without a copy kernel (line 1803). |
| 3092 | `        } else if (!strcmp(a, "--count")) {` | Tests for `--count`. |
| 3093 | `            cfg.count = 1;` | `--count` sets `cfg.count` to 1. Then each worker opens its counter group and reads it before and after every timed interval. `main` prints the C rows from these readings. |
| 3094 | `        } else if (!strcmp(a, "--threads") && more) {` | Tests for `--threads` with a value after it. |
| 3095 | `            cfg.threads = (int)parse_long(argv[++i], "--threads", 1, 4096);` | The number of worker threads. `parse_long` (line 384) accepts a whole number from 1 to 4096. |
| 3096 | `            threads_given = 1;` | Notes that `--threads` was given. |
| 3097 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 3098 | `            parse_cpus(argv[++i]);` | `parse_cpus` (line 419) appends the CPUs of each range of the list to `cfg.cpus`, in the order of the text. `cfg.ncpus` counts them. |
| 3099 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 3100 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size of each thread, read by `parse_bytes` (line 365). That function reads the letter `M` as 2 to the power 20. |
| 3101 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Tests for `--min-ms` with a value after it. |
| 3102 | `            char *end;` | `end`: will point to the first character that `strtod` did not read. |
| 3103 | `            double ms = strtod(argv[++i], &end);` | `strtod` reads the value as a decimal number of milliseconds. A fraction is allowed. |
| 3104 | `            if (end == argv[i] \|\| *end != '\0' \|\| !(ms > 0) \|\| ms > 3.6e6) {` | Tests for a bad value: no number, other text after the number, a value that is not above 0, or a value above 3.6e6 ms (1 hour). |
| 3105 | `                fprintf(stderr, "bad --min-ms: '%s' (a number of milliseconds above 0 is needed)\n", argv[i]);` | Prints a message with the bad value to stderr. |
| 3106 | `                exit(2);` | Ends the program with exit status 2. |
| 3107 | `            }` | Ends the `if` of line 3104. |
| 3108 | `            cfg.min_s = ms / 1000.0;` | `cfg.min_s`: the value in seconds. With `--stop common` it is the time from the common start to the deadline (line 3224). With `--stop pass` it is the least duration of an interval (line 1871). |
| 3109 | `        } else if (!strcmp(a, "--rounds") && more) {` | Tests for `--rounds` with a value after it. |
| 3110 | `            cfg.rounds = (int)parse_long(argv[++i], "--rounds", 1, 1000000);` | The number of rounds, a whole number from 1 to 1000000. The program runs the `--seq` list that many times. |
| 3111 | `        } else if (!strcmp(a, "--seq") && more) {` | Tests for `--seq` with a value after it. |
| 3112 | `            snprintf(seq_text, sizeof seq_text, "%s", argv[++i]);` | Copies the text of the list to `seq_text`, for the second header line (line 3186). The copy is made first: `parse_seq` changes the argument text. |
| 3113 | `            parse_seq(argv[i]);` | `parse_seq` (line 1906) cuts the argument text itself at each comma. It looks up each name in the kernel table and appends its index to `cfg.seq`. An unknown name ends the program. `cfg.nseq` counts the entries. An entry without an `@SIZE` part keeps the size 0 until line 3153. |
| 3114 | `        } else if (!strcmp(a, "--stop") && more) {` | Tests for `--stop` with a value after it. |
| 3115 | `            const char *s = argv[++i];` | `s`: the value. |
| 3116 | `            if (strcmp(s, "pass") && strcmp(s, "common"))` | Tests whether the value is neither `pass` nor `common`. |
| 3117 | `                usage();` | Any other value prints the option summary and ends the program (`usage`, line 1893). |
| 3118 | `            cfg.stop_common = !strcmp(s, "common");` | `cfg.stop_common` becomes 1 for `common` and 0 for `pass`. With 1 all threads get one common start time and one common deadline for each interval (lines 3221 to 3226). |
| 3119 | `        } else if (!strcmp(a, "--start") && more) {` | Tests for `--start` with a value after it. |
| 3120 | `            const char *s = argv[++i];` | `s`: the value. |
| 3121 | `            if (strcmp(s, "common") && strcmp(s, "offset"))` | Tests whether the value is neither `common` nor `offset`. |
| 3122 | `                usage();` | Any other value prints the option summary and ends the program (`usage`). |
| 3123 | `            cfg.start_offset = !strcmp(s, "offset");` | `cfg.start_offset` becomes 1 for `offset` and 0 for `common`. With 0 every worker starts its timed work at byte 0 of its own buffer (line 1818). |
| 3124 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 3125 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. It goes into the field `type` of the structure `perf_event_attr` (line 1745). |
| 3126 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 3127 | `            parse_events(argv[++i]);` | `parse_events` (line 1927) stores the names in `cfg.ev_name` and the codes in `cfg.ev_code`. `cfg.nev` becomes the number of events. `main` does not interpret the codes. Each worker passes them to Linux in `open_counters` (line 1738). |
| 3128 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 3129 | `            usage();` | `usage` (line 1893) prints the option summary to stderr and ends the process with exit status 2. |
| 3130 | `        }` | Ends the chain of tests that starts in line 3082. |
| 3131 | `    }` | Ends the loop over the arguments (line 3079). |

### Function `main`: checks of the settings (lines 3132 to 3164)

| Line | Source | Explanation |
|---:|---|---|
| 3132 | `    if (threads_given && cfg.ncpus == 0) {` | Check: `--threads` is accepted only together with `--cpus`. The test is true when `--threads` was given and the CPU list is empty. |
| 3133 | `        fprintf(stderr, "--threads requires --cpus\n");` | Prints `--threads requires --cpus` to stderr. |
| 3134 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 3135 | `    }` | Ends the `if` of line 3132. |
| 3136 | `    if (cfg.threads < 1 \|\| cfg.rounds < 1 \|\| cfg.nseq < 1 \|\| cfg.bytes == 0 \|\| cfg.bytes % 256 != 0)` | Checks of the values: the thread count, the round count and the number of `--seq` entries are at least 1, and `--bytes` is above 0 and a multiple of 256 bytes. |
| 3137 | `        usage();` | A failed check prints the option summary and ends the program with exit status 2 (`usage`). |
| 3138 | `    /* run_bwx.sh passes the counter settings in the environment */` | Comment: the script `run_bwx.sh`, the run script of the first runner, passes the counter settings in the environment. |
| 3139 | `    if (cfg.count && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: with `--count`, without `--pmu-type`, and when the environment variable `BWX_PMU_TYPE` is set. |
| 3140 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 3141 | `    if (cfg.count && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: with `--count`, without `--events`, and when the environment variable `BWX_EVENTS` is set. |
| 3142 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 3143 | `        parse_events(copy);` | Reads the event list from the copy. |
| 3144 | `        free(copy);` | Frees the copy. |
| 3145 | `    }` | Ends the `if` of line 3141. |
| 3146 | `    if (cfg.count && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether `--count` is given and the PMU type or the events are still missing. |
| 3147 | `        fprintf(stderr, "--count requires --pmu-type and --events (or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Prints a message to stderr: `--count` requires `--pmu-type` and `--events`, or the two environment variables. |
| 3148 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 3149 | `    }` | Ends the `if` of line 3146. |
| 3150 | `    for (int s = 0; s < cfg.nseq; s++) {` | Loop over the `--seq` entries. |
| 3151 | `        struct entry *e = &cfg.seq[s];` | `e`: one entry. |
| 3152 | `        if (e->bytes == 0)` | Tests whether the entry has no size of its own (no `@SIZE` part). |
| 3153 | `            e->bytes = cfg.bytes;` | Such an entry gets the size of `--bytes`. |
| 3154 | `        if (e->bytes > cfg.bytes \|\| e->bytes % 256 != 0 \|\|` | Size check of an entry. The size must be at most `--bytes` and a multiple of 256 bytes. The check goes on in line 3155. |
| 3155 | `            (cfg.stop_common && e->bytes > CHUNK_BYTES && e->bytes % CHUNK_BYTES != 0)) {` | With `--stop common` a size above 2 MiB (`CHUNK_BYTES`) must also be a multiple of 2 MiB. With this stop rule the worker calls the kernel on chunks of 2 MiB (line 1849). A size of 256 MiB passes: 268435456 bytes is 128 times 2 MiB. |
| 3156 | `            fprintf(stderr, "bad size of --seq entry %d (%s): %lu\n", s, kernels[e->k].name, (unsigned long)e->bytes);` | A bad size prints a message to stderr: the number of the entry, the kernel name and the size. |
| 3157 | `            usage();` | Then the option summary is printed, and the program ends with exit status 2 (`usage`). |
| 3158 | `        }` | Ends the `if` of line 3154. |
| 3159 | `        if (kernels[e->k].type == T_COPY)` | Tests whether the kernel of the entry is a copy kernel (type `T_COPY`). |
| 3160 | `            cfg.two_buffers = 1;` | A copy kernel in the list sets `cfg.two_buffers` to 1. Then each thread gets a second buffer `b` (line 1803). |
| 3161 | `    }` | Ends the loop over the entries (line 3150). |
| 3162 | `    if (cfg.ncpus && cfg.threads > cfg.ncpus)` | Tests whether a CPU list was given and has fewer CPUs than the process has threads. |
| 3163 | `        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);` | This only gives a warning on stderr, with both numbers. The CPU list is then used again from its start (line 3174). |

### Function `main`: thread records, barrier and start of the workers (lines 3165 to 3180)

| Line | Source | Explanation |
|---:|---|---|
| 3165 | `    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);` | `th`: one record per thread, filled with zeros by `calloc`. |
| 3166 | `    uint64_t **bufs = calloc((size_t)cfg.threads * 2, sizeof *bufs);` | `bufs`: two buffer addresses per thread, for buffer `a` and buffer `b`, filled with zeros. |
| 3167 | `    struct page *pg = calloc((size_t)cfg.threads * 2, sizeof *pg);` | `pg`: one page-state record per entry of `bufs`. |
| 3168 | `    if (!th \|\| !bufs \|\| !pg \|\| pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {` | Tests the three allocations and creates the barrier `bar` for the thread count plus 1: the workers and the main thread. |
| 3169 | `        perror("setup");` | On a failure: `perror` prints the word `setup` and the reason. |
| 3170 | `        return 2;` | On a failure: the program ends with exit status 2. |
| 3171 | `    }` | Ends the `if` of line 3168. |
| 3172 | `    for (int i = 0; i < cfg.threads; i++) {` | Loop that starts the workers. |
| 3173 | `        th[i].idx = i;` | Thread `i` gets the index `i`. |
| 3174 | `        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;` | Thread placement. Thread `i` gets the CPU `cfg.cpus[i % cfg.ncpus]`: entry `i` of the CPU list. The list is used again from its start when there are more threads than entries. Without a CPU list the value is -1, and the thread is not pinned (line 1797). |
| 3175 | `        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {` | Creates the thread. It runs `worker` (line 1788): it pins itself, opens its counters, maps its buffer and writes it. `main` does not wait for that here. It goes on with the header lines. The function `main` does not pin the main thread. So the main thread may run on any CPU of the allowed CPU set of the process. |
| 3176 | `            perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 3177 | `            return 2;` | The program then ends with exit status 2. |
| 3178 | `        }` | Ends the `if` of line 3175. |
| 3179 | `    }` | Ends the loop of line 3172. |

### Function `main`: the header lines of the csv file (lines 3181 to 3201)

| Line | Source | Explanation |
|---:|---|---|
| 3181 | `    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "` | Starts the `printf` call of the first header line. The line starts with `# bandwidth:`. It gives the meaning of GB (1e9 bytes) and the formula of the rate of the I rows: `aggregate_GBps` is the sum of the bytes of all threads divided by the longest elapsed time of one thread. |
| 3182 | `           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",` | Continues the text of the first header line: a copy kernel counts the bytes read plus the bytes written. Then come four settings: the thread count, the bytes per thread, `min_ms` and `thp`. |
| 3183 | `           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");` | The four values. `min_ms` is `cfg.min_s` times 1000, printed without decimals. `thp` is `madvise` when the program asks for 2 MiB pages, and `nohugepage` with `--no-thp`. It only says what the program asked for. The P rows show what the buffers got. |
| 3184 | `    printf("# bwx: seq=%s rounds=%d stop=%s start=%s two_buffers=%d count=%d kernels=%s; "` | Starts the `printf` call of the second header line. The line starts with `# bwx:`. It holds the `--seq` text, the rounds, the stop rule, the start rule, `two_buffers`, `count` and the build kind (`kernels=`). |
| 3185 | `           "round and pos count from 0; times are seconds since process start\n",` | Continues the text of the second header line: round and position count from 0, and the times are seconds after the process start. |
| 3186 | `           seq_text, cfg.rounds, cfg.stop_common ? "common" : "pass", cfg.start_offset ? "offset" : "common",` | The values: the `--seq` text, the number of rounds, `common` or `pass` for the stop rule, and `offset` or `common` for the start rule. |
| 3187 | `           cfg.two_buffers, cfg.count, STANDIN ? "STAND-IN (not AArch64: rates mean nothing)" : "aarch64");` | The values of `two_buffers`, `count` and the build kind. `STANDIN` is 0 in the AArch64 build (line 523), and the build kind is then `aarch64`. A build with stand-in kernels prints a text that starts with `STAND-IN` and says that the rates mean nothing. |
| 3188 | `    printf("# I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps\n"` | Starts the `printf` call of the third, fourth and fifth header line. This line holds the column names of the I rows (line 3240). |
| 3189 | `           "# T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags\n"` | The fourth header line: the column names of the T rows (line 3244). |
| 3190 | `           "# P,round,pos,tid,buffer,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n");` | The fifth header line: the column names of the P rows. `print_p` (line 1726) prints these rows. |
| 3191 | `    if (cfg.count) {` | Tests whether counting is on (`--count`). Only then the header has a sixth line. |
| 3192 | `        printf("# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns");` | Starts the sixth header line: the first nine column names of the C rows, up to `cputime_ns`. |
| 3193 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 3194 | `            printf(",%s", cfg.ev_name[e]);` | Appends the event names in the order of `--events`, one column per event. |
| 3195 | `        printf("; pmu_type=%ld codes=", cfg.pmu_type);` | Appends the PMU type (`pmu_type=`) and the word `codes=`. |
| 3196 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 3197 | `            printf("%s0x%llx", e ? "," : "", (unsigned long long)cfg.ev_code[e]);` | Appends the event codes in hexadecimal, with commas between them. |
| 3198 | `        printf("\n");` | Ends the header line with a line break. |
| 3199 | `    }` | Ends the `if` of line 3191. |
| 3200 | `    fflush(stdout);` | `fflush` writes the header lines to the standard output now. |

### Function `main`: the loop over rounds and positions, and the common start (lines 3202 to 3228)

| Line | Source | Explanation |
|---:|---|---|
| 3202 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds, as in `worker` (line 1812). |
| 3203 | `        for (int pos = -1; pos < cfg.nseq; pos++) {` | Loop over the positions. `pos` starts at -1, not at 0. Position -1 is one extra pass of the loop before the first interval. Each position from 0 up is one timed interval. `main` and the workers go through the same rounds and positions. At each barrier call below a thread waits until all workers and `main` have arrived. |
| 3204 | `            if (pos < 0 && (round > 0 \|\| cfg.threads == 1))` | Tests whether the pass with position -1 must be skipped: in every round after round 0, and in a process with one thread. |
| 3205 | `                continue;` | Skips that pass. So in a process with more than one thread it runs once, before the first interval. |
| 3206 | `            if (pos < 0) {` | The case of position -1. |
| 3207 | `                /* the workers have allocated and first touched their buffers */` | Comment: at this point the workers have allocated their buffers and have written them for the first time. |
| 3208 | `                pthread_barrier_wait(&bar);` | `main` calls the barrier. The call returns when all workers have mapped and written their buffers and wait in line 1808. |
| 3209 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 3210 | `                    bufs[2 * i] = th[i].a;` | Copies the address of buffer `a` of thread `i` into entry `2 * i` of `bufs`. |
| 3211 | `                    bufs[2 * i + 1] = th[i].b;` | Copies the address of buffer `b` of thread `i` into entry `2 * i + 1`. The entry stays NULL when the thread has no second buffer. |
| 3212 | `                }` | Ends the loop of line 3209. This pass of the position loop goes on with the page-state block in line 3268. That block prints the page state before the first interval. |
| 3213 | `            } else {` | The case of a position from 0 up: one interval. |
| 3214 | `                const struct entry *e = &cfg.seq[pos];` | `e`: the `--seq` entry of this position. |
| 3215 | `                const char *name = kernels[e->k].name;` | `name`: the name of its kernel. |
| 3216 | `                double per_pass = (double)e->bytes * (kernels[e->k].type == T_COPY ? 2 : 1);` | `per_pass`: the byte count of one pass over the range of the entry: its size, or twice its size for a copy kernel. The column `passes` of the T rows uses it (line 3247). |
| 3217 | `                uint64_t total = 0;` | `total`: the sum of the byte counts of all threads. It starts at 0. |
| 3218 | `                int64_t max_el = 0;` | `max_el`: the longest elapsed time of one thread, in ns. It starts at 0. |
| 3220 | `                pthread_barrier_wait(&bar); /* release the workers */` | First barrier call of the interval. It returns when all workers have finished the warm-up pass of this kernel and wait in line 1831. The barrier then lets all of these threads continue. With `--stop common` the workers do not start the kernel yet: each worker waits in an empty loop until `gen` changes (line 1833). The comment says: release the workers. |
| 3221 | `                if (cfg.stop_common) {` | Tests for `--stop common`. Only then `main` sets a common start (lines 3222 to 3225). With `--stop pass` each worker starts its timed interval directly after the barrier. |
| 3222 | `                    int64_t sched = now_ns() + LEAD_NS;` | Common start, set by the main thread. `main` reads the clock once and adds `LEAD_NS` (2 ms, line 163). The result `sched` is the common start time of all threads. `main` is not pinned. |
| 3223 | `                    atomic_store(&t_sched_ns, sched);` | Stores `sched` in the shared variable `t_sched_ns`. The lead of 2 ms is the time that `main` has for lines 3223 to 3225 and that the workers have to see the new `gen`. A worker that sees it only after `sched` has passed starts after the common start time. When its `t0` is then more than 100 us after `sched`, the late flag shows it (line 1881). |
| 3224 | `                    atomic_store(&deadline_ns, sched + (int64_t)(cfg.min_s * 1e9));` | Stores the deadline in the shared variable `deadline_ns`: `sched` plus `cfg.min_s`. |
| 3225 | `                    atomic_fetch_add(&gen, 1);` | Only after both stores `main` adds 1 to `gen`. So a worker that sees the new `gen` reads the new start time and the new deadline. Each worker then reads the clock in a loop until `sched`, and then reads its own start time `t0` (lines 1837 to 1844). After this line `main` passes nothing more to the workers. Each worker stops by itself, at its first clock read at or after the deadline (lines 1856 to 1857). |
| 3226 | `                }` | Ends the `if` of line 3221. |
| 3227 | `                pthread_barrier_wait(&bar); /* all workers finished this interval */` | Second barrier call of the interval. `main` blocks here until all workers have stored their results and wait in line 1883. So between the change of `gen` and the end of the timed interval this call is the only code that `main` runs. It prints nothing in that time. The comment says: all workers finished this interval. |

### Function `main`: the I row, the T rows and the C rows (lines 3229 to 3267)

| Line | Source | Explanation |
|---:|---|---|
| 3229 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the results of the threads. In a process with more than one thread every worker waits at the barrier of line 1887 from here to line 3277. So no kernel runs while `main` prints the I, T and C rows. |
| 3230 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i` for this interval (line 1882). |
| 3231 | `                    total += r->bytes;` | `total` becomes the sum of the byte counts of all threads. |
| 3232 | `                    if (r->t_end - r->t_start > max_el)` | Tests whether the elapsed time of this thread, `t_end - t_start` in ns, is the longest so far. `t_start` is the `t0` of the worker, and `t_end` is its last `t1` (lines 1878 to 1879). |
| 3233 | `                        max_el = r->t_end - r->t_start;` | Keeps the longest elapsed time in `max_el`. |
| 3234 | `                }` | Ends the loop of line 3229. |
| 3235 | `                if (cfg.threads == 1) { /* read by the worker before the interval */` | The branch of a process with one thread. There the worker has read the page state itself before the interval (lines 1826 to 1830), and `main` prints it here. The comment says: read by the worker before the interval. |
| 3236 | `                    print_p(round, pos, 0, 'a', &th[0].res.pg[0], th[0].res.vm);` | Prints the P row of buffer `a` (`print_p`, line 1726). |
| 3237 | `                    if (th[0].b)` | Tests whether the thread has a second buffer. |
| 3238 | `                        print_p(round, pos, 0, 'b', &th[0].res.pg[1], th[0].res.vm);` | Prints the P row of buffer `b`. It holds the same four counter values as the row of buffer `a`. |
| 3239 | `                }` | Ends the `if` of line 3235. |
| 3240 | `                printf("I,%d,%d,%s,%lu,%d,%lu,%.6f,%.2f\n", round, pos, name, (unsigned long)e->bytes, cfg.threads,` | I row, one per interval, with 9 fields: the letter `I`, round, position, kernel name, `bytes_per_thread`, thread count, `total_bytes`, `max_elapsed_s` and `aggregate_GBps`. `bytes_per_thread` is the size of the `--seq` entry. It is a setting, not a measured value. |
| 3241 | `                       (unsigned long)total, (double)max_el * 1e-9, (double)total / (double)max_el);` | Continues the call of line 3240. `total_bytes` is `total`. `max_elapsed_s` is `max_el` in seconds, with 6 decimals. `aggregate_GBps` is `total` in bytes divided by `max_el` in ns, with 2 decimals. One byte per ns is 1 GB/s with GB = 1e9 bytes. So this rate is the bytes of all threads divided by the longest elapsed time of one thread. |
| 3242 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 3243 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 3244 | `                    printf("T,%d,%d,%s,%d,%d,%lu,%.6f,%.6f,%.6f,%.6f,%.3f,%s\n", round, pos, name, i, th[i].cpu,` | T row, one per thread and interval, with 13 fields. Fields 1 to 6: the letter `T`, round, position, kernel name, thread index (`tid`) and the CPU of the thread. A thread without a CPU list shows -1. |
| 3245 | `                           (unsigned long)r->bytes, (double)(r->t_end - r->t_start) * 1e-9,` | Continues the call of line 3244. Field 7, `bytes`: the byte count of the worker (line 1852, line 1868). Field 8, `elapsed_s`: `t_end - t_start` in seconds, with 6 decimals. The rate of a thread is field 7 divided by field 8, in bytes per second. The program does not print it. |
| 3246 | `                           (double)(r->t_sched - t_base_ns) * 1e-9, (double)(r->t_start - t_base_ns) * 1e-9,` | Continues the call of line 3244. Fields 9 and 10, `t_sched_s` and `t_start_s`: the common start time and `t0`, in seconds after the process start `t_base_ns`, with 6 decimals. With `--stop pass` field 9 equals field 10 (line 1880). |
| 3247 | `                           (double)(r->t_end - t_base_ns) * 1e-9, (double)r->bytes / per_pass, r->late ? "late" : "-");` | Continues the call of line 3244. Field 11, `t_end_s`: the last `t1`, in seconds after the process start. Field 12, `passes`: `bytes / per_pass`, the number of passes over the range of the entry, with 3 decimals. Field 13, `flags`: `late` when `t0` came more than 100 us after the common start (line 1881), and `-` if not. |
| 3248 | `                }` | Ends the loop of line 3242. |
| 3249 | `                for (int i = 0; cfg.count && i < cfg.threads; i++) {` | Loop over the threads. It runs only with `--count`. It prints the C rows: one per thread and interval. |
| 3250 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 3251 | `                    printf("C,%d,%d,%s,%d,%d", round, pos, name, i, th[i].cpu);` | Starts a C row. Fields 1 to 6: the letter `C`, round, position, kernel name, thread index and CPU. |
| 3252 | `                    if (th[i].group_fd < 0)` | Tests whether the thread has no open counter group. |
| 3253 | `                        printf(",NA,NA");` | Fields 7 and 8 are then `NA`. |
| 3254 | `                    else` | The case of a thread with an open group. |
| 3255 | `                        printf(",%llu,%llu", (unsigned long long)(r->c1.enabled - r->c0.enabled),` | Fields 7 and 8, `enabled_ns` and `running_ns`: the enabled time and the running time of the counter group at the second reading minus the same values at the first reading. This line holds the enabled time. |
| 3256 | `                               (unsigned long long)(r->c1.running - r->c0.running));` | Continues the call of line 3255: the running time. |
| 3257 | `                    printf(",%llu", (unsigned long long)(r->c1.cpu_ns - r->c0.cpu_ns));` | Field 9, `cputime_ns`: the thread CPU time at the second reading minus the value at the first reading. The worker takes the first reading (`c0`) directly before `t0` and the second reading (`c1`) directly after its last `t1` (lines 1840 to 1843, lines 1873 to 1876). |
| 3258 | `                    for (int ev = 0; ev < cfg.nev; ev++) {` | Loop over the events, in the order of `--events`. |
| 3259 | `                        int at = th[i].ev_pos[ev];` | `at`: the place of the event in a group reading. It is -1 when the event did not open (line 1756). |
| 3260 | `                        if (at < 0)` | Tests whether the event did not open. |
| 3261 | `                            printf(",NA");` | Its field is then `NA`. |
| 3262 | `                        else` | The case of an event that opened. |
| 3263 | `                            printf(",%llu", (unsigned long long)(r->c1.val[at] - r->c0.val[at]));` | One field per event: the count at the second reading minus the count at the first reading. |
| 3264 | `                    }` | Ends the loop over the events (line 3258). |
| 3265 | `                    printf("\n");` | Ends the row with a line break. |
| 3266 | `                }` | Ends the loop of line 3249. |
| 3267 | `            }` | Ends the `else` of line 3213. |

### Function `main`: the page state, the P rows and the end (lines 3268 to 3289)

| Line | Source | Explanation |
|---:|---|---|
| 3268 | `            if (cfg.threads > 1) {` | Page-state block. It runs only in a process with more than one thread: once at position -1 and once after every interval. At this time every worker waits at a barrier: in line 1809 after position -1, in line 1887 after an interval. So no kernel runs while `main` reads the page state. |
| 3269 | `                /* Page state of all buffers, read between two intervals. It is` | Comment: the page state of all buffers is read between two intervals. The sentence goes on in line 3270. |
| 3270 | `                 * the state after interval pos (pos -1: before the first). The` | Comment: it is the state after interval `pos`. For `pos` -1 it is the state before the first interval. The sentence about the workers starts here. |
| 3271 | `                 * workers wait on the barrier below until it is read. */` | Comment: the workers wait at the barrier below (line 3277) until the state is read. |
| 3272 | `                long long vm[4];` | `vm`: will hold the four counters of `/proc/vmstat`. |
| 3273 | `                int64_t r0 = now_ns();` | `r0`: the clock value before the reading (`now_ns`, line 358). |
| 3274 | `                read_smaps(pg, bufs, 2 * cfg.threads);` | `read_smaps` (line 1671) looks up each entry of `bufs` in `/proc/self/smaps` and skips the NULL entries. It stores the size of each buffer and its part on 2 MiB pages in `pg`. |
| 3275 | `                read_vmstat(vm);` | `read_vmstat` (line 1701) reads the four counters of `/proc/vmstat`, once for the whole block. |
| 3276 | `                double ms = (double)(now_ns() - r0) * 1e-6;` | `ms`: the duration of both readings in ms: the clock value now minus `r0`. |
| 3277 | `                pthread_barrier_wait(&bar); /* the reading is done: the workers go on */` | Barrier call that lets the workers continue. Each worker then starts the warm-up pass of the next interval, while `main` prints the P rows below. After the last interval the workers end at this point. The comment says: the reading is done, and the workers go on. |
| 3278 | `                for (int i = 0; i < 2 * cfg.threads; i++)` | Loop over the entries of `bufs`. Entry `i` belongs to thread `i / 2`. An even `i` is buffer `a`, and an odd `i` is buffer `b`. |
| 3279 | `                    if (bufs[i])` | Skips an entry without a buffer. |
| 3280 | `                        print_p(round, pos, i / 2, i % 2 ? 'b' : 'a', &pg[i], vm);` | P row, one per existing buffer, printed by `print_p` (line 1726). The fields: the letter `P`, round, position, thread index, buffer letter, size of the buffer in kB, part on 2 MiB pages in kB, then the four counters of `/proc/vmstat`. The position is that of the interval before the reading, or -1 for the reading before the first interval. All rows of one block carry the same four counter values: they count for the whole system and were read once (line 3275). |
| 3281 | `                printf("# page_read,%d,%d,%.3f ms\n", round, pos, ms);` | Prints the line `# page_read` with the round, the position and `ms`, the duration of the page-state reading of this block, with 3 decimals and the unit `ms`. |
| 3282 | `            }` | Ends the `if` of line 3268. |
| 3283 | `            fflush(stdout);` | `fflush` writes all rows that are still in the output buffer to the standard output. Then the loops go on with the next position. A new timed interval cannot start before `main` has passed line 3220 again, and with `--stop common` also line 3225. So `main` writes no output during a timed interval. |
| 3284 | `        }` | Ends the loop over the positions (line 3203). Between two intervals lie the output of the rows, the page-state reading, the barrier calls, the warm-up pass of the next kernel and, with `--stop common`, the 2 ms lead. No code of the interval mode calls a sleep function. |
| 3285 | `    }` | Ends the loop over the rounds (line 3202). |
| 3286 | `    for (int i = 0; i < cfg.threads; i++)` | Loop over the threads, after the last interval. |
| 3287 | `        pthread_join(th[i].tid, NULL);` | Waits for the end of worker thread `i` (`pthread_join`). |
| 3288 | `    return 0;` | Returns 0: the process ends with exit status 0. |
| 3289 | `}` | Ends the function `main`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/listing.txt`: objdump text of the 58 kernel functions of the `bwx13` binary that was built on CRB on 2026-11-15. Source of the start addresses, the loop starts and the instruction counts. Each function stands under a heading such as `=== bwx13 read ===`. The file `offsets.tsv` of the same folder lists the start address and the loop start of each kernel.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/build.txt`: build record of CRB. The row `## cc=` names the compiler, gcc 14.2.0. The row `## CFLAGS=` gives the flags. They hold no `-D` option, and the build command of `build13.sh` adds none. The rows `## placement bwx13` and `## placement bwx12` both hold `call=24`: the function `call` starts at 24 modulo 64 in both binaries. The row after them says that the placement up to `timed_sequence_hot` is the same as in `bwx12`. The block `## sha256:` gives the sha256 of `bwx13.c` at the build. It is the sha256 of the source file of this page.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/probe.txt`: objdump text of the kernels of `bw_new` (sections `=== bw_new ... ===`) and of `bw_old` (sections `=== bw_old ... ===`). Compared with the listing of [Ref1] by a script on 2026-11-25, with absolute code addresses and data addresses left out. `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite` and `k_asmcopy` of `bw_new` have the instruction text of the functions with the same names in `bwx13`. `k_read`, `k_write` and `k_copy` of `bw_old` have the instruction text of `k_oldread`, `k_oldwrite` and `k_oldcopy` of `bwx13`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/check_listing13.out`: output of the script `check_listing13.py` for the CRB build. It holds one row per kernel of `bwx12`: the loop offset, the loop offset of the reference listing of `bwx12`, the word `same` for the instruction text and the result `ok`. Three more rows are those of the `rand_nop` kernels: each has the loop offset 20, the word `expected` for the code and the result `ok`. The last row says `kernels=55 failed_rows=0 new_kernels=3 new_failed_rows=0`.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: sections B.4 to B.8, the specification of the first runner `bwx` that the comments cite: the two stop methods (B.4), the start offsets (B.5), the page state (B.6), the loop addresses (B.7) and the counters (B.8). B.7 names the loop offset as a factor of step B3. B.8 says that counter code without user-mode counting fails without root on CRB, and that a counter is opened with `pid = 0` and `cpu = -1`.
- [Ref6] `/usr/include/linux/perf_event.h`: the comment above `enum perf_event_read_format` (header of the machine on which this page was written). With `PERF_FORMAT_GROUP` the data of one `read` are `nr`, `time_enabled`, `time_running` and then one value per counter.
- [Ref7] external source: Linux kernel documentation on docs.kernel.org, read on 2026-11-25. Page https://docs.kernel.org/admin-guide/mm/transhuge.html: `thp_fault_alloc` "is incremented every time a huge page is successfully allocated and charged to handle a page fault". `thp_fault_fallback` "is incremented if a page fault fails to allocate or charge a huge page and instead falls back to using small pages". `thp_collapse_alloc` is incremented when the Linux thread khugepaged has allocated a huge page for a range of pages that it joins. Page https://docs.kernel.org/mm/page_migration.html: page migration moves the physical location of pages, and for the counter of successful migrations "Each count means that a page was migrated".
- [Ref8] `/home/jhan/workspace/ai-proj/arm-crb/code/w120-2026-11-15/FINDINGS.md`: the notes of the investigation of the whole-chip read rate of 2026-11-15. Section F5 names `bwx13` as its runner and describes the three `rand_nop` kernels and the question that they were built for.
