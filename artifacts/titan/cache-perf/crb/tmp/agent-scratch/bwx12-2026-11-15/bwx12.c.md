# `bwx12.c` explained

- Source file: `bwx12.c` in this folder (C source, 3126 lines, 119709 bytes).
- sha256 of the source when this page was built: `e3d4442b83d0aabdb8bf68ec62dfeb43d489df1d7c36de82e64e5482a1089127`.
- Role in the whole-chip test: Source of bwx12, the benchmark program that parts L, C and control I run.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

In the whole-chip test bwx12 starts 120 threads, one pinned to each of the CPUs 0 to 119, and every thread reads its own 256 MiB buffer for 6 s with each read kernel of the `--seq` list. The program prints the bytes and the times of every thread and interval as csv rows, and the analysis computes the rates from these rows.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means such a loop, or a write loop or copy loop of the same program. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bandwidth.orig.c**: the benchmark source until 2026-11-13 (the old source). The binary bw_old was built from it [Ref12]. The comment of lines 453 to 460 names it as the origin of the kernels `oldread`, `oldwrite` and `oldcopy`.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **bwx8, bwx10**: two more older versions of the runner, between bwx and bwx11. The comment at the top of the file (lines 1 to 105) says what each version added. Comment lines such as `/* bwx12+ */` and `/* bwx12- */` enclose the text that one version added.
- **Round 3, round 4, round 5 (in source comments)**: the work steps of 2026-11-15 that produced the versions bwx10, bwx11 and bwx12 (lines 62, 36 and 3 of the file). They are not rounds of `--rounds`.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Spec file**: a text file with one line of the form `tag|arguments`. The files of the test are like.spec (part L and control I), cfwd.spec and crev.spec (part C) [Ref4].
- **rx.sh**: the shell script that starts bwx12 in the test. For each line of a spec file it runs `taskset -c 0-119 bwx12 <arguments>` and writes the standard output to the file `<tag>.csv` [Ref3]. `taskset -c 0-119` is the Linux command that limits a process to the CPUs 0 to 119.
- **csv file**: a text file whose rows hold fields separated by commas. Here: the output file of one bwx12 process.
- **Header lines**: the first 6 lines of a csv file of the test. Each starts with `#`. They hold the settings and the column names of the I, T, P and C rows.
- **stderr, exit status**: stderr is the standard error output of a process. The script rx.sh appends the stderr of bwx12 to the file stderr.txt of the result folder [Ref3]. The exit status is the number that a process returns when it ends. bwx12 ends with status 0 after a complete run and with status 2 after an error that it found itself. rx.sh writes the status to the file launches.txt [Ref3].
- **Allowed CPU set**: the set of CPUs on which Linux may run a thread. `taskset -c 0-119` limits it to the CPUs 0 to 119 for the whole process.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Rate, total**: part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **GB, MiB, kB**: GB = 1e9 bytes (used for rates). MiB = 2^20 bytes. In a size argument the letter M means MiB, so `--bytes 256M` is 268435456 bytes. kB in the P rows is the unit of the Linux file smaps. It is 1024 bytes: a buffer of 268435456 bytes is reported as 262144 kB [Ref5].
- **2 MiB pages**: transparent huge pages. The "P" rows of bwx12 report how many kB of each buffer lie on them.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Build record**: the file build.txt that the build script wrote on CRB. It holds the compiler, the flags, the start addresses modulo 64 of some functions and the sha256 values [Ref2].
- **Listing, objdump**: objdump is the GNU tool that prints the machine code of a binary as assembler text. The listing is the file listing.txt of the CRB build. It holds the objdump text of every kernel function of the bwx12 binary [Ref1].
- **Interval mode, trial mode**: the two modes of the program. The interval mode (option `--seq`) runs the number of threads that `--threads` gives. It times one interval per round and kernel of the sequence. The trial mode (option `--trial`) runs one worker thread through the trials of a plan file. The whole-chip test uses the interval mode only.
- **Kernel table, `kernels[]`**: the array at lines 1454 to 1484. Each entry holds the name of a kernel (the word used in `--seq`), its type (T_READ, T_WRITE, T_COPY or T_OLDREAD) and a pointer to its function `k_<name>`. It has 55 entries.
- **`cfg`**: the global structure (lines 264 to 282) that holds the settings from the arguments: thread count, CPU list, buffer size, kernel sequence, rounds, stop rule, counter settings.
- **Worker, main thread**: a worker is one benchmark thread (function `worker`). The test has 120 workers. The main thread runs `main`: it starts the workers, sets the start time of each interval and prints all rows.
- **Pinning**: binding a thread to one CPU with the Linux call `sched_setaffinity`, so that Linux does not move it to another CPU.
- **First touch**: the first write to the pages of a new mapping. Linux gives a page its physical memory at that moment. Here each pinned worker writes its whole buffer once with `k_write` before any read.
- **Barrier**: a POSIX thread barrier (`pthread_barrier_wait`). A thread that calls it blocks until 121 threads have called it (120 workers plus the main thread). Then all of them continue. So no thread goes on to the next step of the run before all the other threads have reached the same point.
- **Warm-up pass**: one pass of the kernel of the coming interval over the whole buffer, before the common start of that interval. It is not timed. Between this pass and the timed interval lie a barrier wait, the 2 ms lead and the first counter reading.
- **Chunk**: a 2 MiB piece of the buffer (CHUNK_BYTES). With `--stop common` the worker calls the kernel on one chunk and then reads the clock. A 256 MiB buffer has 128 chunks.
- **Common start, lead**: the start time `t_sched_ns` of an interval. The main thread sets it to the clock value plus 2 ms (LEAD_NS, the lead). Every worker waits for this time in a loop that only reads the clock.
- **Deadline**: the common start time plus the `--min-ms` value (6 s in the test), variable `deadline_ns`. A worker stops at its first clock read at or after the deadline.
- **`gen`**: an atomic counter of intervals. The main thread adds 1 after it has stored the start time and the deadline of the next interval. A worker waits until `gen` equals its own interval count plus 1.
- **Spin-wait**: a loop that only tests a condition again and again. The thread stays on its CPU and does not sleep.
- **us**: microsecond. 1 us = 1000 ns. 1000 us = 1 ms.
- **Late flag**: the word `late` in the last column of a T row. It marks a thread whose start clock read was more than 100 us (0.1 ms, the constant LATE_NS) after the common start time. Otherwise the column holds `-`.
- **`sink`**: a volatile variable on the stack of each worker. `call` stores there the sum that an old read kernel returns. So the compiler cannot remove the adds of the old read kernel.
- **CLOCK_MONOTONIC**: the Linux clock that the function `now_ns` reads for every time stamp, in ns. The start and the end of a timed interval are two readings of this clock.
- **Thread CPU time**: the CPU time that one thread has used, read from the Linux clock CLOCK_THREAD_CPUTIME_ID by the function `cpu_ns`. The C rows print its change over an interval as `cputime_ns`.
- **smaps, page state**: `/proc/self/smaps` is a Linux file that lists every memory mapping of the process. Its lines `Size` and `AnonHugePages` give the size of a mapping and the part of it on 2 MiB pages, in kB. The page state of a buffer is this pair of values.
- **vmstat counters**: four counters of the Linux file `/proc/vmstat`: `thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc` and `pgmigrate_success`. They count for the whole system, not for one buffer. The Linux documentation gives their meanings [Ref13]. `thp_fault_alloc` counts the 2 MiB pages that Linux gave at a page fault. `thp_fault_fallback` counts the page faults at which Linux could not give a 2 MiB page and used small pages instead. `thp_collapse_alloc` counts the 2 MiB pages that Linux made later from a range of small pages. `pgmigrate_success` counts the pages that Linux moved to another place in physical memory.
- **`madvise`, MADV_HUGEPAGE**: `madvise` is the Linux call that gives advice about a memory range. With MADV_HUGEPAGE it asks Linux to use 2 MiB pages for the range.
- **`mmap`, `mprotect`, private anonymous mapping**: `mmap` is the Linux call that maps new memory into the process. A private anonymous mapping is memory of this process only, with no file behind it. `mprotect` changes the access rights of a memory range. `alloc_buf` uses it to forbid every access to the unused parts before and after the buffer.
- **PMU, PMU type, event code**: PMU: performance monitoring unit, the hardware event counters of a CPU core. The value of `--pmu-type` (11 in the test) goes into the field `type` of the structure `perf_event_attr`. An event code goes into the field `config`. The two fields tell Linux which event to count.
- **File descriptor**: the number that Linux returns when a program opens a file or a counter. Later calls such as `read` use it for the open object.
- **`perf_event_open`, counter group, group leader**: `perf_event_open` is the Linux system call that opens one counter and returns a file descriptor. The first counter that a thread opens here is the group leader. Counters that are opened with the same leader form a group. One `read` of the leader returns the number of counters, the enabled time, the running time and one value per counter [Ref8].
- **Enabled time, running time**: two times of a counter group, in ns: how long the counters were enabled, and how long they really counted. A running time below the enabled time means that the counters did not count all the time.
- **User mode**: the state in which a CPU runs the code of the program itself, not Linux kernel code. The counters of the test count in user mode only.
- **Hypervisor**: the software that runs virtual machines. The field `exclude_hv` keeps its code out of the counts.
- **cbusy0, cbusy1, cbusy2, cbusy3, cbusy_mt, bus_access**: the six event names of the argument lines, with the codes 0x198, 0x199, 0x19a, 0x19b, 0x19c and 0x19. The interval mode uses a name in two places: as a column title in the header line of the C rows, and in the error message of a counter that does not open. It passes the code to Linux and does not interpret it.
- **AArch64, NEON**: AArch64 is the 64-bit Arm instruction set. The CRB binary is an AArch64 build. NEON is the vector part of it: 32 registers of 16 bytes, written v0 to v31, or q0 to q31 when an instruction uses all 16 bytes, or d0 to d31 for the low 8 bytes.
- **ldp q, ldr q, nop, vector add**: `ldp q0, q1, [x0]` loads 32 bytes from memory into two vector registers. `ldr q0, [x0]` loads 16 bytes into one. `nop` does nothing. `add v24.2d, v24.2d, v6.2d` adds two vectors that each hold two 64-bit numbers.
- **`stp`, `movi`, `addp`, `fmov`, `ret`**: more AArch64 instructions of the listing. `stp q0, q1, [x0]` stores two 16-byte vector registers (32 bytes) to memory. `stp d8, d9, [sp, #-64]!` stores the low 8 bytes of two vector registers on the stack. The kernels use this form for the save of d8 to d15 (see the entry "Save of d8 to d15"). `movi v16.4s, #0` sets the four 32-bit parts of v16 to 0. `addp d31, v31.2d` adds the two 64-bit halves of one vector register. `fmov x0, d31` copies the low 8 bytes of a vector register to the general register x0. `ret` returns to the caller.
- **`cmp`, `b.lo`, `b.cc`, `b.hi`**: `cmp` compares two registers and sets the condition flags. `b.lo` branches when the first value is lower, as unsigned numbers. `b.cc` is a second name of the same instruction: the source writes `b.lo`, and objdump prints `b.cc`. `b.hi` branches when the first value is higher, as unsigned numbers.
- **x0, x1**: 64-bit general registers of AArch64. When a kernel function starts, x0 holds its first argument (the start address `a`) and x1 holds its second argument (the word count `n`).
- **Loop pass**: one run of the loop body of a kernel. One loop pass covers 256 B of the buffer in the kernels `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl`, and 128 B in `oldread` [Ref1]. It is not a pass over the whole buffer.
- **Read address, end address (of a kernel)**: the read address is the pointer `p` of a kernel loop: the address of the block that the loop pass loads. The end address is the first address after the range of the call. In the listings of `k_read`, `k_asmread`, `k_read_nop96`, `k_read_nop256` and `k_read_1pl`, x0 holds the read address. One `add` instruction before the loop puts the end address into x1 [Ref1]. `k_oldread` has no end address. It counts its loop passes in x1 and compares the count with the number of passes in x2 [Ref1].
- **64 B line**: a block of 64 bytes of memory. The source comments count memory in such lines. They mean cache lines: a CPU cache holds memory in blocks of this size. A record of CRB gives a cache line size of 64 bytes for each of the four caches of CPU 0 [Ref14].
- **`.rept N`, `.endr`**: two directives of the GNU assembler. The assembler writes the lines between them N times. `.rept 96`, `nop`, `.endr` gives 96 `nop` instructions. `.rept 0` writes nothing.
- **Clobber list**: the last list of a gcc `__asm__` statement. It names the registers and the other state that the assembler text changes. gcc keeps no value there across the statement.
- **Stack check, guard value**: instructions that gcc added to `k_oldread`. At the start of the function they copy a value (the guard value) to the stack. Before the return they compare the copy with the value. When the two differ, the function calls `__stack_chk_fail`. These instructions run once per call, outside the loop [Ref1].
- **Prefetch, `prfm pldl1keep`**: an instruction that asks the CPU to bring a 64 B line into the first-level data cache before a load needs it. It loads no data into a register. Only the read_pf kernels use it (lines 966 to 969).
- **read_pf kernels**: the kernels `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048`: the asmread loop plus four prefetch instructions per loop pass. The whole-chip test does not run them.
- **NEON intrinsic, `vld1q_u64`**: an intrinsic is a C function of the header arm_neon.h that maps to one vector instruction. `vld1q_u64(p)` loads 16 bytes (two 64-bit numbers) from the address `p`.
- **Save of d8 to d15**: the Arm calling rules (AAPCS64) say that a function must keep the registers d8 to d15 for its caller. A kernel that uses v8 to v15 stores d8 to d15 on the stack once at its start and loads them back once at its end. This is outside its loop.
- **PLACE, pad, loop offset**: `PLACE(name)` is a macro that stands before each kernel. It adds unused bytes (the pad) so that the kernel starts at a chosen address modulo 64. The aim is a fixed loop offset: the address of the first instruction of the loop modulo 64.
- **LOOP, HEAD, PAD (`LOOP_<name>`, `HEAD_<name>`, `PAD_<name>`, `PADOF`)**: the values of the loop placement (comment of lines 142 to 160). `LOOP_<name>` is the planned loop offset of a kernel. `HEAD_<name>` is the number of bytes of code between the start of the function and the start of its loop. `PAD_<name>` is the number of zero bytes that `PLACE` adds after a 64 B boundary, directly before the function. For a kernel with a planned loop offset the macro `PADOF(loop, head)` computes the pad: (LOOP - HEAD) modulo 64. The other kernels have a fixed pad.
- **Stand-in**: a plain C loop that replaces a NEON kernel or an assembler kernel when the file is compiled for a machine that is not AArch64 (the `#else` branches). The CRB binary holds no stand-in.
- **A/A copy**: the same kernel source under a second name, for example `oldread2` and `asmread2`. The whole-chip test does not run them.
- **Handoff B.4 to B.8, step B2, B3, B5**: comments cite sections of the file `crb/new-test-kernel/handoff.md`, the specification of the first runner bwx.c: B.4 the two stop methods, B.5 start offsets, B.6 page state, B.7 loop addresses, B.8 counters. B2, B3 and B5 are steps of that earlier investigation (section B.9) [Ref10].
- **Plan file, trial, window (trial mode)**: the plan file lists the trials of one process. A trial is a list of windows. A window runs one kernel on one range of the buffer for a fixed time. The whole-chip test does not use them.
- **Bin, trace, evict step (trial mode)**: a bin is a part of a target window with a requested length of 10 ms. Its record holds the clock time of its end and the bytes since the start of the window. The trace (`--trace`) is a log of events with clock times. The evict step (`--evict-mb`) writes other memory before the first trial so that the buffer leaves the caches. The whole-chip test does not use them.
- **Phase, target window (trial mode)**: a trial has up to four phases, in this order: previous activity (`prev`, 1 window), prefix (4 windows), predecessor (`pred`, 1 window) and target (`nwin` windows). The plan may leave out each of the first three. A target window is a window of the last phase. Bins and counter readings exist only for target windows. The whole-chip test does not use them.
- **Timed sequence (trial mode)**: the run of all windows of one trial, done by the function `timed_sequence` (line 1995) or, with the option `--hot-copy`, by `timed_sequence_hot` (line 2056). The clock reads that time the windows are inside these functions. The whole-chip test does not use it.
- **Counter state (trial mode)**: the field `count` of a plan line: `closed` (the counter group is closed for the trial), `open` (the group is open and is not read during the trial) or `read` (the group is read at the boundaries of the target windows). The E row prints `fail` in its place when an event did not open.
- **Record, record block (trial mode)**: the record of a trial (`struct trec`, line 1867) holds its results. The record block is one memory block that `alloc_records` allocates for all trials: the trial records, the window records, the counter readings, the bins and, with `--trace`, the event log.
- **Controlling thread (trial mode)**: the main thread of a process in the trial mode: the thread that runs `trial_main`. It pins itself to the CPU of `--ctl-cpu`, starts the one worker of the trial mode and waits for its end. The whole-chip test does not use it.
- **S, W, B, E, X, TR, M, K rows (trial mode)**: row kinds that only the trial mode prints: S (the plan line of a trial), W (one window), B (one bin), E (the summary of a trial), X (a problem), TR (one trace event), M (one setting or one fact of the process), K (the address of one kernel). The trial mode also prints P and C rows, with other columns than the P and C rows of the interval mode. The csv files of the whole-chip test hold no S, W, B, E, X, TR, M or K row [Ref5].
- **FNV-1a hash (trial mode)**: a 64-bit checksum that `read_plan` computes over the bytes of the plan file. The whole-chip test does not use it.
- **Context switch, voluntary and involuntary**: a context switch is the moment at which Linux stops running a thread on its CPU. Voluntary (`ru_nvcsw` of the Linux call `getrusage`): the thread stopped because it asked to wait for something. Involuntary (`ru_nivcsw`): Linux took the CPU away from the thread. Only the trial mode reads these counts.
- **Minor page fault**: a page fault that Linux serves without disk access (`ru_minflt` of `getrusage`). The first touch of a page is one. Only the trial mode reads this count.
- **Self-test**: the option `--selftest` runs the function `selftest` of the included file bwx12_selftest.c (line 2900). The build script runs it once after the build. The whole-chip test does not run it.

</details>

## Main flow

1. Start. The script rx.sh starts the program as `taskset -c 0-119 bwx12` plus the argument line of a spec file [Ref3] [Ref4]. `main` reads the clock once for the process start time `t_base_ns`. The T rows print the times `t_sched_s`, `t_start_s` and `t_end_s` as seconds since this reading (lines 2904-2910).
2. `restrict_cpus` removes every CPU above 119 from the allowed CPU set of the process. Here `taskset` has already limited the set to the CPUs 0 to 119, so the call changes nothing (line 2911).
3. Mode choice. `main` compares every argument with the word `--trial`. Only when one is equal it calls `trial_main`. Line 2914 is the only call of `trial_main` in the file. The argument lines of like.spec, cfwd.spec and crev.spec do not hold `--trial` [Ref4]. So the test never enters the trial mode. It runs the interval mode, which is the rest of `main` (lines 2912-2914).
4. Argument parsing. One loop over the arguments fills the settings structure `cfg`. Result for like.spec: 120 threads, the CPU list 0, 1, ... 119, 268435456 bytes (256 MiB) per thread, common stop, `--start common` (every thread starts at byte 0 of its own buffer), 6 s per interval, 2 rounds, 5 kernels in `cfg.seq`, counting on, PMU type 11, 6 events. cfwd.spec and crev.spec differ only in `--seq`: 3 kernels (lines 2916-2968).
5. Checks of the settings. Each `--seq` entry without `@SIZE` gets the size of `--bytes`. With `--count` the PMU type and the events must be known. No kernel of the test is a copy kernel, so `cfg.two_buffers` stays 0 and each thread has one buffer (buffer `a`) (lines 2969-3000).
6. Threads. `main` creates a barrier for 121 threads (120 workers plus the main thread). It starts 120 threads that run `worker`. Thread i gets the CPU `cfg.cpus[i]`, which is CPU i (lines 3002-3016).
7. CPU pinning. Each worker binds itself to its CPU with `pin_cpu`. Every later step of the worker runs on that CPU (lines 1641-1642).
8. Counters, open. With `--count` each worker calls `open_counters` (line 1644). It opens one counter per event with the system call `perf_event_open`: field `type` = 11, field `config` = the event code, user mode only, for the calling thread on any CPU. The first counter that opens is the leader of the group. The counters count from this moment on (lines 1582-1607).
9. Buffer allocation. Each worker maps its own buffer with `alloc_buf`: 256 MiB, start at a 2 MiB boundary, with a request for 2 MiB pages. Then it writes every 8-byte word once with `k_write`. This is the first touch, done by the pinned thread (lines 1645-1646).
10. Header. `main` prints the header lines of the csv file. They start with `#`. They hold the settings and the column names of the I, T, P and C rows (lines 3018-3037).
11. First barrier wait (worker lines 1651 to 1654). When all 120 buffers exist, `main` copies the buffer addresses. Then it runs the page-state block of lines 3105 to 3119 with position -1: 120 P rows and one `# page_read` line for the state before the first interval (lines 3041-3049).
12. Loops. The worker runs two nested loops. `--rounds 2` runs the `--seq` list 2 times (round 0 and round 1). Each kernel of the list is one position. One pair of round and position is one interval: 10 intervals for like.spec, 6 for cfwd.spec and crev.spec. `main` runs the same two loops (lines 3039 to 3040). At each barrier call the workers and `main` wait for each other. So all of them work on the same interval at the same time (lines 1656-1658).
13. Warm-up. The worker calls the kernel of the position once on the whole buffer. This pass is not timed (line 1669).
14. Common start, main thread. When all workers have finished the warm-up, `main` reads the clock. It sets the start time `t_sched_ns` to this value plus 2 ms. It sets `deadline_ns` to the start time plus 6 s. Then it adds 1 to `gen`. It blocks at the barrier of line 3064 until all workers have finished the interval (lines 3057-3064).
15. Common start, worker. Each worker waits in a spin-wait loop until it sees the new value of `gen`. It copies the start time and the deadline. Then it reads the clock in a second spin-wait loop until the start time (lines 1675-1683).
16. Start of the timed interval. With `--count` the worker first reads its counter group (`read_group`) and its thread CPU time (`cpu_ns`). Then it reads the clock: `t0` (line 1688). The timed interval starts here (lines 1684-1689).
17. Timed loop with `--stop common`. The worker calls the kernel on one 2 MiB chunk of its buffer, adds 2097152 bytes to its byte count, and reads the clock: `t1` (line 1700). It repeats this with the next chunk while `t1` is below the deadline. After the last chunk of the buffer it continues with the first chunk. So the common deadline stops the interval, and each thread stops at the end of the chunk that it is in (lines 1690-1701).
18. End of the interval, worker. The worker reads its thread CPU time and its counter group again. It stores the byte count, `t0`, the last `t1`, the common start time and the late flag in `t->res`. Then it waits at the barrier (lines 1717-1727).
19. I row. `main` adds the bytes of all threads and finds the longest elapsed time `t1 - t0` of one thread. It prints one I row (lines 3077 to 3078). The last column is the total bytes divided by that longest time in ns. This is GB/s with GB = 1e9 bytes (lines 3066-3078).
20. T rows. `main` prints one T row per thread: round, position, kernel, thread number, CPU, bytes, elapsed seconds, the common start time, `t0` and `t1` in seconds since the process start, the number of buffer passes, and the late flag. The script stat_bwx.py computes the rate of an interval from these rows: the sum over the threads of bytes divided by elapsed seconds [Ref6] (lines 3079-3085).
21. C rows. With `--count`, `main` prints one C row per thread. It holds the change between the two counter readings of the interval: enabled time, running time, thread CPU time and one value per event (lines 3086-3103).
22. P rows and `# page_read` line. The workers wait at the barrier (worker line 1731). `main` reads the page state of all buffers with `read_smaps` and `read_vmstat` and measures the time of this reading. It releases the workers at line 3114. Then it prints one P row per buffer through `print_p` (lines 3115 to 3117) and the line `# page_read,round,pos,time in ms` (line 3118). The released workers start the warm-up of the next interval (lines 3105-3120).
23. End. After the last interval `main` waits for the 120 threads and returns 0 (lines 3123-3125).

## Behavior a reader must know

- The test runs the interval mode only. `main` calls `trial_main` only when an argument is the word `--trial` (lines 2912 to 2914), and no argument line of the test holds it [Ref4]. The file launches.txt of each result folder records the argument line that ran. It equals the line of the spec file [Ref5]. The trial-mode code (lines 1795 to 2886) and the self-test file do not run in the test.
- The source in this folder is the source of the binary that ran. Its sha256 is the value that the build record of CRB gives for bwx12.c, and the file env.txt of each of the 9 result folders names the sha256 of the binary of that build [Ref2] [Ref5]. The script rx.sh computes the sha256 of the binary file before it starts the program. It stops when the result differs from the value that it writes to env.txt [Ref3]. The file bwx12_selftest.c, which line 2900 includes, also has the sha256 that the build record gives for it [Ref2].
- The CRB binary is the AArch64 build: each `#if defined(__aarch64__)` took its first branch. Line 2 of every csv file of the test says `kernels=aarch64` [Ref5]. So the stand-in kernels of lines 851 to 897, 1005 to 1022 and 1406 to 1438 are not in the binary.
- Kernels of the test in the AArch64 build. `oldread` is the function `k_oldread`: macro DEF_OLDREAD (lines 461 to 473), used at line 474. `read` is `k_read` (lines 501 to 528). `asmread` is `k_asmread`: macro DEF_ASMREAD (lines 616 to 641), used at line 642. `read_nop96` is `k_read_nop96`: the same macro, used at line 1063. `read_nop256` is `k_read_nop256`: the same macro, used at line 1199. `read_1pl` is `k_read_1pl` (lines 988 to 1004). The other 49 kernels of the table are not in any `--seq` list of the test [Ref4]. One of them, `k_write`, runs for the first touch only.
- Machine code of the six kernels, one loop pass [Ref1]. `k_oldread`: 128 B, 4 `ldp q` loads, 8 vector adds (each loaded register is added to one of 8 sum registers), 16 instructions. `k_read`: 256 B, 8 `ldp q` loads, no use of the loaded values, 11 instructions. `k_asmread`: the same 8 loads, 11 instructions. `k_read_nop96` and `k_read_nop256`: the asmread loop plus 96 or 256 `nop`, 107 or 267 instructions. `k_read_1pl`: the read address moves on by 256 B, with 4 `ldr q` loads of 16 B each (64 B loaded), 7 instructions.
- Machine code that gcc produced from the C text of the two C kernels [Ref1]. `k_oldread`: the C text has 16 sums of 8 bytes and 16 adds per 128 B. gcc put the 16 sums into 8 vector registers, two sums per register. So the loop has 4 `ldp q` loads and 8 vector adds per 128 B. `k_read`: nothing computes with the 16 loaded values. An empty `__asm__` statement (lines 522 to 525) names them as inputs in vector registers, so gcc must keep the loads. gcc joined the 16 loads of 16 B into 8 `ldp q` loads. The other four kernels of the test are assembler text. gcc adds only the instructions before and after their loop.
- Cross-check with bw_old and bw_new, the binaries of part A. With absolute addresses left out, three functions of bwx12 have the same instruction text as a function of these binaries [Ref1] [Ref7]. `k_read` of bwx12 equals `k_read` of bw_new. `k_oldread` of bwx12 equals `k_read` of bw_old. `k_asmread` of bwx12 equals `k_asmread` of bw_new.
- What is timed: only lines 1688 to 1700 of `worker`. The interval starts at the clock read `t0` (line 1688) and ends at the last clock read `t1` (line 1700). Between them lie the kernel calls through `call`, the byte count and one clock read per 2 MiB chunk. Not timed: allocation, first touch, warm-up, barrier waits, spin-waits, counter readings, page-state readings and all output.
- Stop rule (`--stop common`): all threads get the same deadline, 6 s after the common start time. A thread stops at its first clock read at or after the deadline. So it finishes the 2 MiB chunk that it is in. The bytes and the time of this last chunk are counted. In the test the last `t1` of a thread was 0 us to 463 us after the deadline [Ref5].
- Bytes counted: 2097152 bytes for each finished chunk call, for every read kernel. The count is the size of the buffer range that the call covered. It is not the number of bytes that the kernel loaded. `read_1pl` loads only 16 B of each 64 B line, but its chunk also counts as 2097152 bytes.
- Rate. The I row divides the bytes of all threads by the longest elapsed time of one thread. The script stat_bwx.py computes its total from the T rows: the sum over the threads of bytes / elapsed seconds. It shows the I row value next to it as `I_agg` [Ref6]. In each of the 74 intervals of the test the two values differ by less than 0.004 % [Ref5]. The script facts_data.py computes the totals of the facts sheet (the file FACTS.md in the folder of the analysis scripts) with the same sum over the T rows [Ref11]. The unit is GB/s with GB = 1e9 bytes.
- Kernel calls. With `--stop common` the kernel function is entered once per 2 MiB chunk: 128 calls per pass over a 256 MiB buffer. The kernels `asmread`, `read_nop96` and `read_nop256` save and restore d8 to d15 once per call, outside the loop. `k_oldread` sets its 8 sum registers to 0 at the start of each call and adds them into one value at the end of each call [Ref1]. One clock read follows each call.
- Thread placement: thread i is pinned to CPU i (0 to 119). So threads 0 to 63 run on mesh 0 and threads 64 to 119 on mesh 1. In every T row of the test the thread number equals the CPU number [Ref5]. The main thread is not pinned in the interval mode. It may run on any CPU of 0 to 119. During a timed interval it blocks at the barrier of line 3064.
- Buffers: one private anonymous mapping per thread. `alloc_buf` maps 260 MiB (256 MiB plus 4 MiB). The buffer is a 256 MiB part of this mapping that starts at a 2 MiB boundary. The unused parts before and after it get no access rights. `alloc_buf` asks for 2 MiB pages for the buffer. The pinned thread writes the buffer once before any read. After that every 8-byte word of a buffer holds the same value `v`, and the read kernels never change it. `v` is a number that the worker computes at line 1637 from the process number (`getpid`) and its thread number. In the test every P row reports 262144 kB of 262144 kB on 2 MiB pages [Ref5].
- Order inside a process: the kernels run in the order of `--seq`, and round 1 follows round 0 directly. There is no sleep between two intervals. Between the end of one interval and the start of the next, these steps run in this order. `main` prints the I, T and C rows. `main` reads the page state (the `# page_read` line gives the duration of this reading). Each worker runs the warm-up pass of the next kernel, and `main` prints the P rows at the same time. The barrier holds each thread until all 121 threads have called it (worker line 1675, `main` line 3057). Then comes the 2 ms lead to the common start. In the test the time from the last `t1` of one interval to the first `t0` of the next was 0.064 s to 0.140 s (65 gaps in 9 processes) [Ref5].
- The warm-up pass uses the kernel of the coming interval. So the kernel of the interval before never runs directly before a timed interval. One full pass of the kernel of the coming interval over the same buffer lies between them. After this pass come the wait at the barrier and the 2 ms lead.
- Counters: each thread opens its group once, after pinning and before it maps its buffer. The counters count user mode only. They are never reset and never stopped. A C row holds the change between a reading directly before `t0` and a reading directly after the last `t1`. An event that does not open in a thread is printed as `NA` in the C rows of that thread. Only thread 0 writes a message to stderr for such an event. A failed group read ends the process with status 2. In the test no csv field is `NA` and every stderr.txt is empty [Ref5]. In every C row of the test the enabled time equals the running time [Ref5].
- Late flag: a T row ends with `late` when the `t0` of the thread is more than 100 us (0.1 ms) after the common start time. The row is still printed. In the 9 csv files of the test no T row has this flag [Ref5]. The largest distance between `t0` and the common start time in the test was 34 us [Ref5].
- What ends the process with status 2: a bad argument, a failed `mmap`, a failed `sched_getaffinity` or `sched_setaffinity` (the Linux calls that read and set the allowed CPU set), an allowed CPU set that holds no CPU from 0 to 119, a failed read of the counter group, a failed setup in `main` (the memory for the thread records, the barrier, or the start of a thread). A failed `mprotect` or `madvise` in `alloc_buf` only writes a message to stderr, and the run continues. A buffer that does not lie on 2 MiB pages does not stop the run: the P rows only report it. Every stderr.txt of the test is empty, and every launches.txt reports the exit status 0 [Ref5]. The program does not look at the marker file. The script rx.sh does that [Ref3].
- Branches that do not run in the test: the one-thread branches of `worker` (lines 1670 to 1674) and of `main` (lines 3072 to 3076), where the worker itself reads the page state. The second buffer `b` (lines 1647 to 1650). The start offset of `--start offset` (line 1662 gives 0 here). The loop of `--stop pass` (lines 1702 to 1716). The fallback to the environment variables BWX_PMU_TYPE and BWX_EVENTS (lines 2976 to 2982): every argument line of the test gives `--pmu-type` and `--events`.
- Build: gcc 14.2.0 with the flags `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4` and no `-D` option (the gcc option that sets a macro from the command line) [Ref2]. So `MAX_USE_CPU` (the highest CPU that the process may use) is 119, and every PAD and HEAD value is the default of the source.
- Insufficient data: whether gcc inlined `call` into `worker` in the CRB binary. The build record shows only that a symbol `call` exists [Ref2]. An objdump listing of `worker` from the binary would resolve it. The binary is not in the local folders. The records hold its sha256 [Ref2] [Ref5]. They hold the listing of its kernel functions [Ref1]. They hold no listing of `worker`.

## Call sequence in the whole-chip test

- `main` (line 2904): entry point. rx.sh starts it under `taskset -c 0-119`
  - `now_ns` (line 327): line 2908: process start time `t_base_ns`
  - `restrict_cpus` (line 368): line 2911: removes CPUs above 119 from the allowed CPU set
  - `trial_main` (line 2800): NOT called: no argument is `--trial` (lines 2912 to 2914)
  - `parse_long` (line 353): `--threads 120`, `--rounds 2`, `--pmu-type 11`
  - `parse_cpus` (line 388): `--cpus 0-63,64-119`: the list 0, 1, ... 119
  - `parse_bytes` (line 334): `--bytes 256M`: 268435456 bytes
  - `parse_seq` (line 1750): `--seq`: each kernel name becomes an index into `kernels[]`
  - `parse_events` (line 1771): `--events`: 6 names and 6 codes
  - `worker` (line 1632): 120 threads, created at line 3012. Thread i runs on CPU i
    - `pin_cpu` (line 415): line 1642: binds the thread to its CPU
    - `open_counters` (line 1582): line 1644: opens the 6 counters as one group
    - `alloc_buf` (line 434): line 1645: maps the 256 MiB buffer, asks for 2 MiB pages
      - `buf_len` (line 426): buffer length, rounded up to a multiple of 2 MiB
    - `k_write` (line 531): line 1646: first touch, writes every word of the buffer once
    - `call` (line 1491): line 1669, per interval: warm-up, one untimed pass, same kernel as below
    - `now_ns` (line 327): line 1681: spin-wait until the common start time
    - `read_group` (line 1617): line 1685: first counter reading, before `t0`
    - `cpu_ns` (line 1609): line 1686: thread CPU time before `t0`
    - `now_ns` (line 327): line 1688: `t0`, the start of the timed interval
    - `call` (line 1491): line 1695, timed: one 2 MiB chunk per call
      - `k_oldread` (line 474): kernel `oldread`: the old read kernel, text in macro `DEF_OLDREAD` (line 461)
      - `k_read` (line 501): kernel `read`: the new read kernel (part C only)
      - `k_asmread` (line 642): kernel `asmread`: hand-written load-only loop, text in macro `DEF_ASMREAD` (line 616)
      - `k_read_nop96` (line 1063): asmread loop plus 96 nop, macro `DEF_ASMREAD` (part L and control I only)
      - `k_read_nop256` (line 1199): asmread loop plus 256 nop, macro `DEF_ASMREAD` (part L and control I only)
      - `k_read_1pl` (line 988): one 16 B load per 64 B line (part L and control I only)
    - `now_ns` (line 327): line 1700: `t1` after each chunk. The loop ends at the deadline
    - `cpu_ns` (line 1609): line 1718: thread CPU time after the last `t1`
    - `read_group` (line 1617): line 1719: second counter reading
  - `now_ns` (line 327): line 3059, main thread, per interval: common start = now + 2 ms
  - `libc:printf`: lines 3077 to 3102 of `main`: I row, T rows, C rows
  - `now_ns` (line 327): line 3110: start of the page-state reading
  - `read_smaps` (line 1515): line 3111, main thread: page state before the first and after each interval
    - `buf_len` (line 426): the length that the mapping of a buffer must have
  - `read_vmstat` (line 1545): line 3112: four counters of the whole system
  - `now_ns` (line 327): line 3113: end of the page-state reading, for its duration in ms
  - `print_p` (line 1570): line 3117: one P row per buffer
    - `print_na` (line 1562): one field, or `NA` for a negative value
  - `libc:printf`: line 3118 of `main`: the `# page_read` line

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `now_ns` | 327-332 | Reads the Linux clock CLOCK_MONOTONIC and returns it in ns. Every time stamp of the program comes from here. | - | yes |
| `parse_bytes` | 334-349 | Turns a size text such as `256M` into bytes. K, M and G mean 2^10, 2^20 and 2^30. A bad size ends the program. | - | no |
| `parse_long` | 353-363 | Turns a text into a whole number inside a given range. Any other text ends the program with status 2. | - | no |
| `restrict_cpus` | 368-385 | Removes every CPU above `MAX_USE_CPU` (119) from the allowed CPU set of the calling thread. | - | no |
| `parse_cpus` | 388-413 | Turns the `--cpus` list into the array `cfg.cpus`, in the order of the list. A CPU above 119 ends the program. | - | no |
| `pin_cpu` | 415-424 | Binds the calling thread to one CPU with `sched_setaffinity`. A failure ends the program. | - | no |
| `buf_len` | 426-429 | Returns the `--bytes` value rounded up to a multiple of 2 MiB. | - | no |
| `alloc_buf` | 434-451 | Maps one buffer that starts at a 2 MiB boundary, puts no-access ranges before and after it, and asks Linux for 2 MiB pages. | `buf_len` | no |
| `DEF_OLDREAD(name)` | 461-473 | Macro with the C text of the old read kernel: 16 running sums, one add per loaded 8-byte word, 128 B per outer loop pass. | - | yes |
| `DEF_OLDREAD(oldread): function k_oldread` | 474-474 | Kernel `oldread`, the old read kernel. Machine code per 128 B: 4 `ldp q` loads, 8 vector adds, 16 instructions [Ref1]. | - | yes |
| `k_read` | 501-528 | Kernel `read`, the new read kernel: 16 NEON loads of 16 B per 256 B, no arithmetic. Machine code: 8 `ldp q` per pass [Ref1]. | - | yes |
| `k_write` | 531-555 | NEON write kernel. The worker calls it once per buffer for the first touch. The test does not time it. | - | no |
| `DEF_ASMREAD(name, nops)` | 616-641 | Macro with a hand-written load-only loop: per 256 B 8 `ldp q` loads, then `nops` nop instructions, then add, cmp and branch. | - | yes |
| `DEF_ASMREAD(asmread, 0): function k_asmread` | 642-642 | Kernel `asmread`: the macro loop with 0 nop. 11 instructions per 256 B. Saves d8 to d15 once per call [Ref1]. | - | yes |
| `k_read_1pl` | 988-1004 | Kernel `read_1pl`: per 256 B four `ldr q` loads of 16 B, one at the start of each 64 B line. 7 instructions per pass. | - | yes |
| `DEF_ASMREAD(read_nop96, 96): function k_read_nop96` | 1063-1063 | Kernel `read_nop96`: the asmread loop with 96 nop instructions after the 8 loads. 107 instructions per 256 B [Ref1]. | - | yes |
| `DEF_ASMREAD(read_nop256, 256): function k_read_nop256` | 1199-1199 | Kernel `read_nop256`: the asmread loop with 256 nop instructions after the 8 loads. 267 instructions per 256 B [Ref1]. | - | yes |
| `call` | 1491-1509 | Runs one kernel on `len` bytes at byte offset `off` of the thread's buffer. Stores the sum of an old read kernel in `sink`. | `k_oldread`, `k_read`, `k_asmread`, `k_read_nop96`, `k_read_nop256`, `k_read_1pl` | yes |
| `read_smaps` | 1515-1542 | Reads /proc/self/smaps. Returns for each buffer its size and its part on 2 MiB pages, in kB, or -1 without an exact entry. | `buf_len` | no |
| `read_vmstat` | 1545-1560 | Reads four counters of the whole system from /proc/vmstat: `thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc`, `pgmigrate_success`. | - | no |
| `print_na` | 1562-1568 | Prints a comma and the number, or `,NA` when the number is negative. | - | no |
| `print_p` | 1570-1578 | Prints one P row: round, position, thread, buffer letter, the two page values and the four vmstat counters. | `print_na` | no |
| `open_counters` | 1582-1607 | Opens one counter per `--events` entry with `perf_event_open`: one group per thread, user mode only. A failed event is printed as NA. | - | no |
| `cpu_ns` | 1609-1614 | Returns the CPU time that the calling thread has used, in ns (clock CLOCK_THREAD_CPUTIME_ID). | - | no |
| `read_group` | 1617-1630 | Reads the counter group with one `read`: enabled time, running time, one value per open event. A failed read ends the program. | - | no |
| `worker` | 1632-1735 | One benchmark thread: pins itself, opens counters, maps its buffer and writes it once. Per interval: warm-up, common start, timed chunk loop, result. | `pin_cpu`, `open_counters`, `alloc_buf`, `k_write`, `call`, `read_smaps`, `read_vmstat`, `now_ns`, `read_group`, `cpu_ns` | yes |
| `usage` | 1737-1748 | Prints the option summary to stderr and ends the program with status 2. The argument lines of the test do not reach it. | - | no |
| `parse_seq` | 1750-1767 | Turns the `--seq` list into `cfg.seq`: one index into `kernels[]` per name, with an optional size after `@`. An unknown name ends the program. | `parse_bytes` | no |
| `parse_events` | 1771-1793 | Turns the `--events` list into names and codes for `cfg.ev_name` and `cfg.ev_code`. A code may be hexadecimal with `0x`. | - | no |
| `trial_main` | 2800-2886 | Entry of the trial mode. `main` calls it only when an argument is `--trial`. The whole-chip test does not call it. | `parse_long`, `parse_cpus`, `parse_bytes`, `parse_events`, `trial_usage`, `read_plan`, `pin_cpu`, `trial_worker` | no |
| `main` | 2904-3126 | Entry point. Chooses the mode, parses the arguments, starts the workers, sets the common start of each interval and prints all rows. | `now_ns`, `restrict_cpus`, `trial_main`, `selftest`, `parse_long`, `parse_cpus`, `parse_bytes`, `parse_seq`, `parse_events`, `usage`, `worker`, `print_p`, `read_smaps`, `read_vmstat` | no |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>File comment: history of the versions, newest first</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   1  /* bwx12+ */
   2  /*
   3   * bwx12.c - bwx11.c plus the additions of round 5 (2026-11-15). Every
   4   * addition stands between a line "bwx12+" and a line "bwx12-" (both are
   5   * comments). Without these blocks this file is bwx11.c byte for byte. So the
   6   * 29 kernels of bwx11, call(), timed_sequence(), timed_sequence_hot(), the
   7   * interval mode and the trial mode are the text of bwx11.c.
   8   *
   9   * Additions: 26 kernels. They stand after the last kernel of bwx11 in the
  10   * source and in kernels[], so the kernels of bwx11 keep their machine code
  11   * and their loop offsets. No option and no output row is added.
  12   *   read_nop48, read_nop56, read_nop72, read_nop80, read_nop88, read_nop112,
  13   *     read_nop160, read_nop192, read_nop256: the asmread loop with that many
  14   *     nop instructions after the 8 ldp (the macro of read_nop64).
  15   *   read_dadd2, read_dadd4, read_dadd8, read_dadd16: the asmread loop with 2,
  16   *     4, 8 or 16 vector adds after the 8 ldp. Each add takes a register that
  17   *     this iteration loaded, so it cannot run before the load data arrives.
  18   *   read_iadd16: the asmread loop with 16 vector adds that take no loaded
  19   *     register. It is the control of read_dadd16.
  20   *   read_sp24, read_sp32, read_sp40, read_sp48, read_sp56: the read_sparse
  21   *     loop (128 B per iteration, 4 ldp) with that many nop in place of 9.
  22   *   read_1pl_nop96: the read_1pl loop with 96 nop after the 4 loads.
  23   *   write_nop32, write_nop96, write_nop128, write_nop256: the asmwrite loop
  24   *     with that many nop after the 8 stp.
  25   *   copy_nop96, copy_nop192: the asmcopy loop with that many nop after the
  26   *     8 stp.
  27   *   A third pad after these kernels, so that call() and the code up to the
  28   *     end of timed_sequence_hot() keep their placement modulo 64.
  29   * The line that includes the self-test file is changed by additions only: the
  30   * old line stands inside "#if 0".
  31   * MAX_SEQ stays 64: the 55 kernels fit in one --seq list.
  32   */
  33  /* bwx12- */</pre></td><td valign="top"><ul><li>The file starts with four history comments, one per version of the runner. This one describes the newest version: bwx12.c is the older runner bwx11.c plus 26 kernels and a third pad after them. No option and no output row is new.</li><li>Every addition stands between a comment line <code>bwx12+</code> and a comment line <code>bwx12-</code>.</li><li>The new kernels stand after the kernels of bwx11, in the source and in the kernel table. Lines 9 to 11 give the reason: the kernels of bwx11 keep their machine code and their loop offsets.</li><li>Of the 26 new kernels the whole-chip test runs one: <code>read_nop256</code> (line 13).</li><li>The third pad keeps the function <code>call</code> at the same start address modulo 64 as in bwx11. The build record (the file build.txt that the build script wrote on CRB) gives the start address 24 modulo 64 for both versions [Ref2].</li><li>"Round 5" in line 3 names a round of work on the program. It is not a round of <code>--rounds</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  34  /* bwx11+ */
  35  /*
  36   * bwx11.c - bwx10.c plus the additions of round 4 (2026-11-15). Every
  37   * addition stands between a line "bwx11+" and a line "bwx11-" (both are
  38   * comments). Without these blocks this file is bwx10.c byte for byte:
  39   * test_runner11.py checks it. So the 26 kernels of bwx10, call(),
  40   * timed_sequence(), timed_sequence_hot() and the interval mode are the text
  41   * of bwx10.c.
  42   *
  43   * Additions:
  44   *   kernels read_nop64, read_nop96, read_nop128: the asmread loop with 64, 96
  45   *     and 128 nop instructions after the 8 ldp. They stand after the last
  46   *     kernel of bwx10 in the source and in kernels[], so the kernels of bwx10
  47   *     keep their machine code and their loop offsets.
  48   *   A second pad after these kernels, so that call() and the code up to the
  49   *     end of timed_sequence_hot() keep their placement modulo 64.
  50   *   --evict-mb N  (trial mode) before the first trial the worker writes N MiB
  51   *     of other memory twice. This pushes the benchmark buffer out of the
  52   *     caches, so its lines are read back from memory.
  53   *   M rows evict_mb and evict_ns. With --trace and N above 0 also the rows
  54   *     TR,-1,0,evict_start,&lt;t_ns&gt; and TR,-1,1,evict_end,&lt;t_ns&gt;.
  55   * The line that includes the self-test file is changed by additions only: the
  56   * old line stands inside "#if 0".
  57   * The plan file format is unchanged ("# bwx8-plan v1").
  58   */
  59  /* bwx11- */</pre></td><td valign="top">What bwx11 added to bwx10. The additions stand between <code>bwx11+</code> and <code>bwx11-</code>.<ul><li>3 kernels: <code>read_nop64</code>, <code>read_nop96</code> and <code>read_nop128</code>. The whole-chip test runs <code>read_nop96</code>.</li><li>A second pad after these kernels, again for the placement of <code>call</code>.</li><li>The option <code>--evict-mb</code> and its output rows. They belong to the trial mode. The whole-chip test does not use the trial mode.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  60  /* bwx10+ */
  61  /*
  62   * bwx10.c - bwx8.c plus the additions of round 3 (2026-11-15). Every addition
  63   * stands between a line "bwx10+" and a line "bwx10-" (both are comments).
  64   * Without these blocks, and with the name of the included self-test file set
  65   * back, this file is bwx8.c byte for byte: test_runner10.py checks it. So the
  66   * 21 kernels of bwx8, call(), timed_sequence() and the interval mode are the
  67   * text of bwx8.c.
  68   *
  69   * Additions:
  70   *   kernels read_pf256, read_pf512, read_pf1024, read_pf2048, read_1pl. They
  71   *     stand after the last kernel of bwx8 in the source and in kernels[], so
  72   *     the kernels of bwx8 keep their machine code and their loop offsets.
  73   *   --rec-pad BYTES  (trial mode) unused bytes before the win[] array of the
  74   *     record block.
  75   *   --hot-copy       (trial mode) timed_sequence_hot() runs the windows: it
  76   *     does not read or write win[i] between the first and the last pass of a
  77   *     window.
  78   *   M rows rec_pad, hot_copy, rec_addr, win_addr, win_size, stack_addr,
  79   *     buf_addr, tw_addr.
  80   *   A pad after the new kernels, so that call() and the code up to the end
  81   *     of timed_sequence() keep their placement modulo 64.
  82   * The plan file format is unchanged ("# bwx8-plan v1").
  83   */
  84  /* bwx10- */</pre></td><td valign="top">What bwx10 added to bwx8. The additions stand between <code>bwx10+</code> and <code>bwx10-</code>.<ul><li>5 kernels: <code>read_pf256</code>, <code>read_pf512</code>, <code>read_pf1024</code>, <code>read_pf2048</code> and <code>read_1pl</code>. The whole-chip test runs <code>read_1pl</code>.</li><li>The options <code>--rec-pad</code> and <code>--hot-copy</code>, and the output rows of lines 78 to 79. They belong to the trial mode.</li><li>A pad after the new kernels, for the placement of <code>call</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  85  /*
  86   * bwx8.c - scratch copy of bwx.c (crb/tmp/agent-scratch/bwx-2026-11-13) for
  87   * the design crb/new-test-kernel/tackle-8mb.md. The contract with the other
  88   * parts is DECISIONS-bwx8.md in this folder.
  89   *
  90   * Two modes:
  91   *   --seq ...    the interval mode of bwx.c. Its code is the text of bwx.c.
  92   *   --trial ...  one pinned worker runs the trials of a plan file. A trial is
  93   *                previous activity, prefix, predecessor and target windows
  94   *                with nothing but clock reads between them.
  95   *
  96   * Everything from "#define _GNU_SOURCE" to the end of parse_events() is the
  97   * text of bwx.c, so the kernels, PLACE, call() and alloc_buf() are unchanged.
  98   * All code of the trial mode stands after it. The build uses
  99   * -fno-toplevel-reorder, so the kernels keep their place in the binary.
 100   *
 101   * On AArch64 the kernels are the real ones. On any other machine every NEON
 102   * and asm kernel is replaced by a plain C stand-in, so that the harness can
 103   * be run on the development machine. Rates of a stand-in build mean nothing.
 104   * GB means 1e9 bytes throughout.
 105   */</pre></td><td valign="top">The oldest comment. bwx8.c is a copy of the first runner bwx.c, plus the trial mode.<ul><li><code>--seq ...</code> names the interval mode. The comment says that its code is the text of bwx.c. <code>main</code> runs this mode when no argument is the word <code>--trial</code> (lines 2912 to 2914). The whole-chip test uses this mode only.</li><li><code>--trial</code> selects the trial mode. All its code stands after the function <code>parse_events</code> (after line 1793).</li><li>Lines 98 to 99: the build uses the gcc flag <code>-fno-toplevel-reorder</code>. With it the kernels keep their place in the binary.</li><li>Lines 101 to 103: on AArch64 the kernels are the real ones. On another machine a stand-in replaces every NEON kernel and every asm kernel, and the rates of such a build mean nothing. CRB ran the AArch64 build (see the row of line 491).</li><li>Line 104: GB means 1e9 bytes in the whole file.</li></ul></td></tr>
<tr><td colspan="2"><b>Includes and constants</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 106  #define _GNU_SOURCE
 107  #ifdef __aarch64__
 108  #include &lt;arm_neon.h&gt;
 109  #endif
 110  #include &lt;errno.h&gt;
 111  #include &lt;linux/perf_event.h&gt;
 112  #include &lt;pthread.h&gt;
 113  #include &lt;sched.h&gt;
 114  #include &lt;setjmp.h&gt;
 115  #include &lt;signal.h&gt;
 116  #include &lt;stdatomic.h&gt;
 117  #include &lt;stdint.h&gt;
 118  #include &lt;stdio.h&gt;
 119  #include &lt;stdlib.h&gt;
 120  #include &lt;string.h&gt;
 121  #include &lt;sys/mman.h&gt;
 122  #include &lt;sys/syscall.h&gt;
 123  #include &lt;time.h&gt;
 124  #include &lt;unistd.h&gt;
 125</pre></td><td valign="top"><ul><li><code>_GNU_SOURCE</code> makes the Linux-specific declarations of the C library visible, for example <code>sched_setaffinity</code> and <code>CPU_SET</code>.</li><li><code>arm_neon.h</code> declares the NEON intrinsics. It is included only when the compiler builds for AArch64.</li><li><code>linux/perf_event.h</code> and <code>sys/syscall.h</code>: the structure <code>perf_event_attr</code> and the system call number for the counters (<code>open_counters</code>, line 1582).</li><li><code>pthread.h</code>, <code>sched.h</code> and <code>stdatomic.h</code>: threads and the barrier, CPU sets, and the atomic variables of the common start.</li><li><code>sys/mman.h</code>: <code>mmap</code>, <code>mprotect</code> and <code>madvise</code> for the buffers. <code>time.h</code>: <code>clock_gettime</code>.</li><li><code>setjmp.h</code> and <code>signal.h</code>: no line of bwx12.c itself uses them. The self-test file that line 2900 includes uses them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 126  #define HUGE_BYTES (2UL &lt;&lt; 20)
 127  #define MAX_CPUS 1024
 128  #define MAX_SEQ 64
 129  #define MAX_EV 8</pre></td><td valign="top"><ul><li><code>HUGE_BYTES</code>: 2097152 bytes (2 MiB), the size of one 2 MiB page. Every buffer starts at a multiple of it.</li><li><code>MAX_CPUS</code>: the <code>--cpus</code> list may hold at most 1024 CPUs.</li><li><code>MAX_SEQ</code>: the <code>--seq</code> list may hold at most 64 kernels. The test uses 5 or 3.</li><li><code>MAX_EV</code>: the <code>--events</code> list may hold at most 8 events. The test uses 6.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 130  #define CHECK_BYTES (8UL &lt;&lt; 20) /* --stop pass: clock is read after at least this many bytes */
 131  #define CHUNK_BYTES HUGE_BYTES  /* --stop common: clock is read after each chunk of this size */
 132  #define LEAD_NS 2000000L        /* --stop common: the common start is this long after the barrier */
 133  #define LATE_NS 100000L         /* --stop common: flag "late" if a thread starts later than this */</pre></td><td valign="top"><ul><li><code>CHECK_BYTES</code>: 8388608 bytes (8 MiB). Only <code>--stop pass</code> (line 1704) and the trial mode (line 2248) use it. The test runs with <code>--stop common</code>. So this value is not used in the test.</li><li><code>CHUNK_BYTES</code>: 2097152 bytes (2 MiB), the size of a chunk. With <code>--stop common</code> a worker calls the kernel on one chunk and then reads the clock (lines 1693 to 1700).</li><li><code>LEAD_NS</code>: 2000000 ns (2 ms). The main thread reads the clock and sets the common start of an interval to that clock value plus 2 ms (line 3059).</li><li><code>LATE_NS</code>: 100000 ns (100 us, which is 0.1 ms). A thread gets the late flag when its start clock read is more than this after the common start (line 1725).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 134  /* Highest CPU that the process may use. Rule of the test machine: CPUs 0 to
 135   * 119 only, never 126 or 127. main() removes every higher CPU from the
 136   * allowed set of the process, and --cpus rejects one. Another machine can
 137   * build with -DMAX_USE_CPU=N. */
 138  #ifndef MAX_USE_CPU
 139  #define MAX_USE_CPU 119
 140  #endif
 141</pre></td><td valign="top"><code>MAX_USE_CPU</code> is the highest CPU number that the process may use: 119, unless the build gives <code>-DMAX_USE_CPU=N</code>. The CRB build gave no <code>-D</code> option [Ref2]. <code>restrict_cpus</code> (line 368) and <code>parse_cpus</code> (line 388) apply the limit. The comment gives the rule of the test machine: CPUs 0 to 119 only, never 126 or 127.</td></tr>
<tr><td colspan="2"><b>Loop placement: the macro <code>PLACE</code> and the pads</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 142  /*
 143   * Loop placement (handoff B.7). PLACE(name) stands directly before kernel
 144   * k_&lt;name&gt;. It pads .text to a 64 B boundary and then adds PAD_&lt;name&gt; zero bytes,
 145   * so the function starts at PAD_&lt;name&gt; modulo 64. This needs the gcc flags
 146   * -fno-toplevel-reorder -falign-functions=4, and PAD must be a multiple of 4.
 147   *
 148   * For a kernel with a planned loop offset, PAD = (LOOP - HEAD) mod 64. LOOP
 149   * is the planned offset of the loop start modulo 64. HEAD is the number of
 150   * bytes between the function start and the loop start: 4 or 20 in the
 151   * listings of bw_new (results/kernels-20261113T181222Z/probe.txt). HEAD is a
 152   * guess until the objdump listing of the CRB build confirms it: override it
 153   * with -DHEAD_&lt;name&gt;=N, or the whole pad with -DPAD_&lt;name&gt;=N.
 154   * -DB3_OFFSET=0|36|52 puts the loops of copy, asmcopy and asmcopy2 at that
 155   * offset (step B3).
 156   *
 157   * For the other kernels the default PAD is the start offset modulo 64 that
 158   * the function has in bw_new (new C and asm kernels) or in bw_old (old
 159   * kernels). An A/A copy takes the PAD of its original.
 160   */</pre></td><td valign="top"><ul><li>Aim: the loop of each kernel starts at a known address modulo 64 (the loop offset). The specification of the first runner treats this offset as a test factor [Ref10].</li><li><code>PLACE(name)</code> stands directly before the kernel <code>k_&lt;name&gt;</code>. It makes the function start at the address <code>PAD_&lt;name&gt;</code> modulo 64.</li><li><code>LOOP</code> is the planned loop offset. <code>HEAD</code> is the number of bytes from the function start to the loop start. <code>PAD</code> is <code>LOOP</code> minus <code>HEAD</code>, modulo 64.</li><li>A kernel without a planned loop offset gets as <code>PAD</code> the start offset that its function has in bw_new or in bw_old (lines 157 to 159).</li><li>Result in the CRB binary: the loop of <code>k_read</code> starts at 36 modulo 64, and the loop of <code>k_oldread</code> starts at 40 modulo 64 [Ref1].</li><li>The <code>k_read</code> loop of bw_new also starts at 36 modulo 64, and the <code>k_read</code> loop of bw_old at 40 modulo 64 [Ref7]. So each of the two read kernels has the same loop offset in bwx12 as in its binary of part A.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 161  #define STR2(x) #x
 162  #define STR(x) STR2(x)</pre></td><td valign="top"><code>STR(x)</code> turns the value of the macro <code>x</code> into a text in quotes. Two steps are needed. <code>STR</code> first replaces a name such as <code>PAD_read</code> by its value 32. <code>STR2</code> then puts the quotes around the value.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 163  #define PLACE(name) __asm__(".pushsection .text\n.p2align 6\n.fill " STR(PAD_##name) ", 1, 0\n.popsection\n")</pre></td><td valign="top"><ul><li>An <code>__asm__</code> statement outside of a function passes its text to the assembler without a change.</li><li><code>.pushsection .text</code>: continue in the code section of the program. <code>.popsection</code>: return to the section that was in use before.</li><li><code>.p2align 6</code>: fill up to the next address that is a multiple of 64 (2^6).</li><li><code>.fill N, 1, 0</code>: add N bytes with the value 0. N is the value of <code>PAD_&lt;name&gt;</code>.</li><li>The comment of lines 145 to 146 names two gcc flags that this method needs: <code>-fno-toplevel-reorder</code> and <code>-falign-functions=4</code>. It adds that a pad must be a multiple of 4. Both flags are in the build record of CRB [Ref2].</li><li><code>-fno-toplevel-reorder</code>: the comment of lines 98 to 99 says that with this flag the kernels keep their place in the binary.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 164  #define PADOF(loop, head) (((loop) - (head)) &amp; 63)
 165</pre></td><td valign="top"><code>PADOF(loop, head)</code>: <code>loop</code> minus <code>head</code>, modulo 64. The operation <code>&amp; 63</code> keeps the low 6 bits. So a negative difference also gives a value from 0 to 63.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 166  #ifdef B3_OFFSET
 167  #define LOOP_copy B3_OFFSET
 168  #define LOOP_asmcopy B3_OFFSET
 169  #else
 170  #define LOOP_copy 36
 171  #define LOOP_asmcopy 52
 172  #endif
 173  #define LOOP_asmcopy_c 52</pre></td><td valign="top">Planned loop offsets of the copy kernels: 36 for <code>copy</code>, 52 for <code>asmcopy</code> and for the three <code>asmcopy_c</code> kernels. A build with <code>-DB3_OFFSET=N</code> would use N for <code>copy</code> and <code>asmcopy</code>. The CRB build gave no <code>-D</code> option [Ref2]. The whole-chip test runs no copy kernel.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 174  #ifndef HEAD_copy
 175  #define HEAD_copy 4
 176  #endif
 177  #ifndef HEAD_asmcopy
 178  #define HEAD_asmcopy 20
 179  #endif
 180  #ifndef HEAD_asmcopy_c
 181  #define HEAD_asmcopy_c 4
 182  #endif
 183  #ifndef HEAD_asmcopy_c_add
 184  #define HEAD_asmcopy_c_add 4
 185  #endif
 186  #ifndef HEAD_asmcopy_c_reg
 187  #define HEAD_asmcopy_c_reg 20
 188  #endif</pre></td><td valign="top"><code>HEAD</code> values of the copy kernels: 4 B or 20 B from the function start to the loop start. Each <code>#ifndef</code> block sets a default value that a <code>-D</code> option of the build can replace. The same pattern is used for every value up to line 251.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 189  #ifndef PAD_copy
 190  #define PAD_copy PADOF(LOOP_copy, HEAD_copy)
 191  #endif
 192  #ifndef PAD_asmcopy
 193  #define PAD_asmcopy PADOF(LOOP_asmcopy, HEAD_asmcopy)
 194  #endif
 195  #ifndef PAD_asmcopy2
 196  #define PAD_asmcopy2 PAD_asmcopy
 197  #endif
 198  #ifndef PAD_asmcopy_c
 199  #define PAD_asmcopy_c PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c)
 200  #endif
 201  #ifndef PAD_asmcopy_c_add
 202  #define PAD_asmcopy_c_add PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_add)
 203  #endif
 204  #ifndef PAD_asmcopy_c_reg
 205  #define PAD_asmcopy_c_reg PADOF(LOOP_asmcopy_c, HEAD_asmcopy_c_reg)
 206  #endif</pre></td><td valign="top">Pads of the copy kernels, computed with <code>PADOF</code>: 32 B for <code>copy</code>, <code>asmcopy</code>, <code>asmcopy2</code> and <code>asmcopy_c_reg</code>, and 48 B for <code>asmcopy_c</code> and <code>asmcopy_c_add</code>. The whole-chip test of 2026-11-17 runs none of these kernels.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 207  #ifndef PAD_read
 208  #define PAD_read 32
 209  #endif
 210  #ifndef PAD_write
 211  #define PAD_write 0
 212  #endif
 213  #ifndef PAD_asmread
 214  #define PAD_asmread 0
 215  #endif</pre></td><td valign="top">Pads of three functions that run in the test.<ul><li><code>PAD_read</code> = 32: the new read kernel <code>k_read</code> starts at 32 modulo 64. In the CRB binary it starts at the address 0x49a0, which is 32 modulo 64 [Ref1].</li><li><code>PAD_write</code> = 0: <code>k_write</code>, the function of the first touch, starts at 0 modulo 64. In the CRB binary it starts at 0x4a00 [Ref1].</li><li><code>PAD_asmread</code> = 0: <code>k_asmread</code> starts at 0 modulo 64. In the CRB binary it starts at 0x4ac0 [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 216  #ifndef PAD_asmread2
 217  #define PAD_asmread2 PAD_asmread
 218  #endif
 219  #ifndef PAD_asmwrite
 220  #define PAD_asmwrite 32
 221  #endif
 222  #ifndef PAD_asmwrite2
 223  #define PAD_asmwrite2 PAD_asmwrite
 224  #endif</pre></td><td valign="top">Pads of <code>asmread2</code> (0 B, the pad of <code>asmread</code>), <code>asmwrite</code> (32 B) and <code>asmwrite2</code> (32 B). The whole-chip test of 2026-11-17 runs none of these three kernels.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 225  #ifndef PAD_oldread
 226  #define PAD_oldread 0
 227  #endif</pre></td><td valign="top"><code>PAD_oldread</code> = 0: the old read kernel <code>k_oldread</code> starts at 0 modulo 64. In the CRB binary it starts at the address 0x4600 [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 228  #ifndef PAD_oldread2
 229  #define PAD_oldread2 PAD_oldread
 230  #endif
 231  #ifndef PAD_oldwrite
 232  #define PAD_oldwrite 32
 233  #endif
 234  #ifndef PAD_oldcopy
 235  #define PAD_oldcopy 32
 236  #endif</pre></td><td valign="top">Pads of <code>oldread2</code> (0 B, the pad of <code>oldread</code>), <code>oldwrite</code> (32 B) and <code>oldcopy</code> (32 B). The whole-chip test of 2026-11-17 runs none of these three kernels.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 237  #ifndef PAD_read_nop4
 238  #define PAD_read_nop4 PAD_asmread
 239  #endif
 240  #ifndef PAD_read_nop8
 241  #define PAD_read_nop8 PAD_asmread
 242  #endif
 243  #ifndef PAD_read_nop16
 244  #define PAD_read_nop16 PAD_asmread
 245  #endif
 246  #ifndef PAD_read_nop32
 247  #define PAD_read_nop32 PAD_asmread
 248  #endif
 249  #ifndef PAD_read_sparse
 250  #define PAD_read_sparse PAD_asmread
 251  #endif
 252</pre></td><td valign="top">Pads of <code>read_nop4</code>, <code>read_nop8</code>, <code>read_nop16</code>, <code>read_nop32</code> and <code>read_sparse</code>. All five use the pad of <code>asmread</code>, which is 0 B. The whole-chip test of 2026-11-17 runs none of them. The pads of the test kernels <code>read_1pl</code>, <code>read_nop96</code> and <code>read_nop256</code> are defined later in the file (lines 927 to 929, 1056 to 1058 and 1134 to 1136).</td></tr>
<tr><td colspan="2"><b>Data types and global variables</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 253  enum ktype { T_READ, T_WRITE, T_COPY, T_OLDREAD };
 254  typedef void (*read_fn)(const uint64_t *, size_t);
 255  typedef uint64_t (*oldread_fn)(const uint64_t *, size_t);
 256  typedef void (*write_fn)(uint64_t *, size_t, uint64_t);
 257  typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);
 258</pre></td><td valign="top"><ul><li><code>enum ktype</code>: the four kernel types. The function <code>call</code> (line 1491) chooses the argument list of a kernel by its type.</li><li><code>read_fn</code> (type T_READ): the kernel gets the start address and the number of 8-byte words. It returns nothing. The test kernels <code>read</code>, <code>asmread</code>, <code>read_nop96</code>, <code>read_nop256</code> and <code>read_1pl</code> have this type.</li><li><code>oldread_fn</code> (type T_OLDREAD): the same two arguments, and the kernel returns a 64-bit sum. The test kernel <code>oldread</code> has this type.</li><li><code>write_fn</code> and <code>copy_fn</code>: the types of the write kernels and the copy kernels. No timed interval of the test runs a kernel of these two types.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 259  struct entry {
 260      int k;          /* index into kernels[] */
 261      uint64_t bytes; /* 0 until main() replaces it by --bytes */
 262  };
 263</pre></td><td valign="top">One entry of the <code>--seq</code> list: the index of the kernel in the kernel table, and the size of the range that the kernel works on. <code>bytes</code> is 0 when the entry has no <code>@SIZE</code> part. <code>main</code> then sets it to the <code>--bytes</code> value (lines 2989 to 2990). In the test every entry gets 268435456 bytes (256 MiB).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 264  static struct {
 265      int threads;
 266      int ncpus;
 267      int cpus[MAX_CPUS];
 268      uint64_t bytes;
 269      double min_s;
 270      int use_thp;
 271      struct entry seq[MAX_SEQ];
 272      int nseq;
 273      int rounds;</pre></td><td valign="top"><code>cfg</code> holds the settings of the process. Values in the test:<ul><li><code>threads</code> = 120. <code>ncpus</code> = 120, and <code>cpus[i]</code> = i for i from 0 to 119.</li><li><code>bytes</code> = 268435456 (256 MiB per thread).</li><li><code>min_s</code> = 6.0: the deadline of an interval is 6 s after its common start.</li><li><code>use_thp</code> = 1: the program asks for 2 MiB pages.</li><li><code>seq</code> and <code>nseq</code>: the kernel list of <code>--seq</code>. It has 5 entries for like.spec and 3 entries for cfwd.spec and crev.spec. <code>rounds</code> = 2: the list runs 2 times.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 274      int stop_common;  /* --stop common */
 275      int start_offset; /* --start offset */
 276      int two_buffers;  /* buffer b exists: --two-buffers, or a copy kernel in the sequence */
 277      int count;        /* --count */
 278      long pmu_type;    /* --pmu-type: the "type" field of perf_event_attr */
 279      int nev;
 280      char ev_name[MAX_EV][32];
 281      uint64_t ev_code[MAX_EV];
 282  } cfg = { .threads = 1, .min_s = 0.5, .use_thp = 1, .rounds = 1, .pmu_type = -1 };
 283</pre></td><td valign="top"><ul><li><code>stop_common</code> = 1 (<code>--stop common</code>).</li><li><code>start_offset</code> = 0 (<code>--start common</code>): every thread starts each interval at byte 0 of its own buffer (line 1662). This option chooses a place in the buffer. It does not set the start time of an interval.</li><li><code>two_buffers</code> = 0: no copy kernel is in the list, and each thread has one buffer.</li><li><code>count</code> = 1 (<code>--count</code>). <code>pmu_type</code> = 11. <code>nev</code> = 6, with the 6 names and the 6 codes of <code>--events</code>.</li><li>Line 282 sets the defaults: 1 thread, 0.5 s per interval, a request for 2 MiB pages, 1 round, and no PMU type (-1). Every other field starts at 0.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 284  struct page {
 285      long kb_total, kb_huge; /* -1: no exact entry in /proc/self/smaps */
 286  };
 287</pre></td><td valign="top">The page state of one buffer: its size and the part of it on 2 MiB pages, both in kB. <code>read_smaps</code> (line 1515) fills it. The value -1 means that the buffer was not found as one exact entry of <code>/proc/self/smaps</code>. It is printed as <code>NA</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 288  struct counts {
 289      uint64_t cpu_ns;              /* CLOCK_THREAD_CPUTIME_ID */
 290      uint64_t enabled, running;    /* of the counter group */
 291      uint64_t val[MAX_EV];
 292  };
 293</pre></td><td valign="top">One reading of the counters of a thread: the thread CPU time, the enabled time and the running time of the counter group, and one value per event.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 294  /* One thread, one interval. Written by the worker between the start barrier
 295   * and the end barrier of the interval; read by main() after the end barrier. */
 296  struct result {
 297      uint64_t bytes;
 298      int64_t t_sched, t_start, t_end; /* CLOCK_MONOTONIC, ns */
 299      int late;
 300      struct page pg[2]; /* one-thread process only: read by the worker before the interval */
 301      long long vm[4];
 302      struct counts c0, c1;
 303  };
 304</pre></td><td valign="top">The result of one thread for one interval.<ul><li><code>bytes</code>: the bytes that the thread counted in the interval. <code>late</code>: the late flag.</li><li><code>t_sched</code>: the common start time. <code>t_start</code>: the start clock read <code>t0</code> of the thread. <code>t_end</code>: its last clock read <code>t1</code>. All three are values of the clock CLOCK_MONOTONIC in ns.</li><li><code>c0</code> and <code>c1</code>: the counter readings before <code>t0</code> and after the last <code>t1</code>.</li><li><code>pg</code> and <code>vm</code>: only a process with one thread uses them. The test does not.</li><li>The worker stores the structure at line 1726, before its barrier of line 1727. <code>main</code> reads it after its barrier of line 3064. So the two threads never use it at the same time.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 305  struct thread {
 306      int idx;
 307      int cpu;
 308      uint64_t *a, *b;
 309      int group_fd;      /* leader of the counter group, -1 if no event opened */
 310      int ev_pos[MAX_EV]; /* position of the event in the group read, -1 if it did not open */
 311      int nopen;
 312      struct result res;
 313      pthread_t tid;
 314  };
 315</pre></td><td valign="top">One record per worker.<ul><li><code>idx</code>: the thread number, 0 to 119 in the test. <code>cpu</code>: the CPU of the thread. In the test the two are equal (line 3011).</li><li><code>a</code>: the buffer. <code>b</code>: the second buffer, which only a copy kernel needs. It stays NULL in the test.</li><li><code>group_fd</code>, <code>ev_pos</code> and <code>nopen</code>: the counter group of the thread. <code>open_counters</code> (line 1582) sets them.</li><li><code>res</code>: the result of the last interval. <code>tid</code>: the thread handle that <code>pthread_create</code> returns.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 316  static pthread_barrier_t bar;
 317  static int64_t t_base_ns; /* clock at process start: printed times are relative to it */
 318  static long page_bytes;
 319</pre></td><td valign="top"><ul><li><code>bar</code>: the barrier. <code>main</code> creates it for 121 threads at line 3005.</li><li><code>t_base_ns</code>: the clock value at the process start (line 2908). The times in the T rows are relative to it.</li><li><code>page_bytes</code>: the page size that Linux reports (line 2909). <code>alloc_buf</code> uses it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 320  /* --stop common (handoff B.4). gen only grows. main() stores the two times
 321   * before it increments gen, so a worker that sees the new gen reads the new
 322   * times. */
 323  static _Atomic uint64_t gen;
 324  static _Atomic int64_t t_sched_ns;
 325  static _Atomic int64_t deadline_ns;
 326</pre></td><td valign="top">The three shared variables of the common start. <code>_Atomic</code>: every load and every store of such a variable is one indivisible step.<ul><li><code>gen</code> starts at 0 and only grows.</li><li>For each interval <code>main</code> first stores the start time <code>t_sched_ns</code> and the stop time <code>deadline_ns</code>. Then it adds 1 to <code>gen</code> (lines 3060 to 3062).</li><li>A worker first waits for the new value of <code>gen</code> (line 1677). Then it loads the two times (lines 1679 to 1680). So it never uses the times of the interval before.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>now_ns</code>: the clock</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 327  static int64_t now_ns(void)
 328  {
 329      struct timespec ts;
 330      clock_gettime(CLOCK_MONOTONIC, &amp;ts);
 331      return (int64_t)ts.tv_sec * 1000000000L + ts.tv_nsec;
 332  }
 333</pre></td><td valign="top">Reads the Linux clock CLOCK_MONOTONIC with <code>clock_gettime</code> and returns the time in ns as one 64-bit number. Every time stamp of the program comes from this function.<ul><li>In a timed interval the worker calls it once for the start <code>t0</code> (line 1688) and once after each 2 MiB chunk for <code>t1</code> (line 1700).</li><li>So one clock read per chunk is inside the timed interval. This is the same for every kernel of the test.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>parse_bytes</code>: a size text such as <code>256M</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 334  static uint64_t parse_bytes(const char *s)
 335  {
 336      char *end;
 337      double v = strtod(s, &amp;end);
 338      double mul = 1;
 339      switch (*end) {
 340      case 'k': case 'K': mul = 1UL &lt;&lt; 10; end++; break;
 341      case 'm': case 'M': mul = 1UL &lt;&lt; 20; end++; break;
 342      case 'g': case 'G': mul = 1UL &lt;&lt; 30; end++; break;
 343      }</pre></td><td valign="top"><code>strtod</code> reads the number. A letter after it multiplies the number: <code>k</code> or <code>K</code> by 2^10, <code>m</code> or <code>M</code> by 2^20, <code>g</code> or <code>G</code> by 2^30. In the test <code>--bytes 256M</code> gives 256 times 2^20, which is 268435456 bytes. <code>main</code> calls the function for <code>--bytes</code> (line 2937).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 344      if (end == s || *end != '\0' || v &lt;= 0 || (uint64_t)(v * mul) == 0) { /* 0 bytes after rounding is no size */
 345          fprintf(stderr, "bad size: %s\n", s);
 346          exit(2);
 347      }
 348      return (uint64_t)(v * mul);
 349  }
 350</pre></td><td valign="top">The program ends with the message <code>bad size</code> and exit status 2 in four cases: the text holds no number, other text follows the size, the value is 0 or below, or the size is 0 bytes after rounding. Otherwise the function returns the size in bytes.</td></tr>
<tr><td colspan="2"><b>Function <code>parse_long</code>: a whole number inside a range</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 351  /* A whole number in [lo, hi], with nothing after it. Anything else ends the
 352   * program: a malformed value must not run as 0. */
 353  static long parse_long(const char *s, const char *what, long lo, long hi)
 354  {
 355      char *end;
 356      errno = 0;
 357      long v = strtol(s, &amp;end, 10);
 358      if (end == s || *end != '\0' || errno != 0 || v &lt; lo || v &gt; hi) {
 359          fprintf(stderr, "bad %s: '%s' (a whole number from %ld to %ld is needed)\n", what, s, lo, hi);
 360          exit(2);
 361      }
 362      return v;
 363  }
 364</pre></td><td valign="top"><code>strtol</code> reads a decimal whole number. The program ends with exit status 2 when the text holds no digit, when other text follows the number, when the number does not fit the type <code>long</code>, or when it lies outside the range <code>lo</code> to <code>hi</code>. On the path of the test: <code>--threads 120</code> (allowed 1 to 4096), <code>--rounds 2</code> (1 to 1000000) and <code>--pmu-type 11</code> (0 to 2147483647).</td></tr>
<tr><td colspan="2"><b>Function <code>restrict_cpus</code>: no CPU above 119</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 365  /* Removes every CPU above MAX_USE_CPU from the allowed set of the calling
 366   * thread. main() calls it before it starts a thread, so the main thread and
 367   * every worker (also one without --cpus) stay on the permitted CPUs. */
 368  static void restrict_cpus(void)
 369  {
 370      cpu_set_t set;
 371      int changed = 0;
 372      if (sched_getaffinity(0, sizeof set, &amp;set) != 0) {
 373          perror("sched_getaffinity");
 374          exit(2);
 375      }</pre></td><td valign="top"><ul><li><code>sched_getaffinity</code> reads the set of CPUs on which Linux may run the calling thread. The first argument 0 means the calling thread. A failure ends the program with exit status 2.</li><li><code>main</code> calls this function before it creates a thread (line 2911). The comment says that the main thread and every worker then stay on the permitted CPUs.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 376      for (int c = MAX_USE_CPU + 1; c &lt; CPU_SETSIZE; c++)
 377          if (CPU_ISSET(c, &amp;set)) {
 378              CPU_CLR(c, &amp;set);
 379              changed = 1;
 380          }</pre></td><td valign="top">Removes every CPU number above <code>MAX_USE_CPU</code> (119) from the set. <code>changed</code> records whether the set held such a CPU. <code>CPU_SETSIZE</code> is the number of CPUs that the set type of the C library can hold.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 381      if (changed &amp;&amp; (CPU_COUNT(&amp;set) == 0 || sched_setaffinity(0, sizeof set, &amp;set) != 0)) {
 382          fprintf(stderr, "cannot keep the process on CPUs 0-%d\n", MAX_USE_CPU);
 383          exit(2);
 384      }
 385  }
 386</pre></td><td valign="top"><ul><li>Only when a CPU was removed, <code>sched_setaffinity</code> passes the smaller set to Linux. An empty set or a failed call ends the program with exit status 2.</li><li>In the test the script rx.sh starts the program under <code>taskset -c 0-119</code> [Ref3]. So the set holds no CPU above 119, <code>changed</code> stays 0, and the function changes nothing.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>parse_cpus</code>: the value of <code>--cpus</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 387  /* "0-119", "0,2,4-7", or "0-118:2" (range with a stride) */
 388  static void parse_cpus(char *list)
 389  {
 390      for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
 391          char *e, *e2;
 392          long lo = strtol(tok, &amp;e, 10), hi = lo, step = 1;
 393          if (e != tok &amp;&amp; *e == '-') {
 394              hi = strtol(e + 1, &amp;e2, 10);
 395              e = e2 == e + 1 ? tok : e2; /* "0-" has no upper bound */
 396              if (e != tok &amp;&amp; *e == ':') {
 397                  step = strtol(e + 1, &amp;e2, 10);
 398                  e = e2 == e + 1 ? tok : e2;
 399              }
 400          }</pre></td><td valign="top"><ul><li><code>strtok</code> splits the list at each comma. The loop handles one item per pass.</li><li>An item is one number, a range <code>lo-hi</code>, or a range with a step <code>lo-hi:step</code>. <code>strtol</code> reads each number.</li><li>When no digit follows <code>-</code> or <code>:</code>, lines 395 and 398 set <code>e</code> back to <code>tok</code>. The test of line 401 then rejects the item.</li><li>In the test the list is <code>0-63,64-119</code>: two ranges with the step 1.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 401          if (e == tok || *e != '\0' || lo &lt; 0 || hi &lt; lo || hi &gt; MAX_USE_CPU || step &lt; 1) {
 402              fprintf(stderr, "bad cpu list: %s (CPUs 0-%d only)\n", tok, MAX_USE_CPU);
 403              exit(2);
 404          }</pre></td><td valign="top">Rejects an item that holds other text, a negative start, an end below the start, an end above 119 (<code>MAX_USE_CPU</code>), or a step below 1. The program then ends with exit status 2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 405          for (long c = lo; c &lt;= hi; c += step) {
 406              if (cfg.ncpus == MAX_CPUS) {
 407                  fprintf(stderr, "bad cpu list: more than %d cpus\n", MAX_CPUS);
 408                  exit(2);
 409              }
 410              cfg.cpus[cfg.ncpus++] = (int)c;
 411          }
 412      }
 413  }
 414</pre></td><td valign="top"><ul><li>Appends every CPU number of the item to <code>cfg.cpus</code> and counts it in <code>cfg.ncpus</code>. More than 1024 entries end the program with exit status 2.</li><li>In the test the result is 120 entries in rising order: <code>cfg.cpus[i]</code> = i.</li><li><code>main</code> gives thread i the CPU <code>cfg.cpus[i]</code> (line 3011). So the threads 0 to 63 get the CPUs of mesh 0, and the threads 64 to 119 get CPUs of mesh 1.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>pin_cpu</code>: bind the calling thread to one CPU</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 415  static void pin_cpu(int cpu)
 416  {
 417      cpu_set_t set;
 418      CPU_ZERO(&amp;set);
 419      CPU_SET(cpu, &amp;set);
 420      if (sched_setaffinity(0, sizeof set, &amp;set) != 0) {
 421          perror("sched_setaffinity");
 422          exit(2);
 423      }
 424  }
 425</pre></td><td valign="top"><ul><li>Builds a CPU set that holds only <code>cpu</code> and passes it to <code>sched_setaffinity</code>. The first argument 0 means the calling thread.</li><li>After the call Linux runs this thread on that CPU only.</li><li>A failure ends the program with exit status 2.</li><li>Each worker calls the function at its start (line 1642), before it opens its counters and before it maps its buffer.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>buf_len</code>: the length of one buffer</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 426  static size_t buf_len(void)
 427  {
 428      return (cfg.bytes + HUGE_BYTES - 1) &amp; ~(HUGE_BYTES - 1);
 429  }
 430</pre></td><td valign="top">Rounds the <code>--bytes</code> value up to a multiple of 2 MiB. In the test the value 268435456 is already 128 times 2 MiB. So the result is 268435456 bytes.</td></tr>
<tr><td colspan="2"><b>Function <code>alloc_buf</code>: map one buffer, aligned to 2 MiB</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 431  /* The buffer starts at a 2 MiB boundary, at least one page above the start
 432   * of the mapping. The unused parts before and after it are PROT_NONE, so the
 433   * buffer is one entry of its own in /proc/self/smaps (handoff B.6). */
 434  static uint64_t *alloc_buf(void)
 435  {
 436      size_t len = buf_len(), maplen = len + 2 * HUGE_BYTES;</pre></td><td valign="top"><ul><li>Each worker calls this function once, after it has pinned itself (line 1645).</li><li><code>len</code> is the buffer length: 268435456 bytes (256 MiB) in the test.</li><li><code>maplen</code> is 4 MiB more: 272629760 bytes (260 MiB). The extra 4 MiB are needed for the alignment of line 442 and for the two no-access ranges of lines 443 to 444.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 437      uint8_t *raw = mmap(NULL, maplen, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
 438      if (raw == MAP_FAILED) {
 439          perror("mmap");
 440          exit(2);
 441      }</pre></td><td valign="top"><ul><li><code>mmap</code> asks Linux for <code>maplen</code> bytes of new memory that the process may read and write.</li><li><code>MAP_PRIVATE | MAP_ANONYMOUS</code>: the memory belongs to this process only, and no file backs it. <code>NULL</code>: Linux chooses the address.</li><li>A failed <code>mmap</code> ends the program with exit status 2.</li><li>The call does not yet give physical memory to the pages. That happens at the first touch (line 1646).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 442      uint8_t *p = (uint8_t *)(((uintptr_t)raw + (size_t)page_bytes + HUGE_BYTES - 1) &amp; ~(uintptr_t)(HUGE_BYTES - 1));</pre></td><td valign="top"><code>p</code> is the buffer start: the first 2 MiB boundary that lies at least one page above the start <code>raw</code> of the mapping. <code>page_bytes</code> is the page size of Linux. The buffer is the range from <code>p</code> to <code>p + len</code>. So it starts at an address that is a multiple of 2 MiB.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 443      if (mprotect(raw, (size_t)(p - raw), PROT_NONE) != 0 ||
 444          mprotect(p + len, (size_t)(raw + maplen - (p + len)), PROT_NONE) != 0)
 445          perror("mprotect of the guard ranges (continuing; page state will be NA)");</pre></td><td valign="top"><ul><li><code>mprotect</code> with <code>PROT_NONE</code> forbids every access to the unused range before the buffer and to the unused range after it.</li><li>The comment of lines 431 to 433 gives the purpose: the buffer is then one entry of its own in <code>/proc/self/smaps</code>. <code>read_smaps</code> (line 1515) looks for an entry with exactly the start and the end of the buffer.</li><li>A failed <code>mprotect</code> only prints a message, and the run continues. The script rx.sh writes the error output of the program to the file stderr.txt [Ref3]. In the test every stderr.txt is empty [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 446      /* MADV_NOHUGEPAGE matters on hosts with THP "always": without it --no-thp
 447       * would still get 2 MiB pages. */
 448      if (madvise(p, len, cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0)
 449          perror("madvise (continuing)");</pre></td><td valign="top"><ul><li><code>madvise</code> with <code>MADV_HUGEPAGE</code> asks Linux to use 2 MiB pages for the buffer.</li><li><code>cfg.use_thp</code> is 1 in the test. Only the option <code>--no-thp</code> sets it to 0 (line 2926), and no argument line of the test holds this option [Ref4].</li><li>A failed <code>madvise</code> only prints a message, and the run continues.</li><li>This function does not test whether the buffer got 2 MiB pages. The P rows show it: in the test each P row reports 262144 kB of 262144 kB on 2 MiB pages [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 450      return (uint64_t *)p;
 451  }
 452</pre></td><td valign="top">Returns the buffer start as a pointer to 8-byte words. No code of the interval mode unmaps a buffer. The buffer stays mapped until the process ends.</td></tr>
<tr><td colspan="2"><b>Old kernels: code of the old benchmark source</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 453  /*
 454   * Old kernels: k_read, k_write and k_copy of bandwidth.orig.c (the benchmark
 455   * until 2026-11-13), renamed. The old comment of k_read was: "16 independent
 456   * accumulators keep the loop load-bound: on 128-bit NEON gcc folds them into
 457   * 8 vector chains, enough to hide a 2-cycle add latency; on AVX-512 they
 458   * become 2 zmm chains." oldread2 is the A/A copy: the same source under a
 459   * second name (the build uses -fno-ipa-icf, so gcc keeps both).
 460   */</pre></td><td valign="top"><ul><li>The comment says: the kernels below are <code>k_read</code>, <code>k_write</code> and <code>k_copy</code> of bandwidth.orig.c, the benchmark source until 2026-11-13, under new names.</li><li>So <code>oldread</code> is the old read kernel. Apart from absolute addresses, its machine code in bwx12 has the same instruction text as <code>k_read</code> of the binary bw_old [Ref7].</li><li>The quoted old comment gives the reason for the 16 running sums ("accumulators"): with 16 separate sums the adds should not limit the speed of the loop. This is a statement of the old comment. It is not a result of the whole-chip test.</li><li>The old comment expects that gcc keeps the 16 sums in 8 vector registers. The machine-code listing of the CRB binary confirms it: the sums are in the registers v24 to v31 [Ref1].</li><li><code>oldread2</code> is the A/A copy. Line 459: the build uses the gcc flag <code>-fno-ipa-icf</code>, and gcc then keeps both functions. The flag is in the build record [Ref2].</li></ul></td></tr>
<tr><td colspan="2"><b>Macro <code>DEF_OLDREAD</code>: source text of the old read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 461  #define DEF_OLDREAD(name) \
 462      PLACE(name); \
 463      __attribute__((noinline)) static uint64_t k_##name(const uint64_t *a, size_t n) \
 464      { \</pre></td><td valign="top"><ul><li><code>DEF_OLDREAD(name)</code> writes <code>PLACE(name)</code> and one function <code>k_&lt;name&gt;</code>.</li><li><code>a</code> is the start of the range to read. <code>n</code> is the length of the range in 8-byte words. The function returns a 64-bit sum.</li><li><code>noinline</code>: gcc must keep the function separate from its caller. The listing shows <code>k_oldread</code> as a function of its own [Ref1].</li><li>In a timed interval of the test one call gets one 2 MiB chunk: <code>n</code> = 262144 words (line 1695). The warm-up pass calls the kernel once on the whole buffer (line 1669).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 465          uint64_t s[16] = { 0 }; \</pre></td><td valign="top"><code>s</code> holds the 16 running sums. All start at 0. Machine code, once per call and before the loop [Ref1]: 4 <code>stp</code> instructions (each stores two 16-byte registers) write 128 B of zeros to the stack, and the 8 registers v24 to v31 are set to 0. During the loop these 8 registers hold the 16 sums, two sums per register.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 466          for (size_t i = 0; i &lt; n; i += 16) \
 467              for (int j = 0; j &lt; 16; j++) \
 468                  s[j] += a[i + j]; \</pre></td><td valign="top"><ul><li>Source: the outer loop takes 16 words (128 B) per pass. The inner loop adds word <code>j</code> of these 16 words to sum <code>j</code>. So every loaded word is an input of one add.</li><li>Machine code: gcc compiled the inner loop to vector instructions. One loop pass is 16 instructions for 128 B [Ref1].</li><li>4 <code>ldp q</code> loads of 32 B each, at the byte offsets 0, 32, 64 and 96 from the read position.</li><li>8 vector adds. Each one adds one loaded register to one of the sum registers v24 to v31. One vector add performs two of the 16 adds of the source.</li><li><code>add x0, x0, #0x80</code> moves the read position by 128 B. <code>add x1, x1, #0x1</code> counts the pass. <code>cmp</code> and <code>b.cc</code> branch back while the count is below the number of passes.</li><li>No instruction of the loop stores to memory. gcc did not unroll the loop: one pass of the machine loop is one pass of the outer source loop.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 469          uint64_t sum = 0; \
 470          for (int j = 0; j &lt; 16; j++) \
 471              sum += s[j]; \
 472          return sum; \
 473      }</pre></td><td valign="top"><ul><li>After the loop the function adds the 16 sums into one value and returns it.</li><li>Machine code, once per call [Ref1]: the 8 sum registers are stored to the stack and loaded back. Then 7 vector adds and one <code>addp</code> add them into one number. <code>addp</code> adds the two 64-bit halves of one register. <code>fmov x0, d31</code> copies the result into the return register x0.</li><li><code>call</code> stores the returned value into the volatile variable <code>sink</code> (line 1500). So the sum is used, and the compiler cannot remove the loads and the adds as unused work.</li><li>gcc also added a stack check to this function. It saves a guard value on the stack at the start and compares it before the return. A changed value leads to a call of <code>__stack_chk_fail</code> [Ref1].</li><li>One call runs 53 instructions outside the loop. One 2 MiB chunk is 16384 loop passes, which are 262144 instructions.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_oldread</code>: kernel <code>oldread</code>, the old read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 474  DEF_OLDREAD(oldread)</pre></td><td valign="top"><ul><li>This line creates the function <code>k_oldread</code>. It is the kernel <code>oldread</code> of <code>--seq</code>, with the type T_OLDREAD in the kernel table (line 1462).</li><li>In the CRB binary the function starts at the address 0x4600 and its loop at 0x4668 (40 modulo 64) [Ref1].</li><li>For 256 B it runs 2 loop passes: 32 instructions with 8 <code>ldp q</code> loads, 16 vector adds and 2 branches. The new read kernel runs 11 instructions for 256 B (see the row of line 527).</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_oldread2</code>: A/A copy, not run in the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 475  DEF_OLDREAD(oldread2)
 476</pre></td><td valign="top">Creates <code>k_oldread2</code>, the A/A copy of the old read kernel. The whole-chip test of 2026-11-17 does not run it.</td></tr>
<tr><td colspan="2"><b>Function <code>k_oldwrite</code>: old write kernel, not run in the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 477  PLACE(oldwrite);
 478  __attribute__((noinline)) static void k_oldwrite(uint64_t *a, size_t n, uint64_t v)
 479  {
 480      for (size_t i = 0; i &lt; n; i++)
 481          a[i] = v;
 482  }
 483</pre></td><td valign="top">The kernel <code>oldwrite</code>: a plain C loop that stores the value <code>v</code> to every 8-byte word of the range. The whole-chip test of 2026-11-17 does not run it. The first touch of a buffer uses <code>k_write</code> (line 531).</td></tr>
<tr><td colspan="2"><b>Function <code>k_oldcopy</code>: old copy kernel, not run in the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 484  PLACE(oldcopy);
 485  __attribute__((noinline)) static void k_oldcopy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
 486  {
 487      for (size_t i = 0; i &lt; n; i++)
 488          d[i] = s[i];
 489  }
 490</pre></td><td valign="top">The kernel <code>oldcopy</code>: a plain C loop that copies <code>n</code> 8-byte words from <code>s</code> to <code>d</code>. <code>restrict</code> tells the compiler that the two ranges do not overlap. The whole-chip test of 2026-11-17 does not run it.</td></tr>
<tr><td colspan="2"><b>AArch64 branch: the kernels of the CRB binary</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 491  #if defined(__aarch64__)
 492  #define STANDIN 0
 493  /*
 494   * C kernels: unchanged from bench/bandwidth.c. Each iteration moves 256 B as
 495   * 16 vectors of 16 B and does no arithmetic on the data. Callers guarantee
 496   * n * 8 is a multiple of 256 and non-zero. The empty asm statement of k_read
 497   * and k_copy takes the 16 loaded vectors as inputs in NEON registers ("w"):
 498   * see the comment in bench/bandwidth.c.
 499   */</pre></td><td valign="top"><ul><li><code>#if defined(__aarch64__)</code>: the lines from here to the <code>#else</code> of line 851 are compiled only for AArch64. The lines from that <code>#else</code> to the <code>#endif</code> of line 897 hold the stand-ins for other machines.</li><li>The CRB binary was compiled from this first branch, and <code>STANDIN</code> is 0. Proof: line 3024 prints <code>kernels=aarch64</code> only in this case, and line 2 of every csv file of the test holds this text [Ref5].</li><li>Comment: the C kernels below are unchanged from the benchmark source bandwidth.c. Each loop pass moves 256 B as 16 vectors of 16 B and does no arithmetic on the data.</li><li>The caller must pass a size that is a multiple of 256 B and not 0. <code>main</code> checks the sizes (lines 2973 and 2991). A chunk is 2 MiB.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_read</code>: kernel <code>read</code>, the new read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 500  PLACE(read);</pre></td><td valign="top"><code>PLACE(read)</code> with <code>PAD_read</code> = 32: the function starts at 32 modulo 64. In the CRB binary <code>k_read</code> starts at the address 0x49a0 and its loop at 0x49a4 (36 modulo 64) [Ref1]. The loop of <code>k_read</code> in bw_new has the same offset 36 [Ref7].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 501  __attribute__((noinline)) static void k_read(const uint64_t *a, size_t n)
 502  {</pre></td><td valign="top"><ul><li>This is the kernel <code>read</code> of <code>--seq</code>, with the type T_READ in the kernel table (line 1460). In the test only part C runs it.</li><li><code>a</code> is the start of the range to read. <code>n</code> is the length of the range in 8-byte words. The function returns nothing: it computes no sum.</li><li><code>noinline</code>: gcc must keep the function separate from its caller. The listing shows it as a function of 13 instructions [Ref1].</li><li>Apart from absolute addresses, its instruction text equals the text of <code>k_read</code> in bw_new, the binary of part A [Ref7].</li><li>In a timed interval of the test one call gets one 2 MiB chunk: <code>n</code> = 262144 words (line 1695). The warm-up pass calls the kernel once on the whole buffer (line 1669).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 503      const uint64_t *p = a;
 504      const uint64_t *end = a + n;</pre></td><td valign="top"><ul><li><code>p</code> is the read position. <code>end</code> is the first address after the range: <code>a</code> plus <code>n</code> words.</li><li>Machine code, once per call and before the loop: <code>add x1, x0, x1, lsl #3</code> [Ref1].</li><li>Before this instruction the register x0 holds <code>a</code> and x1 holds <code>n</code>. After it x1 holds <code>end</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 505      do {</pre></td><td valign="top"><code>do</code>: the loop body runs once before the first test of the end. So the range must not be empty.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 506          uint64x2_t v0 = vld1q_u64(p + 0);
 507          uint64x2_t v1 = vld1q_u64(p + 2);
 508          uint64x2_t v2 = vld1q_u64(p + 4);
 509          uint64x2_t v3 = vld1q_u64(p + 6);</pre></td><td valign="top"><ul><li>Each <code>vld1q_u64(p + k)</code> loads 16 B, which are two 8-byte words, from word <code>k</code> after the read position.</li><li>These 4 lines load the bytes 0 to 63 of the current 256 B block.</li><li>Machine code: gcc joined each two neighbour loads into one <code>ldp q</code> load of 32 B. For these 4 lines: <code>ldp q31, q30, [x0]</code> and <code>ldp q29, q28, [x0, #32]</code> [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 510          uint64x2_t v4 = vld1q_u64(p + 8);
 511          uint64x2_t v5 = vld1q_u64(p + 10);
 512          uint64x2_t v6 = vld1q_u64(p + 12);
 513          uint64x2_t v7 = vld1q_u64(p + 14);</pre></td><td valign="top">The loads of the bytes 64 to 127 of the block. Machine code: <code>ldp q27, q26, [x0, #64]</code> and <code>ldp q25, q24, [x0, #96]</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 514          uint64x2_t v8 = vld1q_u64(p + 16);
 515          uint64x2_t v9 = vld1q_u64(p + 18);
 516          uint64x2_t v10 = vld1q_u64(p + 20);
 517          uint64x2_t v11 = vld1q_u64(p + 22);</pre></td><td valign="top">The loads of the bytes 128 to 191 of the block. Machine code: <code>ldp q23, q22, [x0, #128]</code> and <code>ldp q21, q20, [x0, #160]</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 518          uint64x2_t v12 = vld1q_u64(p + 24);
 519          uint64x2_t v13 = vld1q_u64(p + 26);
 520          uint64x2_t v14 = vld1q_u64(p + 28);
 521          uint64x2_t v15 = vld1q_u64(p + 30);</pre></td><td valign="top"><ul><li>The loads of the bytes 192 to 255 of the block. Machine code: <code>ldp q19, q18, [x0, #192]</code> and <code>ldp q17, q16, [x0, #224]</code> [Ref1].</li><li>One loop pass has 16 loads in the source and 8 <code>ldp q</code> loads in the machine code. It reads 256 B, each byte once, in rising address order.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 522          __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),
 523                           "w"(v4), "w"(v5), "w"(v6), "w"(v7),
 524                           "w"(v8), "w"(v9), "w"(v10), "w"(v11),
 525                           "w"(v12), "w"(v13), "w"(v14), "w"(v15));</pre></td><td valign="top"><ul><li>An <code>asm</code> statement with an empty instruction text. It adds no instruction to the loop.</li><li>It names the 16 loaded vectors as inputs that must be in vector registers (<code>"w"</code>). The comment in the benchmark source bandwidth.c gives the purpose: gcc must have all 16 values in registers at this point, and this keeps gcc from deleting the loads.</li><li>After this statement nothing uses the values. They are dropped. The listing shows no add and no other instruction that uses a loaded register [Ref1].</li><li>This is the difference to the old read kernel, which adds every loaded word to a sum.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 526          p += 32;</pre></td><td valign="top">Moves the read position forward by 32 words, which are 256 B. Machine code: <code>add x0, x0, #0x100</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 527      } while (p &lt; end);</pre></td><td valign="top"><ul><li>Repeats the loop while the read position is below the end. Machine code: <code>cmp x1, x0</code>, then <code>b.hi</code> back to the first <code>ldp</code> [Ref1].</li><li>One loop pass is 11 instructions for 256 B: 8 <code>ldp q</code>, 1 <code>add</code>, 1 <code>cmp</code> and 1 branch [Ref1].</li><li>One 2 MiB chunk is 8192 loop passes, which are 90112 instructions.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 528  }
 529</pre></td><td valign="top">End of <code>k_read</code>: one <code>ret</code> instruction. gcc used the registers q16 to q31 for the loads, and the function saves and restores no register [Ref1]. The <code>#if</code> branch of line 491 continues after this row, up to line 851.</td></tr>
<tr><td colspan="2"><b>Function <code>k_write</code>: NEON write kernel, used for the first touch</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 530  PLACE(write);
 531  __attribute__((noinline)) static void k_write(uint64_t *a, size_t n, uint64_t v)</pre></td><td valign="top"><ul><li>Lines 530 to 850 stand inside the first branch of the <code>#if defined(__aarch64__)</code> of line 491. That branch holds the AArch64 kernels. Its <code>#else</code> is at line 851.</li><li>The CRB binary holds this branch. The listing shows the <code>dup</code> and <code>stp</code> instructions of this function [Ref1]. <code>dup</code> copies one 8-byte value into both halves of a 16-byte vector register.</li><li><code>PLACE(write)</code> adds the pad of this kernel. <code>PAD_write</code> is 0 (line 211). So the function starts at a multiple of 64 bytes: address 0x4a00 in the listing [Ref1].</li><li><code>k_write</code> stores the value <code>v</code> to <code>n</code> 8-byte words, from the address <code>a</code> on.</li><li>In the test each worker calls it once on its whole buffer, directly after the allocation (line 1646). This is the first touch. It happens before the first interval, and it is not timed.</li><li>The kernel table also offers this function as the kernel <code>write</code>. No <code>--seq</code> list of the test names <code>write</code> [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 532  {
 533      uint64_t *p = a;
 534      const uint64_t *end = a + n;
 535      uint64x2_t q = vdupq_n_u64(v);</pre></td><td valign="top"><code>p</code> is the write pointer. <code>end</code> is the first address after the range: <code>a</code> plus <code>n</code> words. <code>vdupq_n_u64(v)</code> builds one 16-byte vector <code>q</code> that holds <code>v</code> twice. Machine code before the loop: <code>dup v31.2d, x2</code> (x2 holds <code>v</code>) and <code>add x1, x0, x1, lsl #3</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 536      do {
 537          vst1q_u64(p + 0, q);
 538          vst1q_u64(p + 2, q);
 539          vst1q_u64(p + 4, q);
 540          vst1q_u64(p + 6, q);
 541          vst1q_u64(p + 8, q);
 542          vst1q_u64(p + 10, q);
 543          vst1q_u64(p + 12, q);
 544          vst1q_u64(p + 14, q);
 545          vst1q_u64(p + 16, q);
 546          vst1q_u64(p + 18, q);
 547          vst1q_u64(p + 20, q);
 548          vst1q_u64(p + 22, q);
 549          vst1q_u64(p + 24, q);
 550          vst1q_u64(p + 26, q);
 551          vst1q_u64(p + 28, q);
 552          vst1q_u64(p + 30, q);</pre></td><td valign="top"><ul><li><code>do</code>: the loop body runs before the first test of the end.</li><li>Each <code>vst1q_u64(p + k, q)</code> stores the 16 bytes of <code>q</code> at word <code>k</code> after the write pointer. The 16 stores of one loop pass fill 256 B. Each byte is written once.</li><li>gcc joined each two neighbour stores into one <code>stp q31, q31</code> instruction. <code>stp</code> stores two 16-byte registers, which is 32 B. Here both are the register q31. The machine loop has 8 <code>stp</code> [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 553          p += 32;
 554      } while (p &lt; end);
 555  }
 556</pre></td><td valign="top"><ul><li>Line 553 moves the write pointer forward by 32 words, which is 256 B. Line 554 repeats the loop while the pointer is below <code>end</code>.</li><li>Machine code of one loop pass: <code>add x0, x0, #0x100</code>, 8 <code>stp</code>, <code>cmp x1, x0</code> and the branch <code>b.hi</code>. That is 11 instructions for 256 B [Ref1].</li><li>gcc put the <code>add</code> at the start of the loop pass. So the <code>stp</code> instructions use the offsets -256 to -32.</li><li>The first touch of a 256 MiB buffer runs 1048576 loop passes (268435456 B / 256 B).</li><li>The binary bw_new of part A holds the same instruction text for its <code>k_write</code> [Ref7].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_copy</code>: NEON copy kernel (the test does not run it)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 557  PLACE(copy);
 558  __attribute__((noinline)) static void k_copy(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
 559  {
 560      uint64_t *dp = d;
 561      const uint64_t *sp = s;
 562      const uint64_t *end = s + n;
 563      do {
 564          uint64x2_t v0 = vld1q_u64(sp + 0);
 565          uint64x2_t v1 = vld1q_u64(sp + 2);
 566          uint64x2_t v2 = vld1q_u64(sp + 4);
 567          uint64x2_t v3 = vld1q_u64(sp + 6);
 568          uint64x2_t v4 = vld1q_u64(sp + 8);
 569          uint64x2_t v5 = vld1q_u64(sp + 10);
 570          uint64x2_t v6 = vld1q_u64(sp + 12);
 571          uint64x2_t v7 = vld1q_u64(sp + 14);
 572          uint64x2_t v8 = vld1q_u64(sp + 16);
 573          uint64x2_t v9 = vld1q_u64(sp + 18);
 574          uint64x2_t v10 = vld1q_u64(sp + 20);
 575          uint64x2_t v11 = vld1q_u64(sp + 22);
 576          uint64x2_t v12 = vld1q_u64(sp + 24);
 577          uint64x2_t v13 = vld1q_u64(sp + 26);
 578          uint64x2_t v14 = vld1q_u64(sp + 28);
 579          uint64x2_t v15 = vld1q_u64(sp + 30);
 580          __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),
 581                           "w"(v4), "w"(v5), "w"(v6), "w"(v7),
 582                           "w"(v8), "w"(v9), "w"(v10), "w"(v11),
 583                           "w"(v12), "w"(v13), "w"(v14), "w"(v15));</pre></td><td valign="top"><ul><li>Kernel <code>copy</code>: copies <code>n</code> words from <code>s</code> to <code>d</code>.</li><li>Each loop pass loads 256 B with 16 NEON loads of 16 B.</li><li>The <code>__asm__</code> statement of lines 580 to 583 has an empty instruction text. It names the 16 loaded vectors as inputs in vector registers (<code>"w"</code>).</li><li>The whole-chip test of 2026-11-17 does not run this kernel. No <code>--seq</code> list of the test names a copy kernel [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 584          vst1q_u64(dp + 0, v0);
 585          vst1q_u64(dp + 2, v1);
 586          vst1q_u64(dp + 4, v2);
 587          vst1q_u64(dp + 6, v3);
 588          vst1q_u64(dp + 8, v4);
 589          vst1q_u64(dp + 10, v5);
 590          vst1q_u64(dp + 12, v6);
 591          vst1q_u64(dp + 14, v7);
 592          vst1q_u64(dp + 16, v8);
 593          vst1q_u64(dp + 18, v9);
 594          vst1q_u64(dp + 20, v10);
 595          vst1q_u64(dp + 22, v11);
 596          vst1q_u64(dp + 24, v12);
 597          vst1q_u64(dp + 26, v13);
 598          vst1q_u64(dp + 28, v14);
 599          vst1q_u64(dp + 30, v15);
 600          sp += 32;
 601          dp += 32;
 602      } while (sp &lt; end);
 603  }
 604</pre></td><td valign="top">16 stores of 16 B to the destination. Then both pointers move forward by 256 B. Machine code of one loop pass: 8 <code>ldp</code>, 8 <code>stp</code>, 2 <code>add</code>, <code>cmp</code> and <code>b.hi</code>. That is 20 instructions [Ref1].</td></tr>
<tr><td colspan="2"><b>Hand-written kernels in assembler text: the comment</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 605  /*
 606   * asm kernels: the asm text of bench/bandwidth.c, inside macros so that an
 607   * A/A copy is the same source under a second name. Each iteration moves
 608   * 256 B with 8 ldp/stp of q registers (16 B each). Callers guarantee n * 8
 609   * is a multiple of 256 and non-zero. v8-v15 are callee-saved in AAPCS64:
 610   * naming them as clobbers makes gcc save d8-d15 once per call, which is
 611   * outside the loop.
 612   *
 613   * DEF_ASMREAD(name, nops) puts "nops" nop instructions after the 8 ldp and
 614   * before the add (step B5). asmread and asmread2 have 0 of them.
 615   */</pre></td><td valign="top"><ul><li>From here to line 849 the loop of each kernel is assembler text inside an <code>__asm__</code> statement. gcc copies this text into the function.</li><li>The comment names bandwidth.c as the origin of the read loop, the write loop and the copy loop. Each of the three is the body of a macro here (<code>DEF_ASMREAD</code>, <code>DEF_ASMWRITE</code>, <code>DEF_ASMCOPY</code>). So one more line defines the same loop under a second name (an A/A copy).</li><li>One loop pass of each of these three loops moves 256 B. The read loop has 8 <code>ldp</code> instructions. The write loop has 8 <code>stp</code> instructions. The copy loop has 8 <code>ldp</code> and 8 <code>stp</code> instructions. Each of these instructions moves two 16-byte registers.</li><li>The size must be a multiple of 256 B and must not be 0. The loop tests the end only after a loop pass. <code>main</code> ends the program with status 2 when <code>--bytes</code> is 0 or is not a multiple of 256 B (line 2973). It does the same when the size of a <code>--seq</code> entry is not a multiple of 256 B (line 2991).</li><li>The comment gives the reason why d8 to d15 are saved once per call. The row of lines 638 to 641 explains it.</li><li>The comment links the parameter <code>nops</code> to step B5 of the earlier investigation [Ref10].</li></ul></td></tr>
<tr><td colspan="2"><b>Macro <code>DEF_ASMREAD</code>: the loop of <code>asmread</code>, <code>read_nop96</code> and <code>read_nop256</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 616  #define DEF_ASMREAD(name, nops) \
 617      PLACE(name); \
 618      __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \</pre></td><td valign="top"><ul><li><code>DEF_ASMREAD(name, nops)</code> defines one kernel function. The backslash at each line end continues the macro on the next line.</li><li><code>k_##name</code> joins <code>k_</code> and the first argument. <code>DEF_ASMREAD(asmread, 0)</code> defines the function <code>k_asmread</code>.</li><li>Three kernels of the test come from this macro: <code>asmread</code> (line 642), <code>read_nop96</code> (line 1063) and <code>read_nop256</code> (line 1199).</li><li><code>PLACE(name)</code> adds the pad <code>PAD_&lt;name&gt;</code> before the function. For these three kernels the pad is 0 bytes (lines 214, 1057 and 1135). So each function starts at a multiple of 64 bytes [Ref1].</li><li><code>a</code> is the start of the range. <code>n</code> is its length in 8-byte words. The function returns nothing.</li><li><code>noinline</code> forbids gcc to merge the function into its caller. So the listing shows each kernel as a function of its own [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 619      { \
 620          const uint64_t *p = a; \
 621          const uint64_t *end = a + n; \</pre></td><td valign="top"><code>p</code> is the read pointer. <code>end</code> is the first address after the range: <code>a</code> plus <code>n</code> words. Machine code: <code>add x1, x0, x1, lsl #3</code>, which computes x1 = x0 + 8 × x1. It runs once per call, before the loop [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 622          __asm__ volatile( \
 623              "1:\n\t" \</pre></td><td valign="top"><ul><li><code>__asm__ volatile( ... )</code> is a gcc statement that holds assembler text. gcc copies the text into the function. The listing shows the instructions in the order of the text [Ref1].</li><li><code>volatile</code> tells gcc to keep the statement, although no later code uses <code>p</code>.</li><li><code>\n\t</code> ends one line of the assembler text and indents the next one.</li><li><code>1:</code> is the label at the start of the loop. In the CRB binary the loops of <code>k_asmread</code>, <code>k_read_nop96</code> and <code>k_read_nop256</code> start at an address of 20 modulo 64 [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 624              "ldp q0, q1, [%[p]]\n\t" \
 625              "ldp q2, q3, [%[p], #32]\n\t" \
 626              "ldp q4, q5, [%[p], #64]\n\t" \
 627              "ldp q6, q7, [%[p], #96]\n\t" \</pre></td><td valign="top"><ul><li><code>%[p]</code> stands for the register that gcc chose for <code>p</code>. In the listing it is x0 [Ref1].</li><li>Each <code>ldp</code> loads 32 B from memory into two 16-byte vector registers. <code>ldp q0, q1, [x0]</code> puts the bytes 0 to 15 into q0 and the bytes 16 to 31 into q1.</li><li>These 4 instructions load the bytes 0 to 127 of the current block of 256 B into q0 to q7.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 628              "ldp q8, q9, [%[p], #128]\n\t" \
 629              "ldp q10, q11, [%[p], #160]\n\t" \
 630              "ldp q12, q13, [%[p], #192]\n\t" \
 631              "ldp q14, q15, [%[p], #224]\n\t" \</pre></td><td valign="top"><ul><li>These 4 instructions load the bytes 128 to 255 of the block into q8 to q15.</li><li>One loop pass has 8 load instructions. It reads 256 B, each byte once, in rising address order.</li><li>Nothing uses the loaded values. No instruction of the loop takes q0 to q15 as an input. The next loop pass overwrites the registers.</li><li>The old read kernel <code>k_oldread</code> (line 474) differs in this point. Its loop adds every loaded register to a sum: 8 vector adds per 128 B [Ref1].</li><li>The unrolling is part of this text: 8 <code>ldp</code> per loop pass. gcc does not change the instructions of assembler text. It only puts register names in the places of <code>%[p]</code> and <code>%[end]</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 632              ".rept " #nops "\n\tnop\n\t.endr\n\t" \</pre></td><td valign="top"><ul><li><code>#nops</code> turns the second macro argument into text. For <code>read_nop96</code> the assembler sees the three lines <code>.rept 96</code>, <code>nop</code> and <code>.endr</code>.</li><li><code>.rept N</code> and <code>.endr</code> are assembler directives. The assembler repeats the lines between them N times. With <code>.rept 0</code> it writes nothing.</li><li>Result in the listing, between the last <code>ldp</code> and the <code>add</code>: 0 <code>nop</code> in <code>k_asmread</code>, 96 in <code>k_read_nop96</code>, 256 in <code>k_read_nop256</code> [Ref1].</li><li><code>nop</code> does nothing. It loads nothing. So every loop pass still reads 256 B, and only the instruction count of the loop pass grows.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 633              "add %[p], %[p], #256\n\t" \
 634              "cmp %[p], %[end]\n\t" \
 635              "b.lo 1b\n\t" \</pre></td><td valign="top"><ul><li><code>add</code> moves the read pointer forward by 256 B.</li><li><code>cmp</code> compares the pointer with <code>end</code>. <code>b.lo 1b</code> branches back to the label <code>1</code> while the pointer is below <code>end</code>. <code>lo</code> means lower in an unsigned compare.</li><li>Machine code: <code>add x0, x0, #0x100</code>, <code>cmp x0, x1</code>, <code>b.cc</code>. The listing prints <code>b.cc</code> for this branch and names <code>b.lo</code> as another name of it [Ref1].</li><li>Instructions of one loop pass: 8 <code>ldp</code>, the <code>nop</code> instructions and these 3. <code>asmread</code>: 11 per 256 B. <code>read_nop96</code>: 107. <code>read_nop256</code>: 267 [Ref1].</li><li>The end test stands after the loop body. So the body runs at least once in every call.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 636              : [p] "+r"(p) \
 637              : [end] "r"(end) \</pre></td><td valign="top"><ul><li>These two lines tell gcc which C variables the text uses.</li><li><code>[p] "+r"(p)</code>: <code>p</code> is in a general register. The text reads it and changes it.</li><li><code>[end] "r"(end)</code>: <code>end</code> is an input in a general register. In the listing it is x1 [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 638              : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \
 639                "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \
 640                "memory", "cc"); \
 641      }</pre></td><td valign="top"><ul><li>The last list is the clobber list. It tells gcc what the text changes besides <code>p</code>: the vector registers v0 to v15 and the condition flags (<code>"cc"</code>). <code>"memory"</code> says that the text accesses memory that no operand names.</li><li>v8 to v15 are in the list. So gcc saves d8 to d15 on the stack before the loop (4 <code>stp</code> instructions) and loads them back after it (4 <code>ldp</code> instructions) [Ref1].</li><li>This save runs once per call of the kernel, not once per loop pass.</li><li>In a timed interval of the test one call covers one 2 MiB chunk (line 1695). That is 8192 loop passes.</li><li><code>k_asmread</code> has 21 instructions: 5 before the loop, 11 in the loop and 5 after it, with <code>ret</code> as the last one [Ref1].</li></ul></td></tr>
<tr><td colspan="2"><b><code>DEF_ASMREAD(asmread, 0)</code>: the kernel <code>asmread</code> of the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 642  DEF_ASMREAD(asmread, 0)</pre></td><td valign="top"><ul><li>Defines <code>k_asmread</code>, the kernel <code>asmread</code>: the macro loop with 0 <code>nop</code>. One loop pass has 8 <code>ldp</code> loads of 32 B, <code>add</code>, <code>cmp</code> and the branch. That is 11 instructions per 256 B [Ref1].</li><li>The test runs it at position 1 in part L and control I. In part C it runs at position 2 (cfwd.spec) or position 0 (crev.spec) [Ref4].</li><li>The worker calls it through the function <code>call</code> (line 1491). Before each interval of this kernel one call covers the whole buffer: the warm-up pass (line 1669). In the timed interval one call covers one 2 MiB chunk (line 1695).</li><li>The instruction text of <code>k_asmread</code> equals the text of <code>k_asmread</code> in bw_new, the binary of part A [Ref7].</li><li><code>k_read</code> (line 501), the new read kernel, has the same 8 <code>ldp</code> loads and the same count of 11 instructions per 256 B [Ref1].</li><li>The two functions differ in four points. Register numbers: q0 to q15 here, q31 to q16 in <code>k_read</code>. Save of d8 to d15, outside the loop: only here. Loop start: 20 modulo 64 here, 36 in <code>k_read</code>. End test: <code>cmp x0, x1</code> with <code>b.cc</code> here, <code>cmp x1, x0</code> with <code>b.hi</code> in <code>k_read</code> [Ref1]. Both end tests branch back while the pointer is below <code>end</code>.</li></ul></td></tr>
<tr><td colspan="2"><b><code>asmread2</code> and <code>read_nop4</code> to <code>read_nop32</code> (not run by the test)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 643  DEF_ASMREAD(asmread2, 0)
 644  DEF_ASMREAD(read_nop4, 4)
 645  DEF_ASMREAD(read_nop8, 8)
 646  DEF_ASMREAD(read_nop16, 16)
 647  DEF_ASMREAD(read_nop32, 32)
 648</pre></td><td valign="top"><ul><li><code>asmread2</code>: the A/A copy of <code>asmread</code>. The listing shows the same instruction text for both [Ref1].</li><li><code>read_nop4</code>, <code>read_nop8</code>, <code>read_nop16</code>, <code>read_nop32</code>: the asmread loop with 4, 8, 16 or 32 <code>nop</code> per loop pass.</li><li>The whole-chip test of 2026-11-17 runs none of these five kernels [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_read_sparse</code> (the test does not run it)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 649  /* Step B5. Per 128 B: 4 ldp, 9 nop, add, cmp, b.lo. That is 16 instructions
 650   * per 128 B, as the old read loop has, and no vector add. */
 651  PLACE(read_sparse);
 652  __attribute__((noinline)) static void k_read_sparse(const uint64_t *a, size_t n)
 653  {
 654      const uint64_t *p = a;
 655      const uint64_t *end = a + n;
 656      __asm__ volatile(
 657          "1:\n\t"
 658          "ldp q0, q1, [%[p]]\n\t"
 659          "ldp q2, q3, [%[p], #32]\n\t"
 660          "ldp q4, q5, [%[p], #64]\n\t"
 661          "ldp q6, q7, [%[p], #96]\n\t"
 662          ".rept 9\n\tnop\n\t.endr\n\t"
 663          "add %[p], %[p], #128\n\t"
 664          "cmp %[p], %[end]\n\t"
 665          "b.lo 1b\n\t"
 666          : [p] "+r"(p)
 667          : [end] "r"(end)
 668          : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc");
 669  }
 670</pre></td><td valign="top"><ul><li>Kernel <code>read_sparse</code>: a read loop of 128 B per loop pass with 4 <code>ldp</code>, 9 <code>nop</code>, <code>add</code>, <code>cmp</code> and <code>b.lo</code>. That is 16 instructions per 128 B [Ref1].</li><li>The comment gives the aim: the instruction count of the old read loop, without its vector adds.</li><li>The whole-chip test of 2026-11-17 does not run this kernel [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Macro <code>DEF_ASMWRITE</code>: <code>asmwrite</code> and <code>asmwrite2</code> (not run by the test)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 671  #define DEF_ASMWRITE(name) \
 672      PLACE(name); \
 673      __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \
 674      { \
 675          uint64_t *p = a; \
 676          const uint64_t *end = a + n; \
 677          __asm__ volatile( \
 678              "dup v0.2d, %[v]\n\t" \
 679              "1:\n\t" \
 680              "stp q0, q0, [%[p]]\n\t" \
 681              "stp q0, q0, [%[p], #32]\n\t" \
 682              "stp q0, q0, [%[p], #64]\n\t" \
 683              "stp q0, q0, [%[p], #96]\n\t" \
 684              "stp q0, q0, [%[p], #128]\n\t" \
 685              "stp q0, q0, [%[p], #160]\n\t" \
 686              "stp q0, q0, [%[p], #192]\n\t" \
 687              "stp q0, q0, [%[p], #224]\n\t" \
 688              "add %[p], %[p], #256\n\t" \
 689              "cmp %[p], %[end]\n\t" \
 690              "b.lo 1b\n\t" \
 691              : [p] "+r"(p) \
 692              : [end] "r"(end), [v] "r"(v) \
 693              : "v0", "memory", "cc"); \
 694      }
 695  DEF_ASMWRITE(asmwrite)
 696  DEF_ASMWRITE(asmwrite2)
 697</pre></td><td valign="top"><ul><li>A hand-written write loop. <code>dup</code> copies <code>v</code> into both halves of v0. Each loop pass stores 256 B with 8 <code>stp q0, q0</code> instructions.</li><li>Lines 695 and 696 define <code>k_asmwrite</code> and its A/A copy <code>k_asmwrite2</code>.</li><li>The whole-chip test of 2026-11-17 runs neither of them [Ref4]. The first touch uses <code>k_write</code> (line 531), not this loop.</li></ul></td></tr>
<tr><td colspan="2"><b>Macro <code>DEF_ASMCOPY</code>: <code>asmcopy</code> and <code>asmcopy2</code> (not run by the test)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 698  #define DEF_ASMCOPY(name) \
 699      PLACE(name); \
 700      __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \
 701      { \
 702          uint64_t *dp = d; \
 703          const uint64_t *sp = s; \
 704          const uint64_t *end = s + n; \
 705          __asm__ volatile( \
 706              "1:\n\t" \
 707              "ldp q0, q1, [%[s]]\n\t" \
 708              "ldp q2, q3, [%[s], #32]\n\t" \
 709              "ldp q4, q5, [%[s], #64]\n\t" \
 710              "ldp q6, q7, [%[s], #96]\n\t" \
 711              "ldp q8, q9, [%[s], #128]\n\t" \
 712              "ldp q10, q11, [%[s], #160]\n\t" \
 713              "ldp q12, q13, [%[s], #192]\n\t" \
 714              "ldp q14, q15, [%[s], #224]\n\t" \
 715              "stp q0, q1, [%[d]]\n\t" \
 716              "stp q2, q3, [%[d], #32]\n\t" \
 717              "stp q4, q5, [%[d], #64]\n\t" \
 718              "stp q6, q7, [%[d], #96]\n\t" \
 719              "stp q8, q9, [%[d], #128]\n\t" \
 720              "stp q10, q11, [%[d], #160]\n\t" \
 721              "stp q12, q13, [%[d], #192]\n\t" \
 722              "stp q14, q15, [%[d], #224]\n\t" \
 723              "add %[s], %[s], #256\n\t" \
 724              "add %[d], %[d], #256\n\t" \
 725              "cmp %[s], %[end]\n\t" \
 726              "b.lo 1b\n\t" \
 727              : [s] "+r"(sp), [d] "+r"(dp) \
 728              : [end] "r"(end) \
 729              : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \
 730                "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \
 731                "memory", "cc"); \
 732      }
 733  DEF_ASMCOPY(asmcopy)
 734  DEF_ASMCOPY(asmcopy2)
 735</pre></td><td valign="top"><ul><li>A hand-written copy loop. Each loop pass loads 256 B from <code>s</code> with 8 <code>ldp</code> and stores them to <code>d</code> with 8 <code>stp</code>. Then both pointers move forward by 256 B.</li><li>Lines 733 and 734 define <code>k_asmcopy</code> and its A/A copy <code>k_asmcopy2</code>.</li><li>The whole-chip test of 2026-11-17 runs neither of them [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_asmcopy_c</code> (the test does not run it)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 736  /*
 737   * Step B2. asmcopy_c: the loop is the machine code of the C copy loop, from
 738   * the listing "bw_new k_copy" of probe.txt: same instruction order, same
 739   * offsets, registers q16 to q31, and "cmp end, s; b.hi" as its loop end. The
 740   * three pointers are bound to x0, x1 and x2, the registers of that listing.
 741   */
 742  PLACE(asmcopy_c);
 743  __attribute__((noinline)) static void k_asmcopy_c(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
 744  {
 745      register uint64_t *dp __asm__("x0") = d;
 746      register const uint64_t *sp __asm__("x1") = s;
 747      register const uint64_t *end __asm__("x2") = s + n;
 748      __asm__ volatile(
 749          "1:\n\t"
 750          "ldp q31, q30, [%[s]]\n\t"
 751          "ldp q29, q28, [%[s], #32]\n\t"
 752          "ldp q27, q26, [%[s], #64]\n\t"
 753          "ldp q25, q24, [%[s], #96]\n\t"
 754          "ldp q23, q22, [%[s], #128]\n\t"
 755          "ldp q21, q20, [%[s], #160]\n\t"
 756          "ldp q19, q18, [%[s], #192]\n\t"
 757          "ldp q17, q16, [%[s], #224]\n\t"
 758          "add %[s], %[s], #256\n\t"
 759          "stp q31, q30, [%[d]]\n\t"
 760          "add %[d], %[d], #256\n\t"
 761          "stp q29, q28, [%[d], #-224]\n\t"
 762          "stp q27, q26, [%[d], #-192]\n\t"
 763          "stp q25, q24, [%[d], #-160]\n\t"
 764          "stp q23, q22, [%[d], #-128]\n\t"
 765          "stp q21, q20, [%[d], #-96]\n\t"
 766          "stp q19, q18, [%[d], #-64]\n\t"
 767          "stp q17, q16, [%[d], #-32]\n\t"
 768          "cmp %[end], %[s]\n\t"
 769          "b.hi 1b\n\t"
 770          : [s] "+r"(sp), [d] "+r"(dp)
 771          : [end] "r"(end)
 772          : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",
 773            "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",
 774            "memory", "cc");
 775  }</pre></td><td valign="top"><ul><li>Kernel <code>asmcopy_c</code>, from step B2 of the earlier investigation [Ref10].</li><li>The comment says where its assembler text comes from: it repeats the machine code that gcc made for the C copy loop <code>k_copy</code> of the binary bw_new.</li><li>In the listing of bwx12, <code>k_asmcopy_c</code> and <code>k_copy</code> have the same instruction text [Ref1].</li><li><code>register ... __asm__("x0")</code> binds a C variable to the named register.</li><li>The whole-chip test of 2026-11-17 does not run this kernel [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_asmcopy_c_add</code> (the test does not run it)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 776
 777  /* As asmcopy_c, but the two add stand after the 8 stp, and the 8 stp use the
 778   * offsets 0 to 224, as in asmcopy. Registers stay q16 to q31. */
 779  PLACE(asmcopy_c_add);
 780  __attribute__((noinline)) static void k_asmcopy_c_add(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
 781  {
 782      register uint64_t *dp __asm__("x0") = d;
 783      register const uint64_t *sp __asm__("x1") = s;
 784      register const uint64_t *end __asm__("x2") = s + n;
 785      __asm__ volatile(
 786          "1:\n\t"
 787          "ldp q31, q30, [%[s]]\n\t"
 788          "ldp q29, q28, [%[s], #32]\n\t"
 789          "ldp q27, q26, [%[s], #64]\n\t"
 790          "ldp q25, q24, [%[s], #96]\n\t"
 791          "ldp q23, q22, [%[s], #128]\n\t"
 792          "ldp q21, q20, [%[s], #160]\n\t"
 793          "ldp q19, q18, [%[s], #192]\n\t"
 794          "ldp q17, q16, [%[s], #224]\n\t"
 795          "stp q31, q30, [%[d]]\n\t"
 796          "stp q29, q28, [%[d], #32]\n\t"
 797          "stp q27, q26, [%[d], #64]\n\t"
 798          "stp q25, q24, [%[d], #96]\n\t"
 799          "stp q23, q22, [%[d], #128]\n\t"
 800          "stp q21, q20, [%[d], #160]\n\t"
 801          "stp q19, q18, [%[d], #192]\n\t"
 802          "stp q17, q16, [%[d], #224]\n\t"
 803          "add %[s], %[s], #256\n\t"
 804          "add %[d], %[d], #256\n\t"
 805          "cmp %[end], %[s]\n\t"
 806          "b.hi 1b\n\t"
 807          : [s] "+r"(sp), [d] "+r"(dp)
 808          : [end] "r"(end)
 809          : "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",
 810            "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",
 811            "memory", "cc");
 812  }
 813</pre></td><td valign="top">Kernel <code>asmcopy_c_add</code>: the loop of <code>asmcopy_c</code> in another order. The two <code>add</code> instructions stand after the 8 <code>stp</code>. The <code>stp</code> offsets are 0 to 224. The whole-chip test of 2026-11-17 does not run this kernel [Ref4].</td></tr>
<tr><td colspan="2"><b>Function <code>k_asmcopy_c_reg</code> (the test does not run it)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 814  /* As asmcopy_c, but with the registers q0 to q15 (q31 becomes q0, q30
 815   * becomes q1, and so on), and d8 to d15 named as clobbered, as in asmcopy. */
 816  PLACE(asmcopy_c_reg);
 817  __attribute__((noinline)) static void k_asmcopy_c_reg(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
 818  {
 819      register uint64_t *dp __asm__("x0") = d;
 820      register const uint64_t *sp __asm__("x1") = s;
 821      register const uint64_t *end __asm__("x2") = s + n;
 822      __asm__ volatile(
 823          "1:\n\t"
 824          "ldp q0, q1, [%[s]]\n\t"
 825          "ldp q2, q3, [%[s], #32]\n\t"
 826          "ldp q4, q5, [%[s], #64]\n\t"
 827          "ldp q6, q7, [%[s], #96]\n\t"
 828          "ldp q8, q9, [%[s], #128]\n\t"
 829          "ldp q10, q11, [%[s], #160]\n\t"
 830          "ldp q12, q13, [%[s], #192]\n\t"
 831          "ldp q14, q15, [%[s], #224]\n\t"
 832          "add %[s], %[s], #256\n\t"
 833          "stp q0, q1, [%[d]]\n\t"
 834          "add %[d], %[d], #256\n\t"
 835          "stp q2, q3, [%[d], #-224]\n\t"
 836          "stp q4, q5, [%[d], #-192]\n\t"
 837          "stp q6, q7, [%[d], #-160]\n\t"
 838          "stp q8, q9, [%[d], #-128]\n\t"
 839          "stp q10, q11, [%[d], #-96]\n\t"
 840          "stp q12, q13, [%[d], #-64]\n\t"
 841          "stp q14, q15, [%[d], #-32]\n\t"
 842          "cmp %[end], %[s]\n\t"
 843          "b.hi 1b\n\t"
 844          : [s] "+r"(sp), [d] "+r"(dp)
 845          : [end] "r"(end)
 846          : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
 847            "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
 848            "memory", "cc");
 849  }
 850</pre></td><td valign="top">Kernel <code>asmcopy_c_reg</code>: the loop of <code>asmcopy_c</code> with the registers q0 to q15 in place of q31 to q16. The clobber list names v8 to v15. So gcc saves d8 to d15 once per call [Ref1]. The whole-chip test of 2026-11-17 does not run this kernel [Ref4].</td></tr>
<tr><td colspan="2"><b>Stand-ins for other machines (not in the CRB binary)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 851  #else
 852  /*
 853   * Stand-ins for a machine that is not AArch64: plain C loops that touch
 854   * exactly the same bytes as the real kernels. They exist only so that the
 855   * harness can be compiled and run on the development machine.
 856   */
 857  #define STANDIN 1</pre></td><td valign="top"><ul><li><code>#else</code> belongs to the <code>#if defined(__aarch64__)</code> of line 491. The compiler reads the lines 852 to 896 only for a machine that is not AArch64.</li><li>The CRB binary does not hold this code. Line 2 of every csv file of the test says <code>kernels=aarch64</code> [Ref5]. The program prints this word when <code>STANDIN</code> is 0 (line 3024).</li><li><code>STANDIN</code> is 1 in this branch. It is 0 in the AArch64 branch (line 492).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 858  #define DEF_ASMREAD(name, nops) \
 859      PLACE(name); \
 860      __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \
 861      { \
 862          const volatile uint64_t *p = a; \
 863          for (size_t i = 0; i &lt; n; i++) \
 864              (void)p[i]; \
 865      }
 866  #define DEF_ASMWRITE(name) \
 867      PLACE(name); \
 868      __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \
 869      { \
 870          for (size_t i = 0; i &lt; n; i++) \
 871              a[i] = v; \
 872      }
 873  #define DEF_ASMCOPY(name) \
 874      PLACE(name); \
 875      __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \
 876      { \
 877          for (size_t i = 0; i &lt; n; i++) \
 878              d[i] = s[i]; \
 879      }</pre></td><td valign="top"><ul><li>The three macro names of the AArch64 branch, here with plain C loops over the same range.</li><li><code>DEF_ASMREAD</code> reads every word through a <code>volatile</code> pointer. It does not use <code>nops</code>.</li><li><code>DEF_ASMWRITE</code> stores <code>v</code> to every word. <code>DEF_ASMCOPY</code> copies word by word.</li><li>Not compiled for CRB.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 880  DEF_ASMREAD(read, 0)
 881  DEF_ASMWRITE(write)
 882  DEF_ASMCOPY(copy)
 883  DEF_ASMREAD(asmread, 0)
 884  DEF_ASMREAD(asmread2, 0)
 885  DEF_ASMREAD(read_nop4, 4)
 886  DEF_ASMREAD(read_nop8, 8)
 887  DEF_ASMREAD(read_nop16, 16)
 888  DEF_ASMREAD(read_nop32, 32)
 889  DEF_ASMREAD(read_sparse, 9)
 890  DEF_ASMWRITE(asmwrite)
 891  DEF_ASMWRITE(asmwrite2)
 892  DEF_ASMCOPY(asmcopy)
 893  DEF_ASMCOPY(asmcopy2)
 894  DEF_ASMCOPY(asmcopy_c)
 895  DEF_ASMCOPY(asmcopy_c_add)
 896  DEF_ASMCOPY(asmcopy_c_reg)
 897  #endif</pre></td><td valign="top">These lines define all 17 kernels of lines 500 to 849 from the stand-in macros. The 17 include <code>k_read</code>, <code>k_write</code> and <code>k_copy</code>. <code>#endif</code> (line 897) closes the <code>#if</code> of line 491. Not compiled for CRB.</td></tr>
<tr><td colspan="2"><b>Kernels added by the version bwx10: the comment</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 898  /* bwx10+ */
 899
 900  /*
 901   * Kernels of round 3. They stand after every kernel of bwx8, so those keep
 902   * their place. Each one is a read kernel (T_READ) with the loop start at 20
 903   * modulo 64, the loop offset of asmread in the accepted build.
 904   *
 905   * read_pf256, read_pf512, read_pf1024, read_pf2048 have the frame of asmread
 906   * (d8-d15 are saved), so HEAD is 20 and the pad is the pad of asmread.
 907   * read_1pl names v0-v3 only, so gcc saves nothing: HEAD is 4, as read_sparse
 908   * has it. HEAD_read_1pl is a guess until the listing of the CRB build
 909   * confirms it (check_listing10.py checks the loop offset).
 910   */</pre></td><td valign="top"><ul><li><code>/* bwx10+ */</code> opens the text that the version bwx10 added. <code>/* bwx10- */</code> (line 1040) closes it.</li><li>"Round 3" in this comment is a step of the earlier investigation of 2026-11-15 (file comment, lines 61 to 83). It is not a round of <code>--rounds</code>.</li><li>The new kernels stand after the older ones. The comment gives the reason: the older kernels keep their place in the binary.</li><li>The planned loop start of every new kernel is 20 modulo 64, the loop offset of <code>asmread</code>.</li><li>The four read_pf kernels (<code>read_pf256</code> to <code>read_pf2048</code>, lines 979 to 982) save d8 to d15, as <code>asmread</code> does. So 20 bytes of code stand before their loop, and they take the pad of <code>asmread</code>.</li><li><code>read_1pl</code> saves nothing. So 4 bytes of code stand before its loop. The comment calls this number a guess. The listing of the CRB build confirms it (row of lines 923 to 930).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 911  #ifndef PAD_read_pf256
 912  #define PAD_read_pf256 PAD_asmread
 913  #endif
 914  #ifndef PAD_read_pf512
 915  #define PAD_read_pf512 PAD_asmread
 916  #endif
 917  #ifndef PAD_read_pf1024
 918  #define PAD_read_pf1024 PAD_asmread
 919  #endif
 920  #ifndef PAD_read_pf2048
 921  #define PAD_read_pf2048 PAD_asmread
 922  #endif</pre></td><td valign="top"><ul><li>The pads of the four read_pf kernels. Each one takes <code>PAD_asmread</code>, which is 0.</li><li><code>#ifndef</code> lets a <code>-D</code> option of the compiler give another value. The CRB build has no <code>-D</code> option [Ref2].</li><li>The test does not run these kernels.</li></ul></td></tr>
<tr><td colspan="2"><b>Placement of <code>read_1pl</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 923  #define LOOP_read_1pl 20
 924  #ifndef HEAD_read_1pl
 925  #define HEAD_read_1pl 4
 926  #endif
 927  #ifndef PAD_read_1pl
 928  #define PAD_read_1pl PADOF(LOOP_read_1pl, HEAD_read_1pl)
 929  #endif
 930</pre></td><td valign="top"><ul><li><code>LOOP_read_1pl</code> is 20: the planned address of the loop start, modulo 64.</li><li><code>HEAD_read_1pl</code> is 4: the number of bytes between the function start and the loop start. That is one instruction of 4 bytes.</li><li><code>PAD_read_1pl</code> is <code>PADOF(20, 4)</code>. <code>PADOF</code> (line 164) computes (20 - 4) modulo 64, which is 16.</li><li><code>PLACE(read_1pl)</code> (line 987) uses this pad. So the function starts at 16 modulo 64.</li><li>Listing of the CRB build: <code>k_read_1pl</code> starts at 0x55d0, which is 16 modulo 64. Its loop starts at 0x55d4, which is 20 modulo 64 [Ref1].</li><li>So <code>read_1pl</code> has the same loop offset as <code>asmread</code>, <code>read_nop96</code> and <code>read_nop256</code>: 20.</li></ul></td></tr>
<tr><td colspan="2"><b>Macro <code>DEF_READ_PF</code>: asmread with prefetches (not run by the test)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 931  #if defined(__aarch64__)
 932  /*
 933   * DEF_READ_PF(name, d0, d1, d2, d3): the loop of asmread (8 ldp of q
 934   * registers per 256 B, same registers, same clobbers) plus four software
 935   * prefetches per iteration, one per 64 B line, after the 8 ldp and before the
 936   * add. d0 is the prefetch distance D in bytes ahead of the block that the
 937   * iteration loads. d1, d2, d3 are D + 64, D + 128, D + 192.
 938   *
 939   * prfm pldl1keep asks for the line in the first-level data cache (PLD: for a
 940   * load, L1: first level, KEEP: normal, not streaming). The form
 941   * [base, #offset] needs an offset that is a multiple of 8 from 0 to 32760.
 942   * In the last iterations of a pass the prefetch address lies past the end of
 943   * the range, and for the last range of the buffer past the end of the
 944   * buffer. That is allowed: prfm never faults, not even on an address that is
 945   * not mapped. It reads no data, so the kernel touches the same bytes as
 946   * asmread.
 947   */</pre></td><td valign="top"><ul><li><code>#if defined(__aarch64__)</code> (line 931) opens a second block of AArch64 kernels. Its <code>#else</code> is at line 1005. The CRB binary holds this first branch: the listing shows the <code>prfm</code> and <code>ldr</code> instructions of its kernels [Ref1].</li><li>The comment describes the read_pf kernels: the asmread loop plus four prefetch instructions per loop pass, one per 64 B line. A line here is a block of 64 B of memory (a cache line).</li><li>A prefetch instruction (<code>prfm pldl1keep</code>) asks the CPU to bring a 64 B line into the first-level data cache. It loads no data into a register.</li><li><code>d0</code> is the byte offset of the first prefetched 64 B line from the start of the block that the loop pass loads.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 948  #define DEF_READ_PF(name, d0, d1, d2, d3) \
 949      _Static_assert((d0) % 8 == 0 &amp;&amp; (d0) &gt;= 0 &amp;&amp; (d1) == (d0) + 64 &amp;&amp; (d2) == (d0) + 128 &amp;&amp; (d3) == (d0) + 192 &amp;&amp; \
 950                     (d3) &lt;= 32760, "prfm offsets: multiples of 8 from 0 to 32760, one per 64 B line"); \
 951      PLACE(name); \
 952      __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \
 953      { \
 954          const uint64_t *p = a; \
 955          const uint64_t *end = a + n; \
 956          __asm__ volatile( \
 957              "1:\n\t" \
 958              "ldp q0, q1, [%[p]]\n\t" \
 959              "ldp q2, q3, [%[p], #32]\n\t" \
 960              "ldp q4, q5, [%[p], #64]\n\t" \
 961              "ldp q6, q7, [%[p], #96]\n\t" \
 962              "ldp q8, q9, [%[p], #128]\n\t" \
 963              "ldp q10, q11, [%[p], #160]\n\t" \
 964              "ldp q12, q13, [%[p], #192]\n\t" \
 965              "ldp q14, q15, [%[p], #224]\n\t" \
 966              "prfm pldl1keep, [%[p], #" #d0 "]\n\t" \
 967              "prfm pldl1keep, [%[p], #" #d1 "]\n\t" \
 968              "prfm pldl1keep, [%[p], #" #d2 "]\n\t" \
 969              "prfm pldl1keep, [%[p], #" #d3 "]\n\t" \
 970              "add %[p], %[p], #256\n\t" \
 971              "cmp %[p], %[end]\n\t" \
 972              "b.lo 1b\n\t" \
 973              : [p] "+r"(p) \
 974              : [end] "r"(end) \
 975              : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \
 976                "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \
 977                "memory", "cc"); \
 978      }
 979  DEF_READ_PF(read_pf256, 256, 320, 384, 448)
 980  DEF_READ_PF(read_pf512, 512, 576, 640, 704)
 981  DEF_READ_PF(read_pf1024, 1024, 1088, 1152, 1216)
 982  DEF_READ_PF(read_pf2048, 2048, 2112, 2176, 2240)
 983</pre></td><td valign="top"><ul><li>The macro is the text of <code>DEF_ASMREAD</code> with four <code>prfm</code> instructions in place of the <code>nop</code> line.</li><li><code>_Static_assert</code> stops the compilation when the four offsets break the rule of the comment.</li><li>Lines 979 to 982 define <code>read_pf256</code>, <code>read_pf512</code>, <code>read_pf1024</code> and <code>read_pf2048</code>. The number in the name is <code>d0</code> in bytes.</li><li>The whole-chip test of 2026-11-17 runs none of these four kernels [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_read_1pl</code>: one 16 B load per 64 B line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 984  /* read_1pl, "one load per line". Per 256 B: four loads of 16 B, one at the
 985   * start of each 64 B line, then add, cmp, b.lo. It reads bytes 0 to 15 of
 986   * every line and no other byte. */
 987  PLACE(read_1pl);
 988  __attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)</pre></td><td valign="top"><ul><li>Defines the kernel <code>read_1pl</code>. The test runs it at position 4, the last position, in part L and control I. Part C does not run it [Ref4].</li><li>The name means one load per line. Here a line is a block of 64 B of memory (a cache line).</li><li><code>PLACE(read_1pl)</code> adds a pad of 16 bytes (line 928). The function starts at 16 modulo 64 [Ref1].</li><li><code>a</code> is the start of the range. <code>n</code> is its length in 8-byte words. The function returns nothing. <code>noinline</code> forbids gcc to merge it into its caller.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 989  {
 990      const uint64_t *p = a;
 991      const uint64_t *end = a + n;</pre></td><td valign="top"><code>p</code> is the read pointer. <code>end</code> is the first address after the range. Machine code: <code>add x1, x0, x1, lsl #3</code>. It is the only instruction before the loop [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 992      __asm__ volatile(
 993          "1:\n\t"</pre></td><td valign="top">The loop is assembler text, as in <code>DEF_ASMREAD</code> (line 622). <code>1:</code> is the label at the start of the loop. In the CRB binary the loop starts at an address of 20 modulo 64 [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 994          "ldr q0, [%[p]]\n\t"
 995          "ldr q1, [%[p], #64]\n\t"
 996          "ldr q2, [%[p], #128]\n\t"
 997          "ldr q3, [%[p], #192]\n\t"</pre></td><td valign="top"><ul><li>Each <code>ldr q</code> loads 16 B from memory into one vector register. The four loads read at the byte offsets 0, 64, 128 and 192 of the current block of 256 B.</li><li>So one loop pass loads 64 B of its block of 256 B: the bytes 0 to 15 of each 64 B line. It does not load the other 48 B of a 64 B line.</li><li><code>asmread</code> has 8 load instructions of 32 B per loop pass. This kernel has 4 load instructions of 16 B per loop pass.</li><li>Nothing uses the loaded values. No instruction of the loop takes q0 to q3 as an input.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 998          "add %[p], %[p], #256\n\t"
 999          "cmp %[p], %[end]\n\t"
1000          "b.lo 1b\n\t"</pre></td><td valign="top"><ul><li><code>add</code> moves the read pointer forward by 256 B. <code>cmp</code> and <code>b.lo 1b</code> repeat the loop while the pointer is below <code>end</code>.</li><li>Machine code of one loop pass: 4 <code>ldr</code>, <code>add x0, x0, #0x100</code>, <code>cmp x0, x1</code> and <code>b.cc</code>. That is 7 instructions per block of 256 B [Ref1].</li><li>The worker counts the bytes outside the kernel. It adds the full chunk size, 2097152 B, for each call (line 1696).</li><li>So the rate of <code>read_1pl</code> counts 256 B per loop pass, although the loop pass loads 64 B.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1001          : [p] "+r"(p)
1002          : [end] "r"(end)
1003          : "v0", "v1", "v2", "v3", "memory", "cc");
1004  }</pre></td><td valign="top"><ul><li><code>p</code> is read and changed. <code>end</code> is an input.</li><li>Of the vector registers, the clobber list names only v0 to v3. The calling rules do not require a function to keep these registers. So gcc saves nothing.</li><li>The whole function has 9 instructions: 1 before the loop, 7 in the loop, then <code>ret</code> [Ref1].</li><li><code>asmread</code> differs here: it saves d8 to d15 and loads them back at each call.</li></ul></td></tr>
<tr><td colspan="2"><b>Stand-ins of the bwx10 kernels (not in the CRB binary)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1005  #else
1006  /* Stand-ins. A prefetch touches no byte, so the stand-in of a read_pf kernel
1007   * is the stand-in of asmread. The stand-in of read_1pl reads the first two
1008   * words (16 B) of every 64 B line, as the real kernel does. */
1009  DEF_ASMREAD(read_pf256, 0)
1010  DEF_ASMREAD(read_pf512, 0)
1011  DEF_ASMREAD(read_pf1024, 0)
1012  DEF_ASMREAD(read_pf2048, 0)
1013  PLACE(read_1pl);
1014  __attribute__((noinline)) static void k_read_1pl(const uint64_t *a, size_t n)
1015  {
1016      const volatile uint64_t *p = a;
1017      for (size_t i = 0; i &lt; n; i += 8) {
1018          (void)p[i];
1019          (void)p[i + 1];
1020      }
1021  }
1022  #endif
1023</pre></td><td valign="top"><ul><li><code>#else</code> of the <code>#if</code> of line 931. The compiler reads these lines only for a machine that is not AArch64.</li><li>The four read_pf kernels become the stand-in loop of <code>asmread</code>.</li><li>The stand-in of <code>read_1pl</code> reads the first two words (16 B) of every 8 words (64 B).</li><li><code>#endif</code> (line 1022) closes the block. The CRB binary does not hold this code [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Pad after the kernels of bwx10</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1024  /*
1025   * Placement of the code after the kernels. In the accepted build of bwx8 the
1026   * last kernel ends at 0x4a14 (ref-bwx8/listing.txt), so the function after
1027   * the kernels starts at 0x4a18: 24 modulo 64. That function is call(), or
1028   * read_smaps() if gcc inlines every call of call(). The pad below gives it
1029   * the same start modulo 64 in bwx10. No code is added between call() and the
1030   * end of timed_sequence(), so that code keeps the placement modulo 64 that it
1031   * has in bwx8. build10.sh prints the placement of both binaries.
1032   * The value 24 holds for the AArch64 build with the accepted compiler. On
1033   * another machine it is only a pad: test_runner10.py builds one copy with the
1034   * local value to check the method.
1035   */</pre></td><td valign="top"><ul><li>This comment explains the lines 1036 to 1039. They place the code that follows the kernels.</li><li>Aim: the first function after the kernels starts at 24 modulo 64, as in the older runner bwx8. That function is <code>call</code>, or <code>read_smaps</code> when gcc merges <code>call</code> into its callers.</li><li>In bwx12 more kernels follow this pad (from line 1043 on). So this pad does not stand directly before <code>call</code> any more. A later pad with the same value does that (lines 1446 to 1449).</li><li>The build record of CRB reports <code>call=24</code>: the function <code>call</code> starts at 24 modulo 64 [Ref2].</li><li><code>timed_sequence</code> in the comment is a function of the trial mode. The test does not use the trial mode.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1036  #ifndef PAD_after_kernels
1037  #define PAD_after_kernels 24
1038  #endif
1039  PLACE(after_kernels);
1040  /* bwx10- */
1041  /* bwx11+ */
1042</pre></td><td valign="top"><ul><li><code>PAD_after_kernels</code> is 24. A <code>-D</code> option could give another value, and the CRB build has none [Ref2].</li><li><code>PLACE(after_kernels)</code> fills the code up to a multiple of 64 bytes and then adds 24 bytes of value 0.</li><li><code>/* bwx10- */</code> closes the text of the version bwx10.</li><li><code>/* bwx11+ */</code> opens the text that the version bwx11 added. That text starts after line 1042 with the kernels <code>read_nop64</code>, <code>read_nop96</code> and <code>read_nop128</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Kernels added by bwx11: <code>read_nop64</code>, <code>read_nop96</code>, <code>read_nop128</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1043  /*
1044   * Kernels of round 4. They stand after every kernel of bwx10, so those keep
1045   * their place. Each one is the asmread loop with more nop instructions
1046   * between the 8 ldp and the add: 64, 96 and 128. The frame is the frame of
1047   * asmread (d8-d15 are saved), so the pad is the pad of asmread and the loop
1048   * starts at 20 modulo 64 (check_listing11.py checks it). DEF_ASMREAD is the
1049   * macro of the kernels of bwx8: the asm text on AArch64, the stand-in loop on
1050   * another machine. A nop touches no byte, so the stand-in is the stand-in of
1051   * asmread.
1052   */</pre></td><td valign="top"><ul><li>The comment introduces three kernels that the version bwx11 added. Each one is the asmread loop with 64, 96 or 128 <code>nop</code> instructions between the 8 loads and the <code>add</code> of the read address.</li><li>"Round 4" is the work step of 2026-11-15 that produced bwx11 (line 36). It is not a round of <code>--rounds</code>.</li><li>The three kernels stand after all older kernels in the source. The comment gives the reason: the older kernels keep their place in the binary.</li><li>Each function saves d8 to d15 before its loop, as <code>k_asmread</code> does. So it gets the pad of asmread, and its loop starts at 20 modulo 64 [Ref1].</li><li>Of these three kernels the whole-chip test runs only <code>read_nop96</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1053  #ifndef PAD_read_nop64
1054  #define PAD_read_nop64 PAD_asmread
1055  #endif
1056  #ifndef PAD_read_nop96
1057  #define PAD_read_nop96 PAD_asmread
1058  #endif
1059  #ifndef PAD_read_nop128
1060  #define PAD_read_nop128 PAD_asmread
1061  #endif</pre></td><td valign="top"><ul><li>Default pads of the three kernels. Each name gets the value of <code>PAD_asmread</code>, unless the build sets another value with a <code>-D</code> option.</li><li><code>PAD_asmread</code> is 0 (line 214). The CRB build has no <code>-D</code> option [Ref2].</li><li>So <code>PLACE</code> (line 163) lets each of the three functions start on a 64 B boundary.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1062  DEF_ASMREAD(read_nop64, 64)</pre></td><td valign="top">Creates the kernel <code>read_nop64</code> from the macro <code>DEF_ASMREAD</code>: the asmread loop with 64 <code>nop</code> instructions per 256 B. The whole-chip test of 2026-11-17 does not run it.</td></tr>
<tr><td colspan="2"><b>Kernel <code>read_nop96</code>: function <code>k_read_nop96</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1063  DEF_ASMREAD(read_nop96, 96)</pre></td><td valign="top"><ul><li>This line creates the function <code>k_read_nop96</code> from the macro <code>DEF_ASMREAD</code> (lines 616 to 641) with the nop count 96. Part L and control I run it at position 2 of the sequence. Part C does not run it [Ref4].</li><li>The loop is assembler text that gcc does not change. gcc only chooses the registers: x0 holds the read address and x1 holds the end address [Ref1].</li><li>One loop pass reads 256 B with 8 <code>ldp</code> instructions. Each one loads 32 B into two of the registers q0 to q15, at the byte offsets 0, 32, 64, ... 224. So each byte is read once. Nothing uses the loaded values.</li><li>After the 8 loads the text <code>.rept 96</code>, <code>nop</code>, <code>.endr</code> tells the assembler to write the <code>nop</code> instruction 96 times. Then <code>add</code> moves the read address forward by 256 B. <code>cmp</code> compares it with the end address. <code>b.lo 1b</code> branches back to the first <code>ldp</code> while the read address is below the end address.</li><li>Listing [Ref1]: one loop pass is 8 <code>ldp</code>, 96 <code>nop</code>, <code>add x0, x0, #0x100</code>, <code>cmp x0, x1</code> and <code>b.cc</code>. That is 107 instructions (428 B of code) per 256 B of data. The listing prints the branch as <code>b.cc</code> and names <code>b.lo</code> as another name of the same instruction. The function starts at address 0x57c0 (0 modulo 64) and the loop at 0x57d4 (20 modulo 64), the loop offset of <code>k_asmread</code>.</li><li>Outside the loop, once per call: 4 <code>stp</code> instructions save d8 to d15 on the stack, one <code>add</code> computes the end address, 4 <code>ldp</code> instructions load d8 to d15 back, and <code>ret</code> returns. In a timed interval of the test one call covers one 2 MiB chunk. That is 8192 loop passes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1064  DEF_ASMREAD(read_nop128, 128)</pre></td><td valign="top">Creates the kernel <code>read_nop128</code>: the asmread loop with 128 <code>nop</code> instructions per 256 B. The whole-chip test of 2026-11-17 does not run it.</td></tr>
<tr><td colspan="2"><b>Second pad after the kernels</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1065
1066  /*
1067   * The pad after the kernels, once more. The pad of bwx10 above now stands
1068   * before the kernels of round 4, so it no longer places call(). This pad has
1069   * the same value, and the function after the kernels starts at that value
1070   * modulo 64, as in bwx10 and in bwx8. build11.sh prints the placement.
1071   */
1072  #ifndef PAD_after_kernels11
1073  #define PAD_after_kernels11 PAD_after_kernels
1074  #endif
1075  PLACE(after_kernels11);
1076  /* bwx11- */
1077  /* bwx12+ */
1078</pre></td><td valign="top"><ul><li><code>PAD_after_kernels11</code> gets the value of <code>PAD_after_kernels</code>: 24 (line 1037).</li><li><code>PLACE(after_kernels11)</code> pads the code up to a 64 B boundary and then adds 24 bytes of value 0.</li><li>In bwx11 this pad set the start address of the function that follows the kernels. In bwx12 more kernels follow here, and the pad of line 1449 sets that start address.</li><li>Lines 1076 and 1077 are markers. The text that bwx11 added ends here, and the text that bwx12 added starts.</li></ul></td></tr>
<tr><td colspan="2"><b>Kernels added by bwx12: where each loop starts</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1079  /*
1080   * Kernels of round 5. They stand after every kernel of bwx11, so those keep
1081   * their place. The pad of each one puts the loop start at the loop offset
1082   * modulo 64 of its original in the accepted build: 20 for a read kernel (the
1083   * offset of asmread), 40 for a write kernel (asmwrite), 52 for a copy kernel
1084   * (asmcopy). PAD = (LOOP - HEAD) mod 64, where HEAD is the number of bytes
1085   * between the function start and the loop start. Every HEAD below is a guess
1086   * until the listing of the CRB build confirms it (check_listing12.py checks
1087   * the loop offset). Override one with -DHEAD_&lt;group&gt;=N or -DPAD_&lt;name&gt;=N.
1088   *
1089   *   read_nopN       frame of asmread (gcc saves d8-d15): HEAD 20, pad of asmread.
1090   *   read_daddK      frame of asmread, then 8 movi: HEAD 20 + 32 = 52.
1091   *   read_iadd16     frame of asmread, then 16 movi: HEAD 20 + 64 = 84.
1092   *   read_spN        no frame, as read_sparse: HEAD 4. read_sparse itself has
1093   *                   its loop at 4 modulo 64 (pad of asmread, HEAD 4). The new
1094   *                   kernels get 20, the offset of asmread.
1095   *                   -DHEAD_read_sp=20 gives them the offset of read_sparse.
1096   *   read_1pl_nop96  no frame, as read_1pl: HEAD 4, pad of read_1pl.
1097   *   write_nopN      as asmwrite (end pointer, dup): pad of asmwrite.
1098   *   copy_nopN       frame of asmcopy: pad of asmcopy.
1099   */</pre></td><td valign="top"><ul><li>The comment gives the placement rule for the 26 kernels that bwx12 added. "Round 5" is the work step of 2026-11-15 that produced bwx12 (line 3).</li><li>Aim: the loop of each new kernel starts at a planned address modulo 64. That is 20 B for a read kernel (the loop offset of asmread), 40 B for a write kernel (the loop offset of asmwrite) and 52 B for a copy kernel (the loop offset of asmcopy).</li><li>Rule: pad = (LOOP - HEAD) modulo 64. LOOP is the planned loop offset. HEAD is the number of bytes of code between the function start and the loop start.</li><li>The listing of the CRB binary shows the planned loop offset for each of the 26 kernels [Ref1].</li><li>Of these 26 kernels the whole-chip test runs only <code>read_nop256</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1100  #define LOOP_read12 20
1101  #ifndef HEAD_read_dadd
1102  #define HEAD_read_dadd 52
1103  #endif
1104  #ifndef HEAD_read_iadd
1105  #define HEAD_read_iadd 84
1106  #endif
1107  #ifndef HEAD_read_sp
1108  #define HEAD_read_sp 4
1109  #endif</pre></td><td valign="top"><code>LOOP_read12</code> is the planned loop offset of the new read kernels: 20 B. The three <code>HEAD</code> values are the bytes of code before the loop: 52 B for the <code>read_dadd</code> kernels, 84 B for <code>read_iadd16</code> and 4 B for the <code>read_sp</code> kernels. The listing of the CRB binary shows these three distances [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1110  #ifndef PAD_read_nop48
1111  #define PAD_read_nop48 PAD_asmread
1112  #endif
1113  #ifndef PAD_read_nop56
1114  #define PAD_read_nop56 PAD_asmread
1115  #endif
1116  #ifndef PAD_read_nop72
1117  #define PAD_read_nop72 PAD_asmread
1118  #endif
1119  #ifndef PAD_read_nop80
1120  #define PAD_read_nop80 PAD_asmread
1121  #endif
1122  #ifndef PAD_read_nop88
1123  #define PAD_read_nop88 PAD_asmread
1124  #endif
1125  #ifndef PAD_read_nop112
1126  #define PAD_read_nop112 PAD_asmread
1127  #endif
1128  #ifndef PAD_read_nop160
1129  #define PAD_read_nop160 PAD_asmread
1130  #endif
1131  #ifndef PAD_read_nop192
1132  #define PAD_read_nop192 PAD_asmread
1133  #endif</pre></td><td valign="top">Default pads of 8 new <code>read_nop</code> kernels: the value of <code>PAD_asmread</code>, 0. The whole-chip test runs none of these 8 kernels.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1134  #ifndef PAD_read_nop256
1135  #define PAD_read_nop256 PAD_asmread
1136  #endif</pre></td><td valign="top"><code>PAD_read_nop256</code> gets the same value 0. So <code>k_read_nop256</code>, a kernel of the test, starts on a 64 B boundary. The listing shows the start address 0x6cc0. That is 0 modulo 64 [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1137  #ifndef PAD_read_dadd2
1138  #define PAD_read_dadd2 PADOF(LOOP_read12, HEAD_read_dadd)
1139  #endif
1140  #ifndef PAD_read_dadd4
1141  #define PAD_read_dadd4 PADOF(LOOP_read12, HEAD_read_dadd)
1142  #endif
1143  #ifndef PAD_read_dadd8
1144  #define PAD_read_dadd8 PADOF(LOOP_read12, HEAD_read_dadd)
1145  #endif
1146  #ifndef PAD_read_dadd16
1147  #define PAD_read_dadd16 PADOF(LOOP_read12, HEAD_read_dadd)
1148  #endif
1149  #ifndef PAD_read_iadd16
1150  #define PAD_read_iadd16 PADOF(LOOP_read12, HEAD_read_iadd)
1151  #endif
1152  #ifndef PAD_read_sp24
1153  #define PAD_read_sp24 PADOF(LOOP_read12, HEAD_read_sp)
1154  #endif
1155  #ifndef PAD_read_sp32
1156  #define PAD_read_sp32 PADOF(LOOP_read12, HEAD_read_sp)
1157  #endif
1158  #ifndef PAD_read_sp40
1159  #define PAD_read_sp40 PADOF(LOOP_read12, HEAD_read_sp)
1160  #endif
1161  #ifndef PAD_read_sp48
1162  #define PAD_read_sp48 PADOF(LOOP_read12, HEAD_read_sp)
1163  #endif
1164  #ifndef PAD_read_sp56
1165  #define PAD_read_sp56 PADOF(LOOP_read12, HEAD_read_sp)
1166  #endif</pre></td><td valign="top">Default pads of 10 kernels that the whole-chip test does not run. <code>PADOF(loop, head)</code> (line 164) computes (loop - head) modulo 64. The results are 32 B for the four <code>read_dadd</code> kernels, 0 B for <code>read_iadd16</code> and 16 B for the five <code>read_sp</code> kernels.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1167  #ifndef PAD_read_1pl_nop96
1168  #define PAD_read_1pl_nop96 PAD_read_1pl
1169  #endif
1170  #ifndef PAD_write_nop32
1171  #define PAD_write_nop32 PAD_asmwrite
1172  #endif
1173  #ifndef PAD_write_nop96
1174  #define PAD_write_nop96 PAD_asmwrite
1175  #endif
1176  #ifndef PAD_write_nop128
1177  #define PAD_write_nop128 PAD_asmwrite
1178  #endif
1179  #ifndef PAD_write_nop256
1180  #define PAD_write_nop256 PAD_asmwrite
1181  #endif
1182  #ifndef PAD_copy_nop96
1183  #define PAD_copy_nop96 PAD_asmcopy
1184  #endif
1185  #ifndef PAD_copy_nop192
1186  #define PAD_copy_nop192 PAD_asmcopy
1187  #endif
1188</pre></td><td valign="top">Default pads of 7 more kernels that the whole-chip test does not run. <code>read_1pl_nop96</code> takes the pad of <code>read_1pl</code> (16 B). The four <code>write_nop</code> kernels take the pad of <code>asmwrite</code> (32 B). The two <code>copy_nop</code> kernels take the pad of <code>asmcopy</code> (32 B).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1189  /* DEF_ASMREAD is the macro of the kernels of bwx8: the asm text on AArch64,
1190   * the stand-in loop on another machine. */
1191  DEF_ASMREAD(read_nop48, 48)
1192  DEF_ASMREAD(read_nop56, 56)
1193  DEF_ASMREAD(read_nop72, 72)
1194  DEF_ASMREAD(read_nop80, 80)
1195  DEF_ASMREAD(read_nop88, 88)
1196  DEF_ASMREAD(read_nop112, 112)
1197  DEF_ASMREAD(read_nop160, 160)
1198  DEF_ASMREAD(read_nop192, 192)</pre></td><td valign="top">Creates 8 kernels from the macro <code>DEF_ASMREAD</code> (lines 616 to 641): the asmread loop with 48, 56, 72, 80, 88, 112, 160 or 192 <code>nop</code> instructions per 256 B. The whole-chip test of 2026-11-17 runs none of them.</td></tr>
<tr><td colspan="2"><b>Kernel <code>read_nop256</code>: function <code>k_read_nop256</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1199  DEF_ASMREAD(read_nop256, 256)</pre></td><td valign="top"><ul><li>This line creates the function <code>k_read_nop256</code> from the macro <code>DEF_ASMREAD</code> (lines 616 to 641) with the nop count 256. Part L and control I run it at position 3 of the sequence. Part C does not run it [Ref4].</li><li>The loop is the loop of <code>k_read_nop96</code> (line 1063) with 256 <code>nop</code> instructions in place of 96. gcc does not change the assembler text. x0 holds the read address and x1 holds the end address [Ref1].</li><li>One loop pass reads 256 B with 8 <code>ldp</code> instructions of 32 B each, at the byte offsets 0, 32, 64, ... 224. So each byte is read once. Nothing uses the loaded values.</li><li>Listing [Ref1]: one loop pass is 8 <code>ldp</code>, 256 <code>nop</code>, <code>add x0, x0, #0x100</code>, <code>cmp x0, x1</code> and the branch <code>b.cc</code> (another name of <code>b.lo</code>). That is 267 instructions (1068 B of code) per 256 B of data.</li><li>The function starts at address 0x6cc0 (0 modulo 64). The loop starts at 0x6cd4 (20 modulo 64), the loop offset of <code>k_asmread</code>.</li><li>Outside the loop, once per call: 4 <code>stp</code> instructions save d8 to d15 on the stack, one <code>add</code> computes the end address, 4 <code>ldp</code> instructions load d8 to d15 back, and <code>ret</code> returns. In a timed interval of the test one call covers one 2 MiB chunk. That is 8192 loop passes.</li></ul></td></tr>
<tr><td colspan="2"><b>AArch64 branch of the other bwx12 kernels</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1200
1201  #if defined(__aarch64__)</pre></td><td valign="top"><code>#if defined(__aarch64__)</code>: lines 1202 to 1405 are compiled only for AArch64. The CRB binary holds this branch. Proof: the listing holds <code>k_read_dadd2</code> with the <code>movi</code> and vector <code>add</code> instructions of line 1273 [Ref1]. The whole-chip test runs no kernel of this branch.</td></tr>
<tr><td colspan="2"><b><code>read_dadd</code> kernels and <code>read_iadd16</code>: not run by the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1202  /*
1203   * DEF_READ_ADD(name, init, adds): the loop of asmread (8 ldp of q registers
1204   * per 256 B, same registers) with the text "adds" after the 8 ldp and before
1205   * the add of the pointer. "init" runs once per call, before the loop.
1206   * v16-v31 are caller-saved in AAPCS64, so gcc saves nothing for them. v8-v15
1207   * are named as clobbers, so gcc saves d8-d15 once per call, as in asmread.
1208   *
1209   * ACC_ZERO sets the accumulators v16-v23 to 0. CONST_ONE sets v24-v31 to the
1210   * value 1 in every 32-bit lane.
1211   * VADD(a, b) is "add va.2d, va.2d, vb.2d": two 64-bit adds, the instruction
1212   * of the old read loop (listing of k_oldread).
1213   *
1214   * read_daddK: every add takes a register that the 8 ldp of this iteration
1215   * loaded. So the add waits for the load data, and it stays in the
1216   * out-of-order window (the instructions that the core has issued and not yet
1217   * retired) until the data arrives.
1218   *   K = 16: v0 to v15, two per accumulator. 8 adds per 128 B, as oldread has.
1219   *   K = 8:  v0, v2, ..., v14, one per accumulator.
1220   *   K = 4:  v0, v4, v8, v12 into v16-v19.
1221   *   K = 2:  v0, v8 into v16, v17.
1222   * read_iadd16: 16 adds of v24-v31 to v16-v23. No add takes a loaded
1223   * register. Same instruction count and same add instruction as read_dadd16.
1224   */</pre></td><td valign="top"><ul><li>The comment describes the macro <code>DEF_READ_ADD</code> and the five kernels that are built from it. Each one is the asmread loop with vector adds between the 8 loads and the <code>add</code> of the read address.</li><li>In a <code>read_daddK</code> kernel each of the K adds takes one register that the loads of the same loop pass filled. The other input is one of the sum registers v16 to v23.</li><li>In <code>read_iadd16</code> the 16 adds take the constants in v24 to v31 and no loaded register.</li><li>The whole-chip test of 2026-11-17 runs none of them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1225  #define ACC_ZERO \
1226      "movi v16.4s, #0\n\t" \
1227      "movi v17.4s, #0\n\t" \
1228      "movi v18.4s, #0\n\t" \
1229      "movi v19.4s, #0\n\t" \
1230      "movi v20.4s, #0\n\t" \
1231      "movi v21.4s, #0\n\t" \
1232      "movi v22.4s, #0\n\t" \
1233      "movi v23.4s, #0\n\t"
1234  #define CONST_ONE \
1235      "movi v24.4s, #1\n\t" \
1236      "movi v25.4s, #1\n\t" \
1237      "movi v26.4s, #1\n\t" \
1238      "movi v27.4s, #1\n\t" \
1239      "movi v28.4s, #1\n\t" \
1240      "movi v29.4s, #1\n\t" \
1241      "movi v30.4s, #1\n\t" \
1242      "movi v31.4s, #1\n\t"
1243  #define VADD(a, b) "add v" #a ".2d, v" #a ".2d, v" #b ".2d\n\t"</pre></td><td valign="top">Three pieces of assembler text for the macro below.<ul><li><code>ACC_ZERO</code>: 8 <code>movi</code> instructions that set the sum registers v16 to v23 to 0. <code>movi</code> is the Arm instruction that writes a constant into a vector register.</li><li><code>CONST_ONE</code>: 8 <code>movi</code> instructions that set each 32-bit part of v24 to v31 to 1.</li><li><code>VADD(a, b)</code>: the instruction <code>add va.2d, va.2d, vb.2d</code>. It adds register b to register a as two 64-bit numbers.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1244  #define DEF_READ_ADD(name, init, adds) \
1245      PLACE(name); \
1246      __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \
1247      { \
1248          const uint64_t *p = a; \
1249          const uint64_t *end = a + n; \
1250          __asm__ volatile( \
1251              init \
1252              "1:\n\t" \
1253              "ldp q0, q1, [%[p]]\n\t" \
1254              "ldp q2, q3, [%[p], #32]\n\t" \
1255              "ldp q4, q5, [%[p], #64]\n\t" \
1256              "ldp q6, q7, [%[p], #96]\n\t" \
1257              "ldp q8, q9, [%[p], #128]\n\t" \
1258              "ldp q10, q11, [%[p], #160]\n\t" \
1259              "ldp q12, q13, [%[p], #192]\n\t" \
1260              "ldp q14, q15, [%[p], #224]\n\t" \
1261              adds \
1262              "add %[p], %[p], #256\n\t" \
1263              "cmp %[p], %[end]\n\t" \
1264              "b.lo 1b\n\t" \
1265              : [p] "+r"(p) \
1266              : [end] "r"(end) \
1267              : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \
1268                "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \
1269                "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23", \
1270                "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31", \
1271                "memory", "cc"); \
1272      }</pre></td><td valign="top"><ul><li>The macro <code>DEF_READ_ADD(name, init, adds)</code> creates the function <code>k_&lt;name&gt;</code>.</li><li>The text <code>init</code> runs once per call, before the loop label <code>1:</code>.</li><li>One loop pass is the 8 <code>ldp</code> loads of asmread, then the text <code>adds</code>, then <code>add</code>, <code>cmp</code> and <code>b.lo</code>.</li><li>The last part of the <code>asm</code> statement names v0 to v31 as registers that the text changes. So gcc saves d8 to d15 once per call, as in <code>k_asmread</code> [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1273  DEF_READ_ADD(read_dadd2, ACC_ZERO, VADD(16, 0) VADD(17, 8))
1274  DEF_READ_ADD(read_dadd4, ACC_ZERO, VADD(16, 0) VADD(17, 4) VADD(18, 8) VADD(19, 12))
1275  DEF_READ_ADD(read_dadd8, ACC_ZERO,
1276               VADD(16, 0) VADD(17, 2) VADD(18, 4) VADD(19, 6) VADD(20, 8) VADD(21, 10) VADD(22, 12) VADD(23, 14))
1277  DEF_READ_ADD(read_dadd16, ACC_ZERO,
1278               VADD(16, 0) VADD(17, 1) VADD(18, 2) VADD(19, 3) VADD(20, 4) VADD(21, 5) VADD(22, 6) VADD(23, 7)
1279               VADD(16, 8) VADD(17, 9) VADD(18, 10) VADD(19, 11) VADD(20, 12) VADD(21, 13) VADD(22, 14) VADD(23, 15))
1280  DEF_READ_ADD(read_iadd16, ACC_ZERO CONST_ONE,
1281               VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27) VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31)
1282               VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27) VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31))
1283</pre></td><td valign="top">Creates five kernels. <code>read_dadd2</code>, <code>read_dadd4</code>, <code>read_dadd8</code> and <code>read_dadd16</code> have 2, 4, 8 and 16 vector adds of loaded registers per 256 B. <code>read_iadd16</code> has 16 vector adds of constants per 256 B. The whole-chip test of 2026-11-17 runs none of them.</td></tr>
<tr><td colspan="2"><b><code>read_sp</code> kernels: not run by the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1284  /* DEF_READ_SP(name, nops): the text of read_sparse with "nops" nop
1285   * instructions in place of 9. Per 128 B: 4 ldp, the nop, add, cmp, b.lo. */
1286  #define DEF_READ_SP(name, nops) \
1287      PLACE(name); \
1288      __attribute__((noinline)) static void k_##name(const uint64_t *a, size_t n) \
1289      { \
1290          const uint64_t *p = a; \
1291          const uint64_t *end = a + n; \
1292          __asm__ volatile( \
1293              "1:\n\t" \
1294              "ldp q0, q1, [%[p]]\n\t" \
1295              "ldp q2, q3, [%[p], #32]\n\t" \
1296              "ldp q4, q5, [%[p], #64]\n\t" \
1297              "ldp q6, q7, [%[p], #96]\n\t" \
1298              ".rept " #nops "\n\tnop\n\t.endr\n\t" \
1299              "add %[p], %[p], #128\n\t" \
1300              "cmp %[p], %[end]\n\t" \
1301              "b.lo 1b\n\t" \
1302              : [p] "+r"(p) \
1303              : [end] "r"(end) \
1304              : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "memory", "cc"); \
1305      }
1306  DEF_READ_SP(read_sp24, 24)
1307  DEF_READ_SP(read_sp32, 32)
1308  DEF_READ_SP(read_sp40, 40)
1309  DEF_READ_SP(read_sp48, 48)
1310  DEF_READ_SP(read_sp56, 56)
1311</pre></td><td valign="top"><ul><li>The macro <code>DEF_READ_SP(name, nops)</code> creates a kernel whose loop pass reads 128 B with 4 <code>ldp</code> instructions. Then follow <code>nops</code> <code>nop</code> instructions, <code>add</code>, <code>cmp</code> and <code>b.lo</code>.</li><li>The <code>asm</code> statement names only v0 to v7 as changed. So gcc saves no register in these functions [Ref1].</li><li>Lines 1306 to 1310 create <code>read_sp24</code>, <code>read_sp32</code>, <code>read_sp40</code>, <code>read_sp48</code> and <code>read_sp56</code> with 24, 32, 40, 48 and 56 <code>nop</code>.</li><li>The whole-chip test of 2026-11-17 runs none of them.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>k_read_1pl_nop96</code>: not run by the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1312  /* read_1pl_nop96: the text of read_1pl with 96 nop after the four loads. It
1313   * reads bytes 0 to 15 of every 64 B line and no other byte. */
1314  PLACE(read_1pl_nop96);
1315  __attribute__((noinline)) static void k_read_1pl_nop96(const uint64_t *a, size_t n)
1316  {
1317      const uint64_t *p = a;
1318      const uint64_t *end = a + n;
1319      __asm__ volatile(
1320          "1:\n\t"
1321          "ldr q0, [%[p]]\n\t"
1322          "ldr q1, [%[p], #64]\n\t"
1323          "ldr q2, [%[p], #128]\n\t"
1324          "ldr q3, [%[p], #192]\n\t"
1325          ".rept 96\n\tnop\n\t.endr\n\t"
1326          "add %[p], %[p], #256\n\t"
1327          "cmp %[p], %[end]\n\t"
1328          "b.lo 1b\n\t"
1329          : [p] "+r"(p)
1330          : [end] "r"(end)
1331          : "v0", "v1", "v2", "v3", "memory", "cc");
1332  }
1333</pre></td><td valign="top"><ul><li>The kernel <code>read_1pl_nop96</code>: the loop of <code>k_read_1pl</code> (line 988) with 96 <code>nop</code> instructions after the four loads.</li><li>One loop pass walks 256 B and loads 16 B at the start of each 64 B line with <code>ldr</code>.</li><li>The whole-chip test of 2026-11-17 does not run it. The test runs <code>read_1pl</code>. That kernel has no <code>nop</code>.</li></ul></td></tr>
<tr><td colspan="2"><b><code>write_nop</code> kernels: not run by the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1334  /* DEF_ASMWRITE_NOP(name, nops): the text of DEF_ASMWRITE with "nops" nop
1335   * instructions after the 8 stp and before the add. */
1336  #define DEF_ASMWRITE_NOP(name, nops) \
1337      PLACE(name); \
1338      __attribute__((noinline)) static void k_##name(uint64_t *a, size_t n, uint64_t v) \
1339      { \
1340          uint64_t *p = a; \
1341          const uint64_t *end = a + n; \
1342          __asm__ volatile( \
1343              "dup v0.2d, %[v]\n\t" \
1344              "1:\n\t" \
1345              "stp q0, q0, [%[p]]\n\t" \
1346              "stp q0, q0, [%[p], #32]\n\t" \
1347              "stp q0, q0, [%[p], #64]\n\t" \
1348              "stp q0, q0, [%[p], #96]\n\t" \
1349              "stp q0, q0, [%[p], #128]\n\t" \
1350              "stp q0, q0, [%[p], #160]\n\t" \
1351              "stp q0, q0, [%[p], #192]\n\t" \
1352              "stp q0, q0, [%[p], #224]\n\t" \
1353              ".rept " #nops "\n\tnop\n\t.endr\n\t" \
1354              "add %[p], %[p], #256\n\t" \
1355              "cmp %[p], %[end]\n\t" \
1356              "b.lo 1b\n\t" \
1357              : [p] "+r"(p) \
1358              : [end] "r"(end), [v] "r"(v) \
1359              : "v0", "memory", "cc"); \
1360      }
1361  DEF_ASMWRITE_NOP(write_nop32, 32)
1362  DEF_ASMWRITE_NOP(write_nop96, 96)
1363  DEF_ASMWRITE_NOP(write_nop128, 128)
1364  DEF_ASMWRITE_NOP(write_nop256, 256)
1365</pre></td><td valign="top"><ul><li>The macro <code>DEF_ASMWRITE_NOP(name, nops)</code> creates a write kernel: the loop of <code>DEF_ASMWRITE</code> (line 671) with <code>nops</code> <code>nop</code> instructions after the 8 <code>stp</code> stores. One <code>stp</code> stores 32 B: the 16-byte register q0 twice.</li><li>Lines 1361 to 1364 create <code>write_nop32</code>, <code>write_nop96</code>, <code>write_nop128</code> and <code>write_nop256</code>.</li><li>The whole-chip test of 2026-11-17 runs none of them.</li></ul></td></tr>
<tr><td colspan="2"><b><code>copy_nop</code> kernels: not run by the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1366  /* DEF_ASMCOPY_NOP(name, nops): the text of DEF_ASMCOPY with "nops" nop
1367   * instructions after the 8 stp and before the two adds. */
1368  #define DEF_ASMCOPY_NOP(name, nops) \
1369      PLACE(name); \
1370      __attribute__((noinline)) static void k_##name(uint64_t *restrict d, const uint64_t *restrict s, size_t n) \
1371      { \
1372          uint64_t *dp = d; \
1373          const uint64_t *sp = s; \
1374          const uint64_t *end = s + n; \
1375          __asm__ volatile( \
1376              "1:\n\t" \
1377              "ldp q0, q1, [%[s]]\n\t" \
1378              "ldp q2, q3, [%[s], #32]\n\t" \
1379              "ldp q4, q5, [%[s], #64]\n\t" \
1380              "ldp q6, q7, [%[s], #96]\n\t" \
1381              "ldp q8, q9, [%[s], #128]\n\t" \
1382              "ldp q10, q11, [%[s], #160]\n\t" \
1383              "ldp q12, q13, [%[s], #192]\n\t" \
1384              "ldp q14, q15, [%[s], #224]\n\t" \
1385              "stp q0, q1, [%[d]]\n\t" \
1386              "stp q2, q3, [%[d], #32]\n\t" \
1387              "stp q4, q5, [%[d], #64]\n\t" \
1388              "stp q6, q7, [%[d], #96]\n\t" \
1389              "stp q8, q9, [%[d], #128]\n\t" \
1390              "stp q10, q11, [%[d], #160]\n\t" \
1391              "stp q12, q13, [%[d], #192]\n\t" \
1392              "stp q14, q15, [%[d], #224]\n\t" \
1393              ".rept " #nops "\n\tnop\n\t.endr\n\t" \
1394              "add %[s], %[s], #256\n\t" \
1395              "add %[d], %[d], #256\n\t" \
1396              "cmp %[s], %[end]\n\t" \
1397              "b.lo 1b\n\t" \
1398              : [s] "+r"(sp), [d] "+r"(dp) \
1399              : [end] "r"(end) \
1400              : "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", \
1401                "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", \
1402                "memory", "cc"); \
1403      }</pre></td><td valign="top">The macro <code>DEF_ASMCOPY_NOP(name, nops)</code> creates a copy kernel: the loop of <code>DEF_ASMCOPY</code> (line 698) with <code>nops</code> <code>nop</code> instructions after the 8 <code>stp</code> stores and before the two <code>add</code>. One loop pass loads 256 B from the source buffer with 8 <code>ldp</code> and stores them to the destination buffer with 8 <code>stp</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1404  DEF_ASMCOPY_NOP(copy_nop96, 96)
1405  DEF_ASMCOPY_NOP(copy_nop192, 192)</pre></td><td valign="top">Creates the copy kernels <code>copy_nop96</code> and <code>copy_nop192</code>. The whole-chip test of 2026-11-17 runs neither of them.</td></tr>
<tr><td colspan="2"><b>Stand-ins of the bwx12 kernels: not in the CRB binary</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1406  #else
1407  /* Stand-ins. A nop and a vector add of registers touch no byte. So the
1408   * stand-in of a read_dadd, read_iadd or read_sp kernel is the stand-in of
1409   * asmread: these kernels read every byte of the range. The stand-in of
1410   * read_1pl_nop96 is the stand-in of read_1pl: the first two words (16 B) of
1411   * every 64 B line. The stand-ins of the write and copy kernels are the
1412   * stand-ins of asmwrite and asmcopy. */
1413  DEF_ASMREAD(read_dadd2, 0)
1414  DEF_ASMREAD(read_dadd4, 0)
1415  DEF_ASMREAD(read_dadd8, 0)
1416  DEF_ASMREAD(read_dadd16, 0)
1417  DEF_ASMREAD(read_iadd16, 0)
1418  DEF_ASMREAD(read_sp24, 24)
1419  DEF_ASMREAD(read_sp32, 32)
1420  DEF_ASMREAD(read_sp40, 40)
1421  DEF_ASMREAD(read_sp48, 48)
1422  DEF_ASMREAD(read_sp56, 56)
1423  PLACE(read_1pl_nop96);
1424  __attribute__((noinline)) static void k_read_1pl_nop96(const uint64_t *a, size_t n)
1425  {
1426      const volatile uint64_t *p = a;
1427      for (size_t i = 0; i &lt; n; i += 8) {
1428          (void)p[i];
1429          (void)p[i + 1];
1430      }
1431  }
1432  DEF_ASMWRITE(write_nop32)
1433  DEF_ASMWRITE(write_nop96)
1434  DEF_ASMWRITE(write_nop128)
1435  DEF_ASMWRITE(write_nop256)
1436  DEF_ASMCOPY(copy_nop96)
1437  DEF_ASMCOPY(copy_nop192)
1438  #endif</pre></td><td valign="top"><ul><li><code>#else</code> branch of the <code>#if</code> of line 1201. It is compiled only when the target is not AArch64.</li><li>In that case each kernel of lines 1273 to 1405 becomes a plain C loop: the stand-in macro of its original, or the loop of lines 1427 to 1430 for <code>read_1pl_nop96</code>.</li><li>The CRB binary does not hold this branch. Line 2 of every csv file of the test says <code>kernels=aarch64</code> [Ref5].</li><li>Line 1438 ends the <code>#if</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Third pad: the start address of <code>call</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1439
1440  /*
1441   * The pad after the kernels, a third time. The pad of bwx11 above now stands
1442   * before the kernels of round 5, so it no longer places call(). This pad has
1443   * the same value, and the function after the kernels starts at that value
1444   * modulo 64, as in bwx11, bwx10 and bwx8. build12.sh prints the placement.
1445   */
1446  #ifndef PAD_after_kernels12
1447  #define PAD_after_kernels12 PAD_after_kernels
1448  #endif
1449  PLACE(after_kernels12);
1450  /* bwx12- */</pre></td><td valign="top"><ul><li><code>PAD_after_kernels12</code> gets the value of <code>PAD_after_kernels</code>: 24 (line 1037).</li><li><code>PLACE(after_kernels12)</code> pads the code up to a 64 B boundary and then adds 24 bytes of value 0. So the function after it starts at 24 modulo 64.</li><li>That function is <code>call</code> (line 1491). The build record of CRB gives <code>call=24</code> for the start of <code>call</code> modulo 64 [Ref2].</li><li>The comment gives the aim: the code after the kernels keeps the placement modulo 64 that it has in bwx11, bwx10 and bwx8.</li><li>Line 1450 is a marker: the text that bwx12 added ends here.</li></ul></td></tr>
<tr><td colspan="2"><b>The kernel table <code>kernels[]</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1451
1452  /* The function is named k_&lt;name&gt;. The cast to void (*)(void) is undone by
1453   * call() according to the type. */
1454  static const struct kdef {
1455      const char *name;
1456      enum ktype type;
1457      void (*fn)(void);
1458  } kernels[] = {
1459  #define K(name, type) { #name, type, (void (*)(void))k_##name }</pre></td><td valign="top"><ul><li>Each entry is one <code>struct kdef</code>: the name of a kernel, its type and a pointer to its function.</li><li>The name is the word that <code>--seq</code> accepts. <code>parse_seq</code> (line 1750) compares each word of <code>--seq</code> with the names and stores the index of the entry that matches.</li><li>The type is one of <code>T_READ</code>, <code>T_WRITE</code>, <code>T_COPY</code> and <code>T_OLDREAD</code> (line 253). It tells <code>call</code> which arguments the function takes.</li><li>The macro <code>K(name, type)</code> writes one entry. <code>K(read, T_READ)</code> becomes <code>{ "read", T_READ, (void (*)(void))k_read }</code>.</li><li>The cast stores every function pointer as one common pointer type. <code>call</code> casts it back to the real type before it calls the function.</li><li>For each interval the worker takes the entry of the kernel from this table (line 1658) and passes it to <code>call</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1460      K(read, T_READ), K(write, T_WRITE), K(copy, T_COPY),
1461      K(asmread, T_READ), K(asmwrite, T_WRITE), K(asmcopy, T_COPY),
1462      K(oldread, T_OLDREAD), K(oldwrite, T_WRITE), K(oldcopy, T_COPY),
1463      K(asmread2, T_READ), K(asmwrite2, T_WRITE), K(asmcopy2, T_COPY), K(oldread2, T_OLDREAD),
1464      K(asmcopy_c, T_COPY), K(asmcopy_c_add, T_COPY), K(asmcopy_c_reg, T_COPY),
1465      K(read_nop4, T_READ), K(read_nop8, T_READ), K(read_nop16, T_READ), K(read_nop32, T_READ),
1466      K(read_sparse, T_READ),</pre></td><td valign="top">The 21 kernels that the older version bwx8 already had (entries 0 to 20). Three of them are kernels of the test:<ul><li><code>read</code> is entry 0, type <code>T_READ</code>: the new read kernel.</li><li><code>asmread</code> is entry 3, type <code>T_READ</code>.</li><li><code>oldread</code> is entry 6, type <code>T_OLDREAD</code>: the old read kernel.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1467  /* bwx10+ */
1468      K(read_pf256, T_READ), K(read_pf512, T_READ), K(read_pf1024, T_READ), K(read_pf2048, T_READ),
1469      K(read_1pl, T_READ),
1470  /* bwx10- */</pre></td><td valign="top">The 5 kernels that bwx10 added (entries 21 to 25). <code>read_1pl</code>, a kernel of the test, is entry 25 with the type <code>T_READ</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1471  /* bwx11+ */
1472      K(read_nop64, T_READ), K(read_nop96, T_READ), K(read_nop128, T_READ),
1473  /* bwx11- */</pre></td><td valign="top">The 3 kernels that bwx11 added (entries 26 to 28). <code>read_nop96</code>, a kernel of the test, is entry 27 with the type <code>T_READ</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1474  /* bwx12+ */
1475      K(read_nop48, T_READ), K(read_nop56, T_READ), K(read_nop72, T_READ), K(read_nop80, T_READ), K(read_nop88, T_READ),
1476      K(read_nop112, T_READ), K(read_nop160, T_READ), K(read_nop192, T_READ), K(read_nop256, T_READ),
1477      K(read_dadd2, T_READ), K(read_dadd4, T_READ), K(read_dadd8, T_READ), K(read_dadd16, T_READ), K(read_iadd16, T_READ),
1478      K(read_sp24, T_READ), K(read_sp32, T_READ), K(read_sp40, T_READ), K(read_sp48, T_READ), K(read_sp56, T_READ),
1479      K(read_1pl_nop96, T_READ),
1480      K(write_nop32, T_WRITE), K(write_nop96, T_WRITE), K(write_nop128, T_WRITE), K(write_nop256, T_WRITE),
1481      K(copy_nop96, T_COPY), K(copy_nop192, T_COPY),
1482  /* bwx12- */</pre></td><td valign="top">The 26 kernels that bwx12 added (entries 29 to 54). <code>read_nop256</code>, a kernel of the test, is entry 37 with the type <code>T_READ</code>. The test runs no other kernel of these lines.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1483  #undef K
1484  };
1485  #define K_COUNT ((int)(sizeof kernels / sizeof kernels[0]))
1486</pre></td><td valign="top"><code>K_COUNT</code> is the number of entries: the size of the table divided by the size of one entry. It is 55. The <code>--seq</code> lists of the test name 6 of the 55 kernels. The worker calls <code>k_write</code> directly for the first touch (line 1646), not through the table.</td></tr>
<tr><td colspan="2"><b>Function <code>call</code>: run one kernel on one range of a buffer</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1487  /* Runs kernel kd on len bytes at byte offset off of the thread's buffers. A
1488   * read or write kernel uses buffer a. A copy kernel reads a and writes b. The
1489   * sink of the old read kernel is on the stack of the thread, as it was in the
1490   * old pass(), so the threads do not all store to one shared cache line. */
1491  static void call(const struct kdef *kd, struct thread *t, size_t off, size_t len, uint64_t v, volatile uint64_t *sink)
1492  {</pre></td><td valign="top"><ul><li><code>kd</code> is the table entry of the kernel. <code>t</code> is the record of the calling thread. <code>off</code> and <code>len</code> give the range in bytes. <code>v</code> is the value that a write kernel stores. <code>sink</code> points to the variable that takes the sum of an old read kernel.</li><li>The worker calls this function once per interval for the warm-up pass (line 1669), and once for each 2 MiB chunk of the timed loop (line 1695).</li><li>In the timed loop the function runs between the clock reads <code>t0</code> and <code>t1</code>. So its own instructions are part of the timed interval, once per 2 MiB chunk.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1493      uint64_t *a = t-&gt;a + off / 8;
1494      size_t n = len / 8;</pre></td><td valign="top"><ul><li><code>a</code> is the address of the first word of the range. <code>t-&gt;a</code> points to 8-byte words. So <code>off / 8</code> words are <code>off</code> bytes.</li><li><code>n</code> is the length of the range in 8-byte words. One 2 MiB chunk gives 262144 words. The warm-up pass over the whole 256 MiB buffer gives 33554432 words.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1495      switch (kd-&gt;type) {
1496      case T_READ:
1497          ((read_fn)kd-&gt;fn)(a, n);
1498          break;</pre></td><td valign="top"><code>switch</code> chooses the form of the call by the type of the kernel. Case <code>T_READ</code>: the pointer is cast to the type <code>read_fn</code> (line 254), and the kernel is called with the address and the word count. It returns nothing. The kernels <code>read</code>, <code>asmread</code>, <code>read_nop96</code>, <code>read_nop256</code> and <code>read_1pl</code> of the test take this path.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1499      case T_OLDREAD:
1500          *sink = ((oldread_fn)kd-&gt;fn)(a, n);
1501          break;</pre></td><td valign="top"><ul><li>Case <code>T_OLDREAD</code>: the kernel returns its sum, and this line stores the sum to <code>*sink</code>.</li><li><code>sink</code> points to a <code>volatile</code> variable on the stack of the worker (line 1635). So the compiler must keep the store and must compute the sum. The listing of <code>k_oldread</code> holds the adds [Ref1].</li><li>The kernel <code>oldread</code> of the test takes this path.</li><li>This path has one 8-byte store per call that the <code>T_READ</code> path does not have. In the timed loop that is one store per 2 MiB chunk.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1502      case T_WRITE:
1503          ((write_fn)kd-&gt;fn)(a, n, v);
1504          break;
1505      case T_COPY:
1506          ((copy_fn)kd-&gt;fn)(t-&gt;b + off / 8, a, n);
1507          break;
1508      }
1509  }
1510</pre></td><td valign="top"><ul><li>Case <code>T_WRITE</code> passes the value <code>v</code> to a write kernel.</li><li>Case <code>T_COPY</code> calls a copy kernel that reads buffer <code>a</code> and writes buffer <code>b</code>.</li><li>No kernel in a <code>--seq</code> list of the test has one of these two types. So the two cases do not run in the test.</li><li>The function returns no value.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>read_smaps</code>: page state of the buffers</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1511  /* Page state (handoff B.6). For each of the n buffers (a NULL entry is
1512   * skipped): the entry of /proc/self/smaps whose start is the buffer and whose
1513   * end is the buffer plus buf_len(). Without such an entry both values stay -1
1514   * and are printed as NA. */
1515  static void read_smaps(struct page *pg, uint64_t *const *buf, int n)
1516  {</pre></td><td valign="top"><ul><li>For each of the <code>n</code> buffer addresses in <code>buf</code> the function looks for the mapping of that buffer in the Linux file <code>/proc/self/smaps</code>. It writes two values to <code>pg</code>: the size of the mapping and the part of it on 2 MiB pages, both in kB.</li><li>In the test <code>main</code> calls it with 240 entries, two per thread (line 3111). The 120 entries of the second buffers are NULL, and the function skips them.</li><li><code>main</code> calls it before the first interval and after each interval. During the call all workers wait at the barrier (line 1653 or line 1731). So the call is not timed.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1517      char line[256];
1518      int cur = -1;
1519      size_t len = buf_len();
1520      for (int i = 0; i &lt; n; i++)
1521          pg[i].kb_total = pg[i].kb_huge = -1;</pre></td><td valign="top"><code>len</code> is the buffer length from <code>buf_len</code> (line 426): 268435456 bytes in the test. <code>cur</code> is the index of the buffer whose mapping the loop below is reading, or -1 for no buffer. The loop of lines 1520 to 1521 sets both values of every entry to -1. The value -1 means "not found".</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1522      FILE *f = fopen("/proc/self/smaps", "r");
1523      if (!f)
1524          return;</pre></td><td valign="top">Opens <code>/proc/self/smaps</code> for reading. The file lists every memory mapping of the process. So it holds the buffers of all threads. When the file does not open, the function returns and all values stay -1.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1525      while (fgets(line, sizeof line, f)) {
1526          unsigned long s, e;
1527          char perms[8];
1528          if (sscanf(line, "%lx-%lx %7s", &amp;s, &amp;e, perms) == 3) {
1529              cur = -1;
1530              for (int i = 0; i &lt; n; i++)
1531                  if (buf[i] &amp;&amp; (unsigned long)(uintptr_t)buf[i] == s &amp;&amp; e == s + len)
1532                      cur = i;</pre></td><td valign="top"><ul><li>The loop reads the file line by line.</li><li><code>sscanf</code> returns 3 when the line starts with <code>start-end</code> (two hexadecimal addresses) and a word after them. Such a line is the first line of a mapping.</li><li>At such a line <code>cur</code> is first set back to -1 (line 1529). Then the inner loop compares the mapping with every buffer. A buffer matches when the mapping starts at the buffer address and ends exactly <code>len</code> bytes after it. Then <code>cur</code> becomes the index of that buffer.</li><li>When no buffer matches, <code>cur</code> is -1. So the lines of that mapping store nothing, and they cannot change the values of a buffer that was read before.</li><li>The comment of <code>alloc_buf</code> (lines 431 to 433) gives the reason for the exact test. No-access ranges stand before and after each buffer. So Linux lists the buffer as one mapping of its own.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1533          } else if (cur &gt;= 0) {
1534              sscanf(line, "Size: %ld kB", &amp;pg[cur].kb_total);
1535              sscanf(line, "AnonHugePages: %ld kB", &amp;pg[cur].kb_huge);
1536          }</pre></td><td valign="top"><ul><li>Every other line belongs to the mapping whose first line was read last. The branch runs only when that mapping is a buffer (<code>cur &gt;= 0</code>).</li><li>The first <code>sscanf</code> stores a number only when the line starts with <code>Size:</code>. The number is the size of the mapping in kB and goes to <code>kb_total</code>.</li><li>The second <code>sscanf</code> stores a number only when the line starts with <code>AnonHugePages:</code>. The number is the part of the mapping on 2 MiB pages in kB and goes to <code>kb_huge</code>.</li><li>All other lines store nothing.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1537      }
1538      fclose(f);
1539      for (int i = 0; i &lt; n; i++)
1540          if (pg[i].kb_total &lt; 0 || pg[i].kb_huge &lt; 0)
1541              pg[i].kb_total = pg[i].kb_huge = -1;
1542  }
1543</pre></td><td valign="top">Closes the file. If one of the two values of an entry is still below 0, both are set to -1. <code>print_p</code> (line 1570) prints a value below 0 as <code>NA</code>. In the test every P row holds 262144 kB for both values [Ref5].</td></tr>
<tr><td colspan="2"><b>Function <code>read_vmstat</code>: four counters of the whole system</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1544  /* Four counters of /proc/vmstat. They count for the whole system. -1: not found. */
1545  static void read_vmstat(long long vm[4])
1546  {
1547      static const char *name[4] = { "thp_fault_alloc", "thp_fault_fallback", "thp_collapse_alloc", "pgmigrate_success" };</pre></td><td valign="top">Reads four counters from the Linux file <code>/proc/vmstat</code> into <code>vm[0]</code> to <code>vm[3]</code>, in the order of the names in line 1547. They count for the whole system, not for one buffer. They become the last four columns of every P row.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1548      char key[64];
1549      long long val;
1550      for (int i = 0; i &lt; 4; i++)
1551          vm[i] = -1;
1552      FILE *f = fopen("/proc/vmstat", "r");
1553      if (!f)
1554          return;</pre></td><td valign="top">Sets the four values to -1. The value -1 means "not found". Then opens the file. When it does not open, the function returns with the four values at -1.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1555      while (fscanf(f, "%63s %lld", key, &amp;val) == 2)
1556          for (int i = 0; i &lt; 4; i++)
1557              if (!strcmp(key, name[i]))
1558                  vm[i] = val;
1559      fclose(f);
1560  }
1561</pre></td><td valign="top"><ul><li>Each line of the file holds a name and a number. <code>fscanf</code> reads one such pair per loop pass.</li><li>When the name equals one of the four names, the number goes to the matching place in <code>vm</code>.</li><li>The loop ends when <code>fscanf</code> finds no further pair, for example at the end of the file.</li><li>In the test <code>main</code> calls this function once before the first interval and once after each interval (line 3112). It is not timed.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>print_na</code>: one csv field, or <code>NA</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1562  static void print_na(long long v)
1563  {
1564      if (v &lt; 0)
1565          printf(",NA");
1566      else
1567          printf(",%lld", v);
1568  }
1569</pre></td><td valign="top">Prints one csv field: a comma and then the number <code>v</code>. For a negative <code>v</code> it prints <code>,NA</code>. The functions <code>read_smaps</code> (line 1515) and <code>read_vmstat</code> (line 1545) store -1 for a value that they did not find. So such a value appears as <code>NA</code> in a P row.</td></tr>
<tr><td colspan="2"><b>Function <code>print_p</code>: prints one P row</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1570  static void print_p(int round, int pos, int tid, char buffer, const struct page *pg, const long long vm[4])
1571  {</pre></td><td valign="top">Prints one P row: the page state of one buffer at one reading. In the test <code>main</code> calls it at line 3117, once per buffer after each page-state reading. <code>pg</code> holds the two page values of the buffer. <code>vm</code> holds the four vmstat counters.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1572      printf("P,%d,%d,%d,%c", round, pos, tid, buffer);</pre></td><td valign="top">Columns 1 to 5: the letter <code>P</code>, the round, the position, the thread number and the buffer letter. The position is -1 in the rows of the reading before the first interval. In all other rows it is the position of the interval that has just ended. In the test the buffer letter is always <code>a</code> [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1573      print_na(pg-&gt;kb_total);
1574      print_na(pg-&gt;kb_huge);</pre></td><td valign="top">Columns 6 and 7, <code>kB_total</code> and <code>kB_huge</code>: the size of the mapping of the buffer, and the part of it that lies on 2 MiB pages. The unit is kB of 1024 bytes. <code>read_smaps</code> (line 1515) took both values from the Linux file smaps. In the test both are 262144 kB (256 MiB) in every P row [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1575      for (int i = 0; i &lt; 4; i++)
1576          print_na(vm[i]);</pre></td><td valign="top">Columns 8 to 11: the four vmstat counters, in the order <code>thp_fault_alloc</code>, <code>thp_fault_fallback</code>, <code>thp_collapse_alloc</code>, <code>pgmigrate_success</code>. They count for the whole system, not for this buffer. <code>main</code> passes the same array <code>vm</code> for all buffers of one reading (line 3117). So all P rows of one reading hold the same four values.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1577      printf("\n");
1578  }
1579</pre></td><td valign="top">Ends the row. Example, the first P row of the file a6456.csv in the result folder of T72L1 (the first of the 3 processes of part L): <code>P,0,-1,0,a,262144,262144,611480,0,2,0</code> [Ref5]. It says: round 0, before the first interval, thread 0, buffer <code>a</code>, a mapping of 262144 kB, 262144 kB of it on 2 MiB pages.</td></tr>
<tr><td colspan="2"><b>Function <code>open_counters</code>: opens the counter group of one thread</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1580  /* Counters (handoff B.8): one group per thread, user mode only, opened by the
1581   * pinned thread for itself. An event that does not open is printed as NA. */
1582  static void open_counters(struct thread *t)
1583  {</pre></td><td valign="top">With <code>--count</code> each worker calls this function once (line 1644). At that moment the thread is pinned and has no buffer yet. The function opens one counter per entry of <code>--events</code>: 6 in the test [Ref4]. <code>t</code> is the record of the calling thread.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1584      t-&gt;group_fd = -1;
1585      t-&gt;nopen = 0;</pre></td><td valign="top">Start state: no group leader (<code>group_fd</code> is -1) and 0 open counters. The group leader is the first counter of a counter group.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1586      for (int e = 0; e &lt; cfg.nev; e++) {
1587          struct perf_event_attr a;
1588          memset(&amp;a, 0, sizeof a);</pre></td><td valign="top"><ul><li>One loop pass per event of <code>--events</code>.</li><li><code>a</code> is the structure that describes one counter to Linux.</li><li><code>memset</code> sets all its fields to 0. So every option that the next lines do not set is off.</li><li>The field <code>disabled</code> also stays 0. So a counter counts from the moment it is opened.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1589          a.type = (uint32_t)cfg.pmu_type;
1590          a.size = sizeof a;
1591          a.config = cfg.ev_code[e];</pre></td><td valign="top"><ul><li><code>type</code> selects the PMU: 11 in the test (<code>--pmu-type 11</code>).</li><li><code>size</code> gives Linux the size of the structure.</li><li><code>config</code> is the event code, for example 0x198 for <code>cbusy0</code> [Ref4]. The program passes the code to Linux and does not interpret it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1592          a.exclude_kernel = 1;
1593          a.exclude_hv = 1;</pre></td><td valign="top"><ul><li><code>exclude_kernel = 1</code>: the counter does not count while the CPU runs Linux kernel code.</li><li><code>exclude_hv = 1</code>: it does not count hypervisor code. A hypervisor is the software that runs virtual machines.</li><li>So the counter counts only in user mode: while the thread runs the code of the program itself.</li><li>The specification of the first runner says that counter code without these two fields fails without root on CRB [Ref10].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1594          a.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;</pre></td><td valign="top"><code>read_format</code> chooses what one <code>read</code> of the group returns. <code>PERF_FORMAT_GROUP</code>: the values of all counters of the group in one reading. The two other flags add the enabled time and the running time of the group [Ref8].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1595          int fd = (int)syscall(SYS_perf_event_open, &amp;a, 0, -1, t-&gt;group_fd, 0);</pre></td><td valign="top"><ul><li>The system call <code>perf_event_open</code> opens the counter. It returns a file descriptor: the number that later calls such as <code>read</code> use for the open counter. A negative value means failure.</li><li>Arguments <code>0</code> and <code>-1</code>: the pid and the cpu argument of the call [Ref10]. Together they mean: count the calling thread, on any CPU that it runs on.</li><li>The thread is pinned, so it runs on one CPU only.</li><li>Argument <code>t-&gt;group_fd</code>: -1 for the first counter, which starts a new group. A later counter passes the file descriptor of the leader and joins its group.</li><li>Last argument <code>0</code>: no flags.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1596          if (fd &lt; 0) {
1597              if (t-&gt;idx == 0)
1598                  fprintf(stderr, "perf_event_open %s (type %ld code 0x%llx): %s (printed as NA)\n", cfg.ev_name[e],
1599                          cfg.pmu_type, (unsigned long long)cfg.ev_code[e], strerror(errno));
1600              t-&gt;ev_pos[e] = -1;
1601              continue;
1602          }</pre></td><td valign="top"><ul><li>The open failed.</li><li>Only thread 0 writes a message to stderr: the event name, the PMU type, the code and the error text.</li><li>The event gets the position -1. <code>main</code> prints <code>NA</code> for it in the C rows (lines 3096 to 3098).</li><li>The loop continues with the next event. The thread does not stop.</li><li>In the test no csv field is <code>NA</code> and every stderr.txt is empty [Ref5]. So every open succeeded in all 120 threads.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1603          t-&gt;ev_pos[e] = t-&gt;nopen++;</pre></td><td valign="top">The open succeeded. <code>ev_pos[e]</code> gets the position of this event in a group reading: 0 for the first open counter, 1 for the next. <code>nopen</code> counts the open counters: 6 per thread in the test.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1604          if (t-&gt;group_fd &lt; 0)
1605              t-&gt;group_fd = fd;
1606      }
1607  }
1608</pre></td><td valign="top">The first counter that opens becomes the leader of the group. <code>group_fd</code> keeps its file descriptor, and every group reading uses it. The file descriptors of the other counters are not kept. The interval mode never closes, resets or stops a counter.</td></tr>
<tr><td colspan="2"><b>Function <code>cpu_ns</code>: CPU time of the calling thread</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1609  static uint64_t cpu_ns(void)
1610  {
1611      struct timespec ts;
1612      clock_gettime(CLOCK_THREAD_CPUTIME_ID, &amp;ts);
1613      return (uint64_t)ts.tv_sec * 1000000000UL + (uint64_t)ts.tv_nsec;
1614  }
1615</pre></td><td valign="top">Returns the CPU time that the calling thread has used so far, in ns. It reads the Linux clock CLOCK_THREAD_CPUTIME_ID. The worker calls it once before and once after each timed interval (lines 1686 and 1718). Both calls lie outside the timed interval.</td></tr>
<tr><td colspan="2"><b>Function <code>read_group</code>: one reading of the counter group</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1616  /* Group read: nr, time_enabled, time_running, then one value per open event. */
1617  static void read_group(const struct thread *t, struct counts *c)
1618  {</pre></td><td valign="top">Takes one reading of all counters of the thread <code>t</code> and stores it in <code>c</code>. The worker calls it once before and once after each timed interval (lines 1685 and 1719). Both calls lie outside the timed interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1619      uint64_t buf[3 + MAX_EV];</pre></td><td valign="top">Space for the largest reading: 3 header words plus 8 counter values (<code>MAX_EV</code> is 8). Each word has 8 bytes. In the test a reading has 9 words: 3 header words and 6 counter values.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1620      if (t-&gt;group_fd &lt; 0)
1621          return;</pre></td><td valign="top">A thread without an open counter returns here. Then <code>c</code> keeps the zeros that the worker wrote at line 1667.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1622      if (read(t-&gt;group_fd, buf, sizeof buf) &lt; (ssize_t)(3 * sizeof buf[0]) || buf[0] != (uint64_t)t-&gt;nopen) {
1623          perror("read of the counter group");
1624          exit(2);
1625      }</pre></td><td valign="top"><ul><li>One <code>read</code> system call on the leader returns the whole group: the number of counters <code>nr</code>, the enabled time, the running time, then one value per counter [Ref8].</li><li>The reading is rejected when it has fewer than 24 bytes (the 3 header words).</li><li>It is also rejected when <code>nr</code> is not the number of counters that this thread opened.</li><li>A rejected reading ends the whole program with a message on stderr and status 2.</li><li>In the test every stderr.txt is empty [Ref5]. So no reading was rejected.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1626      c-&gt;enabled = buf[1];
1627      c-&gt;running = buf[2];</pre></td><td valign="top">Stores the enabled time and the running time of the group, in ns. <code>main</code> prints the difference between the two readings of an interval as <code>enabled_ns</code> and <code>running_ns</code> in the C row (lines 3092 to 3093). In the test the two columns are equal in all 8880 C rows (checked on 2026-11-21) [Ref5]. So the counters counted during all of their enabled time.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1628      for (int i = 0; i &lt; t-&gt;nopen; i++)
1629          c-&gt;val[i] = buf[3 + i];
1630  }
1631</pre></td><td valign="top">Stores one value per open counter, in the order in which the counters were opened. <code>main</code> prints for each event the difference between the reading after the interval and the reading before it (line 3100).</td></tr>
<tr><td colspan="2"><b>Function <code>worker</code>: one benchmark thread</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1632  static void *worker(void *arg)
1633  {
1634      struct thread *t = arg;</pre></td><td valign="top">The start function of every worker thread. <code>main</code> creates 120 of them at line 3012. <code>t</code> is the record of this thread: <code>main</code> has set its index <code>idx</code> and its CPU <code>cpu</code> (lines 3010 to 3011).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1635      volatile uint64_t sink;</pre></td><td valign="top"><code>sink</code> is a volatile variable on the stack of this thread. <code>call</code> stores there the sum that the old read kernel returns (line 1500). So the compiler cannot remove the adds of the old read kernel. Each thread has its own <code>sink</code>, and the threads do not store to one shared cache line.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1636      /* Runtime-dependent, non-byte-repeating store value: cannot fold to memset. */
1637      uint64_t v = ((uint64_t)getpid() + (uint64_t)t-&gt;idx + 1) * 0x9E3779B97F4A7C15ULL;</pre></td><td valign="top"><code>v</code> is the value that <code>k_write</code> stores into every 8-byte word of the buffer. It depends on the process number and on the thread index. The source comment gives the reason: the compiler cannot replace the store loop by <code>memset</code>. The read kernels do not use <code>v</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1638      uint64_t k = 0; /* intervals this thread has run (--stop common) */</pre></td><td valign="top"><code>k</code> counts the timed intervals that this thread has started. Line 1677 compares it with the shared counter <code>gen</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1639      int64_t min_ns = (int64_t)(cfg.min_s * 1e9);
1640</pre></td><td valign="top"><code>min_ns</code> is the <code>--min-ms</code> value in ns: 6000000000 ns (6 s) in the test. Only the loop of <code>--stop pass</code> uses it (line 1715). The test runs with <code>--stop common</code>, so this variable does not end an interval of the test.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1641      if (cfg.ncpus)
1642          pin_cpu(t-&gt;cpu);</pre></td><td valign="top"><b>CPU pinning.</b> The test passes <code>--cpus</code>, so <code>cfg.ncpus</code> is 120. The thread binds itself to its CPU with <code>pin_cpu</code> (line 415). Thread <code>i</code> gets CPU <code>i</code>: the threads 0 to 63 run on mesh 0, the threads 64 to 119 on mesh 1. Every later line of the worker runs on that CPU.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1643      if (cfg.count)
1644          open_counters(t);</pre></td><td valign="top">With <code>--count</code> the thread opens its 6 counters with <code>open_counters</code> (line 1582). The counters count from this moment on. So they also count during the first touch and the warm-up passes. A C row holds only the change between the two readings of one interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1645      t-&gt;a = alloc_buf();</pre></td><td valign="top"><b>Buffer allocation.</b> <code>alloc_buf</code> (line 434) maps buffer <code>a</code> of this thread: 268435456 bytes (256 MiB), starting at a 2 MiB boundary, with a request to Linux for 2 MiB pages. Each thread has its own buffer. A thread reads only its own buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1646      k_write(t-&gt;a, cfg.bytes / 8, v); /* first touch by this thread */</pre></td><td valign="top"><b>First touch.</b> <code>k_write</code> (line 531) stores <code>v</code> into all 33554432 words of the buffer. The pinned thread does this write itself, before any read. Linux gives a page its physical memory at the first write. This line is not timed.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1647      if (cfg.two_buffers) {
1648          t-&gt;b = alloc_buf();
1649          k_write(t-&gt;b, cfg.bytes / 8, v);
1650      }</pre></td><td valign="top">A second buffer <code>b</code> exists only with <code>--two-buffers</code> or with a copy kernel in <code>--seq</code>. The test has neither, so these lines do not run. Every P row of the test is a row of buffer <code>a</code> [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1651      if (cfg.threads &gt; 1) {
1652          pthread_barrier_wait(&amp;bar); /* the buffers exist: main() reads the first page state */
1653          pthread_barrier_wait(&amp;bar); /* main() has read it */
1654      }
1655</pre></td><td valign="top"><ul><li>Two waits at the barrier. The barrier needs 121 threads: the 120 workers and the main thread (line 3005).</li><li>First wait: all 120 buffers exist and are written. <code>main</code> arrives at line 3045. Then it copies the buffer addresses and reads the page state for the P rows with position -1.</li><li>Second wait: the workers block until that reading is done. <code>main</code> releases them at line 3114.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1656      for (int round = 0; round &lt; cfg.rounds; round++) {
1657          for (int pos = 0; pos &lt; cfg.nseq; pos++) {</pre></td><td valign="top">The two loops over the timed intervals. <code>--rounds 2</code> runs the <code>--seq</code> list two times: round 0, then round 1. <code>pos</code> is the position in the list: 0 to 4 for like.spec, 0 to 2 for cfwd.spec and crev.spec [Ref4]. One loop pass is one interval, and <code>main</code> runs the same two loops (lines 3039 to 3040).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1658              const struct kdef *kd = &amp;kernels[cfg.seq[pos].k];</pre></td><td valign="top"><code>kd</code> is the entry of the kernel table for this position: name, type and function pointer. Example: position 0 of like.spec is <code>oldread</code>, with the type T_OLDREAD and the function <code>k_oldread</code>. The order is fixed by the list. In like.spec <code>asmread</code> always runs after <code>oldread</code>, and <code>oldread</code> of round 1 runs after <code>read_1pl</code> of round 0.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1659              size_t size = cfg.seq[pos].bytes;
1660              size_t nchunk = size / HUGE_BYTES;</pre></td><td valign="top"><code>size</code> is the number of bytes of this position: 268435456 bytes, the whole buffer. No <code>--seq</code> entry of the test has an <code>@SIZE</code> part, so <code>main</code> has set the size to the <code>--bytes</code> value (line 2990). <code>nchunk</code> is the number of 2 MiB pieces in it: 128.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1661              /* --start offset (handoff B.5): thread i starts at (i * 37 mod n) * 2 MiB */
1662              size_t off = cfg.start_offset &amp;&amp; nchunk ? ((size_t)t-&gt;idx * 37 % nchunk) * HUGE_BYTES : 0;</pre></td><td valign="top">The start offset of <code>--start offset</code>. The test passes <code>--start common</code>, so <code>off</code> is 0. Every thread starts its timed interval at byte 0 of its own buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1663              uint64_t per_byte = kd-&gt;type == T_COPY ? 2 : 1; /* copy counts read+write bytes */</pre></td><td valign="top">A copy kernel counts every byte two times: once read, once written. The kernels of the test are read kernels, so <code>per_byte</code> is 1.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1664              uint64_t bytes = 0, p = 0;
1665              int64_t sched = 0, deadline = 0, t0, t1;
1666              struct result r;
1667              memset(&amp;r, 0, sizeof r);
1668</pre></td><td valign="top">Variables of one interval. <code>bytes</code> is the byte count of the timed interval, and <code>p</code> counts its kernel calls. <code>sched</code>, <code>deadline</code>, <code>t0</code> and <code>t1</code> are clock values in ns. <code>r</code> is the result record, and <code>memset</code> sets it to zero.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1669              call(kd, t, 0, size, v, &amp;sink); /* warm-up */</pre></td><td valign="top"><b>Warm-up, not timed.</b> One call of the kernel of this position over the whole buffer: offset 0, 268435456 bytes. So before every timed interval the thread has run the same kernel once over its whole buffer. Between this pass and the timed interval lie the barrier wait, the wait for the common start and the first counter reading (lines 1675 to 1687).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1670              if (cfg.threads == 1) {
1671                  uint64_t *buf[2] = { t-&gt;a, t-&gt;b };
1672                  read_smaps(r.pg, buf, 2);
1673                  read_vmstat(r.vm);
1674              }</pre></td><td valign="top">Only a process with one thread reads the page state here, in the worker. The test has 120 threads, so these lines do not run.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1675              pthread_barrier_wait(&amp;bar);</pre></td><td valign="top">Barrier wait after the warm-up. The thread blocks until all 120 workers have ended their warm-up and <code>main</code> has arrived at line 3057. Then all 121 threads continue. A thread whose warm-up ends early waits here and reads no memory.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1676              if (cfg.stop_common) {
1677                  while (atomic_load(&amp;gen) != k + 1)
1678                      ;</pre></td><td valign="top"><b>Common start, step 1.</b> Lines 1676 to 1683 run only with <code>--stop common</code>, which the test uses. The thread repeats an empty loop until the shared counter <code>gen</code> equals <code>k + 1</code>. <code>main</code> adds 1 to <code>gen</code> at line 3062, after it has stored the start time and the deadline of this interval. In this loop the thread stays on its CPU and does not sleep.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1679                  sched = atomic_load(&amp;t_sched_ns);
1680                  deadline = atomic_load(&amp;deadline_ns);</pre></td><td valign="top">Copies the common start time into <code>sched</code> and the common deadline into <code>deadline</code>. <code>main</code> computed them at lines 3059 to 3061: the start time is its clock reading plus 2 ms (<code>LEAD_NS</code>), and the deadline is the start time plus 6 s. All 120 threads read the same two values.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1681                  while (now_ns() &lt; sched)
1682                      ;
1683              }</pre></td><td valign="top"><b>Common start, step 2.</b> The thread reads the clock again and again until the clock reaches the start time. It leaves the loop at its first clock read at or after the start time. This spin-wait is not timed.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1684              if (cfg.count) {
1685                  read_group(t, &amp;r.c0);
1686                  r.c0.cpu_ns = cpu_ns();
1687              }</pre></td><td valign="top"><ul><li>With <code>--count</code>, which the test uses: the first counter reading (<code>read_group</code>), then the thread CPU time (<code>cpu_ns</code>). Both go into <code>r.c0</code>.</li><li>These two calls run after the wait for the common start and before the clock read of line 1688.</li><li>So they are not inside the timed interval. But <code>t0</code> is later than the common start time by at least their duration.</li><li>In the test <code>t0</code> is 2 us to 34 us after the common start time (us = microsecond, computed on 2026-11-21 from the columns <code>t_sched_s</code> and <code>t_start_s</code> of all 8880 T rows) [Ref5]. Both columns are printed with 6 decimal places, so each time is rounded to 1 us.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1688              t0 = now_ns();</pre></td><td valign="top"><b>Start of the timed interval.</b> The thread reads the clock into <code>t0</code>. Each thread has its own <code>t0</code>. Nothing above this line is inside the timed interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1689              k++;</pre></td><td valign="top">Counts this interval. At the next interval line 1677 waits for the next value of <code>gen</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1690              if (cfg.stop_common) {
1691                  /* chunks of 2 MiB (or the whole entry if it is smaller); the
1692                   * position continues from chunk to chunk and wraps */
1693                  size_t chunk = size &lt; CHUNK_BYTES ? size : CHUNK_BYTES, at = off;</pre></td><td valign="top">The branch of <code>--stop common</code>, which the test uses. <code>chunk</code> is the number of bytes of one kernel call: 2097152 bytes (2 MiB, <code>CHUNK_BYTES</code>). <code>at</code> is the byte offset of the next chunk in the buffer. It starts at <code>off</code>, which is 0.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1694                  do {
1695                      call(kd, t, at, chunk, v + p++, &amp;sink);</pre></td><td valign="top"><ul><li><b>Timed kernel call.</b> <code>call</code> (line 1491) runs the kernel on the chunk at byte offset <code>at</code> of buffer <code>a</code>.</li><li>The kernel gets the address of the chunk and its length in 8-byte words: 262144.</li><li>So the kernel function is entered once per 2 MiB: 128 times per pass over the buffer.</li><li>For <code>oldread</code>, <code>call</code> stores the returned sum in <code>sink</code> after each call. The other five kernels of the test return nothing.</li><li>A read kernel does not get the argument <code>v + p++</code>. The <code>p++</code> only counts the calls.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1696                      bytes += per_byte * chunk;</pre></td><td valign="top"><ul><li><b>Bytes counted.</b> Each finished call adds 2097152 bytes.</li><li>This is the size of the range that was passed to the kernel. Nothing is counted inside a kernel.</li><li>The number is the same for every read kernel. It is also used for <code>read_1pl</code>, which loads 16 B of each 64 B line.</li><li>Example: the first T row of the file a6456.csv in the result folder of T72L1 (thread 0, <code>oldread</code>) holds 28934406144 bytes. That is 13797 calls [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1697                      at += chunk;
1698                      if (at == size)
1699                          at = 0;</pre></td><td valign="top">Moves <code>at</code> to the next chunk. After the last chunk of the buffer (chunk 127) the offset returns to 0. So the kernel calls go through the 256 MiB buffer from start to end and then start again at byte 0, until the interval ends.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1700                      t1 = now_ns();</pre></td><td valign="top"><b>Clock read after every chunk.</b> <code>t1</code> is the clock value after this call. The last <code>t1</code> is the end of the timed interval. So the timed interval holds one clock read per 2 MiB chunk: 13797 clock reads in the example above.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1701                  } while (t1 &lt; deadline);</pre></td><td valign="top"><ul><li><b>Stop rule.</b> The loop repeats while <code>t1</code> is before the common deadline.</li><li>A thread stops at its first clock read at or after the deadline. So it finishes the chunk that it is in.</li><li>The bytes and the time of this last chunk are counted.</li><li>The deadline is the same for all threads. Each thread has its own end time <code>t1</code>.</li><li>In the test the last <code>t1</code> is 0 us to 463 us after the deadline [Ref5]. The elapsed time <code>t1 - t0</code> is 5.999979 s to 6.000457 s. Both ranges were computed on 2026-11-21 from all 8880 T rows, with the deadline taken as <code>t_sched_s</code> plus 6 s.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1702              } else {
1703                  /* whole passes; with an offset a pass is [off, size) then [0, off) */
1704                  uint64_t passes_per_check = CHECK_BYTES / size;
1705                  if (passes_per_check == 0)
1706                      passes_per_check = 1;
1707                  do {
1708                      for (uint64_t c = 0; c &lt; passes_per_check; c++, p++) {
1709                          call(kd, t, off, size - off, v + p, &amp;sink);
1710                          if (off)
1711                              call(kd, t, 0, off, v + p, &amp;sink);
1712                          bytes += per_byte * size;
1713                      }
1714                      t1 = now_ns();
1715                  } while (t1 - t0 &lt; min_ns);
1716              }</pre></td><td valign="top">The branch of <code>--stop pass</code>. The test does not use it. Here a thread would run whole passes over its buffer and stop when its own elapsed time <code>t1 - t0</code> reaches the <code>--min-ms</code> value.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1717              if (cfg.count) {
1718                  r.c1.cpu_ns = cpu_ns();
1719                  read_group(t, &amp;r.c1);
1720              }</pre></td><td valign="top"><ul><li><b>After the timed interval.</b> The interval ended at the last clock read of line 1700.</li><li>The thread reads its thread CPU time and then takes the second counter reading. Both go into <code>r.c1</code>.</li><li>The order is the reverse of lines 1685 to 1686. So the timed interval lies between the two CPU-time readings, and these lie between the two counter readings.</li><li>So the counter values of a C row cover the timed interval plus a few calls around it: the two readings of the thread CPU time and the clock read <code>t0</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1721              r.bytes = bytes;
1722              r.t_start = t0;
1723              r.t_end = t1;</pre></td><td valign="top">Stores the result of this thread: the byte count, <code>t0</code> and the last <code>t1</code>. <code>main</code> computes the elapsed time of a thread as <code>t_end - t_start</code> (lines 3069 and 3082). The script stat_bwx.py computes the rate of a thread from the T row as bytes / elapsed seconds / 1e9, in GB/s [Ref6].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1724              r.t_sched = cfg.stop_common ? sched : t0;</pre></td><td valign="top">Stores the common start time. <code>main</code> prints it in the T row as <code>t_sched_s</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1725              r.late = cfg.stop_common &amp;&amp; t0 - sched &gt; LATE_NS;</pre></td><td valign="top"><b>Late flag.</b> It is set when <code>t0</code> is more than 100000 ns (100 us, <code>LATE_NS</code>) after the common start time. <code>main</code> then prints <code>late</code> in the last column of the T row. The program does nothing else with the flag: the interval runs, and its bytes are counted. In the test no T row has the flag [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1726              t-&gt;res = r;</pre></td><td valign="top">Copies the record into the thread structure. <code>main</code> reads it there after the barrier wait of the next line.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1727              pthread_barrier_wait(&amp;bar);</pre></td><td valign="top">Barrier wait at the end of the interval. The thread blocks until all 120 workers have ended their interval and <code>main</code> waits at line 3064. A thread that has stopped reads no memory while other threads finish their last chunk.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1728              /* main() reads the page state of all buffers. The warm-up pass of
1729               * the next interval starts only after that reading (handoff B.6). */
1730              if (cfg.threads &gt; 1)
1731                  pthread_barrier_wait(&amp;bar);</pre></td><td valign="top"><ul><li>Second barrier wait at the end of the interval.</li><li>While the workers block here, <code>main</code> prints the I, T and C rows of the interval and reads the page state of all buffers (lines 3066 to 3113).</li><li><code>main</code> releases the workers at line 3114. Then each worker starts the warm-up pass of the next interval.</li><li><code>main</code> prints the P rows and the <code># page_read</code> line after the release (lines 3115 to 3118). So this output can run while the workers do their warm-up.</li><li>The output ends before the next timed interval starts. The barrier of line 1675 lets the workers pass only when <code>main</code> has finished the output and waits at line 3057.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1732          }
1733      }
1734      return NULL;
1735  }
1736</pre></td><td valign="top">The ends of the two loops. The worker calls no sleep function. So between two intervals lie only the waits, the readings and the warm-up pass of the rows above. After the last interval of round 1 the thread returns, and <code>main</code> waits for all threads at line 3124.</td></tr>
<tr><td colspan="2"><b>Function <code>usage</code>: option summary, then exit</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1737  static void usage(void)
1738  {
1739      fprintf(stderr,
1740              "usage: bwx --seq LIST [--threads T --cpus LIST] [--bytes B] [--min-ms MS] [--no-thp]\n"
1741              "           [--rounds N] [--stop pass|common] [--start common|offset] [--two-buffers]\n"
1742              "           [--count --pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"
1743              "       bwx --selftest | --list\n"
1744              "  --seq: comma-separated entries KERNEL or KERNEL@SIZE; --list prints the kernel names\n"
1745              "  sizes must be multiples of 256; with --stop common: multiples of 2M, or below 2M\n"
1746              "  --pmu-type and CODE: the perf_event_attr fields type and config of the core PMU (CODE may be 0x..)\n");
1747      exit(2);
1748  }
1749</pre></td><td valign="top">Prints the option summary to stderr and ends the program with status 2. <code>main</code> calls it for an argument that it does not accept and for settings that fail one of its checks (lines 2969 to 2995), for example <code>--threads</code> without <code>--cpus</code>. The argument lines of the test do not reach it. The text names the program <code>bwx</code>, the name of an older version of the runner.</td></tr>
<tr><td colspan="2"><b>Function <code>parse_seq</code>: reads the <code>--seq</code> list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1750  static void parse_seq(char *list)
1751  {
1752      for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {</pre></td><td valign="top"><code>main</code> calls it with the text after <code>--seq</code> (line 2950). <code>strtok</code> cuts the text at every comma. Each loop pass handles one entry, in the order of the list. This order is the order in which the kernels run in each round.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1753          char *at = strchr(tok, '@');
1754          int k = 0;
1755          if (at)
1756              *at = '\0';</pre></td><td valign="top">An entry may have the form <code>KERNEL@SIZE</code>. Then the name ends at the <code>@</code>. No entry of the test has an <code>@</code> [Ref4].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1757          while (k &lt; K_COUNT &amp;&amp; strcmp(tok, kernels[k].name))
1758              k++;</pre></td><td valign="top">Searches the kernel table <code>kernels[]</code> (lines 1454 to 1484) for the name, from the first entry on. <code>k</code> becomes the index of the entry with this name.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1759          if (k == K_COUNT || cfg.nseq == MAX_SEQ) {
1760              fprintf(stderr, "bad --seq entry: %s\n", tok);
1761              exit(2);
1762          }</pre></td><td valign="top">A name that is not in the table ends the program with a message and status 2. So does a 65th entry (<code>MAX_SEQ</code> is 64).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1763          cfg.seq[cfg.nseq].k = k;
1764          cfg.seq[cfg.nseq].bytes = at ? parse_bytes(at + 1) : 0;
1765          cfg.nseq++;</pre></td><td valign="top">Stores the index and the size of the entry in <code>cfg.seq</code>. An entry without <code>@SIZE</code> gets the size 0 here. <code>main</code> later replaces 0 by the <code>--bytes</code> value (line 2990).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1766      }
1767  }
1768</pre></td><td valign="top"><ul><li>Result for like.spec: <code>oldread</code>, <code>asmread</code>, <code>read_nop96</code>, <code>read_nop256</code>, <code>read_1pl</code> (5 positions) [Ref4].</li><li>Result for cfwd.spec: <code>oldread</code>, <code>read</code>, <code>asmread</code> (3 positions).</li><li>Result for crev.spec: <code>asmread</code>, <code>read</code>, <code>oldread</code> (3 positions). This is the reverse order of cfwd.spec.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>parse_events</code>: reads the <code>--events</code> list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1769  /* "NAME=CODE,..." or "CODE,...". A code without a name gets the name of its
1770   * position in the list of handoff B.8. */
1771  static void parse_events(char *list)
1772  {
1773      static const char *by_pos[5] = { "cycles", "instructions", "l1d_refill", "l2d_refill", "ll_miss_rd" };</pre></td><td valign="top"><code>main</code> calls it with the text after <code>--events</code> (line 2964). An entry is <code>NAME=CODE</code> or only <code>CODE</code>. The table <code>by_pos</code> holds the names for an entry without a name at one of the first 5 places of the list. Every entry of the test has a name, so the table is not used [Ref4].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1774      for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
1775          char *eq = strchr(tok, '='), *code = eq ? eq + 1 : tok, *end;</pre></td><td valign="top">One loop pass per entry. <code>eq</code> points to the <code>=</code> sign of the entry. <code>code</code> points to the text after it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1776          if (eq == tok || cfg.nev == MAX_EV || (eq &amp;&amp; (size_t)(eq - tok) &gt;= sizeof cfg.ev_name[0])) {
1777              fprintf(stderr, "bad --events entry: %s\n", tok);
1778              exit(2);
1779          }</pre></td><td valign="top">Rejects an entry with an empty name, a 9th entry (<code>MAX_EV</code> is 8) and a name of 32 characters or more. The program then ends with a message and status 2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1780          if (eq)
1781              snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "%.*s", (int)(eq - tok), tok);</pre></td><td valign="top">Copies the text before the <code>=</code> as the name of the event. The interval mode uses the name in two places: as a column title in the header line of the C rows (line 3031), and in the error message of <code>open_counters</code> (line 1598).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1782          else if (cfg.nev &lt; 5)
1783              strcpy(cfg.ev_name[cfg.nev], by_pos[cfg.nev]);
1784          else
1785              snprintf(cfg.ev_name[cfg.nev], sizeof cfg.ev_name[0], "ev%d", cfg.nev);</pre></td><td valign="top">Names for an entry without <code>=</code>: a name of <code>by_pos</code>, or <code>ev</code> plus the entry number. The test does not use these lines.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1786          cfg.ev_code[cfg.nev] = strtoull(code, &amp;end, 0);
1787          if (end == code || *end != '\0') {
1788              fprintf(stderr, "bad --events code: %s\n", code);
1789              exit(2);
1790          }</pre></td><td valign="top"><code>strtoull</code> with base 0 turns the code text into a number. With base 0 a text that starts with <code>0x</code> is read as hexadecimal. A text that is not a whole number ends the program with a message and status 2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1791          cfg.nev++;
1792      }
1793  }
1794</pre></td><td valign="top">Counts the entry. Result in the test: 6 events with the names cbusy0, cbusy1, cbusy2, cbusy3, cbusy_mt, bus_access and the codes 0x198, 0x199, 0x19a, 0x19b, 0x19c, 0x19 [Ref4].</td></tr>
<tr><td colspan="2"><b>Trial mode (lines 1795 to 2886): not run by the whole-chip test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1795  /*
1796   * Trial mode (--trial). Design: crb/new-test-kernel/tackle-8mb.md, "Runner
1797   * design". Formats: DECISIONS-bwx8.md.
1798   *
1799   * The plan file gives the trials of the process. The whole plan is read and
1800   * checked before the process pins, allocates or opens a counter. A defect
1801   * ends the process with status 2.
1802   *
1803   * One trial is a list of windows: previous activity (1), prefix (4),
1804   * predecessor (1), target (nwin). timed_sequence() runs them. It calls only
1805   * the kernels and the clock. With count "read" it also reads the counter
1806   * group and the thread CPU clock at the boundaries of the target windows.
1807   * Page state, context switches, counter open and close, and all output lie
1808   * outside the timed sequence.
1809   */</pre></td><td valign="top"><ul><li>The trial mode starts here and ends at line 2886.</li><li><code>main</code> enters it only when an argument is the word <code>--trial</code> (lines 2912 to 2914). No argument line of the test holds that word [Ref4].</li><li>So no function of this section runs in the test. The rows below say only what each part is.</li><li>This comment describes the mode: a plan file lists the trials, a trial is a list of windows, and <code>timed_sequence</code> runs the windows.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1810  #include &lt;stdarg.h&gt;
1811  #include &lt;sys/resource.h&gt;
1812
1813  #define BIN_NS 10000000L     /* requested width of a bin: 10 ms */
1814  #define TRACE_CAP (1L &lt;&lt; 20) /* --trace: events kept per trial */
1815  #define PLAN_LINE1 "# bwx8-plan v1"
1816  #define PLAN_LINE3 "# trial cond rep prev pfx pred tgt nwin win_ms count bins"
1817  #define PLAN_FIELDS 11
1818  #define MAX_PAIRS 64
1819  #define MAX_NWIN 4096
1820  #define MAX_MS 3600000L
1821  #define MAX_REC_BYTES (256UL &lt;&lt; 20) /* bound of the record storage of one plan */
1822</pre></td><td valign="top">Two more headers and the constants of the trial mode. <code>BIN_NS</code> is the requested width of a bin: 10 ms. <code>TRACE_CAP</code> is the largest number of trace events per trial: 1048576. The other lines fix line 1 and line 3 of a plan file, the number of fields of a plan line (11) and upper limits for the values of a plan.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1823  enum { PH_PREV, PH_PREFIX, PH_PRED, PH_TARGET };
1824  enum { CS_CLOSED, CS_OPEN, CS_READ, CS_FAIL };
1825  enum { EV_CLOCK, EV_KERNEL_FIRST, EV_COUNT_READ, EV_CPU_CLOCK, EV_PAGE_READ, EV_RUSAGE, EV_OUTPUT, EV_COUNT_OPEN, EV_COUNT_CLOSE };
1826  static const char *const phase_name[] = { "prev", "prefix", "pred", "target" };
1827  static const char *const count_name[] = { "closed", "open", "read", "fail" };
1828  static const char *const event_name[] = { "clock", "kernel_first", "count_read", "cpu_clock", "page_read",
1829                                            "rusage", "output", "count_open", "count_close" };
1830</pre></td><td valign="top">Number codes and their printed names. The first group names the four kinds of window of a trial, called phases: previous activity, prefix, predecessor and target. The second group names the states of the counters: closed, open, read and fail. The third group names the nine kinds of trace event.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1831  /* One kernel on a range for a time. k &lt; 0: this part is absent ("-"). */
1832  struct part {
1833      int k;
1834      uint64_t size;
1835      long ms;
1836  };
1837
1838  /* One line of the plan. */
1839  struct trial {
1840      char *f[PLAN_FIELDS]; /* the fields as text, for the S row */
1841      int nwin, count, bins;
1842      long win_ms;
1843      struct part prev, pfx, pred, tgt;
1844  };
1845</pre></td><td valign="top"><code>struct part</code> is one kernel on one buffer range for one duration in ms. <code>struct trial</code> is one line of the plan file: its text fields, the number of target windows, the counter setting, the bin setting, the duration of a target window and the four parts.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1846  struct bin {
1847      int64_t t_end;  /* a clock read of the window loop */
1848      uint64_t bytes; /* bytes since the start of the window */
1849  };
1850
1851  /* One window. set_windows() fills the first group of fields before the first
1852   * trial. timed_sequence() fills the second group. */
1853  struct win {
1854      int k, phase, widx;
1855      uint64_t size;
1856      uint64_t passes; /* passes between two clock reads */
1857      int64_t dur_ns;
1858      struct bin *bin; /* NULL: no bins */
1859      int bin_cap;
1860
1861      int nbin;
1862      uint64_t bytes;
1863      int64_t t_start, t_end; /* CLOCK_MONOTONIC, ns */
1864  };
1865</pre></td><td valign="top"><code>struct bin</code> is one clock read of a window with the byte count at that read. <code>struct win</code> is one window. Its first group of fields is the plan: kernel, phase, index, size, passes between two clock reads, duration and bin storage. Its second group is the result: number of bins, bytes, start time and end time.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1866  /* The record of one trial. */
1867  struct trec {
1868      struct win *win;
1869      int nw;
1870      struct counts *cnt; /* count "read": nwin + 1 readings, one per target boundary */
1871      struct page pg[2];  /* before and after the timed sequence */
1872      long long vm[2][4];
1873      uint64_t cpu[2];
1874      long nvcsw[2], nivcsw[2];
1875      long minflt[2]; /* minor page faults of the thread, for the --trace check */
1876      int state;   /* CS_* */
1877      int sink_ok; /* 1, 0, or -1 if the trial ran no old read */
1878      int read_fail, close_fail;
1879  };
1880</pre></td><td valign="top"><code>struct trec</code> is the record of one trial. It holds the windows and the counter readings. It holds the page state, the thread CPU time, the context-switch counts and the page-fault counts before and after the timed sequence. It also holds the counter state, the result of the sum check (<code>sink_ok</code>) and two failure counts.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1881  struct tev {
1882      int64_t t;
1883      int widx;
1884      uint8_t ev, phase;
1885  };
1886
1887  /* The worker of the trial mode. */
1888  struct tw {
1889      struct thread t; /* a, group_fd, ev_pos, nopen: used as in the interval mode */
1890      uint64_t v;      /* every word of the buffer holds v */
1891      int fd[MAX_EV], nfd;
1892      int group_open; /* an open was tried and no close followed */
1893      int open_fail;  /* events that did not open */
1894      int close_fail, read_fail;
1895      char open_err[160];
1896      /* --trace */
1897      struct tev *log;
1898      long nlog, ndrop;
1899      int64_t last_t;
1900      int cur_phase, cur_widx;
1901  };
1902</pre></td><td valign="top"><code>struct tev</code> is one event of the trace: a clock time, a window index, the event kind and the phase. <code>struct tw</code> is the state of the worker of the trial mode. Its first field is a <code>struct thread</code>, the same record that the interval mode uses for a worker.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1903  static struct {
1904      const char *path;
1905      uint64_t hash;
1906      char *pair[MAX_PAIRS];
1907      int npair;
1908      struct trial *tr;
1909      int n;
1910      int ctl_cpu, trace;
1911  /* bwx10+ */
1912      size_t rec_pad; /* --rec-pad: unused bytes before win[] in the record block */
1913      int hot_copy;   /* --hot-copy: timed_sequence_hot() runs the windows */
1914  /* bwx10- */
1915  } plan;
1916
1917  static struct trec *rec;
1918  static struct {
1919      size_t windows, bins, counts, trace, bytes;
1920  } recsz;
1921</pre></td><td valign="top">Three global variables of the trial mode. <code>plan</code> holds the plan file and the options of the mode. <code>rec</code> points to the records of all trials. <code>recsz</code> holds the sizes of the record storage.</td></tr>
<tr><td colspan="2"><b>Function <code>tev_add</code> (trial mode): adds one event to the trace</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1922  /* --trace. An event that is not a clock read carries the time of the latest
1923   * clock read: the trace adds no clock read of its own. */
1924  static inline void tev_add(struct tw *w, int ev, int phase, int widx)
1925  {
1926      if (!w-&gt;log)
1927          return;
1928      if (w-&gt;nlog == TRACE_CAP) {
1929          w-&gt;ndrop++;
1930          return;
1931      }
1932      w-&gt;log[w-&gt;nlog++] = (struct tev){ .t = w-&gt;last_t, .widx = widx, .ev = (uint8_t)ev, .phase = (uint8_t)phase };
1933  }
1934</pre></td><td valign="top">Without <code>--trace</code> there is no log, and the function returns at once. Otherwise it appends one event with the time of the latest clock read. A full log (1048576 events) only raises the count of dropped events. The whole-chip test does not call this function.</td></tr>
<tr><td colspan="2"><b>Function <code>tclock</code> (trial mode): clock read</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1935  static inline int64_t tclock(struct tw *w)
1936  {
1937      int64_t t = now_ns();
1938      if (w-&gt;log) {
1939          w-&gt;last_t = t;
1940          tev_add(w, EV_CLOCK, 0, 0);
1941      }
1942      return t;
1943  }
1944</pre></td><td valign="top">Reads the clock with <code>now_ns</code> (line 327). With <code>--trace</code> it also stores the time and logs the read as an event. The whole-chip test does not call this function.</td></tr>
<tr><td colspan="2"><b>Function <code>tcpu</code> (trial mode): thread CPU time</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1945  static uint64_t tcpu(struct tw *w)
1946  {
1947      uint64_t c = cpu_ns();
1948      tev_add(w, EV_CPU_CLOCK, 0, 0);
1949      return c;
1950  }
1951</pre></td><td valign="top">Reads the thread CPU time with <code>cpu_ns</code> (line 1609). With <code>--trace</code> it also logs the read as an event. The whole-chip test does not call this function.</td></tr>
<tr><td colspan="2"><b>Function <code>tcall</code> (trial mode): one kernel call of a window</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1952  /* Every kernel call of a trial goes through here, and from here through the
1953   * unchanged call(). The trace gets the first call of each window. */
1954  static inline void tcall(struct tw *w, const struct win *r, volatile uint64_t *sink)
1955  {
1956      if (w-&gt;log &amp;&amp; (r-&gt;phase != w-&gt;cur_phase || r-&gt;widx != w-&gt;cur_widx)) {
1957          w-&gt;cur_phase = r-&gt;phase;
1958          w-&gt;cur_widx = r-&gt;widx;
1959          tev_add(w, EV_KERNEL_FIRST, r-&gt;phase, r-&gt;widx);
1960      }
1961      call(&amp;kernels[r-&gt;k], &amp;w-&gt;t, 0, r-&gt;size, 0, sink);
1962  }
1963</pre></td><td valign="top">Runs the kernel of the window <code>r</code> once on the first <code>r-&gt;size</code> bytes of the buffer. It goes through <code>call</code> (line 1491), the same function that the interval mode uses. With <code>--trace</code> it logs the first call of each window. The whole-chip test does not call this function.</td></tr>
<tr><td colspan="2"><b>Function <code>tcount</code> (trial mode): counter reading at a window boundary</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1964  /* Group read and thread CPU clock, at a boundary of a target window. Not
1965   * inlined: build8.sh lists the branch targets of timed_sequence(), and this
1966   * function must be one name there. */
1967  __attribute__((noinline)) static void tcount(struct tw *w, struct counts *c)
1968  {
1969      uint64_t buf[3 + MAX_EV];
1970      if (w-&gt;t.group_fd &gt;= 0) {
1971          ssize_t want = (ssize_t)((3 + (size_t)w-&gt;t.nopen) * sizeof buf[0]);
1972          if (read(w-&gt;t.group_fd, buf, sizeof buf) != want || buf[0] != (uint64_t)w-&gt;t.nopen) {
1973              w-&gt;read_fail++;
1974          } else {
1975              c-&gt;enabled = buf[1];
1976              c-&gt;running = buf[2];
1977              for (int i = 0; i &lt; w-&gt;t.nopen; i++)
1978                  c-&gt;val[i] = buf[3 + i];
1979          }
1980          tev_add(w, EV_COUNT_READ, 0, 0);
1981      }
1982      c-&gt;cpu_ns = tcpu(w);
1983  }
1984</pre></td><td valign="top">Reads the counter group and then the thread CPU time. In <code>read_group</code> (line 1617) a bad reading ends the process. Here it only adds 1 to <code>read_fail</code>. The whole-chip test does not call this function.</td></tr>
<tr><td colspan="2"><b>Function <code>timed_sequence</code> (trial mode): the timed windows of one trial</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1985  /*
1986   * The timed sequence of one trial. Each window runs whole passes over
1987   * [0, size) and reads the clock after every "passes" passes. It ends at the
1988   * first clock read at or after its duration. At a boundary the clock is read
1989   * for the end of the window and again for the start of the next one, so the
1990   * gap is measured. No output, allocation, page read, sleep or warm-up pass
1991   * is in here. Not inlined: build8.sh and test_runner8.py read the branch
1992   * targets of this function from the machine code. Only clock_gettime, the
1993   * kernel call of call() and tcount() are allowed there.
1994   */
1995  __attribute__((noinline)) static void timed_sequence(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)
1996  {</pre></td><td valign="top">The timed part of the trial mode. It runs the windows of one trial one after another, as the comment describes. The whole-chip test does not call this function. The timed loop of the test is in <code>worker</code> (lines 1688 to 1701).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1997      for (int i = 0; i &lt; r-&gt;nw; i++) {
1998          struct win *x = &amp;r-&gt;win[i];
1999          uint64_t bytes = 0;
2000          int64_t t0, t1, next_bin;
2001          int nbin = 0;
2002
2003          if (count_read &amp;&amp; x-&gt;phase == PH_TARGET)
2004              tcount(w, &amp;r-&gt;cnt[x-&gt;widx]);
2005          t0 = tclock(w);
2006          next_bin = t0 + BIN_NS;
2007          do {
2008              for (uint64_t c = 0; c &lt; x-&gt;passes; c++) {
2009                  tcall(w, x, sink);
2010                  bytes += x-&gt;size;
2011              }
2012              t1 = tclock(w);
2013              /* A bin closes on this clock read if its requested end has
2014               * passed. The last clock read of the window closes the last bin. */
2015              if (x-&gt;bin &amp;&amp; (t1 &gt;= next_bin || t1 - t0 &gt;= x-&gt;dur_ns) &amp;&amp; nbin &lt; x-&gt;bin_cap) {
2016                  x-&gt;bin[nbin].t_end = t1;
2017                  x-&gt;bin[nbin].bytes = bytes;
2018                  nbin++;
2019                  while (next_bin &lt;= t1)
2020                      next_bin += BIN_NS;
2021              }
2022          } while (t1 - t0 &lt; x-&gt;dur_ns);
2023          x-&gt;bytes = bytes;
2024          x-&gt;t_start = t0;
2025          x-&gt;t_end = t1;
2026          x-&gt;nbin = nbin;
2027      }
2028      if (count_read)
2029          tcount(w, &amp;r-&gt;cnt[r-&gt;win[r-&gt;nw - 1].widx + 1]);
2030  }
2031</pre></td><td valign="top"><ul><li>One loop pass per window.</li><li>When the trial reads counters, a target window starts with a call of <code>tcount</code>. One more call follows after the last window.</li><li><code>t0</code> is the start clock read of the window.</li><li>The inner loop runs <code>passes</code> whole passes of the kernel and then reads the clock into <code>t1</code>. It repeats until the duration of the window has passed.</li><li>A bin closes at a clock read when its requested end has passed. It stores <code>t1</code> and the byte count.</li><li>At the end the window record gets the bytes, <code>t0</code>, the last <code>t1</code> and the number of bins.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>tcall_hot</code> (trial mode): <code>tcall</code> with value arguments</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2032  /* bwx10+ */
2033  /* tcall() for timed_sequence_hot(): the kernel index, the phase, the window
2034   * index and the size come by value, so no field of win[i] is read here. */
2035  static inline void tcall_hot(struct tw *w, int k, int phase, int widx, uint64_t size, volatile uint64_t *sink)
2036  {
2037      if (w-&gt;log &amp;&amp; (phase != w-&gt;cur_phase || widx != w-&gt;cur_widx)) {
2038          w-&gt;cur_phase = phase;
2039          w-&gt;cur_widx = widx;
2040          tev_add(w, EV_KERNEL_FIRST, phase, widx);
2041      }
2042      call(&amp;kernels[k], &amp;w-&gt;t, 0, size, 0, sink);
2043  }
2044</pre></td><td valign="top">The same as <code>tcall</code> (line 1954), but the kernel index, the phase, the window index and the size arrive as arguments. So it reads no field of the window record. The comment <code>/* bwx10+ */</code> marks text that the version bwx10 added. The whole-chip test does not call this function.</td></tr>
<tr><td colspan="2"><b>Function <code>timed_sequence_hot</code> (trial mode): variant for <code>--hot-copy</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2045  /*
2046   * --hot-copy: timed_sequence() with one difference. Before the start clock
2047   * read of a window it copies the fields of win[i] that the window loop needs
2048   * into local variables. After the end clock read it stores bytes, t_start,
2049   * t_end and nbin. Between the first pass and the last pass of a window it
2050   * does not read or write win[i]. The compiler cannot read a field again
2051   * inside the loop in place of the local copy: the loop calls a kernel
2052   * through a pointer, and such a call may change any memory. The self-test
2053   * checks it on the machine code (test_hot_touch). The same rules as for
2054   * timed_sequence() hold for the calls made here.
2055   */
2056  __attribute__((noinline)) static void timed_sequence_hot(struct tw *w, struct trec *r, int count_read, volatile uint64_t *sink)</pre></td><td valign="top">The variant of <code>timed_sequence</code> that the trial-mode option <code>--hot-copy</code> selects. The whole-chip test does not call this function.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2057  {
2058      for (int i = 0; i &lt; r-&gt;nw; i++) {
2059          struct win *x = &amp;r-&gt;win[i];
2060          const int k = x-&gt;k, phase = x-&gt;phase, widx = x-&gt;widx, bin_cap = x-&gt;bin_cap;
2061          const uint64_t size = x-&gt;size, passes = x-&gt;passes;
2062          const int64_t dur_ns = x-&gt;dur_ns;
2063          struct bin *const bin = x-&gt;bin;
2064          uint64_t bytes = 0;
2065          int64_t t0, t1, next_bin;
2066          int nbin = 0;
2067
2068          if (count_read &amp;&amp; phase == PH_TARGET)
2069              tcount(w, &amp;r-&gt;cnt[widx]);
2070          t0 = tclock(w);
2071          next_bin = t0 + BIN_NS;
2072          do {
2073              for (uint64_t c = 0; c &lt; passes; c++) {
2074                  tcall_hot(w, k, phase, widx, size, sink);
2075                  bytes += size;
2076              }
2077              t1 = tclock(w);
2078              if (bin &amp;&amp; (t1 &gt;= next_bin || t1 - t0 &gt;= dur_ns) &amp;&amp; nbin &lt; bin_cap) {
2079                  bin[nbin].t_end = t1;
2080                  bin[nbin].bytes = bytes;
2081                  nbin++;
2082                  while (next_bin &lt;= t1)
2083                      next_bin += BIN_NS;
2084              }
2085          } while (t1 - t0 &lt; dur_ns);
2086          x-&gt;bytes = bytes;
2087          x-&gt;t_start = t0;
2088          x-&gt;t_end = t1;
2089          x-&gt;nbin = nbin;
2090      }
2091      if (count_read)
2092          tcount(w, &amp;r-&gt;cnt[r-&gt;win[r-&gt;nw - 1].widx + 1]);
2093  }
2094</pre></td><td valign="top">The same loop as lines 1997 to 2030, with one difference. Before the start clock read of a window it copies the fields of the window record into local constants (lines 2060 to 2063). It writes the results back after the end clock read (lines 2086 to 2089). The source comment says that between these two points the loop does not read or write the window record.</td></tr>
<tr><td colspan="2"><b>Trial mode, lines 2095 to 2598: not run in the test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2095  /* bwx10- */</pre></td><td valign="top">This comment line ends a block that bwx10 added. The block starts at line 2032.<ul><li>Every line from here to line 2598 belongs to the trial mode. <code>main</code> enters the trial mode only when an argument is the word <code>--trial</code> (lines 2912 to 2914). No argument line of the whole-chip test holds this word [Ref4]. So these lines did not run in the test.</li><li>The self-test also calls some of these functions. It runs only with the option <code>--selftest</code> (line 2919), and no argument line of the test holds it [Ref4].</li><li>Cross-check with the data: the trial mode prints rows that start with <code>M</code> before its first trial (line 2481). In the 9 csv files of the test every line starts with <code>I</code>, <code>T</code>, <code>P</code>, <code>C</code> or <code>#</code> (counted with awk on 2026-11-21) [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>count_close</code>: closes the counter group (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2096  static void count_close(struct tw *w)
2097  {
2098      for (int i = 0; i &lt; w-&gt;nfd; i++)
2099          if (close(w-&gt;fd[i]) != 0)
2100              w-&gt;close_fail++;
2101      w-&gt;nfd = 0;
2102      w-&gt;t.group_fd = -1;
2103      w-&gt;t.nopen = 0;
2104      w-&gt;group_open = 0;
2105      w-&gt;open_fail = 0;
2106      tev_add(w, EV_COUNT_CLOSE, 0, 0);
2107  }
2108</pre></td><td valign="top">Closes every counter file descriptor that <code>count_open</code> stored in <code>w-&gt;fd</code>. Each <code>close</code> that fails adds 1 to <code>w-&gt;close_fail</code>. Then it resets the group state of the worker: no leader, no open event, no failed open. <code>tev_add</code> (line 1924) records the step in the trace, and it does nothing without the option <code>--trace</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>count_open</code>: opens the counter group (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2109  /* One group, user mode only, opened by the pinned worker for itself. The
2110   * events count from the open on. An event that does not open is counted in
2111   * open_fail and is printed as NA. */
2112  static void count_open(struct tw *w)
2113  {
2114      w-&gt;t.group_fd = -1;
2115      w-&gt;t.nopen = 0;
2116      w-&gt;nfd = 0;
2117      w-&gt;open_fail = 0;
2118      for (int e = 0; e &lt; cfg.nev; e++) {
2119          struct perf_event_attr a;
2120          memset(&amp;a, 0, sizeof a);
2121          a.type = (uint32_t)cfg.pmu_type;
2122          a.size = sizeof a;
2123          a.config = cfg.ev_code[e];
2124          a.exclude_kernel = 1;
2125          a.exclude_hv = 1;
2126          a.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
2127          int fd = (int)syscall(SYS_perf_event_open, &amp;a, 0, -1, w-&gt;t.group_fd, 0);
2128          if (fd &lt; 0) {
2129              if (w-&gt;open_fail++ == 0)
2130                  snprintf(w-&gt;open_err, sizeof w-&gt;open_err, "%s type %ld code 0x%llx: %s", cfg.ev_name[e], cfg.pmu_type,
2131                           (unsigned long long)cfg.ev_code[e], strerror(errno));
2132              w-&gt;t.ev_pos[e] = -1;
2133              continue;
2134          }
2135          w-&gt;t.ev_pos[e] = w-&gt;t.nopen++;
2136          w-&gt;fd[w-&gt;nfd++] = fd;
2137          if (w-&gt;t.group_fd &lt; 0)
2138              w-&gt;t.group_fd = fd;
2139      }
2140      w-&gt;group_open = 1;
2141      tev_add(w, EV_COUNT_OPEN, 0, 0);
2142  }
2143</pre></td><td valign="top"><ul><li>The trial-mode version of <code>open_counters</code> (line 1582). The test uses <code>open_counters</code>, not this function.</li><li>Lines 2119 to 2127 set up each counter in the same way as <code>open_counters</code>: one counter per event of <code>cfg</code>, user mode only, for the calling thread on any CPU. The first counter that opens is the leader of the group. The counters count from the open on.</li><li>Different: it keeps every file descriptor in <code>w-&gt;fd</code>, so that <code>count_close</code> can close the group.</li><li>Different: it writes nothing to stderr. An event that does not open adds 1 to <code>w-&gt;open_fail</code>. The error text of the first such event goes to <code>w-&gt;open_err</code>, and <code>emit_trial</code> prints it in an X row (a row that reports a problem).</li><li><code>group_open</code> becomes 1 also when no event opened.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>page_read</code>: page state before or after a trial (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2144  static void page_read(struct tw *w, struct trec *r, int at)
2145  {
2146      uint64_t *buf[1] = { w-&gt;t.a };
2147      read_smaps(&amp;r-&gt;pg[at], buf, 1);
2148      read_vmstat(r-&gt;vm[at]);
2149      tev_add(w, EV_PAGE_READ, 0, 0);
2150  }
2151</pre></td><td valign="top"><ul><li>Reads the page state of the one buffer of the worker into <code>r-&gt;pg[at]</code> with <code>read_smaps</code> (line 1515). Reads the four vmstat counters into <code>r-&gt;vm[at]</code> with <code>read_vmstat</code> (line 1545).</li><li><code>at</code> is 0 before the timed sequence and 1 after it. The timed sequence is the run of all windows of one trial (function <code>timed_sequence</code>, line 1995).</li><li>The <code># page_read</code> lines of the test files do not come from this function. <code>main</code> prints them at line 3118.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>switches</code>: context switches and page faults of the thread (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2152  /* Context-switch counts of the calling thread. -1: not readable. */
2153  static void switches(struct tw *w, struct trec *r, int at)
2154  {
2155      struct rusage ru;
2156      int ok = getrusage(RUSAGE_THREAD, &amp;ru) == 0;
2157      r-&gt;nvcsw[at] = ok ? ru.ru_nvcsw : -1;
2158      r-&gt;nivcsw[at] = ok ? ru.ru_nivcsw : -1;
2159      r-&gt;minflt[at] = ok ? ru.ru_minflt : -1;
2160      tev_add(w, EV_RUSAGE, 0, 0);
2161  }
2162</pre></td><td valign="top">Asks Linux for the resource use of the calling thread (<code>getrusage</code> with RUSAGE_THREAD). It stores three counts in the record <code>r</code> of the trial.<ul><li><code>ru_nvcsw</code>: voluntary context switches. The thread stopped running by its own request, usually to wait for something.</li><li><code>ru_nivcsw</code>: involuntary context switches. Linux took the CPU away from the thread.</li><li><code>ru_minflt</code>: minor page faults. These are page faults that need no disk access. The first touch of a page is one.</li><li>When the call fails, each of the three is stored as -1.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>first_multiplexed</code>: counters that did not count all the time (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2163  /* The index of the first target window whose counters ran for less time
2164   * than they were enabled, or -1. cnt holds nwin + 1 readings. */
2165  static int first_multiplexed(const struct counts *cnt, int nwin)
2166  {
2167      for (int i = 0; i &lt; nwin; i++)
2168          if (cnt[i + 1].running - cnt[i].running &lt; cnt[i + 1].enabled - cnt[i].enabled)
2169              return i;
2170      return -1;
2171  }
2172</pre></td><td valign="top"><ul><li>A trial ends with <code>nwin</code> target windows (the windows of its last phase, see <code>trial_windows</code> at line 2217). <code>cnt</code> holds one counter reading per boundary of the target windows: <code>nwin</code> + 1 readings.</li><li>For each target window the function compares the growth of the running time with the growth of the enabled time. It returns the number of the first window in which the running time grew less. In such a window the counters did not count all the time.</li><li>It returns -1 when there is no such window.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>run_trial</code>: runs one trial, prints nothing (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2173  /* One trial: the work before the timed sequence, the timed sequence, the
2174   * work after it. Prints nothing. */
2175  static void run_trial(struct tw *w, const struct trial *p, struct trec *r, volatile uint64_t *sink)
2176  {
2177      uint64_t expect = 0;
2178      int old = -1;
2179
2180      if (p-&gt;count == CS_CLOSED &amp;&amp; w-&gt;group_open)
2181          count_close(w);
2182      else if (p-&gt;count != CS_CLOSED &amp;&amp; !w-&gt;group_open)
2183          count_open(w);
2184      r-&gt;state = p-&gt;count != CS_CLOSED &amp;&amp; w-&gt;open_fail ? CS_FAIL : p-&gt;count;
2185      r-&gt;close_fail = w-&gt;close_fail;
2186      w-&gt;close_fail = 0;
2187      w-&gt;read_fail = 0;
2188
2189      /* The last old read of the trial must leave the sum of its range in the
2190       * sink. The sink starts with another value, so an old value cannot pass. */
2191      for (int i = 0; i &lt; r-&gt;nw; i++)
2192          if (kernels[r-&gt;win[i].k].type == T_OLDREAD)
2193              old = i;
2194      if (old &gt;= 0) {
2195          expect = w-&gt;v * (r-&gt;win[old].size / 8);
2196          *sink = expect + 1;
2197      }
2198</pre></td><td valign="top"><ul><li>Lines 2180 to 2183 put the counter group into the counter state of this trial. The counter state is the field <code>count</code> of a plan line: <code>closed</code>, <code>open</code> or <code>read</code>. For <code>closed</code> an open group is closed. For <code>open</code> or <code>read</code> a closed group is opened.</li><li>Line 2184: the record keeps this state, or <code>fail</code> when counters are wanted and an event did not open.</li><li>Lines 2185 to 2187 move the number of failed closes into the record and set the two failure counts of the worker to 0.</li><li>Lines 2189 to 2197 prepare a check of the old read kernel. <code>old</code> is the last window of the trial whose kernel has the type T_OLDREAD. Every 8-byte word of the buffer holds <code>w-&gt;v</code>. So this kernel must return <code>w-&gt;v</code> times the number of words of its range. The sink is set to this value plus 1, so that a value from an earlier call cannot pass the check.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2199      page_read(w, r, 0);
2200      switches(w, r, 0);
2201      r-&gt;cpu[0] = tcpu(w);
2202  /* bwx10+ */
2203      /* --hot-copy selects the other function. The statement after this block
2204       * is the else branch. */
2205      if (plan.hot_copy)
2206          timed_sequence_hot(w, r, p-&gt;count == CS_READ, sink);
2207      else
2208  /* bwx10- */
2209      timed_sequence(w, r, p-&gt;count == CS_READ, sink);
2210      r-&gt;cpu[1] = tcpu(w);
2211      switches(w, r, 1);
2212      page_read(w, r, 1);
2213      r-&gt;sink_ok = old &lt; 0 ? -1 : *sink == expect;
2214      r-&gt;read_fail = w-&gt;read_fail;
2215  }
2216</pre></td><td valign="top"><ul><li>Before the timed sequence: page state (<code>page_read</code>), context switches (<code>switches</code>), thread CPU time (<code>tcpu</code>, line 1945).</li><li>Lines 2205 to 2209 run the timed sequence: <code>timed_sequence_hot</code> (line 2056) with the option <code>--hot-copy</code>, otherwise <code>timed_sequence</code> (line 1995). Line 2209 is the else branch of the <code>if</code> at line 2205. The clock reads that time the windows are inside these two functions.</li><li>The third argument is 1 for the counter state <code>read</code>. Then the timed sequence also reads the counter group at the boundaries of the target windows.</li><li>After the timed sequence: the same three readings in the reverse order.</li><li><code>sink_ok</code> becomes 1 when the sink holds the expected sum, 0 when it does not, and -1 when the trial ran no old read kernel.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>trial_windows</code>: number of windows of one trial (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2217  static int trial_windows(const struct trial *p)
2218  {
2219      return (p-&gt;prev.k &gt;= 0) + 4 * (p-&gt;pfx.k &gt;= 0) + (p-&gt;pred.k &gt;= 0) + p-&gt;nwin;
2220  }
2221</pre></td><td valign="top">A trial has up to four phases, in this order: previous activity (1 window), prefix (4 windows), predecessor (1 window) and target (<code>nwin</code> windows). The plan may leave out each of the first three. Then the field <code>k</code> of that part is -1. The function adds the windows of the phases that the trial has.</td></tr>
<tr><td colspan="2"><b>Function <code>window_bins</code>: bin storage of one target window (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2222  /* Bins that one target window can close: one per 10 ms that ends inside the
2223   * window, one at the end of the window, and one spare. */
2224  static int window_bins(const struct trial *p)
2225  {
2226      return p-&gt;bins ? (int)(p-&gt;win_ms / 10) + 2 : 0;
2227  }
2228</pre></td><td valign="top">Returns the number of bins that one target window can fill: the window length <code>win_ms</code> divided by 10 (rounded down), plus 2. The requested length of a bin is 10 ms (BIN_NS, line 1813). For a trial without bins it returns 0.</td></tr>
<tr><td colspan="2"><b>Function <code>set_windows</code>: fills the plan fields of the windows (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2229  /* Fills the plan part of the windows of one trial. bin: storage for
2230   * nwin * window_bins(p) bins. */
2231  static void set_windows(const struct trial *p, struct win *win, struct bin *bin)
2232  {
2233      const struct {
2234          const struct part *part;
2235          int phase, n;
2236      } ph[4] = { { &amp;p-&gt;prev, PH_PREV, 1 }, { &amp;p-&gt;pfx, PH_PREFIX, 4 }, { &amp;p-&gt;pred, PH_PRED, 1 }, { &amp;p-&gt;tgt, PH_TARGET, p-&gt;nwin } };
2237      struct win *x = win;
2238      for (int i = 0; i &lt; 4; i++) {
2239          const struct part *part = ph[i].part;
2240          if (part-&gt;k &lt; 0)
2241              continue;
2242          for (int j = 0; j &lt; ph[i].n; j++, x++) {
2243              memset(x, 0, sizeof *x);
2244              x-&gt;k = part-&gt;k;
2245              x-&gt;phase = ph[i].phase;
2246              x-&gt;widx = j;
2247              x-&gt;size = part-&gt;size;
2248              x-&gt;passes = CHECK_BYTES / part-&gt;size ? CHECK_BYTES / part-&gt;size : 1;
2249              x-&gt;dur_ns = (ph[i].phase == PH_TARGET ? p-&gt;win_ms : part-&gt;ms / ph[i].n) * 1000000L;
2250              if (ph[i].phase == PH_TARGET &amp;&amp; p-&gt;bins) {
2251                  x-&gt;bin_cap = window_bins(p);
2252                  x-&gt;bin = bin + (size_t)j * (size_t)x-&gt;bin_cap;
2253              }
2254          }
2255      }
2256  }
2257</pre></td><td valign="top"><ul><li>Goes through the four phases of a trial in the order of the run: previous activity, prefix, predecessor, target. It skips a phase that the plan leaves out.</li><li>For each window it sets the kernel <code>k</code>, the phase, the window number <code>widx</code> inside the phase (from 0) and the range <code>size</code> in bytes.</li><li><code>passes</code> is the number of kernel calls between two clock reads: 8 MiB (CHECK_BYTES, line 130) divided by <code>size</code>, rounded down, and at least 1.</li><li><code>dur_ns</code> is the requested length of the window in ns. A target window gets <code>win_ms</code>. Every other window gets the time of its phase divided by the number of windows of the phase.</li><li>A target window of a trial with bins gets its own part of the bin storage: <code>bin_cap</code> bins.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>alloc_records</code>: one memory block for all trial records (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2258  /* The record storage of all trials: one block, sized from the plan, written
2259   * once here so that no page of it is first touched during a trial.
2260   * plan_trial() has filled recsz and has checked its bound. */
2261  static void alloc_records(struct tw *w)
2262  {
2263      char *mem = malloc(recsz.bytes);
2264      if (!mem) {
2265          fprintf(stderr, "no memory for %zu bytes of records\n", recsz.bytes);
2266          exit(2);
2267      }
2268      memset(mem, 0, recsz.bytes);
2269      /* gcc joins malloc and memset into calloc, and calloc does not write a
2270       * fresh block. One volatile store per page is the first touch. */
2271      for (size_t at = 0; at &lt; recsz.bytes; at += (size_t)page_bytes)
2272          ((volatile char *)mem)[at] = 0;
2273      ((volatile char *)mem)[recsz.bytes - 1] = 0;
2274      rec = (struct trec *)mem;</pre></td><td valign="top"><ul><li>Allocates one block of <code>recsz.bytes</code> bytes with <code>malloc</code>. It holds the records of all trials. <code>plan_trial</code> (line 2663) computed this size from the plan. Without memory the process ends with status 2.</li><li>Fills the block with 0 (<code>memset</code>). Then it stores one byte in every page of the block and in its last byte, through a pointer to <code>volatile</code> data.</li><li>The comment gives the reason for the extra stores: gcc joins <code>malloc</code> and <code>memset</code> into <code>calloc</code>, and <code>calloc</code> does not write a fresh block.</li><li>Effect: every page of the block gets its first touch here, and not during a trial.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2275      struct win *win = (struct win *)(rec + plan.n);
2276  /* bwx10+ */
2277      /* --rec-pad: win[] starts this many bytes later. With 0 nothing moves. */
2278      win = (struct win *)((char *)win + plan.rec_pad);
2279  /* bwx10- */
2280      struct counts *cnt = (struct counts *)(win + recsz.windows);
2281      struct bin *bin = (struct bin *)(cnt + recsz.counts);
2282      if (plan.trace)
2283          w-&gt;log = (struct tev *)(bin + recsz.bins);
2284      for (int i = 0; i &lt; plan.n; i++) {
2285          const struct trial *p = &amp;plan.tr[i];
2286          rec[i].win = win;
2287          rec[i].nw = trial_windows(p);
2288          rec[i].cnt = p-&gt;count == CS_READ ? cnt : NULL;
2289          set_windows(p, win, bin);
2290          win += rec[i].nw;
2291          bin += (size_t)p-&gt;nwin * (size_t)window_bins(p);
2292          if (p-&gt;count == CS_READ)
2293              cnt += p-&gt;nwin + 1;
2294      }
2295  }
2296</pre></td><td valign="top"><ul><li>Divides the block into arrays, in this order: the trial records (<code>rec</code>, one per trial), the window records, the counter readings, the bins, and with <code>--trace</code> the event log.</li><li>The option <code>--rec-pad</code> moves the start of the window records by that many bytes (line 2278). The default is 0 bytes.</li><li>The loop gives each trial its part of each array and calls <code>set_windows</code> for it. <code>nw</code> is the number of windows of the trial.</li><li>Only a trial with the counter state <code>read</code> gets counter readings: <code>nwin</code> + 1 of them.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>print_s</code>: the S row of one trial (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2297  static void print_s(int i)
2298  {
2299      const struct trial *p = &amp;plan.tr[i];
2300      printf("S");
2301      for (int f = 0; f &lt; PLAN_FIELDS; f++)
2302          printf(",%s", p-&gt;f[f]);
2303      printf(",%s,%s\n", i ? plan.tr[i - 1].f[1] : "none", i ? plan.tr[i - 1].f[6] : "none");
2304  }
2305</pre></td><td valign="top">Prints <code>S</code> and the 11 fields of the plan line of trial <code>i</code>, as text from the plan file. Then it prints the fields <code>cond</code> and <code>tgt</code> of the trial before it. For trial 0 it prints <code>none</code> two times.</td></tr>
<tr><td colspan="2"><b>Function <code>print_p8</code>: the P row of the trial mode</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2306  static void print_p8(int i, const char *when, const struct page *pg, const long long vm[4])
2307  {
2308      printf("P,%d,%s", i, when);
2309      print_na(pg-&gt;kb_total);
2310      print_na(pg-&gt;kb_huge);
2311      for (int k = 0; k &lt; 4; k++)
2312          print_na(vm[k]);
2313      printf("\n");
2314  }
2315</pre></td><td valign="top">Prints <code>P</code>, the trial number, the word <code>pre</code> or <code>post</code>, the two page values of the buffer in kB and the four vmstat counters. <code>print_na</code> (line 1562) prints <code>NA</code> for a negative value. The P rows of the test files have other columns: round, position, thread and buffer letter come first. Those rows come from <code>print_p</code> (line 1570), not from this function.</td></tr>
<tr><td colspan="2"><b>Function <code>emit_trial</code>: prints all result rows of one trial (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2316  /* All rows of one trial after its S row. */
2317  static void emit_trial(struct tw *w, int i)
2318  {
2319      const struct trial *p = &amp;plan.tr[i];
2320      const struct trec *r = &amp;rec[i];
2321      int g = r-&gt;nw - p-&gt;nwin; /* index of target window 0 */
2322      int64_t max_gap = -1;
2323
2324      tev_add(w, EV_OUTPUT, 0, 0);
2325      print_p8(i, "pre", &amp;r-&gt;pg[0], r-&gt;vm[0]);
2326      for (int k = 0; k &lt; r-&gt;nw; k++) {
2327          const struct win *x = &amp;r-&gt;win[k];
2328          printf("W,%d,%s,%d,%s,%lu,%lu,%lld,%lld\n", i, phase_name[x-&gt;phase], x-&gt;widx, kernels[x-&gt;k].name,
2329                 (unsigned long)x-&gt;size, (unsigned long)x-&gt;bytes, (long long)(x-&gt;t_start - t_base_ns),
2330                 (long long)(x-&gt;t_end - t_base_ns));
2331          if (k &amp;&amp; x-&gt;t_start - r-&gt;win[k - 1].t_end &gt; max_gap)
2332              max_gap = x-&gt;t_start - r-&gt;win[k - 1].t_end;
2333      }
2334      for (int k = g; k &lt; r-&gt;nw; k++)
2335          for (int b = 0; b &lt; r-&gt;win[k].nbin; b++)
2336              printf("B,%d,%d,%d,%lld,%lu\n", i, r-&gt;win[k].widx, b, (long long)(r-&gt;win[k].bin[b].t_end - t_base_ns),
2337                     (unsigned long)r-&gt;win[k].bin[b].bytes);</pre></td><td valign="top"><ul><li><code>g</code> is the index of target window 0 in the window list of the trial.</li><li>P row <code>pre</code>: the page state before the timed sequence (<code>print_p8</code>).</li><li>W rows, one per window: trial, phase, window number, kernel name, range size, bytes, start time and end time. The bytes are the range size times the number of kernel calls. The times are in ns since the process start.</li><li><code>max_gap</code> becomes the longest time between the end clock read of one window and the start clock read of the next window.</li><li>B rows, one per bin of each target window: trial, window number, bin number, end time of the bin, bytes since the start of the window.</li><li>The function prints bytes and times. It computes no rate.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2338      for (int k = 0; r-&gt;cnt &amp;&amp; k &lt; p-&gt;nwin; k++) {
2339          const struct counts *c0 = &amp;r-&gt;cnt[k], *c1 = &amp;r-&gt;cnt[k + 1];
2340          int group = w-&gt;t.group_fd &gt;= 0 &amp;&amp; !r-&gt;read_fail;
2341          printf("C,%d,%d", i, k);
2342          if (group)
2343              printf(",%llu,%llu", (unsigned long long)(c1-&gt;enabled - c0-&gt;enabled),
2344                     (unsigned long long)(c1-&gt;running - c0-&gt;running));
2345          else
2346              printf(",NA,NA");
2347          printf(",%llu", (unsigned long long)(c1-&gt;cpu_ns - c0-&gt;cpu_ns));
2348          for (int e = 0; e &lt; cfg.nev; e++) {
2349              int at = w-&gt;t.ev_pos[e];
2350              if (!group || at &lt; 0)
2351                  printf(",NA");
2352              else
2353                  printf(",%llu", (unsigned long long)(c1-&gt;val[at] - c0-&gt;val[at]));
2354          }
2355          printf("\n");
2356      }
2357      print_p8(i, "post", &amp;r-&gt;pg[1], r-&gt;vm[1]);
2358
2359      if (r-&gt;pg[0].kb_huge &lt; 0 || r-&gt;pg[1].kb_huge &lt; 0)
2360          printf("X,%d,coverage_na,the buffer has no exact entry in /proc/self/smaps\n", i);
2361      if (r-&gt;close_fail)
2362          printf("X,%d,count_close,%d counter descriptors did not close\n", i, r-&gt;close_fail);
2363      if (r-&gt;state == CS_FAIL)
2364          printf("X,%d,count_open,%d of %d events did not open; first: %s\n", i, w-&gt;open_fail, cfg.nev, w-&gt;open_err);
2365      if (r-&gt;read_fail)
2366          printf("X,%d,count_read,%d reads of the counter group failed\n", i, r-&gt;read_fail);
2367      if (r-&gt;cnt &amp;&amp; w-&gt;t.group_fd &gt;= 0 &amp;&amp; !r-&gt;read_fail) {
2368          int m = first_multiplexed(r-&gt;cnt, p-&gt;nwin);
2369          if (m &gt;= 0)
2370              printf("X,%d,count_multiplexed,target window %d: running_ns %llu below enabled_ns %llu\n", i, m,
2371                     (unsigned long long)(r-&gt;cnt[m + 1].running - r-&gt;cnt[m].running),
2372                     (unsigned long long)(r-&gt;cnt[m + 1].enabled - r-&gt;cnt[m].enabled));
2373      }
2374      if (r-&gt;sink_ok == 0)
2375          printf("X,%d,sink,the last old read did not leave the sum of its range in the sink\n", i);
2376</pre></td><td valign="top"><ul><li>C rows, only for a trial with counter readings (counter state <code>read</code>): one row per target window. Each value is the difference of two readings. The first reading is taken before the start clock read of the window, the second after its end clock read.</li><li>Columns of a C row: trial, window number, enabled time, running time, thread CPU time (all in ns), then one value per event.</li><li><code>NA</code> stands for the two times and for every event when no group is open or a group read failed in the trial. It also stands for an event that did not open.</li><li>The C rows of the test files have other columns: round, position, kernel name, thread index and CPU come first. Those rows come from <code>main</code> (lines 3086 to 3103), not from this function.</li><li>P row <code>post</code>: the page state after the timed sequence.</li><li>X rows report problems, one row per kind. <code>coverage_na</code>: smaps has no exact entry for the buffer. <code>count_close</code>, <code>count_open</code> and <code>count_read</code>: a close, an open or a read of the counter group failed. <code>count_multiplexed</code>: the result of <code>first_multiplexed</code>. <code>sink</code>: the check of the old read kernel failed.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2377      printf("E,%d,%lld,%llu", i, (long long)(r-&gt;win[r-&gt;nw - 1].t_end - r-&gt;win[0].t_start),
2378             (unsigned long long)(r-&gt;cpu[1] - r-&gt;cpu[0]));
2379      if (r-&gt;nvcsw[0] &lt; 0 || r-&gt;nvcsw[1] &lt; 0)
2380          printf(",NA,NA");
2381      else
2382          printf(",%ld,%ld", r-&gt;nvcsw[1] - r-&gt;nvcsw[0], r-&gt;nivcsw[1] - r-&gt;nivcsw[0]);
2383      print_na(g ? r-&gt;win[g].t_start - r-&gt;win[g - 1].t_end : -1);
2384      print_na(max_gap);
2385      if (r-&gt;sink_ok &lt; 0)
2386          printf(",NA");
2387      else
2388          printf(",%d", r-&gt;sink_ok);
2389      printf(",%s\n", count_name[r-&gt;state]);
2390
2391      for (long n = 0; n &lt; w-&gt;nlog; n++) {
2392          const struct tev *e = &amp;w-&gt;log[n];
2393          if (e-&gt;ev == EV_KERNEL_FIRST)
2394              printf("TR,%d,%ld,%s:%s:%d,%lld\n", i, n, event_name[e-&gt;ev], phase_name[e-&gt;phase], e-&gt;widx,
2395                     (long long)(e-&gt;t - t_base_ns));
2396          else
2397              printf("TR,%d,%ld,%s,%lld\n", i, n, event_name[e-&gt;ev], (long long)(e-&gt;t - t_base_ns));
2398      }
2399      if (w-&gt;ndrop)
2400          printf("# trace_dropped,%d,%ld\n", i, w-&gt;ndrop);
2401      /* --trace: minor page faults of the worker between the two rusage reads.
2402       * Above 0: a page was first touched inside the timed sequence. */
2403      if (w-&gt;log)
2404          printf("# minflt,%d,%ld\n", i, r-&gt;minflt[0] &lt; 0 || r-&gt;minflt[1] &lt; 0 ? -1 : r-&gt;minflt[1] - r-&gt;minflt[0]);
2405      fflush(stdout);
2406  }
2407</pre></td><td valign="top"><ul><li>E row, one per trial. The header (line 2478) names its columns. <code>wall_ns</code>: from the start of the first window to the end of the last window. <code>cpu_ns</code>: thread CPU time between the two <code>tcpu</code> calls of <code>run_trial</code>.</li><li>The other columns of the E row: voluntary and involuntary context switches, the gap in ns between target window 0 and the window before it, <code>max_gap</code>, <code>sink_ok</code> and the counter state. <code>NA</code> stands for a value that could not be read or that the trial does not have.</li><li>TR rows, only with <code>--trace</code>: one row per event of the trace, with its time in ns since the process start.</li><li><code># trace_dropped</code>: printed when events did not fit into the trace. The trace keeps 1048576 events per trial (TRACE_CAP, line 1814).</li><li><code># minflt</code>, only with <code>--trace</code>: the minor page faults of the worker between the two <code>switches</code> calls, or -1 when a reading failed.</li><li><code>fflush</code> writes the buffered rows to the output before the next trial starts.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>evict_step</code>: writes other memory before the first trial (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2408  /* bwx11+ */
2409  /*
2410   * --evict-mb N. evict_step() maps N MiB of anonymous private memory (plain
2411   * mmap, no madvise), stores one 8-byte word to every 64 B line in ascending
2412   * order, in two passes, and unmaps the range. The stores go through a
2413   * volatile pointer, so gcc keeps every one of them and does not call memset.
2414   * Purpose: the lines of the benchmark buffer leave the caches. The first
2415   * touch wrote them, so they were dirty. The next read brings them back from
2416   * memory, clean.
2417   * trial_worker() calls it once, after the first touch of the buffer and of
2418   * the record block and before the first trial. No timed sequence holds it.
2419   * evict_t holds one clock read before the mmap and one after the munmap.
2420   * Returns 0, or -1 with the text of the error in evict_err.
2421   * These definitions stand after timed_sequence_hot() and after every other
2422   * variable of the trial mode, so nothing before them moves.
2423   */
2424  static long evict_mb;      /* --evict-mb: 0 = no evict step */
2425  static int64_t evict_t[2]; /* CLOCK_MONOTONIC, ns */
2426  static char evict_err[160];
2427</pre></td><td valign="top"><ul><li>The comment describes the evict step of the option <code>--evict-mb N</code>. It gives the purpose: the lines of the benchmark buffer leave the caches, so the next read brings them back from memory.</li><li><code>evict_mb</code> holds N in MiB. <code>evict_t</code> holds the two clock readings around the step, and <code>evict_err</code> the text of an error.</li><li>The comment lines <code>bwx11+</code> (2408) and <code>bwx11-</code> (2448) mark this text as added by bwx11.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2428  __attribute__((noinline)) static int evict_step(void)
2429  {
2430      size_t len = (size_t)evict_mb &lt;&lt; 20;
2431      evict_t[0] = now_ns();
2432      volatile uint64_t *m = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
2433      if (m == MAP_FAILED) {
2434          snprintf(evict_err, sizeof evict_err, "mmap of %ld MiB failed: %s", evict_mb, strerror(errno));
2435          return -1;
2436      }
2437      for (int pass = 0; pass &lt; 2; pass++)
2438          for (size_t i = 0; i &lt; len / 8; i += 8)
2439              m[i] = (uint64_t)i + (uint64_t)pass + 1;
2440      if (munmap((void *)m, len) != 0) {
2441          snprintf(evict_err, sizeof evict_err, "munmap of %ld MiB failed: %s", evict_mb, strerror(errno));
2442          return -1;
2443      }
2444      evict_t[1] = now_ns();
2445      return 0;
2446  }
2447
2448  /* bwx11- */</pre></td><td valign="top"><ul><li>Reads the clock (<code>now_ns</code>, line 327). Maps <code>evict_mb</code> MiB of new anonymous private memory with <code>mmap</code>.</li><li>Stores one 8-byte word at the start of every 64 B cache line of this memory, from the lowest address up. <code>i</code> counts 8-byte words, so <code>i += 8</code> is a step of 64 B. It does this 2 times over the whole range.</li><li><code>m</code> points to <code>volatile</code> data, so the compiler must keep every store.</li><li>Unmaps the memory and reads the clock again.</li><li>Returns 0. When <code>mmap</code> or <code>munmap</code> fails, it returns -1 and leaves the error text in <code>evict_err</code>.</li><li>No timed window holds this step. <code>trial_worker</code> calls it once, before the first trial (line 2502).</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>trial_worker</code>: the one worker thread of the trial mode</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2449  static void *trial_worker(void *arg)
2450  {
2451      struct tw *w = arg;
2452      volatile uint64_t sink = 0;
2453      int madvise_ok;
2454
2455      pin_cpu(cfg.cpus[0]);
2456      if (sched_getcpu() != cfg.cpus[0]) {
2457          fprintf(stderr, "the worker runs on CPU %d, not on CPU %d\n", sched_getcpu(), cfg.cpus[0]);
2458          exit(2);
2459      }
2460      w-&gt;v = ((uint64_t)getpid() + 1) * 0x9E3779B97F4A7C15ULL;
2461      w-&gt;t.group_fd = -1;
2462      w-&gt;t.a = alloc_buf();
2463      /* alloc_buf() does not return the result of its madvise. The same request
2464       * again gives it. */
2465      madvise_ok = madvise(w-&gt;t.a, buf_len(), cfg.use_thp ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) == 0;
2466      k_write(w-&gt;t.a, cfg.bytes / 8, w-&gt;v); /* first touch by the pinned worker */
2467      alloc_records(w);
2468      w-&gt;last_t = t_base_ns;
2469</pre></td><td valign="top"><ul><li>Pins the thread to the one CPU of <code>--cpus</code> (<code>pin_cpu</code>, line 415). Then it asks Linux on which CPU it runs (<code>sched_getcpu</code>). If this is another CPU, the process ends with status 2.</li><li><code>w-&gt;v</code> is the value for every 8-byte word of the buffer: the process ID (<code>getpid</code>) plus 1, times a fixed 64-bit constant.</li><li>Maps the buffer with <code>alloc_buf</code> (line 434). Line 2465 repeats the <code>madvise</code> request of <code>alloc_buf</code> only to learn its result (<code>madvise_ok</code>).</li><li>First touch: the pinned worker writes the whole buffer once with <code>k_write</code> (line 531).</li><li><code>alloc_records</code> allocates the record block and touches every page of it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2470      printf("# bwx8 trial mode: GB = 1e9 bytes; times are whole ns since process start on CLOCK_MONOTONIC\n"
2471             "# S,trial,cond,rep,prev,pfx,pred,tgt,nwin,win_ms,count,bins,prev_cond,prev_tgt\n"
2472             "# P,trial,when,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n"
2473             "# W,trial,phase,widx,kernel,pass_bytes,bytes,t_start_ns,t_end_ns\n"
2474             "# B,trial,widx,bin,t_end_ns,bytes_since_window_start\n"
2475             "# C,trial,widx,enabled_ns,running_ns,cputime_ns");
2476      for (int e = 0; e &lt; cfg.nev; e++)
2477          printf(",%s", cfg.ev_name[e]);
2478      printf("\n# E,trial,wall_ns,cpu_ns,nvcsw,nivcsw,gap_ns,max_boundary_gap_ns,sink_ok,count_state\n"
2479             "# X,trial,code,text\n"
2480             "# TR,trial,n,event,t_ns; t_ns of an event that is not a clock read is the time of the clock read before it\n");
2481      printf("M,mode,trial\nM,cpu,%d\nM,ctl_cpu,%d\nM,bytes,%lu\nM,thp,%s\nM,madvise_ok,%d\nM,check_bytes,%lu\nM,kernels,%s\n",
2482             cfg.cpus[0], plan.ctl_cpu, (unsigned long)cfg.bytes, cfg.use_thp ? "madvise" : "nohugepage", madvise_ok,
2483             (unsigned long)CHECK_BYTES, STANDIN ? "STAND-IN" : "aarch64");
2484      printf("M,plan_fnv1a64,%016llx\nM,ntrials,%d\nM,rec_windows,%zu\nM,rec_bins,%zu\nM,rec_counts,%zu\nM,rec_trace,%zu\n"
2485             "M,rec_bytes,%zu\nM,trace,%d\n",
2486             (unsigned long long)plan.hash, plan.n, recsz.windows, recsz.bins, recsz.counts, recsz.trace, recsz.bytes,
2487             plan.trace);
2488  /* bwx10+ */
2489      /* Addresses in hex without "0x", as in the K rows. rec_addr: the record
2490       * block. win_addr: win[0] of trial 0. stack_addr: the sink of the worker. */
2491      printf("M,rec_pad,%zu\nM,hot_copy,%d\nM,rec_addr,%lx\nM,win_addr,%lx\nM,win_size,%zu\nM,stack_addr,%lx\nM,buf_addr,%lx\n"
2492             "M,tw_addr,%lx\n",
2493             plan.rec_pad, plan.hot_copy, (unsigned long)(uintptr_t)rec, (unsigned long)(uintptr_t)rec[0].win,
2494             sizeof(struct win), (unsigned long)(uintptr_t)&amp;sink, (unsigned long)(uintptr_t)w-&gt;t.a,
2495             (unsigned long)(uintptr_t)w);
2496  /* bwx10- */</pre></td><td valign="top"><ul><li>Lines 2470 to 2480 print the header: one <code>#</code> line with the column names for each row kind of the trial mode (S, P, W, B, C, E, X, TR). The first line still says <code>bwx8</code>, the version that added the trial mode.</li><li>Lines 2481 to 2483 print M rows of the form <code>M,name,value</code>: the mode, the worker CPU, the CPU of the controlling thread (the thread of <code>trial_main</code>), the buffer size and the page policy (<code>madvise</code> or <code>nohugepage</code>). Then <code>madvise_ok</code>, CHECK_BYTES, and <code>aarch64</code> or <code>STAND-IN</code>.</li><li>Lines 2484 to 2487: a checksum of the plan file, the number of trials, the sizes of the record block and whether the trace is on.</li><li>Lines 2491 to 2495 (added by bwx10) print <code>rec_pad</code>, <code>hot_copy</code> and the size of one window record. They also print five addresses in hexadecimal: the record block, the first window record, the sink, the buffer and the worker structure.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2497  /* bwx11+ */
2498      /* The evict step. The buffer and the record block are first touched, and
2499       * no trial has started. With --evict-mb 0 no call is made. A failure
2500       * ends the process here: the X row is the last row. */
2501      printf("M,evict_mb,%ld\n", evict_mb);
2502      if (evict_mb &gt; 0 &amp;&amp; evict_step() != 0) {
2503          printf("X,-1,evict,%s\n", evict_err);
2504          fflush(stdout);
2505          exit(2);
2506      }
2507      printf("M,evict_ns,%lld\n", (long long)(evict_t[1] - evict_t[0]));
2508      if (evict_mb &gt; 0 &amp;&amp; plan.trace)
2509          printf("TR,-1,0,evict_start,%lld\nTR,-1,1,evict_end,%lld\n", (long long)(evict_t[0] - t_base_ns),
2510                 (long long)(evict_t[1] - t_base_ns));
2511  /* bwx11- */
2512      if (cfg.pmu_type &lt; 0)
2513          printf("M,pmu_type,none\n");
2514      else
2515          printf("M,pmu_type,%ld\n", cfg.pmu_type);
2516      printf("M,events,%s", cfg.nev ? "" : "none");
2517      for (int e = 0; e &lt; cfg.nev; e++)
2518          printf("%s%s=0x%llx", e ? ";" : "", cfg.ev_name[e], (unsigned long long)cfg.ev_code[e]);
2519      printf("\n");
2520      for (int i = 0; i &lt; plan.npair; i++) {
2521          char *eq = strchr(plan.pair[i], '=');
2522          printf("M,plan.%.*s,%s\n", (int)(eq - plan.pair[i]), plan.pair[i], eq + 1);
2523      }
2524      for (int k = 0; k &lt; K_COUNT; k++) {
2525          int used = 0;
2526          for (int i = 0; i &lt; plan.n &amp;&amp; !used; i++) {
2527              const struct trial *p = &amp;plan.tr[i];
2528              used = p-&gt;prev.k == k || p-&gt;pfx.k == k || p-&gt;pred.k == k || p-&gt;tgt.k == k;
2529          }
2530          if (used)
2531              printf("K,%s,%lx,%lu\n", kernels[k].name, (unsigned long)(uintptr_t)kernels[k].fn,
2532                     (unsigned long)((uintptr_t)kernels[k].fn % 64));
2533      }
2534      if (!madvise_ok)
2535          printf("X,-1,madvise,the page policy request failed\n");
2536</pre></td><td valign="top"><ul><li>Evict step (added by bwx11): prints <code>M,evict_mb</code>. With a value above 0 it calls <code>evict_step</code>. On an error it prints an X row and the process ends with status 2.</li><li><code>M,evict_ns</code> is the time between the two clock reads of the step. It is 0 when no step ran. With a step and <code>--trace</code>, two TR rows give its start and its end.</li><li><code>M,pmu_type</code> and <code>M,events</code>: the counter settings, or <code>none</code>.</li><li>One row <code>M,plan.&lt;key&gt;,&lt;value&gt;</code> for each pair of line 2 of the plan file.</li><li>K rows, one per kernel that a trial of the plan uses: name, address of the function in hexadecimal, and this address modulo 64.</li><li>An X row when the <code>madvise</code> request of line 2465 failed.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2537      for (int i = 0; i &lt; plan.n; i++) {
2538          w-&gt;nlog = w-&gt;ndrop = 0;
2539          w-&gt;cur_phase = -1;
2540          tev_add(w, EV_OUTPUT, 0, 0);
2541          print_s(i);
2542          fflush(stdout);
2543          run_trial(w, &amp;plan.tr[i], &amp;rec[i], &amp;sink);
2544          emit_trial(w, i);
2545      }
2546      if (w-&gt;group_open)
2547          count_close(w);
2548      if (w-&gt;close_fail)
2549          printf("X,-1,count_close,%d counter descriptors did not close\n", w-&gt;close_fail);
2550      fflush(stdout);
2551      return NULL;
2552  }
2553</pre></td><td valign="top"><ul><li>The loop runs the trials in the order of the plan. Per trial it clears the trace, prints the S row (<code>print_s</code>), flushes the output buffer (<code>fflush</code>), runs the trial (<code>run_trial</code>) and prints the result rows (<code>emit_trial</code>).</li><li><code>run_trial</code> prints nothing. So the process writes no output inside a timed sequence.</li><li>After the last trial it closes the counter group if it is open. It prints an X row when a <code>close</code> failed.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>plan_bad</code>: reports a defect of the plan file (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2554  static void plan_bad(int line, const char *fmt, ...)
2555  {
2556      va_list ap;
2557      fprintf(stderr, "bad plan %s, line %d: ", plan.path, line);
2558      va_start(ap, fmt);
2559      vfprintf(stderr, fmt, ap);
2560      va_end(ap);
2561      fprintf(stderr, "\n");
2562      exit(2);
2563  }
2564</pre></td><td valign="top">Writes <code>bad plan &lt;file&gt;, line &lt;n&gt;:</code> and a message to stderr. The message is built like a <code>printf</code> text from <code>fmt</code> and the arguments after it. Then the process ends with status 2.</td></tr>
<tr><td colspan="2"><b>Function <code>plan_long</code>: a whole number of the plan (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2565  /* A whole number in [lo, hi] made of digits only. */
2566  static int plan_long(const char *s, long lo, long hi, long *out)
2567  {
2568      char *end;
2569      if (*s &lt; '0' || *s &gt; '9')
2570          return 0;
2571      errno = 0;
2572      long v = strtol(s, &amp;end, 10);
2573      if (*end != '\0' || errno != 0 || v &lt; lo || v &gt; hi)
2574          return 0;
2575      *out = v;
2576      return 1;
2577  }
2578</pre></td><td valign="top">Accepts a text that holds decimal digits only and whose value lies from <code>lo</code> to <code>hi</code>. Then it stores the value in <code>*out</code> and returns 1. For any other text it returns 0. The caller then reports the defect with <code>plan_bad</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>plan_size</code>: a size of the plan (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2579  /* A whole number above 0 with an optional K, M or G. */
2580  static int plan_size(const char *s, uint64_t *out)
2581  {
2582      char *end;
2583      int shift = 0;
2584      if (*s &lt; '0' || *s &gt; '9')
2585          return 0;
2586      errno = 0;
2587      unsigned long long v = strtoull(s, &amp;end, 10);
2588      switch (*end) {
2589      case 'K': shift = 10; end++; break;
2590      case 'M': shift = 20; end++; break;
2591      case 'G': shift = 30; end++; break;
2592      }
2593      if (*end != '\0' || errno != 0 || v == 0 || v &gt; (UINT64_MAX &gt;&gt; shift))
2594          return 0;
2595      *out = (uint64_t)v &lt;&lt; shift;
2596      return 1;
2597  }
2598</pre></td><td valign="top">Accepts decimal digits with an optional capital letter <code>K</code>, <code>M</code> or <code>G</code> at the end (the number times 2^10, 2^20 or 2^30). The value must be above 0, and the size in bytes must fit into 64 bits. Then it stores the size in bytes in <code>*out</code> and returns 1. For any other text it returns 0.</td></tr>
<tr><td colspan="2"><b>Function <code>plan_part</code>: one kernel field of a plan line (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2599  /* "KERNEL@SIZE:MS" (with_ms, where "-" is also allowed) or "KERNEL@SIZE". */
2600  static void plan_part(int line, const char *what, const char *s, int with_ms, struct part *p)
2601  {
2602      char buf[96];
2603      p-&gt;k = -1;
2604      p-&gt;size = 0;
2605      p-&gt;ms = 0;
2606      if (with_ms &amp;&amp; !strcmp(s, "-"))
2607          return;
2608      if (strlen(s) &gt;= sizeof buf)
2609          plan_bad(line, "%s is too long", what);
2610      strcpy(buf, s);
2611      char *at = strchr(buf, '@'), *colon = at ? strchr(at, ':') : NULL;
2612      if (!at || with_ms != (colon != NULL))
2613          plan_bad(line, "%s '%s' is not %s", what, s, with_ms ? "'-' or KERNEL@SIZE:MS" : "KERNEL@SIZE");
2614      *at = '\0';
2615      if (colon)
2616          *colon = '\0';
2617      int k = 0;
2618      while (k &lt; K_COUNT &amp;&amp; strcmp(buf, kernels[k].name))
2619          k++;
2620      if (k == K_COUNT)
2621          plan_bad(line, "%s: unknown kernel '%s'", what, buf);
2622      if (kernels[k].type != T_READ &amp;&amp; kernels[k].type != T_OLDREAD)
2623          plan_bad(line, "%s: '%s' is not a read kernel", what, buf);
2624      if (!plan_size(at + 1, &amp;p-&gt;size) || p-&gt;size % 256 != 0 || p-&gt;size &gt; cfg.bytes)
2625          plan_bad(line, "%s: size '%s' must be a multiple of 256, above 0 and at most --bytes (%lu)", what, at + 1,
2626                   (unsigned long)cfg.bytes);
2627      if (colon &amp;&amp; !plan_long(colon + 1, 1, MAX_MS, &amp;p-&gt;ms))
2628          plan_bad(line, "%s: bad duration '%s' (whole ms from 1 to %ld)", what, colon + 1, MAX_MS);
2629      p-&gt;k = k;
2630  }
2631</pre></td><td valign="top"><ul><li>Trial mode only. The code of the trial mode starts at line 1795, in the rows above. The whole-chip test never calls this function. <code>main</code> does not enter the trial mode there (lines 2912 to 2914).</li><li>It reads one field of a plan line into <code>*p</code>: the index of the kernel in <code>kernels[]</code>, the size in bytes and the duration in ms.</li><li>With <code>with_ms</code> = 1 the field has the form <code>KERNEL@SIZE:MS</code>. The text <code>-</code> is also allowed. It means that this part is absent, and <code>p-&gt;k</code> stays -1. With <code>with_ms</code> = 0 the form is <code>KERNEL@SIZE</code>.</li><li>Checks: the text is shorter than 96 characters, the name is in <code>kernels[]</code>, the kernel is a read kernel, the size is above 0, a multiple of 256 bytes and at most <code>--bytes</code>, the duration is 1 ms to 3600000 ms (1 hour).</li><li>A defect goes to <code>plan_bad</code> (line 2554). It prints the plan path, the line number and a message to stderr and ends the process with status 2. <code>plan_size</code> and <code>plan_long</code> (lines 2566 to 2597) convert the numbers.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>plan_pairs</code>: line 2 of the plan file (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2632  /* Line 2: "# key=value key=value ...". bytes and cpu must equal the options. */
2633  static void plan_pairs(char *s)
2634  {
2635      int have_bytes = 0, have_cpu = 0;
2636      if (strncmp(s, "# ", 2))
2637          plan_bad(2, "the line must start with '# '");
2638      for (char *tok = s + 2, *sp; tok; tok = sp ? sp + 1 : NULL) {
2639          sp = strchr(tok, ' ');
2640          if (sp)
2641              *sp = '\0';
2642          char *eq = strchr(tok, '=');
2643          if (!eq || eq == tok || strchr(tok, ',') || plan.npair == MAX_PAIRS)
2644              plan_bad(2, "bad key=value pair '%s'", tok);
2645          plan.pair[plan.npair++] = tok;
2646          if (!strncmp(tok, "bytes=", 6)) {
2647              uint64_t b;
2648              if (!plan_size(eq + 1, &amp;b) || b != cfg.bytes)
2649                  plan_bad(2, "%s differs from --bytes %lu", tok, (unsigned long)cfg.bytes);
2650              have_bytes = 1;
2651          }
2652          if (!strncmp(tok, "cpu=", 4)) {
2653              long c;
2654              if (!plan_long(eq + 1, 0, MAX_USE_CPU, &amp;c) || c != cfg.cpus[0])
2655                  plan_bad(2, "%s differs from --cpus %d", tok, cfg.cpus[0]);
2656              have_cpu = 1;
2657          }
2658      }
2659      if (!have_bytes || !have_cpu)
2660          plan_bad(2, "bytes= and cpu= are needed");
2661  }
2662</pre></td><td valign="top"><ul><li>Trial mode only. The whole-chip test does not run it.</li><li>Line 2 of the plan file has the form <code># key=value key=value ...</code>. The function splits it at each space and keeps a pointer to every pair in <code>plan.pair</code>. At most 64 pairs are allowed.</li><li>The pair <code>bytes=</code> must equal <code>--bytes</code>. The pair <code>cpu=</code> must equal the first CPU of <code>--cpus</code>. Both pairs must be present. Otherwise <code>plan_bad</code> ends the process.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>plan_trial</code>: one trial line of the plan (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2663  static void plan_trial(int line, char *s)
2664  {
2665      char *f[PLAN_FIELDS];
2666      int nf = 0;
2667      long v;
2668      for (char *tok = s, *sp; tok; tok = sp ? sp + 1 : NULL) {
2669          sp = strchr(tok, ' ');
2670          if (sp)
2671              *sp = '\0';
2672          if (nf == PLAN_FIELDS || *tok == '\0')
2673              plan_bad(line, "%d fields separated by single spaces are needed", PLAN_FIELDS);
2674          f[nf++] = tok;
2675      }
2676      if (nf != PLAN_FIELDS)
2677          plan_bad(line, "%d fields separated by single spaces are needed, %d found", PLAN_FIELDS, nf);
2678      plan.tr = realloc(plan.tr, ((size_t)plan.n + 1) * sizeof *plan.tr);
2679      if (!plan.tr)
2680          plan_bad(line, "no memory");
2681      struct trial *p = &amp;plan.tr[plan.n];
2682      memcpy(p-&gt;f, f, sizeof f);
2683      if (!plan_long(f[0], 0, 1000000, &amp;v) || v != plan.n)
2684          plan_bad(line, "trial '%s': the trial numbers must be 0, 1, 2, ... (%d expected)", f[0], plan.n);
2685      if (strchr(f[1], ','))
2686          plan_bad(line, "cond '%s' holds a comma", f[1]);
2687      if (!plan_long(f[2], 1, 4, &amp;v))
2688          plan_bad(line, "rep '%s' is not 1 to 4", f[2]);
2689      plan_part(line, "prev", f[3], 1, &amp;p-&gt;prev);
2690      plan_part(line, "pfx", f[4], 1, &amp;p-&gt;pfx);
2691      plan_part(line, "pred", f[5], 1, &amp;p-&gt;pred);
2692      plan_part(line, "tgt", f[6], 0, &amp;p-&gt;tgt);</pre></td><td valign="top"><ul><li>Trial mode only. The whole-chip test does not run it.</li><li>Lines 2668 to 2677 split one trial line at single spaces into exactly 11 fields. Their names stand in <code>PLAN_LINE3</code> (line 1816): trial, cond, rep, prev, pfx, pred, tgt, nwin, win_ms, count, bins.</li><li>Lines 2678 to 2682 add one <code>struct trial</code> to the array <code>plan.tr</code> and keep the 11 field texts in it.</li><li>Lines 2683 to 2688 check the trial number (0, 1, 2, ... in file order), <code>cond</code> (no comma) and <code>rep</code> (1 to 4).</li><li>Lines 2689 to 2692: <code>plan_part</code> reads the four parts of the trial: previous activity (<code>prev</code>), prefix (<code>pfx</code>), predecessor (<code>pred</code>) and target (<code>tgt</code>). The first three may be <code>-</code>. The target has no duration field.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2693      if (p-&gt;pfx.k &gt;= 0 &amp;&amp; p-&gt;pfx.ms % 4 != 0)
2694          plan_bad(line, "pfx duration %ld ms is not a multiple of 4", p-&gt;pfx.ms);
2695      if (!plan_long(f[7], 1, MAX_NWIN, &amp;v))
2696          plan_bad(line, "nwin '%s' is not 1 to %d", f[7], MAX_NWIN);
2697      p-&gt;nwin = (int)v;
2698      if (!plan_long(f[8], 1, MAX_MS, &amp;p-&gt;win_ms))
2699          plan_bad(line, "win_ms '%s' is not 1 to %ld", f[8], MAX_MS);
2700      p-&gt;count = !strcmp(f[9], "closed") ? CS_CLOSED : !strcmp(f[9], "open") ? CS_OPEN : !strcmp(f[9], "read") ? CS_READ : -1;
2701      if (p-&gt;count &lt; 0)
2702          plan_bad(line, "count '%s' is not closed, open or read", f[9]);
2703      if (strcmp(f[10], "0") &amp;&amp; strcmp(f[10], "1"))
2704          plan_bad(line, "bins '%s' is not 0 or 1", f[10]);
2705      p-&gt;bins = f[10][0] == '1';
2706      plan.n++;
2707      /* The record storage is bounded here, before the process pins or
2708       * allocates. */
2709      recsz.windows += (size_t)trial_windows(p);
2710      recsz.bins += (size_t)p-&gt;nwin * (size_t)window_bins(p);
2711      if (p-&gt;count == CS_READ)
2712          recsz.counts += (size_t)p-&gt;nwin + 1;
2713      recsz.trace = plan.trace ? TRACE_CAP : 0;
2714      recsz.bytes = (size_t)plan.n * sizeof(struct trec) + recsz.windows * sizeof(struct win) +
2715                    recsz.counts * sizeof(struct counts) + recsz.bins * sizeof(struct bin) + recsz.trace * sizeof(struct tev);
2716  /* bwx10+ */
2717      recsz.bytes += plan.rec_pad;
2718  /* bwx10- */
2719      if (recsz.bytes &gt; MAX_REC_BYTES)
2720          plan_bad(line, "the records of the plan up to this line need %zu bytes, the bound is %lu bytes", recsz.bytes,
2721                   MAX_REC_BYTES);
2722  }
2723</pre></td><td valign="top"><ul><li>Continues <code>plan_trial</code>. The duration of a prefix must be a multiple of 4 ms. <code>nwin</code> (the number of target windows) must be 1 to 4096. <code>win_ms</code> (the duration of one target window) must be 1 ms to 3600000 ms.</li><li><code>count</code> must be the word <code>closed</code>, <code>open</code> or <code>read</code>. <code>bins</code> must be 0 or 1.</li><li>Lines 2707 to 2721 compute in <code>recsz</code> the storage that the records of all trials up to this line need: trial records, windows, bins, counter readings, trace events and the pad of <code>--rec-pad</code>. A total above 256 MiB (<code>MAX_REC_BYTES</code>) ends the process.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>read_plan</code>: reads and checks the whole plan (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2724  /* Reads and checks the whole plan. Returns only if it can run. */
2725  static void read_plan(void)
2726  {
2727      size_t cap = 1 &lt;&lt; 16, len = 0, got;
2728      FILE *f = fopen(plan.path, "rb");
2729      char *text = malloc(cap + 1);
2730      int line = 0;
2731      if (!f || !text) {
2732          fprintf(stderr, "cannot read the plan %s: %s\n", plan.path, strerror(errno));
2733          exit(2);
2734      }
2735      while ((got = fread(text + len, 1, cap - len, f)) &gt; 0) {
2736          len += got;
2737          if (len == cap &amp;&amp; !(text = realloc(text, (cap *= 2) + 1))) {
2738              fprintf(stderr, "no memory for the plan\n");
2739              exit(2);
2740          }
2741      }
2742      if (ferror(f)) {
2743          fprintf(stderr, "cannot read the plan %s\n", plan.path);
2744          exit(2);
2745      }
2746      fclose(f);
2747      text[len] = '\0';
2748      plan.hash = 14695981039346656037ULL; /* FNV-1a, 64 bit, over the bytes of the file */
2749      for (size_t i = 0; i &lt; len; i++)
2750          plan.hash = (plan.hash ^ (uint8_t)text[i]) * 1099511628211ULL;
2751      if (strlen(text) != len)
2752          plan_bad(0, "the file holds a zero byte");</pre></td><td valign="top"><ul><li>Trial mode only. The whole-chip test does not run it.</li><li>Reads the whole plan file (<code>plan.path</code>, the value of <code>--plan</code>) into memory. The text buffer starts with 65536 bytes and doubles when it is full. A file that cannot be read ends the process with status 2.</li><li>Lines 2748 to 2750 compute a 64-bit checksum of the file bytes (the FNV-1a hash) into <code>plan.hash</code>.</li><li>Lines 2751 to 2752 refuse a file that holds a zero byte.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2753      for (char *s = text, *next; *s; s = next) {
2754          char *nl = strchr(s, '\n');
2755          next = nl ? nl + 1 : s + strlen(s);
2756          if (nl)
2757              *nl = '\0';
2758          line++;
2759          if (line == 1) {
2760              if (strcmp(s, PLAN_LINE1))
2761                  plan_bad(1, "the line must be '%s'", PLAN_LINE1);
2762          } else if (line == 2) {
2763              plan_pairs(s);
2764          } else if (line == 3) {
2765              if (strcmp(s, PLAN_LINE3))
2766                  plan_bad(3, "the line must be '%s'", PLAN_LINE3);
2767          } else {
2768              plan_trial(line, s);
2769          }
2770      }
2771      if (line &lt; 3)
2772          plan_bad(line + 1, "the three header lines are needed");
2773      if (plan.n == 0)
2774          plan_bad(line + 1, "no trial");
2775  }
2776</pre></td><td valign="top"><ul><li>Continues <code>read_plan</code>. The loop goes through the text line by line.</li><li>Line 1 must be the text <code># bwx8-plan v1</code>. Line 3 must be the line of column names <code>PLAN_LINE3</code> (line 1816).</li><li>Line 2 goes to <code>plan_pairs</code>. Every line from line 4 on is one trial and goes to <code>plan_trial</code>.</li><li>A plan with fewer than 3 lines, or without a trial, ends the process through <code>plan_bad</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>trial_usage</code>: option summary of the trial mode</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2777  static void trial_usage(void)
2778  {
2779      fprintf(stderr,
2780              "usage: bwx8 --trial --cpus C --bytes B --plan FILE [--ctl-cpu N] [--no-thp] [--trace]\n"
2781              "            [--pmu-type N --events NAME=CODE,...]   (or env BWX_PMU_TYPE, BWX_EVENTS)\n"
2782              "  --cpus: exactly one CPU. --ctl-cpu: CPU of the controlling thread (default 0), another CPU.\n"
2783              "  the counter settings are required if a trial of the plan has count open or read\n");
2784  /* bwx10+ */
2785      fprintf(stderr,
2786              "  bwx10 adds: [--rec-pad BYTES] [--hot-copy]\n"
2787              "  --rec-pad: unused bytes before the window records, a multiple of %zu from 0 to 65536 (default 0)\n"
2788              "  --hot-copy: the window loop works on a local copy of its window record\n",
2789              _Alignof(struct win));
2790  /* bwx10- */
2791  /* bwx11+ */
2792      fprintf(stderr,
2793              "  bwx11 adds: [--evict-mb N]\n"
2794              "  --evict-mb: before the first trial the worker writes N MiB of other memory twice, a whole number\n"
2795              "              from 0 to 4096 (default 0: no such step)\n");
2796  /* bwx11- */
2797      exit(2);
2798  }
2799</pre></td><td valign="top">Trial mode only. Prints the option summary of the trial mode to stderr and ends the process with status 2. The whole-chip test does not reach it.</td></tr>
<tr><td colspan="2"><b>Function <code>trial_main</code>: entry of the trial mode (not run by the test)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2800  static int trial_main(int argc, char **argv)
2801  {
2802      struct tw w;
2803      pthread_t tid;
2804      cpu_set_t set;
2805      int bytes_given = 0, counting = 0;
2806
2807      for (int i = 1; i &lt; argc; i++) {
2808          const char *a = argv[i];
2809          int more = i + 1 &lt; argc;
2810          if (!strcmp(a, "--trial")) {
2811          } else if (!strcmp(a, "--no-thp")) {
2812              cfg.use_thp = 0;
2813          } else if (!strcmp(a, "--trace")) {
2814              plan.trace = 1;
2815  /* bwx10+ */
2816          } else if (!strcmp(a, "--hot-copy")) {
2817              plan.hot_copy = 1;
2818          } else if (!strcmp(a, "--rec-pad") &amp;&amp; more) {
2819              long pad = parse_long(argv[++i], "--rec-pad", 0, 65536);
2820              if (pad % (long)_Alignof(struct win) != 0) {
2821                  fprintf(stderr, "bad --rec-pad: '%s' (a multiple of %zu is needed: the window records stay aligned)\n",
2822                          argv[i], _Alignof(struct win));
2823                  exit(2);
2824              }
2825              plan.rec_pad = (size_t)pad;
2826  /* bwx10- */
2827  /* bwx11+ */
2828          } else if (!strcmp(a, "--evict-mb") &amp;&amp; more) {
2829              evict_mb = parse_long(argv[++i], "--evict-mb", 0, 4096);
2830  /* bwx11- */
2831          } else if (!strcmp(a, "--cpus") &amp;&amp; more) {
2832              parse_cpus(argv[++i]);
2833          } else if (!strcmp(a, "--bytes") &amp;&amp; more) {
2834              cfg.bytes = parse_bytes(argv[++i]);
2835              bytes_given = 1;
2836          } else if (!strcmp(a, "--plan") &amp;&amp; more) {
2837              plan.path = argv[++i];
2838          } else if (!strcmp(a, "--ctl-cpu") &amp;&amp; more) {
2839              plan.ctl_cpu = (int)parse_long(argv[++i], "--ctl-cpu", 0, MAX_USE_CPU);
2840          } else if (!strcmp(a, "--pmu-type") &amp;&amp; more) {
2841              cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);
2842          } else if (!strcmp(a, "--events") &amp;&amp; more) {
2843              parse_events(argv[++i]);
2844          } else {
2845              trial_usage();
2846          }
2847      }</pre></td><td valign="top"><ul><li><code>main</code> calls this function only when an argument is the word <code>--trial</code> (lines 2912 to 2914). No argument line of the whole-chip test holds that word [Ref4]. So the test never runs it.</li><li>Lines 2807 to 2847 are one loop over the arguments. Options of the trial mode only: <code>--trace</code>, <code>--hot-copy</code>, <code>--rec-pad</code>, <code>--evict-mb</code>, <code>--plan</code> and <code>--ctl-cpu</code>. Options that the interval mode also has: <code>--no-thp</code>, <code>--cpus</code>, <code>--bytes</code>, <code>--pmu-type</code> and <code>--events</code>.</li><li>Any other argument goes to <code>trial_usage</code>, which ends the process. The options <code>--threads</code>, <code>--seq</code>, <code>--stop</code>, <code>--start</code>, <code>--rounds</code>, <code>--min-ms</code> and <code>--count</code> of the test have no branch in this loop.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2848      if (cfg.ncpus != 1 || !bytes_given || !plan.path || cfg.bytes % 256 != 0) {
2849          fprintf(stderr, "--trial needs --cpus with exactly one CPU, --bytes (a multiple of 256) and --plan\n");
2850          trial_usage();
2851      }
2852      if (plan.ctl_cpu == cfg.cpus[0]) {
2853          fprintf(stderr, "the controlling thread and the worker must not share CPU %d\n", plan.ctl_cpu);
2854          exit(2);
2855      }
2856      if (sched_getaffinity(0, sizeof set, &amp;set) != 0 || !CPU_ISSET(cfg.cpus[0], &amp;set) || !CPU_ISSET(plan.ctl_cpu, &amp;set)) {
2857          fprintf(stderr, "CPU %d or CPU %d is not in the allowed set of the process\n", cfg.cpus[0], plan.ctl_cpu);
2858          exit(2);
2859      }
2860      read_plan();
2861      for (int i = 0; i &lt; plan.n; i++)
2862          counting |= plan.tr[i].count != CS_CLOSED;
2863      if (counting &amp;&amp; cfg.pmu_type &lt; 0 &amp;&amp; getenv("BWX_PMU_TYPE"))
2864          cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);
2865      if (counting &amp;&amp; cfg.nev == 0 &amp;&amp; getenv("BWX_EVENTS")) {
2866          char *copy = strdup(getenv("BWX_EVENTS"));
2867          parse_events(copy);
2868          free(copy);
2869      }
2870      if (counting &amp;&amp; (cfg.pmu_type &lt; 0 || cfg.nev == 0)) {
2871          fprintf(stderr, "the plan has a trial with count open or read: --pmu-type and --events are needed "
2872                          "(or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");
2873          exit(2);
2874      }
2875
2876      /* The plan can run. The controlling thread pins itself, starts the
2877       * worker and waits. It never touches the buffer. */
2878      pin_cpu(plan.ctl_cpu);
2879      memset(&amp;w, 0, sizeof w);
2880      if (pthread_create(&amp;tid, NULL, trial_worker, &amp;w) != 0) {
2881          perror("pthread_create");
2882          return 2;
2883      }
2884      pthread_join(tid, NULL);
2885      return 0;
2886  }
2887</pre></td><td valign="top"><ul><li>Continues <code>trial_main</code>. Checks: <code>--cpus</code> names exactly one CPU, <code>--bytes</code> is given and is a multiple of 256 bytes, <code>--plan</code> is given. The CPU of the controlling thread (<code>--ctl-cpu</code>, default 0) differs from the worker CPU. Both CPUs are in the allowed CPU set of the process.</li><li><code>read_plan</code> (line 2725) reads and checks the plan. When a trial of the plan counts events, the PMU type and the events must be known, from the options or from the environment variables BWX_PMU_TYPE and BWX_EVENTS.</li><li>Lines 2878 to 2885: the controlling thread (the main thread of the trial mode) pins itself with <code>pin_cpu</code>. It starts one thread that runs <code>trial_worker</code> (line 2449), waits for its end and returns 0.</li></ul></td></tr>
<tr><td colspan="2"><b>Include of the self-test file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2888  /* bwx11+ */
2889  #if 0
2890  /* bwx11- */
2891  #include "bwx10_selftest.c"
2892  /* bwx11+ */
2893  #endif
2894  /* bwx12+ */
2895  #if 0
2896  /* bwx12- */
2897  #include "bwx11_selftest.c"
2898  /* bwx12+ */
2899  #endif
2900  #include "bwx12_selftest.c"
2901  /* bwx12- */
2902  /* bwx11- */
2903</pre></td><td valign="top">The include lines of the two older self-test files (bwx10_selftest.c and bwx11_selftest.c) stand between <code>#if 0</code> and <code>#endif</code>. So the compiler skips them. Line 2900 includes bwx12_selftest.c, which defines the function <code>selftest</code>. <code>main</code> calls it only for the option <code>--selftest</code> (line 2920), and no argument line of the whole-chip test holds this option [Ref4].</td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: start of the program</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2904  int main(int argc, char **argv)
2905  {
2906      int threads_given = 0;
2907      char seq_text[1024] = "";</pre></td><td valign="top">Entry point of the program. <code>threads_given</code> records that <code>--threads</code> was given. <code>seq_text</code> will hold a copy of the <code>--seq</code> text for header line 2 of the output.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2908      t_base_ns = now_ns();</pre></td><td valign="top">Process start time: one reading of the clock CLOCK_MONOTONIC through <code>now_ns</code> (line 327), in ns. The T rows print the common start, <code>t0</code> and <code>t1</code> of each thread as seconds after this time.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2909      page_bytes = sysconf(_SC_PAGESIZE);
2910      cfg.bytes = 1UL &lt;&lt; 20;</pre></td><td valign="top"><code>page_bytes</code> is the size of one small memory page, as Linux reports it. <code>alloc_buf</code> (line 434) uses it when it places a buffer inside its mapping. <code>cfg.bytes</code> gets its default of 1 MiB here. <code>--bytes 256M</code> replaces it at line 2937.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2911      restrict_cpus();</pre></td><td valign="top"><code>restrict_cpus</code> (line 368) removes every CPU above 119 from the allowed CPU set of the process. The script rx.sh has already limited the process to the CPUs 0 to 119 with <code>taskset</code> [Ref3]. So this call changes nothing in the test.</td></tr>
<tr><td colspan="2"><b><code>main</code>: mode choice, interval mode or trial mode</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2912      for (int i = 1; i &lt; argc; i++)
2913          if (!strcmp(argv[i], "--trial"))
2914              return trial_main(argc, argv);
2915</pre></td><td valign="top"><ul><li>The loop compares every argument with the word <code>--trial</code>. When one is equal, <code>main</code> returns the result of <code>trial_main</code>, and no line below runs.</li><li>Line 2914 is the only call of <code>trial_main</code> in the file.</li><li>The argument lines of like.spec, cfwd.spec and crev.spec do not hold the word <code>--trial</code> [Ref4]. So in the whole-chip test the loop ends without that call. The program continues in the interval mode, which is the rest of <code>main</code>.</li></ul></td></tr>
<tr><td colspan="2"><b><code>main</code>: argument parsing</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2916      for (int i = 1; i &lt; argc; i++) {
2917          const char *a = argv[i];
2918          int more = i + 1 &lt; argc;</pre></td><td valign="top">Loop over the arguments from left to right. <code>a</code> is the current argument. <code>more</code> is 1 when one more argument follows it. An option with a value is accepted only when <code>more</code> is 1, and <code>argv[++i]</code> then takes the value.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2919          if (!strcmp(a, "--selftest")) {
2920              return selftest();
2921          } else if (!strcmp(a, "--list")) {
2922              for (int k = 0; k &lt; K_COUNT; k++)
2923                  printf("%s\n", kernels[k].name);
2924              return 0;</pre></td><td valign="top"><code>--selftest</code> runs the self-test and ends the program. <code>--list</code> prints the 55 kernel names of <code>kernels[]</code> and ends the program. The argument lines of the test hold neither option [Ref4].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2925          } else if (!strcmp(a, "--no-thp")) {
2926              cfg.use_thp = 0;
2927          } else if (!strcmp(a, "--two-buffers")) {
2928              cfg.two_buffers = 1;</pre></td><td valign="top">The argument lines of the test hold neither <code>--no-thp</code> nor <code>--two-buffers</code> [Ref4]. So <code>cfg.use_thp</code> keeps its default 1 (line 282), and <code>alloc_buf</code> asks Linux for 2 MiB pages. <code>cfg.two_buffers</code> stays 0 at this point.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2929          } else if (!strcmp(a, "--count")) {
2930              cfg.count = 1;</pre></td><td valign="top"><code>--count</code> (given in the test) sets <code>cfg.count</code> to 1. Then each worker opens its counter group and reads it before and after every timed interval. <code>main</code> prints the C rows from these readings.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2931          } else if (!strcmp(a, "--threads") &amp;&amp; more) {
2932              cfg.threads = (int)parse_long(argv[++i], "--threads", 1, 4096);
2933              threads_given = 1;</pre></td><td valign="top"><code>--threads 120</code>: <code>parse_long</code> (line 353) accepts a whole number from 1 to 4096. <code>cfg.threads</code> becomes 120.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2934          } else if (!strcmp(a, "--cpus") &amp;&amp; more) {
2935              parse_cpus(argv[++i]);</pre></td><td valign="top"><code>--cpus 0-63,64-119</code>: <code>parse_cpus</code> (line 388) appends the CPUs of each range to <code>cfg.cpus</code>, in the order of the text. The result is the list 0, 1, ... 119. <code>cfg.ncpus</code> becomes 120.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2936          } else if (!strcmp(a, "--bytes") &amp;&amp; more) {
2937              cfg.bytes = parse_bytes(argv[++i]);</pre></td><td valign="top"><code>--bytes 256M</code>: <code>parse_bytes</code> (line 334) reads the letter <code>M</code> as 2^20. <code>cfg.bytes</code> becomes 268435456 bytes (256 MiB). This is the buffer size of each thread.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2938          } else if (!strcmp(a, "--min-ms") &amp;&amp; more) {
2939              char *end;
2940              double ms = strtod(argv[++i], &amp;end);
2941              if (end == argv[i] || *end != '\0' || !(ms &gt; 0) || ms &gt; 3.6e6) {
2942                  fprintf(stderr, "bad --min-ms: '%s' (a number of milliseconds above 0 is needed)\n", argv[i]);
2943                  exit(2);
2944              }
2945              cfg.min_s = ms / 1000.0;</pre></td><td valign="top"><code>--min-ms 6000</code>: <code>strtod</code> reads the text as a decimal number of milliseconds. The number must be above 0 and at most 3.6e6 ms (1 hour). <code>cfg.min_s</code> becomes 6.0 s. With <code>--stop common</code> this is the time from the common start to the deadline (line 3061).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2946          } else if (!strcmp(a, "--rounds") &amp;&amp; more) {
2947              cfg.rounds = (int)parse_long(argv[++i], "--rounds", 1, 1000000);</pre></td><td valign="top"><code>--rounds 2</code>: a whole number from 1 to 1000000. <code>cfg.rounds</code> becomes 2. The program then runs the <code>--seq</code> list 2 times, as round 0 and round 1.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2948          } else if (!strcmp(a, "--seq") &amp;&amp; more) {
2949              snprintf(seq_text, sizeof seq_text, "%s", argv[++i]);
2950              parse_seq(argv[i]);</pre></td><td valign="top"><ul><li><code>--seq</code>: line 2949 first copies the text to <code>seq_text</code>. <code>parse_seq</code> then splits the argument text itself at each comma.</li><li><code>parse_seq</code> (line 1750) looks up each name in <code>kernels[]</code> and appends its index to <code>cfg.seq</code>. An unknown name ends the process.</li><li>Result: 5 entries for like.spec (<code>oldread</code>, <code>asmread</code>, <code>read_nop96</code>, <code>read_nop256</code>, <code>read_1pl</code>) and 3 entries for cfwd.spec and crev.spec [Ref4]. <code>cfg.nseq</code> holds this number.</li><li>No name of the test has an <code>@SIZE</code> part. So the size of every entry stays 0 until line 2990.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2951          } else if (!strcmp(a, "--stop") &amp;&amp; more) {
2952              const char *s = argv[++i];
2953              if (strcmp(s, "pass") &amp;&amp; strcmp(s, "common"))
2954                  usage();
2955              cfg.stop_common = !strcmp(s, "common");</pre></td><td valign="top"><code>--stop common</code>: the value must be <code>pass</code> or <code>common</code>. Any other value goes to <code>usage</code>. <code>cfg.stop_common</code> becomes 1. Then all threads get one common start time and one common deadline for each interval (lines 3058 to 3063).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2956          } else if (!strcmp(a, "--start") &amp;&amp; more) {
2957              const char *s = argv[++i];
2958              if (strcmp(s, "common") &amp;&amp; strcmp(s, "offset"))
2959                  usage();
2960              cfg.start_offset = !strcmp(s, "offset");</pre></td><td valign="top"><code>--start common</code>: the value must be <code>common</code> or <code>offset</code>. <code>cfg.start_offset</code> becomes 0 for <code>common</code>. So every worker starts its timed loop at byte 0 of its own buffer (worker line 1662).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2961          } else if (!strcmp(a, "--pmu-type") &amp;&amp; more) {
2962              cfg.pmu_type = parse_long(argv[++i], "--pmu-type", 0, 0x7fffffffL);
2963          } else if (!strcmp(a, "--events") &amp;&amp; more) {
2964              parse_events(argv[++i]);</pre></td><td valign="top"><ul><li><code>--pmu-type 11</code>: <code>cfg.pmu_type</code> becomes 11.</li><li><code>--events</code>: <code>parse_events</code> (line 1771) stores the 6 names in <code>cfg.ev_name</code> and the 6 codes in <code>cfg.ev_code</code>. <code>cfg.nev</code> becomes 6.</li><li><code>main</code> does not interpret the codes. Each worker passes them to Linux in <code>open_counters</code> (line 1582).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2965          } else {
2966              usage();
2967          }
2968      }</pre></td><td valign="top"><ul><li>Any other argument goes to <code>usage</code> (line 1737). The same holds for an option whose value is missing.</li><li><code>usage</code> prints the option summary to stderr and ends the process with status 2.</li><li>Every option of the three argument lines of the test has a branch above [Ref4]. So the test does not reach these lines.</li></ul></td></tr>
<tr><td colspan="2"><b><code>main</code>: checks of the settings</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2969      if (threads_given &amp;&amp; cfg.ncpus == 0) {
2970          fprintf(stderr, "--threads requires --cpus\n");
2971          usage();
2972      }
2973      if (cfg.threads &lt; 1 || cfg.rounds &lt; 1 || cfg.nseq &lt; 1 || cfg.bytes == 0 || cfg.bytes % 256 != 0)
2974          usage();</pre></td><td valign="top">Two checks that end in <code>usage</code>. First: <code>--threads</code> needs <code>--cpus</code>. Second: the thread count, the round count and the number of <code>--seq</code> entries are at least 1, and <code>--bytes</code> is above 0 and a multiple of 256 bytes. The settings of the test pass both checks.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2975      /* run_bwx.sh passes the counter settings in the environment */
2976      if (cfg.count &amp;&amp; cfg.pmu_type &lt; 0 &amp;&amp; getenv("BWX_PMU_TYPE"))
2977          cfg.pmu_type = parse_long(getenv("BWX_PMU_TYPE"), "BWX_PMU_TYPE", 0, 0x7fffffffL);
2978      if (cfg.count &amp;&amp; cfg.nev == 0 &amp;&amp; getenv("BWX_EVENTS")) {
2979          char *copy = strdup(getenv("BWX_EVENTS"));
2980          parse_events(copy);
2981          free(copy);
2982      }</pre></td><td valign="top">Fallback for the counter settings, for <code>--count</code> without <code>--pmu-type</code> or without <code>--events</code>. The program then takes the missing setting from the environment variable BWX_PMU_TYPE or BWX_EVENTS, if that variable is set. The argument lines of the test give both options [Ref4]. So these lines change nothing there.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2983      if (cfg.count &amp;&amp; (cfg.pmu_type &lt; 0 || cfg.nev == 0)) {
2984          fprintf(stderr, "--count requires --pmu-type and --events (or BWX_PMU_TYPE and BWX_EVENTS in the environment)\n");
2985          usage();
2986      }</pre></td><td valign="top">With <code>--count</code> the PMU type and at least one event must be known at this point. Otherwise the program prints a message and ends through <code>usage</code>. In the test the type is 11 and there are 6 events.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2987      for (int s = 0; s &lt; cfg.nseq; s++) {
2988          struct entry *e = &amp;cfg.seq[s];
2989          if (e-&gt;bytes == 0)
2990              e-&gt;bytes = cfg.bytes;</pre></td><td valign="top">Loop over the <code>--seq</code> entries. An entry without an <code>@SIZE</code> part gets the size of <code>--bytes</code>. In the test every entry gets 268435456 bytes.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2991          if (e-&gt;bytes &gt; cfg.bytes || e-&gt;bytes % 256 != 0 ||
2992              (cfg.stop_common &amp;&amp; e-&gt;bytes &gt; CHUNK_BYTES &amp;&amp; e-&gt;bytes % CHUNK_BYTES != 0)) {
2993              fprintf(stderr, "bad size of --seq entry %d (%s): %lu\n", s, kernels[e-&gt;k].name, (unsigned long)e-&gt;bytes);
2994              usage();
2995          }</pre></td><td valign="top"><ul><li>Size check of an entry. The size must be at most <code>--bytes</code> and a multiple of 256 bytes. Otherwise the program prints a message to stderr and ends through <code>usage</code>.</li><li>With <code>--stop common</code> a size above 2 MiB (<code>CHUNK_BYTES</code>) must also be a multiple of 2 MiB. With this stop rule the worker calls the kernel on chunks of 2 MiB (worker line 1693).</li><li>268435456 bytes is 128 times 2 MiB. So the entries of the test pass.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2996          if (kernels[e-&gt;k].type == T_COPY)
2997              cfg.two_buffers = 1;
2998      }</pre></td><td valign="top">A copy kernel in the list sets <code>cfg.two_buffers</code> to 1. The six kernels of the test have the type T_READ or T_OLDREAD in <code>kernels[]</code> (lines 1460 to 1476). So <code>cfg.two_buffers</code> stays 0, and each thread has one buffer, <code>a</code>. Header line 2 of every csv file of the test says <code>two_buffers=0</code> [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2999      if (cfg.ncpus &amp;&amp; cfg.threads &gt; cfg.ncpus)
3000          fprintf(stderr, "warning: %d threads on %d cpus: cpus are oversubscribed\n", cfg.threads, cfg.ncpus);
3001</pre></td><td valign="top">A warning on stderr when there are more threads than CPUs in the list. The test has 120 threads and 120 CPUs. So no warning is printed.</td></tr>
<tr><td colspan="2"><b><code>main</code>: thread records, barrier, start of the workers</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3002      struct thread *th = calloc((size_t)cfg.threads, sizeof *th);
3003      uint64_t **bufs = calloc((size_t)cfg.threads * 2, sizeof *bufs);
3004      struct page *pg = calloc((size_t)cfg.threads * 2, sizeof *pg);</pre></td><td valign="top"><ul><li>Three arrays, filled with 0 by <code>calloc</code>.</li><li><code>th</code>: one record per thread (120 in the test).</li><li><code>bufs</code>: two buffer addresses per thread, for buffer <code>a</code> and buffer <code>b</code> (240 entries).</li><li><code>pg</code>: one page-state record per entry of <code>bufs</code> (240 entries).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3005      if (!th || !bufs || !pg || pthread_barrier_init(&amp;bar, NULL, (unsigned)cfg.threads + 1) != 0) {
3006          perror("setup");
3007          return 2;
3008      }</pre></td><td valign="top">Creates the barrier <code>bar</code> for the thread count plus 1. In the test this is 121: the 120 workers and the main thread. A failed allocation or a failed barrier setup ends the program with status 2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3009      for (int i = 0; i &lt; cfg.threads; i++) {
3010          th[i].idx = i;
3011          th[i].cpu = cfg.ncpus ? cfg.cpus[i % cfg.ncpus] : -1;
3012          if (pthread_create(&amp;th[i].tid, NULL, worker, &amp;th[i]) != 0) {
3013              perror("pthread_create");
3014              return 2;
3015          }
3016      }
3017</pre></td><td valign="top"><ul><li>Starts the workers. Thread <code>i</code> gets the index <code>i</code> and the CPU <code>cfg.cpus[i % cfg.ncpus]</code>.</li><li>With 120 threads and the CPU list 0 to 119 this is CPU <code>i</code>. So threads 0 to 63 run on mesh 0 and threads 64 to 119 run on mesh 1.</li><li>Each new thread runs <code>worker</code> (line 1632). It pins itself, opens its counters, maps its buffer and writes it. <code>main</code> does not wait for that here. It continues with the header.</li><li><code>main</code> never pins itself in the interval mode. It may run on any CPU of the allowed CPU set, the CPUs 0 to 119.</li><li>A failed <code>pthread_create</code> ends the program with status 2.</li></ul></td></tr>
<tr><td colspan="2"><b><code>main</code>: header lines of the csv file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3018      printf("# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); "
3019             "copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n",
3020             cfg.threads, (unsigned long)cfg.bytes, cfg.min_s * 1000.0, cfg.use_thp ? "madvise" : "nohugepage");</pre></td><td valign="top"><ul><li>Header line 1. It gives the meaning of GB, the formula of the rate in the I rows, and four settings.</li><li>In the test the settings are <code>threads=120 bytes_per_thread=268435456 min_ms=6000 thp=madvise</code> in all 9 csv files [Ref5].</li><li><code>thp=madvise</code> only says that the program asked for 2 MiB pages. The P rows show what the buffers got.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3021      printf("# bwx: seq=%s rounds=%d stop=%s start=%s two_buffers=%d count=%d kernels=%s; "
3022             "round and pos count from 0; times are seconds since process start\n",
3023             seq_text, cfg.rounds, cfg.stop_common ? "common" : "pass", cfg.start_offset ? "offset" : "common",
3024             cfg.two_buffers, cfg.count, STANDIN ? "STAND-IN (not AArch64: rates mean nothing)" : "aarch64");</pre></td><td valign="top"><ul><li>Header line 2: the <code>--seq</code> text, the rounds, the stop rule, the start rule, <code>two_buffers</code>, <code>count</code> and the build kind.</li><li><code>STANDIN</code> is 0 in the AArch64 build (line 492). So the build kind is printed as <code>kernels=aarch64</code>. Every csv file of the test has this text [Ref5].</li><li>The line also says that round and position count from 0, and that the times are seconds since the process start.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3025      printf("# I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps\n"
3026             "# T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags\n"
3027             "# P,round,pos,tid,buffer,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success\n");</pre></td><td valign="top">Header lines 3 to 5: the column names of the I rows, the T rows and the P rows. Lines 3077 to 3085 print the I rows and the T rows. <code>print_p</code> (line 1570) prints the P rows.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3028      if (cfg.count) {
3029          printf("# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns");
3030          for (int e = 0; e &lt; cfg.nev; e++)
3031              printf(",%s", cfg.ev_name[e]);
3032          printf("; pmu_type=%ld codes=", cfg.pmu_type);
3033          for (int e = 0; e &lt; cfg.nev; e++)
3034              printf("%s0x%llx", e ? "," : "", (unsigned long long)cfg.ev_code[e]);
3035          printf("\n");
3036      }</pre></td><td valign="top">Header line 6, only with <code>--count</code>: the column names of the C rows. After <code>cputime_ns</code> it lists the event names in the order of <code>--events</code>. The line ends with the PMU type and the event codes in hexadecimal. In the test this is <code>pmu_type=11 codes=0x198,0x199,0x19a,0x19b,0x19c,0x19</code> [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3037      fflush(stdout);
3038</pre></td><td valign="top">Writes the header lines to the standard output now. In the test the standard output is the csv file. The script rx.sh redirects it there [Ref3].</td></tr>
<tr><td colspan="2"><b><code>main</code>: loop over rounds and positions</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3039      for (int round = 0; round &lt; cfg.rounds; round++) {
3040          for (int pos = -1; pos &lt; cfg.nseq; pos++) {</pre></td><td valign="top"><ul><li>Two nested loops, as in <code>worker</code> (lines 1656 to 1657). <code>round</code> runs from 0 to 1 in the test.</li><li><code>pos</code> starts at -1, not at 0. Position -1 is one extra loop pass before the first interval. Each position from 0 up is one timed interval.</li><li>The test has 10 intervals per process for like.spec and 6 for cfwd.spec and crev.spec.</li><li><code>main</code> and the 120 workers go through the same rounds and positions. At each barrier call below a thread waits until all 121 threads have arrived.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3041              if (pos &lt; 0 &amp;&amp; (round &gt; 0 || cfg.threads == 1))
3042                  continue;</pre></td><td valign="top">The loop pass with position -1 is skipped in every round after round 0, and in a process with one thread. So in the test it runs once, before the first interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3043              if (pos &lt; 0) {
3044                  /* the workers have allocated and first touched their buffers */
3045                  pthread_barrier_wait(&amp;bar);
3046                  for (int i = 0; i &lt; cfg.threads; i++) {
3047                      bufs[2 * i] = th[i].a;
3048                      bufs[2 * i + 1] = th[i].b;
3049                  }</pre></td><td valign="top"><ul><li>Position -1. <code>main</code> calls the barrier. The call returns when all 120 workers have mapped and written their buffers and wait at worker line 1652.</li><li>Then <code>main</code> copies the buffer addresses of every thread into <code>bufs</code>: entry <code>2 * i</code> for buffer <code>a</code>, entry <code>2 * i + 1</code> for buffer <code>b</code>.</li><li>Buffer <code>b</code> does not exist in the test. Its entries stay NULL.</li><li>This loop pass continues with the page-state block at line 3105. That block prints the page state before the first interval.</li></ul></td></tr>
<tr><td colspan="2"><b><code>main</code>: one interval, common start</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3050              } else {
3051                  const struct entry *e = &amp;cfg.seq[pos];
3052                  const char *name = kernels[e-&gt;k].name;
3053                  double per_pass = (double)e-&gt;bytes * (kernels[e-&gt;k].type == T_COPY ? 2 : 1);
3054                  uint64_t total = 0;
3055                  int64_t max_el = 0;
3056</pre></td><td valign="top">One interval. <code>e</code> is the <code>--seq</code> entry of this position, and <code>name</code> is the name of its kernel. <code>per_pass</code> is the byte count of one pass over the buffer: 268435456 in the test (a copy kernel counts twice the size). <code>total</code> and <code>max_el</code> start at 0.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3057                  pthread_barrier_wait(&amp;bar); /* release the workers */</pre></td><td valign="top"><ul><li>First barrier call of the interval. It returns when all 120 workers have finished the warm-up pass of this kernel and wait at worker line 1675.</li><li>The barrier then lets all 121 threads continue.</li><li>With <code>--stop common</code> the workers do not start the kernel yet. Each worker spins until <code>gen</code> changes (worker line 1677).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3058                  if (cfg.stop_common) {
3059                      int64_t sched = now_ns() + LEAD_NS;
3060                      atomic_store(&amp;t_sched_ns, sched);
3061                      atomic_store(&amp;deadline_ns, sched + (int64_t)(cfg.min_s * 1e9));
3062                      atomic_fetch_add(&amp;gen, 1);
3063                  }</pre></td><td valign="top"><ul><li><b>Common start, set by the main thread.</b> <code>main</code> reads the clock once and adds <code>LEAD_NS</code> (2 ms, line 132). The result <code>sched</code> is the common start time of all threads.</li><li>It stores <code>sched</code> in <code>t_sched_ns</code>. It stores the deadline in <code>deadline_ns</code>: <code>sched</code> plus <code>cfg.min_s</code>, which is 6 s (6000000000 ns) in the test.</li><li>Only after both stores it adds 1 to <code>gen</code>. So a worker that sees the new <code>gen</code> reads the new start time and the new deadline.</li><li>Each worker then spins on the clock until <code>sched</code> and reads its own start time <code>t0</code> (worker lines 1681 to 1688).</li><li>After the change of <code>gen</code>, <code>main</code> passes nothing more to the workers. Each worker stops on its own, at its first clock read at or after the deadline (worker lines 1700 to 1701).</li><li><code>main</code> is not pinned. In the test it runs these lines on one of the CPUs 0 to 119, and a pinned worker spins on each of these CPUs at that time.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3064                  pthread_barrier_wait(&amp;bar); /* all workers finished this interval */
3065</pre></td><td valign="top"><ul><li>Second barrier call of the interval. <code>main</code> calls it directly after the change of <code>gen</code>.</li><li><code>main</code> blocks here until all 120 workers have stored their results and wait at worker line 1727.</li><li>So between the change of <code>gen</code> and the end of the timed interval this call is the only code that <code>main</code> runs. It prints nothing in that time.</li></ul></td></tr>
<tr><td colspan="2"><b><code>main</code>: I row, T rows, C rows</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3066                  for (int i = 0; i &lt; cfg.threads; i++) {
3067                      struct result *r = &amp;th[i].res;
3068                      total += r-&gt;bytes;
3069                      if (r-&gt;t_end - r-&gt;t_start &gt; max_el)
3070                          max_el = r-&gt;t_end - r-&gt;t_start;
3071                  }</pre></td><td valign="top"><ul><li>Loop over the results of the 120 threads. <code>total</code> becomes the sum of their byte counts.</li><li><code>max_el</code> becomes the longest elapsed time of one thread, <code>t_end - t_start</code> in ns. <code>t_start</code> is the <code>t0</code> of the worker, and <code>t_end</code> is its last <code>t1</code> (worker lines 1722 to 1723).</li><li>From here to line 3114 every worker waits at the barrier of worker line 1731. So no kernel runs while <code>main</code> prints the I, T and C rows.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3072                  if (cfg.threads == 1) { /* read by the worker before the interval */
3073                      print_p(round, pos, 0, 'a', &amp;th[0].res.pg[0], th[0].res.vm);
3074                      if (th[0].b)
3075                          print_p(round, pos, 0, 'b', &amp;th[0].res.pg[1], th[0].res.vm);
3076                  }</pre></td><td valign="top">Branch for a process with one thread. There the worker reads the page state itself before the interval, and <code>main</code> prints it here. The test has 120 threads. So these lines do not run.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3077                  printf("I,%d,%d,%s,%lu,%d,%lu,%.6f,%.2f\n", round, pos, name, (unsigned long)e-&gt;bytes, cfg.threads,
3078                         (unsigned long)total, (double)max_el * 1e-9, (double)total / (double)max_el);</pre></td><td valign="top"><ul><li><b>I row</b>: one per interval, 9 fields: <code>I</code>, round, position, kernel name, <code>bytes_per_thread</code>, thread count, <code>total_bytes</code>, <code>max_elapsed_s</code>, <code>aggregate_GBps</code>.</li><li><code>bytes_per_thread</code> is the size of the <code>--seq</code> entry (268435456 bytes in the test). It is a setting, not a measured value.</li><li><code>max_elapsed_s</code> is <code>max_el</code> in seconds, with 6 decimals.</li><li><code>aggregate_GBps</code> is <code>total</code> in bytes divided by <code>max_el</code> in ns, with 2 decimals. One byte per ns is 1 GB/s with GB = 1e9 bytes. So this rate is the bytes of all threads divided by the longest time of one thread.</li><li>The script stat_bwx.py computes the rate of an interval in another way: the sum over the T rows of bytes / elapsed seconds / 1e9, in GB/s. It keeps the I value next to it as <code>I_agg</code> [Ref6].</li><li>In the 74 intervals of the 9 csv files of the test the two values differ by less than 0.004 % (computed on 2026-11-21) [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3079                  for (int i = 0; i &lt; cfg.threads; i++) {
3080                      struct result *r = &amp;th[i].res;
3081                      printf("T,%d,%d,%s,%d,%d,%lu,%.6f,%.6f,%.6f,%.6f,%.3f,%s\n", round, pos, name, i, th[i].cpu,
3082                             (unsigned long)r-&gt;bytes, (double)(r-&gt;t_end - r-&gt;t_start) * 1e-9,
3083                             (double)(r-&gt;t_sched - t_base_ns) * 1e-9, (double)(r-&gt;t_start - t_base_ns) * 1e-9,
3084                             (double)(r-&gt;t_end - t_base_ns) * 1e-9, (double)r-&gt;bytes / per_pass, r-&gt;late ? "late" : "-");
3085                  }</pre></td><td valign="top"><ul><li><b>T rows</b>: one per thread and interval, 13 fields. Fields 1 to 6: <code>T</code>, round, position, kernel name, thread index (<code>tid</code>), CPU of the thread.</li><li>Field 7 <code>bytes</code>: the byte count of the worker. Field 8 <code>elapsed_s</code>: <code>t_end - t_start</code> in seconds, with 6 decimals.</li><li>The rate of a thread is field 7 divided by field 8, in bytes per second. The program does not print it. The script stat_bwx.py computes it and divides it by 1e9 to get GB/s [Ref6].</li><li>Fields 9 to 11 (<code>t_sched_s</code>, <code>t_start_s</code>, <code>t_end_s</code>): the common start time, <code>t0</code> and the last <code>t1</code>, in seconds since the process start <code>t_base_ns</code>.</li><li>Field 12 <code>passes</code>: <code>bytes / per_pass</code>, the number of passes over the buffer, with 3 decimals. Field 13 <code>flags</code>: <code>late</code> when <code>t0</code> came more than 100 us after the common start (worker line 1725), otherwise <code>-</code>.</li><li>In the 9 csv files of the test no T row is <code>late</code>. The largest <code>t_start_s - t_sched_s</code> is 34 us (0.034 ms, computed on 2026-11-21) [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3086                  for (int i = 0; cfg.count &amp;&amp; i &lt; cfg.threads; i++) {
3087                      struct result *r = &amp;th[i].res;
3088                      printf("C,%d,%d,%s,%d,%d", round, pos, name, i, th[i].cpu);</pre></td><td valign="top"><b>C rows</b>, only with <code>--count</code>: one per thread and interval. The first 6 fields are <code>C</code>, round, position, kernel name, thread index and CPU.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3089                      if (th[i].group_fd &lt; 0)
3090                          printf(",NA,NA");
3091                      else
3092                          printf(",%llu,%llu", (unsigned long long)(r-&gt;c1.enabled - r-&gt;c0.enabled),
3093                                 (unsigned long long)(r-&gt;c1.running - r-&gt;c0.running));
3094                      printf(",%llu", (unsigned long long)(r-&gt;c1.cpu_ns - r-&gt;c0.cpu_ns));</pre></td><td valign="top"><ul><li>Fields 7 and 8, <code>enabled_ns</code> and <code>running_ns</code>: the enabled time and the running time of the counter group at the second reading minus the same values at the first reading. A thread without an open group gets <code>NA,NA</code>.</li><li>Field 9, <code>cputime_ns</code>: the thread CPU time at the second reading minus the value at the first reading.</li><li>The worker takes the first reading (<code>c0</code>) directly before <code>t0</code> and the second reading (<code>c1</code>) directly after its last <code>t1</code> (worker lines 1684 to 1687 and 1717 to 1720).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3095                      for (int ev = 0; ev &lt; cfg.nev; ev++) {
3096                          int at = th[i].ev_pos[ev];
3097                          if (at &lt; 0)
3098                              printf(",NA");
3099                          else
3100                              printf(",%llu", (unsigned long long)(r-&gt;c1.val[at] - r-&gt;c0.val[at]));
3101                      }
3102                      printf("\n");
3103                  }
3104              }</pre></td><td valign="top">One field per event, in the order of <code>--events</code>: the count at the second reading minus the count at the first reading. <code>ev_pos[ev]</code> is the place of the event in the group reading. It is -1 when the event did not open, and then the field is <code>NA</code>. In the 9 csv files of the test no field is <code>NA</code> [Ref5].</td></tr>
<tr><td colspan="2"><b><code>main</code>: page state, P rows, <code># page_read</code> line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3105              if (cfg.threads &gt; 1) {
3106                  /* Page state of all buffers, read between two intervals. It is
3107                   * the state after interval pos (pos -1: before the first). The
3108                   * workers wait on the barrier below until it is read. */
3109                  long long vm[4];</pre></td><td valign="top"><ul><li>Page-state block. It runs in a process with more than one thread: once at position -1 and once after every interval.</li><li>At this time every worker waits at a barrier: worker line 1653 after position -1, worker line 1731 after an interval. So no kernel runs while <code>main</code> reads the page state.</li><li><code>vm</code> will hold the four vmstat counters.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3110                  int64_t r0 = now_ns();
3111                  read_smaps(pg, bufs, 2 * cfg.threads);
3112                  read_vmstat(vm);
3113                  double ms = (double)(now_ns() - r0) * 1e-6;</pre></td><td valign="top"><code>main</code> reads the clock, reads the page state and reads the clock again. <code>read_smaps</code> (line 1515) looks up each of the 240 entries of <code>bufs</code> in <code>/proc/self/smaps</code> and skips the NULL entries. <code>read_vmstat</code> (line 1545) reads the four vmstat counters. <code>ms</code> is the duration of both readings in ms.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3114                  pthread_barrier_wait(&amp;bar); /* the reading is done: the workers go on */</pre></td><td valign="top">Barrier call that lets the workers continue. Each worker then starts the warm-up pass of the next interval, while <code>main</code> prints the P rows below. After the last interval the workers end instead.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3115                  for (int i = 0; i &lt; 2 * cfg.threads; i++)
3116                      if (bufs[i])
3117                          print_p(round, pos, i / 2, i % 2 ? 'b' : 'a', &amp;pg[i], vm);</pre></td><td valign="top"><ul><li><b>P rows</b>: one per existing buffer, printed by <code>print_p</code> (line 1570). Entry <code>i</code> of <code>bufs</code> belongs to thread <code>i / 2</code>. An even <code>i</code> is buffer <code>a</code>.</li><li>Fields: <code>P</code>, round, position, thread index, buffer letter, size of the buffer in kB, part on 2 MiB pages in kB, then the four vmstat counters.</li><li>The position is that of the interval before the reading, or -1 for the reading before the first interval.</li><li>All rows of one block carry the same four vmstat values. They count for the whole system and were read once (line 3112).</li><li>In the test every P row is a row of buffer <code>a</code> and reports 262144 kB of 262144 kB on 2 MiB pages [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3118                  printf("# page_read,%d,%d,%.3f ms\n", round, pos, ms);
3119              }</pre></td><td valign="top">The line <code># page_read,round,pos,&lt;time&gt; ms</code>: the duration <code>ms</code> of the page-state reading of this block, with 3 decimals. In the 9 csv files of the test it lies between 3.745 ms and 4.947 ms (83 lines, read on 2026-11-21) [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3120              fflush(stdout);
3121          }
3122      }</pre></td><td valign="top"><ul><li>Writes all rows that are still in the output buffer to the csv file. Then the loops continue with the next position.</li><li>A new timed interval cannot start before <code>main</code> has passed line 3057 and line 3062 again. So <code>main</code> writes no output during a timed interval.</li><li>Measured in the test: the time from the latest <code>t_end_s</code> of one interval to the <code>t_sched_s</code> of the next interval of the same process. It is 63.8 ms to 139.8 ms (65 pairs in the 9 csv files, computed on 2026-11-21) [Ref5].</li><li>In this time lie the output of the rows, the page-state reading, the barrier calls, the warm-up pass of the next kernel and the 2 ms lead. No code of the interval mode calls a sleep function.</li></ul></td></tr>
<tr><td colspan="2"><b><code>main</code>: end</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3123      for (int i = 0; i &lt; cfg.threads; i++)
3124          pthread_join(th[i].tid, NULL);
3125      return 0;
3126  }</pre></td><td valign="top">After the last interval <code>main</code> waits for the end of all 120 worker threads. Then the process ends with status 0. The script rx.sh writes this status to the file launches.txt of the result folder [Ref3].</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt`: objdump text of every kernel of the bwx12 binary that was built on CRB. Source of the instruction counts per loop pass. The build record holds the sha256 of this file (line 21 of Ref2). Lines: `k_read` 2 to 15 (loop 4 to 14), `k_asmread` 60 to 81 (loop 66 to 76), `k_oldread` 134 to 204 (loop 161 to 176), `k_read_1pl` 755 to 764 (loop 757 to 763), `k_read_nop96` 855 to 972 (loop 861 to 967), `k_read_nop256` 2127 to 2404 (loop 2133 to 2399).
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: build record of CRB. Line 2: the compiler. Line 3: the flags. Line 9: the binary has a symbol `call`, and this function starts at 24 modulo 64 (`call=24`). Line 14: the same value `call=24` for the binary of bwx11. Line 17: sha256 of bwx12.c at the build, equal to the sha256 of the source file in this folder (checked with sha256sum on 2026-11-21). Line 18: sha256 of bwx12_selftest.c at the build, equal to the sha256 of the file in this folder (same check). Line 20: sha256 of the binary bwx12. Line 21: sha256 of the file listing.txt that the build wrote, equal to the sha256 of the listing file of Ref1 (same check). The build command is at lines 37 and 47 of build12.sh in the folder above: it has no `-D` option.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: the script that starts the program. Line 17: `taskset -c 0-119 $BW $args > $out/$tag.csv`, with stderr appended to stderr.txt. Lines 7, 13 and 19: the checks of the marker file. Line 16: it appends the launch line, which ends with the argument line, to launches.txt. Line 20: it appends a line that starts with `rc` and the exit status of the program to launches.txt. Line 8: the command `sha256sum -c` computes the sha256 of the binary file and compares it with the third argument of the script. When the two values differ, the script prints `sha mismatch` and ends with status 2. Line 10: it writes the path of the binary and this third argument to env.txt. The scripts go.sh and go2.sh of the test, in the folder of Ref4, check the sha256 of rx.sh before they call it (line 22 of go.sh, line 18 of go2.sh). The local file rx.sh has the sha256 that both scripts hold (checked with sha256sum on 2026-11-21).
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/like.spec, cfwd.spec, crev.spec`: the argument lines of the test. Each file has one line. like.spec: part L and control I. cfwd.spec and crev.spec: part C. The line of like.spec is `a6456|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 6000 --rounds 2 --seq oldread,asmread,read_nop96,read_nop256,read_1pl --count --pmu-type 11 --events cbusy0=0x198,cbusy1=0x199,cbusy2=0x19a,cbusy3=0x19b,cbusy_mt=0x19c,bus_access=0x19`. The text before the `|` is the tag. The lines of cfwd.spec and crev.spec differ from this line only in the tag and in the `--seq` list. cfwd.spec has the tag `cfwd` and the list `--seq oldread,read,asmread`. crev.spec has the tag `crev` and the list `--seq asmread,read,oldread`. No line holds the word `--trial`, `--selftest` or `--list`. No line holds `--no-thp` or `--two-buffers`. The three `--seq` lists name only the six kernels `oldread`, `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl`, and no entry holds `@`. Each of the 6 `--events` entries has the form NAME=CODE.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72*-20261117T*Z/`: the 9 result folders of the bwx12 processes of the test (2026-11-17): 3 of part L (T72L1 to T72L3), 4 of part C (T72C1 to T72C4), 2 of control I (T72I1, T72I2). Checked with grep and awk on 2026-11-21: line 2 of each csv file says `kernels=aarch64`. No csv field is `NA`. No T row has the flag `late`. In each T row the thread number equals the CPU number. Each P row reports 262144 kB of 262144 kB on 2 MiB pages, buffer `a` only. Each stderr.txt has 0 bytes. Each launches.txt holds two lines. The first line records the launch with the argument line that ran: it equals the line of the spec file of Ref4. The second line starts with `rc 0` (exit status 0). No csv file holds a row that starts with `S,`, `W,`, `B,`, `E,`, `X,`, `TR,`, `M,` or `K,`. Each env.txt names the binary sha256 of line 20 of Ref2. A csv file of like.spec holds 10 I rows, 1200 T rows, 1200 C rows, 1320 P rows and 11 `# page_read` lines. A csv file of cfwd.spec or crev.spec holds 6, 720, 720, 840 and 7. Computed from the T rows of the 9 csv files on 2026-11-21 (the columns have a resolution of 1 us): `t_start_s - t_sched_s` is 2 us to 34 us. `t_end_s - t_sched_s - 6 s` is 0 us to 463 us. The time from the largest `t_end_s` of one interval to the smallest `t_start_s` of the next interval of the same file is 0.064 s to 0.140 s (65 gaps). The time from the largest `t_end_s` of one interval to the `t_sched_s` of the next interval of the same file is 63.8 ms to 139.8 ms (the same 65 gaps). More checks of 2026-11-21 that the explanations cite: line 1 of each csv file says `threads=120 bytes_per_thread=268435456 min_ms=6000 thp=madvise`, and line 2 says `two_buffers=0`. The 9 csv files hold 8880 T rows and 8880 C rows. `elapsed_s` of a T row is 5.999979 s to 6.000457 s. `enabled_ns` equals `running_ns` in every C row. In each of the 74 intervals the value `aggregate_GBps` of the I row and the sum over the T rows of bytes / elapsed_s / 1e9 differ by less than 0.004 %. The times of the `# page_read` lines are 3.745 ms to 4.947 ms (83 lines). Line 6 of each csv file ends with `pmu_type=11 codes=0x198,0x199,0x19a,0x19b,0x19c,0x19`. Every line of the 9 csv files starts with `I`, `T`, `P`, `C` or `#`. Two rows that the explanations quote come from the file a6456.csv of T72L1. Line 7 is its first P row: `P,0,-1,0,a,262144,262144,611480,0,2,0`. Line 129 is its first T row (thread 0, `oldread`). It holds 28934406144 bytes, which is 13797 chunks of 2097152 bytes.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_bwx.py`: lines 52 to 57 and lines 68 to 69: the rate of an interval is the sum over its T rows of bytes / elapsed_s / 1e9. The value `aggregate_GBps` of the I row is kept as `I_agg`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: objdump text of the kernels of bw_new (from line 23) and of bw_old (from line 155). Compared with Ref1 by a script on 2026-11-21, with absolute code addresses and data addresses left out: `k_read` of bw_new against `k_read` of bwx12 (13 instructions, equal), `k_read` of bw_old against `k_oldread` of bwx12 (70 instructions, equal), `k_asmread` of bw_new against `k_asmread` of bwx12 (21 instructions, equal). The same script: `k_write` of bw_new against `k_write` of bwx12 (14 instructions, equal). Loop start modulo 64 in both listings: 36 for `k_read` of bw_new and `k_read` of bwx12, 40 for `k_read` of bw_old and `k_oldread` of bwx12. Lines 19 and 20 of this file give the sha256 of bw_old and of bw_new. The script ra.sh of part A, in the folder of Ref4, holds the same two values at its lines 17 and 18. It ends with status 2 before it starts a binary when one of the two binaries does not have its value (lines 16 to 20). So the two listings show the machine code of the binaries that part A ran.
- [Ref8] `/usr/include/linux/perf_event.h`: lines 307 to 314 (header of the development machine): the layout of a group read is nr, time_enabled, time_running, then one value per counter.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: lines 38 to 89, "Words used here": the project word list. The definitions of CRB, the meshes, whole chip, the kernels, the binaries, process, interval, round, position, the parts, control I, argument line, the row kinds, common stop, rate, 2 MiB pages, marker file and sha256 are copied from it. In the entry "Read kernel" one sentence was changed for this page.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md`: sections B.4 to B.9 (lines 230 to 319): the specification of the first runner bwx.c that the comments cite. It describes the protocol of the common start and stop (B.4), the page-state reading (B.6), the loop placement (B.7) and the counters (B.8).
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`: lines 338 to 343: the parser keeps the CPU, the bytes and elapsed_s of each T row. Lines 356 to 374 (function `bwx_intervals`): the total of an interval is the sum over its T rows of bytes / elapsed_s / 1e9. The script build_facts.py calls this function for the facts sheet.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: line 31: the script builds the binary bw_old from the file bandwidth.orig.c.
- [Ref13] external source: Linux kernel documentation on docs.kernel.org, read on 2026-11-21. The page admin-guide/mm/transhuge.html describes three counters of /proc/vmstat. `thp_fault_alloc` "is incremented every time a huge page is successfully allocated and charged to handle a page fault". `thp_fault_fallback` "is incremented if a page fault fails to allocate or charge a huge page and instead falls back to using small pages". `thp_collapse_alloc` is incremented when the Linux thread khugepaged has allocated a huge page for a range of small pages that it joins into one huge page. The page mm/page_migration.html says that page migration moves the physical location of pages. For the counter PGMIGRATE_SUCCESS it says: "Each count means that a page was migrated." The documentation writes this name in capital letters, and the file /proc/vmstat holds it in small letters. A huge page that was moved adds the number of small pages that it holds. No copy of these pages is on the machine on which this page was written.
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/results/20261030T193108Z/sysinfo.txt`: a record of CRB of 2026-10-30. Lines 65 to 68 describe the four caches that Linux lists for CPU 0. They say `level=1 type=Data`, `level=1 type=Instruction`, `level=2 type=Unified` and `level=3 type=Unified`. Each of these 4 lines says `line=64`. The script run_crb.sh of the folder cache-perf/bench writes a file of this name and form: its line 107 prints `line=` and then the content of the Linux file coherency_line_size of the cache. The Linux documentation describes this file as "the minimum amount of data in bytes that gets transferred from memory to cache" (external source: the file Documentation/ABI/testing/sysfs-devices-system-cpu on www.kernel.org, read on 2026-11-21). A second record of CRB, of 2026-11-15, gives `line=64` for the four caches of CPU 2: lines 109 to 112 of the file hostfacts-20261115T0403Z.txt in the folder crb/new-test-kernel/tackle-8mb-analysis/h3.
