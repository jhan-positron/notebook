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
- **Kernel table, `kernels[]`**: the array of {L1051-1068}. Each entry holds the name of a kernel (the word used in `--seq`), its type (`T_READ`, `T_WRITE`, `T_COPY` or `T_OLDREAD`) and a pointer to its function. In this version it has 29 entries.
- **`cfg`**: the structure that holds the settings from the arguments: thread count, CPU list, buffer size, kernel sequence, rounds, stop rule and counter settings ({L231-249}).
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

1. Start. `main` reads the clock once for the process start time `t_base_ns`, reads the page size and sets the default buffer size of 1 MiB. Then `restrict_cpus` removes every CPU above 119 from the allowed CPU set of the process ({L2481-2488}).
2. Mode choice. `main` compares every argument with the word `--trial`. When one is equal, it calls `trial_main` and returns its result. Otherwise it goes on in the interval mode, which is the rest of `main` ({L2489-2491}).
3. Argument parsing. One loop over the arguments fills the settings structure `cfg`: threads, CPU list, bytes per thread, interval length, rounds, the `--seq` list, the stop rule, the start rule and the counter settings. `--selftest` and `--list` end the program in this loop ({L2493-2545}).
4. Checks of the settings. A failed check prints the option summary and ends the program with exit status 2. Each `--seq` entry without `@SIZE` gets the size of `--bytes`, and a copy kernel in the list gives each thread a second buffer ({L2546-2577}).
5. Threads. `main` creates a barrier for all workers plus itself and starts one thread per worker. Thread `i` gets entry `i` of the CPU list ({L2579-2593}).
6. Each worker pins itself to its CPU, opens its counters when `--count` is given, maps its buffer with `alloc_buf` and writes every word of the `--bytes` range of it once with `k_write`. This write is the first touch ({L1225-1234}).
7. Header. `main` prints the header lines: the settings and the column names of the I, T, P and C rows ({L2595-2614}).
8. Only in a process with more than one thread: when all buffers exist, `main` reads the page state of all buffers and prints P rows with the position -1 ({L2618-2626}, {L2682-2696}).
9. Loops. The workers and `main` run the same two loops: the rounds, and inside a round the positions of the `--seq` list. One pair of round and position is one interval ({L1240-1241}, {L2616-2617}).
10. Warm-up pass. Each worker calls the kernel of the position once over the whole range of the entry. This call is not timed ({L1253}).
11. Common start, only with `--stop common`. When all workers wait at the barrier, `main` reads the clock, sets the start time to that value plus 2 ms and the deadline to the start time plus the `--min-ms` value, and then adds 1 to `gen` ({L2634-2639}). Each worker waits for the new `gen` and then reads the clock in a loop until the start time ({L1260-1267}).
12. Start of the timed interval. With `--count` the worker first reads its counter group and its thread CPU time. Then it reads the clock: `t0` ({L1268-1272}).
13. Timed loop with `--stop common`. The worker calls the kernel on one chunk of 2 MiB, adds the size of the chunk to its byte count and reads the clock: `t1`. It repeats this with the next chunk until `t1` is at or after the deadline ({L1274-1285}).
14. Timed loop with `--stop pass`. The worker runs whole passes over the range of the entry. It reads the clock after a fixed number of passes: 8 MiB divided by the size of the entry, rounded down, and at least 1 pass. It stops when the `--min-ms` time has passed after `t0` ({L1286-1300}).
15. End of the interval, worker. The worker reads its thread CPU time and its counter group again. It stores the byte count, `t0`, the last `t1`, the common start time and the late flag, and it waits at the barrier ({L1301-1315}).
16. I row. `main` adds the bytes of all threads and takes the longest elapsed time `t1 - t0` of one thread. The last column of the I row is the total divided by that time, in GB/s ({L2643-2655}).
17. T rows and C rows. `main` prints one T row per thread with its bytes and its times, and with `--count` one C row per thread with the change of its counters over the interval ({L2656-2680}).
18. Page state, in a process with more than one thread. While the workers wait at the barrier, `main` reads the page state of all buffers. Then it releases the workers and prints the P rows and one `# page_read` line ({L2682-2696}). In a process with one thread the worker reads the page state itself before each interval, and `main` prints its P rows before the I row ({L1254-1258}, {L2649-2653}).
19. End. After the last interval `main` waits for the end of all threads and returns 0 ({L2700-2702}).

## Behavior a reader must know

- Difference to `bwx10.c`: additions only. The command `diff` shows 138 added lines in nine blocks, each between a `bwx11+` line and a `bwx11-` line: the history comment ({L1-26}), the three kernels with a second pad ({L1008-1043}), three entries of the kernel table ({L1064-1066}), the evict step ({L1992-2032}), its rows in `trial_worker` ({L2081-2095}), its usage text ({L2375-2380}), its option ({L2411-2414}) and the two blocks around the include of the self-test file ({L2472-2474}, {L2476-2479}).
- Difference to the next version: `bwx12.c` is this file plus 423 added lines in five blocks, for 26 more kernels, a third pad and the include of its own self-test file. Every line of this file stands in `bwx12.c`.
- The three kernels of round 4 are the `asmread` loop with 64, 96 and 128 `nop` instructions between the 8 loads and the `add` of the read address: 75, 107 and 139 instructions per 256 B against 11 in `asmread`. They read the same bytes as `asmread`, and the worker counts their bytes in the same way ({L1029-1031}, {L1280}).
- The evict step runs only in the trial mode, only with `--evict-mb` above 0, and once per process: after the first touch of the buffer and of the record block and before the first trial ({L2085-2091}). It lies in no timed sequence. Its duration is printed in the M row `evict_ns`. When it fails, the process prints an X row and ends with exit status 2.
- Apart from the three kernels, the interval mode is the interval mode of `bwx10.c`: the other additions belong to the trial mode and to the include of the self-test file.
- The trial mode follows the design of the investigation: one pinned worker, and trials of prefix, predecessor and target windows [Ref7]. Between two windows lie only the store of the results of the window, the clock reads and, before a target window of a trial with the counter state `read`, one reading of the counter group and of the thread CPU time ({L1607-1610}, {L1587-1589}). With `--trace` these clock reads and this reading also store events in the trace.
- CRB build of `bwx11`. The source of this page has the sha256 that the build record gives for `bwx11.c` [Ref2]. In the listing the loops of the three new kernels start at 20 modulo 64, the loop offset of `k_asmread` [Ref1]. The function `call` starts at 24 modulo 64, as in `bwx10` and in `bwx8` [Ref2].
- What is timed: only {L1272-1284} or {L1272-1298} of `worker`. The interval starts at the clock read `t0` and ends at the last clock read `t1`. Between them lie the kernel calls through `call`, the byte count and the clock reads. Not timed: allocation, first touch, warm-up pass, barrier waits, the wait for the common start, counter readings, page-state readings and all output.
- Stop rule `--stop common`: all threads get the same deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted ({L1285}).
- Rate. The program prints one rate: the last column of the I row, the bytes of all threads divided by the longest elapsed time of one thread, in GB/s with GB = 1e9 bytes ({L2655}). A T row holds the bytes and the elapsed time of one thread and no rate ({L2659}).
- Kernel calls. With `--stop common` the kernel function is entered once per chunk. A kernel that saves `d8` to `d15` does so once per call, outside its loop. One clock read follows each call ({L1279-1284}).
- Thread placement: thread `i` pins itself to entry `i` of the CPU list before it opens its counters and before it maps its buffer ({L1225-1229}, {L2588}). The main thread is not pinned in the interval mode.
- Buffers: each buffer is a private mapping of its own, and no two threads share a buffer. A thread has one buffer, or two with `--two-buffers` or with a copy kernel in `--seq`. A buffer starts at a 2 MiB boundary, and `alloc_buf` asks Linux for 2 MiB pages for it unless `--no-thp` is given. The pinned thread writes the `--bytes` range of the buffer once before any read. The read kernels never change it ({L401-418}, {L1229-1230}).
- Order inside a process: the kernels run in the order of `--seq`, and the rounds follow one another directly. The file holds no call of a sleep function. Before each timed interval the worker runs the warm-up pass with the kernel of that interval ({L1253}).
- Counters in the interval mode: each thread opens its group once and never resets it. A C row holds the change between a reading directly before `t0` and a reading directly after the last `t1`. An event that does not open is printed as `NA` ({L1184}, {L2674-2675}).
- What ends a process of the interval mode with exit status 2: a bad argument, a failed `mmap`, a failed call that reads or sets the allowed CPU set, an allowed CPU set without a CPU from 0 to 119, a failed read of the counter group, and a failed setup in `main`. A failed `mprotect` or `madvise` in `alloc_buf` only writes a message, and the run continues ({L412}, {L416}). The trial mode also ends with exit status 2 on a defect of its plan file.
- The code of this file does not look at the marker file and opens files only for reading. Its output is the csv text on the standard output and the messages on stderr.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx11-crb-build-1/listing.txt`: objdump text of the 29 kernel functions of the `bwx11` binary that was built on CRB on 2026-11-15. Source of the start addresses, the loop starts and the instruction counts. Each function stands under a heading such as `=== bwx11 read ===`. The file `offsets.tsv` of the same folder lists the start address and the loop start of each kernel.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx11-crb-build-1/build.txt`: build record of CRB. The row `## cc=` names the compiler, gcc 14.2.0. The row `## CFLAGS=` gives the flags. They hold no `-D` option, and the build command of `build11.sh` adds none. The rows `## placement bwx11`, `## placement bwx10` and `## placement bwx8` all hold `call=24`: the function `call` starts at 24 modulo 64 in the three binaries. The block `## sha256:` gives the sha256 of `bwx11.c` at the build. It is the sha256 of the source file of this page.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/probe.txt`: objdump text of the kernels of `bw_new` (sections `=== bw_new ... ===`) and of `bw_old` (sections `=== bw_old ... ===`). Compared with the listing of [Ref1] by a script on 2026-11-25, with absolute code addresses and data addresses left out. `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite` and `k_asmcopy` of `bw_new` have the instruction text of the functions with the same names in `bwx11`. `k_read`, `k_write` and `k_copy` of `bw_old` have the instruction text of `k_oldread`, `k_oldwrite` and `k_oldcopy` of `bwx11`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: sections B.4 to B.8, the specification of the first runner `bwx` that the comments cite: the two stop methods (B.4), the start offsets (B.5), the page state (B.6), the loop addresses (B.7) and the counters (B.8). B.7 names the loop offset as a factor of step B3. B.8 says that counter code without user-mode counting fails without root on CRB, and that a counter is opened with `pid = 0` and `cpu = -1`.
- [Ref5] `/usr/include/linux/perf_event.h`: the comment above `enum perf_event_read_format` (header of the machine on which this page was written). With `PERF_FORMAT_GROUP` the data of one `read` are `nr`, `time_enabled`, `time_running` and then one value per counter.
- [Ref6] external source: Linux kernel documentation on docs.kernel.org, read on 2026-11-25. Page https://docs.kernel.org/admin-guide/mm/transhuge.html: `thp_fault_alloc` "is incremented every time a huge page is successfully allocated and charged to handle a page fault". `thp_fault_fallback` "is incremented if a page fault fails to allocate or charge a huge page and instead falls back to using small pages". `thp_collapse_alloc` is incremented when the Linux thread khugepaged has allocated a huge page for a range of pages that it joins. Page https://docs.kernel.org/mm/page_migration.html: page migration moves the physical location of pages, and for the counter of successful migrations "Each count means that a page was migrated".
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design of the investigation into the small gain of the new read kernel at 8 MiB. Its section "Runner design" describes the trial mode: one pinned worker, the trial with prefix, predecessor and target windows, and the required records.
- [Ref8] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb-results.md`: the result handoff of that investigation. Its table "What ran" names `bwx11` as the binary of round 4, with the first 8 digits of its sha256, `f1215f9e`. The build record gives a sha256 with these first digits for the binary `bwx11` [Ref2].
