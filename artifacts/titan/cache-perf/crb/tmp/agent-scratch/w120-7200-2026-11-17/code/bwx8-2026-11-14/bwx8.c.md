# `bwx8.c` explained, line by line

- Source file: `bwx8-2026-11-14/bwx8.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 2283 lines, 85771 bytes).
- sha256 of the source when this page was built: `d5e6c2039139caf92d8610e40de249941724ae876a95541ffe0532635fe557b2`.

## Short version: purpose

`bwx8.c` is the source of `bwx8`, the version of the runner that the investigation into the small gain of the new read kernel at a buffer of 8 MiB used in its rounds 1 and 2 [Ref8]. It is the first runner `bwx.c` plus a second mode, the trial mode: one pinned worker thread runs the trials of a plan file, and each trial is a list of timed windows with only clock reads and, when the plan asks for it, counter readings between them. The interval mode of `bwx.c` stays as it is: it times a sequence of kernels in one process and prints the bytes and the times as csv rows.

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
- **Window record**: the structure `struct win` of one window: its kernel, its range and its requested duration, and after the run its byte count and its two clock times.
- **Stop rules of the runner**: `--stop pass` selects the whole-pass stop. `--stop common` selects the common stop.
- **Interval mode, trial mode**: the two modes of the program. The interval mode (option `--seq`) runs the number of threads that `--threads` gives and times one interval per round and kernel of the sequence. The trial mode (option `--trial`) runs one worker thread through the trials of a plan file.
- **Kernel table, `kernels[]`**: the array of lines 821 to 831. Each entry holds the name of a kernel (the word used in `--seq`), its type (`T_READ`, `T_WRITE`, `T_COPY` or `T_OLDREAD`) and a pointer to its function. In this version it has 21 entries.
- **`cfg`**: the structure that holds the settings from the arguments: thread count, CPU list, buffer size, kernel sequence, rounds, stop rule and counter settings (lines 180 to 198).
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
- **`handoff.md`**: the specification of the first runner `bwx`. The comments cite its sections B.4 to B.8 [Ref4].
- **Build record**: the files that the build script `build8.sh` wrote on CRB. `build.txt` holds the compiler, the flags and the sha256 values [Ref2]. `listing.txt` holds the machine-code listing of every kernel [Ref1].
- **Plan file, trial, window (trial mode)**: the plan file lists the trials of one process. A trial is a list of windows. A window runs one kernel on one range of the buffer for a fixed time.
- **Phase, target window (trial mode)**: a trial has up to four phases, in this order: previous activity (1 window), prefix (4 windows), predecessor (1 window) and target. A target window is a window of the last phase.
- **Timed sequence (trial mode)**: the run of all windows of one trial, done by the function `timed_sequence`.
- **Counter state (trial mode)**: the field `count` of a plan line: `closed` (no counter group is open), `open` (the group is open and is not read during the trial) or `read` (the group is read at the boundaries of the target windows).
- **Record block (trial mode)**: one memory block that holds the records of all trials: the trial records, the window records, the counter readings, the bins and, with `--trace`, the event log.
- **Bin, trace (trial mode)**: a bin is a part of a target window with a requested length of 10 ms. The trace (`--trace`) is a log of events with clock times.
- **Controlling thread (trial mode)**: the thread that runs `trial_main`. It pins itself to the CPU of `--ctl-cpu`, starts the one worker of the trial mode and waits for its end.
- **S, W, B, E, X, TR, M, K rows (trial mode)**: row kinds that only the trial mode prints: S (the plan line of a trial), W (one window), B (one bin), E (the summary of a trial), X (a problem), TR (one trace event), M (one setting or one fact of the process) and K (the address of one kernel).
- **Context switch**: Linux stops running a thread on its CPU. It is voluntary when the thread waits by itself, and involuntary when Linux takes the CPU away.
- **Minor page fault**: a page fault that Linux serves without disk access. The first touch of a page is one.

## Main flow

1. Start. `main` reads the clock once for the process start time `t_base_ns`, reads the page size and sets the default buffer size of 1 MiB. Then `restrict_cpus` removes every CPU above 119 from the allowed CPU set of the process (lines 2061 to 2068).
2. Mode choice. `main` compares every argument with the word `--trial`. When one is equal, it calls `trial_main` and returns its result. Otherwise it goes on in the interval mode, which is the rest of `main` (lines 2069 to 2071).
3. Argument parsing. One loop over the arguments fills the settings structure `cfg`: threads, CPU list, bytes per thread, interval length, rounds, the `--seq` list, the stop rule, the start rule and the counter settings. `--selftest` and `--list` end the program in this loop (lines 2073 to 2125).
4. Checks of the settings. A failed check prints the option summary and ends the program with exit status 2. Each `--seq` entry without `@SIZE` gets the size of `--bytes`, and a copy kernel in the list gives each thread a second buffer (lines 2126 to 2157).
5. Threads. `main` creates a barrier for all workers plus itself and starts one thread per worker. Thread `i` gets entry `i` of the CPU list (lines 2159 to 2173).
6. Each worker pins itself to its CPU, opens its counters when `--count` is given, maps its buffer with `alloc_buf` and writes every word of the `--bytes` range of it once with `k_write`. This write is the first touch (lines 988 to 997).
7. Header. `main` prints the header lines: the settings and the column names of the I, T, P and C rows (lines 2175 to 2194).
8. Only in a process with more than one thread: when all buffers exist, `main` reads the page state of all buffers and prints P rows with the position -1 (lines 2198 to 2206, lines 2262 to 2276).
9. Loops. The workers and `main` run the same two loops: the rounds, and inside a round the positions of the `--seq` list. One pair of round and position is one interval (lines 1003 to 1004, lines 2196 to 2197).
10. Warm-up pass. Each worker calls the kernel of the position once over the whole range of the entry. This call is not timed (line 1016).
11. Common start, only with `--stop common`. When all workers wait at the barrier, `main` reads the clock, sets the start time to that value plus 2 ms and the deadline to the start time plus the `--min-ms` value, and then adds 1 to `gen` (lines 2214 to 2219). Each worker waits for the new `gen` and then reads the clock in a loop until the start time (lines 1023 to 1030).
12. Start of the timed interval. With `--count` the worker first reads its counter group and its thread CPU time. Then it reads the clock: `t0` (lines 1031 to 1035).
13. Timed loop with `--stop common`. The worker calls the kernel on one chunk of 2 MiB, adds the size of the chunk to its byte count and reads the clock: `t1`. It repeats this with the next chunk until `t1` is at or after the deadline (lines 1037 to 1048).
14. Timed loop with `--stop pass`. The worker runs whole passes over the range of the entry. It reads the clock after each group of passes: 8 MiB divided by the size of the range, rounded down, and at least 1 pass. It repeats this until the `--min-ms` time has passed after `t0` (lines 1049 to 1063).
15. End of the interval, worker. The worker reads its thread CPU time and its counter group again. It stores the byte count, `t0`, the last `t1`, the common start time and the late flag, and it waits at the barrier (lines 1064 to 1078).
16. I row. `main` adds the bytes of all threads and takes the longest elapsed time `t1 - t0` of one thread. The last column of the I row is the total divided by that time, in GB/s (lines 2223 to 2235).
17. T rows and C rows. `main` prints one T row per thread with its bytes and its times, and with `--count` one C row per thread with the change of its counters over the interval (lines 2236 to 2260).
18. Page state, in a process with more than one thread. While the workers wait at the barrier, `main` reads the page state of all buffers. Then it releases the workers and prints the P rows and one `# page_read` line (lines 2262 to 2276). In a process with one thread the worker reads the page state itself before each interval, and `main` prints its P rows before the I row (lines 1017 to 1021, lines 2229 to 2233).
19. End. After the last interval `main` waits for the end of all threads and returns 0 (lines 2280 to 2282).
20. Trial mode, the other path of step 2. `trial_main` reads its arguments. It checks that `--cpus` names exactly one CPU, that `--bytes` is given and is a multiple of 256, and that `--plan` is given. It also checks that the CPU of the controlling thread is another CPU and that both CPUs are in the allowed CPU set (lines 1994 to 2030).
21. `read_plan` reads and checks the whole plan file. A defect ends the process with exit status 2. A plan with a counter state `open` or `read` also needs the counter settings (lines 2031 to 2045).
22. The controlling thread pins itself to the CPU of `--ctl-cpu`, starts the one worker and waits for its end (lines 2049 to 2055).
23. The worker pins itself to the CPU of `--cpus`, maps the buffer with `alloc_buf` and writes every word of the `--bytes` range once with `k_write`. This write is the first touch. Then `alloc_records` allocates the record block and writes one byte to every page of it (lines 1682 to 1694).
24. The worker prints the header lines, the M rows and the K rows (lines 1697 to 1738).
25. For each trial, in the order of the plan: the worker prints the S row. `run_trial` opens or closes the counter group as the plan line asks. It reads the page state, the context switches and the thread CPU time, runs the timed sequence and takes the three readings again. Then `emit_trial` prints the rows of the trial (lines 1740 to 1748, lines 1459 to 1486).
26. The timed sequence, function `timed_sequence`. For each window it reads the clock: `t0`. Then it calls the kernel on the first `size` bytes of the buffer, in groups of whole passes, and reads the clock after each group: `t1`. The window ends at the first `t1` at or after its requested duration (lines 1340 to 1370).
27. After the last trial the worker closes the counter group when it is open, and the thread ends. `trial_main` returns 0 (lines 1749 to 1754, line 2056).

## Behavior a reader must know

- Difference to `bwx.c`. The command `diff` shows five changed places in three parts of the file. The header comment has other text in lines 2 to 4, lines 6 to 15 and lines 18 to 20. In the place where `bwx.c` includes the file `bwx_selftest.c`, this file holds the whole trial mode and the include of `bwx8_selftest.c` (lines 1142 to 2059). `main` has three more lines, the mode choice (lines 2069 to 2071). Every other line of this file stands in `bwx.c`, in the same order.
- So the interval mode is the code of `bwx.c`: the text from line 22 to the end of `parse_events` (line 1140) and the rest of `main`. A process without the argument `--trial` runs only this code, the three lines of the mode choice and, with `--selftest`, the self-test of the included file.
- Difference to the next version: `bwx10.c` is this file plus 282 added lines in eleven blocks, for five more read kernels and two options of the trial mode. One more line differs: the include of the self-test file.
- The trial mode follows the design of the investigation: one pinned worker, and trials of prefix, predecessor and target windows [Ref7]. Between two windows lie only the store of the results of the window, the clock reads and, before a target window of a trial with the counter state `read`, one reading of the counter group and of the thread CPU time (lines 1366 to 1369, lines 1346 to 1348). With `--trace` these clock reads and this reading also store events in the trace. The file `DECISIONS-bwx8.md` fixes the format of the plan file and of the output rows [Ref9].
- What is timed in the trial mode: a window is the time from its start clock read `t0` to its last clock read `t1` (line 1348, line 1355). Between them lie the kernel calls, the byte count, the clock reads and, for a target window with bins, the bin records. With `--trace` each clock read and the first kernel call of a window also add an event to the log (line 1283, line 1302). A window ends at its first clock read at or after its requested duration, at the end of a whole pass (line 1365).
- Not timed in the trial mode: the time between two windows belongs to no window. With the counter state `read` the reading of the counter group lies there, before the start clock read of a target window (lines 1346 to 1347). `run_trial` reads the page state, the context switches and the thread CPU time before and after the timed sequence, and it opens or closes the counter group before it (lines 1459 to 1486). The S row of a trial is printed before `run_trial` starts, and all other rows after it has returned (lines 1744 to 1747).
- The trial mode prints no rate. A W row holds the byte count and the two clock times of one window (lines 1596 to 1598).
- The plan of the trial mode accepts read kernels only (line 1825). The whole plan is read and checked before the process pins a thread or maps a buffer, and a defect ends the process with exit status 2 (line 2031).
- After the checks of `trial_main` (lines 2019 to 2045) the process can still end with exit status 2: when a pinning call fails (`pin_cpu`), when the worker thread cannot be created (lines 2051 to 2053), when the worker does not run on the CPU of `--cpus` after the pinning (lines 1683 to 1686), when `mmap` fails in `alloc_buf`, or when the record block cannot be allocated. A problem during a trial gives an X row, and the process still ends with exit status 0.
- CRB build of `bwx8`. The source of this page has the sha256 that the build record gives for `bwx8.c` [Ref2]. The listing holds the 21 kernels [Ref1]. The build record lists the branch targets of `timed_sequence`: indirect calls, `clock_gettime`, `tcount` and `__stack_chk_fail` [Ref2].
- What is timed in the interval mode: only lines 1035 to 1047 or lines 1035 to 1061 of `worker`. The interval starts at the clock read `t0` and ends at the last clock read `t1`. Between them lie the kernel calls through `call`, the byte count and the clock reads. Not timed: allocation, first touch, warm-up pass, barrier waits, the wait for the common start, counter readings, page-state readings and all output.
- Stop rule `--stop common`: all threads get the same deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted (line 1048).
- Rate. The program prints one rate: the last column of the I row, the bytes of all threads divided by the longest elapsed time of one thread, in GB/s with GB = 1e9 bytes (line 2235). A T row holds the bytes and the elapsed time of one thread and no rate (line 2239).
- Kernel calls. With `--stop common` the kernel function is entered once per chunk. A kernel that saves `d8` to `d15` does so once per call, outside its loop. One clock read follows each call (lines 1042 to 1047).
- Thread placement: thread `i` pins itself to entry `i` of the CPU list before it opens its counters and before it maps its buffer (lines 988 to 992, line 2168). The main thread is not pinned in the interval mode.
- Buffers: each buffer is a private mapping of its own, and no two threads share a buffer. A thread has one buffer, or two with `--two-buffers` or with a copy kernel in `--seq`. A buffer starts at a 2 MiB boundary, and `alloc_buf` asks Linux for 2 MiB pages for it unless `--no-thp` is given. The pinned thread writes the `--bytes` range of the buffer once before any read. The read kernels never change it (lines 350 to 367, lines 992 to 993).
- Order inside a process: the kernels run in the order of `--seq`, and the rounds follow one another directly. The file holds no call of a sleep function. Before each timed interval the worker runs the warm-up pass with the kernel of that interval (line 1016).
- Counters in the interval mode: each thread opens its group once and never resets it. A C row holds the change between a reading directly before `t0` and a reading directly after the last `t1`. An event that does not open is printed as `NA` (line 947, lines 2254 to 2255).
- What ends a process of the interval mode with exit status 2: a bad argument, a failed `mmap`, a failed call that reads or sets the allowed CPU set, an allowed CPU set without a CPU from 0 to 119, a failed read of the counter group, and a failed setup in `main`. A failed `mprotect` or `madvise` in `alloc_buf` only writes a message, and the run continues (line 361, line 365). The trial mode also ends with exit status 2 on a defect of its plan file.
- The code of this file does not look at the marker file and opens files only for reading. Its output is the csv text on the standard output and the messages on stderr.

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/bwx8.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (2283 lines, 85771 bytes, sha256 `d5e6c2039139caf92d8610e40de249941724ae876a95541ffe0532635fe557b2`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Comment of the version `bwx8`: the two modes and the stand-in kernels (lines 1 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Opens the header comment of the file. It says what `bwx8.c` is: a copy of the first runner `bwx.c` with a second mode, the trial mode. |
| 2 | ` * bwx8.c - scratch copy of bwx.c (crb/tmp/agent-scratch/bwx-2026-11-13) for` | Comment: `bwx8.c` is a scratch copy of `bwx.c`, the first runner. The path in parentheses is the folder of `bwx.c`. In the code repo that folder has the name `bwx-2026-11-13`. |
| 3 | ` * the design crb/new-test-kernel/tackle-8mb.md. The contract with the other` | Comment: the copy was made for the design document `tackle-8mb.md` in the folder `crb/new-test-kernel`. The sentence about the contract continues in line 4. |
| 4 | ` * parts is DECISIONS-bwx8.md in this folder.` | Comment: the contract with the other parts of that work is the file `DECISIONS-bwx8.md`. It fixes the file formats that the parts exchange. The file lies in the code folder `bwx8-2026-11-14`, the folder of `bwx8.c`. |
| 5 | ` *` | Comment: an empty line of the comment. |
| 6 | ` * Two modes:` | Comment: the program has two modes. |
| 7 | ` *   --seq ...    the interval mode of bwx.c. Its code is the text of bwx.c.` | Comment: the option `--seq` selects the interval mode of `bwx.c`. The comment says that the code of this mode is the text of `bwx.c`. `main` runs this mode when no argument is the word `--trial` (lines 2069 to 2071). |
| 8 | ` *   --trial ...  one pinned worker runs the trials of a plan file. A trial is` | Comment: the option `--trial` selects the trial mode. One pinned worker thread runs the trials of a plan file. All code of this mode stands after the function `parse_events` (lines 1118 to 1140). |
| 9 | ` *                previous activity, prefix, predecessor and target windows` | Comment: a trial is a list of windows in four phases: previous activity, prefix, predecessor and target. A window runs one kernel on one range of the buffer for a fixed time. |
| 10 | ` *                with nothing but clock reads between them.` | Comment: between two windows the worker does nothing but read the clock. The code has one more step there: for a trial with the counter state `read` it also reads the counter group and the thread CPU time before each target window (lines 1346 to 1347). |
| 11 | ` *` | Comment: an empty line of the comment. |
| 12 | ` * Everything from "#define _GNU_SOURCE" to the end of parse_events() is the` | Comment: names a range of this file. It reaches from the line `#define _GNU_SOURCE` (line 22) to the end of the function `parse_events` (line 1140). |
| 13 | ` * text of bwx.c, so the kernels, PLACE, call() and alloc_buf() are unchanged.` | Comment: that range is the text of `bwx.c`. So the kernels, the macro `PLACE` (line 79), the function `call` (line 838) and the function `alloc_buf` (line 350) are unchanged. The later versions put their marked blocks into this range too. |
| 14 | ` * All code of the trial mode stands after it. The build uses` | Comment: all code of the trial mode stands after that range. The sentence about the build continues in line 15. |
| 15 | ` * -fno-toplevel-reorder, so the kernels keep their place in the binary.` | Comment: the build uses the gcc flag `-fno-toplevel-reorder`. With it gcc writes the functions in the order of the source. So the kernels keep their place in the binary. The build record of CRB for `bwx8` holds this flag [Ref2]. |
| 16 | ` *` | Comment: an empty line of the comment. |
| 17 | ` * On AArch64 the kernels are the real ones. On any other machine every NEON` | Comment: on AArch64, the 64-bit Arm instruction set, the kernels are the real ones. The sentence about other machines starts here. |
| 18 | ` * and asm kernel is replaced by a plain C stand-in, so that the harness can` | Comment: on any other machine a plain C loop replaces every NEON kernel and every assembly kernel. The comment calls this loop a stand-in. NEON is the vector part of AArch64. |
| 19 | ` * be run on the development machine. Rates of a stand-in build mean nothing.` | Comment: the stand-ins have one purpose: the program can then run on the development machine. The rates of a build with stand-ins mean nothing. |
| 20 | ` * GB means 1e9 bytes throughout.` | Comment: GB means 1e9 bytes in the whole file. |
| 21 | ` */` | Ends the comment. |

### Includes, constants and the highest CPU that the process may use (lines 22 to 57)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the first include. It makes the Linux-specific declarations of the C library visible, for example `sched_setaffinity` and `CPU_SET`. |
| 23 | `#ifdef __aarch64__` | Compiles line 24 only when the compiler builds for AArch64, the 64-bit Arm instruction set. gcc defines the macro `__aarch64__` in that case. |
| 24 | `#include <arm_neon.h>` | Includes `arm_neon.h`. It declares the NEON intrinsics, for example `vld1q_u64`. An intrinsic is a C function that maps to one vector instruction. NEON is the vector part of AArch64. |
| 25 | `#endif` | Ends the `#ifdef` of line 23. |
| 26 | `#include <errno.h>` | Includes `errno.h`. It declares `errno`, the error number that a failed library call sets. `parse_long` tests it (lines 272 to 274). |
| 27 | `#include <linux/perf_event.h>` | Includes `linux/perf_event.h`. It declares the structure `perf_event_attr` and the `PERF_FORMAT` constants. `open_counters` (line 929) opens the hardware counters with them. |
| 28 | `#include <pthread.h>` | Includes `pthread.h`. It declares the thread functions `pthread_create` and `pthread_join` and the barrier function `pthread_barrier_wait`. |
| 29 | `#include <sched.h>` | Includes `sched.h`. It declares the CPU set type `cpu_set_t` and the calls `sched_getaffinity` and `sched_setaffinity`. They read and set the CPUs on which Linux may run a thread. |
| 30 | `#include <setjmp.h>` | Includes `setjmp.h`. It declares `sigsetjmp` and `siglongjmp`. No other line of this file uses them. The self-test file that this file includes uses them. |
| 31 | `#include <signal.h>` | Includes `signal.h`. It declares `sigaction` and the signal numbers. No other line of this file uses them. The included self-test file uses them to catch `SIGSEGV`, the signal that Linux sends at a forbidden memory access. |
| 32 | `#include <stdatomic.h>` | Includes `stdatomic.h`. It declares the atomic types and the functions `atomic_load`, `atomic_store` and `atomic_fetch_add`. The three variables of the common start use them (lines 239 to 241). |
| 33 | `#include <stdint.h>` | Includes `stdint.h`. It declares the integer types of fixed size, for example `uint64_t` (64 bits, without a sign) and `int64_t` (64 bits, with a sign). |
| 34 | `#include <stdio.h>` | Includes `stdio.h`. It declares the input and output functions, for example `printf`, `fprintf`, `fopen` and `fgets`. |
| 35 | `#include <stdlib.h>` | Includes `stdlib.h`. It declares `exit`, `strtol`, `strtod`, `calloc` and `getenv`. |
| 36 | `#include <string.h>` | Includes `string.h`. It declares the text and memory functions, for example `strcmp`, `strtok`, `memset` and `strerror`. |
| 37 | `#include <sys/mman.h>` | Includes `sys/mman.h`. It declares `mmap`, `mprotect` and `madvise`. `alloc_buf` (line 350) uses them for the buffers. |
| 38 | `#include <sys/syscall.h>` | Includes `sys/syscall.h`. It declares the numbers of the system calls, here `SYS_perf_event_open`. `open_counters` passes this number to `syscall` (line 942). |
| 39 | `#include <time.h>` | Includes `time.h`. It declares `clock_gettime` and the structure `timespec`. `now_ns` (line 243) reads the clock with them. |
| 40 | `#include <unistd.h>` | Includes `unistd.h`. It declares `sysconf`, `getpid` and `read`. |
| 42 | `#define HUGE_BYTES (2UL << 20)` | `HUGE_BYTES`: 2097152 bytes (2 MiB), the size of one huge page. The expression is 2 shifted left by 20 bits. Every buffer starts at a multiple of this value (line 358). |
| 43 | `#define MAX_CPUS 1024` | `MAX_CPUS`: the `--cpus` list may hold at most 1024 CPUs (line 322). |
| 44 | `#define MAX_SEQ 64` | `MAX_SEQ`: the `--seq` list may hold at most 64 kernels (line 1106). |
| 45 | `#define MAX_EV 8` | `MAX_EV`: the `--events` list may hold at most 8 counter events (line 1123). |
| 46 | `#define CHECK_BYTES (8UL << 20) /* --stop pass: clock is read after at least this many bytes */` | `CHECK_BYTES`: 8388608 bytes (8 MiB). Comment: with `--stop pass` a thread reads the clock after at least this many bytes. For some sizes the code reads the clock earlier. The number of whole passes between two clock reads is this value divided by the size of the range, rounded down, and at least 1 (lines 1051 to 1053). So with a range of 3 MiB the thread reads the clock after 2 passes, which are 6 MiB. The trial mode computes its passes in the same way (line 1520). |
| 47 | `#define CHUNK_BYTES HUGE_BYTES  /* --stop common: clock is read after each chunk of this size */` | `CHUNK_BYTES`: the value of `HUGE_BYTES`, 2097152 bytes (2 MiB). It is the size of a chunk. Comment: with `--stop common` a worker calls the kernel on one chunk and then reads the clock (lines 1040 to 1047). When the range of a `--seq` entry is below 2 MiB, the chunk is that whole range (line 1040). |
| 48 | `#define LEAD_NS 2000000L        /* --stop common: the common start is this long after the barrier */` | `LEAD_NS`: 2000000 ns (2 ms). With `--stop common` the main thread reads the clock after its barrier wait and sets the common start time of an interval to that clock value plus 2 ms (lines 2214 to 2216). The release at the barrier is not the start of the timed interval. Each worker waits until the clock reaches the common start time (line 1028). Then it starts its timed interval with its own clock read `t0` (line 1035). |
| 49 | `#define LATE_NS 100000L         /* --stop common: flag "late" if a thread starts later than this */` | `LATE_NS`: 100000 ns (100 us, which is 0.1 ms). With `--stop common` a thread gets the flag `late` when its start clock read is more than this after the common start (line 1072). |
| 50 | `/* Highest CPU that the process may use. Rule of the test machine: CPUs 0 to` | Comment: the macro below gives the highest CPU number that the process may use. The rule of the test machine starts here: only the CPUs 0 to 119. |
| 51 | ` * 119 only, never 126 or 127. main() removes every higher CPU from the` | Comment: the end of the rule: never CPU 126 or CPU 127. `main` calls `restrict_cpus` (line 2068), which removes every higher CPU from the set of CPUs that Linux may use for the process. |
| 52 | ` * allowed set of the process, and --cpus rejects one. Another machine can` | Comment: the option `--cpus` also rejects a higher CPU (line 317). |
| 53 | ` * build with -DMAX_USE_CPU=N. */` | Comment: for another machine the build can set another limit with the compiler option `-DMAX_USE_CPU=N`. |
| 54 | `#ifndef MAX_USE_CPU` | Tests whether the build command has already defined `MAX_USE_CPU`. Only if not, line 55 is compiled. `restrict_cpus` (line 284) and `parse_cpus` (line 304) apply the limit. |
| 55 | `#define MAX_USE_CPU 119` | The default value: the highest CPU that the process may use is CPU 119. The CRB build of `bwx8` gave no `-D` option, so this value was used [Ref2]. |
| 56 | `#endif` | Ends the `#ifndef` of line 54. |

### Loop placement: the macros `PLACE` and `PADOF` (lines 58 to 81)

| Line | Source | Explanation |
|---:|---|---|
| 58 | `/*` | Opens the comment about the placement of the kernel loops. |
| 59 | ` * Loop placement (handoff B.7). PLACE(name) stands directly before kernel` | Comment: the topic is the loop placement. The aim is that the loop of each kernel starts at a known address modulo 64, the loop offset. Section B.7 of the file `handoff.md`, the specification of the first runner, treats this offset as a test factor [Ref4]. The macro `PLACE(name)` stands directly before the kernel function. |
| 60 | ` * k_<name>. It pads .text to a 64 B boundary and then adds PAD_<name> zero bytes,` | Comment: the kernel function has the name `k_` plus the kernel name. `PLACE` first pads the code section `.text` to a 64 B boundary. Then it adds zero bytes. The macro `PAD_` plus the kernel name gives their number. |
| 61 | ` * so the function starts at PAD_<name> modulo 64. This needs the gcc flags` | Comment: so the function starts at that pad value modulo 64. The method needs two gcc flags. |
| 62 | ` * -fno-toplevel-reorder -falign-functions=4, and PAD must be a multiple of 4.` | Comment: the two flags are `-fno-toplevel-reorder` and `-falign-functions=4`. A pad must be a multiple of 4. Both flags are in the build record of CRB for `bwx8` [Ref2]. |
| 63 | ` *` | Comment: an empty line of the comment. |
| 64 | ` * For a kernel with a planned loop offset, PAD = (LOOP - HEAD) mod 64. LOOP` | Comment: the rule for a kernel with a planned loop offset: the pad is `(LOOP - HEAD) mod 64`. |
| 65 | ` * is the planned offset of the loop start modulo 64. HEAD is the number of` | Comment: `LOOP` is the planned offset of the loop start, modulo 64. `HEAD` is a number of bytes. |
| 66 | ` * bytes between the function start and the loop start: 4 or 20 in the` | Comment: `HEAD` counts the bytes of code between the start of the function and the start of its loop. The comment gives the values 4 and 20. |
| 67 | ` * listings of bw_new (results/kernels-20261113T181222Z/probe.txt). HEAD is a` | Comment: these two values come from the listings of the binary `bw_new` in the file `probe.txt` of the result folder `kernels-20261113T181222Z`. `bw_new` is the benchmark binary of 2026-11-13 with the new kernels. In that file the loop of `k_copy` starts 4 bytes after the function start, and the loop of `k_asmcopy` 20 bytes after it [Ref3]. |
| 68 | ` * guess until the objdump listing of the CRB build confirms it: override it` | Comment: a `HEAD` value is a guess until the machine-code listing of the CRB build confirms it. |
| 69 | ` * with -DHEAD_<name>=N, or the whole pad with -DPAD_<name>=N.` | Comment: the build can replace one `HEAD` value with `-DHEAD_<name>=N`, or a whole pad with `-DPAD_<name>=N`. The CRB build of `bwx8` used no `-D` option [Ref2]. |
| 70 | ` * -DB3_OFFSET=0\|36\|52 puts the loops of copy, asmcopy and asmcopy2 at that` | Comment: the build option `-DB3_OFFSET=0`, `-DB3_OFFSET=36` or `-DB3_OFFSET=52` moves the loops of the kernels `copy`, `asmcopy` and `asmcopy2`. |
| 71 | ` * offset (step B3).` | Comment: these loops then start at that offset modulo 64 (lines 82 to 84). The option belongs to step B3 of the test plan of the first runner. |
| 72 | ` *` | Comment: an empty line of the comment. |
| 73 | ` * For the other kernels the default PAD is the start offset modulo 64 that` | Comment: the rule for every other kernel: the default pad is a start offset modulo 64 that the function has in an older binary. |
| 74 | ` * the function has in bw_new (new C and asm kernels) or in bw_old (old` | Comment: for a new C kernel or an assembly kernel the older binary is `bw_new`. For an old kernel it is `bw_old`. The old read kernel and the new read kernel show the result. The loop of `k_read` starts at 36 modulo 64 in the CRB build of `bwx8` and in `bw_new`. The loop of `k_oldread` in `bwx8` and the loop of `k_read` in `bw_old` both start at 40 modulo 64 [Ref1] [Ref3]. |
| 75 | ` * kernels). An A/A copy takes the PAD of its original.` | Comment: an A/A copy takes the pad of its original. An A/A copy is the same kernel source under a second name, for example `asmread2`. |
| 76 | ` */` | Ends the comment. |
| 77 | `#define STR2(x) #x` | `STR2(x)` turns its argument into a text in quotes. The preprocessor operator `#` does that. |
| 78 | `#define STR(x) STR2(x)` | `STR(x)` first replaces `x` by its value when `x` is a macro. Then it calls `STR2`. So with the default value 32 of `PAD_read`, `STR(PAD_read)` gives the text `"32"` and not the name in quotes. |
| 79 | `#define PLACE(name) __asm__(".pushsection .text\n.p2align 6\n.fill " STR(PAD_##name) ", 1, 0\n.popsection\n")` | `PLACE(name)` writes an `__asm__` statement outside of a function. gcc passes its text to the assembler without a change. `.pushsection .text` continues in the code section. `.p2align 6` pads the code up to an address that is a multiple of 64. `.fill N, 1, 0` adds N bytes of value 0. N is the value of the macro whose name `PAD_##name` builds from `PAD_` and the argument. `.popsection` returns to the section that was in use before. So the function that follows starts at N modulo 64. |
| 80 | `#define PADOF(loop, head) (((loop) - (head)) & 63)` | `PADOF(loop, head)`: `loop` minus `head`, modulo 64. The operation `& 63` keeps the low 6 bits. So a negative difference also gives a value from 0 to 63. |

### Planned loop offsets, head sizes and pads of the kernels (lines 82 to 168)

| Line | Source | Explanation |
|---:|---|---|
| 82 | `#ifdef B3_OFFSET` | Tests whether the build command defined `B3_OFFSET`. The CRB build of `bwx8` did not, so the `#else` branch of lines 85 to 87 was compiled [Ref2]. |
| 83 | `#define LOOP_copy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_copy`, the planned loop offset of the kernel `copy`, is N. |
| 84 | `#define LOOP_asmcopy B3_OFFSET` | Only with `-DB3_OFFSET=N`: `LOOP_asmcopy`, the planned loop offset of the kernel `asmcopy`, is N too. |
| 85 | `#else` | Starts the branch for a build without `B3_OFFSET`. |
| 86 | `#define LOOP_copy 36` | `LOOP_copy`: the loop of the kernel `copy` must start at 36 modulo 64. In the CRB binary of `bwx8` the loop of `k_copy` starts at `0x40e4`, which is 36 modulo 64 [Ref1]. |
| 87 | `#define LOOP_asmcopy 52` | `LOOP_asmcopy`: the loop of the kernel `asmcopy` must start at 52 modulo 64. In the CRB binary of `bwx8` the loop of `k_asmcopy` starts at `0x46b4`, which is 52 modulo 64 [Ref1]. |
| 88 | `#endif` | Ends the `#ifdef` of line 82. |
| 89 | `#define LOOP_asmcopy_c 52` | `LOOP_asmcopy_c`: 52 modulo 64, the planned loop offset of the three kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg` (lines 114 to 122). `B3_OFFSET` does not change it. |
| 90 | `#ifndef HEAD_copy` | Compiles line 91 only when the build command has not defined `HEAD_copy`. Every value up to line 167 has this pattern of three lines: a default that a `-D` option of the build can replace. |
| 91 | `#define HEAD_copy 4` | `HEAD_copy`: 4 bytes of code, which is one instruction, stand between the start of `k_copy` and the start of its loop. The listing of the CRB build of `bwx8` shows this distance [Ref1]. |
| 92 | `#endif` | Ends the `#ifndef` of line 90. |
| 93 | `#ifndef HEAD_asmcopy` | Compiles line 94 only when the build command has not defined `HEAD_asmcopy`. |
| 94 | `#define HEAD_asmcopy 20` | `HEAD_asmcopy`: 20 bytes of code, which are 5 instructions, stand before the loop of `k_asmcopy`. The listing of the CRB build of `bwx8` shows them: 4 `stp` instructions that save the registers `d8` to `d15`, and the `add` that computes the end address [Ref1]. |
| 95 | `#endif` | Ends the `#ifndef` of line 93. |
| 96 | `#ifndef HEAD_asmcopy_c` | Compiles line 97 only when the build command has not defined `HEAD_asmcopy_c`. |
| 97 | `#define HEAD_asmcopy_c 4` | `HEAD_asmcopy_c`: 4 bytes of code stand before the loop of `k_asmcopy_c`. The listing of the CRB build of `bwx8` shows this distance [Ref1]. |
| 98 | `#endif` | Ends the `#ifndef` of line 96. |
| 99 | `#ifndef HEAD_asmcopy_c_add` | Compiles line 100 only when the build command has not defined `HEAD_asmcopy_c_add`. |
| 100 | `#define HEAD_asmcopy_c_add 4` | `HEAD_asmcopy_c_add`: 4 bytes of code stand before the loop of `k_asmcopy_c_add`. The listing of the CRB build of `bwx8` shows this distance [Ref1]. |
| 101 | `#endif` | Ends the `#ifndef` of line 99. |
| 102 | `#ifndef HEAD_asmcopy_c_reg` | Compiles line 103 only when the build command has not defined `HEAD_asmcopy_c_reg`. |
| 103 | `#define HEAD_asmcopy_c_reg 20` | `HEAD_asmcopy_c_reg`: 20 bytes of code stand before the loop of `k_asmcopy_c_reg`. This kernel saves `d8` to `d15`, as `asmcopy` does. The listing of the CRB build of `bwx8` shows this distance [Ref1]. |
| 104 | `#endif` | Ends the `#ifndef` of line 102. |
| 105 | `#ifndef PAD_copy` | Compiles line 106 only when the build command has not defined `PAD_copy`. |
| 106 | `#define PAD_copy PADOF(LOOP_copy, HEAD_copy)` | `PAD_copy`: `PADOF` (line 80) computes it from the two values above. With the defaults it is (36 - 4) modulo 64 = 32 bytes. In the CRB binary of `bwx8` the function `k_copy` starts at `0x40e0`, which is 32 modulo 64 [Ref1]. |
| 107 | `#endif` | Ends the `#ifndef` of line 105. |
| 108 | `#ifndef PAD_asmcopy` | Compiles line 109 only when the build command has not defined `PAD_asmcopy`. |
| 109 | `#define PAD_asmcopy PADOF(LOOP_asmcopy, HEAD_asmcopy)` | `PAD_asmcopy`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx8` the function `k_asmcopy` starts at `0x46a0`, which is 32 modulo 64 [Ref1]. |
| 110 | `#endif` | Ends the `#ifndef` of line 108. |
| 111 | `#ifndef PAD_asmcopy2` | Compiles line 112 only when the build command has not defined `PAD_asmcopy2`. |
| 112 | `#define PAD_asmcopy2 PAD_asmcopy` | `PAD_asmcopy2`: the A/A copy `asmcopy2` takes the pad of its original `asmcopy`. With the defaults that is 32 bytes. |
| 113 | `#endif` | Ends the `#ifndef` of line 111. |
| 114 | `#ifndef PAD_asmcopy_c` | Compiles line 115 only when the build command has not defined `PAD_asmcopy_c`. |
| 115 | `#define PAD_asmcopy_c PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c)` | `PAD_asmcopy_c`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx8` the function `k_asmcopy_c` starts at `0x4830`, which is 48 modulo 64 [Ref1]. |
| 116 | `#endif` | Ends the `#ifndef` of line 114. |
| 117 | `#ifndef PAD_asmcopy_c_add` | Compiles line 118 only when the build command has not defined `PAD_asmcopy_c_add`. |
| 118 | `#define PAD_asmcopy_c_add PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_add)` | `PAD_asmcopy_c_add`: with the defaults it is (52 - 4) modulo 64 = 48 bytes. In the CRB binary of `bwx8` the function `k_asmcopy_c_add` starts at `0x48f0`, which is 48 modulo 64 [Ref1]. |
| 119 | `#endif` | Ends the `#ifndef` of line 117. |
| 120 | `#ifndef PAD_asmcopy_c_reg` | Compiles line 121 only when the build command has not defined `PAD_asmcopy_c_reg`. |
| 121 | `#define PAD_asmcopy_c_reg PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_reg)` | `PAD_asmcopy_c_reg`: with the defaults it is (52 - 20) modulo 64 = 32 bytes. In the CRB binary of `bwx8` the function `k_asmcopy_c_reg` starts at `0x49a0`, which is 32 modulo 64 [Ref1]. |
| 122 | `#endif` | Ends the `#ifndef` of line 120. |
| 123 | `#ifndef PAD_read` | Compiles line 124 only when the build command has not defined `PAD_read`. |
| 124 | `#define PAD_read 32` | `PAD_read` = 32: the new read kernel `k_read` starts at 32 modulo 64. In the CRB binary of `bwx8` it starts at the address `0x4020`, which is 32 modulo 64 [Ref1]. |
| 125 | `#endif` | Ends the `#ifndef` of line 123. |
| 126 | `#ifndef PAD_write` | Compiles line 127 only when the build command has not defined `PAD_write`. |
| 127 | `#define PAD_write 0` | `PAD_write` = 0: `k_write`, the function of the first touch, starts at 0 modulo 64. In the CRB binary of `bwx8` it starts at the address `0x4080` [Ref1]. |
| 128 | `#endif` | Ends the `#ifndef` of line 126. |
| 129 | `#ifndef PAD_asmread` | Compiles line 130 only when the build command has not defined `PAD_asmread`. |
| 130 | `#define PAD_asmread 0` | `PAD_asmread` = 0: `k_asmread` starts at 0 modulo 64. In the CRB binary of `bwx8` it starts at the address `0x4140` [Ref1]. |
| 131 | `#endif` | Ends the `#ifndef` of line 129. |
| 132 | `#ifndef PAD_asmread2` | Compiles line 133 only when the build command has not defined `PAD_asmread2`. |
| 133 | `#define PAD_asmread2 PAD_asmread` | `PAD_asmread2`: the A/A copy `asmread2` takes the pad of `asmread`, which is 0 bytes. |
| 134 | `#endif` | Ends the `#ifndef` of line 132. |
| 135 | `#ifndef PAD_asmwrite` | Compiles line 136 only when the build command has not defined `PAD_asmwrite`. |
| 136 | `#define PAD_asmwrite 32` | `PAD_asmwrite` = 32: `k_asmwrite` starts at 32 modulo 64. |
| 137 | `#endif` | Ends the `#ifndef` of line 135. |
| 138 | `#ifndef PAD_asmwrite2` | Compiles line 139 only when the build command has not defined `PAD_asmwrite2`. |
| 139 | `#define PAD_asmwrite2 PAD_asmwrite` | `PAD_asmwrite2`: the A/A copy `asmwrite2` takes the pad of `asmwrite`, which is 32 bytes. |
| 140 | `#endif` | Ends the `#ifndef` of line 138. |
| 141 | `#ifndef PAD_oldread` | Compiles line 142 only when the build command has not defined `PAD_oldread`. |
| 142 | `#define PAD_oldread 0` | `PAD_oldread` = 0: the old read kernel `k_oldread` starts at 0 modulo 64. In the CRB binary of `bwx8` it starts at the address `0x3c80` [Ref1]. |
| 143 | `#endif` | Ends the `#ifndef` of line 141. |
| 144 | `#ifndef PAD_oldread2` | Compiles line 145 only when the build command has not defined `PAD_oldread2`. |
| 145 | `#define PAD_oldread2 PAD_oldread` | `PAD_oldread2`: the A/A copy `oldread2` takes the pad of `oldread`, which is 0 bytes. |
| 146 | `#endif` | Ends the `#ifndef` of line 144. |
| 147 | `#ifndef PAD_oldwrite` | Compiles line 148 only when the build command has not defined `PAD_oldwrite`. |
| 148 | `#define PAD_oldwrite 32` | `PAD_oldwrite` = 32: `k_oldwrite` starts at 32 modulo 64. |
| 149 | `#endif` | Ends the `#ifndef` of line 147. |
| 150 | `#ifndef PAD_oldcopy` | Compiles line 151 only when the build command has not defined `PAD_oldcopy`. |
| 151 | `#define PAD_oldcopy 32` | `PAD_oldcopy` = 32: `k_oldcopy` starts at 32 modulo 64. |
| 152 | `#endif` | Ends the `#ifndef` of line 150. |
| 153 | `#ifndef PAD_read_nop4` | Compiles line 154 only when the build command has not defined `PAD_read_nop4`. |
| 154 | `#define PAD_read_nop4 PAD_asmread` | `PAD_read_nop4`: the kernel `read_nop4` takes the pad of `asmread`, which is 0 bytes. |
| 155 | `#endif` | Ends the `#ifndef` of line 153. |
| 156 | `#ifndef PAD_read_nop8` | Compiles line 157 only when the build command has not defined `PAD_read_nop8`. |
| 157 | `#define PAD_read_nop8 PAD_asmread` | `PAD_read_nop8`: the kernel `read_nop8` takes the pad of `asmread`, which is 0 bytes. |
| 158 | `#endif` | Ends the `#ifndef` of line 156. |
| 159 | `#ifndef PAD_read_nop16` | Compiles line 160 only when the build command has not defined `PAD_read_nop16`. |
| 160 | `#define PAD_read_nop16 PAD_asmread` | `PAD_read_nop16`: the kernel `read_nop16` takes the pad of `asmread`, which is 0 bytes. |
| 161 | `#endif` | Ends the `#ifndef` of line 159. |
| 162 | `#ifndef PAD_read_nop32` | Compiles line 163 only when the build command has not defined `PAD_read_nop32`. |
| 163 | `#define PAD_read_nop32 PAD_asmread` | `PAD_read_nop32`: the kernel `read_nop32` takes the pad of `asmread`, which is 0 bytes. |
| 164 | `#endif` | Ends the `#ifndef` of line 162. |
| 165 | `#ifndef PAD_read_sparse` | Compiles line 166 only when the build command has not defined `PAD_read_sparse`. |
| 166 | `#define PAD_read_sparse PAD_asmread` | `PAD_read_sparse`: the kernel `read_sparse` takes the pad of `asmread`, which is 0 bytes. |
| 167 | `#endif` | Ends the `#ifndef` of line 165. |

### Kernel types and one entry of the `--seq` list (lines 169 to 179)

| Line | Source | Explanation |
|---:|---|---|
| 169 | `enum ktype { T_READ, T_WRITE, T_COPY, T_OLDREAD };` | `enum ktype`: the four kernel types `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD`. The function `call` (line 838) chooses the argument list of a kernel by its type. |
| 170 | `typedef void (*read_fn)(const uint64_t *, size_t);` | `read_fn`: the function type of a read kernel (type `T_READ`). The kernel gets the start address and the number of 8-byte words. It returns nothing. |
| 171 | `typedef uint64_t (*oldread_fn)(const uint64_t *, size_t);` | `oldread_fn`: the function type of an old read kernel (type `T_OLDREAD`). The kernel gets the same two arguments and returns a 64-bit sum. |
| 172 | `typedef void (*write_fn)(uint64_t *, size_t, uint64_t);` | `write_fn`: the function type of a write kernel (type `T_WRITE`). The kernel gets the start address, the number of 8-byte words and the 64-bit value to store. |
| 173 | `typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);` | `copy_fn`: the function type of a copy kernel (type `T_COPY`). The kernel gets the destination address, the source address and the number of 8-byte words. `restrict` tells the compiler that the two ranges do not overlap. |
| 175 | `struct entry {` | Starts `struct entry`: one entry of the `--seq` list. |
| 176 | `    int k;          /* index into kernels[] */` | `k`: the index of the kernel in the kernel table `kernels[]` (line 821). |
| 177 | `    uint64_t bytes; /* 0 until main() replaces it by --bytes */` | `bytes`: the size of the range that the kernel works on, in bytes. It is 0 when the entry has no `@SIZE` part. `main` then sets it to the `--bytes` value (lines 2146 to 2147). |
| 178 | `};` | Ends `struct entry`. |

### The settings structure `cfg` (lines 180 to 199)

| Line | Source | Explanation |
|---:|---|---|
| 180 | `static struct {` | Starts the structure `cfg`. It holds the settings of the process. The code that reads the arguments fills it. |
| 181 | `    int threads;` | `threads`: the number of worker threads (`--threads`). |
| 182 | `    int ncpus;` | `ncpus`: the number of entries of `cpus`. |
| 183 | `    int cpus[MAX_CPUS];` | `cpus`: the CPU list of `--cpus`, in the order of the list. `parse_cpus` (line 304) fills it. |
| 184 | `    uint64_t bytes;` | `bytes`: the value of `--bytes` in bytes. It is the range of each buffer that the program uses: the first touch writes this many bytes (line 993), and no `--seq` entry may be larger (line 2148). The mapped buffer is this value rounded up to a multiple of 2 MiB (line 344). |
| 185 | `    double min_s;` | `min_s`: the `--min-ms` value in seconds. With `--stop common` the deadline of an interval is this long after its common start (line 2218). With `--stop pass` a thread runs at least this long (line 1062). |
| 186 | `    int use_thp;` | `use_thp`: 1 when the program asks Linux for 2 MiB pages (transparent huge pages) for the buffers. The option `--no-thp` sets it to 0. |
| 187 | `    struct entry seq[MAX_SEQ];` | `seq`: the kernel list of `--seq`, one `struct entry` per kernel. |
| 188 | `    int nseq;` | `nseq`: the number of entries of `seq`. |
| 189 | `    int rounds;` | `rounds`: how many times the list runs (`--rounds`). |
| 190 | `    int stop_common;  /* --stop common */` | `stop_common`: 1 with `--stop common`. With this stop rule all threads of an interval get the same deadline. |
| 191 | `    int start_offset; /* --start offset */` | `start_offset`: 1 with `--start offset`. Then the place in its buffer at which a thread starts an interval depends on the number of the thread (line 1009). The option chooses a place in the buffer. It does not set the start time of an interval. |
| 192 | `    int two_buffers;  /* buffer b exists: --two-buffers, or a copy kernel in the sequence */` | `two_buffers`: 1 when each thread has a second buffer `b`. The option `--two-buffers` sets it. `main` also sets it when the list holds a copy kernel (lines 2153 to 2154). |
| 193 | `    int count;        /* --count */` | `count`: 1 with `--count`. Then each thread opens hardware counters and reads them before and after each interval. |
| 194 | `    long pmu_type;    /* --pmu-type: the "type" field of perf_event_attr */` | `pmu_type`: the value of `--pmu-type`. It goes into the field `type` of the structure `perf_event_attr` (line 936). The field tells Linux which counter hardware to use. |
| 195 | `    int nev;` | `nev`: the number of counter events of `--events`. |
| 196 | `    char ev_name[MAX_EV][32];` | `ev_name`: the names of the events, at most 31 characters each. |
| 197 | `    uint64_t ev_code[MAX_EV];` | `ev_code`: the codes of the events. A code goes into the field `config` of `perf_event_attr` (line 938). |
| 198 | `} cfg = { .threads = 1, .min_s = 0.5, .use_thp = 1, .rounds = 1, .pmu_type = -1 };` | Ends the structure and sets the defaults: 1 thread, 0.5 s per interval, a request for 2 MiB pages, 1 round and no PMU type (the value -1). Every other field starts at 0. |

### Structures `page`, `counts`, `result` and `thread` (lines 200 to 231)

| Line | Source | Explanation |
|---:|---|---|
| 200 | `struct page {` | Starts `struct page`: the page state of one buffer. |
| 201 | `    long kb_total, kb_huge; /* -1: no exact entry in /proc/self/smaps */` | `kb_total`: the size of the mapping of the buffer. `kb_huge`: the part of it that lies on 2 MiB pages. Both are in kB (1 kB is 1024 bytes here). `read_smaps` (line 862) fills them. Comment: -1 means that the Linux file `/proc/self/smaps` has no exact entry for the buffer. Such a value is printed as `NA`. |
| 202 | `};` | Ends `struct page`. |
| 204 | `struct counts {` | Starts `struct counts`: one reading of the counters of a thread. |
| 205 | `    uint64_t cpu_ns;              /* CLOCK_THREAD_CPUTIME_ID */` | `cpu_ns`: the CPU time that the thread has used, in ns. The Linux clock `CLOCK_THREAD_CPUTIME_ID` gives it (line 959). |
| 206 | `    uint64_t enabled, running;    /* of the counter group */` | `enabled` and `running`: two times of the counter group in ns. They say how long the counters were enabled and how long they really counted. |
| 207 | `    uint64_t val[MAX_EV];` | `val`: one count per event that opened. |
| 208 | `};` | Ends `struct counts`. |
| 210 | `/* One thread, one interval. Written by the worker between the start barrier` | Comment: the structure below holds the result of one thread for one interval. The worker writes it after the start barrier of the interval. The start barrier is the barrier wait that stands before the timed interval (line 1022). The timed interval of a thread does not start at this barrier. It starts later, at the clock read `t0` of the thread (line 1035). |
| 211 | ` * and the end barrier of the interval; read by main() after the end barrier. */` | Comment: the worker writes it before the end barrier of the interval, and `main` reads it after that barrier. In the code the worker stores the structure at line 1073, before its barrier wait of line 1074. `main` reads it after its barrier wait of line 2221. So the two threads never use it at the same time. |
| 212 | `struct result {` | Starts `struct result`. |
| 213 | `    uint64_t bytes;` | `bytes`: the bytes that the thread counted in the interval (line 1068). |
| 214 | `    int64_t t_sched, t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_sched`: the common start time. `t_start`: the start clock read `t0` of the thread. `t_end`: its last clock read `t1`. All three are values of the clock `CLOCK_MONOTONIC` in ns (lines 1069 to 1071). With `--stop pass` there is no common start, and `t_sched` gets the value of `t0`. |
| 215 | `    int late;` | `late`: the late flag. It is 1 when `t0` of the thread was more than `LATE_NS` after the common start (line 1072). |
| 216 | `    struct page pg[2]; /* one-thread process only: read by the worker before the interval */` | `pg`: the page state of the buffers `a` and `b`. Comment: only a process with one thread uses it. There the worker reads the page state before the interval (lines 1017 to 1021). |
| 217 | `    long long vm[4];` | `vm`: four counters of the Linux file `/proc/vmstat` (line 892). As for `pg`, only the worker of a process with one thread fills it. |
| 218 | `    struct counts c0, c1;` | `c0` and `c1`: the counter readings before `t0` (lines 1032 to 1033) and after the last `t1` (lines 1065 to 1066). |
| 219 | `};` | Ends `struct result`. |
| 221 | `struct thread {` | Starts `struct thread`: one record per worker. |
| 222 | `    int idx;` | `idx`: the number of the thread, counted from 0 (line 2167). |
| 223 | `    int cpu;` | `cpu`: the CPU that the thread pins itself to, or -1 without `--cpus` (line 2168). |
| 224 | `    uint64_t *a, *b;` | `a`: the buffer of the thread. `b`: the second buffer, which only a copy kernel or `--two-buffers` needs. Without it `b` stays `NULL`. |
| 225 | `    int group_fd;      /* leader of the counter group, -1 if no event opened */` | `group_fd`: the file descriptor of the leader of the counter group. A file descriptor is the number that Linux returns for an open object. Comment: it is -1 when no event opened. `open_counters` (line 929) sets it. |
| 226 | `    int ev_pos[MAX_EV]; /* position of the event in the group read, -1 if it did not open */` | `ev_pos`: for each event its position among the values of a group read. Comment: -1 when the event did not open. |
| 227 | `    int nopen;` | `nopen`: the number of events that opened. |
| 228 | `    struct result res;` | `res`: the result of the last interval of this thread. |
| 229 | `    pthread_t tid;` | `tid`: the thread handle that `pthread_create` returns (line 2169). |
| 230 | `};` | Ends `struct thread`. |

### Global variables: the barrier, the base time and the common start (lines 232 to 242)

| Line | Source | Explanation |
|---:|---|---|
| 232 | `static pthread_barrier_t bar;` | `bar`: the barrier. A thread that calls `pthread_barrier_wait` on it blocks until all workers and the main thread have called it. `main` creates it for the number of workers plus 1 (line 2162). |
| 233 | `static int64_t t_base_ns; /* clock at process start: printed times are relative to it */` | `t_base_ns`: the clock value at the process start (line 2065). Comment: the printed times are relative to it. |
| 234 | `static long page_bytes;` | `page_bytes`: the page size that Linux reports, in bytes (line 2066). `alloc_buf` uses it (line 358). |
| 236 | `/* --stop common (handoff B.4). gen only grows. main() stores the two times` | Comment: the three variables below belong to `--stop common`. The comment cites section B.4 of the file `handoff.md`, the specification of the first runner. `gen` only grows. |
| 237 | ` * before it increments gen, so a worker that sees the new gen reads the new` | Comment: `main` stores the two times before it adds 1 to `gen` (lines 2217 to 2219). A worker first waits for the new value of `gen` (line 1024). |
| 238 | ` * times. */` | Comment: then the worker loads the two times (lines 1026 to 1027). So it never uses the times of the interval before. |
| 239 | `static _Atomic uint64_t gen;` | `gen`: an atomic counter of intervals. It starts at 0. `_Atomic` makes every load and every store of the variable one indivisible step. |
| 240 | `static _Atomic int64_t t_sched_ns;` | `t_sched_ns`: the common start time of the coming interval, as a value of the clock `CLOCK_MONOTONIC` in ns. With `--stop common` every worker waits until the clock reaches this time (line 1028). The timed interval of a worker starts after that, at its own clock read `t0` (line 1035). |
| 241 | `static _Atomic int64_t deadline_ns;` | `deadline_ns`: the common deadline of the coming interval: the common start time plus the `--min-ms` value (line 2218). With `--stop common` a worker ends its timed interval at its first clock read `t1` at or after this deadline (lines 1047 to 1048). So each worker finishes the chunk that it is in. |

### Function `now_ns`: read the clock (lines 243 to 249)

| Line | Source | Explanation |
|---:|---|---|
| 243 | `static int64_t now_ns(void)` | Starts the function `now_ns`. It reads the clock and returns the time in ns. Every time stamp of the program comes from this function. In a timed interval the worker calls it once for the start `t0` (line 1035). With `--stop common` it then calls it once after each chunk for `t1` (line 1047). A chunk is 2 MiB, or the whole range of the `--seq` entry when that is smaller. So one clock read per chunk is inside the timed interval. This is the same for every kernel. |
| 244 | `{` | Opens the body of `now_ns`. |
| 245 | `    struct timespec ts;` | `ts`: a `timespec`, the structure for a time as whole seconds plus ns. |
| 246 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | `clock_gettime` reads the Linux clock `CLOCK_MONOTONIC` into `ts`. This clock cannot be set. It does not jump when the date or the time of the system is changed. |
| 247 | `    return (int64_t)ts.tv_sec * 1000000000L + ts.tv_nsec;` | Returns the seconds times 1000000000 plus the ns part: the time in ns as one 64-bit number. |
| 248 | `}` | Ends the function `now_ns`. |

### Function `parse_bytes`: a size text such as `256M` (lines 250 to 266)

| Line | Source | Explanation |
|---:|---|---|
| 250 | `static uint64_t parse_bytes(const char *s)` | Starts the function `parse_bytes`. It turns a size text such as `256M` into a number of bytes. `main` calls it for `--bytes` (line 2094). `parse_seq` calls it for the `@SIZE` part of a `--seq` entry (line 1111). |
| 251 | `{` | Opens the body of `parse_bytes`. |
| 252 | `    char *end;` | `end`: `strtod` sets it to the first character after the number. |
| 253 | `    double v = strtod(s, &end);` | `strtod` reads a decimal number from the start of the text into `v`. The number may have a fraction, for example `1.5`. |
| 254 | `    double mul = 1;` | `mul`: the factor of the unit letter. It stays 1 when no letter follows the number. |
| 255 | `    switch (*end) {` | Looks at the character after the number. |
| 256 | `    case 'k': case 'K': mul = 1UL << 10; end++; break;` | The letter `k` or `K`: the factor is 1024. `end++` moves `end` to the character after the letter. |
| 257 | `    case 'm': case 'M': mul = 1UL << 20; end++; break;` | The letter `m` or `M`: the factor is 1048576, which is 1 MiB. So the text `256M` gives 256 times 1048576, which is 268435456 bytes. |
| 258 | `    case 'g': case 'G': mul = 1UL << 30; end++; break;` | The letter `g` or `G`: the factor is 1073741824, which is 1024 MiB. |
| 259 | `    }` | Ends the `switch` of line 255. |
| 260 | `    if (end == s \|\| *end != '\0' \|\| v <= 0 \|\| (uint64_t)(v * mul) == 0) { /* 0 bytes after rounding is no size */` | Tests four error cases. The text holds no number (`end == s`). Other text follows the size. The value is 0 or below. The size is 0 bytes after the conversion to a whole number. Comment: 0 bytes after rounding is no size. |
| 261 | `        fprintf(stderr, "bad size: %s\n", s);` | In an error case: prints `bad size:` and the text to stderr, the error output of the program. |
| 262 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 263 | `    }` | Ends the `if` of line 260. |
| 264 | `    return (uint64_t)(v * mul);` | Returns the size in bytes as a whole number. The conversion drops a fraction of a byte. |
| 265 | `}` | Ends the function `parse_bytes`. |

### Function `parse_long`: a whole number inside a range (lines 267 to 280)

| Line | Source | Explanation |
|---:|---|---|
| 267 | `/* A whole number in [lo, hi], with nothing after it. Anything else ends the` | Comment: the function below accepts only a whole number from `lo` to `hi` with no text after it. |
| 268 | ` * program: a malformed value must not run as 0. */` | Comment: any other text ends the program. The reason: a malformed value must not run as the number 0. |
| 269 | `static long parse_long(const char *s, const char *what, long lo, long hi)` | Starts the function `parse_long`. It turns the text `s` into a whole number inside the range `lo` to `hi`. `what` is the name of the option, for the error message. `main` reads `--threads` (allowed 1 to 4096), `--rounds` (1 to 1000000) and `--pmu-type` (0 to 2147483647) with it (line 2089, line 2104, line 2119). |
| 270 | `{` | Opens the body of `parse_long`. |
| 271 | `    char *end;` | `end`: `strtol` sets it to the first character after the number. |
| 272 | `    errno = 0;` | Sets `errno` to 0. `strtol` sets it to an error value when the number does not fit the type `long`. |
| 273 | `    long v = strtol(s, &end, 10);` | `strtol` reads a decimal whole number (base 10) from the start of the text into `v`. |
| 274 | `    if (end == s \|\| *end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi) {` | Tests the error cases: no digit was read, other text follows the number, the number does not fit the type `long`, or it lies outside the range `lo` to `hi`. |
| 275 | `        fprintf(stderr, "bad %s: '%s' (a whole number from %ld to %ld is needed)\n", what, s, lo, hi);` | In an error case: prints `bad`, the option name, the text and the allowed range to stderr. |
| 276 | `        exit(2);` | In an error case: the whole program ends with exit status 2. |
| 277 | `    }` | Ends the `if` of line 274. |
| 278 | `    return v;` | Returns the number. |
| 279 | `}` | Ends the function `parse_long`. |

### Function `restrict_cpus`: no CPU above `MAX_USE_CPU` (lines 281 to 302)

| Line | Source | Explanation |
|---:|---|---|
| 281 | `/* Removes every CPU above MAX_USE_CPU from the allowed set of the calling` | Comment: the function below removes every CPU above `MAX_USE_CPU` from the allowed set of the calling thread. The allowed set is the set of CPUs on which Linux may run the thread. |
| 282 | ` * thread. main() calls it before it starts a thread, so the main thread and` | Comment: `main` calls the function before it starts a thread (line 2068). A new thread takes over the allowed set of the thread that creates it. |
| 283 | ` * every worker (also one without --cpus) stay on the permitted CPUs. */` | Comment: so the main thread and every worker stay on the permitted CPUs. This also holds for a worker of a run without `--cpus`. |
| 284 | `static void restrict_cpus(void)` | Starts the function `restrict_cpus`. |
| 285 | `{` | Opens the body of `restrict_cpus`. |
| 286 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 287 | `    int changed = 0;` | `changed`: becomes 1 when the set held a CPU above the limit. |
| 288 | `    if (sched_getaffinity(0, sizeof set, &set) != 0) {` | `sched_getaffinity` with the first argument 0 reads the allowed set of the calling thread into `set`. A return value other than 0 means that the call failed. |
| 289 | `        perror("sched_getaffinity");` | On failure: `perror` prints the word `sched_getaffinity` and the reason that Linux gave. |
| 290 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 291 | `    }` | Ends the `if` of line 288. |
| 292 | `    for (int c = MAX_USE_CPU + 1; c < CPU_SETSIZE; c++)` | Starts a loop over every CPU number above `MAX_USE_CPU`, up to `CPU_SETSIZE - 1`. `CPU_SETSIZE` is the number of CPUs that the set type of the C library can hold. With the default limit the loop starts at CPU 120. |
| 293 | `        if (CPU_ISSET(c, &set)) {` | Tests whether the set holds the CPU `c`. |
| 294 | `            CPU_CLR(c, &set);` | Removes the CPU `c` from the set. |
| 295 | `            changed = 1;` | Records that the set was changed. |
| 296 | `        }` | Ends the `if` of line 293. |
| 297 | `    if (changed && (CPU_COUNT(&set) == 0 \|\| sched_setaffinity(0, sizeof set, &set) != 0)) {` | Runs only when a CPU was removed. An empty set is an error. If the set is not empty, `sched_setaffinity` passes the smaller set to Linux, and a failed call is an error too. When the process starts with an allowed set that holds no CPU above `MAX_USE_CPU`, `changed` stays 0, and the function changes nothing. |
| 298 | `        fprintf(stderr, "cannot keep the process on CPUs 0-%d\n", MAX_USE_CPU);` | On error: prints `cannot keep the process on CPUs 0-` and the limit to stderr. |
| 299 | `        exit(2);` | On error: the whole program ends with exit status 2. |
| 300 | `    }` | Ends the `if` of line 297. |
| 301 | `}` | Ends the function `restrict_cpus`. |

### Function `parse_cpus`: the value of `--cpus` (lines 303 to 330)

| Line | Source | Explanation |
|---:|---|---|
| 303 | `/* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */` | Comment: three examples of a CPU list: `0-119`, `0,2,4-7` and `0-118:2`. The last one is a range with a stride: every second CPU from 0 to 118. |
| 304 | `static void parse_cpus(char *list)` | Starts the function `parse_cpus`. It turns the value of `--cpus` into the array `cfg.cpus`, in the order of the list. |
| 305 | `{` | Opens the body of `parse_cpus`. |
| 306 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | Starts a loop over the items of the list. `strtok` splits the text at each comma and returns one item per call. It writes into the text to do that. |
| 307 | `        char *e, *e2;` | `e` and `e2`: positions in the item that `strtol` sets. |
| 308 | `        long lo = strtol(tok, &e, 10), hi = lo, step = 1;` | `strtol` reads the first number of the item into `lo`. `hi` starts with the same value and `step` with 1. So an item that is one number names one CPU. |
| 309 | `        if (e != tok && *e == '-') {` | When a number was read and a `-` follows it: the item is a range. |
| 310 | `            hi = strtol(e + 1, &e2, 10);` | Reads the upper bound of the range into `hi`. |
| 311 | `            e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */` | When no digit follows the `-`, `e` is set back to `tok`, and the test of line 317 then rejects the item. If a number was read, `e` moves to the character after it. Comment: the item `0-` has no upper bound. |
| 312 | `            if (e != tok && *e == ':') {` | When the upper bound was read and a `:` follows it: the range has a stride. |
| 313 | `                step = strtol(e + 1, &e2, 10);` | Reads the stride into `step`. |
| 314 | `                e = e2 == e + 1 ? tok : e2;` | When no digit follows the `:`, `e` is set back to `tok`, and the test of line 317 rejects the item. If a number was read, `e` moves to the character after it. |
| 315 | `            }` | Ends the `if` of line 312. |
| 316 | `        }` | Ends the `if` of line 309. |
| 317 | `        if (e == tok \|\| *e != '\0' \|\| lo < 0 \|\| hi < lo \|\| hi > MAX_USE_CPU \|\| step < 1) {` | Rejects an item in six cases: it holds no number, other text follows, the start is negative, the end is below the start, the end is above `MAX_USE_CPU` (119 with the default), or the stride is below 1. |
| 318 | `            fprintf(stderr, "bad cpu list: %s (CPUs 0-%d only)\n", tok, MAX_USE_CPU);` | On such an item: prints `bad cpu list:`, the item and the permitted range to stderr. |
| 319 | `            exit(2);` | On such an item: the whole program ends with exit status 2. |
| 320 | `        }` | Ends the `if` of line 317. |
| 321 | `        for (long c = lo; c <= hi; c += step) {` | Starts a loop over the CPU numbers of the item, from `lo` to `hi` in steps of `step`. |
| 322 | `            if (cfg.ncpus == MAX_CPUS) {` | Tests whether the array `cfg.cpus` is full. It holds at most `MAX_CPUS` entries, which is 1024. |
| 323 | `                fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);` | When the array is full: prints `bad cpu list: more than 1024 cpus` to stderr. |
| 324 | `                exit(2);` | When the array is full: the whole program ends with exit status 2. |
| 325 | `            }` | Ends the `if` of line 322. |
| 326 | `            cfg.cpus[cfg.ncpus++] = (int)c;` | Appends the CPU number to `cfg.cpus` and counts it in `cfg.ncpus`. For example the list `0-63,64-119` gives 120 entries in rising order: `cfg.cpus[i]` is `i`. `main` gives thread `i` the CPU `cfg.cpus[i % cfg.ncpus]` (line 2168). |
| 327 | `        }` | Ends the loop of line 321. |
| 328 | `    }` | Ends the loop of line 306. |
| 329 | `}` | Ends the function `parse_cpus`. |

### Function `pin_cpu`: limit the calling thread to one CPU (lines 331 to 341)

| Line | Source | Explanation |
|---:|---|---|
| 331 | `static void pin_cpu(int cpu)` | Starts the function `pin_cpu`. It limits the calling thread to the CPU with the number `cpu`. A worker of a run with `--cpus` calls it at its start (lines 988 to 989), before it opens its counters and before it maps its buffer. |
| 332 | `{` | Opens the body of `pin_cpu`. |
| 333 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 334 | `    CPU_ZERO(&set);` | Empties the set. |
| 335 | `    CPU_SET(cpu, &set);` | Adds the CPU `cpu` to the set. The set now holds this one CPU. |
| 336 | `    if (sched_setaffinity(0, sizeof set, &set) != 0) {` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed. |
| 337 | `        perror("sched_setaffinity");` | On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave. |
| 338 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 339 | `    }` | Ends the `if` of line 336. |
| 340 | `}` | Ends the function `pin_cpu`. |

### Function `buf_len`: the length of one buffer (lines 342 to 346)

| Line | Source | Explanation |
|---:|---|---|
| 342 | `static size_t buf_len(void)` | Starts the function `buf_len`. It returns the length of one buffer in bytes. |
| 343 | `{` | Opens the body of `buf_len`. |
| 344 | `    return (cfg.bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);` | Returns the `--bytes` value rounded up to a multiple of 2 MiB (`HUGE_BYTES`). The expression adds `HUGE_BYTES - 1` and then clears the low 21 bits. A value of 268435456 bytes (256 MiB) is already 128 times 2 MiB and stays as it is. |
| 345 | `}` | Ends the function `buf_len`. |

### Function `alloc_buf`: map one buffer, aligned to 2 MiB (lines 347 to 368)

| Line | Source | Explanation |
|---:|---|---|
| 347 | `/* The buffer starts at a 2 MiB boundary, at least one page above the start` | Comment: the buffer starts at a 2 MiB boundary. That boundary lies at least one page above the start of the mapping. |
| 348 | ` * of the mapping. The unused parts before and after it are PROT_NONE, so the` | Comment: the unused parts of the mapping before and after the buffer get the access right `PROT_NONE`, which forbids every access. |
| 349 | ` * buffer is one entry of its own in /proc/self/smaps (handoff B.6). */` | Comment: so the buffer is one entry of its own in `/proc/self/smaps`, the Linux file that lists every memory mapping of the process. `read_smaps` (line 862) looks for an entry with exactly the start and the end of the buffer. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. |
| 350 | `static uint64_t *alloc_buf(void)` | Starts the function `alloc_buf`. It maps one buffer and returns its address. Each worker calls it once (line 992). A worker of a run with `--cpus` has pinned itself before this call (lines 988 to 989). A worker that needs the second buffer calls it once more (line 995). |
| 351 | `{` | Opens the body of `alloc_buf`. |
| 352 | `    size_t len = buf_len(), maplen = len + 2 * HUGE_BYTES;` | `len`: the buffer length from `buf_len`. `maplen`: 4 MiB more. The extra 4 MiB make room for the alignment of line 358 and for the two no-access ranges of lines 359 to 360. For a buffer of 256 MiB `len` is 268435456 bytes and `maplen` is 272629760 bytes (260 MiB). |
| 353 | `    uint8_t *raw = mmap(NULL, maplen, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `maplen` bytes of new memory that the process may read and write (`PROT_READ \| PROT_WRITE`). `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process only, and no file backs it. `NULL`: Linux chooses the address. `-1` and `0` are the two file arguments, which are not used here. The call does not yet give physical memory to the pages. That happens at the first touch (line 993). |
| 354 | `    if (raw == MAP_FAILED) {` | Tests whether `mmap` failed. |
| 355 | `        perror("mmap");` | On failure: `perror` prints the word `mmap` and the reason that Linux gave. |
| 356 | `        exit(2);` | On failure: the whole program ends with exit status 2. |
| 357 | `    }` | Ends the `if` of line 354. |
| 358 | `    uint8_t *p = (uint8_t *)(((uintptr_t)raw + (size_t)page_bytes + HUGE_BYTES - 1) & ~(uintptr_t)(HUGE_BYTES - 1));` | `p`: the buffer start. It is the first 2 MiB boundary that lies at least one page above the start `raw` of the mapping. The expression adds the page size `page_bytes` and `HUGE_BYTES - 1` to `raw` and then clears the low 21 bits. The buffer is the range from `p` to `p + len`. So it starts at an address that is a multiple of 2 MiB. |
| 359 | `    if (mprotect(raw, (size_t)(p - raw), PROT_NONE) != 0 \|\|` | `mprotect` with `PROT_NONE` forbids every access to the unused range before the buffer, from `raw` to `p`. |
| 360 | `        mprotect(p + len, (size_t)(raw + maplen - (p + len)), PROT_NONE) != 0)` | Continues the test of line 359: the same for the unused range after the buffer, from `p + len` to the end of the mapping. This second call runs only when the first one succeeded. |
| 361 | `        perror("mprotect of the guard ranges (continuing; page state will be NA)");` | When one of the two calls failed: `perror` prints a message which says that the run continues and that the page state will be `NA`. The program does not stop. The message goes to stderr, the error output of the program. |
| 362 | `    /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp` | Comment: the advice `MADV_NOHUGEPAGE` matters on a host whose setting for transparent huge pages is `always`. |
| 363 | `     * would still get 2 MiB pages. */` | Comment: without that advice a run with `--no-thp` would still get 2 MiB pages on such a host. |
| 364 | `    if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)` | `madvise` gives Linux advice about the buffer range. With `cfg.use_thp` set, the advice is `MADV_HUGEPAGE`: use 2 MiB pages for this range. With `--no-thp` it is `MADV_NOHUGEPAGE`: do not use them. The function does not test whether the buffer got 2 MiB pages. The P rows show how much of each buffer lies on 2 MiB pages (line 921). |
| 365 | `        perror("madvise (continuing)");` | When `madvise` failed: `perror` prints `madvise (continuing)` and the reason that Linux gave. The run continues. |
| 366 | `    return (uint64_t *)p;` | Returns the buffer start as a pointer to 8-byte words. No line of this file unmaps a buffer. So the buffer stays mapped until the process ends. |
| 367 | `}` | Ends the function `alloc_buf`. |

### Old read kernel: the macro `DEF_OLDREAD` and the kernels `oldread` and `oldread2` (lines 369 to 392)

| Line | Source | Explanation |
|---:|---|---|
| 369 | `/*` | Opens the comment about the old kernels. |
| 370 | ` * Old kernels: k_read, k_write and k_copy of bandwidth.orig.c (the benchmark` | Comment: the old kernels below are the functions `k_read`, `k_write` and `k_copy` of the file `bandwidth.orig.c`. |
| 371 | ` * until 2026-11-13), renamed. The old comment of k_read was: "16 independent` | Comment: `bandwidth.orig.c` was the benchmark source until 2026-11-13. Here its three kernels have the new names `k_oldread`, `k_oldwrite` and `k_oldcopy`. `bw_old` is the benchmark binary of 2026-11-13 that was built from that file. Apart from absolute addresses, the machine code of `k_oldread` in the CRB build of `bwx8` has the same instruction text as `k_read` of `bw_old` [Ref1] [Ref3]. A quotation of the old comment of `k_read` starts in this line. |
| 372 | ` * accumulators keep the loop load-bound: on 128-bit NEON gcc folds them into` | Comment, quotation: 16 separate running sums (accumulators) keep the loop load-bound. This means that the loads and not the adds should limit the speed of the loop. This is a statement of the old comment. It is not a measured result. |
| 373 | ` * 8 vector chains, enough to hide a 2-cycle add latency; on AVX-512 they` | Comment, quotation: with the 128-bit NEON registers gcc puts the 16 sums into 8 vector registers. Each register is a chain of adds of its own. The old comment says that 8 chains are enough for an add that takes 2 clock cycles: the adds then do not limit the speed of the loop. The listing of the CRB binary of `bwx8` confirms the 8 registers: the sums are in the registers `v24` to `v31` [Ref1]. |
| 374 | ` * become 2 zmm chains." oldread2 is the A/A copy: the same source under a` | Comment: the end of the quotation: with AVX-512, a vector instruction set of x86 processors, the sums become 2 chains in 512-bit registers. The next sentence: `oldread2` is the A/A copy, the same source under a second name. |
| 375 | ` * second name (the build uses -fno-ipa-icf, so gcc keeps both).` | Comment: the build uses the gcc flag `-fno-ipa-icf`. With it gcc keeps both functions. The flag is in the build record of CRB for `bwx8` [Ref2]. |
| 376 | ` */` | Ends the comment. |
| 377 | `#define DEF_OLDREAD(name) \` | Starts the macro `DEF_OLDREAD(name)`. It writes `PLACE(name)` and one function: the source text of the old read kernel. The backslash at the end of each line continues the macro on the next line. |
| 378 | `    PLACE(name); \` | `PLACE` (line 79) adds the pad of this kernel. So the function starts at the value of `PAD_` plus `name`, modulo 64. |
| 379 | `    __attribute__((noinline)) static uint64_t k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the macro argument into the function name. `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns a 64-bit sum. `noinline`: gcc must keep the function separate from its caller. The listing of the CRB build of `bwx8` shows `k_oldread` as a function of its own [Ref1]. With `--stop common` one call in a timed interval gets one chunk of 2 MiB: `n` is then 262144 words (line 1042). The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1016). |
| 380 | `    { \` | Opens the body of the kernel function. |
| 381 | `        uint64_t s[16] = { 0 }; \` | `s`: the 16 running sums. All start at 0. Machine code of `k_oldread` in `bwx8`, once per call and before the loop: 4 `stp` instructions write 128 B of zeros to the stack (each stores two 16-byte registers), and the 8 registers `v24` to `v31` are set to 0. During the loop these 8 registers hold the 16 sums, two sums per register [Ref1]. |
| 382 | `        for (size_t i = 0; i < n; i += 16) \` | The outer loop. One pass takes 16 words, which are 128 B. Machine code of `k_oldread` in `bwx8`: gcc did not unroll this loop. One pass of the machine loop is one pass of this source loop. Before the loop the code computes the number of passes into the register `x2` [Ref1]. |
| 383 | `            for (int j = 0; j < 16; j++) \` | The inner loop over the 16 words of the block. Machine code of `k_oldread` in `bwx8`: gcc compiled this loop to vector instructions. No loop over `j` is left [Ref1]. |
| 384 | `                s[j] += a[i + j]; \` | Adds word `j` of the block to sum `j`. So every loaded word is an input of one add. Machine code of `k_oldread` in `bwx8`, one loop pass of 16 instructions for 128 B [Ref1]: 4 `ldp` loads of 32 B each, at the byte offsets 0, 32, 64 and 96 from the read position. 8 vector adds: each one adds one loaded register to one of the sum registers `v24` to `v31` and so performs two of the 16 adds of the source. `add x0, x0, #0x80` moves the read position by 128 B. `add x1, x1, #0x1` counts the pass. `cmp` and `b.cc` branch back while the count is below the number of passes. No instruction of the loop stores to memory. |
| 385 | `        uint64_t sum = 0; \` | `sum`: the total of the 16 sums. It starts at 0. |
| 386 | `        for (int j = 0; j < 16; j++) \` | A loop over the 16 sums. It runs once per call, after the read loop. |
| 387 | `            sum += s[j]; \` | Adds the 16 sums into one value. Machine code of `k_oldread` in `bwx8`, once per call [Ref1]: the 8 sum registers are stored to the stack and loaded back. Then 7 vector adds and one `addp` add them into one number. `addp` adds the two 64-bit halves of one register. |
| 388 | `        return sum; \` | Returns the total. Machine code of `k_oldread` in `bwx8`: `fmov x0, d31` copies the result into the return register `x0` [Ref1]. `call` stores the returned value into the volatile variable `sink` (line 847). So the sum is used, and the compiler cannot remove the loads and the adds as unused work. gcc also added a stack check to this function. It saves a guard value on the stack at the start and compares it before the return. A changed value leads to a call of `__stack_chk_fail` [Ref1]. |
| 389 | `    }` | Ends the kernel function and the macro. In `bwx8` one call of `k_oldread` runs 53 instructions outside the loop [Ref1]. One chunk of 2 MiB is 16384 loop passes, which are 262144 instructions. |
| 390 | `DEF_OLDREAD(oldread)` | Creates the function `k_oldread`. It is the kernel `oldread` of `--seq`, the old read kernel, with the type `T_OLDREAD` in the kernel table (line 825). In the CRB binary of `bwx8` the function starts at the address `0x3c80` and its loop at `0x3ce8`, which is 40 modulo 64 [Ref1]. For 256 B it runs 2 loop passes: 32 instructions with 8 `ldp` loads, 16 vector adds and 2 branches. The new read kernel runs 11 instructions for 256 B (line 443). Apart from absolute addresses, the machine code of `k_oldread` has the same instruction text as `k_read` of the binary `bw_old` [Ref3]. |
| 391 | `DEF_OLDREAD(oldread2)` | Creates `k_oldread2`, the A/A copy of the old read kernel. The listing of the CRB build of `bwx8` shows the same instruction text for both functions [Ref1]. |

### Old write kernel `oldwrite` and old copy kernel `oldcopy` (lines 393 to 406)

| Line | Source | Explanation |
|---:|---|---|
| 393 | `PLACE(oldwrite);` | `PLACE` adds the pad of the kernel `oldwrite`. `PAD_oldwrite` is 32 (line 148). |
| 394 | `__attribute__((noinline)) static void k_oldwrite(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_oldwrite`, the kernel `oldwrite`: the write kernel of the old benchmark source. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. The first touch of a buffer uses `k_write` (line 447). |
| 395 | `{` | Opens the body of `k_oldwrite`. |
| 396 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 397 | `        a[i] = v;` | Stores `v` to word `i`: one store of 8 B per pass of the source loop. Machine code in the CRB binary of `bwx8`: gcc compiled the loop to instructions of SVE, the scalable vector extension of Arm. One loop pass has 4 instructions with one `st1d` store, which writes one vector of 8-byte words. The program reads the number of words per vector at run time with the instruction `cntd`. The listing does not give this number [Ref1]. |
| 398 | `}` | Ends the function `k_oldwrite`. |
| 400 | `PLACE(oldcopy);` | `PLACE` adds the pad of the kernel `oldcopy`. `PAD_oldcopy` is 32 (line 151). |
| 401 | `__attribute__((noinline)) static void k_oldcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_oldcopy`, the kernel `oldcopy`: the copy kernel of the old benchmark source. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 402 | `{` | Opens the body of `k_oldcopy`. |
| 403 | `    for (size_t i = 0; i < n; i++)` | A plain C loop over the `n` words. The source has no unrolling: one pass handles one word of 8 B. |
| 404 | `        d[i] = s[i];` | Loads word `i` of the source and stores it to word `i` of the destination. The loaded value is stored and has no other use. Machine code in the CRB binary of `bwx8`: SVE instructions, as in `k_oldwrite`. One loop pass has 5 instructions with one `ld1d` load and one `st1d` store of one vector of 8-byte words [Ref1]. |
| 405 | `}` | Ends the function `k_oldcopy`. |

### AArch64 branch and the function `k_read`: the new read kernel (lines 407 to 445)

| Line | Source | Explanation |
|---:|---|---|
| 407 | `#if defined(__aarch64__)` | The lines from here to the `#else` of line 767 are compiled only for AArch64. The lines from that `#else` to the `#endif` of line 813 hold the stand-ins for other machines. The CRB build of `bwx8` is an AArch64 build: its listing holds AArch64 instructions such as the `ldp` of `k_read` [Ref1]. So it was compiled from this first branch. |
| 408 | `#define STANDIN 0` | `STANDIN` is 0 in the AArch64 branch: the kernels are the real ones. The program then prints `kernels=aarch64` in its header (line 2181). |
| 409 | `/*` | Opens the comment about the C kernels. |
| 410 | ` * C kernels: unchanged from bench/bandwidth.c. Each iteration moves 256 B as` | Comment: the C kernels below are unchanged from the benchmark source `bandwidth.c` in the folder `bench`. One loop pass moves 256 B. |
| 411 | ` * 16 vectors of 16 B and does no arithmetic on the data. Callers guarantee` | Comment: the 256 B move as 16 vectors of 16 B. The loop does no arithmetic on the data. |
| 412 | ` * n * 8 is a multiple of 256 and non-zero. The empty asm statement of k_read` | Comment: the callers guarantee that the size `n * 8` in bytes is a multiple of 256 and is not 0. `main` checks the sizes (line 2130 and line 2148). A chunk of 2 MiB is a multiple of 256. The sentence about the empty `asm` statement starts here. |
| 413 | ` * and k_copy takes the 16 loaded vectors as inputs in NEON registers ("w"):` | Comment: the empty `asm` statement of `k_read` (lines 438 to 441) and of `k_copy` (lines 496 to 499) takes the 16 loaded vectors as inputs. The letter `w` says that each input must be in a NEON register. |
| 414 | ` * see the comment in bench/bandwidth.c.` | Comment: a comment in the file `bandwidth.c` of the folder `bench` explains this statement. |
| 415 | ` */` | Ends the comment. |
| 416 | `PLACE(read);` | `PLACE(read)` with `PAD_read` = 32 (line 124): the function starts at 32 modulo 64. In the CRB binary of `bwx8` the function `k_read` starts at the address `0x4020` and its loop at `0x4024`, which is 36 modulo 64 [Ref1]. The loop of `k_read` in `bw_new` has the same offset 36 [Ref3]. |
| 417 | `__attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)` | Starts the function `k_read`: the kernel `read` of `--seq`, the new read kernel, with the type `T_READ` in the kernel table (line 823). `a` is the start of the range to read. `n` is the length of the range in 8-byte words. The function returns nothing: it computes no sum. `noinline`: gcc must keep the function separate from its caller. The listing of `bwx8` shows it as a function of 13 instructions [Ref1]. Apart from absolute addresses, its instruction text equals the text of `k_read` in `bw_new`, the benchmark binary of 2026-11-13 with the new kernels [Ref3]. |
| 418 | `{` | Opens the body of `k_read`. With `--stop common` one call of the function in a timed interval gets one chunk of 2 MiB: `n` is then 262144 words (line 1042). The warm-up pass calls the kernel once on the whole range of the `--seq` entry (line 1016). |
| 419 | `    const uint64_t *p = a;` | `p`: the read position. It starts at `a`. |
| 420 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx8`, once per call and before the loop: `add x1, x0, x1, lsl #3`. Before this instruction the register `x0` holds `a` and `x1` holds `n`. After it `x1` holds `end` [Ref1]. |
| 421 | `    do {` | Starts the loop. With `do` the loop body runs once before the first test of the end. So the range must not be empty. |
| 422 | `        uint64x2_t v0 = vld1q_u64(p + 0);` | `vld1q_u64(p + 0)` loads 16 B, which are two 8-byte words, from the read position into the vector `v0`. These are the bytes 0 to 15 of the current block of 256 B. |
| 423 | `        uint64x2_t v1 = vld1q_u64(p + 2);` | Loads the bytes 16 to 31 of the block, 2 words after the read position, into `v1`. Machine code of `bwx8`: gcc joined this load and the load of line 422 into one instruction, `ldp q31, q30, [x0]`, which loads 32 B [Ref1]. |
| 424 | `        uint64x2_t v2 = vld1q_u64(p + 4);` | Loads the bytes 32 to 47 of the block into `v2`. |
| 425 | `        uint64x2_t v3 = vld1q_u64(p + 6);` | Loads the bytes 48 to 63 of the block into `v3`. Machine code of `bwx8` for this load and the load of line 424: `ldp q29, q28, [x0, #32]` [Ref1]. |
| 426 | `        uint64x2_t v4 = vld1q_u64(p + 8);` | Loads the bytes 64 to 79 of the block into `v4`. |
| 427 | `        uint64x2_t v5 = vld1q_u64(p + 10);` | Loads the bytes 80 to 95 of the block into `v5`. Machine code of `bwx8` for this load and the load of line 426: `ldp q27, q26, [x0, #64]` [Ref1]. |
| 428 | `        uint64x2_t v6 = vld1q_u64(p + 12);` | Loads the bytes 96 to 111 of the block into `v6`. |
| 429 | `        uint64x2_t v7 = vld1q_u64(p + 14);` | Loads the bytes 112 to 127 of the block into `v7`. Machine code of `bwx8` for this load and the load of line 428: `ldp q25, q24, [x0, #96]` [Ref1]. |
| 430 | `        uint64x2_t v8 = vld1q_u64(p + 16);` | Loads the bytes 128 to 143 of the block into `v8`. |
| 431 | `        uint64x2_t v9 = vld1q_u64(p + 18);` | Loads the bytes 144 to 159 of the block into `v9`. Machine code of `bwx8` for this load and the load of line 430: `ldp q23, q22, [x0, #128]` [Ref1]. |
| 432 | `        uint64x2_t v10 = vld1q_u64(p + 20);` | Loads the bytes 160 to 175 of the block into `v10`. |
| 433 | `        uint64x2_t v11 = vld1q_u64(p + 22);` | Loads the bytes 176 to 191 of the block into `v11`. Machine code of `bwx8` for this load and the load of line 432: `ldp q21, q20, [x0, #160]` [Ref1]. |
| 434 | `        uint64x2_t v12 = vld1q_u64(p + 24);` | Loads the bytes 192 to 207 of the block into `v12`. |
| 435 | `        uint64x2_t v13 = vld1q_u64(p + 26);` | Loads the bytes 208 to 223 of the block into `v13`. Machine code of `bwx8` for this load and the load of line 434: `ldp q19, q18, [x0, #192]` [Ref1]. |
| 436 | `        uint64x2_t v14 = vld1q_u64(p + 28);` | Loads the bytes 224 to 239 of the block into `v14`. |
| 437 | `        uint64x2_t v15 = vld1q_u64(p + 30);` | Loads the bytes 240 to 255 of the block into `v15`. Machine code of `bwx8` for this load and the load of line 436: `ldp q17, q16, [x0, #224]`. One loop pass has 16 loads in the source and 8 `ldp` loads in the machine code. It reads 256 B, each byte once, in rising address order [Ref1]. |
| 438 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text. It adds no instruction to the loop. It names the loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. A comment in the benchmark source `bandwidth.c` gives the purpose: gcc must have all 16 values in registers at this point, and this keeps gcc from deleting the loads. After this statement nothing uses the values. They are dropped. The listing of `bwx8` shows no add and no other instruction that uses a loaded register [Ref1]. This is the difference to the old read kernel, which adds every loaded word to a sum. |
| 439 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 438: the inputs `v4` to `v7`. |
| 440 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 438: the inputs `v8` to `v11`. |
| 441 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 438: the inputs `v12` to `v15`. The statement ends here. |
| 442 | `        p += 32;` | Moves the read position forward by 32 words, which are 256 B. Machine code of `bwx8`: `add x0, x0, #0x100` [Ref1]. |
| 443 | `    } while (p < end);` | Repeats the loop while the read position is below the end. Machine code of `bwx8`: `cmp x1, x0`, then `b.hi` back to the first `ldp`. One loop pass is 11 instructions for 256 B: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1]. One chunk of 2 MiB is 8192 loop passes, which are 90112 instructions. |
| 444 | `}` | Ends the function `k_read`. Machine code of `bwx8`: one `ret` instruction. gcc used the registers `q16` to `q31` for the loads, and the function saves and restores no register [Ref1]. The AArch64 branch of line 407 continues after this function, up to line 767. |

### Function `k_write`: the NEON write kernel, used for the first touch (lines 446 to 472)

| Line | Source | Explanation |
|---:|---|---|
| 446 | `PLACE(write);` | `PLACE(write)` adds the pad of this kernel. `PAD_write` is 0 (line 127). So the function starts at a multiple of 64 bytes: the address `0x4080` in the listing of the CRB build of `bwx8`. The function stands in the AArch64 branch of line 407, and the CRB binary holds this branch: the listing shows the `dup` and `stp` instructions of this function [Ref1]. |
| 447 | `__attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)` | Starts the function `k_write`, the NEON write kernel. It stores the value `v` to `n` 8-byte words, from the address `a` on. Each worker calls it once per buffer, directly after the allocation (line 993). This call is the first touch. It happens before the first interval, and it is not timed. The call writes the first `cfg.bytes` bytes of the buffer, the range of `--bytes`. The buffer is this value rounded up to a multiple of 2 MiB (line 344). So the call writes the whole buffer only when `--bytes` is a multiple of 2 MiB. The kernel table also offers this function as the kernel `write` (line 823). |
| 448 | `{` | Opens the body of `k_write`. |
| 449 | `    uint64_t *p = a;` | `p`: the write position. It starts at `a`. |
| 450 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx8`, before the loop: `add x1, x0, x1, lsl #3` [Ref1]. |
| 451 | `    uint64x2_t q = vdupq_n_u64(v);` | `vdupq_n_u64(v)` builds one 16-byte vector `q` that holds `v` twice. Machine code of `bwx8`, before the loop: `dup v31.2d, x2`. The register `x2` holds `v`. `dup` copies one 8-byte value into both halves of a 16-byte vector register [Ref1]. |
| 452 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 453 | `        vst1q_u64(p + 0, q);` | `vst1q_u64(p + 0, q)` stores the 16 bytes of `q` at the write position. These are the bytes 0 to 15 of the current block of 256 B. |
| 454 | `        vst1q_u64(p + 2, q);` | Stores `q` to the bytes 16 to 31 of the block. Machine code of `bwx8`: gcc joined this store and the store of line 453 into one instruction `stp q31, q31`. `stp` stores two 16-byte registers, which is 32 B. Here both are the register `q31` [Ref1]. |
| 455 | `        vst1q_u64(p + 4, q);` | Stores `q` to the bytes 32 to 47 of the block. |
| 456 | `        vst1q_u64(p + 6, q);` | Stores `q` to the bytes 48 to 63 of the block. |
| 457 | `        vst1q_u64(p + 8, q);` | Stores `q` to the bytes 64 to 79 of the block. |
| 458 | `        vst1q_u64(p + 10, q);` | Stores `q` to the bytes 80 to 95 of the block. |
| 459 | `        vst1q_u64(p + 12, q);` | Stores `q` to the bytes 96 to 111 of the block. |
| 460 | `        vst1q_u64(p + 14, q);` | Stores `q` to the bytes 112 to 127 of the block. |
| 461 | `        vst1q_u64(p + 16, q);` | Stores `q` to the bytes 128 to 143 of the block. |
| 462 | `        vst1q_u64(p + 18, q);` | Stores `q` to the bytes 144 to 159 of the block. |
| 463 | `        vst1q_u64(p + 20, q);` | Stores `q` to the bytes 160 to 175 of the block. |
| 464 | `        vst1q_u64(p + 22, q);` | Stores `q` to the bytes 176 to 191 of the block. |
| 465 | `        vst1q_u64(p + 24, q);` | Stores `q` to the bytes 192 to 207 of the block. |
| 466 | `        vst1q_u64(p + 26, q);` | Stores `q` to the bytes 208 to 223 of the block. |
| 467 | `        vst1q_u64(p + 28, q);` | Stores `q` to the bytes 224 to 239 of the block. |
| 468 | `        vst1q_u64(p + 30, q);` | Stores `q` to the bytes 240 to 255 of the block. The 16 stores of one loop pass fill 256 B. Each byte is written once. The machine loop of `bwx8` has 8 `stp` instructions [Ref1]. |
| 469 | `        p += 32;` | Moves the write position forward by 32 words, which are 256 B. Machine code of `bwx8`: `add x0, x0, #0x100`. gcc put this `add` at the start of the loop pass. So the 8 `stp` instructions use the offsets -256 to -32 [Ref1]. |
| 470 | `    } while (p < end);` | Repeats the loop while the write position is below `end`. Machine code of `bwx8`: `cmp x1, x0` and the branch `b.hi`. One loop pass is 11 instructions for 256 B: 1 `add`, 8 `stp`, 1 `cmp` and 1 branch [Ref1]. With `--bytes 256M` the first touch writes 268435456 bytes in 1048576 loop passes. The binary `bw_new` holds the same instruction text for its `k_write` [Ref3]. |
| 471 | `}` | Ends the function `k_write`. |

### Function `k_copy`: the NEON copy kernel (lines 473 to 520)

| Line | Source | Explanation |
|---:|---|---|
| 473 | `PLACE(copy);` | `PLACE(copy)` adds the pad `PAD_copy`, which is 32 bytes with the default values (line 106). |
| 474 | `__attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_copy`, the kernel `copy`: the NEON copy kernel. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. |
| 475 | `{` | Opens the body of `k_copy`. |
| 476 | `    uint64_t *dp = d;` | `dp`: the write position in the destination. It starts at `d`. |
| 477 | `    const uint64_t *sp = s;` | `sp`: the read position in the source. It starts at `s`. |
| 478 | `    const uint64_t *end = s + n;` | `end`: the first address after the source range: `s` plus `n` words. |
| 479 | `    do {` | Starts the loop. With `do` the loop body runs before the first test of the end. |
| 480 | `        uint64x2_t v0 = vld1q_u64(sp + 0);` | `vld1q_u64(sp + 0)` loads 16 B from the read position into the vector `v0`. These are the bytes 0 to 15 of the current source block of 256 B. |
| 481 | `        uint64x2_t v1 = vld1q_u64(sp + 2);` | Loads the bytes 16 to 31 of the source block into `v1`. |
| 482 | `        uint64x2_t v2 = vld1q_u64(sp + 4);` | Loads the bytes 32 to 47 of the source block into `v2`. |
| 483 | `        uint64x2_t v3 = vld1q_u64(sp + 6);` | Loads the bytes 48 to 63 of the source block into `v3`. |
| 484 | `        uint64x2_t v4 = vld1q_u64(sp + 8);` | Loads the bytes 64 to 79 of the source block into `v4`. |
| 485 | `        uint64x2_t v5 = vld1q_u64(sp + 10);` | Loads the bytes 80 to 95 of the source block into `v5`. |
| 486 | `        uint64x2_t v6 = vld1q_u64(sp + 12);` | Loads the bytes 96 to 111 of the source block into `v6`. |
| 487 | `        uint64x2_t v7 = vld1q_u64(sp + 14);` | Loads the bytes 112 to 127 of the source block into `v7`. |
| 488 | `        uint64x2_t v8 = vld1q_u64(sp + 16);` | Loads the bytes 128 to 143 of the source block into `v8`. |
| 489 | `        uint64x2_t v9 = vld1q_u64(sp + 18);` | Loads the bytes 144 to 159 of the source block into `v9`. |
| 490 | `        uint64x2_t v10 = vld1q_u64(sp + 20);` | Loads the bytes 160 to 175 of the source block into `v10`. |
| 491 | `        uint64x2_t v11 = vld1q_u64(sp + 22);` | Loads the bytes 176 to 191 of the source block into `v11`. |
| 492 | `        uint64x2_t v12 = vld1q_u64(sp + 24);` | Loads the bytes 192 to 207 of the source block into `v12`. |
| 493 | `        uint64x2_t v13 = vld1q_u64(sp + 26);` | Loads the bytes 208 to 223 of the source block into `v13`. |
| 494 | `        uint64x2_t v14 = vld1q_u64(sp + 28);` | Loads the bytes 224 to 239 of the source block into `v14`. |
| 495 | `        uint64x2_t v15 = vld1q_u64(sp + 30);` | Loads the bytes 240 to 255 of the source block into `v15`. One loop pass loads 256 B with 16 NEON loads of 16 B. |
| 496 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | An `asm` statement with an empty instruction text, as in `k_read` (line 438). It adds no instruction. It names the 16 loaded vectors as inputs that must be in vector registers (`"w"`), here `v0` to `v3`. So gcc must have all 16 loaded values in registers at this point. A comment in the benchmark source `bandwidth.c` of the folder `bench` reports the effect on the copy loop with gcc 14.2.0: with the statement the 8 `ldp` stand ahead of the 8 `stp`, and without it loads and stores alternate. |
| 497 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the statement of line 496: the inputs `v4` to `v7`. |
| 498 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the statement of line 496: the inputs `v8` to `v11`. |
| 499 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Continues the statement of line 496: the inputs `v12` to `v15`. The statement ends here. |
| 500 | `        vst1q_u64(dp + 0, v0);` | `vst1q_u64(dp + 0, v0)` stores the vector `v0` to the bytes 0 to 15 of the current destination block. So each loaded value is stored once and has no other use. |
| 501 | `        vst1q_u64(dp + 2, v1);` | Stores `v1` to the bytes 16 to 31 of the destination block. |
| 502 | `        vst1q_u64(dp + 4, v2);` | Stores `v2` to the bytes 32 to 47 of the destination block. |
| 503 | `        vst1q_u64(dp + 6, v3);` | Stores `v3` to the bytes 48 to 63 of the destination block. |
| 504 | `        vst1q_u64(dp + 8, v4);` | Stores `v4` to the bytes 64 to 79 of the destination block. |
| 505 | `        vst1q_u64(dp + 10, v5);` | Stores `v5` to the bytes 80 to 95 of the destination block. |
| 506 | `        vst1q_u64(dp + 12, v6);` | Stores `v6` to the bytes 96 to 111 of the destination block. |
| 507 | `        vst1q_u64(dp + 14, v7);` | Stores `v7` to the bytes 112 to 127 of the destination block. |
| 508 | `        vst1q_u64(dp + 16, v8);` | Stores `v8` to the bytes 128 to 143 of the destination block. |
| 509 | `        vst1q_u64(dp + 18, v9);` | Stores `v9` to the bytes 144 to 159 of the destination block. |
| 510 | `        vst1q_u64(dp + 20, v10);` | Stores `v10` to the bytes 160 to 175 of the destination block. |
| 511 | `        vst1q_u64(dp + 22, v11);` | Stores `v11` to the bytes 176 to 191 of the destination block. |
| 512 | `        vst1q_u64(dp + 24, v12);` | Stores `v12` to the bytes 192 to 207 of the destination block. |
| 513 | `        vst1q_u64(dp + 26, v13);` | Stores `v13` to the bytes 208 to 223 of the destination block. |
| 514 | `        vst1q_u64(dp + 28, v14);` | Stores `v14` to the bytes 224 to 239 of the destination block. |
| 515 | `        vst1q_u64(dp + 30, v15);` | Stores `v15` to the bytes 240 to 255 of the destination block. One loop pass stores 256 B with 16 NEON stores of 16 B. |
| 516 | `        sp += 32;` | Moves the read position forward by 32 words, which are 256 B. |
| 517 | `        dp += 32;` | Moves the write position forward by 32 words, which are 256 B. |
| 518 | `    } while (sp < end);` | Repeats the loop while the read position is below `end`. Machine code of `bwx8`, one loop pass: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.hi`. That is 20 instructions for 256 B loaded and 256 B stored. gcc joined each two neighbour loads into one `ldp` and each two neighbour stores into one `stp` [Ref1]. |
| 519 | `}` | Ends the function `k_copy`. |

### Macro `DEF_ASMREAD`: the hand-written read loop and its six kernels (lines 521 to 564)

| Line | Source | Explanation |
|---:|---|---|
| 521 | `/*` | Opens the comment about the assembly kernels. |
| 522 | ` * asm kernels: the asm text of bench/bandwidth.c, inside macros so that an` | Comment: the kernels below hold the assembly text of the benchmark source `bandwidth.c` in the folder `bench`. From here to line 765 the loop of each kernel is assembly text inside an `__asm__` statement. gcc copies this text into the function. The text of three loops stands inside macros. |
| 523 | ` * A/A copy is the same source under a second name. Each iteration moves` | Comment: the reason for the macros: one more line then defines the same loop under a second name, an A/A copy. |
| 524 | ` * 256 B with 8 ldp/stp of q registers (16 B each). Callers guarantee n * 8` | Comment: one loop pass moves 256 B with 8 `ldp` or `stp` instructions. Each of them moves two `q` registers of 16 B. The read loop has 8 `ldp`. The write loop has 8 `stp`. The copy loop has 8 `ldp` and 8 `stp`. |
| 525 | ` * is a multiple of 256 and non-zero. v8-v15 are callee-saved in AAPCS64:` | Comment: the callers guarantee that the size in bytes is a multiple of 256 and is not 0. The loop tests the end only after a loop pass. `main` ends the program with status 2 when `--bytes` is 0 or is not a multiple of 256 (line 2130), and when the size of a `--seq` entry is not a multiple of 256 (line 2148). The next sentence: AAPCS64, the calling rules of Arm, say that a function must keep `v8` to `v15` for its caller. |
| 526 | ` * naming them as clobbers makes gcc save d8-d15 once per call, which is` | Comment: the `asm` statement names these registers as changed (clobbers). So gcc saves `d8` to `d15`, the low 8 bytes of these registers, once per call. |
| 527 | ` * outside the loop.` | Comment: this save is outside the loop. |
| 528 | ` *` | Comment: an empty line of the comment. |
| 529 | ` * DEF_ASMREAD(name, nops) puts "nops" nop instructions after the 8 ldp and` | Comment: the macro `DEF_ASMREAD(name, nops)` puts `nops` instructions of the kind `nop` after the 8 `ldp`. |
| 530 | ` * before the add (step B5). asmread and asmread2 have 0 of them.` | Comment: the `nop` instructions stand before the `add`. The comment links them to step B5 of the file `handoff.md`, the specification of the first runner. `asmread` and `asmread2` have 0 `nop`. |
| 531 | ` */` | Ends the comment. |
| 532 | `#define DEF_ASMREAD(name, nops) \` | Starts the macro `DEF_ASMREAD(name, nops)`. It defines one kernel function with a hand-written read loop. The backslash at the end of each line continues the macro on the next line. The kernel `asmread` (line 558) and every `read_nop` kernel come from this macro. |
| 533 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 79). For `asmread` and for every `read_nop` kernel the pad is 0 bytes. So each of these functions starts at a multiple of 64 bytes. |
| 534 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function. `k_##name` joins `k_` and the first macro argument: `DEF_ASMREAD(asmread, 0)` defines the function `k_asmread`. `a` is the start of the range. `n` is its length in 8-byte words. The function returns nothing. `noinline` forbids gcc to merge the function into its caller. So the listing of the CRB build of `bwx8` shows each kernel as a function of its own [Ref1]. |
| 535 | `    { \` | Opens the body of the kernel function. |
| 536 | `        const uint64_t *p = a; \` | `p`: the read pointer. It starts at `a`. |
| 537 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. Machine code of `bwx8`: `add x1, x0, x1, lsl #3`, which adds 8 times `x1` to `x0` and puts the result into `x1`. It runs once per call, before the loop [Ref1]. |
| 538 | `        __asm__ volatile( \` | Starts a gcc statement that holds assembly text. gcc copies the text into the function. `volatile` tells gcc to keep the statement, although no later code uses `p`. The listing of `bwx8` shows the instructions in the order of the text [Ref1]. |
| 539 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. `\n\t` ends one line of the assembly text and indents the next one. In the CRB binary of `bwx8` the loop of `k_asmread` and the loop of every `read_nop` kernel start at an address of 20 modulo 64 [Ref1]. |
| 540 | `            "ldp q0, q1, [%[p]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 15 of the current block of 256 B into `q0` and the bytes 16 to 31 into `q1`. `%[p]` stands for the register that gcc chose for `p`. In the listing of `bwx8` it is `x0` [Ref1]. |
| 541 | `            "ldp q2, q3, [%[p], #32]\n\t" \` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 542 | `            "ldp q4, q5, [%[p], #64]\n\t" \` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 543 | `            "ldp q6, q7, [%[p], #96]\n\t" \` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. With this instruction the bytes 0 to 127 of the block are loaded. |
| 544 | `            "ldp q8, q9, [%[p], #128]\n\t" \` | Loads the bytes 128 to 159 of the block into `q8` and `q9`. |
| 545 | `            "ldp q10, q11, [%[p], #160]\n\t" \` | Loads the bytes 160 to 191 of the block into `q10` and `q11`. |
| 546 | `            "ldp q12, q13, [%[p], #192]\n\t" \` | Loads the bytes 192 to 223 of the block into `q12` and `q13`. |
| 547 | `            "ldp q14, q15, [%[p], #224]\n\t" \` | Loads the bytes 224 to 255 of the block into `q14` and `q15`. One loop pass has 8 load instructions. It reads 256 B, each byte once, in rising address order. Nothing uses the loaded values: no instruction of the loop takes `q0` to `q15` as an input, and the next loop pass overwrites the registers. The old read kernel `k_oldread` (line 390) differs in this point: its source adds every loaded word to a sum (line 384). The unrolling is part of this text: 8 `ldp` per loop pass. gcc does not change the instructions of assembly text. It only puts register names in the places of `%[p]` and `%[end]`. |
| 548 | `            ".rept " #nops "\n\tnop\n\t.endr\n\t" \` | `#nops` turns the second macro argument into text. For `read_nop4` the assembler sees the three lines `.rept 4`, `nop` and `.endr`. `.rept N` and `.endr` are assembler directives: the assembler repeats the lines between them N times. With `.rept 0` it writes nothing. So the loop of `asmread` has 0 `nop` between the last `ldp` and the `add`, and the loop of `read_nop4` has 4. A `nop` does nothing and loads nothing. So every loop pass still reads 256 B, and only the instruction count of the loop pass grows. |
| 549 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the read pointer forward by 256 B. Machine code of `bwx8`: `add x0, x0, #0x100` [Ref1]. |
| 550 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the read pointer with `end` and sets the condition flags. Machine code of `bwx8`: `cmp x0, x1` [Ref1]. |
| 551 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. `lo` means lower in an unsigned compare. The end test stands after the loop body. So the body runs at least once in every call. Instructions of one loop pass: 8 `ldp`, the `nop` instructions and these 3. That is 11 per 256 B in `asmread`, which has no `nop`. The listing of `bwx8` prints `b.cc` for this branch and names `b.lo` as another name of it [Ref1]. |
| 552 | `            : [p] "+r"(p) \` | Tells gcc which C variables the text uses. `[p] "+r"(p)`: `p` is in a general register, and the text reads it and changes it. |
| 553 | `            : [end] "r"(end) \` | `[end] "r"(end)`: `end` is an input in a general register. In the listing of `bwx8` it is `x1` [Ref1]. |
| 554 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list. It tells gcc what the text changes besides `p`. This line names the vector registers `v0` to `v7`. |
| 555 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` on the stack before the loop and loads them back after it. In the listing of `bwx8` these are 4 `stp` instructions before the loop and 4 `ldp` instructions after it [Ref1]. This save runs once per call of the kernel, not once per loop pass. With `--stop common` one call in a timed interval covers one chunk of 2 MiB (line 1042). That is 8192 loop passes. |
| 556 | `              "memory", "cc"); \` | Ends the clobber list and the statement. `"memory"` says that the text accesses memory that no operand names. `"cc"` says that the text changes the condition flags. |
| 557 | `    }` | Ends the kernel function and the macro. In `bwx8` the function `k_asmread` has 21 instructions: 5 before the loop, 11 in the loop and 5 after it, with `ret` as the last one [Ref1]. |
| 558 | `DEF_ASMREAD(asmread, 0)` | Defines `k_asmread`, the kernel `asmread`: the macro loop with 0 `nop`. One loop pass has 8 `ldp` loads of 32 B, `add`, `cmp` and the branch: 11 instructions per 256 B. In the CRB build of `bwx8` its instruction text equals the text of `k_asmread` in the benchmark binary `bw_new` [Ref1] [Ref3]. `k_read` (line 417), the new read kernel, has the same 8 `ldp` loads and the same 11 instructions per 256 B. The listing shows four differences [Ref1]. Registers: `q0` to `q15` here, `q31` to `q16` in `k_read`. Save of `d8` to `d15`, outside the loop: only here. Loop start: 20 modulo 64 here, 36 in `k_read`. End test: `cmp x0, x1` with `b.cc` here, `cmp x1, x0` with `b.hi` in `k_read`. |
| 559 | `DEF_ASMREAD(asmread2, 0)` | Defines `k_asmread2`, the A/A copy of `asmread`. The listing of the CRB build of `bwx8` shows the same instruction text for both [Ref1]. |
| 560 | `DEF_ASMREAD(read_nop4, 4)` | Defines `k_read_nop4`: the `asmread` loop with 4 `nop` per loop pass. That is 15 instructions per 256 B: 8 `ldp`, 4 `nop`, `add`, `cmp` and the branch. |
| 561 | `DEF_ASMREAD(read_nop8, 8)` | Defines `k_read_nop8`: the `asmread` loop with 8 `nop` per loop pass. That is 19 instructions per 256 B. |
| 562 | `DEF_ASMREAD(read_nop16, 16)` | Defines `k_read_nop16`: the `asmread` loop with 16 `nop` per loop pass. That is 27 instructions per 256 B. |
| 563 | `DEF_ASMREAD(read_nop32, 32)` | Defines `k_read_nop32`: the `asmread` loop with 32 `nop` per loop pass. That is 43 instructions per 256 B. |

### Function `k_read_sparse`: 128 B per loop pass, 4 loads and 9 `nop` (lines 565 to 586)

| Line | Source | Explanation |
|---:|---|---|
| 565 | `/* Step B5. Per 128 B: 4 ldp, 9 nop, add, cmp, b.lo. That is 16 instructions` | Comment: the kernel below belongs to step B5 of the file `handoff.md`, the specification of the first runner. Per 128 B it has 4 `ldp`, 9 `nop`, `add`, `cmp` and `b.lo`. That is 16 instructions. |
| 566 | ` * per 128 B, as the old read loop has, and no vector add. */` | Comment: the old read loop also has 16 instructions per 128 B. This kernel has the same instruction count, and it has no vector add. |
| 567 | `PLACE(read_sparse);` | `PLACE` adds the pad of the kernel `read_sparse`. It is the pad of `asmread`, 0 bytes (line 166). |
| 568 | `__attribute__((noinline)) static void k_read_sparse(const uint64_t *a, size_t n)` | Starts the function `k_read_sparse`, the kernel `read_sparse`. `a` is the start of the range to read. `n` is its length in 8-byte words. The function returns nothing. |
| 569 | `{` | Opens the body of `k_read_sparse`. |
| 570 | `    const uint64_t *p = a;` | `p`: the read pointer. It starts at `a`. |
| 571 | `    const uint64_t *end = a + n;` | `end`: the first address after the range: `a` plus `n` words. |
| 572 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text of the loop. |
| 573 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx8` the loop starts 4 bytes after the function start, at an address of 4 modulo 64 [Ref1]. |
| 574 | `        "ldp q0, q1, [%[p]]\n\t"` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current block of 128 B into `q0` and `q1`. |
| 575 | `        "ldp q2, q3, [%[p], #32]\n\t"` | Loads the bytes 32 to 63 of the block into `q2` and `q3`. |
| 576 | `        "ldp q4, q5, [%[p], #64]\n\t"` | Loads the bytes 64 to 95 of the block into `q4` and `q5`. |
| 577 | `        "ldp q6, q7, [%[p], #96]\n\t"` | Loads the bytes 96 to 127 of the block into `q6` and `q7`. One loop pass has 4 load instructions. It reads 128 B, each byte once. Nothing uses the loaded values. |
| 578 | `        ".rept 9\n\tnop\n\t.endr\n\t"` | The assembler writes the instruction `nop` 9 times here. A `nop` does nothing. |
| 579 | `        "add %[p], %[p], #128\n\t"` | Moves the read pointer forward by 128 B. |
| 580 | `        "cmp %[p], %[end]\n\t"` | Compares the read pointer with `end`. |
| 581 | `        "b.lo 1b\n\t"` | Branches back to the label `1` while the pointer is below `end`. One loop pass is 16 instructions per 128 B: 4 `ldp`, 9 `nop`, `add`, `cmp` and the branch. |
| 582 | `        : [p] "+r"(p)` | `p` is in a general register. The text reads it and changes it. |
| 583 | `        : [end] "r"(end)` | `end` is an input in a general register. |
| 584 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc");` | The clobber list: the vector registers `v0` to `v7`, memory and the condition flags. It names none of `v8` to `v15`. So gcc saves no register in this function. The listing of `bwx8` shows one `add` before the loop and one `ret` after it [Ref1]. |
| 585 | `}` | Ends the function `k_read_sparse`. |

### Macro `DEF_ASMWRITE`: the hand-written write loop, kernels `asmwrite` and `asmwrite2` (lines 587 to 613)

| Line | Source | Explanation |
|---:|---|---|
| 587 | `#define DEF_ASMWRITE(name) \` | Starts the macro `DEF_ASMWRITE(name)`. It defines one kernel function with a hand-written write loop. The backslash at the end of each line continues the macro on the next line. |
| 588 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 79). |
| 589 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores the value `v` to `n` 8-byte words, from the address `a` on. `noinline`: gcc must keep the function separate from its caller. |
| 590 | `    { \` | Opens the body of the kernel function. |
| 591 | `        uint64_t *p = a; \` | `p`: the write pointer. It starts at `a`. |
| 592 | `        const uint64_t *end = a + n; \` | `end`: the first address after the range: `a` plus `n` words. |
| 593 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. gcc copies the text into the function. |
| 594 | `            "dup v0.2d, %[v]\n\t" \` | `dup` copies the 8-byte value `v` into both halves of the 16-byte vector register `v0`. It stands before the loop label, so it runs once per call. `%[v]` stands for the register that gcc chose for `v`. |
| 595 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx8` the loop of `k_asmwrite` starts at an address of 40 modulo 64 [Ref1]. |
| 596 | `            "stp q0, q0, [%[p]]\n\t" \` | `stp` stores two 16-byte vector registers to memory, which is 32 B. Here both are `q0`. This instruction writes the bytes 0 to 31 of the current block of 256 B. `%[p]` stands for the register of the write pointer `p`. |
| 597 | `            "stp q0, q0, [%[p], #32]\n\t" \` | Stores `q0` twice to the bytes 32 to 63 of the block. |
| 598 | `            "stp q0, q0, [%[p], #64]\n\t" \` | Stores `q0` twice to the bytes 64 to 95 of the block. |
| 599 | `            "stp q0, q0, [%[p], #96]\n\t" \` | Stores `q0` twice to the bytes 96 to 127 of the block. |
| 600 | `            "stp q0, q0, [%[p], #128]\n\t" \` | Stores `q0` twice to the bytes 128 to 159 of the block. |
| 601 | `            "stp q0, q0, [%[p], #160]\n\t" \` | Stores `q0` twice to the bytes 160 to 191 of the block. |
| 602 | `            "stp q0, q0, [%[p], #192]\n\t" \` | Stores `q0` twice to the bytes 192 to 223 of the block. |
| 603 | `            "stp q0, q0, [%[p], #224]\n\t" \` | Stores `q0` twice to the bytes 224 to 255 of the block. One loop pass has 8 store instructions. It writes 256 B, each byte once, in rising address order. The unrolling is part of this text: 8 `stp` per loop pass. |
| 604 | `            "add %[p], %[p], #256\n\t" \` | `add` moves the write pointer forward by 256 B. |
| 605 | `            "cmp %[p], %[end]\n\t" \` | `cmp` compares the write pointer with `end`. |
| 606 | `            "b.lo 1b\n\t" \` | `b.lo 1b` branches back to the label `1` while the pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 607 | `            : [p] "+r"(p) \` | `[p] "+r"(p)`: `p` is in a general register. The text reads it and changes it. |
| 608 | `            : [end] "r"(end), [v] "r"(v) \` | `end` and `v` are inputs in general registers. |
| 609 | `            : "v0", "memory", "cc"); \` | The clobber list: the text changes the vector register `v0`, memory and the condition flags. The calling rules do not require a function to keep `v0`. So gcc saves no register in this function. |
| 610 | `    }` | Ends the kernel function and the macro. |
| 611 | `DEF_ASMWRITE(asmwrite)` | Defines `k_asmwrite`, the kernel `asmwrite`. Machine code in `bwx8`: one loop pass is 11 instructions for 256 B: 8 `stp`, `add x0, x0, #0x100`, `cmp x0, x1` and `b.cc`. Before the loop stand the `add` that computes the end address and the `dup`. After it stands `ret` [Ref1]. The first touch uses `k_write` (line 447), not this loop. |
| 612 | `DEF_ASMWRITE(asmwrite2)` | Defines `k_asmwrite2`, the A/A copy of `asmwrite`. The listing of the CRB build of `bwx8` shows the same instruction text for both [Ref1]. |

### Macro `DEF_ASMCOPY`: the hand-written copy loop, kernels `asmcopy` and `asmcopy2` (lines 614 to 651)

| Line | Source | Explanation |
|---:|---|---|
| 614 | `#define DEF_ASMCOPY(name) \` | Starts the macro `DEF_ASMCOPY(name)`. It defines one kernel function with a hand-written copy loop. |
| 615 | `    PLACE(name); \` | `PLACE(name)` adds the pad `PAD_<name>` before the function (line 79). |
| 616 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. `restrict` tells the compiler that the two ranges do not overlap. `noinline`: gcc must keep the function separate from its caller. |
| 617 | `    { \` | Opens the body of the kernel function. |
| 618 | `        uint64_t *dp = d; \` | `dp`: the write pointer in the destination. It starts at `d`. |
| 619 | `        const uint64_t *sp = s; \` | `sp`: the read pointer in the source. It starts at `s`. |
| 620 | `        const uint64_t *end = s + n; \` | `end`: the first address after the source range: `s` plus `n` words. |
| 621 | `        __asm__ volatile( \` | Starts the gcc statement that holds the assembly text. |
| 622 | `            "1:\n\t" \` | `1:` is the label at the start of the loop. In the CRB binary of `bwx8` the loop of `k_asmcopy` starts at an address of 52 modulo 64 [Ref1]. |
| 623 | `            "ldp q0, q1, [%[s]]\n\t" \` | `ldp` loads 32 B from memory into two 16-byte vector registers: the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. `%[s]` stands for the register of the read pointer `sp`. |
| 624 | `            "ldp q2, q3, [%[s], #32]\n\t" \` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 625 | `            "ldp q4, q5, [%[s], #64]\n\t" \` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 626 | `            "ldp q6, q7, [%[s], #96]\n\t" \` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 627 | `            "ldp q8, q9, [%[s], #128]\n\t" \` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 628 | `            "ldp q10, q11, [%[s], #160]\n\t" \` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 629 | `            "ldp q12, q13, [%[s], #192]\n\t" \` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 630 | `            "ldp q14, q15, [%[s], #224]\n\t" \` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 load instructions for 256 B. |
| 631 | `            "stp q0, q1, [%[d]]\n\t" \` | `stp` stores two 16-byte vector registers to memory: `q0` and `q1` to the bytes 0 to 31 of the current destination block. `%[d]` stands for the register of the write pointer `dp`. Each loaded register is stored once and has no other use. |
| 632 | `            "stp q2, q3, [%[d], #32]\n\t" \` | Stores `q2` and `q3` to the bytes 32 to 63 of the destination block. |
| 633 | `            "stp q4, q5, [%[d], #64]\n\t" \` | Stores `q4` and `q5` to the bytes 64 to 95 of the destination block. |
| 634 | `            "stp q6, q7, [%[d], #96]\n\t" \` | Stores `q6` and `q7` to the bytes 96 to 127 of the destination block. |
| 635 | `            "stp q8, q9, [%[d], #128]\n\t" \` | Stores `q8` and `q9` to the bytes 128 to 159 of the destination block. |
| 636 | `            "stp q10, q11, [%[d], #160]\n\t" \` | Stores `q10` and `q11` to the bytes 160 to 191 of the destination block. |
| 637 | `            "stp q12, q13, [%[d], #192]\n\t" \` | Stores `q12` and `q13` to the bytes 192 to 223 of the destination block. |
| 638 | `            "stp q14, q15, [%[d], #224]\n\t" \` | Stores `q14` and `q15` to the bytes 224 to 255 of the destination block. One loop pass has 8 store instructions for 256 B. The unrolling is part of this text: 8 `ldp` and 8 `stp` per loop pass. |
| 639 | `            "add %[s], %[s], #256\n\t" \` | Moves the read pointer forward by 256 B. |
| 640 | `            "add %[d], %[d], #256\n\t" \` | Moves the write pointer forward by 256 B. |
| 641 | `            "cmp %[s], %[end]\n\t" \` | Compares the read pointer with `end`. |
| 642 | `            "b.lo 1b\n\t" \` | Branches back to the label `1` while the read pointer is below `end`. The end test stands after the loop body. So the body runs at least once in every call. |
| 643 | `            : [s] "+r"(sp), [d] "+r"(dp) \` | `sp` and `dp` are in general registers. The text reads them and changes them. |
| 644 | `            : [end] "r"(end) \` | `end` is an input in a general register. |
| 645 | `            : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 646 | `              "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call, outside the loop, as in the read loop of line 555. |
| 647 | `              "memory", "cc"); \` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 648 | `    }` | Ends the kernel function and the macro. |
| 649 | `DEF_ASMCOPY(asmcopy)` | Defines `k_asmcopy`, the kernel `asmcopy`. Machine code in `bwx8`: one loop pass is 20 instructions for 256 B loaded and 256 B stored: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and `b.cc`. The function saves `d8` to `d15` before the loop and loads them back after it [Ref1]. |
| 650 | `DEF_ASMCOPY(asmcopy2)` | Defines `k_asmcopy2`, the A/A copy of `asmcopy`. The listing of the CRB build of `bwx8` shows the same instruction text for both [Ref1]. |

### Function `k_asmcopy_c`: the machine code of the C copy loop as assembly text (lines 652 to 692)

| Line | Source | Explanation |
|---:|---|---|
| 652 | `/*` | Opens the comment about the kernel `asmcopy_c`. |
| 653 | ` * Step B2. asmcopy_c: the loop is the machine code of the C copy loop, from` | Comment: the kernel belongs to step B2 of the file `handoff.md`, the specification of the first runner. Its loop is the machine code of the C copy loop, written as assembly text. |
| 654 | ` * the listing "bw_new k_copy" of probe.txt: same instruction order, same` | Comment: the machine code comes from the listing `bw_new k_copy` of the file `probe.txt` [Ref3]. The loop has the same order of instructions. |
| 655 | ` * offsets, registers q16 to q31, and "cmp end, s; b.hi" as its loop end. The` | Comment: it also has the same offsets and the same registers `q16` to `q31`. Its loop end is `cmp end, s` followed by `b.hi`. |
| 656 | ` * three pointers are bound to x0, x1 and x2, the registers of that listing.` | Comment: the three pointers are bound to the registers `x0`, `x1` and `x2`, the registers of that listing. In the listing of `bwx8` the functions `k_asmcopy_c` and `k_copy` have the same instruction text [Ref1]. |
| 657 | ` */` | Ends the comment. |
| 658 | `PLACE(asmcopy_c);` | `PLACE` adds the pad `PAD_asmcopy_c`, which is 48 bytes with the default values (line 115). |
| 659 | `__attribute__((noinline)) static void k_asmcopy_c(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c`, the kernel `asmcopy_c`. It copies `n` 8-byte words from `s` to `d`. |
| 660 | `{` | Opens the body of `k_asmcopy_c`. |
| 661 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer. `register ... __asm__("x0")` binds this C variable to the register `x0` for the `asm` statement below. |
| 662 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 663 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 664 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 665 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx8` the loop starts 4 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 666 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 667 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 668 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 669 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 670 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 671 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 672 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 673 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 674 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. In this kernel the `add` stands before the stores. |
| 675 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 676 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 677 | `        "stp q29, q28, [%[d], #-224]\n\t"` | Stores `q29` and `q28` at the offset -224 from the moved write pointer. These are the bytes 32 to 63 of the destination block. |
| 678 | `        "stp q27, q26, [%[d], #-192]\n\t"` | Stores `q27` and `q26` at the offset -192: the bytes 64 to 95 of the destination block. |
| 679 | `        "stp q25, q24, [%[d], #-160]\n\t"` | Stores `q25` and `q24` at the offset -160: the bytes 96 to 127 of the destination block. |
| 680 | `        "stp q23, q22, [%[d], #-128]\n\t"` | Stores `q23` and `q22` at the offset -128: the bytes 128 to 159 of the destination block. |
| 681 | `        "stp q21, q20, [%[d], #-96]\n\t"` | Stores `q21` and `q20` at the offset -96: the bytes 160 to 191 of the destination block. |
| 682 | `        "stp q19, q18, [%[d], #-64]\n\t"` | Stores `q19` and `q18` at the offset -64: the bytes 192 to 223 of the destination block. |
| 683 | `        "stp q17, q16, [%[d], #-32]\n\t"` | Stores `q17` and `q16` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 684 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 685 | `        "b.hi 1b\n\t"` | `b.hi 1b` branches back to the label `1` while `end` is higher than the read pointer, as unsigned numbers. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 686 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 687 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 688 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 689 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. The calling rules do not require a function to keep `v16` to `v31`. So gcc saves no register in this function. |
| 690 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 691 | `}` | Ends the function `k_asmcopy_c`. |

### Function `k_asmcopy_c_add`: the same loop with both `add` after the stores (lines 693 to 729)

| Line | Source | Explanation |
|---:|---|---|
| 693 | `/* As asmcopy_c, but the two add stand after the 8 stp, and the 8 stp use the` | Comment: the kernel below is `asmcopy_c` with two changes. The two `add` instructions stand after the 8 `stp`. |
| 694 | ` * offsets 0 to 224, as in asmcopy. Registers stay q16 to q31. */` | Comment: the 8 `stp` use the offsets 0 to 224, as in `asmcopy`. The registers stay `q16` to `q31`. |
| 695 | `PLACE(asmcopy_c_add);` | `PLACE` adds the pad `PAD_asmcopy_c_add`, which is 48 bytes with the default values (line 118). |
| 696 | `__attribute__((noinline)) static void k_asmcopy_c_add(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_add`, the kernel `asmcopy_c_add`. It copies `n` 8-byte words from `s` to `d`. |
| 697 | `{` | Opens the body of `k_asmcopy_c_add`. |
| 698 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 699 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 700 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 701 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 702 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx8` the loop starts at an address of 52 modulo 64 [Ref1]. |
| 703 | `        "ldp q31, q30, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q31` and `q30`. |
| 704 | `        "ldp q29, q28, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q29` and `q28`. |
| 705 | `        "ldp q27, q26, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q27` and `q26`. |
| 706 | `        "ldp q25, q24, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q25` and `q24`. |
| 707 | `        "ldp q23, q22, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q23` and `q22`. |
| 708 | `        "ldp q21, q20, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q21` and `q20`. |
| 709 | `        "ldp q19, q18, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q19` and `q18`. |
| 710 | `        "ldp q17, q16, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q17` and `q16`. One loop pass has 8 `ldp` for 256 B. |
| 711 | `        "stp q31, q30, [%[d]]\n\t"` | Stores `q31` and `q30` to the bytes 0 to 31 of the current destination block. |
| 712 | `        "stp q29, q28, [%[d], #32]\n\t"` | Stores `q29` and `q28` to the bytes 32 to 63 of the destination block. |
| 713 | `        "stp q27, q26, [%[d], #64]\n\t"` | Stores `q27` and `q26` to the bytes 64 to 95 of the destination block. |
| 714 | `        "stp q25, q24, [%[d], #96]\n\t"` | Stores `q25` and `q24` to the bytes 96 to 127 of the destination block. |
| 715 | `        "stp q23, q22, [%[d], #128]\n\t"` | Stores `q23` and `q22` to the bytes 128 to 159 of the destination block. |
| 716 | `        "stp q21, q20, [%[d], #160]\n\t"` | Stores `q21` and `q20` to the bytes 160 to 191 of the destination block. |
| 717 | `        "stp q19, q18, [%[d], #192]\n\t"` | Stores `q19` and `q18` to the bytes 192 to 223 of the destination block. |
| 718 | `        "stp q17, q16, [%[d], #224]\n\t"` | Stores `q17` and `q16` to the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 719 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B. Here both `add` instructions stand after the stores. |
| 720 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. |
| 721 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 722 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 723 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 724 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 725 | `        : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",` | Starts the clobber list: the text changes the vector registers `v16` to `v23`. |
| 726 | `          "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",` | Continues the clobber list: `v24` to `v31`. gcc saves no register for them. |
| 727 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 728 | `}` | Ends the function `k_asmcopy_c_add`. |

### Function `k_asmcopy_c_reg`: the same loop with the registers `q0` to `q15` (lines 730 to 766)

| Line | Source | Explanation |
|---:|---|---|
| 730 | `/* As asmcopy_c, but with the registers q0 to q15 (q31 becomes q0, q30` | Comment: the kernel below is `asmcopy_c` with other registers: `q0` to `q15`. The register `q31` of `asmcopy_c` becomes `q0` here. |
| 731 | ` * becomes q1, and so on), and d8 to d15 named as clobbered, as in asmcopy. */` | Comment: `q30` becomes `q1`, and so on. The clobber list names `v8` to `v15`, as in `asmcopy`. So gcc saves `d8` to `d15`. |
| 732 | `PLACE(asmcopy_c_reg);` | `PLACE` adds the pad `PAD_asmcopy_c_reg`, which is 32 bytes with the default values (line 121). |
| 733 | `__attribute__((noinline)) static void k_asmcopy_c_reg(uint64_t *restrict d, const uint64_t *restrict s, size_t n)` | Starts the function `k_asmcopy_c_reg`, the kernel `asmcopy_c_reg`. It copies `n` 8-byte words from `s` to `d`. |
| 734 | `{` | Opens the body of `k_asmcopy_c_reg`. |
| 735 | `    register uint64_t *dp __asm__("x0") = d;` | `dp`: the write pointer, bound to the register `x0`. |
| 736 | `    register const uint64_t *sp __asm__("x1") = s;` | `sp`: the read pointer, bound to the register `x1`. |
| 737 | `    register const uint64_t *end __asm__("x2") = s + n;` | `end`: the first address after the source range, bound to the register `x2`. |
| 738 | `    __asm__ volatile(` | Starts the gcc statement that holds the assembly text. |
| 739 | `        "1:\n\t"` | `1:` is the label at the start of the loop. In the CRB binary of `bwx8` the loop starts 20 bytes after the function start, at an address of 52 modulo 64 [Ref1]. |
| 740 | `        "ldp q0, q1, [%[s]]\n\t"` | Loads the bytes 0 to 31 of the current source block of 256 B into `q0` and `q1`. |
| 741 | `        "ldp q2, q3, [%[s], #32]\n\t"` | Loads the bytes 32 to 63 of the source block into `q2` and `q3`. |
| 742 | `        "ldp q4, q5, [%[s], #64]\n\t"` | Loads the bytes 64 to 95 of the source block into `q4` and `q5`. |
| 743 | `        "ldp q6, q7, [%[s], #96]\n\t"` | Loads the bytes 96 to 127 of the source block into `q6` and `q7`. |
| 744 | `        "ldp q8, q9, [%[s], #128]\n\t"` | Loads the bytes 128 to 159 of the source block into `q8` and `q9`. |
| 745 | `        "ldp q10, q11, [%[s], #160]\n\t"` | Loads the bytes 160 to 191 of the source block into `q10` and `q11`. |
| 746 | `        "ldp q12, q13, [%[s], #192]\n\t"` | Loads the bytes 192 to 223 of the source block into `q12` and `q13`. |
| 747 | `        "ldp q14, q15, [%[s], #224]\n\t"` | Loads the bytes 224 to 255 of the source block into `q14` and `q15`. One loop pass has 8 `ldp` for 256 B. |
| 748 | `        "add %[s], %[s], #256\n\t"` | Moves the read pointer forward by 256 B, before the stores. |
| 749 | `        "stp q0, q1, [%[d]]\n\t"` | Stores `q0` and `q1` to the bytes 0 to 31 of the current destination block. |
| 750 | `        "add %[d], %[d], #256\n\t"` | Moves the write pointer forward by 256 B. So the 7 stores below use negative offsets. |
| 751 | `        "stp q2, q3, [%[d], #-224]\n\t"` | Stores `q2` and `q3` at the offset -224 from the moved write pointer: the bytes 32 to 63 of the destination block. |
| 752 | `        "stp q4, q5, [%[d], #-192]\n\t"` | Stores `q4` and `q5` at the offset -192: the bytes 64 to 95 of the destination block. |
| 753 | `        "stp q6, q7, [%[d], #-160]\n\t"` | Stores `q6` and `q7` at the offset -160: the bytes 96 to 127 of the destination block. |
| 754 | `        "stp q8, q9, [%[d], #-128]\n\t"` | Stores `q8` and `q9` at the offset -128: the bytes 128 to 159 of the destination block. |
| 755 | `        "stp q10, q11, [%[d], #-96]\n\t"` | Stores `q10` and `q11` at the offset -96: the bytes 160 to 191 of the destination block. |
| 756 | `        "stp q12, q13, [%[d], #-64]\n\t"` | Stores `q12` and `q13` at the offset -64: the bytes 192 to 223 of the destination block. |
| 757 | `        "stp q14, q15, [%[d], #-32]\n\t"` | Stores `q14` and `q15` at the offset -32: the bytes 224 to 255 of the destination block. One loop pass has 8 `stp` for 256 B. Each loaded register is stored once and has no other use. |
| 758 | `        "cmp %[end], %[s]\n\t"` | Compares `end` with the read pointer. |
| 759 | `        "b.hi 1b\n\t"` | Branches back to the label `1` while `end` is higher than the read pointer. One loop pass is 20 instructions: 8 `ldp`, 8 `stp`, 2 `add`, `cmp` and the branch. |
| 760 | `        : [s] "+r"(sp), [d] "+r"(dp)` | `sp` and `dp` are in their registers. The text reads them and changes them. |
| 761 | `        : [end] "r"(end)` | `end` is an input in its register. |
| 762 | `        : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",` | Starts the clobber list: the text changes the vector registers `v0` to `v7`. |
| 763 | `          "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",` | Continues the clobber list: `v8` to `v15`. These registers are in the list. So gcc saves `d8` to `d15` once per call: the listing of `bwx8` shows 4 `stp` before the loop and 4 `ldp` after it [Ref1]. |
| 764 | `          "memory", "cc");` | Ends the clobber list and the statement: the text also accesses memory and changes the condition flags. |
| 765 | `}` | Ends the function `k_asmcopy_c_reg`. |

### Stand-ins for a machine that is not AArch64 (lines 767 to 814)

| Line | Source | Explanation |
|---:|---|---|
| 767 | `#else` | `#else` of the `#if defined(__aarch64__)` of line 407. The compiler reads lines 768 to 812 only for a machine that is not AArch64. A build on CRB, an Arm machine, does not compile these lines. |
| 768 | `/*` | Opens the comment about the stand-ins. |
| 769 | ` * Stand-ins for a machine that is not AArch64: plain C loops that touch` | Comment: the stand-ins are for a machine that is not AArch64. They are plain C loops. |
| 770 | ` * exactly the same bytes as the real kernels. They exist only so that the` | Comment: each stand-in touches exactly the same bytes as the real kernel. The stand-ins have one purpose only. |
| 771 | ` * harness can be compiled and run on the development machine.` | Comment: the purpose: the program can be compiled and run on the development machine. |
| 772 | ` */` | Ends the comment. |
| 773 | `#define STANDIN 1` | `STANDIN` is 1 in this branch. It is 0 in the AArch64 branch (line 408). The header of the output then says that the kernels are stand-ins and that the rates mean nothing (line 2181). |
| 774 | `#define DEF_ASMREAD(name, nops) \` | Starts the stand-in form of the macro `DEF_ASMREAD(name, nops)`. It has the name and the arguments of the AArch64 macro of line 532, with a plain C loop over the same range. A build on CRB, an Arm machine, does not compile this branch. |
| 775 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel, as in the AArch64 branch. |
| 776 | `    __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. `a` is the start of the range and `n` its length in 8-byte words. |
| 777 | `    { \` | Opens the body of the kernel function. |
| 778 | `        const volatile uint64_t *p = a; \` | `p` points to the same words as `a`. `volatile` tells the compiler that every read through `p` must really happen. |
| 779 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 780 | `            (void)p[i]; \` | Reads word `i` and drops the value. The cast to `void` says that the value is not used. So the loop reads every word of the range once. The macro argument `nops` is not used in this branch. |
| 781 | `    }` | Ends the kernel function and the macro. |
| 782 | `#define DEF_ASMWRITE(name) \` | Starts the stand-in form of the macro `DEF_ASMWRITE(name)`, with a plain C loop. |
| 783 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 784 | `    __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \` | Starts the kernel function with the name `k_` plus `name`. It stores `v` to `n` 8-byte words, from the address `a` on. |
| 785 | `    { \` | Opens the body of the kernel function. |
| 786 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 787 | `            a[i] = v; \` | Stores `v` to word `i`. |
| 788 | `    }` | Ends the kernel function and the macro. |
| 789 | `#define DEF_ASMCOPY(name) \` | Starts the stand-in form of the macro `DEF_ASMCOPY(name)`, with a plain C loop. |
| 790 | `    PLACE(name); \` | `PLACE(name)` adds the pad of the kernel. |
| 791 | `    __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \` | Starts the kernel function with the name `k_` plus `name`. It copies `n` 8-byte words from `s` to `d`. |
| 792 | `    { \` | Opens the body of the kernel function. |
| 793 | `        for (size_t i = 0; i < n; i++) \` | A loop over the `n` words of the range. |
| 794 | `            d[i] = s[i]; \` | Copies word `i` from the source to the destination. |
| 795 | `    }` | Ends the kernel function and the macro. |
| 796 | `DEF_ASMREAD(read, 0)` | Stand-in build only: defines `k_read` as the plain read loop of lines 774 to 781. This line and the 16 lines below define all 17 kernels of lines 416 to 765 from the three stand-in macros. |
| 797 | `DEF_ASMWRITE(write)` | Stand-in build only: defines `k_write` as the plain write loop of lines 782 to 788. In such a build this function also does the first touch (line 993). |
| 798 | `DEF_ASMCOPY(copy)` | Stand-in build only: defines `k_copy` as the plain copy loop of lines 789 to 795. |
| 799 | `DEF_ASMREAD(asmread, 0)` | Stand-in build only: defines `k_asmread` as the plain read loop. |
| 800 | `DEF_ASMREAD(asmread2, 0)` | Stand-in build only: defines `k_asmread2` as the plain read loop. |
| 801 | `DEF_ASMREAD(read_nop4, 4)` | Stand-in build only: defines `k_read_nop4` as the plain read loop. The stand-in macro does not use the number 4. |
| 802 | `DEF_ASMREAD(read_nop8, 8)` | Stand-in build only: defines `k_read_nop8` as the plain read loop. The number 8 is not used. |
| 803 | `DEF_ASMREAD(read_nop16, 16)` | Stand-in build only: defines `k_read_nop16` as the plain read loop. The number 16 is not used. |
| 804 | `DEF_ASMREAD(read_nop32, 32)` | Stand-in build only: defines `k_read_nop32` as the plain read loop. The number 32 is not used. |
| 805 | `DEF_ASMREAD(read_sparse, 9)` | Stand-in build only: defines `k_read_sparse` as the plain read loop. The number 9 is not used. The real kernel also reads every byte of its range. |
| 806 | `DEF_ASMWRITE(asmwrite)` | Stand-in build only: defines `k_asmwrite` as the plain write loop. |
| 807 | `DEF_ASMWRITE(asmwrite2)` | Stand-in build only: defines `k_asmwrite2` as the plain write loop. |
| 808 | `DEF_ASMCOPY(asmcopy)` | Stand-in build only: defines `k_asmcopy` as the plain copy loop. |
| 809 | `DEF_ASMCOPY(asmcopy2)` | Stand-in build only: defines `k_asmcopy2` as the plain copy loop. |
| 810 | `DEF_ASMCOPY(asmcopy_c)` | Stand-in build only: defines `k_asmcopy_c` as the plain copy loop. |
| 811 | `DEF_ASMCOPY(asmcopy_c_add)` | Stand-in build only: defines `k_asmcopy_c_add` as the plain copy loop. |
| 812 | `DEF_ASMCOPY(asmcopy_c_reg)` | Stand-in build only: defines `k_asmcopy_c_reg` as the plain copy loop. |
| 813 | `#endif` | Ends the `#if` of line 407. |

### The kernel table `kernels` (lines 815 to 833)

| Line | Source | Explanation |
|---:|---|---|
| 815 | `/* The function is named k_<name>. The cast to void (*)(void) is undone by` | Comment: the function of a kernel has the name `k_` plus the kernel name. The table stores its address with a cast to the common pointer type `void (*)(void)`. |
| 816 | ` * call() according to the type. */` | Comment: `call` (line 838) undoes the cast according to the type of the kernel. |
| 817 | `static const struct kdef {` | Starts `struct kdef`, the type of one entry of the kernel table. |
| 818 | `    const char *name;` | `name`: the name of the kernel. It is the word that `--seq` accepts. `parse_seq` (line 1097) compares each word of `--seq` with the names and stores the index of the entry that matches. |
| 819 | `    enum ktype type;` | `type`: one of `T_READ`, `T_WRITE`, `T_COPY` and `T_OLDREAD` (line 169). It tells `call` which arguments the function takes. |
| 820 | `    void (*fn)(void);` | `fn`: the pointer to the kernel function, stored as one common pointer type. `call` casts it back to the real type before it calls the function. |
| 821 | `} kernels[] = {` | Ends the structure and starts the kernel table `kernels[]`. For each interval the worker takes the entry of the kernel from this table (line 1005) and passes it to `call`. |
| 822 | `#define K(name, type) { #name, type, (void (*)(void))k_##name }` | The macro `K(name, type)` writes one entry. `K(read, T_READ)` becomes `{ "read", T_READ, (void (*)(void))k_read }`. `#name` gives the kernel name as text. `k_##name` gives the function. |
| 823 | `    K(read, T_READ), K(write, T_WRITE), K(copy, T_COPY),` | Entries 0 to 2: `read`, `write` and `copy`, the C kernels with NEON intrinsics. `read` is entry 0 with the type `T_READ`: the new read kernel. |
| 824 | `    K(asmread, T_READ), K(asmwrite, T_WRITE), K(asmcopy, T_COPY),` | Entries 3 to 5: `asmread`, `asmwrite` and `asmcopy`, the hand-written assembly kernels. `asmread` is entry 3 with the type `T_READ`. |
| 825 | `    K(oldread, T_OLDREAD), K(oldwrite, T_WRITE), K(oldcopy, T_COPY),` | Entries 6 to 8: `oldread`, `oldwrite` and `oldcopy`, the old kernels. `oldread` is entry 6 with the type `T_OLDREAD`: the old read kernel. |
| 826 | `    K(asmread2, T_READ), K(asmwrite2, T_WRITE), K(asmcopy2, T_COPY), K(oldread2, T_OLDREAD),` | Entries 9 to 12: the A/A copies `asmread2`, `asmwrite2`, `asmcopy2` and `oldread2`. |
| 827 | `    K(asmcopy_c, T_COPY), K(asmcopy_c_add, T_COPY), K(asmcopy_c_reg, T_COPY),` | Entries 13 to 15: the copy kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. |
| 828 | `    K(read_nop4, T_READ), K(read_nop8, T_READ), K(read_nop16, T_READ), K(read_nop32, T_READ),` | Entries 16 to 19: the read kernels `read_nop4`, `read_nop8`, `read_nop16` and `read_nop32`. |
| 829 | `    K(read_sparse, T_READ),` | Entry 20: the read kernel `read_sparse`. In this version of the runner it is the last entry of the table. |
| 830 | `#undef K` | Removes the macro `K`. It is needed only inside the table. |
| 831 | `};` | Ends the kernel table. |
| 832 | `#define K_COUNT ((int)(sizeof kernels / sizeof kernels[0]))` | `K_COUNT`: the number of entries of the table. It is the size of the table divided by the size of one entry. In `bwx8` it is 21, and the listing of the CRB build holds 21 kernel functions [Ref1]. The worker calls `k_write` directly for the first touch (line 993), not through the table. |

### Function `call`: run one kernel on one range of a buffer (lines 834 to 857)

| Line | Source | Explanation |
|---:|---|---|
| 834 | `/* Runs kernel kd on len bytes at byte offset off of the thread's buffers. A` | Comment: the function below runs the kernel `kd` on `len` bytes that start at the byte offset `off` of the buffers of the thread. |
| 835 | ` * read or write kernel uses buffer a. A copy kernel reads a and writes b. The` | Comment: a read kernel or a write kernel uses the buffer `a`. A copy kernel reads `a` and writes `b`. |
| 836 | ` * sink of the old read kernel is on the stack of the thread, as it was in the` | Comment: the sink of the old read kernel is the variable that takes its sum. It lies on the stack of the thread (line 982), as it did in the function `pass` of the old benchmark source. |
| 837 | ` * old pass(), so the threads do not all store to one shared cache line. */` | Comment: so the threads do not all store to one shared cache line. |
| 838 | `static void call(const struct kdef *kd, struct thread *t, size_t off, size_t len, uint64_t v, volatile uint64_t *sink)` | Starts the function `call`. It runs one kernel on one range of a buffer. `kd` is the table entry of the kernel. `t` is the record of the calling thread. `off` and `len` give the range in bytes. `v` is the value that a write kernel stores. `sink` points to the variable that takes the sum of an old read kernel. The worker calls this function once per interval for the warm-up pass (line 1016). With `--stop common` it calls it once for each chunk of the timed loop (line 1042). In the timed loop the function runs between the clock reads `t0` and `t1`. So its own instructions are part of the timed interval, once per chunk. |
| 839 | `{` | Opens the body of `call`. |
| 840 | `    uint64_t *a = t->a + off / 8;` | `a`: the address of the first word of the range. `t->a` points to 8-byte words. So `off / 8` words are `off` bytes. |
| 841 | `    size_t n = len / 8;` | `n`: the length of the range in 8-byte words. One chunk of 2 MiB gives 262144 words. The warm-up pass of a `--seq` entry of 256 MiB gives 33554432 words. |
| 842 | `    switch (kd->type) {` | Chooses the form of the call by the type of the kernel. |
| 843 | `    case T_READ:` | The case of a read kernel. |
| 844 | `        ((read_fn)kd->fn)(a, n);` | Casts the pointer to the type `read_fn` (line 170) and calls the kernel with the address and the word count. The kernel returns nothing. |
| 845 | `        break;` | Leaves the `switch`. |
| 846 | `    case T_OLDREAD:` | The case of an old read kernel. |
| 847 | `        *sink = ((oldread_fn)kd->fn)(a, n);` | Calls the kernel, which returns its sum, and stores the sum to `*sink`. `sink` points to a `volatile` variable on the stack of the worker (line 982). So the compiler must keep the store and must compute the sum. The listing of `k_oldread` in `bwx8` holds the adds [Ref1]. This path has one store of 8 bytes per call that the `T_READ` path does not have. In the timed loop of `--stop common` that is one store per chunk (line 1042). |
| 848 | `        break;` | Leaves the `switch`. |
| 849 | `    case T_WRITE:` | The case of a write kernel. |
| 850 | `        ((write_fn)kd->fn)(a, n, v);` | Casts the pointer to the type `write_fn` and calls the write kernel with the address, the word count and the value `v` to store. |
| 851 | `        break;` | Leaves the `switch`. |
| 852 | `    case T_COPY:` | The case of a copy kernel. |
| 853 | `        ((copy_fn)kd->fn)(t->b + off / 8, a, n);` | Casts the pointer to the type `copy_fn` and calls the copy kernel. The kernel reads the range of the buffer `a` and writes the same range of the buffer `b`. |
| 854 | `        break;` | Leaves the `switch`. |
| 855 | `    }` | Ends the `switch` of line 842. |
| 856 | `}` | Ends the function `call`. It returns no value. |

### Function `read_smaps`: the page state of the buffers (lines 858 to 890)

| Line | Source | Explanation |
|---:|---|---|
| 858 | `/* Page state (handoff B.6). For each of the n buffers (a NULL entry is` | Comment: the function below reads the page state. The comment cites section B.6 of the file `handoff.md`, the specification of the first runner. The function works on `n` buffers and skips an entry that is `NULL`. |
| 859 | ` * skipped): the entry of /proc/self/smaps whose start is the buffer and whose` | Comment: for each buffer it looks for the entry of the Linux file `/proc/self/smaps` whose start is the buffer address. |
| 860 | ` * end is the buffer plus buf_len(). Without such an entry both values stay -1` | Comment: the end of that entry must be the buffer address plus `buf_len()`. Without such an entry both values stay -1. |
| 861 | ` * and are printed as NA. */` | Comment: a value of -1 is printed as `NA`. |
| 862 | `static void read_smaps(struct page *pg, uint64_t *const *buf, int n)` | Starts the function `read_smaps`. For each of the `n` buffer addresses in `buf` it looks for the mapping of that buffer in `/proc/self/smaps`. It writes two values to `pg`: the size of the mapping and the part of it on 2 MiB pages, both in kB. In a process with more than one thread `main` calls it before the first interval and after each interval (line 2268). During the call all workers wait at the barrier (line 1000 or line 1078). So the call is not timed. |
| 863 | `{` | Opens the body of `read_smaps`. In a process with one thread the worker calls the function before each interval (line 1019): after the warm-up pass and before its barrier wait of line 1022. The timed interval starts later, at the clock read `t0` (line 1035). This call is not timed either. |
| 864 | `    char line[256];` | `line`: the buffer for one line of the file, at most 255 characters. |
| 865 | `    int cur = -1;` | `cur`: the index of the buffer whose mapping the loop below is reading, or -1 for no buffer. |
| 866 | `    size_t len = buf_len();` | `len`: the buffer length from `buf_len` (line 342). |
| 867 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 868 | `        pg[i].kb_total = pg[i].kb_huge = -1;` | Sets both values of the entry to -1. The value -1 means that the buffer was not found. |
| 869 | `    FILE *f = fopen("/proc/self/smaps", "r");` | Opens `/proc/self/smaps` for reading. The file lists every memory mapping of the process. So it holds the buffers of all threads. |
| 870 | `    if (!f)` | Tests whether the file did not open. |
| 871 | `        return;` | In that case the function returns, and all values stay -1. |
| 872 | `    while (fgets(line, sizeof line, f)) {` | Starts a loop that reads the file line by line. It ends at the end of the file. |
| 873 | `        unsigned long s, e;` | `s` and `e`: the start address and the end address of a mapping. |
| 874 | `        char perms[8];` | `perms`: the word after the two addresses, at most 7 characters. In the file it holds the access rights of the mapping. The function does not use its content. |
| 875 | `        if (sscanf(line, "%lx-%lx %7s", &s, &e, perms) == 3) {` | `sscanf` returns 3 when the line starts with `start-end`, two hexadecimal addresses, and a word after them. Such a line is the first line of a mapping. |
| 876 | `            cur = -1;` | At the first line of a mapping `cur` is first set back to -1. |
| 877 | `            for (int i = 0; i < n; i++)` | Then a loop compares the mapping with every buffer. |
| 878 | `                if (buf[i] && (unsigned long)(uintptr_t)buf[i] == s && e == s + len)` | A buffer matches when its entry is not `NULL`, the mapping starts at the buffer address and the mapping ends exactly `len` bytes after it. The comment of `alloc_buf` (lines 347 to 349) gives the reason for the exact test: no-access ranges stand before and after each buffer, so Linux lists the buffer as one mapping of its own. |
| 879 | `                    cur = i;` | On a match `cur` becomes the index of that buffer. When no buffer matches, `cur` stays -1. Then the next lines of that mapping store nothing, and they cannot change the values of a buffer that was read before. |
| 880 | `        } else if (cur >= 0) {` | Every other line belongs to the mapping whose first line was read last. This branch runs only when that mapping is a buffer (`cur >= 0`). |
| 881 | `            sscanf(line, "Size: %ld kB", &pg[cur].kb_total);` | This `sscanf` stores a number only when the line starts with `Size:`. The number is the size of the mapping in kB and goes to `kb_total`. |
| 882 | `            sscanf(line, "AnonHugePages: %ld kB", &pg[cur].kb_huge);` | This `sscanf` stores a number only when the line starts with `AnonHugePages:`. The number is the part of the mapping on 2 MiB pages in kB and goes to `kb_huge`. All other lines store nothing. |
| 883 | `        }` | Ends the `else if` of line 880. |
| 884 | `    }` | Ends the loop of line 872. |
| 885 | `    fclose(f);` | Closes the file. |
| 886 | `    for (int i = 0; i < n; i++)` | A loop over all `n` entries of `pg`. |
| 887 | `        if (pg[i].kb_total < 0 \|\| pg[i].kb_huge < 0)` | Tests whether one of the two values of the entry is still below 0. |
| 888 | `            pg[i].kb_total = pg[i].kb_huge = -1;` | In that case both values are set to -1. `print_p` (line 917) prints a value below 0 as `NA`. |
| 889 | `}` | Ends the function `read_smaps`. |

### Function `read_vmstat`: four counters of the whole system (lines 891 to 908)

| Line | Source | Explanation |
|---:|---|---|
| 891 | `/* Four counters of /proc/vmstat. They count for the whole system. -1: not found. */` | Comment: the function below reads four counters of the Linux file `/proc/vmstat`. They count for the whole system, not for one buffer. The value -1 means that a counter was not found. |
| 892 | `static void read_vmstat(long long vm[4])` | Starts the function `read_vmstat`. It reads the four counters into `vm[0]` to `vm[3]`, in the order of the names in line 894. They become the last four columns of every P row. In a process with more than one thread `main` calls it once before the first interval and once after each interval (line 2269). In a process with one thread the worker calls it before each interval (line 1020): after the warm-up pass and before its barrier wait of line 1022. The timed interval starts later, at the clock read `t0` (line 1035). It is not timed. |
| 893 | `{` | Opens the body of `read_vmstat`. |
| 894 | `    static const char *name[4] = { "thp_fault_alloc", "thp_fault_fallback", "thp_collapse_alloc", "pgmigrate_success" };` | `name`: the names of the four counters. The Linux documentation gives their meanings [Ref6]. `thp_fault_alloc` counts the 2 MiB pages that Linux gave at a page fault. `thp_fault_fallback` counts the page faults at which Linux could not give a 2 MiB page and used small pages. `thp_collapse_alloc` counts the 2 MiB pages that Linux made later from a range of small pages. `pgmigrate_success` counts the pages that Linux moved to another place in physical memory. |
| 895 | `    char key[64];` | `key`: the buffer for one name of the file, at most 63 characters. |
| 896 | `    long long val;` | `val`: the number that follows the name. |
| 897 | `    for (int i = 0; i < 4; i++)` | A loop over the four values. |
| 898 | `        vm[i] = -1;` | Sets the value to -1. The value -1 means that the counter was not found. |
| 899 | `    FILE *f = fopen("/proc/vmstat", "r");` | Opens `/proc/vmstat` for reading. |
| 900 | `    if (!f)` | Tests whether the file did not open. |
| 901 | `        return;` | In that case the function returns with the four values at -1. |
| 902 | `    while (fscanf(f, "%63s %lld", key, &val) == 2)` | Each line of the file holds a name and a number. `fscanf` reads one such pair per loop pass. The loop ends when `fscanf` finds no further pair, for example at the end of the file. |
| 903 | `        for (int i = 0; i < 4; i++)` | A loop over the four names. |
| 904 | `            if (!strcmp(key, name[i]))` | Tests whether the name from the file equals name `i`. `strcmp` returns 0 for equal texts. |
| 905 | `                vm[i] = val;` | On a match the number goes to the matching place in `vm`. |
| 906 | `    fclose(f);` | Closes the file. |
| 907 | `}` | Ends the function `read_vmstat`. |

### Function `print_na`: one csv field, or `NA` (lines 909 to 916)

| Line | Source | Explanation |
|---:|---|---|
| 909 | `static void print_na(long long v)` | Starts the function `print_na`. It prints one more field of a csv row: a comma and then the number `v`. For a negative `v` it prints `,NA`. The functions `read_smaps` (line 862) and `read_vmstat` (line 892) store -1 for a value that they did not find. So such a value shows as `NA` in a P row. |
| 910 | `{` | Opens the body of `print_na`. |
| 911 | `    if (v < 0)` | Tests whether `v` is negative. |
| 912 | `        printf(",NA");` | A negative value prints as a comma and the text `NA` (not available). |
| 913 | `    else` | The case of a value of 0 or more. |
| 914 | `        printf(",%lld", v);` | Prints a comma and the number in decimal. |
| 915 | `}` | Ends the function `print_na`. |

### Function `print_p`: one P row, the page state of one buffer (lines 917 to 926)

| Line | Source | Explanation |
|---:|---|---|
| 917 | `static void print_p(int round, int pos, int tid, char buffer, const struct page *pg, const long long vm[4])` | Starts the function `print_p`. It prints one P row: the page state of one buffer at one reading. `round`, `pos` and `tid` are the round, the position and the thread index. `buffer` is the letter `a` or `b`. `pg` holds the two page values of the buffer. `vm` holds four counters of the Linux file `/proc/vmstat`. In a process with more than one thread `main` calls it once per buffer after each reading of the page state (line 2274). In a process with one thread `main` calls it in line 2230 and line 2232. |
| 918 | `{` | Opens the body of `print_p`. |
| 919 | `    printf("P,%d,%d,%d,%c", round, pos, tid, buffer);` | Columns 1 to 5 of the row: the letter `P`, the round, the position, the thread index and the buffer letter. The position is -1 in the rows of the reading before the first interval (line 2200). In every other row of a process with more than one thread it is the position of the interval that has ended directly before the reading. In a process with one thread the row holds the state that the worker read before the interval of that position (line 1017). |
| 920 | `    print_na(pg->kb_total);` | Column 6, `kB_total`: the size of the mapping of the buffer. The unit is kB of 1024 bytes. `read_smaps` (line 862) took the value from the line `Size` of the Linux file `/proc/self/smaps`. A value that it did not find prints as `NA`. |
| 921 | `    print_na(pg->kb_huge);` | Column 7, `kB_huge`: the part of the buffer that lies on 2 MiB pages, in kB of 1024 bytes. `read_smaps` took it from the line `AnonHugePages` of the same file. |
| 922 | `    for (int i = 0; i < 4; i++)` | Loop over the four counters of `/proc/vmstat`. |
| 923 | `        print_na(vm[i]);` | Columns 8 to 11: the counters `thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc` and `pgmigrate_success`, in this order (line 894). They count for the whole system, not for this buffer. `main` passes the same array `vm` for all buffers of one reading (line 2274). So all P rows of one reading hold the same four values. |
| 924 | `    printf("\n");` | Ends the row with a line break. |
| 925 | `}` | Ends the function `print_p`. |

### Function `open_counters`: open the counter group of one thread (lines 927 to 955)

| Line | Source | Explanation |
|---:|---|---|
| 927 | `/* Counters (handoff B.8): one group per thread, user mode only, opened by the` | Comment: the counters follow section B.8 of the file `handoff.md`, the specification of the first runner. Each thread has one counter group. The counters count in user mode only. The sentence about who opens them goes on in line 928. |
| 928 | ` * pinned thread for itself. An event that does not open is printed as NA. */` | Comment: the pinned thread opens the counters for itself. An event that does not open is printed as `NA` (lines 2254 to 2255). |
| 929 | `static void open_counters(struct thread *t)` | Starts the function `open_counters`. It opens one counter per entry of `--events` for the calling thread and joins the counters into one group. With `--count` each worker calls it once (line 991), after the pinning and before it maps its buffer. `t` is the record of the calling thread. |
| 930 | `{` | Opens the body of `open_counters`. |
| 931 | `    t->group_fd = -1;` | Start state: no group leader (`group_fd` is -1). The group leader is the first counter of a counter group. |
| 932 | `    t->nopen = 0;` | Start state: 0 open counters. |
| 933 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `--events`, in the order of the list. `cfg.nev` is their number. |
| 934 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 935 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. So every option that the next lines do not set is off. The field `disabled` also stays 0. So a counter counts from the moment it is opened. |
| 936 | `        a.type = (uint32_t)cfg.pmu_type;` | `type` selects the PMU (performance monitoring unit, the hardware event counters of a core). It is the value of `--pmu-type`. |
| 937 | `        a.size = sizeof a;` | `size` gives Linux the size of the structure. |
| 938 | `        a.config = cfg.ev_code[e];` | `config` is the event code of this entry of `--events`. The program passes the code to Linux and does not interpret it. |
| 939 | `        a.exclude_kernel = 1;` | `exclude_kernel = 1`: the counter does not count while the CPU runs code of the Linux kernel. |
| 940 | `        a.exclude_hv = 1;` | `exclude_hv = 1`: the counter does not count code of a hypervisor. A hypervisor is the software that runs virtual machines. With these two fields the counter counts in user mode only: while the thread runs the code of the program itself. The specification of the first runner says that counter code without these two fields fails without root rights on CRB [Ref4]. |
| 941 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | `read_format` chooses what one `read` of the group returns. `PERF_FORMAT_GROUP`: the values of all counters of the group in one reading. The two other flags add the enabled time and the running time of the group [Ref5]. |
| 942 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, t->group_fd, 0);` | The system call `perf_event_open` opens the counter. It returns a file descriptor: the number that later calls such as `read` use for the open counter. A negative value means failure. The arguments `0` and `-1` are the pid and the cpu argument of the call [Ref4]. Together they mean: count the calling thread, on any CPU that it runs on. With `--cpus` the thread is pinned, so this is one CPU. The argument `t->group_fd` is -1 for the first counter, which starts a new group. A later counter passes the file descriptor of the leader and joins its group. The last argument `0` means no flags. |
| 943 | `        if (fd < 0) {` | Tests whether the open failed. |
| 944 | `            if (t->idx == 0)` | Only thread 0 writes a message. So an event that fails in every thread gives one message, not one per thread. |
| 945 | `                fprintf(stderr, "perf_event_open %s (type %ld code 0x%llx): %s (printed as NA)\n", cfg.ev_name[e],` | The message goes to stderr: the word `perf_event_open`, the event name, the PMU type, the event code in hexadecimal, the error text of Linux and the words `printed as NA`. This line holds the format and the event name. |
| 946 | `                        cfg.pmu_type, (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 945: the PMU type, the event code and the error text (`strerror(errno)`). |
| 947 | `            t->ev_pos[e] = -1;` | The event gets the position -1. `main` prints `NA` for it in the C rows (lines 2253 to 2255). |
| 948 | `            continue;` | The loop goes on with the next event. The thread does not stop. |
| 949 | `        }` | Ends the `if` of line 943. |
| 950 | `        t->ev_pos[e] = t->nopen++;` | The open succeeded. `ev_pos[e]` gets the position of this event in a group reading: 0 for the first open counter, 1 for the next. `nopen` counts the open counters of the thread. |
| 951 | `        if (t->group_fd < 0)` | Tests whether the group has no leader yet. |
| 952 | `            t->group_fd = fd;` | The first counter that opens becomes the leader of the group. `group_fd` keeps its file descriptor, and every group reading uses it (line 969). The file descriptors of the other counters are not kept. The function `worker` never closes, resets or stops a counter. |
| 953 | `    }` | Ends the loop over the events (line 933). |
| 954 | `}` | Ends the function `open_counters`. |

### Function `cpu_ns`: the CPU time of the calling thread (lines 956 to 962)

| Line | Source | Explanation |
|---:|---|---|
| 956 | `static uint64_t cpu_ns(void)` | Starts the function `cpu_ns`. It returns the CPU time that the calling thread has used so far, in ns. With `--count` the worker calls it once before and once after each timed interval (line 1033, line 1065). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 957 | `{` | Opens the body of `cpu_ns`. |
| 958 | `    struct timespec ts;` | `ts`: a time value with two fields: whole seconds (`tv_sec`) and nanoseconds (`tv_nsec`). |
| 959 | `    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);` | Reads the Linux clock `CLOCK_THREAD_CPUTIME_ID` into `ts`. This clock counts the CPU time of the calling thread only. |
| 960 | `    return (uint64_t)ts.tv_sec * 1000000000UL + (uint64_t)ts.tv_nsec;` | Returns the time in ns: the seconds times 1000000000, plus the nanoseconds. |
| 961 | `}` | Ends the function `cpu_ns`. |

### Function `read_group`: one reading of the counter group (lines 963 to 978)

| Line | Source | Explanation |
|---:|---|---|
| 963 | `/* Group read: nr, time_enabled, time_running, then one value per open event. */` | Comment: the layout of one group reading: the number of counters (`nr`), the enabled time, the running time, then one value per open event [Ref5]. |
| 964 | `static void read_group(const struct thread *t, struct counts *c)` | Starts the function `read_group`. It takes one reading of all counters of the thread `t` and stores it in `c`. With `--count` the worker calls it once before and once after each timed interval (line 1032, line 1066). Both calls lie outside the timed interval. Without `--count` the worker does not call it. |
| 965 | `{` | Opens the body of `read_group`. |
| 966 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest reading: 3 header words plus 8 counter values (`MAX_EV` is 8). Each word has 8 bytes. |
| 967 | `    if (t->group_fd < 0)` | Tests whether the thread has no open counter. |
| 968 | `        return;` | Such a thread returns here. Then `c` keeps the zeros that the worker wrote in line 1014. |
| 969 | `    if (read(t->group_fd, buf, sizeof buf) < (ssize_t)(3 * sizeof buf[0]) \|\| buf[0] != (uint64_t)t->nopen) {` | One `read` system call on the leader returns the whole group: the number of counters `nr`, the enabled time, the running time, then one value per counter [Ref5]. The reading is rejected when it has fewer than 24 bytes (the 3 header words). It is also rejected when `nr` is not the number of counters that this thread opened. |
| 970 | `        perror("read of the counter group");` | A rejected reading: `perror` prints the words `read of the counter group` and the reason that Linux gave to stderr. |
| 971 | `        exit(2);` | The whole program then ends with exit status 2. |
| 972 | `    }` | Ends the `if` of line 969. |
| 973 | `    c->enabled = buf[1];` | Stores the enabled time of the group, in ns: how long the counters were enabled. |
| 974 | `    c->running = buf[2];` | Stores the running time of the group, in ns: how long the counters really counted. `main` prints the difference between the two readings of an interval as `enabled_ns` and `running_ns` in the C row (lines 2249 to 2250). |
| 975 | `    for (int i = 0; i < t->nopen; i++)` | Loop over the open counters of the thread. |
| 976 | `        c->val[i] = buf[3 + i];` | Stores one value per open counter, in the order in which the counters were opened. `main` prints for each event the difference between the reading after the interval and the reading before it (line 2257). |
| 977 | `}` | Ends the function `read_group`. |

### Function `worker`: start values, pinning, counters, buffers and first touch (lines 979 to 1002)

| Line | Source | Explanation |
|---:|---|---|
| 979 | `static void *worker(void *arg)` | Starts the function `worker`, the start function of every worker thread. `main` creates the workers in line 2169. `arg` points to the record of the thread. |
| 980 | `{` | Opens the body of `worker`. |
| 981 | `    struct thread *t = arg;` | `t`: the record of this thread. `main` has set its index `idx` and its CPU `cpu` (lines 2167 to 2168). |
| 982 | `    volatile uint64_t sink;` | `sink`: a volatile variable on the stack of this thread. `call` stores there the sum that an old read kernel returns (line 847). The compiler must keep this store. So it cannot remove the adds of the old read kernel. Each thread has its own `sink`. So the threads do not all store to one shared cache line. |
| 983 | `    /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */` | Comment: the store value is known only when the program runs, and its 8 bytes are not all equal. So the compiler cannot turn the store loop into a call of `memset`, the library function that fills memory with one byte value. |
| 984 | `    uint64_t v = ((uint64_t)getpid() + (uint64_t)t->idx + 1) * 0x9E3779B97F4A7C15ULL;` | `v`: the value that `k_write` stores into the 8-byte words of a buffer at the first touch (line 993). It is the process id (`getpid`) plus the thread index plus 1, times a fixed 64-bit constant. The timed loop gives `v` plus a counter to a write kernel (line 1042, line 1056). The read kernels do not use `v`. |
| 985 | `    uint64_t k = 0; /* intervals this thread has run (--stop common) */` | `k`: the number of timed intervals that this thread has started. Line 1024 compares it with the shared counter `gen`. The comment says that `--stop common` uses it. |
| 986 | `    int64_t min_ns = (int64_t)(cfg.min_s * 1e9);` | `min_ns`: the `--min-ms` value in ns. Only the loop of `--stop pass` uses it (line 1062). |
| 988 | `    if (cfg.ncpus)` | Tests whether a CPU list was given (`--cpus`). |
| 989 | `        pin_cpu(t->cpu);` | CPU pinning. The thread pins itself to its CPU with `pin_cpu` (line 331). `main` chose the CPU in line 2168. Every later line of the worker runs on that CPU. Without `--cpus` the thread is not pinned. |
| 990 | `    if (cfg.count)` | Tests whether counting is on (`--count`). |
| 991 | `        open_counters(t);` | The thread opens its counters with `open_counters` (line 929). The counters count from this moment on. So they also count during the first touch and the warm-up passes. A C row holds only the change between the two readings of one interval (line 1032, line 1066). |
| 992 | `    t->a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 350) maps buffer `a` of this thread. The buffer starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. `alloc_buf` also asks Linux for 2 MiB pages for it (with `--no-thp`: for no such pages). Each thread has its own buffer and reads only its own buffer. |
| 993 | `    k_write(t->a, cfg.bytes / 8, v); /* first touch by this thread */` | First touch. `k_write` (line 447) stores `v` into `cfg.bytes / 8` words of 8 bytes, from the start of the buffer: every word of the `--bytes` range. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 344). Then the worker does not write the rest. No kernel call reaches the rest: the size of a `--seq` entry is at most `--bytes` (line 2148). The pinned thread does this write itself, before any read. Linux assigns the memory pages at this first write. This line is not timed. The comment says: first touch by this thread. |
| 994 | `    if (cfg.two_buffers) {` | Tests whether the thread needs a second buffer `b`. It exists only with `--two-buffers` or with a copy kernel in `--seq` (lines 2153 to 2154). |
| 995 | `        t->b = alloc_buf();` | Maps buffer `b` in the same way as buffer `a`. |
| 996 | `        k_write(t->b, cfg.bytes / 8, v);` | First touch of buffer `b`: the same write as in line 993. It is not timed. |
| 997 | `    }` | Ends the `if` of line 994. |
| 998 | `    if (cfg.threads > 1) {` | Tests whether the process has more than one worker. Only then the two barrier waits of lines 999 to 1000 exist. The barrier releases its waiting threads when all workers and the main thread have called it (line 2162). |
| 999 | `        pthread_barrier_wait(&bar); /* the buffers exist: main() reads the first page state */` | First wait at the barrier. It returns when all workers have mapped and written their buffers and `main` has arrived in line 2202. Then `main` copies the buffer addresses and reads the page state for the P rows with position -1. The comment says: the buffers exist, and `main` reads the first page state. |
| 1000 | `        pthread_barrier_wait(&bar); /* main() has read it */` | Second wait at the barrier. The worker blocks until that reading is done. `main` releases the workers in line 2271. The comment says: `main` has read it. |
| 1001 | `    }` | Ends the `if` of line 998. |

### Function `worker`: one interval, from the warm-up pass to the clock read `t0` (lines 1003 to 1036)

| Line | Source | Explanation |
|---:|---|---|
| 1003 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds. `--rounds N` runs the `--seq` list N times, and the rounds count from 0. |
| 1004 | `        for (int pos = 0; pos < cfg.nseq; pos++) {` | Loop over the positions of the `--seq` list. One pass of this loop is one timed interval. `main` runs the same two loops (lines 2196 to 2197). |
| 1005 | `            const struct kdef *kd = &kernels[cfg.seq[pos].k];` | `kd`: the entry of the kernel table for this position: name, type and function pointer (line 821). The kernels run in the order of the `--seq` list. |
| 1006 | `            size_t size = cfg.seq[pos].bytes;` | `size`: the number of bytes of this position. It is the size after `@` in the `--seq` entry, or the `--bytes` value for an entry without `@` (line 2147). |
| 1007 | `            size_t nchunk = size / HUGE_BYTES;` | `nchunk`: the number of whole 2 MiB pieces in `size`. It is 128 for a size of 256 MiB. Only the start offset of line 1009 uses it. |
| 1008 | `            /* --start offset (handoff B.5): thread i starts at (i * 37 mod n) * 2 MiB */` | Comment: with `--start offset` thread i starts at the 2 MiB piece with the number i times 37 modulo n. Here n is `nchunk`. The comment names section B.5 of the file `handoff.md`, the specification of the first runner. |
| 1009 | `            size_t off = cfg.start_offset && nchunk ? ((size_t)t->idx * 37 % nchunk) * HUGE_BYTES : 0;` | `off`: the byte offset in the buffer at which this thread starts its timed work. With `--start common` it is 0. It is also 0 for a size below 2 MiB. With `--start offset` it is `idx * 37 % nchunk` times 2 MiB. So most threads start at a place of their buffer other than byte 0. Thread 0 starts at byte 0, and with one piece (`nchunk` is 1) every thread does. |
| 1010 | `            uint64_t per_byte = kd->type == T_COPY ? 2 : 1; /* copy counts read+write bytes */` | `per_byte`: 2 for a copy kernel, 1 for every other kernel. A copy kernel counts every byte two times: once read, once written. |
| 1011 | `            uint64_t bytes = 0, p = 0;` | `bytes`: the byte count of the timed interval. `p`: the number of kernel calls of the interval with `--stop common`, or of passes with `--stop pass`. Both start at 0. |
| 1012 | `            int64_t sched = 0, deadline = 0, t0, t1;` | Clock values in ns: `sched` (the common start time), `deadline`, `t0` (the start of the timed interval) and `t1` (the clock read after the latest kernel work). |
| 1013 | `            struct result r;` | `r`: the result record of this thread for this interval (line 212). |
| 1014 | `            memset(&r, 0, sizeof r);` | `memset` sets every field of `r` to 0. |
| 1016 | `            call(kd, t, 0, size, v, &sink); /* warm-up */` | Warm-up pass, not timed. One call of the kernel of this position over the range from byte 0 to `size`, through `call` (line 838). So before every timed interval the thread has run the same kernel once over the whole range. Between this pass and the timed interval lie the barrier wait, the wait for the common start and the first counter reading (lines 1022 to 1034). In a process with one thread the page-state reading of lines 1017 to 1021 also lies between them. |
| 1017 | `            if (cfg.threads == 1) {` | Tests whether the process has one worker only. Only such a process reads the page state here, in the worker: after the warm-up pass and before the barrier. |
| 1018 | `                uint64_t *buf[2] = { t->a, t->b };` | `buf`: the addresses of the two buffers of the thread. `t->b` is NULL when the thread has no second buffer. |
| 1019 | `                read_smaps(r.pg, buf, 2);` | `read_smaps` (line 862) reads the page state of both buffers into `r.pg`. It skips a NULL entry. |
| 1020 | `                read_vmstat(r.vm);` | `read_vmstat` (line 892) reads the four counters of `/proc/vmstat` into `r.vm`. `main` prints both readings as P rows after the interval (lines 2229 to 2233). |
| 1021 | `            }` | Ends the `if` of line 1017. |
| 1022 | `            pthread_barrier_wait(&bar);` | Barrier wait after the warm-up pass. The thread blocks until all workers have ended their warm-up pass and `main` has arrived in line 2214. Then all of these threads continue. A thread whose warm-up pass ends early waits here and reads no memory. |
| 1023 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Only then lines 1024 to 1029 run. |
| 1024 | `                while (atomic_load(&gen) != k + 1)` | Common start, step 1. The thread repeats an empty loop until the shared counter `gen` equals `k + 1`. `main` adds 1 to `gen` in line 2219, after it has stored the start time and the deadline of this interval. In this loop the thread stays on its CPU and does not sleep. |
| 1025 | `                    ;` | The empty body of the loop of line 1024. |
| 1026 | `                sched = atomic_load(&t_sched_ns);` | Copies the common start time into `sched`. `main` computed it in line 2216: its clock reading plus 2 ms (`LEAD_NS`). All workers read the same value. |
| 1027 | `                deadline = atomic_load(&deadline_ns);` | Copies the common deadline into `deadline`. `main` computed it in line 2218: the start time plus the `--min-ms` value. All workers read the same value. |
| 1028 | `                while (now_ns() < sched)` | Common start, step 2. The thread reads the clock again and again until the clock reaches `sched`. It leaves the loop at its first clock read at or after the start time. This wait is not timed. |
| 1029 | `                    ;` | The empty body of the loop of line 1028. |
| 1030 | `            }` | Ends the `if` of line 1023. |
| 1031 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). |
| 1032 | `                read_group(t, &r.c0);` | First counter reading (`read_group`, line 964). It goes into `r.c0`. With `--stop common` it runs after the wait for the common start. With `--stop pass` it runs directly after the barrier. In both cases it runs before the clock read of line 1035. So it is not inside the timed interval. But `t0` is later than the common start time by at least the duration of this line and of line 1033. |
| 1033 | `                r.c0.cpu_ns = cpu_ns();` | Reads the thread CPU time (`cpu_ns`, line 956) into `r.c0`. |
| 1034 | `            }` | Ends the `if` of line 1031. |
| 1035 | `            t0 = now_ns();` | Start of the timed interval. The thread reads the clock (`now_ns`, line 243) into `t0`. Each thread has its own `t0`. Nothing above this line is inside the timed interval. |
| 1036 | `            k++;` | Counts this interval. At the next interval line 1024 waits for the next value of `gen`. This line runs after the clock read `t0`, so it is the first statement inside the timed interval. |

### Function `worker`: the timed loop and the two stop rules (lines 1037 to 1063)

| Line | Source | Explanation |
|---:|---|---|
| 1037 | `            if (cfg.stop_common) {` | Tests for `--stop common`. Lines 1040 to 1048 are the timed loop of this stop rule. |
| 1038 | `                /* chunks of 2 MiB (or the whole entry if it is smaller); the` | Comment: the kernel runs on chunks of 2 MiB, or on the whole entry when the entry is smaller than 2 MiB. The sentence goes on in line 1039. |
| 1039 | `                 * position continues from chunk to chunk and wraps */` | Comment: the position in the buffer goes on from chunk to chunk. At the end of the entry it returns to the start. |
| 1040 | `                size_t chunk = size < CHUNK_BYTES ? size : CHUNK_BYTES, at = off;` | `chunk`: the number of bytes of one kernel call: 2097152 bytes (2 MiB, `CHUNK_BYTES`), or `size` when `size` is smaller. `at`: the byte offset of the next chunk in the buffer. It starts at `off` (line 1009). |
| 1041 | `                do {` | Starts the timed loop. Its body runs at least once. |
| 1042 | `                    call(kd, t, at, chunk, v + p++, &sink);` | Timed kernel call. `call` (line 838) runs the kernel on the chunk at byte offset `at`. The kernel gets the address of the chunk and its length in 8-byte words: 262144 words for a chunk of 2 MiB. So the kernel function is entered once per chunk: 128 times per pass over a buffer of 256 MiB. For a kernel of the type `T_OLDREAD`, `call` stores the returned sum in `sink` after each call. A kernel of the type `T_READ` returns nothing. `v + p++` gives a write kernel a new value in every call and counts the calls. A read kernel does not get this argument. |
| 1043 | `                    bytes += per_byte * chunk;` | Bytes counted. Each finished call adds `per_byte * chunk`: 2097152 bytes for a 2 MiB chunk of a read kernel. This is the size of the range that was passed to the kernel. Nothing is counted inside a kernel. So the number is the same for every read kernel. |
| 1044 | `                    at += chunk;` | Moves `at` to the next chunk. |
| 1045 | `                    if (at == size)` | Tests whether `at` has reached the end of the entry. |
| 1046 | `                        at = 0;` | After the last chunk the offset returns to 0. For a size of 256 MiB this is after chunk 127. So the kernel calls go from the start offset `off` to the end of the range. Then they repeat the whole range from byte 0, until the interval ends. With `--start common` the offset `off` is 0, and the first pass is also a whole pass. |
| 1047 | `                    t1 = now_ns();` | Clock read after every chunk: `t1` is the clock value after this call. The last `t1` is the end of the timed interval. So the timed interval is the code from line 1035 to this line: the kernel calls, the byte count, the step of the offset and one clock read per chunk. |
| 1048 | `                } while (t1 < deadline);` | Stop rule of `--stop common`. The loop repeats while `t1` is before the common deadline. A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in, and the bytes and the time of this last chunk are counted. The deadline is the same for all threads. Each thread has its own end time `t1`. |
| 1049 | `            } else {` | The branch of `--stop pass`. Lines 1051 to 1062 are the timed loop of this stop rule. |
| 1050 | `                /* whole passes; with an offset a pass is [off, size) then [0, off) */` | Comment: the thread runs whole passes. With a start offset one pass is the range from `off` to the end of the entry and then the range from 0 to `off`. |
| 1051 | `                uint64_t passes_per_check = CHECK_BYTES / size;` | `passes_per_check`: the number of passes between two clock reads. It is 8 MiB (`CHECK_BYTES`) divided by `size`, rounded down. So for a size below 8 MiB that does not divide 8 MiB, the clock is read after less than 8 MiB. |
| 1052 | `                if (passes_per_check == 0)` | Tests whether the division gave 0. That is the case for every size above 8 MiB. |
| 1053 | `                    passes_per_check = 1;` | The value is then 1: the thread reads the clock after every pass. |
| 1054 | `                do {` | Starts the timed loop of `--stop pass`. Its body runs at least once. |
| 1055 | `                    for (uint64_t c = 0; c < passes_per_check; c++, p++) {` | Runs `passes_per_check` passes without a clock read between them. `p` counts the passes. |
| 1056 | `                        call(kd, t, off, size - off, v + p, &sink);` | Timed kernel call: the range from `off` to the end of the entry. With an `off` of 0 this is the whole entry. `v + p` gives a write kernel a new value in every pass. |
| 1057 | `                        if (off)` | Tests whether the thread has a start offset above 0. |
| 1058 | `                            call(kd, t, 0, off, v + p, &sink);` | Second kernel call of the pass: the range from byte 0 to `off`. So each pass covers every byte of the entry once. |
| 1059 | `                        bytes += per_byte * size;` | Bytes counted: each pass adds `per_byte * size`. This is the size of the entry, or twice the size for a copy kernel. Nothing is counted inside a kernel. |
| 1060 | `                    }` | Ends the `for` of line 1055. |
| 1061 | `                    t1 = now_ns();` | Clock read after the passes: `t1`. The clock is never read inside a pass. The last `t1` is the end of the timed interval. So with this stop rule the timed interval is the code from line 1035 to this line. |
| 1062 | `                } while (t1 - t0 < min_ns);` | Stop rule of `--stop pass`. The loop repeats while less than `min_ns` (the `--min-ms` value) has passed after the `t0` of this thread. So a thread stops only at the end of a whole pass, after a full group of `passes_per_check` passes. The threads stop at different times. |
| 1063 | `            }` | Ends the `if` and `else` of line 1037. |

### Function `worker`: after the timed interval, the result record and the barrier waits (lines 1064 to 1083)

| Line | Source | Explanation |
|---:|---|---|
| 1064 | `            if (cfg.count) {` | Tests whether counting is on (`--count`). The timed interval has ended at the last clock read `t1` (line 1047 or line 1061). |
| 1065 | `                r.c1.cpu_ns = cpu_ns();` | Reads the thread CPU time into `r.c1` (`cpu_ns`). |
| 1066 | `                read_group(t, &r.c1);` | Second counter reading, into `r.c1` (`read_group`). The order is the reverse of lines 1032 to 1033. So the timed interval lies between the two readings of the thread CPU time, and these lie between the two counter readings. The counter values of a C row therefore cover the timed interval plus a few calls around it: the two readings of the thread CPU time and the clock read `t0`. |
| 1067 | `            }` | Ends the `if` of line 1064. |
| 1068 | `            r.bytes = bytes;` | Stores the byte count of the interval in the result record. |
| 1069 | `            r.t_start = t0;` | Stores `t0`, the start of the timed interval. |
| 1070 | `            r.t_end = t1;` | Stores the last `t1`, the end of the timed interval. `main` computes the elapsed time of a thread as `t_end - t_start` (line 2226, line 2239). |
| 1071 | `            r.t_sched = cfg.stop_common ? sched : t0;` | Stores the common start time. `main` prints it in the T row as `t_sched_s` (line 2240). With `--stop pass` there is no common start time, and the field gets `t0`. |
| 1072 | `            r.late = cfg.stop_common && t0 - sched > LATE_NS;` | Late flag. With `--stop common` it is set when `t0` is more than 100000 ns (100 us, `LATE_NS`) after the common start time. `main` then prints `late` in the last column of the T row (line 2241). The program does nothing else with the flag: the interval runs, and its bytes are counted. |
| 1073 | `            t->res = r;` | Copies the record into the thread structure. `main` reads it there after the barrier wait of line 1074. |
| 1074 | `            pthread_barrier_wait(&bar);` | Barrier wait at the end of the interval. The thread blocks until all workers have ended their interval and `main` waits in line 2221. A thread that has stopped reads no memory while other threads finish their last chunk or pass. |
| 1075 | `            /* main() reads the page state of all buffers. The warm-up pass of` | Comment: `main` reads the page state of all buffers at this point. The sentence about the next warm-up pass starts here. |
| 1076 | `             * the next interval starts only after that reading (handoff B.6). */` | Comment: the warm-up pass of the next interval starts only after that reading. The comment names section B.6 of the file `handoff.md`, the specification of the first runner. |
| 1077 | `            if (cfg.threads > 1)` | Tests whether the process has more than one worker. Only then the second barrier wait exists. |
| 1078 | `                pthread_barrier_wait(&bar);` | Second barrier wait at the end of the interval. While the workers block here, `main` prints the I, T and C rows of the interval and reads the page state of all buffers (lines 2223 to 2270). `main` releases the workers in line 2271. Then each worker starts the warm-up pass of the next interval. `main` prints the P rows and the `# page_read` line after the release (lines 2272 to 2275). So this output can run while the workers do their warm-up pass. The output ends before the next timed interval starts: the barrier of line 1022 lets the workers pass only when `main` has finished the output and waits in line 2214. |
| 1079 | `        }` | Ends the loop over the positions (line 1004). The worker calls no sleep function. So between two intervals lie only the waits, the readings and the warm-up pass of the rows above. |
| 1080 | `    }` | Ends the loop over the rounds (line 1003). |
| 1081 | `    return NULL;` | After the last interval of the last round the thread returns. `main` waits for the end of all threads in line 2281. |
| 1082 | `}` | Ends the function `worker`. |

### Function `usage`: option summary, then exit status 2 (lines 1084 to 1096)

| Line | Source | Explanation |
|---:|---|---|
| 1084 | `static void usage(void)` | Starts the function `usage`. It prints the option summary to stderr and ends the program with exit status 2. `main` calls it for an argument that it does not accept and for settings that fail one of its checks (lines 2126 to 2152), for example `--threads` without `--cpus`. |
| 1085 | `{` | Opens the body of `usage`. |
| 1086 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to stderr. Its text stands in lines 1087 to 1093. |
| 1087 | `            "usage: bwx --seq LIST [--threads T --cpus LIST] [--bytes B] [--min-ms MS] [--no-thp]\n"` | Text of the message: the first usage line, with the options `--seq`, `--threads`, `--cpus`, `--bytes`, `--min-ms` and `--no-thp`. The text names the program `bwx`, the name of the first version of the runner. |
| 1088 | `            "           [--rounds N] [--stop pass\|common] [--start common\|offset] [--two-buffers]\n"` | Text of the message: the options `--rounds`, `--stop`, `--start` and `--two-buffers`. |
| 1089 | `            "           [--count --pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options of the counters (`--count`, `--pmu-type`, `--events`), and the two environment variables that can give the counter settings in their place (lines 2133 to 2139). |
| 1090 | `            "       bwx --selftest \| --list\n"` | Text of the message: the second form of the command, with `--selftest` or `--list`. |
| 1091 | `            "  --seq: comma-separated entries KERNEL or KERNEL@SIZE; --list prints the kernel names\n"` | Text of the message: an entry of `--seq` is a kernel name, or a kernel name with `@` and a size. `--list` prints the kernel names. |
| 1092 | `            "  sizes must be multiples of 256; with --stop common: multiples of 2M, or below 2M\n"` | Text of the message: a size must be a multiple of 256. With `--stop common` it must be a multiple of 2M or below 2M (lines 2148 to 2149). |
| 1093 | `            "  --pmu-type and CODE: the perf_event_attr fields type and config of the core PMU (CODE may be 0x..)\n");` | Text of the message: `--pmu-type` and the code of an event go into the fields `type` and `config` of the structure `perf_event_attr` (line 936, line 938). A code may be written in hexadecimal with `0x`. This line ends the `fprintf` call. |
| 1094 | `    exit(2);` | Ends the program with exit status 2. |
| 1095 | `}` | Ends the function `usage`. |

### Function `parse_seq`: read the `--seq` list (lines 1097 to 1115)

| Line | Source | Explanation |
|---:|---|---|
| 1097 | `static void parse_seq(char *list)` | Starts the function `parse_seq`. It turns the text after `--seq` into the entries of `cfg.seq`. `main` calls it in line 2107. |
| 1098 | `{` | Opens the body of `parse_seq`. |
| 1099 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. Each pass of the loop handles one entry, in the order of the list. This order is the order in which the kernels run in each round. |
| 1100 | `        char *at = strchr(tok, '@');` | `at`: the place of an `@` in the entry, or NULL when the entry has none. An entry may have the form `KERNEL@SIZE`. |
| 1101 | `        int k = 0;` | `k`: the index into the kernel table. The search of line 1104 starts at entry 0. |
| 1102 | `        if (at)` | Tests whether the entry has an `@`. |
| 1103 | `            *at = '\0';` | Ends the name at the `@`: a zero byte replaces the `@`. |
| 1104 | `        while (k < K_COUNT && strcmp(tok, kernels[k].name))` | Searches the kernel table `kernels[]` (line 821) for the name, from the first entry on. `strcmp` returns 0 when two texts are equal. The loop stops at the entry with this name. When no entry has the name, it stops with `k` equal to `K_COUNT`, the number of entries. |
| 1105 | `            k++;` | The body of the search loop: goes on to the next entry of the table. |
| 1106 | `        if (k == K_COUNT \|\| cfg.nseq == MAX_SEQ) {` | Tests for two defects: the name is not in the table, or `cfg.seq` already holds 64 entries (`MAX_SEQ`). |
| 1107 | `            fprintf(stderr, "bad --seq entry: %s\n", tok);` | Prints `bad --seq entry:` and the name to stderr. |
| 1108 | `            exit(2);` | Ends the program with exit status 2. |
| 1109 | `        }` | Ends the `if` of line 1106. |
| 1110 | `        cfg.seq[cfg.nseq].k = k;` | Stores the index of the kernel in the next free entry of `cfg.seq`. |
| 1111 | `        cfg.seq[cfg.nseq].bytes = at ? parse_bytes(at + 1) : 0;` | Stores the size of the entry: the text after the `@`, read by `parse_bytes` (line 250). An entry without `@` gets the size 0 here. `main` later replaces 0 by the `--bytes` value (line 2147). |
| 1112 | `        cfg.nseq++;` | Counts the entry. |
| 1113 | `    }` | Ends the loop of line 1099. |
| 1114 | `}` | Ends the function `parse_seq`. |

### Function `parse_events`: read the `--events` list (lines 1116 to 1141)

| Line | Source | Explanation |
|---:|---|---|
| 1116 | `/* "NAME=CODE,..." or "CODE,...". A code without a name gets the name of its` | Comment: the list has the form `NAME=CODE,...` or `CODE,...`. The sentence about a code without a name starts here. |
| 1117 | ` * position in the list of handoff B.8. */` | Comment: a code without a name gets the name of its place in the event list of section B.8 of the file `handoff.md`, the specification of the first runner. The code has one more rule that the comment does not name: from the sixth place on the name is `ev` plus the place number (lines 1131 to 1132). |
| 1118 | `static void parse_events(char *list)` | Starts the function `parse_events`. It turns the text of an event list into the names `cfg.ev_name` and the codes `cfg.ev_code`. `main` calls it with the text after `--events` (line 2121), and with the text of the environment variable `BWX_EVENTS` (line 2137). |
| 1119 | `{` | Opens the body of `parse_events`. |
| 1120 | `    static const char *by_pos[5] = { "cycles", "instructions", "l1d_refill", "l2d_refill", "ll_miss_rd" };` | `by_pos`: the names for an entry without a name at one of the first 5 places of the list: `cycles`, `instructions`, `l1d_refill`, `l2d_refill` and `ll_miss_rd`. |
| 1121 | `    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {` | `strtok` cuts the text at every comma. One pass of the loop handles one entry. |
| 1122 | `        char *eq = strchr(tok, '='), *code = eq ? eq + 1 : tok, *end;` | `eq`: the place of the `=` sign in the entry, or NULL. `code`: the text of the code. It is the text after the `=`, or the whole entry when the entry has no `=`. `end` is used in line 1133. |
| 1123 | `        if (eq == tok \|\| cfg.nev == MAX_EV \|\| (eq && (size_t)(eq - tok) >= sizeof cfg.ev_name[0])) {` | Tests for three defects: an entry with an empty name (the `=` is its first character), a 9th entry (`MAX_EV` is 8), and a name of 32 characters or more (the size of one entry of `cfg.ev_name`). |
| 1124 | `            fprintf(stderr, "bad --events entry: %s\n", tok);` | Prints `bad --events entry:` and the entry to stderr. |
| 1125 | `            exit(2);` | Ends the program with exit status 2. |
| 1126 | `        }` | Ends the `if` of line 1123. |
| 1127 | `        if (eq)` | Tests whether the entry has a name. |
| 1128 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "%.*s", (int)(eq - tok), tok);` | Copies the text before the `=` as the name of the event. The format `%.*s` prints only the first `eq - tok` characters of the entry. The program uses the name as a column title in the header line of the C rows (line 2188) and in the error message of `open_counters` (line 945). |
| 1129 | `        else if (cfg.nev < 5)` | The case of an entry without a name at one of the first 5 places of the list. |
| 1130 | `            strcpy(cfg.ev_name[cfg.nev], by_pos[cfg.nev]);` | The entry gets the name of `by_pos` for its place. |
| 1131 | `        else` | The case of an entry without a name at place 6 or later. |
| 1132 | `            snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "ev%d", cfg.nev);` | The entry gets the name `ev` plus its place number counted from 0, for example `ev5`. |
| 1133 | `        cfg.ev_code[cfg.nev] = strtoull(code, &end, 0);` | `strtoull` with base 0 turns the code text into a number. With base 0 a text that starts with `0x` is read as hexadecimal. |
| 1134 | `        if (end == code \|\| *end != '\0') {` | Tests whether the text is not a whole number: no digit was read, or other text follows the number. |
| 1135 | `            fprintf(stderr, "bad --events code: %s\n", code);` | Prints `bad --events code:` and the code text to stderr. |
| 1136 | `            exit(2);` | Ends the program with exit status 2. |
| 1137 | `        }` | Ends the `if` of line 1134. |
| 1138 | `        cfg.nev++;` | Counts the entry. |
| 1139 | `    }` | Ends the loop of line 1121. |
| 1140 | `}` | Ends the function `parse_events`. |

### Trial mode: the comment, the constants and the name tables (lines 1142 to 1177)

| Line | Source | Explanation |
|---:|---|---|
| 1142 | `/*` | Comment: starts the comment about the trial mode. The code of the trial mode goes from here to line 2057. `main` enters it only when an argument is the word `--trial` (lines 2069 to 2071). |
| 1143 | ` * Trial mode (--trial). Design: crb/new-test-kernel/tackle-8mb.md, "Runner` | Comment: the option `--trial` selects the trial mode. Its design is the section "Runner design" of the file `tackle-8mb.md`. |
| 1144 | ` * design". Formats: DECISIONS-bwx8.md.` | Comment: the file `DECISIONS-bwx8.md` describes the formats: the plan file and the output rows. |
| 1145 | ` *` | Comment: an empty line inside the comment. |
| 1146 | ` * The plan file gives the trials of the process. The whole plan is read and` | Comment: the plan file lists the trials of the process. The program reads the whole plan first. The sentence goes on in line 1147. |
| 1147 | ` * checked before the process pins, allocates or opens a counter. A defect` | Comment: the program checks the whole plan before it pins a thread, maps a buffer or opens a counter. The sentence about a defect starts here. |
| 1148 | ` * ends the process with status 2.` | Comment: a defect of the plan ends the process with exit status 2 (line 1757). |
| 1149 | ` *` | Comment: an empty line inside the comment. |
| 1150 | ` * One trial is a list of windows: previous activity (1), prefix (4),` | Comment: one trial is a list of windows. A window runs one kernel on one range of the buffer for a fixed time. The list starts with 1 window of previous activity and 4 windows of the prefix. |
| 1151 | ` * predecessor (1), target (nwin). timed_sequence() runs them. It calls only` | Comment: the list goes on with 1 window of the predecessor and `nwin` target windows. The function `timed_sequence` (line 1338) runs the windows. The sentence about its calls starts here. |
| 1152 | ` * the kernels and the clock. With count "read" it also reads the counter` | Comment: `timed_sequence` calls only the kernels and the clock. With the counter state `read` it also reads the counter group. The sentence goes on in line 1153. |
| 1153 | ` * group and the thread CPU clock at the boundaries of the target windows.` | Comment: with the counter state `read` it also reads the thread CPU time. Both readings are taken at the boundaries of the target windows. |
| 1154 | ` * Page state, context switches, counter open and close, and all output lie` | Comment: the readings of the page state and of the context switches, the opening and the closing of the counters, and all output are named here. The sentence ends in line 1155. |
| 1155 | ` * outside the timed sequence.` | Comment: all the steps of line 1154 lie outside the timed sequence. |
| 1156 | ` */` | Comment: the end of the comment. |
| 1157 | `#include <stdarg.h>` | Includes the header `stdarg.h`. It gives `va_list`, `va_start` and `va_end` for a function with a variable number of arguments. The function `plan_bad` uses them (line 1757). |
| 1158 | `#include <sys/resource.h>` | Includes the header `sys/resource.h`. It gives the call `getrusage`, which the function `switches` uses (line 1435). |
| 1160 | `#define BIN_NS 10000000L     /* requested width of a bin: 10 ms */` | `BIN_NS`: the requested width of a bin: 10000000 ns (10 ms). A bin is a part of a target window. Its record holds a clock time and the bytes up to that time (line 1193). |
| 1161 | `#define TRACE_CAP (1L << 20) /* --trace: events kept per trial */` | `TRACE_CAP`: the largest number of events that the trace keeps per trial: 1048576 (2 to the power 20). The trace is the event log of the option `--trace`. |
| 1162 | `#define PLAN_LINE1 "# bwx8-plan v1"` | `PLAN_LINE1`: the text that the first line of a plan file must have (line 1960). |
| 1163 | `#define PLAN_LINE3 "# trial cond rep prev pfx pred tgt nwin win_ms count bins"` | `PLAN_LINE3`: the text that the third line of a plan file must have (line 1965). It names the 11 fields of a trial line. |
| 1164 | `#define PLAN_FIELDS 11` | `PLAN_FIELDS`: a trial line of the plan has 11 fields. |
| 1165 | `#define MAX_PAIRS 64` | `MAX_PAIRS`: the second line of a plan holds at most 64 pairs of the form `key=value` (line 1846). |
| 1166 | `#define MAX_NWIN 4096` | `MAX_NWIN`: a trial has at most 4096 target windows (line 1898). |
| 1167 | `#define MAX_MS 3600000L` | `MAX_MS`: a duration of the plan is at most 3600000 ms (1 hour). |
| 1168 | `#define MAX_REC_BYTES (256UL << 20) /* bound of the record storage of one plan */` | `MAX_REC_BYTES`: the records of one plan may need at most 256 MiB (268435456 bytes) of memory (line 1919). |
| 1170 | `enum { PH_PREV, PH_PREFIX, PH_PRED, PH_TARGET };` | Number codes of the four phases of a trial, from 0 to 3: previous activity, prefix, predecessor and target. |
| 1171 | `enum { CS_CLOSED, CS_OPEN, CS_READ, CS_FAIL };` | Number codes of the counter state of a trial, from 0 to 3: closed, open, read and fail. |
| 1172 | `enum { EV_CLOCK, EV_KERNEL_FIRST, EV_COUNT_READ, EV_CPU_CLOCK, EV_PAGE_READ, EV_RUSAGE, EV_OUTPUT, EV_COUNT_OPEN, EV_COUNT_CLOSE };` | Number codes of the nine kinds of trace event: a clock read, the first kernel call of a window, a reading of the counter group, a reading of the thread CPU time, a reading of the page state, a `getrusage` call, an output step, the opening of the counter group and its closing. |
| 1173 | `static const char *const phase_name[] = { "prev", "prefix", "pred", "target" };` | `phase_name`: the printed names of the four phases, in the order of line 1170. The W rows and the TR rows show them (line 1596, line 1662). |
| 1174 | `static const char *const count_name[] = { "closed", "open", "read", "fail" };` | `count_name`: the printed names of the four counter states, in the order of line 1171. The E row shows one of them (line 1657). |
| 1175 | `static const char *const event_name[] = { "clock", "kernel_first", "count_read", "cpu_clock", "page_read",` | `event_name`: the printed names of the trace events, in the order of line 1172. The TR rows show them (line 1662, line 1665). This line holds the first five names. |
| 1176 | `                                          "rusage", "output", "count_open", "count_close" };` | Continues the list of line 1175: the last four names. |

### Trial mode: the structures of the plan, the windows, the records and the trace (lines 1178 to 1233)

| Line | Source | Explanation |
|---:|---|---|
| 1178 | `/* One kernel on a range for a time. k < 0: this part is absent ("-"). */` | Comment: a part is one kernel on one range for a time. A `k` below 0 means that the plan leaves this part out. The plan then holds the text `-` in its place. |
| 1179 | `struct part {` | Starts `struct part`: one kernel field of a trial line of the plan. |
| 1180 | `    int k;` | `k`: the index of the kernel in the kernel table, or -1 for a part that the plan leaves out. |
| 1181 | `    uint64_t size;` | `size`: the number of bytes of the range: the first `size` bytes of the buffer. |
| 1182 | `    long ms;` | `ms`: the duration in ms. The target part has no duration of its own and keeps 0 here. |
| 1183 | `};` | Ends `struct part`. |
| 1185 | `/* One line of the plan. */` | Comment: one line of the plan. |
| 1186 | `struct trial {` | Starts `struct trial`: one trial line of the plan file. |
| 1187 | `    char *f[PLAN_FIELDS]; /* the fields as text, for the S row */` | `f`: the 11 fields of the line as text. `print_s` prints them in the S row (line 1570). The comment says the same. |
| 1188 | `    int nwin, count, bins;` | `nwin`: the number of target windows. `count`: the counter state that the plan asks for (a code of line 1171). `bins`: 1 when the target windows record bins, 0 if not. |
| 1189 | `    long win_ms;` | `win_ms`: the requested duration of one target window, in ms. |
| 1190 | `    struct part prev, pfx, pred, tgt;` | The four parts of the trial: previous activity (`prev`), prefix (`pfx`), predecessor (`pred`) and target (`tgt`). |
| 1191 | `};` | Ends `struct trial`. |
| 1193 | `struct bin {` | Starts `struct bin`: one bin of a target window. |
| 1194 | `    int64_t t_end;  /* a clock read of the window loop */` | `t_end`: the clock time that closed the bin, in ns. The comment says: a clock read of the window loop. The loop reads the clock no more often with bins than without them. |
| 1195 | `    uint64_t bytes; /* bytes since the start of the window */` | `bytes`: the bytes that the window has counted from its start to that clock read. |
| 1196 | `};` | Ends `struct bin`. |
| 1198 | `/* One window. set_windows() fills the first group of fields before the first` | Comment: one window. `set_windows` (line 1503) fills the first group of fields (lines 1201 to 1206) before the first trial. The sentence about the second group starts here. |
| 1199 | ` * trial. timed_sequence() fills the second group. */` | Comment: `timed_sequence` fills the second group of fields (lines 1208 to 1210) when the window runs. |
| 1200 | `struct win {` | Starts `struct win`: the record of one window. |
| 1201 | `    int k, phase, widx;` | `k`: the index of the kernel in the kernel table. `phase`: the phase of the window (a code of line 1170). `widx`: the number of the window inside its phase, counted from 0. |
| 1202 | `    uint64_t size;` | `size`: the number of bytes that one kernel call covers: the first `size` bytes of the buffer. |
| 1203 | `    uint64_t passes; /* passes between two clock reads */` | `passes`: the number of kernel calls between two clock reads (line 1520). Each call is one whole pass over the range. |
| 1204 | `    int64_t dur_ns;` | `dur_ns`: the requested duration of the window, in ns. |
| 1205 | `    struct bin *bin; /* NULL: no bins */` | `bin`: the storage for the bins of this window. NULL means that the window records no bins. |
| 1206 | `    int bin_cap;` | `bin_cap`: the number of bins that fit into that storage. |
| 1208 | `    int nbin;` | `nbin`: the number of bins that the window closed. |
| 1209 | `    uint64_t bytes;` | `bytes`: the byte count of the window: `size` times the number of kernel calls. |
| 1210 | `    int64_t t_start, t_end; /* CLOCK_MONOTONIC, ns */` | `t_start`, `t_end`: the clock read at the start of the window and the last clock read of the window, in ns of the Linux clock `CLOCK_MONOTONIC`. |
| 1211 | `};` | Ends `struct win`. |
| 1213 | `/* The record of one trial. */` | Comment: the record of one trial. |
| 1214 | `struct trec {` | Starts `struct trec`: the results of one trial. |
| 1215 | `    struct win *win;` | `win`: the window records of the trial, in the order in which the windows run. |
| 1216 | `    int nw;` | `nw`: the number of windows of the trial. |
| 1217 | `    struct counts *cnt; /* count "read": nwin + 1 readings, one per target boundary */` | `cnt`: the counter readings of the trial, or NULL. Only a trial with the counter state `read` has them: `nwin + 1` readings, one per boundary of the target windows. |
| 1218 | `    struct page pg[2];  /* before and after the timed sequence */` | `pg`: the page state of the buffer before the timed sequence (entry 0) and after it (entry 1). |
| 1219 | `    long long vm[2][4];` | `vm`: the four counters of `/proc/vmstat` before and after the timed sequence. |
| 1220 | `    uint64_t cpu[2];` | `cpu`: the thread CPU time before and after the timed sequence, in ns. |
| 1221 | `    long nvcsw[2], nivcsw[2];` | `nvcsw`, `nivcsw`: the counts of voluntary and of involuntary context switches of the thread, before and after the timed sequence (lines 1436 to 1437). |
| 1222 | `    long minflt[2]; /* minor page faults of the thread, for the --trace check */` | `minflt`: the count of minor page faults of the thread, before and after the timed sequence. A minor page fault is a page fault that Linux serves without disk access. The first touch of a page is one. The comment says that the check of `--trace` uses the count (line 1672). |
| 1223 | `    int state;   /* CS_* */` | `state`: the counter state of the trial as it ran (a code of line 1171). |
| 1224 | `    int sink_ok; /* 1, 0, or -1 if the trial ran no old read */` | `sink_ok`: the result of the sum check of the old read kernel (line 1485): 1 for a right sum, 0 for a wrong sum, -1 when the trial ran no old read kernel. |
| 1225 | `    int read_fail, close_fail;` | `read_fail`: the number of failed counter readings of the trial. `close_fail`: the number of counter file descriptors that did not close when the group was closed for this trial (line 1460). |
| 1226 | `};` | Ends `struct trec`. |
| 1228 | `struct tev {` | Starts `struct tev`: one event of the trace. |
| 1229 | `    int64_t t;` | `t`: the time of the event in ns. It is the time of the latest clock read (line 1275). |
| 1230 | `    int widx;` | `widx`: the window number of the event. Only the event of the first kernel call of a window sets it. |
| 1231 | `    uint8_t ev, phase;` | `ev`: the kind of event (a code of line 1172). `phase`: the phase of the window (a code of line 1170). |
| 1232 | `};` | Ends `struct tev`. |

### Trial mode: the worker state `struct tw` and the global variables (lines 1234 to 1264)

| Line | Source | Explanation |
|---:|---|---|
| 1234 | `/* The worker of the trial mode. */` | Comment: the worker of the trial mode. |
| 1235 | `struct tw {` | Starts `struct tw`: the state of the one worker thread of the trial mode. |
| 1236 | `    struct thread t; /* a, group_fd, ev_pos, nopen: used as in the interval mode */` | `t`: a `struct thread` (line 221), the record that a worker of the interval mode also has. The comment says that the fields `a`, `group_fd`, `ev_pos` and `nopen` are used as in the interval mode. |
| 1237 | `    uint64_t v;      /* every word of the buffer holds v */` | `v`: the value that every 8-byte word of the `--bytes` range of the buffer holds after the first touch (line 1687, line 1693). The comment says: every word of the buffer holds `v`. |
| 1238 | `    int fd[MAX_EV], nfd;` | `fd`: the file descriptors of the open counters. `nfd`: their number. `count_close` closes them (line 1378). |
| 1239 | `    int group_open; /* an open was tried and no close followed */` | `group_open`: 1 when the worker has tried to open the counter group and has not closed it after that. |
| 1240 | `    int open_fail;  /* events that did not open */` | `open_fail`: the number of events that did not open at the last opening of the group. |
| 1241 | `    int close_fail, read_fail;` | `close_fail`, `read_fail`: the numbers of failed `close` calls and of failed group readings. `run_trial` sets both to 0 for each trial (lines 1465 to 1466). |
| 1242 | `    char open_err[160];` | `open_err`: the error text of the first event that did not open. |
| 1243 | `    /* --trace */` | Comment: the fields below belong to the option `--trace`. |
| 1244 | `    struct tev *log;` | `log`: the event log of the trace. It is NULL without `--trace`. |
| 1245 | `    long nlog, ndrop;` | `nlog`: the number of events in the log. `ndrop`: the number of events that did not fit into the log. |
| 1246 | `    int64_t last_t;` | `last_t`: the time of the latest clock read. An event that is not a clock read gets this time. |
| 1247 | `    int cur_phase, cur_widx;` | `cur_phase`, `cur_widx`: the phase and the number of the window whose first kernel call was logged last (line 1299). |
| 1248 | `};` | Ends `struct tw`. |
| 1250 | `static struct {` | Starts the definition of `plan`, the variable that holds the plan and the options of the trial mode. |
| 1251 | `    const char *path;` | `path`: the path of the plan file (option `--plan`). |
| 1252 | `    uint64_t hash;` | `hash`: a 64-bit checksum of the bytes of the plan file (lines 1948 to 1950). |
| 1253 | `    char *pair[MAX_PAIRS];` | `pair`: the `key=value` pairs of the second line of the plan, as text. |
| 1254 | `    int npair;` | `npair`: the number of these pairs. |
| 1255 | `    struct trial *tr;` | `tr`: the trials of the plan, one `struct trial` per trial line. |
| 1256 | `    int n;` | `n`: the number of trials. |
| 1257 | `    int ctl_cpu, trace;` | `ctl_cpu`: the CPU of the controlling thread (option `--ctl-cpu`, default 0). `trace`: 1 with the option `--trace`. |
| 1258 | `} plan;` | Ends the definition of `plan`. Every field starts at 0. |
| 1260 | `static struct trec *rec;` | `rec`: the records of all trials, one `struct trec` per trial. `alloc_records` sets the pointer (line 1546). |
| 1261 | `static struct {` | Starts the definition of `recsz`, the sizes of the record storage. |
| 1262 | `    size_t windows, bins, counts, trace, bytes;` | `windows`, `bins`, `counts`, `trace`: the numbers of window records, bins, counter readings and trace events that the plan needs. `bytes`: the size of the record block in bytes. `plan_trial` computes all five (lines 1912 to 1918). |
| 1263 | `} recsz;` | Ends the definition of `recsz`. |

### Trial mode: the trace helpers `tev_add`, `tclock` and `tcpu` (lines 1265 to 1294)

| Line | Source | Explanation |
|---:|---|---|
| 1265 | `/* --trace. An event that is not a clock read carries the time of the latest` | Comment: the option `--trace`. An event that is not a clock read carries the time of the latest clock read. The reason follows in line 1266. |
| 1266 | ` * clock read: the trace adds no clock read of its own. */` | Comment: the trace adds no clock read of its own. |
| 1267 | `static inline void tev_add(struct tw *w, int ev, int phase, int widx)` | Starts the function `tev_add`. It appends one event to the trace: the kind `ev`, the phase and the window number. Without `--trace` it does nothing. |
| 1268 | `{` | Opens the body of `tev_add`. |
| 1269 | `    if (!w->log)` | Tests whether there is no log. That is the case without `--trace`. |
| 1270 | `        return;` | Without a log the function returns immediately. |
| 1271 | `    if (w->nlog == TRACE_CAP) {` | Tests whether the log is full: it holds `TRACE_CAP` (1048576) events. |
| 1272 | `        w->ndrop++;` | A full log does not keep the event. It only counts it in `ndrop`. |
| 1273 | `        return;` | The function then returns and stores nothing. |
| 1274 | `    }` | Ends the `if` of line 1271. |
| 1275 | `    w->log[w->nlog++] = (struct tev){ .t = w->last_t, .widx = widx, .ev = (uint8_t)ev, .phase = (uint8_t)phase };` | Appends the event to the log. Its time is `last_t`, the time of the latest clock read. |
| 1276 | `}` | Ends the function `tev_add`. |
| 1278 | `static inline int64_t tclock(struct tw *w)` | Starts the function `tclock`. It reads the clock for the trial mode and returns the time in ns. Every clock read of a timed sequence goes through it (line 1348, line 1355). |
| 1279 | `{` | Opens the body of `tclock`. |
| 1280 | `    int64_t t = now_ns();` | Reads the clock with `now_ns` (line 243). |
| 1281 | `    if (w->log) {` | Tests whether a log exists (`--trace`). |
| 1282 | `        w->last_t = t;` | Stores the time as the time of the latest clock read. |
| 1283 | `        tev_add(w, EV_CLOCK, 0, 0);` | Logs the clock read as an event. |
| 1284 | `    }` | Ends the `if` of line 1281. |
| 1285 | `    return t;` | Returns the time. |
| 1286 | `}` | Ends the function `tclock`. |
| 1288 | `static uint64_t tcpu(struct tw *w)` | Starts the function `tcpu`. It returns the thread CPU time in ns and logs the reading. |
| 1289 | `{` | Opens the body of `tcpu`. |
| 1290 | `    uint64_t c = cpu_ns();` | Reads the thread CPU time with `cpu_ns` (line 956). |
| 1291 | `    tev_add(w, EV_CPU_CLOCK, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 1292 | `    return c;` | Returns the CPU time. |
| 1293 | `}` | Ends the function `tcpu`. |

### Trial mode: the functions `tcall` and `tcount` (lines 1295 to 1327)

| Line | Source | Explanation |
|---:|---|---|
| 1295 | `/* Every kernel call of a trial goes through here, and from here through the` | Comment: every kernel call of a trial goes through this function, and from here through the unchanged function `call`. |
| 1296 | ` * unchanged call(). The trace gets the first call of each window. */` | Comment: the trace gets the first call of each window. |
| 1297 | `static inline void tcall(struct tw *w, const struct win *r, volatile uint64_t *sink)` | Starts the function `tcall`. It runs the kernel of the window `r` once on the first `r->size` bytes of the buffer. |
| 1298 | `{` | Opens the body of `tcall`. |
| 1299 | `    if (w->log && (r->phase != w->cur_phase \|\| r->widx != w->cur_widx)) {` | Tests, only with `--trace`, whether this call belongs to another window than the call before it. |
| 1300 | `        w->cur_phase = r->phase;` | Remembers the phase of the new window. |
| 1301 | `        w->cur_widx = r->widx;` | Remembers the number of the new window. |
| 1302 | `        tev_add(w, EV_KERNEL_FIRST, r->phase, r->widx);` | Logs the first kernel call of the window as an event. |
| 1303 | `    }` | Ends the `if` of line 1299. |
| 1304 | `    call(&kernels[r->k], &w->t, 0, r->size, 0, sink);` | The kernel call. It goes through `call` (line 838), the function that the interval mode also uses: offset 0, `r->size` bytes, and 0 as the store value. The plan accepts read kernels only (line 1825), and a read kernel does not use the store value. |
| 1305 | `}` | Ends the function `tcall`. |
| 1307 | `/* Group read and thread CPU clock, at a boundary of a target window. Not` | Comment: the function takes a group reading and reads the thread CPU clock, at a boundary of a target window. The sentence about inlining starts here. |
| 1308 | ` * inlined: build8.sh lists the branch targets of timed_sequence(), and this` | Comment: the function is not inlined. The script `build8.sh` lists the branch targets of `timed_sequence`. The sentence goes on in line 1309. |
| 1309 | ` * function must be one name there. */` | Comment: this function must be one name in that list. |
| 1310 | `__attribute__((noinline)) static void tcount(struct tw *w, struct counts *c)` | Starts the function `tcount`. It reads the counter group and then the thread CPU time into `c`. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 1311 | `{` | Opens the body of `tcount`. |
| 1312 | `    uint64_t buf[3 + MAX_EV];` | `buf`: space for the largest group reading: 3 header words plus 8 counter values, 8 bytes each. |
| 1313 | `    if (w->t.group_fd >= 0) {` | Tests whether a counter group is open. |
| 1314 | `        ssize_t want = (ssize_t)((3 + (size_t)w->t.nopen) * sizeof buf[0]);` | `want`: the size in bytes that a complete reading must have: 3 header words plus one word per open counter, 8 bytes each. |
| 1315 | `        if (read(w->t.group_fd, buf, sizeof buf) != want \|\| buf[0] != (uint64_t)w->t.nopen) {` | One `read` on the group leader. The reading is rejected when its size is not `want`, or when its counter number `nr` is not the number of open counters. |
| 1316 | `            w->read_fail++;` | A rejected reading only adds 1 to `read_fail`. In `read_group` a rejected reading ends the process (lines 969 to 972). |
| 1317 | `        } else {` | The case of a good reading. |
| 1318 | `            c->enabled = buf[1];` | Stores the enabled time of the group, in ns. |
| 1319 | `            c->running = buf[2];` | Stores the running time of the group, in ns. |
| 1320 | `            for (int i = 0; i < w->t.nopen; i++)` | Loop over the open counters. |
| 1321 | `                c->val[i] = buf[3 + i];` | Stores one value per open counter. |
| 1322 | `        }` | Ends the `else` of line 1317. |
| 1323 | `        tev_add(w, EV_COUNT_READ, 0, 0);` | Logs the group reading as an event. Without `--trace` this call does nothing. |
| 1324 | `    }` | Ends the `if` of line 1313. |
| 1325 | `    c->cpu_ns = tcpu(w);` | Reads the thread CPU time through `tcpu` (line 1288) and stores it. This line runs also when no group is open. |
| 1326 | `}` | Ends the function `tcount`. |

### Function `timed_sequence` (trial mode): the timed windows of one trial (lines 1328 to 1374)

| Line | Source | Explanation |
|---:|---|---|
| 1328 | `/*` | Comment: starts the comment of the function `timed_sequence`. The comment ends in line 1337. |
| 1329 | ` * The timed sequence of one trial. Each window runs whole passes over` | Comment: the function is the timed sequence of one trial. Each window runs whole passes over its range. The sentence goes on in line 1330. |
| 1330 | ` * [0, size) and reads the clock after every "passes" passes. It ends at the` | Comment: the range is the first `size` bytes of the buffer. The window reads the clock after every `passes` passes. The sentence about the end of a window starts here. |
| 1331 | ` * first clock read at or after its duration. At a boundary the clock is read` | Comment: a window ends at the first clock read at or after its duration. The sentence about a boundary between two windows starts here. |
| 1332 | ` * for the end of the window and again for the start of the next one, so the` | Comment: at a boundary the clock is read once for the end of the window and once more for the start of the next window. The sentence goes on in line 1333. |
| 1333 | ` * gap is measured. No output, allocation, page read, sleep or warm-up pass` | Comment: so the gap between two windows is measured. The function holds no output, no allocation, no reading of the page state, no sleep and no warm-up pass. This sentence ends in line 1334. |
| 1334 | ` * is in here. Not inlined: build8.sh and test_runner8.py read the branch` | Comment: the function is not inlined. The script `build8.sh` and the test `test_runner8.py` read the branch targets of this function from the machine code. The sentence goes on in line 1335. |
| 1335 | ` * targets of this function from the machine code. Only clock_gettime, the` | Comment: only three branch targets are allowed in this function. The first is the library function `clock_gettime`, which reads the clock. The list goes on in line 1336. |
| 1336 | ` * kernel call of call() and tcount() are allowed there.` | Comment: the other two allowed targets are the kernel call of `call` and the function `tcount`. |
| 1337 | ` */` | Comment: the end of the comment. |
| 1338 | `__attribute__((noinline)) static void timed_sequence(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)` | Starts the function `timed_sequence`. It runs all windows of the trial record `r`, one after another. For each window it stores the byte count and two clock times. `count_read` is 1 for a trial with the counter state `read`. `sink` receives the sum of an old read kernel. The attribute `noinline` forbids the compiler to copy the body into the caller. |
| 1339 | `{` | Opens the body of `timed_sequence`. |
| 1340 | `    for (int i = 0; i < r->nw; i++) {` | Loop over the windows of the trial, in the order in which they run. |
| 1341 | `        struct win *x = &r->win[i];` | `x`: the record of this window. |
| 1342 | `        uint64_t bytes = 0;` | `bytes`: the byte count of the window. It starts at 0. |
| 1343 | `        int64_t t0, t1, next_bin;` | Clock values in ns: `t0` (the start of the window), `t1` (the latest clock read) and `next_bin` (the requested end of the bin that is open). |
| 1344 | `        int nbin = 0;` | `nbin`: the number of bins that this window has closed. |
| 1346 | `        if (count_read && x->phase == PH_TARGET)` | Tests whether the trial reads counters and this window is a target window. |
| 1347 | `            tcount(w, &r->cnt[x->widx]);` | Counter reading before a target window: `tcount` (line 1310) reads the counter group and the thread CPU time into the reading with the number `widx`. It runs before the start clock read of line 1348. So it lies outside the window. |
| 1348 | `        t0 = tclock(w);` | Start of the window: the clock read `t0` (`tclock`, line 1278). |
| 1349 | `        next_bin = t0 + BIN_NS;` | The first bin has its requested end 10 ms (`BIN_NS`) after `t0`. |
| 1350 | `        do {` | Starts the timed loop of the window. Its body runs at least once. |
| 1351 | `            for (uint64_t c = 0; c < x->passes; c++) {` | Runs `passes` kernel calls without a clock read between them. |
| 1352 | `                tcall(w, x, sink);` | Timed kernel call: one pass of the kernel of the window over the first `size` bytes of the buffer (`tcall`, line 1297). |
| 1353 | `                bytes += x->size;` | Bytes counted: each call adds `size`, the size of the range that was passed to the kernel. Nothing is counted inside a kernel. |
| 1354 | `            }` | Ends the `for` of line 1351. |
| 1355 | `            t1 = tclock(w);` | Clock read after the passes: `t1`. The clock is never read inside a pass. |
| 1356 | `            /* A bin closes on this clock read if its requested end has` | Comment: a bin closes at this clock read when its requested end has passed. The sentence about the last bin starts here. |
| 1357 | `             * passed. The last clock read of the window closes the last bin. */` | Comment: the last clock read of the window closes the last bin. |
| 1358 | `            if (x->bin && (t1 >= next_bin \|\| t1 - t0 >= x->dur_ns) && nbin < x->bin_cap) {` | Tests three things. The window records bins. A bin can close now: its requested end has passed, or the window is over. The storage has room for one more bin. |
| 1359 | `                x->bin[nbin].t_end = t1;` | Stores the clock time `t1` as the end of the bin. |
| 1360 | `                x->bin[nbin].bytes = bytes;` | Stores the bytes that the window has counted up to this clock read. |
| 1361 | `                nbin++;` | Counts the bin. |
| 1362 | `                while (next_bin <= t1)` | Moves the requested end of the next bin forward in steps of 10 ms until it lies after `t1`. |
| 1363 | `                    next_bin += BIN_NS;` | The body of the loop of line 1362: one step of 10 ms. |
| 1364 | `            }` | Ends the `if` of line 1358. |
| 1365 | `        } while (t1 - t0 < x->dur_ns);` | Stop rule of a window. The loop repeats while less than `dur_ns` has passed after `t0`. So a window ends at its first clock read at or after its requested duration, and only at the end of a whole pass. |
| 1366 | `        x->bytes = bytes;` | Stores the byte count in the window record. The W row prints it (line 1597). This function computes no rate. |
| 1367 | `        x->t_start = t0;` | Stores `t0` as the start time of the window. |
| 1368 | `        x->t_end = t1;` | Stores the last `t1` as the end time of the window. The next window reads the clock again for its own start (line 1348). So the time between two windows is measured and belongs to no window. |
| 1369 | `        x->nbin = nbin;` | Stores the number of bins that the window closed. |
| 1370 | `    }` | Ends the loop over the windows (line 1340). |
| 1371 | `    if (count_read)` | Tests whether the trial reads counters. |
| 1372 | `        tcount(w, &r->cnt[r->win[r->nw - 1].widx + 1]);` | Last counter reading, after the last window. It goes into the reading with the number of the last target window plus 1. So a trial with `nwin` target windows has `nwin + 1` readings. |
| 1373 | `}` | Ends the function `timed_sequence`. |

### Function `count_close` (trial mode): close the counter group (lines 1375 to 1387)

| Line | Source | Explanation |
|---:|---|---|
| 1375 | `static void count_close(struct tw *w)` | Starts the function `count_close`. It closes every counter of the worker and sets the group state of the worker back to closed. |
| 1376 | `{` | Opens the body of `count_close`. |
| 1377 | `    for (int i = 0; i < w->nfd; i++)` | Loop over the counter file descriptors that `count_open` stored in `w->fd` (line 1415). |
| 1378 | `        if (close(w->fd[i]) != 0)` | Closes one counter and tests whether the `close` call failed. |
| 1379 | `            w->close_fail++;` | A failed `close` adds 1 to `w->close_fail`. |
| 1380 | `    w->nfd = 0;` | No file descriptor is stored any more. |
| 1381 | `    w->t.group_fd = -1;` | The group has no leader. |
| 1382 | `    w->t.nopen = 0;` | No event is open. |
| 1383 | `    w->group_open = 0;` | The group counts as closed. |
| 1384 | `    w->open_fail = 0;` | The count of events that did not open is 0 again. |
| 1385 | `    tev_add(w, EV_COUNT_CLOSE, 0, 0);` | Logs the closing as an event. Without `--trace` this call does nothing. |
| 1386 | `}` | Ends the function `count_close`. |

### Function `count_open` (trial mode): open the counter group (lines 1388 to 1422)

| Line | Source | Explanation |
|---:|---|---|
| 1388 | `/* One group, user mode only, opened by the pinned worker for itself. The` | Comment: the worker has one counter group, which counts in user mode only. The pinned worker opens it for itself. The next sentence starts here. |
| 1389 | ` * events count from the open on. An event that does not open is counted in` | Comment: the events count from the moment of the open. The sentence about an event that does not open starts here. |
| 1390 | ` * open_fail and is printed as NA. */` | Comment: an event that does not open is counted in `open_fail` and is printed as `NA`. |
| 1391 | `static void count_open(struct tw *w)` | Starts the function `count_open`. It is the version of `open_counters` (line 929) for the trial mode: it opens one counter per event of `cfg` and joins the counters into one group. Two things differ. It keeps every file descriptor in `w->fd`: `count_close` needs them to close the group. And it writes no message to stderr. |
| 1392 | `{` | Opens the body of `count_open`. |
| 1393 | `    w->t.group_fd = -1;` | Start state: no group leader. |
| 1394 | `    w->t.nopen = 0;` | Start state: 0 open events. |
| 1395 | `    w->nfd = 0;` | Start state: no stored file descriptor. |
| 1396 | `    w->open_fail = 0;` | Start state: 0 events that did not open. |
| 1397 | `    for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `cfg`, in the order of the option `--events`. |
| 1398 | `        struct perf_event_attr a;` | `a`: the structure that describes one counter to Linux. |
| 1399 | `        memset(&a, 0, sizeof a);` | `memset` sets all fields of `a` to 0. The field `disabled` stays 0, so a counter counts from the moment it is opened. |
| 1400 | `        a.type = (uint32_t)cfg.pmu_type;` | `type`: the PMU type (`--pmu-type`). |
| 1401 | `        a.size = sizeof a;` | `size`: the size of the structure. |
| 1402 | `        a.config = cfg.ev_code[e];` | `config`: the event code of this event. |
| 1403 | `        a.exclude_kernel = 1;` | The counter does not count code of the Linux kernel. |
| 1404 | `        a.exclude_hv = 1;` | The counter does not count code of a hypervisor. With line 1403 it counts in user mode only. |
| 1405 | `        a.read_format = PERF_FORMAT_GROUP \| PERF_FORMAT_TOTAL_TIME_ENABLED \| PERF_FORMAT_TOTAL_TIME_RUNNING;` | One `read` of the group returns the values of all its counters, the enabled time and the running time, as in line 941. |
| 1406 | `        int fd = (int)syscall(SYS_perf_event_open, &a, 0, -1, w->t.group_fd, 0);` | The system call `perf_event_open` opens the counter for the calling thread, on any CPU that it runs on, as in line 942. The first counter starts a new group. A later counter joins the group of the leader. |
| 1407 | `        if (fd < 0) {` | Tests whether the open failed. |
| 1408 | `            if (w->open_fail++ == 0)` | Counts the event as not opened. The test is true only for the first such event of this opening. |
| 1409 | `                snprintf(w->open_err, sizeof w->open_err, "%s type %ld code 0x%llx: %s", cfg.ev_name[e], cfg.pmu_type,` | For the first such event: stores an error text in `w->open_err`: the event name, the PMU type, the event code and the error text of Linux. `emit_trial` prints it in an X row (line 1632). |
| 1410 | `                         (unsigned long long)cfg.ev_code[e], strerror(errno));` | Continues the call of line 1409: the event code and the error text (`strerror(errno)`). |
| 1411 | `            w->t.ev_pos[e] = -1;` | The event gets the position -1. Its field in the C rows is `NA` (lines 1618 to 1619). |
| 1412 | `            continue;` | The loop goes on with the next event. |
| 1413 | `        }` | Ends the `if` of line 1407. |
| 1414 | `        w->t.ev_pos[e] = w->t.nopen++;` | The open succeeded. The event gets its position in a group reading, and `nopen` counts it. |
| 1415 | `        w->fd[w->nfd++] = fd;` | Keeps the file descriptor for `count_close` (line 1378). |
| 1416 | `        if (w->t.group_fd < 0)` | Tests whether the group has no leader yet. |
| 1417 | `            w->t.group_fd = fd;` | The first counter that opens becomes the leader of the group. |
| 1418 | `    }` | Ends the loop over the events (line 1397). |
| 1419 | `    w->group_open = 1;` | The group counts as open from here on. This is also the case when no event opened. |
| 1420 | `    tev_add(w, EV_COUNT_OPEN, 0, 0);` | Logs the opening as an event. Without `--trace` this call does nothing. |
| 1421 | `}` | Ends the function `count_open`. |

### Functions `page_read`, `switches` and `first_multiplexed` (trial mode) (lines 1423 to 1451)

| Line | Source | Explanation |
|---:|---|---|
| 1423 | `static void page_read(struct tw *w, struct trec *r, int at)` | Starts the function `page_read`. It reads the page state of the one buffer of the worker and the four counters of `/proc/vmstat` into the trial record `r`. `at` is 0 before the timed sequence and 1 after it. |
| 1424 | `{` | Opens the body of `page_read`. The `# page_read` lines of the interval mode do not come from this function. `main` prints them in line 2275. |
| 1425 | `    uint64_t *buf[1] = { w->t.a };` | `buf`: the address of the one buffer of the worker. |
| 1426 | `    read_smaps(&r->pg[at], buf, 1);` | `read_smaps` (line 862) reads the size of the buffer and its part on 2 MiB pages into `r->pg[at]`. |
| 1427 | `    read_vmstat(r->vm[at]);` | `read_vmstat` (line 892) reads the four counters of `/proc/vmstat` into `r->vm[at]`. |
| 1428 | `    tev_add(w, EV_PAGE_READ, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 1429 | `}` | Ends the function `page_read`. |
| 1431 | `/* Context-switch counts of the calling thread. -1: not readable. */` | Comment: the function reads the context-switch counts of the calling thread. A value of -1 means that a count could not be read. The function also stores the count of minor page faults (line 1438), which the comment does not name. |
| 1432 | `static void switches(struct tw *w, struct trec *r, int at)` | Starts the function `switches`. It stores three counts of the calling thread in the trial record `r`: the voluntary context switches, the involuntary context switches and the minor page faults. `at` is 0 before the timed sequence and 1 after it. |
| 1433 | `{` | Opens the body of `switches`. |
| 1434 | `    struct rusage ru;` | `ru`: the structure that `getrusage` fills. |
| 1435 | `    int ok = getrusage(RUSAGE_THREAD, &ru) == 0;` | `getrusage` with `RUSAGE_THREAD` asks Linux for the resource use of the calling thread. `ok` is 1 when the call succeeded. |
| 1436 | `    r->nvcsw[at] = ok ? ru.ru_nvcsw : -1;` | Stores `ru_nvcsw`, the number of voluntary context switches: the thread stopped running by its own request, usually to wait for something. A failed call stores -1. |
| 1437 | `    r->nivcsw[at] = ok ? ru.ru_nivcsw : -1;` | Stores `ru_nivcsw`, the number of involuntary context switches: Linux took the CPU away from the thread. A failed call stores -1. |
| 1438 | `    r->minflt[at] = ok ? ru.ru_minflt : -1;` | Stores `ru_minflt`, the number of minor page faults. These are page faults that need no disk access. The first touch of a page is one. A failed call stores -1. |
| 1439 | `    tev_add(w, EV_RUSAGE, 0, 0);` | Logs the reading as an event. Without `--trace` this call does nothing. |
| 1440 | `}` | Ends the function `switches`. |
| 1442 | `/* The index of the first target window whose counters ran for less time` | Comment: the function returns the index of the first target window whose counters ran for less time than they were enabled. The sentence ends in line 1443. |
| 1443 | ` * than they were enabled, or -1. cnt holds nwin + 1 readings. */` | Comment: it returns -1 when there is no such window. `cnt` holds `nwin + 1` readings. |
| 1444 | `static int first_multiplexed(const struct counts *cnt, int nwin)` | Starts the function `first_multiplexed`. `cnt` holds one counter reading per boundary of the `nwin` target windows. The function looks for a target window in which the counters did not count all the time. |
| 1445 | `{` | Opens the body of `first_multiplexed`. |
| 1446 | `    for (int i = 0; i < nwin; i++)` | Loop over the target windows. |
| 1447 | `        if (cnt[i + 1].running - cnt[i].running < cnt[i + 1].enabled - cnt[i].enabled)` | Compares, for one target window, the growth of the running time with the growth of the enabled time between its two readings. A smaller growth of the running time means that the counters did not count all the time in this window. |
| 1448 | `            return i;` | Returns the index of the first such window. |
| 1449 | `    return -1;` | Returns -1 when there is no such window. |
| 1450 | `}` | Ends the function `first_multiplexed`. |

### Function `run_trial` (trial mode): one trial, without output (lines 1452 to 1488)

| Line | Source | Explanation |
|---:|---|---|
| 1452 | `/* One trial: the work before the timed sequence, the timed sequence, the` | Comment: the function runs one trial: the work before the timed sequence, then the timed sequence. The list ends in line 1453. |
| 1453 | ` * work after it. Prints nothing. */` | Comment: then comes the work after the timed sequence. The function prints nothing. |
| 1454 | `static void run_trial(struct tw *w, const struct trial *p, struct trec *r, volatile uint64_t *sink)` | Starts the function `run_trial`. `p` is the trial of the plan. `r` is the record of the trial. `sink` receives the sum of an old read kernel. |
| 1455 | `{` | Opens the body of `run_trial`. |
| 1456 | `    uint64_t expect = 0;` | `expect`: the sum that the last old read kernel of the trial must return. |
| 1457 | `    int old = -1;` | `old`: the index of the last window with an old read kernel, or -1 when the trial has none. |
| 1459 | `    if (p->count == CS_CLOSED && w->group_open)` | Tests whether the plan wants the counters closed for this trial while the group is open. |
| 1460 | `        count_close(w);` | Then the group is closed (`count_close`, line 1375). |
| 1461 | `    else if (p->count != CS_CLOSED && !w->group_open)` | Tests whether the plan wants counters for this trial (state `open` or `read`) while the group is not open. |
| 1462 | `        count_open(w);` | Then the group is opened (`count_open`, line 1391). It stays open over the next trials until a trial wants it closed. |
| 1463 | `    r->state = p->count != CS_CLOSED && w->open_fail ? CS_FAIL : p->count;` | The record keeps the counter state of the trial. It is `fail` when the trial wants counters and an event did not open. In every other case it is the state of the plan. |
| 1464 | `    r->close_fail = w->close_fail;` | Moves the number of failed `close` calls of line 1460 into the record. |
| 1465 | `    w->close_fail = 0;` | Sets the count of failed `close` calls of the worker to 0. |
| 1466 | `    w->read_fail = 0;` | Sets the count of failed group readings of the worker to 0. |
| 1468 | `    /* The last old read of the trial must leave the sum of its range in the` | Comment: the last old read kernel of the trial must leave the sum of its range in the sink. The sentence ends in line 1469. |
| 1469 | `     * sink. The sink starts with another value, so an old value cannot pass. */` | Comment: the sink starts with another value. So a value from an earlier call cannot pass the check. |
| 1470 | `    for (int i = 0; i < r->nw; i++)` | Loop over the windows of the trial. |
| 1471 | `        if (kernels[r->win[i].k].type == T_OLDREAD)` | Tests whether the kernel of the window has the type `T_OLDREAD`. |
| 1472 | `            old = i;` | `old` keeps the index of the last such window. |
| 1473 | `    if (old >= 0) {` | Tests whether the trial has such a window. |
| 1474 | `        expect = w->v * (r->win[old].size / 8);` | The expected sum. Every 8-byte word of the `--bytes` range of the buffer holds `w->v` (line 1693), and the range of a window lies inside it (line 1827). So the kernel must return `w->v` times the number of words of its range. Only the low 64 bits of the product are kept, as in the sum of the kernel. |
| 1475 | `        *sink = expect + 1;` | The sink starts with the expected sum plus 1. |
| 1476 | `    }` | Ends the `if` of line 1473. |
| 1478 | `    page_read(w, r, 0);` | Before the timed sequence: reads the page state (`page_read`, line 1423). |
| 1479 | `    switches(w, r, 0);` | Before the timed sequence: reads the context switches and the minor page faults (`switches`, line 1432). |
| 1480 | `    r->cpu[0] = tcpu(w);` | Before the timed sequence: reads the thread CPU time (`tcpu`, line 1288). This is the last step before the timed sequence. |
| 1481 | `    timed_sequence(w, r, p->count == CS_READ, sink);` | `timed_sequence` (line 1338) runs the timed sequence. The clock reads that time the windows are inside that function. The third argument is 1 for the counter state `read`. Then the function also reads the counter group at the boundaries of the target windows. |
| 1482 | `    r->cpu[1] = tcpu(w);` | After the timed sequence: reads the thread CPU time again. |
| 1483 | `    switches(w, r, 1);` | After the timed sequence: reads the context switches and the minor page faults again. |
| 1484 | `    page_read(w, r, 1);` | After the timed sequence: reads the page state again. So the three readings come in the reverse order of lines 1478 to 1480. |
| 1485 | `    r->sink_ok = old < 0 ? -1 : *sink == expect;` | `sink_ok`: -1 when the trial ran no old read kernel. For a trial that ran one: 1 when the sink holds the expected sum, 0 when it does not. |
| 1486 | `    r->read_fail = w->read_fail;` | Moves the number of failed group readings of the timed sequence into the record. |
| 1487 | `}` | Ends the function `run_trial`. |

### Functions `trial_windows`, `window_bins` and `set_windows` (trial mode) (lines 1489 to 1529)

| Line | Source | Explanation |
|---:|---|---|
| 1489 | `static int trial_windows(const struct trial *p)` | Starts the function `trial_windows`. It returns the number of windows of one trial. |
| 1490 | `{` | Opens the body of `trial_windows`. |
| 1491 | `    return (p->prev.k >= 0) + 4 * (p->pfx.k >= 0) + (p->pred.k >= 0) + p->nwin;` | Adds the windows of the phases that the trial has: 1 for the previous activity, 4 for the prefix, 1 for the predecessor and `nwin` for the target. The plan may leave out each of the first three. Then the field `k` of that part is -1, and the phase adds 0. |
| 1492 | `}` | Ends the function `trial_windows`. |
| 1494 | `/* Bins that one target window can close: one per 10 ms that ends inside the` | Comment: the number of bins that one target window can close: one per 10 ms that ends inside the window. The list goes on in line 1495. |
| 1495 | ` * window, one at the end of the window, and one spare. */` | Comment: plus one bin at the end of the window, and one extra bin. |
| 1496 | `static int window_bins(const struct trial *p)` | Starts the function `window_bins`. It returns the number of bins for which one target window of the trial gets storage. |
| 1497 | `{` | Opens the body of `window_bins`. |
| 1498 | `    return p->bins ? (int)(p->win_ms / 10) + 2 : 0;` | For a trial with bins: the window duration `win_ms` divided by 10 and rounded down, plus 2. The 10 is the requested length of a bin in ms (`BIN_NS`, line 1160). For a trial without bins: 0. |
| 1499 | `}` | Ends the function `window_bins`. |
| 1501 | `/* Fills the plan part of the windows of one trial. bin: storage for` | Comment: the function fills the plan part of the windows of one trial. The sentence about `bin` starts here. |
| 1502 | ` * nwin * window_bins(p) bins. */` | Comment: `bin` is the storage for `nwin` times `window_bins(p)` bins. |
| 1503 | `static void set_windows(const struct trial *p, struct win *win, struct bin *bin)` | Starts the function `set_windows`. It fills the plan fields of all window records of the trial `p`, in the order in which the windows run. `win` points to the first window record of the trial. |
| 1504 | `{` | Opens the body of `set_windows`. |
| 1505 | `    const struct {` | Starts the definition of the table `ph`, with one entry per phase. |
| 1506 | `        const struct part *part;` | `part`: the part of the trial that the phase runs. |
| 1507 | `        int phase, n;` | `phase`: the code of the phase. `n`: the number of windows of the phase. |
| 1508 | `    } ph[4] = { { &p->prev, PH_PREV, 1 }, { &p->pfx, PH_PREFIX, 4 }, { &p->pred, PH_PRED, 1 }, { &p->tgt, PH_TARGET, p->nwin } };` | The four entries, in the order of the run: previous activity (1 window), prefix (4 windows), predecessor (1 window) and target (`nwin` windows). |
| 1509 | `    struct win *x = win;` | `x`: the window record that is filled next. |
| 1510 | `    for (int i = 0; i < 4; i++) {` | Loop over the four phases. |
| 1511 | `        const struct part *part = ph[i].part;` | `part`: the part of this phase. |
| 1512 | `        if (part->k < 0)` | Tests whether the plan leaves this phase out. |
| 1513 | `            continue;` | Such a phase gets no window. |
| 1514 | `        for (int j = 0; j < ph[i].n; j++, x++) {` | Loop over the windows of the phase. After each window `x` moves on to the next record. |
| 1515 | `            memset(x, 0, sizeof *x);` | Sets every field of the record to 0. |
| 1516 | `            x->k = part->k;` | The kernel of the window. |
| 1517 | `            x->phase = ph[i].phase;` | The phase of the window. |
| 1518 | `            x->widx = j;` | The number of the window inside its phase, counted from 0. |
| 1519 | `            x->size = part->size;` | The size of the range of the window, in bytes. |
| 1520 | `            x->passes = CHECK_BYTES / part->size ? CHECK_BYTES / part->size : 1;` | `passes`: the number of kernel calls between two clock reads. It is 8 MiB (`CHECK_BYTES`, line 46) divided by the range size, rounded down, and at least 1. |
| 1521 | `            x->dur_ns = (ph[i].phase == PH_TARGET ? p->win_ms : part->ms / ph[i].n) * 1000000L;` | `dur_ns`: the requested duration of the window in ns. A target window gets `win_ms`. Every other window gets the duration of its phase divided by the number of windows of the phase. So each of the 4 prefix windows gets a quarter of the prefix duration. |
| 1522 | `            if (ph[i].phase == PH_TARGET && p->bins) {` | Tests whether this is a target window of a trial with bins. |
| 1523 | `                x->bin_cap = window_bins(p);` | `bin_cap`: the number of bins that the window can close (`window_bins`, line 1496). |
| 1524 | `                x->bin = bin + (size_t)j * (size_t)x->bin_cap;` | The window gets its own part of the bin storage: target window `j` starts at bin `j * bin_cap`. |
| 1525 | `            }` | Ends the `if` of line 1522. |
| 1526 | `        }` | Ends the loop over the windows of the phase (line 1514). |
| 1527 | `    }` | Ends the loop over the phases (line 1510). |
| 1528 | `}` | Ends the function `set_windows`. |

### Function `alloc_records` (trial mode): one memory block for all trial records (lines 1530 to 1564)

| Line | Source | Explanation |
|---:|---|---|
| 1530 | `/* The record storage of all trials: one block, sized from the plan, written` | Comment: the record storage of all trials is one block. Its size comes from the plan. The sentence goes on in line 1531. |
| 1531 | ` * once here so that no page of it is first touched during a trial.` | Comment: the block is written once here. So no page of it gets its first touch during a trial. |
| 1532 | ` * plan_trial() has filled recsz and has checked its bound. */` | Comment: `plan_trial` has filled `recsz` and has checked its upper limit (line 1919). |
| 1533 | `static void alloc_records(struct tw *w)` | Starts the function `alloc_records`. It allocates the record block, touches every page of it, and divides it into the arrays of the records. |
| 1534 | `{` | Opens the body of `alloc_records`. |
| 1535 | `    char *mem = malloc(recsz.bytes);` | Allocates one block of `recsz.bytes` bytes with `malloc`. |
| 1536 | `    if (!mem) {` | Tests whether the allocation failed. |
| 1537 | `        fprintf(stderr, "no memory for %zu bytes of records\n", recsz.bytes);` | Prints `no memory for`, the number of bytes and `bytes of records` to stderr. |
| 1538 | `        exit(2);` | Ends the process with exit status 2. |
| 1539 | `    }` | Ends the `if` of line 1536. |
| 1540 | `    memset(mem, 0, recsz.bytes);` | Fills the block with zero bytes. |
| 1541 | `    /* gcc joins malloc and memset into calloc, and calloc does not write a` | Comment: the compiler gcc joins `malloc` and `memset` into one call of `calloc`. `calloc` does not write a new block. The sentence ends in line 1542. |
| 1542 | `     * fresh block. One volatile store per page is the first touch. */` | Comment: one store per page through a `volatile` pointer is the first touch. |
| 1543 | `    for (size_t at = 0; at < recsz.bytes; at += (size_t)page_bytes)` | Loop over the block in steps of one page (`page_bytes`). |
| 1544 | `        ((volatile char *)mem)[at] = 0;` | Stores one zero byte in each page. The pointer is `volatile`, so the compiler must keep the store. |
| 1545 | `    ((volatile char *)mem)[recsz.bytes - 1] = 0;` | Stores one zero byte in the last byte of the block. |
| 1546 | `    rec = (struct trec *)mem;` | `rec`: the trial records stand at the start of the block, one per trial. |
| 1547 | `    struct win *win = (struct win *)(rec + plan.n);` | `win`: the window records follow the trial records. |
| 1548 | `    struct counts *cnt = (struct counts *)(win + recsz.windows);` | `cnt`: the counter readings follow the window records. |
| 1549 | `    struct bin *bin = (struct bin *)(cnt + recsz.counts);` | `bin`: the bins follow the counter readings. |
| 1550 | `    if (plan.trace)` | Tests for the option `--trace`. |
| 1551 | `        w->log = (struct tev *)(bin + recsz.bins);` | With `--trace` the event log follows the bins. |
| 1552 | `    for (int i = 0; i < plan.n; i++) {` | Loop over the trials of the plan. |
| 1553 | `        const struct trial *p = &plan.tr[i];` | `p`: the trial of the plan. |
| 1554 | `        rec[i].win = win;` | The trial gets the next free window records. |
| 1555 | `        rec[i].nw = trial_windows(p);` | `nw`: the number of windows of the trial (`trial_windows`, line 1489). |
| 1556 | `        rec[i].cnt = p->count == CS_READ ? cnt : NULL;` | Only a trial with the counter state `read` gets counter readings. Every other trial gets NULL. |
| 1557 | `        set_windows(p, win, bin);` | Fills the plan fields of the windows of the trial (`set_windows`, line 1503). |
| 1558 | `        win += rec[i].nw;` | Moves `win` past the windows of this trial. |
| 1559 | `        bin += (size_t)p->nwin * (size_t)window_bins(p);` | Moves `bin` past the bins of this trial: `nwin` times `window_bins(p)`. |
| 1560 | `        if (p->count == CS_READ)` | Tests whether the trial has the counter state `read`. |
| 1561 | `            cnt += p->nwin + 1;` | Moves `cnt` past the `nwin + 1` readings of this trial. |
| 1562 | `    }` | Ends the loop over the trials (line 1552). |
| 1563 | `}` | Ends the function `alloc_records`. |

### Functions `print_s` and `print_p8` (trial mode): the S row and the P row (lines 1565 to 1583)

| Line | Source | Explanation |
|---:|---|---|
| 1565 | `static void print_s(int i)` | Starts the function `print_s`. It prints the S row of trial `i`: the plan line of the trial and two fields of the trial before it. |
| 1566 | `{` | Opens the body of `print_s`. |
| 1567 | `    const struct trial *p = &plan.tr[i];` | `p`: trial `i` of the plan. |
| 1568 | `    printf("S");` | Prints the letter `S`. |
| 1569 | `    for (int f = 0; f < PLAN_FIELDS; f++)` | Loop over the 11 fields of the plan line. |
| 1570 | `        printf(",%s", p->f[f]);` | Prints a comma and one field, as the text of the plan file. |
| 1571 | `    printf(",%s,%s\n", i ? plan.tr[i - 1].f[1] : "none", i ? plan.tr[i - 1].f[6] : "none");` | Prints two more fields and the line break: the fields `cond` and `tgt` of the trial before this one. For trial 0 it prints the word `none` two times. |
| 1572 | `}` | Ends the function `print_s`. |
| 1574 | `static void print_p8(int i, const char *when, const struct page *pg, const long long vm[4])` | Starts the function `print_p8`. It prints the P row of the trial mode: the page state of the buffer before or after the timed sequence of trial `i`. `when` is the word `pre` or `post`. |
| 1575 | `{` | Opens the body of `print_p8`. The P rows of the interval mode have other columns: round, position, thread index and buffer letter come first. Those rows come from `print_p` (line 917). |
| 1576 | `    printf("P,%d,%s", i, when);` | Prints the letter `P`, the trial number and the word `pre` or `post`. |
| 1577 | `    print_na(pg->kb_total);` | Prints the size of the mapping of the buffer in kB, or `NA` (`print_na`, line 909). |
| 1578 | `    print_na(pg->kb_huge);` | Prints the part of the buffer that lies on 2 MiB pages in kB, or `NA`. |
| 1579 | `    for (int k = 0; k < 4; k++)` | Loop over the four counters of `/proc/vmstat`. |
| 1580 | `        print_na(vm[k]);` | Prints one counter, or `NA` for a counter that was not found. |
| 1581 | `    printf("\n");` | Ends the row with a line break. |
| 1582 | `}` | Ends the function `print_p8`. |

### Function `emit_trial` (trial mode): the P, W, B and C rows of one trial (lines 1584 to 1626)

| Line | Source | Explanation |
|---:|---|---|
| 1584 | `/* All rows of one trial after its S row. */` | Comment: the function prints all rows of one trial that come after its S row. |
| 1585 | `static void emit_trial(struct tw *w, int i)` | Starts the function `emit_trial`. It prints the result rows of trial `i` from the record of the trial. It prints bytes and times. It computes no rate. |
| 1586 | `{` | Opens the body of `emit_trial`. |
| 1587 | `    const struct trial *p = &plan.tr[i];` | `p`: trial `i` of the plan. |
| 1588 | `    const struct trec *r = &rec[i];` | `r`: the record of trial `i`. |
| 1589 | `    int g = r->nw - p->nwin; /* index of target window 0 */` | `g`: the index of target window 0 in the window list of the trial: the number of all windows minus the number of target windows. The comment says the same. |
| 1590 | `    int64_t max_gap = -1;` | `max_gap`: the longest time between two windows of the trial, in ns. It starts at -1, which prints as `NA`. |
| 1592 | `    tev_add(w, EV_OUTPUT, 0, 0);` | Logs the start of the output as an event. Without `--trace` this call does nothing. |
| 1593 | `    print_p8(i, "pre", &r->pg[0], r->vm[0]);` | P row `pre`: the page state before the timed sequence (`print_p8`, line 1574). |
| 1594 | `    for (int k = 0; k < r->nw; k++) {` | Loop over all windows of the trial. |
| 1595 | `        const struct win *x = &r->win[k];` | `x`: the record of window `k`. |
| 1596 | `        printf("W,%d,%s,%d,%s,%lu,%lu,%lld,%lld\n", i, phase_name[x->phase], x->widx, kernels[x->k].name,` | W row, one per window. Its columns: the letter `W`, the trial number, the name of the phase, the number of the window inside the phase, the kernel name, `pass_bytes`, `bytes`, `t_start_ns` and `t_end_ns`. This line holds the format and the first four values. |
| 1597 | `               (unsigned long)x->size, (unsigned long)x->bytes, (long long)(x->t_start - t_base_ns),` | Continues the call of line 1596. `pass_bytes` is the range size of one kernel call. `bytes` is the byte count of the window: the range size times the number of kernel calls. `t_start_ns` is the start clock read of the window, in ns after the process start (`t_base_ns`). |
| 1598 | `               (long long)(x->t_end - t_base_ns));` | Continues the call of line 1596: `t_end_ns`, the last clock read of the window, in ns after the process start. The row holds no rate. The file `DECISIONS-bwx8.md` defines the rate of a window as `bytes` divided by `t_end_ns - t_start_ns`. |
| 1599 | `        if (k && x->t_start - r->win[k - 1].t_end > max_gap)` | Tests, for every window but the first, whether the time from the end clock read of the window before to the start clock read of this window is the longest so far. |
| 1600 | `            max_gap = x->t_start - r->win[k - 1].t_end;` | Keeps the longest such time in `max_gap`. |
| 1601 | `    }` | Ends the loop over the windows (line 1594). |
| 1602 | `    for (int k = g; k < r->nw; k++)` | Loop over the target windows of the trial. |
| 1603 | `        for (int b = 0; b < r->win[k].nbin; b++)` | Loop over the bins that the window closed. |
| 1604 | `            printf("B,%d,%d,%d,%lld,%lu\n", i, r->win[k].widx, b, (long long)(r->win[k].bin[b].t_end - t_base_ns),` | B row, one per bin. Its columns: the letter `B`, the trial number, the number of the target window, the bin number, `t_end_ns` and the byte count of the bin. `t_end_ns` is the clock read that closed the bin, in ns after the process start. This line holds the format and the first four values. |
| 1605 | `                   (unsigned long)r->win[k].bin[b].bytes);` | Continues the call of line 1604: the bytes that the window counted from its start to that clock read. |
| 1606 | `    for (int k = 0; r->cnt && k < p->nwin; k++) {` | Loop over the target windows. It runs only for a trial with counter readings (counter state `read`). |
| 1607 | `        const struct counts *c0 = &r->cnt[k], *c1 = &r->cnt[k + 1];` | `c0`, `c1`: the reading before the start clock read of the window, and the reading after its end clock read. |
| 1608 | `        int group = w->t.group_fd >= 0 && !r->read_fail;` | `group`: 1 when a counter group is open and no group reading of the trial failed. |
| 1609 | `        printf("C,%d,%d", i, k);` | C row, one per target window. It starts with the letter `C`, the trial number and the window number. Every value after them is the difference of the two readings. The C rows of the interval mode have other columns: round, position, kernel name, thread index and CPU come first. `main` prints those rows (lines 2243 to 2260). |
| 1610 | `        if (group)` | Tests whether the group readings can be used. |
| 1611 | `            printf(",%llu,%llu", (unsigned long long)(c1->enabled - c0->enabled),` | Columns 4 and 5, `enabled_ns` and `running_ns`: the growth of the enabled time and of the running time between the two readings, in ns. This line holds the enabled time. |
| 1612 | `                   (unsigned long long)(c1->running - c0->running));` | Continues the call of line 1611: the growth of the running time. |
| 1613 | `        else` | The case of no open group, or of a failed group reading. |
| 1614 | `            printf(",NA,NA");` | Columns 4 and 5 are then `NA`. |
| 1615 | `        printf(",%llu", (unsigned long long)(c1->cpu_ns - c0->cpu_ns));` | Column 6, `cputime_ns`: the growth of the thread CPU time between the two readings, in ns. |
| 1616 | `        for (int e = 0; e < cfg.nev; e++) {` | Loop over the events of `cfg`. |
| 1617 | `            int at = w->t.ev_pos[e];` | `at`: the position of the event in a group reading, or -1 for an event that did not open. |
| 1618 | `            if (!group \|\| at < 0)` | Tests whether the value cannot be given: the group readings cannot be used, or the event did not open. |
| 1619 | `                printf(",NA");` | The field is then `NA`. |
| 1620 | `            else` | The case of a value that can be given. |
| 1621 | `                printf(",%llu", (unsigned long long)(c1->val[at] - c0->val[at]));` | One column per event: the count at the second reading minus the count at the first reading. |
| 1622 | `        }` | Ends the loop over the events (line 1616). |
| 1623 | `        printf("\n");` | Ends the row with a line break. |
| 1624 | `    }` | Ends the loop over the target windows (line 1606). |
| 1625 | `    print_p8(i, "post", &r->pg[1], r->vm[1]);` | P row `post`: the page state after the timed sequence. |

### Function `emit_trial` (trial mode): the X rows, the E row and the trace rows (lines 1627 to 1675)

| Line | Source | Explanation |
|---:|---|---|
| 1627 | `    if (r->pg[0].kb_huge < 0 \|\| r->pg[1].kb_huge < 0)` | Tests whether a reading of the page state found no exact entry for the buffer in `/proc/self/smaps`, before or after the timed sequence. |
| 1628 | `        printf("X,%d,coverage_na,the buffer has no exact entry in /proc/self/smaps\n", i);` | X row with the code `coverage_na`. An X row reports a problem: the letter `X`, the trial number, a code and a text. |
| 1629 | `    if (r->close_fail)` | Tests whether a `close` call failed when the counter group was closed at the start of this trial (line 1460). |
| 1630 | `        printf("X,%d,count_close,%d counter descriptors did not close\n", i, r->close_fail);` | X row with the code `count_close` and the number of counter file descriptors that did not close. |
| 1631 | `    if (r->state == CS_FAIL)` | Tests whether the trial wanted counters and an event did not open. |
| 1632 | `        printf("X,%d,count_open,%d of %d events did not open; first: %s\n", i, w->open_fail, cfg.nev, w->open_err);` | X row with the code `count_open`: how many of the events did not open, and the error text of the first one. |
| 1633 | `    if (r->read_fail)` | Tests whether a group reading failed during the timed sequence. |
| 1634 | `        printf("X,%d,count_read,%d reads of the counter group failed\n", i, r->read_fail);` | X row with the code `count_read` and the number of failed group readings. |
| 1635 | `    if (r->cnt && w->t.group_fd >= 0 && !r->read_fail) {` | Tests whether the trial has counter readings that can be used: readings exist, a group is open, and no reading failed. |
| 1636 | `        int m = first_multiplexed(r->cnt, p->nwin);` | `m`: the first target window in which the counters did not count all the time (`first_multiplexed`, line 1444), or -1. |
| 1637 | `        if (m >= 0)` | Tests whether there is such a window. |
| 1638 | `            printf("X,%d,count_multiplexed,target window %d: running_ns %llu below enabled_ns %llu\n", i, m,` | X row with the code `count_multiplexed`: the number of the target window, and its running time and its enabled time in ns. The running time is the smaller one. |
| 1639 | `                   (unsigned long long)(r->cnt[m + 1].running - r->cnt[m].running),` | Continues the call of line 1638: the growth of the running time in that window. |
| 1640 | `                   (unsigned long long)(r->cnt[m + 1].enabled - r->cnt[m].enabled));` | Continues the call of line 1638: the growth of the enabled time in that window. |
| 1641 | `    }` | Ends the `if` of line 1635. |
| 1642 | `    if (r->sink_ok == 0)` | Tests whether the sum check of the old read kernel failed (line 1485). |
| 1643 | `        printf("X,%d,sink,the last old read did not leave the sum of its range in the sink\n", i);` | X row with the code `sink`: the last old read kernel did not leave the sum of its range in the sink. |
| 1645 | `    printf("E,%d,%lld,%llu", i, (long long)(r->win[r->nw - 1].t_end - r->win[0].t_start),` | E row, one per trial: the summary of the trial. Columns 1 to 4: the letter `E`, the trial number, `wall_ns` and `cpu_ns`. `wall_ns` is the time from the start clock read of the first window to the end clock read of the last window, in ns. |
| 1646 | `           (unsigned long long)(r->cpu[1] - r->cpu[0]));` | Continues the call of line 1645: `cpu_ns`, the growth of the thread CPU time between the two `tcpu` calls of `run_trial` (line 1480, line 1482), in ns. |
| 1647 | `    if (r->nvcsw[0] < 0 \|\| r->nvcsw[1] < 0)` | Tests whether a reading of the context switches failed. |
| 1648 | `        printf(",NA,NA");` | Columns 5 and 6 are then `NA`. |
| 1649 | `    else` | The case of two good readings. |
| 1650 | `        printf(",%ld,%ld", r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]);` | Columns 5 and 6, `nvcsw` and `nivcsw`: the numbers of voluntary and of involuntary context switches of the worker between the two `switches` calls of `run_trial` (line 1479, line 1483). |
| 1651 | `    print_na(g ? r->win[g].t_start - r->win[g - 1].t_end : -1);` | Column 7, `gap_ns`: the time from the end clock read of the window before target window 0 to the start clock read of target window 0. A trial without a window before its first target window prints `NA`. |
| 1652 | `    print_na(max_gap);` | Column 8, `max_boundary_gap_ns`: `max_gap`, the longest time between two windows of the trial (lines 1599 to 1600). A trial with one window prints `NA`. |
| 1653 | `    if (r->sink_ok < 0)` | Tests whether the trial ran no old read kernel. |
| 1654 | `        printf(",NA");` | Column 9, `sink_ok`, is then `NA`. |
| 1655 | `    else` | The case of a trial that ran an old read kernel. |
| 1656 | `        printf(",%d", r->sink_ok);` | Column 9 is then 1 for a right sum and 0 for a wrong sum. |
| 1657 | `    printf(",%s\n", count_name[r->state]);` | Column 10, `count_state`: the counter state of the trial as a word: `closed`, `open`, `read` or `fail`. The line break ends the row. |
| 1659 | `    for (long n = 0; n < w->nlog; n++) {` | Loop over the events of the trace. Without `--trace` the log holds no event. |
| 1660 | `        const struct tev *e = &w->log[n];` | `e`: one event of the log. |
| 1661 | `        if (e->ev == EV_KERNEL_FIRST)` | Tests whether the event is the first kernel call of a window. |
| 1662 | `            printf("TR,%d,%ld,%s:%s:%d,%lld\n", i, n, event_name[e->ev], phase_name[e->phase], e->widx,` | TR row of such an event: the letters `TR`, the trial number, the event number, then the event name with the phase name and the window number (joined by colons), then the time of the event. |
| 1663 | `                   (long long)(e->t - t_base_ns));` | Continues the call of line 1662: the time of the event, in ns after the process start. |
| 1664 | `        else` | The case of every other event. |
| 1665 | `            printf("TR,%d,%ld,%s,%lld\n", i, n, event_name[e->ev], (long long)(e->t - t_base_ns));` | TR row of another event: the letters `TR`, the trial number, the event number, the event name and the time in ns after the process start. For an event that is not a clock read this is the time of the clock read before it. |
| 1666 | `    }` | Ends the loop over the events (line 1659). |
| 1667 | `    if (w->ndrop)` | Tests whether events did not fit into the log. |
| 1668 | `        printf("# trace_dropped,%d,%ld\n", i, w->ndrop);` | Prints the line `# trace_dropped` with the trial number and the number of events that the log did not keep. The log keeps 1048576 events per trial (`TRACE_CAP`, line 1161). |
| 1669 | `    /* --trace: minor page faults of the worker between the two rusage reads.` | Comment: with `--trace` the next statement prints the minor page faults of the worker between the two `getrusage` readings. |
| 1670 | `     * Above 0: a page was first touched inside the timed sequence. */` | Comment: a value above 0 means that a page got its first touch inside the timed sequence. The two readings also enclose the two `tcpu` calls of `run_trial` (line 1480, line 1482). |
| 1671 | `    if (w->log)` | Tests whether a log exists (`--trace`). |
| 1672 | `        printf("# minflt,%d,%ld\n", i, r->minflt[0] < 0 \|\| r->minflt[1] < 0 ? -1 : r->minflt[1] - r->minflt[0]);` | Prints the line `# minflt` with the trial number and the number of minor page faults between the two `switches` calls. It prints -1 when a reading failed. |
| 1673 | `    fflush(stdout);` | `fflush` writes the buffered rows to the output before the next trial starts. |
| 1674 | `}` | Ends the function `emit_trial`. |

### Function `trial_worker` (trial mode): pinning, buffer, first touch and records (lines 1676 to 1696)

| Line | Source | Explanation |
|---:|---|---|
| 1676 | `static void *trial_worker(void *arg)` | Starts the function `trial_worker`, the start function of the one worker thread of the trial mode. `trial_main` creates the thread in line 2051. |
| 1677 | `{` | Opens the body of `trial_worker`. |
| 1678 | `    struct tw *w = arg;` | `w`: the state of the worker (line 1235). |
| 1679 | `    volatile uint64_t sink = 0;` | `sink`: the volatile variable on the stack of the worker that receives the sum of an old read kernel. It starts at 0. |
| 1680 | `    int madvise_ok;` | `madvise_ok`: will hold whether the request for the page policy succeeded (line 1692). |
| 1682 | `    pin_cpu(cfg.cpus[0]);` | CPU pinning. The worker pins itself to the one CPU of `--cpus` (`pin_cpu`, line 331). |
| 1683 | `    if (sched_getcpu() != cfg.cpus[0]) {` | Asks Linux on which CPU the thread runs now (`sched_getcpu`) and tests whether it is another CPU than the one of `--cpus`. |
| 1684 | `        fprintf(stderr, "the worker runs on CPU %d, not on CPU %d\n", sched_getcpu(), cfg.cpus[0]);` | Prints both CPU numbers to stderr. |
| 1685 | `        exit(2);` | Ends the process with exit status 2. |
| 1686 | `    }` | Ends the `if` of line 1683. |
| 1687 | `    w->v = ((uint64_t)getpid() + 1) * 0x9E3779B97F4A7C15ULL;` | `w->v`: the value that the first touch of line 1693 stores into the 8-byte words of the buffer: the process id (`getpid`) plus 1, times a fixed 64-bit constant. |
| 1688 | `    w->t.group_fd = -1;` | The worker has no counter group yet. |
| 1689 | `    w->t.a = alloc_buf();` | Buffer allocation. `alloc_buf` (line 350) maps the one buffer of the worker: it starts at a 2 MiB boundary and has the size of `--bytes`, rounded up to a multiple of 2 MiB. |
| 1690 | `    /* alloc_buf() does not return the result of its madvise. The same request` | Comment: `alloc_buf` does not return the result of its `madvise` call. The sentence about the next statement starts here. |
| 1691 | `     * again gives it. */` | Comment: the same request once more gives the result. |
| 1692 | `    madvise_ok = madvise(w->t.a, buf_len(), cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) == 0;` | Repeats the `madvise` request of `alloc_buf` for the buffer: a request for 2 MiB pages, or with `--no-thp` for no such pages. `madvise_ok` is 1 when the call succeeded. |
| 1693 | `    k_write(w->t.a, cfg.bytes / 8, w->v); /* first touch by the pinned worker */` | First touch. The pinned worker stores `w->v` into `cfg.bytes / 8` words of 8 bytes with `k_write` (line 447): every word of the `--bytes` range of the buffer. The buffer is longer than this range only when `--bytes` is not a multiple of 2 MiB (line 344). This line is not timed. |
| 1694 | `    alloc_records(w);` | `alloc_records` (line 1533) allocates the record block and touches every page of it. |
| 1695 | `    w->last_t = t_base_ns;` | The trace starts with the process start time as the time of the latest clock read. |

### Function `trial_worker` (trial mode): header lines and the rows before the first trial (lines 1697 to 1739)

| Line | Source | Explanation |
|---:|---|---|
| 1697 | `    printf("# bwx8 trial mode: GB = 1e9 bytes; times are whole ns since process start on CLOCK_MONOTONIC\n"` | Starts the `printf` call that prints the header lines of the trial mode. Each header line starts with `#`. This first line says: GB means 1e9 bytes, and times are whole ns after the process start on the clock `CLOCK_MONOTONIC`. The text names `bwx8`, the version of the runner that added the trial mode. |
| 1698 | `           "# S,trial,cond,rep,prev,pfx,pred,tgt,nwin,win_ms,count,bins,prev_cond,prev_tgt\n"` | Text of the header: the column names of the S rows. |
| 1699 | `           "# P,trial,when,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n"` | Text of the header: the column names of the P rows of the trial mode. |
| 1700 | `           "# W,trial,phase,widx,kernel,pass_bytes,bytes,t_start_ns,t_end_ns\n"` | Text of the header: the column names of the W rows. |
| 1701 | `           "# B,trial,widx,bin,t_end_ns,bytes_since_window_start\n"` | Text of the header: the column names of the B rows. |
| 1702 | `           "# C,trial,widx,enabled_ns,running_ns,cputime_ns");` | Text of the header: the first six column names of the C rows of the trial mode. The header line has no line break yet. |
| 1703 | `    for (int e = 0; e < cfg.nev; e++)` | Loop over the events of `cfg`. |
| 1704 | `        printf(",%s", cfg.ev_name[e]);` | Appends one event name per event to the header line of the C rows. |
| 1705 | `    printf("\n# E,trial,wall_ns,cpu_ns,nvcsw,nivcsw,gap_ns,max_boundary_gap_ns,sink_ok,count_state\n"` | Ends the header line of the C rows. Then comes the header line with the column names of the E rows. |
| 1706 | `           "# X,trial,code,text\n"` | Text of the header: the column names of the X rows. |
| 1707 | `           "# TR,trial,n,event,t_ns; t_ns of an event that is not a clock read is the time of the clock read before it\n");` | Text of the header: the column names of the TR rows. The text adds: the time of an event that is not a clock read is the time of the clock read before it. |
| 1708 | `    printf("M,mode,trial\nM,cpu,%d\nM,ctl_cpu,%d\nM,bytes,%lu\nM,thp,%s\nM,madvise_ok,%d\nM,check_bytes,%lu\nM,kernels,%s\n",` | M rows. Each M row holds one setting or one fact in the form `M,name,value`. This call prints `mode` (the word `trial`), `cpu` (the worker CPU), `ctl_cpu` (the CPU of the controlling thread), `bytes` (the buffer size), `thp` (the page policy), `madvise_ok`, `check_bytes` and `kernels`. |
| 1709 | `           cfg.cpus[0], plan.ctl_cpu, (unsigned long)cfg.bytes, cfg.use_thp ? "madvise" : "nohugepage", madvise_ok,` | Continues the call of line 1708: the values of `cpu`, `ctl_cpu`, `bytes`, `thp` (the word `madvise` or `nohugepage`) and `madvise_ok`. |
| 1710 | `           (unsigned long)CHECK_BYTES, STANDIN ? "STAND-IN" : "aarch64");` | Continues the call of line 1708: `check_bytes` is `CHECK_BYTES` (8388608 bytes, which is 8 MiB). `kernels` is `aarch64`, or `STAND-IN` for a build with stand-in kernels. |
| 1711 | `    printf("M,plan_fnv1a64,%016llx\nM,ntrials,%d\nM,rec_windows,%zu\nM,rec_bins,%zu\nM,rec_counts,%zu\nM,rec_trace,%zu\n"` | More M rows: `plan_fnv1a64` (the checksum of the plan file, 16 hexadecimal digits), `ntrials` (the number of trials), and the sizes of the record storage: `rec_windows`, `rec_bins`, `rec_counts` and `rec_trace`. |
| 1712 | `           "M,rec_bytes,%zu\nM,trace,%d\n",` | Continues the format of line 1711: `rec_bytes` (the size of the record block in bytes) and `trace` (0 or 1). |
| 1713 | `           (unsigned long long)plan.hash, plan.n, recsz.windows, recsz.bins, recsz.counts, recsz.trace, recsz.bytes,` | Continues the call of line 1711: the values of the first seven of these rows. |
| 1714 | `           plan.trace);` | Continues the call of line 1711: the value of `trace`. |
| 1715 | `    if (cfg.pmu_type < 0)` | Tests whether no PMU type was given. |
| 1716 | `        printf("M,pmu_type,none\n");` | M row `pmu_type` with the word `none`. |
| 1717 | `    else` | The case of a given PMU type. |
| 1718 | `        printf("M,pmu_type,%ld\n", cfg.pmu_type);` | M row `pmu_type` with the number. |
| 1719 | `    printf("M,events,%s", cfg.nev ? "" : "none");` | Starts the M row `events`. Without events its value is the word `none`. |
| 1720 | `    for (int e = 0; e < cfg.nev; e++)` | Loop over the events of `cfg`. |
| 1721 | `        printf("%s%s=0x%llx", e ? ";" : "", cfg.ev_name[e], (unsigned long long)cfg.ev_code[e]);` | Prints one event as its name, the sign `=` and its code in hexadecimal with `0x`. A semicolon separates two events. |
| 1722 | `    printf("\n");` | Ends the row with a line break. |
| 1723 | `    for (int i = 0; i < plan.npair; i++) {` | Loop over the `key=value` pairs of the second line of the plan. |
| 1724 | `        char *eq = strchr(plan.pair[i], '=');` | `eq`: the place of the `=` sign in the pair. |
| 1725 | `        printf("M,plan.%.*s,%s\n", (int)(eq - plan.pair[i]), plan.pair[i], eq + 1);` | One M row per pair: the name is `plan.` plus the key, and the value is the text after the `=` sign. |
| 1726 | `    }` | Ends the loop of line 1723. |
| 1727 | `    for (int k = 0; k < K_COUNT; k++) {` | Loop over the kernel table. |
| 1728 | `        int used = 0;` | `used`: becomes 1 when a trial of the plan uses kernel `k`. |
| 1729 | `        for (int i = 0; i < plan.n && !used; i++) {` | Loop over the trials. It stops at the first trial that uses the kernel. |
| 1730 | `            const struct trial *p = &plan.tr[i];` | `p`: one trial of the plan. |
| 1731 | `            used = p->prev.k == k \|\| p->pfx.k == k \|\| p->pred.k == k \|\| p->tgt.k == k;` | Tests whether one of the four parts of the trial names kernel `k`. |
| 1732 | `        }` | Ends the loop of line 1729. |
| 1733 | `        if (used)` | Tests whether the plan uses the kernel. |
| 1734 | `            printf("K,%s,%lx,%lu\n", kernels[k].name, (unsigned long)(uintptr_t)kernels[k].fn,` | K row, one per kernel that the plan uses: the letter `K`, the kernel name, the address of its function in hexadecimal, and this address modulo 64. |
| 1735 | `                   (unsigned long)((uintptr_t)kernels[k].fn % 64));` | Continues the call of line 1734: the address modulo 64. |
| 1736 | `    }` | Ends the loop over the kernel table (line 1727). |
| 1737 | `    if (!madvise_ok)` | Tests whether the `madvise` request of line 1692 failed. |
| 1738 | `        printf("X,-1,madvise,the page policy request failed\n");` | X row with the trial number -1 and the code `madvise`: the request for the page policy failed. |

### Function `trial_worker` (trial mode): the loop over the trials and the end (lines 1740 to 1756)

| Line | Source | Explanation |
|---:|---|---|
| 1740 | `    for (int i = 0; i < plan.n; i++) {` | Loop over the trials, in the order of the plan. |
| 1741 | `        w->nlog = w->ndrop = 0;` | Empties the trace: no event in the log, and a count of 0 for the events that did not fit. |
| 1742 | `        w->cur_phase = -1;` | No window counts as logged yet. So the first kernel call of the trial is logged (line 1299). |
| 1743 | `        tev_add(w, EV_OUTPUT, 0, 0);` | Logs the start of the output as an event. Without `--trace` this call does nothing. |
| 1744 | `        print_s(i);` | Prints the S row of the trial (`print_s`, line 1565). |
| 1745 | `        fflush(stdout);` | Writes the buffered rows to the output before the trial runs. |
| 1746 | `        run_trial(w, &plan.tr[i], &rec[i], &sink);` | Runs the trial (`run_trial`, line 1454). That function prints nothing. So the process writes no output inside a timed sequence. |
| 1747 | `        emit_trial(w, i);` | Prints the result rows of the trial (`emit_trial`, line 1585). |
| 1748 | `    }` | Ends the loop over the trials (line 1740). |
| 1749 | `    if (w->group_open)` | Tests whether the counter group is still open after the last trial. |
| 1750 | `        count_close(w);` | Then the group is closed (`count_close`, line 1375). |
| 1751 | `    if (w->close_fail)` | Tests whether a `close` call failed. |
| 1752 | `        printf("X,-1,count_close,%d counter descriptors did not close\n", w->close_fail);` | X row with the trial number -1 and the code `count_close`: the number of counter file descriptors that did not close. |
| 1753 | `    fflush(stdout);` | Writes the buffered rows to the output. |
| 1754 | `    return NULL;` | The worker thread ends. `trial_main` waits for its end in line 2055. |
| 1755 | `}` | Ends the function `trial_worker`. |

### Function `plan_bad` (trial mode): report a defect of the plan file (lines 1757 to 1767)

| Line | Source | Explanation |
|---:|---|---|
| 1757 | `static void plan_bad(int line, const char *fmt, ...)` | Starts the function `plan_bad`. It reports a defect of the plan file on stderr and ends the process with exit status 2. `line` is the number of the plan line. `fmt` and the arguments after it form the message, as in `printf`. |
| 1758 | `{` | Opens the body of `plan_bad`. |
| 1759 | `    va_list ap;` | `ap`: the list of the arguments that follow `fmt`. |
| 1760 | `    fprintf(stderr, "bad plan %s, line %d: ", plan.path, line);` | Prints the start of the message to stderr: the words `bad plan`, the path of the plan file, the word `line` and the number of the plan line. |
| 1761 | `    va_start(ap, fmt);` | Starts the reading of the arguments that follow `fmt`. |
| 1762 | `    vfprintf(stderr, fmt, ap);` | `vfprintf` prints the message itself to stderr. It builds the text from `fmt` and these arguments. |
| 1763 | `    va_end(ap);` | Ends the reading of the arguments. |
| 1764 | `    fprintf(stderr, "\n");` | Ends the message with a line break. |
| 1765 | `    exit(2);` | Ends the process with exit status 2. |
| 1766 | `}` | Ends the function `plan_bad`. |

### Functions `plan_long` and `plan_size` (trial mode): a number and a size of the plan (lines 1768 to 1801)

| Line | Source | Explanation |
|---:|---|---|
| 1768 | `/* A whole number in [lo, hi] made of digits only. */` | Comment: the function accepts a whole number from `lo` to `hi` that is made of digits only. |
| 1769 | `static int plan_long(const char *s, long lo, long hi, long *out)` | Starts the function `plan_long`. It turns the text `s` into a whole number. For a good text it stores the number in `*out` and returns 1. For any other text it returns 0. The caller then reports the defect with `plan_bad`. |
| 1770 | `{` | Opens the body of `plan_long`. |
| 1771 | `    char *end;` | `end`: will point to the first character that `strtol` did not read. |
| 1772 | `    if (*s < '0' \|\| *s > '9')` | Tests whether the first character is not a decimal digit. So a sign or a space at the start is rejected. |
| 1773 | `        return 0;` | Such a text returns 0. |
| 1774 | `    errno = 0;` | Sets `errno` to 0. After the next call a value other than 0 shows that the number was too large for the type. |
| 1775 | `    long v = strtol(s, &end, 10);` | `strtol` reads the text as a decimal number. |
| 1776 | `    if (*end != '\0' \|\| errno != 0 \|\| v < lo \|\| v > hi)` | Tests for four defects: other text follows the number, the number was too large for the type, the number is below `lo`, or it is above `hi`. |
| 1777 | `        return 0;` | A defect returns 0. |
| 1778 | `    *out = v;` | Stores the number. |
| 1779 | `    return 1;` | Returns 1. |
| 1780 | `}` | Ends the function `plan_long`. |
| 1782 | `/* A whole number above 0 with an optional K, M or G. */` | Comment: the function accepts a whole number above 0 with an optional letter `K`, `M` or `G`. |
| 1783 | `static int plan_size(const char *s, uint64_t *out)` | Starts the function `plan_size`. It turns a size text such as `8M` into a number of bytes. For a good text it stores the bytes in `*out` and returns 1. For any other text it returns 0. |
| 1784 | `{` | Opens the body of `plan_size`. |
| 1785 | `    char *end;` | `end`: will point to the first character that `strtoull` did not read. |
| 1786 | `    int shift = 0;` | `shift`: the number of bits by which a letter shifts the number. It is 0 without a letter. |
| 1787 | `    if (*s < '0' \|\| *s > '9')` | Tests whether the first character is not a decimal digit. |
| 1788 | `        return 0;` | Such a text returns 0. |
| 1789 | `    errno = 0;` | Sets `errno` to 0, as in line 1774. |
| 1790 | `    unsigned long long v = strtoull(s, &end, 10);` | `strtoull` reads the text as a decimal number. |
| 1791 | `    switch (*end) {` | Looks at the character after the number. |
| 1792 | `    case 'K': shift = 10; end++; break;` | The letter `K`: the number times 1024 (a shift by 10 bits). |
| 1793 | `    case 'M': shift = 20; end++; break;` | The letter `M`: the number times 1048576, which gives MiB (a shift by 20 bits). |
| 1794 | `    case 'G': shift = 30; end++; break;` | The letter `G`: the number times 1073741824 (a shift by 30 bits). Only capital letters are accepted in a plan. |
| 1795 | `    }` | Ends the `switch` of line 1791. |
| 1796 | `    if (*end != '\0' \|\| errno != 0 \|\| v == 0 \|\| v > (UINT64_MAX >> shift))` | Tests for four defects: other text follows, the number was too large for the type, the number is 0, or the size in bytes does not fit into 64 bits. |
| 1797 | `        return 0;` | A defect returns 0. |
| 1798 | `    *out = (uint64_t)v << shift;` | Stores the size in bytes: the number shifted left by `shift` bits. |
| 1799 | `    return 1;` | Returns 1. |
| 1800 | `}` | Ends the function `plan_size`. |

### Function `plan_part` (trial mode): one kernel field of a trial line (lines 1802 to 1834)

| Line | Source | Explanation |
|---:|---|---|
| 1802 | `/* "KERNEL@SIZE:MS" (with_ms, where "-" is also allowed) or "KERNEL@SIZE". */` | Comment: the field has the form `KERNEL@SIZE:MS` or the form `KERNEL@SIZE`. The first form holds when `with_ms` is set. Then the text `-` is also allowed. |
| 1803 | `static void plan_part(int line, const char *what, const char *s, int with_ms, struct part *p)` | Starts the function `plan_part`. It reads one kernel field `s` of a trial line into `*p`: the index of the kernel, the size in bytes and the duration in ms. `line` is the number of the plan line and `what` the name of the field. Both are for the error message. A defect ends the process through `plan_bad` (line 1757). |
| 1804 | `{` | Opens the body of `plan_part`. |
| 1805 | `    char buf[96];` | `buf`: room for a copy of the field of at most 95 characters. The function cuts the copy into pieces. |
| 1806 | `    p->k = -1;` | Start value: no kernel (`k` is -1). |
| 1807 | `    p->size = 0;` | Start value: the size 0. |
| 1808 | `    p->ms = 0;` | Start value: the duration 0. |
| 1809 | `    if (with_ms && !strcmp(s, "-"))` | Tests whether the field may be left out (`with_ms` is 1) and is the text `-`. |
| 1810 | `        return;` | Then the part is absent, and `p->k` stays -1. |
| 1811 | `    if (strlen(s) >= sizeof buf)` | Tests whether the field has 96 characters or more. |
| 1812 | `        plan_bad(line, "%s is too long", what);` | Such a field is a defect. The message says that the field is too long. |
| 1813 | `    strcpy(buf, s);` | Copies the field into `buf`. |
| 1814 | `    char *at = strchr(buf, '@'), *colon = at ? strchr(at, ':') : NULL;` | `at`: the place of the `@` in the field. `colon`: the place of a colon after the `@`. Each is NULL when the character is missing. |
| 1815 | `    if (!at \|\| with_ms != (colon != NULL))` | Tests for a wrong form. The field has no `@`. Or it has no colon although a duration is needed. Or it has a colon although no duration is allowed. |
| 1816 | `        plan_bad(line, "%s '%s' is not %s", what, s, with_ms ? "'-' or KERNEL@SIZE:MS" : "KERNEL@SIZE");` | The message names the field, its text and the form that is needed. |
| 1817 | `    *at = '\0';` | Ends the kernel name at the `@`: a zero byte replaces the `@`. |
| 1818 | `    if (colon)` | Tests whether the field has a colon. |
| 1819 | `        *colon = '\0';` | Ends the size text at the colon. |
| 1820 | `    int k = 0;` | `k`: the index into the kernel table. The search starts at entry 0. |
| 1821 | `    while (k < K_COUNT && strcmp(buf, kernels[k].name))` | Searches the kernel table for the name, as in line 1104. |
| 1822 | `        k++;` | The body of the search loop: goes on to the next entry of the table. |
| 1823 | `    if (k == K_COUNT)` | Tests whether no entry has the name. |
| 1824 | `        plan_bad(line, "%s: unknown kernel '%s'", what, buf);` | The message says that the kernel is unknown. |
| 1825 | `    if (kernels[k].type != T_READ && kernels[k].type != T_OLDREAD)` | Tests whether the kernel is not a read kernel: its type is not `T_READ` and not `T_OLDREAD`. So the trial mode accepts read kernels only. |
| 1826 | `        plan_bad(line, "%s: '%s' is not a read kernel", what, buf);` | The message says that the kernel is not a read kernel. |
| 1827 | `    if (!plan_size(at + 1, &p->size) \|\| p->size % 256 != 0 \|\| p->size > cfg.bytes)` | Reads the size with `plan_size` (line 1783) and tests for three defects: the text is not a size, the size is not a multiple of 256 bytes, or it is above the `--bytes` value. |
| 1828 | `        plan_bad(line, "%s: size '%s' must be a multiple of 256, above 0 and at most --bytes (%lu)", what, at + 1,` | The message names the size text and the rule: a multiple of 256, above 0 and at most the `--bytes` value. |
| 1829 | `                 (unsigned long)cfg.bytes);` | Continues the call of line 1828: the `--bytes` value. |
| 1830 | `    if (colon && !plan_long(colon + 1, 1, MAX_MS, &p->ms))` | For a field with a duration: reads it with `plan_long` (line 1769). It must be a whole number from 1 to 3600000 ms (`MAX_MS`, 1 hour). |
| 1831 | `        plan_bad(line, "%s: bad duration '%s' (whole ms from 1 to %ld)", what, colon + 1, MAX_MS);` | The message names the bad duration and the allowed range. |
| 1832 | `    p->k = k;` | Stores the index of the kernel. From here on the part exists. |
| 1833 | `}` | Ends the function `plan_part`. |

### Function `plan_pairs` (trial mode): the second line of the plan file (lines 1835 to 1865)

| Line | Source | Explanation |
|---:|---|---|
| 1835 | `/* Line 2: "# key=value key=value ...". bytes and cpu must equal the options. */` | Comment: the second line of the plan has the form `# key=value key=value ...`. The values of `bytes` and `cpu` must equal the options. |
| 1836 | `static void plan_pairs(char *s)` | Starts the function `plan_pairs`. It splits the second line of the plan at each space and keeps a pointer to every pair in `plan.pair`. It also checks the pairs `bytes=` and `cpu=`. |
| 1837 | `{` | Opens the body of `plan_pairs`. |
| 1838 | `    int have_bytes = 0, have_cpu = 0;` | `have_bytes`, `have_cpu`: become 1 when the line holds a pair `bytes=` and a pair `cpu=`. |
| 1839 | `    if (strncmp(s, "# ", 2))` | Tests whether the line does not start with `#` and a space. |
| 1840 | `        plan_bad(2, "the line must start with '# '");` | That is a defect of the plan (`plan_bad`, line 1757). |
| 1841 | `    for (char *tok = s + 2, *sp; tok; tok = sp ? sp + 1 : NULL) {` | Loop over the pairs. `tok` is the start of one pair. `sp` is the space after it, or NULL after the last pair. |
| 1842 | `        sp = strchr(tok, ' ');` | Finds the next space. |
| 1843 | `        if (sp)` | Tests whether a space was found. |
| 1844 | `            *sp = '\0';` | Ends the pair at the space: a zero byte replaces the space. |
| 1845 | `        char *eq = strchr(tok, '=');` | `eq`: the place of the `=` sign in the pair, or NULL. |
| 1846 | `        if (!eq \|\| eq == tok \|\| strchr(tok, ',') \|\| plan.npair == MAX_PAIRS)` | Tests for four defects: no `=` sign, an empty key, a comma in the pair, or a 65th pair (`MAX_PAIRS` is 64). |
| 1847 | `            plan_bad(2, "bad key=value pair '%s'", tok);` | The message names the bad pair. |
| 1848 | `        plan.pair[plan.npair++] = tok;` | Keeps a pointer to the pair. `trial_worker` prints each pair as an M row (lines 1723 to 1726). |
| 1849 | `        if (!strncmp(tok, "bytes=", 6)) {` | Tests whether the pair starts with `bytes=`. |
| 1850 | `            uint64_t b;` | `b`: the size of the pair in bytes. |
| 1851 | `            if (!plan_size(eq + 1, &b) \|\| b != cfg.bytes)` | Reads the size with `plan_size` and tests whether it is no size or differs from the `--bytes` value. |
| 1852 | `                plan_bad(2, "%s differs from --bytes %lu", tok, (unsigned long)cfg.bytes);` | Then the plan has a defect. The message names the pair and the `--bytes` value. |
| 1853 | `            have_bytes = 1;` | Notes that the line has a pair `bytes=`. |
| 1854 | `        }` | Ends the `if` of line 1849. |
| 1855 | `        if (!strncmp(tok, "cpu=", 4)) {` | Tests whether the pair starts with `cpu=`. |
| 1856 | `            long c;` | `c`: the CPU number of the pair. |
| 1857 | `            if (!plan_long(eq + 1, 0, MAX_USE_CPU, &c) \|\| c != cfg.cpus[0])` | Reads the number with `plan_long` (0 to `MAX_USE_CPU`) and tests whether it is no such number or differs from the first CPU of `--cpus`. |
| 1858 | `                plan_bad(2, "%s differs from --cpus %d", tok, cfg.cpus[0]);` | Then the plan has a defect. The message names the pair and the CPU of `--cpus`. |
| 1859 | `            have_cpu = 1;` | Notes that the line has a pair `cpu=`. |
| 1860 | `        }` | Ends the `if` of line 1855. |
| 1861 | `    }` | Ends the loop over the pairs (line 1841). |
| 1862 | `    if (!have_bytes \|\| !have_cpu)` | Tests whether one of the two pairs is missing. |
| 1863 | `        plan_bad(2, "bytes= and cpu= are needed");` | That is a defect. The message says that `bytes=` and `cpu=` are needed. |
| 1864 | `}` | Ends the function `plan_pairs`. |

### Function `plan_trial` (trial mode): one trial line of the plan (lines 1866 to 1923)

| Line | Source | Explanation |
|---:|---|---|
| 1866 | `static void plan_trial(int line, char *s)` | Starts the function `plan_trial`. It reads one trial line `s` of the plan, checks every field and adds one `struct trial` to `plan.tr`. `line` is the number of the plan line. A defect ends the process through `plan_bad` (line 1757). |
| 1867 | `{` | Opens the body of `plan_trial`. |
| 1868 | `    char *f[PLAN_FIELDS];` | `f`: the 11 fields of the line as text. |
| 1869 | `    int nf = 0;` | `nf`: the number of fields found so far. |
| 1870 | `    long v;` | `v`: a number that `plan_long` returns. |
| 1871 | `    for (char *tok = s, *sp; tok; tok = sp ? sp + 1 : NULL) {` | Loop over the fields. `tok` is the start of one field. `sp` is the space after it, or NULL after the last field. |
| 1872 | `        sp = strchr(tok, ' ');` | Finds the next space. |
| 1873 | `        if (sp)` | Tests whether a space was found. |
| 1874 | `            *sp = '\0';` | Ends the field at the space: a zero byte replaces the space. |
| 1875 | `        if (nf == PLAN_FIELDS \|\| *tok == '\0')` | Tests for two defects: a 12th field, or an empty field. An empty field comes from two spaces one after the other, from a space at the start or at the end of the line, or from an empty line. |
| 1876 | `            plan_bad(line, "%d fields separated by single spaces are needed", PLAN_FIELDS);` | The message says that 11 fields separated by single spaces are needed. |
| 1877 | `        f[nf++] = tok;` | Keeps a pointer to the field and counts it. |
| 1878 | `    }` | Ends the loop over the fields (line 1871). |
| 1879 | `    if (nf != PLAN_FIELDS)` | Tests whether the line has fewer than 11 fields. |
| 1880 | `        plan_bad(line, "%d fields separated by single spaces are needed, %d found", PLAN_FIELDS, nf);` | The message says how many fields are needed and how many were found. |
| 1881 | `    plan.tr = realloc(plan.tr, ((size_t)plan.n + 1) * sizeof *plan.tr);` | `realloc` makes the array `plan.tr` one trial longer. |
| 1882 | `    if (!plan.tr)` | Tests whether the memory could not be given. |
| 1883 | `        plan_bad(line, "no memory");` | That ends the process through `plan_bad` with the message `no memory`. |
| 1884 | `    struct trial *p = &plan.tr[plan.n];` | `p`: the new trial. |
| 1885 | `    memcpy(p->f, f, sizeof f);` | Copies the 11 field pointers into the trial. `print_s` prints these texts in the S row (line 1570). |
| 1886 | `    if (!plan_long(f[0], 0, 1000000, &v) \|\| v != plan.n)` | Field 1, `trial`: it must be the number of this trial, counted from 0 in the order of the file. |
| 1887 | `        plan_bad(line, "trial '%s': the trial numbers must be 0, 1, 2, ... (%d expected)", f[0], plan.n);` | The message names the field and the number that was expected. |
| 1888 | `    if (strchr(f[1], ','))` | Field 2, `cond`, a label of the condition: it must hold no comma. |
| 1889 | `        plan_bad(line, "cond '%s' holds a comma", f[1]);` | The message names the label. |
| 1890 | `    if (!plan_long(f[2], 1, 4, &v))` | Field 3, `rep`: a whole number from 1 to 4. The file `DECISIONS-bwx8.md` calls it the number of this repeat of the condition in the process. |
| 1891 | `        plan_bad(line, "rep '%s' is not 1 to 4", f[2]);` | The message names the bad value. |
| 1892 | `    plan_part(line, "prev", f[3], 1, &p->prev);` | Field 4, `prev`: the previous activity. `plan_part` (line 1803) reads it. It has a duration and may be `-`. |
| 1893 | `    plan_part(line, "pfx", f[4], 1, &p->pfx);` | Field 5, `pfx`: the prefix. It has a duration and may be `-`. |
| 1894 | `    plan_part(line, "pred", f[5], 1, &p->pred);` | Field 6, `pred`: the predecessor. It has a duration and may be `-`. |
| 1895 | `    plan_part(line, "tgt", f[6], 0, &p->tgt);` | Field 7, `tgt`: the target. It has no duration field and cannot be left out. |
| 1896 | `    if (p->pfx.k >= 0 && p->pfx.ms % 4 != 0)` | Tests whether the trial has a prefix whose duration is not a multiple of 4 ms. The prefix runs as 4 windows of a quarter of its duration each (line 1521). |
| 1897 | `        plan_bad(line, "pfx duration %ld ms is not a multiple of 4", p->pfx.ms);` | The message names the duration. |
| 1898 | `    if (!plan_long(f[7], 1, MAX_NWIN, &v))` | Field 8, `nwin`: the number of target windows, a whole number from 1 to 4096 (`MAX_NWIN`). |
| 1899 | `        plan_bad(line, "nwin '%s' is not 1 to %d", f[7], MAX_NWIN);` | The message names the bad value. |
| 1900 | `    p->nwin = (int)v;` | Stores the number of target windows. |
| 1901 | `    if (!plan_long(f[8], 1, MAX_MS, &p->win_ms))` | Field 9, `win_ms`: the duration of one target window, a whole number from 1 to 3600000 ms (`MAX_MS`). |
| 1902 | `        plan_bad(line, "win_ms '%s' is not 1 to %ld", f[8], MAX_MS);` | The message names the bad value. |
| 1903 | `    p->count = !strcmp(f[9], "closed") ? CS_CLOSED : !strcmp(f[9], "open") ? CS_OPEN : !strcmp(f[9], "read") ? CS_READ : -1;` | Field 10, `count`: the counter state. The words `closed`, `open` and `read` give the codes of line 1171. Any other word gives -1. |
| 1904 | `    if (p->count < 0)` | Tests whether the word was none of the three. |
| 1905 | `        plan_bad(line, "count '%s' is not closed, open or read", f[9]);` | The message names the bad word. |
| 1906 | `    if (strcmp(f[10], "0") && strcmp(f[10], "1"))` | Field 11, `bins`: tests whether the text is neither `0` nor `1`. |
| 1907 | `        plan_bad(line, "bins '%s' is not 0 or 1", f[10]);` | The message names the bad text. |
| 1908 | `    p->bins = f[10][0] == '1';` | `bins` becomes 1 for the text `1` and 0 for the text `0`. |
| 1909 | `    plan.n++;` | Counts the trial. |
| 1910 | `    /* The record storage is bounded here, before the process pins or` | Comment: the size of the record storage is limited here. The sentence goes on in line 1911. |
| 1911 | `     * allocates. */` | Comment: this happens before the process pins a thread or allocates the records. |
| 1912 | `    recsz.windows += (size_t)trial_windows(p);` | Adds the windows of this trial to the number of window records (`trial_windows`, line 1489). |
| 1913 | `    recsz.bins += (size_t)p->nwin * (size_t)window_bins(p);` | Adds the bins of this trial: `nwin` times `window_bins(p)` (line 1496). |
| 1914 | `    if (p->count == CS_READ)` | Tests whether the trial has the counter state `read`. |
| 1915 | `        recsz.counts += (size_t)p->nwin + 1;` | Adds the `nwin + 1` counter readings of this trial. |
| 1916 | `    recsz.trace = plan.trace ? TRACE_CAP : 0;` | With `--trace` the storage holds `TRACE_CAP` (1048576) trace events. Without `--trace` it holds none. |
| 1917 | `    recsz.bytes = (size_t)plan.n * sizeof(struct trec) + recsz.windows * sizeof(struct win) +` | `recsz.bytes`: the size of the record block for all trials up to this line: the trial records plus the window records. The sum goes on in line 1918. |
| 1918 | `                  recsz.counts * sizeof(struct counts) + recsz.bins * sizeof(struct bin) + recsz.trace * sizeof(struct tev);` | Continues the sum of line 1917: plus the counter readings, the bins and the trace events. |
| 1919 | `    if (recsz.bytes > MAX_REC_BYTES)` | Tests whether the size is above 256 MiB (`MAX_REC_BYTES`). |
| 1920 | `        plan_bad(line, "the records of the plan up to this line need %zu bytes, the bound is %lu bytes", recsz.bytes,` | Then the plan has a defect. The message gives the size that the records up to this line need, and the upper limit. |
| 1921 | `                 MAX_REC_BYTES);` | Continues the call of line 1920: the upper limit. |
| 1922 | `}` | Ends the function `plan_trial`. |

### Function `read_plan` (trial mode): read and check the whole plan (lines 1924 to 1976)

| Line | Source | Explanation |
|---:|---|---|
| 1924 | `/* Reads and checks the whole plan. Returns only if it can run. */` | Comment: the function reads and checks the whole plan. It returns only when the plan can run. |
| 1925 | `static void read_plan(void)` | Starts the function `read_plan`. It reads the plan file `plan.path` into memory, computes its checksum and checks it line by line. A defect ends the process with exit status 2. |
| 1926 | `{` | Opens the body of `read_plan`. |
| 1927 | `    size_t cap = 1 << 16, len = 0, got;` | `cap`: the size of the text buffer, 65536 bytes at the start. `len`: the number of bytes read so far. `got`: the number of bytes of one read. |
| 1928 | `    FILE *f = fopen(plan.path, "rb");` | Opens the plan file for reading. |
| 1929 | `    char *text = malloc(cap + 1);` | Allocates the text buffer, with room for one more byte at its end. |
| 1930 | `    int line = 0;` | `line`: the number of the plan line that is checked. |
| 1931 | `    if (!f \|\| !text) {` | Tests whether the file could not be opened or the buffer could not be allocated. |
| 1932 | `        fprintf(stderr, "cannot read the plan %s: %s\n", plan.path, strerror(errno));` | Prints `cannot read the plan`, the path and the reason to stderr. |
| 1933 | `        exit(2);` | Ends the process with exit status 2. |
| 1934 | `    }` | Ends the `if` of line 1931. |
| 1935 | `    while ((got = fread(text + len, 1, cap - len, f)) > 0) {` | Loop that reads the file in pieces until no byte is left. |
| 1936 | `        len += got;` | Counts the bytes of the piece. |
| 1937 | `        if (len == cap && !(text = realloc(text, (cap *= 2) + 1))) {` | When the buffer is full, `realloc` doubles its size. The test is true when that fails. |
| 1938 | `            fprintf(stderr, "no memory for the plan\n");` | Prints `no memory for the plan` to stderr. |
| 1939 | `            exit(2);` | Ends the process with exit status 2. |
| 1940 | `        }` | Ends the `if` of line 1937. |
| 1941 | `    }` | Ends the read loop (line 1935). |
| 1942 | `    if (ferror(f)) {` | Tests whether a read failed. |
| 1943 | `        fprintf(stderr, "cannot read the plan %s\n", plan.path);` | Prints `cannot read the plan` and the path to stderr. |
| 1944 | `        exit(2);` | Ends the process with exit status 2. |
| 1945 | `    }` | Ends the `if` of line 1942. |
| 1946 | `    fclose(f);` | Closes the file. |
| 1947 | `    text[len] = '\0';` | Ends the text with a zero byte. |
| 1948 | `    plan.hash = 14695981039346656037ULL; /* FNV-1a, 64 bit, over the bytes of the file */` | `plan.hash`: the start value of the FNV-1a hash, a 64-bit checksum. The comment says that it is computed over the bytes of the file. |
| 1949 | `    for (size_t i = 0; i < len; i++)` | Loop over the bytes of the file. |
| 1950 | `        plan.hash = (plan.hash ^ (uint8_t)text[i]) * 1099511628211ULL;` | One step of the hash per byte: an exclusive or with the byte, then a multiplication by the constant 1099511628211. `trial_worker` prints the result in the M row `plan_fnv1a64` (line 1711). |
| 1951 | `    if (strlen(text) != len)` | Tests whether the text ends before the end of the file. The file then holds a zero byte. |
| 1952 | `        plan_bad(0, "the file holds a zero byte");` | That is a defect of the plan. |
| 1953 | `    for (char *s = text, *next; *s; s = next) {` | Loop over the lines of the text. `s` is the start of a line. `next` is the start of the line after it. |
| 1954 | `        char *nl = strchr(s, '\n');` | `nl`: the line break at the end of the line, or NULL for a last line without one. |
| 1955 | `        next = nl ? nl + 1 : s + strlen(s);` | The next line starts after the line break. Without a line break `next` points to the end of the text, and the loop ends after this line. |
| 1956 | `        if (nl)` | Tests whether the line has a line break. |
| 1957 | `            *nl = '\0';` | Ends the line there: a zero byte replaces the line break. |
| 1958 | `        line++;` | Counts the line. |
| 1959 | `        if (line == 1) {` | Tests for the first line of the plan. |
| 1960 | `            if (strcmp(s, PLAN_LINE1))` | The first line must be the text of `PLAN_LINE1` (line 1162). |
| 1961 | `                plan_bad(1, "the line must be '%s'", PLAN_LINE1);` | If it is not: a defect of the plan. The message gives the text that is needed. |
| 1962 | `        } else if (line == 2) {` | Tests for the second line. |
| 1963 | `            plan_pairs(s);` | `plan_pairs` (line 1836) reads the second line. |
| 1964 | `        } else if (line == 3) {` | Tests for the third line. |
| 1965 | `            if (strcmp(s, PLAN_LINE3))` | The third line must be the text of `PLAN_LINE3` (line 1163): the names of the 11 fields. |
| 1966 | `                plan_bad(3, "the line must be '%s'", PLAN_LINE3);` | If it is not: a defect of the plan. The message gives the text that is needed. |
| 1967 | `        } else {` | The case of every later line. |
| 1968 | `            plan_trial(line, s);` | Every line from the fourth on is one trial. `plan_trial` (line 1866) reads it. |
| 1969 | `        }` | Ends the chain of tests that starts in line 1959. |
| 1970 | `    }` | Ends the loop over the lines (line 1953). |
| 1971 | `    if (line < 3)` | Tests whether the plan has fewer than three lines. |
| 1972 | `        plan_bad(line + 1, "the three header lines are needed");` | That is a defect: the three header lines are needed. |
| 1973 | `    if (plan.n == 0)` | Tests whether the plan has no trial. |
| 1974 | `        plan_bad(line + 1, "no trial");` | That is a defect too. The message is `no trial`. |
| 1975 | `}` | Ends the function `read_plan`. |

### Function `trial_usage` (trial mode): option summary of the trial mode, then exit status 2 (lines 1977 to 1986)

| Line | Source | Explanation |
|---:|---|---|
| 1977 | `static void trial_usage(void)` | Starts the function `trial_usage`. It prints the option summary of the trial mode to stderr and ends the process with exit status 2. |
| 1978 | `{` | Opens the body of `trial_usage`. |
| 1979 | `    fprintf(stderr,` | Starts the `fprintf` call that writes to stderr. Its text stands in lines 1980 to 1983. |
| 1980 | `            "usage: bwx8 --trial --cpus C --bytes B --plan FILE [--ctl-cpu N] [--no-thp] [--trace]\n"` | Text of the message: the usage line with the options `--trial`, `--cpus`, `--bytes`, `--plan`, `--ctl-cpu`, `--no-thp` and `--trace`. The text names the program `bwx8`, the version of the runner that added the trial mode. |
| 1981 | `            "            [--pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"` | Text of the message: the options `--pmu-type` and `--events`, and the two environment variables that can give the counter settings in their place. |
| 1982 | `            "  --cpus: exactly one CPU. --ctl-cpu: CPU of the controlling thread (default 0), another CPU.\n"` | Text of the message: `--cpus` takes exactly one CPU. `--ctl-cpu` is the CPU of the controlling thread (default 0), and it must be another CPU. |
| 1983 | `            "  the counter settings are required if a trial of the plan has count open or read\n");` | Text of the message: the counter settings are required when a trial of the plan has the counter state `open` or `read`. This line ends the call. |
| 1984 | `    exit(2);` | Ends the process with exit status 2. |
| 1985 | `}` | Ends the function `trial_usage`. |

### Function `trial_main` (trial mode): the arguments (lines 1987 to 2018)

| Line | Source | Explanation |
|---:|---|---|
| 1987 | `static int trial_main(int argc, char **argv)` | Starts the function `trial_main`, the entry of the trial mode. `main` calls it only when an argument is the word `--trial` (lines 2069 to 2071). |
| 1988 | `{` | Opens the body of `trial_main`. |
| 1989 | `    struct tw w;` | `w`: the state of the one worker of the trial mode (line 1235). |
| 1990 | `    pthread_t tid;` | `tid`: the handle of the worker thread. |
| 1991 | `    cpu_set_t set;` | `set`: a CPU set, for the check of line 2027. |
| 1992 | `    int bytes_given = 0, counting = 0;` | `bytes_given`: becomes 1 when `--bytes` is given. `counting`: becomes 1 when a trial of the plan wants counters. |
| 1994 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 1995 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 1996 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value needs that. |
| 1997 | `        if (!strcmp(a, "--trial")) {` | The word `--trial` itself needs no action. |
| 1998 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 1999 | `            cfg.use_thp = 0;` | `--no-thp`: the program asks Linux for no 2 MiB pages for the buffer. |
| 2000 | `        } else if (!strcmp(a, "--trace")) {` | Tests for `--trace`. |
| 2001 | `            plan.trace = 1;` | `--trace` enables the event log of the trace. |
| 2002 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 2003 | `            parse_cpus(argv[++i]);` | Reads the CPU list with `parse_cpus` (line 304). The check of line 2019 later demands exactly one CPU. |
| 2004 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 2005 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size, read by `parse_bytes` (line 250). |
| 2006 | `            bytes_given = 1;` | Notes that `--bytes` was given. |
| 2007 | `        } else if (!strcmp(a, "--plan") && more) {` | Tests for `--plan` with a value after it. |
| 2008 | `            plan.path = argv[++i];` | The path of the plan file. |
| 2009 | `        } else if (!strcmp(a, "--ctl-cpu") && more) {` | Tests for `--ctl-cpu` with a value after it. |
| 2010 | `            plan.ctl_cpu = (int)parse_long(argv[++i], "--ctl-cpu", 0, MAX_USE_CPU);` | The CPU of the controlling thread, a whole number from 0 to `MAX_USE_CPU`. |
| 2011 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 2012 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. |
| 2013 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 2014 | `            parse_events(argv[++i]);` | Reads the event list with `parse_events` (line 1118). |
| 2015 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 2016 | `            trial_usage();` | Prints the option summary of the trial mode and ends the process (`trial_usage`, line 1977). Options of the interval mode such as `--threads`, `--seq`, `--stop`, `--start`, `--rounds`, `--min-ms` and `--count` have no branch in this loop. So they end here too. |
| 2017 | `        }` | Ends the chain of tests that starts in line 1997. |
| 2018 | `    }` | Ends the loop over the arguments (line 1994). |

### Function `trial_main` (trial mode): checks, the plan and the start of the worker (lines 2019 to 2058)

| Line | Source | Explanation |
|---:|---|---|
| 2019 | `    if (cfg.ncpus != 1 \|\| !bytes_given \|\| !plan.path \|\| cfg.bytes % 256 != 0) {` | Tests the settings: `--cpus` names exactly one CPU, `--bytes` was given and is a multiple of 256 bytes, and `--plan` was given. |
| 2020 | `        fprintf(stderr, "--trial needs --cpus with exactly one CPU, --bytes (a multiple of 256) and --plan\n");` | If one of them fails: prints the rule to stderr. |
| 2021 | `        trial_usage();` | Then prints the option summary and ends the process with exit status 2 (`trial_usage`). |
| 2022 | `    }` | Ends the `if` of line 2019. |
| 2023 | `    if (plan.ctl_cpu == cfg.cpus[0]) {` | Tests whether the controlling thread and the worker would share one CPU. |
| 2024 | `        fprintf(stderr, "the controlling thread and the worker must not share CPU %d\n", plan.ctl_cpu);` | Prints a message with the CPU number to stderr. |
| 2025 | `        exit(2);` | Ends the process with exit status 2. |
| 2026 | `    }` | Ends the `if` of line 2023. |
| 2027 | `    if (sched_getaffinity(0, sizeof set, &set) != 0 \|\| !CPU_ISSET(cfg.cpus[0], &set) \|\| !CPU_ISSET(plan.ctl_cpu, &set)) {` | Reads the allowed CPU set of the process (`sched_getaffinity`) and tests whether the worker CPU or the CPU of the controlling thread is not in it. A failed call counts as a defect too. |
| 2028 | `        fprintf(stderr, "CPU %d or CPU %d is not in the allowed set of the process\n", cfg.cpus[0], plan.ctl_cpu);` | Prints both CPU numbers to stderr. |
| 2029 | `        exit(2);` | Ends the process with exit status 2. |
| 2030 | `    }` | Ends the `if` of line 2027. |
| 2031 | `    read_plan();` | Reads and checks the whole plan (`read_plan`, line 1925). At this point no thread is pinned and no buffer is mapped. |
| 2032 | `    for (int i = 0; i < plan.n; i++)` | Loop over the trials of the plan. |
| 2033 | `        counting \|= plan.tr[i].count != CS_CLOSED;` | `counting` becomes 1 when a trial has the counter state `open` or `read`. |
| 2034 | `    if (counting && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: a plan with counters, no `--pmu-type`, and the environment variable `BWX_PMU_TYPE` is set. |
| 2035 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 2036 | `    if (counting && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: a plan with counters, no `--events`, and the environment variable `BWX_EVENTS` is set. |
| 2037 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 2038 | `        parse_events(copy);` | Reads the event list from the copy. |
| 2039 | `        free(copy);` | Frees the copy. |
| 2040 | `    }` | Ends the `if` of line 2036. |
| 2041 | `    if (counting && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether a plan with counters still has no PMU type or no event. |
| 2042 | `        fprintf(stderr, "the plan has a trial with count open or read: --pmu-type and --events are needed "` | Prints a message to stderr: the plan has a trial with the counter state `open` or `read`, and `--pmu-type` and `--events` are needed. |
| 2043 | `                        "(or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Continues the text of line 2042: or the two environment variables. |
| 2044 | `        exit(2);` | Ends the process with exit status 2. |
| 2045 | `    }` | Ends the `if` of line 2041. |
| 2047 | `    /* The plan can run. The controlling thread pins itself, starts the` | Comment: the plan can run. The controlling thread pins itself and starts the worker. The sentence goes on in line 2048. |
| 2048 | `     * worker and waits. It never touches the buffer. */` | Comment: then the controlling thread waits. It never touches the buffer. |
| 2049 | `    pin_cpu(plan.ctl_cpu);` | The controlling thread pins itself to the CPU of `--ctl-cpu` (`pin_cpu`, line 331). |
| 2050 | `    memset(&w, 0, sizeof w);` | Sets every field of the worker state to 0. |
| 2051 | `    if (pthread_create(&tid, NULL, trial_worker, &w) != 0) {` | Starts the one worker thread. It runs `trial_worker` (line 1676). |
| 2052 | `        perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 2053 | `        return 2;` | `trial_main` then returns 2, which becomes the exit status of the process (line 2071). |
| 2054 | `    }` | Ends the `if` of line 2051. |
| 2055 | `    pthread_join(tid, NULL);` | Waits for the end of the worker thread (`pthread_join`). |
| 2056 | `    return 0;` | Returns 0, which becomes the exit status of the process (line 2071). |
| 2057 | `}` | Ends the function `trial_main`. |

### The include of the self-test file (lines 2059 to 2060)

| Line | Source | Explanation |
|---:|---|---|
| 2059 | `#include "bwx8_selftest.c"` | Includes the file `bwx8_selftest.c`. It defines the function `selftest`. `main` calls that function only for the option `--selftest` (line 2077). |

### Function `main`: the start of the program (lines 2061 to 2068)

| Line | Source | Explanation |
|---:|---|---|
| 2061 | `int main(int argc, char **argv)` | Starts the function `main`, the entry point of the program. It reads the arguments, starts the workers, sets the common start of each interval and prints all rows. |
| 2062 | `{` | Opens the body of `main`. |
| 2063 | `    int threads_given = 0;` | `threads_given`: becomes 1 when `--threads` is given (line 2090). The check of line 2126 uses it. |
| 2064 | `    char seq_text[1024] = "";` | `seq_text`: will hold a copy of the `--seq` text for the second header line of the output (line 2180). It has room for 1023 characters. |
| 2065 | `    t_base_ns = now_ns();` | Process start time: one reading of the Linux clock `CLOCK_MONOTONIC` through `now_ns` (line 243), in ns. The T rows print the common start, `t0` and `t1` of each thread as seconds after this time (lines 2240 to 2241). |
| 2066 | `    page_bytes = sysconf(_SC_PAGESIZE);` | `page_bytes`: the size of one small memory page in bytes, as Linux reports it (`sysconf`). `alloc_buf` (line 350) uses it when it places a buffer inside its mapping. |
| 2067 | `    cfg.bytes = 1UL << 20;` | `cfg.bytes` gets its default here: 1 MiB (1048576 bytes). The option `--bytes` replaces it (line 2094). |
| 2068 | `    restrict_cpus();` | `restrict_cpus` (line 284) removes every CPU above `MAX_USE_CPU` from the allowed CPU set of the process. `MAX_USE_CPU` is 119 unless the build sets another value (line 55). The build of `bwx8` on CRB set no other value [Ref2]. |

### Function `main`: the choice between the trial mode and the interval mode (lines 2069 to 2072)

| Line | Source | Explanation |
|---:|---|---|
| 2069 | `    for (int i = 1; i < argc; i++)` | Mode choice. The loop compares every argument with the word `--trial`. |
| 2070 | `        if (!strcmp(argv[i], "--trial"))` | Tests whether one argument is the word `--trial`. |
| 2071 | `            return trial_main(argc, argv);` | When an argument is `--trial`, `main` returns the result of `trial_main` (line 1987), and no line below runs. This is the only call of `trial_main` in the file. |

### Function `main`: reading the arguments (lines 2073 to 2125)

| Line | Source | Explanation |
|---:|---|---|
| 2073 | `    for (int i = 1; i < argc; i++) {` | Loop over the arguments, from left to right. |
| 2074 | `        const char *a = argv[i];` | `a`: the argument that is read now. |
| 2075 | `        int more = i + 1 < argc;` | `more`: 1 when one more argument follows. An option with a value is accepted only when `more` is 1, and `argv[++i]` then takes the value. |
| 2076 | `        if (!strcmp(a, "--selftest")) {` | Tests for `--selftest`. |
| 2077 | `            return selftest();` | `--selftest` runs the self-test (the function `selftest` of the included self-test file) and ends the program with its result. |
| 2078 | `        } else if (!strcmp(a, "--list")) {` | Tests for `--list`. |
| 2079 | `            for (int k = 0; k < K_COUNT; k++)` | Loop over the kernel table. |
| 2080 | `                printf("%s\n", kernels[k].name);` | `--list` prints the name of every kernel of the table, one per line. |
| 2081 | `            return 0;` | Then the program ends with exit status 0. |
| 2082 | `        } else if (!strcmp(a, "--no-thp")) {` | Tests for `--no-thp`. |
| 2083 | `            cfg.use_thp = 0;` | `--no-thp` sets `cfg.use_thp` to 0. Then `alloc_buf` asks Linux for no 2 MiB pages. |
| 2084 | `        } else if (!strcmp(a, "--two-buffers")) {` | Tests for `--two-buffers`. |
| 2085 | `            cfg.two_buffers = 1;` | `--two-buffers` sets `cfg.two_buffers` to 1. Then every thread gets a second buffer `b`, also without a copy kernel (line 994). |
| 2086 | `        } else if (!strcmp(a, "--count")) {` | Tests for `--count`. |
| 2087 | `            cfg.count = 1;` | `--count` sets `cfg.count` to 1. Then each worker opens its counter group and reads it before and after every timed interval. `main` prints the C rows from these readings. |
| 2088 | `        } else if (!strcmp(a, "--threads") && more) {` | Tests for `--threads` with a value after it. |
| 2089 | `            cfg.threads = (int)parse_long(argv[++i], "--threads", 1, 4096);` | The number of worker threads. `parse_long` (line 269) accepts a whole number from 1 to 4096. |
| 2090 | `            threads_given = 1;` | Notes that `--threads` was given. |
| 2091 | `        } else if (!strcmp(a, "--cpus") && more) {` | Tests for `--cpus` with a value after it. |
| 2092 | `            parse_cpus(argv[++i]);` | `parse_cpus` (line 304) appends the CPUs of each range of the list to `cfg.cpus`, in the order of the text. `cfg.ncpus` counts them. |
| 2093 | `        } else if (!strcmp(a, "--bytes") && more) {` | Tests for `--bytes` with a value after it. |
| 2094 | `            cfg.bytes = parse_bytes(argv[++i]);` | The buffer size of each thread, read by `parse_bytes` (line 250). That function reads the letter `M` as 2 to the power 20. |
| 2095 | `        } else if (!strcmp(a, "--min-ms") && more) {` | Tests for `--min-ms` with a value after it. |
| 2096 | `            char *end;` | `end`: will point to the first character that `strtod` did not read. |
| 2097 | `            double ms = strtod(argv[++i], &end);` | `strtod` reads the value as a decimal number of milliseconds. A fraction is allowed. |
| 2098 | `            if (end == argv[i] \|\| *end != '\0' \|\| !(ms > 0) \|\| ms > 3.6e6) {` | Tests for a bad value: no number, other text after the number, a value that is not above 0, or a value above 3.6e6 ms (1 hour). |
| 2099 | `                fprintf(stderr, "bad --min-ms: '%s' (a number of milliseconds above 0 is needed)\n", argv[i]);` | Prints a message with the bad value to stderr. |
| 2100 | `                exit(2);` | Ends the program with exit status 2. |
| 2101 | `            }` | Ends the `if` of line 2098. |
| 2102 | `            cfg.min_s = ms / 1000.0;` | `cfg.min_s`: the value in seconds. With `--stop common` it is the time from the common start to the deadline (line 2218). With `--stop pass` it is the least duration of an interval (line 1062). |
| 2103 | `        } else if (!strcmp(a, "--rounds") && more) {` | Tests for `--rounds` with a value after it. |
| 2104 | `            cfg.rounds = (int)parse_long(argv[++i], "--rounds", 1, 1000000);` | The number of rounds, a whole number from 1 to 1000000. The program runs the `--seq` list that many times. |
| 2105 | `        } else if (!strcmp(a, "--seq") && more) {` | Tests for `--seq` with a value after it. |
| 2106 | `            snprintf(seq_text, sizeof seq_text, "%s", argv[++i]);` | Copies the text of the list to `seq_text`, for the second header line (line 2180). The copy is made first: `parse_seq` changes the argument text. |
| 2107 | `            parse_seq(argv[i]);` | `parse_seq` (line 1097) cuts the argument text itself at each comma. It looks up each name in the kernel table and appends its index to `cfg.seq`. An unknown name ends the program. `cfg.nseq` counts the entries. An entry without an `@SIZE` part keeps the size 0 until line 2147. |
| 2108 | `        } else if (!strcmp(a, "--stop") && more) {` | Tests for `--stop` with a value after it. |
| 2109 | `            const char *s = argv[++i];` | `s`: the value. |
| 2110 | `            if (strcmp(s, "pass") && strcmp(s, "common"))` | Tests whether the value is neither `pass` nor `common`. |
| 2111 | `                usage();` | Any other value prints the option summary and ends the program (`usage`, line 1084). |
| 2112 | `            cfg.stop_common = !strcmp(s, "common");` | `cfg.stop_common` becomes 1 for `common` and 0 for `pass`. With 1 all threads get one common start time and one common deadline for each interval (lines 2215 to 2220). |
| 2113 | `        } else if (!strcmp(a, "--start") && more) {` | Tests for `--start` with a value after it. |
| 2114 | `            const char *s = argv[++i];` | `s`: the value. |
| 2115 | `            if (strcmp(s, "common") && strcmp(s, "offset"))` | Tests whether the value is neither `common` nor `offset`. |
| 2116 | `                usage();` | Any other value prints the option summary and ends the program (`usage`). |
| 2117 | `            cfg.start_offset = !strcmp(s, "offset");` | `cfg.start_offset` becomes 1 for `offset` and 0 for `common`. With 0 every worker starts its timed work at byte 0 of its own buffer (line 1009). |
| 2118 | `        } else if (!strcmp(a, "--pmu-type") && more) {` | Tests for `--pmu-type` with a value after it. |
| 2119 | `            cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);` | The PMU type, a whole number from 0 to 2147483647. It goes into the field `type` of the structure `perf_event_attr` (line 936). |
| 2120 | `        } else if (!strcmp(a, "--events") && more) {` | Tests for `--events` with a value after it. |
| 2121 | `            parse_events(argv[++i]);` | `parse_events` (line 1118) stores the names in `cfg.ev_name` and the codes in `cfg.ev_code`. `cfg.nev` becomes the number of events. `main` does not interpret the codes. Each worker passes them to Linux in `open_counters` (line 929). |
| 2122 | `        } else {` | The case of every other argument, and of an option whose value is missing. |
| 2123 | `            usage();` | `usage` (line 1084) prints the option summary to stderr and ends the process with exit status 2. |
| 2124 | `        }` | Ends the chain of tests that starts in line 2076. |
| 2125 | `    }` | Ends the loop over the arguments (line 2073). |

### Function `main`: checks of the settings (lines 2126 to 2158)

| Line | Source | Explanation |
|---:|---|---|
| 2126 | `    if (threads_given && cfg.ncpus == 0) {` | Check: `--threads` is accepted only together with `--cpus`. The test is true when `--threads` was given and the CPU list is empty. |
| 2127 | `        fprintf(stderr, "--threads requires --cpus\n");` | Prints `--threads requires --cpus` to stderr. |
| 2128 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 2129 | `    }` | Ends the `if` of line 2126. |
| 2130 | `    if (cfg.threads < 1 \|\| cfg.rounds < 1 \|\| cfg.nseq < 1 \|\| cfg.bytes == 0 \|\| cfg.bytes % 256 != 0)` | Checks of the values: the thread count, the round count and the number of `--seq` entries are at least 1, and `--bytes` is above 0 and a multiple of 256 bytes. |
| 2131 | `        usage();` | A failed check prints the option summary and ends the program with exit status 2 (`usage`). |
| 2132 | `    /* run_bwx.sh passes the counter settings in the environment */` | Comment: the script `run_bwx.sh`, the run script of the first runner, passes the counter settings in the environment. |
| 2133 | `    if (cfg.count && cfg.pmu_type < 0 && getenv("BWX_PMU_TYPE"))` | Fallback for the PMU type: with `--count`, without `--pmu-type`, and when the environment variable `BWX_PMU_TYPE` is set. |
| 2134 | `        cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);` | Then the PMU type comes from that variable. |
| 2135 | `    if (cfg.count && cfg.nev == 0 && getenv("BWX_EVENTS")) {` | Fallback for the events: with `--count`, without `--events`, and when the environment variable `BWX_EVENTS` is set. |
| 2136 | `        char *copy = strdup(getenv("BWX_EVENTS"));` | `copy`: a copy of the text of the variable. `parse_events` cuts its text into pieces, so it gets a copy. |
| 2137 | `        parse_events(copy);` | Reads the event list from the copy. |
| 2138 | `        free(copy);` | Frees the copy. |
| 2139 | `    }` | Ends the `if` of line 2135. |
| 2140 | `    if (cfg.count && (cfg.pmu_type < 0 \|\| cfg.nev == 0)) {` | Tests whether `--count` is given and the PMU type or the events are still missing. |
| 2141 | `        fprintf(stderr, "--count requires --pmu-type and --events (or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");` | Prints a message to stderr: `--count` requires `--pmu-type` and `--events`, or the two environment variables. |
| 2142 | `        usage();` | Prints the option summary and ends the program with exit status 2 (`usage`). |
| 2143 | `    }` | Ends the `if` of line 2140. |
| 2144 | `    for (int s = 0; s < cfg.nseq; s++) {` | Loop over the `--seq` entries. |
| 2145 | `        struct entry *e = &cfg.seq[s];` | `e`: one entry. |
| 2146 | `        if (e->bytes == 0)` | Tests whether the entry has no size of its own (no `@SIZE` part). |
| 2147 | `            e->bytes = cfg.bytes;` | Such an entry gets the size of `--bytes`. |
| 2148 | `        if (e->bytes > cfg.bytes \|\| e->bytes % 256 != 0 \|\|` | Size check of an entry. The size must be at most `--bytes` and a multiple of 256 bytes. The check goes on in line 2149. |
| 2149 | `            (cfg.stop_common && e->bytes > CHUNK_BYTES && e->bytes % CHUNK_BYTES != 0)) {` | With `--stop common` a size above 2 MiB (`CHUNK_BYTES`) must also be a multiple of 2 MiB. With this stop rule the worker calls the kernel on chunks of 2 MiB (line 1040). A size of 256 MiB passes: 268435456 bytes is 128 times 2 MiB. |
| 2150 | `            fprintf(stderr, "bad size of --seq entry %d (%s): %lu\n", s, kernels[e->k].name, (unsigned long)e->bytes);` | A bad size prints a message to stderr: the number of the entry, the kernel name and the size. |
| 2151 | `            usage();` | Then the option summary is printed, and the program ends with exit status 2 (`usage`). |
| 2152 | `        }` | Ends the `if` of line 2148. |
| 2153 | `        if (kernels[e->k].type == T_COPY)` | Tests whether the kernel of the entry is a copy kernel (type `T_COPY`). |
| 2154 | `            cfg.two_buffers = 1;` | A copy kernel in the list sets `cfg.two_buffers` to 1. Then each thread gets a second buffer `b` (line 994). |
| 2155 | `    }` | Ends the loop over the entries (line 2144). |
| 2156 | `    if (cfg.ncpus && cfg.threads > cfg.ncpus)` | Tests whether a CPU list was given and has fewer CPUs than the process has threads. |
| 2157 | `        fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);` | This only gives a warning on stderr, with both numbers. The CPU list is then used again from its start (line 2168). |

### Function `main`: thread records, barrier and start of the workers (lines 2159 to 2174)

| Line | Source | Explanation |
|---:|---|---|
| 2159 | `    struct thread *th = calloc((size_t)cfg.threads, sizeof *th);` | `th`: one record per thread, filled with zeros by `calloc`. |
| 2160 | `    uint64_t **bufs = calloc((size_t)cfg.threads * 2, sizeof *bufs);` | `bufs`: two buffer addresses per thread, for buffer `a` and buffer `b`, filled with zeros. |
| 2161 | `    struct page *pg = calloc((size_t)cfg.threads * 2, sizeof *pg);` | `pg`: one page-state record per entry of `bufs`. |
| 2162 | `    if (!th \|\| !bufs \|\| !pg \|\| pthread_barrier_init(&bar, NULL, (unsigned)cfg.threads + 1) != 0) {` | Tests the three allocations and creates the barrier `bar` for the thread count plus 1: the workers and the main thread. |
| 2163 | `        perror("setup");` | On a failure: `perror` prints the word `setup` and the reason. |
| 2164 | `        return 2;` | On a failure: the program ends with exit status 2. |
| 2165 | `    }` | Ends the `if` of line 2162. |
| 2166 | `    for (int i = 0; i < cfg.threads; i++) {` | Loop that starts the workers. |
| 2167 | `        th[i].idx = i;` | Thread `i` gets the index `i`. |
| 2168 | `        th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;` | Thread placement. Thread `i` gets the CPU `cfg.cpus[i % cfg.ncpus]`: entry `i` of the CPU list. The list is used again from its start when there are more threads than entries. Without a CPU list the value is -1, and the thread is not pinned (line 988). |
| 2169 | `        if (pthread_create(&th[i].tid, NULL, worker, &th[i]) != 0) {` | Creates the thread. It runs `worker` (line 979): it pins itself, opens its counters, maps its buffer and writes it. `main` does not wait for that here. It goes on with the header lines. The function `main` does not pin the main thread. So the main thread may run on any CPU of the allowed CPU set of the process. |
| 2170 | `            perror("pthread_create");` | If the thread cannot be created: `perror` prints the word `pthread_create` and the reason. |
| 2171 | `            return 2;` | The program then ends with exit status 2. |
| 2172 | `        }` | Ends the `if` of line 2169. |
| 2173 | `    }` | Ends the loop of line 2166. |

### Function `main`: the header lines of the csv file (lines 2175 to 2195)

| Line | Source | Explanation |
|---:|---|---|
| 2175 | `    printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "` | Starts the `printf` call of the first header line. The line starts with `# bandwidth:`. It gives the meaning of GB (1e9 bytes) and the formula of the rate of the I rows: `aggregate_GBps` is the sum of the bytes of all threads divided by the longest elapsed time of one thread. |
| 2176 | `           "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",` | Continues the text of the first header line: a copy kernel counts the bytes read plus the bytes written. Then come four settings: the thread count, the bytes per thread, `min_ms` and `thp`. |
| 2177 | `           cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");` | The four values. `min_ms` is `cfg.min_s` times 1000, printed without decimals. `thp` is `madvise` when the program asks for 2 MiB pages, and `nohugepage` with `--no-thp`. It only says what the program asked for. The P rows show what the buffers got. |
| 2178 | `    printf("# bwx: seq=%s rounds=%d stop=%s start=%s two_buffers=%d count=%d kernels=%s; "` | Starts the `printf` call of the second header line. The line starts with `# bwx:`. It holds the `--seq` text, the rounds, the stop rule, the start rule, `two_buffers`, `count` and the build kind (`kernels=`). |
| 2179 | `           "round and pos count from 0; times are seconds since process start\n",` | Continues the text of the second header line: round and position count from 0, and the times are seconds after the process start. |
| 2180 | `           seq_text, cfg.rounds, cfg.stop_common ? "common" : "pass", cfg.start_offset ? "offset" : "common",` | The values: the `--seq` text, the number of rounds, `common` or `pass` for the stop rule, and `offset` or `common` for the start rule. |
| 2181 | `           cfg.two_buffers, cfg.count, STANDIN ? "STAND-IN (not AArch64: rates mean nothing)" : "aarch64");` | The values of `two_buffers`, `count` and the build kind. `STANDIN` is 0 in the AArch64 build (line 408), and the build kind is then `aarch64`. A build with stand-in kernels prints a text that starts with `STAND-IN` and says that the rates mean nothing. |
| 2182 | `    printf("# I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps\n"` | Starts the `printf` call of the third, fourth and fifth header line. This line holds the column names of the I rows (line 2234). |
| 2183 | `           "# T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags\n"` | The fourth header line: the column names of the T rows (line 2238). |
| 2184 | `           "# P,round,pos,tid,buffer,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n");` | The fifth header line: the column names of the P rows. `print_p` (line 917) prints these rows. |
| 2185 | `    if (cfg.count) {` | Tests whether counting is on (`--count`). Only then the header has a sixth line. |
| 2186 | `        printf("# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns");` | Starts the sixth header line: the first nine column names of the C rows, up to `cputime_ns`. |
| 2187 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 2188 | `            printf(",%s", cfg.ev_name[e]);` | Appends the event names in the order of `--events`, one column per event. |
| 2189 | `        printf("; pmu_type=%ld codes=", cfg.pmu_type);` | Appends the PMU type (`pmu_type=`) and the word `codes=`. |
| 2190 | `        for (int e = 0; e < cfg.nev; e++)` | Loop over the events. |
| 2191 | `            printf("%s0x%llx", e ? "," : "", (unsigned long long)cfg.ev_code[e]);` | Appends the event codes in hexadecimal, with commas between them. |
| 2192 | `        printf("\n");` | Ends the header line with a line break. |
| 2193 | `    }` | Ends the `if` of line 2185. |
| 2194 | `    fflush(stdout);` | `fflush` writes the header lines to the standard output now. |

### Function `main`: the loop over rounds and positions, and the common start (lines 2196 to 2222)

| Line | Source | Explanation |
|---:|---|---|
| 2196 | `    for (int round = 0; round < cfg.rounds; round++) {` | Loop over the rounds, as in `worker` (line 1003). |
| 2197 | `        for (int pos = -1; pos < cfg.nseq; pos++) {` | Loop over the positions. `pos` starts at -1, not at 0. Position -1 is one extra pass of the loop before the first interval. Each position from 0 up is one timed interval. `main` and the workers go through the same rounds and positions. At each barrier call below a thread waits until all workers and `main` have arrived. |
| 2198 | `            if (pos < 0 && (round > 0 \|\| cfg.threads == 1))` | Tests whether the pass with position -1 must be skipped: in every round after round 0, and in a process with one thread. |
| 2199 | `                continue;` | Skips that pass. So in a process with more than one thread it runs once, before the first interval. |
| 2200 | `            if (pos < 0) {` | The case of position -1. |
| 2201 | `                /* the workers have allocated and first touched their buffers */` | Comment: at this point the workers have allocated their buffers and have written them for the first time. |
| 2202 | `                pthread_barrier_wait(&bar);` | `main` calls the barrier. The call returns when all workers have mapped and written their buffers and wait in line 999. |
| 2203 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 2204 | `                    bufs[2 * i] = th[i].a;` | Copies the address of buffer `a` of thread `i` into entry `2 * i` of `bufs`. |
| 2205 | `                    bufs[2 * i + 1] = th[i].b;` | Copies the address of buffer `b` of thread `i` into entry `2 * i + 1`. The entry stays NULL when the thread has no second buffer. |
| 2206 | `                }` | Ends the loop of line 2203. This pass of the position loop goes on with the page-state block in line 2262. That block prints the page state before the first interval. |
| 2207 | `            } else {` | The case of a position from 0 up: one interval. |
| 2208 | `                const struct entry *e = &cfg.seq[pos];` | `e`: the `--seq` entry of this position. |
| 2209 | `                const char *name = kernels[e->k].name;` | `name`: the name of its kernel. |
| 2210 | `                double per_pass = (double)e->bytes * (kernels[e->k].type == T_COPY ? 2 : 1);` | `per_pass`: the byte count of one pass over the range of the entry: its size, or twice its size for a copy kernel. The column `passes` of the T rows uses it (line 2241). |
| 2211 | `                uint64_t total = 0;` | `total`: the sum of the byte counts of all threads. It starts at 0. |
| 2212 | `                int64_t max_el = 0;` | `max_el`: the longest elapsed time of one thread, in ns. It starts at 0. |
| 2214 | `                pthread_barrier_wait(&bar); /* release the workers */` | First barrier call of the interval. It returns when all workers have finished the warm-up pass of this kernel and wait in line 1022. The barrier then lets all of these threads continue. With `--stop common` the workers do not start the kernel yet: each worker waits in an empty loop until `gen` changes (line 1024). The comment says: release the workers. |
| 2215 | `                if (cfg.stop_common) {` | Tests for `--stop common`. Only then `main` sets a common start (lines 2216 to 2219). With `--stop pass` each worker starts its timed interval directly after the barrier. |
| 2216 | `                    int64_t sched = now_ns() + LEAD_NS;` | Common start, set by the main thread. `main` reads the clock once and adds `LEAD_NS` (2 ms, line 48). The result `sched` is the common start time of all threads. `main` is not pinned. |
| 2217 | `                    atomic_store(&t_sched_ns, sched);` | Stores `sched` in the shared variable `t_sched_ns`. The lead of 2 ms is the time that `main` has for lines 2217 to 2219 and that the workers have to see the new `gen`. A worker that sees it only after `sched` has passed starts after the common start time. When its `t0` is then more than 100 us after `sched`, the late flag shows it (line 1072). |
| 2218 | `                    atomic_store(&deadline_ns, sched + (int64_t)(cfg.min_s * 1e9));` | Stores the deadline in the shared variable `deadline_ns`: `sched` plus `cfg.min_s`. |
| 2219 | `                    atomic_fetch_add(&gen, 1);` | Only after both stores `main` adds 1 to `gen`. So a worker that sees the new `gen` reads the new start time and the new deadline. Each worker then reads the clock in a loop until `sched`, and then reads its own start time `t0` (lines 1028 to 1035). After this line `main` passes nothing more to the workers. Each worker stops by itself, at its first clock read at or after the deadline (lines 1047 to 1048). |
| 2220 | `                }` | Ends the `if` of line 2215. |
| 2221 | `                pthread_barrier_wait(&bar); /* all workers finished this interval */` | Second barrier call of the interval. `main` blocks here until all workers have stored their results and wait in line 1074. So between the change of `gen` and the end of the timed interval this call is the only code that `main` runs. It prints nothing in that time. The comment says: all workers finished this interval. |

### Function `main`: the I row, the T rows and the C rows (lines 2223 to 2261)

| Line | Source | Explanation |
|---:|---|---|
| 2223 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the results of the threads. In a process with more than one thread every worker waits at the barrier of line 1078 from here to line 2271. So no kernel runs while `main` prints the I, T and C rows. |
| 2224 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i` for this interval (line 1073). |
| 2225 | `                    total += r->bytes;` | `total` becomes the sum of the byte counts of all threads. |
| 2226 | `                    if (r->t_end - r->t_start > max_el)` | Tests whether the elapsed time of this thread, `t_end - t_start` in ns, is the longest so far. `t_start` is the `t0` of the worker, and `t_end` is its last `t1` (lines 1069 to 1070). |
| 2227 | `                        max_el = r->t_end - r->t_start;` | Keeps the longest elapsed time in `max_el`. |
| 2228 | `                }` | Ends the loop of line 2223. |
| 2229 | `                if (cfg.threads == 1) { /* read by the worker before the interval */` | The branch of a process with one thread. There the worker has read the page state itself before the interval (lines 1017 to 1021), and `main` prints it here. The comment says: read by the worker before the interval. |
| 2230 | `                    print_p(round, pos, 0, 'a', &th[0].res.pg[0], th[0].res.vm);` | Prints the P row of buffer `a` (`print_p`, line 917). |
| 2231 | `                    if (th[0].b)` | Tests whether the thread has a second buffer. |
| 2232 | `                        print_p(round, pos, 0, 'b', &th[0].res.pg[1], th[0].res.vm);` | Prints the P row of buffer `b`. It holds the same four counter values as the row of buffer `a`. |
| 2233 | `                }` | Ends the `if` of line 2229. |
| 2234 | `                printf("I,%d,%d,%s,%lu,%d,%lu,%.6f,%.2f\n", round, pos, name, (unsigned long)e->bytes, cfg.threads,` | I row, one per interval, with 9 fields: the letter `I`, round, position, kernel name, `bytes_per_thread`, thread count, `total_bytes`, `max_elapsed_s` and `aggregate_GBps`. `bytes_per_thread` is the size of the `--seq` entry. It is a setting, not a measured value. |
| 2235 | `                       (unsigned long)total, (double)max_el * 1e-9, (double)total / (double)max_el);` | Continues the call of line 2234. `total_bytes` is `total`. `max_elapsed_s` is `max_el` in seconds, with 6 decimals. `aggregate_GBps` is `total` in bytes divided by `max_el` in ns, with 2 decimals. One byte per ns is 1 GB/s with GB = 1e9 bytes. So this rate is the bytes of all threads divided by the longest elapsed time of one thread. |
| 2236 | `                for (int i = 0; i < cfg.threads; i++) {` | Loop over the threads. |
| 2237 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 2238 | `                    printf("T,%d,%d,%s,%d,%d,%lu,%.6f,%.6f,%.6f,%.6f,%.3f,%s\n", round, pos, name, i, th[i].cpu,` | T row, one per thread and interval, with 13 fields. Fields 1 to 6: the letter `T`, round, position, kernel name, thread index (`tid`) and the CPU of the thread. A thread without a CPU list shows -1. |
| 2239 | `                           (unsigned long)r->bytes, (double)(r->t_end - r->t_start) * 1e-9,` | Continues the call of line 2238. Field 7, `bytes`: the byte count of the worker (line 1043, line 1059). Field 8, `elapsed_s`: `t_end - t_start` in seconds, with 6 decimals. The rate of a thread is field 7 divided by field 8, in bytes per second. The program does not print it. |
| 2240 | `                           (double)(r->t_sched - t_base_ns) * 1e-9, (double)(r->t_start - t_base_ns) * 1e-9,` | Continues the call of line 2238. Fields 9 and 10, `t_sched_s` and `t_start_s`: the common start time and `t0`, in seconds after the process start `t_base_ns`, with 6 decimals. With `--stop pass` field 9 equals field 10 (line 1071). |
| 2241 | `                           (double)(r->t_end - t_base_ns) * 1e-9, (double)r->bytes / per_pass, r->late ? "late" : "-");` | Continues the call of line 2238. Field 11, `t_end_s`: the last `t1`, in seconds after the process start. Field 12, `passes`: `bytes / per_pass`, the number of passes over the range of the entry, with 3 decimals. Field 13, `flags`: `late` when `t0` came more than 100 us after the common start (line 1072), and `-` if not. |
| 2242 | `                }` | Ends the loop of line 2236. |
| 2243 | `                for (int i = 0; cfg.count && i < cfg.threads; i++) {` | Loop over the threads. It runs only with `--count`. It prints the C rows: one per thread and interval. |
| 2244 | `                    struct result *r = &th[i].res;` | `r`: the result of thread `i`. |
| 2245 | `                    printf("C,%d,%d,%s,%d,%d", round, pos, name, i, th[i].cpu);` | Starts a C row. Fields 1 to 6: the letter `C`, round, position, kernel name, thread index and CPU. |
| 2246 | `                    if (th[i].group_fd < 0)` | Tests whether the thread has no open counter group. |
| 2247 | `                        printf(",NA,NA");` | Fields 7 and 8 are then `NA`. |
| 2248 | `                    else` | The case of a thread with an open group. |
| 2249 | `                        printf(",%llu,%llu", (unsigned long long)(r->c1.enabled - r->c0.enabled),` | Fields 7 and 8, `enabled_ns` and `running_ns`: the enabled time and the running time of the counter group at the second reading minus the same values at the first reading. This line holds the enabled time. |
| 2250 | `                               (unsigned long long)(r->c1.running - r->c0.running));` | Continues the call of line 2249: the running time. |
| 2251 | `                    printf(",%llu", (unsigned long long)(r->c1.cpu_ns - r->c0.cpu_ns));` | Field 9, `cputime_ns`: the thread CPU time at the second reading minus the value at the first reading. The worker takes the first reading (`c0`) directly before `t0` and the second reading (`c1`) directly after its last `t1` (lines 1031 to 1034, lines 1064 to 1067). |
| 2252 | `                    for (int ev = 0; ev < cfg.nev; ev++) {` | Loop over the events, in the order of `--events`. |
| 2253 | `                        int at = th[i].ev_pos[ev];` | `at`: the place of the event in a group reading. It is -1 when the event did not open (line 947). |
| 2254 | `                        if (at < 0)` | Tests whether the event did not open. |
| 2255 | `                            printf(",NA");` | Its field is then `NA`. |
| 2256 | `                        else` | The case of an event that opened. |
| 2257 | `                            printf(",%llu", (unsigned long long)(r->c1.val[at] - r->c0.val[at]));` | One field per event: the count at the second reading minus the count at the first reading. |
| 2258 | `                    }` | Ends the loop over the events (line 2252). |
| 2259 | `                    printf("\n");` | Ends the row with a line break. |
| 2260 | `                }` | Ends the loop of line 2243. |
| 2261 | `            }` | Ends the `else` of line 2207. |

### Function `main`: the page state, the P rows and the end (lines 2262 to 2283)

| Line | Source | Explanation |
|---:|---|---|
| 2262 | `            if (cfg.threads > 1) {` | Page-state block. It runs only in a process with more than one thread: once at position -1 and once after every interval. At this time every worker waits at a barrier: in line 1000 after position -1, in line 1078 after an interval. So no kernel runs while `main` reads the page state. |
| 2263 | `                /* Page state of all buffers, read between two intervals. It is` | Comment: the page state of all buffers is read between two intervals. The sentence goes on in line 2264. |
| 2264 | `                 * the state after interval pos (pos -1: before the first). The` | Comment: it is the state after interval `pos`. For `pos` -1 it is the state before the first interval. The sentence about the workers starts here. |
| 2265 | `                 * workers wait on the barrier below until it is read. */` | Comment: the workers wait at the barrier below (line 2271) until the state is read. |
| 2266 | `                long long vm[4];` | `vm`: will hold the four counters of `/proc/vmstat`. |
| 2267 | `                int64_t r0 = now_ns();` | `r0`: the clock value before the reading (`now_ns`, line 243). |
| 2268 | `                read_smaps(pg, bufs, 2 * cfg.threads);` | `read_smaps` (line 862) looks up each entry of `bufs` in `/proc/self/smaps` and skips the NULL entries. It stores the size of each buffer and its part on 2 MiB pages in `pg`. |
| 2269 | `                read_vmstat(vm);` | `read_vmstat` (line 892) reads the four counters of `/proc/vmstat`, once for the whole block. |
| 2270 | `                double ms = (double)(now_ns() - r0) * 1e-6;` | `ms`: the duration of both readings in ms: the clock value now minus `r0`. |
| 2271 | `                pthread_barrier_wait(&bar); /* the reading is done: the workers go on */` | Barrier call that lets the workers continue. Each worker then starts the warm-up pass of the next interval, while `main` prints the P rows below. After the last interval the workers end at this point. The comment says: the reading is done, and the workers go on. |
| 2272 | `                for (int i = 0; i < 2 * cfg.threads; i++)` | Loop over the entries of `bufs`. Entry `i` belongs to thread `i / 2`. An even `i` is buffer `a`, and an odd `i` is buffer `b`. |
| 2273 | `                    if (bufs[i])` | Skips an entry without a buffer. |
| 2274 | `                        print_p(round, pos, i / 2, i % 2 ? 'b' : 'a', &pg[i], vm);` | P row, one per existing buffer, printed by `print_p` (line 917). The fields: the letter `P`, round, position, thread index, buffer letter, size of the buffer in kB, part on 2 MiB pages in kB, then the four counters of `/proc/vmstat`. The position is that of the interval before the reading, or -1 for the reading before the first interval. All rows of one block carry the same four counter values: they count for the whole system and were read once (line 2269). |
| 2275 | `                printf("# page_read,%d,%d,%.3f ms\n", round, pos, ms);` | Prints the line `# page_read` with the round, the position and `ms`, the duration of the page-state reading of this block, with 3 decimals and the unit `ms`. |
| 2276 | `            }` | Ends the `if` of line 2262. |
| 2277 | `            fflush(stdout);` | `fflush` writes all rows that are still in the output buffer to the standard output. Then the loops go on with the next position. A new timed interval cannot start before `main` has passed line 2214 again, and with `--stop common` also line 2219. So `main` writes no output during a timed interval. |
| 2278 | `        }` | Ends the loop over the positions (line 2197). Between two intervals lie the output of the rows, the page-state reading, the barrier calls, the warm-up pass of the next kernel and, with `--stop common`, the 2 ms lead. No code of the interval mode calls a sleep function. |
| 2279 | `    }` | Ends the loop over the rounds (line 2196). |
| 2280 | `    for (int i = 0; i < cfg.threads; i++)` | Loop over the threads, after the last interval. |
| 2281 | `        pthread_join(th[i].tid, NULL);` | Waits for the end of worker thread `i` (`pthread_join`). |
| 2282 | `    return 0;` | Returns 0: the process ends with exit status 0. |
| 2283 | `}` | Ends the function `main`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/listing.txt`: objdump text of the 21 kernel functions of the `bwx8` binary that was built on CRB on 2026-11-15. Source of the start addresses, the loop starts and the instruction counts. Each function stands under a heading such as `=== bwx8 read ===`. The file `offsets.tsv` of the same folder lists the start address and the loop start of each kernel. A script compared this listing with the listing of `bwx10` on 2026-11-25: apart from absolute addresses, the 21 kernels have the same instruction text in both.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/build.txt`: build record of CRB. The row `## cc=` names the compiler, gcc 14.2.0. The row `## CFLAGS=` gives the flags. They hold no `-D` option, and the build command of `build8.sh` adds none. The row `## timed_sequence branch targets:` holds `(indirect)=4 __stack_chk_fail=1 clock_gettime=2 tcount=2`. The block `## sha256:` gives the sha256 of `bwx8.c` at the build. It is the sha256 of the source file of this page. The block also gives the sha256 of the binary `bwx8`. Its first 8 digits are `f84be912`.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/probe.txt`: objdump text of the kernels of `bw_new` (sections `=== bw_new ... ===`) and of `bw_old` (sections `=== bw_old ... ===`). Compared with the listing of [Ref1] by a script on 2026-11-25, with absolute code addresses and data addresses left out. `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite` and `k_asmcopy` of `bw_new` have the instruction text of the functions with the same names in `bwx8`. `k_read`, `k_write` and `k_copy` of `bw_old` have the instruction text of `k_oldread`, `k_oldwrite` and `k_oldcopy` of `bwx8`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: sections B.4 to B.8, the specification of the first runner `bwx` that the comments cite: the two stop methods (B.4), the start offsets (B.5), the page state (B.6), the loop addresses (B.7) and the counters (B.8). B.7 names the loop offset as a factor of step B3. B.8 says that counter code without user-mode counting fails without root on CRB, and that a counter is opened with `pid = 0` and `cpu = -1`.
- [Ref5] `/usr/include/linux/perf_event.h`: the comment above `enum perf_event_read_format` (header of the machine on which this page was written). With `PERF_FORMAT_GROUP` the data of one `read` are `nr`, `time_enabled`, `time_running` and then one value per counter.
- [Ref6] external source: Linux kernel documentation on docs.kernel.org, read on 2026-11-25. Page https://docs.kernel.org/admin-guide/mm/transhuge.html: `thp_fault_alloc` "is incremented every time a huge page is successfully allocated and charged to handle a page fault". `thp_fault_fallback` "is incremented if a page fault fails to allocate or charge a huge page and instead falls back to using small pages". `thp_collapse_alloc` "is incremented by khugepaged when it has found a range of pages to collapse into one huge page and has successfully allocated a new huge page to store the data". Page https://docs.kernel.org/mm/page_migration.html: page migration moves the physical location of pages, and for the counter of successful migrations "Each count means that a page was migrated".
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design of the investigation into the small gain of the new read kernel at 8 MiB. Its section "Runner design" describes the trial mode: one pinned worker, the trial with prefix, predecessor and target windows, and the required records.
- [Ref8] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb-results.md`: the result handoff of that investigation. Its table "What ran" names `bwx8` as the binary of round 1 and of round 2, with the first 8 digits of its sha256, `f84be912`. The build record gives a sha256 with these first digits for the binary `bwx8` [Ref2]. The table also names `bwx8` for step `YL` of round 3.
- [Ref9] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: the sections "Plan file", "bwx8 command line" and "Output rows of trial mode". They give the format of the plan file, the options of the trial mode, the order of the work of the worker and the fields of each row kind. The section says that a process with an X row still ends with status 0 unless the plan cannot run.
